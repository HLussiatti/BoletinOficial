param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir,
    [Parameter(Mandatory = $true)]
    [string]$DataDir,
    [string]$GeminiKeyFile = ""
)

$ErrorActionPreference = "Stop"
$executable = Join-Path $InstallDir "epe-boletin.exe"
$rules = Join-Path $InstallDir "config\relevance_rules.json"

if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "No se encontró el ejecutable: $executable"
}

Set-Location -LiteralPath $InstallDir
& $executable --data-dir $DataDir --rules $rules run --mode daily
$collectionExitCode = $LASTEXITCODE
if ($collectionExitCode -ne 0) {
    exit $collectionExitCode
}

if (-not $env:GEMINI_API_KEY) {
    $keyCandidates = @()
    if ($GeminiKeyFile) {
        $keyCandidates += $GeminiKeyFile
    }
    $keyCandidates += (Join-Path $DataDir "gemini_api_key.txt")
    $keyCandidates += (Join-Path $InstallDir "gemini_api_key.txt")
    $keyPath = $keyCandidates | Where-Object {
        Test-Path -LiteralPath $_ -PathType Leaf
    } | Select-Object -First 1
    if (-not $keyPath) {
        throw "No se encontró GEMINI_API_KEY ni el archivo gemini_api_key.txt"
    }
    $env:GEMINI_API_KEY = (Get-Content -LiteralPath $keyPath -Raw).Trim()
}

$today = Get-Date -Format "yyyy-MM-dd"
& $executable --data-dir $DataDir summarize --provider gemini --date $today
exit $LASTEXITCODE
