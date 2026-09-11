import argparse
import asyncio
import os
import sys

from GarimpoInvestimentos.local_runtime import LocalRuntimePathError


def main() -> None:
    if sys.argv[1:2] == ["research-export"]:
        try:
            from crypto_research_export import main as export_main
        except ImportError:
            print("Install the local crypto-research-export wheel first.", file=sys.stderr)
            raise SystemExit(1) from None
        raise SystemExit(export_main(sys.argv[2:]))
    if any(argument in {"-h", "--help"} for argument in sys.argv[1:]):
        print(
            "usage: cripto-predictor [--ingest] [--assets IDS] [--discover N] [--summary] [--output-dir PATH]"
        )
        print("Fail-closed cryptocurrency research pipeline (no capital authorization).")
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
        from GarimpoInvestimentos.security.redaction import (
            configured_secret_values,
            install_log_redaction,
        )

        install_log_redaction(configured_secret_values())
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
