# Fuentes externas: fichas (borrador para el README)

> **Borrador de trabajo del 29/09/2026.** La versión vigente, actualizada al dataset limpio y al modelo, está en `docs/entregas_grupo/fuentes_externas.md`.

Formato pedido por el enunciado de la PreEntrega 2: fuente concreta, cobertura
geográfica, período, granularidad, mecanismo de unión, variable derivada,
análisis/KPI/hipótesis al que aporta y limitaciones conocidas.

Estado: **integrada** (ya está en el dataset), **prevista** (compatible, todavía
no integrada) o **descartada** (se evaluó y no sirve para esta unidad de análisis).

Unidad de análisis del proyecto: **el aviso de departamento usado en venta**,
comparado dentro de su **sub-zona** (cluster espacial dentro del barrio, mínimo
30 avisos). Cualquier fuente tiene que poder resolverse a nivel de punto
(lat/lon) o, como mínimo, de sub-zona. Una fuente agregada por comuna o por
barrio no sirve para explicar diferencias dentro de una sub-zona.

---

## 1. Normalizador de direcciones USIG (integrada)

| Campo | Detalle |
|---|---|
| Fuente concreta | Servicio de normalización y geocodificación de direcciones de USIG, GCBA (`servicios.usig.buenosaires.gob.ar/normalizar`) |
| Cobertura geográfica | CABA completa |
| Período | Consultas hechas durante la corrida de geocodificación (septiembre 2026). El callejero es el vigente al momento de la consulta |
| Granularidad | Punto (dirección, altura) |
| Mecanismo de unión | Consulta 1 a 1 por dirección limpia (`dir_limpia`) del aviso |
| Variable derivada | `lat`, `lon`, `geo_status` |
| Aporta a | Todo el análisis espacial: sub-zonas, distancias, H2 y H3 |
| Limitaciones | 17,9% de los avisos sin coordenadas. **La pérdida no es aleatoria**: varía de 59,5% de éxito en Puerto Madero a 92,5% en Boedo (chi², p < 1e-100). Detalle en `diagnostico.md` |

## 2. Estaciones de subte, BA Data (integrada)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Subte: estaciones", BA Data (GeoJSON). Snapshot versionado en `data/external/estaciones-de-subte.geojson` |
| Cobertura geográfica | CABA, 90 estaciones |
| Período | Snapshot descargado el 14/09/2026 |
| Granularidad | Punto (estación) |
| Mecanismo de unión | Distancia haversine de cada aviso geocodificado a la estación más cercana |
| Variable derivada | `dist_transporte_m` |
| Aporta a | H3 (efecto de la ubicación), gap ajustado por ubicación, índice de accesibilidad |
| Limitaciones | Solo subte. Deja afuera tren y Metrobus, que son el transporte pesado en buena parte del sur y el oeste. Distancia en línea recta, no a pie. No distingue líneas ni frecuencia |

## 3. Polos de centralidad (integrada, definición propia)

| Campo | Detalle |
|---|---|
| Fuente concreta | Coordenadas fijadas por el grupo en `config/config.yaml`: Obelisco, Puerto Madero, Catalinas |
| Cobertura geográfica | CABA |
| Período | No aplica (puntos fijos) |
| Granularidad | Punto |
| Mecanismo de unión | Distancia haversine mínima a cualquiera de los tres polos |
| Variable derivada | `dist_centralidad_m` |
| Aporta a | H3 |
| Limitaciones | Es una elección del grupo, no un dato externo. Hallazgo del TP1: correlación casi nula con el precio por m², porque el valor está en el corredor norte y no en el centro geográfico |

## 4. Estaciones de ferrocarril, BA Data (prevista)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Estaciones de Ferrocarril", BA Data (GeoJSON, CSV, SHP) |
| Cobertura geográfica | Estaciones dentro de CABA |
| Período | A registrar al descargar (fecha de snapshot) |
| Granularidad | Punto (estación) |
| Mecanismo de unión | Igual que subte: haversine a la estación más cercana. Se puede combinar con subte en una sola `dist_transporte_pesado_m` |
| Variable derivada | `dist_tren_m`, `dist_transporte_pesado_m` |
| Aporta a | H3. Corrige el sesgo del subte, que casi no cubre el sur y el oeste |
| Limitaciones | Sin frecuencias. La cercanía al tren puede tener efecto negativo (ruido, barrera urbana): el signo no se puede asumir |

## 5. Metrobus, BA Data (prevista)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Metrobus", BA Data: estaciones y recorridos (GeoJSON) |
| Cobertura geográfica | Corredores de Metrobus en CABA |
| Período | Última actualización del portal: junio 2026. A registrar al descargar |
| Granularidad | Punto (estación) y línea (recorrido) |
| Mecanismo de unión | Haversine a la estación más cercana |
| Variable derivada | `dist_metrobus_m` |
| Aporta a | H3 |
| Limitaciones | Es transporte de superficie: su efecto sobre el precio no es comparable directamente con el del subte |

## 6. Espacios verdes, BA Data (prevista)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Espacios Verdes", BA Data (GeoJSON, polígonos) |
| Cobertura geográfica | CABA: plazas, parques, plazoletas, canteros |
| Período | Última actualización del portal: julio 2026, actualización semestral |
| Granularidad | Polígono |
| Mecanismo de unión | Distancia del aviso al borde del polígono más cercano, filtrando por superficie mínima (un cantero no es una plaza). El umbral de superficie es decisión del grupo |
| Variable derivada | `dist_espacio_verde_m` |
| Aporta a | H3 (pregunta de diagnóstico "efecto infraestructura" del enunciado general) |
| Limitaciones | Requiere geopandas o shapely. La calidad del espacio verde no está en el dataset |

## 7. Polígonos de barrios, BA Data (prevista, para control de calidad)

| Campo | Detalle |
|---|---|
| Fuente concreta | Dataset "Barrios", BA Data (GeoJSON) |
| Cobertura geográfica | Los 48 barrios oficiales de CABA |
| Período | Última actualización del portal: julio 2026 |
| Granularidad | Polígono |
| Mecanismo de unión | Punto en polígono con `lat`/`lon` |
| Variable derivada | `barrio_oficial`, `barrio_coincide` |
| Aporta a | Evaluación de calidad: el barrio del aviso lo declara el anunciante (ej. "Barrio Norte", que no es oficial). Permite medir cuántos avisos están mal asignados |
| Limitaciones | Solo para los geocodificados |

## 8. Tipo de cambio, BCRA (prevista, necesaria para esta entrega)

| Campo | Detalle |
|---|---|
| Fuente concreta | Tipo de cambio de referencia Com. "A" 3500, BCRA (serie diaria, XLS). Alternativa a discutir: dólar MEP |
| Cobertura geográfica | Nacional |
| Período | Fecha de corte del scraping |
| Granularidad | Diaria |
| Mecanismo de unión | Un único valor a la fecha de extracción, aplicado a todos los avisos |
| Variable derivada | `expensas_usd`, precio en USD de los 5 avisos publicados en ARS |
| Aporta a | KPI "Eficiencia de expensas". El enunciado exige declarar fuente, tipo de cambio, fecha y criterio para toda normalización monetaria |
| Limitaciones | Las expensas están en pesos y el precio en dólares. La elección entre oficial y MEP cambia el ratio y es decisión del grupo |

## 9. Permisos de obra, BA Data (prevista, a confirmar)

| Campo | Detalle |
|---|---|
| Fuente concreta | Permisos de obra registrados, BA Data / AGC. **Pendiente confirmar el dataset exacto y si trae coordenadas** |
| Cobertura geográfica | CABA |
| Período | Serie histórica |
| Granularidad | Punto o parcela, según el dataset |
| Mecanismo de unión | Conteo de permisos en un radio o dentro de la sub-zona |
| Variable derivada | `permisos_obra_subzona` (proxy de dinamismo) |
| Aporta a | La línea de "dinamismo de zona" planteada en el TP1 |
| Limitaciones | Mide actividad constructiva, no valorización. Queda para la PreEntrega 3 |

## Descartadas o a descartar

- **Datos agregados por comuna** (censo, NBI, etc.): la comuna agrupa 2 o 3 barrios y
  el análisis compara dentro de la sub-zona. Pueden servir solo como contexto
  descriptivo, no para explicar precios.
- **Alquileres (scraping propio)**: permitirían estimar rentabilidad bruta por zona,
  que es un ancla económica externa al índice. Queda como próximo paso por costo de
  tiempo (8 a 15 h de scraping más geocodificación).
