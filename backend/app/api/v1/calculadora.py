"""Calculadora de Custos (ferramenta exclusiva Premium). As contas ficam em services/calculadora_service.py."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_producer
from app.db.database import get_db
from app.models.cost_model import CostCalculation
from app.models.product_model import Product
from app.models.user_model import Producer
from app.schemas.cost import CostRequest
from app.services import calculadora_service as calc

router = APIRouter(prefix="/api/v1/calculadora", tags=["Calculadora de Custos"])

_EXTRAS = ("horas_trabalho", "valor_hora", "outros_gastos", "incluir_taxas")


def _exigir_premium(produtor: Producer) -> None:
    if not produtor.is_premium:
        raise HTTPException(403, "A Calculadora de Custos é exclusiva do plano Premium.")


@router.post("/calcular")
def calcular_custos(req: CostRequest, db: Session = Depends(get_db),
                    produtor: Producer = Depends(get_current_producer)):
    _exigir_premium(produtor)
    try:
        resultado = calc.calcular(req)
    except calc.CalculoError as e:
        raise HTTPException(400, str(e)) from e

    produto_atualizado = None
    if req.product_id:
        produto = db.get(Product, req.product_id)
        if not produto or produto.producer_id != produtor.id:
            raise HTTPException(404, "Produto não encontrado")
        produto.preco = resultado["preco_sugerido"]
        produto_atualizado = {"id": produto.id, "nome": produto.nome, "preco": produto.preco}

    if req.salvar:
        itens = [{**i.model_dump(exclude_none=True), "custo": c}
                 for i, c in zip(req.itens, resultado["custo_itens"])]
        db.add(CostCalculation(
            producer_id=produtor.id, product_id=req.product_id, nome=req.nome, rendimento=req.rendimento,
            itens=json.dumps(itens, ensure_ascii=False),
            extras=json.dumps({k: getattr(req, k) for k in _EXTRAS}),
            margem=req.margem, custo_total=resultado["custo_total"],
            custo_unitario=resultado["custo_unitario"], preco_sugerido=resultado["preco_sugerido"],
        ))
    db.commit()
    return {**resultado, "produto_atualizado": produto_atualizado}


@router.get("/config")
def config(_: Producer = Depends(get_current_producer)):
    """Taxas usadas para mostrar, na tela, quanto o produtor recebe com o preço sugerido."""
    return {"comissao": settings.PLATFORM_FEE_PERCENT, "taxa_pix": settings.TAXA_MP_PIX,
            "taxa_cartao": settings.TAXA_MP_CREDITO}


@router.get("/historico")
def historico(db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    _exigir_premium(produtor)
    calculos = (
        db.query(CostCalculation).filter(CostCalculation.producer_id == produtor.id)
        .order_by(CostCalculation.id.desc()).limit(20).all()
    )
    return [
        {"id": c.id, "nome": c.nome, "rendimento": c.rendimento, "itens": json.loads(c.itens),
         **(json.loads(c.extras) if c.extras else {}),
         "margem": c.margem, "custo_total": c.custo_total, "custo_unitario": c.custo_unitario,
         "preco_sugerido": c.preco_sugerido, "product_id": c.product_id,
         "created_at": c.created_at.isoformat() if c.created_at else None}
        for c in calculos
    ]
