"""Theoretical paper ledger, subject to the scientific family freeze.

Historical cached signals are not prospective observations. New records require
an open family and a current decision timestamp. No orders or capital are enabled.
"""

import argparse
import asyncio
import json
import logging
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.analyzers.trials import FrozenFamilyError
from GarimpoInvestimentos.core.paths import DATA_DIR
from GarimpoInvestimentos.durable_io import atomic_write, file_lock
from GarimpoInvestimentos.governance import load_scientific_state
from GarimpoInvestimentos.v3.backtest_v3 import DEFAULT_KELLY_FRACTION
from GarimpoInvestimentos.v3.collectors.record_io import validate_observation
from GarimpoInvestimentos.v3.collectors.spot_collector import load_spot_csv
from GarimpoInvestimentos.v3.feature_builder import build_spot_index
from GarimpoInvestimentos.v3.pipeline import run_symbol, spot_path
from GarimpoInvestimentos.v3.signal_engine import SignalRecord
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


def _ref_price(ts_ms: int, spot_index: dict[int, float]) -> float | None:
    """Ultimo close de 1h que ja era publico no instante ``ts_ms``.

    As chaves do indice sao open-times, embora os valores sejam closes; por
    isso a vela elegivel abre uma hora antes da decisao.
    """
    return SortedTimeIndex(spot_index).as_of(ts_ms - _SPOT_CANDLE_MS, _PRICE_TOLERANCE_MS)


def _already_recorded(symbol: str, timestamp_exchange_ms: int) -> bool:
    """Idempotência (C4, auditoria 2026-07-09): re-execução no mesmo dia (retry
    manual pós-falha, agendador disparado 2x) gerava linha duplicada com o MESMO
    timestamp_exchange_ms — e o paper_report NÃO deduplica: o P&L do trade
    contava dobrado. O sinal é determinístico por timestamp, então basta checar
    se o timestamp já está no livro (arquivo é pequeno: 1 linha/dia)."""
    path = _paper_path(symbol)
    if not path.exists():
        return False
    found = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError("historico paper invalido")
        if row.get("timestamp_exchange_ms") == timestamp_exchange_ms:
            found = True
    return found


def _latest_signal(signals: list[SignalRecord]) -> SignalRecord | None:
    """O sinal de maior timestamp_exchange_ms (o mais recente da série)."""
    if not signals:
        return None
    return max(signals, key=lambda s: s.timestamp_exchange_ms)


def _require_open_family() -> None:
    if "funding_oi_hmm_v3" in load_scientific_state().frozen_families:
        raise FrozenFamilyError(
            "Paper V3 bloqueado: funding_oi_hmm_v3 esta congelada; preservar livro existente"
        )


def _record_paper_trade(
    symbol: str,
    signal: SignalRecord,
    ref_price: float | None,
    kelly_fraction: float,
) -> dict:
    """Monta, persiste e emite o trade teórico. Retorna o dict gravado."""
    _require_open_family()
    if (
        not math.isfinite(kelly_fraction)
        or not 0 < kelly_fraction <= 1
        or ref_price is None
        or not math.isfinite(ref_price)
        or ref_price <= 0
    ):
        raise ValueError("paper exige preco valido e fracao em (0,1]")
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    if (
        not 0 <= now_ms - signal.timestamp_signal_ms <= 300_000
        or not 0 <= now_ms - signal.timestamp_exchange_ms <= 8 * _SPOT_CANDLE_MS
    ):
        raise ValueError("sinal desatualizado nao pode ser registrado como prospectivo")
    position = signal.direction * signal.strength * kelly_fraction
    signal_ts_utc = datetime.now(UTC).isoformat(timespec="seconds")

    paper = {
        "symbol": symbol,
        "recording_mode": "SHADOW_REFERENCE_CLOSE_ONLY",
        "capital_enabled": False,
        "timestamp_entry_ms": now_ms,
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
    with file_lock(path):
        if _already_recorded(symbol, signal.timestamp_exchange_ms):
            raise ValueError("sinal paper ja registrado")
        original = path.read_bytes() if path.exists() else b""
        separator = b"\n" if original and not original.endswith(b"\n") else b""
        atomic_write(
            path,
            original
            + separator
            + (json.dumps(paper, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"),
        )

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
    _require_open_family()
    validate_observation(symbol, 0, {})
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
        ref_price = _ref_price(int(datetime.now(UTC).timestamp() * 1000), spot_index)

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
        help=f"Fração de Kelly (default historico de pesquisa: {DEFAULT_KELLY_FRACTION})",
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
