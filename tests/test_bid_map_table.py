"""Tests for historical 21-column and current 23-column BidMap parsing."""

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
    row[17] = "4"
    row[18] = "[2000,1600,1300,1100,0]"
    row[19] = "[102,103,103,104,105]"
    for k, v in overrides.items():
        idx = int(k[3:])
        row[idx] = v
    return row


def test_parses_anthology_map() -> None:
    bm = parse_bid_map_row(_make_row())
    assert bm.map_id == 2101
    assert bm.name == "未知快递"
    assert bm.auction_mode == "open"
    assert bm.sub_pool_weights == [(2101, 100), (2102, 20)]
    assert bm.drop_pool_id == 2101
    assert bm.items_per_session_min == 16
    assert bm.items_per_session_max == 32
    assert bm.entry_fee_silver == 2000
    assert bm.starting_budget_silver == 10000
    assert bm.value_tier_ui == "ui_value_low"
    assert bm.rounds_total == 10
    assert bm.mode_flag == 4
    assert bm.bid_price_ladder == [2000, 1600, 1300, 1100, 0]
    assert bm.round_category_hints == [102, 103, 103, 104, 105]


def test_round_category_hints_with_zeros() -> None:
    """Mansion-style maps only hint R1 and R3 (zeros for other rounds)."""
    bm = parse_bid_map_row(_make_row(**{"col19": "[103,0,103,0,0]"}))
    assert bm.round_category_hints == [103, 0, 103, 0, 0]


def test_round_category_hints_missing() -> None:
    bm = parse_bid_map_row(_make_row(**{"col19": ""}))
    assert bm.round_category_hints == []


def test_parses_leaf_map() -> None:
    bm = parse_bid_map_row(_make_row(**{"col8": "[[]]", "col11": "[1,1,0]", "col14": "[[]]"}))
    assert bm.sub_pool_weights == []
    assert bm.entry_fee_silver == 0
    assert bm.starting_budget_silver == 0


def test_sealed_mode_for_tier4() -> None:
    bm = parse_bid_map_row(_make_row(**{"col0": "4401", "col17": "4"}))
    assert bm.auction_mode == "sealed"


def test_training_mode_for_tier3() -> None:
    bm = parse_bid_map_row(_make_row(**{"col0": "3401", "col17": "1", "col18": "[0,0,0,0,0]"}))
    assert bm.auction_mode == "training"
    assert bm.bid_price_ladder == [0, 0, 0, 0, 0]


def test_rejects_bad_drop_ref() -> None:
    with pytest.raises(Exception):
        parse_bid_map_row(_make_row(**{"col16": "[9999,2101]"}))


def test_dedups() -> None:
    rows = [_make_row(), _make_row()]
    with pytest.raises(ValueError, match="duplicate map_id"):
        parse_bid_map_table(rows)
