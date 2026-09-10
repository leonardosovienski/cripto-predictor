@echo off
setlocal
set "CRIPTO_ROOT=%~dp0"
call "%~dp0pesquisa-20260909\cripto.cmd" %*
exit /b %errorlevel%
