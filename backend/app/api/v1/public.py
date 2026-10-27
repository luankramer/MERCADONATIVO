"""Vitrine pública: rotas usadas pelo consumidor (não exigem login)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.rate_limit import limitar
from app.db.database import get_db
from app.models.product_model import CATEGORIAS, STATUS_APROVADO, Product
from app.models.review_model import Review
from app.models.user_model import Producer
from app.schemas.product import ReviewCreate
from app.services import busca_service, geo_service
from app.services.serializer_service import (
    producer_publico, product_card, product_detail, resumo_avaliacoes,
)
from app.services.whatsapp_service import link_whatsapp

router = APIRouter(prefix="/api/v1/public", tags=["Vitrine Pública"])

RAIO_MAXIMO = 200  # 200+ km = sem limite


def _visita_nova(request: Request, product_id: int) -> bool:
    """Conta no máximo 1 visita por IP a cada 30 min (evita inflar as métricas atualizando a página)."""
    from app.core.rate_limit import ip_cliente, registrar
    try:
        registrar(f"visita:{product_id}:{ip_cliente(request)}", 1, 1800)
        return True
    except HTTPException:
        return False


def _produto_publico(db: Session, product_id: int) -> Product:
    product = (
        db.query(Product)
        .options(joinedload(Product.producer), selectinload(Product.imagens))
        .filter(Product.id == product_id)
        .first()
    )
    if not product or product.status != STATUS_APROVADO or not product.producer or product.producer.ativo is False:
        raise HTTPException(404, "Produto não encontrado")
    return product


@router.get("/filtros")
def filtros(uf: str = "AC"):
    return {"categorias": CATEGORIAS, "estados": ["AC", "AM", "RO"], "cidades": geo_service.cidades_por_estado(uf),
            "raio_maximo": RAIO_MAXIMO}


@router.get("/cidades")
def cidades(uf: str = "AC"):
    return geo_service.cidades_por_estado(uf)


def listar_produtos(
    db: Session,
    categoria: Optional[str] = None,
    estado: Optional[str] = None,
    cidade: Optional[str] = None,
    raio_km: Optional[float] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    q: Optional[str] = None,
    producer_id: Optional[int] = None,
) -> list[dict]:
    query = (
        db.query(Product)
        .join(Producer, Product.producer_id == Producer.id)
        .options(joinedload(Product.producer), selectinload(Product.imagens))
        .filter(Product.status == STATUS_APROVADO)
        .filter((Producer.ativo.is_(None)) | (Producer.ativo.is_(True)))
    )
    if categoria and categoria.lower() != "todos":
        query = query.filter(Product.categoria == categoria)
    if producer_id:
        query = query.filter(Product.producer_id == producer_id)
    produtos = query.all()
    if q and q.strip():
        # sem acento, com nomes regionais e tolerando erro de digitação (services/busca_service.py)
        produtos = [p for p in produtos if busca_service.corresponde(
            q, p.nome, p.categoria, p.descricao_tecnica, p.producer.business_name if p.producer else None)]

    # ---- Busca geográfica ----
    # Centro da busca: localização do navegador (lat/lng) ou a cidade escolhida
    centro = (lat, lng) if lat is not None and lng is not None else (
        geo_service.coordenadas(cidade, estado or "AC") if cidade else None
    )
    usar_raio = centro is not None and raio_km is not None and raio_km < RAIO_MAXIMO
    cidade_exata = geo_service.nome_oficial(cidade, estado) if (cidade and raio_km is None) else None

    resultado = []
    for p in produtos:
        prod = p.producer
        distancia = None
        if centro and prod.latitude is not None and prod.longitude is not None:
            distancia = geo_service.distancia_km(centro[0], centro[1], prod.latitude, prod.longitude)
        if usar_raio:
            if distancia is None or distancia > raio_km:
                continue
        else:
            if estado and prod.uf != estado.upper():
                continue
            if cidade_exata and geo_service.nome_oficial(prod.city, prod.uf) != cidade_exata:
                continue
        resultado.append((p, distancia))

    avaliacoes = resumo_avaliacoes(db, [p.id for p, _ in resultado])
    cards = [product_card(p, avaliacoes.get(p.id), d) for p, d in resultado]
    # Ordenação: destaques Premium primeiro, depois disponíveis, depois mais próximos/recentes
    cards.sort(key=lambda c: (
        not c["destaque"],
        c["estoque"] <= 0,
        c["distancia_km"] if c["distancia_km"] is not None else 99999,
        -c["id"],
    ))
    return cards


@router.get("/products")
def vitrine(
    db: Session = Depends(get_db),
    categoria: Optional[str] = None,
    estado: Optional[str] = None,
    cidade: Optional[str] = None,
    raio_km: Optional[float] = Query(None, ge=1),
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    q: Optional[str] = None,
    producer_id: Optional[int] = None,
):
    return listar_produtos(db, categoria, estado, cidade, raio_km, lat, lng, q, producer_id)


@router.get("/products/{product_id}")
def produto(product_id: int, request: Request, registrar_visita: bool = True, db: Session = Depends(get_db)):
    product = _produto_publico(db, product_id)
    if registrar_visita and _visita_nova(request, product_id):
        product.visualizacoes = (product.visualizacoes or 0) + 1
        db.commit()
        db.refresh(product)
    avaliacao = resumo_avaliacoes(db, [product.id]).get(product.id)
    dados = product_detail(product, avaliacao)
    media_produtor, total_produtor = _nota_produtor(db, product.producer_id)
    dados["produtor"] = producer_publico(product.producer, media_produtor, total_produtor)
    return dados


@router.post("/products/{product_id}/contato", dependencies=[Depends(limitar("contato", 30, 3600))])
def registrar_contato(product_id: int, db: Session = Depends(get_db)):
    """Conta um clique em 'Reservar pelo WhatsApp' e devolve o link pronto."""
    product = _produto_publico(db, product_id)
    product.contatos_whatsapp = (product.contatos_whatsapp or 0) + 1
    db.commit()
    mensagem = (
        f"Olá! Vi o produto \"{product.nome}\" (R$ {product.preco:.2f}) no Mercado Nativo "
        "e gostaria de reservar. Como combinamos a retirada?"
    )
    return {"link": link_whatsapp(product.producer.whatsapp, mensagem)}


@router.get("/products/{product_id}/reviews")
def avaliacoes(product_id: int, db: Session = Depends(get_db)):
    _produto_publico(db, product_id)
    lista = db.query(Review).filter(Review.product_id == product_id).order_by(Review.id.desc()).all()
    return [
        {"id": r.id, "nome": r.nome, "nota": r.nota, "comentario": r.comentario,
         "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in lista
    ]


@router.post("/products/{product_id}/reviews", status_code=201, dependencies=[Depends(limitar("avaliacao", 5, 3600))])
def avaliar(product_id: int, req: ReviewCreate, db: Session = Depends(get_db)):
    _produto_publico(db, product_id)
    review = Review(product_id=product_id, nome=req.nome.strip(), nota=req.nota,
                    comentario=(req.comentario or "").strip() or None)
    db.add(review)
    db.commit()
    return {"message": "Obrigado pela sua avaliação!", "id": review.id}


def _nota_produtor(db: Session, producer_id: int) -> tuple[float | None, int]:
    media, total = (
        db.query(func.avg(Review.nota), func.count(Review.id))
        .join(Product, Review.product_id == Product.id)
        .filter(Product.producer_id == producer_id)
        .first()
    )
    return (round(float(media), 1) if media is not None else None), int(total or 0)


@router.get("/producers/{producer_id}")
def perfil_produtor(producer_id: int, db: Session = Depends(get_db)):
    producer = db.get(Producer, producer_id)
    if not producer or producer.ativo is False:
        raise HTTPException(404, "Produtor não encontrado")
    media, total = _nota_produtor(db, producer_id)
    dados = producer_publico(producer, media, total)
    dados["produtos"] = listar_produtos(db, producer_id=producer_id)
    return dados


@router.post("/producers/{producer_id}/seguir", dependencies=[Depends(limitar("seguir", 30, 3600))])
def seguir(producer_id: int, seguir: bool = True, db: Session = Depends(get_db)):
    producer = db.get(Producer, producer_id)
    if not producer:
        raise HTTPException(404, "Produtor não encontrado")
    producer.seguidores = max(0, (producer.seguidores or 0) + (1 if seguir else -1))
    db.commit()
    return {"seguidores": producer.seguidores}
