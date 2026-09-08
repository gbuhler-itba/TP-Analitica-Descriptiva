
# =============================================================================
# SCRAPER MERCADOLIBRE INMUEBLES (v8 - POR CUOTAS + AMENITIES)
# Trabajo Práctico 1 - Analítica Descriptiva 2026C2
# =============================================================================
# Extrae datos del LISTADO de MercadoLibre (todos los datos están ahí).
#
# CAMBIO IMPORTANTE respecto a v1:
#   Ya NO se descartan los emprendimientos. Se marcan con una columna
#   "es_emprendimiento" (True/False) y se guarda todo. Así no se pierden
#   datos y en el análisis se decide qué usar.
#
# Estructura del listado (verificada agosto 2026):
#   <li class="ui-search-layout__item">          <- cada propiedad
#     <span class="poly-component__headline">    <- tipo
#     <a class="poly-component__title">          <- link + título
#     <div class="poly-component__price">        <- precio (a veces "Desde US$...")
#     <div class="poly-component__attributes-list"> <- ambientes, m², baños
#     <span class="poly-component__location">    <- ubicación
# =============================================================================

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os
import random

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

session = requests.Session()


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
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_precio(price_text):
    """
    Separa moneda, monto y si es 'desde' (emprendimiento).
    Ejemplos: 'US$ 159.000', 'Desde US$ 826.800', '$ 45.000.000'
    Devuelve (moneda, monto_numerico, es_desde).
    """
    if not price_text or price_text == "N/A":
        return "N/A", None, False

    texto = price_text.strip()

    # ¿Es un precio "desde"? (típico de emprendimientos)
    es_desde = "desde" in texto.lower()

    # Detectar moneda
    if "US$" in texto or "u$s" in texto.lower():
        moneda = "USD"
    elif "$" in texto:
        moneda = "ARS"
    else:
        moneda = "N/A"

    # Extraer el número (quitar los puntos de miles)
    # Primero quitamos la palabra "Desde" y símbolos, dejamos solo dígitos y puntos
    solo_numero = re.sub(r'[^\d.]', '', texto)
    solo_numero = solo_numero.replace('.', '')
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
    Ejemplos: '4 ambs.3 a 4 baños139 - 166 m² cubiertos', '2 ambientes', '45 m²'
    NOTA: los emprendimientos suelen tener RANGOS (ej: '3 a 4 baños', '139 - 166 m²').
          En esos casos tomamos el primer número del rango.
    """
    resultado = {
        "ambientes": None,
        "dormitorios": None,
        "banos": None,
        "m2": None,
    }
    if not attrs_text or attrs_text == "N/A":
        return resultado

    texto = attrs_text.lower()

    # Ambientes (puede ser "4 ambs" o "2 ambientes")
    m = re.search(r'(\d+)\s*amb', texto)
    if m:
        resultado["ambientes"] = int(m.group(1))

    # Dormitorios
    m = re.search(r'(\d+)\s*dormitorio', texto)
    if m:
        resultado["dormitorios"] = int(m.group(1))

    # Baños (tomamos el primer número, sirve para rangos tipo "3 a 4 baños")
    m = re.search(r'(\d+)(?:\s*a\s*\d+)?\s*ba[ñn]o', texto)
    if m:
        resultado["banos"] = int(m.group(1))

    # m² (tomamos el primer número, sirve para rangos tipo "139 - 166 m²")
    m = re.search(r'(\d+)(?:\s*-\s*\d+)?\s*m²', texto)
    if m:
        resultado["m2"] = int(m.group(1))

    return resultado


def extraer_propiedad(item):
    """
    Extrae los datos de una card. Devuelve un dict (o None si no hay link).
    Ya NO descarta emprendimientos: los marca con es_emprendimiento.
    """
    title_tag = item.find('a', class_='poly-component__title')
    if not title_tag:
        return None
    link = title_tag.get('href', 'N/A')
    titulo = clean_text(title_tag.text)

    headline_tag = item.find('span', class_='poly-component__headline')
    headline = clean_text(headline_tag.text) if headline_tag else "N/A"

    price_tag = item.find('div', class_='poly-component__price')
    price_text = clean_text(price_tag.text) if price_tag else "N/A"
    moneda, precio, es_desde = parse_precio(price_text)

    attrs_tag = item.find('div', class_='poly-component__attributes-list')
    attrs_text = clean_text(attrs_tag.text) if attrs_tag else "N/A"
    atributos = parse_atributos(attrs_text)

    location_tag = item.find('span', class_='poly-component__location')
    ubicacion = clean_text(location_tag.text) if location_tag else "N/A"

    return {
        "tipo": headline,
        "titulo": titulo,
        "precio": precio,
        "moneda": moneda,
        "precio_texto": price_text,
        "es_emprendimiento": es_desde,  # True si el precio decía "Desde"
        "ambientes": atributos["ambientes"],
        "dormitorios": atributos["dormitorios"],
        "banos": atributos["banos"],
        "m2": atributos["m2"],
        "atributos_texto": attrs_text,
        "ubicacion": ubicacion,
        "link": link,
    }





# =============================================================================
# EXTRACCIÓN DE CARACTERÍSTICAS DEL DETALLE
# =============================================================================
# Entra a la página de detalle de una propiedad y extrae la tabla completa
# de características (incluye amenities: pileta, gimnasio, cochera, etc.).
#
# Estructura de la tabla (verificada agosto 2026):
#   <tr class="andes-table__row">
#     <th> ... <div class="andes-table__header__container">NOMBRE</div> </th>
#     <td> ... <span class="andes-table__column--value">VALOR</span> </td>
#   </tr>
# =============================================================================

def normalizar_nombre_columna(nombre):
    """
    Convierte el nombre de una característica en un nombre de columna limpio.
    Ej: 'Superficie total' -> 'superficie_total'
        'Admite mascotas'  -> 'admite_mascotas'
    """
    nombre = nombre.lower().strip()
    # Reemplazar tildes
    reemplazos = {'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u', 'ñ':'n'}
    for viejo, nuevo in reemplazos.items():
        nombre = nombre.replace(viejo, nuevo)
    # Espacios y caracteres raros a guión bajo
    nombre = re.sub(r'[^a-z0-9]+', '_', nombre)
    nombre = nombre.strip('_')
    return nombre


def extraer_caracteristicas_detalle(url):
    """
    Entra al detalle de una propiedad y extrae TODAS las características
    de la tabla (specs + amenities).

    Devuelve un dict {nombre_columna: valor}, o dict vacío si falla.
    """
    try:
        r = session.get(url, headers=get_headers(), timeout=15)
        if r.status_code != 200:
            return {}

        soup = BeautifulSoup(r.text, 'html.parser')

        caracteristicas = {}

        # Buscar todas las filas de las tablas de especificaciones
        filas = soup.find_all('tr', class_='andes-table__row')

        for fila in filas:
            # Nombre de la característica (en el <th>)
            th = fila.find('th')
            if not th:
                continue
            nombre_div = th.find('div', class_='andes-table__header__container')
            nombre = clean_text(nombre_div.text) if nombre_div else clean_text(th.text)

            # Valor (en el <span class="andes-table__column--value">)
            valor_span = fila.find('span', class_='andes-table__column--value')
            valor = clean_text(valor_span.text) if valor_span else None

            if nombre and valor:
                col = normalizar_nombre_columna(nombre)
                caracteristicas[col] = valor

        return caracteristicas

    except Exception as e:
        return {}


# =============================================================================
# LISTA DE BARRIOS DE CABA
# =============================================================================
BARRIOS_CABA = [
    "palermo", "belgrano", "caballito", "recoleta", "villa-urquiza",
    "almagro", "nunez", "flores", "villa-crespo", "barrio-norte",
    "puerto-madero", "san-telmo", "colegiales", "villa-devoto", "balvanera",
    "villa-del-parque", "saavedra", "boedo", "monserrat", "constitucion",
    "san-nicolas", "retiro", "chacarita", "parque-patricios", "villa-pueyrredon",
    "coghlan", "floresta", "villa-luro", "mataderos", "liniers",
    "villa-general-mitre", "parque-chacabuco", "villa-ortuzar", "agronomia",
    "paternal", "villa-santa-rita", "monte-castro", "velez-sarsfield",
    "versalles", "villa-real", "villa-riachuelo", "villa-soldati",
    "villa-lugano", "nueva-pompeya", "barracas", "la-boca",
    "parque-avellaneda",
]


def construir_url(barrio, pagina):
    """Arma la URL de un barrio y página específica."""
    prefijo = f"https://inmuebles.mercadolibre.com.ar/departamentos/venta/propiedades-individuales/capital-federal/{barrio}/departamentos-en-venta-{barrio}-usados"
    sufijo = "_ITEM*CONDITION_2230581_NoIndex_True?sb=all_mercadolibre"
    if pagina == 1:
        return prefijo + sufijo
    else:
        offset = (pagina - 1) * 48 + 1
        return f"{prefijo}_Desde_{offset}{sufijo}"


def scrapear_barrio(barrio, max_paginas_por_barrio, seen_links, all_data, output_dir, con_detalle):
    """
    Scrapea todas las páginas de un barrio.
    Si con_detalle=True, entra a cada propiedad para sacar amenities.
    """
    nuevas_barrio = 0

    for pag in range(1, max_paginas_por_barrio + 1):
        url = construir_url(barrio, pag)

        try:
            r = session.get(url, headers=get_headers(), timeout=15)
            if r.status_code != 200:
                time.sleep(8)
                r = session.get(url, headers=get_headers(), timeout=15)
                if r.status_code != 200:
                    break

            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.find_all('li', class_='ui-search-layout__item')
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

                    # --- NUEVO: entrar al detalle para sacar amenities ---
                    if con_detalle:
                        caracteristicas = extraer_caracteristicas_detalle(datos["link"])
                        # Agregar cada característica como columna
                        datos.update(caracteristicas)
                        # Pausa extra porque hicimos un request más
                        time.sleep(random.uniform(1, 2))

                    all_data.append(datos)
                    nuevas_barrio += 1
                    nuevas_pagina += 1

                except Exception:
                    continue

            if nuevas_pagina == 0:
                break

            # Guardado parcial cada ~100 propiedades
            if len(all_data) % 100 < 48 and len(all_data) > 0:
                df_temp = pd.DataFrame(all_data)
                temp_path = os.path.join(output_dir, "cuota_actual_parcial.tsv")
                df_temp.to_csv(temp_path, sep='\t', index=False, encoding='utf-8-sig')

            time.sleep(random.uniform(1.5, 3))

        except Exception:
            continue

    return nuevas_barrio


def run_scrapper(nombre_cuota, max_paginas_por_barrio=42, barrios=None, con_detalle=True):
    """
    Scraper multi-barrio de MercadoLibre CON amenities del detalle.

    Parámetros:
        max_paginas_por_barrio: máximo de páginas por barrio (42 = tope, ~2000 props)
        barrios: lista de barrios (por defecto todos los de BARRIOS_CABA)
        con_detalle: si True, entra a cada propiedad para sacar amenities.
                     ¡OJO! Esto multiplica MUCHO el tiempo (un request extra por propiedad).

    ADVERTENCIA DE TIEMPO:
        Con con_detalle=True, cada propiedad requiere un request adicional.
        Para 20.000 propiedades, pueden ser 8-15 horas. Dejar corriendo de noche.
        El guardado parcial permite retomar si se corta.
    """
    if barrios is None:
        barrios = BARRIOS_CABA

    all_data = []
    seen_links = set()
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"=== SCRAPING MULTI-BARRIO {'CON AMENITIES' if con_detalle else 'SIN AMENITIES'} ===")
    print(f"Barrios a procesar: {len(barrios)}")
    print(f"Máx. páginas por barrio: {max_paginas_por_barrio}")
    if con_detalle:
        print(f"[!] Modo detalle ACTIVADO: entra a cada propiedad. Va a tardar MUCHO.")
    print()

    for i, barrio in enumerate(barrios, 1):
        print(f"[{i}/{len(barrios)}] Barrio: {barrio}")
        nuevas = scrapear_barrio(barrio, max_paginas_por_barrio, seen_links, all_data, output_dir, con_detalle)
        print(f"    -> {nuevas} propiedades. Total acumulado: {len(all_data)}")
        time.sleep(random.uniform(2, 4))

    if all_data:
        df = pd.DataFrame(all_data)
        # El archivo lleva el nombre de la cuota, así no se pisan entre sesiones
        filename = f"{nombre_cuota}.tsv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, sep='\t', index=False, encoding='utf-8-sig')

        parcial_path = os.path.join(output_dir, f"{nombre_cuota}_parcial.tsv")
        if os.path.exists(parcial_path):
            os.remove(parcial_path)

        print(f"\n{'='*50}")
        print(f"¡ÉXITO! {len(df)} propiedades extraídas en total.")
        print(f"Archivo: {filepath}")
        print(f"Columnas totales: {len(df.columns)}")
        print(f"{'='*50}")

        print(f"\n--- Resumen ---")
        print(f"Total: {len(df)}")
        print(f"\nColumnas capturadas:")
        print(", ".join(df.columns))
        print(f"\nPropiedades por barrio:")
        print(df['barrio'].value_counts().to_string())
    else:
        print("\nNo se obtuvieron datos.")


if __name__ == "__main__":
    # =========================================================================
    # SCRAPING POR CUOTAS
    # =========================================================================
    # Los 48 barrios están divididos en 5 cuotas de ~2-3 horas cada una.
    # Cada cuota agota sus barrios (max_paginas_por_barrio=42) con amenities.
    #
    # CÓMO USARLO:
    #   1. Descomentá SOLO la cuota que querés correr ahora.
    #   2. Corré el script. Genera un archivo (ej: cuota1.tsv).
    #   3. En la próxima sesión, comentá esa cuota y descomentá la siguiente.
    #   4. Al terminar las 5 cuotas, corré unir_cuotas.py para juntar todo.
    #
    # Cada cuota guarda su propio archivo, así que podés correrlas en días
    # distintos sin que se pisen.
    # =========================================================================

    # ----- CUOTA 1 (barrios grandes) -----
    # run_scrapper(
    #     nombre_cuota="cuota1",
    #     max_paginas_por_barrio=42,
    #     con_detalle=True,
    #     barrios=[
    #         "palermo", "belgrano", "caballito", "recoleta",
    #         "villa-urquiza", "almagro", "nunez", "flores",
    #     ]
    # )

    # ----- CUOTA 2 -----
    # run_scrapper(
    #     nombre_cuota="cuota2",
    #     max_paginas_por_barrio=42,
    #     con_detalle=True,
    #     barrios=[
    #         "villa-crespo", "barrio-norte", "puerto-madero", "san-telmo",
    #         "colegiales", "villa-devoto", "balvanera", "villa-del-parque",
    #         "saavedra", "boedo",
    #     ]
    # )

    # ----- CUOTA 3 -----
    # run_scrapper(
    #     nombre_cuota="cuota3",
    #     max_paginas_por_barrio=42,
    #     con_detalle=True,
    #     barrios=[
    #         "monserrat", "constitucion", "san-nicolas", "retiro",
    #         "chacarita", "parque-patricios", "villa-pueyrredon", "coghlan",
    #         "floresta", "villa-luro",
    #     ]
    # )

    # ----- CUOTA 4 -----
    # run_scrapper(
    #     nombre_cuota="cuota4",
    #     max_paginas_por_barrio=42,
    #     con_detalle=True,
    #     barrios=[
    #         "mataderos", "liniers", "villa-general-mitre", "parque-chacabuco",
    #         "villa-ortuzar", "agronomia", "paternal", "villa-santa-rita",
    #         "monte-castro", "velez-sarsfield",
    #     ]
    # )

    # ----- CUOTA 5 (barrios chicos, va rápido) -----
    run_scrapper(
        nombre_cuota="cuota5",
        max_paginas_por_barrio=42,
        con_detalle=True,
        barrios=[
            "versalles", "villa-real", "villa-riachuelo", "villa-soldati",
            "villa-lugano", "nueva-pompeya", "barracas", "la-boca",
            "parque-avellaneda",
        ]
    )
