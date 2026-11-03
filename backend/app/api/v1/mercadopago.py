"""Conexão do produtor com o Mercado Pago (OAuth do split): link pelo WhatsApp e retorno da autorização."""
from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import TokenInvalido, create_access_token, decode_token
from app.db.database import get_db
from app.models.user_model import Producer
from app.services import conexao_mp_service, payment_service

router = APIRouter(prefix="/api/v1/mercadopago", tags=["Mercado Pago"])

MENSAGENS = {
    "ok": ("Pronto!", f"Sua conta Mercado Pago foi conectada. Agora {100 - settings.PLATFORM_FEE_PERCENT:g}% de cada "
           "venda cai direto nela. Pode fechar esta página.", True),
    "cancelado": ("Conexão cancelada", "Você não autorizou no Mercado Pago. Quando quiser, toque no link de novo.", False),
    "expirado": ("Link vencido", "Este link já foi usado ou passou de 24 horas. Peça um novo no seu perfil "
                 "do Mercado Nativo ou para a equipe.", False),
    "erro": ("Não deu certo", "Não foi possível conectar agora. Tente de novo daqui a pouco ou peça ajuda à equipe.", False),
}


def _voltar(resultado: str, origem: str | None = None):
    if origem == "link":  # veio do WhatsApp, provavelmente no celular: responde aqui mesmo
        titulo, texto, ok = MENSAGENS.get(resultado, MENSAGENS["erro"])
        return conexao_mp_service.pagina(titulo, texto, ok)
    return RedirectResponse(f"{settings.FRONTEND_URL}/painel/perfil?mp={resultado}", status_code=303)


@router.get("/conectar/{token}")
def conectar_pelo_link(token: str, db: Session = Depends(get_db)):
    """Link enviado por WhatsApp: leva direto para a tela de autorização do Mercado Pago."""
    try:
        payload = decode_token(token)
    except TokenInvalido:
        return _voltar("expirado", "link")
    produtor = db.get(Producer, int(payload.get("sub", 0))) if payload.get("role") == "mp_link" else None
    # Conta removida/desativada ou link substituído (troca de WhatsApp, desconexão...): não vale mais
    if (not produtor or produtor.ativo is False or not produtor.mp_link_jti
            or payload.get("jti") != produtor.mp_link_jti):
        return _voltar("expirado", "link")
    state = create_access_token(produtor.id, "mp_oauth", timedelta(minutes=15),
                                extra={"origem": "link", "jti": produtor.mp_link_jti})
    try:
        return RedirectResponse(payment_service.url_conexao(state), status_code=303)
    except payment_service.PaymentError:
        return _voltar("erro", "link")


@router.get("/callback")
async def callback(code: str | None = None, state: str | None = None, error: str | None = None,
                   db: Session = Depends(get_db)):
    try:
        # O "state" é um token assinado e de curta duração: impede que alguém conecte
        # uma conta Mercado Pago ao perfil de outro produtor (ataque CSRF).
        payload = decode_token(state) if state else {}
    except TokenInvalido:
        return _voltar("expirado")
    origem = payload.get("origem")
    if error or not code or not payload:
        return _voltar("cancelado", origem)
    if payload.get("role") != "mp_oauth":
        return _voltar("erro", origem)
    produtor = db.get(Producer, int(payload["sub"]))
    if not produtor or produtor.ativo is False:
        return _voltar("erro", origem)
    if origem == "link" and (not produtor.mp_link_jti or payload.get("jti") != produtor.mp_link_jti):
        return _voltar("expirado", origem)  # link já usado ou substituído por outro
    if origem != "link" and int(payload.get("tv", 0)) != int(produtor.token_versao or 0):
        return _voltar("expirado", origem)  # pedido feito por uma sessão que já foi encerrada
    try:
        payment_service.trocar_codigo(produtor, code)
    except payment_service.PaymentError:
        return _voltar("erro", origem)
    produtor.mp_link_jti = None  # qualquer link pendente deixa de valer
    db.commit()
    await conexao_mp_service.avisar_conexao(produtor)
    return _voltar("ok", origem)
