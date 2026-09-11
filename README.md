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
```

Los estados distinguen una fecha cubierta, una edición todavía no publicada y una
consulta fallida. Las publicaciones se deduplican por el identificador oficial del
BORA. Los documentos pertinentes se validan como PDF, se escriben de forma atómica
y se registran con SHA-256. El texto se extrae de todas las páginas y los anexos
indicados por el BORA se guardan como documentos separados vinculados al aviso.

## Desarrollo

Las pruebas no acceden a Internet:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

El alcance y las etapas completas están en [PLAN_DE_TRABAJO.md](PLAN_DE_TRABAJO.md).
