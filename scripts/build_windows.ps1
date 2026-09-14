param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "No se encontró Python para construir el paquete: $Python"
}

& $Python -m PyInstaller --noconfirm --clean --onedir `
    --name epe-boletin --paths src src\epe_boletin\__main__.py
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller no pudo construir el ejecutable"
}

$package = Join-Path $projectRoot "dist\epe-boletin"
Copy-Item -LiteralPath "config" -Destination (Join-Path $package "config") -Recurse
$scriptDestination = Join-Path $package "scripts"
New-Item -ItemType Directory -Path $scriptDestination -Force | Out-Null
Copy-Item -LiteralPath "scripts\run_daily.ps1" -Destination $scriptDestination
Copy-Item -LiteralPath "scripts\install_scheduled_task.ps1" -Destination $scriptDestination
Copy-Item -LiteralPath "scripts\run_ui.ps1" -Destination $scriptDestination
Copy-Item -LiteralPath "README.md" -Destination $package
Copy-Item -LiteralPath "OPERACION_WINDOWS.md" -Destination $package

$archive = Join-Path $projectRoot "dist\epe-boletin-$Version-windows-x64.zip"
if (Test-Path -LiteralPath $archive) {
    Remove-Item -LiteralPath $archive -Force
}
Compress-Archive -LiteralPath $package -DestinationPath $archive -CompressionLevel Optimal
Write-Output $archive
