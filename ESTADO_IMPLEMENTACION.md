# Estado de implementación

Actualizado el 11 de septiembre de 2026. Rama de trabajo:
`codex/base-recoleccion-bora`.

## Hito actual

La base correspondiente a la etapa 1 está implementada y se inició la etapa 2:

- paquete Python instalable y comando único `epe-boletin`;
- modos diario, histórico y simulación, con rango de fechas;
- base SQLite versionada con ejecuciones, cobertura, publicaciones y documentos;
- bloqueo contra ejecuciones simultáneas;
- lectura de la Primera Sección por edición completa, incluida la paginación;
- control de la cantidad anunciada por el índice antes de marcar la cobertura;
- suplementos incorporados en el mismo índice, diferenciados por categoría, y
  registro por fecha de la existencia de suplemento;
- clasificación preliminar en los cuatro estados acordados;
- descarga atómica, validación básica y huella SHA-256 de los PDF;
- consulta de estado y exportación CSV;
- pruebas locales sin red sobre la edición del 29/05/2025.

La prueba de aceptación provisional procesó 90 publicaciones y una coincidencia
sectorial. Dos ejecuciones consecutivas mantuvieron 90 registros, lo que verifica
la deduplicación por identificador oficial para esa muestra.

## Próximo trabajo

1. Guardar una muestra local de una fecha con suplemento para automatizar la prueba
   del contrato ya inspeccionado en el sitio oficial.
2. Ejecutar una descarga real desde el flujo nuevo y contrastar hash, tamaño y
   apertura del documento.
3. Incorporar el texto completo del detalle y los anexos como documentos separados.
4. Ampliar las pruebas a varias fechas conocidas de 2025 antes del histórico.

La instalación aislada de dependencias y la validación HTTP completa quedaron
pendientes porque el acceso de terminal con red fue rechazado por el límite de uso
de la sesión. Las pruebas pudieron ejecutarse con las bibliotecas ya instaladas en
el equipo; no se tomó ese entorno global como evidencia de instalación limpia.
