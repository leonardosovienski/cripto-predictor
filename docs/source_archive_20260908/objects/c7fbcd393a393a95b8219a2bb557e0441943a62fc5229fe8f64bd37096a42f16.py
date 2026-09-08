import hashlib
import json
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "work/cripto-research"
RUN = ROOT / "work/profit-comparison-v1"
EVIDENCE = REPO / "docs/evidence/profit_comparison_20260908"
OUTPUTS = ROOT / "outputs"
ORIGINAL = ROOT.parent / "files-mentioned-by-the-user-cripto/work/cripto-v1.2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, obj):
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ORIGINAL), *args], text=True).strip()


old = read(OUTPUTS / "ENTREGA_SHA256.json")
assert sha(OUTPUTS / old["package"]) == old["package_sha256"]
assert sha(OUTPUTS / "CRIPTO_RESULTADOS.md") == old["report_sha256"]
latest = read(OUTPUTS / "CRIPTO_BASIS_ENTREGA_SHA256.json")
for name, digest in latest["outputs"].items():
    assert sha(OUTPUTS / name) == digest, name
preserved = read(REPO / "docs/evidence/basis_research_20260908/preservation_before.json")
automation = Path("C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml")
assert sha(automation) == preserved["automation_sha256"]
assert git("status", "--porcelain") == ""
assert git("rev-parse", "HEAD") == preserved["original_head"]
assert git("rev-parse", "main") == preserved["main_head"]
ledger_sha = sha(ORIGINAL.parent / "altcoin-reviewed-data/ledger.jsonl")
assert ledger_sha == "42e96f95f1765784e12cbf9fed2d77d26cbd0f268bbbaf46bcdf3715ec6141a5"

comparison = read(RUN / "comparison.json")
verification = {
    "checked_utc": datetime.now(UTC).isoformat(),
    "code_commit_at_replay": subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
    "executed_this_request": {
        "pytest": {
            "command": "python -m pytest tests/test_btc_basis.py tests/test_btc_execution_plan.py tests/test_absolute_research.py -q",
            "exit_code": 0,
            "passed": 42,
            "seconds_reported_by_pytest": 1.74,
            "full_repository_suite_run": False,
        },
        "ruff_comparison_script": "PASS",
        "pyright_comparison_script": "0 errors, 0 warnings, 0 informations",
        "economics": comparison["verification"],
    },
    "preservation": {
        "original_repository_clean": True,
        "original_head": git("rev-parse", "HEAD"),
        "main_head": git("rev-parse", "main"),
        "automation_sha256_unchanged": sha(automation),
        "observer_ledger_sha256_unchanged": ledger_sha,
        "observer_runtime_verification_this_request": {"status": "PASS", "files_checked": 3785},
        "previous_packages_and_reports_hashes_verified": True,
    },
}
write(EVIDENCE / "validation.json", verification)
for source, target in (
    (RUN / "comparison.json", EVIDENCE / "comparison.json"),
    (RUN / "run_receipt.json", EVIDENCE / "run_receipt.json"),
    (OUTPUTS / "CRIPTO_COMPARACAO_LUCRO.md", EVIDENCE / "DECISAO.md"),
    (RUN / "comparison.json", OUTPUTS / "CRIPTO_COMPARACAO_LUCRO.json"),
):
    assert not target.exists()
    target.write_bytes(source.read_bytes())
write(OUTPUTS / "CRIPTO_COMPARACAO_VERIFICACAO.json", verification)

instructions = """Comparação de lucro — reprodução

Este ZIP é um complemento de código e evidência. Não substitui os dois pacotes anteriores nem contém novamente seus dados ou o interpretador.
Requer o worktree de pesquisa preservado, seus scripts congelados e os três diretórios de dados já existentes: carry-research-data, basis-research-data e btc-execution-diagnostic-v1. Os pacotes anteriores CRIPTO_CODIGO_DADOS_REPRODUCAO.zip e CRIPTO_BASIS_IMPLEMENTACAO.zip continuam com os dados e instruções de restauração próprios.

No worktree C:/Users/Superleo13/Documents/Codex/2026-09-07/files-pasted-by-the-user-quero/work/cripto-research, com Python 3.13.14, NumPy 2.5.1 e httpx 0.28.1 instalados:

python -m scripts.compare_absolute_profit --carry-data ../carry-research-data --basis-data ../basis-research-data --diagnostic ../btc-execution-diagnostic-v1 --output ../profit-comparison-NOVA-PASTA

A pasta de saída deve ser nova. O comando bloqueia conexões de rede, reproduz 12 cenários antigos e seis novos, verifica 23 arquivos históricos byte a byte, executa a auditoria Decimal separada e reproduz os 12 planos de quantidades usando cotações salvas. comparison.json é determinístico; run_receipt.json tem a data da nova execução.

Testes de software (pytest 8.4.2):
python -m pytest tests/test_btc_basis.py tests/test_btc_execution_plan.py tests/test_absolute_research.py -q

Não alterar arquivos congelados nem recalcular hashes para aceitar diferenças. Este comparador não baixa evidência futura, não procura parâmetros, não envia ordens e não produz previsão validada de lucro. Os resultados são históricos e adaptativos.
"""
(EVIDENCE / "REPRODUZIR.txt").write_text(instructions, encoding="utf-8")
files = {"scripts/compare_absolute_profit.py": REPO / "scripts/compare_absolute_profit.py"}
files.update({"evidence/" + p.name: p for p in EVIDENCE.iterdir() if p.is_file()})
package = OUTPUTS / "CRIPTO_COMPARACAO_EVIDENCIAS.zip"
assert not package.exists()
with zipfile.ZipFile(package, "x", compression=zipfile.ZIP_DEFLATED) as archive:
    for name, path in sorted(files.items()):
        archive.writestr(name, path.read_bytes())
    archive.writestr("FILES_SHA256.json", json.dumps({n: sha(p) for n, p in sorted(files.items())}, indent=2))
with zipfile.ZipFile(package) as archive:
    recorded = json.loads(archive.read("FILES_SHA256.json"))
    for name, digest in recorded.items():
        assert hashlib.sha256(archive.read(name)).hexdigest() == digest
write(OUTPUTS / "CRIPTO_COMPARACAO_SHA256.json", {
    "verified_package_files": len(recorded),
    "outputs": {p.name: sha(p) for p in sorted(OUTPUTS.glob("CRIPTO_COMPARACAO*")) if p.is_file()},
})
print(json.dumps({"status": "PASS", "package_files_checked": len(recorded), "package_bytes": package.stat().st_size, "preservation": verification["preservation"]}, indent=2))
