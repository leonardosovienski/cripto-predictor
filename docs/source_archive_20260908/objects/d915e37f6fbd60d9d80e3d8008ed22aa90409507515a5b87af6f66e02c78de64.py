import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "FILES_SHA256.json").read_text(encoding="utf-8"))
for name, expected in manifest.items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError("Packaged file hash mismatch: " + name)
names = ("results.json", "weekly_results.json", "decisions.json", "scores.json.gz", "audit.json")
for name in names:
    if (root / "reproduced" / name).read_bytes() != (root / "expected" / name).read_bytes():
        raise ValueError("Reproduction differs: " + name)
print(f"PASS: {len(manifest)} packaged files checked; {len(names)} reproduced files byte-identical.")
