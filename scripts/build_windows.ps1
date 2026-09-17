param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$Version = "0.1.0",
    [string]$HistoricalDataDir = "var\operacion",
    [string]$GeminiKeyFile = "",
    [string]$SnapshotTag = (Get-Date -Format "yyyyMMdd")
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "No se encontró Python para construir el paquete: $Python"
}
$dataSource = if ([IO.Path]::IsPathRooted($HistoricalDataDir)) {
    $HistoricalDataDir
} else {
    Join-Path $projectRoot $HistoricalDataDir
}
if (-not (Test-Path -LiteralPath (Join-Path $dataSource "boletin.sqlite3") -PathType Leaf)) {
    throw "No se encontró la base histórica en $dataSource"
}
if (-not $GeminiKeyFile) {
    $GeminiKeyFile = Join-Path $dataSource "gemini_api_key.txt"
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
$setupDestination = Join-Path $package "setup"
New-Item -ItemType Directory -Path $setupDestination -Force | Out-Null
Copy-Item -LiteralPath $keySource -Destination (Join-Path $setupDestination "gemini_api_key.txt") -Force
$historicalBackup = Join-Path $setupDestination "historico.zip"
& (Join-Path $package "epe-boletin.exe") --data-dir $dataSource `
    --rules (Join-Path $projectRoot "config\relevance_rules.json") `
    backup $historicalBackup
if ($LASTEXITCODE -ne 0) {
    throw "No se pudo crear el respaldo verificado del histórico"
}
$scriptDestination = Join-Path $package "scripts"
New-Item -ItemType Directory -Path $scriptDestination -Force | Out-Null
Copy-Item -LiteralPath "scripts\run_daily.ps1" -Destination $scriptDestination
Copy-Item -LiteralPath "scripts\install_scheduled_task.ps1" -Destination $scriptDestination
Copy-Item -LiteralPath "scripts\install_package.ps1" -Destination $scriptDestination
Copy-Item -LiteralPath "scripts\run_ui.ps1" -Destination $scriptDestination
Copy-Item -LiteralPath "README.md" -Destination $package
Copy-Item -LiteralPath "OPERACION_WINDOWS.md" -Destination $package
Copy-Item -LiteralPath "INSTALL_WINDOWS.md" -Destination $package

$archive = Join-Path $projectRoot "dist\epe-boletin-$Version-windows-x64-historico-$SnapshotTag.zip"
if (Test-Path -LiteralPath $archive) {
    Remove-Item -LiteralPath $archive -Force
}
Compress-Archive -LiteralPath $package -DestinationPath $archive -CompressionLevel Optimal
if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
    throw "No se creó el ZIP de distribución"
}
$hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$archive.sha256" -Encoding ascii `
    -Value "$hash  $(Split-Path -Leaf $archive)"
Write-Output $archive
Write-Output "SHA-256: $hash"
