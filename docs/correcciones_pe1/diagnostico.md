# Correcciones de la PreEntrega 1: diagnóstico

Trabajo operativo sobre las observaciones de la devolución. Todos los números salen
de `docs/correcciones_pe1/diagnostico.py`, que corre sobre
`data/processed/propiedades_enriquecidas.tsv` sin modificarlo:

```bash
python3 docs/correcciones_pe1/diagnostico.py
```

Las tablas completas quedan en `docs/correcciones_pe1/salida/`.

> Todo lo marcado con **[DECIDIR]** es criterio del grupo. El script usa un valor
> provisorio para poder correr, pero no es una decisión tomada.

---

## 1. Cifras narradas vs. calculadas: 130.000 o 135.000

**El número correcto es USD 130.000, el del PDF entregado. El README (135.000) está mal.**

La causa es un error de parseo que ya conocíamos por el "BAJÓ DE PRECIO". En
**627 avisos** (2,2%) el scraper pegó el precio anterior y el vigente en un solo
número:

| `precio_texto` | `precio` guardado |
|---|---|
| US$120.000US$112.000 BAJÓ DE PRECIO | 120.000.112.000 |
| US$44.500US$42.000 BAJÓ DE PRECIO | 4.450.042.000 |

Esos 627 valores quedan arriba de todo en la distribución, así que corren la mediana
de 130.000 a 135.000. La media en USD del dataset actual es **5.215 millones**; con
el precio corregido es **209.160**. Cualquier media, desvío o gráfico que se haga
sin corregir esto sale mal.

**Arreglo:** `src/limpieza.py::corregir_precio()` separa `precio_actual`,
`precio_anterior`, `bajo_de_precio` y `baja_pct`. Verificado: en los 27.295 avisos
sin baja el precio corregido coincide exactamente con el original.

**De yapa sale una variable nueva:** la baja mediana es 6,8% y la mínima es
exactamente 5,0%, lo que sugiere que la plataforma muestra la etiqueta solo a
partir de 5%. `bajo_de_precio` sirve como indicio de vendedor con urgencia o de
aviso sobrevaluado, y viene bien para la pregunta de liquidez.

**Pendiente:** corregir el 135.000 del README (sección 7). No lo toqué porque es
el README de la entrega anterior.

---

## 2. Sesgo del geocoding

Lo que se va a preguntar: ¿el 17,9% sin coordenadas es aleatorio?

**No lo es por barrio.** La tasa de éxito va de **59,5% en Puerto Madero** a
**92,5% en Boedo**, y la diferencia entre barrios es muy significativa
(chi², p ≈ 1e-101). Barrios bajo 75%: Puerto Madero, Villa Real, Villa Lugano,
Nueva Pompeya, Villa General Mitre, La Boca, Villa Riachuelo, Paternal, Vélez
Sarsfield. Tabla completa: `salida/geocoding_por_barrio.csv`.

Puerto Madero es el caso crítico: es un barrio premium y pierde **4 de cada 10
avisos** del análisis por sub-zona. La causa probable son direcciones del tipo
"Zencity Boulevard..." o "Le Parc, Torre Río", con nombres de emprendimientos que
USIG no reconoce.

**En cambio, casi no hay sesgo en las características:**

| | Geocodificados | No geocodificados |
|---|---|---|
| Mediana precio/m² (USD) | 2.389 | 2.454 |
| Mediana superficie | 56 m² | 58 m² |
| Completitud de amenities | 52,2% | 53,5% |

La diferencia de precio/m² es de 2,7%. Es estadísticamente significativa
(Mann-Whitney, p ≈ 1e-6) por el tamaño de muestra, pero chica en magnitud. A
nivel barrio, la tasa de geocoding casi no se relaciona con el precio
(Spearman 0,15).

**Lectura sugerida para el README:** la pérdida es desigual entre barrios, así que
las conclusiones por sub-zona tienen menos respaldo en esos 9 barrios, y en
especial en Puerto Madero. Dentro de cada barrio, los avisos perdidos no son
sistemáticamente más caros ni más equipados.

---

## 3. Índice de confort: cuánto discrimina cada bloque y qué pasa si cambian los pesos

Es lo que pidió el profe textualmente: "midan cuánto discrimina cada bloque dentro
de CABA, eviten fijar los pesos como definitivos antes de analizar los datos y
muestren cómo cambian los resultados con otras ponderaciones".

### 3.0. Antes de medir, dos decisiones que no están tomadas

El índice nunca se implementó en código. Para poder medirlo, `src/indice_confort.py`
usa un **mapeo provisorio** armado a partir de la descripción del README:

| Bloque | Componentes usados |
|---|---|
| Infraestructura (45%) | gas_natural, agua_corriente, aire_acondicionado, calefaccion, acceso_a_internet, con_conexion_para_lavarropas, ascensor |
| Amenities (30%) | pileta, gimnasio, sauna, salon_de_usos_multiples, seguridad, parrilla, lavanderia, roof_garden, salon_de_fiestas, playroom |
| Atributos (25%) | balcon, terraza, es_frente (disposicion = Frente), es_piso_alto (piso ≥ 5) |

- **[DECIDIR]** Qué columnas van en cada bloque, y si "piso alto" es desde el 5.
- **[DECIDIR]** Qué significa una celda vacía (ver 3.1).

Dentro de cada bloque todos los componentes pesan igual. El README dice que "lo más
esencial pesa más", pero eso nunca se cuantificó.

Muestra del diagnóstico: 22.406 avisos geocodificados, en USD, de 15 a 1.000 m²,
con precio/m² entre p1 y p99 (918 a 6.809 USD/m²). Es un recorte provisorio: la
limpieza formal va en el notebook 01.

### 3.1. Hallazgo 1: hay dos tipos de columnas y el nulo no significa lo mismo

MercadoLibre publica algunas características solo cuando están presentes:

- **Columnas "solo Sí"** (agua_corriente, acceso_a_internet, gimnasio, sauna, SUM,
  parrilla, etc.): nunca aparece "No". Un vacío puede ser "no tiene" o "no lo
  cargó", y no hay forma de distinguirlo.
- **Columnas "Sí/No"** (gas_natural, ascensor, pileta, balcón, etc.): el vacío es
  falta de dato.

Consecuencia directa: `agua_corriente` tiene 61,7% de "Sí" y 0% de "No". No mide si
el departamento tiene agua, mide si el anunciante lo tildó.

### 3.2. Hallazgo 2: el bloque de infraestructura mide lo completo que está el aviso, no la infraestructura

Si el vacío se toma como "no tiene", el puntaje de infraestructura correlaciona
**0,60** con la completitud del aviso. Los departamentos "con más infraestructura"
son, en buena medida, los que tienen el aviso más completo.

Además, dentro de la misma sub-zona, la infraestructura **casi no se relaciona con
el precio**:

| Bloque | Peso asignado | Spearman con log(precio/m²), dentro de la sub-zona | Avisos con puntaje 0 | Varianza que queda dentro de la sub-zona |
|---|---|---|---|---|
| Infraestructura | 45% | **0,05** | 18% | 97% |
| Amenities | 30% | **0,29** | 51% | 87% |
| Atributos | 25% | **0,21** | 17% | 96% |

El orden empírico (amenities > atributos > infraestructura) es **el inverso** de los
pesos asignados. Con la otra lectura del nulo (promediar solo lo declarado) el
orden se mantiene: 0,27 / 0,21 / 0,06.

Los tres bloques discriminan dentro de la sub-zona: entre 87% y 97% de su varianza
está entre departamentos de la misma zona y no entre zonas. O sea que el índice sí
separa departamentos comparables, que es lo que el proyecto necesita.

**Por componente** (diferencia mediana de precio/m² entre avisos con y sin el
atributo, dentro de la misma sub-zona). Es asociación, no efecto causal:

| Componente | Prima | Sub-zonas comparables |
|---|---|---|
| gimnasio | +38,6% | 54 |
| sauna | +35,3% | 16 |
| pileta | +33,5% | 77 |
| SUM | +29,9% | 68 |
| parrilla | +26,2% | 95 |
| balcón | +11,6% | 157 |
| terraza | +10,1% | 102 |
| aire acondicionado | +9,1% | 140 |
| seguridad | +7,7% | 109 |
| ascensor | +7,1% | 153 |
| piso alto | +6,6% | 131 |
| frente | +1,8% | 154 |
| agua corriente | −0,6% | 153 |
| gas natural | **−4,8%** | 155 |

El gas natural con prima negativa es un buen ejemplo de por qué no hay que atribuir
sin comparar semejantes. Una explicación posible, a verificar, es que los edificios
nuevos con amenities sean todo-eléctricos: el gas estaría marcando antigüedad, no
confort.
Tabla completa: `salida/componentes.csv`.

### 3.3. Hallazgo 3: las propiedades señaladas son bastante estables ante cambios de pesos

Se recorrieron **171 ponderaciones** (cada peso de 5% a 90%, de a 5%). Para cada una
se calculó el gap dentro de la sub-zona (residuo de log precio/m² contra el índice)
y se marcó el 5% con el precio más bajo para su confort, unos 1.120 avisos.

| Métrica | Valor |
|---|---|
| Coincidencia con la ponderación 45/30/25 (Jaccard), mediana | 0,82 |
| Coincidencia, peor caso (5/40/55) | 0,66 |
| Correlación del gap con el de 45/30/25, peor caso | 0,95 |
| Avisos marcados en alguna ponderación | 1.705 |
| Avisos marcados en **las 171** | **692** |
| Coincidencia 45/30/25 vs. otra lectura del nulo | 0,73 |
| Coincidencia 45/30/25 vs. **sin índice** (solo "barato para su sub-zona") | **0,67** |

Dos lecturas:

1. Los pesos importan menos de lo que parecía. Hay un núcleo de **692 avisos** que
   aparecen señalados con cualquier ponderación. Es un argumento para el README:
   los resultados no dependen de un 45/30/25 elegido a mano.
2. La contracara: **dos tercios de lo que marca el índice ya aparece mirando solo el
   precio relativo a la sub-zona.** El índice reordena en el margen, pero la mayor
   parte de la señal es "precio atípicamente bajo". Esto coincide con lo que dijo el
   profe: hay que presentarlos como señales de precio atípico para investigar, no
   como confort subvaluado.

Tabla completa: `salida/sensibilidad_pesos.csv`.

### 3.4. Decisiones de criterio que abre este diagnóstico

- **[DECIDIR]** ¿Se mantiene la infraestructura como bloque? Hay tres caminos:
  sacarla del índice y usarla como filtro de calidad del aviso; quedarse solo con sus
  columnas Sí/No; o bajarle el peso.
- **[DECIDIR]** ¿Cómo se justifican los pesos? El enunciado del TP2 prohíbe
  ponderaciones sin justificar. Las opciones: (a) pesos iguales como base neutral,
  con análisis de sensibilidad; (b) pesos derivados de los datos (primas, o la
  correlación de la tabla de 3.2); (c) mantener pesos de preferencia del fondo, pero
  declarados como tales y acompañados de este análisis de sensibilidad. La (b) tiene
  un problema conceptual: si los pesos salen del precio, el gap contra el precio
  queda circular.
- **[DECIDIR]** ¿Qué se hace con el vacío en las columnas "solo Sí"?
- **[DECIDIR]** ¿Se reescribe H1? Hoy dice que los casos marcados "constituyen
  oportunidades de inversión subvaluadas". La devolución y el hallazgo 3 piden
  reformularla como "señal de precio atípico a investigar".

---

## 4. Problemas de calidad encontrados de paso (van al notebook 01)

| Problema | Filas | Tratamiento sugerido |
|---|---|---|
| Precio concatenado por "BAJÓ DE PRECIO" | 627 | `corregir_precio()`. Resuelto |
| Precios en ARS con valores absurdos ($1.111.111.111 por 30 m²) | 5 | Fuera de alcance o conversión documentada. **[DECIDIR]** |
| Superficie de 0 a 14 m² (el listado toma mal el valor: 1 m² cubierto y 26 m² totales) | 36 | Recuperar desde `superficie_total` / `superficie_cubierta` o excluir |
| `superficie_cubierta` con separador de miles ("45.000 m²" = 45 m²) | a medir | Parseo específico |
| `departamentos_por_piso` = 99 | 6.970 | Faltante disfrazado: pasar a NaN |
| Expensas en ARS como texto ("290.000 ARS") | 97% con dato | Parsear y convertir con tipo de cambio documentado |
| Antigüedad como texto ("71 años") | 97% con dato | Parsear a entero |
| Avisos de más de USD 5 millones después de corregir el precio | a medir | Revisar uno por uno: ¿súper lujo o error de carga? |
| Barrio declarado por el anunciante ("Barrio Norte" no es barrio oficial) | a medir | Cruce con polígonos oficiales (ver fuentes) |

**Fecha de extracción:** 14/08/2026, según el grupo. El dataset no tiene una
columna de fecha y las fechas de los archivos se perdieron al reorganizar el repo,
así que hay que declararla en el README y en el notebook. Es también la fecha de
referencia para el tipo de cambio de las expensas.
