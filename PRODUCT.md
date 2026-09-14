# Producto: seguimiento del Boletín Oficial para EPESF

## Propósito

Aplicación local de Windows para detectar y revisar publicaciones de la Primera
Sección del BORA que puedan afectar a la Empresa Provincial de la Energía de
Santa Fe. Debe reducir el volumen que revisa una persona sin ocultar el respaldo
documental ni el estado operativo de cada ejecución.

## Usuarios y contexto

El usuario principal es personal técnico o regulatorio de EPESF. La consulta se
realiza desde una PC de trabajo, normalmente después del proceso diario de las
05:30. La información, los PDF y las credenciales permanecen en el equipo.

## Plataforma y tecnología

La interfaz se abre en el navegador predeterminado mediante un acceso directo de
Windows. Un servicio local escucha exclusivamente en `127.0.0.1` y consulta la
base SQLite y los documentos ya administrados por el paquete Python. La primera
versión usa HTML renderizado en el servidor, CSS y JavaScript acotado, sin requerir
Node.js ni alojamiento público.

## Tareas principales

- Conocer si la edición del día fue procesada completa o tuvo fallas.
- Consultar publicaciones por fecha, tipo, número, organismo y texto.
- Distinguir seleccionadas, pendientes de revisión y descartadas.
- Leer el resumen conceptual y la relación estimada con EPESF.
- Abrir el aviso oficial, el PDF principal y sus anexos.
- Identificar documentos, resúmenes o entregas con errores pendientes.
- Exportar el conjunto filtrado cuando haga falta un control adicional.

## Reglas y decisiones confirmadas

- Los archivos se nombran `YYYY_MM_DD_Tipo_Número.pdf`; los anexos agregan
  `_Anexo_N`.
- Se preservan correctamente los caracteres españoles, incluida «Resolución».
- El CSV no se genera durante la ejecución diaria. Su exportación normal incluye
  sólo publicaciones seleccionadas o pendientes; la inclusión de descartadas es
  una acción explícita de control.
- El texto por artículo y sus páginas se conserva como respaldo interno. La salida
  principal para el usuario es un resumen conceptual.
- Los avisos eléctricos particulares sin vínculo con EPESF o Santa Fe se
  descartan, aunque pueden descargarse inicialmente para evaluar su texto.
- Una edición sin publicaciones relevantes es un resultado válido y no genera un
  correo vacío.
- El envío de correo y la instalación de la tarea programada requieren la
  configuración institucional correspondiente.

## Evidencia disponible

Las validaciones reales del 11/09/2026 y 14/09/2026 comprobaron la lectura completa,
la descarga, la nomenclatura, la clasificación, los anexos, la idempotencia, los
resúmenes revisados, el correo de simulación, el respaldo y la restauración. La
segunda validación confirmó correctamente un día sin novedades relevantes.

## Criterios de calidad de la interfaz

La pantalla debe priorizar el estado diario y la lista de publicaciones. Debe ser
legible en monitores de oficina y usable con teclado, ofrecer foco visible, estados
con texto además de color y mantener una jerarquía sobria acorde con documentación
normativa. La interfaz debe responder bien en ventanas angostas, sin convertir cada
dato en una tarjeta ni ocultar información crítica detrás de interacciones frágiles.

## Direction contract

**THESIS:** Un expediente operativo que conduce del estado diario al documento y
evita la disposición genérica de tablero con tarjetas.

**OWN-WORLD:** Papel marfil, tinta negra, reglas finas y un único hilo dorado;
títulos editoriales, controles sobrios y registros separados por líneas continuas.

**STORY:** El usuario confirma la cobertura, reduce el conjunto con filtros,
comprende la clasificación y abre la fuente que respalda la decisión.

**FIRST VIEWPORT:** Cabecera documental y última ejecución arriba; cuatro métricas
en una franja; filtros debajo; la lista empieza antes del pliegue y la acción
principal es aplicar el filtro.

**FORM:** Expediente operativo, cuarta dirección de la lista fundamentada; semilla
`90acf5ee`. Interacción distintiva: el hilo dorado conecta el estado con el flujo
documental y reaparece al desplegar el resumen conceptual.

**FINISH:** unreviewed and undocumented is unfinished; this build ends with the
finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
