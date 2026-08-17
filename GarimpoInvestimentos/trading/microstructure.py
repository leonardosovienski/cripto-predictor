"""Microestrutura — book de ofertas, simulação de fill contra profundidade, impacto.

Parte do override de governança 2026-08-14 (docs/HYPOTHESES.md). Fecha a lacuna de
"custo fixo em bps" (v3/costs.py: 10bps taker + 5bps slippage, o mesmo número
para qualquer tamanho de ordem) com simulação que anda o book de verdade — o custo
de uma ordem de 0.01 BTC não é o mesmo de uma de 10 BTC, e só profundidade real
diferencia isso.

⚠️ `sqrt_impact_bps` é uma fórmula-texto-padrão (Almgren-Chriss/Kyle simplificado),
NÃO calibrada contra fills reais deste projeto — ver aviso completo no docstring da
função. `BinanceOrderBookCollector` não foi verificado ao vivo nesta sessão (rede
bloqueada para hosts externos); testado só com HTTP mockado, mesma ressalva já
registrada para o DXYProvider.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from predictor_core.net import get_http_client, with_retry

from GarimpoInvestimentos.trading.contracts import Instrument, OrderSide, ensure_utc

_BINANCE_DEPTH_URL = "https://api.binance.com/api/v3/depth"


@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    qty: float

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError("OrderBookLevel.price deve ser > 0")
        if self.qty <= 0:
            raise ValueError("OrderBookLevel.qty deve ser > 0")


@dataclass(frozen=True)
class OrderBookSnapshot:
    """Book de ofertas num instante. `bids` decrescente por preço, `asks`
    crescente — validado na construção, nunca aceito fora de ordem."""

    instrument: Instrument
    timestamp: datetime
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]

    def __post_init__(self) -> None:
        ts = ensure_utc(self.timestamp, "OrderBookSnapshot.timestamp")
        if not self.bids or not self.asks:
            raise ValueError("OrderBookSnapshot precisa de ao menos 1 nível de bid e de ask")
        bid_prices = [level.price for level in self.bids]
        if bid_prices != sorted(bid_prices, reverse=True):
            raise ValueError("OrderBookSnapshot.bids devem estar ordenados por preço decrescente")
        ask_prices = [level.price for level in self.asks]
        if ask_prices != sorted(ask_prices):
            raise ValueError("OrderBookSnapshot.asks devem estar ordenados por preço crescente")
        if self.bids[0].price >= self.asks[0].price:
            raise ValueError(
                f"OrderBookSnapshot cruzado: best_bid ({self.bids[0].price}) >= "
                f"best_ask ({self.asks[0].price})"
            )
        object.__setattr__(self, "timestamp", ts)

    @property
    def best_bid(self) -> float:
        return self.bids[0].price

    @property
    def best_ask(self) -> float:
        return self.asks[0].price

    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2

    @property
    def spread_bps(self) -> float:
        return (self.best_ask - self.best_bid) / self.mid_price * 10_000


@dataclass(frozen=True)
class SimulatedFill:
    """Resultado de simular uma ordem a mercado contra um OrderBookSnapshot —
    NÃO é um Fill real (trading/contracts.py); é a estimativa de como o mercado
    reagiria, pra alimentar backtest/pré-trade check, nunca pra registrar
    execução de verdade."""

    side: OrderSide
    requested_qty: float
    filled_qty: float
    vwap_price: float | None
    slippage_bps: float | None  # custo vs. mid, sempre >= 0 pra quem cruza o spread
    levels_consumed: int

    @property
    def fully_filled(self) -> bool:
        return self.filled_qty >= self.requested_qty - 1e-12


@dataclass(frozen=True)
class CollectedOrderBook:
    """Envelope temporal do snapshot REST.

    O endpoint de depth não fornece event time. Por honestidade, `timestamp` do
    snapshot é o instante local de recebimento, e a ausência do tempo do venue
    fica explícita em quality_flags. `lastUpdateId` é preservado para permitir
    ligação futura com o diff-depth WebSocket; um snapshot sozinho não prova
    continuidade do book.
    """

    snapshot: OrderBookSnapshot
    last_update_id: int
    requested_at: datetime
    received_at: datetime
    ingested_at: datetime
    quality_flags: frozenset[str] = frozenset({"snapshot_no_exchange_event_time"})

    def __post_init__(self) -> None:
        requested = ensure_utc(self.requested_at, "CollectedOrderBook.requested_at")
        received = ensure_utc(self.received_at, "CollectedOrderBook.received_at")
        ingested = ensure_utc(self.ingested_at, "CollectedOrderBook.ingested_at")
        if self.last_update_id < 0:
            raise ValueError("CollectedOrderBook.last_update_id não pode ser negativo")
        if not (requested <= received <= ingested):
            raise ValueError("tempos precisam obedecer requested_at <= received_at <= ingested_at")
        object.__setattr__(self, "requested_at", requested)
        object.__setattr__(self, "received_at", received)
        object.__setattr__(self, "ingested_at", ingested)


@dataclass(frozen=True)
class DepthUpdate:
    instrument: Instrument
    first_update_id: int
    final_update_id: int
    event_at: datetime
    bids: tuple[tuple[float, float], ...]
    asks: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        event_at = ensure_utc(self.event_at, "DepthUpdate.event_at")
        if self.first_update_id < 0 or self.final_update_id < self.first_update_id:
            raise ValueError("DepthUpdate sequence inválida")
        for price, qty in (*self.bids, *self.asks):
            if price <= 0 or qty < 0:
                raise ValueError("DepthUpdate exige price > 0 e qty >= 0")
        object.__setattr__(self, "event_at", event_at)


class DepthSequenceGap(RuntimeError):
    """O book local perdeu updates e precisa de novo snapshot."""


class LocalOrderBook:
    """Reconstrói um book a partir de snapshot REST + diff-depth ordenado."""

    def __init__(self, snapshot: OrderBookSnapshot, *, last_update_id: int):
        if last_update_id < 0:
            raise ValueError("last_update_id não pode ser negativo")
        self._instrument = snapshot.instrument
        self._last_update_id = last_update_id
        self._timestamp = snapshot.timestamp
        self._bids = {level.price: level.qty for level in snapshot.bids}
        self._asks = {level.price: level.qty for level in snapshot.asks}

    @property
    def last_update_id(self) -> int:
        return self._last_update_id

    def apply(self, update: DepthUpdate) -> bool:
        if update.instrument != self._instrument:
            raise ValueError("DepthUpdate pertence a outro instrumento/venue")
        if update.final_update_id <= self._last_update_id:
            return False
        expected = self._last_update_id + 1
        if not (update.first_update_id <= expected <= update.final_update_id):
            raise DepthSequenceGap(
                f"gap de sequence: esperado {expected}, recebido "
                f"[{update.first_update_id},{update.final_update_id}]"
            )
        for book, changes in ((self._bids, update.bids), (self._asks, update.asks)):
            for price, qty in changes:
                if qty == 0:
                    book.pop(price, None)
                else:
                    book[price] = qty
        if not self._bids or not self._asks:
            raise DepthSequenceGap("update esvaziou um lado do book; resnapshot obrigatório")
        self._last_update_id = update.final_update_id
        self._timestamp = update.event_at
        return True

    def snapshot(self) -> OrderBookSnapshot:
        bids = tuple(
            OrderBookLevel(price, qty) for price, qty in sorted(self._bids.items(), reverse=True)
        )
        asks = tuple(OrderBookLevel(price, qty) for price, qty in sorted(self._asks.items()))
        return OrderBookSnapshot(self._instrument, self._timestamp, bids, asks)


def simulate_market_fill(snapshot: OrderBookSnapshot, side: OrderSide, qty: float) -> SimulatedFill:
    """Anda o book nível a nível ("walk the book") consumindo liquidez até
    preencher `qty` ou esgotar os níveis disponíveis — nunca preenche além do
    que o book realmente oferece, nunca interpola profundidade que não existe."""
    if qty <= 0:
        raise ValueError("simulate_market_fill: qty deve ser > 0")
    levels = snapshot.asks if side is OrderSide.BUY else snapshot.bids

    remaining = qty
    notional = 0.0
    levels_consumed = 0
    for level in levels:
        if remaining <= 1e-12:
            break
        take = min(remaining, level.qty)
        notional += take * level.price
        remaining -= take
        levels_consumed += 1

    filled_qty = qty - remaining
    vwap_price = (notional / filled_qty) if filled_qty > 1e-12 else None
    slippage_bps = None
    if vwap_price is not None:
        sign = 1.0 if side is OrderSide.BUY else -1.0
        slippage_bps = sign * (vwap_price - snapshot.mid_price) / snapshot.mid_price * 10_000

    return SimulatedFill(
        side=side,
        requested_qty=qty,
        filled_qty=filled_qty,
        vwap_price=vwap_price,
        slippage_bps=slippage_bps,
        levels_consumed=levels_consumed,
    )


def sqrt_impact_bps(participation_rate: float, volatility_bps: float, kappa: float = 1.0) -> float:
    """Modelo de impacto raiz-quadrada (Almgren-Chriss/Kyle simplificado):
    impacto(bps) = kappa * sqrt(participation_rate) * volatility_bps.

    ⚠️ FÓRMULA-TEXTO-PADRÃO, NÃO CALIBRADA: `kappa=1.0` é um placeholder
    didático, não um coeficiente ajustado a fills reais deste projeto — mesmo
    status do resto da camada de trading construída no override de governança
    de 2026-08-14 (docs/HYPOTHESES.md). Não usar pra decidir GO/NO-GO sem
    calibração contra execução real; `simulate_market_fill` (que anda o book
    de verdade) é a estimativa mais confiável disponível hoje.

    `participation_rate`: fração do volume da janela que a própria ordem
    representa, em [0, 1]. `volatility_bps`: volatilidade do ativo no mesmo
    horizonte, em bps.
    """
    if not (0 <= participation_rate <= 1):
        raise ValueError("sqrt_impact_bps: participation_rate deve estar em [0, 1]")
    if volatility_bps < 0:
        raise ValueError("sqrt_impact_bps: volatility_bps não pode ser negativo")
    if kappa < 0:
        raise ValueError("sqrt_impact_bps: kappa não pode ser negativo")
    return kappa * math.sqrt(participation_rate) * volatility_bps


class BinanceOrderBookCollector:
    """Coletor de snapshot do book da Binance spot (`GET /api/v3/depth`, público,
    sem chave). NÃO verificado ao vivo nesta sessão — rede bloqueada para hosts
    externos no ambiente de desenvolvimento; testado só com HTTP mockado, mesma
    ressalva já registrada para o DXYProvider (dpl/providers/dxy.py)."""

    def __init__(self, venue: str = "binance_spot"):
        self._venue = venue

    @with_retry()
    async def _get_depth(self, symbol: str, limit: int) -> dict:
        async with get_http_client() as client:
            resp = await client.get(
                _BINANCE_DEPTH_URL, params={"symbol": symbol, "limit": str(limit)}
            )
            resp.raise_for_status()
            return resp.json()

    async def fetch_observation(self, symbol: str, *, limit: int = 100) -> CollectedOrderBook:
        if limit not in {5, 10, 20, 50, 100, 500, 1000, 5000}:
            raise ValueError("binance depth limit inválido")
        requested_at = datetime.now(UTC)
        data = await self._get_depth(symbol, limit)
        received_at = datetime.now(UTC)
        if "lastUpdateId" not in data or "bids" not in data or "asks" not in data:
            raise RuntimeError(
                f"binance_orderbook[{symbol}]: resposta sem lastUpdateId/bids/asks — "
                "formato inesperado"
            )
        bids = tuple(OrderBookLevel(float(p), float(q)) for p, q in data["bids"])
        asks = tuple(OrderBookLevel(float(p), float(q)) for p, q in data["asks"])
        snapshot = OrderBookSnapshot(
            instrument=Instrument(symbol.upper(), self._venue, "crypto_spot"),
            timestamp=received_at,
            bids=bids,
            asks=asks,
        )
        return CollectedOrderBook(
            snapshot=snapshot,
            last_update_id=int(data["lastUpdateId"]),
            requested_at=requested_at,
            received_at=received_at,
            ingested_at=datetime.now(UTC),
        )

    async def fetch(self, symbol: str, *, limit: int = 100) -> OrderBookSnapshot:
        """Compatibilidade: consumidores novos devem preferir fetch_observation()."""
        return (await self.fetch_observation(symbol, limit=limit)).snapshot
