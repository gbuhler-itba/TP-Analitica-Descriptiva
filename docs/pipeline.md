# Pipeline de datos: instalación, ejecución y verificación

Documentación técnica de la cadena completa: del scraping al dataset enriquecido (etapas 1 a 4), la limpieza (etapa 5) y el análisis que produce la lista oficial de avisos a investigar (etapa 6), más los scripts auxiliares de la PreEntrega 3 (fuentes externas, permisos de obra, segundo relevamiento y capa de datos del dashboard). Hasta la PreEntrega 1 estaba en el README; se movió acá para que el README se concentre en el análisis. Qué explica cada notebook está en el README, sección 9.

---

## 1. Pipeline de datos

```
data/raw/cuotas/cuota1..5.tsv                          etapa 1: scraping
          ↓
data/interim/mercadolibre_CABA_completo.tsv            etapa 2: consolidación
          ↓
data/interim/propiedades_geocodificadas.tsv            etapa 3: geocodificación
          ↓
data/processed/propiedades_enriquecidas.tsv            etapa 4: enriquecimiento
          ↓                        ← data/processed/accesibilidad.tsv (src/fuentes_externas.py)
data/processed/propiedades_limpias.tsv                 etapa 5: limpieza
          ↓                        ← accesibilidad.tsv, permisos_obra.tsv (src/permisos_obra.py),
          ↓                          seguimiento_avisos.csv (src/seguimiento.py), config/costos.yaml
data/processed/precio_esperado.tsv                     etapa 6: análisis (precio esperado, brecha,
data/processed/avisos_a_investigar.csv                 marcas, regla de decisión, ranking, embudo)
          ↓
docs/dashboard/data/*.json                             src/exportar_dashboard.py
```

Las etapas 1 a 4 construyen el dataset y son las de la PreEntrega 1. Las etapas 5 y 6 se sumaron en las
PreEntregas 2 y 3: reproducen en `src/` la lógica que los notebooks explican, para que la lista oficial salga de
un script y no de una celda. Los scripts auxiliares de la derecha no forman parte del runner (leen snapshots
versionados y sus salidas también vienen versionadas); se corren a mano cuando cambia una fuente o un dataset.

### Tabla de etapas

Los números de la columna de control son los de la **corrida documentada** descripta
en la [sección 8](#8-corrida-documentada-de-punta-a-punta).

| # | Qué entra | Qué transformación se aplica | Qué control se ejecuta | Qué archivo sale |
|---|---|---|---|---|
| **1. Scraping** | Listados y fichas de MercadoLibre Inmuebles, 47 barrios de CABA repartidos en 5 cuotas, hasta 42 páginas de 48 avisos por barrio | Parseo de cada card (tipo, título, precio con moneda y flag `es_emprendimiento`, ambientes, dormitorios, baños, m², ubicación, link) más la tabla de características de la ficha de detalle, normalizada a columnas de amenities. Deduplicación por link dentro de la corrida | Filas de salida por cuota: 13.000 / 7.514 / 4.050 / 1.913 / 1.445 = **27.922**. Columnas: 86 / 85 / 86 / 86 / 85. Duplicados de link dentro de cada cuota: **0**. Barrios cubiertos: 8 / 10 / 10 / 10 / 9 = **47 de 47** | `data/raw/cuotas/cuota1..5.tsv` |
| **2. Consolidación** | Las 5 cuotas, **27.922** filas concatenadas, 86 columnas tras unir el esquema | Concatenación, unión de columnas y deduplicación por `link` conservando la primera aparición | Entran **27.922**, salen **27.922**, duplicados detectados **0**, duplicados eliminados **0**, duplicados residuales **0**. Nulos en columnas clave: `link` 0, `precio` 0, `ubicacion` 0, `barrio` 0, `m2` **26** | `data/interim/mercadolibre_CABA_completo.tsv` (27.922 × 86) |
| **3. Geocodificación** | Consolidado, **27.922** × 86 | Limpieza de la dirección (corte en la primera coma, "Av." a "Avenida", descarte del texto tras un punto, normalización de la abreviatura "Al") y consulta al normalizador de USIG con 3 reintentos. Agrega `dir_limpia`, `lat`, `lon`, `geo_status` | Entran **27.922**, salen **27.922**. Direcciones geocodificables **26.338** (94,3%), no geocodificables **1.584**. Tasa de éxito **82,06%**: `OK` 22.912, `SIN_RESULTADO` 3.406, `NO_GEOCODIFICABLE` 1.584, `SIN_COORDENADAS` 20. Coordenadas presentes **22.912**. Duplicados residuales **0**. Nulos clave sin cambios (`m2` 26) | `data/interim/propiedades_geocodificadas.tsv` (27.922 × 90) |
| **4. Enriquecimiento** | Geocodificado, **27.922** × 90, de las cuales **22.912** con coordenadas | GeoJSON de estaciones de subte de BA Data (cacheado en `data/external/`). Haversine a la estación más cercana y al polo de centralidad más cercano (Obelisco, Puerto Madero, Catalinas). KMeans por barrio sobre lat/lon, k = min(5, n/30), `random_state=42`, `n_init=10` | Entran **27.922**, salen **27.922**. Con `dist_transporte_m` **22.912**, con `dist_centralidad_m` **22.912**. Media a transporte **925 m**, media a centralidad **5.696 m**. Sub-zonas creadas **198**. Duplicados residuales **0**. Nulos clave sin cambios (`m2` 26) | `data/processed/propiedades_enriquecidas.tsv` (27.922 × 93) |

**Duplicados.** La deduplicación de las etapas 1 y 2 es por `link`, y los links traen parámetros de seguimiento que cambian en cada búsqueda. Por eso detecta 0 duplicados, aunque 68 avisos aparecen dos veces con distinto link (27 de ellos, listados en dos barrios; el resto, dos veces en la misma búsqueda). Se resuelven en la etapa 5, deduplicando por el ID del aviso: entre dos filas del mismo ID queda la que coincide con el polígono oficial del barrio (17 casos) y, si ninguna coincide o no hay coordenadas, la primera.

### Etapas 5 y 6 y scripts auxiliares (PreEntregas 2 y 3)

Los números son los de la regeneración del 02/11/2026 en la Mac de referencia (commit 963d072).

| # | Qué entra | Qué transformación se aplica | Qué control se ejecuta | Qué archivo sale |
|---|---|---|---|---|
| **5. Limpieza** (`src/limpiar.py`, `src/limpieza.py`) | Enriquecido, **27.922** × 93, más `accesibilidad.tsv` para resolver duplicados | La lógica del notebook 01: ID del aviso y deduplicación con el polígono oficial, precio corregido ("BAJÓ DE PRECIO"), superficie de trabajo, antigüedad, expensas (menores a ARS 1.000 a vacío), baños en 0 a vacío, pisos cargados como número de unidad, exclusión de lo que no es un departamento usado en venta, y marcas (posible duplicado, alquiler, casa, barrio popular, atípicos con IQR del precio por m² en su zona como marca informativa, incoherencias) | Entran **27.922**, salen **27.578** (344 eliminados: 68 duplicados por ID, 237 en pozo, 28 con superficie inválida, 5 en pesos, 4 bajo el precio mínimo, 1 precio imposible, 1 que no es venta). Duplicados residuales por `id_aviso` **0**. El notebook 01 verifica al final que su resultado coincide con el de la etapa | `data/processed/propiedades_limpias.tsv` (27.578 × 115), `registro_limpieza.csv` |
| **6. Análisis** (`src/analisis.py`, con `modelo.py`, `validacion.py`, `regla.py`) | Limpio, **27.578** × 115, más `accesibilidad.tsv`, `permisos_obra.tsv`, `seguimiento_avisos.csv` y `config/costos.yaml` | Avisos con geocodificación dudosa tratados como sin coordenadas; sub-zonas estables (ARI con bootstrap); precio esperado fuera de muestra con el modelo oficial (`analisis.modelo_oficial`, lineal ampliado) en 5 vueltas agrupadas por unidad y sin fuga; intervalo del 80% por aviso (conformal por barrio); brecha, marca de la ciudad, marca por barrio y marca de consenso con el gradient boosting; señales de error de carga; regla R1; regla de decisión con costos (brecha neta, nivel de refacción, riesgo legal, liquidez por ambientes); ranking por unidad y embudo; explicación por aviso | **27.578** avisos / **25.169** unidades analizados, **1.819** / **1.714** marcados, **1.556** / **1.470** bajo el umbral de su barrio, **1.455** / **1.375** cumplen la regla (lista oficial), **884** / **840** candidatos después de costos. Error mediano fuera de muestra 12,5%; cobertura del intervalo 79,5%. QC en `outputs/logs/qc_06_analisis.json` | `precio_esperado.tsv` (27.578 × 77), `unidades_marcadas.csv` (1.714), `avisos_a_investigar.csv` (1.375), `embudo_ranking.csv`, `explicacion_avisos.tsv` (1.819) |
| `src/fuentes_externas.py` | Enriquecido más los snapshots de BA Data en `data/external/` (tren, Metrobus, premetro, espacios verdes, barrios, barrios populares) | Distancias a puntos con haversine, a polígonos en UTM 21S; barrio oficial del punto y si coincide con el buscado; distancia al barrio buscado y `geo_dudoso` (más de 1 km) | 27.922 filas; 22.912 con coordenadas; `barrio_coincide` 18.687 sí / 4.225 no; `geo_dudoso` 249; en barrio popular 96. Controles por fuente en `docs/entregas_grupo/control_fuentes.md` | `data/processed/accesibilidad.tsv` (27.922 × 14) |
| `src/permisos_obra.py` | Enriquecido más `data/external/obras-registradas.csv` | Permisos de obra nueva a menos de 500 m en los 3 años previos al scraping, una vez por obra (deduplicado por parcela y por punto) | 27.922 filas; mediana 9 obras; `tests/test_permisos_obra.py` reproduce el archivo versionado desde el snapshot | `data/processed/permisos_obra.tsv` (27.922 × 2) |
| `src/seguimiento.py` | Cuotas del segundo relevamiento (`data/raw/relevamiento_2/`, 27 y 28/10/2026) y el dataset limpio | Une las cuotas, deduplica por ID y cruza cada aviso del primer relevamiento: sigue, republicado (misma dirección, m² y ambientes con otro ID) o salió; marca los barrios truncados por el tope de paginación | 27.516 avisos en el segundo relevamiento; una fila por aviso del primero (27.578). Se corre **después** de la etapa 5 y **antes** de la 6, que lo usa para la liquidez por ambientes y corta si las filas no coinciden | `data/processed/relevamiento_2.tsv`, `seguimiento_avisos.csv` |
| `src/exportar_dashboard.py` | Salidas de la etapa 6, `accesibilidad.tsv`, estaciones y `config/costos.yaml` | Una fila por unidad de la lista oficial con lo que muestra la ficha y lo que necesita el simulador; embudo, indicadores, resumen por barrio, sensibilidad de la regla y parámetros de costos por escenario; capas de estaciones | `tests/test_exportar_dashboard.py` compara los JSON con el embudo y el ranking | `docs/dashboard/data/avisos.json`, `resumen.json`, `estaciones.json`, `fondo.json` (todos los avisos con coordenadas, para el fondo del mapa). Además calcula el tercer nivel del dashboard, **candidato firme** (candidato aun vendiendo al límite inferior del rango del 80%: 83 unidades), y la tasa de salida por decil de brecha del notebook 05 |

El detalle de los desafíos técnicos (bloqueo por CloudFront, IP de datacenter vs.
residencial, contenido corrupto por compresión Brotli, distinción entre
emprendimientos y propiedades usadas, límite de paginación y normalización de
direcciones) está en [`docs/proceso_tecnico.md`](proceso_tecnico.md).

---

## 2. Qué viene versionado y qué se regenera

Los datasets se versionan a propósito. Sin ellos habría que rehacer entre 8 y 15
horas de scraping para poder correr cualquier etapa, y el pipeline dejaría de ser
reproducible por un tercero.

| Archivo | ¿Versionado? | Tamaño | Cómo se regenera |
|---|---|---|---|
| `data/raw/cuotas/cuota1..5.tsv` | Sí | 19,4 MB | Etapa 1, `--incluir-scraping`. Entre 8 y 15 h, IP residencial |
| `data/interim/mercadolibre_CABA_completo.tsv` | Sí | 19,7 MB | Etapa 2, segundos |
| `data/interim/propiedades_geocodificadas.tsv` | Sí | 20,9 MB | Etapa 3, unas 2 h contra USIG |
| `data/processed/propiedades_enriquecidas.tsv` | Sí | 21,5 MB | Etapa 4, menos de 1 min más la descarga del GeoJSON |
| `data/external/estaciones-de-subte.geojson` | Sí | 16 KB | Snapshot congelado, ver abajo. Con `--forzar-descarga` se rebaja fresco |
| `data/external/*.geojson` (tren, Metrobus, premetro, espacios verdes, barrios, barrios populares) y `obras-registradas.csv` | Sí | 40 MB | Snapshots de BA Data del 27 y 28/10/2026, con SHA-256 en `docs/entregas_grupo/fuentes_externas.md`. No se rebajan: `src/fuentes_externas.py` y `src/permisos_obra.py` los leen sin red |
| `data/processed/accesibilidad.tsv`, `permisos_obra.tsv` | Sí | 19 MB | `python3 src/fuentes_externas.py` y `python3 src/permisos_obra.py`, un par de minutos cada uno, sin red |
| `data/processed/propiedades_limpias.tsv`, `registro_limpieza.csv` | Sí | 26 MB | Etapa 5, segundos |
| `data/raw/relevamiento_2/*.tsv` | Sí | 20 MB | Segundo scraping (27 y 28/10/2026). No se repite: es una foto de esa fecha. `cuota2.tsv` es el parcial de una corrida que se cortó (se usa solo Villa Crespo; el resto está en `cuota_custom.tsv`): se renombró el 03/11/2026 porque `.gitignore` excluye `*_parcial.tsv` y sin él `relevamiento_2.tsv` no se reproducía |
| `data/processed/relevamiento_2.tsv`, `seguimiento_avisos.csv` | Sí | 25 MB | `python3 src/seguimiento.py`, segundos, después de la etapa 5 |
| `data/processed/precio_esperado.tsv`, `unidades_marcadas.csv`, `avisos_a_investigar.csv`, `embudo_ranking.csv`, `explicacion_avisos.tsv` | Sí | 20 MB | Etapa 6, unos 2 min. **Generados en la Mac de referencia** (sección 10: el gradient boosting puede variar entre plataformas) |
| `data/interim/shap_gbm.tsv` | Sí | 1,2 MB | Notebook 04, sección 9: se recalcula solo si no coincide con las predicciones (varios minutos) |
| `docs/dashboard/data/*.json` | Sí | 2,6 MB | `python3 src/exportar_dashboard.py`, segundos, después de la etapa 6 |
| `outputs/logs/pipeline.log`, `outputs/logs/qc_*.json` | No | — | Los escribe cada corrida |
| `docs/corrida-documentada/*` | Sí | 13 KB | No se regenera: es una instantánea curada |
| `*_parcial.tsv` | No | — | Los escribe y borra el propio pipeline |

Total versionado: unos 225 MB (19 MB son las cuotas crudas del primer relevamiento).

### Por qué el GeoJSON de subte se versiona

`data/external/estaciones-de-subte.geojson` es un **snapshot** del dataset de
estaciones de subte de BA Data, descargado el **14 de septiembre de 2026**, con
**90 estaciones**. SHA256:

```
b001f82960c34cedd5489e149498e7a32d978ada1537df7eab69a5a6b935226f
```

Se versiona por una razón concreta: `dist_transporte_m` se calcula contra ese
set de estaciones. Si BA Data publica una versión distinta, por ejemplo al
inaugurar una estación, esa columna cambiaría **sin que nadie toque una línea de
código** y el hash del dataset final dejaría de reproducirse por un motivo
invisible desde el repositorio. Congelarlo convierte la etapa 4 en
determinística y, de paso, la vuelve reproducible sin conexión.

La etapa 4 **usa el cache si existe** y solo sale a la red cuando falta. Para
traer la versión viva de BA Data y pisar el snapshot:

```bash
python3 src/enriquecimiento.py --forzar-descarga        # etapa suelta
python3 run_pipeline.py --forzar-descarga-subte         # desde el runner
```

Si hacés eso, es esperable que `dist_transporte_m` y el hash del dataset final
cambien. Es el comportamiento correcto: el snapshot documenta una corrida, no
pretende ser la versión actual del dato.

### Por qué los logs no se versionan pero la evidencia sí

`outputs/logs/` es salida de trabajo: **cada corrida lo sobrescribe**. Versionarlo
tendría dos problemas. Uno, cualquier corrida ensucia el árbol de git. Dos, y
más grave, la evidencia se pisaría sola: después de un spot check con
`--limite 20`, el `qc_03_geocoding.json` del repositorio pasaría a describir una
corrida de 20 filas en lugar de la corrida documentada de 27.922.

Por eso la evidencia vive aparte, en
[`docs/corrida-documentada/`](corrida-documentada/): una instantánea curada
e inmutable de los controles de calidad de la corrida documentada y de los tres
spot checks, con un README que explica qué prueba cada archivo y en qué entorno
se generó. Esa carpeta sí se versiona.

---

## 3. Instalación

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
> Windows suele ser `python`. Todos los ejemplos de este documento usan `python3`.
> Dentro de un entorno virtual ya activado, `python` y `python3` apuntan al
> mismo intérprete.

`run_pipeline.py` chequea la versión al arrancar: corta con un mensaje claro si
el intérprete es anterior a 3.9, y avisa (sin cortar) si no es 3.9, para que
quede explícito cuándo la reproducción byte a byte no está garantizada. El
mismo chequeo mínimo corre al invocar cualquier etapa por separado.

Todas las versiones de `requirements.txt` están verificadas contra PyPI y
todas tienen wheels para CPython 3.9. La instalación está **probada de punta a
punta**: `pip install -r requirements.txt` corre limpio en macOS con Python 3.9
bajando wheels `cp39` para todos los paquetes, y en Linux con Python 3.9.23,
donde además se verificó que el pipeline reproduce los datasets versionados.

No hace falta editar ningún archivo. Todas las rutas se resuelven a partir de la
ubicación del repositorio, así que los scripts se pueden invocar desde cualquier
directorio de trabajo.

---

## 4. Cómo correr el pipeline

### Runner único

```bash
python3 run_pipeline.py                      # etapas 2 a 6 (default)
python3 run_pipeline.py --desde-etapa 5      # limpieza y análisis, unos 3 minutos
python3 run_pipeline.py --desde-etapa 6      # solo el análisis
python3 run_pipeline.py --hasta-etapa 4      # etapas 2, 3 y 4, hasta el dataset enriquecido
python3 run_pipeline.py --incluir-scraping   # etapas 1 a 6
```

Por defecto **el pipeline arranca en la etapa 2**, asumiendo que las cuotas ya
están descargadas en `data/raw/cuotas/` (vienen versionadas), **y llega hasta la 6**.
Las etapas 5 y 6 leen además `accesibilidad.tsv`, `permisos_obra.tsv` y
`seguimiento_avisos.csv`, que vienen versionados; si falta alguno, la etapa 5 avisa
y resuelve los duplicados por orden de aparición, y la etapa 6 corta.

> ⚠️ **El scraping completo son entre 8 y 15 horas.** La etapa 1 solo corre con
> `--incluir-scraping` explícito, nunca por accidente. Además debe ejecutarse desde
> una **IP residencial**: desde Google Colab u otro entorno con IP de datacenter se
> dispara el bloqueo anti-bot de la plataforma (ver
> [`docs/proceso_tecnico.md`](proceso_tecnico.md), sección 2.2). Por eso las
> cuotas ya descargadas están versionadas en el repositorio.

### Validar la cadena sin volver a geocodificar

La etapa 3 consulta un servicio público gratuito 26.338 veces y tarda unas dos
horas. Para validar la cadena no hace falta repetirla: el TSV geocodificado
viene versionado y se puede verificar en segundos.

```bash
python3 run_pipeline.py --verificar-geocoding          # etapas 2, 3 (verificación), 4, 5 y 6
python3 src/geocoding_propiedades.py --verificar       # solo la etapa 3
```

En ese modo la etapa 3 **no hace ninguna llamada a USIG**. En su lugar recalcula
la limpieza de direcciones sobre la entrada, la contrasta con la que quedó
guardada, revisa la coherencia interna del resultado y corre el mismo bloque de
control de calidad. No escribe ningún dataset, solo el log de QC. Son ocho
controles:

| Control | Resultado sobre el dataset versionado |
|---|---|
| Misma cantidad de filas que la entrada | 27.922 |
| Columnas de geocodificación presentes | `dir_limpia`, `lat`, `lon`, `geo_status` |
| Mismos links y en el mismo orden | sí |
| `dir_limpia` se reproduce recalculándola desde `ubicacion` | 27.922 / 27.922 |
| Ninguna fila quedó sin `geo_status` | 0 pendientes |
| Hay coordenadas exactamente en las filas con `geo_status` OK | 22.912 y 22.912 |
| Las direcciones no geocodificables están marcadas como tales | 1.584 |
| Sin duplicados por link | 0 |

### Etapas por separado

```bash
python3 src/scrapper_mercadolibre.py --cuota cuota3
python3 src/unir_cuotas.py
python3 src/geocoding_propiedades.py
python3 src/enriquecimiento.py
python3 src/limpiar.py
python3 src/analisis.py
```

Cada script tiene su propio `--help` con todos los parámetros disponibles.

### Scripts auxiliares de la PreEntrega 3

No están en el runner: leen snapshots versionados, sus salidas también vienen
versionadas y solo hay que volver a correrlos si cambia una fuente, el dataset
enriquecido o el limpio. El orden importa, porque cada uno alimenta al siguiente:

```bash
python3 src/fuentes_externas.py      # accesibilidad.tsv: antes de la etapa 5 (resuelve duplicados por ID)
python3 src/permisos_obra.py         # permisos_obra.tsv: antes de la etapa 6
python3 run_pipeline.py --desde-etapa 5 --hasta-etapa 5
python3 src/seguimiento.py           # seguimiento_avisos.csv: después de la etapa 5 y antes de la 6
python3 run_pipeline.py --desde-etapa 6
python3 src/exportar_dashboard.py    # docs/dashboard/data/*.json: después de la etapa 6
```

Si cambia el dataset limpio (una fila más o menos, u otro orden), hay que regenerar
el seguimiento antes de la etapa 6: la etapa 6 verifica que `seguimiento_avisos.csv`
tenga los mismos avisos en el mismo orden y corta si no. Los notebooks 03 a 07 leen
estas salidas, así que después de regenerarlas conviene volver a ejecutarlos
(`jupyter nbconvert --to notebook --execute --inplace notebooks/NN_*.ipynb`; el 04
tarda unos 4 minutos y el 06 unos 10).

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

El parcial **se borra** cuando la corrida termina bien. Por eso `--parcial` se
niega a apuntar al mismo archivo que `--entrada` o que `--salida`: apuntarlo a un
dataset versionado lo destruiría. Si lo que querés es validar sin geocodificar,
usá `--verificar`.

---

## 5. Configuración

Todo lo parametrizable vive en [`config/config.yaml`](../config/config.yaml):

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
- **`limpieza`**: los umbrales de la etapa 5 (precio mínimo, rango de superficie, antigüedad
  máxima, expensas máximas y mínimas, k del IQR, tipo de cambio, desde cuántos pisos se mide
  la incoherencia de piso). El notebook 01 lee los mismos valores.
- **`analisis`**: la etapa 6: vueltas de la validación cruzada, semilla, mínimo por zona,
  umbral de la brecha (−25%), mínimo de avisos por barrio para el umbral por barrio, modelo
  oficial (`lineal_ampliado` o `gbm`; el otro se usa para la marca de consenso), nivel del
  intervalo de predicción (0,80), ARI mínimo para usar las sub-zonas de un barrio (0,7) y el
  umbral de la brecha neta de la regla de decisión (+10%).
- **`fuentes_externas`** y **`permisos_obra`**: rutas de los snapshots, proyección métrica,
  qué clases de espacio verde cuentan, equivalencias de barrio (Barrio Norte), umbral de
  `geo_dudoso` (1 km), tipos de trámite, ventana de 3 años y radio de 500 m.
- **`qc`**: qué columnas se consideran clave para el conteo de nulos.

Los **costos de la regla de decisión** viven en [`config/costos.yaml`](../config/costos.yaml):
costos de entrada (escribano, Sellos con su umbral, comisión, otros), refacción por nivel, brecha
publicado-cierre, costos de salida (comisión del vendedor, mitad de Sellos, certificados, Ganancias
con alícuota 0 como supuesto declarado), liquidez, las expresiones regulares del estado del
inmueble y las señales de riesgo legal, cada valor con su fuente y un rango optimista y pesimista.

Cualquier valor del YAML puede pisarse por línea de comandos sin tocar el archivo.

---

## 6. Controles de calidad

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

## 7. Verificación

Hay dos cosas distintas y conviene no confundirlas.

### 7.1. Suite de tests (pytest)

Desde la raíz del repositorio, con el entorno de `requirements.txt` instalado:

```bash
pytest            # toda la suite, 161 tests, unos 2 minutos, sin red
pytest -v         # con el nombre de cada test
pytest tests/test_limpieza.py   # un solo archivo
```

La misma suite corre en GitHub Actions (`.github/workflows/tests.yml`) en cada
push y pull request, con Python 3.9.

| Archivo | Qué cubre |
|---|---|
| `tests/test_pipeline.py` | Los controles de `verificar_offline.py`, uno por test: parseo del scraper contra HTML guardado (etapa 1), SHA256 del consolidado (etapa 2), del geocodificado con USIG replayeado (etapa 3) y del enriquecido con el GeoJSON de subte versionado (etapa 4), encadenado de rutas y ausencia de rutas absolutas |
| `tests/test_limpieza.py` | `corregir_precio`, `parsear_superficie`, `parsear_antiguedad`, `parsear_expensas`, `marcas_del_titulo`, `estado_y_riesgo_del_titulo`, `piso_desde_numero_de_unidad` y `outliers_iqr_por_grupo`, con casos armados a mano (incluidos los errores de carga que cada función corrige) |
| `tests/test_deduplicar.py` | Duplicados por ID: se conserva la fila que coincide con el polígono oficial, si no la primera, y la fila conservada queda en la posición de la primera aparición (el orden de las filas define las vueltas) |
| `tests/test_fuentes_externas.py` | Distancias a puntos y polígonos, área verde en el radio, barrio oficial y coincidencia, barrios populares, `geo_dudoso`, con geometrías chicas armadas a mano y una corrida sobre el snapshot |
| `tests/test_analisis.py` | La etapa 6 sobre un dataset sintético: vueltas agrupadas por unidad sin fuga, marcas, ranking por unidad y embudo coherente |
| `tests/test_explicacion.py` | La explicación por aviso: las contribuciones del lineal suman exactamente la predicción, el SHAP por permutación suma la del gradient boosting, y la tabla de factores de la etapa 6 |
| `tests/test_regla.py` | La regla de decisión con los costos reales de `config/costos.yaml`: Sellos con umbral, refacción por estado, brecha neta, riesgo legal y niveles de decisión |
| `tests/test_inferencia.py` | Bootstrap por unidad, fila de un test, corrección de Holm y tabla de coeficientes |
| `tests/test_segmentos.py` | MCA e índice de equipamiento, K-means, nombres de segmentos y estabilidad, sobre datos sintéticos |
| `tests/test_no_modifica_entradas.py` | Regresión: las funciones que reciben `y` no modifican lo que reciben |
| `tests/test_exportar_dashboard.py` | Los JSON del dashboard coinciden con el embudo y el ranking versionados |
| `tests/test_geocoding.py` | `limpiar_direccion`: abreviaturas de avenida, "Al", texto después de un punto, esquinas y direcciones no geocodificables |
| `tests/test_enriquecimiento.py` | `haversine_np` (Obelisco a Plaza de Mayo, ~1 km; un grado de latitud, 111,2 km) y `parsear_estaciones` |
| `tests/test_eda.py` | `precio_relativo` y `error_vara_fuera_de_muestra` |
| `tests/test_permisos_obra.py` | Filtro de tipos, ventana y parcelas, conteo en el radio de 500 m, y una corrida completa de `src/permisos_obra.py` sobre el snapshot que tiene que reproducir `data/processed/permisos_obra.tsv` |

`tests/verificar_offline.py` se conserva como script de consola con salida legible;
verifica lo mismo que `test_pipeline.py`. Los tests de las etapas 5 y 6 usan datos
sintéticos (`tests/conftest.py`) y los archivos versionados chicos, así que la suite
sigue sin necesitar red.

### 7.2. Smoke test reproducible, sin red

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
| 4 | Se corre `enriquecimiento` con el GeoJSON de subte **versionado** y se compara por **SHA256** | Reproducción byte a byte, `dist_transporte_m` incluida |
| cadena | Se comprueba que la salida de cada etapa es la entrada de la siguiente y que no queda ninguna ruta absoluta en el código | Es justamente lo que estaba roto antes |

Resultado de la última corrida: **26 de 26 controles OK**, sobre
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

Las tres etapas que no dependen del scraping dan **hash idéntico** al dataset
versionado: consolidado, geocodificado y enriquecido. Con el GeoJSON de subte
versionado, la etapa 4 reproduce las 93 columnas, `dist_transporte_m` incluida,
y las 198 sub-zonas. O sea que la cadena entera, desde las cuotas versionadas
hasta el dataset final, es reproducible byte a byte **sin tocar la red**.

### 7.3. Corrida completa real

El smoke test no reemplaza una corrida real: las etapas 1, 3 y 4 dependen de
MercadoLibre, USIG y BA Data respectivamente. La corrida completa contra los
servicios reales está documentada en la sección siguiente.

---

## 8. Corrida documentada de punta a punta

Los datasets versionados salen de una corrida completa hecha en macOS con
Python 3.9 y las versiones fijadas en `requirements.txt`. Los controles de
calidad de esa corrida y de los spot checks descriptos más abajo están
versionados como evidencia en
[`docs/corrida-documentada/`](corrida-documentada/).

**Comando equivalente en la estructura actual:**

```bash
python3 run_pipeline.py --incluir-scraping
```

Esta sección cubre las etapas 1 a 4. Las etapas 5 y 6 y los scripts auxiliares se
regeneraron por última vez el 02/11/2026 en la Mac de referencia (Python 3.9.6, commit
963d072), con los controles en `outputs/logs/qc_05_limpieza.json` y `qc_06_analisis.json`;
sus números están en la tabla de la sección 1.

### 8.1. Etapa 1, scraping

Cinco cuotas corridas en sesiones separadas, con `con_detalle=true` y
`max_paginas_por_barrio=42`.

| Cuota | Barrios | Filas | Columnas |
|---|---|---|---|
| cuota1 | 8 | 13.000 | 86 |
| cuota2 | 10 | 7.514 | 85 |
| cuota3 | 10 | 4.050 | 86 |
| cuota4 | 10 | 1.913 | 86 |
| cuota5 | 9 | 1.445 | 85 |
| **Total** | **47** | **27.922** | **86 tras unir esquemas** |

Duplicados de `link` dentro de cada cuota: 0. Cuatro barrios llegaron al tope de
paginación con 2.016 avisos cada uno (Palermo, Belgrano, Caballito, Recoleta);
el más chico fue Villa Riachuelo con 15.

### 8.2. Etapa 2, consolidación

Entran 27.922, salen 27.922. Duplicados detectados 0, eliminados 0, residuales 0.
Nulos en columnas clave: solo `m2` con 26.
Evidencia: `docs/corrida-documentada/qc_02_consolidacion.json`.

### 8.3. Etapa 3, geocodificación

Entran 27.922, salen 27.922, 90 columnas. Direcciones que pasaron la limpieza
previa: 26.338 (94,3%).

| `geo_status` | Filas | % |
|---|---|---|
| `OK` | 22.912 | 82,06% |
| `SIN_RESULTADO` | 3.406 | 12,20% |
| `NO_GEOCODIFICABLE` | 1.584 | 5,67% |
| `SIN_COORDENADAS` | 20 | 0,07% |

Evidencia: `docs/corrida-documentada/qc_03_geocoding_verificacion.json`.

### 8.4. Etapa 4, enriquecimiento

Entran 27.922, salen 27.922, 93 columnas. Con distancias calculadas: 22.912.
Estaciones de subte descargadas de BA Data: 90. Media a la estación más
cercana: **925 m**. Media al polo de centralidad más cercano: **5.696 m**.
Sub-zonas creadas: **198**.
Evidencia: `docs/corrida-documentada/qc_04_enriquecimiento.json`.

### 8.5. Qué está verificado y cómo

Esta es la parte que importa para juzgar la reproducibilidad. Hay tres niveles
de evidencia y conviene no confundirlos.

| Etapa | Verificado sin red (smoke test) | Verificado CON red real | Qué queda apoyado solo en el dataset versionado |
|---|---|---|---|
| 1. Scraping | Parseo de precios, atributos, paginación y ficha de detalle, contra HTML guardado | **Sí.** Spot check real contra MercadoLibre: 1 barrio, sin fichas, 1 página, 15 avisos, 0 duplicados, 14 columnas | La corrida masiva de 47 barrios con fichas, que son 8 a 15 horas. Sus resultados son las cuotas versionadas |
| 2. Consolidación | **Sí, SHA256 idéntico** al dataset versionado | No requiere red | Nada |
| 3. Geocodificación | **Sí, SHA256 idéntico**, con las respuestas de USIG replayeadas y la limpieza de direcciones recalculada sobre las 27.922 filas | **Sí.** Spot check real contra USIG con `--limite 20`: 19 `OK` y 1 `SIN_RESULTADO`, 95% en esas 20 | Las 26.338 consultas de la corrida masiva, que son unas 2 horas contra un servicio público gratuito |
| 4. Enriquecimiento | **Sí, SHA256 idéntico**, usando el GeoJSON de subte versionado. Cubre las 93 columnas, `dist_transporte_m` incluida | **Sí, completo y SHA256 idéntico.** Bajando el GeoJSON real de BA Data, el TSV regenerado coincide byte a byte con el versionado | Nada |

En resumen: **las cuatro etapas tienen su camino de red ejercitado contra el
servicio real**, y las etapas 2, 3 y 4 reproducen los datasets versionados con
hash idéntico, tanto contra los servicios reales como offline. Lo único que no se reejecutó es el volumen del scraping y el
volumen de la geocodificación, por costo de tiempo y por no castigar
innecesariamente servicios públicos gratuitos. En ambos casos el camino de
código es el mismo que ejercitan los spot checks.

### 8.6. Los spot checks, reproducibles

```bash
# Etapa 1: un barrio chico, sin fichas, una página. ~1 request.
python3 src/scrapper_mercadolibre.py --barrios villa-riachuelo --sin-detalle \
    --max-paginas 1 --salida-dir /tmp/prueba_scraping

# Etapa 3: 20 direcciones reales contra USIG. ~20 requests.
python3 src/geocoding_propiedades.py --limite 20 --salida /tmp/geo_prueba.tsv \
    --parcial /tmp/geo_parcial.tsv --sin-resume

# Etapa 4: baja el GeoJSON de verdad y compara contra el dataset versionado.
python3 src/enriquecimiento.py --salida /tmp/enriquecido_nuevo.tsv
shasum -a 256 /tmp/enriquecido_nuevo.tsv data/processed/propiedades_enriquecidas.tsv
```

Son unos 25 requests en total, contra los 26.338 de la corrida completa.
Resultado obtenido el 14 de septiembre de 2026, con los hashes de la etapa 4
coincidiendo:

```
498328bdefbcbb8e2f7c1552688a4639de8dd32e4ede91f962653894a3e0d9d9  /tmp/enriquecido_nuevo.tsv
498328bdefbcbb8e2f7c1552688a4639de8dd32e4ede91f962653894a3e0d9d9  data/processed/propiedades_enriquecidas.tsv
```

---

## 9. Arreglos técnicos de la PreEntrega 1

Esta versión no cambia la lógica analítica ni los resultados. Los tres datasets son
bit a bit los mismos. Lo que cambió es estructura, parametrización y documentación,
más un único cambio de comportamiento deliberado que está documentado aparte, al
final de esta sección.

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
| No había forma de validar la etapa 3 sin repetir 26.338 consultas a un servicio público y dos horas de espera | Modo `--verificar`: ocho controles sobre el geocodificado existente, cero llamadas a USIG |
| Nada impedía apuntar `--parcial` a un dataset versionado, y el parcial se borra al terminar la corrida | El script se niega a arrancar si `--parcial` coincide con `--entrada` o con `--salida` |

Ninguno de esos cambios altera los datasets. Los dos arreglos de bug tampoco: el
primero solo limpia un archivo temporal y el segundo solo afecta el camino de
retome de una corrida cortada, que en la corrida documentada no se activó.

### Un cambio de comportamiento deliberado

Hay **un solo punto** donde el pipeline se comporta distinto del script original.
No es un arreglo de bug sino una decisión de diseño, y por eso va separado de la
tabla de arriba.

**Qué hacía el original.** Si fallaba la descarga del GeoJSON de estaciones de
subte de BA Data, `descargar_estaciones_subte()` capturaba la excepción,
imprimía un aviso y devolvía `None`. La etapa seguía adelante y escribía el
dataset final con `dist_transporte_m` en `NaN` para las 27.922 filas.

**Qué hace ahora.** La etapa 4 corta con código de salida 1 y no escribe nada.

**Por qué.** Un dataset con una columna entera en `NaN` tiene el mismo nombre, la
misma cantidad de filas y las mismas 93 columnas que uno correcto. Pasa
desapercibido y se arrastra al análisis. Un error visible, en cambio, se corrige
en el momento. El mensaje de corte dice exactamente qué hacer:

```
[!] No se pudo obtener el GeoJSON de estaciones de subte de BA Data.
    Motivo: <la excepción>
    URL:    <la URL configurada>

    La etapa 4 CORTA en lugar de continuar. Si siguiera, dist_transporte_m
    quedaría en NaN para las 27.922 filas y el dataset resultante parecería
    completo sin serlo.

    Qué hacer:
      1. Reintentá: el portal de BA Data suele tener caídas cortas.
      2. Revisá la conectividad hacia cdn.buenosaires.gob.ar, por ejemplo
         curl -I <la URL>
      3. Si ya bajaste el GeoJSON alguna vez, dejalo en
         data/external/estaciones-de-subte.geojson y la etapa lo usa sin pedir red.
      4. También podés apuntar a una copia local con
         python3 src/enriquecimiento.py --subte-geojson RUTA/AL/ARCHIVO.geojson
```

**Alcance.** El cambio solo afecta el camino de error. En una corrida donde la
descarga funciona, el resultado es idéntico al del script original, como
confirma el smoke test offline.

---

## 10. Limitaciones técnicas

- **El GeoJSON de subte es un snapshot, no el dato vivo.**
  `data/external/estaciones-de-subte.geojson` es una copia congelada del dataset
  de BA Data descargada el **14 de septiembre de 2026**, con **90 estaciones**.
  Se versiona a propósito para que `dist_transporte_m` sea determinística y la
  etapa 4 reproducible sin red, pero eso significa que **no refleja
  inauguraciones ni correcciones posteriores** del portal. Si BA Data publicó
  una versión más nueva, este repositorio sigue usando la de esa fecha hasta que
  alguien corra `--forzar-descarga`. Para un análisis que dependa del estado
  actual de la red de subte, conviene rebajarlo y asumir que el hash del dataset
  final va a cambiar.
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
- **La asignación de las vueltas de validación cruzada depende del orden de las filas.**
  `modelo.grupo_de_unidad` numera las unidades (dirección y m²) por orden de aparición
  en el dataset limpio y `modelo.folds_agrupados` permuta esos números con una semilla
  fija. Con las mismas filas en otro orden, las unidades reciben otros números y otras
  vueltas: el 02/11/2026, mover 17 filas de lugar (una versión preliminar de la regla
  de duplicados por ID) reasignó la vuelta de 9.941 avisos, movió el error del modelo
  de 12,5% a 12,6%, la lista oficial de 1.362 a 1.331 unidades y dejó a Villa Santa
  Rita como barrio inestable. Por eso la regla definitiva conserva la fila elegida en
  la posición de la primera aparición del ID. Mientras no cambie el orden, los
  resultados son reproducibles; cualquier cambio de orden mueve los números en el
  margen. **Mejora pendiente para la entrega final:** asignar las vueltas a partir de
  la clave de la unidad (por ejemplo, un hash de la dirección y los m²), para que no
  dependan del orden de las filas.
- **El gradient boosting puede variar entre plataformas.** Con los mismos datos, la
  misma semilla y el mismo resultado del modelo lineal, la etapa 6 corrida en el
  entorno de claude.ai (Linux, Python 3.11) y en la Mac de referencia (Python 3.9.6,
  scikit-learn 1.6.1) dio el mismo gradient boosting en 3 de las 5 vueltas y uno
  distinto en las otras 2: diferencia del precio esperado con mediana 0% y p95 3,2%;
  1.442 contra 1.456 avisos marcados por ese modelo y 1.109 contra 1.112 de consenso.
  En cada máquina el resultado es determinista. La hipótesis es un empate casi exacto
  en algún corte que la aritmética de cada plataforma resuelve distinto, y desde ahí
  los árboles divergen (no verificado). Como el modelo oficial es el lineal, la lista
  oficial y el embudo no cambian. **Los archivos versionados de la etapa 6 y el
  notebook 04 se generaron en la Mac de referencia**; en otra plataforma, las columnas
  `brecha_otro_modelo`, `marcado_otro_modelo` y `marcado_consenso` pueden diferir un
  poco. El SHAP guardado (`data/interim/shap_gbm.tsv`) se recalcula solo si no
  coincide con las predicciones de la máquina donde se corre.
