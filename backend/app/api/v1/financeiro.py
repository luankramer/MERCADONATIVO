"""Financeiro do painel admin: relatório do mês, repasses aos produtores e planilha (CSV)."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_admin, get_super_admin
from app.db.database import get_db
from app.services import financeiro_service as fin

router = APIRouter(prefix="/api/v1/admin/financeiro", tags=["Financeiro"])


class RepasseNovo(BaseModel):
    mes: str = Field(pattern=r"^\d{4}-\d{2}$")
    producer_id: int
    observacao: str | None = Field(default=None, max_length=300)


@router.get("")
def relatorio(mes: str | None = None, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    try:
        return fin.relatorio(db, mes)
    except fin.FinanceiroError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/relatorio.csv")
def relatorio_csv(mes: str | None = None, db: Session = Depends(get_db), _=Depends(get_current_admin)):
    try:
        dados = fin.relatorio(db, mes)
    except fin.FinanceiroError as e:
        raise HTTPException(400, str(e)) from e
    return Response(fin.csv_do_mes(dados), media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="mercado-nativo-financeiro-{dados["mes"]}.csv"'})


@router.post("/repasses", status_code=201)
def registrar_repasse(req: RepasseNovo, db: Session = Depends(get_db), admin=Depends(get_super_admin)):
    try:
        r = fin.registrar_repasse(db, req.mes, req.producer_id, req.observacao, admin.id)
    except fin.FinanceiroError as e:
        raise HTTPException(400, str(e)) from e
    return {"id": r.id, "valor_repasse": r.valor_repasse, "quantidade_pedidos": r.quantidade_pedidos}
