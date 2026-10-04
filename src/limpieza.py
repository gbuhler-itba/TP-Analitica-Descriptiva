"""
Funciones de limpieza reutilizables desde los notebooks.

Cada función hace una sola transformación y devuelve columnas nuevas, sin
pisar las originales, para poder comparar crudo vs. procesado.
"""

import re

import numpy as np
import pandas as pd

_PATRON_MONTO = re.compile(r"(US\$|\$)\s?([\d\.]+)")
_PATRON_MILES_AMBIGUO = re.compile(r"^\d{1,3}(\.\d{3})+$")


def _a_numero(texto):
    return float(texto.replace(".", ""))


# ---------------------------------------------------------------------------
# Identificador y duplicados
# ---------------------------------------------------------------------------
def extraer_id_aviso(link):
    """ID estable del aviso (ej. "MLA1661865565").

    El link completo trae parámetros de seguimiento que cambian en cada
    búsqueda, por eso deduplicar por link no detecta el mismo aviso
    aparecido en dos barrios.
    """
    return link.str.extract(r"(MLA-?\d+)")[0].str.replace("-", "", regex=False)


def marcar_posible_duplicado(df, columnas=("precio_usd", "m2_final", "dir_limpia", "ambientes")):
    """True si otro aviso (con otro ID) tiene el mismo precio, superficie,
    dirección y ambientes. Puede ser el mismo depto publicado por dos
    inmobiliarias o unidades idénticas de un edificio nuevo: se marca, no se borra.
    """
    columnas = list(columnas)
    con_dir = df["dir_limpia"].notna()
    marca = df.loc[con_dir].duplicated(columnas, keep=False)
    return marca.reindex(df.index, fill_value=False).astype(bool)


# ---------------------------------------------------------------------------
# Precio
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Superficie
# ---------------------------------------------------------------------------
def parsear_superficie(serie):
    """Texto "103,71 m²" -> 103.71. Devuelve NaN cuando:
    - la unidad no es m² (hay "ha");
    - el número tiene punto de miles ("45.000 m²" en un 2 ambientes): es
      ambiguo y no se puede saber qué quiso cargar el anunciante.
    """
    def _uno(texto):
        if pd.isna(texto) or not str(texto).endswith(" m²"):
            return np.nan
        numero = str(texto)[:-3].strip()
        if _PATRON_MILES_AMBIGUO.match(numero):
            return np.nan
        return float(numero.replace(",", "."))
    return serie.map(_uno)


def superficie_final(df, minimo=15, maximo=1000):
    """Superficie de trabajo y su origen.

    - m2 del listado si está entre minimo y maximo (caso normal);
    - si no, superficie total de la ficha, si cae en el rango ("1 m²
      cubierto, 26 m² totales" es un error de carga del cubierto);
    - si ninguna sirve, NaN.
    """
    total = parsear_superficie(df["superficie_total"])
    m2_ok = df["m2"].between(minimo, maximo)
    total_ok = total.between(minimo, maximo)
    valor = np.where(m2_ok, df["m2"], np.where(total_ok, total, np.nan))
    origen = np.where(m2_ok, "listado", np.where(total_ok, "recuperada_de_total", "invalida"))
    return pd.Series(valor, index=df.index), pd.Series(origen, index=df.index)


# ---------------------------------------------------------------------------
# Antigüedad
# ---------------------------------------------------------------------------
def parsear_antiguedad(serie, anio_referencia=2026, maximo=150):
    """Texto "71 años" -> 71. Casos especiales:
    - valores >= 1800 son el año de construcción, no la edad ("1.976 años");
    - valores negativos ("-2 años") son edificios en construcción: edad 0 y
      se marcan aparte;
    - edades mayores a `maximo` pasan a NaN (error de carga).
    Devuelve (antiguedad, en_construccion).
    """
    numero = pd.to_numeric(
        serie.str.replace(r"\s*años?$", "", regex=True).str.replace(".", "", regex=False),
        errors="coerce",
    )
    numero = numero.where(numero < 1800, anio_referencia - numero)
    en_construccion = numero < 0
    numero = numero.where(~en_construccion, 0)
    numero = numero.where(numero <= maximo, np.nan)
    return numero, en_construccion


# ---------------------------------------------------------------------------
# Expensas
# ---------------------------------------------------------------------------
def parsear_expensas(serie, maximo_ars=10_000_000):
    """Texto "290.000 ARS" -> (290000, "ARS").

    - 0 pasa a NaN: un departamento sin expensas es casi imposible, se lee
      como "no informado";
    - montos en ARS por encima de `maximo_ars` pasan a NaN (errores de carga
      del tipo 111.111.111.111).
    Devuelve (monto, moneda).
    """
    moneda = serie.str.extract(r"\s(ARS|USD)$")[0]
    monto = pd.to_numeric(
        serie.str.replace(r"\s(ARS|USD)$", "", regex=True).str.replace(".", "", regex=False),
        errors="coerce",
    )
    monto = monto.where(monto > 0, np.nan)
    monto = monto.where(~((moneda == "ARS") & (monto > maximo_ars)), np.nan)
    return monto, moneda


def expensas_en_ars(monto, moneda, tipo_cambio):
    """Unifica expensas a pesos. Las publicadas en USD se convierten con
    `tipo_cambio` (ARS por USD, a la fecha de extracción)."""
    return np.where(moneda == "USD", monto * tipo_cambio, monto)


# ---------------------------------------------------------------------------
# Alcance y outliers
# ---------------------------------------------------------------------------
def motivo_fuera_de_alcance(df, precio_minimo=20_000, precio_m2_maximo=50_000):
    """Motivo por el que un aviso queda fuera del alcance (NaN si queda adentro).

    El alcance es: departamento usado en venta, precio en USD y superficie
    interpretable. Los avisos en pozo (columna `en_construccion`, si existe)
    quedan fuera porque no son usados. `precio_m2_maximo` corta errores de carga (USD 111.111.111
    por 163 m²): está muy por encima del máximo real del mercado de CABA.
    """
    motivo = pd.Series(np.nan, index=df.index, dtype="object")
    motivo[df["moneda"] != "USD"] = "precio_en_pesos"
    if "en_construccion" in df.columns:
        motivo[motivo.isna() & df["en_construccion"]] = "en_pozo"
    motivo[motivo.isna() & (df["precio_usd"] < precio_minimo)] = "precio_menor_a_minimo"
    motivo[motivo.isna() & df["m2_final"].isna()] = "superficie_invalida"
    motivo[motivo.isna() & (df["precio_usd"] / df["m2_final"] > precio_m2_maximo)] = "precio_imposible"
    return motivo


def menciona_alquiler(titulo):
    """True si el título menciona alquiler. Se marca, no se excluye: los
    precios de esos avisos son de venta (el título suele estar mal)."""
    return titulo.fillna("").str.contains(r"alquil", case=False)


def outliers_iqr_por_grupo(valores, grupo, k=1.5, minimo_grupo=10):
    """Marca outliers con el criterio IQR (Q1 - k*IQR, Q3 + k*IQR) calculado
    dentro de cada grupo. Grupos con menos de `minimo_grupo` datos no se
    evalúan (devuelven False)."""
    datos = pd.DataFrame({"v": valores, "g": grupo})
    q1 = datos.groupby("g")["v"].transform(lambda s: s.quantile(0.25))
    q3 = datos.groupby("g")["v"].transform(lambda s: s.quantile(0.75))
    n = datos.groupby("g")["v"].transform("count")
    iqr = q3 - q1
    fuera = (datos["v"] < q1 - k * iqr) | (datos["v"] > q3 + k * iqr)
    return fuera & (n >= minimo_grupo) & datos["v"].notna()
