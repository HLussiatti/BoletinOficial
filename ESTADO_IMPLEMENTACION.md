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
- descubrimiento, descarga y almacenamiento separado de anexos;
- consulta de estado y exportación CSV;
- pruebas locales sin red sobre la edición del 29/05/2025.
- pruebas de edición ausente, respuestas HTTP transitorias, agotamiento de
  reintentos y rechazo de PDF inválidos.

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

## Próximo trabajo

1. Guardar una muestra local de una fecha con suplemento para automatizar la prueba
   del contrato ya inspeccionado en el sitio oficial.
2. Construir la interfaz local de consulta, filtros, detalle y apertura de PDF.
3. Automatizar el resumen conceptual ya validado y conservar su evidencia.
4. Ampliar las pruebas a varias fechas conocidas antes del histórico.

La instalación aislada de las dependencias declaradas se completó en `.venv`. La
validación sobre un equipo Windows limpio continúa pendiente para la etapa del
instalador.
