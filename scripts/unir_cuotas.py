
# =============================================================================
# UNIR CUOTAS - Une todos los archivos de cuotas en un solo dataset final
# =============================================================================
# Correr esto DESPUÉS de haber completado las 5 cuotas.
# Busca todos los archivos cuota1.tsv ... cuota5.tsv en la carpeta output/
# y los combina en un único archivo: mercadolibre_CABA_completo.tsv
# =============================================================================

import pandas as pd
import os
import glob

output_dir = "output"

# Buscar todos los archivos de cuotas
archivos_cuota = sorted(glob.glob(os.path.join(output_dir, "cuota*.tsv")))
# Filtrar los parciales (por si quedó alguno)
archivos_cuota = [a for a in archivos_cuota if "parcial" not in a]

print(f"=== UNIR CUOTAS ===")
print(f"Archivos de cuotas encontrados: {len(archivos_cuota)}")
for a in archivos_cuota:
    print(f"  - {a}")
print()

if not archivos_cuota:
    print("[!] No se encontraron archivos de cuotas en output/.")
    print("    Asegurate de haber corrido al menos una cuota.")
else:
    # Leer y combinar todos
    dfs = []
    for archivo in archivos_cuota:
        df = pd.read_csv(archivo, sep='\t')
        print(f"  {os.path.basename(archivo)}: {len(df)} propiedades")
        dfs.append(df)

    # Concatenar todo
    df_total = pd.concat(dfs, ignore_index=True)

    # Eliminar duplicados por link (por si alguna propiedad apareció en dos barrios)
    antes = len(df_total)
    df_total = df_total.drop_duplicates(subset=['link'], keep='first')
    duplicados = antes - len(df_total)

    # Guardar el dataset final
    filepath = os.path.join(output_dir, "mercadolibre_CABA_completo.tsv")
    df_total.to_csv(filepath, sep='\t', index=False, encoding='utf-8-sig')

    print(f"\n{'='*50}")
    print(f"¡LISTO! Dataset final combinado.")
    print(f"Archivo: {filepath}")
    print(f"{'='*50}")
    print(f"\n--- Resumen ---")
    print(f"Total propiedades: {len(df_total)}")
    print(f"Duplicados eliminados: {duplicados}")
    print(f"Columnas: {len(df_total.columns)}")
    print(f"\nPropiedades por barrio:")
    print(df_total['barrio'].value_counts().to_string())
