"""Fotos grandes ficam leves (mesmo nome de arquivo); fotos pequenas não são mexidas."""
import os

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from app.services import imagem_service  # noqa: E402


def test_reduz_foto_grande_e_mantem_a_pequena(tmp_path):
    produtos = tmp_path / "produtos"
    produtos.mkdir()
    grande = produtos / "p1_grande.jpg"
    Image.frombytes("RGB", (3000, 2400), os.urandom(3000 * 2400 * 3)).save(grande, "JPEG", quality=98)
    pequena = produtos / "p1_pequena.jpg"
    Image.new("RGB", (300, 300), (20, 120, 60)).save(pequena, "JPEG")
    antes_pequena = pequena.read_bytes()
    tamanho_antes = grande.stat().st_size

    fotos, economia = imagem_service.otimizar_pasta(tmp_path)

    assert fotos == 1 and economia > 0
    assert grande.stat().st_size < tamanho_antes
    with Image.open(grande) as img:
        assert max(img.size) <= imagem_service.LADO_MAXIMO and img.format == "JPEG"
    assert pequena.read_bytes() == antes_pequena
    assert not list(produtos.glob("*.tmp"))
