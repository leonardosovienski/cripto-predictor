"""CCXTProvider — base genérica para conectores de exchange via CCXT.

O CCXT abstrai 100+ exchanges com a mesma API; um conector concreto é só o id da
exchange + o symbol_map. Binance e Kraken (Fase 3) são subclasses triviais. O CCXT
é encapsulado AQUI: o domínio nunca o importa. Import lazy → o pacote dpl é
importável sem ccxt instalado (testes injetam provedores fake).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from GarimpoInvestimentos.dpl.contracts import DataProvider, MarketDataPoint
from GarimpoInvestimentos.dpl.providers._validation import require_finite

logger = logging.getLogger(__name__)

_SUPPORTED_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d"}
_INTERVAL_DURATION = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
}


class CCXTProvider(DataProvider):
    #: id da exchange no CCXT (ex.: "binance", "kraken"). Subclasses sobrescrevem.
    exchange_id: str = "abstract"

    def __init__(self, symbol_map: dict[str, str]):
        self._symbol_map = symbol_map

    @property
    def name(self) -> str:
        return self.exchange_id

    def _client(self):
        # Instância NOVA por chamada: o cliente async detém uma sessão aiohttp que
        # precisa ser fechada; reusar uma já fechada quebraria a próxima chamada.
        import ccxt.async_support as ccxt

        return getattr(ccxt, self.exchange_id)({"enableRateLimit": True})

    def _native_symbol(self, symbol: str) -> str:
        try:
            return self._symbol_map[symbol]
        except KeyError as exc:
            raise ValueError(
                f"{self.exchange_id}: símbolo '{symbol}' sem mapeamento em sources.json"
            ) from exc

    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        if interval not in _SUPPORTED_INTERVALS:
            raise ValueError(f"{self.exchange_id}: intervalo '{interval}' não suportado")
        pair = self._native_symbol(symbol)
        client = self._client()
        try:
            rows = await client.fetch_ohlcv(pair, timeframe=interval, limit=limit)
        finally:
            try:
                await client.close()
            except Exception:
                # Best-effort: um close() com falha não deve mascarar o erro
                # original do bloco try acima (relançado via `finally`), só
                # não há ação corretiva possível aqui além de registrar.
                logger.debug("%s: falha ao fechar client ccxt (ignorada)", self.exchange_id)
        points = []
        collected_at = datetime.now(UTC)
        for ts_ms, o, h, l, c, v in rows:
            ts = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
            available_at = ts + _INTERVAL_DURATION[interval]
            # CCXT timestamps identify candle OPEN. OHLCV final values are not
            # knowable until the interval closes. Never persist the live candle
            # as though its final close/high/low/volume were already public.
            if available_at > collected_at:
                continue
            kw = {
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": float(v),
            }
            for field, val in kw.items():
                require_finite(val, field=field, provider=self.exchange_id, symbol=symbol)
            points.append(
                MarketDataPoint(
                    symbol=symbol,
                    timestamp=ts,
                    source=self.name,
                    interval=interval,
                    published_at=available_at,
                    **kw,
                )
            )
        if not points:
            raise RuntimeError(f"{self.exchange_id}: resposta vazia para {pair}")
        return points

    async def health_check(self) -> bool:
        client = self._client()
        try:
            await client.fetch_status()
            return True
        except Exception:
            return False
        finally:
            try:
                await client.close()
            except Exception:
                # Best-effort: um close() com falha não deve mascarar o erro
                # original do bloco try acima (relançado via `finally`), só
                # não há ação corretiva possível aqui além de registrar.
                logger.debug("%s: falha ao fechar client ccxt (ignorada)", self.exchange_id)
