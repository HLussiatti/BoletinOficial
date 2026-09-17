# Instalación en otra computadora Windows

El archivo de distribución es `epe-boletin-0.1.0-windows-x64-historico-AAAAmmdd.zip`.
Incluye el ejecutable, la base SQLite histórica, los PDF y anexos, los borradores
de correo ya preparados, las reglas y el instalador de la tarea diaria. No hace
falta instalar Python. La consulta y el resumen diario usan Internet; la interfaz
web funciona sólo en la computadora donde se instala.

El ZIP **incluye la clave de Gemini en texto legible** y documentos de trabajo.
Trasladarlo y conservarlo únicamente en una ubicación autorizada. El archivo
`.sha256` entregado junto a él sirve para comprobar que llegó íntegro.

## Requisitos en el equipo de destino

- Windows de 64 bits y una cuenta con permisos de administrador para instalar.
- La misma cuenta debe usarse después para abrir la interfaz. Si se eleva
  PowerShell con otra cuenta, indicá una carpeta de instalación accesible a la
  persona que va a usar el aplicativo.
- Espacio libre para el ZIP, su extracción y los datos restaurados. Se recomienda
  al menos 2 GB durante la instalación.
- Acceso a BORA y Gemini para la tarea diaria. Para abrir los correos preparados,
  un cliente de correo local asociado a `.eml`, por ejemplo Thunderbird.

## Instalación paso a paso

1. Copiá el ZIP y su archivo `.sha256` al equipo nuevo. En PowerShell, comprobá
   la huella: `(Get-FileHash .\epe-boletin-0.1.0-windows-x64-historico-AAAAmmdd.zip -Algorithm SHA256).Hash`.
   Comparala con el valor del `.sha256`.
2. Extraé el ZIP, por ejemplo con el Explorador de Windows, en una carpeta
   temporal. Dentro aparecerá la carpeta `epe-boletin`.
3. Abrí **PowerShell como administrador con la cuenta que usará la aplicación** y
   entrá en esa carpeta extraída: `Set-Location "C:\ruta\temporal\epe-boletin"`.
4. Ejecutá: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_package.ps1`.
   El instalador copia el aplicativo a `%LOCALAPPDATA%\EPESF\Boletin`, verifica y
   restaura la base y los archivos históricos en `var\operacion`, y registra la
   tarea **EPESF - Boletin Oficial** para las **05:30 todos los días**. Si esa
   carpeta o esa tarea ya existen, se detiene sin reemplazarlas.
5. Comprobá la tarea: `Get-ScheduledTask -TaskName "EPESF - Boletin Oficial" |
   Select-Object TaskName,State`. Para ver la hora, ejecutá
   `(Get-ScheduledTask -TaskName "EPESF - Boletin Oficial").Triggers |
   Select-Object StartBoundary`.
6. Cerrá el PowerShell elevado. Abrí una consola normal y ejecutá
   `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\EPESF\Boletin\scripts\run_ui.ps1"`.
   El navegador abre la interfaz en `http://127.0.0.1:8765`. Revisá una fecha
   histórica y abrí uno de sus PDF para confirmar la restauración. La consola
   debe quedar abierta mientras se usa la interfaz.

Para instalar en otra carpeta, agregá `-InstallDir "D:\EPESF\Boletin"` al final
del comando del paso 4. El script de la interfaz detecta su ubicación. La tarea
diaria usa la cuenta de servicio **SYSTEM**; puede ejecutarse aunque nadie haya
iniciado sesión, siempre que la computadora esté encendida y tenga conectividad.
Si a las 05:30 no estaba disponible, Windows intentará iniciarla al volver.

## Verificación de la operación diaria

La tarea sólo **consulta y resume**. Los correos siguen requiriendo revisión y
envío manual desde la interfaz. Para revisar el resultado de una ejecución:

```powershell
Get-ScheduledTaskInfo -TaskName "EPESF - Boletin Oficial" |
    Select-Object LastRunTime,LastTaskResult,NextRunTime
Get-Content "$env:LOCALAPPDATA\EPESF\Boletin\var\operacion\logs\epe-boletin.log" -Tail 40
```

`LastTaskResult = 0` indica que el proceso terminó sin error. Los detalles de
cobertura y publicaciones también aparecen en la web. Podés ejecutar la tarea
manualmente con `Start-ScheduledTask -TaskName "EPESF - Boletin Oficial"`; esa
acción realiza una consulta real y puede llamar a Gemini. No se realiza durante
la instalación.

Para respaldos posteriores y restauraciones, consultá
[OPERACION_WINDOWS.md](OPERACION_WINDOWS.md). La carpeta extraída y el ZIP
contienen la clave; guardalos de forma segura o retiralos del equipo nuevo tras
verificar la instalación.
