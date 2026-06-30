"""FallbackRouter — orquestra tentativas sequenciais entre provedores.

Política inicial (Fase 1): fallback SEQUENCIAL com fail-fast. Tenta o primeiro
provedor; em falha, emite telemetria `data.fallback` e passa ao próximo. Se todos
falharem, emite `data.unavailable` e levanta `DataUnavailableError`.

Ambiente com inspeção TLS penaliza conexões concorrentes — por isso o fallback é
sequencial (ver docs/DOSSIE_PLATAFORMA.md, decisão "Fallback sequencial"). A
agregação (consensus_median/twap) da Fase 3 é deliberadamente CONCORRENTE — precisa
de todas as fontes para fundir — e vive no AggregationRouter abaixo.

Ambos os routers consultam um CircuitBreaker opcional por provedor: uma fonte com o
circuito aberto é pulada (fail-fast) sem desperdiçar requisição.
"""
from __future__ import annotations

import asyncio

from predictor_core.obs import emit_event

from GarimpoInvestimentos.dpl.aggregation import consensus_median, consensus_mean
from GarimpoInvestimentos.dpl.circuit_breaker import CircuitBreaker
from GarimpoInvestimentos.dpl.contracts import (
    DataProvider,
    DataUnavailableError,
    MarketDataPoint,
)

_DOMAIN = "previsao_cripto"

_AGG_POLICIES = {
    "consensus_median": consensus_median,
    "consensus_mean": consensus_mean,
}


class FallbackRouter:
    def __init__(self, providers: list[DataProvider],
                 breakers: dict[str, CircuitBreaker] | None = None):
        if not providers:
            raise ValueError("FallbackRouter exige ao menos um provedor")
        self._providers = providers
        self._breakers = breakers or {}

    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        last_exc: Exception | None = None
        for idx, provider in enumerate(self._providers):
            breaker = self._breakers.get(provider.name)
            if breaker is not None and not breaker.allow():
                # Circuito aberto: pula sem gastar requisição (fail-fast).
                emit_event(_DOMAIN, "circuit.skipped", metrics={"provider_index": idx},
                           metadata={"symbol": symbol, "provider": provider.name})
                continue
            try:
                points = await provider.fetch_ohlcv(symbol, interval=interval, limit=limit)
                if breaker is not None:
                    breaker.record_success()
                if idx > 0:
                    # Sucesso após uma fonte ter falhado: operamos em modo degradado.
                    emit_event(
                        _DOMAIN, "data.fallback",
                        metrics={"provider_index": idx},
                        metadata={"symbol": symbol, "interval": interval,
                                  "used": provider.name},
                    )
                return points
            except Exception as exc:  # noqa: BLE001 — qualquer falha aciona o próximo
                last_exc = exc
                if breaker is not None:
                    breaker.record_failure()
                proximo = self._providers[idx + 1].name if idx + 1 < len(self._providers) else None
                emit_event(
                    _DOMAIN, "data.fallback" if proximo else "data.provider_failed",
                    metrics={"provider_index": idx},
                    metadata={"symbol": symbol, "interval": interval,
                              "failed": provider.name, "next": proximo,
                              "error": type(exc).__name__},
                )
        emit_event(
            _DOMAIN, "data.unavailable",
            metrics={"n_providers": len(self._providers)},
            metadata={"symbol": symbol, "interval": interval,
                      "last_error": type(last_exc).__name__ if last_exc else None},
        )
        raise DataUnavailableError(
            f"nenhuma fonte entregou {symbol} ({interval}); "
            f"último erro: {last_exc!r}"
        ) from last_exc


class AggregationRouter:
    """Consolida o MESMO dado de várias fontes em paralelo (imuniza contra anomalia
    de uma única corretora). Tolera falhas parciais: funde sobre os sobreviventes;
    só levanta DataUnavailableError se TODAS falharem.
    """

    def __init__(self, providers: list[DataProvider], policy: str = "consensus_median",
                 breakers: dict[str, CircuitBreaker] | None = None):
        if len(providers) < 1:
            raise ValueError("AggregationRouter exige ao menos um provedor")
        if policy not in _AGG_POLICIES:
            raise ValueError(f"política de agregação desconhecida: '{policy}'")
        self._providers = providers
        self._policy = policy
        self._breakers = breakers or {}

    async def _try(self, provider, symbol, interval, limit):
        breaker = self._breakers.get(provider.name)
        if breaker is not None and not breaker.allow():
            emit_event(_DOMAIN, "circuit.skipped", metrics={},
                       metadata={"symbol": symbol, "provider": provider.name})
            return provider.name, None
        try:
            pts = await provider.fetch_ohlcv(symbol, interval=interval, limit=limit)
            if breaker is not None:
                breaker.record_success()
            return provider.name, pts
        except Exception as exc:  # noqa: BLE001
            if breaker is not None:
                breaker.record_failure()
            emit_event(_DOMAIN, "data.provider_failed", metrics={},
                       metadata={"symbol": symbol, "provider": provider.name,
                                 "error": type(exc).__name__})
            return provider.name, None

    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        results = await asyncio.gather(*[
            self._try(p, symbol, interval, limit) for p in self._providers
        ])
        survivors = [pts for _, pts in results if pts]
        used = [name for name, pts in results if pts]
        if not survivors:
            emit_event(_DOMAIN, "data.unavailable",
                       metrics={"n_providers": len(self._providers)},
                       metadata={"symbol": symbol, "interval": interval, "agg": self._policy})
            raise DataUnavailableError(
                f"agregação: nenhuma fonte entregou {symbol} ({interval})")
        fused = _AGG_POLICIES[self._policy](survivors)
        emit_event(_DOMAIN, "data.aggregated",
                   metrics={"n_sources": len(survivors), "n_points": len(fused)},
                   metadata={"symbol": symbol, "interval": interval,
                             "policy": self._policy, "used": used})
        return fused
