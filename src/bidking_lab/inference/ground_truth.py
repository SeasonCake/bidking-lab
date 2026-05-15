"""Sample one auction session with full ground-truth visibility.

The Phase 1A inference engine consumes *partial* observations (tool
readings + hero outlines) and produces top-K hypotheses for the unknown
warehouse contents. To evaluate that engine's accuracy we need
*ground-truth* sessions — sessions where we know exactly which items
landed in the cabinet, then synthetically apply only the readings the
player would have, then compare engine output against truth.

This module owns the ground-truth side of that loop. ``synth_readings``
owns the tool-reveal mapping, ``roi`` owns the leave-one-out ROI math.

Sampling reuses the same drop-pool flattening + per-item count
distribution as :mod:`bidking_lab.simulation.basic_mc` so that sampled
sessions are statistically identical to those in our existing MC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.inference.observation import HUGE_CELLS_PER_QUALITY
from bidking_lab.simulation.basic_mc import flatten_pool


def is_huge_item(item: Item) -> bool:
    """True iff ``item`` matches the canonical huge-band cell area for its quality.

    Only purple (q=4, 16 cells), gold (q=5, 18 cells), and red (q=6,
    16 cells) have huge-band semantics; other qualities always return
    False (no in-game "huge" concept for white/green/blue).
    """
    threshold = HUGE_CELLS_PER_QUALITY.get(item.quality)
    if threshold is None:
        return False
    return item.shape_w * item.shape_h >= threshold


@dataclass
class BucketTruth:
    """Ground-truth contents of one quality bucket in a sampled session."""

    quality: int
    count: int = 0
    total_cells: int = 0
    value_sum: int = 0
    huge_count: int = 0
    items: list[Item] = field(default_factory=list)


@dataclass
class SessionTruth:
    """Ground-truth contents of one full sampled session."""

    map_id: int
    map_name: str
    warehouse_total_cells: int
    buckets: dict[int, BucketTruth] = field(default_factory=dict)

    def bucket(self, quality: int) -> BucketTruth | None:
        return self.buckets.get(quality)

    def total_value(self) -> int:
        """Sum of value across all buckets — the headline ground-truth number."""
        return sum(b.value_sum for b in self.buckets.values())


def _resolve_sub_pool(
    bid_map: BidMap,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    rng: np.random.Generator,
):
    """Pick one sub-pool (anthology routing) and return its flattened form."""
    if not bid_map.sub_pool_weights:
        return flatten_pool(bid_map.drop_pool_id, drops, items)
    sub_pools = []
    weights = []
    for sub_map_id, w in bid_map.sub_pool_weights:
        sub_map = maps.get(sub_map_id)
        if sub_map is None:
            continue
        fp = flatten_pool(sub_map.drop_pool_id, drops, items)
        if not fp.item_ids:
            continue
        sub_pools.append(fp)
        weights.append(w)
    if not sub_pools:
        return flatten_pool(bid_map.drop_pool_id, drops, items)
    weights_arr = np.array(weights, dtype=np.float64)
    weights_arr = weights_arr / weights_arr.sum()
    idx = int(rng.choice(len(sub_pools), p=weights_arr))
    return sub_pools[idx]


def sample_session_truth(
    map_id: int,
    *,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    rng: np.random.Generator | None = None,
) -> SessionTruth:
    """Sample one ground-truth session for ``map_id``.

    Statistically equivalent to one trial of
    :func:`bidking_lab.simulation.bidding.simulate_session`, but exposes
    the actual sampled :class:`Item` objects (grouped by quality) so that
    downstream tooling can compute exact per-bucket truth.
    """
    if rng is None:
        rng = np.random.default_rng()
    bid_map = maps[map_id]
    fp = _resolve_sub_pool(bid_map, maps, drops, items, rng)

    probs = np.array(fp.probabilities, dtype=np.float64)
    if len(probs) == 0:
        return SessionTruth(
            map_id=map_id,
            map_name=bid_map.name,
            warehouse_total_cells=0,
            buckets={},
        )

    k_lo = bid_map.items_per_session_min
    k_hi = bid_map.items_per_session_max
    k = int(rng.integers(k_lo, k_hi + 1))
    sampled_idx = rng.choice(len(probs), size=k, replace=True, p=probs)

    n_min = np.array(fp.n_min, dtype=np.int64)
    n_max = np.array(fp.n_max, dtype=np.int64)
    counts = rng.integers(n_min[sampled_idx], n_max[sampled_idx] + 1)

    buckets: dict[int, BucketTruth] = {}
    for pool_i, cnt in zip(sampled_idx, counts):
        item = items[fp.item_ids[int(pool_i)]]
        area = item.shape_w * item.shape_h
        bucket = buckets.setdefault(item.quality, BucketTruth(quality=item.quality))
        for _ in range(int(cnt)):
            bucket.count += 1
            bucket.total_cells += area
            bucket.value_sum += item.value
            if is_huge_item(item):
                bucket.huge_count += 1
            bucket.items.append(item)

    warehouse_total = sum(b.total_cells for b in buckets.values())
    return SessionTruth(
        map_id=map_id,
        map_name=bid_map.name,
        warehouse_total_cells=warehouse_total,
        buckets=buckets,
    )


__all__ = (
    "BucketTruth",
    "SessionTruth",
    "is_huge_item",
    "sample_session_truth",
)
