"""
Deixa as fotos enviadas leves para carregar rápido no celular.

O site já reduz as fotos novas antes de enviar; aqui ficam as antigas (enviadas antes disso ou
importadas do computador): fotos grandes demais são reduzidas para no máximo 1200 px e recomprimidas,
mantendo o mesmo nome de arquivo (os endereços no banco não mudam). Roda ao iniciar o backend.
"""
import logging
from pathlib import Path

log = logging.getLogger("mercado_nativo")

LIMITE_BYTES = 450 * 1024
LADO_MAXIMO = 1200
SUBPASTAS = ("perfis", "produtos")


def otimizar_arquivo(caminho: Path) -> int:
    """Reduz a foto se ela for grande. Devolve quantos bytes foram economizados (0 se nada mudou)."""
    try:
        from PIL import Image, ImageOps
    except ImportError:  # Pillow não instalado: segue sem otimizar
        return 0
    original = caminho.stat().st_size
    if original <= LIMITE_BYTES:
        return 0
    try:
        with Image.open(caminho) as img:
            formato = (img.format or "").upper()
            # MPO = JPEG de várias imagens que alguns celulares gravam
            if formato not in ("JPEG", "MPO", "PNG", "WEBP"):
                return 0
            img = ImageOps.exif_transpose(img)
            img.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
            temporario = caminho.with_suffix(caminho.suffix + ".tmp")
            if formato in ("JPEG", "MPO"):
                img.convert("RGB").save(temporario, "JPEG", quality=82, optimize=True, progressive=True)
            elif formato == "WEBP":
                img.save(temporario, "WEBP", quality=80, method=6)
            else:
                img.save(temporario, "PNG", optimize=True)
    except Exception as e:  # foto corrompida ou formato estranho: deixa como está
        log.warning("Não foi possível otimizar %s: %s", caminho.name, type(e).__name__)
        return 0
    novo = temporario.stat().st_size
    if novo >= original:
        temporario.unlink(missing_ok=True)
        return 0
    temporario.replace(caminho)
    return original - novo


def otimizar_pasta(pasta: Path) -> tuple[int, int]:
    """Devolve (fotos reduzidas, bytes economizados)."""
    fotos, economia = 0, 0
    for sub in SUBPASTAS:
        alvo = Path(pasta) / sub
        if not alvo.is_dir():
            continue
        for arquivo in alvo.iterdir():
            if arquivo.is_file() and not arquivo.name.endswith(".tmp"):
                ganho = otimizar_arquivo(arquivo)
                if ganho:
                    fotos += 1
                    economia += ganho
    return fotos, economia
