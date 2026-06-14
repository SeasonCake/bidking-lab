"""Quantify Aisha live ref latency at schedule combo caps (R3–R5, dual-pass).

Mirrors `ahmad_live_panel_server` skill+item passes with `hero_max_combos_for_round`.
Optional cap sweep shows sensitivity vs 8k/12k/20k/50k. Local audit only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "external_references" / "ahmad_live_reference_lab" / "tools"
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
for path in (ROOT / "src", AHMAD_SRC, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ahmad_ref_engine import prepare_reference_engine_snapshot, run_reference_engine  # noqa: E402
from audit_aisha_gap import SAMPLE_ROOTS, _build_snapshot  # noqa: E402
from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events, parse_fatbeans_capture  # noqa: E402
from hero_ref_live_schedule import hero_max_combos_for_round  # noqa: E402

try:
    from ahmad_live_panel_server import (  # noqa: E402
        _aisha_dual_pass_ref_result,
        _aisha_item_frame_ready,
        _aisha_run_engine_pass,
        AISHA_ENGINE_PASS_ITEM,
        AISHA_ENGINE_PASS_SKILL,
    )
except ImportError:
    _aisha_dual_pass_ref_result = None  # type: ignore[assignment]
CAP_SWEEP = (8000, 12000, 20000, 50000)
EXTRA_ROOTS = (
    ROOT / "data/samples/hero_ref/archive/reset/2026-06-10",
    ROOT / "data/samples/hero_ref/investigations/aisha_r1_r2_dive_559959",
)
UI_BUDGET_MS = 500.0


@dataclass(frozen=True)
class PassTiming:
    file: str
    round: int
    schedule_cap: int
    cap_used: int
    pass_kind: str
    elapsed_ms: float
    status: str
    combo_count: int
    route: str


def _clone_skill_pass(snapshot: dict[str, Any]) -> dict[str, Any]:
    cloned = json.loads(json.dumps(snapshot, ensure_ascii=False))
    cloned["action_result_rows"] = []
    uc = cloned.get("ui_contract") if isinstance(cloned.get("ui_contract"), dict) else {}
    cloned["ui_contract"] = uc
    actions = uc.get("actions") if isinstance(uc.get("actions"), dict) else {}
    uc["actions"] = actions
    actions["results"] = []
    return cloned


def _item_frame_ready(snapshot: dict[str, Any]) -> bool:
    rows = snapshot.get("action_result_rows")
    if not isinstance(rows, list) or not rows:
        return False
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("action_id") in (100101, 100102, 100103, 100104, 100105, 100106, 100107, 100108):
            return True
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if payload.get("items") or payload.get("revealed_items"):
            return True
    return bool(rows)


def _run_pass(
    snapshot: dict[str, Any],
    *,
    pass_kind: str,
    round_no: int,
    max_combos: int,
) -> tuple[dict[str, Any], float]:
    base = _clone_skill_pass(snapshot) if pass_kind == AISHA_ENGINE_PASS_SKILL else snapshot
    prepared = prepare_reference_engine_snapshot(base)
    prepared["audit_aisha_engine_pass"] = pass_kind
    if round_no < 3:
        prepared["audit_aisha_early_round"] = True
    started = time.perf_counter()
    result = run_reference_engine(prepared, max_combos=max_combos).as_dict()
    return result, (time.perf_counter() - started) * 1000.0


def _dual_pass_ms(snapshot: dict[str, Any], *, round_no: int, max_combos: int | None = None) -> tuple[float, list[PassTiming], bool]:
    cap = max_combos if max_combos is not None else hero_max_combos_for_round("aisha", round_no)
    schedule_cap = hero_max_combos_for_round("aisha", round_no)
    if _aisha_dual_pass_ref_result is not None and max_combos in (None, schedule_cap):
        _, timing = _aisha_dual_pass_ref_result(snapshot, round_no=round_no, public_info={})
        skill_ms = float(timing.get("skill") or 0.0)
        item_ms = timing.get("item")
        item_ran = item_ms is not None
        total = skill_ms + (float(item_ms) if item_ran else 0.0)
        rows: list[PassTiming] = [
            PassTiming("", round_no, schedule_cap, cap, AISHA_ENGINE_PASS_SKILL, round(skill_ms, 2), "", 0, "")
        ]
        if item_ran:
            rows.append(
                PassTiming("", round_no, schedule_cap, cap, AISHA_ENGINE_PASS_ITEM, round(float(item_ms), 2), "", 0, "")
            )
        return total, rows, item_ran

    rows: list[PassTiming] = []
    skill_result, skill_ms = _run_pass(snapshot, pass_kind=AISHA_ENGINE_PASS_SKILL, round_no=round_no, max_combos=cap)
    rows.append(
        PassTiming(
            file="",
            round=round_no,
            schedule_cap=hero_max_combos_for_round("aisha", round_no),
            cap_used=cap,
            pass_kind=AISHA_ENGINE_PASS_SKILL,
            elapsed_ms=round(skill_ms, 2),
            status=str(skill_result.get("status") or ""),
            combo_count=int(skill_result.get("combo_count") or 0),
            route=_route_label(skill_result),
        )
    )
    total = skill_ms
    item_ran = _aisha_item_frame_ready(snapshot, round_no) if _aisha_item_frame_ready else _item_frame_ready(snapshot)
    if item_ran:
        item_result, item_ms = _run_pass(snapshot, pass_kind=AISHA_ENGINE_PASS_ITEM, round_no=round_no, max_combos=cap)
        item_ran = True
        total += item_ms
        rows.append(
            PassTiming(
                file="",
                round=round_no,
                schedule_cap=hero_max_combos_for_round("aisha", round_no),
                cap_used=cap,
                pass_kind=AISHA_ENGINE_PASS_ITEM,
                elapsed_ms=round(item_ms, 2),
                status=str(item_result.get("status") or ""),
                combo_count=int(item_result.get("combo_count") or 0),
                route=_route_label(item_result),
            )
        )
    return total, rows, item_ran


def _route_label(result: dict[str, Any]) -> str:
    notes = list(result.get("notes") or [])
    status = str(result.get("status") or "")
    if status == "count_prior":
        return "count_prior"
    if status == "exact_total":
        return "exact_total"
    if "layout" in ";".join(notes):
        return "layout"
    return status or "unknown"


def _snapshot_for_round(path: Path, round_no: int) -> dict[str, Any] | None:
    events = parse_fatbeans_capture(path)
    batches = [b for b in live_batches_from_fatbeans_events(events) if b.phase != "settled"]
    if round_no > len(batches):
        return None
    prefix = batches[:round_no]
    map_id = None
    for state in events.states:
        if state.map_id:
            map_id = int(state.map_id)
            break
    snapshot = _build_snapshot(hero="aisha", events=events, prefix_batches=prefix, map_id=map_id)
    snapshot["ui_contract"]["context"]["round"] = round_no
    snapshot["round"] = round_no
    return snapshot


def _collect_files(*, sample_limit: int) -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for root in (*SAMPLE_ROOTS, *EXTRA_ROOTS):
        if not root.is_dir():
            continue
        for pattern in ("fatbeans*aisha*.json", "windivert*aisha*.json", "windivert*.json"):
            for path in sorted(root.glob(pattern)):
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                files.append(path)
    files.sort(key=lambda p: p.name)
    return files[:sample_limit] if sample_limit else files


def audit(*, sample_limit: int, rounds: tuple[int, ...], sweep: bool) -> dict[str, Any]:
    schedule_rows: list[dict[str, Any]] = []
    sweep_rows: list[dict[str, Any]] = []
    files = _collect_files(sample_limit=sample_limit)

    for path in files:
        for rnd in rounds:
            snapshot = _snapshot_for_round(path, rnd)
            if snapshot is None:
                continue
            schedule_cap = hero_max_combos_for_round("aisha", rnd)
            total_ms, passes, item_ran = _dual_pass_ms(snapshot, round_no=rnd, max_combos=schedule_cap)
            schedule_rows.append(
                {
                    "file": path.name,
                    "round": rnd,
                    "schedule_cap": schedule_cap,
                    "dual_pass_total_ms": round(total_ms, 2),
                    "item_pass_ran": item_ran,
                    "passes": [{**asdict(p), "file": path.name} for p in passes],
                }
            )
            if sweep:
                for cap in CAP_SWEEP:
                    if cap == schedule_cap:
                        continue
                    sweep_total, _, _ = _dual_pass_ms(snapshot, round_no=rnd, max_combos=cap)
                    sweep_rows.append(
                        {
                            "file": path.name,
                            "round": rnd,
                            "schedule_cap": schedule_cap,
                            "cap_used": cap,
                            "dual_pass_total_ms": round(sweep_total, 2),
                            "delta_vs_schedule_ms": round(sweep_total - total_ms, 2),
                        }
                    )

    return {
        "sample_limit": sample_limit,
        "rounds": list(rounds),
        "files_scanned": len(files),
        "schedule_cap_rows": schedule_rows,
        "cap_sweep_rows": sweep_rows,
        "summary": _summarize(schedule_rows, sweep_rows),
    }


def _summarize(schedule_rows: list[dict[str, Any]], sweep_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_round: dict[int, list[float]] = defaultdict(list)
    by_round_item: dict[int, list[float]] = defaultdict(list)
    slow_ui = 0
    for row in schedule_rows:
        by_round[int(row["round"])].append(float(row["dual_pass_total_ms"]))
        if row.get("item_pass_ran"):
            by_round_item[int(row["round"])].append(float(row["dual_pass_total_ms"]))
        if float(row["dual_pass_total_ms"]) >= UI_BUDGET_MS:
            slow_ui += 1

    round_stats: dict[str, Any] = {}
    for rnd in sorted(by_round):
        vals = sorted(by_round[rnd])
        p95_idx = max(0, int(len(vals) * 0.95) - 1)
        round_stats[f"R{rnd}"] = {
            "n": len(vals),
            "schedule_cap": hero_max_combos_for_round("aisha", rnd),
            "avg_ms": round(mean(vals), 1),
            "p50_ms": round(vals[len(vals) // 2], 1),
            "p95_ms": round(vals[p95_idx], 1),
            "max_ms": round(max(vals), 1),
            "over_500ms": sum(1 for v in vals if v >= UI_BUDGET_MS),
            "dual_pass_n": len(by_round_item.get(rnd, [])),
        }

    sweep_stats: dict[str, Any] = {}
    for cap in CAP_SWEEP:
        subset = [r for r in sweep_rows if int(r["cap_used"]) == cap]
        if not subset:
            continue
        deltas = [float(r["delta_vs_schedule_ms"]) for r in subset]
        totals = [float(r["dual_pass_total_ms"]) for r in subset]
        sweep_stats[str(cap)] = {
            "n": len(subset),
            "avg_total_ms": round(mean(totals), 1),
            "avg_delta_vs_schedule_ms": round(mean(deltas), 1),
            "max_delta_ms": round(max(deltas), 1),
        }

    return {
        "ui_budget_ms": UI_BUDGET_MS,
        "schedule_over_budget": slow_ui,
        "by_round": round_stats,
        "cap_sweep": sweep_stats,
    }


def format_text(report: dict[str, Any]) -> str:
    lines = [
        "audit_aisha_live_cap_perf (schedule caps + dual-pass)",
        f"files={report['files_scanned']} rounds={report['rounds']} rows={len(report['schedule_cap_rows'])}",
        f"ui_budget={UI_BUDGET_MS:.0f}ms",
        "",
        "round | cap | n | avg | p50 | p95 | max | >500ms | dual_pass_samples",
        "-" * 78,
    ]
    for key, stats in sorted(report["summary"]["by_round"].items()):
        lines.append(
            f"{key:4} | {stats['schedule_cap']:5} | {stats['n']:2} | "
            f"{stats['avg_ms']:5.0f} | {stats['p50_ms']:4.0f} | {stats['p95_ms']:4.0f} | "
            f"{stats['max_ms']:5.0f} | {stats['over_500ms']:7} | {stats['dual_pass_n']}"
        )
    sweep = report["summary"].get("cap_sweep") or {}
    if sweep:
        lines.extend(["", "cap sweep vs schedule (dual-pass total_ms):"])
        for cap, stats in sorted(sweep.items(), key=lambda kv: int(kv[0])):
            lines.append(
                f"  cap={cap:>5} n={stats['n']:2} avg_total={stats['avg_total_ms']:6.0f}ms "
                f"avg_delta={stats['avg_delta_vs_schedule_ms']:+.0f}ms max_delta={stats['max_delta_ms']:+.0f}ms"
            )
    slow = sorted(report["schedule_cap_rows"], key=lambda r: r["dual_pass_total_ms"], reverse=True)[:10]
    if slow:
        lines.extend(["", "slowest schedule-cap dual-pass:"])
        for row in slow:
            flag = "SLOW" if row["dual_pass_total_ms"] >= UI_BUDGET_MS else "ok"
            lines.append(
                f"  {flag} {row['dual_pass_total_ms']:7.0f}ms R{row['round']} cap={row['schedule_cap']} "
                f"item={row['item_pass_ran']} {row['file'][:56]}"
            )
    lines.extend(
        [
            "",
            "interpretation:",
            "  - live Aisha R3–R4 cap=8000, R5+ cap=12000 (not 50k)",
            "  - dual-pass = skill + item when prop frame present",
            f"  - target: dual-pass p95 < {UI_BUDGET_MS:.0f}ms for UI responsiveness",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-limit", type=int, default=30)
    parser.add_argument("--rounds", default="3,4,5")
    parser.add_argument("--sweep", action="store_true", help="Also run 8k/12k/20k/50k sweep")
    parser.add_argument("--json-out", type=Path, default=ROOT / "data/reports/audit_aisha_live_cap_perf.json")
    parser.add_argument("--txt-out", type=Path, default=ROOT / "data/reports/audit_aisha_live_cap_perf.txt")
    args = parser.parse_args()
    rounds = tuple(int(p.strip()) for p in args.rounds.split(",") if p.strip())
    t0 = time.perf_counter()
    report = audit(sample_limit=args.sample_limit, rounds=rounds, sweep=args.sweep)
    report["elapsed_s"] = round(time.perf_counter() - t0, 1)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    text = format_text(report)
    args.txt_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nelapsed_s={report['elapsed_s']} wrote {args.json_out} {args.txt_out}")


if __name__ == "__main__":
    main()
