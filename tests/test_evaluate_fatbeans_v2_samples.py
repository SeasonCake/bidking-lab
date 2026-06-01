from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def _eval_module():
    path = ROOT / "scripts" / "evaluate_fatbeans_v2_samples.py"
    spec = importlib.util.spec_from_file_location("evaluate_fatbeans_v2_samples", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_zero_match_root_classifies_exact_and_public_constraints() -> None:
    module = _eval_module()

    root = module._zero_match_root(
        {
            "v2_matched": 0,
            "layout_conflict": True,
            "layout_conflict_root": "footprint_overlap;footprint_count_relaxed",
            "relaxed_exact_used": True,
            "public_max_item_cells_used": True,
            "bucket_targets": "q6:count=1,cells=16;q4:avg=12000.00",
        }
    )

    assert "layout_conflict" in root
    assert "footprint_overlap" in root
    assert "footprint_count_relaxed" in root
    assert "relaxed_exact_fallback" in root
    assert "public_max_item_cells" in root
    assert "q6_exact_count_cells" in root
    assert "q4_avg_value" in root


def test_q6_plannable_miss_root_splits_rate_and_value_causes() -> None:
    module = _eval_module()

    low_value_root = module._q6_plannable_miss_root(
        {
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_match_rate": 1.0,
            "q6_below_drop_prior": False,
            "v2_q6_count_p90_under_by": 1,
            "v2_q6_cells_p90_under_by": 4,
            "v2_q6_count_p90_under_prior_by": 1.0,
            "v2_q6_cells_p90_under_prior_by": 3.0,
            "v2_q6_space_pressure_p90": 1.25,
            "v2_q6_space_overflow_rate": 0.5,
            "final_q6_count": 2,
            "final_top_item_quality": 6,
            "final_top_item_cells": 12,
            "layout_conflict": True,
            "layout_conflict_root": "footprint_overlap",
            "bucket_targets": "",
        }
    )
    low_rate_root = module._q6_plannable_miss_root(
        {
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_match_rate": 0.0,
            "q6_below_drop_prior": True,
            "final_q6_count": 1,
            "final_top_item_quality": 6,
            "final_top_item_cells": 1,
            "bucket_targets": "q6:count=1,cells=1",
        }
    )

    assert "low_q6_value_distribution" in low_value_root
    assert "q6_count_under" in low_value_root
    assert "q6_cells_under" in low_value_root
    assert "q6_count_below_prior" in low_value_root
    assert "q6_cells_below_prior" in low_value_root
    assert "q6_space_pressure_high" in low_value_root
    assert "q6_space_overflow" in low_value_root
    assert "layout_conflict" in low_value_root
    assert "q6_top_large" in low_value_root
    assert "low_q6_sample_rate" in low_rate_root
    assert "below_drop_prior" in low_rate_root
    assert "q6_exact_count_cells" in low_rate_root


def test_summary_reports_q6_priority_and_root_causes() -> None:
    module = _eval_module()

    rows = [
        {
            "file": "a.json",
            "status": "ok",
            "hero": "ethan",
            "map_id": 2501,
            "map_family": "shipwreck",
            "value_tier": ">=1.2m",
            "final_value": 1_500_000,
            "final_trimmed_tail_value": 600_000,
            "final_q6_count": 1,
            "final_q6_value": 700_000,
            "final_q6_decision_value": 250_000,
            "final_q6_trimmed_tail_value": 450_000,
            "final_top_item_quality": 6,
            "final_top_item_cells": 9,
            "v2_matched": 2,
            "v2_match_rate": 0.2,
            "v2_value_p50_error": -100_000,
            "v2_decision_value_p50_error": -80_000,
            "v2_value_p90_error": -20_000,
            "v2_value_p90_covers_final": False,
            "v2_q6_value_p90": 300_000,
            "v2_q6_decision_value_p90": 300_000,
            "v2_q6_value_p90_error": -400_000,
            "v2_q6_value_p90_under_by": 400_000,
            "v2_q6_decision_value_p90_under_by": 0,
            "v2_q6_count_p90_under_by": 0,
            "v2_q6_cells_p90_under_by": 0,
            "v2_q6_count_p90_under_prior_by": 0,
            "v2_q6_cells_p90_under_prior_by": 0,
            "v2_q6_match_rate": 0.05,
            "v2_q6_prior_expected_value": 800_000,
            "q6_false_low_risk": True,
            "q6_below_drop_prior": True,
            "q6_p90_misses_truth": True,
            "q6_plannable_p90_misses_truth": False,
            "layout_conflict": False,
            "relaxed_exact_used": False,
            "category_target_count": 2,
            "category_exclusion_count": 1,
            "category_action_combo": "100153:时尚;100158:能源",
            "diagnostics": "",
            "presolve_unreachable_exact_buckets": "",
            "public_constraint_key": "none",
            "evidence_profile_key": "tool:category",
            "anchor_band": "3-5",
            "q6_top_size_band": "q6_top_large",
            "q6_miss_root": "low_q6_sample_rate;q6_top_large",
            "evidence_stage": "mid_3_4",
            "information_density_band": "medium",
            "density_value_tier": "medium|>=1.2m",
            "hero_information_density": "ethan|medium",
            "hero_evidence_stage": "ethan|mid_3_4",
            "trusted_footprint_count": 2,
            "footprint_occupied_cells": 10,
            "calibration_eligible": True,
        },
        {
            "file": "b.json",
            "status": "ok",
            "hero": "ethan",
            "map_id": 2501,
            "map_family": "shipwreck",
            "value_tier": "300k-800k",
            "final_value": 500_000,
            "final_trimmed_tail_value": 0,
            "final_q6_count": 0,
            "final_q6_value": 0,
            "final_q6_decision_value": 0,
            "final_q6_trimmed_tail_value": 0,
            "v2_matched": 0,
            "v2_match_rate": 0.0,
            "v2_value_p50_error": 50_000,
            "v2_decision_value_p50_error": 40_000,
            "v2_value_p90_error": 100_000,
            "v2_value_p90_covers_final": True,
            "q6_false_low_risk": False,
            "v2_q6_decision_value_p90": None,
            "v2_q6_count_p90_under_by": 0,
            "v2_q6_cells_p90_under_by": 0,
            "v2_q6_count_p90_under_prior_by": 0,
            "v2_q6_cells_p90_under_prior_by": 0,
            "q6_p90_misses_truth": False,
            "q6_plannable_p90_misses_truth": False,
            "layout_conflict": True,
            "layout_conflict_root": "footprint_overlap;footprint_count_relaxed",
            "relaxed_exact_used": True,
            "bucket_targets": "q4:count=4,cells=12",
            "category_target_count": 1,
            "category_exclusion_count": 0,
            "category_action_combo": "100152:医疗",
            "diagnostics": "category_target_no_pool_match:108:6:33:9",
            "presolve_unreachable_exact_buckets": "q4:count=4,cells=12",
            "zero_match_root": (
                "layout_conflict;footprint_overlap;footprint_count_relaxed;"
                "relaxed_exact_fallback;presolve_unreachable_exact_bucket;"
                "q4_exact_count_cells"
            ),
            "public_constraint_key": "none",
            "evidence_profile_key": "tool:category",
            "anchor_band": "6+",
            "q6_top_size_band": "no_q6",
            "evidence_stage": "early_1_2",
            "information_density_band": "low",
            "density_value_tier": "low|300k-800k",
            "hero_information_density": "ethan|low",
            "hero_evidence_stage": "ethan|early_1_2",
            "trusted_footprint_count": 0,
            "footprint_occupied_cells": 0,
            "calibration_eligible": False,
        },
    ]

    summary = module._summary(rows)

    zero_causes = {row["cause"]: row["n"] for row in summary["zero_match_root_causes"]}
    assert zero_causes["layout_conflict"] == 1
    assert zero_causes["footprint_overlap"] == 1
    assert zero_causes["q4_exact_count_cells"] == 1
    layout_causes = {
        row["cause"]: row["n"]
        for row in summary["layout_conflict_root_causes"]
    }
    assert layout_causes["footprint_count_relaxed"] == 1

    q6_causes = {row["cause"]: row["n"] for row in summary["q6_miss_root_causes"]}
    assert q6_causes["low_q6_sample_rate"] == 1
    assert q6_causes["q6_top_large"] == 1

    priority = summary["q6_calibration_priority"]
    assert priority[0]["group"] == "hero=ethan|map_family=shipwreck"
    assert priority[0]["q6_p90_misses_truth"] == 1
    assert priority[0]["median_q6_under_by"] == 400_000
    assert summary["q6_truth_files"] == 1
    assert summary["q6_plannable_truth_files"] == 1
    assert summary["q6_no_plannable_truth_files"] == 0
    assert summary["q6_no_plannable_p90_positive"] == 0
    assert summary["q6_tail_event_files"] == 1
    assert summary["q6_p90_misses_truth"] == 1
    assert summary["q6_plannable_p90_misses_truth"] == 0
    assert summary["q6_value_p90_coverage"] == 0.0
    assert summary["q6_plannable_value_p90_coverage"] == 1.0
    assert summary["q6_tail_trimmed_value_median"] == 450_000
    assert (
        summary["q6_plannable_risk_groups"]["hero_map_family"][0][
            "q6_plannable_p90_misses_truth"
        ]
        == 0
    )
    assert summary["q6_plannable_calibration_priority"] == []
    assert summary["tail_event_count"] == 1
    assert summary["regular_decision_value_mae"] == 40_000
    assert summary["tail_event_decision_value_mae"] == 80_000
    assert summary["category_evidence"]["target_rows"] == 2
    assert summary["category_evidence"]["exclusion_rows"] == 1
    assert summary["category_evidence"]["target_total"] == 3
    assert summary["category_evidence"]["exclusion_total"] == 1
    assert summary["category_evidence"]["no_pool_match_rows"] == 1
    assert summary["category_evidence"]["action_combo_top"][0] == {
        "combo": "100153:时尚;100158:能源",
        "n": 1,
    }
    assert summary["category_evidence"]["examples"][0]["file"] == "a.json"
    assert (
        summary["category_evidence"]["no_pool_match_examples"][0]["file"]
        == "b.json"
    )
    assert summary["presolve_unreachable_exact_rows"] == 1
    assert summary["presolve_exact_bucket"]["unreachable_rows"] == 1
    assert summary["presolve_exact_bucket"]["zero_match_rows"] == 1
    assert summary["presolve_exact_bucket"]["relaxed_exact_rows"] == 1
    assert (
        summary["presolve_exact_bucket"]["examples"][0][
            "presolve_unreachable_exact_buckets"
        ]
        == "q4:count=4,cells=12"
    )
    assert summary["sample_feasibility"]["calibration_eligible_rows"] == 1
    assert summary["sample_feasibility"]["early_rows"] == 1
    assert summary["sample_feasibility"]["calibration_decision_value_mae"] == 80_000
    assert summary["sample_feasibility"]["calibration_q6_p90_misses_truth"] == 1
    assert summary["sample_feasibility"]["by_evidence_stage"] == {
        "mid_3_4": 1,
        "early_1_2": 1,
    }
    assert summary["sample_feasibility"]["by_information_density"] == {
        "medium": 1,
        "low": 1,
    }
    assert {
        row["information_density_band"]: row["n"]
        for row in summary["groups"]["information_density"]
    } == {"low": 1, "medium": 1}
    assert {
        row["density_value_tier"]: row["n"]
        for row in summary["groups"]["density_value_tier"]
    } == {"low|300k-800k": 1, "medium|>=1.2m": 1}
    assert {
        row["hero_information_density"]: row["n"]
        for row in summary["groups"]["hero_information_density"]
    } == {"ethan|low": 1, "ethan|medium": 1}
    assert (
        summary["q6_plannable_risk_groups"]["information_density"][0][
            "q6_plannable_truth"
        ]
        == 1
    )
    assert (
        summary["q6_plannable_risk_groups"]["hero_map_family"][0][
            "trusted_footprint_median"
        ]
        == 1
    )
    assert (
        summary["q6_plannable_risk_groups"]["hero_map_family"][0][
            "footprint_occupied_cells_median"
        ]
        == 5
    )
    assert summary["groups"]["evidence_profile"][0]["evidence_profile_key"] == (
        "tool:category"
    )

    experiment = module._summary(rows, q6_residual_floor_ratio=0.75)[
        "q6_residual_floor_experiment"
    ]
    assert experiment["eligible_rows"] == 1
    assert experiment["floor_median"] == 600_000
    assert experiment["q6_p90_misses_truth"] == 1
    assert experiment["groups"]["hero_map_family"][0]["group"] == (
        "hero=ethan|map_family=shipwreck"
    )
    assert experiment["groups"]["hero_map_family"][0]["eligible_rows"] == 1
    assert (
        experiment["groups"]["hero_map_family"][0]["q6_p90_misses_before"]
        == 1
    )
    assert (
        experiment["groups"]["hero_map_family"][0]["q6_p90_misses_after"]
        == 1
    )

    experiment = module._summary(rows, q6_residual_floor_ratio=1.0)[
        "q6_residual_floor_experiment"
    ]
    assert experiment["q6_p90_misses_truth"] == 0
    assert experiment["q6_value_p90_coverage"] == 1.0
    assert (
        experiment["groups"]["hero_map_family"][0]["q6_p90_miss_improvement"]
        == 1
    )


def test_q6_count_cell_prior_floor_experiment_is_separate_from_raw_floor() -> None:
    module = _eval_module()
    rows = [
        {
            "status": "ok",
            "file": "q6.json",
            "hero": "aisha",
            "map_family": "shipwreck",
            "q6_top_size_band": "q6_top_large",
            "final_q6_value": 500,
            "final_q6_decision_value": 500,
            "v2_q6_value_p90": 100,
            "v2_q6_decision_value_p90": 100,
            "v2_match_rate": 1.0,
            "q6_p90_misses_truth": True,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
            "v2_q6_cells_p90_under_prior_by": 4.0,
        },
        {
            "status": "ok",
            "file": "no_q6.json",
            "hero": "aisha",
            "map_family": "shipwreck",
            "q6_top_size_band": "no_q6",
            "final_q6_value": 0,
            "final_q6_decision_value": 0,
            "v2_q6_value_p90": 0,
            "v2_q6_decision_value_p90": 0,
            "v2_match_rate": 1.0,
            "q6_p90_misses_truth": False,
            "q6_plannable_p90_misses_truth": False,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
        },
    ]

    experiment = module._summary(rows, q6_residual_floor_ratio=1.0)[
        "q6_count_cell_prior_floor_experiment"
    ]

    assert experiment["eligible_rows"] == 1
    assert experiment["eligible_no_q6_rows"] == 1
    assert experiment["q6_plannable_p90_misses_truth"] == 0
    assert experiment["q6_plannable_value_p90_coverage"] == 1.0
    assert (
        experiment["groups"]["hero_map_family"][0][
            "q6_plannable_miss_improvement"
        ]
        == 1
    )


def test_summary_reports_no_q6_positive_p90_proxy() -> None:
    module = _eval_module()
    rows = [
        {
            "status": "ok",
            "file": "no_q6.json",
            "final_value": 100,
            "final_q6_count": 0,
            "final_q6_decision_value": 0,
            "final_q6_trimmed_tail_value": 0,
            "v2_matched": 10,
            "v2_match_rate": 1.0,
            "v2_value_p50_error": 0,
            "v2_decision_value_p50_error": 0,
            "v2_value_p90_error": 50,
            "v2_value_p90_covers_final": True,
            "v2_q6_decision_value_p90": 200,
            "q6_false_low_risk": False,
            "q6_below_drop_prior": False,
            "q6_p90_misses_truth": False,
            "q6_plannable_p90_misses_truth": False,
            "layout_conflict": False,
            "relaxed_exact_used": False,
            "category_target_count": 0,
            "category_exclusion_count": 0,
            "presolve_unreachable_exact_buckets": "",
        }
    ]

    summary = module._summary(rows)

    assert summary["q6_no_plannable_truth_files"] == 1
    assert summary["q6_no_plannable_p90_positive"] == 1
    assert summary["q6_no_plannable_p90_positive_rate"] == 1.0
    assert summary["q6_no_plannable_p90_positive_median"] == 200


def test_q6_residual_boost_profile_gate_is_narrow() -> None:
    module = _eval_module()

    assert module._q6_residual_boost_for_profile(
        hero="aisha",
        map_family="shipwreck",
        evidence_profile_key="shape+layout",
        requested_boost=3.0,
        gate="shipwreck_profile_v1",
    ) == 3.0
    assert module._q6_residual_boost_for_profile(
        hero="aisha",
        map_family="villa",
        evidence_profile_key="shape+layout",
        requested_boost=3.0,
        gate="shipwreck_profile_v1",
    ) == 1.0
    assert module._q6_residual_boost_for_profile(
        hero="aisha",
        map_family="shipwreck",
        evidence_profile_key="public:random_avg+shape+layout",
        requested_boost=3.0,
        gate="shipwreck_profile_v1",
    ) == 1.0


def test_q6_low_space_residual_floor_experiment_is_narrower_than_prior_floor() -> None:
    module = _eval_module()
    rows = [
        {
            "status": "ok",
            "file": "low_space_q6.json",
            "hero": "aisha",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
            "v2_q6_space_pressure_p90": 0.2,
            "v2_q6_space_overflow_rate": 0.0,
        },
        {
            "status": "ok",
            "file": "high_space_q6.json",
            "hero": "aisha",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
            "v2_q6_space_pressure_p90": 1.2,
            "v2_q6_space_overflow_rate": 0.0,
        },
        {
            "status": "ok",
            "file": "low_space_no_q6.json",
            "hero": "aisha",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 0,
            "v2_q6_decision_value_p90": 0,
            "q6_plannable_p90_misses_truth": False,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
            "v2_q6_space_pressure_p90": 0.1,
            "v2_q6_space_overflow_rate": 0.0,
        },
    ]

    experiment = module._q6_low_space_residual_floor_experiment(
        rows,
        floor_ratio=1.0,
    )

    assert experiment["eligible_rows"] == 1
    assert experiment["eligible_no_q6_rows"] == 1
    assert experiment["q6_plannable_p90_misses_truth"] == 1
    assert experiment["groups"]["hero_map_profile"][0]["net_improvement"] == 0


def test_q6_low_space_residual_gated_floor_keeps_positive_net_profiles() -> None:
    module = _eval_module()
    rows = [
        {
            "hero": "aisha",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
            "v2_q6_space_pressure_p90": 0.2,
            "v2_q6_space_overflow_rate": 0.0,
        },
        {
            "hero": "aisha",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
            "v2_q6_space_pressure_p90": 0.3,
            "v2_q6_space_overflow_rate": 0.0,
        },
        {
            "hero": "aisha",
            "map_family": "villa",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
            "v2_q6_space_pressure_p90": 0.2,
            "v2_q6_space_overflow_rate": 0.0,
        },
        {
            "hero": "aisha",
            "map_family": "villa",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 0,
            "v2_q6_decision_value_p90": 0,
            "q6_plannable_p90_misses_truth": False,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
            "v2_q6_space_pressure_p90": 0.2,
            "v2_q6_space_overflow_rate": 0.0,
        },
    ]

    experiment = module._q6_low_space_residual_gated_floor_experiment(
        rows,
        floor_ratio=1.0,
        min_q6_truth=1,
    )

    assert [row["group"] for row in experiment["gates"]] == [
        "hero=aisha|map_family=shipwreck|evidence_profile_key=shape+layout"
    ]
    assert experiment["eligible_rows"] == 2
    assert experiment["eligible_no_q6_rows"] == 0
    assert experiment["q6_plannable_p90_misses_truth"] == 1


def test_q6_count_cell_prior_gated_floor_prefers_positive_net_groups() -> None:
    module = _eval_module()
    rows = [
        {
            "status": "ok",
            "file": "good_gate_q6.json",
            "hero": "ethan",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
        },
        {
            "status": "ok",
            "file": "bad_gate_q6.json",
            "hero": "aisha",
            "map_family": "villa",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
        },
        {
            "status": "ok",
            "file": "bad_gate_no_q6.json",
            "hero": "aisha",
            "map_family": "villa",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 0,
            "v2_q6_decision_value_p90": 0,
            "q6_plannable_p90_misses_truth": False,
            "v2_q6_prior_expected_value": 600,
            "v2_q6_count_p90_under_prior_by": 1.0,
        },
    ]

    experiment = module._q6_count_cell_prior_gated_floor_experiment(
        rows,
        floor_ratio=1.0,
    )

    assert [row["group"] for row in experiment["gates"]] == [
        "hero=ethan|map_family=shipwreck"
    ]
    assert experiment["eligible_rows"] == 1
    assert experiment["eligible_no_q6_rows"] == 0
    assert experiment["q6_plannable_p90_misses_truth"] == 1

    profile_experiment = module._q6_count_cell_prior_gated_floor_experiment(
        rows,
        floor_ratio=1.0,
        gate_keys=("hero", "map_family", "evidence_profile_key"),
        gate_name="hero_map_family_profile_positive_net",
    )
    assert profile_experiment["gates"][0]["group"] == (
        "hero=ethan|map_family=shipwreck|evidence_profile_key=shape+layout"
    )
    strict_profile_experiment = module._q6_count_cell_prior_gated_floor_experiment(
        rows,
        floor_ratio=1.0,
        gate_keys=("hero", "map_family", "evidence_profile_key"),
        gate_name="hero_map_family_profile_positive_net",
        min_q6_truth=2,
    )
    assert strict_profile_experiment["gates"] == []


def test_q6_actionable_targets_prioritize_shipwreck_profiles() -> None:
    module = _eval_module()
    rows = [
        {
            "status": "ok",
            "hero": "aisha",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "information_density_band": "high",
            "final_q6_decision_value": 500_000,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_decision_value_p90_under_by": 300_000,
            "v2_q6_space_pressure_p90": 0.10,
            "v2_q6_space_overflow_rate": 0.0,
            "final_q6_trimmed_tail_value": 0,
            "v2_matched": 10,
            "layout_conflict": True,
        }
        for _ in range(10)
    ]

    targets = module._q6_actionable_targets(rows)

    assert targets[0]["q6_plannable_truth"] == 10
    assert targets[0]["q6_plannable_misses"] == 10
    assert any(
        target["scope"] == "hero_map_profile"
        and target["recommended_next"] == "shipwreck_shape_residual_sampler"
        for target in targets
    )


def test_q6_space_diagnostics_separates_residual_from_space_pressure() -> None:
    module = _eval_module()
    rows = [
        {
            "hero": "aisha",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 500_000,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_decision_value_p90_under_by": 300_000,
            "v2_q6_space_pressure_p90": 0.25,
            "v2_q6_space_overflow_rate": 0.0,
        },
        {
            "hero": "aisha",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 400_000,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_decision_value_p90_under_by": 200_000,
            "v2_q6_space_pressure_p90": 0.40,
            "v2_q6_space_overflow_rate": 0.0,
        },
        {
            "hero": "ethan",
            "map_family": "villa",
            "evidence_profile_key": "layout",
            "final_q6_decision_value": 300_000,
            "q6_plannable_p90_misses_truth": True,
            "v2_q6_decision_value_p90_under_by": 100_000,
            "v2_q6_space_pressure_p90": 1.20,
            "v2_q6_space_overflow_rate": 0.5,
        },
        {
            "hero": "aisha",
            "map_family": "shipwreck",
            "evidence_profile_key": "shape+layout",
            "final_q6_decision_value": 300_000,
            "q6_plannable_p90_misses_truth": False,
            "v2_q6_space_pressure_p90": 0.30,
            "v2_q6_space_overflow_rate": 0.0,
        },
    ]

    diagnostics = module._q6_space_diagnostics(rows)

    assert diagnostics["q6_plannable_miss_rows"] == 3
    assert diagnostics["low_space_pressure_miss_rows"] == 2
    assert diagnostics["high_space_pressure_miss_rows"] == 1
    assert diagnostics["recommended_next"] == "residual_q6_count_cell_sampler"
    assert diagnostics["groups"]["hero_map_profile"][0]["group"] == (
        "hero=aisha|map_family=shipwreck|evidence_profile_key=shape+layout"
    )
    assert diagnostics["groups"]["hero_map_profile"][0]["recommended_next"] == (
        "residual_q6_count_cell_sampler"
    )


def test_expand_cli_paths_supports_globs(tmp_path: Path) -> None:
    module = _eval_module()
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    first.write_text("[]", encoding="utf-8")
    second.write_text("[]", encoding="utf-8")

    assert module._expand_cli_paths([str(tmp_path / "*.json")]) == [
        first,
        second,
    ]


def test_evidence_stage_marks_early_rounds_separately() -> None:
    module = _eval_module()

    assert module._evidence_stage(1) == "early_1_2"
    assert module._evidence_stage(2) == "early_1_2"
    assert module._evidence_stage(3) == "mid_3_4"
    assert module._evidence_stage(5) == "full_5"


def test_information_density_combines_round_and_evidence_counts() -> None:
    module = _eval_module()

    score = module._information_density_score(
        {
            "capture_round": 4,
            "anchor_count": 3,
            "shape_target_count": 1,
            "category_target_count": 2,
            "category_exclusion_count": 1,
            "trusted_footprint_count": 5,
            "public_constraint_key": "max_quality",
        }
    )

    assert score == 29
    assert module._information_density_band(score) == "medium"
    assert module._information_density_band(17) == "low"
    assert module._information_density_band(18) == "medium"
    assert module._information_density_band(34) == "high"


def test_evidence_profile_key_summarizes_public_tool_and_layout() -> None:
    module = _eval_module()

    assert module._evidence_profile_key(
        {
            "public_constraint_key": "max_quality",
            "random_sample_avg_values": "n=6:avg=96897.66",
            "category_action_count": 2,
            "shape_target_count": 1,
            "trusted_footprint_count": 3,
        }
    ) == "public:max_quality+public:random_avg+tool:category+shape+layout"
    assert module._evidence_profile_key({}) == "basic"


def test_capture_round_uses_cumulative_actions_at_settlement() -> None:
    module = _eval_module()
    events = SimpleNamespace(
        states=(
            SimpleNamespace(round_no=1, action_results=(1,)),
            SimpleNamespace(round_no=2, action_results=(1, 2)),
            SimpleNamespace(round_no=3, action_results=(1, 2, 3, 4)),
        ),
    )

    assert module._capture_round(events) == 4


def test_category_action_combo_uses_first_seen_order() -> None:
    module = _eval_module()
    events = SimpleNamespace(
        states=(
            SimpleNamespace(
                action_results=(
                    SimpleNamespace(action_id=100153),
                    SimpleNamespace(action_id=100158),
                ),
            ),
            SimpleNamespace(
                action_results=(
                    SimpleNamespace(action_id=100153),
                    SimpleNamespace(action_id=100151),
                    SimpleNamespace(action_id=100129),
                ),
            ),
        ),
    )

    assert (
        module._category_action_combo(events)
        == "100153:时尚;100158:能源;100151:家具"
    )


def test_presolve_unreachable_exact_bucket_formatter() -> None:
    module = _eval_module()
    problem = SimpleNamespace(
        map_id=2401,
        bucket_targets={
            6: SimpleNamespace(count_exact=1, total_cells_exact=16),
            5: SimpleNamespace(count_exact=2, total_cells_exact=None),
        },
    )
    payload = {
        "maps": {
            "2401": {
                "6": {
                    "1": [12],
                },
            },
        },
    }

    assert module._format_presolve_unreachable_exact_buckets(
        problem,
        payload,
    ) == "q6:count=1,cells=16"
