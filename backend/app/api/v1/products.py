"""Gestão de produtos pelo próprio produtor (requer login)."""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.security import get_current_producer
from app.db.database import get_db
from app.models.product_model import CATEGORIAS, STATUS_PENDENTE, Product, ProductImage
from app.models.user_model import Producer
from app.services.ai_service import analisar_produto
from app.services.remocao_service import remover_produto
from app.services.serializer_service import product_owner
from app.services.storage_service import remover_arquivo, salvar_imagem

router = APIRouter()

MAX_IMAGENS = 6


def _meu_produto(db: Session, product_id: int, producer: Producer) -> Product:
    product = db.get(Product, product_id)
    if not product or product.producer_id != producer.id:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


def _validar(nome: str, preco: float, estoque: int, categoria: str,
             lote: str = "", descricao: str = "", historia: str = "") -> None:
    if not nome.strip():
        raise HTTPException(400, "Informe o nome do produto.")
    if len(nome) > 255 or len(lote) > 100:
        raise HTTPException(400, "Nome ou lote muito longo.")
    if len(descricao) > 3000 or len(historia) > 3000:
        raise HTTPException(400, "Descrição e história podem ter no máximo 3.000 caracteres.")
    if preco > 100000 or estoque > 100000:
        raise HTTPException(400, "Preço ou estoque fora do limite permitido.")
    if preco <= 0:
        raise HTTPException(400, "O preço precisa ser maior que zero.")
    if estoque < 0:
        raise HTTPException(400, "O estoque não pode ser negativo.")
    if categoria not in CATEGORIAS:
        raise HTTPException(400, f"Categoria inválida. Use: {', '.join(CATEGORIAS)}.")


def _reanalisar(product: Product) -> None:
    """Envia para a curadoria com a análise automática da IA."""
    product.status = STATUS_PENDENTE
    product.motivo_rejeicao = None
    product.analise_ia = json.dumps(
        analisar_produto(product.nome, product.descricao_tecnica, product.historia,
                         product.categoria, bool(product.imagens)),
        ensure_ascii=False,
    )


async def _adicionar_imagens(product: Product, imagens: list[UploadFile] | None) -> bool:
    arquivos = [i for i in (imagens or []) if i and i.filename]
    if not arquivos:
        return False
    if len(product.imagens) + len(arquivos) > MAX_IMAGENS:
        raise HTTPException(400, f"Cada produto pode ter no máximo {MAX_IMAGENS} fotos.")
    ordem = len(product.imagens)
    for arquivo in arquivos:
        url = await salvar_imagem(arquivo, "produtos", f"p{product.id}")
        product.imagens.append(ProductImage(url=url, ordem=ordem))
        ordem += 1
    return True


@router.get("/products")
def list_my_products(db: Session = Depends(get_db), producer: Producer = Depends(get_current_producer)):
    produtos = db.query(Product).filter(Product.producer_id == producer.id).order_by(Product.id.desc()).all()
    return [product_owner(p) for p in produtos]


@router.post("/products", status_code=201)
async def create_product(
    nome: str = Form(...),
    preco: float = Form(...),
    categoria: str = Form("Alimentos"),
    estoque: int = Form(0),
    lote: str = Form(""),
    descricao_tecnica: str = Form(""),
    historia: str = Form(""),
    imagens: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    producer: Producer = Depends(get_current_producer),
):
    _validar(nome, preco, estoque, categoria, lote, descricao_tecnica, historia)
    product = Product(
        nome=nome.strip(), preco=round(preco, 2), categoria=categoria, estoque=estoque,
        lote=lote or None, descricao_tecnica=descricao_tecnica, historia=historia,
        producer_id=producer.id, visualizacoes=0, contatos_whatsapp=0, destaque=False,
    )
    db.add(product)
    db.flush()  # gera o id para nomear as fotos
    await _adicionar_imagens(product, imagens)
    _reanalisar(product)
    db.commit()
    db.refresh(product)
    return product_owner(product)


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db), producer: Producer = Depends(get_current_producer)):
    return product_owner(_meu_produto(db, product_id, producer))


@router.put("/products/{product_id}")
async def update_product(
    product_id: int,
    nome: str = Form(...),
    preco: float = Form(...),
    categoria: str = Form("Alimentos"),
    estoque: int = Form(0),
    lote: str = Form(""),
    descricao_tecnica: str = Form(""),
    historia: str = Form(""),
    remover_imagens: str = Form(""),  # ids separados por vírgula
    imagens: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    producer: Producer = Depends(get_current_producer),
):
    product = _meu_produto(db, product_id, producer)
    _validar(nome, preco, estoque, categoria, lote, descricao_tecnica, historia)

    # Mudanças de conteúdo voltam para a curadoria; preço/estoque/lote não.
    conteudo_mudou = (
        product.nome != nome.strip()
        or product.categoria != categoria
        or (product.descricao_tecnica or "") != descricao_tecnica
        or (product.historia or "") != historia
    )

    product.nome = nome.strip()
    product.preco = round(preco, 2)
    product.categoria = categoria
    product.estoque = estoque
    product.lote = lote or None
    product.descricao_tecnica = descricao_tecnica
    product.historia = historia

    ids_remover = {int(i) for i in remover_imagens.split(",") if i.strip().isdigit()}
    for img in list(product.imagens):
        if img.id in ids_remover:
            remover_arquivo(img.url)
            product.imagens.remove(img)
            conteudo_mudou = True
    if await _adicionar_imagens(product, imagens):
        conteudo_mudou = True
    for i, img in enumerate(product.imagens):
        img.ordem = i

    if conteudo_mudou:
        _reanalisar(product)
    db.commit()
    db.refresh(product)
    return product_owner(product)


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), producer: Producer = Depends(get_current_producer)):
    product = _meu_produto(db, product_id, producer)
    remover_produto(db, product)
    db.commit()
    return {"message": "Produto removido com sucesso"}
