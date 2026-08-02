"""Deprecated source-checkout adapter; use ``cripto-predictor-job watchdog``."""

from GarimpoInvestimentos.watchdog import *  # noqa: F403
from GarimpoInvestimentos.watchdog import main

if __name__ == "__main__":
    raise SystemExit(main())
