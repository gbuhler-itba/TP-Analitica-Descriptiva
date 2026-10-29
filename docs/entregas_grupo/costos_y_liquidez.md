# Costos y liquidez para la regla de decisión

*Analítica Descriptiva (ITBA, 2026 C2) · PreEntrega 3 · Tarea 3*

Estos parámetros convierten la brecha de precio en una brecha neta: lo que queda después de comprar, refaccionar y negociar. Los valores se leen de `config/costos.yaml`. Cada uno tiene un rango para el análisis de sensibilidad. Fuentes consultadas el 29/10/2026. Los montos en pesos se pasaron a dólares con el MEP de la fecha de cada fuente.

## 1. Tabla de valores

| Bloque | Parámetro | Valor | Mínimo | Máximo | Unidad | Confiabilidad |
|---|---|---|---|---|---|---|
| Entrada | Honorarios de escribano (con IVA) | 2,42 | 1,21 | 2,42 | % del precio | Alta |
| Entrada | Sellos, parte del comprador | 1,35 | 1,35 | 3,50 | % del precio | Alta |
| Entrada | Comisión inmobiliaria del comprador (con IVA) | 4,84 | 3,63 | 4,84 | % del precio | Media |
| Entrada | Otros gastos de escritura | 0,15 | 0,10 | 1,23 | % del precio | Media |
| Entrada | **Total costos de entrada** | **8,76** | **6,29** | **11,99** | % del precio | Media |
| Refacción | Liviana (pintura, pisos) | 105 | 60 | 130 | USD por m² | Media |
| Refacción | Media (baño y cocina) | 330 | 240 | 510 | USD por m² | Media |
| Refacción | Integral (instalaciones) | 1.227 | 1.143 | 1.549 | USD por m² | Baja |
| Negociación | Brecha publicado-cierre | 4,79 | 4,18 | 5,14 | % | Alta |
| Liquidez | Tiempo de venta en CABA | 8,8 | 2,0 | 11,5 | meses | Media |
| Liquidez | Escrituras de compraventa por mes en CABA | 5.355 | 4.193 | 6.612 | cantidad | Alta |

**Costos de entrada.** Son números de norma o de arancel, por eso son los más firmes. El escribano sugiere 2% + IVA, con un honorario mínimo de ARS 1.980.000 (USD 1.275) que pesa en avisos de menos de USD 63.770 [1]. En la práctica se negocia entre 1% y 2% [2]. Sellos es 2,7% si el mayor valor entre precio, valuación fiscal y valor de referencia no supera ARS 226.100.000, y 3,5% si lo supera, sobre el total y no sobre el excedente [3]. Ese umbral equivale a USD 148.941 al MEP del 14/08/2026, y el 57% de nuestros avisos queda por debajo. La exención por vivienda única no aplica a un fondo. La costumbre es repartir el impuesto 50/50, pero se puede negociar. La comisión del comprador no tiene tope desde la Ley 5859 [4]. La más citada es 4% + IVA [5], y 3% es un piso negociado razonable [6]. Otros gastos: el Registro de la Propiedad cobra 1 por mil [7]. Certificados y estudio de títulos los paga el vendedor por costumbre [6]; el máximo supone que los absorbe el comprador [1]. El total central, 8,76%, cae dentro del rango de 5,5% a 12% que informa la prensa especializada [8].

**Refacción.** La liviana y la media salen del relevamiento trimestral de Reporte Inmobiliario: baño de 3,75 m² y cocina de 5,6 m² cuestan ARS 18.453.373 (USD 12.950), la pintura de un 2 ambientes ARS 3.700.000 y el pulido ARS 66.000 por m² [9][10]. Baño y cocina son un costo casi fijo por unidad, así que en USD por m² bajan con el tamaño. El rango de la media va de un 4 ambientes (95 m²) a un monoambiente (32 m²). Para el cálculo conviene usar `costo_bano_cocina_usd + liviana × m²` en lugar del valor por m². La integral es la menos confiable y se expresa con IVA, como el resto de los costos, porque el fondo no lo recupera. Sale de una sola fuente, un estudio que publica un caso real de 52 m² en CABA, convertido al MEP promedio de febrero [11]. El techo de referencia es la obra nueva, que costó USD 1.594 por m² en septiembre [12]. Antes de invertir, el analista tiene que pedir dos o tres presupuestos.

**Negociación.** El índice M² Real se calcula sobre operaciones cerradas de departamentos usados en CABA. En agosto de 2026 dio 4,79% por debajo del precio publicado, el último mes del informe de UCEMA [14]; la prensa informa 4,75% para septiembre [13], sin el informe primario. La serie mensual desde 2024 nunca bajó de 4,15%: el mínimo de 2025 fue 4,18% (febrero) [14] y el máximo, 5,14% en enero de 2026 [15]. Reemplaza al ~5% que usamos hoy, con poco cambio.

**Liquidez.** El tiempo medio de publicación en CABA fue de 263 días (8,8 meses) a fines de 2025, según el IDECBA [16]. No es tiempo de venta: incluye avisos mal tasados que nunca se venden. Un aviso bien tasado se vende en dos a cuatro meses, y los avisos activos de 5 ambientes o más llevan 349 días publicados [17]. **No se encontró el dato por zona:** las fuentes lo abren solo por ambientes (`config/costos.yaml` tiene la apertura del IDECBA). Las escrituras son el dato más sólido: 48.195 entre enero y septiembre de 2026, con un máximo de 6.612 en septiembre [18]. El mínimo es el promedio del 1er. trimestre, cálculo propio con el total del 2do. trimestre del IDECBA [19].

## 2. Qué implica para la regla

- Para que una brecha sea ganancia, primero tiene que cubrir los costos de entrada (8,76%) y la negociación al revender (4,79%). Eso todavía no incluye refacción, costos de la venta ni los meses de espera. El umbral de −25% que usamos hoy cubre esos dos costos con margen.
- En un aviso "a refaccionar", la refacción media equivale a entre 14 y 30 puntos del precio, según el tamaño (USD 240 a 510 por m² contra una mediana de USD 1.693 por m²). En un aviso "a reciclar", la integral supera la mitad del precio. Ahí la brecha de −25% no alcanza.
- La sensibilidad más importante es la refacción integral y la comisión. Sellos y escribano mueven poco.

## 3. Estado del aviso y nivel de refacción

**Problema en la marca actual.** `titulo_a_refaccionar` busca `refacc`, y eso también captura "refaccionado", que significa lo contrario. De los 381 avisos marcados, 135 (35%) dicen "refaccionado". Eso no infla el hallazgo del README de que los avisos "a refaccionar" se marcan tres veces más: lo diluye. Con la marca corregida, los "a refaccionar" o "a reciclar" se marcan más de cuatro veces más que el resto, y los "refaccionado" solos casi no se marcan (medido en la revisión del 29/10/2026). Proponemos separar las marcas así. Se evalúan en orden y gana la primera que coincide; las regex completas están en `config/costos.yaml`.

| Estado | Señal en el título | Avisos | Nivel central | Sensibilidad | Por qué |
|---|---|---|---|---|---|
| A reciclar | "a reciclar", "para reciclar", "reciclaje" | 141 | Integral | Media a integral | En el uso local, reciclar es rehacer el departamento |
| A refaccionar | "a refaccionar", "a refacc", "ideal refacción" | 111 | Media | Media a integral | Hay que hacer baño y cocina como mínimo |
| Ya reformado | "refaccionado", "reciclado", "recicl a nuevo", "refacción total" | 671 | Ninguna | Ninguna a liviana | La obra ya está hecha y el precio la incluye |
| A estrenar | "a estrenar" | 868 | Ninguna | Ninguna | Unidad nueva |
| Sin marca | Ninguna de las anteriores | 25.800 | Liviana | Ninguna a media | Un usado siempre pide pintura y pisos |

Para los 8.643 avisos sin marca con 50 años o más, conviene correr la sensibilidad con nivel media. Control de coherencia: la mediana del precio por m² es de USD 1.623 en "a reciclar" y USD 1.693 en "a refaccionar", contra USD 2.353 en "ya reformado" y USD 2.379 sin marca. La diferencia, de unos USD 700 por m², cae entre la refacción media (330) y la integral (1.014) de la tabla. Es una comparación entre zonas distintas, no un efecto medido.

## 4. Riesgo legal: palabras del título

El dataset no trae la descripción del aviso, así que solo se puede buscar en el título. Por eso las coincidencias son pocas y una ausencia no prueba nada: el analista igual tiene que pedir el informe de dominio. "Descartar" significa que el aviso no entra al ranking. "Revisar" significa que entra, con la señal visible.

| Señal | Ejemplos | Avisos | Acción | Por qué |
|---|---|---|---|---|
| Nuda propiedad | "nuda propiedad", "usufructo" | 4 | Descartar | Se compra sin derecho a usar ni alquilar hasta que muera el usufructuario. El precio es bajo por diseño: es un falso aviso atípico |
| Ocupado | "ocupado" (no "desocupado") | 0 | Descartar | Ocupación sin contrato: desalojo largo e incierto |
| Sin escritura | "sin escritura", "boleto", "cesión" (palabra entera, para no tomar "sucesiones") | 1 | Descartar | No hay título perfecto: no es apto crédito y cuesta revender |
| Parte indivisa | "parte indivisa" | 1 | Descartar | Se compra un porcentaje, no la unidad |
| En pozo | "pozo", "fideicomiso", "en construcción", "preventa" | 169 | Descartar | No es un usado terminado: riesgo de obra y precio no comparable. `\b` evita "Combate de los Pozos" |
| Sucesión | "sucesión", "tracto abreviado" | 2 | Revisar | Vende una sucesión: firman todos los herederos y suma un honorario de tracto abreviado (0,4%, mínimo ARS 960.000) [1] |
| Con inquilino | "con renta", "inquilino", "alquilado", "rentado", "renta vigente" | 201 | Revisar | No se puede refaccionar ni revender libre hasta que venza el contrato |
| Subasta | "subasta", "remate", "judicial" | 0 | Revisar | Deudas y ocupantes posibles; la escritura judicial lleva 50% de recargo en el honorario [1] |
| Crédito pendiente | "con hipoteca", "embargo", "inhibición" | 0 | Revisar | La deuda del vendedor tiene que cancelarse en la escritura. Ojo: "apto crédito hipotecario" (47 avisos) no es riesgo |
| Con financiación | "financiación", "cuotas", "anticipo" | 197 | Revisar | El precio publicado puede no ser de contado: no se compara con el resto |
| No apto crédito | "no apto crédito" | 6 | Revisar | Suele indicar papeles incompletos (final de obra, subdivisión) o mal estado. `\b` evita "Lugano apto crédito" |

Dos notas para la limpieza. Primero, de los 283 avisos de la marca actual `titulo_con_renta`, unos 80 no tienen inquilino: la mayoría es publicidad ("ideal renta", "excelente renta", renta temporaria), y también aparecen el barrio "La Imprenta", "rentabilidad" y "con o sin renta". La regex de "con inquilino" de arriba los separa y suma unos 15 que sí lo tienen y la marca actual no veía ("hoy rentado", "renta vigente"). Segundo, hay un aviso que dice "compro sucesiones": es un pedido, no una venta, y conviene sacarlo del dataset.

## Fuentes

1. Colegio de Escribanos de la Ciudad de Buenos Aires, Arancel Notarial 2026, Res. 353/26, vigente desde el 01/10/2026. https://www.colegio-escribanos.org.ar/noticias/Arancel-web.pdf
2. iProfesional, "Escriturar un inmueble en 2026" (25/05/2026). https://www.iprofesional.com/realestate/455280-escriturar-en-provincia-de-buenos-aires-cuanto-cuesta-y-que-cambia-respecto-a-caba-mayo-2026
3. Ley 6927, Ley Impositiva 2026 de la CABA, Anexo, art. 34 (B.O. 19/12/2025). https://contadoresenred.com/wp-content/uploads/2025/12/PL-FEERR-LCABA-LCABA-6927-25-ANX.pdf ; ficha oficial: https://boletinoficial.buenosaires.gob.ar/normativaba/norma/829857 . La Ley 6948 (B.O. 19/05/2026) modificó Ingresos Brutos, no Sellos.
4. Ley 2340 de la CABA, art. 11 inc. 2, texto según Ley 5859. https://garciaalonso.com.ar/?p=4813
5. Mudafy, "Gastos de comprar una propiedad en Argentina 2026" (act. 02/10/2026). https://mudafy.com.ar/guias/post/que-gastos-se-afrontan-al-comprar-una-propiedad
6. iProfesional, "Cuánto cuesta escriturar una casa". https://www.iprofesional.com/realestate/423461-cuanto-cuesta-escriturar-una-casa-2025-como-se-hace
7. Decreto 902/2024, tasa del Registro de la Propiedad Inmueble de la Capital Federal (B.O. 14/10/2024). https://www.boletinoficial.gob.ar/detalleAviso/primera/315455/20241014
8. Ámbito (11/06/2026). https://www.ambito.com/real-estate/cuales-son-los-gastos-que-pagan-comprador-y-vendedor-una-propiedad-us100000-caba-y-provincia-n6287354
9. Reporte Inmobiliario, "Costos para refaccionar departamentos" (11/05/2026). https://www.reporteinmobiliario.com/article5813-costos-para-refaccionar-departamentos
10. La Nación, con datos de Reporte Inmobiliario (11/05/2026). Convertido al MEP del 11/05/2026, ARS 1.425,02. https://www.lanacion.com.ar/propiedades/casas-y-departamentos/remodelar-el-bano-y-la-cocina-cuesta-mas-de-us10000-nid11052026/
11. RenovArqui (febrero de 2026). Convertido al MEP promedio de febrero, ARS 1.429,53 (https://indicadores.ar/cotizacion-dolar/2026-02). https://renovarqui.com/cuanto-cuesta-remodelar-un-departamento-en-buenos-aires-en-2026
12. APYMECO, Informe Mensual N° 132, citado en InfoPlatense. https://www.infoplatense.com.ar/metro-cuadrado-construccion-septiembre-2026-apymeco-fondo-pymes/
13. Índice M² Real (RE/MAX, UCEMA, Reporte Inmobiliario), septiembre de 2026, citado en iProfesional (19/10/2026). https://www.iprofesional.com/realestate/466916-cuanto-cuesta-el-metro-cuadrado-de-un-departamento-usado-en-caba
14. UCEMA, Informe M² Real agosto 2026, con la serie mensual desde 2024. https://ucema.edu.ar/sites/default/files/2026-09/Informe_M2_Real_Agosto_2026.pdf
15. Reporte Inmobiliario, "Precio real de cierre por m², enero 2026". https://www.reporteinmobiliario.com/article5775-recio-real-de-cierre-por-m%C3%82%C2%B2-%C3%82%E2%80%93-enero-2026
16. IDECBA, citado en Infobae (23/04/2026). https://www.infobae.com/economia/2026/04/23/se-acorto-el-tiempo-de-venta-de-propiedades-en-caba-cuales-son-los-inmuebles-mas-faciles-de-vender/
17. El Cronista (26/10/2026). https://www.cronista.com/negocios/el-mercado-inmobiliario-de-caba-desperto-que-conviene-hacer-si-vas-a-comprar-vender-o-alquilar-hoy/
18. Colegio de Escribanos de la Ciudad de Buenos Aires, escrituras de septiembre de 2026. https://www.colegio-escribanos.org.ar/?p=144949
19. IDECBA, Informe 2052, Dinámica del mercado de venta de departamentos, 2do. trimestre de 2026 (28/08/2026). https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2026/08/ir_2026_2052.pdf
