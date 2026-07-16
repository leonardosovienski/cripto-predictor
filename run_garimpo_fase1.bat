@echo off
rem ============================================================================
rem run_garimpo_fase1.bat - entry point do Windows Task Scheduler (diario, 22h)
rem Orquestra a coleta H5 (Multi-Juiz) via scripts\garimpo_fase1.py.
rem Caminhos ABSOLUTOS: o Task Scheduler nao herda cwd nem PATH do usuario.
rem O venv real do projeto e GarimpoInvestimentos\env (nao .venv).
rem Manter este arquivo em ASCII puro (mesma regra dos .ps1 do projeto).
rem ============================================================================

set "PROJ=C:\Claude-projetos\Claude\previsao-cripto"
set "VENV=%PROJ%\GarimpoInvestimentos\env"

cd /d "%PROJ%" || exit /b 1

"%VENV%\Scripts\python.exe" "%PROJ%\..\tools\operational_runner.py" run --task "GarimpoFase1" --project "previsao-cripto" --cwd "%PROJ%" --log "%PROJ%\logs\operations\GarimpoFase1.log" --event-log "%PROJ%\logs\operations\events.jsonl" --heartbeat "%PROJ%\logs\operations\GarimpoFase1.heartbeat.json" --expected-artifact "%PROJ%\output\feature_store.db" --timeout 252000 -- "%VENV%\Scripts\python.exe" -X utf8 "%PROJ%\scripts\garimpo_fase1.py"
set "RC=%ERRORLEVEL%"

rem Backtest H5 (Spearman+IC95+DSR) orfao desde que a ColetaDiaria foi
rem desabilitada (11/07); roda aqui apos a coleta, sem gastar cota de LLM.
rem Roda mesmo com a coleta falha (analisa o que ja amadureceu), mas o exit
rem code da coleta tem precedencia sobre o do backtest.
"%VENV%\Scripts\python.exe" "%PROJ%\..\tools\operational_runner.py" run --task "GarimpoBacktest" --project "previsao-cripto" --cwd "%PROJ%" --log "%PROJ%\logs\operations\GarimpoBacktest.log" --event-log "%PROJ%\logs\operations\events.jsonl" --heartbeat "%PROJ%\logs\operations\GarimpoBacktest.heartbeat.json" --expected-artifact "%PROJ%\output\garimpo_backtest.csv" --timeout 1800 -- "%VENV%\Scripts\python.exe" -X utf8 -m GarimpoInvestimentos.analyzers.backtest
set "RC_BT=%ERRORLEVEL%"

set "RC_FINAL=%RC%"
if "%RC%"=="0" set "RC_FINAL=%RC_BT%"

echo garimpo_fase1 finalizado com exit code %RC% (backtest: %RC_BT%)
exit /b %RC_FINAL%
