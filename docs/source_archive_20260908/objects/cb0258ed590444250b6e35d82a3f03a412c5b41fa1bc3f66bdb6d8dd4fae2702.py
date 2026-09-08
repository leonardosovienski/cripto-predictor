import argparse
import hashlib
import json
import shutil
import subprocess
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

WORK = Path(__file__).resolve().parent
REPO = WORK / "cripto-v1.2"
OUT = WORK.parent / "outputs"
EVIDENCE = REPO / "docs/evidence/project_review_20260907"
BASE = "5d28a63c1b2a147d17054ace3914de698a7959a4"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
dump = lambda p, x: p.write_text(json.dumps(x, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def stage():
    full = (WORK / "review-final-tests.txt").read_text(encoding="utf-8")
    minimal = (WORK / "review-ci-tests.txt").read_text(encoding="utf-8")
    assert "1045 passed" in full and "failed" not in full.lower()
    assert "1011 passed, 4 skipped" in minimal
    runtime = read(EVIDENCE / "runtime_integrity.json")
    assert all(not r["mismatches"] and not r["missing"] for r in runtime.values())
    for log in ("review-build-final.txt", "review-uv-build-final.txt"):
        assert "Successfully built" in (WORK / log).read_text(encoding="utf-8")
    for source, name in (
        ("review-final-tests.txt", "full_tests.txt"),
        ("review-ci-tests.txt", "minimal_ci_tests.txt"),
        ("review-regressions-before.txt", "recovery_controls_before_fix.txt"),
        ("review-runtime-integrity.json", "runtime_integrity_before.json"),
        ("review-runtime-repair.json", "runtime_repair.json"),
        ("review-build-final.txt", "python_build.txt"),
        ("review-uv-build-final.txt", "uv_build.txt"),
        ("review-secret-scan.json", "secret_scan.json"),
    ):
        shutil.copyfile(WORK / source, EVIDENCE / name)
    shutil.copyfile(WORK / "altcoin-reviewed-data/status.json", EVIDENCE / "observer_status.json")
    shutil.copyfile(WORK / "review-retro-replay/audit.json", EVIDENCE / "retrospective_audit.json")
    config = tomllib.loads(Path("C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml").read_text(encoding="utf-8"))
    assert config["status"] == "ACTIVE"
    assert "altcoin-reviewed-data" in config["prompt"] and "scripts.verify_research_runtime" in config["prompt"]
    assert config["rrule"] == "FREQ=WEEKLY;BYDAY=SU;BYHOUR=21;BYMINUTE=0;BYSECOND=0"
    automation = {"id": config["id"], "name": config["name"], "status": config["status"],
                  "profile": "altcoin_reviewed_20260907", "schedule": "Domingos às 21h America/Sao_Paulo",
                  "first_entry": "2026-09-13 21:00 America/Sao_Paulo", "final_exit": "2026-12-06 21:00 America/Sao_Paulo",
                  "prompt_sha256": hashlib.sha256(config["prompt"].encode()).hexdigest(),
                  "notification_intent": "Somente mudança relevante, falha, conclusão ou informação necessária",
                  "target_thread_id": config["target_thread_id"]}
    dump(EVIDENCE / "automation.json", automation)
    validation = {
        "as_of_utc": datetime.now(timezone.utc).isoformat(), "base_commit": BASE,
        "full_suite": {"passed": 1045, "failed": 0, "skipped": 0, "source": "full_tests.txt"},
        "isolated_minimal_ci_profile": {"passed": 1011, "skipped": 4, "extras": ["test", "science"], "source": "minimal_ci_tests.txt"},
        "observer_review_controls": {"passed": 28, "includes": "OS lock crash recovery, concurrency, missingness, full 12-slot lifecycle, loss accounting and idempotency"},
        "ruff": "PASS", "ruff_format": "PASS", "pyright": "PASS",
        "build_uv": "PASS", "build_python_isolated": "PASS_AFTER_EXACT_RUNTIME_REPAIR",
        "installed_wheel_outside_checkout": "PASS",
        "wheel_sha256": sha(WORK / "review-build/cripto_predictor-1.0.0-py3-none-any.whl"),
        "runtime_integrity": {"status": "PASS", "files_checked": sum(r["files_checked"] for r in runtime.values())},
        "secret_scan_findings": read(EVIDENCE / "secret_scan.json")["finding_count"],
        "historical_replay": "BYTE_IDENTICAL", "live_snapshot_offline_replay": "PASS",
        "docker": "NOT_VALIDATED: daemon unavailable; Windows denied service startup",
        "remote_ci": "NOT_EXECUTED", "posix_lock_branch": "NOT_EXECUTED_ON_WINDOWS",
        "new_model_searches": 0, "profit_attestation": False, "capital": False,
    }
    dump(EVIDENCE / "validation.json", validation)
    title = "### 2026-09-07 — Final project review and operational v6"
    history = REPO / "docs/HYPOTHESES.md"
    assert title not in history.read_text(encoding="utf-8")
    with history.open("a", encoding="utf-8") as stream:
        stream.write("\n\n" + title + "\n\n" + """User requests complete review, justified changes, execution and validation. Registered in 3179b1d before corrections. Seven initial failing controls comprised two demonstrated stale-lock recovery failures and five missing accounting capabilities. Operational fixes and regression controls landed in d81ba94: OS-released persistent-file advisory lock, coverage-aware 12-slot accounting, failed-run status and required science dependencies in CI. No model/threshold/cost/search change. The complete lifecycle tests use synthetic quotes and do not manufacture future observations.

Economic correction: the previous BTC/ETH carry rejection used an external benchmark subsequently rejected by the user. Independent Decimal reconciliation of the same eight original raw responses confirms +54.84071944 USDT (+1.0968%) BTC and +34.62367591 USDT (+0.6925%) ETH per separate hypothetical 5000-USDT scenario over 2025-09-07 to 2026-09-07, after assumed transaction fees/slippage. Account costs, conversion, taxes, margin viability and actual fills remain unverified. This is an adaptive interpretation of consumed evidence, not a new independent strategy success. Original negative-priority report and all raw sources remain intact. No verified investor net profit is claimed.

The v5 retrospective was replayed with identical results/decisions/scores; independent audit reconfirmed zero trades and zero simulated profit in 140 weeks. No threshold was relaxed to force trades. New operational v6 preflight: 487 current pairs, 472 after exclusions, 44 eligible, zero selected; 616 public response hashes, 44 independent entry-book calculations, exact cached snapshot reproduction and ledger integrity pass. The same existing automation now uses a separate reviewed data directory/profile, with original dates and notification intent preserved. No prospective decisions or outcomes exist yet.

Final all-extras suite: 1045 passed, zero failed/skipped. Separate test+science installation: 1011 passed, four optional skips. Ruff/format/Pyright, two build routes, wheel installation outside checkout and 3785 runtime file checks pass. A local integrity discrepancy in distlib/virtualenv broke the generic build path; exact lockfile-SHA-verified wheels were restored via uncached copies, after which integrity and build passed. No unsupported cause is inferred. Docker daemon was unavailable and Windows denied starting its service; container, POSIX lock branch and remote CI are explicitly unvalidated. Six prior reproduction archives and eleven protected scientific/model files were verified unchanged. Details: docs/evidence/project_review_20260907 and docs/PROJECT_STATE_20260907.md.
""")
    report = """# Revisão final do projeto de cripto — 07/09/2026

**A revisão foi executada, as correções foram aplicadas e os testes locais passaram. Ainda não há lucro real comprovado. Há dois cenários históricos de carry positivos após custos de negociação assumidos.**

| Estudo | Capital hipotético | Resultado |
|---|---:|---:|
| Seletor atual de altcoins, 140 semanas de 2024 a setembro/2026 | 5.000 USDT | **0 USDT / 0%**, nenhuma operação |
| Carry BTC, setembro/2025 a setembro/2026 | 5.000 USDT | **+54,84 USDT / +1,10%** |
| Carry ETH, mesmo ano | 5.000 USDT | **+34,62 USDT / +0,69%** |

Cada linha é um cenário separado; os ganhos não devem ser somados como se usassem os mesmos 5.000 USDT. Carry, aqui, combina uma posição na moeda com uma posição vendida equivalente em contrato perpétuo. Os números usam preços de referência, taxas e deslizamento assumidos; não foram operações realizadas.

## A conclusão que precisava mudar

O carry havia sido descartado por não superar uma comparação externa. Você depois retirou essa exigência. **Eu deveria ter trazido os seus saldos positivos de volta à conclusão geral. Corrigi essa omissão e refiz a conta a partir dos dados brutos.** O objetivo agora é somente lucro absoluto.

Isso ainda não confirma lucro líquido real: faltam custos efetivos da conta, conversões/transferências, impostos e comprovação da execução e da margem ao longo do caminho. No BTC, apenas 54,84 USDT de custos adicionais eliminariam o ganho do cenário; no ETH, 34,62 USDT. Os dados já foram consultados na pesquisa, portanto são diagnóstico histórico, não validação independente nem promessa futura.

## O que foi corrigido e validado

- Recuperação do observador após encerramento brusco, mantendo a proteção contra duas execuções simultâneas.
- Balanço que distingue semanas conhecidas, perdidas, com posições e em caixa. Falta de observação não vira lucro zero; término do calendário não vira aprovação.
- Registro atualizado quando a coleta falha. A soma de experimentos semanais de tamanho fixo não é apresentada como saldo de uma conta capitalizada.
- Dependências científicas do CI e arquivos inconsistentes de duas ferramentas de empacotamento. As versões fixadas foram restauradas e receberam checagem permanente de integridade.
- Acompanhamento existente atualizado para a versão corrigida, mantendo datas e preferências de aviso. O novo preflight encontrou 44 candidatos elegíveis e nenhuma seleção.

**Validação final: 1.045 testes passaram, sem falhas ou pulos.** Também passaram lint, formatação, checagem de tipos, geração do pacote, instalação fora da pasta de código, verificação de 3.785 arquivos do ambiente e reprodução dos cálculos. Um ambiente mínimo separado passou em 1.011 testes, com quatro pulos por dependências opcionais. Os seis pacotes históricos anteriores foram preservados.

Docker e CI remoto não foram validados: o serviço local do Docker não ficou acessível e o Windows negou sua inicialização. Não considero essas verificações aprovadas.

## Qualidade final e lucro

**A infraestrutura funciona como ferramenta de pesquisa e simulação nos controles locais executados. A rentabilidade do projeto ainda não está comprovada.** O seletor atual não mostrou capacidade de lucrar; eu não afrouxei seus filtros para fabricar entradas. O carry apresentou saldos históricos positivos pequenos, ainda dependentes de hipóteses de custo e execução.

O acompanhamento futuro permanece agendado para domingo às 21h de Brasília, primeira janela em 13/09 e última saída em 06/12. Não há observações futuras ainda. Testar o ciclo inteiro com dados sintéticos valida o software, não antecipa esses resultados. O computador e o app precisam estar ativos para a automação local. [Documentação oficial](https://learn.chatgpt.com/docs/automations?surface=app).

Nenhuma ordem, conta, transferência ou capital foi ativado. A conclusão é: **simulação positiva de carry existe; lucro real comprovado ainda não.**
"""
    (OUT / "CRIPTO_REVISAO_FINAL.md").write_text(report, encoding="utf-8")
    combined = {"validation": validation, "carry": read(EVIDENCE / "carry_absolute_profit.json"),
                "reconciliation": read(EVIDENCE / "reconciliation.json"),
                "observer_status": read(EVIDENCE / "observer_status.json"), "automation": automation,
                "conclusion": "HISTORICAL_CARRY_SCENARIOS_POSITIVE; CURRENT_SELECTOR_ZERO_TRADES; NO_VERIFIED_REAL_PROFIT"}
    dump(OUT / "CRIPTO_REVISAO_FINAL.json", combined)
    tracking = OUT / "ACOMPANHAMENTO_CRIPTO.md"
    archive = OUT / "ACOMPANHAMENTO_CRIPTO_V5_20260907.md"
    if not archive.exists():
        shutil.copyfile(tracking, archive)
    tracking.write_text("""# Acompanhamento cripto — estado após revisão final

**Lucro real ainda não comprovado.** O seletor atual fez zero operações em 140 semanas históricas: lucro simulado zero. Os estudos separados de carry mostram +54,84 USDT no BTC e +34,62 USDT no ETH, cada um sobre 5.000 USDT hipotéticos durante um ano, após custos assumidos. A antiga rejeição por comparação externa foi revista; não há comprovação de lucro real após execução, conversão e impostos.

A revisão aplicou correções de recuperação após interrupção, registro de falhas, integridade do ambiente e contabilização das 12 janelas. Passaram 1.045 testes. O preflight atualizado teve 44 candidatos elegíveis e zero selecionados. O perfil ativo é altcoin_reviewed_20260907, com dados em work/altcoin-reviewed-data; versões anteriores foram preservadas.

Primeira janela: 13/09/2026 às 21h de Brasília. Última saída: 06/12 às 21h. Computador e aplicativo precisam estar ativos. Nenhuma observação futura existe ainda. Ausências continuarão desconhecidas e serão relatadas; terminar as 12 semanas não garante lucro. Avisos apenas em mudança relevante, falha, conclusão ou necessidade de informação.

Relatório completo: CRIPTO_REVISAO_FINAL.md. Evidências: CRIPTO_REVISAO_FINAL.json. Reprodução: CRIPTO_REVISAO_FINAL_REPRODUCAO.zip. Registros anteriores deste acompanhamento estão nas cópias V3, V4 e V5.
""", encoding="utf-8")
    print(json.dumps({"validation": validation["full_suite"], "automation": automation["status"]}))


def package():
    stage_dir = WORK / "project-review-package"
    stage_dir.mkdir(exist_ok=True)
    def copy(source, relative):
        target = stage_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO).decode().split("\0")
    for relative in files:
        if relative and (REPO / relative).is_file():
            copy(REPO / relative, Path("project") / relative)
    for source, name in (("altcoin-retro-data", "retro"), ("altcoin-reviewed-data", "forward-reviewed"), ("carry-data", "carry")):
        for path in sorted((WORK / source).rglob("*")):
            if path.is_file() and path.name != "observer.lock":
                copy(path, Path("data") / name / path.relative_to(WORK / source))
    copy(WORK / "altcoin-data/acquisition.json", "data/base/acquisition.json")
    copy(WORK / "altcoin-payoff-results/samples_identity_corrected.json.gz", "data/training/samples_identity_corrected.json.gz")
    for path in (WORK / "review-retro-replay").iterdir():
        if path.is_file():
            copy(path, Path("expected/retro") / path.name)
    copy(EVIDENCE / "carry_absolute_profit.json", "expected/carry.json")
    copy(WORK / "review-build/cripto_predictor-1.0.0-py3-none-any.whl", "wheel/cripto_predictor-1.0.0-py3-none-any.whl")
    copy(OUT / "CRIPTO_REVISAO_FINAL.md", "RELATORIO.md")
    copy(OUT / "CRIPTO_REVISAO_FINAL.json", "RESULTADOS.json")
    copy(WORK / "reproduce_project_review.py", "reproduce_review.py")
    for name in ("deliver_project_review.py", "audit_review_state.py", "prepare_review_profile.py", "repair_review_build_runtime.py"):
        copy(WORK / name, Path("provenance") / name)
    (stage_dir / "README.md").write_text("""# Reprodução da revisão final

Leia RELATORIO.md. A revisão não autorizou capital, ordens ou contas. Dados históricos e preflight são preservados; o script de reprodução não consulta rede.

Python usado: 3.13.14. A instalação inicial exige rede para obter as dependências exatas do uv.lock. O modo sem cache e com cópias evita reutilizar arquivos de um cache local alterado. Execute a partir desta pasta:

```powershell
cd project
uv sync --locked --all-extras --no-cache --link-mode copy
uv run --no-sync python ../reproduce_review.py
```

O script confere os arquivos, reproduz o teste retrospectivo e a conta independente de carry, reconstrói o snapshot a partir das respostas preservadas e executa os 62 testes de seleção/observação. Confere hashes e decisões contra expected/. Ele não reexecuta a coleta futura nem altera qualquer ledger. Não use python -O nos auditores.

O código completo está em project/, os insumos em data/, resultados esperados em expected/ e a wheel em wheel/. Para a suíte completa, use o ambiente instalado e execute `python -m pytest -q tests` dentro de project. O teste de integridade do ambiente é `python -m scripts.verify_research_runtime`.

As referências absolutas nos ledgers são proveniência original e permanecem intactas. A reprodução localiza o snapshot arquivado pelo nome e confirma seu hash; ela não migra nem continua o ledger original. Uma nova observação deve usar diretório de dados novo e o protocolo correto. Os scripts em provenance/ registram como a entrega foi montada na máquina original, não são os comandos portáveis de reprodução.

1045 testes locais completos passaram; a execução selecionada de 62 testes neste pacote não substitui o registro da suíte completa. Docker, branch POSIX do bloqueio e CI remoto não foram validados na máquina Windows. Resultados positivos simulados de carry não comprovam margem executável, custos reais, impostos ou lucro do investidor. Zero operações do seletor não fornece taxa de acerto.
""", encoding="utf-8")
    checksum = {p.relative_to(stage_dir).as_posix(): sha(p) for p in sorted(stage_dir.rglob("*")) if p.is_file() and p.name != "FILES_SHA256.json"}
    dump(stage_dir / "FILES_SHA256.json", checksum)
    archive = OUT / "CRIPTO_REVISAO_FINAL_REPRODUCAO.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(stage_dir.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(stage_dir).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(json.dumps({"archive": str(archive), "sha256": sha(archive), "bytes": archive.stat().st_size, "files": len(checksum) + 1}))


def manifest():
    patch = subprocess.check_output(["git", "diff", "--binary", BASE, "HEAD"], cwd=REPO)
    (OUT / "CRIPTO_REVISAO_FINAL.patch").write_bytes(patch)
    names = ("CRIPTO_REVISAO_FINAL.md", "CRIPTO_REVISAO_FINAL.json", "CRIPTO_REVISAO_FINAL.patch", "CRIPTO_REVISAO_FINAL_REPRODUCAO.zip", "ACOMPANHAMENTO_CRIPTO.md", "ACOMPANHAMENTO_CRIPTO_V5_20260907.md")
    dump(OUT / "CRIPTO_REVISAO_FINAL_MANIFESTO.json", {
        "base_commit": BASE, "head_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "files": {name: {"sha256": sha(OUT / name), "bytes": (OUT / name).stat().st_size} for name in names},
        "standalone_reproduction": read(WORK / "review-package-check.json"),
        "profit": "Historical carry scenarios positive; real investor net profit unverified",
    })
    print("Final manifest saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("stage", "package", "manifest"))
    args = parser.parse_args()
    {"stage": stage, "package": package, "manifest": manifest}[args.mode]()
