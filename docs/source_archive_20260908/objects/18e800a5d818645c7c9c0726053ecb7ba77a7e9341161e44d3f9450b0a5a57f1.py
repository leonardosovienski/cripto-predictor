"""Deprecated source-checkout adapter; use ``cripto-predictor-job phase1``."""

from GarimpoInvestimentos.phase1 import *  # noqa: F403
from GarimpoInvestimentos.phase1 import _setup_logging, main

if __name__ == "__main__":
    import asyncio

    _setup_logging()
    raise SystemExit(asyncio.run(main()))
