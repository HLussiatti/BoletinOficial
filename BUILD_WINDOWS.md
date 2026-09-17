# Construcción para Windows

El proyecto genera un paquete portable de 64 bits con PyInstaller. El ejecutable no
requiere que Python esté instalado en el equipo de destino.

## Preparación

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[build]"
```

## Construcción

```powershell
.\scripts\build_windows.ps1 -Version 0.1.0
```

Por defecto, la construcción toma la clave de
`var\operacion\gemini_api_key.txt`. Para usar otra ubicación, indicá
`-GeminiKeyFile` con la ruta del archivo. La construcción se detiene si falta o
está vacío.

El script crea `dist\epe-boletin` y el archivo
`dist\epe-boletin-0.1.0-windows-x64.zip`. El paquete incluye:

- `epe-boletin.exe` y sus bibliotecas privadas;
- la configuración versionada de relevancia;
- los scripts de ejecución y programación diaria;
- el script `run_ui.ps1` para abrir la interfaz local;
- `var\gemini_api_key.txt`, que usan la web y la tarea diaria en el equipo de destino;
- los manuales de uso y operación.

El ZIP contiene la clave en texto legible. Guardá y compartí el paquete sólo en
una ubicación autorizada; la clave y el ZIP generado permanecen fuera de Git.
Al extraer el paquete, `scripts\run_ui.ps1` usa `var` como carpeta de datos y
encuentra allí la clave sin configuración adicional. El lanzador detecta su carpeta
de instalación automáticamente.

## Uso en otra máquina

Extraé el ZIP en una carpeta local y ejecutá `scripts\run_ui.ps1` dentro de la
carpeta `epe-boletin` extraída. La web se abre en `127.0.0.1:8765`. La base SQLite
se crea en `var` junto a la clave incluida. Para trasladar el histórico y los PDF,
restaurá un respaldo con el procedimiento de `OPERACION_WINDOWS.md`.

`build`, `dist` y el archivo `.spec` generado quedan fuera de Git. Cada versión debe
construirse desde un commit identificado y publicar su SHA-256 junto con el
instalador o paquete entregado.

## Verificación realizada

La versión 0.1.0 se extrajo en una carpeta aislada y se comprobó que el ejecutable:

1. muestra la ayuda con caracteres españoles en UTF-8;
2. crea una base SQLite nueva;
3. informa correctamente un estado vacío;
4. procesa las muestras del 29 y 30 de mayo de 2025, con 153 publicaciones y el
   suplemento identificado;
5. inicia la interfaz local, consulta una base real y exporta la vista filtrada.

Esta construcción incluye la interfaz en navegador local. El instalador con acceso
directo continúa como siguiente etapa de distribución.
