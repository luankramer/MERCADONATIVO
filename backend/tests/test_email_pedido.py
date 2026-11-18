"""Pedido pago: comprador e produtor recebem a confirmação por e-mail."""
from app.services import order_service, payment_service
from tests.test_payment import _Resp, _modo_real, _produto_aprovado


def test_compra_aprovada_manda_email_para_comprador_e_produtor(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    pid = _produto_aprovado(client, produtor, admin, nome="Geleia de Cupuaçu")
    from app.db.database import SessionLocal
    from app.models.user_model import Producer
    db = SessionLocal()
    p = db.query(Producer).filter(Producer.whatsapp == "68999112233").first()
    email_antigo, p.email = p.email, "produtor.teste@exemplo.com"
    db.commit()
    db.close()

    emails = []
    monkeypatch.setattr(order_service, "_enviar_email", lambda para, assunto, texto: emails.append((para, assunto, texto)))
    monkeypatch.setattr(payment_service.requests, "post", lambda *a, **k: _Resp(201, {
        "id": 555, "status": "approved", "status_detail": "accredited", "payment_type_id": "credit_card", "installments": 1}))
    try:
        pedido = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": 1, "nome": "Maria Lima",
                                                      "whatsapp": "68999990001"}).json()
        r = client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar", json={
            "payment_method_id": "master", "token": "tok", "installments": 1, "payer": {"email": "Maria@Teste.com"}})
        assert r.status_code == 200, r.text
    finally:
        db = SessionLocal()
        p = db.query(Producer).filter(Producer.whatsapp == "68999112233").first()
        p.email = email_antigo
        db.commit()
        db.close()

    para = {e[0]: e for e in emails}
    assert "maria@teste.com" in para and "produtor.teste@exemplo.com" in para
    _, assunto, texto = para["maria@teste.com"]
    assert "confirmado" in assunto and "Geleia de Cupuaçu" in texto and pedido["codigo"] in texto
    assert "Você recebe" in para["produtor.teste@exemplo.com"][2]


def test_email_falhando_nao_atrapalha(monkeypatch):
    from app.services import email_service
    monkeypatch.setattr(email_service, "email_configurado", lambda: True)

    def explode(*a):
        raise RuntimeError("fora do ar")
    monkeypatch.setattr(email_service, "enviar_email", explode)
    order_service._enviar_email("a@b.com", "x", "y")   # não lança erro
    order_service._enviar_email(None, "x", "y")        # sem e-mail: nada a fazer
