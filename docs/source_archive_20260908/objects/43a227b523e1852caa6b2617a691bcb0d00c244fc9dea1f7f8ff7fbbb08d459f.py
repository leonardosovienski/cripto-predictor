import hashlib
import json
import subprocess
from pathlib import Path

work = Path(__file__).resolve().parent
repo = work / "cripto-v1.2"
out = work.parent / "outputs"
result = json.loads((work / "project-review-package-check/reproduced/verification.json").read_text(encoding="utf-8"))
assert result["status"] == "PASS" and result["selected_tests_passed"] == 62
archive = out / "CRIPTO_REVISAO_FINAL_REPRODUCAO.zip"
result.update({"archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
               "archive_bytes": archive.stat().st_size,
               "package_source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()})
text = json.dumps(result, indent=2) + "\n"
(work / "review-package-check.json").write_text(text, encoding="utf-8")
(repo / "docs/evidence/project_review_20260907/package_validation.json").write_text(text, encoding="utf-8")
report_path = out / "CRIPTO_REVISAO_FINAL.json"
report = json.loads(report_path.read_text(encoding="utf-8"))
report["standalone_reproduction"] = result
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(text)
