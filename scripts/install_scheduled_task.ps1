param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir,
    [Parameter(Mandatory = $true)]
    [string]$DataDir,
    [string]$TaskName = "EPESF - Boletín Oficial",
    [string]$StartTime = "05:30"
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $InstallDir "scripts\run_daily.ps1"
if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "No se encontró el script de ejecución: $runner"
}

$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" " +
             "-InstallDir `"$InstallDir`" -DataDir `"$DataDir`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments `
                                  -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -WakeToRun -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Seguimiento diario del BORA para EPESF" -Force
