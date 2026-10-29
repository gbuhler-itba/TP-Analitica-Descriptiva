"""
Etapa 5 del pipeline: limpieza del dataset enriquecido.

Es la misma lógica que el notebook 01 explica paso a paso, en un solo lugar y
sin gráficos. El notebook 01 verifica al final que su resultado coincide con
el de esta función.

ENTRADA: data/processed/propiedades_enriquecidas.tsv (etapa 4)
SALIDAS: data/processed/propiedades_limpias.tsv
         data/processed/registro_limpieza.csv (lo que se eliminó y por qué)

Uso:  python3 src/limpiar.py   (o python3 run_pipeline.py --desde-etapa 5)
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import limpieza  # noqa: E402
from src.configuracion import agregar_argumento_config, cargar_config  # noqa: E402
from src.qc import ControlCalidad  # noqa: E402
from src.rutas import asegurar_directorio, resolver, ruta_relativa  # noqa: E402


def incoherencia_piso(df, pisos_edificio_desde=3):
    """Piso de la unidad mayor que los pisos del edificio.

    `cantidad_de_pisos` mezcla las plantas del departamento (1, o 2 en un
    dúplex) con los pisos del edificio: solo se compara desde
    `pisos_edificio_desde` (con 0 se reproduce el criterio de la PreEntrega 2).
    """
    piso = df["numero_de_piso_de_la_unidad"]
    pisos = df["cantidad_de_pisos"]
    return (pisos >= pisos_edificio_desde) & (piso > pisos)


def limpiar(df_crudo, p):
    """Del dataset enriquecido al limpio. `p`: sección `limpieza` de la configuración.

    Devuelve (df_limpio, registro, conteos).
    """
    df = df_crudo.copy()
    conteos = {}

    # Identificador y duplicados por ID (se conserva la primera aparición)
    df["id_aviso"] = limpieza.extraer_id_aviso(df["link"])
    duplicados_id = df[df["id_aviso"].duplicated(keep="first")].copy()
    duplicados_id["motivo"] = "duplicado_mismo_id"
    df = df.drop_duplicates("id_aviso", keep="first").copy()
    conteos["duplicados_id"] = len(duplicados_id)

    # Precio corregido ("BAJÓ DE PRECIO" concatenado)
    precios = limpieza.corregir_precio(df)
    df["precio_usd"] = precios["precio_actual"]
    df["precio_anterior_usd"] = precios["precio_anterior"]
    df["bajo_de_precio"] = precios["bajo_de_precio"]
    df["baja_pct"] = precios["baja_pct"].round(1)
    conteos["bajo_de_precio"] = int(df["bajo_de_precio"].sum())

    # Superficie y precio por m²
    df["m2_final"], df["m2_origen"] = limpieza.superficie_final(df, p["m2_minimo"], p["m2_maximo"])
    df["precio_m2_usd"] = df["precio_usd"] / df["m2_final"]

    # Antigüedad y expensas
    df["antiguedad"], df["en_construccion"] = limpieza.parsear_antiguedad(
        df["antig_edad"], p["anio_referencia"], p["antiguedad_maxima"])
    df["expensas_monto"], df["expensas_moneda"] = limpieza.parsear_expensas(df["expensas"], p["expensas_maximo_ars"])
    tc = p["tipo_cambio_ars_usd"]
    df["expensas_ars"] = limpieza.expensas_en_ars(df["expensas_monto"], df["expensas_moneda"], tc)
    relleno = df["expensas_ars"] < p["expensas_minimo_ars"]
    df.loc[relleno, ["expensas_monto", "expensas_ars"]] = np.nan
    df["expensas_usd"] = df["expensas_ars"] / tc
    conteos["expensas_relleno"] = int(relleno.sum())

    # Faltantes disfrazados y correcciones de carga
    df["departamentos_por_piso"] = df["departamentos_por_piso"].replace(99, np.nan)
    df["ambientes"] = df["ambientes"].replace(0, np.nan)
    df["banos"] = df["banos"].replace(0, np.nan)
    conteos["piso_como_unidad"] = int((df["numero_de_piso_de_la_unidad"] >= 100).sum())
    df["numero_de_piso_de_la_unidad"] = limpieza.piso_desde_numero_de_unidad(df["numero_de_piso_de_la_unidad"])
    df["tipo_de_seguridad"] = df["tipo_de_seguridad"].replace({"24 hs": "24 horas"})
    df["tipo_de_departamento"] = df["tipo_de_departamento"].replace({"Penthhouse": "Penthouse"})

    # Fuera de alcance
    df["motivo_exclusion"] = limpieza.motivo_fuera_de_alcance(df, p["precio_minimo_usd"], p["precio_m2_maximo_usd"])
    excluidos = df[df["motivo_exclusion"].notna()].copy()
    df_limpio = df[df["motivo_exclusion"].isna()].drop(columns="motivo_exclusion").copy()

    # Marcas (no se elimina nada)
    df_limpio["posible_duplicado"] = limpieza.marcar_posible_duplicado(df_limpio)
    df_limpio["menciona_alquiler"] = limpieza.menciona_alquiler(df_limpio["titulo"])
    df_limpio = df_limpio.join(limpieza.marcas_casa(df_limpio["titulo"]))
    df_limpio["titulo_barrio_popular"] = limpieza.menciona_barrio_popular(df_limpio["titulo"])
    grupo = df_limpio["subzona"].fillna(df_limpio["barrio"])
    df_limpio["outlier_precio_m2"] = limpieza.outliers_iqr_por_grupo(df_limpio["precio_m2_usd"], grupo, k=p["iqr_k"])
    es_monoambiente = (df_limpio["ambientes"] == 1) & (df_limpio["dormitorios"] == 1)
    df_limpio["incoherencia_dormitorios"] = (df_limpio["dormitorios"] >= df_limpio["ambientes"]) & ~es_monoambiente
    df_limpio["incoherencia_piso"] = incoherencia_piso(df_limpio, p["pisos_edificio_desde"])

    registro = pd.concat([
        duplicados_id[["id_aviso", "link", "barrio", "precio", "m2", "motivo"]],
        excluidos[["id_aviso", "link", "barrio", "precio", "m2", "motivo_exclusion"]].rename(
            columns={"motivo_exclusion": "motivo"}),
    ], ignore_index=True)
    conteos["excluidos"] = excluidos["motivo_exclusion"].value_counts().to_dict()
    return df_limpio, registro, conteos


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Etapa 5: limpieza del dataset enriquecido.")
    agregar_argumento_config(parser)
    return parser


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    cfg = cargar_config(args.config)
    rutas = cfg["rutas"]
    entrada = resolver(rutas["enriquecido"])
    if not entrada.exists():
        print(f"[!] No se encontró el dataset enriquecido: {entrada}")
        return 1

    print("=== ETAPA 5: LIMPIEZA ===")
    df_crudo = pd.read_csv(entrada, sep="\t", low_memory=False)
    df_limpio, registro, conteos = limpiar(df_crudo, cfg["limpieza"])
    df_limpio.to_csv(asegurar_directorio(rutas["limpio"]), sep="\t", index=False)
    registro.to_csv(asegurar_directorio(rutas["registro_limpieza"]), index=False)
    print(f"  {len(df_crudo):,} avisos -> {len(df_limpio):,} ({len(registro)} eliminados, ver registro)")

    qc = ControlCalidad("05_limpieza", rutas["logs_dir"])
    qc.metrica("filas_entrada", len(df_crudo))
    qc.metrica("filas_salida", len(df_limpio))
    qc.metrica("columnas_salida", df_limpio.shape[1])
    qc.metrica("duplicados_id_eliminados", conteos["duplicados_id"])
    qc.desglose("excluidos_por_motivo", conteos["excluidos"])
    qc.metrica("bajo_de_precio", conteos["bajo_de_precio"])
    qc.metrica("expensas_de_relleno", conteos["expensas_relleno"])
    qc.metrica("piso_cargado_como_unidad", conteos["piso_como_unidad"])
    qc.duplicados(df_limpio, ["id_aviso"], "duplicados_residuales")
    qc.nulos_por_columna(df_limpio, ["id_aviso", "precio_usd", "m2_final", "precio_m2_usd", "barrio"])
    qc.metrica("archivo_salida", ruta_relativa(resolver(rutas["limpio"])))
    qc.cerrar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
