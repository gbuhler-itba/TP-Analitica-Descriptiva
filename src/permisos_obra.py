"""
Permisos de obra cerca de cada aviso (señal de dinamismo de la zona).

Para cada aviso geocodificado del dataset enriquecido cuenta las parcelas con
permiso de obra nueva a menos de 500 m, en los 3 años anteriores al scraping.

ENTRADA: data/processed/propiedades_enriquecidas.tsv
         data/external/obras-registradas.csv  (snapshot de BA Data, sin red)
SALIDA:  data/processed/permisos_obra.tsv     (link + permisos_obra_500m)

No modifica el dataset enriquecido: la salida es un archivo aparte, con
`link` como clave, que se une después al dataset de trabajo.

Decisiones (justificadas en docs/entregas_grupo/fuentes_externas.md, ficha 9):
  - Tipos: solo trámites de obra nueva o ampliación mayor (TIPOS_OBRA). Quedan
    afuera instalaciones, demoliciones, regularizaciones y planos.
  - Ventana: 3 años antes del scraping (14/08/2023 a 13/08/2026). Todo lo
    posterior al 14/08/2026 se descarta: no se conocía al publicarse el aviso.
  - Se cuenta una vez cada obra: una misma obra suele tener varios trámites
    (permiso temprano + permiso de ejecución), y algunas ocupan varias parcelas
    (smp distintos con el mismo punto y el mismo expediente). Se deduplica por
    parcela y después por punto.
  - m2_obra_500m no se calcula: el dataset no trae superficie autorizada.

Uso:  python3 src/permisos_obra.py
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import numpy as np
import pandas as pd

from src.enriquecimiento import haversine_np
from src.rutas import asegurar_directorio, resolver, ruta_relativa

from src.configuracion import cargar_config  # noqa: E402

_CFG = cargar_config()
ENTRADA = _CFG["rutas"]["enriquecido"]
SNAPSHOT = _CFG["rutas"]["permisos_obra_snapshot"]
SALIDA = _CFG["rutas"]["permisos_obra"]

FECHA_SCRAPING = _CFG["permisos_obra"]["fecha_scraping"]
ANIOS_VENTANA = _CFG["permisos_obra"]["anios_ventana"]
RADIO_M = _CFG["permisos_obra"]["radio_m"]

# Trámites que indican una obra nueva o una ampliación mayor (lista en config.yaml).
# Los nombres cambiaron en 2021-2022 ("REGISTRO-PERMISO OBRA" pasó a "PERMISO DE
# EJECUCION DE OBRA CIVIL"); se incluyen los dos para que la lista sirva con otra ventana.
TIPOS_OBRA = _CFG["permisos_obra"]["tipos_obra"]


def leer_snapshot(ruta):
    """Lee el CSV de BA Data: separado por ';', con BOM y fecha día/mes/año."""
    df = pd.read_csv(ruta, sep=";", encoding="utf-8-sig", low_memory=False)
    df["fecha"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y %H:%M")
    return df


def parsear_punto_wkt(serie):
    """'POINT(-58.44 -34.62)' -> DataFrame con lat y lon (WKT es lon lat)."""
    coords = serie.str.extract(r"POINT\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s*\)").astype(float)
    return pd.DataFrame({"lat": coords[1], "lon": coords[0]}, index=serie.index)


def filtrar_permisos(df, fecha_scraping=FECHA_SCRAPING, anios=ANIOS_VENTANA, tipos=TIPOS_OBRA):
    """Permisos de obra dentro de la ventana, uno por obra (el trámite más reciente).

    Una obra puede tener varios trámites sobre la misma parcela (smp) y varias
    parcelas con el mismo punto: se deduplica por parcela y después por punto.

    La ventana es [fecha_scraping - anios, fecha_scraping): incluye el inicio
    y excluye el día del scraping en adelante.
    """
    fin = pd.Timestamp(fecha_scraping)
    inicio = fin - pd.DateOffset(years=anios)
    en_ventana = (df["fecha"] >= inicio) & (df["fecha"] < fin)
    obras = df[en_ventana & df["descripcio"].isin(tipos)]
    obras = obras.sort_values("fecha").drop_duplicates("smp", keep="last")
    obras = obras.drop_duplicates("wkt_2", keep="last")
    return obras.reset_index(drop=True)


def contar_en_radio(lat, lon, lat_puntos, lon_puntos, radio_m=RADIO_M):
    """Para cada (lat, lon), cuántos puntos hay a menos de `radio_m` metros."""
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    conteo = np.zeros(len(lat), dtype=int)
    for p_lat, p_lon in zip(lat_puntos, lon_puntos):
        conteo += haversine_np(lat, lon, p_lat, p_lon) < radio_m
    return conteo


def calcular(avisos, permisos, radio_m=RADIO_M):
    """Una fila por aviso: link y permisos_obra_500m (vacío sin coordenadas)."""
    salida = pd.DataFrame({"link": avisos["link"], "permisos_obra_500m": np.nan})
    ok = (avisos["geo_status"] == "OK") & avisos["lat"].notna() & avisos["lon"].notna()
    puntos = parsear_punto_wkt(permisos["wkt_2"])
    salida.loc[ok, "permisos_obra_500m"] = contar_en_radio(
        avisos.loc[ok, "lat"], avisos.loc[ok, "lon"], puntos["lat"], puntos["lon"], radio_m
    )
    salida["permisos_obra_500m"] = salida["permisos_obra_500m"].astype("Int64")
    return salida


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Cuenta permisos de obra a menos de 500 m de cada aviso.")
    parser.add_argument("--entrada", default=ENTRADA, help="TSV enriquecido.")
    parser.add_argument("--snapshot", default=SNAPSHOT, help="CSV de Obras Registradas de BA Data.")
    parser.add_argument("--salida", default=SALIDA, help="TSV de salida.")
    args = parser.parse_args(argv)

    snapshot = resolver(args.snapshot)
    if not snapshot.exists():
        print(f"[!] Falta el snapshot {ruta_relativa(snapshot)}.")
        print("    Bajarlo de https://data.buenosaires.gob.ar/dataset/obras-registradas (recurso CSV).")
        return 1

    avisos = pd.read_csv(resolver(args.entrada), sep="\t", low_memory=False,
                         usecols=["link", "lat", "lon", "geo_status"])
    permisos = filtrar_permisos(leer_snapshot(snapshot))
    print(f"Avisos: {len(avisos)} ({(avisos['geo_status'] == 'OK').sum()} con coordenadas)")
    print(f"Obras con permiso en la ventana (una por punto): {len(permisos)}")

    salida = calcular(avisos, permisos)
    destino = asegurar_directorio(args.salida)
    salida.to_csv(destino, sep="\t", index=False)

    col = salida["permisos_obra_500m"]
    print(f"permisos_obra_500m: mediana {col.median():.0f}, media {col.mean():.1f}, "
          f"máximo {col.max()}, avisos con 0: {(col == 0).sum()}")
    print(f"Salida: {ruta_relativa(destino)} ({len(salida)} filas)")
    return 0 if len(salida) == len(avisos) else 1


if __name__ == "__main__":
    raise SystemExit(main())
