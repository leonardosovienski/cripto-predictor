# V3 pipeline payload. Called only by run_daily_v3.ps1 through operational_runner.
# Keep ASCII only: Windows PowerShell 5.1 may parse UTF-8 without BOM as cp1252.
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
$py = Join-Path $proj ".venv_v3\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Error "venv V3 ausente em $py"; exit 3 }

$symbols = @("BTCUSDT")
$startDate = "2021-01-01"
$endDate = ([DateTime]::UtcNow.AddDays(-1)).ToString("yyyy-MM-dd")
$logDir = Join-Path $proj "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir ("v3_daily_{0}.log" -f (Get-Date -Format "yyyyMMdd"))
$env:PYTHONPATH = (Join-Path $proj "vendor") + ";" + $proj
$env:PREDICTOR_EVENTS_PATH = Join-Path $proj "data\v3\events_v3.jsonl"

function Invoke-V3Step([string]$label, [scriptblock]$command) {
    "---- $label ----" | Out-File -FilePath $log -Append -Encoding utf8
    # PS 5.1: '*>>' grava UTF-16 e quebrava o log. Stringificar cada linha
    # (ErrorRecords viram texto) e anexar em UTF-8 explicito.
    & $command 2>&1 | ForEach-Object { $_.ToString() } | Out-File -FilePath $log -Append -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        "---- $label FAILED (exit $LASTEXITCODE) ----" | Out-File -FilePath $log -Append -Encoding utf8
        exit $LASTEXITCODE
    }
}

Set-Location $proj
"==== run $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (endDate=$endDate UTC) ====" | Out-File -FilePath $log -Append -Encoding utf8
foreach ($sym in $symbols) {
    Invoke-V3Step "[$sym] vision_ingest" { & $py -m GarimpoInvestimentos.v3.vision_ingest --symbol $sym --start-date $startDate --end-date $endDate }
    Invoke-V3Step "[$sym] pipeline (without force-refresh)" { & $py -m GarimpoInvestimentos.v3.pipeline --symbol $sym --start-date $startDate }
    Invoke-V3Step "[$sym] paper_trader (k=0.50)" { & $py -m GarimpoInvestimentos.v3.paper_trader --symbol $sym --start-date $startDate }
}
Invoke-V3Step "paper_report ($($symbols -join ', '))" { & $py -m GarimpoInvestimentos.v3.paper_report --symbol $symbols }
"==== fim (exit 0) ====" | Out-File -FilePath $log -Append -Encoding utf8
exit 0
