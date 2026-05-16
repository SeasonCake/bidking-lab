"""Tests for the inference observation dataclasses + brute-force engine."""

from __future__ import annotations

import pytest

from bidking_lab.inference.display import parse_reading
from bidking_lab.inference.observation import (
    AISHA_DEFAULT_LOADOUT,
    ETHAN_ALT_LOADOUT,
    ETHAN_DEFAULT_LOADOUT,
    HUGE_BAND_RANGE,
    HUGE_CELLS_PER_QUALITY,
    STANDARD_LOADOUTS,
    QualityBucketObs,
    SessionObs,
    aisha_can_observe_huge,
    candidates_for_bucket,
    top_k_for_session,
)


# --- Huge band metadata ---

def test_huge_band_ranges() -> None:
    assert HUGE_BAND_RANGE["none"] == (0, 0)
    assert HUGE_BAND_RANGE["1"] == (1, 1)
    assert HUGE_BAND_RANGE["2-3"] == (2, 3)
    assert HUGE_BAND_RANGE["4+"][0] == 4
    assert HUGE_BAND_RANGE["4+"][1] >= 4


def test_huge_cells_per_quality() -> None:
    """Purple uses a relaxed ≥10 threshold; gold/red ≥12."""
    assert HUGE_CELLS_PER_QUALITY[4] == 10   # 紫 (5×2 加特林重机枪 / 3×4 防护盾)
    assert HUGE_CELLS_PER_QUALITY[5] == 12   # 金 (重型全生态作战防弹衣 3×4)
    assert HUGE_CELLS_PER_QUALITY[6] == 12   # 红 (单兵外骨骼 3×4)


def test_aisha_visibility_rule() -> None:
    """Aisha only sees purple huge items; Ethan sees all."""
    assert aisha_can_observe_huge(4) is True
    assert aisha_can_observe_huge(5) is False
    assert aisha_can_observe_huge(6) is False


def test_standard_loadouts_distinct() -> None:
    """Sanity: the two loadouts differ (different hero needs)."""
    assert set(ETHAN_DEFAULT_LOADOUT) != set(AISHA_DEFAULT_LOADOUT)
    assert "优品均格" in ETHAN_DEFAULT_LOADOUT
    assert "总仓储空间" in AISHA_DEFAULT_LOADOUT
    assert "随机抽检(2)" in AISHA_DEFAULT_LOADOUT
    assert len(ETHAN_DEFAULT_LOADOUT) == 5
    assert len(AISHA_DEFAULT_LOADOUT) == 5


def test_ethan_alt_loadout_swaps_purple_value_for_random_reveal() -> None:
    """ETHAN_ALT replaces 优品估价 with 随机抽检(1) for category info."""
    assert "优品估价" not in ETHAN_ALT_LOADOUT
    assert "随机抽检(1)" in ETHAN_ALT_LOADOUT
    # The cheap-side three scan/avg tools stay shared between default and alt
    assert "普品扫描" in ETHAN_ALT_LOADOUT
    assert "良品扫描" in ETHAN_ALT_LOADOUT
    assert "优品均格" in ETHAN_ALT_LOADOUT


def test_standard_loadouts_dict_indexed_by_hero_mode() -> None:
    assert STANDARD_LOADOUTS["ethan"] == ETHAN_DEFAULT_LOADOUT
    assert STANDARD_LOADOUTS["aisha"] == AISHA_DEFAULT_LOADOUT


def test_tool_price_by_rarity_monotonic_increasing() -> None:
    """User-reported tool prices: 1200 < 2500 < 20000 < 35000 ≤ 50000."""
    from bidking_lab.inference.observation import TOOL_PRICE_BY_RARITY

    prices = [
        TOOL_PRICE_BY_RARITY["white"],
        TOOL_PRICE_BY_RARITY["green"],
        TOOL_PRICE_BY_RARITY["blue"],
        TOOL_PRICE_BY_RARITY["purple"],
        TOOL_PRICE_BY_RARITY["gold"],
    ]
    assert prices == sorted(prices)
    assert TOOL_PRICE_BY_RARITY["white"] == 1_200
    assert TOOL_PRICE_BY_RARITY["green"] == 2_500
    assert TOOL_PRICE_BY_RARITY["blue"] == 20_000
    assert TOOL_PRICE_BY_RARITY["purple"] == 35_000


def test_tool_price_override_for_warehouse_total() -> None:
    """总仓储空间 has a tool-specific 55k price (user-confirmed 2026-05-15)."""
    from bidking_lab.inference.observation import (
        TOOL_PRICE_BY_RARITY,
        TOOL_PRICE_OVERRIDES,
        tool_price,
    )

    assert TOOL_PRICE_OVERRIDES["总仓储空间"] == 55_000
    assert tool_price("总仓储空间") == 55_000
    # Unknown tool falls back to the rarity tier (default gold = 50k).
    assert tool_price("极品估价") == TOOL_PRICE_BY_RARITY["gold"]
    assert tool_price("普品扫描", rarity="white") == 1_200


# --- QualityBucketObs helpers ---

def test_bucket_huge_methods_defaults() -> None:
    b = QualityBucketObs(quality=4)
    assert b.huge_count_range() == (0, 0)
    assert b.huge_cells_per_item() == 10
    assert b.min_huge_cells() == 0
    assert b.max_huge_cells() == 0


def test_bucket_huge_band_purple_2_to_3() -> None:
    b = QualityBucketObs(quality=4, huge_band="2-3")
    assert b.huge_count_range() == (2, 3)
    assert b.min_huge_cells() == 20   # 2 × 10
    assert b.max_huge_cells() == 30   # 3 × 10


def test_bucket_huge_band_gold_one() -> None:
    """Gold huge min = 3×4 = 12 cells."""
    b = QualityBucketObs(quality=5, huge_band="1")
    assert b.huge_cells_per_item() == 12
    assert b.min_huge_cells() == 12


def test_bucket_huge_cells_override() -> None:
    """Override beats the per-quality default."""
    b = QualityBucketObs(quality=4, huge_band="1", huge_cells_override=20)
    assert b.huge_cells_per_item() == 20
    assert b.min_huge_cells() == 20


# --- Engine: candidate enumeration ---

def test_shipwreck_r4_purple_inference() -> None:
    """Reproduce the demo: avg=2.5 + value=86490 → top-1 is (35, 14)."""
    bucket = QualityBucketObs(
        quality=4,
        avg_cells=parse_reading("2.5"),
        value_sum=86_490,
    )
    cands = candidates_for_bucket(bucket, warehouse_capacity=159)
    assert cands, "expected at least one candidate"
    assert (cands[0].total_cells, cands[0].count) == (35, 14)


def test_huge_band_filters_candidates() -> None:
    """A '1 huge' band should pin total_cells >= 16 (purple) and count >= 1."""
    bucket = QualityBucketObs(
        quality=4,
        avg_cells=parse_reading("4.5"),    # 9/2, 18/4, 27/6, ...
        huge_band="1",
    )
    cands = candidates_for_bucket(bucket, warehouse_capacity=120)
    assert cands
    for c in cands:
        assert c.total_cells >= 16
        assert c.count >= 1


def test_huge_band_4plus_rejects_small_candidates() -> None:
    """4+ huge red means total_cells >= 48 (4 × 12 cells min); small excluded."""
    bucket = QualityBucketObs(
        quality=6,
        avg_cells=parse_reading("4"),
        huge_band="4+",
        value_range=(2_000_000, 5_000_000),
    )
    cands = candidates_for_bucket(bucket, warehouse_capacity=159)
    for c in cands:
        assert c.total_cells >= 48   # 4 huge × 12 cells minimum
        assert c.count >= 4


def test_huge_band_none_allows_zero_huge() -> None:
    bucket = QualityBucketObs(
        quality=4,
        avg_cells=parse_reading("2.5"),
        value_sum=86_490,
        huge_band="none",
    )
    cands = candidates_for_bucket(bucket, warehouse_capacity=159)
    # Top candidate stays (35, 14) — same as before band system.
    assert (cands[0].total_cells, cands[0].count) == (35, 14)


def test_warehouse_capacity_prunes_oversized() -> None:
    bucket = QualityBucketObs(quality=4, avg_cells=parse_reading("2.5"))
    cands = candidates_for_bucket(bucket, warehouse_capacity=20)
    for c in cands:
        assert c.total_cells <= 20


def test_avg_value_filter_with_value_sum_pins_count() -> None:
    """avg_value × count ≈ value_sum should reject mismatching counts."""
    bucket = QualityBucketObs(
        quality=4,
        avg_cells=parse_reading("2.5"),
        value_sum=86_490,
        avg_value=6178,   # 86490 / 14 ≈ 6178; (35, 14) survives
    )
    cands = candidates_for_bucket(bucket, warehouse_capacity=159)
    assert cands
    assert (cands[0].total_cells, cands[0].count) == (35, 14)
    for c in cands:
        implied = bucket.value_sum / max(1, c.count)
        assert abs(implied - bucket.avg_value) / bucket.avg_value <= 0.10


def test_avg_value_filter_rejects_off_target() -> None:
    """If avg_value ≠ value_sum/count within ±10%, candidate is dropped."""
    bucket = QualityBucketObs(
        quality=4,
        avg_cells=parse_reading("2.5"),
        value_sum=86_490,
        avg_value=20_000,   # implies count ≈ 4, very far from cells/2.5
    )
    cands = candidates_for_bucket(bucket, warehouse_capacity=159)
    for c in cands:
        implied = bucket.value_sum / max(1, c.count)
        assert abs(implied - bucket.avg_value) / bucket.avg_value <= 0.10


def test_avg_value_without_value_sum_uses_loose_pcv_filter() -> None:
    """No value_sum → fall back to per-cell prior estimate, ±25% tol."""
    bucket = QualityBucketObs(
        quality=4,
        avg_cells=parse_reading("2.5"),
        avg_value=6500,
    )
    cands = candidates_for_bucket(bucket, warehouse_capacity=159)
    assert cands  # at least some candidates survive


def test_capacity_minus_known_cells() -> None:
    """other_known_cells reduces the effective capacity for this bucket."""
    bucket = QualityBucketObs(quality=4, avg_cells=parse_reading("2.5"))
    cands = candidates_for_bucket(
        bucket, warehouse_capacity=159, other_known_cells=130,
    )
    # 159 - 130 = 29 cells available for purple
    for c in cands:
        assert c.total_cells <= 29


# --- Top-K per session ---

def test_top_k_returns_per_quality_dict() -> None:
    session = SessionObs(
        map_id=2510,
        hero="ethan",
        warehouse_total_cells=159,
        buckets={
            4: QualityBucketObs(
                quality=4,
                avg_cells=parse_reading("2.5"),
                value_sum=86_490,
            ),
            3: QualityBucketObs(quality=3, total_cells=18),
            1: QualityBucketObs(quality=1, total_cells=15),
        },
    )
    out = top_k_for_session(session, k=3)
    assert set(out.keys()) == {1, 3, 4}
    assert out[4][0].total_cells == 35
    assert out[4][0].count == 14
    # Top-K each bucket should not exceed 3 entries
    for q, cands in out.items():
        assert len(cands) <= 3


def test_top_k_subtracts_higher_quality_cells_from_budget() -> None:
    """Solving q=4 first should reduce the q=1 budget downstream."""
    session = SessionObs(
        map_id=2510,
        hero="ethan",
        warehouse_total_cells=100,
        buckets={
            4: QualityBucketObs(
                quality=4,
                avg_cells=parse_reading("2.5"),
                value_sum=86_490,   # → 35 cells
            ),
            1: QualityBucketObs(quality=1),   # no total_cells given
        },
    )
    out = top_k_for_session(session, k=3)
    # After purple takes 35 cells, white bucket capped at 100-35 = 65.
    for c in out[1]:
        assert c.total_cells <= 65
