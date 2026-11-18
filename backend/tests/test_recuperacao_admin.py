"""Recuperação de conta do painel administrativo ("Esqueci minha senha")."""
import re

import pytest

from app.core import rate_limit
from app.core.config import settings
from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.admin_model import Admin
from app.services import recuperacao_admin_service as recuperacao

MENSAGEM_PADRAO = "Se este e-mail for de um administrador"


@pytest.fixture
def whatsapp_falso(monkeypatch):
    rate_limit.resetar_tudo()
    enviados = []

    async def falso(numero, codigo, texto):
        enviados.append((numero, codigo, texto))
        return True
    monkeypatch.setattr(recuperacao, "enviar_codigo", falso)
    monkeypatch.setattr(settings, "ADMIN_MASTER_WHATSAPP", "(68) 9 9999-8888")
    yield enviados
    # Devolve a senha usada pelos outros testes
    db = SessionLocal()
    mestre = db.query(Admin).filter(Admin.email == "mestre@teste.com").first()
    mestre.senha_hash = hash_password("senha123")
    mestre.whatsapp = None
    db.commit()
    db.close()
    rate_limit.resetar_tudo()


def _pedir(client, email):
    r = client.post("/api/v1/auth/admin/recuperar", json={"email": email})
    assert r.status_code == 200, r.text
    assert MENSAGEM_PADRAO in r.json()["mensagem"]
    return r.json()["desafio"]


def test_super_admin_recupera_a_senha_pelo_whatsapp(client, whatsapp_falso):
    desafio = _pedir(client, "MESTRE@teste.com")
    numero, codigo, texto = whatsapp_falso[-1]
    assert numero == "68999998888" and re.fullmatch(r"\d{6}", codigo) and codigo in texto

    r = client.post("/api/v1/auth/admin/recuperar/confirmar",
                    json={"desafio": desafio, "codigo": "000000" if codigo != "000000" else "111111",
                          "nova_senha": "senha-nova-123"})
    assert r.status_code == 400 and "incorreto" in r.json()["detail"]

    r = client.post("/api/v1/auth/admin/recuperar/confirmar",
                    json={"desafio": desafio, "codigo": codigo, "nova_senha": "senha-nova-123"})
    assert r.status_code == 200, r.text
    assert client.post("/api/v1/auth/admin/login", json={"email": "mestre@teste.com", "senha": "senha123"}).status_code == 401
    assert client.post("/api/v1/auth/admin/login",
                       json={"email": "mestre@teste.com", "senha": "senha-nova-123"}).status_code == 200
    # O código é de uso único
    r = client.post("/api/v1/auth/admin/recuperar/confirmar",
                    json={"desafio": desafio, "codigo": codigo, "nova_senha": "outra-senha-123"})
    assert r.status_code == 400


def test_email_desconhecido_tem_a_mesma_resposta_e_nao_envia(client, whatsapp_falso):
    desafio = _pedir(client, "ninguem@teste.com")
    assert whatsapp_falso == []
    r = client.post("/api/v1/auth/admin/recuperar/confirmar",
                    json={"desafio": desafio, "codigo": "123456", "nova_senha": "senha-nova-123"})
    assert r.status_code == 400


def test_cinco_erros_invalidam_o_codigo(client, whatsapp_falso):
    desafio = _pedir(client, "mestre@teste.com")
    codigo = whatsapp_falso[-1][1]
    errado = "000000" if codigo != "000000" else "111111"
    for _ in range(recuperacao.MAX_TENTATIVAS):
        r = client.post("/api/v1/auth/admin/recuperar/confirmar",
                        json={"desafio": desafio, "codigo": errado, "nova_senha": "senha-nova-123"})
        assert r.status_code == 400
    r = client.post("/api/v1/auth/admin/recuperar/confirmar",
                    json={"desafio": desafio, "codigo": codigo, "nova_senha": "senha-nova-123"})
    assert r.status_code == 400 and "Peça um novo código" in r.json()["detail"]


def test_pedido_novo_invalida_o_anterior(client, whatsapp_falso):
    antigo = _pedir(client, "mestre@teste.com")
    codigo_antigo = whatsapp_falso[-1][1]
    _pedir(client, "mestre@teste.com")
    r = client.post("/api/v1/auth/admin/recuperar/confirmar",
                    json={"desafio": antigo, "codigo": codigo_antigo, "nova_senha": "senha-nova-123"})
    assert r.status_code == 400


def test_whatsapp_do_admin_no_cadastro(client, admin, whatsapp_falso):
    lista = client.get("/api/v1/auth/admin/list", headers=admin).json()
    mestre = next(a for a in lista if a["email"] == "mestre@teste.com")
    corpo = {"nome": mestre["nome"], "email": mestre["email"], "whatsapp": "123"}
    assert client.put(f"/api/v1/auth/admin/{mestre['id']}", headers=admin, json=corpo).status_code == 400
    corpo["whatsapp"] = "(68) 9 8107-1483"
    assert client.put(f"/api/v1/auth/admin/{mestre['id']}", headers=admin, json=corpo).status_code == 200
    lista = client.get("/api/v1/auth/admin/list", headers=admin).json()
    assert next(a for a in lista if a["id"] == mestre["id"])["whatsapp"] == "68981071483"
    # O número do cadastro tem prioridade sobre o ADMIN_MASTER_WHATSAPP
    _pedir(client, "mestre@teste.com")
    assert whatsapp_falso[-1][0] == "68981071483"


def test_super_admin_exclui_outro_super_admin_mas_nao_o_principal_nem_a_si_mesmo(client, admin):
    from app.models.admin_model import NIVEL_SUPER
    db = SessionLocal()
    extra = Admin(nome="Duplicado", email="mestre@teste.co", senha_hash=hash_password("senha-qualquer-1"), nivel=NIVEL_SUPER)
    db.add(extra)
    db.commit()
    extra_id = extra.id
    mestre_id = db.query(Admin).filter(Admin.email == "mestre@teste.com").first().id
    db.close()
    lista = {a["email"]: a for a in client.get("/api/v1/auth/admin/list", headers=admin).json()}
    assert lista["mestre@teste.com"]["principal"] is True and lista["mestre@teste.co"]["principal"] is False
    assert client.delete(f"/api/v1/auth/admin/{mestre_id}", headers=admin).status_code == 400
    assert client.delete(f"/api/v1/auth/admin/{extra_id}", headers=admin).status_code == 200
    assert "mestre@teste.co" not in {a["email"] for a in client.get("/api/v1/auth/admin/list", headers=admin).json()}
