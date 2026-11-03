"""
Autenticação: hash de senha (bcrypt) e tokens JWT (HS256) para produtores e administradores.

O JWT é gerado com a biblioteca padrão do Python (hmac/hashlib) — não precisa instalar PyJWT.
"""
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db

_bearer = HTTPBearer(auto_error=False)


# ---------------- Senhas ----------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------------- JWT (HS256) ----------------
class TokenInvalido(Exception):
    pass


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def _b64_decode(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _assinar(mensagem: str) -> str:
    return _b64(hmac.new(settings.SECRET_KEY.encode(), mensagem.encode(), hashlib.sha256).digest())


def create_access_token(subject: int, role: str, validade: timedelta | None = None,
                        extra: dict | None = None) -> str:
    if validade is None:
        horas = settings.ADMIN_TOKEN_HOURS if role == "admin" else settings.PRODUCER_TOKEN_HOURS
        validade = timedelta(hours=horas)
    exp = datetime.now(timezone.utc) + validade
    cabecalho = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    dados = {**(extra or {}), "sub": str(subject), "role": role, "exp": int(exp.timestamp())}
    corpo = _b64(json.dumps(dados, separators=(",", ":")).encode())
    return f"{cabecalho}.{corpo}.{_assinar(f'{cabecalho}.{corpo}')}"


def decode_token(token: str) -> dict:
    try:
        cabecalho, corpo, assinatura = token.split(".")
    except ValueError:
        raise TokenInvalido("formato")
    # Compara bytes: um caractere estranho na assinatura vira "token inválido" (401), não erro 500
    if not hmac.compare_digest(assinatura.encode("utf-8", "replace"), _assinar(f"{cabecalho}.{corpo}").encode()):
        raise TokenInvalido("assinatura")
    try:
        payload = json.loads(_b64_decode(corpo))
    except (ValueError, UnicodeDecodeError):
        raise TokenInvalido("conteudo")
    if int(payload.get("exp", 0)) < datetime.now(timezone.utc).timestamp():
        raise TokenInvalido("expirado")
    return payload


def _payload(credentials: HTTPAuthorizationCredentials | None, role: str) -> dict:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar.")
    try:
        payload = decode_token(credentials.credentials)
    except TokenInvalido as e:
        msg = "Sessão expirada. Entre novamente." if str(e) == "expirado" else "Sessão inválida. Entre novamente."
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, msg)
    if payload.get("role") != role:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acesso não permitido para este perfil.")
    return payload


def _decode(credentials: HTTPAuthorizationCredentials | None, role: str) -> int:
    return int(_payload(credentials, role)["sub"])


def token_produtor(produtor) -> str:
    """Token de login do produtor, preso à versão atual da conta (ver Producer.token_versao)."""
    return create_access_token(produtor.id, "producer", extra={"tv": int(produtor.token_versao or 0)})


# ---------------- Dependências das rotas ----------------
def get_current_producer(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
):
    from app.models.user_model import Producer

    payload = _payload(credentials, "producer")
    producer = db.get(Producer, int(payload["sub"]))
    if not producer or producer.ativo is False:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Produtor não encontrado ou inativo.")
    # Depois de trocar o WhatsApp de login, as sessões abertas antes da troca deixam de valer
    if int(payload.get("tv", 0)) != int(producer.token_versao or 0):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão encerrada. Entre novamente.")
    return producer


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
):
    from app.models.admin_model import Admin

    admin_id = _decode(credentials, "admin")
    admin = db.get(Admin, admin_id)
    if not admin or admin.ativo is False:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Administrador não encontrado ou inativo.")
    return admin


def get_super_admin(admin=Depends(get_current_admin)):
    if not admin.is_super:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Apenas o Super Admin pode gerenciar a equipe.")
    return admin
