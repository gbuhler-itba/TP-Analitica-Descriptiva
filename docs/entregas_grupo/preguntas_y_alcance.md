# Preguntas por nivel, nivel predictivo y alcance

Entregable de la Tarea B para la PreEntrega 2. Reemplaza la sección 3 del README de la PreEntrega 1 y agrega dos secciones nuevas: la definición del nivel predictivo y lo que el análisis no mide.

**Cambio de enfoque que atraviesa todo el documento.** La idea del índice se mantiene, pero sus pesos dejan de ser los 45/30/25 elegidos a mano. Los 45/30/25 quedan como primera propuesta, ya contrastada con los datos (ver `docs/correcciones_pe1/diagnostico.md`), y los pesos pasan a salir de lo que el mercado paga por cada característica dentro de la misma sub-zona. Así, cada aviso tiene un **precio esperado** según sus características. Los avisos que se marcan son **avisos con precio atípicamente bajo para investigar**, es decir, publicados por debajo de su precio esperado. Son una señal para que el analista mire, no una oportunidad comprobada.

## Hipótesis y KPIs de referencia

Las preguntas de la tabla remiten a estas hipótesis. H2 y H3 se mantienen. H1 se reformula para alinearse con el enfoque nuevo (propuesta a validar con el grupo):

- **H1 (reformulada).** Dentro de una misma sub-zona, el precio de publicación no refleja de forma uniforme las características del departamento: existe un grupo de avisos publicados sistemáticamente por debajo del precio que el mercado paga por esas características. Estos avisos son candidatos a investigar, no oportunidades confirmadas.
- **H2.** Un barrio no es una unidad homogénea de precios; la sub-zona es una vara de referencia más precisa.
- **H3.** Parte de la variación de precios se explica por variables de entorno (transporte, centralidad). Controlar por ellas separa los avisos baratos para su ubicación de los que son baratos simplemente por estar peor ubicados.

**KPIs con nombre actualizado:** precio por m² de la sub-zona, tasa de completitud, prima por característica (reemplaza al "peso empírico por bloque"), precio esperado, brecha de precio (reemplaza al "gap de confort": diferencia porcentual entre precio publicado y precio esperado), error de estimación fuera de muestra, índice de accesibilidad, eficiencia de expensas y ranking de avisos a investigar (reemplaza al "ranking de oportunidades").

## Parte 1: preguntas reclasificadas

Criterio usado para asignar el nivel:

| Nivel | Pregunta que responde | Señal en la redacción |
|---|---|---|
| Descriptivo | ¿Qué hay? ¿Cómo se distribuye? | Cuánto, cuántos, cómo se reparte |
| Diagnóstico | ¿Por qué? ¿Qué se relaciona con qué? | Explica, se asocia, depende de |
| Predictivo | ¿Cuánto valdría algo que no observamos? | Estimar, esperar, anticipar |
| Prescriptivo | ¿Qué hacemos? | Conviene, priorizar, umbral, regla |

### Descriptivo

| # | Pregunta | Por qué es este nivel | Aporta a |
|---|---|---|---|
| D1 | ¿Cómo se distribuye el precio por m² (mediana, dispersión, asimetría) entre barrios y entre las sub-zonas de un mismo barrio? | Mide cómo se reparte una variable, sin explicar causas | H2 · Precio por m² de la sub-zona |
| D2 | ¿Qué proporción de avisos declara cada característica, cuáles columnas son "solo Sí" y cuáles "Sí/No", y qué tan completo está cada aviso? | Cuantifica la calidad del dato tal como está | Tasa de completitud · condiciona la confianza en el precio esperado |
| D3 | ¿Con qué frecuencia aparece cada característica (pileta, gimnasio, balcón, cochera, piso alto) en cada sub-zona? | Cuenta y reparte; no relaciona con el precio | Prima por característica: si una característica no aparece, o aparece en todos los avisos de una sub-zona, su prima no se puede estimar ahí |
| D4 | ¿Qué proporción de avisos muestra "bajó de precio", en cuánto bajaron y cómo se reparte por barrio? | Describe una variable nueva del dataset | Señal de liquidez (Parte 3) · ranking de avisos a investigar |

### Diagnóstico

| # | Pregunta | Por qué es este nivel | Aporta a |
|---|---|---|---|
| G1 | Dentro de la misma sub-zona, ¿cuánto se asocia cada característica con el precio por m², y cuáles explican más diferencia de precio? | Busca qué variables se relacionan con el precio, controlando por zona. Reemplaza "¿los pesos asignados a mano se sostienen?", que ya no aplica | H1 · Prima por característica |
| G2 | ¿La prima de una característica es la misma en todas las zonas y en todos los segmentos de precio, o depende de dónde está el departamento y de su gama? | Pregunta si una relación depende de una tercera variable | H1, H2 · Prima por característica por segmento |
| G3 | ¿Cuánto de la diferencia de precio entre sub-zonas se explica por accesibilidad al transporte y centralidad, y los avisos con precio atípicamente bajo lo siguen siendo después de controlar por ubicación? | Busca la explicación de una diferencia | H3 · Índice de accesibilidad · Brecha de precio |
| G4 | ¿Qué distingue a los avisos con precio atípicamente bajo: tienen características que el mercado no está pagando, o tienen señales de otro problema (aviso incompleto, baja de precio previa, mucha antigüedad, expensas altas)? | Explica por qué un aviso queda barato. Es la versión correcta de "¿cuál bloque está más regalado?", que estaba como predictiva y es diagnóstica: no anticipa nada, explica | H1 · Tasa de completitud · Eficiencia de expensas |

### Predictivo

| # | Pregunta | Por qué es este nivel | Aporta a |
|---|---|---|---|
| P1 | Dadas las características y la ubicación de un aviso, ¿qué precio por m² se esperaría para él según lo que el mercado paga en su sub-zona? | Estima un valor que no se observa: el precio "normal" para ese aviso | H1 · Precio esperado · Brecha de precio |
| P2 | ¿Con qué error se estima el precio por m² de avisos que el modelo no vio, y en qué barrios o segmentos el error es mayor? | Cuantifica la calidad de una estimación sobre datos no observados | Error de estimación fuera de muestra · define cuándo una brecha es "atípica" y no ruido |
| P3 | ¿Qué precio por m² se esperaría para un departamento que no está publicado (por ejemplo, uno que el fondo recibe por fuera del portal), y con qué margen de error? | Estima el valor de una unidad no observada, con las mismas reglas que P1 | Precio esperado · uso operativo de la herramienta |
| P4 | Si se repite el scraping, ¿los avisos marcados hoy salen del portal o bajan su precio antes que avisos comparables no marcados? | Anticipa qué va a pasar con avisos concretos y se valida contra una observación futura real. Es la evolución de la pregunta de estabilidad temporal de la PreEntrega 1. Mide si la señal es real o ruido, sin pronosticar precios | H1 · valida el ranking de avisos a investigar · liquidez (Parte 3). Requiere un segundo relevamiento |

### Prescriptivo

| # | Pregunta | Por qué es este nivel | Aporta a |
|---|---|---|---|
| R1 | ¿Qué regla conviene usar para decidir qué avisos pasan a revisión del analista: qué brecha mínima, qué completitud mínima y cómo se tiene en cuenta el error de estimación de su zona? | Define un umbral de decisión | Ranking de avisos a investigar · Brecha de precio · Tasa de completitud |
| R2 | Al priorizar entre avisos marcados, ¿conviene ponderar distinto uno bien ubicado frente a uno en zona periférica, dado que el primero suele tener más liquidez? | Es una decisión de priorización. Estaba como predictiva y es prescriptiva: no estima nada, elige | H3 · Ranking de avisos a investigar · Índice de accesibilidad |
| R3 | ¿En qué sub-zonas conviene concentrar el análisis, según dónde las brechas sean más frecuentes y la estimación más precisa? | Recomienda dónde asignar esfuerzo | H2 · Error de estimación por zona |

**Preguntas eliminadas o absorbidas respecto de la PreEntrega 1:**

- "¿Cómo se distribuye el índice de confort y cuánto pesa cada bloque?" y "¿El índice de confort depende del tamaño?": ya no hay bloques con pesos fijos que describir. Lo que queda útil está en D2 y D3, y el peso real de cada característica pasa a G1.
- "¿Existen perfiles contradictorios y el índice los penaliza más que una suma?": era una pregunta sobre el diseño del índice.
- "¿Se puede marcar automáticamente cualquier aviso nuevo o hace falta research?": queda respondida por la combinación de P2 (cuánto error tiene la estimación) y R1 (la regla de qué pasa a revisión).
- "¿Cada cuánto re-testear las ponderaciones?": no hay ponderaciones fijas. Queda como recomendación operativa del cierre: re-estimar las primas en cada nuevo relevamiento.

## Parte 2: definición del nivel predictivo

**Variable objetivo.** Se predice el precio por m² de publicación de un aviso, en USD/m², calculado como `precio_actual / m2`, después de corregir los 627 precios concatenados por "BAJÓ DE PRECIO". Se trabaja con su logaritmo, porque la distribución es asimétrica a derecha y porque las primas se interpretan mejor en términos porcentuales: una cochera agrega un porcentaje del precio, no un monto fijo igual en Palermo que en Lugano. Quedan fuera los 5 avisos en pesos. Es importante remarcar que se predice el precio publicado, no el precio de venta, porque es el único que se observa.

**Información disponible al momento de predecir.** El criterio es simple: solo se puede usar lo que se conocería de un departamento antes de saber a qué precio se publica. Entran las características declaradas (superficie, ambientes, dormitorios, baños, cocheras, antigüedad, piso, disposición, orientación, amenities), las expensas, la ubicación (barrio, sub-zona, latitud y longitud) y las variables de entorno (distancia a subte y a centralidad). Quedan afuera tres grupos. Primero, todo lo que sale del precio del propio aviso: `precio_anterior`, `baja_pct` y `bajo_de_precio` son en los hechos el precio con otro nombre, y usarlos sería darle la respuesta al modelo. Segundo, cualquier resumen de precios que incluya al propio aviso, por ejemplo la mediana de precio por m² de su sub-zona calculada sobre todo el dataset: tiene que calcularse sin ese aviso. Tercero, información posterior a la fecha del scraping (14/08/2026), como datos de una fuente externa publicados después: un analista que evalúa un aviso hoy no la tendría.

**Validación fuera de muestra.** Se dividen los avisos en 5 grupos. Se estima el modelo con 4 grupos y se mide el error en el quinto, y se rota hasta que cada grupo fue el de prueba una vez. Esto evita hacer trampa porque el error de cada aviso se mide con un modelo que nunca lo vio: si se midiera sobre los mismos avisos con los que se estimó, el modelo podría memorizarlos y el error saldría artificialmente bajo. La validación cumple además una segunda función clave para el proyecto: la brecha de precio de cada aviso se calcula con el precio esperado que dio el modelo que no lo vio. Si se usara un modelo que lo incluyó, el propio aviso arrastraría su precio esperado hacia abajo y la brecha se achicaría justo en los casos que queremos encontrar. Para que la separación sea real, todo cálculo que use precios (medianas por sub-zona, primas, umbrales de outliers) se hace dentro de cada vuelta, solo con los 4 grupos de entrenamiento. Hay un riesgo concreto en nuestros datos: unos 3.000 avisos geocodificados comparten dirección, superficie y precio con otro aviso, probablemente el mismo departamento publicado por varias inmobiliarias. Si una copia queda en entrenamiento y otra en prueba, el modelo "ya vio" la respuesta. Por eso los grupos se arman de forma que los avisos con la misma dirección y superficie caigan siempre en el mismo grupo. El error se reporta como error porcentual absoluto mediano y se compara contra una referencia simple, la mediana de precio por m² de la sub-zona: si el modelo no la mejora, las características no están aportando información.

**Predicción no es pronóstico.** Estimar cuánto valdría hoy un departamento que no observamos es una predicción válida: se predice un valor actual que no se ve. Eso no es un pronóstico de cómo van a evolucionar los precios en el tiempo. Este trabajo hace lo primero. Con una sola foto del mercado no hay forma de anticipar ni de validar la evolución de precios, y ninguna conclusión del análisis debe leerse como una proyección de precios futuros.

La pregunta P4 tampoco es un pronóstico de precios. Usa un segundo relevamiento como validación fuera del período: si los avisos marcados hoy salen del portal o bajan su precio más que sus comparables, la señal capta algo real del mercado; si se comportan igual que el resto, la brecha era ruido. Esta validación es más exigente que la de 5 grupos, porque mide el resultado contra lo que efectivamente pasó y no contra datos del mismo momento. Las definiciones de los tres párrafos anteriores aplican a P1, P2 y P3. Para P4, la variable objetivo es si el aviso sigue publicado y a qué precio, y se evalúa con la información del primer relevamiento.

## Parte 3: qué NO mide el análisis

Un precio atípicamente bajo frente a sus comparables no prueba una oportunidad económica sin mirar costos, estado, liquidez y riesgo. El análisis compara precios publicados con características declaradas, y deja afuera todo lo que sigue. Los puntos están ordenados según esos cuatro ejes: estado (estado del inmueble, errores de carga), costos (entrada y refacción), liquidez (tiempo de venta, precio de cierre) y riesgo (situación legal, entorno, riesgo de mercado). Cada punto es un paso que el analista tiene que verificar antes de proponer una compra.

- **Estado del inmueble.** Las características dicen qué hay, no en qué condiciones está. Un departamento a refaccionar se publica más barato con razón. El dataset no tiene una variable confiable de estado. Se verifica con fotos, visita e inspección técnica (humedad, instalaciones, estructura).
- **Costos de entrada y de refacción.** Escritura, impuestos, honorarios y comisión inmobiliaria se suman al precio, y la refacción puede comerse toda la brecha. No están en los avisos. Se verifica con un presupuesto de obra y un cálculo de costo total de adquisición antes de comparar contra el precio esperado.
- **Situación legal y dominial.** Sucesiones, embargos, inhibiciones, inmuebles ocupados o deudas de expensas bajan el precio y no se ven en el aviso. Se verifica con informe de dominio, certificado de deuda de expensas y revisión del escribano.
- **Tiempo de venta y liquidez.** Con una sola foto no sabemos cuánto tarda en venderse cada aviso. "Bajó de precio" es apenas un indicio de vendedor con apuro o de aviso sobrevaluado. Se verifica con la antigüedad del aviso en el portal y con el volumen de operaciones de la zona; a futuro, repitiendo el scraping.
- **Precio real de cierre.** Solo vemos el precio publicado, y en el mercado argentino se negocia hacia abajo. Una brecha de 10% puede desaparecer si los comparables cierran más abajo de lo que publican. Se verifica consultando operaciones cerradas con tasadores o inmobiliarias de la zona.
- **Errores de carga.** Una superficie mal cargada o un precio con un dígito de menos generan una brecha enorme que no existe. Son el falso positivo más probable. Se verifica leyendo el aviso completo antes de cualquier otro paso.
- **Entorno inmediato.** Ruido, vista, seguridad de la cuadra o un frente a una avenida no están en el dataset y pueden explicar el precio. Se verifica con la visita y con Street View.
- **Riesgo de mercado.** El análisis es una foto: no dice si los precios de la zona van a subir o bajar, ni cómo afectan la macroeconomía, el acceso al crédito o los cambios regulatorios al valor de salida. Comprar barato respecto de los comparables no protege si toda la zona cae. Se evalúa con el contexto del mercado argentino (sección de contexto del README) y diversificando entre zonas.

### Borrador de regla de decisión

1. **Presupuesto.** Solo entran avisos cuyo costo total (precio, costos de entrada y refacción estimada) no supere el ticket máximo por unidad que defina el fondo.
2. **Señal suficiente.** La brecha de precio debe superar con margen el error de estimación de su sub-zona (por ejemplo, el doble del error mediano), y el aviso debe tener una completitud mínima para que su precio esperado sea confiable.
3. **Liquidez.** Se priorizan sub-zonas con suficientes avisos comparables, y un aviso con baja de precio reciente se trata como indicio a confirmar, no como ventaja.
4. **Tolerancia al riesgo.** Cualquier problema legal o dominial descarta el aviso; un problema de estado no descarta pero obliga a recalcular la brecha con el costo de refacción.
5. **Elección.** Entre los que pasan los filtros, se ordena por brecha de precio ajustada por ubicación, y el comité decide sobre los primeros del ranking después de la verificación de la Parte 3.

Los valores concretos (ticket máximo, margen sobre el error, completitud mínima) los fija el fondo y se calibran con los resultados de la validación.
