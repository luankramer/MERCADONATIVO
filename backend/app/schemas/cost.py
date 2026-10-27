from typing import Optional

from pydantic import BaseModel, Field


class CostItem(BaseModel):
    descricao: str = Field(min_length=1, max_length=200)
    valor: float = Field(ge=0)


class CostRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    rendimento: int = Field(ge=1)
    itens: list[CostItem] = Field(min_length=1)
    margem: float = Field(ge=0, le=1000)
    product_id: Optional[int] = None      # se informado, aplica o preço sugerido ao produto
    salvar: bool = True
