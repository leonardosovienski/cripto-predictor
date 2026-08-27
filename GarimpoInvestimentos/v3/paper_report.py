"""
Paper Report — relatório do paper trading V3 (shadow, sem capital real).

Lê os trades teóricos persistidos em data/v3/paper/{symbol}_paper.jsonl, casa
cada posição com o preço realizado D+horizon (via spot_1h.csv) e computa:

  - n trades (ativos vs flat), distribuição por direção/regime/motivo
  - P&L acumulado dos trades MADUROS (entry + horizon já dentro da série spot)
  - curva de equity + MaxDD corrente (predictor_core.stats.max_drawdown)
  - hit rate (% dos trades ativos maduros com retorno > 0)

P&L de um trade = position × ln(price_{t+H} / price_t), onde position já embute
direção × strength × kelly_fraction. Trades flat (position=0) contribuem 0.

Emite o evento `paper_report` (domain=v3_paper) com as métricas agregadas e
imprime o relatório legível. Rode semanalmente no período de observação de 30d.

USO (CLI):
    python -m GarimpoInvestimentos.v3.paper_report --symbol BTCUSDT
    python -m GarimpoInvestimentos.v3.paper_report --symbol BTCUSDT ETHUSDT --horizon-hours 24
"""

import argparse
import json
import logging
import math
import sys
from pathlib import Path

from predictor_core.obs import emit_event
from predictor_core.stats import max_drawdown

from GarimpoInvestimentos.core.paths import DATA_DIR
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
    return _PAPER_DIR / f"{symbol}_paper.jsonl"


def _spot_path(symbol: str) -> Path:
    return _DATA_ROOT / symbol / "spot_1h.csv"


def _load_paper_trades(symbol: str) -> list[dict]:
    path = _paper_path(symbol)
    if not path.exists():
        return []
    trades = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                trades.append(json.loads(line))
    return trades


def _closest_price(ts_ms: int, spot_index: dict[int, float]) -> float | None:
    """Ultimo close de 1h disponivel no instante, nunca uma vela futura."""
    return SortedTimeIndex(spot_index).as_of(
        ts_ms - _SPOT_CANDLE_MS, _PRICE_TOLERANCE_MS
    )


def _equity_curve(returns: list[float]) -> list[float]:
    """Retornos por-trade → equity acumulada (base 1.0). Igual ao backtest_v3."""
    equity, acc = [], 1.0
    for r in returns:
        acc *= 1.0 + r
        equity.append(acc)
    return equity


def build_report(symbol: str, horizon_hours: int = 24) -> dict:
    """Computa as métricas do paper trading de um símbolo. Retorna dict de resumo."""
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
        "cum_pnl": 0.0,
        "max_dd": 0.0,
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

    # P&L realizado: precisa do preço D+horizon (spot)
    spot_path = _spot_path(symbol)
    if not spot_path.exists():
        logger.warning("paper_report [%s]: sem spot_1h.csv — P&L não computável", symbol)
        return summary

    spot_index = build_spot_index(load_spot_csv(spot_path))
    ms_horizon = horizon_hours * 3_600_000

    returns: list[float] = []
    n_wins = 0
    n_mature_active = 0
    for t in trades:
        position = t.get("position", 0.0)
        entry_ms = t.get("timestamp_exchange_ms")
        entry_px = t.get("ref_price")
        if entry_px is None or entry_ms is None:
            continue
        exit_px = _closest_price(entry_ms + ms_horizon, spot_index)
        if exit_px is None or entry_px <= 0:
            continue  # trade ainda não maduro (sem preço D+H na série)
        fwd = math.log(exit_px / entry_px)
        pnl = position * fwd
        returns.append(pnl)
        if position != 0:
            n_mature_active += 1
            if pnl > 0:
                n_wins += 1

    summary["n_mature"] = len(returns)
    if returns:
        summary["cum_pnl"] = round(sum(returns), 6)
        summary["max_dd"] = round(max_drawdown(_equity_curve(returns)), 6)
    if n_mature_active > 0:
        summary["hit_rate"] = round(n_wins / n_mature_active, 4)

    return summary


def _print_report(s: dict) -> None:
    logger.info("=" * 58)
    logger.info("PAPER REPORT — %s", s["symbol"])
    logger.info("=" * 58)
    logger.info("Trades: %d total | %d ativos | %d flat", s["n_total"], s["n_active"], s["n_flat"])
    logger.info("Maduros (com P&L): %d", s["n_mature"])
    logger.info("P&L acumulado (log): %+.4f", s["cum_pnl"])
    logger.info("MaxDD corrente     : %.2f%%", s["max_dd"] * 100)
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
            "cum_pnl": float(s["cum_pnl"]),
            "max_dd": float(s["max_dd"]),
            "hit_rate": float(s["hit_rate"]) if s["hit_rate"] is not None else -1.0,
        },
        metadata={"symbol": s["symbol"], "by_regime": s["by_regime"], "by_reason": s["by_reason"]},
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
