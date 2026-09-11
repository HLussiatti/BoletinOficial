param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir,
    [Parameter(Mandatory = $true)]
    [string]$DataDir
)

$ErrorActionPreference = "Stop"
$executable = Join-Path $InstallDir "epe-boletin.exe"
$rules = Join-Path $InstallDir "config\relevance_rules.json"

if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "No se encontró el ejecutable: $executable"
}

& $executable --data-dir $DataDir --rules $rules run --mode daily
exit $LASTEXITCODE
