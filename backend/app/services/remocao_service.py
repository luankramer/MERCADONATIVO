"""
Exclusão de publicações e de vendedores (pelo admin ou pelo próprio produtor).

Regras (ver Política de Privacidade):
- Produto excluído: some da vitrine, as fotos são apagadas do disco e as avaliações também.
  Pedidos antigos continuam no histórico com o nome do produto (sem o vínculo).
- Vendedor excluído: todos os produtos são excluídos e os DADOS PESSOAIS são apagados na hora
  (nome, WhatsApp, e-mail, endereço, foto, história, conta Mercado Pago). O cadastro fica só como
  "Vendedor removido", porque os pedidos pagos precisam continuar no histórico financeiro
  (obrigação legal e defesa em caso de reclamação), sem dados pessoais do vendedor.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.cost_model import CostCalculation
from app.models.order_model import OrderItem
from app.models.product_model import Product
from app.models.user_model import Producer
from app.services import payment_service
from app.services.storage_service import remover_arquivo

NOME_REMOVIDO = "Vendedor removido"


def remover_produto(db: Session, produto: Product) -> None:
    """Apaga o produto, as fotos e as avaliações, preservando o histórico de pedidos."""
    db.query(OrderItem).filter(OrderItem.product_id == produto.id).update({OrderItem.product_id: None})
    db.query(CostCalculation).filter(CostCalculation.product_id == produto.id).update({CostCalculation.product_id: None})
    for img in list(produto.imagens):
        remover_arquivo(img.url)
    db.delete(produto)


def remover_produtor(db: Session, produtor: Producer) -> int:
    """Exclui os produtos e apaga os dados pessoais do vendedor. Devolve quantos produtos saíram."""
    produtos = db.query(Product).filter(Product.producer_id == produtor.id).all()
    for p in produtos:
        remover_produto(db, p)
    db.query(CostCalculation).filter(CostCalculation.producer_id == produtor.id).delete()

    remover_arquivo(produtor.foto_perfil)
    payment_service.desconectar(produtor)
    produtor.name = NOME_REMOVIDO
    produtor.business_name = NOME_REMOVIDO
    for campo in ("email", "whatsapp", "telefone", "foto_perfil", "cep", "address",
                  "latitude", "longitude", "hashed_password"):
        setattr(produtor, campo, None)
    produtor.description = None
    produtor.endereco_publico = False
    produtor.premium = False
    produtor.premium_ate = None
    produtor.seguidores = 0
    produtor.ativo = False
    produtor.excluido_em = datetime.utcnow()
    return len(produtos)


def exportar_dados(db: Session, produtor: Producer) -> dict:
    """Cópia dos dados do produtor (direito de acesso e portabilidade — LGPD art. 18)."""
    produtos = db.query(Product).filter(Product.producer_id == produtor.id).all()
    return {
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "perfil": {
            "nome": produtor.name, "nome_do_negocio": produtor.business_name, "email": produtor.email,
            "whatsapp": produtor.whatsapp, "cep": produtor.cep, "endereco": produtor.address,
            "cidade": produtor.city, "estado": produtor.uf, "endereco_publico": bool(produtor.endereco_publico),
            "historia": produtor.description, "foto_perfil": produtor.foto_perfil,
            "plano_premium": produtor.is_premium,
            "conta_mercado_pago_conectada": produtor.mp_conectado,
            "cadastrado_em": produtor.created_at.isoformat() if produtor.created_at else None,
            "termos_aceitos_em": produtor.termos_aceitos_em.isoformat() if produtor.termos_aceitos_em else None,
            "versao_dos_termos": produtor.termos_versao,
        },
        "produtos": [
            {"nome": p.nome, "preco": p.preco, "categoria": p.categoria, "estoque": p.estoque, "lote": p.lote,
             "descricao": p.descricao_tecnica, "historia": p.historia, "situacao": p.status,
             "fotos": [i.url for i in p.imagens]}
            for p in produtos
        ],
    }
