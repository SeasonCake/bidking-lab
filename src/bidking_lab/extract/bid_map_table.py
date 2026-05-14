"""Parse Tables/BidMap.txt into typed ``BidMapSummary`` records.

This is the *summary* form used for Layer 1 (data) exports. The deep
schema (sub-pool weight breakdown, ticket cost array, etc.) lands in a
later milestone — see ``docs/project_vision.md`` Layer 2 / Q1 ("地图
期望价值"). For now we expose id, name, description, and the raw 21-col
row so UI dropdowns can render `name (id=2101)`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from pydantic import BaseModel

from bidking_lab.extract.tables import load_table_rows

BID_MAP_TABLE_COLUMN_COUNT = 21


class BidMapSummary(BaseModel):
    map_id: int
    name: str
    description: str
    raw_row: list[str]


def parse_bid_map_row(row: Sequence[str]) -> BidMapSummary:
    if len(row) != BID_MAP_TABLE_COLUMN_COUNT:
        raise ValueError(
            f"bid map row must have {BID_MAP_TABLE_COLUMN_COUNT} columns, got {len(row)}"
        )
    return BidMapSummary(
        map_id=int(row[0]),
        name=row[1],
        description=row[2],
        raw_row=list(row),
    )


def parse_bid_map_table(rows: Iterable[Sequence[str]]) -> dict[int, BidMapSummary]:
    out: dict[int, BidMapSummary] = {}
    for i, row in enumerate(rows):
        try:
            bm = parse_bid_map_row(row)
        except Exception as exc:
            raise ValueError(f"failed to parse bid map row index {i}: {exc}") from exc
        if bm.map_id in out:
            raise ValueError(f"duplicate map_id={bm.map_id} at row {i}")
        out[bm.map_id] = bm
    return out


def load_bid_map_table(path: Path) -> dict[int, BidMapSummary]:
    return parse_bid_map_table(load_table_rows(path))


__all__ = (
    "BID_MAP_TABLE_COLUMN_COUNT",
    "BidMapSummary",
    "load_bid_map_table",
    "parse_bid_map_row",
    "parse_bid_map_table",
)
