# 2026-09-28 — B4 item 7: controle do H7/H9 — resultado

**Pergunta** (`docs/HYPOTHESES.md`, B4, item 7): o `Sharpe = −1,0041` do H9 vem da covariável OI/volume ou do período e do harness? A resposta decide se vale ativar a H7, que usa o mesmo mecanismo `extra_features`.

**Autorização e protocolo:** autorizado pelo dono em 2026-09-28. O protocolo é `protocol.md`, publicado antes de qualquer download (`b21942f`). As emendas 1 (`66f7dbe`) e 2 (`0414a13`) foram publicadas antes das execuções que corrigem.

## Resposta curta

**Nos dados públicos reconstruídos, a covariável é inocente, e o harness não tem poder para responder à pergunta.**

- O braço A, sem covariável, e o braço B, com a covariável do H9, dão praticamente o mesmo resultado.
- Os dois braços têm **1 fold avaliável em 45**.
- O NO-GO do H9 mediu a escassez de sinais do pipeline V3 no BTCUSDT, não o crowding.
- Isso é coerente com a errata que fechou o H9 como `CLOSED_INSUFFICIENT_SAMPLE`.

## Resultados

Números extraídos dos logs por `extract_results.py` (detalhe em `results.json`, com sha256 de cada log):

| execução | braço | vetores | folds (avaliáveis) | Sharpe | PSR | IC [CI_lower] | MaxDD | erro |
|---|---|--:|--:|--:|--:|--:|--:|---|
| `h9-e3ee0af` | A_baseline | 6096 | 45 (1) | -0.9414 | 0.169 | 0.0683 [-0.1021] | 9.9% |  |
| `h9-e3ee0af` | B_oivol | 6096 | 45 (1) | -0.922 | 0.1779 | 0.0644 [-0.1195] | 14.33% |  |
| `h9-e3ee0af-repeticao` | A_baseline | 6096 | 45 (1) | -0.9414 | 0.169 | 0.0683 [-0.1021] | 9.9% |  |
| `h9-e3ee0af-repeticao` | B_oivol | 6096 | 45 (1) | -0.922 | 0.1779 | 0.0644 [-0.1195] | 14.33% |  |
| `h9-e3ee0af-tentativa1` | A/B | 0 | - | - | - | - | - | 0 vetores (emenda 2) |
| `main-905ab7a` | A/B | 0 | - | - | - | - | - | 0 vetores (emenda 1) |
| H9 (2026-09-04, produção) | B | - | 45 (1) | -1.0041 | 0.1621 | 0.0283 [-0.1476] | 11.49% | |

**Status dos folds, iguais nos dois braços** (`fold_status_counts`):
- 44 `INSUFFICIENT_DATA`, dos quais 17 sem nenhum sinal ativo no OOS;
- 1 `NO-GO`, o fold 3 (fim de 2021), com IC de 0,0242 [−0,4369, 0,4878] no braço A e −0,0107 [−0,5714, 0,3297] no braço B.

## Validade: a reprodução do H9 não é exata

O braço B chega **perto** do H9 (mesma estrutura, 45 folds com 1 avaliável, e Sharpe −0,92 contra −1,00), mas não o reproduz exatamente.

A execução é **determinística**: a repetição deu números idênticos. Então a diferença vem dos dados ou do ambiente, não de aleatoriedade:

- funding e klines vão até 2026-08-31 aqui, porque o Vision só publica o mês fechado; na produção iam até 2026-09-03;
- a produção tinha dados coletados via REST nos meses recentes;
- o sistema operacional e as versões de bibliotecas também diferem.

Como o protocolo manda, a leitura abaixo vale para **os dados públicos reconstruídos**. Ela não confirma nem refuta o número específico de −1,0041.

## Leitura (tabela do runbook, definida antes do dado)

| Resultado previsto | Observado |
|---|---|
| **A ≈ B ≈ −1,0** → a covariável é inocente; o −1,0 vem do período ou do harness | **sim:** A = −0,9414 e B = −0,9220 na mesma janela |
| A ≈ 0 e B ≈ −1,0 → a covariável exógena degrada | não |
| A pior que B → inesperado | por 0,02 de Sharpe; é ruído diante de 1 fold avaliável |

**Implicação para a H7:** ativá-la neste harness, com o mesmo mecanismo, tende a produzir outro veredito sem informação. O limite é a escassez de sinais, não a covariável.

A recomendação do próprio B4 era rodar este controle antes da coleta da H7. A resposta é que o problema a resolver antes está no desenho: poucos sinais ativos por fold. É decisão do dono; nada foi alterado aqui.

## Achados de infraestrutura (não corrigidos: é código do domínio fora dos `adapter_paths`)

1. **O `backtest_v3` do `main` não roda sobre dados do próprio `vision_ingest`.**
   - Desde `9d89871` (2026-09-10), o `feature_builder` exige cadência exata de 8 h no funding.
   - Os instantes do `fundingRate` do Vision têm ruído de milissegundos (`2021-01-01T00:00:00.002Z` em `data_manifest.json`).
   - Resultado: 6.118 de 6.207 instantes descartados e 0 vetores (`run_logs/main-905ab7a/`).
   - Se o data lake de produção ainda for alimentado pelo `vision_ingest`, o `backtest_v3` atual deve falhar lá também. Isso **não foi verificado** na produção.
   - Correção possível, decisão do dono: normalizar o instante de funding no importador ou tolerar o ruído na checagem de cadência.
2. **O CSV de preços mudou de nome** (`spot_1h.csv` → `spot_binance_1h.csv`, em `9d89871`). Um harness antigo sobre um data lake novo lê um índice vazio sem erro claro (`run_logs/h9-e3ee0af-tentativa1/`).

## O que isto não é

- Não reabre o H9 nem reparametriza a família congelada.
- Não registra trial: o sha256 do `trials.json` é igual antes e depois em cada `controle_checks.txt`.
- Não toca o holdout selado: os dados terminam em 2026-09-03, antes de 2026-09-26.
- Não autoriza capital.
- Ledger: o de runtime do `backtest_v3` (`CRIPTO_RUN_LEDGER`) só existe no código do `main`; a tentativa `main-905ab7a` gravou `STARTED` → `CRASHED` em `run_logs/main-905ab7a/runs.jsonl`. O harness `e3ee0af` é anterior a esse ledger e não grava nenhum. O `docs/research_ledger/runs.jsonl` versionado não foi tocado.

## Arquivos

- `protocol.md`: protocolo e emendas 1 e 2.
- `data_manifest.json`: CSVs (linhas, intervalo, sha256) e os 2.208 arquivos do Vision (2.072 de metrics, 68 de fundingRate, 68 de klines), todos conferidos contra o `.CHECKSUM` publicado.
- `run_logs/`: `vision_ingest.log` e as quatro execuções (`main-905ab7a`, `h9-e3ee0af-tentativa1`, `h9-e3ee0af`, `h9-e3ee0af-repeticao`), cada uma com os logs dos dois braços e `controle_checks.txt`; a do `main` traz também o ledger de runtime.
- `extract_results.py`, `results.json`, `results_table.md`, `data_manifest.py`.
- **Código:**
  - harness do H9 `e3ee0afc37f1e42a1a44fcaf95e1e9ced976735b`, venv do `uv.lock` daquele commit (Python 3.13.15, predictor-core 3.0.0, hmmlearn 0.3.3);
  - importador `vision_ingest` do `main` `905ab7a`.
- **Ambiente:** PC 2 do dono, WSL Ubuntu 24.04.
