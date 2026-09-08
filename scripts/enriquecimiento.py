
# =============================================================================
# ENRIQUECIMIENTO DEL DATASET - Etapas 2, 3 y 4
# =============================================================================
# Toma el dataset geocodificado y le agrega:
#   ETAPA 2: descarga capas de transporte de BA Data (subte, y opcionalmente
#            tren/metrobus si se agregan las URLs)
#   ETAPA 3: calcula distancia a la estación de transporte más cercana
#            y distancia a la centralidad (Obelisco / polo de oficinas)
#   ETAPA 4: define sub-zonas dentro de cada barrio por clustering geográfico
#
# ENTRADA: output/propiedades_geocodificadas.tsv
# SALIDA:  output/propiedades_enriquecidas.tsv
#
# Las propiedades sin coordenadas (geo_status != OK) se conservan, pero con
# las columnas nuevas vacías (no se puede calcular distancia sin coordenadas).
# =============================================================================

import pandas as pd
import numpy as np
import requests
import json
import os
from sklearn.cluster import KMeans

# --- Configuración ---
ARCHIVO_ENTRADA = "/Users/gonzalobuhler/Documents/Facultad (ITBA)/2026 - 2C/Descriptiva/propiedades_geocodificadas.tsv"
ARCHIVO_SALIDA = "output/propiedades_enriquecidas.tsv"

# URL oficial de BA Data con las estaciones de subte (GeoJSON)
URL_SUBTE = "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/sbase/subte-estaciones/estaciones-de-subte.geojson"

# Puntos de centralidad de CABA (coordenadas fijas conocidas)
OBELISCO = (-34.6037, -58.3816)          # centro simbólico / microcentro
PUERTO_MADERO = (-34.6083, -58.3625)     # polo de oficinas moderno
CATALINAS = (-34.5950, -58.3720)         # polo corporativo tradicional

# Cantidad de sub-zonas por barrio (aproximada; se ajusta según tamaño del barrio)
SUBZONAS_POR_BARRIO = 5
MIN_PROPIEDADES_SUBZONA = 30  # si una sub-zona tiene menos, se puede reagrupar


def haversine_np(lat1, lon1, lat2, lon2):
    """Distancia en metros entre puntos (fórmula de Haversine, vectorizada)."""
    R = 6371000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))


def descargar_estaciones_subte():
    """
    ETAPA 2: descarga las estaciones de subte de BA Data.
    Devuelve un array de (lat, lon) de cada estación.
    """
    print("ETAPA 2: Descargando estaciones de subte de BA Data...")
    try:
        r = requests.get(URL_SUBTE, timeout=30)
        r.raise_for_status()
        data = r.json()

        estaciones = []
        for feature in data.get("features", []):
            geom = feature.get("geometry", {})
            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]  # GeoJSON: [lon, lat]
                    estaciones.append((lat, lon))

        print(f"  {len(estaciones)} estaciones de subte descargadas.")
        return np.array(estaciones)

    except Exception as e:
        print(f"  [!] Error al descargar subte: {e}")
        print(f"  [!] Verificá tu conexión o la URL. Continuando sin transporte...")
        return None


def calcular_distancia_transporte(lat, lon, estaciones):
    """
    ETAPA 3a: para cada propiedad, distancia a la estación más cercana.
    """
    if estaciones is None or len(estaciones) == 0:
        return np.full(len(lat), np.nan)

    # Para cada propiedad, calcular distancia a TODAS las estaciones y quedarse con la mínima
    dist_min = np.full(len(lat), np.inf)
    for est_lat, est_lon in estaciones:
        d = haversine_np(lat, lon, est_lat, est_lon)
        dist_min = np.minimum(dist_min, d)
    return dist_min


def calcular_distancia_centralidad(lat, lon):
    """
    ETAPA 3b: distancia a la centralidad (mínima entre Obelisco, Puerto Madero, Catalinas).
    """
    d_obelisco = haversine_np(lat, lon, OBELISCO[0], OBELISCO[1])
    d_madero = haversine_np(lat, lon, PUERTO_MADERO[0], PUERTO_MADERO[1])
    d_catalinas = haversine_np(lat, lon, CATALINAS[0], CATALINAS[1])
    # La centralidad es la distancia al polo más cercano
    return np.minimum(np.minimum(d_obelisco, d_madero), d_catalinas)


def asignar_subzonas(df_ok):
    """
    ETAPA 4: dentro de cada barrio, agrupa las propiedades en sub-zonas por
    clustering geográfico (KMeans sobre lat/lon).
    Devuelve una Serie con el id de sub-zona (formato "barrio_N").
    """
    print("ETAPA 4: Definiendo sub-zonas por clustering...")
    subzonas = pd.Series(index=df_ok.index, dtype='object')

    for barrio in df_ok['barrio'].unique():
        mask = df_ok['barrio'] == barrio
        sub = df_ok[mask]
        n = len(sub)

        if n < MIN_PROPIEDADES_SUBZONA:
            # Barrio muy chico: toda una sola sub-zona (= el barrio)
            subzonas[mask] = f"{barrio}_0"
            continue

        # Cantidad de clusters: no más que n/MIN, tope SUBZONAS_POR_BARRIO
        k = min(SUBZONAS_POR_BARRIO, max(1, n // MIN_PROPIEDADES_SUBZONA))

        coords = sub[['lat', 'lon']].astype(float).values
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(coords)
        subzonas[mask] = [f"{barrio}_{l}" for l in labels]

    print(f"  Sub-zonas creadas: {subzonas.nunique()} en total.")
    return subzonas


def main():
    print(f"Cargando {ARCHIVO_ENTRADA}...")
    df = pd.read_csv(ARCHIVO_ENTRADA, sep='\t', low_memory=False)
    print(f"  {len(df)} propiedades.")

    # Separar las que tienen coordenadas
    ok_mask = df['geo_status'] == 'OK'
    print(f"  Con coordenadas: {ok_mask.sum()}")

    # Inicializar columnas nuevas
    df['dist_transporte_m'] = np.nan
    df['dist_centralidad_m'] = np.nan
    df['subzona'] = None

    # Trabajar solo con las que tienen coordenadas
    df_ok = df[ok_mask].copy()
    df_ok['lat'] = pd.to_numeric(df_ok['lat'], errors='coerce')
    df_ok['lon'] = pd.to_numeric(df_ok['lon'], errors='coerce')
    df_ok = df_ok.dropna(subset=['lat', 'lon'])

    lat = df_ok['lat'].values
    lon = df_ok['lon'].values

    # --- ETAPA 2: descargar estaciones ---
    estaciones = descargar_estaciones_subte()

    # --- ETAPA 3: calcular distancias ---
    print("ETAPA 3: Calculando distancias...")
    dist_transp = calcular_distancia_transporte(lat, lon, estaciones)
    dist_centr = calcular_distancia_centralidad(lat, lon)
    print(f"  Distancia media a transporte: {np.nanmean(dist_transp):.0f} m")
    print(f"  Distancia media a centralidad: {np.nanmean(dist_centr):.0f} m")

    # Asignar de vuelta al df_ok
    df_ok['dist_transporte_m'] = dist_transp.round(0)
    df_ok['dist_centralidad_m'] = dist_centr.round(0)

    # --- ETAPA 4: sub-zonas ---
    df_ok['subzona'] = asignar_subzonas(df_ok)

    # Volcar los resultados de df_ok al df original (por índice)
    df.loc[df_ok.index, 'dist_transporte_m'] = df_ok['dist_transporte_m']
    df.loc[df_ok.index, 'dist_centralidad_m'] = df_ok['dist_centralidad_m']
    df.loc[df_ok.index, 'subzona'] = df_ok['subzona']

    # Guardar
    os.makedirs("output", exist_ok=True)
    df.to_csv(ARCHIVO_SALIDA, sep='\t', index=False, encoding='utf-8-sig')

    # Reporte
    print(f"\n{'='*55}")
    print(f"¡ENRIQUECIMIENTO COMPLETO!")
    print(f"Archivo: {ARCHIVO_SALIDA}")
    print(f"{'='*55}")
    print(f"\n--- Resumen ---")
    print(f"Total propiedades: {len(df)}")
    print(f"Con distancias calculadas: {df['dist_transporte_m'].notna().sum()}")
    print(f"Sub-zonas totales: {df['subzona'].nunique()}")
    print(f"\nColumnas nuevas agregadas:")
    print(f"  - dist_transporte_m  (distancia a estación de subte más cercana)")
    print(f"  - dist_centralidad_m (distancia al polo de centralidad más cercano)")
    print(f"  - subzona            (sub-zona geográfica dentro del barrio)")

    # Verificación rápida
    print(f"\n--- Verificación: distancia a transporte por barrio ---")
    for b in ['san-nicolas', 'palermo', 'villa-lugano']:
        sub = df[(df['barrio']==b) & df['dist_transporte_m'].notna()]
        if len(sub) > 0:
            print(f"  {b:15s}: {sub['dist_transporte_m'].mean():.0f} m promedio a subte")


if __name__ == "__main__":
    main()
