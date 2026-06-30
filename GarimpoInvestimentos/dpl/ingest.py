"""Camada de INGESTÃO — coleta → alinhamento → gravação na Feature Store.

É o único ponto que toca a rede. Roda fora do caminho de serving (ex.: agendada
diariamente). O domínio nunca chama isto em tempo de previsão; ele lê a Feature
Store já materializada. Emite telemetria `data.ingested` / `data.materialized`.
"""
from __future__ import annotations

from datetime import timedelta

from predictor_core.obs import emit_event

from GarimpoInvestimentos.dpl.alignment import AlignmentEngine
from GarimpoInvestimentos.dpl.facade import CryptoDataProvider
from GarimpoInvestimentos.dpl.feature_engineering import derive_features
from GarimpoInvestimentos.dpl.feature_store import FeatureStore
from GarimpoInvestimentos.dpl.signals import SignalProvider

# Esta função é crypto-específica (importa CryptoDataProvider), então o default é o
# domínio cripto — mas continua INJETÁVEL para o futuro ingest genérico não herdar a
# atribuição errada (mesma regra Core↔Domínio dos routers).
_DEFAULT_DOMAIN = "previsao_cripto"


async def ingest_crypto(
    store: FeatureStore,
    facade: CryptoDataProvider,
    symbol: str,
    interval: str = "1d",
    limit: int = 30,
    signal_providers: list[SignalProvider] | None = None,
    max_staleness: dict[str, timedelta] | None = None,
    domain: str = _DEFAULT_DOMAIN,
) -> list[dict]:
    """Coleta candles (+ sinais), grava bruto, alinha e materializa features.

    Retorna as linhas alinhadas materializadas. Erro de um signal provider é
    tolerado (segue sem aquele sinal) — falha de preço propaga (sem preço não há grade).
    """
    points = await facade.fetch_ohlcv(symbol, interval=interval, limit=limit)
    store.write_raw(points)
    emit_event(domain, "data.ingested",
               metrics={"n_candles": len(points)},
               metadata={"symbol": symbol, "interval": interval,
                         "source": points[0].source})

    signals: dict[str, list] = {}
    for sp in (signal_providers or []):
        try:
            series = await sp.fetch(limit=limit)
            store.write_signals(series)
            signals[sp.name] = series
        except Exception as exc:  # noqa: BLE001 — sinal é opcional; preço não
            emit_event(domain, "data.signal_failed",
                       metrics={}, metadata={"signal": sp.name,
                                             "error": type(exc).__name__})

    aligned = AlignmentEngine().align(points, signals, max_staleness)
    # Features derivadas (change_*, indicadores) pertencem ao ÚLTIMO candle —
    # são calculadas da série inteira e materializadas na linha mais recente.
    derived = derive_features(points)
    if aligned and derived:
        aligned[-1].update(derived)
    n_features = store.write_features(symbol, interval, aligned)
    emit_event(domain, "data.materialized",
               metrics={"n_rows": len(aligned), "n_cells": n_features,
                        "n_derived": len(derived)},
               metadata={"symbol": symbol, "interval": interval,
                         "signals": list(signals)})
    return aligned
