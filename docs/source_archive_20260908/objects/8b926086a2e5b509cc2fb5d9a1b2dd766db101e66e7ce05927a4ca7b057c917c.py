"""Match net BTC after assumed spot commission using saved public quotes only."""

import argparse
import gzip
import json
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path

from scripts.basis_data import sha, write
from scripts.diagnose_btc_execution import filters, walk

D = lambda v: Decimal(str(v))


def net_hedge_plan(spot: dict, future: dict, sf: dict, ff: dict, precision: int) -> dict:
    fee = D("0.001")
    spot_step, future_step = D(sf["step"]), D(ff["step"])
    quantum = D(10) ** -precision
    budget = D(1250)
    ask = D(spot["asks"][0][0])
    q = (budget * (1 - fee) / ask / future_step).to_integral_value(
        rounding=ROUND_FLOOR
    ) * future_step
    for _ in range(1000):
        if q <= 0:
            raise ValueError("No affordable hedge after current quantity constraints")
        gross = (q / (1 - fee) / spot_step).to_integral_value(rounding=ROUND_CEILING) * spot_step
        commission = (gross * fee / quantum).to_integral_value(rounding=ROUND_CEILING) * quantum
        if gross - commission < q:
            gross += spot_step
            commission = (gross * fee / quantum).to_integral_value(rounding=ROUND_CEILING) * quantum
        buy = D(walk(spot["asks"], float(gross), True))
        spot_outlay = gross * buy
        if spot_outlay <= budget:
            break
        q -= future_step
    else:
        raise ValueError("Quantity sizing bound exceeded")
    sell = D(walk(future["bids"], float(q), False))
    for f, quantity, price in ((sf, gross, buy), (ff, q, sell)):
        if (
            f["status"] != "TRADING"
            or not D(f["min_qty"]) <= quantity <= D(f["max_qty"])
            or quantity * price < D(f["min_notional"])
        ):
            raise ValueError("Current lot or minimum constraint")
    received = gross - commission
    dust = received - q
    if not 0 <= dust < spot_step + quantum:
        raise ValueError("Unexpected unmatched net quantity")
    future_fee = q * sell * D("0.0005")
    reserve = D(5000) - spot_outlay - future_fee
    smid = (D(spot["bids"][0][0]) + D(spot["asks"][0][0])) / 2
    fmid = (D(future["bids"][0][0]) + D(future["asks"][0][0])) / 2
    stress = fmid * D("1.3")
    values = {
        "gross_spot_buy_btc": gross,
        "spot_commission_btc_assumed": commission,
        "net_received_btc": received,
        "future_short_btc": q,
        "unhedged_dust_btc": dust,
        "dust_marked_usdt": dust * smid,
        "spot_outlay_usdt": spot_outlay,
        "future_entry_fee_usdt_assumed": future_fee,
        "cash_reserve_usdt": reserve,
        "margin_surplus_30pct_mid_jump_usdt": reserve
        + q * (sell - stress)
        - D("0.015") * q * stress,
    }
    return {
        **{k: str(v) for k, v in values.items()},
        "spot_fee_assumption_bps": 10,
        "future_fee_assumption_bps": 5,
        "spot_fee_asset_assumption": "BTC",
        "commission_rounding": "Conservative upward rounding to public baseCommissionPrecision",
        "actual_account_commission_asset_and_rate": "UNKNOWN",
        "orders_sent": 0,
        "execution_certified": False,
    }


def replay(directory: Path, output: Path) -> None:
    record = json.loads((directory / "diagnostic.json").read_text(encoding="utf-8"))
    sources = {}
    for meta in record["sources"]:
        raw = gzip.decompress((directory / "raw" / (meta["name"] + ".bin.gz")).read_bytes())
        if sha(raw) != meta["sha256"]:
            raise ValueError("Changed public diagnostic source")
        sources[meta["name"]] = json.loads(raw)
    sf, ff = filters(sources["spot_info"]), filters(sources["future_info"])
    symbol = next(s for s in sources["spot_info"]["symbols"] if s["symbol"] == "BTCUSDT")
    precision = int(symbol["baseCommissionPrecision"])
    rows = []
    for sample in record["snapshots"]:
        index = sample["index"]
        try:
            plan = net_hedge_plan(
                sources[f"spot_{index:02d}"], sources[f"future_{index:02d}"], sf, ff, precision
            )
            error = None
        except ValueError as exc:
            plan, error = None, str(exc)
        rows.append(
            {
                "snapshot_index": index,
                "transport_freshness_pass": sample["freshness_pass"],
                "plan": plan,
                "error": error,
            }
        )
    write(
        output,
        {
            "diagnostic_source_sha256": sha((directory / "diagnostic.json").read_bytes()),
            "source_code_sha256": sha(Path(__file__).read_bytes()),
            "historical_strategy_changed": False,
            "new_network_requests": 0,
            "orders_sent": 0,
            "plans": rows,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    replay(args.diagnostic, args.output)
