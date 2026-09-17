param(
    [string]$InstallDir = "",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
if (-not $InstallDir) {
    $InstallDir = Split-Path -Parent $PSScriptRoot
}
$executable = Join-Path $InstallDir "epe-boletin.exe"
$dataDir = Join-Path $InstallDir "var"

if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "No se encontró el ejecutable: $executable"
}

& $executable --data-dir $dataDir serve --port $Port
