# GarimpoInvestimentos

Pipeline de análise de criptoativos: coleta dados de mercado e notícias, gera uma
análise qualitativa com IA (Google Gemini), calcula um score de oportunidade e
exporta os resultados em CSV/XLSX. Mantém cache e histórico para o backtesting (Fase 2).

```
coleta (CoinGecko + SerpAPI) → indicadores técnicos → análise (Gemini) → score → CSV/XLSX + histórico
```

> **Localização canônica:** `C:\Claude\previsao-cripto\` (o pacote é
> `previsao-cripto\GarimpoInvestimentos\`). Estado consolidado da plataforma em
> `../ECOSYSTEM_STATUS.md` e `../FINAL_CERTIFICATION.md`.

## Estado atual

Integrado ao **predictor_core** via `vendor/` (significância por block bootstrap, carimbo
do juiz, cross-check flag-only, trava de credenciais P0). Suíte: **27 testes verdes**.
Pipeline roda ponta a ponta ao vivo; agendamento diário **ativo**.

**Validação em t≈0:** o forward test mal começou a acumular — sem veredito ainda. Achado de
instrumento: o score é **~40% RSI** (Spearman +0,68, n=10) e fraco com trend/momentum.
**Mitigação JÁ IMPLEMENTADA:** cada previsão agora **persiste o snapshot técnico**
(RSI/MACD/SMA50/SMA200/Bollinger) no histórico, e o backtest reporta o **Spearman
RESIDUALIZADO contra o RSI** — se o resíduo ainda prevê, o LLM agrega além do RSI; senão, o
"sinal" era RSI disfarçado. (medição pontual da atribuição: `score_attribution.py`.)
Classificação: **pesquisa** (operacional, validação no zero).

## Ambiente

Esta máquina tem **apenas Python 3.14.6**. Dois interpretadores em uso:
- **venv do pacote** `GarimpoInvestimentos\env\Scripts\python.exe` — roda o **pipeline ao vivo**
  (tem httpx/pydantic/loguru/openpyxl/SDKs do LLM, mas **não** pytest).
- **venv raiz** `C:\Claude\.venv\Scripts\python.exe` — roda os **testes** (stack completo).

`__init__.py` injeta `vendor/` no `sys.path`, então `python -m GarimpoInvestimentos.main`
resolve o `predictor_core` a partir de `previsao-cripto`.

## Como rodar (ao vivo)

Exige chaves reais no `.env`. ⚠️ Por design (fail-fast), `.env` sem chaves reais **crasha
no segundo zero** (trava P0). A partir de `C:\Claude\previsao-cripto`:

```powershell
$py = ".\GarimpoInvestimentos\env\Scripts\python.exe"
& $py -m GarimpoInvestimentos.main                       # usa DEFAULT_ASSETS do .env (22 ativos)
& $py -m GarimpoInvestimentos.main --assets bitcoin,solana --no-cache --min-score 70 --summary
& $py -m GarimpoInvestimentos.analyzers.backtest          # Fase 2 (correlação score×retorno)
& $py score_attribution.py                                # validação: quanto do score é RSI?
```

Testes (27 verdes): `& "C:\Claude\.venv\Scripts\python.exe" -m pytest tests/ -q`.

### Opções de CLI

| Flag | Efeito |
|------|--------|
| `--assets bitcoin,cardano` | Analisa essa lista em vez do `DEFAULT_ASSETS` |
| `--min-score 70` | Limiar (0-100) para o destaque 🏅; default = `LIMIAR_SCORE_MINIMO` |
| `--no-cache` | Ignora o cache e **não** regrava o `cache.json` (coleta sempre fresca) |
| `--output-dir <pasta>` | Grava CSV/XLSX/histórico/cache nessa pasta |
| `--summary` | Ao final, imprime só os ativos com score ≥ limiar |

## Estrutura

```
previsao-cripto/                     ← raiz do repositório (rode a partir daqui)
├── pyproject.toml
├── vendor/predictor_core/           ← biblioteca core vendorizada (net, stats, obs, settings...)
├── score_attribution.py            ← validação de instrumento (score vs técnicos)
├── tests/                           ← pytest (27 verdes)
├── scripts/run_daily.ps1           ← roda o pipeline 1×/dia (Agendador do Windows)
└── GarimpoInvestimentos/            ← pacote Python
    ├── __init__.py                  ← guard UTF-8 + injeta vendor/ no sys.path
    ├── main.py                      ← ponto de entrada
    ├── config.py                    ← lê chaves do .env + trava P0 (require_secrets)
    ├── .env                         ← suas chaves de API (NÃO versionar)
    ├── requirements.txt
    ├── collectors/
    │   ├── coingecko_api.py         ← dados de mercado + série de 200 closes
    │   └── serpapi_news.py          ← notícias via SerpAPI (Google News)
    ├── analyzers/
    │   ├── ai_insights.py           ← análise via LLM (Gemini ou OpenAI), prompt ancorado, judge_signature
    │   ├── indicators.py            ← RSI, SMA 50/200, MACD, Bollinger (Python puro)
    │   ├── score_engine.py          ← score = opportunity_score do LLM (puro) + divergence_flag
    │   └── backtest.py              ← Fase 2: D+1/7/30, Spearman+IC, estratificação, residualização⊥RSI
    ├── core/
    │   ├── paths.py                 ← caminhos fixos de output/ e logs/ (à prova de cwd)
    │   ├── cache.py                 ← cache JSON com TTL UTC (auto-poda no load)
    │   ├── history.py               ← histórico CSV (dedup Ativo+Data) + snapshot técnico p/ residualizar
    │   └── logger.py                ← logging via loguru (logs/garimpo.log)
    └── output/
        └── reporter.py              ← exportação CSV + XLSX com gráfico
```

> **Rede:** não há mais `core/retry.py` nem `core/http_client.py` — a rede (retry/backoff +
> cliente httpx) migrou para `predictor_core.net` (`with_retry`, `get_http_client`).
> **Pacote `output/` vs dados:** `GarimpoInvestimentos/output/` é **código** (`reporter.py`);
> os arquivos gerados vão para `output/`+`logs/` na **raiz** (ancorados via `core/paths.py`).

## Configurar as chaves de API

Edite `GarimpoInvestimentos/.env`. `SERP_API_KEY` + a chave do provedor de LLM são
obrigatórias (lidas no import; se faltarem ou forem placeholder/<16 chars → `ValueError`
imediato). As demais têm default:

```
LLM_PROVIDER=gemini                 # "gemini" (default) ou "openai"
GEMINI_API_KEY=sua_chave_gemini
GEMINI_MODEL=gemini-2.5-flash       # ⚠️ alias FLUTUANTE — pine um snapshot datado p/ reprodutibilidade
OPENAI_API_KEY=                     # só se LLM_PROVIDER=openai (API paga, NÃO é ChatGPT Plus)
OPENAI_MODEL=gpt-4o-mini
SERP_API_KEY=sua_chave_serpapi
LIMIAR_SCORE_MINIMO=60
DEFAULT_ASSETS=bitcoin,ethereum,solana,binancecoin,ripple,cardano,dogecoin,tron,avalanche-2,chainlink,polkadot,litecoin,bitcoin-cash,stellar,uniswap,cosmos,monero,aave,near,algorand,vechain,filecoin
CACHE_TTL_HOURS=6
ENABLE_CACHE=true
SCORE_HORIZON_DAYS=7
```

- Gemini: https://aistudio.google.com/app/apikey · SerpAPI: https://serpapi.com/manage-api-key
- OpenAI (API paga, ≠ ChatGPT Plus): https://platform.openai.com/api-keys · CoinGecko free **não exige chave**.

> ⚠️ **Não troque de provedor no meio de uma janela de coleta** — mistura dois "juízes" de
> calibrações diferentes e invalida o backtest. E **pine o `GEMINI_MODEL`** num snapshot
> datado: o alias flutuante pode mudar de pesos sem mudar a `judge_signature`.

## Agendamento diário (ATIVO)

O backtest só amadurece com **tempo real decorrido**, então o pipeline roda 1×/dia via
Agendador do Windows. **Já registrado** (status Ready):

```
Task: GarimpoInvestimentos  →  scripts\run_daily.ps1  →  diário 08:00
Remover:  schtasks /Delete /TN "GarimpoInvestimentos" /F
```

`run_daily.ps1` roda o pipeline (22 ativos do `DEFAULT_ASSETS`) e loga em
`logs/cron_<data>.log`.

> **Cota/escala:** o CoinGecko free **rate-limita rajadas** (429) — 22 ativos seguidos podem
> perder os últimos (missingness sistemática); o `run_daily` espaça as chamadas. O Gemini free
> também tem cota diária — ao estourar, o ativo cai em fallback (score 50/neutro, evento
> `llm_error` no `events.jsonl`).

## Resiliência

| Etapa | Em caso de falha |
|-------|------------------|
| CoinGecko (mercado) | o ativo é **pulado** (sem dados reais não há análise) |
| SerpAPI (notícias) | segue com `news=[]`; emite `input_degraded` |
| Gemini (análise) | fallback (`sentimento=neutro`, score 50) + emite `llm_error` |

Retry com backoff (`predictor_core.net.with_retry`): `503`/`429` transitório re-tenta;
404/chave inválida/cota diária não (retry não resolve).

## Como o score funciona

- O LLM recebe preço + variações **+ indicadores técnicos** (RSI, SMA 50/200, MACD, Bollinger,
  de `indicators.py`) injetados no prompt — ele *interpreta* os números, não os calcula.
- Devolve `opportunity_score` (0-100) **ancorado a `SCORE_HORIZON_DAYS`** (0=queda forte,
  50=incerteza, 100=alta forte nesse prazo).
- O **`Score` final é esse número puro**; o `sentiment` é só metadado (não multiplica o score).
- `divergence_flag` tagueia contradição LLM×técnico (só sinaliza, não muta o score).
- ⚠️ **~40% do score é explicado pelo RSI** (medido, n=10). Por isso o snapshot técnico é
  **persistido em cada previsão** e o backtest **residualiza o score contra o RSI** — só o
  resíduo pode ser atribuído ao LLM. (medição pontual: `score_attribution.py`.)

## Saídas (na pasta `output/` da raiz)

- `garimpo_resultados_<timestamp>.csv` / `.xlsx` — relatório da execução (XLSX com gráfico).
- `garimpo_historico.csv` — histórico acumulado; colunas: `Ativo, Sentimento, Score, Resumo,
  Data, price_usd, Juiz, Divergencia, RSI14, MACD_hist, vs_SMA50_pct, vs_SMA200_pct,
  Bollinger_pctB` (dedup por Ativo+Data; o snapshot técnico permite residualizar o score).
- `garimpo_backtest.csv` — variações D+1/D+7/D+30 (Fase 2). · `cache.json` — TTL 6h.
- Logs em `logs/garimpo.log` (rotação 5 MB). · Telemetria em `events.jsonl` (gitignored).

## Fase 2 — backtesting

`analyzers/backtest.py` lê o histórico (descartando fallback, dedup), busca o preço real em
D+1/D+7/D+30 via CoinGecko, e para o horizonte `SCORE_HORIZON_DAYS` calcula Spearman(Score,
variação) **com IC block bootstrap** (core.stats), estratificado por `divergence_flag`, mais
acurácia direcional/hit rate/benchmark BTC. **Reporta também o Spearman RESIDUALIZADO contra
o RSI** (OLS score~RSI; correlação do resíduo com o retorno) — separa o sinal do LLM do RSI
redescoberto. ⚠️ Só dá número significativo após **semanas** de previsões acumuladas (uma
previsão de hoje só tem preço em D+7 daqui a 7 dias) **e** com o RSI salvo (a partir de agora).
