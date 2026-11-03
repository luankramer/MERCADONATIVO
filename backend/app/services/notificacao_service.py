"""
Avisos por WhatsApp que não podem se perder (pedido pago, pedido cancelado...).

Tenta enviar na hora (Evolution API e, se falhar, a API da Meta). Se nenhuma funcionar,
guarda na fila `mensagens_pendentes` e as tarefas automáticas reenviam depois
(1, 2, 4, 8... minutos, até 1 h entre tentativas, por no máximo 24 h).
"""
import asyncio
import logging
import threading
from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.models.fila_model import MensagemPendente
from app.services.whatsapp_service import enviar_mensagem_openwa, numero_nacional, whatsapp_configurado

log = logging.getLogger("mercado_nativo")
PRAZO_MAXIMO = timedelta(hours=24)


def _rodar(coro) -> bool:
    """Executa o envio assíncrono a partir de código síncrono (rotas `def` rodam fora do loop)."""
    return bool(asyncio.run(coro))


def enfileirar(numero: str, texto: str) -> None:
    db = SessionLocal()
    try:
        db.add(MensagemPendente(numero=numero_nacional(numero), texto=texto, tentativas=1,
                                proxima_tentativa=datetime.utcnow() + timedelta(minutes=1)))
        db.commit()
    finally:
        db.close()


def _enviar_ou_enfileirar(numero: str, texto: str) -> bool:
    try:
        if _rodar(enviar_mensagem_openwa(numero, texto)):
            return True
    except Exception as e:
        log.warning("Erro ao enviar WhatsApp: %s", type(e).__name__)
    if not whatsapp_configurado():
        return False  # desenvolvimento sem WhatsApp: não adianta guardar
    try:
        enfileirar(numero, texto)
    except Exception as e:
        log.warning("Não foi possível guardar a mensagem na fila: %s", type(e).__name__)
    return False


def notificar(numero: str | None, texto: str) -> bool:
    """Envia agora ou deixa na fila para reenviar. Retorna True se saiu na hora.
    Dentro de uma rota assíncrona, o envio vai para uma thread à parte (não trava o servidor)."""
    if not numero:
        return False
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _enviar_ou_enfileirar(numero, texto)
    threading.Thread(target=_enviar_ou_enfileirar, args=(numero, texto), daemon=True).start()
    return False


def reenviar_pendentes(db, limite: int = 30) -> int:
    """Chamado pelas tarefas automáticas. Retorna quantas mensagens saíram."""
    agora = datetime.utcnow()
    pendentes = (db.query(MensagemPendente)
                 .filter(MensagemPendente.enviada_em.is_(None), MensagemPendente.desistiu_em.is_(None),
                         MensagemPendente.proxima_tentativa <= agora)
                 .order_by(MensagemPendente.id).limit(limite).all())
    enviadas = 0
    for m in pendentes:
        if _rodar(enviar_mensagem_openwa(m.numero, m.texto)):
            m.enviada_em = datetime.utcnow()
            enviadas += 1
        elif agora - (m.created_at or agora) > PRAZO_MAXIMO:
            m.desistiu_em = agora
            log.warning("Mensagem %s não foi entregue em 24 h e saiu da fila.", m.id)
        else:
            m.tentativas = (m.tentativas or 0) + 1
            m.proxima_tentativa = agora + timedelta(minutes=min(60, 2 ** min(m.tentativas, 6)))
    db.commit()
    return enviadas
