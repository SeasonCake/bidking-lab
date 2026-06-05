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
    assert gates["formal_baseline_metrics"]["status"] == "blocked"
    assert "holdout_candidate_rows" in gates["ccv_sampler"]
    assert "applied_ccv_hurts_groups" in gates["ccv_sampler"]
    assert "holdout_candidate_rows" in gates["tail_value_review"]
    assert "tail_under_combined_holdout" in gates
    assert gates["v2_archive_readiness"]["status"] == "pending"
    assert "ccv_holdout" in result
    assert "applied_ccv_hurts_groups" in result["ccv_holdout"]
    assert "map_applied_ccv_hurts_groups" in result["ccv_holdout"]
    assert "tail_holdout" in result
    assert "tail_under_holdout" in result


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
