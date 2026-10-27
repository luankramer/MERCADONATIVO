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


def ip_cliente(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def registrar(chave: str, maximo: int, janela_segundos: int) -> None:
    """Lança 429 se `chave` passou de `maximo` eventos dentro da janela."""
    agora = time.monotonic()
    with _lock:
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
        fila = _eventos.get(chave)
        while fila and agora - fila[0] > janela_segundos:
            fila.popleft()
        if fila and len(fila) >= maximo:
            espera = int(janela_segundos - (agora - fila[0])) + 1
            raise HTTPException(429, f"Muitas tentativas. Aguarde cerca de {max(1, round(espera / 60))} min e tente de novo.")


def limpar(chave: str) -> None:
    with _lock:
        _eventos.pop(chave, None)


def limitar(nome: str, maximo: int, janela_segundos: int):
    """Dependência do FastAPI que limita por IP."""
    def dependencia(request: Request) -> None:
        registrar(f"{nome}:{ip_cliente(request)}", maximo, janela_segundos)
    return dependencia


def resetar_tudo() -> None:  # usado nos testes
    with _lock:
        _eventos.clear()
