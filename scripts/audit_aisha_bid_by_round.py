"""Aisha balanced-bid audit by round cohort: baseline vs D1 shadow vs D1 apply (local only).

Compares three engine modes on the same curated rows:
  off     — layout off, D1 off (legacy audit baseline)
  shadow  — live defaults via prepare_reference_engine_snapshot (band + D1 notes; balanced unchanged)
  apply   — explicit audit_aisha_d1_mode=apply (Phase 2 simulation; not live)

Local audit only — not shipped in Hero Ref packages.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events, parse_fatbeans_capture  # noqa: E402

from ahmad_ref_engine import (  # noqa: E402
    AISHA_D1_APPLY_Q6_DISCOUNT_NOTE,
    AISHA_D1_SHADOW_Q6_DISCOUNT_NOTE,
    prepare_reference_engine_snapshot,
    run_reference_engine,
)

from audit_aisha_gap import (  # noqa: E402
    SAMPLE_ROOTS,
    FilterStats,
    _build_snapshot,
    _events_through_sort,
    _hero_from_events,
    _map_id_from_events,
    _passes_filters,
    _prefix_sort_id,
    _settlement_breakdown,
)

MODES = ("off", "shadow", "apply")


@dataclass(frozen=True)
class BidRow:
    file: str
    audit_round: int
    truth_value: int
    by_mode: dict[str, tuple[int | None, bool, int | None, bool]]


def _balanced_hit(truth: int, balanced: int | None) -> bool:
    if balanced is None or truth <= 0:
        return False
    return int(balanced * 0.85) <= truth <= int(balanced * 1.15)


def _balanced_direction(truth: int, balanced: int | None) -> str:
    if balanced is None or truth <= 0:
        return "na"
    if truth > int(balanced * 1.15):
        return "under"
    if truth < int(balanced * 0.85):
        return "over"
    return "hit"


def _evaluate_snapshot(snapshot: dict[str, Any], *, mode: str) -> dict[str, Any]:
    payload = dict(snapshot)
    if mode == "off":
        payload["audit_aisha_layout_mode"] = "off"
        payload["audit_aisha_d1_mode"] = "off"
    elif mode == "shadow":
        payload = prepare_reference_engine_snapshot(payload)
    elif mode == "apply":
        payload = prepare_reference_engine_snapshot(payload)
        payload["audit_aisha_d1_mode"] = "apply"
    else:
        raise ValueError(mode)
    return run_reference_engine(payload, max_combos=50_000).as_dict()


def _collect_rows(*, limit: int) -> tuple[list[BidRow], FilterStats]:
    stats = FilterStats()
    rows: list[BidRow] = []
    for root in SAMPLE_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("fatbeans*aisha*.json")):
            try:
                events = parse_fatbeans_capture(path)
            except OSError:
                stats.reasons["parse_error"] += 1
                continue
            hero = _hero_from_events(events)
            pre_batches = [b for b in live_batches_from_fatbeans_events(events) if b.phase != "settled"]
            settlement = _settlement_breakdown(events)
            ok, audit_round = _passes_filters(
                path=path,
                events=events,
                hero=hero,
                pre_batches=pre_batches,
                settlement=settlement,
                min_rounds=3,
                min_evidence_score=4,
                max_q6_value=2_000_000,
                max_q6_count=3,
                audit_round_override=0,
                stats=stats,
            )
            if not ok or not settlement:
                continue
            prefix_batches = pre_batches[:audit_round]
            sort_id = _prefix_sort_id(prefix_batches)
            prefix_events = _events_through_sort(events, sort_id) if sort_id else events
            snapshot = _build_snapshot(
                hero="aisha",
                events=prefix_events,
                prefix_batches=prefix_batches,
                map_id=_map_id_from_events(events),
            )
            truth_value = int(settlement["total_value"])
            by_mode: dict[str, tuple[int | None, bool, int | None, bool]] = {}
            for mode in MODES:
                result = _evaluate_snapshot(snapshot, mode=mode)
                balanced_raw = result.get("balanced")
                try:
                    balanced = int(balanced_raw) if balanced_raw not in (None, "") else None
                except (TypeError, ValueError):
                    balanced = None
                hit = _balanced_hit(truth_value, balanced)
                gap = truth_value - balanced if balanced is not None else None
                notes = result.get("notes") or ()
                has_d1_note = any(
                    str(note).startswith(prefix)
                    for note in notes
                    for prefix in (AISHA_D1_SHADOW_Q6_DISCOUNT_NOTE, AISHA_D1_APPLY_Q6_DISCOUNT_NOTE)
                )
                by_mode[mode] = (balanced, hit, gap, has_d1_note)
            rows.append(
                BidRow(
                    file=path.name,
                    audit_round=audit_round,
                    truth_value=truth_value,
                    by_mode=by_mode,
                )
            )
            if limit and len(rows) >= limit:
                return rows, stats
    return rows, stats


def _summarize(rows: list[BidRow], *, mode: str) -> dict[str, float | int]:
    applicable = [row for row in rows if row.by_mode[mode][0] is not None]
    n = len(applicable)
    if not n:
        return {"n": 0, "hit_pct": 0.0, "under_pct": 0.0, "over_pct": 0.0, "avg_abs_gap": 0.0}
    hits = sum(1 for row in applicable if row.by_mode[mode][1])
    under = sum(1 for row in applicable if _balanced_direction(row.truth_value, row.by_mode[mode][0]) == "under")
    over = sum(1 for row in applicable if _balanced_direction(row.truth_value, row.by_mode[mode][0]) == "over")
    gaps = [abs(row.by_mode[mode][2] or 0) for row in applicable if row.by_mode[mode][2] is not None]
    return {
        "n": n,
        "hit_pct": hits / n * 100.0,
        "under_pct": under / n * 100.0,
        "over_pct": over / n * 100.0,
        "avg_abs_gap": sum(gaps) / len(gaps) if gaps else 0.0,
    }


def format_report(rows: list[BidRow], *, elapsed_s: float) -> str:
    lines = [
        "audit_aisha_bid_by_round (curated penultimate, ±15% balanced vs settlement total value)",
        f"rows={len(rows)} elapsed_s={elapsed_s:.1f}",
        "",
        "modes:",
        "  off     layout=off d1=off (audit baseline)",
        "  shadow  prepare_reference_engine_snapshot (band + d1 notes; balanced same as off)",
        "  apply   d1 apply simulation (Phase 2; NOT live)",
        "",
    ]
    all_off = _summarize(rows, mode="off")
    all_shadow = _summarize(rows, mode="shadow")
    all_apply = _summarize(rows, mode="apply")
    lines.extend(
        [
            "ALL curated:",
            f"  off     hit={all_off['hit_pct']:.1f}% under={all_off['under_pct']:.1f}% "
            f"over={all_off['over_pct']:.1f}% avg|gap|={all_off['avg_abs_gap']:.0f}",
            f"  shadow  hit={all_shadow['hit_pct']:.1f}% (balanced unchanged vs off)",
            f"  apply   hit={all_apply['hit_pct']:.1f}% under={all_apply['under_pct']:.1f}% "
            f"over={all_apply['over_pct']:.1f}% avg|gap|={all_apply['avg_abs_gap']:.0f} "
            f"Δhit={all_apply['hit_pct'] - all_off['hit_pct']:+.1f}pp",
            "",
            "round | n  | off_hit | apply_hit | apply_Δ | off_under% | apply_under%",
            "-" * 78,
        ]
    )
    by_round: dict[int, list[BidRow]] = defaultdict(list)
    for row in rows:
        by_round[row.audit_round].append(row)
    for rnd in sorted(by_round):
        sub = by_round[rnd]
        off = _summarize(sub, mode="off")
        apply = _summarize(sub, mode="apply")
        lines.append(
            f"R{rnd:2d}  | {off['n']:3d} | {off['hit_pct']:6.1f}% | {apply['hit_pct']:8.1f}% | "
            f"{apply['hit_pct'] - off['hit_pct']:+6.1f}pp | {off['under_pct']:9.1f}% | {apply['under_pct']:11.1f}%"
        )
    improved = sum(
        1
        for row in rows
        if not row.by_mode["off"][1]
        and row.by_mode["apply"][1]
        and row.by_mode["off"][0] is not None
        and row.by_mode["apply"][0] is not None
    )
    worsened = sum(
        1
        for row in rows
        if row.by_mode["off"][1]
        and not row.by_mode["apply"][1]
        and row.by_mode["off"][0] is not None
        and row.by_mode["apply"][0] is not None
    )
    shadow_note_rows = sum(1 for row in rows if row.by_mode["shadow"][3])
    lines.extend(
        [
            "",
            f"apply vs off: improved_hit={improved} worsened_hit={worsened}",
            f"shadow d1 notes present: {shadow_note_rows}/{len(rows)} rows",
            "",
            "interpretation:",
            "  - balanced miss ~83% is structural (nest prior vs inventory truth); cells fix comes first",
            "  - shadow mode is live-safe diagnostics only; apply mode is Phase 2 gate input",
            "  - do not promote apply until good_regression + per-round cohort review",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "data/reports/audit_aisha_bid_by_round.txt")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    started = time.perf_counter()
    rows, stats = _collect_rows(limit=args.limit)
    elapsed = time.perf_counter() - started
    report = format_report(rows, elapsed_s=elapsed)
    report += f"\n\nfilter_scanned={stats.scanned}\n"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nwrote {args.report}")


if __name__ == "__main__":
    main()
