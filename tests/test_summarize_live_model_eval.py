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
                "raw_minus_decision_p90": 0,
                "layout_conflict": False,
                "layout_conflict_root": "",
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
                "q6_below_drop_prior": True,
                "raw_minus_decision_p90": 300_000,
                "layout_conflict": True,
                "posterior_diagnostics": (
                    "footprint_overlap_cells:2;footprint_count_relaxed:3->1"
                ),
            },
            {
                "ts": 3,
                "file": "c.json",
                "map_id": 2402,
                "final_value": 300,
                "final_cells": 14,
                "raw_minus_decision_p90": 900_000,
                "layout_conflict": False,
                "layout_conflict_root": "",
            },
        ],
        target_per_hero_family=2,
        hidden_target_per_hero=1,
    )

    readiness = summary["collection_readiness"]
    assert readiness["ready"] is False
    assert readiness["total_needed"] == 8
    assert readiness["hidden_target_per_hero"] == 1
    assert summary["next_sampling_targets"][0] == {
        "hero": "aisha",
        "map_family": "hidden",
        "needed": 1,
        "reason": "hidden_cold_start",
    }
    assert summary["log_quality"]["missing_hero"] == 1
    assert summary["log_quality"]["missing_q6_truth_fields"] == 1
    assert summary["q6_below_drop_prior_count"] == 1
    assert summary["layout_conflict_count"] == 1
    assert summary["layout_conflict_root_causes"][0]["cause"] == "footprint_overlap"
    assert summary["raw_ceiling_gap_median"] == 300_000
    assert summary["raw_ceiling_gap_250k_count"] == 2
    assert summary["raw_ceiling_gap_700k_count"] == 1
    assert any(
        row["hero"] == "aisha"
        and row["map_family"] == "villa"
        and row["n"] == 1
        and row["needed"] == 1
        for row in readiness["groups"]
    )
    assert any(
        row["map_family"] == "villa"
        and row["raw_ceiling_gap_median"] == 450_000
        and row["layout_overlap_rate"] == 0.0
        for row in summary["groups"]["map_family"]
    )
    assert any(
        row["hero"] == "ethan"
        and row["layout_overlap_rate"] == 1.0
        for row in summary["groups"]["hero"]
    )
    assert any(
        row["hero"] == "ethan"
        and row["map_family"] == "hidden"
        and row["n"] == 0
        and row["needed"] == 1
        for row in readiness["priority_needs"]
    )


def test_map_family_groups_hidden_and_late_map_prefixes() -> None:
    module = _summary_module()

    summary = module.summarize(
        [
            {"file": "a.json", "hero": "aisha", "map_id": 2601, "final_value": 1},
            {"file": "b.json", "hero": "aisha", "map_id": 3401, "final_value": 1},
            {"file": "c.json", "hero": "aisha", "map_id": 4510, "final_value": 1},
        ]
    )

    groups = {
        row["map_family"]: row["n"]
        for row in summary["groups"]["map_family"]
    }
    assert groups["hidden"] == 1
    assert groups["villa"] == 1
    assert groups["shipwreck"] == 1
