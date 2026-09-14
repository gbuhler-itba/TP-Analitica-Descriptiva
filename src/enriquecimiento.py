"""
ETAPA 4 - Enriquecimiento del dataset.

Toma el dataset geocodificado y le agrega tres columnas:
  - dist_transporte_m   distancia a la estación de subte más cercana
  - dist_centralidad_m  distancia al polo de centralidad más cercano
  - subzona             sub-zona geográfica dentro del barrio (clustering)

ENTRADA: data/interim/propiedades_geocodificadas.tsv
SALIDA:  data/processed/propiedades_enriquecidas.tsv

Las estaciones de subte salen del GeoJSON oficial de BA Data. Se cachean en
data/external/ para que una segunda corrida no dependa de la red y para que
el resultado sea reproducible aunque el portal cambie el archivo. Con
--forzar-descarga se vuelve a bajar y se pisa el cache.

Las propiedades sin coordenadas (geo_status != OK) se conservan, pero con
las columnas nuevas vacías: no se puede calcular distancia sin coordenadas.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import numpy as np
import pandas as pd
import requests
from sklearn.cluster import KMeans

from src.configuracion import agregar_argumento_config, cargar_config, elegir
from src.entorno import verificar_python
from src.qc import ControlCalidad
from src.rutas import asegurar_directorio, resolver, ruta_relativa


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Etapa 4: agrega distancias a transporte y centralidad, y sub-zonas.",
    )
    agregar_argumento_config(parser)
    parser.add_argument("--entrada", default=None, help="TSV geocodificado de entrada.")
    parser.add_argument("--salida", default=None, help="TSV enriquecido de salida.")
    parser.add_argument("--logs-dir", default=None, help="Directorio de logs de control de calidad.")
    parser.add_argument("--subte-geojson", default=None, help="Cache local del GeoJSON de estaciones de subte.")
    parser.add_argument("--url-subte", default=None, help="URL del GeoJSON de BA Data.")
    parser.add_argument("--forzar-descarga", action="store_true", help="Rebajar el GeoJSON aunque exista el cache.")
    parser.add_argument("--subzonas-por-barrio", type=int, default=None, help="Tope de sub-zonas por barrio.")
    parser.add_argument("--min-propiedades-subzona", type=int, default=None, help="Mínimo de propiedades por sub-zona.")
    return parser


def haversine_np(lat1, lon1, lat2, lon2):
    """Distancia en metros entre puntos (fórmula de Haversine, vectorizada)."""
    R = 6371000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def obtener_geojson_subte(cache, url, timeout=30, forzar=False):
    """
    Devuelve el GeoJSON de estaciones de subte, desde el cache local o
    descargándolo de BA Data y guardándolo en el cache.
    """
    destino = asegurar_directorio(cache)

    if destino.exists() and not forzar:
        print(f"[subte] Usando cache local: {ruta_relativa(destino)}")
        with open(destino, "r", encoding="utf-8") as fh:
            return json.load(fh), "cache"

    print("[subte] Descargando estaciones de subte de BA Data...")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    print(f"  Cache guardado en {ruta_relativa(destino)}")
    return data, "descarga"


def parsear_estaciones(data):
    """Extrae los puntos (lat, lon) de un GeoJSON de estaciones."""
    estaciones = []
    for feature in data.get("features", []):
        geom = feature.get("geometry", {})
        if geom.get("type") == "Point":
            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                lon, lat = coords[0], coords[1]  # GeoJSON: [lon, lat]
                estaciones.append((lat, lon))
    return np.array(estaciones)


def calcular_distancia_transporte(lat, lon, estaciones):
    """Para cada propiedad, distancia a la estación más cercana."""
    if estaciones is None or len(estaciones) == 0:
        return np.full(len(lat), np.nan)

    dist_min = np.full(len(lat), np.inf)
    for est_lat, est_lon in estaciones:
        d = haversine_np(lat, lon, est_lat, est_lon)
        dist_min = np.minimum(dist_min, d)
    return dist_min


def calcular_distancia_centralidad(lat, lon, centralidades):
    """Distancia al polo de centralidad más cercano."""
    distancias = [haversine_np(lat, lon, c[0], c[1]) for c in centralidades.values()]
    resultado = distancias[0]
    for d in distancias[1:]:
        resultado = np.minimum(resultado, d)
    return resultado


def asignar_subzonas(df_ok, subzonas_por_barrio, min_propiedades, kmeans_params):
    """
    Dentro de cada barrio, agrupa las propiedades en sub-zonas por clustering
    geográfico (KMeans sobre lat/lon). Devuelve una Serie "barrio_N".
    """
    print("Definiendo sub-zonas por clustering...")
    subzonas = pd.Series(index=df_ok.index, dtype="object")

    for barrio in df_ok["barrio"].unique():
        mask = df_ok["barrio"] == barrio
        sub = df_ok[mask]
        n = len(sub)

        if n < min_propiedades:
            # Barrio muy chico: toda una sola sub-zona (= el barrio)
            subzonas[mask] = f"{barrio}_0"
            continue

        # Cantidad de clusters: no más que n/min, tope subzonas_por_barrio
        k = min(subzonas_por_barrio, max(1, n // min_propiedades))

        coords = sub[["lat", "lon"]].astype(float).values
        km = KMeans(n_clusters=k, **kmeans_params)
        labels = km.fit_predict(coords)
        subzonas[mask] = [f"{barrio}_{l}" for l in labels]

    print(f"  Sub-zonas creadas: {subzonas.nunique()} en total.")
    return subzonas


def enriquecer(entrada, salida, logs_dir, cfg_enr, cache_subte, columnas_clave,
               forzar_descarga=False) -> int:
    entrada = resolver(entrada)
    destino = asegurar_directorio(salida)

    if not entrada.exists():
        print(f"[!] No se encontró la entrada: {entrada}")
        print("    Corré primero la etapa 3 (geocoding_propiedades).")
        return 1

    print("=== ETAPA 4: ENRIQUECIMIENTO ===")
    print(f"Cargando {entrada}...")
    df = pd.read_csv(entrada, sep="\t", low_memory=False)
    filas_entrada = len(df)
    print(f"  {filas_entrada} propiedades.")

    ok_mask = df["geo_status"] == "OK"
    print(f"  Con coordenadas: {ok_mask.sum()}")

    # Inicializar columnas nuevas (el orden define el orden de columnas de salida)
    df["dist_transporte_m"] = np.nan
    df["dist_centralidad_m"] = np.nan
    df["subzona"] = None

    df_ok = df[ok_mask].copy()
    df_ok["lat"] = pd.to_numeric(df_ok["lat"], errors="coerce")
    df_ok["lon"] = pd.to_numeric(df_ok["lon"], errors="coerce")
    df_ok = df_ok.dropna(subset=["lat", "lon"])

    lat = df_ok["lat"].values
    lon = df_ok["lon"].values

    data, origen_geojson = obtener_geojson_subte(
        cache_subte, cfg_enr["url_subte"], timeout=cfg_enr["timeout"], forzar=forzar_descarga
    )
    estaciones = parsear_estaciones(data)
    print(f"  {len(estaciones)} estaciones de subte.")

    print("Calculando distancias...")
    dist_transp = calcular_distancia_transporte(lat, lon, estaciones)
    dist_centr = calcular_distancia_centralidad(lat, lon, cfg_enr["centralidades"])
    print(f"  Distancia media a transporte: {np.nanmean(dist_transp):.0f} m")
    print(f"  Distancia media a centralidad: {np.nanmean(dist_centr):.0f} m")

    df_ok["dist_transporte_m"] = dist_transp.round(0)
    df_ok["dist_centralidad_m"] = dist_centr.round(0)

    df_ok["subzona"] = asignar_subzonas(
        df_ok,
        subzonas_por_barrio=cfg_enr["subzonas_por_barrio"],
        min_propiedades=cfg_enr["min_propiedades_subzona"],
        kmeans_params=cfg_enr["kmeans"],
    )

    df.loc[df_ok.index, "dist_transporte_m"] = df_ok["dist_transporte_m"]
    df.loc[df_ok.index, "dist_centralidad_m"] = df_ok["dist_centralidad_m"]
    df.loc[df_ok.index, "subzona"] = df_ok["subzona"]

    df.to_csv(destino, sep="\t", index=False, encoding="utf-8-sig")
    print(f"\nDataset enriquecido: {destino}")

    qc = ControlCalidad("04_enriquecimiento", logs_dir)
    qc.metrica("filas_entrada", filas_entrada)
    qc.metrica("filas_salida", len(df))
    qc.metrica("columnas_salida", len(df.columns))
    qc.metrica("origen_geojson_subte", origen_geojson)
    qc.metrica("estaciones_subte", int(len(estaciones)))
    qc.tasa_geocoding(df)
    qc.metrica("con_dist_transporte", int(df["dist_transporte_m"].notna().sum()))
    qc.metrica("con_dist_centralidad", int(df["dist_centralidad_m"].notna().sum()))
    qc.metrica("subzonas_totales", int(df["subzona"].nunique()))
    qc.metrica("dist_transporte_media_m", round(float(np.nanmean(dist_transp)), 1))
    qc.metrica("dist_centralidad_media_m", round(float(np.nanmean(dist_centr)), 1))
    qc.duplicados(df, ["link"], "duplicados_residuales")
    qc.nulos_por_columna(df, columnas_clave)
    qc.metrica("archivo_salida", ruta_relativa(destino))
    qc.cerrar()

    if len(df) != filas_entrada:
        print("[!] La cantidad de filas cambió entre entrada y salida.")
        return 1
    return 0


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    verificar_python(avisar=False)
    cfg = cargar_config(args.config)
    cfg_enr = dict(cfg["enriquecimiento"])
    cfg_enr["url_subte"] = elegir(args.url_subte, cfg_enr["url_subte"])
    cfg_enr["subzonas_por_barrio"] = elegir(args.subzonas_por_barrio, cfg_enr["subzonas_por_barrio"])
    cfg_enr["min_propiedades_subzona"] = elegir(args.min_propiedades_subzona, cfg_enr["min_propiedades_subzona"])

    return enriquecer(
        entrada=elegir(args.entrada, cfg["rutas"]["geocodificado"]),
        salida=elegir(args.salida, cfg["rutas"]["enriquecido"]),
        logs_dir=elegir(args.logs_dir, cfg["rutas"]["logs_dir"]),
        cfg_enr=cfg_enr,
        cache_subte=elegir(args.subte_geojson, cfg["rutas"]["subte_geojson"]),
        columnas_clave=cfg["qc"]["columnas_clave"],
        forzar_descarga=args.forzar_descarga,
    )


if __name__ == "__main__":
    raise SystemExit(main())
