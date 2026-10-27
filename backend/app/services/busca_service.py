"""
Busca da vitrine pensada para quem digita do jeito que fala:
- ignora acentos e maiúsculas ("acai" encontra "Açaí")
- entende nomes regionais ("macaxeira" encontra "mandioca", "jerimum" encontra "abóbora")
- tolera pequenos erros de digitação ("gelea" encontra "geleia")
Tudo em Python puro, sem depender de recurso do banco de dados.
"""
import difflib
import re
import unicodedata

# Cada grupo reúne nomes que significam a mesma coisa por aqui. Para incluir mais, é só acrescentar.
SINONIMOS: list[set[str]] = [
    {"mandioca", "macaxeira", "aipim"},
    {"abobora", "jerimum"},
    {"farinha", "farinha de mandioca", "farinha d'agua"},
    {"cupuacu", "cupu"},
    {"castanha", "castanha do brasil", "castanha do para"},
    {"acai", "jucara"},
    {"feijao", "feijão"},
    {"milho", "espiga"},
    {"queijo", "requeijao", "coalho"},
    {"doce", "geleia", "compota"},
    {"cesto", "cesta", "balaio", "cestaria"},
    {"croche", "tricô", "trico", "tapete"},
    {"ceramica", "barro", "vaso"},
    {"hortalica", "verdura", "folha"},
    {"suco", "polpa"},
]
_STOP = {"de", "da", "do", "das", "dos", "e", "com", "para", "o", "a", "os", "as", "um", "uma"}


def normalizar(texto: str | None) -> str:
    """Minúsculas, sem acentos e só letras/números separados por espaço."""
    if not texto:
        return ""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


_GRUPOS = [{normalizar(s) for s in g} for g in SINONIMOS]


def _variantes(palavra: str) -> set[str]:
    """A palavra, seu singular simples e os sinônimos regionais."""
    base = {palavra}
    if len(palavra) > 3 and palavra.endswith("s"):
        base.add(palavra[:-1])
    for g in _GRUPOS:
        if base & g or any(palavra in s.split() for s in g):
            base |= g
    return base


def _palavra_bate(palavra: str, texto: str, palavras_texto: list[str]) -> bool:
    for v in _variantes(palavra):
        if v in texto:  # trecho ("geleia" em "geleias de cupuacu")
            return True
    # pequenos erros de digitação: só para palavras com 4+ letras
    if len(palavra) >= 4 and difflib.get_close_matches(palavra, palavras_texto, n=1, cutoff=0.8):
        return True
    return False


def corresponde(busca: str | None, *campos: str | None) -> bool:
    """True se TODAS as palavras importantes da busca aparecem em algum dos campos."""
    termos = [p for p in normalizar(busca).split() if p not in _STOP]
    if not termos:
        return True
    texto = " ".join(normalizar(c) for c in campos if c)
    palavras_texto = texto.split()
    return all(_palavra_bate(p, texto, palavras_texto) for p in termos)
