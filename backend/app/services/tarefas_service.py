"""
Tarefas automáticas: mantêm tudo em dia quando o Mercado Pago ou o WhatsApp falham.

Roda numa thread do próprio backend, a cada TAREFAS_INTERVALO segundos (padrão 2 min):
1. Avisos do Mercado Pago (webhook) que ficaram na fila porque a API estava fora do ar.
2. Pedidos e mensalidades pendentes: reconsulta o status (Pix pago enquanto o webhook falhou).
3. Cobranças cuja resposta se perdeu (queda de rede): acha o pagamento pelo código do pedido.
4. Devoluções em andamento: acompanha até o Mercado Pago aprovar (ou marca "falhou").
5. Mensagens de WhatsApp que não saíram: reenvia.
Também pode ser chamada na mão:  python -m app.services.tarefas_service
"""
import logging
import threading
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.fila_model import NotificacaoPagamento
from app.models.order_model import PEDIDO_AGUARDANDO, PEDIDO_CANCELADO, Order, PremiumSubscription
from app.services import notificacao_service, payment_service
from app.services.checkout_service import sincronizar
from app.services.order_service import aplicar_status

log = logging.getLogger("mercado_nativo")
MAX_TENTATIVAS_AVISO = 30
JANELA_PENDENTES = timedelta(days=3)

_parar = threading.Event()
_thread: threading.Thread | None = None


# ---------------- Avisos do Mercado Pago ----------------
def processar_notificacao(db: Session, payment_id: str) -> bool:
    """Aplica o status atual do pagamento. True = resolvido (ou nada a fazer); False = tentar depois."""
    pedido = db.query(Order).filter(Order.gateway_payment_id == payment_id).first()
    if pedido:
        resultado = payment_service.consultar_pagamento(payment_id, pedido.producer)
        if not resultado:
            return False
        aplicar_status(db, pedido, resultado)
        return True
    assinatura = db.query(PremiumSubscription).filter(PremiumSubscription.gateway_payment_id == payment_id).first()
    if assinatura:
        resultado = payment_service.consultar_pagamento(payment_id)
        if not resultado:
            return False
        aplicar_status(db, assinatura, resultado)
        return True
    # Pagamento que o sistema ainda não conhece: a resposta da cobrança pode ter se perdido.
    # O Mercado Pago informa o código do pedido (external_reference); ligamos os dois.
    resultado = payment_service.consultar_pagamento(payment_id)
    if not resultado:
        return False
    alvo = (db.query(Order).filter(Order.codigo == resultado.referencia).first() if resultado.referencia else None) \
        or (db.query(PremiumSubscription).filter(PremiumSubscription.codigo == resultado.referencia).first()
            if resultado.referencia else None)
    if alvo and alvo.gateway in ("mercadopago", "desativado") and not alvo.gateway_payment_id:
        aplicar_status(db, alvo, resultado)
    return True


def enfileirar_notificacao(db: Session, payment_id: str) -> None:
    existente = (db.query(NotificacaoPagamento)
                 .filter(NotificacaoPagamento.payment_id == payment_id, NotificacaoPagamento.processada_em.is_(None))
                 .first())
    if not existente:
        db.add(NotificacaoPagamento(payment_id=payment_id, tentativas=0,
                                    proxima_tentativa=datetime.utcnow() + timedelta(minutes=1)))
        db.commit()
        log.warning("Aviso do Mercado Pago %s guardado para tentar de novo (API indisponível).", payment_id)


def _avisos_pendentes(db: Session) -> int:
    agora = datetime.utcnow()
    feitos = 0
    fila = (db.query(NotificacaoPagamento)
            .filter(NotificacaoPagamento.processada_em.is_(None), NotificacaoPagamento.proxima_tentativa <= agora)
            .order_by(NotificacaoPagamento.id).limit(50).all())
    for n in fila:
        if not payment_service.mp_disponivel():
            break
        if processar_notificacao(db, n.payment_id):
            n.processada_em = datetime.utcnow()
            feitos += 1
        else:
            n.tentativas = (n.tentativas or 0) + 1
            if n.tentativas >= MAX_TENTATIVAS_AVISO:
                n.processada_em = datetime.utcnow()
                n.erro = "desistiu: o Mercado Pago não confirmou este pagamento"
            else:
                n.proxima_tentativa = agora + timedelta(minutes=min(60, 2 ** min(n.tentativas, 6)))
        db.commit()
    return feitos


# ---------------- Reconsultas ----------------
def _pendentes_com_pagamento(db: Session) -> int:
    desde = datetime.utcnow() - JANELA_PENDENTES
    total = 0
    pedidos = (db.query(Order).filter(Order.status == PEDIDO_AGUARDANDO, Order.gateway == "mercadopago",
                                      Order.gateway_payment_id.isnot(None), Order.created_at >= desde)
               .order_by(Order.id.desc()).limit(50).all())
    for p in pedidos:
        if not payment_service.mp_disponivel():
            break
        sincronizar(db, p, p.producer)
        total += 1
    assinaturas = (db.query(PremiumSubscription)
                   .filter(PremiumSubscription.status == PEDIDO_AGUARDANDO, PremiumSubscription.gateway == "mercadopago",
                           PremiumSubscription.gateway_payment_id.isnot(None), PremiumSubscription.created_at >= desde)
                   .limit(50).all())
    for a in assinaturas:
        if not payment_service.mp_disponivel():
            break
        sincronizar(db, a)
        total += 1
    return total


def _cobrancas_sem_resposta(db: Session) -> int:
    """Pedidos em que o site pediu a cobrança mas não recebeu a resposta (queda no meio)."""
    desde = datetime.utcnow() - timedelta(days=2)
    achados = 0
    pedidos = (db.query(Order).filter(Order.status == PEDIDO_AGUARDANDO, Order.gateway == "mercadopago",
                                      Order.gateway_payment_id.is_(None), Order.pagamento_iniciado_em.isnot(None),
                                      Order.pagamento_iniciado_em >= desde)
               .limit(30).all())
    for p in pedidos:
        if not payment_service.mp_disponivel():
            break
        resultado = payment_service.buscar_por_referencia(p.codigo, p.producer)
        if resultado:
            aplicar_status(db, p, resultado)
            achados += 1
    return achados


def _devolucoes_em_andamento(db: Session) -> int:
    resolvidas = 0
    pedidos = (db.query(Order).filter(Order.status == PEDIDO_CANCELADO, Order.reembolso_status == "pending",
                                      Order.reembolso_id.isnot(None)).limit(30).all())
    for p in pedidos:
        if not payment_service.mp_disponivel():
            break
        status = payment_service.consultar_reembolso(p.gateway_payment_id, p.reembolso_id, p.producer,
                                                     bool(p.split_aplicado))
        if status == "approved":
            p.reembolso_status = "approved"
            resolvidas += 1
        elif status in ("rejected", "cancelled", "canceled"):
            p.reembolso_status = "falhou"
            log.warning("A devolução do pedido %s falhou no Mercado Pago: a equipe precisa resolver.", p.id)
        db.commit()
    return resolvidas


def executar_ciclo() -> dict:
    """Uma rodada de todas as tarefas. Cada parte é independente: um erro não para as outras."""
    resumo = {}
    partes = [("mensagens_reenviadas", notificacao_service.reenviar_pendentes)]
    if payment_service.modo_pagamento() == "mercadopago":
        partes = [("avisos_processados", _avisos_pendentes), ("pendentes_consultados", _pendentes_com_pagamento),
                  ("cobrancas_recuperadas", _cobrancas_sem_resposta),
                  ("devolucoes_confirmadas", _devolucoes_em_andamento)] + partes
    for nome, tarefa in partes:
        db = SessionLocal()
        try:
            resumo[nome] = tarefa(db)
        except Exception as e:
            db.rollback()
            log.warning("Tarefa automática '%s' falhou: %s", nome, type(e).__name__)
            resumo[nome] = "erro"
        finally:
            db.close()
    return resumo


def situacao(db: Session) -> dict:
    """Para o painel da equipe: como estão os serviços externos e as filas."""
    from app.models.fila_model import MensagemPendente
    from app.services.whatsapp_service import evolution_configurada, meta_configurada
    from app.services.email_service import email_configurado
    return {
        "pagamentos": payment_service.modo_pagamento(),
        "mercado_pago_respondendo": payment_service.mp_disponivel(),
        "pix_reserva_configurado": payment_service.pix_reserva_disponivel(),
        "whatsapp_principal": evolution_configurada(),
        "whatsapp_reserva_meta": meta_configurada(),
        "email_reserva": email_configurado(),
        "avisos_mp_na_fila": db.query(NotificacaoPagamento).filter(NotificacaoPagamento.processada_em.is_(None)).count(),
        "mensagens_na_fila": db.query(MensagemPendente).filter(MensagemPendente.enviada_em.is_(None),
                                                               MensagemPendente.desistiu_em.is_(None)).count(),
        "pix_reserva_a_conferir": db.query(Order).filter(Order.status == PEDIDO_AGUARDANDO, Order.gateway == "manual",
                                                         Order.reserva_informado_em.isnot(None)).count(),
        "devolucoes_com_problema": db.query(Order).filter(Order.reembolso_status == "falhou").count(),
    }


# ---------------- Thread em segundo plano ----------------
def _laco() -> None:
    while not _parar.wait(settings.TAREFAS_INTERVALO):
        try:
            executar_ciclo()
        except Exception as e:  # nunca deixa a thread morrer
            log.warning("Erro nas tarefas automáticas: %s", type(e).__name__)


def iniciar() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _parar.clear()
    _thread = threading.Thread(target=_laco, name="tarefas-mercado-nativo", daemon=True)
    _thread.start()


def parar() -> None:
    _parar.set()


if __name__ == "__main__":
    print(executar_ciclo())
