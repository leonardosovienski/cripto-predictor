"""Opt-in local runtime profile; no machine paths or secrets are shipped in wheels."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
MARKER = PROJECT / ".cripto-root"


class LocalRuntimePathError(ValueError):
    """An operational destination escapes the configured project root."""


def local_root() -> Path | None:
    raw = os.environ.get("CRIPTO_ROOT")
    if not raw and MARKER.is_file():
        raw = MARKER.read_text(encoding="utf-8-sig").strip()
        if not raw:
            raise ValueError(".cripto-root vazio")
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise ValueError("CRIPTO_ROOT precisa ser um caminho absoluto")
    return path.resolve()


def within_root(root: Path, value: str | Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise LocalRuntimePathError("Caminho operacional fora de CRIPTO_ROOT")
    return resolved


def configure_local_runtime() -> dict[str, str]:
    """Validate all destinations before making directories or changing the environment."""
    root = local_root()
    if root is None:
        return {}
    directories = {
        "DATA_DIR": ("GARIMPO_DATA_DIR", "operacao/dados"),
        "OUTPUT_DIR": ("GARIMPO_OUTPUT_DIR", "operacao/saidas"),
        "CACHE_DIR": ("GARIMPO_CACHE_DIR", "operacao/cache"),
        "LOGS_DIR": ("GARIMPO_LOGS_DIR", "operacao/logs"),
        "PREDICTOR_OPS_STATE_DIR": ("", "operacao/estado"),
    }
    paths = {}
    for name, (legacy, default) in directories.items():
        raw = os.getenv(name) or (os.getenv(legacy) if legacy else None) or default
        paths[name] = str(within_root(root, raw))
    files = {
        "CRIPTO_ENV_FILE": "configuracao/pipeline.env",
        "PREDICTOR_EVENTS_PATH": str(Path(paths["LOGS_DIR"]) / "events.jsonl"),
    }
    for name, default in files.items():
        paths[name] = str(within_root(root, os.getenv(name) or default))
    # These are per-process scratch/cache settings, replacing inherited OS defaults.
    scratch = {
        "TEMP": "operacao/temporarios",
        "TMP": "operacao/temporarios",
        "TMPDIR": "operacao/temporarios",
        "PIP_CACHE_DIR": "operacao/cache/pip",
        "UV_CACHE_DIR": "pesquisa-20260909/work/uv-cache",
        "UV_PYTHON_INSTALL_DIR": "pesquisa-20260909/work/managed-python",
        "UV_PYTHON_BIN_DIR": "ferramentas/bin",
        "UV_TOOL_DIR": "ferramentas/uv-tools",
        "UV_TOOL_BIN_DIR": "ferramentas/bin",
        "XDG_CACHE_HOME": "operacao/cache/xdg",
        "XDG_DATA_HOME": "operacao/dados/xdg",
        "XDG_STATE_HOME": "operacao/estado/xdg",
        "MPLCONFIGDIR": "operacao/cache/matplotlib",
        "NUMBA_CACHE_DIR": "operacao/cache/numba",
        "JOBLIB_TEMP_FOLDER": "operacao/temporarios/joblib",
    }
    for name, relative in scratch.items():
        paths[name] = str(within_root(root, relative))
    for name, value in paths.items():
        destination = Path(value)
        (destination.parent if name in files else destination).mkdir(parents=True, exist_ok=True)
    for name, (legacy, _) in directories.items():
        if legacy:
            paths[legacy] = paths[name]
    paths.update(
        CRIPTO_ROOT=str(root),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
    )
    os.environ.update(paths)
    sys.dont_write_bytecode = True
    tempfile.tempdir = paths["TEMP"]
    return paths


def environment_file() -> Path:
    configure_local_runtime()
    return (
        Path(os.environ["CRIPTO_ENV_FILE"])
        if local_root()
        else PROJECT / "GarimpoInvestimentos/.env"
    )


def status() -> dict:
    paths = configure_local_runtime()
    if not paths:
        raise ValueError("Configure CRIPTO_ROOT ou o arquivo local .cripto-root")
    configuration: dict[str, object] = {"loaded": False, "network_requests": 0}
    try:
        from GarimpoInvestimentos.config import settings

        configuration["loaded"] = settings is not None
    except Exception as exc:
        # Never print the exception: validation errors can include input secrets.
        configuration["error_type"] = type(exc).__name__
    return {
        "root": paths["CRIPTO_ROOT"],
        "project": str(PROJECT),
        "python": sys.executable,
        "paths": paths,
        "pipeline_configuration": configuration,
        "capital_permission": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Execução local centralizada na raiz Cripto.")
    parser.add_argument(
        "command", choices=("status", "pipeline", "python", "uv"), nargs="?", default="status"
    )
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    remainder = args.arguments
    paths = configure_local_runtime()
    if not paths:
        parser.error("Configure CRIPTO_ROOT ou .cripto-root antes de executar")
    if args.command == "status":
        if remainder:
            parser.error("status não recebe argumentos adicionais")
        print(json.dumps(status(), indent=2, ensure_ascii=False))
        return
    root = Path(paths["CRIPTO_ROOT"])
    within_root(root, PROJECT)
    within_root(root, sys.executable)
    if args.command == "pipeline":
        sys.argv = ["cripto-predictor", *remainder]
        from GarimpoInvestimentos.cli import main as pipeline

        pipeline()
        return
    executable = (
        PROJECT / "work/tooling/bin/uv.exe" if args.command == "uv" else Path(sys.executable)
    )
    within_root(root, executable)
    command = [str(executable), *(["-B"] if args.command == "python" else []), *remainder]
    raise SystemExit(subprocess.call(command, cwd=PROJECT))


if __name__ == "__main__":
    main()
