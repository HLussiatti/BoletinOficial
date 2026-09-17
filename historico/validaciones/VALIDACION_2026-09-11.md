# Validación de la edición del 11 de septiembre de 2026

Se ejecutó el recolector contra la Primera Sección del BORA del día, en modo de
simulación y con una base separada, conservada localmente en
`var/pruebas/validation-20260911`.

## Resultado técnico

- 91 publicaciones recuperadas y cobertura marcada como completa.
- 2 resoluciones clasificadas con impacto sectorial potencial.
- 4 documentos principales y 1 anexo descargados y extraídos completamente.
- 0 errores de consulta, descarga o extracción.
- La cuarta ejecución recuperó los mismos 91 registros y descargó 0 archivos, con
  lo que se comprobó la reanudación sin duplicar documentos.
- No se detectaron menciones directas a EPESF en esta edición.

La clasificación inicial encontró un falso positivo por la palabra `transporte` en
un aviso de la Secretaría de Transporte. La regla fue corregida: los términos de
actividad sólo califican cuando también hay una señal eléctrica o energética. Los
avisos eléctricos sobre casos particulares sin vínculo con EPESF o Santa Fe se
descargan como candidatos para analizar su texto, pero luego quedan descartados.

## Publicaciones detectadas

### Resolución 238/2026 - Secretaría de Energía

Sustituye el Anexo I de la Resolución 221/2026 para corregir un error material en
los bloques de consumo base de electricidad del régimen de Subsidios Energéticos
Focalizados. La corrección fija para septiembre de 2026 un consumo base de 200
kWh/mes en todas las zonas bioambientales. El anexo completo también conserva los
valores de 550/370/300 kWh/mes para enero, febrero y diciembre según zona; 300
kWh/mes entre mayo y agosto; y 150 kWh/mes en marzo, abril, octubre y noviembre.
Entra en vigencia el día de su publicación.

Relación potencial con EPESF: incide en el régimen nacional aplicado a usuarios
residenciales y puede afectar la gestión de subsidios y consumos base de la
distribuidora. La aplicabilidad concreta debe validarse con el área responsable.

### Resolución 239/2026 - Secretaría de Energía

Autoriza a la Empresa Provincial de Energía de Chubut S.A.U. a ingresar al Mercado
Eléctrico Mayorista como Participante Comercializador. Ordena al Organismo Encargado
del Despacho informar a los agentes del MEM y notifica a EPECH, CAMMESA y ENRGE.
Entra en vigencia el día de su publicación.

Relación potencial con EPESF: es una decisión sectorial sobre otra empresa
provincial y no contiene una obligación directa para EPESF.

### Aviso oficial BORA 347338 - descartado

Comunica la solicitud de YPF Energía Eléctrica S.A. para desafectar la Central
Térmica Loma Campana I como nodo de generación de su autogenerador distribuido y
autorizarla posteriormente como Agente Generador del MEM, manteniendo la vinculación
al SADI. Establece diez días corridos para objeciones u oposiciones.

Se descartó porque se refiere a un generador y una central sin ubicación ni vínculo
identificado con Santa Fe o EPESF.

### Aviso oficial BORA 347339 - descartado

Comunica cambios de titularidad y solicitudes de habilitación en el MEM: INTERPACK
S.A. como GUME en reemplazo de Kimberly Clark Argentina S.A., con EDENOR como
distribuidor/PAFTT; y SANSIS S.A. como GUMA en reemplazo de Fibercord S.A., con
EDESUR. Establece diez días corridos para objeciones u oposiciones.

Se descartó porque las instalaciones y los distribuidores involucrados pertenecen
a las áreas de EDENOR y EDESUR y no se identificó relación con EPESF.

## Exportación

La aplicación conserva en SQLite los metadatos mínimos de las 91 publicaciones
para acreditar cobertura y evitar reprocesamientos. No genera un CSV de forma
automática. La exportación normal de esta validación contiene únicamente las
Resoluciones 238/2026 y 239/2026; la exportación completa queda disponible sólo con
la opción explícita `--all` para controles de auditoría.

La reclasificación posterior con la configuración versionada `2026-09-11.1`
reprodujo el resultado aprobado: 89 publicaciones descartadas y 2 seleccionadas.
No fue necesario volver a consultar el BORA ni descargar los PDF.

Los resúmenes conceptuales de las Resoluciones 238/2026 y 239/2026 se importaron a
la base como contenido revisado por una persona. El correo de simulación resultante
contiene ambas fichas y adjunta los dos PDF principales y el Anexo 1 de la
Resolución 238/2026. El archivo se creó localmente y no fue enviado.
