param(
    [string]$InstallDir = "C:\EPESF\Boletin",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$executable = Join-Path $InstallDir "epe-boletin.exe"
$dataDir = Join-Path $InstallDir "var"

if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "No se encontró el ejecutable: $executable"
}

& $executable --data-dir $dataDir serve --port $Port
