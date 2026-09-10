"""FRED DTWEXBGS observed vintage, not an invented historical publication date.

The H.10 release is weekly and historical FRED values can be revised.
This current CSV provides no publication history. Values become usable at receipt.
Historical tests require archived releases or a separately verified vintage table.
https://www.federalreserve.gov/releases/h10/about.htm
"""

from __future__ import annotations

import csv
import io
import math
from datetime import UTC, datetime

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.business_days import add_business_days
from GarimpoInvestimentos.dpl.signals import SignalPoint, SignalProvider

_BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_DEFAULT_SERIES = "DTWEXBGS"  # Nominal Broad U.S. Dollar Index (diário)


# Alias retrocompatível: a implementação canônica vive em dpl/business_days.py
# (fonte única — ver o docstring de lá para o look-ahead que a duplicação causou).
_add_business_days = add_business_days


class DXYProvider(SignalProvider):
    """Série diária de um índice de força do dólar do FRED. `name` fixo (casa com
    o alignment engine); `series` é o ID da série FRED — parametrizável caso se
    prefira outra variante (ex.: DTWEXAFEGS, economias avançadas)."""

    name = "dxy"

    def __init__(self, series: str = _DEFAULT_SERIES, publish_lag_days: int = 1):
        if (
            isinstance(publish_lag_days, bool)
            or not isinstance(publish_lag_days, int)
            or publish_lag_days < 0
        ):
            raise ValueError("publish_lag_days nao pode ser negativo ou fracionario")
        self._series = series
        self._lag_business_days = publish_lag_days

    @with_retry()
    async def _get_csv(self) -> str:
        async with get_http_client() as client:
            resp = await client.get(_BASE_URL, params={"id": self._series})
            resp.raise_for_status()
            return resp.text

    async def fetch(self, limit: int = 90) -> list[SignalPoint]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit deve ser inteiro positivo")
        raw = await self._get_csv()
        received_at = datetime.now(UTC)
        rows = list(csv.DictReader(io.StringIO(raw)))
        if not rows or self._series not in rows[0]:
            raise RuntimeError(
                f"dxy[{self._series}]: resposta vazia ou formato de CSV inesperado "
                f"(verifique a série em https://fred.stlouisfed.org/series/{self._series})"
            )

        points: list[SignalPoint] = []
        seen: dict[datetime, float] = {}
        for row in rows:
            if row.get(self._series) == ".":
                continue
            try:
                day = datetime.strptime(row["observation_date"], "%Y-%m-%d").replace(tzinfo=UTC)
                value = float(row[self._series])
            except (KeyError, ValueError) as exc:
                raise ValueError("Linha FRED invalida") from exc
            if not math.isfinite(value) or value <= 0 or day > received_at:
                raise ValueError("Valor/data FRED invalido")
            if day in seen:
                if seen[day] != value:
                    raise ValueError("FRED tem observacoes conflitantes")
                continue
            seen[day] = value
            points.append(
                SignalPoint(
                    name=self.name,
                    timestamp=day,
                    value=value,
                    source="fred",
                    published_at=received_at,
                    vintage=received_at,
                    collector_version="fred_observed_vintage_v2",
                    quality_flags=frozenset(
                        {"publication_history_unverified", "available_at_receipt"}
                    ),
                )
            )
        if not points:
            raise RuntimeError(f"dxy[{self._series}]: nenhuma linha válida no CSV recebido")
        return sorted(points, key=lambda point: point.timestamp)[-limit:]
