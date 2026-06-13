"""Focused Aisha ref_v0 latency audit (local only, not shipped).

Spot-checks early rounds + R4「总仓储/总格」窗口 vs live defaults (band + D1 shadow).
Avoid full-library scans (>60min); prefer representative samples + hidden 2601 gate.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter, defaultdict
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
from bidking_lab.live.monitor import (  # noqa: E402
    _ahmad_ref_inputs_from_batches,
    _minimap_grid_items,
    _public_info_rows,
    _skill_reveal_rows,
    load_monitor_tables,
)

from ahmad_ref_engine import PINNED_QUALITY_CELLS_SPARSE_PRIOR_NOTE, prepare_reference_engine_snapshot, run_reference_engine  # noqa: E402

from audit_aisha_gap import SAMPLE_ROOTS, _build_snapshot, _events_through_sort, _prefix_sort_id  # noqa: E402
from audit_data7_perf import classify_route, _notes_list  # noqa: E402

HIDDEN_2601 = ROOT / "data/samples/fatbeans/fatbeans_valid_aisha_2601_3rounds_2601_1295018740835056_0215.json"
PERF_GATE_MS = 2000.0
WARM_GATE_MS = 500.0


@dataclass(frozen=True)
class PerfSpot:
    file: str
    round: int
    mode: str
    route: str
    status: str
    elapsed_ms: float
    combo_count: int
    total_count: int | None
    total_cells_bridge: bool
    total_grid_target: float | None
    notes_tail: str


def _bridge_flags(bridge: dict[str, Any]) -> tuple[bool, float | None]:
    total_cells = bridge.get("total_cells")
    has_cells = total_cells not in (None, "")
    target = bridge.get("total_grid_target")
    try:
        parsed_target = float(target) if target not in (None, "") else None
    except (TypeError, ValueError):
        parsed_target = None
    return has_cells, parsed_target


def _run_timed(snapshot: dict[str, Any], *, mode: str, max_combos: int) -> tuple[dict[str, Any], float]:
    payload = dict(snapshot)
    if mode == "off":
        payload["audit_aisha_layout_mode"] = "off"
        payload["audit_aisha_d1_mode"] = "off"
    elif mode == "live":
        payload = prepare_reference_engine_snapshot(payload)
    else:
        raise ValueError(mode)
    started = time.perf_counter()
    result = run_reference_engine(payload, max_combos=max_combos).as_dict()
    return result, (time.perf_counter() - started) * 1000.0


def _snapshot_at_round(path: Path, round_no: int, *, include_minimap: bool) -> dict[str, Any]:
    events = parse_fatbeans_capture(path)
    pre = [b for b in live_batches_from_fatbeans_events(events) if b.phase != "settled"]
    prefix = pre[:round_no]
    sort_id = _prefix_sort_id(prefix)
    prefix_events = _events_through_sort(events, sort_id) if sort_id else events
    bridge = _ahmad_ref_inputs_from_batches(prefix, hero="aisha") or {}
    snapshot = _build_snapshot(
        hero="aisha",
        events=prefix_events,
        prefix_batches=prefix,
        map_id=None,
    )
    snapshot["ui_contract"]["context"]["round"] = int(round_no)
    snapshot["structured_ref_inputs"] = bridge
    if include_minimap:
        try:
            tables = load_monitor_tables()
            snapshot["minimap_grid_items"] = _minimap_grid_items(prefix, tables.items)
        except OSError:
            pass
    return snapshot


def _spot_row(
    *,
    path: Path,
    round_no: int,
    mode: str,
    result: dict[str, Any],
    elapsed_ms: float,
    bridge: dict[str, Any],
) -> PerfSpot:
    notes = _notes_list(result)
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    total_count = evidence.get("total_count")
    try:
        parsed_total = int(total_count) if total_count not in (None, "") else None
    except (TypeError, ValueError):
        parsed_total = None
    has_cells, grid_target = _bridge_flags(bridge)
    return PerfSpot(
        file=path.name,
        round=round_no,
        mode=mode,
        route=classify_route(notes, status=str(result.get("status") or "")),
        status=str(result.get("status") or ""),
        elapsed_ms=round(elapsed_ms, 1),
        combo_count=int(result.get("combo_count") or 0),
        total_count=parsed_total,
        total_cells_bridge=has_cells,
        total_grid_target=grid_target,
        notes_tail=";".join(notes[-3:]),
    )


def _collect_spots(*, sample_limit: int, rounds: tuple[int, ...], max_combos: int) -> list[PerfSpot]:
    spots: list[PerfSpot] = []
    files: list[Path] = []
    for root in SAMPLE_ROOTS:
        if not root.is_dir():
            continue
        files.extend(sorted(root.glob("fatbeans*aisha*.json")))
    files = files[:sample_limit] if sample_limit else files

    for path in files:
        events = parse_fatbeans_capture(path)
        pre = [b for b in live_batches_from_fatbeans_events(events) if b.phase != "settled"]
        for rnd in rounds:
            if rnd > len(pre):
                continue
            prefix = pre[:rnd]
            bridge = _ahmad_ref_inputs_from_batches(prefix, hero="aisha") or {}
            snapshot = _snapshot_at_round(path, rnd, include_minimap=False)
            for mode in ("off", "live"):
                result, elapsed = _run_timed(snapshot, mode=mode, max_combos=max_combos)
                spots.append(
                    _spot_row(
                        path=path,
                        round_no=rnd,
                        mode=mode,
                        result=result,
                        elapsed_ms=elapsed,
                        bridge=bridge,
                    )
                )
    return spots


def _hidden_2601_spots(*, max_combos: int) -> list[PerfSpot]:
    if not HIDDEN_2601.is_file():
        return []
    spots: list[PerfSpot] = []
    for rnd in (3, 4):
        snapshot = _snapshot_at_round(HIDDEN_2601, rnd, include_minimap=True)
        prefix_batches = live_batches_from_fatbeans_events(parse_fatbeans_capture(HIDDEN_2601))
        prefix_batches = [b for b in prefix_batches if b.phase != "settled"][:rnd]
        bridge = _ahmad_ref_inputs_from_batches(prefix_batches, hero="aisha") or {}
        for mode in ("off", "live"):
            result, elapsed = _run_timed(snapshot, mode=mode, max_combos=max_combos)
            spots.append(
                _spot_row(
                    path=HIDDEN_2601,
                    round_no=rnd,
                    mode=mode,
                    result=result,
                    elapsed_ms=elapsed,
                    bridge=bridge,
                )
            )
    return spots


def format_report(spots: list[PerfSpot], *, elapsed_s: float, sample_limit: int) -> str:
    lines = [
        "audit_aisha_perf (spot check — not full library)",
        f"spots={len(spots)} sample_limit={sample_limit} elapsed_s={elapsed_s:.1f}",
        f"gates: hidden_2601<{PERF_GATE_MS:.0f}ms  warm_exact_avg<{WARM_GATE_MS:.0f}ms",
        "",
    ]
    by_round_mode: dict[tuple[int, str], list[PerfSpot]] = defaultdict(list)
    for spot in spots:
        by_round_mode[(spot.round, spot.mode)].append(spot)
    lines.append("round | mode | n | avg_ms | p95_ms | max_ms | slow>=2s | with_total_cells_bridge")
    lines.append("-" * 88)
    for rnd in sorted({spot.round for spot in spots}):
        for mode in ("off", "live"):
            subset = by_round_mode.get((rnd, mode), [])
            if not subset:
                continue
            elapsed = [row.elapsed_ms for row in subset]
            p95 = sorted(elapsed)[max(0, int(len(elapsed) * 0.95) - 1)]
            slow = sum(1 for value in elapsed if value >= PERF_GATE_MS)
            cells_n = sum(1 for row in subset if row.total_cells_bridge)
            lines.append(
                f"R{rnd:2d}  | {mode:4} | {len(subset):2d} | {sum(elapsed)/len(elapsed):6.0f} | "
                f"{p95:6.0f} | {max(elapsed):6.0f} | {slow:8d} | {cells_n}/{len(subset)}"
            )

    live_delta = []
    off_by_key = {(s.file, s.round): s for s in spots if s.mode == "off"}
    for spot in spots:
        if spot.mode != "live":
            continue
        base = off_by_key.get((spot.file, spot.round))
        if base:
            live_delta.append(spot.elapsed_ms - base.elapsed_ms)
    if live_delta:
        lines.extend(
            [
                "",
                f"live vs off delta_ms: avg={sum(live_delta)/len(live_delta):+.0f} "
                f"max={max(live_delta):+.0f} (band+d1 shadow should be ~0)",
            ]
        )

    r4_cells = [s for s in spots if s.round == 4 and s.total_cells_bridge]
    if r4_cells:
        lines.extend(["", "R4 rows with total_cells bridge (群友「第四轮总仓储」路径):"])
        for spot in sorted(r4_cells, key=lambda row: row.elapsed_ms, reverse=True)[:12]:
            flag = "SLOW" if spot.elapsed_ms >= PERF_GATE_MS else "ok"
            lines.append(
                f"  {flag} {spot.elapsed_ms:7.0f}ms {spot.mode:4} r{spot.round} "
                f"route={spot.route} combos={spot.combo_count} {spot.file[:52]}"
            )

    hidden = [s for s in spots if "2601_0215" in s.file]
    if hidden:
        lines.extend(["", "hidden map 2601 gate sample:"])
        for spot in hidden:
            gate = "PASS" if spot.elapsed_ms < PERF_GATE_MS else "FAIL"
            sparse = PINNED_QUALITY_CELLS_SPARSE_PRIOR_NOTE in spot.notes_tail
            lines.append(
                f"  {gate} {spot.elapsed_ms:7.0f}ms {spot.mode:4} r{spot.round} "
                f"combos={spot.combo_count} sparse_pin={sparse}"
            )

    routes = Counter(spot.route for spot in spots)
    lines.extend(["", "route_mix:", *[f"  {route}: {count}" for route, count in routes.most_common()]])

    lines.extend(
        [
            "",
            "interpretation:",
            "  - count_prior + wide combo space remains main latency risk (not band/D1 shadow)",
            "  - R4 total_cells bridge alone does not imply slow if sparse/tight prior routes",
            "  - full-library audit_data7 --hero aisha --max-round 5 still deferred (>5min)",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-limit", type=int, default=25, help="Max aisha fatbeans files (0=all).")
    parser.add_argument("--rounds", default="3,4,5", help="Comma rounds to replay, e.g. 3,4,5")
    parser.add_argument("--max-combos", type=int, default=50_000)
    parser.add_argument("--report", type=Path, default=ROOT / "data/reports/audit_aisha_perf.txt")
    args = parser.parse_args()

    rounds = tuple(int(part.strip()) for part in args.rounds.split(",") if part.strip())
    t0 = time.perf_counter()
    spots = _collect_spots(sample_limit=args.sample_limit, rounds=rounds, max_combos=args.max_combos)
    spots.extend(_hidden_2601_spots(max_combos=args.max_combos))
    report = format_report(spots, elapsed_s=time.perf_counter() - t0, sample_limit=args.sample_limit)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(f"\nwrote {args.report}")


if __name__ == "__main__":
    main()
