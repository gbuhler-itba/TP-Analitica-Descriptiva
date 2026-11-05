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
- **Pará después de cada bloque de trabajo** y mostrá `git diff --stat` más un resumen de 3 o 4 líneas de qué
  cambió y por qué.
- **Preguntá antes de** instalar paquetes y de restaurar, borrar o pisar archivos commiteados.
- **Si encontrás algo raro** (por ejemplo, predicciones que no coinciden con las versionadas), contalo y proponé
  opciones antes de resolverlo.
- **Entorno de referencia: la Mac de Gonzalo** (`.venv`), no el entorno de claude.ai donde se generaron algunos
  archivos (Linux, Python 3.11).

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
  validacion.py              # comparación de modelos, conformal, estabilidad, bootstrap de primas,
                             # explicación por aviso (lineal exacta, SHAP por permutación del GBM)
  eda.py, qc.py, rutas.py, configuracion.py, entorno.py
  fuentes_externas.py        # tren, Metrobus, premetro, espacios verdes, barrios populares, geo_dudoso
  permisos_obra.py           # permisos de obra a 500 m
  seguimiento.py             # cruce con el segundo relevamiento
  inferencia.py              # bootstrap por unidad, tabla de tests formales, Holm, coeficientes con IC (05)
  segmentos.py               # exploratorio (06): MCA, K-means, estabilidad; la etapa 6 no lo importa
  regla.py                   # regla de decisión: brecha neta de costos y "candidato después de costos" (etapa 6)
  chequeo_comparables.py     # chequeo del esperado de los destacados contra comparables simples (README, sección 10)
notebooks/
  01_calidad_y_limpieza      # actualizado en PE3 (lee PARAMS de config, verifica igualdad con la etapa 5)
  02_eda, 03_precio_esperado # de la PE2, con banner; números actualizados a la limpieza nueva
  04_validacion_modelos      # PE3: completo, con interpretaciones y conclusiones de Gonzalo (sección 9: SHAP)
  05_hipotesis               # PE3: H1, H2 y H3 con tests formales, magnitud, IC y robustez
  06_segmentos_exploratorio  # PE3, exploratorio: índice de equipamiento (MCA) y segmentos (K-means)
  07_regla_de_decision       # PE3: regla de decisión con costos, sensibilidad y alertas legales
docs/pipeline.md             # instalación, ejecución, tests, corrida documentada
docs/entregas_grupo/         # documentos de los compañeros (fuentes externas, costos, control de fuentes...)
data/external/               # snapshots versionados de BA Data (para correr sin red)
data/processed/              # datasets versionados (ver abajo)
tests/                       # pytest, 193 tests pasando (unos 40 s)
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
| `explicacion_avisos.tsv` | etapa 6: por aviso marcado, referencia de su zona y los 3 factores que más suben y bajan su precio esperado, con el modelo oficial (para la ficha del dashboard) |
| `../interim/shap_gbm.tsv` | SHAP del GBM de la sección 9 del 04, guardado (se recalcula solo si no coincide con las predicciones) |
| `relevamiento_2.tsv` | segundo relevamiento consolidado |
| `seguimiento_avisos.csv` | estado de cada aviso del primer relevamiento en el segundo |
| `chequeo_comparables.csv`, `.json` | chequeo del esperado de los 486 destacados contra comparables simples (README, sección 10; `src/chequeo_comparables.py`) |

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
- **Sub-zonas inestables** (ARI < 0,7): ese barrio se compara entero. Desde la regla de duplicados (02/11) se activa
  en **Villa Santa Rita** (97 avisos, 3 sub-zonas, ARI 0,68); antes no se activaba en ninguno (Coghlan justo, 0,72). Sensibilidad: sacando la sub-zona a los 5
  barrios con ARI < 0,8, el error pasa de 12,69% a 12,68%. Gonzalo pidió presentarlo igual aunque no cambie nada.
- **Modelo oficial: lineal ampliado** (parámetro `analisis.modelo_oficial` en `config/config.yaml`), decidido por
  Gonzalo en las conclusiones del 04 (sección 8): 1,2 puntos menos preciso que el GBM, pero cada prima se explica y
  la explicación por aviso es exacta. El GBM se usa para la marca de consenso.

**Dashboard:** HTML estático en GitHub Pages (`docs/dashboard/`), "Radar de avisos · CABA", estética de informe
financiero (diseño de Gonzalo, 03/11): verde oscuro #1F3A2E, crema #F7F4EE, oro #C9A227 para candidatos y ocre
#B5651D para firmes, serif (Source Serif 4) en títulos y números, sin tarjetas ni sombras, tiles en gris. Los tres
niveles se separan por luminancia y por forma (círculo, cuadrado, triángulo; validador de paleta: ΔE ≥ 14 para
deutan, protan y tritan). La lista destacada del resumen excluye barrio popular o a menos de 500 m de uno, casas o
PH, usos comerciales u oficinas, "barrio dudoso" (sin coordenadas y el título nombra otro barrio oficial; Barrio
Norte equivale a Recoleta, se ignoran calles y esquinas y los títulos que también nombran el barrio propio) y
"posible venta de varias unidades" (en block, unidades, departamentos o deptos en plural; "unidos" o "unificados"
anulan), "precio posiblemente con financiación" (financ, anticipo, cuotas: misma regex que la señal de revisión de
`costos.yaml`) y "en pozo" (ya es de descarte en la regla, nunca candidato); hotel, hostel y apart hotel cuentan como
uso no residencial. Campo `exclusiones` de `avisos.json`, calculado en el exportador; no toca las 1.375 señales, los
840 candidatos ni los 83 firmes. Con todas las reglas: 327 señales con alguna alerta, 486 destacados
(38 firmes). Esos
avisos siguen en el mapa y el buscador con la alerta. No existe una marca de "brecha extrema" en el pipeline. El
embudo está solo en Resumen; en Tendencias va el error del modelo por barrio. El simulador reproduce en JS la regla
de `src/regla.py` y da exactamente los mismos conteos que `sensibilidad`. Desde el 05/11 el exportador reproduce la
segmentación del 06 (`segmento_por_aviso`, misma semilla) y cada aviso lleva su `segmento`; en "Familiares amplios
y antiguos" la tabla y la ficha muestran una alerta de revisión (chip `chip-revisar`), descriptiva: no excluye.

## 6. Resultados actuales (para no recalcular de memoria; verificá contra los datos si los usás)

- Error mediano fuera de muestra: mediana de la zona 17,5%; lineal 12,7%; lineal ampliado 12,5%; Ridge 12,5%;
  gradient boosting 11,3%. Marcados: lineal ampliado 1.819, GBM 1.447. Jaccard entre ambos 0,52; consenso
  1.124 (números del 02/11, después de la regla de duplicados; antes: 1.800, 1.456 y 1.112). Números de la Mac de referencia: el GBM varía entre plataformas (en claude.ai daba 1.442 y 1.109; ver
  `docs/pipeline.md`, sección 10). La lista oficial no depende del GBM.
- SHAP del GBM (04, sección 9; 2.144 avisos marcados por alguno de los dos modelos): la ubicación es el 47% de la
  importancia, amenities y cochera 18%, antigüedad 14%, tamaño 12%. Orden estable entre vueltas (Spearman ≥ 0,98).
  Es aproximado: frente a un fondo de 200 y 1.000 evaluaciones, el top 3 coincide en el 82% de los avisos.
  El TreeExplainer de shap da valores errados con la categórica nativa de barrio: por eso, permutación.
- Intervalo 80%: ancho mediano 64,9%, o sea alrededor de ±32%.
- Primas por estado (bootstrap por unidad): "a refaccionar" −16,1%, "a reciclar" −17,7% (con la regex vieja daba −8%:
  la regex vieja agarraba "refaccionado").
- **Embudo oficial** (`embudo_ranking.csv`): 27.578 avisos / 25.169 unidades analizados → 1.819 / 1.714 marcados
  (brecha < −25%) → 1.556 / 1.470 también bajo el umbral de su barrio → **1.455 avisos / 1.375 unidades sin
  señales de error de carga = lista oficial (señales a investigar)** → **884 avisos / 840 unidades candidatos
  después de costos** (brecha neta ≥ +10% y sin riesgo legal de descarte).
- **Regla de decisión** (notebook 07, `src/regla.py`, aprobada el 02/11): se compra al publicado, se vende a precio
  de cierre (−4,79%), con costos de entrada (Sellos con umbral), refacción según `estado_titulo` (sin la prima de
  estado al refaccionar: "a reciclar" −19,8%, "a refaccionar" −16,6%) y costos de salida (bloque `costos_salida` de
  `costos.yaml`, supuestos con fuente; Ganancias 0 en la base, 15% y 35% en sensibilidad). Brecha neta mediana de
  las señales 12,3%; refacción integral −36% (casi nunca cierra). Sensibilidad (unidades candidatas): costos
  pesimistas 519, refacción alta 359, umbral +20% 358, Ganancias 35% 547, **límite inferior del 80% como salida:
  83**. Límite declarado: costo de tenencia (expensas y tiempo de venta) no incluido.
- **H3** (notebook 05): Wald de transporte p = 6e-5 y de entorno p = 2e-7 (agrupado por sub-zona), pero con Holm
  solo área verde (+1,5% por ha) y permisos de obra (+4,4% cada 10). El −24% del premetro es la zona: sin los avisos
  a menos de 500 m de un barrio popular pasa a −4% (IC incluye el 0, 9 avisos). "Sur y oeste" = comunas 4, 8, 9 y
  10 (elección del grupo). La ubicación baja el error fuera de muestra 0,19 pp.
- **H2** (notebook 05): la sub-zona baja el error mediano 0,60 pp (17,71% a 17,12%); con Holm mejoran 4 de 41
  barrios y ninguno empeora.
- **Segundo relevamiento (27 y 28/10/2026):** 27.516 avisos. Republicaciones detectadas por dirección + m² +
  ambientes (~24%). Se excluyen los barrios truncados por el tope de 2.016 resultados en el primer relevamiento
  (Palermo, Belgrano, Caballito, Recoleta). Los avisos marcados salen del portal 46,7% contra 39,7% (74 días entre
  relevamientos). Dentro del barrio, controlando log del valor esperado, log de m² y baja de precio previa:
  **+9,4 pp** (IC 6,5 a 12,3), logit OR 1,48 (notebook 05). Gradiente (principal, aprobado: brecha en log con dos
  pendientes): cada 10 pp más por debajo del esperado, +2,2 pp de salida (IC 1,6 a 2,8); con una sola pendiente,
  +2,1. Placebo (brecha > +33%): −8,4 pp. En el tercil de barrios medios el IC incluye el 0. H1a (colas) no se
  sostiene: la cola de abajo es más liviana que la de arriba (6,6% contra 7,7%). Ojo: controlar por el precio
  publicado es un mal control (borra el efecto porque la brecha está hecha de ese precio); el comparable correcto
  es el valor esperado. Esto le da a H1 y a P4 una evidencia que en la PE2 no tenían. Salir del portal no es lo
  mismo que venderse: puede ser venta, retiro o republicación no detectada.
- Costos (`config/costos.yaml`): brecha publicado-cierre 4,79% (mínimo 4,18%, UCEMA); entrada total ~8,8%; Sellos
  con umbral de USD 148.941 (2,7% total abajo, 3,5% arriba, mitad comprador); refacción integral con IVA
  1.227 USD/m² (rango 1.143 a 1.549); tiempo de venta solo por ambientes, no por zona.

## 7. Material de la cursada y decisiones abiertas

**Material:** en `_material_grupo/cursada/` (no versionado) están la consigna oficial de la PE3
(`consigna_pe3.txt`), la devolución de la PE2, el plan original del TP, las clases de visualización, tests de
hipótesis y MCA, y material de BI. **Empezá por `README_cursada.md`**: resume qué pide la consigna, los
criterios de visualización de la clase (para el dashboard) y lo que se vio de PCA, K-means y MCA. Cuando una
decisión de método o de gráfico tenga una versión "como lo vimos en clase", preferí esa, y si te apartás,
justificalo.

**Decisión abierta (preguntarle a Gonzalo antes del notebook 05):** el plan original de la materia esperaba
para esta etapa un índice sintético con PCA o MCA y una segmentación con K-means o DBSCAN ("micro-mercados"
con nombre), y el profe dio esas clases justo antes de la PE3. La consigna oficial dice que ninguna técnica es
obligatoria y que no se premia la cantidad. Hoy el TP no tiene ni índice ni segmentación de mercado. La idea a
proponerle (solo si responde a una pregunta del TP, no por sumar técnica):
- MCA sobre las características Sí/No (amenities) como índice, comparado contra usarlas sueltas en el modelo.
- K-means de micro-mercados por características (tamaño, antigüedad, índice, precio esperado), con codo y
  silhouette, nombres de negocio, estabilidad (ARI con bootstrap, como en la clase: > 0,8) y utilidad
  concreta: primas por segmento (G2), error del modelo y tasa de salida del segundo relevamiento por segmento
  (liquidez para la regla de decisión) y filtro del dashboard.

## 8. Pendientes, en orden

1. ~~Commit del orden del repo~~ (hecho el 30/10, 3c15710, pusheado).
2. ~~SHAP sobre el gradient boosting~~ (hecho el 30/10; falta que Gonzalo escriba las interpretaciones): sección nueva **al final** del 04, sin
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
4. ~~Regla de decisión~~ (hecha el 02/11; ver sección 6) (R1 con costos): brecha neta = brecha menos costos de entrada (con el umbral de Sellos),
   negociación y refacción según `estado_titulo`; liquidez con la tasa de salida del seguimiento por zona;
   riesgo legal como descarte o revisión. Análisis de sensibilidad. Mantener dos niveles: "señal a investigar"
   y "candidato después de costos", nunca "oportunidad confirmada".
5. ~~Dashboard HTML~~ (primera versión navegable el 03/11, diseño de Gonzalo: `docs/dashboard/`, HTML + CSS +
   JS plano + Leaflet, sin build; páginas Resumen, Mapa, Buscador, Tendencias con simulador y Cómo leer, más la
   ficha). Tercer nivel "candidato firme" (83) calculado en `src/exportar_dashboard.py`. En local:
   `cd docs/dashboard && python3 -m http.server 8765`. Revisado por Gonzalo el 03/11 (estética de informe, lista
   destacada con exclusiones, README con la justificación de la herramienta). Pages activo y linkeado desde el
   README el 04/11 (`docs/index.html` redirige la raíz al dashboard).
6. ~~Documentación~~ (hecho el 03/11: `docs/pipeline.md` con etapas 5 y 6 y scripts auxiliares, diccionario con
   todas las columnas de la PE3, README reescrito como borrador de la PE3 con la sección del dashboard y
   `run_pipeline.py`; interpretaciones del 07 completas; link de GitHub Pages en el README el 04/11).
7. **Revisión final:** correr todo de cero (etapas 5 y 6, notebooks, tests), revisar que los números coincidan
   en README, notebooks y dashboard, buscar rayas (`grep -rn "—"`), y una revisión independiente (un subagente
   que no haya hecho el trabajo).
8. **Para la entrega final (18/11):** revisar el sesgo del precio esperado en departamentos grandes y antiguos
   (segmento "Familiares amplios y antiguos" del 06: marca el 11,1% contra 5,2% a 6,5% en el resto, brecha mediana
   −3,1%; son 397 de las 1.375 señales, 170 de los 486 destacados y 19 de los 38 firmes); probar una interacción
   tamaño × antigüedad en el lineal ampliado. Desde el 05/11 el dashboard muestra una alerta de revisión en ese
   segmento (descriptiva, no excluye). También: calcular la estabilidad de las sub-zonas dentro de cada vuelta (hoy `analisis.py` la calcula una vez sobre todo el dataset). También: una sensibilidad de la regla con costo de tenencia (expensas e
   impuestos por los meses hasta la venta), porque hoy la liquidez no modifica la regla.

## 9. Errores conocidos y cuidados

- Sacar o agregar una sola fila cambia la asignación de las vueltas (factorización de grupos): si cambia el
  dataset limpio, los números de los notebooks 03 y 04 cambian y hay que actualizarlos en el texto.
- **La asignación de vueltas depende del orden de las filas**, no solo de la cantidad: `grupo_de_unidad` numera
  las unidades por orden de aparición y `folds_agrupados` permuta esos números. Cualquier cambio de orden en el
  dataset limpio (el 02/11, mover 17 filas por la regla de duplicados reasignó la vuelta de 9.941 avisos) mueve
  los números en el margen y puede cambiar qué barrios quedan inestables. Por eso `deduplicar_por_id` conserva la
  fila en la posición de la primera aparición. **Mejora para la entrega final (no implementada):** asignar las
  vueltas a partir de la clave de la unidad (por ejemplo, un hash de la dirección y los m²), para que no dependan
  del orden.
- Después de la etapa 5 hay que regenerar `seguimiento_avisos.csv` (`python3 src/seguimiento.py`): la etapa 6 y
  los notebooks 05 y 06 verifican que esté alineado con el dataset limpio.
- La estabilidad de sub-zonas cerca del umbral 0,7 depende de la semilla: presentarla como señal, no como
  clasificación exacta.
- La clave de republicación castea `ambientes` a float (antes no matcheaba nada por int contra str).
- `cantidad_de_pisos` a veces son plantas del depto y a veces pisos del edificio.
- Los avisos de "ideal renta" son publicidad, no inquilino: la regex de `con_inquilino` en `costos.yaml` los
  separa.
- El notebook 04 se generó con un script en la conversación de claude.ai que no está en el repo. A partir de
  ahora, la fuente es el propio `.ipynb`: editalo directamente.
