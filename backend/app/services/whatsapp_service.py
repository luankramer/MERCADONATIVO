"""
Envio de mensagens pelo WhatsApp, com rota de reserva.

1. Evolution API (principal): EVOLUTION_BASE_URL, EVOLUTION_TOKEN, EVOLUTION_INSTANCE.
2. WhatsApp Cloud API da Meta (reserva, opcional): META_WA_TOKEN e META_WA_PHONE_ID.
   - Mensagem de texto livre só chega se a pessoa falou com o número da empresa nas últimas
     24 h (regra da Meta). Para o código de login, cadastre na Meta um modelo da categoria
     "Autenticação" e informe o nome em META_WA_TEMPLATE_CODIGO: ele chega a qualquer hora.
3. Se nada funcionar, os avisos vão para a fila e são reenviados depois (notificacao_service).
"""
import logging
import re
from urllib.parse import quote

import httpx

from app.core.config import settings

log = logging.getLogger("mercado_nativo")
META_API = "https://graph.facebook.com/v21.0"


def somente_digitos(numero: str | None) -> str:
    return re.sub(r"\D", "", numero or "")


def numero_nacional(numero: str | None) -> str:
    """Retorna DDD + número, sem o 55 (ex.: 68999112233)."""
    digitos = somente_digitos(numero)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    return digitos


def numero_valido(numero: str | None) -> bool:
    return len(numero_nacional(numero)) in (10, 11)


def numero_internacional(numero: str | None) -> str:
    return "55" + numero_nacional(numero)


def link_whatsapp(numero: str | None, mensagem: str = "") -> str:
    url = f"https://wa.me/{numero_internacional(numero)}"
    return f"{url}?text={quote(mensagem)}" if mensagem else url


_LINK = re.compile(r"(https?://|www\.)\S*|\S+\.(com|net|org|br|io|me|ly|app|xyz|info)(/\S*)?\b", re.I)


def texto_seguro(texto: str | None, limite: int = 80) -> str:
    """Texto digitado por cliente que vai dentro de uma mensagem enviada pelo número oficial:
    sem links, sem formatação do WhatsApp (* _ ~ `), numa linha só e curto."""
    t = _LINK.sub("[link removido]", texto or "")
    t = re.sub(r"[*_~`]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limite]


def evolution_configurada() -> bool:
    return bool(settings.EVOLUTION_BASE_URL and settings.EVOLUTION_TOKEN)


def meta_configurada() -> bool:
    return bool(settings.META_WA_TOKEN and settings.META_WA_PHONE_ID)


def whatsapp_configurado() -> bool:
    return evolution_configurada() or meta_configurada()


async def _enviar_evolution(numero: str, texto: str) -> bool:
    url = f"{settings.EVOLUTION_BASE_URL.rstrip('/')}/message/sendText/{settings.EVOLUTION_INSTANCE}"
    payload = {"number": numero_internacional(numero), "text": texto}  # formato da Evolution API v2.3+
    headers = {"Content-Type": "application/json", "apikey": settings.EVOLUTION_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code not in (200, 201):
            log.warning("Evolution API respondeu %s", response.status_code)
            return False
        return True
    except Exception as e:
        log.warning("Falha de conexão com a Evolution API: %s", type(e).__name__)
        return False


async def _enviar_meta(numero: str, corpo: dict) -> bool:
    url = f"{META_API}/{settings.META_WA_PHONE_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": numero_internacional(numero), **corpo}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, json=payload,
                                         headers={"Authorization": f"Bearer {settings.META_WA_TOKEN}"})
        if response.status_code not in (200, 201):
            log.warning("WhatsApp Cloud API (Meta) respondeu %s", response.status_code)
            return False
        return True
    except Exception as e:
        log.warning("Falha de conexão com a WhatsApp Cloud API: %s", type(e).__name__)
        return False


async def enviar_mensagem_openwa(numero: str, texto: str) -> bool:
    """Envia uma mensagem de texto pela Evolution API e, se falhar, pela API da Meta.
    Retorna False (sem lançar erro) se nenhuma das duas conseguiu."""
    if not numero:
        return False
    if not whatsapp_configurado():
        print("⚠️  WhatsApp não configurado no .env (EVOLUTION_BASE_URL / EVOLUTION_TOKEN).")
        return False
    if evolution_configurada() and await _enviar_evolution(numero, texto):
        return True
    if meta_configurada():
        return await _enviar_meta(numero, {"type": "text", "text": {"preview_url": False, "body": texto}})
    return False


async def enviar_codigo(numero: str, codigo: str, texto: str) -> bool:
    """Código de acesso: Evolution API; reserva pela Meta com o modelo de autenticação aprovado
    (ou texto simples, se não houver modelo). Nunca vai para a fila: código vence em minutos."""
    if evolution_configurada() and await _enviar_evolution(numero, texto):
        return True
    if not meta_configurada():
        return False
    if settings.META_WA_TEMPLATE_CODIGO:
        return await _enviar_meta(numero, {"type": "template", "template": {
            "name": settings.META_WA_TEMPLATE_CODIGO, "language": {"code": settings.META_WA_IDIOMA},
            "components": [
                {"type": "body", "parameters": [{"type": "text", "text": codigo}]},
                {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": codigo}]},
            ],
        }})
    return await _enviar_meta(numero, {"type": "text", "text": {"preview_url": False, "body": texto}})
