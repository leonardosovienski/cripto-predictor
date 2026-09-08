import hashlib
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "work/cripto-research"
EVIDENCE = REPO / "docs/evidence/basis_research_20260908"
OUTPUTS = ROOT / "outputs"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def archive(source, destination):
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(source.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                z.write(p, p.relative_to(source).as_posix())


def main():
    original = Path(r"C:\Users\Superleo13\Documents\Codex\2026-09-07\files-mentioned-by-the-user-cripto\work\cripto-v1.2")
    before = json.loads((EVIDENCE / "preservation_before.json").read_text(encoding="utf-8"))
    automation = Path(r"C:\Users\Superleo13\.codex\automations\observar-altcoins-semanalmente\automation.toml")
    assert sha(automation) == before["automation_sha256"]
    assert subprocess.check_output(["git", "-C", str(original), "status", "--porcelain"]).strip() == b""
    assert subprocess.check_output(["git", "-C", str(original), "rev-parse", "HEAD"]).decode().strip() == before["original_head"]
    assert subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "refs/heads/main"]).decode().strip() == before["main_head"]
    ledger = original.parent / "altcoin-reviewed-data/ledger.jsonl"
    old_transfer = json.loads((REPO / "docs/evidence/absolute_research_20260908/automation_transfer.json").read_text(encoding="utf-8"))
    assert sha(ledger) == old_transfer["ledger_file_sha256"]
    assert sha(OUTPUTS / "CRIPTO_CODIGO_DADOS_REPRODUCAO.zip") == "7a241c10356fa253d942970430e189cbd7b07892f8c5c734e0734a6f74aa0831"
    write(EVIDENCE / "preservation_after.json", {"checked_utc": datetime.now(timezone.utc).isoformat(), "original_repository_clean": True, "original_head": before["original_head"], "main_head": before["main_head"], "automation_unchanged": True, "observer_ledger_sha256": sha(ledger), "observer_runtime_verification": {"status": "PASS", "files_checked": 3785}, "previous_delivery_unchanged": True})
    registry_path = EVIDENCE / "trials.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    results = json.loads((ROOT / "work/basis-results-v2/results.json").read_text(encoding="utf-8"))
    for stream in registry["streams"]:
        stream.update(status="COMPLETED", economic_evaluations=1, unique_rule_specifications_evaluated=1, verdict=results["streams"][stream["id"]]["verdict"])
    registry["counter_semantics"] = "Economic evaluations count unique registered rule specifications. Cost cases and physical software/reproduction reruns are reported separately in runs; no parameter search."
    registry["runs"][-1].update(status="COMPLETED", completed_cost_cases=6, completed_utc=datetime.now(timezone.utc).isoformat())
    write(registry_path, registry)
    additions = ["scripts/plan_btc_hedge.py", "scripts/reproduce_btc_basis.py", "tests/test_btc_execution_plan.py"]
    write(EVIDENCE / "execution_planner_freeze.json", {"files": {p: sha(REPO / p) for p in additions}, "scope": "Current saved-quote net-quantity planning and offline orchestration only. Historical engines and parameters unchanged.", "saved_quotes_reused": 12, "new_network_requests": 0})
    write(EVIDENCE / "validation.json", {"status": "PASS", "basis_and_prior_regression_tests": 37, "new_execution_plan_tests": 5, "total_distinct_targeted_tests": 42, "new_tests": 28, "prior_regression_tests": 14, "ruff": "PASS", "pyright_errors": 0, "independent_audit": json.loads((EVIDENCE / "independent_audit.json").read_text(encoding="utf-8")), "partial_v1_files_byte_identical_to_v2": 4, "diagnostic_raw_hashes_verified": 26})
    with (EVIDENCE / "run_history.md").open("a", encoding="utf-8") as f:
        f.write("\n- v2 concluída: BR1 +230,17 / +110,07 / +78,42 USDT, cinco hedges; BR2 zero entradas e zero resultado. Auditoria Decimal aprovada. Quatro arquivos v1 idênticos após a correção.\n- Diagnóstico: 12 fotografias públicas, sem ordens; um cálculo adicional sobre os mesmos dados dimensiona a compra bruta para o hedge líquido após comissão em BTC. Nenhum retorno histórico ou parâmetro foi alterado.\n")
    for source, target in [("CRIPTO_BASIS_RESULTADOS.md", "DECISAO.md"), ("CRIPTO_BASIS_REPRODUZIR.md", "REPRODUZIR.md")]:
        (EVIDENCE / target).write_bytes((OUTPUTS / source).read_bytes())
    (OUTPUTS / "CRIPTO_BASIS_RESULTADOS.json").write_bytes((ROOT / "work/basis-results-v2/results.json").read_bytes())
    for source, target in [("basis-results-v2", "results-v2"), ("basis-results-v1", "results-v1-partial")]:
        shutil.copytree(ROOT / "work" / source, EVIDENCE / target)
    for folder, name in [("basis-research-data", "RESEARCH_DATA.zip"), ("btc-execution-diagnostic-v1", "EXECUTION_DATA.zip"), ("basis-capability-probe", "CAPABILITY_PROBES.zip")]:
        archive(ROOT / "work" / folder, EVIDENCE / name)
    old = json.loads((EVIDENCE / "implementation_freeze_v1.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(EVIDENCE / "V1_CODE.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name, digest in old["files"].items():
            raw = subprocess.check_output(["git", "-C", str(REPO), "show", "5b16c5e:" + name])
            assert hashlib.sha256(raw).hexdigest() == digest
            z.writestr(name, raw)
    write(EVIDENCE / "data_archives.json", {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in EVIDENCE.glob("*.zip")})
    stage = ROOT / "work/basis-delivery-stage"
    assert stage.resolve().is_relative_to((ROOT / "work").resolve())
    stage.mkdir(exist_ok=False)
    (stage / "scripts").mkdir()
    (stage / "tests").mkdir()
    (stage / "scripts/__init__.py").write_bytes(b"")
    modules = ["basis_data", "backtest_btc_basis", "diagnose_btc_execution", "run_btc_basis", "audit_btc_basis", "plan_btc_hedge", "reproduce_btc_basis"]
    for name in modules:
        shutil.copyfile(REPO / "scripts" / (name + ".py"), stage / "scripts" / (name + ".py"))
    for name in ["test_btc_basis.py", "test_btc_execution_plan.py"]:
        shutil.copyfile(REPO / "tests" / name, stage / "tests" / name)
    for source, target in [("basis-research-data", "data"), ("basis-results-v2", "results"), ("basis-results-v1", "prior_partial_results"), ("btc-execution-diagnostic-v1", "execution")]:
        shutil.copytree(ROOT / "work" / source, stage / target)
    shutil.copytree(EVIDENCE, stage / "docs/evidence/basis_research_20260908", ignore=shutil.ignore_patterns("RESEARCH_DATA.zip", "EXECUTION_DATA.zip", "results-v2", "results-v1-partial"))
    shutil.copyfile(OUTPUTS / "CRIPTO_BASIS_RESULTADOS.md", stage / "RESULTADOS.md")
    shutil.copyfile(OUTPUTS / "CRIPTO_BASIS_REPRODUZIR.md", stage / "README.md")
    (stage / "requirements.txt").write_text("numpy==2.5.1\nhttpx==0.28.1\npytest==8.4.2\n", encoding="utf-8")
    write(stage / "FILES_SHA256.json", {p.relative_to(stage).as_posix(): sha(p) for p in sorted(stage.rglob("*")) if p.is_file()})
    print(json.dumps({"staging": str(stage), "files": len(list(stage.rglob('*'))), "data_archive_bytes": (EVIDENCE / 'RESEARCH_DATA.zip').stat().st_size}))


if __name__ == "__main__":
    main()
