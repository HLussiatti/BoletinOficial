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

Para un histórico se usa `--mode historical`; el modo `daily` toma la fecha actual
si no se especifica un período. Los resultados se consultan y exportan con:

```powershell
.\.venv\Scripts\epe-boletin.exe --data-dir var status
.\.venv\Scripts\epe-boletin.exe --data-dir var export-csv var\publicaciones.csv
.\.venv\Scripts\epe-boletin.exe --data-dir var `
  --rules config\relevance_rules.json reclassify
```

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

## Desarrollo

Las pruebas no acceden a Internet:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

El alcance y las etapas completas están en [PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md).
