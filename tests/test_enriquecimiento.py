"""Tests unitarios de haversine_np y parsear_estaciones (src/enriquecimiento.py)."""

import numpy as np

from src.enriquecimiento import haversine_np, parsear_estaciones

OBELISCO = (-34.60372, -58.38159)
PLAZA_DE_MAYO = (-34.60837, -58.37216)   # Pirámide de Mayo


def test_haversine_obelisco_a_plaza_de_mayo_es_alrededor_de_1_km():
    d = haversine_np(*OBELISCO, *PLAZA_DE_MAYO)
    assert 950 < d < 1050


def test_haversine_un_grado_de_latitud_mide_111_km():
    # Sobre un meridiano: 2 * pi * R / 360, con R = 6.371 km
    d = haversine_np(-34.0, -58.0, -35.0, -58.0)
    assert np.isclose(d, 2 * np.pi * 6_371_000 / 360)


def test_haversine_mismo_punto_es_cero():
    assert haversine_np(*OBELISCO, *OBELISCO) == 0


def test_haversine_es_simetrica():
    assert np.isclose(haversine_np(*OBELISCO, *PLAZA_DE_MAYO), haversine_np(*PLAZA_DE_MAYO, *OBELISCO))


def test_haversine_es_vectorizada():
    lat = np.array([OBELISCO[0], PLAZA_DE_MAYO[0]])
    lon = np.array([OBELISCO[1], PLAZA_DE_MAYO[1]])
    d = haversine_np(lat, lon, *OBELISCO)
    assert d.shape == (2,)
    assert d[0] == 0 and d[1] > 0


def test_parsear_estaciones_invierte_lon_lat_de_geojson_a_lat_lon():
    data = {"features": [{"geometry": {"type": "Point", "coordinates": [-58.38, -34.60]}}]}
    assert parsear_estaciones(data).tolist() == [[-34.60, -58.38]]


def test_parsear_estaciones_ignora_lo_que_no_es_punto():
    data = {"features": [
        {"geometry": {"type": "Point", "coordinates": [-58.38, -34.60]}},
        {"geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}},
        {"geometry": {"type": "Point", "coordinates": [-58.38]}},
        {"geometry": {}},
    ]}
    assert len(parsear_estaciones(data)) == 1


def test_parsear_estaciones_geojson_vacio():
    assert len(parsear_estaciones({})) == 0
