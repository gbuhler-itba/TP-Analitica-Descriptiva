# Fondo de inversión inmobiliario: avisos con precio atípicamente bajo en CABA

**Analítica Descriptiva, ITBA, 2026 C2 · PreEntrega 2**

Herramienta para que el analista de un fondo de inversión inmobiliario encuentre, entre decenas de miles de
avisos de departamentos usados en venta en CABA, los que se publican claramente por debajo del precio que el
mercado paga por sus características en su zona. Son **señales de precio atípicamente bajo para investigar**, no
oportunidades confirmadas.

| Para ver | Dónde |
|---|---|
| Limpieza y calidad del dato | [`notebooks/01_calidad_y_limpieza.ipynb`](notebooks/01_calidad_y_limpieza.ipynb) |
| Análisis exploratorio (H2, H3) | [`notebooks/02_eda.ipynb`](notebooks/02_eda.ipynb) |
| Precio esperado, brecha y ranking (H1) | [`notebooks/03_precio_esperado.ipynb`](notebooks/03_precio_esperado.ipynb) |
| Diccionario de datos | [`docs/entregas_grupo/diccionario_datos.md`](docs/entregas_grupo/diccionario_datos.md) |
| Fuentes externas (fichas) | [`docs/entregas_grupo/fuentes_externas.md`](docs/entregas_grupo/fuentes_externas.md) |
| Contexto del mercado argentino | [`docs/entregas_grupo/contexto_argentino.md`](docs/entregas_grupo/contexto_argentino.md) |
| Preguntas, nivel predictivo y qué no mide el análisis | [`docs/entregas_grupo/preguntas_y_alcance.md`](docs/entregas_grupo/preguntas_y_alcance.md) |
| Respuesta a la devolución de la PreEntrega 1 | [`docs/correcciones_pe1/estado_correcciones.md`](docs/correcciones_pe1/estado_correcciones.md) |
| Pipeline de datos (scraping a dataset enriquecido) | [`docs/pipeline.md`](docs/pipeline.md) |

---

## 1. Descripción del proyecto

Dos departamentos de la misma zona y con características parecidas deberían publicarse a un precio por m²
parecido. El proyecto estima, para cada aviso, un **precio esperado** según lo que tiene (superficie, antigüedad,
cochera, amenities, piso, etc.) y dónde está, y mide la **brecha de precio**: cuánto se aleja el precio publicado
de ese valor. Los avisos con una brecha muy negativa pasan a un **ranking de avisos a investigar**.

En la PreEntrega 1 esa comparación se hacía con un índice de confort de pesos fijos (45/30/25). A partir de la
devolución, los pesos dejaron de elegirse a mano: salen de los datos, como la prima que el mercado paga por cada
característica dentro de la zona (sección 10).

**Resultados de esta entrega**

- El modelo de precio esperado erra 12,7% en la mediana, fuera de muestra, contra 17,2% de usar la mediana de la
  zona como referencia.
- 1.704 avisos (6,2%) piden más de 25% menos que su precio esperado; 1.434 de ellos siguen marcados con un umbral
  ajustado al error de su barrio, y 1.225 de esos no tienen señales de error de carga. Pero la cola de abajo no es más
  pesada de lo esperable (6,0% con una normal de la misma dispersión) y es más chica que la de arriba (8,9%): la
  brecha ordena los avisos, no prueba que su precio sea atípico.
- La revisión de avisos en el portal muestra que los casos más extremos son errores de carga o casos especiales, y
  que en los intermedios el descuento suele tener un motivo que el aviso no registra (se vende con inquilino, está
  sin terminar). La brecha sirve para priorizar qué revisar, no para afirmar una subvaluación.
- Las palabras del título lo confirman a escala: los avisos que se publican "a refaccionar" quedan marcados tres veces
  más que el resto (19,2% contra 6,0%). Parte de la brecha es el estado del inmueble, que la ficha no informa.
- La antigüedad es lo que más pesa en el precio por m² dentro de la zona (un edificio de 0 a 5 años se publica 37%
  más caro que uno de más de 70); la cercanía al subte no, una vez controlada la antigüedad.

## 2. Interlocutor y usuario

**Usuario principal: el analista de inversiones del fondo.** Revisa el flujo de avisos publicados y arma la lista
de candidatos que eleva al comité. Su problema es de volumen: hay decenas de miles de avisos activos en CABA y no
puede leerlos todos. La herramienta le devuelve un ranking corto de avisos con precio atípicamente bajo para su
zona y sus características, con señales que indican qué revisar primero (posible error de carga, baja de precio).

**Usuario secundario: el comité de inversión**, que recibe los casos ya verificados por el analista y decide la
compra. Usa además el análisis por zona para decidir dónde concentrar el capital.

## 3. Contexto de negocio

El fondo compra departamentos usados en CABA. Busca avisos publicados por debajo de lo que el mercado paga por
departamentos comparables, para después verificarlos y decidir la compra.

El mercado argentino condiciona cómo se lee un precio publicado. Resumen (detalle, fuentes y números propios en
[`contexto_argentino.md`](docs/entregas_grupo/contexto_argentino.md)):

| Rasgo | Qué implica para el análisis |
|---|---|
| **Dolarización**: 27.917 de 27.922 avisos están en USD | Los precios se comparan sin ajustar por inflación; las expensas están en pesos y se convierten con un tipo de cambio declarado |
| **Crédito hipotecario limitado** (~1% del PBI) y cíclico | El precio lo fija quien tiene dólares ahorrados. El precio esperado vale para agosto de 2026, en la fase baja del ciclo |
| **Operaciones al contado** (85% de las escrituras de 2026) | `apto_credito` indica requisitos legales, no forma de pago. Entra al modelo como control |
| **Iliquidez**: vender lleva unos 9 meses | Un precio bajo puede ser un vendedor apurado. "Bajó de precio" se analiza aparte |
| **Brecha publicado-cierre** (~5%) | Solo vemos precios publicados: el umbral para marcar un aviso tiene que ser claramente mayor que el margen de negociación |
| **Ciclos regulatorios del alquiler** | El stock en venta de 2026 no es comparable con el de 2020-2023 |

**Tipo de cambio.** Las expensas se convierten con el dólar MEP del 14/08/2026 (ARS 1.518,05 por USD, Ámbito),
porque es el tipo de cambio al que una persona convierte legalmente sus dólares a pesos. Como referencia, el A
3500 del BCRA ese día era ARS 1.488,70; la elección cambia la mediana de expensas de USD 131,7 a USD 134,3 y no
cambia el orden de los avisos dentro de una zona.

## 4. Alcance y unidad de análisis

- **Unidad de análisis:** el aviso de departamento usado en venta publicado en MercadoLibre Inmuebles.
- **Unidad de comparación:** la **zona de referencia**. Es la sub-zona (cluster espacial de avisos dentro del
  barrio, hasta 5 por barrio) en los 28 barrios donde mejora la referencia de precio fuera de muestra, y el barrio
  completo en los otros 19. Los avisos sin coordenadas y las zonas con menos de 10 avisos se comparan contra el
  barrio (notebook 02, sección 4; notebook 03, sección 2).
- **Geográfico:** 47 categorías de barrio de MercadoLibre. No coinciden con los 48 barrios oficiales: incluyen
  "Barrio Norte" y no incluyen San Cristóbal ni Parque Chas.
- **Tipología:** departamentos usados en venta. Quedan fuera casas, alquileres y unidades en pozo (237 avisos: 235
  con antigüedad negativa y 2 con la antigüedad mal cargada, se excluyen en la limpieza). Una casa publicada como
  departamento sigue en el dataset, marcada como atípica.
- **Precio:** precio de publicación en USD, no precio de cierre.
- **Temporal:** una foto del mercado; fecha de extracción 14/08/2026.

## 5. Preguntas por nivel analítico

Reclasificadas a partir de la devolución. Versión completa, con el porqué de cada nivel, en
[`preguntas_y_alcance.md`](docs/entregas_grupo/preguntas_y_alcance.md).

| Nivel | # | Pregunta (resumida) | Estado en esta entrega |
|---|---|---|---|
| Descriptivo | D1 | ¿Cómo se distribuye el precio por m² entre barrios y entre sub-zonas de un barrio? | Respondida: la mediana va de USD 1.016 a 6.125 por m² entre barrios, y las sub-zonas de un mismo barrio difieren en una mediana de 18% (notebook 02, secciones 2 a 5) |
| | D2 | ¿Qué proporción de avisos declara cada característica y qué tan completo está cada aviso? | Respondida: por columna (diccionario y notebook 01) y por aviso, con la tasa de completitud (notebook 03, sección 11) |
| | D3 | ¿Con qué frecuencia aparece cada característica en cada zona? | Parcial: frecuencias generales en el diccionario |
| | D4 | ¿Cuántos avisos bajaron de precio, cuánto y dónde? | Respondida: 626 avisos (2,3%), baja mediana de 6,8%, de 0% a 5,2% según el barrio (notebook 01; notebook 02, sección 8; notebook 03, sección 8) |
| Diagnóstico | G1 | Dentro de la zona, ¿cuánto se asocia cada característica con el precio por m²? | Respondida (notebook 03, sección 5) |
| | G2 | ¿La prima de cada característica cambia según la zona o el segmento de precio? | Pendiente |
| | G3 | ¿Cuánto de la diferencia de precio se explica por accesibilidad y centralidad? | Parcial: casi nada dentro del barrio, una vez controlada la antigüedad (notebook 02, sección 6); falta ver si los marcados lo siguen siendo al controlar por ubicación |
| | G4 | ¿Qué distingue a los avisos con precio atípicamente bajo? | Parcial: errores de carga, bajas de precio, palabras del título, expensas y revisión en el portal (notebook 03, secciones 7, 8, 10 y 11) |
| Predictivo | P1 | ¿Qué precio por m² se esperaría para un aviso según sus características y su zona? | Respondida (notebook 03, sección 4) |
| | P2 | ¿Con qué error, y dónde es mayor? | Respondida: 12,7% en la mediana; mayor en Puerto Madero y en barrios chicos del sur y el oeste (notebook 03, secciones 4 y 9) |
| | P3 | ¿Qué precio se esperaría para un departamento no publicado? | Posible con el mismo modelo; no se aplicó a casos concretos |
| | P4 | Si se repite el scraping, ¿los avisos marcados salen del portal o bajan antes que sus comparables? | Requiere un segundo relevamiento |
| Prescriptivo | R1 | ¿Qué regla decide qué avisos pasan a revisión? | Propuesta: brecha menor a −25% (dos veces el error mediano del modelo, que además supera la suma de error y negociación), con el umbral por barrio y sin señales de error de carga. En el ranking, columna `cumple_regla` (1.150 unidades) |
| | R2 | ¿Conviene ponderar distinto un aviso bien ubicado que uno periférico? | Pendiente |
| | R3 | ¿En qué zonas concentrar el análisis? | Parcial: el error del modelo por barrio indica dónde la brecha es más confiable (notebook 03, sección 9) |

## 6. Hipótesis y KPIs revisados

### Hipótesis

| | Hipótesis | Evidencia | Estado |
|---|---|---|---|
| H1 | Dentro de una zona hay avisos publicados claramente por debajo del precio esperado para sus características, más allá del margen normal de negociación (~5%). Son candidatos a investigar, no oportunidades confirmadas | 1.704 avisos con brecha menor a −25%; la mayoría (84%) se mantiene con un umbral por barrio. Pero la cola de abajo (6,2%) no es más pesada que la de una normal con la misma dispersión (6,0%) ni que la de arriba (8,9%), y los casos revisados en el portal muestran errores de carga o motivos no registrados | Apoyo débil: la brecha prioriza qué revisar, pero no prueba precios atípicos más allá del error del modelo (notebook 03) |
| H2 | Un barrio no es homogéneo: la sub-zona da una referencia de precio más precisa que el barrio | El error de la referencia (avisos con coordenadas) baja de 17,7% a 17,2% en total, pero en algunos barrios baja mucho (Villa Lugano, de 25% a 14%) y en otros empeora | Apoyo parcial: depende del barrio (notebook 02) |
| H3 | Parte de la diferencia de precio dentro de un barrio se explica por la ubicación: cercanía al subte y a los polos de centralidad | A menos de 300 m del subte los precios son 5,5% menores, pero a igual antigüedad la diferencia baja a −1,9%. La centralidad no se relaciona con el precio (ρ ≈ 0) | No se detectó con estos indicadores (notebook 02): los polos están en el microcentro y falta el transporte del sur y el oeste |

### KPIs

| KPI | Qué mide | Cómo se calcula | Estado |
|---|---|---|---|
| Precio por m² de la zona | La referencia simple de precio | Mediana de `precio_m2_usd` en la zona de referencia | Calculado (notebooks 02 y 03) |
| Prima por característica | Cuánto paga el mercado por cada característica dentro de la zona (reemplaza al peso empírico por bloque) | Coeficiente del modelo de precio esperado, en % | Calculado (notebook 03, sección 5) |
| Precio esperado | El precio por m² "normal" para un aviso | Predicción fuera de muestra del modelo | Calculado (`precio_esperado.tsv`) |
| Brecha de precio | Cuánto se aleja el precio publicado del esperado (reemplaza al gap de confort) | `precio_m2_usd / precio_m2_esperado − 1` | Calculado (notebook 03, sección 6) |
| Error de estimación fuera de muestra | Si la brecha es señal o ruido | Mediana del error absoluto del precio esperado, por zona y por barrio | Calculado: 12,7% |
| Ranking de avisos a investigar | Lista priorizada para el analista (reemplaza al ranking de oportunidades) | Avisos con brecha menor a −25%, uno por unidad, con señales de error de carga, de baja de precio y del título, y la columna `cumple_regla` | Calculado (`avisos_a_investigar.csv`) |
| Tasa de completitud | Qué tan confiable es el precio esperado de un aviso | % de los 26 campos de la ficha donde el vacío es falta de dato que tienen dato | Calculado (notebook 03, sección 11): mediana 88%; no se asocia con la marca |
| Eficiencia de expensas | Si las expensas son altas para lo que ofrece el edificio | Expensas en USD por m², relativas a la mediana de la zona (`expensas_rel_zona`) | Calculado (notebook 03, sección 11): con expensas bajas para su zona se marca el 9,9% de los avisos; con expensas altas, el 3,3% |
| Índice de accesibilidad | Qué tan bien conectado está un aviso | Distancia al transporte pesado | Replanteado: con subte solo no explicó el precio (H3); se retoma con tren y Metrobus |

## 7. Datasets y fuentes externas

### Dataset principal

Construido por web scraping de MercadoLibre Inmuebles, extraído el 14/08/2026, y enriquecido con geocodificación
y distancias. El detalle de cada columna está en el
[diccionario de datos](docs/entregas_grupo/diccionario_datos.md).

| Archivo | Filas × columnas | Qué es |
|---|---|---|
| `data/raw/cuotas/cuota1..5.tsv` | 27.922 en total | Salida cruda del scraper, sin modificaciones |
| `data/processed/propiedades_enriquecidas.tsv` | 27.922 × 93 | Consolidado, geocodificado y con distancias y sub-zonas (pipeline) |
| `data/processed/propiedades_limpias.tsv` | 27.579 × 112 | Dataset de trabajo, salida del notebook 01 |
| `data/processed/registro_limpieza.csv` | 343 | Avisos excluidos y su motivo |
| `data/processed/precio_esperado.tsv` | 27.579 | Precio esperado, brecha, marcas, variables del título y KPIs de cada aviso (notebook 03) |
| `data/processed/avisos_a_investigar.csv` | 1.590 | Ranking: una fila por unidad marcada; `cumple_regla` señala las 1.150 que pasan la regla R1 (notebook 03) |

**Del crudo al limpio.** Se excluyen 343 avisos: 68 duplicados por ID de aviso, 237 en pozo, 28 con superficie
inválida, 5 con precio en pesos, 4 con precio menor a USD 20.000 y 1 con precio imposible. Se corrigen 627
precios concatenados por "BAJÓ DE PRECIO" (la mediana correcta es USD 130.000, no 135.000), se unifican dos
etiquetas mal cargadas ("24 hs" y "Penthhouse") y se marcan, sin
borrarlos, posibles duplicados con otro ID (3.059), outliers de precio por m² para su zona (928) e incoherencias
entre variables. Todo está justificado en el notebook 01.

| Métrica (dataset limpio) | Valor |
|---|---|
| Avisos | 27.579 |
| Con coordenadas | 82,1% |
| Mediana de precio | USD 130.000 |
| Mediana de precio por m² | USD 2.393 |
| Mediana de superficie | 57 m² |

### Fuentes externas

Fichas completas, con el formato del enunciado, en
[`fuentes_externas.md`](docs/entregas_grupo/fuentes_externas.md).

| Fuente | Granularidad | Variable | Estado |
|---|---|---|---|
| Normalizador de direcciones USIG (GCBA) | Punto | `lat`, `lon` | Integrada |
| Estaciones de subte (BA Data) | Punto | `dist_transporte_m` | Integrada |
| Polos de centralidad (definición propia) | Punto | `dist_centralidad_m` | Integrada |
| Dólar MEP del 14/08/2026 | Un valor | `expensas_ars`, `expensas_usd` | Integrada |
| Estaciones de ferrocarril (BA Data) | Punto | `dist_tren_m` | Prevista |
| Metrobus (BA Data) | Punto | `dist_metrobus_m` | Prevista |
| Espacios verdes (BA Data) | Polígono | `dist_espacio_verde_m` | Prevista |
| Polígonos de barrios (BA Data) | Polígono | `barrio_oficial` | Prevista, control de calidad |
| Barrios populares (BA Data) | Polígono | `en_barrio_popular` | Prevista |
| Permisos de obra (BA Data) | Punto | `permisos_obra_500m` | Prevista |

Las previstas se unen por punto o por polígonos más chicos que la zona, así que pueden distinguir avisos dentro de
una misma zona; los polígonos de barrios se usan solo como control de calidad. Se descartaron las fuentes agregadas por comuna, que toman el mismo valor para barrios distintos.

## 8. Estructura del repositorio

```
├── README.md
├── requirements.txt                 Dependencias con versiones fijadas
├── run_pipeline.py                  Runner del pipeline (scraping a dataset enriquecido)
├── config/config.yaml               Rutas y parámetros del pipeline
├── data/
│   ├── raw/cuotas/                  Salida cruda del scraper, sin modificaciones
│   ├── interim/                     Consolidado y geocodificado
│   ├── processed/                   Enriquecido, limpio, precio esperado y ranking
│   └── external/                    Snapshot del GeoJSON de estaciones de subte
├── notebooks/
│   ├── 01_calidad_y_limpieza.ipynb
│   ├── 02_eda.ipynb
│   └── 03_precio_esperado.ipynb
├── src/
│   ├── limpieza.py                  Funciones de limpieza (notebook 01)
│   ├── eda.py                       Funciones del análisis exploratorio (notebook 02)
│   ├── modelo.py                    Precio esperado y validación cruzada (notebook 03)
│   ├── indice_confort.py            Índice de la PreEntrega 1, usado en el diagnóstico de la devolución
│   ├── scrapper_mercadolibre.py     Etapa 1 del pipeline
│   ├── unir_cuotas.py               Etapa 2
│   ├── geocoding_propiedades.py     Etapa 3
│   ├── enriquecimiento.py           Etapa 4
│   └── rutas.py, configuracion.py, entorno.py, qc.py
├── tests/                           Verificación offline del pipeline
├── outputs/logs/                    Logs de corrida (no versionados)
└── docs/
    ├── entregas_grupo/              Contexto, preguntas, diccionario y fuentes externas
    ├── correcciones_pe1/            Diagnóstico de la devolución y estado de las correcciones
    ├── pipeline.md                  Pipeline: instalación, ejecución, controles y verificación
    ├── proceso_tecnico.md           Desafíos técnicos del scraping
    ├── corrida-documentada/         Evidencia de la corrida del pipeline
    └── caso_de_negocio.pdf          Documento de negocio de la PreEntrega 1
```

## 9. Cómo reproducir el análisis

Requiere Python 3.9 a 3.12; la versión de referencia es 3.9, y los notebooks se ejecutaron con 3.11 y las versiones de `requirements.txt`.

```bash
git clone https://github.com/gbuhler-itba/TP-Analitica-Descriptiva.git
cd TP-Analitica-Descriptiva
python3 -m venv .venv && source .venv/bin/activate    # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Análisis.** Los datasets vienen versionados, así que no hace falta correr el pipeline. Abrir los notebooks con el
kernel del entorno virtual y ejecutarlos en orden:

1. `01_calidad_y_limpieza.ipynb` lee `propiedades_enriquecidas.tsv` y escribe `propiedades_limpias.tsv` y
   `registro_limpieza.csv`.
2. `02_eda.ipynb` lee el dataset limpio.
3. `03_precio_esperado.ipynb` lee el dataset limpio y escribe `precio_esperado.tsv` y `avisos_a_investigar.csv`.

Los notebooks usan rutas relativas a la raíz del repositorio y concentran sus parámetros en un diccionario
`PARAMS` al principio. No hace falta editar nada.

**Pipeline.** Para regenerar el dataset enriquecido desde las cuotas crudas: `python3 run_pipeline.py`. El
scraping completo (8 a 15 horas, desde una IP residencial) solo corre con `--incluir-scraping`. Instalación,
opciones, controles de calidad y verificación offline en [`docs/pipeline.md`](docs/pipeline.md).

## 10. Cambios a partir de la devolución de la PreEntrega 1

Detalle punto por punto en [`estado_correcciones.md`](docs/correcciones_pe1/estado_correcciones.md).

| Observación de la devolución | Qué se hizo |
|---|---|
| Rutas absolutas, falta de parametrización, cadena de etapas cortada | Runner único, configuración en YAML, controles por etapa, corrida documentada y verificación offline ([`docs/pipeline.md`](docs/pipeline.md)) |
| Los pesos 45/30/25 se fijaron antes de ver los datos | Se midió cuánto discrimina cada bloque y cómo cambian los resultados con 171 ponderaciones ([`diagnostico.md`](docs/correcciones_pe1/diagnostico.md)). Los pesos se reemplazaron por las primas de un modelo de precio esperado estimado sobre los datos |
| Los casos detectados no son "subvaluación" | H1 reformulada; KPIs renombrados (brecha de precio, ranking de avisos a investigar); revisión de avisos en el portal |
| Una oportunidad requiere costos, estado, liquidez y riesgo | Sección "qué no mide el análisis" y borrador de regla de decisión ([`preguntas_y_alcance.md`](docs/entregas_grupo/preguntas_y_alcance.md)) |
| Preguntas mal clasificadas por nivel | Reclasificadas (sección 5) |
| Nivel predictivo sin definir | Variable objetivo, información disponible al predecir y validación fuera de muestra, implementados en el notebook 03 |
| Falta el contexto argentino | [`contexto_argentino.md`](docs/entregas_grupo/contexto_argentino.md), con fuentes y números propios |
| Fuentes externas sin granularidad ni aporte | 10 fichas con el formato del enunciado |
| Cifras narradas distintas de las calculadas (135.000 contra 130.000) | La diferencia venía de 627 precios concatenados; se corrigen en la limpieza |

**Encontrado además:** 68 avisos duplicados que la deduplicación por link no detectaba, el sesgo de la
geocodificación por barrio (de 59,5% de éxito en Puerto Madero a 92,5% en Boedo) y la fecha de extracción, que no
estaba declarada.

## 11. Observaciones pendientes y plan

| Pendiente | Por qué importa | Plan |
|---|---|---|
| Las primas pueden cambiar según la zona o el segmento (G2) | Un único coeficiente por característica para toda la ciudad puede no alcanzar | Estimar primas por grupos de barrios o por segmento de precio |
| Estado del inmueble y expensas fuera del modelo | Explican parte de la brecha: los avisos "a refaccionar" se marcan tres veces más, y los de expensas bajas para su zona también | Sumar las marcas del título y las expensas relativas como controles del modelo, y medir cuánto cambia el ranking |
| Ubicaciones especiales dentro de un barrio (Rodrigo Bueno en Puerto Madero) | El modelo las compara con el resto del barrio | Integrar la fuente de barrios populares |
| Accesibilidad solo con subte | Deja afuera el transporte del sur y el oeste | Integrar tren y Metrobus y volver a evaluar H3 |
| Validación de la señal (P4) | Es la única forma de saber si la brecha anticipa algo real | Repetir el scraping y comparar marcados contra comparables |
| Errores residuales de la limpieza: 303 baños en 0, pisos cargados como número de unidad, 254 expensas de 1 a 1.000 pesos, una casa publicada como departamento | Se verificó que no cambian el modelo (1.702 marcados en lugar de 1.704), pero son datos incorrectos | Corregirlos en la próxima versión de la limpieza |
| Marca de outliers y elección de barrios calculadas con todos los avisos, y comparación de H2 con particiones que no agrupan por unidad | Tocan la separación de la validación cruzada. Con particiones agrupadas, la sub-zona mejora en 24 barrios en lugar de 28 | Calcularlas dentro de cada vuelta y con particiones por unidad |
| Atípicos marcados con IQR sobre el precio por m², no sobre su logaritmo | Solo dejan fuera del ajuste la cola de arriba (con el logaritmo serían 536 atípicos, 187 por debajo) | Recalcularlos sobre el logaritmo y por zona de referencia |
| En las características Sí/No, el vacío entra al modelo junto con el "No" | La prima compara "lo declara" contra "no lo declara" | Probar una categoría propia para el vacío |
| Permisos de obra y alquileres | Dinamismo de zona y rentabilidad | Evaluar para la PreEntrega 3 |

## 12. Limitaciones

- **Precio publicado, no de cierre.** La brecha se mide contra precios publicados; la negociación ronda el 5%.
- **Una sola foto.** Sin fechas de publicación no se puede medir cuánto tiempo lleva un aviso ni si la brecha se
  cierra.
- **Características declaradas, no verificadas.** En las columnas que solo muestran "Sí", el vacío no distingue
  "no tiene" de "no se cargó". El estado del departamento no está en los datos.
- **Geocodificación desigual.** El 17,9% de los avisos no tiene coordenadas, y la pérdida varía por barrio. Esos
  avisos se comparan contra su barrio.
- **Barrios truncados.** Palermo, Belgrano, Caballito y Recoleta llegaron al tope de paginación (2.016 avisos):
  son una muestra de la oferta, no el total.
- **Error del modelo.** Un error mediano de 13% sirve para ordenar avisos, no para tasar uno en particular ni para
  separar un precio atípico de un error de estimación.
