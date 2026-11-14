"""Cancelamento de pedidos e devolução do dinheiro."""
from app.core.config import settings
from app.core.crypto import criptografar
from app.services import payment_service
from tests.test_payment import _modo_real, _produto_aprovado, _Resp

WHATS = "68999990000"


def _estoque(client, pid):
    return client.get(f"/api/v1/public/products/{pid}", params={"registrar_visita": False}).json()["estoque"]


def _pedido_pago(client, pid, qtd=2):
    pedido = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": qtd,
                                                  "nome": "Ana Souza", "whatsapp": WHATS}).json()
    pago = client.post(f"/api/v1/checkout/{pedido['codigo']}/simular", json={"metodo": "pix"}).json()
    if pago["status"] != "pago":  # Pix simulado: confirma o pagamento
        pago = client.post(f"/api/v1/checkout/{pedido['codigo']}/simular/confirmar-pix").json()
    assert pago["status"] == "pago"
    return pago


def test_cliente_pede_cancelamento_e_a_equipe_aprova(client, produtor, admin):
    pid = _produto_aprovado(client, produtor, admin, nome="Doce de Caju", estoque="5")
    pedido = _pedido_pago(client, pid)
    assert _estoque(client, pid) == 3
    assert pedido["pode_cancelar"] is False and pedido["pode_solicitar_cancelamento"] is True
    url = f"/api/v1/checkout/{pedido['codigo']}/cancelar"
    assert client.post(url, json={"whatsapp_final": "1234"}).status_code == 403   # não é o comprador
    r = client.post(url, json={"whatsapp_final": WHATS[-4:], "motivo": "Mudei de ideia"})
    assert r.status_code == 200, r.text
    c = r.json()
    # pago: NÃO cancela na hora; vira um pedido para a equipe conferir com o produtor
    assert c["status"] == "pago" and c["solicitacao"]["status"] == "pendente"
    assert c["solicitacao"]["motivo"] == "Mudei de ideia" and c["pode_solicitar_cancelamento"] is False
    assert _estoque(client, pid) == 3
    assert client.post(url, json={"whatsapp_final": WHATS[-4:]}).status_code == 400  # já pediu
    # a equipe vê o pedido na fila e o produtor vê o aviso no painel
    assert client.get("/api/v1/admin/orders/solicitacoes/total", headers=admin).json()["total"] == 1
    fila = client.get("/api/v1/admin/orders", headers=admin, params={"status": "solicitacoes"}).json()
    assert [x["id"] for x in fila] == [c["numero"]]
    meus = client.get("/api/v1/producers/me/orders", headers=produtor).json()
    assert next(p for p in meus if p["id"] == c["numero"])["solicitacao"]["status"] == "pendente"
    # a equipe confirmou com o produtor que não foi entregue: aprova (cancela e devolve)
    r = client.post(f"/api/v1/admin/orders/{c['numero']}/cancelar", headers=admin,
                    json={"motivo": "Produtor confirmou que não entregou"})
    assert r.status_code == 200 and r.json()["status"] == "cancelado"
    info = client.get(f"/api/v1/checkout/{pedido['codigo']}").json()
    assert info["solicitacao"]["status"] == "aprovada" and info["reembolso_status"] == "simulado"
    assert info["whatsapp_link"] is None and _estoque(client, pid) == 5
    assert client.get("/api/v1/admin/orders/solicitacoes/total", headers=admin).json()["total"] == 0
    # Cancelado não entra no faturamento do admin
    extrato = client.get("/api/v1/admin/overview", headers=admin).json()["extrato_split"]
    assert all(e["id"] != c["numero"] for e in extrato)


def test_equipe_recusa_quando_o_produto_ja_foi_entregue(client, produtor, admin):
    pid = _produto_aprovado(client, produtor, admin, nome="Queijo Coalho", estoque="3")
    pedido = _pedido_pago(client, pid, qtd=1)
    client.post(f"/api/v1/checkout/{pedido['codigo']}/cancelar", json={"whatsapp_final": WHATS[-4:]})
    recusa = f"/api/v1/admin/orders/{pedido['numero']}/solicitacao/recusar"
    assert client.post(recusa, headers=admin, json={"motivo": "ok"}).status_code == 422  # motivo curto demais
    r = client.post(recusa, headers=admin, json={"motivo": "O produtor entregou o produto ontem"})
    assert r.status_code == 200, r.text
    info = client.get(f"/api/v1/checkout/{pedido['codigo']}").json()
    assert info["status"] == "pago" and info["solicitacao"]["status"] == "recusada"
    assert info["solicitacao"]["resposta"] == "O produtor entregou o produto ontem"
    assert _estoque(client, pid) == 2                                  # nada foi devolvido
    assert info["pode_solicitar_cancelamento"] is False                # depois da recusa, só pelo SAC
    assert client.post(recusa, headers=admin, json={"motivo": "de novo"}).status_code == 400


def test_pedido_nao_pago_o_cliente_cancela_na_hora(client, produtor, admin):
    pid = _produto_aprovado(client, produtor, admin, nome="Pupunha", estoque="3")
    pedido = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": 1,
                                                  "nome": "Ana Souza", "whatsapp": WHATS}).json()
    assert pedido["pode_cancelar"] is True
    r = client.post(f"/api/v1/checkout/{pedido['codigo']}/cancelar", json={"whatsapp_final": WHATS[-4:]})
    assert r.status_code == 200 and r.json()["status"] == "cancelado"
    assert r.json()["reembolso_status"] == "sem_cobranca" and r.json()["solicitacao"] is None


def test_depois_da_retirada_so_a_equipe_cancela(client, produtor, admin):
    pid = _produto_aprovado(client, produtor, admin, nome="Farinha de Cruzeiro", estoque="4")
    pedido = _pedido_pago(client, pid, qtd=1)
    assert client.patch(f"/api/v1/producers/me/orders/{pedido['numero']}/retirado", headers=produtor).status_code == 200
    info = client.get(f"/api/v1/checkout/{pedido['codigo']}").json()
    assert info["pode_cancelar"] is False and info["dentro_do_prazo"] is True and info["prazo_arrependimento"]
    # dentro dos 7 dias o cliente pode pedir; quem decide é a equipe
    assert info["pode_solicitar_cancelamento"] is True
    r = client.post(f"/api/v1/checkout/{pedido['codigo']}/cancelar", json={"whatsapp_final": WHATS[-4:]})
    assert r.status_code == 200 and r.json()["status"] == "retirado" and r.json()["solicitacao"]["status"] == "pendente"
    assert client.post(f"/api/v1/producers/me/orders/{pedido['numero']}/cancelar", headers=produtor,
                       json={"motivo": "teste"}).status_code == 400
    lista = client.get("/api/v1/admin/orders", headers=admin, params={"q": "Farinha"}).json()
    assert lista[0]["pode_cancelar"] is True
    r = client.post(f"/api/v1/admin/orders/{pedido['numero']}/cancelar", headers=admin,
                    json={"motivo": "Arrependimento em 7 dias"})
    assert r.status_code == 200 and r.json()["status"] == "cancelado"
    assert _estoque(client, pid) == 4


def test_produtor_cancela_quando_acaba_o_produto(client, produtor, admin):
    pid = _produto_aprovado(client, produtor, admin, nome="Mel de Jandaíra", estoque="3")
    pedido = _pedido_pago(client, pid, qtd=1)
    r = client.post(f"/api/v1/producers/me/orders/{pedido['numero']}/cancelar", headers=produtor,
                    json={"motivo": "O lote acabou"})
    assert r.status_code == 200 and r.json()["cancelado_por"] == "produtor"
    meus = client.get("/api/v1/producers/me/orders", headers=produtor).json()
    assert any(p["id"] == pedido["numero"] and p["status"] == "cancelado" for p in meus)


def _conectar_produtor():
    from app.db.database import SessionLocal
    from app.models.user_model import Producer
    db = SessionLocal()
    p = db.query(Producer).filter(Producer.whatsapp == "68999112233").first()
    p.mp_public_key, p.mp_access_token_enc = "TEST-pk-produtor", criptografar("TEST-token-produtor")
    db.commit()
    db.close()


def _desconectar_produtor():
    from app.db.database import SessionLocal
    from app.models.user_model import Producer
    db = SessionLocal()
    p = db.query(Producer).filter(Producer.whatsapp == "68999112233").first()
    p.mp_public_key = p.mp_access_token_enc = None
    db.commit()
    db.close()


def test_devolucao_real_sai_da_conta_do_produtor_no_split(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    pid = _produto_aprovado(client, produtor, admin, nome="Polpa de Cupuaçu", estoque="5")
    _conectar_produtor()
    chamadas = []

    def post(url, json, headers, timeout):
        chamadas.append((url, headers))
        if url.endswith("/refunds"):
            return _Resp(201, {"id": 555, "status": "approved"})
        return _Resp(201, {"id": 777, "status": "approved", "status_detail": "accredited",
                           "payment_type_id": "credit_card", "installments": 1})
    monkeypatch.setattr(payment_service.requests, "post", post)
    try:
        pedido = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": 1,
                                                      "nome": "Ana Souza", "whatsapp": WHATS}).json()
        client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar", json={
            "payment_method_id": "master", "token": "tok", "installments": 1,
            "payer": {"email": "ana@teste.com"}})
        r = client.post(f"/api/v1/checkout/{pedido['codigo']}/cancelar", json={"whatsapp_final": WHATS[-4:]})
        assert r.status_code == 200 and r.json()["solicitacao"]["status"] == "pendente"
        assert not chamadas[-1][0].endswith("/refunds")                 # ainda não devolveu: espera a equipe
        r = client.post(f"/api/v1/admin/orders/{pedido['numero']}/cancelar", headers=admin,
                        json={"motivo": "Produtor confirmou que não entregou"})
        assert r.status_code == 200, r.text
        url, headers = chamadas[-1]
        assert url.endswith("/v1/payments/777/refunds")
        assert headers["Authorization"] == "Bearer TEST-token-produtor"    # sai da conta do produtor
        assert r.json()["reembolso_status"] == "approved"
    finally:
        _desconectar_produtor()


def test_se_a_devolucao_falhar_o_pedido_continua_pago(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    pid = _produto_aprovado(client, produtor, admin, nome="Banana Passa", estoque="5")

    def post(url, json, headers, timeout):
        if url.endswith("/refunds"):
            return _Resp(400, {"message": "insufficient_amount"})
        return _Resp(201, {"id": 888, "status": "approved", "status_detail": "accredited",
                           "payment_type_id": "pix", "installments": 1})
    monkeypatch.setattr(payment_service.requests, "post", post)
    pedido = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": 1,
                                                  "nome": "Ana Souza", "whatsapp": WHATS}).json()
    client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar", json={
        "payment_method_id": "pix", "payer": {"email": "ana@teste.com"}})
    client.post(f"/api/v1/checkout/{pedido['codigo']}/cancelar", json={"whatsapp_final": WHATS[-4:]})
    r = client.post(f"/api/v1/admin/orders/{pedido['numero']}/cancelar", headers=admin,
                    json={"motivo": "Produtor confirmou que não entregou"})
    assert r.status_code == 400 and "devolver" in r.json()["detail"]
    info = client.get(f"/api/v1/checkout/{pedido['codigo']}").json()
    assert info["status"] == "pago" and info["solicitacao"]["status"] == "pendente"   # continua na fila da equipe


def test_painel_mostra_situacao_do_mercado_pago(client, produtor):
    mp = client.get("/api/v1/dashboard/me", headers=produtor).json()["produtor"]["mercadopago"]
    assert mp["conectado"] is False and "split_disponivel" in mp
