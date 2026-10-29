"""
Fuentes externas para H3: transporte, espacios verdes y barrios oficiales.

Para cada aviso del dataset enriquecido calcula la accesibilidad a tren,
Metrobus y premetro, la cercanía y la superficie de espacios verdes, y en qué
barrio oficial y barrio popular cae el punto.

ENTRADA: data/processed/propiedades_enriquecidas.tsv (no se modifica)
SALIDA:  data/processed/accesibilidad.tsv, con `link` como clave

Columnas de salida:
  dist_tren_m               estación de tren más cercana, incluidas las del
                            conurbano (un aviso junto a la General Paz puede
                            tener la más cercana en la provincia)
  dist_metrobus_m           parada de Metrobus más cercana
  dist_premetro_m           estación de premetro más cercana
  dist_riel_m               mínimo entre subte, tren y premetro
  dist_transporte_pesado_m  mínimo entre riel y Metrobus
  dist_espacio_verde_m      borde de la plaza, parque o jardín más cercano;
                            0 si el aviso cae adentro
  area_verde_500m_ha        hectáreas de espacio verde dentro del círculo de
                            500 m alrededor del aviso
  barrio_oficial            barrio oficial donde cae el punto
  barrio_coincide           1 si coincide con el barrio de búsqueda de
                            MercadoLibre, 0 si no
  en_barrio_popular         1 si el punto cae en un barrio popular, 0 si no
  tipo_barrio_popular       tipo de barrio popular según BA Data

El subte no se vuelve a calcular: se toma `dist_transporte_m` del dataset
enriquecido. Las distancias a puntos usan haversine, igual que el subte, para
que el mínimo compare distancias medidas de la misma forma. Las operaciones
con polígonos se hacen en una proyección métrica (UTM 21S), nunca en grados.

Los avisos sin coordenadas (geo_status != OK) quedan con todas las columnas
vacías: no se puede ubicar un punto que no existe, y un 0 afirmaría algo que
no sabemos.

Todas las fuentes se leen de snapshots en data/external/. El módulo no usa la
red.
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyproj import CRS, Geod, Transformer

from src.configuracion import agregar_argumento_config, cargar_config, elegir
from src.enriquecimiento import calcular_distancia_transporte, haversine_np, parsear_estaciones
from src.entorno import verificar_python
from src.qc import ControlCalidad
from src.rutas import asegurar_directorio, resolver, ruta_relativa

CRS_GEOGRAFICO = "EPSG:4326"

# Caja (lat_min, lat_max, lon_min, lon_max) que contiene la red de tren
# metropolitana completa, de Capilla del Señor a Altamirano. Un punto fuera
# de ella indica un sistema de coordenadas mal leído.
LIMITES_REGION = (-36.0, -33.5, -60.0, -57.5)

COLUMNAS_SALIDA = [
    "link",
    "dist_tren_m",
    "dist_metrobus_m",
    "dist_premetro_m",
    "dist_riel_m",
    "dist_transporte_pesado_m",
    "dist_espacio_verde_m",
    "area_verde_500m_ha",
    "barrio_oficial",
    "barrio_coincide",
    "en_barrio_popular",
    "tipo_barrio_popular",
    "dist_barrio_busqueda_m",
    "geo_dudoso",
]


class ErrorFuenteExterna(RuntimeError):
    """Falta un snapshot o no tiene el contenido esperado."""


# -----------------------------------------------------------------------------
# Lectura de snapshots
# -----------------------------------------------------------------------------

def leer_geojson(ruta) -> dict:
    """Lee un GeoJSON local; corta con un mensaje claro si no está."""
    destino = resolver(ruta)
    if not destino.exists():
        raise ErrorFuenteExterna(
            f"No se encontró el snapshot {ruta_relativa(destino)}. "
            "Ver la ficha de la fuente en docs/entregas_grupo/fuentes_externas.md."
        )
    with open(destino, "r", encoding="utf-8") as fh:
        return json.load(fh)


def crs_de(data: dict) -> CRS:
    """
    Sistema de coordenadas declarado en el GeoJSON; WGS84 si no declara ninguno.

    No se puede suponer: la mayoría de los recursos de BA Data vienen en
    longitud y latitud (CRS84), pero el de estaciones de premetro viene en
    POSGAR 2007 / CABA 2019 (EPSG:9498), en metros. Leído como grados, daría
    distancias absurdas sin ningún error.
    """
    nombre = (data.get("crs") or {}).get("properties", {}).get("name")
    return CRS.from_user_input(nombre) if nombre else CRS.from_user_input(CRS_GEOGRAFICO)


def a_wgs84(data: dict) -> dict:
    """Devuelve una copia del GeoJSON de puntos con las coordenadas en longitud y latitud."""
    origen = crs_de(data)
    if origen.equals(CRS.from_user_input(CRS_GEOGRAFICO), ignore_axis_order=True):
        return data
    transformar = Transformer.from_crs(origen, CRS_GEOGRAFICO, always_xy=True).transform
    features = []
    for f in data.get("features", []):
        geom = f.get("geometry") or {}
        if geom.get("type") == "Point" and len(geom.get("coordinates", [])) >= 2:
            lon, lat = transformar(*geom["coordinates"][:2])
            f = {**f, "geometry": {"type": "Point", "coordinates": [lon, lat]}}
        features.append(f)
    return {**data, "features": features}


def filtrar_features(data: dict, campo: str, patron_excluir) -> dict:
    """Devuelve una copia del GeoJSON sin los features cuyo campo matchea el patrón."""
    if not patron_excluir:
        return data
    regex = re.compile(patron_excluir)
    features = [
        f for f in data.get("features", [])
        if not regex.search(str(f.get("properties", {}).get(campo) or ""))
    ]
    return {**data, "features": features}


def solo_poligonos(geom):
    """Se queda con la parte poligonal de una geometría (sirve tras make_valid)."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    partes = [p for p in shapely.get_parts(geom) if p.geom_type in ("Polygon", "MultiPolygon")]
    if not partes:
        return None
    return shapely.union_all(partes)


def cargar_poligonos(ruta, crs_metrico) -> tuple:
    """
    Lee un GeoJSON de polígonos, repara las geometrías inválidas y lo proyecta.

    Devuelve el GeoDataFrame proyectado y la cantidad de geometrías reparadas.
    """
    data = leer_geojson(ruta)
    gdf = gpd.GeoDataFrame.from_features(data["features"], crs=crs_de(data))
    if gdf.empty:
        raise ErrorFuenteExterna(f"{ruta_relativa(ruta)} no tiene polígonos.")
    invalidas = ~gdf.geometry.is_valid
    if invalidas.any():
        gdf.loc[invalidas, "geometry"] = gdf.loc[invalidas, "geometry"].make_valid().apply(solo_poligonos)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    return gdf.to_crs(crs_metrico), int(invalidas.sum())


def cargar_estaciones(ruta, campo_nombre=None, patron_excluir=None) -> np.ndarray:
    """Lee un GeoJSON de puntos, lo pasa a WGS84 si hace falta y devuelve un array (lat, lon)."""
    data = a_wgs84(leer_geojson(ruta))
    if campo_nombre:
        data = filtrar_features(data, campo_nombre, patron_excluir)
    estaciones = parsear_estaciones(data)
    if len(estaciones) == 0:
        raise ErrorFuenteExterna(f"{ruta_relativa(ruta)} no tiene puntos.")
    lat_min, lat_max, lon_min, lon_max = LIMITES_REGION
    fuera = ~((estaciones[:, 0] > lat_min) & (estaciones[:, 0] < lat_max)
              & (estaciones[:, 1] > lon_min) & (estaciones[:, 1] < lon_max))
    if fuera.any():
        raise ErrorFuenteExterna(
            f"{ruta_relativa(ruta)}: {int(fuera.sum())} puntos quedan fuera de la región metropolitana. "
            "Probablemente el archivo no declara su sistema de coordenadas o declara uno equivocado."
        )
    return estaciones


# -----------------------------------------------------------------------------
# Normalización de textos
# -----------------------------------------------------------------------------

def normalizar_texto(texto, abreviaturas=None):
    """Mayúsculas, sin tildes, sin guiones ni puntos y con abreviaturas expandidas."""
    if texto is None or (isinstance(texto, float) and np.isnan(texto)) or texto is pd.NA:
        return None
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[-_.]", " ", s)
    palabras = [(abreviaturas or {}).get(p, p) for p in s.split()]
    return " ".join(palabras) or None


def barrio_coincide(barrio_busqueda, barrio_oficial, equivalencias, abreviaturas=None):
    """
    1 si el barrio de búsqueda de MercadoLibre coincide con el oficial, 0 si no.

    Las equivalencias cubren categorías de búsqueda que no son barrios
    oficiales (Barrio Norte). Sin barrio oficial devuelve pd.NA.
    """
    oficial = normalizar_texto(barrio_oficial, abreviaturas)
    if oficial is None:
        return pd.NA
    busqueda = normalizar_texto(barrio_busqueda, abreviaturas)
    aceptados = equivalencias.get(busqueda, {busqueda})
    return int(oficial in aceptados)


def preparar_equivalencias(equivalencias, abreviaturas=None) -> dict:
    """Normaliza claves y valores del mapa de equivalencias de config."""
    return {
        normalizar_texto(k, abreviaturas): {normalizar_texto(v, abreviaturas) for v in valores}
        for k, valores in (equivalencias or {}).items()
    }


# -----------------------------------------------------------------------------
# Cálculos espaciales
# -----------------------------------------------------------------------------

def puntos_proyectados(lat, lon, crs_metrico) -> gpd.GeoDataFrame:
    """Arma un GeoDataFrame de puntos en la proyección métrica."""
    geometria = gpd.points_from_xy(lon, lat, crs=CRS_GEOGRAFICO)
    return gpd.GeoDataFrame(geometry=geometria).to_crs(crs_metrico)


def distancia_a_poligonos(puntos, poligonos) -> np.ndarray:
    """Distancia en metros al borde del polígono más cercano; 0 si el punto cae adentro."""
    unidos = gpd.sjoin_nearest(
        puntos[["geometry"]], poligonos[["geometry"]], how="left", distance_col="_dist"
    )
    # sjoin_nearest repite el punto cuando hay empates: la distancia es la misma
    return unidos.groupby(level=0)["_dist"].min().reindex(puntos.index).to_numpy()


def area_en_radio(puntos, poligonos, radio_m, segmentos_cuarto=32) -> np.ndarray:
    """
    Hectáreas de los polígonos dentro de un círculo de radio_m alrededor de cada punto.

    Los polígonos se disuelven antes, para no contar dos veces una superficie
    cubierta por polígonos superpuestos. Se mide la intersección con el
    círculo, no el área completa de los parques que lo tocan.
    """
    union = shapely.union_all(poligonos.geometry.to_numpy())
    partes = shapely.get_parts(union)
    arbol = shapely.STRtree(partes)
    circulos = shapely.buffer(puntos.geometry.to_numpy(), radio_m, quad_segs=segmentos_cuarto)
    i_circulo, i_parte = arbol.query(circulos, predicate="intersects")
    areas = shapely.area(shapely.intersection(circulos[i_circulo], partes[i_parte]))
    total_m2 = np.bincount(i_circulo, weights=areas, minlength=len(circulos))
    return total_m2 / 10_000


def asignar_poligono(puntos, poligonos, columnas, orden=None) -> tuple:
    """
    Para cada punto, los atributos del polígono que lo contiene.

    Si un punto cae en más de un polígono (bordes compartidos o polígonos
    superpuestos), se queda con el primero según `orden`, una lista de
    columnas por las que se ordena antes de elegir. Devuelve el DataFrame de
    atributos alineado con los puntos y cuántos puntos cayeron en dos o más.
    """
    cols = list(dict.fromkeys(columnas + [c for c in (orden or []) if c in poligonos]))
    unidos = gpd.sjoin(puntos[["geometry"]], poligonos[cols + ["geometry"]], how="left", predicate="intersects")
    multiples = int(unidos.index.value_counts().gt(1).sum())
    if orden:
        unidos = unidos.sort_values(orden, kind="mergesort", na_position="last")
    unidos = unidos[~unidos.index.duplicated(keep="first")]
    return unidos.reindex(puntos.index)[columnas], multiples


def control_proyeccion(lat, lon, estaciones, crs_metrico, n=2000, semilla=42) -> dict:
    """
    Error máximo, en %, de haversine y de la proyección contra la distancia geodésica.

    La referencia es la distancia sobre el elipsoide WGS84. Haversine supone
    una Tierra esférica y su error depende de la dirección; la proyección
    tiene un error de escala casi constante. Sirve para documentar que las
    distancias a puntos (haversine) y a polígonos (proyectadas) son comparables.
    """
    rng = np.random.default_rng(semilla)
    idx = rng.choice(len(lat), size=min(n, len(lat)), replace=False)
    est = estaciones[rng.integers(0, len(estaciones), size=len(idx))]
    _, _, d_geo = Geod(ellps="WGS84").inv(lon[idx], lat[idx], est[:, 1], est[:, 0])
    d_hav = haversine_np(lat[idx], lon[idx], est[:, 0], est[:, 1])
    a = puntos_proyectados(lat[idx], lon[idx], crs_metrico).geometry
    b = puntos_proyectados(est[:, 0], est[:, 1], crs_metrico).geometry
    d_proy = a.distance(b, align=False).to_numpy()
    validos = d_geo > 100
    return {
        "haversine": round(float(np.max(np.abs(d_hav[validos] / d_geo[validos] - 1)) * 100), 3),
        "proyeccion": round(float(np.max(np.abs(d_proy[validos] / d_geo[validos] - 1)) * 100), 3),
    }


# -----------------------------------------------------------------------------
# Etapa
# -----------------------------------------------------------------------------

def calcular_accesibilidad(df, cfg) -> tuple:
    """
    Calcula las columnas nuevas para los avisos con coordenadas.

    Devuelve el DataFrame de salida (una fila por aviso, en el orden de
    entrada) y un diccionario de métricas de control.
    """
    rutas = cfg["rutas"]
    crs = cfg["crs_metrico"]
    abrev = cfg.get("abreviaturas_barrio", {})
    met = {}

    ok_mask = (df["geo_status"] == "OK")
    lat_all = pd.to_numeric(df["lat"], errors="coerce")
    lon_all = pd.to_numeric(df["lon"], errors="coerce")
    ok_mask &= lat_all.notna() & lon_all.notna()
    met["con_coordenadas"] = int(ok_mask.sum())

    # Se calcula una vez por coordenada distinta: varios avisos del mismo
    # edificio comparten punto, y así el resultado es el mismo para todos.
    coords = pd.DataFrame({"lat": lat_all[ok_mask], "lon": lon_all[ok_mask]})
    unicas = coords.drop_duplicates().reset_index(drop=True)
    met["coordenadas_unicas"] = len(unicas)
    lat = unicas["lat"].to_numpy()
    lon = unicas["lon"].to_numpy()
    res = pd.DataFrame(index=unicas.index)

    # --- Transporte (puntos, haversine) ---
    tren = cargar_estaciones(rutas["tren"], cfg["tren"]["campo_nombre"], cfg["tren"]["excluir_nombre_regex"])
    metrobus = cargar_estaciones(rutas["metrobus"])
    premetro = cargar_estaciones(rutas["premetro"])
    met["estaciones_tren"] = len(tren)
    met["paradas_metrobus"] = len(metrobus)
    met["estaciones_premetro"] = len(premetro)
    res["dist_tren_m"] = calcular_distancia_transporte(lat, lon, tren).round(0)
    res["dist_metrobus_m"] = calcular_distancia_transporte(lat, lon, metrobus).round(0)
    res["dist_premetro_m"] = calcular_distancia_transporte(lat, lon, premetro).round(0)
    error = control_proyeccion(lat, lon, metrobus, crs)
    met["error_max_haversine_vs_geodesica_pct"] = error["haversine"]
    met["error_max_proyeccion_vs_geodesica_pct"] = error["proyeccion"]

    # --- Polígonos (proyección métrica) ---
    puntos = puntos_proyectados(lat, lon, crs)

    verdes, rep = cargar_poligonos(rutas["espacios_verdes"], crs)
    met["espacios_verdes_poligonos"] = len(verdes)
    met["espacios_verdes_reparados"] = rep
    clase = verdes[cfg["verdes"]["campo_clase"]].map(normalizar_texto)
    clases_dist = {normalizar_texto(c) for c in cfg["verdes"]["clases_distancia"]}
    clases_fuera_area = {normalizar_texto(c) for c in cfg["verdes"]["clases_excluidas_area"]}
    ids_fuera_area = set(cfg["verdes"]["ids_excluidos_area"])
    verdes_dist = verdes[clase.isin(clases_dist)]
    verdes_area = verdes[~clase.isin(clases_fuera_area) & ~verdes["id"].isin(ids_fuera_area)]
    met["espacios_verdes_para_distancia"] = len(verdes_dist)
    met["espacios_verdes_para_area"] = len(verdes_area)
    res["dist_espacio_verde_m"] = distancia_a_poligonos(puntos, verdes_dist).round(0)
    res["area_verde_500m_ha"] = area_en_radio(
        puntos, verdes_area, cfg["verdes"]["radio_area_m"], cfg["verdes"]["segmentos_cuarto"]
    ).round(4)

    barrios, rep = cargar_poligonos(rutas["barrios"], crs)
    met["barrios_poligonos"] = len(barrios)
    met["barrios_reparados"] = rep
    asignado, multiples = asignar_poligono(puntos, barrios, ["nombre"], orden=["id"])
    res["barrio_oficial"] = asignado["nombre"].to_numpy()
    met["puntos_en_dos_o_mas_barrios"] = multiples

    populares, rep = cargar_poligonos(rutas["barrios_populares"], crs)
    met["barrios_populares_poligonos"] = len(populares)
    met["barrios_populares_reparados"] = rep
    prioridad = {t: i for i, t in enumerate(cfg["barrios_populares"]["prioridad_tipo"])}
    populares["_prioridad"] = populares["tipo"].map(prioridad).fillna(len(prioridad))
    asignado, multiples = asignar_poligono(puntos, populares, ["tipo"], orden=["_prioridad", "id"])
    res["tipo_barrio_popular"] = asignado["tipo"].to_numpy()
    res["en_barrio_popular"] = asignado["tipo"].notna().astype(int).to_numpy()
    met["puntos_en_dos_o_mas_barrios_populares"] = multiples

    # --- Volver a una fila por aviso ---
    llave = coords.merge(unicas.reset_index(), on=["lat", "lon"], how="left")["index"].to_numpy()
    out = pd.DataFrame(index=df.index)
    out["link"] = df["link"]
    for col in res.columns:
        out[col] = pd.Series(res[col].to_numpy()[llave], index=coords.index).reindex(df.index)

    subte = pd.to_numeric(df["dist_transporte_m"], errors="coerce")
    out["dist_riel_m"] = np.fmin(np.fmin(subte, out["dist_tren_m"]), out["dist_premetro_m"]).where(ok_mask)
    out["dist_transporte_pesado_m"] = np.fmin(out["dist_riel_m"], out["dist_metrobus_m"])

    equivalencias = preparar_equivalencias(cfg.get("equivalencias_barrio"), abrev)
    out["barrio_coincide"] = [
        barrio_coincide(b, o, equivalencias, abrev) if ok else pd.NA
        for b, o, ok in zip(df["barrio"], out["barrio_oficial"], ok_mask)
    ]
    out["barrio_coincide"] = out["barrio_coincide"].astype("Int64")
    out["en_barrio_popular"] = out["en_barrio_popular"].round().astype("Int64")

    # Distancia del punto al barrio con el que se buscó el aviso. Un punto a
    # más de `umbral_geo_dudoso_m` del barrio buscado es casi seguro un error de
    # geocodificación (calles homónimas: "Arroyo 800" cae en Villa Crespo).
    # Agregado en la integración de la PreEntrega 3 (control_fuentes.md, sección 4).
    poly = dict(zip(barrios["nombre"].map(lambda t: normalizar_texto(t, abrev)), barrios.geometry))
    geom_busqueda = {}
    for b in df.loc[ok_mask, "barrio"].unique():
        k = normalizar_texto(b, abrev)
        partes = [poly[x] for x in equivalencias.get(k, {k}) if x in poly]
        geom_busqueda[b] = shapely.union_all(partes) if partes else None
    puntos_aviso = puntos_proyectados(lat_all[ok_mask].to_numpy(), lon_all[ok_mask].to_numpy(), crs).geometry.to_numpy()
    distancias = [shapely.distance(p, geom_busqueda[b]) if geom_busqueda[b] is not None else np.nan
                  for p, b in zip(puntos_aviso, df.loc[ok_mask, "barrio"])]
    out["dist_barrio_busqueda_m"] = pd.Series(np.round(distancias, 0), index=df.index[ok_mask]).reindex(df.index)
    umbral = cfg.get("umbral_geo_dudoso_m", 1000)
    out["geo_dudoso"] = (out["dist_barrio_busqueda_m"] > umbral).astype("Int64").where(ok_mask)
    met["geo_dudoso"] = int(out["geo_dudoso"].sum())

    met["fuera_de_barrio_oficial"] = int((ok_mask & out["barrio_oficial"].isna()).sum())
    met["en_barrio_popular"] = int(out["en_barrio_popular"].sum())
    met["barrio_coincide_pct"] = round(float(out["barrio_coincide"].mean()) * 100, 2)
    return out[COLUMNAS_SALIDA], met


def generar(entrada, salida, logs_dir, cfg) -> int:
    """Lee el dataset enriquecido, calcula las columnas y escribe el TSV de salida."""
    entrada = resolver(entrada)
    destino = asegurar_directorio(salida)
    if not entrada.exists():
        print(f"[!] No se encontró la entrada: {entrada}")
        print("    Corré primero el pipeline hasta la etapa 4 (enriquecimiento).")
        return 1

    print("=== FUENTES EXTERNAS: ACCESIBILIDAD, VERDE Y BARRIOS ===")
    df = pd.read_csv(entrada, sep="\t", low_memory=False)
    print(f"  {len(df)} avisos, {int((df['geo_status'] == 'OK').sum())} con coordenadas.")

    try:
        out, met = calcular_accesibilidad(df, cfg)
    except ErrorFuenteExterna as e:
        print(f"[!] {e}")
        return 1

    out.to_csv(destino, sep="\t", index=False, encoding="utf-8-sig")
    print(f"\nAccesibilidad: {ruta_relativa(destino)}")

    qc = ControlCalidad("07_fuentes_externas", logs_dir)
    qc.metrica("filas_entrada", len(df))
    qc.metrica("filas_salida", len(out))
    for nombre, valor in met.items():
        qc.metrica(nombre, valor)
    qc.duplicados(out, ["link"], "links_duplicados")
    con = out["dist_tren_m"].notna()
    for col in ["dist_tren_m", "dist_metrobus_m", "dist_premetro_m", "dist_riel_m",
                "dist_transporte_pesado_m", "dist_espacio_verde_m", "area_verde_500m_ha"]:
        qc.metrica(f"mediana_{col}", round(float(out.loc[con, col].median()), 2))
    qc.nulos_por_columna(out, COLUMNAS_SALIDA, "nulos_por_columna")
    qc.metrica("archivo_salida", ruta_relativa(destino))
    qc.cerrar()

    if len(out) != len(df) or out["link"].duplicated().any():
        print("[!] La salida no tiene una fila por aviso con link único.")
        return 1
    return 0


def construir_parser() -> argparse.ArgumentParser:
    """Parser de línea de comandos, con el mismo esquema que las etapas del pipeline."""
    parser = argparse.ArgumentParser(
        description="Calcula accesibilidad, espacios verdes y barrios oficiales para cada aviso.",
    )
    agregar_argumento_config(parser)
    parser.add_argument("--entrada", default=None, help="TSV enriquecido de entrada.")
    parser.add_argument("--salida", default=None, help="TSV de accesibilidad de salida.")
    parser.add_argument("--logs-dir", default=None, help="Directorio de logs de control de calidad.")
    return parser


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    verificar_python(avisar=False)
    cfg = cargar_config(args.config)
    cfg_fe = cfg["fuentes_externas"]
    return generar(
        entrada=elegir(args.entrada, cfg["rutas"]["enriquecido"]),
        salida=elegir(args.salida, cfg_fe["rutas"]["salida"]),
        logs_dir=elegir(args.logs_dir, cfg["rutas"]["logs_dir"]),
        cfg=cfg_fe,
    )


if __name__ == "__main__":
    raise SystemExit(main())
