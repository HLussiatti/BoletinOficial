# Estado de implementación

Actualizado el 11 de septiembre de 2026. Rama de trabajo:
`codex/base-recoleccion-bora`.

## Hito actual

La base correspondiente a la etapa 1 está implementada y se inició la etapa 2:

- paquete Python instalable y comando único `epe-boletin`;
- modos diario, histórico y simulación, con rango de fechas;
- base SQLite versionada con ejecuciones, cobertura, publicaciones y documentos;
- bloqueo contra ejecuciones simultáneas;
- reintentos HTTP acotados, con espera creciente, tiempo máximo configurable y
  registro persistente de las fallas;
- lectura de la Primera Sección por edición completa, incluida la paginación;
- control de la cantidad anunciada por el índice antes de marcar la cobertura;
- suplementos incorporados en el mismo índice, diferenciados por categoría, y
  registro por fecha de la existencia de suplemento;
- clasificación preliminar en los cuatro estados acordados;
- reglas de selección editables en JSON, con versión persistida y reclasificación
  de registros existentes sin nuevas descargas;
- descarga atómica, validación básica y huella SHA-256 de los PDF;
- extracción completa de texto y registro de páginas y estado de extracción;
- identificación interna de considerandos, parte dispositiva y artículos con sus
  páginas de origen, como respaldo para generar resúmenes conceptuales;
- almacenamiento versionado de resúmenes conceptuales, vinculado a la huella de
  los documentos utilizados;
- integración preparada con la Responses API mediante salida estructurada, consumo
  registrado y credencial tomada del entorno;
- generación de boletines `.eml` en modo simulación, con cuerpo de texto y HTML,
  PDF y anexos, y división automática por límite de tamaño;
- recuperación diaria desde la última cobertura completa, con siete días de
  solapamiento configurables;
- respaldo ZIP transaccional de SQLite, documentos y reglas, con manifiesto y
  huellas SHA-256;
- scripts de Windows preparados para la ejecución diaria a las 05:30, sin haber
  instalado todavía la tarea programada.
- descubrimiento, descarga y almacenamiento separado de anexos;
- consulta de estado y exportación CSV;
- pruebas locales sin red sobre la edición del 29/05/2025.
- pruebas de edición ausente, respuestas HTTP transitorias, agotamiento de
  reintentos y rechazo de PDF inválidos.
- muestra reproducible del 30/05/2025 con suplemento y prueba de un rango de dos
  días que registra 153 publicaciones sin omisiones.

La prueba de aceptación provisional procesó 90 publicaciones y una coincidencia
sectorial. Dos ejecuciones consecutivas mantuvieron 90 registros, lo que verifica
la deduplicación por identificador oficial para esa muestra.

El 11 de septiembre de 2026 se realizó además una validación real de la edición del
día. Se registraron 91 publicaciones, se descargaron cuatro candidatos sectoriales
y un anexo para evaluar el texto completo, y quedaron seleccionadas las
Resoluciones 238/2026 y 239/2026. Los dos avisos fueron descartados con la regla de
negocio ajustada. Una ejecución posterior no volvió a descargar archivos. El
detalle está en `VALIDACION_2026-09-11.md`.

La base de esa validación se migró al esquema 4. La reclasificación con las reglas
`2026-09-11.1` mantuvo exactamente 89 publicaciones descartadas y las Resoluciones
238/2026 y 239/2026 como los dos resultados de impacto sectorial potencial. Los
cinco PDF existentes se procesaron sin errores; las dos resoluciones quedaron con
referencias de página y los documentos sin estructura normativa se marcaron como
no aplicables.

Los dos resúmenes conceptuales aprobados se importaron como revisión humana. Con
ellos se generó un correo de simulación de 727.692 bytes que contiene las dos
publicaciones y tres adjuntos. No se realizó ningún envío.

El respaldo de la validación contiene la base, los cinco PDF y la configuración de
reglas. Se verificaron las siete huellas del manifiesto contra el contenido del ZIP.

## Próximo trabajo

1. Construir la interfaz local de consulta, filtros, detalle y apertura de PDF.
2. Validar el resumen automático con una credencial y un modelo habilitado.
3. Integrar el correo institucional, la programación de Windows y el instalador.
4. Ampliar la muestra histórica antes del procesamiento desde enero de 2025.

La instalación aislada de las dependencias declaradas se completó en `.venv`. La
validación sobre un equipo Windows limpio continúa pendiente para la etapa del
instalador.
