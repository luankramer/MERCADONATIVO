"""
Regressões das falhas apontadas na auditoria de segurança (nov/2026) e das rotas de reserva
(Mercado Pago fora do ar, WhatsApp fora do ar). Tudo sem internet: as APIs são simuladas.
"""
import asyncio
import re
from datetime import datetime, timedelta

import pytest
import requests

from app.core.config import settings
from app.core.crypto import criptografar
from app.db.database import SessionLocal
from app.models.fila_model import MensagemPendente, NotificacaoPagamento
from app.models.order_model import Order, PremiumSubscription
from app.models.user_model import Producer
from app.services import (
    conexao_mp_service, email_service, notificacao_service, order_service, payment_service, tarefas_service,
    whatsapp_service,
)
from tests.conftest import _login_produtor, _pedir_codigo
from tests.test_payment import _modo_real, _produto_aprovado, _Resp

WHATS = "68999990000"


def _novo_produtor(client, whatsapp, email=None):
    r = client.post("/api/v1/auth/producer/register", json={
        "aceite_termos": True, "name": "Teste Silva", "business_name": f"Loja {whatsapp[-4:]}",
        "whatsapp": whatsapp, "city": "Rio Branco", "email": email})
    assert r.status_code == 201, r.text
    return r.json()["id"], _login_produtor(client, whatsapp)


def _pedido(client, pid, qtd=1):
    r = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": qtd, "nome": "Ana Souza", "whatsapp": WHATS})
    assert r.status_code == 201, r.text
    return r.json()


def _db_get(modelo, id_):
    db = SessionLocal()
    try:
        obj = db.get(modelo, id_)
        db.expunge(obj)
        return obj
    finally:
        db.close()


# ============ 1. Modo simulado não liga por engano ============
def test_mercadopago_sem_chave_desativa_em_vez_de_simular(client, produtor, admin, monkeypatch):
    pid = _produto_aprovado(client, produtor, admin, nome="Mel de Abelha Nativa")
    monkeypatch.setattr(settings, "PAYMENT_MODE", "mercadopago")
    monkeypatch.setattr(settings, "MP_ACCESS_TOKEN", "TEST-plataforma")
    monkeypatch.setattr(settings, "MP_PUBLIC_KEY", "")           # falta uma chave
    assert payment_service.modo_pagamento() == "desativado"
    pedido = _pedido(client, pid)
    r = client.post(f"/api/v1/checkout/{pedido['codigo']}/simular", json={"metodo": "credit_card"})
    assert r.status_code == 400
    assert client.get(f"/api/v1/checkout/{pedido['codigo']}").json()["status"] == "aguardando_pagamento"
    # Premium também não pode ser "pago" de graça
    assinatura = client.post("/api/v1/producers/me/premium", headers=produtor).json()
    r = client.post(f"/api/v1/producers/me/premium/{assinatura['codigo']}/simular", headers=produtor,
                    json={"metodo": "credit_card"})
    assert r.status_code == 400


def test_simulado_nunca_vale_em_producao(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_MODE", "simulado")
    monkeypatch.setattr(settings, "APP_ENV", "producao")
    assert payment_service.modo_pagamento() == "desativado"
    monkeypatch.setattr(settings, "PAYMENT_MODE", "mercado_pago")  # erro de digitação
    monkeypatch.setattr(settings, "APP_ENV", "dev")
    assert payment_service.modo_pagamento() == "desativado"
    assert "não existe" in payment_service.aviso_configuracao()


def test_pedido_real_nao_vira_simulado(client, produtor, admin, monkeypatch):
    pid = _produto_aprovado(client, produtor, admin, nome="Castanha Real")
    _modo_real(monkeypatch)
    pedido = _pedido(client, pid)                       # criado com pagamento real
    monkeypatch.setattr(settings, "PAYMENT_MODE", "simulado")  # alguém volta para o simulado
    r = client.post(f"/api/v1/checkout/{pedido['codigo']}/simular", json={"metodo": "credit_card"})
    assert r.status_code == 400 and "real" in r.json()["detail"]


# ============ 2. Link do Mercado Pago perde o valor ============
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


def _link_token(mensagens):
    return re.search(r"/api/v1/mercadopago/conectar/(\S+)", mensagens[-1][1]).group(1)


def test_link_mp_nao_vale_depois_de_trocar_whatsapp(client, split_ligado):
    _, h = _novo_produtor(client, "68911110001")
    assert client.post("/api/v1/producers/me/mercadopago/enviar-link", headers=h).status_code == 200
    token = _link_token(split_ligado)
    # troca o número (com o código do número novo)
    assert client.post("/api/v1/producers/me/whatsapp/codigo", headers=h, json={"whatsapp": "68911110002"}).status_code == 200
    from app.api.v1.producers import troca_whatsapp
    pid = next(iter(k for k, v in troca_whatsapp.items() if v["numero"] == "68911110002"))
    code = troca_whatsapp[pid]["code"]
    assert client.post("/api/v1/producers/me/whatsapp/confirmar", headers=h,
                       json={"whatsapp": "68911110002", "code": code}).status_code == 200
    r = client.get(f"/api/v1/mercadopago/conectar/{token}", follow_redirects=False)
    assert r.status_code == 400 and "Link vencido" in r.text


def test_link_mp_nao_vale_depois_de_excluir_conta(client, split_ligado):
    _, h = _novo_produtor(client, "68911110003")
    client.post("/api/v1/producers/me/mercadopago/enviar-link", headers=h)
    token = _link_token(split_ligado)
    assert client.delete("/api/v1/producers/me", headers=h).status_code == 200
    r = client.get(f"/api/v1/mercadopago/conectar/{token}", follow_redirects=False)
    assert r.status_code == 400


# ============ 3. Trocar o WhatsApp exige código no número novo ============
def test_troca_de_whatsapp_exige_codigo_e_encerra_sessoes(client):
    pid, h = _novo_produtor(client, "68911110004")
    r = client.put("/api/v1/producers/me", headers=h, data={"whatsapp": "68911110005"})
    assert r.status_code == 400                                     # direto pelo perfil, não
    r = client.put("/api/v1/producers/me", headers=h, data={"whatsapp": "(68) 9 1111-0004", "nome": "Teste Novo"})
    assert r.status_code == 200                                     # mesmo número: segue normal

    client.post("/api/v1/producers/me/whatsapp/codigo", headers=h, json={"whatsapp": "68911110005"})
    from app.api.v1.producers import troca_whatsapp
    code = troca_whatsapp[pid]["code"]
    assert client.post("/api/v1/producers/me/whatsapp/confirmar", headers=h,
                       json={"whatsapp": "68911110005", "code": "999999" if code != "999999" else "111111"}).status_code == 400
    r = client.post("/api/v1/producers/me/whatsapp/confirmar", headers=h, json={"whatsapp": "68911110005", "code": code})
    assert r.status_code == 200
    novo = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/v1/producers/me", headers=h).status_code == 401      # sessão antiga caiu
    assert client.get("/api/v1/producers/me", headers=novo).json()["whatsapp"] == "68911110005"
    assert client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "68911110004"}).status_code == 404


# ============ 4. Reembolso só conta como devolvido quando o Mercado Pago aprova ============
def _pedido_pago_real(client, produtor, admin, monkeypatch, nome, resposta_reembolso):
    _modo_real(monkeypatch)
    pid = _produto_aprovado(client, produtor, admin, nome=nome)

    def post(url, json=None, headers=None, timeout=None):
        if url.endswith("/refunds"):
            return resposta_reembolso
        return _Resp(201, {"id": abs(hash(nome)) % 10**8, "status": "approved", "payment_type_id": "credit_card",
                           "installments": 1})
    monkeypatch.setattr(payment_service.requests, "post", post)
    pedido = _pedido(client, pid)
    r = client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar", json={
        "payment_method_id": "master", "token": "tok", "installments": 1, "payer": {"email": "a@teste.com"}})
    assert r.json()["status"] == "pago", r.text
    return pedido


def test_reembolso_recusado_mantem_pedido_pago(client, produtor, admin, monkeypatch):
    pedido = _pedido_pago_real(client, produtor, admin, monkeypatch, "Açaí Recusa", _Resp(201, {"id": 1, "status": "rejected"}))
    r = client.post(f"/api/v1/admin/orders/{pedido['numero']}/cancelar", headers=admin, json={"motivo": "Pedido do cliente"})
    assert r.status_code == 400
    assert client.get(f"/api/v1/checkout/{pedido['codigo']}").json()["status"] == "pago"


def test_reembolso_sem_status_fica_em_andamento_e_e_acompanhado(client, produtor, admin, monkeypatch):
    pedido = _pedido_pago_real(client, produtor, admin, monkeypatch, "Açaí Andamento", _Resp(201, {"id": 4321}))
    r = client.post(f"/api/v1/admin/orders/{pedido['numero']}/cancelar", headers=admin, json={"motivo": "Pedido do cliente"})
    assert r.status_code == 200 and r.json()["reembolso_status"] == "pending"     # nada de "approved" por padrão
    monkeypatch.setattr(payment_service.requests, "get", lambda url, **k: _Resp(200, {"id": 4321, "status": "approved"}))
    tarefas_service.executar_ciclo()
    assert client.get(f"/api/v1/checkout/{pedido['codigo']}").json()["reembolso_status"] == "approved"


# ============ 5. Produto rejeitado/excluído não pode mais ser pago ============
def test_rejeitar_produto_cancela_pedidos_pendentes(client, produtor, admin):
    pid = _produto_aprovado(client, produtor, admin, nome="Farinha Moderada")
    pedido = _pedido(client, pid)
    assert client.post(f"/api/v1/admin/products/{pid}/rejeitar", headers=admin, json={"motivo": "foto ruim"}).status_code == 200
    assert client.get(f"/api/v1/checkout/{pedido['codigo']}").json()["status"] == "cancelado"
    assert client.post(f"/api/v1/checkout/{pedido['codigo']}/simular", json={"metodo": "credit_card"}).status_code == 400


def test_excluir_produto_cancela_pedidos_pendentes(client, produtor, admin):
    pid = _produto_aprovado(client, produtor, admin, nome="Doce Excluído")
    pedido = _pedido(client, pid)
    assert client.delete(f"/api/v1/admin/products/{pid}", headers=admin).status_code == 200
    final = client.get(f"/api/v1/checkout/{pedido['codigo']}").json()
    assert final["status"] == "cancelado" and final["reembolso_status"] == "sem_cobranca"


# ============ 6 e 7. Código de login: não dá para adivinhar nem atrapalhar o produtor ============
def test_pedidos_de_outra_pessoa_nao_apagam_o_codigo_do_produtor(client, produtor, monkeypatch):
    import app.api.v1.auth as auth
    desafio, code = _pedir_codigo(client, "68999112233")                # o produtor pede
    monkeypatch.setattr(auth, "ip_cliente", lambda request: "203.0.113.9")  # outra pessoa, outro IP
    for _ in range(3):
        d2 = client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "68999112233"}).json()["desafio"]
    for _ in range(5):
        client.post("/api/v1/auth/producer/verify-code", json={"whatsapp": "68999112233", "code": "000000", "desafio": d2})
    monkeypatch.undo()
    r = client.post("/api/v1/auth/producer/verify-code", json={"whatsapp": "68999112233", "code": code, "desafio": desafio})
    assert r.status_code == 200                                     # o código dele continua valendo


def test_erros_somados_bloqueiam_tentativas_por_24h(client, produtor):
    from app.core.rate_limit import registrar
    for _ in range(30):
        registrar("otp-falhas:68999112233", 30, 86400)
    r = client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "68999112233"})
    assert r.status_code == 429


def test_errar_conta_no_total_do_numero(client, produtor):
    from app.core import rate_limit
    desafio, _ = _pedir_codigo(client, "68999112233")
    client.post("/api/v1/auth/producer/verify-code", json={"whatsapp": "68999112233", "code": "123", "desafio": desafio})
    assert len(rate_limit._eventos["otp-falhas:68999112233"]) == 1


# ============ 8 e 9. Busca pública ============
def test_busca_publica_nunca_chama_o_nominatim(client, monkeypatch):
    from app.services import geo_service
    chamadas = []
    monkeypatch.setattr(geo_service.requests, "get", lambda *a, **k: chamadas.append(a) or _Resp(200, []))
    for i in range(5):
        assert client.get("/api/v1/public/products", params={"cidade": f"Inexistente{i}"}).status_code == 200
    assert chamadas == []


def test_nominatim_tem_cache(monkeypatch):
    from app.services import geo_service
    chamadas = []
    monkeypatch.setattr(geo_service.requests, "get",
                        lambda *a, **k: chamadas.append(1) or _Resp(200, [{"lat": "-1", "lon": "-2"}]))
    geo_service._ultima_consulta[0] = 0.0
    assert geo_service.coordenadas("Cidade Nova Teste", "PA") == (-1.0, -2.0)
    assert geo_service.coordenadas("cidade nova teste", "PA") == (-1.0, -2.0)
    assert len(chamadas) == 1


def test_busca_limita_tamanho_e_termos(client):
    from app.services.busca_service import termos_da_busca
    assert client.get("/api/v1/public/products", params={"q": "r " * 60}).status_code == 422
    assert len(termos_da_busca(" ".join(f"palavra{i}" for i in range(50)))) == 8
    assert termos_da_busca("mel mel mel") == ["mel"]


# ============ 10. Número absurdo não vira chave na memória ============
def test_numero_gigante_e_rejeitado_antes_do_limitador(client):
    from app.core import rate_limit
    assert client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "6" * 5000}).status_code == 422
    assert client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "6" * 15}).status_code == 400
    assert not any("6" * 15 in k for k in rate_limit._eventos)


def test_limitador_apaga_chaves_vencidas():
    from app.core import rate_limit
    rate_limit._eventos["velha"].append(0.0)
    rate_limit._limpar_expiradas(rate_limit.JANELA_MAXIMA + 10)
    assert "velha" not in rate_limit._eventos


# ============ Outras correções ============
def test_premium_revogado_em_chargeback(client):
    pid, _ = _novo_produtor(client, "68911110006")
    db = SessionLocal()
    try:
        a = PremiumSubscription(producer_id=pid, valor=9.9, gateway="mercadopago", gateway_payment_id="pm-1")
        db.add(a)
        db.commit()
        order_service.confirmar_assinatura(db, a)
        assert db.get(Producer, pid).is_premium
        order_service.aplicar_status(db, a, payment_service.ResultadoPagamento(
            status="charged_back", status_detalhe=None, payment_id="pm-1", metodo="credit_card"))
        assert db.get(Producer, pid).is_premium is False
    finally:
        db.close()


def test_pagamento_aprovado_depois_de_cancelado_e_devolvido(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    pid = _produto_aprovado(client, produtor, admin, nome="Pix Tardio")
    reembolsos = []
    monkeypatch.setattr(payment_service.requests, "post", lambda url, **k: (
        reembolsos.append(url) or _Resp(201, {"id": 9, "status": "approved"})) if url.endswith("/refunds") else
        _Resp(201, {"id": 7001, "status": "pending", "payment_type_id": "bank_transfer",
                    "point_of_interaction": {"transaction_data": {"qr_code": "000201PIX"}}}))
    monkeypatch.setattr(payment_service.requests, "put", lambda url, **k: _Resp(200, {"status": "cancelled"}))
    pedido = _pedido(client, pid)
    client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar", json={"payment_method_id": "pix", "payer": {"email": "a@t.com"}})
    assert client.post(f"/api/v1/checkout/{pedido['codigo']}/cancelar", json={"whatsapp_final": WHATS[-4:]}).status_code == 200
    # o banco confirma o Pix depois do cancelamento
    monkeypatch.setattr(payment_service.requests, "get", lambda url, **k: _Resp(200, {
        "id": 7001, "status": "approved", "payment_type_id": "bank_transfer"}))
    client.post("/api/v1/checkout/webhook/mercadopago?data.id=7001&type=payment", json={"type": "payment"})
    assert reembolsos and reembolsos[-1].endswith("/v1/payments/7001/refunds")
    assert client.get(f"/api/v1/checkout/{pedido['codigo']}").json()["status"] == "cancelado"


def test_token_com_caractere_estranho_da_401():
    from app.core.security import TokenInvalido, decode_token
    with pytest.raises(TokenInvalido):
        decode_token("abc.def.ção")


def test_nome_do_comprador_sem_links_nas_mensagens(client, produtor, admin):
    pid = _produto_aprovado(client, produtor, admin, nome="Queijo Coalho Link")
    r = client.post("/api/v1/checkout", json={"product_id": pid, "quantidade": 1,
                                             "nome": "*Ganhe* um premio em http://golpe.com", "whatsapp": WHATS})
    pedido = _db_get(Order, r.json()["numero"])
    assert "http" not in pedido.consumidor_nome and "*" not in pedido.consumidor_nome


# ============ Reserva: Mercado Pago fora do ar ============
def _mp_fora(monkeypatch):
    def cai(*a, **k):
        raise requests.ConnectionError("sem internet")
    for m in ("post", "get", "put"):
        monkeypatch.setattr(payment_service.requests, m, cai)


def test_mp_fora_do_ar_responde_rapido_e_oferece_pix_reserva(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    monkeypatch.setattr(settings, "PIX_RESERVA_CHAVE", "financeiro@mercadonativo.com.br")
    pid = _produto_aprovado(client, produtor, admin, nome="Polpa Reserva")
    pedido = _pedido(client, pid)
    _mp_fora(monkeypatch)
    for _ in range(settings.MP_FALHAS_PARA_PAUSAR):
        r = client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar",
                        json={"payment_method_id": "pix", "payer": {"email": "a@t.com"}})
        assert r.status_code == 503 and "nada foi cobrado" in r.json()["detail"]
    assert payment_service.mp_disponivel() is False
    estado = client.get(f"/api/v1/checkout/{pedido['codigo']}").json()
    assert estado["mp_disponivel"] is False and estado["pix_reserva"] is True

    r = client.post(f"/api/v1/checkout/{pedido['codigo']}/pix-reserva")
    assert r.status_code == 200, r.text
    codigo_pix = r.json()["pix_qr_code"]
    assert codigo_pix.startswith("000201") and "financeiro@mercadonativo.com.br" in codigo_pix
    assert payment_service._crc16(codigo_pix[:-4]) == codigo_pix[-4:]   # código Pix válido
    assert client.post(f"/api/v1/checkout/{pedido['codigo']}/pix-reserva/paguei").json()["reserva_informado"] is True

    # o cliente não consegue se confirmar; a equipe confere e confirma
    assert client.post(f"/api/v1/checkout/{pedido['codigo']}/simular", json={"metodo": "pix"}).status_code == 400
    lista = client.get("/api/v1/admin/orders", headers=admin, params={"status": "aguardando_pagamento"}).json()
    linha = next(p for p in lista if p["codigo"] == pedido["codigo"])
    assert linha["pix_reserva"] and linha["reserva_informado_em"]
    r = client.post(f"/api/v1/admin/orders/{linha['id']}/confirmar-pix-reserva", headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "pago"
    # cancelar depois: a devolução fica com a equipe (Pix manual)
    r = client.post(f"/api/v1/admin/orders/{linha['id']}/cancelar", headers=admin, json={"motivo": "Pedido do cliente"})
    assert r.json()["reembolso_status"] == "manual"


def test_pix_reserva_so_aparece_com_mp_fora(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    monkeypatch.setattr(settings, "PIX_RESERVA_CHAVE", "financeiro@mercadonativo.com.br")
    pid = _produto_aprovado(client, produtor, admin, nome="Polpa Normal")
    pedido = _pedido(client, pid)
    assert pedido["pix_reserva"] is False
    assert client.post(f"/api/v1/checkout/{pedido['codigo']}/pix-reserva").status_code == 400


def test_webhook_com_mp_fora_fica_na_fila_e_e_processado_depois(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    pid = _produto_aprovado(client, produtor, admin, nome="Pix da Fila")
    monkeypatch.setattr(payment_service.requests, "post", lambda url, **k: _Resp(201, {
        "id": 8001, "status": "pending", "payment_type_id": "bank_transfer",
        "point_of_interaction": {"transaction_data": {"qr_code": "000201PIX"}}}))
    pedido = _pedido(client, pid)
    client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar", json={"payment_method_id": "pix", "payer": {"email": "a@t.com"}})

    _mp_fora(monkeypatch)
    r = client.post("/api/v1/checkout/webhook/mercadopago?data.id=8001&type=payment", json={"type": "payment"})
    assert r.status_code == 200
    db = SessionLocal()
    assert db.query(NotificacaoPagamento).filter_by(payment_id="8001", processada_em=None).count() == 1
    n = db.query(NotificacaoPagamento).filter_by(payment_id="8001").first()
    n.proxima_tentativa = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    db.close()

    payment_service.resetar_circuito()                 # o Mercado Pago voltou
    monkeypatch.setattr(payment_service.requests, "get", lambda url, **k: _Resp(200, {
        "id": 8001, "status": "approved", "payment_type_id": "bank_transfer"}))
    tarefas_service.executar_ciclo()
    assert client.get(f"/api/v1/checkout/{pedido['codigo']}").json()["status"] == "pago"


def test_cobranca_com_resposta_perdida_e_recuperada(client, produtor, admin, monkeypatch):
    _modo_real(monkeypatch)
    pid = _produto_aprovado(client, produtor, admin, nome="Resposta Perdida")
    pedido = _pedido(client, pid)
    _mp_fora(monkeypatch)                              # a cobrança chegou, mas a resposta se perdeu
    assert client.post(f"/api/v1/checkout/{pedido['codigo']}/pagar", json={
        "payment_method_id": "master", "token": "t", "payer": {"email": "a@t.com"}}).status_code == 503

    payment_service.resetar_circuito()

    def get(url, **k):
        if "/v1/payments/search" in url:
            assert f"external_reference={pedido['codigo']}" in url
            return _Resp(200, {"results": [{"id": 9901, "status": "approved", "payment_type_id": "credit_card",
                                            "external_reference": pedido["codigo"]}]})
        return _Resp(200, {"id": 9901, "status": "approved", "payment_type_id": "credit_card"})
    monkeypatch.setattr(payment_service.requests, "get", get)
    tarefas_service.executar_ciclo()
    assert client.get(f"/api/v1/checkout/{pedido['codigo']}").json()["status"] == "pago"


def test_crc_do_pix_segue_o_padrao():
    assert payment_service._crc16("123456789") == "29B1"   # CRC-16/CCITT-FALSE (padrão do BR Code)


# ============ Reserva: WhatsApp fora do ar ============
def test_whatsapp_usa_a_meta_quando_a_evolution_falha(monkeypatch):
    monkeypatch.setattr(settings, "EVOLUTION_BASE_URL", "http://evolution")
    monkeypatch.setattr(settings, "EVOLUTION_TOKEN", "x")
    monkeypatch.setattr(settings, "META_WA_TOKEN", "meta")
    monkeypatch.setattr(settings, "META_WA_PHONE_ID", "123")
    usados = []

    async def evolution(numero, texto):
        usados.append("evolution")
        return False

    async def meta(numero, corpo):
        usados.append("meta")
        return True
    monkeypatch.setattr(whatsapp_service, "_enviar_evolution", evolution)
    monkeypatch.setattr(whatsapp_service, "_enviar_meta", meta)
    assert asyncio.run(whatsapp_service.enviar_mensagem_openwa("68999112233", "oi")) is True
    assert usados == ["evolution", "meta"]


def test_aviso_que_nao_saiu_vai_para_a_fila_e_e_reenviado(monkeypatch):
    monkeypatch.setattr(settings, "EVOLUTION_BASE_URL", "http://evolution")
    monkeypatch.setattr(settings, "EVOLUTION_TOKEN", "x")
    resultado = {"ok": False}

    async def envio(numero, texto):
        return resultado["ok"]
    monkeypatch.setattr(notificacao_service, "enviar_mensagem_openwa", envio)
    assert notificacao_service.notificar("68999112233", "Pedido pago!") is False
    db = SessionLocal()
    m = db.query(MensagemPendente).filter_by(texto="Pedido pago!").first()
    assert m and m.enviada_em is None
    m.proxima_tentativa = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    resultado["ok"] = True                              # o WhatsApp voltou
    assert notificacao_service.reenviar_pendentes(db) >= 1
    db.refresh(m)
    assert m.enviada_em is not None
    db.close()


def test_codigo_de_login_vai_por_email_se_o_whatsapp_cair(client, monkeypatch):
    _novo_produtor(client, "68911110007", email="dona.maria@exemplo.com")
    enviados = []
    monkeypatch.setattr(email_service, "email_configurado", lambda: True)
    monkeypatch.setattr(email_service, "enviar_email", lambda para, assunto, texto: enviados.append((para, texto)) or True)
    r = client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "68911110007"})
    assert r.status_code == 200 and r.json()["canal"] == "email"
    assert "do********@exemplo.com" in r.json()["message"] and "dona.maria" not in r.json()["message"]
    from app.api.v1.auth import otp_storage
    code = otp_storage[r.json()["desafio"]]["code"]
    assert enviados[-1][0] == "dona.maria@exemplo.com" and code in enviados[-1][1]


def test_situacao_dos_servicos_no_painel(client, admin):
    r = client.get("/api/v1/admin/status-servicos", headers=admin)
    assert r.status_code == 200 and "mercado_pago_respondendo" in r.json()
