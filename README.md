# Fondo de inversión inmobiliario: avisos con precio atípicamente bajo en CABA

**Analítica Descriptiva, ITBA, 2026 C2 · PreEntrega 3**

Herramienta para que el analista de un fondo de inversión inmobiliario encuentre, entre decenas de miles de
avisos de departamentos usados en venta en CABA, los que se publican claramente por debajo del precio que el
mercado paga por sus características en su zona. Son **señales de precio atípicamente bajo para investigar**, no
oportunidades confirmadas: la brecha prioriza qué revisar, y una regla de decisión con costos separa, dentro de
esas señales, los **candidatos después de costos**. En ningún nivel se afirma una subvaluación.

| Para ver | Dónde |
|---|---|
| **Dashboard para el analista del fondo** | [Radar de avisos · CABA en GitHub Pages](https://gbuhler-itba.github.io/TP-Analitica-Descriptiva/dashboard/) (código y datos en [`docs/dashboard/`](docs/dashboard/)) |
| Limpieza y calidad del dato | [`notebooks/01_calidad_y_limpieza.ipynb`](notebooks/01_calidad_y_limpieza.ipynb) |
| Análisis exploratorio (PE2) | [`notebooks/02_eda.ipynb`](notebooks/02_eda.ipynb) |
| Precio esperado, brecha y ranking (PE2, números actualizados) | [`notebooks/03_precio_esperado.ipynb`](notebooks/03_precio_esperado.ipynb) |
| Validación y comparación de modelos, intervalo, primas, SHAP | [`notebooks/04_validacion_modelos.ipynb`](notebooks/04_validacion_modelos.ipynb) |
| Evaluación de las hipótesis H1, H2 y H3 | [`notebooks/05_hipotesis.ipynb`](notebooks/05_hipotesis.ipynb) |
| Índice de equipamiento (MCA) y micro-mercados (K-means), exploratorio | [`notebooks/06_segmentos_exploratorio.ipynb`](notebooks/06_segmentos_exploratorio.ipynb) |
| Regla de decisión con costos | [`notebooks/07_regla_de_decision.ipynb`](notebooks/07_regla_de_decision.ipynb) |
| Diccionario de datos | [`docs/entregas_grupo/diccionario_datos.md`](docs/entregas_grupo/diccionario_datos.md) |
| Fuentes externas (fichas) y sus controles | [`fuentes_externas.md`](docs/entregas_grupo/fuentes_externas.md), [`control_fuentes.md`](docs/entregas_grupo/control_fuentes.md) |
| Costos, liquidez, estado y riesgo legal (fuentes) | [`costos_y_liquidez.md`](docs/entregas_grupo/costos_y_liquidez.md), [`config/costos.yaml`](config/costos.yaml) |
| Contexto del mercado argentino | [`contexto_argentino.md`](docs/entregas_grupo/contexto_argentino.md) |
| Preguntas, nivel predictivo y qué no mide el análisis | [`preguntas_y_alcance.md`](docs/entregas_grupo/preguntas_y_alcance.md) |
| Pipeline de datos (scraping a lista oficial), tests y reproducibilidad | [`docs/pipeline.md`](docs/pipeline.md) |
| Respuesta a la devolución de la PreEntrega 1 | [`docs/correcciones_pe1/estado_correcciones.md`](docs/correcciones_pe1/estado_correcciones.md) |

---

## 1. Descripción del proyecto

Dos departamentos de la misma zona y con características parecidas deberían publicarse a un precio por m²
parecido. El proyecto estima, para cada aviso, un **precio esperado** según lo que tiene (superficie, antigüedad,
cochera, amenities, piso, estado declarado en el título) y dónde está, y mide la **brecha de precio**: cuánto se
aleja el precio publicado de ese valor. Los avisos con una brecha muy negativa pasan a una **lista de avisos a
investigar**; sobre esa lista, una regla con costos de entrada, refacción, venta y riesgo legal señala cuáles
dejarían margen si el precio esperado fuera el de venta.

Qué cambió en cada entrega:

- **PreEntrega 1:** un índice de confort con pesos fijos (45/30/25).
- **PreEntrega 2:** los pesos salen de los datos, como la prima que el mercado paga por cada característica dentro
  de la zona (modelo hedónico, validado fuera de muestra). H1 quedó con apoyo débil.
- **PreEntrega 3:** validación sin fuga de información, comparación contra un baseline y contra un gradient boosting,
  intervalo de predicción por aviso, hipótesis evaluadas con tests formales e intervalos, un **segundo relevamiento**
  que permite ver qué pasa con los avisos marcados, fuentes externas de transporte y entorno con cobertura de toda la
  ciudad, una regla de decisión con costos y un dashboard para el analista.

**Resultados de esta entrega** (números de `data/processed/`, regenerados el 02/11/2026 y reproducidos de cero, byte a byte, el
05/11/2026: `docs/corrida-documentada/corrida_de_cero_2026-11-05.log`)

- **Recomendación · El embudo, con sus universos reconciliados:** 27.578 avisos (25.169 unidades) analizados → 1.819 avisos
  (1.714 unidades) piden más de 25% menos que su precio esperado → 1.556 (1.470) siguen marcados con el umbral de su
  barrio → **1.455 avisos, 1.375 unidades, sin señales de error de carga: la lista oficial** → 884 avisos (840
  unidades) son candidatos después de costos en el escenario base, y **83 si se vende al límite inferior del rango
  del 80%** (`embudo_ranking.csv`).
- **Predictivo · El precio esperado es una referencia sólida, con incertidumbre grande en cada aviso.** El modelo oficial
  (lineal ampliado con el estado del título) erra 12,5% en la mediana fuera de muestra, contra 17,5% de usar la
  mediana de la zona; el gradient boosting llega a 11,3% pero no se explica aviso por aviso, así que se usa como
  segunda opinión (1.124 avisos marcados por los dos). El rango del 80% del precio esperado de un aviso es de
  alrededor de ±32% y cubre el precio publicado el 79,5% de las veces: por eso la ficha muestra un rango, no un
  número.
- **Relación estadística · H1 tiene un resultado doble.** La cola de brechas negativas no es más pesada de lo que explica el error del modelo
  (6,6% por debajo de −25% contra 7,7% por encima de +33%): la brecha no prueba precios atípicos. Pero **los avisos
  marcados salen más del portal** en los 74 días hasta el segundo relevamiento: 46,7% contra 39,7%, y dentro del
  barrio, a igual valor esperado, +9,4 puntos (IC 6,5 a 12,2), con un gradiente (cada 10 puntos más por debajo,
  +2,2 puntos de salida) y un placebo a favor (los avisos caros salen menos). Salir del portal no prueba una venta,
  pero muestra que la brecha ordena algo real.
- **Relación estadística · H2 (sub-zonas): apoyo parcial.** La sub-zona baja el error de la referencia 0,6 puntos en total (IC 0,4 a 0,85),
  con mejora significativa en 4 de 41 barrios y grande en uno (Villa Lugano). Por eso el modelo la usa barrio por
  barrio, donde mejora y es estable.
- **Relación estadística · H3 (ubicación): apoyo, menor del esperado.** Con tren, Metrobus, premetro, espacios verdes y permisos de obra,
  los bloques de transporte y entorno son significativos en conjunto, pero por variable quedan 2 de 16 con un efecto
  interpretable, y chico: +1,5% por hectárea de espacio verde a 500 m y +4,4% por cada 10 obras nuevas. El premetro
  (−24%) también sobrevive a la corrección de Holm, pero es la zona y no el premetro: sin los avisos a menos de 500 m
  de un barrio popular pasa a −4%, con un intervalo que incluye el 0. El subte a menos de 300 m da −4,8% pero no
  sobrevive a Holm (p ajustado 0,27); que la avenida pese más que la estación es una conjetura, no algo medido. En
  la PE2, con subte y centralidad, no se detectaba nada.
- **Relación estadística · El estado del inmueble pesa más de lo que parecía.** Un aviso "a reciclar" se publica 18% más barato que uno
  igual sin esa marca, y uno "a refaccionar" 16%. Entra al modelo y a la regla: una parte de la brecha es el estado,
  no una subvaluación.
- **Predictivo · Lo que mira el gradient boosting** (SHAP): la ubicación explica el 47% de la importancia; amenities y cochera,
  17%; antigüedad, 14%; tamaño, 12%. El orden es estable entre vueltas y coincide con las primas del lineal.
- **Descriptivo · Índice de equipamiento y micro-mercados (exploratorio):** sirven para describir la oferta y para marcar dónde el
  precio esperado es menos preciso; no mejoran el precio esperado ni la liquidez frente a las alternativas simples
  (amenities sueltas y cantidad de ambientes). No entran a la lista oficial.

## 2. Interlocutor y usuario

**Usuario principal: el analista de inversiones del fondo.** Revisa el flujo de avisos publicados y arma la lista
de candidatos que eleva al comité. Su problema es de volumen: hay decenas de miles de avisos activos en CABA y no
puede leerlos todos. La herramienta le devuelve una lista corta de avisos con precio atípicamente bajo para su zona y
sus características, con el rango del precio esperado, qué características lo explican, señales de qué revisar
primero (posible error de carga, baja de precio, estado, riesgo legal) y la brecha neta de costos.
El dashboard es la vista del analista: mapa, embudo, ficha del aviso y simulador de la regla (sección 9).

**Usuario secundario: el comité de inversión**, que recibe los casos ya verificados por el analista y decide la
compra. Usa además el análisis por zona para decidir dónde concentrar el capital.

## 3. Contexto de negocio

El fondo compra departamentos usados en CABA. Busca avisos publicados por debajo de lo que el mercado paga por
departamentos comparables, para después verificarlos y decidir la compra.

El mercado argentino condiciona cómo se lee un precio publicado. Resumen (detalle, fuentes y números propios en
[`contexto_argentino.md`](docs/entregas_grupo/contexto_argentino.md) y
[`costos_y_liquidez.md`](docs/entregas_grupo/costos_y_liquidez.md)):

| Rasgo | Qué implica para el análisis |
|---|---|
| **Dolarización**: 27.917 de 27.922 avisos están en USD | Los precios se comparan sin ajustar por inflación; las expensas están en pesos y se convierten con un tipo de cambio declarado |
| **Crédito hipotecario limitado** (~1% del PBI) y cíclico | El precio lo fija quien tiene dólares ahorrados. El precio esperado vale para agosto de 2026 |
| **Operaciones al contado** (85% de las escrituras de 2026) | `apto_credito` indica requisitos legales, no forma de pago. Entra al modelo como control |
| **Iliquidez**: vender lleva meses | Un precio bajo puede ser un vendedor apurado. El segundo relevamiento mide la salida del portal, que no es lo mismo que una venta |
| **Brecha publicado-cierre** de 4,79% (mínimo 4,18%) | El umbral para marcar un aviso (−25%) es mucho mayor que el margen de negociación; en la regla de decisión se compra al precio publicado y se vende al de cierre |
| **Costos de transacción** altos: entrada alrededor del 8,8% del precio (escribano, Sellos, comisión), salida alrededor del 6% | Una brecha de 25% deja menos margen del que parece: por eso existe la brecha neta |
| **Ciclos regulatorios del alquiler** | El stock en venta de 2026 no es comparable con el de 2020-2023 |

**Tipo de cambio.** Las expensas se convierten con el dólar MEP del 14/08/2026 (ARS 1.518,05 por USD, Ámbito),
porque es el tipo de cambio al que una persona convierte legalmente sus dólares a pesos. Como referencia, el A
3500 del BCRA ese día era ARS 1.488,70; la elección cambia la mediana de expensas de USD 131,7 a USD 134,3 y no
cambia el orden de los avisos dentro de una zona.

## 4. Alcance y unidad de análisis

- **Unidad de análisis:** el aviso de departamento usado en venta publicado en MercadoLibre Inmuebles. Para el
  ranking, la **unidad** (dirección y superficie): si varios avisos publican el mismo departamento, cuenta una vez,
  representada por el aviso que llega más lejos en el embudo. Los notebooks 04 y 05 agrupan por dirección y
  superficie sin mirar el piso (24.552 unidades, para armar las vueltas de la validación); el ranking separa además
  los avisos con piso declarado distinto (25.169 unidades).
- **Unidad de comparación:** la **zona de referencia**. Es la sub-zona (cluster espacial de avisos dentro del
  barrio, hasta 5 por barrio) en los barrios donde mejora la referencia de precio fuera de muestra y donde las
  sub-zonas son estables (ARI con bootstrap de 0,7 o más; hoy Villa Santa Rita no lo es y se compara entero), y el
  barrio completo en el resto. Se decide dentro de cada vuelta de la validación, sin fuga. Los avisos sin
  coordenadas, los de geocodificación dudosa (a más de 1 km del barrio buscado: 249 de los 27.922 avisos
  enriquecidos, 244 de los 27.578 limpios) y las zonas con menos de 10
  avisos se comparan contra el barrio.
- **Geográfico:** 47 categorías de barrio de MercadoLibre. No coinciden con los 48 barrios oficiales: incluyen
  "Barrio Norte" y no incluyen San Cristóbal ni Parque Chas. Se usa el barrio de búsqueda y no el polígono oficial
  porque es la categoría donde el comprador encuentra el aviso y donde el mercado forma el precio; el polígono
  oficial se usa como control (sección 13).
- **Tipología:** departamentos usados en venta. Quedan fuera casas, alquileres, avisos de compra y unidades en pozo
  (237 avisos con antigüedad negativa, se excluyen en la limpieza; otros 9 avisos de la lista de señales, 8 unidades, lo
  dicen solo en el título: la regla de decisión los descarta y el dashboard los marca). Una casa publicada como departamento sigue en el
  dataset, marcada.
- **Precio:** precio de publicación en USD, no precio de cierre. La regla de decisión descuenta la brecha
  publicado-cierre al vender.
- **Temporal:** dos fotos del mercado: el relevamiento principal del 14/08/2026 y un segundo relevamiento del 27 y
  28/10/2026, que solo se usa para seguir qué pasó con los avisos del primero.

## 5. Preguntas por nivel analítico

Versión completa, con el porqué de cada nivel, en [`preguntas_y_alcance.md`](docs/entregas_grupo/preguntas_y_alcance.md).

| Nivel | # | Pregunta (resumida) | Estado en esta entrega |
|---|---|---|---|
| Descriptivo | D1 | ¿Cómo se distribuye el precio por m² entre barrios y entre sub-zonas de un barrio? | Respondida (notebook 02); la sub-zona se evalúa formalmente en H2 (notebook 05) |
| | D2 | ¿Qué proporción de avisos declara cada característica y qué tan completo está cada aviso? | Respondida: por columna (diccionario y notebook 01) y por aviso, con la tasa de completitud (notebook 03) |
| | D3 | ¿Con qué frecuencia aparece cada característica en cada zona? | Parcial: frecuencias generales en el diccionario; por segmento de departamento en el notebook 06 |
| | D4 | ¿Cuántos avisos bajaron de precio, cuánto y dónde? | Respondida: 626 avisos (2,3%), baja mediana de 6,8% (notebooks 01, 02 y 03); entre relevamientos, 4.998 avisos bajaron más de 0,5% (notebooks 01 y 02) |
| Diagnóstico | G1 | Dentro de la zona, ¿cuánto se asocia cada característica con el precio por m²? | Respondida, ahora con intervalos por bootstrap de unidades (notebook 04, sección 6) |
| | G2 | ¿La prima de cada característica cambia según la zona o el segmento de precio? | Respondida: cambian poco por tercil de barrio y por segmento de departamento; no justifica un modelo por segmento (notebook 04, sección 7; notebook 06, sección 4.3) |
| | G3 | ¿Cuánto de la diferencia de precio se explica por accesibilidad y entorno? | Respondida (H3, notebook 05): una parte chica pero significativa, con efectos fijos de barrio |
| | G4 | ¿Qué distingue a los avisos con precio atípicamente bajo? | Respondida: errores de carga, estado del inmueble, riesgo legal, bajas de precio; y se comportan distinto en el mercado (salen más del portal). Notebooks 03, 05 y 07 |
| Predictivo | P1 | ¿Qué precio por m² se esperaría para un aviso según sus características y su zona? | Respondida (notebook 04); por aviso, con rango del 80% y explicación de qué sube y qué baja su precio esperado |
| | P2 | ¿Con qué error, y dónde es mayor? | Respondida: 12,5% en la mediana; mayor en los departamentos familiares antiguos y en los nuevos con amenities (notebook 06) y en barrios chicos del sur y el oeste |
| | P3 | ¿Qué precio se esperaría para un departamento no publicado? | Posible con el mismo modelo; no se aplicó a casos concretos |
| | P4 | Si se repite el scraping, ¿los avisos marcados salen del portal antes que sus comparables? | Respondida con el segundo relevamiento (H1b, notebook 05): sí, +9,4 puntos dentro del barrio |
| Prescriptivo | R1 | ¿Qué regla decide qué avisos pasan a revisión? | Implementada en dos niveles: **señal a investigar** (regla R1: brecha menor a −25%, umbral por barrio, sin señales de error de carga; 1.375 unidades) y **candidato después de costos** (brecha neta de costos de 10% o más y sin riesgo legal de descarte; 840 unidades, 83 en el escenario conservador). Notebook 07 y `src/regla.py` |
| | R2 | ¿Conviene ponderar distinto un aviso bien ubicado que uno periférico? | Replanteada: la ubicación ya está en el precio esperado (H3); lo que cambia por zona es la precisión, que la ficha muestra con el rango |
| | R3 | ¿En qué zonas concentrar el análisis? | Parcial: el error del modelo por barrio y por segmento indica dónde la brecha es más confiable (pestaña Tendencias del dashboard: señales por barrio) |

## 6. Hipótesis y KPIs

### Hipótesis

Las tres se evalúan en el notebook 05 con magnitud, intervalo (bootstrap por unidad o errores agrupados) y robustez,
y una tabla de tests formales por hipótesis (H0, H1, estadístico, p-valor, decisión; Holm cuando hay varias
comparaciones).

| | Hipótesis | Evidencia (PE3) | Estado |
|---|---|---|---|
| H1 | Dentro de una zona hay avisos publicados claramente por debajo del precio esperado para sus características, más allá del margen normal de negociación. Son candidatos a investigar, no oportunidades confirmadas | **H1a (colas):** 6,6% de los avisos por debajo de −25% contra 7,7% por encima de +33%; la cola de abajo no es más pesada que la de una normal con la misma dispersión (test binomial a una cola, no se rechaza H0). **H1b (salida del portal):** los marcados salen 46,7% contra 39,7%; dentro del barrio y a igual valor esperado, +9,4 pp (IC 6,5 a 12,2; logit OR 1,48); gradiente de +2,2 pp por cada 10 pp más de brecha (IC 1,6 a 2,9); placebo (brecha mayor a +33%): −8,6 pp. Se mantiene sin republicaciones y con el gradient boosting; en el tercil de barrios medios el IC incluye el 0 | **Resultado doble:** la brecha no prueba precios atípicos (H1a no), pero predice el comportamiento del aviso en el mercado (H1b sí). En la PE2 solo había H1a |
| H2 | Un barrio no es homogéneo: la sub-zona da una referencia de precio más precisa que el barrio | Con vueltas agrupadas por unidad: el error de la referencia baja de 17,7% a 17,1%, 0,6 pp (IC 0,4 a 0,85; t y Wilcoxon por unidad rechazan H0). Barrio por barrio, mejora significativa con Holm en 4 de 41 y grande en Villa Lugano; en ninguno empeora significativamente. Sub-zonas estables en 40 de 41 barrios, aunque 4 quedan cerca del umbral (ARI entre 0,7 y 0,8: Coghlan, Parque Chacabuco, Barrio Norte y Villa Pueyrredón); compararlos enteros mueve el error 0,01 pp y la lista en un aviso | Apoyo parcial: depende del barrio; el modelo la usa donde mejora y es estable |
| H3 | Parte de la diferencia de precio dentro de un barrio se explica por la ubicación: transporte, espacios verdes y dinamismo | Regresión del precio por m² con efectos fijos de barrio y errores agrupados por sub-zona: bloque de transporte p = 3,7e-5 y bloque de entorno p = 2,4e-7 (Wald); con Holm sobreviven 3 de 16 variables, pero solo 2 con un efecto interpretable: área verde a 500 m (+1,5% por ha) y permisos de obra (+4,4% por 10 obras); el premetro (−24%) sobrevive pero es un artefacto de zona (sin los avisos a menos de 500 m de un barrio popular, −4% con IC que incluye el 0) y el subte a menos de 300 m (−4,8%) no sobrevive (p ajustado 0,27). Fuera de muestra, sumar la ubicación al modelo baja el error 0,19 pp. En el sur y el oeste las obras pesan más (+12%, IC 5 a 19) y el tren queda en el borde (−10%, IC −20 a +0,1: incluye el 0) | Apoyo, menor del esperado: la zona de referencia ya capta casi todo; la ubicación explica más que lo que cambia la lista |

### KPIs

| KPI | Qué mide | Cómo se calcula | Estado |
|---|---|---|---|
| Precio por m² de la zona | La referencia simple de precio | Mediana de `precio_m2_usd` en la zona de referencia, en las otras vueltas | Calculado (`precio_m2_mediana_zona`); es el baseline del modelo |
| Prima por característica | Cuánto paga el mercado por cada característica dentro de la zona | Coeficiente del modelo oficial, en %, con IC por bootstrap de unidades | Calculado (notebook 04, sección 6) |
| Precio esperado y su rango | El precio por m² "normal" para un aviso y su incertidumbre | Predicción fuera de muestra del modelo oficial; intervalo conformal del 80% por barrio | Calculado (`precio_esperado.tsv`); cobertura 79,5% |
| Brecha de precio | Cuánto se aleja el precio publicado del esperado | `precio_m2_usd / precio_m2_esperado − 1` | Calculado |
| Error de estimación fuera de muestra | Si la brecha es señal o ruido | Mediana del error absoluto del precio esperado, por zona, barrio y segmento | Calculado: 12,5% |
| Lista de avisos a investigar | Lista priorizada para el analista | Unidades que cumplen la regla R1, con señales, estado, riesgo legal, rango y explicación | Calculado (`avisos_a_investigar.csv`, 1.375 unidades) |
| Brecha neta de costos | Margen que dejaría la operación si el precio esperado fuera el de venta | (venta de cierre − costos de salida − impuesto − costo total) / costo total, con `config/costos.yaml` | Calculado (`brecha_neta`); mediana 12,3% entre las señales; 840 candidatos |
| Tasa de salida del portal | Si los marcados se comportan distinto en el mercado | Proporción de avisos del primer relevamiento que no están en el segundo, sin republicaciones ni barrios truncados | Calculado (notebook 05): 46,7% marcados, 39,7% resto; por ambientes, como liquidez informativa en la regla |
| Tasa de completitud | Qué tan confiable es la ficha de un aviso | % de los 26 campos donde el vacío es falta de dato que tienen dato | Calculado: mediana 88%; no se asocia con la marca |
| Eficiencia de expensas | Si las expensas son altas para lo que ofrece el edificio | Expensas en USD por m², relativas a la mediana de la zona | Calculado (notebook 03) |
| Distancias de accesibilidad | Qué tan bien conectado está un aviso | Distancia al transporte pesado (subte, tren, premetro, Metrobus) y área verde a 500 m | Calculado (`accesibilidad.tsv`) y evaluado en H3 |
| Índice de equipamiento | Cuánto equipamiento declara un aviso | Primer eje de un MCA sobre 17 características Sí/No (notebook 06) | Exploratorio: casi coincide con contar amenities (correlación 0,96); no entra al modelo |

## 7. Datasets y fuentes externas

### Dataset principal

Construido por web scraping de MercadoLibre Inmuebles, extraído el 14/08/2026, y enriquecido con geocodificación
y distancias. El detalle de cada columna está en el
[diccionario de datos](docs/entregas_grupo/diccionario_datos.md).

| Archivo | Filas × columnas | Qué es |
|---|---|---|
| `data/raw/cuotas/cuota1..5.tsv` | 27.922 en total | Salida cruda del scraper, sin modificaciones |
| `data/processed/propiedades_enriquecidas.tsv` | 27.922 × 93 | Consolidado, geocodificado y con distancias y sub-zonas (etapas 1 a 4) |
| `data/processed/accesibilidad.tsv`, `permisos_obra.tsv` | 27.922 | Fuentes externas por aviso (tren, Metrobus, premetro, espacios verdes, barrio oficial, barrios populares, `geo_dudoso`, permisos de obra), por `link` |
| `data/processed/propiedades_limpias.tsv` | 27.578 × 115 | Dataset de trabajo, salida de la etapa 5 (notebook 01) |
| `data/processed/registro_limpieza.csv` | 344 | Avisos excluidos y su motivo |
| `data/processed/precio_esperado.tsv` | 27.578 × 77 | Por aviso: precio esperado, rango del 80%, brechas, marcas, estado, riesgo legal, KPIs y regla de decisión (etapa 6) |
| `data/processed/unidades_marcadas.csv` | 1.714 | Una fila por unidad con algún aviso marcado, con el paso del embudo al que llega |
| `data/processed/avisos_a_investigar.csv` | 1.375 | **La lista oficial:** unidades que cumplen la regla R1, con `nivel_decision` (señal o candidato) |
| `data/processed/embudo_ranking.csv` | 5 | El embudo por avisos y por unidades |
| `data/processed/explicacion_avisos.tsv` | 1.819 | Por aviso marcado: referencia de la zona y las 3 características que más suben y bajan su precio esperado |
| `data/raw/relevamiento_2/`, `data/processed/relevamiento_2.tsv` | 27.516 | Segundo relevamiento (27 y 28/10/2026) |
| `data/processed/seguimiento_avisos.csv` | 27.578 | Estado de cada aviso del primer relevamiento en el segundo: sigue, republicado o salió |
| `docs/dashboard/data/*.json` | 1.375 unidades | Capa de datos del dashboard, exportada de la etapa 6 (sección 9) |
| `data/processed/chequeo_comparables.csv`, `.json` | 486 destacados | Chequeo del precio esperado contra comparables simples (sección 10) |

**Del crudo al limpio.** Se excluyen 344 avisos: 68 duplicados por ID de aviso (entre dos filas del mismo ID queda
la que coincide con el polígono oficial del barrio; en 17 de los 68 la regla de la PE2, primera aparición, se quedaba
con la otra fila y en 12 eso cambiaba el barrio), 237 en pozo, 28 con superficie inválida, 5 con precio en pesos,
4 con precio menor a USD 20.000, 1 con precio imposible y 1 que es una compra, no una venta. Se corrigen 627 precios
concatenados por "BAJÓ DE PRECIO", baños en 0 y pisos cargados como número de unidad; las expensas de relleno
(menos de ARS 1.000) pasan a sin dato; se unifican etiquetas mal cargadas y se marcan, sin borrarlos, posibles
duplicados con otro ID (3.059), atípicos de precio por m² (931), casas publicadas como departamento, menciones de
barrios populares e incoherencias entre variables. Todo está justificado en el notebook 01, y la etapa 5 del pipeline
reproduce exactamente ese resultado.

| Métrica (dataset limpio) | Valor |
|---|---|
| Avisos | 27.578 (25.169 unidades) |
| Con coordenadas | 82,1% (menos 249 de geocodificación dudosa) |
| Mediana de precio | USD 130.000 |
| Mediana de precio por m² | USD 2.393 |
| Mediana de superficie | 57 m² |

### Fuentes externas

Fichas completas, con el formato del enunciado (fuente, cobertura, período, granularidad, unión, variable, aporte
y límites), en [`fuentes_externas.md`](docs/entregas_grupo/fuentes_externas.md); controles de cada una (conteos,
distancias por barrio, aporte) en [`control_fuentes.md`](docs/entregas_grupo/control_fuentes.md). Todas son
snapshots versionados en `data/external/`, con SHA-256: el pipeline corre sin red.

| Fuente | Granularidad | Variable | Uso |
|---|---|---|---|
| Normalizador de direcciones USIG (GCBA) | Punto | `lat`, `lon` | Ubica cada aviso |
| Estaciones de subte (BA Data) | Punto | `dist_transporte_m` | H3, modelo con ubicación |
| Polos de centralidad (definición propia) | Punto | `dist_centralidad_m` | PE2; sin efecto |
| Dólar MEP del 14/08/2026 | Un valor | `expensas_usd` | KPI de expensas |
| Estaciones de ferrocarril (BA Data) | Punto | `dist_tren_m` | H3 (integrada en PE3) |
| Metrobus (BA Data) | Punto | `dist_metrobus_m` | H3 (integrada en PE3) |
| Premetro (BA Data) | Punto | `dist_premetro_m` | H3, robustez en el sur (integrada en PE3) |
| Espacios verdes (BA Data) | Polígono | `dist_espacio_verde_m`, `area_verde_500m_ha` | H3 (integrada en PE3) |
| Polígonos de barrios (BA Data) | Polígono | `barrio_oficial`, `barrio_coincide`, `geo_dudoso` | Control de calidad: duplicados por ID y geocodificación dudosa (integrada en PE3) |
| Barrios populares (BA Data) | Polígono | `en_barrio_popular`, `tipo_barrio_popular` | Alerta en la ficha; robustez de H3 (integrada en PE3) |
| Permisos de obra (BA Data) | Punto | `permisos_obra_500m` | H3, dinamismo de la zona (integrada en PE3) |
| Costos de transacción, refacción, liquidez y riesgo legal (UCEMA, Colegio de Escribanos, AGIP, cámaras del sector) | Parámetros | `config/costos.yaml` | Regla de decisión (PE3) |

## 8. Estructura del repositorio

```
├── README.md
├── requirements.txt                 Dependencias con versiones fijadas (Python 3.9 de referencia)
├── run_pipeline.py                  Runner del pipeline: etapas 1 a 6
├── config/
│   ├── config.yaml                  Rutas y parámetros de todas las etapas y de las fuentes externas
│   └── costos.yaml                  Costos de entrada, refacción, venta, liquidez, estado y riesgo legal, con fuentes
├── data/
│   ├── raw/cuotas/                  Salida cruda del scraper (14/08/2026)
│   ├── raw/relevamiento_2/          Salida cruda del segundo relevamiento (27 y 28/10/2026)
│   ├── interim/                     Consolidado, geocodificado y el SHAP guardado
│   ├── processed/                   Enriquecido, fuentes externas, limpio, etapa 6 y seguimiento
│   └── external/                    Snapshots de BA Data (subte, tren, Metrobus, premetro, verdes, barrios, obras)
├── notebooks/
│   ├── 01_calidad_y_limpieza.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_precio_esperado.ipynb
│   ├── 04_validacion_modelos.ipynb
│   ├── 05_hipotesis.ipynb
│   ├── 06_segmentos_exploratorio.ipynb
│   └── 07_regla_de_decision.ipynb
├── src/
│   ├── scrapper_mercadolibre.py     Etapa 1
│   ├── unir_cuotas.py               Etapa 2
│   ├── geocoding_propiedades.py     Etapa 3
│   ├── enriquecimiento.py           Etapa 4 (subte, centralidad, sub-zonas)
│   ├── limpiar.py, limpieza.py      Etapa 5 (notebook 01)
│   ├── analisis.py                  Etapa 6: precio esperado, intervalo, marcas, regla, ranking, embudo, explicación
│   ├── modelo.py                    Modelo hedónico y validación cruzada por unidad sin fuga
│   ├── validacion.py                Comparación de modelos, conformal, estabilidad, bootstrap, explicación (lineal y SHAP)
│   ├── regla.py                     Regla de decisión con costos
│   ├── inferencia.py                Bootstrap por unidad, tests, Holm, coeficientes (notebook 05)
│   ├── segmentos.py                 MCA y K-means exploratorios (notebook 06)
│   ├── fuentes_externas.py          Tren, Metrobus, premetro, verdes, barrios, barrios populares, geo_dudoso
│   ├── permisos_obra.py             Permisos de obra a 500 m
│   ├── seguimiento.py               Segundo relevamiento y seguimiento de avisos
│   ├── exportar_dashboard.py        Capa de datos del dashboard
│   ├── eda.py                       Funciones del análisis exploratorio
│   ├── indice_confort.py            Índice de la PreEntrega 1, usado en el diagnóstico de la devolución
│   └── rutas.py, configuracion.py, entorno.py, qc.py
├── tests/                           191 tests (pytest), corren en GitHub Actions con Python 3.9
├── outputs/logs/                    Logs y controles de calidad de cada corrida (no versionados)
└── docs/
    ├── dashboard/                   Dashboard estático (GitHub Pages) y su capa de datos
    ├── entregas_grupo/              Contexto, preguntas, diccionario, fuentes externas, controles, costos
    ├── correcciones_pe1/            Diagnóstico de la devolución de la PE1 y estado de las correcciones
    ├── pipeline.md                  Pipeline: instalación, ejecución, controles, tests y limitaciones técnicas
    ├── proceso_tecnico.md           Desafíos técnicos del scraping
    ├── corrida-documentada/         Evidencia de la corrida del pipeline
    └── caso_de_negocio.pdf          Documento de negocio de la PreEntrega 1
```

## 9. Cómo reproducir el análisis

Requiere Python 3.9 a 3.12; la versión de referencia es 3.9 (es la de la CI y la de los archivos versionados).

```bash
git clone https://github.com/gbuhler-itba/TP-Analitica-Descriptiva.git
cd TP-Analitica-Descriptiva
python3 -m venv .venv && source .venv/bin/activate    # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 -m pytest -q                                   # 191 tests, unos 2 minutos, sin red
```

**Todos los datasets vienen versionados**, así que los notebooks se pueden abrir y ejecutar directamente con el
kernel del entorno virtual. Para regenerar las salidas desde el dataset enriquecido:

```bash
python3 run_pipeline.py --desde-etapa 5     # limpieza (etapa 5) y análisis (etapa 6), unos 3 minutos
python3 src/exportar_dashboard.py           # capa de datos del dashboard
```

El pipeline completo, las fuentes externas, el segundo relevamiento, el orden en que hay que correr cada script y
los controles de calidad están en [`docs/pipeline.md`](docs/pipeline.md). El scraping (8 a 15 horas, desde una IP
residencial) solo corre con `--incluir-scraping` y no hace falta repetirlo.

### Mapa de notebooks: qué leer y en qué orden

Los notebooks leen las salidas del pipeline y las explican; no generan la lista oficial (la genera la etapa 6, para
que el resultado no dependa de una celda). Orden de lectura sugerido para corregir:

| Orden | Notebook | Qué responde | Qué pide la consigna de la PE3 |
|---|---|---|---|
| 1 | `01_calidad_y_limpieza` | Qué se limpió y por qué; verifica que coincide con la etapa 5 | Repo reproducible |
| 2 | `04_validacion_modelos` | Fuga indirecta, estabilidad de sub-zonas, **modelos comparados contra el baseline fuera de muestra** (mediana de la zona, lineal, lineal ampliado, Ridge, gradient boosting), intervalo de predicción, primas con IC, primas por segmento, **SHAP** | Técnicas avanzadas con supuestos, validación, qué agregan y límites; modelos contra baseline |
| 3 | `05_hipotesis` | **H1, H2 y H3 con magnitud, IC, robustez y tests formales**; el segundo relevamiento | Hipótesis evaluadas con estadística |
| 4 | `07_regla_de_decision` | De señal a candidato: costos, refacción por estado, riesgo legal, liquidez, **sensibilidad y escenario conservador** | Regla de decisión con costos, liquidez, estado y riesgo (devolución de la PE2) |
| 5 | `06_segmentos_exploratorio` | Índice con MCA y micro-mercados con K-means: codo, silhouette, **estabilidad (ARI 0,99)**, nombres, utilidad frente a la alternativa simple, y por qué no entran a la lista | Segmentos e índices con estabilidad verificada; qué agrega frente a lo simple |
| 6 | `02_eda`, `03_precio_esperado` | El análisis exploratorio y el modelo de la PE2, con los números actualizados a la limpieza nueva (banner al principio) | Contexto |

### El dashboard: "Radar de avisos · CABA"

Publicado en [https://gbuhler-itba.github.io/TP-Analitica-Descriptiva/dashboard/](https://gbuhler-itba.github.io/TP-Analitica-Descriptiva/dashboard/). Código y datos en [`docs/dashboard/`](docs/dashboard/). Está pensado para el analista
del fondo, no para quien corrige: no repite los notebooks, los resume en una decisión. Tiene cinco pestañas y una ficha.
Si el link no responde, el dashboard también corre en local: desde la raíz del repo, `python3 -m http.server -d docs 8000`
y abrir http://localhost:8000/dashboard/.

| Pestaña | Qué muestra |
|---|---|
| Resumen | Una línea que recuerda que son señales a revisar y no oportunidades, y que la mitad ya no estaba publicada al 28/10; los indicadores (avisos analizados, señales, candidatos, candidatos firmes, error del modelo) con un subtítulo corto cada uno, la lista "los que más vale la pena mirar" (candidatos de los dos modelos, sin barrio popular a menos de 500 m, casas o PH, usos comerciales, oficinas u hoteles, avisos sin coordenadas con otro barrio en el título, posibles ventas de varias unidades, precio posiblemente con financiación ni en pozo; esos siguen en el mapa y el buscador con su alerta; cada aviso que salió del portal o fue republicado lo dice al final de su título) y el embudo |
| Mapa | Todos los avisos de fondo en gris, señales, candidatos y firmes con color y forma propios, filtro por barrio y capas de subte, tren, Metrobus y premetro; el clic abre la ficha |
| Buscador | Filtros por barrio, ambientes, precio, m², estado del título, nivel, riesgo legal, consenso de modelos, alertas ("sin alertas" viene tildado; quien quiera ver los casos especiales lo destilda, y esos avisos van siempre al final) y "solo los que seguían publicados al 28/10" (los republicados cuentan como publicados); mismo orden que el resumen |
| Tendencias | La tasa de salida del portal por decil de brecha (H1), el error del modelo por barrio (dónde la brecha es más confiable), señales por barrio, la sensibilidad de la regla y el simulador "¿y si…?" (negociación, costos, refacción, Ganancias, margen mínimo y valor de salida) |
| Cómo leer este tablero | La advertencia completa, qué es cada nivel, qué se excluye de la lista destacada, los límites en palabras simples y los links a los notebooks |
| Ficha del aviso | Publicado contra esperado con el rango del 80%, qué suma y qué resta, la cascada de costos hasta la brecha neta, alertas, consenso, liquidez por ambientes y el link al aviso, que avisa si ya no estaba publicado o fue republicado al 28/10 |

El tercer nivel, **candidato firme**, es el escenario conservador del notebook 07 (candidato aun vendiendo al piso del
rango del 80%: 83 unidades) calculado por unidad en `src/exportar_dashboard.py`.

**La lista destacada es un filtro de presentación sobre la lista oficial, no un resultado del análisis.** Parte de los
664 candidatos que marcan los dos modelos y aparta los casos donde el comparable del modelo (un departamento común de
su zona) puede no aplicar: barrio popular o a menos de 500 m de uno, casa o PH, uso comercial, oficina u hotel, barrio
dudoso en el título, posible venta de varias unidades, precio posiblemente con financiación y en pozo. Son 178 de los
664; quedan 486 destacados (38 firmes). Los 500 m son un criterio de prudencia, no un resultado: el modelo no ve el
entorno inmediato y el precio de un departamento pegado a un barrio popular responde a cosas que el modelo no mide.
Es la exclusión que más saca (106 candidatos, 99 solo por eso) y pega sobre todo en el sur. Los apartados siguen en
el mapa y en el buscador con su alerta, y nada de esto cambia las 1.375 señales ni los 840 candidatos.

**Por qué una página estática y no una herramienta de BI.** El criterio fue el del profesor: lo más fácil de armar,
mantener y desplegar con nuestro modelo de datos y nuestro volumen. El dashboard es HTML, CSS y JavaScript sin
dependencias de build (solo Leaflet para el mapa) que lee los JSON que genera el pipeline (`docs/dashboard/data/`,
2,6 MB para 1.375 unidades y el fondo de 22.389 puntos). Se actualiza con regenerar los datos, un test
(`tests/test_exportar_dashboard.py`) verifica que los números coinciden con el embudo y el ranking de la etapa 6, el
simulador reproduce la regla de `src/regla.py` y da los mismos conteos que la sensibilidad del notebook 07, y GitHub
Pages lo publica gratis con un link público desde el mismo repo, así que versionar el dashboard es versionar el
trabajo. Se evaluó **Power BI**: pide una licencia y Windows para el escritorio, el archivo `.pbix` queda fuera del
repo y no se regenera desde el pipeline, y publicarlo con link público requiere "publicar en la web" o licencias Pro
para cada lector. Se evaluó **Databricks**: un workspace y un clúster son una infraestructura que hay que mantener y
pagar para 27.578 filas que entran en 26 MB, y el tablero no es público sin acceso al workspace. Ninguna de las dos
mejoraba la experiencia del analista para este volumen y las dos rompían la reproducibilidad del repo.

## 10. Cambios a partir de la devolución de la PreEntrega 2

| Observación de la devolución | Qué se hizo | Dónde |
|---|---|---|
| Universos del ranking sin reconciliar (1.704, 1.434, 1.225, 1.590, 1.150) | Un embudo único por avisos y por unidades, generado por la etapa 6, que todos los documentos citan: 27.578 / 25.169 → 1.819 / 1.714 → 1.556 / 1.470 → 1.455 / 1.375 → 884 / 840 | `embudo_ranking.csv`; notebooks 03 (banner) y 07; dashboard |
| H3 incompleta: faltaban tren, Metrobus y espacios verdes | Integradas con premetro, barrios populares y permisos de obra, como snapshots versionados con controles; H3 reevaluada con efectos fijos de barrio y errores agrupados por sub-zona | `src/fuentes_externas.py`, `control_fuentes.md`, notebook 05 |
| Estabilidad de las sub-zonas | ARI con 100 remuestreos por barrio dentro de cada vuelta; un barrio inestable (ARI < 0,7) se compara entero. Hoy, Villa Santa Rita | Notebook 04, sección 3 |
| Fuga indirecta (atípicos y elección de zona con todos los datos) | Todas las decisiones se toman dentro de cada vuelta, con atípicos sobre el log; el error casi no cambia, la lista cambia en el borde | Notebook 04, sección 2 |
| Validación temporal con un segundo relevamiento | Scraping del 27 y 28/10/2026 y seguimiento de cada aviso (sigue, republicado, salió), con republicaciones detectadas por dirección, m² y ambientes y barrios truncados excluidos | `src/seguimiento.py`, notebook 05 (H1b) |
| Tests formales | Tabla por hipótesis con H0, H1, estadístico, p-valor y decisión; bootstrap por unidad; Holm | `src/inferencia.py`, notebook 05 |
| Costos de refacción, liquidez, estado y riesgo legal en una regla de decisión | Regla en dos niveles con `config/costos.yaml` (cada valor con fuente y rango), estado del inmueble desde el título, 11 señales de riesgo legal, liquidez por ambientes del seguimiento, sensibilidad | `src/regla.py`, notebook 07 |
| Mantener "señal a investigar" separado de "oportunidad" | Dos niveles explícitos en todos los archivos y textos: señal a investigar y candidato después de costos; nunca "oportunidad confirmada" | `nivel_decision` |
| H1 con apoyo débil | H1 dividida en H1a (colas, no se sostiene) y H1b (salida del portal, se sostiene) | Notebook 05, sección 2 |
| Errores residuales de la limpieza (baños en 0, pisos como número de unidad, expensas de relleno, casas) | Corregidos o marcados en la etapa 5; duplicados por ID resueltos con el polígono oficial | Notebook 01, diccionario |
| Modelos predictivos contra un baseline, fuera de muestra | Cinco modelos sobre las mismas vueltas; el lineal ampliado es el oficial por ser explicable aviso por aviso; el gradient boosting, segunda opinión | Notebook 04, sección 4 |
| Técnicas de clase (PCA/MCA, K-means) | Índice de equipamiento con MCA y micro-mercados con K-means, con estabilidad y utilidad frente a la alternativa simple; conclusión: describen, no mejoran el modelo | Notebook 06 |

**Chequeo con comparables** (`src/chequeo_comparables.py`; salida en `data/processed/chequeo_comparables.csv` y
`.json`): para cada destacado se buscaron en la base departamentos
del mismo barrio con ±1 ambiente, ±30% de superficie y ±15 años de antigüedad, excluida la propia unidad y los
atípicos. En los 425 destacados con al menos 5 comparables, el precio esperado queda en la mediana 1,9% por encima
de la mediana de los comparables, y el 83% sigue estando 25% o más por debajo de ellos (los 33 firmes con
comparables, todos). Por segmento, el esperado queda más alto en "Nuevos con amenities" (+11,8%, en parte porque los
comparables no distinguen amenities y el modelo sí) y en "Familiares amplios y antiguos" (+5,4%), consistente con el
mayor error del modelo en esos dos segmentos.

**Encontrado además en esta entrega:** 17 de los 68 duplicados por ID en los que la PE2, al quedarse con la primera
aparición, conservaba la fila equivocada (12 cambiaban de barrio), 249 avisos geocodificados a más de 1 km de su
barrio (244 en el dataset limpio; una calle homónima en otro barrio), y que la asignación de las
vueltas de la validación depende del orden de las filas del dataset (`docs/pipeline.md`, sección 10).

La respuesta a la devolución de la PreEntrega 1 (rutas, parametrización, pesos fijos, contexto, fuentes) sigue en
[`estado_correcciones.md`](docs/correcciones_pe1/estado_correcciones.md).

## 11. Técnicas utilizadas

Una fila por técnica, con lo que pide la consigna: qué resuelve, supuestos, validación, qué agrega frente a una
alternativa más simple y su límite principal. Los números son los de los notebooks indicados.

| Técnica | Qué problema resuelve | Supuestos o transformaciones | Cómo se valida | Qué aporta frente a la alternativa simple (y cuál es) | Limitación principal | Dónde |
|---|---|---|---|---|---|---|
| Modelo hedónico lineal ampliado (oficial) | El precio por m² esperado de cada aviso según sus características, su zona y el estado del título | Log del precio por m²; primas aditivas en log; atípicos marcados sobre el log dentro de la zona y solo con el entrenamiento | 5 vueltas agrupadas por unidad, sin fuga: error mediano fuera de muestra 12,5% | Contra la mediana de la zona (17,5%): 5 puntos menos de error, y cada prima se explica, con una explicación por aviso exacta | Erra más en "Familiares amplios y antiguos" (14,3%), donde el esperado tiende a quedar alto; por aviso, el rango es de alrededor de ±32% | Notebook 04 (secciones 4 y 6), `src/modelo.py` |
| Gradient boosting con SHAP | Una segunda opinión no lineal sobre el precio esperado, y qué mira ese modelo | Sin forma funcional; barrio como categórica nativa; SHAP por permutación (el TreeExplainer da valores errados con esa categórica) | Mismas vueltas: 11,3%; el orden de los bloques de importancia es estable entre vueltas (Spearman mínimo 0,98) | 1,2 puntos menos de error que el lineal ampliado; el consenso de los dos modelos (1.124 avisos; Jaccard 0,52) es la marca de robustez del dashboard | No se explica aviso por aviso, por eso no es el oficial; SHAP explica al modelo, no causas | Notebook 04 (secciones 4 y 9), `src/validacion.py` |
| Intervalo conformal del 80% | Cuánto puede equivocarse el precio esperado en un aviso concreto, en su barrio | Cuantiles de los residuos fuera de muestra de las otras vueltas, dentro del barrio (50 avisos o más; si no, toda la ciudad); no supone normalidad | Cobertura fuera de muestra 79,5% para un nivel nominal de 80%, en total y por barrio | Frente a un único número o a un ±25% fijo: un rango por aviso (ancho mediano de alrededor de ±32%) que define el candidato firme (83 unidades) | El rango es ancho: ordena avisos, no tasa uno | Notebook 04 (sección 5), `src/validacion.py`, columnas `precio_m2_esperado_inf` y `_sup` |
| H1b: modelo lineal de probabilidad y logit con efectos fijos de barrio | Si los avisos marcados salen más del portal que sus comparables, a igual valor esperado | Controla el log del valor esperado, el log de m² y la baja de precio previa (no el precio publicado, que es un mal control); errores agrupados por unidad; sin los 4 barrios truncados | Robustez sin republicaciones, con la brecha del gradient boosting y por terciles de barrio; placebo con brecha mayor a +33%: −8,6 pp | Frente a la diferencia bruta (46,7% contra 39,7%): +9,4 pp dentro del barrio (IC 6,5 a 12,2; OR 1,48) y un gradiente de +2,2 pp por cada 10 pp más de brecha | Salir del portal no es venderse (venta, retiro o republicación no detectada); en el tercil de barrios medios el IC incluye el 0 | Notebook 05 (H1), `src/inferencia.py`, `src/seguimiento.py` |
| H3: regresión con efectos fijos de barrio y errores agrupados, Wald y Holm | Cuánto de la diferencia de precio dentro de un barrio se explica por transporte, espacios verdes y obras | Log del precio por m²; distancias y entorno a 500 m; errores agrupados por sub-zona; avisos con geocodificación dudosa excluidos | Wald por bloque (transporte p = 3,7e-5, entorno p = 2,4e-7); Holm por variable; fuera de muestra, la ubicación baja el error 0,19 pp | Frente a la PE2 (subte y centralidad, sin detectar nada): 2 de 16 efectos interpretables, +1,5% por ha de espacio verde y +4,4% por cada 10 obras | Efectos chicos; el premetro (−24%) es un artefacto de zona (barrios populares), no una causa | Notebook 05 (H3), `src/fuentes_externas.py`, `src/inferencia.py` |
| MCA (índice de equipamiento) | Resumir 17 características Sí/No en un índice de equipamiento | El vacío se lee como "No" (el MCA ingenuo medía la completitud del aviso: −0,94); se usa el primer eje | Correlación 0,99 con el índice calculado solo en avisos completos; 0,96 con el conteo de amenities | Frente a contar amenities: hace aparecer el segmento "Nuevos con amenities", que con el conteo se diluye, y en el modelo le gana al conteo por 0,15 pp | No mejora el precio esperado: sube el error 0,19 pp (IC 0,09 a 0,26) frente a las amenities sueltas, así que no entra al modelo | Notebook 06 (secciones 2 y 5), `src/segmentos.py` |
| K-means (tipos de departamento) | Describir la oferta en tipos de departamento y ver dónde el precio esperado es menos preciso | K = 4 (sin codo claro; silhouette parecida entre 2 y 6) sobre tamaño, antigüedad, índice y precio esperado estandarizados | Estabilidad con bootstrap: ARI 0,99 en 100 remuestreos (umbral de clase 0,8), tamaños que se mueven menos de 0,5 pp; silhouette 0,22 | Frente a terciles de barrio y ambientes: una mirada que la ubicación no da (ARI 0,045 con los terciles); error del modelo 14,3% y 13,4% en dos tipos contra 11,9% en el resto, y la alerta de sesgo del dashboard | No son grupos separados (silhouette 0,22); para la liquidez no le ganan a las ambientes; no entran a la lista oficial | Notebook 06 (secciones 3 a 5), `src/segmentos.py`, alerta en la ficha del dashboard |

## 12. Regla de decisión: de señal a candidato

### Cómo se arma la lista de señales

Tres pasos, con los números del embudo (`embudo_ranking.csv`, por avisos):

1. **Brecha menor a −25%** respecto del precio esperado del modelo oficial: 1.819 avisos (1.714 unidades).
2. **Umbral según el error de su barrio.** El −25% de la ciudad equivale a 2 veces el error mediano del modelo
   (12,5%); en cada barrio se exige lo mismo, 2 veces su propio error mediano, para no marcar de más donde el modelo
   se equivoca más. El umbral va de −16,5% (Villa General Mitre) a −36,4% (Parque Avellaneda); los 4 barrios con
   menos de 50 avisos usan el error de la ciudad. Saca 263 avisos: quedan 1.556 (1.470 unidades).
3. **Sin señales de error de carga.** Se apartan los avisos donde el dato parece mal cargado: m² por ambiente fuera
   del percentil 1 a 99 de la ciudad (51 avisos entre los marcados), dormitorios incoherentes con los ambientes (37),
   piso incoherente con el edificio (8), mención de alquiler en el título (7) o superficie recuperada del total (3).
   Saca 101 avisos: quedan **1.455 avisos, 1.375 unidades: la lista oficial**.

Las definiciones están en `src/analisis.py` (`marca_por_barrio`, `senales_error_carga`).

La lista oficial son **señales a investigar**. Para cada una, la regla (`src/regla.py`, notebook 07) calcula qué
dejaría comprarla al precio publicado, refaccionarla según el estado declarado en el título y venderla al precio
esperado descontando la brecha publicado-cierre (4,79%), con los costos de entrada (escribano, Sellos con su umbral,
comisión), de salida (comisión del vendedor, mitad de Sellos, certificados) y el impuesto a las ganancias:

> brecha neta = (venta de cierre − costos de salida − impuesto − costo total) / costo total

Una señal pasa a **candidato después de costos** si la brecha neta es de 10% o más y el título no tiene una señal de
riesgo legal de descarte (en pozo, nuda propiedad, parte indivisa, sin escritura). Las señales de revisión (con
inquilino, con financiación, no apto crédito, sucesión) se muestran, no descartan.

| Escenario | Candidatos (unidades) |
|---|---|
| Base (valores centrales, Ganancias 0%) | **840** de 1.375 señales |
| Costos optimistas / pesimistas | 1.344 / 519 |
| Refacción baja / alta | 1.317 / 359 |
| Ganancias 15% / 35% | 721 / 547 |
| Umbral 0% / 20% | 1.349 / 358 |
| **Conservador: se vende al límite inferior del rango del 80%** | **83** |

El escenario conservador es el mensaje central: con la incertidumbre del precio esperado tomada en serio, quedan 83
unidades. El impuesto a las ganancias se deja en 0 en el escenario base porque depende de la forma jurídica del fondo
(supuesto declarado; el simulador muestra 15% y 35%). La liquidez entra como información (tasa de salida del portal
por cantidad de ambientes), no como filtro: en esta versión no modifica la regla. El costo de tenencia (expensas,
impuestos y meses hasta la venta) no está en la regla y es un límite declarado; una sensibilidad que lo descuente
queda para la entrega final.
El simulador del dashboard (pestaña Tendencias) permite cambiar escenario de costos, negociación, refacción,
Ganancias, margen mínimo y valor de salida, y reproduce exactamente estos conteos.

## 13. Limitaciones

- **Precio publicado, no de cierre.** La brecha se mide contra precios publicados; la regla descuenta 4,79% al vender,
  pero compra al publicado (supuesto conservador).
- **Error del modelo.** Un error mediano de 12,5% y un rango del 80% de alrededor de ±32% sirven para ordenar avisos,
  no para tasar uno ni para separar un precio atípico de un error de estimación (H1a). En los departamentos familiares
  antiguos y en los nuevos con amenities el error es mayor (notebook 06). Además, en los familiares amplios y antiguos el
  modelo marca el doble de avisos (11,1% contra 5,2% a 6,5%) con una brecha mediana de −3,1%: el precio esperado tiende
  a quedar alto ahí y parte de esas señales puede ser sesgo del modelo, no un precio bajo.
- **Salir del portal no es venderse.** La tasa de salida (H1b) mezcla ventas, retiros y republicaciones no detectadas
  (las detectadas, por dirección, m² y ambientes, son cerca de un cuarto de los avisos). Dos relevamientos separados
  por 74 días no permiten medir tiempos de venta.
- **Barrio de búsqueda contra barrio oficial.** El análisis usa el barrio de MercadoLibre, que es donde el comprador
  encuentra el aviso y donde el mercado forma el precio, pero no es el polígono oficial: **4.225 de los 22.912 avisos
  geocodificados (18,4%) caen en otro polígono**, casi todos de borde (a menos de 1 km), y 249 (244 en el limpio) a más de 1 km, que se
  tratan como sin coordenadas. El polígono oficial se usa como control (duplicados, geocodificación dudosa), no como
  zona. Además, "Barrio Norte" no es oficial y San Cristóbal y Parque Chas no tienen categoría.
- **Características declaradas, no verificadas.** El estado del inmueble y el riesgo legal salen del título (expresiones
  regulares): un aviso que no lo dice se trata como "sin marca". En las columnas que solo muestran "Sí", el vacío no
  distingue "no tiene" de "no se cargó".
- **Geocodificación desigual.** El 17,9% de los avisos no tiene coordenadas, y la pérdida varía por barrio. Esos
  avisos se comparan contra su barrio y quedan fuera de H3.
- **Barrios truncados.** Palermo, Belgrano, Caballito y Recoleta llegaron al tope de paginación (2.016 avisos): son una
  muestra de la oferta, no el total, y se excluyen del análisis de salida.
- **Costos como supuestos.** Los costos vienen de fuentes públicas con un rango, no de operaciones del fondo; Ganancias
  en 0 y sin costo de tenencia. La sensibilidad (notebook 07) muestra cuánto cambia el resultado con cada supuesto.
- **La liquidez no modifica la regla.** La tasa de salida del portal por ambientes se muestra como referencia, pero ni
  la liquidez ni el costo de tenencia cambian la brecha neta en esta versión; la sensibilidad con costo de tenencia
  queda para la entrega final.
- **Reproducibilidad.** La asignación de las vueltas depende del orden de las filas del dataset, y el gradient boosting
  puede variar un poco entre plataformas; la lista oficial no depende de él. Detalle en `docs/pipeline.md`, sección 10.
- **Sub-zonas cerca del umbral de estabilidad** dependen de la semilla: la estabilidad es una señal, no una
  clasificación exacta.
