from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProducerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    business_name: str = Field(min_length=2, max_length=255)
    whatsapp: str = Field(min_length=10, max_length=20)
    description: str = ""
    cep: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    estado: Optional[str] = "AC"
    email: Optional[str] = None
    # Precisa ser True: o produtor aceita os Termos de Uso e a Política de Privacidade
    aceite_termos: bool = False


class LoginWhatsApp(BaseModel):
    whatsapp: str = Field(min_length=8, max_length=20)
    # "email" = receber o código no e-mail cadastrado (reserva quando o WhatsApp está fora do ar)
    canal: Literal["whatsapp", "email"] = "whatsapp"


class VerifyOTP(BaseModel):
    whatsapp: str = Field(min_length=8, max_length=20)
    code: str = Field(max_length=10)
    # Identifica este pedido de código: só quem pediu consegue usá-lo (e errar não apaga o de outra pessoa)
    desafio: str = Field(min_length=10, max_length=64)


class TrocarWhatsApp(BaseModel):
    whatsapp: str = Field(min_length=8, max_length=20)


class ConfirmarWhatsApp(BaseModel):
    whatsapp: str = Field(min_length=8, max_length=20)
    code: str = Field(max_length=10)
