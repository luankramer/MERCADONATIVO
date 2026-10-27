import json
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base

# Status da curadoria
STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_REJEITADO = "rejeitado"

CATEGORIAS = ["Alimentos", "Hortifruti", "Artesanato", "Bebidas"]


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), index=True, nullable=False)
    preco = Column(Float, nullable=False)
    lote = Column(String(100), nullable=True)
    categoria = Column(String(100), nullable=False)
    estoque = Column(Integer, default=0)
    descricao_tecnica = Column(Text, nullable=True)
    historia = Column(Text, nullable=True)

    # Faz a ligação exata com o id do produtor
    producer_id = Column(Integer, ForeignKey("producers.id"))

    # --- Curadoria administrativa ---
    status = Column(String(20), default=STATUS_PENDENTE, server_default=STATUS_PENDENTE, index=True)
    analise_ia = Column(Text, nullable=True)  # JSON com o resultado da análise automática
    motivo_rejeicao = Column(String(500), nullable=True)

    # --- Vitrine Premium ---
    destaque = Column(Boolean, default=False, server_default="0")

    # --- Métricas ---
    visualizacoes = Column(Integer, default=0, server_default="0")
    contatos_whatsapp = Column(Integer, default=0, server_default="0")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    producer = relationship("Producer", back_populates="products")
    imagens = relationship(
        "ProductImage", back_populates="product", cascade="all, delete-orphan",
        order_by="ProductImage.ordem",
    )
    avaliacoes = relationship("Review", back_populates="product", cascade="all, delete-orphan")

    @property
    def analise(self) -> dict | None:
        if not self.analise_ia:
            return None
        try:
            return json.loads(self.analise_ia)
        except ValueError:
            return None


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    url = Column(String(255), nullable=False)
    ordem = Column(Integer, default=0)

    product = relationship("Product", back_populates="imagens")
