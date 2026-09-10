"""FearAndGreedProvider — sentimento diário do mercado cripto (alternative.me).

Fonte de BAIXA frequência (1 ponto/dia) usada como prova de conceito da fusão de
granularidades do Alignment Engine: diário (sentimento) × horário/diário (preço).
O timestamp da API e a referencia. Esta versao fica disponivel no recebimento;
nao existe prova de publicacao historica neste endpoint.
"""

from __future__ import annotations

import math
import time
from datetime import UTC, datetime

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.signals import SignalPoint, SignalProvider

_URL = "https://api.alternative.me/fng/"


class FearAndGreedProvider(SignalProvider):
    name = "fear_greed"

    def __init__(self, cache_ttl_seconds: float = 300.0):
        if not math.isfinite(cache_ttl_seconds) or cache_ttl_seconds <= 0:
            raise ValueError("cache_ttl_seconds deve ser positivo finito")
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[int, tuple[float, tuple[SignalPoint, ...]]] = {}

    @with_retry()
    async def fetch(self, limit: int = 30) -> list[SignalPoint]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit deve ser inteiro positivo")
        cached = self._cache.get(limit)
        if cached and time.monotonic() - cached[0] < self._cache_ttl_seconds:
            return list(cached[1])
        async with get_http_client() as client:
            resp = await client.get(_URL, params={"limit": str(limit), "format": "json"})
            resp.raise_for_status()
            data = resp.json()
        received_at = datetime.now(UTC)
        points = []
        seen = {}
        for item in data.get("data", []):
            ts = datetime.fromtimestamp(int(item["timestamp"]), tz=UTC)
            value = float(item["value"])
            if not math.isfinite(value) or not 0 <= value <= 100 or ts > received_at:
                raise ValueError("Fear and Greed com valor/data invalido")
            if ts in seen:
                if seen[ts] != value:
                    raise ValueError("Fear and Greed com observacoes conflitantes")
                continue
            seen[ts] = value
            points.append(
                SignalPoint(
                    name=self.name,
                    timestamp=ts,
                    value=value,
                    source="alternative.me",
                    published_at=received_at,
                    vintage=received_at,
                    collector_version="fear_greed_observed_vintage_v2",
                    quality_flags=frozenset(
                        {"publication_history_unverified", "available_at_receipt"}
                    ),
                )
            )
        if not points:
            raise RuntimeError("fear_greed: resposta vazia")
        points.sort(key=lambda point: point.timestamp)
        self._cache[limit] = (time.monotonic(), tuple(points))
        return list(points)
