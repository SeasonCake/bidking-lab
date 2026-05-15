"""User-facing observation dataclasses + brute-force candidate enumeration.

This module is the bridge between *what the player types into the UI* and
*what the inference engine consumes*. It deliberately keeps the data
model flat and dataclass-shaped so that a future Streamlit / form UI
can bind to fields directly.

Field tiers (from the 2026-05-15 design session):

* **Required** in all modes: ``warehouse_total_cells``, ``red``
  ``value_range`` (red variance is too high to skip).
* **Required for Ethan** but optional for Aisha: blue/white-green
  ``total_cells`` (Ethan scans quickly; Aisha makes you count outlines
  by hand). Ethan also sees huge items in every quality; Aisha can
  only see *purple* huge items (the rest she has to guess).
* **Always optional**: ``count``, ``avg_cells``, ``value_sum`` — these
  come from tool readings the player may or may not have used.

Huge-count input is a **band**, not a single integer: the player picks
``"1"``, ``"2-3"``, or ``"4+"`` from a dropdown. The engine enumerates
within the band. Each quality has a canonical huge-item area:

* ``4`` (紫): 4×4 = 16 cells (eg 翡翠屏风, 防弹衣, 雷达, 毯子, 单兵外骨骼)
* ``5`` (金): 6×3 = 18 cells (only 单人郊游快艇)
* ``6`` (红): 4×4 = 16 cells (翡翠屏风, 红木屏风, 碳纤维车壳, 黑曜石屏风, ...)

The brute-force candidate enumeration walks ``(total_cells, count)``
integer pairs and filters by every constraint the player provided.
Output is ranked top-K by a composite score combining the cells-side
display-rule match and the value-side prior fit.
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

HugeBand = Literal["none", "1", "2-3", "4+"]
"""Discrete buckets the UI offers for huge-item count input.

The wide ``"4+"`` bucket is bounded at 7 in the enumerator (no real
map has more than ~10 large items across all qualities combined).
"""

HUGE_BAND_RANGE: dict[str, tuple[int, int]] = {
    "none": (0, 0),
    "1":    (1, 1),
    "2-3":  (2, 3),
    "4+":   (4, 7),
}

HUGE_CELLS_PER_QUALITY: dict[int, int] = {
    4: 16,   # 紫色巨物: 4×4 (e.g., 翡翠屏风, 防弹衣, 雷达, 单兵外骨骼)
    5: 18,   # 金色巨物: 6×3 only (单人郊游快艇)
    6: 16,   # 红色巨物: 4×4 (e.g., 翡翠屏风, 红木屏风, 碳纤维车壳)
}


def aisha_can_observe_huge(quality: int) -> bool:
    """Aisha sees outlines only for the purple bucket; for gold/red she guesses.

    This is the central asymmetry between the two heroes' observation
    forms: the UI should grey-out non-purple huge inputs in Aisha mode.
    """
    return quality == 4


# --- Standard tool loadouts (Phase 2 will refine; here for UI defaults) ---

# 伊森 standard kit (5 slots, mostly white-green + 1 gold):
#   普品扫描   (cheap)   → white-green total cells
#   良品扫描   (cheap)   → blue total cells
#   优品均格   (cheap)   → purple avg cells
#   优品估价   (cheap)   → purple value sum
#   珍品估价 OR 珍品扫描 (gold) → red value sum / red total cells
ETHAN_DEFAULT_LOADOUT: tuple[str, ...] = (
    "普品扫描",
    "良品扫描",
    "优品均格",
    "优品估价",
    "珍品估价",   # gold-tier; swap to 珍品扫描 for cells-side bias
)

# 艾莎 standard kit (4 slots; she prefers value tools because outline
# already gives her cells-side intuition):
#   珍品估价     (gold)  → red value sum (high impact, cheaper than scan)
#   抽检一/抽检二 (low)   → exact reveals of 1-2 items
#   宝光四鉴      (mid)  → 4 random qualities
#   总仓储空间    (gold) → total cells (or 全库透视 for full layout)
AISHA_DEFAULT_LOADOUT: tuple[str, ...] = (
    "珍品估价",
    "抽检二",
    "宝光四鉴",
    "总仓储空间",
)


@dataclass
class QualityBucketObs:
    """Everything the player knows about one quality bucket.

    All fields are optional at the dataclass level; the inference engine
    will raise if a required field (per the hero mode) is missing.

    Huge-item input is a **band** (``"none"`` / ``"1"`` / ``"2-3"`` /
    ``"4+"``). The engine enumerates within the band and assumes the
    canonical huge-item area for the quality (16 cells for purple/red,
    18 cells for gold) unless the player overrides via
    ``huge_cells_override``.
    """

    quality: int   # 1=白 … 6=红
    avg_cells: Reading | None = None
    total_cells: int | None = None        # exact, from scan tool or map
    total_cells_approx: int | None = None # player estimate, soft prior only
    count: int | None = None              # X品存量
    value_sum: int | None = None          # X品估价 silver
    value_range: tuple[int, int] | None = None
    huge_band: HugeBand = "none"
    huge_cells_override: int = 0          # if set, beats the per-quality default

    def huge_count_range(self) -> tuple[int, int]:
        """Min and max huge-item count from the band."""
        return HUGE_BAND_RANGE[self.huge_band]

    def huge_cells_per_item(self) -> int:
        """Cells consumed by one huge item in this quality (UI-side spec)."""
        if self.huge_cells_override:
            return self.huge_cells_override
        return HUGE_CELLS_PER_QUALITY.get(self.quality, 16)

    def min_huge_cells(self) -> int:
        return self.huge_count_range()[0] * self.huge_cells_per_item()

    def max_huge_cells(self) -> int:
        return self.huge_count_range()[1] * self.huge_cells_per_item()


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
    # Aisha cannot observe huge items in gold/red — if the player set a
    # non-"none" band for those qualities in Aisha mode they likely
    # confused herself with Ethan; warn rather than error.
    if session.hero == "aisha":
        for q in (5, 6):
            b = session.buckets.get(q)
            if b is not None and b.huge_band != "none":
                issues.append(
                    f"quality {q} huge_band: Aisha cannot observe huge "
                    f"items for non-purple quality; treat as guess"
                )
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
    huge_min, huge_max = bucket.huge_count_range()
    huge_per_item = bucket.huge_cells_per_item()

    base: list[tuple[int, int]]
    if bucket.avg_cells is not None:
        # Display rule already filters tightly; pull candidates from there.
        base = enumerate_candidates(
            bucket.avg_cells,
            max_count=max_count,
            max_total_cells=min(capacity, 252),
        )
    else:
        # No avg reading → enumerate everything within budget. Floor the
        # count at max(1, huge_min); floor the cells at huge_min cells.
        min_cells_floor = huge_min * huge_per_item
        base = [
            (tc, c)
            for c in range(max(1, huge_min), max_count + 1)
            for tc in range(min_cells_floor, capacity + 1)
        ]

    out: list[BucketCandidate] = []
    for total_cells, count in base:
        if bucket.total_cells is not None and total_cells != bucket.total_cells:
            continue
        if bucket.count is not None and count != bucket.count:
            continue
        if total_cells > capacity:
            continue

        # Huge-band constraint: there must exist an integer ``h`` in
        # [huge_min, huge_max] such that ``h <= count`` and
        # ``h * huge_per_item <= total_cells``. Otherwise the candidate
        # is incompatible with the player-reported huge band.
        h_lo = huge_min
        h_hi = min(huge_max, count, total_cells // max(1, huge_per_item))
        if h_hi < h_lo:
            continue
        # Pick the value of h that minimizes value-side error (the
        # engine doesn't need to commit to a specific h here; the band
        # is just a hard filter and a soft prior on huge cells).
        huge_cells = h_lo * huge_per_item

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

        if bucket.value_sum is not None:
            implied_cells = estimate_total_cells(
                bucket.quality,
                bucket.value_sum,
                huge_cells=huge_cells,
            )
            cells_score = abs(total_cells - implied_cells) / max(1, total_cells)
        else:
            cells_score = 0.0

        # Composite: 70% value-side fit + 30% cells-side fit, then a
        # small Occam penalty on count (fewer items more plausible at
        # equal per-cell value).
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
    "HugeBand",
    "HUGE_BAND_RANGE",
    "HUGE_CELLS_PER_QUALITY",
    "ETHAN_DEFAULT_LOADOUT",
    "AISHA_DEFAULT_LOADOUT",
    "aisha_can_observe_huge",
    "QualityBucketObs",
    "SessionObs",
    "BucketCandidate",
    "candidates_for_bucket",
    "top_k_for_session",
)
