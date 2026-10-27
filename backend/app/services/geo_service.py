"""
Geolocalização: coordenadas das cidades e cálculo de distância (fórmula de Haversine).

As 22 cidades do Acre e as capitais vizinhas estão embutidas, então a busca por raio
funciona offline. Para outras cidades tentamos o Nominatim (OpenStreetMap).
"""
import math
import unicodedata

import requests

CIDADES = {
    # Acre (todos os municípios)
    ("AC", "Rio Branco"): (-9.9747, -67.8100),
    ("AC", "Acrelândia"): (-9.8258, -66.8972),
    ("AC", "Assis Brasil"): (-10.9298, -69.5738),
    ("AC", "Brasiléia"): (-11.0094, -68.7482),
    ("AC", "Bujari"): (-9.8153, -67.9550),
    ("AC", "Capixaba"): (-10.5800, -67.6860),
    ("AC", "Cruzeiro do Sul"): (-7.6307, -72.6700),
    ("AC", "Epitaciolândia"): (-11.0188, -68.7341),
    ("AC", "Feijó"): (-8.1642, -70.3536),
    ("AC", "Jordão"): (-9.1933, -71.9506),
    ("AC", "Mâncio Lima"): (-7.6142, -72.8958),
    ("AC", "Manoel Urbano"): (-8.8329, -69.2679),
    ("AC", "Marechal Thaumaturgo"): (-8.9383, -72.7997),
    ("AC", "Plácido de Castro"): (-10.2806, -67.1371),
    ("AC", "Porto Acre"): (-9.5814, -67.5478),
    ("AC", "Porto Walter"): (-8.2686, -72.7439),
    ("AC", "Rodrigues Alves"): (-7.7386, -72.6472),
    ("AC", "Santa Rosa do Purus"): (-9.4465, -70.4902),
    ("AC", "Senador Guiomard"): (-10.1497, -67.7362),
    ("AC", "Sena Madureira"): (-9.0659, -68.6571),
    ("AC", "Tarauacá"): (-8.1569, -70.7722),
    ("AC", "Xapuri"): (-10.6516, -68.4969),
    # Vizinhos
    ("RO", "Porto Velho"): (-8.7612, -63.9004),
    ("AM", "Manaus"): (-3.1190, -60.0217),
    ("AM", "Boca do Acre"): (-8.7523, -67.3919),
}


def _norm(texto: str | None) -> str:
    texto = unicodedata.normalize("NFKD", (texto or "").strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def cidades_por_estado(uf: str = "AC") -> list[str]:
    return sorted(nome for (estado, nome) in CIDADES if estado == uf.upper())


def nome_oficial(cidade: str | None, uf: str | None = None) -> str | None:
    """Corrige acentuação/maiúsculas: 'rio branco' -> 'Rio Branco'."""
    alvo = _norm(cidade)
    for (estado, nome) in CIDADES:
        if _norm(nome) == alvo and (not uf or estado == uf.upper()):
            return nome
    return cidade.strip() if cidade else None


def coordenadas(cidade: str | None, uf: str | None = "AC", online: bool = True) -> tuple[float, float] | None:
    if not cidade:
        return None
    alvo = _norm(cidade)
    for (estado, nome), coords in CIDADES.items():
        if _norm(nome) == alvo and (not uf or estado == (uf or "").upper()):
            return coords
    if not online:
        return None
    # Fora da tabela: tenta o Nominatim (precisa de internet); falha silenciosamente
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"city": cidade, "state": uf or "", "country": "Brasil", "format": "json", "limit": 1},
            headers={"User-Agent": "MercadoNativo-TCC/1.0"},
            timeout=5,
        )
        dados = resp.json()
        if dados:
            return float(dados[0]["lat"]), float(dados[0]["lon"])
    except Exception:
        pass
    return None


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
