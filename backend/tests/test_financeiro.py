"""Financeiro: taxas do Mercado Pago, relatório do mês, repasse ao produtor e planilha."""
from datetime import datetime

from app.db.database import SessionLocal
from app.models.order_model import PEDIDO_CANCELADO, PEDIDO_PAGO, PEDIDO_RETIRADO, Order, OrderItem
from app.models.user_model import Producer
from app.services import payment_service
from app.services.order_service import fechar_valores

MES = "2025-03"  # mês antigo: os outros testes não criam pedidos nele


def _pedido(db, produtor_id, valor, metodo, split, status=PEDIDO_RETIRADO, taxa_real=None, dia=15):
    o = Order(producer_id=produtor_id, consumidor_nome="Cliente", consumidor_whatsapp="68999000000",
              valor_total=valor, taxa_plataforma=round(valor * 0.10, 2), valor_produtor=0, status=status,
              gateway="mercadopago", metodo=metodo, split_aplicado=split,
              paid_at=datetime(2025, 3, dia, 15, 0), taxa_mercadopago=taxa_real, taxa_mp_real=taxa_real is not None)
    o.itens.append(OrderItem(nome_produto="Geleia", quantidade=1, preco_unitario=valor))
    fechar_valores(o)
    db.add(o)
    db.commit()
    return o


def test_taxa_real_do_mercado_pago_vem_do_fee_details():
    r = payment_service._resultado({"id": 1, "status": "approved", "payment_type_id": "credit_card",
                                    "fee_details": [{"type": "mercadopago_fee", "amount": 2.49},
                                                    {"type": "application_fee", "amount": 5.0}]}, True)
    assert r.taxa_mp == 2.49
    assert payment_service.estimar_taxa_mp(25.0, "pix") == 0.25
    assert payment_service.estimar_taxa_mp(25.0, "credit_card") == 1.25
    assert payment_service.estimar_taxa_mp(25.0, "pix", gateway="manual") == 0.0  # Pix de reserva


def test_relatorio_do_mes_e_repasse(client, admin, produtor):
    db = SessionLocal()
    loja_id = db.query(Producer).filter(Producer.whatsapp == "68999112233").first().id
    plataforma = _pedido(db, loja_id, 100.0, "pix", split=False)                      # caiu na conta da plataforma
    _pedido(db, loja_id, 50.0, "credit_card", split=True, taxa_real=2.49)              # caiu direto no produtor
    _pedido(db, loja_id, 30.0, "pix", split=False, status=PEDIDO_CANCELADO)           # devolvido: fora da conta
    assert plataforma.valor_produtor == round(100 - 10 - 0.99, 2)
    db.close()

    d = client.get(f"/api/v1/admin/financeiro?mes={MES}", headers=admin).json()
    r = d["resumo"]
    assert r["pedidos"] == 2 and r["vendas"] == 150.0 and r["cancelados"] == 1
    assert r["taxa_mercadopago"] == round(0.99 + 2.49, 2)
    assert r["comissao"] == 15.0
    assert r["a_repassar"] == 89.01
    assert r["entrou_na_plataforma"] == round((100 - 0.99) + 5.0, 2)   # venda sem taxa + comissão do split
    assert r["recebido_direto_pelos_produtores"] == round(50 - 5 - 2.49, 2)
    linha = next(p for p in d["produtores"] if p["producer_id"] == loja_id)
    assert linha["situacao"] == "pendente" and linha["a_repassar"] == 89.01

    csv = client.get(f"/api/v1/admin/financeiro/relatorio.csv?mes={MES}", headers=admin)
    assert csv.status_code == 200 and "attachment" in csv.headers["content-disposition"]
    assert "A repassar aos produtores;89,01" in csv.text and "Conta do Mercado Nativo" in csv.text

    r = client.post("/api/v1/admin/financeiro/repasses", headers=admin,
                    json={"mes": MES, "producer_id": loja_id, "observacao": "Pix enviado"})
    assert r.status_code == 201 and r.json()["valor_repasse"] == 89.01
    # Não dá para pagar duas vezes
    assert client.post("/api/v1/admin/financeiro/repasses", headers=admin,
                       json={"mes": MES, "producer_id": loja_id}).status_code == 400

    d = client.get(f"/api/v1/admin/financeiro?mes={MES}", headers=admin).json()
    linha = next(p for p in d["produtores"] if p["producer_id"] == loja_id)
    assert linha["situacao"] == "pago" and linha["repassado"] == 89.01 and linha["repasses"][0]["observacao"] == "Pix enviado"
    assert d["resumo"]["a_repassar"] == 0


def test_produtor_ve_taxas_e_como_recebe(client, produtor):
    pedidos = client.get("/api/v1/producers/me/orders", headers=produtor).json()
    alvo = next(p for p in pedidos if p["valor_total"] == 100.0)
    assert alvo["recebimento"] == "plataforma" and alvo["taxa_mercadopago"] == 0.99
    assert alvo["valor_produtor"] == 89.01 and alvo["repasse_pago_em"]


def test_mes_invalido_e_acesso(client, admin):
    assert client.get("/api/v1/admin/financeiro?mes=03-2025", headers=admin).status_code == 400
    assert client.get("/api/v1/admin/financeiro").status_code in (401, 403)
