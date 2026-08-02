# Alinha a config de energia da GarimpoFase1 com a GarimpoV3Daily.
#
# Motivo: em 2026-07-12 a GarimpoFase1 falhou as 22:00 com 0x800710E0
# ("operador ou administrador recusou") sem invocar o Python (nenhuma linha
# nova no log daquela execucao). Diferenca encontrada: GarimpoFase1 tinha
# DisallowStartIfOnBatteries=True e StartWhenAvailable=False, enquanto a
# GarimpoV3Daily (que rodou OK no mesmo periodo) tinha ambos ajustados para
# tolerar bateria/disponibilidade. Alinhar remove essa hipotese como causa.
#
# Uso: abra um PowerShell elevado (Executar como Administrador) e rode:
#   .\fix_task_power.ps1

#Requires -RunAsAdministrator

$task = Get-ScheduledTask -TaskName 'GarimpoFase1'
$settings = $task.Settings
$settings.DisallowStartIfOnBatteries = $false
$settings.StopIfGoingOnBatteries = $false
$settings.StartWhenAvailable = $true

try {
    Set-ScheduledTask -TaskName 'GarimpoFase1' -Settings $settings | Out-Null
    Write-Host "OK: GarimpoFase1 -> energia alinhada" -ForegroundColor Green
} catch {
    Write-Host "FALHOU: $($_.Exception.Message)" -ForegroundColor Red
}

$x = Get-ScheduledTask -TaskName 'GarimpoFase1'
[PSCustomObject]@{
    Task                        = 'GarimpoFase1'
    DisallowStartIfOnBatteries  = $x.Settings.DisallowStartIfOnBatteries
    StopIfGoingOnBatteries      = $x.Settings.StopIfGoingOnBatteries
    StartWhenAvailable          = $x.Settings.StartWhenAvailable
    LogonType                   = $x.Principal.LogonType
} | Format-Table -AutoSize

# Habilita o log operacional do Task Scheduler, para capturar o codigo Win32
# exato (nao so o generico 0x800710E0) se alguma tarefa falhar de novo.
try {
    wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true
    Write-Host "OK: log operacional do Task Scheduler habilitado" -ForegroundColor Green
} catch {
    Write-Host "FALHOU ao habilitar log operacional: $($_.Exception.Message)" -ForegroundColor Red
}

Read-Host "`nPressione Enter para fechar"


