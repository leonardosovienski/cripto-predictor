import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import httpx

work = Path(__file__).resolve().parent
repo = work / "cripto-v1.2"
lock = tomllib.loads((repo / "uv.lock").read_text(encoding="utf-8"))
output = work / "review-runtime-wheels"
output.mkdir(exist_ok=True)
paths, records = [], []
for name in ("distlib", "virtualenv"):
    package = next(row for row in lock["package"] if row["name"] == name)
    wheel = next(row for row in package["wheels"] if row["url"].endswith("none-any.whl"))
    response = httpx.get(wheel["url"], timeout=30)
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    assert "sha256:" + digest == wheel["hash"], name
    path = output / wheel["url"].split("/")[-1]
    path.write_bytes(response.content)
    paths.append(str(path))
    records.append({"package": name, "version": package["version"], "sha256": digest, "url": wheel["url"]})
subprocess.run(["uv", "pip", "install", "--python", sys.executable, "--no-cache", "--no-deps", "--reinstall", "--link-mode", "copy", *paths], check=True)
(work / "review-runtime-repair.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
print("Restored both exact lockfile-verified wheels without shared cache links.")
