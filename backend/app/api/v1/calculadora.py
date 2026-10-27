"""Calculadora de Custos (ferramenta exclusiva Premium)."""
import json
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_producer
from app.db.database import get_db
from app.models.cost_model import CostCalculation
from app.models.product_model import Product
from app.models.user_model import Producer
from app.schemas.cost import CostRequest

router = APIRouter(prefix="/api/v1/calculadora", tags=["Calculadora de Custos"])


def calcular(itens_valores: list[float], rendimento: int, margem: float) -> dict:
    """custo total -> custo unitário -> preço sugerido = unitário × (1 + margem%)."""
    def moeda(valor: Decimal) -> float:  # arredondamento comercial (11,775 -> 11,78)
        return float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    total = sum((Decimal(str(v)) for v in itens_valores), Decimal("0"))
    unitario = total / Decimal(rendimento)
    preco = unitario * (Decimal("1") + Decimal(str(margem)) / Decimal("100"))
    return {"custo_total": moeda(total), "custo_unitario": moeda(unitario), "preco_sugerido": moeda(preco)}


def _exigir_premium(produtor: Producer) -> None:
    if not produtor.is_premium:
        raise HTTPException(403, "A Calculadora de Custos é exclusiva do plano Premium.")


@router.post("/calcular")
def calcular_custos(req: CostRequest, db: Session = Depends(get_db),
                    produtor: Producer = Depends(get_current_producer)):
    _exigir_premium(produtor)
    resultado = calcular([i.valor for i in req.itens], req.rendimento, req.margem)

    produto_atualizado = None
    if req.product_id:
        produto = db.get(Product, req.product_id)
        if not produto or produto.producer_id != produtor.id:
            raise HTTPException(404, "Produto não encontrado")
        produto.preco = resultado["preco_sugerido"]
        produto_atualizado = {"id": produto.id, "nome": produto.nome, "preco": produto.preco}

    if req.salvar:
        db.add(CostCalculation(
            producer_id=produtor.id, product_id=req.product_id, nome=req.nome, rendimento=req.rendimento,
            itens=json.dumps([i.model_dump() for i in req.itens], ensure_ascii=False),
            margem=req.margem, **resultado,
        ))
    db.commit()
    return {**resultado, "produto_atualizado": produto_atualizado}


@router.get("/historico")
def historico(db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    _exigir_premium(produtor)
    calculos = (
        db.query(CostCalculation).filter(CostCalculation.producer_id == produtor.id)
        .order_by(CostCalculation.id.desc()).limit(20).all()
    )
    return [
        {"id": c.id, "nome": c.nome, "rendimento": c.rendimento, "itens": json.loads(c.itens),
         "margem": c.margem, "custo_total": c.custo_total, "custo_unitario": c.custo_unitario,
         "preco_sugerido": c.preco_sugerido, "product_id": c.product_id,
         "created_at": c.created_at.isoformat() if c.created_at else None}
        for c in calculos
    ]
