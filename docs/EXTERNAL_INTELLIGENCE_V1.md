# External Intelligence V1

## 1. Scope and status

This is a CRIPTO-owned, research-only evidence layer. It is downstream from Opportunity Radar and is
physically isolated in `external_intelligence.db`. It cannot alter an `OpportunitySignal`, economic
gate, portfolio, execution or capital permission.

| Axis | Status |
|---|---|
| ENGINEERING_IMPLEMENTATION_STATUS | `OPERATIONAL_PARTIAL` |
| BASELINE_STATUS | `PARTIAL_PREEXISTING_FAILURES` |
| COINMETRICS_ADAPTER_STATUS | `COMPLETE_V1` |
| COINMETRICS_LIVE_VALIDATION_STATUS | `PASS_COMMUNITY_API_READ_ONLY` |
| SANTIMENT_ADAPTER_STATUS | `COMPLETE_BY_FIXTURE` |
| SANTIMENT_LIVE_VALIDATION_STATUS | `BLOCKED_MISSING_CREDENTIAL` |
| NANSEN_ADAPTER_STATUS | `COMPLETE_BY_FIXTURE` |
| NANSEN_LIVE_VALIDATION_STATUS | `BLOCKED_MISSING_CREDENTIAL` |
| TEMPORAL_INTEGRITY_STATUS | `PASS_FIXTURE` |
| RADAR_INVARIANCE_STATUS | `PASS_FIXTURE` |
| DATASET_SNAPSHOT_STATUS | `PASS` |
| CONDITIONAL_ANALYSIS_ENGINE_STATUS | `COMPLETE_MECHANISM_ONLY` |
| SCIENTIFIC_EVALUATION_STATUS | `NOT_EVALUATED` |
| RESEARCH_BUNDLE_STATUS | `PASS_FIXTURE` |
| CAIN_EXPORT_STATUS | `PASS_FIXTURE_DERIVED_READ_ONLY` |
| CAIN_ROUND_TRIP_STATUS | `BLOCKED_CURRENT_CAIN_CHECKOUT` |
| ECONOMIC_PROMOTION_STATUS | `PROHIBITED` |

`OPERATIONAL_PARTIAL` is intentional: the Coin Metrics collection job is runnable after explicit
rights/cutoff configuration. Santiment and Nansen transports and parsers exist, but live collection
is not validated without credentials. No scientific edge was tested.

## 2. Implemented architecture

```text
official provider API
  -> provider adapter (CORE HTTP/retry)
  -> explicit asset mapping + normalized ExternalObservationV1
  -> external_intelligence.db (CORE SQLite/migrations, append-only)
  -> deterministic dataset snapshot + context_at(cutoff)
  -> ShadowOpportunityContext / causal-ledger hash references
  -> exploratory conditional analysis
  -> sanitized ResearchBundleV1 stream
  -> CAIN read policy (generate remains false unless separately authorized)
```

Implemented: contracts, isolated store, receipts/revisions, capability snapshots, mappings,
Coin Metrics/Santiment/Nansen adapters, first expanding causal z-score, shadow context, temporal
perturbation audit, conditional analysis, OPS Coin Metrics job and separate bundle exporter.

Deferred: promotion to CORE, feature materialization, generic FeatureRegistry, candidate policy,
ablation, capital integration and any new shared bundle/task/result schema.

Blocked: live Santiment/Nansen, CAIN end-to-end result ingestion on the current detached/dirty CAIN
checkout, and any generation/persistent-memory use without provider-rights evidence.

## 3. Files and responsibilities

- `GarimpoInvestimentos/external_intelligence/contracts.py`: versioned observation/document,
  four clocks, PIT, rights, capability, mapping, collection-run and feature identities.
- `store.py`: isolated schema, idempotent migrations, database append-only guards, receipts and
  deterministic dataset snapshots.
- `context.py`, `features.py`, `audit.py`: cutoff serving, first causal transform and full-versus-
  physically-truncated recomputation.
- `providers/*.py`: small adapters reusing CORE network transport; no third provider framework.
- `collection.py`, `__main__.py`: failure isolation and an explicit-rights Coin Metrics collector.
- `shadow.py`, `ledger.py`, `conditional.py`: downstream association, hash-only causal references and
  conditional outcome mechanism.
- `GarimpoInvestimentos/jobs.py`: one OPS job, `external-coinmetrics`, with expected isolated DB.
- `packages/research-export/.../external.py`: separate, allowlisted ResearchBundleV1 producer stream.
- `tests/test_external_intelligence.py` and `packages/research-export/tests/test_external.py`: gates.

## 4. Schema

| Table | Identity/constraints | Purpose |
|---|---|---|
| `collection_runs` | PK `(collection_run_id, collection_run_revision)` | Operational manifest revisions. |
| `provider_capability_snapshots` | PK `snapshot_id` | Time-stamped discovered capability state. |
| `asset_mappings` | PK `mapping_id`; unique provider/canonical/provider/chain/contract/version | Explicit asset identity. |
| `external_observations` | PK `(observation_id, revision_id)`; unique `revision_id`; cutoff and metric indexes | Scientific observation revisions. |
| `observation_receipts` | PK `(revision_id, collection_run_id, collection_run_revision)` | Recollection provenance; earliest receipt controls receipt PIT. |
| `external_documents` | PK `(document_id, revision_id)`; unique revision | Research documents, not numeric features. |
| `dataset_snapshots` | PK deterministic snapshot revision; hash equality CHECK | Immutable scientific dataset identity. |

Migrations are deterministic/idempotent through `predictor_core.kernel.infra.run_migrations`.
Triggers reject UPDATE/DELETE on observations, receipts, documents, capabilities, runs and snapshots.

## 5. Observation and dataset identity

`observation_id` hashes provider, dataset, canonical/provider asset, metric/version, observed time and
semantic dimensions. `revision_id` hashes observation identity, normalized content, provider
availability evidence, PIT grade, capability state, collector version and metadata. It deliberately
does not hash the collection run or a later identical receipt.

An identical recollection therefore adds an operational receipt but not a scientific revision. A
changed provider value preserves the observation identity and creates another revision. Another
asset/metric/time creates another observation.

`collection_run_id` names an operational attempt. `collection_run_revision` hashes its full
operational manifest. `dataset_snapshot_revision` hashes ordered observation/document/feature
revisions plus cutoff/selection/cohort semantics. Two runs with identical scientific content may have
different run revisions and the same dataset snapshot revision.

## 6. Temporal semantics

- `observed_at`: represented phenomenon time.
- `provider_available_at`: only populated with auditable provider publication/availability evidence.
- `received_at`: when this system received a version.
- `effective_available_at`: causal cutoff used by serving/replay.

Derivation is exact: `PROVIDER_PIT -> provider_available_at`; `RECEIPT_PIT -> earliest received_at`;
`RECONSTRUCTED -> earliest received_at`. Every `context_at(T)` requires
`effective_available_at <= T`. Backfill does not gain historical availability.

Historical Coin Metrics/Santiment/Nansen data is `RECONSTRUCTED` unless better per-observation
availability evidence is supplied. The documented Nansen typical processing window is retained as a
note, never converted to a factual 05:00/07:00 timestamp.

## 7. Rights

Rights are orthogonal to PIT and default false. `RightsPolicy` records policy version, evidence
reference/hash, checked time, status and notes.

| Data class | Local research | Raw storage | Derived export | Raw export | CAIN read | CAIN generate | Persistent memory | Redistribution |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Unknown/default | false | false | false | false | false | false | false | false |
| Coin Metrics collection | requires explicit policy | requires explicit policy | requires explicit policy | false by default | requires explicit policy | false by default | false by default | false by default |
| Santiment | same fail-closed policy | same | same | false | same | false | false | false |
| Nansen | same, plus request gate | same | same | false | same | false | false | false |

The exporter admits only sanitized derived evidence with both `derived_export=true` and
`cain_read=true`; keys, headers, raw payloads and wallet lists are rejected. Bundle-level generate is
false. This is internal policy enforcement, not a universal legal opinion.

## 8. Providers

Coin Metrics uses API v4 pagination with trusted-host validation, catalog capability snapshots,
explicit missing versus unsupported states and a working Community API job. Live read-only validation
on 2026-09-21 fetched BTC `TxCnt` for 2025-01-01..02 (2 rows). Historical rows remain reconstructed.

Santiment implements authenticated GraphQL transport, body-level errors, partial-response refusal,
access/restriction/deprecation/version discovery and timeseries normalization. Weekly/Insights remain
`BLOCKED_NO_OFFICIAL_MACHINE_INTERFACE`; supplied texts must be documents.

Nansen implements authenticated POST, explicit chain capabilities, request/credit budget, rights
gate, status taxonomy, historical-holdings normalization and BTC != WBTC. Historical holdings are
reconstructed; live validation is blocked by missing `NANSEN_API_KEY`.

Official references rechecked: Coin Metrics API v4, Santiment Academy metric/access documentation,
and Nansen Smart Money, credits/authentication and methodology documentation (2026-09-21).

## 9. Temporal audit and failure isolation

The fixture gate compares full-store `context_at(T)` with recomputation from a physically truncated
SQLite store. It covers late revision, reconstructed history, future deletion, expanding z-score
leakage and missing semantics. Insertion-order determinism is achieved by content identities, sorted
selection and earliest-receipt semantics. Result: `PASS_FIXTURE`.

Failure-isolation tests prove a credit-exhausted provider yields a partial external result while a
healthy provider succeeds. External failures are not imported by Opportunity Radar. The radar
invariance fixture serializes the same canonical signal before/after downstream shadow attachment.

## 10. Causal ledger and conditional analysis

The bridge copies an existing research ledger row and adds only snapshot revision, context hash,
cutoff, PIT/rights composition and feature definition revisions. It never copies raw provider payload
or mutates the canonical row. Replay remains owned by the existing CRIPTO/CORE mechanisms.

The conditional engine filters only rows explicitly marked PIT-valid, preserves missingness and
reports baseline/conditional means by predeclared horizon. Current fixture use is
`HYPOTHESIS_GENERATING_ONLY`; search space was one condition and one horizon. No real provider outcome
dataset, matched cohort, multiple-testing claim, predictive edge or economic edge was evaluated.

## 11. ResearchBundle and CAIN

Producer: `crypto_research_export.external.export_external`.
Stream: `external-intelligence-shadow`. Source: one explicitly admitted, committed and hash-pinned
sanitized export. Artifacts use the existing `feature_slice` role. Raw/restricted data is excluded.

CAIN may read only evidence carrying explicit CAIN-read rights. Generation remains bundle-false;
persistent memory remains false. CAIN must not read `external_intelligence.db`. A future experiment can
use the existing ResearchTask registry with the dataset snapshot as a hash-pinned dataset/evidence
reference, existing CRIPTO admission/materialization, OPS execution and ResearchResultV1. No new task
or result schema was added.

The fixture proves bundle contract compatibility, not CAIN model behavior or scientific validity. The
full CAIN round trip is blocked because the current checkout lacks `cain.research_results`, is detached
and dirty, and its test environment is incomplete.

## 12. Operation

Set `EXTERNAL_INTELLIGENCE_RIGHTS_POLICY` to a reviewed JSON policy with explicit local-research
permission, `COINMETRICS_START_TIME`, `COINMETRICS_END_TIME`, and optionally asset/DB variables. Then:

```text
cripto-predictor-job external-coinmetrics
```

Direct context serving:

```text
python -m GarimpoInvestimentos.external_intelligence context-at \
  --asset crypto:btc --decision-time 2026-01-02T00:00:00Z
```

No job is scheduled automatically. Missing rights or cutoffs fails closed before persistence.

## 13. Validation summary

- New CRIPTO gates: 13 tests after OPS job coverage was added (contracts/store/PIT/audit/providers/
  radar/conditional/ledger/job).
- External ResearchBundle gates: 3 tests.
- Remaining CRIPTO suite: `1615 passed, 1 skipped`.
- Ruff lint: pass. New-file format check: pass. Targeted pyright: pass.
- Build: wheel and sdist pass. Secret scan: zero findings.
- Coin Metrics Community API: pass read-only; Santiment/Nansen live: blocked missing credentials.
- Global format, full pyright and full CRIPTO collection retain the preexisting blockers documented in
  `BASELINE_REPORT.md`.

## 14. Final verdict

The defensible operational core is implemented: isolated, append-only, revision-aware, rights-aware,
content-addressed, cutoff-safe, reproducible and failure-isolated. Coin Metrics is operational after
explicit rights configuration. Santiment/Nansen are fixture-complete but not live-validated. Temporal
integrity and radar invariance pass by fixture. Scientific value is not evaluated; economic promotion
is prohibited; prospective evidence remains pending.
