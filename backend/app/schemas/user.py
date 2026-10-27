from typing import Optional

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
    whatsapp: str


class VerifyOTP(BaseModel):
    whatsapp: str
    code: str
