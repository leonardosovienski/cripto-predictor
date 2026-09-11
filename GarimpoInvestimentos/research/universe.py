"""Composable, explainable filters over supplied versioned instrument observations."""

from dataclasses import dataclass

from .factors import finite


@dataclass(frozen=True)
class Rule:
    field: str
    operation: str
    value: object

    def __post_init__(self):
        if not self.field or self.operation not in {"eq", "min", "max", "not_in"}:
            raise ValueError("Unsupported universe rule")
        if self.operation in {"min", "max"}:
            finite(self.value)
        if self.operation == "not_in" and not isinstance(self.value, (list, tuple, set)):
            raise ValueError("not_in requires explicit values")


def select_universe(
    rows: list[dict],
    rules: list[Rule],
    *,
    cutoff: int,
    sort_field: str | None = None,
    limit: int | None = None,
) -> dict:
    """Latest received version per explicit instrument_id, then ordered filters.

    Missing classification/units stay missing. Inactive latest versions are not
    replaced by older active ones. Acquisition time is not listing/publication proof.
    Sort metrics must have one explicit shared unit; USD and USDT never alias.
    """
    if type(cutoff) is not int or (limit is not None and (type(limit) is not int or limit < 0)):
        raise ValueError("Invalid cutoff or limit")
    latest: dict[str, dict] = {}
    future = 0
    for row in rows:
        ident, known = row.get("instrument_id"), row.get("known_at")
        if not isinstance(ident, str) or not ident or type(known) is not int:
            raise ValueError("Explicit instrument identity and receipt time required")
        if known > cutoff:
            future += 1
            continue
        prior = latest.get(ident)
        if prior is not None and known == prior["known_at"] and row != prior:
            raise ValueError("Ambiguous same-time versions")
        if prior is None or known > prior["known_at"]:
            latest[ident] = dict(row)
    rejected: dict[str, str] = {}
    survivors = []
    for ident, row in sorted(latest.items()):
        reason = None
        for rule in rules:
            value = row.get(rule.field)
            if value is None:
                reason = "UNKNOWN:" + rule.field
                break
            if rule.operation in {"min", "max"}:
                value = finite(value)
                threshold = finite(rule.value)
                passed = value >= threshold if rule.operation == "min" else value <= threshold
            elif rule.operation == "eq":
                passed = type(value) is type(rule.value) and value == rule.value
            else:
                passed = value not in rule.value  # type: ignore[operator]
            if not passed:
                reason = "FILTER:" + rule.field
                break
        if reason:
            rejected[ident] = reason
        else:
            survivors.append(row)
    if sort_field:
        units = set()
        for row in survivors:
            finite(row.get(sort_field))
            unit = row.get(sort_field + "_unit")
            if not isinstance(unit, str) or not unit:
                raise ValueError("Explicit sorting unit required")
            units.add(unit)
        if len(units) > 1:
            raise ValueError("Incomparable ranking units")
        survivors.sort(key=lambda r: (-r[sort_field], r["instrument_id"]))
    if limit is not None:
        for row in survivors[limit:]:
            rejected[row["instrument_id"]] = "LIMIT"
        survivors = survivors[:limit]
    return {
        "selected": [r["instrument_id"] for r in survivors],
        "rejected": rejected,
        "future_versions_excluded": future,
        "cutoff": cutoff,
        "historical_universe_certified": False,
    }
