from sqlalchemy import Boolean, Column, Integer, String

from app.core.config import settings
from app.db.database import Base

NIVEL_SUPER = "super"
NIVEL_ADMIN = "admin"


class Admin(Base):
    __tablename__ = "administradores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    ativo = Column(Boolean, default=True)
    nivel = Column(String(20), default=NIVEL_ADMIN, server_default=NIVEL_ADMIN)

    @property
    def is_super(self) -> bool:
        return self.nivel == NIVEL_SUPER or (self.email or "").lower() == settings.ADMIN_MASTER_EMAIL
