"""
ETAPA 2 - Consolidación de cuotas.

Une los TSV de las cuotas producidas por el scraper en un único dataset y
elimina duplicados por link (una misma propiedad puede aparecer en dos
barrios si el aviso está mal categorizado).

ENTRADA:  data/raw/cuotas/cuota*.tsv   (se excluyen los archivos parciales)
SALIDA:   data/interim/mercadolibre_CABA_completo.tsv

Nota de fidelidad: la lectura usa pd.read_csv(archivo, sep="\t") sin
low_memory=False de forma deliberada. Cambiar ese parámetro altera la
inferencia de tipos de pandas y, con ella, la representación de algunos
valores en el TSV de salida. Se mantiene tal cual para que la salida sea
idéntica byte a byte a la corrida original.
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd

from src.configuracion import agregar_argumento_config, cargar_config, elegir
from src.entorno import verificar_python
from src.qc import ControlCalidad
from src.rutas import asegurar_directorio, resolver, ruta_relativa


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Etapa 2: une las cuotas del scraper y deduplica por link.",
    )
    agregar_argumento_config(parser)
    parser.add_argument("--cuotas-dir", default=None, help="Directorio con los TSV de cuotas.")
    parser.add_argument("--salida", default=None, help="TSV consolidado de salida.")
    parser.add_argument("--patron", default=None, help='Patrón glob de cuotas (default: "cuota*.tsv").')
    parser.add_argument("--logs-dir", default=None, help="Directorio de logs de control de calidad.")
    return parser


def listar_cuotas(cuotas_dir: Path, patron: str):
    """Devuelve los TSV de cuotas ordenados, excluyendo los parciales."""
    archivos = sorted(cuotas_dir.glob(patron))
    return [a for a in archivos if "parcial" not in a.name]


def unir_cuotas(cuotas_dir, salida, patron, clave, logs_dir, columnas_clave) -> int:
    cuotas_dir = resolver(cuotas_dir)
    archivos = listar_cuotas(cuotas_dir, patron)

    print("=== ETAPA 2: UNIR CUOTAS ===")
    print(f"Directorio: {cuotas_dir}")
    print(f"Archivos de cuotas encontrados: {len(archivos)}")
    for a in archivos:
        print(f"  - {a.name}")
    print()

    if not archivos:
        print(f"[!] No se encontraron cuotas en {cuotas_dir}.")
        print("    Corré la etapa 1 (scraping) o revisá --cuotas-dir.")
        return 1

    qc = ControlCalidad("02_consolidacion", logs_dir)
    qc.metrica("archivos_cuotas", len(archivos))

    dfs = []
    filas_por_cuota = {}
    for archivo in archivos:
        df = pd.read_csv(archivo, sep="\t")
        print(f"  {archivo.name}: {len(df)} propiedades, {len(df.columns)} columnas")
        filas_por_cuota[archivo.name] = len(df)
        dfs.append(df)

    df_total = pd.concat(dfs, ignore_index=True)
    filas_entrada = len(df_total)

    duplicados_detectados = qc.duplicados(df_total, [clave], "duplicados_detectados")
    df_total = df_total.drop_duplicates(subset=[clave], keep="first")
    filas_salida = len(df_total)

    destino = asegurar_directorio(salida)
    df_total.to_csv(destino, sep="\t", index=False, encoding="utf-8-sig")

    print(f"\nDataset consolidado: {destino}")

    qc.desglose("filas_por_cuota", filas_por_cuota)
    qc.metrica("filas_entrada", filas_entrada)
    qc.metrica("filas_salida", filas_salida)
    qc.metrica("duplicados_eliminados", filas_entrada - filas_salida)
    qc.metrica("columnas_salida", len(df_total.columns))
    qc.duplicados(df_total, [clave], "duplicados_residuales")
    qc.nulos_por_columna(df_total, columnas_clave)
    qc.desglose("propiedades_por_barrio", df_total["barrio"].value_counts().to_dict())
    qc.metrica("archivo_salida", ruta_relativa(destino))
    qc.cerrar()

    if duplicados_detectados != filas_entrada - filas_salida:
        print("[!] Los duplicados detectados no coinciden con los eliminados.")
        return 1
    return 0


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    verificar_python(avisar=False)
    cfg = cargar_config(args.config)
    return unir_cuotas(
        cuotas_dir=elegir(args.cuotas_dir, cfg["rutas"]["cuotas_dir"]),
        salida=elegir(args.salida, cfg["rutas"]["consolidado"]),
        patron=elegir(args.patron, cfg["consolidacion"]["patron_cuotas"]),
        clave=cfg["consolidacion"]["clave_duplicados"],
        logs_dir=elegir(args.logs_dir, cfg["rutas"]["logs_dir"]),
        columnas_clave=cfg["qc"]["columnas_clave"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
