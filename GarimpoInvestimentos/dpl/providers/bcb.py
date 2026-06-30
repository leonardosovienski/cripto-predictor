"""BCBProvider — séries macro do Banco Central (SGS) → SignalPoint.

Ex.: Selic (cód. 11/432), IPCA (433), câmbio (1). Reusa predictor_core.net (httpx +
retry/backoff) e, opcionalmente, um CircuitBreaker. Modela point-in-time:
  - reference_date : data de referência (vem da API).
  - published_at   : reference_date + lag de divulgação (macro não é público no dia
                     da referência — IPCA do mês M sai em ~M+1). Configurável por série.
  - vintage        : instante da coleta — distingue revisões (mesmo reference_date,
                     valor diferente coletado depois).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.circuit_breaker import CircuitBreaker, CircuitOpenError
from GarimpoInvestimentos.dpl.signals import SignalPoint, SignalProvider

_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{n}"


class BCBProvider(SignalProvider):
    """Um provider por série SGS. `name` é o rótulo da feature (ex.: 'selic')."""

    def __init__(self, series_code: int, name: str, *, publish_lag_days: int = 1,
                 breaker: CircuitBreaker | None = None):
        self.series_code = series_code
        self.name = name
        self._lag = timedelta(days=publish_lag_days)
        self._breaker = breaker

    @with_retry()
    async def _get(self, limit: int) -> list[dict]:
        async with get_http_client() as client:
            url = _BASE.format(code=self.series_code, n=limit)
            resp = await client.get(url, params={"formato": "json"})
            resp.raise_for_status()
            return resp.json()

    async def fetch(self, limit: int = 30, *, collected_at: datetime | None = None
                    ) -> list[SignalPoint]:
        if self._breaker is not None and not self._breaker.allow():
            raise CircuitOpenError(f"bcb[{self.name}]: circuito aberto")
        vintage = collected_at or datetime.now(timezone.utc)
        try:
            rows = await self._get(limit)
        except Exception:
            if self._breaker is not None:
                self._breaker.record_failure()
            raise
        if self._breaker is not None:
            self._breaker.record_success()

        points = []
        for item in rows:
            ref = datetime.strptime(item["data"], "%d/%m/%Y").replace(tzinfo=timezone.utc)
            points.append(SignalPoint(
                name=self.name, timestamp=ref, value=float(item["valor"]),
                source="bcb_sgs", published_at=ref + self._lag,
                reference_date=ref, vintage=vintage,
            ))
        if not points:
            raise RuntimeError(f"bcb[{self.name}]: resposta vazia")
        return points
