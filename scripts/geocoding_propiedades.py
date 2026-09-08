
# =============================================================================
# GEOCODING DE PROPIEDADES - Etapa 1 del enriquecimiento
# =============================================================================
# Convierte las direcciones del dataset en coordenadas (lat/long) usando el
# normalizador oficial de USIG (Gobierno de la Ciudad de Buenos Aires).
#
# ENTRADA:  output/mercadolibre_CABA_completo.tsv
# SALIDA:   output/propiedades_geocodificadas.tsv (mismo dataset + lat/lon)
#
# El servicio USIG es gratuito y oficial de CABA. Convierte "calle altura"
# en coordenadas. Este script:
#   - Limpia las direcciones (abreviatura "Al", "Av.", etc.)
#   - Geocodifica cada una con reintentos
#   - Guarda parциales cada 500 (por si se corta, se retoma)
#   - Reporta la tasa de éxito al final
# =============================================================================

import pandas as pd
import requests
import time
import re
import os
import random

# --- Configuración ---
ARCHIVO_ENTRADA = "/Users/gonzalobuhler/Documents/Facultad (ITBA)/2026 - 2C/Descriptiva/mercadolibre_CABA_completo.tsv"
ARCHIVO_SALIDA = "output/propiedades_geocodificadas.tsv"
ARCHIVO_PARCIAL = "output/geocoding_parcial.tsv"
GUARDAR_CADA = 500
URL_USIG = "http://servicios.usig.buenosaires.gob.ar/normalizar/"


def limpiar_direccion(ubicacion):
    """
    Limpia una dirección de MercadoLibre para geocodificar con USIG.
    Devuelve la query lista, o None si no es geocodificable.
    """
    if pd.isna(ubicacion):
        return None

    # Tomar solo la primera parte (antes de la primera coma) = calle + altura
    parte = ubicacion.split(',')[0].strip()

    # Normalizar "Av." y "Av" a "Avenida" ANTES de tocar los puntos
    parte = re.sub(r'\bAv\.\s*', 'Avenida ', parte)
    parte = re.sub(r'\bAv\s+', 'Avenida ', parte)

    # Sacar texto después de un punto (ej: "Sinclair 3100. Entre...")
    if '. ' in parte:
        parte = parte.split('. ')[0].strip()

    # Reemplazar " Al " (abreviatura de "altura") por espacio
    parte = re.sub(r'\s+Al\s+', ' ', parte)

    # Limpiar espacios múltiples
    parte = re.sub(r'\s+', ' ', parte).strip()

    # ¿Geocodificable? Tiene altura (número) o es esquina (" Y ")
    tiene_altura = bool(re.search(r'\d', parte))
    es_esquina = ' Y ' in parte.upper()

    if not tiene_altura and not es_esquina:
        return None

    return parte


def geocode_usig(direccion_limpia, max_reintentos=3):
    """
    Geocodifica una dirección limpia usando USIG.
    Devuelve (lat, lon, status).
    """
    if not direccion_limpia:
        return None, None, "NO_GEOCODIFICABLE"

    query = f"{direccion_limpia}, caba"
    params = {"direccion": query, "geocodificar": "true"}

    for intento in range(max_reintentos):
        try:
            r = requests.get(URL_USIG, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                normalizadas = data.get("direccionesNormalizadas", [])
                if normalizadas:
                    coord = normalizadas[0].get("coordenadas", {})
                    lat = coord.get("y")
                    lon = coord.get("x")
                    if lat and lon:
                        return float(lat), float(lon), "OK"
                    else:
                        return None, None, "SIN_COORDENADAS"
                else:
                    return None, None, "SIN_RESULTADO"
            else:
                time.sleep(3)
        except requests.exceptions.Timeout:
            time.sleep(3)
        except requests.exceptions.ConnectionError:
            time.sleep(5)
        except Exception as e:
            return None, None, f"ERROR_{type(e).__name__}"

    return None, None, "FALLO_REINTENTOS"


def main():
    # Cargar el dataset
    print(f"Cargando {ARCHIVO_ENTRADA}...")
    df = pd.read_csv(ARCHIVO_ENTRADA, sep='\t', low_memory=False)
    print(f"  {len(df)} propiedades cargadas.")

    # Limpiar todas las direcciones primero
    print("\nLimpiando direcciones...")
    df['dir_limpia'] = df['ubicacion'].apply(limpiar_direccion)
    geocodificables = df['dir_limpia'].notna().sum()
    print(f"  Geocodificables: {geocodificables} ({100*geocodificables/len(df):.1f}%)")
    print(f"  No geocodificables (se marcarán sin coords): {len(df)-geocodificables}")

    # Retomar si hay un parcial previo
    inicio = 0
    if os.path.exists(ARCHIVO_PARCIAL):
        print(f"\n[!] Encontrado parcial previo: {ARCHIVO_PARCIAL}")
        df_parcial = pd.read_csv(ARCHIVO_PARCIAL, sep='\t', low_memory=False)
        # Contar cuántas ya tienen resultado de geocoding
        ya_hechas = df_parcial['geo_status'].notna().sum()
        print(f"    Ya procesadas: {ya_hechas}. Retomando desde ahí.")
        df = df_parcial
        inicio = ya_hechas
    else:
        # Inicializar columnas nuevas
        df['lat'] = None
        df['lon'] = None
        df['geo_status'] = None

    os.makedirs("output", exist_ok=True)

    print(f"\n=== GEOCODIFICANDO (desde {inicio}) ===")
    t_inicio = time.time()

    for i in range(inicio, len(df)):
        dir_limpia = df.at[i, 'dir_limpia']
        lat, lon, status = geocode_usig(dir_limpia)

        df.at[i, 'lat'] = lat
        df.at[i, 'lon'] = lon
        df.at[i, 'geo_status'] = status

        # Progreso cada 100
        if (i + 1) % 100 == 0:
            transcurrido = time.time() - t_inicio
            hechas = i + 1 - inicio
            vel = hechas / transcurrido if transcurrido > 0 else 0
            faltan = len(df) - (i + 1)
            eta_min = (faltan / vel / 60) if vel > 0 else 0
            ok = (df['geo_status'] == 'OK').sum()
            print(f"  [{i+1}/{len(df)}] OK: {ok} | vel: {vel:.1f}/s | ETA: {eta_min:.0f} min")

        # Guardado parcial
        if (i + 1) % GUARDAR_CADA == 0:
            df.to_csv(ARCHIVO_PARCIAL, sep='\t', index=False, encoding='utf-8-sig')

        # Pausa para no saturar el servicio (importante: es un servicio público gratuito)
        time.sleep(random.uniform(0.15, 0.35))

    # Guardar resultado final
    df.to_csv(ARCHIVO_SALIDA, sep='\t', index=False, encoding='utf-8-sig')
    if os.path.exists(ARCHIVO_PARCIAL):
        os.remove(ARCHIVO_PARCIAL)

    # Reporte final
    print(f"\n{'='*55}")
    print(f"¡GEOCODING COMPLETO!")
    print(f"Archivo: {ARCHIVO_SALIDA}")
    print(f"{'='*55}")
    print(f"\n--- Resumen ---")
    print(f"Total: {len(df)}")
    total_ok = (df['geo_status'] == 'OK').sum()
    print(f"Geocodificadas OK: {total_ok} ({100*total_ok/len(df):.1f}%)")
    print(f"\nDetalle de estados:")
    print(df['geo_status'].value_counts().to_string())


if __name__ == "__main__":
    main()
