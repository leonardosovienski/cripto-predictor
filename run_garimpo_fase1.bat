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

call "%VENV%\Scripts\activate.bat"

"%VENV%\Scripts\python.exe" "%PROJ%\scripts\garimpo_fase1.py"
set "RC=%ERRORLEVEL%"

echo garimpo_fase1 finalizado com exit code %RC%
exit /b %RC%
