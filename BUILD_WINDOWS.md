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

El script crea `dist\epe-boletin` y el archivo
`dist\epe-boletin-0.1.0-windows-x64.zip`. El paquete incluye:

- `epe-boletin.exe` y sus bibliotecas privadas;
- la configuración versionada de relevancia;
- los scripts de ejecución y programación diaria;
- el script `run_ui.ps1` para abrir la interfaz local;
- los manuales de uso y operación.

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
