"""
Curadoria automática das publicações (verificação por palavras-chave).

Antes de um produto ir para a vitrine, o texto (nome, descrição e história) é conferido
em busca de indícios de produto artesanal/regional (pontos positivos) ou de
industrialização e revenda (pontos negativos). O resultado é só uma SUGESTÃO para a
equipe: quem aprova ou rejeita é sempre uma pessoa, no painel admin.
Funciona sem internet e sem nenhum serviço externo.
"""
import re
import unicodedata


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
