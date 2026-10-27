"""Busca da vitrine: sem acento, nomes regionais e pequenos erros de digitação."""
from app.services.busca_service import corresponde, normalizar


def test_normalizar_tira_acentos():
    assert normalizar("Geléia de Cupuaçu!") == "geleia de cupuacu"


def test_busca_sem_acento_e_regional():
    assert corresponde("acai", "Polpa de Açaí")
    assert corresponde("macaxeira", "Mandioca descascada")
    assert corresponde("jerimum", "Abóbora cabotiá")
    assert corresponde("balaio", "Cesto de palha")


def test_busca_tolera_erro_e_exige_todas_as_palavras():
    assert corresponde("gelea", "Geleias de Cupuaçu Orgânico")
    assert corresponde("geleia cupuacu", "Geleias de Cupuaçu Orgânico")
    assert not corresponde("geleia manga", "Geleias de Cupuaçu Orgânico")
    assert not corresponde("alface", "Tomate Cereja")


def test_busca_vazia_traz_tudo():
    assert corresponde("", "qualquer coisa")
    assert corresponde("de da", "qualquer coisa")
