# Offline research toolkit

Five opt-in capabilities share a JSON workflow: universe filters, factor diagnostics,
interval-aware validation, synthetic spot order accounting and immutable experiment runs.
The production pipeline, scientific trials and frozen observers are not modified.

```powershell
C:\Cripto\CRIPTO.cmd python -m GarimpoInvestimentos.research demo --store C:\Cripto\operacao\relatorios\research-runs
C:\Cripto\CRIPTO.cmd python -m GarimpoInvestimentos.research run --input C:\Cripto\input.json --store C:\Cripto\operacao\relatorios\research-runs
```

The installed CLI also accepts `cripto-predictor research ...`. `list`, `verify` and
`compare LEFT RIGHT` use the same `--store`. Run IDs are unique; reuse is rejected.
Copy a demo run's `config.json` to start a new input. Keep each input's economic and
temporal interpretation explicit. All output records have `economic_validation=false`.

## Input contract

Top-level keys are optional `panel`, `universe`, `validation`, `scenario`; at least
one is required. The demo contains a runnable example of every component.

* `panel`: rows with integer `date`, nonempty `asset`, finite numeric `factor` and
  supplied `label`; optional explicit `group`. `quantiles` defaults to 5 and
  `group_adjust` to false. Adjustment demeans **labels**, not factors, within each
  date/group. Average-rank ties stay together, so bins may be empty. Quantile means
  are descriptive equal-weight label means, not cost-adjusted strategy returns.
  Turnover is new/current members (Alphalens convention), not transaction volume.
* `universe`: rows require `instrument_id` and integer `known_at`; rules have
  `field`, `operation` (`eq`, `min`, `max`, `not_in`) and `value`. Supply `cutoff`,
  optionally `sort_field` and `limit`. Sorting requires a common explicit
  `<sort_field>_unit`; quote currencies never alias. Classification is explicit;
  no stable/wrapped inference by ticker. `known_at` is a received-version clock,
  not historical listing proof. Missing fields are rejected with reasons.
* `validation`: labels have integer `start`, `end`, `available`; windows are ordered
  disjoint half-open `[start,end)` pairs. Training label intervals are closed;
  end must be strictly before test start minus nonnegative time `gap`, and label
  availability strictly before test start. This is forward-only, not CPCV.
  No post-test embargo is necessary because future training is excluded entirely.
* `scenario`: requires `synthetic=true`, explicit balances and spot contracts,
  followed by `submit`, `fill`, `cancel` events. Quantities/prices/fees use decimal
  strings. Fills are imposed inputs; no fills inferred from market data. Capital
  is reserved by venue and asset; fee currency is explicitly quote. No margin,
  derivatives, price impact, queue, cash transfers or venue rounding is modeled.

The four analysis outputs are independent: universe selection does not silently
filter the factor panel. This avoids retrospectively selecting factor observations.
The run store binds config, metrics, results, input hashes and implementation hash.
A completed run is identified by its manifest; interruption before that leaves an
incomplete directory, never a completed run. Hashes detect changes relative to the
manifest; they are not digital signatures against an attacker replacing everything.

## Python API

```python
from GarimpoInvestimentos.research.factors import analyze_panel, residualize
from GarimpoInvestimentos.research.universe import Rule, select_universe
from GarimpoInvestimentos.research.validation import LabelInterval, walk_forward
from GarimpoInvestimentos.research.simulation import ScenarioLedger, SpotContract
from GarimpoInvestimentos.research.registry import RunStore
```

`residualize(y, exposures)` performs OLS with intercept and rejects collinearity.
It uses NumPy from the existing `science` extra. Other tools require no new optional
dependency. IC calls the existing Core Spearman implementation; SciPy is only a
test oracle. Tests cover ties, missing fields, versions, dimensional contracts,
asynchronous labels, reservations, partial fills, duplicate events and persistence.

Design references are recorded with commits, licenses and limits in
`docs/open_source_research/20260911T0525/`. Freqtrade inspired filter composition,
Alphalens panel diagnostics, skfolio split interfaces, Hummingbot order events,
and MLflow experiment records. No external implementation was copied into this
package; existing native atomic I/O and Core metrics were reused.

## CPCV, strategy metrics and decision policy

```python
from GarimpoInvestimentos.research.cpcv import cpcv_splits, backtest_paths, derive_purge_and_embargo
from GarimpoInvestimentos.research.strategy_metrics import (
    strategy_metrics,
    dsr_sensitivity,
    pbo_cscv,
)
from GarimpoInvestimentos.research.decision_policy import load_policy, decide, record_decision
```

`cpcv_splits` purges every training observation whose `[start, available]` window
meets a test block and embargoes those starting within `embargo` after it.
`derive_purge_and_embargo` sets purge = label horizon and embargo = the leading
significant ACF lags of non-overlapping step returns. PSR/DSR reuse Core, PBO reuses
`analyzers/pbo.py`. Decision thresholds live only in `policies/decision_policy_v1.json`,
`APPROVED` by the owner on 2026-09-25 and effective from 2026-09-25T15:56:09Z, never
retroactive. Missing evidence yields `NO_DECISION`. A threshold change needs a new
version approved by the owner. Evidence: `docs/evidence/2026-09-24-prompt3b-cpcv-psr-dsr-pbo-politica.md`
and `docs/evidence/2026-09-25-aprovacao-politica-v1.md`.

## Pre-registered evaluation, holdouts and re-evaluation

```python
from GarimpoInvestimentos.research import ledgers  # docs/research_ledger paths
from GarimpoInvestimentos.research.preregistration import (
    register_preregistration,
    require_preregistered_before_run,
)
from GarimpoInvestimentos.research.holdout import (
    seal_holdout,
    open_holdout,
    assert_outside_holdouts,
)
from GarimpoInvestimentos.research.dedup import redundancy_check
from GarimpoInvestimentos.research.fm_zero_shot import (
    run_evaluation,
)  # Chronos zero-shot (Prompt 3c)
from GarimpoInvestimentos.research.reevaluation import run_reevaluation  # Prompt 4
```

New hypotheses are pre-registered in `docs/research_ledger/preregistrations.jsonl`
before any backtest; a development period touching a sealed holdout is refused, and
evaluations inside a sealed, unopened holdout are refused and recorded as `CRASHED`.
`redundancy_check` needs an explicit threshold with its source: policy v1 has none yet.
These modules read `docs/`, so they need a repository checkout (the wheel has no `docs/`).
See `docs/research_ledger/README.md` for the ledger rules.

F03/F04 historical economic gates remain scoped to their data requirements.
This package makes new engineering experiments possible; it supplies neither
missing historical specifications nor evidence of profitability.
