"""
Conexão do produtor com o Mercado Pago, pensada para quem tem pouca familiaridade com tecnologia.

- Link pelo WhatsApp: o produtor (ou a equipe, pelo painel admin) pede um link que chega no
  WhatsApp dele. Ele abre no celular, onde o app do Mercado Pago costuma estar logado, e só
  toca em "Autorizar". Não precisa entrar no Mercado Nativo nem lembrar senha.
- O link vale 24 horas e só funciona uma vez (fica sem efeito depois da conexão ou se outro
  link for pedido). Ele só é enviado para o WhatsApp cadastrado do produtor.
- Depois de conectar, o produtor recebe uma confirmação no WhatsApp (se não foi ele, avisa).
"""
import html
import logging
import secrets
from datetime import timedelta

from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.security import create_access_token
from app.services import payment_service
from app.services.whatsapp_service import enviar_mensagem_openwa

log = logging.getLogger("mercado_nativo")

VALIDADE_LINK = timedelta(hours=24)


class ConexaoError(Exception):
    pass


def gerar_link(produtor) -> str:
    """Cria um link novo de conexão (o anterior deixa de valer)."""
    if not payment_service.split_disponivel():
        raise ConexaoError("A conexão com o Mercado Pago ainda não foi habilitada pela plataforma.")
    if not settings.PUBLIC_API_URL.startswith("https://"):
        raise ConexaoError("Preencha PUBLIC_API_URL (endereço HTTPS do backend) para enviar o link.")
    jti = secrets.token_urlsafe(12)
    produtor.mp_link_jti = jti
    token = create_access_token(produtor.id, "mp_link", VALIDADE_LINK, extra={"jti": jti})
    return f"{settings.PUBLIC_API_URL}/api/v1/mercadopago/conectar/{token}"


async def enviar_link_whatsapp(produtor) -> bool:
    """Manda o link para o WhatsApp do produtor. Retorna False se não conseguiu enviar."""
    if not produtor.whatsapp:
        raise ConexaoError("Este produtor não tem WhatsApp cadastrado.")
    link = gerar_link(produtor)
    nome = (produtor.name or "").split(" ")[0] or "produtor"
    texto = (
        f"🍃 *Mercado Nativo*\n\nOlá, {nome}! Para receber o dinheiro das suas vendas direto na sua "
        f"conta Mercado Pago, toque no link abaixo:\n\n{link}\n\n"
        "1. Vai abrir o Mercado Pago.\n"
        "2. Se pedir para entrar, escolha receber um *código pelo WhatsApp ou SMS* (não precisa de senha).\n"
        "3. Toque em *Autorizar*. Pronto!\n\n"
        "O link vale por 24 horas. Se você não pediu este link, é só ignorar."
    )
    enviado = await enviar_mensagem_openwa(produtor.whatsapp, texto)
    if not enviado and settings.OTP_DEV_MODE:
        # Desenvolvimento sem WhatsApp configurado: mostra o link só na janela do backend
        log.warning("[DEV] Link de conexão Mercado Pago do produtor %s: %s", produtor.id, link)
    return enviado


async def avisar_conexao(produtor) -> None:
    if produtor.whatsapp:
        await enviar_mensagem_openwa(
            produtor.whatsapp,
            "🍃 *Mercado Nativo*\n\nSua conta Mercado Pago foi conectada! A partir de agora, "
            f"{100 - settings.PLATFORM_FEE_PERCENT:g}% de cada venda cai direto nela.\n\n"
            "Não foi você? Fale com a equipe do Mercado Nativo respondendo esta mensagem.",
        )


def pagina(titulo: str, texto: str, ok: bool = True) -> HTMLResponse:
    """Página simples (letra grande) para quem conectou pelo celular a partir do WhatsApp."""
    cor = "#0B6B4A" if ok else "#9A4A1E"
    simbolo = "✓" if ok else "!"
    corpo = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Mercado Nativo</title>
<style>body{{margin:0;font-family:system-ui,Arial,sans-serif;background:#FBFAF6;color:#14231C;
display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px;box-sizing:border-box}}
main{{max-width:440px;text-align:center}}.s{{width:88px;height:88px;border-radius:50%;background:{cor};color:#fff;
font-size:52px;line-height:88px;margin:0 auto 20px}}h1{{font-size:28px;margin:0 0 12px;color:{cor}}}
p{{font-size:20px;line-height:1.5;margin:0}}</style></head>
<body><main><div class="s">{simbolo}</div><h1>{html.escape(titulo)}</h1><p>{html.escape(texto)}</p></main></body></html>"""
    return HTMLResponse(corpo, status_code=200 if ok else 400)
