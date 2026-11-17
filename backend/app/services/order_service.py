"""Regras executadas quando um pagamento muda de status."""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order_model import (
    METODOS, PEDIDO_AGUARDANDO, PEDIDO_CANCELADO, PEDIDO_PAGO, PEDIDO_RETIRADO, Order, PremiumSubscription,
)
from app.models.product_model import Product
from app.services import notificacao_service
from app.services.payment_service import ResultadoPagamento
from app.services.whatsapp_service import texto_seguro

log = logging.getLogger("mercado_nativo")


def _notificar(numero: str | None, texto: str) -> None:
    """Envia o aviso; se o WhatsApp estiver fora do ar, ele fica na fila e é reenviado depois."""
    try:
        notificacao_service.notificar(numero, texto)
    except Exception as e:
        log.warning("Aviso por WhatsApp não enviado: %s", type(e).__name__)


def registrar_resultado(alvo: Order | PremiumSubscription, r: ResultadoPagamento) -> None:
    """Guarda os dados do pagamento (sem dados de cartão)."""
    alvo.gateway = "mercadopago"
    alvo.gateway_payment_id = r.payment_id
    alvo.metodo = r.metodo
    alvo.status_detalhe = r.status_detalhe
    if r.pix_qr_code:
        alvo.pix_qr_code = r.pix_qr_code
        alvo.pix_qr_base64 = r.pix_qr_base64
    if isinstance(alvo, Order):
        alvo.parcelas = r.parcelas
        alvo.split_aplicado = r.split_aplicado
        if r.taxa_mp is not None:
            alvo.taxa_mercadopago = r.taxa_mp
            alvo.taxa_mp_real = True


def fechar_valores(order: Order) -> None:
    """Valor que o produtor recebe = venda - taxa do Mercado Pago - comissão do Mercado Nativo.
    Usa a taxa real do Mercado Pago quando ela veio; senão, a estimativa da tabela."""
    from app.services.payment_service import estimar_taxa_mp

    if order.taxa_mercadopago is None or not order.taxa_mp_real:
        order.taxa_mercadopago = estimar_taxa_mp(order.valor_total, order.metodo, order.gateway)
        order.taxa_mp_real = False
    order.valor_produtor = round(max(0.0, order.valor_total - order.taxa_plataforma - order.taxa_mercadopago), 2)


def confirmar_pedido(db: Session, order: Order) -> Order:
    """Marca o pedido como pago e dá baixa automática no estoque (idempotente)."""
    if order.status != PEDIDO_AGUARDANDO:
        return order
    order.status = PEDIDO_PAGO
    order.paid_at = datetime.utcnow()
    fechar_valores(order)
    for item in order.itens:
        if item.product_id:
            produto = db.get(Product, item.product_id)
            if produto:
                produto.estoque = max(0, (produto.estoque or 0) - item.quantidade)
    db.commit()
    db.refresh(order)

    itens = ", ".join(f"{i.quantidade}x {i.nome_produto}" for i in order.itens)
    metodo = METODOS.get(order.metodo or "", "PIX")
    repasse = f"{order.valor_produtor:.2f}".replace(".", ",")
    # O nome foi digitado pelo comprador: sai sem links nem formatação no número oficial
    cliente = texto_seguro(order.consumidor_nome, 60)
    complemento = ("\nPago pelo Pix de reserva: a equipe faz o seu repasse manualmente."
                   if order.gateway == "manual" else "")
    _notificar(
        order.producer.whatsapp if order.producer else None,
        f"🍃 *Mercado Nativo*\n\nNovo pedido pago ({metodo})!\n{itens}\n"
        f"Cliente: {cliente} ({order.consumidor_whatsapp})\n"
        f"Você recebe: R$ {repasse} (já sem a taxa do Mercado Pago e a comissão){complemento}\n\n"
        "Combine a retirada com o cliente.",
    )
    # Resumo para o comprador: assim ele não precisa guardar o link do pedido
    total = f"{order.valor_total:.2f}".replace(".", ",")
    produtor = order.producer
    local = f"{produtor.business_name} ({produtor.city or ''}{'/' + produtor.uf if produtor.uf else ''})" if produtor else ""
    _notificar(
        order.consumidor_whatsapp,
        f"🍃 *Mercado Nativo*\n\nOlá, {cliente.split(' ')[0]}! Recebemos o seu pagamento.\n"
        f"Pedido nº {order.id}: {itens}\nValor: R$ {total} ({metodo})\n"
        f"Retirada com: {local}\n\n"
        f"Ver o pedido e falar com o produtor: {settings.FRONTEND_URL}/pedido/{order.codigo}",
    )
    return order


def cancelar_pedido(db: Session, order: Order, detalhe: str | None = None) -> None:
    if order.status == PEDIDO_AGUARDANDO:
        order.status = PEDIDO_CANCELADO
        order.status_detalhe = detalhe
        db.commit()


def confirmar_assinatura(db: Session, assinatura: PremiumSubscription) -> PremiumSubscription:
    """Ativa (ou renova) o plano Premium por PREMIUM_DAYS dias."""
    if assinatura.status != PEDIDO_AGUARDANDO:
        return assinatura
    assinatura.status = PEDIDO_PAGO
    assinatura.paid_at = datetime.utcnow()
    produtor = assinatura.producer
    inicio = max(produtor.premium_ate or datetime.utcnow(), datetime.utcnow())
    produtor.premium = True
    produtor.premium_ate = inicio + timedelta(days=settings.PREMIUM_DAYS)
    db.commit()
    db.refresh(assinatura)
    return assinatura


def revogar_assinatura(db: Session, assinatura: PremiumSubscription) -> None:
    """Mensalidade estornada ou contestada (chargeback): tira os dias que ela tinha dado."""
    if assinatura.status != PEDIDO_PAGO:
        return
    assinatura.status = PEDIDO_CANCELADO
    produtor = assinatura.producer
    if produtor and produtor.premium_ate:
        produtor.premium_ate = produtor.premium_ate - timedelta(days=settings.PREMIUM_DAYS)
        if produtor.premium_ate <= datetime.utcnow():
            produtor.premium = False
            produtor.premium_ate = None
            for p in produtor.products:  # sem Premium, sem destaque
                p.destaque = False
    db.commit()
    log.warning("Premium revogado: mensalidade %s foi estornada/contestada.", assinatura.id)


def aplicar_status(db: Session, alvo: Order | PremiumSubscription, r: ResultadoPagamento) -> None:
    """Atualiza o pedido/assinatura conforme o status retornado pelo Mercado Pago."""
    cancelado_antes = alvo.status == PEDIDO_CANCELADO
    registrar_resultado(alvo, r)
    db.commit()
    if r.status == "approved":
        if isinstance(alvo, Order) and cancelado_antes:
            # Pix pago depois que o pedido já tinha sido cancelado: o dinheiro não pode ficar retido
            from app.services.cancelamento_service import devolver_pagamento_tardio
            devolver_pagamento_tardio(db, alvo)
        elif isinstance(alvo, Order):
            confirmar_pedido(db, alvo)
        else:
            confirmar_assinatura(db, alvo)
    elif r.status in ("cancelled", "refunded", "charged_back") and alvo.status == PEDIDO_AGUARDANDO:
        alvo.status = PEDIDO_CANCELADO
        db.commit()
    elif (r.status in ("refunded", "charged_back") and isinstance(alvo, Order)
          and alvo.status in (PEDIDO_PAGO, PEDIDO_RETIRADO)):
        # Devolução feita fora do site (ex.: produtor devolveu pelo app do Mercado Pago):
        # o pedido acompanha, o estoque volta e todos são avisados.
        from app.services.cancelamento_service import cancelar
        cancelar(db, alvo, "mercadopago", "Valor devolvido pelo Mercado Pago", ja_devolvido_no_mp=True)
    elif r.status in ("refunded", "charged_back") and isinstance(alvo, PremiumSubscription):
        revogar_assinatura(db, alvo)
