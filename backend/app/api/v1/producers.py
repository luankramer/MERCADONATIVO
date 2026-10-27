"""Perfil do produtor logado: dados da loja, recebimentos, plano Premium e pedidos."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from datetime import timedelta

from app.core.config import settings
from app.core.security import create_access_token, get_current_producer
from app.db.database import get_db
from app.models.order_model import METODOS, PEDIDO_PAGO, PEDIDO_RETIRADO, Order, PremiumSubscription
from app.models.user_model import Producer
from app.schemas.order import PagamentoBrick, PagamentoSimulado
from app.services import geo_service, payment_service
from app.services.checkout_service import confirmar_pix_simulado, pagar_com_brick, pagar_simulado, sincronizar
from app.services.remocao_service import exportar_dados, remover_produtor
from app.services.storage_service import remover_arquivo, salvar_imagem
from app.services.whatsapp_service import numero_nacional

router = APIRouter(prefix="/api/v1/producers", tags=["Producers"])


def _perfil(p: Producer) -> dict:
    return {
        "id": p.id,
        "nome": p.name,
        "nome_loja": p.business_name,
        "email": p.email,
        "cidade": p.city,
        "estado": p.uf,
        "cep": p.cep,
        "endereco": p.address,
        "endereco_publico": bool(p.endereco_publico),
        "telefone": p.telefone,
        "whatsapp": p.whatsapp,
        "descricao": p.description,
        "foto_perfil": p.foto_perfil,
        "premium": p.is_premium,
        "premium_ate": p.premium_ate.isoformat() if p.premium_ate else None,
        "mercadopago": {
            "conectado": p.mp_conectado,
            "conta": p.mp_user_id,
            "conectado_em": p.mp_conectado_em.isoformat() if p.mp_conectado_em else None,
            "split_disponivel": payment_service.split_disponivel(),
        },
        "modo_pagamento": payment_service.modo_pagamento(),
        # Cadastros antigos (ou termos novos): o painel pede para ler e aceitar
        "termos_pendentes": p.termos_versao != settings.TERMOS_VERSAO,
        "termos_versao_atual": settings.TERMOS_VERSAO,
    }


@router.get("/me")
def get_producer(produtor: Producer = Depends(get_current_producer)):
    return _perfil(produtor)


@router.post("/me/aceitar-termos")
def aceitar_termos(db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    from datetime import datetime
    produtor.termos_aceitos_em = datetime.utcnow()
    produtor.termos_versao = settings.TERMOS_VERSAO
    db.commit()
    return {"termos_versao": produtor.termos_versao}


@router.get("/me/dados")
def baixar_meus_dados(db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    """Cópia de todos os dados do produtor (LGPD: acesso e portabilidade)."""
    return exportar_dados(db, produtor)


@router.delete("/me")
def excluir_minha_conta(db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    """O próprio produtor encerra a conta: produtos saem da vitrine e os dados pessoais são apagados."""
    total = remover_produtor(db, produtor)
    db.commit()
    return {"message": f"Conta excluída. {total} produto(s) removido(s) e seus dados pessoais apagados."}


@router.put("/me")
async def update_producer(
    nome: Optional[str] = Form(None),
    nome_loja: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    cidade: Optional[str] = Form(None),
    estado: Optional[str] = Form(None),
    cep: Optional[str] = Form(None),
    endereco: Optional[str] = Form(None),
    endereco_publico: Optional[bool] = Form(None),
    telefone: Optional[str] = Form(None),
    whatsapp: Optional[str] = Form(None),
    descricao: Optional[str] = Form(None),
    foto_perfil: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    produtor: Producer = Depends(get_current_producer),
):
    for valor, limite in ((nome, 255), (nome_loja, 255), (email, 150), (cidade, 120), (endereco, 255), (descricao, 3000)):
        if valor and len(valor) > limite:
            raise HTTPException(400, "Um dos campos passou do tamanho permitido.")
    if nome is not None and nome.strip():
        produtor.name = nome.strip()
    if nome_loja is not None and nome_loja.strip():
        produtor.business_name = nome_loja.strip()
    if email is not None:
        email = email.strip() or None
        if email and db.query(Producer).filter(Producer.email == email, Producer.id != produtor.id).first():
            raise HTTPException(400, "E-mail já usado por outro produtor.")
        produtor.email = email
    if estado is not None and estado.strip():
        produtor.estado = estado.strip().upper()[:2]
    if cidade is not None and cidade.strip():
        produtor.city = geo_service.nome_oficial(cidade, produtor.uf)
    if cidade is not None or estado is not None:
        coords = geo_service.coordenadas(produtor.city, produtor.uf)
        if coords:
            produtor.latitude, produtor.longitude = coords
    if cep is not None:
        produtor.cep = cep.strip() or None
    if endereco is not None:
        produtor.address = endereco.strip() or None
    if endereco_publico is not None:
        produtor.endereco_publico = endereco_publico
    if telefone is not None:
        produtor.telefone = telefone.strip() or None
    if whatsapp is not None and whatsapp.strip():
        numero = numero_nacional(whatsapp)
        if len(numero) not in (10, 11):
            raise HTTPException(400, "WhatsApp inválido.")
        outro = db.query(Producer).filter(Producer.whatsapp == numero, Producer.id != produtor.id).first()
        if outro:
            raise HTTPException(400, "Este WhatsApp já pertence a outro produtor.")
        produtor.whatsapp = numero
    if descricao is not None:
        produtor.description = descricao

    if foto_perfil and foto_perfil.filename:
        antiga = produtor.foto_perfil
        produtor.foto_perfil = await salvar_imagem(foto_perfil, "perfis", str(produtor.id))
        remover_arquivo(antiga)

    db.commit()
    db.refresh(produtor)
    return {"message": "Perfil atualizado com sucesso!", "perfil": _perfil(produtor)}


# ---------------- Recebimentos: conectar conta Mercado Pago (split) ----------------
@router.post("/me/mercadopago/conectar")
def conectar_mercadopago(produtor: Producer = Depends(get_current_producer)):
    """Gera o link de autorização do Mercado Pago (o produtor faz login lá, não aqui)."""
    state = create_access_token(produtor.id, "mp_oauth", timedelta(minutes=15))
    try:
        return {"url": payment_service.url_conexao(state)}
    except payment_service.PaymentError as e:
        raise HTTPException(400, str(e))


@router.delete("/me/mercadopago")
def desconectar_mercadopago(db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    payment_service.desconectar(produtor)
    db.commit()
    return {"message": "Conta Mercado Pago desconectada.", "perfil": _perfil(produtor)}


# ---------------- Plano Premium ----------------
def _assinatura_dict(a: PremiumSubscription) -> dict:
    pago = a.status == PEDIDO_PAGO
    return {
        "codigo": a.codigo, "valor": a.valor, "status": a.status, "gateway": a.gateway,
        "modo": payment_service.modo_pagamento(), "public_key": payment_service.public_key_para(None),
        "metodo": a.metodo, "metodo_nome": METODOS.get(a.metodo or ""),
        "pix_qr_code": None if pago else a.pix_qr_code, "pix_qr_base64": None if pago else a.pix_qr_base64,
        "premium": a.producer.is_premium,
        "premium_ate": a.producer.premium_ate.isoformat() if a.producer.premium_ate else None,
    }


def _minha_assinatura(db: Session, codigo: str, produtor: Producer) -> PremiumSubscription:
    a = db.query(PremiumSubscription).filter(PremiumSubscription.codigo == codigo).first()
    if not a or a.producer_id != produtor.id:
        raise HTTPException(404, "Assinatura não encontrada")
    return a


@router.post("/me/premium")
def assinar_premium(db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    """Cria a cobrança da mensalidade Premium (paga com crédito, débito ou PIX)."""
    assinatura = PremiumSubscription(producer_id=produtor.id, valor=settings.PREMIUM_PRICE,
                                     gateway=payment_service.modo_pagamento())
    db.add(assinatura)
    db.commit()
    db.refresh(assinatura)
    return _assinatura_dict(assinatura)


@router.get("/me/premium/{codigo}")
def status_premium(codigo: str, db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    assinatura = _minha_assinatura(db, codigo, produtor)
    sincronizar(db, assinatura)
    return _assinatura_dict(assinatura)


@router.post("/me/premium/{codigo}/pagar")
def pagar_premium(codigo: str, dados: PagamentoBrick, db: Session = Depends(get_db),
                  produtor: Producer = Depends(get_current_producer)):
    assinatura = _minha_assinatura(db, codigo, produtor)
    pagar_com_brick(db, assinatura, dados, valor=assinatura.valor,
                    descricao="Mercado Nativo — Plano Premium (30 dias)", producer=None, cobrar_comissao=False)
    db.refresh(assinatura)
    return _assinatura_dict(assinatura)


@router.post("/me/premium/{codigo}/simular")
def simular_premium(codigo: str, dados: PagamentoSimulado, db: Session = Depends(get_db),
                    produtor: Producer = Depends(get_current_producer)):
    assinatura = _minha_assinatura(db, codigo, produtor)
    pagar_simulado(db, assinatura, dados)
    db.refresh(assinatura)
    return _assinatura_dict(assinatura)


@router.post("/me/premium/{codigo}/simular/confirmar-pix")
def simular_premium_pix(codigo: str, db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    assinatura = _minha_assinatura(db, codigo, produtor)
    confirmar_pix_simulado(db, assinatura)
    db.refresh(assinatura)
    return _assinatura_dict(assinatura)


# ---------------- Pedidos recebidos ----------------
def _pedido_dict(o: Order) -> dict:
    return {
        "id": o.id,
        "cliente": o.consumidor_nome,
        "whatsapp": o.consumidor_whatsapp,
        "itens": [{"produto": i.nome_produto, "quantidade": i.quantidade, "preco": i.preco_unitario} for i in o.itens],
        "valor_total": o.valor_total,
        "valor_produtor": o.valor_produtor,
        "taxa_plataforma": o.taxa_plataforma,
        "status": o.status,
        "metodo": METODOS.get(o.metodo or "", "PIX"),
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "paid_at": o.paid_at.isoformat() if o.paid_at else None,
    }


@router.get("/me/orders")
def meus_pedidos(db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    pedidos = (
        db.query(Order).filter(Order.producer_id == produtor.id, Order.status.in_([PEDIDO_PAGO, PEDIDO_RETIRADO]))
        .order_by(Order.id.desc()).limit(50).all()
    )
    return [_pedido_dict(o) for o in pedidos]


@router.patch("/me/orders/{order_id}/retirado")
def marcar_retirado(order_id: int, db: Session = Depends(get_db), produtor: Producer = Depends(get_current_producer)):
    pedido = db.get(Order, order_id)
    if not pedido or pedido.producer_id != produtor.id:
        raise HTTPException(404, "Pedido não encontrado")
    if pedido.status != PEDIDO_PAGO:
        raise HTTPException(400, "Só pedidos pagos podem ser marcados como retirados.")
    pedido.status = PEDIDO_RETIRADO
    db.commit()
    return _pedido_dict(pedido)
