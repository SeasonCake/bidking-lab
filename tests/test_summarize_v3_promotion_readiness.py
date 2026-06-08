import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_v3_promotion_readiness.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_v3_promotion_readiness",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _row(
    group: str,
    *,
    session_id: str,
    truth: int,
    pred: int,
    p90: int,
) -> dict[str, object]:
    return {
        "status": "ready",
        "round": 1,
        "session_id": session_id,
        "hero": group.split("|", 1)[0],
        "hero_map_id": group,
        "hero_map_evidence_profile": f"{group}|item+shape",
        "evidence_stage": "early_1_2",
        "information_density_band": "medium",
        "evidence_profile_key": "item+shape",
        "numeric_constraints": 1,
        "item_anchors": 1,
        "shape_anchors": 1,
        "quality_floor_anchors": 1,
        "v3_prior_available": True,
        "v3_robust_available": True,
        "v3_robust_affects_bid": False,
        "v3_robust_status": "ok",
        "v3_robust_prior_usable": True,
        "v3_robust_prior_trusted": True,
        "v3_robust_fallback_mode": "normal_prior",
        "v3_robust_activity_candidate": False,
        "v3_robust_prior_stress_score": 0,
        "v3_robust_reasons": "",
        "v3_truth_available": True,
        "v3_truth_decision_available": True,
        "v3_summary_available": True,
        "v3_summary_conflict_count": 0,
        "v3_summary_session_total_cells_exact": 80,
        "v3_summary_q6_cells_floor": 4,
        "v3_post_available": True,
        "v3_post_ready": True,
        "v3_post_strict_ready": False,
        "v3_post_match_scope": "summary_likelihood",
        "v3_post_formal_decision_value_p50": pred,
        "v3_post_formal_decision_value_p90": p90,
        "v3_post_q6_formal_decision_value_p50": pred // 2,
        "v3_post_q6_formal_decision_value_p90": p90 // 2,
        "v3_post_q6_count_p50": 2,
        "v3_post_q6_count_p90": 3,
        "v3_post_q6_cells_p50": 8,
        "v3_post_q6_cells_p90": 12,
        "v3_post_q6_value_p50": pred // 2,
        "v3_truth_formal_decision_value": truth,
        "v3_truth_tail_replacement_decision_value": truth + 100,
        "v3_truth_tail_replacement_value": 100,
        "v3_truth_q6_formal_decision_value": truth // 2,
        "v3_truth_q6_tail_replacement_decision_value": truth // 2 + 100,
        "v3_truth_q6_tail_replacement_value": 100,
        "v3_truth_q6_count": 2,
        "v3_truth_q6_cells": 8,
        "v3_truth_q6_raw_value": truth // 2,
        "v3_ccv_ready": True,
        "v3_ccv_match_scope": "ccv_likelihood",
        "v3_ccv_q6_count_p50": 2,
        "v3_ccv_q6_count_p90": 3,
        "v3_ccv_q6_cells_p50": 8,
        "v3_ccv_q6_cells_p90": 12,
        "v3_ccv_q6_value_p50": truth // 2,
        "v3_ccv_q6_formal_decision_value_p50": truth // 2,
        "v3_resid_ready": True,
        "v3_resid_match_scope": "residual_likelihood",
        "v3_resid_q6_count_p50": 2,
        "v3_resid_q6_count_p90": 3,
        "v3_resid_q6_cells_p50": 8,
        "v3_resid_q6_cells_p90": 12,
        "v3_resid_q6_value_p50": truth // 2,
        "v3_resid_gate_ready": True,
        "v3_resid_gate_active": False,
        "v3_resid_gate_q6_count_p50": 2,
        "v3_resid_gate_q6_count_p90": 3,
        "v3_resid_gate_q6_cells_p50": 8,
        "v3_resid_gate_q6_cells_p90": 12,
        "v3_resid_gate_q6_value_p50": truth // 2,
        "v3_cal_ready": True,
        "v3_cal_active": False,
        "v3_cal_formal_decision_value_p50": pred,
        "v3_cal_formal_decision_value_p90": p90,
        "v3_cal_q6_formal_decision_value_p50": pred // 2,
        "v3_cal_q6_formal_decision_value_p90": p90 // 2,
        "v3_under_ready": True,
        "v3_under_active": False,
        "v3_under_candidate": False,
        "v3_under_formal_decision_value_p50": pred,
        "v3_under_formal_decision_value_p90": p90,
        "v3_under_q6_formal_decision_value_p50": pred // 2,
        "v3_under_q6_formal_decision_value_p90": p90 // 2,
        "v3_fv_ready": True,
        "v3_fv_affects_bid": False,
        "v3_fv_active": False,
        "v3_fv_candidate": False,
        "v3_fv_stress_class": "none",
        "v3_fv_formal_decision_value_p50": pred,
        "v3_fv_formal_decision_value_p90": p90,
        "v3_fv_q6_formal_decision_value_p50": pred // 2,
        "v3_fv_q6_formal_decision_value_p90": p90 // 2,
        "v3_scp_ready": True,
        "v3_scp_active": False,
        "v3_scp_candidate": False,
        "v3_scp_missing_table": False,
        "v3_scp_status": "table_caps_cover_observed_shadow_only",
        "v3_cse_ready": True,
        "v3_cse_affects_bid": False,
        "v3_cse_active": False,
        "v3_cse_candidate": False,
        "v3_cse_pressure_candidate": False,
        "v3_cse_status": "within_capacity_source_semantics_shadow_only",
        "v3_post_tail_replacement_decision_value_p50": pred + 100,
        "v3_post_tail_replacement_decision_value_p90": p90 + 100,
        "v3_post_q6_tail_replacement_decision_value_p50": pred // 2 + 100,
        "v3_post_q6_tail_replacement_decision_value_p90": p90 // 2 + 100,
    }


def test_readiness_blocks_formal_when_below_rate_is_high() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
    )

    assert result["overall_status"] == "not_ready"
    gates = {row["name"]: row for row in result["gates"]}
    assert gates["archive_data_quality"]["status"] == "pass"
    assert gates["shared_shadow_pipeline"]["status"] == "pass"
    assert gates["v3_practical_archive_live_guard_metrics"]["status"] == "pending"
    assert gates["prior_robustness"]["status"] == "pass"
    assert gates["prior_stress_capacity_table_drift"]["status"] == "pass"
    assert gates["settlement_count_prior_shadow"]["status"] == "watch"
    assert gates["settlement_count_prior_shadow"]["active_rows"] == 0
    assert gates["capacity_source_expansion_shadow"]["status"] == "watch"
    assert gates["capacity_source_expansion_shadow"]["active_rows"] == 0
    assert gates["capacity_source_expansion_shadow"]["pressure_candidate_rows"] == 0
    assert gates["settlement_count_formal_value_link"]["status"] == "blocked"
    assert gates["settlement_count_formal_value_link"]["scp_candidate_formal_rows"] == 0
    assert gates["settlement_count_cells_value_bridge"]["status"] == "blocked"
    assert gates["settlement_count_cells_value_bridge"]["count_cells_value_bridge_rows"] == 0
    assert gates["settlement_count_cells_value_bridge_holdout"]["status"] == "blocked"
    assert gates["settlement_count_cells_value_bridge_holdout"]["applied_rows"] == 0
    assert gates["settlement_count_guarded_bridge_holdout"]["status"] == "blocked"
    assert gates["settlement_count_guarded_bridge_holdout"]["applied_rows"] == 0
    assert gates["settlement_count_guarded_bridge_stability"]["status"] == "blocked"
    assert gates["settlement_count_guarded_bridge_stability"]["overall_status"] == (
        "not_evaluated"
    )
    assert gates["formal_baseline_metrics"]["status"] == "blocked"
    assert "holdout_candidate_rows" in gates["ccv_sampler"]
    assert "applied_ccv_hurts_groups" in gates["ccv_sampler"]
    assert "ccv_directionality" in gates
    assert "map_direction_hurts" in gates["ccv_directionality"]
    assert "ccv_direction_holdout" in gates
    assert "map_candidate_rows" in gates["ccv_direction_holdout"]
    assert "shadow_sampler_prototype" not in gates
    assert "holdout_candidate_rows" in gates["tail_value_review"]
    assert "tail_under_combined_holdout" in gates
    assert "formal_value_sampler_holdout" in gates
    assert "candidate_rows" in gates["formal_value_sampler_holdout"]
    assert "mixed_value_floor_watch_rows" in gates["formal_value_sampler_holdout"]
    assert gates["v2_archive_readiness"]["status"] == "pending"
    assert "ccv_holdout" in result
    assert "applied_ccv_hurts_groups" in result["ccv_holdout"]
    assert "map_applied_ccv_hurts_groups" in result["ccv_holdout"]
    assert "ccv_directionality" in result
    assert "ccv_direction_holdout" in result
    assert "tail_holdout" in result
    assert "tail_under_holdout" in result
    assert "formal_value_sampler_holdout" in result
    assert "mixed_value_floor_watch_rows" in result["formal_value_sampler_holdout"]
    assert "settlement_count_formal_value_link" in result
    assert "settlement_count_cells_value_bridge" in result
    assert "settlement_count_cells_value_bridge_holdout" in result
    assert "settlement_count_guarded_bridge_holdout" in result
    assert "settlement_count_guarded_bridge_stability" in result
    assert "gate_dependencies" in result
    dependencies = result["gate_dependencies"]
    assert "formal_value_shadow_sampler" in dependencies["blocked_or_pending_lanes"]
    assert "settlement_bridge_support" in dependencies["blocked_or_pending_lanes"]
    assert "v2_archive_after_promotion" in dependencies["blocked_or_pending_lanes"]
    dependency_gates = {
        row["gate"]: row for row in dependencies["blocked_or_pending_gates"]
    }
    assert dependency_gates["formal_baseline_metrics"]["lane"] == (
        "formal_value_shadow_sampler"
    )
    assert dependency_gates["settlement_count_guarded_bridge_holdout"]["lane"] == (
        "settlement_bridge_support"
    )
    assert dependency_gates["settlement_count_guarded_bridge_stability"]["lane"] == (
        "settlement_bridge_support"
    )
    assert dependency_gates["v2_archive_readiness"]["status"] == "pending"
    assert "prior_stress_detail_summary" in result
    assert result["prior_stress_detail_summary"]["rows"] == 0
    assert result["v3_practical_archive_live_guard_metrics"]["status"] == "not_supplied"
    assert result["shadow_sampler_prototype_contract"]["status"] == "not_supplied"
    assert (
        "attach v3 practical archive-live guard brief JSON before promotion review"
        in result["next_actions"]
    )


def test_readiness_attaches_shadow_sampler_prototype_contract() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]
    prototype = {
        "interface": "v3_ccvc_evidence_driven_count_cell_value_sampler",
        "shadow_only": True,
        "affects_bid": False,
        "active": False,
        "status": "blocked_seed_instability",
        "posterior_seeds": [0, 1],
        "stable_watch_candidate_labels": [],
        "min_watch_support_rows": 20,
        "min_watch_support_sessions": 8,
        "component_statuses": [
            {
                "component": "q6_count",
                "status": "blocked_seed_instability",
                "support_gate": {
                    "status": "watch_low_support",
                    "low_support_watch_metrics": [
                        {
                            "posterior_seed": 1,
                            "watch_label": (
                                "q6_count|map_id,evidence_profile_key|down_only:"
                                "q6_count:map_id=2501|"
                                "evidence_profile_key=tool:category+item+shape"
                            ),
                            "support_rows": 8,
                            "support_sessions": 3,
                        }
                    ],
                    "stable_low_support_watch_metrics": [],
                },
            }
        ],
        "guard_trial_contract": {
            "interface": "v3_ccvc_shadow_sampler_guard_trial_contract",
            "status": "requires_source_support_gate",
            "shadow_only": True,
            "affects_bid": False,
            "active": False,
            "can_promote": False,
            "action_counts": {"require_source_support_gate": 1},
            "component_actions": [
                {
                    "component": "q6_count",
                    "trial_action": "require_source_support_gate",
                    "requires_source_parser": True,
                }
            ],
        },
    }

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        shadow_sampler_prototype=prototype,
    )

    gates = {row["name"]: row for row in result["gates"]}
    gate = gates["shadow_sampler_prototype"]
    assert gate["status"] == "blocked"
    assert gate["contract_status"] == "blocked"
    assert gate["prototype_status"] == "blocked_seed_instability"
    assert gate["component_status_counts"] == {"blocked_seed_instability": 1}
    assert gate["support_gate_status_counts"] == {"watch_low_support": 1}
    assert gate["guard_trial_status"] == "requires_source_support_gate"
    assert gate["guard_trial_action_counts"] == {
        "require_source_support_gate": 1
    }
    assert gate["low_support_watch_metrics"][0]["support_rows"] == 8
    contract = result["shadow_sampler_prototype_contract"]
    assert contract["status"] == "blocked"
    assert contract["shadow_safe"] is True
    assert contract["blocking_component_statuses"] == [
        {
            "component": "q6_count",
            "status": "blocked_seed_instability",
            "support_gate": "watch_low_support",
        }
    ]
    assert contract["guard_trial_status"] == "requires_source_support_gate"
    assert contract["guard_trial_contract"]["component_actions"][0][
        "requires_source_parser"
    ] is True
    assert result["shadow_sampler_prototype"] == prototype
    dependency_gates = {
        row["gate"]: row
        for row in result["gate_dependencies"]["blocked_or_pending_gates"]
    }
    assert dependency_gates["shadow_sampler_prototype"]["lane"] == (
        "sampler_safety_holdout"
    )


def test_readiness_attaches_shadow_sampler_guard_trial_contract() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]
    trial = {
        "interface": "v3_ccvc_shadow_sampler_guarded_trial",
        "status": "blocked_guarded_shadow_trial",
        "sampler_status": "blocked_seed_instability",
        "shadow_only": True,
        "affects_bid": False,
        "active": False,
        "can_promote": False,
        "source_prototype_status": "blocked_seed_instability",
        "source_guard_trial_status": "shadow_guard_trial_design",
        "trial_options": {
            "component_move_cells": False,
            "excluded_components": ["q6_cells", "q6_count"],
            "candidate_exclude_labels": ["q6_value:2510"],
        },
        "component_status_counts": {
            "blocked_seed_instability": 1,
            "sample_limited": 2,
        },
        "support_gate_status_counts": {"no_watch": 2, "pass": 1},
        "guarded_sampler_result": {
            "component_statuses": [
                {
                    "component": "q6_value",
                    "status": "blocked_seed_instability",
                    "support_gate": {"status": "pass"},
                }
            ]
        },
        "required_verification": ["archive", "posterior_seed"],
    }

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        shadow_sampler_guard_trial=trial,
    )

    gates = {row["name"]: row for row in result["gates"]}
    gate = gates["shadow_sampler_guard_trial"]
    assert gate["status"] == "blocked"
    assert gate["contract_status"] == "blocked"
    assert gate["trial_status"] == "blocked_guarded_shadow_trial"
    assert gate["sampler_status"] == "blocked_seed_instability"
    assert gate["component_status_counts"] == {
        "blocked_seed_instability": 1,
        "sample_limited": 2,
    }
    contract = result["shadow_sampler_guard_trial_contract"]
    assert contract["status"] == "blocked"
    assert contract["trial_options"]["component_move_cells"] is False
    assert contract["blocking_component_statuses"] == [
        {
            "component": "q6_value",
            "status": "blocked_seed_instability",
            "support_gate": "pass",
        }
    ]
    dependency_gates = {
        row["gate"]: row
        for row in result["gate_dependencies"]["blocked_or_pending_gates"]
    }
    assert dependency_gates["shadow_sampler_guard_trial"]["lane"] == (
        "sampler_safety_holdout"
    )


def test_readiness_attaches_shadow_sampler_value_source_profile_audit() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]
    audit = {
        "interface": "v3_ccvc_q6_value_source_profile_audit",
        "status": "blocked_risk_migration",
        "shadow_only": True,
        "affects_bid": False,
        "active": False,
        "can_promote": False,
        "component": "q6_value",
        "run_count": 2,
        "runs": [
            {
                "label": "baseline",
                "audit_probe": False,
                "component_status": "blocked_seed_instability",
                "sampler_status": "blocked_seed_instability",
                "support_gate": "pass",
                "source_profile_parser_required": True,
                "hurt_label_count": 2,
                "hurt_map_ids": ["2510"],
                "hurt_evidence_profiles": ["public:total+item+shape"],
                "hurt_group_field_counts": {"map_id": 1},
            },
            {
                "label": "probe",
                "audit_probe": True,
                "component_status": "blocked_seed_instability",
                "sampler_status": "blocked_seed_instability",
                "support_gate": "watch_low_support",
                "source_profile_parser_required": True,
                "hurt_label_count": 2,
                "hurt_map_ids": ["2405"],
                "hurt_evidence_profiles": ["public:max_item_cells+item+shape"],
                "hurt_group_field_counts": {"evidence_profile_key": 1},
            },
        ],
        "migration": {
            "status": "evaluated",
            "risk_migration_detected": True,
            "introduced_hurt_labels": [
                "q6_value|map_id|up_only:q6_value:2405"
            ],
            "removed_hurt_labels": [
                "q6_value|map_id|up_only:q6_value:2510"
            ],
        },
        "source_profile_parser": {
            "status": "blocked_mixed_map_profile_risk",
            "profile_semantic_migration_detected": True,
            "latest_map_only_hurt_label_count": 1,
            "latest_profile_hurt_label_count": 1,
        },
        "next_action": (
            "stop adding manual q6_value excludes; design source/profile "
            "parser or higher-level value guard"
        ),
    }

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        shadow_sampler_value_source_profile_audit=audit,
    )

    gates = {row["name"]: row for row in result["gates"]}
    gate = gates["shadow_sampler_value_source_profile_audit"]
    assert gate["status"] == "blocked"
    assert gate["contract_status"] == "blocked"
    assert gate["audit_status"] == "blocked_risk_migration"
    assert gate["component"] == "q6_value"
    assert gate["risk_migration_detected"] is True
    assert gate["source_profile_parser_status"] == (
        "blocked_mixed_map_profile_risk"
    )
    assert gate["latest_map_only_hurt_label_count"] == 1
    assert gate["introduced_hurt_labels"] == [
        "q6_value|map_id|up_only:q6_value:2405"
    ]
    contract = result["shadow_sampler_value_source_profile_contract"]
    assert contract["status"] == "blocked"
    assert contract["shadow_safe"] is True
    assert contract["profile_semantic_migration_detected"] is True
    assert contract["run_summaries"][1]["support_gate"] == "watch_low_support"
    assert result["shadow_sampler_value_source_profile_audit"] == audit
    dependency_gates = {
        row["gate"]: row
        for row in result["gate_dependencies"]["blocked_or_pending_gates"]
    }
    assert dependency_gates["shadow_sampler_value_source_profile_audit"]["lane"] == (
        "sampler_safety_holdout"
    )


def test_readiness_attaches_live_practical_guard_brief() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]
    brief = {
        "total_rows": 49,
        "source_counts": {"windivert_archive": 49},
        "overall": {
            "rows": 49,
            "formal_mode_counts": {"v2": 15, "v3_practical": 34},
            "formal_mode_reason_counts": {
                "v2_mode_requested": 15,
                "v3_practical_ready_live_guarded": 34,
            },
            "v3_practical_formal_rows": 34,
            "v3_practical_live_guard_rows": 23,
            "v3_practical_live_guard_rate": 0.68,
            "v3_practical_live_guard_reason_counts": {
                "live_prior_only_raise_guard": 23,
            },
            "v3_practical_unguarded_rows": 23,
            "v3_practical_guard_comparison_rows": 23,
            "v3_practical_guarded_mae_on_comparison": 120_000,
            "v3_practical_unguarded_mae_on_comparison": 120_000,
            "v3_practical_guarded_minus_unguarded_mae": 0.0,
            "v3_practical_guarded_minus_unguarded_median_p50": 0.0,
            "v3_practical_guarded_minus_unguarded_median_p90": -30_000,
            "v3_practical_guarded_p90_coverage_on_comparison": 0.57,
            "v3_practical_unguarded_p90_coverage_on_comparison": 1.0,
            "v3_practical_guarded_minus_unguarded_p90_coverage": -0.43,
            "v3_practical_guarded_p90_extreme_over_on_comparison": 0.09,
            "v3_practical_unguarded_p90_extreme_over_on_comparison": 0.57,
            "v3_practical_guarded_minus_unguarded_p90_extreme_over": -0.48,
        },
        "prebid_overall": {
            "rows": 49,
            "formal_mode_counts": {"v2": 15, "v3_practical": 34},
            "formal_mode_reason_counts": {
                "v2_mode_requested": 15,
                "v3_practical_ready_live_guarded": 34,
            },
            "v3_practical_formal_rows": 34,
            "v3_practical_live_guard_rows": 23,
            "v3_practical_live_guard_reason_counts": {
                "live_prior_only_raise_guard": 23,
            },
            "v3_practical_unguarded_rows": 23,
            "v3_practical_guard_comparison_rows": 23,
            "v3_practical_guarded_mae_on_comparison": 120_000,
            "v3_practical_unguarded_mae_on_comparison": 120_000,
            "v3_practical_guarded_minus_unguarded_mae": 0.0,
            "v3_practical_guarded_minus_unguarded_median_p50": 0.0,
            "v3_practical_guarded_minus_unguarded_median_p90": -30_000,
            "v3_practical_guarded_p90_coverage_on_comparison": 0.57,
            "v3_practical_unguarded_p90_coverage_on_comparison": 1.0,
            "v3_practical_guarded_minus_unguarded_p90_coverage": -0.43,
            "v3_practical_guarded_p90_extreme_over_on_comparison": 0.09,
            "v3_practical_unguarded_p90_extreme_over_on_comparison": 0.57,
            "v3_practical_guarded_minus_unguarded_p90_extreme_over": -0.48,
        },
    }

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        live_practical_guard_brief=brief,
    )

    gates = {row["name"]: row for row in result["gates"]}
    guard_gate = gates["v3_practical_archive_live_guard_metrics"]
    assert guard_gate["status"] == "watch"
    assert guard_gate["overall"]["v3_practical_guard_comparison_rows"] == 23
    metrics = result["v3_practical_archive_live_guard_metrics"]
    assert metrics["status"] == "watch"
    assert metrics["overall"]["v3_practical_formal_rows"] == 34
    assert (
        metrics["overall"]["v3_practical_guarded_minus_unguarded_p90_coverage"]
        == -0.43
    )
    assert metrics["contract_checks"]["overall"]["status"] == "watch"
    assert metrics["contract_checks"]["prebid_overall"]["status"] == "watch"
    assert (
        "review v3 practical guard coverage/extreme-over tradeoff by slice before promotion"
        in result["next_actions"]
    )


def test_readiness_blocks_malformed_live_practical_guard_brief() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        live_practical_guard_brief={
            "overall": {
                "v3_practical_formal_rows": 34,
                "v3_practical_guard_comparison_rows": 0,
            }
        },
    )

    gates = {row["name"]: row for row in result["gates"]}
    assert gates["v3_practical_archive_live_guard_metrics"]["status"] == "blocked"
    assert result["v3_practical_archive_live_guard_metrics"]["status"] == "blocked"
    assert (
        "regenerate v3 practical brief with paired guarded/unguarded rows"
        in result["next_actions"]
    )


def test_readiness_blocks_live_practical_guard_brief_without_prebid_contract() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]
    brief = {
        "overall": {
            "rows": 4,
            "formal_mode_counts": {"v3_practical": 4},
            "formal_mode_reason_counts": {"v3_practical_ready_live_guarded": 4},
            "v3_practical_formal_rows": 4,
            "v3_practical_live_guard_rows": 4,
            "v3_practical_live_guard_reason_counts": {"guard": 4},
            "v3_practical_unguarded_rows": 4,
            "v3_practical_guard_comparison_rows": 4,
            "v3_practical_guarded_mae_on_comparison": 1.0,
            "v3_practical_unguarded_mae_on_comparison": 1.0,
            "v3_practical_guarded_minus_unguarded_mae": 0.0,
            "v3_practical_guarded_minus_unguarded_median_p50": 0.0,
            "v3_practical_guarded_minus_unguarded_median_p90": -10.0,
            "v3_practical_guarded_p90_coverage_on_comparison": 0.5,
            "v3_practical_unguarded_p90_coverage_on_comparison": 1.0,
            "v3_practical_guarded_minus_unguarded_p90_coverage": -0.5,
            "v3_practical_guarded_p90_extreme_over_on_comparison": 0.0,
            "v3_practical_unguarded_p90_extreme_over_on_comparison": 0.5,
            "v3_practical_guarded_minus_unguarded_p90_extreme_over": -0.5,
        },
        "prebid_overall": {
            "rows": 4,
            "v3_practical_formal_rows": 4,
            "v3_practical_guard_comparison_rows": 0,
        },
    }

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        live_practical_guard_brief=brief,
    )

    metrics = result["v3_practical_archive_live_guard_metrics"]
    assert metrics["status"] == "blocked"
    assert metrics["contract_checks"]["overall"]["status"] == "watch"
    assert metrics["contract_checks"]["prebid_overall"]["status"] == "blocked"
    assert (
        "formal_mode_counts"
        in metrics["contract_checks"]["prebid_overall"]["missing_keys"]
    )


def test_readiness_attaches_guarded_bridge_stability_matrix() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        scp_guarded_bridge_stability={
            "overall_status": "blocked_applied_hurt",
            "status_reasons": ["applied_hurts_present"],
            "posterior_trials": 64,
            "posterior_seeds": [0, 1],
            "run_count": 2,
            "watch_runs": 1,
            "required_selected_groups": ["2506"],
            "stable_selected_groups": ["2506"],
            "union_selected_groups": ["2501", "2506"],
            "selected_signature_counts": {"2506:2": 1, "2501:1,2506:1": 1},
            "hurt_group_counts": {"2501": 1},
            "min_applied_rows": 20,
            "min_applied_rows_required": 20,
            "selected_group_support_summary": [
                {
                    "group": "2501",
                    "run_count": 1,
                    "min_applied_rows": 53,
                    "hurt_run_count": 1,
                }
            ],
            "selected_group_support_gap": [],
            "selected_group_guard_summary": [
                {
                    "group": "2501",
                    "run_count": 1,
                    "guard_status_counts": {"watch_train_guard": 1},
                }
            ],
            "selected_group_instability_summary": [
                {
                    "group": "2501",
                    "status": "blocked_train_holdout_instability",
                }
            ],
        },
    )

    gates = {row["name"]: row for row in result["gates"]}
    stability = gates["settlement_count_guarded_bridge_stability"]
    assert stability["status"] == "blocked"
    assert stability["overall_status"] == "blocked_applied_hurt"
    assert stability["contract_check"]["status"] == "watch"
    assert stability["posterior_trials"] == 64
    assert stability["posterior_seeds"] == [0, 1]
    assert stability["status_reasons"] == ["applied_hurts_present"]
    assert stability["hurt_group_counts"] == {"2501": 1}
    assert stability["selected_group_support_summary"][0]["group"] == "2501"
    assert stability["selected_group_guard_summary"][0]["group"] == "2501"
    assert stability["selected_group_instability_summary"][0]["status"] == (
        "blocked_train_holdout_instability"
    )
    assert result["settlement_count_guarded_bridge_stability"]["status"] == (
        "blocked_applied_hurt"
    )


def test_readiness_blocks_malformed_guarded_bridge_stability_matrix() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        scp_guarded_bridge_stability={
            "overall_status": "watch",
            "run_count": 1,
            "watch_runs": 1,
            "required_selected_groups": ["2506"],
            "stable_selected_groups": [],
            "union_selected_groups": ["2506"],
            "selected_signature_counts": {"2506:1": 1},
            "hurt_group_counts": {},
            "min_applied_rows": 20,
            "min_applied_rows_required": 20,
            "selected_group_support_summary": [],
            "selected_group_support_gap": [],
            "selected_group_guard_summary": [],
            "selected_group_instability_summary": [],
        },
    )

    gates = {row["name"]: row for row in result["gates"]}
    stability = gates["settlement_count_guarded_bridge_stability"]
    assert stability["status"] == "blocked"
    assert stability["contract_check"]["status"] == "blocked"
    assert "posterior_trials" in stability["contract_check"]["missing_keys"]
    assert "posterior_seeds" in stability["contract_check"]["missing_keys"]
    assert "watch stability must cover all required selected groups" in stability["reason"]


def _cse_artifact(*, active: bool = False) -> dict[str, object]:
    return {
        "affects_bid": False,
        "active": active,
        "generated_at": "2026-06-08",
        "source": "archive_settlement_source_semantics_audit",
        "group_bys": ["map_id", "map_family"],
        "table_overlay_metadata": {"raw_file_version": 303},
        "cohorts": [{"label": "default_archive", "status": "ok"}],
        "entries": [
            {
                "scope": "map_id",
                "group": "2506",
                "status": "watch_capacity_source_expansion_shadow_only",
                "gate_reason": "observed_unique_round_over_cap_source_expansion",
                "source": "archive_capacity_source_expansion_shadow:default_archive",
                "archive_sessions": 21,
                "mechanism_classes": "session_capacity_source_semantics:1",
                "source_evidence_classes": "settlement_payload_verified_only:1",
                "source_context_classes": "payload_verified_partial_action_only:1",
                "unique_round_overflow_rows": 1,
                "server_side_expansion_rows": 0,
                "session_capacity_source_semantics_rows": 1,
                "public_total_match_rows": 0,
                "full_action_rows": 0,
                "payload_verified_only_rows": 1,
                "payload_inventory_mismatch_rows": 0,
                "non_zodiac_missing_max": 0,
            }
        ],
    }


def test_readiness_attaches_capacity_source_expansion_artifact_contract() -> None:
    module = _load_module()
    rows = [
        {
            **_row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700),
            "v3_cse_candidate": True,
            "v3_cse_pressure_candidate": True,
            "v3_cse_status": "watch_capacity_source_expansion_shadow_only",
        }
        for idx in range(4)
    ]

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        capacity_source_expansion_artifact=_cse_artifact(),
    )

    gates = {row["name"]: row for row in result["gates"]}
    cse = gates["capacity_source_expansion_shadow"]
    assert cse["status"] == "watch"
    assert cse["artifact_contract"]["status"] == "watch"
    assert cse["artifact_contract"]["entries"] == 1
    assert cse["artifact_contract"]["candidate_entries"] == 1
    assert cse["artifact_contract"]["group_bys"] == ["map_id", "map_family"]
    assert result["capacity_source_expansion_artifact_contract"]["cohorts"] == 1


def test_readiness_blocks_malformed_capacity_source_expansion_artifact() -> None:
    module = _load_module()
    rows = [
        _row("aisha|2506", session_id=f"s{idx}", truth=1_000, pred=500, p90=700)
        for idx in range(4)
    ]

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
        capacity_source_expansion_artifact={
            **_cse_artifact(active=True),
            "entries": [{"scope": "map_id", "group": "2506"}],
        },
    )

    gates = {row["name"]: row for row in result["gates"]}
    cse = gates["capacity_source_expansion_shadow"]
    assert cse["status"] == "blocked"
    assert cse["artifact_contract"]["status"] == "blocked"
    assert "artifact active must be false" in cse["reason"]
    assert "status" in cse["artifact_contract"]["entry_missing_key_counts"]


def test_readiness_blocks_prior_robustness_on_activity_candidate() -> None:
    module = _load_module()
    rows = [
        {
            **_row("aisha|2526", session_id=f"s{idx}", truth=1_000, pred=1_000, p90=1_200),
            "v3_robust_status": "prior_unavailable",
            "v3_robust_prior_usable": False,
            "v3_robust_prior_trusted": False,
            "v3_robust_fallback_mode": "missing_prior_truth_only",
            "v3_robust_activity_candidate": True,
            "v3_robust_reasons": "activity_map_id_candidate",
        }
        for idx in range(2)
    ]

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
    )

    gates = {row["name"]: row for row in result["gates"]}
    assert gates["prior_robustness"]["status"] == "blocked"
    assert gates["prior_robustness"]["robust_activity_candidate"] == 2
    assert gates["prior_robustness"]["robust_prior_trusted"] == 0
    dependency_gates = {
        row["gate"]: row
        for row in result["gate_dependencies"]["blocked_or_pending_gates"]
    }
    assert dependency_gates["prior_robustness"]["lane"] == "table_activity_capacity"
    assert "activity_candidate_rows=2" in dependency_gates["prior_robustness"]["focus"]
    assert "separate activity/prior-drift rows before formal promotion" in result["next_actions"]


def test_readiness_surfaces_prior_stress_capacity_groups() -> None:
    module = _load_module()
    rows = [
        {
            **_row(
                "ethan|2501",
                session_id=f"s{idx}",
                truth=1_000,
                pred=700,
                p90=900,
            ),
            "map_id": 2501,
            "v3_robust_status": "prior_stressed",
            "v3_robust_prior_trusted": False,
            "v3_robust_prior_stress_score": 2,
            "v3_robust_reasons": "total_count_above_prior;total_cells_above_prior",
            "v3_prior_expected_count": 2,
            "v3_prior_expected_cells": 20,
            "v3_prior_q6_expected_cells": 4,
            "v3_prior_items_per_session_max": 5,
            "v3_summary_session_total_count_exact": 7,
            "v3_summary_session_total_cells_exact": 48,
            "v3_summary_q6_cells_floor": 8,
            "v3_truth_item_count": 7,
            "v3_truth_total_cells": 48,
            "v3_post_total_cells_p50": 40,
            "v3_post_total_cells_p90": 50,
            "v3_truth_q6_cells": 8,
            "v3_post_q6_cells_p50": 6,
            "v3_post_q6_cells_p90": 10,
        }
        for idx in range(2)
    ]

    result = module.summarize_readiness(
        rows,
        [],
        min_windows=2,
        min_sessions=2,
        folds=2,
    )

    gates = {row["name"]: row for row in result["gates"]}
    drift = gates["prior_stress_capacity_table_drift"]
    assert drift["status"] == "blocked"
    assert drift["detail_rows"] == 2
    assert drift["capacity_flag_hits"] == 4
    assert drift["capacity_flag_counts"] == {
        "target_count_above_prior_max": 2,
        "truth_count_above_prior_max": 2,
    }
    assert drift["capacity_count_summary"]["target_prior_max_delta"]["avg"] == 2
    assert drift["capacity_count_summary"]["truth_prior_max_delta"]["avg"] == 2
    assert drift["capacity_count_summary"]["target_truth_delta"]["avg"] == 0
    assert drift["capacity_count_summary"]["case_counts"] == {
        "direct_prior_max_conflict": 2
    }
    assert drift["detail_contract"]["status"] == "watch"
    assert drift["detail_contract"]["rows"] == 2
    assert drift["detail_contract"]["capacity_flag_hits"] == 4
    assert drift["detail_contract"]["case_counts"] == {
        "direct_prior_max_conflict": 2
    }
    assert drift["detail_contract"]["top_map_groups"][0]["value"] == "2501"
    assert drift["consistency_bucket_counts"] == {
        "hard_capacity_conflict": 2
    }
    assert drift["consistency_class_counts"]["capacity_direct_prior_max_conflict"] == 2
    assert drift["top_map_groups"][0]["value"] == "2501"
    assert drift["top_map_groups"][0]["capacity_flag_hits"] == 4
    assert (
        drift["top_map_groups"][0]["capacity_count_summary"][
            "target_prior_max_delta"
        ]["max"]
        == 2
    )
    assert drift["top_map_groups"][0]["capacity_count_summary"]["case_counts"] == {
        "direct_prior_max_conflict": 2
    }
    assert drift["top_profile_groups"][0]["value"] == "ethan|2501|item+shape"
    assert result["prior_stress_detail_summary"]["rows"] == 2
    assert result["prior_stress_detail_summary"]["top_map_groups"][0]["value"] == "2501"
    assert (
        result["prior_stress_detail_summary"]["capacity_count_summary"][
            "truth_prior_max_delta"
        ]["avg"]
        == 2
    )
    assert result["prior_stress_detail_summary"]["consistency_bucket_counts"] == {
        "hard_capacity_conflict": 2
    }
    assert (
        "audit prior-stressed capacity/table drift by map/profile before promotion"
        in result["next_actions"]
    )
    dependency_gates = {
        row["gate"]: row
        for row in result["gate_dependencies"]["blocked_or_pending_gates"]
    }
    drift_dependency = dependency_gates["prior_stress_capacity_table_drift"]
    assert drift_dependency["lane"] == "table_activity_capacity"
    assert drift_dependency["focus"] == (
        "detail_rows=2;capacity_flag_hits=4;"
        "top_cases=direct_prior_max_conflict:2"
    )


def test_prior_stress_detail_contract_blocks_malformed_summary() -> None:
    module = _load_module()
    result = module.summarize_prior_stress_detail_contract(
        {
            "overall": {
                "rows": 1,
                "capacity_flag_counts": {"truth_count_above_prior_max": 1},
            },
            "by_group": [],
        },
        top_map_groups=[],
        top_profile_groups=[],
    )

    assert result["status"] == "blocked"
    assert "capacity_count_summary" in result["missing_keys"]
    assert "top map groups are missing" in result["reason"]


def test_readiness_blocks_archive_data_quality_on_parse_errors() -> None:
    module = _load_module()
    rows = [
        _row("ethan|2502", session_id="s1", truth=1_000, pred=1_000, p90=1_200),
        _row("ethan|2502", session_id="s2", truth=1_000, pred=1_000, p90=1_200),
    ]

    result = module.summarize_readiness(
        rows,
        [{"file": "bad.json", "error": "ValueError"}],
        min_windows=2,
        min_sessions=2,
        folds=2,
    )

    gates = {row["name"]: row for row in result["gates"]}
    assert gates["archive_data_quality"]["status"] == "blocked"
    assert result["blocked_gates"] >= 1
