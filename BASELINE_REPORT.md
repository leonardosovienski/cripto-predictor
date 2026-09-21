# External Intelligence V1 — baseline report

Checked on 2026-09-21 before the implementation patch. Preparation SHAs were re-resolved; no
assumption from the mission was treated as current authority without inspection.

| Repository | Initial branch | Initial SHA | Initial tree | Baseline result |
|---|---|---|---|---|
| cripto-predictor | `main` | `002ed71d36c631955072c1f52a0dd00097a78b30` | clean | Full collection initially blocked by missing installed cross-project packages. With source-pinned `PYTHONPATH`, all tests except the two files requiring the absent `cain.research_results` module were runnable. |
| core-predictor | `main` | `9bf43efe92459a0b484cac00f51170b2c70d420f` | clean | `278 passed` |
| predictor-ops | `main` | `b19e69527c0fda5cb1f96281d3a984fea1431768` | clean | `86 passed, 1 failed`; preexisting Windows timeout/truncation failure in `tests_v2/test_runner.py::test_timeout_and_truncation`. |
| ecosystem-predictor | `main` | `a879525c49f1b3ac2050a3a70b10a322501b1e56` | clean | `186 passed` across ecosystem and transport packages. |
| cain | detached HEAD | `24f784c5dde1fa66c262ad5899f4fd8d02526adf` | dirty, 14 preexisting paths | Diverged from preparation SHA `5fe340a...`. Its venv has no pytest; fallback collection has 25 missing-FastAPI errors. No CAIN file was changed. |

## Commands and receipts

| Check | Command/result | Exit |
|---|---|---:|
| CRIPTO initial tests | `.venv/Scripts/python.exe -m pytest -q` — four collection errors: missing `research_protocol` and `cain` | 1 |
| CRIPTO source-pinned tests | full suite attempt — two collection errors because current CAIN has no `cain.research_results` | 1 |
| CRIPTO remaining suite | same source-pinned environment with `test_research_execution.py` and `test_research_recovery.py` explicitly excluded — `1615 passed, 1 skipped` | 0 |
| CORE tests | CRIPTO managed Python, `PYTHONPATH=core/src`, `pytest -q` — `278 passed` | 0 |
| OPS tests | OPS venv, `pytest -q` — `86 passed, 1 failed` | 1 |
| ECOSYSTEM tests | source-pinned ecosystem packages, `pytest` — `186 passed` | 0 |
| CAIN venv | `C:/CAIN/.venv/Scripts/python.exe -m pytest -q` — pytest absent | 1 |
| CAIN fallback | CRIPTO managed Python with CAIN source — 25 collection errors, FastAPI absent | 1 |

`uv` is not available on the host PATH. The already-installed project virtual environments and
source-pinned package roots were used instead; no production database or installation was mutated.

## Existing mechanisms verified

- CORE: `predictor_core.kernel.net` supplies HTTP client/retry; `predictor_core.kernel.infra`
  supplies WAL, busy timeout, foreign keys and idempotent migrations. CORE remains domain-neutral.
- CRIPTO: Opportunity Radar emits immutable `OpportunitySignal`; the canonical Feature Store is
  separate; `profit_recovery_v1` already owns causal ledger clocks; research admission/execution
  already resolves hash-pinned references and delegates deterministic execution to OPS.
- OPS: `JobConfig`, `run_job`, runtime roots, locks, heartbeat, expected artifacts and terminal
  receipts already exist and are reused.
- ECOSYSTEM: `ResearchBundleV1`, `ResearchTaskV1` and `ResearchResultV1` cover the required transport
  and immutable-reference semantics; no new shared schema is justified.
- CAIN: bundle restrictions already distinguish read from generate; CAIN does not need direct access
  to the CRIPTO SQLite database.

## Baseline classification

`BASELINE_STATUS = PARTIAL_PREEXISTING_FAILURES`

The known red checks are environment/current-checkout failures and the isolated OPS test above. They
were preserved, not reclassified as regressions and not fixed because none blocks the isolated CRIPTO
implementation.
