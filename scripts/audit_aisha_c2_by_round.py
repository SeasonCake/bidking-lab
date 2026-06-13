"""Round-stratified layout batch metrics (local audit only)."""

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

from audit_aisha_c2_batch import (  # noqa: E402
    SAMPLE_ROOTS,
    VARIANTS,
    _variant_direction,
    collect_batch_rows,
)


def _hit_rate(rows, variant: str) -> float:
    if not rows:
        return 0.0
    hits = sum(1 for row in rows if row.by_variant[variant][3])
    return hits / len(rows)


def _avg_gap(rows, variant: str) -> float:
    gaps = [abs(row.by_variant[variant][4]) for row in rows if row.by_variant[variant][4] is not None]
    return sum(gaps) / len(gaps) if gaps else 0.0


def _band_delta(rows) -> tuple[int, int]:
    improved = worsened = 0
    for row in rows:
        _, _, _, b_hit, b_gap = row.by_variant["b_only"]
        _, _, _, band_hit, band_gap = row.by_variant["c2_band"]
        direction = _variant_direction(
            truth=row.truth_cells,
            b_hit=b_hit,
            b_gap=b_gap,
            v_hit=band_hit,
            v_gap=band_gap,
        )
        if direction == "improved_hit":
            improved += 1
        elif direction == "worsened_miss":
            worsened += 1
    return improved, worsened


def format_report(*, cohort: str, rows) -> str:
    label = "full curated" if cohort == "all" else "C2-eligible"
    lines = [
        f"Aisha layout metrics by audit_round ({label}, n={len(rows)})",
        "",
        "round | n  | b_hit | band_hit | delta_pp | band_improved | band_worsened | b_avg|gap| | band_avg|gap|",
        "-" * 95,
    ]
    by_round: dict[int, list] = defaultdict(list)
    for row in rows:
        by_round[row.audit_round].append(row)

    total_imp = total_wors = 0
    for rnd in sorted(by_round):
        sub = by_round[rnd]
        b_hr = _hit_rate(sub, "b_only") * 100
        band_hr = _hit_rate(sub, "c2_band") * 100
        imp, wors = _band_delta(sub)
        total_imp += imp
        total_wors += wors
        lines.append(
            f"R{rnd:2d}  | {len(sub):3d} | {b_hr:5.1f}% | {band_hr:7.1f}% | "
            f"{band_hr - b_hr:+6.1f} | {imp:13d} | {wors:13d} | "
            f"{_avg_gap(sub, 'b_only'):11.1f} | {_avg_gap(sub, 'c2_band'):13.1f}"
        )

    lines.extend(
        [
            "-" * 95,
            f"ALL   | {len(rows):3d} | {_hit_rate(rows, 'b_only') * 100:5.1f}% | "
            f"{_hit_rate(rows, 'c2_band') * 100:7.1f}% | "
            f"{(_hit_rate(rows, 'c2_band') - _hit_rate(rows, 'b_only')) * 100:+6.1f} | "
            f"{total_imp:13d} | {total_wors:13d} | "
            f"{_avg_gap(rows, 'b_only'):11.1f} | {_avg_gap(rows, 'c2_band'):13.1f}",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", choices=("eligible", "all"), default="all")
    parser.add_argument("--min-rounds", type=int, default=3)
    parser.add_argument("--min-evidence-score", type=int, default=4)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "data/reports/audit_aisha_c2_by_round.txt",
    )
    args = parser.parse_args()

    rows = collect_batch_rows(
        sample_roots=SAMPLE_ROOTS,
        min_rounds=args.min_rounds,
        min_evidence_score=args.min_evidence_score,
        max_q6_value=2_000_000,
        max_q6_count=3,
        audit_round_override=0,
        limit=0,
        cohort=args.cohort,
    )
    report = format_report(cohort=args.cohort, rows=rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nwrote {args.report}")


if __name__ == "__main__":
    main()
