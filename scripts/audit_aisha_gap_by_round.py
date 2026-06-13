"""Gap audit metrics stratified by audit_round (local audit only)."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "external_references" / "ahmad_live_reference_lab" / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "external_references" / "ahmad_live_reference_lab" / "src"))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from audit_aisha_gap import SAMPLE_ROOTS, audit_aisha_gaps  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "data/reports/audit_aisha_gap_by_round.txt")
    args = parser.parse_args()

    rows, _stats = audit_aisha_gaps(
        sample_roots=SAMPLE_ROOTS,
        min_rounds=3,
        min_evidence_score=4,
        max_q6_value=2_000_000,
        max_q6_count=3,
        audit_round_override=0,
        limit=0,
    )
    by_round: dict[int, list] = defaultdict(list)
    for row in rows:
        by_round[row.audit_round].append(row)

    lines = [
        "audit_aisha_gap by audit_round (engine default layout=off)",
        f"rows={len(rows)}",
        "",
        "round | n  | total_cells_miss | avg|cells_gap| | balanced_miss | q6_value_miss | q5_cells_miss",
        "-" * 90,
    ]
    for rnd in sorted(by_round):
        sub = by_round[rnd]
        n = len(sub)
        tc_miss = sum(1 for row in sub if row.count_miss.get("total_cells")) / n * 100
        tc_gaps = [abs(row.gaps.get("total_cells") or 0) for row in sub if row.gaps.get("total_cells") is not None]
        bal = sum(1 for row in sub if row.bid_balanced_miss) / n * 100
        q6v = sum(1 for row in sub if row.q6_value_miss) / n * 100
        q5c = sum(1 for row in sub if row.cells_miss.get("q5") is True) / n * 100
        lines.append(
            f"R{rnd:2d}  | {n:3d} | {tc_miss:15.1f}% | {sum(tc_gaps)/len(tc_gaps):13.1f} | "
            f"{bal:12.1f}% | {q6v:12.1f}% | {q5c:12.1f}%"
        )

    n = len(rows)
    tc_miss = sum(1 for row in rows if row.count_miss.get("total_cells")) / n * 100
    lines.append("-" * 90)
    lines.append(f"ALL   | {n:3d} | {tc_miss:15.1f}% | (see audit_aisha_gap.txt for full breakdown)")

    report = "\n".join(lines)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nwrote {args.report}")


if __name__ == "__main__":
    main()
