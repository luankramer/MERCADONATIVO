"""
Levar os dados do computador local para o servidor (ex.: Railway).

- exportar(engine): gera um .zip com todas as tabelas (dados.json) e as fotos enviadas.
- importar(engine, conteudo_zip): troca TODO o conteúdo do banco pelo do .zip e grava as fotos.

A importação pelo site só funciona com IMPORTACAO_LIBERADA=true e para o Super Admin
(veja api/v1/importacao.py). Depois de usar, desligue a variável.
"""
import base64
import io
import json
import re
import zipfile
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Date, DateTime, LargeBinary, Numeric, Time, select, text
from sqlalchemy.engine import Engine

import app.models  # noqa: F401  (registra todas as tabelas)
from app.core.config import settings
from app.db.database import Base

VERSAO_FORMATO = 1
EXTENSOES_FOTO = ("jpg", "jpeg", "png", "webp", "gif")
NOME_FOTO = re.compile(r"^uploads/(perfis|produtos)/[A-Za-z0-9_.-]+\.(" + "|".join(EXTENSOES_FOTO) + r")$", re.I)
LIMITE_DESCOMPACTADO = 150 * 1024 * 1024  # proteção contra zip-bomba


class ImportacaoError(Exception):
    pass


def _para_json(valor):
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (bytes, bytearray)):
        return base64.b64encode(bytes(valor)).decode()
    return valor


def _do_json(coluna, valor):
    if valor is None:
        return None
    tipo = coluna.type
    if isinstance(tipo, DateTime):
        return datetime.fromisoformat(valor)
    if isinstance(tipo, Date):
        return date.fromisoformat(valor)
    if isinstance(tipo, Time):
        return time.fromisoformat(valor)
    if isinstance(tipo, Numeric) and isinstance(valor, str):
        return Decimal(valor)
    if isinstance(tipo, LargeBinary):
        return base64.b64decode(valor)
    return valor


def exportar(engine: Engine, pasta_fotos: Path | None = None) -> tuple[bytes, dict]:
    """Devolve (zip, resumo) com o banco inteiro e as fotos."""
    pasta_fotos = pasta_fotos or settings.UPLOAD_DIR
    tabelas: dict[str, list[dict]] = {}
    with engine.connect() as conn:
        for tabela in Base.metadata.sorted_tables:
            linhas = conn.execute(select(tabela)).mappings().all()
            tabelas[tabela.name] = [{k: _para_json(v) for k, v in linha.items()} for linha in linhas]

    buffer = io.BytesIO()
    fotos = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dados.json", json.dumps({"versao": VERSAO_FORMATO, "tabelas": tabelas}, ensure_ascii=False))
        for sub in ("perfis", "produtos"):
            pasta = Path(pasta_fotos) / sub
            if not pasta.is_dir():
                continue
            for arq in sorted(pasta.iterdir()):
                nome = f"uploads/{sub}/{arq.name}"
                if arq.is_file() and NOME_FOTO.match(nome):
                    zf.write(arq, nome)
                    fotos += 1
    resumo = {"tabelas": {n: len(l) for n, l in tabelas.items()}, "fotos": fotos}
    return buffer.getvalue(), resumo


def _ler_zip(conteudo: bytes) -> tuple[dict, list[tuple[str, bytes]]]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(conteudo))
    except zipfile.BadZipFile as e:
        raise ImportacaoError("O arquivo enviado não é um .zip válido.") from e
    total = sum(info.file_size for info in zf.infolist())
    if total > LIMITE_DESCOMPACTADO:
        raise ImportacaoError("O .zip é grande demais.")
    nomes = zf.namelist()
    if "dados.json" not in nomes:
        raise ImportacaoError("O .zip não tem o dados.json.")
    fotos = []
    for nome in nomes:
        if nome == "dados.json" or nome.endswith("/"):
            continue
        if not NOME_FOTO.match(nome):
            raise ImportacaoError(f"Arquivo não permitido no .zip: {nome}")
        fotos.append((nome, zf.read(nome)))
    try:
        dados = json.loads(zf.read("dados.json").decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise ImportacaoError("O dados.json está corrompido.") from e
    if dados.get("versao") != VERSAO_FORMATO or not isinstance(dados.get("tabelas"), dict):
        raise ImportacaoError("Formato de exportação desconhecido.")
    return dados, fotos


def importar(engine: Engine, conteudo: bytes, pasta_fotos: Path | None = None) -> dict:
    """Troca todo o conteúdo do banco pelo do .zip e grava as fotos. Devolve um resumo."""
    pasta_fotos = Path(pasta_fotos or settings.UPLOAD_DIR)
    dados, fotos = _ler_zip(conteudo)
    tabelas_zip: dict = dados["tabelas"]
    conhecidas = {t.name for t in Base.metadata.sorted_tables}
    desconhecidas = set(tabelas_zip) - conhecidas
    if desconhecidas:
        raise ImportacaoError(f"Tabelas desconhecidas no .zip: {', '.join(sorted(desconhecidas))}")

    mysql = engine.dialect.name == "mysql"
    resumo: dict[str, int] = {}
    with engine.begin() as conn:
        if mysql:
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        try:
            for tabela in reversed(Base.metadata.sorted_tables):
                conn.execute(tabela.delete())
            for tabela in Base.metadata.sorted_tables:
                linhas = tabelas_zip.get(tabela.name, [])
                colunas = {c.name: c for c in tabela.columns}
                registros = [{k: _do_json(colunas[k], v) for k, v in linha.items() if k in colunas}
                             for linha in linhas]
                if registros:
                    conn.execute(tabela.insert(), registros)
                resumo[tabela.name] = len(registros)
        finally:
            if mysql:
                conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    for nome, conteudo_foto in fotos:
        destino = pasta_fotos / nome.removeprefix("uploads/")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo_foto)
    return {"tabelas": resumo, "fotos": len(fotos)}
