"""Audit Aisha R1→R2 quote dive for session 2404:1425860640559959 (local).

Parses WinDivert reset capture, rebuilds R1/R2 snapshots, runs ref_v0 at
schedule combo caps, and writes a compact report. Local audit only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "external_references" / "ahmad_live_reference_lab" / "tools"
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
for path in (ROOT / "src", AHMAD_SRC, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ahmad_ref_engine import prepare_reference_engine_snapshot, run_reference_engine  # noqa: E402
from audit_aisha_gap import _build_snapshot  # noqa: E402
from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events, parse_fatbeans_capture  # noqa: E402
from hero_ref_live_schedule import hero_max_combos_for_round  # noqa: E402

DEFAULT_CAPTURE = Path(
    r"C:\Users\shenc\Desktop\recordings\data10\logs\live\raw\archive\reset"
    r"\windivert_live_2026-06-14_014209_2404_1425860640559959_reset.json"
)
DEFAULT_REPORT = ROOT / "data/reports/audit_aisha_r1_r2_dive_559959.json"
COMBO_CAPS = (1500, 2500, 8000, 12000, 20000, 50000)


def _max_sort_for_round(events: Any, target_round: int) -> int:
    best = 0
    for state in events.states:
        if state.round_index is not None and int(state.round_index) <= target_round:
            sort_id = int(state.sort_id or 0)
            if sort_id > best:
                best = sort_id
    return best


def _round_snapshot(
    events: Any,
    batches: list[Any],
    *,
    target_round: int,
    map_id: int,
) -> dict[str, Any]:
    sort_cutoff = _max_sort_for_round(events, target_round)
    prefix = [
        batch
        for batch in batches
        if batch.sequence is not None and int(batch.sequence) <= sort_cutoff
    ]
    if not prefix:
        prefix = batches[: max(1, target_round)]
    snapshot = _build_snapshot(
        hero="aisha",
        events=events,
        prefix_batches=prefix,
        map_id=map_id,
    )
    snapshot["ui_contract"]["context"]["round"] = target_round
    snapshot["round"] = target_round
    return snapshot


def _run_cap(snapshot: dict[str, Any], *, cap: int, round_no: int) -> dict[str, Any]:
    prepared = prepare_reference_engine_snapshot(snapshot)
    prepared["audit_aisha_engine_pass"] = "skill"
    if round_no < 3:
        prepared["audit_aisha_early_round"] = True
    started = time.perf_counter()
    result = run_reference_engine(prepared, max_combos=cap).as_dict()
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    return {
        "max_combos": cap,
        "elapsed_ms": elapsed_ms,
        "status": result.get("status"),
        "combo_count": result.get("combo_count"),
        "conservative": result.get("conservative"),
        "balanced": result.get("balanced"),
        "aggressive": result.get("aggressive"),
        "total_count": evidence.get("total_count"),
        "total_grid_target": evidence.get("total_grid_target"),
        "fixed_counts": evidence.get("fixed_counts"),
        "notes_head": list(result.get("notes") or [])[:8],
    }


def audit_capture(capture_path: Path) -> dict[str, Any]:
    events = parse_fatbeans_capture(capture_path)
    batches = [batch for batch in live_batches_from_fatbeans_events(events) if batch.phase != "settled"]
    map_id = 2404
    for state in events.states:
        if state.map_id:
            map_id = int(state.map_id)
            break
    rows: list[dict[str, Any]] = []
    for target_round in (1, 2, 3):
        snapshot = _round_snapshot(events, batches, target_round=target_round, map_id=map_id)
        schedule_cap = hero_max_combos_for_round("aisha", target_round)
        row: dict[str, Any] = {
            "round": target_round,
            "schedule_cap": schedule_cap,
            "structured_ref_inputs": snapshot.get("structured_ref_inputs"),
            "runs": [],
        }
        caps = sorted(set([schedule_cap, *COMBO_CAPS]))
        for cap in caps:
            row["runs"].append(_run_cap(snapshot, cap=cap, round_no=target_round))
        rows.append(row)
    return {
        "session_id": "2404:1425860640559959",
        "capture_path": str(capture_path),
        "map_id": map_id,
        "round_rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Aisha R1/R2 dive session")
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    if not args.capture.is_file():
        print(f"missing capture: {args.capture}", file=sys.stderr)
        return 1
    report = audit_capture(args.capture)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
