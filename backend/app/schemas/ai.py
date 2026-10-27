from typing import Literal, Optional

from pydantic import BaseModel


class AIPrompt(BaseModel):
    prompt: str
    tipo: Literal["produto", "produtor"] = "produto"
    nome: Optional[str] = None  # nome do produto/loja (dá contexto à IA)
