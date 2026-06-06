"""Summarize v3 readiness blockers across archive/live shadow gates."""

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
    _default_calibration_path,
    _default_capacity_source_expansion_path,
    _default_paths,
    _default_settlement_count_prior_path,
    _default_tail_value_review_path,
    _default_underestimate_repair_path,
    evaluate_paths,
    load_monitor_tables,
    load_prior_calibration_entries,
    load_capacity_source_expansion_entries,
    load_settlement_count_prior_entries,
    load_tail_value_review_entries,
    load_underestimate_repair_entries,
    summarize_rows,
)
from summarize_v3_ccv_profile_candidates import (  # noqa: E402
    summarize_candidates as summarize_ccv_candidates,
)
from summarize_v3_ccv_holdout import (  # noqa: E402
    summarize_holdout as summarize_ccv_holdout,
)
from summarize_v3_ccv_direction_audit import (  # noqa: E402
    summarize_direction as summarize_ccv_direction,
)
from summarize_v3_ccv_direction_holdout import (  # noqa: E402
    summarize_holdout as summarize_ccv_direction_holdout,
)
from summarize_v3_residual_profile_candidates import (  # noqa: E402
    summarize_candidates as summarize_residual_candidates,
)
from summarize_v3_tail_value_candidates import (  # noqa: E402
    summarize_candidates as summarize_tail_candidates,
)
from summarize_v3_tail_value_holdout import (  # noqa: E402
    summarize_holdout as summarize_tail_holdout,
)
from summarize_v3_tail_under_holdout import (  # noqa: E402
    summarize_holdout as summarize_tail_under_holdout,
)
from summarize_v3_formal_value_sampler_holdout import (  # noqa: E402
    summarize_holdout as summarize_formal_value_sampler_holdout,
)
from summarize_v3_scp_formal_value_link import (  # noqa: E402
    summarize_link as summarize_scp_formal_value_link,
)
from summarize_v3_scp_count_value_bridge import (  # noqa: E402
    summarize_bridge as summarize_scp_count_value_bridge,
)
from summarize_v3_scp_count_value_bridge_holdout import (  # noqa: E402
    summarize_holdout as summarize_scp_count_value_bridge_holdout,
)
from summarize_v3_scp_guarded_bridge_holdout import (  # noqa: E402
    summarize_guarded_holdout as summarize_scp_guarded_bridge_holdout,
)
from summarize_v3_prior_robustness_audit import (  # noqa: E402
    summarize_prior_stress_details,
    summarize_prior_stress_detail_summary,
)
from summarize_v3_underestimate_holdout import (  # noqa: E402
    summarize_holdout as summarize_under_holdout,
)


def _status_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get("candidate_status")) for row in rows).items()))


def _top_groups(
    rows: Iterable[dict[str, Any]],
    status: str,
    *,
    limit: int = 5,
) -> list[str]:
    return [
        str(row.get("group"))
        for row in rows
        if row.get("candidate_status") == status
    ][:limit]


def _gate(
    name: str,
    status: str,
    reason: str,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "reason": reason,
        **fields,
    }


def _blocked_count(gates: Iterable[dict[str, Any]]) -> int:
    return sum(1 for gate in gates if str(gate.get("status")) == "blocked")


_GATE_DEPENDENCY_META: dict[str, tuple[str, str]] = {
    "archive_data_quality": (
        "archive_pipeline_quality",
        "fix parse/constraint issues before trusting archive metrics",
    ),
    "shared_shadow_pipeline": (
        "archive_pipeline_quality",
        "keep v3 posterior shadow coverage complete and inactive",
    ),
    "prior_robustness": (
        "table_activity_capacity",
        "resolve missing/activity/prior-drift rows before default prior use",
    ),
    "prior_stress_capacity_table_drift": (
        "table_activity_capacity",
        "audit cells/capacity/evidence semantics by map/profile",
    ),
    "settlement_count_prior_shadow": (
        "table_activity_capacity",
        "keep settlement count prior visible and inactive while table gaps remain",
    ),
    "capacity_source_expansion_shadow": (
        "table_activity_capacity",
        "keep capacity/source expansion evidence visible and inactive until the capacity blocker is fully closed",
    ),
    "settlement_count_formal_value_link": (
        "formal_value_shadow_sampler",
        "prove settlement count candidates overlap value/formal stress",
    ),
    "settlement_count_cells_value_bridge": (
        "settlement_bridge_support",
        "find count->cells/value bridge candidates before holdout",
    ),
    "settlement_count_cells_value_bridge_holdout": (
        "settlement_bridge_support",
        "hold out count->cells/value bridge before sampler use",
    ),
    "settlement_count_guarded_bridge_holdout": (
        "settlement_bridge_support",
        "collect support and seed-stability for guarded settlement bridge",
    ),
    "settlement_count_guarded_bridge_stability": (
        "settlement_bridge_support",
        "prove guarded settlement bridge selection is stable across posterior seeds",
    ),
    "formal_baseline_metrics": (
        "formal_value_shadow_sampler",
        "formal baseline must enter promotion band or be safely bridged",
    ),
    "underestimate_repair_holdout": (
        "sampler_safety_holdout",
        "keep bounded upshift inactive until holdout remains safe",
    ),
    "ccv_sampler": (
        "sampler_safety_holdout",
        "prove CCV candidate signal without global/map-layer hurt",
    ),
    "ccv_directionality": (
        "sampler_safety_holdout",
        "remove directional p50 hurt before CCV promotion",
    ),
    "ccv_direction_holdout": (
        "sampler_safety_holdout",
        "hold out directionally selected CCV movements",
    ),
    "tail_value_review": (
        "sampler_safety_holdout",
        "keep tail/value review non-formal until holdout is stable",
    ),
    "tail_under_combined_holdout": (
        "sampler_safety_holdout",
        "hold out combined under/tail policy before formal use",
    ),
    "formal_value_sampler_holdout": (
        "formal_value_shadow_sampler",
        "prove formal/value sampler support without over/under regressions",
    ),
    "residual_gate": (
        "sampler_safety_holdout",
        "residual remains watch-only with active rows at zero",
    ),
    "profile_sample_depth": (
        "profile_sample_depth",
        "collect enough profile-level samples before profile promotion",
    ),
    "v2_archive_readiness": (
        "v2_archive_after_promotion",
        "archive v2 only after v3 formal path is promoted and verified",
    ),
}


def _gate_focus(gate: Mapping[str, Any]) -> str:
    name = str(gate.get("name") or "")
    if name == "prior_robustness":
        activity = int(gate.get("robust_activity_candidate") or 0)
        stressed = int(gate.get("robust_prior_stressed") or 0)
        untrusted = int(gate.get("ready") or 0) - int(
            gate.get("robust_prior_trusted") or 0
        )
        parts = []
        if activity:
            parts.append(f"activity_candidate_rows={activity}")
        if stressed:
            parts.append(f"prior_stressed_rows={stressed}")
        if untrusted > 0:
            parts.append(f"untrusted_ready_rows={untrusted}")
        return ";".join(parts)
    if name == "prior_stress_capacity_table_drift":
        hits = int(gate.get("capacity_flag_hits") or 0)
        rows = int(gate.get("detail_rows") or 0)
        return f"detail_rows={rows};capacity_flag_hits={hits}"
    if name == "settlement_count_prior_shadow":
        missing = int(gate.get("missing_table_rows") or 0)
        candidates = int(gate.get("candidate_rows") or 0)
        return f"candidate_rows={candidates};missing_table_rows={missing}"
    if name == "capacity_source_expansion_shadow":
        candidates = int(gate.get("candidate_rows") or 0)
        pressure = int(gate.get("pressure_candidate_rows") or 0)
        active = int(gate.get("active_rows") or 0)
        return (
            f"candidate_rows={candidates};"
            f"pressure_candidate_rows={pressure};active_rows={active}"
        )
    if name in {
        "settlement_count_cells_value_bridge_holdout",
        "settlement_count_guarded_bridge_holdout",
        "settlement_count_guarded_bridge_stability",
    }:
        applied = gate.get("applied_rows")
        selected = gate.get("selected_group_fold_counts") or {}
        if not selected:
            selected = gate.get("selected_signature_counts") or {}
        parts = [f"applied_rows={applied}"]
        if selected:
            parts.append(
                "selected_groups="
                + ",".join(
                    f"{key}:{selected[key]}"
                    for key in sorted(selected)
                )
            )
        return ";".join(parts)
    if name == "settlement_count_formal_value_link":
        return (
            f"formal_rows={gate.get('scp_candidate_formal_rows')};"
            f"value_floor_rows={gate.get('scp_candidate_value_floor_rows')};"
            f"capacity_watch_rows={gate.get('scp_candidate_capacity_watch_rows')}"
        )
    if name == "formal_value_sampler_holdout":
        return (
            f"candidate_rows={gate.get('candidate_rows')};"
            f"candidate_groups={','.join(gate.get('candidate_groups') or [])}"
        )
    if name == "formal_baseline_metrics":
        return (
            f"below_rate={gate.get('formal_p50_below_rate')};"
            f"p90_coverage={gate.get('formal_p90_coverage')}"
        )
    if name == "profile_sample_depth":
        return (
            f"ccv_profile_rows={gate.get('ccv_profile_holdout_candidate_rows')};"
            f"tail_profile_rows={gate.get('tail_profile_holdout_candidate_rows')}"
        )
    return ""


def summarize_gate_dependencies(gates: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    lane_status_counts: dict[str, Counter[str]] = {}
    for gate in gates:
        name = str(gate.get("name") or "")
        lane, action = _GATE_DEPENDENCY_META.get(
            name,
            ("other", "review gate-specific evidence"),
        )
        status = str(gate.get("status") or "unknown")
        lane_status_counts.setdefault(lane, Counter())[status] += 1
        rows.append(
            {
                "gate": name,
                "status": status,
                "lane": lane,
                "blocking": status in {"blocked", "pending"},
                "focus": _gate_focus(gate),
                "action": action,
            }
        )
    blocked_or_pending = [
        row for row in rows if row["status"] in {"blocked", "pending"}
    ]
    watch = [row for row in rows if row["status"] == "watch"]
    return {
        "lane_status_counts": {
            lane: dict(sorted(counts.items()))
            for lane, counts in sorted(lane_status_counts.items())
        },
        "blocked_or_pending_lanes": sorted(
            {row["lane"] for row in blocked_or_pending}
        ),
        "blocked_or_pending_gates": blocked_or_pending,
        "watch_gates": watch,
    }


def _ccv_applied_hurt_groups(result: dict[str, Any]) -> list[str]:
    return [
        str(row.get("group"))
        for row in result.get("group_results", ())
        if int(row.get("candidate_rows") or 0) > 0
        and (
            (
                row.get("delta_q6_count_p50_mae") is not None
                and float(row["delta_q6_count_p50_mae"]) > 0.05
            )
            or (
                row.get("delta_q6_cells_p50_mae") is not None
                and float(row["delta_q6_cells_p50_mae"]) > 0.25
            )
            or (
                row.get("delta_q6_value_p50_mae") is not None
                and float(row["delta_q6_value_p50_mae"]) > 10_000.0
            )
            or (
                row.get("delta_q6_formal_p50_mae") is not None
                and float(row["delta_q6_formal_p50_mae"]) > 10_000.0
            )
        )
    ][:5]


def _ccv_directional_hurts(rows: Iterable[dict[str, Any]]) -> list[str]:
    return [
        f"{row.get('component')}:{row.get('group')}"
        for row in rows
        if row.get("status") == "blocked_directional_hurt"
    ][:8]


def _top_prior_stress_groups(
    detail_summary: dict[str, Any],
    field: str,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in detail_summary.get("by_group", ()):
        if row.get("field") != field:
            continue
        out.append(
            {
                "value": row.get("value"),
                "rows": row.get("rows"),
                "capacity_flag_hits": row.get("capacity_flag_hits"),
                "max_cells_ratio": row.get("max_cells_ratio"),
                "max_value_ratio": row.get("max_value_ratio"),
                "capacity_flag_counts": row.get("capacity_flag_counts"),
                "capacity_count_summary": row.get("capacity_count_summary"),
                "consistency_bucket_counts": row.get(
                    "consistency_bucket_counts"
                ),
                "consistency_class_counts": row.get(
                    "consistency_class_counts"
                ),
                "reason_counts": row.get("reason_counts"),
                "source_counts": row.get("source_counts"),
            }
        )
    return out[:limit]


def summarize_readiness(
    rows: list[dict[str, Any]],
    errors: list[dict[str, str]],
    *,
    group_field: str = "hero_map_id",
    profile_field: str = "hero_map_evidence_profile",
    min_windows: int = 20,
    min_sessions: int = 8,
    folds: int = 5,
    scp_guarded_bridge_stability: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary = summarize_rows(rows, errors)
    prior_stress_details = summarize_prior_stress_details(rows)
    prior_stress_detail_summary = summarize_prior_stress_detail_summary(
        prior_stress_details,
        top=8,
        group_fields=("map_id", "hero_map_evidence_profile"),
    )
    under = summarize_under_holdout(
        rows,
        group_field=group_field,
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    under_profile = summarize_under_holdout(
        rows,
        group_field=profile_field,
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    ccv = summarize_ccv_candidates(
        rows,
        group_field=group_field,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    ccv_profile = summarize_ccv_candidates(
        rows,
        group_field=profile_field,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    ccv_holdout = summarize_ccv_holdout(
        rows,
        group_field=group_field,
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    ccv_profile_holdout = summarize_ccv_holdout(
        rows,
        group_field=profile_field,
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    ccv_map_holdout = summarize_ccv_holdout(
        rows,
        group_field="map_id",
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    ccv_map_direction = summarize_ccv_direction(
        rows,
        group_field="map_id",
        components=("q6_count", "q6_cells"),
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    ccv_profile_direction = summarize_ccv_direction(
        rows,
        group_field="evidence_profile_key",
        components=("q6_count", "q6_cells"),
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    ccv_map_direction_holdout = summarize_ccv_direction_holdout(
        rows,
        group_field="map_id",
        components=("q6_count", "q6_cells"),
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    ccv_profile_direction_holdout = summarize_ccv_direction_holdout(
        rows,
        group_field="evidence_profile_key",
        components=("q6_count", "q6_cells"),
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    residual = summarize_residual_candidates(
        rows,
        group_field=group_field,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    tail = summarize_tail_candidates(
        rows,
        group_field=group_field,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    tail_holdout = summarize_tail_holdout(
        rows,
        group_field=group_field,
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    tail_profile_holdout = summarize_tail_holdout(
        rows,
        group_field=profile_field,
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    tail_profile = summarize_tail_candidates(
        rows,
        group_field=profile_field,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    tail_under_holdout = summarize_tail_under_holdout(
        rows,
        group_field=group_field,
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    formal_value_sampler_holdout = summarize_formal_value_sampler_holdout(
        rows,
        group_field=group_field,
        folds=folds,
        min_windows=min_windows,
        min_sessions=min_sessions,
    )
    scp_formal_value_link = summarize_scp_formal_value_link(
        rows,
        group_field="v3_scp_group",
    )
    scp_count_value_bridge = summarize_scp_count_value_bridge(
        rows,
        group_field="v3_scp_group",
    )
    scp_count_value_bridge_holdout = summarize_scp_count_value_bridge_holdout(
        rows,
        group_field="v3_scp_group",
        folds=folds,
        min_train_sessions=min_sessions,
    )
    scp_guarded_bridge_holdout = summarize_scp_guarded_bridge_holdout(
        rows,
        group_field="v3_scp_group",
        folds=folds,
        inner_folds=max(2, folds - 1),
        min_train_sessions=min_sessions,
        min_guard_sessions=min_sessions,
        min_guard_fold_sessions=max(1, min_sessions // 4),
        formal_lift_cap=10_000.0,
        max_guard_over_increase=0.0,
    )

    gates: list[dict[str, Any]] = []
    data_status = "pass" if not errors and not summary.get("constraint_conflict") else "blocked"
    if data_status == "pass" and int(summary.get("no_state") or 0) > 0:
        data_status = "watch"
    gates.append(
        _gate(
            "archive_data_quality",
            data_status,
            "parse/constraint clean; no_state rows are separated from metric rows"
            if data_status != "blocked"
            else "parse errors or constraint conflicts remain",
            parse_errors=summary.get("parse_errors"),
            constraint_conflict=summary.get("constraint_conflict"),
            no_state=summary.get("no_state"),
            ready=summary.get("ready"),
        )
    )
    pipeline_ready = (
        int(summary.get("ready") or 0) > 0
        and int(summary.get("posterior_ready") or 0) == int(summary.get("ready") or 0)
        and int(summary.get("posterior_no_match") or 0) == 0
    )
    gates.append(
        _gate(
            "shared_shadow_pipeline",
            "pass" if pipeline_ready else "blocked",
            "archive/live v3 shadow pipeline produces ready posterior rows"
            if pipeline_ready
            else "posterior readiness does not cover all ready rows",
            posterior_ready=summary.get("posterior_ready"),
            ready=summary.get("ready"),
            posterior_no_match=summary.get("posterior_no_match"),
        )
    )
    ready_count = int(summary.get("ready") or 0)
    robust_prior_usable = int(summary.get("robust_prior_usable") or 0)
    robust_prior_trusted = int(summary.get("robust_prior_trusted") or 0)
    robust_activity_candidate = int(summary.get("robust_activity_candidate") or 0)
    robust_prior_stressed = int(summary.get("robust_prior_stressed") or 0)
    robust_ready = (
        ready_count > 0
        and robust_prior_usable == ready_count
        and robust_prior_trusted == ready_count
        and robust_activity_candidate == 0
        and robust_prior_stressed == 0
    )
    gates.append(
        _gate(
            "prior_robustness",
            "pass" if robust_ready else "blocked",
            "all ready rows have trusted priors and no activity/drift signal"
            if robust_ready
            else "prior trust is incomplete or activity/drift candidates are present",
            ready=ready_count,
            robust_prior_usable=robust_prior_usable,
            robust_prior_trusted=robust_prior_trusted,
            robust_activity_candidate=robust_activity_candidate,
            robust_prior_stressed=robust_prior_stressed,
            robust_status_counts=summary.get("robust_status_counts"),
        )
    )
    prior_stress_overall = prior_stress_detail_summary["overall"]
    prior_stress_capacity_flags = prior_stress_overall.get(
        "capacity_flag_counts",
        {},
    )
    prior_stress_capacity_hits = sum(prior_stress_capacity_flags.values())
    prior_stress_group_rows = int(prior_stress_overall.get("rows") or 0)
    prior_stress_drift_ready = (
        prior_stress_group_rows == 0 and prior_stress_capacity_hits == 0
    )
    gates.append(
        _gate(
            "prior_stress_capacity_table_drift",
            "pass" if prior_stress_drift_ready else "blocked",
            "no prior-stressed capacity/table/evidence drift rows"
            if prior_stress_drift_ready
            else "prior-stressed capacity/table/evidence drift requires targeted map/profile audit",
            detail_rows=prior_stress_group_rows,
            capacity_flag_hits=prior_stress_capacity_hits,
            capacity_flag_counts=prior_stress_capacity_flags,
            capacity_count_summary=prior_stress_overall.get("capacity_count_summary"),
            consistency_bucket_counts=prior_stress_overall.get(
                "consistency_bucket_counts"
            ),
            consistency_class_counts=prior_stress_overall.get(
                "consistency_class_counts"
            ),
            source_counts=prior_stress_overall.get("source_counts"),
            ratio_summary=prior_stress_overall.get("ratio_summary"),
            top_map_groups=_top_prior_stress_groups(
                prior_stress_detail_summary,
                "map_id",
            ),
            top_profile_groups=_top_prior_stress_groups(
                prior_stress_detail_summary,
                "hero_map_evidence_profile",
            ),
        )
    )
    scp_ready = int(summary.get("v3_scp_ready_rows") or 0)
    scp_candidate = int(summary.get("v3_scp_candidate_rows") or 0)
    scp_missing_table = int(summary.get("v3_scp_missing_table_rows") or 0)
    scp_active = int(summary.get("v3_scp_active_rows") or 0)
    scp_status = "watch" if scp_ready > 0 and scp_active == 0 else "blocked"
    gates.append(
        _gate(
            "settlement_count_prior_shadow",
            scp_status,
            "settlement count prior evidence is visible and inactive"
            if scp_status == "watch"
            else "settlement count prior shadow fields are missing or active",
            ready_rows=scp_ready,
            candidate_rows=scp_candidate,
            missing_table_rows=scp_missing_table,
            active_rows=scp_active,
            status_counts=summary.get("v3_scp_status_counts"),
        )
    )
    cse_ready = int(summary.get("v3_cse_ready_rows") or 0)
    cse_candidate = int(summary.get("v3_cse_candidate_rows") or 0)
    cse_pressure_candidate = int(
        summary.get("v3_cse_pressure_candidate_rows") or 0
    )
    cse_active = int(summary.get("v3_cse_active_rows") or 0)
    cse_status = "watch" if cse_ready > 0 and cse_active == 0 else "blocked"
    gates.append(
        _gate(
            "capacity_source_expansion_shadow",
            cse_status,
            "capacity/source expansion evidence is visible and inactive"
            if cse_status == "watch"
            else "capacity/source expansion shadow fields are missing or active",
            ready_rows=cse_ready,
            candidate_rows=cse_candidate,
            pressure_candidate_rows=cse_pressure_candidate,
            active_rows=cse_active,
            status_counts=summary.get("v3_cse_status_counts"),
        )
    )
    scp_link_overall = scp_formal_value_link["overall"]
    scp_link_value_rows = int(
        scp_link_overall.get("scp_candidate_value_floor_rows") or 0
    )
    scp_link_candidate_rows = int(
        scp_link_overall.get("scp_candidate_formal_rows") or 0
    )
    scp_link_delta = scp_link_overall.get("formal_fv_delta_p50_mae")
    scp_link_ready = (
        scp_link_candidate_rows > 0
        and scp_link_value_rows > 0
        and scp_link_delta is not None
        and float(scp_link_delta) < 0.0
    )
    gates.append(
        _gate(
            "settlement_count_formal_value_link",
            "watch" if scp_link_ready else "blocked",
            "settlement count-prior candidates have value-floor overlap and improve formal shadow metrics"
            if scp_link_ready
            else "settlement count-prior candidates are mostly capacity/no-value bridge or do not improve formal shadow metrics",
            formal_rows=scp_link_overall.get("formal_rows"),
            scp_candidate_formal_rows=scp_link_candidate_rows,
            scp_candidate_value_floor_rows=scp_link_value_rows,
            scp_candidate_capacity_watch_rows=scp_link_overall.get(
                "scp_candidate_capacity_watch_rows"
            ),
            formal_fv_delta_p50_mae=scp_link_delta,
            formal_baseline_p50_below_rate=scp_link_overall.get(
                "formal_baseline_p50_below_rate"
            ),
            formal_baseline_p90_coverage=scp_link_overall.get(
                "formal_baseline_p90_coverage"
            ),
            status_counts=scp_formal_value_link.get("status_counts"),
            top_groups=[
                {
                    "group": row.get("group"),
                    "link_status": row.get("link_status"),
                    "scp_candidate_formal_rows": row.get(
                        "scp_candidate_formal_rows"
                    ),
                    "scp_candidate_value_floor_rows": row.get(
                        "scp_candidate_value_floor_rows"
                    ),
                    "scp_candidate_capacity_watch_rows": row.get(
                        "scp_candidate_capacity_watch_rows"
                    ),
                    "formal_baseline_p50_mae": row.get(
                        "formal_baseline_p50_mae"
                    ),
                    "formal_baseline_p50_below_rate": row.get(
                        "formal_baseline_p50_below_rate"
                    ),
                    "formal_baseline_p90_coverage": row.get(
                        "formal_baseline_p90_coverage"
                    ),
                }
                for row in scp_formal_value_link.get("rows", ())[:5]
            ],
        )
    )
    scp_bridge_overall = scp_count_value_bridge["overall"]
    scp_bridge_rows = int(
        scp_bridge_overall.get("count_cells_value_bridge_rows") or 0
    )
    scp_bridge_status = (
        "watch"
        if scp_bridge_rows > 0
        and int(scp_bridge_overall.get("scp_active_rows") or 0) == 0
        else "blocked"
    )
    gates.append(
        _gate(
            "settlement_count_cells_value_bridge",
            scp_bridge_status,
            "settlement count-prior has archive count->cells/value bridge candidates; holdout is still required"
            if scp_bridge_status == "watch"
            else "settlement count-prior lacks a usable count->cells/value bridge or has active rows",
            metric_rows=scp_bridge_overall.get("metric_rows"),
            scp_candidate_metric_rows=scp_bridge_overall.get(
                "scp_candidate_metric_rows"
            ),
            scp_p95_above_target_rows=scp_bridge_overall.get(
                "scp_p95_above_target_rows"
            ),
            cells_p90_under_rows=scp_bridge_overall.get("cells_p90_under_rows"),
            formal_p90_under_rows=scp_bridge_overall.get("formal_p90_under_rows"),
            count_cells_bridge_rows=scp_bridge_overall.get(
                "count_cells_bridge_rows"
            ),
            count_value_bridge_rows=scp_bridge_overall.get(
                "count_value_bridge_rows"
            ),
            count_cells_value_bridge_rows=scp_bridge_rows,
            cells_per_item=scp_bridge_overall.get("truth_cells_per_item"),
            formal_per_item=scp_bridge_overall.get("truth_formal_per_item"),
            status_counts=scp_count_value_bridge.get("status_counts"),
            top_groups=[
                {
                    "group": row.get("group"),
                    "bridge_status": row.get("bridge_status"),
                    "count_cells_value_bridge_rows": row.get(
                        "count_cells_value_bridge_rows"
                    ),
                    "count_cells_bridge_rows": row.get("count_cells_bridge_rows"),
                    "count_value_bridge_rows": row.get("count_value_bridge_rows"),
                    "truth_cells_per_item": row.get("truth_cells_per_item"),
                    "truth_formal_per_item": row.get("truth_formal_per_item"),
                }
                for row in scp_count_value_bridge.get("rows", ())[:5]
            ],
        )
    )
    scp_bridge_holdout_candidate = scp_count_value_bridge_holdout["candidate_only"]
    scp_bridge_holdout_status = scp_count_value_bridge_holdout.get("overall_status")
    gates.append(
        _gate(
            "settlement_count_cells_value_bridge_holdout",
            "watch" if scp_bridge_holdout_status == "watch" else "blocked",
            "settlement count->cells/value bridge passes session holdout but remains shadow-only"
            if scp_bridge_holdout_status == "watch"
            else "settlement count->cells/value bridge does not pass session holdout",
            overall_status=scp_bridge_holdout_status,
            candidate_rows=scp_bridge_holdout_candidate.get("candidate_rows"),
            applied_rows=scp_bridge_holdout_candidate.get("applied_rows"),
            candidate_delta_formal_p50_mae=scp_bridge_holdout_candidate.get(
                "delta_formal_p50_mae"
            ),
            candidate_delta_formal_p90_coverage=scp_bridge_holdout_candidate.get(
                "delta_formal_p90_coverage"
            ),
            candidate_bridge_formal_p50_over_rate=scp_bridge_holdout_candidate.get(
                "bridge_formal_p50_over_rate"
            ),
            applied_hurts_groups=scp_count_value_bridge_holdout.get("applied_hurts"),
            status_counts=scp_count_value_bridge_holdout.get("status_counts"),
        )
    )
    scp_guarded_candidate = scp_guarded_bridge_holdout["candidate_only"]
    scp_guarded_status = scp_guarded_bridge_holdout.get("overall_status")
    gates.append(
        _gate(
            "settlement_count_guarded_bridge_holdout",
            "watch" if scp_guarded_status == "watch" else "blocked",
            "nested train-only guard has a shadow holdout candidate; sample depth and seed stability remain required"
            if scp_guarded_status == "watch"
            else "nested train-only settlement bridge guard does not pass holdout",
            overall_status=scp_guarded_status,
            formal_lift_cap=scp_guarded_bridge_holdout.get("formal_lift_cap"),
            max_guard_over_increase=scp_guarded_bridge_holdout.get(
                "max_guard_over_increase"
            ),
            candidate_rows=scp_guarded_candidate.get("candidate_rows"),
            applied_rows=scp_guarded_candidate.get("applied_rows"),
            candidate_delta_formal_p50_mae=scp_guarded_candidate.get(
                "delta_formal_p50_mae"
            ),
            candidate_delta_formal_p90_coverage=scp_guarded_candidate.get(
                "delta_formal_p90_coverage"
            ),
            candidate_bridge_formal_p50_over_rate=scp_guarded_candidate.get(
                "bridge_formal_p50_over_rate"
            ),
            selected_group_fold_counts=scp_guarded_bridge_holdout.get(
                "selected_group_fold_counts"
            ),
            applied_hurts_groups=scp_guarded_bridge_holdout.get("applied_hurts"),
            guard_status_counts=scp_guarded_bridge_holdout.get(
                "guard_status_counts"
            ),
        )
    )
    stability_status = (
        str(scp_guarded_bridge_stability.get("overall_status") or "unknown")
        if scp_guarded_bridge_stability is not None
        else "not_evaluated"
    )
    stability_gate_status = "watch" if stability_status == "watch" else "blocked"
    if scp_guarded_bridge_stability is None:
        stability_reason = (
            "guarded settlement bridge seed stability has not been evaluated"
            if scp_guarded_status == "watch"
            else "guarded settlement bridge holdout must pass before seed stability can promote"
        )
        stability_fields: dict[str, Any] = {
            "overall_status": stability_status,
            "status_reasons": ["missing_stability_matrix"],
            "run_count": 0,
            "watch_runs": 0,
            "required_selected_groups": [],
            "stable_selected_groups": [],
            "union_selected_groups": [],
            "selected_signature_counts": {},
            "hurt_group_counts": {},
            "min_applied_rows": 0,
            "min_applied_rows_required": None,
            "selected_group_support_summary": [],
            "selected_group_support_gap": [],
            "selected_group_guard_summary": [],
            "selected_group_instability_summary": [],
        }
    else:
        stability_reason = (
            "guarded settlement bridge is stable across posterior seeds"
            if stability_gate_status == "watch"
            else "guarded settlement bridge is not stable across posterior seeds"
        )
        stability_fields = {
            "overall_status": stability_status,
            "status_reasons": scp_guarded_bridge_stability.get(
                "status_reasons"
            ),
            "run_count": scp_guarded_bridge_stability.get("run_count"),
            "watch_runs": scp_guarded_bridge_stability.get("watch_runs"),
            "required_selected_groups": scp_guarded_bridge_stability.get(
                "required_selected_groups"
            ),
            "stable_selected_groups": scp_guarded_bridge_stability.get(
                "stable_selected_groups"
            ),
            "union_selected_groups": scp_guarded_bridge_stability.get(
                "union_selected_groups"
            ),
            "selected_signature_counts": scp_guarded_bridge_stability.get(
                "selected_signature_counts"
            ),
            "hurt_group_counts": scp_guarded_bridge_stability.get(
                "hurt_group_counts"
            ),
            "min_applied_rows": scp_guarded_bridge_stability.get(
                "min_applied_rows"
            ),
            "min_applied_rows_required": scp_guarded_bridge_stability.get(
                "min_applied_rows_required"
            ),
            "selected_group_support_summary": scp_guarded_bridge_stability.get(
                "selected_group_support_summary"
            ),
            "selected_group_support_gap": scp_guarded_bridge_stability.get(
                "selected_group_support_gap"
            ),
            "selected_group_guard_summary": scp_guarded_bridge_stability.get(
                "selected_group_guard_summary"
            ),
            "selected_group_instability_summary": scp_guarded_bridge_stability.get(
                "selected_group_instability_summary"
            ),
        }
    gates.append(
        _gate(
            "settlement_count_guarded_bridge_stability",
            stability_gate_status,
            stability_reason,
            **stability_fields,
        )
    )
    formal_below = float(summary.get("formal_p50_below_rate") or 0.0)
    formal_p90 = float(summary.get("formal_p90_coverage") or 0.0)
    formal_status = "blocked" if formal_below > 0.50 or formal_p90 < 0.80 else "watch"
    gates.append(
        _gate(
            "formal_baseline_metrics",
            formal_status,
            "formal baseline is still too low for promotion"
            if formal_status == "blocked"
            else "formal baseline is near promotion band but still shadow-only",
            formal_p50_mae=summary.get("formal_p50_mae"),
            formal_p50_below_rate=summary.get("formal_p50_below_rate"),
            formal_p90_coverage=summary.get("formal_p90_coverage"),
            q6_formal_p50_mae=summary.get("q6_formal_p50_mae"),
        )
    )

    under_candidate_only = under["candidate_only"]
    under_candidate_rows = int(under_candidate_only.get("n") or 0)
    under_delta = under_candidate_only.get("delta_formal_p50_mae")
    gates.append(
        _gate(
            "underestimate_repair_holdout",
            "watch" if under_candidate_rows else "blocked",
            "bounded upshift has holdout candidates but remains inactive"
            if under_candidate_rows
            else "no holdout candidate at current sample gate",
            candidate_rows=under_candidate_rows,
            candidate_groups=under_candidate_only.get("candidate_groups"),
            candidate_delta_formal_p50_mae=under_delta,
            overall_delta_formal_p50_mae=under["overall"].get(
                "delta_formal_p50_mae"
            ),
        )
    )

    ccv_counts = _status_counts(ccv)
    ccv_candidate_only = ccv_holdout["candidate_only"]
    ccv_holdout_rows = int(ccv_candidate_only.get("n") or 0)
    ccv_count_delta = ccv_candidate_only.get("delta_q6_count_p50_mae")
    ccv_cells_delta = ccv_candidate_only.get("delta_q6_cells_p50_mae")
    ccv_q6_formal_delta = ccv_candidate_only.get("delta_q6_formal_p50_mae")
    ccv_applied_hurts_groups = _ccv_applied_hurt_groups(ccv_holdout)
    ccv_map_applied_hurts_groups = _ccv_applied_hurt_groups(ccv_map_holdout)
    ccv_holdout_improves = (
        ccv_holdout_rows > 0
        and ccv_count_delta is not None
        and ccv_cells_delta is not None
        and ccv_q6_formal_delta is not None
        and float(ccv_count_delta) <= 0.0
        and float(ccv_cells_delta) < 0.0
        and float(ccv_q6_formal_delta) <= 0.0
        and not ccv_applied_hurts_groups
        and not ccv_map_applied_hurts_groups
    )
    ccv_global_cells_delta = summary.get("v3_ccv_delta_q6_cells_p50_mae")
    ccv_status = (
        "watch"
        if ccv_holdout_improves
        and (ccv_global_cells_delta is None or float(ccv_global_cells_delta) <= 0.0)
        else "blocked"
    )
    gates.append(
        _gate(
            "ccv_sampler",
            ccv_status,
            "CCV holdout is locally positive but remains shadow-only"
            if ccv_status == "watch"
            else "CCV candidate signal does not pass session holdout/global gates",
            status_counts=ccv_counts,
            watch_groups=_top_groups(ccv, "watch_only_count_cell_candidate"),
            global_count_delta=summary.get("v3_ccv_delta_q6_count_p50_mae"),
            global_cells_delta=ccv_global_cells_delta,
            holdout_candidate_rows=ccv_holdout_rows,
            holdout_candidate_groups=ccv_candidate_only.get("candidate_groups"),
            holdout_count_delta=ccv_count_delta,
            holdout_cells_delta=ccv_cells_delta,
            holdout_q6_formal_delta=ccv_q6_formal_delta,
            applied_ccv_hurts_groups=ccv_applied_hurts_groups,
            map_holdout_candidate_rows=ccv_map_holdout["candidate_only"].get("n"),
            map_holdout_candidate_groups=ccv_map_holdout["candidate_only"].get(
                "candidate_groups"
            ),
            map_applied_ccv_hurts_groups=ccv_map_applied_hurts_groups,
        )
    )
    ccv_direction_hurts = _ccv_directional_hurts(ccv_map_direction)
    ccv_profile_direction_hurts = _ccv_directional_hurts(ccv_profile_direction)
    gates.append(
        _gate(
            "ccv_directionality",
            "blocked" if ccv_direction_hurts or ccv_profile_direction_hurts else "watch",
            "CCV p50 movements have map/profile directional hurt"
            if ccv_direction_hurts or ccv_profile_direction_hurts
            else "CCV p50 movement direction is not currently blocking",
            map_direction_hurts=ccv_direction_hurts,
            profile_direction_hurts=ccv_profile_direction_hurts,
        )
    )
    ccv_direction_holdout_hurts = (
        ccv_map_direction_holdout.get("applied_direction_hurts_groups") or []
    )
    ccv_profile_direction_holdout_hurts = (
        ccv_profile_direction_holdout.get("applied_direction_hurts_groups") or []
    )
    ccv_direction_holdout_blocked = (
        ccv_map_direction_holdout.get("overall_status") != "watch"
        or ccv_profile_direction_holdout.get("overall_status") != "watch"
    )
    gates.append(
        _gate(
            "ccv_direction_holdout",
            "blocked" if ccv_direction_holdout_blocked else "watch",
            "directionally selected CCV movements fail session holdout"
            if ccv_direction_holdout_blocked
            else "directionally selected CCV movements pass current holdout but remain shadow-only",
            map_status=ccv_map_direction_holdout.get("overall_status"),
            map_candidate_rows=ccv_map_direction_holdout["candidate_only"].get(
                "candidate_rows"
            ),
            map_candidate_delta=ccv_map_direction_holdout["candidate_only"].get(
                "candidate_only_delta_p50_mae"
            ),
            map_applied_hurts_groups=ccv_direction_holdout_hurts,
            profile_status=ccv_profile_direction_holdout.get("overall_status"),
            profile_candidate_rows=ccv_profile_direction_holdout[
                "candidate_only"
            ].get("candidate_rows"),
            profile_candidate_delta=ccv_profile_direction_holdout[
                "candidate_only"
            ].get("candidate_only_delta_p50_mae"),
            profile_applied_hurts_groups=ccv_profile_direction_holdout_hurts,
        )
    )

    tail_counts = _status_counts(tail)
    tail_watch = (
        tail_counts.get("watch_only_q6_tail_value_candidate", 0)
        + tail_counts.get("watch_only_tail_value_candidate", 0)
    )
    tail_candidate_only = tail_holdout["candidate_only"]
    tail_holdout_rows = int(tail_candidate_only.get("n") or 0)
    tail_delta = tail_candidate_only.get("delta_tail_p50_mae")
    q6_tail_delta = tail_candidate_only.get("delta_q6_tail_p50_mae")
    tail_holdout_improves = (
        tail_holdout_rows > 0
        and (
            (tail_delta is not None and float(tail_delta) < 0.0)
            or (q6_tail_delta is not None and float(q6_tail_delta) < 0.0)
        )
    )
    tail_holdout_hurts = [
        str(row.get("group"))
        for row in tail_holdout.get("group_results", ())
        if (
            row.get("delta_tail_p50_mae") is not None
            and float(row["delta_tail_p50_mae"]) > 10_000.0
        )
        or (
            row.get("delta_q6_tail_p50_mae") is not None
            and float(row["delta_q6_tail_p50_mae"]) > 10_000.0
        )
    ][:5]
    gates.append(
        _gate(
            "tail_value_review",
            "watch" if tail_watch and tail_holdout_improves else "blocked",
            "tail/value review has holdout signal but remains non-formal"
            if tail_watch and tail_holdout_improves
            else "tail/value review lacks stable holdout support",
            status_counts=tail_counts,
            q6_tail_groups=_top_groups(tail, "watch_only_q6_tail_value_candidate"),
            tail_groups=_top_groups(tail, "watch_only_tail_value_candidate"),
            tail_hurts_groups=_top_groups(tail, "blocked_tail_estimate_hurts"),
            holdout_candidate_rows=tail_holdout_rows,
            holdout_candidate_groups=tail_candidate_only.get("candidate_groups"),
            holdout_tail_delta=tail_delta,
            holdout_q6_tail_delta=q6_tail_delta,
            holdout_hurts_groups=tail_holdout_hurts,
        )
    )

    tail_under_candidate = tail_under_holdout["candidate_only"]
    tail_under_rows = int(tail_under_candidate.get("n") or 0)
    tail_under_delta = tail_under_candidate.get("delta_formal_p50_mae")
    tail_under_p90_delta = tail_under_candidate.get("delta_formal_p90_coverage")
    tail_under_extreme_delta = tail_under_candidate.get(
        "delta_formal_p90_extreme_over_rate"
    )
    tail_under_q6_miss = tail_under_candidate.get(
        "candidate_q6_formal_p90_miss_rate"
    )
    tail_under_hurts_groups = [
        str(row.get("group"))
        for row in tail_under_holdout.get("group_results", ())
        if int(row.get("tail_candidate_rows") or 0) > 0
        and (
            (
                row.get("delta_tail_p50_mae") is not None
                and float(row["delta_tail_p50_mae"]) > 10_000.0
            )
            or (
                row.get("delta_q6_tail_p50_mae") is not None
                and float(row["delta_q6_tail_p50_mae"]) > 10_000.0
            )
        )
    ][:5]
    tail_under_improves = (
        tail_under_rows > 0
        and tail_under_delta is not None
        and float(tail_under_delta) <= 0.0
        and (
            tail_under_p90_delta is None
            or float(tail_under_p90_delta) >= 0.0
        )
        and (
            tail_under_extreme_delta is None
            or float(tail_under_extreme_delta) <= 0.02
        )
        and not tail_under_hurts_groups
    )
    gates.append(
        _gate(
            "tail_under_combined_holdout",
            "watch" if tail_under_improves else "blocked",
            "guarded under/tail combination improves holdout without excessive P90 over"
            if tail_under_improves
            else "guarded under/tail combination is not promotion-ready",
            candidate_rows=tail_under_rows,
            under_candidate_groups=tail_under_candidate.get(
                "under_candidate_groups"
            ),
            tail_candidate_groups=tail_under_candidate.get("tail_candidate_groups"),
            tail_hurt_guard_groups=tail_under_holdout["overall"].get(
                "tail_hurt_guard_groups"
            ),
            applied_tail_hurts_groups=tail_under_hurts_groups,
            candidate_delta_formal_p50_mae=tail_under_delta,
            candidate_delta_formal_p50_below_rate=tail_under_candidate.get(
                "delta_formal_p50_below_rate"
            ),
            candidate_delta_formal_p90_coverage=tail_under_p90_delta,
            candidate_delta_formal_p90_extreme_over_rate=tail_under_extreme_delta,
            candidate_q6_formal_p90_miss_rate=tail_under_q6_miss,
            overall_delta_formal_p50_mae=tail_under_holdout["overall"].get(
                "delta_formal_p50_mae"
            ),
        )
    )

    formal_value_sampler_candidate = formal_value_sampler_holdout["candidate_only"]
    formal_value_sampler_rows = int(
        formal_value_sampler_candidate.get("candidate_rows") or 0
    )
    formal_value_sampler_delta = formal_value_sampler_candidate.get(
        "delta_formal_p50_mae"
    )
    formal_value_sampler_q6_delta = formal_value_sampler_candidate.get(
        "delta_q6_formal_p50_mae"
    )
    formal_value_sampler_hurts = formal_value_sampler_holdout.get(
        "applied_hurts",
        [],
    )
    formal_value_sampler_mixed_watch_rows = int(
        formal_value_sampler_holdout["overall"].get("mixed_value_floor_watch_rows")
        or 0
    )
    formal_value_sampler_watch = (
        formal_value_sampler_holdout.get("overall_status") == "watch"
        and formal_value_sampler_rows > 0
        and not formal_value_sampler_hurts
    )
    gates.append(
        _gate(
            "formal_value_sampler_holdout",
            "watch" if formal_value_sampler_watch else "blocked",
            "formal/value sampler has holdout signal but remains shadow-only"
            if formal_value_sampler_watch
            else "formal/value sampler lacks enough safe holdout support",
            overall_status=formal_value_sampler_holdout.get("overall_status"),
            candidate_rows=formal_value_sampler_rows,
            candidate_groups=formal_value_sampler_candidate.get(
                "candidate_groups"
            ),
            candidate_delta_formal_p50_mae=formal_value_sampler_delta,
            candidate_delta_q6_formal_p50_mae=formal_value_sampler_q6_delta,
            candidate_formal_below_rate=formal_value_sampler_candidate.get(
                "candidate_formal_p50_below_rate"
            ),
            candidate_formal_over_rate=formal_value_sampler_candidate.get(
                "candidate_formal_p50_over_rate"
            ),
            candidate_formal_p90_coverage=formal_value_sampler_candidate.get(
                "candidate_formal_p90_coverage"
            ),
            mixed_value_floor_watch_rows=formal_value_sampler_mixed_watch_rows,
            applied_hurts_groups=formal_value_sampler_hurts,
        )
    )

    residual_counts = _status_counts(residual)
    gates.append(
        _gate(
            "residual_gate",
            "blocked",
            "residual remains watch-only; active rows must stay zero",
            status_counts=residual_counts,
            active_rows=summary.get("v3_resid_gate_active_rows"),
        )
    )

    profile_blocked = (
        under_profile["overall"].get("candidate_rows") == 0
        and ccv_profile_holdout["overall"].get("candidate_rows") == 0
        and tail_profile_holdout["overall"].get("candidate_rows") == 0
        and _status_counts(ccv_profile).get("blocked_low_sample", 0) > 0
        and _status_counts(tail_profile).get("blocked_low_sample", 0) > 0
    )
    gates.append(
        _gate(
            "profile_sample_depth",
            "blocked" if profile_blocked else "watch",
            "profile-level promotion remains sample-limited"
            if profile_blocked
            else "some profile-level candidates need review",
            under_profile_candidate_rows=under_profile["overall"].get(
                "candidate_rows"
            ),
            ccv_profile_holdout_candidate_rows=ccv_profile_holdout["overall"].get(
                "candidate_rows"
            ),
            tail_profile_holdout_candidate_rows=tail_profile_holdout["overall"].get(
                "candidate_rows"
            ),
            ccv_profile_status_counts=_status_counts(ccv_profile),
            tail_profile_status_counts=_status_counts(tail_profile),
        )
    )

    gates.append(
        _gate(
            "v2_archive_readiness",
            "pending",
            "v2 cannot be archived until v3 formal path is promoted and verified",
        )
    )

    next_actions = []
    if any(gate["name"] == "formal_baseline_metrics" and gate["status"] == "blocked" for gate in gates):
        next_actions.append("continue 2506 bounded upshift/tail-value shadow validation")
    if profile_blocked:
        next_actions.append("collect targeted profile samples before profile-level promotion")
    if tail_counts.get("blocked_tail_estimate_hurts", 0):
        next_actions.append("keep tail-hurts guard before any tail/value sampler")
    if tail_under_hurts_groups:
        next_actions.append("tighten tail guard; holdout still applies hurting groups")
    if not tail_under_improves:
        next_actions.append("keep under/tail combination in audit until holdout improves")
    if ccv_applied_hurts_groups:
        next_actions.append("tighten CCV guard; holdout still applies hurting groups")
    if ccv_map_applied_hurts_groups:
        next_actions.append("tighten CCV map-layer guard; map holdout applies hurting groups")
    if ccv_direction_hurts or ccv_profile_direction_hurts:
        next_actions.append("redesign CCV likelihood; p50 movement direction is unstable")
    if ccv_direction_holdout_blocked:
        next_actions.append("keep CCV direction selection in audit; holdout is not stable")
    if ccv_counts.get("watch_only_count_cell_candidate", 0):
        next_actions.append("redesign CCV likelihood; current holdout is not promotion-ready")
    if not formal_value_sampler_watch:
        next_actions.append("keep formal/value sampler shadow-only until holdout has safe support")
    if not scp_link_ready:
        next_actions.append("bridge settlement count-prior to cells/value before formal/value sampler promotion")
    if scp_bridge_rows:
        next_actions.append("hold out settlement count->cells/value bridge candidates before sampler use")
    if scp_bridge_holdout_status != "watch":
        next_actions.append("guard or redesign settlement count->cells/value bridge; holdout over-risk is high")
    if scp_guarded_status == "watch":
        next_actions.append("collect more 2506 guarded-bridge holdout support across posterior seeds")
    else:
        next_actions.append("keep nested settlement bridge guard in audit until holdout stabilizes")
    if stability_gate_status != "watch":
        if stability_status == "not_evaluated":
            next_actions.append(
                "run guarded settlement bridge stability matrix before treating seed-0 watch as support"
            )
        else:
            next_actions.append(
                "keep guarded settlement bridge out of promotion; multi-seed stability failed"
            )
    if not prior_stress_drift_ready:
        next_actions.append("audit prior-stressed capacity/table drift by map/profile before promotion")
    if not robust_ready:
        next_actions.append("separate activity/prior-drift rows before formal promotion")

    blocked = _blocked_count(gates)
    gate_dependencies = summarize_gate_dependencies(gates)
    return {
        "overall_status": "not_ready" if blocked else "watch_only",
        "blocked_gates": blocked,
        "group_field": group_field,
        "profile_field": profile_field,
        "min_windows": int(min_windows),
        "min_sessions": int(min_sessions),
        "folds": int(folds),
        "summary": {
            key: summary.get(key)
            for key in (
                "windows",
                "ready",
                "no_state",
                "constraint_conflict",
                "parse_errors",
                "posterior_ready",
                "posterior_strict_ready",
                "posterior_summary_likelihood",
                "robust_prior_usable",
                "robust_prior_trusted",
                "robust_activity_candidate",
                "robust_prior_stressed",
                "formal_p50_mae",
                "formal_p50_below_rate",
                "formal_p90_coverage",
                "q6_formal_p50_mae",
                "v3_cal_delta_formal_p50_mae",
                "v3_under_delta_formal_p50_mae",
                "v3_ccv_delta_q6_count_p50_mae",
                "v3_ccv_delta_q6_cells_p50_mae",
                "v3_tail_review_candidate_rows",
                "v3_tail_review_hurt_guard_rows",
                "v3_tail_review_active_rows",
                "v3_fv_candidate_rows",
                "v3_fv_capacity_watch_rows",
                "v3_fv_value_floor_candidate_rows",
                "v3_fv_delta_formal_p50_mae",
                "v3_cse_ready_rows",
                "v3_cse_candidate_rows",
                "v3_cse_pressure_candidate_rows",
                "v3_cse_active_rows",
                "v3_resid_gate_active_rows",
            )
        },
        "gates": gates,
        "gate_dependencies": gate_dependencies,
        "prior_stress_detail_summary": {
            "rows": prior_stress_group_rows,
            "capacity_flag_hits": prior_stress_capacity_hits,
            "capacity_flag_counts": prior_stress_capacity_flags,
            "capacity_count_summary": prior_stress_overall.get(
                "capacity_count_summary"
            ),
            "consistency_bucket_counts": prior_stress_overall.get(
                "consistency_bucket_counts"
            ),
            "consistency_class_counts": prior_stress_overall.get(
                "consistency_class_counts"
            ),
            "source_counts": prior_stress_overall.get("source_counts"),
            "ratio_summary": prior_stress_overall.get("ratio_summary"),
            "top_map_groups": _top_prior_stress_groups(
                prior_stress_detail_summary,
                "map_id",
            ),
            "top_profile_groups": _top_prior_stress_groups(
                prior_stress_detail_summary,
                "hero_map_evidence_profile",
            ),
        },
        "underestimate_holdout": {
            "candidate_rows": under_candidate_rows,
            "candidate_groups": under_candidate_only.get("candidate_groups"),
            "candidate_delta_formal_p50_mae": under_delta,
            "overall_delta_formal_p50_mae": under["overall"].get(
                "delta_formal_p50_mae"
            ),
        },
        "ccv_holdout": {
            "candidate_rows": ccv_holdout_rows,
            "candidate_groups": ccv_candidate_only.get("candidate_groups"),
            "candidate_delta_q6_count_p50_mae": ccv_count_delta,
            "candidate_delta_q6_cells_p50_mae": ccv_cells_delta,
            "candidate_delta_q6_formal_p50_mae": ccv_q6_formal_delta,
            "applied_ccv_hurts_groups": ccv_applied_hurts_groups,
            "map_candidate_rows": ccv_map_holdout["candidate_only"].get("n"),
            "map_candidate_groups": ccv_map_holdout["candidate_only"].get(
                "candidate_groups"
            ),
            "map_applied_ccv_hurts_groups": ccv_map_applied_hurts_groups,
            "map_candidate_delta_q6_count_p50_mae": ccv_map_holdout[
                "candidate_only"
            ].get("delta_q6_count_p50_mae"),
            "map_candidate_delta_q6_cells_p50_mae": ccv_map_holdout[
                "candidate_only"
            ].get("delta_q6_cells_p50_mae"),
            "map_candidate_delta_q6_formal_p50_mae": ccv_map_holdout[
                "candidate_only"
            ].get("delta_q6_formal_p50_mae"),
            "overall_delta_q6_cells_p50_mae": ccv_holdout["overall"].get(
                "delta_q6_cells_p50_mae"
            ),
        },
        "ccv_directionality": {
            "map_direction_hurts": ccv_direction_hurts,
            "profile_direction_hurts": ccv_profile_direction_hurts,
            "map_status_counts": dict(
                sorted(Counter(str(row.get("status")) for row in ccv_map_direction).items())
            ),
            "profile_status_counts": dict(
                sorted(
                    Counter(
                        str(row.get("status")) for row in ccv_profile_direction
                    ).items()
                )
            ),
        },
        "ccv_direction_holdout": {
            "map_status": ccv_map_direction_holdout.get("overall_status"),
            "map_candidate_rows": ccv_map_direction_holdout["candidate_only"].get(
                "candidate_rows"
            ),
            "map_candidate_delta": ccv_map_direction_holdout["candidate_only"].get(
                "candidate_only_delta_p50_mae"
            ),
            "map_applied_hurts_groups": ccv_direction_holdout_hurts,
            "profile_status": ccv_profile_direction_holdout.get("overall_status"),
            "profile_candidate_rows": ccv_profile_direction_holdout[
                "candidate_only"
            ].get("candidate_rows"),
            "profile_candidate_delta": ccv_profile_direction_holdout[
                "candidate_only"
            ].get("candidate_only_delta_p50_mae"),
            "profile_applied_hurts_groups": ccv_profile_direction_holdout_hurts,
        },
        "tail_holdout": {
            "candidate_rows": tail_holdout_rows,
            "candidate_groups": tail_candidate_only.get("candidate_groups"),
            "candidate_delta_tail_p50_mae": tail_delta,
            "candidate_delta_q6_tail_p50_mae": q6_tail_delta,
            "overall_delta_tail_p50_mae": tail_holdout["overall"].get(
                "delta_tail_p50_mae"
            ),
            "overall_delta_q6_tail_p50_mae": tail_holdout["overall"].get(
                "delta_q6_tail_p50_mae"
            ),
            "holdout_hurts_groups": tail_holdout_hurts,
        },
        "tail_under_holdout": {
            "candidate_rows": tail_under_rows,
            "under_candidate_groups": tail_under_candidate.get(
                "under_candidate_groups"
            ),
            "tail_candidate_groups": tail_under_candidate.get(
                "tail_candidate_groups"
            ),
            "tail_hurt_guard_groups": tail_under_holdout["overall"].get(
                "tail_hurt_guard_groups"
            ),
            "applied_tail_hurts_groups": tail_under_hurts_groups,
            "candidate_delta_formal_p50_mae": tail_under_delta,
            "candidate_delta_formal_p50_below_rate": tail_under_candidate.get(
                "delta_formal_p50_below_rate"
            ),
            "candidate_delta_formal_p90_coverage": tail_under_p90_delta,
            "candidate_delta_formal_p90_extreme_over_rate": tail_under_extreme_delta,
            "candidate_q6_formal_p90_miss_rate": tail_under_q6_miss,
            "overall_delta_formal_p50_mae": tail_under_holdout["overall"].get(
                "delta_formal_p50_mae"
            ),
        },
        "formal_value_sampler_holdout": {
            "status": formal_value_sampler_holdout.get("overall_status"),
            "candidate_rows": formal_value_sampler_rows,
            "candidate_groups": formal_value_sampler_candidate.get(
                "candidate_groups"
            ),
            "candidate_delta_formal_p50_mae": formal_value_sampler_delta,
            "candidate_delta_q6_formal_p50_mae": formal_value_sampler_q6_delta,
            "candidate_formal_below_rate": formal_value_sampler_candidate.get(
                "candidate_formal_p50_below_rate"
            ),
            "candidate_formal_over_rate": formal_value_sampler_candidate.get(
                "candidate_formal_p50_over_rate"
            ),
            "candidate_formal_p90_coverage": formal_value_sampler_candidate.get(
                "candidate_formal_p90_coverage"
            ),
            "mixed_value_floor_watch_rows": formal_value_sampler_mixed_watch_rows,
            "applied_hurts_groups": formal_value_sampler_hurts,
            "train_candidate_status_counts": formal_value_sampler_holdout.get(
                "train_candidate_status_counts"
            ),
        },
        "settlement_count_formal_value_link": {
            "formal_rows": scp_link_overall.get("formal_rows"),
            "scp_candidate_formal_rows": scp_link_candidate_rows,
            "scp_candidate_value_floor_rows": scp_link_value_rows,
            "scp_candidate_capacity_watch_rows": scp_link_overall.get(
                "scp_candidate_capacity_watch_rows"
            ),
            "formal_fv_delta_p50_mae": scp_link_delta,
            "formal_baseline_p50_below_rate": scp_link_overall.get(
                "formal_baseline_p50_below_rate"
            ),
            "formal_baseline_p90_coverage": scp_link_overall.get(
                "formal_baseline_p90_coverage"
            ),
            "status_counts": scp_formal_value_link.get("status_counts"),
        },
        "settlement_count_cells_value_bridge": {
            "status": scp_bridge_status,
            "metric_rows": scp_bridge_overall.get("metric_rows"),
            "scp_candidate_metric_rows": scp_bridge_overall.get(
                "scp_candidate_metric_rows"
            ),
            "scp_p95_above_target_rows": scp_bridge_overall.get(
                "scp_p95_above_target_rows"
            ),
            "cells_p90_under_rows": scp_bridge_overall.get("cells_p90_under_rows"),
            "formal_p90_under_rows": scp_bridge_overall.get("formal_p90_under_rows"),
            "count_cells_bridge_rows": scp_bridge_overall.get(
                "count_cells_bridge_rows"
            ),
            "count_value_bridge_rows": scp_bridge_overall.get(
                "count_value_bridge_rows"
            ),
            "count_cells_value_bridge_rows": scp_bridge_rows,
            "cells_per_item": scp_bridge_overall.get("truth_cells_per_item"),
            "formal_per_item": scp_bridge_overall.get("truth_formal_per_item"),
            "status_counts": scp_count_value_bridge.get("status_counts"),
        },
        "settlement_count_cells_value_bridge_holdout": {
            "status": scp_bridge_holdout_status,
            "candidate_rows": scp_bridge_holdout_candidate.get("candidate_rows"),
            "applied_rows": scp_bridge_holdout_candidate.get("applied_rows"),
            "candidate_delta_formal_p50_mae": scp_bridge_holdout_candidate.get(
                "delta_formal_p50_mae"
            ),
            "candidate_delta_formal_p90_coverage": scp_bridge_holdout_candidate.get(
                "delta_formal_p90_coverage"
            ),
            "candidate_bridge_formal_p50_over_rate": scp_bridge_holdout_candidate.get(
                "bridge_formal_p50_over_rate"
            ),
            "applied_hurts_groups": scp_count_value_bridge_holdout.get(
                "applied_hurts"
            ),
            "status_counts": scp_count_value_bridge_holdout.get("status_counts"),
        },
        "settlement_count_guarded_bridge_holdout": {
            "status": scp_guarded_status,
            "formal_lift_cap": scp_guarded_bridge_holdout.get("formal_lift_cap"),
            "max_guard_over_increase": scp_guarded_bridge_holdout.get(
                "max_guard_over_increase"
            ),
            "candidate_rows": scp_guarded_candidate.get("candidate_rows"),
            "applied_rows": scp_guarded_candidate.get("applied_rows"),
            "candidate_delta_formal_p50_mae": scp_guarded_candidate.get(
                "delta_formal_p50_mae"
            ),
            "candidate_delta_formal_p90_coverage": scp_guarded_candidate.get(
                "delta_formal_p90_coverage"
            ),
            "candidate_bridge_formal_p50_over_rate": scp_guarded_candidate.get(
                "bridge_formal_p50_over_rate"
            ),
            "selected_group_fold_counts": scp_guarded_bridge_holdout.get(
                "selected_group_fold_counts"
            ),
            "applied_hurts_groups": scp_guarded_bridge_holdout.get(
                "applied_hurts"
            ),
            "guard_status_counts": scp_guarded_bridge_holdout.get(
                "guard_status_counts"
            ),
        },
        "settlement_count_guarded_bridge_stability": {
            "status": stability_status,
            **stability_fields,
        },
        "ccv_status_counts": ccv_counts,
        "tail_status_counts": tail_counts,
        "residual_status_counts": residual_counts,
        "next_actions": next_actions,
    }


def _print_summary(result: dict[str, Any]) -> None:
    summary = result["summary"]
    print(
        " ".join(
            (
                f"overall_status={result['overall_status']}",
                f"blocked_gates={result['blocked_gates']}",
                f"windows={summary['windows']}",
                f"ready={summary['ready']}",
                f"formal_mae={summary['formal_p50_mae']}",
                f"formal_below={summary['formal_p50_below_rate']}",
                f"formal_p90_cover={summary['formal_p90_coverage']}",
                f"under_delta={summary['v3_under_delta_formal_p50_mae']}",
                f"ccv_cells_delta={summary['v3_ccv_delta_q6_cells_p50_mae']}",
                f"ccv_holdout_rows={result['ccv_holdout']['candidate_rows']}",
                "ccv_applied_hurts="
                + ",".join(result["ccv_holdout"]["applied_ccv_hurts_groups"]),
                f"ccv_map_rows={result['ccv_holdout']['map_candidate_rows']}",
                "ccv_map_applied_hurts="
                + ",".join(result["ccv_holdout"]["map_applied_ccv_hurts_groups"]),
                "ccv_direction_hurts="
                + ",".join(result["ccv_directionality"]["map_direction_hurts"]),
                "ccv_direction_holdout="
                f"{result['ccv_direction_holdout']['map_status']}",
                f"tail_review_candidate_rows={summary['v3_tail_review_candidate_rows']}",
                f"tail_review_hurt_guard_rows={summary['v3_tail_review_hurt_guard_rows']}",
                f"tail_holdout_q6_delta={result['tail_holdout']['candidate_delta_q6_tail_p50_mae']}",
                f"tail_under_rows={result['tail_under_holdout']['candidate_rows']}",
                f"tail_under_formal_delta={result['tail_under_holdout']['candidate_delta_formal_p50_mae']}",
                f"tail_under_p90_extreme_delta={result['tail_under_holdout']['candidate_delta_formal_p90_extreme_over_rate']}",
                "tail_under_applied_hurts="
                + ",".join(result["tail_under_holdout"]["applied_tail_hurts_groups"]),
                f"formal_value_rows={result['formal_value_sampler_holdout']['candidate_rows']}",
                f"formal_value_delta={result['formal_value_sampler_holdout']['candidate_delta_formal_p50_mae']}",
                "formal_value_applied_hurts="
                + ",".join(
                    result["formal_value_sampler_holdout"]["applied_hurts_groups"]
                ),
                f"scp_value_link_rows={result['settlement_count_formal_value_link']['scp_candidate_value_floor_rows']}",
                f"scp_capacity_link_rows={result['settlement_count_formal_value_link']['scp_candidate_capacity_watch_rows']}",
                f"scp_value_link_delta={result['settlement_count_formal_value_link']['formal_fv_delta_p50_mae']}",
                f"scp_count_cells_value_bridge_rows={result['settlement_count_cells_value_bridge']['count_cells_value_bridge_rows']}",
                f"scp_count_cells_bridge_rows={result['settlement_count_cells_value_bridge']['count_cells_bridge_rows']}",
                f"scp_count_value_bridge_rows={result['settlement_count_cells_value_bridge']['count_value_bridge_rows']}",
                f"scp_bridge_holdout_status={result['settlement_count_cells_value_bridge_holdout']['status']}",
                f"scp_bridge_holdout_delta={result['settlement_count_cells_value_bridge_holdout']['candidate_delta_formal_p50_mae']}",
                f"scp_bridge_holdout_over={result['settlement_count_cells_value_bridge_holdout']['candidate_bridge_formal_p50_over_rate']}",
                f"scp_guarded_status={result['settlement_count_guarded_bridge_holdout']['status']}",
                f"scp_guarded_rows={result['settlement_count_guarded_bridge_holdout']['applied_rows']}",
                f"scp_guarded_delta={result['settlement_count_guarded_bridge_holdout']['candidate_delta_formal_p50_mae']}",
                f"scp_guarded_over={result['settlement_count_guarded_bridge_holdout']['candidate_bridge_formal_p50_over_rate']}",
                f"scp_guarded_stability={result['settlement_count_guarded_bridge_stability']['status']}",
                "scp_guarded_stable_groups="
                + ",".join(
                    result["settlement_count_guarded_bridge_stability"].get(
                        "stable_selected_groups"
                    )
                    or []
                ),
                f"cse_candidate_rows={summary['v3_cse_candidate_rows']}",
                f"cse_pressure_candidate_rows={summary['v3_cse_pressure_candidate_rows']}",
                f"cse_active_rows={summary['v3_cse_active_rows']}",
                f"prior_stress_detail_rows={result['prior_stress_detail_summary']['rows']}",
                f"prior_stress_capacity_hits={result['prior_stress_detail_summary']['capacity_flag_hits']}",
                f"resid_gate_active={summary['v3_resid_gate_active_rows']}",
            )
        )
    )
    for gate in result["gates"]:
        print(
            " ".join(
                (
                    f"gate={gate['name']}",
                    f"status={gate['status']}",
                    f"reason={json.dumps(gate['reason'], ensure_ascii=False)}",
                )
            )
        )
    dependencies = result["gate_dependencies"]
    if dependencies["blocked_or_pending_lanes"]:
        print(
            "gate_dependency_lanes="
            + ",".join(dependencies["blocked_or_pending_lanes"])
        )
    if result["next_actions"]:
        print("next_actions=" + " | ".join(result["next_actions"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize v3 formal-promotion readiness blockers.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument("--by", default="hero_map_id")
    parser.add_argument("--profile-by", default="hero_map_evidence_profile")
    parser.add_argument("--min-windows", type=int, default=20)
    parser.add_argument("--min-sessions", type=int, default=8)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    parser.add_argument("--posterior-trials", type=int, default=512)
    parser.add_argument("--posterior-seed", type=int, default=0)
    parser.add_argument(
        "--tail-value-review",
        type=Path,
        default=_default_tail_value_review_path(),
    )
    parser.add_argument("--no-tail-value-review", action="store_true")
    parser.add_argument(
        "--settlement-count-prior",
        type=Path,
        default=_default_settlement_count_prior_path(),
    )
    parser.add_argument("--no-settlement-count-prior", action="store_true")
    parser.add_argument(
        "--capacity-source-expansion",
        type=Path,
        default=_default_capacity_source_expansion_path(),
    )
    parser.add_argument("--no-capacity-source-expansion", action="store_true")
    parser.add_argument(
        "--guarded-bridge-stability-json",
        type=Path,
        help=(
            "Optional JSON output from summarize_v3_scp_guarded_bridge_stability.py "
            "to attach multi-seed stability evidence to readiness."
        ),
    )
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
        tail_value_review_entries=(
            {}
            if args.no_tail_value_review
            else load_tail_value_review_entries(args.tail_value_review)
        ),
        settlement_count_prior_entries=(
            {}
            if args.no_settlement_count_prior
            else load_settlement_count_prior_entries(args.settlement_count_prior)
        ),
        capacity_source_expansion_entries=(
            {}
            if args.no_capacity_source_expansion
            else load_capacity_source_expansion_entries(args.capacity_source_expansion)
        ),
        posterior_trials=args.posterior_trials,
        posterior_seed=args.posterior_seed,
    )
    guarded_bridge_stability = None
    if args.guarded_bridge_stability_json is not None:
        with args.guarded_bridge_stability_json.open("r", encoding="utf-8") as handle:
            guarded_bridge_stability = json.load(handle)
    result = summarize_readiness(
        rows,
        errors,
        group_field=args.by,
        profile_field=args.profile_by,
        min_windows=args.min_windows,
        min_sessions=args.min_sessions,
        folds=args.folds,
        scp_guarded_bridge_stability=guarded_bridge_stability,
    )
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_summary(result)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
