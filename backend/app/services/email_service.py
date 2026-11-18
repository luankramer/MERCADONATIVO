"""
E-mail do sistema: código de login (reserva do WhatsApp) e recuperação de senha do admin.

Dois jeitos de enviar (o primeiro configurado é usado):
1. API do Brevo (HTTPS): BREVO_API_KEY + EMAIL_REMETENTE. Funciona no Railway, que bloqueia SMTP
   nos planos Trial/Hobby. Plano grátis: 300 e-mails por dia.
2. SMTP: SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD e SMTP_FROM (ex.: Gmail com senha de app).
"""
import html
import logging
import smtplib
import ssl
from email.message import EmailMessage

import requests

from app.core.config import settings

BREVO_URL = "https://api.brevo.com/v3/smtp/email"

log = logging.getLogger("mercado_nativo")


def brevo_configurado() -> bool:
    return bool(settings.BREVO_API_KEY and settings.EMAIL_REMETENTE)


def smtp_configurado() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def email_configurado() -> bool:
    return brevo_configurado() or smtp_configurado()


def _html(texto: str) -> str:
    corpo = html.escape(texto).replace("\n", "<br>")
    return (f'<div style="font-family:Arial,sans-serif;font-size:16px;line-height:1.5;color:#14231C">'
            f'<p style="font-size:18px;font-weight:bold;color:#0B6B4A">Mercado Nativo</p><p>{corpo}</p></div>')


def _enviar_brevo(para: str, assunto: str, texto: str) -> bool:
    try:
        r = requests.post(BREVO_URL, timeout=15, headers={
            "api-key": settings.BREVO_API_KEY, "accept": "application/json", "content-type": "application/json",
        }, json={
            "sender": {"name": settings.EMAIL_REMETENTE_NOME, "email": settings.EMAIL_REMETENTE},
            "to": [{"email": para}],
            "subject": assunto,
            "textContent": texto,
            "htmlContent": _html(texto),
        })
    except requests.RequestException as e:
        log.warning("Falha de conexão com o Brevo: %s", type(e).__name__)
        return False
    if r.status_code in (200, 201, 202):
        return True
    # A mensagem do Brevo ajuda a achar o problema (chave errada, remetente não verificado...)
    try:
        detalhe = r.json().get("message", "")
    except ValueError:
        detalhe = ""
    log.warning("Brevo recusou o e-mail (HTTP %s): %s", r.status_code, str(detalhe)[:200])
    return False


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
    if brevo_configurado():
        return _enviar_brevo(para, assunto, texto)
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
