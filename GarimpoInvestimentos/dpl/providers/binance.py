"""BinanceProvider — wrapper fino sobre o CCXT (fonte primária de preço).

O CCXT é encapsulado AQUI: o domínio nunca importa ccxt. Trocar Binance por
Kraken (Fase 3) é só instanciar outro id de exchange — o CCXT abstrai ambos.
O import do ccxt é LAZY (dentro dos métodos) para que o pacote dpl seja
importável sem ccxt instalado (ex.: nos testes que injetam provedores fake).
"""
from __future__ import annotations

from datetime import datetime, timezone

from GarimpoInvestimentos.dpl.contracts import DataProvider, MarketDataPoint

# CCXT usa timeframes no formato "1m"/"1h"/"1d"; o domínio já fala esse dialeto,
# então o mapa é identidade para os intervalos suportados no piloto.
_SUPPORTED_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d"}


class BinanceProvider(DataProvider):
    name = "binance"

    def __init__(self, symbol_map: dict[str, str]):
        """`symbol_map` traduz o ID canônico do domínio → par nativo da exchange.
        Ex.: {"bitcoin": "BTC/USDT"}. Vem do sources.json.
        """
        self._symbol_map = symbol_map

    def _client(self):
        # Instância NOVA por chamada: o cliente ccxt async detém uma sessão aiohttp
        # que precisa ser fechada (close()) ao fim. Reusar uma instância já fechada
        # quebraria a próxima chamada — por isso criamos e fechamos a cada operação.
        import ccxt.async_support as ccxt  # lazy: só quem usa Binance precisa de ccxt

        return ccxt.binance({"enableRateLimit": True})

    def _native_symbol(self, symbol: str) -> str:
        try:
            return self._symbol_map[symbol]
        except KeyError as exc:
            raise ValueError(
                f"binance: símbolo '{symbol}' sem mapeamento em sources.json"
            ) from exc

    async def fetch_ohlcv(
        self, symbol: str, interval: str = "1d", limit: int = 1
    ) -> list[MarketDataPoint]:
        if interval not in _SUPPORTED_INTERVALS:
            raise ValueError(f"binance: intervalo '{interval}' não suportado")
        pair = self._native_symbol(symbol)
        client = self._client()
        try:
            # CCXT devolve [[ts_ms, open, high, low, close, volume], ...]
            rows = await client.fetch_ohlcv(pair, timeframe=interval, limit=limit)
        finally:
            try:
                await client.close()
            except Exception:
                pass
        points = []
        for ts_ms, o, h, l, c, v in rows:
            ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            points.append(
                MarketDataPoint(
                    symbol=symbol,
                    timestamp=ts,
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(v),
                    source=self.name,
                    interval=interval,
                    # candle de exchange: disponível ao fechar o período.
                    published_at=ts,
                )
            )
        if not points:
            raise RuntimeError(f"binance: resposta vazia para {pair}")
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
                pass
