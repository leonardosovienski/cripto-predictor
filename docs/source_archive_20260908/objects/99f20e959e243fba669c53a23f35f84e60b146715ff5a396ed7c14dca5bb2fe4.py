import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

work = Path(__file__).resolve().parent
target = work / "altcoin-retro-package-check"
archive = work.parent / "outputs/CRIPTO_TESTE_HISTORICO_REPRODUCAO.zip"
old = json.loads((target / "FILES_SHA256.json").read_text(encoding="utf-8"))
with zipfile.ZipFile(archive) as z:
    new = json.loads(z.read("FILES_SHA256.json"))
    assert new.keys() == old.keys()
    changed = {key for key in old if old[key] != new[key]}
    assert changed == {"verify_reproduction.py", "provenance/deliver_retro.py"}, changed
    for name in sorted(changed | {"FILES_SHA256.json"}):
        (target / name).write_bytes(z.read(name))

result = subprocess.run([sys.executable, "verify_reproduction.py"], cwd=target,
                        text=True, capture_output=True)
assert result.returncode == 0, result.stdout + result.stderr
records = json.loads((work / "altcoin-retro-package-validation.json").read_text(encoding="utf-8"))
assert all(record["exit_code"] == 0 for record in records[:3])
assert "53 passed" in records[0]["stdout"]
validation = {
    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "archive_bytes": archive.stat().st_size,
    "extracted_package_tests": {"passed": 53, "output": records[0]["stdout"]},
    "extracted_package_backtest": "PASS",
    "extracted_package_independent_audit": "PASS",
    "package_integrity_and_reproduced_results": result.stdout.strip(),
    "packaging_correction": "Initial verification failed because Windows decoded a UTF-8 filename manifest as cp1252. Added explicit UTF-8 to package checker. Only checker and packaging provenance changed; all data, model, tests and result files kept identical hashes.",
    "post_correction_changed_files": sorted(changed),
    "initial_execution_log": records,
    "final_status": "PASS",
}
path = work / "cripto-v1.2/docs/evidence/altcoin_retro_20260907/package_validation.json"
path.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "PASS", "verification": result.stdout.strip(),
                  "archive_sha256": validation["archive_sha256"]}))
