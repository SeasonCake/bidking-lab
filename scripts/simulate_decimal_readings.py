"""Simulate 均格 / 均价 decimal displays from Item.txt and MC sessions.

Usage (from bidking-lab/):

    python scripts/simulate_decimal_readings.py
    python scripts/simulate_decimal_readings.py --trials 5000 --sessions 600

Writes a text report to stdout and optionally ``data/processed/decimal_reading_sim.txt``.
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

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bidking_lab.extract.bid_map_table import load_bid_map_table
from bidking_lab.extract.drop_table import load_drop_table
from bidking_lab.extract.item_table import load_item_table
from bidking_lab.inference.decimal_reading_sim import (
    format_summary_report,
    items_by_quality,
    run_item_pool_simulation,
    run_session_simulation,
)
from bidking_lab.inference.ground_truth import sample_session_truth


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=3000, help="per-quality item draws")
    parser.add_argument("--sessions", type=int, default=500, help="MC session samples")
    parser.add_argument("--warehouse", type=int, default=130)
    parser.add_argument("--other-cells", type=int, default=45, help="non-target bucket cells")
    parser.add_argument("--seed", type=int, default=20260519)
    parser.add_argument(
        "--map-ids",
        type=int,
        nargs="*",
        default=[2401, 2510],
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_ROOT / "data" / "processed" / "decimal_reading_sim.txt",
    )
    args = parser.parse_args()

    raw = _ROOT / "data" / "raw" / "tables"
    items = load_item_table(raw / "Item.txt")
    drops = load_drop_table(raw / "Drop.txt")
    maps = load_bid_map_table(raw / "BidMap.txt")
    by_q = items_by_quality(items)

    print("Item pool sizes by quality:")
    for q in sorted(by_q.keys()):
        if q in (1, 2, 3, 4, 5, 6):
            print(f"  q={q}: {len(by_q[q])} items")

    pool_summary = run_item_pool_simulation(
        by_q,
        trials_per_quality=args.trials,
        warehouse_capacity=args.warehouse,
        other_known_cells=args.other_cells,
        seed=args.seed,
    )
    session_summary = run_session_simulation(
        sample_session_truth=sample_session_truth,
        maps=maps,
        drops=drops,
        items=items,
        map_ids=args.map_ids,
        n_sessions=args.sessions,
        seed=args.seed + 1,
    )

    report = []
    report.append("PART A — random item combinations (explores decimal tails)")
    report.append(format_summary_report(pool_summary))
    report.append("")
    report.append("PART B — sampled MC sessions (realistic warehouse totals)")
    report.append(format_summary_report(session_summary))
    report.append("")
    report.append("Notes for enumeration Phase 2:")
    report.append(
        "  • candidates_for_bucket pre-filters total_cells <= warehouse - other_known."
    )
    report.append(
        "  • avg_cells: use display rule + warehouse cap; integer/half/quarter → many pairs."
    )
    report.append(
        "  • avg_value: fractional cents → integer_total_leak on count; "
        "then tie cells via 均格 or scan."
    )
    report.append(
        "  • Common tails (.12/.17/.43) often admit 1–3 leak counts; "
        "combine with warehouse + max_cells/item."
    )

    text = "\n".join(report)
    print(text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"\n(wrote {args.out})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
