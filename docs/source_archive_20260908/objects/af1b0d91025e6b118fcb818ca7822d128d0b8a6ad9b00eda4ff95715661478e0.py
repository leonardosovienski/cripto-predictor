import json
import subprocess
import sys
import zipfile
from pathlib import Path

work = Path(__file__).resolve().parent
archive = work.parent / "outputs/CRIPTO_TESTE_HISTORICO_REPRODUCAO.zip"
target = work / "altcoin-retro-package-check"
target.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as z:
    for name in z.namelist():
        if not (target / name).resolve().is_relative_to(target.resolve()):
            raise ValueError(name)
    z.extractall(target)

commands = [
    [sys.executable, "-m", "pytest", "-q", "tests"],
    [sys.executable, "-m", "scripts.backtest_altcoin_payoff", "--data-dir", "data",
     "--training", "training/samples_identity_corrected.json.gz", "--output-dir", "reproduced"],
    [sys.executable, "-m", "scripts.audit_altcoin_retro", "--data-dir", "data",
     "--results-dir", "reproduced", "--training", "training/samples_identity_corrected.json.gz"],
    [sys.executable, "verify_reproduction.py"],
]
records = []
for command in commands:
    result = subprocess.run(command, cwd=target, text=True, capture_output=True)
    records.append({"command": command[1:], "exit_code": result.returncode,
                    "stdout": result.stdout, "stderr": result.stderr})
    print(json.dumps({"command": command[1:3], "exit_code": result.returncode,
                      "output_tail": result.stdout[-400:]}, ensure_ascii=True), flush=True)
    (work / "altcoin-retro-package-validation.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
