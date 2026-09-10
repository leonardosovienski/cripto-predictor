"""BCB SGS current observations, stamped at the receipt of this vintage.

Reference dates identify periods, not releases. A fixed lag cannot date revisions.
Historical as-of use requires an independently documented release/vintage archive.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.circuit_breaker import CircuitBreaker, CircuitOpenError
from GarimpoInvestimentos.dpl.signals import SignalPoint, SignalProvider
from GarimpoInvestimentos.trading.contracts import ensure_utc

_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{n}"


class BCBProvider(SignalProvider):
    """Um provider por série SGS. `name` é o rótulo da feature (ex.: 'selic')."""

    def __init__(
        self,
        series_code: int,
        name: str,
        *,
        publish_lag_days: int = 1,
        breaker: CircuitBreaker | None = None,
    ):
        if (
            isinstance(series_code, bool)
            or not isinstance(series_code, int)
            or series_code <= 0
            or not name
        ):
            raise ValueError("series_code/name invalido")
        if (
            isinstance(publish_lag_days, bool)
            or not isinstance(publish_lag_days, int)
            or publish_lag_days < 0
        ):
            raise ValueError("lag invalido")
        self.series_code = series_code
        self.name = name
        # Legacy parameter accepted for compatibility; never used to backdate publication.
        self._breaker = breaker

    @with_retry()
    async def _get(self, limit: int) -> list[dict]:
        async with get_http_client() as client:
            url = _BASE.format(code=self.series_code, n=limit)
            resp = await client.get(url, params={"formato": "json"})
            resp.raise_for_status()
            return resp.json()

    async def fetch(
        self, limit: int = 30, *, collected_at: datetime | None = None
    ) -> list[SignalPoint]:
        if self._breaker is not None and not self._breaker.allow():
            raise CircuitOpenError(f"bcb[{self.name}]: circuito aberto")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit deve ser inteiro positivo")
        if collected_at is not None:
            ensure_utc(collected_at, "collected_at")
        try:
            rows = await self._get(limit)
            vintage = ensure_utc(collected_at or datetime.now(UTC), "collected_at")
        except Exception:
            if self._breaker is not None:
                self._breaker.record_failure()
            raise
        if self._breaker is not None:
            self._breaker.record_success()

        points = []
        seen = {}
        for item in rows:
            ref = datetime.strptime(item["data"], "%d/%m/%Y").replace(tzinfo=UTC)
            value = float(item["valor"])
            if not math.isfinite(value) or ref > vintage:
                raise ValueError("valor/data SGS invalido")
            if ref in seen:
                if seen[ref] != value:
                    raise ValueError("observacoes SGS conflitantes")
                continue
            seen[ref] = value
            points.append(
                SignalPoint(
                    name=self.name,
                    timestamp=ref,
                    value=value,
                    source="bcb_sgs",
                    published_at=vintage,
                    collector_version="bcb_observed_vintage_v2",
                    quality_flags=frozenset(
                        {"publication_history_unverified", "available_at_receipt"}
                    ),
                    reference_date=ref,
                    vintage=vintage,
                )
            )
        if not points:
            raise RuntimeError(f"bcb[{self.name}]: resposta vazia")
        return sorted(points, key=lambda point: point.timestamp)
