"""Compare offline q6 residual boost configurations on Fatbeans samples."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import evaluate_fatbeans_v2_samples as evaluator


_CONFIGS: tuple[tuple[str, float, str], ...] = (
    ("baseline", 1.0, "all"),
    ("global_b3", 3.0, "all"),
    ("profile_b3", 3.0, "shipwreck_profile_v1"),
    ("profile_b5", 5.0, "shipwreck_profile_v1"),
)


def _comparison_row(
    label: str,
    boost: float,
    gate: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    boost_summary = summary.get("q6_residual_boost_experiment") or {}
    return {
        "label": label,
        "boost": boost,
        "gate": gate,
        "files": summary.get("files"),
        "ok": summary.get("ok"),
        "valued": summary.get("valued"),
        "zero_match": summary.get("zero_match"),
        "decision_value_mae": summary.get("decision_value_mae"),
        "value_p90_coverage": summary.get("value_p90_coverage"),
        "q6_plannable_coverage": summary.get("q6_plannable_value_p90_coverage"),
        "q6_plannable_misses": summary.get("q6_plannable_p90_misses_truth"),
        "q6_no_plannable_rows": summary.get("q6_no_plannable_truth_files"),
        "q6_no_plannable_p90_positive_rate": summary.get(
            "q6_no_plannable_p90_positive_rate"
        ),
        "q6_no_plannable_p90_positive_median": summary.get(
            "q6_no_plannable_p90_positive_median"
        ),
        "active_rows": boost_summary.get("active_rows"),
        "active_no_q6_rows": boost_summary.get("active_no_q6_rows"),
        "active_no_q6_p90_positive_rate": boost_summary.get(
            "active_no_q6_p90_positive_rate"
        ),
    }


def _with_baseline_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    baseline = rows[0]
    for row in rows:
        row["delta_q6_plannable_coverage"] = _delta(
            row.get("q6_plannable_coverage"),
            baseline.get("q6_plannable_coverage"),
        )
        row["delta_q6_plannable_misses"] = _delta(
            row.get("q6_plannable_misses"),
            baseline.get("q6_plannable_misses"),
        )
        row["delta_decision_value_mae"] = _delta(
            row.get("decision_value_mae"),
            baseline.get("decision_value_mae"),
        )
        row["delta_no_q6_positive_rate"] = _delta(
            row.get("q6_no_plannable_p90_positive_rate"),
            baseline.get("q6_no_plannable_p90_positive_rate"),
        )
        row["delta_no_q6_positive_median"] = _delta(
            row.get("q6_no_plannable_p90_positive_median"),
            baseline.get("q6_no_plannable_p90_positive_median"),
        )
    return rows


def _delta(value: Any, baseline: Any) -> float | int | None:
    if value is None or baseline is None:
        return None
    if isinstance(value, int) and isinstance(baseline, int):
        return value - baseline
    return round(float(value) - float(baseline), 4)


def _evaluate_config(
    paths: list[Path],
    *,
    label: str,
    boost: float,
    gate: str,
    tables: Any,
    combo_presolve: Any,
    trials: int,
    seed: int,
    cells_tol: int,
    count_tol: int,
) -> dict[str, Any]:
    rows = [
        evaluator.evaluate_path(
            path,
            tables=tables,
            n_trials=trials,
            seed=seed,
            cells_tol=cells_tol,
            count_tol=count_tol,
            combo_presolve=combo_presolve,
            q6_residual_boost=boost,
            q6_residual_boost_gate=gate,
        )
        for path in paths
    ]
    summary = evaluator._summary(rows)
    return _comparison_row(label, boost, gate, summary)


def _write_csv(rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare q6 residual boost configs on Fatbeans samples.",
    )
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--cells-tol", type=int, default=8)
    parser.add_argument("--count-tol", type=int, default=3)
    parser.add_argument(
        "--combo-presolve",
        default=str(evaluator._DEFAULT_COMBO_PRESOLVE_PATH),
    )
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    args = parser.parse_args()

    raw_paths = evaluator._expand_cli_paths(args.paths) if args.paths else evaluator._default_paths()
    paths = list(evaluator._iter_unique(raw_paths))
    tables = evaluator.load_monitor_tables()
    combo_presolve = None
    combo_presolve_path = Path(args.combo_presolve) if args.combo_presolve else None
    if combo_presolve_path is not None and combo_presolve_path.exists():
        combo_presolve = evaluator.load_quality_combo_presolve(combo_presolve_path)

    rows = _with_baseline_deltas(
        [
            _evaluate_config(
                paths,
                label=label,
                boost=boost,
                gate=gate,
                tables=tables,
                combo_presolve=combo_presolve,
                trials=args.trials,
                seed=args.seed,
                cells_tol=args.cells_tol,
                count_tol=args.count_tol,
            )
            for label, boost, gate in _CONFIGS
        ]
    )
    if args.format == "csv":
        _write_csv(rows)
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
