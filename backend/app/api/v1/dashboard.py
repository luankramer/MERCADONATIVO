"""Painel gerencial do produtor: visão financeira, métricas e estoque."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_producer
from app.db.database import get_db
from app.models.order_model import PEDIDO_PAGO, PEDIDO_RETIRADO, Order, OrderItem
from app.models.product_model import Product
from app.models.user_model import Producer
from app.services.serializer_service import product_owner

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/me")
def get_dashboard_data(db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    produtos_db = db.query(Product).filter(Product.producer_id == produtor.id).order_by(Product.id.desc()).all()

    pagos = [PEDIDO_PAGO, PEDIDO_RETIRADO]
    # Unidades vendidas por produto (conversões)
    vendas_por_produto = dict(
        db.query(OrderItem.product_id, func.coalesce(func.sum(OrderItem.quantidade), 0))
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Order.producer_id == produtor.id, Order.status.in_(pagos))
        .group_by(OrderItem.product_id)
        .all()
    )
    pedidos_pagos = db.query(Order).filter(Order.producer_id == produtor.id, Order.status.in_(pagos))
    desde = datetime.utcnow() - timedelta(days=30)
    receita_30d = sum(o.valor_produtor for o in pedidos_pagos.filter(Order.paid_at >= desde).all())
    receita_total = sum(o.valor_produtor for o in pedidos_pagos.all())
    vendas_concluidas = pedidos_pagos.count()

    produtos = []
    for p in produtos_db:
        item = product_owner(p)
        item["views"] = p.visualizacoes or 0
        item["conversoes"] = int(vendas_por_produto.get(p.id, 0)) + (p.contatos_whatsapp or 0)
        produtos.append(item)

    visitas = sum(p.visualizacoes or 0 for p in produtos_db)
    contatos = sum(p.contatos_whatsapp or 0 for p in produtos_db)
    inicios_compra = contatos + vendas_concluidas
    taxa = round(inicios_compra / visitas * 100, 1) if visitas else 0.0

    return {
        "produtor": {
            "id": produtor.id,
            "nome": produtor.name,
            "nome_loja": produtor.business_name,
            "cidade": produtor.city,
            "estado": produtor.uf,
            "foto_perfil": produtor.foto_perfil,
            "premium": produtor.is_premium,
            "premium_ate": produtor.premium_ate.isoformat() if produtor.premium_ate else None,
            "termos_pendentes": produtor.termos_versao != settings.TERMOS_VERSAO,
        },
        "produtos": produtos,
        "estatisticas": {
            "visitas": visitas,
            "contatos_whatsapp": inicios_compra,
            "cliques_whatsapp": contatos,
            "taxa_conversao": min(taxa, 100.0),
            "receita_total": round(receita_total, 2),
            "receita_30_dias": round(receita_30d, 2),
            "vendas_concluidas": vendas_concluidas,
            "pendentes_curadoria": sum(1 for p in produtos_db if p.status == "pendente"),
        },
    }
