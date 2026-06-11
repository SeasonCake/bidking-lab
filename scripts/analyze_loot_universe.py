"""Cross-reference raw Drop.txt entries with Item.txt.

This is a broad table-audit helper: it counts every item referenced by any
Drop pool, including non-map-reachable pools and non-physical rows. It is not
the formal map prior used by simulation; use ``items_droppable.json`` for the
map-reachable physical loot universe.

Writes nothing to disk — pure stdout summary.
"""

from __future__ import annotations

import io
import sys
from collections import Counter, defaultdict
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from bidking_lab.extract.drop_table import load_drop_table
from bidking_lab.extract.tables import load_table_rows

# Tentative Item.txt column indices we trust enough to use for analysis.
COL_ITEM_ID = 0
COL_NAME = 1
COL_DESC = 2
COL_QUALITY = 8
COL_VALUE = 9
COL_PRICE_TIERS = 16


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    tables_in = repo_root / "data" / "raw" / "tables"

    item_rows = load_table_rows(tables_in / "Item.txt")
    drop_pools = load_drop_table(tables_in / "Drop.txt")

    items_by_id: dict[int, list[str]] = {}
    for r in item_rows:
        items_by_id[int(r[COL_ITEM_ID])] = r

    # Drop coverage: which items are referenced, and from how many pools / total weight.
    appearances: dict[int, int] = Counter()
    total_weight: dict[int, int] = Counter()
    pool_count: dict[int, set[int]] = defaultdict(set)
    by_category: dict[int, set[int]] = defaultdict(set)
    for pool in drop_pools.values():
        for e in pool.entries:
            appearances[e.item_id] += 1
            total_weight[e.item_id] += e.weight
            pool_count[e.item_id].add(pool.pool_id)
            by_category[e.category].add(e.item_id)

    referenced_ids = set(appearances.keys())
    known_in_item = {iid for iid in referenced_ids if iid in items_by_id}
    missing = referenced_ids - known_in_item

    print("=" * 72)
    print("RAW DROP REFERENCE UNIVERSE")
    print("=" * 72)
    print(f"Item.txt rows                  : {len(item_rows)}")
    print(f"Drop.txt distinct item_ids     : {len(referenced_ids)}")
    print(f"  ...present in Item.txt       : {len(known_in_item)}")
    print(f"  ...not in Item.txt           : {len(missing)}"
          + ("  (probably hero/skin/avatar ids in other tables)" if missing else ""))

    print()
    print("=" * 72)
    print("QUALITY DISTRIBUTION (col[8])")
    print("=" * 72)
    all_quality = Counter(int(r[COL_QUALITY]) for r in item_rows)
    drop_quality = Counter(
        int(items_by_id[iid][COL_QUALITY]) for iid in known_in_item
    )
    print(f"{'quality':>8}  {'all items':>10}  {'raw refs':>10}")
    for q in sorted(set(all_quality) | set(drop_quality)):
        print(f"{q:>8}  {all_quality.get(q, 0):>10}  {drop_quality.get(q, 0):>10}")

    print()
    print("=" * 72)
    print("VALUE (col[9]) STATS PER QUALITY - among raw Drop refs only")
    print("=" * 72)
    by_q_vals: dict[int, list[int]] = defaultdict(list)
    for iid in known_in_item:
        r = items_by_id[iid]
        q = int(r[COL_QUALITY])
        v = int(r[COL_VALUE])
        by_q_vals[q].append(v)
    print(f"{'q':>3}  {'n':>5}  {'min':>10}  {'median':>10}  {'mean':>12}  {'max':>12}  {'#nonzero':>9}")
    for q in sorted(by_q_vals):
        vals = sorted(by_q_vals[q])
        n = len(vals)
        nz = sum(1 for v in vals if v > 0)
        med = vals[n // 2] if n else 0
        mean = sum(vals) / n if n else 0
        print(
            f"{q:>3}  {n:>5}  {min(vals):>10}  {med:>10}  {mean:>12.1f}  "
            f"{max(vals):>12}  {nz:>9}"
        )

    print()
    print("=" * 72)
    print("SAMPLE RAW DROP REF ITEMS PER QUALITY (sorted by value desc)")
    print("=" * 72)
    for q in sorted(by_q_vals):
        rows_q = [
            (iid, items_by_id[iid][COL_NAME], int(items_by_id[iid][COL_VALUE]),
             appearances[iid], total_weight[iid], len(pool_count[iid]))
            for iid in known_in_item
            if int(items_by_id[iid][COL_QUALITY]) == q
        ]
        rows_q.sort(key=lambda t: (-t[2], t[0]))
        print(f"\n  quality={q}  (n={len(rows_q)})")
        for iid, name, val, appear, tw, npools in rows_q[:6]:
            print(
                f"    id={iid:>7}  name={name[:14]:<14}  "
                f"value_?={val:>10}  appears={appear:>3}  "
                f"pools={npools:>3}  total_weight={tw}"
            )

    print()
    print("=" * 72)
    print("CATEGORIES IN DROP ENTRIES (cat → distinct item_ids)")
    print("=" * 72)
    print(f"{'cat':>5}  {'distinct items':>14}  {'sample item_ids':<40}")
    for cat in sorted(by_category):
        ids = sorted(by_category[cat])
        sample = ", ".join(str(x) for x in ids[:5])
        print(f"{cat:>5}  {len(ids):>14}  {sample}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
