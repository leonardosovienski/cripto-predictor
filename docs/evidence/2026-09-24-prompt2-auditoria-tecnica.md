# 2026-09-24 — Prompt 2: auditoria técnica antes de alterações (cripto-predictor / GarimpoInvestimentos)

Modo: **somente leitura**. O único código executado foi a suíte de testes, isolada de rede e de segredos (item 8). Repositório `leonardosovienski/cripto-predictor`, HEAD `174573d` (= `origin/main`, buscado em 2026-09-24 ~14:05 UTC; árvore idêntica ao commit qualificado `341d270`). Nenhum arquivo do repositório foi alterado.

Classificação: **PROVEN** = constatado nesta sessão (código lido, comando rodado, git). **DECLARED** = só em doc ou comentário. **UNKNOWN** = indeterminado. A leitura de código foi dividida entre esta sessão e 3 agentes de exploração somente leitura. As afirmações que sustentam conclusões foram reconferidas aqui: WFA `backtest_v3.py:115-130,1070-1078`, bruto em `analyzers/backtest.py:906-913`, PBO sem chamador, `trials.json` (26/16/0 `superseded`/0 `sharpe_basis`), `ef6192c`, `pipeline.py:323-358`, rótulo da H6 com `pred_price`, OI `oi_collector.py:18×65`, Vision `mark_price=0.0`.

## Pré-condição

- `docs/evidence/secret-rotation-attestation.md`: **não existe**. Foi procurada em todos os repositórios do stack no GitHub, no WSL e nos discos C:, D:, E: e F: (relatório do Prompt 1).
- **Dispensada pelo dono** em 2026-09-24, nesta sessão (resposta "sim" à pergunta sobre dispensar a atestação e seguir). Registro: `SECRET_ROTATION_GATE = WAIVED_BY_OWNER`, **não** `CLEARED`.
- A comparação de cobertura com o Prompt 1 fica N/A, porque não há atestação para comparar. Ficam sem registro de rotação 7 classes de credencial (`OPENAI`, `OPENROUTER`, `NEWSAPIAI`, `MEDIASTACK`, `CRYPTOPANIC`, `COINGECKO`, `ALERTA_WEBHOOK_URL`), e a revogação das 5 antigas não foi verificada.
- Consequência operacional mantida: **nenhuma execução com credenciais nem acesso externo**. A suíte rodou sem rede e sem ambiente.

## 1. Resumo executivo factual

1. **Suíte isolada** (sem rede, ambiente vazio): **1664 passed, 0 failed, 0 skipped**, 211 s, cobertura 74%. Nenhum teste tentou rede nem `.env` (PROVEN). O "~615 testes" do contexto está desatualizado.
2. **Hipóteses:** H1, H2, H3 e H5 = `CLOSED_NO_GO`; H4, H6 e H9 = `CLOSED_INSUFFICIENT_SAMPLE`; H7 e H8 = `REGISTERED_NOT_ACTIVATED` (`charters/scientific_state.json`, PROVEN). H6 é uma relação Spearman (score invertido × retorno D+7), não uma estratégia. Seu estado persistido: n=84, ρ=−0,057, IC [−0,231; 0,129] (`GarimpoInvestimentos/h6_status.json`).
3. **Caminhos de avaliação:** há 5 separados. O único com walk-forward purgado e custos é o WFA do V3 (H1–H3). O caminho do juiz LLM (H4/H5) e o da H6 são **só brutos**, inclusive o Sharpe gravado no ledger.
4. **Vazamento:** nenhum vazamento clássico provado no WFA do V3 (purga 7d ≥ 7× o horizonte de 24h; HMM e scaler ajustados só no IS). Há riscos concretos em quatro pontos:
   - o rótulo legado da H6 parte de `pred_price`;
   - a semântica do timestamp do OI é ambígua;
   - seleções (grade e Kelly) são feitas sobre todos os folds OOS;
   - o H8 é avaliado in-sample.
5. **Tentativas:** `N_trials_observed = 23` (H1–H6); `N_trials_total_known = LOWER_BOUND(32)`; `N_upper ≈ 42`.
6. **Integridade do ledger:** o `trials.json` foi reescrito em hipóteses fechadas (`ef6192c`), não tem `sharpe_basis` em nenhuma entrada (o DSR é **não computável** pela regra do próprio projeto) e o git não é o ledger completo.
7. **Baselines:** não há naive, random walk nem seasonal-naive em lugar nenhum. O WFA do V3 não tem baseline. Só o `profit_recovery_v1` compara com baselines no mesmo protocolo.
8. **`predictor_core` 3.2.1:** **não tem** `RunManifest`, `TrialLedger`, `Evaluator`, `DecisionPolicy` nem arquivo de política. Tem `TrialRegistryV2`, DSR, PSR, bootstrap e `JsonlStore` append-only.
9. **Conflito com a qualificação:** `trials.json`, `scientific_state.json`, `HYPOTHESES.md`, `EVIDENCE_REGISTRY.md`, `h6_status.json`, `analyzers/pbo.py` e `cripto_v12_dsr_inventory.json` estão no **conjunto protegido** da qualificação Etapa A (P0 se alterados). E o `cripto-predictor` qualificado (`341d270`) só pode mudar nos `adapter_paths` (C24.3).
10. **Dados:** os dados horários do V3 e o banco de previsões do LLM **não estão versionados nem existem no PC 2** (`data/` no `.gitignore:11`). O único dataset local com hash é o da D-16 (BTCUSDT diário + funding, set/2025–set/2026).

## 2. Mapa do pipeline

### A. V3 HMM funding/OI: H1 (fr90), H2 (fr21), H3 (h48); H7/H9 por flag

| etapa | achado | evidência | cl. |
|---|---|---|---|
| dados | REST Binance: funding (`/fapi/v1/fundingRate`), OI (`/futures/data/openInterestHist`, período 1h, só ~30 dias), spot klines 1h. Histórico via data.binance.vision: funding mensal, klines 1h, OI de `daily/metrics` 5 min | `v3/collectors/funding_collector.py:39-40`; `oi_collector.py:49-53`; `spot_collector.py:38-40`; `binance_vision.py:30,155,191,217-229`; `v3/vision_ingest.py:47-61` | P |
| armazenamento | `data/v3/<SYM>/{funding,oi,spot_binance_1h}.csv` (fora do git) | `v3/pipeline.py:90-99`; `.gitignore:11` | P |
| período | CLI `--start-date`; o WFA usa o CSV inteiro. Veredito "2021→jul/2026" | `pipeline.py:420-423`; `backtest_v3.py:623-642`; `docs/HYPOTHESES.md:34-35` | P / D |
| granularidade | grade de 8h (cadência de funding) | `v3/feature_builder.py:239-256` | P |
| features | `funding_zscore` (90 ou 21), `oi_log_delta`, `leverage_pressure`, `log_return_8h`, `realized_vol_24h`; tudo as-of, spot em t−1h | `feature_builder.py:60-61,257-311,283-285` | P |
| target | log(close t+h / close t), h=24 (H3: 48) | `backtest_v3.py:125,228-257` | P |
| modelo | GaussianHMM, 3 estados, cov full, n_iter 300, seeds 42..46, StandardScaler, forward filtering causal | `v3/regime_engine.py:45-64,327-355,389-397` | P |
| sinal | SHORT se z≥2, ΔOI>0 e regime bull/sideways; LONG se z≤−2, ΔOI>0 e regime bear/sideways; conf ≥0,60; strength=min(\|z\|/4,1)·P | `v3/signal_engine.py:59-62,222-259` | P |
| posição / execução | direção × strength × kelly (1,0); spot como proxy do perp; saída no close; SL/TP desligados | `backtest_v3.py:134-135,209-211,267-304,519,878,883-892` | P |
| custos | fee 10 + slip 5 bps/perna; funding **realizado** por mark price (§5) | `v3/costs.py:39-56`; `backtest_v3.py:123-124,322-342,896-910` | P |
| validação | WFA: IS 180d / purga 7d / OOS 30d / passo 30d; HMM e scaler só no IS; sem embargo | `backtest_v3.py:115-118,739-796` | P |
| métricas | Spearman + IC (block bootstrap), PSR (benchmark padrão do core), MaxDD, Sharpe, Sortino, Calmar, bruto vs líquido | `backtest_v3.py:934-949,1008-1045` | P |
| veredito | GO = PSR≥0,80 e IC_lo>0 e MaxDD<20%. Mas `final_verdict="UNVALIDATED"` fixo; GO/NO-GO só em `diagnostic_verdict` | `backtest_v3.py:129-130,1074-1077` | P |
| persistência | `data/v3/<SYM>/research_runs/<run_id>/returns.json` (`wfa-descriptive/2`) | `backtest_v3.py:1092-1123` | P |
| registro | `run_wfa` **não registra**; só `run_kelly_sweep` e `run_threshold_grid` registram (antes do resultado), e ambos estão bloqueados pela família congelada | `backtest_v3.py:1187-1191,1239-1262,1389-1427,1695-1713` | P |

Fluxo: CSV Binance → FeatureVector 8h → target log-ret 24h → HMM (IS) + regra z-score → posição dir×strength×kelly → fee/slip/funding → P&L líquido → WFA purgado + PSR/IC/MaxDD → JSON do run. **Lacuna:** nenhum baseline.

### B. Juiz LLM, "phase1"/DPL (H4, H5)

| etapa | achado | evidência | cl. |
|---|---|---|---|
| dados | preço DPL (fallback binance→coingecko), candles 1d (200), Fear&Greed, notícias (SerpAPI por padrão) | `dpl/sources.json`; `phase1.py:63,147-173`; `collectors/news.py:35-210` | P |
| universo | símbolos da store ou `DEFAULT_ASSETS` = bitcoin, ethereum, solana | `phase1.py:322`; `config.py:53` | P |
| features | preço, variações 24h/7d/30d, RSI14, SMA50/200, MACD, Bollinger | `dpl/feature_engineering.py:20-90` | P |
| modelo | juiz LLM por ativo (gemini/groq/cerebras/mistral), partição por sha256, temperature 0,2 | `analyzers/ai_insights.py:81-125,245,264` | P |
| sinal | `opportunity_score` 0–100 | `analyzers/score_engine.py:4-18` | P |
| persistência | tabela `predictions` na Feature Store SQLite (append-only com arquivo e hash chain) | `dpl/migrations/_0006…:16`, `_0016…:38`, `_0019…:5,15` | P |
| target | `var_d{h}_pct`, h ∈ {1,7,30}; legado parte de `pred_price`; contrato novo `future-daily-close-v1` | `analyzers/backtest.py:42-43,81-114,193-247` | P |
| posição / custos | não há posição (estratégia fictícia score≥60); **sem custos** (`GROSS_RETURNS_ONLY`) | `backtest.py:906-913,926-941` | P |
| validação / métricas | sem treino/teste (coleta prospectiva); Spearman + block bootstrap; Sharpe e DSR **brutos** | `backtest.py:55-71,398,917-969` | P |
| registro | `close_trial_sharpes` grava no `trials.json` o Sharpe **bruto** por trade | `backtest.py:573-656` | P |
| divergência | doc pede "Sharpe **líquido** + DSR"; o código usa bruto | `docs/HYPOTHESES.md:70,123` × `backtest.py:626-640,909` | D≠P |

### C. H6, Spearman do score invertido (não é estratégia)

Pares (100−score, var_d7) só com `fonte=="dpl:fallback"` e `pred_date > registered_at` (anti-snooping); n≥30; `spearman_block_ci` com bloco 7. Veredito VALIDADO / REFUTADO_DIRECAO_OPOSTA / INCONCLUSIVO; `economic_verdict=NOT_EVALUATED` (`analyzers/backtest.py:659-893`, P). Sharpe auxiliar (score≤40) gravado no ledger (`:729-790`). Só roda sobre linhas do contrato legado (`:265-268`).

### D. `profit_recovery_v1`

- **Dados:** SQLite `raw_market_data` 1d (somente leitura).
- **Detector:** "PR122" com features técnicas.
- **Alvo:** 3d.
- **Modelo:** média expansiva por classe.
- **Custos:** 35 bps no cenário base, com cenários de 10, 35, 70 e 105 bps.
- **Validação:** split cronológico 60/20/20, com a parte `reserved_final` não avaliada.
- **Baselines:** comparados no mesmo protocolo.
- **Decisão:** a regra `WATCH` (se n<20 **ou** custo ASSUMED) impede qualquer TRADE.

Evidência: `profit_recovery_v1.py:110-153,224-290,412-488,602-627,756-965,1236-1254` (P).

### E. `research_worker` (sonda de qualificação, não é hipótese)

- **Dados:** JSON materializado por hash.
- **Checagem temporal:** `replay` do core (`LookaheadError`).
- **Sinal:** fixo long, ou aleatório como placebo.
- **Custos:** `CostModel` do V3.
- **Estado científico:** vem do IC **bruto**.
- **Estado econômico:** vem do IC líquido.

Evidência: `research_worker.py:50,120-153,254-296` (P).

### F. H8 e scripts avulsos

- **H8:** Spearman do fator proposto pelo LLM na amostra inteira, sem custos nem split (`analyzers/hypothesis_loop_runner.py:64,84-117`; `hypothesis_loop.py:217-245`, P).
- **Scripts de carry/basis/altcoin:** têm custos próprios (`scripts/backtest_altcoin_payoff.py:161-166`, `backtest_absolute_carry.py:176-177`, `backtest_btc_basis.py:150-153`). Protocolo não mapeado em detalhe (U).

## 3. Inventário de tentativas (H1–H6)

| H | trials registradas (`GarimpoInvestimentos/trials.json`) | status | o que variou | variantes documentadas e **não** registradas | evidência |
|---|---|---|---|---|---|
| H1 | `v3-hmm-funding-oi-fr90` + 16 `v3-grid-btcusdt-fr{1.5,2,2.5,3}-conf{0.55,0.6,0.65,0.7}` | CLOSED_NO_GO | base: HMM 3 estados, z(90), 24h, custos; grade 4×4 de thresholds | fr90 pré-custos (1); Kelly BTC 0,5/0,25/0,10 (3); Kelly ETH (4) | `27281bd`, `495eaf3`, `b5440ac`, `af51758`; `HANDOFF_HISTORICO_ATE_20260917.md:729-739,816-827,1081` (D) |
| H2 | `v3-hmm-funding-oi-fr21` (`sharpe: null`) | CLOSED_NO_GO | janela 21 | fr21 pré-custos (1) | `27281bd`, `6d9fc85`; `HANDOFF_HISTORICO:1082` (D) |
| H3 | `v3-hmm-funding-oi-fr90-h48` | CLOSED_NO_GO | horizonte 48h | — | `6d9fc85` |
| H4 | `v2-dpl-gemini-h7` + ancestral `v1-direct-gemini-h7` | CLOSED_INSUFFICIENT_SAMPLE | fonte DPL; juiz Gemini; D+7 | revisões pré-protocolo sem métrica própria: UNKNOWN | `ab346d3`, `da71160` |
| H5 | `v2-dpl-multi-h7` | CLOSED_NO_GO | juiz multi-provedor | — (estratos não são trials) | `da71160`, `39d13a5`, `ef6192c` |
| H6 | `h6-sinal-invertido-d7` | CLOSED_INSUFFICIENT_SAMPLE | score invertido, D+7 | origem por data-snooping declarado; o refreeze do veredito é reparo | `883a6af`, `556f5ad`, `aefa405`, `ef6192c`; `docs/HYPOTHESES.md:229-234`; `docs/H6_REFREEZE_2026-08-27.md:11-13` |

- **`N_trials_observed = 23`** (PROVEN). São as entradas da linhagem H1–H6 no HEAD: 6 do charter, a ancestral e as 16 da grade. O arquivo inteiro tem 26 entradas e 23 Sharpes finitos. Uma ressalva: `v3-grid-btcusdt-fr2-conf0.6` usa os mesmos thresholds de H1 e pode ser quase-repetição (sem ela, 22).
- **`N_trials_total_known = LOWER_BOUND(32)`**: 23 + 9 configurações distintas documentadas e não registradas (acima).
  - Regra de contagem: params diferentes = N+1 (`core-predictor@v3.2.1: measurement/trials.py:401-407`; `backtest_v3.py:1221-1245`).
  - Repetições não contam: os 9 meses, a replicação de 09/07 e o `psr_nonoverlap`.
- **Por que é só limite inferior** (PROVEN):
  - `run_wfa` não registra (`backtest_v3.py:1695-1713`);
  - `run_kelly_sweep` só passou a registrar em `9d89871`;
  - `run_threshold_grid` rodou sem registrar entre `dfaccf1` e `af51758`;
  - o V3 foi desenvolvido fora do git até `3507809`;
  - os jobs de produção gravam o `trials.json` sem commitar: a grade foi registrada em produção em 04/09 e só entrou no git em 05/09 (`b5440ac`), e há commits de produção não publicados (`1804213`, `baad153`, `62cc323`, `75cea8c`).
- **`N_upper ≈ 42`** (plausível, não é teto rígido): +9 de uma grade SL×TP 3×3 (`docs/RISK_MGMT_E_CALIBRACAO_2026-08-27.md:62-64`), com indício de execução (`docs/MAQUINA_DE_PRODUCAO.md:279` cita o commit `1804213`, que não está no repo), e +1 se H1-ETH contar à parte. A busca de junho, anterior ao git, é UNKNOWN.
- **Append-only:**
  - O core recusa remoção e mutação de `params` e `metric` (`core@v3.2.1:trials.py:565-585,603-612`). O wrapper local proíbe reescrever trial de hipótese fechada e criar trial em família congelada (`analyzers/trials.py:102-164`).
  - **No histórico:** nenhuma entrada foi removida (a lista de nomes só cresce: 2→…→26, PROVEN). **Mas** o `sharpe` foi sobrescrito ~15 vezes; `ef6192c` editou à mão os Sharpes de H5 (−0,312→−0,4186) e de H6 (0,3479→0,4766) em hipóteses fechadas, por fora do guard; `notes` foi reescrito (`495eaf3`, `6d9fc85`, `aefa405`, `8af1e4f`); o HEAD tem 0 campos `superseded` (PROVEN).
  - **A grade rodou numa família já congelada:** `frozen_families` existe desde `aefa405` (17/08) e a grade rodou em 04/09. As 16 entradas não declaram `family`.
- **DSR:** nenhuma das 26 entradas tem `sharpe_basis`. Pela regra do próprio projeto (`analyzers/trials.py:45-52`), o DSR desse ledger é **não computável** (PROVEN). O inventário `docs/evidence/cripto_v12_dsr_inventory.json` já registra `diagnostic_valid_for_inference: false` (D).

## 4. Auditoria de vazamento

| severidade | problema | evidência | impacto provável |
|---|---|---|---|
| ALTO: RISK | Rótulo legado (H6 e avaliação LLM) parte de `pred_price`, o preço gravado na previsão, que pode ter até 26h, e não do próximo fechamento após a decisão | `analyzers/backtest.py:231-247` (conferido: `(price - pred_price)/pred_price`); o contrato novo admite o problema (`:194-199`); `dpl/snapshots.py:88-91`; o veredito da H6 usa só linhas legadas (`:265-272`) | O rótulo pode incluir movimento já observável na decisão. Mistura correlação contemporânea no Spearman da H6, em direção desconhecida (a H6 já está encerrada) |
| MÉDIO: vazamento contido | `pipeline.py` ajusta HMM e scaler na **série inteira** e infere nela mesma | `v3/pipeline.py:323-358` (conferido: "Descriptive in-sample fit"); saída `signals.replay.v3_2.jsonl` marcada `DESCRIPTIVE_REPLAY` | Qualquer métrica tirada desse arquivo é in-sample. O paper trader usa só o último sinal (OK) |
| MÉDIO: RISK | Timestamp do OI ambíguo: o cabeçalho diz "instante da observação", o campo diz "início do período" (1h); a junção inclui ts == decisão | `v3/collectors/oi_collector.py:18` × `:65` (conferido); `feature_builder.py:261`; `binance_vision.py:90` (`historical_availability_verified: False`) | Se o valor for o fim do período, `oi_log_delta` usa até 1h de futuro, e ΔOI>0 é condição do sinal |
| MÉDIO: RISK | O WFA lê CSVs e trata tempo do evento como tempo de conhecimento; não usa a store bitemporal | `backtest_v3.py:623-625`; `dpl/derivatives.py:50-101` (`publication_history_unverified`) | O point-in-time depende de premissa não certificada |
| MÉDIO: RISK | Grade de thresholds e sweep de Kelly escolhem o melhor pelo agregado de **todos** os folds OOS | `backtest_v3.py:1281-1289,1453-1466`; mitigado por pré-registro e `UNVALIDATED` | O OOS da escolhida deixa de ser OOS (snooping). Só serve como hipótese nova |
| MÉDIO: RISK | H8: fatores propostos pelo LLM avaliados na história inteira | `hypothesis_loop_runner.py:169-186`; `hypothesis_loop.py:217-244` | In-sample; o LLM tem prioris do mesmo período |
| BAIXO: RISK | Execução com latência zero no mesmo close usado como feature | `backtest_v3.py:287,893`; `feature_builder.py:283` | Não é look-ahead, mas o fill é otimista |
| BAIXO: RISK | Trades descartados quando faltam dados futuros (preço no horizonte, funding) | `backtest_v3.py:338-339,858-860,891-904` | Seleção condicionada ao futuro |
| BAIXO: RISK | Horizonte e fuso no caminho legado (CoinGecko por data; BRT sem fuso antes de 07/07) | `analyzers/backtest.py:81-89,140`; `core/history.py:27-30` | Horizonte ±1 dia; não afeta a H6 (registrada em 20/07) |
| BAIXO: RISK | Bloco do bootstrap da H6 = 7 observações com vários ativos por dia (embargo efetivo subdimensionado) | `analyzers/backtest.py:52-71,855`; `dpl/feature_store.py:735` | IC estreito demais |
| BAIXO: RISK | PBO/CSCV sem purga nem embargo entre blocos | `analyzers/pbo.py:134-137` | PBO subestimado com rótulos sobrepostos (hoje sem uso em produção) |
| BAIXO: RISK | `research_worker` não verifica maturidade do rótulo; o gate usa média de funding da amostra inteira | `research_worker.py:124-129,284-291` | Dataset mal declarado passa |
| BAIXO: RISK | Candles não bitemporais (o upsert sobrescreve `close`); `features_aligned` carrega o close do candle no `ts` de abertura | `dpl/ingest.py:181-182`; `dpl/feature_store.py:192-199`; `dpl/alignment.py:94-103` | Consumidor futuro que trate `ts` como decisão recebe o close antes |
| BAIXO: RISK | Sobrevivência: universo atual (top-100 hoje; BTC/ETH/SOL) | `config.py:53`; `collectors/discovery.py:144-150`; `research/universe.py` (`historical_universe_certified: False`) | Afeta backtests históricos multiativo |
| BAIXO: RISK | Notícias sem `published_at` por artigo | `collectors/news.py:49-54,168-180` | Idade da notícia não é auditável em replay |
| OK | Split temporal | folds IS→purga→OOS disjuntos (`backtest_v3.py:739-796`) | — |
| OK | Purga vs horizonte | purga 7d = 168h contra horizonte de 24h (`:117,125`); calibração exige `ts+H ≤ is_end` (`:822`) | — |
| OK | HMM e scaler | só no IS (`:774-779`); forward causal (`regime_engine.py:213-252`) | — |
| OK | Indicadores disponíveis no timestamp | só candles fechados (`feature_builder.py:283-302`); DXY com `published_at` (`v3/macro_features.py:45-114`) | — |
| OK | Custos | gate calibrado no IS; funding de t (`economic_gate.py:102-103`; `backtest_v3.py:864-872`) | — |

Purga e embargo reais: WFA do V3 com purga de 7d contra rótulo de 24h, sem embargo (não precisa, é só para frente); LLM e H6 sem split, bloco 7; H8 bloco 21; PBO com purga 0 e embargo 0; `research/validation.walk_forward` com `gap` padrão 0.

Guardas existentes, com testes: `SortedTimeIndex.as_of` (`v3/timeindex.py:49-63`; `tests/test_v3_feature_prefix_regression.py`); HMM causal (`tests/test_v3_hmm_no_lookahead.py`, com skip se faltar `hmmlearn`); fatiamento real do WFA (`tests/test_v3_wfa_actual_slicing.py`, enquanto `test_v3_wfa_purge_contract.py` só replica a aritmética); `FeatureStore._check_temporal`; AlignmentEngine; vintages; `close_on(published_as_of)`; `LookaheadError` via replay (`tests/conformance/*`); causalidade da DSL; `walk_forward` com purga; anti-snooping da H6 (`tests/test_h6_spearman_verdict_eligibility.py`); macro e DXY; ledger causal do profit_recovery; pré-registro com família congelada (`tests/test_threshold_grid_registry.py`); PBO e placebo testados, mas sem purga e sem ligação ao pipeline.

**Achado operacional (fora de vazamento):** o funding do Vision grava `mark_price=0.0` (`binance_vision.py:168`), e `_realized_funding_pnl` devolve `None` quando `mark_price <= 0` (`backtest_v3.py:336-339`). Conferido. Com isso, um WFA alimentado só pelo Vision descarta todos os trades.

## 5. Auditoria de custos

| caminho | componentes (padrão) | antes da métrica líquida? | evidência |
|---|---|---|---|
| WFA V3 | taker 10 + slippage 5 bps por perna; fricção (1+exit)·(fee+slip)·\|pos\|; funding **realizado** por mark price; spread não separado | **sim** (PSR, Sharpe, MaxDD, Sortino e Calmar sobre P&L líquido; o IC de Spearman é bruto por desenho) | `v3/costs.py:39-56`; `backtest_v3.py:123-124,322-342,905-913` |
| gate econômico V3 e worker | funding constante na abertura × janelas | sim | `v3/costs.py:58-84`; `v3/economic_gate.py:106,117` |
| `pipeline.py`, `paper_report` | nenhum | **só bruto** | `pipeline.py:357-366`; `paper_report.py:92-157` |
| juiz LLM (H4/H5) | nenhum | **só bruto** (Sharpe e DSR do ledger) | `analyzers/backtest.py:906-913,933-961` |
| H6 e H8 | nenhum | **só bruto** | `backtest.py:887-893`; `hypothesis_loop.py:217-245` |
| `profit_recovery_v1` | 2·fee + spread + slip + latência + funding + borrow + infra = 35 bps base; cenários 10/35/70/105; funding e borrow = 0 até no short | sim (o bruto também é reportado) | `profit_recovery_v1.py:110-153,869,1236-1254,1475-1485` |
| `research_worker` | `CostModel` do V3 | sim para o estado econômico; **o científico usa o bruto** | `research_worker.py:254-296` |
| trading (spot) | VWAP walk-the-book + fee + latência | sim | `trading/costs.py:28-90` |
| política de custo | `CALIBRATED_FOR_VERDICT = frozenset()`: nenhum modelo de custo tem grau de veredito | — | `trading/cost_policy.py:17,28-50` |

A origem do fee de 10 bps não está documentada (`v3/costs.py:6-16`, D). A docstring do `backtest_v3` está desatualizada (`:24-26`).

## 6. Baselines

| baseline | onde | avaliado no mesmo período e protocolo? |
|---|---|---|
| naive / random walk | **não existe** | — (PROVEN, ausência) |
| seasonal-naive | **não existe** | — |
| buy-and-hold (LLM) | `analyzers/backtest.py:966-969` (média de var_dH do BTC) | parcial: mesmo horizonte, mas só BTC contra estratégia multiativo; bruto; sem teste |
| buy-and-hold (profit_recovery) | `profit_recovery_v1.py:763,782,832` (long em cada evento) | sim, mas é condicional a evento, não B&H contínuo |
| flat / no-trade | `profit_recovery_v1.py:762,781`; `research_worker.py:372-381` (constante 0/0 bps) | sim no profit_recovery (mas excluído do "melhor baseline", `:931`); no worker é constante, não computada |
| regras simples (momentum, mean-reversion, breakout, MA) | `profit_recovery_v1.py:783-796` | sim |
| **WFA V3 (H1–H3)** | **nenhum**; o PSR usa `benchmark_sharpe` padrão do core | **não** |
| H6, H8 | nenhum | não |

"B&H BTC +0,99%" aparece em `docs/HYPOTHESES.md:95,131` (D).

## 7. Integração com o predictor_core

| contrato pedido | existe no core 3.2.1? | o que existe | o cripto usa? | custo e risco |
|---|---|---|---|---|
| `RunManifest` | **não** | `TrialRegistryV2` (`contracts/trial_v2.py:277`): `TRIAL_V2_FIELDS` (`:20-45`) com seed, dataset_hash, data_cutoff, label_start/end, code_version, params, selection_path, `n_trials_family/domain/ecosystem`, metric, result; `testing/harness.py:166` recusa árvore suja | sim, só no circuito de pesquisa (`research_execution.py`, `research_worker.py`) | baixo para reusar; faltam `costs`, `validation_protocol` e `policy_version` (em `params` como dívida, ou estender no core) |
| `TrialLedger` | **não** | `measurement/trials.py`: `register_trial :388`, `load_trials :125`, `validate_trials :276`, `TrialRegistry :748`; `kernel/jsonl_store.py` (append-only) | sim: `analyzers/trials.py:19-28,143` sobre o `trials.json` | médio: o ledger legado não é encadeado; o append-only depende de disciplina (§3) |
| `Evaluator` | **não** (só `PrequentialEvaluator` abstrato, `testing/prequential.py:23`) | `measurement/stats.py` (sharpe, sortino, max_drawdown, `probabilistic_sharpe_ratio :154`, block_bootstrap, ci_mean, spearman); `metrics.py` (brier, log_loss, rps, `diebold_mariano`); `bootstrap_ci` | sim (PSR em `backtest_v3.py:936,1015`) | baixo |
| DSR | **sim** | `deflated_sharpe_ratio :692`, `expected_max_sharpe :666`; `DeflationNotEstimableError :680`. Recebe a **lista de Sharpes** (estima V[SR]), não só N | sim (`analyzers/trials.py:26,34,39`) | a sensibilidade N/2N/5N exige chamar `expected_max_sharpe(N, V)` direto |
| PBO | não | local: `analyzers/pbo.py` (**protegido**) | sem chamador de produção | — |
| `DecisionPolicy` / política | **não** | limiares espalhados: PSR 0,80 (`backtest_v3.py:129`; `operational/attest_harness.py:74`); PBO 0,2/0,5 (`pbo.py:65-67`); charters por hipótese; `v3/economic_gate.py`; `trading/cost_policy.py` | — | criar arquivo versionado (o guia manda que seja no core) |

## 8. Resultado real dos testes (isolado)

- **Como o CI roda** (`.github/workflows/ci.yml:25,32,33`): `uv sync --locked --all-extras` → `uv build` → `uv run --no-sync pytest --cov=GarimpoInvestimentos --cov-report=term-missing` (`pyproject.toml:49-50`: `testpaths=["tests"]`, `--strict-config --strict-markers`).
- **Ambiente:** worktree `~/predictors/work/cripto-cripto-predictor` (`341d270`, árvore == HEAD); venv `~/predictors/runtime/cripto/venv` criado do `uv.lock` (`9ab423a0…`); `dist/` do `uv build` do mesmo commit.
- **Isolamento:**
  - `env -i` (PATH = venv + /usr/bin + /bin; HOME temporário vazio; nenhum `.env` na árvore);
  - `unshare -rn` (namespace de rede vazio, loopback DOWN; `connect(1.1.1.1:443)` → errno 101, conferido no log).
- **Comando:** `env -i PATH=… HOME=… LANG=C.UTF-8 unshare -rn …/venv/bin/python -m pytest -p no:cacheprovider --cov=GarimpoInvestimentos --cov-report=term-missing --junitxml=…/suite_isolated.junit.xml`
- **Resultado:** 1664 coletados, **1664 passed, 0 failed, 0 skipped, 0 errors**; 33 warnings; **211,3 s**; exit 0; cobertura 74%.
- **Warnings:** os 33 são `ResourceWarning: unclosed database` (SQLite) em `tests/conformance/test_import_closure.py`. **Nenhum teste tentou rede nem `.env`**.
- **Logs:** `~/predictors/runtime/cripto/prompt2/suite_isolated.log`, `suite_isolated.junit.xml`.

## 9. Plano para os Prompts 3a, 3b e 3c

### Bloqueios que o dono precisa decidir antes do 3a

1. **Qualificação (C24.3 / C15.1).**
   - O `cripto-predictor` qualificado (`341d270`) só pode mudar dentro dos `adapter_paths` na Etapa B. Qualquer mudança fora deles reabre a Etapa A (C24.4: novo `STACK_BASELINE_V1.n`, requalificação).
   - **O conjunto protegido inclui** `GarimpoInvestimentos/trials.json`, `charters/*`, `docs/HYPOTHESES.md`, `docs/EVIDENCE_REGISTRY.md`, `GarimpoInvestimentos/h6_status.json`, `GarimpoInvestimentos/analyzers/pbo.py` e `docs/evidence/cripto_v12_dsr_inventory.json` (conferido em `predictor-qualification/qualification/crypto/PROTECTED_SET.json`). Alterar = P0.
   - Opções: (a) branch longa, não mergeada, até o plano da Etapa B; (b) reabertura aceita e requalificação; (c) implementar num repo ou pasta nova que não mude o domínio, lendo os artefatos protegidos só para leitura.
2. **Contratos do core.**
   - `RunManifest`, `TrialLedger`, `Evaluator`, `DecisionPolicy` e o arquivo de política não existem. O guia manda rodar o `01-core.md` antes.
   - O core também está congelado na Etapa A: mudar exige decisão do dono, `STACK_BASELINE_V1.n` e C14 nas 3 missões.
   - Sem o core, o 3a/3b cria o mínimo localmente, como dívida.
3. **Dados** (regra dos prompts: só local, com hash; se precisar baixar, parar e perguntar).
   - Os dados horários do V3 (spot 1h, funding **com mark price**, OI) e a Feature Store (previsões LLM de H4–H6) não estão no PC 2 nem no git.
   - O único dataset local com hash é o da D-16 (BTCUSDT diário e funding, set/2025–set/2026, 52 semanas). Ele não serve ao WFA do V3.
   - Opções: copiar `data/v3/*` e a Feature Store do PC 1 com sha256; ou autorizar download do data.binance.vision (klines 1h, fundingRate, metrics, **markPriceKlines** para suprir o mark price).
4. **Atestação dispensada**, mantida a restrição de não rodar nada com credenciais nem rede.

### 3a: baselines, custos, walk-forward, manifesto

- **Obrigatório:**
  - baselines naive/random walk e buy-and-hold **no protocolo do WFA do V3**, hoje inexistentes (novo módulo, por exemplo `v3/baselines.py`, chamado por `run_wfa`);
  - custos explícitos e configuráveis também nos caminhos só-brutos que forem avaliados;
  - teste de monotonicidade líquido × custo com turnover alto;
  - teste "nenhum ts de teste ≤ último ts de treino" (hoje o `test_v3_wfa_purge_contract.py` só replica aritmética);
  - reprodutibilidade (mesma config + hash + seed; o HMM usa seeds 42..46);
  - manifesto em **toda** execução avaliativa (`run_wfa` hoje não registra), baseado em `TrialRegistryV2` e completado com costs, protocolo e política;
  - crash também vai para o ledger.
- **Arquivos prováveis:** `v3/backtest_v3.py` (não protegido), novo `v3/baselines.py`, novo `run_manifest`/ledger local; **não** o `trials.json` (protegido: usar ledger novo append-only, por exemplo `JsonlStore`).
- **Riscos:** mudar `backtest_v3.py` altera o caminho que produziu os vereditos H1–H3. Manter os artefatos antigos intactos.
- **Dependências:** bloqueios 1 a 3.

### 3b: CPCV, PSR/DSR/PBO, política

- **Obrigatório:**
  - CPCV com purga derivada do horizonte (24h, ou 48h no H3) e embargo derivado da autocorrelação dos retornos de 8h. Hoje não existe;
  - PBO **sem tocar** o `analyzers/pbo.py` protegido (novo módulo com purga e embargo, reusando a lógica por import);
  - DSR: `N_trials = LOWER_BOUND(32)`, sensibilidade com N=32, 64, 160 e N_upper=42, decisão pelo pior caso;
  - V[SR] exige Sharpes na **mesma base**: o ledger atual não tem `sharpe_basis`, então é preciso recomputar numa base única ou declarar V[SR] UNKNOWN (`DeflationNotEstimableError`);
  - arquivo de política versionado (limiares hoje hardcoded: `backtest_v3.py:129`, `attest_harness.py:74`, `pbo.py:65-67`);
  - "sem baseline → NO_DECISION".
- **Opcional:** skfolio para CPCV (licença e versão a verificar no momento; não verificadas nesta etapa); não usar mlfinlab; pypbo é AGPL (evitar).
- **Testes:** purga sintética; DSR mais conservador com N maior; valor numérico conferido (Bailey & López de Prado 2014); NO_DECISION.

### 3c: foundation model zero-shot e execução real

- **Obrigatório:**
  - verificar a licença **atual** do código e do checkpoint Chronos (model card), a data de publicação e o corte pós-publicação;
  - baixar o checkpoint exige parar e perguntar (o PC 2 não tem nenhum);
  - CRPS / quantile loss;
  - execução real **só** com dado local com hash (bloqueio 3), período definido **antes**, todos os runs no ledger.
- **Risco:** a amostra pós-corte provavelmente é pequena (o checkpoint é de 2024–2025 e o dataset local tem 52 semanas) → `INSUFFICIENT_SAMPLE` é o desfecho provável, e é resultado válido.
- **Dependências:** bloqueios 1 a 3; licença; download.

### Prompt 4 (antecipado)

- Reavaliar H6 exige as previsões legadas da Feature Store (PC 1).
- H1–H3 exigem os CSVs do V3.
- Sem esses artefatos, o status é `NOT_REPRODUCIBLE`. O prompt proíbe recriar variantes.
- Pré-registro e holdout selado precisam de ledger novo (o `trials.json` é protegido). Status de hipótese vive em `charters/scientific_state.json`, que também é protegido: mudança só com decisão do dono.

## Adendo de 2026-09-25: anexos versionados

O log e o junit da suíte isolada (§8), antes citados só em `~/predictors/runtime/cripto/prompt2/`, agora estão
em `docs/evidence/2026-09-24-prompt2/`, junto do script que os gerou:

| arquivo | sha256 |
|---|---|
| `suite_isolated.log` | `bd40de9a…` |
| `suite_isolated.junit.xml` | `a53fe2c6…` |
| `run_suite_isolated.sh` | `d2ce1fdb…` |

Um desvio do plano do §9: o 3b implementou o PBO pelo CSCV **padrão** (Bailey et al. 2017), que é o que o
Prompt 3b pede, reusando o `analyzers/pbo.py` protegido. A menção deste plano a "PBO com purga e embargo" não foi
implementada. O efeito da adjacência entre blocos IS/OOS com rótulos sobrepostos fica como limitação conhecida,
hoje sem uso, porque nenhuma avaliação real computou PBO.
