"""
Popula o banco com dados de demonstração (os mesmos dos protótipos do TCC).

Uso (na pasta backend, com o venv ativo):
    python -m app.seed

Só insere se ainda não houver produtos cadastrados — seguro para rodar mais de uma vez.
"""
import json
from datetime import datetime, timedelta

import app.models  # noqa: F401
from app.db.database import SessionLocal, engine
from app.db.migrations import run_migrations
from app.models.order_model import PEDIDO_PAGO, Order, OrderItem, PremiumSubscription
from app.models.product_model import STATUS_APROVADO, STATUS_PENDENTE, Product
from app.models.review_model import Review
from app.models.user_model import Producer
from app.services import geo_service
from app.services.ai_service import analisar_produto

PRODUTORES = [
    dict(name="Dona Carmem", business_name="Doce Querência", whatsapp="68999112233", city="Rio Branco",
         address="Estrada da Borracha, Km 05, Zona Rural", cep="69930-000", endereco_publico=True, premium=True,
         description="A Doce Querência nasceu do amor de Dona Carmem pelas frutas amazônicas. Com receitas passadas "
                     "de geração em geração, ela transforma as frutas do próprio quintal em geleias puras, sem "
                     "conservantes e cheias de afeto. Cada pote é um pedaço da história de sua família."),
    dict(name="João Pereira", business_name="Horta do João", whatsapp="68999220011", city="Senador Guiomard",
         description="Hortaliças orgânicas cultivadas com sementes crioulas e adubo natural."),
    dict(name="Vitória Santos", business_name="Horticultura Vitória", whatsapp="68999330022", city="Senador Guiomard",
         description="Horta familiar agroecológica, colheita fresca toda semana."),
    dict(name="Seu Antônio", business_name="Fazenda Boa Vista", whatsapp="68999440033", city="Rio Branco",
         description="Doces caseiros feitos no tacho, receita de família."),
    dict(name="Dona Maria", business_name="Ateliê Dona Maria", whatsapp="68999550044", city="Xapuri", premium=True,
         description="Crochê e artesanato feitos à mão em Xapuri."),
    dict(name="Mestre Carlos", business_name="Arte em Barro", whatsapp="68999660055", city="Rio Branco", premium=True,
         description="Cerâmica artesanal inspirada na tradição marajoara."),
]

HISTORIA_GELEIA = ("Cada pote carrega o tempo exato de maturação da fruta no pé. Dona Carmem colhe no quintal de sua "
                   "casa e cozinha em fogo brando...")
DESC_GELEIA = "Geleias artesanais feitas com frutas selecionadas e açúcar orgânico. Sem conservantes químicos."

PRODUTOS = [
    # (loja, nome, preço, categoria, estoque, destaque, status, descrição, história)
    ("Doce Querência", "Geleias de Manga Orgânicas", 28.0, "Alimentos", 12, True, STATUS_APROVADO, DESC_GELEIA, HISTORIA_GELEIA),
    ("Doce Querência", "Geleias de Goiaba Orgânicas", 28.0, "Alimentos", 12, True, STATUS_APROVADO, DESC_GELEIA, HISTORIA_GELEIA),
    ("Doce Querência", "Geleias de Cupuaçu Orgânico", 28.0, "Alimentos", 12, True, STATUS_APROVADO, DESC_GELEIA, HISTORIA_GELEIA),
    ("Ateliê Dona Maria", "Jogo Tapete Banheiro 3P Crochê", 28.0, "Artesanato", 5, True, STATUS_APROVADO,
     "Jogo com 3 peças em crochê feito à mão com barbante 100% algodão.", "Peças tecidas à mão, uma a uma, nas tardes de Xapuri."),
    ("Horta do João", "Alface Crespa Orgânica", 4.5, "Hortifruti", 3, False, STATUS_APROVADO,
     "Alface crespa orgânica, colhida no dia.", "Cultivada sem agrotóxicos, com adubo natural do próprio sítio."),
    ("Horta do João", "Cenoura Orgânica", 4.5, "Hortifruti", 20, False, STATUS_APROVADO,
     "Cenoura orgânica, maço com cerca de 500 g.", "Plantada em canteiros agroecológicos, colheita fresca."),
    ("Horticultura Vitória", "Alface Lisa Orgânica", 4.5, "Hortifruti", 15, False, STATUS_APROVADO,
     "Alface lisa orgânica, colhida no dia.", "Horta familiar, colheita fresca toda manhã."),
    ("Horticultura Vitória", "Tomate Cereja", 4.5, "Hortifruti", 18, False, STATUS_APROVADO,
     "Bandeja de 250 g de tomate cereja cultivado sem agrotóxicos.", "Da horta da família direto para a sua mesa."),
    ("Fazenda Boa Vista", "Doce de Leite na Palha", 15.0, "Alimentos", 0, False, STATUS_APROVADO,
     "Doce de leite caseiro embalado na palha de milho.", "Feito no tacho de cobre, mexido por horas no fogo a lenha."),
    ("Arte em Barro", "Vaso de Cerâmica Marajoara", 120.0, "Artesanato", 4, True, STATUS_APROVADO,
     "Vaso de cerâmica artesanal com grafismos marajoaras pintados à mão.", "Modelado em barro e queimado em forno a lenha."),
    ("Horta do João", "Melancia Orgânica (Unidade)", 18.0, "Hortifruti", 10, False, STATUS_PENDENTE,
     "Melancia doce cultivada sem agrotóxicos.",
     "Sementes crioulas passadas pela minha família há 3 gerações. Cultivada no tempo certo, com adubo 100% natural orgânico."),
]


def main() -> None:
    run_migrations(engine)
    db = SessionLocal()
    try:
        if db.query(Product).count() > 0:
            print("O banco já possui produtos — seed ignorado.")
            return

        lojas: dict[str, Producer] = {}
        for dados in PRODUTORES:
            existente = db.query(Producer).filter(Producer.whatsapp == dados["whatsapp"]).first()
            if existente:
                lojas[dados["business_name"]] = existente
                continue
            lat, lng = geo_service.coordenadas(dados["city"], "AC")
            premium = dados.pop("premium", False)
            p = Producer(**dados, estado="AC", latitude=lat, longitude=lng, premium=premium,
                         premium_ate=datetime.utcnow() + timedelta(days=30) if premium else None)
            db.add(p)
            db.flush()
            lojas[p.business_name] = p
            if premium:
                db.add(PremiumSubscription(producer_id=p.id, valor=9.90, status=PEDIDO_PAGO,
                                           gateway="simulado", paid_at=datetime.utcnow() - timedelta(hours=5)))

        produtos: dict[str, Product] = {}
        for loja, nome, preco, cat, est, dest, status, desc, hist in PRODUTOS:
            prod = Product(
                nome=nome, preco=preco, categoria=cat, estoque=est, destaque=dest, status=status,
                descricao_tecnica=desc, historia=hist, producer_id=lojas[loja].id,
                visualizacoes=340 if loja == "Doce Querência" else 60, contatos_whatsapp=20,
                analise_ia=json.dumps(analisar_produto(nome, desc, hist, cat), ensure_ascii=False),
                created_at=datetime.utcnow() - timedelta(hours=2),
            )
            db.add(prod)
            produtos[nome] = prod
        db.flush()

        db.add(Review(product_id=produtos["Geleias de Cupuaçu Orgânico"].id, nome="Mariana Silva", nota=5,
                      comentario="A geleia de cupuaçu me lembrou a infância na casa da minha avó! "
                                 "Dá pra sentir que é feita com muito amor."))
        for nome in ["Geleias de Manga Orgânicas", "Geleias de Goiaba Orgânicas", "Alface Crespa Orgânica"]:
            db.add(Review(product_id=produtos[nome].id, nome="Carlos Eduardo", nota=5, comentario="Excelente!"))

        vendas = [("Geleias de Manga Orgânicas", 2, "Mariana Silva", "pix"),
                  ("Vaso de Cerâmica Marajoara", 1, "Carlos Eduardo", "credit_card")]
        for nome, qtd, cliente, metodo in vendas:
            prod = produtos[nome]
            total = round(prod.preco * qtd, 2)
            pedido = Order(producer_id=prod.producer_id, consumidor_nome=cliente, consumidor_whatsapp="68999000000",
                           valor_total=total, taxa_plataforma=round(total * 0.10, 2),
                           valor_produtor=round(total * 0.90, 2), status=PEDIDO_PAGO, gateway="simulado", metodo=metodo,
                           split_aplicado=True, paid_at=datetime.utcnow() - timedelta(hours=1))
            pedido.itens.append(OrderItem(product_id=prod.id, nome_produto=prod.nome, quantidade=qtd,
                                          preco_unitario=prod.preco))
            db.add(pedido)

        db.commit()
        print(f"✅ Dados de demonstração criados: {len(lojas)} produtores e {len(produtos)} produtos.")
        print("   Login de produtor demo: WhatsApp (68) 9 9911-2233 (Doce Querência, Premium)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
