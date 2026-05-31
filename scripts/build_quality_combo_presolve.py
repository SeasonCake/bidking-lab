"""Build q4/q5/q6 count/cell presolve data from local game tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.config import project_root  # noqa: E402
from bidking_lab.extract.bid_map_table import load_bid_map_table  # noqa: E402
from bidking_lab.extract.drop_table import load_drop_table  # noqa: E402
from bidking_lab.extract.item_table import load_item_table  # noqa: E402
from bidking_lab.inference.quality_combo_presolve import (  # noqa: E402
    quality_combo_presolve_payload,
)


def _default_tables_dir() -> Path:
    return project_root() / "data" / "raw" / "tables"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Precompute reachable q4/q5/q6 count/cell combinations.",
    )
    parser.add_argument(
        "--tables-dir",
        default=str(_default_tables_dir()),
        help="Directory containing BidMap.txt, Drop.txt, and Item.txt.",
    )
    parser.add_argument(
        "--out",
        default=str(project_root() / "data" / "processed" / "quality_combo_presolve_q456.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--maps",
        nargs="*",
        type=int,
        help="Map ids to include. Defaults to all loaded maps.",
    )
    parser.add_argument(
        "--max-count",
        type=int,
        default=None,
        help="Optional max per-quality count to retain.",
    )
    args = parser.parse_args()

    tables_dir = Path(args.tables_dir)
    maps = load_bid_map_table(tables_dir / "BidMap.txt")
    drops = load_drop_table(tables_dir / "Drop.txt")
    items = load_item_table(tables_dir / "Item.txt")
    map_ids = sorted(args.maps or maps)
    payload = quality_combo_presolve_payload(
        map_ids,
        maps=maps,
        drops=drops,
        items=items,
        max_count=args.max_count,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"wrote {out} maps={len(map_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
