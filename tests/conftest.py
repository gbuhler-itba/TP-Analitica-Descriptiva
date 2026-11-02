"""
Configuración común de pytest.

Agrega la raíz del repositorio al sys.path para que los tests puedan hacer
`from src import ...` sin instalar el proyecto como paquete, igual que los
scripts de src/.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def dataset_sintetico(n=400, semilla=0):
    """Avisos con todas las columnas que usan los modelos, en dos barrios con dos sub-zonas cada uno."""
    from src import modelo

    rng = np.random.default_rng(semilla)
    barrio = rng.choice(["Almagro", "Boedo"], n)
    sub = rng.integers(0, 2, n)
    lat = np.where(barrio == "Almagro", -34.60, -34.63) + 0.01 * sub + rng.normal(0, 0.002, n)
    lon = -58.42 + 0.01 * sub + rng.normal(0, 0.002, n)
    m2 = rng.uniform(30, 120, n)
    precio_m2 = 2000 * np.where(barrio == "Almagro", 1.1, 0.9) * (1 + 0.1 * sub) * rng.lognormal(0, 0.1, n)
    df = pd.DataFrame({
        "id_aviso": [f"MLA{i}" for i in range(n)],
        "dir_limpia": [f"calle {i}" for i in range(n)],
        "barrio": barrio,
        "subzona": [f"{b}_{s}" for b, s in zip(barrio, sub)],
        "lat": lat, "lon": lon,
        "m2_final": m2,
        "precio_m2_usd": precio_m2,
        "ambientes": rng.integers(1, 5, n).astype(float),
        "dormitorios": rng.integers(0, 4, n).astype(float),
        "banos": np.where(rng.random(n) < 0.2, np.nan, rng.integers(1, 3, n)),
        "cocheras": rng.integers(0, 2, n).astype(float),
        "antiguedad": np.where(rng.random(n) < 0.2, np.nan, rng.integers(0, 90, n)),
        "numero_de_piso_de_la_unidad": np.where(rng.random(n) < 0.2, np.nan, rng.integers(0, 12, n)),
        "disposicion": rng.choice(["Frente", "Contrafrente"], n),
        "apto_credito": rng.choice(["Sí", "No"], n),
        "titulo": rng.choice(["Depto a reciclar", "Depto luminoso", "Depto a estrenar"], n),
        "titulo_casa": rng.random(n) < 0.05,
        "titulo_tipo_casa": rng.random(n) < 0.05,
        "expensas_usd": np.where(rng.random(n) < 0.2, np.nan, rng.uniform(50, 300, n)),
    })
    for c in modelo.AMENITIES_Y_EXTRAS:
        df[c] = rng.choice(["Sí", "No"], n)
    return df, np.log(df["precio_m2_usd"])


@pytest.fixture(scope="session")
def avisos_sinteticos():
    """(df, y) sintéticos con todas las columnas que usan los modelos (ver `dataset_sintetico`)."""
    return dataset_sintetico()
