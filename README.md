# cripto-predictor (GarimpoInvestimentos + DPL)

> ## Estado do incidente de segurança — `ROTATED_CONFIRMED_BY_OWNER_2026-08-19`
>
> Uma credencial SerpAPI apareceu em texto claro em 5 logs históricos de
> `logs/garimpo_fase1_*.log` (gitignored, nunca entraram no Git). A **causa** — o
> wrapper de execução preservava stdout/stderr do processo filho sem redação — foi
> corrigida e verificada (`GarimpoInvestimentos/security/redaction.py`, delegando a
> `predictor_ops.redaction`). As 5 chaves expostas foram **rotacionadas**, confirmado
> diretamente pelo dono do repositório em 2026-08-19.
>
> Continua pendente como ação externa (não observável a partir deste repositório):
> confirmar no painel de cada provedor que as chaves **antigas foram revogadas** (não
> apenas que novas foram geradas) e verificar uso indevido antes da rotação. Por isso
> o estado é `ROTATED_CONFIRMED_BY_OWNER`, não `RESOLVED`. Nada disso bloqueia o
> pipeline, que já opera com as chaves novas.
>
> Registro canônico: [docs/SECURITY_INCIDENT_SERPAPI.md](docs/SECURITY_INCIDENT_SERPAPI.md).
> Nunca abra os 5 logs históricos em texto bruto.

Sistema de **pesquisa** em previsão de criptoativos, em duas camadas:

- **GarimpoInvestimentos** (previsão): descobre candidatos no mercado, analisa com
  LLM (Gemini/OpenAI/Groq/Cerebras/Mistral) + indicadores técnicos, grava previsões
  carimbadas e valida com backtest estatístico (Spearman + IC95% + Deflated Sharpe).
- **DPL — Data Provider Layer** (`GarimpoInvestimentos/dpl/`): camada de dados
  bitemporal com fallback multi-fonte, agregação por consenso, Circuit Breaker e
  **Feature Store** (SQLite) que é o repositório oficial de dados E de previsões.

```
--discover (momentum+trending) ─┐
--assets ───────────────────────┼→ INGESTÃO (DPL: Binance→CoinGecko | consenso c/ Kraken)
                                └→ Feature Store (bitemporal, anti-lookahead)
                                        ↓ serving offline
                     ANÁLISE (LLM + indicadores + notícias) → score 0-100
                                        ↓ carimbos: Juiz + Fonte
                     predictions (histórico oficial) → BACKTEST (Spearman IC95% + DSR)
```

A **V3 quantitativa** (HMM de regimes + funding/OI + walk-forward com custos) vive em
`GarimpoInvestimentos/v3/`, já integrada nesta linha — a reconciliação planejada em
[docs/RECONCILIACAO_V3.md](docs/RECONCILIACAO_V3.md) foi executada, e a branch
`claude/v3-quant-wip` citada naquele plano não existe mais.

## Status do projeto (2026-08-21)

**Pesquisa. Nenhuma recomendação de capital real.** Nota da auditoria: **6,0/10**
([docs/ARQUITETURA_CONSOLIDADA.md](docs/ARQUITETURA_CONSOLIDADA.md) §5). Modo atual:
`PROSPECTIVE_OBSERVATION` — auditoria e remediação fechadas (`AUDIT_AND_REMEDIATION =
CLOSED`, sem blockers de código), o próximo passo é acumular coleta, não nova auditoria.
Fechamento canônico em [docs/RELATORIO_FINAL.md](docs/RELATORIO_FINAL.md) §9.

Estado das hipóteses pré-registradas ([docs/HYPOTHESES.md](docs/HYPOTHESES.md);
travado em código por `charters/scientific_state.json`):

| # | Hipótese | Trial (`trials.json`) | Status |
|---|---|---|---|
| H1 | Funding/OI + regime HMM prevê retorno 24h | `v3-hmm-funding-oi-fr90` | **CLOSED_NO_GO** — bruto +0,44bps → líquido −0,09bps; PSR 0,445 |
| H2 | Janela curta de funding (fr21) | `v3-hmm-funding-oi-fr21` | **CLOSED_NO_GO** — PSR 0,215 |
| H3 | Horizonte 48h amortiza a fricção | `v3-hmm-funding-oi-fr90-h48` | **CLOSED_NO_GO** — edge bruto vira negativo; MaxDD 50,3% |
| H4 | Score do LLM prevê retorno D+7 | `v2-dpl-gemini-h7` | **CLOSED_INSUFFICIENT_SAMPLE** — coleta encerrada com n=5 |
| H5 | Idem, partição multi-juiz | `v2-dpl-multi-h7` | **CLOSED_NO_GO** — Spearman −0,166 [−0,266; −0,057], n=440 (IC não cruza zero, mas na direção oposta) |
| H6 | Leitura **invertida** do score do LLM | `h6-sinal-invertido-d7` | **ATIVA / IMATURA** — definição congelada por hash; gate exige n≥30 |
| H7 | Calendário macro (FOMC/CPI/PPI) + DXY | não registrada | **REGISTERED_NOT_ACTIVATED** — infra pronta, coleta não iniciada |

O NO-GO da V3 é o primeiro veredito *confiável* do projeto: HMM auditado sem
look-ahead, custos modelados, controle positivo provando que o pipeline detecta edge
quando ele existe, e DSR descontando as 7 tentativas registradas em
`GarimpoInvestimentos/trials.json`.

**Limitação registrada:** `HISTORICAL_REPRODUCIBILITY = LIMITED` — os dados brutos da
H5 foram perdidos, então a reanálise retrospectiva não é reproduzível. O IC histórico
dela foi *qualificado* (bootstrap sem `block_length` overlap-aware na época), nunca
reescrito.

## Funcionalidades

| Camada | O que faz |
|---|---|
| Discovery | Varre o top 100 (CoinGecko) + trending; filtra stablecoin/wrapped/volume<US$10M; ranqueia por momentum 7d/24h |
| Coleta (DPL) | Fallback Binance→CoinGecko ou consenso (mediana Binance+Kraken); Circuit Breaker; telemetria (`events.jsonl`) |
| Feature Store | OHLCV + sinais (Fear&Greed) alinhados por `published_at` (zero lookahead); features materializadas; tabela `predictions` append-only (migração 0016) |
| Análise | LLM sobre mercado offline + notícias live; carimbo do **Juiz** (provider:modelo:hash-do-prompt) e da **Fonte** (`direct`\|`dpl:fallback`\|`dpl:consensus`); ensemble multi-sample opcional (`LLM_ENSEMBLE_N`) |
| Backtest | Spearman(score, retorno D+1/7/30) com IC95% (block bootstrap pareado, `block_length` overlap-aware), estratificado por divergência e por Fonte; **DSR** contra o máximo-por-sorte das tentativas |
| Governança | Controle positivo (edge sintético → "validado"; ruído → "RUÍDO"); `trials.json` versionado; charters com checksum; migrações aditivas (ADR-017); **PBO/CSCV** ao lado do DSR (perguntas complementares: o DSR desconta por N tentativas, o PBO mede se a SELEÇÃO entre configurações é frágil) |
| V3 | GaussianHMM 3 estados com decodificação **causal** (auditada), sinais de funding/OI, WFA com custos (taker+slippage+funding real) |
| Operação | Jobs via `predictor_ops` (lock, heartbeat, artefato esperado), watchdogs, painel diário `quality_snapshot` com histórico append-only |

## Estrutura

```
GarimpoInvestimentos/
├── main.py / cli.py       ← CLI: --ingest, --discover N, --assets, --mode, --summary
├── phase1.py              ← orquestrador da coleta diária automatizada (H5 multi-juiz)
├── jobs.py                ← jobs operacionais via predictor_ops.run_job
├── governance.py          ← charters, planos de observação, validação por checksum
├── contracts.py           ← contratos do plugin (predição, coleta, settlement, health)
├── plugin.py              ← entry-point `predictor.plugins` (expõe a fronteira research-only)
├── config.py              ← Settings tipado (pydantic-settings) + fail-fast de segredos
├── collectors/            ← discovery.py (candidatos), news.py, serpapi_news.py
├── dpl/                   ← contratos, providers, routers, feature_store, migrações,
│                             macro_calendar.py (calendário FOMC — B1/H7)
├── analyzers/             ← ai_insights (LLM), indicators, prefilter, score_engine,
│                             backtest (inclui os gates da H6), trials (DSR), equivalence,
│                             pbo (Probabilidade de Overfitting via CSCV — B10),
│                             judge_calibration (régua por juiz — B11a),
│                             factor_dsl (fatores point-in-time, causal por
│                             construção — pré-requisito do B9),
│                             hypothesis_loop (LLM propõe hipótese, motor
│                             determinístico avalia — B9; NÃO registra trial,
│                             NÃO emite veredito, NÃO promove nada),
│                             gate_power (poder do gate — 'RUÍDO' com poder
│                             baixo é ausência de evidência, não evidência
│                             de ausência; NÃO altera gate nenhum),
│                             ground_truth_harness (afere o pipeline INTEIRO
│                             contra verdade plantada: erro de medição, perda
│                             de amostra, sensibilidade e especificidade)
├── services/              ← ingestion, features, inference, backtest, reporting
├── providers/             ← contratos de provider da camada de aplicação
├── v3/                    ← HMM de regimes, funding/OI, walk-forward com custos
├── trading/               ← contrato econômico, execução, microestrutura, portfólio, store,
│                             signal_adapter (SignalRecord→TradeIntent, recusa família
│                             congelada), report (visão única), cost_policy (escolhe o
│                             modelo de custo pelo instrumento e recusa o errado) —
│                             infraestrutura construída por OVERRIDE de governança
│                             2026-08-14 (docs/HYPOTHESES.md), ANTES de qualquer edge
│                             validado; não autoriza capital, não muda nenhum gate
├── observation_*.py       ← coleta, qualidade, resiliência e watchdog da observação
├── quality_snapshot.py    ← painel diário (engenharia × amostra científica)
├── security/redaction.py  ← redação de segredos em log (delega a predictor_ops)
├── core/                  ← paths, cache, history (store-first), logger, api_guard
├── output/reporter.py     ← exportação CSV/XLSX
├── macro_calendar.json    ← calendário FOMC 2026 (sourced/citado — ver source_note)
├── trials.json            ← registro VERSIONADO de tentativas (denominador do DSR)
└── h6_status.json         ← estado publicado da H6 (n, gate, veredito quando abrir).
                              Ponte produção→git: o n real vem do feature_store.db,
                              que é gitignored — sem este arquivo, nada fora da
                              máquina de coleta enxerga o n. Gerado pelo
                              quality_snapshot; commitado à mão quando muda.
charters/                  ← estado científico, definição congelada da H6, charters de coleta
observation_plans/         ← planos e ativações COLLECTION_ONLY (imutáveis, com checksum)
scripts/                   ← atestado do harness, backup, scan de segredos, CI check
tests/                     ← 738 verdes com `--all-extras`; 723 verdes + 2 skips com
                              `--extra test` (skips = numpy/hmmlearn, cobertos no CI)
docs/                      ← ADRs e auditorias (ver HANDOFF)
```

predictor-core/predictor-ops não são vendorizados: são wheels externas resolvidas via
`[tool.uv.sources]` a partir das GitHub Releases de core-predictor/predictor-ops, com
hash fixado em `uv.lock`. Boa parte da DPL (contratos, routers, circuit breaker,
trials/DSR, stats) já foi promovida ao core — os módulos locais correspondentes são
compat shims finos.

## Coleta exploratória `COLLECTION_ONLY`

Funding e open interest da V3 entram na DPL como `SignalPoint` bitemporal
enriquecido, com instrumento, métrica, unidade, `event_at`, `published_at`,
`ingested_at`, hash de conteúdo, versões de coletor/schema e flags de qualidade.
O charter versionado em `charters/funding_oi_v3.json` fixa SLA, retenção,
orçamentos e thresholds antes da coleta.

Esses dados permanecem em `scientific_state=COLLECTION_ONLY`: uma execução pode
terminar com `run_status=SUCCEEDED`, mas isso não constitui validação de hipótese
nem autorização de capital. O core exige registro de hipótese e `DatasetFreeze`
selado antes de qualquer promoção científica. Scorecards persistidos classificam
fontes separadamente como `HEALTHY`, `DEGRADED` ou `QUARANTINED`.

O Feature Store é ignorado pelo Git e possui backup online verificável e restore não
destrutivo. Procedimento: [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

## Instalação e configuração

Pré-requisitos: Python **3.13 ou 3.14** (`requires-python = ">=3.13,<3.15"`; ambos
exercitados no CI). O gerenciador canônico é o **uv** — Linux/container é o runtime
principal, e `DATA_DIR`, `OUTPUT_DIR` e `CACHE_DIR` são configuráveis.

```bash
# suíte offline, sem chaves:
uv sync --locked --extra test     # 723 verdes + 2 skips (numpy/hmmlearn ausentes)
uv build                          # necessário: test_distribution_security.py inspeciona dist/
uv run pytest -q

# suíte completa, sem skips:
uv sync --locked --all-extras && uv build && uv run pytest -q   # 738 verdes
```

Extras disponíveis: `llm`, `v3`, `excel`, `science` e `test`.

Para o **caminho ao vivo**, sincronize os extras que o pipeline usa e coloque as chaves
reais (>=16 chars) em `GarimpoInvestimentos/.env` — veja `.env.example`:

```bash
uv sync --extra llm --extra excel --extra v3
```

⚠️ Por design (fail-fast): `.env` sem as chaves exigidas pelo provedor configurado
**crasha no segundo zero**, na carga de `GarimpoInvestimentos.config`.

## Como rodar

```bash
# 1) DESCOBERTA + INGESTÃO (rede): acha candidatos e materializa na Feature Store
uv run python -m GarimpoInvestimentos.main --ingest --discover 10   # N máx: 20 (cota free tier)
#    ou lista fixa / consenso multi-exchange:
uv run python -m GarimpoInvestimentos.main --ingest --assets bitcoin,ethereum --mode consensus

# 2) ANÁLISE (mercado offline; só notícias/LLM tocam a rede)
#    sem --assets analisa tudo que está na Feature Store; previsões saem carimbadas
uv run python -m GarimpoInvestimentos.main --summary

# 3) BACKTEST (absorve CSV legado automaticamente; estratifica por Fonte; imprime DSR)
uv run python -m GarimpoInvestimentos.analyzers.backtest

# validações avulsas:
uv run python -m GarimpoInvestimentos.analyzers.equivalence --assets bitcoin,solana  # DPL vs direto
uv run python -m GarimpoInvestimentos.quality_snapshot                               # painel diário
```

O `quality_snapshot` também grava `GarimpoInvestimentos/h6_status.json` — **só quando o
estado da H6 muda**, para não gerar commit de ruído diário. Esse arquivo é a única via
pela qual o `n` da H6 sai da máquina de coleta: o `feature_store.db` que o produz é
gitignored. Commite-o quando ele mudar; é o que qualquer acompanhamento externo lê.

Em produção (Windows Task Scheduler), `run_sinal_diario.bat` e `run_garimpo_fase1.bat`
encapsulam esse fluxo — inclusive o `uv sync` com os três extras juntos, porque
sincronizar só `llm+excel` desinstalaria numpy/hmmlearn/ccxt e quebraria a família V3.

Jobs operacionais (lock, heartbeat, artefato esperado e `scientific_state` declarado):

```bash
uv run cripto-predictor-job phase1 | backtest | watchdog | v3-daily
                                   | observation-daily | observation-live | microstructure-live
```

Container (read-only, usuário não-root, sem capabilities):

```bash
docker build -t cripto-predictor . && docker run --rm --read-only --tmpfs /tmp --cap-drop ALL cripto-predictor
# ou: docker compose up
```

O histórico oficial é a tabela `predictions` de `output/feature_store.db`; o
`garimpo_historico.csv`, se existir, é absorvido uma vez (backfill `Fonte=direct`)
e fica congelado.

## Próximos passos

1. **Observação prospectiva** — acumular coleta diária (`--ingest --discover` + análise)
   até a H6 atingir `n >= 30` maduras e o gate pré-registrado poder rodar. O `n` real
   vive no `feature_store.db` de produção, não em ambiente de auditoria; a única via
   pela qual ele sai de lá é `GarimpoInvestimentos/h6_status.json`, gravado pelo
   `quality_snapshot` e **commitado à mão**.
   O critério diz "`n >= 30` antes de calcular veredito"; ele **não** diz "pare em 30".
   O poder do gate foi medido em 2026-08-21 (B12 em `docs/HYPOTHESES.md`): em `n=30`
   um efeito real de rho=0,2 é detectado em apenas **14,7%** das vezes, e o mesmo
   critério — sem nenhuma alteração — só fica bem dimensionado por volta de `n≈250`.
   Um "RUÍDO" em n=30 é ausência de evidência, não evidência de ausência.
2. Rodar `python -m scripts.freeze_h6_definition --check` antes de cada deploy enquanto
   a H6 estiver ativa — hash divergente é bloqueante até investigação humana.
3. **H7** — CPI/PPI ainda vazios em `macro_calendar.json` (fonte primária indisponível
   nas últimas sessões); `publish_lag_days=1` do `DXYProvider` não confirmado contra o
   release H.10 oficial do Fed; integração V3-vs-Fase1 a decidir. Nenhuma coleta começou.
4. **Pivot de pesquisa da V3** — o NO-GO líquido fecha a família funding/OI + HMM como
   formulada (`frozen_families`); hipótese nova exige trial nova e atestado de poder.
5. Camada `trading/` — gap remanescente: **sem venue real** (`ExchangeAdapter` só tem
   implementação simulada), o que é decisão humana adjacente a capital, não tarefa
   técnica. Os outros dois gaps fecharam em 2026-08-21: o adapter
   `SignalRecord`→`TradeIntent` existe (`trading/signal_adapter.py`, e RECUSA converter
   sinal de família congelada), e os modelos de custo ganharam ponto de entrada único
   (`trading/cost_policy.py`) — que ao ser implementado dissolveu a premissa do gap:
   `v3/costs.py` e `trading/microstructure.py` não são respostas concorrentes à mesma
   pergunta, são respostas a **instrumentos** diferentes (perp com funding × spot
   walk-the-book); fundi-los cobraria funding de spot. O dispatcher escolhe pelo
   instrumento e recusa que o modelo não calibrado sustente veredito científico.
6. Verificação externa da revogação das chaves antigas da SerpAPI (ver banner no topo).

Qualquer ativação real exige, sem exceção: atestado do harness
(`scripts/attest_harness.py`, expira em 7 dias), registro em `trials.json` com `metric`
declarado, e dado coletado **depois** do registro — nunca reaproveitando histórico já visto.

## Histórico e decisões

[HANDOFF-2026-08-14.md](HANDOFF-2026-08-14.md) (ensemble, H7, camada `trading/`) ·
[HANDOFF-2026-07-02.md](HANDOFF-2026-07-02.md) (linha do tempo da era DPL) ·
[HANDOFF.md](HANDOFF.md) (era pré-DPL) ·
[docs/CONFERENCIA_GERAL.md](docs/CONFERENCIA_GERAL.md) ·
[docs/RELATORIO_FINAL.md](docs/RELATORIO_FINAL.md) (fechamento canônico).

**Partida frio — leia primeiro:** [docs/OVERVIEW_E_ROADMAP_2026-08-21.md](docs/OVERVIEW_E_ROADMAP_2026-08-21.md)
reúne o estado do projeto e o roadmap da fase de coleta num documento só.

Panorama geral do estado atual — o que existe, o que falta e o que **não** falta:
[docs/PANORAMA_2026-08-21.md](docs/PANORAMA_2026-08-21.md).

Os documentos datados são **registros históricos** e não são reescritos: correções
entram como errata ou adendo, preservando o texto original. O índice consolidado do
que neles já não vale está em
[docs/ERRATA_2026-08-21.md](docs/ERRATA_2026-08-21.md).
