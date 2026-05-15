"""Tests for the R2 snipe-bid recommendation."""

from __future__ import annotations

import numpy as np

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropEntry, DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.inference.observation import (
    QualityBucketObs,
    SessionObs,
)
from bidking_lab.inference.snipe import (
    SnipeRecommendation,
    compute_snipe_recommendation,
)


def _make_item(item_id, value, quality, shape=(1, 1)) -> Item:
    w, h = shape
    return Item(
        item_id=item_id, name=f"i{item_id}", description="",
        name_key="k", desc_key="d", quality=quality, quality_color="x",
        value=value, shape_w=w, shape_h=h,
        tags=[], allowed_shelves=[], icon_name="", model_name="",
        raw_row=["0"] * 38,
    )


def _make_pool(pool_id, entries) -> DropPool:
    return DropPool(
        pool_id=pool_id, name=f"pool_{pool_id}", description="",
        pool_type=2,
        entries=[
            DropEntry(category=c, item_id=i, n_min=mn, n_max=mx, weight=w)
            for c, i, mn, mx, w in entries
        ],
    )


def _make_map(map_id, drop_pool_id, *, min_items=15, max_items=20) -> BidMap:
    return BidMap(
        map_id=map_id, name=f"map_{map_id}", description="",
        category=101, auction_mode="open", sub_pool_weights=[],
        rounds_total=10, entry_fee_silver=0, starting_budget_silver=500_000,
        drop_pool_id=drop_pool_id,
        items_per_session_min=min_items, items_per_session_max=max_items,
        value_tier_ui="ui_value_low", mode_flag=4,
        bid_price_ladder=[], raw_row=["0"] * 21,
    )


def _build_big_warehouse_world():
    """A pool that consistently produces ~130-cell big-warehouse sessions."""
    items = {
        # Whites/greens — cheap fillers
        101: _make_item(101, value=130, quality=1, shape=(2, 2)),         # 4 cells, 130 silver
        201: _make_item(201, value=320, quality=2, shape=(2, 2)),         # 4 cells, 320 silver
        # Blues
        301: _make_item(301, value=1_200, quality=3, shape=(2, 2)),       # 4 cells
        # Purples
        401: _make_item(401, value=8_000, quality=4, shape=(2, 2)),       # 4 cells, 2k/cell
        402: _make_item(402, value=42_000, quality=4, shape=(4, 4)),      # huge, 16 cells
        # Golds — high variance
        501: _make_item(501, value=180_000, quality=5, shape=(3, 3)),     # 9 cells, 20k/cell
        # Reds
        601: _make_item(601, value=500_000, quality=6, shape=(3, 3)),     # 9 cells, big
    }
    pool = _make_pool(900, [
        (101, 101, 2, 4, 6),
        (101, 201, 2, 4, 5),
        (101, 301, 2, 4, 5),
        (101, 401, 1, 3, 3),
        (101, 402, 0, 1, 1),
        (101, 501, 0, 1, 1),
        (101, 601, 0, 1, 1),
    ])
    bid_map = _make_map(2407, 900, min_items=10, max_items=14)
    return {2407: bid_map}, {900: pool}, items


# --- Gating ---

def test_snipe_returns_none_when_aisha_missing_green_outline() -> None:
    """Aisha requires q=1, q=2, q=3 all observed (her R1-R3 outline accumulation)."""
    maps, drops, items = _build_big_warehouse_world()
    session = SessionObs(
        map_id=2407, hero="aisha", warehouse_total_cells=130,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=10),
            # missing q=2 (green outline cells)
            3: QualityBucketObs(quality=3, total_cells=8),
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=200, rng=np.random.default_rng(0),
    )
    assert rec is None


def test_snipe_returns_none_for_unknown_hero() -> None:
    maps, drops, items = _build_big_warehouse_world()
    session = SessionObs(
        map_id=2407, hero="sophie", warehouse_total_cells=130,   # type: ignore[arg-type]
        buckets={
            1: QualityBucketObs(quality=1, total_cells=10),
            3: QualityBucketObs(quality=3, total_cells=8),
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=200, rng=np.random.default_rng(0),
    )
    assert rec is None


def test_snipe_returns_none_when_warehouse_below_120() -> None:
    maps, drops, items = _build_big_warehouse_world()
    session = SessionObs(
        map_id=2407, hero="ethan", warehouse_total_cells=110,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=10),
            3: QualityBucketObs(quality=3, total_cells=8),
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=200, rng=np.random.default_rng(0),
    )
    assert rec is None


def test_snipe_returns_none_when_white_green_cells_missing() -> None:
    maps, drops, items = _build_big_warehouse_world()
    session = SessionObs(
        map_id=2407, hero="ethan", warehouse_total_cells=130,
        buckets={
            3: QualityBucketObs(quality=3, total_cells=8),
            # missing q=1
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=200, rng=np.random.default_rng(0),
    )
    assert rec is None


def test_snipe_returns_none_when_blue_cells_missing() -> None:
    maps, drops, items = _build_big_warehouse_world()
    session = SessionObs(
        map_id=2407, hero="ethan", warehouse_total_cells=130,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=10),
            # missing q=3
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=200, rng=np.random.default_rng(0),
    )
    assert rec is None


def test_snipe_returns_none_when_warehouse_total_cells_unknown() -> None:
    maps, drops, items = _build_big_warehouse_world()
    session = SessionObs(
        map_id=2407, hero="ethan", warehouse_total_cells=None,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=10),
            3: QualityBucketObs(quality=3, total_cells=8),
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=200, rng=np.random.default_rng(0),
    )
    assert rec is None


def test_snipe_returns_none_when_too_few_matching_samples() -> None:
    """If MC produces zero matches in the warehouse_tolerance window,
    bail rather than emit a noisy recommendation."""
    maps, drops, items = _build_big_warehouse_world()
    # Ask for a warehouse_total_cells far from what the pool ever produces.
    session = SessionObs(
        map_id=2407, hero="ethan", warehouse_total_cells=400,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=10),
            3: QualityBucketObs(quality=3, total_cells=8),
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=200, warehouse_tolerance=2,
        min_matching_samples=10, rng=np.random.default_rng(0),
    )
    assert rec is None


# --- Happy path ---

def test_snipe_produces_recommendation_for_big_ethan_session() -> None:
    maps, drops, items = _build_big_warehouse_world()
    # The pool produces ~10-14 items × 4-16 cells ≈ 40-130 cells.
    # Use warehouse_total_cells=80 with tolerance=20 → most samples match.
    session = SessionObs(
        map_id=2407, hero="ethan", warehouse_total_cells=130,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=14),
            3: QualityBucketObs(quality=3, total_cells=10),
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=500, warehouse_tolerance=40,        # generous for synthetic pool
        min_matching_samples=30,
        rng=np.random.default_rng(123),
    )
    assert isinstance(rec, SnipeRecommendation)
    assert rec.map_id == 2407
    assert rec.warehouse_total_cells == 130
    assert rec.low_tier_cells_observed == 24
    # Monotonic quantiles
    assert rec.p25_value <= rec.expected_value <= rec.p75_value <= rec.p90_value
    # safe_floor < expected < snipe_max
    assert rec.safe_floor_bid <= rec.expected_value
    assert rec.snipe_max_bid >= rec.p75_value
    # Rationale references the observed warehouse + low-tier numbers
    assert "130" in rec.rationale
    assert "24" in rec.rationale
    # UI tooltip is non-empty
    tip = rec.as_ui_tooltip()
    assert "\u79d2\u4ed3" in tip and str(rec.snipe_max_bid) in tip.replace(",", "")


def test_snipe_produces_aisha_r3_recommendation() -> None:
    """Aisha at R3 with full q=1+q=2+q=3 outlines: rationale mentions R3 + 0 silver scan."""
    maps, drops, items = _build_big_warehouse_world()
    session = SessionObs(
        map_id=2407, hero="aisha", warehouse_total_cells=130,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=8),
            2: QualityBucketObs(quality=2, total_cells=6),
            3: QualityBucketObs(quality=3, total_cells=10),
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=500, warehouse_tolerance=40, min_matching_samples=30,
        rng=np.random.default_rng(2026),
    )
    assert isinstance(rec, SnipeRecommendation)
    assert rec.hero == "aisha"
    assert rec.round_window == "R3"
    assert rec.low_tier_cells_observed == 24       # 8 + 6 + 10
    # Aisha rationale should mention R3 and the "0 silver" framing.
    assert "R3" in rec.rationale
    assert "\u8f6e\u5ed3" in rec.rationale          # 轮廓
    assert "0 \u94f6\u5e01" in rec.rationale       # 0 银币
    # Tooltip prefix carries the round window.
    tip = rec.as_ui_tooltip()
    assert "(R3)" in tip


def test_snipe_ethan_rationale_mentions_R2_and_scan_tools() -> None:
    """Sanity: Ethan branch produces R2-labelled rationale referencing scan tools."""
    maps, drops, items = _build_big_warehouse_world()
    session = SessionObs(
        map_id=2407, hero="ethan", warehouse_total_cells=130,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=14),
            3: QualityBucketObs(quality=3, total_cells=10),
        },
    )
    rec = compute_snipe_recommendation(
        session, maps=maps, drops=drops, items=items,
        n_trials=400, warehouse_tolerance=40, min_matching_samples=20,
        rng=np.random.default_rng(11),
    )
    assert rec is not None
    assert rec.hero == "ethan"
    assert rec.round_window == "R2"
    assert "\u666e\u54c1\u626b\u63cf" in rec.rationale   # 普品扫描
    assert "\u826f\u54c1\u626b\u63cf" in rec.rationale   # 良品扫描
    assert "(R2)" in rec.as_ui_tooltip()


def test_snipe_recommendation_is_reproducible_with_seed() -> None:
    maps, drops, items = _build_big_warehouse_world()
    session = SessionObs(
        map_id=2407, hero="ethan", warehouse_total_cells=130,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=14),
            3: QualityBucketObs(quality=3, total_cells=10),
        },
    )
    kwargs = dict(
        maps=maps, drops=drops, items=items,
        n_trials=300, warehouse_tolerance=40, min_matching_samples=20,
    )
    rec1 = compute_snipe_recommendation(
        session, rng=np.random.default_rng(7), **kwargs,
    )
    rec2 = compute_snipe_recommendation(
        session, rng=np.random.default_rng(7), **kwargs,
    )
    assert rec1 is not None and rec2 is not None
    assert rec1.expected_value == rec2.expected_value
    assert rec1.snipe_max_bid == rec2.snipe_max_bid
    assert rec1.n_matching_samples == rec2.n_matching_samples
