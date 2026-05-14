"""Parse data/raw/tables/Drop.txt and print summary stats.

Confirms the 608-row parser works end-to-end on real data and surfaces
useful aggregates (pool_type histogram, top categories, entry counts).
"""

from __future__ import annotations

import io
import sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from bidking_lab.extract.drop_table import load_drop_table


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    drop_path = repo_root / "data" / "raw" / "tables" / "Drop.txt"
    if not drop_path.is_file():
        print(f"missing: {drop_path}", file=sys.stderr)
        return 2

    pools = load_drop_table(drop_path)
    print(f"parsed pools: {len(pools)}")

    type_hist = Counter(p.pool_type for p in pools.values())
    print(f"pool_type histogram: {dict(sorted(type_hist.items()))}")

    cat_hist: Counter[int] = Counter()
    entry_counts: list[int] = []
    nonempty_total_weight: list[int] = []
    for pool in pools.values():
        entry_counts.append(len(pool.entries))
        for e in pool.entries:
            cat_hist[e.category] += 1
        if pool.entries:
            nonempty_total_weight.append(pool.total_weight)

    if entry_counts:
        print(
            f"entries per pool: min={min(entry_counts)} max={max(entry_counts)} "
            f"mean={sum(entry_counts) / len(entry_counts):.1f}"
        )
    print("top 10 categories (by entry count):")
    for cat, n in cat_hist.most_common(10):
        print(f"  cat={cat:>4}  entries={n}")

    print("\n3 sample pools:")
    for pool_id in list(pools.keys())[:3]:
        pool = pools[pool_id]
        print(
            f"  pool_id={pool.pool_id} type={pool.pool_type} "
            f"name={pool.name!r} desc={pool.description!r} "
            f"entries={len(pool.entries)} total_weight={pool.total_weight}"
        )
        for e in pool.entries[:2]:
            print(
                f"    -> cat={e.category} item={e.item_id} "
                f"count=[{e.n_min},{e.n_max}] weight={e.weight}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
