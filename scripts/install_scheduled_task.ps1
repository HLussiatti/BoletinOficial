param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir,
    [Parameter(Mandatory = $true)]
    [string]$DataDir,
    [string]$TaskName = "EPESF - Boletin Oficial",
    [string]$StartTime = "05:30"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $InstallDir "scripts\run_daily.ps1"
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "No se encontró el script de ejecución: $runner"
}
if (-not (Test-Path -LiteralPath (Join-Path $DataDir "boletin.sqlite3") -PathType Leaf)) {
    throw "No se encontró la base histórica en $DataDir"
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw "Ya existe una tarea con el nombre $TaskName; no se reemplazó"
}

$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" " +
             "-InstallDir `"$InstallDir`" -DataDir `"$DataDir`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments `
                                  -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" `
    -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "Seguimiento diario del BORA para EPESF"
