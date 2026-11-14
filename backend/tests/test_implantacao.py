"""Publicação num servidor novo (Railway): endereço do banco, domínio público e primeiro administrador."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import config
from app.core.security import verify_password
from app.db.database import Base
from app.models.admin_model import NIVEL_SUPER, Admin
from app.services import implantacao_service


def test_url_do_banco_do_railway_vira_pymysql(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MYSQL_URL", "mysql://root:x@mysql.railway.internal:3306/railway")
    assert config._url_banco() == "mysql+pymysql://root:x@mysql.railway.internal:3306/railway"

    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://root:@localhost:3306/mercado_nativo")
    assert config._url_banco() == "mysql+pymysql://root:@localhost:3306/mercado_nativo"


def test_endereco_publico_usa_o_dominio_do_railway(monkeypatch):
    monkeypatch.delenv("PUBLIC_API_URL", raising=False)
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "backend-producao.up.railway.app")
    assert config._url_publica_api() == "https://backend-producao.up.railway.app"

    monkeypatch.setenv("PUBLIC_API_URL", "https://api.mercadonativo.com.br/")
    assert config._url_publica_api() == "https://api.mercadonativo.com.br"


def _banco_vazio():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_cria_o_super_admin_so_com_o_banco_vazio(monkeypatch):
    monkeypatch.setattr(config.settings, "ADMIN_INICIAL_SENHA", "senha-forte-123")
    db = _banco_vazio()
    try:
        assert implantacao_service.criar_admin_inicial(db) is True
        admin = db.query(Admin).one()
        assert admin.email == config.settings.ADMIN_MASTER_EMAIL
        assert admin.nivel == NIVEL_SUPER
        assert verify_password("senha-forte-123", admin.senha_hash)
        # Segunda vez não mexe em nada (já existe administrador)
        assert implantacao_service.criar_admin_inicial(db) is False
        assert db.query(Admin).count() == 1
    finally:
        db.close()


def test_nao_cria_admin_sem_senha_ou_com_senha_curta(monkeypatch):
    db = _banco_vazio()
    try:
        monkeypatch.setattr(config.settings, "ADMIN_INICIAL_SENHA", "")
        assert implantacao_service.criar_admin_inicial(db) is False
        monkeypatch.setattr(config.settings, "ADMIN_INICIAL_SENHA", "curta")
        assert implantacao_service.criar_admin_inicial(db) is False
        assert db.query(Admin).count() == 0
    finally:
        db.close()
