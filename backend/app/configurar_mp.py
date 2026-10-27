"""
Assistente para configurar o Mercado Pago no backend/.env.

Uso (na pasta backend, com o .venv ativo):
    python -m app.configurar_mp            -> configura as chaves
    python -m app.configurar_mp --testar   -> só confere as chaves já salvas
    python -m app.configurar_mp --simulado -> volta para o modo de demonstração

O Access Token é digitado sem aparecer na tela e nunca é impresso.
"""
import getpass
import os
import re
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parents[1]  # pasta backend/
ENV_PATH = BASE_DIR / ".env"
EXEMPLO_PATH = BASE_DIR / ".env.example"
API = "https://api.mercadopago.com"
PAINEL = "https://www.mercadopago.com.br/developers/panel/app"


# ---------------------------------------------------------------- .env
def ler_env() -> dict[str, str]:
    valores: dict[str, str] = {}
    if not ENV_PATH.exists():
        return valores
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        linha = raw.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        valores[k.strip()] = v.split(" #", 1)[0].strip().strip('"').strip("'")
    return valores


def salvar_env(novos: dict[str, str]) -> None:
    """Atualiza só as chaves informadas e mantém o resto do arquivo (comentários, outras senhas)."""
    if not ENV_PATH.exists():
        base = EXEMPLO_PATH.read_text(encoding="utf-8") if EXEMPLO_PATH.exists() else ""
        ENV_PATH.write_text(base, encoding="utf-8")
    linhas = ENV_PATH.read_text(encoding="utf-8").splitlines()
    pendentes = dict(novos)
    saida = []
    for raw in linhas:
        m = re.match(r"^\s*([A-Z0-9_]+)\s*=", raw)
        if m and m.group(1) in pendentes:
            saida.append(f"{m.group(1)}={pendentes.pop(m.group(1))}")
        else:
            saida.append(raw)
    if pendentes:
        saida.append("")
        saida.append("# Mercado Pago (adicionado pelo configurar_mercadopago)")
        saida.extend(f"{k}={v}" for k, v in pendentes.items())
    tmp = ENV_PATH.with_suffix(".tmp")
    tmp.write_text("\n".join(saida) + "\n", encoding="utf-8")
    os.replace(tmp, ENV_PATH)


# ---------------------------------------------------------------- validação
def mascarar(valor: str) -> str:
    return f"{valor[:8]}…{valor[-4:]}" if len(valor) > 14 else "(vazio)"


def ambiente(chave: str) -> str:
    if chave.startswith("TEST-"):
        return "teste"
    if chave.startswith("APP_USR-"):
        return "produção/conta de teste"
    return "desconhecido"


def validar_access_token(token: str) -> tuple[bool, str]:
    """Confere o token na própria API de pagamentos (a que o sistema usa).

    O /users/me às vezes responde 403 para credenciais de teste novas mesmo com o
    token certo, então ele só serve para mostrar o nome da conta, sem reprovar.
    """
    cab = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{API}/v1/payments/search", params={"limit": 1}, headers=cab, timeout=15)
    except requests.RequestException:
        return False, "sem internet ou Mercado Pago fora do ar. Tente de novo."
    if r.status_code == 401:
        return False, "Access Token inválido (o Mercado Pago recusou). Copie de novo no painel."
    if r.status_code != 200:
        try:
            detalhe = r.json().get("message", "")
        except ValueError:
            detalhe = ""
        return False, f"o Mercado Pago respondeu HTTP {r.status_code} {detalhe}".strip()
    conta = ""
    try:
        me = requests.get(f"{API}/users/me", headers=cab, timeout=15)
        if me.status_code == 200:
            dados = me.json()
            if dados.get("site_id") and dados["site_id"] != "MLB":
                return False, f"esta conta é do país {dados['site_id']}; o projeto usa Mercado Pago Brasil (MLB)."
            conta = f" — conta '{dados.get('nickname', '?')}' (ID {dados.get('id', '?')})"
    except (requests.RequestException, ValueError):
        pass
    return True, "aceito pela API de pagamentos" + conta


def validar_public_key(chave: str) -> tuple[bool, str]:
    try:
        r = requests.get(f"{API}/v1/payment_methods", params={"public_key": chave}, timeout=15)
    except requests.RequestException:
        return False, "sem internet para conferir a Public Key."
    if r.status_code != 200:
        return False, "o Mercado Pago não confirmou a Public Key. Confira se copiou a do mesmo quadro do Access Token."
    metodos = {m.get("payment_type_id") for m in r.json() if isinstance(m, dict)}
    aceitos = [n for t, n in (("credit_card", "crédito"), ("debit_card", "débito"), ("bank_transfer", "Pix")) if t in metodos]
    return True, "aceita " + (", ".join(aceitos) if aceitos else "os meios da conta")


# ---------------------------------------------------------------- interação
def perguntar(texto: str, atual: str = "", segredo: bool = False) -> str:
    dica = f" [Enter mantém {mascarar(atual)}]" if atual else ""
    leitor = getpass.getpass if segredo else input
    valor = leitor(f"{texto}{dica}: ").strip().strip('"').strip("'")
    return valor or atual


def sim(texto: str) -> bool:
    return input(f"{texto} (s/N): ").strip().lower() in ("s", "sim", "y")


def testar(env: dict[str, str]) -> bool:
    token, pk = env.get("MP_ACCESS_TOKEN", ""), env.get("MP_PUBLIC_KEY", "")
    print(f"\nModo atual: PAYMENT_MODE={env.get('PAYMENT_MODE', 'simulado')}")
    if not token or not pk:
        print("❌ MP_ACCESS_TOKEN e/ou MP_PUBLIC_KEY vazios no .env.")
        return False
    ok1, msg1 = validar_access_token(token)
    print(f"{'✅' if ok1 else '❌'} Access Token {mascarar(token)}: {msg1}")
    ok2, msg2 = validar_public_key(pk)
    print(f"{'✅' if ok2 else '❌'} Public Key {mascarar(pk)}: {msg2}")
    if ambiente(token) != ambiente(pk):
        print("⚠️  Access Token e Public Key parecem ser de ambientes diferentes (teste x produção).")
    if env.get("MP_CLIENT_ID") and env.get("MP_CLIENT_SECRET"):
        uri = env.get("MP_REDIRECT_URI", "")
        aviso = "" if uri.startswith("https://") and "SEU-ENDERECO" not in uri else "  (⚠️ MP_REDIRECT_URI precisa ser HTTPS)"
        print(f"✅ Split configurado (Client ID {env['MP_CLIENT_ID']}){aviso}")
    else:
        print("ℹ️  Split não configurado: as vendas entram na conta da plataforma (repasse fica no extrato).")
    return ok1 and ok2


def configurar() -> None:
    env = ler_env()
    print("=" * 62)
    print(" Mercado Nativo — configurar Mercado Pago")
    print("=" * 62)
    print(f"1) Abra {PAINEL}")
    print("2) Entre na sua aplicação (ou crie: Pagamentos online > Checkout Transparente)")
    print("3) Menu 'Credenciais de teste' > copie a Public Key e o Access Token\n")

    while True:
        pk = perguntar("Cole a Public Key", env.get("MP_PUBLIC_KEY", ""))
        token = perguntar("Cole o Access Token (não aparece ao digitar)", env.get("MP_ACCESS_TOKEN", ""), segredo=True)
        if not pk or not token:
            print("❌ As duas chaves são obrigatórias.\n")
            continue
        if pk == token:
            print("❌ Você colou a mesma chave duas vezes. A Public Key e o Access Token são diferentes.\n")
            continue
        print("\nConferindo com o Mercado Pago...")
        ok1, msg1 = validar_access_token(token)
        print(f"{'✅' if ok1 else '❌'} Access Token: {msg1}")
        ok2, msg2 = validar_public_key(pk)
        print(f"{'✅' if ok2 else '⚠️ '} Public Key: {msg2}")
        mesmo_ambiente = ambiente(token) == ambiente(pk)
        if not mesmo_ambiente:
            print("❌ Uma chave é de teste e a outra de produção. Use as duas do mesmo quadro.")
        if ok1 and mesmo_ambiente:
            break  # a Public Key é conferida de novo pelo próprio formulário do Mercado Pago
        if "sem internet" in msg1 and mesmo_ambiente and sim("Não deu para conferir agora. Salvar mesmo assim?"):
            break
        if not sim("Tentar de novo?"):
            print("Nada foi alterado.")
            return
        print()

    novos = {"PAYMENT_MODE": "mercadopago", "MP_PUBLIC_KEY": pk, "MP_ACCESS_TOKEN": token}

    print("\n--- Opcional: split (90% direto na conta de cada produtor) ---")
    print("Precisa de um endereço HTTPS para o backend (ex.: ngrok). Pode deixar para depois.")
    if sim("Configurar o split agora?"):
        novos["MP_CLIENT_ID"] = perguntar("Client ID", env.get("MP_CLIENT_ID", ""))
        novos["MP_CLIENT_SECRET"] = perguntar("Client Secret (não aparece)", env.get("MP_CLIENT_SECRET", ""), segredo=True)
        base = perguntar("Endereço HTTPS do backend (ex.: https://abc.ngrok-free.app)", env.get("PUBLIC_API_URL", "")).rstrip("/")
        if not base.startswith("https://"):
            print("⚠️  O Mercado Pago exige HTTPS. Split não salvo; rode de novo quando tiver o endereço.")
            novos.pop("MP_CLIENT_ID"); novos.pop("MP_CLIENT_SECRET")
        else:
            novos["PUBLIC_API_URL"] = base
            novos["MP_REDIRECT_URI"] = f"{base}/api/v1/mercadopago/callback"
            print(f"\n👉 No painel, em 'URLs de redirecionamento', cadastre exatamente:\n   {novos['MP_REDIRECT_URI']}")
            print(f"👉 Em 'Webhooks', use a URL {base}/api/v1/checkout/webhook/mercadopago (evento Pagamentos)")
            segredo_wh = perguntar("Assinatura secreta do webhook (Enter para pular)", env.get("MP_WEBHOOK_SECRET", ""), segredo=True)
            if segredo_wh:
                novos["MP_WEBHOOK_SECRET"] = segredo_wh

    salvar_env(novos)
    print("\n✅ Salvo em backend/.env (PAYMENT_MODE=mercadopago).")
    print("   Feche e abra de novo o iniciar_backend.bat para valer.")
    if ambiente(token) == "teste" or ambiente(pk) == "teste":
        print("\nPara testar a compra use um cartão de teste do Mercado Pago, por exemplo:")
        print("   Mastercard 5480 8328 0103 3311 | Visa 4235 6477 2802 5682 | Elo débito 5067 7667 8388 8311")
        print("   CVV 123, validade 11/30, CPF 12345678909")
        print("   Nome do titular: APRO = aprovado | OTHE = recusado | CONT = pendente")
        print("   E-mail do comprador: qualquer um diferente do e-mail da sua conta Mercado Pago.")


def main() -> None:
    args = sys.argv[1:]
    try:
        if "--testar" in args:
            sys.exit(0 if testar(ler_env()) else 1)
        if "--simulado" in args:
            salvar_env({"PAYMENT_MODE": "simulado"})
            print("✅ Voltou para PAYMENT_MODE=simulado (as chaves continuam guardadas no .env).")
            return
        configurar()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelado. Nada foi alterado.")


if __name__ == "__main__":
    main()
