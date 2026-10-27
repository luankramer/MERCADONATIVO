"""Conexão do produtor com o Mercado Pago pelo link enviado no WhatsApp."""
import re

import pytest

from app.core.config import settings
from app.services import conexao_mp_service, payment_service


@pytest.fixture
def split_ligado(monkeypatch):
    monkeypatch.setattr(settings, "MP_CLIENT_ID", "123")
    monkeypatch.setattr(settings, "MP_CLIENT_SECRET", "segredo")
    monkeypatch.setattr(settings, "MP_REDIRECT_URI", "https://exemplo.ngrok-free.dev/api/v1/mercadopago/callback")
    monkeypatch.setattr(settings, "PUBLIC_API_URL", "https://exemplo.ngrok-free.dev")
    mensagens = []

    async def falso_envio(numero, texto):
        mensagens.append((numero, texto))
        return True
    monkeypatch.setattr(conexao_mp_service, "enviar_mensagem_openwa", falso_envio)
    return mensagens


def _token_do_link(texto):
    return re.search(r"/api/v1/mercadopago/conectar/(\S+)", texto).group(1)


def test_link_whatsapp_conecta_uma_vez(client, produtor, split_ligado, monkeypatch):
    r = client.post("/api/v1/producers/me/mercadopago/enviar-link", headers=produtor)
    assert r.status_code == 200, r.text
    numero, texto = split_ligado[-1]
    assert "Autorizar" in texto and "código" in texto
    token = _token_do_link(texto)

    # O link leva direto para a autorização do Mercado Pago
    r = client.get(f"/api/v1/mercadopago/conectar/{token}", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("https://auth.mercadopago.com/authorization")
    state = re.search(r"state=([^&]+)", r.headers["location"]).group(1)

    # Retorno do Mercado Pago (troca do código simulada): página simples + aviso no WhatsApp
    def falsa_troca(prod, code):
        prod.mp_access_token_enc, prod.mp_public_key, prod.mp_user_id = "x", "TEST-pk", "999"
    monkeypatch.setattr(payment_service, "trocar_codigo", falsa_troca)
    r = client.get("/api/v1/mercadopago/callback", params={"code": "TG-1", "state": state})
    assert r.status_code == 200 and "Pronto!" in r.text
    assert "foi conectada" in split_ligado[-1][1]

    # Link de uso único: depois de conectar, não funciona de novo
    r = client.get(f"/api/v1/mercadopago/conectar/{token}", follow_redirects=False)
    assert r.status_code == 400 and "Link vencido" in r.text
    perfil = client.get("/api/v1/producers/me", headers=produtor).json()
    assert perfil["mercadopago"]["conectado"] is True
    client.delete("/api/v1/producers/me/mercadopago", headers=produtor)


def test_link_novo_invalida_o_anterior(client, produtor, split_ligado):
    client.post("/api/v1/producers/me/mercadopago/enviar-link", headers=produtor)
    antigo = _token_do_link(split_ligado[-1][1])
    client.post("/api/v1/producers/me/mercadopago/enviar-link", headers=produtor)
    r = client.get(f"/api/v1/mercadopago/conectar/{antigo}", follow_redirects=False)
    assert r.status_code == 400
    assert client.get("/api/v1/mercadopago/conectar/token-falso", follow_redirects=False).status_code == 400


def test_admin_envia_link_sem_ver_o_link(client, admin, produtor, split_ligado):
    lista = client.get("/api/v1/admin/producers", headers=admin).json()
    alvo = next(v for v in lista if v["nome_loja"] == "Doce Querência")
    assert alvo["mp_conectado"] is False
    r = client.post(f"/api/v1/admin/producers/{alvo['id']}/mercadopago/enviar-link", headers=admin)
    assert r.status_code == 200 and "conectar" not in r.text   # o link vai só para o WhatsApp do produtor
    assert "/mercadopago/conectar/" in split_ligado[-1][1]


def test_sem_split_configurado_nao_envia(client, produtor):
    r = client.post("/api/v1/producers/me/mercadopago/enviar-link", headers=produtor)
    assert r.status_code == 400
