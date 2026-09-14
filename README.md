# Seguimiento del Boletín Oficial para EPESF

Aplicación local en desarrollo para relevar la Primera Sección del Boletín Oficial
de la República Argentina (BORA), registrar la cobertura diaria y conservar las
publicaciones del sector eléctrico en una base SQLite.

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
filtrar por fecha, relevancia y texto, recorrer el histórico consolidado desde
noviembre de 2025, abrir los PDF registrados y exportar solamente la vista filtrada.
Cada publicación con resumen completo incluye una casilla. El botón **Generar correo
con seleccionadas** crea un `.eml` sólo con las casillas marcadas y lo abre con el
cliente de correo asociado en Windows. El usuario completa remitente y destinatarios
y decide si lo envía. Se
cierra con `Ctrl+C` en la ventana desde la que se inició.

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
