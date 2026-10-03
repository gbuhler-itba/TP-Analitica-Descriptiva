"""
Índice de confort: construcción parametrizable y diagnóstico.

La asignación de columnas a bloques y los pesos son una PROPUESTA A VALIDAR,
no una definición cerrada. Todo lo que es decisión de criterio vive en
MAPEO_BLOQUES, PESOS_BASE y en los argumentos de las funciones, para poder
contrastar alternativas sin tocar la lógica.
"""

import numpy as np
import pandas as pd

# Borrador de mapeo. Sale de la descripción del README (sección 1).
# Pendiente de validación por el grupo.
MAPEO_BLOQUES = {
    "infraestructura": [
        "gas_natural",
        "agua_corriente",
        "aire_acondicionado",
        "calefaccion",
        "acceso_a_internet",
        "con_conexion_para_lavarropas",
        "ascensor",
    ],
    "amenities": [
        "pileta",
        "gimnasio",
        "sauna",
        "salon_de_usos_multiples",
        "seguridad",
        "parrilla",
        "lavanderia",
        "roof_garden",
        "salon_de_fiestas",
        "playroom",
    ],
    "atributos": [
        "balcon",
        "terraza",
        "es_frente",
        "es_piso_alto",
    ],
}

PESOS_BASE = {"infraestructura": 0.45, "amenities": 0.30, "atributos": 0.25}

PISO_ALTO_DESDE = 5  # criterio a validar


def preparar_componentes(df, piso_alto_desde=PISO_ALTO_DESDE):
    """Devuelve un DataFrame con cada componente codificado 1 / 0 / NaN.

    1 = "Sí", 0 = "No", NaN = no declarado en el aviso.
    Las variables derivadas (es_frente, es_piso_alto) quedan en NaN cuando la
    columna de origen es nula.
    """
    comp = pd.DataFrame(index=df.index)
    for bloque, columnas in MAPEO_BLOQUES.items():
        for col in columnas:
            if col in df.columns:
                comp[col] = df[col].map({"Sí": 1.0, "No": 0.0})
    comp["es_frente"] = np.where(
        df["disposicion"].isna(), np.nan, (df["disposicion"] == "Frente").astype(float)
    )
    comp["es_piso_alto"] = np.where(
        df["numero_de_piso_de_la_unidad"].isna(),
        np.nan,
        (df["numero_de_piso_de_la_unidad"] >= piso_alto_desde).astype(float),
    )
    return comp


def tipo_de_columna(serie_original):
    """Clasifica una columna según cómo la publica la plataforma."""
    valores = set(serie_original.dropna().unique())
    if valores == {"Sí"}:
        return "solo_si"  # el nulo no distingue "no tiene" de "no lo cargó"
    if {"Sí", "No"} <= valores:
        return "si_no"  # el nulo es falta de dato
    return "otro"


def puntaje_bloques(comp, tratamiento_nulos="nulo_es_no"):
    """Puntaje 0-1 por bloque.

    tratamiento_nulos:
      "nulo_es_no"      -> NaN cuenta como ausencia (0)
      "solo_declarados" -> promedio sobre los componentes con dato
    """
    bloques = pd.DataFrame(index=comp.index)
    for bloque, columnas in MAPEO_BLOQUES.items():
        sub = comp[columnas]
        if tratamiento_nulos == "nulo_es_no":
            bloques[bloque] = sub.fillna(0).mean(axis=1)
        elif tratamiento_nulos == "solo_declarados":
            bloques[bloque] = sub.mean(axis=1, skipna=True)
        else:
            raise ValueError(f"tratamiento_nulos desconocido: {tratamiento_nulos}")
    return bloques


def completitud(comp):
    """Proporción de componentes del índice con dato declarado."""
    return comp.notna().mean(axis=1)


def indice(bloques, pesos):
    """Índice 1-10 como suma ponderada de bloques 0-1."""
    total = sum(pesos.values())
    x = sum(bloques[b] * (w / total) for b, w in pesos.items())
    return 1 + 9 * x


def gap_por_zona(log_pm2, indice_serie, zona):
    """Residuo de log(precio/m2) explicado por el índice, ajustado dentro de cada zona.

    Residuo negativo = precio bajo para el confort que declara.
    Es una señal de precio atípico para investigar, no una subvaluación comprobada.
    """
    res = pd.Series(np.nan, index=log_pm2.index)
    datos = pd.DataFrame({"y": log_pm2, "x": indice_serie, "z": zona}).dropna()
    for _, g in datos.groupby("z"):
        if len(g) < 10 or g["x"].std() == 0:
            res.loc[g.index] = g["y"] - g["y"].mean()
            continue
        b, a = np.polyfit(g["x"], g["y"], 1)
        res.loc[g.index] = g["y"] - (a + b * g["x"])
    return res
