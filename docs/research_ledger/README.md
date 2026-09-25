# Ledgers de pesquisa (versionados, append-only)

Os caminhos ficam em `GarimpoInvestimentos/research/ledgers.py`. Cada linha é encadeada pela anterior
(`prev_sha256`/`record_sha256`); confira com `RunLedger(<arquivo>).verify_chain()`. **Nunca edite nem apague
linhas**: correções entram como linhas novas.

| arquivo | o que registra | quem escreve |
|---|---|---|
| `runs.jsonl` | Execuções de pesquisa pré-registrada, inclusive as que falharam (`STARTED` → `COMPLETED`/`CRASHED`), e eventos `DECISION` (política com id, versão e sha256, a execução e a decisão, no mesmo registro). Começa com as execuções dos Prompts 3c e 4 | `run_ledger.recorded_run` e `decision_policy.record_decision`; hoje `research/fm_zero_shot.py` (padrão do `--ledger`) e `research/reevaluation.py` |
| `preregistrations.jsonl` | Pré-registros de hipóteses **novas** (template do Prompt 4), gravados antes do primeiro backtest. Cada ID é imutável e conta como tentativa no N do DSR | `research/preregistration.register_preregistration` |
| `holdouts.jsonl` | Holdouts selados, hash do conteúdo e abertura única com aprovação humana | `research/holdout.py` |

## Regras

- **Nova hipótese:**
  1. pré-registre com `register_preregistration(RunLedger(ledgers.PREREGISTRATIONS), doc, holdouts=RunLedger(ledgers.HOLDOUTS))`;
  2. o período de desenvolvimento não pode tocar holdout selado;
  3. antes do primeiro backtest, chame `require_preregistered_before_run`;
  4. grave as execuções em `runs.jsonl`.
- **Avaliação num intervalo de holdout selado e não aberto é recusada** (`fm_zero_shot.run_evaluation`, e o
  `CRASHED` fica registrado). Abrir exige aprovação humana registrada e acontece uma única vez.
- **N de tentativas para o DSR:** `trials.json` (protegido) + configurações documentadas e não registradas
  (Prompt 2) + FM-3c + os pré-registros deste ledger (`reevaluation.n_trials_summary` soma sozinho).
- **Cópias congeladas:** as pastas `docs/evidence/<data>-promptN/` guardam o ledger como estava em cada
  relatório; o arquivo vivo é o daqui.
- **Não confunda com o ledger de runtime do `backtest_v3`** (`CRIPTO_RUN_LEDGER` ou
  `<data>/research_ledger/runs.jsonl`), que registra execuções operacionais e ad hoc do WFA e não é versionado.

## Estado em 2026-09-25

- **Holdout selado:** `cripto-holdout-btcusdt-20260926-20270326`, com os dados de mercado do BTCUSDT de
  2026-09-26 a 2027-03-26.
- **Conflito em aberto:** o universo do selo cobre também a coleta prospectiva de H7 e H8, que estão
  `REGISTERED_NOT_ACTIVATED`. Se forem ativadas, o dado novo delas cai no intervalo selado. **Decisão do dono**:
  (a) ativá-las só depois da janela; (b) excluir a coleta prospectiva delas do selo, numa linha de emenda; ou
  (c) retirar o selo antes do início e selar outra janela.
