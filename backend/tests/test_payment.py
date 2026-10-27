"""Integração Mercado Pago testada sem internet (respostas da API simuladas)."""
import io

from app.core.config import settings
from app.core.crypto import criptografar, descriptografar
from app.services import payment_service
from tests.test_products import PNG


class _Resp:
    def __init__(self, status, data):
        self.status_code, self._data = status, data

    def json(self):
        return self._data


def _modo_real(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_MODE", "mercadopago")
    monkeypatch.setattr(settings, "MP_ACCESS_TOKEN", "TEST-plataforma")
    monkeypatch.setattr(settings, "MP_PUBLIC_KEY", "TEST-pk-plataforma")


def _produto_aprovado(client, produtor, admin, nome="Doce de Buriti", estoque="5"):
    r = client.post("/api/v1/products", headers=produtor, files=[("imagens", ("f.png", io.BytesIO(PNG), "image/png"))],
                    data={"nome": nome, "preco": "10", "categoria": "Alimentos", "estoque": estoque})
    pid = r.json()["id"]
    client.post(f"/api/v1/admin/products/{pid}/aprovar", headers=admin)
    return pid


def test_cartao_de_credito_com_split(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    pid = _produto_aprovado(client, produtor, admin)
    # Produtor com conta Mercado Pago conectada (tokens criptografados no banco)
    from app.db.database import SessionLocal
    from app.models.user_model import Producer
    db = SessionLocal()
    p = db.query(Producer).filter(Producer.whatsapp == "68999112233").first()
    p.mp_public_key, p.mp_access_token_enc = "TEST-pk-produtor", criptografar("TEST-token-produtor")
    db.commit()
    assert p.mp_access_token_enc != "TEST-token-produtor"               # não fica em texto puro
    db.close()

    enviado = {}

    def fake_post(url, json, headers, timeout):
        enviado.update(url=url, body=json, headers=headers)
        return _Resp(201, {"id": 987, "status": "approved", "status_detail": "accredited",
                           "payment_type_id": "credit_card", "installments": 3})

    monkeypatch.setattr(payment_service.requests, "post", fake_post)
    pedido = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": 2, "nome": "Ana Souza",
                                                  "whatsapp": "68999990000"}).json()
    assert pedido["public_key"] == "TEST-pk-produtor"                   # cartão tokenizado na conta do produtor
    r = client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar", json={
        "payment_method_id": "master", "token": "tok_123", "installments": 3, "issuer_id": "24",
        "payer": {"email": "ana@teste.com", "identification": {"type": "CPF", "number": "12345678909"}},
        # tentativa de manipular o valor pelo navegador é ignorada
        "transaction_amount": 0.01,
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pago" and r.json()["metodo_nome"] == "Crédito"
    assert enviado["body"]["transaction_amount"] == 20.0                # valor sempre do banco
    assert enviado["body"]["application_fee"] == 2.0                    # 10% para a plataforma
    assert enviado["headers"]["Authorization"] == "Bearer TEST-token-produtor"
    assert enviado["headers"]["X-Idempotency-Key"]
    assert "card_number" not in str(enviado["body"])


def test_pix_pendente_e_cartao_recusado(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    pid = _produto_aprovado(client, produtor, admin, nome="Farinha de Cruzeiro")
    respostas = [
        _Resp(201, {"id": 555, "status": "rejected", "status_detail": "cc_rejected_insufficient_amount",
                    "payment_type_id": "debit_card"}),
        _Resp(201, {"id": 556, "status": "pending", "payment_type_id": "bank_transfer",
                    "point_of_interaction": {"transaction_data": {"qr_code": "00020126PIX", "qr_code_base64": "iVBOR"}}}),
    ]
    monkeypatch.setattr(payment_service.requests, "post", lambda *a, **k: respostas.pop(0))
    pedido = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": 1, "nome": "Bia Lima",
                                                  "whatsapp": "68999990001"}).json()
    corpo = {"payment_method_id": "debvisa", "token": "t", "payer": {"email": "b@teste.com"}}
    r = client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar", json=corpo)
    assert r.status_code == 402 and "insuficiente" in r.json()["detail"]
    r = client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar",
                    json={"payment_method_id": "pix", "payer": {"email": "b@teste.com"}})
    assert r.json()["status"] == "aguardando_pagamento" and r.json()["pix_qr_code"] == "00020126PIX"

    # Webhook: o status é reconsultado na API (notificação sozinha não aprova nada)
    monkeypatch.setattr(payment_service.requests, "get", lambda *a, **k: _Resp(200, {
        "id": 556, "status": "approved", "payment_type_id": "bank_transfer"}))
    client.post("/api/v1/checkout/webhook/mercadopago?data.id=556&type=payment", json={"type": "payment", "data": {"id": "556"}})
    final = client.get(f"/api/v1/checkout/{pedido['codigo']}").json()
    assert final["status"] == "pago" and final["pix_qr_code"] is None


def test_webhook_com_assinatura(monkeypatch):
    import hashlib, hmac
    monkeypatch.setattr(settings, "MP_WEBHOOK_SECRET", "segredo")
    manifesto = "id:123;request-id:abc;ts:1700;"
    v1 = hmac.new(b"segredo", manifesto.encode(), hashlib.sha256).hexdigest()
    assert payment_service.assinatura_valida(f"ts=1700,v1={v1}", "abc", "123")
    assert not payment_service.assinatura_valida("ts=1700,v1=falso", "abc", "123")
    assert not payment_service.assinatura_valida(None, "abc", "123")


def test_simulacao_bloqueada_no_modo_real(client, produtor, admin, monkeypatch):
    pid = _produto_aprovado(client, produtor, admin, nome="Castanha")
    pedido = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": 1, "nome": "Caio Reis",
                                                  "whatsapp": "68999990002"}).json()
    _modo_real(monkeypatch)
    assert client.post(f"/api/v1/checkout/{pedido['codigo']}/simular", json={"metodo": "credit_card"}).status_code == 400


def test_criptografia():
    enc = criptografar("APP_USR-segredo")
    assert enc and "segredo" not in enc and descriptografar(enc) == "APP_USR-segredo"


def test_conectar_mercadopago_oauth(client, produtor, monkeypatch):
    monkeypatch.setattr(settings, "MP_CLIENT_ID", "123")
    monkeypatch.setattr(settings, "MP_CLIENT_SECRET", "sec")
    monkeypatch.setattr(settings, "MP_REDIRECT_URI", "https://exemplo.ngrok.app/api/v1/mercadopago/callback")
    url = client.post("/api/v1/producers/me/mercadopago/conectar", headers=produtor).json()["url"]
    assert url.startswith("https://auth.mercadopago.com/authorization?")
    from urllib.parse import parse_qs, urlparse
    state = parse_qs(urlparse(url).query)["state"][0]

    monkeypatch.setattr(payment_service.requests, "post", lambda *a, **k: _Resp(200, {
        "access_token": "APP_USR-tok", "refresh_token": "TG-ref", "public_key": "APP_USR-pk",
        "user_id": 777, "expires_in": 15552000}))
    r = client.get(f"/api/v1/mercadopago/callback?code=abc&state={state}", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("mp=ok")
    perfil = client.get("/api/v1/producers/me", headers=produtor).json()
    assert perfil["mercadopago"]["conectado"] is True and "APP_USR-tok" not in str(perfil)

    # "state" forjado não conecta nada
    r = client.get("/api/v1/mercadopago/callback?code=abc&state=falso", follow_redirects=False)
    assert r.headers["location"].endswith("mp=expirado")
    client.delete("/api/v1/producers/me/mercadopago", headers=produtor)
