"""
ETAPA 1 - Scraping de MercadoLibre Inmuebles.

Extrae departamentos usados en venta de los 47 barrios de CABA. De cada
aviso toma los datos del listado y, si con_detalle está activo, entra a la
ficha para extraer la tabla completa de características (amenities).

SALIDA:  data/raw/cuotas/<cuota>.tsv
PARCIAL: data/raw/cuotas/<cuota>_parcial.tsv  (se borra al terminar bien)

Los emprendimientos NO se descartan: se marcan con la columna
es_emprendimiento (el precio decía "Desde") y se decide en el análisis.

ATENCIÓN: con con_detalle activo cada aviso cuesta un request extra. Las
cinco cuotas completas son entre 8 y 15 horas. Por eso el trabajo se
reparte en cuotas de barrios que se corren en sesiones separadas, y por eso
las cuotas ya descargadas vienen versionadas en el repositorio.

El scraping debe correrse desde una IP residencial. Desde Colab u otro
entorno con IP de datacenter se dispara el bloqueo anti-bot.

Arreglo respecto de la versión original: el archivo parcial se escribe y se
borra con el MISMO nombre (<cuota>_parcial.tsv). Antes se escribía como
"cuota_actual_parcial.tsv" y se intentaba borrar "<cuota>_parcial.tsv", así
que el parcial nunca se limpiaba y quedaba basura en disco.
"""

import argparse
import os
import random
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.configuracion import agregar_argumento_config, cargar_config, elegir
from src.entorno import verificar_python
from src.qc import ControlCalidad
from src.rutas import asegurar_directorio, resolver, ruta_relativa

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

session = requests.Session()


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Etapa 1: scrapea una cuota de barrios de MercadoLibre Inmuebles.",
        epilog="Ejemplo: python3 src/scrapper_mercadolibre.py --cuota cuota3",
    )
    agregar_argumento_config(parser)
    parser.add_argument("--cuota", default=None, help="Nombre de la cuota definida en config/config.yaml.")
    parser.add_argument("--barrios", nargs="+", default=None, help="Lista explícita de barrios (pisa --cuota).")
    parser.add_argument("--salida-dir", default=None, help="Directorio donde se escribe el TSV de la cuota.")
    parser.add_argument("--logs-dir", default=None, help="Directorio de logs de control de calidad.")
    parser.add_argument("--max-paginas", type=int, default=None, help="Tope de páginas por barrio.")
    parser.add_argument("--sin-detalle", action="store_true", help="No entrar a la ficha de cada aviso (mucho más rápido).")
    parser.add_argument("--timeout", type=int, default=None, help="Timeout por request, en segundos.")
    parser.add_argument("--guardar-cada", type=int, default=None, help="Cada cuántos avisos se escribe el parcial.")
    parser.add_argument("--delay-pagina", nargs=2, type=float, default=None, metavar=("MIN", "MAX"),
                        help="Rango de pausa entre páginas de listado.")
    parser.add_argument("--delay-detalle", nargs=2, type=float, default=None, metavar=("MIN", "MAX"),
                        help="Rango de pausa entre fichas de detalle.")
    parser.add_argument("--delay-barrio", nargs=2, type=float, default=None, metavar=("MIN", "MAX"),
                        help="Rango de pausa al cambiar de barrio.")
    return parser


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",  # sin br (Brotli) para evitar problemas de decodificación
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def clean_text(text):
    if not text:
        return "N/A"
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_precio(price_text):
    """
    Separa moneda, monto y si es "desde" (emprendimiento).
    Ejemplos: "US$ 159.000", "Desde US$ 826.800", "$ 45.000.000"
    Devuelve (moneda, monto_numerico, es_desde).
    """
    if not price_text or price_text == "N/A":
        return "N/A", None, False

    texto = price_text.strip()

    es_desde = "desde" in texto.lower()

    if "US$" in texto or "u$s" in texto.lower():
        moneda = "USD"
    elif "$" in texto:
        moneda = "ARS"
    else:
        moneda = "N/A"

    solo_numero = re.sub(r"[^\d.]", "", texto)
    solo_numero = solo_numero.replace(".", "")
    monto = None
    if solo_numero:
        try:
            monto = int(solo_numero)
        except ValueError:
            monto = None

    return moneda, monto, es_desde


def parse_atributos(attrs_text):
    """
    Extrae ambientes, dormitorios, baños y m² del texto.
    Los emprendimientos suelen traer RANGOS ("3 a 4 baños", "139 - 166 m²");
    en esos casos se toma el primer número del rango.
    """
    resultado = {"ambientes": None, "dormitorios": None, "banos": None, "m2": None}
    if not attrs_text or attrs_text == "N/A":
        return resultado

    texto = attrs_text.lower()

    m = re.search(r"(\d+)\s*amb", texto)
    if m:
        resultado["ambientes"] = int(m.group(1))

    m = re.search(r"(\d+)\s*dormitorio", texto)
    if m:
        resultado["dormitorios"] = int(m.group(1))

    m = re.search(r"(\d+)(?:\s*a\s*\d+)?\s*ba[ñn]o", texto)
    if m:
        resultado["banos"] = int(m.group(1))

    m = re.search(r"(\d+)(?:\s*-\s*\d+)?\s*m²", texto)
    if m:
        resultado["m2"] = int(m.group(1))

    return resultado


def extraer_propiedad(item):
    """Extrae los datos de una card del listado. Devuelve dict o None."""
    title_tag = item.find("a", class_="poly-component__title")
    if not title_tag:
        return None
    link = title_tag.get("href", "N/A")
    titulo = clean_text(title_tag.text)

    headline_tag = item.find("span", class_="poly-component__headline")
    headline = clean_text(headline_tag.text) if headline_tag else "N/A"

    price_tag = item.find("div", class_="poly-component__price")
    price_text = clean_text(price_tag.text) if price_tag else "N/A"
    moneda, precio, es_desde = parse_precio(price_text)

    attrs_tag = item.find("div", class_="poly-component__attributes-list")
    attrs_text = clean_text(attrs_tag.text) if attrs_tag else "N/A"
    atributos = parse_atributos(attrs_text)

    location_tag = item.find("span", class_="poly-component__location")
    ubicacion = clean_text(location_tag.text) if location_tag else "N/A"

    return {
        "tipo": headline,
        "titulo": titulo,
        "precio": precio,
        "moneda": moneda,
        "precio_texto": price_text,
        "es_emprendimiento": es_desde,
        "ambientes": atributos["ambientes"],
        "dormitorios": atributos["dormitorios"],
        "banos": atributos["banos"],
        "m2": atributos["m2"],
        "atributos_texto": attrs_text,
        "ubicacion": ubicacion,
        "link": link,
    }


def normalizar_nombre_columna(nombre):
    """
    Convierte el nombre de una característica en nombre de columna limpio.
    Ej: "Superficie total" -> "superficie_total"
    """
    nombre = nombre.lower().strip()
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for viejo, nuevo in reemplazos.items():
        nombre = nombre.replace(viejo, nuevo)
    nombre = re.sub(r"[^a-z0-9]+", "_", nombre)
    nombre = nombre.strip("_")
    return nombre


def parsear_caracteristicas(html):
    """
    Extrae la tabla de características de una ficha de detalle ya descargada.
    Separado de la descarga para poder testearlo contra HTML guardado.
    """
    soup = BeautifulSoup(html, "html.parser")
    caracteristicas = {}

    for fila in soup.find_all("tr", class_="andes-table__row"):
        th = fila.find("th")
        if not th:
            continue
        nombre_div = th.find("div", class_="andes-table__header__container")
        nombre = clean_text(nombre_div.text) if nombre_div else clean_text(th.text)

        valor_span = fila.find("span", class_="andes-table__column--value")
        valor = clean_text(valor_span.text) if valor_span else None

        if nombre and valor:
            caracteristicas[normalizar_nombre_columna(nombre)] = valor

    return caracteristicas


def extraer_caracteristicas_detalle(url, timeout=15):
    """Descarga la ficha de una propiedad y devuelve sus características."""
    try:
        r = session.get(url, headers=get_headers(), timeout=timeout)
        if r.status_code != 200:
            return {}
        return parsear_caracteristicas(r.text)
    except Exception:
        return {}


def construir_url(barrio, pagina, avisos_por_pagina=48):
    """Arma la URL de un barrio y página específica."""
    prefijo = (
        "https://inmuebles.mercadolibre.com.ar/departamentos/venta/"
        f"propiedades-individuales/capital-federal/{barrio}/"
        f"departamentos-en-venta-{barrio}-usados"
    )
    sufijo = "_ITEM*CONDITION_2230581_NoIndex_True?sb=all_mercadolibre"
    if pagina == 1:
        return prefijo + sufijo
    offset = (pagina - 1) * avisos_por_pagina + 1
    return f"{prefijo}_Desde_{offset}{sufijo}"


def scrapear_barrio(barrio, seen_links, all_data, ruta_parcial, cfg):
    """Scrapea todas las páginas de un barrio. Devuelve cuántas sumó."""
    nuevas_barrio = 0

    for pag in range(1, cfg["max_paginas_por_barrio"] + 1):
        url = construir_url(barrio, pag, cfg["avisos_por_pagina"])

        try:
            r = session.get(url, headers=get_headers(), timeout=cfg["timeout"])
            if r.status_code != 200:
                time.sleep(cfg["espera_reintento"])
                r = session.get(url, headers=get_headers(), timeout=cfg["timeout"])
                if r.status_code != 200:
                    break

            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.find_all("li", class_="ui-search-layout__item")
            if not items:
                break

            nuevas_pagina = 0
            for item in items:
                try:
                    datos = extraer_propiedad(item)
                    if datos is None:
                        continue
                    if datos["link"] in seen_links:
                        continue
                    seen_links.add(datos["link"])
                    datos["barrio"] = barrio

                    if cfg["con_detalle"]:
                        datos.update(extraer_caracteristicas_detalle(datos["link"], cfg["timeout"]))
                        time.sleep(random.uniform(*cfg["delay_detalle"]))

                    all_data.append(datos)
                    nuevas_barrio += 1
                    nuevas_pagina += 1

                except Exception:
                    continue

            if nuevas_pagina == 0:
                break

            # Guardado parcial cada ~guardar_cada propiedades
            if len(all_data) % cfg["guardar_cada"] < cfg["avisos_por_pagina"] and len(all_data) > 0:
                pd.DataFrame(all_data).to_csv(ruta_parcial, sep="\t", index=False, encoding="utf-8-sig")

            time.sleep(random.uniform(*cfg["delay_pagina"]))

        except Exception:
            continue

    return nuevas_barrio


def run_scrapper(nombre_cuota, barrios, salida_dir, logs_dir, cfg, columnas_clave) -> int:
    salida_dir = resolver(salida_dir)
    salida_dir.mkdir(parents=True, exist_ok=True)
    destino = salida_dir / f"{nombre_cuota}.tsv"
    ruta_parcial = salida_dir / f"{nombre_cuota}_parcial.tsv"

    modo = "CON AMENITIES" if cfg["con_detalle"] else "SIN AMENITIES"
    print(f"=== ETAPA 1: SCRAPING {nombre_cuota.upper()} ({modo}) ===")
    print(f"Barrios a procesar: {len(barrios)}")
    print(f"Máx. páginas por barrio: {cfg['max_paginas_por_barrio']}")
    print(f"Salida: {destino}")
    if cfg["con_detalle"]:
        print("[!] Modo detalle ACTIVADO: entra a cada aviso. Va a tardar MUCHO.")
    print()

    all_data = []
    seen_links = set()

    for i, barrio in enumerate(barrios, 1):
        print(f"[{i}/{len(barrios)}] Barrio: {barrio}")
        nuevas = scrapear_barrio(barrio, seen_links, all_data, ruta_parcial, cfg)
        print(f"    -> {nuevas} propiedades. Total acumulado: {len(all_data)}")
        time.sleep(random.uniform(*cfg["delay_barrio"]))

    if not all_data:
        print("\n[!] No se obtuvieron datos.")
        print("    Revisá la conexión y que la IP sea residencial (ver docs/proceso_tecnico.md).")
        return 1

    df = pd.DataFrame(all_data)
    df.to_csv(destino, sep="\t", index=False, encoding="utf-8-sig")

    if ruta_parcial.exists():
        ruta_parcial.unlink()

    print(f"\n¡ÉXITO! {len(df)} propiedades extraídas. Archivo: {destino}")

    qc = ControlCalidad(f"01_scraping_{nombre_cuota}", logs_dir)
    qc.metrica("cuota", nombre_cuota)
    qc.metrica("barrios_solicitados", len(barrios))
    qc.metrica("barrios_con_datos", int(df["barrio"].nunique()))
    qc.metrica("filas_entrada", 0)  # la entrada es la web, no un archivo
    qc.metrica("filas_salida", len(df))
    qc.metrica("columnas_salida", len(df.columns))
    qc.metrica("con_detalle", bool(cfg["con_detalle"]))
    qc.duplicados(df, ["link"], "duplicados_residuales")
    qc.metrica("emprendimientos", int(df["es_emprendimiento"].sum()))
    qc.nulos_por_columna(df, columnas_clave)
    qc.desglose("propiedades_por_barrio", df["barrio"].value_counts().to_dict())
    qc.metrica("archivo_salida", ruta_relativa(destino))
    qc.cerrar()

    barrios_vacios = sorted(set(barrios) - set(df["barrio"].unique()))
    if barrios_vacios:
        print(f"[!] Barrios sin datos: {', '.join(barrios_vacios)}")
    return 0


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    verificar_python(avisar=False)
    cfg_completa = cargar_config(args.config)
    cuotas = cfg_completa["scraping"]["cuotas"]

    if args.barrios:
        barrios = args.barrios
        nombre_cuota = args.cuota or "cuota_custom"
    else:
        nombre_cuota = args.cuota
        if nombre_cuota is None:
            print("[!] Especificá --cuota o --barrios.")
            print(f"    Cuotas disponibles: {', '.join(cuotas)}")
            return 2
        if nombre_cuota not in cuotas:
            print(f"[!] La cuota '{nombre_cuota}' no está en config/config.yaml.")
            print(f"    Cuotas disponibles: {', '.join(cuotas)}")
            return 2
        barrios = cuotas[nombre_cuota]

    cfg = dict(cfg_completa["scraping"])
    cfg["max_paginas_por_barrio"] = elegir(args.max_paginas, cfg["max_paginas_por_barrio"])
    cfg["con_detalle"] = False if args.sin_detalle else cfg["con_detalle"]
    cfg["timeout"] = elegir(args.timeout, cfg["timeout"])
    cfg["guardar_cada"] = elegir(args.guardar_cada, cfg["guardar_cada"])
    cfg["delay_pagina"] = elegir(args.delay_pagina, cfg["delay_pagina"])
    cfg["delay_detalle"] = elegir(args.delay_detalle, cfg["delay_detalle"])
    cfg["delay_barrio"] = elegir(args.delay_barrio, cfg["delay_barrio"])

    return run_scrapper(
        nombre_cuota=nombre_cuota,
        barrios=barrios,
        salida_dir=elegir(args.salida_dir, cfg_completa["rutas"]["cuotas_dir"]),
        logs_dir=elegir(args.logs_dir, cfg_completa["rutas"]["logs_dir"]),
        cfg=cfg,
        columnas_clave=cfg_completa["qc"]["columnas_clave"],
    )


if __name__ == "__main__":
    raise SystemExit(main())
