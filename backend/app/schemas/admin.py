from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class AdminCreate(BaseModel):
    nome: str = Field(min_length=2)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)


class AdminUpdate(BaseModel):
    nome: str
    email: EmailStr
    senha: Optional[str] = None  # Senha opcional na edição


class AdminLogin(BaseModel):
    email: EmailStr
    senha: str


class PremiumUpdate(BaseModel):
    premium: bool
