# Fuentes externas: fichas

*TP2, Analítica Descriptiva (ITBA, 2026 C2) · PreEntrega 2*

Formato pedido por el enunciado de la PreEntrega 2: fuente concreta, cobertura
geográfica, período, granularidad, mecanismo de unión, variable derivada,
análisis/KPI/hipótesis al que aporta y limitaciones conocidas.

Estado: **integrada** (ya está en el dataset), **prevista** (compatible, todavía
no integrada) o **descartada** (se evaluó y no sirve para esta unidad de análisis).

Todos los datasets se verificaron en el portal el **05/10/2026** (el de barrios populares, el 06/10/2026). En cada ficha,
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
| Aporta a | H3 (efecto de la ubicación) e índice de accesibilidad. **No entra al modelo de precio esperado:** en el notebook 02, dentro del barrio y a igual antigüedad, la cercanía al subte casi no se relaciona con el precio (H3 no se apoya) |
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
| Aporta a | H3, que no se apoyó: dentro del barrio la distancia a los polos no se relaciona con el precio (ρ ≈ 0, notebook 02). No entra al modelo de precio esperado |
| Limitaciones | Es una elección del grupo, no un dato externo, y hay que presentarla como tal. Hallazgo del TP1: correlación casi nula con el precio por m², porque el valor está en el corredor norte y no en el centro geográfico |

## 4. Estaciones de ferrocarril, BA Data (prevista)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Estaciones de Ferrocarril.", BA Data (responsable: Ministerio de Desarrollo Urbano y Transporte, Secretaría de Transporte), recurso GeoJSON (también CSV y SHP). Link: https://data.buenosaires.gob.ar/dataset/estaciones-ferrocarril |
| Cobertura geográfica | **Toda la red metropolitana, no solo CABA**, aunque la descripción diga "de la Ciudad". En la vista previa, solo los primeros 43 registros tienen barrio porteño; el resto son estaciones del conurbano y más lejos (La Plata, Luján, Cañuelas) |
| Período | Última actualización del portal: 02/09/2026 (frecuencia trimestral). A registrar la fecha al descargar y guardar el archivo en `data/external/`, igual que el de subte |
| Granularidad | Punto (estación, una por línea: Retiro figura tres veces), en WGS84. Compatible con la sub-zona |
| Mecanismo de unión | Igual que subte: haversine a la estación más cercana, **sin filtrar por CABA**, porque para un aviso junto a la General Paz o el Riachuelo la estación más cercana puede estar en la provincia. Se puede combinar con subte en una sola `dist_transporte_pesado_m` |
| Variable derivada | `dist_tren_m`, `dist_transporte_pesado_m` |
| Aporta a | H3. Corrige el sesgo del subte, que casi no cubre el sur y el oeste: permitiría ver si el resultado negativo de H3 cambia en esas zonas |
| Limitaciones | Sin frecuencias. La cercanía al tren puede tener efecto negativo (ruido, barrera urbana): el signo no se puede asumir. El recurso con el trazado de las vías tiene último cambio en 2022; las estaciones, en 2026 |

## 5. Metrobus, BA Data (prevista)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Metrobus", BA Data (responsable: Secretaría de Transporte y Obras Públicas, Jefatura de Gabinete): estaciones y recorridos (GeoJSON, CSV, SHP). Link: https://data.buenosaires.gob.ar/dataset/metrobus |
| Cobertura geográfica | Corredores de Metrobus en CABA |
| Período | Última actualización del portal: 23/06/2026 (frecuencia eventual). A registrar al descargar |
| Granularidad | Punto: cada registro es una parada **por sentido**, en WGS84 (EPSG:4326), con barrio, comuna y las líneas de colectivo que paran. El recorrido viene aparte, como línea. Compatible con la sub-zona |
| Mecanismo de unión | Haversine a la parada más cercana. Las paradas repetidas por sentido no afectan la mínima |
| Variable derivada | `dist_metrobus_m` |
| Aporta a | H3 |
| Limitaciones | Es transporte de superficie: su efecto sobre el precio no es comparable directamente con el del subte, así que conviene usarlo como variable separada y no sumarlo a `dist_transporte_pesado_m`. Estar sobre un corredor también puede significar estar sobre una avenida ruidosa |

## 6. Espacios verdes, BA Data (prevista)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Espacios Verdes", BA Data (responsable: Gerencia Operativa de Explotación de Datos Geoespaciales, Jefatura de Gabinete), recurso "Espacios Verdes Públicos" (GeoJSON, polígonos). Link: https://data.buenosaires.gob.ar/dataset/espacios-verdes |
| Cobertura geográfica | CABA: jardines, parques, patios recreativos, plazas, plazoletas, canteros y polideportivos. Los espacios verdes privados vienen en otro recurso del mismo dataset |
| Período | Última actualización del portal: 06/07/2026 (frecuencia semestral) |
| Granularidad | Polígono. Compatible con la sub-zona: la distancia al borde varía entre avisos cercanos |
| Mecanismo de unión | Distancia del aviso al borde del polígono más cercano, después de filtrar los que no son plazas (un cantero no es una plaza). El recurso trae un campo de clasificación (`clasificac`) además del área: **filtrar por tipo es más defendible que inventar un umbral de superficie**. Qué tipos cuentan es decisión del grupo. Para medir en metros hay que proyectar a un sistema métrico (por ejemplo UTM 21S, EPSG:32721) |
| Variable derivada | `dist_espacio_verde_m` |
| Aporta a | H3 (pregunta de diagnóstico "efecto infraestructura" del enunciado general) |
| Limitaciones | Requiere geopandas o shapely. La calidad y el estado del espacio verde no están en el dataset. Los campos de clasificación y área se vieron en el recurso SHP: confirmar que el GeoJSON trae los mismos |

## 7. Polígonos de barrios, BA Data (prevista, para control de calidad)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Barrios", BA Data (responsable: Gerencia Operativa de Explotación de Datos Geoespaciales, Jefatura de Gabinete), recurso GeoJSON con nombre, comuna, perímetro y área de cada barrio. Link: https://data.buenosaires.gob.ar/dataset/barrios |
| Cobertura geográfica | Los 48 barrios oficiales de CABA |
| Período | Última actualización del portal: 29/07/2026 (frecuencia trimestral) |
| Granularidad | Polígono (barrio). Más grande que la sub-zona, así que no sirve para explicar precios dentro de ella; su uso es de control |
| Mecanismo de unión | Punto en polígono con `lat`/`lon` |
| Variable derivada | `barrio_oficial`, `barrio_coincide` |
| Aporta a | Evaluación de calidad. El `barrio` del dataset no lo escribe el anunciante: es la categoría de búsqueda de MercadoLibre en la que apareció el aviso. Esa lista incluye "barrio-norte", que no es oficial, y no incluye San Cristóbal ni Parque Chas, que no están en las cuotas del scraping. El cruce permite medir cuántos avisos están mal asignados y en qué categoría quedaron los avisos de esos dos barrios |
| Limitaciones | Solo para los geocodificados (82,1%) |

## 8. Tipo de cambio: dólar MEP (integrada)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dólar MEP, cierre del 14/08/2026: ARS 1.518,05 por USD (Ámbito, "Dólar hoy: a cuánto cerró este viernes 14 de agosto"). Como referencia se registra el tipo de cambio de referencia Com. "A" 3500 del BCRA del mismo día: ARS 1.488,70. Fuentes completas en `docs/entregas_grupo/contexto_argentino.md` |
| Cobertura geográfica | Nacional |
| Período | Un valor: 14/08/2026, fecha de extracción del scraping |
| Granularidad | Un único valor para todos los avisos. No necesita variar entre avisos: es una conversión de unidades, no una variable explicativa |
| Mecanismo de unión | Se aplica el mismo valor a todos los avisos en el notebook 01 (`PARAMS`) |
| Variable derivada | `expensas_ars` (las publicadas en USD pasadas a pesos) y `expensas_usd` (todas las expensas en dólares) |
| Aporta a | KPI "eficiencia de expensas". El enunciado exige declarar fuente, tipo de cambio, fecha y criterio para toda normalización monetaria |
| Criterio | Se eligió el MEP porque el comprador paga el departamento con dólares propios y las expensas en pesos: el MEP es el tipo de cambio al que una persona convierte legalmente dólares a pesos. El A 3500 es mayorista y un comprador no accede a él |
| Limitaciones | La elección pesa poco: la brecha entre los dos era de 2%, y la mediana de expensas pasa de USD 131,7 (MEP) a USD 134,3 (A 3500). Como se aplica un solo valor a todos, **no cambia el orden de los avisos dentro de una zona**. Los 5 avisos con precio en pesos no se convierten: se excluyen en la limpieza (`precio_en_pesos`), porque sus montos no cierran como pesos |

## 9. Permisos de obra: Obras Registradas, BA Data (prevista, confirmada)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Obras Registradas", BA Data (responsable: Dirección General Registro de Obras y Catastro, Jefatura de Gabinete), recurso CSV (también XLSX, SHP y GeoJSON). Link: https://data.buenosaires.gob.ar/dataset/obras-registradas |
| Cobertura geográfica | CABA |
| Período | Última actualización del portal: 17/09/2026 (frecuencia mensual). El archivo descargado tiene 87.784 registros de 2020 a 2026. **La fecha viene en formato día/mes/año** ("7/9/2021 16:30" es el 7 de septiembre, verificado contra la vista previa del portal) y hay que leerla con `format="%d/%m/%Y %H:%M"`. Leída sin formato, pandas asume mes/día: invierte las fechas con día hasta 12 (así apareció una fecha imposible, el 08/12/2026, que casi seguro es el 12/08/2026) y deja vacías las que tienen día mayor que 12. Solo pueden usarse los registros anteriores al 14/08/2026, porque uno posterior no se conocía cuando se publicó el aviso |
| Granularidad | **Punto a nivel de parcela, con coordenadas en el 100% de los registros.** Cada registro trae el punto dos veces: `wkt_1` en coordenadas planas de la Ciudad y `wkt_2` en longitud y latitud WGS84 (el portal las describe como "punto de inicio" y "de destino", pero son el mismo punto). Trae también el código de parcela (`smp`), la dirección, el barrio y la comuna. Compatible con la sub-zona |
| Mecanismo de unión | Conteo de permisos de obra nueva en un radio alrededor de cada aviso (por ejemplo, 500 m) dentro de una ventana previa al scraping (por ejemplo, 24 meses), con `wkt_2`. Se prefiere el radio a contar "dentro de la sub-zona" porque la sub-zona no tiene límites definidos. Radio, ventana y tipos de trámite son decisión del grupo. Hay que deduplicar por expediente o por parcela, porque una misma obra puede tener varios trámites |
| Variable derivada | `permisos_obra_500m` (proxy de dinamismo) |
| Aporta a | La línea de "dinamismo de zona" planteada en el TP1 |
| Limitaciones | Mide actividad constructiva registrada, no valorización ni obra ejecutada. **Cerca de un tercio de los registros no son obras**: al menos 23.443 (26,7%) son proyectos de instalaciones (ventilación mecánica, prevención de incendios, ascensores, instalaciones térmicas y eléctricas) y 2.705 (3,1%) son regularizaciones de obras en contravención. Los trámites de obra propiamente dicha son "Permiso de ejecución de obra civil" (5.311) y "Registro-permiso obra" (4.198), en conjunto el 10,8%. Podrían ser el mismo trámite con dos nombres: en la vista previa del portal, el segundo aparece en registros de 2021 y el primero en 2023, a confirmar con el archivo completo. Las demoliciones también vienen con dos nombres, "Permiso de demolición" (5.308) y "Demolición" (2.705), que conviene contar juntos. El tipo más frecuente, "P. obra e. proy. / conforme / r. obras en contra" (22.604, 25,7%), mezcla trámites distintos y no se puede separar. Queda para la PreEntrega 3 |

## 10. Barrios populares, BA Data (prevista)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Barrios Populares", BA Data (responsable: Ministerio de Desarrollo Humano y Hábitat), recursos SHP, GeoJSON, CSV y XLSX. Link: https://data.buenosaires.gob.ar/dataset/barrios-populares |
| Cobertura geográfica | CABA |
| Período | Última actualización del portal: 02/10/2026 (frecuencia trimestral). Verificado el 06/10/2026 |
| Granularidad | Polígono (barrio popular y manzanas). Más chico que un barrio oficial: puede separar una zona de precios muy distintos dentro de un barrio |
| Mecanismo de unión | Punto en polígono con `lat`/`lon` |
| Variable derivada | `en_barrio_popular` (booleana) |
| Aporta a | Modelo de precio esperado, como control de ubicación. Surge de la revisión del ranking del notebook 03: un aviso real del barrio Rodrigo Bueno, dentro de Puerto Madero, quedó entre los primeros puestos porque el modelo lo compara con las torres del barrio |
| Limitaciones | Hay que confirmar al descargarlo que incluye Rodrigo Bueno y qué otros barrios cubre. Solo sirve para los avisos geocodificados (82,1%) |

## Descartadas o a descartar

- **Datos agregados por comuna**, como la superficie de espacios verdes por habitante
  por comuna que publica BA Data: la comuna agrupa 2 o 3 barrios y el análisis compara
  dentro de la sub-zona. Pueden servir solo como contexto descriptivo, no para
  explicar precios.
- **Alquileres (scraping propio)**: permitirían estimar rentabilidad bruta por zona,
  un ancla económica externa al modelo de precio esperado. Queda como próximo paso por
  costo de tiempo (8 a 15 h de scraping más geocodificación).
