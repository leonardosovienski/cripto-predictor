# GarimpoInvestimentos + DPL

> ## ATENÇÃO — incidente de segurança aberto (ver HANDOFF.md / ECOSYSTEM_HANDOFF.md)
>
> Uma credencial (SerpAPI) foi encontrada em texto claro em 5 logs históricos de
> `logs/garimpo_fase1_*.log`. Estado: `BLOCKED_PENDING_SECRET_ROTATION` — a
> causa (o wrapper de execução preservava stdout/stderr do processo filho sem
> redação) já foi corrigida e verificada (`predictor_ops.redaction`); falta
> apenas a rotação/revogação humana da chave no provedor e a decisão sobre os
> logs históricos, ambas de baixa prioridade por decisão explícita do usuário.
> Ver `SECURITY_INCIDENT_SECRET_ROTATION.md` na raiz do workspace para o
> estado atual e o escopo completo.

Sistema de **pesquisa** em previsão de criptoativos, em duas camadas:

- **GarimpoInvestimentos** (previsão): descobre candidatos no mercado, analisa com
  LLM (Gemini/OpenAI) + indicadores técnicos, grava previsões carimbadas e valida
  com backtest estatístico (Spearman + IC95% + Deflated Sharpe).
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

Há ainda a **V3 quantitativa** (HMM de regimes + funding/OI + walk-forward com
custos), na branch `claude/v3-quant-wip`, em reconciliação com esta linha — plano
em [docs/RECONCILIACAO_V3.md](docs/RECONCILIACAO_V3.md).

## Status do projeto (2026-07-20)

**Pesquisa. Nenhuma recomendação de capital real.** Nota da auditoria: **5,5/10**
([docs/ARQUITETURA_CONSOLIDADA.md](docs/ARQUITETURA_CONSOLIDADA.md)). O walk-forward
da V3 com custos completos deu **NO-GO** (BTC e ETH) — e, pela primeira vez, é um
NO-GO *confiável*: HMM auditado sem look-ahead, custos modelados, controle positivo
provando que o pipeline detecta edge quando ele existe, e DSR descontando as
tentativas registradas em `GarimpoInvestimentos/trials.json`.

## Funcionalidades

| Camada | O que faz |
|---|---|
| Discovery | Varre o top 100 (CoinGecko) + trending; filtra stablecoin/wrapped/volume<US$10M; ranqueia por momentum 7d/24h |
| Coleta (DPL) | Fallback Binance→CoinGecko ou consenso (mediana Binance+Kraken); Circuit Breaker; telemetria (`events.jsonl`) |
| Feature Store | OHLCV + sinais (Fear&Greed) alinhados por `published_at` (zero lookahead); features materializadas; tabela `predictions` |
| Análise | LLM (Gemini/OpenAI) sobre mercado offline + notícias live; carimbo do **Juiz** (provider:modelo:hash) e da **Fonte** (`direct`\|`dpl:fallback`\|`dpl:consensus`) |
| Backtest | Spearman(score, retorno D+1/7/30) com IC95% (block bootstrap pareado), estratificado por divergência e por Fonte; **DSR** contra o máximo-por-sorte das tentativas |
| Governança | Controle positivo (edge sintético → "validado"; ruído → "RUÍDO"); `trials.json` versionado; migrações aditivas (ADR-017) |
| V3 (branch própria) | GaussianHMM 3 estados com decodificação **causal** (auditada), sinais de funding/OI, WFA com custos (taker+slippage+funding real) |

## Estrutura

```
GarimpoInvestimentos/
├── main.py                ← CLI: --ingest, --discover N, --assets, --mode, --summary
├── collectors/            ← discovery.py (candidatos) + coleta direta legada
├── dpl/                   ← contratos, providers, routers, feature_store, migrações
├── analyzers/             ← ai_insights (LLM), indicators, backtest, trials (DSR), equivalence
├── core/                  ← paths, cache, history (store-first), logger
├── output/reporter.py     ← exportação CSV/XLSX
└── trials.json            ← registro VERSIONADO de tentativas (denominador do DSR)
tests/                     ← 350 testes verdes (offline, sem chaves; 2 skips opcionais)
docs/                      ← ADRs e auditorias (ver HANDOFF)
```

predictor-core/predictor-ops nao sao vendorizados: sao wheels externas resolvidas
via [tool.uv.sources] a partir das GitHub Releases de core-predictor/tools-predictor,
com hash fixado em uv.lock.

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


O Feature Store ignorado pelo Git possui backup online verificavel e restore
nao destrutivo. Procedimento: [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

## Instalação e configuração

Pré-requisitos: Python **3.13+** (suíte validada em 3.13.14 e 3.14.6).

```powershell
# testes (offline, sem chaves — Python do sistema):
py -3.14 -m pytest tests/ -q          # 350 verdes, 2 skips (suíte completa, verificada em CI)

# caminho AO VIVO: venv + chaves reais
py -3.13 -m venv GarimpoInvestimentos\env
GarimpoInvestimentos\env\Scripts\python.exe -m pip install -r GarimpoInvestimentos\requirements.txt
# cole GEMINI_API_KEY / OPENAI_API_KEY / SERP_API_KEY (>=16 chars) em GarimpoInvestimentos\.env
```
⚠️ Por design (fail-fast): `.env` sem chaves reais **crasha no segundo zero**.

## Como rodar

```powershell
$py = ".\GarimpoInvestimentos\env\Scripts\python.exe"
# 1) DESCOBERTA + INGESTÃO (rede): acha candidatos e materializa na Feature Store
& $py -m GarimpoInvestimentos.main --ingest --discover 10
#    ou lista fixa / consenso multi-exchange:
& $py -m GarimpoInvestimentos.main --ingest --assets bitcoin,ethereum --mode consensus
# 2) ANÁLISE (mercado offline; só notícias/LLM tocam a rede)
#    sem --assets analisa tudo que está na Feature Store; previsões saem carimbadas
& $py -m GarimpoInvestimentos.main --summary
# 3) BACKTEST (absorve CSV legado automaticamente; estratifica por Fonte; imprime DSR)
& $py -m GarimpoInvestimentos.analyzers.backtest
# validações avulsas:
& $py -m GarimpoInvestimentos.analyzers.equivalence --assets bitcoin,solana   # DPL vs direto
```

O histórico oficial é a tabela `predictions` de `output/feature_store.db`; o
`garimpo_historico.csv`, se existir, é absorvido uma vez (backfill `Fonte=direct`)
e fica congelado.

## Próximos passos

1. Reconciliação V3 × esta linha ([plano](docs/RECONCILIACAO_V3.md), aguarda aprovação).
2. Acumular semanas de coleta diária (`--ingest --discover` + análise) até o backtest
   ter n para veredito com IC.
3. Pós-reconciliação: collectors V3 (funding/OI) viram providers da DPL (`SignalPoint`
   bitemporal, `published_at` no FIM da janela de 8h).
4. Pivot de pesquisa da V3 (o NO-GO líquido fecha a hipótese atual como formulada).

Histórico completo e decisões: [HANDOFF-2026-07-02.md](HANDOFF-2026-07-02.md) ·
era pré-DPL: [HANDOFF.md](HANDOFF.md) · conferência: [docs/CONFERENCIA_GERAL.md](docs/CONFERENCIA_GERAL.md)

# cripto-predictor — modernização portátil

Instalação: `uv sync --locked --extra test`. Extras: `llm`, `v3`, `excel`, `science` e `test`. `predictor-core` e `predictor-ops` são pacotes instalados de wheels verificadas. Linux/container é o runtime principal; `DATA_DIR`, `OUTPUT_DIR` e `CACHE_DIR` são configuráveis. A modernização preserva juiz, partição de providers, features, thresholds, população, trials e estados de capital.
