"""Descriptive gross returns from a theoretical ledger; not realized profit.

Per-row horizons and reference dates are preserved. Legacy retrospective records
are counted explicitly and do not become prospective evidence. Costs, allocation,
execution and an intratrade mark path are absent: no portfolio P&L or MaxDD is certified.
"""

import argparse
import json
import logging
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.core.paths import DATA_DIR
from GarimpoInvestimentos.v3.collectors.record_io import validate_observation
from GarimpoInvestimentos.v3.collectors.spot_collector import load_spot_csv
from GarimpoInvestimentos.v3.feature_builder import build_spot_index
from GarimpoInvestimentos.v3.timeindex import SortedTimeIndex

logger = logging.getLogger(__name__)

_DOMAIN = "v3_paper"
_DATA_ROOT = DATA_DIR / "v3"
_PAPER_DIR = _DATA_ROOT / "paper"
_PRICE_TOLERANCE_MS = 300_000
_SPOT_CANDLE_MS = 3_600_000


def _paper_path(symbol: str) -> Path:
    validate_observation(symbol, 0, {})
    return _PAPER_DIR / f"{symbol}_paper.jsonl"


def _spot_path(symbol: str) -> Path:
    return _DATA_ROOT / symbol / "spot_binance_1h.csv"


def _load_paper_trades(symbol: str) -> list[dict]:
    path = _paper_path(symbol)
    if not path.exists():
        return []
    trades = []
    identities = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                row = json.loads(line)
                if not isinstance(row, dict) or row.get("symbol") != symbol:
                    raise ValueError("registro paper invalido")
                identity = row["timestamp_exchange_ms"]
                if identity in identities:
                    raise ValueError("registro paper duplicado")
                identities.add(identity)
                trades.append(row)
    return trades


def _closest_price(ts_ms: int, spot_index: dict[int, float]) -> float | None:
    """Ultimo close de 1h disponivel no instante, nunca uma vela futura."""
    return SortedTimeIndex(spot_index).as_of(ts_ms - _SPOT_CANDLE_MS, _PRICE_TOLERANCE_MS)


def _equity_curve(returns: list[float]) -> list[float]:
    """Retornos por-trade → equity acumulada (base 1.0). Igual ao backtest_v3."""
    equity, acc = [1.0], 1.0
    for r in returns:
        acc *= 1.0 + r
        equity.append(acc)
    return equity


def build_report(symbol: str, horizon_hours: int = 24) -> dict:
    """Computa as métricas do paper trading de um símbolo. Retorna dict de resumo."""
    if isinstance(horizon_hours, bool) or not isinstance(horizon_hours, int) or horizon_hours <= 0:
        raise ValueError("horizon_hours deve ser inteiro positivo")
    trades = _load_paper_trades(symbol)
    n_total = len(trades)
    n_active = sum(1 for t in trades if t.get("direction", 0) != 0)
    n_flat = n_total - n_active

    summary = {
        "symbol": symbol,
        "n_total": n_total,
        "n_active": n_active,
        "n_flat": n_flat,
        "n_mature": 0,
        "cum_pnl": None,  # compatibility alias: sum of gross trade returns, not portfolio P&L
        "sum_gross_trade_returns": None,
        "max_dd": None,
        "scientific_state": "DESCRIPTIVE_REPLAY",
        "capital_enabled": False,
        "portfolio_metrics_status": "UNAVAILABLE_ALLOCATION_COSTS_EXECUTION_AND_MARK_PATH",
        "retrospective_records": 0,
        "hit_rate": None,
        "by_regime": {},
        "by_reason": {},
    }
    if n_total == 0:
        return summary

    # Distribuições
    for t in trades:
        reg = t.get("regime_state", "?")
        rsn = t.get("reason", "?")
        summary["by_regime"][reg] = summary["by_regime"].get(reg, 0) + 1
        summary["by_reason"][rsn] = summary["by_reason"].get(rsn, 0) + 1

    for row in trades:
        recorded = datetime.fromisoformat(row["signal_ts_utc"])
        if recorded.tzinfo is None:
            raise ValueError("paper exige timestamp com timezone")
        entry = row.get("timestamp_entry_ms")
        if entry is None or int(recorded.astimezone(UTC).timestamp() * 1000) > entry + 300_000:
            summary["retrospective_records"] += 1

    # Retorno bruto descritivo: precisa do preco no horizonte de cada registro.
    spot_path = _spot_path(symbol)
    if not spot_path.exists():
        logger.warning("paper_report [%s]: sem spot_binance_1h.csv — P&L não computável", symbol)
        return summary

    spot_index = build_spot_index(load_spot_csv(spot_path))
    time_index = SortedTimeIndex(spot_index)

    returns: list[float] = []
    n_wins = 0
    n_mature_active = 0
    for t in trades:
        position = t.get("position", 0.0)
        entry_ms = t.get("timestamp_entry_ms", t.get("timestamp_exchange_ms"))
        row_horizon = t.get("horizon_hours", horizon_hours)
        if not isinstance(row_horizon, int) or row_horizon < 0:
            raise ValueError("horizonte paper invalido")
        entry_px = t.get("ref_price")
        if entry_px is None or entry_ms is None:
            continue
        if not math.isfinite(position):
            raise ValueError("position deve ser finita")
        if position != 0 and row_horizon == 0:
            raise ValueError("posicao ativa sem horizonte")
        exit_px = time_index.as_of(
            entry_ms + row_horizon * _SPOT_CANDLE_MS - _SPOT_CANDLE_MS, _PRICE_TOLERANCE_MS
        )
        if (
            exit_px is None
            or not math.isfinite(entry_px)
            or not math.isfinite(exit_px)
            or entry_px <= 0
            or exit_px <= 0
        ):
            continue  # trade ainda não maduro (sem preço D+H na série)
        pnl = position * (exit_px / entry_px - 1)
        returns.append(pnl)
        if position != 0:
            n_mature_active += 1
            if pnl > 0:
                n_wins += 1

    summary["n_mature"] = len(returns)
    if returns:
        summary["cum_pnl"] = round(sum(returns), 6)
        summary["sum_gross_trade_returns"] = summary["cum_pnl"]
    if n_mature_active > 0:
        summary["hit_rate"] = round(n_wins / n_mature_active, 4)

    return summary


def _print_report(s: dict) -> None:
    logger.info("=" * 58)
    logger.info("PAPER REPORT — %s", s["symbol"])
    logger.info("=" * 58)
    logger.info("Trades: %d total | %d ativos | %d flat", s["n_total"], s["n_active"], s["n_flat"])
    logger.info("Maduros (com P&L): %d", s["n_mature"])
    logger.info("Soma bruta de retornos por trade: %s", s["sum_gross_trade_returns"])
    logger.info("PnL/MaxDD de carteira nao estimaveis: %s", s["portfolio_metrics_status"])
    if s["hit_rate"] is not None:
        logger.info("Hit rate (ativos)  : %.1f%%", s["hit_rate"] * 100)
    logger.info("Por regime: %s", s["by_regime"])
    logger.info("Por motivo: %s", s["by_reason"])
    logger.info("=" * 58)


def _emit_report(s: dict) -> None:
    emit_event(
        _DOMAIN,
        "paper_report",
        metrics={
            "n_total": float(s["n_total"]),
            "n_active": float(s["n_active"]),
            "n_mature": float(s["n_mature"]),
            **(
                {"sum_gross_trade_returns": float(s["cum_pnl"])} if s["cum_pnl"] is not None else {}
            ),
            "hit_rate": float(s["hit_rate"]) if s["hit_rate"] is not None else -1.0,
        },
        metadata={
            "symbol": s["symbol"],
            "by_regime": s["by_regime"],
            "by_reason": s["by_reason"],
            "scientific_state": s["scientific_state"],
            "portfolio_metrics_status": s["portfolio_metrics_status"],
        },
    )


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Crypto-Predictor V3 — Relatório de Paper Trading",
    )
    parser.add_argument("--symbol", nargs="+", default=["BTCUSDT"])
    parser.add_argument("--horizon-hours", type=int, default=24)
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
        s = build_report(symbol.upper(), horizon_hours=args.horizon_hours)
        _print_report(s)
        _emit_report(s)


if __name__ == "__main__":
    _main()
