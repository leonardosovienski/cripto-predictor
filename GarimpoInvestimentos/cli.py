import asyncio
import argparse
import os
import sys


def main() -> None:
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
    from GarimpoInvestimentos.main import run

    asyncio.run(run())
