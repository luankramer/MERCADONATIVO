"""
Inteligência Artificial do Mercado Nativo ("A Alma do Produto" e curadoria).

Geração de textos — tenta, nesta ordem:
  1. Ollama local (padrão: qwen2.5:3b, bom em português e leve para CPU)
  2. Groq (nuvem, gratuito) — só se GROQ_API_KEY estiver no .env
  3. Texto montado a partir das palavras-chave (nunca falha)

Curadoria — `analisar_produto` usa análise de palavras-chave local (determinística),
então a moderação funciona mesmo sem nenhum serviço de IA disponível.
"""
import re
import unicodedata

import requests

from app.core.config import settings

# ============================================================
# 1) GERAÇÃO DE TEXTOS
# ============================================================
_PROMPTS = {
    "produto": (
        "Você é redator de um marketplace de produtores rurais e artesãos do Acre. "
        "Escreva em português do Brasil a história de origem de um PRODUTO artesanal, "
        "em um único parágrafo acolhedor e verdadeiro, com no máximo 4 frases, "
        "sem inventar números, prêmios ou certificações. "
        "Não use títulos, aspas, emojis nem listas. Produto e palavras-chave: {prompt}"
    ),
    "produtor": (
        "Você é redator de um marketplace de produtores rurais e artesãos do Acre. "
        "Escreva em português do Brasil, na primeira pessoa do plural, a história de um "
        "PRODUTOR LOCAL em um único parágrafo acolhedor e profissional, com no máximo 4 frases, "
        "sem inventar números ou certificações. Não use títulos, aspas, emojis nem listas. "
        "Palavras-chave: {prompt}"
    ),
}


def _limpar(texto: str) -> str:
    texto = texto.strip().strip('"').strip("“”").strip()
    # Remove preâmbulos comuns ("Claro! Aqui está...")
    texto = re.sub(r"^(claro|aqui est[aá]|segue|com certeza)[^:\n]*[:\n]\s*", "", texto, flags=re.I)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _via_ollama(prompt: str) -> str | None:
    try:
        resp = requests.post(
            f"{settings.OLLAMA_URL.rstrip('/')}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",
                "options": {"temperature": 0.7, "num_predict": 220},
            },
            timeout=settings.OLLAMA_TIMEOUT,
        )
        if resp.status_code == 200:
            return _limpar(resp.json().get("response", "")) or None
        print(f"⚠️  Ollama respondeu {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"⚠️  Ollama indisponível ({settings.OLLAMA_MODEL}): {e}")
    return None


def _via_groq(prompt: str) -> str | None:
    if not settings.GROQ_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=20,
        )
        if resp.status_code == 200:
            return _limpar(resp.json()["choices"][0]["message"]["content"]) or None
        print(f"⚠️  Groq respondeu {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"⚠️  Groq indisponível: {e}")
    return None


def _texto_modelo(palavras: str, tipo: str, nome: str | None = None) -> str:
    """Fallback: monta um texto coerente usando as palavras-chave digitadas."""
    termos = [t.strip() for t in re.split(r"[,;\n]+", palavras) if t.strip()]
    if not termos:
        termos = ["cuidado artesanal"]
    lista = termos[0] if len(termos) == 1 else ", ".join(termos[:-1]) + " e " + termos[-1]
    if tipo == "produtor":
        return (
            f"Nossa história se resume em poucas palavras: {lista}. "
            "Cada etapa do nosso trabalho é feita com dedicação, respeitando o tempo da natureza "
            "e as tradições que aprendemos em família. "
            "Aqui no Acre, produzimos com as próprias mãos para levar até você algo autêntico e cheio de afeto."
        )
    return (
        f"{nome.strip() if nome else 'Este produto'} carrega a essência de quem produz: {lista}. "
        "É preparado em pequena escala, com atenção a cada detalhe e respeito ao tempo certo de cada etapa. "
        "Um sabor e um feitio que carregam a identidade da nossa terra e o cuidado de quem produz."
    )


def gerar_historia(palavras_chave: str, tipo: str = "produto", nome: str | None = None) -> tuple[str, str]:
    """Retorna (texto, fonte). Fonte: 'ollama', 'groq' ou 'modelo'."""
    contexto = f"{nome}. {palavras_chave}" if nome else palavras_chave
    prompt = _PROMPTS.get(tipo, _PROMPTS["produto"]).format(prompt=contexto)
    texto = _via_ollama(prompt)
    if texto:
        return texto, "ollama"
    texto = _via_groq(prompt)
    if texto:
        return texto, "groq"
    return _texto_modelo(palavras_chave, tipo, nome), "modelo"


def gerar_historia_produto(prompt: str) -> str:
    """Mantido por compatibilidade com o código anterior."""
    return gerar_historia(prompt, "produto")[0]


def status_ia() -> dict:
    ollama_ok = False
    modelo_instalado = False
    try:
        r = requests.get(f"{settings.OLLAMA_URL.rstrip('/')}/api/tags", timeout=3)
        if r.status_code == 200:
            ollama_ok = True
            nomes = [m.get("name", "") for m in r.json().get("models", [])]
            base = settings.OLLAMA_MODEL.split(":")[0]
            modelo_instalado = any(n == settings.OLLAMA_MODEL or n.startswith(base + ":") for n in nomes)
    except Exception:
        pass
    return {
        "ollama_online": ollama_ok,
        "ollama_modelo": settings.OLLAMA_MODEL,
        "ollama_modelo_instalado": modelo_instalado,
        "groq_configurado": bool(settings.GROQ_API_KEY),
        "fallback_local": True,
    }


# ============================================================
# 2) CURADORIA — análise de indícios de industrialização
# ============================================================
def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


POSITIVAS = {
    "organico": "orgânico", "organica": "orgânica", "artesanal": "artesanal", "caseiro": "caseiro",
    "caseira": "caseira", "feito a mao": "feito à mão", "feita a mao": "feita à mão",
    "crioula": "crioulas", "crioulo": "crioulos", "colhid": "colhido", "natural": "natural",
    "sem agrotoxico": "sem agrotóxicos", "sem conservante": "sem conservantes",
    "agroecolog": "agroecológico", "familia": "familiar", "tradic": "tradicional",
    "quintal": "quintal", "sitio": "sítio", "roca": "roça", "amazon": "amazônico",
    "regional": "regional", "nativ": "nativo", "fresc": "fresco", "safra": "safra",
    "lote": "lote", "manual": "manual", "barro": "barro", "ceramica": "cerâmica",
    "croche": "crochê", "palha": "palha", "sementes": "sementes", "adubo": "adubo natural",
    "fogo brando": "fogo brando", "receita de familia": "receita de família",
}

NEGATIVAS = {
    "industrializad": "industrializado", "industrial": "industrial", "fabrica": "fábrica",
    "importad": "importado", "revenda": "revenda", "atacado": "atacado",
    "conservante": "conservante", "corante": "corante", "aromatizante": "aromatizante",
    "realcador de sabor": "realçador de sabor", "glutamato": "glutamato",
    "gordura vegetal hidrogenada": "gordura hidrogenada", "replica": "réplica",
    "falsificad": "falsificado", "made in china": "made in china", "produzido em larga escala": "larga escala",
    "marca lider": "marca líder", "ultraprocessad": "ultraprocessado",
}


def analisar_produto(nome: str, descricao: str | None, historia: str | None,
                     categoria: str | None = None, tem_imagem: bool = False) -> dict:
    texto = _sem_acento(" ".join(filter(None, [nome, descricao, historia])))

    positivas: list[str] = []
    for chave, rotulo in POSITIVAS.items():
        if chave in texto and rotulo not in positivas:
            positivas.append(rotulo)

    negativas: list[str] = []
    for chave, rotulo in NEGATIVAS.items():
        for m in re.finditer(re.escape(chave), texto):
            antes = texto[max(0, m.start() - 12):m.start()]
            if re.search(r"\b(sem|zero|livre de|nao usa|nao tem)\s*$", antes):
                continue  # "sem conservantes" é positivo, não negativo
            if rotulo not in negativas:
                negativas.append(rotulo)
            break

    score = 55 + 8 * min(len(positivas), 5) - 25 * len(negativas)
    if descricao and len(descricao.strip()) >= 30:
        score += 6
    if historia and len(historia.strip()) >= 60:
        score += 6
    if tem_imagem:
        score += 4
    score = max(3, min(99, score))

    if negativas:
        resumo = (
            "Atenção: foram encontrados indícios de industrialização ou revenda "
            f"({', '.join(negativas)}). Recomenda-se revisar antes de aprovar."
        )
    else:
        resumo = "O conteúdo não apresenta indícios de industrialização."
    if positivas:
        resumo += f" Palavras-chave positivas detectadas: {', '.join(positivas[:6])}."
    resumo += f" Nível de confiança: {score}% de adequação."

    recomendacao = "aprovar" if score >= 70 and not negativas else ("rejeitar" if score < 40 else "revisar")
    return {
        "score": score,
        "positivas": positivas,
        "negativas": negativas,
        "recomendacao": recomendacao,
        "resumo": resumo,
    }
