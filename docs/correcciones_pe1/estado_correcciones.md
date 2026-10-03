# Estado de las correcciones de la PreEntrega 1

Actualizado: 29/09/2026. Detalle y números en `diagnostico.md`.

✅ hecho · 🟡 evidencia lista, falta decidir o redactar · ❌ pendiente

| # | Qué pidió el profe | Peso | Estado | Qué hay / qué falta |
|---|---|---|---|---|
| 1 | Rutas absolutas, parametrizar, cadena de etapas, corrida única documentada | 15% | ✅ | Hecho en septiembre: runner único, config, QC por etapa, smoke test 26/26 |
| 2 | Medir cuánto discrimina cada bloque del índice | 20% | 🟡 | Medido (`diagnostico.md` 3.2 y `correlaciones_indice.py`). Falta pasarlo al README y al notebook |
| 3 | Mostrar cómo cambian los resultados con otras ponderaciones | 20% | 🟡 | Hecho: 171 ponderaciones, 692 avisos estables (3.3). Falta pasarlo al README y al notebook |
| 4 | No fijar los pesos antes de ver los datos | 20% | 🟡 | Hay evidencia (correlaciones, redundancias, agrupación). **Falta decidir** mapeo, agrupación y criterio de pesos |
| 5 | Casos detectados = "señal de precio atípico", no "subvaluación" | 20% | ❌ | Evidencia a favor: 2/3 de lo que marca el índice ya sale con "barato para su sub-zona". Falta reescribir H1, objetivo, KPIs "Gap de confort" y "Ranking de oportunidades" |
| 6 | Una oportunidad requiere costos, estado, liquidez y riesgo | 20% | ❌ | Falta decir explícitamente qué no mide el análisis. `bajo_de_precio` puede servir como indicio de liquidez |
| 7 | Reclasificar preguntas ("bloque más regalado" es diagnóstico, "cómo ponderar" es prescriptivo) | 20% | ❌ | Falta |
| 8 | Predictivo: variable objetivo, información disponible al predecir, validación fuera de muestra | 20% | ❌ | Falta. Distinguir predicción de un valor no observado vs. pronóstico temporal |
| 9 | Contexto argentino: dolarización, crédito, contado, iliquidez, brecha publicación/cierre, ciclos de alquiler | 15% | ❌ | Falta. Es redacción con fuentes |
| 10 | Qué aporta cada fuente, granularidad, qué mejora | 10% | 🟡 | Borrador de 9 fichas en `fuentes_externas.md`. Falta revisar y pasar al README |
| 11 | Cifras narradas = calculadas (130.000 vs 135.000) | 10% | 🟡 | Causa encontrada y corregida (`src/limpieza.py`): la mediana correcta es 130.000. Falta corregir el README |

## Encontrado además (no lo pidió, pero se lo va a encontrar)

| Tema | Estado |
|---|---|
| 627 precios concatenados por "BAJÓ DE PRECIO" (media en USD de 5.215 millones) | ✅ función de corrección. Falta aplicarla en el notebook 01 |
| Sesgo del geocoding por barrio (Puerto Madero 60%, Boedo 92%) | ✅ medido. Falta pasarlo a limitaciones del README |
| Fecha de extracción (14/08/2026) | ✅ registrada. Falta declararla en README y notebook |

## Decisiones para el grupo

1. **Pesos del índice:** ¿derivados de los datos (el índice pasa a ser "lo que el mercado paga" y se reescribe H1) o preferencia del fondo, declarada y contrastada con la sensibilidad?
2. **Qué componentes entran:** ¿se agrupan pileta, gimnasio, SUM y parrilla? ¿Salen lavandería, lavarropas, agua corriente, internet y gas?
3. **Infraestructura:** ¿sale del índice, se usa como filtro de calidad del aviso o se queda con peso bajo?
4. **Nulos en columnas "solo Sí":** ¿"no tiene" o "sin dato"?
5. **Tipo de cambio para expensas:** ¿oficial A3500 o MEP?
6. **Alquileres:** propuesta de dejarlo como próximo paso y no scrapear para esta entrega.
7. **Reparto:** contexto macro y preguntas (redacción), índice (decisión metodológica), notebooks (código).

## Además, lo que pide el TP2 y no es corrección

Notebooks numerados en `/notebooks` (01 calidad y limpieza, 02 EDA), diccionario de
datos, dataset limpio en `/data/processed`, y en el README las secciones "cambios a
partir de la devolución" y "observaciones pendientes y plan". Entrega: 07/10.
