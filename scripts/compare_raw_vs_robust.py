"""Quick comparison: raw E[session value] vs robust (small-rare trimmed).

Prints a side-by-side table for the representative high-tier leaf maps:
how much of the raw expected value is "phantom long tail" that the player
cannot realistically plan around.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bidking_lab.extract.bid_map_table import load_bid_map_table
from bidking_lab.extract.drop_table import load_drop_table
from bidking_lab.extract.item_table import load_item_table
from bidking_lab.simulation.basic_mc import flatten_pool
from bidking_lab.simulation.robust_value import (
    is_confusable_long_tail,
    robust_session_value,
)

TABLES = ROOT / "data" / "raw" / "tables"


def raw_session_value(fp, items, items_per_session):
    return items_per_session * sum(p * items[iid].value for iid, p in zip(fp.item_ids, fp.probabilities))


def main():
    maps = load_bid_map_table(TABLES / "BidMap.txt")
    drops = load_drop_table(TABLES / "Drop.txt")
    items = load_item_table(TABLES / "Item.txt")

    # Top-tier leaf map per theme
    sample_maps = [2107, 2207, 2310, 2410, 2510, 2407, 2507, 4407, 4507]

    print(f"{'map':>5s}  {'name':<14s}  {'items/sess':>10s}  {'raw E':>12s}  {'robust E':>12s}  {'trim%':>6s}  {'trimmed items':<30s}")
    print("-" * 110)
    for mid in sample_maps:
        bm = maps.get(mid)
        if bm is None:
            continue
        if bm.sub_pool_weights:
            continue
        fp = flatten_pool(bm.drop_pool_id, drops, items)
        ips = (bm.items_per_session_min + bm.items_per_session_max) / 2
        raw = raw_session_value(fp, items, ips)
        robust = robust_session_value(fp, items, ips)
        trimmed = [items[iid].name for iid in fp.item_ids if is_confusable_long_tail(items[iid])]
        pct = (raw - robust) / raw * 100 if raw else 0.0
        print(
            f"{mid:>5d}  {bm.name[:14]:<14s}  {ips:>10.1f}  "
            f"{raw:>12,.0f}  {robust:>12,.0f}  {pct:>5.1f}%  {', '.join(trimmed[:4]):<30s}"
        )


if __name__ == "__main__":
    main()
