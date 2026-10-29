"""
Tests de src/fuentes_externas.py.

Los tests de geometría usan casos chicos armados a mano, con resultado
conocido. Los que leen snapshots reales se saltean si el archivo no está.

Uso:  pytest tests/test_fuentes_externas.py
"""

import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, box

from src import fuentes_externas as fe
from src.configuracion import cargar_config
from src.enriquecimiento import calcular_distancia_transporte

CRS = "EPSG:32721"
X0, Y0 = 370_000.0, 6_170_000.0  # un punto cualquiera de CABA en UTM 21S

CFG = cargar_config()["fuentes_externas"]
SNAPSHOTS = {k: RAIZ / v for k, v in CFG["rutas"].items() if k != "salida"}
OBELISCO = (-34.603722, -58.381592)


def requiere(*fuentes):
    """Saltea el test si falta alguno de los snapshots."""
    faltan = [f for f in fuentes if not SNAPSHOTS[f].exists()]
    return pytest.mark.skipif(bool(faltan), reason=f"faltan snapshots: {faltan}")


def puntos(*xy):
    return gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in xy], crs=CRS)


def poligonos(geoms, **atributos):
    return gpd.GeoDataFrame(atributos, geometry=list(geoms), crs=CRS)


# --- Normalización de barrios ----------------------------------------------

def test_normalizar_texto_saca_tildes_guiones_y_puntos():
    assert fe.normalizar_texto("Nuñez") == "NUNEZ"
    assert fe.normalizar_texto("villa-del-parque") == "VILLA DEL PARQUE"
    assert fe.normalizar_texto("Constitución") == "CONSTITUCION"


def test_normalizar_texto_expande_abreviaturas():
    abrev = {"GRAL": "GENERAL"}
    assert fe.normalizar_texto("Villa Gral. Mitre", abrev) == fe.normalizar_texto("villa-general-mitre", abrev)


def test_normalizar_texto_devuelve_none_para_vacios():
    assert fe.normalizar_texto(None) is None
    assert fe.normalizar_texto(float("nan")) is None
    assert fe.normalizar_texto("") is None


def test_barrio_norte_coincide_solo_con_recoleta_retiro_o_palermo():
    eq = fe.preparar_equivalencias({"barrio-norte": ["Recoleta", "Retiro", "Palermo"]})
    for oficial in ["Recoleta", "Retiro", "Palermo"]:
        assert fe.barrio_coincide("barrio-norte", oficial, eq) == 1
    assert fe.barrio_coincide("barrio-norte", "Balvanera", eq) == 0


def test_barrio_coincide_compara_el_nombre_normalizado():
    eq = fe.preparar_equivalencias({"barrio-norte": ["Recoleta"]})
    assert fe.barrio_coincide("nunez", "Nuñez", eq) == 1
    assert fe.barrio_coincide("palermo", "Recoleta", eq) == 0
    assert fe.barrio_coincide("palermo", None, eq) is pd.NA


# --- Lectura de fuentes ------------------------------------------------------

def test_filtrar_features_excluye_estaciones_cerradas():
    data = {"type": "FeatureCollection", "features": [
        {"properties": {"nombre": "Liniers"}, "geometry": {"type": "Point", "coordinates": [0, 0]}},
        {"properties": {"nombre": 'Ex-estación "La Salada"'}, "geometry": {"type": "Point", "coordinates": [1, 1]}},
    ]}
    filtrado = fe.filtrar_features(data, "nombre", CFG["tren"]["excluir_nombre_regex"])
    assert [f["properties"]["nombre"] for f in filtrado["features"]] == ["Liniers"]


def _geojson_puntos(tmp_path, coords, crs=None):
    data = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"nombre": str(i)}, "geometry": {"type": "Point", "coordinates": list(c)}}
        for i, c in enumerate(coords)
    ]}
    if crs:
        data["crs"] = {"type": "name", "properties": {"name": crs}}
    ruta = tmp_path / "puntos.geojson"
    ruta.write_text(__import__("json").dumps(data), encoding="utf-8")
    return ruta


def test_cargar_estaciones_reproyecta_el_plano_de_la_ciudad(tmp_path):
    # Estación Int. Saguier del premetro, tal como viene en BA Data (EPSG:9498, metros)
    ruta = _geojson_puntos(tmp_path, [(20166.60243404428, 68392.72486529384)], "urn:ogc:def:crs:EPSG::9498")
    lat, lon = fe.cargar_estaciones(ruta)[0]
    assert lat == pytest.approx(-34.64376, abs=1e-4)
    assert lon == pytest.approx(-58.46149, abs=1e-4)


def test_cargar_estaciones_respeta_crs84(tmp_path):
    ruta = _geojson_puntos(tmp_path, [(-58.5, -34.6)], "urn:ogc:def:crs:OGC:1.3:CRS84")
    assert tuple(fe.cargar_estaciones(ruta)[0]) == (-34.6, -58.5)


def test_cargar_estaciones_corta_si_las_coordenadas_no_son_grados(tmp_path):
    # Metros sin CRS declarado: leído como grados quedaría fuera de la región
    ruta = _geojson_puntos(tmp_path, [(20166.6, 68392.7)])
    with pytest.raises(fe.ErrorFuenteExterna):
        fe.cargar_estaciones(ruta)


def test_leer_geojson_corta_con_error_claro_si_falta_el_snapshot(tmp_path):
    with pytest.raises(fe.ErrorFuenteExterna):
        fe.leer_geojson(tmp_path / "no_existe.geojson")


# --- Geometría con casos sintéticos -----------------------------------------

def test_distancia_a_poligono_es_cero_adentro_y_mide_hasta_el_borde():
    cuadrado = poligonos([box(X0, Y0, X0 + 100, Y0 + 100)])
    pts = puntos((X0 + 50, Y0 + 50), (X0 + 150, Y0 + 50), (X0 + 130, Y0 + 140))
    d = fe.distancia_a_poligonos(pts, cuadrado)
    assert d[0] == 0
    assert d[1] == pytest.approx(50)
    assert d[2] == pytest.approx(50)  # 30 m en x y 40 m en y desde la esquina


def test_distancia_a_poligonos_toma_el_mas_cercano():
    cerca = box(X0 + 200, Y0, X0 + 300, Y0 + 100)
    lejos = box(X0 + 1000, Y0, X0 + 1100, Y0 + 100)
    d = fe.distancia_a_poligonos(puntos((X0, Y0 + 50)), poligonos([lejos, cerca]))
    assert d[0] == pytest.approx(200)


def test_area_en_radio_de_un_parque_que_cubre_todo_el_circulo():
    parque = poligonos([box(X0 - 1000, Y0 - 1000, X0 + 1000, Y0 + 1000)])
    ha = fe.area_en_radio(puntos((X0, Y0)), parque, 500)
    assert ha[0] == pytest.approx(math.pi * 500**2 / 10_000, rel=1e-3)


def test_area_en_radio_mide_la_interseccion_y_no_el_poligono_entero():
    medio_plano = poligonos([box(X0, Y0 - 5000, X0 + 5000, Y0 + 5000)])
    ha = fe.area_en_radio(puntos((X0, Y0)), medio_plano, 500)
    assert ha[0] == pytest.approx(math.pi * 500**2 / 2 / 10_000, rel=1e-3)


def test_area_en_radio_no_cuenta_dos_veces_los_poligonos_superpuestos():
    plaza = box(X0 - 50, Y0 - 50, X0 + 50, Y0 + 50)
    ha = fe.area_en_radio(puntos((X0, Y0)), poligonos([plaza, plaza]), 500)
    assert ha[0] == pytest.approx(1.0, rel=1e-6)


def test_area_en_radio_es_cero_sin_verde_cerca():
    lejos = poligonos([box(X0 + 2000, Y0, X0 + 2100, Y0 + 100)])
    assert fe.area_en_radio(puntos((X0, Y0)), lejos, 500)[0] == 0


def test_asignar_poligono_prefiere_el_tipo_mas_informal_en_superposiciones():
    pol = poligonos(
        [box(X0, Y0, X0 + 100, Y0 + 100), box(X0, Y0, X0 + 100, Y0 + 100)],
        tipo=["Barrio urbanizado", "Asentamiento precario"], _prioridad=[3, 1], id=[1, 2],
    )
    pts = puntos((X0 + 50, Y0 + 50), (X0 + 500, Y0 + 500))
    asignado, multiples = fe.asignar_poligono(pts, pol, ["tipo"], orden=["_prioridad", "id"])
    assert asignado["tipo"].iloc[0] == "Asentamiento precario"
    assert pd.isna(asignado["tipo"].iloc[1])
    assert multiples == 1


# --- Con los snapshots reales -------------------------------------------------

@requiere("barrios", "barrios_populares")
def test_obelisco_cae_en_san_nicolas_y_fuera_de_barrios_populares():
    pts = fe.puntos_proyectados(np.array([OBELISCO[0]]), np.array([OBELISCO[1]]), CFG["crs_metrico"])
    barrios, _ = fe.cargar_poligonos(SNAPSHOTS["barrios"], CFG["crs_metrico"])
    populares, _ = fe.cargar_poligonos(SNAPSHOTS["barrios_populares"], CFG["crs_metrico"])
    assert fe.asignar_poligono(pts, barrios, ["nombre"], ["id"])[0]["nombre"].iloc[0] == "San Nicolas"
    assert pd.isna(fe.asignar_poligono(pts, populares, ["tipo"], ["id"])[0]["tipo"].iloc[0])


@requiere("barrios_populares")
def test_un_punto_dentro_de_rodrigo_bueno_cae_en_barrio_popular():
    populares, _ = fe.cargar_poligonos(SNAPSHOTS["barrios_populares"], CFG["crs_metrico"])
    rb = populares[populares["nombre"] == "Barrio Rodrigo Bueno"]
    pts = gpd.GeoDataFrame(geometry=[rb.geometry.iloc[0].representative_point()], crs=CFG["crs_metrico"])
    assert fe.asignar_poligono(pts, populares, ["tipo"], ["id"])[0]["tipo"].notna().iloc[0]


@requiere("tren")
def test_distancia_cero_en_la_estacion_liniers_y_conocida_a_flores():
    tren = fe.cargar_estaciones(SNAPSHOTS["tren"], "nombre", CFG["tren"]["excluir_nombre_regex"])
    liniers = (-34.638899, -58.526465)
    d = calcular_distancia_transporte(np.array([liniers[0]]), np.array([liniers[1]]), tren)
    assert d[0] < 1
    # Flores y Floresta (Sarmiento) están a 1,43 km por haversine
    flores = np.array([[-34.627897, -58.466248]])
    d = calcular_distancia_transporte(np.array([-34.632384]), np.array([-58.480881]), flores)
    assert d[0] == pytest.approx(1430, abs=10)


@requiere("tren")
def test_el_snapshot_de_tren_no_trae_estaciones_cerradas():
    tren = fe.leer_geojson(SNAPSHOTS["tren"])
    filtrado = fe.filtrar_features(tren, "nombre", CFG["tren"]["excluir_nombre_regex"])
    assert len(tren["features"]) - len(filtrado["features"]) == 1


@requiere("tren", "metrobus", "premetro", "espacios_verdes", "barrios", "barrios_populares")
def test_aviso_sin_coordenadas_queda_vacio_y_no_en_cero():
    df = pd.DataFrame({
        "link": ["a", "b", "c"],
        "barrio": ["san-nicolas", "palermo", "san-nicolas"],
        "geo_status": ["OK", "SIN_RESULTADO", "OK"],
        "lat": [OBELISCO[0], np.nan, OBELISCO[0]],
        "lon": [OBELISCO[1], np.nan, OBELISCO[1]],
        "dist_transporte_m": [150.0, np.nan, 150.0],
    })
    out, met = fe.calcular_accesibilidad(df, CFG)
    assert list(out.columns) == fe.COLUMNAS_SALIDA
    assert list(out["link"]) == ["a", "b", "c"]
    assert out.drop(columns="link").iloc[1].isna().all()
    assert out["en_barrio_popular"].iloc[0] == 0
    assert out["barrio_coincide"].iloc[0] == 1
    # dos avisos en el mismo punto dan el mismo resultado
    pd.testing.assert_series_equal(out.iloc[0].drop("link"), out.iloc[2].drop("link"), check_names=False)
    assert met["coordenadas_unicas"] == 1


@requiere("tren", "metrobus", "premetro", "espacios_verdes", "barrios", "barrios_populares")
def test_riel_y_transporte_pesado_son_los_minimos_correctos():
    df = pd.DataFrame({
        "link": ["a"], "barrio": ["villa-lugano"], "geo_status": ["OK"],
        "lat": [-34.6773], "lon": [-58.4771], "dist_transporte_m": [4400.0],
    })
    out, _ = fe.calcular_accesibilidad(df, CFG)
    fila = out.iloc[0]
    assert fila["dist_riel_m"] == min(4400.0, fila["dist_tren_m"], fila["dist_premetro_m"])
    assert fila["dist_transporte_pesado_m"] == min(fila["dist_riel_m"], fila["dist_metrobus_m"])
    assert fila["dist_tren_m"] < 50  # el punto está en la estación Villa Lugano
