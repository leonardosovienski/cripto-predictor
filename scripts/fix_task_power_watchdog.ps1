# Alinha a config de energia do cripto-watchdog-coleta com as tarefas de coleta.
#
# Motivo: em 2026-07-18 19:00 o watchdog NAO rodou; a tentativa atrasada de
# 2026-07-19 00:14 falhou com 0x800710E0 ("operador ou administrador recusou")
# -- o MESMO erro da GarimpoFase1 em 2026-07-12. O fix_task_power.ps1 daquela
# epoca corrigiu SO a GarimpoFase1; o watchdog ficou com
# DisallowStartIfOnBatteries=True, StopIfGoingOnBatteries=True e
# StartWhenAvailable=False (verificado read-only em 2026-07-19). Ou seja: o
# guardiao da coleta falha exatamente na condicao (maquina indisponivel no
# horario) que ele existe para vigiar. As coletas em si (GarimpoFase1,
# GarimpoV3Daily) ja toleram isso e rodaram normalmente.
#
# Manter este arquivo em ASCII puro (regra dos .ps1 do projeto).
# Uso: abra um PowerShell elevado (Executar como Administrador) e rode:
#   .\fix_task_power_watchdog.ps1

#Requires -RunAsAdministrator

$taskName = 'cripto-watchdog-coleta'
$task = Get-ScheduledTask -TaskName $taskName
$settings = $task.Settings
$settings.DisallowStartIfOnBatteries = $false
$settings.StopIfGoingOnBatteries = $false
$settings.StartWhenAvailable = $true

try {
    Set-ScheduledTask -TaskName $taskName -Settings $settings | Out-Null
    Write-Host "OK: $taskName -> energia alinhada" -ForegroundColor Green
} catch {
    Write-Host "FALHOU: $($_.Exception.Message)" -ForegroundColor Red
}

$x = Get-ScheduledTask -TaskName $taskName
[PSCustomObject]@{
    Task                        = $taskName
    DisallowStartIfOnBatteries  = $x.Settings.DisallowStartIfOnBatteries
    StopIfGoingOnBatteries      = $x.Settings.StopIfGoingOnBatteries
    StartWhenAvailable          = $x.Settings.StartWhenAvailable
    LogonType                   = $x.Principal.LogonType
} | Format-Table -AutoSize

Read-Host "`nPressione Enter para fechar"
