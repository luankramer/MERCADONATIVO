import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func

import app.models  # noqa: F401  (registra todas as tabelas)
from app.api.v1 import (
    admin, adm_auth, ai, auth, calculadora, checkout, dashboard, mercadopago, producers, products, public,
)
from app.core.config import settings
from app.db.database import SessionLocal, engine
from app.db.migrations import run_migrations
from app.models.admin_model import NIVEL_SUPER, Admin
from app.models.user_model import Producer
from app.services import geo_service, payment_service
from app.services.whatsapp_service import numero_nacional

log = logging.getLogger("mercado_nativo")

settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(settings.UPLOAD_DIR / "perfis").mkdir(exist_ok=True)
(settings.UPLOAD_DIR / "produtos").mkdir(exist_ok=True)


def preparar_banco() -> None:
    """Cria/atualiza tabelas e garante que exista um Super Admin."""
    run_migrations(engine)
    db = SessionLocal()
    try:
        mestre = db.query(Admin).filter(func.lower(Admin.email) == settings.ADMIN_MASTER_EMAIL).first()
        if mestre and mestre.nivel != NIVEL_SUPER:
            mestre.nivel = NIVEL_SUPER
        if db.query(Admin).count() == 0:
            # Sem senha padrão (seria uma brecha): o administrador define a própria senha
            print("👤 Nenhum administrador cadastrado. Rode:  python -m app.reset_admin  (ou redefinir_admin.bat)")
        # Cadastros antigos: WhatsApp só com dígitos e coordenadas para a busca por raio
        for p in db.query(Producer).all():
            if p.whatsapp and p.whatsapp != numero_nacional(p.whatsapp):
                p.whatsapp = numero_nacional(p.whatsapp)
            if p.latitude is None and p.city:
                coords = geo_service.coordenadas(p.city, p.uf, online=False)
                if coords:
                    p.latitude, p.longitude = coords
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        preparar_banco()
    except Exception as e:  # mensagem clara em vez de um traceback enorme
        print("\n❌ Não foi possível conectar/preparar o banco de dados.")
        print(f"   DATABASE_URL = {settings.DATABASE_URL}")
        print("   Verifique se o MySQL está ligado e se o banco 'mercado_nativo' existe.")
        print(f"   Detalhe: {e}\n")
        raise
    print(f"✅ Mercado Nativo API pronta  |  pagamentos: {payment_service.modo_pagamento()}  |  docs: /docs")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    # Em produção a documentação interativa fica desligada
    docs_url=None if settings.is_producao else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_producao else "/openapi.json",
)


@app.middleware("http")
async def cabecalhos_de_seguranca(request: Request, call_next):
    resposta = await call_next(request)
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resposta.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/uploads/"):
        # Imagens enviadas nunca são executadas como página/script
        resposta.headers["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; sandbox"
        resposta.headers["Cache-Control"] = "public, max-age=604800"
    if request.url.scheme == "https":
        resposta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resposta


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URLS,
    # Aceita o Vite em qualquer porta local (5173, 5174...) e na rede local (celular no mesmo Wi-Fi)
    allow_origin_regex=(
        None if settings.is_producao else
        r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?"
    ),
    allow_credentials=False,  # usamos token no cabeçalho, não cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticação"])
app.include_router(adm_auth.router, prefix="/api/v1/auth/admin", tags=["Gestão Admin"])
app.include_router(ai.router, prefix="/api/v1", tags=["Inteligência Artificial"])
app.include_router(products.router, prefix="/api/v1", tags=["Produtos"])
app.include_router(dashboard.router)
app.include_router(producers.router)
app.include_router(public.router)
app.include_router(checkout.router)
app.include_router(calculadora.router)
app.include_router(admin.router)
app.include_router(mercadopago.router)


@app.get("/", tags=["Status"])
def raiz():
    return {"app": settings.APP_NAME, "status": "online", "docs": "/docs"}
