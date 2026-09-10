from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

PATTERNS = {
    "openai": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "google": re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    "github": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{16,}\b"),
    "credential_assignment": re.compile(
        r"(?i)(?<![a-z0-9_])"
        r"(?P<name>(?:[a-z0-9]+[_-])*(?:api[_-]?key|secret|token|password|"
        r"(?:access|auth|bearer|refresh)token))"
        r"[\"']?\s*[=:]\s*[\"']?(?P<value>[^\s\"'#,]{16,})"
    ),
}
ALLOWLIST = ("test-", "unit-test", "example", "placeholder", "dummy", "fake_", "synthetic", "your_")


def source_files(root: Path):
    """Scan publishable Git sources, not ignored environments and dependency caches.

    Outside a Git checkout, walk ordinary files without following directory links.
    Built archives have a separate byte-level security contract in the test suite.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "."],
            cwd=root,
            capture_output=True,
        )
    except FileNotFoundError:
        result = None
    if result is not None and result.returncode == 0:
        paths = (root / name for name in result.stdout.decode("utf-8").split("\0") if name)
    else:
        files = []
        for folder, directories, names in os.walk(root, followlinks=False):
            directories[:] = [
                name for name in directories if name not in {".git", ".venv", "__pycache__"}
            ]
            files.extend(Path(folder) / name for name in names)
        paths = iter(files)
    return sorted(
        {path for path in paths if path.is_file() and path.resolve().is_relative_to(root)}
    )


def scan(root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in source_files(root):
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
                    # Aave's a_token is a public EVM contract identity. An API
                    # token containing the same hexadecimal shape is still a
                    # credential; do not exempt arbitrary addresses or hashes.
                    if (
                        kind == "credential_assignment"
                        and match.group("name").lower() == "a_token"
                        and re.fullmatch(r"0x[0-9a-fA-F]{40}", value)
                    ):
                        continue
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
