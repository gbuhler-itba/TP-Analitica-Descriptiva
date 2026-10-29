# Control de las fuentes externas

*Analítica Descriptiva (ITBA, 2026 C2) · PreEntrega 3, tarea 2*

Este documento controla las columnas que agrega `src/fuentes_externas.py` en
`data/processed/accesibilidad.tsv`: distancias a tren, Metrobus y premetro,
distancia y superficie de espacios verdes, barrio oficial y barrios populares.
Las fichas de cada fuente (link, fecha de descarga, SHA-256, criterios) están en
[`fuentes_externas.md`](fuentes_externas.md), fichas 4 a 7, 10 y 11.

Todos los números salen de un script, así que se pueden volver a generar:

```bash
python3 src/fuentes_externas.py                              # escribe accesibilidad.tsv
python3 docs/entregas_grupo/control_fuentes_numeros.py       # imprime las tablas de este documento
```

Las medianas por barrio usan el **barrio oficial**, es decir, el polígono donde
cae el punto, y no la categoría de búsqueda de MercadoLibre (ver la sección 4).

## Resumen

- **El transporte del sur y el oeste cambia por completo.** Con solo subte, la
  mediana de distancia en Liniers, Lugano, Versalles y Villa Riachuelo pasaba los
  4 km. Con tren, premetro y Metrobus cae entre 83% y 95%. En el norte y el centro
  casi no cambia, porque el subte ya estaba más cerca. Es la variación que le
  faltaba a H3.
- **Cada fuente nueva aporta algo propio.** Para 403 avisos la estación de tren
  más cercana está en la provincia. El premetro es el riel más cercano para 206
  avisos, y en Lugano baja la mediana de riel de 1.290 m a 631 m. El Metrobus es el
  transporte más cercano para el 29,7% de los avisos y casi no se correlaciona con
  el riel (Spearman −0,08).
- **El criterio de espacio verde importa.** La mediana de distancia va de 158 m
  con todos los polígonos a 285 m con el criterio elegido (plazas, parques y
  jardines).
- **El barrio de MercadoLibre coincide con el oficial en el 81,6% de los avisos.**
  De las discrepancias, el 94% está a menos de 1 km del barrio buscado: son
  avisos de borde. Pero hay **249 avisos a más de 1 km**: en 246 la dirección
  nombra el barrio buscado y el geocoding la ubicó en otro, por calles homónimas.
- **Hay 96 avisos en barrios populares, y la mayoría no son villas**: 76 son
  barrios municipales, como Lugano I y II y Piedrabuena. Villas hay 11.

## 1. Conteos por fuente

| Fuente | Registros | Detalle |
|---|---|---|
| Estaciones de tren | 301 | 43 en CABA y 258 en la provincia. Se excluye 1 estación cerrada |
| Paradas de Metrobus | 390 | 139 nombres de parada distintos: hay una parada por sentido |
| Estaciones de premetro | 18 | Viene en el plano de la Ciudad (EPSG:9498) y se reproyecta |
| Espacios verdes públicos | 2.176 | 485 cuentan para la distancia y 1.420 para el área. Se repararon 25 geometrías inválidas |
| Barrios oficiales | 48 | Sin geometrías inválidas |
| Barrios populares | 132 | Sin geometrías inválidas |

El archivo del premetro es el único que no viene en longitud y latitud: trae
coordenadas en metros en el sistema plano de la Ciudad. El módulo lee el sistema
de coordenadas que declara cada archivo y lo reproyecta. Como control
independiente, la estación Pte. Illia del premetro queda a 13 m de la estación
Presidente Illia del Belgrano Sur, que es la combinación real entre las dos
líneas, y las 18 estaciones caen en el barrio que declara el propio archivo.

Clases de espacio verde y cuáles entran en cada variable:

| Clase | Polígonos | Hectáreas | Distancia | Área |
|---|---|---|---|---|
| PLAZOLETA | 906 | 211,6 | no | sí |
| CANTERO CENTRAL | 755 | 110,3 | no | no |
| PLAZA | 391 | 273,3 | sí | sí |
| PARQUE | 61 | 602,1 | sí | sí |
| JARDÍN | 27 | 28,4 | sí | sí |
| PATIO RECREATIVO | 18 | 1,2 | no | sí |
| PATIO | 6 | 0,1 | no | sí |
| PARQUE SEMIPÚBLICO | 5 | 341,8 | sí | sí |
| PATIO DE JUEGOS INCLUSIVO | 3 | 0,1 | no | sí |
| PASEO | 2 | 0,1 | no | sí |
| JARDÍN BOTÁNICO | 1 | 5,0 | sí | sí |
| BARRIO/COMPLEJO | 1 | 9,2 | no | sí |

Para el área se excluye además la franja de la General Paz (sección 6).

## 2. Distancias por barrio

Mediana de cada distancia por barrio oficial, en metros. "Riel" es el mínimo
entre subte, tren y premetro; "Pesado" suma el Metrobus. "Verde 500 m" son las
hectáreas de espacio verde dentro del círculo de 500 m. La última columna compara
transporte pesado contra solo subte, que era el único indicador de la PE2.

Barrios del sur y el oeste, ordenados por la caída:

| Barrio | n | Subte | Tren | Premetro | Metrobus | Riel | Pesado | Verde | Verde 500 m (ha) | Caída pesado vs subte (%) |
|---|---|---|---|---|---|---|---|---|---|---|
| Villa Riachuelo | 48 | 5.190 | 1.271 | 994 | 256 | 962 | 256 | 262 | 1,25 | −95 |
| Versalles | 47 | 4.759 | 965 | 5.651 | 432 | 965 | 432 | 167 | 1,63 | −91 |
| Villa Soldati | 48 | 2.906 | 802 | 670 | 268 | 670 | 268 | 148 | 23,41 | −91 |
| Villa Lugano | 218 | 4.232 | 1.290 | 1.183 | 1.084 | 631 | 540 | 131 | 3,74 | −87 |
| Villa Luro | 259 | 3.073 | 530 | 3.794 | 570 | 530 | 403 | 368 | 0,67 | −87 |
| Liniers | 324 | 4.708 | 1.078 | 5.232 | 982 | 1.078 | 812 | 241 | 0,81 | −83 |
| Parque Avellaneda | 118 | 1.554 | 1.260 | 1.753 | 269 | 1.026 | 269 | 364 | 1,97 | −83 |
| Floresta | 210 | 1.054 | 462 | 2.311 | 413 | 459 | 286 | 308 | 0,97 | −73 |
| Mataderos | 210 | 3.903 | 1.876 | 3.816 | 1.390 | 1.876 | 1.390 | 489 | 0,16 | −64 |
| Nueva Pompeya | 55 | 1.009 | 705 | 3.362 | 492 | 551 | 453 | 437 | 0,42 | −55 |

Para comparar, en Recoleta, Almagro, Parque Chacabuco y Villa Ortúzar la caída
es 0: el subte sigue siendo lo más cercano. La tabla completa de los 48 barrios
está en el anexo.

Medianas sobre los 22.912 avisos con coordenadas: subte 508 m, tren 985 m,
premetro 7.181 m, Metrobus 962 m, riel 423 m, transporte pesado 337 m, espacio
verde 284 m y verde a 500 m 0,87 ha.

Mataderos sigue lejos de todo, incluso con las cuatro fuentes: 1.390 m de
mediana. Es un resultado real y no un error: no hay estaciones de tren ni de
premetro dentro del barrio. La estación más cercana para 141 de sus 210 avisos
es Villa Luro, del Sarmiento; para el resto, Villa Madero (en la provincia),
Liniers o Villa Lugano.

Villa Soldati tiene 23,4 ha de verde en el círculo de 500 m porque ahí están el
Parque Indoamericano (88 ha), la Ciudad del Rock (50 ha) y el Parque Roca (44 ha).

## 3. Aporte de cada fuente

**Tren y efecto borde.** Para 403 avisos la estación de tren más cercana está en
la provincia: Aristóbulo del Valle para Saavedra y Núñez, Sáenz Peña para Devoto,
Villa Madero para Mataderos y Lugano. Con solo estaciones de CABA, esos avisos
quedarían una mediana de 256 m más lejos, y hasta 903 m. Por eso el módulo no
filtra por CABA.

**Premetro.** Es el riel más cercano para 206 avisos: 86 en Villa Lugano, 35 en
Villa Riachuelo, 31 en Villa Soldati, 25 en Flores, 22 en Parque Avellaneda y 7 en
Mataderos. Solo pesa en el sur, como era de esperar.

**Metrobus.** Es el transporte más cercano para el 29,7% de los avisos, y su
distancia casi no se correlaciona con la del riel (Spearman −0,08): mide otra
cosa. Por eso, además de entrar en `dist_transporte_pesado_m`, queda como columna
propia, y `dist_riel_m` no lo incluye. Así el sábado se puede probar H3 con cada
definición.

## 4. Barrio de MercadoLibre contra barrio oficial

Los 22.912 avisos con coordenadas caen en exactamente un barrio oficial: ninguno
queda afuera de CABA ni en dos barrios a la vez.

| Resultado | Avisos | % |
|---|---|---|
| Coincide (nombre normalizado) | 18.184 | 79,4 |
| Barrio Norte en Recoleta, Retiro o Palermo | 503 | 2,2 |
| Discrepancia | 4.225 | 18,4 |

La comparación usa los nombres sin tildes, guiones ni puntos, y con "Gral."
expandido a "General". Barrio Norte no es un barrio oficial: se toma como
coincidente si cae en Recoleta, Retiro o Palermo. Los 74 avisos de Barrio Norte
que caen en Balvanera cuentan como discrepancia.

**Una discrepancia no es necesariamente un error.** El barrio del dataset no lo
escribe el anunciante: es la categoría de búsqueda en la que apareció el aviso, y
un aviso cerca del límite entre dos barrios puede aparecer en la categoría del
vecino. Para separar ese ruido de los errores, se midió la distancia de cada
discrepancia al barrio buscado:

| Tramo | Avisos | % de las discrepancias |
|---|---|---|
| Hasta 200 m del barrio buscado | 2.711 | 64,2 |
| De 200 m a 1 km | 1.265 | 29,9 |
| A más de 1 km | 249 | 5,9 |

Las dos primeras filas son avisos de borde. Los 249 avisos a más de 1 km (171
ubicaciones distintas) son otra cosa. **En 246 la dirección publicada nombra el
barrio de la búsqueda, pero el punto cayó a más de 1 km**: el normalizador de USIG
encontró una calle con el mismo nombre en otro barrio, o la dirección está mal
cargada. Los 3 restantes son al revés: la dirección dice Villa Lugano y el aviso
se publicó en la categoría Villa General Mitre, así que el punto está bien y el
error es de la categoría. Ejemplos del primer grupo:

| Búsqueda | Dirección publicada | Ubicado en | Avisos | Km al barrio buscado |
|---|---|---|---|---|
| retiro | Arroyo Al 800, Retiro | Villa Crespo | 17 | 6,0 |
| liniers | Madero 100, Liniers | San Nicolás | 8 | 13,1 |
| palermo | Beruti Al 4400, Palermo | Nueva Pompeya | 6 | 6,6 |
| liniers | Madero Al 100, Liniers | San Nicolás | 4 | 13,1 |
| retiro | Arroyo 800, Retiro | Villa Crespo | 4 | 6,0 |
| belgrano | Mendoza Al 900, Belgrano | La Boca | 4 | 10,7 |

Esos 246 avisos tienen mal **todas** las variables espaciales, incluidas las de la
PE2 (`dist_transporte_m`, `dist_centralidad_m` y `subzona`), no solo las nuevas.
Se puede usar `barrio_coincide` para excluirlos o revisarlos, pero no todos los 0
son errores. Sugerencia para la limpieza: marcar como sospechosos de mal
geocoding los avisos a más de 1 km del barrio buscado cuya dirección nombra ese
barrio.

**Barrios que el scraping no buscaba.** Aparecen 100 avisos en San Cristóbal y 39
en Parque Chas. Se publicaron sobre todo como Boedo (37) y Balvanera (33) los de
San Cristóbal, y como Villa Urquiza (33) los de Parque Chas.

## 5. Barrios populares

Hay 96 avisos dentro de un barrio popular, el 0,42% de los geocodificados.
Ninguno cae en dos polígonos a la vez.

| Tipo | Avisos |
|---|---|
| Barrio municipal | 76 |
| Villa | 11 |
| Barrio urbanizado | 9 |

| Barrio popular | Tipo | Barrio oficial | Avisos |
|---|---|---|---|
| Barrio Gral. Savio (ex Lugano I y II) | Barrio municipal | Villa Lugano | 38 |
| Barrio Piedrabuena | Barrio municipal | Villa Lugano | 20 |
| Barrio Padre Mugica | Villa | Retiro | 11 |
| Barrio Olímpico | Barrio urbanizado | Villa Soldati | 9 |
| Barrio Juan XXIII | Barrio municipal | Parque Chacabuco | 4 |
| Barrio Marcelo T. de Alvear | Barrio municipal | Parque Avellaneda | 3 |
| Barrio Mitre | Barrio municipal | Saavedra | 3 |
| Barrio Los Perales (ex Dorrego) | Barrio municipal | Mataderos | 2 |
| Otros 6 barrios municipales | Barrio municipal | Lugano, La Boca, Villa del Parque, Soldati | 6 |

`en_barrio_popular` marca todos los tipos, como pide la consigna. Pero la mayoría
de los avisos marcados son conjuntos de vivienda social, que se comportan distinto
de una villa o un asentamiento. Por eso `tipo_barrio_popular` va aparte: para el
modelo conviene filtrar villas y asentamientos.

**Rodrigo Bueno.** El dataset lo incluye, con dos polígonos, pero ningún aviso
geocodificado cae ahí. Los 2 avisos que lo mencionan en el título, incluido el del
ranking del notebook 03, no tienen coordenadas. Se marcan por el título en la
limpieza, como acordamos.

## 6. Criterio de espacio verde

Mediana y percentil 90 de `dist_espacio_verde_m` según qué polígonos cuentan:

| Criterio | Polígonos | Mediana (m) | P90 (m) | % adentro |
|---|---|---|---|---|
| Todos los polígonos | 2.176 | 158 | 368 | 0,2 |
| Sin canteros centrales | 1.421 | 182 | 407 | 0,2 |
| Sin canteros ni plazoletas | 515 | 275 | 571 | 0,1 |
| **Criterio elegido**: plazas, parques, jardines y parques semipúblicos | 485 | 285 | 602 | 0,1 |

Con todos los polígonos, casi cualquier aviso tiene "un espacio verde" a menos de
dos cuadras, porque los canteros centrales de las avenidas y las plazoletas de
esquina están en todas partes, y la variable deja de distinguir. El criterio
elegido mide la distancia a un lugar que funciona como plaza o parque. La
diferencia con "sin canteros ni plazoletas" es chica (10 m de mediana): solo
saca patios, paseos y un complejo habitacional.

**La franja de la General Paz.** El polígono 652 está clasificado como
"plazoleta", pero es la franja verde de 104,4 ha que bordea la avenida. Se
excluye del área porque, incluida, sumaría verde a 557 avisos del borde de la
Ciudad sin que haya un parque:

| Barrio | Avisos | Hectáreas extra (media) |
|---|---|---|
| Saavedra | 146 | 1,31 |
| Núñez | 110 | 1,49 |
| Liniers | 90 | 2,09 |
| Villa Devoto | 70 | 2,26 |
| Mataderos | 30 | 3,15 |
| Villa Lugano | 25 | 3,77 |
| Villa Real | 22 | 2,78 |
| Villa Riachuelo | 20 | 1,67 |
| Versalles | 18 | 2,16 |
| Villa Pueyrredón | 18 | 3,22 |
| Villa Urquiza | 8 | 1,97 |

El "Parque Gral. Paz" de Saavedra (polígono 937) es un parque real y queda.

## 7. Controles técnicos

| Control | Resultado |
|---|---|
| Una fila por aviso | 27.922 filas de entrada y 27.922 de salida |
| `link` único | 0 duplicados |
| Avisos sin coordenadas | Los 5.010 quedan vacíos en todas las columnas, nunca en 0 |
| Avisos en el mismo punto | Se calcula una vez por coordenada (9.766 distintas) y se repite, así que dan exactamente el mismo resultado |
| Error de haversine | Máximo 0,24% contra la distancia geodésica sobre el elipsoide WGS84 (2.000 pares aviso-parada): 1,2 m a 500 m |
| Error de la proyección UTM 21S | Máximo 0,02% contra la misma referencia |
| Área del círculo de 500 m | El polígono de 128 vértices pierde 0,04% del área del círculo |
| Reproducibilidad | La salida es idéntica byte a byte en el entorno exacto del repo (Python 3.9, numpy 2.0.2, pandas 2.3.3, geopandas 1.0.1, shapely 2.0.7, pyproj 3.6.1) y en uno nuevo (Python 3.13, pandas 3.0, geopandas 1.1.1, shapely 2.1.1). Este documento también sale idéntico en los dos |
| Sin red | El módulo solo lee los snapshots de `data/external/` |
| Tests | 23 en `tests/test_fuentes_externas.py`, todos pasan en los dos entornos |

Haversine y la proyección tienen errores distintos, pero los dos son
despreciables a la escala de una cuadra. Se mantuvo haversine para los puntos
porque es lo que usa `dist_transporte_m`, y así el mínimo entre subte, tren y
premetro compara distancias medidas de la misma forma.

## 8. Limitaciones

- Todas las distancias son en línea recta, no a pie, y al punto de la estación,
  no a la boca de acceso.
- Ninguna fuente de transporte trae frecuencia ni cantidad de pasajeros: una
  estación del premetro pesa igual que una de subte en `dist_riel_m`.
- Las variables solo existen para los avisos geocodificados (82,1%). Y entre esos
  hay 246 con la ubicación casi seguramente equivocada (sección 4).
- El dataset de espacios verdes no informa calidad, estado ni seguridad, y la
  clase la asigna la Ciudad: hay "plazoletas" de más de 4 ha.

## Anexo: todos los barrios

Medianas en metros, salvo "Verde 500 m", en hectáreas.

| Barrio | n | Subte | Tren | Premetro | Metrobus | Riel | Pesado | Verde | Verde 500 m (ha) | Caída pesado vs subte (%) |
|---|---|---|---|---|---|---|---|---|---|---|
| Agronomía | 56 | 2.021 | 410 | 6.456 | 408 | 410 | 275 | 318 | 0,15 | −86 |
| Almagro | 1.474 | 352 | 1.496 | 5.466 | 2.243 | 352 | 352 | 508 | 0,09 | 0 |
| Balvanera | 1.585 | 252 | 926 | 6.825 | 1.750 | 251 | 251 | 305 | 0,72 | 0 |
| Barracas | 334 | 1.134 | 956 | 7.196 | 1.069 | 922 | 836 | 169 | 2,78 | −26 |
| Belgrano | 1.293 | 474 | 645 | 9.266 | 404 | 376 | 315 | 243 | 1,01 | −34 |
| Boedo | 354 | 444 | 1.906 | 4.180 | 1.125 | 444 | 380 | 322 | 0,17 | −14 |
| Caballito | 1.510 | 398 | 1.003 | 3.426 | 2.118 | 382 | 360 | 286 | 0,95 | −10 |
| Chacarita | 309 | 593 | 613 | 6.693 | 1.134 | 593 | 579 | 252 | 1,84 | −2 |
| Coghlan | 171 | 1.419 | 670 | 9.417 | 1.299 | 670 | 670 | 453 | 0,43 | −53 |
| Colegiales | 529 | 530 | 572 | 8.009 | 482 | 386 | 349 | 208 | 1,44 | −34 |
| Constitución | 428 | 284 | 883 | 7.212 | 418 | 279 | 248 | 215 | 2,19 | −13 |
| Flores | 1.034 | 462 | 748 | 1.811 | 872 | 415 | 338 | 330 | 0,69 | −27 |
| Floresta | 210 | 1.054 | 462 | 2.311 | 413 | 459 | 286 | 308 | 0,97 | −73 |
| La Boca | 234 | 1.869 | 1.767 | 8.409 | 424 | 1.767 | 424 | 193 | 1,85 | −77 |
| Liniers | 324 | 4.708 | 1.078 | 5.232 | 982 | 1.078 | 812 | 241 | 0,81 | −83 |
| Mataderos | 210 | 3.903 | 1.876 | 3.816 | 1.390 | 1.876 | 1.390 | 489 | 0,16 | −64 |
| Monserrat | 623 | 281 | 1.760 | 7.869 | 332 | 281 | 221 | 255 | 0,38 | −21 |
| Monte Castro | 158 | 3.334 | 1.719 | 4.730 | 1.380 | 1.719 | 1.332 | 290 | 1,11 | −60 |
| Nueva Pompeya | 55 | 1.009 | 705 | 3.362 | 492 | 551 | 453 | 437 | 0,42 | −55 |
| Núñez | 605 | 1.003 | 533 | 10.637 | 286 | 473 | 234 | 313 | 0,79 | −77 |
| Palermo | 1.843 | 471 | 773 | 7.851 | 793 | 417 | 343 | 253 | 1,12 | −27 |
| Parque Avellaneda | 118 | 1.554 | 1.260 | 1.753 | 269 | 1.026 | 269 | 364 | 1,97 | −83 |
| Parque Chacabuco | 303 | 371 | 1.614 | 2.260 | 1.747 | 371 | 371 | 305 | 0,77 | 0 |
| Parque Chas | 39 | 407 | 916 | 6.740 | 1.658 | 362 | 362 | 283 | 0,20 | −11 |
| Parque Patricios | 138 | 366 | 1.534 | 5.096 | 224 | 364 | 202 | 314 | 2,95 | −45 |
| Paternal | 31 | 1.715 | 582 | 4.746 | 180 | 582 | 180 | 804 | 0,02 | −90 |
| Puerto Madero | 421 | 974 | 2.321 | 9.444 | 626 | 974 | 626 | 117 | 10,91 | −36 |
| Recoleta | 1.832 | 411 | 1.551 | 8.113 | 1.711 | 411 | 411 | 264 | 1,37 | 0 |
| Retiro | 763 | 360 | 784 | 9.188 | 328 | 360 | 263 | 159 | 3,63 | −27 |
| Saavedra | 393 | 1.779 | 690 | 10.812 | 569 | 690 | 359 | 209 | 1,38 | −80 |
| San Cristóbal | 100 | 416 | 1.581 | 5.388 | 945 | 416 | 366 | 262 | 0,61 | −12 |
| San Nicolás | 872 | 220 | 1.572 | 8.299 | 440 | 220 | 196 | 286 | 1,49 | −11 |
| San Telmo | 361 | 625 | 1.190 | 8.151 | 335 | 625 | 283 | 158 | 1,82 | −55 |
| Vélez Sarsfield | 167 | 1.908 | 876 | 2.818 | 558 | 876 | 491 | 166 | 1,72 | −74 |
| Versalles | 47 | 4.759 | 965 | 5.651 | 432 | 965 | 432 | 167 | 1,63 | −91 |
| Villa Crespo | 799 | 476 | 1.103 | 5.367 | 551 | 453 | 293 | 521 | 0,05 | −38 |
| Villa del Parque | 458 | 2.829 | 536 | 5.432 | 446 | 536 | 271 | 456 | 0,26 | −90 |
| Villa Devoto | 473 | 3.831 | 517 | 6.631 | 1.058 | 517 | 431 | 469 | 0,34 | −89 |
| Villa General Mitre | 167 | 1.994 | 1.232 | 4.185 | 250 | 1.232 | 250 | 723 | 0,02 | −87 |
| Villa Lugano | 218 | 4.232 | 1.290 | 1.183 | 1.084 | 631 | 540 | 131 | 3,74 | −87 |
| Villa Luro | 259 | 3.073 | 530 | 3.794 | 570 | 530 | 403 | 368 | 0,67 | −87 |
| Villa Ortúzar | 239 | 398 | 985 | 7.005 | 1.943 | 398 | 398 | 257 | 0,88 | 0 |
| Villa Pueyrredón | 207 | 1.848 | 634 | 7.361 | 1.141 | 634 | 614 | 413 | 0,60 | −67 |
| Villa Real | 30 | 5.442 | 1.572 | 6.674 | 1.931 | 1.572 | 1.478 | 281 | 1,56 | −73 |
| Villa Riachuelo | 48 | 5.190 | 1.271 | 994 | 256 | 962 | 256 | 262 | 1,25 | −95 |
| Villa Santa Rita | 150 | 1.992 | 1.509 | 3.623 | 416 | 1.509 | 416 | 549 | 0,01 | −79 |
| Villa Soldati | 48 | 2.906 | 802 | 670 | 268 | 670 | 268 | 148 | 23,41 | −91 |
| Villa Urquiza | 892 | 621 | 554 | 8.166 | 2.347 | 467 | 467 | 322 | 0,48 | −25 |
