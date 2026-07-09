"""Blindagem de regressao — CI minima local (portada do wc-predictor-v2).

Roda as barreiras que impedem a reintroducao dos bugs ja corrigidos AQUI:
  1. pytest — a suite inteira (241+ testes, inclui repo hygiene e o schema
     do Experiment Registry) tem que passar.
  2. .ps1 em ASCII puro — o agendador GarimpoV3Daily falhou em 27/06/2026
     (exit 1, sem log) porque o PowerShell 5.1 le .ps1 sem BOM como
     Windows-1252: bytes UTF-8 multibyte (em-dash, acentos) viram aspas
     soltas e corrompem o parse ANTES de executar (incidente V3.3.2).
     A suite pytest nao cobre o entry-point real do agendador — esta
     barreira cobre.
  3. Parse real dos .ps1 — [Parser]::ParseFile na invocacao identica a do
     schtasks; pega qualquer erro de sintaxe, nao so encoding (pulado com
     WARN se o powershell nao estiver no PATH).

Uso:
    python scripts/ci_check.py            # tudo
    python scripts/ci_check.py --fast     # pula o pytest (so barreiras estaticas)
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

failures: list[str] = []
warnings_: list[str] = []


def check_pytest() -> None:
    print("[1/3] pytest (suite completa)...")
    env = dict(os.environ)
    # A suite importa predictor_core do vendor e o pacote da raiz.
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "vendor"), str(ROOT), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    tail = (r.stdout or "").strip().splitlines()[-1:] or ["(sem saida)"]
    print(f"      {tail[0]}")
    if r.returncode != 0:
        failures.append(f"pytest falhou (exit {r.returncode}) — rode: python -m pytest tests/")


def check_ps1_ascii() -> None:
    print("[2/3] .ps1 em ASCII puro (incidente V3.3.2)...")
    scripts = sorted((ROOT / "scripts").glob("*.ps1"))
    if not scripts:
        warnings_.append("nenhum .ps1 em scripts/ — layout mudou?")
        print("      (nenhum .ps1)")
        return
    for f in scripts:
        data = f.read_bytes()
        bad = [(i, b) for i, b in enumerate(data) if b > 127]
        if bad:
            i, b = bad[0]
            line = data[:i].count(b"\n") + 1
            failures.append(
                f"scripts/{f.name}: {len(bad)} byte(s) nao-ASCII (1o: 0x{b:02x} "
                f"na linha {line}) — PowerShell 5.1 le sem BOM como cp1252 e "
                f"corrompe o parse; reescreva sem acentos/travessoes")
    print(f"      {len(scripts)} script(s) verificados")


def check_ps1_parse() -> None:
    print("[3/3] parse real dos .ps1 ([Parser]::ParseFile)...")
    pwsh = shutil.which("powershell") or shutil.which("pwsh")
    if not pwsh:
        warnings_.append("parse dos .ps1 PULADO: powershell nao encontrado no PATH")
        print("      PULADO (sem powershell)")
        return
    scripts = sorted((ROOT / "scripts").glob("*.ps1"))
    for f in scripts:
        cmd = (
            "$e=$null;"
            f"[void][System.Management.Automation.Language.Parser]::ParseFile('{f}',[ref]$null,[ref]$e);"
            "if($e){$e|ForEach-Object{$_.Message};exit 1}"
        )
        r = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", cmd],
                           capture_output=True, text=True)
        if r.returncode != 0:
            msg = (r.stdout or r.stderr or "").strip().splitlines()[:1]
            failures.append(f"scripts/{f.name}: erro de parse — {msg} "
                            f"(o agendador sairia 1 sem criar log)")
    print(f"      {len(scripts)} script(s) parseados")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="pula o pytest")
    args = ap.parse_args()

    if not args.fast:
        check_pytest()
    else:
        print("[1/3] pytest PULADO (--fast)")
    check_ps1_ascii()
    check_ps1_parse()

    print()
    for w in warnings_:
        print(f"WARN: {w}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        print(f"\nCI: {len(failures)} falha(s) — commit bloqueado.")
        return 1
    print("CI: todas as barreiras verdes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
