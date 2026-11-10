"""Human-friendly route summaries ("I 30, I 57") from per-step road names."""

from __future__ import annotations

import re
from collections.abc import Iterable

MAX_SUMMARY_ROADS = 3
DIRECTION_SUFFIX = re.compile(r"\s+(North|South|East|West|N|S|E|W)$", re.IGNORECASE)


def summarise_road_names(named_lengths: Iterable[tuple[str, float]]) -> str:
    """The roads carrying the most distance, listed in driving order.

    ``named_lengths`` is ``(road name, length)`` per step; multi-ref names such as
    ``"I 30; US 67"`` are reduced to their first reference and direction suffixes
    (``"I 30 East"``) are dropped so both directions read the same.
    """
    totals: dict[str, float] = {}
    for raw_name, length in named_lengths:
        name = DIRECTION_SUFFIX.sub("", raw_name.split(";")[0].strip())
        if name:
            totals[name] = totals.get(name, 0.0) + length
    top = sorted(totals, key=totals.__getitem__, reverse=True)[:MAX_SUMMARY_ROADS]
    in_order = [name for name in totals if name in top]  # dicts keep first-seen order
    return ", ".join(in_order)
