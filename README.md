# Seguimiento del Boletín Oficial para EPESF

Aplicación local en desarrollo para relevar la Primera Sección del Boletín Oficial
de la República Argentina (BORA), registrar la cobertura diaria y conservar las
publicaciones del sector eléctrico en una base SQLite.

La [ficha del producto](PRODUCT.md), el [diseño aprobado](DESIGN.md) y el
[registro de cambios](CHANGELOG.md) documentan el alcance vigente de la web.

## Puesta en marcha

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\epe-boletin.exe --data-dir var init
```

La aplicación no hace consultas de red al importarse. Una simulación acotada se
ejecuta así:

```powershell
.\.venv\Scripts\epe-boletin.exe --data-dir var run `
  --mode simulation --from 2025-05-29 --to 2025-05-29 --no-download
```

Para un histórico se usa `--mode historical`; el modo `daily` consulta únicamente
la fecha actual. Los resultados se consultan y exportan con:

```powershell
.\.venv\Scripts\epe-boletin.exe --data-dir var status
.\.venv\Scripts\epe-boletin.exe --data-dir var export-csv var\publicaciones.csv
.\.venv\Scripts\epe-boletin.exe --data-dir var `
  --rules config\relevance_rules.json reclassify
```

La interfaz de consulta local se inicia con:

```powershell
.\.venv\Scripts\epe-boletin.exe --data-dir var serve
```

El comando abre el navegador predeterminado y mantiene el servicio exclusivamente
en `127.0.0.1`. La pantalla muestra el estado de la última ejecución, permite
filtrar por período, relevancia, tipo de publicación y texto, recorrer el histórico consolidado desde
noviembre de 2025, abrir los PDF registrados y exportar solamente la vista filtrada.
Dentro de cada fecha, las publicaciones se ordenan por prioridad de revisión:
primero las menciones directas a EPESF, luego el impacto potencial y después las
pendientes de revisión. A igual clasificación, se prioriza la Secretaría de Energía
y se dejan después las del ENRE o del regulador nacional de gas y electricidad.
El correo generado conserva este criterio. El orden estima la incidencia y no
modifica la clasificación ni confirma por sí solo una obligación para EPESF.
Cada publicación con resumen completo incluye una casilla. El botón **Generar correo
con seleccionadas** crea un `.eml` sólo con las casillas marcadas y lo abre con el
cliente de correo asociado en Windows. El usuario completa remitente y destinatarios
y decide si lo envía. Se
cierra con `Ctrl+C` en la ventana desde la que se inició.

La interfaz sigue la guía `estilo_web_v2.md`: blanco frío, grafito y azul institucional,
sin serif; título, pestañas y estado en una barra superior de ancho completo.
Incluye un selector de período único que abre un calendario para elegir Desde/Hasta
de manera continua, accesos Hoy, Ayer, siete
días y mes, métricas de publicaciones, relevancia e impacto, calendario histórico
y vista de fallas. La tabla da más espacio al resumen de Análisis y agrupa el
selector de densidad y la exportación CSV en una barra sobre los resultados.
La selección habilita el correo y muestra una barra con conteo y exportación de
las publicaciones marcadas. El CSV superior exporta toda la vista filtrada.
La densidad cómoda/compacta se conserva en el navegador. **?** muestra la
ayuda de teclado (`/`, flechas, `j`/`k`, `x`, Enter y Esc).
**Consultar ahora** y **Reintentar consulta** usan el proceso de lectura existente.
**Generar resumen** y **Reintentar resumen** toman la clave de la variable de entorno
del servicio o, para Gemini, de `gemini_api_key.txt` dentro de `--data-dir`.
Con la tanda automática activada, al iniciar la web y después de cada consulta
completa el servicio genera en segundo plano los resúmenes pendientes de las
publicaciones con **Impacto potencial** y PDF extraído. Procesa una publicación por
vez; ante límites de tasa o cortes temporales espera y reintenta. Si hay tres fallas
no transitorias consecutivas, detiene la tanda y conserva las demás como pendientes.
El botón permite reintentar una falla
individual. El texto de los PDF se envía al proveedor de IA configurado para generar
estos resúmenes. La tanda automática queda activa por defecto; `EPE_AUTO_SUMMARIES=0`
la pausa sin deshabilitar el botón manual. El progreso se consulta en
`/summary-status` dentro del servidor local.

El CSV sólo se genera cuando se ejecuta `export-csv` y, por defecto, contiene las
publicaciones seleccionadas o pendientes de revisión. La opción `--all` incorpora
también los metadatos descartados y se reserva para controles de cobertura.

Cada consulta HTTP tiene tres intentos como máximo, con una espera creciente entre
ellos. Se pueden ajustar con `--max-attempts` y `--timeout`. La ejecución registra
su actividad en `var\logs\epe-boletin.log`, además de conservar en SQLite el estado
y el detalle de las fallas por fecha.

Las reglas de selección están en `config\relevance_rules.json`. Cada modificación
debe llevar una versión nueva; `reclassify` vuelve a evaluar la base existente sin
descargar nuevamente los documentos y registra qué versión produjo el resultado.

Los estados distinguen una fecha cubierta, una edición todavía no publicada y una
consulta fallida. Las publicaciones se deduplican por el identificador oficial del
BORA. Los documentos pertinentes se validan como PDF, se escriben de forma atómica
y se registran con SHA-256. El texto se extrae de todas las páginas y los anexos
indicados por el BORA se guardan como documentos separados vinculados al aviso.
La aplicación conserva referencias internas de página para respaldar las fichas,
pero el resultado destinado al usuario es un resumen conceptual de cada norma.

Los resúmenes aprobados pueden importarse y el boletín puede prepararse como correo
sin enviarlo:

```powershell
.\.venv\Scripts\epe-boletin.exe --data-dir var `
  import-summaries tests\fixtures\summaries_20260911.json
.\.venv\Scripts\epe-boletin.exe --data-dir var build-email `
  --date 2026-09-11 --output var\outbox\boletin_2026_09_11.eml
```

La generación automática usa la Interactions API de Gemini con una salida JSON
estructurada y `store=false`. El modelo predeterminado es
`gemini-3.5-flash-lite`; puede sustituirse con `--model` o `EPE_SUMMARY_MODEL`. La clave se lee de
`GEMINI_API_KEY`; ninguna credencial se guarda en el repositorio. OpenAI permanece
disponible mediante `--provider openai`. La referencia técnica es la
[documentación oficial de Interactions](https://ai.google.dev/api/interactions-api).

```powershell
$env:GEMINI_API_KEY = "..."
.\.venv\Scripts\epe-boletin.exe --data-dir var summarize --date 2026-09-14
```

`build-email` adjunta únicamente los documentos de las publicaciones seleccionadas
y divide el boletín en varios `.eml` cuando el límite configurado con `--max-mb`
no permite enviarlo como una sola pieza.

Cada correo recibe un `Message-ID` estable y queda registrado como `prepared`. La
aplicación no contiene un envío automático: el `.eml` se abre para que una persona
complete remitente y destinatarios, lo revise y use el cliente de correo instalado.

En la interfaz, **Generar correo** guarda el `.eml` en `outbox` y muestra la
aplicación de correo predeterminada de Windows sin bloquear la página. Cuando el
archivo queda guardado, las publicaciones se desmarcan y la barra inferior
desaparece. No se muestra un cartel de confirmación. Si falla la generación, se
conserva la selección para reintentar. Si falla la apertura, se informa que el
borrador quedó guardado y se ofrecen descarga y reapertura.

`config\operation.example.json` reúne las definiciones de producción sin incluir
contraseñas. Se puede comprobar antes de activar la tarea diaria:

```powershell
.\.venv\Scripts\epe-boletin.exe check-config config\operation.example.json
```

El resultado enumera los campos y variables de entorno faltantes y devuelve código
0 únicamente cuando la configuración está completa.

La base, los documentos y las reglas pueden respaldarse de manera transaccional:

```powershell
.\.venv\Scripts\epe-boletin.exe --data-dir var `
  --rules config\relevance_rules.json backup var\backups\boletin.zip
```

El ZIP contiene un manifiesto con tamaño y SHA-256 de cada archivo. La preparación
de la tarea diaria de Windows está documentada en
[OPERACION_WINDOWS.md](OPERACION_WINDOWS.md); los scripts no instalan la tarea por
sí solos durante el desarrollo.

La restauración valida todas las huellas y la integridad de SQLite antes de dejar
los datos disponibles, y exige como destino una carpeta nueva o vacía:

```powershell
.\.venv\Scripts\epe-boletin.exe restore `
  var\backups\boletin.zip C:\EPESF\Boletin\datos-restaurados
```

## Desarrollo

Las pruebas no acceden a Internet:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Las muestras incluyen dos ediciones consecutivas —29 y 30 de mayo de 2025— con
153 publicaciones en total. La segunda contiene un suplemento y permite comprobar
que se registra junto con la edición principal.

El alcance y las etapas completas están en [PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md).
La construcción del ejecutable portable de Windows se describe en
[BUILD_WINDOWS.md](BUILD_WINDOWS.md).
