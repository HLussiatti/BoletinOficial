# Validación integral del 14/09/2026

La prueba se ejecutó contra la Primera Sección publicada por el Boletín Oficial
de la República Argentina para el 14 de septiembre de 2026. Se utilizó una base
aislada en `var/validation-20260914`, sin mezclar registros con validaciones
anteriores.

## Resultado de la recolección

- Estado de la ejecución: `complete`.
- Publicaciones recorridas: 74.
- Fechas fallidas: 0.
- Publicaciones seleccionadas como relevantes para EPESF: 0.
- Documentos descargados por el proceso: 1.
- Errores de descarga o extracción: 0.
- Sucesivas ejecuciones sobre la misma fecha conservaron 74 publicaciones y no
  volvieron a descargar documentos.

El proceso descargó el Aviso Oficial 347418 de la Subsecretaría de Energía
Eléctrica. El texto comunica solicitudes de dos grandes usuarios mayores para
cambiar su categoría a grandes usuarios menores. No identifica a EPESF ni a
Santa Fe, por lo que la clasificación final fue `not_relevant`, de acuerdo con
la regla vigente para avisos particulares sin vínculo local.

## Control de posibles omisiones

Se revisó manualmente la Resolución 1544/2026 del Ministerio de Economía porque
los metadatos del índice no indican el área temática y ese organismo también
puede publicar normas energéticas. La resolución cierra una investigación por
presunto dumping sobre lavarropas originarios de China, sin aplicar derechos
antidumping definitivos. Se confirmó que no corresponde seleccionarla para
EPESF.

Las restantes resoluciones pertenecen a organismos o materias sin indicios del
sector eléctrico en el índice. Con la información publicada y los controles
realizados, el resultado esperado para el día es **sin novedades relevantes**.

## Salidas y controles

- El archivo `publicaciones_2026_09_14.csv` contiene solamente el encabezado,
  porque la exportación operativa no conserva las 74 publicaciones descartadas.
- No se creó un correo `.eml`: sin publicaciones relevantes y resumidas, el
  sistema informó correctamente que no había contenido para enviar.
- No se realizó ningún envío de correo.
- Se creó `validation_2026_09_14.zip` y se restauró en una carpeta nueva.
- La base original y la restaurada pasaron `PRAGMA integrity_check` y no
  presentaron errores de claves foráneas.
- La restauración conservó 74 publicaciones y 1 documento registrado.
- La suite automatizada terminó con 30 pruebas aprobadas.

## Validación funcional pendiente

El resultado debe compararse con el relevamiento humano del 14/09/2026. Si ese
relevamiento contiene una norma eléctrica que aquí no fue seleccionada, su
organismo, tipo y número permitirán reproducir el falso negativo y ajustar la
regla de preselección.
