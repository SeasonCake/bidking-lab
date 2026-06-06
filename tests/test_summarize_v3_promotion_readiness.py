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
    assert gates["prior_robustness"]["status"] == "pass"
    assert gates["prior_stress_capacity_table_drift"]["status"] == "pass"
    assert gates["settlement_count_prior_shadow"]["status"] == "watch"
    assert gates["settlement_count_prior_shadow"]["active_rows"] == 0
    assert gates["settlement_count_formal_value_link"]["status"] == "blocked"
    assert gates["settlement_count_formal_value_link"]["scp_candidate_formal_rows"] == 0
    assert gates["settlement_count_cells_value_bridge"]["status"] == "blocked"
    assert gates["settlement_count_cells_value_bridge"]["count_cells_value_bridge_rows"] == 0
    assert gates["formal_baseline_metrics"]["status"] == "blocked"
    assert "holdout_candidate_rows" in gates["ccv_sampler"]
    assert "applied_ccv_hurts_groups" in gates["ccv_sampler"]
    assert "ccv_directionality" in gates
    assert "map_direction_hurts" in gates["ccv_directionality"]
    assert "ccv_direction_holdout" in gates
    assert "map_candidate_rows" in gates["ccv_direction_holdout"]
    assert "holdout_candidate_rows" in gates["tail_value_review"]
    assert "tail_under_combined_holdout" in gates
    assert "formal_value_sampler_holdout" in gates
    assert "candidate_rows" in gates["formal_value_sampler_holdout"]
    assert gates["v2_archive_readiness"]["status"] == "pending"
    assert "ccv_holdout" in result
    assert "applied_ccv_hurts_groups" in result["ccv_holdout"]
    assert "map_applied_ccv_hurts_groups" in result["ccv_holdout"]
    assert "ccv_directionality" in result
    assert "ccv_direction_holdout" in result
    assert "tail_holdout" in result
    assert "tail_under_holdout" in result
    assert "formal_value_sampler_holdout" in result
    assert "settlement_count_formal_value_link" in result
    assert "settlement_count_cells_value_bridge" in result
    assert "prior_stress_detail_summary" in result
    assert result["prior_stress_detail_summary"]["rows"] == 0


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
    assert (
        "audit prior-stressed capacity/table drift by map/profile before promotion"
        in result["next_actions"]
    )


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
