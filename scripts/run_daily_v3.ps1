# Observable Task Scheduler entrypoint for the V3 daily pipeline.
# Keep ASCII only: Windows PowerShell 5.1 may parse UTF-8 without BOM as cp1252.
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
$workspace = Split-Path -Parent $proj
$py = Join-Path $proj ".venv_v3\Scripts\python.exe"
$runner = Join-Path $workspace "tools\operational_runner.py"
$payload = Join-Path $PSScriptRoot "run_daily_v3_payload.ps1"

if (-not (Test-Path $py)) { Write-Error "venv V3 ausente em $py"; exit 3 }
if (-not (Test-Path $runner)) { Write-Error "operational runner ausente em $runner"; exit 3 }
if (-not (Test-Path $payload)) { Write-Error "payload V3 ausente em $payload"; exit 3 }

& $py $runner run --task "GarimpoV3Daily" --project "previsao-cripto" --cwd $proj --log (Join-Path $proj "logs\operations\GarimpoV3Daily.log") --event-log (Join-Path $proj "logs\operations\events.jsonl") --heartbeat (Join-Path $proj "logs\operations\GarimpoV3Daily.heartbeat.json") --expected-artifact (Join-Path $proj "data\v3\events_v3.jsonl") --timeout 252000 -- powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $payload
exit $LASTEXITCODE
