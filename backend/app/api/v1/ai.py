from fastapi import APIRouter, Depends, HTTPException

from app.core.rate_limit import limitar

from app.schemas.ai import AIPrompt
from app.services.ai_service import gerar_historia, status_ia

router = APIRouter()


# Rota declarada como 'def' normal. O FastAPI executa em thread e não trava o servidor.
@router.post("/ai/generate", dependencies=[Depends(limitar("assistente", 15, 600))])
def generate_product_story(req: AIPrompt):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Nenhuma palavra-chave fornecida.")
    texto, fonte = gerar_historia(req.prompt.strip()[:500], req.tipo, (req.nome or "").strip()[:120] or None)
    return {"texto": texto, "fonte": fonte}


@router.get("/ai/status")
def ai_status():
    """Mostra quais provedores de IA estão disponíveis (útil para diagnóstico)."""
    return status_ia()
