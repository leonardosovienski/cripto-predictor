# Coleta diaria do GarimpoInvestimentos - o relogio da pesquisa.
# Fluxo: descoberta+ingestao (rede) -> analise offline (LLM) -> backtest (veredito).
# Registrado no Agendador do Windows (ver README). Log em logs/cron_<data>.log.
# REGRA PERMANENTE: manter este arquivo em ASCII puro (sem acentos/travessoes).
# O PowerShell 5.1 le .ps1 sem BOM como Windows-1252 e bytes UTF-8 multibyte
# viram aspas/caracteres soltos, corrompendo o parse (incidente V3.3.2).
$ErrorActionPreference = "Continue"   # uma etapa falhar nao pode calar as seguintes

$proj = "C:\Claude-projetos\Claude\previsao-cripto"
$py   = Join-Path $proj "GarimpoInvestimentos\env\Scripts\python.exe"
$logDir = Join-Path $proj "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir ("cron_{0}.log" -f (Get-Date -Format "yyyyMMdd"))

Set-Location $proj
"==== run $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====" | Out-File -FilePath $log -Append -Encoding utf8

# 1) Descoberta + ingestao (DPL, fallback; ~10 candidatos = cota LLM free tier)
& $py -m GarimpoInvestimentos.main --ingest --discover 10 *>> $log
"---- ingestao: exit $LASTEXITCODE ----" | Out-File -FilePath $log -Append -Encoding utf8

# 2) Analise offline (universo = Feature Store; previsoes carimbadas Juiz+Fonte)
& $py -m GarimpoInvestimentos.main --summary *>> $log
"---- analise: exit $LASTEXITCODE ----" | Out-File -FilePath $log -Append -Encoding utf8

# 3) Backtest (Spearman+IC95 estratificado por Fonte + DSR; amadurece com o tempo)
& $py -m GarimpoInvestimentos.analyzers.backtest *>> $log
"==== fim $(Get-Date -Format 'HH:mm:ss') (exit $LASTEXITCODE) ====" | Out-File -FilePath $log -Append -Encoding utf8
