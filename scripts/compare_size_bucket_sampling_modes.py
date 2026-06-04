"""Compare size-bucket evidence integration modes on settlement truth.

Modes:
- none: no size-bucket evidence
- score_only: current production (post-trial weighting)
- prefill: pre-place footprint items + cap + score (experimental)
- pool_mask: zero residual pool mass for locked footprints + score (experimental)

Uses simulated tool readings from settlement inventory (oracle) plus
warehouse/item count from truth.
"""

from __future__ import annotations

import argparse
import io
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from bidking_lab.inference.observation import SessionObs
from bidking_lab.inference.size_avg_evidence import size_bucket_value_stats
from bidking_lab.inference.v2 import (
    EvidenceFact,
    EvidenceStoreBuilder,
    RuntimeEvidence,
    build_residual_problem,
    estimate_posterior_v2,
    evidence_store_from_fatbeans_events,
)
from bidking_lab.live.fatbeans import parse_fatbeans_capture
from bidking_lab.live.monitor import load_monitor_tables

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SettlementCase:
    file_name: str
    map_id: int
    truth: object
    warehouse_cells: int
    total_items: int
    footprint_cells: int
    footprint_count: int
    footprint_avg: float
    footprint_value_sum: int


def _truth_from_inventory(events, items) -> tuple[object, int, int] | None:
    from bidking_lab.inference.ground_truth import BucketTruth, SessionTruth

    state = None
    map_id = None
    for st in events.states:
        if st.map_id is not None:
            map_id = int(st.map_id)
        if st.inventory_items:
            state = st
    if state is None or map_id is None:
        return None
    buckets: dict = {}
    wh = 0
    for inv in state.inventory_items:
        item = items.get(int(inv.item_id))
        if item is None:
            continue
        cells = int(inv.cells) if inv.cells else item.shape_w * item.shape_h
        wh += cells
        q = int(item.quality)
        bucket = buckets.setdefault(q, BucketTruth(quality=q))
        bucket.count += 1
        bucket.total_cells += cells
        bucket.value_sum += int(item.value)
        bucket.items.append(item)
    truth = SessionTruth(
        map_id=map_id,
        map_name=str(map_id),
        warehouse_total_cells=wh,
        buckets=buckets,
    )
    return truth, map_id, wh


def _oracle_store_for_footprint(
    truth,
    *,
    footprint: int,
    full_outline: bool,
) -> EvidenceStoreBuilder:
    builder = EvidenceStoreBuilder()
    count, value_sum = size_bucket_value_stats(truth, footprint)
    if count <= 0:
        return builder
    avg = value_sum / count
    action_id = {1: 100169, 2: 100170, 3: 100171, 4: 100172, 6: 100173}[footprint]
    builder.add_fact(
        EvidenceFact(
            kind="action",
            key=str(action_id),
            value=float(avg),
            source=f"action:{action_id}",
            strength="soft",
        )
    )
    if full_outline:
        for bucket in truth.buckets.values():
            for item in bucket.items:
                if item.shape_w * item.shape_h != footprint:
                    continue
                builder.add_item(
                    RuntimeEvidence(
                        runtime_id=item.item_id,
                        item_id=item.item_id,
                        quality=item.quality,
                        cells=footprint,
                        shape_key=f"{item.shape_w}{item.shape_h}",
                        sources=("action:100100",),
                    )
                )
    return builder


def _obs_from_truth(truth, *, full_outline: bool) -> SessionObs:
    total = sum(bucket.count for bucket in truth.buckets.values())
    return SessionObs(
        map_id=truth.map_id,
        hero="aisha",
        warehouse_total_cells=truth.warehouse_total_cells,
        warehouse_total_cells_tolerance=0 if full_outline else 8,
        total_item_count=total if full_outline else None,
    )


def _collect_cases(paths: tuple[Path, ...], footprint: int) -> list[SettlementCase]:
    tables = load_monitor_tables()
    items = tables.items
    cases: list[SettlementCase] = []
    for path in paths:
        try:
            events = parse_fatbeans_capture(path)
        except Exception:
            continue
        parsed = _truth_from_inventory(events, items)
        if parsed is None:
            continue
        truth, map_id, wh = parsed
        count, value_sum = size_bucket_value_stats(truth, footprint)
        if count < 2:
            continue
        cases.append(
            SettlementCase(
                file_name=path.name,
                map_id=map_id,
                truth=truth,
                warehouse_cells=wh,
                total_items=sum(b.count for b in truth.buckets.values()),
                footprint_cells=footprint,
                footprint_count=count,
                footprint_avg=value_sum / count,
                footprint_value_sum=value_sum,
            )
        )
    return cases


def _run_mode(
    case: SettlementCase,
    mode: str,
    *,
    tables,
    n_trials: int,
    seed: int,
    full_outline: bool,
):
    builder = _oracle_store_for_footprint(
        case.truth,
        footprint=case.footprint_cells,
        full_outline=full_outline,
    )
    store = builder.build()
    obs = _obs_from_truth(case.truth, full_outline=full_outline)
    prefill = mode == "prefill"
    mask = mode == "pool_mask"
    if mode == "none":
        store = EvidenceStoreBuilder().build()
    report = estimate_posterior_v2(
        case.map_id,
        obs,
        store,
        maps=tables.maps,
        drops=tables.drops,
        items=tables.items,
        n_trials=n_trials,
        seed=seed,
        size_bucket_prefill=prefill,
        size_bucket_mask_residual_pool=mask,
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--footprint", type=int, default=4)
    parser.add_argument("--n-trials", type=int, default=120)
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    sample_dir = ROOT / "data" / "samples" / "fatbeans"
    paths = tuple(sorted(sample_dir.rglob("*.json")))[:200]
    cases = _collect_cases(paths, args.footprint)[: args.max_cases]
    if not cases:
        print("No cases with footprint count>=2")
        return 1

    tables = load_monitor_tables()
    modes = ("none", "score_only", "prefill", "pool_mask")
    rows: list[dict] = []

    print(f"footprint={args.footprint}cell cases={len(cases)} trials={args.n_trials}")
    print("mode,matched_rate,total_value_mae,footprint_sum_mae,wh_cells_mae,decision_p50_median")
    for case in cases:
        truth_total = case.truth.total_value()
        for mode in modes:
            for outline in (False, True):
                label = f"{mode}{'_outline' if outline else ''}"
                report = _run_mode(
                    case,
                    mode,
                    tables=tables,
                    n_trials=args.n_trials,
                    seed=args.seed + hash(case.file_name) % 1000,
                    full_outline=outline,
                )
                if report.n_matched <= 0:
                    rows.append(
                        {
                            "case": case.file_name,
                            "mode": label,
                            "matched": 0,
                            "total_mae": None,
                            "fp_mae": None,
                            "wh_mae": None,
                        }
                    )
                    continue
                # single-trial oracle check via problem build + one sample not needed;
                # use decision P50 vs truth
                dec = report.decision_value.p50 if report.decision_value else None
                rows.append(
                    {
                        "case": case.file_name,
                        "mode": label,
                        "matched": report.n_matched / max(1, report.n_total),
                        "total_mae": abs(dec - truth_total) if dec is not None else None,
                        "fp_mae": None,
                        "wh_mae": None,
                        "dec_p50": dec,
                        "truth_total": truth_total,
                        "truth_fp_sum": case.footprint_value_sum,
                    }
                )

    by_mode: dict[str, list[float]] = {}
    match_by_mode: dict[str, list[float]] = {}
    for row in rows:
        mode = row["mode"]
        if row["total_mae"] is not None:
            by_mode.setdefault(mode, []).append(float(row["total_mae"]))
        match_by_mode.setdefault(mode, []).append(float(row["matched"]))

    print()
    print("=== Aggregated (median) ===")
    for mode in sorted(by_mode):
        maes = by_mode[mode]
        matches = match_by_mode.get(mode, [])
        print(
            f"{mode:20s}  match_median={statistics.median(matches):.3f}  "
            f"total_value_mae_median={statistics.median(maes):,.0f}  n={len(maes)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
