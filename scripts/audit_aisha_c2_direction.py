"""Compare Aisha ref total_cells band: B-only vs B+C2 layout shadow.

Local audit only. Scans curated fatbeans rows (same filters as audit_aisha_gap)
where C2 layout hint activates, then compares total_grid_range vs settlement cells.
"""

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events, parse_fatbeans_capture  # noqa: E402

import ahmad_ref_engine as ref_engine  # noqa: E402
from ahmad_ref_engine import AISHA_LAYOUT_GRID_HINT_NOTE, run_reference_engine  # noqa: E402

from audit_aisha_gap import (  # noqa: E402
    FilterStats,
    SAMPLE_ROOTS,
    _build_snapshot,
    _events_through_sort,
    _hero_from_events,
    _map_id_from_events,
    _mid_gap,
    _passes_filters,
    _prefix_sort_id,
    _settlement_breakdown,
    _triplet,
    _truth_in_range,
)


@dataclass(frozen=True)
class C2CompareRow:
    file: str
    audit_round: int
    truth_cells: int
    b_low: int | None
    b_mid: int | None
    b_high: int | None
    b_target: float | None
    b_hit: bool
    b_gap: int | None
    c2_low: int | None
    c2_mid: int | None
    c2_high: int | None
    c2_target: float | None
    c2_hit: bool
    c2_gap: int | None
    footroom_note: str
    direction: str


@contextmanager
def _disable_aisha_layout_hint() -> Iterator[None]:
    original = ref_engine._apply_aisha_layout_grid_hint

    def _noop(**kwargs: Any) -> float | None:
        return kwargs.get("total_grid_target")

    ref_engine._apply_aisha_layout_grid_hint = _noop  # type: ignore[assignment]
    try:
        yield
    finally:
        ref_engine._apply_aisha_layout_grid_hint = original


def _footroom_note(notes: tuple[str, ...] | list[str]) -> str:
    for note in notes:
        text = str(note)
        if text.startswith("aisha_layout_footroom_mult:"):
            return text
    return "-"


def _direction(
    *,
    truth: int,
    b_hit: bool,
    b_gap: int | None,
    c2_hit: bool,
    c2_gap: int | None,
) -> str:
    if not b_hit and c2_hit:
        return "improved_hit"
    if b_hit and not c2_hit:
        return "worsened_miss"
    if b_hit and c2_hit:
        return "unchanged_hit"
    if b_gap is None or c2_gap is None:
        return "unchanged_miss"
    b_abs = abs(int(b_gap))
    c2_abs = abs(int(c2_gap))
    if c2_abs < b_abs:
        return "narrowed_gap"
    if c2_abs > b_abs:
        return "widened_gap"
    return "unchanged_miss"


def _evaluate_snapshot(snapshot: dict[str, Any], *, disable_c2: bool) -> dict[str, Any]:
    if disable_c2:
        with _disable_aisha_layout_hint():
            return run_reference_engine(snapshot, max_combos=50_000).as_dict()
    return run_reference_engine(snapshot, max_combos=50_000).as_dict()


def _compare_row(
    *,
    path: Path,
    events,
    audit_round: int,
    pre_batches: list,
) -> C2CompareRow | None:
    settlement = _settlement_breakdown(events)
    if not settlement:
        return None
    truth_cells = int(settlement["total_cells"])
    prefix_batches = pre_batches[:audit_round]
    sort_id = _prefix_sort_id(prefix_batches)
    prefix_events = _events_through_sort(events, sort_id) if sort_id else events
    snapshot = _build_snapshot(
        hero="aisha",
        events=prefix_events,
        prefix_batches=prefix_batches,
        map_id=_map_id_from_events(events),
    )

    c2_result = _evaluate_snapshot(snapshot, disable_c2=False)
    c2_notes = tuple(str(part) for part in (c2_result.get("notes") or []))
    if not any(AISHA_LAYOUT_GRID_HINT_NOTE in note for note in c2_notes):
        return None

    b_result = _evaluate_snapshot(snapshot, disable_c2=True)
    b_low, b_mid, b_high = _triplet(b_result, "total_grid_range")
    c2_low, c2_mid, c2_high = _triplet(c2_result, "total_grid_range")
    b_evidence = b_result.get("evidence") if isinstance(b_result.get("evidence"), dict) else {}
    c2_evidence = c2_result.get("evidence") if isinstance(c2_result.get("evidence"), dict) else {}
    b_hit = _truth_in_range(truth_cells, b_low, b_mid, b_high)
    c2_hit = _truth_in_range(truth_cells, c2_low, c2_mid, c2_high)
    b_gap = _mid_gap(truth_cells, b_low, b_mid, b_high)
    c2_gap = _mid_gap(truth_cells, c2_low, c2_mid, c2_high)

    return C2CompareRow(
        file=path.name,
        audit_round=audit_round,
        truth_cells=truth_cells,
        b_low=b_low,
        b_mid=b_mid,
        b_high=b_high,
        b_target=_safe_float(b_evidence.get("total_grid_target")),
        b_hit=b_hit,
        b_gap=b_gap,
        c2_low=c2_low,
        c2_mid=c2_mid,
        c2_high=c2_high,
        c2_target=_safe_float(c2_evidence.get("total_grid_target")),
        c2_hit=c2_hit,
        c2_gap=c2_gap,
        footroom_note=_footroom_note(c2_notes),
        direction=_direction(
            truth=truth_cells,
            b_hit=b_hit,
            b_gap=b_gap,
            c2_hit=c2_hit,
            c2_gap=c2_gap,
        ),
    )


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def collect_c2_compare_rows(
    *,
    sample_roots: tuple[Path, ...],
    min_rounds: int,
    min_evidence_score: int,
    max_q6_value: int,
    max_q6_count: int,
    audit_round_override: int,
    limit: int,
) -> list[C2CompareRow]:
    rows: list[C2CompareRow] = []
    stats_filter = FilterStats()
    for root in sample_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("fatbeans*aisha*.json")):
            try:
                events = parse_fatbeans_capture(path)
            except OSError:
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
                min_rounds=min_rounds,
                min_evidence_score=min_evidence_score,
                max_q6_value=max_q6_value,
                max_q6_count=max_q6_count,
                audit_round_override=audit_round_override,
                stats=stats_filter,
            )
            if not ok:
                continue
            row = _compare_row(
                path=path,
                events=events,
                audit_round=audit_round,
                pre_batches=pre_batches,
            )
            if row is None:
                continue
            rows.append(row)
            if limit and len(rows) >= limit:
                return rows
    return rows


def _hit_rate(rows: list[C2CompareRow], *, use_c2: bool) -> float | None:
    if not rows:
        return None
    hits = sum(1 for row in rows if (row.c2_hit if use_c2 else row.b_hit))
    return hits / len(rows)


def _avg_abs_gap(rows: list[C2CompareRow], *, use_c2: bool) -> float | None:
    gaps = [
        abs(int(row.c2_gap if use_c2 else row.b_gap))
        for row in rows
        if (row.c2_gap if use_c2 else row.b_gap) is not None
    ]
    if not gaps:
        return None
    return sum(gaps) / len(gaps)


def format_report(rows: list[C2CompareRow]) -> str:
    lines = [
        "Aisha C2′ direction audit: B-only vs B+C2 layout shadow on curated rows",
        f"rows={len(rows)}",
        "",
    ]
    if not rows:
        lines.append("No curated rows activated C2 layout hint.")
        return "\n".join(lines)

    b_rate = _hit_rate(rows, use_c2=False)
    c2_rate = _hit_rate(rows, use_c2=True)
    b_gap = _avg_abs_gap(rows, use_c2=False)
    c2_gap = _avg_abs_gap(rows, use_c2=True)
    lines.extend(
        [
            "aggregate (C2-active subset only):",
            f"  total_cells hit  B={b_rate:.1%}  B+C2={c2_rate:.1%}" if b_rate is not None else "",
            f"  avg |mid_gap|    B={b_gap:.1f}  B+C2={c2_gap:.1f}"
            if b_gap is not None and c2_gap is not None
            else "",
            "",
            "direction counts:",
        ]
    )
    from collections import Counter

    direction_counts = Counter(row.direction for row in rows)
    for key in (
        "improved_hit",
        "narrowed_gap",
        "unchanged_hit",
        "unchanged_miss",
        "widened_gap",
        "worsened_miss",
    ):
        if direction_counts.get(key):
            lines.append(f"  {key}: {direction_counts[key]}")
    lines.extend(
        [
            "",
            "file | R | truth | B band | B tgt | B hit | C2 band | C2 tgt | C2 hit | dir | footroom",
            "-" * 120,
        ]
    )
    for row in rows:
        lines.append(
            f"{row.file} | {row.audit_round} | {row.truth_cells} | "
            f"[{row.b_low},{row.b_mid},{row.b_high}] | "
            f"{int(row.b_target) if row.b_target is not None else '-'} | "
            f"{'Y' if row.b_hit else 'N'} | "
            f"[{row.c2_low},{row.c2_mid},{row.c2_high}] | "
            f"{int(row.c2_target) if row.c2_target is not None else '-'} | "
            f"{'Y' if row.c2_hit else 'N'} | {row.direction} | {row.footroom_note}"
        )
    lines.extend(
        [
            "",
            "interpretation:",
            "  - improved_hit / narrowed_gap => C2 helps direction on total_cells",
            "  - widened_gap / worsened_miss => C2 too aggressive or wrong round weight",
            "  - unchanged_hit with higher C2 target => shadow widened band without harm",
        ]
    )
    return "\n".join(line for line in lines if line is not None)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-rounds", type=int, default=3)
    parser.add_argument("--min-evidence-score", type=int, default=4)
    parser.add_argument("--max-q6-value", type=int, default=2_000_000)
    parser.add_argument("--max-q6-count", type=int, default=3)
    parser.add_argument("--audit-round", type=int, default=0, help="0=penultimate")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "data/reports/audit_aisha_c2_direction.txt",
    )
    args = parser.parse_args()

    rows = collect_c2_compare_rows(
        sample_roots=SAMPLE_ROOTS,
        min_rounds=args.min_rounds,
        min_evidence_score=args.min_evidence_score,
        max_q6_value=args.max_q6_value,
        max_q6_count=args.max_q6_count,
        audit_round_override=args.audit_round,
        limit=args.limit,
    )
    report = format_report(rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nwrote {args.report}")


if __name__ == "__main__":
    main()
