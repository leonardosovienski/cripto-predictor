# Registra a tarefa diaria do attest-renew (item 0.2 do roadmap de 2026-08-21).
#
# Motivo: o atestado de poder vale 7 dias. Vencido, o Experiment Registry
# recusa registrar QUALQUER trial nova - o registry fecha. Ate aqui a renovacao
# era 100% manual, entao o prazo dependia de alguem lembrar. O job carrega
# --if-expiring-within 2 embutido (GarimpoInvestimentos/jobs.py): rodar todo dia
# NAO grava todo dia, so quando faltam menos de 2 dias para o vencimento.
#
# Nao afrouxa nada. O atestado so e gravado se o controle positivo passar nos
# quatro bracos (2 juizes x edge/ruido), como sempre.
#
# REGRA PERMANENTE: manter este arquivo em ASCII puro (sem acentos/travessoes).
# O PowerShell 5.1 le .ps1 sem BOM como Windows-1252 e bytes UTF-8 multibyte
# corrompem o parse (incidente V3.3.2).
#
# Uso: abra um PowerShell elevado (Executar como Administrador) e rode:
#   .\register_task_attest_renew.ps1
#
# Idempotente: se a tarefa ja existir, atualiza em vez de duplicar.

#Requires -RunAsAdministrator

param(
    [string]$TaskName = 'cripto-attest-renew',
    [string]$At       = '21:00',
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
$action  = New-ScheduledTaskAction -Execute $py -Argument "-m GarimpoInvestimentos.jobs attest-renew" -WorkingDirectory $proj
$trigger = New-ScheduledTaskTrigger -Daily -At $At

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
    Write-Host "OK: $TaskName atualizada (diaria as $At)" -ForegroundColor Green
} else {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
    Write-Host "OK: $TaskName registrada (diaria as $At)" -ForegroundColor Green
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
Write-Host "LastTaskResult 0 = OK. Com o atestado ainda longe do vencimento, o job"
Write-Host "roda e NAO grava - isso e o comportamento correto, nao falha."

# NAO usar Read-Host aqui. O runbook manda rodar este script de um PowerShell
# elevado ja aberto, e nesse modo um prompt no fim ENGOLE a proxima linha colada:
# em 2026-08-22 o operador colou o bloco inteiro e o `Start-ScheduledTask` virou
# a resposta do prompt, entao a tarefa nunca foi disparada e o
# Get-ScheduledTaskInfo mostrou 267011 (SCHED_S_TASK_HAS_NOT_RUN) com
# LastRunTime 30/11/1999. Parecia falha de registro; era o prompt comendo o
# comando. Quem executa por duplo-clique perde a janela no fim -- custo aceito,
# porque o caminho documentado e o do prompt ja aberto.
