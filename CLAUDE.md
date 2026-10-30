# CLAUDE.md: contexto del TP para Claude Code

Este archivo resume dónde está el trabajo, cómo trabajamos y qué falta. Leelo entero antes de tocar nada.
Lo escribió Claude (claude.ai) el 30/10/2026, al pasar el trabajo de esa conversación a Claude Code.
Si algo de acá contradice al código o a los datos, manda el código y los datos: avisá la diferencia.

## 1. El proyecto

- **Materia:** Analítica Descriptiva, ITBA, 2° cuatrimestre 2026. Profesor que corrige: José Ignacio López Sáez.
- **Grupo:** Teo, Lola, Matías y Gonzalo. Trabajás con **Gonzalo** (usa la cuenta de su mamá, Maisa; si aparece
  ese nombre es la misma persona del otro lado).
- **Caso:** un fondo de inversión inmobiliario quiere encontrar departamentos en venta en CABA publicados en
  MercadoLibre a un precio atípicamente bajo para sus características y su zona. El producto es una **lista de
  avisos a investigar**, no una lista de oportunidades: la brecha es una señal para revisar, nunca una
  subvaluación confirmada. Esta diferencia la remarcó el profe y hay que mantenerla en todo el texto.
- **Repo:** github.com/gbuhler-itba/TP-Analitica-Descriptiva, rama `main`. Se entrega el repo.
- **Entregas:** PE1 y PE2 entregadas (PE2: nota 8,9). **PE3 se entrega el jueves 5/11/2026.**
  Gonzalo además tiene el tercer parcial de la materia el miércoles 4/11.

## 2. Cómo trabajamos (importante)

- **Idioma:** español rioplatense, con voseo, informal. Respuestas concisas y listas para pegar.
- **Nunca usar raya (—) en ningún texto** (README, notebooks, markdown, comentarios, mensajes). Usar comas, dos
  puntos o paréntesis. Solo se tolera en celdas de tablas tipo "X — Y". Respetar mayúsculas de nombres propios
  sin abusar de ellas.
- **Python:** siempre comillas dobles. En la Mac de Gonzalo el intérprete es `python3` y el entorno es `.venv`
  (`source .venv/bin/activate`). Código en celdas cortas y separadas, no una celda gigante.
- **Decisiones de criterio:** si algo requiere una decisión (qué umbral, qué excluir, qué modelo), listá las
  opciones con su pro y contra, recomendá una y **preguntá antes de decidir**. No decidas solo.
- **Las interpretaciones de los notebooks las escribe Gonzalo.** Dejá las celdas con
  `> **Interpretación:** _(a completar)_`. No escribas interpretaciones por él, salvo que lo pida.
  Antes de regenerar o sobrescribir un notebook, fijate si ya completó algo (`grep -c "a completar"`) y no se lo
  pises: si hay texto suyo, editá celdas puntuales.
- **Tareas de los compañeros:** cuando Gonzalo te pase algo que hizo otro miembro del grupo, **revisalo todo
  antes de darlo por bueno** (correr, verificar números contra los datos, buscar errores) y recién después
  integrarlo. En PE3 las tres entregas tenían errores que hubo que corregir.
- **Git:** commits en castellano, descriptivos. Antes de `git push` preguntá. No reescribas historia.
- **No tocar `data/raw/`** (scraping crudo de los dos relevamientos). El scraping necesita IP residencial y
  tarda horas: no se vuelve a correr.
- **Revisá tu propio trabajo:** después de cambiar algo, corré `pytest` y verificá números. Si un número del
  README o de un notebook cambia, actualizalo en todos lados donde aparece.
- Gonzalo quiere que la entrega **se destaque**, más allá de lo mínimo. Pero con criterio: cada técnica nueva
  tiene que explicar qué resuelve, sus supuestos, cómo se valida, qué agrega frente a una alternativa más simple
  y sus límites (eso pide la consigna).
- Cuando Gonzalo diga "no entiendo", explicá más simple y con un ejemplo concreto, sin jerga.

## 3. Qué pide la consigna de la PE3

1. Evaluar las hipótesis con estadística: magnitud, incertidumbre y robustez.
2. Técnicas avanzadas, cada una con qué resuelve, supuestos, validación, qué agrega frente a una alternativa
   simple y límites. Modelos predictivos comparados contra un baseline y evaluados fuera de muestra. Segmentos e
   índices con estabilidad verificada.
3. **Dashboard interactivo** para el interlocutor (el fondo), que no sea una copia de los notebooks. El profe
   dejó libre la herramienta; elegimos **HTML estático publicado en GitHub Pages** (Power BI descartado).
4. Repo ordenado y reproducible.
5. README actualizado.

**Devolución de la PE2 (lo que hay que cerrar):** reconciliar los universos del ranking (antes había cifras
sueltas: 1.704, 1.434, 1.225, 1.590, 1.150); completar H3 con tren, Metrobus y espacios verdes; estabilidad de
sub-zonas; leakage indirecto; validación temporal con un segundo relevamiento; tests formales; costos de
refacción, liquidez, estado y riesgo legal en una regla de decisión; mantener "señal a investigar" separado de
"oportunidad de inversión"; H1 tenía apoyo débil. Detalle en `README.md` secciones 5, 6 y 11 (versión PE2).

## 4. Estructura y pipeline

```
run_pipeline.py              # runner: etapas 1 a 6 (por defecto corre hasta la 6, el scraping requiere flag)
config/config.yaml           # todos los parámetros (rutas, limpieza, análisis, fuentes externas, permisos)
config/costos.yaml           # costos de entrada, refacción, negociación, liquidez, estado y riesgo legal
src/
  scrapper_mercadolibre.py   # etapa 1
  unir_cuotas.py             # etapa 2
  geocoding_propiedades.py   # etapa 3
  enriquecimiento.py         # etapa 4 (subte, sub-zonas con k-means)
  limpiar.py + limpieza.py   # etapa 5: limpieza (reproduce el notebook 01; el notebook verifica igualdad)
  analisis.py                # etapa 6: modelo, intervalo, marcas, regla, ranking, embudo
  modelo.py                  # modelo hedónico, validación cruzada sin fuga
  validacion.py              # comparación de modelos, conformal, estabilidad, bootstrap de primas
  eda.py, qc.py, rutas.py, configuracion.py, entorno.py
  fuentes_externas.py        # tren, Metrobus, premetro, espacios verdes, barrios populares, geo_dudoso
  permisos_obra.py           # permisos de obra a 500 m
  seguimiento.py             # cruce con el segundo relevamiento
notebooks/
  01_calidad_y_limpieza      # actualizado en PE3 (lee PARAMS de config, verifica igualdad con la etapa 5)
  02_eda, 03_precio_esperado # de la PE2, con banner; números actualizados a la limpieza nueva
  04_validacion_modelos      # PE3, nuevo: faltan las interpretaciones de Gonzalo
docs/pipeline.md             # instalación, ejecución, tests, corrida documentada
docs/entregas_grupo/         # documentos de los compañeros (fuentes externas, costos, control de fuentes...)
data/external/               # snapshots versionados de BA Data (para correr sin red)
data/processed/              # datasets versionados (ver abajo)
tests/                       # pytest, 124 tests pasando
.github/workflows/tests.yml  # CI con Python 3.9
_material_grupo/             # material de trabajo, NO versionado (zips de los compañeros, PDFs viejos)
```

Datasets clave en `data/processed/`:

| Archivo | Qué es |
|---|---|
| `propiedades_enriquecidas.tsv` | salida de la etapa 4 |
| `propiedades_limpias.tsv` | etapa 5: 27.578 avisos, 115 columnas (344 excluidos) |
| `registro_limpieza.csv` | qué se excluyó y por qué |
| `accesibilidad.tsv` | distancias a tren, Metrobus, premetro, espacios verdes, barrios populares, `geo_dudoso` |
| `permisos_obra.tsv` | permisos de obra a 500 m (1.795 obras tras deduplicar; mediana CABA 9) |
| `precio_esperado.tsv` | etapa 6: precio esperado, intervalo 80%, brechas, marcas, señales por aviso |
| `unidades_marcadas.csv` | una fila por unidad marcada |
| `avisos_a_investigar.csv` | **la lista oficial** (unidades que cumplen la regla) |
| `embudo_ranking.csv` | el embudo por avisos y por unidades |
| `relevamiento_2.tsv` | segundo relevamiento consolidado |
| `seguimiento_avisos.csv` | estado de cada aviso del primer relevamiento en el segundo |

Comandos:

```bash
source .venv/bin/activate
python3 run_pipeline.py --desde-etapa 5          # limpieza + análisis (ver docs/pipeline.md para flags)
python3 src/analisis.py                           # solo etapa 6 (~2 min)
python3 -m pytest -q                              # tests
jupyter nbconvert --to notebook --execute --inplace notebooks/04_validacion_modelos.ipynb   # ~4 min
```

## 5. Decisiones tomadas (no reabrir sin preguntar)

**Limpieza (etapa 5):**
- Expensas menores a 1.000 ARS pasan a sin dato. Baños en 0 pasan a sin dato (en el modelo: `banos.fillna(1)` más
  la marca `banos_sin_dato`). Pisos cargados como número de unidad (≥100) se quedan con las centenas (`//100`).
- Atípicos con IQR sobre el **log** del precio por m², dentro de la zona, calculados solo con entrenamiento.
- Casas publicadas como departamento: se marcan (`titulo_casa`, `titulo_tipo_casa`), no se excluyen.
- Se excluyen los avisos que no son venta ("compro", "compramos").
- `incoherencia_piso`: solo cuando el edificio declara 3 o más pisos (`cantidad_de_pisos` es ambiguo).
- Marca `titulo_barrio_popular` (Rodrigo Bueno, barrio Mugica, villa 31).
- Estado del inmueble desde el título con las regex de `config/costos.yaml` (`estado_titulo`, primera coincidencia
  gana) y una columna `riesgo_<señal>` por cada riesgo legal. La vieja `marcas_del_titulo` se mantiene para el
  notebook 03 de la PE2.

**Modelo y validación (etapa 6, notebook 04):**
- Validación cruzada de 5 vueltas **agrupadas por unidad** (unidad = dirección limpia + m²). Dentro de cada
  vuelta, sin fuga: elegir barrios con sub-zona, armar la zona, marcar atípicos, ajustar y predecir.
- **Ranking por unidad:** si al menos un aviso de la unidad cumple la regla, la unidad entra. El representante
  es el aviso que llega más lejos en el embudo y, a igualdad, el más barato. Avisos con misma dirección y m² pero
  pisos declarados distintos cuentan como unidades separadas.
- **Intervalo de predicción del 80%** por aviso (conformal cruzado por barrio), opción "B": se muestra el rango,
  no un único número. Cobertura fuera de muestra 79,5%.
- **geo_dudoso** (punto a más de 1 km del barrio buscado, 249 avisos), opción "B": se tratan como sin
  coordenadas (comparados contra su barrio) y se excluyen de los análisis espaciales. Las sub-zonas se recalculan
  sin ellos.
- **Sub-zonas inestables** (ARI < 0,7): ese barrio se compara entero. Hoy no se activa en ninguno: con los
  geo_dudoso había 5 inestables, sin ellos 0 (Coghlan justo, 0,72). Sensibilidad: sacando la sub-zona a los 5
  barrios con ARI < 0,8, el error pasa de 12,69% a 12,68%. Gonzalo pidió presentarlo igual aunque no cambie nada.
- **Modelo oficial: PENDIENTE de Gonzalo** (parámetro `analisis.modelo_oficial` en `config/config.yaml`, hoy
  `lineal_ampliado`). Lo decide después de completar las interpretaciones del 04. El otro modelo se usa para la
  marca de consenso.

**Dashboard:** HTML estático en GitHub Pages.

## 6. Resultados actuales (para no recalcular de memoria; verificá contra los datos si los usás)

- Error mediano fuera de muestra: mediana de la zona 17,5%; lineal 12,7%; lineal ampliado 12,5%; Ridge 12,5%;
  gradient boosting 11,2%. Marcados: lineal ampliado ~1.800, GBM ~1.442. Jaccard entre ambos ~0,53; consenso
  ~1.125.
- Intervalo 80%: ancho mediano aproximado ±30%.
- Primas por estado (bootstrap por unidad): "a refaccionar" −16%, "a reciclar" −18% (con la regex vieja daba −8%:
  la regex vieja agarraba "refaccionado").
- **Embudo oficial** (`embudo_ranking.csv`): 27.578 avisos / 25.168 unidades analizados → 1.800 / 1.695 marcados
  (brecha < −25%) → 1.546 / 1.459 también bajo el umbral de su barrio → **1.443 avisos / 1.362 unidades sin
  señales de error de carga = lista oficial**.
- **Segundo relevamiento (27 y 28/10/2026):** 27.516 avisos. Republicaciones detectadas por dirección + m² +
  ambientes (~24%). Se excluyen los barrios truncados por el tope de 2.016 resultados en el primer relevamiento
  (Palermo, Belgrano, Caballito, Recoleta). Los avisos marcados salen del portal 46,5% contra 39,7%. Dentro del
  barrio, controlando log del valor esperado, log de m² y baja de precio previa: **+9 pp** (IC 6 a 12), logit
  OR 1,46. Gradiente: cada 10 pp más de brecha negativa, +2,1 pp de salida. Ojo: controlar por el precio
  publicado es un mal control (borra el efecto porque la brecha está hecha de ese precio); el comparable correcto
  es el valor esperado. Esto le da a H1 y a P4 una evidencia que en la PE2 no tenían. Salir del portal no es lo
  mismo que venderse: puede ser venta, retiro o republicación no detectada.
- Costos (`config/costos.yaml`): brecha publicado-cierre 4,79% (mínimo 4,18%, UCEMA); entrada total ~8,8%; Sellos
  con umbral de USD 148.941 (2,7% total abajo, 3,5% arriba, mitad comprador); refacción integral con IVA
  1.227 USD/m² (rango 1.143 a 1.549); tiempo de venta solo por ambientes, no por zona.

## 7. Pendientes, en orden

1. **Commit del orden del repo:** `CLAUDE.md` y `.gitignore` (lo del 29/10 ya está commiteado en 47ceca3).
   Correr `pytest` antes. Preguntar antes del push (hay dos commits de PE3 sin pushear, verificá con
   `git status`).
2. **SHAP sobre el gradient boosting** (propuesto, confirmar con Gonzalo): sección nueva **al final** del 04, sin
   mover las celdas existentes. Calcularlo con el modelo de cada vuelta sobre los avisos que esa vuelta no vio.
   Importancia global comparada con las primas del lineal, gráficos de dependencia (m², piso, antigüedad) y
   explicación por aviso para la ficha del dashboard. Límites: explica al modelo, no causas; con variables
   correlacionadas (lat/lon/barrio, zona/expensas) el crédito se reparte de forma algo arbitraria.
3. **Notebook 05, hipótesis:**
   - H1: colas de la brecha y P4 con el segundo relevamiento (gradiente de salida, OLS/logit con errores
     agrupados, advertencia de republicaciones, barrios truncados excluidos).
   - H2: sub-zona contra barrio con particiones agrupadas por unidad y la estabilidad del 04.
   - H3: tren, Metrobus, premetro, espacios verdes y permisos de obra, con efectos fijos de barrio y errores
     agrupados; geo_dudoso excluidos.
   - Cada una con magnitud, IC y robustez.
4. **Regla de decisión** (R1 con costos): brecha neta = brecha menos costos de entrada (con el umbral de Sellos),
   negociación y refacción según `estado_titulo`; liquidez con la tasa de salida del seguimiento por zona;
   riesgo legal como descarte o revisión. Análisis de sensibilidad. Mantener dos niveles: "señal a investigar"
   y "candidato después de costos", nunca "oportunidad confirmada".
5. **Dashboard HTML** (GitHub Pages): mapa con capas, embudo, ficha del aviso con precio esperado y rango 80%
   (y SHAP si se hace), simulador de la regla de decisión, pestaña de limitaciones. Primero una capa de datos
   chica (JSON/CSV exportado por un script en `src/`), después el HTML. Que no sea una copia de los notebooks:
   pensado para el analista del fondo.
6. **Documentación:** diccionario de datos (`docs/entregas_grupo/diccionario_datos.md`) con las columnas nuevas;
   README con sección PE3 (cambios por la devolución, cómo correr, hallazgos: H1 más fuerte, estado del
   inmueble pesa más de lo que parecía); mencionar `permisos_obra` y `fuentes_externas` en `run_pipeline.py`
   y `docs/pipeline.md`.
7. **Revisión final:** correr todo de cero (etapas 5 y 6, notebooks, tests), revisar que los números coincidan
   en README, notebooks y dashboard, buscar rayas (`grep -rn "—"`), y una revisión independiente (un subagente
   que no haya hecho el trabajo).

## 8. Errores conocidos y cuidados

- Sacar o agregar una sola fila cambia la asignación de las vueltas (factorización de grupos): si cambia el
  dataset limpio, los números de los notebooks 03 y 04 cambian y hay que actualizarlos en el texto.
- La estabilidad de sub-zonas cerca del umbral 0,7 depende de la semilla: presentarla como señal, no como
  clasificación exacta.
- La clave de republicación castea `ambientes` a float (antes no matcheaba nada por int contra str).
- `cantidad_de_pisos` a veces son plantas del depto y a veces pisos del edificio.
- Los avisos de "ideal renta" son publicidad, no inquilino: la regex de `con_inquilino` en `costos.yaml` los
  separa.
- El notebook 04 se generó con un script en la conversación de claude.ai que no está en el repo. A partir de
  ahora, la fuente es el propio `.ipynb`: editalo directamente.
