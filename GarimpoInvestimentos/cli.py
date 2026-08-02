import asyncio
import sys


def main() -> None:
    if any(argument in {"-h", "--help"} for argument in sys.argv[1:]):
        print(
            "usage: cripto-predictor [--ingest] [--assets IDS] [--discover N] [--summary] [--output-dir PATH]"
        )
        print("Fail-closed cryptocurrency research pipeline (no capital authorization).")
        return
    from GarimpoInvestimentos.main import run

    asyncio.run(run())
