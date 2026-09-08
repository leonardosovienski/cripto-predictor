"""Portable, offline reproduction of the final project review package."""

import gzip
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

root = Path(__file__).resolve().parent
project = root / "project"
data = root / "data"
reproduced = root / "reproduced"
reproduced.mkdir(exist_ok=True)
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
manifest = read(root / "FILES_SHA256.json")
for name, expected in manifest.items():
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("path outside package")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("packaged file differs: " + name)
print(f"Verified {len(manifest)} packaged files.", flush=True)

env = os.environ | {"DATA_DIR": str(reproduced / "test-data"),
                    "PREDICTOR_EVENTS_PATH": str(reproduced / "events.jsonl")}
commands = [
    ["-m", "scripts.backtest_altcoin_payoff", "--data-dir", str(data / "retro"),
     "--training", str(data / "training/samples_identity_corrected.json.gz"),
     "--output-dir", str(reproduced / "retro")],
    ["-m", "scripts.audit_altcoin_retro", "--data-dir", str(data / "retro"),
     "--training", str(data / "training/samples_identity_corrected.json.gz"),
     "--results-dir", str(reproduced / "retro")],
    ["-m", "scripts.review_carry_absolute_profit", "--data-dir", str(data / "carry"),
     "--output", str(reproduced / "carry.json")],
    ["-m", "pytest", "-q", "tests/test_altcoin_retro.py", "tests/test_altcoin_payoff.py",
     "tests/test_altcoin_analogs.py", "tests/test_altcoin_forward.py", "tests/test_altcoin_observer_review.py"],
]
logs = []
for command in commands:
    run = subprocess.run([sys.executable, *command], cwd=project, env=env, text=True, capture_output=True)
    logs.append({"command": command, "exit_code": run.returncode, "stdout": run.stdout, "stderr": run.stderr})
    (reproduced / "commands.json").write_text(json.dumps(logs, indent=2), encoding="utf-8")
    if run.returncode:
        raise RuntimeError(run.stdout + run.stderr)
    print(command[1] + ": PASS", flush=True)
assert "62 passed" in logs[-1]["stdout"]
for name in ("results.json", "weekly_results.json", "decisions.json", "scores.json.gz", "audit.json"):
    if (reproduced / "retro" / name).read_bytes() != (root / "expected/retro" / name).read_bytes():
        raise ValueError("historical reproduction differs: " + name)
assert (reproduced / "carry.json").read_bytes() == (root / "expected/carry.json").read_bytes()

sys.path.insert(0, str(project))
from scripts.observe_altcoin_forward import Ledger, snapshot, verify_freeze

forward = data / "forward-reviewed"
cache = {}
for path in (forward / "raw").glob("*.json"):
    meta = read(path)
    body = gzip.decompress(path.with_suffix(".bin.gz").read_bytes())
    assert hashlib.sha256(body).hexdigest() == meta["sha256"]
    url = urlparse(meta["url"])
    cache[(url.path, tuple(sorted((k, v[0]) for k, v in parse_qs(url.query).items())))] = (json.loads(body), meta)

class RecordedSource:
    def get(self, endpoint, params=None):
        path = "/bapi/composite/v1/public/cms/article/list/query" if endpoint == "cms" else "/api/v3/" + endpoint
        return cache[(path, tuple(sorted((k, str(v)) for k, v in (params or {}).items())))]

ledger = Ledger(forward / "ledger.jsonl")
event = next(row for row in ledger.rows if row["kind"] == "PREFLIGHT")
# Windows provenance paths also remain readable when reproduced on POSIX.
name = event["payload"]["snapshot"].replace("\\", "/").split("/")[-1]
path = forward / "snapshots" / name
assert hashlib.sha256(path.read_bytes()).hexdigest() == event["payload"]["snapshot_sha256"]
original = read(path)
rebuilt = snapshot(RecordedSource(), datetime.fromisoformat(original["anchor_utc"]), data / "base",
                   data / "training/samples_identity_corrected.json.gz", "all_current_spot_usdt")
for key in ("recorded_after_acquisition", "sample_status_changes", "compared_with_ledger_sha256"):
    original.pop(key, None)
    rebuilt.pop(key, None)
assert rebuilt == original
verify_freeze(data / "base", data / "training/samples_identity_corrected.json.gz",
              project / "docs/evidence/altcoin_reviewed_20260907")
result = {"status": "PASS", "packaged_file_hashes": len(manifest), "selected_tests_passed": 62,
          "reproduced_result_files_byte_identical": 6, "forward_snapshot": "REPLAYED_FROM_SAVED_RESPONSES",
          "forward_eligible": len(rebuilt["ranked"]), "forward_selected": rebuilt["selected"],
          "public_requests_during_reproduction": 0, "orders": False}
(reproduced / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
