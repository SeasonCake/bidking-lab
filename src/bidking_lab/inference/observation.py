"""User-facing observation dataclasses + brute-force candidate enumeration.

This module is the bridge between *what the player types into the UI* and
*what the inference engine consumes*. It deliberately keeps the data
model flat and dataclass-shaped so that a future Streamlit / form UI
can bind to fields directly.

Field tiers (from the 2026-05-15 design session):

* **Required** in all modes: ``warehouse_total_cells``, per-quality
  ``huge_count`` (the player can count huge cells off the cabinet),
  ``red`` ``value_range`` (red variance is too high to skip).
* **Required for Ethan** but optional for Aisha: blue/white-green
  ``total_cells`` (Ethan scans quickly; Aisha makes you count outlines
  by hand).
* **Always optional**: ``count``, ``avg_cells``, ``value_sum`` — these
  come from tool readings the player may or may not have used.

The brute-force candidate enumeration walks ``(total_cells, count)``
integer pairs and filters by every constraint the player provided.
Output is ranked top-K by a composite score combining the cells-side
display-rule match and the value-side prior fit (see
:func:`rank_candidates`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from bidking_lab.inference.display import (
    Reading,
    enumerate_candidates,
    filter_by_warehouse_size,
    is_compatible,
    parse_reading,
)
from bidking_lab.inference.quality_priors import (
    PER_CELL_VALUE_DEFAULT,
    estimate_total_cells,
    per_cell_value,
    value_consistency_score,
)

HeroMode = Literal["aisha", "ethan"]
"""Which hero the player has equipped; controls which fields are required."""


@dataclass
class QualityBucketObs:
    """Everything the player knows about one quality bucket.

    All fields are optional at the dataclass level; the inference engine
    will raise if a required field (per the hero mode) is missing.

    ``huge_count`` and ``huge_cells`` are paired: if the player counts
    1 four-by-four 屏风 in the red bucket, they set ``huge_count=1`` and
    ``huge_cells=16``. If they aren't sure of the exact area they can
    leave ``huge_cells=0`` and the engine assumes 16 cells per huge red.
    """

    quality: int   # 1=白 … 6=红
    avg_cells: Reading | None = None
    total_cells: int | None = None        # exact, from scan tool or map
    total_cells_approx: int | None = None # player estimate, used only as soft prior
    count: int | None = None              # X品存量
    value_sum: int | None = None          # X品估价 silver
    value_range: tuple[int, int] | None = None
    huge_count: int = 0
    huge_cells: int = 0                   # 0 → engine assumes 16 per huge item

    def assumed_huge_cells(self) -> int:
        """Cells attributed to huge items (uses 16 as fallback per-huge area)."""
        if self.huge_cells:
            return self.huge_cells
        return 16 * self.huge_count


@dataclass
class SessionObs:
    """All inputs for one auction session."""

    map_id: int
    hero: HeroMode
    warehouse_total_cells: int | None = None
    warehouse_total_cells_approx: int | None = None
    buckets: dict[int, QualityBucketObs] = field(default_factory=dict)

    def warehouse_capacity(self) -> int:
        """Best estimate of total cabinet cells."""
        if self.warehouse_total_cells is not None:
            return self.warehouse_total_cells
        if self.warehouse_total_cells_approx is not None:
            return self.warehouse_total_cells_approx
        return 159   # fallback: big shipwreck size


@dataclass(frozen=True)
class BucketCandidate:
    """One ``(total_cells, count)`` candidate for a quality bucket, with its rank score."""

    quality: int
    total_cells: int
    count: int
    avg_match: bool        # True iff candidate matches the avg_cells reading exactly
    value_score: float     # value_consistency_score (lower = better)
    cells_score: float     # |total_cells - estimate_from_value| / total_cells
    composite: float       # weighted sum used for ranking (lower = better)


def _check_required_fields(session: SessionObs) -> list[str]:
    """Return a list of human-readable missing-field warnings.

    Not raised — the engine still tries to return candidates, but the
    caller (a Streamlit UI) can surface these to ask the user to fill in.
    """
    issues: list[str] = []
    if session.warehouse_total_cells is None and session.warehouse_total_cells_approx is None:
        issues.append("warehouse_total_cells: required (exact or approximate)")
    red = session.buckets.get(6)
    if red and red.value_range is None and red.value_sum is None:
        issues.append("red.value_range: required (red variance too high)")
    if session.hero == "ethan":
        for q in (1, 2, 3):
            b = session.buckets.get(q)
            if b is not None and b.total_cells is None:
                issues.append(f"quality {q} total_cells: required in Ethan mode")
    return issues


def candidates_for_bucket(
    bucket: QualityBucketObs,
    *,
    warehouse_capacity: int,
    other_known_cells: int = 0,
    max_count: int = 50,
) -> list[BucketCandidate]:
    """Brute-force enumeration for one quality bucket.

    The enumeration is pruned at three levels:

    1. **Hard ceiling on total cells**: ``warehouse_capacity -
       other_known_cells`` (the budget remaining for this bucket).
    2. **Huge-cells floor**: ``total_cells >= huge_cells``,
       ``count >= huge_count``.
    3. **avg_cells reading**: if provided, only candidates matching the
       game-display rule survive.

    The output list is sorted ascending by composite score. The top-3
    are what the UI shows to the user.
    """
    capacity = max(0, warehouse_capacity - other_known_cells)
    huge_cells = bucket.assumed_huge_cells()
    huge_count = bucket.huge_count

    base: list[tuple[int, int]]
    if bucket.avg_cells is not None:
        # Display rule already filters tightly; pull candidates from there.
        base = enumerate_candidates(
            bucket.avg_cells,
            max_count=max_count,
            max_total_cells=min(capacity, 252),
        )
    else:
        # No avg reading → enumerate everything within budget.
        base = [
            (tc, c)
            for c in range(max(1, huge_count), max_count + 1)
            for tc in range(huge_cells, capacity + 1)
        ]

    # Apply explicit constraints
    out: list[BucketCandidate] = []
    for total_cells, count in base:
        if total_cells < huge_cells or count < huge_count:
            continue
        if bucket.total_cells is not None and total_cells != bucket.total_cells:
            continue
        if bucket.count is not None and count != bucket.count:
            continue
        if total_cells > capacity:
            continue

        avg_match = (
            bucket.avg_cells is None
            or is_compatible(bucket.avg_cells, total_cells, count)
        )
        value_score = value_consistency_score(
            bucket.quality,
            total_cells,
            value_sum=bucket.value_sum,
            value_range=bucket.value_range,
            huge_cells=huge_cells,
        )

        # cells_score: relative gap between candidate cells and
        # value-implied cells. If no value_sum is given this collapses to
        # 0 and ranking is by tie-breakers below.
        if bucket.value_sum is not None:
            implied_cells = estimate_total_cells(
                bucket.quality,
                bucket.value_sum,
                huge_cells=huge_cells,
            )
            cells_score = abs(total_cells - implied_cells) / max(1, total_cells)
        else:
            cells_score = 0.0

        # Composite: 70% value-side fit + 30% cells-side fit, then add a
        # small penalty for very large counts (Occam: fewer items is more
        # plausible at the same per-cell average).
        composite = 0.7 * value_score + 0.3 * cells_score + 0.001 * count

        out.append(
            BucketCandidate(
                quality=bucket.quality,
                total_cells=total_cells,
                count=count,
                avg_match=avg_match,
                value_score=value_score,
                cells_score=cells_score,
                composite=composite,
            )
        )

    out.sort(key=lambda c: c.composite)
    return out


def top_k_for_session(
    session: SessionObs,
    *,
    k: int = 3,
) -> dict[int, list[BucketCandidate]]:
    """Top-K candidates per quality bucket, processed in priority order.

    "Priority order" handles the huge-item-first cut: gold and red
    buckets are solved first (where the player likely flagged huge
    items), the chosen total-cells contributions are subtracted from
    the warehouse budget, then purple, then white-green/blue.

    This is intentional brute-force — typical session sizes (<= 252
    cells, <= 50 count per bucket) leave well under 10^4 candidate
    pairs per bucket, total wall time is sub-second on a laptop.
    """
    capacity = session.warehouse_capacity()
    other_known_cells = 0
    out: dict[int, list[BucketCandidate]] = {}

    for q in (6, 5, 4, 3, 2, 1):
        bucket = session.buckets.get(q)
        if bucket is None:
            continue
        cands = candidates_for_bucket(
            bucket,
            warehouse_capacity=capacity,
            other_known_cells=other_known_cells,
        )
        if not cands:
            out[q] = []
            continue
        out[q] = cands[:k]
        # Subtract the top-1 cells from the remaining budget for the
        # next, less-valuable quality (a coarse but effective greedy
        # approach).
        other_known_cells += cands[0].total_cells

    return out


__all__ = (
    "HeroMode",
    "QualityBucketObs",
    "SessionObs",
    "BucketCandidate",
    "candidates_for_bucket",
    "top_k_for_session",
)
