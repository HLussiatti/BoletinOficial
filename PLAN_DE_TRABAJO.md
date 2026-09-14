**Plan de trabajo: seguimiento diario de normativa relevante para EPESF**

Revisión realizada el 11 de septiembre de 2026 sobre el proyecto local `C:\Dev\epe_boletin_oficial`. Plan actualizado con las definiciones del usuario. Último commit observado en la revisión inicial: `37b3e6a`, del 3 de octubre de 2025.

Repositorio oficial: [HLussiatti/BoletinOficial](https://github.com/HLussiatti/BoletinOficial). Se verificó mediante el conector de GitHub que existe, su rama predeterminada es `main` y su dirección coincide con el remoto `origin` local. El desarrollo se realizará localmente y los cambios se subirán a ese repositorio al cierre de la jornada, siguiendo el procedimiento de cierre definido más adelante.

El proyecto tiene un prototipo aprovechable de consulta al Boletín Oficial de la República Argentina (BORA), extracción de avisos, descarga de PDF y almacenamiento en Excel. La evidencia confirma descargas previas, pero el estado actual no permite una ejecución diaria completa y confiable. Faltan la selección específica para EPESF, los resúmenes integrados, el correo y la operación programada.

El objetivo es producir un correo diario con las novedades nacionales del sector eléctrico, sus documentos y un resumen verificable de los fundamentos y de la parte dispositiva en relación con EPESF. Se mantendrá una base de datos consultable que permita recuperar fallas y evitar envíos repetidos. La operación prevista es local en esta máquina, antes de las 06:00, y la aplicación deberá poder instalarse en otra computadora Windows.

El código artesanal y los notebooks existentes documentan la exploración anterior. No condicionan la arquitectura ni es necesario repararlos o reutilizarlos: se podrá desarrollar una implementación nueva y conservar únicamente lo que aporte valor comprobado. Los notebooks serán opcionales para experimentación; la consulta de resultados formará parte de la aplicación. Excel tampoco es un requisito: se reemplazará como almacenamiento operativo por una base de datos con una forma accesible de consultar sus registros.

**1. Estado comprobado del proyecto**

| Necesidad | Avance observado | Trabajo pendiente |
|---|---|---|
| Consultar el boletín diariamente | Hay funciones HTTP y un notebook que recorre fechas. Sólo se consulta BORA. | Corregir ejecución, validar acceso actual, recuperar fechas pendientes y configurar el programador. |
| Detectar normativa de energía eléctrica y EPESF | El notebook usa la palabra `energía`; el parser extrae organismo, identificación, fecha y enlace. | Implementar cobertura nacional del sector eléctrico y evaluar pertinencia. Santa Fe queda para una etapa futura. |
| Descargar documentos identificados | Existen siete PDF de publicaciones del 28 al 30 de mayo de 2025; los siete pudieron abrirse y extraerse como texto. | Reactivar su integración, identificar tipo/número/año/organismo, validar archivos, contemplar anexos y evitar colisiones. |
| Resumir considerandos y parte dispositiva | Hay `NLP.py` y experimentos comentados de extracción y resumen en el notebook. | Procesar textos completos en español, contemplar distintos tipos de norma, enfocar EPESF y verificar referencias. |
| Registrar lo procesado | Existen funciones de comparación y guardado en Excel. | El Excel actual tiene ocho columnas y cero registros. Hace falta persistir estados de descarga, análisis y entrega. |
| Enviar correo al grupo definido | No se encontró implementación en los archivos revisados. | Configurar remitente, destinatarios, adjuntos, plantilla y seguimiento de envíos. |
| Operación y mantenimiento | Hay un log con 67 errores históricos de conexión, del 6 de junio de 2025. | Reintentos acotados, alertas, métricas, pruebas y manual de operación. |

El archivo [README.md](C:/Dev/epe_boletin_oficial/README.md) sólo contiene el título del proyecto. No se encontraron pruebas automatizadas, un comando que integre el proceso completo ni configuración de programación dentro del repositorio. No se inspeccionó el Programador de tareas del equipo, por lo que esta observación no descarta tareas creadas externamente.

**2. Hallazgos del prototipo y requisitos para la nueva implementación**

Esta tabla conserva el diagnóstico como antecedente y como fuente de casos de prueba. Las soluciones pueden implementarse con código nuevo; no constituyen una obligación de corregir o mantener los módulos y notebooks originales.

| Prioridad | Hallazgo y evidencia | Consecuencia | Corrección propuesta |
|---|---|---|---|
| Crítica | [scrapper.py:19](C:/Dev/epe_boletin_oficial/scrapper.py:19) llama a `search_avisos` antes de definirla. Se reprodujo el `NameError` al importar. | El notebook no puede iniciar desde una sesión limpia. | Quitar la ejecución al importar y colocar la entrada del programa en un comando explícito. |
| Crítica | [app.ipynb:172](C:/Dev/epe_boletin_oficial/app.ipynb:172) compara `fecha`, pero incrementa `fecha_desde`; un `break` aparece antes de procesar la respuesta. | El bucle no avanza y el procesamiento queda inaccesible en la ruta exitosa. | Usar un único iterador de fechas y eliminar las interrupciones de depuración. |
| Crítica | [app.ipynb:54](C:/Dev/epe_boletin_oficial/app.ipynb:54) vacía el historial cargado en memoria. | La comparación pierde las publicaciones previas; un guardado posterior puede reemplazar el historial por sólo lo nuevo. | Conservar el historial e incorporar persistencia transaccional. |
| Alta | [app.ipynb:41](C:/Dev/epe_boletin_oficial/app.ipynb:41) reemplaza las fechas actuales por el 5 de junio de 2025. | No se buscan las novedades del día. | Fechas parametrizadas y recuperación desde el último período consultado correctamente. |
| Alta | [scrapper.py:65](C:/Dev/epe_boletin_oficial/scrapper.py:65) declara un formulario, pero usa `json=payload`. La página queda fija en 1. | El formato de solicitud es inconsistente y no se recorren resultados adicionales. | Validar el contrato vigente del sitio, serializar correctamente y recorrer toda la paginación. La diferencia entre `data` y `json` está documentada por [Requests](https://requests.readthedocs.io/en/latest/user/quickstart/#more-complicated-post-requests). |
| Alta | [functions.py:23](C:/Dev/epe_boletin_oficial/functions.py:23) rechaza una lista vacía de resultados. Se reprodujo el `ValueError`. El notebook tampoco inicializa siempre `df_nuevos_avisos`. | Un día sin novedades puede terminar como error. | Representar el resultado vacío con un esquema estable y distinguirlo de una consulta fallida. |
| Alta | [app.ipynb:486](C:/Dev/epe_boletin_oficial/app.ipynb:486) guarda los avisos antes de completar las etapas posteriores, que están comentadas. | Una norma podría quedar registrada sin documento, resumen o entrega; la deduplicación podría excluirla de un nuevo intento. | Separar estados y reintentar las etapas pendientes. |
| Alta | [NLP.py:25](C:/Dev/epe_boletin_oficial/NLP.py:25) conserva sólo los primeros 4.000 caracteres. | Se pueden perder artículos y decisiones completos. | Extraer la totalidad y segmentar por secciones y artículos, conservando el vínculo con las páginas. |
| Alta | [NLP.py:7](C:/Dev/epe_boletin_oficial/NLP.py:7) inicializa BART al importar; su ficha describe entrenamiento en inglés y ajuste sobre CNN/DailyMail. | No hay evidencia de calidad suficiente para el resumen normativo en español; cargar el módulo también carga el modelo. | Evaluar un modelo apto para español, inicializarlo sólo cuando se necesite y medir fidelidad sobre ejemplos reales. Fuente: [ficha de BART](https://huggingface.co/facebook/bart-large-cnn). |
| Media | [scrapper_pdf.py:26](C:/Dev/epe_boletin_oficial/scrapper_pdf.py:26) usa referencia y fecha como nombre; [obtener_detalles.py:29](C:/Dev/epe_boletin_oficial/obtener_detalles.py:29) usa el texto recibido sin saneamiento. | Barras y otros caracteres pueden producir rutas inválidas; referencias genéricas pueden colisionar. | Nombres normalizados con jurisdicción, organismo, tipo, número, año e identificador de publicación. |
| Media | La descarga y la obtención de detalles no fijan tiempos máximos; se acepta un archivo existente sin verificarlo. | La ejecución puede quedar esperando o reutilizar documentos incompletos. | Límites de tiempo, validación de PDF, escritura temporal y comprobación de integridad. |
| Media | `NLP.py` importa `fitz`, pero `PyMuPDF` no figura en [requirements.txt](C:/Dev/epe_boletin_oficial/requirements.txt). Las dependencias incluyen muchas herramientas de exploración. | Instalar lo declarado no garantiza reproducir el resumen. | Definir dependencias de ejecución y desarrollo y verificar una instalación limpia. |

La lectura de los PDF aporta dos casos útiles para las futuras pruebas: un aviso oficial sin encabezados `CONSIDERANDO`/`RESUELVE`, y una resolución cuyo `RESUELVE` aparece después del carácter 8.000. El sistema debe soportar ambas situaciones. Archivo del segundo caso: [Resolución 165/2025](<C:/Dev/epe_boletin_oficial/pdfs/Resolución 165_2025_20250529.pdf>).

**3. Alcance confirmado y reglas de selección**

La primera versión cubrirá exclusivamente el **Boletín Oficial de la República Argentina**, con foco en normativa del sector eléctrico: leyes, decretos, resoluciones, disposiciones, decisiones administrativas y avisos oficiales pertinentes. Se consultará la Primera Sección y los suplementos correspondientes. La [búsqueda avanzada del BORA](https://www.boletinoficial.gob.ar/busquedaAvanzada/primera) permite filtrar texto, número, año y fechas.

**El Boletín Provincial de Santa Fe queda fuera de esta entrega.** La estructura permitirá incorporar otra fuente posteriormente, pero esa integración no será una dependencia, una condición de aceptación ni parte del esfuerzo estimado actual. Las menciones a Santa Fe o EPESF se seguirán buscando dentro de las publicaciones nacionales.

Se incluirán avisos oficiales sobre el mercado eléctrico aunque no tengan número de resolución. No se incorporará un seguimiento general de licitaciones, avisos judiciales, materias tributarias o laborales, ni de otras ramas energéticas: sólo se considerarán cuando formen parte de un acto con relación concreta con el sector eléctrico. Las coincidencias genéricas con `energía` no serán suficientes.

La recolección debe priorizar la cobertura completa de las secciones acordadas por fecha. Si una fuente obliga a depender de búsquedas, se usarán consultas amplias y se contrastarán con el índice o edición completa. Buscar sólo `energía` puede omitir normas relevantes y traer coincidencias ajenas al objetivo.

La clasificación propuesta tendrá cuatro resultados: mención directa a EPESF, impacto sectorial potencial, no pertinente y requiere revisión. La pertinencia debe evaluarse sobre el texto completo y los anexos disponibles, no sólo sobre el título. Una norma general puede interesar a EPESF sin nombrarla.

El vocabulario inicial incluirá `EPE`, `EPESF`, `E.P.E.`, `Empresa Provincial de la Energía`, `Santa Fe`, energía eléctrica, distribución, transporte, generación, tarifas, subsidios, mercado eléctrico mayorista, CAMMESA, usuarios y generación distribuida. Se normalizarán mayúsculas y tildes, se controlarán siglas ambiguas y se mantendrá configurable el listado de organismos, incluidas sus denominaciones históricas. La coincidencia de una palabra será un indicio, no una conclusión de aplicabilidad.

**4. Diseño funcional propuesto**

Ejecución programada → consulta de períodos pendientes → recuperación de publicaciones → identificación y almacenamiento → lectura completa y clasificación → resumen verificable → preparación de correo y adjuntos → envío y registro del resultado.

Se propone una aplicación modular en Python, con libertad para reconstruir recolector, almacenamiento, clasificación, resumen y correo. Un único comando ejecutará el proceso con fechas configurables y un modo de simulación que genere documentos y un correo `.eml` sin enviarlo. La aplicación incluirá consulta de resultados y estado de ejecución; no requerirá abrir notebooks ni ejecutar celdas manualmente. Los archivos originales se conservarán como antecedente en el historial Git, sin condicionar la implementación nueva.

Se usará SQLite como base local, con esquema versionado, transacciones y copias de respaldo. SQLite dispone de integración en Python, adecuada para registrar las etapas de este proceso sin agregar un servidor de base de datos. Fuente: [documentación de sqlite3](https://docs.python.org/3/library/sqlite3.html). Excel no será necesario para operar; una exportación CSV permitirá llevar resultados a otras herramientas.

La base será consultable desde una interfaz local sencilla, accesible desde un acceso directo de la aplicación y limitada a esta computadora. Permitirá buscar por texto y filtrar por fecha de publicación, tipo y número de norma, organismo, relevancia para EPESF y estado de procesamiento o envío. Cada registro mostrará el resumen, sus referencias, el enlace oficial y los PDF/anexos guardados. También mostrará la última ejecución, el período cubierto y los pendientes. La aceptación incluirá consultar y exportar resultados sin escribir SQL ni usar notebooks.

Se conservarían por separado las publicaciones, las normas, los documentos y los envíos. La identidad de una publicación combinaría fuente e identificador oficial; la identidad de una norma contemplaría jurisdicción, organismo, tipo, número y año. Las rectificaciones y republicaciones se vincularían con sus antecedentes sin descartarlas como duplicados. Una huella del contenido permitiría detectar cambios sin sobrescribir evidencia anterior.

Cada etapa tendría estado propio: descubierta, documento pendiente/descargado/error, clasificación pendiente/completa, resumen pendiente/listo/revisión y entrega pendiente/enviada/error/resultado incierto. Haber encontrado una norma no equivaldría a haberla comunicado. El avance de consulta se guardaría por fuente y sólo después de recorrer correctamente el período; los documentos pendientes conservarían sus propios reintentos.

Los PDF se guardarían como originales, con anexos separados y un inventario de origen, fecha de descarga, hash y páginas. Ejemplo de nombre propuesto: `NACION_SE_Resolucion_223_2025_BORA_326046.pdf`. Si sólo existe el PDF de la edición, se conservará completo; cualquier extracto por páginas se identificará como extracto y conservará su referencia. Si no se consigue el documento, se informará la falta y quedará pendiente de recuperación.

**5. Contenido del resumen y del correo**

Cada ficha debería ocupar aproximadamente 150–250 palabras, ampliables cuando haya decisiones o plazos que no puedan omitirse:

- Identificación: tipo, número, año, organismo, jurisdicción y fechas de emisión y publicación.
- Considerandos: fundamentos relevantes para EPESF o para su actividad.
- Parte dispositiva: qué establece, dispone o modifica, con artículos concretos; conservar importes, plazos, sujetos y excepciones.
- Relación con EPESF: indicar si hay mención expresa o una posible incidencia sectorial, explicando el motivo.
- Vigencia y fechas relevantes: sólo lo sustentado en la fuente; si no se identifican, señalarlo.
- Evidencia: enlaces oficiales y referencias a artículos, páginas o párrafos; estado de anexos y eventuales faltantes.

Las leyes no siempre presentan considerandos y otros actos usan `DECRETA`, `DISPONE` o encabezados con espacios. Si una sección no existe o el texto está incompleto, la ficha lo indicará. Los PDF escaneados se derivarán a OCR cuando la extracción resulte insuficiente. Los documentos largos se segmentarán conservando contexto y cobertura; no se truncará el final.

El modelo recibirá el documento como fuente de datos y no ejecutará instrucciones contenidas en él. Se exigirá una salida estructurada para validar identificación, referencias y campos numéricos. La explicación sobre EPESF distinguirá lo expresamente establecido de las inferencias que requieren evaluación del área responsable. Se versionarán las reglas y el modelo para poder reproducir y comparar resultados.

Se adopta la Responses API de OpenAI con `gpt-5.6-terra` como modelo inicial por su equilibrio entre calidad y costo para trabajo profesional. La salida es estructurada, las solicitudes usan `store=false` y el modelo sigue siendo configurable. La credencial de API se mantiene fuera del repositorio. Antes del procesamiento histórico masivo se medirá una muestra y se estimará el consumo total; se aplicarán límites configurables y reanudación por lotes. Un modelo local podrá evaluarse más adelante como proveedor alternativo, después de medir hardware, calidad y tamaño de instalación.

El correo tendrá fecha, cantidad de novedades y una ficha por norma. Adjuntará los PDF y anexos disponibles e incluirá una versión legible de las fichas en el cuerpo. El tamaño total se medirá al generar el archivo; si excede el límite configurado, se dividirá en `.eml` numerados, manteniendo la correspondencia entre fichas y adjuntos.

El usuario inicia la preparación desde la interfaz después de aplicar los filtros. La aplicación crea el `.eml`, deja vacíos remitente y destinatarios y lo abre mediante la asociación predeterminada de Windows. El envío queda bajo control humano en el cliente instalado. No se integran API de correo, SMTP ni automatización del cliente.

**6. Etapas, entregables y condiciones de cierre**

Estimación preliminar para una persona desarrolladora con apoyo del referente de EPESF. Contempla construir una aplicación nueva, sólo para BORA, con consulta local e instalador. Los plazos presuponen acceso al sitio y disponibilidad de la cuenta institucional y del servicio de resumen; se ajustarán al validar estas integraciones.

| Etapa | Esfuerzo | Trabajo y entregable | Condición de cierre |
|---|---|---|---|
| 1. Construir la base de la aplicación | 1–2 días hábiles | Crear estructura modular, comando, configuración, modos diario/histórico/simulación y pruebas iniciales. Definir el flujo de cierre en GitHub. | Ejecutar un rango acotado desde una sesión limpia; no depender de notebooks ni provocar consultas al importar módulos. |
| 2. Implementar la recolección nacional | 2–3 días hábiles | Validar BORA; cubrir identificación, paginación, suplementos, respuestas fallidas y descargas con anexos. Guardar muestras desde 2025. | Comparar fechas conocidas contra las publicaciones oficiales y demostrar que no faltan páginas de resultados ni se confunde error con ausencia de novedades. |
| 3. Crear la base consultable | 3–4 días hábiles | Incorporar SQLite, estados, integridad de archivos, respaldo e interfaz local de búsqueda, detalle y exportación. Inventariar los PDF existentes como muestras; no exigir migración del Excel vacío. | Consultar normas, resúmenes y documentos desde la interfaz; repetir ejecuciones sin duplicados y recuperar una etapa interrumpida. |
| 4. Construir y evaluar los resúmenes | 3–4 días hábiles | Clasificación eléctrica, separación de secciones, OCR cuando haga falta, integración de API y resumen en español con referencias. Registrar consumo y tiempos. | Aprobar una muestra representativa con un referente de EPESF; ausencia de números, obligaciones o fechas inventados y cobertura de los artículos relevantes. |
| 5. Integrar correo y operación temprana | 2–3 días hábiles | Preparar `.eml` desde la vista filtrada, abrirlo en el cliente predeterminado y programar la recolección a las 05:30. | Validar el contenido, los adjuntos y la apertura en los clientes instalados; medir el tiempo del ciclo diario respecto de las 06:00. |
| 6. Crear el instalador Windows | 2–3 días hábiles | Empaquetar aplicación y dependencias, configuración inicial, accesos directos, tarea programada, actualización y desinstalación. | Instalar y ejecutar en otro equipo o entorno Windows limpio, consultar la base y conservar datos al actualizar. |
| 7. Validar históricos y documentar | 2–3 días hábiles de preparación y análisis | Preparar y supervisar el procesamiento desde el 01/01/2025, evaluar muestras, probar respaldo/restauración y entregar manual. | Todo el período tiene cobertura registrada o pendientes explícitos; no hay huecos silenciosos ni envío masivo del histórico. Una persona distinta puede operar y recuperar el sistema. |

Total orientativo actualizado: **15–22 días hábiles de desarrollo**, más un **piloto de 10 días hábiles** con comparación manual de resultados. La reducción a una fuente se compensa con el alcance nuevo de consulta local, instalador y validación histórica. El tiempo de ejecución del histórico y su costo de API se estimarán tras medir volumen, límites de acceso y duración de una muestra; no están garantizados dentro de los 2–3 días de preparación y análisis de la última etapa.

El piloto permitirá medir cobertura, falsos positivos, calidad del resumen, duración, disponibilidad de la edición antes de las 06:00 y consumo del servicio elegido. La ausencia de edición a esa hora quedará registrada para decidir si conviene cambiar el horario; no se interpretará automáticamente como ausencia de normativa pertinente.

**7. Operación diaria y pruebas de aceptación**

La operación permanente se diseñará para esta máquina Windows. Se utilizará el Programador de tareas con cuenta de ejecución, ejecutable y directorio de trabajo explícitos, registro de resultados y recuperación de una ejecución omitida. Fuente: [documentación de Microsoft](https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page). No se requiere un servidor externo para esta entrega.

El horario inicial propuesto es **05:30 todos los días**, hora de Buenos Aires (`America/Argentina/Buenos_Aires`), para cumplir el requisito de correr antes de las 06:00. Se medirá la duración para procurar que el informe disponible también quede preparado antes de esa hora; el inicio y la finalización se registrarán por separado. Si el boletín aún no está publicado, se guardará ese estado y luego se revisará el horario con la evidencia del piloto. No se incorpora por defecto una segunda ejecución más tarde. La programación todavía no está instalada.

La máquina deberá tener conectividad y estar encendida o en un estado de suspensión desde el que pueda reanudarse con la configuración disponible. Se comprobarán las condiciones reales de energía, sesión y correo: no se supondrá que la aplicación puede arrancar una computadora completamente apagada. Si la ejecución no ocurre, se recuperará al volver a estar disponible y quedará identificada como tardía. El procesamiento histórico será independiente y no deberá bloquear el ciclo diario ni competir por el envío de correos.

Cada ejecución recuperará el período desde el último avance exitoso y revisará además una ventana de solapamiento, inicialmente de siete días, para detectar incorporaciones o cambios recientes. La recuperación de una interrupción prolongada no quedará limitada a esos siete días. Habrá un bloqueo para evitar ejecuciones simultáneas.

Se distinguirán cuatro resultados: novedades pertinentes, consulta completa sin novedades pertinentes, edición aún no disponible y consulta incompleta/fallida. Propongo guardar todos los resultados y enviar al grupo sólo novedades; los fallos persistentes se comunicarían al responsable operativo. La política de correo sin novedades queda por definir con EPESF.

Antes de la producción deberán verificarse estos casos:

- Búsqueda vacía, varias páginas, edición principal y suplementos, y una publicación recuperada por más de una palabra.
- Norma explícita sobre EPESF y norma sectorial pertinente que no la nombre; coincidencias ajenas al objetivo.
- Ley sin considerandos, disposición, aviso oficial, resolución larga y encabezados con variantes de formato.
- PDF escaneado, inválido, incompleto y norma con anexos publicados por separado.
- Caída de una fuente, publicación tardía, días sin edición y recuperación tras varios días sin ejecución.
- Reejecución del mismo período, interrupción entre etapas, cambio de documento y republicación.
- Rechazo de correo, destinatario rechazado, adjuntos que exceden el límite y resultado de envío incierto.
- Restauración del historial y los documentos a partir de un respaldo.
- Consulta por filtros, apertura de PDF y exportación sin conocimientos de SQL ni notebooks.
- Instalación limpia, actualización con datos existentes, traslado a otra computadora y ejecución a las 05:30 con sesión bloqueada.
- Períodos históricos desde enero de 2025, recuperación por lotes y exclusión de ese histórico del correo diario.

La muestra de evaluación debe tener publicaciones nacionales pertinentes y no pertinentes, distribuidas desde el 01/01/2025 hasta la fecha de ejecución y seleccionadas y etiquetadas por una persona del área. Como criterio inicial propongo detectar el 100 % de los casos explícitos de EPESF de esa muestra, revisar las omisiones sectoriales y exigir cero afirmaciones sin respaldo en las fichas aprobadas. Cumplirlo sobre una muestra no equivale a garantizar cobertura universal; el piloto deberá contrastar también las ediciones completas.

**8. Validación histórica desde el 01/01/2025**

La validación comenzará el **1 de enero de 2025**, inclusive, y llegará hasta la fecha de ejecución. Se usará la fecha de publicación para recorrer el período; se conservará por separado la fecha de emisión de cada norma.

El trabajo histórico se organizará en lotes reanudables, inicialmente por mes. Primero se validarán algunas fechas y documentos representativos; después se recorrerá todo el intervalo y se identificarán las publicaciones del sector eléctrico, descargando sus documentos y elaborando sus resúmenes. Se registrarán por período las ediciones consultadas, los resultados evaluados, los documentos obtenidos, los resúmenes listos y los errores pendientes. Los días sin edición se diferenciarán de las consultas fallidas.

La base resultante quedará disponible para consulta. La evaluación humana se hará sobre una muestra estratificada por fecha, organismo y tipo de acto, incluyendo tanto positivos como publicaciones descartadas para detectar omisiones. Se informarán cobertura técnica, precisión de la selección, omisiones conocidas y calidad de las fichas como resultados distintos.

El modo histórico no enviará el acumulado a los destinatarios del boletín diario. Al activar la operación se establecerá una fecha de corte de notificaciones y los registros históricos quedarán identificados como tales, sin marcarlos falsamente como enviados. La deduplicación y el seguimiento de estados permitirán reanudar el procesamiento sin volver a descargar o resumir lo ya completado, salvo cambios de contenido o una regeneración explícita.

**9. Instalador, actualización y traslado**

Se entregará un instalador Windows versionado, con la aplicación y las dependencias necesarias para que el usuario no tenga que instalar Python ni bibliotecas manualmente. El empaquetado concreto se elegirá durante la implementación y se probará en un entorno limpio. Se incluirán accesos directos para abrir la consulta local y ejecutar una comprobación manual.

La configuración inicial permitirá seleccionar la carpeta de datos, configurar el servicio de resumen, el correo y los destinatarios, comprobar conexiones y configurar el horario. El registro de la tarea programada se realizará una vez completada y validada la configuración; no se distribuirán credenciales personales dentro del instalador.

La base, los PDF, los resúmenes, la configuración y los logs se almacenarán fuera de los archivos reemplazables de la aplicación. Las actualizaciones harán respaldo previo y migraciones de esquema cuando correspondan. La desinstalación preservará los datos por defecto y retirará la tarea programada asociada a esa instalación.

El traslado a otra computadora incluirá copia y restauración del historial y documentos, nueva configuración de credenciales y prueba del correo. Se desactivará la programación en el equipo anterior cuando se transfiera la operación, para evitar que dos instalaciones envíen el mismo boletín. Instalar en otro equipo no implica compartir una única base SQLite por red ni habilitar varias máquinas remitentes simultáneas.

**10. Trabajo con GitHub y cierre diario**

El repositorio de referencia será [HLussiatti/BoletinOficial](https://github.com/HLussiatti/BoletinOficial), actualmente con rama predeterminada `main`. Los cambios se trabajarán y validarán localmente durante la jornada. Cuando se utilicen ramas de trabajo, se nombrarán con el prefijo `codex/` y se registrará cuál contiene el trabajo del día.

El procedimiento de cierre de jornada será: revisar los cambios, ejecutar las comprobaciones correspondientes, actualizar la documentación y el estado de pendientes, realizar commits con mensajes descriptivos, sincronizar de forma segura con el remoto y subir los commits al repositorio. Se comprobará el resultado del push y se dejará constancia de la rama y el commit subidos. Si el remoto contiene cambios nuevos, se resolverá su integración sin sobrescribir trabajo ajeno ni usar un push forzado como rutina.

La sincronización se hará como parte del cierre de trabajo de la sesión al finalizar el día, no por cada edición. Para que ocurra debe ejecutarse mientras la sesión o el proceso de cierre aún esté disponible; este plan no presupone una subida autónoma después de cerrar la aplicación o apagar la máquina. Esta actualización del plan se conserva localmente para ese cierre y no dispara una publicación inmediata.

El repositorio versionará código, pruebas, documentación, configuración de ejemplo y los scripts de construcción del instalador. Los datos operativos, documentos descargados, logs, credenciales y listas de destinatarios quedarán fuera del código versionado. Las versiones distribuibles se generarán desde una revisión identificable del repositorio y tendrán sus instrucciones de instalación y actualización. El respaldo de la base y los PDF tendrá un procedimiento propio, independiente del push de código.

**11. Decisiones confirmadas y datos operativos por completar**

| Definición | Decisión actual o dato restante | Estado |
|---|---|---|
| Repositorio | `HLussiatti/BoletinOficial`; subida al cierre de jornada. | Confirmado. |
| Código y notebooks | Libertad para reconstruir; notebooks opcionales y fuera de la operación obligatoria. | Confirmado. |
| Fuentes | BORA; Santa Fe en una etapa futura. | Confirmado. |
| Materias | Sólo sector eléctrico: leyes, decretos, resoluciones, disposiciones y avisos pertinentes, entre otros actos. | Confirmado. |
| Base consultable | SQLite e interfaz local con búsqueda, filtros, documentos y exportación; Excel no es requisito. | Requisito confirmado; diseño propuesto. |
| Correo | Creación manual de `.eml` desde la vista filtrada y apertura en el cliente predeterminado. Remitente y destinatarios los completa el usuario. | Confirmado; no habrá envío automático ni SMTP. |
| Infraestructura | Operación local en esta máquina; instalador para otras computadoras Windows. | Confirmado; verificar energía, conexión y sesión. |
| Horario | Antes de las 06:00; propuesta inicial 05:30, hora de Buenos Aires. | Franja confirmada; ajuste según piloto. |
| Ausencia de novedades y fallos | Propuesta: registrar todas las ejecuciones, correo al grupo sólo con novedades y fallos persistentes al responsable operativo. | Política y contacto por precisar. |
| Servicio de resumen | Responses API con `gpt-5.6-terra`, salida estructurada y `store=false`. Obtener credencial de API y configurar límites de consumo. | Modelo definido; credencial y validación real pendientes. |
| Validación | Desde el 01/01/2025 inclusive hasta la fecha de ejecución. | Confirmado. |
| Inicio del correo diario | Definir el corte al activar producción, separándolo de la carga histórica. | Se establece en la puesta en marcha. |
| Custodia | Precisar responsable, carpeta de datos, retención y destino de respaldos. | Datos operativos por completar. |

Los datos operativos pendientes se resolverán en las etapas que los necesiten. No impiden comenzar la aplicación, el recolector nacional, el esquema de datos y las pruebas históricas. La selección de bibliotecas, arquitectura interna y herramientas de resumen queda a criterio técnico del desarrollo dentro de los requisitos anteriores.

**12. Alcance de la revisión y de esta actualización**

Se revisaron los seis archivos Python, las celdas y salidas guardadas del notebook, el esquema y las filas del Excel, el log, los requisitos y la documentación. Se verificó sintaxis de los seis módulos; se reprodujeron la falla de importación y el error ante una lista vacía con la red bloqueada durante esas pruebas. Se abrieron y extrajeron los siete PDF locales. Las verificaciones de comportamiento se ejecutaron con el Python 3.12.1 instalado en el equipo, sin reconstruir el entorno virtual ni instalar las dependencias declaradas.

Se consultaron las páginas oficiales indicadas para comprobar las fuentes disponibles y sustentar las recomendaciones. No se ejecutó el proceso completo ni se validaron de extremo a extremo los endpoints POST de búsqueda y descarga actuales. Los errores históricos de conexión no prueban por sí solos que esos endpoints estén caídos hoy. Tampoco se ejecutaron modelos de resumen, se enviaron correos o se crearon tareas programadas.

El entregable de esta sesión es el diagnóstico y plan actualizado, no la implementación del sistema. La primera entrega de desarrollo será una ejecución nueva sobre un período acotado del BORA desde 2025, con documentos almacenados y estados persistidos. Las siguientes incorporarán consulta local, resúmenes, correo institucional, horario temprano e instalador. La cobertura provincial se abordará en un proyecto de ampliación posterior.
