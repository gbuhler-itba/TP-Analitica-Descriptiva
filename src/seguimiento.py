"""
Segundo relevamiento y seguimiento de los avisos (PreEntrega 3, pregunta P4).

Une las cuotas del segundo scraping (27 y 28 de octubre de 2026) y cruza cada
aviso del dataset limpio del primer relevamiento (14 de agosto) con lo que se
encuentra dos meses y medio después:

  - sigue con el mismo ID;
  - republicado: el ID desapareció, pero aparece un aviso nuevo con la misma
    dirección, superficie y ambientes (las inmobiliarias republican para
    aparecer como aviso nuevo);
  - salió: no aparece de ninguna de las dos formas. Salir del portal no
    prueba una venta (puede ser un aviso retirado).

Los barrios que llegaron al tope de paginación de MercadoLibre (2.016 avisos)
en alguno de los dos relevamientos son una muestra de la oferta, no el total:
ahí que un aviso no aparezca no significa que salió. Se marcan con
`barrio_truncado` y se excluyen del análisis de salida.

ENTRADAS: data/raw/relevamiento_2/*.tsv, data/processed/propiedades_limpias.tsv
SALIDAS:  data/processed/relevamiento_2.tsv      un aviso por fila, segundo relevamiento
          data/processed/seguimiento_avisos.csv  un aviso del primer relevamiento por fila

Uso:  python3 src/seguimiento.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src import limpieza  # noqa: E402
from src.geocoding_propiedades import limpiar_direccion  # noqa: E402
from src.rutas import resolver  # noqa: E402

# Archivos del segundo relevamiento: (archivo, barrios a tomar o None, fecha)
# La cuota 2 se cortó a la mitad de Barrio Norte: del parcial se toma solo
# Villa Crespo (completo) y el resto de la cuota se volvió a correr entero.
ARCHIVOS_R2 = [
    ("cuota1.tsv", None, "2026-10-27"),
    ("cuota2_parcial.tsv", ["villa-crespo"], "2026-10-27"),
    ("cuota_custom.tsv", None, "2026-10-28"),
    ("cuota3.tsv", None, "2026-10-27"),
    ("cuota4.tsv", None, "2026-10-27"),
    ("cuota5.tsv", None, "2026-10-28"),
]
TOPE_PAGINACION = 2016
UMBRAL_CAMBIO = 0.005   # cambios de precio menores a 0,5% se toman como "sin cambio"


def clave_unidad(df):
    """Dirección normalizada + superficie + ambientes (para detectar republicaciones)."""
    ambientes = pd.to_numeric(df["ambientes"], errors="coerce").replace(0, np.nan).astype(float)
    clave = (df["dir_limpia"].fillna("").str.upper().str.strip() + "|"
             + df["m2_final"].astype(float).round(0).astype(str) + "|" + ambientes.astype(str))
    return clave.where(df["dir_limpia"].notna())


def consolidar_relevamiento_2(directorio="data/raw/relevamiento_2"):
    """Une las cuotas del segundo relevamiento, una fila por ID de aviso."""
    partes = []
    for archivo, barrios, fecha in ARCHIVOS_R2:
        d = pd.read_csv(resolver(directorio) / archivo, sep="\t", encoding="utf-8-sig", low_memory=False)
        if barrios:
            d = d[d["barrio"].isin(barrios)]
        partes.append(d.assign(archivo=archivo, fecha_relevamiento=fecha))
    r2 = pd.concat(partes, ignore_index=True)
    r2["id_aviso"] = limpieza.extraer_id_aviso(r2["link"])
    r2 = r2.drop_duplicates("id_aviso").reset_index(drop=True)
    precios = limpieza.corregir_precio(r2)
    r2["precio_usd"] = precios["precio_actual"].values
    r2["bajo_de_precio"] = precios["bajo_de_precio"].values
    r2["m2_final"], r2["m2_origen"] = limpieza.superficie_final(r2, 15, 1000)
    r2["dir_limpia"] = r2["ubicacion"].map(limpiar_direccion)
    r2["clave_unidad"] = clave_unidad(r2)
    return r2


def avisos_por_barrio_r1(directorio="data/raw/cuotas"):
    """Avisos por barrio en el crudo del primer relevamiento (antes de la limpieza)."""
    cuotas = [pd.read_csv(f, sep="\t", encoding="utf-8-sig", usecols=["barrio"])
              for f in sorted(resolver(directorio).glob("cuota*.tsv"))]
    return pd.concat(cuotas)["barrio"].value_counts()


def seguir_avisos(r1, r2, crudo_r1_por_barrio):
    """Estado de cada aviso del primer relevamiento en el segundo."""
    s = r1[["id_aviso", "barrio", "precio_usd", "m2_final", "ambientes", "dir_limpia"]].copy()
    s["clave_unidad"] = clave_unidad(s)
    mismo_id = r2.set_index("id_aviso")["precio_usd"]
    s["precio_r2_mismo_id"] = s["id_aviso"].map(mismo_id)
    nuevos = r2[~r2["id_aviso"].isin(r1["id_aviso"])]
    precio_republicado = nuevos.dropna(subset=["clave_unidad"]).groupby("clave_unidad")["precio_usd"].min()

    sigue = s["precio_r2_mismo_id"].notna()
    republicado = ~sigue & s["clave_unidad"].isin(precio_republicado.index)
    s["estado"] = np.select([sigue, republicado], ["sigue", "republicado"], "salio")
    s["precio_r2"] = s["precio_r2_mismo_id"].where(sigue, s["clave_unidad"].map(precio_republicado))
    s["cambio_precio"] = s["precio_r2"] / s["precio_usd"] - 1
    s["bajo_en_r2"] = s["cambio_precio"] < -UMBRAL_CAMBIO
    s["subio_en_r2"] = s["cambio_precio"] > UMBRAL_CAMBIO

    conteo = pd.concat([crudo_r1_por_barrio, r2["barrio"].value_counts()], axis=1).max(axis=1)
    s["barrio_truncado"] = s["barrio"].map(conteo) >= TOPE_PAGINACION
    s["salio"] = s["estado"] == "salio"
    return s.drop(columns=["precio_r2_mismo_id", "dir_limpia", "m2_final", "ambientes", "precio_usd", "barrio"])


def main() -> int:
    r1 = pd.read_csv(resolver("data/processed/propiedades_limpias.tsv"), sep="\t", low_memory=False)
    r2 = consolidar_relevamiento_2()
    seguimiento = seguir_avisos(r1, r2, avisos_por_barrio_r1())
    r2.to_csv(resolver("data/processed/relevamiento_2.tsv"), sep="\t", index=False)
    seguimiento.to_csv(resolver("data/processed/seguimiento_avisos.csv"), index=False)
    print(f"Segundo relevamiento: {len(r2):,} avisos | seguimiento: {len(seguimiento):,} avisos del primero")
    print(seguimiento["estado"].value_counts().to_string())
    print(f"Barrios truncados: {sorted(r1.loc[r1['id_aviso'].isin(seguimiento.loc[seguimiento['barrio_truncado'], 'id_aviso']), 'barrio'].unique())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
