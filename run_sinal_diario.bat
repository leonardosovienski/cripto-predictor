@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PYTHONUTF8=1"
rem Top cripto por market cap (fixos, sempre cobertos):
set "ATIVOS=bitcoin,ethereum,solana,binancecoin,ripple,cardano,dogecoin,polkadot,avalanche-2,chainlink"
rem Quantos candidatos extras (momentum/trending) buscar via --discover, alem dos fixos acima:
set "DISCOVER_N=15"

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

echo === Ingestao (rede): top cripto fixos -^> Feature Store ===
uv run python -m GarimpoInvestimentos.main --ingest --assets %ATIVOS% --mode fallback
if errorlevel 1 (
    echo Ingestao dos ativos fixos falhou. Verifique GarimpoInvestimentos\.env (GEMINI_API_KEY / SERP_API_KEY) e conexao de rede.
    popd
    exit /b %errorlevel%
)

echo === Ingestao (rede): descoberta de candidatos (momentum + trending) -^> Feature Store ===
uv run python -m GarimpoInvestimentos.main --ingest --discover %DISCOVER_N% --mode fallback
if errorlevel 1 (
    echo Descoberta falhou ou nao retornou candidatos. Seguindo so com os ativos fixos.
)

echo === Analise (offline, le TODO o universo da Feature Store) ===
uv run python -m GarimpoInvestimentos.main --summary
set "RESULT=%errorlevel%"

popd
exit /b %RESULT%
