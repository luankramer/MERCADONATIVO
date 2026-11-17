from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# Unidades aceitas na calculadora (kg/g, L/ml, metro/cm, unidade)
Unidade = Literal["kg", "g", "L", "ml", "m", "cm", "un"]


class CostItem(BaseModel):
    """Um insumo: como foi comprado e quanto foi usado nesta produção.
    Ex.: "paguei R$ 5,50 por 1 kg de açúcar e usei 2 kg"; "paguei R$ 30 por 12 potes e usei 10";
    "paguei R$ 18 por um novelo de 500 m e usei 120 m"."""
    descricao: str = Field(min_length=1, max_length=200)
    preco_compra: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    qtd_compra: Optional[float] = Field(default=None, gt=0, le=1_000_000)
    unidade_compra: Optional[Unidade] = None
    qtd_usada: Optional[float] = Field(default=None, ge=0, le=1_000_000)
    unidade_usada: Optional[Unidade] = None
    # Formato antigo (só o valor gasto no item). Ainda aceito para cálculos já salvos.
    valor: Optional[float] = Field(default=None, ge=0, le=1_000_000)

    @model_validator(mode="after")
    def _completo(self):
        novo = (self.preco_compra, self.qtd_compra, self.unidade_compra, self.qtd_usada, self.unidade_usada)
        if all(v is None for v in novo):
            if self.valor is None:
                raise ValueError("Informe quanto pagou, quanto comprou e quanto usou.")
            return self
        if any(v is None for v in novo):
            raise ValueError(f"Complete o item \"{self.descricao}\": preço, quantidade comprada e quantidade usada.")
        return self


class CostRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    rendimento: int = Field(ge=1, le=100_000)           # quantas unidades a produção rende
    itens: list[CostItem] = Field(min_length=1, max_length=60)
    horas_trabalho: float = Field(default=0, ge=0, le=10_000)
    valor_hora: float = Field(default=0, ge=0, le=10_000)
    outros_gastos: float = Field(default=0, ge=0, le=1_000_000)   # gás, energia, transporte...
    margem: float = Field(ge=0, le=1000)
    # true = o preço já cobre a taxa do Mercado Pago (cartão) e a comissão do Mercado Nativo
    incluir_taxas: bool = False
    product_id: Optional[int] = None      # se informado, aplica o preço sugerido ao produto
    salvar: bool = True
