"""Cadastro e login do produtor (código de acesso enviado pelo WhatsApp, sem senha)."""
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import ip_cliente, limitar, registrar
from app.core.security import create_access_token
from app.db.database import get_db
from app.models.user_model import Producer
from app.schemas.user import LoginWhatsApp, ProducerCreate, VerifyOTP
from app.services import geo_service
from app.services.whatsapp_service import enviar_mensagem_openwa, numero_nacional

router = APIRouter()

# Códigos OTP em memória: {whatsapp: {"code": str, "expira": datetime, "tentativas": int}}
otp_storage: dict[str, dict] = {}


def buscar_por_whatsapp(db: Session, whatsapp: str) -> Producer | None:
    numero = numero_nacional(whatsapp)
    produtor = db.query(Producer).filter(Producer.whatsapp == numero).first()
    if produtor:
        return produtor
    # Compatibilidade com cadastros antigos gravados com máscara "(68) 9 9999-9999"
    for p in db.query(Producer).filter(Producer.whatsapp.isnot(None)).all():
        if numero_nacional(p.whatsapp) == numero:
            return p
    return None


@router.post("/producer/register", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(limitar("cadastro", 5, 3600))])
async def register_producer(req: ProducerCreate, db: Session = Depends(get_db)):
    if not req.aceite_termos:
        raise HTTPException(400, "Para se cadastrar é preciso aceitar os Termos de Uso e a Política de Privacidade.")
    numero = numero_nacional(req.whatsapp)
    if len(numero) not in (10, 11):
        raise HTTPException(400, "WhatsApp inválido. Use DDD + número, ex.: (68) 9 9999-9999.")
    if buscar_por_whatsapp(db, numero):
        raise HTTPException(400, "WhatsApp já cadastrado.")
    if req.email and db.query(Producer).filter(Producer.email == req.email).first():
        raise HTTPException(400, "E-mail já cadastrado.")

    uf = (req.estado or "AC").upper()[:2]
    cidade = geo_service.nome_oficial(req.city, uf)
    coords = geo_service.coordenadas(cidade, uf)

    novo_produtor = Producer(
        name=req.name.strip(),
        business_name=req.business_name.strip(),
        whatsapp=numero,
        description=req.description or "Produtor local.",
        cep=req.cep,
        address=req.address,
        city=cidade,
        estado=uf,
        email=req.email or None,
        latitude=coords[0] if coords else None,
        longitude=coords[1] if coords else None,
        termos_aceitos_em=datetime.utcnow(),
        termos_versao=settings.TERMOS_VERSAO,
    )
    db.add(novo_produtor)
    db.commit()
    db.refresh(novo_produtor)
    return {"message": "Cadastro realizado com sucesso", "id": novo_produtor.id}


@router.post("/producer/request-code")
async def request_code(req: LoginWhatsApp, request: Request, db: Session = Depends(get_db)):
    numero = numero_nacional(req.whatsapp)
    # Evita envio em massa de mensagens: por IP e por número
    registrar(f"otp-ip:{ip_cliente(request)}", 10, 600)
    registrar(f"otp-num:{numero}", 3, 600)

    produtor = buscar_por_whatsapp(db, numero)
    if not produtor:
        raise HTTPException(404, "Este WhatsApp ainda não tem cadastro. Crie sua conta de produtor.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    otp_storage[numero] = {
        "code": code,
        "expira": datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        "tentativas": 0,
    }
    texto = (
        f"🍃 *Mercado Nativo*\n\nSeu código de acesso é: *{code}*\n\n"
        f"Ele vale por {settings.OTP_EXPIRE_MINUTES} minutos. Não compartilhe com ninguém."
    )
    if await enviar_mensagem_openwa(numero, texto):
        return {"message": "Código enviado pelo WhatsApp.", "enviado": True}

    if settings.OTP_DEV_MODE:
        # O código NUNCA vai para o navegador: aparece apenas no terminal de quem roda o servidor
        print(f"\n🔑 [MODO DESENVOLVIMENTO] WhatsApp indisponível. Código para {numero}: {code}\n")
        return {"message": "WhatsApp indisponível. Veja o código no terminal do backend.", "enviado": False}
    otp_storage.pop(numero, None)
    raise HTTPException(502, "Não conseguimos enviar o código pelo WhatsApp agora. Tente em instantes.")


@router.post("/producer/verify-code")
async def verify_code(req: VerifyOTP, request: Request, db: Session = Depends(get_db)):
    numero = numero_nacional(req.whatsapp)
    registrar(f"otp-verificar:{ip_cliente(request)}", 20, 600)
    registro = otp_storage.get(numero)
    if not registro:
        raise HTTPException(401, "Código expirado. Solicite um novo.")
    if datetime.utcnow() > registro["expira"]:
        otp_storage.pop(numero, None)
        raise HTTPException(401, "Código expirado. Solicite um novo.")
    if not hmac.compare_digest(registro["code"].encode(), (req.code or "").strip().encode()):
        registro["tentativas"] += 1
        if registro["tentativas"] >= 5:
            otp_storage.pop(numero, None)
            raise HTTPException(429, "Muitas tentativas. Solicite um novo código.")
        raise HTTPException(401, "Código incorreto.")

    otp_storage.pop(numero, None)
    produtor = buscar_por_whatsapp(db, numero)
    if not produtor:
        raise HTTPException(404, "Produtor não encontrado.")
    return {
        "access_token": create_access_token(produtor.id, "producer"),
        "token_type": "bearer",
        "producer": {"id": produtor.id, "nome": produtor.name, "nome_loja": produtor.business_name},
    }


@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_mode_alt: str = Query(None, alias="hub_mode"),
    hub_verify_token_alt: str = Query(None, alias="hub_verify_token"),
    hub_challenge_alt: str = Query(None, alias="hub_challenge"),
):
    mode = hub_mode or hub_mode_alt
    token = hub_verify_token or hub_verify_token_alt
    challenge = hub_challenge or hub_challenge_alt

    if mode == "subscribe" and token == "mercadonativo_2026":
        return PlainTextResponse(content=str(challenge))

    raise HTTPException(status_code=403, detail="Falha na verificação")
