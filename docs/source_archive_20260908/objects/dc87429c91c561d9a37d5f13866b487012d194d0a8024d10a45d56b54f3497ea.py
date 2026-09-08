import gzip
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlparse

work = Path(__file__).resolve().parent
repo = work / "cripto-v1.2"
sys.path.insert(0, str(repo))
from scripts.observe_altcoin_forward import Ledger, snapshot, verify_freeze

evidence = repo / "docs/evidence/project_review_20260907"
data = work / "altcoin-reviewed-data"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
cache = {}
raw_checks = 0
for p in (data / "raw").glob("*.json"):
    meta = read(p)
    body = gzip.decompress(p.with_suffix(".bin.gz").read_bytes())
    assert hashlib.sha256(body).hexdigest() == meta["sha256"]
    u = urlparse(meta["url"])
    key = (u.path, tuple(sorted((k, v[0]) for k, v in parse_qs(u.query).items())))
    cache[key] = (json.loads(body), meta)
    raw_checks += 1

class Recorded:
    def get(self, endpoint, params=None):
        path = "/bapi/composite/v1/public/cms/article/list/query" if endpoint == "cms" else "/api/v3/" + endpoint
        return cache[(path, tuple(sorted((k, str(v)) for k, v in (params or {}).items())))]

snap_path = next((data / "snapshots").glob("*.json"))
original = read(snap_path)
rebuilt = snapshot(Recorded(), datetime.fromisoformat(original["anchor_utc"]), work / "altcoin-data",
                   work / "altcoin-payoff-results/samples_identity_corrected.json.gz", "all_current_spot_usdt")
for key in ("recorded_after_acquisition", "sample_status_changes", "compared_with_ledger_sha256"):
    original.pop(key, None)
    rebuilt.pop(key, None)
assert rebuilt == original
ledger = Ledger(data / "ledger.jsonl")
preflight = next(r for r in ledger.rows if r["kind"] == "PREFLIGHT")
assert preflight["payload"]["snapshot_sha256"] == sha(snap_path)
marks = read(data / "preflight_marks.json")
assert marks == next(r for r in ledger.rows if r["kind"] == "PREFLIGHT_QUOTES")["payload"]["marks"]
book_checks = 0
for position in marks["cost_probe_1000"]["positions"]:
    if not position["entry"]:
        continue
    meta = position["source"]
    assert datetime.fromisoformat(meta["requested_at"]) >= datetime.fromisoformat(preflight["known_at"])
    book = json.loads(gzip.decompress((data / meta["raw_file"]).read_bytes()))
    remaining, units = Decimal(1000), Decimal(0)
    for price, available in book["asks"]:
        amount = min(remaining, Decimal(price) * Decimal(available))
        units += amount / Decimal(price)
        remaining -= amount
        if remaining == 0:
            break
    assert remaining == 0
    entry = position["entry"]
    assert abs(units - Decimal(entry["gross_quantity"])) < Decimal("1e-15")
    for slip, qty in entry["quantity_after_assumed_fee_and_extra_slippage"].items():
        expected = units * Decimal("0.999") * (1 - Decimal(slip) / 10000)
        assert abs(expected - Decimal(qty)) < Decimal("1e-15")
    book_checks += 1

frozen = verify_freeze(work / "altcoin-data", work / "altcoin-payoff-results/samples_identity_corrected.json.gz",
                       repo / "docs/evidence/altcoin_reviewed_20260907")
historical = {}
for name in ("results.json", "weekly_results.json", "decisions.json", "scores.json.gz"):
    assert sha(work / "review-retro-replay" / name) == sha(work / "altcoin-retro-results" / name), name
    historical[name] = sha(work / "review-retro-replay" / name)
protected = ["charters/scientific_state.json", "GarimpoInvestimentos/trials.json",
             "GarimpoInvestimentos/v3/costs.py", "charters/h6_definition_frozen.json",
             "GarimpoInvestimentos/h6_status.json", "CR_RESEARCH_FREEZE.md", "CR_FREEZE_INDEX.md",
             "scripts/prepare_altcoin_payoff.py", "scripts/research_altcoin_analogs.py",
             "docs/evidence/altcoin_profit_20260907/freeze.json",
             "docs/evidence/altcoin_profit_20260907/protocol.json"]
for name in protected:
    assert not subprocess.check_output(["git", "diff", "5d28a63", "--", name], cwd=repo), name
out = work.parent / "outputs"
manifest_text = "\n".join(p.read_text(encoding="utf-8") for p in out.glob("*MANIFESTO.json"))
archives = {}
for path in sorted(out.glob("*.zip")):
    if path.name.startswith("CRIPTO_REVISAO_FINAL"):
        continue
    digest = sha(path)
    assert digest in manifest_text, path.name
    archives[path.name] = digest
result = {
    "live_preflight": {"sample_size": original["sample_size"],
                       "currently_trading_after_exclusions": original["currently_trading_after_exclusions"],
                       "eligible": len(original["ranked"]), "selected": original["selected"],
                       "raw_response_hashes": raw_checks, "independent_book_entry_checks": book_checks,
                       "offline_snapshot_replay": "EXACT_EXCEPT_NEW_EXECUTION_TIMESTAMP_AND_LEDGER_LINK_FIELDS",
                       "freeze_sha256": frozen, "ledger_integrity": "PASS", "prospective": False},
    "historical_replay": {"status": "BYTE_IDENTICAL", "sha256": historical},
    "protected_files_unchanged": {name: sha(repo / name) for name in protected},
    "prior_reproduction_archives_unchanged": archives,
    "model_tuning": False, "orders": False,
}
(evidence / "reconciliation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"preflight": result["live_preflight"], "historical_replay": "BYTE_IDENTICAL",
                  "protected_files": len(protected), "prior_archives": len(archives)}, indent=2))
