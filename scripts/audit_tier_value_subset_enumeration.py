#!/usr/bin/env python3
"""Audit tier value → (count, cells) subset enumeration feasibility and cost.

Uses extracted numeric fixtures only (no snapshot replay). See
``data/fixtures/tier_value_subset_audit_cases.json``.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT / "data" / "fixtures" / "tier_value_subset_audit_cases.json"
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bidking_lab.inference.quality_combo_presolve import (  # noqa: E402
    is_quality_combo_reachable,
    load_quality_combo_presolve,
)
from bidking_lab.inference.tier_value_subset import (  # noqa: E402
    benchmark_pool_scaling,
    enumerate_avg_value_combos,
    enumerate_exact_value_combos,
    filter_candidates_by_presolve_cells,
    load_maps_summary,
    quality_pool_catalog,
    quality_pool_for_map,
    resolve_tables_dir,
)


def _ensure_utf8_stdio() -> None:
    if sys.platform != "win32":
        return
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


@dataclass(frozen=True)
class AuditCase:
    label: str
    map_id: int
    quality: int
    mode: str  # exact | avg
    value: float
    truth_count: int | None = None
    truth_cells: int | None = None
    max_count: int = 12
    source: str = ""


def _load_cases(path: Path) -> tuple[AuditCase, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError(f"expected cases list in {path}")
    cases: list[AuditCase] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cases.append(
            AuditCase(
                label=str(row.get("label") or ""),
                map_id=int(row["map_id"]),
                quality=int(row["quality"]),
                mode=str(row["mode"]),
                value=float(row["value"]),
                truth_count=(
                    int(row["truth_count"])
                    if row.get("truth_count") not in (None, "")
                    else None
                ),
                truth_cells=(
                    int(row["truth_cells"])
                    if row.get("truth_cells") not in (None, "")
                    else None
                ),
                max_count=int(row.get("max_count") or 12),
                source=str(row.get("source") or ""),
            )
        )
    return tuple(cases)


def _summarize_case(case: AuditCase, presolve: dict[str, object]) -> dict[str, object]:
    pool, pool_source = quality_pool_for_map(case.map_id, case.quality)
    maps = load_maps_summary()
    max_count = min(
        case.max_count,
        maps.get(case.map_id, {}).get("items_max", 40) or 40,
    )
    if case.mode == "exact":
        stats = enumerate_exact_value_combos(
            pool,
            int(case.value),
            max_count=max_count,
            tolerance=0,
        )
    else:
        stats = enumerate_avg_value_combos(
            pool,
            float(case.value),
            max_count=max_count,
            product_tolerance=0.51,
        )
    filtered = filter_candidates_by_presolve_cells(
        stats.candidates,
        presolve_payload=presolve,
        map_id=case.map_id,
        quality=case.quality,
    )
    unique = stats.unique_count_cells
    unique_filtered = tuple(sorted({(c.count, c.cells) for c in filtered}))
    truth_pair = (
        (case.truth_count, case.truth_cells)
        if case.truth_count is not None and case.truth_cells is not None
        else None
    )
    truth_count_only = case.truth_count
    return {
        "label": case.label,
        "source": case.source,
        "map_id": case.map_id,
        "quality": case.quality,
        "mode": case.mode,
        "input_value": case.value,
        "pool_source": pool_source,
        "pool_size": len(pool),
        "max_count": max_count,
        "elapsed_ms": stats.elapsed_ms,
        "nodes_visited": stats.nodes_visited,
        "candidate_count": len(stats.candidates),
        "unique_count_cells": unique,
        "unique_counts": stats.unique_counts,
        "filtered_unique_count_cells": unique_filtered,
        "truth_count_cells": truth_pair,
        "truth_count": truth_count_only,
        "truth_in_candidates": truth_pair in unique if truth_pair else None,
        "truth_count_in_unique_counts": (
            truth_count_only in stats.unique_counts if truth_count_only is not None else None
        ),
        "truth_reachable_after_presolve": (
            is_quality_combo_reachable(
                presolve,
                map_id=case.map_id,
                quality=case.quality,
                count=case.truth_count,
                cells=case.truth_cells,
            )
            if truth_pair
            else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help="JSON fixture with extracted numeric inputs",
    )
    parser.add_argument(
        "--scaling",
        action="store_true",
        help="Also run synthetic pool-size scaling benchmark",
    )
    args = parser.parse_args()

    _ensure_utf8_stdio()
    tables = resolve_tables_dir()
    cases = _load_cases(args.cases)
    print(f"tables_dir={tables or 'NONE (catalog fallback)'}")
    print(f"cases={args.cases} ({len(cases)} rows, numeric-only)")
    presolve_path = ROOT / "data" / "processed" / "quality_combo_presolve_q456.json"
    presolve = load_quality_combo_presolve(presolve_path)

    print("\n=== Case audit ===")
    case_rows = [_summarize_case(case, presolve) for case in cases]
    for row in case_rows:
        print(json.dumps(row, ensure_ascii=False))

    scaling: list[dict[str, object]] = []
    if args.scaling:
        print("\n=== Pool scaling benchmark (q5 catalog, synthetic target) ===")
        q5_pool, _ = quality_pool_catalog(5)
        scaling = benchmark_pool_scaling(q5_pool, sizes=(20, 40, 48), max_count=8)
        for row in scaling:
            print(json.dumps(row, ensure_ascii=False))

    out_path = ROOT / "data" / "reports" / "audit_tier_value_subset_enumeration.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "experimental_deferred",
        "tables_dir": str(tables) if tables else None,
        "cases_fixture": str(args.cases),
        "cases": case_rows,
        "scaling_q5_catalog": scaling,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
