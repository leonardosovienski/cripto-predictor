"""FearAndGreedProvider — sentimento diário do mercado cripto (alternative.me).

Fonte de BAIXA frequência (1 ponto/dia) usada como prova de conceito da fusão de
granularidades do Alignment Engine: diário (sentimento) × horário/diário (preço).
O índice de um dia é publicado naquele mesmo dia → published_at = timestamp.
"""
from __future__ import annotations

from datetime import datetime, timezone

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.signals import SignalPoint, SignalProvider

_URL = "https://api.alternative.me/fng/"


class FearAndGreedProvider(SignalProvider):
    name = "fear_greed"

    @with_retry()
    async def fetch(self, limit: int = 30) -> list[SignalPoint]:
        async with get_http_client() as client:
            resp = await client.get(_URL, params={"limit": str(limit), "format": "json"})
            resp.raise_for_status()
            data = resp.json()
        points = []
        for item in data.get("data", []):
            ts = datetime.fromtimestamp(int(item["timestamp"]), tz=timezone.utc)
            points.append(
                SignalPoint(
                    name=self.name,
                    timestamp=ts,
                    value=float(item["value"]),
                    source="alternative.me",
                    published_at=ts,  # índice diário publicado no próprio dia
                )
            )
        if not points:
            raise RuntimeError("fear_greed: resposta vazia")
        return points
