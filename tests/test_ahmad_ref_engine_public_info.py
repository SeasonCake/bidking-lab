from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
FATBEANS_SAMPLE_DIR = ROOT / "data" / "samples" / "fatbeans"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))

from ahmad_ref_engine import (  # noqa: E402
    AISHA_LAYOUT_FOOTROOM_CAP_NOTE,
    AISHA_LAYOUT_FOOTROOM_MULT_NOTE,
    AISHA_LAYOUT_FOOTROOM_NOTE,
    AISHA_LAYOUT_FOOTROOM_SKIP_NOTE,
    AISHA_LAYOUT_FOOTROOM_SPARSE_NOTE,
    AISHA_LAYOUT_GRID_HINT_NOTE,
    PINNED_QUALITY_CELLS_SPARSE_PRIOR_NOTE,
    RESIDUAL_AVG_CELLS_NOTE,
    TOTAL_GRID_FROM_HIGH_TIER_CELLS_NOTE,
    _avg_count_from_cells,
    _avg_grid_options,
    _fit_grids_to_total_target,
    can_compose_grid_total,
    extract_evidence,
    run_reference_engine,
)

CAPTURE_AVG_CELL_FIXTURES = [
    pytest.param(
        2.909090995788574,
        11,
        32,
        "2.90",
        "fatbeans_valid_aisha_2401_1rounds_2401_1367517774693221_0001.json public_info 200013",
        id="capture_q4_2p90_ratio_11x32",
    ),
    pytest.param(
        2.4285714626312256,
        7,
        17,
        "2.42",
        "recordings/data6/data/logs/live/latest_snapshot.json bucket.q3.avg_cells",
        id="capture_q3_2p42_ratio_7x17",
    ),
    pytest.param(
        2.09,
        11,
        23,
        "2.09",
        "display reading when packet stores rounded 2.09 (2.09×11→23)",
        id="display_q5_2p09_literal_11x23",
    ),
    pytest.param(
        23 / 11,
        11,
        23,
        "2.09",
        "exact ratio float 23/11 from detailed packet capture",
        id="capture_ratio_23_over_11",
    ),
    pytest.param(
        3.43,
        16,
        55,
        "3.43",
        "display reading 3.43 (3.43×16→55, shipwreck screenshot scenario)",
        id="display_q4_3p43_literal_16x55",
    ),
    pytest.param(
        55 / 16,
        16,
        55,
        "3.43",
        "exact ratio float 55/16 from detailed packet capture",
        id="capture_ratio_55_over_16",
    ),
]

FATBEANS_Q4_290_SAMPLE = (
    FATBEANS_SAMPLE_DIR
    / "fatbeans_valid_aisha_2401_1rounds_2401_1367517774693221_0001.json"
)


def _snapshot(
    *,
    hero: str = "ahmed",
    map_id: int = 2402,
    phase: str = "bidding",
    structured_ref_inputs: dict | None = None,
    public_info: dict | None = None,
    public_rows: list[dict] | None = None,
) -> dict:
    return {
        "ui_contract": {
            "context": {
                "hero": hero,
                "map_id": map_id,
                "phase": phase,
            },
            "constraints": {
                "public_info": public_info or {},
            },
        },
        "structured_ref_inputs": (
            {"total_count": 34} if structured_ref_inputs is None else structured_ref_inputs
        ),
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


def test_ref_engine_public_red_reveal_min_count_constrains_enumeration() -> None:
    result = run_reference_engine(
        _snapshot(
            public_rows=[
                {
                    "info_id": 200028,
                    "revealed_items_detail": [
                        {"runtime_id": 1, "quality": 6},
                        {"runtime_id": 2, "quality": 6},
                        {"runtime_id": 2, "quality": 6},
                    ],
                }
            ],
        ),
        max_combos=60000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["evidence"]["min_counts"]["q6"] == 2
    assert result["quality_count_ranges"]["q6"][0] >= 2
    assert "public_quality_reveal_min_counts" in result["notes"]


def test_ref_engine_public_red_reveal_value_and_cells_are_floors() -> None:
    result = run_reference_engine(
        _snapshot(
            structured_ref_inputs={
                "total_count": 48,
                "fixed_counts": {"q1": 9, "q3": 15, "q4": 17, "q5": 5},
                "quality_cells": {"q1": 15, "q3": 49, "q4": 48, "q5": 24},
                "avg_cells": {
                    "q3": 49 / 15,
                    "q4": 48 / 17,
                    "q5": 24 / 5,
                },
            },
            public_rows=[
                {
                    "info_id": 200023,
                    "revealed_items_detail": [
                        {
                            "runtime_id": 1425860479021732,
                            "quality": 6,
                            "value": 452800,
                            "shape_code": 53,
                            "cells": 15,
                        }
                    ],
                }
            ],
        ),
        max_combos=60000,
    ).as_dict()

    assert result["status"] == "ok"
    assert result["evidence"]["fixed_counts"]["q6"] == 2
    assert result["evidence"]["quality_cell_floors"]["q6"] == 15.0
    assert result["evidence"]["quality_value_floors"]["q6"] == 452800.0
    assert min(result["red_cells_range"]) >= 15
    assert min(result["red_value_range"]) >= 452800
    assert "public_quality_reveal_q6_cell_floor" in result["notes"]
    assert "public_quality_reveal_q6_value_floor" in result["notes"]


def test_ref_engine_partial_known_red_value_includes_unknown_estimate() -> None:
    result = run_reference_engine(
        _snapshot(
            structured_ref_inputs={
                "total_count": 50,
                "fixed_counts": {"q1": 10, "q3": 24, "q4": 10, "q5": 4, "q6": 2},
                "quality_cells": {"q1": 15, "q3": 49, "q4": 48, "q5": 24},
                "avg_cells": {
                    "q3": 49 / 24,
                    "q4": 48 / 10,
                    "q5": 24 / 4,
                },
            },
            public_rows=[
                {
                    "info_id": 200023,
                    "revealed_items_detail": [
                        {
                            "runtime_id": 1425860479021733,
                            "quality": 6,
                            "value": 390000,
                            "shape_code": 11,
                            "cells": 1,
                        }
                    ],
                }
            ],
        ),
        max_combos=60000,
    ).as_dict()

    assert result["status"] == "ok"
    assert result["evidence"]["quality_value_floors"]["q6"] == 390000.0
    assert result["evidence"]["quality_value_floor_item_counts"]["q6"] == 1
    rv10, rv50, rv90 = result["red_value_range"]
    assert rv10 is not None and rv50 is not None and rv90 is not None
    assert rv10 > 390000
    assert rv50 > 390000
    assert rv10 >= 550000  # 390k known + at least one default red item floor
    assert rv10 <= rv50 <= rv90
    assert min(result["red_value_range"]) >= 390000


def test_ref_engine_partial_known_red_data6_style_above_known_not_flat() -> None:
    """EXECUTION_NOTES §43 data6: one 452800/15-cell red, q6=2; settlement q6≈520900."""
    result = run_reference_engine(
        _snapshot(
            map_id=2309,
            structured_ref_inputs={
                "total_count": 48,
                "fixed_counts": {"q1": 9, "q3": 15, "q4": 17, "q5": 5},
                "quality_cells": {"q1": 15, "q3": 49, "q4": 48, "q5": 24},
                "avg_cells": {
                    "q3": 49 / 15,
                    "q4": 48 / 17,
                    "q5": 24 / 5,
                },
            },
            public_rows=[
                {
                    "info_id": 200023,
                    "revealed_items_detail": [
                        {
                            "runtime_id": 1425860479021732,
                            "quality": 6,
                            "value": 452800,
                            "shape_code": 53,
                            "cells": 15,
                        }
                    ],
                }
            ],
        ),
        max_combos=60000,
    ).as_dict()

    rv10, rv50, rv90 = result["red_value_range"]
    assert rv10 is not None and rv50 is not None and rv90 is not None
    assert rv10 > 452800
    assert rv50 > 452800
    assert rv10 >= 612800  # 452800 + one default red (~160k)
    assert rv10 <= rv50 <= rv90
    assert min(result["red_value_range"]) >= 452800


def test_ref_engine_uses_public_bucket_outline_as_exact_count_and_cells() -> None:
    evidence = extract_evidence(
        _snapshot(
            public_rows=[
                {
                    "info_id": 200001,
                    "revealed_items_detail": [
                        {"runtime_id": 1, "quality": 4, "shape_code": 23},
                        {"runtime_id": 2, "shape_key": 11},
                    ],
                }
            ],
        )
    )

    assert evidence.fixed_counts["q4"] == 2
    assert evidence.min_counts["q4"] == 2
    assert evidence.quality_cells["q4"] == 7.0
    assert evidence.avg_cells["q4"] == 3.5
    assert "public_bucket_outline_q4_count" in evidence.source_notes
    assert "public_bucket_outline_q4_cells" in evidence.source_notes
    assert "public_quality_reveal_min_counts" not in evidence.source_notes


def test_ref_engine_uses_public_red_bucket_outline_as_exact_count_and_cells() -> None:
    evidence = extract_evidence(
        _snapshot(
            public_rows=[
                {
                    "info_id": 200003,
                    "revealed_items_detail": [
                        {"runtime_id": 1, "shape_code": 23},
                        {"runtime_id": 2, "shape_key": 11},
                    ],
                }
            ],
        )
    )

    assert evidence.fixed_counts["q6"] == 2
    assert evidence.min_counts["q6"] == 2
    assert evidence.quality_cells["q6"] == 7.0
    assert evidence.avg_cells["q6"] == 3.5
    assert "public_bucket_outline_q6_count" in evidence.source_notes
    assert "public_bucket_outline_q6_cells" in evidence.source_notes
    assert "public_quality_reveal_min_counts" not in evidence.source_notes


def test_ref_engine_public_bucket_outline_does_not_override_structured_exact_inputs() -> None:
    evidence = extract_evidence(
        _snapshot(
            structured_ref_inputs={
                "total_count": 21,
                "field_updates": [
                    {"path": ["bucket", "4", "count"], "value": 1},
                    {"path": ["bucket", "4", "total_cells"], "value": 4},
                ],
            },
            public_rows=[
                {
                    "info_id": 200001,
                    "revealed_items_detail": [
                        {"runtime_id": 1, "quality": 4, "shape_code": 23},
                        {"runtime_id": 2, "quality": 4, "shape_key": 11},
                    ],
                }
            ],
        )
    )

    assert evidence.fixed_counts["q4"] == 1
    assert evidence.min_counts["q4"] == 1
    assert evidence.quality_cells["q4"] == 4.0
    assert "field_update_q4_count" in evidence.source_notes
    assert "field_update_q4_cells" in evidence.source_notes
    assert "public_bucket_outline_q4_count_conflict" in evidence.source_notes
    assert "public_bucket_outline_q4_count" not in evidence.source_notes


def test_ref_engine_does_not_treat_random_quality_reveal_shape_as_bucket_total() -> None:
    evidence = extract_evidence(
        _snapshot(
            public_rows=[
                {
                    "info_id": 200028,
                    "revealed_items_detail": [
                        {"runtime_id": 1, "quality": 4, "shape_code": 23},
                    ],
                }
            ],
        )
    )

    assert evidence.min_counts.get("q4", 0) == 0
    assert "q4" not in evidence.fixed_counts
    assert "q4" not in evidence.quality_cells
    assert "coarse_quality_reveal_min_counts" not in evidence.source_notes
    assert "public_bucket_outline_q4_count" not in evidence.source_notes


def test_ref_engine_uses_structured_hero_when_context_is_unknown() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="?",
            map_id=2404,
            structured_ref_inputs={
                "hero": "victor",
                "total_count": 21,
            },
        )
    )

    assert evidence.hero == "victor"
    assert "structured_hero" in evidence.source_notes


def test_ref_engine_duplicate_total_count_sources_do_not_add_counts() -> None:
    evidence = extract_evidence(
        {
            "ui_contract": {
                "context": {"hero": "ahmed", "map_id": 2401, "phase": "bidding"},
                "actions": {"results": [{"action_id": 100204, "result": 38}]},
                "constraints": {
                    "public_info": {
                        "public_numeric_facts": [
                            {"semantic": "total_item_count", "kind": "count", "value": 38}
                        ]
                    }
                },
            },
            "structured_ref_inputs": {
                "field_updates": [
                    {"path": ["session", "total_item_count"], "value": 38}
                ]
            },
        }
    )

    assert evidence.total_count == 38
    assert "field_update_total_count" in evidence.source_notes
    assert "action_100204_total_count" in evidence.source_notes
    assert "public_total_item_count" in evidence.source_notes
    assert not any("conflicts_total_count" in note for note in evidence.source_notes)


def test_ref_engine_duplicate_total_count_sources_log_conflicts() -> None:
    evidence = extract_evidence(
        {
            "ui_contract": {
                "context": {"hero": "ahmed", "map_id": 2401, "phase": "bidding"},
                "actions": {"results": [{"action_id": 100204, "result": 38}]},
                "constraints": {
                    "public_info": {
                        "public_numeric_facts": [
                            {"semantic": "total_item_count", "kind": "count", "value": 39}
                        ]
                    }
                },
            },
            "structured_ref_inputs": {
                "field_updates": [
                    {"path": ["session", "total_item_count"], "value": 38}
                ]
            },
        }
    )

    assert evidence.total_count == 39
    assert "public_total_item_count_conflicts_total_count:38->39" in evidence.source_notes


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


def test_ref_engine_public_quality_avg_value_decimal_filters_count() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=4406,
            structured_ref_inputs={
                "total_count": 10,
                "fixed_counts": {"q1": 0, "q3": 3, "q4": 0},
                "count_sums": {"q4q5q6": 7},
            },
            public_info={
                "public_avg_values": [
                    {
                        "semantic": "q5_avg_value",
                        "kind": "avg_value",
                        "quality": 5,
                        "value": 34288.75,
                    }
                ]
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "ok"
    assert result["evidence"]["avg_values"] == {"q5": 34288.75}
    assert result["quality_count_ranges"]["q5"] == [4, 4, 4]
    assert result["red_count_range"] == [3, 3, 3]
    assert "public_q5_avg_value" in result["notes"]


def test_ref_engine_public_numeric_fact_quality_avg_value_uses_same_route() -> None:
    evidence = extract_evidence(
        _snapshot(
            public_info={
                "public_numeric_facts": [
                    {
                        "info_id": 200037,
                        "semantic": "q5_avg_value",
                        "kind": "avg_value",
                        "quality": 5,
                        "value": 34288.75,
                    }
                ]
            },
        )
    )

    assert evidence.avg_values == {"q5": 34288.75}
    assert "public_q5_avg_value" in evidence.source_notes


def test_ref_engine_quality_avg_value_uses_three_decimal_fraction() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=4402,
            structured_ref_inputs={
                "total_count": 10,
                "fixed_counts": {"q1": 0, "q3": 2, "q5": 0, "q6": 0},
            },
            public_info={
                "public_avg_values": [
                    {
                        "semantic": "q4_avg_value",
                        "kind": "avg_value",
                        "quality": 4,
                        "value": 5615.625,
                    }
                ]
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "ok"
    assert result["quality_count_ranges"]["q4"] == [8, 8, 8]
    assert result["evidence"]["fixed_counts"]["q4"] == 8
    assert "public_q4_avg_value" in result["notes"]
    assert "quality_count_q4_from_total_count_residual" in result["notes"]


def test_ref_engine_public_quality_avg_value_falls_back_when_table_conflicts() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2402,
            structured_ref_inputs={
                "counts": {"q3": 14},
                "quality_cells": {"q3": 31},
                "split_counts": {"white": 4, "green": 7},
                "split_quality_cells": {"white": 8, "green": 10},
            },
            public_info={
                "public_avg_values": [
                    {
                        "semantic": "q4_avg_value",
                        "kind": "avg_value",
                        "quality": 4,
                        "value": 6659.21435546875,
                    }
                ]
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["combo_count"] > 0
    assert result["evidence"]["avg_values"] == {}
    assert result["quality_count_ranges"]["q4"] == [3, 4, 6]
    assert "public_quality_avg_value_conflict_fallback" in result["notes"]
    assert "public_q4_avg_value_downgraded" in result["notes"]


def test_ref_engine_zero_quality_avg_value_fixes_count_zero() -> None:
    evidence = extract_evidence(
        _snapshot(
            public_info={
                "public_avg_values": [
                    {
                        "semantic": "q5_avg_value",
                        "kind": "avg_value",
                        "quality": 5,
                        "value": 0,
                    }
                ]
            },
        )
    )

    assert evidence.avg_values["q5"] == 0
    assert evidence.fixed_counts["q5"] == 0
    assert evidence.min_counts["q5"] == 0
    assert "zero_avg_value_q5_count_zero" in evidence.source_notes


def test_ref_engine_marks_rare_actions_diagnostic_only_without_constraints() -> None:
    snapshot = _snapshot()
    snapshot["ui_contract"]["actions"] = {
        "results": [
            {
                "action_id": 100121,
                "tool": "终极审计",
                "result": 728211,
                "revealed_items": 0,
            },
            {
                "action_id": 100127,
                "tool": "全知全能",
                "result": None,
                "revealed_items": 42,
                "revealed_items_detail": [{"local_index": 1, "quality": 6}],
            },
            {
                "action_id": 100134,
                "tool": "明镜之眼",
                "result": None,
                "revealed_items": 42,
                "revealed_items_detail": [{"local_index": 1, "quality": 6}],
            },
        ],
    }

    evidence = extract_evidence(snapshot)

    assert "action_100121_total_value_diagnostic_only" in evidence.source_notes
    assert "action_100127_all_items_diagnostic_only" in evidence.source_notes
    assert "action_100134_all_item_quality_diagnostic_only" in evidence.source_notes
    assert "action_100127_revealed_items:42" in evidence.source_notes
    assert "action_100134_revealed_items:42" in evidence.source_notes
    assert evidence.min_counts.get("q6") == 1
    assert "coarse_quality_reveal_min_counts" in evidence.source_notes
    assert evidence.quality_values == {}
    assert evidence.fixed_counts == {}


def test_ref_engine_marks_total_avg_value_public_info_diagnostic_only() -> None:
    evidence = extract_evidence(
        _snapshot(
            public_info={
                "public_numeric_facts": [
                    {
                        "info_id": 200035,
                        "semantic": "total_avg_value",
                        "kind": "avg_value",
                        "quality": None,
                        "value": 18502.75,
                    }
                ]
            },
        )
    )

    assert "public_total_avg_value_diagnostic_only" in evidence.source_notes
    assert evidence.avg_values == {}
    assert evidence.quality_values == {}


def test_ref_engine_quality_value_sum_and_avg_value_derive_count() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=4406,
            structured_ref_inputs={
                "total_count": 10,
                "avg_values": {"q5": 34288.75},
                "quality_values": {"q5": 137155},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["evidence"]["fixed_counts"]["q5"] == 4
    assert result["quality_count_ranges"]["q5"] == [4, 4, 4]
    assert "quality_value_q5_count_derived" in result["notes"]


def test_ref_engine_action_quality_value_sum_joins_public_avg_value() -> None:
    result = run_reference_engine(
        {
            "ui_contract": {
                "context": {"hero": "ahmed", "map_id": 4406, "phase": "bidding"},
                "constraints": {
                    "public_info": {
                        "public_numeric_facts": [
                            {
                                "info_id": 200037,
                                "semantic": "q5_avg_value",
                                "kind": "avg_value",
                                "quality": 5,
                                "value": 34288.75,
                            }
                        ]
                    }
                },
                "actions": {
                    "results": [
                        {
                            "action_id": 100125,
                            "tool": "金品总价",
                            "result": 137155,
                        }
                    ]
                },
            },
            "structured_ref_inputs": {"total_count": 10},
        },
        max_combos=60_000,
    ).as_dict()

    assert result["evidence"]["avg_values"] == {"q5": 34288.75}
    assert result["evidence"]["quality_values"] == {"q5": 137155.0}
    assert result["evidence"]["fixed_counts"]["q5"] == 4
    assert "action_100125_q5_value_sum" in result["notes"]
    assert "public_q5_avg_value" in result["notes"]


def test_ref_engine_quality_value_sum_soft_weights_count_without_avg_value() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={
                "total_count": 50,
                "counts": {"q3": 16},
                "avg_cells": {
                    "q1": 1.2666666507720947,
                    "q3": 2.5,
                    "q4": 3.923076868057251,
                    "q5": 3.6666667461395264,
                },
                "quality_values": {"q5": 208230},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] in {"ok", "count_prior"}
    assert result["quality_count_ranges"]["q5"] == [6, 6, 6]
    assert result["quality_count_ranges"]["q6"] == [0, 0, 0]
    assert result["red_count_range"] == [0, 0, 0]
    assert "quality_value_soft_weight_v0" in result["notes"]
    assert "quality_value_q5_count_derived" not in result["notes"]


def test_ref_engine_avg_value_and_avg_cells_unique_intersection_derives_count() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={
                "total_count": 7,
                "avg_values": {"q5": 34288.75},
                "avg_cells": {"q5": 3.25},
            },
        )
    )

    assert evidence.fixed_counts["q5"] == 4
    assert evidence.min_counts["q5"] == 4
    assert "avg_value_cells_q5_count_derived" in evidence.source_notes


def test_ref_engine_avg_value_and_avg_cells_multiple_intersections_do_not_lock() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={
                "total_count": 12,
                "avg_values": {"q5": 34288.75},
                "avg_cells": {"q5": 3.25},
            },
        )
    )

    assert "q5" not in evidence.fixed_counts
    assert "avg_value_cells_q5_count_derived" not in evidence.source_notes


def test_ref_engine_keeps_value_band_when_quality_counts_and_cells_are_fixed() -> None:
    result = run_reference_engine(
        _snapshot(
            map_id=2404,
            structured_ref_inputs={
                "total_count": 25,
                "fixed_counts": {"q1": 5, "q3": 8, "q4": 6, "q5": 4, "q6": 2},
                "quality_cells": {"q1": 8, "q3": 11, "q4": 12, "q5": 9, "q6": 10},
            },
        )
    ).as_dict()

    assert result["combo_count"] == 1
    assert result["quality_count_ranges"]["q6"] == [2, 2, 2]
    assert result["value_p25"] < result["value_p50"] < result["value_p75"]
    assert result["conservative"] < result["balanced"] < result["aggressive"]
    assert "intra_quality_value_band_v0" in result["notes"]


def test_ref_engine_keeps_value_point_when_quality_values_are_exact() -> None:
    result = run_reference_engine(
        _snapshot(
            map_id=2404,
            structured_ref_inputs={
                "total_count": 25,
                "fixed_counts": {"q1": 5, "q3": 8, "q4": 6, "q5": 4, "q6": 2},
                "quality_cells": {"q1": 8, "q3": 11, "q4": 12, "q5": 9, "q6": 10},
                "quality_values": {
                    "q1": 2027,
                    "q3": 11784,
                    "q4": 32128,
                    "q5": 101220,
                    "q6": 336915,
                },
            },
        )
    ).as_dict()

    assert result["combo_count"] == 1
    assert result["value_p25"] == result["value_p50"] == result["value_p75"]
    assert "intra_quality_value_band_v0" not in result["notes"]


def test_ref_engine_settlement_truth_overrides_stale_bridge_totals() -> None:
    result = run_reference_engine(
        {
            "ui_contract": {
                "context": {"hero": "ahmed", "map_id": 4406, "phase": "settled"},
                "truth": {
                    "available": True,
                    "total_items": 24,
                    "total_cells": 62,
                    "total_value": 477562,
                },
            },
            "structured_ref_inputs": {
                "total_count": 39,
                "total_cells": 99,
                "counts": {"q3": 12},
                "avg_cells": {"q3": 2.0833332538604736, "q5": 2.799999952316284},
            },
            "final_quality_counts": "q1=1;q2=4;q3=9;q4=6;q5=2;q6=2",
            "final_quality_cells": "q1=1;q2=9;q3=17;q4=18;q5=5;q6=12",
        },
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "ok"
    assert result["evidence"]["total_count"] == 24
    assert result["evidence"]["total_grid_target"] == 62
    assert result["evidence"]["fixed_counts"] == {
        "q1": 5,
        "q3": 9,
        "q4": 6,
        "q5": 2,
        "q6": 2,
    }
    assert result["quality_count_ranges"]["q5"] == [2, 2, 2]
    assert result["red_count_range"] == [2, 2, 2]
    assert "settlement_review_total_count_overrode_bridge" in result["notes"]
    assert "settlement_review_total_grid_overrode_bridge" in result["notes"]


def test_ref_engine_sparse_exact_total_uses_probability_prior() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2401,
            structured_ref_inputs={"total_count": 33},
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["balanced"] is not None
    assert result["combo_count"] < 10_000
    assert "sparse_exact_total_prior_enumeration" in result["notes"]
    assert "combo_cap_hit" not in result["notes"]


def test_ref_engine_nonzero_quality_count_still_routes_fast_when_sparse() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2401,
            structured_ref_inputs={
                "total_count": 38,
                "avg_cells": {"q5": 9.0},
                "fixed_counts": {"q3": 13},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert "sparse_exact_total_prior_enumeration" in result["notes"]
    assert result["evidence"]["fixed_counts"]["q3"] == 13


def test_ref_engine_public_gold_total_cells_keeps_sparse_prior_path() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2401,
            public_rows=[
                {"info_id": 200017, "value": 33},
                {"info_id": 200011, "value": 23},
            ],
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["balanced"] is not None
    assert result["combo_count"] < 10_000
    assert "public_info_200011_q5_cells" in result["notes"]
    assert "sparse_exact_total_prior_enumeration" in result["notes"]
    assert "combo_cap_hit" not in result["notes"]


def test_ref_engine_derives_fixed_counts_from_avg_and_quality_cells() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="victor",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "total_cells": 34,
                "avg_cells": {
                    "q1": 1.1428571428571428,
                    "q3": 2.0,
                    "q5": 6.0,
                },
                "quality_cells": {
                    "q1": 8,
                    "q3": 16,
                    "q5": 24,
                },
            },
        ),
        max_combos=60_000,
    ).as_dict()

    evidence = result["evidence"]

    assert evidence["fixed_counts"]["q1"] == 7
    assert evidence["fixed_counts"]["q3"] == 8
    assert evidence["fixed_counts"]["q5"] == 4
    assert "quality_cells_q1_count_derived" in result["notes"]
    assert "quality_cells_q3_count_derived" in result["notes"]
    assert "quality_cells_q5_count_derived" in result["notes"]


def test_ref_engine_rejects_conflicting_count_cells_and_avg_cells() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="victor",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "fixed_counts": {"q4": 7},
                "quality_cells": {"q4": 15},
                "avg_cells": {"q4": 2.0},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "no_reachable_combo"
    assert "quality_cells_q4_avg_count_conflict" in result["notes"]
    assert "constraints_conflict_or_too_strict" in result["notes"]


def test_ref_engine_rejects_avg_and_quality_cells_without_integer_count() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="victor",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "quality_cells": {"q4": 15},
                "avg_cells": {"q4": 2.0},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "no_reachable_combo"
    assert "quality_cells_q4_avg_cells_conflict" in result["notes"]
    assert "constraints_conflict_or_too_strict" in result["notes"]


def test_ref_engine_aisha_split_white_green_fold_to_merged_q1() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "split_counts": {"white": 3, "green": 4},
                "split_quality_cells": {"white": 5, "green": 8},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    evidence = result["evidence"]

    assert result["status"] in {"ok", "count_prior"}
    assert evidence["hero"] == "aisha"
    assert evidence["split_counts"] == {"white": 3, "green": 4}
    assert evidence["split_quality_cells"] == {"white": 5.0, "green": 8.0}
    assert evidence["fixed_counts"]["q1"] == 7
    assert evidence["quality_cells"]["q1"] == 13.0
    assert evidence["avg_cells"]["q1"] == 13.0 / 7.0
    assert "split_low_quality_q1_count_merged" in result["notes"]
    assert "split_low_quality_q1_cells_merged" in result["notes"]


def test_ref_engine_aisha_split_complements_missing_green_from_merged_q1_exact() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "fixed_counts": {"q1": 7},
                "quality_cells": {"q1": 13},
                "split_counts": {"white": 3},
                "split_quality_cells": {"white": 5},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    evidence = result["evidence"]

    assert result["status"] in {"ok", "count_prior"}
    assert evidence["split_counts"] == {"white": 3, "green": 4}
    assert evidence["split_quality_cells"] == {"white": 5.0, "green": 8.0}
    assert evidence["fixed_counts"]["q1"] == 7
    assert evidence["quality_cells"]["q1"] == 13.0
    assert evidence["split_avg_cells"]["green"] == 2.0
    assert "split_low_quality_green_count_from_q1_exact" in result["notes"]
    assert "split_low_quality_green_cells_from_q1_exact" in result["notes"]


def test_ref_engine_aisha_split_derives_q1_from_total_residual_before_complement() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "fixed_counts": {"q3": 5, "q4": 4, "q5": 3, "q6": 2},
                "split_counts": {"white": 3},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    evidence = result["evidence"]

    assert result["status"] == "ok"
    assert evidence["fixed_counts"]["q1"] == 7
    assert evidence["split_counts"] == {"white": 3, "green": 4}
    assert result["quality_count_ranges"]["q1"] == [7, 7, 7]
    assert "quality_count_q1_from_total_count_residual" in result["notes"]
    assert "split_low_quality_green_count_from_q1_exact" in result["notes"]


def test_ref_engine_aisha_split_complement_rejects_count_overflow() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "fixed_counts": {"q1": 2},
                "split_counts": {"white": 3},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "no_reachable_combo"
    assert "hard_conflict:split_low_quality_q1_count_complement" in result["notes"]
    assert "constraints_conflict_or_too_strict" in result["notes"]


def test_ref_engine_settlement_truth_overrides_stale_live_action_counts() -> None:
    snapshot = _snapshot(
        hero="ahmed",
        map_id=4521,
        phase="settled",
        structured_ref_inputs={
            "total_count": 21,
            "fixed_counts": {"q1": 3, "q3": 9, "q5": 2},
            "quality_cells": {"q1": 25},
            "avg_cells": {"q1": 1.6666666269302368},
        },
    )
    snapshot["final_quality_counts"] = "q2=3;q3=2;q4=4;q5=2;q6=3"
    snapshot["final_quality_cells"] = "q2=6;q3=10;q4=12;q5=8;q6=7"
    snapshot["ui_contract"]["truth"] = {
        "total_items": 14,
        "total_cells": 43,
    }
    snapshot["ui_contract"]["actions"] = {
        "results": [
            {"action_id": 100117, "result": 9},
            {"action_id": 100104, "result": 25},
            {"action_id": 100110, "result": 1.6666666269302368},
        ]
    }

    result = run_reference_engine(snapshot, max_combos=60_000).as_dict()
    evidence = result["evidence"]

    assert result["status"] == "ok"
    assert evidence["total_count"] == 14
    assert evidence["total_grid_target"] == 43.0
    assert evidence["fixed_counts"] == {"q1": 3, "q3": 2, "q4": 4, "q5": 2, "q6": 3}
    assert evidence["quality_cells"] == {"q1": 6.0, "q3": 10.0, "q4": 12.0, "q5": 8.0, "q6": 7.0}
    assert evidence["avg_cells"]["q1"] == 2.0
    assert "settlement_review_quality_counts_overrode_live" in result["notes"]
    assert "settlement_review_quality_cells_overrode_live" in result["notes"]
    assert "quality_cells_q1_avg_count_conflict" not in result["notes"]


def test_ref_engine_aisha_white_only_is_q1_lower_bound_not_exact() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="艾莎",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "split_counts": {"white": 3},
                "split_quality_cells": {"white": 5},
            },
        )
    )

    assert evidence.hero == "aisha"
    assert evidence.split_counts == {"white": 3}
    assert evidence.split_quality_cells == {"white": 5.0}
    assert evidence.min_counts["q1"] == 3
    assert "q1" not in evidence.fixed_counts
    assert "q1" not in evidence.quality_cells
    assert "split_low_quality_q1_min_count" in evidence.source_notes
    assert "split_low_quality_q1_grid_floor" in evidence.source_notes


def test_ref_engine_aisha_white_only_q1_avg_respects_split_cell_floor() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "avg_cells": {"q1": 1.0},
                "split_counts": {"white": 3},
                "split_quality_cells": {"white": 5},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "no_reachable_combo"
    assert "split_low_quality_q1_grid_floor" in result["notes"]
    assert "constraints_conflict_or_too_strict" in result["notes"]


def test_ref_engine_aisha_white_only_q1_avg_can_remain_reachable_above_split_floor() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "avg_cells": {"q1": 2.0},
                "split_counts": {"white": 3},
                "split_quality_cells": {"white": 5},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["quality_count_ranges"]["q1"][0] >= 3
    assert result["quality_cells_ranges"]["q1"][0] >= result["quality_count_ranges"]["q1"][0] + 2
    assert "q1" not in result["evidence"]["fixed_counts"]
    assert "q1" not in result["evidence"]["quality_cells"]


def test_ref_engine_aisha_split_rejects_impossible_count_cells_pair() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "split_counts": {"white": 3},
                "split_quality_cells": {"white": 2},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "no_reachable_combo"
    assert "hard_conflict:split_low_quality_white_count_cells" in result["notes"]
    assert "constraints_conflict_or_too_strict" in result["notes"]


def test_ref_engine_aisha_split_input_without_total_count_uses_simple_prior() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2401,
            structured_ref_inputs={
                "split_counts": {"white": 3},
                "split_quality_cells": {"white": 5},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["combo_count"] > 0
    assert "total_count_from_ref_count_prior" in result["notes"]
    assert result["quality_count_ranges"]["q1"][0] >= 3


def test_ref_engine_aisha_split_conflict_with_merged_q1_is_hard_conflict() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "fixed_counts": {"q1": 8},
                "quality_cells": {"q1": 13},
                "split_counts": {"white": 3, "green": 4},
                "split_quality_cells": {"white": 5, "green": 8},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "no_reachable_combo"
    assert "split_low_quality_q1_count_conflict" in result["notes"]
    assert "hard_conflict:split_low_quality_q1_count" in result["notes"]
    assert "constraints_conflict_or_too_strict" in result["notes"]


def test_ref_engine_ahmed_r5_exact_q1_overrides_coarse_public_split() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2107,
            structured_ref_inputs={
                "total_count": 37,
                "counts": {"q1": 18},
                "split_counts": {"white": 4, "green": 4},
            },
            public_rows=[
                {
                    "info_id": 200028,
                    "revealed_items_detail": [
                        {"quality": 1},
                        {"quality": 1},
                        {"quality": 1},
                        {"quality": 2},
                    ],
                },
            ],
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] in {"ok", "count_prior"}
    assert result["combo_count"] > 0
    assert "split_low_quality_q1_exact_overrides_coarse_split" in result["notes"]
    assert "hard_conflict:split_low_quality_q1_count" not in result["notes"]
    assert result["evidence"]["fixed_counts"]["q1"] == 18


def test_ref_engine_total_grid_prior_does_not_collapse_to_known_count_floor() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2410,
            structured_ref_inputs={
                "total_cells": 70,
                "fixed_counts": {"q3": 13, "q4": 9, "q5": 3},
                "quality_cells": {"q3": 19, "q4": 29, "q5": 3},
                "split_counts": {"white": 2, "green": 6},
                "split_quality_cells": {"white": 3, "green": 8},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["red_count_range"][1] >= 1
    assert result["red_cells_range"][1] >= 1
    assert result["total_grid_range"] == [70, 70, 70]
    assert "total_count_from_ref_count_prior" in result["notes"]


def test_ref_engine_total_grid_hard_when_gold_count_unknown() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2410,
            structured_ref_inputs={
                "total_cells": 70,
                "counts": {"q3": 13, "q4": 9},
                "quality_cells": {"q3": 19, "q4": 29, "q5": 3},
                "split_counts": {"white": 2, "green": 6},
                "split_quality_cells": {"white": 3, "green": 8},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["red_count_range"][1] >= 1
    assert result["red_cells_range"][1] >= 1
    assert result["total_grid_range"] == [70, 70, 70]
    assert "structured_ref_bridge_total_cells" in result["notes"]


def test_ref_engine_total_count_residual_derives_single_missing_quality_count() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 25,
                "fixed_counts": {"q1": 5, "q3": 8, "q4": 6, "q5": 4},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "ok"
    assert result["evidence"]["fixed_counts"]["q6"] == 2
    assert result["quality_count_ranges"]["q6"] == [2, 2, 2]
    assert "quality_count_q6_from_total_count_residual" in result["notes"]


def test_ref_engine_count_sum_residual_derives_single_missing_group_count() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="victor",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "fixed_counts": {"q4": 3, "q5": 2},
                "count_sums": {"q4q5q6": 8},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "ok"
    assert result["evidence"]["fixed_counts"]["q6"] == 3
    assert result["quality_count_ranges"]["q6"] == [3, 3, 3]
    assert "count_sum_q4q5q6_q6_count_from_residual" in result["notes"]


def test_ref_engine_total_grid_residual_derives_single_missing_quality_cells() -> None:
    fixed_counts = {"q1": 5, "q3": 8, "q4": 6, "q5": 4, "q6": 2}
    all_quality_cells = {"q1": 8, "q3": 11, "q4": 12, "q5": 9, "q6": 10}

    for missing_key in ("q1", "q4", "q6"):
        quality_cells = {
            key: value for key, value in all_quality_cells.items() if key != missing_key
        }
        result = run_reference_engine(
            _snapshot(
                hero="ahmed",
                map_id=2404,
                structured_ref_inputs={
                    "total_count": 25,
                    "total_cells": 50,
                    "fixed_counts": fixed_counts,
                    "quality_cells": quality_cells,
                },
            ),
            max_combos=60_000,
        ).as_dict()

        assert result["status"] == "ok"
        assert result["total_grid_range"] == [50, 50, 50]
        assert result["quality_cells_ranges"][missing_key] == [
            all_quality_cells[missing_key],
            all_quality_cells[missing_key],
            all_quality_cells[missing_key],
        ]
        assert result["evidence"]["quality_cells"][missing_key] == float(
            all_quality_cells[missing_key]
        )
        assert f"quality_cells_{missing_key}_from_total_grid_residual" in result["notes"]


def test_ref_engine_aisha_split_uses_total_grid_residual_for_missing_green_cells() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 25,
                "total_cells": 50,
                "fixed_counts": {"q1": 5, "q3": 8, "q4": 6, "q5": 4, "q6": 2},
                "quality_cells": {"q3": 11, "q4": 12, "q5": 9, "q6": 10},
                "split_counts": {"white": 2},
                "split_quality_cells": {"white": 3},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    evidence = result["evidence"]

    assert result["status"] == "ok"
    assert evidence["quality_cells"]["q1"] == 8.0
    assert evidence["split_counts"] == {"white": 2, "green": 3}
    assert evidence["split_quality_cells"] == {"white": 3.0, "green": 5.0}
    assert "quality_cells_q1_from_total_grid_residual" in result["notes"]
    assert "split_low_quality_green_cells_from_q1_exact" in result["notes"]


def test_ref_engine_total_grid_residual_rejects_negative_missing_quality_cells() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 25,
                "total_cells": 20,
                "fixed_counts": {"q1": 5, "q3": 8, "q4": 6, "q5": 4, "q6": 2},
                "quality_cells": {"q3": 11, "q4": 12, "q5": 9, "q6": 10},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "no_reachable_combo"
    assert "hard_conflict:quality_cells_q1_total_grid_residual" in result["notes"]


def test_ref_engine_public_gold_total_cells_zero_locks_q5_like_screenshot() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={
                "total_count": 25,
                "counts": {"q3": 8},
            },
            public_rows=[
                {"info_id": 200011, "value": 0},
                {"info_id": 200017, "value": 25},
            ],
        ),
        max_combos=80_000,
    ).as_dict()

    evidence = result["evidence"]

    assert evidence["quality_cells"]["q5"] == 0.0
    assert evidence["fixed_counts"]["q5"] == 0
    assert "public_info_200011_q5_cells" in result["notes"]
    assert "zero_quality_cells_q5_count_zero" in result["notes"]
    assert result["quality_count_ranges"]["q5"] == [0, 0, 0]
    assert result["quality_cells_ranges"]["q5"] == [0, 0, 0]


def test_ref_engine_structured_bridge_gold_total_cells_zero_locks_q5() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={
                "total_count": 25,
                "quality_cells": {"q5": 0},
            },
        ),
        max_combos=80_000,
    ).as_dict()

    assert result["evidence"]["fixed_counts"]["q5"] == 0
    assert result["quality_count_ranges"]["q5"] == [0, 0, 0]


PUBLIC_EXACT_QUALITY_CELLS_ZERO_CASES = [
    pytest.param(200010, "q4", id="public_q4_total_cells_zero"),
    pytest.param(200011, "q5", id="public_q5_total_cells_zero"),
    pytest.param(200012, "q6", id="public_q6_total_cells_zero"),
]

PUBLIC_EXACT_QUALITY_CELLS_NONZERO_CASES = [
    pytest.param(200010, "q4", 17, id="public_q4_total_cells_17"),
    pytest.param(200011, "q5", 24, id="public_q5_total_cells_24"),
    pytest.param(200012, "q6", 9, id="public_q6_total_cells_9"),
]

PUBLIC_EXACT_QUALITY_COUNT_LOCK_CASES = [
    pytest.param(200018, "q4", 6, id="public_q4_count_6"),
    pytest.param(200019, "q5", 3, id="public_q5_count_3"),
    pytest.param(200020, "q6", 2, id="public_q6_count_2"),
]

PUBLIC_EXACT_QUALITY_COUNT_ZERO_CASES = [
    pytest.param(200018, "q4", id="public_q4_count_zero"),
    pytest.param(200019, "q5", id="public_q5_count_zero"),
    pytest.param(200020, "q6", id="public_q6_count_zero"),
]


@pytest.mark.parametrize("info_id,quality_key", PUBLIC_EXACT_QUALITY_CELLS_ZERO_CASES)
def test_ref_engine_public_exact_quality_cells_zero_locks_count(
    info_id: int,
    quality_key: str,
) -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={"total_count": 30},
            public_rows=[{"info_id": info_id, "value": 0}],
        )
    )

    assert evidence.quality_cells[quality_key] == 0.0
    assert evidence.fixed_counts[quality_key] == 0
    assert f"public_info_{info_id}_{quality_key}_cells" in evidence.source_notes
    assert f"zero_quality_cells_{quality_key}_count_zero" in evidence.source_notes


@pytest.mark.parametrize("info_id,quality_key,value", PUBLIC_EXACT_QUALITY_CELLS_NONZERO_CASES)
def test_ref_engine_public_exact_quality_cells_nonzero_does_not_force_zero(
    info_id: int,
    quality_key: str,
    value: int,
) -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={"total_count": 30},
            public_rows=[{"info_id": info_id, "value": value}],
        )
    )

    assert evidence.quality_cells[quality_key] == float(value)
    assert evidence.fixed_counts.get(quality_key) != 0
    assert f"public_info_{info_id}_{quality_key}_cells" in evidence.source_notes
    assert f"zero_quality_cells_{quality_key}_count_zero" not in evidence.source_notes


@pytest.mark.parametrize("info_id,quality_key,value", PUBLIC_EXACT_QUALITY_COUNT_LOCK_CASES)
def test_ref_engine_public_exact_quality_count_locks_ranges(
    info_id: int,
    quality_key: str,
    value: int,
) -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={"total_count": 30},
            public_rows=[{"info_id": info_id, "value": value}],
        ),
        max_combos=80_000,
    ).as_dict()

    assert result["evidence"]["fixed_counts"][quality_key] == value
    assert result["quality_count_ranges"][quality_key] == [value, value, value]
    assert f"public_info_{info_id}_{quality_key}_count" in result["notes"]


@pytest.mark.parametrize("info_id,quality_key", PUBLIC_EXACT_QUALITY_COUNT_ZERO_CASES)
def test_ref_engine_public_exact_quality_count_zero_locks_ranges(
    info_id: int,
    quality_key: str,
) -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={"total_count": 30},
            public_rows=[{"info_id": info_id, "value": 0}],
        ),
        max_combos=80_000,
    ).as_dict()

    assert result["evidence"]["fixed_counts"][quality_key] == 0
    assert result["quality_count_ranges"][quality_key] == [0, 0, 0]
    assert f"public_info_{info_id}_{quality_key}_count" in result["notes"]


PUBLIC_EXACT_SESSION_INFO_CASES = [
    pytest.param(200017, "total_count", 25, "public_info_total_item_count", id="public_total_count_25"),
    pytest.param(200009, "total_grid_target", 100, "public_info_total_cells", id="public_total_cells_100"),
]


@pytest.mark.parametrize(
    "info_id,evidence_attr,expected_value,note_token",
    PUBLIC_EXACT_SESSION_INFO_CASES,
)
def test_ref_engine_public_exact_session_info_rows(
    info_id: int,
    evidence_attr: str,
    expected_value: int,
    note_token: str,
) -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            public_rows=[{"info_id": info_id, "value": expected_value}],
        )
    )

    assert getattr(evidence, evidence_attr) == expected_value
    assert note_token in evidence.source_notes


def test_ref_engine_public_exact_quality_cells_conflict_preserves_bridge() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="ahmed",
            map_id=2410,
            structured_ref_inputs={
                "total_count": 25,
                "quality_cells": {"q5": 24},
            },
            public_rows=[{"info_id": 200011, "value": 0}],
        )
    )

    assert evidence.quality_cells["q5"] == 24.0
    assert evidence.fixed_counts.get("q5") != 0
    assert "public_info_200011_q5_cells_conflict" in evidence.source_notes
    assert "zero_quality_cells_q5_count_zero" not in evidence.source_notes


def test_ref_engine_public_q5_avg_value_and_count_zero_from_public_numeric_facts() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="maria",
            map_id=2102,
            structured_ref_inputs={"total_count": 20},
            public_info={
                "public_numeric_facts": [
                    {
                        "info_id": 200037,
                        "semantic": "q5_avg_value",
                        "kind": "avg_value",
                        "quality": 5,
                        "label": "金均价",
                        "value": 0.0,
                        "display_value": "0.00",
                        "text": "金均价 0.00",
                    },
                    {
                        "info_id": 200019,
                        "semantic": "q5_count",
                        "kind": "count",
                        "quality": 5,
                        "label": "金件",
                        "value": 0,
                        "display_value": "0",
                        "text": "金件 0",
                    },
                ],
                "public_avg_values": [
                    {
                        "info_id": 200037,
                        "semantic": "q5_avg_value",
                        "kind": "avg_value",
                        "quality": 5,
                        "label": "金均价",
                        "value": 0.0,
                        "display_value": "0.00",
                        "text": "金均价 0.00",
                    }
                ],
            },
            public_rows=[
                {"info_id": 200037, "value": 0.0},
                {"info_id": 200019, "value": 0},
            ],
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["evidence"]["avg_values"]["q5"] == 0.0
    assert result["evidence"]["fixed_counts"]["q5"] == 0
    assert result["quality_count_ranges"]["q5"] == [0, 0, 0]
    assert "public_q5_avg_value" in result["notes"]
    assert "public_info_200019_q5_count" in result["notes"]
    assert "zero_avg_value_q5_count_zero" in result["notes"]


def test_ref_engine_public_q5_avg_cells_zero_locks_count() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="maria",
            map_id=2101,
            structured_ref_inputs={"total_count": 20},
            public_info={
                "public_numeric_facts": [
                    {
                        "info_id": 200015,
                        "semantic": "q5_avg_cells",
                        "kind": "avg_cells",
                        "quality": 5,
                        "label": "金均格",
                        "value": 0.0,
                        "display_value": "0.00",
                        "text": "金均格 0.00",
                    }
                ],
                "public_avg_cells": [
                    {
                        "info_id": 200015,
                        "semantic": "q5_avg_cells",
                        "kind": "avg_cells",
                        "quality": 5,
                        "label": "金均格",
                        "value": 0.0,
                        "display_value": "0.00",
                        "text": "金均格 0.00",
                    }
                ],
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["evidence"]["avg_cells"]["q5"] == 0.0
    assert result["evidence"]["fixed_counts"]["q5"] == 0
    assert result["quality_count_ranges"]["q5"] == [0, 0, 0]
    assert result["quality_cells_ranges"]["q5"] == [0, 0, 0]
    assert "public_q5_avg_cells" in result["notes"]
    assert "zero_avg_cells_q5_count_zero" in result["notes"]


def test_ref_engine_ahmed_express_zero_purple_cells_and_gold_avg_lock_counts() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2105,
            structured_ref_inputs={
                "total_count": 17,
                "quality_cells": {"q4": 0},
                "avg_cells": {"q5": 0.0},
            },
            public_rows=[
                {"info_id": 200010, "value": 0, "value_field": 14},
            ],
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["quality_count_ranges"]["q4"] == [0, 0, 0]
    assert result["quality_count_ranges"]["q5"] == [0, 0, 0]
    assert result["evidence"]["fixed_counts"]["q4"] == 0
    assert result["evidence"]["fixed_counts"]["q5"] == 0
    assert "public_info_200010_q4_cells" in result["notes"]
    assert "zero_quality_cells_q4_count_zero" in result["notes"]
    assert "zero_avg_cells_q5_count_zero" in result["notes"]


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
    assert ranges["q4"] == [5, 5, 5]
    assert result["red_count_range"] == [1, 1, 1]
    assert result["quality_cells_ranges"]["q4"] == [9, 9, 9]
    assert result["quality_cells_ranges"]["q5"] == [0, 0, 0]
    assert result["red_cells_range"] == [2, 3, 4]


def test_ref_engine_victor_inferred_zero_action_constrains_gold_avg() -> None:
    snapshot = _snapshot(
        hero="victor",
        map_id=2404,
        structured_ref_inputs={
            "total_count": 21,
            "total_cells": 34,
            "avg_cells": {"q4": 1.8},
            "count_sums": {"q4q5q6": 6},
        },
    )
    snapshot["ui_contract"]["actions"] = {
        "results": [
            {
                "action_id": "100113",
                "result": "0",
                "inferred_zero": "True",
            }
        ],
    }

    result = run_reference_engine(snapshot, max_combos=60_000).as_dict()

    assert result["status"] == "ok"
    assert result["evidence"]["avg_cells"]["q5"] == 0.0
    assert result["evidence"]["fixed_counts"]["q5"] == 0
    assert result["quality_count_ranges"]["q5"] == [0, 0, 0]
    assert result["quality_cells_ranges"]["q5"] == [0, 0, 0]
    assert "action_100113_q5_avg_cells_inferred_zero" in result["notes"]


def test_ref_engine_victor_decimal_q4_avg_keeps_reachable_counts() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="victor",
            map_id=2401,
            structured_ref_inputs={
                "avg_cells": {"q4": 1.8666666746139526},
                "count_sums": {"q4q5q6": 18},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert result["combo_count"] > 0
    assert result["quality_count_ranges"]["q4"][1] == 15
    assert result["quality_cells_ranges"]["q4"][1] == 28
    assert result["red_count_range"][1] is not None


def test_ref_engine_sparse_map_family_prior_centers_cover_non_villa_maps() -> None:
    cases = [
        (2101, "nest_price:2001", "tier_prob:101", "total_count_prior_center:24"),
        (2201, "nest_price:2011", "tier_prob:102", "total_count_prior_center:24"),
        (2301, "nest_price:2021", "tier_prob:103", "total_count_prior_center:27"),
        (2401, "nest_price:2031", "tier_prob:104", "total_count_prior_center:28"),
        (2501, "nest_price:2041", "tier_prob:105", "total_count_prior_center:33"),
        (2601, "fallback_default_price", "tier_prob:106", "total_count_prior_center:33"),
    ]

    for map_id, price_note, tier_note, count_center_note in cases:
        result = run_reference_engine(
            _snapshot(
                hero="victor",
                map_id=map_id,
                structured_ref_inputs={"min_counts": {"q4": 1}},
            ),
            max_combos=500,
        ).as_dict()

        assert result["status"] == "count_prior"
        assert result["combo_count"] > 0
        assert price_note in result["notes"]
        assert tier_note in result["notes"]
        assert "total_count_from_ref_count_prior" in result["notes"]
        assert count_center_note in result["notes"]


def test_ref_engine_known_non_villa_maps_are_reachable_with_explicit_total() -> None:
    for map_id, tier_note in ((2101, "tier_prob:101"), (2301, "tier_prob:103"), (2601, "tier_prob:106")):
        result = run_reference_engine(
            _snapshot(
                hero="victor",
                map_id=map_id,
                structured_ref_inputs={
                    "total_count": 24 if map_id == 2101 else 33,
                    "count_sums": {"q4q5q6": 4},
                },
            ),
            max_combos=500,
        ).as_dict()

        assert result["status"] == "ok"
        assert result["combo_count"] > 0
        assert tier_note in result["notes"]


def test_ref_engine_avg_cells_map_to_integer_grid_options() -> None:
    assert _avg_grid_options(4, 1.8) == []
    assert _avg_grid_options(5, 1.8) == [9]
    assert _avg_grid_options(6, 1.8) == []
    assert _avg_grid_options(0, 0) == [0]
    assert _avg_grid_options(1, 0) == []


def test_ref_engine_avg_grid_options_use_game_display_for_truncated_ratios() -> None:
    assert _avg_grid_options(11, 2.09) == [23]
    assert _avg_grid_options(11, 23 / 11) == [23]
    assert _avg_grid_options(11, 2.9) == [32]
    assert _avg_grid_options(10, 2.9) == [29]
    assert _avg_grid_options(7, 2.4285714285714284) == [17]
    assert _avg_grid_options(16, 3.4375) == [55]


@pytest.mark.parametrize(
    ("avg", "count", "cells", "display", "source_note"),
    CAPTURE_AVG_CELL_FIXTURES,
)
def test_ref_engine_avg_grid_options_match_capture_and_display_samples(
    avg: float,
    count: int,
    cells: int,
    display: str,
    source_note: str,
) -> None:
    del source_note
    assert _avg_grid_options(count, avg) == [cells]
    assert _avg_count_from_cells(avg, cells) == count


def test_ref_engine_avg_grid_options_reject_nearby_capture_mismatch() -> None:
    # 24/7 packet float displays as 3.42, not 3.43 — must not lock 55 cells at count 16.
    assert _avg_grid_options(16, 3.4285714626312256) == []
    assert _avg_grid_options(7, 3.4285714626312256) == [24]


@pytest.mark.skipif(
    not FATBEANS_Q4_290_SAMPLE.exists(),
    reason="fatbeans q4 2.90 capture sample is not available",
)
def test_ref_engine_avg_grid_options_load_q4_290_from_fatbeans_capture() -> None:
    from bidking_lab.inference.display import format_value
    from bidking_lab.live.fatbeans import parse_fatbeans_capture

    events = parse_fatbeans_capture(FATBEANS_Q4_290_SAMPLE)
    observed = [
        float(info.value)
        for state in events.states
        for info in state.public_infos
        if info.info_id == 200013 and info.value is not None
    ]

    assert observed
    avg = observed[0]
    assert avg == pytest.approx(2.909090995788574, abs=1e-6)
    assert _avg_grid_options(11, avg) == [32]
    assert format_value(32, 11) == "2.90"
    assert _avg_grid_options(22, avg) == [64]


def test_ref_engine_q5_avg_209_locks_count_from_group_report() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="victor",
            map_id=2404,
            structured_ref_inputs={
                "total_count": 21,
                "avg_cells": {"q5": 2.09},
            },
        ),
        max_combos=80_000,
    ).as_dict()

    assert result["quality_count_ranges"]["q5"] == [11, 11, 11]


def test_ref_engine_avg_count_from_cells_accepts_display_truncated_ratios() -> None:
    assert _avg_count_from_cells(2.09, 23) == 11
    assert _avg_count_from_cells(23 / 11, 23) == 11
    assert _avg_count_from_cells(2.909090995788574, 32) == 11
    assert _avg_count_from_cells(2.4285714626312256, 17) == 7
    assert _avg_count_from_cells(3.43, 55) == 16
    assert _avg_count_from_cells(55 / 16, 55) == 16
    assert _avg_count_from_cells(2.9, 32) == 11
    assert _avg_count_from_cells(1.8, 9) == 5


def test_ref_engine_total_grid_fit_keeps_scalable_cells_integer_and_composable() -> None:
    counts = {"q1": 4, "q3": 9, "q4": 5, "q5": 0, "q6": 2}
    grids = {"q1": 5.2, "q3": 18.4, "q4": 9.0, "q5": 0.0, "q6": 4.6}

    fitted = _fit_grids_to_total_target(
        grids,
        counts,
        {"q4": 1.8, "q5": 0.0},
        34.0,
    )

    assert fitted["q4"] == 9.0
    assert fitted["q5"] == 0.0
    assert sum(fitted.values()) == 34.0
    for key, value in fitted.items():
        assert value == int(value)
        assert can_compose_grid_total(counts[key], int(value))


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


def test_ref_engine_recognizes_full_hero_id_map() -> None:
    evidence = extract_evidence(
        {
            "ui_contract": {
                "context": {
                    "hero": "?",
                    "hero_id": 110,
                    "map_id": 2401,
                    "phase": "bidding",
                },
                "constraints": {"public_info": {}},
            },
            "structured_ref_inputs": {"total_count": 30},
            "public_info_rows": [],
        }
    )

    assert evidence.hero == "isabella"


def test_ref_engine_generic_hero_runs_reference_engine() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ethan",
            structured_ref_inputs={"total_count": 28},
        )
    )

    assert result.status != "not_structured_hero"
    assert "generic_ref_hero" in result.notes


def test_ref_engine_ethan_full_outline_skill_sets_total_grid_target() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="ethan",
            structured_ref_inputs={"total_count": 34},
        )
        | {
            "skill_reveals": [
                {
                    "skill_id": 1002085,
                    "hero_id": 208,
                    "observed_items": [
                        {
                            "runtime_id": 1,
                            "shape_code": 11,
                            "cells": 1,
                        },
                        {
                            "runtime_id": 2,
                            "shape_code": 22,
                            "cells": 4,
                        },
                    ],
                }
            ],
        }
    )

    assert evidence.total_count == 2
    assert evidence.total_grid_target == 5.0
    assert "ethan_skill_full_outline_count" in evidence.source_notes
    assert "ethan_skill_full_outline_cells" in evidence.source_notes
    assert any(
        note.startswith("ethan_skill_full_outline_count_conflicts_total_count:")
        for note in evidence.source_notes
    )


def test_ref_engine_ethan_r1_outline_is_diagnostic_only() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="ethan",
            structured_ref_inputs={"total_count": 28},
        )
        | {
            "skill_reveals": [
                {
                    "skill_id": 1002081,
                    "hero_id": 208,
                    "observed_items": [
                        {"runtime_id": 1, "shape_code": 23, "cells": 4},
                        {"runtime_id": 2, "shape_code": 11, "cells": 1},
                    ],
                }
            ],
        }
    )

    assert evidence.total_grid_target is None
    assert "ethan_skill_r1_outline:2:5" in evidence.source_notes
    assert "ethan_skill_full_outline_cells" not in evidence.source_notes


def test_ref_engine_public_max_quality_gold_locks_q6_to_zero() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="isabella",
            structured_ref_inputs={"total_count": 24},
            public_rows=[
                {
                    "info_id": 200048,
                    "revealed_items_detail": [
                        {"runtime_id": 501, "quality": 5},
                    ],
                }
            ],
        )
    )

    assert evidence.fixed_counts.get("q6") == 0
    assert evidence.min_counts.get("q6") == 0
    assert "public_max_quality_ceiling:5" in evidence.source_notes
    assert "public_max_quality_zero_q6" in evidence.source_notes


def test_ref_engine_public_max_quality_conflicts_with_existing_red_count() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="isabella",
            structured_ref_inputs={"total_count": 24},
            public_rows=[
                {
                    "info_id": 200048,
                    "revealed_items_detail": [
                        {"runtime_id": 501, "quality": 5},
                    ],
                },
                {
                    "info_id": 200028,
                    "revealed_items_detail": [
                        {"runtime_id": 601, "quality": 6},
                    ],
                },
            ],
        )
    )

    assert "hard_conflict:public_max_quality_zero_q6" in evidence.source_notes
    assert evidence.min_counts.get("q6", 0) >= 1


def test_ref_engine_maria_coarse_quality_and_value_from_action_rows() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="maria",
            structured_ref_inputs={"total_count": 24},
            public_rows=[],
        )
        | {
            "action_result_rows": [
                {
                    "action_id": 100134,
                    "tool": "明镜之眼",
                    "revealed_items_detail": [
                        {"local_index": 3, "quality": 1, "value": 1200},
                        {"local_index": 7, "quality": 2, "value": 800},
                        {"local_index": 11, "quality": 3, "value": 4500},
                        {"local_index": 15, "quality": 3, "value": 3200},
                    ],
                }
            ],
        }
    )

    assert evidence.min_counts["q1"] == 2
    assert evidence.min_counts["q3"] == 2
    assert evidence.split_counts == {"white": 1, "green": 1}
    assert evidence.quality_value_floors["q1"] == 2000.0
    assert evidence.quality_value_floors["q3"] == 7700.0
    assert "coarse_quality_reveal_min_counts" in evidence.source_notes
    assert "coarse_quality_reveal_source:action_result_100134" in evidence.source_notes


def test_ref_engine_maria_skill_reveal_rows_use_maria_specific_notes() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="maria",
            structured_ref_inputs={"total_count": 30},
            public_rows=[
                {
                    "info_id": 200027,
                    "revealed_items_detail": [
                        {"local_index": 58, "quality": 5},
                        {"local_index": 90, "quality": 1},
                    ],
                }
            ],
        )
        | {
            "skill_reveal_rows": [
                {
                    "skill_id": 100108,
                    "hero_id": 108,
                    "tool": "玛丽亚·总价",
                    "result": 37063,
                    "observed_items": [],
                    "revealed_items_detail": [],
                },
                {
                    "skill_id": 10010801,
                    "hero_id": 108,
                    "tool": "玛丽亚·品质",
                    "result": None,
                    "observed_items": [
                        {"local_index": 90, "quality": 1},
                        {"local_index": 43, "quality": 2},
                        {"local_index": 36, "quality": 3},
                        {"local_index": 104, "quality": 1},
                    ],
                    "revealed_items_detail": [
                        {"local_index": 90, "quality": 1},
                        {"local_index": 43, "quality": 2},
                        {"local_index": 36, "quality": 3},
                        {"local_index": 104, "quality": 1},
                    ],
                },
            ],
        }
    )

    assert evidence.min_counts["q1"] >= 2
    assert evidence.min_counts.get("q3", 0) >= 1
    assert evidence.min_counts.get("q5", 0) >= 1
    assert evidence.split_counts.get("green", 0) >= 1
    assert evidence.split_counts == {"white": 2, "green": 1}
    assert evidence.quality_value_floors["q1"] == 37063.0
    assert "maria_skill_coarse_quality_min_counts" in evidence.source_notes
    assert "maria_skill_coarse_quality_source:maria_skill_10010801" in evidence.source_notes
    assert "maria_skill_q1_value_floor" in evidence.source_notes
    assert "coarse_quality_reveal_source:public_info_200027" in evidence.source_notes
    assert "coarse_quality_reveal_source:maria_skill_10010801" not in evidence.source_notes


def test_ref_engine_raven_all_item_quality_public_info_sets_min_counts() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="raven",
            structured_ref_inputs={"total_count": 30},
            public_rows=[
                {
                    "info_id": 200030,
                    "revealed_items_detail": [
                        {"local_index": 1, "quality": 1},
                        {"local_index": 2, "quality": 3},
                        {"local_index": 3, "quality": 4},
                        {"local_index": 4, "quality": 5},
                        {"local_index": 5, "quality": 6},
                    ],
                }
            ],
        )
    )

    assert evidence.min_counts["q1"] == 1
    assert evidence.min_counts["q3"] == 1
    assert evidence.min_counts["q4"] == 1
    assert evidence.min_counts["q5"] == 1
    assert evidence.min_counts["q6"] == 1
    assert "coarse_quality_reveal_source:public_info_200030" in evidence.source_notes


def test_ref_engine_skips_shaped_items_for_coarse_min_counts() -> None:
    evidence = extract_evidence(
        _snapshot(
            public_rows=[
                {
                    "info_id": 200001,
                    "revealed_items_detail": [
                        {"runtime_id": 1, "quality": 4, "shape_code": 23},
                    ],
                },
                {
                    "info_id": 200028,
                    "revealed_items_detail": [
                        {"local_index": 9, "quality": 4},
                    ],
                },
            ],
        )
    )

    assert evidence.fixed_counts.get("q4") == 1
    assert evidence.min_counts.get("q4") == 1
    assert "coarse_quality_reveal_source:public_info_200028" in evidence.source_notes
    assert "coarse_quality_reveal_source:public_info_200001" not in evidence.source_notes


def test_ref_engine_treasure_value_action_locks_q6_when_merged_quality_is_q5() -> None:
    snapshot = {
        "ui_contract": {
            "context": {
                "hero": "sophie",
                "map_id": 2403,
                "phase": "bidding",
            },
            "constraints": {"public_info": {}},
        },
        "structured_ref_inputs": {"total_count": 34},
        "public_info_rows": [],
        "skill_reveals": [
            {
                "skill_id": 1001073,
                "hero_id": 107,
                "observed_items": [
                    {
                        "local_index": 31,
                        "runtime_id": 1425860544908193,
                        "quality": 5,
                    }
                ],
            }
        ],
        "action_result_rows": [
            {
                "action_id": 100163,
                "tool": "至宝估价",
                "revealed_items_detail": [
                    {
                        "local_index": 30,
                        "runtime_id": 1425860544908193,
                        "value": 43650,
                    }
                ],
            }
        ],
    }

    evidence = extract_evidence(snapshot)

    assert evidence.fixed_counts.get("q6") == 0
    assert evidence.min_counts.get("q6") == 0
    assert "public_max_quality_ceiling:5" in evidence.source_notes
    assert "public_max_quality_zero_q6" in evidence.source_notes


def test_ref_engine_defers_grid_only_total_count_prior_for_ahmed() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2309,
            structured_ref_inputs={},
            public_rows=[{"info_id": 200009, "value": 152}],
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "missing_total_count"
    assert "waiting_total_count" in result["notes"]
    assert "total_count_from_ref_count_prior" not in result["notes"]
    assert result["combo_count"] == 0


def test_ref_engine_runs_after_public_total_count_for_ahmed() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ahmed",
            map_id=2309,
            structured_ref_inputs={},
            public_rows=[
                {"info_id": 200009, "value": 152},
                {"info_id": 200017, "value": 48},
            ],
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] in {"ok", "count_prior"}
    assert result["combo_count"] > 0
    assert "waiting_total_count" not in result["notes"]


def test_ref_engine_defers_grid_only_total_count_prior_for_generic_ethan() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="ethan",
            map_id=2401,
            structured_ref_inputs={},
            public_rows=[{"info_id": 200009, "value": 95}],
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "missing_total_count"
    assert "waiting_total_count:grid_only" in result["notes"]


def test_ref_engine_keeps_aisha_grid_prior_when_quality_constraints_present() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2410,
            structured_ref_inputs={
                "total_cells": 70,
                "fixed_counts": {"q3": 13, "q4": 9, "q5": 3},
                "quality_cells": {"q3": 19, "q4": 29, "q5": 3},
                "split_counts": {"white": 2, "green": 6},
                "split_quality_cells": {"white": 3, "green": 8},
            },
        ),
        max_combos=60_000,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert "total_count_from_ref_count_prior" in result["notes"]
    assert "waiting_total_count" not in result["notes"]


def test_ref_engine_keeps_victor_min_count_prior_without_total_grid() -> None:
    result = run_reference_engine(
        _snapshot(
            hero="victor",
            map_id=2101,
            structured_ref_inputs={"min_counts": {"q4": 1}},
        ),
        max_combos=500,
    ).as_dict()

    assert result["status"] == "count_prior"
    assert "total_count_from_ref_count_prior" in result["notes"]
    assert "waiting_total_count" not in result["notes"]


SECTION_50_2_FATBEANS_SAMPLES = (
    FATBEANS_SAMPLE_DIR / "fatbeans_mixed_ahmed_2406_5rounds_2406_1388889389495497_0001.json",
    FATBEANS_SAMPLE_DIR / "fatbeans_valid_ahmed_2403_2rounds_2403_1388889391900123_0022.json",
)


def _ahmed_fatbeans_snapshot(sample_path: Path, *, round_count: int = 2) -> dict:
    from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events, parse_fatbeans_capture
    from bidking_lab.live.monitor import (
        _ahmad_ref_inputs_from_batches,
        _public_info_rows,
        _skill_reveal_rows,
    )

    events = parse_fatbeans_capture(sample_path)
    batches = [batch for batch in live_batches_from_fatbeans_events(events) if batch.phase != "settled"]
    prefix = batches[:round_count]
    return {
        "ui_contract": {
            "context": {"hero": "ahmed", "phase": "bidding"},
            "constraints": {"public_info": {}},
        },
        "structured_ref_inputs": _ahmad_ref_inputs_from_batches(prefix, hero="ahmed") or {},
        "public_info_rows": _public_info_rows(events, {}),
        "skill_reveals": _skill_reveal_rows(events, {}),
        "skill_reveal_rows": _skill_reveal_rows(events, {}),
        "action_result_rows": [],
    }


@pytest.mark.parametrize("sample_path", SECTION_50_2_FATBEANS_SAMPLES, ids=lambda path: path.name[:40])
def test_ref_engine_exact_total_q5_avg_cells_fast_path_preserves_outputs(
    sample_path: Path,
) -> None:
    snapshot = _ahmed_fatbeans_snapshot(sample_path)
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()

    assert result["status"] == "ok"
    assert "exact_total_avg_cells_fast_path" in result["notes"]
    if sample_path.name.startswith("fatbeans_mixed_ahmed_2406"):
        assert result["combo_count"] == 253
        assert result["balanced"] == 375_163
    else:
        assert result["combo_count"] == 196
        assert result["balanced"] == 901_101


@pytest.mark.parametrize("sample_path", SECTION_50_2_FATBEANS_SAMPLES, ids=lambda path: path.name[:40])
def test_ref_engine_exact_total_q5_avg_cells_fast_path_warm_run_is_bounded(
    sample_path: Path,
) -> None:
    snapshot = _ahmed_fatbeans_snapshot(sample_path)
    run_reference_engine(snapshot, max_combos=50_000)
    started = time.perf_counter()
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    assert "exact_total_avg_cells_fast_path" in result["notes"]
    assert elapsed_ms < 500.0


AISHA_BATCH_B_BAND_SAMPLES = (
    (
        FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2501_5rounds_2501_1295018669960456_0139.json",
        140,
    ),
    (
        FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2401_5rounds_2401_1295018668661353_0045.json",
        113,
    ),
    (
        FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2401_3rounds_2401_1295019017806948_0032.json",
        121,
    ),
    (
        FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2403_3rounds_2403_1295019017648392_0051.json",
        111,
    ),
    (
        FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2510_3rounds_2510_1274128128479934_0209.json",
        100,
    ),
    (
        FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2401_3rounds_2401_1295018668515929_0030.json",
        99,
    ),
    (
        FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2504_5rounds_2504_1295018708289152_0166.json",
        96,
    ),
)


def _aisha_fatbeans_snapshot(sample_path: Path, *, round_count: int | None = None) -> dict:
    from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events, parse_fatbeans_capture
    from bidking_lab.live.monitor import (
        _ahmad_ref_inputs_from_batches,
        _public_info_rows,
        _skill_reveal_rows,
    )

    events = parse_fatbeans_capture(sample_path)
    batches = [batch for batch in live_batches_from_fatbeans_events(events) if batch.phase != "settled"]
    if round_count is None:
        round_count = max(3, len(batches) - 1)
    prefix = batches[:round_count]
    sort_id = max(int(batch.sequence or 0) for batch in prefix if batch.sequence is not None)
    prefix_events = events
    if sort_id:
        prefix_events = type(events)(
            packets=tuple(row for row in events.packets if int(row.sort_id) <= sort_id),
            frames=tuple(row for row in events.frames if int(row.sort_id) <= sort_id),
            sends=tuple(row for row in events.sends if int(row.sort_id) <= sort_id),
            states=tuple(row for row in events.states if int(row.sort_id) <= sort_id),
            statuses=tuple(row for row in events.statuses if int(row.sort_id) <= sort_id),
        )
    return {
        "ui_contract": {
            "context": {"hero": "aisha", "phase": "bidding"},
            "constraints": {"public_info": {}},
        },
        "structured_ref_inputs": _ahmad_ref_inputs_from_batches(prefix, hero="aisha") or {},
        "public_info_rows": _public_info_rows(prefix_events, {}),
        "skill_reveals": _skill_reveal_rows(prefix_events, {}),
        "skill_reveal_rows": _skill_reveal_rows(prefix_events, {}),
        "action_result_rows": [],
    }


def _aisha_fatbeans_settlement_total_value(sample_path: Path) -> int:
    from bidking_lab.live.fatbeans import parse_fatbeans_capture

    events = parse_fatbeans_capture(sample_path)
    items_path = ROOT / "data" / "processed" / "items.json"
    values_by_id: dict[int, int] = {}
    if items_path.exists():
        import json

        for row in json.loads(items_path.read_text(encoding="utf-8-sig")):
            values_by_id[int(row["item_id"])] = int(row.get("value") or 0)
    for state in reversed(events.states):
        if not state.inventory_items:
            continue
        return sum(
            int(values_by_id.get(int(item.item_id), 0))
            for item in state.inventory_items
        )
    raise AssertionError(f"no settlement inventory in {sample_path.name}")


# Penultimate replay baselines (2026-06-13). Truth is outside ±15% of balanced today;
# gate locks quote path and forbids >15% worsening of |truth - balanced|.
AISHA_GOOD_REGRESSION_SAMPLES = (
    (
        FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2501_4rounds_2501_1295018669612326_0123.json",
        290_810,
        233,
        63_702,
    ),
    (
        FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2505_5rounds_2505_1295018595274342_0173.json",
        250_172,
        15,
        83_626,
    ),
)


@pytest.mark.parametrize(
    ("sample_path", "baseline_balanced", "baseline_combo_count", "baseline_abs_gap"),
    AISHA_GOOD_REGRESSION_SAMPLES,
    ids=[sample[0].name[:36] for sample in AISHA_GOOD_REGRESSION_SAMPLES],
)
def test_ref_engine_aisha_good_regression_balanced_bid_does_not_worsen(
    sample_path: Path,
    baseline_balanced: int,
    baseline_combo_count: int,
    baseline_abs_gap: int,
) -> None:
    result = run_reference_engine(
        _aisha_fatbeans_snapshot(sample_path),
        max_combos=50_000,
    ).as_dict()
    truth = _aisha_fatbeans_settlement_total_value(sample_path)
    balanced = int(result["balanced"])

    assert result["status"] == "count_prior"
    assert result["combo_count"] == baseline_combo_count
    assert balanced == baseline_balanced
    assert abs(truth - balanced) <= int(baseline_abs_gap * 1.15)


@pytest.mark.parametrize(
    ("sample_path", "settlement_cells"),
    AISHA_BATCH_B_BAND_SAMPLES,
    ids=[sample[0].name[:36] for sample in AISHA_BATCH_B_BAND_SAMPLES],
)
def test_ref_engine_aisha_batch_b_exact_total_grid_band_no_regress(
    sample_path: Path,
    settlement_cells: int,
) -> None:
    snapshot = _aisha_fatbeans_snapshot(sample_path)
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()
    low, mid, high = result["total_grid_range"]

    assert low <= settlement_cells <= high
    if settlement_cells == 140:
        assert "total_grid_target_from_known_high_tier_cells" in result["notes"]
        assert result["evidence"]["total_grid_target"] == settlement_cells


def test_ref_engine_avg_value_only_q5_count_derivation_is_unique() -> None:
    # Integer avg prices match every count; use a fractional public avg instead.
    result = run_reference_engine(
        _snapshot(
            hero="aisha",
            map_id=2404,
            structured_ref_inputs={"total_count": 15},
            public_info={
                "public_avg_values": [
                    {
                        "semantic": "q5_avg_value",
                        "kind": "avg_value",
                        "quality": 5,
                        "value": 1560.125,
                    }
                ]
            },
        ),
        max_combos=20_000,
    ).as_dict()

    assert result["evidence"]["fixed_counts"].get("q5") == 8
    assert "avg_value_only_q5_count_derived" in result["notes"]


def test_ref_engine_total_grid_target_residual_uses_unfixed_avg_cells() -> None:
    evidence = extract_evidence(
        _snapshot(
            hero="aisha",
            map_id=2501,
            structured_ref_inputs={
                "total_count": 20,
                "fixed_counts": {"q3": 5, "q4": 4, "q5": 2},
                "quality_cells": {"q3": 12, "q4": 10},
                "avg_cells": {"q1": 2.0, "q6": 3.0},
            },
        )
    )

    assert evidence.total_grid_target == 44.0
    assert RESIDUAL_AVG_CELLS_NOTE in evidence.source_notes
    assert TOTAL_GRID_FROM_HIGH_TIER_CELLS_NOTE in evidence.source_notes


def test_ref_engine_aisha_layout_grid_hint_raises_target_from_deep_minimap() -> None:
    snapshot = _snapshot(
        hero="aisha",
        map_id=2501,
        structured_ref_inputs={"total_count": 25},
    )
    snapshot["ui_contract"]["context"]["round"] = 3
    snapshot["audit_aisha_layout_mode"] = "target"
    snapshot["minimap_grid_items"] = [
        {"quality": 3, "row": 14, "width": 2, "height": 1, "cells": 8},
        {"quality": 4, "row": 12, "width": 3, "height": 2, "cells": 15},
    ]
    evidence = extract_evidence(snapshot)

    assert evidence.total_grid_target == 38.0
    assert AISHA_LAYOUT_GRID_HINT_NOTE in evidence.source_notes
    assert AISHA_LAYOUT_FOOTROOM_NOTE in evidence.source_notes
    assert AISHA_LAYOUT_FOOTROOM_CAP_NOTE in evidence.source_notes
    assert AISHA_LAYOUT_FOOTROOM_SPARSE_NOTE in evidence.source_notes
    assert any(
        note.startswith(f"{AISHA_LAYOUT_FOOTROOM_MULT_NOTE}:")
        for note in evidence.source_notes
    )


def test_ref_engine_aisha_layout_grid_hint_skips_when_hard_total_cells_present() -> None:
    snapshot = _snapshot(
        hero="aisha",
        map_id=2501,
        structured_ref_inputs={"total_count": 25, "total_cells": 120},
    )
    snapshot["ui_contract"]["context"]["round"] = 5
    snapshot["minimap_grid_items"] = [
        {"quality": 5, "row": 16, "width": 3, "height": 2, "cells": 40},
        {"quality": 4, "row": 15, "width": 2, "height": 2, "cells": 30},
    ]
    evidence = extract_evidence(snapshot)

    assert evidence.total_grid_target == 120.0
    assert AISHA_LAYOUT_GRID_HINT_NOTE not in evidence.source_notes


def test_aisha_layout_target_looks_undershot_rejects_high_soft_target() -> None:
    from ahmad_ref_engine import _aisha_layout_target_looks_undershot

    assert not _aisha_layout_target_looks_undershot(
        total_grid_target=120.0,
        known_cells=70,
        rows_below=1,
        columns=10,
        round_no=5,
    )
    assert _aisha_layout_target_looks_undershot(
        total_grid_target=70.0,
        known_cells=70,
        rows_below=8,
        columns=10,
        round_no=3,
    )


def test_ref_engine_aisha_layout_band_mode_widens_high_bound_only() -> None:
    snapshot = _snapshot(
        hero="aisha",
        map_id=2501,
        structured_ref_inputs={"total_count": 25},
    )
    snapshot["ui_contract"]["context"]["round"] = 3
    snapshot["audit_aisha_layout_mode"] = "band"
    snapshot["minimap_grid_items"] = [
        {"quality": 3, "row": 14, "width": 2, "height": 1, "cells": 8},
        {"quality": 4, "row": 12, "width": 3, "height": 2, "cells": 15},
    ]
    off = run_reference_engine({**snapshot, "audit_aisha_layout_mode": "off"}, max_combos=20_000).as_dict()
    band = run_reference_engine(snapshot, max_combos=20_000).as_dict()
    off_evidence = off.get("evidence") if isinstance(off.get("evidence"), dict) else {}
    band_evidence = band.get("evidence") if isinstance(band.get("evidence"), dict) else {}

    assert off_evidence.get("total_grid_target") == band_evidence.get("total_grid_target")
    assert band["total_grid_range"][2] >= off["total_grid_range"][2]
    assert "aisha_layout_band_widen_applied" in band["notes"]


def test_ref_engine_aisha_layout_shadow_mode_keeps_target() -> None:
    snapshot = _snapshot(
        hero="aisha",
        map_id=2501,
        structured_ref_inputs={"total_count": 25},
    )
    snapshot["ui_contract"]["context"]["round"] = 3
    snapshot["audit_aisha_layout_mode"] = "shadow"
    snapshot["minimap_grid_items"] = [
        {"quality": 3, "row": 14, "width": 2, "height": 1, "cells": 8},
        {"quality": 4, "row": 12, "width": 3, "height": 2, "cells": 15},
    ]
    off = run_reference_engine({**snapshot, "audit_aisha_layout_mode": "off"}, max_combos=20_000).as_dict()
    shadow = run_reference_engine(snapshot, max_combos=20_000).as_dict()

    assert shadow["evidence"]["total_grid_target"] == off["evidence"]["total_grid_target"]
    assert AISHA_LAYOUT_GRID_HINT_NOTE in shadow["notes"]
    assert "aisha_layout_application_mode:shadow" in shadow["notes"]
    assert off["total_grid_range"] == shadow["total_grid_range"]


def test_ref_engine_aisha_layout_grid_hint_skips_round_two_white_only() -> None:
    snapshot = _snapshot(
        hero="aisha",
        map_id=2501,
        structured_ref_inputs={"total_count": 25},
    )
    snapshot["ui_contract"]["context"]["round"] = 2
    snapshot["minimap_grid_items"] = [
        {"quality": 1, "row": 15, "width": 2, "height": 1, "cells": 6},
    ]
    evidence = extract_evidence(snapshot)

    assert evidence.total_grid_target is None
    assert AISHA_LAYOUT_GRID_HINT_NOTE not in evidence.source_notes


def test_ref_engine_aisha_layout_grid_hint_skips_white_only_through_round_three() -> None:
    snapshot = _snapshot(
        hero="aisha",
        map_id=2501,
        structured_ref_inputs={"total_count": 25},
    )
    snapshot["ui_contract"]["context"]["round"] = 3
    snapshot["minimap_grid_items"] = [
        {"quality": 1, "row": 15, "width": 2, "height": 1, "cells": 6},
    ]
    evidence = extract_evidence(snapshot)

    assert evidence.total_grid_target is None
    assert AISHA_LAYOUT_GRID_HINT_NOTE not in evidence.source_notes


HIDDEN_2601_SLOW_SAMPLE = (
    FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2601_3rounds_2601_1295018740835056_0215.json"
)


def _aisha_fatbeans_snapshot_at_round(
    sample_path: Path,
    *,
    round_count: int | None = None,
    include_minimap: bool = False,
) -> dict:
    from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events, parse_fatbeans_capture
    from bidking_lab.live.monitor import (
        _ahmad_ref_inputs_from_batches,
        _minimap_grid_items,
        _public_info_rows,
        _skill_reveal_rows,
        load_monitor_tables,
    )

    events = parse_fatbeans_capture(sample_path)
    batches = [batch for batch in live_batches_from_fatbeans_events(events) if batch.phase != "settled"]
    if round_count is None:
        round_count = max(3, len(batches) - 1)
    prefix = batches[:round_count]
    sort_id = max(int(batch.sequence or 0) for batch in prefix if batch.sequence is not None)
    prefix_events = events
    if sort_id:
        prefix_events = type(events)(
            packets=tuple(row for row in events.packets if int(row.sort_id) <= sort_id),
            frames=tuple(row for row in events.frames if int(row.sort_id) <= sort_id),
            sends=tuple(row for row in events.sends if int(row.sort_id) <= sort_id),
            states=tuple(row for row in events.states if int(row.sort_id) <= sort_id),
            statuses=tuple(row for row in events.statuses if int(row.sort_id) <= sort_id),
        )
    map_id = None
    marker = sample_path.name.split("_")
    for part in marker:
        if part.isdigit() and len(part) == 4 and part.startswith(("21", "22", "23", "24", "25", "26", "45")):
            map_id = int(part)
            break
    snapshot = {
        "ui_contract": {
            "context": {
                "hero": "aisha",
                "phase": "bidding",
                "round": int(round_count),
                "map_id": map_id,
            },
            "constraints": {"public_info": {}},
        },
        "structured_ref_inputs": _ahmad_ref_inputs_from_batches(prefix, hero="aisha") or {},
        "public_info_rows": _public_info_rows(prefix_events, {}),
        "skill_reveals": _skill_reveal_rows(prefix_events, {}),
        "skill_reveal_rows": _skill_reveal_rows(prefix_events, {}),
        "action_result_rows": [],
        "map_id": map_id,
    }
    if include_minimap:
        tables = load_monitor_tables()
        snapshot["minimap_grid_items"] = _minimap_grid_items(prefix, tables.items)
    return snapshot


def test_ref_engine_pinned_quality_cells_sparse_prior_routes_fast_on_hidden_sample() -> None:
    if not HIDDEN_2601_SLOW_SAMPLE.exists():
        pytest.skip("hidden fatbeans sample missing")
    snapshot = _aisha_fatbeans_snapshot_at_round(HIDDEN_2601_SLOW_SAMPLE)
    started = time.perf_counter()
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    assert elapsed_ms < 2000.0
    assert result["status"] == "count_prior"
    assert PINNED_QUALITY_CELLS_SPARSE_PRIOR_NOTE in result["notes"]
    assert "sparse_exact_total_prior_enumeration" in result["notes"]
    assert result["combo_count"] < 500


def test_ref_engine_hidden_high_total_early_round_stays_under_perf_gate() -> None:
    if not HIDDEN_2601_SLOW_SAMPLE.exists():
        pytest.skip("hidden fatbeans sample missing")
    snapshot = _aisha_fatbeans_snapshot_at_round(HIDDEN_2601_SLOW_SAMPLE, round_count=3)
    started = time.perf_counter()
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    assert elapsed_ms < 2000.0
    assert result["status"] == "count_prior"
    assert "sparse_exact_high_total_tight_prior" in result["notes"]
    assert result["combo_count"] < 500


AISHA_0052_SAMPLE = (
    FATBEANS_SAMPLE_DIR / "fatbeans_valid_aisha_2402_3rounds_2402_1367586310602652_0052.json"
)


def test_ref_engine_aisha_0052_fatbeans_r3_live_bridge_regression() -> None:
    """Batch B #3: white/green split bridge + public q4 avg must stay reachable at r3."""
    snapshot = _aisha_fatbeans_snapshot(AISHA_0052_SAMPLE, round_count=3)
    result = run_reference_engine(snapshot, max_combos=50_000).as_dict()
    evidence = result["evidence"]

    assert result["status"] == "count_prior"
    assert result["combo_count"] == 2421
    assert result["balanced"] == 292_763
    assert evidence["split_counts"] == {"green": 7, "white": 4}
    assert evidence["split_quality_cells"] == {"green": 10.0, "white": 8.0}
    assert evidence["fixed_counts"].get("q1") == 11
    assert "split_low_quality_q1_count_merged" in result["notes"]
    assert result["quality_count_ranges"]["q3"] == [6, 8, 11]
    assert result["quality_count_ranges"]["q4"] == [3, 6, 9]
