"""Offline CLI: python -m GarimpoInvestimentos.research --help."""

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from GarimpoInvestimentos.durable_io import strict_json_loads

from .factors import analyze_panel
from .registry import RunStore, encoded
from .simulation import ScenarioLedger, SpotContract
from .universe import Rule, select_universe
from .validation import LabelInterval, walk_forward


def code_version() -> str:
    source = b"".join(
        p.name.encode() + p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py"))
    )
    return hashlib.sha256(source + version("predictor-core").encode()).hexdigest()


def evaluate(config: dict) -> dict:
    """Compose independent diagnostics; no automatic strategy or capital activation."""
    if not config or set(config) - {"panel", "universe", "validation", "scenario"}:
        raise ValueError("Specify panel, universe, validation or scenario; unknown keys rejected")
    results = {}
    if "panel" in config:
        p = config["panel"]
        results["factors"] = analyze_panel(
            p["rows"], quantiles=p.get("quantiles", 5), group_adjust=p.get("group_adjust", False)
        )
    if "universe" in config:
        u = config["universe"]
        results["universe"] = select_universe(
            u["rows"],
            [Rule(**r) for r in u["rules"]],
            cutoff=u["cutoff"],
            sort_field=u.get("sort_field"),
            limit=u.get("limit"),
        )
    if "validation" in config:
        v = config["validation"]
        results["splits"] = walk_forward(
            [LabelInterval(**r) for r in v["labels"]],
            [tuple(w) for w in v["windows"]],
            gap=v.get("gap", 0),
        )
    if "scenario" in config:
        s = config["scenario"]
        balances = {(r["venue"], r["asset"]): r["amount"] for r in s["balances"]}
        if len(balances) != len(s["balances"]):
            raise ValueError("Duplicate opening balance")
        ledger = ScenarioLedger(balances, synthetic=s["synthetic"])
        contracts = {k: SpotContract(**v) for k, v in s["contracts"].items()}
        for raw in s["events"]:
            event = dict(raw)
            kind = event.pop("type")
            if kind == "submit":
                event["contract"] = contracts[event["contract"]]
                ledger.submit(**event)
            elif kind == "fill":
                ledger.fill(**event)
            elif kind == "cancel":
                ledger.cancel(**event)
            else:
                raise ValueError("Unsupported scenario event")
        results["simulation"] = ledger.snapshot()
    return results


def demo_config() -> dict:
    return {
        "panel": {
            "quantiles": 2,
            "rows": [
                {"date": date, "asset": asset, "factor": i, "label": (i - 2) / 100}
                for date in [10, 20]
                for i, asset in enumerate(["A", "B", "C", "D"])
            ],
        },
        "universe": {
            "cutoff": 10,
            "sort_field": "volume",
            "limit": 2,
            "rows": [
                {
                    "instrument_id": "SIM:A/USD",
                    "known_at": 9,
                    "active": True,
                    "volume": 100,
                    "volume_unit": "USD",
                },
                {
                    "instrument_id": "SIM:B/USD",
                    "known_at": 11,
                    "active": True,
                    "volume": 200,
                    "volume_unit": "USD",
                },
            ],
            "rules": [{"field": "active", "operation": "eq", "value": True}],
        },
        "validation": {
            "labels": [{"start": i, "end": i + 2, "available": i + 3} for i in range(12)],
            "windows": [[6, 9], [9, 12]],
            "gap": 0,
        },
        "scenario": {
            "synthetic": True,
            "balances": [{"venue": "SIM", "asset": "USD", "amount": "1000"}],
            "contracts": {
                "a": {
                    "instrument_id": "SIM:A/USD",
                    "venue": "SIM",
                    "base": "A",
                    "quote": "USD",
                    "quantity_unit": "A",
                    "price_unit": "USD/A",
                    "settlement": "USD",
                }
            },
            "events": [
                {
                    "type": "submit",
                    "order_id": "one",
                    "contract": "a",
                    "side": "BUY",
                    "quantity": "2",
                    "limit": "100",
                    "at": 0,
                    "latency": 2,
                    "fee_rate": "0.001",
                },
                {
                    "type": "fill",
                    "fill_id": "f1",
                    "order_id": "one",
                    "quantity": "0.5",
                    "price": "99",
                    "at": 2,
                },
                {"type": "cancel", "order_id": "one", "at": 3},
            ],
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Offline research: factors, universe, splits, synthetic orders, immutable runs."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["demo", "run"]:
        p = commands.add_parser(name)
        p.add_argument("--store", required=True)
        p.add_argument("--run-id")
        if name == "run":
            p.add_argument("--input", required=True)
    for name in ["list", "verify", "compare"]:
        p = commands.add_parser(name)
        p.add_argument("--store", required=True)
        if name == "verify":
            p.add_argument("run_id")
        if name == "compare":
            p.add_argument("left")
            p.add_argument("right")
    args = parser.parse_args(argv)
    store = RunStore(args.store)
    if args.command in {"demo", "run"}:
        raw = encoded(demo_config()) if args.command == "demo" else Path(args.input).read_bytes()
        config = strict_json_loads(raw.decode("utf-8"))
        if not isinstance(config, dict):
            raise ValueError("Research config must be an object")
        results = evaluate(config)
        metrics = {
            "capability_outputs": len(results),
            "factor_dates": len(results.get("factors", {}).get("dates", [])),
            "folds": len(results.get("splits", [])),
            "economic_validation": False,
        }
        path = store.create(
            config,
            metrics,
            artifacts={"results": results},
            inputs={"config": hashlib.sha256(raw).hexdigest()},
            code_version=code_version(),
            run_id=args.run_id,
        )
        output = {"run": str(path), "metrics": metrics}
    elif args.command == "list":
        output = store.list_runs()
    elif args.command == "verify":
        output = store.verify(args.run_id)
    else:
        output = store.compare(args.left, args.right)
    print(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
