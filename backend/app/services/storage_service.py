"""Gravação de imagens enviadas (fotos de perfil e de produtos) na pasta uploads/."""
import os
import uuid

from fastapi import HTTPException, UploadFile

from app.core.config import settings

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _formato_real(conteudo: bytes) -> str | None:
    """Identifica a imagem pelos primeiros bytes (assinatura do arquivo)."""
    if conteudo.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return ".webp"
    if conteudo[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    return None


async def salvar_imagem(arquivo: UploadFile, subpasta: str, prefixo: str) -> str:
    """Salva a imagem e devolve a URL pública (ex.: /uploads/produtos/3_ab12.jpg)."""
    ext = os.path.splitext(arquivo.filename or "")[1].lower()
    if ext and ext not in EXTENSOES:
        raise HTTPException(400, f"Arquivo '{arquivo.filename}' não é uma imagem (use JPG, PNG ou WEBP).")

    conteudo = await arquivo.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(conteudo) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"A imagem '{arquivo.filename}' passa de {settings.MAX_UPLOAD_MB} MB.")
    # Confere o conteúdo real do arquivo (não basta a extensão): bloqueia scripts disfarçados de imagem
    formato = _formato_real(conteudo)
    if not formato:
        raise HTTPException(400, f"O arquivo '{arquivo.filename}' não é uma imagem válida.")
    ext = formato

    pasta = settings.UPLOAD_DIR / subpasta
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{prefixo}_{uuid.uuid4().hex[:10]}{ext}"
    (pasta / nome).write_bytes(conteudo)
    return f"/uploads/{subpasta}/{nome}"


def remover_arquivo(url: str | None) -> None:
    if not url or not url.startswith("/uploads/"):
        return
    caminho = (settings.UPLOAD_DIR / url.removeprefix("/uploads/")).resolve()
    if settings.UPLOAD_DIR.resolve() not in caminho.parents:
        return  # nunca apaga nada fora da pasta de uploads
    try:
        caminho.unlink(missing_ok=True)
    except OSError:
        pass
