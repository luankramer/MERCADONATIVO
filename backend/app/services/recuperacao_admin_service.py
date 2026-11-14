"""
Recuperação de conta do painel administrativo ("Esqueci minha senha").

1. O admin informa o e-mail. Se for de um administrador ativo, um código de 6 dígitos vai para o
   WhatsApp cadastrado (ou ADMIN_MASTER_WHATSAPP, no caso do Super Admin) e para o e-mail
   (quando o SMTP estiver configurado). A resposta é sempre a mesma, exista ou não o e-mail.
2. Com o código, ele define uma senha nova. O código vale 10 minutos e aceita 5 tentativas.
"""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.security import hash_password
from app.models.admin_model import Admin
from app.services import email_service
from app.services.whatsapp_service import enviar_codigo, numero_nacional, numero_valido

log = logging.getLogger("mercado_nativo")

VALIDADE = timedelta(minutes=10)
MAX_TENTATIVAS = 5
SENHA_MINIMA = 8

# desafio -> {"admin_id", "codigo_hash", "expira", "tentativas"}
_pedidos: dict[str, dict] = {}


class RecuperacaoError(Exception):
    pass


def _hash(codigo: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), codigo.encode(), hashlib.sha256).hexdigest()


def _limpar_vencidos() -> None:
    agora = datetime.utcnow()
    for d in [d for d, p in _pedidos.items() if p["expira"] < agora]:
        _pedidos.pop(d, None)


def whatsapp_do_admin(admin: Admin) -> str:
    numero = admin.whatsapp or ""
    if not numero and admin.is_super:
        numero = settings.ADMIN_MASTER_WHATSAPP
    numero = numero_nacional(numero)
    return numero if numero_valido(numero) else ""


def texto_codigo(codigo: str) -> str:
    return (f"Mercado Nativo: o código para criar uma nova senha do painel administrativo é {codigo}.\n"
            f"Ele vale por {int(VALIDADE.total_seconds() // 60)} minutos. Se não foi você que pediu, "
            "ignore esta mensagem e avise a equipe.")


def preparar(db: Session, email: str) -> tuple[str, dict | None]:
    """Cria o desafio. Devolve (desafio, envio). envio é None se o e-mail não for de um admin ativo."""
    _limpar_vencidos()
    desafio = secrets.token_urlsafe(18)
    admin = db.query(Admin).filter(func.lower(Admin.email) == (email or "").strip().lower()).first()
    if not admin or admin.ativo is False:
        return desafio, None
    # Um pedido novo invalida os anteriores do mesmo admin
    for d in [d for d, p in _pedidos.items() if p["admin_id"] == admin.id]:
        _pedidos.pop(d, None)
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    _pedidos[desafio] = {"admin_id": admin.id, "codigo_hash": _hash(codigo),
                         "expira": datetime.utcnow() + VALIDADE, "tentativas": 0}
    return desafio, {"codigo": codigo, "whatsapp": whatsapp_do_admin(admin), "email": admin.email}


async def enviar(envio: dict) -> bool:
    """Manda o código pelo WhatsApp e pelo e-mail. Roda depois da resposta (não revela se o e-mail existe)."""
    codigo, texto = envio["codigo"], texto_codigo(envio["codigo"])
    enviado = False
    if envio["whatsapp"]:
        enviado = await enviar_codigo(envio["whatsapp"], codigo, texto)
    if email_service.email_configurado():
        enviado = await run_in_threadpool(
            email_service.enviar_email, envio["email"], "Recuperação de senha — Mercado Nativo", texto) or enviado
    if not enviado:
        if settings.OTP_DEV_MODE:
            # Só no terminal de quem roda o servidor, nunca no navegador
            print(f"\n🔑 [MODO DESENVOLVIMENTO] Código de recuperação do admin {envio['email']}: {codigo}\n")
        else:
            log.warning("Recuperação de senha: sem WhatsApp nem e-mail para enviar o código de %s",
                        email_service.mascarar(envio["email"]))
    return enviado


def redefinir(db: Session, desafio: str, codigo: str, nova_senha: str) -> Admin:
    _limpar_vencidos()
    pedido = _pedidos.get(desafio or "")
    if not pedido:
        raise RecuperacaoError("Código vencido ou inválido. Peça um novo código.")
    if not hmac.compare_digest(pedido["codigo_hash"], _hash((codigo or "").strip())):
        pedido["tentativas"] += 1
        if pedido["tentativas"] >= MAX_TENTATIVAS:
            _pedidos.pop(desafio, None)
            raise RecuperacaoError("Muitas tentativas erradas. Peça um novo código.")
        raise RecuperacaoError("Código incorreto. Confira e tente de novo.")
    if len(nova_senha or "") < SENHA_MINIMA:
        raise RecuperacaoError(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")
    admin = db.get(Admin, pedido["admin_id"])
    if not admin or admin.ativo is False:
        _pedidos.pop(desafio, None)
        raise RecuperacaoError("Acesso desativado.")
    admin.senha_hash = hash_password(nova_senha)
    db.commit()
    _pedidos.pop(desafio, None)
    return admin
