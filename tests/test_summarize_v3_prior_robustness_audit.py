import importlib.util
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "summarize_v3_prior_robustness_audit.py"
    )
    spec = importlib.util.spec_from_file_location(
        "summarize_v3_prior_robustness_audit",
        path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _ready_row(
    *,
    map_id: int,
    pred: int,
    truth: int,
    p90: int,
    stress_score: int,
    reasons: str,
    status: str = "prior_stressed",
    trusted: bool = False,
    activity: bool = False,
    post_ready: bool = True,
    scope: str = "strict",
) -> dict[str, object]:
    return {
        "status": "ready",
        "map_id": map_id,
        "hero": "aisha",
        "round": 2,
        "evidence_profile_key": "shape+layout",
        "hero_map_evidence_profile": f"aisha|{map_id}|shape+layout",
        "v3_truth_decision_available": True,
        "v3_post_ready": post_ready,
        "v3_post_match_scope": scope,
        "v3_truth_formal_decision_value": truth,
        "v3_post_formal_decision_value_p50": pred,
        "v3_post_formal_decision_value_p90": p90,
        "v3_truth_q6_count": 3,
        "v3_post_q6_count_p50": 1,
        "v3_truth_q6_cells": 10,
        "v3_post_q6_cells_p50": 4,
        "v3_truth_q6_raw_value": 300,
        "v3_post_q6_value_p50": 100,
        "v3_prior_q6_expected_count": 1,
        "v3_prior_q6_expected_cells": 4,
        "v3_prior_q6_expected_value": 100,
        "v3_summary_q6_count_floor": 3,
        "v3_summary_q6_cells_floor": 10,
        "v3_summary_q6_value_floor": 300,
        "v3_robust_status": status,
        "v3_robust_prior_usable": not activity,
        "v3_robust_prior_trusted": trusted,
        "v3_robust_fallback_mode": (
            "missing_prior_truth_only" if activity else "strict_with_prior_stress"
        ),
        "v3_robust_activity_candidate": activity,
        "v3_robust_prior_stress_score": stress_score,
        "v3_robust_reasons": reasons,
    }


def test_prior_robustness_audit_groups_stress_and_activity() -> None:
    module = _load_module()
    rows = [
        _ready_row(
            map_id=2506,
            pred=80,
            truth=100,
            p90=110,
            stress_score=2,
            reasons="q6_count_above_prior;q6_cells_above_prior",
        ),
        {
            **_ready_row(
                map_id=2506,
                pred=160,
                truth=200,
                p90=210,
                stress_score=2,
                reasons="q6_count_above_prior;q6_cells_above_prior",
            ),
            "v3_prior_q6_expected_count": 2,
            "v3_prior_q6_expected_cells": 6,
            "v3_summary_q6_count_floor": 4,
            "v3_summary_q6_cells_floor": 12,
        },
        _ready_row(
            map_id=2401,
            pred=100,
            truth=100,
            p90=120,
            stress_score=0,
            reasons="summary_likelihood_fallback",
            status="weak_prior_fallback",
            scope="summary_likelihood",
        ),
        _ready_row(
            map_id=2526,
            pred=0,
            truth=0,
            p90=0,
            stress_score=0,
            reasons="prior_error=KeyError;activity_map_id_candidate",
            status="prior_unavailable",
            activity=True,
            post_ready=False,
            scope="none",
        ),
    ]

    by_map = module.summarize_prior_robustness(rows, "map_id")
    by_reason = module.summarize_prior_robustness(rows, "v3_robust_reason")

    stressed = next(row for row in by_map if row["value"] == "2506")
    assert stressed["ready"] == 2
    assert stressed["posterior_ready"] == 2
    assert stressed["metric_rows"] == 2
    assert stressed["prior_stressed"] == 2
    assert stressed["prior_trusted"] == 0
    assert stressed["reason_counts"] == {
        "q6_cells_above_prior": 2,
        "q6_count_above_prior": 2,
    }
    assert stressed["formal_p50_mae"] == 30
    assert stressed["formal_p50_bias"] == -30
    assert stressed["formal_p50_below_rate"] == 1.0
    assert stressed["formal_p90_coverage"] == 1.0
    assert stressed["q6_count_target_prior_ratio_avg"] == 2.5
    assert stressed["q6_count_target_prior_ratio_max"] == 3.0
    assert stressed["q6_cells_target_prior_ratio_avg"] == 2.25
    assert "prior_stressed" in stressed["flags"]
    assert "high_below" in stressed["flags"]

    activity = next(row for row in by_map if row["value"] == "2526")
    assert activity["metric_rows"] == 0
    assert activity["posterior_ready"] == 0
    assert activity["activity_candidate"] == 1
    assert activity["prior_usable"] == 0
    assert activity["fallback_counts"] == {"missing_prior_truth_only": 1}
    assert activity["posterior_scope_counts"] == {}
    assert "activity_or_new_table" in activity["flags"]
    assert "no_metric_rows" in activity["flags"]

    q6_count_reason = next(
        row for row in by_reason if row["value"] == "q6_count_above_prior"
    )
    assert q6_count_reason["ready"] == 2
    assert q6_count_reason["prior_stressed"] == 2
    assert q6_count_reason["maps"] == {"2506": 2}
