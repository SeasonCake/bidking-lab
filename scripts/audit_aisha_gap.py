"""Curated Aisha fatbeans gap audit: ref ranges vs settlement truth.

Filters out low-quality captures (1-round, tail-heavy, insufficient evidence)
before measuring where Hero Ref v0 misses on counts/cells/value.
Local audit only — not shipped in Hero Ref packages.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bidking_lab.live.fatbeans import (  # noqa: E402
    FatbeansCaptureEvents,
    _hero_mode_from_state,
    live_batches_from_fatbeans_events,
    parse_fatbeans_capture,
)
from bidking_lab.live.monitor import (  # noqa: E402
    _ahmad_ref_inputs_from_batches,
    _public_info_rows,
    _skill_reveal_rows,
)
from bidking_lab.live.replay import final_truth_from_events  # noqa: E402
from ahmad_ref_engine import normalize_hero_key, run_reference_engine  # noqa: E402

SAMPLE_ROOTS = (
    ROOT / "data/samples/fatbeans",
    ROOT / "data/samples/fatbeans_activity_20260605_shipwreck",
)
DEFAULT_REPORT = ROOT / "data/reports/audit_aisha_gap.txt"
ITEMS_PATH = ROOT / "data/processed/items.json"
_ITEM_VALUES: dict[int, int] | None = None

QUALITY_KEYS = {
    1: "q1",
    3: "q3",
    4: "q4",
    5: "q5",
    6: "q6",
}


@dataclass
class FilterStats:
    scanned: int = 0
    reasons: Counter = field(default_factory=Counter)


@dataclass(frozen=True)
class GapRow:
    file: str
    map_id: int | None
    rounds: int
    audit_round: int
    status: str
    total_count_exact: bool
    total_items_miss: bool
    total_cells_miss: bool
    q5_count_miss: bool
    q5_cells_miss: bool | None
    q6_count_miss: bool
    q6_cells_miss: bool | None
    q6_value_miss: bool
    total_cells_gap: int | None
    q5_count_gap: int | None
    q6_count_gap: int | None
    q6_value_gap: int | None


def _events_through_sort(events: FatbeansCaptureEvents, sort_id: int) -> FatbeansCaptureEvents:
    return FatbeansCaptureEvents(
        packets=tuple(row for row in events.packets if int(row.sort_id) <= sort_id),
        frames=tuple(row for row in events.frames if int(row.sort_id) <= sort_id),
        sends=tuple(row for row in events.sends if int(row.sort_id) <= sort_id),
        states=tuple(row for row in events.states if int(row.sort_id) <= sort_id),
        statuses=tuple(row for row in events.statuses if int(row.sort_id) <= sort_id),
    )


def _hero_from_events(events) -> str:
    for state in reversed(events.states):
        hero = _hero_mode_from_state(state)
        if hero:
            return normalize_hero_key(hero)
    return ""


def _item_values() -> dict[int, int]:
    global _ITEM_VALUES
    if _ITEM_VALUES is not None:
        return _ITEM_VALUES
    if not ITEMS_PATH.is_file():
        _ITEM_VALUES = {}
        return _ITEM_VALUES
    import json

    payload = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        _ITEM_VALUES = {
            int(entry["item_id"]): int(entry.get("value") or 0)
            for entry in payload
            if isinstance(entry, dict) and entry.get("item_id") is not None
        }
    elif isinstance(payload, dict):
        _ITEM_VALUES = {
            int(item_id): int(entry.get("value") or 0)
            for item_id, entry in payload.items()
            if isinstance(entry, dict)
        }
    else:
        _ITEM_VALUES = {}
    return _ITEM_VALUES


def _settlement_breakdown(events) -> dict[str, Any]:
    values_by_id = _item_values()
    for state in reversed(events.states):
        if not state.inventory_items:
            continue
        counts: Counter[int] = Counter()
        cells: Counter[int] = Counter()
        values: Counter[int] = Counter()
        for item in state.inventory_items:
            quality = int(item.quality or 0)
            if quality <= 0:
                continue
            counts[quality] += 1
            cells[quality] += int(item.cells or 0)
            values[quality] += int(values_by_id.get(int(item.item_id), 0))
        return {
            "total_items": len(state.inventory_items),
            "total_cells": sum(int(item.cells or 0) for item in state.inventory_items),
            "counts": dict(counts),
            "cells": dict(cells),
            "values": dict(values),
        }
    return {}


def _rounds_from_filename(path: Path) -> int | None:
    name = path.name.lower()
    marker = "_rounds_"
    if marker not in name:
        return None
    token = name.split(marker, 1)[1].split("_", 1)[0]
    try:
        return int(token)
    except ValueError:
        return None


def _triplet(payload: dict[str, Any], key: str) -> tuple[int | None, int | None, int | None]:
    raw = payload.get(key)
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        return None, None, None
    out: list[int | None] = []
    for part in raw:
        if part in (None, ""):
            out.append(None)
            continue
        try:
            out.append(int(part))
        except (TypeError, ValueError):
            out.append(None)
    return out[0], out[1], out[2]


def _truth_in_range(truth: int | None, low: int | None, mid: int | None, high: int | None) -> bool | None:
    if truth is None:
        return None
    if low is None and mid is None and high is None:
        return False
    lo = low if low is not None else mid
    hi = high if high is not None else mid
    if lo is None or hi is None:
        return None
    return lo <= truth <= hi


def _mid_gap(truth: int | None, low: int | None, mid: int | None, high: int | None) -> int | None:
    if truth is None:
        return None
    pivot = mid
    if pivot is None and low is not None and high is not None:
        pivot = (low + high) // 2
    if pivot is None:
        pivot = low if low is not None else high
    if pivot is None:
        return None
    return truth - pivot


def _total_count_range(result: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    evidence = result.get("evidence")
    if isinstance(evidence, dict) and evidence.get("total_count") not in (None, ""):
        try:
            exact = int(evidence["total_count"])
            return exact, exact, exact
        except (TypeError, ValueError):
            pass
    return _triplet(result, "total_count_range")


def _build_snapshot(*, hero: str, events, prefix_batches) -> dict:
    bridge = _ahmad_ref_inputs_from_batches(prefix_batches, hero=hero) or {}
    return {
        "ui_contract": {
            "context": {"hero": hero, "phase": "bidding"},
            "constraints": {"public_info": {}},
        },
        "structured_ref_inputs": bridge,
        "public_info_rows": _public_info_rows(events, {}),
        "skill_reveals": _skill_reveal_rows(events, {}),
        "skill_reveal_rows": _skill_reveal_rows(events, {}),
        "action_result_rows": [],
    }


def _prefix_sort_id(prefix_batches) -> int:
    sort_ids = [int(batch.sequence or 0) for batch in prefix_batches if batch.sequence is not None]
    return max(sort_ids) if sort_ids else 0


def _evidence_strength(snapshot: dict[str, Any], result: dict[str, Any]) -> int:
    score = 0
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    if evidence.get("total_count") not in (None, ""):
        score += 2
    if evidence.get("total_grid_target") not in (None, ""):
        score += 1
    for bucket in ("fixed_counts", "quality_cells", "avg_cells", "split_counts"):
        payload = evidence.get(bucket)
        if isinstance(payload, dict):
            score += sum(1 for value in payload.values() if value not in (None, ""))
    return score


def _passes_filters(
    *,
    path: Path,
    events,
    hero: str,
    pre_batches: list,
    settlement: dict[str, Any],
    min_rounds: int,
    min_evidence_score: int,
    max_q6_value: int,
    max_q6_count: int,
    stats: FilterStats,
) -> tuple[bool, str, int]:
    stats.scanned += 1
    if hero != "aisha":
        stats.reasons["not_aisha"] += 1
        return False, "not_aisha", 0
    if not settlement:
        stats.reasons["no_settlement"] += 1
        return False, "no_settlement", 0
    rounds_file = _rounds_from_filename(path)
    rounds_live = len(pre_batches)
    rounds = rounds_live
    if rounds_file is not None:
        rounds = min(rounds_file, rounds_live) if rounds_live else rounds_file
    if rounds < min_rounds:
        stats.reasons[f"rounds<{min_rounds}"] += 1
        return False, f"rounds<{min_rounds}", rounds
    q6_value = int(settlement.get("values", {}).get(6, 0) or 0)
    q6_count = int(settlement.get("counts", {}).get(6, 0) or 0)
    if q6_value > max_q6_value:
        stats.reasons["tail_q6_value"] += 1
        return False, "tail_q6_value", rounds
    if q6_count > max_q6_count:
        stats.reasons["tail_q6_count"] += 1
        return False, "tail_q6_count", rounds
    audit_round = max(min_rounds, rounds - 1)
    audit_round = min(audit_round, len(pre_batches))
    prefix_batches = pre_batches[:audit_round]
    sort_id = _prefix_sort_id(prefix_batches)
    prefix_events = _events_through_sort(events, sort_id) if sort_id else events
    snapshot = _build_snapshot(hero=hero, events=prefix_events, prefix_batches=prefix_batches)
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()
    status = str(result.get("status") or "")
    if status in {"missing_total_count", "no_reachable_combo"}:
        stats.reasons[f"status:{status}"] += 1
        return False, f"status:{status}", audit_round
    if _evidence_strength(snapshot, result) < min_evidence_score:
        stats.reasons["insufficient_evidence"] += 1
        return False, "insufficient_evidence", audit_round
    return True, "ok", audit_round


def _evaluate_row(
    *,
    path: Path,
    events,
    audit_round: int,
    pre_batches: list,
) -> GapRow | None:
    settlement = _settlement_breakdown(events)
    if not settlement:
        return None
    prefix_batches = pre_batches[:audit_round]
    sort_id = _prefix_sort_id(prefix_batches)
    prefix_events = _events_through_sort(events, sort_id) if sort_id else events
    snapshot = _build_snapshot(hero="aisha", events=prefix_events, prefix_batches=prefix_batches)
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()
    q_ranges = result.get("quality_count_ranges")
    if not isinstance(q_ranges, dict):
        q_ranges = {}
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    quality_cells = evidence.get("quality_cells")
    if not isinstance(quality_cells, dict):
        quality_cells = {}

    total_low, total_mid, total_high = _total_count_range(result)
    grid_low, grid_mid, grid_high = _triplet(result, "total_grid_range")
    q5_low, q5_mid, q5_high = _triplet(q_ranges, "q5")
    q6_low, q6_mid, q6_high = _triplet(q_ranges, "q6")
    rv_low, rv_mid, rv_high = _triplet(result, "red_value_range")

    truth_items = int(settlement["total_items"])
    truth_cells = int(settlement["total_cells"])
    truth_q5 = int(settlement["counts"].get(5, 0))
    truth_q5_cells = int(settlement["cells"].get(5, 0))
    truth_q6 = int(settlement["counts"].get(6, 0))
    truth_q6_cells = int(settlement["cells"].get(6, 0))
    truth_q6_value = int(settlement["values"].get(6, 0))

    def _cells_miss(quality_key: str, truth_cells_value: int) -> bool:
        if quality_key in quality_cells and quality_cells[quality_key] not in (None, ""):
            try:
                ref_cells = int(float(quality_cells[quality_key]))
            except (TypeError, ValueError):
                return True
            return ref_cells != truth_cells_value
        return False

    map_id = None
    for state in events.states:
        if state.map_id:
            map_id = int(state.map_id)
            break

    return GapRow(
        file=path.name,
        map_id=map_id,
        rounds=len(pre_batches),
        audit_round=audit_round,
        status=str(result.get("status") or ""),
        total_count_exact=evidence.get("total_count") not in (None, ""),
        total_items_miss=not _truth_in_range(truth_items, total_low, total_mid, total_high),
        total_cells_miss=not _truth_in_range(truth_cells, grid_low, grid_mid, grid_high),
        q5_count_miss=not _truth_in_range(truth_q5, q5_low, q5_mid, q5_high),
        q5_cells_miss=(
            _cells_miss("q5", truth_q5_cells)
            if "q5" in quality_cells and quality_cells["q5"] not in (None, "")
            else None
        ),
        q6_count_miss=not _truth_in_range(truth_q6, q6_low, q6_mid, q6_high),
        q6_cells_miss=(
            _cells_miss("q6", truth_q6_cells)
            if "q6" in quality_cells and quality_cells["q6"] not in (None, "")
            else None
        ),
        q6_value_miss=not _truth_in_range(truth_q6_value, rv_low, rv_mid, rv_high)
        if truth_q6_value > 0
        else False,
        total_cells_gap=_mid_gap(truth_cells, grid_low, grid_mid, grid_high),
        q5_count_gap=_mid_gap(truth_q5, q5_low, q5_mid, q5_high),
        q6_count_gap=_mid_gap(truth_q6, q6_low, q6_mid, q6_high),
        q6_value_gap=_mid_gap(truth_q6_value, rv_low, rv_mid, rv_high),
    )


def audit_aisha_gaps(
    *,
    sample_roots: tuple[Path, ...],
    min_rounds: int,
    min_evidence_score: int,
    max_q6_value: int,
    max_q6_count: int,
    limit: int,
) -> tuple[list[GapRow], FilterStats]:
    stats = FilterStats()
    rows: list[GapRow] = []
    for root in sample_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("fatbeans*aisha*.json")):
            if limit and stats.scanned >= limit + 500:
                break
            try:
                events = parse_fatbeans_capture(path)
            except OSError:
                stats.reasons["parse_error"] += 1
                continue
            hero = _hero_from_events(events)
            pre_batches = [b for b in live_batches_from_fatbeans_events(events) if b.phase != "settled"]
            settlement = _settlement_breakdown(events)
            ok, _reason, audit_round = _passes_filters(
                path=path,
                events=events,
                hero=hero,
                pre_batches=pre_batches,
                settlement=settlement,
                min_rounds=min_rounds,
                min_evidence_score=min_evidence_score,
                max_q6_value=max_q6_value,
                max_q6_count=max_q6_count,
                stats=stats,
            )
            if not ok:
                continue
            row = _evaluate_row(path=path, events=events, audit_round=audit_round, pre_batches=pre_batches)
            if row is None:
                continue
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    return rows, stats


def _miss_rate(rows: list[GapRow], attr: str) -> float | None:
    applicable = [row for row in rows if getattr(row, attr) is not None]
    if not applicable:
        return None
    return sum(1 for row in applicable if getattr(row, attr)) / len(applicable)


def _avg_abs_gap(rows: list[GapRow], attr: str) -> float | None:
    gaps = [abs(getattr(row, attr)) for row in rows if getattr(row, attr) is not None]
    if not gaps:
        return None
    return sum(gaps) / len(gaps)


def format_report(
    rows: list[GapRow],
    stats: FilterStats,
    *,
    min_rounds: int,
    min_evidence_score: int,
) -> str:
    lines: list[str] = []
    lines.append("audit_aisha_gap")
    lines.append(f"curated_rows={len(rows)} scanned={stats.scanned}")
    lines.append(
        f"filters: min_rounds={min_rounds} min_evidence_score={min_evidence_score} "
        "exclude_tail_q6_value exclude_tail_q6_count exclude_status_missing/no_combo"
    )
    lines.append("")
    lines.append("filter_funnel:")
    for reason, count in stats.reasons.most_common():
        lines.append(f"  {reason}: {count}")
    lines.append("")
    if not rows:
        lines.append("No curated rows — relax filters or add samples.")
        return "\n".join(lines)

    dimensions = [
        ("total_items", "total_items_miss", None),
        ("total_cells", "total_cells_miss", "total_cells_gap"),
        ("q5_count", "q5_count_miss", "q5_count_gap"),
        ("q5_cells", "q5_cells_miss", None),
        ("q6_count", "q6_count_miss", "q6_count_gap"),
        ("q6_cells", "q6_cells_miss", None),
        ("q6_value", "q6_value_miss", "q6_value_gap"),
    ]
    lines.append("miss_rate (truth outside ref conservative/aggressive band):")
    ranked: list[tuple[str, float]] = []
    for label, miss_attr, gap_attr in dimensions:
        rate = _miss_rate(rows, miss_attr)
        if rate is None:
            lines.append(f"  {label:12}   n/a (no locked ref cells / not measured)")
            continue
        ranked.append((label, rate))
        gap_text = ""
        if gap_attr:
            avg_gap = _avg_abs_gap(rows, gap_attr)
            if avg_gap is not None:
                gap_text = f" avg_abs_mid_gap={avg_gap:.1f}"
        lines.append(f"  {label:12} {rate*100:5.1f}%{gap_text}")
    ranked = [item for item in ranked if item[1] is not None]
    ranked.sort(key=lambda item: item[1], reverse=True)
    lines.append("largest_gaps_first: " + ", ".join(f"{name}={rate*100:.0f}%" for name, rate in ranked[:4]))
    lines.append("")
    exact_total_rows = [row for row in rows if row.total_count_exact]
    lines.append(
        f"subset_exact_total_count: n={len(exact_total_rows)} "
        "(200017 or equivalent already in evidence at audit round)"
    )
    if exact_total_rows:
        for label, miss_attr, _gap_attr in dimensions:
            if label == "total_items":
                continue
            rate = _miss_rate(exact_total_rows, miss_attr)
            if rate is None:
                continue
            lines.append(f"  exact_total.{label:10} {rate*100:5.1f}%")
    lines.append("")
    lines.append("interpretation:")
    lines.append("  - total_items miss is inflated while ref still on count_prior / no 200017")
    lines.append("  - prioritize total_cells + q5_count + q6_value gaps for Hero Ref v0 fixes")
    lines.append("  - q5/q6 cells need locked quality_cells in evidence; v3 shape/bucket deferred")
    lines.append("")
    lines.append("worst_total_cells (top 8):")
    for row in sorted(rows, key=lambda item: abs(item.total_cells_gap or 0), reverse=True)[:8]:
        lines.append(
            f"  gap={row.total_cells_gap} r{row.audit_round}/{row.rounds} map={row.map_id} "
            f"{row.status} {row.file[:70]}"
        )
    lines.append("")
    lines.append("worst_q5_count (top 8):")
    for row in sorted(rows, key=lambda item: abs(item.q5_count_gap or 0), reverse=True)[:8]:
        lines.append(
            f"  gap={row.q5_count_gap} r{row.audit_round}/{row.rounds} map={row.map_id} "
            f"{row.status} {row.file[:70]}"
        )
    lines.append("")
    lines.append("worst_q6 (count/value, top 8 each):")
    for row in sorted(rows, key=lambda item: abs(item.q6_count_gap or 0), reverse=True)[:8]:
        lines.append(f"  q6_count gap={row.q6_count_gap} {row.file[:70]}")
    for row in sorted(rows, key=lambda item: abs(item.q6_value_gap or 0), reverse=True)[:8]:
        lines.append(f"  q6_value gap={row.q6_value_gap} {row.file[:70]}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-rounds", type=int, default=3)
    parser.add_argument("--min-evidence-score", type=int, default=4)
    parser.add_argument("--max-q6-value", type=int, default=1_200_000)
    parser.add_argument("--max-q6-count", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="Max curated rows (0=all)")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    rows, stats = audit_aisha_gaps(
        sample_roots=SAMPLE_ROOTS,
        min_rounds=args.min_rounds,
        min_evidence_score=args.min_evidence_score,
        max_q6_value=args.max_q6_value,
        max_q6_count=args.max_q6_count,
        limit=args.limit,
    )
    report = format_report(
        rows,
        stats,
        min_rounds=args.min_rounds,
        min_evidence_score=args.min_evidence_score,
    )
    print(report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report + "\n", encoding="utf-8")
    print(f"\nwrote {args.report}")


if __name__ == "__main__":
    main()
