"""Levar os dados do computador local para o servidor: exportar, importar e a rota protegida."""
import io
import json
import zipfile

import pytest
from sqlalchemy import create_engine, func, select

from app.api.v1 import importacao as rota
from app.core.config import settings
from app.db.database import Base, engine
from app.models.admin_model import Admin
from app.models.user_model import Producer
from app.services import importacao_service as servico


def test_exporta_e_importa_banco_e_fotos(client, produtor, tmp_path):
    origem = tmp_path / "origem"
    (origem / "produtos").mkdir(parents=True)
    (origem / "produtos" / "p1_abc.jpg").write_bytes(b"foto")
    (origem / "produtos" / "nao_e_foto.exe").write_bytes(b"x")  # fica de fora

    conteudo, resumo = servico.exportar(engine, origem)
    assert resumo["fotos"] == 1 and resumo["tabelas"]["producers"] >= 1

    destino_engine = create_engine("sqlite://")
    Base.metadata.create_all(destino_engine)
    destino = tmp_path / "destino"
    resultado = servico.importar(destino_engine, conteudo, destino)

    assert (destino / "produtos" / "p1_abc.jpg").read_bytes() == b"foto"
    assert resultado["fotos"] == 1
    with engine.connect() as a, destino_engine.connect() as b:
        assert a.scalar(select(func.count()).select_from(Producer.__table__)) == \
               b.scalar(select(func.count()).select_from(Producer.__table__))
        # Os administradores do servidor não são trocados
        assert b.scalar(select(func.count()).select_from(Admin.__table__)) == 0
        loja = b.execute(select(Producer.__table__.c.business_name)).scalars().all()
        assert "Doce Querência" in loja

    # Importar de novo troca tudo (não duplica)
    servico.importar(destino_engine, conteudo, destino)
    with destino_engine.connect() as b:
        assert b.scalar(select(func.count()).select_from(Producer.__table__)) == resumo["tabelas"]["producers"]


def _zip(arquivos: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for nome, dado in arquivos.items():
            zf.writestr(nome, dado)
    return buf.getvalue()


@pytest.mark.parametrize("nome", ["../../app/main.py", "uploads/produtos/../../x.jpg", "uploads/outra/x.jpg",
                                  "uploads/produtos/script.html"])
def test_recusa_arquivos_fora_das_fotos(nome, tmp_path):
    dados = json.dumps({"versao": 1, "tabelas": {}})
    with pytest.raises(servico.ImportacaoError):
        servico.importar(create_engine("sqlite://"), _zip({"dados.json": dados, nome: b"x"}), tmp_path)


def test_recusa_zip_invalido_ou_sem_dados(tmp_path):
    with pytest.raises(servico.ImportacaoError):
        servico.importar(create_engine("sqlite://"), b"nao e zip", tmp_path)
    with pytest.raises(servico.ImportacaoError):
        servico.importar(create_engine("sqlite://"), _zip({"outro.txt": b"x"}), tmp_path)


def test_rota_fica_desligada_sem_a_variavel(client, admin, monkeypatch):
    monkeypatch.setattr(settings, "IMPORTACAO_LIBERADA", False)
    r = client.post("/api/v1/admin/importacao", headers=admin, files={"arquivo": ("a.zip", b"x", "application/zip")})
    assert r.status_code == 404


def test_rota_exige_admin_e_importa_quando_liberada(client, admin, monkeypatch):
    monkeypatch.setattr(settings, "IMPORTACAO_LIBERADA", True)
    r = client.post("/api/v1/admin/importacao", files={"arquivo": ("a.zip", b"x", "application/zip")})
    assert r.status_code in (401, 403)

    chamado = {}

    def falso_importar(eng, conteudo):  # não mexe no banco dos testes
        chamado["bytes"] = conteudo
        return {"tabelas": {"producers": 2}, "fotos": 3}
    monkeypatch.setattr(rota, "importar", falso_importar)
    r = client.post("/api/v1/admin/importacao", headers=admin, files={"arquivo": ("a.zip", b"zipzip", "application/zip")})
    assert r.status_code == 200 and r.json()["fotos"] == 3 and chamado["bytes"] == b"zipzip"
