"""DXYProvider — US Dollar Index (DXY) via stooq.com (CSV público, sem chave).

Parte do backlog B1 (docs/HYPOTHESES.md, H7): DXY como contexto exógeno de regime,
ortogonal a tudo que já foi testado (nenhum sinal atual do projeto olha câmbio/juros).

Fechamento diário, publicado no próprio dia (mercado fecha, o CSV atualiza no fim do
pregão) — mesmo padrão conservador do FearAndGreedProvider: published_at = timestamp.

⚠️ Endpoint e símbolo NÃO verificados ao vivo: este ambiente de desenvolvimento não
tem rede liberada para hosts externos (só PyPI/npm/GitHub). O teste deste módulo usa
HTTP mockado. Antes do primeiro uso real, rode `fetch()` uma vez num ambiente com rede
e confira o CSV retornado; se o símbolo "dx.f" não resolver em stooq.com, ajuste
`DXYProvider(symbol=...)` (lista de símbolos em https://stooq.com/db/h/).
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.dpl.signals import SignalPoint, SignalProvider

_BASE_URL = "https://stooq.com/q/d/l/"
_DEFAULT_SYMBOL = "dx.f"  # contrato contínuo de futuros do ICE US Dollar Index


class DXYProvider(SignalProvider):
    """Série diária do US Dollar Index. `name` fixo (casa com o alignment engine);
    `symbol` é o ticker do stooq — parametrizável caso o default não resolva."""

    name = "dxy"

    def __init__(self, symbol: str = _DEFAULT_SYMBOL):
        self._symbol = symbol

    @with_retry()
    async def _get_csv(self) -> str:
        async with get_http_client() as client:
            resp = await client.get(_BASE_URL, params={"s": self._symbol, "i": "d"})
            resp.raise_for_status()
            return resp.text

    async def fetch(self, limit: int = 90) -> list[SignalPoint]:
        raw = await self._get_csv()
        rows = list(csv.DictReader(io.StringIO(raw)))
        if not rows or "Close" not in rows[0]:
            raise RuntimeError(
                f"dxy[{self._symbol}]: resposta vazia ou formato de CSV inesperado "
                "(verifique o símbolo em https://stooq.com/db/h/)"
            )

        points: list[SignalPoint] = []
        for row in rows[-limit:]:
            try:
                day = datetime.strptime(row["Date"], "%Y-%m-%d").replace(tzinfo=UTC)
                close = float(row["Close"])
            except (KeyError, ValueError):
                continue  # linha malformada (ex.: "N/D" em pregão sem fechamento) — pula, não interpola
            points.append(
                SignalPoint(
                    name=self.name,
                    timestamp=day,
                    value=close,
                    source="stooq",
                    published_at=day,
                )
            )
        if not points:
            raise RuntimeError(f"dxy[{self._symbol}]: nenhuma linha válida no CSV recebido")
        return points
