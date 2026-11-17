"""
Controle financeiro do mês: quanto entrou, quanto o Mercado Pago cobrou, a comissão do Mercado Nativo
e quanto precisa ser repassado a cada produtor.

Dois caminhos do dinheiro:
- "direto": o produtor conectou a conta Mercado Pago. O valor cai na conta dele e a comissão na
  da plataforma (split). Não há repasse a fazer.
- "plataforma": o produtor não estava conectado (ou foi Pix de reserva). O valor cai na conta do
  Mercado Nativo, que repassa ao produtor no fim do mês, descontando a taxa do Mercado Pago e a comissão.
"""
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.order_model import METODOS, PEDIDO_CANCELADO, PEDIDO_PAGO, PEDIDO_RETIRADO, Order
from app.models.repasse_model import Repasse
from app.services.payment_service import estimar_taxa_mp


class FinanceiroError(Exception):
    pass


def mes_valido(mes: str | None) -> str:
    """'2026-11'. Sem mês: o mês atual (no fuso de Rio Branco)."""
    if not mes:
        return (datetime.utcnow() + timedelta(hours=settings.FUSO_HORAS)).strftime("%Y-%m")
    try:
        datetime.strptime(mes, "%Y-%m")
    except ValueError as e:
        raise FinanceiroError("Mês inválido. Use o formato AAAA-MM, ex.: 2026-11.") from e
    return mes


def intervalo_utc(mes: str) -> tuple[datetime, datetime]:
    """Início e fim do mês (horário local) convertidos para UTC, como o banco guarda as datas."""
    inicio_local = datetime.strptime(mes, "%Y-%m")
    fim_local = (inicio_local.replace(day=28) + timedelta(days=4)).replace(day=1)
    deslocamento = timedelta(hours=-settings.FUSO_HORAS)
    return inicio_local + deslocamento, fim_local + deslocamento


def taxa_mp(o: Order) -> float:
    if o.taxa_mercadopago is not None:
        return float(o.taxa_mercadopago)
    return estimar_taxa_mp(o.valor_total, o.metodo, o.gateway)


def liquido(o: Order) -> float:
    return round(max(0.0, o.valor_total - (o.taxa_plataforma or 0) - taxa_mp(o)), 2)


def caminho(o: Order) -> str:
    return "direto" if o.split_aplicado else "plataforma"


def _local(dt: datetime | None) -> str | None:
    return (dt + timedelta(hours=settings.FUSO_HORAS)).strftime("%d/%m/%Y %H:%M") if dt else None


def pedidos_do_mes(db: Session, mes: str) -> list[Order]:
    inicio, fim = intervalo_utc(mes)
    return (db.query(Order).options(joinedload(Order.producer), joinedload(Order.itens))
            .filter(Order.paid_at >= inicio, Order.paid_at < fim, Order.gateway != "simulado")
            .order_by(Order.paid_at).all())


def pedido_linha(o: Order) -> dict:
    return {
        "id": o.id,
        "pago_em": _local(o.paid_at),
        "produtor_id": o.producer_id,
        "loja": o.producer.business_name if o.producer else "(removido)",
        "itens": ", ".join(f"{i.quantidade}x {i.nome_produto}" for i in o.itens),
        "metodo": METODOS.get(o.metodo or "", "PIX"),
        "status": o.status,
        "valor": round(o.valor_total, 2),
        "taxa_mercadopago": round(taxa_mp(o), 2),
        "taxa_real": bool(o.taxa_mp_real),
        "comissao": round(o.taxa_plataforma or 0, 2),
        "produtor_recebe": liquido(o),
        "caminho": caminho(o),
        "repasse_id": o.repasse_id,
    }


@dataclass
class _Produtor:
    producer_id: int | None
    loja: str
    nome: str
    whatsapp: str
    pedidos_direto: int = 0
    pedidos_plataforma: int = 0
    vendas: float = 0
    taxa_mp: float = 0
    comissao: float = 0
    recebeu_direto: float = 0
    a_repassar: float = 0
    repassado: float = 0
    repasses: list = field(default_factory=list)


def relatorio(db: Session, mes: str) -> dict:
    mes = mes_valido(mes)
    pedidos = pedidos_do_mes(db, mes)
    validos = [o for o in pedidos if o.status in (PEDIDO_PAGO, PEDIDO_RETIRADO)]
    por_produtor: dict[int | None, _Produtor] = {}
    for o in validos:
        p = o.producer
        item = por_produtor.setdefault(o.producer_id, _Produtor(
            o.producer_id, p.business_name if p else "(removido)", p.name if p else "", p.whatsapp if p else ""))
        item.vendas += o.valor_total
        item.taxa_mp += taxa_mp(o)
        item.comissao += o.taxa_plataforma or 0
        if caminho(o) == "direto":
            item.pedidos_direto += 1
            item.recebeu_direto += liquido(o)
        elif o.repasse_id:
            item.pedidos_plataforma += 1
            item.repassado += liquido(o)
        else:
            item.pedidos_plataforma += 1
            item.a_repassar += liquido(o)

    repasses = db.query(Repasse).filter(Repasse.mes == mes).order_by(Repasse.id).all()
    for r in repasses:
        if r.producer_id in por_produtor:
            por_produtor[r.producer_id].repasses.append(
                {"id": r.id, "valor": r.valor_repasse, "pago_em": _local(r.pago_em), "observacao": r.observacao or ""})

    # Devolvidos depois de já terem sido repassados: descontar no próximo repasse
    inicio, fim = intervalo_utc(mes)
    ajustes = (db.query(Order).filter(Order.status == PEDIDO_CANCELADO, Order.repasse_id.isnot(None),
                                      Order.cancelado_em >= inicio, Order.cancelado_em < fim).all())

    def r2(v: float) -> float:
        return round(v, 2)

    produtores = []
    for p in sorted(por_produtor.values(), key=lambda x: -x.a_repassar):
        produtores.append({
            "producer_id": p.producer_id, "loja": p.loja, "nome": p.nome, "whatsapp": p.whatsapp,
            "pedidos_direto": p.pedidos_direto, "pedidos_plataforma": p.pedidos_plataforma,
            "vendas": r2(p.vendas), "taxa_mercadopago": r2(p.taxa_mp), "comissao": r2(p.comissao),
            "recebeu_direto": r2(p.recebeu_direto), "a_repassar": r2(p.a_repassar), "repassado": r2(p.repassado),
            "situacao": "pendente" if p.a_repassar > 0 else ("pago" if p.repassado > 0 else "sem_repasse"),
            "repasses": p.repasses,
        })
    plataforma = [o for o in validos if caminho(o) == "plataforma"]
    return {
        "mes": mes,
        "taxas_tabela": {"pix": settings.TAXA_MP_PIX, "credito": settings.TAXA_MP_CREDITO,
                         "debito": settings.TAXA_MP_DEBITO, "comissao": settings.PLATFORM_FEE_PERCENT},
        "resumo": {
            "pedidos": len(validos),
            "vendas": r2(sum(o.valor_total for o in validos)),
            "taxa_mercadopago": r2(sum(taxa_mp(o) for o in validos)),
            "comissao": r2(sum(o.taxa_plataforma or 0 for o in validos)),
            # Entrou na conta Mercado Pago da plataforma (já sem a taxa do Mercado Pago)
            "entrou_na_plataforma": r2(sum(o.valor_total - taxa_mp(o) for o in plataforma)
                                       + sum(o.taxa_plataforma or 0 for o in validos if caminho(o) == "direto")),
            "a_repassar": r2(sum(p["a_repassar"] for p in produtores)),
            "repassado": r2(sum(p["repassado"] for p in produtores)),
            "recebido_direto_pelos_produtores": r2(sum(p["recebeu_direto"] for p in produtores)),
            "cancelados": sum(1 for o in pedidos if o.status == PEDIDO_CANCELADO),
        },
        "produtores": produtores,
        "pedidos": [pedido_linha(o) for o in pedidos],
        "ajustes": [{"id": o.id, "loja": o.producer.business_name if o.producer else "", "valor": liquido(o),
                     "repasse_id": o.repasse_id} for o in ajustes],
    }


def registrar_repasse(db: Session, mes: str, producer_id: int, observacao: str | None, admin_id: int) -> Repasse:
    """Marca como pagos ao produtor todos os pedidos do mês que caíram na conta da plataforma."""
    mes = mes_valido(mes)
    pendentes = [o for o in pedidos_do_mes(db, mes)
                 if o.producer_id == producer_id and o.status in (PEDIDO_PAGO, PEDIDO_RETIRADO)
                 and caminho(o) == "plataforma" and not o.repasse_id]
    if not pendentes:
        raise FinanceiroError("Não há valores pendentes de repasse para este produtor neste mês.")
    repasse = Repasse(
        producer_id=producer_id, mes=mes, quantidade_pedidos=len(pendentes),
        valor_vendas=round(sum(o.valor_total for o in pendentes), 2),
        taxa_mercadopago=round(sum(taxa_mp(o) for o in pendentes), 2),
        comissao=round(sum(o.taxa_plataforma or 0 for o in pendentes), 2),
        valor_repasse=round(sum(liquido(o) for o in pendentes), 2),
        observacao=(observacao or "").strip()[:300] or None, admin_id=admin_id,
    )
    db.add(repasse)
    db.flush()
    for o in pendentes:
        o.repasse_id = repasse.id
    db.commit()
    db.refresh(repasse)
    return repasse


def csv_do_mes(dados: dict) -> str:
    """Relatório para abrir no Excel (separador ; e vírgula decimal)."""
    def br(v: float) -> str:
        return f"{v:.2f}".replace(".", ",")

    saida = io.StringIO()
    w = csv.writer(saida, delimiter=";")
    w.writerow([f"Mercado Nativo - relatório financeiro de {dados['mes']}"])
    w.writerow([])
    w.writerow(["Pedido", "Pago em", "Loja", "Itens", "Forma", "Situação", "Valor da venda",
                "Taxa Mercado Pago", "Taxa real?", "Comissão Mercado Nativo", "Produtor recebe",
                "Onde caiu o dinheiro", "Repasse"])
    situacoes = {"pago": "Pago", "retirado": "Retirado", "cancelado": "Cancelado/devolvido"}
    for p in dados["pedidos"]:
        w.writerow([p["id"], p["pago_em"], p["loja"], p["itens"], p["metodo"], situacoes.get(p["status"], p["status"]),
                    br(p["valor"]), br(p["taxa_mercadopago"]), "sim" if p["taxa_real"] else "estimada",
                    br(p["comissao"]), br(p["produtor_recebe"]),
                    "Conta do produtor" if p["caminho"] == "direto" else "Conta do Mercado Nativo",
                    f"nº {p['repasse_id']}" if p["repasse_id"] else ("-" if p["caminho"] == "direto" else "pendente")])
    w.writerow([])
    w.writerow(["Produtor", "WhatsApp", "Vendas", "Taxa Mercado Pago", "Comissão", "Recebeu direto",
                "A repassar", "Já repassado"])
    for p in dados["produtores"]:
        w.writerow([p["loja"], p["whatsapp"], br(p["vendas"]), br(p["taxa_mercadopago"]), br(p["comissao"]),
                    br(p["recebeu_direto"]), br(p["a_repassar"]), br(p["repassado"])])
    r = dados["resumo"]
    w.writerow([])
    w.writerow(["Total vendido", br(r["vendas"])])
    w.writerow(["Taxas do Mercado Pago", br(r["taxa_mercadopago"])])
    w.writerow(["Comissão do Mercado Nativo", br(r["comissao"])])
    w.writerow(["Entrou na conta do Mercado Nativo", br(r["entrou_na_plataforma"])])
    w.writerow(["A repassar aos produtores", br(r["a_repassar"])])
    w.writerow(["Já repassado", br(r["repassado"])])
    return "﻿" + saida.getvalue()  # BOM: o Excel abre com acentos certos
