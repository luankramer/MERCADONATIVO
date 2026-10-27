"""
Converte os modelos do banco em dicionários (JSON) para o frontend.
Centralizar aqui evita respostas diferentes para o mesmo objeto em rotas distintas.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product_model import Product
from app.models.review_model import Review
from app.models.user_model import Producer


def resumo_avaliacoes(db: Session, product_ids: list[int]) -> dict[int, tuple[float, int]]:
    if not product_ids:
        return {}
    linhas = (
        db.query(Review.product_id, func.avg(Review.nota), func.count(Review.id))
        .filter(Review.product_id.in_(product_ids))
        .group_by(Review.product_id)
        .all()
    )
    return {pid: (round(float(media), 1), int(total)) for pid, media, total in linhas}


def local_referencia(producer: Producer | None) -> str:
    if not producer:
        return ""
    cidade = producer.city or "Acre"
    return f"{cidade}, {producer.uf}"


def producer_card(producer: Producer | None) -> dict | None:
    if not producer:
        return None
    return {
        "id": producer.id,
        "nome": producer.name,
        "nome_loja": producer.business_name,
        "cidade": producer.city,
        "estado": producer.uf,
        "local": local_referencia(producer),
        "foto_perfil": producer.foto_perfil,
        "premium": producer.is_premium,
    }


def producer_publico(producer: Producer, media: float | None = None, total_avaliacoes: int = 0) -> dict:
    dados = producer_card(producer) or {}
    dados.update({
        "descricao": producer.description,
        "whatsapp": producer.whatsapp,
        "seguidores": producer.seguidores or 0,
        "endereco_publico": bool(producer.endereco_publico),
        # Privacidade: o endereço completo só aparece se o produtor autorizar
        "endereco": producer.address if producer.endereco_publico else None,
        "cep": producer.cep if producer.endereco_publico else None,
        "nota_media": media,
        "total_avaliacoes": total_avaliacoes,
    })
    return dados


def product_card(p: Product, avaliacao: tuple[float, int] | None = None, distancia: float | None = None) -> dict:
    media, total = avaliacao or (None, 0)
    produtor = p.producer
    return {
        "id": p.id,
        "nome": p.nome,
        "preco": float(p.preco or 0),
        "categoria": p.categoria,
        "estoque": p.estoque or 0,
        "imagem": p.imagens[0].url if p.imagens else None,
        "destaque": bool(p.destaque and produtor and produtor.is_premium),
        "nota_media": media,
        "total_avaliacoes": total,
        "produtor": producer_card(produtor),
        "distancia_km": round(distancia, 1) if distancia is not None else None,
    }


def product_detail(p: Product, avaliacao: tuple[float, int] | None = None) -> dict:
    dados = product_card(p, avaliacao)
    dados.update({
        "lote": p.lote,
        "descricao_tecnica": p.descricao_tecnica,
        "historia": p.historia,
        "imagens": [{"id": i.id, "url": i.url} for i in p.imagens],
        "status": p.status,
    })
    return dados


def product_owner(p: Product) -> dict:
    """Visão do próprio produtor (inclui status da curadoria e métricas)."""
    dados = product_detail(p)
    dados.update({
        "motivo_rejeicao": p.motivo_rejeicao,
        "visualizacoes": p.visualizacoes or 0,
        "contatos_whatsapp": p.contatos_whatsapp or 0,
        "producer_id": p.producer_id,
    })
    return dados


def product_admin(p: Product) -> dict:
    dados = product_owner(p)
    dados.update({
        "analise_ia": p.analise,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "destaque_marcado": bool(p.destaque),
    })
    return dados
