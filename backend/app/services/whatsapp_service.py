"""
Envio de mensagens pelo WhatsApp usando a Evolution API.
As credenciais ficam no .env (EVOLUTION_BASE_URL, EVOLUTION_TOKEN, EVOLUTION_INSTANCE).
"""
import re
from urllib.parse import quote

import httpx

from app.core.config import settings


def somente_digitos(numero: str | None) -> str:
    return re.sub(r"\D", "", numero or "")


def numero_nacional(numero: str | None) -> str:
    """Retorna DDD + número, sem o 55 (ex.: 68999112233)."""
    digitos = somente_digitos(numero)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    return digitos


def numero_internacional(numero: str | None) -> str:
    return "55" + numero_nacional(numero)


def link_whatsapp(numero: str | None, mensagem: str = "") -> str:
    url = f"https://wa.me/{numero_internacional(numero)}"
    return f"{url}?text={quote(mensagem)}" if mensagem else url


def whatsapp_configurado() -> bool:
    return bool(settings.EVOLUTION_BASE_URL and settings.EVOLUTION_TOKEN)


async def enviar_mensagem_openwa(numero: str, texto: str) -> bool:
    """Envia uma mensagem de texto. Retorna False (sem lançar erro) se falhar."""
    if not whatsapp_configurado():
        print("⚠️  WhatsApp não configurado no .env (EVOLUTION_BASE_URL / EVOLUTION_TOKEN).")
        return False

    url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/message/sendText/{settings.EVOLUTION_INSTANCE}"
    # Estrutura simplificada exigida pela Evolution API v2.3+
    payload = {"number": numero_internacional(numero), "text": texto}
    headers = {"Content-Type": "application/json", "apikey": settings.EVOLUTION_TOKEN}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code not in (200, 201):
                print(f"🚨 ERRO EVOLUTION API ({response.status_code}): {response.text}")
                return False
            return True
        except Exception as e:
            print(f"🚨 Falha de conexão com a Evolution API: {e}")
            return False
