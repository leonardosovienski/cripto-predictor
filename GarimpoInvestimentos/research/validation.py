"""Reusable interval-aware walk-forward splits; no changes to frozen trial designs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LabelInterval:
    start: int
    end: int
    available: int

    def __post_init__(self):
        if any(type(v) is not int for v in (self.start, self.end, self.available)):
            raise ValueError("Integer instants on one declared clock required")
        if self.end < self.start or self.available < self.end:
            raise ValueError("Invalid label interval/availability")


def walk_forward(
    labels: list[LabelInterval], windows: list[tuple[int, int]], *, gap: int = 0
) -> list[dict]:
    """Closed label intervals, half-open test windows; end < test_start-gap.

    Training labels must also have become available strictly before test_start.
    Gap is time in the declared unit, not row count. Future training is never used,
    so post-test embargo is not applicable to this forward-only splitter.
    """
    if type(gap) is not int or gap < 0:
        raise ValueError("Nonnegative time gap required")
    output = []
    previous_end = None
    for start, end in windows:
        if type(start) is not int or type(end) is not int or start >= end:
            raise ValueError("Invalid test window")
        if previous_end is not None and start < previous_end:
            raise ValueError("Test windows must be ordered and disjoint")
        previous_end = end
        train, test, excluded = [], [], {}
        for i, label in enumerate(labels):
            if start <= label.start < end:
                test.append(i)
            elif label.start >= end:
                excluded[str(i)] = "FUTURE"
            elif label.end >= start - gap:
                excluded[str(i)] = "LABEL_OVERLAP_OR_GAP"
            elif label.available >= start:
                excluded[str(i)] = "LABEL_NOT_AVAILABLE"
            else:
                train.append(i)
        output.append(
            {"start": start, "end": end, "train": train, "test": test, "excluded": excluded}
        )
    return output
