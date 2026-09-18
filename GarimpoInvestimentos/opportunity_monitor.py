"""Operational opportunity radar driven by the existing daily market snapshot.

Runs independently from LLM inference and scientific-family authorization. It persists
state locally, emits telemetry and sends a best-effort webhook when a material move is
first detected, escalates, or reverses direction.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from predictor_core.obs import emit_event

from GarimpoInvestimentos.analyzers.opportunity_detector import (
    BreadthSignal,
    NORMAL,
    OpportunitySignal,
    augment_opportunity_features,
    detect_asset_opportunity,
    detect_market_breadth,
    should_notify_transition,
)
from GarimpoInvestimentos.core.paths import DATA_DIR
from GarimpoInvestimentos.dpl.feature_engineering import to_hard_data
from GarimpoInvestimentos.dpl.snapshots import serving_context
from GarimpoInvestimentos.durable_io import atomic_write, file_lock

log = logging.getLogger("previsao_cripto.opportunity")

_STATE_PATH = DATA_DIR / "output" / "opportunity_state.json"
_ALERT_PATH = DATA_DIR / "output" / "OPPORTUNITY_ALERT_CRIPTO.txt"


def _load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("opportunity state must be a JSON object")
    return data


def _save_state(path: Path, payload: dict) -> None:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ).encode("utf-8")
    with file_lock(path):
        atomic_write(path, encoded + b"\n")


def _notify_webhook(text: str, *, title: str) -> bool:
    """Best-effort push using the same ALERTA_WEBHOOK_URL already used by ops."""

    url = os.getenv("ALERTA_WEBHOOK_URL", "").strip()
    if not url:
        return False
    try:
        req = urllib.request.Request(
            url,
            data=text.encode("utf-8"),
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "Title": title,
            },
        )
        urllib.request.urlopen(req, timeout=10).close()
        return True
    except Exception as exc:  # noqa: BLE001 - alert file remains the durable fallback
        log.warning("webhook de oportunidade falhou: %s", type(exc).__name__)
        return False


def _pct(signal: OpportunitySignal, key: str) -> str:
    value = signal.metrics.get(key)
    return "n/d" if value is None else f"{value:+.2f}%"


def _signal_line(signal: OpportunitySignal) -> str:
    extension = " | esticado/RSI" if signal.extension_risk else ""
    reasons = "; ".join(signal.reasons) if signal.reasons else "sem gatilho"
    return (
        f"- {signal.asset.upper()}: {signal.state} {signal.direction.upper()} | "
        f"1d {_pct(signal, 'change_24h')} | 3d {_pct(signal, 'change_3d')} | "
        f"7d {_pct(signal, 'change_7d')} | 30d {_pct(signal, 'change_30d')}"
        f"{extension}\n  motivos: {reasons}"
    )


def _breadth_line(breadth: BreadthSignal) -> str:
    assets = ", ".join(asset.upper() for asset in breadth.assets)
    return (
        f"- MARKET BREADTH: {breadth.direction.upper()} {breadth.count} ativo(s) "
        f"com movimento diário >= {breadth.daily_move_threshold_pct:.1f}% em módulo"
        f" ({assets})"
    )


def scan_opportunities(
    store,
    assets: list[str],
    *,
    now: datetime | None = None,
    state_path: Path = _STATE_PATH,
    alert_path: Path = _ALERT_PATH,
) -> dict:
    """Scan all available assets and notify only meaningful state transitions."""

    now = now or datetime.now(UTC)
    signals: list[OpportunitySignal] = []
    failures: list[dict[str, str]] = []

    for asset in assets:
        try:
            snapshot = serving_context(store, asset, now=now)
            hard_data = to_hard_data(snapshot["features"])
            detector_data = augment_opportunity_features(
                hard_data,
                list(snapshot.get("normalized_candles") or []),
                source=str(snapshot["source"]),
            )
            signal = detect_asset_opportunity(asset, detector_data)
            signals.append(signal)
            emit_event(
                "previsao_cripto",
                "opportunity.scanned",
                metrics={
                    "active": float(signal.active),
                    "rank": float(signal.rank),
                    "change_24h": signal.metrics.get("change_24h", 0.0),
                    "change_7d": signal.metrics.get("change_7d", 0.0),
                    "change_30d": signal.metrics.get("change_30d", 0.0),
                },
                metadata={
                    "asset": signal.asset,
                    "state": signal.state,
                    "direction": signal.direction,
                    "reasons": list(signal.reasons),
                    "extension_risk": signal.extension_risk,
                    "capital_authorized": False,
                    "decision_type": "INFORMATIONAL_MARKET_ALERT",
                },
            )
        except Exception as exc:  # isolate one asset, but never hide total radar failure
            failures.append({"asset": asset.lower(), "error": type(exc).__name__})
            emit_event(
                "previsao_cripto",
                "opportunity.scan_failed",
                metrics={},
                metadata={"asset": asset.lower(), "error": type(exc).__name__},
            )

    if not signals:
        raise RuntimeError("opportunity radar could not scan any asset")

    breadth = detect_market_breadth(signals)
    previous = _load_state(state_path)
    previous_assets = previous.get("assets")
    if not isinstance(previous_assets, dict):
        previous_assets = {}

    triggered = [
        signal
        for signal in signals
        if should_notify_transition(previous_assets.get(signal.asset), signal)
    ]

    previous_breadth = previous.get("breadth")
    if not isinstance(previous_breadth, dict):
        previous_breadth = {}
    breadth_triggered = bool(
        breadth.active
        and (
            not previous_breadth.get("active")
            or previous_breadth.get("direction") != breadth.direction
        )
    )

    current_state = {
        "schema_version": "opportunity-state/1",
        "updated_at": now.isoformat(),
        "capital_authorized": False,
        "assets": {signal.asset: signal.as_dict() for signal in signals},
        "breadth": breadth.as_dict(),
        "failures": failures,
    }
    _save_state(state_path, current_state)

    alert_sent = False
    if triggered or breadth_triggered:
        lines = [
            f"RADAR CRIPTO — {now.isoformat(timespec='seconds')}",
            "Alerta informativo de mercado; NÃO autoriza capital nem envia ordens.",
            "",
        ]
        lines.extend(_signal_line(signal) for signal in triggered)
        if breadth_triggered:
            lines.append(_breadth_line(breadth))
        text = "\n".join(lines) + "\n"
        alert_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(alert_path, text.encode("utf-8"))
        alert_sent = _notify_webhook(text, title="RADAR CRIPTO: movimento relevante")
        emit_event(
            "previsao_cripto",
            "opportunity.alert",
            metrics={"n_asset_alerts": float(len(triggered)), "breadth": float(breadth_triggered)},
            metadata={
                "assets": [signal.asset for signal in triggered],
                "breadth_direction": breadth.direction if breadth_triggered else NORMAL,
                "webhook_sent": alert_sent,
                "capital_authorized": False,
            },
        )

    return {
        "scanned": len(signals),
        "failed": len(failures),
        "active": sum(signal.active for signal in signals),
        "triggered": len(triggered),
        "breadth_triggered": breadth_triggered,
        "webhook_sent": alert_sent,
    }
