"""Tests for hero skill info scoring (v2 timing-aware)."""

from __future__ import annotations

from bidking_lab.extract.item_table import Item
from bidking_lab.simulation.hero_skills import (
    CAT_FASHION,
    HERO_SKILLS,
    InfoType,
    TIMING_WEIGHTS,
    compute_info_score,
)


def _item(item_id: int, quality: int, category: int, value: int = 1000) -> Item:
    raw = ["0"] * 38
    raw[0] = str(item_id)
    raw[5] = str(category)
    raw[8] = str(quality)
    return Item(
        item_id=item_id, name=f"i{item_id}", description="",
        name_key="", desc_key="", quality=quality, quality_color="",
        value=value, shape_w=1, shape_h=1,
        tags=[category], allowed_shelves=[],
        icon_name="", model_name="", raw_row=raw,
    )


def test_all_20_heroes_defined() -> None:
    assert len(HERO_SKILLS) == 20


def test_raven_timing_penalised() -> None:
    """Hero 301 (拉文) reveals quality at R5 — heavily discounted."""
    items = [_item(1, 3, CAT_FASHION), _item(2, 1, 101)]
    scores_timed = compute_info_score(301, items, use_timing=True)
    scores_raw = compute_info_score(301, items, use_timing=False)
    # Without timing: full quality score
    assert all(s == InfoType.QUALITY.value for s in scores_raw)
    # With timing: quality * R5 weight → tiny
    expected = InfoType.QUALITY.value * TIMING_WEIGHTS[5]
    assert all(abs(s - expected) < 1e-9 for s in scores_timed)
    assert scores_timed[0] < 0.05


def test_maria_unaffected_by_timing() -> None:
    """Hero 108 (玛丽亚) reveals value at R1 — full score with timing."""
    items = [
        _item(1, 1, 101),  # white → value
        _item(2, 2, 102),  # green → value
        _item(3, 3, 103),  # blue → value
        _item(4, 4, 104),  # purple → nothing
        _item(5, 5, 105),  # gold → nothing
    ]
    scores = compute_info_score(108, items, use_timing=True)
    assert scores[0] == InfoType.VALUE.value
    assert scores[1] == InfoType.VALUE.value
    assert scores[2] == InfoType.VALUE.value
    assert scores[3] == 0.0
    assert scores[4] == 0.0


def test_ahmed_r1_effect_dominates() -> None:
    """Hero 204 (艾哈迈德) R1 total count covers all items."""
    items = [_item(1, 3, 101), _item(2, 5, 102)]
    scores = compute_info_score(204, items, use_timing=True)
    expected = InfoType.COUNT_HINT.value * TIMING_WEIGHTS[1]
    assert all(abs(s - expected) < 1e-9 for s in scores)


def test_unknown_hero_returns_zeros() -> None:
    items = [_item(1, 3, 101)]
    scores = compute_info_score(9999, items)
    assert scores == [0.0]


def test_category_filter_works() -> None:
    """Hero 105 (塔蒂安娜) only reveals fashion items (R1)."""
    items = [
        _item(1, 3, CAT_FASHION),  # match
        _item(2, 3, 101),          # no match
    ]
    scores = compute_info_score(105, items, use_timing=True)
    assert scores[0] == InfoType.QUALITY.value * TIMING_WEIGHTS[1]
    assert scores[1] == 0.0


def test_timing_disabled_gives_raw_scores() -> None:
    """With use_timing=False, scores are the raw InfoType values."""
    items = [_item(1, 3, CAT_FASHION)]
    s_raw = compute_info_score(105, items, use_timing=False)
    s_timed = compute_info_score(105, items, use_timing=True)
    assert s_raw[0] == InfoType.QUALITY.value
    assert s_timed[0] < s_raw[0] or TIMING_WEIGHTS[1] == 1.0
