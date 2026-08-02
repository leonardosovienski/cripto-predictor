# Portable V3 entrypoint for schedulers and containers.
# Keep ASCII only: Windows PowerShell 5.1 may parse UTF-8 without BOM as cp1252.
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
$py = Join-Path $proj ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Error "venv V3 ausente em $py"; exit 3 }
& $py -m GarimpoInvestimentos.jobs v3-daily
exit $LASTEXITCODE
