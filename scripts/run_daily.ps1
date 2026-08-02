# Coleta diaria do GarimpoInvestimentos - o relogio da pesquisa.
# Fluxo: descoberta+ingestao (rede) -> analise offline (LLM) -> backtest (veredito).
# Adaptador portatil; o mesmo comando e usado por cron, systemd ou container.
# REGRA PERMANENTE: manter este arquivo em ASCII puro (sem acentos/travessoes).
# O PowerShell 5.1 le .ps1 sem BOM como Windows-1252 e bytes UTF-8 multibyte
# viram aspas/caracteres soltos, corrompendo o parse (incidente V3.3.2).
$ErrorActionPreference = "Continue"   # registra todas as etapas, mas nao esconde falhas

$proj = Split-Path -Parent $PSScriptRoot
$py   = Join-Path $proj ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$logDir = Join-Path $proj "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir ("cron_{0}.log" -f (Get-Date -Format "yyyyMMdd"))

Set-Location $proj
"==== run $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====" | Out-File -FilePath $log -Append -Encoding utf8

# 1) Coleta + analise sob lock/timeout/heartbeat/eventos do predictor_ops.
& $py -m GarimpoInvestimentos.jobs phase1 *>> $log
$ingestExit = $LASTEXITCODE
$analysisExit = $ingestExit
"---- phase1: exit $ingestExit ----" | Out-File -FilePath $log -Append -Encoding utf8

# 2) Backtest via o mesmo runner operacional instalado.
& $py -m GarimpoInvestimentos.jobs backtest *>> $log
$backtestExit = $LASTEXITCODE
$overallExit = 0
foreach ($stepExit in @($ingestExit, $analysisExit, $backtestExit)) {
    if ($overallExit -eq 0 -and $stepExit -ne 0) { $overallExit = [int]$stepExit }
}
"==== fim $(Get-Date -Format 'HH:mm:ss') (exit $overallExit) ====" | Out-File -FilePath $log -Append -Encoding utf8
exit $overallExit
