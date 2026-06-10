from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AHMAD_SRC = ROOT / "external_references" / "ahmad_live_reference_lab" / "src"
if str(AHMAD_SRC) not in sys.path:
    sys.path.insert(0, str(AHMAD_SRC))

from ahmad_ref_engine import (  # noqa: E402
    _avg_grid_options,
    _fit_grids_to_total_target,
    can_compose_grid_total,
    extract_evidence,
    run_reference_engine,
)


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

    assert evidence.min_counts["q4"] == 1
    assert "q4" not in evidence.fixed_counts
    assert "q4" not in evidence.quality_cells
    assert "public_quality_reveal_min_counts" in evidence.source_notes
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

    assert result["status"] == "count_prior"
    assert result["quality_count_ranges"]["q4"] == [8, 8, 8]
    assert "public_q4_avg_value" in result["notes"]


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
    assert evidence.quality_values == {}
    assert evidence.fixed_counts == {}
    assert evidence.min_counts == {}


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

    assert result["status"] == "ok"
    assert evidence["hero"] == "aisha"
    assert evidence["split_counts"] == {"white": 3, "green": 4}
    assert evidence["split_quality_cells"] == {"white": 5.0, "green": 8.0}
    assert evidence["fixed_counts"]["q1"] == 7
    assert evidence["quality_cells"]["q1"] == 13.0
    assert evidence["avg_cells"]["q1"] == 13.0 / 7.0
    assert "split_low_quality_q1_count_merged" in result["notes"]
    assert "split_low_quality_q1_cells_merged" in result["notes"]


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
