"""
Limite de requisições em memória (anti-abuso): login, códigos por WhatsApp, avaliações, etc.

Uso numa rota:
    @router.post("/x", dependencies=[Depends(limitar("nome", 5, 60))])
"""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

_eventos: dict[str, deque] = defaultdict(deque)
_lock = Lock()
_chamadas = 0
JANELA_MAXIMA = 86400        # nenhuma regra usa janela maior que 24 h
LIMPAR_A_CADA = 500          # a cada N registros, apaga chaves que já expiraram
MAX_CHAVE = 200              # chaves enormes (entrada maliciosa) são cortadas


def _limpar_expiradas(agora: float) -> None:
    """Remove chaves sem eventos recentes (senão o dicionário cresce até reiniciar o servidor)."""
    for chave in [c for c, f in _eventos.items() if not f or agora - f[-1] > JANELA_MAXIMA]:
        _eventos.pop(chave, None)


def ip_cliente(request: Request) -> str:
    """IP de quem fez o pedido. Atrás do ngrok (ou outro proxy na própria máquina) todo mundo
    chega como 127.0.0.1; aí vale o último IP do X-Forwarded-For, que é o que o proxy anotou."""
    host = request.client.host if request.client else "desconhecido"
    encaminhado = request.headers.get("x-forwarded-for")
    if host in ("127.0.0.1", "::1", "localhost") and encaminhado:
        return encaminhado.split(",")[-1].strip() or host
    return host


def registrar(chave: str, maximo: int, janela_segundos: int) -> None:
    """Lança 429 se `chave` passou de `maximo` eventos dentro da janela."""
    global _chamadas
    agora = time.monotonic()
    chave = chave[:MAX_CHAVE]
    with _lock:
        _chamadas += 1
        if _chamadas % LIMPAR_A_CADA == 0:
            _limpar_expiradas(agora)
        fila = _eventos[chave]
        while fila and agora - fila[0] > janela_segundos:
            fila.popleft()
        if len(fila) >= maximo:
            espera = int(janela_segundos - (agora - fila[0])) + 1
            minutos = max(1, round(espera / 60))
            raise HTTPException(429, f"Muitas tentativas. Aguarde cerca de {minutos} min e tente de novo.")
        fila.append(agora)


def verificar(chave: str, maximo: int, janela_segundos: int) -> None:
    """Como `registrar`, mas só confere o limite (não conta um novo evento)."""
    agora = time.monotonic()
    with _lock:
        fila = _eventos.get(chave[:MAX_CHAVE])
        while fila and agora - fila[0] > janela_segundos:
            fila.popleft()
        if fila and len(fila) >= maximo:
            espera = int(janela_segundos - (agora - fila[0])) + 1
            raise HTTPException(429, f"Muitas tentativas. Aguarde cerca de {max(1, round(espera / 60))} min e tente de novo.")


def limpar(chave: str) -> None:
    with _lock:
        _eventos.pop(chave[:MAX_CHAVE], None)


def limitar(nome: str, maximo: int, janela_segundos: int):
    """Dependência do FastAPI que limita por IP."""
    def dependencia(request: Request) -> None:
        registrar(f"{nome}:{ip_cliente(request)}", maximo, janela_segundos)
    return dependencia


def resetar_tudo() -> None:  # usado nos testes
    with _lock:
        _eventos.clear()
