"""Ledgers de pesquisa versionados: um lugar só para os caminhos.

`docs/research_ledger/` guarda, no git e encadeados por hash (`run_ledger.RunLedger`):
  runs.jsonl              execuções de pesquisa pré-registrada (previsão, avaliação, reavaliação),
                          inclusive as que falharam; continua o ledger dos Prompts 3c e 4
  preregistrations.jsonl  pré-registros de hipóteses novas, gravados antes do primeiro backtest
  holdouts.jsonl          holdouts selados, hashes de conteúdo e aberturas

As pastas `docs/evidence/<data>-promptN/` guardam cópias congeladas do ledger no momento de cada
relatório. O ledger de runtime do `backtest_v3` (`CRIPTO_RUN_LEDGER` ou
`<data>/research_ledger/runs.jsonl`) é outro: registra execuções operacionais e ad hoc do WFA.

Os caminhos só existem num checkout do repositório; a wheel não leva `docs/`.
"""

from __future__ import annotations

from pathlib import Path

RESEARCH_LEDGER_DIR = Path(__file__).resolve().parents[2] / "docs" / "research_ledger"
RUNS = RESEARCH_LEDGER_DIR / "runs.jsonl"
PREREGISTRATIONS = RESEARCH_LEDGER_DIR / "preregistrations.jsonl"
HOLDOUTS = RESEARCH_LEDGER_DIR / "holdouts.jsonl"
