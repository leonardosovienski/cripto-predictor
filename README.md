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

Sistema de **pesquisa** em previsÃ£o de criptoativos, em duas camadas:

- **GarimpoInvestimentos** (previsÃ£o): descobre candidatos no mercado, analisa com
  LLM (Gemini/OpenAI) + indicadores tÃ©cnicos, grava previsÃµes carimbadas e valida
  com backtest estatÃ­stico (Spearman + IC95% + Deflated Sharpe).
- **DPL â€” Data Provider Layer** (`GarimpoInvestimentos/dpl/`): camada de dados
  bitemporal com fallback multi-fonte, agregaÃ§Ã£o por consenso, Circuit Breaker e
  **Feature Store** (SQLite) que Ã© o repositÃ³rio oficial de dados E de previsÃµes.

```
--discover (momentum+trending) â”€â”
--assets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â†’ INGESTÃƒO (DPL: Binanceâ†’CoinGecko | consenso c/ Kraken)
                                â””â†’ Feature Store (bitemporal, anti-lookahead)
                                        â†“ serving offline
                     ANÃLISE (LLM + indicadores + notÃ­cias) â†’ score 0-100
                                        â†“ carimbos: Juiz + Fonte
                     predictions (histÃ³rico oficial) â†’ BACKTEST (Spearman IC95% + DSR)
```

HÃ¡ ainda a **V3 quantitativa** (HMM de regimes + funding/OI + walk-forward com
custos), na branch `claude/v3-quant-wip`, em reconciliaÃ§Ã£o com esta linha â€” plano
em [docs/RECONCILIACAO_V3.md](docs/RECONCILIACAO_V3.md).

## Status do projeto (2026-07-20)

**Pesquisa. Nenhuma recomendaÃ§Ã£o de capital real.** Nota da auditoria: **5,5/10**
([docs/ARQUITETURA_CONSOLIDADA.md](docs/ARQUITETURA_CONSOLIDADA.md)). O walk-forward
da V3 com custos completos deu **NO-GO** (BTC e ETH) â€” e, pela primeira vez, Ã© um
NO-GO *confiÃ¡vel*: HMM auditado sem look-ahead, custos modelados, controle positivo
provando que o pipeline detecta edge quando ele existe, e DSR descontando as
tentativas registradas em `GarimpoInvestimentos/trials.json`.

## Funcionalidades

| Camada | O que faz |
|---|---|
| Discovery | Varre o top 100 (CoinGecko) + trending; filtra stablecoin/wrapped/volume<US$10M; ranqueia por momentum 7d/24h |
| Coleta (DPL) | Fallback Binanceâ†’CoinGecko ou consenso (mediana Binance+Kraken); Circuit Breaker; telemetria (`events.jsonl`) |
| Feature Store | OHLCV + sinais (Fear&Greed) alinhados por `published_at` (zero lookahead); features materializadas; tabela `predictions` |
| AnÃ¡lise | LLM (Gemini/OpenAI) sobre mercado offline + notÃ­cias live; carimbo do **Juiz** (provider:modelo:hash) e da **Fonte** (`direct`\|`dpl:fallback`\|`dpl:consensus`) |
| Backtest | Spearman(score, retorno D+1/7/30) com IC95% (block bootstrap pareado), estratificado por divergÃªncia e por Fonte; **DSR** contra o mÃ¡ximo-por-sorte das tentativas |
| GovernanÃ§a | Controle positivo (edge sintÃ©tico â†’ "validado"; ruÃ­do â†’ "RUÃDO"); `trials.json` versionado; migraÃ§Ãµes aditivas (ADR-017) |
| V3 (branch prÃ³pria) | GaussianHMM 3 estados com decodificaÃ§Ã£o **causal** (auditada), sinais de funding/OI, WFA com custos (taker+slippage+funding real) |

## Estrutura

```
GarimpoInvestimentos/
â”œâ”€â”€ main.py                â† CLI: --ingest, --discover N, --assets, --mode, --summary
â”œâ”€â”€ collectors/            â† discovery.py (candidatos) + coleta direta legada
â”œâ”€â”€ dpl/                   â† contratos, providers, routers, feature_store, migraÃ§Ãµes
â”œâ”€â”€ analyzers/             â† ai_insights (LLM), indicators, backtest, trials (DSR), equivalence
â”œâ”€â”€ core/                  â† paths, cache, history (store-first), logger
â”œâ”€â”€ output/reporter.py     â† exportaÃ§Ã£o CSV/XLSX
â””â”€â”€ trials.json            â† registro VERSIONADO de tentativas (denominador do DSR)
tests/                     â† 320 testes verdes (offline, sem chaves; 2 skips opcionais)
docs/                      â† ADRs e auditorias (ver HANDOFF)
```

predictor-core/predictor-ops nao sao vendorizados: sao wheels externas resolvidas
via [tool.uv.sources] a partir das GitHub Releases de core-predictor/tools-predictor,
com hash fixado em uv.lock.


O Feature Store ignorado pelo Git possui backup online verificavel e restore
nao destrutivo. Procedimento: [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

## InstalaÃ§Ã£o e configuraÃ§Ã£o

PrÃ©-requisitos: Python **3.13+** (suÃ­te validada em 3.13.14 e 3.14.6).

```powershell
# testes (offline, sem chaves â€” Python do sistema):
py -3.14 -m pytest tests/ -q          # 256 verdes no Python global (269 na .venv_v3, que tem hmmlearn)

# caminho AO VIVO: venv + chaves reais
py -3.13 -m venv GarimpoInvestimentos\env
GarimpoInvestimentos\env\Scripts\python.exe -m pip install -r GarimpoInvestimentos\requirements.txt
# cole GEMINI_API_KEY / OPENAI_API_KEY / SERP_API_KEY (>=16 chars) em GarimpoInvestimentos\.env
```
âš ï¸ Por design (fail-fast): `.env` sem chaves reais **crasha no segundo zero**.

## Como rodar

```powershell
$py = ".\GarimpoInvestimentos\env\Scripts\python.exe"
# 1) DESCOBERTA + INGESTÃƒO (rede): acha candidatos e materializa na Feature Store
& $py -m GarimpoInvestimentos.main --ingest --discover 10
#    ou lista fixa / consenso multi-exchange:
& $py -m GarimpoInvestimentos.main --ingest --assets bitcoin,ethereum --mode consensus
# 2) ANÃLISE (mercado offline; sÃ³ notÃ­cias/LLM tocam a rede)
#    sem --assets analisa tudo que estÃ¡ na Feature Store; previsÃµes saem carimbadas
& $py -m GarimpoInvestimentos.main --summary
# 3) BACKTEST (absorve CSV legado automaticamente; estratifica por Fonte; imprime DSR)
& $py -m GarimpoInvestimentos.analyzers.backtest
# validaÃ§Ãµes avulsas:
& $py -m GarimpoInvestimentos.analyzers.equivalence --assets bitcoin,solana   # DPL vs direto
```

O histÃ³rico oficial Ã© a tabela `predictions` de `output/feature_store.db`; o
`garimpo_historico.csv`, se existir, Ã© absorvido uma vez (backfill `Fonte=direct`)
e fica congelado.

## PrÃ³ximos passos

1. ReconciliaÃ§Ã£o V3 Ã— esta linha ([plano](docs/RECONCILIACAO_V3.md), aguarda aprovaÃ§Ã£o).
2. Acumular semanas de coleta diÃ¡ria (`--ingest --discover` + anÃ¡lise) atÃ© o backtest
   ter n para veredito com IC.
3. PÃ³s-reconciliaÃ§Ã£o: collectors V3 (funding/OI) viram providers da DPL (`SignalPoint`
   bitemporal, `published_at` no FIM da janela de 8h).
4. Pivot de pesquisa da V3 (o NO-GO lÃ­quido fecha a hipÃ³tese atual como formulada).

HistÃ³rico completo e decisÃµes: [HANDOFF-2026-07-02.md](HANDOFF-2026-07-02.md) Â·
era prÃ©-DPL: [HANDOFF.md](HANDOFF.md) Â· conferÃªncia: [docs/CONFERENCIA_GERAL.md](docs/CONFERENCIA_GERAL.md)

# cripto-predictor — modernização portátil

Instalação: `uv sync --locked --extra test`. Extras: `llm`, `v3`, `excel`, `science` e `test`. `predictor-core` e `predictor-ops` são pacotes instalados de wheels verificadas. Linux/container é o runtime principal; `DATA_DIR`, `OUTPUT_DIR` e `CACHE_DIR` são configuráveis. A modernização preserva juiz, partição de providers, features, thresholds, população, trials e estados de capital.
