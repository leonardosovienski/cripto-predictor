"""FallbackRouter — orquestra tentativas sequenciais entre provedores.

Política inicial (Fase 1): fallback SEQUENCIAL com fail-fast. Tenta o primeiro
provedor; em falha, emite telemetria `data.fallback` e passa ao próximo. Se todos
falharem, emite `data.unavailable` e levanta `DataUnavailableError`.

Ambiente com inspeção TLS penaliza conexões concorrentes — por isso sequencial,
não paralelo (ver docs/DOSSIE_PLATAFORMA.md, decisão "Fallback sequencial").
Agregação (consensus_median/twap) é evolução da Fase 3.
"""
from __future__ import annotations

from predictor_core.obs import emit_event

from GarimpoInvestimentos.dpl.contracts import (
    DataProvider,
    DataUnavailableError,
    MarketDataPoint,
)

_DOMAIN = "previsao_cripto"


class FallbackRouter:
    def __init__(self, providers: list[DataProvider]):
        if not providers:
            raise ValueError("FallbackRouter exige ao menos um provedor")
        self._providers = providers

    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        last_exc: Exception | None = None
        for idx, provider in enumerate(self._providers):
            try:
                points = await provider.fetch_ohlcv(symbol, interval=interval, limit=limit)
                if idx > 0:
                    # Sucesso só após pelo menos uma fonte ter falhado: registra que
                    # operamos em modo degradado (a primária não respondeu).
                    emit_event(
                        _DOMAIN, "data.fallback",
                        metrics={"provider_index": idx},
                        metadata={"symbol": symbol, "interval": interval,
                                  "used": provider.name},
                    )
                return points
            except Exception as exc:  # noqa: BLE001 — qualquer falha aciona o próximo
                last_exc = exc
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
