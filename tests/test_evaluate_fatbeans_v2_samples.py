from __future__ import annotations

import importlib.util
from pathlib import Path


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
            "final_top_item_quality": 6,
            "final_top_item_cells": 9,
            "v2_matched": 2,
            "v2_match_rate": 0.2,
            "v2_value_p50_error": -100_000,
            "v2_decision_value_p50_error": -80_000,
            "v2_value_p90_error": -20_000,
            "v2_value_p90_covers_final": False,
            "v2_q6_value_p90": 300_000,
            "v2_q6_value_p90_error": -400_000,
            "v2_q6_value_p90_under_by": 400_000,
            "v2_q6_match_rate": 0.05,
            "v2_q6_prior_expected_value": 800_000,
            "q6_false_low_risk": True,
            "q6_below_drop_prior": True,
            "q6_p90_misses_truth": True,
            "layout_conflict": False,
            "relaxed_exact_used": False,
            "public_constraint_key": "none",
            "anchor_band": "3-5",
            "q6_top_size_band": "q6_top_large",
            "q6_miss_root": "low_q6_sample_rate;q6_top_large",
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
            "v2_matched": 0,
            "v2_match_rate": 0.0,
            "v2_value_p50_error": 50_000,
            "v2_decision_value_p50_error": 40_000,
            "v2_value_p90_error": 100_000,
            "v2_value_p90_covers_final": True,
            "q6_false_low_risk": False,
            "q6_p90_misses_truth": False,
            "layout_conflict": True,
            "layout_conflict_root": "footprint_overlap;footprint_count_relaxed",
            "relaxed_exact_used": True,
            "bucket_targets": "q4:count=4,cells=12",
            "zero_match_root": (
                "layout_conflict;footprint_overlap;footprint_count_relaxed;"
                "relaxed_exact_fallback;q4_exact_count_cells"
            ),
            "public_constraint_key": "none",
            "anchor_band": "6+",
            "q6_top_size_band": "no_q6",
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
    assert summary["tail_event_count"] == 1
    assert summary["regular_decision_value_mae"] == 40_000
    assert summary["tail_event_decision_value_mae"] == 80_000

    experiment = module._summary(rows, q6_residual_floor_ratio=0.75)[
        "q6_residual_floor_experiment"
    ]
    assert experiment["eligible_rows"] == 1
    assert experiment["floor_median"] == 600_000
    assert experiment["q6_p90_misses_truth"] == 1

    experiment = module._summary(rows, q6_residual_floor_ratio=1.0)[
        "q6_residual_floor_experiment"
    ]
    assert experiment["q6_p90_misses_truth"] == 0
    assert experiment["q6_value_p90_coverage"] == 1.0
