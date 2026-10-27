import secrets
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base

# Status do pedido
PEDIDO_AGUARDANDO = "aguardando_pagamento"
PEDIDO_PAGO = "pago"
PEDIDO_RETIRADO = "retirado"
PEDIDO_CANCELADO = "cancelado"

METODOS = {"pix": "PIX", "credit_card": "Crédito", "debit_card": "Débito"}


def novo_codigo() -> str:
    """Código público do pedido (aleatório — não dá para adivinhar pedidos de outras pessoas)."""
    return secrets.token_urlsafe(16)


class Order(Base):
    """Pedido feito na vitrine (checkout transparente com split)."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(40), unique=True, index=True, default=novo_codigo)
    producer_id = Column(Integer, ForeignKey("producers.id"), index=True)
    consumidor_nome = Column(String(150), nullable=False)
    consumidor_whatsapp = Column(String(20), nullable=False)
    consumidor_email = Column(String(150), nullable=True)

    valor_total = Column(Float, nullable=False)
    taxa_plataforma = Column(Float, nullable=False)  # comissão da plataforma
    valor_produtor = Column(Float, nullable=False)   # repasse líquido ao produtor

    status = Column(String(30), default=PEDIDO_AGUARDANDO, index=True)
    status_detalhe = Column(String(80), nullable=True)
    metodo = Column(String(20), nullable=True)       # pix | credit_card | debit_card
    parcelas = Column(Integer, nullable=True)
    gateway = Column(String(20), default="simulado")
    gateway_payment_id = Column(String(40), nullable=True, index=True)
    pix_qr_code = Column(Text, nullable=True)
    pix_qr_base64 = Column(Text, nullable=True)
    split_aplicado = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    producer = relationship("Producer")
    itens = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    nome_produto = Column(String(255), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)

    order = relationship("Order", back_populates="itens")


class PremiumSubscription(Base):
    """Mensalidade do plano Premium paga pelo produtor."""

    __tablename__ = "premium_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(40), unique=True, index=True, default=novo_codigo)
    producer_id = Column(Integer, ForeignKey("producers.id"), index=True)
    valor = Column(Float, nullable=False)
    status = Column(String(30), default=PEDIDO_AGUARDANDO)
    status_detalhe = Column(String(80), nullable=True)
    metodo = Column(String(20), nullable=True)
    gateway = Column(String(20), default="simulado")
    gateway_payment_id = Column(String(40), nullable=True, index=True)
    pix_qr_code = Column(Text, nullable=True)
    pix_qr_base64 = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    producer = relationship("Producer")
