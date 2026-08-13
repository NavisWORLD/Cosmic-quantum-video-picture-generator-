$ErrorActionPreference = "Stop"

$Python = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$Venv = if ($env:COSMOS_VENV) { $env:COSMOS_VENV } else { ".venv" }

& $Python -m venv $Venv
$Activate = Join-Path $Venv "Scripts\Activate.ps1"
. $Activate
python -m pip install --upgrade pip
pip install -e ".[server,media,test]"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

cosmos-media doctor
Write-Host ""
Write-Host "COSMOS Media installed."
Write-Host "Run: .\.venv\Scripts\Activate.ps1; cosmos-media serve"
Write-Host "Open: http://127.0.0.1:8788/app/"
