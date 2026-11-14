from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class AdminCreate(BaseModel):
    nome: str = Field(min_length=2)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)
    whatsapp: Optional[str] = Field(default=None, max_length=25)  # para recuperar a senha


class AdminUpdate(BaseModel):
    nome: str
    email: EmailStr
    senha: Optional[str] = None  # Senha opcional na edição
    whatsapp: Optional[str] = Field(default=None, max_length=25)


class AdminLogin(BaseModel):
    email: EmailStr
    senha: str


class AdminRecuperar(BaseModel):
    email: EmailStr


class AdminRedefinir(BaseModel):
    desafio: str = Field(min_length=10, max_length=64)
    codigo: str = Field(pattern=r"^\d{6}$")
    nova_senha: str = Field(min_length=8, max_length=128)


class PremiumUpdate(BaseModel):
    premium: bool
