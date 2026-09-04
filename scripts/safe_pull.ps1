# safe_pull.ps1 — puxa codigo novo sem perder o estado local que os jobs
# agendados escrevem sem commitar (trials.json, h6_status.json, os dois
# atestados de harness). Por design (GarimpoInvestimentos/jobs.py), esses
# arquivos SO entram no git por decisao humana — este script preserva isso,
# so remove a fricao manual de stash/pull/pop repetida toda sessao.
#
# Uso: .\scripts\safe_pull.ps1 [-Branch main]

param(
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
Set-Location $proj

$dirty = git status --porcelain
if (-not $dirty) {
    Write-Host "Nada de local para preservar — pull direto." -ForegroundColor Cyan
    git pull origin $Branch
    exit $LASTEXITCODE
}

Write-Host "Estado local detectado (provavelmente escrita de job agendado):" -ForegroundColor Yellow
git status --short

$stashMsg = "safe_pull.ps1 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
git stash push -u -m $stashMsg
if ($LASTEXITCODE -ne 0) {
    Write-Error "git stash falhou — abortando antes de tocar no pull."
    exit 1
}

git pull origin $Branch
$pullExit = $LASTEXITCODE

Write-Host "Restaurando estado local..." -ForegroundColor Cyan
git stash pop
$popExit = $LASTEXITCODE

if ($popExit -ne 0) {
    Write-Warning "CONFLITO ao restaurar o estado local (provavelmente trials.json ou h6_status.json)."
    Write-Warning "O stash NAO foi descartado — resolva manualmente e rode 'git stash drop' so depois de confirmar."
    git status --short
    exit 1
}

if ($pullExit -ne 0) {
    Write-Warning "O pull retornou erro (exit $pullExit) mas o estado local foi restaurado com sucesso."
    exit $pullExit
}

Write-Host "Pull concluido e estado local preservado." -ForegroundColor Green
