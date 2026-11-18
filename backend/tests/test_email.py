"""E-mail do sistema: API do Brevo (HTTPS) com prioridade sobre o SMTP."""
import requests

from app.core.config import settings
from app.services import email_service


class _Resposta:
    def __init__(self, status, corpo=None):
        self.status_code, self._corpo = status, corpo or {}

    def json(self):
        return self._corpo


def test_envia_pelo_brevo_quando_configurado(monkeypatch):
    monkeypatch.setattr(settings, "BREVO_API_KEY", "chave-teste")
    monkeypatch.setattr(settings, "EMAIL_REMETENTE", "contato@exemplo.com")
    enviados = []

    def falso_post(url, **kw):
        enviados.append((url, kw))
        return _Resposta(201, {"messageId": "x"})
    monkeypatch.setattr(email_service.requests, "post", falso_post)

    assert email_service.email_configurado()
    assert email_service.enviar_email("cliente@exemplo.com", "Seu código", "Código: 123456\nVale 10 min <b>")
    url, kw = enviados[0]
    assert url == email_service.BREVO_URL and kw["headers"]["api-key"] == "chave-teste"
    corpo = kw["json"]
    assert corpo["sender"] == {"name": "Mercado Nativo", "email": "contato@exemplo.com"}
    assert corpo["to"] == [{"email": "cliente@exemplo.com"}] and "123456" in corpo["textContent"]
    assert "&lt;b&gt;" in corpo["htmlContent"]  # texto escapado no HTML


def test_falha_do_brevo_nao_quebra(monkeypatch):
    monkeypatch.setattr(settings, "BREVO_API_KEY", "chave-errada")
    monkeypatch.setattr(settings, "EMAIL_REMETENTE", "contato@exemplo.com")
    monkeypatch.setattr(email_service.requests, "post",
                        lambda url, **kw: _Resposta(401, {"message": "Key not found"}))
    assert email_service.enviar_email("a@b.com", "x", "y") is False

    def sem_rede(url, **kw):
        raise requests.ConnectionError()
    monkeypatch.setattr(email_service.requests, "post", sem_rede)
    assert email_service.enviar_email("a@b.com", "x", "y") is False


def test_sem_configuracao_nao_envia(monkeypatch):
    monkeypatch.setattr(settings, "BREVO_API_KEY", "")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    assert not email_service.email_configurado()
    assert email_service.enviar_email("a@b.com", "x", "y") is False
