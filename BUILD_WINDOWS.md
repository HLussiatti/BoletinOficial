# Construcción del paquete para Windows

El proyecto genera un ZIP instalable de 64 bits con PyInstaller. El destino no
necesita Python. Las instrucciones para instalarlo están en
[INSTALL_WINDOWS.md](INSTALL_WINDOWS.md).

## Preparación

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[build]"
```

La carpeta `var\operacion` debe contener `boletin.sqlite3`, `documents\`,
`outbox\` si hay borradores que conservar y `gemini_api_key.txt`. El respaldo se
crea con la API de copia en línea de SQLite; los PDF, anexos y borradores se
incluyen con un manifiesto de tamaños y SHA-256. La restauración verifica ese
manifiesto, la integridad de SQLite y reubica las rutas de documentos y correos.

## Construcción

```powershell
.\scripts\build_windows.ps1 -Version 0.1.0
```

Para otras rutas se pueden usar `-HistoricalDataDir` y `-GeminiKeyFile`. La
construcción se detiene si faltan la base o la clave. En `dist\` quedan:

- `epe-boletin-0.1.0-windows-x64-historico-AAAAmmdd.zip`: paquete completo;
- el mismo nombre con extensión `.zip.sha256`: huella SHA-256 para el traslado;
- `epe-boletin\`: carpeta sin comprimir para inspección.

El ZIP contiene `epe-boletin.exe`, bibliotecas privadas, configuración,
documentación, scripts de instalación y ejecución, `setup\historico.zip` y
`setup\gemini_api_key.txt`. **Contiene una credencial en texto legible**. Los
resultados de `build/`, `dist/` y el `.spec` están excluidos de Git.

La instalación utiliza `scripts\install_package.ps1`. Copia el aplicativo a una
carpeta nueva, restaura el histórico, comprueba el estado de la base y registra
la tarea de Windows a las 05:30. Los scripts `run_daily.ps1` y `run_ui.ps1`
utilizan `var\operacion` dentro de esa carpeta.
