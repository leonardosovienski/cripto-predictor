"""Deterministic synthetic spot order lifecycle with capital reserved per venue/asset.

Fills are explicit scenario inputs, not inferred from last/mark/L2. No exchange API.
Amounts use Decimal without venue-specific rounding; derivatives are unsupported.
"""

from dataclasses import dataclass
from decimal import Decimal


def amount(value: str | int | Decimal) -> Decimal:
    if isinstance(value, (bool, float)):
        raise ValueError("Use exact decimal strings, not floats")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Finite amount required")
    return result


@dataclass(frozen=True)
class SpotContract:
    instrument_id: str
    venue: str
    base: str
    quote: str
    quantity_unit: str
    price_unit: str
    settlement: str

    def __post_init__(self):
        if any(not isinstance(v, str) or not v for v in vars(self).values()):
            raise ValueError("Explicit synthetic identity required")
        if (
            self.base == self.quote
            or self.quantity_unit != self.base
            or self.price_unit != f"{self.quote}/{self.base}"
            or self.settlement != self.quote
        ):
            raise ValueError("Only declared direct spot contracts supported")


@dataclass
class SimOrder:
    contract: SpotContract
    side: str
    quantity: Decimal
    limit: Decimal
    fee_rate: Decimal
    active_at: int
    filled: Decimal = Decimal(0)
    state: str = "OPEN"


class ScenarioLedger:
    def __init__(self, balances: dict[tuple[str, str], str], *, synthetic: bool):
        if synthetic is not True:
            raise ValueError(
                "Explicit synthetic scenario required; historical replay not certified"
            )
        self.balances = {k: amount(v) for k, v in balances.items()}
        if any(
            not isinstance(k, tuple) or len(k) != 2 or not all(isinstance(v, str) and v for v in k)
            for k in balances
        ) or any(v < 0 for v in self.balances.values()):
            raise ValueError("Invalid opening balances")
        self.reserved: dict[tuple[str, str], Decimal] = {}
        self.orders: dict[str, SimOrder] = {}
        self.fills: dict[str, tuple] = {}
        self.events: list[dict] = []
        self.clock = -1

    def _time(self, at: int):
        if type(at) is not int or at < 0 or at < self.clock:
            raise ValueError("Scenario clock must be monotonic")

    def free(self, venue: str, asset: str) -> Decimal:
        key = (venue, asset)
        return self.balances.get(key, Decimal(0)) - self.reserved.get(key, Decimal(0))

    @staticmethod
    def _reservation(order: SimOrder, quantity: Decimal) -> tuple[tuple[str, str], Decimal]:
        c = order.contract
        return (
            ((c.venue, c.quote), quantity * order.limit * (1 + order.fee_rate))
            if order.side == "BUY"
            else ((c.venue, c.base), quantity)
        )

    def submit(
        self,
        order_id: str,
        contract: SpotContract,
        side: str,
        quantity: str,
        limit: str,
        *,
        at: int,
        latency: int = 0,
        fee_rate: str = "0",
    ) -> None:
        self._time(at)
        q, p, fee = amount(quantity), amount(limit), amount(fee_rate)
        if (
            not isinstance(order_id, str)
            or not order_id
            or order_id in self.orders
            or side not in {"BUY", "SELL"}
        ):
            raise ValueError("Invalid or duplicate order")
        if q <= 0 or p <= 0 or not 0 <= fee < 1 or type(latency) is not int or latency < 0:
            raise ValueError("Invalid order terms")
        order = SimOrder(contract, side, q, p, fee, at + latency)
        key, reserve = self._reservation(order, q)
        if self.free(*key) < reserve:
            raise ValueError("Insufficient local venue/asset capital")
        self.reserved[key] = self.reserved.get(key, Decimal(0)) + reserve
        self.orders[order_id] = order
        self.clock = at
        self.events.append({"type": "SUBMIT", "order": order_id, "at": at})

    def fill(self, fill_id: str, order_id: str, quantity: str, price: str, *, at: int) -> bool:
        q, p = amount(quantity), amount(price)
        signature = (order_id, q, p, at)
        if fill_id in self.fills:
            if self.fills[fill_id] != signature:
                raise ValueError("Conflicting duplicate fill")
            return False
        self._time(at)
        if not isinstance(fill_id, str) or not fill_id:
            raise ValueError("Explicit fill ID required")
        o = self.orders[order_id]
        if (
            o.state not in {"OPEN", "PARTIALLY_FILLED"}
            or at < o.active_at
            or q <= 0
            or p <= 0
            or q > o.quantity - o.filled
        ):
            raise ValueError("Invalid fill state, latency or quantity")
        if (o.side == "BUY" and p > o.limit) or (o.side == "SELL" and p < o.limit):
            raise ValueError("Fill violates limit")
        key, release = self._reservation(o, q)
        base, quote = (o.contract.venue, o.contract.base), (o.contract.venue, o.contract.quote)
        fee = q * p * o.fee_rate
        self.reserved[key] -= release
        if o.side == "BUY":
            self.balances[quote] -= q * p + fee
            self.balances[base] = self.balances.get(base, Decimal(0)) + q
        else:
            self.balances[base] -= q
            self.balances[quote] = self.balances.get(quote, Decimal(0)) + q * p - fee
        o.filled += q
        o.state = "FILLED" if o.filled == o.quantity else "PARTIALLY_FILLED"
        self.fills[fill_id] = signature
        self.clock = at
        self.events.append(
            {
                "type": "FILL",
                "order": order_id,
                "fill_id": fill_id,
                "quantity": str(q),
                "price": str(p),
                "fee_quote": str(fee),
                "at": at,
            }
        )
        return True

    def cancel(self, order_id: str, *, at: int) -> None:
        self._time(at)
        o = self.orders[order_id]
        if o.state not in {"OPEN", "PARTIALLY_FILLED"}:
            raise ValueError("Order already terminal")
        key, release = self._reservation(o, o.quantity - o.filled)
        self.reserved[key] -= release
        o.state = "CANCELED"
        self.clock = at
        self.events.append({"type": "CANCEL", "order": order_id, "at": at})

    def snapshot(self) -> dict:
        return {
            "synthetic": True,
            "clock": self.clock,
            "accounts": [
                {
                    "venue": k[0],
                    "asset": k[1],
                    "balance": str(v),
                    "reserved": str(self.reserved.get(k, Decimal(0))),
                    "free": str(self.free(*k)),
                }
                for k, v in sorted(self.balances.items())
            ],
            "orders": {
                k: {
                    "state": v.state,
                    "filled": str(v.filled),
                    "remaining": str(v.quantity - v.filled),
                }
                for k, v in self.orders.items()
            },
            "events": list(self.events),
            "fill_model": "explicit scenario events; no queue, probability or market impact claim",
        }
