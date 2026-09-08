# TP 1 — Fondo de Inversión Inmobiliario (CABA)

**Analítica Descriptiva — ITBA, 2026 C2**

Detección sistemática de departamentos usados en venta en la Ciudad Autónoma de
Buenos Aires cuyo nivel de confort está por encima de lo que su precio por metro
cuadrado sugeriría dentro de su zona, con el fin de identificar oportunidades de
inversión potencialmente subvaluadas.

---

## 1. Contexto y situación de negocio

La unidad de negocio es un **fondo de inversión inmobiliario** que opera en los 47
barrios de CABA.

La hipótesis de partida es simple: dos departamentos ubicados en el mismo barrio y
en la misma zona —porque no es lo mismo Palermo Chico que Palermo Soho— y
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

### Descriptivo — ¿Qué pasó / qué está pasando?

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

### Diagnóstico — ¿Por qué pasó / por qué sucede?

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

### Predictivo — ¿Qué pasará?

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

### Prescriptivo — ¿Qué deberíamos hacer?

- Definir un umbral de gap de confort + eficiencia de expensas para decidir si una
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
| Propiedades geocodificadas | 22.912 (82%) |
| Sub-zonas definidas | 198 |
| Mediana de precio | USD 130.000 |
| Mediana de superficie | 57 m² |

La extracción recorrió cada barrio de forma independiente, lo que permitió alcanzar
un volumen alto y garantizar representación de toda la ciudad: desde barrios de
gran oferta como Palermo, Belgrano, Caballito y Recoleta (~2.000 propiedades cada
uno) hasta barrios más chicos del sur y el oeste con unas pocas decenas de avisos.

### Tipos de variables

- **Numéricas continuas:** precio en dólares, superficie en m², expensas.
- **Numéricas discretas:** ambientes, dormitorios, baños, cocheras, antigüedad.
- **Categóricas:** barrio, orientación, disposición, tipo de departamento.
- **Dicotómicas:** más de 40 columnas de amenities y características Sí/No (pileta,
  gimnasio, ascensor, parrilla, seguridad, balcón, …).
- **Textuales:** título y dirección del aviso.
- **Geográficas:** latitud, longitud, sub-zona, distancias a subte y centralidad.

### Fuentes externas de enriquecimiento

- **Normalizador de direcciones de USIG** — Gobierno de la Ciudad de Buenos Aires.
- **Dataset de estaciones de subte de BA Data** — portal de datos abiertos del GCBA.

---

## 8. Pipeline de datos

```
scrapper_mercadolibre.py  →  output/cuota1..5.tsv
          ↓
unir_cuotas.py            →  data/raw/mercadolibre_CABA_completo.tsv   (27.922 × 86)
          ↓
geocoding_propiedades.py  →  data/raw/propiedades_geocodificadas.tsv   (27.922 × 90)
          ↓
enriquecimiento.py        →  data/raw/propiedades_enriquecidas.tsv     (27.922 × 93)
```

1. **Extracción (scraping).** Relevamiento de MercadoLibre por barrio y por cuotas,
   capturando datos del listado y de la ficha de detalle de cada propiedad.
   Resultado: 27.922 propiedades con 86 variables.
2. **Consolidación.** Unificación de los archivos de las cinco cuotas en un único
   dataset, con eliminación de duplicados por link.
3. **Geocodificación.** Conversión de direcciones en coordenadas mediante el
   normalizador de USIG. Resultado: 22.912 propiedades con latitud y longitud (82%).
4. **Enriquecimiento.** Distancia a la estación de subte más cercana y a los polos
   de centralidad (BA Data), y asignación de cada propiedad a una sub-zona mediante
   clustering espacial. Resultado: dataset final de 93 variables.

El detalle completo de los desafíos técnicos —bloqueo por CloudFront, IP de
datacenter vs. residencial, contenido corrupto por compresión Brotli, distinción
entre emprendimientos y propiedades usadas, límite de paginación y normalización de
direcciones— está documentado en [`docs/proceso_tecnico.md`](docs/proceso_tecnico.md).

---

## 9. Estructura del repositorio

```
tp1-fondo-inmobiliario/
├── README.md
├── data/
│   └── raw/
│       ├── mercadolibre_CABA_completo.tsv      18,8 MB — dataset consolidado
│       ├── propiedades_geocodificadas.tsv      19,9 MB — + lat/lon (USIG)
│       └── propiedades_enriquecidas.tsv        20,5 MB — + entorno y sub-zonas
├── scripts/
│   ├── scrapper_mercadolibre.py                Scraping por barrio y por cuotas
│   ├── unir_cuotas.py                          Consolidación y deduplicación
│   ├── geocoding_propiedades.py                Geocodificación vía USIG
│   └── enriquecimiento.py                      Distancias, centralidad, sub-zonas
└── docs/
    ├── caso_de_negocio.pdf                     Documento de negocio (entrega)
    └── proceso_tecnico.md                      Documentación del proceso técnico
```

---

## 10. Cómo reproducir

### Dependencias

```bash
pip install requests beautifulsoup4 pandas numpy scikit-learn
```

### Ejecución

```bash
python scripts/scrapper_mercadolibre.py   # editar la cuota a correr al final del archivo
python scripts/unir_cuotas.py
python scripts/geocoding_propiedades.py
python scripts/enriquecimiento.py
```

> **Nota sobre rutas:** `geocoding_propiedades.py` y `enriquecimiento.py` tienen las
> rutas de entrada **hardcodeadas como rutas absolutas** de la máquina donde se
> corrieron, y todos los scripts escriben en un directorio `output/` relativo al
> directorio de trabajo. Para reproducir el pipeline hay que ajustar las constantes
> `ARCHIVO_ENTRADA` / `ARCHIVO_SALIDA` de cada script para que apunten a
> `data/raw/`.

> **Nota sobre el scraping:** el scraping **debe ejecutarse localmente**, desde una
> IP residencial. Ejecutarlo desde Google Colab u otro entorno con IP de datacenter
> dispara el bloqueo anti-bot de las plataformas (ver
> [`docs/proceso_tecnico.md`](docs/proceso_tecnico.md), sección 2.2).

---

## 11. Limitaciones conocidas

- **Precio de publicación, no de venta.** El dataset contiene el precio al que se
  publica cada aviso, no el precio de venta efectivo. El análisis detecta
  publicaciones cuyo precio es bajo respecto a sus características, lo que es una
  aproximación a la "subvaluación" pero no equivale a ella.
- **Foto de un momento puntual.** Un único relevamiento, no una serie temporal.
- **Cobertura del geocoding.** El 18% de las propiedades no pudo geocodificarse por
  direcciones incompletas o no normalizables. Se conservan en el dataset y
  participan del análisis a nivel barrio, pero quedan fuera del análisis espacial
  fino (distancias y sub-zonas).
- **Truncamiento por límite de paginación.** Los barrios de mayor oferta (Palermo,
  Belgrano, Caballito, Recoleta) quedaron limitados a ~2.000 registros por el tope
  de la plataforma, lo que podría introducir sesgo hacia las publicaciones más
  recientes o mejor posicionadas.
- **Interpretación de amenities faltantes.** Una celda vacía no siempre permite
  distinguir entre ausencia real del amenity y dato no cargado por el anunciante.
  Esta distinción se aborda en la etapa de limpieza.
- **Datos de entorno acotados a subte.** La accesibilidad al transporte considera
  solo la red de subte. La incorporación de tren y Metrobus queda planteada para
  etapas posteriores.
