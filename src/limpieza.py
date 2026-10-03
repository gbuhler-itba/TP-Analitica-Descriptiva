"""
Funciones de limpieza reutilizables desde los notebooks.
"""

import re

import numpy as np
import pandas as pd

_PATRON_MONTO = re.compile(r"(US\$|\$)\s?([\d\.]+)")


def _a_numero(texto):
    return float(texto.replace(".", ""))


def corregir_precio(df, col_texto="precio_texto"):
    """Separa precio actual y anterior en avisos con "BAJÓ DE PRECIO".

    El scraper original concatenaba ambos montos en `precio`
    (ej. "US$120.000US$112.000 BAJÓ DE PRECIO" -> 120000112000).
    Devuelve un DataFrame con:
      precio_actual    -> último monto del texto (el vigente)
      precio_anterior  -> primer monto si hubo baja, NaN si no
      bajo_de_precio   -> bool
      baja_pct         -> caída porcentual respecto del precio anterior
    """
    filas = []
    for texto in df[col_texto].fillna(""):
        montos = _PATRON_MONTO.findall(texto)
        if not montos:
            filas.append((np.nan, np.nan, False))
            continue
        actual = _a_numero(montos[-1][1])
        bajo = "BAJÓ DE PRECIO" in texto.upper() and len(montos) >= 2
        anterior = _a_numero(montos[0][1]) if bajo else np.nan
        filas.append((actual, anterior, bajo))
    out = pd.DataFrame(filas, index=df.index,
                       columns=["precio_actual", "precio_anterior", "bajo_de_precio"])
    out["baja_pct"] = 100 * (1 - out["precio_actual"] / out["precio_anterior"])
    return out
