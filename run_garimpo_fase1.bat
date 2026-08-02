@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PYTHONUTF8=1"
if exist "%PROJECT_DIR%.venv\Scripts\python.exe" (set "PYTHON=%PROJECT_DIR%.venv\Scripts\python.exe") else (set "PYTHON=python")
pushd "%PROJECT_DIR%"
"%PYTHON%" -m GarimpoInvestimentos.jobs phase1
if errorlevel 1 exit /b %errorlevel%
"%PYTHON%" -m GarimpoInvestimentos.jobs backtest
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
