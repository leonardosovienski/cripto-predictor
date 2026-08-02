# Corrige o LogonType de tarefas do Agendador de Windows que rodam automacao
# do previsao-cripto de Interactive para S4U, permitindo execucao headless
# (tela bloqueada / usuario deslogado) sem salvar senha em texto plano.
#
# Motivo: tarefas Interactive falham com 0x80070005 (Access Denied) quando
# disparadas sem sessao interativa ativa, sem deixar rastro nos logs da
# aplicacao (o Agendador bloqueia antes do Python ser invocado).
#
# Uso: clique com o botao direito -> "Executar com o PowerShell" como
# Administrador, ou abra um PowerShell elevado e rode:
#   .\fix_task_logon.ps1

#Requires -RunAsAdministrator

$tasks = 'cripto-watchdog-coleta', 'GarimpoFase1', 'GarimpoV3Daily'

foreach ($t in $tasks) {
    try {
        $principal = New-ScheduledTaskPrincipal -UserId 'Superleo13' -LogonType S4U -RunLevel Limited
        Set-ScheduledTask -TaskName $t -Principal $principal | Out-Null
        Write-Host "OK: $t -> S4U" -ForegroundColor Green
    } catch {
        Write-Host "FALHOU: $t -> $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nEstado final:"
$tasks | ForEach-Object {
    $x = Get-ScheduledTask -TaskName $_
    [PSCustomObject]@{ Task = $_; LogonType = $x.Principal.LogonType; UserId = $x.Principal.UserId }
} | Format-Table -AutoSize

Read-Host "`nPressione Enter para fechar"


