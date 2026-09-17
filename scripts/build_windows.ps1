param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$Version = "0.1.0",
    [string]$GeminiKeyFile = "var\operacion\gemini_api_key.txt"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "No se encontró Python para construir el paquete: $Python"
}
$keySource = if ([IO.Path]::IsPathRooted($GeminiKeyFile)) {
    $GeminiKeyFile
} else {
    Join-Path $projectRoot $GeminiKeyFile
}
if (-not (Test-Path -LiteralPath $keySource -PathType Leaf)) {
    throw "No se encontró el archivo de clave de Gemini: $keySource"
}
if ((Get-Item -LiteralPath $keySource).Length -eq 0) {
    throw "El archivo de clave de Gemini está vacío: $keySource"
}

& $Python -m PyInstaller --noconfirm --clean --onedir `
    --name epe-boletin --paths src src\epe_boletin\__main__.py
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller no pudo construir el ejecutable"
}

$package = Join-Path $projectRoot "dist\epe-boletin"
Copy-Item -LiteralPath "config" -Destination (Join-Path $package "config") -Recurse
$dataDestination = Join-Path $package "var"
New-Item -ItemType Directory -Path $dataDestination -Force | Out-Null
Copy-Item -LiteralPath $keySource -Destination (Join-Path $dataDestination "gemini_api_key.txt") -Force
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
