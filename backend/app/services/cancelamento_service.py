"""
Cancelamento de pedidos e devolução do dinheiro.

Quem pode cancelar:
  - Cliente: pelo link do pedido (confirma com os 4 últimos números do WhatsApp da compra).
    Pedido ainda NÃO pago: cancela na hora. Pedido PAGO (ou retirado, dentro dos 7 dias):
    vira um PEDIDO DE CANCELAMENTO, que a equipe analisa. Ela fala com o produtor para saber se
    o produto já foi entregue ou enviado e então aprova (cancela e devolve) ou recusa (com o motivo).
  - Produtor: pelo painel, antes da retirada (ex.: acabou o produto).
  - Equipe (admin): a qualquer momento — é ela quem atende o direito de arrependimento
    depois da retirada (7 dias, Código de Defesa do Consumidor, art. 49).
  - Sistema: quando a moderação rejeita/exclui um produto ou um vendedor é removido,
    os pedidos que ainda não foram pagos são cancelados (ninguém paga por algo que saiu do ar).

Ao cancelar um pedido pago, o valor TOTAL é devolvido pelo Mercado Pago (Pix ou cartão).
- Mercado Pago aprovou a devolução: pedido cancelado, "devolvido".
- Mercado Pago aceitou mas ainda está processando: pedido cancelado, "devolução em andamento";
  as tarefas automáticas acompanham até aprovar (ou marcam "falhou" para a equipe resolver).
- Mercado Pago recusou ou não respondeu: o pedido NÃO é cancelado (nada fica pela metade).
- Pago pelo Pix de reserva: a devolução é feita pela equipe (status "manual").
Depois: o estoque volta e cliente e produtor recebem aviso no WhatsApp.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.order_model import (
    METODOS, PEDIDO_AGUARDANDO, PEDIDO_CANCELADO, PEDIDO_PAGO, PEDIDO_RETIRADO, Order, OrderItem,
)
from app.models.product_model import Product
from app.services import payment_service
from app.services.order_service import _notificar
from app.services.whatsapp_service import texto_seguro

log = logging.getLogger("mercado_nativo")

PRAZO_ARREPENDIMENTO_DIAS = 7
QUEM = {"cliente": "pelo cliente", "produtor": "pelo produtor", "admin": "pela equipe do Mercado Nativo",
        "mercadopago": "pelo Mercado Pago", "sistema": "pelo Mercado Nativo"}
DEVOLUCAO_APROVADA = "approved"
DEVOLUCAO_EM_ANDAMENTO = ("pending", "in_process", "authorized", "in_mediation", "")
DEVOLUCAO_RECUSADA = ("rejected", "cancelled", "canceled")


class CancelamentoError(Exception):
    pass


def prazo_arrependimento(order: Order) -> datetime | None:
    """Até quando o cliente pode desistir depois de retirar (7 dias)."""
    base = order.retirado_em or (order.paid_at if order.status == PEDIDO_RETIRADO else None)
    return base + timedelta(days=PRAZO_ARREPENDIMENTO_DIAS) if base else None


def pode_cancelar(order: Order, quem: str) -> bool:
    """Quem pode cancelar NA HORA (sem passar pela equipe)."""
    if order.status == PEDIDO_CANCELADO:
        return False
    if quem in ("admin", "sistema"):
        return order.status in (PEDIDO_AGUARDANDO, PEDIDO_PAGO, PEDIDO_RETIRADO)
    if quem == "cliente":  # pago: o cliente PEDE o cancelamento e a equipe confere com o produtor
        return order.status == PEDIDO_AGUARDANDO
    return order.status in (PEDIDO_AGUARDANDO, PEDIDO_PAGO)  # produtor: só antes da retirada


def solicitacao_pendente(order: Order) -> bool:
    return order.solicitacao_status == "pendente" and order.status != PEDIDO_CANCELADO


def pode_solicitar(order: Order) -> bool:
    """O cliente pode pedir o cancelamento de um pedido pago, ou retirado dentro dos 7 dias."""
    if solicitacao_pendente(order) or order.solicitacao_status == "recusada":
        return False  # recusado: a conversa continua pelo SAC
    if order.status == PEDIDO_PAGO:
        return True
    prazo = prazo_arrependimento(order)
    return order.status == PEDIDO_RETIRADO and bool(prazo and datetime.utcnow() <= prazo)


def solicitar(db: Session, order: Order, motivo: str | None = None) -> Order:
    """O cliente pede o cancelamento. Nada é devolvido ainda: a equipe confere com o produtor
    se o produto já foi entregue ou enviado e depois aprova ou recusa."""
    if solicitacao_pendente(order):
        raise CancelamentoError("Já recebemos o seu pedido de cancelamento. A equipe vai responder pelo WhatsApp.")
    if not pode_solicitar(order):
        if order.status == PEDIDO_CANCELADO:
            raise CancelamentoError("Este pedido já está cancelado.")
        raise CancelamentoError("O prazo para pedir o cancelamento terminou. Fale com o SAC do Mercado Nativo.")
    order.solicitacao_status = "pendente"
    order.solicitacao_em = datetime.utcnow()
    order.solicitacao_motivo = texto_seguro(motivo, 300) or None
    order.solicitacao_resposta = None
    order.solicitacao_respondida_em = None
    db.commit()
    db.refresh(order)

    itens = ", ".join(f"{i.quantidade}x {i.nome_produto}" for i in order.itens)
    _notificar(
        order.consumidor_whatsapp,
        f"🍃 *Mercado Nativo*\n\nRecebemos o seu pedido de cancelamento do pedido nº {order.id} ({itens}).\n"
        "A nossa equipe vai confirmar com o produtor se o produto ainda não foi entregue e te responde "
        "por aqui. Se for aprovado, o dinheiro volta pela mesma forma de pagamento.",
    )
    if order.producer:
        _notificar(
            order.producer.whatsapp,
            f"🍃 *Mercado Nativo*\n\nO cliente do pedido nº {order.id} ({itens}) pediu para cancelar.\n"
            "A equipe do Mercado Nativo vai falar com você para saber se o produto já foi entregue ou enviado. "
            "Se ainda não entregou, espere a nossa confirmação antes de entregar.",
        )
    return order


def recusar_solicitacao(db: Session, order: Order, resposta: str) -> Order:
    """A equipe recusa o pedido de cancelamento (ex.: o produto já tinha sido entregue)."""
    if not solicitacao_pendente(order):
        raise CancelamentoError("Este pedido não tem um pedido de cancelamento aguardando resposta.")
    order.solicitacao_status = "recusada"
    order.solicitacao_resposta = texto_seguro(resposta, 300) or None
    order.solicitacao_respondida_em = datetime.utcnow()
    db.commit()
    db.refresh(order)
    _notificar(
        order.consumidor_whatsapp,
        f"🍃 *Mercado Nativo*\n\nO seu pedido de cancelamento do pedido nº {order.id} não foi aprovado.\n"
        f"Motivo: {order.solicitacao_resposta or 'não informado'}\n"
        "Se tiver dúvida, fale com o SAC do Mercado Nativo (WhatsApp, telefone ou e-mail no rodapé do site).",
    )
    return order


def _texto_devolucao(order: Order) -> str:
    if order.reembolso_status == "manual":
        return "A equipe do Mercado Nativo devolve o valor pelo Pix em até 2 dias úteis."
    if order.reembolso_status == "pending":
        return "A devolução já foi pedida ao Mercado Pago e está sendo processada."
    if order.metodo == "pix":
        return "O dinheiro volta para a conta que pagou o Pix, normalmente em poucos minutos."
    if order.metodo in ("credit_card", "debit_card"):
        return "O estorno aparece no cartão conforme o prazo do seu banco (no crédito, pode levar até 2 faturas)."
    return "O valor será devolvido pela mesma forma de pagamento."


def _devolver_no_mercadopago(order: Order) -> None:
    try:
        reembolso_id, status = payment_service.reembolsar(
            order.gateway_payment_id, order.producer, bool(order.split_aplicado))
    except payment_service.PaymentError as e:
        raise CancelamentoError(f"Não foi possível devolver o dinheiro agora: {e}")
    if status in DEVOLUCAO_RECUSADA:
        raise CancelamentoError("O Mercado Pago recusou a devolução. O pedido continua pago; fale com a equipe.")
    order.reembolso_id = reembolso_id or None
    # Só "approved" é devolução concluída; qualquer outro status fica "em andamento" até confirmar
    order.reembolso_status = DEVOLUCAO_APROVADA if status == DEVOLUCAO_APROVADA else "pending"


def cancelar(db: Session, order: Order, quem: str, motivo: str | None = None,
             ja_devolvido_no_mp: bool = False) -> Order:
    """Cancela o pedido e devolve o dinheiro. `ja_devolvido_no_mp`: a devolução foi feita fora
    do sistema (ex.: pelo app do Mercado Pago) e só falta atualizar o pedido."""
    if order.status == PEDIDO_CANCELADO:
        raise CancelamentoError("Este pedido já está cancelado.")
    if not pode_cancelar(order, quem) and not ja_devolvido_no_mp:
        raise CancelamentoError("Depois da retirada, a devolução é pedida ao SAC do Mercado Nativo.")

    pago = order.status in (PEDIDO_PAGO, PEDIDO_RETIRADO)
    if not pago:
        if order.gateway == "mercadopago" and order.gateway_payment_id and not ja_devolvido_no_mp:
            try:  # Pix gerado e ainda não pago: invalida o código para ninguém pagar depois
                payment_service.cancelar_pendente(order.gateway_payment_id, order.producer, bool(order.split_aplicado))
            except payment_service.PaymentError as e:
                atual = payment_service.consultar_pagamento(order.gateway_payment_id, order.producer)
                if atual is None or atual.status in ("pending", "in_process", "authorized", "approved"):
                    raise CancelamentoError(f"Não foi possível cancelar o pagamento agora: {e}")
                # recusado/expirado/cancelado: não há o que cancelar no Mercado Pago
        order.reembolso_status = "sem_cobranca"
    elif ja_devolvido_no_mp:
        order.reembolso_status = DEVOLUCAO_APROVADA
    elif order.gateway == "mercadopago" and order.gateway_payment_id:
        _devolver_no_mercadopago(order)
    elif order.gateway == "manual":
        order.reembolso_status = "manual"  # pago no Pix de reserva: a equipe devolve pelo Pix
    else:
        order.reembolso_status = "simulado"  # modo demonstração: não há dinheiro de verdade

    if pago:  # o estoque tinha sido descontado no pagamento: devolve
        for item in order.itens:
            produto = db.get(Product, item.product_id) if item.product_id else None
            if produto:
                produto.estoque = (produto.estoque or 0) + item.quantidade

    if order.solicitacao_status == "pendente":  # cancelado (pela equipe ou pelo produtor): pedido aprovado
        order.solicitacao_status = "aprovada"
        order.solicitacao_respondida_em = datetime.utcnow()
    order.status = PEDIDO_CANCELADO
    order.cancelado_em = datetime.utcnow()
    order.cancelado_por = quem
    order.motivo_cancelamento = texto_seguro(motivo, 300) or None
    db.commit()
    db.refresh(order)

    if pago:
        _avisar(order)
    return order


def cancelar_pendentes(db: Session, *, product_id: int | None = None, producer_id: int | None = None,
                       motivo: str) -> int:
    """Cancela os pedidos ainda NÃO pagos de um produto ou vendedor que saiu da vitrine.
    Chame ANTES de apagar o produto (depois o vínculo do item com o produto some)."""
    q = db.query(Order).filter(Order.status == PEDIDO_AGUARDANDO)
    if product_id is not None:
        q = q.join(OrderItem, OrderItem.order_id == Order.id).filter(OrderItem.product_id == product_id)
    if producer_id is not None:
        q = q.filter(Order.producer_id == producer_id)
    total = 0
    for pedido in q.all():
        try:
            cancelar(db, pedido, "sistema", motivo)
            total += 1
        except CancelamentoError as e:
            # O Mercado Pago não respondeu: o pedido fica pendente, mas o pagamento é bloqueado
            # pela checagem de "produto ainda à venda" e as tarefas automáticas tentam depois.
            log.warning("Pedido %s não pôde ser cancelado agora: %s", pedido.id, e)
    return total


def devolver_pagamento_tardio(db: Session, order: Order) -> None:
    """O Mercado Pago aprovou um pagamento de um pedido que já estava cancelado sem cobrança
    (ex.: o Pix foi pago bem na hora do cancelamento). Devolve o dinheiro na hora."""
    if order.reembolso_status not in (None, "sem_cobranca") or order.reembolso_id:
        return  # já existe devolução para este pedido
    try:
        _devolver_no_mercadopago(order)
    except CancelamentoError as e:
        order.reembolso_status = "falhou"
        log.warning("Pedido %s foi pago depois de cancelado e a devolução falhou: %s", order.id, e)
    db.commit()
    _notificar(order.consumidor_whatsapp,
               f"🍃 *Mercado Nativo*\n\nRecebemos um pagamento do pedido nº {order.id}, que já estava cancelado. "
               f"Pedimos a devolução do valor. {_texto_devolucao(order)}")


def _avisar(order: Order) -> None:
    itens = ", ".join(f"{i.quantidade}x {i.nome_produto}" for i in order.itens)
    total = f"{order.valor_total:.2f}".replace(".", ",")
    motivo = f"\nMotivo: {order.motivo_cancelamento}" if order.motivo_cancelamento else ""
    concluida = order.reembolso_status in (DEVOLUCAO_APROVADA, "simulado")
    _notificar(
        order.consumidor_whatsapp,
        f"🍃 *Mercado Nativo*\n\nSeu pedido nº {order.id} ({itens}) foi cancelado {QUEM.get(order.cancelado_por, '')}.{motivo}\n"
        f"{'Valor devolvido' if concluida else 'Valor a devolver'}: R$ {total}. {_texto_devolucao(order)}",
    )
    if order.producer and order.cancelado_por != "produtor":
        _notificar(
            order.producer.whatsapp,
            f"🍃 *Mercado Nativo*\n\nO pedido nº {order.id} ({itens}, {METODOS.get(order.metodo or '', 'PIX')}) "
            f"foi cancelado {QUEM.get(order.cancelado_por, '')}.{motivo}\n"
            f"{'O valor foi devolvido ao cliente' if concluida else 'A devolução ao cliente está em andamento'} "
            "e o produto voltou para o seu estoque.",
        )


def resumo(order: Order) -> dict:
    """Informações de cancelamento para as telas."""
    prazo = prazo_arrependimento(order)
    return {
        "cancelado_em": order.cancelado_em.isoformat() if order.cancelado_em else None,
        "cancelado_por": order.cancelado_por,
        "motivo_cancelamento": order.motivo_cancelamento,
        "reembolso_status": order.reembolso_status,
        "retirado_em": order.retirado_em.isoformat() if order.retirado_em else None,
        "prazo_arrependimento": prazo.isoformat() if prazo else None,
        "dentro_do_prazo": bool(prazo and datetime.utcnow() <= prazo),
        "pode_solicitar_cancelamento": pode_solicitar(order),
        "solicitacao": {
            "status": order.solicitacao_status,
            "em": order.solicitacao_em.isoformat() if order.solicitacao_em else None,
            "motivo": order.solicitacao_motivo,
            "resposta": order.solicitacao_resposta,
            "respondida_em": order.solicitacao_respondida_em.isoformat() if order.solicitacao_respondida_em else None,
        } if order.solicitacao_status else None,
    }
