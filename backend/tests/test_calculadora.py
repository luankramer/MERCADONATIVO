"""Calculadora de Custos: compra em kg, g, L, ml, metro, cm ou unidade, tempo de trabalho e taxas da venda."""
from datetime import datetime, timedelta

import pytest

from app.db.database import SessionLocal
from app.models.user_model import Producer
from app.schemas.cost import CostRequest
from app.services import calculadora_service as calc


def _req(**kw):
    base = {"nome": "Geleia de goiaba", "rendimento": 10, "margem": 50, "itens": []}
    return CostRequest(**{**base, **kw})


def _item(descricao, preco, qtd_c, un_c, qtd_u, un_u):
    return {"descricao": descricao, "preco_compra": preco, "qtd_compra": qtd_c, "unidade_compra": un_c,
            "qtd_usada": qtd_u, "unidade_usada": un_u}


def test_converte_kg_g_unidade_e_metro():
    r = calc.calcular(_req(itens=[
        _item("Açúcar", 5.50, 1, "kg", 2, "kg"),          # 2 kg  -> 11,00
        _item("Polpa de goiaba", 12, 1, "kg", 1500, "g"),  # 1,5 kg -> 18,00
        _item("Pote de vidro", 30, 12, "un", 10, "un"),    # 10 potes -> 25,00
        _item("Linha de crochê", 18, 500, "m", 120, "m"),  # 120 m -> 4,32
        _item("Fita", 2, 1, "m", 50, "cm"),                # 50 cm -> 1,00
        _item("Óleo", 9, 900, "ml", 0.45, "L"),            # 450 ml -> 4,50
    ]))
    assert r["custo_itens"] == [11.0, 18.0, 25.0, 4.32, 1.0, 4.5]
    assert r["custo_total"] == 63.82 and r["custo_unitario"] == 6.38
    assert r["preco_sugerido"] == 9.57                      # 6,382 × 1,5


def test_tempo_de_trabalho_outros_gastos_e_taxas_da_venda():
    r = calc.calcular(_req(rendimento=4, margem=0, horas_trabalho=2, valor_hora=10, outros_gastos=6,
                           itens=[_item("Barbante", 20, 1, "un", 1, "un")]))
    assert (r["custo_materiais"], r["custo_trabalho"], r["outros_gastos"], r["custo_total"]) == (20, 20, 6, 46)
    assert r["custo_unitario"] == 11.5 and r["preco_sugerido"] == 11.5

    com_taxas = calc.calcular(_req(rendimento=4, margem=0, horas_trabalho=2, valor_hora=10, outros_gastos=6,
                                   incluir_taxas=True, itens=[_item("Barbante", 20, 1, "un", 1, "un")]))
    # Com o preço ajustado, depois da comissão (10%) e da taxa do cartão (4,98%) sobra o custo
    assert com_taxas["preco_sugerido"] == 13.53
    assert com_taxas["recebe_cartao"] >= 11.49 and com_taxas["recebe_pix"] > com_taxas["recebe_cartao"]


def test_unidades_que_nao_combinam_e_item_incompleto():
    with pytest.raises(calc.CalculoError):
        calc.calcular(_req(itens=[_item("Açúcar", 5, 1, "kg", 2, "un")]))
    with pytest.raises(ValueError):
        _req(itens=[{"descricao": "Açúcar", "preco_compra": 5, "qtd_compra": 1}])


def test_api_salva_e_devolve_o_historico(client, produtor):
    db = SessionLocal()
    p = db.query(Producer).filter(Producer.whatsapp == "68999112233").first()
    p.premium, p.premium_ate = True, datetime.utcnow() + timedelta(days=30)
    db.commit()
    try:
        _testar_api(client, produtor)
    finally:  # os outros testes esperam o produtor sem Premium
        p.premium, p.premium_ate = False, None
        db.commit()
        db.close()


def _testar_api(client, produtor):
    corpo = {"nome": "Tapete de crochê", "rendimento": 1, "margem": 100, "horas_trabalho": 6, "valor_hora": 8,
             "incluir_taxas": True, "itens": [_item("Barbante", 18, 500, "m", 300, "m")]}
    r = client.post("/api/v1/calculadora/calcular", headers=produtor, json=corpo)
    assert r.status_code == 200, r.text
    assert r.json()["custo_total"] == round(18 / 500 * 300 + 48, 2)
    errado = {**corpo, "itens": [_item("Barbante", 18, 500, "m", 2, "kg")]}
    assert client.post("/api/v1/calculadora/calcular", headers=produtor, json=errado).status_code == 400
    hist = client.get("/api/v1/calculadora/historico", headers=produtor).json()
    assert hist[0]["nome"] == "Tapete de crochê" and hist[0]["horas_trabalho"] == 6
    assert hist[0]["itens"][0]["unidade_usada"] == "m" and hist[0]["itens"][0]["custo"] == 10.8
    assert client.get("/api/v1/calculadora/config", headers=produtor).json()["comissao"] == 10
