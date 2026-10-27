"""Funções compartilhadas entre o checkout da vitrine e a assinatura Premium."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.order_model import PEDIDO_AGUARDANDO, Order, PremiumSubscription
from app.schemas.order import PagamentoBrick, PagamentoSimulado
from app.services import payment_service
from app.services.order_service import aplicar_status, confirmar_assinatura, confirmar_pedido

PIX_DEMO = ("00020126580014BR.GOV.BCB.PIX0136mercado-nativo-demonstracao5204000053039865802BR"
            "5914MERCADO NATIVO6010RIO BRANCO62070503***6304DEMO")


def exigir_aguardando(alvo) -> None:
    if alvo.status != PEDIDO_AGUARDANDO:
        raise HTTPException(400, "Este pagamento já foi concluído ou cancelado.")


def pagar_com_brick(db: Session, alvo: Order | PremiumSubscription, dados: PagamentoBrick, *,
                    valor: float, descricao: str, producer=None, cobrar_comissao=True) -> None:
    exigir_aguardando(alvo)
    try:
        resultado = payment_service.criar_pagamento(
            dados.model_dump(), valor=valor, descricao=descricao, referencia=alvo.codigo,
            producer=producer, cobrar_comissao=cobrar_comissao,
        )
    except payment_service.PaymentError as e:
        raise HTTPException(400, str(e))
    aplicar_status(db, alvo, resultado)
    if resultado.status == "rejected":
        raise HTTPException(402, mensagem_recusa(resultado.status_detalhe))


def pagar_simulado(db: Session, alvo: Order | PremiumSubscription, dados: PagamentoSimulado) -> None:
    if payment_service.modo_pagamento() != "simulado":
        raise HTTPException(400, "Simulação desativada: os pagamentos estão no modo real.")
    exigir_aguardando(alvo)
    alvo.gateway = "simulado"
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
    if payment_service.modo_pagamento() != "simulado" or alvo.gateway != "simulado" or alvo.metodo != "pix":
        raise HTTPException(400, "Não há PIX de demonstração para confirmar.")
    exigir_aguardando(alvo)
    confirmar_pedido(db, alvo) if isinstance(alvo, Order) else confirmar_assinatura(db, alvo)


def sincronizar(db: Session, alvo: Order | PremiumSubscription, producer=None) -> None:
    """Consulta o Mercado Pago quando o pagamento ainda está pendente (ex.: PIX)."""
    if alvo.status == PEDIDO_AGUARDANDO and alvo.gateway == "mercadopago" and alvo.gateway_payment_id:
        resultado = payment_service.consultar_pagamento(alvo.gateway_payment_id, producer)
        if resultado:
            aplicar_status(db, alvo, resultado)


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
