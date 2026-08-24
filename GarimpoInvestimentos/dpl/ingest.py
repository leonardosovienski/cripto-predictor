"""Camada de INGESTÃO — coleta → alinhamento → gravação na Feature Store.

É o único ponto que toca a rede. Roda fora do caminho de serving (ex.: agendada
diariamente). O domínio nunca chama isto em tempo de previsão; ele lê a Feature
Store já materializada. Emite telemetria `data.ingested` / `data.materialized`.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Protocol

import predictor_core
from predictor_core.data.contracts import MarketDataPoint
from predictor_core.data.quality import detect_jumps
from predictor_core.obs import emit_event

from GarimpoInvestimentos.dpl.alignment import AlignmentEngine
from GarimpoInvestimentos.dpl.feature_engineering import derive_features
from GarimpoInvestimentos.security.redaction import safe_redact_text
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.signals import SignalProvider


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
    """Coleta candles (+ sinais), grava bruto, alinha e materializa features.

    Retorna as linhas alinhadas materializadas. Erro de um signal provider é
    tolerado (segue sem aquele sinal) — falha de preço propaga (sem preço não há grade).
    """
    points = await facade.fetch_ohlcv(symbol, interval=interval, limit=limit)
    store.write_raw(points)
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
    derived = derive_features(points)
    if aligned and derived:
        aligned[-1].update(derived)
    n_features = store.write_features(symbol, interval, aligned)
    emit_event(
        domain,
        "data.materialized",
        metrics={"n_rows": len(aligned), "n_cells": n_features, "n_derived": len(derived)},
        metadata={"symbol": symbol, "interval": interval, "signals": list(signals)},
    )
    return aligned
