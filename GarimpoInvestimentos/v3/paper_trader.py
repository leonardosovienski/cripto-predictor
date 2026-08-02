"""
Paper Trader — V3 Crypto-Predictor (produção shadow, sem capital real).

Roda o pipeline V3 (dados em cache), pega o SINAL MAIS RECENTE de cada símbolo,
aplica a fração de Kelly homologada (DEFAULT_KELLY_FRACTION = 0.50, ver HANDOFF.md)
e registra um trade teórico:

  - emite evento `paper_trade` via predictor_core.obs (domain="v3_paper")
  - persiste a posição teórica em data/v3/paper/{symbol}_paper.jsonl

NÃO move capital. NÃO envia ordens. É o registro shadow que valida o edge em
tempo real, alimentado pelo MESMO pipeline causal do backtest (paridade total).

CONTRATO DO EVENTO paper_trade:
    metrics  : direction, strength, kelly_fraction, position, ref_price,
               regime_confidence
    metadata : symbol, timestamp_exchange_ms, signal_ts_utc, regime_state,
               reason, horizon_hours, engine_id, active

USO (CLI):
    python -m GarimpoInvestimentos.v3.paper_trader --symbol BTCUSDT --start-date 2021-01-01
    python -m GarimpoInvestimentos.v3.paper_trader --symbol BTCUSDT ETHUSDT --start-date 2024-01-01

    # Roda 1×/dia (após o pipeline diário) — cada execução registra o sinal corrente.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.v3.backtest_v3 import DEFAULT_KELLY_FRACTION
from GarimpoInvestimentos.v3.collectors.spot_collector import load_spot_csv
from GarimpoInvestimentos.v3.feature_builder import build_spot_index
from GarimpoInvestimentos.v3.pipeline import run_symbol, spot_path
from GarimpoInvestimentos.v3.signal_engine import SignalRecord
from GarimpoInvestimentos.v3.timeindex import nearest_value

logger = logging.getLogger(__name__)

_DOMAIN = "v3_paper"
_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "v3"
_PAPER_DIR = _DATA_ROOT / "paper"
_PRICE_TOLERANCE_MS = 300_000  # ±5 min para casar o preço de referência


def _paper_path(symbol: str) -> Path:
    return _PAPER_DIR / f"{symbol}_paper.jsonl"


def _ref_price(ts_ms: int, spot_index: dict[int, float]) -> float | None:
    """Close de spot mais próximo de ts_ms (±5 min). None se não houver.
    Delegado ao helper único (C5) — antes era a 2ª de 3 cópias da mesma lógica."""
    return nearest_value(spot_index, ts_ms, _PRICE_TOLERANCE_MS)


def _already_recorded(symbol: str, timestamp_exchange_ms: int) -> bool:
    """Idempotência (C4, auditoria 2026-07-09): re-execução no mesmo dia (retry
    manual pós-falha, agendador disparado 2x) gerava linha duplicada com o MESMO
    timestamp_exchange_ms — e o paper_report NÃO deduplica: o P&L do trade
    contava dobrado. O sinal é determinístico por timestamp, então basta checar
    se o timestamp já está no livro (arquivo é pequeno: 1 linha/dia)."""
    path = _paper_path(symbol)
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            if json.loads(line).get("timestamp_exchange_ms") == timestamp_exchange_ms:
                return True
        except ValueError:
            continue
    return False


def _latest_signal(signals: list[SignalRecord]) -> SignalRecord | None:
    """O sinal de maior timestamp_exchange_ms (o mais recente da série)."""
    if not signals:
        return None
    return max(signals, key=lambda s: s.timestamp_exchange_ms)


def _record_paper_trade(
    symbol: str,
    signal: SignalRecord,
    ref_price: float | None,
    kelly_fraction: float,
) -> dict:
    """Monta, persiste e emite o trade teórico. Retorna o dict gravado."""
    position = signal.direction * signal.strength * kelly_fraction
    signal_ts_utc = datetime.now(UTC).isoformat(timespec="seconds")

    paper = {
        "symbol": symbol,
        "timestamp_exchange_ms": signal.timestamp_exchange_ms,
        "signal_ts_utc": signal_ts_utc,
        "direction": signal.direction,
        "strength": signal.strength,
        "kelly_fraction": kelly_fraction,
        "position": round(position, 6),
        "ref_price": ref_price,
        "regime_state": signal.regime_state,
        "regime_confidence": signal.regime_confidence,
        "reason": signal.reason,
        "horizon_hours": signal.horizon_hours,
        "engine_id": signal.engine_id,
        "active": signal.active,
        "event_id": signal.event_id,
    }

    # Persistência local (append-only)
    path = _paper_path(symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    # Telemetria estruturada
    emit_event(
        _DOMAIN,
        "paper_trade",
        metrics={
            "direction": float(signal.direction),
            "strength": float(signal.strength),
            "kelly_fraction": float(kelly_fraction),
            "position": round(position, 6),
            "ref_price": float(ref_price) if ref_price is not None else 0.0,
            "regime_confidence": float(signal.regime_confidence),
        },
        metadata={
            "symbol": symbol,
            "timestamp_exchange_ms": signal.timestamp_exchange_ms,
            "signal_ts_utc": signal_ts_utc,
            "regime_state": signal.regime_state,
            "reason": signal.reason,
            "horizon_hours": signal.horizon_hours,
            "engine_id": signal.engine_id,
            "active": signal.active,
        },
    )
    return paper


async def run_paper(
    symbol: str,
    start_date: str,
    end_date: str | None = None,
    kelly_fraction: float = DEFAULT_KELLY_FRACTION,
    horizon_hours: int = 24,
) -> dict | None:
    """
    Roda o pipeline V3 para um símbolo, pega o sinal mais recente e registra
    o trade teórico. Retorna o dict do paper trade, ou None se não houver sinal.
    """
    signals = await run_symbol(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        horizon_hours=horizon_hours,
    )
    latest = _latest_signal(signals)
    if latest is None:
        logger.warning("paper_trader [%s]: nenhum sinal gerado — nada a registrar", symbol)
        return None

    if _already_recorded(symbol, latest.timestamp_exchange_ms):
        logger.info(
            "paper_trader [%s]: sinal ts=%d já registrado no livro — pulando "
            "(idempotência; re-execução não duplica trade)",
            symbol,
            latest.timestamp_exchange_ms,
        )
        return None

    # Preço de referência: close de spot no timestamp do sinal
    spot_csv_path = spot_path(symbol)
    ref_price = None
    if spot_csv_path.exists():
        spot_index = build_spot_index(load_spot_csv(spot_csv_path))
        ref_price = _ref_price(latest.timestamp_exchange_ms, spot_index)

    paper = _record_paper_trade(symbol, latest, ref_price, kelly_fraction)

    side = {1: "LONG", -1: "SHORT", 0: "FLAT"}.get(latest.direction, "?")
    logger.info(
        "paper_trader [%s]: %s pos=%.4f (kelly=%.2f) @ %s — regime=%s reason=%s",
        symbol,
        side,
        paper["position"],
        kelly_fraction,
        f"{ref_price:.2f}" if ref_price else "n/d",
        latest.regime_state,
        latest.reason,
    )
    return paper


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Crypto-Predictor V3 — Paper Trading (shadow, sem capital real)",
    )
    parser.add_argument("--symbol", nargs="+", default=["BTCUSDT"])
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="YYYY-MM-DD (default: hoje)")
    parser.add_argument(
        "--kelly-fraction",
        type=float,
        default=DEFAULT_KELLY_FRACTION,
        help=f"Fração de Kelly (default homologado: {DEFAULT_KELLY_FRACTION})",
    )
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
        await run_paper(
            symbol=symbol.upper(),
            start_date=args.start_date,
            end_date=args.end_date,
            kelly_fraction=args.kelly_fraction,
            horizon_hours=args.horizon_hours,
        )


if __name__ == "__main__":
    asyncio.run(_main())
