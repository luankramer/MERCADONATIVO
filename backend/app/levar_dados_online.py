"""
Leva os dados deste computador (MySQL local + fotos) para o Mercado Nativo publicado no Railway.

Uso (na pasta backend):  python -m app.levar_dados_online      (ou scripts/levar_dados_para_o_railway.bat)

1. Exporta o banco local e as fotos para backend/exportacao_mercado_nativo.zip (não vai para o GitHub).
2. Pede o e-mail e a senha do Super Admin do site ONLINE (a senha não aparece ao digitar).
3. Envia o .zip. O servidor troca TODO o conteúdo do banco online pelo deste computador.
   Depois disso, os administradores e as senhas passam a ser os deste computador.

O servidor só aceita com a variável IMPORTACAO_LIBERADA=true. Desligue-a depois.
"""
import getpass
import sys

import requests

from app.core.config import BASE_DIR, settings
from app.db.database import engine
from app.db.migrations import run_migrations
from app.services.importacao_service import exportar

ENDERECO_PADRAO = "https://backend-production-ef5e2dac.up.railway.app"
ARQUIVO = BASE_DIR / "exportacao_mercado_nativo.zip"


def main() -> None:
    print("1/3  Exportando o banco deste computador...")
    run_migrations(engine)  # deixa as tabelas locais no formato atual antes de exportar
    conteudo, resumo = exportar(engine)
    ARQUIVO.write_bytes(conteudo)
    total = sum(resumo["tabelas"].values())
    print(f"     {total} registros e {resumo['fotos']} fotos ({len(conteudo) / 1024 / 1024:.1f} MB) em {ARQUIVO.name}")

    endereco = (input(f"\n2/3  Endereço do backend online [{ENDERECO_PADRAO}]: ").strip() or ENDERECO_PADRAO).rstrip("/")
    if not endereco.startswith("https://"):
        print("O endereço precisa começar com https://")
        sys.exit(1)
    email = input(f"     E-mail do Super Admin online [{settings.ADMIN_MASTER_EMAIL}]: ").strip() or settings.ADMIN_MASTER_EMAIL
    senha = getpass.getpass("     Senha do Super Admin online (não aparece ao digitar): ")

    r = requests.post(f"{endereco}/api/v1/auth/admin/login", json={"email": email, "senha": senha}, timeout=30)
    if r.status_code != 200:
        print(f"Não foi possível entrar: {r.json().get('detail', r.text) if r.headers.get('content-type', '').startswith('application/json') else r.status_code}")
        sys.exit(1)
    token = r.json()["access_token"]

    resposta = input("\n3/3  Isto APAGA os dados do site online e coloca os deste computador. Continuar? (s/n): ")
    if resposta.strip().lower() not in ("s", "sim"):
        print("Cancelado. Nada foi enviado.")
        return
    with ARQUIVO.open("rb") as f:
        r = requests.post(f"{endereco}/api/v1/admin/importacao", headers={"Authorization": f"Bearer {token}"},
                          files={"arquivo": (ARQUIVO.name, f, "application/zip")}, timeout=300)
    if r.status_code == 404:
        print("O servidor não aceitou: falta IMPORTACAO_LIBERADA=true nas variáveis do Backend no Railway.")
        sys.exit(1)
    if r.status_code != 200:
        print(f"Falhou ({r.status_code}): {r.text[:300]}")
        sys.exit(1)
    dados = r.json()
    print(f"\n✅ Pronto! {sum(dados['tabelas'].values())} registros e {dados['fotos']} fotos no site online.")
    print("👉 Agora o login de admin online usa o e-mail e a senha deste computador.")
    print("👉 No Railway, apague IMPORTACAO_LIBERADA (ou ponha false) no Backend.")


if __name__ == "__main__":
    main()
