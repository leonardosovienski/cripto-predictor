@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PYTHONUTF8=1"
pushd "%PROJECT_DIR%"

where uv >nul 2>nul
if errorlevel 1 (
    echo uv nao encontrado no PATH. Instale com: pip install uv
    popd
    exit /b 1
)

rem O mesmo .venv e compartilhado por phase1, v3-daily e microstructure-live
rem (GarimpoInvestimentos/jobs.py usa sys.executable para todos). Sincronizar
rem so --extra llm+excel (como run_sinal_diario.bat fazia) DESINSTALA numpy/
rem scipy/hmmlearn/ccxt (extra v3), quebrando a familia V3/HMM na proxima
rem execucao dela. Sincronizar tudo junto sempre (auditoria 2026-08-19).
echo === Sync do ambiente (uv: llm + excel + v3) ===
uv sync --extra llm --extra excel --extra v3
if errorlevel 1 (
    echo uv sync falhou.
    popd
    exit /b %errorlevel%
)

if exist "%PROJECT_DIR%.venv\Scripts\python.exe" (set "PYTHON=%PROJECT_DIR%.venv\Scripts\python.exe") else (set "PYTHON=python")
"%PYTHON%" -m GarimpoInvestimentos.jobs phase1
if errorlevel 1 exit /b %errorlevel%
"%PYTHON%" -m GarimpoInvestimentos.jobs backtest
set "RESULT=%errorlevel%"

rem Publica o painel diario e o historico local da H6 fora do git -
rem quality_snapshot_history.jsonl. h6_status.json continua exigindo commit
rem a mao. Roda por conta propria: falha aqui NAO deve mascarar o resultado
rem do phase1/backtest, que e' o que decide o exit code desta tarefa.
"%PYTHON%" -m GarimpoInvestimentos.jobs quality-snapshot

popd
exit /b %RESULT%
