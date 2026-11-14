import os
import sys
import tempfile
from pathlib import Path

# Banco SQLite temporário: os testes nunca tocam no MySQL de verdade
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.db"
os.environ["PAYMENT_MODE"] = "simulado"
os.environ["SECRET_KEY"] = "chave-de-teste-com-mais-de-32-caracteres-123"
os.environ["OTP_DEV_MODE"] = "true"
os.environ["EVOLUTION_BASE_URL"] = ""
os.environ["EVOLUTION_TOKEN"] = ""
os.environ["ADMIN_MASTER_EMAIL"] = "mestre@teste.com"
os.environ["TAREFAS_AUTOMATICAS"] = "false"   # nos testes, as tarefas são chamadas na mão
os.environ["MP_TENTATIVAS"] = "0"            # sem esperas entre tentativas nos testes
os.environ["META_WA_TOKEN"] = ""
os.environ["SMTP_HOST"] = ""
os.environ["PIX_RESERVA_CHAVE"] = ""
os.environ["DADOS_DEMO"] = "false"            # sem dados de demonstração nos testes
os.environ["ADMIN_INICIAL_SENHA"] = ""
os.environ["UPLOAD_DIR"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        # Cria o Super Admin dos testes (não existe mais senha padrão)
        from app.core.security import hash_password
        from app.db.database import SessionLocal
        from app.models.admin_model import Admin
        db = SessionLocal()
        if not db.query(Admin).filter(Admin.email == "mestre@teste.com").first():
            db.add(Admin(nome="Mestre", email="mestre@teste.com", senha_hash=hash_password("senha123"), nivel="super"))
            db.commit()
        db.close()
        yield c


@pytest.fixture(autouse=True)
def _sem_limites():
    from app.api.v1.auth import otp_storage
    from app.core.rate_limit import resetar_tudo
    from app.services.payment_service import resetar_circuito
    resetar_tudo()
    resetar_circuito()
    otp_storage.clear()
    yield


def _pedir_codigo(client, whatsapp):
    """Pede o código e devolve (desafio, código). O código só existe no servidor (nunca na resposta)."""
    r = client.post("/api/v1/auth/producer/request-code", json={"whatsapp": whatsapp})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert "dev_code" not in corpo and "code" not in corpo   # o código nunca vai para o navegador
    from app.api.v1.auth import otp_storage
    return corpo["desafio"], otp_storage[corpo["desafio"]]["code"]


def _login_produtor(client, whatsapp):
    desafio, code = _pedir_codigo(client, whatsapp)
    r = client.post("/api/v1/auth/producer/verify-code", json={"whatsapp": whatsapp, "code": code, "desafio": desafio})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def produtor(client):
    r = client.post("/api/v1/auth/producer/register", json={"aceite_termos": True, 
        "name": "Dona Carmem", "business_name": "Doce Querência", "whatsapp": "(68) 9 9911-2233",
        "description": "Geleias caseiras", "city": "rio branco", "cep": "69900-000", "address": "Rua A",
    })
    assert r.status_code == 201, r.text
    return _login_produtor(client, "68999112233")


@pytest.fixture(scope="session")
def admin(client):
    r = client.post("/api/v1/auth/admin/login", json={"email": "mestre@teste.com", "senha": "senha123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
