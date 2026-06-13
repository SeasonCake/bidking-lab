"""20-sample fixed-round cohort spot audit (fast, curated pool only).

Picks ~10 full-round (>=5) + ~10 representative gap rows, evaluates at R1–R5 once,
compares layout=off (baseline / no C2) vs layout=band (Phase 1 candidate).
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
    _mid_gap,
    _prefix_sort_id,
    _settlement_breakdown,
    _total_items_range,
    _triplet,
    _truth_in_range,
)

COHORTS = (
    ("R1", (1,), 0),
    ("R2", (2,), 0),
    ("R3", (3,), 1),
    ("R4-R5", (4, 5), 4),
)


@dataclass
class SpotRow:
    file: str
    eval_round: int
    truth_cells: int
    truth_items: int
    off_cells_hit: bool
    band_cells_hit: bool
    off_items_hit: bool
    off_balanced_miss: bool


def _resolve_paths(filenames: set[str]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for root in SAMPLE_ROOTS:
        if not root.is_dir():
            continue
        for path in root.glob("fatbeans*aisha*.json"):
            if path.name in filenames and path.name not in out:
                out[path.name] = path
    return out


def _pick_sample_files(*, target: int) -> list[str]:
    five_round: list[str] = []
    four_round: list[str] = []
    for root in SAMPLE_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("fatbeans*aisha*5rounds*.json")):
            five_round.append(path.name)
        for path in sorted(root.glob("fatbeans*aisha*4rounds*.json")):
            four_round.append(path.name)
    chosen: list[str] = []
    for name in five_round:
        if name not in chosen:
            chosen.append(name)
        if len(chosen) >= max(8, target // 2):
            break
    for name in four_round:
        if name not in chosen:
            chosen.append(name)
        if len(chosen) >= target:
            break
    return chosen[:target]


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


def collect_spot_rows(
    filenames: list[str],
    *,
    max_combos: int,
    min_evidence_by_round: dict[int, int],
) -> list[SpotRow]:
    paths = _resolve_paths(set(filenames))
    rows: list[SpotRow] = []
    for file_name in filenames:
        path = paths.get(file_name)
        if path is None:
            continue
        try:
            events = parse_fatbeans_capture(path)
        except OSError:
            continue
        if _hero_from_events(events) != "aisha":
            continue
        pre_batches = [b for b in live_batches_from_fatbeans_events(events) if b.phase != "settled"]
        settlement = _settlement_breakdown(events)
        if not settlement:
            continue
        map_id = _map_id_from_events(events)
        for rnd in (1, 2, 3, 4, 5):
            if len(pre_batches) < rnd:
                continue
            prefix = pre_batches[:rnd]
            sort_id = _prefix_sort_id(prefix)
            pe = _events_through_sort(events, sort_id) if sort_id else events
            snap = _build_snapshot(hero="aisha", events=pe, prefix_batches=prefix, map_id=map_id)
            off = _run(snap, "off", max_combos=max_combos)
            if str(off.get("status") or "") in {"missing_total_count", "no_reachable_combo"}:
                continue
            if _evidence_strength(off) < min_evidence_by_round.get(rnd, 0):
                continue
            band = off if rnd < 3 else _run(snap, "band", max_combos=max_combos)
            q_ranges = off.get("quality_count_ranges") if isinstance(off.get("quality_count_ranges"), dict) else {}
            ev = off.get("evidence") if isinstance(off.get("evidence"), dict) else {}
            exact = ev.get("total_count") not in (None, "")
            il, im, ih = _total_items_range(off, q_ranges, total_count_exact=exact, evidence=ev)
            tc, ti, tv = int(settlement["total_cells"]), int(settlement["total_items"]), int(settlement["total_value"])
            rows.append(
                SpotRow(
                    file=file_name,
                    eval_round=rnd,
                    truth_cells=tc,
                    truth_items=ti,
                    off_cells_hit=_truth_in_range(tc, *_triplet(off, "total_grid_range")),
                    band_cells_hit=_truth_in_range(tc, *_triplet(band, "total_grid_range")),
                    off_items_hit=_truth_in_range(ti, il, im, ih),
                    off_balanced_miss=_balanced_miss(off, tv),
                )
            )
    return rows


def _rate(rows: list[SpotRow], attr: str) -> float:
    return sum(1 for row in rows if getattr(row, attr)) / len(rows) if rows else 0.0


def _band_delta(rows: list[SpotRow]) -> tuple[int, int]:
    imp = sum(1 for row in rows if not row.off_cells_hit and row.band_cells_hit)
    wors = sum(1 for row in rows if row.off_cells_hit and not row.band_cells_hit)
    return imp, wors


def format_report(*, sample_files: list[str], rows: list[SpotRow], elapsed_s: float) -> str:
    lines = [
        "Aisha round-cohort SPOT audit (20-sample curated, fixed eval rounds)",
        f"sample_files={len(sample_files)} spot_rows={len(rows)} runtime={elapsed_s:.0f}s",
        "",
        "baseline = layout off (no C2 band) | candidate = layout band (Phase 1 live default for Aisha)",
        "",
    ]
    min_evidence = {1: 0, 2: 0, 3: 1, 4: 4, 5: 4}
    for label, rounds, min_ev in COHORTS:
        cohort_rows = [row for row in rows if row.eval_round in rounds]
        imp, wors = _band_delta(cohort_rows)
        lines.append(f"## {label}")
        lines.append(f"rows={len(cohort_rows)}")
        if label == "R4-R5":
            for rnd in (4, 5):
                sub = [row for row in cohort_rows if row.eval_round == rnd]
                if not sub:
                    continue
                si, sw = _band_delta(sub)
                lines.append(
                    f"  R{rnd} n={len(sub)} | cells off={_rate(sub,'off_cells_hit'):.1%} "
                    f"band={_rate(sub,'band_cells_hit'):.1%} | items off={_rate(sub,'off_items_hit'):.1%} "
                    f"| band +{si}/-{sw}"
                )
        lines.append(
            f"  ALL | cells off={_rate(cohort_rows,'off_cells_hit'):.1%} → band={_rate(cohort_rows,'band_cells_hit'):.1%} "
            f"(+{imp}/-{wors}) | items off={_rate(cohort_rows,'off_items_hit'):.1%} "
            f"| balanced miss={_rate(cohort_rows,'off_balanced_miss'):.1%} (Phase 2)"
        )
        lines.append("")
    all_imp, all_wors = _band_delta(rows)
    lines.extend(
        [
            "## vs baseline (all spot rows)",
            f"cells hit: off={_rate(rows,'off_cells_hit'):.1%} band={_rate(rows,'band_cells_hit'):.1%} (+{all_imp}/-{all_wors})",
            "",
            "148 curated penultimate (prior full batch): off=34.5% band=43.9% (+14/0)",
            "",
            "sample list:",
            *[f"  - {name}" for name in sample_files],
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--max-combos", type=int, default=12_000)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "data/reports/audit_aisha_round_cohorts_sample20.txt",
    )
    args = parser.parse_args()
    t0 = time.monotonic()
    sample_files = _pick_sample_files(target=args.sample_size)
    min_evidence_by_round = {1: 0, 2: 0, 3: 1, 4: 4, 5: 4}
    rows = collect_spot_rows(
        sample_files,
        max_combos=args.max_combos,
        min_evidence_by_round=min_evidence_by_round,
    )
    # Apply cohort min evidence filter post-hoc by re-tagging — rows already filtered per-round in collect
    report = format_report(sample_files=sample_files, rows=rows, elapsed_s=time.monotonic() - t0)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"wrote {args.report}")


if __name__ == "__main__":
    main()
