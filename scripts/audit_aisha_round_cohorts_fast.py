"""Fast fixed-round cohort audit (single pass, off+band only, ~5–10 min).

Evaluates curated tail-filtered Aisha captures at fixed rounds 1–5 once per file.
R1/R2 skip band (layout min round 3). See data/reports/audit_aisha_round_cohorts_fast.txt
"""

from __future__ import annotations

import argparse
import sys
import time
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

from ahmad_ref_engine import run_reference_engine  # noqa: E402

from audit_aisha_gap import (  # noqa: E402
    SAMPLE_ROOTS,
    _build_snapshot,
    _events_through_sort,
    _evidence_strength,
    _hero_from_events,
    _map_id_from_events,
    _prefix_sort_id,
    _settlement_breakdown,
    _total_items_range,
    _triplet,
    _truth_in_range,
)

DEFENSE_MULT_HINT = {
    1: "2.0× round-high (defense)",
    2: "1.6× round-high",
    3: "1.3× round-high",
    4: "1.1× round-high",
    5: "competitive (highest wins)",
}

COHORT_ORDER = ("R1", "R2", "R3", "R4-R5")


@dataclass(frozen=True)
class CohortSpec:
    name: str
    eval_rounds: tuple[int, ...]
    min_evidence_score: int
    note: str


COHORTS: dict[str, CohortSpec] = {
    "R1": CohortSpec("R1", (1,), 0, "defense — high error OK"),
    "R2": CohortSpec("R2", (2,), 0, "defense — tapering error"),
    "R3": CohortSpec("R3", (3,), 1, "pre-warehouse — band may help"),
    "R4-R5": CohortSpec("R4-R5", (4, 5), 4, "primary gate — R4 focus"),
}


@dataclass
class EvalRow:
    file: str
    eval_round: int
    truth_cells: int
    truth_items: int
    cells_off_hit: bool
    cells_band_hit: bool
    items_off_hit: bool
    balanced_off_miss: bool


def _run(snapshot: dict[str, Any], mode: str, *, max_combos: int) -> dict[str, Any]:
    return run_reference_engine({**snapshot, "audit_aisha_layout_mode": mode}, max_combos=max_combos).as_dict()


def _balanced_miss(result: dict[str, Any], truth_value: int) -> bool:
    balanced = result.get("balanced")
    try:
        balanced_int = int(balanced) if balanced not in (None, "") else None
    except (TypeError, ValueError):
        balanced_int = None
    if balanced_int is None or truth_value <= 0:
        return False
    return not (int(balanced_int * 0.85) <= truth_value <= int(balanced_int * 1.15))


def assign_rows(
    cache: dict[tuple[str, int], EvalRow],
    strengths: dict[tuple[str, int], int],
    spec: CohortSpec,
) -> list[EvalRow]:
    rows: list[EvalRow] = []
    for rnd in spec.eval_rounds:
        for key, row in cache.items():
            if key[1] != rnd:
                continue
            if strengths.get(key, 0) < spec.min_evidence_score:
                continue
            rows.append(row)
    return rows


def _rate(rows: list[EvalRow], attr: str) -> float:
    return sum(1 for r in rows if getattr(r, attr)) / len(rows) if rows else 0.0


def _band_delta(rows: list[EvalRow]) -> tuple[int, int]:
    imp = sum(1 for r in rows if not r.cells_off_hit and r.cells_band_hit)
    wors = sum(1 for r in rows if r.cells_off_hit and not r.cells_band_hit)
    return imp, wors


def format_report(
    cache: dict[tuple[str, int], EvalRow],
    strengths: dict[tuple[str, int], int],
) -> str:
    lines = [
        "Aisha FAST round-cohort audit (tail filters, fixed eval rounds 1–5)",
        "Phase 1 gate: cells + items at R4 slice | Phase 2: balanced (D1 deferred)",
        "R1/R2: band=off (layout inactive); R3+: off vs band",
        "",
        "Also see penultimate-round reports:",
        "  audit_aisha_c2_batch_full.txt (148 curated, band +9.5pp cells hit)",
        "  audit_aisha_gap_by_round.txt (cells/balanced by penultimate round)",
        "",
    ]
    for name in COHORT_ORDER:
        spec = COHORTS[name]
        rows = assign_rows(cache, strengths, spec)
        imp, wors = _band_delta(rows)
        lines.append(f"## {name} — {spec.note}")
        lines.append(f"rows={len(rows)}")
        if name == "R4-R5" and rows:
            for rnd in (4, 5):
                sub = [r for r in rows if r.eval_round == rnd]
                if not sub:
                    continue
                si, sw = _band_delta(sub)
                lines.append(
                    f"  R{rnd} n={len(sub)} | cells off={_rate(sub, 'cells_off_hit'):.1%} "
                    f"band={_rate(sub, 'cells_band_hit'):.1%} | items off={_rate(sub, 'items_off_hit'):.1%} "
                    f"| band +{si}/-{sw} | {DEFENSE_MULT_HINT[rnd]}"
                )
        if rows:
            lines.append(
                f"  ALL | cells off={_rate(rows, 'cells_off_hit'):.1%} band={_rate(rows, 'cells_band_hit'):.1%} "
                f"| items off={_rate(rows, 'items_off_hit'):.1%} | band +{imp}/-{wors} "
                f"| balanced miss={_rate(rows, 'balanced_off_miss'):.1%} (Phase 2)"
            )
        else:
            lines.append("  (no rows)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-combos", type=int, default=12_000)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "data/reports/audit_aisha_round_cohorts_fast.txt",
    )
    args = parser.parse_args()

    cache: dict[tuple[str, int], EvalRow] = {}
    strengths: dict[tuple[str, int], int] = {}
    t0 = time.monotonic()
    scanned = 0
    for root in SAMPLE_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("fatbeans*aisha*.json")):
            scanned += 1
            try:
                events = parse_fatbeans_capture(path)
            except OSError:
                continue
            if _hero_from_events(events) != "aisha":
                continue
            pre_batches = [b for b in live_batches_from_fatbeans_events(events) if b.phase != "settled"]
            settlement = _settlement_breakdown(events)
            if not settlement or not pre_batches:
                continue
            q6v = int(settlement.get("values", {}).get(6, 0) or 0)
            q6c = int(settlement.get("counts", {}).get(6, 0) or 0)
            if q6v > 2_000_000 or q6c > 3:
                continue
            map_id = _map_id_from_events(events)
            for rnd in (1, 2, 3, 4, 5):
                if len(pre_batches) < rnd:
                    continue
                prefix = pre_batches[:rnd]
                sort_id = _prefix_sort_id(prefix)
                pe = _events_through_sort(events, sort_id) if sort_id else events
                snap = _build_snapshot(hero="aisha", events=pe, prefix_batches=prefix, map_id=map_id)
                off = _run(snap, "off", max_combos=args.max_combos)
                if str(off.get("status") or "") in {"missing_total_count", "no_reachable_combo"}:
                    continue
                strengths[(path.name, rnd)] = _evidence_strength(off)
                band = off if rnd < 3 else _run(snap, "band", max_combos=args.max_combos)
                q_ranges = off.get("quality_count_ranges") if isinstance(off.get("quality_count_ranges"), dict) else {}
                ev = off.get("evidence") if isinstance(off.get("evidence"), dict) else {}
                exact = ev.get("total_count") not in (None, "")
                il, im, ih = _total_items_range(off, q_ranges, total_count_exact=exact, evidence=ev)
                tc, ti, tv = int(settlement["total_cells"]), int(settlement["total_items"]), int(settlement["total_value"])
                cache[(path.name, rnd)] = EvalRow(
                    file=path.name,
                    eval_round=rnd,
                    truth_cells=tc,
                    truth_items=ti,
                    cells_off_hit=_truth_in_range(tc, *_triplet(off, "total_grid_range")),
                    cells_band_hit=_truth_in_range(tc, *_triplet(band, "total_grid_range")),
                    items_off_hit=_truth_in_range(ti, il, im, ih),
                    balanced_off_miss=_balanced_miss(off, tv),
                )
            if scanned % 15 == 0:
                print(f"[{time.monotonic()-t0:4.0f}s] {scanned} files, {len(cache)} rows", file=sys.stderr, flush=True)

    report = format_report(cache, strengths)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"wrote {args.report} ({time.monotonic()-t0:.0f}s)", file=sys.stderr)


if __name__ == "__main__":
    main()
