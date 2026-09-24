# 2026-09-24 — Prompt 3b: CPCV, PSR/DSR/PBO e política de decisão versionada

Base: Prompt 3a (`docs/evidence/2026-09-24-prompt3a-baselines-custos-walkforward-manifesto.md`), já no `main`
(`46ff7d2`). Branch `research/cripto-prompt3b-20260924`, a partir de `46ff7d2`. Classificação: **PROVEN** =
constatado nesta sessão; **DECLARED** = só em doc ou comentário; **UNKNOWN** = indeterminado.

> Como no 3a: mudança fora dos `adapter_paths` reabre a Etapa A da qualificação (C24.3/C24.4). Isso já
> aconteceu com o merge do #128, e a decisão sobre a requalificação continua com o dono.

## Decisões tomadas

1. **CPCV local, sem skfolio.** O skfolio não está instalado no venv (PROVEN: `import skfolio` →
   `ModuleNotFoundError`). O `CombinatorialPurgedCV` dele purga e embarga **por contagem de linhas**
   (DECLARED: `docs/open_source_research/20260911T0525/COMPETITIVE_LANDSCAPE.md:14`, licença BSD-3-Clause).
   O prompt exige purga pelo horizonte **real** do rótulo, então o skfolio não faz exatamente isso. Adotá-lo
   também exigiria download e dependência nova. Implementei o mínimo localmente, com testes fortes e
   mutantes. **Nenhuma dependência nova.** mlfinlab (proprietário) e pypbo (AGPL) não foram usados: o PBO
   por CSCV já existe em stdlib no arquivo protegido `analyzers/pbo.py`, que é reutilizado sem alteração.
2. **Política no core: não existe.** O `predictor_core` 3.2.1 não tem arquivo de política de decisão
   (PROVEN: `grep -i polic` no pacote só acha `revision_policy`/`retention_policy`/`exclusion_policy` em
   `contracts/scientific.py` e a política de agregação de `data/router.py`). Criei um arquivo local
   versionado e registrei **dívida técnica a migrar para o core**.
3. **A política nasce `PROPOSED`.** Limiar de decisão exige aprovação humana. Eu não posso aprovar a
   própria proposta, então a v1 fica `PROPOSED` e, assim, **toda decisão sai `NO_DECISION`** até o dono
   aprovar. Para aprovar: num commit revisado por PR, trocar `status` para `APPROVED` e preencher
   `approval.approved_by`, `approval.approved_at_utc` e `effective_from_utc` (≥ aprovação). O validador
   recusa `APPROVED` sem esses campos e recusa vigência anterior à aprovação.
4. **Nada retroativo.** Hipótese registrada antes de `effective_from_utc` recebe `NO_DECISION` por esta
   política. As hipóteses H1–H8 existentes continuam com os critérios pré-registrados delas. A reavaliação
   fica para o Prompt 4, sem reabrir busca.
5. **O `run_wfa` continua registrando `policy = NOT_DEFINED`** no manifesto: nenhuma política está
   aprovada, e o veredito dele (`final_verdict`) é o critério legado do charter, não uma decisão sob a v1.
   Quando houver política `APPROVED`, a decisão sai de `decide()` e vai para o ledger como linha `DECISION`,
   com id, versão e sha256 da política.

## O que mudou

| arquivo | mudança |
|---|---|
| `GarimpoInvestimentos/research/cpcv.py` (novo) | `cpcv_splits`: N grupos contíguos e C(N,k) divisões. Purga toda observação de treino cuja janela `[start, available]` cruza a janela de um bloco de teste `[menor start, maior available]`. Embargo explícito e configurável: sai do treino quem começa em `(t1, t1+embargo]`. Também `backtest_paths` (C(N−1,k−1) caminhos) e `derive_purge_and_embargo` |
| `GarimpoInvestimentos/research/strategy_metrics.py` (novo) | Sharpe líquido, max drawdown, turnover, PSR, `psr_from_moments`, `deflated_sharpe`, `trial_sharpe_variance`, `n_trials_scenarios`, `dsr_sensitivity`, `pbo_cscv`, com referência no docstring. Reusa o core (`sharpe`, `max_drawdown`, `probabilistic_sharpe_ratio`, `expected_max_sharpe`) e o `analyzers/pbo.py` protegido |
| `GarimpoInvestimentos/research/decision_policy.py` (novo) | `load_policy`/`validate_policy` (schema e sha256 canônico), `decide` → `GO`/`NO_GO`/`NO_DECISION` com motivos e referência da política, `record_decision` no ledger encadeado do 3a |
| `GarimpoInvestimentos/research/policies/decision_policy_v1.json` (novo) | todos os limiares, com justificativa de cada um e status `PROPOSED` |
| `GarimpoInvestimentos/run_ledger.py` | só o comentário de `POLICY_NOT_DEFINED` |
| `GarimpoInvestimentos/research/README.md` | seção da API nova |
| `tests/test_evaluation_protocol_3b.py` (novo) | 65 testes (abaixo) |

**Nenhum arquivo do conjunto protegido foi tocado**: `trials.json`, `charters/*`, `v3/costs.py`,
`analyzers/pbo.py` e `HYPOTHESES.md` ficam iguais. Nenhum teste existente foi alterado.

## purge_size e embargo_size: definição exata e valores

Relógio: ms. Cada observação é uma decisão com janela de informação `[start, available]`, onde `start` é o
instante da decisão e `available` o instante em que o alvo fica conhecido (`available ≥ end`).

| grandeza | definição | valor no V3 | classificação |
|---|---|---|---|
| `purge_size` | = horizonte do rótulo. No CPCV, a purga não é uma contagem: sai do treino toda observação cuja janela `[start, available]` cruza a janela do bloco de teste (fechada nas duas pontas) | **24 h** (`backtest_v3.py:132` `_DEFAULT_HORIZON_HOURS = 24`). Com decisões a cada 8 h (`backtest_v3.py:14-15`; a docstring em `:495` diz que coexistem 3 posições), isso dá **3 decisões purgadas antes e 3 depois** de cada bloco de teste | PROVEN (código + `test_purge_size_follows_the_label_horizon`) |
| `embargo_size` | = `embargo_steps × passo`. `embargo_steps` é o número de lags iniciais **consecutivos** com \|ACF\| ≥ 1,96/√n (banda de Bartlett sob ruído branco), nos retornos **por passo, não sobrepostos** (8 h no V3). Nos retornos de 24 h amostrados a cada 8 h, a ACF viria inflada pela própria sobreposição, que já é tratada pela purga. Se nenhum lag até `max_lag` sai da banda, `capped = True` | **UNKNOWN**: os dados horários do V3 não estão no PC 2 (Prompt 2, §9). A regra está implementada e testada. O valor sai da série de retornos do universo avaliado: é um parâmetro estrutural do protocolo, que não usa o desempenho de nenhuma configuração | regra PROVEN (MA(2) → 2 passos; ruído branco → 0); valor real UNKNOWN |

O WFA registrado do V3 continua com a própria purga de 7 dias entre IS e OOS (`backtest_v3.py:124`),
maior que o horizonte de 24 h. O CPCV é uma ferramenta nova; não substitui o protocolo das hipóteses já
registradas.

## Métricas

Base de Sharpe (`SHARPE_BASIS = per_decision_unannualized_sample_std`): a mesma dos baselines do 3a
(`backtest_v3._series_metrics`). O PSR do core usa internamente o desvio populacional; a diferença é o fator
√(n/(n−1)), de ordem 1/(2n), declarada no docstring.

| métrica | fórmula / referência | teste que prova |
|---|---|---|
| Sharpe líquido | média/desvio amostral do P&L líquido por decisão, sem anualizar (core `sharpe`, `periods_per_year=1`) | `test_net_sharpe_drawdown_and_turnover_by_hand` (√0,6 à mão) |
| Max drawdown | max (pico − equity)/pico sobre ∏(1+r) a partir de 1 (core `max_drawdown`) | idem (1 − 0,8316/1,1 à mão) |
| Turnover | média por período de \|p_t − p_{t−1}\|, com p_{−1} = 0 e a liquidação final contada; `round_trip=True` → 2·\|p_t\| (V3: cada decisão abre e fecha) | idem (0,5 e 0,75 à mão) |
| PSR | Φ((SR − SR*)·√(T−1)/√(1 − γ3·SR + (γ4−1)/4·SR²)). Bailey & López de Prado (2012), *The Sharpe Ratio Efficient Frontier*, J. of Risk 15(2) | `test_psr_from_moments_equals_the_core_psr_on_a_series` (`rel=1e-12`) |
| DSR | PSR(SR0), SR0 = √V[SR]·((1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(N·e))). Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*, JPM 40(5) | `test_dsr_matches_the_published_numerical_example`: o exemplo do artigo (N=100, V[SR anual]=½, SR anual 2,5, T=1250, assimetria −3, curtose 10) dá **SR0 = 0,1132/dia e DSR = 0,9004**, iguais ao publicado; a conta à mão está no docstring |
| DSR × N | cenários N, 2N, 5N (multiplicadores da política) e N_upper; a decisão usa o **menor** DSR | `test_larger_n_makes_the_dsr_more_conservative_with_identical_candidate` |
| V[SR] | variância amostral dos Sharpes das tentativas, **só** se todas as tentativas com Sharpe finito tiverem `params.sharpe_basis` igual (mesma regra de `analyzers/trials.py:39-53`) | `test_trial_variance_requires_a_single_sharpe_basis`, `test_dsr_refuses_to_pass_as_deflated_without_a_discount` |
| PBO | CSCV: S blocos contíguos, C(S,S/2) divisões IS/OOS, ω = rank OOS da melhor IS/(N+1), PBO = fração com logit(ω) ≤ 0. Bailey, Borwein, López de Prado & Zhu (2017), *The Probability of Backtest Overfitting*, J. of Computational Finance 20(4) | `test_pbo_matches_a_hand_computed_cscv`: S=4, 2 configurações, 6 combinações enumeradas à mão → **PBO = 4/6**, logits ±ln 2 |

### N de tentativas no DSR (sensibilidade)

O N conhecido é `LOWER_BOUND(32)`, com `N_upper ≈ 42` (Prompt 2). Um N menor que o real infla o DSR. A
política manda calcular N=32, 2N=64, 5N=160 e N_upper=42 e decidir pelo pior caso, que é sempre o **5N**
(maior N → maior SR0 → menor DSR), e registrar todos os valores (`dsr_sensitivity` devolve os quatro).

**Aplicado ao ledger real (somente leitura):** o `trials.json` (sha256 `b43661d5…`) tem 26 entradas, 23
com Sharpe finito e **0 com `sharpe_basis`**. Então `trial_sharpe_variance` levanta
`DeflationNotEstimableError` (PROVEN; saída em `2026-09-24-prompt3b/real_trials_vsr.txt`). Sem V[SR], não
há DSR, e qualquer decisão sobre essas tentativas sai `NO_DECISION`. Para destravar, é preciso recomputar
os Sharpes das tentativas numa base única, com o dado original, que não está no PC 2.

## Política de decisão (`research/policies/decision_policy_v1.json`)

sha256 canônico `f2c482b7aee9959089b37b78b99310633ef7fe73d83a3a828d4555e1af11bc28` (bytes do arquivo
`7561d53a…`). Status **PROPOSED**.

| limiar | valor | origem |
|---|---|---|
| `min_seeds` | 5 | as 5 seeds já fixadas no RegimeEngine (42..46); a decisão usa a pior seed |
| `dsr_min` | 0,95 | confiança de 95% (Bailey & López de Prado, 2014) |
| `pbo_max_exclusive` | 0,20 | corte "BAIXO" de `analyzers/pbo.py`, que hoje é só leitura; vira gate apenas para hipóteses futuras |
| `required_baselines` | random_walk, naive_persistence, always_long, buy_and_hold | os baselines do 3a; o candidato precisa de Sharpe líquido (pior seed) maior que o do melhor deles |
| `require_dataset_sha256` | true | identidade do dataset (manifesto do 3a) |
| `max_missing_fraction` | 0,01 | **proposta sem derivação empírica**; decisão do dono |
| `min_oos_observations` | 32 | 2 × `pbo_n_splits` (16): mínimo para o PBO ser definido |
| `dsr_n_sensitivity` | ×1, ×2, ×5 + N_upper; pior caso | Prompt 3b §3 |

Regra de `decide`: qualquer insumo ausente ou não finito (baseline, DSR de algum cenário ou seed, PBO,
seeds, hash, qualidade de dados), política não aprovada ou hipótese anterior à vigência → `NO_DECISION`.
Com tudo presente, vira `GO` só se o DSR do pior caso ≥ `dsr_min`, o PBO < `pbo_max_exclusive` e o
Sharpe da pior seed > o melhor baseline. Senão, `NO_GO` com os motivos. Toda saída carrega
`policy.{id, version, sha256, status}`.

**Limiares legados que ficam no código (dívida registrada):**
- `backtest_v3.py:136-137`: `_GO_PSR_THRESHOLD = 0.80` e `_GO_MAX_DD_THRESHOLD = 0.20`.
- `operational/attest_harness.py:74`: `_PSR_THRESHOLD = 0.80`.

Esses valores são os critérios pré-registrados do veredito legado das hipóteses já registradas e do
harness de poder. Movê-los mudaria código qualificado e o critério de hipóteses encerradas, o que fica
para o dono e o Prompt 4. `ENTROPY_THRESHOLD` (`v3/regime_engine.py:46`) é parâmetro do modelo e
`JUMP_THRESHOLD` (`dpl/ingest.py:46`) é da ingestão; nenhum dos dois é limiar de decisão.

## Verificação

Venv `~/predictors/runtime/cripto/venv-prompts`, isolado de rede e segredos
(`env -i PATH=… HOME=<tmp vazio> LANG=C.UTF-8 unshare -rn python -m pytest …`).

| teste (`tests/test_evaluation_protocol_3b.py`) | prova |
|---|---|
| `test_without_purge_train_labels_would_cross_test_and_cpcv_leaves_no_forbidden_pair` | rótulos de 24 h a cada 8 h, N=6, k=2, embargo 16 h. **Sem a purga**, o complemento do teste tem pares que se sobrepõem (`naive_leaks > 0`). **Com o mecanismo**, em todas as 15 divisões: partição exata e nenhum par treino × teste com janelas cruzadas ou treino começando no embargo |
| `test_no_forbidden_pair_with_irregular_labels_and_late_availability[0..24]` | propriedade em 25 casos aleatórios (seed fixa): rótulos de duração irregular, `available > end`, N, k e embargo sorteados. Mesmas garantias, verificadas par a par por força bruta |
| `test_purge_size_follows_the_label_horizon` | horizonte de 3 passos → 3 purgados antes e 3 depois de um grupo interior; horizonte de 6 passos → 12 |
| `test_embargo_is_explicit_and_configurable` | embargo 0 → nada embargado; o treino encolhe monotonicamente com o embargo; embargo negativo é recusado |
| `test_backtest_paths_cover_every_group_once` | C(5,1) = 5 caminhos, cada um cobre todos os grupos uma vez, sem reuso de previsão |
| `test_embargo_is_derived_from_the_autocorrelation_of_step_returns` | MA(2) (ACF 2/3, 1/3, 0) → embargo de 2 passos; ruído branco → 0; purga = horizonte |
| `test_dsr_matches_the_published_numerical_example` | exemplo publicado: DSR 0,9004 |
| `test_psr_from_moments_equals_the_core_psr_on_a_series` | fórmula por momentos = PSR do core |
| `test_larger_n_makes_the_dsr_more_conservative_with_identical_candidate` | mesmo candidato: N ↑ → SR0 ↑ e DSR ↓ em 32 < 42 < 64 < 160; pior caso = 5N |
| `test_dsr_refuses_to_pass_as_deflated_without_a_discount[4]` | N < 2, V[SR] 0, NaN ou negativo → `DeflationNotEstimableError` |
| `test_trial_variance_requires_a_single_sharpe_basis` | base misturada ou menos de 2 Sharpes → erro |
| `test_pbo_matches_a_hand_computed_cscv` | PBO = 4/6 à mão |
| `test_net_sharpe_drawdown_and_turnover_by_hand` | Sharpe, max DD e turnover à mão |
| `test_versioned_policy_file_is_proposed_and_hashed` | a v1 carrega com status PROPOSED e sha256 canônico |
| `test_unapproved_policy_never_decides` | política não aprovada → `NO_DECISION`, mesmo com evidência forte |
| `test_strong_evidence_under_approved_policy_is_go_and_records_the_policy` | com política aprovada (cópia em memória) e evidência forte → `GO`, com id/versão/sha256 |
| `test_without_baseline_comparison_the_decision_is_no_decision[5]` | **sem baseline → `NO_DECISION`**: `None`, vazio, um ausente, `None` ou NaN |
| `test_missing_or_invalid_evidence_never_becomes_go[9]` | DSR não computável, cenário de N ausente, seeds < 5, sem PBO, sem hash, dados ruins, fração desconhecida, OOS curto e hipótese retroativa → `NO_DECISION` |
| `test_worst_case_n_scenario_and_worst_seed_decide` | um único 5N fraco numa seed → `NO_GO`, apontando seed e cenário; Sharpe de uma seed abaixo do baseline → `NO_GO`; PBO = 0,20 → `NO_GO` |
| `test_thresholds_come_from_the_policy_file_not_from_code` | trocar `dsr_min` no arquivo muda a decisão e o sha256; a AST do `decision_policy.py` não tem nenhum dos valores numéricos da política |
| `test_invalid_policy_is_rejected[5]` | limiar faltando, APPROVED sem aprovador, vigência retroativa, multiplicadores sem 1, versão 0 → `PolicyError` |
| `test_decision_is_appended_to_the_hash_chained_ledger` | linha `DECISION` no ledger do 3a, com a política; a cadeia confere; `DECISION` não conta como tentativa |

**Resultados reais:**

- **Testes novos:** 65 passed.
- **Mutantes do CPCV** (`2026-09-24-prompt3b/mutation_check.py`): 5 de 5 mortos. Sem purga, purga por `end`
  em vez de `available`, janela do teste por `end`, sem embargo e embargo com borda aberta: cada um derruba
  ao menos um teste. Log: `mutation_check.log`.
- **Suíte completa** (isolada, `pytest --cov`): **1742 passed, 0 failed, 0 skipped**, 33 warnings (os
  mesmos `ResourceWarning` de SQLite do 3a), 285 s, cobertura total 74%. `cpcv.py` 88%,
  `decision_policy.py` 92%, `strategy_metrics.py` 92%. Log: `2026-09-24-prompt3b/suite_isolated.log`
  (sha256 `98a04559…`).
- **Lint:** `ruff check` e `ruff format --check` limpos.
- **pyright** (1.1.411, a versão fixada no projeto; `pyrightconfig.json`, modo basic): **0 errors, 0
  warnings**, rodado localmente. O WSL não tem `libatomic.so.1`; usei `LD_LIBRARY_PATH` apontando para a
  lib de um sysroot já extraído em `~/predictors/runtime`, sem sudo e sem mudar a configuração do sistema.
  O node do pyright foi copiado para `~/predictors/runtime/cripto/pyright-cache`.

## O que continua DECLARED / UNKNOWN

- **Valor real do `embargo_size` e qualquer decisão sobre dado real:** UNKNOWN. Os dados do V3 não estão no
  PC 2, e nenhum download foi feito.
- **V[SR] do histórico:** não estimável (0 de 23 Sharpes com `sharpe_basis`). O DSR real é **não
  computável**, e as decisões sobre H1–H8 continuam `NO_DECISION` sob esta política.
- **Limiares da v1:** propostos. Só valem depois da aprovação do dono, e só para hipóteses registradas a
  partir da vigência. `max_missing_fraction` não tem derivação empírica.
- **Política no core:** não existe. O arquivo local é dívida técnica a migrar (`01-core.md`).
- **Limiares legados** em `backtest_v3.py` e `attest_harness.py`: continuam no código (ver acima).
- **CI:** o resultado dos 4 jobs na PR fica registrado nela.
