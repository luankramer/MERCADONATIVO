"""Painel administrativo: visão geral, curadoria de publicações e Vitrine Premium."""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.rate_limit import limitar
from app.core.security import get_current_admin, get_super_admin
from app.db.database import get_db
from app.models.order_model import METODOS, PEDIDO_AGUARDANDO, PEDIDO_PAGO, PEDIDO_RETIRADO, Order, PremiumSubscription
from app.models.product_model import STATUS_APROVADO, STATUS_PENDENTE, STATUS_REJEITADO, Product
from app.models.user_model import Producer
from app.schemas.admin import PremiumUpdate
from app.schemas.order import CancelamentoMotivo
from app.schemas.product import DestaqueUpdate, RejectRequest
from app.services.curadoria_service import analisar_produto
from app.services.remocao_service import remover_produto, remover_produtor
from app.services.serializer_service import product_admin
from app.services import cancelamento_service, conexao_mp_service, tarefas_service
from app.services.order_service import confirmar_pedido
from app.services.whatsapp_service import enviar_mensagem_openwa

log = logging.getLogger("mercado_nativo.admin")

router = APIRouter(prefix="/api/v1/admin", tags=["Painel Administrativo"], dependencies=[Depends(get_current_admin)])


def _tempo_relativo(data: datetime | None) -> str:
    if not data:
        return ""
    segundos = int((datetime.utcnow() - data).total_seconds())
    if segundos < 60:
        return "Agora"
    if segundos < 3600:
        return f"Há {segundos // 60} min"
    if segundos < 86400:
        horas = segundos // 3600
        return f"Há {horas} hora{'s' if horas > 1 else ''}"
    dias = segundos // 86400
    return f"Há {dias} dia{'s' if dias > 1 else ''}"


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    pendentes = db.query(Product).filter(Product.status == STATUS_PENDENTE).count()
    ativos = db.query(Product).filter(Product.status == STATUS_APROVADO).count()
    produtores = db.query(Producer).all()
    premium = sum(1 for p in produtores if p.is_premium)

    pagos = db.query(Order).filter(Order.status.in_([PEDIDO_PAGO, PEDIDO_RETIRADO]))
    volume = round(sum(o.valor_total for o in pagos.all()), 2)
    receita = round(sum(o.taxa_plataforma for o in pagos.all()), 2)
    repasse = round(sum(o.valor_produtor for o in pagos.all()), 2)
    assinaturas_pagas = db.query(PremiumSubscription).filter(PremiumSubscription.status == PEDIDO_PAGO).all()
    receita_premium = round(sum(a.valor for a in assinaturas_pagas), 2)

    extrato = []
    for o in pagos.options(joinedload(Order.producer), selectinload(Order.itens)).order_by(Order.id.desc()).limit(10):
        item = o.itens[0] if o.itens else None
        extrato.append({
            "id": o.id,
            "descricao": f"{item.quantidade}x {item.nome_produto}" if item else f"Pedido #{o.id}",
            "cliente": o.consumidor_nome,
            "metodo": METODOS.get(o.metodo or "", "PIX"),
            "produtor": o.producer.business_name if o.producer else "-",
            "valor_bruto": o.valor_total,
            "repasse_produtor": o.valor_produtor,
            "comissao_plataforma": o.taxa_plataforma,
            "gateway": o.gateway,
            "data": o.paid_at.isoformat() if o.paid_at else None,
        })

    # Atividade recente: publicações, assinaturas e vendas
    atividades = []
    for p in db.query(Product).options(joinedload(Product.producer)).order_by(Product.id.desc()).limit(6):
        atividades.append({
            "tipo": "publicacao", "titulo": f'Nova publicação: "{p.nome}"',
            "detalhe": f"{_tempo_relativo(p.created_at)} ({p.producer.business_name if p.producer else '-'})",
            "status": p.status, "product_id": p.id, "data": p.created_at,
        })
    for a in db.query(PremiumSubscription).options(joinedload(PremiumSubscription.producer)) \
            .filter(PremiumSubscription.status == PEDIDO_PAGO).order_by(PremiumSubscription.id.desc()).limit(4):
        atividades.append({
            "tipo": "premium", "titulo": f'Assinatura Premium ativada: "{a.producer.business_name}"',
            "detalhe": _tempo_relativo(a.paid_at), "status": "pago", "data": a.paid_at,
        })
    for o in pagos.options(joinedload(Order.producer)).order_by(Order.id.desc()).limit(4):
        atividades.append({
            "tipo": "venda", "titulo": f"Venda #{o.id} — {o.producer.business_name if o.producer else ''}",
            "detalhe": f"{_tempo_relativo(o.paid_at)} (R$ {o.valor_total:.2f})".replace(".", ","), "status": "pago", "data": o.paid_at,
        })
    atividades.sort(key=lambda a: a["data"] or datetime.min, reverse=True)
    for a in atividades:
        a.pop("data")

    return {
        "pendentes": pendentes,
        "premium": premium,
        "ativos": ativos,
        "produtores": len(produtores),
        "financeiro": {
            "volume_transacionado": volume,
            "receita_plataforma": receita,
            "repasse_produtores": repasse,
            "receita_premium": receita_premium,
            "assinaturas_pagas": len(assinaturas_pagas),
            "percentual_plataforma": settings.PLATFORM_FEE_PERCENT,
            "preco_premium": settings.PREMIUM_PRICE,
        },
        "extrato_split": extrato,
        "atividades": atividades[:8],
    }


# ---------------- Curadoria ----------------
@router.get("/products")
def listar_publicacoes(status: Optional[str] = STATUS_PENDENTE, categoria: Optional[str] = None,
                       db: Session = Depends(get_db)):
    query = db.query(Product).options(joinedload(Product.producer), selectinload(Product.imagens))
    if status and status != "todos":
        query = query.filter(Product.status == status)
    if categoria and categoria.lower() not in ("todas", "todos"):
        query = query.filter(Product.categoria == categoria)
    return [product_admin(p) for p in query.order_by(Product.id.desc()).all()]


@router.get("/products/counts")
def contagens(db: Session = Depends(get_db)):
    linhas = db.query(Product.status, func.count(Product.id)).group_by(Product.status).all()
    return {status or "sem_status": total for status, total in linhas}


def _produto(db: Session, product_id: int) -> Product:
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    return p


@router.get("/products/{product_id}")
def detalhe_publicacao(product_id: int, db: Session = Depends(get_db)):
    p = _produto(db, product_id)
    if not p.analise:  # produtos antigos: gera a análise na hora
        p.analise_curadoria = json.dumps(
            analisar_produto(p.nome, p.descricao_tecnica, p.historia, p.categoria, bool(p.imagens)),
            ensure_ascii=False)
        db.commit()
    return product_admin(p)


@router.post("/products/{product_id}/reanalisar")
def reanalisar(product_id: int, db: Session = Depends(get_db)):
    p = _produto(db, product_id)
    p.analise_curadoria = json.dumps(
        analisar_produto(p.nome, p.descricao_tecnica, p.historia, p.categoria, bool(p.imagens)),
        ensure_ascii=False)
    db.commit()
    return product_admin(p)


@router.post("/products/{product_id}/aprovar")
async def aprovar(product_id: int, db: Session = Depends(get_db)):
    p = _produto(db, product_id)
    p.status = STATUS_APROVADO
    p.motivo_rejeicao = None
    db.commit()
    if p.producer and p.producer.whatsapp:
        await enviar_mensagem_openwa(
            p.producer.whatsapp, f"🍃 *Mercado Nativo*\n\nBoa notícia! Seu produto \"{p.nome}\" foi aprovado e já está aparecendo na vitrine.\n\n"
            f"Ver no seu painel: {settings.FRONTEND_URL}/painel")
    return product_admin(p)


@router.post("/products/{product_id}/rejeitar")
async def rejeitar(product_id: int, req: RejectRequest, db: Session = Depends(get_db)):
    p = _produto(db, product_id)
    p.status = STATUS_REJEITADO
    p.motivo_rejeicao = req.motivo.strip()
    p.destaque = False
    db.commit()
    # Pedidos ainda não pagos deste produto são cancelados (e o Pix gerado, invalidado)
    await run_in_threadpool(cancelamento_service.cancelar_pendentes, db, product_id=p.id,
                            motivo="O produto saiu da vitrine")
    if p.producer and p.producer.whatsapp:
        await enviar_mensagem_openwa(
            p.producer.whatsapp,
            f"🍃 *Mercado Nativo*\n\nSeu produto \"{p.nome}\" precisa de ajustes antes de ir para a vitrine.\n"
            f"O que ajustar: {p.motivo_rejeicao}\n\nAbra o seu painel, toque em Editar no produto e salve de novo: {settings.FRONTEND_URL}/painel")
    return product_admin(p)


@router.delete("/products/{product_id}")
async def excluir_publicacao(product_id: int, motivo: Optional[str] = None, db: Session = Depends(get_db),
                             admin=Depends(get_current_admin)):
    """Exclui de vez uma publicação (fotos e avaliações juntas). Pedidos antigos ficam no histórico."""
    p = _produto(db, product_id)
    nome, dono = p.nome, p.producer
    # Antes de apagar: depois o vínculo dos itens com o produto some
    await run_in_threadpool(cancelamento_service.cancelar_pendentes, db, product_id=p.id,
                            motivo="O produto saiu da vitrine")
    remover_produto(db, p)
    db.commit()
    log.warning("Admin %s excluiu o produto %s (%s). Motivo: %s", admin.email, product_id, nome, motivo or "-")
    if dono and dono.whatsapp:
        texto = f"🍃 *Mercado Nativo*\n\nSeu produto \"{nome}\" foi removido da plataforma pela equipe."
        if motivo and motivo.strip():
            texto += f"\nMotivo: {motivo.strip()[:300]}"
        texto += "\n\nDúvidas? Responda esta mensagem ou veja as Regras para Vendedores no site."
        await enviar_mensagem_openwa(dono.whatsapp, texto)
    return {"message": f"Publicação \"{nome}\" excluída."}


# ---------------- Pedidos (SAC: cancelamento e devolução) ----------------
@router.get("/orders")
def listar_pedidos(status: Optional[str] = None, q: Optional[str] = None, db: Session = Depends(get_db)):
    """Últimos pedidos, para a equipe atender o SAC (inclui contato do comprador)."""
    query = db.query(Order).options(joinedload(Order.producer), selectinload(Order.itens))
    if status == "solicitacoes":  # pedidos de cancelamento esperando a equipe
        query = query.filter(Order.solicitacao_status == "pendente", Order.status != "cancelado")
    elif status and status != "todos":
        query = query.filter(Order.status == status)
    termo = (q or "").strip().lower()
    resultado = []
    for o in query.order_by(Order.id.desc()).limit(200):
        item = o.itens[0] if o.itens else None
        linha = {
            "id": o.id,
            "codigo": o.codigo,
            "descricao": f"{item.quantidade}x {item.nome_produto}" if item else f"Pedido #{o.id}",
            "cliente": o.consumidor_nome,
            "whatsapp": o.consumidor_whatsapp,
            "produtor": o.producer.business_name if o.producer else "-",
            "produtor_whatsapp": o.producer.whatsapp if o.producer else None,  # a equipe confere a entrega com ele
            "valor_total": o.valor_total,
            "metodo": METODOS.get(o.metodo or "", "-"),
            "gateway": o.gateway,
            "status": o.status,
            "criado_em": o.created_at.isoformat() if o.created_at else None,
            "pago_em": o.paid_at.isoformat() if o.paid_at else None,
            "pode_cancelar": cancelamento_service.pode_cancelar(o, "admin"),
            # Pix de reserva: a equipe confere no extrato e confirma
            "pix_reserva": o.gateway == "manual",
            "reserva_informado_em": o.reserva_informado_em.isoformat() if o.reserva_informado_em else None,
            **cancelamento_service.resumo(o),
        }
        if termo and termo not in f"{o.id} {linha['cliente']} {linha['whatsapp']} {linha['produtor']} {linha['descricao']}".lower():
            continue
        resultado.append(linha)
        if len(resultado) >= 100:
            break
    return resultado


@router.post("/orders/{order_id}/confirmar-pix-reserva")
def confirmar_pix_reserva(order_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """A equipe viu o Pix de reserva no extrato da conta da plataforma: confirma o pedido.
    O repasse ao produtor deste pedido é feito manualmente (o valor está em `valor_produtor`)."""
    pedido = db.get(Order, order_id)
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    if pedido.gateway != "manual" or pedido.status != PEDIDO_AGUARDANDO:
        raise HTTPException(400, "Este pedido não está aguardando um Pix de reserva.")
    pedido.status_detalhe = f"pix_reserva_conferido_por:{admin.email}"[:80]
    db.commit()
    confirmar_pedido(db, pedido)
    log.warning("Admin %s confirmou o Pix de reserva do pedido %s (R$ %.2f).", admin.email, order_id, pedido.valor_total)
    return {"message": f"Pedido nº {order_id} confirmado. Lembre-se de repassar R$ {pedido.valor_produtor:.2f} ao produtor.",
            "status": pedido.status, **cancelamento_service.resumo(pedido)}


@router.get("/status-servicos")
def status_servicos(db: Session = Depends(get_db)):
    """Situação do Mercado Pago, do WhatsApp e das filas de reenvio."""
    return tarefas_service.situacao(db)


@router.post("/orders/{order_id}/cancelar")
def cancelar_pedido(order_id: int, dados: CancelamentoMotivo, db: Session = Depends(get_db),
                    admin=Depends(get_current_admin)):
    """A equipe cancela e devolve o dinheiro (inclusive depois da retirada: direito de arrependimento)."""
    pedido = db.get(Order, order_id)
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    try:
        cancelamento_service.cancelar(db, pedido, "admin", dados.motivo)
    except cancelamento_service.CancelamentoError as e:
        raise HTTPException(400, str(e))
    log.warning("Admin %s cancelou o pedido %s. Motivo: %s", admin.email, order_id, dados.motivo)
    situacao = {"approved": "e valor devolvido ao cliente", "pending": "e devolução em andamento no Mercado Pago",
                "manual": "— devolva o Pix ao cliente pela conta da plataforma",
                "sem_cobranca": "(nada tinha sido cobrado)"}.get(pedido.reembolso_status or "", "")
    return {"message": f"Pedido nº {order_id} cancelado {situacao}".strip() + ".", **cancelamento_service.resumo(pedido),
            "status": pedido.status, "pode_cancelar": False}


@router.get("/orders/solicitacoes/total")
def total_solicitacoes(db: Session = Depends(get_db)):
    """Quantos pedidos de cancelamento estão esperando resposta (aviso no menu da equipe)."""
    return {"total": db.query(Order).filter(Order.solicitacao_status == "pendente", Order.status != "cancelado").count()}


@router.post("/orders/{order_id}/solicitacao/recusar")
def recusar_solicitacao(order_id: int, dados: CancelamentoMotivo, db: Session = Depends(get_db),
                        admin=Depends(get_current_admin)):
    """A equipe falou com o produtor e o produto já tinha sido entregue (ou outro motivo): recusa."""
    pedido = db.get(Order, order_id)
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    try:
        cancelamento_service.recusar_solicitacao(db, pedido, dados.motivo)
    except cancelamento_service.CancelamentoError as e:
        raise HTTPException(400, str(e))
    log.warning("Admin %s recusou o pedido de cancelamento do pedido %s. Motivo: %s", admin.email, order_id, dados.motivo)
    return {"message": f"Pedido de cancelamento do pedido nº {order_id} recusado. O cliente foi avisado.",
            "status": pedido.status, "pode_cancelar": cancelamento_service.pode_cancelar(pedido, "admin"),
            **cancelamento_service.resumo(pedido)}


# ---------------- Vendedores ----------------
@router.get("/producers")
def listar_vendedores(q: Optional[str] = None, db: Session = Depends(get_db)):
    produtores = (db.query(Producer).options(selectinload(Producer.products))
                  .filter((Producer.ativo.is_(None)) | (Producer.ativo.is_(True))).all())
    vendas = dict(db.query(Order.producer_id, func.count(Order.id))
                  .filter(Order.status.in_([PEDIDO_PAGO, PEDIDO_RETIRADO])).group_by(Order.producer_id).all())
    termo = (q or "").strip().lower()
    resultado = []
    for p in produtores:
        if termo and termo not in f"{p.name} {p.business_name} {p.city} {p.whatsapp}".lower():
            continue
        resultado.append({
            "id": p.id, "nome": p.name, "nome_loja": p.business_name, "whatsapp": p.whatsapp,
            "local": f"{p.city or '-'}, {p.uf}", "premium": p.is_premium,
            "produtos": len(p.products),
            "na_vitrine": sum(1 for x in p.products if x.status == STATUS_APROVADO),
            "vendas": int(vendas.get(p.id, 0)),
            "mp_conectado": p.mp_conectado,
            "cadastrado_em": p.created_at.isoformat() if p.created_at else None,
        })
    resultado.sort(key=lambda r: (r["nome_loja"] or "").lower())
    return resultado


@router.post("/producers/{producer_id}/mercadopago/enviar-link", dependencies=[Depends(limitar("mp_link_admin", 30, 3600))])
async def enviar_link_mercadopago(producer_id: int, db: Session = Depends(get_db)):
    """A equipe ajuda o produtor: o link vai só para o WhatsApp cadastrado dele (o admin não vê o link)."""
    prod = db.get(Producer, producer_id)
    if not prod or prod.ativo is False:
        raise HTTPException(404, "Vendedor não encontrado")
    try:
        enviado = await conexao_mp_service.enviar_link_whatsapp(prod)
    except conexao_mp_service.ConexaoError as e:
        raise HTTPException(400, str(e))
    if not enviado:
        db.commit() if settings.OTP_DEV_MODE else db.rollback()  # sem envio, o link anterior continua valendo
        raise HTTPException(503, "Não foi possível enviar pelo WhatsApp agora. Tente de novo em alguns minutos.")
    db.commit()
    return {"message": f"Link de conexão enviado para o WhatsApp de \"{prod.business_name}\"."}


@router.delete("/producers/{producer_id}")
async def excluir_vendedor(producer_id: int, motivo: Optional[str] = None, db: Session = Depends(get_db),
                           admin=Depends(get_super_admin)):
    """Só o Super Admin: exclui os produtos e apaga os dados pessoais do vendedor (ver remocao_service)."""
    prod = db.get(Producer, producer_id)
    if not prod or prod.ativo is False:
        raise HTTPException(404, "Vendedor não encontrado")
    nome, whatsapp = prod.business_name, prod.whatsapp
    if whatsapp:  # avisa antes de apagar o número
        texto = "🍃 *Mercado Nativo*\n\nSua conta de vendedor no Mercado Nativo foi encerrada pela equipe."
        if motivo and motivo.strip():
            texto += f"\nMotivo: {motivo.strip()[:300]}"
        texto += "\nSeus dados pessoais foram apagados da plataforma."
        await enviar_mensagem_openwa(whatsapp, texto)
    # Pedidos não pagos são cancelados ANTES de desconectar o Mercado Pago do vendedor
    await run_in_threadpool(cancelamento_service.cancelar_pendentes, db, producer_id=prod.id,
                            motivo="O vendedor saiu da plataforma")
    total = remover_produtor(db, prod)
    db.commit()
    log.warning("Super Admin %s excluiu o vendedor %s (%s) e %s produto(s). Motivo: %s",
                admin.email, producer_id, nome, total, motivo or "-")
    return {"message": f"Vendedor \"{nome}\" excluído junto com {total} produto(s)."}


# ---------------- Vitrine Premium ----------------
@router.get("/premium")
def vitrine_premium(db: Session = Depends(get_db)):
    produtores = (db.query(Producer).options(selectinload(Producer.products))
                  .filter((Producer.ativo.is_(None)) | (Producer.ativo.is_(True)))
                  .order_by(Producer.business_name).all())
    resultado = []
    for prod in produtores:
        resultado.append({
            "id": prod.id,
            "nome": prod.name,
            "nome_loja": prod.business_name,
            "local": f"{prod.city or '-'}, {prod.uf}",
            "premium": prod.is_premium,
            "premium_ate": prod.premium_ate.isoformat() if prod.premium_ate else None,
            "produtos": [
                {"id": p.id, "nome": p.nome, "destaque": bool(p.destaque), "status": p.status}
                for p in sorted(prod.products, key=lambda x: x.id) if p.status == STATUS_APROVADO
            ],
        })
    resultado.sort(key=lambda r: (not r["premium"], r["nome_loja"] or ""))
    return resultado


@router.patch("/products/{product_id}/destaque")
def alterar_destaque(product_id: int, req: DestaqueUpdate, db: Session = Depends(get_db)):
    p = _produto(db, product_id)
    if req.destaque and not (p.producer and p.producer.is_premium):
        raise HTTPException(400, "Somente produtos de assinantes Premium podem ficar em destaque.")
    if req.destaque and p.status != STATUS_APROVADO:
        raise HTTPException(400, "Aprove o produto antes de destacá-lo.")
    p.destaque = req.destaque
    db.commit()
    return {"id": p.id, "destaque": p.destaque}


@router.patch("/producers/{producer_id}/premium")
def alterar_premium(producer_id: int, req: PremiumUpdate, db: Session = Depends(get_db)):
    prod = db.get(Producer, producer_id)
    if not prod:
        raise HTTPException(404, "Produtor não encontrado")
    prod.premium = req.premium
    prod.premium_ate = None  # concedido manualmente pelo admin: sem data de expiração
    if not req.premium:
        for p in prod.products:
            p.destaque = False
    db.commit()
    return {"id": prod.id, "premium": prod.is_premium}
