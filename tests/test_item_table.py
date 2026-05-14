"""Tests for Item.txt parser."""

from __future__ import annotations

import pytest

from bidking_lab.extract.item_table import (
    ITEM_TABLE_COLUMN_COUNT,
    parse_item_row,
    parse_item_table,
)


def _make_row(**overrides: str) -> list[str]:
    row = ["0"] * ITEM_TABLE_COLUMN_COUNT
    row[0] = "1"
    row[1] = "测试物品"
    row[2] = "一个测试物品"
    row[3] = "itemName_1"
    row[5] = "itemDesc_1"
    row[6] = "[1]"
    row[8] = "3"
    row[9] = "1500"
    row[19] = "[101,102]"
    row[24] = "icon_test"
    row[33] = "Cube"
    row[37] = ""
    for k, v in overrides.items():
        idx = int(k[3:])
        row[idx] = v
    return row


def test_parse_item_row_basic() -> None:
    item = parse_item_row(_make_row())
    assert item.item_id == 1
    assert item.name == "测试物品"
    assert item.description == "一个测试物品"
    assert item.quality == 3
    assert item.quality_color == "blue"
    assert item.value == 1500
    assert item.tags == [1]
    assert item.allowed_shelves == [101, 102]
    assert item.icon_name == "icon_test"
    assert item.model_name == "Cube"
    assert len(item.raw_row) == ITEM_TABLE_COLUMN_COUNT


def test_quality_color_mapping() -> None:
    colors = {0: "none", 1: "white", 2: "green", 3: "blue", 4: "purple", 5: "gold", 6: "red"}
    for q, expected in colors.items():
        item = parse_item_row(_make_row(**{"col8": str(q)}))
        assert item.quality == q
        assert item.quality_color == expected


def test_rejects_wrong_column_count() -> None:
    with pytest.raises(ValueError, match="must have 38 columns"):
        parse_item_row(["1", "x"])


def test_rejects_out_of_range_quality() -> None:
    with pytest.raises(Exception):
        parse_item_row(_make_row(**{"col8": "9"}))


def test_parse_item_table_dedups() -> None:
    rows = [_make_row(), _make_row(**{"col0": "1"})]
    with pytest.raises(ValueError, match="duplicate item_id"):
        parse_item_table(rows)


def test_parse_item_table_round_trip() -> None:
    r1 = _make_row(**{"col0": "1"})
    r2 = _make_row(**{"col0": "2", "col8": "6", "col9": "19000000"})
    out = parse_item_table([r1, r2])
    assert set(out.keys()) == {1, 2}
    assert out[2].quality_color == "red"
    assert out[2].value == 19_000_000
