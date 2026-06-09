from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))

from ahmad_ref_engine import _avg_grid_options, extract_evidence, run_reference_engine  # noqa: E402


def _snapshot(
    *,
    hero: str = "ahmed",
    map_id: int = 2402,
    structured_ref_inputs: dict | None = None,
    public_info: dict | None = None,
    public_rows: list[dict] | None = None,
) -> dict:
    return {
        "ui_contract": {
            "context": {
                "hero": hero,
                "map_id": map_id,
                "phase": "bidding",
            },
            "constraints": {
                "public_info": public_info or {},
            },
        },
        "structured_ref_inputs": structured_ref_inputs or {"total_count": 34},
        "public_info_rows": public_rows or [],
    }


def test_ref_engine_uses_public_quality_reveal_as_min_counts() -> None:
    evidence = extract_evidence(
        _snapshot(
            public_rows=[
                {
                    "info_id": 200028,
                    "revealed_items_detail": [
                        {"runtime_id": 1, "quality": 6},
                        {"runtime_id": 2, "quality": 6},
                        {"runtime_id": 3, "quality": 4},
                        {"runtime_id": 4, "quality": 1},
                        {"runtime_id": 4, "quality": 1},
                    ],
                }
            ],
        )
    )

    assert evidence.min_counts["q6"] == 2
    assert evidence.min_counts["q4"] == 1
    assert evidence.min_counts["q1"] == 1
    assert "public_quality_reveal_min_counts" in evidence.source_notes


def test_ref_engine_random_avg_value_soft_floor_raises_low_prior() -> None:
    base = {
        "ui_contract": {
            "context": {"hero": "ahmed", "map_id": 2402, "phase": "bidding"},
        },
        "structured_ref_inputs": {"total_count": 5},
    }
    with_random_avg = {
        "ui_contract": {
            "context": {"hero": "ahmed", "map_id": 2402, "phase": "bidding"},
            "constraints": {
                "public_info": {
                    "public_numeric_facts": [
                        {
                            "semantic": "random_3_avg_value",
                            "kind": "random_avg_value",
                            "sample_count": 3,
                            "value": 120_000,
                        }
                    ],
                },
            },
        },
        "structured_ref_inputs": {"total_count": 5},
    }

    base_result = run_reference_engine(base, max_combos=60_000).as_dict()
    floor_result = run_reference_engine(with_random_avg, max_combos=60_000).as_dict()

    assert floor_result["balanced"] > base_result["balanced"]
    assert floor_result["red_count_range"][1] >= base_result["red_count_range"][1]
    assert "public_random_avg_value_floor_3:360000" in floor_result["notes"]
    assert "random_value_floor_soft_weight:360000" in floor_result["notes"]


def test_ref_engine_victor_q4_q5_q6_count_sum_and_zero_gold_avg() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="victor",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "total_cells": 34,
                "avg_cells": {"q4": 1.8, "q5": 0},
                "count_sums": {"q4q5q6": 6},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    evidence = result["evidence"]
    ranges = result["quality_count_ranges"]

    assert result["status"] == "ok"
    assert evidence["count_sums"] == {"q4q5q6": 6}
    assert evidence["fixed_counts"]["q5"] == 0
    assert "zero_avg_cells_q5_count_zero" in result["notes"]
    assert ranges["q5"] == [0, 0, 0]
    assert ranges["q4"][2] <= 6
    assert result["red_count_range"][2] <= 6


def test_ref_engine_avg_cells_map_to_integer_grid_options() -> None:
    assert _avg_grid_options(4, 1.8) == [7]
    assert _avg_grid_options(5, 1.8) == [9]
    assert _avg_grid_options(6, 1.8) == [11]
    assert _avg_grid_options(0, 0) == [0]
    assert _avg_grid_options(1, 0) == []


def test_ref_engine_legacy_victor_q4_q5_count_sum_still_supported() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="victor",
            structured_ref_inputs={
                "total_count": 21,
                "count_sums": {"q4q5": 6},
            },
        )
    )

    assert evidence.count_sums == {"q4q5": 6}
