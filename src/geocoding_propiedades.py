"""
ETAPA 3 - Geocodificación de propiedades.

Convierte las direcciones del dataset consolidado en coordenadas (lat/lon)
usando el normalizador oficial de USIG (Gobierno de la Ciudad de Buenos
Aires). Agrega cuatro columnas: dir_limpia, lat, lon y geo_status.

ENTRADA:  data/interim/mercadolibre_CABA_completo.tsv
SALIDA:   data/interim/propiedades_geocodificadas.tsv
PARCIAL:  data/interim/geocoding_parcial.tsv  (se borra al terminar bien)

El servicio es público y gratuito, por eso hay una pausa deliberada entre
llamadas. La corrida completa sobre 27.922 direcciones son unas 2 horas.

Arreglo respecto de la versión original: el resume de una corrida cortada
se hace con una MÁSCARA BOOLEANA sobre geo_status (se reprocesa toda fila
cuyo geo_status esté vacío) en lugar de asumir que lo ya procesado es un
prefijo contiguo del DataFrame. No cambia el resultado de una corrida
limpia; solo deja de corromper el retome cuando el parcial tiene huecos.
"""

import argparse
import random
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
import requests

from src.configuracion import agregar_argumento_config, cargar_config, elegir
from src.entorno import verificar_python
from src.qc import ControlCalidad
from src.rutas import asegurar_directorio, resolver, ruta_relativa


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Etapa 3: geocodifica las direcciones con el normalizador de USIG.",
    )
    agregar_argumento_config(parser)
    parser.add_argument("--entrada", default=None, help="TSV consolidado de entrada.")
    parser.add_argument("--salida", default=None, help="TSV geocodificado de salida.")
    parser.add_argument("--parcial", default=None, help="TSV de guardado parcial.")
    parser.add_argument("--logs-dir", default=None, help="Directorio de logs de control de calidad.")
    parser.add_argument("--url-usig", default=None, help="Endpoint del normalizador de USIG.")
    parser.add_argument("--max-reintentos", type=int, default=None, help="Reintentos por dirección.")
    parser.add_argument("--timeout", type=int, default=None, help="Timeout por request, en segundos.")
    parser.add_argument("--guardar-cada", type=int, default=None, help="Cada cuántas filas se escribe el parcial.")
    parser.add_argument("--reportar-cada", type=int, default=None, help="Cada cuántas filas se imprime el progreso.")
    parser.add_argument("--limite", type=int, default=None, help="Procesar solo las primeras N filas (para pruebas).")
    parser.add_argument("--sin-resume", action="store_true", help="Ignorar el parcial previo y empezar de cero.")
    return parser


def limpiar_direccion(ubicacion):
    """
    Limpia una dirección de MercadoLibre para geocodificar con USIG.
    Devuelve la query lista, o None si no es geocodificable.
    """
    if pd.isna(ubicacion):
        return None

    # Tomar solo la primera parte (antes de la primera coma) = calle + altura
    parte = ubicacion.split(",")[0].strip()

    # Normalizar "Av." y "Av" a "Avenida" ANTES de tocar los puntos
    parte = re.sub(r"\bAv\.\s*", "Avenida ", parte)
    parte = re.sub(r"\bAv\s+", "Avenida ", parte)

    # Sacar texto después de un punto (ej: "Sinclair 3100. Entre...")
    if ". " in parte:
        parte = parte.split(". ")[0].strip()

    # Reemplazar " Al " (abreviatura de "altura") por espacio
    parte = re.sub(r"\s+Al\s+", " ", parte)

    # Limpiar espacios múltiples
    parte = re.sub(r"\s+", " ", parte).strip()

    # ¿Geocodificable? Tiene altura (número) o es esquina (" Y ")
    tiene_altura = bool(re.search(r"\d", parte))
    es_esquina = " Y " in parte.upper()

    if not tiene_altura and not es_esquina:
        return None

    return parte


def geocode_usig(direccion_limpia, url_usig, max_reintentos=3, timeout=10,
                 espera_http=3, espera_conexion=5):
    """
    Geocodifica una dirección limpia usando USIG.
    Devuelve (lat, lon, status).
    """
    if not direccion_limpia:
        return None, None, "NO_GEOCODIFICABLE"

    query = f"{direccion_limpia}, caba"
    params = {"direccion": query, "geocodificar": "true"}

    for intento in range(max_reintentos):
        try:
            r = requests.get(url_usig, params=params, timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                normalizadas = data.get("direccionesNormalizadas", [])
                if normalizadas:
                    coord = normalizadas[0].get("coordenadas", {})
                    lat = coord.get("y")
                    lon = coord.get("x")
                    if lat and lon:
                        return float(lat), float(lon), "OK"
                    else:
                        return None, None, "SIN_COORDENADAS"
                else:
                    return None, None, "SIN_RESULTADO"
            else:
                time.sleep(espera_http)
        except requests.exceptions.Timeout:
            time.sleep(espera_http)
        except requests.exceptions.ConnectionError:
            time.sleep(espera_conexion)
        except Exception as e:
            return None, None, f"ERROR_{type(e).__name__}"

    return None, None, "FALLO_REINTENTOS"


def geocodificar(entrada, salida, parcial, logs_dir, cfg_geo, columnas_clave,
                 limite=None, sin_resume=False) -> int:
    entrada = resolver(entrada)
    destino = asegurar_directorio(salida)
    ruta_parcial = asegurar_directorio(parcial)

    if not entrada.exists():
        print(f"[!] No se encontró la entrada: {entrada}")
        print("    Corré primero la etapa 2 (unir_cuotas).")
        return 1

    print("=== ETAPA 3: GEOCODIFICACIÓN ===")
    print(f"Cargando {entrada}...")
    df = pd.read_csv(entrada, sep="\t", low_memory=False)
    filas_entrada = len(df)
    print(f"  {filas_entrada} propiedades cargadas.")

    print("\nLimpiando direcciones...")
    df["dir_limpia"] = df["ubicacion"].apply(limpiar_direccion)
    geocodificables = int(df["dir_limpia"].notna().sum())
    print(f"  Geocodificables: {geocodificables} ({100 * geocodificables / filas_entrada:.1f}%)")
    print(f"  No geocodificables (se marcarán sin coords): {filas_entrada - geocodificables}")

    # Retomar una corrida cortada, si hay parcial previo.
    if ruta_parcial.exists() and not sin_resume:
        print(f"\n[!] Encontrado parcial previo: {ruta_parcial}")
        df_parcial = pd.read_csv(ruta_parcial, sep="\t", low_memory=False)
        if len(df_parcial) == len(df):
            ya_hechas = int(df_parcial["geo_status"].notna().sum())
            print(f"    Ya procesadas: {ya_hechas}. Se reprocesan solo las filas sin geo_status.")
            df = df_parcial
        else:
            print(f"    [!] El parcial tiene {len(df_parcial)} filas y la entrada {len(df)}.")
            print("        Se ignora el parcial y se arranca de cero.")
            df["lat"] = None
            df["lon"] = None
            df["geo_status"] = None
    else:
        df["lat"] = None
        df["lon"] = None
        df["geo_status"] = None

    # Máscara booleana: pendiente es toda fila sin geo_status, esté donde esté.
    pendientes = df.index[df["geo_status"].isna()].tolist()
    if limite is not None:
        pendientes = pendientes[:limite]

    total_pendientes = len(pendientes)
    print(f"\n=== GEOCODIFICANDO ({total_pendientes} pendientes de {len(df)}) ===")
    t_inicio = time.time()
    delay_min, delay_max = cfg_geo["delay"]

    for n, i in enumerate(pendientes, 1):
        lat, lon, status = geocode_usig(
            df.at[i, "dir_limpia"],
            url_usig=cfg_geo["url_usig"],
            max_reintentos=cfg_geo["max_reintentos"],
            timeout=cfg_geo["timeout"],
            espera_http=cfg_geo["espera_http"],
            espera_conexion=cfg_geo["espera_conexion"],
        )

        df.at[i, "lat"] = lat
        df.at[i, "lon"] = lon
        df.at[i, "geo_status"] = status

        if n % cfg_geo["reportar_cada"] == 0:
            transcurrido = time.time() - t_inicio
            vel = n / transcurrido if transcurrido > 0 else 0
            faltan = total_pendientes - n
            eta_min = (faltan / vel / 60) if vel > 0 else 0
            ok = int((df["geo_status"] == "OK").sum())
            print(f"  [{n}/{total_pendientes}] OK: {ok} | vel: {vel:.1f}/s | ETA: {eta_min:.0f} min")

        if n % cfg_geo["guardar_cada"] == 0:
            df.to_csv(ruta_parcial, sep="\t", index=False, encoding="utf-8-sig")

        time.sleep(random.uniform(delay_min, delay_max))

    df.to_csv(destino, sep="\t", index=False, encoding="utf-8-sig")
    if ruta_parcial.exists():
        ruta_parcial.unlink()

    print(f"\nDataset geocodificado: {destino}")

    qc = ControlCalidad("03_geocoding", logs_dir)
    qc.metrica("filas_entrada", filas_entrada)
    qc.metrica("filas_salida", len(df))
    qc.metrica("columnas_salida", len(df.columns))
    qc.metrica("direcciones_geocodificables", geocodificables)
    qc.metrica("direcciones_no_geocodificables", filas_entrada - geocodificables)
    qc.metrica("filas_procesadas_en_esta_corrida", total_pendientes)
    qc.tasa_geocoding(df)
    qc.metrica("coordenadas_presentes", int(df["lat"].notna().sum()))
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
    cfg_geo = dict(cfg["geocoding"])
    cfg_geo["url_usig"] = elegir(args.url_usig, cfg_geo["url_usig"])
    cfg_geo["max_reintentos"] = elegir(args.max_reintentos, cfg_geo["max_reintentos"])
    cfg_geo["timeout"] = elegir(args.timeout, cfg_geo["timeout"])
    cfg_geo["guardar_cada"] = elegir(args.guardar_cada, cfg_geo["guardar_cada"])
    cfg_geo["reportar_cada"] = elegir(args.reportar_cada, cfg_geo["reportar_cada"])

    parcial_default = str(Path(cfg["rutas"]["geocodificado"]).parent / "geocoding_parcial.tsv")
    return geocodificar(
        entrada=elegir(args.entrada, cfg["rutas"]["consolidado"]),
        salida=elegir(args.salida, cfg["rutas"]["geocodificado"]),
        parcial=elegir(args.parcial, parcial_default),
        logs_dir=elegir(args.logs_dir, cfg["rutas"]["logs_dir"]),
        cfg_geo=cfg_geo,
        columnas_clave=cfg["qc"]["columnas_clave"],
        limite=args.limite,
        sin_resume=args.sin_resume,
    )


if __name__ == "__main__":
    raise SystemExit(main())
