"""Parse Tables/BidMap.txt into typed ``BidMap`` records.

The historical 21-column row and current 23-column row have been profiled
(see ``docs/bid_map_schema.md``). Current fileVersion 300 rows use the
23-column layout. Schema fields confirmed by cross-checking with Drop.txt
and user-provided sample evidence:

- col[0]   map_id
- col[1]   name
- col[2]   description
- col[7]   category (101-105 / 201; 9 distinct values)
- col[9]   sub_pool_weights: ``[[map_id, weight], ...]`` for anthology
           maps (the "未知" series); leaf maps store ``[[]]``
- col[11]  rounds_total (5 distinct: 10 / 15 / 20 / 25 / 30)
- col[12]  entry_fee: ``[1, 1, silver]`` — currency cost to play
- col[14]  round-cap candidate: ``[40/50/60, ...]``; audit-only
- col[15]  starting_budget: ``[[1, 1, silver]]`` — bidding budget granted
- col[17]  ``[9999, drop_pool_id, items_per_session_min, items_per_session_max]``
- col[10]  value_tier_ui: ``ui_value_{low,lower,medium,higher,high}``
- col[18]  mode_flag: 4=normal auction, 1=training, 2=tutorial
- col[19]  bid_price_ladder: per-round starting price tiers
- col[20]  round_category_hints: 5-element list, one per auction round.
           Each element is an Item category code (102/103/104/105) the
           game previews to the player for that round, or ``0`` if no
           hint is given. Confirmed by ``scripts/probe_round_categories.py``:
           * R1 always carries a hint (55/55 leaf maps)
           * R3 carries a hint in ~67% of maps
           * R5 / R2 / R4 progressively rarer
           * Hint density correlates with difficulty: 快递/仓库 = 5 hints,
             集装箱 = 3, 别墅 = 2, 沉船 = 1.
           Only categories 102/103/104/105 ever appear as hints; the
           game never previews 101/106-110.

Auction mode derived from map_id prefix + current col[18] mode_flag:
  2xxx + mode_flag∈{2,4} → "open"   (明拍: bids visible)
  4xxx + mode_flag=4     → "sealed" (暗拍: blind bids)
  3xxx + mode_flag=1     → "training"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

from typing import Literal

from pydantic import BaseModel, Field

from bidking_lab.extract.tables import load_table_rows

BID_MAP_TABLE_COLUMN_COUNT = 21
BID_MAP_TABLE_COLUMN_COUNT_V2 = 23

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
    """drop_ref blob → (drop_pool_id, items_min, items_max)."""
    data = json.loads(blob)
    if len(data) < 4:
        raise ValueError(f"drop_ref must have 4 elements, got {data!r}")
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
    round_category_hints: list[int] = Field(default_factory=list)
    """Per-round category preview shown to the player (5 entries).

    ``0`` means the game gives no hint for that round; non-zero values
    are Item category codes (only 102/103/104/105 ever observed)."""
    raw_row: list[str]


# Backwards-compat alias for earlier imports. v0 only exposed map_id /
# name / description / raw_row; the new BidMap is a strict superset.
BidMapSummary = BidMap


def parse_bid_map_row(row: Sequence[str]) -> BidMap:
    if len(row) == BID_MAP_TABLE_COLUMN_COUNT:
        idx = {
            "category": 7,
            "sub_pool_weights": 8,
            "value_tier_ui": 9,
            "rounds_total": 10,
            "entry_fee": 11,
            "starting_budget": 14,
            "drop_ref": 16,
            "mode_flag": 17,
            "bid_price_ladder": 18,
            "round_category_hints": 19,
        }
    elif len(row) == BID_MAP_TABLE_COLUMN_COUNT_V2:
        # Current v300 game data has two extra columns. Confirmed old fields
        # moved as follows: old col[8] -> new col[9], and old col[9+] ->
        # new col[10+]. The parser keeps the previous public schema and
        # preserves all raw columns for future mapping of the new fields.
        idx = {
            "category": 7,
            "sub_pool_weights": 9,
            "value_tier_ui": 10,
            "rounds_total": 11,
            "entry_fee": 12,
            "starting_budget": 15,
            "drop_ref": 17,
            "mode_flag": 18,
            "bid_price_ladder": 19,
            "round_category_hints": 20,
        }
    else:
        raise ValueError(
            f"bid map row must have {BID_MAP_TABLE_COLUMN_COUNT} or "
            f"{BID_MAP_TABLE_COLUMN_COUNT_V2} columns, got {len(row)}"
        )
    drop_pool_id, items_min, items_max = _parse_drop_ref(row[idx["drop_ref"]])
    map_id = int(row[0])
    mode_flag = int(row[idx["mode_flag"]])
    ladder_text = row[idx["bid_price_ladder"]]
    ladder_raw = json.loads(ladder_text) if ladder_text not in ("", "[]") else []
    hints_raw_text = row[idx["round_category_hints"]]
    hints_parsed = json.loads(hints_raw_text) if hints_raw_text not in ("", "[]") else []
    hints_raw = hints_parsed if isinstance(hints_parsed, list) else []
    return BidMap(
        map_id=map_id,
        name=row[1],
        description=row[2],
        category=int(row[idx["category"]]),
        auction_mode=_infer_auction_mode(map_id, mode_flag),
        sub_pool_weights=_parse_sub_pool_weights(row[idx["sub_pool_weights"]]),
        rounds_total=int(row[idx["rounds_total"]]),
        entry_fee_silver=_silver_amount(row[idx["entry_fee"]]),
        starting_budget_silver=_silver_amount(row[idx["starting_budget"]]),
        drop_pool_id=drop_pool_id,
        items_per_session_min=items_min,
        items_per_session_max=items_max,
        value_tier_ui=row[idx["value_tier_ui"]],
        mode_flag=mode_flag,
        bid_price_ladder=ladder_raw,
        round_category_hints=[int(x) for x in hints_raw],
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
