"""Checkout transparente: crédito, débito ou PIX com split produtor/plataforma."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.rate_limit import limitar
from app.db.database import get_db
from app.models.order_model import METODOS, PEDIDO_AGUARDANDO, Order, OrderItem, PremiumSubscription
from app.models.product_model import STATUS_APROVADO, Product
from app.schemas.order import CancelamentoCliente, CheckoutCreate, PagamentoBrick, PagamentoSimulado
from app.services import cancelamento_service, payment_service, tarefas_service
from app.services.checkout_service import (
    confirmar_pix_simulado, escolher_pix_reserva, exigir_vendavel, informar_pix_reserva, pagar_com_brick,
    pagar_simulado, sincronizar,
)
from app.services.order_service import aplicar_status
from app.services.whatsapp_service import link_whatsapp, numero_nacional, texto_seguro

router = APIRouter(prefix="/api/v1/checkout", tags=["Checkout"])


def _pedido(db: Session, codigo: str) -> Order:
    pedido = db.query(Order).filter(Order.codigo == codigo).first() if 16 <= len(codigo) <= 40 else None
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    return pedido


def _pedido_publico(o: Order) -> dict:
    """Dados que o próprio comprador vê (sem telefone nem e-mail)."""
    produtor = o.producer
    item = o.itens[0] if o.itens else None
    mensagem = f"Olá! Sou {o.consumidor_nome}, fiz um pedido no Mercado Nativo ({item.quantidade}x {item.nome_produto}). Como combinamos a retirada?" if item else ""
    pago = o.status not in (PEDIDO_AGUARDANDO, "cancelado")
    aguardando = o.status == PEDIDO_AGUARDANDO
    return {
        "codigo": o.codigo,
        "numero": o.id,
        "status": o.status,
        "status_detalhe": o.status_detalhe,
        "gateway": o.gateway,
        "modo": payment_service.modo_pagamento(),
        "mp_disponivel": payment_service.mp_disponivel(),
        # Pix de reserva: aparece quando o Mercado Pago está fora (ou já foi escolhido para este pedido)
        "pix_reserva": aguardando and (o.gateway == "manual" or payment_service.oferecer_pix_reserva()),
        "reserva_informado": bool(o.reserva_informado_em),
        "public_key": payment_service.public_key_para(produtor),
        "metodo": o.metodo,
        "metodo_nome": METODOS.get(o.metodo or "", None),
        "parcelas": o.parcelas,
        "produto": item.nome_produto if item else None,
        "product_id": item.product_id if item else None,
        "quantidade": item.quantidade if item else 0,
        "preco_unitario": item.preco_unitario if item else 0,
        "valor_total": o.valor_total,
        # A divisão (repasse/comissão) é assunto do produtor e do admin: não vai para o comprador
        "pix_qr_code": o.pix_qr_code if aguardando else None,
        "pix_qr_base64": o.pix_qr_base64 if aguardando else None,
        "cliente": o.consumidor_nome.split(" ")[0],
        "produtor": {"id": produtor.id, "nome_loja": produtor.business_name, "cidade": produtor.city,
                     "estado": produtor.uf,
                     # endereço de retirada só depois de pago e se o produtor deixou público
                     "endereco": produtor.address if pago and produtor.endereco_publico else None} if produtor else None,
        "whatsapp_link": link_whatsapp(produtor.whatsapp, mensagem)
                         if produtor and produtor.whatsapp and pago and o.status != "cancelado" else None,
        "pode_cancelar": cancelamento_service.pode_cancelar(o, "cliente"),
        **cancelamento_service.resumo(o),
    }


@router.get("/config")
def config():
    return {
        "modo": payment_service.modo_pagamento(),
        "mp_disponivel": payment_service.mp_disponivel(),
        "pix_reserva": payment_service.oferecer_pix_reserva(),
        "percentual_plataforma": settings.PLATFORM_FEE_PERCENT,
        "preco_premium": settings.PREMIUM_PRICE,
        "split_disponivel": payment_service.split_disponivel(),
    }


@router.post("", status_code=201, dependencies=[Depends(limitar("checkout", 20, 3600))])
def criar_pedido(req: CheckoutCreate, db: Session = Depends(get_db)):
    produto = db.get(Product, req.product_id)
    if not produto or produto.status != STATUS_APROVADO or not produto.producer or produto.producer.ativo is False:
        raise HTTPException(404, "Produto indisponível.")
    if (produto.estoque or 0) < req.quantidade:
        raise HTTPException(400, f"Estoque insuficiente. Disponível: {produto.estoque or 0} unidade(s).")
    whatsapp = numero_nacional(req.whatsapp)
    if len(whatsapp) not in (10, 11):
        raise HTTPException(400, "WhatsApp inválido.")
    # O nome aparece em mensagens do número oficial: sem links nem formatação
    nome = texto_seguro(req.nome, 150)
    if len(nome) < 2:
        raise HTTPException(400, "Informe o seu nome.")

    total = round(produto.preco * req.quantidade, 2)
    taxa, repasse = payment_service.calcular_split(total)
    pedido = Order(
        producer_id=produto.producer_id, consumidor_nome=nome, consumidor_whatsapp=whatsapp,
        valor_total=total, taxa_plataforma=taxa, valor_produtor=repasse, status=PEDIDO_AGUARDANDO,
        gateway=payment_service.modo_pagamento(),
    )
    pedido.itens.append(OrderItem(product_id=produto.id, nome_produto=produto.nome,
                                  quantidade=req.quantidade, preco_unitario=produto.preco))
    db.add(pedido)
    # Início de compra conta como contato (métrica de conversão)
    produto.contatos_whatsapp = (produto.contatos_whatsapp or 0) + 1
    db.commit()
    db.refresh(pedido)
    return _pedido_publico(pedido)


@router.get("/{codigo}")
def status_pedido(codigo: str, db: Session = Depends(get_db)):
    pedido = _pedido(db, codigo)
    sincronizar(db, pedido, pedido.producer)
    return _pedido_publico(pedido)


@router.post("/{codigo}/pagar", dependencies=[Depends(limitar("pagar", 10, 600))])
def pagar(codigo: str, dados: PagamentoBrick, db: Session = Depends(get_db)):
    pedido = _pedido(db, codigo)
    exigir_vendavel(db, pedido)
    item = pedido.itens[0]
    pagar_com_brick(db, pedido, dados, valor=pedido.valor_total,
                    descricao=f"{item.quantidade}x {item.nome_produto} — Mercado Nativo", producer=pedido.producer)
    db.refresh(pedido)
    return _pedido_publico(pedido)


@router.post("/{codigo}/cancelar", dependencies=[Depends(limitar("cancelar", 5, 600))])
def cancelar_pedido(codigo: str, dados: CancelamentoCliente, db: Session = Depends(get_db)):
    """Não pago: o cliente cancela na hora. Pago: vira um PEDIDO de cancelamento, que a equipe
    analisa com o produtor (o produto pode já ter sido entregue ou enviado) antes de devolver."""
    pedido = _pedido(db, codigo)
    if "".join(c for c in (pedido.consumidor_whatsapp or "") if c.isdigit())[-4:] != dados.whatsapp_final:
        raise HTTPException(403, "Os números não conferem com o WhatsApp usado na compra.")
    try:
        if cancelamento_service.pode_cancelar(pedido, "cliente"):
            cancelamento_service.cancelar(db, pedido, "cliente", dados.motivo)
        else:
            cancelamento_service.solicitar(db, pedido, dados.motivo)
    except cancelamento_service.CancelamentoError as e:
        raise HTTPException(400, str(e))
    return _pedido_publico(pedido)


@router.post("/{codigo}/simular", dependencies=[Depends(limitar("simular", 20, 600))])
def simular(codigo: str, dados: PagamentoSimulado, db: Session = Depends(get_db)):
    """Modo de demonstração: simula crédito, débito ou PIX (só com PAYMENT_MODE=simulado e fora de produção)."""
    pedido = _pedido(db, codigo)
    exigir_vendavel(db, pedido)
    pagar_simulado(db, pedido, dados)
    db.refresh(pedido)
    return _pedido_publico(pedido)


@router.post("/{codigo}/simular/confirmar-pix", dependencies=[Depends(limitar("simular", 20, 600))])
def simular_confirmar_pix(codigo: str, db: Session = Depends(get_db)):
    pedido = _pedido(db, codigo)
    exigir_vendavel(db, pedido)
    confirmar_pix_simulado(db, pedido)
    db.refresh(pedido)
    return _pedido_publico(pedido)


# ---------------- Pix de reserva (Mercado Pago fora do ar) ----------------
@router.post("/{codigo}/pix-reserva", dependencies=[Depends(limitar("pix_reserva", 10, 600))])
def pix_reserva(codigo: str, db: Session = Depends(get_db)):
    """Gera o Pix Copia e Cola da conta da plataforma. A equipe confere e confirma o pedido."""
    pedido = _pedido(db, codigo)
    exigir_vendavel(db, pedido)
    escolher_pix_reserva(db, pedido)
    db.refresh(pedido)
    return _pedido_publico(pedido)


@router.post("/{codigo}/pix-reserva/paguei", dependencies=[Depends(limitar("pix_reserva", 10, 600))])
def pix_reserva_paguei(codigo: str, db: Session = Depends(get_db)):
    """O cliente avisa que já pagou: o pedido entra na lista de conferência da equipe."""
    pedido = _pedido(db, codigo)
    informar_pix_reserva(db, pedido)
    db.refresh(pedido)
    return _pedido_publico(pedido)


@router.post("/webhook/mercadopago", dependencies=[Depends(limitar("webhook", 300, 60))])
async def webhook_mercadopago(request: Request, db: Session = Depends(get_db)):
    """
    Configure no painel do Mercado Pago (Suas integrações > Webhooks) o evento "Pagamentos"
    apontando para PUBLIC_API_URL/api/v1/checkout/webhook/mercadopago.

    Se a API do Mercado Pago não responder na hora, o aviso vai para uma fila e é
    reprocessado pelas tarefas automáticas: nenhum pagamento fica sem confirmação.
    """
    try:
        corpo = await request.json()
    except ValueError:
        corpo = {}
    if not isinstance(corpo, dict):
        corpo = {}
    data_id = request.query_params.get("data.id") or str((corpo.get("data") or {}).get("id") or "")
    data_id = data_id.strip()[:40]
    if not payment_service.assinatura_valida(request.headers.get("x-signature"),
                                             request.headers.get("x-request-id"), data_id):
        raise HTTPException(401, "Assinatura inválida")
    if (corpo.get("type") or request.query_params.get("type")) != "payment" or not data_id:
        return {"ok": True}

    # Nunca confiamos no conteúdo da notificação: o status é reconsultado na API do Mercado Pago.
    # A consulta roda fora do loop principal para um Mercado Pago lento não travar o servidor.
    if not await run_in_threadpool(tarefas_service.processar_notificacao, db, data_id):
        tarefas_service.enfileirar_notificacao(db, data_id)
    return {"ok": True}
