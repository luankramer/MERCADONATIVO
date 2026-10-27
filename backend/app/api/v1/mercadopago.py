"""Retorno do OAuth do Mercado Pago (quando o produtor autoriza o split na conta dele)."""
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import TokenInvalido, decode_token
from app.db.database import get_db
from app.models.user_model import Producer
from app.services import payment_service

router = APIRouter(prefix="/api/v1/mercadopago", tags=["Mercado Pago"])


def _voltar(resultado: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.FRONTEND_URL}/painel/perfil?mp={resultado}", status_code=303)


@router.get("/callback")
def callback(code: str | None = None, state: str | None = None, error: str | None = None,
             db: Session = Depends(get_db)):
    if error or not code or not state:
        return _voltar("cancelado")
    try:
        # O "state" é um token assinado e de curta duração: impede que alguém conecte
        # uma conta Mercado Pago ao perfil de outro produtor (ataque CSRF).
        payload = decode_token(state)
    except TokenInvalido:
        return _voltar("expirado")
    if payload.get("role") != "mp_oauth":
        return _voltar("erro")
    produtor = db.get(Producer, int(payload["sub"]))
    if not produtor:
        return _voltar("erro")
    try:
        payment_service.trocar_codigo(produtor, code)
    except payment_service.PaymentError:
        return _voltar("erro")
    db.commit()
    return _voltar("ok")
