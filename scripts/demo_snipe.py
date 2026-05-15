"""Demo: R2 snipe-bid recommendation for an Ethan session.

Loads real game tables and runs ``compute_snipe_recommendation`` on a
hand-crafted scenario for \u522b\u5885 2407 (private vault, mid-tier
mansion). Prints the full rationale and the one-line UI tooltip.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from bidking_lab.extract.bid_map_table import load_bid_map_table
from bidking_lab.extract.drop_table import load_drop_table
from bidking_lab.extract.item_table import load_item_table
from bidking_lab.inference.observation import (
    QualityBucketObs,
    SessionObs,
)
from bidking_lab.inference.snipe import compute_snipe_recommendation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-id", type=int, default=2407)
    parser.add_argument("--warehouse-cells", type=int, default=132,
                        help="player-observed warehouse total cells")
    parser.add_argument("--wg-cells", type=int, default=22,
                        help="white+green total cells from \u666e\u54c1\u626b\u63cf")
    parser.add_argument("--blue-cells", type=int, default=16,
                        help="blue total cells from \u826f\u54c1\u626b\u63cf")
    parser.add_argument("--trials", type=int, default=3000)
    parser.add_argument("--tol", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260515)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    tables_in = repo_root / "data" / "raw" / "tables"
    print(f"loading tables from {tables_in}")
    maps = load_bid_map_table(tables_in / "BidMap.txt")
    drops = load_drop_table(tables_in / "Drop.txt")
    items = load_item_table(tables_in / "Item.txt")
    print(f"  loaded: maps={len(maps)}, drops={len(drops)}, items={len(items)}\n")

    if args.map_id not in maps:
        print(f"error: map_id={args.map_id} not in BidMap.txt")
        return 1

    session = SessionObs(
        map_id=args.map_id,
        hero="ethan",
        warehouse_total_cells=args.warehouse_cells,
        buckets={
            1: QualityBucketObs(quality=1, total_cells=args.wg_cells),
            3: QualityBucketObs(quality=3, total_cells=args.blue_cells),
        },
    )

    print(f"=== Snipe scenario: map {args.map_id} ({maps[args.map_id].name}) ===")
    print(f"  warehouse_total_cells = {args.warehouse_cells}")
    print(f"  observed: wg={args.wg_cells}, blue={args.blue_cells}, "
          f"low_total={args.wg_cells + args.blue_cells}")
    print(f"  MC: n_trials={args.trials}, tolerance=\u00b1{args.tol} cells\n")

    rec = compute_snipe_recommendation(
        session,
        maps=maps, drops=drops, items=items,
        n_trials=args.trials, warehouse_tolerance=args.tol,
        rng=np.random.default_rng(args.seed),
    )
    if rec is None:
        print("Snipe gating failed; no recommendation surfaced.")
        print("  (Most likely: warehouse < 120 cells, missing low-tier scan,"
              " or too few MC samples in the warehouse tolerance window.)")
        return 0

    print(f"--- MC distribution (n_matching = {rec.n_matching_samples}) ---")
    print(f"  P25  total value : {rec.p25_value:>12,} silver")
    print(f"  P50  (expected)  : {rec.expected_value:>12,} silver")
    print(f"  P75              : {rec.p75_value:>12,} silver")
    print(f"  P90              : {rec.p90_value:>12,} silver\n")
    print(f"--- Recommendation ---")
    print(f"  safe_floor_bid   : {rec.safe_floor_bid:>12,} silver  (P50 \u00d7 0.70)")
    print(f"  snipe_max_bid    : {rec.snipe_max_bid:>12,} silver  (P75 \u00d7 1.15)\n")
    print(f"UI tooltip:  {rec.as_ui_tooltip()}\n")
    print("Rationale (multiline):")
    for line in rec.rationale.splitlines():
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
