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

echo garimpo_fase1 finalizado com exit code %RC%
exit /b %RC%
