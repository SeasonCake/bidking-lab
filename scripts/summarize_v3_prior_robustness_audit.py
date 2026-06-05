"""Audit v3 prior robustness, activity, and prior-stress slices."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from evaluate_fatbeans_v3_samples import (  # noqa: E402
    _default_calibration_path,
    _default_paths,
    _default_tail_value_review_path,
    _default_underestimate_repair_path,
    _float_or_none,
    _mean,
    _round_metric,
    evaluate_paths,
    load_monitor_tables,
    load_prior_calibration_entries,
    load_tail_value_review_entries,
    load_underestimate_repair_entries,
)


DEFAULT_GROUP_FIELDS: tuple[str, ...] = (
    "v3_robust_status",
    "v3_robust_reason",
    "v3_robust_fallback_mode",
    "map_id",
    "hero_map_evidence_profile",
)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _reason_tokens(row: dict[str, Any]) -> tuple[str, ...]:
    text = str(row.get("v3_robust_reasons") or "").strip()
    if not text:
        return ("none",)
    return tuple(token.strip() for token in text.split(";") if token.strip()) or ("none",)


def _group_values(row: dict[str, Any], field: str) -> tuple[str, ...]:
    if field == "v3_robust_reason":
        return _reason_tokens(row)
    value = row.get(field)
    return (str(value) if value not in (None, "") else "none",)


def _ready_rows(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    return tuple(row for row in rows if row.get("status") == "ready")


def _metric_rows(rows: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    return tuple(
        row
        for row in rows
        if row.get("status") == "ready"
        and row.get("v3_truth_decision_available")
        and row.get("v3_post_ready")
        and _float_or_none(row.get("v3_post_formal_decision_value_p50")) is not None
        and _float_or_none(row.get("v3_truth_formal_decision_value")) is not None
    )


def _pairs(
    rows: Iterable[dict[str, Any]],
    pred_key: str,
    truth_key: str,
) -> tuple[tuple[float, float], ...]:
    pairs: list[tuple[float, float]] = []
    for row in rows:
        pred = _float_or_none(row.get(pred_key))
        truth = _float_or_none(row.get(truth_key))
        if pred is not None and truth is not None:
            pairs.append((pred, truth))
    return tuple(pairs)


def _mae(pairs: Iterable[tuple[float, float]]) -> float | None:
    return _mean(abs(pred - truth) for pred, truth in pairs)


def _bias(pairs: Iterable[tuple[float, float]]) -> float | None:
    return _mean(pred - truth for pred, truth in pairs)


def _below_rate(pairs: Iterable[tuple[float, float]]) -> float | None:
    return _mean(1.0 if pred < truth else 0.0 for pred, truth in pairs)


def _coverage_rate(pairs: Iterable[tuple[float, float]]) -> float | None:
    return _mean(1.0 if truth <= pred else 0.0 for pred, truth in pairs)


def _top_counts(
    rows: Iterable[dict[str, Any]],
    field: str,
    *,
    top: int = 5,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        value = row.get(field)
        counts[str(value) if value not in (None, "") else "none"] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top])


def _reason_counts(rows: Iterable[dict[str, Any]], *, top: int = 8) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(_reason_tokens(row))
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top])


def _constraint_target(row: dict[str, Any], exact_key: str, floor_key: str) -> float | None:
    values = [
        value
        for value in (
            _float_or_none(row.get(exact_key)),
            _float_or_none(row.get(floor_key)),
        )
        if value is not None and value > 0.0
    ]
    return max(values) if values else None


def _ratio_values(
    rows: Iterable[dict[str, Any]],
    *,
    exact_key: str,
    floor_key: str,
    expected_key: str,
) -> tuple[float, ...]:
    values: list[float] = []
    for row in rows:
        target = _constraint_target(row, exact_key, floor_key)
        expected = _float_or_none(row.get(expected_key))
        if target is None or expected is None or expected <= 0.0:
            continue
        values.append(target / expected)
    return tuple(values)


def _audit_flags(row: dict[str, Any]) -> tuple[str, ...]:
    flags: list[str] = []
    if row["activity_candidate"]:
        flags.append("activity_or_new_table")
    if row["prior_stressed"]:
        flags.append("prior_stressed")
    if row["prior_trusted_rate"] is not None and float(row["prior_trusted_rate"]) < 0.5:
        flags.append("mostly_untrusted")
    if row["metric_rows"] == 0:
        flags.append("no_metric_rows")
    if row["formal_p50_below_rate"] is not None and float(row["formal_p50_below_rate"]) >= 0.6:
        flags.append("high_below")
    if row["formal_p90_coverage"] is not None and float(row["formal_p90_coverage"]) < 0.7:
        flags.append("poor_p90")
    return tuple(flags)


def summarize_prior_robustness(
    rows: Iterable[dict[str, Any]],
    group_field: str,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for value in _group_values(row, group_field):
            groups[value].append(row)

    out: list[dict[str, Any]] = []
    for value, group in groups.items():
        ready = _ready_rows(group)
        metric = _metric_rows(group)
        if not ready:
            continue
        formal_p50 = _pairs(
            metric,
            "v3_post_formal_decision_value_p50",
            "v3_truth_formal_decision_value",
        )
        formal_p90 = _pairs(
            metric,
            "v3_post_formal_decision_value_p90",
            "v3_truth_formal_decision_value",
        )
        q6_count = _pairs(metric, "v3_post_q6_count_p50", "v3_truth_q6_count")
        q6_cells = _pairs(metric, "v3_post_q6_cells_p50", "v3_truth_q6_cells")
        q6_value = _pairs(metric, "v3_post_q6_value_p50", "v3_truth_q6_raw_value")
        stress_scores = tuple(
            int(row.get("v3_robust_prior_stress_score") or 0)
            for row in ready
        )
        q6_count_ratios = _ratio_values(
            ready,
            exact_key="v3_summary_q6_count_exact",
            floor_key="v3_summary_q6_count_floor",
            expected_key="v3_prior_q6_expected_count",
        )
        q6_cells_ratios = _ratio_values(
            ready,
            exact_key="v3_summary_q6_cells_exact",
            floor_key="v3_summary_q6_cells_floor",
            expected_key="v3_prior_q6_expected_cells",
        )
        q6_value_ratios = _ratio_values(
            ready,
            exact_key="v3_summary_q6_value_exact",
            floor_key="v3_summary_q6_value_floor",
            expected_key="v3_prior_q6_expected_value",
        )
        row = {
            "field": group_field,
            "value": value,
            "windows": len(group),
            "ready": len(ready),
            "posterior_ready": sum(1 for item in ready if item.get("v3_post_ready")),
            "metric_rows": len(metric),
            "prior_usable": sum(1 for item in ready if _bool(item.get("v3_robust_prior_usable"))),
            "prior_trusted": sum(1 for item in ready if _bool(item.get("v3_robust_prior_trusted"))),
            "activity_candidate": sum(
                1 for item in ready if _bool(item.get("v3_robust_activity_candidate"))
            ),
            "prior_stressed": sum(
                1
                for item in ready
                if int(item.get("v3_robust_prior_stress_score") or 0) > 0
            ),
            "avg_stress_score": _round_metric(_mean(float(value) for value in stress_scores), 3),
            "max_stress_score": max(stress_scores) if stress_scores else 0,
            "status_counts": _top_counts(ready, "v3_robust_status"),
            "fallback_counts": _top_counts(ready, "v3_robust_fallback_mode"),
            "reason_counts": _reason_counts(ready),
            "posterior_scope_counts": _top_counts(
                (item for item in ready if item.get("v3_post_ready")),
                "v3_post_match_scope",
            ),
            "maps": _top_counts(ready, "map_id"),
            "heroes": _top_counts(ready, "hero"),
            "rounds": _top_counts(ready, "round"),
            "evidence_profiles": _top_counts(ready, "evidence_profile_key"),
            "prior_trusted_rate": _round_metric(
                _mean(1.0 if _bool(item.get("v3_robust_prior_trusted")) else 0.0 for item in ready),
                6,
            ),
            "activity_rate": _round_metric(
                _mean(1.0 if _bool(item.get("v3_robust_activity_candidate")) else 0.0 for item in ready),
                6,
            ),
            "prior_stress_rate": _round_metric(
                _mean(
                    1.0
                    if int(item.get("v3_robust_prior_stress_score") or 0) > 0
                    else 0.0
                    for item in ready
                ),
                6,
            ),
            "formal_p50_mae": _round_metric(_mae(formal_p50), 1),
            "formal_p50_bias": _round_metric(_bias(formal_p50), 1),
            "formal_p50_below_rate": _round_metric(_below_rate(formal_p50), 6),
            "formal_p90_coverage": _round_metric(_coverage_rate(formal_p90), 6),
            "q6_count_p50_mae": _round_metric(_mae(q6_count), 2),
            "q6_cells_p50_mae": _round_metric(_mae(q6_cells), 2),
            "q6_value_p50_mae": _round_metric(_mae(q6_value), 1),
            "q6_count_target_prior_ratio_avg": _round_metric(_mean(q6_count_ratios), 3),
            "q6_count_target_prior_ratio_max": _round_metric(
                max(q6_count_ratios) if q6_count_ratios else None,
                3,
            ),
            "q6_cells_target_prior_ratio_avg": _round_metric(_mean(q6_cells_ratios), 3),
            "q6_cells_target_prior_ratio_max": _round_metric(
                max(q6_cells_ratios) if q6_cells_ratios else None,
                3,
            ),
            "q6_value_target_prior_ratio_avg": _round_metric(_mean(q6_value_ratios), 3),
            "q6_value_target_prior_ratio_max": _round_metric(
                max(q6_value_ratios) if q6_value_ratios else None,
                3,
            ),
        }
        row["flags"] = list(_audit_flags(row))
        out.append(row)
    return sorted(
        out,
        key=lambda item: (
            -int(item["prior_stressed"]),
            -int(item["activity_candidate"]),
            -(item["formal_p50_mae"] or 0.0),
            str(item["field"]),
            str(item["value"]),
        ),
    )


def _print_table(rows: list[dict[str, Any]], *, top: int) -> None:
    for row in rows[:top]:
        flags = "+".join(row["flags"]) if row["flags"] else "normalish"
        reasons = ",".join(f"{key}:{value}" for key, value in row["reason_counts"].items())
        scopes = ",".join(
            f"{key}:{value}" for key, value in row["posterior_scope_counts"].items()
        )
        maps = ",".join(f"{key}:{value}" for key, value in row["maps"].items())
        profiles = ",".join(
            f"{key}:{value}" for key, value in row["evidence_profiles"].items()
        )
        print(
            " ".join(
                (
                    f"{row['field']}={row['value']}",
                    f"ready={row['ready']}",
                    f"post_ready={row['posterior_ready']}",
                    f"metric={row['metric_rows']}",
                    f"trusted={row['prior_trusted']}/{row['ready']}",
                    f"activity={row['activity_candidate']}",
                    f"stressed={row['prior_stressed']}",
                    f"avg_stress={row['avg_stress_score']}",
                    f"mae={row['formal_p50_mae']}",
                    f"bias={row['formal_p50_bias']}",
                    f"below={row['formal_p50_below_rate']}",
                    f"p90_cover={row['formal_p90_coverage']}",
                    f"q6_count_mae={row['q6_count_p50_mae']}",
                    f"q6_cells_mae={row['q6_cells_p50_mae']}",
                    f"q6_value_mae={row['q6_value_p50_mae']}",
                    f"q6_count_ratio={row['q6_count_target_prior_ratio_avg']}",
                    f"q6_cells_ratio={row['q6_cells_target_prior_ratio_avg']}",
                    f"q6_value_ratio={row['q6_value_target_prior_ratio_avg']}",
                    f"scopes={scopes or '-'}",
                    f"maps={maps or '-'}",
                    f"profiles={profiles or '-'}",
                    f"reasons={reasons or '-'}",
                    f"flags={flags}",
                )
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit v3 prior robustness/activity/prior-stress slices.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument(
        "--by",
        action="append",
        default=None,
        help="Row field to group by. Use v3_robust_reason to split reason tokens.",
    )
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    parser.add_argument("--posterior-trials", type=int, default=64)
    parser.add_argument("--posterior-seed", type=int, default=0)
    args = parser.parse_args(argv)

    rows, errors = evaluate_paths(
        args.paths or _default_paths(),
        tables=load_monitor_tables(),
        calibration_entries=load_prior_calibration_entries(
            _default_calibration_path()
        ),
        underestimate_repair_entries=load_underestimate_repair_entries(
            _default_underestimate_repair_path()
        ),
        tail_value_review_entries=load_tail_value_review_entries(
            _default_tail_value_review_path()
        ),
        posterior_trials=args.posterior_trials,
        posterior_seed=args.posterior_seed,
    )
    fields = tuple(args.by or DEFAULT_GROUP_FIELDS)
    audits = [
        item
        for field in fields
        for item in summarize_prior_robustness(rows, field)
    ]
    result = {"errors": errors, "audits": audits}
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if errors:
            print(f"errors={len(errors)}")
        for field in fields:
            print(f"== {field} ==")
            _print_table([row for row in audits if row["field"] == field], top=args.top)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
