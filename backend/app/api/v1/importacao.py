"""
Importação dos dados do computador local para o servidor (uso único, na publicação).
Só existe com IMPORTACAO_LIBERADA=true e só o Super Admin pode usar. Depois, desligue a variável.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.security import get_super_admin
from app.db.database import engine
from app.services.importacao_service import ImportacaoError, importar

router = APIRouter(prefix="/api/v1/admin/importacao", tags=["Publicação"])

LIMITE_MB = 80


@router.post("")
async def importar_dados(arquivo: UploadFile, admin=Depends(get_super_admin)):
    if not settings.IMPORTACAO_LIBERADA:
        raise HTTPException(404, "Not Found")
    conteudo = await arquivo.read(LIMITE_MB * 1024 * 1024 + 1)
    if len(conteudo) > LIMITE_MB * 1024 * 1024:
        raise HTTPException(413, f"Arquivo maior que {LIMITE_MB} MB.")
    try:
        resumo = await run_in_threadpool(importar, engine, conteudo)
    except ImportacaoError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, **resumo}
