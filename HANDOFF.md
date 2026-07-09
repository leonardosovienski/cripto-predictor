# HANDOFF — GarimpoInvestimentos (Fase 1 + melhorias)

Data: 2026-06-14 (última rodada: 2026-07-07 — Auditoria + Experiment Registry)
Estado: **Fase 1 + CLI + notícias + backtesting + sinal calibrado + indicadores técnicos + LLM multi-provedor + métricas + retry/backoff + agendamento diário + V3 (edge mecânico: funding/OI/HMM).**

> **NOTA (jun/2026 — Red Team):** o pacote `core/` foi **renomeado para `store/`**
> (eliminar a colisão de nome com `predictor_core`). Toda referência a `core/X.py` nas
> entradas históricas abaixo corresponde hoje a **`store/X.py`** — o texto do changelog
> foi preservado como registro do que aconteceu, não reescrito. Falhas silenciosas
> (`except Exception`) foram instrumentadas e a Fase-1 passou a emitir o sinal via
> `predictor_core.obs.emit_event` (paridade de telemetria com o V3).
>
> **ERRATA (jul/2026):** o rename `core/`→`store/` foi DESFEITO na reconciliação
> com o histórico antigo do GitHub (merge `a3404ce`) — a árvore atual usa
> **`GarimpoInvestimentos/core/`** de novo. A colisão temida era com
> `predictor_core` (nomes distintos, sem conflito de import real). Referências a
> `store/X.py` abaixo correspondem hoje a `core/X.py`.

---

## 🔴 Rodada 2026-07-09 — Auditoria cruzada: correções + REFUTAÇÃO do GO do BTC

**Correções (commits 7cd3d58, 1e033c8, c43ce51, 7d6cc07)**: CLI do Kelly sweep
consertado (TypeError com --taker-fee-bps — regressão do Risco 4, sem teste de
CLI; agora coberto); idempotência no paper_trader (re-execução duplicava o
sinal do dia e o paper_report contava dobrado — livro real tinha 2 duplicatas,
todas FLAT, deduplicado com backup); helper único `v3/timeindex.py` (3 cópias
de nearest-timestamp viraram bisect O(log n)); reporter em UTC. Suíte 254→266.

**ACHADO MAIOR (C2 → refutação)**: investigando o PSR sobre retornos de 24h
amostrados a cada 8h (sobreposição infla significância), o WFA foi re-rodado
na base ATUAL (2021 → jul/2026; a homologação de jun/2026 usou 2021 → out/2024):

| Config | PSR | IC_lower | MaxDD | Veredicto |
|---|---|---|---|---|
| Custos completos (fee 10bps + funding), kelly 0.5 | 0.465 | **−0.0794** | 15.56% | **NO-GO** |
| Custos da época da homologação (slip 5bps) | 0.728 | **−0.0794** | 23.74% | **NO-GO** |
| PSR sem sobreposição (3 sub-séries 24h) | 0.009 / 0.701 / 0.470 | — | — | 0/3 |

Causa dominante: **extensão da base** — o edge funding/OI não se sustentou no
forward 2025-26 (IC_lower era +0.0205 em out/2024; virou −0.079 e cruza zero).
Retorno líquido médio por sinal: **−0.000003** (IC95 cruza zero). Todos os 45
folds ficam INSUFFICIENT_DATA (<10 sinais ativos). Coerente com o paper
trading: só FLATs desde 28/06. Reprodução: `python -m ...backtest_v3 --symbol
BTCUSDT` e `python scripts/psr_nonoverlap.py`.

**Implicação para a decisão de 28/07: NÃO promover a capital real.** O GO de
junho era específico do regime 2021-24 e anterior ao modelo de custos.

**Decisões de produto PENDENTES (dono)**: (1) destino do V3 — encerrar,
manter em paper como sonda de regime, ou pesquisar variante; (2) **C6**:
Fase 1 LLM maturou Sharpe **−0.5734** (trial 1, n pequeno) — decidir
continuidade até 28/07 e registrar no Experiment Registry.

**Limitação documentada (C3)**: MaxDD do WFA compõe P&L de sinais
sobrepostos como sequenciais — não é DD de portfólio realizável (nota em
`_equity_curve`; correção na v2 do backtest, no core).

---

## ⭐ Rodada 2026-07-07 — Auditoria + Experiment Registry + qualidade de medição

**Bug CRÍTICO corrigido:** a regra não-ancorada `data/` no `.gitignore` engolia o
pacote `vendor/predictor_core/data/` (o commit `20128f6` referenciava a camada,
mas ela nunca entrou no git) — **qualquer clone fresco quebrava com 22 erros de
coleta**; a suíte só passava na máquina do dono (arquivos presentes, untracked).
Corrigido (`/data/` ancorado + camada commitada do canônico, hashes batem com o
CORE_MANIFEST) e blindado: `tests/test_repo_hygiene.py` falha se qualquer `.py`
de código estiver gitignorado ou se arquivo do manifesto estiver untracked.
Prova: clone limpo → suíte verde.

**Experiment Registry (governança do DSR):** schema formal do `trials.json`
(`validate_trials`, validado pela suíte contra o arquivo real); mudar `params`
de trial existente é ERRO — variação de configuração é tentativa NOVA (N+1);
`close_trial_sharpes` no backtest grava o Sharpe por-trade automaticamente
quando um estrato de Fonte casa com uma trial e tem n≥3 sinais fortes maduros
(nunca cria trial — pré-registro segue humano).

**Feature Store (schema 6→8):** guard temporal bidirecional na inserção
(`published_at < ts` = look-ahead de rotulagem; `> ts+45d` = anomalia; segunda
cinta — o contrato já barrava o limite inferior); migração **0007**
`feature_version` na PK de `features_aligned` (lógica nova escreve ao lado,
nunca por cima; histórico = 'v1'); migração **0008** `input_degradado` nas
predictions (NULL p/ legado — nunca reinterpretar o passado).

**Qualidade de medição:** backtest mede o preço realizado OFFLINE-FIRST
(`close_on` na store, preferindo a família de fontes da previsão; CoinGecko só
como fallback; coluna `medida_d*` carimba a régua); estratificação por input
degradado no relatório; `series_quality` na ingestão (gaps + saltos >30% viram
`data.quality_warning` + aviso no console, sem bloquear); previsões carimbadas
em **UTC** (`utc_stamp`; pré-2026-07-07 são BRT, skew ≤3h documentado).

**Backlog condicional B1–B8** em docs/HYPOTHESES.md (triagem de propostas
externas; nada consome tentativa; ativação típica: pós-veredicto H4).

Suíte: **201 → 241 verdes** (+40 testes). Nenhuma dependência nova. Auditoria
externa (LLM sem ler o código) foi triada: achados factualmente errados
descartados e documentados; Prefect/Docker/L2/Regime-Shift rejeitados por
complexidade sem benefício.

---

## ⭐ V3.3.2 — Bug do agendador (encoding) + smoke test validado (2026-06-28)

**Incidente:** o agendador `GarimpoV3Daily` rodou em 27/06 21:30 mas **falhou
(Último resultado: 1) e não criou log** — não havia smoke test de fato.

**Causa-raiz:** `scripts/run_daily_v3.ps1` tinha caracteres não-ASCII (em-dash `—`,
acentos). O Windows PowerShell 5.1 lê `.ps1` **sem BOM como Windows-1252**; o byte
`0x94` do em-dash UTF-8 (`E2 80 94`) vira **`"` (aspas)** no 1252, corrompendo o
balanceamento de aspas/chaves → **erro de parse** → `powershell -File` sai 1 ANTES
de executar (por isso nenhum log). Diagnosticado com
`[Parser]::ParseFile(...)` ("`}` de fechamento ausente na linha 30").

**Correção:** script reescrito em **ASCII puro** (0 bytes não-ASCII). Regra
permanente: **manter `.ps1` sem acentos e sem travessões** (comentário no topo do
script avisa). Parse confirmado limpo.

**Smoke test validado (28/06):** rodado na invocação idêntica à do schtasks, exit 0.
- Encanamento end-to-end OK (vision_ingest → pipeline → paper_trader → paper_report).
- **Catch-up não-destrutivo provado:** funding 4108→**5931**, OI 433k→**616k** (cresceu,
  não foi clampado — o fix do V3.3.1 segurou).
- **Sinal corrente:** BTC FLAT @ **73.499** (jun/2026), não mais o cache de out/2024.

**Lição registrada:** os 3 paper trades acumulados são TODOS FLAT — confirma na
prática que 30 dias com sinal a 2.4% geram ~0–2 trades ativos. **A janela de 30
dias é smoke test OPERACIONAL, não validação estatística.** A validação do edge já
é a WFA (29 folds, PSR 0.909); capital pequeno se apoia nela + encanamento limpo,
não em significância de 2 trades.

> Cross-projeto: nesta mesma sessão, o `wc-predictor-v2` (futebol) teve seu edge
> **refutado** com a régua open-CLV (sem edge — ver HANDOFF do wc). O investimento
> de atenção fica no V3, que é o único dos dois que passou no juiz estatístico.

---

## ⭐ VERSÃO V3.3 — Sweep multi-ativo e automação (2026-06-27)

### Resumo

Fechamento para **produção assistida**: lock de dependências limpo, automação do
feed diário, relatório semanal de paper trading e início da ingestão ETH/SOL.

### Tarefas executadas

| # | Tarefa | Estado |
|---|--------|--------|
| 1 | Ingestão histórica ETHUSDT/SOLUSDT (Binance Vision) | 🟡 EM ANDAMENTO (ver abaixo) |
| 2 | Feed diário automatizado | ✅ `scripts/run_daily_v3.ps1` |
| 3 | Regeneração do `requirements.lock.txt` (sem loguru) | ✅ |
| 4 | Relatório de paper trading | ✅ `v3/paper_report.py` |
| 5 | Integridade do wc-predictor-v2 | ✅ 94/94 |

### Tarefa 3 — Lock regenerado

`requirements.lock.txt` regenerado na `.venv_v3` (Python 3.13.14) com o
`requirements.txt` COMPLETO instalado (Fase 1 + V3). **loguru removido**;
confirmadas: google-genai, openai, openpyxl, python-dotenv, hmmlearn, httpx,
pydantic, numpy, scikit-learn, pandas. (Atenção: congelar só a venv V3 sem as
deps da Fase 1 truncaria o lock — por isso o `pip install -r requirements.txt`
ANTES do freeze.)

### Tarefa 2 — Feed diário (`scripts/run_daily_v3.ps1`)

Auto-ancorado (raiz via `$PSScriptRoot`, sem path hardcoded — o `run_daily.ps1`
da Fase 1 tem path defasado `C:\Claude\ProjetosPython`, **não alterado** por ora).

> 🔴 **BUG corrigido durante a execução:** a 1ª versão usava `pipeline
> --force-refresh`. Isso é **DESTRUTIVO**: `force_refresh=True` re-coleta OI via
> `OICollector` REST, que **clampa em 30 dias** (`_MAX_OI_HISTORY_DAYS=30`,
> limite da Binance) e **sobrescreve** os 433k registros históricos de OI (base
> de treino do HMM). Corrigido para o fluxo NÃO-destrutivo:
> **`vision_ingest` (estende histórico do data lake até ontem) → `pipeline` SEM
> force-refresh (lê CSVs atualizados + modelo treinado) → `paper_trader` →
> `paper_report`.** A atualização de dados é responsabilidade do `vision_ingest`,
> nunca do REST. Lag de ~1 dia (data lake), aceitável para horizonte de 24h.

Loga em `logs/v3_daily_<data>.log`.

### Tarefa 4 — Relatório de paper trading (`v3/paper_report.py`)

Lê `data/v3/paper/{symbol}_paper.jsonl`, casa cada posição com o preço D+horizon
(spot_1h.csv) e computa: P&L acumulado (log), MaxDD corrente (predictor_core.stats),
hit rate, distribuição por regime/motivo. Emite `paper_report` (domain `v3_paper`).
8 testes novos (puros, rodam no global).

### Tarefa 5 — wc-predictor-v2

94/94 testes verdes. `prediction` e `status_check` confirmados emitindo em
execução real (`predict Brazil Argentina`, `status`). `ingest_done` está cabeado
e compila, mas **não exercido** — rodar o `ingest` toca rede/produção (projeto é
SHADOW read-only). Verificar numa janela de manutenção dedicada.

### Tarefa 1 — Ingestão + Sweep ETHUSDT: **NO-GO (sem edge)**

ETHUSDT ingerido (funding 4381, OI 324k de **mai/2022**, spot 35k). Sweep rodado
(26 folds, fr_window=90, frações [1.0, 0.5, 0.25, 0.10]):

| Kelly | PSR | IC | IC_lower | MaxDD | Veredicto |
|-------|-----|-----|----------|-------|-----------|
| 1.00 | 0.125 | **−0.113** | −0.353 | 22.61% | ❌ NO-GO |
| 0.50 | 0.125 | −0.113 | −0.353 | 11.73% | ❌ NO-GO |
| 0.25 | 0.125 | −0.113 | −0.353 | 5.97% | ❌ NO-GO |
| 0.10 | 0.125 | −0.113 | −0.353 | 2.41% | ❌ NO-GO |

**Conclusão (crítica):** o ETH **não tem edge** neste período. Diferente do BTC,
a falha **NÃO é de risco** (MaxDD passa folgado em 0.25/0.10) — é de **sinal**:
PSR=0.125 (vs BTC 0.909) e **IC NEGATIVO** −0.113 (vs BTC +0.229), IC_lower
−0.353 (cruza zero). Kelly fracional é **inútil** aqui: ele só escala MaxDD, não
PSR/IC. Nenhuma fração resgata um edge inexistente.

**Decisão:** ETHUSDT **NÃO homologado**, **NÃO adicionado** ao `$symbols` do feed
diário. O edge funding/OI-overcrowding é **específico do BTC** nestes regimes.
Resultado negativo valioso: confirma que o juiz estatístico **não dá falso
positivo** (coerente com a validação de "NO-GO correto em ruído"). SOLUSDT
permanece em backlog. BTCUSDT segue como único ativo em produção assistida.

> Ressalva metodológica: a janela do ETH (mai/2022–dez/2024) difere da do BTC
> (2021–2024) por indisponibilidade de OI no data lake. Ainda assim, IC negativo
> não é artefato de período — indica ausência de edge, não edge enfraquecido.

### Produção Assistida — início dos 30 dias (autorizado pelo arquiteto)

| Item | Valor |
|------|-------|
| **Ativo em produção assistida** | BTCUSDT |
| **Kelly homologado** | **0.50** (PSR 0.909, IC_lower +0.0205, MaxDD 10.45%) |
| **Agendador** | Task `GarimpoV3Daily`, Windows Task Scheduler |
| **Horário** | 21:30 local (UTC-3) = **00:30 UTC** (após fechamento do daily candle) |
| **Comando** | `powershell -ExecutionPolicy Bypass -NoProfile -File <repo>\scripts\run_daily_v3.ps1` |
| **1ª execução agendada** | 2026-06-27 21:30 local |
| **Início oficial dos 30 dias** | **2026-06-28** (1º candle diário com agendador ativo) |
| **Fim previsto** | **2026-07-28** (avaliação: capital real + design `predictor_core.backtest`) |

Validação manual da cadeia (em cache out/2024): `paper_trade` emitido,
`paper_report` coerente (trades flat / `no_signal` — esperado até o catch-up de
dados frescos via `vision_ingest` no 1º run agendado). Acompanhamento semanal via
`paper_report.py`. **Gatilho de alerta:** MaxDD corrente do paper > 15% → reportar
imediatamente ao arquiteto.

### Testes (contagem atual)

- **previsao-cripto: 88** (76 portáveis no global + 12 hmmlearn-gated na venv V3).
- **wc-predictor-v2: 94**.

---

## ⭐ V3.3.1 — Correção de force-refresh destrutivo (2026-06-27)

**Incidente (capturado em revisão, ANTES de ir a produção):** a 1ª versão do
`scripts/run_daily_v3.ps1` chamava `pipeline --force-refresh` no feed diário.

**Falha latente:** `force_refresh=True` faz o pipeline re-coletar OI via
`OICollector` REST, que **clampa em 30 dias** (`_MAX_OI_HISTORY_DAYS=30`, limite
da API Binance, erro -1130 acima disso) e em seguida **`save_oi_csv` sobrescreve**
`data/v3/{symbol}/oi.csv`. Resultado: os **433k registros históricos de OI
(2021-2024)** seriam trocados por ~30 dias de REST — **destruindo a base de treino
do HMM**. O modelo continuaria rodando sobre dados mutilados, emitindo sinais
espúrios **sem alerta** (falha silenciosa).

**Correção:** fluxo NÃO-destrutivo — a atualização de dados é responsabilidade
EXCLUSIVA do `vision_ingest` (data lake, append/cache não-destrutivo); o
`pipeline` no diário roda **sem** `--force-refresh` (lê os CSVs já estendidos +
carrega o modelo HMM treinado, inferência causal). Ver V3.3 Tarefa 2.

**Lição arquitetural (regra permanente):** *nunca permitir que um comando de
coleta LIMITADA (REST clampado, amostragem, janela curta) sobrescreva um artefato
de dados HISTÓRICO COMPLETO.* Coleta incremental/limitada e base histórica devem
ter caminhos de escrita separados. Onde houver clamp/limite de API, o save deve
ser append-guarded ou bloqueado contra overwrite de série longa.

---

## ⭐ VERSÃO V3.2 — Kelly Sweep + Paper Trading + Logging Unificado (2026-06-27)

### Resumo executivo

O V3 **passou no Go/No-Go** via position sizing (Kelly fracional), sem tocar no
modelo. O edge sempre foi real; o único gargalo era risk sizing — resolvido.

### Kelly Sweep — BTCUSDT (homologado)

Comando: `python -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT --kelly-fractions 1.0 0.5 0.25 0.10`

Data do sweep: **2026-06-27** | Dados: BTCUSDT 2021-01-01 → 2024-10-01 (29 folds, fr_window=90)

| Kelly | PSR | IC_lower | MaxDD | Veredicto |
|-------|------|----------|-------|-----------|
| 1.00 | 0.909 | +0.0205 | 20.14% | ❌ NO-GO |
| **0.50** | **0.909** | **+0.0205** | **10.45%** | ✅ **GO (homologado)** |
| 0.25 | 0.909 | +0.0205 | 5.32% | ✅ GO |
| 0.10 | 0.909 | +0.0205 | 2.15% | ✅ GO |

**Insight-chave:** PSR e IC_lower são **invariantes** sob fracionamento de Kelly
(o Kelly escala exposição, não o sinal). Só o MaxDD escala — quase linearmente.

**Thresholds aprovados (Go/No-Go):** PSR ≥ 0.80 · IC_lower > 0 · MaxDD < 20%.

**Fração homologada: `DEFAULT_KELLY_FRACTION = 0.50`** (`v3/backtest_v3.py`).
Critério: maior fração com GO → maximiza retorno absoluto dentro do orçamento de
risco, com margem confortável (10.45% < 18%). A escolha "menor fração vencedora"
foi rejeitada por ser degenerada (a menor sempre vence trivialmente, subutilizando
o orçamento de risco). PSR idêntico em todas → a decisão é retorno absoluto vs DD.

### Paper Trading (`v3/paper_trader.py` — NOVO)

- Domain `v3_paper`; evento `paper_trade` (direction, strength, kelly_fraction,
  position, ref_price, regime_confidence + metadados).
- Persiste em `data/v3/paper/{symbol}_paper.jsonl` (append-only).
- Aplica a fração homologada (0.50) ao sinal MAIS RECENTE do pipeline V3.
- Uso: `python -m GarimpoInvestimentos.v3.paper_trader --symbol BTCUSDT --start-date 2021-01-01`
- ⚠️ Para sinal "de hoje" real, o pipeline precisa re-ingerir dados frescos
  (`--force-refresh`). Hoje o cache do BTC termina em out/2024.

### Logging unificado (Fase 1) — `loguru` REMOVIDO

- `store/logger.py` reescrito: stdlib `logging` + `emit_event`. Zero `print()`.
- Domain padronizado **`previsao_cripto`** (Fase 1/2). V3 mantém `v3_cripto`;
  paper trading usa `v3_paper`.
- Eventos: `pipeline_start/success/error`, `fallback_triggered`, `cache_integrity`,
  `llm_quota_alert`, `batch_start/success`, `toll_passed`.
- Collectors e analyzers deixaram de ser silenciosos (logging mínimo adicionado).

### Resiliência (Fase 1)

- `main.py`: `asyncio.gather` + `Semaphore(5)` (paralelismo respeitando rate limit).
- Alerta de cota LLM: fallback > 20% dos ativos → `llm_quota_alert` + WARNING.

### Ambiente

- **venv V3: `.venv_v3` (Python 3.13.14)** — hmmlearn NÃO compila no 3.14 global
  (sem MSVC). 3.13 tem wheel binário. `py install 3.13` resolveu.
- Suíte: **80 testes verdes** na venv V3 (`PYTHONPATH=vendor;. pytest tests/`).
  68 no global (sem os testes que dependem de hmmlearn).

### Pendências

- **ETHUSDT / SOLUSDT:** sweep não rodou — dados não existem em `data/v3/`.
  Exigem `python -m GarimpoInvestimentos.v3.pipeline --symbol ETHUSDT SOLUSDT --start-date 2021-01-01`
  (ingestão via rede Binance Vision).
- **Feed diário:** automatizar pipeline `--force-refresh` 1×/dia para o paper
  trading registrar sinais correntes (hoje usa cache até out/2024).

---

## 0. Integração à plataforma predictor_core (2026-06-16/17)

Sessão de plataforma — o Garimpo virou consumidor do núcleo canônico `predictor_core`
(vendorizado em `vendor/`, sincronizado por hash). Visão arquitetural completa da
plataforma (DPL, Feature Store, Alignment Engine, CCXT, ADRs, backlog) no
[docs/DOSSIE_PLATAFORMA.md](docs/DOSSIE_PLATAFORMA.md). Mudanças:

| Área | Mudança |
|------|---------|
| Significância | `analyzers/backtest.py` emite **Spearman com IC95%** (block bootstrap PAREADO via `predictor_core.stats`) — "validado / RUÍDO" em vez de estimativa pontual nua. |
| Modo B / reprodutibilidade | **carimbo do juiz** (`provider:modelo:hash-do-prompt`) em cada previsão (`ai_insights.judge_signature`), persistido no histórico (coluna `Juiz`). |
| Cross-check | `score_engine.divergence_flag` — tagueia contradição LLM×indicadores determinísticos (flag-only, **não muta o score**); o backtest **estratifica** alinhadas vs divergentes. |
| Degradação | `main.py` instrumenta `input_degraded` (notícia/indicador faltando deixou de ser engolido). |
| Rede unificada | imports de rede agora vêm de `predictor_core.net` (httpx async + retry); `core/retry.py` e `core/http_client.py` **deletados** (duplicata aposentada). |
| Trava de credenciais | `config.__post_init__` usa `predictor_core.settings.require_secrets` — chave ausente/falsa/`<16 chars` → **crash imediato**. `requirements.lock.txt` cravado. |

**Suíte: 26 testes verdes** (`py -3.12 -m pytest tests/ -q`). O caminho **live nunca
rodou** (`.env` vazio crasha de propósito — falta colar chaves reais: P0).

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

## 2f. V3 Crypto-Predictor — Fase 1: validação de edge mecânico (2026-06-25)

Linha de pesquisa **nova e independente** do pipeline LLM. Hipótese: edge vem de
ineficiência mecânica — **funding rate extremo + OI crescendo** (alavancagem forçada)
condicionado por **regime de volatilidade (HMM)**. Sem WebSocket L2, sem notícias.

**Arquitetura** (`GarimpoInvestimentos/v3/`):

| Arquivo | Papel |
|---|---|
| `circuit_breaker.py` | CLOSED/OPEN/HALF_OPEN; propaga `data_quality_score` (1.0/0.5/0.0). |
| `collectors/funding_collector.py` | Funding rate 8h (Binance fapi), CSV idempotente, `with_retry`+CB. |
| `collectors/oi_collector.py` | Open Interest (period **`1h`**), clampa em 30d (limite Binance). |
| `collectors/spot_collector.py` | Klines 1h spot. |
| `feature_builder.py` | `funding_zscore`, `oi_log_delta`, `leverage_pressure`, `realized_vol_24h`. Nunca interpola. |
| `regime_engine.py` | GaussianHMM 3 estados; **Forward Algorithm causal à mão** (hmmlearn.predict_proba usa forward-backward = lookahead). |
| `signal_engine.py` | SignalRecord canônico; short/long/flat; degradado→CRITICAL. |
| `pipeline.py` | Orquestra coleta→features→HMM→sinais; CLI `--symbol/--start-date`. |
| `backtest_v3.py` | WFA 180/30/7d + PSR + Spearman CI + MaxDD → veredicto GO/NO-GO. |

**Bugs reais encontrados e corrigidos na verificação** (o backtest quebrava ou produzia
lixo silencioso antes disso):

| Bug | Sintoma | Fix |
|---|---|---|
| `spearman_block_ci` retorna **tupla** `(rho,lo,hi)`, programei contra objeto `.ci_lower` | `AttributeError` no 1º fold | unpack de tupla + None-handling |
| `max_drawdown` espera **equity acumulada**, passei retornos brutos | `max_drawdown([.01,-.02,.03])=3.0` (300% falso) | `_equity_curve()` composto antes |
| Warmup do z-score (90 períodos) recomputado por fatia OOS (30d≈90) | **~0 features/fold** | features construídas **uma vez** na série contínua, particionadas por timestamp |
| `period="8h"` no OI hist | HTTP 400 (-1130) toda chamada | → `"1h"` (alinha exato nos funding times) |

**🔴 LIMITE DURO do REST: OI histórico grátis = ~30 dias.** `openInterestHist` recusa
start > ~30d (`startTime invalid`). Com z-score consumindo 30d de warmup, sobram **~61
feature vectors reais**, abaixo do piso de 100 do HMM → Go/No-Go histórico inviável só
com REST.

**✅ RESOLVIDO — Quarta Via: data lake público `data.binance.vision`.** A Binance arquiva
anos de funding + OI (dataset **`metrics`**, 5min, desde ~2021) + klines em ZIPs grátis.
Dois módulos novos:

| Arquivo | Papel |
|---|---|
| `collectors/binance_vision.py` | Baixa ZIPs (cache local + verificação **SHA256**), parseia e devolve os MESMOS dataclasses (FundingRecord/OIRecord/KlineRecord). Funding/klines = mensais; OI metrics = diários. |
| `vision_ingest.py` | CLI que grava nos MESMOS CSVs do caminho REST → `pipeline`/`backtest_v3` rodam sem alteração. |

Schemas reais confirmados (2026-06-25): funding `calc_time(ms)/last_funding_rate` (sem
mark_price → 0.0); metrics `create_time(str UTC)/sum_open_interest/sum_open_interest_value`;
klines padrão. Join funding×OI: match exato em ~86% dos ts, resto cai na tolerância ±5min.
`oi_collector` REST permanece só para coleta **ao vivo**. Decisão do Leo: validar o
Go/No-Go sobre BTC com janela de anos via Vision **antes** de qualquer infra de WebSocket.

**Perf:** `feature_builder` tinha hotspot O(n²) (re-ordenava o spot a cada ts) — corrigido
com `bisect` (O(n log n)), necessário para escala de anos do data lake.

### Diário de pesquisa — runs do WFA (Go/No-Go)

| Data | Janela | fr_window | Folds | PSR | IC_CI_lower | MaxDD | Veredicto | Leitura honesta |
|---|---|---|---|---|---|---|---|---|
| 2026-06-25 | BTC 2024-01→10 (9m) | 90 | 2 | 1.000 | −0.148 | 0.1% | NO-GO | **INCONCLUSIVO por underpowering** — <10 sinais/OOS, CI [−1,1] degenerado. |
| 2026-06-25 | BTC 2021→2024 (anos) | **90** | **29** | **0.909** | **+0.021** | **20.14%** | NO-GO (só MaxDD, por 0.14pp) | **EDGE REAL.** IC_lower>0 (não cruza zero) + PSR>0.80. Falha só no risco, na trave. |
| 2026-06-25 | BTC 2021→2024 (anos) | **21** | **36** | 0.896 | **−0.092** | **12.06%** | NO-GO (só IC) | Pivot baixou MaxDD (20→12%) mas **matou o edge** (IC cruza zero). Janela curta = ruído de spike. |

**Conclusão dos 3 runs:** a tese de alavancagem **sobrevive ao WFA de poder real** — no baseline de
29 folds (anos, 5bps slippage) o IC_lower ficou **positivo** e o PSR limpou 0.80. As duas configs
reprovam em critérios **opostos**: fr_window=90 tem edge mas MaxDD=20.14% (0.14pp acima); fr_window=21
controla risco (12%) mas perde significância. **O pivot de fr_window foi o lever errado** — o edge mora
na janela longa (funding extremo *sustentado*), e a falha do baseline é de **gestão de risco**, não de
normalização. Próximo lever: **position sizing** (fractional Kelly 0.25x / vol-targeting) para puxar o
MaxDD <20% preservando o IC_lower>0. NÃO mexer mais no fr_window.

**Diagnóstico de esparsidade** (727 features): `|z|≥2.0` → só 36 (5%); `|z|≥1.0` → 141 (19%).
z-score std=1.29 e max=7.66 ⇒ janela de 90 (30d) mistura regimes de funding (não-estacionária).

**Plano aprovado (próximo run, dados 2021→2024):**
1. Ingestão massiva via Vision (em andamento) — engloba bull 2021 / bear 2022 / recovery 2023-24.
2. **Baseline:** `backtest_v3 --fr-window 90` (linha de base de longo prazo).
3. **Pivot:** `backtest_v3 --fr-window 21` (z-score local-estacionário; +gatilhos sem baratear o threshold).
   - Flag `--fr-window` adicionada ao `backtest_v3` (default 90; thread → `build_feature_vectors`; gravada no `wfa_result`).

**Camada 1 auditada (sem lookahead):** HMM re-treina por fold (`engine=RegimeEngine()` DENTRO do
loop, `fit()` só no IS); `StandardScaler` fit no IS e só `transform` no OOS; rotulagem bull/bear
por mean-return do IS; `all_features` construído 1× é seguro (features são rolantes causais);
purge de 7d entre IS e OOS.

**Validação real (não só syntax):**
- ✅ Cadeia pura testada (feature_builder→signal_engine, todos os caminhos).
- ✅ HMM treinado + Forward causal + WFA rodados em dado sintético → **NO-GO correto em
  ruído** (juiz não dá falso positivo); evento `wfa_result` emitido.
- ✅ Coletores batem na Binance real: funding=359, OI clampado ~21d, 2877 klines, 61 features.
- 🔴 Veredicto sobre BTC real bloqueado pelo limite de OI.

**Deps novas** (`requirements.txt`): `hmmlearn`, `numpy`, `scikit-learn` — instaladas neste ambiente.

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
