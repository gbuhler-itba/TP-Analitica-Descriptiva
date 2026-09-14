# Evidencia de la corrida documentada

Instantánea **curada e inmutable** de los controles de calidad, tomada el
14 de septiembre de 2026. No se regenera con cada corrida: es la evidencia a
la que apunta la sección 16 del README principal.

Los logs de trabajo viven en `outputs/logs/` y están excluidos por
`.gitignore`, porque cada corrida los sobrescribe. Esta carpeta existe
justamente para que la evidencia no se pise sola.

Entorno de todas estas corridas: macOS, Python 3.9, con las versiones fijadas
en `requirements.txt` (`requests 2.32.5`, `beautifulsoup4 4.15.0`,
`pandas 2.3.3`, `numpy 2.0.2`, `scikit-learn 1.6.1`, `PyYAML 6.0.3`).

## Qué prueba cada archivo

| Archivo | Qué corrida documenta | Red real | Qué prueba |
|---|---|---|---|
| `qc_02_consolidacion.json` | Etapa 2 completa sobre las 5 cuotas versionadas | no aplica | 27.922 entran, 27.922 salen, 0 duplicados eliminados |
| `qc_03_geocoding_verificacion.json` | Etapa 3 en modo `--verificar` sobre las 27.922 filas | no, 0 llamadas a USIG | 8 de 8 controles OK, tasa de geocodificación 82,06% |
| `qc_04_enriquecimiento.json` | Etapa 4 completa, bajando el GeoJSON de BA Data | **sí**, BA Data | 90 estaciones, 198 sub-zonas, `dist_transporte_m` media 925 m |
| `spot_01_scraping.json` + `spot_etapa1.txt` | Etapa 1 acotada: 1 barrio, sin fichas, 1 página | **sí**, MercadoLibre | El crawling y la paginación funcionan: 15 avisos, 0 duplicados |
| `spot_03_geocoding.json` + `spot_etapa3.txt` | Etapa 3 acotada con `--limite 20` | **sí**, USIG | El camino HTTP real contra USIG funciona: 19 OK, 1 SIN_RESULTADO |
| `spot_etapa4.txt` | Etapa 4 completa más comparación de hashes | **sí**, BA Data | El TSV regenerado es **byte a byte idéntico** al versionado |

## Nota sobre `spot_03_geocoding.json`

Ese archivo se generó **antes** de un ajuste posterior al bloque de control de
calidad. Por eso su campo `geocoding_tasa_exito_pct` dice `0.07`: se calculaba
sobre las 27.922 filas del dataset cuando la corrida solo procesó 20. Los
números crudos del archivo son correctos (19 `OK` y 1 `SIN_RESULTADO` sobre 20
procesadas, o sea 95%).

En la versión actual del código una corrida parcial reporta además
`corrida_parcial`, `geocoding_por_estado_de_esta_corrida`,
`geocoding_tasa_exito_de_esta_corrida_pct` y una `nota_alcance`, así que el
mismo spot check hoy informa 95,0% además de la tasa global.

## El GeoJSON de subte que se usó

La corrida de la etapa 4 documentada acá descargó el dataset de estaciones de
subte de BA Data el 14 de septiembre de 2026 y lo dejó cacheado. Ese archivo
quedó **versionado** en `data/external/estaciones-de-subte.geojson`, así que la
etapa 4 es determinística y reproducible sin red.

```
b001f82960c34cedd5489e149498e7a32d978ada1537df7eab69a5a6b935226f  data/external/estaciones-de-subte.geojson
```

90 estaciones, 16.399 bytes. Con `--forzar-descarga` se trae la versión viva de
BA Data y se pisa el snapshot; si el portal publicó cambios, `dist_transporte_m`
y el hash del dataset final van a cambiar.

## Hashes de los datasets versionados

```
7977d795f622a0fe5136c8736f5bfe724ad6dff19e21c61382f8626b6c80e1a4  data/interim/mercadolibre_CABA_completo.tsv
62b1a0b7be9c202ffdeddf965698dbb53f262a9e9d599227b78d662baee6d016  data/interim/propiedades_geocodificadas.tsv
498328bdefbcbb8e2f7c1552688a4639de8dd32e4ede91f962653894a3e0d9d9  data/processed/propiedades_enriquecidas.tsv
```

Para recalcularlos: `shasum -a 256 <archivo>` en macOS, `sha256sum <archivo>` en Linux.
