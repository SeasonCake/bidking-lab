"""Tests for the expanded BidMap parser (col[16] / col[8] / col[11] / col[14])."""

from __future__ import annotations

import pytest

from bidking_lab.extract.bid_map_table import (
    BID_MAP_TABLE_COLUMN_COUNT,
    parse_bid_map_row,
    parse_bid_map_table,
)


def _make_row(**overrides: str) -> list[str]:
    row = ["0"] * BID_MAP_TABLE_COLUMN_COUNT
    row[0] = "2101"
    row[1] = "未知快递"
    row[2] = "desc"
    row[7] = "101"
    row[8] = "[[2101,100],[2102,20]]"
    row[9] = "ui_value_low"
    row[10] = "10"
    row[11] = "[1,1,2000]"
    row[14] = "[[1,1,10000]]"
    row[16] = "[9999,2101,16,32]"
    for k, v in overrides.items():
        idx = int(k[3:])
        row[idx] = v
    return row


def test_parses_anthology_map() -> None:
    bm = parse_bid_map_row(_make_row())
    assert bm.map_id == 2101
    assert bm.name == "未知快递"
    assert bm.sub_pool_weights == [(2101, 100), (2102, 20)]
    assert bm.drop_pool_id == 2101
    assert bm.items_per_session_min == 16
    assert bm.items_per_session_max == 32
    assert bm.entry_fee_silver == 2000
    assert bm.starting_budget_silver == 10000
    assert bm.value_tier_ui == "ui_value_low"
    assert bm.rounds_total == 10


def test_parses_leaf_map() -> None:
    bm = parse_bid_map_row(_make_row(**{"col8": "[[]]", "col11": "[1,1,0]", "col14": "[[]]"}))
    assert bm.sub_pool_weights == []
    assert bm.entry_fee_silver == 0
    assert bm.starting_budget_silver == 0


def test_rejects_bad_drop_ref() -> None:
    with pytest.raises(Exception):
        parse_bid_map_row(_make_row(**{"col16": "[9999,2101]"}))


def test_dedups() -> None:
    rows = [_make_row(), _make_row()]
    with pytest.raises(ValueError, match="duplicate map_id"):
        parse_bid_map_table(rows)
