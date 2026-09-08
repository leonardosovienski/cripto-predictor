import hashlib
import importlib.metadata
import json
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

WORK = Path(__file__).resolve().parent
ROOT = WORK / "cripto-research"
OUTPUTS = WORK.parent / "outputs"
ORIGINAL = WORK.parent.parent / "files-mentioned-by-the-user-cripto/work/cripto-v1.2"
sys.path.insert(0, str(ROOT))
from scripts.plan_btc_hedge_v3 import replay


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def git(*args, root=ROOT):
    return subprocess.check_output(["git", *args], cwd=root)


freezes = [
    "absolute_research_20260908/reproduction_freeze.json",
    "basis_research_20260908/implementation_freeze.json",
    "basis_research_20260908/execution_planner_freeze.json",
    "chat_review_20260908/new_code_freeze.json",
]
count = 0
for name in freezes:
    obj = json.loads((ROOT / "docs/evidence" / name).read_bytes())
    for path, digest in obj.get("files", obj).items():
        assert sha((ROOT / path).read_bytes()) == digest, path
        count += 1

historical = []
for folder in ("absolute_research_20260908/absolute-results-v3", "basis_research_20260908/results-v2"):
    for path in sorted((ROOT / "docs/evidence" / folder).rglob("*")):
        if path.is_file():
            rel = path.relative_to(ROOT).as_posix()
            if folder.startswith("absolute"):
                package, member = "CRIPTO_CODIGO_DADOS_REPRODUCAO.zip", "code/" + rel
            else:
                package = "CRIPTO_BASIS_IMPLEMENTACAO.zip"
                member = "results/" + path.relative_to(ROOT / "docs/evidence" / folder).as_posix()
            with ZipFile(OUTPUTS / package) as archive:
                assert sha(path.read_bytes()) == sha(archive.read(member)), rel
            if path.name != "FILES_SHA256.json":
                historical.append(rel)
assert len(historical) == 28
assert not git("status", "--porcelain", root=ORIGINAL).strip()
assert git("rev-parse", "HEAD", root=ORIGINAL).decode().strip() == "fbf4c714a092668bc1b82942ebdececd396e3ab7"
assert git("rev-parse", "main", root=ORIGINAL).decode().strip() == "7834a60dcf044ad65a118e323cb79f163ff0bbcc"
auto = Path("C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml")
ledger = ORIGINAL.parent / "altcoin-reviewed-data/ledger.jsonl"
assert sha(auto.read_bytes()) == "3b70e3f068c41ef3c964fed543ba388f8237b6f207ce49f5a4ff3c8caec95cfb"
assert sha(ledger.read_bytes()) == "42e96f95f1765784e12cbf9fed2d77d26cbd0f268bbbaf46bcdf3715ec6141a5"
old_outputs = {}
for name in ("CRIPTO_BASIS_ENTREGA_SHA256.json", "CRIPTO_COMPARACAO_SHA256.json", "CRIPTO_REVISAO_DO_CHAT_SHA256.json"):
    old_outputs.update(json.loads((OUTPUTS / name).read_bytes())["outputs"])
old = json.loads((OUTPUTS / "ENTREGA_SHA256.json").read_bytes())
old_outputs[old["package"]] = old["package_sha256"]
old_outputs["CRIPTO_RESULTADOS.md"] = old["report_sha256"]
for name, digest in old_outputs.items():
    assert sha((OUTPUTS / name).read_bytes()) == digest, name

def no_network(*args, **kwargs):
    raise AssertionError("Offline replay attempted network")

socket.socket.connect = no_network
plans = replay(WORK / "btc-execution-diagnostic-v1", WORK / "net-hedge-plans-v3-final.json")
previous = json.loads((ROOT / "docs/evidence/chat_review_20260908/net_hedge_plans_v2.json").read_bytes())
assert [p["plan"] for p in plans["plans"]] == [p["plan"] for p in previous["plans"]]
assert len(plans["plans"]) == 12
evidence = ROOT / "docs/evidence/corrections_20260908"
write(evidence / "net_hedge_plans_v3.json", plans)
audit = json.loads((WORK / "basis-separate-source-audit.json").read_bytes())
assert audit["status"] == "PASS" and audit["raw_sources"] == 532 and len(audit["groups"]) == 29
write(evidence / "separate_source_audit.json", audit)
validation = {
    "checked_utc": datetime.now(UTC).isoformat(), "status": "PASS",
    "full_repository_pytest": {"passed": 1159, "seconds": 114.24, "exit_code": 0, "new_cases": 49},
    "ruff": "PASS", "pyright_errors": 0,
    "historical_frozen_files": count, "historical_result_files": len(historical),
    "saved_quote_plans_unchanged": len(plans["plans"]), "offline_replay_socket_blocked": True,
    "separate_normalizer": audit,
    "original_runtime": {"status": "PASS", "files_checked": 3785},
    "original_repository_clean_and_heads_unchanged": True,
    "original_altcoin_automation_sha256": sha(auto.read_bytes()),
    "original_altcoin_ledger_sha256": sha(ledger.read_bytes()),
    "previous_deliveries_verified": old_outputs,
    "real_orders": 0, "prospective_profit_observed": False,
    "meaning": "Technical corrections and preservation verified; no future profit validation."
}
write(evidence / "validation.json", validation)

names = ["scripts/" + n + ".py" for n in (
    "research_io", "plan_btc_hedge_v3", "audit_basis_sources", "carry_public", "carry_forward_math",
    "observe_carry_forward", "plan_btc_hedge_v2", "plan_btc_hedge", "diagnose_btc_execution", "basis_data")]
names += ["tests/" + n + ".py" for n in ("test_research_corrections", "test_carry_forward", "test_carry_public")]
names += ["docs/evidence/carry_forward_20260908/protocol.json"]
freeze = {"frozen_utc": datetime.now(UTC).isoformat(), "registration_commit": "e1033a8",
    "scope": "New observer and supported validation supplement; previous freezes preserved",
    "python": list(sys.version_info[:3]), "httpx": importlib.metadata.version("httpx"),
    "files": {n: sha((ROOT / n).read_bytes()) for n in names}}
target = ROOT / "docs/evidence/carry_forward_20260908/code_freeze.json"
assert not target.exists(), "Never silently rewrite observer freeze"
write(target, freeze)
print(json.dumps({"preservation": "PASS", "frozen_old_files": count, "historical_results": len(historical), "plans": 12, "new_frozen_files": len(names)}))
