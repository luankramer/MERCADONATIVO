from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    nome: str
    preco: float
    lote: Optional[str] = None
    categoria: str
    estoque: int
    descricao_tecnica: Optional[str] = None
    historia: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    producer_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    nota: int = Field(ge=1, le=5)
    comentario: Optional[str] = Field(default=None, max_length=1000)


class RejectRequest(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)


class DestaqueUpdate(BaseModel):
    destaque: bool
