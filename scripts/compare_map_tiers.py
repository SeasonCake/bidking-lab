"""Compare tier-2 / tier-3 / tier-4 maps of the same theme side by side.

Answers the question: does difficulty change drop composition, or only
the bidding economics (entry fee / budget / item count)?
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from bidking_lab.extract.bid_map_table import load_bid_map_table


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    maps = load_bid_map_table(repo_root / "data" / "raw" / "tables" / "BidMap.txt")

    by_name: dict[str, list] = {}
    for m in maps.values():
        by_name.setdefault(m.name.strip(), []).append(m)

    print(
        f"{'theme':<24}  {'tier':>4}  {'pool':>6}  {'items':>10}  "
        f"{'rounds':>6}  {'fee':>10}  {'budget':>12}"
    )
    print("-" * 86)

    for name, group in sorted(by_name.items()):
        if len(group) < 2:
            continue  # not a multi-tier theme
        group.sort(key=lambda m: m.map_id)
        for m in group:
            tier = str(m.map_id)[0]
            print(
                f"{name[:24]:<24}  {tier:>4}  {m.drop_pool_id:>6}  "
                f"{m.items_per_session_min:>4}-{m.items_per_session_max:<4}  "
                f"{m.rounds_total:>6}  {m.entry_fee_silver:>10,}  "
                f"{m.starting_budget_silver:>12,}"
            )
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
