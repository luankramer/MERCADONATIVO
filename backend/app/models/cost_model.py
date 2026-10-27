from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.db.database import Base


class CostCalculation(Base):
    """Cálculo salvo da Calculadora de Custos (ferramenta Premium)."""

    __tablename__ = "cost_calculations"

    id = Column(Integer, primary_key=True, index=True)
    producer_id = Column(Integer, ForeignKey("producers.id"), index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    nome = Column(String(255), nullable=False)
    rendimento = Column(Integer, nullable=False)
    itens = Column(Text, nullable=False)  # JSON: [{"descricao": str, "valor": float}]
    margem = Column(Float, nullable=False)
    custo_total = Column(Float, nullable=False)
    custo_unitario = Column(Float, nullable=False)
    preco_sugerido = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
