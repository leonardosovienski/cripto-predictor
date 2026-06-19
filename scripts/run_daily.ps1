# Executa o pipeline Garimpo uma vez e registra a saída em logs/cron_<data>.log.
# Pensado para o Agendador de Tarefas do Windows (ver README — seção "Agendamento diário").
$ErrorActionPreference = "Stop"

# Raiz canônica do projeto (corrigida: era C:\Claude\ProjetosPython, que não existe
# mais — o pacote vive agora em C:\Claude\previsao-cripto).
$proj = "C:\Claude\previsao-cripto"
$py   = Join-Path $proj "GarimpoInvestimentos\env\Scripts\python.exe"
$logDir = Join-Path $proj "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir ("cron_{0}.log" -f (Get-Date -Format "yyyyMMdd"))

Set-Location $proj
"==== run $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====" | Out-File -FilePath $log -Append -Encoding utf8
& $py -m GarimpoInvestimentos.main *>> $log
"==== fim (exit $LASTEXITCODE) ===="                      | Out-File -FilePath $log -Append -Encoding utf8
