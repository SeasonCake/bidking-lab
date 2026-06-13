"""Aisha evaluation by fixed round cohorts: R1, R2, R3, R4-R5.

Each row replays the capture through audit_round=N (prefix batches) and compares
ref bands vs final settlement. Phase 1 gate focuses on total_cells + total_items
at R4 (R5 reported separately inside R4-R5 cohort).

Local audit only — not shipped in Hero Ref packages.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

from pathlib import Path

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

DEFENSE_MULT_HINT = {
    1: "2.0× round-high (defense)",
    2: "1.6× round-high",
    3: "1.3× round-high",
    4: "1.1× round-high",
    5: "competitive (highest wins)",
}

ALL_EVAL_ROUNDS = (1, 2, 3, 4, 5)


@dataclass(frozen=True)
class CohortSpec:
    name: str
    eval_rounds: tuple[int, ...]
    min_file_rounds: int
    min_evidence_score: int
    phase_note: str


COHORTS: tuple[CohortSpec, ...] = (
    CohortSpec("R1", (1,), 1, 0, "early defense — high cells/items error acceptable"),
    CohortSpec("R2", (2,), 2, 0, "early defense — error tapering"),
    CohortSpec("R3", (3,), 3, 1, "pre-warehouse — layout band may apply"),
    CohortSpec("R4-R5", (4, 5), 4, 4, "primary cells/items gate — R4 focus; R5 no new skills"),
)


@dataclass(frozen=True)
class EvalRow:
    file: str
    eval_round: int
    file_total_rounds: int
    evidence_strength: int
    truth_cells: int
    truth_items: int
    truth_value: int
    cells_off_hit: bool
    cells_band_hit: bool
    items_off_hit: bool
    items_band_hit: bool
    balanced_off_miss: bool
    balanced_band_miss: bool
    cells_off_gap: int | None
    cells_band_gap: int | None


def _evaluate_snapshot(snapshot: dict[str, Any], *, layout_mode: str) -> dict[str, Any]:
    payload = dict(snapshot)
    payload["audit_aisha_layout_mode"] = layout_mode
    return run_reference_engine(payload, max_combos=50_000).as_dict()


def _balanced_miss(result: dict[str, Any], truth_value: int) -> bool:
    balanced = result.get("balanced")
    try:
        balanced_int = int(balanced) if balanced not in (None, "") else None
    except (TypeError, ValueError):
        balanced_int = None
    if balanced_int is None or truth_value <= 0:
        return False
    return not (int(balanced_int * 0.85) <= truth_value <= int(balanced_int * 1.15))


def _row_from_results(
    *,
    file_name: str,
    eval_round: int,
    file_total_rounds: int,
    evidence_strength: int,
    settlement: dict[str, Any],
    off: dict[str, Any],
    band: dict[str, Any],
) -> EvalRow:
    q_ranges = off.get("quality_count_ranges")
    if not isinstance(q_ranges, dict):
        q_ranges = {}
    evidence = off.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    total_count_exact = evidence.get("total_count") not in (None, "")
    items_low, items_mid, items_high = _total_items_range(
        off,
        q_ranges,
        total_count_exact=total_count_exact,
        evidence=evidence,
    )
    truth_cells = int(settlement["total_cells"])
    truth_items = int(settlement["total_items"])
    truth_value = int(settlement["total_value"])
    off_cells = _triplet(off, "total_grid_range")
    band_cells = _triplet(band, "total_grid_range")
    return EvalRow(
        file=file_name,
        eval_round=eval_round,
        file_total_rounds=file_total_rounds,
        evidence_strength=evidence_strength,
        truth_cells=truth_cells,
        truth_items=truth_items,
        truth_value=truth_value,
        cells_off_hit=_truth_in_range(truth_cells, *off_cells),
        cells_band_hit=_truth_in_range(truth_cells, *band_cells),
        items_off_hit=_truth_in_range(truth_items, items_low, items_mid, items_high),
        items_band_hit=_truth_in_range(truth_items, items_low, items_mid, items_high),
        balanced_off_miss=_balanced_miss(off, truth_value),
        balanced_band_miss=_balanced_miss(band, truth_value),
        cells_off_gap=_mid_gap(truth_cells, *off_cells),
        cells_band_gap=_mid_gap(truth_cells, *band_cells),
    )


def _passes_base_filters(
    *,
    hero: str,
    settlement: dict[str, Any] | None,
    pre_batches: list,
    min_file_rounds: int,
    max_q6_value: int,
    max_q6_count: int,
) -> bool:
    if hero != "aisha" or not settlement:
        return False
    if len(pre_batches) < min_file_rounds:
        return False
    q6_value = int(settlement.get("values", {}).get(6, 0) or 0)
    q6_count = int(settlement.get("counts", {}).get(6, 0) or 0)
    return q6_value <= max_q6_value and q6_count <= max_q6_count


def collect_all_eval_rows(
    *,
    sample_roots: tuple[Path, ...],
    max_q6_value: int,
    max_q6_count: int,
    limit: int,
    progress: bool,
) -> dict[tuple[str, int], EvalRow]:
    """Single-pass scan: cache one (off, band) pair per file × eval_round."""
    cache: dict[tuple[str, int], EvalRow] = {}
    scanned = 0
    for root in sample_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("fatbeans*aisha*.json")):
            scanned += 1
            if progress and scanned % 10 == 0:
                print(f"scanning {scanned} files, cached rows={len(cache)}", file=sys.stderr, flush=True)
            try:
                events = parse_fatbeans_capture(path)
            except OSError:
                continue
            hero = _hero_from_events(events)
            pre_batches = [b for b in live_batches_from_fatbeans_events(events) if b.phase != "settled"]
            settlement = _settlement_breakdown(events)
            if not _passes_base_filters(
                hero=hero,
                settlement=settlement,
                pre_batches=pre_batches,
                min_file_rounds=1,
                max_q6_value=max_q6_value,
                max_q6_count=max_q6_count,
            ):
                continue
            map_id = _map_id_from_events(events)
            for eval_round in ALL_EVAL_ROUNDS:
                if len(pre_batches) < eval_round:
                    continue
                prefix_batches = pre_batches[:eval_round]
                sort_id = _prefix_sort_id(prefix_batches)
                prefix_events = _events_through_sort(events, sort_id) if sort_id else events
                snapshot = _build_snapshot(
                    hero="aisha",
                    events=prefix_events,
                    prefix_batches=prefix_batches,
                    map_id=map_id,
                )
                off = _evaluate_snapshot(snapshot, layout_mode="off")
                if str(off.get("status") or "") in {"missing_total_count", "no_reachable_combo"}:
                    continue
                band = _evaluate_snapshot(snapshot, layout_mode="band")
                cache[(path.name, eval_round)] = _row_from_results(
                    file_name=path.name,
                    eval_round=eval_round,
                    file_total_rounds=len(pre_batches),
                    evidence_strength=_evidence_strength(off),
                    settlement=settlement,
                    off=off,
                    band=band,
                )
            if limit and len({key[0] for key in cache}) >= limit:
                return cache
    return cache


def assign_cohort_rows(cache: dict[tuple[str, int], EvalRow], spec: CohortSpec) -> list[EvalRow]:
    rows: list[EvalRow] = []
    for eval_round in spec.eval_rounds:
        for (file_name, rnd), row in cache.items():
            if rnd != eval_round:
                continue
            if row.file_total_rounds < spec.min_file_rounds:
                continue
            if row.evidence_strength < spec.min_evidence_score:
                continue
            rows.append(row)
    return rows


def _rate(rows: list[EvalRow], attr: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if getattr(row, attr)) / len(rows)


def _avg_gap(rows: list[EvalRow], attr: str) -> float:
    gaps = [abs(getattr(row, attr)) for row in rows if getattr(row, attr) is not None]
    return sum(gaps) / len(gaps) if gaps else 0.0


def _band_cells_improved(rows: list[EvalRow]) -> tuple[int, int]:
    improved = sum(1 for row in rows if not row.cells_off_hit and row.cells_band_hit)
    worsened = sum(1 for row in rows if row.cells_off_hit and not row.cells_band_hit)
    return improved, worsened


def format_cohort_block(spec: CohortSpec, rows: list[EvalRow]) -> list[str]:
    lines = [
        f"## {spec.name}  ({spec.phase_note})",
        f"rows={len(rows)}",
    ]
    if spec.eval_rounds == (4, 5) and rows:
        for rnd in (4, 5):
            sub = [row for row in rows if row.eval_round == rnd]
            if not sub:
                continue
            imp, wors = _band_cells_improved(sub)
            hint = DEFENSE_MULT_HINT.get(rnd, "")
            lines.append(
                f"  R{rnd} slice n={len(sub)} | cells hit off={_rate(sub, 'cells_off_hit'):.1%} "
                f"band={_rate(sub, 'cells_band_hit'):.1%} | items off={_rate(sub, 'items_off_hit'):.1%} "
                f"band={_rate(sub, 'items_band_hit'):.1%} | band +{imp}/-{wors} | {hint}"
            )
    if not rows:
        lines.append("  (no eligible rows)")
        return lines

    imp, wors = _band_cells_improved(rows)
    rnd_hints = ", ".join(
        f"R{r}={DEFENSE_MULT_HINT.get(r, '')}" for r in spec.eval_rounds if r in DEFENSE_MULT_HINT
    )
    lines.extend(
        [
            "",
            "metric              | off (B)  | band (C2) | band Δ cells",
            "-" * 62,
            f"total_cells hit     | {_rate(rows, 'cells_off_hit'):7.1%} | "
            f"{_rate(rows, 'cells_band_hit'):8.1%} | +{imp} / -{wors}",
            f"total_items hit     | {_rate(rows, 'items_off_hit'):7.1%} | "
            f"{_rate(rows, 'items_band_hit'):8.1%} | (band unchanged)",
            f"avg |cells mid_gap| | {_avg_gap(rows, 'cells_off_gap'):7.1f} | "
            f"{_avg_gap(rows, 'cells_band_gap'):8.1f} |",
            f"balanced miss ±15%  | {_rate(rows, 'balanced_off_miss'):7.1%} | "
            f"{_rate(rows, 'balanced_band_miss'):8.1%} | Phase 2 (D1 bid weight)",
            "",
            f"defense hint: {rnd_hints}",
        ]
    )
    return lines


def format_report(all_rows: dict[str, list[EvalRow]]) -> str:
    lines = [
        "Aisha round-cohort audit (fixed eval rounds, settlement truth)",
        "Phase 1 active gate: total_cells + total_items at R4 slice (inside R4-R5 cohort)",
        "Phase 2 deferred: D1 bid weight / balanced stability",
        "",
        "cohorts: R1 | R2 | R3 | R4-R5 (R4 primary, R5 sub-slice)",
        "layout: off vs band only (target/shadow omitted in phase 1)",
        "",
    ]
    for spec in COHORTS:
        lines.extend(format_cohort_block(spec, all_rows.get(spec.name, [])))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "data/reports/audit_aisha_round_cohorts.txt",
    )
    parser.add_argument("--max-q6-value", type=int, default=2_000_000)
    parser.add_argument("--max-q6-count", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0, help="Limit unique files scanned (0=all)")
    parser.add_argument("--progress", action="store_true", help="Print scan progress to stderr")
    args = parser.parse_args()

    cache = collect_all_eval_rows(
        sample_roots=SAMPLE_ROOTS,
        max_q6_value=args.max_q6_value,
        max_q6_count=args.max_q6_count,
        limit=args.limit,
        progress=args.progress,
    )
    all_rows: dict[str, list[EvalRow]] = {}
    for spec in COHORTS:
        all_rows[spec.name] = assign_cohort_rows(cache, spec)

    report = format_report(all_rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"wrote {args.report}")


if __name__ == "__main__":
    main()
