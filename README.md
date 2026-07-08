# GarimpoInvestimentos + DPL

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

## Status do projeto (2026-07-02)

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
tests/                     ← 229 testes (offline, sem chaves)
docs/                      ← ADRs e auditorias (ver HANDOFF)
vendor/predictor_core/     ← núcleo estatístico vendorizado (NÃO editar local)
```

## Instalação e configuração

Pré-requisitos: Python **3.13+** (suíte validada em 3.13.14 e 3.14.6).

```powershell
# testes (offline, sem chaves — Python do sistema):
py -3.14 -m pytest tests/ -q          # 229 verdes

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
