"""Exclusão de publicações e vendedores, exclusão da própria conta e aceite dos termos (LGPD)."""
from conftest import _login_produtor
from test_products import _criar


def _novo_produtor(client, whatsapp, nome="Sítio Teste"):
    r = client.post("/api/v1/auth/producer/register", json={
        "aceite_termos": True, "name": "Fulano", "business_name": nome, "whatsapp": whatsapp, "city": "Xapuri"})
    assert r.status_code == 201, r.text
    return _login_produtor(client, whatsapp)


def test_cadastro_exige_aceite_dos_termos(client):
    r = client.post("/api/v1/auth/producer/register", json={
        "name": "Sem Aceite", "business_name": "Teste", "whatsapp": "68977770000", "city": "Xapuri"})
    assert r.status_code == 400
    assert "Termos" in r.json()["detail"]


def test_admin_exclui_publicacao(client, admin):
    h = _novo_produtor(client, "68977771111", "Horta Exclusão")
    p = _criar(client, h, nome="Alface Para Excluir")
    client.post(f"/api/v1/admin/products/{p['id']}/aprovar", headers=admin)
    assert client.get(f"/api/v1/public/products/{p['id']}").status_code == 200

    r = client.delete(f"/api/v1/admin/products/{p['id']}", headers=admin, params={"motivo": "Foto de outra pessoa"})
    assert r.status_code == 200, r.text
    assert client.get(f"/api/v1/public/products/{p['id']}").status_code == 404
    assert client.get(f"/api/v1/admin/products/{p['id']}", headers=admin).status_code == 404
    # produtor não precisa de nada: o produto sumiu do painel dele
    assert all(x["id"] != p["id"] for x in client.get("/api/v1/dashboard/me", headers=h).json()["produtos"])


def test_so_super_admin_exclui_vendedor_e_dados_somem(client, admin):
    h = _novo_produtor(client, "68977772222", "Ateliê Para Excluir")
    p = _criar(client, h, nome="Cesto de Palha")
    client.post(f"/api/v1/admin/products/{p['id']}/aprovar", headers=admin)
    vendedores = client.get("/api/v1/admin/producers", headers=admin, params={"q": "ateliê para"}).json()
    assert len(vendedores) == 1
    vid = vendedores[0]["id"]

    # admin comum não pode
    client.post("/api/v1/auth/admin/register", headers=admin, json={"nome": "Comum", "email": "comum@teste.com", "senha": "12345678"})
    r = client.post("/api/v1/auth/admin/login", json={"email": "comum@teste.com", "senha": "12345678"})
    comum = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.delete(f"/api/v1/admin/producers/{vid}", headers=comum).status_code == 403

    r = client.delete(f"/api/v1/admin/producers/{vid}", headers=admin)
    assert r.status_code == 200, r.text
    assert client.get(f"/api/v1/public/producers/{vid}").status_code == 404
    assert client.get(f"/api/v1/public/products/{p['id']}").status_code == 404
    assert all(v["id"] != vid for v in client.get("/api/v1/admin/producers", headers=admin).json())
    # o login antigo deixa de funcionar e o número pode ser usado de novo
    assert client.get("/api/v1/producers/me", headers=h).status_code == 401
    from app.db.database import SessionLocal
    from app.models.user_model import Producer
    db = SessionLocal()
    v = db.get(Producer, vid)
    assert v.whatsapp is None and v.name == "Vendedor removido" and v.address is None and v.excluido_em
    db.close()
    assert client.post("/api/v1/auth/producer/register", json={
        "aceite_termos": True, "name": "Fulano", "business_name": "Volta", "whatsapp": "68977772222"}).status_code == 201


def test_produtor_baixa_dados_e_exclui_a_conta(client):
    h = _novo_produtor(client, "68977773333", "Doces da Serra")
    _criar(client, h, nome="Doce de Buriti")
    dados = client.get("/api/v1/producers/me/dados", headers=h).json()
    assert dados["perfil"]["nome_do_negocio"] == "Doces da Serra"
    assert dados["perfil"]["termos_aceitos_em"] and dados["perfil"]["versao_dos_termos"]
    assert dados["produtos"][0]["nome"] == "Doce de Buriti"

    assert client.delete("/api/v1/producers/me", headers=h).status_code == 200
    assert client.get("/api/v1/producers/me", headers=h).status_code == 401
    r = client.post("/api/v1/auth/producer/request-code", json={"whatsapp": "68977773333"})
    assert r.status_code in (200, 404)  # número não leva mais a conta nenhuma
