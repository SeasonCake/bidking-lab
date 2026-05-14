"""Produce derived JSON datasets under ``data/processed/``.

The outputs of this script are **committed to git** so users who clone
the repo can run the simulator without owning the game. They differ
from the raw Tables/*.txt files in:

- column names (our schema, not the game's anonymous indices)
- field selection (only what we've verified)
- format (UTF-8 JSON with stable key ordering)

The script only reads from ``data/raw/tables/`` (which IS gitignored,
because those are byte-for-byte copies of game files). If you do not
own the game, the JSONs already in the repo are what you use.

Outputs:
  data/processed/items.json             all 1132 items, full Item schema
  data/processed/items_droppable.json   subset: 883 items referenced by Drop pools
  data/processed/battle_items.json      all 64 battle items
  data/processed/heroes.json            all 20 heroes
  data/processed/maps.json              all 105 maps (summary form only)
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from bidking_lab.extract.battle_item_table import load_battle_item_table
from bidking_lab.extract.bid_map_table import load_bid_map_table
from bidking_lab.extract.drop_table import load_drop_table
from bidking_lab.extract.hero_table import load_hero_table
from bidking_lab.extract.item_table import load_item_table


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=False)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    tables_in = repo_root / "data" / "raw" / "tables"
    processed_dir = repo_root / "data" / "processed"

    if not tables_in.is_dir():
        print(f"missing raw tables: {tables_in}", file=sys.stderr)
        return 2

    print(f"reading raw tables: {tables_in}")
    print(f"writing processed : {processed_dir}\n")

    items = load_item_table(tables_in / "Item.txt")
    battle_items = load_battle_item_table(tables_in / "BattleItem.txt")
    heroes = load_hero_table(tables_in / "Hero.txt")
    maps = load_bid_map_table(tables_in / "BidMap.txt")
    drops = load_drop_table(tables_in / "Drop.txt")

    droppable_ids: set[int] = set()
    for pool in drops.values():
        for e in pool.entries:
            droppable_ids.add(e.item_id)

    # Exclude raw_row from JSON to keep the published dataset compact. Users who
    # want every original game-table column can regenerate the full TSV locally
    # via scripts/dump_processed_tables.py.
    exclude_raw = {"raw_row"}

    items_payload = [items[k].model_dump(exclude=exclude_raw) for k in sorted(items)]
    _write_json(processed_dir / "items.json", items_payload)
    print(f"  items.json              : {len(items_payload)} items")

    droppable_payload = [
        items[k].model_dump(exclude=exclude_raw)
        for k in sorted(items)
        if k in droppable_ids
    ]
    _write_json(processed_dir / "items_droppable.json", droppable_payload)
    print(
        f"  items_droppable.json    : {len(droppable_payload)} items "
        f"(referenced by some Drop pool)"
    )

    battle_payload = [battle_items[k].model_dump() for k in sorted(battle_items)]
    _write_json(processed_dir / "battle_items.json", battle_payload)
    print(f"  battle_items.json       : {len(battle_payload)} battle items")

    heroes_payload = [heroes[k].model_dump(exclude=exclude_raw) for k in sorted(heroes)]
    _write_json(processed_dir / "heroes.json", heroes_payload)
    print(f"  heroes.json             : {len(heroes_payload)} heroes")

    maps_payload = [maps[k].model_dump(exclude=exclude_raw) for k in sorted(maps)]
    _write_json(processed_dir / "maps.json", maps_payload)
    print(f"  maps.json               : {len(maps_payload)} maps (summary)")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
