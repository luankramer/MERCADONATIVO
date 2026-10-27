from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Producer(Base):
    """Produtor rural / artesão (perfil 'Produtor' do diagrama de classes)."""

    __tablename__ = "producers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    business_name = Column(String(255))
    hashed_password = Column(String(255), nullable=True)  # não usado: login é por WhatsApp
    estado = Column(String(255), nullable=True)
    telefone = Column(String(255), nullable=True)
    foto_perfil = Column(String(255), nullable=True)
    whatsapp = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # --- Campos de Endereço ---
    cep = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    endereco_publico = Column(Boolean, default=False, server_default="0")

    # --- Geolocalização (busca por raio) ---
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # --- Plano Premium ---
    premium = Column(Boolean, default=False, server_default="0")
    premium_ate = Column(DateTime, nullable=True)

    # --- Recebimentos: conta Mercado Pago conectada via OAuth (split automático) ---
    # Não guardamos dados bancários. Só o vínculo com o Mercado Pago, com os tokens criptografados.
    mp_user_id = Column(String(40), nullable=True)
    mp_public_key = Column(String(120), nullable=True)
    mp_access_token_enc = Column(Text, nullable=True)
    mp_refresh_token_enc = Column(Text, nullable=True)
    mp_token_expira = Column(DateTime, nullable=True)
    mp_conectado_em = Column(DateTime, nullable=True)

    seguidores = Column(Integer, default=0, server_default="0")
    ativo = Column(Boolean, default=True, server_default="1")

    # --- LGPD: aceite dos Termos/Política de Privacidade e exclusão da conta ---
    termos_aceitos_em = Column(DateTime, nullable=True)
    termos_versao = Column(String(20), nullable=True)
    excluido_em = Column(DateTime, nullable=True)  # conta excluída: dados pessoais apagados
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="producer")

    @property
    def is_premium(self) -> bool:
        if not self.premium:
            return False
        return self.premium_ate is None or self.premium_ate >= datetime.utcnow()

    @property
    def mp_conectado(self) -> bool:
        return bool(self.mp_access_token_enc and self.mp_public_key)

    @property
    def uf(self) -> str:
        return (self.estado or "AC").upper()
