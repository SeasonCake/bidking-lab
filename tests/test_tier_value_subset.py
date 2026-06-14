from __future__ import annotations

from bidking_lab.inference.tier_value_subset import (
    TierPoolItem,
    enumerate_avg_value_combos,
    enumerate_exact_value_combos,
)


def test_exact_subset_finds_simple_combo() -> None:
    pool = [
        TierPoolItem(item_id=1, value=10_000, cells=4),
        TierPoolItem(item_id=2, value=20_000, cells=4),
        TierPoolItem(item_id=3, value=30_000, cells=4),
    ]
    stats = enumerate_exact_value_combos(pool, 30_000, max_count=2)
    assert (1, 4) in stats.unique_count_cells
    assert stats.elapsed_ms >= 0


def test_avg_value_expands_count_candidates() -> None:
    pool = [
        TierPoolItem(item_id=1, value=8_000, cells=1),
        TierPoolItem(item_id=2, value=12_000, cells=2),
        TierPoolItem(item_id=3, value=20_000, cells=4),
        TierPoolItem(item_id=4, value=32_000, cells=4),
    ]
    stats = enumerate_avg_value_combos(pool, 20_000.0, max_count=4, product_tolerance=0.51)
    assert (1, 4) in stats.unique_count_cells
