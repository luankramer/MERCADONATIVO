"""Funções compartilhadas entre o checkout da vitrine e a assinatura Premium."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.order_model import PEDIDO_AGUARDANDO, Order, PremiumSubscription
from app.models.product_model import STATUS_APROVADO, Product
from app.schemas.order import PagamentoBrick, PagamentoSimulado
from app.services import payment_service
from app.services.order_service import aplicar_status, confirmar_assinatura, confirmar_pedido

PIX_DEMO = ("00020126580014BR.GOV.BCB.PIX0136mercado-nativo-demonstracao5204000053039865802BR"
            "5914MERCADO NATIVO6010RIO BRANCO62070503***6304DEMO")
FORA_DO_AR = ("O Mercado Pago está fora do ar agora e nada foi cobrado. Tente de novo em alguns minutos"
              " ou use o Pix de reserva, se aparecer abaixo.")


def exigir_aguardando(alvo) -> None:
    if alvo.status != PEDIDO_AGUARDANDO:
        raise HTTPException(400, "Este pagamento já foi concluído ou cancelado.")


def exigir_vendavel(db: Session, pedido: Order) -> None:
    """O produto ainda está à venda? (a moderação pode ter rejeitado/excluído depois do pedido)"""
    item = pedido.itens[0] if pedido.itens else None
    produto = db.get(Product, item.product_id) if item and item.product_id else None
    vendedor = pedido.producer
    if not produto or produto.status != STATUS_APROVADO or not vendedor or vendedor.ativo is False:
        raise HTTPException(400, "Este produto não está mais disponível. Nenhum valor foi cobrado.")
    if (produto.estoque or 0) < item.quantidade:
        raise HTTPException(400, "O estoque acabou antes do pagamento. Nenhum valor foi cobrado.")


def _encerrar_tentativa_anterior(db: Session, alvo: Order | PremiumSubscription, producer) -> None:
    """Antes de criar uma cobrança nova, cancela a anterior que ainda está em aberto (ex.: um Pix
    gerado e não pago). Assim não sobra um Pix pagável que o sistema não acompanha mais."""
    # Só um Pix gerado fica "em aberto"; cartão recusado/aprovado já está encerrado no Mercado Pago
    if alvo.gateway != "mercadopago" or not alvo.gateway_payment_id or alvo.metodo != "pix" or not alvo.pix_qr_code:
        return
    split = bool(getattr(alvo, "split_aplicado", False))
    try:
        payment_service.cancelar_pendente(alvo.gateway_payment_id, producer, split)
        return
    except payment_service.PaymentError:
        pass
    atual = payment_service.consultar_pagamento(alvo.gateway_payment_id, producer)
    if atual and atual.status == "approved":
        aplicar_status(db, alvo, atual)
        raise HTTPException(409, "Este pagamento já foi aprovado. Atualize a página.")
    if atual is None or atual.status in ("pending", "in_process", "authorized"):
        raise HTTPException(409, "Já existe um pagamento em andamento. Pague o Pix gerado ou tente em alguns minutos.")


def pagar_com_brick(db: Session, alvo: Order | PremiumSubscription, dados: PagamentoBrick, *,
                    valor: float, descricao: str, producer=None, cobrar_comissao=True) -> None:
    exigir_aguardando(alvo)
    if payment_service.modo_pagamento() != "mercadopago":
        raise HTTPException(400, "Os pagamentos com cartão e Pix automático estão desativados no momento.")
    if alvo.gateway == "manual":
        raise HTTPException(400, "Este pedido está sendo pago pelo Pix de reserva.")
    _encerrar_tentativa_anterior(db, alvo, producer)
    if isinstance(alvo, Order):
        # Se a resposta do Mercado Pago se perder, as tarefas automáticas acham o pagamento pelo código
        alvo.pagamento_iniciado_em = datetime.utcnow()
        alvo.gateway = "mercadopago"
        db.commit()
    try:
        resultado = payment_service.criar_pagamento(
            dados.model_dump(), valor=valor, descricao=descricao, referencia=alvo.codigo,
            producer=producer, cobrar_comissao=cobrar_comissao,
        )
    except payment_service.MPIndisponivel:
        raise HTTPException(503, FORA_DO_AR)
    except payment_service.PaymentError as e:
        raise HTTPException(400, str(e))
    aplicar_status(db, alvo, resultado)
    if resultado.status == "rejected":
        raise HTTPException(402, mensagem_recusa(resultado.status_detalhe))


def _exigir_simulacao(alvo) -> None:
    # Só pedidos criados no modo demonstração, e só enquanto ele estiver ligado de propósito
    if payment_service.modo_pagamento() != "simulado" or alvo.gateway != "simulado":
        raise HTTPException(400, "Simulação desativada: este pagamento é real.")


def pagar_simulado(db: Session, alvo: Order | PremiumSubscription, dados: PagamentoSimulado) -> None:
    _exigir_simulacao(alvo)
    exigir_aguardando(alvo)
    alvo.metodo = dados.metodo
    if isinstance(alvo, Order):
        alvo.parcelas = dados.parcelas if dados.metodo == "credit_card" else 1
        alvo.split_aplicado = True
    if dados.metodo == "pix":
        alvo.pix_qr_code = PIX_DEMO
        db.commit()
        return
    db.commit()
    confirmar_pedido(db, alvo) if isinstance(alvo, Order) else confirmar_assinatura(db, alvo)


def confirmar_pix_simulado(db: Session, alvo: Order | PremiumSubscription) -> None:
    _exigir_simulacao(alvo)
    if alvo.metodo != "pix":
        raise HTTPException(400, "Não há PIX de demonstração para confirmar.")
    exigir_aguardando(alvo)
    confirmar_pedido(db, alvo) if isinstance(alvo, Order) else confirmar_assinatura(db, alvo)


def sincronizar(db: Session, alvo: Order | PremiumSubscription, producer=None) -> None:
    """Consulta o Mercado Pago quando o pagamento ainda está pendente (ex.: PIX).
    Se o Mercado Pago não responder, a tela mostra o último status conhecido (não trava)."""
    if alvo.status == PEDIDO_AGUARDANDO and alvo.gateway == "mercadopago" and alvo.gateway_payment_id:
        if not payment_service.mp_disponivel():
            return
        resultado = payment_service.consultar_pagamento(alvo.gateway_payment_id, producer)
        if resultado:
            aplicar_status(db, alvo, resultado)


# ---------------- Pix de reserva ----------------
def escolher_pix_reserva(db: Session, pedido: Order) -> None:
    """O Mercado Pago está fora: gera um Pix Copia e Cola da conta da plataforma com o valor exato.
    A equipe confere o recebimento no painel e confirma o pedido."""
    exigir_aguardando(pedido)
    if pedido.gateway != "manual":
        if not payment_service.oferecer_pix_reserva():
            raise HTTPException(400, "O Pix de reserva só é usado quando o Mercado Pago está fora do ar.")
        if pedido.gateway == "mercadopago" and pedido.gateway_payment_id:
            raise HTTPException(409, "Já existe um pagamento em andamento no Mercado Pago para este pedido.")
    pedido.gateway = "manual"
    pedido.metodo = "pix"
    pedido.split_aplicado = False
    pedido.pix_qr_code = payment_service.pix_copia_e_cola(pedido.valor_total, f"MN{pedido.id}")
    pedido.pix_qr_base64 = None
    db.commit()


def informar_pix_reserva(db: Session, pedido: Order) -> None:
    exigir_aguardando(pedido)
    if pedido.gateway != "manual":
        raise HTTPException(400, "Este pedido não está no Pix de reserva.")
    pedido.reserva_informado_em = pedido.reserva_informado_em or datetime.utcnow()
    db.commit()


def mensagem_recusa(detalhe: str | None) -> str:
    mensagens = {
        "cc_rejected_insufficient_amount": "Saldo ou limite insuficiente.",
        "cc_rejected_bad_filled_security_code": "Código de segurança (CVV) inválido.",
        "cc_rejected_bad_filled_date": "Data de validade inválida.",
        "cc_rejected_bad_filled_other": "Confira os dados do cartão.",
        "cc_rejected_call_for_authorize": "O banco pediu autorização. Ligue para o seu banco e tente de novo.",
        "cc_rejected_card_disabled": "Cartão bloqueado. Fale com o seu banco.",
        "cc_rejected_high_risk": "Pagamento recusado por segurança. Tente outro cartão ou o PIX.",
        "cc_rejected_duplicated_payment": "Você já fez um pagamento igual há pouco.",
    }
    return mensagens.get(detalhe or "", "Pagamento recusado. Tente outro cartão ou pague com PIX.")
