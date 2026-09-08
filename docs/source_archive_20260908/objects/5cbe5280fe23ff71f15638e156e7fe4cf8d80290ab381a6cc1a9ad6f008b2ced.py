import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

work = Path(__file__).resolve().parent
root = work / "cripto-research"
sys.path.insert(0, str(root))
from scripts.observe_carry_forward import verify

verify()
old = json.loads((root / "docs/evidence/carry_forward_20260908/code_freeze.json").read_bytes())
files = list(old["files"])
files += ["scripts/__init__.py", "scripts/immediate_public.py", "scripts/run_immediate_audit.py", "scripts/audit_immediate_decimal.py", "tests/test_immediate_audit.py", "docs/evidence/immediate_audit_20260908/protocol.json"]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
evidence = root / "docs/evidence/immediate_audit_20260908"
freeze = {"registered_utc":datetime.now(UTC).isoformat(), "protocol_commit":"46d52b9", "before_market_collection":True,
          "files":{n:sha(root/n) for n in files}, "tests_passed_before_collection":57, "new_tests":8,
          "ruff":"PASS", "pyright_errors":0, "same_author":True}
with (evidence / "freeze.json").open("x", encoding="utf-8") as stream:
    json.dump(freeze, stream, indent=2)
paths = list((work.parent/"outputs").glob("*"))
paths += [work/"carry-forward-data/ledger.jsonl", Path("C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml"),
          work.parent.parent/"files-mentioned-by-the-user-cripto/work/altcoin-reviewed-data/ledger.jsonl"]
preservation = {str(p):sha(p) for p in paths if p.is_file()}
with (evidence / "preservation_before.json").open("x", encoding="utf-8") as stream:
    json.dump(preservation, stream, indent=2)
print(json.dumps({"frozen_files":len(files),"preserved_files":len(preservation)}))
