"""
Regla de decisión (PreEntrega 3): de "señal a investigar" a "candidato después de costos".

La lista oficial (avisos que cumplen la regla R1) son señales a investigar. Un
aviso pasa a "candidato después de costos" si, además, comprarlo, refaccionarlo
según su estado y venderlo deja un margen mínimo (`umbral_brecha_neta`) con los
costos de config/costos.yaml, y no tiene una señal de riesgo legal de descarte.
Nunca es una "oportunidad confirmada": todo depende del precio esperado, que
tiene error, y de supuestos de costos.

Brecha neta = (venta neta − impuesto − costo total) / costo total, con:
  costo total  = precio publicado × (1 + costos de entrada) + refacción
                 (se compra al precio publicado: un aviso ya barato deja poco
                 margen para negociar, supuesto conservador);
  venta neta   = valor de salida × (1 − negociación) × (1 − costos de salida)
                 (se vende a precio de cierre, no al publicado);
  valor de salida = valor esperado del modelo; si el aviso se refacciona (nivel
                 medio o integral), sin la prima negativa de su estado ("a
                 reciclar", "a refaccionar"): se compra en mal estado y se vende
                 refaccionado.
"""

import numpy as np
import pandas as pd

CAMPO_ESCENARIO = {"base": "valor", "optimista": "minimo", "pesimista": "maximo"}
NIVELES_QUE_QUITAN_LA_PRIMA = ("media", "integral")
SENAL = "señal a investigar"
CANDIDATO = "candidato después de costos"


def parametros(costos, escenario="base"):
    """Parámetros numéricos de costos.yaml para un escenario.

    "base" usa el valor central de cada costo, "optimista" el mínimo y
    "pesimista" el máximo. En el pesimista el comprador paga todo el impuesto
    de Sellos de la compra (máximo de costos.yaml).
    """
    campo = CAMPO_ESCENARIO[escenario]
    entrada, salida, refaccion = costos["costos_entrada"], costos["costos_salida"], costos["refaccion"]
    sellos = entrada["impuesto_sellos"]
    return {
        "escribano": entrada["honorarios_escribano"][campo] / 100,
        "escribano_minimo_usd": entrada["honorarios_escribano"]["minimo_absoluto_usd"],
        "sellos_hasta_umbral": sellos["alicuota_total_hasta_umbral"] / 100,
        "sellos_sobre_umbral": sellos["alicuota_total_sobre_umbral"] / 100,
        "sellos_umbral_usd": sellos["umbral_usd"],
        "sellos_comprador": 1.0 if escenario == "pesimista" else sellos["proporcion_comprador"],
        "comision_comprador": entrada["comision_inmobiliaria_comprador"][campo] / 100,
        "otros_entrada": entrada["otros_gastos_escritura"][campo] / 100,
        "negociacion": costos["negociacion"]["brecha_publicado_cierre"][campo] / 100,
        "comision_vendedor": salida["comision_inmobiliaria_vendedor"][campo] / 100,
        "sellos_vendedor": salida["impuesto_sellos_vendedor"]["proporcion_vendedor"],
        "certificados": salida["certificados_y_estudio_de_titulos"][campo] / 100,
        "ganancias": salida["impuesto_ganancias"]["valor"] / 100,
        "liviana_m2": refaccion["liviana"][campo],
        "bano_cocina_usd": refaccion["media"]["costo_bano_cocina_usd"],
        "integral_m2": refaccion["integral"][campo],
    }


def nivel_de_refaccion(estado, costos, variante="central"):
    """Nivel de refacción de cada aviso según su estado del título (costos.yaml, estado_refaccion).
    `variante`: "central" (nivel), "baja" o "alta" (los extremos de nivel_sensibilidad)."""
    columna = {"central": None, "baja": 0, "alta": 1}[variante]
    mapa = {e["estado"]: e["nivel"] if columna is None else e["nivel_sensibilidad"][columna]
            for e in costos["estado_refaccion"]}
    return estado.map(mapa).fillna(mapa["sin_marca"])


def _sellos(precio, p, proporcion):
    alicuota = np.where(precio <= p["sellos_umbral_usd"], p["sellos_hasta_umbral"], p["sellos_sobre_umbral"])
    return alicuota * proporcion * precio


def costo_entrada(precio, p):
    """Escribano (con su mínimo en USD), mitad de Sellos según el umbral, comisión y otros gastos."""
    escribano = np.maximum(p["escribano"] * precio, p["escribano_minimo_usd"])
    return (escribano + _sellos(precio, p, p["sellos_comprador"])
            + (p["comision_comprador"] + p["otros_entrada"]) * precio)


def costo_refaccion(nivel, m2, p):
    """USD de refacción: liviana por m²; media = baño y cocina (fijo) + liviana por m²; integral por m²."""
    return pd.Series(np.select(
        [nivel == "liviana", nivel == "media", nivel == "integral"],
        [p["liviana_m2"] * m2, p["bano_cocina_usd"] + p["liviana_m2"] * m2, p["integral_m2"] * m2],
        default=0.0), index=m2.index)


def costo_salida(venta, p):
    """Comisión del vendedor, su parte de Sellos según el umbral y certificados."""
    return (p["comision_vendedor"] + p["certificados"]) * venta + _sellos(venta, p, p["sellos_vendedor"])


def calcular(df, primas_estado, costos, escenario="base", refaccion="central", valor_salida="esperado",
             ganancias=None):
    """Brecha neta de cada aviso y sus componentes en USD.

    `df`: precio_usd, m2_final, precio_m2_esperado, precio_m2_esperado_inf y estado_titulo.
    `primas_estado`: {estado: coeficiente en log del modelo lineal} (ver `primas_estado`).
    `valor_salida`: "esperado" o "limite_inferior" (el límite inferior del
    intervalo del 80%, escenario conservador).
    `ganancias`: alícuota del impuesto a las ganancias (0 a 1); None usa costos.yaml.
    """
    p = parametros(costos, escenario)
    if ganancias is not None:
        p["ganancias"] = ganancias
    precio, m2 = df["precio_usd"], df["m2_final"]
    nivel = nivel_de_refaccion(df["estado_titulo"], costos, refaccion)
    columna = {"esperado": "precio_m2_esperado", "limite_inferior": "precio_m2_esperado_inf"}[valor_salida]
    prima = df["estado_titulo"].map(primas_estado).fillna(0).clip(upper=0)
    quita_prima = nivel.isin(NIVELES_QUE_QUITAN_LA_PRIMA)
    valor = df[columna] * m2 * np.exp(np.where(quita_prima, -prima, 0.0))
    venta = valor * (1 - p["negociacion"])
    salida = costo_salida(venta, p)
    entrada = costo_entrada(precio, p)
    obra = costo_refaccion(nivel, m2, p)
    costo_total = precio + entrada + obra
    ganancia = venta - salida - costo_total
    impuesto = p["ganancias"] * ganancia.clip(lower=0)
    return pd.DataFrame({
        "nivel_refaccion": nivel, "costo_entrada_usd": entrada, "refaccion_usd": obra, "costo_total_usd": costo_total,
        "valor_salida_usd": valor, "venta_cierre_usd": venta, "costo_salida_usd": salida, "impuesto_usd": impuesto,
        "resultado_usd": ganancia - impuesto, "brecha_neta": (ganancia - impuesto) / costo_total,
    }, index=df.index)


def senales_legales(df, costos):
    """Señales de riesgo legal del título según su acción en costos.yaml: (descartar, revisar), en texto."""
    def juntar(accion):
        columnas = [f"riesgo_{r['senal']}" for r in costos["riesgo_legal"]
                    if r["accion"] == accion and f"riesgo_{r['senal']}" in df.columns]
        marcas = df[columnas].fillna(False).astype(bool)
        return marcas.apply(lambda fila: ", ".join(c.replace("riesgo_", "").replace("_", " ")
                                                   for c in columnas if fila[c]), axis=1)
    return juntar("descartar"), juntar("revisar")


def decidir(cumple_regla, brecha_neta, descartar, umbral=0.10):
    """Nivel de cada aviso ("señal a investigar", "candidato después de costos" o vacío) y el motivo
    por el que una señal no llega a candidato."""
    candidato = cumple_regla & (brecha_neta >= umbral) & (descartar == "")
    nivel = np.where(candidato, CANDIDATO, np.where(cumple_regla, SENAL, ""))
    motivo = np.where(~cumple_regla | candidato, "",
                      np.where(descartar != "", "riesgo legal: " + descartar,
                               "brecha neta " + (100 * brecha_neta).round(0).astype(int).astype(str)
                               + f"% < {100 * umbral:.0f}%"))
    return pd.Series(candidato, index=brecha_neta.index), pd.Series(nivel, index=brecha_neta.index), \
        pd.Series(motivo, index=brecha_neta.index)


def primas_estado(ajustes):
    """Prima (log) de cada estado del título en el lineal ampliado, promedio de las vueltas."""
    coefs = pd.DataFrame([aj["coef_lineal_ampliado"] for aj in ajustes.values()])
    estados = [c for c in coefs.columns if c.startswith("titulo_a_") or c.startswith("titulo_ya_")]
    return {c.replace("titulo_", ""): float(coefs[c].mean()) for c in estados}


def tasa_salida_por_ambientes(df, seguimiento):
    """Tasa de salida del portal entre relevamientos por ambientes (sin barrios truncados), para cada aviso.
    Liquidez informativa: el notebook 06 mostró que las ambientes alcanzan."""
    grupo = df["ambientes"].fillna(df["dormitorios"] + 1).clip(1, 5).astype(int)
    validos = ~seguimiento["barrio_truncado"].astype(bool).values
    tasas = pd.Series(seguimiento["salio"].astype(float).values[validos]).groupby(grupo.values[validos]).mean()
    return grupo.map(tasas)
