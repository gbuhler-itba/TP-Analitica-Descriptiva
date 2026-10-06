# Estado de las correcciones de la PreEntrega 1

Actualizado: 06/10/2026. Cada fila dice qué pidió la devolución y dónde está resuelto.

| # | Qué pidió la devolución | Estado | Dónde está |
|---|---|---|---|
| 1 | Rutas absolutas, parametrizar, cadena de etapas, corrida única documentada | Hecho | Runner único (`run_pipeline.py`), `config/config.yaml`, QC por etapa y corrida documentada en `docs/corrida-documentada/`. Los notebooks usan rutas relativas al repositorio y parámetros centralizados (`PARAMS`) |
| 2 | Medir cuánto discrimina cada bloque del índice | Hecho | `docs/correcciones_pe1/diagnostico.md` (3.2) y `correlaciones_indice.py`. El bloque de infraestructura casi no se relaciona con el precio dentro de la sub-zona |
| 3 | Mostrar cómo cambian los resultados con otras ponderaciones | Hecho | `diagnostico.md` (3.3): 171 ponderaciones probadas: la lista de marcados cambia poco (coincidencia mediana de 0,82 con la de 45/30/25, y 692 avisos marcados con todas). Pero dos tercios de lo marcado ya aparecía mirando solo el precio relativo a la sub-zona: el índice aportaba poco, y eso llevó al cambio del punto 4 |
| 4 | No fijar los pesos antes de ver los datos | Hecho | Los pesos 45/30/25 se reemplazan por el **precio esperado**: una regresión estima cuánto paga el mercado por cada característica dentro de la zona (prima por característica). Notebook 03, secciones 3 a 5 |
| 5 | Casos detectados = "señal de precio atípico", no "subvaluación" | Hecho | H1 reformulada; los KPIs pasan a "brecha de precio" y "ranking de avisos a investigar". La revisión de avisos del ranking (notebook 03, sección 10) muestra por qué no son oportunidades confirmadas |
| 6 | Una oportunidad requiere costos, estado, liquidez y riesgo | Hecho | `docs/entregas_grupo/preguntas_y_alcance.md`, Parte 3 ("qué NO mide el análisis") y borrador de regla de decisión. `bajo_de_precio` se analiza aparte como indicio de liquidez (notebook 03, sección 8) |
| 7 | Reclasificar preguntas por nivel | Hecho | `preguntas_y_alcance.md`, Parte 1 |
| 8 | Predictivo: variable objetivo, información disponible al predecir, validación fuera de muestra | Hecho | `preguntas_y_alcance.md`, Parte 2, implementado en el notebook 03: validación en 5 partes agrupadas por unidad, comparada contra la mediana de la zona (12,7% contra 17,2% de error) |
| 9 | Contexto argentino | Hecho | `docs/entregas_grupo/contexto_argentino.md`, con fuentes y números propios reproducibles |
| 10 | Qué aporta cada fuente, granularidad, qué mejora | Hecho | `docs/entregas_grupo/fuentes_externas.md`: 10 fichas con el formato del enunciado. Reemplaza al borrador `docs/correcciones_pe1/fuentes_externas.md` |
| 11 | Cifras narradas = calculadas (130.000 vs 135.000) | Hecho | La diferencia venía de 627 precios concatenados por "BAJÓ DE PRECIO". Se corrigen en la limpieza (notebook 01); la mediana correcta es USD 130.000 |

## Encontrado además

| Tema | Estado |
|---|---|
| 627 precios concatenados por "BAJÓ DE PRECIO" | Corregido en el notebook 01 (`corregir_precio()`) |
| 68 avisos duplicados por ID que la deduplicación por link no detectaba | Eliminados en el notebook 01 |
| Sesgo del geocoding por barrio (Puerto Madero 60%, Boedo 92%) | Medido y declarado como limitación; en el modelo, los avisos sin coordenadas se comparan contra su barrio |
| Fecha de extracción (14/08/2026) | Declarada en el notebook 01 y en el diccionario |

## Decisiones del grupo

1. **Pesos del índice:** derivados de los datos, como primas de un modelo de precio esperado. H1 se reescribe.
2. **Unidad de comparación:** sub-zona solo en los barrios donde mejora la referencia fuera de muestra; barrio en el resto.
3. **Umbral para marcar un aviso:** brecha menor a −25%, dos veces el error típico del modelo, con un control por el error de cada barrio.
4. **Tipo de cambio para expensas:** dólar MEP del 14/08/2026 (ARS 1.518,05).
5. **Avisos en pozo:** excluidos, porque el alcance es departamentos usados.
6. **Alquileres:** quedan como próximo paso; no se scrapearon para esta entrega.
