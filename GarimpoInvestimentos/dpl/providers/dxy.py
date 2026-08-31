"""DXYProvider — Nominal Broad U.S. Dollar Index (Federal Reserve, série DTWEXBGS)
via FRED (fredgraph.csv, público, sem chave).

Parte do backlog B1 (docs/HYPOTHESES.md, H7): força do dólar como contexto exógeno
de regime, ortogonal a tudo que já foi testado. Fonte trocada de stooq.com (que
passou a exigir um desafio anti-bot em JavaScript no endpoint de CSV — confirmado
ao vivo em 2026-08-14, não é mais acessível por um cliente HTTP simples, e
contorná-lo não é algo que este projeto deveria fazer) para o FRED — dado oficial
do Federal Reserve, mesma instituição do calendário FOMC em macro_calendar.json.

`DTWEXBGS` é publicada pelo Fed com defasagem: o release H.10 (foreign exchange
rates) de um dia útil sai no dia útil seguinte. O lag exato NÃO foi confirmado
contra o texto oficial do release nesta sessão — `publish_lag_days=1` é a
estimativa conservadora (assume o dado mais tarde disponível, nunca mais cedo);
confirme contra https://www.federalreserve.gov/releases/h10/ antes de depender
disso para timing fino.

Endpoint revalidado ao vivo em 2026-08-31 pelo próprio `DXYProvider`: retornou
observações válidas de 2026-08-24 a 2026-08-28, com `source=fred`, sem interpolar
feriados. O CSV usa o cabeçalho `observation_date,DTWEXBGS` (o FRED
usa `observation_date`, não `DATE`, como nome da primeira coluna — só isso
tinha ficado errado na primeira versão). `Invoke-WebRequest` do PowerShell
travou/deu timeout contra o mesmo endpoint que o `curl` respondeu rápido —
suspeita de inspeção de TLS no proxy corporativo interferindo com um cliente
especificamente; o `httpx` usado aqui respondeu no smoke de 2026-08-31.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.signals import SignalPoint, SignalProvider

_BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_DEFAULT_SERIES = "DTWEXBGS"  # Nominal Broad U.S. Dollar Index (diário)


class DXYProvider(SignalProvider):
    """Série diária de um índice de força do dólar do FRED. `name` fixo (casa com
    o alignment engine); `series` é o ID da série FRED — parametrizável caso se
    prefira outra variante (ex.: DTWEXAFEGS, economias avançadas)."""

    name = "dxy"

    def __init__(self, series: str = _DEFAULT_SERIES, publish_lag_days: int = 1):
        self._series = series
        self._lag = timedelta(days=publish_lag_days)

    @with_retry()
    async def _get_csv(self) -> str:
        async with get_http_client() as client:
            resp = await client.get(_BASE_URL, params={"id": self._series})
            resp.raise_for_status()
            return resp.text

    async def fetch(self, limit: int = 90) -> list[SignalPoint]:
        raw = await self._get_csv()
        rows = list(csv.DictReader(io.StringIO(raw)))
        if not rows or self._series not in rows[0]:
            raise RuntimeError(
                f"dxy[{self._series}]: resposta vazia ou formato de CSV inesperado "
                f"(verifique a série em https://fred.stlouisfed.org/series/{self._series})"
            )

        points: list[SignalPoint] = []
        for row in rows[-limit:]:
            try:
                day = datetime.strptime(row["observation_date"], "%Y-%m-%d").replace(tzinfo=UTC)
                value = float(row[self._series])
            except (KeyError, ValueError):
                continue  # "." = feriado/sem dado publicado — pula, não interpola
            points.append(
                SignalPoint(
                    name=self.name,
                    timestamp=day,
                    value=value,
                    source="fred",
                    published_at=day + self._lag,
                )
            )
        if not points:
            raise RuntimeError(f"dxy[{self._series}]: nenhuma linha válida no CSV recebido")
        return points
