"""Cross-sectional diagnostics; input labels are supplied, never downloaded or inferred."""

from collections import defaultdict
from math import floor, fsum, isfinite

from predictor_core.measurement.stats import spearman


def finite(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError("Expected finite numeric observation")
    return float(value)


def analyze_panel(rows: list[dict], *, quantiles: int = 5, group_adjust: bool = False) -> dict:
    """IC, tied-score quantiles, equal-weight label means and membership turnover.

    Quantiles use average ranks: ties stay together and bins may be empty. Turnover
    is entrants/current members, matching Alphalens semantics, not traded notional.
    Group adjustment demeans labels within date/group before IC and quantile means.
    Dates are integer instants on one caller-declared clock; no PIT claim is made.
    """
    if type(quantiles) is not int or quantiles < 2:
        raise ValueError("At least two quantiles required")
    dates: dict[int, list[dict]] = defaultdict(list)
    seen = set()
    for row in rows:
        date, asset = row["date"], row["asset"]
        if type(date) is not int or not isinstance(asset, str) or not asset:
            raise ValueError("Integer date and nonempty asset required")
        if (date, asset) in seen:
            raise ValueError("Duplicate date/asset")
        seen.add((date, asset))
        if group_adjust and (not isinstance(row.get("group"), str) or not row["group"]):
            raise ValueError("Explicit group required")
        dates[date].append({**row, "factor": finite(row["factor"]), "label": finite(row["label"])})
    output = []
    previous: dict[int, set[str]] | None = None
    for date, values in sorted(dates.items()):
        values.sort(key=lambda r: r["asset"])
        labels = [r["label"] for r in values]
        if group_adjust:
            groups: dict[str, list[float]] = defaultdict(list)
            for row in values:
                groups[row["group"]].append(row["label"])
            labels = [
                r["label"] - fsum(groups[r["group"]]) / len(groups[r["group"]]) for r in values
            ]
        order = sorted(range(len(values)), key=lambda i: values[i]["factor"])
        membership: dict[int, set[str]] = {q: set() for q in range(1, quantiles + 1)}
        buckets: dict[int, list[float]] = defaultdict(list)
        start = 0
        while start < len(order):
            end = start + 1
            while (
                end < len(order) and values[order[end]]["factor"] == values[order[start]]["factor"]
            ):
                end += 1
            q = min(quantiles, 1 + floor(((start + end - 1) / 2) * quantiles / len(order)))
            for i in order[start:end]:
                membership[q].add(values[i]["asset"])
                buckets[q].append(labels[i])
            start = end
        output.append(
            {
                "date": date,
                "n": len(values),
                "rank_ic": spearman([r["factor"] for r in values], labels),
                "quantiles": {
                    str(q): {
                        "members": sorted(members),
                        "mean_label": fsum(buckets[q]) / len(buckets[q]) if members else None,
                        "turnover": len(members - previous[q]) / len(members)
                        if previous is not None and members
                        else None,
                    }
                    for q, members in membership.items()
                },
            }
        )
        previous = membership
    return {
        "dates": output,
        "group_adjust": group_adjust,
        "quantile_policy": "average_rank_ties_together",
        "economic_validation": False,
        "label_contract": "caller supplied; equal-weight descriptive means, no costs",
    }


def residualize(values: list[float], exposures: list[list[float]]) -> list[float]:
    """OLS residual with intercept. Requires the existing science extra (NumPy)."""
    import numpy as np

    y = np.asarray([finite(v) for v in values], dtype=float)
    x = np.asarray([[finite(v) for v in row] for row in exposures], dtype=float)
    if x.ndim != 2 or x.shape[0] != len(y) or len(y) <= x.shape[1] + 1:
        raise ValueError("More observations than coefficients required")
    design = np.column_stack((np.ones(len(y)), x))
    if np.linalg.matrix_rank(design) != design.shape[1]:
        raise ValueError("Collinear exposures")
    beta, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    return (y - design @ beta).tolist()
