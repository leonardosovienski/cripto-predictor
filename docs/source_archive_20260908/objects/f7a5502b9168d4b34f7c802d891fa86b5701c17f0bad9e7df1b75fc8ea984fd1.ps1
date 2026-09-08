# Registra a tarefa semanal de backup do Feature Store.
#
# As previsoes vivem SO no feature_store.db desta maquina. A tabela e append-only
# (migracao 0016: DELETE bloqueado por trigger, UPDATE arquiva o estado anterior),
# entao nada se perde por sobrescrita -- mas isso nao protege contra disco,
# maquina ou rm. Este projeto ja perdeu as 440 previsoes brutas da H5 em
# definitivo; o backup e a unica defesa contra repetir isso.
#
# Domingo 20:00 fica livre entre os gatilhos existentes (watchdog 19:00,
# attest-renew 21:00, GarimpoFase1 22:00). O job usa sqlite3.Connection.backup,
# consistente com WAL, entao nao precisa parar a coleta.
#
# O destino sai em DATA_DIR/backups com carimbo de tempo no nome, entao execucoes
# sucessivas nunca colidem e nenhum backup e sobrescrito.
#
# Nasce com as mesmas duas configuracoes que os fix_task_*.ps1 tiveram que
# corrigir depois nas outras tarefas: energia (0x800710E0) e LogonType S4U
# (0x80070005). Idempotente.
#
# Uso: abra um PowerShell elevado (Executar como Administrador) e rode:
#   .\scripts\register_task_backup.ps1

#Requires -RunAsAdministrator

param(
    [string]$TaskName = 'cripto-backup-featurestore',
    [string]$At       = '20:00',
    [string]$UserId   = $env:USERNAME
)

$ErrorActionPreference = "Stop"

$proj = Split-Path -Parent $PSScriptRoot
$py   = Join-Path $proj ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "AVISO: $py nao existe ainda. Rode um dos .bat uma vez para criar o .venv," -ForegroundColor Yellow
    Write-Host "       ou a tarefa vai falhar no primeiro disparo." -ForegroundColor Yellow
}

# 21:00 fica livre entre os gatilhos existentes (watchdog 19:00, GarimpoFase1
# 22:00, watchdog 22:30) e antes da coleta - assim, se o atestado for renovado,
# ele ja esta valido quando a coleta da noite roda.
$action  = New-ScheduledTaskAction -Execute $py -Argument "-m GarimpoInvestimentos.jobs backup" -WorkingDirectory $proj
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $At

# Mesma config de energia que os fix_task_power*.ps1 aplicaram nas outras
# tarefas: DisallowStartIfOnBatteries/StopIfGoingOnBatteries desligados e
# StartWhenAvailable ligado. Sem isso, o modo de falha 0x800710E0 volta - e ele
# e silencioso (o Agendador barra antes do Python, nada aparece no log da app).
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# S4U, nao Interactive: permite execucao headless (tela bloqueada ou usuario
# deslogado) sem salvar senha em texto plano. Interactive falha com 0x80070005
# (Access Denied), tambem sem rastro no log da aplicacao.
$principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType S4U -RunLevel Limited

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Set-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
    Write-Host "OK: $TaskName atualizada (domingos as $At)" -ForegroundColor Green
} else {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
    Write-Host "OK: $TaskName registrada (domingos as $At)" -ForegroundColor Green
}

$x = Get-ScheduledTask -TaskName $TaskName
[PSCustomObject]@{
    Task                       = $TaskName
    LogonType                  = $x.Principal.LogonType
    UserId                     = $x.Principal.UserId
    DisallowStartIfOnBatteries = $x.Settings.DisallowStartIfOnBatteries
    StartWhenAvailable         = $x.Settings.StartWhenAvailable
    Triggers                   = ($x.Triggers | ForEach-Object { $_.StartBoundary }) -join ', '
} | Format-Table -AutoSize

Write-Host "`nTeste imediato (nao espera o horario):" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName $TaskName"
Write-Host "  Get-ScheduledTaskInfo -TaskName $TaskName | Select LastRunTime, LastTaskResult"
Write-Host "LastTaskResult 0 = OK. Cada execucao grava um backup novo, com carimbo"
Write-Host "de tempo no nome - nenhum backup anterior e sobrescrito."

# NAO usar Read-Host aqui. O runbook manda rodar este script de um PowerShell
# elevado ja aberto, e nesse modo um prompt no fim ENGOLE a proxima linha colada:
# em 2026-08-22 o operador colou o bloco inteiro e o `Start-ScheduledTask` virou
# a resposta do prompt, entao a tarefa nunca foi disparada e o
# Get-ScheduledTaskInfo mostrou 267011 (SCHED_S_TASK_HAS_NOT_RUN) com
# LastRunTime 30/11/1999. Parecia falha de registro; era o prompt comendo o
# comando. Quem executa por duplo-clique perde a janela no fim -- custo aceito,
# porque o caminho documentado e o do prompt ja aberto.
