"""
Filas usadas para o sistema continuar funcionando quando um serviço externo cai.

- NotificacaoPagamento: aviso do Mercado Pago (webhook) que não deu para processar na hora
  (ex.: a API do Mercado Pago estava fora do ar). As tarefas automáticas tentam de novo.
- MensagemPendente: mensagem de WhatsApp que não saiu (Evolution API e reserva fora do ar).
  É reenviada depois, para o produtor/cliente não ficar sem o aviso.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.database import Base


class NotificacaoPagamento(Base):
    __tablename__ = "notificacoes_pagamento"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(40), index=True, nullable=False)
    tentativas = Column(Integer, default=0, server_default="0")
    proxima_tentativa = Column(DateTime, default=datetime.utcnow, index=True)
    processada_em = Column(DateTime, nullable=True, index=True)
    erro = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MensagemPendente(Base):
    __tablename__ = "mensagens_pendentes"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(20), nullable=False)
    texto = Column(Text, nullable=False)
    tentativas = Column(Integer, default=0, server_default="0")
    proxima_tentativa = Column(DateTime, default=datetime.utcnow, index=True)
    enviada_em = Column(DateTime, nullable=True, index=True)
    desistiu_em = Column(DateTime, nullable=True)   # passou de 24 h sem conseguir enviar
    created_at = Column(DateTime, default=datetime.utcnow)
