# Binance COLLECTION_ONLY observation

The active, checksum-sealed plan is `observation_plans/binance_funding_oi_v1.yaml`.
It characterizes Binance Futures empirically; it does not treat Binance as truth and
does not authorize capital, hypotheses, backtests, `PENDING_SAMPLE`, `SHADOW`, or `GO`.

## Operations

Generate independent UTC daily scorecards after the observed day has closed:

```console
cripto-predictor-job observation-daily
```

The job writes the SQLite audit record plus an append-only JSONL. A rerun with identical
content is idempotent; changed content for the same plan/source/metric/day fails closed.

Generate a weekly summary and maturity snapshots explicitly:

```console
python -m GarimpoInvestimentos.observation_reporting weekly --date 2026-08-10
python -m GarimpoInvestimentos.observation_reporting maturity-initial --date 2026-09-07
python -m GarimpoInvestimentos.observation_reporting maturity-final --date 2026-11-06
```

Run resilience drills only against the automatically-created temporary database:

```console
python -m GarimpoInvestimentos.observation_resilience
```

The active plan is immutable. Threshold recalibration requires a new versioned plan or
charter. Human approval is a separate signed record referencing the plan checksum and
report hash; it is never inferred or written by an automated job.

Scheduling is intentionally environment-owned. Install the daily and weekly commands in
the existing cron, systemd, Kubernetes, or Windows Task Scheduler deployment only after
verifying its Feature Store path, UTC timezone, service account, retention, and alert sink.
