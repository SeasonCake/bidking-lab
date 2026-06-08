"""Run a shadow-only guard trial from a v3 sampler prototype contract."""

from __future__ import annotations

import argparse
import json
import re
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
from summarize_v3_ccvc_count_policy_matrix import (  # noqa: E402
    DEFAULT_GROUP_FIELDS,
    DEFAULT_POLICIES,
)
from summarize_v3_shadow_sampler_prototype import (  # noqa: E402
    DEFAULT_COMPONENTS,
    DEFAULT_FEATURES,
    DEFAULT_MIN_WATCH_SUPPORT_ROWS,
    DEFAULT_MIN_WATCH_SUPPORT_SESSIONS,
    summarize_prototype_runs,
    summarize_seed_run,
)

DEFAULT_TRIAL_GROUP_FIELDS = ("map_family", *DEFAULT_GROUP_FIELDS)
BLOCKING_SAMPLER_STATUSES = {
    "blocked_shadow_affects_bid",
    "blocked_shadow_active",
    "blocked_no_component_likelihood",
    "blocked_seed_instability",
    "blocked_low_support",
    "blocked_holdout_hurt",
    "watch_with_hurt_alternatives",
}


def _counter_dict(values: Iterable[Any]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _guard_trial_contract(prototype: Mapping[str, Any]) -> Mapping[str, Any]:
    contract = prototype.get("guard_trial_contract")
    return contract if isinstance(contract, Mapping) else {}


def _component_actions(contract: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    actions = contract.get("component_actions")
    if not isinstance(actions, list):
        return []
    return [row for row in actions if isinstance(row, Mapping)]


def _component_exclude_pattern(component: str) -> str:
    return f"^{re.escape(component)}:.*"


def _label_exclude_pattern(label: str) -> str:
    return f"^{re.escape(label)}$"


def _dedupe(seq: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in seq:
        if item in seen:
            continue
        out.append(item)
        seen.add(item)
    return out


def build_trial_options(prototype: Mapping[str, Any]) -> dict[str, Any]:
    contract = _guard_trial_contract(prototype)
    actions = _component_actions(contract)
    exclude_patterns: list[str] = []
    exclude_labels: list[str] = []
    excluded_components: list[str] = []
    freeze_cells = False
    for action in actions:
        component = str(action.get("component") or "")
        trial_action = str(action.get("trial_action") or "")
        if not component:
            continue
        if trial_action == "freeze_component":
            if component == "q6_cells":
                freeze_cells = True
            excluded_components.append(component)
            exclude_patterns.append(_component_exclude_pattern(component))
        elif trial_action in {
            "require_source_support_gate",
            "collect_support_before_trial",
            "fix_shadow_safety",
            "fix_component_likelihood_contract",
            "keep_inactive_sample_limited",
        }:
            excluded_components.append(component)
            exclude_patterns.append(_component_exclude_pattern(component))
        elif trial_action in {
            "guard_hurt_groups",
            "guard_hurt_groups_keep_component_inactive",
        }:
            labels = [
                str(label)
                for label in action.get("candidate_exclude_labels") or ()
                if label
            ]
            if labels:
                exclude_labels.extend(labels)
                exclude_patterns.extend(_label_exclude_pattern(label) for label in labels)
            elif trial_action == "guard_hurt_groups_keep_component_inactive":
                excluded_components.append(component)
                exclude_patterns.append(_component_exclude_pattern(component))
    exclude_patterns = _dedupe(exclude_patterns)
    return {
        "source_guard_trial_status": contract.get("status"),
        "source_action_counts": dict(contract.get("action_counts") or {}),
        "component_move_cells": not freeze_cells,
        "candidate_exclude_pattern": "|".join(exclude_patterns) or None,
        "candidate_exclude_labels": _dedupe(exclude_labels),
        "excluded_components": _dedupe(excluded_components),
        "requires_source_parser": bool(contract.get("requires_source_parser")),
        "source_component_actions": [dict(row) for row in actions],
    }


def _trial_status(sampler_status: str) -> str:
    if sampler_status == "watch_shadow_candidate":
        return "watch_guarded_shadow_trial"
    if sampler_status == "sample_limited":
        return "sample_limited_guarded_shadow_trial"
    if sampler_status in BLOCKING_SAMPLER_STATUSES:
        return "blocked_guarded_shadow_trial"
    return "blocked_guarded_shadow_trial"


def _wrap_trial_result(
    sampler_result: Mapping[str, Any],
    *,
    prototype: Mapping[str, Any],
    trial_options: Mapping[str, Any],
) -> dict[str, Any]:
    sampler_status = str(sampler_result.get("status") or "unknown")
    return {
        "interface": "v3_ccvc_shadow_sampler_guarded_trial",
        "status": _trial_status(sampler_status),
        "sampler_status": sampler_status,
        "shadow_only": True,
        "affects_bid": False,
        "active": False,
        "can_promote": False,
        "source_prototype_status": prototype.get("status"),
        "source_guard_trial_status": trial_options.get(
            "source_guard_trial_status"
        ),
        "trial_options": dict(trial_options),
        "component_status_counts": _counter_dict(
            row.get("status")
            for row in sampler_result.get("component_statuses") or ()
            if isinstance(row, Mapping)
        ),
        "support_gate_status_counts": _counter_dict(
            (
                row.get("support_gate") or {}
            ).get("status")
            if isinstance(row.get("support_gate"), Mapping)
            else "missing"
            for row in sampler_result.get("component_statuses") or ()
            if isinstance(row, Mapping)
        ),
        "guarded_sampler_result": dict(sampler_result),
        "required_verification": [
            "archive",
            "session",
            "map_family",
            "map_id",
            "evidence_profile",
            "posterior_seed",
            "readiness_attachment",
        ],
        "blocked_actions": [
            "change formal bid path",
            "wire guarded trial into live decisions",
            "archive v2 fallback",
            "relax readiness or promotion gates",
        ],
    }


def summarize_guard_trial_rows(
    rows_by_seed: Mapping[int, Iterable[dict[str, Any]]],
    *,
    prototype: Mapping[str, Any],
    posterior_trials: int,
    components: Iterable[str] = DEFAULT_COMPONENTS,
    group_fields: Iterable[str] = DEFAULT_TRIAL_GROUP_FIELDS,
    movement_policies: Iterable[str] = DEFAULT_POLICIES,
    features: Iterable[str] = DEFAULT_FEATURES,
    folds: int = 5,
    min_windows: int = 20,
    min_sessions: int = 8,
    min_changed: int = 5,
    max_hurt_rate: float = 0.45,
    max_directional_error_rate: float = 0.35,
    min_watch_support_rows: int = DEFAULT_MIN_WATCH_SUPPORT_ROWS,
    min_watch_support_sessions: int = DEFAULT_MIN_WATCH_SUPPORT_SESSIONS,
) -> dict[str, Any]:
    trial_options = build_trial_options(prototype)
    seed_results = [
        summarize_seed_run(
            rows,
            posterior_seed=seed,
            components=components,
            group_fields=group_fields,
            movement_policies=movement_policies,
            features=features,
            folds=folds,
            min_windows=min_windows,
            min_sessions=min_sessions,
            min_changed=min_changed,
            max_hurt_rate=max_hurt_rate,
            max_directional_error_rate=max_directional_error_rate,
            candidate_exclude_pattern=trial_options["candidate_exclude_pattern"],
        )
        for seed, rows in sorted(rows_by_seed.items())
    ]
    sampler_result = summarize_prototype_runs(
        seed_results,
        posterior_trials=posterior_trials,
        component_move_cells=bool(trial_options["component_move_cells"]),
        min_watch_support_rows=min_watch_support_rows,
        min_watch_support_sessions=min_watch_support_sessions,
    )
    return _wrap_trial_result(
        sampler_result,
        prototype=prototype,
        trial_options=trial_options,
    )


def _print_summary(result: Mapping[str, Any], *, top: int) -> None:
    options = result.get("trial_options") or {}
    print(
        " ".join(
            (
                f"status={result.get('status')}",
                f"sampler_status={result.get('sampler_status')}",
                f"source_guard_trial={result.get('source_guard_trial_status')}",
                f"shadow_only={result.get('shadow_only')}",
                f"affects_bid={result.get('affects_bid')}",
                f"component_move_cells={options.get('component_move_cells')}",
                "excluded_components="
                + ",".join(options.get("excluded_components") or ()),
                "exclude_labels="
                + ",".join((options.get("candidate_exclude_labels") or ())[:top]),
                "component_statuses="
                + ",".join(
                    f"{status}:{count}"
                    for status, count in (
                        result.get("component_status_counts") or {}
                    ).items()
                ),
                "support_gates="
                + ",".join(
                    f"{status}:{count}"
                    for status, count in (
                        result.get("support_gate_status_counts") or {}
                    ).items()
                ),
            )
        )
    )
    sampler = result.get("guarded_sampler_result") or {}
    for row in sampler.get("component_statuses") or ():
        if not isinstance(row, Mapping):
            continue
        support_gate = row.get("support_gate") or {}
        top_hurts = [
            str(item.get("watch_label") or "")
            for item in row.get("top_applied_hurt_metrics") or ()
            if isinstance(item, Mapping)
        ][:top]
        print(
            " ".join(
                (
                    f"component={row.get('component')}",
                    f"status={row.get('status')}",
                    f"support_gate={support_gate.get('status')}",
                    "stable_watch="
                    + ",".join(
                        (row.get("stable_watch_candidate_labels") or ())[:top]
                    ),
                    "top_hurts=" + ",".join(top_hurts),
                    f"next_action=\"{row.get('next_action')}\"",
                )
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a shadow-only guard trial from a sampler prototype JSON.",
    )
    parser.add_argument(
        "--prototype-json",
        type=Path,
        required=True,
        help="JSON output from summarize_v3_shadow_sampler_prototype.py.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument("--component", action="append")
    parser.add_argument("--group-field", action="append")
    parser.add_argument("--movement-policy", action="append", choices=DEFAULT_POLICIES)
    parser.add_argument("--feature", action="append", choices=DEFAULT_FEATURES)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-windows", type=int, default=20)
    parser.add_argument("--min-sessions", type=int, default=8)
    parser.add_argument("--min-changed", type=int, default=5)
    parser.add_argument("--max-hurt-rate", type=float, default=0.45)
    parser.add_argument("--max-directional-error-rate", type=float, default=0.35)
    parser.add_argument("--posterior-trials", type=int, default=64)
    parser.add_argument("--posterior-seed", action="append", type=int)
    parser.add_argument(
        "--min-watch-support-rows",
        type=int,
        default=DEFAULT_MIN_WATCH_SUPPORT_ROWS,
    )
    parser.add_argument(
        "--min-watch-support-sessions",
        type=int,
        default=DEFAULT_MIN_WATCH_SUPPORT_SESSIONS,
    )
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args(argv)

    with args.prototype_json.open("r", encoding="utf-8-sig") as handle:
        prototype = json.load(handle)
    trial_options = build_trial_options(prototype)
    tables = load_monitor_tables()
    calibration_entries = load_prior_calibration_entries(
        _default_calibration_path()
    )
    seeds = args.posterior_seed or [0]
    rows_by_seed: dict[int, list[dict[str, Any]]] = {}
    all_errors: list[str] = []
    for seed in seeds:
        rows, errors = evaluate_paths(
            args.paths or _default_paths(),
            tables=tables,
            calibration_entries=calibration_entries,
            posterior_trials=args.posterior_trials,
            posterior_seed=seed,
            ccv_options=V3CcvOptions(
                component_likelihood=True,
                component_move_cells=bool(trial_options["component_move_cells"]),
            ),
        )
        rows_by_seed[int(seed)] = rows
        all_errors.extend(str(error) for error in errors)
    result = {
        "errors": all_errors,
        **summarize_guard_trial_rows(
            rows_by_seed,
            prototype=prototype,
            posterior_trials=args.posterior_trials,
            components=args.component or DEFAULT_COMPONENTS,
            group_fields=args.group_field or DEFAULT_TRIAL_GROUP_FIELDS,
            movement_policies=args.movement_policy or DEFAULT_POLICIES,
            features=args.feature or DEFAULT_FEATURES,
            folds=args.folds,
            min_windows=args.min_windows,
            min_sessions=args.min_sessions,
            min_changed=args.min_changed,
            max_hurt_rate=args.max_hurt_rate,
            max_directional_error_rate=args.max_directional_error_rate,
            min_watch_support_rows=args.min_watch_support_rows,
            min_watch_support_sessions=args.min_watch_support_sessions,
        ),
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if all_errors:
            print(f"errors={len(all_errors)}")
        _print_summary(result, top=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
