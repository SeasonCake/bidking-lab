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
            "q6_residual_boost_experiment": {
                "active_rows": 5,
                "active_no_q6_rows": 1,
                "active_no_q6_p90_positive_rate": 1.0,
            },
        },
    )

    assert row["label"] == "profile_b5"
    assert row["q6_plannable_coverage"] == 0.6
    assert row["active_rows"] == 5
    assert row["active_no_q6_rows"] == 1


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
            },
            {
                "label": "profile_b5",
                "q6_plannable_coverage": 0.6,
                "q6_plannable_misses": 7,
                "decision_value_mae": 450,
                "q6_no_plannable_p90_positive_rate": 0.25,
                "q6_no_plannable_p90_positive_median": 150,
            },
        ]
    )

    assert rows[1]["delta_q6_plannable_coverage"] == 0.2
    assert rows[1]["delta_q6_plannable_misses"] == -3
    assert rows[1]["delta_decision_value_mae"] == -50
    assert rows[1]["delta_no_q6_positive_rate"] == 0.05
    assert rows[1]["delta_no_q6_positive_median"] == 50
