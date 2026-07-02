# =====================================================================
# Feed diario do V3 Crypto-Predictor (paper trading shadow).
#
# IMPORTANTE: arquivo em ASCII puro de proposito. O Windows PowerShell 5.1
# le .ps1 sem BOM como Windows-1252; caracteres nao-ASCII (em-dash, acentos)
# corrompem o parse (o byte 0x94 do em-dash UTF-8 vira aspas) -> exit 1 sem log.
# Mantenha este script SEM acentos e SEM travessoes.
#
# Fluxo NAO-DESTRUTIVO:
#   1. vision_ingest -> estende o historico (funding/OI/klines) do data lake
#      publico da Binance ate ONTEM, preservando 2021->hoje (cache local SHA256).
#   2. pipeline (SEM --force-refresh) -> reconstroi features + carrega o modelo
#      HMM treinado e infere o sinal causal mais recente.
#   3. paper_trader -> registra o trade teorico (k=0.50 homologado).
#   4. paper_report -> P&L acumulado, MaxDD corrente, hit rate.
#
# NUNCA usar `pipeline --force-refresh` aqui: o OICollector REST clampa em 30
# dias e SOBRESCREVERIA os 433k registros historicos de OI (base do HMM).
#
# Auto-ancorado: raiz do projeto via $PSScriptRoot (sem path hardcoded).
# Agendado via schtasks (ver HANDOFF.md V3.3 - Producao Assistida).
# =====================================================================
$ErrorActionPreference = "Stop"

$proj = Split-Path -Parent $PSScriptRoot
$py   = Join-Path $proj ".venv_v3\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Error "venv V3 ausente em $py - crie com py -3.13 -m venv .venv_v3 e instale requirements.txt"
    exit 1
}

# Simbolos a operar. ETHUSDT/SOLUSDT so apos ingestao + sweep GO (ver HANDOFF V3.3).
$symbols = @("BTCUSDT")
$startDate = "2021-01-01"
# Ontem em UTC - o data lake tem lag; pedir "hoje" retornaria 404 (parser ignora).
$endDate = ([DateTime]::UtcNow.AddDays(-1)).ToString("yyyy-MM-dd")

$logDir = Join-Path $proj "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir ("v3_daily_{0}.log" -f (Get-Date -Format "yyyyMMdd"))

$env:PYTHONPATH = (Join-Path $proj "vendor") + ";" + $proj
$env:PREDICTOR_EVENTS_PATH = Join-Path $proj "data\v3\events_v3.jsonl"

Set-Location $proj
"==== run $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (endDate=$endDate UTC) ====" | Out-File -FilePath $log -Append -Encoding utf8

foreach ($sym in $symbols) {
    "---- [$sym] vision_ingest (estende historico, nao-destrutivo) ----" | Out-File -FilePath $log -Append -Encoding utf8
    & $py -m GarimpoInvestimentos.v3.vision_ingest --symbol $sym --start-date $startDate --end-date $endDate *>> $log

    "---- [$sym] pipeline (SEM force-refresh; usa modelo treinado) ----" | Out-File -FilePath $log -Append -Encoding utf8
    & $py -m GarimpoInvestimentos.v3.pipeline --symbol $sym --start-date $startDate *>> $log

    "---- [$sym] paper_trader (k=0.50) ----" | Out-File -FilePath $log -Append -Encoding utf8
    & $py -m GarimpoInvestimentos.v3.paper_trader --symbol $sym --start-date $startDate *>> $log
}

"---- paper_report ($($symbols -join ', ')) ----" | Out-File -FilePath $log -Append -Encoding utf8
& $py -m GarimpoInvestimentos.v3.paper_report --symbol $symbols *>> $log

"==== fim (exit $LASTEXITCODE) ====" | Out-File -FilePath $log -Append -Encoding utf8
