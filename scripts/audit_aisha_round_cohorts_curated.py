"""Fixed-round cohort metrics using curated pool only (~2 min).

Reuses audit_aisha_gap filters; evaluates at --audit-round 1|2|3|4|5.
Reports off vs band cells/items only (Phase 1).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from audit_aisha_c2_batch import (  # noqa: E402
    SAMPLE_ROOTS,
    VARIANTS,
    _summarize_variant,
    _variant_direction,
    collect_batch_rows,
)

DEFENSE = {1: "2.0× defense", 2: "1.6×", 3: "1.3×", 4: "1.1×", 5: "competitive"}


def run_cohort(
    *,
    eval_round: int,
    min_rounds: int,
    min_evidence: int,
) -> dict[str, object]:
    rows = collect_batch_rows(
        sample_roots=SAMPLE_ROOTS,
        min_rounds=min_rounds,
        min_evidence_score=min_evidence,
        max_q6_value=2_000_000,
        max_q6_count=3,
        audit_round_override=eval_round,
        limit=0,
        cohort="all",
    )
    b = _summarize_variant(rows, "b_only")
    band = _summarize_variant(rows, "c2_band")
    return {"rows": rows, "b": b, "band": band}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "data/reports/audit_aisha_round_cohorts_fast.txt")
    args = parser.parse_args()

    specs = [
        ("R1", 1, 1, 0),
        ("R2", 2, 2, 0),
        ("R3", 3, 3, 1),
        ("R4", 4, 4, 4),
        ("R5", 5, 5, 4),
    ]
    lines = [
        "Aisha round-cohort audit (curated pool, fixed eval round via audit_aisha_c2_batch)",
        "Phase 1: cells/items off vs band | Phase 2 balanced deferred (D1)",
        "",
    ]
    t0 = time.monotonic()
    r4_rows = r5_rows = None
    for label, rnd, min_r, min_ev in specs:
        data = run_cohort(eval_round=rnd, min_rounds=min_r, min_evidence=min_ev)
        rows = data["rows"]
        b, band = data["b"], data["band"]
        if rnd == 4:
            r4_rows = rows
        if rnd == 5:
            r5_rows = rows
        lines.append(f"## {label} — eval at round {rnd} ({DEFENSE.get(rnd, '')})")
        lines.append(f"rows={len(rows)}")
        lines.append(
            f"  cells hit: off={b.hit_rate:.1%} band={band.hit_rate:.1%} "
            f"(+{band.improved_hit}/-{band.worsened_miss}) | avg|gap| off={b.avg_abs_gap:.1f} band={band.avg_abs_gap:.1f}"
        )
        lines.append(f"  (items/balanced: see audit_aisha_gap at penultimate for Phase 2 baseline)")
        lines.append("")

    lines.extend(["## R4-R5 combined (primary Phase 1 gate)", ""])
    if r4_rows is not None and r5_rows is not None:
        combined = list({(r.file, r.audit_round): r for r in r4_rows + r5_rows}.values())
        hits_off = sum(1 for r in combined if r.b_hit) / len(combined) if combined else 0
        hits_band = sum(
            1 for r in combined if r.by_variant["c2_band"][3]
        ) / len(combined) if combined else 0
        imp = sum(
            1
            for r in combined
            if not r.b_hit and r.by_variant["c2_band"][3]
        )
        wors = sum(
            1
            for r in combined
            if r.b_hit and not r.by_variant["c2_band"][3]
        )
        lines.append(f"rows={len(combined)} (R4 n={len(r4_rows)}, R5 n={len(r5_rows)})")
        lines.append(
            f"  cells hit: off={hits_off:.1%} band={hits_band:.1%} (+{imp}/-{wors})"
        )
    lines.append("")
    lines.append(f"runtime={time.monotonic()-t0:.0f}s")
    lines.append("See also: audit_aisha_c2_batch_full.txt (penultimate, 148 rows, band 43.9%)")

    report = "\n".join(lines)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"wrote {args.report}")


if __name__ == "__main__":
    main()
