"""Verify BidMap → Drop.txt linkage and decode the ticket / item-count fields."""

from __future__ import annotations

import io
import json
import sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from bidking_lab.extract.drop_table import load_drop_table
from bidking_lab.extract.tables import load_table_rows


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    tables_in = repo_root / "data" / "raw" / "tables"

    drops = load_drop_table(tables_in / "Drop.txt")
    map_rows = load_table_rows(tables_in / "BidMap.txt")

    map_ids = {int(r[0]) for r in map_rows}
    drop_ids = set(drops.keys())

    overlap = map_ids & drop_ids
    print(f"BidMap ids                 : {len(map_ids)}")
    print(f"Drop.txt pool ids          : {len(drop_ids)}")
    print(f"intersection (map ↔ drop)  : {len(overlap)}")
    print(f"  sample overlap           : {sorted(overlap)[:10]}")
    print(f"  maps without same-id drop: {sorted(map_ids - drop_ids)[:10]}")
    print()

    print("=== col[16] decode `[meta_cat, drop_pool_id, min_items?, max_items?]` ===")
    col16_samples = Counter()
    for r in map_rows[:10]:
        col16 = json.loads(r[16])
        print(f"  map={r[0]:>4}  col[16]={col16}  → drop pool {col16[1]} (exists in Drop.txt: {col16[1] in drops})")
        col16_samples[tuple(col16[2:])] += 1
    print(f"  col16 trailing pair histogram (across first 10): {dict(col16_samples)}")

    # full histogram of trailing pair
    full_hist = Counter()
    for r in map_rows:
        col16 = json.loads(r[16])
        full_hist[tuple(col16[2:])] += 1
    print(f"  full histogram across all 105 maps: {dict(full_hist)}")
    print()

    print("=== col[11] decode `[?, ?, value]` (suspected ticket fee in silver) ===")
    for r in map_rows[:6]:
        col11 = json.loads(r[11]) if r[11] not in ("[]", "") else None
        col9 = r[9]
        print(f"  map={r[0]:>4}  tier_ui={col9:>16}  col[11]={col11}")
    print()

    print("=== col[14] decode `[[?, ?, value]]` (suspected prize / budget) ===")
    for r in map_rows[:6]:
        col14 = json.loads(r[14]) if r[14] not in ("[]", "") else None
        col9 = r[9]
        print(f"  map={r[0]:>4}  tier_ui={col9:>16}  col[14]={col14}")
    print()

    print("=== col[10] / col[13] / col[18] / col[19] for the same first 6 maps ===")
    for r in map_rows[:6]:
        print(
            f"  map={r[0]:>4}  col10={r[10]:>3}  col13={r[13]:<22}  "
            f"col18={r[18]:<26}  col19={r[19]}"
        )

    # Same-name maps across tiers: check if their cols differ
    print()
    print("=== Same-name across tiers: 'X 别墅' tier-by-tier (col 10/11/14/16) ===")
    names_by_tier: dict[str, list[list[str]]] = {}
    for r in map_rows:
        name = r[1].strip()
        names_by_tier.setdefault(name, []).append(r)
    for name, rs in names_by_tier.items():
        if len(rs) >= 2 and "别墅" in name:
            print(f"  {name!r}: {len(rs)} tiers")
            for r in rs:
                print(
                    f"    id={r[0]:>4}  col9={r[9]:>16}  col10={r[10]:>3}  "
                    f"col11={r[11]:<22}  col14={r[14]:<22}  col16={r[16]}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
