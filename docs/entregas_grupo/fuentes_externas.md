# Fuentes externas: fichas

*Analítica Descriptiva (ITBA, 2026 C2) · PreEntrega 2, actualizado en la PreEntrega 3*

Formato pedido por el enunciado de la PreEntrega 2: fuente concreta, cobertura
geográfica, período, granularidad, mecanismo de unión, variable derivada,
análisis/KPI/hipótesis al que aporta y limitaciones conocidas.

Estado: **integrada** (ya está en el dataset), **prevista** (compatible, todavía
no integrada) o **descartada** (se evaluó y no sirve para esta unidad de análisis).

Todos los datasets se verificaron en el portal el **05/10/2026** (el de barrios populares, el 06/10/2026). Las fuentes integradas en la PreEntrega 3 (fichas 4 a 7, 10 y 11) se descargaron el **27/10/2026** como snapshots en `data/external/`, con su SHA-256 en la ficha: `src/fuentes_externas.py` las lee sin red y escribe `data/processed/accesibilidad.tsv`. En cada ficha,
"Fuente concreta" lleva el link y el responsable, y "Período" lleva la fecha de
actualización que muestra el portal. Esa fecha indica que algo del recurso se
modificó, no que hayan cambiado los datos: en subte, por ejemplo, el portal marca un
cambio el 02/10/2026, pero el archivo publicado es idéntico a nuestro snapshot.

Unidad de análisis del proyecto: **el aviso de departamento usado en venta**,
comparado dentro de su **zona de referencia**. La zona es la sub-zona (cluster espacial
dentro del barrio, hasta 5 por barrio) en los 28 barrios donde mejora la referencia de
precio fuera de muestra, y el barrio completo en el resto (notebook 02, sección 4, y
notebook 03, sección 2). Las sub-zonas no tienen un tamaño mínimo garantizado: k se fija
en min(5, n // 30), pero KMeans no controla el tamaño de cada cluster, y 42 de las 198
tienen menos de 30 avisos. Por eso el modelo vuelve al barrio cuando una zona tiene menos
de 10 avisos y para los avisos sin coordenadas.
Cualquier fuente tiene que poder resolverse a nivel de punto (lat/lon), de parcela
o, como mínimo, de sub-zona. Una fuente agregada por comuna o por barrio no sirve
para explicar diferencias dentro de una sub-zona, porque toma el mismo valor para
todos los avisos que se comparan.

---

## 1. Normalizador de direcciones USIG (integrada)

| Campo | Detalle |
|---|---|
| Fuente concreta | Servicio de normalización y geocodificación de direcciones de USIG, GCBA (`servicios.usig.buenosaires.gob.ar/normalizar`), consultado con `geocodificar=true`. Verificado el 05/10/2026: responde y devuelve las coordenadas en SRID 4326, es decir, longitud y latitud WGS84 |
| Cobertura geográfica | CABA completa. El servicio cubre también el AMBA; el pipeline fuerza CABA agregando ", caba" a cada consulta |
| Período | Consultas hechas durante la corrida de geocodificación (septiembre 2026). El callejero es el vigente al momento de la consulta: repetir la corrida hoy puede dar resultados levemente distintos |
| Granularidad | Punto (calle y altura, o esquina). Es la fuente que ubica cada aviso, así que es compatible con la sub-zona por definición |
| Mecanismo de unión | Consulta 1 a 1 por dirección limpia (`dir_limpia`) del aviso. Se toma la primera dirección normalizada que devuelve el servicio |
| Variable derivada | `lat`, `lon`, `geo_status` |
| Aporta a | Todo el análisis espacial: sub-zonas, distancias, H2, H3 y la zona de referencia del modelo de precio esperado |
| Limitaciones | 17,9% de los avisos (5.010) sin coordenadas. **La pérdida no es aleatoria por barrio**: varía de 59,5% de éxito en Puerto Madero a 92,5% en Boedo (chi², p < 1e-100). Dentro de cada barrio, en cambio, los avisos perdidos casi no difieren en precio por m² ni en superficie. Las alturas redondeadas ("Esmeralda Al 900") ubican el punto en esa altura y no en el edificio: error de hasta una cuadra. La primera coincidencia no se coteja con el barrio del aviso. En el modelo, los avisos sin coordenadas se comparan contra su barrio. Detalle en `docs/correcciones_pe1/diagnostico.md` |

## 2. Estaciones de subte, BA Data (integrada)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Subte: Estaciones.", BA Data (responsable: SBASE), recurso GeoJSON. Snapshot versionado en `data/external/estaciones-de-subte.geojson`. Link: https://data.buenosaires.gob.ar/dataset/subte-estaciones |
| Cobertura geográfica | CABA, líneas A, B, C, D, E y H: 90 puntos, uno por estación y por línea (las combinaciones aparecen repetidas, como Retiro en la C y en la E). No incluye el Premetro, que BA Data publica en un dataset aparte |
| Período | Snapshot descargado el 14/09/2026, un mes después del scraping. El dataset declara actualización anual (última: 02/09/2026). Verificado el 05/10/2026: el archivo que publica hoy el portal es idéntico al snapshot (90 estaciones, ninguna diferencia) |
| Granularidad | Punto (estación), en WGS84. Compatible con la sub-zona: la distancia varía entre avisos de la misma sub-zona |
| Mecanismo de unión | Distancia haversine de cada aviso geocodificado a la estación más cercana. Las estaciones repetidas por combinación no afectan la mínima |
| Variable derivada | `dist_transporte_m` |
| Aporta a | H3 (efecto de la ubicación) e distancias de accesibilidad. **No entra al modelo de precio esperado:** en el notebook 02, dentro del barrio y a igual antigüedad, la cercanía al subte casi no se relaciona con el precio (H3 no se detectó con este indicador) |
| Limitaciones | Solo subte. Deja afuera tren y Metrobus, que son el transporte pesado en buena parte del sur y el oeste. Distancia en línea recta al punto de la estación, no a pie ni a la boca de acceso. No distingue líneas ni frecuencia |

## 3. Polos de centralidad (integrada, definición propia)

| Campo | Detalle |
|---|---|
| Fuente concreta | Coordenadas fijadas por el grupo en `config/config.yaml`: Obelisco, Puerto Madero, Catalinas |
| Cobertura geográfica | CABA |
| Período | No aplica (puntos fijos) |
| Granularidad | Punto. Compatible con la sub-zona, aunque dentro de una sub-zona la distancia al centro casi no varía: los avisos que se comparan están a pocas cuadras entre sí |
| Mecanismo de unión | Distancia haversine mínima a cualquiera de los tres polos |
| Variable derivada | `dist_centralidad_m` |
| Aporta a | H3, que no se detectó con este indicador: dentro del barrio la distancia a los polos no se relaciona con el precio (ρ ≈ 0, notebook 02). No entra al modelo de precio esperado |
| Limitaciones | Es una elección del grupo, no un dato externo, y hay que presentarla como tal. Hallazgo de la PreEntrega 1: correlación casi nula con el precio por m², porque el valor está en el corredor norte y no en el centro geográfico |

## 4. Estaciones de ferrocarril, BA Data (integrada en PE3)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Estaciones de Ferrocarril.", BA Data (responsable: Ministerio de Desarrollo Urbano y Transporte, Secretaría de Transporte), recurso GeoJSON. Link: https://data.buenosaires.gob.ar/dataset/estaciones-ferrocarril. Snapshot en `data/external/estaciones-ferrocarril.geojson`, descargado el 27/10/2026 (SHA-256 `aaec67421815b952aa1a09bb55d3403f700b93da7965616c72575666a2bba4ca`, 97.153 bytes) |
| Cobertura geográfica | **Toda la red metropolitana**, aunque la descripción diga "de la Ciudad": 301 estaciones, 43 en CABA (las únicas con `barrio` y `comuna`) y 258 en la provincia, hasta Luján, Cañuelas y La Plata. Ocho líneas (Mitre, Sarmiento, Roca, San Martín, Urquiza, Belgrano Norte, Belgrano Sur y Tren de la Costa) |
| Período | Última actualización del recurso en el portal: 02/10/2026 (frecuencia trimestral). El snapshot congela ese estado |
| Granularidad | Punto (estación, una por línea: Retiro figura tres veces), en WGS84. Compatible con la sub-zona: la distancia varía entre avisos de la misma sub-zona |
| Mecanismo de unión | Haversine de cada aviso geocodificado a la estación más cercana, igual que el subte, **sin filtrar por CABA**: para 403 avisos la estación más cercana está en la provincia (Aristóbulo del Valle para Saavedra y Núñez, Sáenz Peña para Devoto, Villa Madero para Mataderos y Lugano). Con solo estaciones de CABA esos avisos quedarían una mediana de 256 m más lejos, y hasta 903 m. El archivo no trae un campo de estado: se excluye por nombre la única estación cerrada ("Ex-estación La Salada", regex `^Ex-estaci` en `config.yaml`), que de todos modos no era la más cercana de ningún aviso |
| Variable derivada | `dist_tren_m`; entra en `dist_riel_m` y en `dist_transporte_pesado_m` |
| Aporta a | H3 e distancias de accesibilidad. Corrige el sesgo del subte en el sur y el oeste: la mediana de distancia a riel baja 77% en Liniers y 83% en Villa Luro respecto de solo subte (ver `control_fuentes.md`) |
| Limitaciones | Sin frecuencias ni cantidad de pasajeros: una estación del Belgrano Sur pesa igual que una del Mitre. Distancia en línea recta al punto de la estación. La cercanía al tren puede tener efecto negativo (ruido, barrera urbana): el signo no se puede asumir. Haversine supone una Tierra esférica: contra la distancia geodésica sobre el elipsoide WGS84, el error máximo es de 0,24% (1,2 m a 500 m) |

## 5. Metrobus, BA Data (integrada en PE3)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Metrobus", BA Data (responsable: Secretaría de Transporte y Obras Públicas, Jefatura de Gabinete), recurso "Estaciones de Metrobus (GeoJSON)". Link: https://data.buenosaires.gob.ar/dataset/metrobus. Snapshot en `data/external/estaciones-metrobus.geojson`, descargado el 27/10/2026 (SHA-256 `3f5089da238f1991d4a163e6022d36731ff8b9e241c3ea81f453a0f26eba2359`, 191.887 bytes) |
| Cobertura geográfica | Corredores de Metrobus en CABA: Cabildo, Juan B. Justo, Paseo Colón y Alem (Metrobus del Bajo), 9 de Julio, Sur (Fernández de la Cruz, Roca, Rabanal), San Martín y Alberdi, entre otros. 390 paradas en 35 barrios |
| Período | Última actualización del recurso en el portal: 23/06/2026 (frecuencia eventual) |
| Granularidad | Punto: cada registro es una parada **por sentido**, en WGS84, con barrio, comuna y las líneas de colectivo que paran. Hay 139 nombres de parada distintos y 38 paradas sin nombre. Compatible con la sub-zona |
| Mecanismo de unión | Haversine a la parada más cercana. Las paradas repetidas por sentido no afectan la mínima |
| Variable derivada | `dist_metrobus_m`; entra en `dist_transporte_pesado_m` pero **no** en `dist_riel_m` |
| Aporta a | H3. Se dejó como variable propia además de sumarla al transporte pesado, porque la ficha de la PE2 advertía que su efecto no es comparable con el del subte. Los datos lo confirman: es el transporte más cercano para el 29,7% de los avisos y su distancia casi no se correlaciona con la del riel (Spearman −0,08). El sábado se puede probar H3 con cada definición |
| Limitaciones | Es transporte de superficie. Estar sobre un corredor también puede significar estar sobre una avenida ruidosa. El campo `BARRIO` trae errores de tipeo ("VELEZ SARFIELD"), pero no se usa |

## 6. Espacios verdes, BA Data (integrada en PE3)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Espacios Verdes", BA Data (responsable: Gerencia Operativa de Explotación de Datos Geoespaciales, Jefatura de Gabinete), recurso "Espacios Verdes Públicos (GEOJSON)". Link: https://data.buenosaires.gob.ar/dataset/espacios-verdes. Snapshot en `data/external/espacios-verdes-publicos.geojson`, descargado el 27/10/2026 (SHA-256 `eb848cf853e6c6f65309fd78bd2688bae032ed88c074eb5a534aee91885eb728`, 18.399.297 bytes) |
| Cobertura geográfica | CABA: 2.176 polígonos públicos (1.361 multipolígonos). Los privados, catastrales e históricos vienen en otros recursos del dataset y no se usan |
| Período | **El recurso GeoJSON que se usa tiene último cambio el 19/08/2025**, verificado en el portal el 28/10/2026. El dataset figura actualizado el 06/07/2026 (frecuencia semestral), pero esa actualización no tocó este recurso, así que el snapshot refleja el estado de agosto de 2025: un parque inaugurado después no está |
| Granularidad | Polígono, con clase (`clasificac`) y área. Compatible con la sub-zona: la distancia al borde varía entre avisos cercanos |
| Mecanismo de unión | Proyección a UTM 21S (EPSG:32721), cuyo error de escala en CABA es de 0,02%. Se reparan 25 geometrías inválidas con `make_valid`. **Distancia**: al borde del polígono más cercano, 0 si el aviso cae adentro, contando solo plazas, parques, jardines, el jardín botánico y los parques semipúblicos, que incluyen la Reserva Ecológica (485 polígonos). **Área**: intersección de un círculo de 500 m alrededor del aviso con todos los polígonos salvo los canteros centrales y la franja de la General Paz (1.420 polígonos), disueltos antes para no contar dos veces las superposiciones. Se mide el verde dentro del círculo, no el área entera de los parques que lo tocan. Las clases y el radio están en `config.yaml` |
| Criterio de clases | Quedan afuera de la distancia los 755 canteros centrales, las 906 plazoletas (el 57% mide menos de 500 m²), los patios, los paseos y un complejo habitacional. Cada criterio cambia mucho la variable: la mediana de distancia es 158 m con todos los polígonos, 182 m sin canteros, 275 m sin canteros ni plazoletas y 285 m con el criterio elegido (tabla en `control_fuentes.md`). La franja de la General Paz (id 652) es una "plazoleta" de 104 ha que bordea la avenida: incluida, sumaría verde a 557 avisos de Saavedra, Núñez, Liniers, Devoto y el resto del borde oeste. El "Parque Gral. Paz" de Saavedra (id 937) es un parque real y queda |
| Variable derivada | `dist_espacio_verde_m`, `area_verde_500m_ha` |
| Aporta a | H3 (pregunta de diagnóstico "efecto infraestructura" del enunciado general). La distancia mide acceso a una plaza; el área distingue una plaza chica de un parque |
| Limitaciones | La calidad, el estado y la seguridad del espacio verde no están en el dataset. La clase la asigna la Ciudad y no siempre coincide con el uso: hay plazoletas de más de 4 ha. Los parques semipúblicos tienen horario |

## 7. Polígonos de barrios, BA Data (integrada en PE3, para control de calidad)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Barrios", BA Data (responsable: Gerencia Operativa de Explotación de Datos Geoespaciales, Jefatura de Gabinete), recurso "Barrios (GeoJSON)" con nombre, comuna, perímetro y área de cada barrio. Link: https://data.buenosaires.gob.ar/dataset/barrios. Snapshot en `data/external/barrios.geojson`, descargado el 27/10/2026 (SHA-256 `c24fabd01c61b889388f0a8cfd9ca4757c1f57583c0ffd1b4ed3b96d768bb655`, 763.670 bytes) |
| Cobertura geográfica | Los 48 barrios oficiales de CABA (204 km² en total) |
| Período | Última actualización del recurso GeoJSON en el portal: 29/07/2026 (frecuencia trimestral), verificada el 28/10/2026 |
| Granularidad | Polígono (barrio). Más grande que la sub-zona, así que no sirve para explicar precios dentro de ella; su uso es de control |
| Mecanismo de unión | Punto en polígono en UTM 21S. Los 22.912 avisos geocodificados caen en exactamente un barrio: ninguno queda afuera ni en dos a la vez |
| Variable derivada | `barrio_oficial`, `barrio_coincide` |
| Regla de `barrio_coincide` | 1 si el barrio de búsqueda de MercadoLibre coincide con el oficial. Se comparan los nombres normalizados: mayúsculas, sin tildes, sin guiones ni puntos, y "Gral." expandido a "General" para que `villa-general-mitre` coincida con "Villa Gral. Mitre". **Barrio Norte**, que no es un barrio oficial, se toma como coincidente si cae en Recoleta, Retiro o Palermo. La equivalencia está en `config.yaml` (`equivalencias_barrio`) |
| Aporta a | Evaluación de calidad y control de los duplicados con discrepancia territorial. El 81,6% de los avisos geocodificados coincide (el 2,2% gracias a la equivalencia de Barrio Norte). Las discrepancias más grandes son de borde: "belgrano" en Palermo (253), "recoleta" en Retiro (227). Aparecen 100 avisos en San Cristóbal y 39 en Parque Chas, los dos barrios que el scraping no buscaba |
| Limitaciones | Solo para los geocodificados (82,1%). Una discrepancia no siempre es un error: el 94% de las discrepancias está a menos de 1 km del barrio buscado (avisos de borde). Pero 249 avisos quedan a más de 1 km, y en 246 la dirección nombra el barrio buscado: son errores de geocodificación por calles homónimas. Por ejemplo, "Arroyo 800, Retiro" quedó en Villa Crespo, "Madero 100, Liniers" en San Nicolás y "Beruti 4400, Palermo" en Nueva Pompeya. Esos 246 avisos tienen mal todas las variables espaciales, también las de la PE2 (`control_fuentes.md`, sección 4) |

## 8. Tipo de cambio: dólar MEP (integrada)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dólar MEP, cierre del 14/08/2026: ARS 1.518,05 por USD (Ámbito, "Dólar hoy: a cuánto cerró este viernes 14 de agosto"). Como referencia se registra el tipo de cambio de referencia Com. "A" 3500 del BCRA del mismo día: ARS 1.488,70. Fuentes completas en `docs/entregas_grupo/contexto_argentino.md` |
| Cobertura geográfica | Nacional |
| Período | Un valor: 14/08/2026, fecha de extracción del scraping |
| Granularidad | Un único valor para todos los avisos. No necesita variar entre avisos: es una conversión de unidades, no una variable explicativa |
| Mecanismo de unión | Se aplica el mismo valor a todos los avisos en el notebook 01 (`PARAMS`) |
| Variable derivada | `expensas_ars` (las publicadas en USD pasadas a pesos) y `expensas_usd` (todas las expensas en dólares) |
| Aporta a | KPI "eficiencia de expensas", calculado en el notebook 03 (sección 11). El enunciado exige declarar fuente, tipo de cambio, fecha y criterio para toda normalización monetaria |
| Criterio | Se eligió el MEP porque el comprador paga el departamento con dólares propios y las expensas en pesos: el MEP es el tipo de cambio al que una persona convierte legalmente dólares a pesos. El A 3500 es mayorista y un comprador no accede a él |
| Limitaciones | La elección pesa poco: la brecha entre los dos era de 2%, y la mediana de expensas pasa de USD 131,7 (MEP) a USD 134,3 (A 3500). Como se aplica un solo valor a todos, **no cambia el orden de los avisos dentro de una zona**. Los 5 avisos con precio en pesos no se convierten: se excluyen en la limpieza (`precio_en_pesos`), porque sus montos no cierran como pesos |

## 9. Permisos de obra: Obras Registradas, BA Data (calculada, a unir al dataset de trabajo)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Obras Registradas", BA Data (responsable: Dirección General Registro de Obras y Catastro, Jefatura de Gabinete), recurso CSV. Link: https://data.buenosaires.gob.ar/dataset/obras-registradas. Snapshot versionado en `data/external/obras-registradas.csv`, **descargado el 29/10/2026** (SHA256 `6106c48d…`). El archivo viene separado por `;`, con BOM y fin de línea CRLF |
| Cobertura geográfica | CABA (48 barrios oficiales en el campo `barrio`) |
| Período | El snapshot tiene 87.784 registros entre el 29/09/2020 y el 02/09/2026. La fecha está en formato día/mes/año y se lee con `format="%d/%m/%Y %H:%M"` (ninguna queda vacía). **Ventana usada: 3 años antes del scraping, del 14/08/2023 al 13/08/2026.** Se descartan los 1.076 registros posteriores al 14/08/2026, que no se conocían al publicarse el aviso |
| Por qué 3 años | (1) El registro empieza a fines de 2020 (918 registros ese año), así que 5 años no entran. (2) **En 2021-2022 cambió el nombre del trámite**: "Registro-permiso obra" tiene 3.698 registros en 2021 y casi desaparece desde 2022, cuando aparece "Permiso de ejecución de obra civil" (1.003 en 2022, ~1.000 por año desde entonces). Con 3 años la ventana cae entera en la nomenclatura nueva y no mezcla dos sistemas. (3) Tres años es del orden de lo que tarda una obra en terminarse: lo que se permisó en la ventana está en obra o recién terminado cuando se publica el aviso |
| Granularidad | Punto a nivel de parcela, con coordenadas en el 100% de los registros. Se usa `wkt_2` (WGS84, `POINT(lon lat)`); `wkt_1` es el mismo punto en coordenadas planas de la Ciudad. Compatible con la sub-zona |
| Filtro de tipos | Solo trámites de obra nueva o ampliación mayor: "Permiso de ejecución de obra civil" (3.371 en la ventana), "Permiso temprano de ejecución de obra civil" (325) y, con muy pocos casos en la ventana, "Demolición total y obra", "Permiso de obra mayor", "Registro-permiso obra" y "Obra nueva". Quedan afuera instalaciones (ventilación, incendio, ascensores, eléctricas), demoliciones sueltas, regularizaciones, planos de propiedad horizontal y "P. obra e. proy. / conforme / r. obras en contra", que mezcla trámites distintos |
| Mecanismo de unión | **Se cuenta cada obra una sola vez.** Una obra suele tener varios trámites (el permiso temprano y después el de ejecución) y algunas ocupan varias parcelas con el mismo punto y el mismo expediente: se deduplica primero por parcela (`smp`) y después por punto (`wkt_2`). Los 3.719 trámites de la ventana son 1.869 parcelas y 1.795 obras. Para cada aviso geocodificado, distancia haversine (`haversine_np` de `src/enriquecimiento.py`) a cada obra y conteo de las que están a menos de 500 m. Parámetros en `config/config.yaml` (sección `permisos_obra`). Módulo: `src/permisos_obra.py`, corre sin red en ~4 segundos |
| Variable derivada | `permisos_obra_500m`, en `data/processed/permisos_obra.tsv` (clave `link`, 27.922 filas, una por aviso del dataset enriquecido; vacía en los 5.010 avisos sin coordenadas). **`m2_obra_500m` no se calcula: el dataset no trae superficie autorizada** (sus columnas son `wkt_1`, `wkt_2`, `id_registr`, `expediente`, `fecha`, `smp`, `ubicacion`, `acronimo`, `descripcio`, `barrio`, `comuna`) |
| Aporta a | Línea de "dinamismo de zona": control del modelo de precio esperado y lectura de liquidez en la regla de decisión |
| Limitaciones | Mide permisos, no obra ejecutada ni valorización. Cuenta obras, no unidades: un edificio de 40 departamentos pesa igual que una casa ampliada. El radio de 500 m es en línea recta y no respeta barreras (vías, autopistas, el Riachuelo). La duda de la versión anterior de esta ficha queda resuelta: "Demolición" y "Regularización de obra en contravención Ley 6478" tienen los dos 2.705 registros en el archivo completo. Es una coincidencia real, no un error de copia. El campo `expediente` está vacío en 4.753 registros, por eso se deduplica por parcela y no por expediente |

**Distribución de `permisos_obra_500m` por barrio** (obras con permiso a menos de 500 m del aviso; barrios ordenados por mediana):

| Barrio (búsqueda de MercadoLibre) | Avisos geocodificados | Mediana | P25 – P75 | % con 0 |
|---|---:|---:|---:|---:|
| Núñez | 737 | 25 | 20 – 28 | 0,0 |
| Villa Ortúzar | 183 | 20 | 16 – 22 | 0,0 |
| Colegiales | 495 | 19 | 16 – 21 | 0,0 |
| Chacarita | 193 | 19 | 17 – 21 | 0,0 |
| Saavedra | 371 | 17 | 13 – 23 | 0,0 |
| Palermo | 1.704 | 16 | 11 – 21 | 0,0 |
| Villa Urquiza | 945 | 16 | 13 – 18 | 0,0 |
| Belgrano | 1.637 | 14 | 11 – 17 | 0,0 |
| Villa Crespo | 858 | 14 | 12 – 19 | 0,2 |
| Villa Devoto | 547 | 14 | 10 – 20 | 0,0 |
| Villa Luro | 310 | 13 | 9 – 15 | 0,3 |
| Villa Santa Rita | 100 | 13 | 10 – 16 | 0,0 |
| Villa del Parque | 495 | 12 | 9 – 16 | 0,0 |
| Caballito | 1.612 | 10 | 6 – 12 | 0,1 |
| Liniers | 286 | 10 | 5 – 14 | 4,2 |
| Villa Pueyrredón | 201 | 10 | 8 – 13 | 0,0 |
| Almagro | 1.373 | 9 | 6 – 11 | 0,0 |
| Coghlan | 151 | 9 | 7 – 17 | 0,0 |
| Paternal | 116 | 9 | 6 – 11 | 0,0 |
| Flores | 1.044 | 8 | 6 – 10 | 0,1 |
| Barrio Norte | 629 | 8 | 6 – 11 | 0,0 |
| San Telmo | 540 | 8 | 7 – 10 | 0,0 |
| Villa Real | 12 | 8 | 7 – 10 | 0,0 |
| Monserrat | 582 | 7 | 6 – 8 | 0,0 |
| Boedo | 393 | 7 | 4 – 10 | 3,3 |
| Monte Castro | 173 | 7 | 6 – 11 | 0,0 |
| Agronomía | 44 | 7 | 4 – 9 | 0,0 |
| Recoleta | 1.669 | 6 | 5 – 9 | 0,4 |
| Balvanera | 1.425 | 6 | 5 – 7 | 0,1 |
| Floresta | 284 | 6 | 4 – 9 | 0,4 |
| Mataderos | 209 | 6 | 5 – 8 | 0,0 |
| Villa General Mitre | 85 | 6 | 5 – 9 | 2,4 |
| San Nicolás | 693 | 5 | 3 – 6 | 0,3 |
| Constitución | 246 | 5 | 3 – 7 | 0,0 |
| Versalles | 56 | 5 | 3 – 8 | 0,0 |
| Vélez Sarsfield | 64 | 4 | 4 – 6 | 0,0 |
| Retiro | 580 | 4 | 3 – 5 | 1,7 |
| Parque Chacabuco | 273 | 4 | 2 – 7 | 8,4 |
| Parque Avellaneda | 84 | 4 | 1 – 7 | 19,0 |
| Barracas | 375 | 3 | 2 – 5 | 12,5 |
| Parque Patricios | 166 | 3 | 2 – 5 | 0,6 |
| Villa Riachuelo | 11 | 3 | 2 – 4 | 18,2 |
| Puerto Madero | 450 | 2 | 1 – 2 | 0,4 |
| La Boca | 172 | 2 | 1 – 2 | 1,2 |
| Nueva Pompeya | 34 | 1 | 0 – 2 | 32,4 |
| Villa Soldati | 32 | 1 | 1 – 1 | 18,8 |
| Villa Lugano | 273 | 0 | 0 – 3 | 51,3 |
| **CABA** | **22.912** | **9** | **5 – 14** | **1,3** |

El patrón es el esperado: el máximo está en el corredor norte en expansión (Núñez,
Villa Ortúzar, Chacarita, Colegiales, Saavedra) y el mínimo en el sur (Villa Lugano,
con la mitad de sus avisos sin ninguna obra cerca, Villa Soldati y Nueva Pompeya).
Puerto Madero y La Boca también dan bajo, probablemente porque el primero ya está casi completo y el segundo tiene poca obra privada nueva.

## 10. Barrios populares, BA Data (integrada en PE3)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Barrios Populares", BA Data (responsable: Ministerio de Desarrollo Humano y Hábitat), recurso "Barrios populares - Polígono (GEOJSON)". Link: https://data.buenosaires.gob.ar/dataset/barrios-populares. Snapshot en `data/external/barrios-populares.geojson`, descargado el 27/10/2026 (SHA-256 `b26493c38ada0b30a998fa5afb6846cdd7f9cfd2ab731335a5217aadd774745e`, 251.678 bytes) |
| Cobertura geográfica | CABA: 132 polígonos. Tipos: 52 barrios municipales, 39 asentamientos precarios, 20 conjuntos habitacionales, 14 villas, 5 barrios urbanizados y 2 núcleos habitacionales transitorios. **Incluye Rodrigo Bueno**, con dos polígonos (asentamiento y barrio urbanizado), igual que el Playón de Chacarita |
| Período | Última actualización del recurso en el portal: 02/10/2026 (frecuencia trimestral) |
| Granularidad | Polígono. Más chico que un barrio oficial: puede separar una zona de precios muy distintos dentro de un barrio |
| Mecanismo de unión | Punto en polígono en UTM 21S. Si un punto cae en dos polígonos superpuestos, se informa el tipo más informal (orden de prioridad en `config.yaml`); en este dataset no pasó con ningún aviso |
| Variable derivada | `en_barrio_popular` (1 o 0, con todos los tipos), `tipo_barrio_popular` |
| Aporta a | Modelo de precio esperado, como control de ubicación. De los 96 avisos que caen en un barrio popular, 76 son barrios municipales, sobre todo Lugano I y II (38) y Piedrabuena (20), que son conjuntos de vivienda social. Villas propiamente dichas hay 11 (Padre Mugica, en Retiro). Por eso el tipo va en una columna aparte: el modelo probablemente use solo villas y asentamientos |
| Limitaciones | Solo sirve para los geocodificados (82,1%). **No detecta el caso que motivó la fuente**: el aviso de Rodrigo Bueno del ranking (Simone de Beauvoir 1100) no tiene coordenadas, igual que el otro aviso que lo menciona. Esos avisos se marcan por el título en la limpieza, junto con las otras marcas |

## 11. Estaciones de premetro, BA Data (integrada en PE3)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Premetro.", BA Data (responsable: SBASE), recurso "Estaciones Premetro (GEOJSON)". Link: https://data.buenosaires.gob.ar/dataset/premetro. Snapshot en `data/external/estaciones-premetro.geojson`, descargado el 28/10/2026 (SHA-256 `5ff83fedbf44550184480721914c0a36d10a2b072359309e8699fc0e89ebceb8`, 7.600 bytes) |
| Cobertura geográfica | 18 estaciones en el sur de CABA: 8 en Villa Soldati, 7 en Villa Lugano, 2 en Flores y 1 en Villa Riachuelo. Dos ramales desde Intendente Saguier: a General Savio y a Centro Cívico Lugano. Las 18 caen en el barrio oficial que declara el propio archivo |
| Período | Última actualización del recurso en el portal: 28/10/2026, el mismo día de la descarga. **En servicio durante el scraping**: la Ciudad propuso reemplazarlo por un trambús en diciembre de 2025 y dejó ese proyecto en suspenso en enero de 2026 |
| Granularidad | Punto (estación). Compatible con la sub-zona |
| Mecanismo de unión | **A diferencia de las otras fuentes, el archivo viene en POSGAR 2007 / CABA 2019 (EPSG:9498), en metros, no en longitud y latitud.** El módulo lee el sistema de coordenadas que declara cada GeoJSON y lo reproyecta a WGS84; si un archivo de puntos no lo declarara y trajera metros, corta con un error en lugar de calcular distancias absurdas. Después, haversine a la estación más cercana, igual que subte y tren. El subte no lo incluye: `dist_transporte_m` usa solo las líneas A a H |
| Variable derivada | `dist_premetro_m`; entra en `dist_riel_m` y en `dist_transporte_pesado_m` |
| Aporta a | H3. Cubre justo Soldati y Lugano: es el riel más cercano para 206 avisos (86 en Villa Lugano, 35 en Villa Riachuelo, 31 en Villa Soldati). En Villa Lugano baja la mediana de distancia a riel de 1.290 m a 631 m, y en Villa Riachuelo de 1.271 m a 962 m |
| Limitaciones | Es un tranvía de baja capacidad: según Wikipedia, 1.593 pasajeros diarios en 2024. En 2026 tiene obras en curso. Pesa igual que una estación de subte en `dist_riel_m`, y el sábado conviene revisar si eso se sostiene |

## Descartadas o a descartar

- **Datos agregados por comuna**, como la superficie de espacios verdes por habitante
  por comuna que publica BA Data: la comuna agrupa varios barrios (hasta seis) y el análisis compara
  dentro de la sub-zona. Pueden servir solo como contexto descriptivo, no para
  explicar precios.
- **Alquileres (scraping propio)**: permitirían estimar rentabilidad bruta por zona,
  un ancla económica externa al modelo de precio esperado. Queda como próximo paso por
  costo de tiempo (8 a 15 h de scraping más geocodificación).
