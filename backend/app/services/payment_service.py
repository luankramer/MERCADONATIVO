"""
Pagamentos com Mercado Pago (Checkout Transparente + Payment Brick).

- Crédito, débito e PIX no mesmo formulário (o "Brick" do Mercado Pago).
- O número do cartão é digitado num campo seguro do Mercado Pago e vira um "token";
  o nosso servidor nunca recebe nem guarda dados de cartão.
- Split: se o produtor conectou a conta Mercado Pago (OAuth), o pagamento é criado
  na conta dele com `application_fee` = comissão da plataforma. Sem conexão, o valor
  entra na conta da plataforma e o repasse fica registrado no extrato.

PAYMENT_MODE=simulado     -> funciona sem conta (apresentação)
PAYMENT_MODE=mercadopago  -> API real (credenciais de teste TEST-... ou produção APP_USR-...)
"""
import hashlib
import logging
import hmac
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import urlencode

import requests

from app.core.config import settings
from app.core.crypto import criptografar, descriptografar

log = logging.getLogger("mercado_nativo")
MP_API = "https://api.mercadopago.com"
MP_AUTH = "https://auth.mercadopago.com/authorization"


class PaymentError(Exception):
    pass


@dataclass
class ResultadoPagamento:
    status: str                 # approved | pending | in_process | rejected | cancelled
    status_detalhe: str | None
    payment_id: str
    metodo: str                 # pix | credit_card | debit_card
    parcelas: int | None = None
    pix_qr_code: str | None = None
    pix_qr_base64: str | None = None
    split_aplicado: bool = False


def modo_pagamento() -> str:
    if settings.PAYMENT_MODE == "mercadopago" and settings.MP_ACCESS_TOKEN and settings.MP_PUBLIC_KEY:
        return "mercadopago"
    return "simulado"


def split_disponivel() -> bool:
    uri = settings.MP_REDIRECT_URI
    return bool(settings.MP_CLIENT_ID and settings.MP_CLIENT_SECRET
                and uri.startswith("https://") and "SEU-ENDERECO" not in uri)


def _ambiente_teste() -> bool:
    """Credenciais TEST-: o OAuth também precisa devolver tokens de teste (test_token)."""
    return settings.MP_ACCESS_TOKEN.startswith("TEST-")


def _moeda(valor: float | Decimal) -> float:
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calcular_split(valor_total: float) -> tuple[float, float]:
    """Retorna (taxa_plataforma, valor_produtor)."""
    taxa = _moeda(Decimal(str(valor_total)) * Decimal(str(settings.PLATFORM_FEE_PERCENT)) / 100)
    return taxa, _moeda(Decimal(str(valor_total)) - Decimal(str(taxa)))


# ---------------- Credenciais ----------------
def _token_produtor(producer) -> str | None:
    """Access token do produtor (renova automaticamente se estiver perto de expirar)."""
    if not producer or not producer.mp_conectado:
        return None
    if producer.mp_token_expira and producer.mp_token_expira < datetime.utcnow() + timedelta(days=2):
        try:
            _renovar_token(producer)
        except PaymentError:
            return None
    return descriptografar(producer.mp_access_token_enc)


def credenciais_para(producer=None) -> tuple[str, str, bool]:
    """(access_token, public_key, split) usados para cobrar um pedido deste produtor."""
    token = _token_produtor(producer)
    if token:
        return token, producer.mp_public_key, True
    return settings.MP_ACCESS_TOKEN, settings.MP_PUBLIC_KEY, False


def public_key_para(producer=None) -> str | None:
    # No split, o formulário do cartão usa a Public Key da plataforma (integrador) e o
    # pagamento é criado com o Access Token do produtor (documentação do Split 1:1).
    if modo_pagamento() != "mercadopago":
        return None
    return settings.MP_PUBLIC_KEY


# ---------------- Criação e consulta de pagamentos ----------------
def _ler_resposta(resp: requests.Response) -> dict:
    try:
        dados = resp.json()
    except ValueError:
        dados = {}
    if resp.status_code >= 400:
        causas = dados.get("cause") if isinstance(dados.get("cause"), list) else []
        # A resposta de erro não traz dados de cartão nem tokens: pode ir para a janela do backend
        log.warning("Mercado Pago HTTP %s | %s | causas=%s", resp.status_code,
                    dados.get("message") or dados.get("error"), causas)
        causa = causas[0] if causas else {}
        texto = causa.get("description") or dados.get("message") or resp.status_code
        codigo = f" (código {causa['code']})" if causa.get("code") else ""
        raise PaymentError(f"Mercado Pago recusou a operação: {texto}{codigo}")
    return dados


def _resultado(dados: dict, split: bool) -> ResultadoPagamento:
    metodo = dados.get("payment_type_id") or "pix"
    if metodo == "bank_transfer":
        metodo = "pix"
    transacao = (dados.get("point_of_interaction") or {}).get("transaction_data") or {}
    return ResultadoPagamento(
        status=dados.get("status", "pending"),
        status_detalhe=dados.get("status_detail"),
        payment_id=str(dados.get("id")),
        metodo=metodo,
        parcelas=dados.get("installments"),
        pix_qr_code=transacao.get("qr_code"),
        pix_qr_base64=transacao.get("qr_code_base64"),
        split_aplicado=split,
    )


def criar_pagamento(dados_brick: dict, *, valor: float, descricao: str, referencia: str,
                    producer=None, cobrar_comissao: bool = True) -> ResultadoPagamento:
    """
    Cria o pagamento a partir dos dados enviados pelo Payment Brick.
    O VALOR vem sempre do banco (parâmetro `valor`), nunca do navegador.
    """
    if modo_pagamento() != "mercadopago":
        raise PaymentError("Pagamentos reais estão desativados (PAYMENT_MODE=simulado).")

    token, _, split = credenciais_para(producer) if producer is not None else (settings.MP_ACCESS_TOKEN, None, False)
    metodo = dados_brick.get("payment_method_id")
    if not metodo:
        raise PaymentError("Forma de pagamento não informada.")

    pagador = dados_brick.get("payer") or {}
    corpo = {
        "transaction_amount": _moeda(valor),
        "description": descricao[:250],
        "external_reference": referencia,
        "payment_method_id": metodo,
        "payer": {
            "email": pagador.get("email"),
            "identification": pagador.get("identification"),
        },
        "metadata": {"referencia": referencia},
    }
    if metodo != "pix":
        # Cartão: token gerado pelo Mercado Pago no navegador (sem dados do cartão aqui)
        if not dados_brick.get("token"):
            raise PaymentError("Dados do cartão incompletos.")
        corpo.update({
            "token": dados_brick["token"],
            "installments": int(dados_brick.get("installments") or 1),
            "issuer_id": dados_brick.get("issuer_id"),
        })
    if split and cobrar_comissao:
        taxa, _ = calcular_split(valor)
        corpo["application_fee"] = taxa
    if settings.PUBLIC_API_URL.startswith("https://"):
        corpo["notification_url"] = f"{settings.PUBLIC_API_URL}/api/v1/checkout/webhook/mercadopago"

    try:
        resp = requests.post(
            f"{MP_API}/v1/payments", json=corpo, timeout=30,
            headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": str(uuid.uuid4())},
        )
    except requests.RequestException:
        raise PaymentError("Não foi possível falar com o Mercado Pago. Tente novamente.")
    if resp.status_code >= 400:
        # Só os campos que ajudam a achar o erro; o token do cartão e o e-mail ficam de fora
        log.warning("Pagamento recusado | valor=%s metodo=%s parcelas=%s emissor=%s split=%s",
                    corpo["transaction_amount"], metodo, corpo.get("installments"),
                    corpo.get("issuer_id"), "application_fee" in corpo)
    return _resultado(_ler_resposta(resp), split)


def consultar_pagamento(payment_id: str, producer=None) -> ResultadoPagamento | None:
    if modo_pagamento() != "mercadopago" or not payment_id:
        return None
    token, _, split = credenciais_para(producer) if producer is not None else (settings.MP_ACCESS_TOKEN, None, False)
    try:
        resp = requests.get(f"{MP_API}/v1/payments/{payment_id}", timeout=15,
                            headers={"Authorization": f"Bearer {token}"})
        return _resultado(_ler_resposta(resp), split)
    except (requests.RequestException, PaymentError):
        return None


# ---------------- OAuth: conectar a conta Mercado Pago do produtor ----------------
def url_conexao(state: str) -> str:
    if not split_disponivel():
        raise PaymentError("Split não configurado: preencha MP_CLIENT_ID, MP_CLIENT_SECRET e MP_REDIRECT_URI no .env.")
    return f"{MP_AUTH}?" + urlencode({
        "client_id": settings.MP_CLIENT_ID, "response_type": "code", "platform_id": "mp",
        "state": state, "redirect_uri": settings.MP_REDIRECT_URI,
    })


def _salvar_tokens(producer, dados: dict) -> None:
    producer.mp_user_id = str(dados.get("user_id") or "")
    producer.mp_public_key = dados.get("public_key")
    producer.mp_access_token_enc = criptografar(dados.get("access_token"))
    producer.mp_refresh_token_enc = criptografar(dados.get("refresh_token"))
    producer.mp_token_expira = datetime.utcnow() + timedelta(seconds=int(dados.get("expires_in") or 15552000))
    producer.mp_conectado_em = producer.mp_conectado_em or datetime.utcnow()


def trocar_codigo(producer, code: str) -> None:
    try:
        resp = requests.post(f"{MP_API}/oauth/token", timeout=20, json={
            "client_id": settings.MP_CLIENT_ID, "client_secret": settings.MP_CLIENT_SECRET,
            "grant_type": "authorization_code", "code": code, "redirect_uri": settings.MP_REDIRECT_URI,
            **({"test_token": "true"} if _ambiente_teste() else {}),
        })
    except requests.RequestException:
        raise PaymentError("Não foi possível falar com o Mercado Pago.")
    _salvar_tokens(producer, _ler_resposta(resp))


def _renovar_token(producer) -> None:
    refresh = descriptografar(producer.mp_refresh_token_enc)
    if not refresh:
        raise PaymentError("Conexão expirada.")
    try:
        resp = requests.post(f"{MP_API}/oauth/token", timeout=20, json={
            "client_id": settings.MP_CLIENT_ID, "client_secret": settings.MP_CLIENT_SECRET,
            "grant_type": "refresh_token", "refresh_token": refresh,
            **({"test_token": "true"} if _ambiente_teste() else {}),
        })
    except requests.RequestException:
        raise PaymentError("Não foi possível renovar a conexão.")
    _salvar_tokens(producer, _ler_resposta(resp))


def desconectar(producer) -> None:
    for campo in ("mp_user_id", "mp_public_key", "mp_access_token_enc", "mp_refresh_token_enc",
                  "mp_token_expira", "mp_conectado_em"):
        setattr(producer, campo, None)


# ---------------- Webhook ----------------
def assinatura_valida(x_signature: str | None, x_request_id: str | None, data_id: str | None) -> bool:
    """Valida o cabeçalho x-signature enviado pelo Mercado Pago (HMAC-SHA256)."""
    if not settings.MP_WEBHOOK_SECRET:
        return True  # sem segredo configurado, a proteção é a reconsulta do pagamento na API
    if not x_signature:
        return False
    partes = dict(p.split("=", 1) for p in x_signature.split(",") if "=" in p)
    ts, v1 = partes.get("ts"), partes.get("v1")
    if not ts or not v1:
        return False
    manifesto = ""
    if data_id:
        manifesto += f"id:{data_id.lower()};"
    if x_request_id:
        manifesto += f"request-id:{x_request_id};"
    manifesto += f"ts:{ts};"
    esperado = hmac.new(settings.MP_WEBHOOK_SECRET.encode(), manifesto.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, v1)
