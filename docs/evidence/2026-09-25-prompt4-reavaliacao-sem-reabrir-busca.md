# 2026-09-25 — Prompt 4: reavaliar hipóteses sem reabrir o espaço de busca

Branch `research/cripto-prompt4-20260924`, cumulativa: 3c (PR #131) + aprovação da política v1 (PR #132, por
cherry-pick) + este prompt. Classificação: **PROVEN** = constatado nesta sessão; **DECLARED** = só em doc;
**UNKNOWN** = indeterminado.

## Resultado em uma linha

Nenhuma hipótese muda de status e nenhuma vira GO. Sem os artefatos históricos, H1–H5, H9, a grade V3 e a
ancestral v1 ficam `NOT_REPRODUCIBLE` e mantêm o status. A H6, reavaliada como correlação sobre o artefato
agregado, continua `CLOSED_INSUFFICIENT_SAMPLE` (poder ≤ 0,45 para ρ = 0,2). H7 e H8 seguem
`REGISTERED_NOT_ACTIVATED`, sem dado para executar. A FM do 3c fica `NO_DECISION`, porque a política aprovada
não é retroativa. **Zero variantes novas, holdout não acessado**, e um holdout futuro ficou selado.

## Verificação prévia (o prompt manda parar se faltar algo): nada falta

| componente | onde | status |
|---|---|---|
| baselines | `v3/backtest_v3.py` (random_walk, naive_persistence, always_long, buy_and_hold); `research/fm_zero_shot.py` | PROVEN (3a, 3c) |
| validação temporal | WFA com separação estrita (3a); `research/validation.py` | PROVEN |
| CPCV | `research/cpcv.py` (purga pela janela do rótulo, embargo pela ACF) | PROVEN (3b) |
| custos explícitos | `v3/cost_spec.py` | PROVEN (3a) |
| registro de tentativas | `trials.json` (core `TrialRegistry`) + ledger de execuções encadeado (`run_ledger.py`) | PROVEN |
| DSR / PBO | `research/strategy_metrics.py`; `analyzers/pbo.py` | PROVEN (3b) |
| política versionada | `research/policies/decision_policy_v1.json`, **APPROVED** pelo dono em 2026-09-25, sha256 `59352bb4…`, vigência pelo merge da PR #132 | PROVEN |

## Tabela principal

Reavaliação: run `20260925T160714507838Z-802ddaa852be` (`2026-09-25-prompt4/reevaluation.json`, sha256
`72fc5bd2…`). Inventário de artefatos: `2026-09-25-prompt4/inventory.json` (sha256 `b3bd2e95…`), com 3366
arquivos do git, 29 zips versionados e 69 arquivos em `~/predictors/data` varridos.

| hipótese | status anterior | protocolo aplicado | status novo | motivo | N_trials | run_id/evidência |
|---|---|---|---|---|---|---|
| H1 `v3-hmm-funding-oi-fr90` | CLOSED_NO_GO | régua nova só com o artefato histórico: **não aplicável** | **CLOSED_NO_GO** (`NOT_REPRODUCIBLE`) | Não há `returns.json` do WFA nem funding/OI/spot 1h da janela registrada. O único spot 1h versionado é uma auditoria de fonte de agosto de 2026, sem funding nem OI, e o d16 só tem 1d e funding de 2025-09 a 2026-09. Usar qualquer um deles seria reconstruir uma variante | 1 | `…802ddaa852be` |
| H2 `…-fr21` | CLOSED_NO_GO | idem | **CLOSED_NO_GO** (`NOT_REPRODUCIBLE`) | idem | 1 | idem |
| H3 `…-fr90-h48` | CLOSED_NO_GO | idem | **CLOSED_NO_GO** (`NOT_REPRODUCIBLE`) | idem | 1 | idem |
| H4 `v2-dpl-gemini-h7` | CLOSED_INSUFFICIENT_SAMPLE | idem | **CLOSED_INSUFFICIENT_SAMPLE** (`NOT_REPRODUCIBLE`) | Não há pares previsão × retorno D+7. Os `feature_store.db` versionados têm só 2–3 linhas em `predictions` e 4–5 em `predictions_archive`, abaixo de n ≥ 30 | 1 | idem |
| H5 `v2-dpl-multi-h7` | CLOSED_NO_GO | idem | **CLOSED_NO_GO** (`NOT_REPRODUCIBLE`) | idem | 1 | idem |
| **H6** `h6-sinal-invertido-d7` | CLOSED_INSUFFICIENT_SAMPLE | **Não é estratégia**: relação Spearman (IC95 em blocos) do sinal invertido com o retorno D+7, contra o nulo ρ = 0. Custos, CPCV, PSR, DSR e PBO = N/A. Régua nova aplicada ao artefato agregado `h6_status.json` | **CLOSED_INSUFFICIENT_SAMPLE** (`REEVALUATED_ON_AGGREGATE`; reprodução completa `NOT_REPRODUCIBLE`) | n = 84, ρ = −0,0567, IC95 [−0,2312; 0,1294] cruza zero. Poder para ρ = 0,2 (α = 0,05): Fisher-z iid **0,446**, bootstrap em blocos declarado 0,233, Fisher com n efetivo = 84/7 **0,093**; todos abaixo de 0,8. O MDE de ρ com n = 84 é **0,302** | 1 | idem |
| H7 `h7-macro-dxy-hmm-v1` | REGISTERED_NOT_ACTIVATED | só a configuração registrada, sem variante | **REGISTERED_NOT_ACTIVATED** (`NOT_EXECUTABLE`) | Não há execução válida anterior (o backtest de 2026-09-04 abortou por bug de infraestrutura) nem dado V3 local. Incompatibilidades abaixo | 1 | idem |
| H8 `h8-llm-hypothesis-generator` | REGISTERED_NOT_ACTIVATED | idem | **REGISTERED_NOT_ACTIVATED** (`NOT_EXECUTABLE`) | A coleta não foi iniciada (`docs/HYPOTHESES.md`, H8). Incompatibilidades abaixo | 1 | idem |
| H9 `h9-oi-volume-ratio-hmm-v1` | CLOSED_INSUFFICIENT_SAMPLE | régua nova só com o artefato histórico | **CLOSED_INSUFFICIENT_SAMPLE** (`NOT_REPRODUCIBLE`) | Sem artefato V3 (como em H1) | 1 | idem |
| grade V3 (16 configurações) | CANDIDATE_ONLY (família `funding_oi_hmm_v3` congelada) | idem | **mantido** (`NOT_REPRODUCIBLE`) | idem | 16 | idem |
| ancestral `v1-direct-gemini-h7` | PRE_PROTOCOL (sem rótulo formal) | idem | **mantido** (`NOT_REPRODUCIBLE`) | Sem pares LLM (como em H4) | 1 | idem |
| **FM-3c** `cripto-fm-zero-shot-chronos-bolt-small-btcusdt-1d-v1` | NO_DECISION (política PROPOSED) | pré-registrado antes do primeiro backtest (3c); **nenhuma execução nova** | **NO_DECISION** (`EVALUATED_PREREGISTERED`) | A previsão é `CANDIDATE_WORSE` e a estratégia `INSUFFICIENT_SAMPLE`. A política v1 APPROVED **não é retroativa**: a FM foi registrada em 2026-09-24T20:40:26Z, antes da vigência. Há ainda 1 seed < 5, DSR não computável e PBO N/A | 1 | `20260924T204649356492Z-9b6626234059` (3c) e `…802ddaa852be` |

Em todas as linhas, o status novo é igual ao anterior. A régua nova não promoveu nada, e a lógica garante
isso:
- sem artefato, o status é mantido;
- com artefato encontrado, a linha vira `REVIEW_REQUIRED` e a revisão fica humana;
- a H6 só sairia do status atual se o IC deixasse de cruzar zero **ou** o poder chegasse a 0,8, e mesmo
  assim para `REVIEW_REQUIRED`, nunca para uma promoção.

### Incompatibilidades entre o protocolo antigo e o novo (hipóteses abertas)

- **H7:**
  - usa `metric = psr` com o gate legado do `backtest_v3` (PSR ≥ 0,80, IC_lower > 0, DD < 20%, constantes
    no código), enquanto a v1 exige DSR ≥ 0,95 no pior N, PBO < 0,20, 5 seeds e 4 baselines;
  - foi registrada em 2026-09-04, antes da vigência da v1, então segue o critério pré-registrado dela;
  - o protocolo antigo não tinha spread explícito nem manifesto de execução.
- **H8:**
  - usa `metric = spearman_ic`, e a v1 é para estratégia (Sharpe/DSR/PBO), sem regra para hipótese de
    correlação. Uma decisão sob a v1 sairia sempre `NO_DECISION`, então uma v2 precisa de regra própria;
  - também foi registrada antes da vigência.

## Integridade experimental

| item | valor |
|---|---|
| novas variantes executadas em hipóteses NO-GO | **0** (nenhum backtest rodou no Prompt 4) |
| holdout acessado? | **NO** |
| pré-registros criados antes dos novos experimentos? | **N/A no Prompt 4** (nenhum experimento novo). **YES para a FM-3c**: pré-registro `c7ce6fe` (20:40:26Z) antes do código de avaliação `a86fc4c` e antes da primeira previsão |
| tentativas acrescentadas ao ledger | **nenhuma tentativa nova**. O ledger de execuções continua o do 3c (as 6 linhas preservadas) e ganhou só a execução de reavaliação (`STARTED` + `COMPLETED`); a cadeia de hash confere (`2026-09-25-prompt4/runs.jsonl`, sha256 `48c3b51d…`). Nenhuma tentativa foi apagada; `trials.json` (protegido) intocado |
| N_trials final | linhagem H1–H6: **LOWER_BOUND(32)**, N_upper ≈ 42 (Prompt 2). Todas as famílias: **LOWER_BOUND(36)** = 26 entradas do `trials.json` + 9 configurações documentadas e não registradas + a FM-3c; N_upper ≈ **46** (+ grade SL×TP 3×3 e H1-ETH) |
| sensibilidade do DSR | N = 36, 2N = 72, 5N = 180 e N_upper = 46: **todos N/A**. V[SR] não é estimável porque nenhuma entrada do `trials.json` tem `sharpe_basis`; `trial_sharpe_variance` recusa na primeira, `v1-direct-gemini-h7`. Sem V[SR] não há SR0, e um "DSR" seria PSR disfarçado |

## Holdout selado (item 5)

Registro durável e versionado: `docs/research_ledger/holdouts.jsonl` (sha256 `a4671956…`; cadeia de hash
confere). Operações em `research/holdout.py`.

| campo | valor |
|---|---|
| identificador | `cripto-holdout-btcusdt-20260926-20270326` |
| intervalo | [2026-09-26T00:00:00Z, 2027-03-26T00:00:00Z), uma janela **futura**: ninguém viu esses dados |
| universo | todos os dados de mercado do BTCUSDT (spot e perpétuo UM; qualquer frequência; preço, volume, funding e OI) no intervalo |
| selagem | 2026-09-25, linha `HOLDOUT_SEALED` (horário exato no ledger) |
| hash do conteúdo | ainda não existe (janela futura). A regra fixada: no fechamento, sha256 do JSON canônico dos candles diários spot do intervalo, gravado **uma vez** com `register_content_hash` antes de qualquer abertura. O código recusa gravar o hash antes do fim da janela |
| condições objetivas de abertura | (1) janela encerrada e hash gravado; (2) hipótese pré-registrada com o template completo, depois da vigência da v1 e antes da abertura, apontando este holdout; (3) período de desenvolvimento fora do intervalo (`assert_outside_holdouts`); (4) avaliação de desenvolvimento no ledger com GO pela política vigente; (5) aprovação humana do dono para a abertura (quem, quando, evidência); (6) uma única avaliação, sem ajuste depois |
| garantias no código | ID imutável; abertura única (a segunda é recusada); abertura sem aprovação, com hash divergente ou sem atestado de cada condição é recusada; desenvolvimento que toca o intervalo é recusado enquanto o holdout estiver selado |

A FM-3c não teve holdout: usou todo o período pós-corte. Isso fica registrado como lacuna do pré-registro
dela (abaixo).

## Pré-registro de hipóteses novas (item 4)

`research/preregistration.py` exige, antes do primeiro backtest e gravado no ledger:
- ID imutável, descrição e mecanismo esperado;
- features, target, período, universo e custos;
- protocolo de validação, métrica primária e métricas secundárias;
- política (id, versão e sha256);
- número máximo de variantes, seeds e holdout;
- critérios de GO, NO_GO e NO_DECISION.

`require_preregistered_before_run` recusa backtest sem registro, e um ID repetido é recusado.

O pré-registro da FM-3c foi feito com o template do Prompt 3c, antes deste. Contra o template do Prompt 4,
ele **não tem**:
- mecanismo esperado;
- número máximo de variantes (implícito: 1, porque "mudança exige pré-registro novo");
- holdout;
- critérios GO/NO_GO/NO_DECISION explícitos (o GO era delegado à política);
- sha256 da política.

Os demais campos existem com outros nomes (`test_prompt3c_preregistration_predates_the_prompt4_template`).
O pré-registro **não foi editado depois da execução**: ele fica como está, e a lacuna fica registrada aqui.

## Deduplicação (item 6)

**N/A nesta etapa**: nenhuma candidata nova. A ferramenta está pronta em `research/dedup.py`:
- compara pelo Spearman do core, só no período de desenvolvimento;
- devolve `REJECTED_REDUNDANT` se |ρ| ≥ limiar;
- registra candidata, fator mais semelhante, métrica, valor, período, limiar e a origem do limiar.

O limiar é argumento **obrigatório**, sem default. **A política v1 aprovada não tem limiar de redundância**, e
o 0,99 do prompt só vira regra numa v2 aprovada pelo dono.

A FM-3c não passou por deduplicação antes do backtest. Hoje também não daria: as séries dos fatores
existentes (sinais V3, scores LLM) não estão no PC 2. Fica registrado como **UNKNOWN**.

## Verificação

- **Testes novos:** `tests/test_evaluation_protocol_4.py`, 13 testes:
  - poder e MDE de Fisher à mão;
  - NO-GO sem artefato vira `NOT_REPRODUCIBLE` e mantém o status;
  - H6 como correlação, com status mantido;
  - agregado conclusivo vira `REVIEW_REQUIRED`, nunca promoção;
  - artefato encontrado exige revisão humana;
  - FM `NO_DECISION` por não retroatividade;
  - N_trials 36/46 e DSR N/A;
  - execução no ledger com a política APPROVED;
  - template de pré-registro, ID imutável e exigência antes do backtest;
  - lacunas do pré-registro do 3c;
  - holdout futuro sem hash nem abertura antecipada, com bloqueio do desenvolvimento;
  - holdout aberto uma vez só, com aprovação e conteúdo conferidos;
  - deduplicação.
- **Suíte completa isolada** (`pytest --cov` sob `env -i … unshare -rn`): **1771 passed, 0 failed**,
  33 warnings (os mesmos `ResourceWarning` de SQLite), 289 s, cobertura total 75%. Por módulo:
  `reevaluation.py` 97%, `holdout.py` 86%, `preregistration.py` 86%, `dedup.py` 83%. Log:
  `2026-09-25-prompt4/suite_isolated.log`.
- **Lint e tipos:** `ruff check`/`format` limpos; **pyright 1.1.411: 0 errors**, rodado localmente.
- **Ordem:** código e protocolo commitados em `98c9e92` **antes** da execução (inventário, selagem e
  reavaliação às 16:07Z).

## Correção de uma falha do Prompt 3c

O `.gitignore` ignora `*.jsonl`, e o `git add` da pasta de evidência do 3c pulou o `runs.jsonl` sem aviso.
Resultado: o relatório do 3c (PR #131, já no `main`) cita o ledger de execuções (sha256 `cb0af383…`), mas o
arquivo não foi versionado. Esta PR corrige em commit próprio:
- adiciona negações explícitas no `.gitignore` para `docs/evidence/**/*.jsonl` e
  `docs/research_ledger/*.jsonl`;
- versiona o arquivo com o mesmo conteúdo gerado em 2026-09-24 (sha256 conferido).

## Conclusão

**PROVEN**
- Nenhum status mudou e nenhuma hipótese virou GO; 0 variantes; holdout não acessado.
- Os artefatos necessários para reaplicar a régua nova a H1–H5, H7–H9, à grade e à v1 não existem no PC 2
  (inventário com hash).
- A H6 continua sem poder para distinguir ρ = 0,2 de zero.
- A política v1 está APPROVED e não retroage.
- O DSR histórico não é estimável.

**DECLARED**
- O poder de 0,233 da H6 por bootstrap em blocos (tabela B12, n_referencia = 60; a errata cita 23% em
  n = 84).
- A contagem de 9 configurações não registradas e o N_upper (Prompt 2, a partir de docs).
- O status CANDIDATE_ONLY da grade (`docs/HYPOTHESES.md`).

**UNKNOWN**
- Se os dados de produção do PC 1 (banco de previsões, CSVs V3, `returns.json`) permitiriam reproduzir
  H1–H9.
- O risco de vazamento do rótulo legado da H6 a partir de `pred_price` (Prompt 2), que não dá para
  verificar sem os pares.
- A deduplicação da FM-3c contra os fatores existentes.

**Limitações de reprodutibilidade**
- Todas as reavaliações completas dependem de dados que estão fora deste PC.
- Trazê-los exige decisão do dono (fonte, hash e janela registrada), e o uso tem de ser exatamente a
  configuração e a janela originais. Qualquer outra coisa seria variante.
