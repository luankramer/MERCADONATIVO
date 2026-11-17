"""
Calculadora de Custos (Premium).

Cada insumo é informado como foi comprado e quanto foi usado, em kg/g, L/ml, metro/cm ou unidade:
    custo do item = preço pago ÷ quantidade comprada × quantidade usada (convertendo g↔kg, ml↔L, cm↔m)
Custo total = insumos + tempo de trabalho (horas × valor da hora) + outros gastos (gás, energia...).
Preço sugerido = custo por unidade × (1 + margem). Com "incluir_taxas", o preço sobe o suficiente para que,
depois da taxa do Mercado Pago (cartão, o caso mais caro) e da comissão do Mercado Nativo, a margem continue.
"""
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import settings

# unidade -> (grandeza, fator para a unidade base: g, ml, cm, un)
UNIDADES = {
    "kg": ("massa", Decimal(1000)), "g": ("massa", Decimal(1)),
    "L": ("volume", Decimal(1000)), "ml": ("volume", Decimal(1)),
    "m": ("comprimento", Decimal(100)), "cm": ("comprimento", Decimal(1)),
    "un": ("unidade", Decimal(1)),
}


class CalculoError(ValueError):
    pass


def moeda(valor: Decimal | float) -> float:
    """Arredondamento comercial (11,775 -> 11,78)."""
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def custo_item(item) -> Decimal:
    """Quanto o item custou nesta produção."""
    if item.preco_compra is None:  # formato antigo: o valor já vem pronto
        return Decimal(str(item.valor or 0))
    grandeza_c, fator_c = UNIDADES[item.unidade_compra]
    grandeza_u, fator_u = UNIDADES[item.unidade_usada]
    if grandeza_c != grandeza_u:
        raise CalculoError(f"\"{item.descricao}\": a unidade usada ({item.unidade_usada}) não combina com a "
                           f"unidade comprada ({item.unidade_compra}).")
    comprado = Decimal(str(item.qtd_compra)) * fator_c
    usado = Decimal(str(item.qtd_usada)) * fator_u
    return Decimal(str(item.preco_compra)) / comprado * usado


def percentual_taxas_venda() -> Decimal:
    """Comissão do Mercado Nativo + taxa do Mercado Pago no cartão (o caso mais caro), em %."""
    return Decimal(str(settings.PLATFORM_FEE_PERCENT)) + Decimal(str(settings.TAXA_MP_CREDITO))


def calcular(req) -> dict:
    custos = [custo_item(i) for i in req.itens]
    materiais = sum(custos, Decimal(0))
    trabalho = Decimal(str(req.horas_trabalho)) * Decimal(str(req.valor_hora))
    outros = Decimal(str(req.outros_gastos))
    total = materiais + trabalho + outros
    unitario = total / Decimal(req.rendimento)
    preco = unitario * (Decimal(1) + Decimal(str(req.margem)) / Decimal(100))
    taxas = percentual_taxas_venda() if req.incluir_taxas else Decimal(0)
    if taxas >= 100:
        raise CalculoError("As taxas configuradas passam de 100%.")
    preco = preco / (Decimal(1) - taxas / Decimal(100))

    preco_final = Decimal(str(moeda(preco)))
    comissao = preco_final * Decimal(str(settings.PLATFORM_FEE_PERCENT)) / 100

    def recebe(taxa_mp: float) -> float:
        return moeda(preco_final - Decimal(str(moeda(comissao))) - Decimal(str(moeda(preco_final * Decimal(str(taxa_mp)) / 100))))

    return {
        "custo_itens": [moeda(c) for c in custos],
        "custo_materiais": moeda(materiais),
        "custo_trabalho": moeda(trabalho),
        "outros_gastos": moeda(outros),
        "custo_total": moeda(total),
        "custo_unitario": moeda(unitario),
        "preco_sugerido": float(preco_final),
        "recebe_pix": recebe(settings.TAXA_MP_PIX),
        "recebe_cartao": recebe(settings.TAXA_MP_CREDITO),
        "lucro_unitario_cartao": moeda(Decimal(str(recebe(settings.TAXA_MP_CREDITO))) - unitario),
    }
