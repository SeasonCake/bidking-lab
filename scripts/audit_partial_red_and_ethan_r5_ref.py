"""Audit partial-known red value floors and Ethan R5 generic ref on real samples."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bidking_lab.live.fatbeans import (
    _hero_mode_from_state,
    live_batches_from_fatbeans_events,
    parse_fatbeans_capture,
)
from bidking_lab.live.monitor import (
    _ahmad_ref_inputs_from_batches,
    _public_info_rows,
    _skill_reveal_rows,
)
from bidking_lab.live.replay import final_truth_from_events
from ahmad_ref_engine import extract_evidence, run_reference_engine

SAMPLE_ROOTS = (
    ROOT / "data/samples/fatbeans",
    ROOT / "data/samples/fatbeans_activity_20260605_shipwreck",
)
DEFAULT_REPORT_PATH = ROOT / "data/reports/audit_cross_hero_q6_value.txt"


@dataclass(frozen=True)
class CrossHeroQ6Row:
    file: str
    hero: str
    pattern: str
    known_count: int
    known_max: int
    known_sum: float
    q6_lock: int
    info_ids: str
    rv10: int | None
    rv50: int | None
    rv90: int | None
    settle_q6: str
    rv50_gap_known: str
    rv10_above_known: bool


def _settlement_quality_totals(events) -> dict[int, dict[str, int]]:
    for state in reversed(events.states):
        if not state.inventory_items:
            continue
        counts: Counter[int] = Counter()
        cells: Counter[int] = Counter()
        for item in state.inventory_items:
            q = int(item.quality or 0)
            if q <= 0:
                continue
            counts[q] += 1
            cells[q] += int(item.cells or 0)
        return {
            q: {"count": counts[q], "cells": cells[q]}
            for q in sorted(counts)
        }
    return {}


def _partial_q6_reveals_from_events(events) -> list[dict]:
    rows: list[dict] = []
    for state in events.states:
        for info in state.public_infos:
            for item in info.observed_items:
                if int(item.quality or 0) != 6:
                    continue
                val = item.value
                if val is None or int(val) <= 0:
                    continue
                rows.append(
                    {
                        "sort": state.sort_id,
                        "info_id": info.info_id,
                        "value": int(val),
                        "cells": item.cells,
                        "runtime_id": item.runtime_id,
                    }
                )
    return rows


def _build_ref_snapshot(
    *,
    hero: str,
    events,
    structured_ref_inputs: dict | None = None,
) -> dict:
    batches = live_batches_from_fatbeans_events(events)
    pre_batches = [b for b in batches if b.phase != "settled"]
    bridge = _ahmad_ref_inputs_from_batches(pre_batches, hero=hero)
    return {
        "ui_contract": {
            "context": {"hero": hero, "phase": "bidding"},
            "constraints": {"public_info": {}},
        },
        "structured_ref_inputs": structured_ref_inputs or bridge or {},
        "public_info_rows": _public_info_rows(events, {}),
        "skill_reveals": _skill_reveal_rows(events, {}),
        "skill_reveal_rows": _skill_reveal_rows(events, {}),
        "action_result_rows": [],
    }


def _pct_gap(estimate: int | None, truth: int) -> str:
    if estimate is None or truth <= 0:
        return "n/a"
    return f"{(estimate - truth) / truth * 100:+.1f}%"


def _hero_from_events(events) -> str:
    for state in reversed(events.states):
        hero = _hero_mode_from_state(state)
        if hero:
            return hero
    return "unknown"


def _classify_q6_value_pattern(evidence) -> str:
    q6_known = evidence.quality_value_floor_item_counts.get("q6", 0)
    q6_lock = evidence.fixed_counts.get("q6") or evidence.min_counts.get("q6") or 0
    if q6_known > 0 and q6_lock and q6_lock > q6_known:
        return "partial"
    if q6_known > 0 and q6_lock == q6_known:
        return "full_known"
    if q6_known >= 1 and not q6_lock:
        return "single_no_lock"
    return "other"


def _q6_public_value_summary(events) -> tuple[list[int], list[int], bool]:
    values: list[int] = []
    info_ids: list[int] = []
    for state in events.states:
        for info in state.public_infos:
            for item in info.observed_items:
                if int(item.quality or 0) != 6:
                    continue
                val = item.value
                if val is None or int(val) <= 0:
                    continue
                values.append(int(val))
                info_ids.append(int(info.info_id))
    return values, info_ids, bool(values)


def _iter_q6_value_sample_paths() -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for root in SAMPLE_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            key = str(path.resolve())
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
    return paths


def _collect_cross_hero_q6_rows(limit: int | None = None) -> list[CrossHeroQ6Row]:
    rows: list[CrossHeroQ6Row] = []
    paths = _iter_q6_value_sample_paths()
    if limit is not None:
        paths = paths[:limit]
    for path in paths:
        try:
            events = parse_fatbeans_capture(path)
        except OSError:
            continue
        public_values, public_info_ids, has_q6_value = _q6_public_value_summary(events)
        if not has_q6_value:
            continue
        hero = _hero_from_events(events)
        snap = _build_ref_snapshot(hero=hero, events=events)
        evidence = extract_evidence(snap)
        result = run_reference_engine(snap, max_combos=60_000).as_dict()
        rv10, rv50, rv90 = result["red_value_range"]
        known_count = evidence.quality_value_floor_item_counts.get("q6", 0) or len(public_values)
        known_sum = float(evidence.quality_value_floors.get("q6", 0.0) or sum(public_values))
        known_max = max(public_values) if public_values else 0
        q6_lock = evidence.fixed_counts.get("q6") or evidence.min_counts.get("q6") or 0
        truth_q6 = _settlement_quality_totals(events).get(6)
        settle_q6 = (
            f"{truth_q6['count']}c/{truth_q6['cells']}g"
            if truth_q6
            else "?"
        )
        unique_info_ids = sorted(set(public_info_ids))
        info_label = ",".join(str(i) for i in unique_info_ids[:3])
        if len(unique_info_ids) > 3:
            info_label += f"+{len(unique_info_ids) - 3}"
        rows.append(
            CrossHeroQ6Row(
                file=path.name,
                hero=hero,
                pattern=_classify_q6_value_pattern(evidence),
                known_count=int(known_count),
                known_max=int(known_max),
                known_sum=known_sum,
                q6_lock=int(q6_lock),
                info_ids=info_label or "?",
                rv10=rv10,
                rv50=rv50,
                rv90=rv90,
                settle_q6=settle_q6,
                rv50_gap_known=_pct_gap(rv50, int(round(known_sum))) if known_sum > 0 else "n/a",
                rv10_above_known=rv10 is not None and rv10 > known_max,
            )
        )
    return rows


def _format_cross_hero_table(rows: list[CrossHeroQ6Row]) -> str:
    buffer = StringIO()
    print_fn = buffer.write

    def emit(line: str = "") -> None:
        print_fn(line + "\n")

    emit("=== Cross-hero public q6 value audit ===")
    emit(
        f"scanned roots: {', '.join(str(p.relative_to(ROOT)) for p in SAMPLE_ROOTS if p.exists())}"
    )
    emit(f"samples with public q6 value: {len(rows)}")
    if not rows:
        emit("No q6-value samples found.")
        return buffer.getvalue()

    by_hero = Counter(row.hero for row in rows)
    by_pattern = Counter(row.pattern for row in rows)
    emit(f"by hero: {dict(sorted(by_hero.items()))}")
    emit(f"by pattern: {dict(sorted(by_pattern.items()))}")
    emit(
        "pattern legend: partial=known value + q6 lock>known;"
        " full_known=all q6 values known;"
        " single_no_lock=one value, no q6 count lock"
    )
    emit()

    header = (
        f"{'file':<52} {'hero':<8} {'pattern':<16} {'known':<14} {'q6':<4} "
        f"{'rv10':>8} {'rv50':>8} {'rv90':>8} {'settle':<10} {'rv50_vs_known':<12} ok"
    )
    emit(header)
    emit("-" * len(header))
    for row in sorted(rows, key=lambda item: (item.hero, item.pattern, item.file)):
        known_label = f"{row.known_count}@{row.known_max}"
        emit(
            f"{row.file:<52} {row.hero:<8} {row.pattern:<16} {known_label:<14} "
            f"{row.q6_lock:<4} "
            f"{row.rv10 or 0:>8} {row.rv50 or 0:>8} {row.rv90 or 0:>8} "
            f"{row.settle_q6:<10} {row.rv50_gap_known:<12} "
            f"{'Y' if row.rv10_above_known else 'N'}"
        )

    partial = [row for row in rows if row.pattern == "partial"]
    partial_old_bug = [
        row
        for row in partial
        if row.rv10 is not None and row.rv10 <= row.known_max + 1000
    ]
    rv10_ok = sum(1 for row in rows if row.rv10_above_known)
    rv10_at_known = sum(
        1
        for row in rows
        if row.rv10 is not None and row.rv10 <= row.known_max + 1000
    )
    emit()
    emit(
        f"summary: rv10 above max known value {rv10_ok}/{len(rows)};"
        f" rv10 pinned at known value {rv10_at_known}/{len(rows)};"
        f" partial cases {len(partial)}"
    )
    if partial:
        emit(
            f"partial old-bug check (rv10 <= known+1k): "
            f"{len(partial_old_bug)}/{len(partial)}"
        )
        emit("partial samples:")
        for row in partial:
            emit(
                f"  {row.file} known={row.known_count}@{row.known_max} "
                f"q6={row.q6_lock} rv={row.rv10}/{row.rv50}/{row.rv90} settle={row.settle_q6}"
            )
    else:
        emit("partial samples: none in library (need live Ahmed 2408 R3-style capture)")
    emit("note: settlement column is q6 count/cells only; item values are not in fatbeans inventory.")
    emit()
    return buffer.getvalue()


def audit_cross_hero_q6_value_table(
    *,
    limit: int | None = None,
    report_path: Path | None = DEFAULT_REPORT_PATH,
) -> None:
    rows = _collect_cross_hero_q6_rows(limit=limit)
    text = _format_cross_hero_table(rows)
    print(text, end="")
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text, encoding="utf-8")
        print(f"report written: {report_path.relative_to(ROOT)}")


def audit_synthetic_390k() -> None:
    snap = {
        "ui_contract": {
            "context": {"hero": "ahmed", "map_id": 2408, "phase": "bidding"},
            "constraints": {"public_info": {}},
        },
        "structured_ref_inputs": {
            "total_count": 50,
            "fixed_counts": {"q1": 10, "q3": 24, "q4": 10, "q5": 4, "q6": 2},
            "quality_cells": {"q1": 15, "q3": 49, "q4": 48, "q5": 24},
            "avg_cells": {"q3": 49 / 24, "q4": 48 / 10, "q5": 24 / 4},
        },
        "public_info_rows": [
            {
                "info_id": 200023,
                "revealed_items_detail": [
                    {
                        "runtime_id": 1,
                        "quality": 6,
                        "value": 390000,
                        "shape_code": 11,
                        "cells": 1,
                    }
                ],
            }
        ],
    }
    result = run_reference_engine(snap, max_combos=60_000).as_dict()
    print("=== Synthetic Ahmed-like (1 red @390k, q6=2) ===")
    print("red_value_range:", result["red_value_range"])
    print(
        "total bid:",
        result["conservative"],
        result["balanced"],
        result["aggressive"],
    )
    print()


def audit_ahmed_partial_red(limit: int = 120) -> None:
    files = sorted((ROOT / "data/samples/fatbeans").glob("*ahmed*.json"))[:limit]
    hits: list[dict] = []
    for path in files:
        try:
            events = parse_fatbeans_capture(path)
        except OSError:
            continue
        truth_q = _settlement_quality_totals(events).get(6)
        if truth_q is None:
            continue
        reveals = _partial_q6_reveals_from_events(events)
        if not reveals:
            continue
        known_value = max(r["value"] for r in reveals)
        known_count = len({r["runtime_id"] for r in reveals if r["runtime_id"] is not None}) or len(reveals)
        snap = _build_ref_snapshot(hero="ahmed", events=events)
        evidence = extract_evidence(snap)
        q6_fixed = evidence.fixed_counts.get("q6") or evidence.min_counts.get("q6") or 0
        if q6_fixed <= known_count:
            continue
        result = run_reference_engine(snap, max_combos=60_000).as_dict()
        rv10, rv50, rv90 = result["red_value_range"]
        min_floor = known_value + 160_000 * (q6_fixed - known_count)
        hits.append(
            {
                "file": path.name,
                "known": f"{known_count}@{known_value}",
                "q6_fixed": q6_fixed,
                "q6_truth": f"{truth_q['count']}c/{truth_q['cells']}g",
                "red_range": (rv10, rv50, rv90),
                "default_floor": min_floor,
                "rv10_ok": rv10 is not None and rv10 > known_value and rv10 >= min_floor * 0.95,
                "old_bug": rv10 is not None and rv10 <= known_value + 1000,
            }
        )
    print(f"=== Ahmed partial-q6 value reveals ({len(hits)} / {len(files)} scanned) ===")
    if not hits:
        print("No partial known-red cases in scanned Ahmed samples.")
        print()
        return
    for row in hits[:8]:
        print(row)
    above_floor = sum(1 for row in hits if row["rv10_ok"])
    not_old_bug = sum(1 for row in hits if not row["old_bug"])
    print(
        f"summary: rv10 above known+default floor {above_floor}/{len(hits)};"
        f" fixed old 390/390 bug {not_old_bug}/{len(hits)}"
    )
    print()


def audit_data6_style() -> None:
    """data6-style: one large red reveal, q6=2 (from EXECUTION_NOTES §43)."""
    snap = {
        "ui_contract": {
            "context": {"hero": "ahmed", "map_id": 2309, "phase": "bidding"},
            "constraints": {"public_info": {}},
        },
        "structured_ref_inputs": {
            "total_count": 48,
            "fixed_counts": {"q1": 9, "q3": 15, "q4": 17, "q5": 5},
            "quality_cells": {"q1": 15, "q3": 49, "q4": 48, "q5": 24},
            "avg_cells": {"q3": 49 / 15, "q4": 48 / 17, "q5": 24 / 5},
        },
        "public_info_rows": [
            {
                "info_id": 200023,
                "revealed_items_detail": [
                    {
                        "runtime_id": 1425860479021732,
                        "quality": 6,
                        "value": 452800,
                        "shape_code": 53,
                        "cells": 15,
                    }
                ],
            }
        ],
    }
    result = run_reference_engine(snap, max_combos=60_000).as_dict()
    print("=== data6-style (452800/15cell, q6=2; settlement q6≈520900) ===")
    print("red_value_range:", result["red_value_range"])
    print("balanced:", result["balanced"])
    print("gap vs 520900:", _pct_gap(result["red_value_range"][1], 520900))
    print()


def audit_ethan_r5(names: list[str] | None = None) -> None:
    pattern = "*ethan*5rounds*.json"
    files = sorted((ROOT / "data/samples/fatbeans").glob(pattern))
    if names:
        files = [p for p in files if p.name in names]
    picked: list[Path] = []
    for path in files:
        events = parse_fatbeans_capture(path)
        if not any(
            r.skill_id == 1002085
            for s in events.states
            for r in s.skill_reveals
            if r.hero_id == 208
        ):
            continue
        picked.append(path)
        if len(picked) >= 3 and not names:
            break
    print(f"=== Ethan R5 generic ref ({len(picked)} samples) ===")
    for path in picked:
        events = parse_fatbeans_capture(path)
        truth = final_truth_from_events(events)
        q6 = _settlement_quality_totals(events).get(6, {})
        snap = _build_ref_snapshot(hero="ethan", events=events)
        if truth is not None and not snap["structured_ref_inputs"].get("total_count"):
            snap["structured_ref_inputs"] = {"total_count": truth.total_items}
        evidence = extract_evidence(snap)
        result = run_reference_engine(snap, max_combos=60_000).as_dict()
        print(path.name)
        print(
            "  settlement:",
            f"items={truth.total_items if truth else '?'}",
            f"cells={truth.total_cells if truth else '?'}",
        )
        if q6:
            print(
                "  q6 truth:",
                q6.get("count"),
                "items",
                q6.get("cells"),
                "cells",
                q6.get("value"),
                "value",
            )
        print(
            "  ref bid:",
            result["conservative"],
            result["balanced"],
            result["aggressive"],
        )
        print(
            "  grid_target:",
            evidence.total_grid_target,
            "vs settlement cells:",
            truth.total_cells if truth else "?",
            f"gap={_pct_gap(int(evidence.total_grid_target or 0), truth.total_cells) if truth and evidence.total_grid_target else 'n/a'}",
        )
        print("  generic_ref:", "generic_ref_hero" in result["notes"])
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cross-hero-limit",
        type=int,
        default=None,
        help="Limit cross-hero q6-value scan to first N sample files (debug).",
    )
    parser.add_argument(
        "--no-report-file",
        action="store_true",
        help="Do not write data/reports/audit_cross_hero_q6_value.txt",
    )
    parser.add_argument(
        "--skip-synthetic",
        action="store_true",
        help="Skip synthetic/data6 fixed fixtures.",
    )
    parser.add_argument(
        "--skip-ethan",
        action="store_true",
        help="Skip Ethan R5 generic ref spot check.",
    )
    args = parser.parse_args()

    if not args.skip_synthetic:
        audit_synthetic_390k()
        audit_data6_style()
    audit_cross_hero_q6_value_table(
        limit=args.cross_hero_limit,
        report_path=None if args.no_report_file else DEFAULT_REPORT_PATH,
    )
    audit_ahmed_partial_red()
    if not args.skip_ethan:
        audit_ethan_r5()


if __name__ == "__main__":
    main()
