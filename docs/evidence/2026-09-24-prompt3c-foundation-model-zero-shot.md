# 2026-09-24 — Prompt 3c: foundation model zero-shot (Chronos) e execução real

Base: Prompts 3a e 3b, já no `main` (`2ce361d`). Branch `research/cripto-prompt3c-20260924`. Classificação:
**PROVEN** = constatado nesta sessão; **DECLARED** = só em doc ou metadado de terceiro; **UNKNOWN** = indeterminado.

## Resultado em uma linha

Com pré-registro, só em dias posteriores à publicação dos pesos (650 dias), o **Chronos-Bolt-Small
zero-shot prevê a distribuição do retorno diário do BTC PIOR que os baselines ingênuos**: perda
quantílica média 12% maior, Diebold-Mariano p < 1e-10 contra os dois, com poder suficiente
(`CANDIDATE_WORSE`). A estratégia derivada tem Sharpe líquido anual de 0,08, mas a amostra só detectaria
Sharpe ≥ 2,1 (`INSUFFICIENT_SAMPLE`). Decisão: **`NO_DECISION`**.

## Ordem dos fatos (o que garante que nada foi escolhido depois de ver o resultado)

| quando (UTC) | commit / run | o quê |
|---|---|---|
| 20:40:26 | `c7ce6fe` (publicado no GitHub) | pré-registro `2026-09-24-prompt3c/preregistro.json` (sha256 `15b13769…`): modelo, revisão, hashes, dados, corte, período, horizonte, contexto, quantis, baselines, métricas, teste, efeito relevante, poder, regra da estratégia, custos, DSR/PBO |
| 20:45:56 | `a86fc4c` (publicado) | código de avaliação e 15 testes com dados **sintéticos**, antes de qualquer previsão real |
| 20:46:12 | run `20260924T204612256753Z-5c0bf8c01bcd` | previsão 1 (código `a86fc4c`, árvore limpa) |
| 20:46:26 | run `20260924T204626428505Z-6186ac7e9731` | previsão 2: conteúdo **idêntico** (`forecasts_body_sha256 812753cc…`) |
| 20:46:49 | run `20260924T204649356492Z-9b6626234059` | avaliação (código `a86fc4c`) |

Depois do resultado, nenhum código de avaliação mudou. Só entraram este relatório, os artefatos e um
diagnóstico **descritivo pós-hoc** rotulado como tal.

## 1. Foundation model: verificação

| item | valor | classificação |
|---|---|---|
| modelo | `amazon/chronos-bolt-small`: prevê diretamente os 9 quantis 0,1..0,9, com contexto máximo de 2048 (`config.json`, PROVEN). Os "48M parâmetros" vêm do model card (DECLARED) | PROVEN / DECLARED |
| revisão fixada | `772f3d25d38aec6d914c8949dab4462e2d46f5d8` | PROVEN (API do HF) |
| pesos | `model.safetensors` sha256 `06a6a19b…a21dd` = oid LFS publicado na revisão fixada **e** no commit inicial `0e96a1377adca89eebae3bbde4f859dc3b9f4b46` (2024-11-13T13:28:57Z). Os commits seguintes só mudam o README | PROVEN (API tree do HF + sha256 local) |
| config | sha256 `9ca0ebbe…`; blob git `d8f9b655…`, igual nas duas revisões | PROVEN |
| data pública | repositório criado em 2024-11-25T09:46:10Z (`createdAt`) | PROVEN (API do HF) |
| licença do checkpoint | `apache-2.0` no front matter do model card da revisão fixada e na tag `license:apache-2.0` | PROVEN (lido hoje) |
| licença do código | Apache-2.0 (`chronos-forecasting` 2.3.2 no PyPI; LICENSE do `amazon-science/chronos-forecasting`) | PROVEN (lido hoje) |
| origem | os arquivos já estavam em `~/predictors/tools/hf/models/amazon--chronos-bolt-small` (baixados por outra missão, com `SHA256SUMS`). **Nada foi baixado nesta sessão**: pesos locais, pacotes vindos do cache do uv (`--offline`) e dados já versionados no repositório | PROVEN |
| ambiente | venv separado `~/predictors/runtime/cripto/venv-chronos`: `chronos-forecasting 2.3.2`, `torch 2.14.0+cpu`, `transformers 5.17.0`, CPU, rede desligada (`unshare -rn`, `HF_HUB_OFFLINE=1`). Licenças dos pacotes: Apache-2.0 (chronos, transformers, accelerate, safetensors, tokenizers, huggingface-hub), BSD/MIT (torch, numpy, pandas, einops) | PROVEN |
| dependência do projeto | **nenhuma nova**: chronos e torch ficam fora do `pyproject`/`uv.lock`. A avaliação usa só stdlib e o core | PROVEN |

Por que o *small* e não o *tiny*: os dois são Apache-2.0 e rodam em CPU (cerca de 14 s para 650
previsões com o small). O small já estava no disco com o hash conferido; o tiny exigiria download.
Chronos-2 e outros modelos citados em documentos anteriores **não** foram usados.

## 2. Contaminação de pré-treino

- **Corte:** 2024-11-25T09:46:10Z, a data pública do repositório. É posterior ao commit dos pesos, então é o
  corte conservador.
- **Avaliação só com alvos após o corte:** primeiro alvo 2024-11-26, último 2026-09-06 (fim dos dados locais).
  O contexto pode ser anterior ao corte, porque o risco de contaminação está no alvo, não no contexto.
- **Tamanho da amostra pós-corte:** **n = 650 dias**. Status de contaminação: `POST_CUTOFF` (avaliação limpa
  quanto ao pré-treino).
- **Poder:**
  - *Previsão.* O MDE relativo (α = 0,05, poder 0,8) é **4,85%**, abaixo do efeito relevante de 5%. A
    amostra basta para a conclusão de previsão.
  - *Estratégia.* O MDE do Sharpe anual é **2,10**, acima do relevante (1,0), então fica
    `INSUFFICIENT_SAMPLE`. Nenhuma conclusão de estratégia é possível com 650 dias.

## 3. Métricas de previsão probabilística

Implementação local pequena e testada (`research/forecast_metrics.py`). A biblioteca `fev` não foi usada:
não está instalada, exigiria dependência nova, e a métrica é uma fórmula de poucas linhas.

| métrica | fórmula / referência | teste que prova |
|---|---|---|
| perda pinball | ρ_τ(y,q) = (y−q)(τ − 1{y<q}). Koenker & Bassett (1978) | `test_pinball_and_crps_by_hand` |
| mean_quantile_loss (primária) | média de ρ_τ nos 9 níveis 0,1..0,9 | idem |
| CRPS_q9 | 2 × mean_quantile_loss: aproximação de CRPS = 2∫ρ_τ dτ (Gneiting & Raftery 2007). Ignora as caudas além de 0,1 e 0,9 | `test_crps_gaussian_closed_form_and_quantile_approximation`: com 999 quantis, bate com o CRPS fechado da normal (rel 5e-3); CRPS(N(0,1), 0) = (√2−1)/√π |
| WQL | Σ 2ρ / (K·Σ\|y\|) (Ansari et al. 2024, Chronos) | `test_pinball_and_crps_by_hand` (0,6 à mão) |
| Diebold-Mariano | com correção HLN, do `predictor_core` (h = 1) | core (já testado lá) |
| quantil empírico | tipo 7 (Hyndman & Fan 1996) | `test_empirical_quantile_is_hyndman_fan_type_7` (= `statistics.quantiles` inclusive) |

## 4. Execução real

**a. Suíte relevante, isolada de rede e segredos:**
- **Suíte completa:** `pytest --cov` sob `env -i … unshare -rn`, **1757 passed, 0 failed**, 33 warnings (os
  mesmos `ResourceWarning` de SQLite), 322 s, cobertura total 75%. `fm_zero_shot.py` 90%,
  `forecast_metrics.py` 80%. Log: `2026-09-24-prompt3c/suite_isolated.log` (sha256 `55bf24be…`).
- **Testes novos:** 15, em `tests/test_evaluation_protocol_3c.py`. Cobrem:
  - métricas à mão e contra o CRPS fechado da normal;
  - quantil tipo 7;
  - hash dos dados reais e recusa de adulteração;
  - lacunas;
  - corte de contaminação e `POTENTIALLY_CONTAMINATED`;
  - baselines que usam só o passado;
  - contabilidade da estratégia à mão;
  - fórmulas de poder;
  - constantes transcritas do pré-registro;
  - avaliação ponta a ponta sem GO;
  - recusa de previsão de outro checkpoint ou com dia faltando;
  - ledger com `COMPLETED` e `CRASHED`.
- **Lint e tipos:** `ruff check`/`format` limpos. **pyright 1.1.411: 0 errors**, rodado localmente.

**b. Dados:** só locais e versionados.
- Arquivo: `docs/continuity_20260909/data-20260907-altcoins-altcoin-data.zip` (sha256 `cbb34177…`).
- Membro: `…/pairs/BTCUSDT.json.gz` (sha256 `f055de92…`).
- Conteúdo: BTCUSDT spot diário da Binance, de 2020-10-01 a 2026-09-06, 2167 linhas, sem lacunas nem
  duplicatas (conferido no carregamento).
- Os closes são idênticos aos da outra fonte versionada (`carry-research-data/BTCUSDT_spot_daily`) nos 1011
  dias em comum.
- Nenhum download de dado.

**c. Período:** fixado no pré-registro antes de qualquer previsão. Não foi alterado.

**d. Ledger:** `2026-09-24-prompt3c/runs.jsonl` (sha256 `cb0af383…`) guarda as 3 execuções, cada uma com
`STARTED` e `COMPLETED`. Nenhuma falhou. A cadeia de hash confere. A 2ª previsão tem `attempt = 2` (mesma
config).

### Tabela comparável

Período: alvos de 2024-11-26 a 2026-09-06 (650 dias, pós-corte). Protocolo: previsão 1 dia à frente,
origem no close do dia t; o contexto do Chronos são os últimos ≤ 2048 closes; os baselines usam os
últimos 365 log-retornos. Custos: taker 10 + slippage 5 bps por perna, spread 0 (CostSpec padrão), cobrados
em cada mudança de posição e na liquidação final. Sharpe líquido: por dia, base
`per_decision_unannualized_sample_std`, com o anualizado (√365) entre parênteses. Avaliação:
`20260924T204649356492Z-9b6626234059`.

| candidato | protocolo | período | custos | métrica de forecast (MQL · CRPS_q9 · WQL) | Sharpe líquido | max DD | turnover | PSR | DSR (pior caso) | PBO | decision | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **chronos_bolt_small** (regra comprado/fora pela mediana) | zero-shot, h=1d | 650 d pós-corte | 10+5 bps/perna | **0,007347 · 0,014694 · 0,9120** | 0,00417 (0,080) | 42,9% | 0,166 | 0,542 | N/A (V[SR] não estimável) | N/A | **NO_DECISION** | previsão `…204612…-5c0bf8c01bcd`, avaliação `…204649…-9b6626234059` |
| historical_quantiles_365 (baseline de previsão) | quantis empíricos, 365 d | idem | N/A | **0,006557** · 0,013114 · 0,8139 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | `…204649…-9b6626234059` |
| gaussian_random_walk_365 (baseline de previsão) | N(0, s²), 365 d | idem | N/A | 0,006631 · 0,013262 · 0,8232 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | idem |
| random_walk (sempre fora) | — | idem | 10+5 bps/perna | N/A | N/A (0/0; 0 por convenção na decisão) | 0% | 0 | N/A | N/A | N/A | N/A | idem |
| naive_persistence (comprado se r_t > 0) | — | idem | idem | N/A | −0,05532 (−1,057) | 50,7% | 0,502 | 0,084 | N/A | N/A | N/A | idem |
| always_long = buy_and_hold | — | idem | idem | N/A | 0,00134 (0,026) | 53,0% | 0,0031 | 0,514 | N/A | N/A | N/A | idem |

Retorno líquido acumulado no período: Chronos −3,0%; sempre comprado −13,9%; persistência −43,8%; sempre
fora 0%.

**Testes de previsão (Diebold-Mariano HLN, perda do Chronos − perda do baseline):**
- contra `historical_quantiles_365`: DM = +6,96, p = 8,4e-12;
- contra `gaussian_random_walk_365`: DM = +6,74, p = 3,5e-11.

O Chronos tem perda **maior** que os dois. Status: **`CANDIDATE_WORSE`**, com MDE de 4,85% (< 5%).

### N_trials, sensibilidade do DSR e política

- **N_trials:** o ledger histórico continua `LOWER_BOUND(32)` com `N_upper ≈ 42` (Prompt 2). Esta avaliação é
  uma tentativa nova, de outra família (baseline de foundation model), registrada no ledger de execuções.
  Pela contagem conservadora, o N passa a ser pelo menos 33.
- **DSR:** **não estimável**. O `trials.json` não tem nenhum Sharpe com `sharpe_basis` (`trial_sharpe_variance`
  levanta na primeira entrada, `v1-direct-gemini-h7`). A sensibilidade N=32, 64, 160 e N_upper=42 fica
  **toda N/A**: sem V[SR] não há SR0, e um "DSR" seria PSR disfarçado. O PSR bruto (0,542) está na tabela
  só como PSR.
- **PBO:** N/A. Havia uma única configuração pré-registrada, sem seleção entre configurações.
- **Política:** `cripto-decision-policy` v1, sha256 `f2c482b7…`, status **PROPOSED**. Motivos do
  `NO_DECISION` registrados na decisão:
  - política não aprovada;
  - 1 seed avaliada, contra as 5 exigidas;
  - DSR não computável (cenários N, 2N e 5N ausentes);
  - PBO não computado.

  Observação para o dono: o Chronos-Bolt é determinístico, então o critério de 5 seeds da v1 nunca se
  aplica a ele. Se o dono quiser avaliar modelos determinísticos, isso pede uma regra própria numa v2.

## Diagnóstico descritivo (PÓS-HOC, não pré-registrado; não muda nenhum status)

`2026-09-24-prompt3c/post_hoc_diagnostics.py` e `.json`, calculado sobre `forecasts_run1.json` (sha256
`5c18b677…`; a previsão 2, com `run_id` diferente, tem o mesmo corpo, `812753cc…`). As licenças dos pacotes
estão em `runtime_licenses.txt`.

| previsor | cobertura do intervalo 10–90% (nominal 80%) | largura média 10–90% (log-ret) |
|---|---|---|
| chronos_bolt_small | **91,4%** | **0,0812** |
| historical_quantiles_365 | 82,5% | 0,0551 |
| gaussian_random_walk_365 | 86,8% | 0,0619 |

Leitura, estritamente sobre esses números: as previsões do Chronos são **largas demais** (subconfiantes)
para o retorno diário do BTC no período. Isso explica a maior parte da perda quantílica pior. A mediana dele
fica perto de zero (média 8e-7), como a dos baselines.

## Interpretação (só o que os resultados sustentam)

- **Previsão probabilística:** no BTCUSDT diário, pós-corte, o Chronos-Bolt-Small zero-shot é
  significativamente **pior** que um passeio aleatório com ruído empírico de 365 dias. O resultado é negativo
  e tem poder adequado.
- **Estratégia:** a regra comprado/fora pela mediana perdeu menos que o sempre comprado num período em que o
  BTC caiu (−3,0% contra −13,9%). Mas o Sharpe anual de 0,08 está muito abaixo do detectável (2,1). Isso
  **não** é evidência de valor; o status é `INSUFFICIENT_SAMPLE`.
- **Nada aqui é GO.** Não foram testadas variantes (outro checkpoint, horizonte, contexto ou calibração).
  Qualquer uma delas seria tentativa nova, com pré-registro novo.

## Limitações

- Um ativo, um horizonte (1 dia), uma frequência (diária). O resultado não generaliza para o V3 (8 h,
  funding/OI), cujos dados não estão no PC 2.
- CRPS_q9 é aproximação com 9 quantis e ignora as caudas.
- O corte usa a data pública dos pesos. A data real de corte do corpus de treino é **UNKNOWN**; ela é anterior
  ou igual à dos pesos, então o corte adotado é seguro.
- Os pesos vieram de uma cópia local feita por outra missão. A integridade foi conferida contra o oid LFS
  publicado, mas o download em si não foi feito nesta sessão.
- O DSR não é estimável até que os Sharpes das tentativas sejam recomputados numa base única.
