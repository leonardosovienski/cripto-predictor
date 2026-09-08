from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PATTERNS = {
    "openai": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "google": re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    "github": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{16,}\b"),
    "credential_assignment": re.compile(
        r"(?i)(?:api[_-]?key|secret|token|password)\s*[=:]\s*[\"']?([^\s\"'#,]{16,})"
    ),
}
ALLOWLIST = ("test-", "unit-test", "example", "placeholder", "dummy", "fake_", "synthetic", "your_")


def scan(root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(
            part in {".git", ".venv", "__pycache__"} for part in path.parts
        ):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, 1):
            for kind, pattern in PATTERNS.items():
                for match in pattern.finditer(line):
                    value = match.group(match.lastindex or 0)
                    if (
                        "(" in value
                        or (path.suffix == ".py" and ("." in value or value.endswith(")")))
                        or any(marker in value.lower() for marker in ALLOWLIST)
                    ):
                        continue
                    findings.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "line": line_number,
                            "kind": kind,
                            "fingerprint": hashlib.sha256(value.encode()).hexdigest()[:12],
                        }
                    )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    args = parser.parse_args()
    findings = scan(args.root.resolve())
    print(json.dumps({"finding_count": len(findings), "findings": findings}, indent=2))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
