# GarimpoInvestimentos

Pipeline de análise de criptoativos: coleta dados de mercado e notícias, gera uma
análise qualitativa com IA (Google Gemini), calcula um score de oportunidade e
exporta os resultados em CSV/XLSX. Mantém cache e histórico para permitir
backtesting na Fase 2.

```
coleta (CoinGecko + SerpAPI) → análise (Gemini) → score → exportação (CSV/XLSX) + histórico
```

## Estado atual / Como rodar

Integrado à plataforma **predictor_core** (significância via block bootstrap pareado,
carimbo do juiz, cross-check flag-only, trava de credenciais). Detalhes no
[HANDOFF.md](HANDOFF.md) §0. Suíte: `python -m pytest tests/ -q` (26 verdes — rodam no
Python do sistema).

**Rodar AO VIVO** exige chaves reais no `.env` **e** a venv (httpx/pydantic/SDKs do LLM):
```powershell
# cole GEMINI_API_KEY / OPENAI_API_KEY / SERP_API_KEY (>=16 chars) em GarimpoInvestimentos\.env
.\GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.main --assets bitcoin,ethereum
.\GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.analyzers.backtest
```
⚠️ Por design (fail-fast): `.env` sem chaves reais **crasha no segundo zero** (trava P0).

## Estrutura

```
ProjetosPython/                      ← raiz do repositório (rode a partir daqui)
├── pyproject.toml
└── GarimpoInvestimentos/            ← pacote Python
    ├── __init__.py
    ├── main.py                      ← ponto de entrada
    ├── config.py                    ← lê chaves do .env + validação de startup
    ├── .env                         ← suas chaves de API (NÃO versionar)
    ├── requirements.txt
    ├── collectors/
    │   ├── coingecko_api.py         ← dados de mercado (preço, volume, variações)
    │   └── serpapi_news.py          ← notícias via SerpAPI (Google News)
    ├── analyzers/
    │   ├── ai_insights.py           ← análise via LLM (Gemini ou OpenAI), prompt ancorado
    │   ├── indicators.py            ← RSI, SMA 50/200, MACD, Bollinger (Python puro)
    │   ├── score_engine.py          ← score final = opportunity_score do LLM (puro, 0-100)
    │   └── backtest.py              ← Fase 2: D+1/7/30, Spearman, hit rate, Sharpe, benchmark
    ├── core/
    │   ├── paths.py                 ← caminhos fixos de output/ e logs/ (à prova de cwd)
    │   ├── retry.py                 ← retry com backoff p/ chamadas transitórias (503/429)
    │   ├── cache.py                 ← cache JSON com TTL (UTC, configurável)
    │   ├── history.py               ← histórico CSV acumulado, dedup por (ativo, data)
    │   ├── http_client.py           ← cliente httpx async
    │   └── logger.py                ← logging via loguru (logs/garimpo.log)
    └── output/
        └── reporter.py              ← exportação CSV + XLSX com gráfico

scripts/run_daily.ps1               ← roda o pipeline 1×/dia (Agendador do Windows)
```

> **Pacote `output/` vs pasta de dados:** `GarimpoInvestimentos/output/` contém só
> **código** (`reporter.py`). Os arquivos gerados vão para `output/` e `logs/` na
> **raiz do projeto**, sempre — o `core/paths.py` ancora esses caminhos via `__file__`,
> então não importa de qual diretório você execute.

## Setup

Pré-requisito: **Python 3.12** (via `python`).

> A venv já vem criada em `GarimpoInvestimentos\env`. **Só refaça os passos abaixo se
> ela não existir** (ex.: clone novo). Rode **sempre a partir da raiz**
> `C:\Claude\ProjetosPython` — note que a venv e o `requirements.txt` ficam dentro de
> `GarimpoInvestimentos\`, então os caminhos abaixo são relativos à raiz:

```powershell
cd C:\Claude\ProjetosPython
python -m venv GarimpoInvestimentos\env
GarimpoInvestimentos\env\Scripts\python.exe -m pip install --upgrade pip
GarimpoInvestimentos\env\Scripts\python.exe -m pip install -r GarimpoInvestimentos\requirements.txt
```

### Configurar as chaves de API

Edite `GarimpoInvestimentos/.env` com chaves **reais**. `GEMINI_API_KEY` e
`SERP_API_KEY` são obrigatórias e lidas em tempo de import — se faltarem, o programa
levanta `ValueError` imediatamente, antes de qualquer requisição. As demais têm
default:

```
# Provedor de LLM: "gemini" (default) ou "openai"
LLM_PROVIDER=gemini
GEMINI_API_KEY=sua_chave_gemini
GEMINI_MODEL=gemini-2.5-flash
# Só necessárias se LLM_PROVIDER=openai (chave de API paga, NÃO é o ChatGPT Plus):
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

SERP_API_KEY=sua_chave_serpapi
LIMIAR_SCORE_MINIMO=60          # score (escala 0-100) p/ destacar oportunidades
DEFAULT_ASSETS=bitcoin,ethereum,solana
CACHE_TTL_HOURS=6
ENABLE_CACHE=true
SCORE_HORIZON_DAYS=7            # horizonte do score; o backtest correlaciona contra ele
```

Obrigatórias: `SERP_API_KEY` + a chave do provedor escolhido (`GEMINI_API_KEY` **ou**
`OPENAI_API_KEY`). As outras têm default.

- **Gemini**: https://aistudio.google.com/app/apikey
- **OpenAI (API paga)**: https://platform.openai.com/api-keys — ⚠️ a assinatura **ChatGPT
  Plus não dá acesso à API**; é cobrança por token, conta separada.
- **SerpAPI**: https://serpapi.com/manage-api-key
- CoinGecko (free tier) **não exige chave**.

> ⚠️ **Não troque de provedor no meio da coleta do backtest.** Um histórico
> meio-Gemini, meio-OpenAI mistura dois "juízes" com calibrações diferentes e
> invalida o estudo. Escolha um e mantenha pela janela inteira.

## Como rodar

Sempre a partir da **raiz** (`C:\Claude\ProjetosPython`), como módulo:

```powershell
cd C:\Claude\ProjetosPython
```

```powershell
GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.main
```

Sem flags, usa `DEFAULT_ASSETS` do `.env` (`bitcoin,ethereum,solana`).

### Opções de CLI

| Flag | Efeito |
|------|--------|
| `--assets bitcoin,cardano` | Analisa essa lista em vez do `DEFAULT_ASSETS` |
| `--min-score 70` | Limiar (0-100) para o destaque 🏅; default = `LIMIAR_SCORE_MINIMO` |
| `--no-cache` | Ignora o cache e **não** regrava o `cache.json` (coleta sempre fresca) |
| `--output-dir <pasta>` | Grava CSV/XLSX/histórico/cache nessa pasta |
| `--summary` | Ao final, imprime só os ativos com score ≥ limiar |

```powershell
# exemplo: dois ativos, sem cache, destacando score >= 70, com resumo final
GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.main `
    --assets bitcoin,solana --no-cache --min-score 70 --summary
```

### Backtesting (Fase 2)

Depois de acumular previsões no histórico, avalie o poder preditivo do score:

```powershell
GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.analyzers.backtest
```

Gera `output/garimpo_backtest.csv` (preço e variação em D+1/D+7/D+30) e imprime a
correlação de Spearman entre `Score` e a variação. ⚠️ Só produz números
significativos depois que tempo suficiente passou desde as previsões (ver Fase 2).

## Como testar o projeto inteiro

Roteiro de smoke-test. Tudo a partir da raiz; defina um atalho para o Python da venv:

```powershell
cd C:\Claude\ProjetosPython
$py = ".\GarimpoInvestimentos\env\Scripts\python.exe"
```

| # | O que valida | Comando | Esperado |
|---|--------------|---------|----------|
| 1 | Deps da venv | `& $py -c "import httpx, loguru, openpyxl, pydantic, dotenv; from google import genai; print('deps OK')"` | `deps OK` |
| 2 | Sintaxe de todos os fontes | `& $py -m compileall -q -x env GarimpoInvestimentos` | sem erros |
| 3 | Pipeline completo | `& $py -m GarimpoInvestimentos.main` | 3 ativos, "exportados", histórico atualizado |
| 4 | Cache (rode o #3 de novo) | `& $py -m GarimpoInvestimentos.main` | "🧠 Cache válido — pulando coleta" |
| 5 | Ajuda da CLI | `& $py -m GarimpoInvestimentos.main --help` | lista as flags |
| 6 | CLI completa | `& $py -m GarimpoInvestimentos.main --assets bitcoin,solana --no-cache --min-score 70 --summary` | bloco "RESUMO" só com score ≥ 70 |
| 7 | `--output-dir` | `& $py -m GarimpoInvestimentos.main --assets bitcoin --no-cache --output-dir output\teste` | arquivos em `output\teste\` |
| 8 | Backtest (Fase 2) | `& $py -m GarimpoInvestimentos.analyzers.backtest` | gera `garimpo_backtest.csv`; hoje reporta "dados insuficientes" |

### Validar a proteção de startup do `.env` (deve falhar de propósito)

```powershell
$env:GEMINI_API_KEY=""; $env:SERP_API_KEY=""
& $py -c "from GarimpoInvestimentos.config import settings"   # espere: ValueError ... ausentes
Remove-Item Env:\GEMINI_API_KEY, Env:\SERP_API_KEY            # desfaz a sobrescrita
```

### Conferir as saídas (após rodar o pipeline ao menos uma vez)

```powershell
Get-Content output\garimpo_historico.csv
& $py -c "from openpyxl import load_workbook; import glob, os; f=max(glob.glob('output/garimpo_resultados_*.xlsx'), key=os.path.getmtime); ws=load_workbook(f).active; [print(r) for r in ws.iter_rows(max_row=2, values_only=True)]"
```

O XLSX deve trazer as 6 colunas preenchidas: `Ativo, Sentimento, Score, Resumo, Data, Preço USD`.

### (Opcional) Independência de diretório

```powershell
cd C:\Claude
$env:PYTHONPATH = "C:\Claude\ProjetosPython"
& C:\Claude\ProjetosPython\GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.main
# a saída cai em C:\Claude\ProjetosPython\output — NUNCA em C:\Claude
Remove-Item Env:\PYTHONPATH; cd C:\Claude\ProjetosPython
```

Ao terminar, limpe os artefatos de teste: `Remove-Item output\teste -Recurse -ErrorAction SilentlyContinue`

## Comportamento e resiliência

O pipeline degrada com elegância — uma falha pontual não derruba a execução:

| Etapa | Em caso de falha |
|-------|------------------|
| CoinGecko (dados de mercado) | o ativo é **pulado** (sem dados reais não há análise) |
| SerpAPI (notícias) | segue com `news=[]`; o Gemini ainda analisa pelos dados de mercado |
| Gemini (análise) | `ai_insights` aplica fallback (`sentimento=neutro`, score base 50) |

> Com chaves placeholder no `.env`, SerpAPI retorna 401 e Gemini retorna 400 — isso
> é **esperado**, e o resultado sai com a análise de fallback. Para análise real,
> preencha chaves válidas.

> ⚠️ **Cota do Gemini (free tier): ~20 requisições/dia** no `gemini-2.5-flash`. Como
> cada ativo = 1 chamada, são ~6 execuções de 3 ativos por dia. Ao estourar, vem
> `429 RESOURCE_EXHAUSTED` e o ativo cai em fallback (score 50/neutro) — espere o
> reset diário ou use uma chave paga. `503` é sobrecarga **transitória** (re-rodar resolve).

Rate limiting: `asyncio.sleep(1)` entre ativos (ausente após o último), adequado ao
free tier da CoinGecko. **Retry com backoff exponencial** (`core/retry.py`) cobre as
chamadas de CoinGecko/SerpAPI/LLM: um `503`/`429` *transitório* espera e re-tenta em vez
de virar fallback. Erros não-transitórios (404, chave inválida, **cota diária** esgotada)
não são reententados — retry não os resolve.

## Agendamento diário (acumular o histórico)

O backtest só amadurece com **tempo real decorrido** — então o quanto antes o pipeline
rodar todo dia, antes começa a coletar previsões. Use o Agendador de Tarefas do Windows
(barato, local; nuvem é over-engineering enquanto não há sinal validado).

Já existe o script [`scripts/run_daily.ps1`](scripts/run_daily.ps1) (roda o pipeline e
loga em `logs/cron_<data>.log`). Registre-o para rodar 1×/dia (ex.: 09:00):

```powershell
schtasks /Create /TN "GarimpoDaily" `
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Claude\ProjetosPython\scripts\run_daily.ps1" `
  /SC DAILY /ST 09:00
```

Para remover: `schtasks /Delete /TN "GarimpoDaily" /F`.

> **Escala vs. cota:** a `DEFAULT_ASSETS` traz ~22 ativos (corte transversal dilui a
> variância). No **free tier do Gemini (~20 req/dia)** isso estoura — rode com **Gemini
> API pago** para a lista cheia, ou reduza para ~18 ativos. E **pine o `GEMINI_MODEL`**
> num snapshot datado para a calibração não derivar durante a coleta.

## Saídas geradas (na pasta `output/` da raiz)

- `garimpo_resultados_<timestamp>.csv` e `.xlsx` — relatório da execução (XLSX com
  gráfico de barras e formatação condicional por score)
- `garimpo_historico.csv` — histórico **acumulado** de todas as execuções, com
  `Data` e `price_usd` (âncora para o backtesting)
- `garimpo_backtest.csv` — gerado pelo módulo de backtest (variações D+1/D+7/D+30)
- `cache.json` — cache com TTL configurável (`CACHE_TTL_HOURS`, default 6h)

Logs em `logs/garimpo.log` (rotação a cada 5 MB).

## Como o score funciona

- O LLM recebe preço + variações **+ indicadores técnicos** (RSI, SMA 50/200, MACD,
  Bollinger), calculados em Python (`indicators.py`) e injetados no prompt — ele
  *interpreta* os números, não os calcula.
- Devolve `opportunity_score` (0-100) **ancorado ao horizonte** `SCORE_HORIZON_DAYS`
  (0 = forte queda esperada, 50 = incerteza, 100 = forte alta esperada nesse prazo).
- O **`Score` final é esse número puro** — o `sentiment` é apenas metadado de exibição/filtro,
  **não** multiplica o score (isso era dupla contagem e distorcia o sinal).
- Chamada ao LLM usa temperatura baixa + JSON mode → score mais reprodutível, o que importa
  para o backtest.

## Fase 2 — backtesting (esqueleto pronto)

`analyzers/backtest.py` já implementa: leitura do histórico (descartando fallback e
deduplicando por ativo+data), busca do preço real em D+1/D+7/D+30 via CoinGecko, cálculo
das variações e, para o horizonte `SCORE_HORIZON_DAYS`:

- **Spearman** (sem `scipy`) entre `Score` e a variação;
- **Acurácia direcional** (score>50 acertou a direção?);
- **Hit rate** dos sinais fortes (score ≥ limiar que fecharam positivos);
- **Estratégia fictícia** (retorno médio comprando score ≥ limiar) + **Sharpe simplificado**;
- **Benchmark** Bitcoin buy & hold no mesmo período.

⚠️ **O valor só amadurece com o tempo:** a análise do Gemini é point-in-time, então
uma previsão de hoje só terá preço em D+7 daqui a 7 dias. O backtest só dá correlação
significativa após acumular previsões reais ao longo de semanas. Se o Spearman ficar
perto de zero ou negativo, revisar o prompt do Gemini antes de investir em mais
infraestrutura.
