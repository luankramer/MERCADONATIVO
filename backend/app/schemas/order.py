from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class CheckoutCreate(BaseModel):
    product_id: int
    quantidade: int = Field(ge=1, le=999)
    nome: str = Field(min_length=2, max_length=150)
    whatsapp: str = Field(min_length=10, max_length=20)


class Identificacao(BaseModel):
    type: str = Field(default="CPF", max_length=10)
    number: str = Field(max_length=20)


class Pagador(BaseModel):
    email: EmailStr
    identification: Optional[Identificacao] = None


class PagamentoBrick(BaseModel):
    """Dados que o Payment Brick do Mercado Pago entrega (o cartão chega apenas como token)."""
    payment_method_id: str = Field(max_length=40)
    token: Optional[str] = Field(default=None, max_length=200)
    issuer_id: Optional[str | int] = None
    installments: Optional[int] = Field(default=1, ge=1, le=24)
    payer: Pagador


class PagamentoSimulado(BaseModel):
    metodo: Literal["pix", "credit_card", "debit_card"]
    parcelas: int = Field(default=1, ge=1, le=12)
