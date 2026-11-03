"""
E-mail simples (SMTP), usado como reserva do WhatsApp para o código de login.

Configure no .env: SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD e SMTP_FROM.
Funciona com Gmail (senha de app), Outlook, Zoho, Brevo, etc.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("mercado_nativo")


def email_configurado() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def mascarar(email: str | None) -> str:
    """cleyton@exemplo.com -> cl****@exemplo.com"""
    if not email or "@" not in email:
        return ""
    nome, dominio = email.split("@", 1)
    return f"{nome[:2]}{'*' * max(2, len(nome) - 2)}@{dominio}"


def enviar_email(para: str, assunto: str, texto: str) -> bool:
    """Envia um e-mail de texto. Retorna False (sem lançar erro) se não conseguir."""
    if not email_configurado() or not para:
        return False
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = para
    msg["Subject"] = assunto
    msg.set_content(texto)
    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15,
                                  context=ssl.create_default_context()) as s:
                if settings.SMTP_USER:
                    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
                s.starttls(context=ssl.create_default_context())
                if settings.SMTP_USER:
                    s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(msg)
        return True
    except Exception as e:
        log.warning("Falha ao enviar e-mail: %s", type(e).__name__)
        return False
