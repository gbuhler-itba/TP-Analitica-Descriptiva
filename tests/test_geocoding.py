"""Tests unitarios de limpiar_direccion (src/geocoding_propiedades.py)."""

import pytest

from src.geocoding_propiedades import limpiar_direccion


@pytest.mark.parametrize("entrada, esperado", [
    ("Av. Santa Fe 3200, Palermo", "Avenida Santa Fe 3200"),
    ("Av Cabildo 2000", "Avenida Cabildo 2000"),
    ("Sinclair 3100. Entre Ortiz y Godoy", "Sinclair 3100"),
    ("Esmeralda Al 900, Centro", "Esmeralda 900"),
    ("Juncal Y Ayacucho", "Juncal Y Ayacucho"),
    ("Gurruchaga   1500", "Gurruchaga 1500"),
])
def test_limpiar_direccion_normaliza_la_query(entrada, esperado):
    assert limpiar_direccion(entrada) == esperado


def test_limpiar_direccion_sin_altura_ni_esquina_no_es_geocodificable():
    assert limpiar_direccion("Palermo Soho") is None


def test_limpiar_direccion_vacia_devuelve_none():
    assert limpiar_direccion(None) is None
