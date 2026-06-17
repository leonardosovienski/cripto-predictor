# HANDOFF — GarimpoInvestimentos (Fase 1 + melhorias)

Data: 2026-06-14
Estado: **Fase 1 + CLI + notícias + backtesting + sinal calibrado + indicadores técnicos + LLM multi-provedor + métricas + retry/backoff + agendamento diário (pronto pra acumular dados).**

---

## 1. Resumo do que foi feito

Refatoração da Fase 1 (deixar o código limpo, funcional e pronto para o backtesting
da Fase 2). As 6 tarefas do roadmap foram aplicadas:

| # | Arquivo | Mudança |
|---|---------|---------|
| 1 | `config.py` | Chaves agora vêm do `.env` via `field(default_factory=os.getenv)`; `__post_init__` levanta `ValueError` no import se faltar `GEMINI_API_KEY`/`SERP_API_KEY`. Removidas as chaves hardcoded. |
| 2 | `collectors/coingecko_api.py` | `CoinData` ganhou `change_7d`, `change_30d`, `volume_avg_7d` (com `or 0.0` contra `None`); import absoluto. |
| 3 | `main.py` | Usa `get_coin_data` real (`model_dump()`) em vez de dados fixos; `asyncio.sleep(1)` entre ativos (ausente após o último); imports absolutos; `price_usd` no resultado. |
| 4 | `core/cache.py` | TTL de 6h com timestamps UTC timezone-aware; entradas sem/`cached_at` inválido descartadas. |
| 5 | `core/history.py` | Coluna `price_usd` adicionada ao histórico (âncora da Fase 2). |
| 6 | estrutura | Deletadas as duplicatas da raiz (`main.py` com `sys.path.insert`, e `core/logger.py`); criados `GarimpoInvestimentos/__init__.py` e `pyproject.toml`. |

---

## 2. O que foi consertado / além do prompt nesta sessão

- **Bug real de runtime — `UnicodeEncodeError`:** o console do Windows (cp1252) quebrava
  ao imprimir os emojis dos `print()`. Corrigido forçando UTF-8 em `sys.stdout`/`sys.stderr`
  no **`GarimpoInvestimentos/__init__.py`** — cobre qualquer entry-point (`main`, `backtest`, …).
- **venv recriada:** a antiga (`GarimpoInvestimentos/env`) apontava para um Python 3.14
  que não existe mais na máquina. Recriada com **Python 3.12** + `requirements.txt`.
- **Imports em 2 arquivos da lista "não tocar"** (`serpapi_news.py`, `ai_insights.py`):
  tinham `from config import...`/`from core.http_client import...` implícitos, que
  quebram sob `python -m`. Corrigidas **apenas as linhas de import** (lógica intacta) —
  era impossível satisfazer o "rodar como módulo" sem isso.
- **`pyproject.toml`:** o backend pedido no prompt (`setuptools.backends.legacy:build`)
  não existe e quebraria `pip install`. Usado o correto `setuptools.build_meta`.
- **Caminhos de saída ancorados (`core/paths.py`, novo):** antes `output/` e `logs/`
  eram relativos ao cwd, gerando pastas duplicadas conforme de onde se rodava. Agora
  `cache.py`/`history.py`/`reporter.py`/`logger.py` resolvem tudo via `core/paths.py`
  (baseado em `__file__`) → sempre na raiz do projeto, independente do cwd. Validado
  rodando de `C:\Claude` sem criar `output/` lá. Atenção: a pasta `GarimpoInvestimentos/output/`
  **é o pacote** que contém `reporter.py` — não apague; os dados agora vão para a raiz.
- **`.gitignore` + chaves no `.env`:** chaves reais (funcionais) movidas para o `.env`
  e `.gitignore` criado protegendo `.env`/venv/saídas.

---

## 2b. Melhorias e features (rodada 2)

Feito pelo Leo e validado/estendido nesta sessão:

| Área | Mudança |
|------|---------|
| `config.py` | Novas configs lidas do `.env`: `DEFAULT_ASSETS`, `CACHE_TTL_HOURS`, `ENABLE_CACHE`. Limiar default corrigido de `0.6` → **`60`** (estava em escala errada; scores são 0-100). |
| `main.py` (CLI) | `--assets`, `--min-score`, `--no-cache`, **`--output-dir`** (novo), **`--summary`** (novo). `--no-cache` agora também **não regrava** o `cache.json`. Pré-parse de `--output-dir` antes dos imports (seta `GARIMPO_OUTPUT_DIR`). |
| `core/cache.py` | TTL agora vem de `settings.CACHE_TTL_HOURS`. |
| `output/reporter.py` | Colunas `Data` e `Preço USD` em CSV **e XLSX** (o corpo do XLSX estava faltando os 2 campos — bug corrigido). |
| `core/paths.py` | `OUTPUT_DIR`/`LOGS_DIR` respeitam `GARIMPO_OUTPUT_DIR`/`GARIMPO_LOGS_DIR` (suporte ao `--output-dir`). |
| `collectors/serpapi_news.py` | **Query corrigida**: removido o filtro `site:news.google.com` que zerava resultados; agora as notícias realmente chegam ao Gemini. Guarda contra payload `{"error": ...}`. |
| `analyzers/backtest.py` (novo) | Esqueleto da Fase 2: lê histórico (ignora fallback), busca preço em D+1/D+7/D+30 (CoinGecko `/history`), calcula variações e **Spearman sem `scipy`**. |

---

## 2c. Calibração do sinal (rodada 3) — corrige a "matemática" do score

Após revisão crítica, atacamos os defeitos que invalidavam o backtesting:

| Arquivo | Correção |
|---------|----------|
| `score_engine.py` | **Removida a multiplicação por sentimento** (era dupla contagem; esmagava o número do modelo, ex.: 35→7). `Score` = `opportunity_score` puro (clamp 0-100). Sentimento vira só metadado. |
| `ai_insights.py` | Prompt **ancorado a um horizonte** (`SCORE_HORIZON_DAYS`); escala 0-100 definida como retorno esperado nesse prazo. **JSON mode + `temperature=0.2`** → score reprodutível. |
| `collectors/coingecko_api.py` | **Removido o `volume_avg_7d` falso** (era o volume de hoje rotulado como média de 7d — enganava o LLM). |
| `core/cache.py` | `save_cache` usa `setdefault` no `cached_at` → **preserva o timestamp da análise original** (antes o TTL era renovado a cada run e nunca expirava). |
| `core/history.py` | **Dedup por (Ativo, Data)** → cache hits/reexecuções não inflam o `n` do Spearman. |
| `analyzers/backtest.py` | Horizonte principal vem do config; dedup defensivo no load. |
| `config.py` | Novo `SCORE_HORIZON_DAYS` (default 7). `.env` carregado por **caminho explícito** (robusto a cwd e a `-m`/`-c`/testes). |

Validado: `score_engine` (negativo+35 → **35**, era 7); `volume_avg_7d` ausente do
`model_dump`; dedup (3 appends idênticos → **1 linha**); `cached_at` preservado p/ entrada
existente e carimbado p/ nova; análise real do Gemini com o novo prompt (BTC 30-35, ETH 75).

> **Cota do Gemini free tier (~20 req/dia)** foi estourada nos testes de hoje → alguns
> ativos caíram em fallback por `429`. Não é bug. Para um dataset limpo, rode com calma
> após o reset diário (ou chave paga).

---

## 2d. Maturidade de dados e análise (rodada 4)

Foco em deixar dados/análise úteis (não em features de infra):

| Área | Mudança |
|------|---------|
| **Feature engineering** | Novo `analyzers/indicators.py` (RSI 14, SMA 50/200, MACD, Bollinger %B — Python puro). `coingecko_api.get_price_series()` busca 200 closes diários; `main.py` calcula e injeta em `hard_data["indicadores"]`. O LLM agora interpreta indicadores reais, não só preço. |
| **Provedor de LLM** | `ai_insights.py` agora é agnóstico (`analyze_asset`): Gemini **ou** OpenAI via `LLM_PROVIDER`. Clientes lazy; validação de chave por provedor. `GEMINI_MODEL`/`OPENAI_MODEL`/`OPENAI_API_KEY` no config. **OpenAI = API paga, não ChatGPT Plus.** |
| **Métricas de backtest** | `backtest.py` ganhou acurácia direcional, hit rate (score≥limiar), estratégia fictícia + Sharpe simplificado, e benchmark BTC buy&hold — no horizonte principal. |
| `requirements.txt` | `+ openai`. |

Validado (sem gastar cota de LLM): indicadores em série real do BTC (RSI 35.9, −17% vs SMA200,
MACD virando, %B 0.37); validação de provedor (openai sem chave → erro certo; com chave →
carrega sem exigir Gemini); métricas em dado sintético (direcional/hit rate/Sharpe/benchmark
corretos); pipeline ponta a ponta sem quebrar (LLM caiu em fallback por 503/cota).

> ⚠️ **Não misture provedores na mesma janela de coleta** — contamina o backtest (dois
> juízes, calibrações diferentes). E **mais chamadas/dia não amadurecem o backtest mais
> rápido**: D+7 leva 7 dias reais (a não ser que se faça replay histórico point-in-time,
> que é projeto à parte com risco de lookahead).

---

## 2e. Coleta honesta: agendamento, escala e resiliência (rodada 5)

Foco: **ligar o relógio** (tempo é incompressível) e não envenenar o histórico com fallback.

| Área | Mudança |
|------|---------|
| **Retry/backoff** | Novo `core/retry.py` (`@with_retry`, backoff exponencial + jitter) aplicado a CoinGecko, SerpAPI e LLM. `503`/`429` transitório re-tenta; 404/chave inválida/**cota diária** não (retry não resolve). Validado por testes unitários. |
| **Escala transversal** | `DEFAULT_ASSETS` expandido para 22 ativos (dilui variância da amostra). Ids inválidos se auto-podam (404 → ativo pulado). |
| **Pin do modelo** | `GEMINI_MODEL` no `.env` com aviso para fixar um snapshot datado (alias flutuante deriva a calibração no meio da coleta). |
| **Agendamento** | `scripts/run_daily.ps1` + comando `schtasks` no README para rodar 1×/dia (Agendador do Windows — nuvem é over-engineering antes de sinal validado). |

> **Decisão metodológica registrada:** replay histórico do LLM é inválido (a memória
> paramétrica do modelo já "conhece" o futuro = look-ahead embutido). Forward test é o
> único caminho limpo para o LLM; replay só vale para o **baseline técnico** (indicadores
> não têm memória). **Teto free Gemini ~20 req/dia** → lista cheia exige Gemini pago.

---

## 3. Validação (execução real, não só syntax)

Tudo rodado de verdade com as **chaves reais** no `.env`:

- ✅ Pipeline ponta a ponta sem erro; CoinGecko traz dados reais e campos temporais.
- ✅ Análise **real do Gemini** (não fallback) — com a query de notícias corrigida, os
  scores ficaram variados (ex.: BTC 5, ETH 80, SOL 85) e os resumos citam notícias.
- ✅ `garimpo_historico.csv` com `Data` + `price_usd`; XLSX com as 6 colunas preenchidas.
- ✅ `cache.json` com `cached_at` UTC; 2ª execução → **cache hit**; `--no-cache` não grava.
- ✅ CLI validada: `--assets`, `--min-score`, `--summary` (lista só ≥ limiar), `--output-dir`
  (grava em pasta alternativa), `--help`.
- ✅ `backtest.py` executa e gera `garimpo_backtest.csv`; reporta "dados insuficientes"
  porque as previsões são de hoje (D+1 ainda não chegou) — comportamento esperado.
- ✅ `ValueError` de startup testado nos dois sentidos.
- ✅ Validado também rodando de outro cwd (`C:\Claude`): saída sempre na raiz do projeto.

---

## 4. Pendências / próximos passos

1. ✅ **Chaves reais já no `.env`** (Gemini + SerpAPI), testadas e funcionais.
2. **🔴 SEGURANÇA — rotacionar chaves antigas:** o `config.py` anterior tinha
   `GEMINI_API_KEY` (`AIzaSy...`) e `SERP_API_KEY` (`d6f8e4f3...`) **reais e hardcoded**.
   São as mesmas chaves em uso hoje. O backup `core.zip` (que as continha) foi apagado
   nesta sessão, mas elas ainda podem existir em cópias antigas do projeto
   (`source\repos\GarimpoInvestimentos`, `Downloads\GarimpoInvestimentos_vstudio`).
   **Rotacionar é recomendável** (não urgente; o `.gitignore` agora protege o `.env`).
3. **Fase 2 — acumular dados e validar:** o esqueleto (`analyzers/backtest.py`) está pronto,
   mas precisa de **tempo**: rodar o pipeline periodicamente por semanas para acumular
   previsões maduras, então rodar o backtest e olhar o Spearman. Se ~0 ou negativo, revisar
   o prompt do Gemini antes de migrar para nuvem/Postgres. (Automatizar via tarefa agendada
   é um bom próximo passo.)
4. ✅ **Retry/backoff** implementado (`core/retry.py`). Restam: registrar o `schtasks`
   diário (ação do usuário — muda o sistema), ativar Gemini pago e fixar o `GEMINI_MODEL`
   num snapshot datado antes de começar a coleta "pra valer".
5. **Baseline técnico no replay** (rápido e honesto): backtestar regras puras (ex.: RSI<30)
   no histórico para estabelecer o Sharpe mínimo que o LLM precisa bater. Indicadores não
   têm memória → replay é válido aqui (ao contrário do LLM).
6. **Features adiadas** (só depois que o backtest provar o sinal): paralelismo entre ativos
   com `Semaphore`, NLP/sentimento de notícias, relatório HTML, e migração nuvem/Postgres.
7. **Testes automatizados:** só há testes manuais/ad-hoc. Priorizar `score_engine`,
   `indicators`, Spearman/métricas e o `retry`.

---

## 5. Limpeza (feita nesta sessão)

Removido tudo que não é usado, deixando só os fontes do pacote + venv + docs:

- `core.zip` (backup stale com chaves antigas), `Novo Arquivo` (órfão),
  `GarimpoInvestimentos/GarimpoInvestimentos/` (subpasta vazia),
  `GarimpoInvestimentosCrypto/` (stub `.pyproj` morto do VS),
  `GarimpoInvestimentos/.vs/` (estado do Visual Studio) e todos os `__pycache__/`.
- Não há módulo `.py` morto: tudo em `analyzers/collectors/core/output` é importado
  por `main` ou `backtest`. O `.gitignore` evita o reacúmulo de `__pycache__`/`.vs`.

Há cópias divergentes e **desatualizadas** do projeto em
`C:\Users\Superleo13\source\repos\GarimpoInvestimentos` e
`C:\Users\Superleo13\Downloads\GarimpoInvestimentos_vstudio`. A cópia canônica é
**`C:\Claude\ProjetosPython\GarimpoInvestimentos`**.

---

## 6. Como rodar (resumo)

```powershell
cd C:\Claude\ProjetosPython
# pipeline (sem flags = DEFAULT_ASSETS do .env)
GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.main
# com CLI
GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.main --assets bitcoin,solana --min-score 70 --summary
# backtest (Fase 2)
GarimpoInvestimentos\env\Scripts\python.exe -m GarimpoInvestimentos.analyzers.backtest
```

Roteiro de testes completo (deps, config, pipeline, CLI, cache, saídas, backtest,
independência de cwd): ver seção **"Como testar o projeto inteiro"** no `README.md`.

> Nota: a pasta foi movida de `C:\ProjetosPython` para `C:\Claude\ProjetosPython` em
> 14/06. O `python.exe -m` da venv continua funcionando no novo local; só os atalhos
> `activate` e `pip.exe` da venv guardam o caminho antigo — use sempre
> `env\Scripts\python.exe -m pip ...` (ou recrie a venv) se precisar instalar algo.
