# Operación en Windows

Esta guía describe los componentes ya preparados para la operación local. La tarea
programada no debe instalarse hasta completar la configuración del equipo, del
servicio de resumen y del correo institucional.

## Ejecución diaria

El modo `daily` toma la última fecha con cobertura completa, retrocede siete días y
consulta hasta la fecha actual. Así recupera días omitidos y vuelve a comprobar
publicaciones tardías. El bloqueo `run.lock` impide dos ejecuciones simultáneas.

```powershell
.\epe-boletin.exe --data-dir C:\EPESF\Boletin\datos `
  --rules C:\EPESF\Boletin\config\relevance_rules.json run --mode daily
```

La salida distinta de cero indica ejecución parcial o fallida. El detalle queda en
la base y en `datos\logs\epe-boletin.log`.

## Tarea programada

`scripts\run_daily.ps1` ejecuta el comando anterior con rutas absolutas.
`scripts\install_scheduled_task.ps1` registra una tarea diaria a las 05:30 con estas
opciones:

- iniciar cuando el equipo vuelva a estar disponible;
- reactivar el equipo cuando Windows y el hardware lo permitan;
- impedir ejecuciones simultáneas;
- limitar cada ejecución a dos horas.

Cuando la instalación esté lista, el registro se realizará desde PowerShell con las
rutas definitivas:

```powershell
.\scripts\install_scheduled_task.ps1 `
  -InstallDir C:\EPESF\Boletin `
  -DataDir C:\EPESF\Boletin\datos
```

## Respaldo

El respaldo usa la API de copia en línea de SQLite y luego incorpora documentos y
reglas a un ZIP. Cada entrada figura en `manifest.json` con su tamaño y SHA-256.

```powershell
.\epe-boletin.exe --data-dir C:\EPESF\Boletin\datos `
  --rules C:\EPESF\Boletin\config\relevance_rules.json `
  backup C:\EPESF\Boletin\respaldos\boletin.zip
```

Los respaldos deben copiarse a la ubicación institucional que se defina para la
custodia. Esa ubicación y la retención todavía requieren definición operativa.

Para restaurar, se utiliza una carpeta nueva o vacía. El comando verifica primero
el manifiesto, las huellas, la integridad de SQLite y sus claves foráneas:

```powershell
.\epe-boletin.exe restore `
  C:\EPESF\Boletin\respaldos\boletin.zip `
  C:\EPESF\Boletin\datos-restaurados
```

Después de comprobar el resultado, la tarea programada puede apuntarse a la carpeta
restaurada. El comando no reemplaza automáticamente una base operativa existente.
