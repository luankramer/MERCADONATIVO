def test_cadastro_duplicado_e_login(client, produtor):
    r = client.post("/api/v1/auth/producer/register", json={"aceite_termos": True, 
        "name": "Outra", "business_name": "Outra", "whatsapp": "68999112233"})
    assert r.status_code == 400

    r = client.get("/api/v1/producers/me", headers=produtor)
    assert r.status_code == 200
    dados = r.json()
    assert dados["cidade"] == "Rio Branco"          # nome normalizado
    assert dados["whatsapp"] == "68999112233"       # só dígitos


def test_login_numero_nao_cadastrado(client):
    r = client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "68900000000"})
    assert r.status_code == 404


def test_codigo_incorreto(client, produtor):
    client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "68999112233"})
    r = client.post("/api/v1/auth/producer/verify-code", json={"whatsapp": "68999112233", "code": "000000x"})
    assert r.status_code == 401


def test_rotas_protegidas(client):
    assert client.get("/api/v1/dashboard/me").status_code == 401
    assert client.get("/api/v1/admin/overview").status_code == 401


def test_admin_gestao(client, admin):
    r = client.post("/api/v1/auth/admin/register", headers=admin,
                    json={"nome": "Ana", "email": "ana@teste.com", "senha": "12345678"})
    assert r.status_code == 201
    lista = client.get("/api/v1/auth/admin/list", headers=admin).json()
    assert any(a["email"] == "ana@teste.com" and not a["is_super"] for a in lista)

    # Administrador comum não pode criar outros
    r = client.post("/api/v1/auth/admin/login", json={"email": "ana@teste.com", "senha": "12345678"})
    ana = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.post("/api/v1/auth/admin/register", headers=ana,
                    json={"nome": "X", "email": "x@teste.com", "senha": "12345678"})
    assert r.status_code == 403
    # Token de admin não serve como produtor
    assert client.get("/api/v1/dashboard/me", headers=ana).status_code == 403


def test_ia_fallback(client):
    r = client.post("/api/v1/ai/generate", json={"prompt": "orgânico, receita de família", "tipo": "produto"})
    assert r.status_code == 200
    assert r.json()["fonte"] == "modelo"
    assert "receita de família" in r.json()["texto"]


def test_bloqueio_de_forca_bruta_no_admin(client):
    for _ in range(5):
        r = client.post("/api/v1/auth/admin/login", json={"email": "mestre@teste.com", "senha": "errada"})
        assert r.status_code == 401
    r = client.post("/api/v1/auth/admin/login", json={"email": "mestre@teste.com", "senha": "senha123"})
    assert r.status_code == 429   # bloqueado mesmo com a senha certa até passar o tempo


def test_limite_de_codigos_whatsapp(client, produtor):
    for _ in range(3):
        assert client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "68999112233"}).status_code == 200
    assert client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "68999112233"}).status_code == 429


def test_token_forjado_e_rejeitado(client):
    import base64, json
    corpo = base64.urlsafe_b64encode(json.dumps({"sub": "1", "role": "admin", "exp": 9999999999}).encode()).decode().rstrip("=")
    falso = f"eyJhbGciOiJIUzI1NiJ9.{corpo}.assinaturafalsa"
    assert client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_upload_disfarcado_e_bloqueado(client, produtor):
    import io
    falso = io.BytesIO(b"<script>alert(1)</script>")
    r = client.post("/api/v1/products", headers=produtor, files=[("imagens", ("foto.png", falso, "image/png"))],
                    data={"nome": "X", "preco": "10", "categoria": "Alimentos", "estoque": "1"})
    assert r.status_code == 400


def test_cabecalhos_de_seguranca(client):
    r = client.get("/")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
