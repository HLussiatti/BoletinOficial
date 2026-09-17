param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "EPESF\Boletin"),
    [string]$TaskName = "EPESF - Boletin Oficial"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $PSScriptRoot
$sourceExe = Join-Path $packageRoot "epe-boletin.exe"
$archive = Join-Path $packageRoot "setup\historico.zip"
$keyFile = Join-Path $packageRoot "setup\gemini_api_key.txt"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Abrí PowerShell como administrador para registrar la tarea diaria"
}
foreach ($source in @($sourceExe, $archive, $keyFile)) {
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Falta un archivo del paquete: $source"
    }
}

$InstallDir = [IO.Path]::GetFullPath($InstallDir).TrimEnd('\')
$packageFull = [IO.Path]::GetFullPath($packageRoot).TrimEnd('\')
if ($InstallDir.StartsWith($packageFull + '\', [StringComparison]::OrdinalIgnoreCase) -or
    $packageFull.StartsWith($InstallDir + '\', [StringComparison]::OrdinalIgnoreCase) -or
    $InstallDir -eq $packageFull) {
    throw "La carpeta de instalación debe estar fuera del paquete extraído"
}
if (Test-Path -LiteralPath $InstallDir) {
    throw "La carpeta de instalación ya existe: $InstallDir. No se sobrescribieron datos"
}
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw "Ya existe una tarea programada con el nombre $TaskName"
}

$parent = Split-Path -Parent $InstallDir
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$stage = Join-Path $parent (".epe-boletin-install-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
$installed = $false
try {
    Get-ChildItem -LiteralPath $packageRoot -Force |
        Where-Object { $_.Name -ne 'setup' } |
        ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $stage -Recurse }
    Move-Item -LiteralPath $stage -Destination $InstallDir
    $installed = $true

    $dataDir = Join-Path $InstallDir "var\operacion"
    & (Join-Path $InstallDir "epe-boletin.exe") restore $archive $dataDir
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo restaurar o verificar el histórico"
    }
    Copy-Item -LiteralPath $keyFile -Destination (Join-Path $dataDir "gemini_api_key.txt")
    & (Join-Path $InstallDir "epe-boletin.exe") --data-dir $dataDir status | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "La base restaurada no pasó la verificación de estado"
    }
} catch {
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
    if ($installed -and (Test-Path -LiteralPath $InstallDir)) {
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
    }
    throw
}

& (Join-Path $InstallDir "scripts\install_scheduled_task.ps1") `
    -InstallDir $InstallDir -DataDir $dataDir -TaskName $TaskName -StartTime "05:30"
Write-Output "Aplicación instalada en $InstallDir"
Write-Output "Base histórica restaurada en $dataDir"
Write-Output "Tarea diaria $TaskName registrada para las 05:30"
