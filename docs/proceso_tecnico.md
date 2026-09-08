# Documentación del Proceso Técnico

## 1\. Fuente de datos elegida

La fuente principal del proyecto es **MercadoLibre Inmuebles**, la mayor plataforma de avisos inmobiliarios de Argentina. Se eligió por tres motivos: es la que mayor volumen de publicaciones concentra en CABA, presenta los datos de forma relativamente estructurada, y expone en la ficha de detalle de cada propiedad una tabla completa de características y amenities, que constituye el diferencial de este trabajo.

Antes de optar por MercadoLibre se evaluaron y descartaron otras fuentes:

- **Argenprop:** se utilizó inicialmente el scraper base provisto por la cátedra, pero la plataforma presentó bloqueos que se detallan más abajo.  
- **Zonaprop y Remax:** se consideraron como fuentes alternativas, pero Zonaprop comparte la misma protección anti-scraping que Argenprop, y Remax carga su contenido dinámicamente mediante JavaScript, lo que hubiera requerido herramientas más complejas (Selenium) sin aportar datos sustancialmente distintos a los de MercadoLibre.

## 2\. Desafíos técnicos encontrados y cómo se resolvieron

El proceso de extracción no fue lineal: se enfrentaron varios obstáculos técnicos que obligaron a iterar sobre la estrategia. Se documentan a continuación porque forman parte central del aprendizaje del proceso.

### 2.1 Bloqueo por CloudFront (error 403\) en Argenprop

Los primeros intentos de scraping sobre Argenprop devolvían un error HTTP 403 (acceso denegado). Se identificó que la plataforma utiliza **CloudFront** (el sistema anti-bot de Amazon), que bloquea las peticiones que no provienen de un navegador real.

Se probaron sucesivamente varias soluciones: rotación de *User-Agents*, uso de sesiones con cookies, la librería `cloudscraper`, y finalmente Selenium con un navegador headless. Ninguna resolvió el bloqueo de forma consistente al ejecutar el proceso desde **Google Colab**.

### 2.2 IP de datacenter vs. IP residencial

El hallazgo clave fue que CloudFront bloquea principalmente las **IPs de datacenter**, y las de Google Colab pertenecen a esa categoría. Al trasladar la ejecución del scraper a una **máquina local con IP residencial**, el bloqueo desapareció. Esta fue una lección importante: el mismo código que fallaba en la nube funcionaba correctamente ejecutado localmente. A partir de este punto, todo el scraping se realizó en local.

### 2.3 Contenido corrupto por compresión Brotli en MercadoLibre

Al migrar a MercadoLibre, apareció un problema más sutil. Las peticiones devolvían un estado HTTP 200 (correcto) y un contenido de tamaño normal, pero al parsear el HTML no se encontraba ninguna propiedad, y aparecía la advertencia "Some characters could not be decoded".

Tras un proceso de diagnóstico (verificando estado, codificación, tamaño y título de la respuesta), se identificó la causa: los *headers* de la petición solicitaban compresión **Brotli** (`Accept-Encoding: br`), pero el entorno no contaba con el decodificador correspondiente, por lo que el HTML llegaba comprimido y corrupto. La solución fue quitar `br` del `Accept-Encoding` y utilizar `response.text` en lugar de `response.content` para delegar la decodificación en la librería. Este error es especialmente engañoso porque un estado 200 sugiere que todo funciona correctamente.

### 2.4 Distinción entre emprendimientos y propiedades usadas

MercadoLibre mezcla en sus listados dos tipos de publicaciones: **emprendimientos** (proyectos en pozo, con precios y superficies expresados en rangos, del tipo "Desde US$...") y **propiedades individuales** (con precio y superficie concretos). Un primer scraper descartaba las publicaciones con la palabra "Desde", pero como los emprendimientos aparecen primero en los listados, esto producía resultados vacíos.

La solución tuvo dos partes: primero se dejó de descartar los emprendimientos, marcándolos con una columna booleana; y luego se ajustó directamente la **URL de búsqueda** aplicando el filtro de "propiedades individuales usadas" desde la propia plataforma, lo que garantizó que solo se relevaran departamentos usados con precio concreto.

### 2.5 Límite de paginación y estrategia por barrio

Se detectó que MercadoLibre limita cada búsqueda a aproximadamente 2.000 resultados (unas 42 páginas), sin importar que existan muchos más. Para superar este techo y alcanzar el volumen requerido, se adoptó una **estrategia de scraping por barrio**: en lugar de una única búsqueda general, se recorrió cada uno de los 47 barrios de CABA de forma independiente. Esto no solo permitió alcanzar casi 28.000 propiedades, sino que además garantizó una representación geográfica balanceada de toda la ciudad.

Dado el volumen y el tiempo de ejecución (el scraping con detalle de cada propiedad demandó varias horas), el proceso se organizó **por cuotas**: los barrios se dividieron en cinco grupos que se ejecutaron en sesiones separadas, cada uno guardando su propio archivo, para luego consolidarse en un dataset único. Se implementó además un guardado parcial periódico, de modo que una eventual interrupción no implicara perder el progreso.

### 2.6 Normalización de direcciones para la geocodificación

En la etapa de enriquecimiento, al geocodificar las direcciones surgió un nuevo obstáculo: cerca del 39% de las direcciones contenían la abreviatura no estándar **"Al"** (por "altura"), del tipo "Billinghurst Al 2500", que el normalizador de USIG no interpretaba. Adicionalmente, la abreviatura "Av." generaba conflictos con la lógica de limpieza.

Se desarrolló una función de limpieza que normaliza estas abreviaturas antes de geocodificar (convirtiendo "Al" en la altura correspondiente y "Av." en "Avenida"), lo que elevó la proporción de direcciones geocodificables del 87% al 94%.

## 3\. Resumen del pipeline de datos

El flujo completo de datos del proyecto se compone de las siguientes etapas:

1. **Extracción (scraping):** relevamiento de MercadoLibre Inmuebles por barrio y por cuotas, capturando datos del listado y de la ficha de detalle de cada propiedad. Resultado: 27.922 propiedades con 86 variables.  
2. **Consolidación:** unificación de los archivos de las distintas cuotas en un único dataset, con eliminación de duplicados.  
3. **Geocodificación:** conversión de las direcciones en coordenadas mediante el normalizador de USIG. Resultado: 22.912 propiedades con latitud y longitud (82% del total).  
4. **Enriquecimiento:** cálculo de la distancia de cada propiedad a la estación de subte más cercana y a los polos de centralidad (usando el dataset de BA Data), y asignación de cada propiedad a una sub-zona geográfica mediante clustering espacial. Resultado: dataset final de 93 variables.

## 4\. Limitaciones del dataset

Se documentan de forma explícita las principales limitaciones del trabajo, por rigor metodológico:

- **Precio de publicación, no de venta:** el dataset contiene el precio al que se publica cada aviso, no el precio de venta efectivo (dato no público). En consecuencia, el análisis detecta publicaciones cuyo precio es bajo respecto a sus características, lo que es una aproximación al concepto de "subvaluación" pero no equivale a él.  
    
- **Foto de un momento puntual:** los datos corresponden a un único relevamiento en el tiempo, no a una serie temporal. El análisis describe el estado del mercado en ese corte, no su evolución.  
    
- **Cobertura del geocoding:** el 18% de las propiedades no pudo geocodificarse por presentar direcciones incompletas o no normalizables. Estas propiedades se conservan en el dataset y participan del análisis a nivel barrio, pero quedan fuera del análisis espacial fino (distancias y sub-zonas).  
    
- **Truncamiento por límite de paginación:** los barrios de mayor oferta (Palermo, Belgrano, Caballito, Recoleta) quedaron limitados a aproximadamente 2.000 registros por el tope de la plataforma, lo que podría introducir un sesgo hacia las publicaciones más recientes o mejor posicionadas en esos barrios.  
    
- **Interpretación de amenities faltantes:** cuando un amenity aparece con la celda vacía, no siempre es posible distinguir si se trata de una ausencia real (la propiedad no lo tiene) o de un dato faltante (el anunciante no lo cargó). Esta distinción se abordará en la etapa de limpieza.  
    
- **Datos de entorno acotados a subte:** por el momento, la variable de accesibilidad al transporte considera únicamente la red de subte. La incorporación de tren y Metrobus queda planteada para etapas posteriores.

