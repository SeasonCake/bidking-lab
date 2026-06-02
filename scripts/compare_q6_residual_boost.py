"""Compare offline q6 residual boost configurations on Fatbeans samples."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import evaluate_fatbeans_v2_samples as evaluator


_DEFAULT_CONFIGS: tuple[tuple[str, float, str, float, str], ...] = (
    ("baseline", 1.0, "all", 0.0, "all"),
    ("global_b3", 3.0, "all", 0.0, "all"),
    ("profile_b3", 3.0, "shipwreck_profile_v1", 0.0, "all"),
    ("profile_b5", 5.0, "shipwreck_profile_v1", 0.0, "all"),
)
_EXTRA_CONFIGS: tuple[tuple[str, float, str, float, str], ...] = (
    ("aisha_deep_b5", 5.0, "aisha_shipwreck_deep_v1", 0.0, "all"),
    ("aisha_deep_floor1", 1.0, "all", 1.0, "aisha_shipwreck_deep_v1"),
    ("aisha_hidden_floor1", 1.0, "all", 1.0, "aisha_hidden_v1"),
    ("aisha_deep_hidden_floor1", 1.0, "all", 1.0, "aisha_deep_or_hidden_v1"),
    ("aisha_hidden_floor15", 1.0, "all", 1.5, "aisha_hidden_v1"),
    ("aisha_villa_floor05", 1.0, "all", 0.5, "aisha_villa_shape_layout_v1"),
    ("aisha_villa_floor075", 1.0, "all", 0.75, "aisha_villa_shape_layout_v1"),
)
_CONFIGS = _DEFAULT_CONFIGS + _EXTRA_CONFIGS
_CONFIG_LABELS = tuple(
    label for label, _boost, _gate, _floor_ratio, _floor_gate in _CONFIGS
)


def _selected_configs(
    labels: list[str] | None,
) -> tuple[tuple[str, float, str, float, str], ...]:
    if not labels:
        return _DEFAULT_CONFIGS
    selected = set(labels)
    return tuple(config for config in _CONFIGS if config[0] in selected)


def _progress(message: str, *, enabled: bool = True) -> None:
    if enabled:
        print(f"[q6-boost] {message}", file=sys.stderr, flush=True)


def _comparison_row(
    label: str,
    boost: float,
    gate: str,
    summary: dict[str, Any],
    *,
    floor_ratio: float = 0.0,
    floor_gate: str = "all",
) -> dict[str, Any]:
    boost_summary = summary.get("q6_residual_boost_experiment") or {}
    floor_summary = summary.get("q6_residual_prior_floor_sampler_experiment") or {}
    feasibility = summary.get("sample_feasibility") or {}
    case_breakdown = summary.get("case_breakdown") or {}
    normal_case = case_breakdown.get("normal_case") or {}
    early_diagnostic = case_breakdown.get("early_diagnostic") or {}
    tail_event = case_breakdown.get("tail_event") or {}
    hidden_case = case_breakdown.get("hidden_case") or {}
    no_q6_control = case_breakdown.get("no_q6_control") or {}
    zero_q6_proven = case_breakdown.get("zero_q6_proven") or {}
    high_info_value_miss = case_breakdown.get("high_info_value_miss") or {}
    high_info_q6_miss = case_breakdown.get("high_info_q6_miss") or {}
    return {
        "label": label,
        "boost": boost,
        "gate": gate,
        "prior_floor_ratio": floor_ratio,
        "prior_floor_gate": floor_gate,
        "files": summary.get("files"),
        "ok": summary.get("ok"),
        "valued": summary.get("valued"),
        "zero_match": summary.get("zero_match"),
        "decision_value_mae": summary.get("decision_value_mae"),
        "calibration_decision_value_mae": feasibility.get(
            "calibration_decision_value_mae"
        ),
        "value_p90_coverage": summary.get("value_p90_coverage"),
        "q6_plannable_coverage": summary.get("q6_plannable_value_p90_coverage"),
        "q6_plannable_misses": summary.get("q6_plannable_p90_misses_truth"),
        "calibration_q6_plannable_coverage": feasibility.get(
            "calibration_q6_plannable_value_p90_coverage"
        ),
        "calibration_q6_plannable_misses": feasibility.get(
            "calibration_q6_plannable_p90_misses_truth"
        ),
        "early_rows": feasibility.get("early_rows"),
        "single_round_rows": feasibility.get("single_round_rows"),
        "early_large_cells_gap_rows": feasibility.get("early_large_cells_gap_rows"),
        "normal_case_rows": normal_case.get("rows"),
        "normal_case_decision_value_mae": normal_case.get("decision_value_mae"),
        "normal_case_value_p90_coverage": normal_case.get("value_p90_coverage"),
        "normal_case_q6_plannable_coverage": normal_case.get(
            "q6_plannable_coverage"
        ),
        "normal_case_q6_plannable_misses": normal_case.get(
            "q6_plannable_miss_rows"
        ),
        "early_diagnostic_rows": early_diagnostic.get("rows"),
        "early_diagnostic_cells_p50_mae": early_diagnostic.get("cells_p50_mae"),
        "tail_event_rows": tail_event.get("rows"),
        "tail_event_decision_value_mae": tail_event.get("decision_value_mae"),
        "tail_event_q6_plannable_coverage": tail_event.get(
            "q6_plannable_coverage"
        ),
        "hidden_case_rows": hidden_case.get("rows"),
        "hidden_case_decision_value_mae": hidden_case.get("decision_value_mae"),
        "hidden_case_value_p90_coverage": hidden_case.get("value_p90_coverage"),
        "hidden_case_q6_plannable_coverage": hidden_case.get(
            "q6_plannable_coverage"
        ),
        "hidden_case_q6_plannable_misses": hidden_case.get(
            "q6_plannable_miss_rows"
        ),
        "no_q6_control_rows": no_q6_control.get("rows"),
        "no_q6_control_positive_rate": no_q6_control.get("no_q6_positive_rate"),
        "no_q6_control_positive_median": no_q6_control.get(
            "no_q6_positive_median"
        ),
        "zero_q6_proven_rows": zero_q6_proven.get("rows"),
        "zero_q6_proven_positive_rate": zero_q6_proven.get("no_q6_positive_rate"),
        "zero_q6_proven_positive_median": zero_q6_proven.get(
            "no_q6_positive_median"
        ),
        "high_info_value_miss_rows": high_info_value_miss.get("rows"),
        "high_info_value_miss_decision_value_mae": (
            high_info_value_miss.get("decision_value_mae")
        ),
        "high_info_q6_miss_rows": high_info_q6_miss.get("rows"),
        "high_info_q6_miss_under_count": high_info_q6_miss.get(
            "q6_plannable_miss_rows"
        ),
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
        "floor_active_rows": floor_summary.get("active_rows"),
        "floor_active_no_q6_rows": floor_summary.get("active_no_q6_rows"),
        "floor_active_no_q6_p90_positive_rate": floor_summary.get(
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
        row["delta_normal_case_decision_value_mae"] = _delta(
            row.get("normal_case_decision_value_mae"),
            baseline.get("normal_case_decision_value_mae"),
        )
        row["delta_normal_case_q6_plannable_coverage"] = _delta(
            row.get("normal_case_q6_plannable_coverage"),
            baseline.get("normal_case_q6_plannable_coverage"),
        )
        row["delta_normal_case_q6_plannable_misses"] = _delta(
            row.get("normal_case_q6_plannable_misses"),
            baseline.get("normal_case_q6_plannable_misses"),
        )
        row["delta_tail_event_decision_value_mae"] = _delta(
            row.get("tail_event_decision_value_mae"),
            baseline.get("tail_event_decision_value_mae"),
        )
        row["delta_hidden_case_decision_value_mae"] = _delta(
            row.get("hidden_case_decision_value_mae"),
            baseline.get("hidden_case_decision_value_mae"),
        )
        row["delta_hidden_case_q6_plannable_coverage"] = _delta(
            row.get("hidden_case_q6_plannable_coverage"),
            baseline.get("hidden_case_q6_plannable_coverage"),
        )
        row["delta_hidden_case_q6_plannable_misses"] = _delta(
            row.get("hidden_case_q6_plannable_misses"),
            baseline.get("hidden_case_q6_plannable_misses"),
        )
        row["delta_no_q6_control_positive_rate"] = _delta(
            row.get("no_q6_control_positive_rate"),
            baseline.get("no_q6_control_positive_rate"),
        )
        row["delta_no_q6_control_positive_median"] = _delta(
            row.get("no_q6_control_positive_median"),
            baseline.get("no_q6_control_positive_median"),
        )
        row["delta_zero_q6_proven_positive_rate"] = _delta(
            row.get("zero_q6_proven_positive_rate"),
            baseline.get("zero_q6_proven_positive_rate"),
        )
        row["delta_zero_q6_proven_positive_median"] = _delta(
            row.get("zero_q6_proven_positive_median"),
            baseline.get("zero_q6_proven_positive_median"),
        )
        row["delta_high_info_value_miss_rows"] = _delta(
            row.get("high_info_value_miss_rows"),
            baseline.get("high_info_value_miss_rows"),
        )
        row["delta_high_info_q6_miss_rows"] = _delta(
            row.get("high_info_q6_miss_rows"),
            baseline.get("high_info_q6_miss_rows"),
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


def _with_paired_baseline_deltas(
    rows: list[dict[str, Any]],
    sample_rows_by_label: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    if not rows:
        return rows
    baseline_label = str(rows[0].get("label") or "")
    baseline_rows = sample_rows_by_label.get(baseline_label, [])
    for row in rows:
        label = str(row.get("label") or "")
        candidate_rows = sample_rows_by_label.get(label, [])
        row.update(_paired_q6_delta_summary(baseline_rows, candidate_rows))
        row.update(
            _prefix_paired_summary(
                "paired_normal",
                _paired_q6_delta_summary(
                    baseline_rows,
                    candidate_rows,
                    row_filter=evaluator._is_normal_case,
                ),
            )
        )
        row.update(
            _prefix_paired_summary(
                "paired_hidden",
                _paired_q6_delta_summary(
                    baseline_rows,
                    candidate_rows,
                    row_filter=evaluator._is_hidden_case,
                ),
            )
        )
    return rows


def _prefix_paired_summary(prefix: str, summary: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in summary.items():
        suffix = key[len("paired_"):] if key.startswith("paired_") else key
        out[f"{prefix}_{suffix}"] = value
    return out


def _paired_q6_delta_summary(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    *,
    row_filter: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    baseline_by_file = _ok_rows_by_file(baseline_rows)
    candidate_by_file = _ok_rows_by_file(candidate_rows)
    files = sorted(set(baseline_by_file).intersection(candidate_by_file))
    paired_rows = 0
    q6_truth_rows = 0
    q6_helped_rows = 0
    q6_newly_missed_rows = 0
    q6_still_missed_rows = 0
    q6_p90_deltas: list[int] = []
    no_q6_rows = 0
    no_q6_new_positive_rows = 0
    no_q6_p90_deltas: list[int] = []
    for file in files:
        baseline = baseline_by_file[file]
        candidate = candidate_by_file[file]
        if row_filter is not None and not (
            row_filter(baseline) and row_filter(candidate)
        ):
            continue
        paired_rows += 1
        final_q6 = int(candidate.get("final_q6_decision_value") or 0)
        baseline_q6_p90 = _int_value(baseline.get("v2_q6_decision_value_p90"))
        candidate_q6_p90 = _int_value(candidate.get("v2_q6_decision_value_p90"))
        if baseline_q6_p90 is None or candidate_q6_p90 is None:
            continue
        if final_q6 > 0:
            q6_truth_rows += 1
            baseline_missed = baseline_q6_p90 < final_q6
            candidate_missed = candidate_q6_p90 < final_q6
            if baseline_missed and not candidate_missed:
                q6_helped_rows += 1
            if not baseline_missed and candidate_missed:
                q6_newly_missed_rows += 1
            if baseline_missed and candidate_missed:
                q6_still_missed_rows += 1
            q6_p90_deltas.append(candidate_q6_p90 - baseline_q6_p90)
        else:
            no_q6_rows += 1
            if baseline_q6_p90 <= 0 and candidate_q6_p90 > 0:
                no_q6_new_positive_rows += 1
            no_q6_p90_deltas.append(candidate_q6_p90 - baseline_q6_p90)
    return {
        "paired_rows": paired_rows,
        "paired_q6_truth_rows": q6_truth_rows,
        "paired_q6_helped_rows": q6_helped_rows,
        "paired_q6_newly_missed_rows": q6_newly_missed_rows,
        "paired_q6_still_missed_rows": q6_still_missed_rows,
        "paired_q6_p90_delta_median": _median(q6_p90_deltas),
        "paired_no_q6_rows": no_q6_rows,
        "paired_no_q6_new_positive_rows": no_q6_new_positive_rows,
        "paired_no_q6_new_positive_rate": (
            round(no_q6_new_positive_rows / no_q6_rows, 4)
            if no_q6_rows
            else None
        ),
        "paired_no_q6_p90_delta_median": _median(no_q6_p90_deltas),
    }


def _ok_rows_by_file(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("file")): row
        for row in rows
        if row.get("status") == "ok" and row.get("file")
    }


def _int_value(value: Any) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def _median(values: list[int]) -> int | None:
    if not values:
        return None
    return int(round(statistics.median(values)))


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
    floor_ratio: float,
    floor_gate: str,
    tables: Any,
    combo_presolve: Any,
    trials: int,
    seed: int,
    cells_tol: int,
    count_tol: int,
    random_sample_avg_profile_floor: float,
    progress: bool,
    progress_every: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    started = time.perf_counter()
    rows = []
    total = len(paths)
    for index, path in enumerate(paths, start=1):
        rows.append(
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
                q6_residual_prior_floor_ratio=floor_ratio,
                q6_residual_prior_floor_gate=floor_gate,
                random_sample_avg_profile_floor=random_sample_avg_profile_floor,
            )
        )
        if progress and (
            index == 1
            or index == total
            or (progress_every > 0 and index % progress_every == 0)
        ):
            elapsed = time.perf_counter() - started
            _progress(
                f"{label}: {index}/{total} files "
                f"({elapsed:.1f}s elapsed, latest={path.name})",
                enabled=progress,
            )
    summary = evaluator._summary(rows)
    _progress(
        f"{label}: done in {time.perf_counter() - started:.1f}s",
        enabled=progress,
    )
    return (
        _comparison_row(
            label,
            boost,
            gate,
            summary,
            floor_ratio=floor_ratio,
            floor_gate=floor_gate,
        ),
        rows,
    )


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
        "--random-sample-avg-profile-floor",
        type=float,
        default=evaluator.RANDOM_SAMPLE_AVG_PROFILE_SIGNAL_FLOOR,
        help=(
            "Offline routing experiment: random N-item average values below "
            "this floor are ignored by evidence-profile gates."
        ),
    )
    parser.add_argument(
        "--combo-presolve",
        default=str(evaluator._DEFAULT_COMBO_PRESOLVE_PATH),
    )
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument(
        "--configs",
        nargs="+",
        choices=_CONFIG_LABELS,
        help=(
            "Subset of configs to run, preserving the default order. "
            "Example: --configs baseline profile_b5 aisha_deep_floor1"
        ),
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=25,
        help="Print progress to stderr every N files per config; 0 disables per-file progress.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Suppress stderr progress messages.",
    )
    args = parser.parse_args()

    raw_paths = (
        evaluator._expand_cli_paths(args.paths)
        if args.paths
        else evaluator._default_paths()
    )
    paths = list(evaluator._iter_unique(raw_paths))
    configs = _selected_configs(args.configs)
    progress = not args.no_progress
    _progress(
        "samples="
        f"{len(paths)} configs="
        f"{','.join(label for label, _boost, _gate, _floor_ratio, _floor_gate in configs)} "
        f"trials={args.trials} "
        f"random_avg_floor={args.random_sample_avg_profile_floor:g} "
        f"posterior_trial_budget={len(paths) * len(configs) * args.trials}",
        enabled=progress,
    )
    tables = evaluator.load_monitor_tables()
    combo_presolve = None
    combo_presolve_path = Path(args.combo_presolve) if args.combo_presolve else None
    if combo_presolve_path is not None and combo_presolve_path.exists():
        combo_presolve = evaluator.load_quality_combo_presolve(combo_presolve_path)

    results = [
        _evaluate_config(
            paths,
            label=label,
            boost=boost,
            gate=gate,
            floor_ratio=floor_ratio,
            floor_gate=floor_gate,
            tables=tables,
            combo_presolve=combo_presolve,
            trials=args.trials,
            seed=args.seed,
            cells_tol=args.cells_tol,
            count_tol=args.count_tol,
            random_sample_avg_profile_floor=args.random_sample_avg_profile_floor,
            progress=progress,
            progress_every=args.progress_every,
        )
        for label, boost, gate, floor_ratio, floor_gate in configs
    ]
    sample_rows_by_label = {
        row["label"]: sample_rows for row, sample_rows in results
    }
    rows = _with_paired_baseline_deltas(
        _with_baseline_deltas([row for row, _sample_rows in results]),
        sample_rows_by_label,
    )
    if args.format == "csv":
        _write_csv(rows)
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
