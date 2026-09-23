"""Frozen conformance vectors for the crypto research contract.

Deterministic synthetic datasets (contract conformance, not scientific evidence):
    positive        gross ~ +200 bps/obs, clearly positive after costs
    case_a          gross oscillates ±300 bps: Core CI crosses zero -> INCONCLUSIVE / NO_EDGE
    case_b          gross ~ +15 bps/obs: gross > 0 but net < 0 after 30 bps round trip
    insufficient    fewer observations than the protocol minimum
    future_canary   one row available after the data cutoff, tagged FUTURE_CANARY_CRYPTO_001
Everything is built through the real operator boundary (ReferenceStore.put_operator_bytes).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from GarimpoInvestimentos.research_contract import canonical
from GarimpoInvestimentos.research_execution import ReferenceStore

CUTOFF = "2026-08-31T00:00:00Z"
CANARY = "FUTURE_CANARY_CRYPTO_001"
HYPOTHESIS = "crypto:QUAL-SHADOW-001"
FAMILY = "crypto-qualification-fixed-shadow"
FEE_BPS, SLIPPAGE_BPS = 10, 5


def _z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def weekly_rows(returns: list[float], *, funding: float = 0.0001, end: str = CUTOFF) -> list[dict]:
    """Non-overlapping 7-day observations ending at (or before) `end`; available 1 min later."""
    last = datetime.fromisoformat(end.replace("Z", "+00:00")) - timedelta(minutes=1)
    rows = []
    for index, value in enumerate(returns):
        observed = last - timedelta(days=7 * (len(returns) - index))
        rows.append(
            {
                "observed_at": _z(observed),
                "available_at": _z(observed + timedelta(minutes=1)),
                "gross_return": value,
                "funding_rate": funding,
            }
        )
    return rows


DATASETS = {
    "positive": [0.018 if i % 2 else 0.022 for i in range(30)],
    "case_a": [0.03 if i % 2 else -0.03 for i in range(30)],
    "case_b": [0.0012 if i % 2 else 0.0018 for i in range(30)],
    "insufficient": [0.02] * 10,
}


def dataset_object(name: str) -> dict:
    if name == "future_canary":
        rows = weekly_rows(DATASETS["positive"])
        future = datetime.fromisoformat(CUTOFF.replace("Z", "+00:00")) + timedelta(days=7)
        rows.append(
            {
                "observed_at": _z(future),
                "available_at": _z(future + timedelta(minutes=1)),
                "gross_return": 0.0987654321,
                "funding_rate": 0.0001,
            }
        )
        return {
            "dataset_version": f"conformance-{name}-v1",
            "data_cutoff": CUTOFF,
            "label_start": rows[0]["observed_at"],
            "label_end": rows[-1]["available_at"],
            "canary": {"token": CANARY, "row_index": len(rows) - 1, "gross_return": 0.0987654321},
            "rows": rows,
        }
    rows = weekly_rows(DATASETS[name])
    return {
        "dataset_version": f"conformance-{name}-v1",
        "data_cutoff": CUTOFF,
        "label_start": rows[0]["observed_at"],
        "label_end": rows[-1]["available_at"],
        "rows": rows,
    }


def objects() -> dict[tuple[str, str], dict]:
    out = {
        ("protocol", "fixed-shadow"): {
            "handler": "crypto.handlers.backtest_existing_hypothesis.v1",
            "minimum_sample": 20,
            "turnover_bps": 0,
            "hypothesis_family": FAMILY,
            "feature_version": "none-fixed-signal-v1",
            "model_version": "fixed-long-shadow-v1",
            "selection_path": {
                "family": FAMILY,
                "candidate_set": ["fixed-long-shadow-v1"],
                "selection_metric": "predeclared",
                "selected_candidate": "fixed-long-shadow-v1",
            },
        },
        ("protocol", "frozen-family"): {
            "handler": "crypto.handlers.backtest_existing_hypothesis.v1",
            "minimum_sample": 20,
            "turnover_bps": 0,
            "hypothesis_family": "funding_oi_hmm_v3",
            "feature_version": "f",
            "model_version": "m",
            "selection_path": {
                "family": "funding_oi_hmm_v3",
                "candidate_set": ["m"],
                "selection_metric": "predeclared",
                "selected_candidate": "m",
            },
        },
        ("baseline", "flat"): {
            "baseline_id": "crypto:BASELINE-FLAT",
            "gross_return_bps": 0,
            "net_return_bps": 0,
        },
        ("cost_model", "v3-frozen"): {"fee_bps": FEE_BPS, "slippage_bps": SLIPPAGE_BPS},
        ("evidence", "none"): {
            "receipt_id": "crypto:EVIDENCE-NONE",
            "classification": "conformance",
        },
    }
    for name in ("positive", "case_a", "case_b", "insufficient", "future_canary"):
        out[("dataset", name.replace("_", "-"))] = dataset_object(name)
    return out


def build(
    root: Path, *, timeout_seconds: int = 120, max_retries: int = 2, max_pending: int = 1000
) -> dict:
    root = Path(root)
    store = ReferenceStore(root / "objects")
    registry = []
    for (kind, name), value in sorted(objects().items()):
        object_hash = store.put_operator_bytes(canonical(value))
        registry.append(
            {
                "kind": kind,
                "name": name,
                "version": "v1",
                "revision_id": f"{kind}:{name}:conformance-v1",
                "content_hash": object_hash,
            }
        )
    policy = {
        "schema_version": "CryptoResearchAdmissionPolicyV2",
        "policy_id": "crypto-conformance",
        "policy_version": 1,
        "owner": "CRIPTO_OPERATOR",
        "requester_trust": "LOCAL_FILE_ONLY",
        "handlers": {
            "BACKTEST_EXISTING_HYPOTHESIS": "crypto.handlers.backtest_existing_hypothesis.v1"
        },
        "hypotheses": {
            HYPOTHESIS: {
                "hypothesis_family": FAMILY,
                "purpose": "qualification probe; not a scientific hypothesis",
            },
            "crypto:QUAL-FROZEN-PROBE": {
                "hypothesis_family": "funding_oi_hmm_v3",
                "purpose": "negative probe",
            },
        },
        "registry": registry,
        "limits": {
            "max_pending_requests": max_pending,
            "max_request_bytes": 16384,
            "max_parameter_bytes": 1024,
            "max_concurrency": 1,
            "cpu_seconds": 120,
            "memory_mb": 512,
            "disk_mb": 256,
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
            "max_priority": "NORMAL",
        },
        "allowed_symbols": ["BTCUSDT"],
    }
    policy_path = root / "policy.json"
    policy_path.write_text(json.dumps(policy, indent=1), encoding="utf-8")
    (root / "requests").mkdir(exist_ok=True)
    return {
        "root": root,
        "policy": policy_path,
        "objects": root / "objects",
        "state": root / "state",
        "requests": root / "requests",
    }


def request(request_id: str, dataset: str = "positive", **overrides) -> dict:
    value = {
        "schema_version": "crypto-research-request/1",
        "request_id": request_id,
        "request_type": "BACKTEST_EXISTING_HYPOTHESIS",
        "research_id": "crypto:RESEARCH-CONFORMANCE",
        "hypothesis_id": HYPOTHESIS,
        "references": {
            "protocol": {"name": "fixed-shadow", "version": "v1"},
            "dataset": {"name": dataset.replace("_", "-"), "version": "v1"},
            "baseline": {"name": "flat", "version": "v1"},
            "cost_model": {"name": "v3-frozen", "version": "v1"},
            "evidence": {"name": "none", "version": "v1"},
        },
        "data_cutoff": CUTOFF,
        "parameters": {
            "symbol": "BTCUSDT",
            "horizon_days": 7,
            "max_observations": 100,
            "fee_bps": FEE_BPS,
            "slippage_bps": SLIPPAGE_BPS,
        },
        "priority_hint": "NORMAL",
    }
    value.update(overrides)
    return value


def write_request(env: dict, name: str, value: dict | str) -> Path:
    path = env["requests"] / f"{name}.json"
    path.write_text(
        value if isinstance(value, str) else json.dumps(value, indent=1), encoding="utf-8"
    )
    return path


def console_script() -> str:
    """The installed `cripto-research` console script next to the running interpreter."""
    folder = Path(sys.executable).parent
    candidate = folder / ("cripto-research.exe" if os.name == "nt" else "cripto-research")
    found = str(candidate) if candidate.exists() else shutil.which("cripto-research")
    if not found:
        raise RuntimeError("cripto-research console script is not installed")
    return found


def cli(
    env: dict, *args: str, fault: str | None = None, timeout: float = 600
) -> tuple[int, list[dict]]:
    """Run the installed entrypoint in a NEW process; returns (exit code, JSON lines)."""
    command = [console_script(), "--state", str(env["state"]), *args]
    if args and args[0] in {"process", "run"}:
        command[4:4] = ["--policy", str(env["policy"]), "--objects", str(env["objects"])]
    environment = dict(os.environ)
    environment.pop("CRIPTO_RESEARCH_FAULT", None)
    if fault:
        environment["CRIPTO_RESEARCH_FAULT"] = fault
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=environment,
        cwd=env["root"],
        encoding="utf-8",
        errors="replace",
    )
    lines = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            lines.append(json.loads(line))
    if completed.returncode not in (0, 2, 3, 4, 5, 86):
        raise AssertionError(f"unexpected exit {completed.returncode}: {completed.stderr[-2000:]}")
    return completed.returncode, lines
