"""
Pagamentos com Mercado Pago (Checkout Transparente + Payment Brick).

- Crédito, débito e PIX no mesmo formulário (o "Brick" do Mercado Pago).
- O número do cartão é digitado num campo seguro do Mercado Pago e vira um "token";
  o nosso servidor nunca recebe nem guarda dados de cartão.
- Split: se o produtor conectou a conta Mercado Pago (OAuth), o pagamento é criado
  na conta dele com `application_fee` = comissão da plataforma. Sem conexão, o valor
  entra na conta da plataforma e o repasse fica registrado no extrato.

PAYMENT_MODE=simulado     -> funciona sem conta (apresentação). Nunca vale com APP_ENV=producao.
PAYMENT_MODE=mercadopago  -> API real (credenciais de teste TEST-... ou produção APP_USR-...)
Se PAYMENT_MODE=mercadopago e faltar credencial, os pagamentos ficam DESATIVADOS (nunca
caem para o modo simulado, que deixaria qualquer um "pagar" sem pagar).

Tolerância a falhas: cada chamada ao Mercado Pago tem tempo limite e novas tentativas em erro de
rede/5xx. Depois de algumas falhas seguidas o sistema considera o Mercado Pago fora do ar por um
tempo (MP_PAUSA_SEGUNDOS): as telas respondem na hora, o Pix de reserva aparece e as tarefas
automáticas reconsultam tudo quando ele voltar.
"""
import hashlib
import logging
import hmac
import re
import threading
import time
import unicodedata
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


class MPIndisponivel(PaymentError):
    """O Mercado Pago não respondeu (fora do ar, lento ou sem internet)."""


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
    referencia: str | None = None   # external_reference = código do pedido/assinatura
    taxa_mp: float | None = None    # taxa real cobrada pelo Mercado Pago (fee_details), quando informada


def modo_pagamento() -> str:
    """'mercadopago' (real), 'simulado' (demonstração) ou 'desativado' (configuração incompleta).

    O modo simulado só vale se for pedido de propósito (PAYMENT_MODE=simulado) e fora de produção.
    Qualquer outra configuração incompleta DESATIVA os pagamentos em vez de cair na simulação."""
    if settings.PAYMENT_MODE == "mercadopago":
        return "mercadopago" if settings.MP_ACCESS_TOKEN and settings.MP_PUBLIC_KEY else "desativado"
    if settings.PAYMENT_MODE == "simulado" and not settings.is_producao:
        return "simulado"
    return "desativado"


def aviso_configuracao() -> str | None:
    """Mensagem para a janela do backend quando a configuração de pagamentos está errada."""
    if modo_pagamento() != "desativado":
        if modo_pagamento() == "mercadopago" and not settings.MP_WEBHOOK_SECRET:
            return "MP_WEBHOOK_SECRET vazio: avisos do Mercado Pago chegam sem assinatura (configure no .env)."
        return None
    if settings.PAYMENT_MODE == "mercadopago":
        return "PAYMENT_MODE=mercadopago, mas falta MP_ACCESS_TOKEN ou MP_PUBLIC_KEY: pagamentos DESATIVADOS."
    if settings.PAYMENT_MODE == "simulado":
        return "PAYMENT_MODE=simulado não é permitido com APP_ENV=producao: pagamentos DESATIVADOS."
    return f"PAYMENT_MODE='{settings.PAYMENT_MODE}' não existe (use mercadopago ou simulado): pagamentos DESATIVADOS."


# ---------------- Disjuntor: o Mercado Pago está respondendo? ----------------
_circuito = {"falhas": 0, "aberto_ate": 0.0}
_circuito_lock = threading.Lock()


def mp_disponivel() -> bool:
    with _circuito_lock:
        return time.monotonic() >= _circuito["aberto_ate"]


def _registrar_sucesso() -> None:
    with _circuito_lock:
        _circuito["falhas"] = 0
        _circuito["aberto_ate"] = 0.0


def _registrar_falha() -> None:
    with _circuito_lock:
        _circuito["falhas"] += 1
        if _circuito["falhas"] >= settings.MP_FALHAS_PARA_PAUSAR:
            _circuito["aberto_ate"] = time.monotonic() + settings.MP_PAUSA_SEGUNDOS
            log.warning("Mercado Pago sem responder: pausando chamadas por %ss.", settings.MP_PAUSA_SEGUNDOS)


def resetar_circuito() -> None:  # usado nos testes
    _registrar_sucesso()


def _mp(metodo: str, caminho: str, token: str, *, json: dict | None = None, idem: str | None = None,
        repetir: bool = True) -> requests.Response:
    """Chamada ao Mercado Pago com tempo limite, novas tentativas e disjuntor.
    Só repete operações seguras: consultas e criações com X-Idempotency-Key (o MP não duplica)."""
    if not mp_disponivel():
        raise MPIndisponivel("O Mercado Pago está fora do ar agora. Tente de novo em alguns minutos.")
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["X-Idempotency-Key"] = idem
    tentativas = 1 + (settings.MP_TENTATIVAS if repetir else 0)
    for i in range(tentativas):
        try:
            kwargs = {"headers": headers, "timeout": settings.MP_TIMEOUT}
            if json is not None:
                kwargs["json"] = json
            resp = getattr(requests, metodo)(f"{MP_API}{caminho}", **kwargs)
        except requests.RequestException:
            resp = None
        if resp is not None and resp.status_code < 500 and resp.status_code != 429:
            _registrar_sucesso()
            return resp
        if i < tentativas - 1:
            time.sleep(min(2.0, 0.4 * (i + 1)))
    _registrar_falha()
    raise MPIndisponivel("Não foi possível falar com o Mercado Pago agora. Tente de novo em alguns minutos.")


def split_disponivel() -> bool:
    uri = settings.MP_REDIRECT_URI
    return bool(settings.MP_CLIENT_ID and settings.MP_CLIENT_SECRET
                and uri.startswith("https://") and "SEU-ENDERECO" not in uri)


def _ambiente_teste() -> bool:
    """Credenciais TEST-: o OAuth também precisa devolver tokens de teste (test_token)."""
    return settings.MP_ACCESS_TOKEN.startswith("TEST-")


def _moeda(valor: float | Decimal) -> float:
    return float(Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def percentual_taxa_mp(metodo: str | None) -> float:
    """Taxa estimada do Mercado Pago (%), pela tabela configurada. Usada quando a taxa real não veio."""
    return {"credit_card": settings.TAXA_MP_CREDITO, "debit_card": settings.TAXA_MP_DEBITO}.get(
        metodo or "pix", settings.TAXA_MP_PIX)


def estimar_taxa_mp(valor_total: float, metodo: str | None, gateway: str | None = "mercadopago") -> float:
    """Taxa do Mercado Pago em R$. Pix de reserva (gateway manual) cai direto na conta, sem taxa."""
    if gateway == "manual":
        return 0.0
    return _moeda(Decimal(str(valor_total)) * Decimal(str(percentual_taxa_mp(metodo))) / 100)


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
    taxas = [f for f in (dados.get("fee_details") or []) if f.get("type") == "mercadopago_fee"]
    taxa_mp = _moeda(sum(float(f.get("amount") or 0) for f in taxas)) if taxas else None
    return ResultadoPagamento(
        status=dados.get("status", "pending"),
        status_detalhe=dados.get("status_detail"),
        payment_id=str(dados.get("id")),
        metodo=metodo,
        parcelas=dados.get("installments"),
        pix_qr_code=transacao.get("qr_code"),
        pix_qr_base64=transacao.get("qr_code_base64"),
        split_aplicado=split,
        referencia=dados.get("external_reference"),
        taxa_mp=taxa_mp,
    )


def criar_pagamento(dados_brick: dict, *, valor: float, descricao: str, referencia: str,
                    producer=None, cobrar_comissao: bool = True) -> ResultadoPagamento:
    """
    Cria o pagamento a partir dos dados enviados pelo Payment Brick.
    O VALOR vem sempre do banco (parâmetro `valor`), nunca do navegador.
    """
    if modo_pagamento() != "mercadopago":
        raise PaymentError("Os pagamentos com cartão e Pix automático estão desativados no momento.")

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

    # Mesma chave em todas as tentativas: se a 1ª chegou ao MP e a resposta se perdeu, ele não cobra 2x
    resp = _mp("post", "/v1/payments", token, json=corpo, idem=str(uuid.uuid4()))
    if resp.status_code >= 400:
        # Só os campos que ajudam a achar o erro; o token do cartão e o e-mail ficam de fora
        log.warning("Pagamento recusado | valor=%s metodo=%s parcelas=%s emissor=%s split=%s",
                    corpo["transaction_amount"], metodo, corpo.get("installments"),
                    corpo.get("issuer_id"), "application_fee" in corpo)
    return _resultado(_ler_resposta(resp), split)


def consultar_pagamento(payment_id: str, producer=None) -> ResultadoPagamento | None:
    """Status atual do pagamento no Mercado Pago, ou None se não deu para saber agora."""
    if modo_pagamento() != "mercadopago" or not payment_id:
        return None
    token, _, split = credenciais_para(producer) if producer is not None else (settings.MP_ACCESS_TOKEN, None, False)
    try:
        resp = _mp("get", f"/v1/payments/{payment_id}", token)
        return _resultado(_ler_resposta(resp), split)
    except PaymentError:
        return None


def buscar_por_referencia(referencia: str, producer=None) -> ResultadoPagamento | None:
    """Acha o pagamento mais recente de um pedido pelo código (external_reference).
    Usado quando a cobrança chegou ao Mercado Pago mas a resposta se perdeu (queda de rede)."""
    if modo_pagamento() != "mercadopago" or not referencia:
        return None
    token, _, split = credenciais_para(producer) if producer is not None else (settings.MP_ACCESS_TOKEN, None, False)
    try:
        resp = _mp("get", "/v1/payments/search?" + urlencode(
            {"external_reference": referencia, "sort": "date_created", "criteria": "desc", "limit": 1}), token)
        resultados = (_ler_resposta(resp).get("results") or [])
    except PaymentError:
        return None
    return _resultado(resultados[0], split) if resultados else None


def _token_reembolso(producer, split: bool) -> str:
    token = settings.MP_ACCESS_TOKEN
    if split:
        token = _token_produtor(producer)
        if not token:
            raise PaymentError("A conta Mercado Pago do produtor está desconectada. Peça para ele conectar de novo.")
    return token


def reembolsar(payment_id: str, producer=None, split: bool = False) -> tuple[str, str]:
    """Devolve o valor TOTAL de um pagamento (Pix ou cartão). Retorna (id_da_devolucao, status).
    O status é o que o Mercado Pago informou ('approved', 'pending', 'in_process', 'rejected'...),
    ou '' se ele não informou. Quem chama decide o que fazer com cada um.

    No split, o pagamento foi criado na conta do produtor, então a devolução também sai de lá
    (o Mercado Pago devolve junto a comissão da plataforma). Sem split, sai da conta da plataforma.
    """
    if modo_pagamento() != "mercadopago":
        raise PaymentError("Pagamentos reais estão desativados.")
    token = _token_reembolso(producer, split)
    resp = _mp("post", f"/v1/payments/{payment_id}/refunds", token, json={}, idem=f"devolucao-{payment_id}")
    dados = _ler_resposta(resp)
    return str(dados.get("id") or ""), str(dados.get("status") or "").lower()


def consultar_reembolso(payment_id: str, reembolso_id: str, producer=None, split: bool = False) -> str | None:
    """Status atual de uma devolução ('approved', 'rejected'...), ou None se não deu para saber."""
    if modo_pagamento() != "mercadopago" or not payment_id or not reembolso_id:
        return None
    try:
        resp = _mp("get", f"/v1/payments/{payment_id}/refunds/{reembolso_id}", _token_reembolso(producer, split))
        return str(_ler_resposta(resp).get("status") or "").lower() or None
    except PaymentError:
        return None


def cancelar_pendente(payment_id: str, producer=None, split: bool = False) -> None:
    """Cancela um pagamento que ainda não foi pago (ex.: Pix gerado e não pago),
    para ninguém conseguir pagar um pedido que já foi cancelado."""
    if modo_pagamento() != "mercadopago":
        # Pagamentos desligados depois de gerar o Pix: não dá para garantir o cancelamento
        raise PaymentError("Os pagamentos estão desativados: não foi possível cancelar o Pix no Mercado Pago.")
    token = (_token_produtor(producer) if split else None) or settings.MP_ACCESS_TOKEN
    resp = _mp("put", f"/v1/payments/{payment_id}", token, json={"status": "cancelled"})
    _ler_resposta(resp)


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
    # mp_link_jti também: um link de conexão pendente deixa de valer
    for campo in ("mp_user_id", "mp_public_key", "mp_access_token_enc", "mp_refresh_token_enc",
                  "mp_token_expira", "mp_conectado_em", "mp_link_jti"):
        setattr(producer, campo, None)


# ---------------- Pix de reserva (quando o Mercado Pago está fora do ar) ----------------
def pix_reserva_disponivel() -> bool:
    """O Pix de reserva só existe com os pagamentos reais ligados e uma chave Pix configurada."""
    return modo_pagamento() in ("mercadopago", "desativado") and bool(settings.PIX_RESERVA_CHAVE)


def oferecer_pix_reserva() -> bool:
    """Mostrar o Pix de reserva agora? Só quando o Mercado Pago não pode ser usado."""
    return pix_reserva_disponivel() and (modo_pagamento() == "desativado" or not mp_disponivel())


def _campo(id_: str, valor: str) -> str:
    return f"{id_}{len(valor):02d}{valor}"


def _crc16(dados: str) -> str:
    crc = 0xFFFF
    for byte in dados.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _ascii(texto: str, limite: int) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9 .\-]", "", sem_acento).upper().strip()[:limite] or "MERCADO NATIVO"[:limite]


def pix_copia_e_cola(valor: float, identificador: str) -> str:
    """Código "Pix Copia e Cola" (padrão BR Code do Banco Central) com valor e identificação do pedido."""
    txid = re.sub(r"[^A-Za-z0-9]", "", identificador)[:25] or "***"
    conta = _campo("00", "br.gov.bcb.pix") + _campo("01", settings.PIX_RESERVA_CHAVE)
    payload = (
        _campo("00", "01")
        + _campo("26", conta)
        + _campo("52", "0000")
        + _campo("53", "986")
        + _campo("54", f"{_moeda(valor):.2f}")
        + _campo("58", "BR")
        + _campo("59", _ascii(settings.PIX_RESERVA_NOME, 25))
        + _campo("60", _ascii(settings.PIX_RESERVA_CIDADE, 15))
        + _campo("62", _campo("05", txid))
        + "6304"
    )
    return payload + _crc16(payload)


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
