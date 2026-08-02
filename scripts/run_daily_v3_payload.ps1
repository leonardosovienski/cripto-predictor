# Compatibility wrapper. Supervision is implemented by predictor_ops.
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
$py = Join-Path $proj ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Error "venv V3 ausente em $py"; exit 3 }
& $py -m GarimpoInvestimentos.jobs v3-daily
exit $LASTEXITCODE
