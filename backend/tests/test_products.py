import io

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
       b"\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


def _criar(client, headers, **extra):
    dados = {"nome": "Geleia de Cupuaçu", "preco": "28", "categoria": "Alimentos", "estoque": "12",
             "descricao_tecnica": "Geleia artesanal sem conservantes, feita com açúcar orgânico.",
             "historia": "Receita de família, colhida no quintal e cozida em fogo brando por horas."}
    dados.update(extra)
    files = [("imagens", ("foto.png", io.BytesIO(PNG), "image/png"))]
    r = client.post("/api/v1/products", headers=headers, data=dados, files=files)
    assert r.status_code == 201, r.text
    return r.json()


def test_fluxo_completo(client, produtor, admin):
    prod = _criar(client, produtor)
    assert prod["status"] == "pendente"
    assert prod["imagens"][0]["url"].startswith("/uploads/produtos/")

    # Pendente não aparece na vitrine
    assert all(p["id"] != prod["id"] for p in client.get("/api/v1/public/products").json())

    # Curadoria com análise da IA
    det = client.get(f"/api/v1/admin/products/{prod['id']}", headers=admin).json()
    assert det["analise_ia"]["score"] >= 70
    assert "sem conservantes" in det["analise_ia"]["positivas"]
    assert det["analise_ia"]["negativas"] == []
    assert client.post(f"/api/v1/admin/products/{prod['id']}/aprovar", headers=admin).status_code == 200

    # Vitrine + filtro geográfico
    vitrine = client.get("/api/v1/public/products", params={"cidade": "Rio Branco", "raio_km": 30}).json()
    assert any(p["id"] == prod["id"] for p in vitrine)
    longe = client.get("/api/v1/public/products", params={"cidade": "Cruzeiro do Sul", "raio_km": 50}).json()
    assert all(p["id"] != prod["id"] for p in longe)
    assert client.get("/api/v1/public/products", params={"categoria": "Artesanato"}).json() == []

    # Página pública conta visita; WhatsApp conta contato
    pub = client.get(f"/api/v1/public/products/{prod['id']}").json()
    assert pub["produtor"]["endereco"] is None   # privacidade: endereço oculto por padrão
    link = client.post(f"/api/v1/public/products/{prod['id']}/contato").json()["link"]
    assert link.startswith("https://wa.me/5568999112233")

    # Avaliação
    r = client.post(f"/api/v1/public/products/{prod['id']}/reviews",
                    json={"nome": "Mariana Silva", "nota": 5, "comentario": "Maravilhosa!"})
    assert r.status_code == 201
    assert client.get(f"/api/v1/public/products/{prod['id']}", params={"registrar_visita": False}).json()["nota_media"] == 5.0

    antes = client.get("/api/v1/dashboard/me", headers=produtor).json()["estatisticas"]
    ov_antes = client.get("/api/v1/admin/overview", headers=admin).json()["financeiro"]

    # Checkout com split 90/10 e baixa de estoque
    pedido = client.post("/api/v1/checkout", json={"product_id": prod["id"], "quantidade": 2,
                                                  "nome": "Mariana Silva", "whatsapp": "68 99999-0000"}).json()
    assert pedido["valor_total"] == 56.0
    assert "valor_produtor" not in pedido and "taxa_plataforma" not in pedido  # divisão não vai para o comprador
    assert pedido["status"] == "aguardando_pagamento"
    assert len(pedido["codigo"]) >= 20 and "whatsapp" not in str(pedido.get("cliente"))
    assert client.get("/api/v1/checkout/1").status_code == 404        # não dá para adivinhar pedidos
    pago = client.post(f"/api/v1/checkout/{pedido['codigo']}/simular",
                       json={"metodo": "debit_card"}).json()
    assert pago["status"] == "pago" and pago["whatsapp_link"] and pago["metodo_nome"] == "Débito"
    # Pagar de novo o mesmo pedido não é permitido
    assert client.post(f"/api/v1/checkout/{pedido['codigo']}/simular", json={"metodo": "pix"}).status_code == 400
    assert client.get(f"/api/v1/products/{prod['id']}", headers=produtor).json()["estoque"] == 10

    # Estoque insuficiente
    r = client.post("/api/v1/checkout", json={"product_id": prod["id"], "quantidade": 50,
                                             "nome": "Xavier", "whatsapp": "68999990000"})
    assert r.status_code == 400

    # Painel do produtor com métricas reais
    dash = client.get("/api/v1/dashboard/me", headers=produtor).json()
    assert dash["estatisticas"]["visitas"] >= 1
    assert dash["estatisticas"]["vendas_concluidas"] == antes["vendas_concluidas"] + 1
    assert round(dash["estatisticas"]["receita_total"] - antes["receita_total"], 2) == 50.4

    # Admin: extrato de split
    ov = client.get("/api/v1/admin/overview", headers=admin).json()
    assert round(ov["financeiro"]["volume_transacionado"] - ov_antes["volume_transacionado"], 2) == 56.0
    assert round(ov["financeiro"]["receita_plataforma"] - ov_antes["receita_plataforma"], 2) == 5.6
    assert ov["extrato_split"][0]["repasse_produtor"] == 50.4

    # Editar preço/estoque não volta para curadoria; mudar a história volta
    base = {"nome": "Geleia de Cupuaçu", "preco": "30", "categoria": "Alimentos", "estoque": "8",
            "descricao_tecnica": "Geleia artesanal sem conservantes, feita com açúcar orgânico.",
            "historia": "Receita de família, colhida no quintal e cozida em fogo brando por horas."}
    r = client.put(f"/api/v1/products/{prod['id']}", headers=produtor, data=base)
    assert r.json()["status"] == "aprovado" and r.json()["preco"] == 30.0
    base["historia"] = "Nova história"
    assert client.put(f"/api/v1/products/{prod['id']}", headers=produtor, data=base).json()["status"] == "pendente"


def test_curadoria_detecta_industrializado(client, produtor, admin):
    prod = _criar(client, produtor, nome="Refrigerante de Guaraná",
                  descricao_tecnica="Produto industrializado de revenda, com corante e aromatizante.", historia="")
    det = client.get(f"/api/v1/admin/products/{prod['id']}", headers=admin).json()
    assert det["analise_ia"]["negativas"]
    assert det["analise_ia"]["recomendacao"] != "aprovar"
    r = client.post(f"/api/v1/admin/products/{prod['id']}/rejeitar", headers=admin, json={"motivo": "Produto industrial"})
    assert r.json()["status"] == "rejeitado"


def test_premium_calculadora_e_destaque(client, produtor, admin):
    calc = {"nome": "Geleia de Cupuaçu", "rendimento": 10, "margem": 50,
            "itens": [{"descricao": "Polpa", "valor": 25}, {"descricao": "Açúcar", "valor": 8.5},
                      {"descricao": "Potes", "valor": 45}]}
    assert client.post("/api/v1/calculadora/calcular", headers=produtor, json=calc).status_code == 403

    assinatura = client.post("/api/v1/producers/me/premium", headers=produtor).json()
    assert assinatura["status"] == "aguardando_pagamento"
    r = client.post(f"/api/v1/producers/me/premium/{assinatura['codigo']}/simular", headers=produtor, json={"metodo": "pix"})
    assert r.json()["pix_qr_code"] and r.json()["premium"] is False       # PIX gerado, aguardando
    r = client.post(f"/api/v1/producers/me/premium/{assinatura['codigo']}/simular/confirmar-pix", headers=produtor)
    assert r.json()["premium"] is True

    res = client.post("/api/v1/calculadora/calcular", headers=produtor, json=calc).json()
    assert res == {"custo_total": 78.5, "custo_unitario": 7.85, "preco_sugerido": 11.78, "produto_atualizado": None}

    # Destaque só para Premium + aprovado
    prod = _criar(client, produtor, nome="Geleia de Manga")
    assert client.patch(f"/api/v1/admin/products/{prod['id']}/destaque", headers=admin,
                        json={"destaque": True}).status_code == 400
    client.post(f"/api/v1/admin/products/{prod['id']}/aprovar", headers=admin)
    assert client.patch(f"/api/v1/admin/products/{prod['id']}/destaque", headers=admin,
                        json={"destaque": True}).status_code == 200
    vitrine = client.get("/api/v1/public/products").json()
    assert vitrine[0]["id"] == prod["id"] and vitrine[0]["destaque"] is True

    premium = client.get("/api/v1/admin/premium", headers=admin).json()
    assert premium[0]["premium"] is True


def test_produtor_nao_edita_produto_de_outro(client, produtor):
    client.post("/api/v1/auth/producer/register", json={"aceite_termos": True, 
        "name": "João", "business_name": "Horta do João", "whatsapp": "68999220011", "city": "Xapuri"})
    from tests.conftest import _login_produtor
    joao = _login_produtor(client, "68999220011")
    prod = _criar(client, produtor, nome="Doce")
    assert client.get(f"/api/v1/products/{prod['id']}", headers=joao).status_code == 404
    assert client.delete(f"/api/v1/products/{prod['id']}", headers=joao).status_code == 404
