"""Duplicados por ID de aviso: se conserva la fila cuyo barrio coincide con el polígono oficial."""

import pandas as pd

from src import limpiar, limpieza


def _avisos():
    return pd.DataFrame({
        "id_aviso": ["A", "A", "B", "B", "C", "D", "D"],
        "link": ["a1", "a2", "b1", "b2", "c1", "d1", "d2"],
        "barrio": ["floresta", "villa-santa-rita", "paternal", "villa-general-mitre", "boedo", "flores", "caballito"],
    }, index=[10, 11, 12, 13, 14, 15, 16])


def test_sin_informacion_conserva_la_primera_aparicion():
    df, eliminadas = limpieza.deduplicar_por_id(_avisos())
    assert list(df["link"]) == ["a1", "b1", "c1", "d1"]
    assert list(df.index) == [10, 12, 14, 15]               # orden original
    assert set(eliminadas["motivo"]) == {"duplicado_mismo_id"}


def test_conserva_la_fila_del_barrio_oficial():
    avisos = _avisos()
    # A: el segundo coincide con el polígono; B: ninguno (sin coordenadas); D: el primero coincide
    coincide = pd.Series([False, True, False, False, True, True, False], index=avisos.index)
    df, eliminadas = limpieza.deduplicar_por_id(avisos, coincide)
    assert list(df["link"]) == ["a2", "b1", "c1", "d1"]
    assert list(df.index) == [11, 12, 14, 15]
    motivos = eliminadas.set_index("link")["motivo"]
    assert motivos["a1"] == "duplicado_mismo_id_barrio_no_oficial"
    assert motivos["b2"] == "duplicado_mismo_id"
    assert motivos["d2"] == "duplicado_mismo_id_barrio_no_oficial"


def test_coincide_barrio_oficial_desde_accesibilidad():
    avisos = _avisos()
    accesibilidad = pd.DataFrame({"link": ["a2", "d1", "c1"], "barrio_coincide": [1.0, 1.0, 0.0]})
    coincide = limpiar.coincide_barrio_oficial(avisos, accesibilidad)
    assert list(coincide) == [False, True, False, False, False, True, False]
    assert list(coincide.index) == list(avisos.index)
    assert not limpiar.coincide_barrio_oficial(avisos, None).any()


def test_la_fila_conservada_queda_en_la_posicion_de_la_primera_aparicion():
    # A aparece primero (no oficial), después B, y después A otra vez (oficial): el A conservado es el segundo,
    # pero queda ANTES de B, en el lugar del primero, así el orden de las filas (y las vueltas) no cambia
    avisos = pd.DataFrame({"id_aviso": ["A", "B", "A"], "link": ["a1", "b1", "a2"],
                           "barrio": ["floresta", "boedo", "villa-santa-rita"]}, index=[10, 11, 12])
    coincide = pd.Series([False, True, True], index=avisos.index)
    df, eliminadas = limpieza.deduplicar_por_id(avisos, coincide)
    assert list(df["link"]) == ["a2", "b1"]
    assert list(df.index) == [12, 11]
    assert list(eliminadas["link"]) == ["a1"]
