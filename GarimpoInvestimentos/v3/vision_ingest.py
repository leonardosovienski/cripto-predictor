"""
Vision Ingest — popula o Data Lake local a partir do arquivo público da Binance.

Baixa funding + OI (metrics) + klines 1h históricos de data.binance.vision e grava
nos MESMOS CSVs que o caminho REST produz (data/v3/<symbol>/funding.csv, oi.csv,
spot_1h.csv). Depois disso, pipeline.py e backtest_v3.py rodam sem qualquer alteração
— eles só leem os CSVs.

Esta é a ponte que destrava o Go/No-Go histórico (anos de OI, não os ~30 dias do REST).

USO:
    python -m GarimpoInvestimentos.v3.vision_ingest \
        --symbol BTCUSDT --start-date 2021-01-01 --end-date 2024-12-31

    # depois:
    python -m GarimpoInvestimentos.v3.pipeline   --symbol BTCUSDT --start-date 2021-01-01
    python -m GarimpoInvestimentos.v3.backtest_v3 --symbol BTCUSDT --slippage-bps 5
"""

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.core.paths import DATA_DIR
from GarimpoInvestimentos.v3.collectors.binance_vision import (
    load_funding_vision,
    load_klines_vision,
    load_oi_vision,
)
from GarimpoInvestimentos.v3.collectors.funding_collector import save_funding_csv
from GarimpoInvestimentos.v3.collectors.oi_collector import save_oi_csv
from GarimpoInvestimentos.v3.collectors.spot_collector import save_spot_csv

logger = logging.getLogger(__name__)

_DATA_ROOT = DATA_DIR / "v3"


def _date_to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def ingest_symbol(symbol: str, start_date: str, end_date: str) -> dict:
    start_ms = _date_to_ms(start_date)
    end_ms = _date_to_ms(end_date)
    sym_dir = _DATA_ROOT / symbol

    logger.info("vision_ingest[%s]: %s → %s", symbol, start_date, end_date)

    funding = load_funding_vision(symbol, start_ms, end_ms)
    n_f = save_funding_csv(funding, sym_dir / "funding.csv")

    oi = load_oi_vision(symbol, start_ms, end_ms)
    n_o = save_oi_csv(oi, sym_dir / "oi.csv")

    klines = load_klines_vision(symbol, start_ms, end_ms, interval="1h")
    n_k = save_spot_csv(klines, sym_dir / "spot_1h.csv")

    summary = {
        "funding_total": len(funding),
        "funding_new": n_f,
        "oi_total": len(oi),
        "oi_new": n_o,
        "klines_total": len(klines),
        "klines_new": n_k,
    }
    logger.info("vision_ingest[%s]: %s", symbol, summary)

    emit_event(
        "v3_cripto",
        "vision_ingest_complete",
        metrics={k: float(v) for k, v in summary.items()},
        metadata={
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "source": "data.binance.vision",
        },
    )
    return summary


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Crypto-Predictor V3 — Ingest do Data Lake (Binance Vision)",
    )
    parser.add_argument("--symbol", nargs="+", default=["BTCUSDT"])
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    for symbol in args.symbol:
        ingest_symbol(symbol.upper(), args.start_date, args.end_date)


if __name__ == "__main__":
    _main()
