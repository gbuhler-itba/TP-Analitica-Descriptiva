"""Las funciones que reciben `y` (o Series derivadas) no tienen que modificar lo que reciben.

Test de regresión: si una función agrandara su entrada in place (por ejemplo,
asignando con una etiqueta que no existe), el `y` del notebook cambiaría de
largo entre celdas.
"""

import numpy as np
import pandas as pd

from src import modelo, validacion


def _copias(*series):
    return [s.copy(deep=True) for s in series]


def _sin_cambios(originales, actuales):
    for o, a in zip(originales, actuales):
        assert len(a) == len(o)
        assert a.index.equals(o.index)
        pd.testing.assert_series_equal(a, o)


def test_modelos_y_validacion_no_modifican_y(avisos_sinteticos):
    df, y = avisos_sinteticos
    df = df.copy()
    y = y.copy()
    unidad = modelo.grupo_de_unidad(df)
    copia_y, copia_unidad = _copias(y, unidad)
    copia_df = df.copy(deep=True)

    list(modelo.vueltas_sin_fuga(df, y, k=2))
    modelo.precio_esperado_sin_fuga(df, y, modelo.matriz_caracteristicas(df), k=2)
    pred, vuelta, ajustes = validacion.comparar_modelos(df, y, k=2, modelos=["mediana_zona", "lineal_ampliado", "gbm"],
                                                        devolver_modelos=True)
    validacion.metricas(y, pred)
    validacion.bootstrap_diferencia_error(y, pred["gbm"], pred["lineal_ampliado"], unidad, b=10)
    residuo = y - pred["lineal_ampliado"]
    copia_residuo = residuo.copy()
    validacion.intervalos_conformes(residuo, df["barrio"], vuelta, minimo=10)
    marcados = pd.Series(np.arange(len(df)) < 20, index=df.index)
    validacion.explicar_lineal(ajustes, marcados)
    validacion.explicar_gbm(ajustes, marcados, n_fondo=10, max_evals=60)

    _sin_cambios([copia_y, copia_unidad, copia_residuo], [y, unidad, residuo])
    pd.testing.assert_frame_equal(df, copia_df)


def test_bootstrap_primas_no_modifica_sus_entradas(avisos_sinteticos):
    df, y = avisos_sinteticos
    y = y.copy()
    unidad = modelo.grupo_de_unidad(df)
    zona = df["barrio"]
    A = modelo.matriz_diseno(modelo.matriz_caracteristicas(df), zona)
    usar = pd.Series(True, index=df.index)
    copias = _copias(y, unidad, usar)
    validacion.bootstrap_primas(y, A, usar, unidad, ["log_m2", "cochera"], b=10)
    _sin_cambios(copias, [y, unidad, usar])
