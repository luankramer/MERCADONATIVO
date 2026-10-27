"""Criptografia de dados sensíveis guardados no banco (tokens do Mercado Pago)."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    chave = settings.ENCRYPTION_KEY
    if not chave:
        # Deriva uma chave Fernet estável a partir da SECRET_KEY
        chave = base64.urlsafe_b64encode(hashlib.sha256(("mn-enc:" + settings.SECRET_KEY).encode()).digest()).decode()
    return Fernet(chave.encode())


def criptografar(texto: str | None) -> str | None:
    if not texto:
        return None
    return _fernet().encrypt(texto.encode()).decode()


def descriptografar(texto: str | None) -> str | None:
    if not texto:
        return None
    try:
        return _fernet().decrypt(texto.encode()).decode()
    except InvalidToken:
        return None  # chave trocada: o produtor precisa reconectar a conta
