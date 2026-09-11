"""Camada de INGESTÃO — coleta → alinhamento → gravação na Feature Store.

É o único ponto que toca a rede. Roda fora do caminho de serving (ex.: agendada
diariamente). O domínio nunca chama isto em tempo de previsão; ele lê a Feature
Store já materializada. Emite telemetria `data.ingested` / `data.materialized`.
"""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime, timedelta
from typing import Protocol

import predictor_core
from predictor_core.data.contracts import MarketDataPoint
from predictor_core.data.quality import detect_jumps
from predictor_core.obs import emit_event

from GarimpoInvestimentos.dpl.alignment import AlignmentEngine
from GarimpoInvestimentos.dpl.feature_engineering import DAILY_FEATURE_VERSION, derive_features
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.signals import SignalProvider
from GarimpoInvestimentos.dpl.snapshots import market_payload
from GarimpoInvestimentos.security.redaction import safe_redact_text


class _OhlcvFacade(Protocol):
    """Estrutural: qualquer fachada com fetch_ohlcv serve — cripto e ações
    reusam esta pipeline (ver docstring de ingest_stocks)."""

    async def fetch_ohlcv(
        self, symbol: str, interval: str = ..., limit: int = ...
    ) -> list[MarketDataPoint]: ...


# Esta função nasceu crypto-específica, então o default é o domínio cripto — mas
# `facade` é estrutural (_OhlcvFacade) e `domain` continua INJETÁVEL, então stocks
# reusa a mesma pipeline sem herdar a atribuição errada (mesma regra Core↔Domínio
# dos routers).
_DEFAULT_DOMAIN = "previsao_cripto"

# |retorno overnight| acima disso é candle suspeito (erro de fonte — cripto não tem
# split). Calibrado folgado: quedas de 30%+ em 24h existem em cripto, mas são raras
# o bastante para merecerem um aviso; o dado NÃO é bloqueado, só sinalizado.
JUMP_THRESHOLD = 0.30


def series_quality(points, interval: str = "1d") -> dict:
    """Qualidade da série OHLCV ingerida: gaps (dias faltantes entre o primeiro e o
    último candle) e saltos overnight anômalos (predictor_core.data.quality).

    Um candle faltando vira change_7d errado, que vira score errado — em silêncio.
    Puro (sem rede/banco): a ingestão emite o resultado como telemetria."""
    pts = sorted(points, key=lambda p: p.timestamp)
    n_gaps = 0
    if interval == "1d" and len(pts) >= 2:
        expected = (pts[-1].timestamp - pts[0].timestamp).days + 1
        n_gaps = max(0, expected - len(pts))
    jumps = detect_jumps([p.timestamp.date() for p in pts], [p.close for p in pts], JUMP_THRESHOLD)
    return {"n_gaps": n_gaps, "jumps": jumps}


async def _ingest_crypto(
    store: FeatureStore,
    facade: _OhlcvFacade,
    symbol: str,
    interval: str = "1d",
    limit: int = 30,
    signal_providers: list[SignalProvider] | None = None,
    max_staleness: dict[str, timedelta] | None = None,
    domain: str = _DEFAULT_DOMAIN,
    record_provenance: bool = True,
    receipt: dict | None = None,
) -> list[dict]:
    """Coleta candles (+ sinais), grava bruto, alinha e materializa features.

    Retorna as linhas alinhadas materializadas. Erro de um signal provider é
    tolerado (segue sem aquele sinal) — falha de preço propaga (sem preço não há grade).
    """
    points = await facade.fetch_ohlcv(symbol, interval=interval, limit=limit)
    if not points:
        raise ValueError("provider returned no market observations")
    if len({(p.symbol, p.source, p.interval) for p in points}) != 1:
        raise ValueError("provider returned mixed market identities")
    if any(p.symbol != symbol or p.interval != interval for p in points):
        raise ValueError("provider returned a different symbol or interval")
    for p in points:
        prices = (p.open, p.high, p.low, p.close)
        if (
            any(not math.isfinite(v) or v <= 0 for v in prices)
            or not math.isfinite(p.volume)
            or p.volume < 0
            or not p.low <= min(p.open, p.close) <= max(p.open, p.close) <= p.high
        ):
            raise ValueError("provider returned invalid OHLCV values")
    # Reject a malformed batch before any persistent write. Gaps are retained
    # as observations; daily derived indicators use the contiguous suffix.
    derived = derive_features(points) if interval == "1d" else {}
    store.write_raw(points)
    if receipt is not None:
        receipt["stages_completed"].append("raw")
    # Proveniência (ADR-015): hash do CONTEÚDO ingerido + versão do core, em coluna
    # própria (migração 0012) — antes o hash ficava sobrecarregado dentro de `origin`,
    # colidindo semanticamente com o uso de `origin` em stocks.py ("cotahist+bcb",
    # descrição da fonte). Sem hash dedicado, "reproduzir o backtest de 6 meses atrás"
    # não tinha âncora de dados verificável por query direta.
    content_hash = hashlib.sha256(
        "\n".join(
            f"{p.timestamp.isoformat()},{p.open},{p.high},{p.low},{p.close},{p.volume}"
            for p in points
        ).encode()
    ).hexdigest()[:16]
    if record_provenance:  # wrappers com proveniência própria (ex.: stocks) desligam
        store.write_provenance(
            source=points[0].source,
            entity=symbol,
            n_rows=len(points),
            ingested_at=datetime.now(UTC),
            code_version=f"predictor_core:{predictor_core.__version__}",
            content_hash=content_hash,
        )
        if receipt is not None:
            receipt["stages_completed"].append("provenance")
    emit_event(
        domain,
        "data.ingested",
        metrics={"n_candles": len(points)},
        metadata={
            "symbol": symbol,
            "interval": interval,
            "source": points[0].source,
            "content_hash": content_hash,
        },
    )

    # Qualidade da série (jul/2026): gap/salto entra na store do mesmo jeito (não
    # bloqueia — pode ser movimento real), mas NUNCA em silêncio: telemetria + console.
    q = series_quality(points, interval)
    if q["n_gaps"] or q["jumps"]:
        emit_event(
            domain,
            "data.quality_warning",
            metrics={"n_gaps": q["n_gaps"], "n_jumps": len(q["jumps"])},
            metadata={
                "symbol": symbol,
                "interval": interval,
                "jumps": [(str(d), round(r, 4)) for d, r in q["jumps"]],
            },
        )
        avisos = []
        if q["n_gaps"]:
            avisos.append(f"{q['n_gaps']} dia(s) faltando na série")
        if q["jumps"]:
            avisos.append(f"{len(q['jumps'])} salto(s) overnight >{JUMP_THRESHOLD:.0%}")
        print(f"  ⚠️  {symbol.upper()}: {'; '.join(avisos)} — ver events.jsonl")

    signals: dict[str, list] = {}
    for sp in signal_providers or []:
        try:
            series = await sp.fetch(limit=limit)
            store.write_signals(series)
            signals[sp.name] = series
        except Exception as exc:  # noqa: BLE001 — sinal é opcional; preço não
            emit_event(
                domain,
                "data.signal_failed",
                metrics={},
                metadata={
                    "signal": sp.name,
                    "error": type(exc).__name__,
                    # Mensagem redatada: exceptions de HTTP podem carregar URL com
                    # chave de API (lição do incidente SerpAPI) — nunca logar cru.
                    "error_msg": safe_redact_text(str(exc))[:300],
                },
            )

    aligned = AlignmentEngine().align(points, signals, max_staleness)
    # Features derivadas (change_*, indicadores) pertencem ao ÚLTIMO candle —
    # são calculadas da série inteira e materializadas na linha mais recente.
    if aligned and derived:
        aligned[-1].update(derived)
    crypto_daily = interval == "1d" and domain == _DEFAULT_DOMAIN
    version = DAILY_FEATURE_VERSION if crypto_daily else "v1"
    n_features = store.write_features(symbol, interval, aligned, feature_version=version)
    if receipt is not None:
        receipt["stages_completed"].append("features")
    if crypto_daily:
        store.write_market_snapshot(market_payload(points, aligned, signals))
        if receipt is not None:
            receipt["stages_completed"].append("market_snapshot")
    emit_event(
        domain,
        "data.materialized",
        metrics={"n_rows": len(aligned), "n_cells": n_features, "n_derived": len(derived)},
        metadata={"symbol": symbol, "interval": interval, "signals": list(signals)},
    )
    return aligned


async def ingest_crypto(
    store: FeatureStore,
    facade: _OhlcvFacade,
    symbol: str,
    interval: str = "1d",
    limit: int = 30,
    signal_providers: list[SignalProvider] | None = None,
    max_staleness: dict[str, timedelta] | None = None,
    domain: str = _DEFAULT_DOMAIN,
    record_provenance: bool = True,
) -> list[dict]:
    """Preserve the legacy return value and record completed persistence stages.

    Separate store commits remain visible after failure; a failed materialization
    must never be reported as a completed ingestion or an atomic rollback.
    """
    receipt = {
        "schema_version": "crypto-ingestion-receipt/1",
        "symbol": symbol,
        "interval": interval,
        "stages_completed": [],
        "status": "FAILED",
    }
    try:
        result = await _ingest_crypto(
            store,
            facade,
            symbol,
            interval,
            limit,
            signal_providers,
            max_staleness,
            domain,
            record_provenance,
            receipt,
        )
        receipt["status"] = "SUCCEEDED"
        return result
    except Exception as exc:
        receipt["error_type"] = type(exc).__name__
        raise
    finally:
        emit_event(domain, "data.ingestion_receipt", metrics={}, metadata=receipt)
