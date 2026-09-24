# 2026-09-24 — Prompt 3a: baselines, custos explícitos, walk-forward estrito e manifesto de execução

Base: relatório do Prompt 2 (`docs/evidence/2026-09-24-prompt2-auditoria-tecnica.md`). Branch
`research/cripto-prompts-20260924`, a partir de `main` `174573d`. **Não mergear** sem a decisão do dono sobre
a qualificação: o `main` está qualificado na Etapa A, e mudança de domínio fora dos `adapter_paths` reabre
a Etapa A (C24.3/C24.4).

## Decisões tomadas (o dono delegou: "pode escolher a melhor")

1. **Qualificação:** trabalho numa branch com PR em rascunho. **Nenhum arquivo do conjunto protegido foi
   tocado**: `trials.json`, `charters/*`, `v3/costs.py`, `analyzers/pbo.py` e `HYPOTHESES.md` ficam iguais.
2. **Core:** `predictor_core` 3.2.1 não tem `RunManifest`/`TrialLedger`/`DecisionPolicy`, e o core está
   congelado. Por isso implementei o mínimo compatível no cripto, sobre `predictor_core.kernel.jsonl_store.JsonlStore`,
   e registrei como **dívida técnica a migrar para o core** (`01-core.md`).
3. **Dados:** nenhum dado real foi usado no 3a. Todas as provas usam CSVs sintéticos determinísticos gravados
   no tmp do teste. Nenhum download, nenhuma credencial, nenhuma rede (testes em `unshare -rn`).
4. **Custos:** os defaults continuam os históricos (fee 10 + slippage 5 bps por perna, spread 0). O spread é
   explícito e configurável, mas com default 0. Mudar os defaults mudaria o custo das hipóteses registradas,
   e o próprio `v3/costs.py` exige trial nova para isso.

## O que mudou

| arquivo | mudança |
|---|---|
| `GarimpoInvestimentos/v3/cost_spec.py` (novo) | `CostSpec(taker_fee_bps, spread_bps, slippage_bps)`: custos explícitos. Meio spread por perna taker. `to_cost_model()` compõe o `CostModel` protegido, sem alterá-lo. Funding é sempre o realizado com mark price |
| `GarimpoInvestimentos/run_ledger.py` (novo) | manifesto + ledger JSONL append-only encadeado por hash (`prev_sha256`/`record_sha256`, `verify_chain`). O `recorded_run` grava `STARTED`, depois `COMPLETED` com métricas ou `CRASHED` com tipo e mensagem do erro, e re-levanta a exceção. `code_identity()` registra versão do pacote, commit e flag dirty (ou `installed_package`) |
| `GarimpoInvestimentos/v3/backtest_v3.py` | `run_wfa` passa a envolver **toda** execução no ledger (inclusive as chamadas do sweep de Kelly e da grade). Novo parâmetro `spread_bps` (default 0) e `--spread-bps` na CLI. Baselines no mesmo protocolo. Trava de separação temporal estrita por fold. `FoldResult` ganha `is_last_train_ms`/`oos_first_test_ms`. `WFAResult` ganha `baselines`, `run_id`, `input_sha256`, `data_interval`, `spread_bps`. O artefato `returns.json` usa o mesmo `run_id` do ledger |
| `tests/test_evaluation_protocol_3a.py` (novo) | 13 testes (abaixo) |

Nenhuma dependência nova. Nenhum teste existente foi alterado. Um defeito de desenho meu, achado pela suíte,
foi corrigido no código, não no teste: na primeira versão, os baselines rodavam antes de o fold ser aceito e
exigiam `mark_price` em folds que seriam descartados. Isso quebrava `tests/test_v3_wfa_actual_slicing.py`, cujo
fixture não tem esse campo. Agora os baselines só rodam nos folds aceitos.

### Manifesto (linha `STARTED` + `COMPLETED`/`CRASHED` no ledger)

- **Identificação:** `run_id`, `kind`, `attempt` (1 + execuções anteriores com o mesmo `config_sha256`).
- **Código:** `code.{package_version, commit, dirty, source}`.
- **Configuração:** `config` e `config_sha256`, `costs` (`CostSpec.as_dict`).
- **Protocolo:** `validation_protocol` (IS 180d / purga 7d / embargo 0 / OOS 30d / passo 30d / horizonte do
  rótulo; o ajuste é só no IS).
- **Modelo:** `model` (família, n_states, covariância, features extras, limiares do sinal); `seeds` = 42..46,
  que são as sementes que o `RegimeEngine` tenta.
- **Política:** `policy` = `NOT_DEFINED` até o Prompt 3b (a ausência é registrada, nunca inventada).
- **Dados:** `dataset.{input_sha256 por arquivo, dataset_sha256, interval}`.
- **Resultado:** `metrics`, `baselines`, `artifacts.returns_json`, ou `error`.

Caminho do ledger: `CRIPTO_RUN_LEDGER` ou `<data>/research_ledger/runs.jsonl`. Nos testes fica no tmp; o
`conftest.py` já isola `DATA_DIR`.

### Baselines, no mesmo universo, período (folds aceitos pelo modelo), pontos de decisão, horizonte, convenção de entrada/saída, barreiras, funding realizado e fricção do modelo

| baseline | definição | por que é o naive adequado |
|---|---|---|
| `random_walk` | previsão de retorno 0 → nenhuma posição (P&L e custo 0) | o target é o log-retorno em H horas; sob passeio aleatório, a melhor previsão é 0 |
| `naive_persistence` | sinal do retorno das últimas H horas já públicas → ±kelly | naive direcional usando só o passado (`_naive_persistence_direction`) |
| `always_long` | +kelly em toda decisão, com o horizonte do modelo | mesma base de comparação do modelo, decisão a decisão |
| `buy_and_hold` | +kelly da 1ª decisão ao fim de cada fold OOS, um round trip | buy-and-hold da estratégia, por fold |

Seasonal-naive não foi incluído: a frequência de 8h do V3 não tem sazonalidade justificada no código nem nos
docs (Prompt 2, §6).

## Verificação

Tudo com o venv `~/predictors/runtime/cripto/venv-prompts` (`uv sync --locked --all-extras --python 3.13`),
isolado de rede e segredos: `env -i PATH=… HOME=<tmp vazio> LANG=C.UTF-8 unshare -rn python -m pytest …`.

| teste (`tests/test_evaluation_protocol_3a.py`) | prova |
|---|---|
| `test_cost_spec_without_spread_is_the_historical_cost_model` | spread 0 → fricção idêntica ao `CostModel` histórico; spread entra como meio spread por perna |
| `test_net_result_is_monotonic_non_increasing_in_each_cost[taker_fee_bps / spread_bps / slippage_bps]` | estratégia sintética de turnover alto (direção alterna a cada decisão), `run_wfa` real: líquido **não crescente** em 0 → 1 → 5 → 20 → 80 bps de cada componente, bruto constante, e o custo morde (último < primeiro). O mesmo vale para o baseline `always_long`. Sem depender de número arbitrário |
| `test_no_test_timestamp_is_at_or_before_the_last_training_timestamp` | em cada fold, primeiro teste > último treino, e a diferença é ≥ a purga |
| `test_overlapping_folds_fail_closed_and_are_recorded` | com purga negativa, os folds se sobrepõem → a trava levanta `RuntimeError` e o ledger registra `CRASHED` |
| `test_baselines_use_the_same_decisions_costs_and_accounting_as_the_model` | com modelo sempre-comprado, o baseline `always_long` reproduz o modelo (`rel=1e-12`). Também: `random_walk` = 0, B&H por fold, custos iguais |
| `test_naive_persistence_uses_only_past_prices` | mudar o futuro não muda a decisão do naive |
| `test_same_config_dataset_and_seed_give_the_same_result` | **HMM real**: duas execuções com a mesma config, dataset (hash) e seeds dão métricas iguais. Tolerância `rel=1e-12`, justificada: mesmo processo e plataforma, seeds fixas; só absorve reordenação de ponto flutuante. Baselines idênticos, `attempt` 1 → 2, mesmo `config_sha256` e `dataset_sha256`, `run_id` distintos |
| `test_every_run_writes_a_complete_manifest` | todos os campos do manifesto presentes |
| `test_crashed_run_is_recorded_and_the_error_propagates` | crash no ajuste do HMM → `CRASHED` com tipo do erro e dataset já identificado; a exceção propaga |
| `test_invalid_configuration_is_recorded_as_crashed` | custo inválido (spread negativo) também vai para o ledger |
| `test_ledger_is_append_only_and_hash_chained` | o arquivo só cresce (bytes antigos são prefixo), a cadeia confere, e alterar uma linha antiga é detectado |

**Resultados reais:**

- **Testes novos:** 13 passed (51,5 s).
- **Testes afetados:** 33 passed (`test_evaluation_protocol_3a`, `test_v3_wfa_actual_slicing`, `test_v3_macro_dxy_integration`, `test_threshold_grid_registry`, `test_kelly_sweep_cli`, `test_audit_release_guards`).
- **Suíte completa** (`uv build` + `pytest --cov`, isolada): **1677 passed, 0 failed, 0 skipped**, 33 warnings (os mesmos `ResourceWarning` de SQLite de antes), 310 s, cobertura 74%. `cost_spec.py` 100%, `run_ledger.py` 93%. Log: `2026-09-24-prompt3a/suite_isolated.log` (sha256 `51640477…`).
- **A/B do modelo** (`2026-09-24-prompt3a/ab_model_unchanged.py`): o mesmo `run_wfa` com HMM real, sobre os mesmos dados sintéticos, no `main` (341d270, mesma árvore de `174573d`) e na branch, dá JSON **idêntico byte a byte** (métricas, folds e séries bruta e líquida). `ab_main.json` = `ab_branch.json` = sha256 `c92149a9…`. Com os defaults, o comportamento do modelo não mudou.
- **Lint:** `ruff check` e `ruff format --check` limpos. `pyright` **não rodou localmente**: o Node baixado pelo pyright-python exige `libatomic.so.1`, ausente no WSL, e instalar exigiria sudo. Fica para o CI (job `quality`).

## O que continua DECLARED / UNKNOWN

- **Política de decisão:** não existe (`policy.status = NOT_DEFINED`); vem no Prompt 3b.
- **`RunManifest`/`TrialLedger` do core:** não existem; o ledger local é dívida técnica a migrar.
- **Caminhos só-brutos:** o juiz LLM (H4/H5), o H6 e o H8 (`analyzers/backtest.py`, `hypothesis_loop*.py`) continuam só brutos e sem manifesto. Aplicar custos ali mudaria o Sharpe que o código grava no `trials.json` protegido para hipóteses encerradas. Isso fica para decisão do dono e para o Prompt 4 (reavaliação sem reabrir busca).
- **Pipeline de replay:** o `v3/pipeline.py` (replay descritivo in-sample) não é execução avaliativa e ficou sem manifesto.
- **Nenhuma avaliação com dado real** foi feita no 3a. Os dados reais do V3 não estão no PC 2 (Prompt 2, §9).
- **pyright:** UNKNOWN até o CI.
