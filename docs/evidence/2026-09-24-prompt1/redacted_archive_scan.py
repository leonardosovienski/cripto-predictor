"""Varredura de segredos DENTRO dos arquivos compactados do histórico Git (zip/gz/whl, aninhados),
em memória, sem gravar nada e sem imprimir valores. Complementa redacted_secret_scan.py.

Uso: python redacted_archive_scan.py <repo> <saida.json>
"""
import gzip
import io
import json
import math
import re
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict

repo, out_path = sys.argv[1], sys.argv[2]
RULES = {
    "google_api_key": re.compile(rb"AIza[0-9A-Za-z_\-]{35}"),
    "openai_like_key": re.compile(rb"\bsk-(?:proj-|or-v1-)?[A-Za-z0-9_\-]{20,}"),
    "groq_key": re.compile(rb"\bgsk_[A-Za-z0-9]{20,}"),
    "cerebras_key": re.compile(rb"\bcsk-[A-Za-z0-9]{20,}"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "aws_access_key": re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "private_key_block": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "telegram_bot_token": re.compile(rb"\b\d{8,10}:AA[A-Za-z0-9_\-]{33}\b"),
    "webhook_url": re.compile(rb"https://(?:discord(?:app)?\.com/api/webhooks|hooks\.slack\.com/services|api\.telegram\.org/bot)[^\s\"'<>]{10,}"),
    "credential_assignment": re.compile(
        rb"(?i)(?<![a-z0-9_])((?:[a-z0-9]+[_-])*(?:api[_-]?key|apikey|secret|token|passw(?:or)?d|auth))[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_\-\.\+/=]{20,})"),
}
PLACEHOLDER = re.compile(rb"(?i)(your|example|placeholder|dummy|fake|test|xxxx|changeme|redact|synthetic|sample|mock|<|\$\{)")
SENSITIVE_NAME = re.compile(r"(?i)(^|/)(\.env(\..*)?|pipeline\.env|.*\.pem|.*\.key|id_rsa.*|credentials?\..*|secrets?\..*)$")


def entropy(v: bytes) -> float:
    c = Counter(v)
    return -sum(n / len(v) * math.log2(n / len(v)) for n in c.values())


def scan_bytes(data: bytes, where: str, out: list, names: list, depth: int = 0) -> None:
    if depth > 6:
        return
    if data[:2] == b"\x1f\x8b":
        try:
            scan_bytes(gzip.decompress(data), where + "!gz", out, names, depth + 1)
        except Exception:
            out.append({"where": where, "rule": "UNREADABLE_GZ"})
        return
    if data[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    if SENSITIVE_NAME.search(info.filename):
                        names.append(f"{where}!{info.filename}")
                    try:
                        scan_bytes(z.read(info), f"{where}!{info.filename}", out, names, depth + 1)
                    except Exception:
                        out.append({"where": f"{where}!{info.filename}", "rule": "UNREADABLE_MEMBER"})
        except zipfile.BadZipFile:
            out.append({"where": where, "rule": "BAD_ZIP"})
        return
    if b"\x00" in data[:8000]:
        return  # binário não textual (sqlite, parquet, imagem): fora do alcance desta varredura
    for number, line in enumerate(data.splitlines(), 1):
        for rule, pattern in RULES.items():
            for m in pattern.finditer(line):
                value = m.group(2) if rule == "credential_assignment" else m.group(0)
                if rule == "credential_assignment":
                    if PLACEHOLDER.search(value) or entropy(value) < 3.5 or not re.search(rb"[0-9]", value):
                        continue
                    if m.group(1).lower() == b"a_token" and re.fullmatch(rb"0x[0-9a-fA-F]{40}", value):
                        continue
                out.append({"where": where, "line": number, "rule": rule,
                            "shape": f"len={len(value)} entropia={entropy(value):.1f}",
                            "key_name": m.group(1).decode("utf-8", "replace")[:40] if rule == "credential_assignment" else None,
                            "sequential_like": sum(1 for a, b in zip(value, value[1:]) if b == a + 1) > len(value) * 0.6})


objs = subprocess.run(["git", "-C", repo, "rev-list", "--all", "--objects"], capture_output=True, text=True).stdout.splitlines()
paths = {}
for l in objs:
    s, _, p = l.partition(" ")
    if p:
        paths[s] = p
archives = [s for s, p in paths.items() if re.search(r"\.(zip|gz|whl|tgz|001|002)$", p)]
findings, names, seen = [], [], 0
parts = defaultdict(dict)
for s in archives:
    data = subprocess.run(["git", "-C", repo, "cat-file", "blob", s], capture_output=True).stdout
    p = paths[s]
    if re.search(r"\.(001|002)$", p):
        parts[p[:-4]][p[-3:]] = data
        continue
    seen += 1
    scan_bytes(data, p, findings, names)
for base, pieces in parts.items():
    seen += 1
    scan_bytes(b"".join(pieces[k] for k in sorted(pieces)), base + "(.001+.002)", findings, names)
json.dump({"archives_scanned": seen, "sensitive_member_names": names, "findings": findings}, open(out_path, "w"), indent=1)
print(json.dumps({"archives": seen, "sensitive_names": len(names), "findings": len(findings),
                  "by_rule": Counter(f["rule"] for f in findings)}))
