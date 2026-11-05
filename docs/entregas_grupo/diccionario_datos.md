# Diccionario de datos

*Analítica Descriptiva (ITBA, 2026 C2) · PreEntrega 2, actualizado en la PreEntrega 3*

Describe el dataset de trabajo, `data/processed/propiedades_limpias.tsv` (27.578 filas × 115 columnas), que sale de la
etapa 5 del pipeline (`src/limpiar.py`, la misma lógica que explica el notebook 01), y los archivos que se derivan de él.
Tiene dos partes:

- **Las 93 columnas originales** del pipeline (`propiedades_enriquecidas.tsv`), una fila por columna, con significado,
  tipo, unidad, fuente y transformaciones, como pide el enunciado. Las cifras de **Con dato** y **Observaciones** se
  calcularon sobre las 27.922 filas antes de la limpieza, para mostrar los problemas que tuvo que resolver.
- **Las 22 columnas que crea la limpieza** (etapa 5, notebook 01), las de las fuentes externas por aviso de la PreEntrega 3
  (`accesibilidad.tsv`, `permisos_obra.tsv`), las de la etapa 6 (precio esperado, intervalo, marcas, regla de decisión y
  ranking) y las del seguimiento con el segundo relevamiento, con su fórmula final.

Al final, un resumen de anomalías con lo que se hizo con cada una.

## El dataset

| Campo | Detalle |
|---|---|
| Archivo de entrada | `data/processed/propiedades_enriquecidas.tsv`: 27.922 filas × 93 columnas |
| Archivo de trabajo | `data/processed/propiedades_limpias.tsv`: 27.578 filas × 115 columnas (93 originales + 22 nuevas). Los 344 avisos excluidos y su motivo están en `data/processed/registro_limpieza.csv` |
| Fuentes externas por aviso (PE3) | `data/processed/accesibilidad.tsv` (tren, Metrobus, premetro, espacios verdes, barrio oficial, barrios populares, `geo_dudoso`) y `data/processed/permisos_obra.tsv`, con `link` como clave |
| Salidas de la etapa 6 | `data/processed/precio_esperado.tsv` (una fila por aviso: precio esperado, intervalo, brecha, marcas, estado, riesgo legal y regla de decisión), `unidades_marcadas.csv`, `avisos_a_investigar.csv` (la lista oficial, una fila por unidad), `embudo_ranking.csv` y `explicacion_avisos.tsv` |
| Segundo relevamiento (PE3) | `data/processed/relevamiento_2.tsv` (27.516 avisos del 27 y 28/10/2026) y `seguimiento_avisos.csv` (estado de cada aviso del primero en el segundo) |
| Formato | Texto separado por tabulaciones, UTF-8. El enriquecido tiene BOM (se lee con `utf-8-sig`); el limpio, no |
| Unidad de observación | Un aviso de departamento usado en venta, publicado en MercadoLibre Inmuebles, en CABA |
| Fecha de extracción | 14/08/2026, declarada por el grupo. El dataset no tiene una columna de fecha. El segundo relevamiento es del 27 y 28/10/2026 (74 días después) y sí la tiene (`fecha_relevamiento`) |
| Filtros de la búsqueda | Departamentos, venta, propiedades individuales, usados; 47 barrios en 5 cuotas (`config.yaml`) |
| Geocodificación | Normalizador de USIG, consultado en septiembre de 2026 |
| Estaciones de subte | Snapshot de BA Data del 14/09/2026 (90 estaciones) |
| Otras fuentes de BA Data (PE3) | Tren, Metrobus, premetro, espacios verdes, barrios, barrios populares y obras registradas: snapshots del 27 y 28/10/2026 en `data/external/`, con SHA-256 en `fuentes_externas.md` |
| Origen de las cifras | Las 93 columnas originales: perfil calculado sobre `propiedades_enriquecidas.tsv`, sin modificarlo. Las columnas nuevas: sobre `propiedades_limpias.tsv` |

## De dónde sale cada columna

| Etapa | Script y función | Columnas | Cantidad |
|---|---|---|---|
| 1. Scraping, tarjeta del listado | `scrapper_mercadolibre.py`, `extraer_propiedad()` | `tipo` a `link` (posiciones 1 a 13) | 13 |
| 1. Scraping, parámetro de búsqueda | `scrapper_mercadolibre.py`, `scrapear_barrio()` | `barrio` | 1 |
| 1. Scraping, ficha de detalle | `scrapper_mercadolibre.py`, `parsear_caracteristicas()` | `superficie_total` a `cancha_de_basquetbol` (posiciones 15 a 86). Además completa `ambientes`, `dormitorios` y `banos` | 72 |
| 2. Consolidación | `unir_cuotas.py` | Ninguna nueva: une los esquemas de las 5 cuotas (86 columnas) | 0 |
| 3. Geocodificación | `geocoding_propiedades.py` | `dir_limpia`, `lat`, `lon`, `geo_status` | 4 |
| 4. Enriquecimiento | `enriquecimiento.py` | `dist_transporte_m`, `dist_centralidad_m`, `subzona` | 3 |
| | | **Total** | **93** |

## Cómo leer el diccionario

**Vacío.** Celda vacía en el TSV, que pandas lee como `NaN`.

**Con dato.** Porcentaje sobre los 27.922 avisos. En las dicotómicas Sí/No se muestran el % de "Sí" y el de "No";
lo que falta para llegar a 100% es vacío. En las "solo Sí" se muestra el % y la cantidad de "Sí".

**Tipos.**

- *Numérica continua* y *numérica discreta*: entre paréntesis va el `dtype` con que pandas lee la columna. Los
  conteos aparecen como `float64` cuando tienen vacíos.
- *Texto con número y unidad*: un número guardado como texto ("50 m²", "71 años", "200.000 ARS"). Hay que
  parsearlo antes de usarlo.
- *Categórica nominal*: categorías sin orden.
- *Dicotómica (Sí / No / vacío)*: la ficha muestra "Sí" o "No", y el vacío es falta de dato.
- *Dicotómica (solo Sí / vacío)*: MercadoLibre solo muestra el ítem cuando está presente, así que nunca aparece "No".
  **El vacío no permite distinguir "no tiene" de "no se cargó".**
- *Booleana*: `True` / `False`, generada por código.

**Fuentes.** *Listado* es la tarjeta del aviso en la página de resultados de búsqueda. *Ficha de detalle* es la tabla
de características de la página del aviso, a la que el scraper entra una vez por aviso.

**Regla general de las columnas de la ficha.** El scraper toma cada fila de la tabla de características, convierte la
etiqueta en nombre de columna con `normalizar_nombre_columna()` (minúsculas, sin tildes, y todo lo que no sea letra o
número pasa a "_") y guarda el valor como texto, con los espacios limpios. Una columna existe en una cuota solo si al
menos un aviso de esa cuota tuvo ese ítem; al unir las cuotas, las filas sin el ítem quedan vacías. Los "N/A"
literales pasan a vacío cuando pandas lee las cuotas en la etapa 2 (hubo uno solo). Por eso, en este bloque,
**Transformación: Ninguna** quiere decir "el valor de la ficha tal cual, con esta regla general".

**"En limpieza:"** describe lo que hacen las funciones de `src/limpieza.py`, aplicadas en el notebook 01. El resultado
queda en `propiedades_limpias.tsv`. Las columnas originales se conservan tal cual, con dos excepciones: en `ambientes` y
`departamentos_por_piso` los faltantes disfrazados pasan a vacío, y en `tipo_de_seguridad` y `tipo_de_departamento` se
unifican dos etiquetas mal cargadas. Las transformaciones generan las columnas nuevas de la última sección.

**Primas.** Para las variables que entran al modelo se cita la **prima del modelo** (notebook 03, sección 5): la
diferencia de precio por m² asociada a la característica comparando dentro de la misma zona y con las demás
características fijas (antigüedad, superficie, amenities, etc.). Son asociación, no efecto causal. Las diferencias
simples del diagnóstico de la PreEntrega 1 (`docs/correcciones_pe1/diagnostico.md`) eran mucho más grandes (por
ejemplo, +33,5% para la pileta contra +4,0% en el modelo) porque mezclaban el efecto de la antigüedad: los amenities son
casi exclusivos de los edificios nuevos.

## Diccionario


### 1. Identificación y metadatos del aviso

Columnas que identifican el aviso o guardan el texto crudo del que salen otras variables. Ninguna entra al análisis como característica del departamento.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `link` | URL de la ficha del aviso en MercadoLibre. Es la clave que une las etapas del pipeline | Texto (identificador) | No aplica | MercadoLibre, listado | Ninguna. Se usa como clave de deduplicación en las etapas 1 y 2 | 27.922 (100%) | Los 27.922 links traen parámetros de seguimiento (`?` o `#`), así que deduplicar por link no detecta nada. Por ID de aviso (`MLA` + número, `extraer_id_aviso()`) hay 27.854 avisos únicos: 136 filas comparten ID, 68 sobran. El "duplicados: 0" de la tabla de etapas de `docs/pipeline.md` se explica ahí: la deduplicación por link no los detecta |
| `titulo` | Título que escribe el anunciante | Texto libre | No aplica | MercadoLibre, listado | Limpieza de espacios (`clean_text`) | 27.922 (100%) | 22.301 valores distintos. No es variable de análisis, pero sirve para controles: `menciona_alquiler()` lo usa para marcar títulos que hablan de alquiler. Puede contradecir a las columnas estructuradas |
| `tipo` | Encabezado de la tarjeta del listado: tipo de inmueble y operación | Categórica nominal | No aplica | MercadoLibre, listado | Limpieza de espacios (`clean_text`) | 27.922 (100%) | Constante: "Departamento en venta" en el 100% de las filas, porque la URL de búsqueda ya filtra departamentos en venta. No aporta información: candidata a descartar |
| `es_emprendimiento` | Indica si el precio venía precedido por "Desde", la señal de un emprendimiento con varias unidades | Booleana (`bool`) | No aplica | Derivada del texto del precio del listado | `parse_precio()`: True si `precio_texto` contiene "desde" | 27.922 (100%) | Constante: False en el 100%. La URL filtra `propiedades-individuales`, que excluye emprendimientos, pero no excluye unidades en pozo publicadas de a una (235 avisos con antigüedad negativa, ver `antig_edad`). Candidata a descartar |
| `atributos_texto` | Texto de atributos de la tarjeta del listado: ambientes, baños y superficie | Texto | No aplica | MercadoLibre, listado | Limpieza de espacios. De acá salen `ambientes`, `dormitorios`, `banos` y `m2` por expresiones regulares (`parse_atributos()`) | 27.921 (>99,9%) | Formato típico: "2 ambs.1 baño40 m² cubiertos". El único vacío es el único "N/A" literal de las cuotas crudas, que pandas convirtió en vacío al leer en la etapa 2. Solo 70 textos mencionan dormitorios. La superficie figura como "m² cubiertos", salvo en 527 textos que muestran solo "totales" (ver `m2`). Ningún texto usa coma decimal en la superficie |

### 2. Precio y costos

La variable objetivo del análisis (precio por m²) sale de este bloque, así que es el que más cuidado necesita. `precio` no se puede usar tal como está: hay que pasarlo por `corregir_precio()`.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `precio` | Precio de publicación del aviso (no el de cierre) | Numérica continua (`int64`) | La que indique `moneda`: USD en 27.917 avisos, ARS en 5 | MercadoLibre, listado | `parse_precio()`: borra todo lo que no sea dígito o punto, después los puntos, y convierte a entero | 27.922 (100%) | **No usar sin corregir.** En 627 avisos con "BAJÓ DE PRECIO" quedaron pegados el precio anterior y el vigente (US\$120.000 y US\$112.000 dan 120.000.112.000): por eso el máximo es 1,85e13 y la mediana cruda en USD da 135.000 en vez de 130.000. Aparte hay 4 precios en USD mayores a 10 millones que no son de la baja (errores de carga) y 4 menores a USD 20.000. Se corrige con `corregir_precio()`, que genera `precio_usd` en el dataset limpio. Quedan 3 avisos de USD 12.000.000 por 367 m² en Belgrano que son edificios enteros (uno con 28 ambientes): pasan el filtro de USD 50.000 por m² y quedan marcados como `outlier_precio_m2`, así que no se usan para ajustar el modelo |
| `moneda` | Moneda en la que se publicó el precio | Categórica nominal (USD, ARS) | No aplica | Derivada del texto del precio del listado | `parse_precio()`: "US\$" o "u\$s" da USD; si no, "\$" da ARS | 27.922 (100%) | Los 5 avisos en ARS no cierran como pesos: \$10.000.000 por 100 m² en Palermo o \$1.111.111.111 por 30 m² en Núñez. `motivo_fuera_de_alcance()` los excluye como `precio_en_pesos`: **se excluyen** (notebook 01) |
| `precio_texto` | Texto crudo del precio tal como aparece en la tarjeta | Texto | No aplica | MercadoLibre, listado | Limpieza de espacios (`clean_text`) | 27.922 (100%) | Es el respaldo para reconstruir el precio: 27.295 traen un solo monto y 627 traen dos montos más "BAJÓ DE PRECIO". Ninguno dice "Desde". Es la entrada de `corregir_precio()` |
| `expensas` | Expensas mensuales que declara el anunciante | Texto con monto y moneda (numérica continua tras el parseo) | ARS por mes (27.048 avisos) o USD por mes (41) | MercadoLibre, ficha de detalle | Ninguna en el pipeline. En limpieza: `parsear_expensas()` separa monto y moneda, pasa los 0 a vacío y los montos en ARS mayores a 10 millones a vacío; en las marcadas en USD, las de 10.000 o más se reinterpretan como pesos y las menores a 10 pasan a vacío. `expensas_en_ars()` lleva todo a pesos con el dólar MEP del 14/08/2026 (ARS 1.518,05) y de ahí sale `expensas_usd` | 27.089 (97,0%) | 3.805 en cero (3.783 son "0 ARS"), que se leen como no informadas. 273 en ARS entre 1 y 1.000 pesos, posiblemente cargadas en miles o en USD: `parsear_expensas()` no las trata y quedan 254 en el dataset limpio. 13 en ARS por encima de 10 millones y 40 que no se pueden convertir a número. Las 41 en USD no eran confiables (mediana 0, máximo 825.000): la regla de arriba deja 27 avisos con la etiqueta USD en el dataset limpio, de los cuales solo 7 tienen monto. Son pesos nominales a la fecha de extracción: compararlas con precios en USD exige declarar tipo de cambio, fuente y fecha |

### 3. Superficie

Hay cuatro medidas de superficie y no son equivalentes: `m2` viene del listado y es la superficie cubierta, salvo en 527 avisos donde es la total; `superficie_total` y `superficie_cubierta` vienen de la ficha como texto con unidad. Como denominador del precio por m² la limpieza usa `m2` del listado y recurre a `superficie_total` solo cuando `m2` está fuera de rango (`m2_final`, 32 avisos recuperados). Así, `m2_final` es la superficie cubierta en casi todos los avisos y la total en unos 560 (2%): se acepta como limitación.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `m2` | Superficie que muestra la tarjeta del listado: la **cubierta** en casi todos los avisos y la **total** en los 527 cuya tarjeta solo informa "totales" | Numérica continua (`float64`, valores enteros) | m² | MercadoLibre, listado | `parse_atributos()`: primer número antes de "m²" en `atributos_texto`; en rangos ("139 - 166 m²") toma el primero | 27.896 (99,9%) | 26 vacíos y 36 menores a 15 m² (mínimo 0; ej. "1 m² cubierto, 26 m² totales"). Máximo 920, mediana 57. **No es una medida homogénea (verificado):** en 527 avisos (1,9%) la tarjeta muestra solo "m² totales", sin mencionar la cubierta, así que ahí `m2` es la total. Además, `superficie_final()` usa `m2` y, si no sirve, cae a `superficie_total`, con lo que suma más casos de superficie total. Verificado: ninguna tarjeta usa coma decimal, así que la expresión regular no pierde decimales |
| `superficie_total` | Superficie total de la unidad según la ficha (cubierta más descubierta) | Texto con número y unidad (numérica continua tras el parseo) | m² (73 casos en ha) | MercadoLibre, ficha de detalle | Ninguna en el pipeline. En limpieza: `parsear_superficie()` cambia coma decimal por punto y deja en vacío los valores en ha y los que tienen punto de miles | 27.879 (99,8%) | 43 vacíos. De los 73 en hectáreas, 48 son "0 ha" y 20 son "0,01 ha" o "0,03 ha" (una superficie chica redondeada a hectáreas); los otros 5 ("33 ha" a "73 ha") son imposibles para un departamento. Todos pasan a vacío y se usa `m2`. 1.589 usan coma decimal ("103,71 m²") y 9 punto de miles, ambiguos ("45.000 m²" en un dos ambientes). No se controló que sea mayor o igual que `superficie_cubierta` |
| `superficie_cubierta` | Superficie cubierta de la unidad según la ficha | Texto con número y unidad (numérica continua tras el parseo) | m² | MercadoLibre, ficha de detalle | Ninguna. `superficie_final()` no la usa | 27.363 (98,0%) | 559 vacíos (2,0%). 1.494 con coma decimal y 9 con punto de miles; ninguna en ha. Es la medida comparable con `m2`, así que sirve para validarla |
| `superficie_de_balcon` | Superficie del balcón | Texto con número y unidad (numérica continua tras el parseo) | m² | MercadoLibre, ficha de detalle | Ninguna | 10.102 (36,2%) | 63,8% vacío. 2.401 con coma decimal y 1 con punto de miles. 339 avisos dicen "1 m²" (¿balcón francés o carga mínima?). No se controló la coherencia con `balcon`: la variable no se usa |

### 4. Ambientes y otros conteos

`ambientes`, `dormitorios` y `banos` salen del listado y de la ficha: el scraper agrega la ficha al registro del listado con `datos.update()`, así que cuando la ficha trae el dato pisa al del listado. Donde los dos tienen dato coinciden en el 100% de los casos. Pero cuando la tarjeta no trae el dato, la ficha tampoco lo tiene y la columna queda en 0: esos ceros son faltantes (verificado aviso por aviso en `ambientes` y en `banos`). `cocheras` y `bauleras` salen solo de la ficha.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `ambientes` | Cantidad de ambientes de la unidad, según la convención del anunciante | Numérica discreta (`int64`) | ambientes | MercadoLibre, listado y ficha de detalle | Del listado por expresión regular ("N amb"); la ficha lo pisa cuando trae "Ambientes". 313 avisos lo tienen solo por la ficha | 27.922 (100%) | 312 en cero, 1 negativo (−1) y 6 mayores a 15 (hasta 30). **Verificado:** los 313 avisos sin ambientes en la tarjeta son exactamente los 313 con valor 0 o −1, y ningún otro aviso tiene 0. La ficha deja 0 cuando no hay dato: son faltantes, no monoambientes. **En limpieza:** pasan a vacío (notebook 01) |
| `dormitorios` | Cantidad de dormitorios | Numérica discreta (`float64` por los vacíos) | dormitorios | MercadoLibre, listado y ficha de detalle | Igual que `ambientes`, pero sale casi entera de la ficha: solo 70 textos del listado mencionan dormitorios | 27.912 (>99,9%) | 10 vacíos. 3.407 en cero (12,2%), que pueden ser monoambientes; hay 14 mayores a 10 (máximo 38). **1.717 avisos (6,1%) tienen dormitorios mayor o igual que ambientes**, algo imposible con la convención argentina (los ambientes cuentan el living). Indica que no todos los anunciantes cuentan los ambientes igual. **En limpieza:** se marcan (`incoherencia_dormitorios`); el tamaño se mide sobre todo con la superficie |
| `banos` | Cantidad de baños | Numérica discreta (`int64`) | baños | MercadoLibre, listado y ficha de detalle | Igual que `ambientes` | 27.922 (100%) | 313 en cero. **Verificado:** son exactamente los 313 avisos cuya tarjeta no trae baños, y ningún otro aviso tiene 0. Son faltantes, pero **la limpieza no los corrigió**: quedan 303 en cero en el dataset limpio. Se verificó que pasarlos a vacío no cambia el modelo (1.702 avisos marcados en lugar de 1.704). No son los mismos avisos que los ceros de `ambientes`: solo 28 coinciden. 6 mayores a 8, hasta 16 |
| `cocheras` | Cantidad de cocheras incluidas en la venta | Numérica discreta (`float64`) | cocheras | MercadoLibre, ficha de detalle | Ninguna | 27.911 (>99,9%) | 11 vacíos; 75,8% en cero. 19 avisos con más de 6 (hasta 22), que probablemente son las cocheras del edificio. El modelo usa si tiene al menos una: prima de +15,8% |
| `bauleras` | Cantidad de bauleras incluidas en la venta | Numérica discreta (`float64`) | bauleras | MercadoLibre, ficha de detalle | Ninguna | 24.138 (86,4%) | 13,6% vacío y 72,6% en cero. Un aviso con 24 |

### 5. Edificio y posición de la unidad

Atributos numéricos y categóricos de la ficha. Es el bloque con más valores imposibles: los numéricos llegan como número, pero la plataforma no valida lo que carga el anunciante.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `tipo_de_departamento` | Subtipo de unidad que declara el anunciante | Categórica nominal (9 categorías) | No aplica | MercadoLibre, ficha de detalle | Ninguna | 26.335 (94,3%) | 5,7% vacío; "Departamento" es el 85,9%. "Penthhouse" (31) viene así escrito desde la plataforma: **en limpieza** se corrige a "Penthouse". Hay 60 "Ph" (0,2%): aparecieron en la búsqueda de departamentos y **se conservan**, porque el anunciante los publicó como departamento; es una limitación menor. "Monoambiente" (372) no coincide con los 4.222 avisos de 1 ambiente: no sirve para contar monoambientes |
| `antig_edad` | Antigüedad del edificio que declara el anunciante | Texto con número y unidad (numérica discreta tras el parseo) | años | MercadoLibre, ficha de detalle | Ninguna en el pipeline. El nombre sale de `normalizar_nombre_columna()`, que no reemplaza la "ü" de "Antigüedad" y la convierte en "_". En limpieza: `parsear_antiguedad()` pasa los valores de 1800 o más a 2026 menos el año, los negativos a 0 marcando `en_construccion`, y los mayores a 150 a vacío | 27.143 (97,2%) | 2,8% vacío. 235 negativos: unidades en pozo o en construcción, que no son usadas. 66 son años de construcción ("1.976 años") y 2 son "40.000 años", que el parser lee como año y deja negativos (se excluyen junto con los de pozo); 6 están entre 151 y 1.799 y 1 no es número. Fuerte redondeo a decenas (50 años es el 10%; 40, el 8%) y 1.479 avisos con "1 años" (5,3%), posible carga por defecto para "a estrenar". Es dato declarado, no verificado |
| `cantidad_de_pisos` | Cantidad de pisos declarada en la ficha; en principio, del edificio | Numérica discreta (`float64`) | pisos | MercadoLibre, ficha de detalle | Ninguna | 18.563 (66,5%) | 33,5% vacío; mediana 7. 4.374 avisos valen 1 (23,6% de los que tienen dato), raro para un edificio de departamentos: probablemente parte de los anunciantes carga los pisos de la unidad (1 si es simple, 2 si es dúplex). 12 avisos superan 60, la altura de cualquier edificio residencial de CABA, e incluyen años (1970, 2008, 2011) y valores como 162 o 410 |
| `departamentos_por_piso` | Cantidad de unidades por planta del edificio | Numérica discreta (`float64`) | unidades por piso | MercadoLibre, ficha de detalle | Ninguna | 17.525 (62,8%) | 37,2% vacío. **6.970 avisos (25%) valen 99:** faltante disfrazado o valor por defecto. **En limpieza:** pasa a vacío (notebook 01). La mediana (5) y el p99 (99) están contaminados por ese valor. 1 negativo; máximo 278 |
| `numero_de_piso_de_la_unidad` | Piso en el que está la unidad | Numérica discreta (`float64`) | piso | MercadoLibre, ficha de detalle | Ninguna | 17.876 (64,0%) | 36,0% vacío. No hay ningún 0, así que la planta baja no se distingue (probablemente se carga como 1, el valor más frecuente: 12%). 1 negativo (−1, ¿subsuelo?). 21 avisos superan 60 (111, 208, 401, 903; máximo 435.454): parecen números de unidad, donde "401" sería piso 4, depto 1. La limpieza los deja y marca `incoherencia_piso` cuando el piso supera `cantidad_de_pisos`; el modelo recorta el piso en 20. Se verificó que pasarlos a vacío no cambia el modelo. Es la base del atributo "piso alto" |
| `numero_de_torre` | Número de torre dentro de un complejo | Numérica discreta (`float64`) | No aplica | MercadoLibre, ficha de detalle | Ninguna | 2.213 (7,9%) | 92,1% vacío; el 96% de los que tienen dato vale 1. 39 superan 20 (hasta 10.750) y parecen alturas de calle o años (2028). Poca utilidad analítica |
| `disposicion` | Ubicación de la unidad respecto de la calle | Categórica nominal (Frente, Contrafrente, Lateral, Interno) | No aplica | MercadoLibre, ficha de detalle | Ninguna | 25.729 (92,1%) | 7,9% vacío; Frente es el 58,9%. Prima del modelo para contrafrente: −0,6% |
| `orientacion` | Orientación cardinal de la unidad | Categórica nominal (Norte, Este, Oeste, Sur) | No aplica | MercadoLibre, ficha de detalle | Ninguna | 19.620 (70,3%) | 29,7% vacío. Solo los 4 puntos cardinales, sin intermedios. Norte es el 41,2%: puede haber sesgo de declaración, porque es la orientación más valorada y se informa más cuando es favorable |

### 6. Espacios de la unidad

Dicotómicas de la ficha que describen la propia unidad. En las "solo Sí" el vacío no distingue "no tiene" de "no se cargó". En algunas "Sí/No" el "No" tampoco significa ausencia: un departamento sin cocina es casi imposible.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `living` | La unidad tiene living | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 37,8% · No 52,4% | El 52,4% dice "No": un departamento sin living es raro. Probablemente indica living-comedor integrado o ítem no tildado. No leer el "No" como ausencia |
| `comedor` | La unidad tiene comedor | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 33,4% · No 39,9% | El 39,9% dice "No". Misma advertencia que `living` |
| `cocina` | La unidad tiene cocina | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 71,2% · No 21,2% | El 21,2% dice "No", en un universo de departamentos: casi seguro significa cocina integrada o ítem no tildado, no ausencia |
| `dormitorio_en_suite` | Al menos un dormitorio tiene baño propio | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 13,2% · No 46,1% | 40,7% vacío. Prima del modelo: +6,6% |
| `toilette` | Tiene toilette (baño de cortesía, sin ducha) | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 27,7% (7.740) | no aplica |
| `estudio` | Tiene estudio | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 4,7% (1.309) | no aplica |
| `desayunador` | Tiene desayunador | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 4,6% (1.274) | no aplica |
| `dependencia_de_servicio` | Tiene dependencia de servicio (cuarto y baño de servicio) | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 7,6% (2.113) | no aplica |
| `vestidor` | Tiene vestidor | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 8,1% (2.256) | no aplica |
| `placards` | Tiene placards (armarios empotrados) | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 24,7% (6.902) | no aplica |
| `con_lavadero` | La unidad tiene lavadero propio | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 39,3% (10.967) | No confundir con `lavanderia`, que es un servicio común del edificio |
| `balcon` | La unidad tiene balcón | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 55,6% · No 34,2% | Prima del modelo: +4,3%. Controlar contra `superficie_de_balcon` |
| `terraza` | La unidad tiene terraza | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 14,7% · No 69,3% | La etiqueta no aclara si es propia o común del edificio. Prima del modelo: +1,9% |
| `patio` | La unidad tiene patio | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 9,8% (2.728) | no aplica |
| `jardin` | La unidad tiene jardín | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 4,2% (1.164) | Raro en departamentos (4,2%): probablemente unidades en planta baja |
| `chimenea` | La unidad tiene chimenea o hogar | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,5% (139) | no aplica |

### 7. Servicios e infraestructura

Era el bloque de mayor peso del índice de confort de la PreEntrega 1 (45%). El diagnóstico mostró que es el que menos se relaciona con el precio dentro de la sub-zona y que, en las columnas "solo Sí", mide lo completo que está el aviso más que la infraestructura real.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `agua_corriente` | El inmueble tiene agua corriente | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 62,4% (17.415) | Nunca aparece "No": mide si el anunciante tildó el ítem, no si hay agua. No entra al modelo |
| `gas_natural` | El inmueble tiene gas natural | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 50,8% · No 38,4% | El 38,4% dice "No". En la PreEntrega 1, la diferencia simple dentro de la sub-zona era negativa (−4,8%): una hipótesis a verificar es que marque edificios nuevos todo-eléctricos, o sea, antigüedad y no confort. No entra al modelo |
| `aire_acondicionado` | Tiene aire acondicionado | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 38,1% · No 51,8% | Prima del modelo: +2,1% |
| `calefaccion` | Tiene calefacción | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 23,1% · No 65,1% | No indica el tipo (central, individual, losa radiante) |
| `caldera` | Tiene caldera | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 7,3% (2.034) | no aplica |
| `con_conexion_para_lavarropas` | Tiene conexión para lavarropas | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 28,9% · No 54,5% | no aplica |
| `linea_telefonica` | Tiene línea telefónica | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 12,6% (3.525) | Poco relevante hoy para el valor |
| `acceso_a_internet` | Tiene acceso a internet | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 24,5% (6.836) | no aplica |
| `ascensor` | El edificio tiene ascensor | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 60,7% · No 32,2% | El 32,2% dice "No", coherente con edificios bajos. Controlar contra `cantidad_de_pisos`. Prima del modelo: −0,1% (sin efecto una vez controlada la antigüedad) |
| `rampa_para_silla_de_ruedas` | El edificio tiene rampa para silla de ruedas | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 15,3% (4.275) | no aplica |
| `grupo_electrogeno` | El edificio tiene grupo electrógeno | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,8% (215) | no aplica |
| `cisterna` | El edificio tiene cisterna | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,7% (208) | no aplica |
| `con_energia_solar` | El edificio tiene energía solar | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí <0,1% (13) | La columna no existe en la cuota 5 (sur de la ciudad) porque ningún aviso de esa cuota mostró el ítem; el vacío significa lo mismo que en el resto. Solo 13 avisos |

### 8. Amenities y servicios del edificio

En las diferencias simples de la PreEntrega 1 era el bloque que más se asociaba con el precio, pero buena parte era efecto de la antigüedad: en el modelo, cada amenity suma entre 2% y 5%. Casi todas son "solo Sí" y muy poco frecuentes: varias tienen menos de 1% de avisos con dato, así que no alcanzan para estimar una prima propia.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `pileta` | El edificio tiene pileta | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 14,4% · No 52,2% | Prima del modelo: +4,0% (la diferencia simple de la PreEntrega 1 era +33,5%) |
| `gimnasio` | El edificio tiene gimnasio | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 9,1% (2.530) | Prima del modelo: +5,2% |
| `sauna` | El edificio tiene sauna | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 3,5% (970) | No entra al modelo: se superpone con gimnasio y pileta, y la diferencia simple de la PreEntrega 1 salía de solo 16 sub-zonas comparables |
| `jacuzzi` | Tiene jacuzzi | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 2,7% (767) | No aclara si es de la unidad o del edificio |
| `salon_de_usos_multiples` | El edificio tiene SUM | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 11,3% (3.148) | Prima del modelo: +2,6% |
| `salon_de_fiestas` | El edificio tiene salón de fiestas | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 1,9% (521) | Se superpone con el SUM: puede ser el mismo espacio declarado de dos formas |
| `playroom` | El edificio tiene playroom | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 2,3% (649) | no aplica |
| `area_de_juegos_infantiles` | El edificio tiene área de juegos infantiles | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 1,6% (460) | no aplica |
| `area_de_cine` | El edificio tiene sala de cine | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,7% (189) | no aplica |
| `parrilla` | Tiene parrilla | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 15,0% (4.200) | No aclara si es propia o común. Prima del modelo: +3,5% |
| `roof_garden` | El edificio tiene roof garden | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,7% (182) | no aplica |
| `con_area_verde` | El edificio tiene área verde | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 5,9% (1.642) | no aplica |
| `cowork` | El edificio tiene espacio de cowork | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,7% (201) | no aplica |
| `lavanderia` | El edificio tiene lavandería común | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 25,6% · No 39,0% | No confundir con `con_lavadero` (lavadero propio de la unidad) |
| `recepcion` | El edificio tiene recepción | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 2,1% (580) | no aplica |
| `seguridad` | El edificio tiene seguridad | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 26,8% · No 38,4% | Solo 3.388 avisos informan `tipo_de_seguridad`, contra 7.496 con "Sí". Prima del modelo: +0,9% |
| `tipo_de_seguridad` | Modalidad de la seguridad del edificio | Categórica nominal (5 categorías) | No aplica | MercadoLibre, ficha de detalle | Ninguna | 3.388 (12,1%) | "24 horas" (1.718) y "24 hs" (26) son la misma categoría: **en limpieza** se unifican en "24 horas" (notebook 01, sección 3.4). Las otras: Diurno, Virtual, Nocturno. No entra al análisis |
| `estacionamiento_para_visitantes` | El edificio tiene estacionamiento para visitantes | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,6% (156) | no aplica |
| `cancha_de_paddle` | El edificio o complejo tiene cancha de pádel | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,1% (25) | no aplica |
| `cancha_de_tenis` | El edificio o complejo tiene cancha de tenis | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,5% (133) | no aplica |
| `con_cancha_de_futbol` | El edificio o complejo tiene cancha de fútbol | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,1% (31) | no aplica |
| `cancha_de_basquetbol` | El edificio o complejo tiene cancha de básquet | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,1% (14) | La columna no existe en la cuota 2 porque ningún aviso de esa cuota mostró el ítem; el vacío significa lo mismo que en el resto. Solo 14 avisos |
| `canchas_de_usos_multiples` | El edificio o complejo tiene canchas de usos múltiples | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,2% (58) | no aplica |
| `en_barrio_cerrado` | La unidad está en un barrio o complejo cerrado | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 0,7% (193) | En CABA casi no hay barrios cerrados: probablemente son complejos con acceso controlado |

### 9. Condiciones comerciales y de uso

Atributos que no describen el inmueble sino las condiciones de la venta o del uso permitido.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `apto_credito` | El anunciante declara que la unidad es apta para crédito hipotecario (documentación en regla para que un banco la acepte como garantía) | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 43,1% · No 47,1% | Declarado, no verificado con ningún banco. El 43,1% dice "Sí". Es relevante en un mercado donde la mayoría de las compras se hacen al contado: un "No" puede indicar problemas de documentación, un dato a revisar antes de invertir. Entra al modelo como control: prima de −1,2% |
| `apto_profesional` | El reglamento permite uso profesional (consultorio, oficina) | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 25,5% (7.128) | Prima del modelo: −3,3% |
| `admite_mascotas` | El reglamento admite mascotas | Dicotómica (Sí / No / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 35,8% · No 49,9% | no aplica |
| `amoblado` | Se vende amoblado | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 4,6% (1.295) | no aplica |
| `heladera` | Se vende con heladera incluida | Dicotómica (solo Sí / vacío) | No aplica | MercadoLibre, ficha de detalle | Ninguna | Sí 2,4% (667) | Es equipamiento que se incluye, no una característica del inmueble |

### 10. Ubicación declarada y geocodificación

`ubicacion` y `barrio` vienen de MercadoLibre; las otras cuatro las agrega la etapa 3 con el normalizador de direcciones de USIG. El 17,9% de los avisos no tiene coordenadas y esa pérdida no es pareja entre barrios.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `ubicacion` | Dirección y barrio tal como los escribe el anunciante ("Calle altura, Barrio, Capital Federal") | Texto libre | No aplica | MercadoLibre, listado | Limpieza de espacios (`clean_text`) | 27.922 (100%) | 20.122 valores distintos. Formato libre: alturas redondeadas ("Esmeralda Al 900"), nombres de emprendimientos ("Le Parc, Torre Río") o solo la comuna. Es la entrada de `limpiar_direccion()` |
| `barrio` | Barrio de la búsqueda de MercadoLibre en la que apareció el aviso | Categórica nominal (47 categorías) | No aplica | Parámetro del scraper: el barrio de la URL de búsqueda, definido en `config.yaml` | La asigna el scraper; no se parsea del aviso | 27.922 (100%) | Es la clasificación de la plataforma, según lo que cargó el anunciante, no un cruce con polígonos oficiales. Incluye "barrio-norte" (801 avisos), que no es barrio oficial, y **no incluye San Cristóbal ni Parque Chas**, que no están en las cuotas de `config.yaml` (CABA tiene 48 barrios oficiales). Palermo, Belgrano, Caballito y Recoleta tienen exactamente 2.016 avisos, el tope de 42 páginas de 48: están truncados. Los valores van sin tildes ("nunez") |
| `dir_limpia` | Dirección (calle y altura, o esquina) preparada para el geocodificador | Texto | No aplica | Cálculo propio sobre `ubicacion` | `limpiar_direccion()`: corta en la primera coma, pasa "Av." a "Avenida", descarta lo que sigue a un punto y saca la abreviatura "Al". Queda vacía si no tiene número ni " Y " de esquina | 26.338 (94,3%) | 1.584 vacías, que son las `NO_GEOCODIFICABLE`. 55 "Comuna X" pasaron el filtro porque tienen un número, pero USIG no las resolvió (`SIN_RESULTADO`), así que no hay falsos positivos. Las más repetidas son edificios con muchas unidades (Esmeralda 900, Avenida Cabildo 4600), no un punto genérico |
| `lat` | Latitud del punto geocodificado | Numérica continua (`float64`) | grados decimales (WGS84) | USIG (GCBA), normalizador de direcciones | Coordenada `y` de la primera dirección normalizada que devuelve USIG con `geocodificar=true`. Solo si `geo_status` es OK | 22.912 (82,1%) | 17,9% vacío y **la pérdida no es aleatoria por barrio**: el éxito va de 59,5% en Puerto Madero a 92,5% en Boedo (chi², p ≈ 1e-101). El rango (−34,695 a −34,536) cae dentro de CABA. Con alturas redondeadas ("Al 900") el punto cae en esa altura y no en el edificio: error de hasta una cuadra |
| `lon` | Longitud del punto geocodificado | Numérica continua (`float64`) | grados decimales (WGS84) | USIG (GCBA), normalizador de direcciones | Coordenada `x` de la misma respuesta. Solo si `geo_status` es OK | 22.912 (82,1%) | Mismos vacíos que `lat`. Rango de −58,530 a −58,354, dentro de CABA |
| `geo_status` | Resultado de la geocodificación | Categórica nominal (4 categorías) | No aplica | Cálculo propio sobre la respuesta de USIG | OK: hay coordenadas. SIN_RESULTADO: USIG no reconoció la dirección. SIN_COORDENADAS: la reconoció pero sin coordenadas. NO_GEOCODIFICABLE: `dir_limpia` vacía, no se consultó | 27.922 (100%) | OK 22.912 (82,1%), SIN_RESULTADO 3.406, NO_GEOCODIFICABLE 1.584 y SIN_COORDENADAS 20. No hubo fallos por reintentos ni errores de conexión |

### 11. Variables geográficas derivadas

Las agrega la etapa 4 solo para los avisos con `geo_status` = OK. Los demás quedan con estas columnas vacías.

| Variable | Significado | Tipo | Unidad | Fuente | Transformación | Con dato | Observaciones |
|---|---|---|---|---|---|---|---|
| `dist_transporte_m` | Distancia a la estación de subte más cercana | Numérica continua (`float64`) | metros | BA Data ("Subte: estaciones", snapshot del 14/09/2026, 90 estaciones) + cálculo propio | Haversine (radio 6.371 km) desde `lat`/`lon` a cada estación; queda la mínima, redondeada a metro entero | 22.912 (82,1%) | Mediana 508 m, media 925 m, máximo 5.805 m. Distancia en línea recta, no a pie. Solo subte: deja afuera tren y Metrobus, que son el transporte pesado del sur y el oeste. El snapshot es un mes posterior al scraping |
| `dist_centralidad_m` | Distancia al polo de centralidad más cercano: Obelisco, Puerto Madero o Catalinas | Numérica continua (`float64`) | metros | Cálculo propio; coordenadas fijadas por el grupo en `config.yaml` | Haversine a los tres polos; queda la mínima, redondeada a metro entero | 22.912 (82,1%) | Mediana 5.265 m, máximo 14.384 m. Los polos son una elección del grupo, no un dato externo. Hallazgo del TP1: casi no se relaciona con el precio por m², porque el valor se concentra en el corredor norte |
| `subzona` | Sub-zona geográfica dentro del barrio: la unidad de comparación del análisis | Categórica nominal (198 categorías) | No aplica (etiqueta `barrio_k`) | Cálculo propio (KMeans, scikit-learn) | Por barrio, con los avisos geocodificados: si son menos de 30, una sola sub-zona `barrio_0`; si no, KMeans sobre `lat`/`lon` con k = min(5, máx(1, n // 30)), `random_state=42`, `n_init=10` | 22.912 (82,1%) | **No hay un mínimo de 30 avisos por sub-zona**, aunque el README de la PreEntrega 1 lo dijera: k limita la cantidad de clusters, pero KMeans no garantiza su tamaño. 42 de 198 tienen menos de 30 avisos y varias tienen 1 (mediana 68, máximo 532). 6 barrios tienen una sola sub-zona. El número k es arbitrario: `palermo_0` y `belgrano_0` no se corresponden. KMeans corre sobre grados sin proyectar (a esta latitud, 1° de longitud mide 0,82 de 1° de latitud), con una leve distorsión. **En el modelo:** la sub-zona se usa solo en los barrios donde mejora la referencia y es estable, decidido dentro de cada vuelta; las zonas con menos de 10 avisos, los avisos con `geo_dudoso` y los barrios inestables vuelven al barrio (`zona`, etapa 6; ver "Variables nuevas") |

## Variables nuevas

### Creadas en la limpieza (etapa 5, notebook 01)

Están en `propiedades_limpias.tsv`. Las marcadas con ★ son las principales para el análisis. Cifras sobre las 27.578
filas del dataset limpio. La etapa 5 (`src/limpiar.py`) reproduce la lógica del notebook 01, que verifica al final que
los dos resultados coinciden.

| Variable | Significado | Tipo y unidad | Fórmula final | Con dato |
|---|---|---|---|---|
| `id_aviso` | ID estable del aviso | Texto (identificador) | `extraer_id_aviso(link)`: "MLA" más el número del link, sin guion. Se usa para deduplicar: de cada ID queda la fila cuyo barrio de búsqueda coincide con el polígono oficial (`barrio_coincide` de `accesibilidad.tsv`, 17 casos) y, si ninguna coincide o no hay coordenadas, la primera (51 casos). La fila conservada queda en la posición de la primera aparición, porque el orden de las filas define las vueltas de la validación | 27.578 (100%), todos distintos |
| `precio_usd` ★ | Precio vigente del aviso | Numérica continua; USD | Último monto de `precio_texto` (`corregir_precio()`). Solo avisos en USD: los publicados en pesos se excluyen | 27.578 (100%). Mediana USD 130.000 |
| `precio_anterior_usd` | Precio previo a la baja | Numérica continua; USD | Primer monto de `precio_texto` si el aviso tiene "BAJÓ DE PRECIO"; vacío si no. **Usa el precio: no entra al modelo** | 626 (2,3%) |
| `bajo_de_precio` ★ | El aviso muestra la etiqueta "BAJÓ DE PRECIO" | Booleana | True si el texto tiene la etiqueta y al menos dos montos. **Usa el precio: no entra al modelo**, se analiza aparte | True en 626 (2,3%) |
| `baja_pct` | Caída del precio respecto del anterior | Numérica continua; % | 100 × (1 − `precio_usd` / `precio_anterior_usd`). **Usa el precio: no entra al modelo** | 626 (2,3%). Mediana 6,8%, mínimo 5,0% |
| `m2_final` ★ | Superficie de trabajo | Numérica continua; m² | `superficie_final()`: `m2` si está entre 15 y 1.000; si no, `superficie_total` parseada si cae en ese rango; si no, el aviso se excluye (`superficie_invalida`) | 27.578 (100%). Mediana 57 m² |
| `m2_origen` | De dónde salió `m2_final` | Categórica nominal: `listado`, `recuperada_de_total` | Segundo valor de `superficie_final()` | `listado` 27.546, `recuperada_de_total` 32 |
| `precio_m2_usd` ★ | Precio por m²: la variable objetivo | Numérica continua; USD/m² | `precio_usd` / `m2_final` | 27.578 (100%). Mediana USD 2.393 |
| `antiguedad` ★ | Antigüedad del edificio | Numérica discreta; años | `parsear_antiguedad(antig_edad)`: valores de 1800 o más se toman como año de construcción (2026 menos el año); mayores a 150 pasan a vacío. Los 1.479 "1 años" se conservan como 1 | 26.809 (97,2%). Mediana 40 años |
| `en_construccion` | Unidad en pozo o en construcción | Booleana | Antigüedad declarada negativa. Esos avisos se excluyen (`en_pozo`, 237), así que en el dataset limpio vale False en todas las filas | False en 100% |
| `expensas_monto` | Monto de las expensas | Numérica continua; ARS o USD por mes, según `expensas_moneda` | `parsear_expensas(expensas)`: 0 pasa a vacío; ARS mayores a 10 millones pasan a vacío; en USD, 10.000 o más se reinterpreta como pesos y menos de 10 pasa a vacío. **Nuevo en la PE3:** las menores a ARS 1.000 (`expensas_minimo_ars`) pasan a vacío, son valores de relleno (267) | 22.884 (83,0%) |
| `expensas_moneda` | Moneda de las expensas | Categórica nominal: ARS, USD | Segundo valor de `parsear_expensas()` | ARS 26.732, USD 27 |
| `expensas_ars` | Expensas en pesos | Numérica continua; ARS por mes | `expensas_en_ars()`: las de USD × 1.518,05 (dólar MEP, 14/08/2026); las de ARS sin cambio | 22.884 (83,0%). Mediana ARS 200.000 |
| `expensas_usd` ★ | Expensas en dólares | Numérica continua; USD por mes | `expensas_ars` / 1.518,05 | 22.884 (83,0%). Mediana USD 131,7 |
| `posible_duplicado` | Otro aviso, con otro ID, tiene el mismo precio, superficie, dirección y ambientes | Booleana | `marcar_posible_duplicado()`, solo entre avisos con dirección. Se marca, no se borra: puede ser el mismo departamento publicado por dos inmobiliarias o unidades gemelas de un edificio | True en 3.059 (11,1%) |
| `menciona_alquiler` | El título menciona alquiler | Booleana | `menciona_alquiler(titulo)`. Se marca, no se excluye: los precios de esos avisos son de venta | True en 162 (0,6%) |
| `titulo_casa` | El título dice que es una casa publicada como departamento | Booleana | `marcas_casa(titulo)`: "casa" en el título, sin contar "casa de" ni "tipo casa". Se marca, no se excluye: el anunciante la publicó como departamento. Entra como señal en el ranking (**nueva en la PE3**) | True en 25 (0,1%) |
| `titulo_tipo_casa` | El título dice "tipo casa" (un departamento con características de casa, no una casa) | Booleana | Ídem, con la expresión "tipo casa" (**nueva en la PE3**) | True en 51 (0,2%) |
| `titulo_barrio_popular` | El título nombra un barrio popular (Rodrigo Bueno, barrio Mugica, villa 31) | Booleana | `menciona_barrio_popular(titulo)` (**nueva en la PE3**). Complementa a `en_barrio_popular` de `accesibilidad.tsv`, que usa el polígono | True en 2 |
| `outlier_precio_m2` | Precio por m² atípico para su zona | Booleana | `outliers_iqr_por_grupo()` sobre `precio_m2_usd`, por sub-zona y por barrio para los avisos sin sub-zona: fuera de [Q1 − 1,5·IQR; Q3 + 1,5·IQR], solo en grupos con 10 datos o más. **Marca informativa:** desde la PE3 el modelo recalcula los atípicos dentro de cada vuelta, sobre el logaritmo del precio por m² y en la zona de referencia | True en 931 (3,4%), 96% por encima de su zona |
| `incoherencia_dormitorios` | Dormitorios mayor o igual que ambientes, sin contar el monoambiente | Booleana | `dormitorios >= ambientes`, salvo 1 ambiente con 1 dormitorio, que es la convención de la plataforma para un monoambiente | True en 376 (1,4%) |
| `incoherencia_piso` | El piso de la unidad supera la cantidad de pisos | Booleana | `numero_de_piso_de_la_unidad > cantidad_de_pisos`, **solo cuando el edificio declara 3 pisos o más** (`pisos_edificio_desde`): con 1 o 2, `cantidad_de_pisos` suele ser las plantas del departamento, no los pisos del edificio (en la PE2 se comparaba siempre y marcaba 2.299) | True en 80 (0,3%) |

Además, en las columnas originales: `ambientes` en 0 o negativo pasa a vacío; **`banos` en 0 pasa a vacío** (303; en el
modelo se completan con 1 más la marca `banos_sin_dato`); **`numero_de_piso_de_la_unidad` de 100 o más se queda con las
centenas** (`piso_desde_numero_de_unidad()`: el anunciante cargó el número de unidad, por ejemplo 1203 es el piso 12;
19 casos); `departamentos_por_piso` = 99 pasa a vacío; y se unifican "24 hs" con "24 horas" (`tipo_de_seguridad`) y
"Penthhouse" con "Penthouse" (`tipo_de_departamento`). Las 344 filas excluidas (68 duplicados por ID, 237 en pozo, 28
con superficie inválida, 5 en pesos, 4 con precio menor a USD 20.000, 1 con precio imposible y 1 que no es una venta,
"compro") están en `registro_limpieza.csv` con su motivo.

### Fuentes externas por aviso (PreEntrega 3)

Archivos aparte, con `link` como clave, que no modifican el dataset enriquecido. Se unen al dataset de trabajo en la
etapa 6. Las fichas de cada fuente, con link, fecha y SHA-256 del snapshot, están en
[`fuentes_externas.md`](fuentes_externas.md); los controles, en [`control_fuentes.md`](control_fuentes.md).

**`accesibilidad.tsv`** (`src/fuentes_externas.py`): 27.922 filas × 14 columnas; las distancias tienen dato en los
22.912 avisos con coordenadas.

| Variable | Significado | Tipo y unidad | Fórmula final |
|---|---|---|---|
| `dist_tren_m` | Estación de ferrocarril más cercana, incluidas las del conurbano | Numérica continua; m | Haversine a la estación más cercana del snapshot de BA Data, sin las "Ex-estación". Mediana 985 m |
| `dist_metrobus_m` | Parada de Metrobus más cercana | Numérica continua; m | Ídem. Mediana 962 m |
| `dist_premetro_m` | Estación de premetro más cercana | Numérica continua; m | Ídem. Mediana 7,2 km: solo importa en el sur |
| `dist_riel_m` | Transporte sobre rieles más cercano | Numérica continua; m | Mínimo entre subte (`dist_transporte_m`), tren y premetro. Mediana 423 m |
| `dist_transporte_pesado_m` ★ | Transporte pesado más cercano | Numérica continua; m | Mínimo entre riel y Metrobus. Mediana 337 m |
| `dist_espacio_verde_m` | Plaza, parque o jardín más cercano | Numérica continua; m | Distancia al borde del polígono (UTM 21S), 0 si el aviso cae adentro. Solo clases PLAZA, PARQUE, PARQUE SEMIPÚBLICO, JARDÍN y JARDÍN BOTÁNICO. Mediana 284 m |
| `area_verde_500m_ha` ★ | Superficie de espacio verde alrededor del aviso | Numérica continua; ha | Área de los espacios verdes (sin canteros centrales ni la franja de la General Paz) dentro del círculo de 500 m. Mediana 0,9 ha |
| `barrio_oficial` | Barrio oficial donde cae el punto | Categórica nominal (48 barrios) | Polígonos de barrios de BA Data. Solo como control de calidad: el análisis usa el barrio de búsqueda |
| `barrio_coincide` | El barrio de búsqueda coincide con el oficial | Booleana (1/0) | Nombres normalizados; Barrio Norte cuenta como coincidente en Recoleta, Retiro o Palermo. Sí en 18.687, no en 4.225 (18,4% de los geocodificados). Se usa para resolver los duplicados por ID |
| `dist_barrio_busqueda_m` | Distancia del punto al polígono del barrio buscado | Numérica continua; m | 0 si cae adentro. Mediana 0 |
| `geo_dudoso` ★ | Geocodificación dudosa | Booleana (1/0) | Punto a más de 1 km del barrio buscado (`umbral_geo_dudoso_m`): el normalizador encontró una calle homónima en otro barrio o la dirección está mal cargada. 249 avisos. En la etapa 6 se tratan como sin coordenadas y quedan fuera de los análisis espaciales |
| `en_barrio_popular` | El punto cae en un barrio popular | Booleana (1/0) | Polígonos de barrios populares de BA Data. 96 avisos |
| `tipo_barrio_popular` | Tipo del barrio popular | Categórica nominal | Villa (11), Barrio municipal (76), Barrio urbanizado (9); con polígonos superpuestos, el tipo más informal |

**`permisos_obra.tsv`** (`src/permisos_obra.py`): 27.922 filas × 2 columnas.

| Variable | Significado | Tipo y unidad | Fórmula final |
|---|---|---|---|
| `permisos_obra_500m` ★ | Obras nuevas cerca del aviso: señal de dinamismo de la zona | Numérica discreta; obras | Parcelas con permiso de obra nueva o ampliación mayor a menos de 500 m, entre el 14/08/2023 y el 13/08/2026, contadas una vez por obra (deduplicadas por parcela y por punto). Mediana 9 obras en CABA. En el modelo entra como `permisos_obra_10` (cada 10 obras) |

### Creadas por la etapa 6 (precio esperado, brecha, regla y ranking; notebooks 03, 04 y 07)

**`precio_esperado.tsv`**: una fila por aviso del dataset limpio (27.578 × 77), unible por `id_aviso`. Lo escribe
`src/analisis.py`; los notebooks lo leen y lo explican. Los números son los de la regeneración del 02/11/2026 en la Mac
de referencia.

*Modelo, intervalo y marcas*

| Variable | Significado | Tipo y unidad | Fórmula final |
|---|---|---|---|
| `unidad` | Identificador de la unidad (dirección limpia y superficie) | Numérica discreta (25.169 unidades) | `modelo.grupo_de_unidad`: numera las unidades por orden de aparición. Avisos con la misma dirección y m² pero pisos distintos son unidades separadas. Define las vueltas de la validación (todos los avisos de una unidad caen en la misma vuelta) |
| `vuelta` | Vuelta de la validación cruzada que predijo el aviso | Numérica discreta (0 a 4) | `modelo.folds_agrupados`, 5 vueltas agrupadas por unidad con semilla 42 |
| `modelo_oficial` | Modelo que produjo el precio esperado | Texto | `analisis.modelo_oficial` de `config.yaml`: `lineal_ampliado` (la decisión está en el notebook 04, sección 8). El otro modelo, el gradient boosting, da la segunda opinión |
| `zona` | Zona de referencia del aviso | Categórica nominal (214 zonas) | `subzona` en los barrios donde la sub-zona reduce el error de referencia fuera de muestra **y** es estable (ARI con bootstrap ≥ 0,7; hoy Villa Santa Rita no lo es y se compara entero); `barrio` en el resto, para los avisos sin coordenadas o con `geo_dudoso` y para las zonas con menos de 10 avisos. Se decide dentro de cada vuelta, sin fuga. En 12.607 avisos la zona es el barrio |
| `precio_m2_mediana_zona` | La referencia simple | Numérica continua; USD/m² | Mediana del precio por m² de la zona, calculada en las otras vueltas |
| `precio_m2_esperado` ★ | Precio por m² esperado para las características y la zona del aviso | Numérica continua; USD/m² | exp de la predicción del modelo oficial: regresión lineal de log(`precio_m2_usd`) sobre características, estado según el título y zona, ajustada **fuera de muestra** en las otras 4 vueltas, sin los atípicos (IQR sobre el log, en la zona, calculados con las vueltas de entrenamiento). Características en `src/modelo.py` (`matriz_caracteristicas()`) y `src/validacion.py` (`caracteristicas_ampliadas()`). Error mediano fuera de muestra 12,5% |
| `precio_m2_esperado_inf`, `precio_m2_esperado_sup` ★ | Rango del 80% del precio esperado | Numérica continua; USD/m² | Intervalo de predicción conformal cruzado, por barrio (barrios con menos de 50 avisos en las otras vueltas usan el de la ciudad). Cobertura fuera de muestra 79,5%; semiancho mediano ±28%. **La ficha muestra el rango, no un único número** |
| `brecha` ★ | Brecha de precio | Numérica continua; proporción (−0,25 = 25% por debajo) | `precio_m2_usd` / `precio_m2_esperado` − 1 |
| `brecha_otro_modelo` | Brecha con la segunda opinión (gradient boosting) | Numérica continua; proporción | Ídem con el modelo no oficial. Puede variar un poco entre plataformas (`docs/pipeline.md`, sección 10) |
| `debajo_del_intervalo` | El precio publicado está por debajo del rango del 80% | Booleana | `precio_m2_usd` < `precio_m2_esperado_inf`. True en 2.821 |
| `marcado` ★ | Precio atípicamente bajo para investigar | Booleana | `brecha` < −0,25 (`analisis.umbral`: dos veces el error mediano del modelo). True en 1.819 (6,6%) |
| `marcado_otro_modelo` | Marcado por la segunda opinión | Booleana | `brecha_otro_modelo` < −0,25. True en 1.447 |
| `marcado_consenso` | Marcado por los dos modelos | Booleana | `marcado` y `marcado_otro_modelo`. True en 1.124. Prioriza dentro de la lista; no cambia quién entra |
| `marcado_barrio` | Marcado con un umbral ajustado al error de su barrio | Booleana | `brecha` < −2 × error mediano del modelo en su barrio (barrios con menos de 50 avisos: el de la ciudad). True en 1.556 |
| `senal_m2_por_ambiente`, `senal_superficie_recuperada`, `senal_dormitorios`, `senal_piso`, `senal_alquiler` | Señales de que el dato puede estar mal | Booleanas | m² por ambiente fuera del 1% a 99% (533); `m2_origen` recuperada de la total (32); `incoherencia_dormitorios` (376); `incoherencia_piso` (80); `menciona_alquiler` (162) |
| `senal_error_carga` | Alguna señal de error de carga | Booleana | Alguna de las cinco anteriores. True en 1.161 |
| `cumple_regla` ★ | Pasa la regla R1: marcado con el umbral de la ciudad y el de su barrio, y sin señales de error de carga | Booleana | `marcado_barrio` y no `senal_error_carga`. True en 1.455 avisos (1.375 unidades): **la lista oficial de señales a investigar** |

*Estado y riesgo legal según el título* (`estado_y_riesgo_del_titulo()` con las expresiones regulares de
`config/costos.yaml`; reemplazan a las `marcas_del_titulo` de la PE2, que el notebook 03 conserva)

| Variable | Significado | Tipo y unidad | Fórmula final |
|---|---|---|---|
| `estado_titulo` ★ | Estado del inmueble declarado en el título | Categórica nominal: `sin_marca` (25.787), `a_estrenar` (868), `ya_reformado` (671), `a_reciclar` (141), `a_refaccionar` (111) | Primera expresión regular que coincide, en el orden de `estado_refaccion` de `costos.yaml`. **Entra al modelo oficial** (lineal ampliado) como característica y a la regla de decisión como nivel de refacción. Primas fuera de muestra: a reciclar −18%, a refaccionar −16% |
| `riesgo_<señal>` | Una columna por señal de riesgo legal en el título | Booleanas (11) | `riesgo_legal` de `costos.yaml`: con inquilino (201), con financiación (197), en pozo (169; "en pozo" en el título de un aviso que no declara antigüedad negativa), no apto crédito (6), nuda propiedad (4), sucesión (1), sin escritura (1), parte indivisa (1), ocupado, subasta y crédito pendiente (0) |
| `titulo_casa`, `titulo_tipo_casa`, `titulo_barrio_popular`, `bajo_de_precio` | Copiadas del dataset limpio | Booleanas | Ver arriba |

*KPIs y variables de ubicación* (copiadas de `accesibilidad.tsv` y `permisos_obra.tsv` para que el notebook 05 y el
dashboard no tengan que unir archivos)

| Variable | Significado | Tipo y unidad | Fórmula final |
|---|---|---|---|
| `tasa_completitud` | KPI: proporción de campos con dato, entre los 26 donde el vacío es falta de dato | Numérica continua; proporción | Promedio de `notna()` sobre las 16 dicotómicas Sí/No y 10 atributos principales. Mediana 0,88 |
| `expensas_usd_m2` | Expensas por m² | Numérica continua; USD por m² por mes | `expensas_usd / m2_final`. 22.884 con dato |
| `expensas_rel_zona` | KPI eficiencia de expensas: expensas por m² relativas a su zona | Numérica continua; log (0 = típica de la zona) | log(`expensas_usd_m2`) menos la mediana del log en su `zona` |
| `geo_dudoso`, `barrio_oficial`, `en_barrio_popular`, `tipo_barrio_popular`, `dist_tren_m`, `dist_metrobus_m`, `dist_riel_m`, `dist_transporte_pesado_m`, `dist_espacio_verde_m`, `area_verde_500m_ha`, `permisos_obra_500m` | Fuentes externas por aviso | Ver la sección anterior | Unidas por `link`. En los 244 avisos con `geo_dudoso` dentro del dataset limpio, `lat`, `lon` y las distancias quedan vacías: se tratan como sin coordenadas |
| `dist_transporte_m`, `lat`, `lon` | Copiadas del dataset enriquecido | Ver el diccionario | Con dato en 22.389 avisos (sin los `geo_dudoso`) |

*Regla de decisión* (`src/regla.py` con `config/costos.yaml`, escenario base; notebook 07). Todas con dato en los
27.578 avisos, aunque solo tienen sentido para los que cumplen la regla.

| Variable | Significado | Tipo y unidad | Fórmula final |
|---|---|---|---|
| `prima_estado` | Prima (log) del estado del título en el modelo oficial | Numérica continua; log | Promedio del coeficiente de `estado_titulo` en las 5 vueltas; 0 para `sin_marca`. Negativa en "a reciclar" y "a refaccionar": se descuenta al vender refaccionado |
| `nivel_refaccion` | Nivel de refacción que se asume por el estado | Categórica nominal: `ninguna` (1.539), `liviana` (25.787), `media` (111), `integral` (141) | `estado_refaccion` de `costos.yaml`: a estrenar y ya reformado, ninguna; sin marca, liviana (pintura y detalles); a refaccionar, media (baño y cocina); a reciclar, integral (USD/m² con IVA) |
| `costo_entrada_usd` | Costos de compra | Numérica continua; USD | Precio publicado × (escribano + Sellos según el umbral de USD 148.941, mitad del comprador + comisión + otros). Se compra al precio publicado: supuesto conservador |
| `refaccion_usd` | Costo de la refacción | Numérica continua; USD | Según `nivel_refaccion` y `m2_final`, valor central de `costos.yaml` |
| `costo_total_usd` | Lo que cuesta tener la unidad lista para vender | Numérica continua; USD | `precio_usd` + `costo_entrada_usd` + `refaccion_usd` |
| `valor_salida_usd` | Valor al que se espera vender | Numérica continua; USD | `precio_m2_esperado` × `m2_final`; si se refacciona (nivel medio o integral), sin la prima negativa del estado (se compra en mal estado y se vende refaccionado) |
| `venta_cierre_usd` | Venta a precio de cierre | Numérica continua; USD | `valor_salida_usd` × (1 − 4,79%): brecha publicado-cierre |
| `costo_salida_usd` | Costos de venta | Numérica continua; USD | Comisión del vendedor, mitad de Sellos y certificados, sobre la venta de cierre |
| `impuesto_usd` | Impuesto a las ganancias sobre el resultado | Numérica continua; USD | Alícuota 0 en el escenario base (**supuesto declarado:** depende de la forma jurídica del fondo). El notebook 07 y el simulador del dashboard muestran 15% y 35% |
| `resultado_usd` | Resultado neto de la operación | Numérica continua; USD | `venta_cierre_usd` − `costo_salida_usd` − `impuesto_usd` − `costo_total_usd` |
| `brecha_neta` ★ | Margen neto sobre lo invertido | Numérica continua; proporción | `resultado_usd` / `costo_total_usd`. Mediana entre las señales: 12,3% |
| `riesgo_descartar` | Señales de riesgo legal que descartan el aviso | Texto (vacío si no hay) | Señales con acción `descartar` en `costos.yaml`: en pozo (169), nuda propiedad (4), parte indivisa (1), sin escritura (1) |
| `riesgo_revisar` | Señales que piden revisar antes de avanzar | Texto (vacío si no hay) | Señales con acción `revisar`: con inquilino (200), con financiación (196), no apto crédito (6), sucesión (1) |
| `candidato` ★ | Candidato después de costos | Booleana | `cumple_regla` y `brecha_neta` ≥ 10% (`umbral_brecha_neta`) y sin `riesgo_descartar`. True en 884 avisos (840 unidades). **Nunca "oportunidad confirmada"**: depende del precio esperado, que tiene error, y de supuestos de costos |
| `nivel_decision` | Nivel del aviso en la regla | Categórica ordinal: vacío (26.123), `señal a investigar` (571), `candidato después de costos` (884) | Vacío si no cumple la regla R1 |
| `motivo_decision` | Por qué una señal no llega a candidato | Texto | "brecha neta X% < 10%" o "riesgo legal: <señal>"; vacío en el resto |
| `tasa_salida_ambientes` | Liquidez informativa: tasa de salida del portal entre relevamientos de los avisos con la misma cantidad de ambientes | Numérica continua; proporción | `seguimiento_avisos.csv`, sin barrios truncados, por ambientes (1 a 5+): 41% para 1, 43% para 2, 40% para 3, 38% para 4, 31% para 5 o más. Salir del portal no prueba una venta |

**`unidades_marcadas.csv`** (1.714 filas × 39) y **`avisos_a_investigar.csv`** (1.375 filas × 35): una fila por
unidad, representada por el aviso que llega más lejos en el embudo y, a igualdad, el más barato. La primera tiene
todas las unidades con algún aviso marcado y las columnas `marcado`, `marcado_barrio`, `cumple_regla` y `candidato`
del paso al que llega; la segunda es **la lista oficial** (unidades que cumplen la regla R1), ordenada por `posicion`
(primero los candidatos, después por brecha). Además de las columnas de arriba (`brecha_%`, `brecha_otro_modelo_%`,
`brecha_neta_%` y `tasa_salida_ambientes_%` van en porcentaje):

| Variable | Significado | Tipo y unidad | Fórmula final |
|---|---|---|---|
| `posicion` | Orden en la lista oficial | Numérica discreta | Candidatos primero; dentro de cada nivel, brecha más negativa primero |
| `avisos_de_la_unidad` | Cuántos avisos marcados repiten la misma unidad | Numérica discreta | Conteo por `unidad` entre los marcados. Más de 1 en 178 unidades |
| `brecha_min_%`, `brecha_max_%` | Rango de brechas de los avisos de la unidad | Numérica continua; % | Mínimo y máximo de `brecha` entre los avisos de la unidad |
| `avisos_discordantes` | Los avisos de la unidad no coinciden en si están marcados | Booleana | Algún aviso de la unidad marcado y otro no. True en 114 |

**`embudo_ranking.csv`**: 5 filas, una por paso (`analizados`, `marcado`, `marcado_barrio`, `cumple_regla`,
`candidato`), con el filtro en palabras, `avisos`, `unidades` y el porcentaje respecto del paso anterior. Es la
reconciliación de universos que pidió la devolución de la PE2: 27.578 / 25.169 → 1.819 / 1.714 → 1.556 / 1.470 →
1.455 / 1.375 → 884 / 840.

**`explicacion_avisos.tsv`** (1.819 filas × 16, una por aviso marcado): la ficha del dashboard. `precio_m2_referencia_zona`
es el precio por m² de un aviso típico de la zona según el modelo oficial, `precio_m2_esperado` el del aviso, y `sube_1`
a `sube_3` y `baja_1` a `baja_3` (con su `_%`) las tres características que más suben y más bajan su precio esperado
respecto de esa referencia, con `resto_%` para las demás. Son contribuciones exactas del modelo lineal (suman la
diferencia entre referencia y esperado); explican al modelo, no causas.

### Segundo relevamiento (`src/seguimiento.py`, pregunta P4, notebook 05)

**`relevamiento_2.tsv`**: 27.516 avisos del scraping del 27 y 28/10/2026 (`fecha_relevamiento`, `archivo`), con las
86 columnas del scraper más `id_aviso`, `precio_usd`, `bajo_de_precio`, `m2_final`, `m2_origen`, `dir_limpia` y
`clave_unidad` (dirección limpia, m² y ambientes), calculadas con las mismas funciones de la limpieza.

**`seguimiento_avisos.csv`**: una fila por aviso del dataset limpio (27.578 × 9), en el mismo orden.

| Variable | Significado | Tipo y unidad | Fórmula final |
|---|---|---|---|
| `clave_unidad` | Clave de republicación | Texto | `dir_limpia` + m² + ambientes (ambientes como número decimal: con enteros contra texto no coincidía nada) |
| `estado` ★ | Qué pasó con el aviso 74 días después | Categórica nominal: `sigue` (9.352), `republicado` (6.463), `salio` (11.763) | Sigue: el mismo ID está en el segundo relevamiento. Republicado: el ID no está, pero hay un aviso nuevo con la misma `clave_unidad`. Salió: ninguna de las dos |
| `precio_r2` | Precio en el segundo relevamiento | Numérica continua; USD | Del aviso con el mismo ID o del republicado. 15.815 con dato |
| `cambio_precio` | Variación del precio entre relevamientos | Numérica continua; proporción | `precio_r2` / `precio_usd` − 1 |
| `bajo_en_r2`, `subio_en_r2` | Bajó o subió más de 0,5% | Booleanas | `cambio_precio` < −0,005 (4.998); > 0,005 (595) |
| `barrio_truncado` | El barrio llegó al tope de paginación en alguno de los dos relevamientos | Booleana | Palermo, Belgrano, Caballito y Recoleta (7.999 avisos): ahí no aparecer no significa haber salido. Se excluyen del análisis de salida |
| `salio` ★ | Salió del portal | Booleana | `estado` = `salio`. Entre los no truncados: 46,7% de los marcados contra 39,7% del resto. **Salir no es venderse**: puede ser venta, retiro o una republicación no detectada |

### Campos del dashboard (`docs/dashboard/data/avisos.json`, `src/exportar_dashboard.py`)

Una fila por unidad de la lista oficial (1.375), con lo que muestran la tabla, la ficha, el mapa y el simulador del
dashboard. Casi todo viene de `precio_esperado.tsv` y `avisos_a_investigar.csv` sin redondear a mano (los porcentajes
se expresan en puntos, de ahí el sufijo `_pct`); los campos marcados "solo dashboard" se calculan en el exportador y
no cambian la lista oficial ni ningún conteo del análisis.

| Campo | Significado | Tipo y unidad | De dónde sale |
|---|---|---|---|
| `id`, `posicion` | ID de MercadoLibre y posición en el ranking | Texto; entero 1 a 1.375 | `avisos_a_investigar.csv` (`id_aviso`, `posicion`) |
| `barrio`, `barrio_nombre`, `zona` | Barrio de búsqueda (slug y nombre) y zona de referencia (sub-zona o barrio) | Texto | `precio_esperado.tsv` |
| `titulo`, `link` | Título y link del aviso, sin los parámetros de tracking | Texto | `propiedades_limpias.tsv` |
| `lat`, `lon` | Coordenadas con 5 decimales; `null` sin coordenadas o con geocodificación dudosa | Numéricas; grados | `precio_esperado.tsv` |
| `precio_usd`, `m2`, `ambientes`, `antiguedad` | Precio publicado, superficie, ambientes y antigüedad | Numéricas; USD, m², unidades, años | `precio_usd`, `m2_final`, `ambientes`, `antiguedad` |
| `precio_m2`, `precio_m2_esperado`, `precio_m2_inf`, `precio_m2_sup` | Precio por m² publicado, esperado y límites del intervalo del 80% | Numéricas; USD por m² | `precio_m2_usd`, `precio_m2_esperado`, `precio_m2_esperado_inf`, `_sup` |
| `precio_m2_referencia_zona` | Mediana del precio por m² de la zona de referencia, fuera de muestra | Numérica; USD por m² | `precio_m2_referencia_zona` |
| `brecha_pct`, `brecha_otro_modelo_pct` | Brecha del modelo oficial y del gradient boosting | Numéricas; puntos porcentuales | `brecha` × 100; `brecha_otro_modelo_%` del ranking |
| `consenso` ★ | Los dos modelos lo marcan (brecha menor a −25% en ambos) | Booleana | `marcado_consenso` |
| `debajo_del_intervalo` | El precio publicado queda por debajo del límite inferior del 80% | Booleana | `debajo_del_intervalo` |
| `avisos_de_la_unidad`, `avisos_discordantes` | Cuántos avisos tiene la unidad y si alguno no está marcado | Entero; booleana | `avisos_a_investigar.csv` |
| `bajo_de_precio`, `tasa_completitud` | "BAJÓ DE PRECIO" en el primer relevamiento; completitud de la ficha | Booleana; proporción 0 a 1 | Limpieza (notebook 01) y etapa 6 |
| `estado`, `estado_nombre`, `prima_estado` | Estado del inmueble según el título (`sin_marca`, `a_estrenar`, `ya_reformado`, `a_reciclar`, `a_refaccionar`), su nombre y su prima en el modelo | Texto; texto; proporción | `estado_titulo`, `prima_estado` |
| `nivel_refaccion` | Nivel de refacción que asume la regla en cada escenario (`central`, `baja`, `alta`): `ninguna`, `liviana`, `media` o `integral` | Objeto de texto | `regla.nivel_de_refaccion` con `config/costos.yaml` |
| `riesgo_descartar`, `riesgo_revisar` | Señales legales del título que descartan o piden revisar; vacío si no hay | Texto | `precio_esperado.tsv` |
| `titulo_casa`, `titulo_barrio_popular`, `geo_dudoso` | Marcas del título y de la geocodificación | Booleanas | Limpieza y `accesibilidad.tsv` |
| `dist_barrio_popular_m` | Distancia al barrio popular más cercano; `null` sin coordenadas | Entero; metros | Solo dashboard: polígonos de BA Data proyectados |
| `exclusiones` ★ | Motivos por los que el aviso no entra a la lista destacada del resumen: `barrio popular`, `a menos de 500 m de un barrio popular`, `casa`, `PH`, `uso comercial u oficina`, `barrio dudoso`, `posible venta de varias unidades`, `precio posiblemente con financiación`, `en pozo: precio no comparable con usados`; lista vacía si no tiene | Lista de texto | Solo dashboard: regex sobre el título y distancia (`exclusiones_del_destacado`). No cambia la lista oficial |
| `segmento` | Tipo de departamento del notebook 06 (`Compactos de edificio antiguo`, `Nuevos con amenities`, `Familiares amplios y antiguos`, `Chicos y recientes`); en "Familiares amplios y antiguos" la ficha muestra una alerta de revisión | Texto | Solo dashboard: `segmento_por_aviso` reproduce el MCA y el K-means del 06 con la misma semilla |
| `estado_r2` | Qué pasó con el aviso en el segundo relevamiento: `sigue`, `republicado` o `salio` | Categórica nominal | `seguimiento_avisos.csv` (`estado`) |
| `brecha_neta_pct` ★ | Brecha neta de costos en el escenario base (resultado sobre costo total) | Numérica; puntos porcentuales | `brecha_neta` × 100 |
| `nivel` ★ | Nivel de decisión: `señal a investigar` o `candidato después de costos` | Categórica | `nivel_decision` |
| `firme` ★ | Candidato firme: sigue siendo candidato vendiendo al límite inferior del rango del 80% (83 unidades) | Booleana | Solo dashboard: `unidades_firmes`, misma regla del notebook 07 |
| `motivo` | Por qué no es candidato (por ejemplo "brecha neta 6% < 10%"); vacío si lo es | Texto | `motivo_decision` |
| `costos` | Cascada del escenario base: `entrada`, `refaccion`, `total`, `valor_salida`, `venta_cierre`, `salida`, `resultado` | Objeto numérico; USD | `costo_entrada_usd`, `refaccion_usd`, `costo_total_usd`, `valor_salida_usd`, `venta_cierre_usd` y derivados |
| `tasa_salida_ambientes_pct` | Tasa de salida del portal de los avisos con la misma cantidad de ambientes (liquidez, informativa) | Numérica; puntos porcentuales | `tasa_salida_ambientes` × 100 |
| `factores` | Hasta tres factores que más suben y tres que más bajan el precio esperado del aviso respecto del típico de su zona, con su efecto | Lista de objetos (`factor`, `efecto_pct`) | `explicacion_avisos.tsv` (modelo oficial) |

Los nombres de los segmentos son los de `segmentos.nombrar_segmentos`; si un nombre no coincide con esta lista, manda
el notebook 06. `resumen.json` lleva los indicadores, el embudo, la sensibilidad y los parámetros de costos por
escenario; `estaciones.json`, las capas de transporte; `fondo.json`, todos los avisos con coordenadas para el fondo
del mapa.

## Resumen de anomalías y qué se hizo con cada una

Problemas detectados en las 93 columnas originales y su resolución en la limpieza (etapa 5, notebook 01) o en el
modelo (etapa 6, notebooks 03 y 04). "Se acepta" quiere decir que se deja como está y se declara como limitación. Las
filas marcadas con **PE3** cambiaron respecto de la PreEntrega 2.

| Problema | Columna | Filas | Resolución |
|---|---|---|---|
| Precio anterior y vigente concatenados por "BAJÓ DE PRECIO" | `precio` | 627 | Corregido: `precio_usd` toma el monto vigente |
| Precios en USD mayores a 10 millones que no son de la baja | `precio` | 4 | 1 se excluye como `precio_imposible`. Los otros 3 son edificios enteros en Belgrano (USD 12 millones, 367 m²): quedan como atípicos y no se usan para ajustar el modelo |
| Precios menores a USD 20.000 | `precio` | 4 | Excluidos (`precio_menor_a_minimo`) |
| Precios en ARS que no cierran como pesos | `precio`, `moneda` | 5 | Excluidos (`precio_en_pesos`) |
| **PE3** Avisos que no son una venta ("compro", "compramos") | `titulo` | 1 | Excluido (`no_es_venta`) |
| Superficie menor a 15 m² en el listado | `m2` | 36 | Se recupera de `superficie_total` si está en rango (32 en el dataset limpio); si no, se excluye (`superficie_invalida`) |
| `m2` mezcla superficie cubierta y total | `m2`, `superficie_total` | 527 avisos con total en la tarjeta, más los recuperados | Se acepta: `m2_final` es la cubierta en el 98% de los avisos y `m2_origen` guarda los recuperados |
| Superficie en hectáreas ("0 ha", "0,01 ha", "42 ha") | `superficie_total` | 73 | Pasa a vacío; se usa `m2` |
| Coma decimal en superficies de la ficha | superficies de la ficha | 1.589 / 1.494 / 2.401 | `parsear_superficie()` |
| Punto de miles ambiguo | superficies de la ficha | 9 / 9 / 1 | Pasa a vacío |
| Ceros y negativo que son faltantes | `ambientes` | 312 + 1 | Pasan a vacío. En el modelo se completan con dormitorios + 1 |
| **PE3** Ceros que son faltantes | `banos` | 313 (303 en el dataset limpio) | Pasan a vacío. En el modelo se completan con 1 más la marca `banos_sin_dato` (en la PE2 no se corregían) |
| Dormitorios mayor o igual que ambientes | `dormitorios`, `ambientes` | 1.717; 376 en el dataset limpio sin contar el monoambiente 1/1 | Marcados (`incoherencia_dormitorios`); el tamaño se mide con la superficie |
| 99 como valor de relleno | `departamentos_por_piso` | 6.970 | Pasa a vacío |
| Años y valores imposibles | `cantidad_de_pisos` | 12 mayores a 60 | Se acepta: la variable no entra al modelo |
| **PE3** Números de unidad cargados como piso | `numero_de_piso_de_la_unidad` | 19 de 100 o más | Se quedan con las centenas (1203 es el piso 12). La incoherencia de piso solo se mide cuando el edificio declara 3 pisos o más (80 marcados; en la PE2, 2.299) |
| Antigüedad negativa (unidades en pozo) | `antig_edad` | 235, más 2 "40.000 años" que el parser deja negativos | Excluidos (`en_pozo`, 237) |
| Año de construcción en lugar de antigüedad | `antig_edad` | 66 | Convertido a edad |
| Antigüedad entre 151 y 1.799 o no numérica | `antig_edad` | 6 + 1 | Pasa a vacío |
| Antigüedad "1 años" (posible carga por defecto de "a estrenar") | `antig_edad` | 1.479 | Se acepta: queda en el tramo de 0 a 5 años, que es donde caería un "a estrenar" |
| Expensas en cero | `expensas` | 3.805 | Pasan a vacío |
| **PE3** Expensas en ARS entre 1 y 1.000 | `expensas` | 267 | Pasan a vacío: son valores de relleno (en la PE2 se aceptaban). Importa para el KPI de eficiencia de expensas |
| Expensas en ARS mayores a 10 millones | `expensas` | 13 | Pasan a vacío |
| Expensas que no se pueden convertir a número | `expensas` | 40 | Pasan a vacío |
| Expensas en USD no confiables | `expensas` | 41 | Las de 10.000 o más se leen como pesos; las menores a 10, vacío. Quedan 27 en USD, convertidas con el dólar MEP |
| **PE3** Mismo aviso en dos filas | `link` | 136 filas (68 sobrantes) | Deduplicado por `id_aviso`: queda la fila cuyo barrio coincide con el polígono oficial (17, de las cuales 12 cambian de barrio respecto de la PE2) y, si no, la primera, siempre en la posición de la primera aparición |
| Misma unidad publicada con otro ID | varias | 3.059 | Marcados (`posible_duplicado`), no se borran. En el modelo, las vueltas de la validación se arman por unidad para que no estén de los dos lados |
| **PE3** Casas publicadas como departamento | `titulo` | 25 ("casa") y 51 ("tipo casa") | Marcadas (`titulo_casa`, `titulo_tipo_casa`), no se excluyen; `titulo_casa` se muestra en el ranking |
| Avisos clasificados como PH | `tipo_de_departamento` | 60 | Se conservan: el anunciante los publicó como departamento |
| Dos etiquetas para la misma categoría | `tipo_de_seguridad`, `tipo_de_departamento` | 26 ("24 hs") y 31 ("Penthhouse") | Unificadas en la limpieza ("24 horas", "Penthouse") |
| "No" que no significa ausencia | `cocina`, `living`, `comedor` | 5.907 / 14.638 / 11.143 | No se usan en el modelo |
| **PE3** Barrio no oficial y barrios oficiales ausentes | `barrio` | 801 en "barrio-norte"; San Cristóbal y Parque Chas sin avisos | Se acepta: el barrio de búsqueda es la categoría donde el comprador encuentra el aviso. El cruce con los polígonos oficiales (`barrio_oficial`, `barrio_coincide`) se usa como control: 4.225 de los 22.912 avisos geocodificados (18,4%) caen en otro polígono, casi todos de borde (a menos de 1 km) |
| **PE3** Geocodificación dudosa | `lat`, `lon` | 249 (244 en el dataset limpio) | Punto a más de 1 km del barrio buscado (`geo_dudoso`): se tratan como sin coordenadas en la etapa 6 y las sub-zonas se recalculan sin ellos |
| **PE3** Avisos en barrios populares | `lat`, `lon`, `titulo` | 96 por polígono, 2 por el título | Marcados (`en_barrio_popular`, `tipo_barrio_popular`, `titulo_barrio_popular`); el modelo los compara con el resto del barrio y la marca se muestra como alerta |
| Barrios truncados por el tope de paginación | `barrio` | 4 barrios con 2.016 avisos | Se acepta y se declara como limitación; se excluyen del análisis de salida del segundo relevamiento |
| **PE3** Sub-zonas con menos de 30 avisos o inestables | `subzona` | 42 de 198 con menos de 30 avisos; 1 barrio inestable (Villa Santa Rita, ARI 0,68) | El modelo elige barrio por barrio, dentro de cada vuelta, si la sub-zona mejora la referencia; vuelve al barrio en zonas con menos de 10 avisos y en los barrios con sub-zonas inestables (ARI < 0,7) |
| Avisos sin coordenadas | `lat`, `lon`, `subzona` | 5.010 (17,9%), más los 244 dudosos | Se comparan contra su barrio en el modelo |
| Columnas constantes | `tipo`, `es_emprendimiento` | Todas | Se conservan en el archivo, pero no se usan |
