"""Audit the v3 evidence-driven CCV shadow sampler prototype.

This script treats the existing ``v3_ccvc_`` component-likelihood report as the
current count/cell/value prototype. It does not change posterior, live, formal,
or UI behavior; it only aggregates archive/session/group/policy/seed evidence
into a single promotion-hardening report.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from evaluate_fatbeans_v3_samples import (  # noqa: E402
    V3CcvOptions,
    _default_calibration_path,
    _default_paths,
    evaluate_paths,
    load_monitor_tables,
    load_prior_calibration_entries,
)
from summarize_v3_ccv_direction_audit import (  # noqa: E402
    MOVEMENT_POLICIES,
    component_fields,
)
from summarize_v3_ccvc_count_policy_matrix import (  # noqa: E402
    DEFAULT_GROUP_FIELDS,
    DEFAULT_POLICIES,
    summarize_matrix,
)
from summarize_v3_ccvc_evidence_contribution import (  # noqa: E402
    DEFAULT_FEATURES,
    summarize_contributions,
)

DEFAULT_COMPONENTS = ("q6_count", "q6_cells", "q6_value")
SHADOW_SAFETY_PREFIXES = ("v3_ccvc_", "v3_fv_", "v3_scp_", "v3_cse_")


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _counter_dict(values: Iterable[Any]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _shadow_safety_counts(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    seq = tuple(rows)
    prefix_counts: dict[str, dict[str, int]] = {}
    affects_rows = 0
    active_rows = 0
    for prefix in SHADOW_SAFETY_PREFIXES:
        affects_key = f"{prefix}affects_bid"
        active_key = f"{prefix}active"
        prefix_affects = sum(1 for row in seq if _bool(row.get(affects_key)))
        prefix_active = sum(1 for row in seq if _bool(row.get(active_key)))
        prefix_counts[prefix.rstrip("_")] = {
            "affects_bid_rows": prefix_affects,
            "active_rows": prefix_active,
        }
        affects_rows += prefix_affects
        active_rows += prefix_active
    return {
        "shadow_affects_bid_rows": affects_rows,
        "shadow_active_rows": active_rows,
        "by_prefix": prefix_counts,
    }


def _row_contract(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    seq = tuple(rows)
    ccvc_ready = [
        row
        for row in seq
        if row.get("status") == "ready"
        and row.get("v3_truth_available")
        and row.get("v3_post_ready")
        and row.get("v3_ccvc_ready")
    ]
    component_rows = [
        row
        for row in ccvc_ready
        if str(row.get("v3_ccvc_match_scope") or "") == "ccv_component_likelihood"
    ]
    return {
        "rows": len(seq),
        "ready_rows": sum(1 for row in seq if row.get("status") == "ready"),
        "ccvc_ready_rows": len(ccvc_ready),
        "ccvc_component_likelihood_rows": len(component_rows),
        "ccvc_match_scope_counts": _counter_dict(
            row.get("v3_ccvc_match_scope") or "none" for row in ccvc_ready
        ),
        **_shadow_safety_counts(seq),
    }


def _matrix_status_counts(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    return _counter_dict(row.get("overall_status") for row in rows)


def _candidate_label(row: Mapping[str, Any]) -> str:
    return "|".join(
        (
            str(row.get("component") or "unknown"),
            str(row.get("group_field") or "unknown"),
            str(row.get("movement_policy") or "unknown"),
        )
    )


def _watch_candidates(
    matrix_rows: Iterable[Mapping[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    rows = [
        row
        for row in matrix_rows
        if str(row.get("overall_status") or "") == "watch"
        and int(row.get("candidate_rows") or 0) > 0
    ]
    rows.sort(
        key=lambda row: (
            float(row.get("candidate_delta_p50_mae") or 0.0),
            float(row.get("candidate_hurt_rate") or 0.0),
            str(row.get("component") or ""),
            str(row.get("group_field") or ""),
            str(row.get("movement_policy") or ""),
        )
    )
    return [
        {
            "label": _candidate_label(row),
            "component": row.get("component"),
            "group_field": row.get("group_field"),
            "movement_policy": row.get("movement_policy"),
            "candidate_rows": row.get("candidate_rows"),
            "candidate_groups": row.get("candidate_groups") or [],
            "candidate_delta_p50_mae": row.get("candidate_delta_p50_mae"),
            "candidate_hurt_rate": row.get("candidate_hurt_rate"),
            "candidate_directional_error_rate": row.get(
                "candidate_directional_error_rate"
            ),
            "candidate_baseline_below_rate": row.get(
                "candidate_baseline_below_rate"
            ),
            "candidate_below_rate": row.get("candidate_below_rate"),
        }
        for row in rows[:limit]
    ]


def _applied_hurt_labels(matrix_rows: Iterable[Mapping[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in matrix_rows:
        for group in row.get("applied_hurts") or ():
            out.append(f"{_candidate_label(row)}:{group}")
    return sorted(set(out))


def _seed_status(
    *,
    row_contract: Mapping[str, Any],
    watch_candidates: Iterable[Mapping[str, Any]],
    applied_hurts: Iterable[str],
) -> str:
    if int(row_contract.get("shadow_affects_bid_rows") or 0) > 0:
        return "blocked_shadow_affects_bid"
    if int(row_contract.get("shadow_active_rows") or 0) > 0:
        return "blocked_shadow_active"
    if int(row_contract.get("ccvc_component_likelihood_rows") or 0) <= 0:
        return "blocked_no_component_likelihood"
    watch_seq = tuple(watch_candidates)
    hurt_seq = tuple(applied_hurts)
    if watch_seq and hurt_seq:
        return "watch_with_hurt_alternatives"
    if watch_seq:
        return "watch_shadow_candidate"
    if hurt_seq:
        return "blocked_holdout_hurt"
    return "sample_limited"


def summarize_seed_run(
    rows: Iterable[dict[str, Any]],
    *,
    posterior_seed: int,
    components: Iterable[str] = DEFAULT_COMPONENTS,
    group_fields: Iterable[str] = DEFAULT_GROUP_FIELDS,
    movement_policies: Iterable[str] = DEFAULT_POLICIES,
    features: Iterable[str] = DEFAULT_FEATURES,
    folds: int = 5,
    min_windows: int = 20,
    min_sessions: int = 8,
    min_changed: int = 5,
    max_hurt_rate: float = 0.45,
    max_directional_error_rate: float = 0.35,
    candidate_include_pattern: str | None = None,
    candidate_exclude_pattern: str | None = None,
) -> dict[str, Any]:
    source_rows = tuple(rows)
    selected_components = tuple(components)
    matrix_rows: list[dict[str, Any]] = []
    for component in selected_components:
        matrix_rows.extend(
            summarize_matrix(
                source_rows,
                group_fields=group_fields,
                movement_policies=movement_policies,
                candidate_prefix="v3_ccvc_",
                component=component,
                folds=folds,
                min_windows=min_windows,
                min_sessions=min_sessions,
                min_changed=min_changed,
                max_hurt_rate=max_hurt_rate,
                max_directional_error_rate=max_directional_error_rate,
                candidate_include_pattern=candidate_include_pattern,
                candidate_exclude_pattern=candidate_exclude_pattern,
            )
        )
    contribution = summarize_contributions(
        source_rows,
        components=selected_components,
        features=features,
        candidate_prefix="v3_ccvc_",
        min_changed=min_changed,
        max_hurt_rate=max_hurt_rate,
        max_directional_error_rate=max_directional_error_rate,
    )
    contract = _row_contract(source_rows)
    watch = _watch_candidates(matrix_rows)
    applied_hurts = _applied_hurt_labels(matrix_rows)
    return {
        "posterior_seed": int(posterior_seed),
        "status": _seed_status(
            row_contract=contract,
            watch_candidates=watch,
            applied_hurts=applied_hurts,
        ),
        "row_contract": contract,
        "matrix_status_counts": _matrix_status_counts(matrix_rows),
        "watch_candidates": watch,
        "applied_hurts": applied_hurts,
        "matrix": matrix_rows,
        "evidence_contribution": {
            "status_counts": contribution["status_counts"],
            "component_results": contribution["component_results"],
            "top_feature_results": contribution["feature_results"][:12],
        },
    }


def _stable_watch_labels(seed_results: Iterable[Mapping[str, Any]]) -> list[str]:
    label_sets: list[set[str]] = []
    for result in seed_results:
        label_sets.append(_watch_label_set(result))
    if not label_sets or any(not labels for labels in label_sets):
        return []
    stable = set.intersection(*label_sets)
    return sorted(stable)


def _watch_label_set(
    result: Mapping[str, Any],
    *,
    component: str | None = None,
) -> set[str]:
    labels: set[str] = set()
    for row in result.get("watch_candidates") or ():
        if not isinstance(row, Mapping):
            continue
        if component is not None and str(row.get("component") or "") != component:
            continue
        label = str(row.get("label"))
        groups = tuple(row.get("candidate_groups") or ())
        if groups:
            labels.update(f"{label}:{group}" for group in groups)
        else:
            labels.add(label)
    return labels


def _stable_watch_labels_for_component(
    seed_results: Iterable[Mapping[str, Any]],
    *,
    component: str,
) -> list[str]:
    label_sets = [
        _watch_label_set(result, component=component)
        for result in seed_results
    ]
    if not label_sets or any(not labels for labels in label_sets):
        return []
    return sorted(set.intersection(*label_sets))


def _component_names(seed_results: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    names: set[str] = set()
    for result in seed_results:
        for row in result.get("matrix") or ():
            if isinstance(row, Mapping) and row.get("component"):
                names.add(str(row["component"]))
        for row in result.get("watch_candidates") or ():
            if isinstance(row, Mapping) and row.get("component"):
                names.add(str(row["component"]))
    return tuple(sorted(names))


def _component_applied_hurts(
    seed_results: Iterable[Mapping[str, Any]],
    *,
    component: str,
) -> list[str]:
    prefix = f"{component}|"
    out: list[str] = []
    for result in seed_results:
        for label in result.get("applied_hurts") or ():
            text = str(label)
            if text.startswith(prefix):
                out.append(text)
    return sorted(set(out))


def _component_matrix_status_counts(
    seed_results: Iterable[Mapping[str, Any]],
    *,
    component: str,
) -> dict[str, int]:
    statuses: list[str] = []
    for result in seed_results:
        for row in result.get("matrix") or ():
            if isinstance(row, Mapping) and str(row.get("component") or "") == component:
                statuses.append(str(row.get("overall_status") or "unknown"))
    return _counter_dict(statuses)


def _watch_labels_by_seed(
    seed_results: Iterable[Mapping[str, Any]],
    *,
    component: str,
) -> list[dict[str, Any]]:
    return [
        {
            "posterior_seed": result.get("posterior_seed"),
            "watch_labels": sorted(_watch_label_set(result, component=component)),
        }
        for result in seed_results
    ]


def _unstable_watch_labels(
    labels_by_seed: Iterable[Mapping[str, Any]],
    *,
    stable: Iterable[str],
) -> list[str]:
    stable_set = set(stable)
    label_sets = [
        set(row.get("watch_labels") or ())
        for row in labels_by_seed
        if isinstance(row, Mapping)
    ]
    if not label_sets:
        return []
    union = set.union(*label_sets) if label_sets else set()
    return sorted(union - stable_set)


def _component_next_action(status: str, component: str) -> str:
    if status == "watch_shadow_candidate":
        return "keep as diagnostic candidate; require readiness and live replay before promotion"
    if status == "watch_with_hurt_alternatives":
        return "narrow candidate groups and exclude hurt alternatives before more tuning"
    if status == "blocked_seed_instability":
        return "do not tune; collect support or add source/evidence filters before retesting"
    if status == "blocked_holdout_hurt" and component == "q6_cells":
        return "freeze q6 cells or add a stronger cells guard before retesting"
    if status == "blocked_holdout_hurt":
        return "keep component inactive and isolate hurt groups before retesting"
    if status.startswith("blocked_shadow"):
        return "fix shadow safety before any sampler work"
    return "keep inactive until movement/support appears"


def _component_statuses(seed_results: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    results = tuple(seed_results)
    statuses = {str(row.get("status") or "") for row in results}
    out: list[dict[str, Any]] = []
    for component in _component_names(results):
        stable = _stable_watch_labels_for_component(results, component=component)
        hurts = _component_applied_hurts(results, component=component)
        has_watch = any(_watch_label_set(result, component=component) for result in results)
        labels_by_seed = _watch_labels_by_seed(results, component=component)
        if "blocked_shadow_affects_bid" in statuses:
            status = "blocked_shadow_affects_bid"
        elif "blocked_shadow_active" in statuses:
            status = "blocked_shadow_active"
        elif len(results) > 1 and has_watch and not stable:
            status = "blocked_seed_instability"
        elif stable and hurts:
            status = "watch_with_hurt_alternatives"
        elif stable:
            status = "watch_shadow_candidate"
        elif hurts:
            status = "blocked_holdout_hurt"
        else:
            status = "sample_limited"
        out.append(
            {
                "component": component,
                "status": status,
                "stable_watch_candidate_labels": stable,
                "unstable_watch_candidate_labels": _unstable_watch_labels(
                    labels_by_seed,
                    stable=stable,
                ),
                "watch_labels_by_seed": labels_by_seed,
                "applied_hurts": hurts,
                "matrix_status_counts": _component_matrix_status_counts(
                    results,
                    component=component,
                ),
                "next_action": _component_next_action(status, component),
            }
        )
    return out


def _overall_status(
    seed_results: Iterable[Mapping[str, Any]],
    stable_labels: Iterable[str],
) -> str:
    results = tuple(seed_results)
    statuses = {str(row.get("status") or "") for row in results}
    if "blocked_shadow_affects_bid" in statuses:
        return "blocked_shadow_affects_bid"
    if "blocked_shadow_active" in statuses:
        return "blocked_shadow_active"
    if "blocked_no_component_likelihood" in statuses:
        return "blocked_no_component_likelihood"
    if len(results) > 1 and not tuple(stable_labels):
        return "blocked_seed_instability"
    if any(status.startswith("watch") for status in statuses):
        if "watch_with_hurt_alternatives" in statuses:
            return "watch_with_hurt_alternatives"
        return "watch_shadow_candidate"
    if "blocked_holdout_hurt" in statuses:
        return "blocked_holdout_hurt"
    return "sample_limited"


def summarize_prototype_runs(
    seed_results: Iterable[Mapping[str, Any]],
    *,
    posterior_trials: int,
    component_move_cells: bool,
) -> dict[str, Any]:
    results = tuple(seed_results)
    stable_labels = _stable_watch_labels(results)
    return {
        "interface": "v3_ccvc_evidence_driven_count_cell_value_sampler",
        "shadow_only": True,
        "affects_bid": False,
        "active": False,
        "can_promote": False,
        "posterior_trials": int(posterior_trials),
        "component_move_cells": bool(component_move_cells),
        "posterior_seeds": [row.get("posterior_seed") for row in results],
        "status": _overall_status(results, stable_labels),
        "seed_status_counts": _counter_dict(row.get("status") for row in results),
        "stable_watch_candidate_labels": stable_labels,
        "component_statuses": _component_statuses(results),
        "required_holdouts": [
            "archive",
            "session",
            "map_family",
            "map_id",
            "evidence_profile",
            "posterior_seed",
        ],
        "blocked_actions": [
            "change formal bid path",
            "wire prototype into live decisions",
            "archive v2 fallback",
            "relax readiness or promotion gates",
        ],
        "seed_results": list(results),
    }


def _print_summary(result: Mapping[str, Any], *, top: int) -> None:
    print(
        " ".join(
            (
                f"status={result.get('status')}",
                f"interface={result.get('interface')}",
                f"shadow_only={result.get('shadow_only')}",
                f"affects_bid={result.get('affects_bid')}",
                f"trials={result.get('posterior_trials')}",
                "seeds=" + ",".join(str(seed) for seed in result.get("posterior_seeds") or ()),
                "stable_watch="
                + ",".join(result.get("stable_watch_candidate_labels") or ()),
                "seed_status_counts="
                + ",".join(
                    f"{status}:{count}"
                    for status, count in (result.get("seed_status_counts") or {}).items()
                ),
            )
        )
    )
    for row in result.get("component_statuses") or ():
        print(
            " ".join(
                (
                    f"component={row.get('component')}",
                    f"status={row.get('status')}",
                    "stable_watch="
                    + ",".join(row.get("stable_watch_candidate_labels") or ()),
                    "unstable_watch="
                    + ",".join((row.get("unstable_watch_candidate_labels") or ())[:top]),
                    "applied_hurts="
                    + ",".join((row.get("applied_hurts") or ())[:top]),
                    f"next_action=\"{row.get('next_action')}\"",
                )
            )
        )
    for seed_result in result.get("seed_results") or ():
        contract = seed_result.get("row_contract") or {}
        print(
            " ".join(
                (
                    f"seed={seed_result.get('posterior_seed')}",
                    f"status={seed_result.get('status')}",
                    f"rows={contract.get('rows')}",
                    "component_rows="
                    f"{contract.get('ccvc_component_likelihood_rows')}",
                    "matrix_status_counts="
                    + ",".join(
                        f"{status}:{count}"
                        for status, count in (
                            seed_result.get("matrix_status_counts") or {}
                        ).items()
                    ),
                    "applied_hurts="
                    + ",".join((seed_result.get("applied_hurts") or ())[:top]),
                )
            )
        )
        for row in (seed_result.get("watch_candidates") or ())[:top]:
            print(
                " ".join(
                    (
                        f"candidate={row.get('label')}",
                        "groups=" + ",".join(row.get("candidate_groups") or ()),
                        f"rows={row.get('candidate_rows')}",
                        f"delta={row.get('candidate_delta_p50_mae')}",
                        f"hurt_rate={row.get('candidate_hurt_rate')}",
                        "directional_error="
                        f"{row.get('candidate_directional_error_rate')}",
                    )
                )
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit the v3 CCVC shadow sampler prototype.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument(
        "--component",
        action="append",
        choices=tuple(component_fields("v3_ccvc_")),
        help="Component to audit. Can be passed more than once.",
    )
    parser.add_argument(
        "--group-field",
        action="append",
        help="Holdout group field. Can be passed more than once.",
    )
    parser.add_argument(
        "--movement-policy",
        action="append",
        choices=MOVEMENT_POLICIES,
        help="Movement policy to audit. Can be passed more than once.",
    )
    parser.add_argument(
        "--feature",
        action="append",
        choices=DEFAULT_FEATURES,
        help="Evidence feature to audit. Can be passed more than once.",
    )
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-windows", type=int, default=20)
    parser.add_argument("--min-sessions", type=int, default=8)
    parser.add_argument("--min-changed", type=int, default=5)
    parser.add_argument("--max-hurt-rate", type=float, default=0.45)
    parser.add_argument("--max-directional-error-rate", type=float, default=0.35)
    parser.add_argument(
        "--candidate-include-pattern",
        help="Regex over 'component:group' labels allowed into holdout candidates.",
    )
    parser.add_argument(
        "--candidate-exclude-pattern",
        help="Regex over 'component:group' labels removed from holdout candidates.",
    )
    parser.add_argument("--posterior-trials", type=int, default=64)
    parser.add_argument(
        "--posterior-seed",
        action="append",
        type=int,
        help="Posterior seed to audit. Can be passed more than once.",
    )
    parser.add_argument(
        "--ccv-component-freeze-cells",
        action="store_true",
        help="Keep q6 cells at baseline when emitting v3_ccvc_ fields.",
    )
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args(argv)

    tables = load_monitor_tables()
    calibration_entries = load_prior_calibration_entries(
        _default_calibration_path()
    )
    seed_results: list[dict[str, Any]] = []
    all_errors: list[str] = []
    seeds = args.posterior_seed or [0]
    for seed in seeds:
        rows, errors = evaluate_paths(
            args.paths or _default_paths(),
            tables=tables,
            calibration_entries=calibration_entries,
            posterior_trials=args.posterior_trials,
            posterior_seed=seed,
            ccv_options=V3CcvOptions(
                component_likelihood=True,
                component_move_cells=not args.ccv_component_freeze_cells,
            ),
        )
        all_errors.extend(str(error) for error in errors)
        seed_results.append(
            summarize_seed_run(
                rows,
                posterior_seed=seed,
                components=args.component or DEFAULT_COMPONENTS,
                group_fields=args.group_field or DEFAULT_GROUP_FIELDS,
                movement_policies=args.movement_policy or DEFAULT_POLICIES,
                features=args.feature or DEFAULT_FEATURES,
                folds=args.folds,
                min_windows=args.min_windows,
                min_sessions=args.min_sessions,
                min_changed=args.min_changed,
                max_hurt_rate=args.max_hurt_rate,
                max_directional_error_rate=args.max_directional_error_rate,
                candidate_include_pattern=args.candidate_include_pattern,
                candidate_exclude_pattern=args.candidate_exclude_pattern,
            )
        )
    result = {
        "errors": all_errors,
        **summarize_prototype_runs(
            seed_results,
            posterior_trials=args.posterior_trials,
            component_move_cells=not args.ccv_component_freeze_cells,
        ),
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if all_errors:
            print(f"errors={len(all_errors)}")
        _print_summary(result, top=args.top)
    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
