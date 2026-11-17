"""Repasses mensais: o que a plataforma recebeu na conta dela e pagou ao produtor no fim do mês."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class Repasse(Base):
    __tablename__ = "repasses"

    id = Column(Integer, primary_key=True, index=True)
    producer_id = Column(Integer, ForeignKey("producers.id", ondelete="SET NULL"), nullable=True, index=True)
    mes = Column(String(7), nullable=False, index=True)          # AAAA-MM das vendas
    quantidade_pedidos = Column(Integer, nullable=False, default=0)
    valor_vendas = Column(Float, nullable=False, default=0)      # total pago pelos clientes
    taxa_mercadopago = Column(Float, nullable=False, default=0)  # taxas do Mercado Pago
    comissao = Column(Float, nullable=False, default=0)          # comissão do Mercado Nativo
    valor_repasse = Column(Float, nullable=False, default=0)     # o que foi pago ao produtor
    observacao = Column(String(300), nullable=True)              # ex.: "Pix enviado, ID E123..."
    pago_em = Column(DateTime, default=datetime.utcnow)
    admin_id = Column(Integer, nullable=True)                    # quem registrou

    producer = relationship("Producer")
