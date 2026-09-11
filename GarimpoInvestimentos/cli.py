import argparse
import asyncio
import os
import sys

from GarimpoInvestimentos.local_runtime import LocalRuntimePathError


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        import json
        from importlib.metadata import version

        print(
            json.dumps(
                {
                    "version": version("cripto-predictor"),
                    "status": "NOT_PROBED",
                    "modes": ["ingest", "analyze", "history", "migrate-history", "research"],
                    "capital_permission": False,
                }
            )
        )
        return
    if len(sys.argv) > 1 and sys.argv[1] in {"ingest", "analyze"}:
        mode = sys.argv.pop(1)
        if mode == "ingest" and "--ingest" not in sys.argv:
            sys.argv.append("--ingest")
        if mode == "analyze" and "--ingest" in sys.argv:
            raise SystemExit("analyze cannot request ingestion")
    if len(sys.argv) > 1 and sys.argv[1] == "migrate-history":
        from GarimpoInvestimentos.migrate_history import main as migrate_main

        raise SystemExit(migrate_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "history":
        from GarimpoInvestimentos.history_cli import main as history_main

        raise SystemExit(history_main(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "research":
        from GarimpoInvestimentos.research.__main__ import main as research_main

        research_main(sys.argv[2:])
        return
    if any(argument in {"-h", "--help"} for argument in sys.argv[1:]):
        print(
            "usage: cripto-predictor [--ingest] [--assets IDS] [--discover N] [--summary] [--output-dir PATH]"
        )
        print("Fail-closed cryptocurrency research pipeline (no capital authorization).")
        print("Offline research tools: cripto-predictor research --help")
        print("Read-only history: cripto-predictor history --database PATH [--limit N]")
        print("Explicit legacy import: cripto-predictor migrate-history --database PATH --csv PATH")
        return
    # Bootstrap oficial: resolve a configuração de caminho antes de qualquer
    # importação do pipeline. O guard em main.py ainda detecta import tardio.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--output-dir")
    known, _ = pre.parse_known_args()
    if known.output_dir:
        os.environ["OUTPUT_DIR"] = known.output_dir
        os.environ["GARIMPO_OUTPUT_DIR"] = known.output_dir
    try:
        from GarimpoInvestimentos.runtime_mode import select_mode

        select_mode("ingest" if "--ingest" in sys.argv else "analysis")
        from GarimpoInvestimentos.security.redaction import (
            configured_secret_values,
            install_log_redaction,
        )

        install_log_redaction(configured_secret_values())
        if "--ingest" in sys.argv:
            from GarimpoInvestimentos.ingest_cli import run
        else:
            from GarimpoInvestimentos.main import run

        asyncio.run(run())
    except Exception as error:
        # A falha pode ocorrer durante Settings, antes de conhecermos os segredos.
        # O tipo é seguro; traceback/ValidationError podem conter entradas privadas.
        reason = (
            "caminho fora de CRIPTO_ROOT"
            if isinstance(error, LocalRuntimePathError)
            else type(error).__name__
        )
        print(f"Pipeline interrompido ({reason}).", file=sys.stderr)
        raise SystemExit(1) from None
