"""Parse Tables/BidMap.txt into typed ``BidMap`` records.

The 21-column row has been profiled (see ``docs/bid_map_schema.md``).
v1 schema fields confirmed by cross-checking with Drop.txt + user:

- col[0]   map_id
- col[1]   name
- col[2]   description
- col[7]   category (101-105 / 201; 9 distinct values)
- col[8]   sub_pool_weights: ``[[map_id, weight], ...]`` for anthology
           maps (the "未知" series); leaf maps store ``[[]]``
- col[10]  rounds_total (5 distinct: 10 / 15 / 20 / 25 / 30)
- col[11]  entry_fee: ``[1, 1, silver]`` — currency cost to play
- col[14]  starting_budget: ``[[1, 1, silver]]`` — bidding budget granted
- col[16]  ``[9999, drop_pool_id, items_per_session_min, items_per_session_max]``
- col[9]   value_tier_ui: ``ui_value_{low,lower,medium,higher,high}``
- col[17]  mode_flag: 4=normal auction, 1=training, 2=tutorial
- col[18]  bid_price_ladder: per-round starting price tiers

Auction mode derived from map_id prefix + col[17]:
  2xxx + col17∈{2,4} → "open"   (明拍: bids visible)
  4xxx + col17=4     → "sealed" (暗拍: blind bids)
  3xxx + col17=1     → "training"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

from typing import Literal

from pydantic import BaseModel, Field

from bidking_lab.extract.tables import load_table_rows

BID_MAP_TABLE_COLUMN_COUNT = 21

AuctionMode = Literal["open", "sealed", "training"]


def _infer_auction_mode(map_id: int, mode_flag: int) -> AuctionMode:
    tier = map_id // 1000
    if mode_flag == 1 or (3000 <= map_id < 4000):
        return "training"
    if tier >= 4:
        return "sealed"
    return "open"


def _silver_amount(blob: str) -> int:
    """Parse `[1, 1, N]` or `[[1, 1, N]]`. Return 0 for empty / missing."""
    if blob in ("", "[]", "[[]]"):
        return 0
    data = json.loads(blob)
    if not data:
        return 0
    if isinstance(data[0], list):
        if not data[0]:
            return 0
        inner = data[0]
    else:
        inner = data
    # Expected form: [cat=1, item_id=1, amount]
    if len(inner) >= 3:
        return int(inner[2])
    return 0


def _parse_sub_pool_weights(blob: str) -> list[tuple[int, int]]:
    if blob in ("", "[]", "[[]]"):
        return []
    raw = json.loads(blob)
    out: list[tuple[int, int]] = []
    for pair in raw:
        if isinstance(pair, list) and len(pair) >= 2:
            out.append((int(pair[0]), int(pair[1])))
    return out


def _parse_drop_ref(blob: str) -> tuple[int, int, int]:
    """col[16] → (drop_pool_id, items_min, items_max)."""
    data = json.loads(blob)
    if len(data) < 4:
        raise ValueError(f"col[16] drop_ref must have 4 elements, got {data!r}")
    return int(data[1]), int(data[2]), int(data[3])


class BidMap(BaseModel):
    """One BidMap.txt row with simulation-relevant fields named.

    For anthology maps (``sub_pool_weights`` non-empty), ``drop_pool_id``
    is the *self* pool — but a real session randomly picks among
    sub-maps weighted by ``sub_pool_weights``, then uses that map's
    own ``drop_pool_id``. The simulator handles this routing.
    """

    map_id: int
    name: str
    description: str
    category: int
    auction_mode: AuctionMode
    sub_pool_weights: list[tuple[int, int]] = Field(default_factory=list)
    rounds_total: int = Field(ge=0)
    entry_fee_silver: int = Field(ge=0)
    starting_budget_silver: int = Field(ge=0)
    drop_pool_id: int
    items_per_session_min: int = Field(ge=0)
    items_per_session_max: int = Field(ge=0)
    value_tier_ui: str
    mode_flag: int = Field(ge=0)
    bid_price_ladder: list[int] = Field(default_factory=list)
    raw_row: list[str]


# Backwards-compat alias for earlier imports. v0 only exposed map_id /
# name / description / raw_row; the new BidMap is a strict superset.
BidMapSummary = BidMap


def parse_bid_map_row(row: Sequence[str]) -> BidMap:
    if len(row) != BID_MAP_TABLE_COLUMN_COUNT:
        raise ValueError(
            f"bid map row must have {BID_MAP_TABLE_COLUMN_COUNT} columns, got {len(row)}"
        )
    drop_pool_id, items_min, items_max = _parse_drop_ref(row[16])
    map_id = int(row[0])
    mode_flag = int(row[17])
    ladder_raw = json.loads(row[18]) if row[18] not in ("", "[]") else []
    return BidMap(
        map_id=map_id,
        name=row[1],
        description=row[2],
        category=int(row[7]),
        auction_mode=_infer_auction_mode(map_id, mode_flag),
        sub_pool_weights=_parse_sub_pool_weights(row[8]),
        rounds_total=int(row[10]),
        entry_fee_silver=_silver_amount(row[11]),
        starting_budget_silver=_silver_amount(row[14]),
        drop_pool_id=drop_pool_id,
        items_per_session_min=items_min,
        items_per_session_max=items_max,
        value_tier_ui=row[9],
        mode_flag=mode_flag,
        bid_price_ladder=ladder_raw,
        raw_row=list(row),
    )


def parse_bid_map_table(rows: Iterable[Sequence[str]]) -> dict[int, BidMap]:
    out: dict[int, BidMap] = {}
    for i, row in enumerate(rows):
        try:
            bm = parse_bid_map_row(row)
        except Exception as exc:
            raise ValueError(f"failed to parse bid map row index {i}: {exc}") from exc
        if bm.map_id in out:
            raise ValueError(f"duplicate map_id={bm.map_id} at row {i}")
        out[bm.map_id] = bm
    return out


def load_bid_map_table(path: Path) -> dict[int, BidMap]:
    return parse_bid_map_table(load_table_rows(path))


__all__ = (
    "BID_MAP_TABLE_COLUMN_COUNT",
    "BidMap",
    "BidMapSummary",
    "load_bid_map_table",
    "parse_bid_map_row",
    "parse_bid_map_table",
)
