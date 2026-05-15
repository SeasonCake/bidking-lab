"""R2 snipe-bid recommendation for Ethan players.

When an Ethan player has scanned the low-tier shelves (white+green and
blue) and either sees or estimates the cabinet's total cell count, the
mid-rounds (R2 in particular) offer a tactical window to "snipe" the
cabinet — submit one aggressive bid before opponents start padding.
This module computes a UI-surfaceable recommendation for that scenario.

Hard gating (returns ``None`` if any fail):

* ``session.hero == "ethan"`` — only Ethan can fully observe low-tier cells
* ``warehouse_total_cells >= 120`` — only big warehouses justify the snipe
  premium (small warehouses have too little upside to overpay)
* ``q=1`` (white+green combined via 普品扫描) total_cells is known
* ``q=3`` (blue via 良品扫描) total_cells is known

Model:

1. Sample ``n_trials`` ground-truth sessions for the map.
2. Filter to sessions whose warehouse_total_cells matches the player's
   observation within ``warehouse_tolerance`` cells (default ±8).
3. From the filtered distribution, compute the 50th/75th/90th percentile
   of *total* session value.
4. Recommended bid range:

   * ``safe_floor`` = 50th percentile × ``safe_floor_ratio`` (default 0.70)
   * ``expected``   = 50th percentile (median session value, conditional)
   * ``snipe_max``  = 75th percentile × ``snipe_premium`` (default 1.15)

The "high-risk premium" is baked into the snipe_max being a quantile
*plus* a multiplier — opponents at R2 typically bid near the median, so
exceeding the 75th-percentile point gives a real edge while staying
below ``snipe_max`` keeps the worst-case loss bounded.

The returned ``rationale`` string is human-readable and can be dropped
verbatim into a Streamlit UI tooltip.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.inference.ground_truth import sample_session_truth
from bidking_lab.inference.observation import SessionObs


@dataclass(frozen=True)
class SnipeRecommendation:
    """R2 snipe-bid suggestion bundle."""

    map_id: int
    map_name: str
    warehouse_total_cells: int
    low_tier_cells_observed: int

    n_matching_samples: int           # how many MC sessions matched the warehouse filter
    expected_value: int               # median total session value (conditional MC)
    p25_value: int                    # 25th percentile (downside reference)
    p75_value: int                    # 75th percentile (snipe upside)
    p90_value: int                    # 90th percentile (extreme upside, not used in recommendation)

    safe_floor_bid: int               # below this is a no-brainer keep bid
    snipe_max_bid: int                # above this is overpaying for the upside
    rationale: str                    # human-readable explanation

    def as_ui_tooltip(self) -> str:
        """One-line summary suitable for a UI badge."""
        return (
            f"\u9ad8\u98ce\u9669\u64cd\u4f5c: \u53ef\u79d2\u4ed3, "
            f"\u63a8\u8350\u4ef7\u683c {self.snipe_max_bid:,} \u4ee5\u5185 "
            f"(\u9884\u671f\u4ed3\u4ef7 \u4e2d\u4f4d\u6570 {self.expected_value:,})"
        )


def compute_snipe_recommendation(
    session: SessionObs,
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    n_trials: int = 2000,
    warehouse_tolerance: int = 8,
    min_matching_samples: int = 30,
    safe_floor_ratio: float = 0.70,
    snipe_premium: float = 1.15,
    min_warehouse_cells: int = 120,
    rng: np.random.Generator | None = None,
) -> SnipeRecommendation | None:
    """Conditional Monte Carlo over the map's drop pool, gated on R2-Ethan
    information state. See module docstring for the model.

    Returns ``None`` if any of the hard preconditions fail or if too few
    MC samples match the observed warehouse size (in which case the
    recommendation would be too noisy to surface).
    """
    if session.hero != "ethan":
        return None
    wh = session.warehouse_total_cells
    if wh is None or wh < min_warehouse_cells:
        return None

    wg = session.buckets.get(1)
    blue = session.buckets.get(3)
    if wg is None or wg.total_cells is None:
        return None
    if blue is None or blue.total_cells is None:
        return None
    low_cells = wg.total_cells + blue.total_cells
    if session.map_id not in maps:
        return None

    rng = rng or np.random.default_rng()
    values: list[int] = []
    for _ in range(n_trials):
        truth = sample_session_truth(
            session.map_id, maps=maps, drops=drops, items=items, rng=rng,
        )
        if abs(truth.warehouse_total_cells - wh) <= warehouse_tolerance:
            values.append(truth.total_value())

    if len(values) < min_matching_samples:
        # Too noisy — bail rather than mislead the UI.
        return None

    arr = np.asarray(values, dtype=np.int64)
    p25 = int(np.percentile(arr, 25))
    p50 = int(np.percentile(arr, 50))
    p75 = int(np.percentile(arr, 75))
    p90 = int(np.percentile(arr, 90))

    safe_floor = int(p50 * safe_floor_ratio)
    snipe_max = int(p75 * snipe_premium)

    rationale = (
        f"\u4ed3\u5e93 {wh} \u683c\uff0c\u4f4e\u54c1 {low_cells} \u683c\u5df2\u626b "
        f"(\u767d\u7eff {wg.total_cells} + \u84dd {blue.total_cells})\u3002\n"
        f"\u5728 {len(values)} \u4e2a\u540c\u4f53\u91cf\u4ed3\u5e93\u7684 MC \u91c7\u6837\u4e2d\uff0c"
        f"\u603b\u4ed3\u4ef7 \u4e2d\u4f4d\u6570 = {p50:,}\u3001"
        f"P75 = {p75:,}\u3001P90 = {p90:,} \u94f6\u5e01\u3002\n"
        f"R2 \u662f\u79d2\u4ed3\u9ec4\u91d1\u7a97\u53e3\uff08\u5bf9\u624b\u8fd8\u672a\u9501\u4ef7\uff09\uff0c"
        f"\u63a8\u8350\u51fa\u4ef7\u533a\u95f4\uff1a"
        f"\u8d77\u7801 {safe_floor:,} \u2192 \u79d2\u4ed3\u9876 {snipe_max:,} \u94f6\u5e01\u3002\n"
        f"\u9876\u4ef7\u91c7\u7528 P75 \u00d7 {snipe_premium:.2f} \u7684\u9ad8\u98ce\u9669\u6e22\u4ef7\uff1a"
        f"\u4f4e\u4e8e P75 \u662f\u591a\u6570\u5bf9\u624b\u7684\u51fa\u4ef7\u9ed8\u8ba4\u533a\uff0c\u8d85\u8fc7 = \u62d3\u5bbd\u80dc\u9762\u3002"
    )

    return SnipeRecommendation(
        map_id=session.map_id,
        map_name=maps[session.map_id].name,
        warehouse_total_cells=wh,
        low_tier_cells_observed=low_cells,
        n_matching_samples=len(values),
        expected_value=p50,
        p25_value=p25,
        p75_value=p75,
        p90_value=p90,
        safe_floor_bid=safe_floor,
        snipe_max_bid=snipe_max,
        rationale=rationale,
    )


__all__ = (
    "SnipeRecommendation",
    "compute_snipe_recommendation",
)
