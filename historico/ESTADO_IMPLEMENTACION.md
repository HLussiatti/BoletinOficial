> Documento histórico del 14/09/2026. Para el estado vigente, consultar
> [README](../README.md), [PRODUCT](../PRODUCT.md) y
> [CHANGELOG](../CHANGELOG.md).

# Estado de implementación

Actualizado el 14 de septiembre de 2026. Rama de trabajo:
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
- registro idempotente de los correos preparados mediante `Message-ID`, vínculo con
  las publicaciones y estados preparado, enviado, error o resultado incierto;
- preparación manual del correo desde la vista filtrada, sin transporte SMTP ni
  envío automático;
- configuración operativa externa y diagnóstico de preparación, sin credenciales
  persistidas ni valores secretos mostrados en la salida;
- ejecución diaria acotada a la fecha corriente, seguida por resúmenes Gemini sólo
  para las publicaciones relevantes de esa edición;
- respaldo ZIP transaccional de SQLite, documentos y reglas, con manifiesto y
  huellas SHA-256;
- restauración segura en una carpeta vacía, con validación de todas las huellas,
  integridad de SQLite y claves foráneas antes de publicar el resultado;
- scripts de Windows preparados para la ejecución diaria a las 05:30.
- construcción reproducible con PyInstaller de un paquete portable para Windows
  x64, con ejecutable, reglas, scripts y manuales.
- descubrimiento, descarga y almacenamiento separado de anexos;
- consulta de estado y exportación CSV;
- interfaz de consulta en navegador, servida exclusivamente en `127.0.0.1`, con
  estado diario, acceso al histórico consolidado, filtros, selección individual
  para `.eml`, exportación de la vista y apertura segura de PDF;
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
detalle está en [la validación del 11/09](validaciones/VALIDACION_2026-09-11.md).

El 14 de septiembre de 2026 se ejecutó una segunda validación real. Se recorrieron
74 publicaciones, se revisó un aviso de la Subsecretaría de Energía Eléctrica y se
descartó correctamente por no identificar vínculo con EPESF o Santa Fe. La
Resolución 1544/2026 del Ministerio de Economía se controló manualmente para evitar
un falso negativo y resultó ajena al sector. El resultado sin novedades relevantes
fue validado por el usuario; la repetición no duplicó datos ni archivos.

Ese mismo día se completó la recolección histórica acordada desde el 01/11/2025
hasta el 14/09/2026, dividida en doce lotes reanudables. Los 318 días tienen
cobertura: 209 ediciones completas y 109 días sin publicación, sin consultas
fallidas. La base operativa contiene 13.258 publicaciones; las reglas dejaron 26
casos con mención directa a EPESF, 573 de impacto sectorial potencial y 42 que
requieren revisión. Se descargaron 1.308 PDF y anexos correspondientes a 717
publicaciones, con un tamaño total de 339,91 MB. Todos los archivos tienen
extracción completa, coinciden con su tamaño y huella registrados y respetan la
nomenclatura acordada. La carpeta no contiene CSV ni resúmenes automáticos y no se
utilizó Gemini. Los datos operativos permanecen en `var/operacion`, fuera de Git.

La comparación posterior contra los 79 PDF aportados por el usuario agrupó 37
publicaciones relevantes. La versión inicial detectaba 32 (86,5 %). Se incorporaron
tres señales de metadatos para Subsidios Energéticos Focalizados, la Subsecretaría
de Transición y Planeamiento Energético y la emergencia del Sector Energético
Nacional. Con las reglas `2026-09-14.1`, las 37 publicaciones quedaron detectadas
(100 % sobre este conjunto positivo) y se descargaron los documentos que faltaban.
La corrección agregó ocho candidatos en las 13.258 publicaciones: los cinco casos
omitidos y tres normas similares para revisión. El conjunto no permite medir
precisión porque no contiene una selección exhaustiva de negativos. El detalle se
encuentra en [la validación de documentos del usuario](validaciones/VALIDACION_USUARIO_2025-11_A_2026-09.md).

La base de esa validación se migró al esquema 4. La reclasificación con las reglas
`2026-09-11.1` mantuvo exactamente 89 publicaciones descartadas y las Resoluciones
238/2026 y 239/2026 como los dos resultados de impacto sectorial potencial. Los
cinco PDF existentes se procesaron sin errores; las dos resoluciones quedaron con
referencias de página y los documentos sin estructura normativa se marcaron como
no aplicables.

Los dos resúmenes conceptuales aprobados se importaron como revisión humana. Con
ellos se generó un correo de simulación de 727.692 bytes que contiene las dos
publicaciones y tres adjuntos. No se realizó ningún envío.
El correo preparado quedó vinculado a ambas publicaciones en la base mediante el
`Message-ID` `<epesf-20260911-1-9b41210fd84100b9@localhost>`.

El 14 de septiembre se validó también la generación automática con una clave del
nivel gratuito de Gemini. `gemini-3.5-flash-lite` completó las Resoluciones 238/2026
y 239/2026 y sus resultados se compararon con los resúmenes humanos aprobados. En
ambos casos identificó correctamente que el texto no impone una obligación directa
a EPESF y mantuvo la marca de revisión. Registró 2.440/257 tokens de entrada/salida
para la Resolución 238 y 1.714/198 para la 239. La clave se conserva fuera del
repositorio. El modelo predeterminado quedó definido como
`gemini-3.5-flash-lite`; las solicitudes usan salida estructurada y `store=false`.

El diagnóstico actual mantiene pendiente únicamente la fecha de corte de
notificaciones. La salida UTF-8 se verificó también mediante el comando instalado
en el entorno virtual.

El respaldo de la validación contiene la base, los cinco PDF y la configuración de
reglas. Se verificaron las siete huellas del manifiesto contra el contenido del ZIP.
También se restauró en una carpeta nueva y se comprobaron los 91 registros, los dos
resúmenes y los cinco documentos. Una copia alterada fue rechazada correctamente.

El paquete `epe-boletin-0.1.0-windows-x64.zip` se extrajo en una carpeta aislada. Su
ejecutable inició una base nueva, mostró el estado y procesó las muestras locales
sin depender del intérprete del proyecto. La salida de consola se fijó en UTF-8.

La interfaz definitiva quedó conectada a `var/operacion` y permite recorrer el
histórico consolidado, volver a una fecha concreta y seleccionar individualmente
qué publicaciones con resumen se incluyen en el `.eml`. Se importaron los dos
resúmenes humanos aprobados del 11/09/2026 para la prueba funcional. Se marcó sólo
la Resolución 238/2026 y se comprobó que el correo preparado contiene una única
publicación. La base registra el `.eml` como preparado y no enviado.

La tarea de Windows `EPESF - Boletin Oficial` quedó instalada y habilitada. Su
próxima ejecución está programada para el 15/09/2026 a las 05:30. Ejecutará el
paquete portable contra `var/operacion`, consultará únicamente la fecha corriente
y resumirá con Gemini sólo los resultados relevantes de ese día. Puede iniciar con
la sesión bloqueada; el usuario debe permanecer conectado a Windows.

## Próximo trabajo

### Decisión diferida hasta después de probar la herramienta

El 15/09/2026 el usuario decidió posponer la depuración de las reglas de impacto
potencial y las exclusiones de resultados sectoriales adicionales. Se retomará
después de las pruebas de uso y funcionamiento. El caso de referencia son las
Resoluciones 507/2026 a 544/2026 del Ente Nacional Regulador del Gas y la
Electricidad, publicadas el 01/09/2026 y ausentes de la carpeta de validación.
La validación comprobó la detección de las 37 publicaciones aportadas, pero no
estableció la pertinencia de todos los resultados adicionales. Hasta resolver
esta decisión se mantienen las reglas, los registros y los PDF existentes.


1. Verificar el resultado real de la primera ejecución programada de las 05:30.
2. Convertir el paquete portable en un instalador y definir la ubicación y retención
   del respaldo institucional.

La instalación aislada de las dependencias declaradas se completó en `.venv`. La
validación sobre un equipo Windows limpio continúa pendiente para la etapa del
instalador.
