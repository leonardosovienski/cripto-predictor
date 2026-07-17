# Adiciona o 2o gatilho diario (22:30) ao cripto-watchdog-coleta.
# Motivo (triagem 16/07, item b): com gatilho unico as 19:00, uma falha da
# GarimpoFase1 (22:00) so alerta ~21h depois. O disparo das 22:30 pega a falha
# ainda na mesma noite (a coleta leva minutos; 30min de folga).
# Rodar como Administrador (mesma exigencia dos fix_task_*.ps1 anteriores).
# Idempotente: nao duplica o gatilho se ja existir.
$ErrorActionPreference = "Stop"
$taskName = "cripto-watchdog-coleta"

$task = Get-ScheduledTask -TaskName $taskName
$existing = @($task.Triggers | Where-Object {
    $_.StartBoundary -match "T22:30"
})
if ($existing.Count -gt 0) {
    Write-Host "Gatilho 22:30 ja existe em $taskName - nada a fazer."
    exit 0
}

$novo = New-ScheduledTaskTrigger -Daily -At "22:30"
$triggers = @($task.Triggers) + $novo
Set-ScheduledTask -TaskName $taskName -Trigger $triggers | Out-Null

$depois = (Get-ScheduledTask -TaskName $taskName).Triggers | ForEach-Object { $_.StartBoundary }
Write-Host "OK: gatilhos de $taskName agora: $($depois -join ', ')"
