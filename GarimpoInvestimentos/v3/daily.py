"""V3 daily payload; supervision belongs to :mod:`GarimpoInvestimentos.jobs`."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta


def commands(symbols: Sequence[str], *, start_date: str, end_date: str) -> list[list[str]]:
    result: list[list[str]] = []
    for symbol in symbols:
        result.extend(
            [
                [
                    sys.executable,
                    "-m",
                    "GarimpoInvestimentos.v3.vision_ingest",
                    "--symbol",
                    symbol,
                    "--start-date",
                    start_date,
                    "--end-date",
                    end_date,
                ],
                [
                    sys.executable,
                    "-m",
                    "GarimpoInvestimentos.v3.pipeline",
                    "--symbol",
                    symbol,
                    "--start-date",
                    start_date,
                ],
            ]
        )
    result.append(
        [
            sys.executable,
            "-m",
            "GarimpoInvestimentos.observation_quality",
            "--date",
            end_date,
        ]
    )
    return result


def main() -> int:
    """Collect and score source quality; no shadow/paper execution in COLLECTION_ONLY."""
    symbols = ("BTCUSDT", "ETHUSDT")
    end_date = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
    for command in commands(symbols, start_date="2021-01-01", end_date=end_date):
        completed = subprocess.run(command, check=False)
        if completed.returncode:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
