# TP 1: Fondo de Inversión Inmobiliario (CABA)

**Analítica Descriptiva, ITBA, 2026 C2**

Detección sistemática de departamentos usados en venta en la Ciudad Autónoma de
Buenos Aires cuyo nivel de confort está por encima de lo que su precio por metro
cuadrado sugeriría dentro de su zona, con el fin de identificar oportunidades de
inversión potencialmente subvaluadas.

> **Reproducibilidad.** El pipeline corre de punta a punta sin editar una sola
> línea de código. Clonar, `pip install -r requirements.txt`, `python3 run_pipeline.py`.
> Todas las rutas son relativas a la raíz del repositorio y todos los parámetros
> están en `config/config.yaml` o en flags de línea de comandos.
> Ver [Instalación](#11-instalación), [Cómo correr el pipeline](#12-cómo-correr-el-pipeline)
> y [Verificación](#15-verificación).

---

## 1. Contexto y situación de negocio

La unidad de negocio es un **fondo de inversión inmobiliario** que opera en los 47
barrios de CABA.

La hipótesis de partida es simple: dos departamentos ubicados en el mismo barrio y
en la misma zona, porque no es lo mismo Palermo Chico que Palermo Soho, y
publicados aproximadamente al mismo precio pueden ofrecer niveles de comodidad muy
distintos. El mercado no siempre le asigna a esas comodidades un valor extra, y ahí
aparece la oportunidad.

Para elegir con criterio, el fondo define un **índice de confort propio (1 a 10)**
compuesto por tres bloques:

| Bloque | Peso | Qué incluye | Por qué ese peso |
|---|---|---|---|
| Infraestructura básica | **45%** | Gas, aire acondicionado, internet, agua, etc. | Define si una propiedad es habitable en condiciones normales |
| Amenities y servicios del edificio | **30%** | Pileta, gimnasio, sauna, SUM, etc. | Mejoran calidad de vida y precio de reventa, pero no son indispensables |
| Atributos propios del departamento | **25%** | Piso, frente/contrafrente, balcón, terraza | Posicionamiento dentro del edificio: luz y vista pesan sobre el confort real |

Dentro de cada bloque, los elementos más esenciales (gas, agua) tienen mayor
ponderación.

**La ubicación no forma parte del índice**, de forma deliberada: la idea es comparar
departamentos de una misma zona entre sí. El índice se contrasta luego contra el
precio del metro cuadrado de propiedades similares de esa misma zona, para detectar
si el confort ofrecido está sistemáticamente por encima de lo que el precio sugiere.

### Unidad de comparación: la sub-zona

Un barrio no es homogéneo. La comparación se hace a nivel de **sub-zona**, una
subdivisión geográfica dentro de cada barrio construida por clustering espacial a
partir de la ubicación de las propiedades (198 sub-zonas en total). Cuando una
sub-zona no alcanza el mínimo de propiedades necesario para ser estadísticamente
confiable, la comparación cae al **barrio completo** como nivel de respaldo.

### Capa complementaria: variables de entorno

Además de las características internas, el análisis incorpora accesibilidad al
transporte público (distancia a la estación de subte más cercana) y cercanía a los
polos de centralidad. Estas variables **no** integran el índice de confort: se usan
para distinguir una oportunidad genuina de un caso donde el menor precio se explica
simplemente por una peor ubicación.

> **Hallazgo preliminar:** contrario a lo que ocurre en muchas ciudades, en CABA la
> cercanía al microcentro no explica el precio por m². Los barrios de mayor valor
> (Palermo, Belgrano, Núñez, Colegiales) están en el corredor norte, a varios
> kilómetros del centro geográfico, mientras que zonas plenamente céntricas como
> Constitución o La Boca están entre las más económicas. Esto responde a una
> transición urbana en curso: el eje corporativo y residencial premium se viene
> desplazando hacia el norte. Por eso la distancia a la centralidad se calcula e
> incorpora, pero se asume que su poder explicativo sobre el precio es limitado.

---

## 2. Hipótesis

1. **El mercado no incorpora completamente el valor del confort en el precio de
   publicación.** Dentro de una misma zona existen propiedades con un índice de
   confort significativamente superior al de sus comparables que, sin embargo, se
   publican a un precio por m² similar o inferior. Esas propiedades constituyen
   oportunidades de inversión subvaluadas.

2. **Un barrio no es una unidad homogénea de precios.** Existe variación
   significativa del precio por m² entre las distintas sub-zonas de un mismo
   barrio; comparar a nivel de sub-zona produce una vara de referencia más precisa
   que comparar a nivel de barrio completo.

3. **Parte de la variación de precios entre zonas se explica por variables de
   entorno**, principalmente accesibilidad al transporte y cercanía a la
   centralidad. Incorporarlas permite depurar las oportunidades detectadas,
   distinguiendo las genuinas de aquellas cuyo menor precio responde a una peor
   ubicación.

---

## 3. Preguntas clave por nivel de análisis

### Descriptivo: ¿qué pasó, qué está pasando?

- ¿Cómo se distribuye el índice de confort dentro de cada zona, y cuánto pesa cada
  bloque (infraestructura básica, amenities, atributos propios) por separado en ese
  promedio?
- ¿Qué tan completos están los datos de las columnas de amenities? Si un amenity
  como gimnasio tiene la celda vacía, ¿es dato faltante o ausencia real del
  amenity? Hay que medir cuánto hay de cada uno para no comprometer la
  confiabilidad del índice.
- ¿Existen propiedades con perfiles contradictorios (amenities de lujo pero sin
  infraestructura básica)? Si existen, ¿el índice las penaliza más que una simple
  suma?
- ¿El índice de confort depende del tamaño de la propiedad, o son independientes?

### Diagnóstico: ¿por qué pasó, por qué sucede?

- ¿Los pesos asignados a mano se sostienen con los datos reales? En una regresión
  de precio por m² contra cada bloque, ¿la infraestructura básica explica precios
  más elevados que los amenities, o el mercado paga más por la belleza que por lo
  esencial?
- ¿Las expensas se comportan como esperamos (a más confort, expensas más caras)? Si
  una propiedad tiene gran confort y expensas bajas, ¿es un buen negocio o una
  señal de que el edificio no mantiene bien los amenities?
- ¿La relación entre índice de confort y precio por m² tiene la misma fuerza en
  todos los segmentos de precio de una misma zona, o el confort se paga más caro en
  la gama alta que en la gama media?
- ¿Cuánto del precio por m² de una zona se explica por accesibilidad y centralidad?
  Al comparar propiedades con gap de confort positivo, ¿ese gap se sostiene cuando
  se controla por ubicación?

### Predictivo: ¿qué pasará?

- Con la curva de referencia por zona (precio por m² según índice de confort), ¿se
  puede marcar automáticamente como oportunidad cualquier aviso nuevo, o hace falta
  research más profundo?
- De los tres bloques del índice, ¿cuál es el que está más "regalado" con mayor
  frecuencia?
- Si se repite el scraping más adelante, ¿el gap de confort de las oportunidades
  detectadas hoy se reduce o se mantiene? Esto muestra si el índice mide algo real
  o solo ruido.
- Al priorizar, ¿conviene ponderar distinto una propiedad subvaluada bien ubicada
  frente a una subvaluada en zona periférica, dado que la primera tiene mayor
  liquidez y potencial de revalorización?

### Prescriptivo: ¿qué deberíamos hacer?

- Definir un umbral de gap de confort más eficiencia de expensas para decidir si una
  propiedad pasa directo al comité de inversión o requiere evaluación manual.
- ¿En qué zona conviene que el fondo concentre análisis e inversiones, según dónde
  el gap promedio sea mayor o más consistente?
- Recomendar cada cuánto conviene re-testear las ponderaciones del índice contra
  los datos y ajustarlas.

---

## 4. KPIs

| KPI | ¿Qué mide? | ¿Cómo se calcula? |
|---|---|---|
| **Índice de Confort (1-10)** | Nivel de equipamiento y posicionamiento de una propiedad | Suma ponderada de 3 bloques normalizada a 1-10: infraestructura básica 45% + amenities del edificio 30% + atributos de la propiedad 25%. La ubicación no participa |
| **Tasa de completitud** | Qué tan confiable es el índice en una propiedad específica | % de columnas de amenities con dato real (no nulo) sobre el total consideradas |
| **Peso empírico por bloque** | Si los pesos definidos a mano se sostienen con evidencia | Coeficiente de cada bloque en una regresión de precio por m² por zona |
| **Precio por m² por zona** | El precio normal de esa zona, usado como vara de comparación | Mediana de precio por m² en propiedades comparables (misma zona, tamaño similar) |
| **Gap de confort** | Cuánto confort de más o de menos ofrece una propiedad respecto a lo que su precio sugeriría en su zona | Residuos de precio por m² en función del índice de confort, calculado por zona |
| **Confort por segmento de precio** | Si el confort se paga más fuerte en propiedades caras que en las de precio medio | Pendiente de precio por m² vs. índice de confort, calculada por separado por encima y por debajo de la mediana de la zona |
| **Eficiencia de expensas** | Si el confort de la propiedad se paga barato o caro por mes | Índice de confort / expensas, o expensas por m² |
| **Ranking de oportunidades** | Las mejores oportunidades para elevar al comité de inversión | Top *n* por zona, ordenadas por gap de confort positivo, ponderadas por segmento de precio y filtradas por buena tasa de completitud |
| **Índice de accesibilidad** | Qué tan bien ubicada está una propiedad respecto a transporte y centralidad | Combinación normalizada de distancia a la estación más cercana y distancia a la centralidad |
| **Gap de confort ajustado por ubicación** | El gap una vez descontado el efecto de la ubicación | Residuo del precio por m² en función del índice de confort **y** las variables de entorno, por zona |

---

## 5. Alcance

- **Geográfico:** los 47 barrios de CABA. Unidad de comparación: sub-zona dentro de
  cada barrio, con el barrio como respaldo.
- **Tipología:** únicamente departamentos usados en venta. Quedan fuera casas, PH,
  alquileres y emprendimientos en pozo.
- **Precio:** se opera sobre el **precio de publicación**, no sobre el precio de
  venta efectivo (dato no público). Lo que se detecta son publicaciones cuyo precio
  resulta bajo en relación con las características y el confort que ofrecen, no
  necesariamente propiedades que vayan a venderse por debajo de su valor.
- **Temporal:** una foto del mercado en un momento puntual, no una serie temporal.

### Línea de trabajo para próximas entregas

Reemplazar o complementar la variable estática de distancia a la centralidad por
una medida del **dinamismo** de cada zona (su tendencia de crecimiento en el
tiempo). Para un fondo de inversión es más valioso identificar hacia dónde se
desplaza el valor que constatar dónde se concentra hoy. Se evaluarán tres fuentes
posibles:

1. Comparación del precio por m² de cada zona entre dos relevamientos sucesivos de
   scraping.
2. Permisos de obra nueva georreferenciados de BA Data, como proxy de zonas en
   desarrollo activo.
3. Proporción de propiedades de construcción reciente por zona, calculable a partir
   de la antigüedad ya presente en el dataset.

---

## 6. Usuario final

El usuario principal es el **analista de inversiones del fondo**. Revisa a diario el
flujo de propiedades publicadas y arma el pipeline de oportunidades que eleva al
comité. Su problema concreto es de volumen: hay decenas de miles de publicaciones
activas en CABA y es inviable analizarlas manualmente. La herramienta le permite
quedarse con el subconjunto de propiedades con gap de confort positivo respecto a
su zona, ordenadas por atractivo, para concentrar el análisis profundo solo donde
tiene sentido.

El usuario secundario es el **comité de inversión**, que recibe las oportunidades ya
filtradas y priorizadas para la decisión final de compra, y que se apoya en el
análisis por zonas para definir dónde concentrar el capital.

---

## 7. Descripción del dataset

Construido íntegramente mediante **web scraping de MercadoLibre Inmuebles**, la
mayor plataforma de avisos inmobiliarios de Argentina. Se relevaron departamentos
usados en venta en los 47 barrios de CABA.

| Métrica | Valor |
|---|---|
| Propiedades únicas | **27.922** |
| Variables (dataset final) | **93** |
| Propiedades geocodificadas | 22.912 (82,1%) |
| Sub-zonas definidas | 198 |
| Mediana de precio (avisos en USD) | USD 135.000 |
| Mediana de superficie | 57 m² |

La extracción recorrió cada barrio de forma independiente, lo que permitió alcanzar
un volumen alto y garantizar representación de toda la ciudad: desde barrios de
gran oferta como Palermo, Belgrano, Caballito y Recoleta (2.016 propiedades cada
uno, el tope de paginación de la plataforma) hasta barrios más chicos del sur y el
oeste con unas pocas decenas de avisos (Villa Riachuelo, 15).

### Tipos de variables

- **Numéricas continuas:** precio en dólares, superficie en m², expensas.
- **Numéricas discretas:** ambientes, dormitorios, baños, cocheras, antigüedad.
- **Categóricas:** barrio, orientación, disposición, tipo de departamento.
- **Dicotómicas:** más de 40 columnas de amenities y características Sí/No (pileta,
  gimnasio, ascensor, parrilla, seguridad, balcón, etc.).
- **Textuales:** título y dirección del aviso.
- **Geográficas:** latitud, longitud, sub-zona, distancias a subte y centralidad.

### Fuentes externas de enriquecimiento

- **Normalizador de direcciones de USIG**, Gobierno de la Ciudad de Buenos Aires.
- **Dataset de estaciones de subte de BA Data**, portal de datos abiertos del GCBA.

---

## 8. Pipeline de datos

```
data/raw/cuotas/cuota1..5.tsv                          etapa 1: scraping
          ↓
data/interim/mercadolibre_CABA_completo.tsv            etapa 2: consolidación
          ↓
data/interim/propiedades_geocodificadas.tsv            etapa 3: geocodificación
          ↓
data/processed/propiedades_enriquecidas.tsv            etapa 4: enriquecimiento
```

### Tabla de etapas

Los números de la columna de control son los de la **corrida documentada** descripta
en la [sección 16](#16-corrida-documentada-de-punta-a-punta).

| # | Qué entra | Qué transformación se aplica | Qué control se ejecuta | Qué archivo sale |
|---|---|---|---|---|
| **1. Scraping** | Listados y fichas de MercadoLibre Inmuebles, 47 barrios de CABA repartidos en 5 cuotas, hasta 42 páginas de 48 avisos por barrio | Parseo de cada card (tipo, título, precio con moneda y flag `es_emprendimiento`, ambientes, dormitorios, baños, m², ubicación, link) más la tabla de características de la ficha de detalle, normalizada a columnas de amenities. Deduplicación por link dentro de la corrida | Filas de salida por cuota: 13.000 / 7.514 / 4.050 / 1.913 / 1.445 = **27.922**. Columnas: 86 / 85 / 86 / 86 / 85. Duplicados de link dentro de cada cuota: **0**. Barrios cubiertos: 8 / 10 / 10 / 10 / 9 = **47 de 47** | `data/raw/cuotas/cuota1..5.tsv` |
| **2. Consolidación** | Las 5 cuotas, **27.922** filas concatenadas, 86 columnas tras unir el esquema | Concatenación, unión de columnas y deduplicación por `link` conservando la primera aparición | Entran **27.922**, salen **27.922**, duplicados detectados **0**, duplicados eliminados **0**, duplicados residuales **0**. Nulos en columnas clave: `link` 0, `precio` 0, `ubicacion` 0, `barrio` 0, `m2` **26** | `data/interim/mercadolibre_CABA_completo.tsv` (27.922 × 86) |
| **3. Geocodificación** | Consolidado, **27.922** × 86 | Limpieza de la dirección (corte en la primera coma, "Av." a "Avenida", descarte del texto tras un punto, normalización de la abreviatura "Al") y consulta al normalizador de USIG con 3 reintentos. Agrega `dir_limpia`, `lat`, `lon`, `geo_status` | Entran **27.922**, salen **27.922**. Direcciones geocodificables **26.338** (94,3%), no geocodificables **1.584**. Tasa de éxito **82,06%**: `OK` 22.912, `SIN_RESULTADO` 3.406, `NO_GEOCODIFICABLE` 1.584, `SIN_COORDENADAS` 20. Coordenadas presentes **22.912**. Duplicados residuales **0**. Nulos clave sin cambios (`m2` 26) | `data/interim/propiedades_geocodificadas.tsv` (27.922 × 90) |
| **4. Enriquecimiento** | Geocodificado, **27.922** × 90, de las cuales **22.912** con coordenadas | GeoJSON de estaciones de subte de BA Data (cacheado en `data/external/`). Haversine a la estación más cercana y al polo de centralidad más cercano (Obelisco, Puerto Madero, Catalinas). KMeans por barrio sobre lat/lon, k = min(5, n/30), `random_state=42`, `n_init=10` | Entran **27.922**, salen **27.922**. Con `dist_transporte_m` **22.912**, con `dist_centralidad_m` **22.912**. Media a transporte **925 m**, media a centralidad **5.696 m**. Sub-zonas creadas **198**. Duplicados residuales **0**. Nulos clave sin cambios (`m2` 26) | `data/processed/propiedades_enriquecidas.tsv` (27.922 × 93) |

El detalle de los desafíos técnicos (bloqueo por CloudFront, IP de datacenter vs.
residencial, contenido corrupto por compresión Brotli, distinción entre
emprendimientos y propiedades usadas, límite de paginación y normalización de
direcciones) está en [`docs/proceso_tecnico.md`](docs/proceso_tecnico.md).

---

## 9. Estructura del repositorio

```
tp1-fondo-inmobiliario/
├── README.md
├── requirements.txt                            Dependencias con versiones fijadas
├── run_pipeline.py                             Runner único de la cadena completa
├── config/
│   └── config.yaml                             Rutas, cuotas, delays y parámetros
├── src/
│   ├── rutas.py                                Resolución de rutas desde la raíz del repo
│   ├── configuracion.py                        Carga del YAML y helpers de argparse
│   ├── qc.py                                   Controles de calidad y logging
│   ├── scrapper_mercadolibre.py                Etapa 1
│   ├── unir_cuotas.py                          Etapa 2
│   ├── geocoding_propiedades.py                Etapa 3
│   └── enriquecimiento.py                      Etapa 4
├── data/
│   ├── raw/cuotas/                             Salida cruda del scraper, una por cuota
│   ├── interim/                                Consolidado y geocodificado
│   ├── processed/                              Dataset final
│   └── external/                               Cache del GeoJSON de subte
├── outputs/
│   └── logs/                                   pipeline.log y qc_<etapa>.json
├── tests/
│   ├── verificar_offline.py                    Smoke test reproducible sin red
│   └── fixtures/ficha_detalle.html             HTML guardado para probar el parseo
└── docs/
    ├── caso_de_negocio.pdf                     Documento de negocio (entrega)
    └── proceso_tecnico.md                      Documentación del proceso técnico
```

---

## 10. Qué viene versionado y qué se regenera

Los datasets se versionan a propósito. Sin ellos habría que rehacer entre 8 y 15
horas de scraping para poder correr cualquier etapa, y el pipeline dejaría de ser
reproducible por un tercero.

| Archivo | ¿Versionado? | Tamaño | Cómo se regenera |
|---|---|---|---|
| `data/raw/cuotas/cuota1..5.tsv` | Sí | 19,4 MB | Etapa 1, `--incluir-scraping`. Entre 8 y 15 h, IP residencial |
| `data/interim/mercadolibre_CABA_completo.tsv` | Sí | 19,7 MB | Etapa 2, segundos |
| `data/interim/propiedades_geocodificadas.tsv` | Sí | 20,9 MB | Etapa 3, unas 2 h contra USIG |
| `data/processed/propiedades_enriquecidas.tsv` | Sí | 21,5 MB | Etapa 4, menos de 1 min más la descarga del GeoJSON |
| `data/external/estaciones-de-subte.geojson` | No | — | Se baja solo en la primera corrida de la etapa 4 y queda cacheado |
| `outputs/logs/pipeline.log`, `outputs/logs/qc_*.json` | No | — | Los escribe cada corrida |
| `*_parcial.tsv` | No | — | Los escribe y borra el propio pipeline |

Total versionado: unos 81 MB.

---

## 11. Instalación

Requiere **Python 3.9 o superior**. La corrida documentada se hizo con
**Python 3.9**, que es la versión de referencia: es la que garantiza reproducir
los datasets byte a byte.

```bash
git clone https://github.com/gbuhler-itba/TP-Analitica-Descriptiva.git
cd TP-Analitica-Descriptiva
python3 -m venv .venv && source .venv/bin/activate    # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Nota sobre el intérprete.** En macOS y en la mayoría de las distribuciones
> de Linux el comando es **`python3`** (`python` a secas puede no existir). En
> Windows suele ser `python`. Todos los ejemplos de este README usan `python3`.
> Dentro de un entorno virtual ya activado, `python` y `python3` apuntan al
> mismo intérprete.

`run_pipeline.py` chequea la versión al arrancar: corta con un mensaje claro si
el intérprete es anterior a 3.9, y avisa (sin cortar) si no es 3.9, para que
quede explícito cuándo la reproducción byte a byte no está garantizada. El
mismo chequeo mínimo corre al invocar cualquier etapa por separado.

Todas las versiones de `requirements.txt` están verificadas contra PyPI y
todas tienen wheels para CPython 3.9.

No hace falta editar ningún archivo. Todas las rutas se resuelven a partir de la
ubicación del repositorio, así que los scripts se pueden invocar desde cualquier
directorio de trabajo.

---

## 12. Cómo correr el pipeline

### Runner único

```bash
python3 run_pipeline.py                      # etapas 2, 3 y 4 (default)
python3 run_pipeline.py --desde-etapa 3      # etapas 3 y 4
python3 run_pipeline.py --hasta-etapa 2      # solo la etapa 2
python3 run_pipeline.py --incluir-scraping   # etapas 1, 2, 3 y 4
```

Por defecto **el pipeline arranca en la etapa 2**, asumiendo que las cuotas ya
están descargadas en `data/raw/cuotas/` (vienen versionadas).

> ⚠️ **El scraping completo son entre 8 y 15 horas.** La etapa 1 solo corre con
> `--incluir-scraping` explícito, nunca por accidente. Además debe ejecutarse desde
> una **IP residencial**: desde Google Colab u otro entorno con IP de datacenter se
> dispara el bloqueo anti-bot de la plataforma (ver
> [`docs/proceso_tecnico.md`](docs/proceso_tecnico.md), sección 2.2). Por eso las
> cuotas ya descargadas están versionadas en el repositorio.

### Etapas por separado

```bash
python3 src/scrapper_mercadolibre.py --cuota cuota3
python3 src/unir_cuotas.py
python3 src/geocoding_propiedades.py
python3 src/enriquecimiento.py
```

Cada script tiene su propio `--help` con todos los parámetros disponibles.

### Ejemplos de parametrización

```bash
# Scrapear solo dos barrios, sin entrar a las fichas, 3 páginas por barrio
python3 src/scrapper_mercadolibre.py --barrios palermo belgrano --sin-detalle --max-paginas 3

# Scrapear una cuota con delays más conservadores
python3 src/scrapper_mercadolibre.py --cuota cuota1 --delay-pagina 3 6 --delay-detalle 2 4

# Geocodificar solo las primeras 500 direcciones pendientes, para probar
python3 src/geocoding_propiedades.py --limite 500

# Enriquecer rebajando el GeoJSON de subte aunque exista el cache
python3 src/enriquecimiento.py --forzar-descarga

# Correr todo con otra configuración y otras rutas de datos
python3 run_pipeline.py --config config/mi_config.yaml
```

### Retomar una corrida cortada

Las etapas 1 y 3 escriben archivos parciales. Si una corrida se corta, basta con
volver a lanzar la misma etapa: la etapa 3 detecta el parcial y reprocesa
únicamente las filas que quedaron sin `geo_status`. Con `--sin-resume` se ignora el
parcial y se arranca de cero.

---

## 13. Configuración

Todo lo parametrizable vive en [`config/config.yaml`](config/config.yaml):

- **`rutas`**: dónde entra y dónde sale cada etapa, más el cache externo y los logs.
- **`scraping`**: tope de páginas por barrio, avisos por página, si se entra o no a
  las fichas, timeouts, cada cuántos avisos se guarda el parcial, los tres rangos de
  delay aleatorio y **la composición de las 5 cuotas de barrios**.
- **`consolidacion`**: patrón glob de cuotas y clave de deduplicación.
- **`geocoding`**: endpoint de USIG, reintentos, timeout, frecuencia de guardado y
  de reporte, y los delays entre llamadas.
- **`enriquecimiento`**: URL del GeoJSON, coordenadas de los polos de centralidad,
  tope de sub-zonas por barrio, mínimo de propiedades por sub-zona y los parámetros
  de KMeans.
- **`qc`**: qué columnas se consideran clave para el conteo de nulos.

Cualquier valor del YAML puede pisarse por línea de comandos sin tocar el archivo.

---

## 14. Controles de calidad

Cada etapa cierra con un bloque de control que se **imprime por pantalla** y se
**escribe a disco** en dos formatos:

- `outputs/logs/pipeline.log`, texto acumulativo con timestamp por corrida.
- `outputs/logs/qc_<etapa>.json`, las mismas métricas en formato consumible.

Qué reporta cada bloque:

| Control | Etapas | Qué mide |
|---|---|---|
| `filas_entrada` / `filas_salida` | 1, 2, 3, 4 | Cuántas filas entran y cuántas salen de la etapa |
| `columnas_salida` | 1, 2, 3, 4 | Ancho del dataset resultante |
| `duplicados_detectados` / `duplicados_eliminados` / `duplicados_residuales` | 2 | Deduplicación por `link`, antes y después |
| `nulos_columnas_clave` | 1, 2, 3, 4 | Nulos en `link`, `precio`, `m2`, `ubicacion`, `barrio` |
| `geocoding_por_estado` / `geocoding_tasa_exito_pct` | 3, 4 | Desglose por `geo_status` y porcentaje de `OK` |
| `direcciones_geocodificables` | 3 | Cuántas direcciones pasaron la limpieza previa |
| `estaciones_subte` / `origen_geojson_subte` | 4 | Cuántas estaciones se usaron y si salieron del cache o de la descarga |
| `subzonas_totales` | 4 | Cuántas sub-zonas produjo el clustering |
| `propiedades_por_barrio` | 1, 2 | Distribución por barrio, para detectar barrios vacíos |

Además, cada etapa devuelve código de salida distinto de cero si la cantidad de
filas cambia entre entrada y salida cuando no debería, y el runner corta la cadena
en ese caso.

---

## 15. Verificación

Hay dos cosas distintas y conviene no confundirlas.

### 15.1. Smoke test reproducible, sin red

```bash
python3 tests/verificar_offline.py
```

Verifica que el código reproduce exactamente los datasets versionados **sin pegarle
a ningún servicio externo**. Tarda un par de minutos. Qué hace:

| Etapa | Cómo se verifica | Alcance |
|---|---|---|
| 1 | Las funciones reales de parseo corren contra HTML guardado en `tests/fixtures/` | Verifica el parseo, **no** el crawling |
| 2 | Se corre `unir_cuotas` sobre las cuotas versionadas y se compara el resultado por **SHA256** | Reproducción byte a byte |
| 3 | Se corre `geocoding_propiedades` con las respuestas de USIG **replayeadas** desde el dataset versionado, y se compara por **SHA256**. La limpieza de direcciones se recalcula de verdad sobre las 27.922 filas | Reproducción byte a byte. No se vuelve a llamar al servicio |
| 4 | Se corre `enriquecimiento` con un GeoJSON **sintético** y se comparan las 92 columnas que no dependen de él | `dist_transporte_m` **no** queda verificada offline |
| cadena | Se comprueba que la salida de cada etapa es la entrada de la siguiente y que no queda ninguna ruta absoluta en el código | Es justamente lo que estaba roto antes |

Resultado de la última corrida: **24 de 24 controles OK**, sobre
**Python 3.9.23** y con el entorno exacto de `requirements.txt` instalado
desde cero: `requests 2.32.5`, `beautifulsoup4 4.15.0`, `pandas 2.3.3`,
`numpy 2.0.2`, `scikit-learn 1.6.1`, `PyYAML 6.0.3`.

> **Sobre scikit-learn.** `requirements.txt` fija **1.6.1**, la versión del
> entorno donde se produjo la corrida original documentada, y con esa versión
> se corrió la verificación de arriba. El smoke test se corrió además con
> **scikit-learn 1.7.2** sobre Python 3.10, y también reprodujo exactamente las
> mismas **198 sub-zonas**: el resultado del clustering se mantuvo entre
> versiones. Se fija igual 1.6.1, porque es la que garantiza reproducir la
> corrida original y porque los labels de KMeans pueden cambiar entre versiones
> aunque `random_state` esté fijado.

Las etapas 2 y 3 dan hash idéntico al dataset versionado. La etapa 4 reproduce
exactamente `dist_centralidad_m`, las **198 sub-zonas** y las otras 92 columnas.

### 15.2. Corrida completa real

El smoke test no reemplaza una corrida real: las etapas 1, 3 y 4 dependen de
MercadoLibre, USIG y BA Data respectivamente. La corrida completa contra los
servicios reales está documentada en la sección siguiente.

---

## 16. Corrida documentada de punta a punta

Corrida original completa, sobre la que están construidos los datasets versionados.

**Comando equivalente en la estructura actual:**

```bash
python3 run_pipeline.py --incluir-scraping
```

**Etapa 1, scraping.** Cinco cuotas corridas en sesiones separadas, con
`con_detalle=true` y `max_paginas_por_barrio=42`.

| Cuota | Barrios | Filas | Columnas |
|---|---|---|---|
| cuota1 | 8 | 13.000 | 86 |
| cuota2 | 10 | 7.514 | 85 |
| cuota3 | 10 | 4.050 | 86 |
| cuota4 | 10 | 1.913 | 86 |
| cuota5 | 9 | 1.445 | 85 |
| **Total** | **47** | **27.922** | **86 tras unir esquemas** |

Duplicados de `link` dentro de cada cuota: 0. Cuatro barrios llegaron al tope de
paginación con 2.016 avisos cada uno (Palermo, Belgrano, Caballito, Recoleta); el
más chico fue Villa Riachuelo con 15.

**Etapa 2, consolidación.** Entran 27.922, salen 27.922. Duplicados detectados 0,
eliminados 0, residuales 0. Nulos en columnas clave: solo `m2` con 26.

**Etapa 3, geocodificación.** Entran 27.922, salen 27.922, 90 columnas.

| `geo_status` | Filas | % |
|---|---|---|
| `OK` | 22.912 | 82,06% |
| `SIN_RESULTADO` | 3.406 | 12,20% |
| `NO_GEOCODIFICABLE` | 1.584 | 5,67% |
| `SIN_COORDENADAS` | 20 | 0,07% |

Direcciones que pasaron la limpieza previa: 26.338 (94,3%).

**Etapa 4, enriquecimiento.** Entran 27.922, salen 27.922, 93 columnas. Con
distancias calculadas: 22.912. Media a la estación de subte más cercana: **925 m**.
Media al polo de centralidad más cercano: **5.696 m**. Sub-zonas creadas: **198**.

**Qué de esto se reverificó y qué no.** Las etapas 2 y 3 se reprodujeron byte a
byte con el smoke test offline (SHA256 idéntico). De la etapa 4 se reprodujeron
exactamente `dist_centralidad_m`, `subzona` y las otras 92 columnas; la media de
`dist_transporte_m` proviene del dataset versionado y no se recalculó offline
porque depende del GeoJSON de BA Data. La etapa 1 no se reejecutó: solo se
verificó su parseo contra HTML guardado.

---

## 17. Arreglos respecto de la versión anterior

Esta versión no cambia la lógica analítica ni los resultados. Los tres datasets son
bit a bit los mismos. Lo que cambió es estructura, parametrización y documentación.

| Qué estaba mal | Qué se hizo |
|---|---|
| `geocoding_propiedades.py` y `enriquecimiento.py` tenían rutas absolutas de una máquina concreta | Todas las rutas se resuelven desde la raíz del repo con `pathlib`. Un control del smoke test falla si reaparece una ruta absoluta |
| La cadena estaba **cortada**: la etapa 2 escribía en `output/` y la etapa 3 leía de otra ruta. El pipeline no corría de punta a punta | Las rutas salen de `config/config.yaml`, la salida de cada etapa es la entrada de la siguiente, y hay un control que lo verifica |
| `output/` era relativo al directorio de trabajo, así que la salida cambiaba de lugar según desde dónde se invocara el script | Las rutas se anclan a la raíz del repo, no al `cwd` |
| Para elegir qué cuota scrapear había que descomentar bloques de código al final del archivo | `--cuota` / `--barrios` y la composición de las cuotas en el YAML |
| Cuotas, barrios, límite de paginación y delays estaban hardcodeados | Todo en `config/config.yaml`, pisable por argparse |
| No había un punto de entrada único | `run_pipeline.py` con `--desde-etapa`, `--hasta-etapa` e `--incluir-scraping` |
| No había controles de calidad ni logs | Bloque de QC al cierre de cada etapa, impreso y escrito a `outputs/logs/` |
| No había `requirements.txt` | Agregado, con versiones fijadas |
| Las cuotas del scraper no estaban versionadas, así que la etapa 2 no se podía correr al clonar | `data/raw/cuotas/cuota1..5.tsv` versionadas |
| **Bug:** el scraper escribía el parcial como `cuota_actual_parcial.tsv` pero intentaba borrar `<cuota>_parcial.tsv`, así que nunca lo limpiaba | Se escribe y se borra con el mismo nombre |
| **Bug:** el resume del geocoding asumía que lo ya procesado era un prefijo contiguo del DataFrame, y se corrompía si el parcial tenía huecos | Resume por máscara booleana sobre `geo_status`: se reprocesa toda fila sin estado, esté donde esté |

Ninguno de los dos arreglos de bug cambia los datasets: el primero solo limpia un
archivo temporal y el segundo solo afecta el camino de retome de una corrida
cortada, que en la corrida documentada no se activó.

---

## 18. Limitaciones conocidas

- **Precio de publicación, no de venta.** El dataset contiene el precio al que se
  publica cada aviso, no el precio de venta efectivo. El análisis detecta
  publicaciones cuyo precio es bajo respecto a sus características, lo que es una
  aproximación a la "subvaluación" pero no equivale a ella.
- **Foto de un momento puntual.** Un único relevamiento, no una serie temporal.
- **Cobertura del geocoding.** El 17,9% de las propiedades no pudo geocodificarse
  por direcciones incompletas o no normalizables. Se conservan en el dataset y
  participan del análisis a nivel barrio, pero quedan fuera del análisis espacial
  fino (distancias y sub-zonas).
- **Truncamiento por límite de paginación.** Los barrios de mayor oferta (Palermo,
  Belgrano, Caballito, Recoleta) quedaron limitados a 2.016 registros por el tope
  de la plataforma, lo que podría introducir sesgo hacia las publicaciones más
  recientes o mejor posicionadas.
- **Interpretación de amenities faltantes.** Una celda vacía no siempre permite
  distinguir entre ausencia real del amenity y dato no cargado por el anunciante.
  Esta distinción se aborda en la etapa de limpieza.
- **Datos de entorno acotados a subte.** La accesibilidad al transporte considera
  solo la red de subte. La incorporación de tren y Metrobus queda planteada para
  etapas posteriores.
- **La columna `es_emprendimiento` es siempre `False`.** La URL de scraping filtra
  por `propiedades-individuales`, que ya excluye los emprendimientos en pozo. La
  columna se conserva porque el parseo del precio "Desde" sigue siendo válido si en
  el futuro se amplía el alcance del scraping.
- **Reproducibilidad del clustering.** Las sub-zonas salen de KMeans, cuyos labels
  pueden variar entre versiones de scikit-learn aunque `random_state` esté fijado.
  Por eso `requirements.txt` fija `scikit-learn==1.6.1`, la versión del entorno
  donde se produjo la corrida documentada. En la práctica el resultado se mostró
  estable: la verificación offline se corrió con `1.6.1` sobre Python 3.9 y con
  `1.7.2` sobre Python 3.10, y las dos reprodujeron las mismas 198 sub-zonas. De todos modos, el dataset final
  versionado congela las sub-zonas de la corrida original.
