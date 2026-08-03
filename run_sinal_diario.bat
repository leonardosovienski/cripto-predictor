@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PYTHONUTF8=1"
set "ATIVOS=bitcoin,ethereum,solana"

pushd "%PROJECT_DIR%"

where uv >nul 2>nul
if errorlevel 1 (
    echo uv nao encontrado no PATH. Instale com: pip install uv
    popd
    exit /b 1
)

echo === Sync do ambiente (uv) ===
uv sync --extra llm --extra excel
if errorlevel 1 (
    echo uv sync falhou.
    popd
    exit /b %errorlevel%
)

echo === Ingestao (rede): OHLCV + Fear^&Greed -^> Feature Store ===
uv run python -m GarimpoInvestimentos.main --ingest --assets %ATIVOS% --mode fallback
if errorlevel 1 (
    echo Ingestao falhou. Verifique GarimpoInvestimentos\.env (GEMINI_API_KEY / SERP_API_KEY) e conexao de rede.
    popd
    exit /b %errorlevel%
)

echo === Analise (offline, le da Feature Store) ===
uv run python -m GarimpoInvestimentos.main --assets %ATIVOS% --summary
set "RESULT=%errorlevel%"

popd
exit /b %RESULT%
