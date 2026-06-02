from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "scripts" / "compare_q6_residual_boost.py"
    spec = importlib.util.spec_from_file_location("compare_q6_residual_boost", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_comparison_row_keeps_core_q6_metrics() -> None:
    module = _module()

    row = module._comparison_row(
        "profile_b5",
        5.0,
        "shipwreck_profile_v1",
        {
            "files": 10,
            "ok": 9,
            "valued": 8,
            "zero_match": 1,
            "decision_value_mae": 123,
            "value_p90_coverage": 0.5,
            "q6_plannable_value_p90_coverage": 0.6,
            "q6_plannable_p90_misses_truth": 4,
            "q6_no_plannable_truth_files": 3,
            "q6_no_plannable_p90_positive_rate": 0.25,
            "q6_no_plannable_p90_positive_median": 200,
            "case_breakdown": {
                "normal_case": {
                    "rows": 6,
                    "decision_value_mae": 111,
                    "value_p90_coverage": 0.7,
                    "q6_plannable_coverage": 0.8,
                    "q6_plannable_miss_rows": 2,
                },
                "early_diagnostic": {
                    "rows": 1,
                    "cells_p50_mae": 30,
                },
                "tail_event": {
                    "rows": 2,
                    "decision_value_mae": 333,
                    "q6_plannable_coverage": 0.5,
                },
                "hidden_case": {
                    "rows": 3,
                    "decision_value_mae": 555,
                    "value_p90_coverage": 0.4,
                    "q6_plannable_coverage": 0.25,
                    "q6_plannable_miss_rows": 6,
                },
                "no_q6_control": {
                    "rows": 3,
                    "no_q6_positive_rate": 0.25,
                    "no_q6_positive_median": 200,
                },
                "zero_q6_proven": {
                    "rows": 2,
                    "no_q6_positive_rate": 0.0,
                    "no_q6_positive_median": None,
                },
                "high_info_value_miss": {
                    "rows": 4,
                    "decision_value_mae": 444,
                },
                "high_info_q6_miss": {
                    "rows": 3,
                    "q6_plannable_miss_rows": 3,
                },
            },
            "q6_residual_boost_experiment": {
                "active_rows": 5,
                "active_no_q6_rows": 1,
                "active_no_q6_p90_positive_rate": 1.0,
            },
            "q6_residual_prior_floor_sampler_experiment": {
                "active_rows": 0,
                "active_no_q6_rows": 0,
                "active_no_q6_p90_positive_rate": None,
            },
        },
    )

    assert row["label"] == "profile_b5"
    assert row["prior_floor_ratio"] == 0.0
    assert row["q6_plannable_coverage"] == 0.6
    assert row["normal_case_decision_value_mae"] == 111
    assert row["normal_case_q6_plannable_coverage"] == 0.8
    assert row["tail_event_decision_value_mae"] == 333
    assert row["hidden_case_decision_value_mae"] == 555
    assert row["hidden_case_q6_plannable_misses"] == 6
    assert row["no_q6_control_positive_rate"] == 0.25
    assert row["zero_q6_proven_rows"] == 2
    assert row["zero_q6_proven_positive_rate"] == 0.0
    assert row["high_info_value_miss_rows"] == 4
    assert row["high_info_q6_miss_under_count"] == 3
    assert row["active_rows"] == 5
    assert row["active_no_q6_rows"] == 1
    assert row["floor_active_rows"] == 0


def test_with_baseline_deltas_adds_directional_comparison() -> None:
    module = _module()

    rows = module._with_baseline_deltas(
        [
            {
                "label": "baseline",
                "q6_plannable_coverage": 0.4,
                "q6_plannable_misses": 10,
                "decision_value_mae": 500,
                "q6_no_plannable_p90_positive_rate": 0.2,
                "q6_no_plannable_p90_positive_median": 100,
                "normal_case_decision_value_mae": 300,
                "normal_case_q6_plannable_coverage": 0.5,
                "normal_case_q6_plannable_misses": 5,
                "tail_event_decision_value_mae": 700,
                "hidden_case_decision_value_mae": 900,
                "hidden_case_q6_plannable_coverage": 0.4,
                "hidden_case_q6_plannable_misses": 6,
                "no_q6_control_positive_rate": 0.2,
                "no_q6_control_positive_median": 100,
                "zero_q6_proven_positive_rate": 0.0,
                "zero_q6_proven_positive_median": 0,
                "high_info_value_miss_rows": 8,
                "high_info_q6_miss_rows": 6,
            },
            {
                "label": "profile_b5",
                "q6_plannable_coverage": 0.6,
                "q6_plannable_misses": 7,
                "decision_value_mae": 450,
                "q6_no_plannable_p90_positive_rate": 0.25,
                "q6_no_plannable_p90_positive_median": 150,
                "normal_case_decision_value_mae": 250,
                "normal_case_q6_plannable_coverage": 0.7,
                "normal_case_q6_plannable_misses": 3,
                "tail_event_decision_value_mae": 650,
                "hidden_case_decision_value_mae": 800,
                "hidden_case_q6_plannable_coverage": 0.6,
                "hidden_case_q6_plannable_misses": 4,
                "no_q6_control_positive_rate": 0.35,
                "no_q6_control_positive_median": 220,
                "zero_q6_proven_positive_rate": 0.1,
                "zero_q6_proven_positive_median": 50,
                "high_info_value_miss_rows": 5,
                "high_info_q6_miss_rows": 4,
            },
        ]
    )

    assert rows[1]["delta_q6_plannable_coverage"] == 0.2
    assert rows[1]["delta_q6_plannable_misses"] == -3
    assert rows[1]["delta_decision_value_mae"] == -50
    assert rows[1]["delta_normal_case_decision_value_mae"] == -50
    assert rows[1]["delta_normal_case_q6_plannable_coverage"] == 0.2
    assert rows[1]["delta_normal_case_q6_plannable_misses"] == -2
    assert rows[1]["delta_tail_event_decision_value_mae"] == -50
    assert rows[1]["delta_hidden_case_decision_value_mae"] == -100
    assert rows[1]["delta_hidden_case_q6_plannable_coverage"] == 0.2
    assert rows[1]["delta_hidden_case_q6_plannable_misses"] == -2
    assert rows[1]["delta_no_q6_control_positive_rate"] == 0.15
    assert rows[1]["delta_zero_q6_proven_positive_rate"] == 0.1
    assert rows[1]["delta_high_info_value_miss_rows"] == -3
    assert rows[1]["delta_high_info_q6_miss_rows"] == -2
    assert rows[1]["delta_no_q6_control_positive_median"] == 120
    assert rows[1]["delta_no_q6_positive_rate"] == 0.05
    assert rows[1]["delta_no_q6_positive_median"] == 50


def test_selected_configs_preserves_default_order() -> None:
    module = _module()

    rows = module._selected_configs(["profile_b5", "baseline"])

    assert [row[0] for row in rows] == ["baseline", "profile_b5"]


def test_selected_configs_can_include_extra_floor_experiment() -> None:
    module = _module()

    rows = module._selected_configs(["baseline", "aisha_deep_floor1"])

    assert [row[0] for row in rows] == ["baseline", "aisha_deep_floor1"]
    assert rows[1][3:] == (1.0, "aisha_shipwreck_deep_v1")


def test_selected_configs_can_include_hidden_floor_experiment() -> None:
    module = _module()

    rows = module._selected_configs(["baseline", "aisha_hidden_floor1"])

    assert [row[0] for row in rows] == ["baseline", "aisha_hidden_floor1"]
    assert rows[1][3:] == (1.0, "aisha_hidden_v1")


def test_selected_configs_can_include_deep_hidden_floor_experiment() -> None:
    module = _module()

    rows = module._selected_configs(["baseline", "aisha_deep_hidden_floor1"])

    assert [row[0] for row in rows] == ["baseline", "aisha_deep_hidden_floor1"]
    assert rows[1][3:] == (1.0, "aisha_deep_or_hidden_v1")


def test_selected_configs_can_include_hidden_floor15_experiment() -> None:
    module = _module()

    rows = module._selected_configs(["baseline", "aisha_hidden_floor15"])

    assert [row[0] for row in rows] == ["baseline", "aisha_hidden_floor15"]
    assert rows[1][3:] == (1.5, "aisha_hidden_v1")


def test_selected_configs_can_include_aisha_villa_floor_experiments() -> None:
    module = _module()

    rows = module._selected_configs(
        ["baseline", "aisha_villa_floor05", "aisha_villa_floor075"]
    )

    assert [row[0] for row in rows] == [
        "baseline",
        "aisha_villa_floor05",
        "aisha_villa_floor075",
    ]
    assert rows[1][3:] == (0.5, "aisha_villa_shape_layout_v1")
    assert rows[2][3:] == (0.75, "aisha_villa_shape_layout_v1")


def test_paired_q6_delta_summary_counts_help_and_new_false_positive() -> None:
    module = _module()

    baseline = [
        {
            "file": "helped.json",
            "status": "ok",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
        },
        {
            "file": "newly_missed.json",
            "status": "ok",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 600,
        },
        {
            "file": "no_q6.json",
            "status": "ok",
            "final_q6_decision_value": 0,
            "v2_q6_decision_value_p90": 0,
        },
    ]
    candidate = [
        {
            "file": "helped.json",
            "status": "ok",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 700,
        },
        {
            "file": "newly_missed.json",
            "status": "ok",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 400,
        },
        {
            "file": "no_q6.json",
            "status": "ok",
            "final_q6_decision_value": 0,
            "v2_q6_decision_value_p90": 200,
        },
    ]

    summary = module._paired_q6_delta_summary(baseline, candidate)

    assert summary["paired_rows"] == 3
    assert summary["paired_q6_truth_rows"] == 2
    assert summary["paired_q6_helped_rows"] == 1
    assert summary["paired_q6_newly_missed_rows"] == 1
    assert summary["paired_no_q6_new_positive_rows"] == 1
    assert summary["paired_no_q6_new_positive_rate"] == 1.0


def test_paired_baseline_deltas_adds_normal_case_q6_summary() -> None:
    module = _module()
    base_common = {
        "status": "ok",
        "calibration_eligible": True,
        "evidence_stage": "mid_3_4",
        "v2_matched": True,
        "v2_decision_value_p50_error": 0,
        "final_trimmed_tail_value": 0,
    }
    baseline_rows = [
        {
            **base_common,
            "file": "normal_helped.json",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
        },
        {
            **base_common,
            "file": "early_helped.json",
            "evidence_stage": "early_1_2",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
        },
        {
            **base_common,
            "file": "hidden_helped.json",
            "map_family": "hidden",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 100,
        },
    ]
    candidate_rows = [
        {
            **base_common,
            "file": "normal_helped.json",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 700,
        },
        {
            **base_common,
            "file": "early_helped.json",
            "evidence_stage": "early_1_2",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 700,
        },
        {
            **base_common,
            "file": "hidden_helped.json",
            "map_family": "hidden",
            "final_q6_decision_value": 500,
            "v2_q6_decision_value_p90": 700,
        },
    ]

    rows = module._with_paired_baseline_deltas(
        [{"label": "baseline"}, {"label": "profile_b5"}],
        {
            "baseline": baseline_rows,
            "profile_b5": candidate_rows,
        },
    )

    assert rows[1]["paired_q6_helped_rows"] == 3
    assert rows[1]["paired_normal_rows"] == 1
    assert rows[1]["paired_normal_q6_helped_rows"] == 1
    assert rows[1]["paired_hidden_rows"] == 1
    assert rows[1]["paired_hidden_q6_helped_rows"] == 1
