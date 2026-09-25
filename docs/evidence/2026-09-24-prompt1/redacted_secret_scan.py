"""Varredura local de segredos, SEM imprimir valores (substituto do gitleaks/trufflehog, ausentes).

Só leitura de objetos Git (git cat-file). Nada de rede, nada de .env, nenhum código do repo executado.
Para cada achado registra só: regra, arquivo, linha, commit que introduziu o conteúdo, se o conteúdo
ainda está no HEAD, e a "forma" do valor (tamanho e classes de caracteres), nunca o valor nem hash dele.

Uso: python redacted_secret_scan.py <repo> <saida.json>
"""
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict

repo, out_path = sys.argv[1], sys.argv[2]
MAX_BLOB = 3_000_000

RULES = {
    "google_api_key": re.compile(rb"AIza[0-9A-Za-z_\-]{35}"),
    "openai_like_key": re.compile(rb"\bsk-(?:proj-|or-v1-)?[A-Za-z0-9_\-]{20,}"),
    "groq_key": re.compile(rb"\bgsk_[A-Za-z0-9]{20,}"),
    "cerebras_key": re.compile(rb"\bcsk-[A-Za-z0-9]{20,}"),
    "huggingface_token": re.compile(rb"\bhf_[A-Za-z0-9]{30,}"),
    "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    "aws_access_key": re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "slack_token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9\-]{10,}"),
    "private_key_block": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "telegram_bot_token": re.compile(rb"\b\d{8,10}:AA[A-Za-z0-9_\-]{33}\b"),
    "webhook_url": re.compile(rb"https://(?:discord(?:app)?\.com/api/webhooks|hooks\.slack\.com/services|api\.telegram\.org/bot)[^\s\"'<>]{10,}"),
    "credential_assignment": re.compile(
        rb"(?i)(?<![a-z0-9_])(?:[a-z0-9]+[_-])*(?:api[_-]?key|apikey|secret|token|passw(?:or)?d|auth)[\"']?\s*[:=]\s*[\"']([A-Za-z0-9_\-\.\+/=]{20,})[\"']"),
}
PLACEHOLDER = re.compile(rb"(?i)(your|example|placeholder|dummy|fake|test|xxxx|changeme|redact|synthetic|sample|mock|<|\$\{)")


def git(*args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", repo, *args], input=data, capture_output=True, check=True).stdout


def entropy(value: bytes) -> float:
    counts = Counter(value)
    return -sum(c / len(value) * math.log2(c / len(value)) for c in counts.values())


def shape(value: bytes) -> str:
    classes = "".join(k for k, pat in (("a", rb"[a-z]"), ("A", rb"[A-Z]"), ("9", rb"[0-9]"), ("_", rb"[_\-\.\+/=]"))
                      if re.search(pat, value))
    return f"len={len(value)} classes={classes} entropia={entropy(value):.1f}"


# objetos alcançáveis por qualquer ref (inclui o histórico inteiro)
objects = git("rev-list", "--all", "--objects").decode("utf-8", "replace").splitlines()
blob_paths: dict[str, set[str]] = defaultdict(set)
for line in objects:
    sha, _, path = line.partition(" ")
    if path:
        blob_paths[sha].add(path)
meta = git("cat-file", "--batch-check", data="\n".join(blob_paths).encode()).decode().splitlines()
blobs = [m.split()[0] for m in meta if m.split()[1] == "blob" and int(m.split()[2]) <= MAX_BLOB]
skipped_large = [m.split()[0] for m in meta if m.split()[1] == "blob" and int(m.split()[2]) > MAX_BLOB]

findings = []
scanned = binary = 0
proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
for sha in blobs:
    proc.stdin.write(sha.encode() + b"\n"); proc.stdin.flush()
    header = proc.stdout.readline().split()
    size = int(header[2]); content = proc.stdout.read(size); proc.stdout.read(1)
    if b"\x00" in content[:8000]:
        binary += 1
        continue
    scanned += 1
    for number, line in enumerate(content.splitlines(), 1):
        for rule, pattern in RULES.items():
            for m in pattern.finditer(line):
                value = m.group(1) if m.groups() else m.group(0)
                if rule == "credential_assignment" and (PLACEHOLDER.search(value) or entropy(value) < 3.5
                                                        or not re.search(rb"[0-9]", value)):
                    continue
                findings.append({"blob": sha, "rule": rule, "line": number, "shape": shape(value),
                                 "placeholder_like": bool(PLACEHOLDER.search(value) or PLACEHOLDER.search(line[:m.start()][-40:]))})
proc.stdin.close(); proc.wait()

head_blobs = {}
for line in git("ls-tree", "-r", "HEAD").decode("utf-8", "replace").splitlines():
    info, path = line.split("\t", 1)
    head_blobs[path] = info.split()[2]

report = []
for sha in sorted({f["blob"] for f in findings}):
    intro = git("log", "--all", "--reverse", "--format=%H", f"--find-object={sha}").decode().split()
    for f in (x for x in findings if x["blob"] == sha):
        for path in sorted(blob_paths[sha]):
            report.append({**{k: v for k, v in f.items() if k != "blob"}, "file": path,
                           "first_commit": intro[0][:12] if intro else None,
                           "in_head": head_blobs.get(path) == sha})
json.dump({"repo_head": git("rev-parse", "HEAD").decode().strip(), "refs_scanned": "all (git rev-list --all)",
           "blobs_total": len(blob_paths), "blobs_scanned_text": scanned, "blobs_binary_skipped": binary,
           "blobs_over_3MB_skipped": len(skipped_large), "rules": sorted(RULES), "findings": report},
          open(out_path, "w"), indent=1)
print(json.dumps({"blobs_text": scanned, "binary": binary, "large_skipped": len(skipped_large),
                  "findings": len(report), "by_rule": Counter(r["rule"] for r in report)}, default=str))
