"""Rebuild and exercise the exact Crypto/CAIN/Ecosystem combination in clean environments."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ECOSYSTEM = "821c7d7411ee983ef2c7ac03fa11083944826321"
CAIN = "5ba4177a11b9312900e5035517aa5ef25d509859"
OWNER = "https://github.com/leonardosovienski/"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def python_in(path):
    return path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--crypto-sha", required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    logs = work / "logs"
    logs.mkdir()
    scratch = work / "tmp"
    scratch.mkdir()
    env = os.environ.copy()
    for name in list(env):
        if any(
            part in name.upper() for part in ("API_KEY", "AUTH_TOKEN", "API_SECRET", "SECRET_KEY")
        ):
            env.pop(name)
    env.update(
        TEMP=str(scratch),
        TMP=str(scratch),
        TMPDIR=str(scratch),
        PIP_CACHE_DIR=str(work / "pip-cache"),
        UV_CACHE_DIR=str(work / "uv-cache"),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        SOURCE_DATE_EPOCH="1789171200",
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    receipts = []

    def run(name, command, cwd=work, extra=None, expected=0):
        command = list(map(str, command))
        start = datetime.now(UTC).isoformat()
        before = time.monotonic()
        log = logs / (name + ".log")
        print(name, flush=True)
        with log.open("wb") as output:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=env | (extra or {}),
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=1800,
                check=False,
            )
        record = dict(
            name=name,
            command=command,
            cwd=str(cwd),
            start=start,
            end=datetime.now(UTC).isoformat(),
            seconds=time.monotonic() - before,
            exit_code=result.returncode,
            expected_exit=expected,
            log=str(log.relative_to(work)),
            log_sha256=digest(log),
        )
        receipts.append(record)
        (work / "commands.json").write_text(json.dumps(receipts, indent=2), encoding="utf-8")
        if result.returncode != expected:
            print(log.read_text(errors="replace")[-12000:], flush=True)
            raise RuntimeError(f"{name}: exit {result.returncode}, expected {expected}")
        return log

    roots = {}
    sources = {}
    for name, repo, sha in (
        ("crypto", "cripto-predictor", args.crypto_sha),
        ("cain", "cain", CAIN),
        ("ecosystem", "ecosystem-predictor", ECOSYSTEM),
    ):
        root = work / name
        run(
            name + "-clone",
            ["git", "clone", "--filter=blob:none", "--no-checkout", OWNER + repo + ".git", root],
        )
        run(
            name + "-fetch-exact",
            [
                "git",
                "-c",
                "fetch.prune=false",
                "-c",
                "fetch.pruneTags=false",
                "fetch",
                "--no-prune",
                "--no-prune-tags",
                "origin",
                sha,
            ],
            root,
        )
        run(name + "-checkout", ["git", "checkout", "--detach", sha], root)
        tree = run(name + "-tree", ["git", "rev-parse", "HEAD^{tree}"], root).read_text().strip()
        status = run(name + "-status", ["git", "status", "--porcelain=v2"], root).read_text()
        assert not status, status
        roots[name] = root
        sources[name] = dict(repository=OWNER + repo, commit=sha, tree=tree, initial_status="clean")
    (work / "sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    crypto, cain, eco = [roots[x] for x in ("crypto", "cain", "ecosystem")]
    distributions = work / "distributions"
    distributions.mkdir()
    packages = {
        "snapshot": eco / "packages/research-snapshot",
        "bundle": eco / "packages/research-bundle",
        "exporter": crypto / "packages/research-export",
        "cain": cain,
    }
    runtime_supported = sys.version_info >= (3, 13)
    if runtime_supported:
        packages.update(crypto=crypto, ecosystem=eco)
    wheels = {}
    for name, root in packages.items():
        destination = distributions / name
        run(name + "-wheel-build", ["uv", "build", "--wheel", "--out-dir", destination], root)
        wheels[name] = next(destination.glob("*.whl"))
    for name in ("snapshot", "bundle"):
        again = distributions / (name + "-rebuild")
        run(name + "-rebuild", ["uv", "build", "--wheel", "--out-dir", again], packages[name])
        assert digest(wheels[name]) == digest(next(again.glob("*.whl")))
    wheel_manifest = {n: dict(filename=p.name, sha256=digest(p)) for n, p in wheels.items()}
    (work / "wheels.json").write_text(json.dumps(wheel_manifest, indent=2), encoding="utf-8")
    interpreters = {}
    for name in ("producer", "receiver"):
        destination = work / "environments" / name
        run(name + "-venv", [sys.executable, "-m", "venv", destination])
        interpreters[name] = python_in(destination)
    producer, receiver = [interpreters[n] for n in ("producer", "receiver")]
    run(
        "producer-install",
        [
            producer,
            "-m",
            "pip",
            "install",
            wheels["snapshot"],
            wheels["bundle"],
            wheels["exporter"],
            "pytest==8.4.2",
        ],
    )
    run(
        "receiver-contracts",
        [
            receiver,
            "-m",
            "pip",
            "install",
            "--no-index",
            cain / "vendor/predictor_research_snapshot-1.0.0-py3-none-any.whl",
            wheels["bundle"],
        ],
    )
    run(
        "receiver-install",
        [receiver, "-m", "pip", "install", "-r", cain / "requirements-dev.lock", wheels["cain"]],
    )
    for name, py in interpreters.items():
        run(name + "-pip-check", [py, "-m", "pip", "check"])
        run(name + "-installed", [py, "-m", "pip", "list", "--format=json"])
    cfg = work / "installed-tests.ini"
    cfg.write_text("[pytest]\naddopts = --strict-config --strict-markers\n", encoding="utf-8")
    for name, py, tests in (
        ("bundle", producer, eco / "packages/research-bundle/tests"),
        ("exporter", producer, crypto / "packages/research-export/tests"),
        ("cain", receiver, cain / "tests"),
    ):
        run(
            name + "-installed-tests",
            [
                py,
                "-I",
                "-m",
                "pytest",
                "-c",
                cfg,
                "--import-mode=prepend",
                "-p",
                "no:cacheprovider",
                "-q",
                tests,
                "--junitxml=" + str(work / (name + ".xml")),
            ],
        )
    run(
        "real-snapshot-bundle-e2e",
        [
            receiver,
            "-I",
            crypto / ".ci/integration-audit/e2e_crypto.py",
            crypto,
            cain,
            producer,
            work / "real-e2e",
        ],
    )
    if runtime_supported:
        runtime = work / "environments/runtime"
        runtime_env = {
            "UV_PROJECT_ENVIRONMENT": str(runtime),
            "COVERAGE_FILE": str(work / ".coverage"),
        }
        run(
            "crypto-locked-all-extras",
            ["uv", "sync", "--locked", "--all-extras", "--python", sys.executable],
            crypto,
            runtime_env,
        )
        py = python_in(runtime)
        run("crypto-build", ["uv", "build"], crypto, runtime_env)
        run("crypto-ruff", [py, "-m", "ruff", "check", "."], crypto)
        run("crypto-format", [py, "-m", "ruff", "format", "--check", "."], crypto)
        run("crypto-pyright", [py, "-m", "pyright", "--pythonpath", py], crypto)
        run("crypto-secrets", [py, "scripts/scan_secrets.py", "."], crypto)
        run(
            "crypto-full-tests",
            [
                py,
                "-m",
                "coverage",
                "run",
                "--rcfile=coverage-runtime.ini",
                "-m",
                "pytest",
                "-q",
                "--junitxml=" + str(work / "crypto.xml"),
            ],
            crypto,
            runtime_env,
        )
        run(
            "crypto-coverage",
            [py, "-m", "coverage", "report", "--rcfile=coverage-runtime.ini"],
            crypto,
            runtime_env,
        )
        requirements = work / "crypto-locked.txt"
        run(
            "crypto-export-lock",
            [
                "uv",
                "export",
                "--locked",
                "--all-extras",
                "--no-emit-project",
                "--output-file",
                requirements,
            ],
            crypto,
        )
        installed = work / "environments/runtime-wheel"
        run("crypto-wheel-venv", [sys.executable, "-m", "venv", installed])
        wp = python_in(installed)
        run(
            "crypto-wheel-install",
            [
                wp,
                "-m",
                "pip",
                "install",
                "-r",
                requirements,
                wheels["crypto"].as_uri() + "#sha256=" + digest(wheels["crypto"]),
            ],
        )
        run("crypto-wheel-check", [wp, "-m", "pip", "check"])
        run("crypto-wheel-contract", [wp, "-I", crypto / "scripts/verify_installed_wheels.py"])
        runstore = work / "synthetic-runstore"
        run(
            "crypto-functional-demo",
            [
                wp,
                "-I",
                "-m",
                "GarimpoInvestimentos.research",
                "demo",
                "--store",
                runstore,
                "--run-id",
                "synthetic-audit",
            ],
        )
        run(
            "crypto-functional-verify",
            [
                wp,
                "-I",
                "-m",
                "GarimpoInvestimentos.research",
                "verify",
                "--store",
                runstore,
                "synthetic-audit",
            ],
        )
        pluginenv = work / "environments/plugins"
        run("plugins-venv", [sys.executable, "-m", "venv", pluginenv])
        pp = python_in(pluginenv)
        manifest = json.loads((eco / "registries/compatibility_candidate.json").read_bytes())
        released = json.loads((eco / "registries/released_architecture.json").read_bytes())
        extra_wheels = [
            w
            for r in released["repositories"]
            for w in r["wheels"]
            if w["name"] in ("stocks-predictor", "brasileirao-predictor")
        ]
        specs = [
            v["url"] + "#" + v["hash"].replace(":", "=", 1) for v in manifest["shared"].values()
        ]
        specs += [w["url"] + "#sha256=" + w["sha256"] for w in extra_wheels]
        specs += [
            wheels[n].as_uri() + "#sha256=" + digest(wheels[n]) for n in ("crypto", "ecosystem")
        ]
        run("plugins-install", [pp, "-m", "pip", "install", *specs])
        for wheel in extra_wheels:
            manifest["consumers"][wheel["name"]]["wheel_sha256"] = wheel["sha256"]
        manifest["consumers"]["cripto-predictor"].update(
            commit=args.crypto_sha, wheel_sha256=digest(wheels["crypto"])
        )
        manifest["consumers"]["cain"].update(commit=CAIN, version="0.4.7")
        manifest_path = work / "candidate-plugins.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        state = work / "plugin-state"
        state.mkdir()
        private_free = state / "synthetic.env"
        private_free.write_text("# Isolated engineering check; no private credentials.\n")
        plugin_vars = {
            "CRIPTO_ROOT": str(work),
            "CRIPTO_ENV_FILE": str(private_free),
            "COMPATIBILITY_RECEIPT": str(work / "plugin-receipt.json"),
        }
        for name in ("DATA", "OUTPUT", "CACHE", "LOGS"):
            plugin_vars[name + "_DIR"] = plugin_vars["GARIMPO_" + name + "_DIR"] = str(
                state / name.lower()
            )
        run(
            "real-plugins",
            [pp, "-I", "scripts/check_real_plugin_integration.py", "--manifest", manifest_path],
            eco,
            plugin_vars,
        )
        run(
            "ecosystem-offline",
            [pp, "-I", "scripts/check_ecosystem_drift.py", "--offline-check"],
            eco,
        )
    for name, root in roots.items():
        run(name + "-source-unchanged", ["git", "diff", "--exit-code", "HEAD"], root)
    result = dict(
        status="PASS",
        python=sys.version,
        platform=sys.platform,
        sources=sources,
        wheels=wheel_manifest,
        crypto_runtime=runtime_supported,
        economic_validation=False,
    )
    (work / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
