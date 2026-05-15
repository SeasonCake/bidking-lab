"""Parse Tables/Item.txt into typed ``Item`` records.

Only the columns we have **confirmed** via cross-checking with Drop.txt
and in-game observations get first-class fields. The remaining 27 raw
columns are kept on ``raw_row`` for future analysis — see
``docs/item_table_schema.md`` for the column-by-column status.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence

from pydantic import BaseModel, Field

from bidking_lab.data.quality import Quality, color_name
from bidking_lab.extract.tables import load_table_rows

ITEM_TABLE_COLUMN_COUNT = 38

_COL_ITEM_ID = 0
_COL_NAME = 1
_COL_DESC = 2
_COL_NAME_KEY = 3
_COL_DESC_KEY = 5
_COL_TAGS = 6
_COL_QUALITY = 8
_COL_VALUE = 9
_COL_ALLOWED_SHELVES = 19
_COL_SHAPE_WH = 7
_COL_ICON_NAME = 24
_COL_MODEL_NAME = 33


def _parse_int_list(blob: str) -> list[int]:
    """Parse a JSON-ish int list. Tolerates ``""`` / ``"[0]"`` / ``"[[]]"``."""
    if not blob or blob == "[]":
        return []
    data = json.loads(blob)
    out: list[int] = []
    if isinstance(data, list):
        for x in data:
            if isinstance(x, int):
                out.append(x)
    return out


class Item(BaseModel):
    """One row of Item.txt, with confirmed fields named.

    The 38-column raw row is preserved on ``raw_row`` so callers that
    need still-unmapped columns can inspect them without re-parsing.
    """

    item_id: int
    name: str
    description: str
    name_key: str
    desc_key: str
    quality: int = Field(ge=0, le=6)
    quality_color: str
    value: int = Field(ge=0)
    shape_w: int = Field(ge=0, le=6)
    shape_h: int = Field(ge=0, le=7)
    tags: list[int]
    allowed_shelves: list[int]
    icon_name: str
    model_name: str
    raw_row: list[str]


def parse_item_row(row: Sequence[str]) -> Item:
    if len(row) != ITEM_TABLE_COLUMN_COUNT:
        raise ValueError(
            f"item row must have {ITEM_TABLE_COLUMN_COUNT} columns, got {len(row)}"
        )
    q_raw = int(row[_COL_QUALITY])
    wh = int(row[_COL_SHAPE_WH])
    return Item(
        item_id=int(row[_COL_ITEM_ID]),
        name=row[_COL_NAME],
        description=row[_COL_DESC],
        name_key=row[_COL_NAME_KEY],
        desc_key=row[_COL_DESC_KEY],
        quality=q_raw,
        quality_color=color_name(q_raw),
        value=int(row[_COL_VALUE]),
        shape_w=wh // 10,
        shape_h=wh % 10,
        tags=_parse_int_list(row[_COL_TAGS]),
        allowed_shelves=_parse_int_list(row[_COL_ALLOWED_SHELVES]),
        icon_name=row[_COL_ICON_NAME],
        model_name=row[_COL_MODEL_NAME],
        raw_row=list(row),
    )


def parse_item_table(rows: Iterable[Sequence[str]]) -> dict[int, Item]:
    out: dict[int, Item] = {}
    for i, row in enumerate(rows):
        try:
            item = parse_item_row(row)
        except Exception as exc:
            raise ValueError(f"failed to parse item row index {i}: {exc}") from exc
        if item.item_id in out:
            raise ValueError(f"duplicate item_id={item.item_id} at row {i}")
        out[item.item_id] = item
    return out


def load_item_table(path: Path) -> dict[int, Item]:
    return parse_item_table(load_table_rows(path))


__all__ = (
    "ITEM_TABLE_COLUMN_COUNT",
    "Item",
    "Quality",
    "load_item_table",
    "parse_item_row",
    "parse_item_table",
)
