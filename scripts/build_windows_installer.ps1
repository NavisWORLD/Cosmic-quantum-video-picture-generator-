param(
    [string]$Version = "0.2.0"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

python scripts/build_desktop.py

$IsccCandidates = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Iscc) {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install innosetup -y --no-progress
        $Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
}

if (-not $Iscc) {
    throw "Inno Setup 6 was not found. Install it or make ISCC.exe available."
}

& $Iscc "/DMyAppVersion=$Version" "packaging\windows\COSMOS.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE"
}

$Installer = Join-Path $Root "dist\installer\COSMOS-Media-Setup-Windows-x86_64.exe"
if (-not (Test-Path $Installer)) {
    throw "Expected installer not created: $Installer"
}

Write-Host "Windows installer ready: $Installer"
