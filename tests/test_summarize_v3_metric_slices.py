import importlib.util
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "summarize_v3_metric_slices.py"
    spec = importlib.util.spec_from_file_location("summarize_v3_metric_slices", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_summarize_slice_reports_formal_and_q6_metrics() -> None:
    module = _load_module()
    rows = [
        {
            "status": "ready",
            "round": 1,
            "v3_truth_decision_available": True,
            "v3_post_ready": True,
            "v3_post_match_scope": "strict",
            "v3_truth_formal_decision_value": 100,
            "v3_post_formal_decision_value_p50": 90,
            "v3_post_formal_decision_value_p90": 120,
            "v3_truth_q6_formal_decision_value": 40,
            "v3_post_q6_formal_decision_value_p50": 50,
            "v3_post_q6_formal_decision_value_p90": 60,
        },
        {
            "status": "ready",
            "round": 1,
            "v3_truth_decision_available": True,
            "v3_post_ready": True,
            "v3_post_match_scope": "summary_likelihood",
            "v3_truth_formal_decision_value": 200,
            "v3_post_formal_decision_value_p50": 240,
            "v3_post_formal_decision_value_p90": 180,
            "v3_truth_q6_formal_decision_value": 20,
            "v3_post_q6_formal_decision_value_p50": 5,
            "v3_post_q6_formal_decision_value_p90": 30,
        },
        {
            "status": "no_state",
            "round": 1,
            "v3_truth_decision_available": False,
            "v3_post_ready": False,
        },
    ]

    result = module.summarize_slice(rows, "round")

    assert result == [
        {
            "field": "round",
            "value": "1",
            "n": 2,
            "strict": 1,
            "summary_likelihood": 1,
            "q6_projection": 0,
            "formal_p50_mae": 25,
            "formal_p50_bias": 15,
            "formal_p50_below_rate": 0.5,
            "formal_p50_over_rate": 0.5,
            "formal_p90_coverage": 0.5,
            "q6_formal_p50_mae": 12.5,
            "q6_formal_p50_bias": -2.5,
            "q6_formal_p50_below_rate": 0.5,
            "q6_formal_p50_over_rate": 0.5,
            "q6_formal_p90_coverage": 1.0,
        }
    ]
