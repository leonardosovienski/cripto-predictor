"""Conditional sample-size planning for positive net return; no outside benchmark."""

import argparse
import json
import math
from pathlib import Path


def planning_grid():
    rows = []
    for annual_net in (0.01, 0.05, 0.10, 0.20):
        weekly_log = math.log1p(annual_net) / 52
        for weekly_sd in (0.01, 0.03, 0.05):
            for dependence in (1, 4):
                weeks = math.ceil(((1.96 + 0.842) * weekly_sd / weekly_log) ** 2) * dependence
                rows.append(
                    {
                        "annual_net_return_scenario": annual_net,
                        "weekly_log_sd_assumed": weekly_sd,
                        "dependence_multiplier_assumed": dependence,
                        "weeks_normal_design": weeks,
                    }
                )
    return {
        "objective": "ABSOLUTE_NET_PROFIT",
        "external_investment_comparison": False,
        "null_net_return": 0,
        "minimum_profit_requested_by_user": None,
        "grid": rows,
        "limitation": "Planning assumptions only, not forecasts, user profit targets, a calibrated horizon or a formal attestation. Arbitrarily small positive net return has no fixed finite evidence horizon. Twelve observation windows test operation; they do not establish profitability automatically.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(planning_grid(), indent=2), encoding="utf-8")
    print("Absolute net-profit planning saved; no external benchmark or market-performance trial.")


if __name__ == "__main__":
    main()
