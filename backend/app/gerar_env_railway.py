"""
Gera as variáveis para colar no Railway (aba Variables > Raw Editor) a partir dos .env locais.

Uso (na pasta backend):  python -m app.gerar_env_railway     (ou scripts/gerar_variaveis_railway.bat)

Cria dois arquivos que NÃO vão para o GitHub (terminam em .local):
- backend/railway-backend.env.local       -> variáveis do serviço "Backend"
- backend/railway-site.env.local          -> variáveis do serviço "Site"
Os valores secretos não aparecem na tela.
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parent

# Nomes dos serviços no projeto do Railway (usados nas referências ${{Servico.VARIAVEL}})
SERVICO_BANCO = "MySQL"
SERVICO_BACKEND = "Backend"
SERVICO_SITE = "Site"

# Estas são montadas para o servidor; o valor local (localhost, ngrok) não serve lá
TROCADAS = {"PORT", "APP_ENV", "DATABASE_URL", "FRONTEND_URL", "FRONTEND_URLS", "PUBLIC_API_URL", "MP_REDIRECT_URI",
            "OTP_DEV_MODE", "UPLOAD_DIR"}
# Sobras de versões antigas (IA removida) que não vão para o servidor
DESCARTADAS_PREFIXOS = ("GROQ_", "OLLAMA", "GEMINI")


def ler_env(caminho: Path) -> dict[str, str]:
    valores: dict[str, str] = {}
    if not caminho.exists():
        return valores
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.split(" #", 1)[0].strip()
    return valores


def variaveis_backend(local: dict[str, str]) -> list[str]:
    linhas = [
        "PORT=8080",
        "APP_ENV=producao",
        f"DATABASE_URL=${{{{{SERVICO_BANCO}.MYSQL_URL}}}}",
        f"FRONTEND_URL=https://${{{{{SERVICO_SITE}.RAILWAY_PUBLIC_DOMAIN}}}}",
        "OTP_DEV_MODE=false",
        "UPLOAD_DIR=/data/uploads",
        "DADOS_DEMO=true",
        # Senha do primeiro acesso do Super Admin (mínimo 8): preencha no Railway e apague depois de entrar
        "ADMIN_INICIAL_SENHA=",
    ]
    for chave, valor in local.items():
        if chave in TROCADAS or chave.startswith(DESCARTADAS_PREFIXOS) or chave in ("DADOS_DEMO", "ADMIN_INICIAL_SENHA"):
            continue
        if valor:
            linhas.append(f"{chave}={valor}")
    return linhas


def variaveis_site(local: dict[str, str]) -> list[str]:
    linhas = ["PORT=8080", f"VITE_API_URL=https://${{{{{SERVICO_BACKEND}.RAILWAY_PUBLIC_DOMAIN}}}}"]
    for chave, valor in local.items():
        if chave.startswith("VITE_SUPORTE_") and valor:
            linhas.append(f"{chave}={valor}")
    return linhas


def main() -> None:
    local_back = ler_env(BACKEND / ".env")
    local_site = ler_env(RAIZ / "front-mercado" / ".env")
    if not local_back:
        print("Não achei o backend/.env. Nada foi gerado.")
        return

    destino_back = BACKEND / "railway-backend.env.local"
    destino_site = BACKEND / "railway-site.env.local"
    destino_back.write_text("\n".join(variaveis_backend(local_back)) + "\n", encoding="utf-8")
    destino_site.write_text("\n".join(variaveis_site(local_site)) + "\n", encoding="utf-8")

    print("✅ Arquivos gerados (não vão para o GitHub):")
    print(f"   {destino_back.name}  -> cole no serviço {SERVICO_BACKEND}, em Variables > Raw Editor")
    print(f"   {destino_site.name}  -> cole no serviço {SERVICO_SITE}, em Variables > Raw Editor")
    print("👉 Preencha ADMIN_INICIAL_SENHA no Railway antes da primeira publicação.")

    modo = local_back.get("PAYMENT_MODE", "simulado").lower()
    if modo != "mercadopago":
        print("⚠️  PAYMENT_MODE não é 'mercadopago'. Com APP_ENV=producao o pagamento simulado fica desligado:")
        print("   use PAYMENT_MODE=mercadopago com as credenciais de TESTE (TEST-...) para a banca.")
    faltando = [c for c in ("SECRET_KEY", "EVOLUTION_BASE_URL", "EVOLUTION_TOKEN") if not local_back.get(c)]
    if faltando:
        print(f"⚠️  Vazias no .env: {', '.join(faltando)}")


if __name__ == "__main__":
    main()
