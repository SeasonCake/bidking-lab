"""Tests for hero skill info scoring."""

from __future__ import annotations

from bidking_lab.extract.item_table import Item
from bidking_lab.simulation.hero_skills import (
    CAT_FASHION,
    HERO_SKILLS,
    InfoType,
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
        value=value, tags=[category], allowed_shelves=[],
        icon_name="", model_name="", raw_row=raw,
    )


def test_all_20_heroes_defined() -> None:
    assert len(HERO_SKILLS) == 20


def test_raven_reveals_all_quality() -> None:
    """Hero 301 (拉文) reveals quality of all items."""
    items = [_item(1, 3, CAT_FASHION), _item(2, 1, 101)]
    scores = compute_info_score(301, items)
    assert all(s == InfoType.QUALITY.value for s in scores)


def test_maria_reveals_value_for_white_green_blue() -> None:
    """Hero 108 (玛丽亚) reveals value for white/green/blue items."""
    items = [
        _item(1, 1, 101),  # white → value
        _item(2, 2, 102),  # green → value
        _item(3, 3, 103),  # blue → value
        _item(4, 4, 104),  # purple → nothing
        _item(5, 5, 105),  # gold → nothing
    ]
    scores = compute_info_score(108, items)
    assert scores[0] == InfoType.VALUE.value
    assert scores[1] == InfoType.VALUE.value
    assert scores[2] == InfoType.VALUE.value
    assert scores[3] == 0.0
    assert scores[4] == 0.0


def test_ahmed_returns_only_count_hints() -> None:
    """Hero 204 (艾哈迈德) gives only COUNT_HINT (0.1)."""
    items = [_item(1, 3, 101), _item(2, 5, 102)]
    scores = compute_info_score(204, items)
    assert all(s == InfoType.COUNT_HINT.value for s in scores)


def test_unknown_hero_returns_zeros() -> None:
    items = [_item(1, 3, 101)]
    scores = compute_info_score(9999, items)
    assert scores == [0.0]


def test_category_filter_works() -> None:
    """Hero 105 (塔蒂安娜) only reveals fashion items."""
    items = [
        _item(1, 3, CAT_FASHION),  # match
        _item(2, 3, 101),          # no match
    ]
    scores = compute_info_score(105, items)
    assert scores[0] == InfoType.QUALITY.value
    assert scores[1] == 0.0
