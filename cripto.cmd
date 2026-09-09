@echo off
setlocal
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONNOUSERSITE=1"
pushd "%~dp0"
"%~dp0.venv\Scripts\python.exe" -B -m GarimpoInvestimentos.local_runtime %*
set "CRIPTO_EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %CRIPTO_EXIT_CODE%
