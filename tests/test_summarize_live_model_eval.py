from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _summary_module():
    path = ROOT / "scripts" / "summarize_live_model_eval.py"
    spec = importlib.util.spec_from_file_location("summarize_live_model_eval", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_summarize_dedupes_latest_row_by_file() -> None:
    module = _summary_module()

    summary = module.summarize(
        [
            {
                "ts": 1,
                "file": "a.json",
                "final_value": 100,
                "decision_value_p50_error": -90,
            },
            {
                "ts": 2,
                "file": "a.json",
                "final_value": 100,
                "decision_value_p50_error": -10,
            },
        ]
    )

    assert summary["raw_rows"] == 2
    assert summary["rows"] == 1
    assert summary["deduped_rows"] == 1
    assert summary["decision_value_mae"] == 10


def test_summarize_reports_collection_readiness_gaps() -> None:
    module = _summary_module()

    summary = module.summarize(
        [
            {
                "ts": 1,
                "file": "a.json",
                "hero": "aisha",
                "map_id": 2401,
                "final_value": 100,
                "final_cells": 10,
                "final_q6_value": 0,
                "decision_value_p50": 120,
            },
            {
                "ts": 2,
                "file": "b.json",
                "hero": "ethan",
                "map_id": 2501,
                "final_value": 200,
                "final_cells": 12,
                "final_q6_value": 80,
                "decision_value_p50": 180,
            },
            {
                "ts": 3,
                "file": "c.json",
                "map_id": 2402,
                "final_value": 300,
                "final_cells": 14,
            },
        ],
        target_per_hero_family=2,
    )

    readiness = summary["collection_readiness"]
    assert readiness["ready"] is False
    assert readiness["total_needed"] == 6
    assert summary["log_quality"]["missing_hero"] == 1
    assert summary["log_quality"]["missing_q6_truth_fields"] == 1
    assert any(
        row["hero"] == "aisha"
        and row["map_family"] == "villa"
        and row["n"] == 1
        and row["needed"] == 1
        for row in readiness["groups"]
    )
