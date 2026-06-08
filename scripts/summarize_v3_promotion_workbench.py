"""Summarize v3 promotion readiness JSON into a lane workbench."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")


STOP_LOSS_GATES = {
    "capacity_source_expansion_shadow",
    "settlement_count_guarded_bridge_stability",
    "settlement_count_cells_value_bridge_holdout",
    "ccv_direction_holdout",
    "formal_value_sampler_holdout",
}

SHADOW_SAMPLER_WATCH_GATES = {
    "v3_practical_archive_live_guard_metrics",
    "prior_stress_capacity_table_drift",
    "capacity_source_expansion_shadow",
    "settlement_count_prior_shadow",
    "settlement_count_formal_value_link",
    "settlement_count_cells_value_bridge",
    "settlement_count_guarded_bridge_holdout",
    "settlement_count_guarded_bridge_stability",
    "ccv_sampler",
    "ccv_directionality",
    "ccv_direction_holdout",
    "tail_value_review",
    "tail_under_combined_holdout",
    "formal_value_sampler_holdout",
}

SHADOW_SAMPLER_REQUIRED_EVIDENCE = (
    "ConstraintSet",
    "FeasibleSummary",
    "public numeric facts",
    "item/category/shape/layout anchors",
    "prior fields",
    "prior-stress detail contract",
    "activity/source alias flags",
    "CSE/SCP shadow risk flags",
)

SHADOW_SAMPLER_REQUIRED_HOLDOUTS = (
    "archive",
    "session",
    "map_family",
    "map_id/profile when sample depth is sufficient",
    "posterior seed stability",
    "live model_eval replay",
)

SHADOW_SAMPLER_REQUIRED_METRICS = (
    "formal_p50_mae",
    "formal_p50_below_rate",
    "formal_p50_over_rate",
    "formal_p50_pinball",
    "formal_p90_coverage",
    "formal_p90_extreme_over_rate",
    "q6_count_p50_mae",
    "q6_cells_p50_mae",
    "q6_value_p50_mae",
    "directional_hurt_groups",
    "component_statuses",
    "watch_labels_by_seed",
    "watch_support_rows",
    "watch_support_sessions",
    "support_gate_status",
    "stable_low_support_watch_metrics",
    "unstable_watch_candidate_metrics",
)

SHADOW_SAMPLER_PROTOTYPE_KEYS = (
    "shadow_sampler_prototype",
    "ccvc_shadow_sampler_prototype",
    "v3_shadow_sampler_prototype",
)

SHADOW_SAMPLER_PROTOTYPE_REQUIRED_FIELDS = (
    "interface",
    "shadow_only",
    "affects_bid",
    "status",
    "posterior_seeds",
    "stable_watch_candidate_labels",
    "component_statuses",
    "min_watch_support_rows",
    "min_watch_support_sessions",
)

SHADOW_SAMPLER_PROTOTYPE_BLOCKING_STATUSES = {
    "blocked_shadow_affects_bid",
    "blocked_shadow_active",
    "blocked_no_component_likelihood",
    "blocked_seed_instability",
    "blocked_low_support",
    "blocked_holdout_hurt",
    "watch_with_hurt_alternatives",
}

SHADOW_SAMPLER_REQUIRED_COMPONENT_GATES = (
    "shadow safety: affects_bid=false and active=false",
    "component status per q6_count/q6_cells/q6_value",
    "selected watch label seed stability",
    "watch support rows/sessions gate",
    "holdout hurt alternatives",
    "archive/session/map-family/map-id/evidence-profile coverage",
)


def _gate_name(gate: Mapping[str, Any]) -> str:
    return str(gate.get("gate") or gate.get("name") or "unknown")


def _gate_status(gate: Mapping[str, Any]) -> str:
    return str(gate.get("status") or "unknown")


def _gate_lane(gate: Mapping[str, Any]) -> str:
    return str(gate.get("lane") or "unknown")


def _as_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _prototype_from_readiness(readiness: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in SHADOW_SAMPLER_PROTOTYPE_KEYS:
        value = readiness.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _counter_from_rows(rows: Iterable[Mapping[str, Any]], key: str) -> dict[str, int]:
    return dict(
        sorted(Counter(str(row.get(key) or "unknown") for row in rows).items())
    )


def _support_gate_status(row: Mapping[str, Any]) -> str:
    gate = row.get("support_gate")
    if not isinstance(gate, Mapping):
        return "missing"
    return str(gate.get("status") or "unknown")


def _low_support_watch_metrics(
    component_statuses: Iterable[Mapping[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in component_statuses:
        gate = row.get("support_gate")
        if not isinstance(gate, Mapping):
            continue
        for item in gate.get("low_support_watch_metrics") or ():
            if isinstance(item, Mapping):
                out.append(dict(item))
    out.sort(
        key=lambda item: (
            str(item.get("watch_label") or ""),
            str(item.get("posterior_seed") or ""),
        )
    )
    return out[:limit]


def _stable_low_support_watch_metrics(
    component_statuses: Iterable[Mapping[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in component_statuses:
        gate = row.get("support_gate")
        if not isinstance(gate, Mapping):
            continue
        for item in gate.get("stable_low_support_watch_metrics") or ():
            if isinstance(item, Mapping):
                out.append(dict(item))
    out.sort(
        key=lambda item: (
            str(item.get("watch_label") or ""),
            str(item.get("posterior_seed") or ""),
        )
    )
    return out[:limit]


def _shadow_sampler_prototype_contract(
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    prototype = _prototype_from_readiness(readiness)
    if not prototype:
        return {
            "status": "missing",
            "attached": False,
            "accepted_keys": list(SHADOW_SAMPLER_PROTOTYPE_KEYS),
            "required_fields": list(SHADOW_SAMPLER_PROTOTYPE_REQUIRED_FIELDS),
            "blocking_statuses": sorted(SHADOW_SAMPLER_PROTOTYPE_BLOCKING_STATUSES),
        }

    missing = [
        field
        for field in SHADOW_SAMPLER_PROTOTYPE_REQUIRED_FIELDS
        if field not in prototype
    ]
    component_statuses = _as_list(prototype.get("component_statuses"))
    component_status_counts = _counter_from_rows(component_statuses, "status")
    support_gate_status_counts = dict(
        sorted(Counter(_support_gate_status(row) for row in component_statuses).items())
    )
    blocking_component_statuses = [
        {
            "component": row.get("component"),
            "status": row.get("status"),
            "support_gate": _support_gate_status(row),
        }
        for row in component_statuses
        if str(row.get("status") or "") in SHADOW_SAMPLER_PROTOTYPE_BLOCKING_STATUSES
    ]
    prototype_status = str(prototype.get("status") or "unknown")
    shadow_safe = (
        prototype.get("shadow_only") is True
        and prototype.get("affects_bid") is False
        and prototype.get("active") is False
    )
    if missing or not shadow_safe:
        status = "malformed"
    elif (
        prototype_status in SHADOW_SAMPLER_PROTOTYPE_BLOCKING_STATUSES
        or blocking_component_statuses
    ):
        status = "blocked"
    else:
        status = "watch_only"
    return {
        "status": status,
        "attached": True,
        "interface": prototype.get("interface"),
        "prototype_status": prototype_status,
        "shadow_safe": shadow_safe,
        "missing_fields": missing,
        "posterior_seeds": prototype.get("posterior_seeds") or [],
        "stable_watch_candidate_labels": prototype.get(
            "stable_watch_candidate_labels"
        )
        or [],
        "min_watch_support_rows": prototype.get("min_watch_support_rows"),
        "min_watch_support_sessions": prototype.get("min_watch_support_sessions"),
        "component_status_counts": component_status_counts,
        "support_gate_status_counts": support_gate_status_counts,
        "blocking_component_statuses": blocking_component_statuses,
        "low_support_watch_metrics": _low_support_watch_metrics(component_statuses),
        "stable_low_support_watch_metrics": _stable_low_support_watch_metrics(
            component_statuses
        ),
        "required_fields": list(SHADOW_SAMPLER_PROTOTYPE_REQUIRED_FIELDS),
        "blocking_statuses": sorted(SHADOW_SAMPLER_PROTOTYPE_BLOCKING_STATUSES),
    }


def _lane_verdict(
    *,
    lane: str,
    status_counts: Mapping[str, Any],
    gates: Iterable[Mapping[str, Any]],
) -> str:
    gate_seq = tuple(gates)
    blocked = int(status_counts.get("blocked") or 0)
    pending = int(status_counts.get("pending") or 0)
    watch = int(status_counts.get("watch") or 0)
    stop_loss = any(_gate_name(gate) in STOP_LOSS_GATES for gate in gate_seq)
    if lane == "archive_pipeline_quality" and blocked == 0 and pending == 0:
        return "usable_watch"
    if blocked or pending:
        return "stop_loss" if stop_loss else "blocked"
    if watch:
        return "watch_only"
    return "pass"


def _lane_next_action(lane: str, verdict: str) -> str:
    if verdict == "stop_loss":
        if lane == "settlement_bridge_support":
            return "freeze unstable bridge lanes; redesign or collect targeted support"
        if lane == "formal_value_shadow_sampler":
            return "define shadow interface and candidate criteria before tuning"
        if lane == "sampler_safety_holdout":
            return "do not promote; isolate hurt groups and high-over risk"
        return "do not tune this lane until new evidence appears"
    if verdict == "watch_only":
        return "keep visible and inactive; use only as support context"
    if verdict == "blocked":
        return "resolve blocker before promotion"
    if verdict == "usable_watch":
        return "safe to use as audit denominator, not promotion evidence"
    return "no immediate action"


def _gate_summary(gate: Mapping[str, Any]) -> dict[str, Any]:
    out = {
        "gate": _gate_name(gate),
        "lane": _gate_lane(gate),
        "status": _gate_status(gate),
    }
    focus = str(gate.get("focus") or gate.get("reason") or "").strip()
    if focus:
        out["focus"] = focus
    return out


def _sampler_contract_status(
    *,
    blocking_gates: Iterable[Mapping[str, Any]],
    frozen_gates: Iterable[Mapping[str, Any]],
) -> str:
    blocking_seq = tuple(blocking_gates)
    frozen_seq = tuple(frozen_gates)
    if any(_gate_name(gate) in STOP_LOSS_GATES for gate in blocking_seq):
        return "shadow_design_only"
    if blocking_seq:
        return "blocked_pending_prerequisites"
    if frozen_seq:
        return "shadow_watch_only"
    return "ready_for_shadow_prototype"


def summarize_shadow_sampler_contract(
    readiness: Mapping[str, Any],
    *,
    lanes: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    deps = readiness.get("gate_dependencies") or {}
    blocked = _as_list(deps.get("blocked_or_pending_gates"))
    watch = _as_list(deps.get("watch_gates"))
    all_gates = blocked + watch
    blocking_gates = [
        gate for gate in all_gates if _gate_status(gate) in {"blocked", "pending"}
    ]
    sampler_watch_gates = [
        gate for gate in all_gates if _gate_name(gate) in SHADOW_SAMPLER_WATCH_GATES
    ]
    frozen_gates = [
        gate
        for gate in sampler_watch_gates
        if _gate_name(gate) in STOP_LOSS_GATES
        or _gate_status(gate) in {"blocked", "pending"}
    ]
    status = _sampler_contract_status(
        blocking_gates=blocking_gates,
        frozen_gates=frozen_gates,
    )
    prototype_contract = _shadow_sampler_prototype_contract(readiness)
    if (
        prototype_contract.get("status") in {"blocked", "malformed"}
        and status == "ready_for_shadow_prototype"
    ):
        status = "shadow_prototype_blocked"
    lane_verdicts = {
        str(row.get("lane")): str(row.get("verdict"))
        for row in lanes
        if isinstance(row, Mapping)
    }
    stop_loss_lanes = sorted(
        lane for lane, verdict in lane_verdicts.items() if verdict == "stop_loss"
    )
    can_start_shadow_prototype = status in {
        "shadow_design_only",
        "shadow_watch_only",
        "ready_for_shadow_prototype",
    }
    return {
        "interface": "evidence_driven_count_cell_value_sampler",
        "status": status,
        "shadow_only": True,
        "affects_bid": False,
        "can_change_live_or_formal": False,
        "can_archive_v2": False,
        "can_start_shadow_prototype": can_start_shadow_prototype,
        "can_promote": False,
        "stop_loss_lanes": stop_loss_lanes,
        "blocking_gates": [_gate_summary(gate) for gate in blocking_gates],
        "frozen_gates": [_gate_summary(gate) for gate in frozen_gates],
        "watch_inputs": [_gate_summary(gate) for gate in sampler_watch_gates],
        "required_evidence": list(SHADOW_SAMPLER_REQUIRED_EVIDENCE),
        "required_holdouts": list(SHADOW_SAMPLER_REQUIRED_HOLDOUTS),
        "required_metrics": list(SHADOW_SAMPLER_REQUIRED_METRICS),
        "required_component_gates": list(SHADOW_SAMPLER_REQUIRED_COMPONENT_GATES),
        "prototype_contract": prototype_contract,
        "allowed_actions": [
            "define sampler interface",
            "emit shadow-only fields",
            "run archive/session/map-family/seed holdout",
            "attach support-aware prototype audit to readiness/workbench",
            "record candidate/watch/frozen gates",
        ],
        "blocked_actions": [
            "change formal bid path",
            "wire shadow sampler into live decisions",
            "tune formal/live parameters from current blockers",
            "archive v2 fallback",
            "relax readiness or promotion gates",
        ],
        "next_action": _sampler_next_action(status, stop_loss_lanes),
    }


def _sampler_next_action(status: str, stop_loss_lanes: Iterable[str]) -> str:
    lanes = tuple(stop_loss_lanes)
    if status == "shadow_design_only":
        if "settlement_bridge_support" in lanes:
            return (
                "freeze settlement bridge inputs and define a sampler interface "
                "that treats CSE/SCP as risk flags only"
            )
        return "define the shadow sampler interface before any parameter tuning"
    if status == "blocked_pending_prerequisites":
        return "resolve blocked readiness prerequisites before sampler tuning"
    if status == "shadow_prototype_blocked":
        return "keep sampler shadow-only; resolve prototype seed/support blockers"
    if status == "shadow_watch_only":
        return "emit prototype fields only; keep watch gates inactive"
    return "run the shadow prototype through required holdouts"


def summarize_workbench(readiness: Mapping[str, Any]) -> dict[str, Any]:
    deps = readiness.get("gate_dependencies") or {}
    blocked = _as_list(deps.get("blocked_or_pending_gates"))
    watch = _as_list(deps.get("watch_gates"))
    all_gates = blocked + watch
    lane_status_counts = deps.get("lane_status_counts") or {}
    lanes: list[dict[str, Any]] = []
    gates_by_lane: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for gate in all_gates:
        gates_by_lane[_gate_lane(gate)].append(gate)

    lane_names = set(gates_by_lane)
    if isinstance(lane_status_counts, Mapping):
        lane_names.update(str(name) for name in lane_status_counts)

    for lane in sorted(lane_names):
        status_counts = (
            lane_status_counts.get(lane)
            if isinstance(lane_status_counts, Mapping)
            else None
        ) or Counter(_gate_status(gate) for gate in gates_by_lane[lane])
        verdict = _lane_verdict(
            lane=lane,
            status_counts=status_counts,
            gates=gates_by_lane[lane],
        )
        lanes.append(
            {
                "lane": lane,
                "verdict": verdict,
                "status_counts": dict(status_counts),
                "blocked_gates": [
                    _gate_name(gate)
                    for gate in gates_by_lane[lane]
                    if _gate_status(gate) in {"blocked", "pending"}
                ],
                "watch_gates": [
                    _gate_name(gate)
                    for gate in gates_by_lane[lane]
                    if _gate_status(gate) == "watch"
                ],
                "next_action": _lane_next_action(lane, verdict),
            }
        )

    verdict_counts = Counter(row["verdict"] for row in lanes)
    sampler_contract = summarize_shadow_sampler_contract(readiness, lanes=lanes)
    return {
        "overall_status": readiness.get("overall_status"),
        "blocked_gates": readiness.get("blocked_gates"),
        "lane_count": len(lanes),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "lanes": lanes,
        "shadow_sampler_contract": sampler_contract,
        "next_mode": _next_mode(lanes),
    }


def _next_mode(lanes: Iterable[Mapping[str, Any]]) -> str:
    lane_seq = tuple(lanes)
    if any(row.get("verdict") == "stop_loss" for row in lane_seq):
        return "build_shadow_formal_value_workbench"
    if any(row.get("verdict") == "blocked" for row in lane_seq):
        return "resolve_blockers"
    return "promotion_review"


def _print_summary(result: Mapping[str, Any]) -> None:
    print(
        " ".join(
            [
                f"overall_status={result.get('overall_status')}",
                f"blocked_gates={result.get('blocked_gates')}",
                f"lane_count={result.get('lane_count')}",
                "verdicts="
                + ",".join(
                    f"{key}:{value}"
                    for key, value in (result.get("verdict_counts") or {}).items()
                ),
                f"next_mode={result.get('next_mode')}",
            ]
        )
    )
    for row in result.get("lanes") or ():
        blocked = ",".join(row.get("blocked_gates") or ()) or "-"
        watch = ",".join(row.get("watch_gates") or ()) or "-"
        print(
            " ".join(
                [
                    f"lane={row.get('lane')}",
                    f"verdict={row.get('verdict')}",
                    "statuses="
                    + ",".join(
                        f"{key}:{value}"
                        for key, value in (row.get("status_counts") or {}).items()
                    ),
                    f"blocked={blocked}",
                    f"watch={watch}",
                    f"next_action=\"{row.get('next_action')}\"",
                ]
            )
        )
    contract = result.get("shadow_sampler_contract") or {}
    if isinstance(contract, Mapping):
        prototype = contract.get("prototype_contract") or {}
        frozen = ",".join(
            str(row.get("gate"))
            for row in contract.get("frozen_gates") or ()
            if isinstance(row, Mapping)
        ) or "-"
        blockers = ",".join(
            str(row.get("gate"))
            for row in contract.get("blocking_gates") or ()
            if isinstance(row, Mapping)
        ) or "-"
        print(
            " ".join(
                [
                    "shadow_sampler_contract",
                    f"status={contract.get('status')}",
                    f"shadow_only={contract.get('shadow_only')}",
                    f"affects_bid={contract.get('affects_bid')}",
                    f"frozen={frozen}",
                    f"blockers={blockers}",
                    f"prototype_status={prototype.get('status')}",
                    f"prototype_overall={prototype.get('prototype_status')}",
                    f"next_action=\"{contract.get('next_action')}\"",
                ]
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize v3 promotion readiness JSON into a lane workbench."
    )
    parser.add_argument("readiness_json", type=Path)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args(argv)

    with args.readiness_json.open("r", encoding="utf-8-sig") as handle:
        readiness = json.load(handle)
    result = summarize_workbench(readiness)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
