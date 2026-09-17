# Mantenimiento y organización del proyecto

Actualizado el 17 de septiembre de 2026, al cerrar el desarrollo del aplicativo.

## Estructura vigente

| Ruta | Uso |
| --- | --- |
| `src/epe_boletin/` | Implementación del aplicativo y CLI. |
| `tests/` | Pruebas automatizadas y muestras necesarias para ejecutarlas; versionadas. |
| `scripts/`, `config/` | Preparación de Windows y reglas de selección. |
| `README.md`, `PRODUCT.md`, `DESIGN.md`, `BUILD_WINDOWS.md`, `OPERACION_WINDOWS.md`, `CHANGELOG.md` | Documentación vigente. |
| `historico/` | Prototipo, plan, informe de avance y validaciones cerradas; versionados para consulta. |
| `.venv/` | Entorno Python local utilizado por la aplicación; excluido de Git. |
| `var/operacion/` | Base, documentos y configuración de la operación local; excluidos de Git. |
| `var/pruebas/` | Evidencias, PDF, capturas y datos de pruebas manuales; excluidos de Git. |
| `var/historico/preoperacion/` | Base y CSV locales anteriores a `var/operacion/`; excluidos de Git. |

## Depuración del 17/09/2026

- Se trasladaron a `historico/prototipo_2025/` los ocho archivos del prototipo:
  `NLP.py`, `app.ipynb`, `app.py`, `database.xlsx`, `functions.py`,
  `obtener_detalles.py`, `scrapper.py` y `scrapper_pdf.py`.
- Se archivaron el plan original, el estado de implementación anterior y la
  primera propuesta visual en `historico/`. Los cuatro informes `VALIDACION_*.md`
  pasaron a `historico/validaciones/`.
- Se retiraron de Git `boletin_errors.log`, `salida.txt` y `help_env.txt`: eran
  respectivamente un registro antiguo, salida temporal y ayuda generada.
- Se reunieron en `var/pruebas/` los PDF del prototipo y de validación, los
  conjuntos de validación del usuario, sondeos, restauraciones de prueba,
  comprobaciones de empaquetado y resiliencia, y capturas de interfaz. Las
  muestras indispensables para `unittest` permanecen versionadas en `tests/fixtures/`.
- Se movieron `var/boletin.sqlite3` y `var/publicaciones.csv` a
  `var/historico/preoperacion/` para conservarlos sin confundirlos con la base
  operativa actual.
- Se eliminó el entorno antiguo `.env/`, que duplicaba `.venv/`; también las
  carpetas generadas `build/`, `dist/`, `tmp/`, cachés de Python y de pruebas, y
  el archivo `.spec` generado. Los paquetes de `dist/` eran anteriores a los
  últimos cambios y deben reconstruirse antes de distribuir la aplicación.
- Se eliminó `gemini_api_key.txt` de la raíz tras comprobar que era una copia
  idéntica de la configuración local de `var/operacion/`. No se versionan claves.

El contenido de `var/`, `.venv/`, paquetes y cachés se excluye mediante
`.gitignore`. Por eso, las evidencias locales archivadas en `var/` no aparecen
en otro clon. Para conservarlas fuera de esta máquina se requiere una copia de
seguridad independiente. No se modificó `var/operacion/` durante esta depuración.

## Verificación y regeneración

Desde la raíz del proyecto, con PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
git status --short
```

El ejecutable de Windows se vuelve a crear según [BUILD_WINDOWS.md](BUILD_WINDOWS.md).
La preparación y las copias de seguridad de los datos operativos están en
[OPERACION_WINDOWS.md](OPERACION_WINDOWS.md). Al agregar nuevas pruebas
automatizadas, se ubican en `tests/`; los resultados y archivos de prueba
manual se guardan en `var/pruebas/`.
