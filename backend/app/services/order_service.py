"""Regras executadas quando um pagamento muda de status."""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.order_model import (
    METODOS, PEDIDO_AGUARDANDO, PEDIDO_CANCELADO, PEDIDO_PAGO, Order, PremiumSubscription,
)
from app.models.product_model import Product
from app.services.payment_service import ResultadoPagamento
from app.services.whatsapp_service import enviar_mensagem_openwa


def _notificar(numero: str | None, texto: str) -> None:
    if not numero:
        return
    try:
        asyncio.get_running_loop().create_task(enviar_mensagem_openwa(numero, texto))
    except RuntimeError:
        try:
            asyncio.run(enviar_mensagem_openwa(numero, texto))
        except Exception:
            pass


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


def confirmar_pedido(db: Session, order: Order) -> Order:
    """Marca o pedido como pago e dá baixa automática no estoque (idempotente)."""
    if order.status != PEDIDO_AGUARDANDO:
        return order
    order.status = PEDIDO_PAGO
    order.paid_at = datetime.utcnow()
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
    _notificar(
        order.producer.whatsapp if order.producer else None,
        f"🍃 *Mercado Nativo*\n\nNovo pedido pago ({metodo})!\n{itens}\n"
        f"Cliente: {order.consumidor_nome} ({order.consumidor_whatsapp})\n"
        f"Seu repasse: R$ {repasse}\n\nCombine a retirada com o cliente.",
    )
    # Resumo para o comprador: assim ele não precisa guardar o link do pedido
    total = f"{order.valor_total:.2f}".replace(".", ",")
    produtor = order.producer
    local = f"{produtor.business_name} ({produtor.city or ''}{'/' + produtor.uf if produtor.uf else ''})" if produtor else ""
    _notificar(
        order.consumidor_whatsapp,
        f"🍃 *Mercado Nativo*\n\nOlá, {order.consumidor_nome.split(' ')[0]}! Recebemos o seu pagamento.\n"
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


def aplicar_status(db: Session, alvo: Order | PremiumSubscription, r: ResultadoPagamento) -> None:
    """Atualiza o pedido/assinatura conforme o status retornado pelo Mercado Pago."""
    registrar_resultado(alvo, r)
    db.commit()
    if r.status == "approved":
        if isinstance(alvo, Order):
            confirmar_pedido(db, alvo)
        else:
            confirmar_assinatura(db, alvo)
    elif r.status in ("cancelled", "refunded", "charged_back") and alvo.status == PEDIDO_AGUARDANDO:
        alvo.status = PEDIDO_CANCELADO
        db.commit()
