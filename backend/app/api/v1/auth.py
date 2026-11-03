"""Cadastro e login do produtor (código de acesso enviado pelo WhatsApp, sem senha).

Proteções do código de acesso:
- Cada pedido de código gera um "desafio" que fica com quem pediu. Outra pessoa pedindo um
  código para o mesmo número NÃO apaga nem troca o código do produtor, e errar o código de
  outro desafio não afeta o dele.
- Limites: por IP, por número+IP e por número (para ninguém encher o WhatsApp do produtor).
- No máximo 5 erros por código e 30 erros por número a cada 24 h (somando todos os códigos):
  adivinhar o código fica inviável mesmo ao longo de meses.
- Reserva: se o WhatsApp estiver fora do ar, o código vai para o e-mail cadastrado.
"""
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import ip_cliente, limitar, limpar, registrar, verificar
from app.core.security import token_produtor
from app.db.database import get_db
from app.models.user_model import Producer
from app.schemas.user import LoginWhatsApp, ProducerCreate, VerifyOTP
from app.services import email_service, geo_service
from app.services.whatsapp_service import enviar_codigo, numero_nacional, numero_valido

router = APIRouter()

# Códigos em memória: {desafio: {"numero", "code", "expira", "tentativas"}}
otp_storage: dict[str, dict] = {}
MAX_CODIGOS_ATIVOS = 5           # por número, ao mesmo tempo
MAX_ERROS_POR_CODIGO = 5
MAX_ERROS_POR_NUMERO_DIA = 30


def _limpar_vencidos() -> None:
    agora = datetime.utcnow()
    for d in [d for d, r in otp_storage.items() if r["expira"] < agora]:
        otp_storage.pop(d, None)


def _ativos(numero: str) -> int:
    return sum(1 for r in otp_storage.values() if r["numero"] == numero)


def novo_codigo() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def texto_codigo(code: str) -> str:
    return (f"🍃 *Mercado Nativo*\n\nSeu código de acesso é: *{code}*\n\n"
            f"Ele vale por {settings.OTP_EXPIRE_MINUTES} minutos. Não compartilhe com ninguém.")


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
    if not numero_valido(numero):  # antes de qualquer limite: número absurdo não vira chave na memória
        raise HTTPException(400, "WhatsApp inválido. Use DDD + número, ex.: (68) 9 9999-9999.")
    ip = ip_cliente(request)
    # Evita envio em massa: por IP, por número+IP (quem pede) e por número (proteção do produtor)
    registrar(f"otp-ip:{ip}", 10, 600)
    registrar(f"otp-num-ip:{numero}:{ip}", 3, 600)
    registrar(f"otp-num:{numero}", 10, 3600)
    verificar(f"otp-falhas:{numero}", MAX_ERROS_POR_NUMERO_DIA, 86400)

    produtor = buscar_por_whatsapp(db, numero)
    if not produtor:
        raise HTTPException(404, "Este WhatsApp ainda não tem cadastro. Crie sua conta de produtor.")

    _limpar_vencidos()
    if _ativos(numero) >= MAX_CODIGOS_ATIVOS:
        raise HTTPException(429, "Já enviamos vários códigos para este número. Use o último que chegou ou aguarde 5 minutos.")
    code = novo_codigo()
    desafio = secrets.token_urlsafe(18)
    otp_storage[desafio] = {
        "numero": numero, "code": code, "tentativas": 0,
        "expira": datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    }
    resposta = {"desafio": desafio, "enviado": True}

    if req.canal == "whatsapp" and await enviar_codigo(numero, code, texto_codigo(code)):
        return {**resposta, "canal": "whatsapp", "message": "Código enviado pelo WhatsApp."}
    # Reserva: e-mail cadastrado (escolhido pelo produtor ou porque o WhatsApp falhou)
    if produtor.email and email_service.email_configurado() and email_service.enviar_email(
            produtor.email, "Seu código de acesso — Mercado Nativo",
            f"Seu código de acesso ao Mercado Nativo é: {code}\n\n"
            f"Ele vale por {settings.OTP_EXPIRE_MINUTES} minutos. Não compartilhe com ninguém.\n"
            "Se não foi você que pediu, ignore este e-mail."):
        aviso = "" if req.canal == "email" else "O WhatsApp está fora do ar. "
        return {**resposta, "canal": "email",
                "message": f"{aviso}Enviamos o código para o e-mail {email_service.mascarar(produtor.email)}."}

    if settings.OTP_DEV_MODE:
        # O código NUNCA vai para o navegador: aparece apenas no terminal de quem roda o servidor
        print(f"\n🔑 [MODO DESENVOLVIMENTO] WhatsApp indisponível. Código para {numero}: {code}\n")
        return {**resposta, "enviado": False, "canal": "terminal",
                "message": "WhatsApp indisponível. Veja o código no terminal do backend."}
    otp_storage.pop(desafio, None)
    if req.canal == "email":
        raise HTTPException(400, "Não há e-mail cadastrado nesta conta (ou o envio por e-mail não está ativo).")
    raise HTTPException(502, "Não conseguimos enviar o código pelo WhatsApp agora. Tente em instantes.")


@router.post("/producer/verify-code")
async def verify_code(req: VerifyOTP, request: Request, db: Session = Depends(get_db)):
    numero = numero_nacional(req.whatsapp)
    registrar(f"otp-verificar:{ip_cliente(request)}", 20, 600)
    verificar(f"otp-falhas:{numero}", MAX_ERROS_POR_NUMERO_DIA, 86400)
    registro = otp_storage.get(req.desafio)
    if not registro or registro["numero"] != numero:
        raise HTTPException(401, "Código expirado. Solicite um novo.")
    if datetime.utcnow() > registro["expira"]:
        otp_storage.pop(req.desafio, None)
        raise HTTPException(401, "Código expirado. Solicite um novo.")
    if not hmac.compare_digest(registro["code"].encode(), (req.code or "").strip().encode()):
        registro["tentativas"] += 1
        # Conta também no total do número (24 h), somando todos os códigos pedidos
        registrar(f"otp-falhas:{numero}", MAX_ERROS_POR_NUMERO_DIA, 86400)
        if registro["tentativas"] >= MAX_ERROS_POR_CODIGO:
            otp_storage.pop(req.desafio, None)
            raise HTTPException(429, "Muitas tentativas. Solicite um novo código.")
        raise HTTPException(401, "Código incorreto.")

    otp_storage.pop(req.desafio, None)
    produtor = buscar_por_whatsapp(db, numero)
    if not produtor:
        raise HTTPException(404, "Produtor não encontrado.")
    limpar(f"otp-falhas:{numero}")
    return {
        "access_token": token_produtor(produtor),
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
