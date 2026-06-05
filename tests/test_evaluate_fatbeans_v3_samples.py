import importlib.util
from pathlib import Path
from types import SimpleNamespace

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropEntry, DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.inference.v3.calibration import propose_prior_calibration
from bidking_lab.live.fatbeans import FatbeansCaptureEvents

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts" / "evaluate_fatbeans_v3_samples.py"
    spec = importlib.util.spec_from_file_location("evaluate_fatbeans_v3_samples", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _item(
    item_id: int,
    *,
    quality: int,
    value: int,
    shape: tuple[int, int],
) -> Item:
    width, height = shape
    return Item(
        item_id=item_id,
        name=f"item_{item_id}",
        description="",
        name_key=f"item_{item_id}",
        desc_key=f"item_{item_id}_desc",
        quality=quality,
        quality_color="",
        value=value,
        shape_w=width,
        shape_h=height,
        tags=[],
        allowed_shelves=[],
        icon_name="",
        model_name="",
        raw_row=[],
    )


def _tables() -> SimpleNamespace:
    filler = _item(1011001, quality=1, value=1_000, shape=(1, 1))
    red = _item(1086001, quality=6, value=200_000, shape=(4, 4))
    return SimpleNamespace(
        maps={
            2401: BidMap(
                map_id=2401,
                name="test_map",
                description="",
                category=101,
                auction_mode="open",
                sub_pool_weights=[],
                rounds_total=5,
                entry_fee_silver=0,
                starting_budget_silver=100_000,
                drop_pool_id=9001,
                items_per_session_min=2,
                items_per_session_max=2,
                value_tier_ui="",
                mode_flag=4,
                bid_price_ladder=[],
                raw_row=[],
            ),
        },
        drops={
            9001: DropPool(
                pool_id=9001,
                name="pool",
                description="",
                pool_type=2,
                entries=[
                    DropEntry(
                        category=101,
                        item_id=filler.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    ),
                    DropEntry(
                        category=108,
                        item_id=red.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    ),
                ],
            ),
        },
        items={filler.item_id: filler, red.item_id: red},
    )


def test_v3_prebid_rows_compile_ready_constraints() -> None:
    module = _load_module()
    state = SimpleNamespace(
        sort_id=5,
        session_id="2401:abc",
        round_index=1,
        map_id=2401,
        public_infos=(
            SimpleNamespace(
                info_id=200009,
                value=98,
                value_field=14,
                observed_items=(),
            ),
        ),
        action_results=(),
        skill_reveals=(),
        inventory_items=(),
    )
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(SimpleNamespace(sort_id=10, kind="bid", session_id="2401:abc", value=1000),),
        states=(state,),
        statuses=(),
    )

    rows = module._round_rows_for_events(Path("sample.json"), events)

    assert len(rows) == 1
    assert rows[0]["status"] == "ready"
    assert rows[0]["map_family"] == "villa"
    assert rows[0]["numeric_constraints"] == 1
    assert rows[0]["constraint_ok"] is True


def test_v3_prebid_rows_include_prior_and_truth_shadow_fields() -> None:
    module = _load_module()
    prebid_state = SimpleNamespace(
        sort_id=5,
        session_id="2401:abc",
        round_index=1,
        map_id=2401,
        public_infos=(),
        action_results=(),
        skill_reveals=(),
        inventory_items=(),
    )
    settlement_state = SimpleNamespace(
        sort_id=20,
        session_id="2401:abc",
        round_index=5,
        map_id=2401,
        public_infos=(),
        action_results=(),
        skill_reveals=(),
        inventory_items=(
            SimpleNamespace(item_id=1011001, quality=1, cells=1),
            SimpleNamespace(item_id=1086001, quality=6, cells=16),
        ),
    )
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(SimpleNamespace(sort_id=10, kind="bid", session_id="2401:abc", value=1000),),
        states=(prebid_state, settlement_state),
        statuses=(),
    )

    rows = module._round_rows_for_events(
        Path("sample.json"),
        events,
        tables=_tables(),
        posterior_trials=64,
    )

    assert len(rows) == 1
    assert rows[0]["v3_prior_available"] is True
    assert rows[0]["v3_prior_expected_value"] == 201_000
    assert rows[0]["v3_prior_q6_session_probability"] == 0.75
    assert rows[0]["v3_truth_available"] is True
    assert rows[0]["v3_truth_raw_total_value"] == 201_000
    assert rows[0]["v3_truth_q6_raw_value"] == 200_000
    assert rows[0]["v3_truth_decision_available"] is True
    assert rows[0]["v3_truth_formal_decision_value"] == 201_000
    assert rows[0]["v3_truth_tail_replacement_decision_value"] == 201_000
    assert rows[0]["v3_summary_available"] is True
    assert rows[0]["v3_summary_feasible"] is True
    assert rows[0]["v3_summary_known_count_floor"] == 0
    assert rows[0]["v3_post_available"] is True
    assert rows[0]["v3_post_affects_bid"] is False
    assert rows[0]["v3_post_match_scope"] == "strict"
    assert rows[0]["v3_post_n_total"] == 64
    assert rows[0]["v3_post_formal_decision_value_p50"] is not None
    assert rows[0]["v3_post_q6_formal_decision_value_p50"] is not None
    assert rows[0]["v3_ccv_available"] is True
    assert rows[0]["v3_ccv_affects_bid"] is False
    assert rows[0]["v3_ccv_ready"] is True
    assert rows[0]["v3_resid_available"] is True
    assert rows[0]["v3_resid_affects_bid"] is False
    assert rows[0]["v3_resid_ready"] is True
    assert rows[0]["v3_cal_available"] is True
    assert rows[0]["v3_cal_affects_bid"] is False
    assert rows[0]["v3_cal_active"] is False
    assert rows[0]["v3_cal_status"] == "missing_entry"


def test_v3_prebid_rows_apply_calibration_shadow_fields() -> None:
    module = _load_module()
    prebid_state = SimpleNamespace(
        sort_id=5,
        session_id="2401:abc",
        round_index=1,
        map_id=2401,
        public_infos=(),
        action_results=(),
        skill_reveals=(),
        inventory_items=(),
    )
    settlement_state = SimpleNamespace(
        sort_id=20,
        session_id="2401:abc",
        round_index=5,
        map_id=2401,
        public_infos=(),
        action_results=(),
        skill_reveals=(),
        inventory_items=(
            SimpleNamespace(item_id=1011001, quality=1, cells=1),
            SimpleNamespace(item_id=1086001, quality=6, cells=16),
        ),
    )
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(SimpleNamespace(sort_id=10, kind="bid", session_id="2401:abc", value=1000),),
        states=(prebid_state, settlement_state),
        statuses=(),
    )
    entry = propose_prior_calibration(
        map_id=2401,
        map_family="villa",
        archive_sessions=70,
        median_ratio=1.5,
        p90_ratio=1.2,
        formal_p50_over_rate=0.4,
        baseline_formal_p50_mae=100_000,
        baseline_formal_p50_bias=-60_000,
    )

    rows = module._round_rows_for_events(
        Path("sample.json"),
        events,
        tables=_tables(),
        calibration_entries={2401: entry},
        posterior_trials=64,
    )

    assert rows[0]["v3_cal_available"] is True
    assert rows[0]["v3_cal_active"] is True
    assert rows[0]["v3_cal_affects_bid"] is False
    assert rows[0]["v3_cal_scale"] > 1.0
    assert rows[0]["v3_cal_formal_decision_value_p50"] >= rows[0][
        "v3_post_formal_decision_value_p50"
    ]


def test_v3_summary_metrics_use_formal_truth_and_prediction() -> None:
    module = _load_module()
    rows = [
        {
            "status": "ready",
            "v3_truth_decision_available": True,
            "v3_truth_available": True,
            "v3_post_ready": True,
            "v3_post_match_scope": "strict",
            "v3_truth_formal_decision_value": 100,
            "v3_post_formal_decision_value_p50": 90,
            "v3_post_formal_decision_value_p90": 120,
            "v3_truth_q6_formal_decision_value": 30,
            "v3_post_q6_formal_decision_value_p50": 10,
            "v3_post_q6_formal_decision_value_p90": 40,
            "v3_truth_q6_count": 1,
            "v3_truth_q6_cells": 4,
            "v3_truth_q6_raw_value": 100,
            "v3_post_q6_count_p50": 0,
            "v3_post_q6_count_p90": 1,
            "v3_post_q6_cells_p50": 2,
            "v3_post_q6_cells_p90": 4,
            "v3_post_q6_value_p50": 80,
            "v3_ccv_ready": True,
            "v3_ccv_match_scope": "ccv_likelihood",
            "v3_ccv_q6_count_p50": 1,
            "v3_ccv_q6_count_p90": 1,
            "v3_ccv_q6_cells_p50": 4,
            "v3_ccv_q6_cells_p90": 4,
            "v3_resid_ready": True,
            "v3_resid_match_scope": "residual_likelihood",
            "v3_resid_q6_count_p50": 1,
            "v3_resid_q6_count_p90": 1,
            "v3_resid_q6_cells_p50": 4,
            "v3_resid_q6_cells_p90": 4,
            "v3_resid_q6_value_p50": 100,
        },
        {
            "status": "ready",
            "v3_truth_decision_available": True,
            "v3_truth_available": True,
            "v3_post_ready": True,
            "v3_post_match_scope": "q6_projection",
            "v3_truth_formal_decision_value": 200,
            "v3_post_formal_decision_value_p50": 250,
            "v3_post_formal_decision_value_p90": 260,
            "v3_truth_q6_formal_decision_value": 0,
            "v3_post_q6_formal_decision_value_p50": 0,
            "v3_post_q6_formal_decision_value_p90": 0,
            "v3_truth_q6_count": 0,
            "v3_truth_q6_cells": 0,
            "v3_truth_q6_raw_value": 0,
            "v3_post_q6_count_p50": 1,
            "v3_post_q6_count_p90": 1,
            "v3_post_q6_cells_p50": 5,
            "v3_post_q6_cells_p90": 5,
            "v3_post_q6_value_p50": 50,
            "v3_ccv_ready": True,
            "v3_ccv_match_scope": "q6_projection",
            "v3_ccv_q6_count_p50": 0,
            "v3_ccv_q6_count_p90": 0,
            "v3_ccv_q6_cells_p50": 0,
            "v3_ccv_q6_cells_p90": 0,
            "v3_resid_ready": True,
            "v3_resid_match_scope": "q6_projection",
            "v3_resid_q6_count_p50": 0,
            "v3_resid_q6_count_p90": 0,
            "v3_resid_q6_cells_p50": 0,
            "v3_resid_q6_cells_p90": 0,
            "v3_resid_q6_value_p50": 0,
            "v3_cal_ready": True,
            "v3_cal_active": True,
            "v3_cal_formal_decision_value_p50": 220,
            "v3_cal_formal_decision_value_p90": 260,
            "v3_cal_q6_formal_decision_value_p50": 0,
            "v3_cal_q6_formal_decision_value_p90": 0,
        },
    ]

    summary = module.summarize_rows(rows, [])

    assert summary["metric_rows"] == 2
    assert summary["metric_strict_rows"] == 1
    assert summary["metric_fallback_rows"] == 1
    assert summary["formal_p50_mae"] == 30
    assert summary["formal_p50_mae_strict"] == 10
    assert summary["formal_p50_mae_fallback"] == 50
    assert summary["formal_p50_bias"] == 20
    assert summary["formal_p50_below_rate"] == 0.5
    assert summary["formal_p50_over_rate"] == 0.5
    assert summary["formal_p50_pinball"] == 15
    assert summary["formal_p90_coverage"] == 1.0
    assert summary["formal_p90_coverage_strict"] == 1.0
    assert summary["formal_p90_coverage_fallback"] == 1.0
    assert summary["formal_p90_pinball"] == 4
    assert summary["q6_formal_p50_mae"] == 10
    assert summary["q6_formal_p50_mae_strict"] == 20
    assert summary["q6_formal_p50_mae_fallback"] == 0
    assert summary["q6_formal_p50_bias"] == -10
    assert summary["q6_formal_p50_over_rate"] == 0.0
    assert summary["q6_formal_p90_pinball"] == 0.5
    assert summary["q6_count_p50_mae"] == 1
    assert summary["q6_cells_p50_mae"] == 3.5
    assert summary["v3_ccv_likelihood_rows"] == 1
    assert summary["v3_ccv_q6_count_p50_mae"] == 0
    assert summary["v3_ccv_delta_q6_count_p50_mae"] == -1
    assert summary["v3_ccv_q6_cells_p50_mae"] == 0
    assert summary["v3_ccv_delta_q6_cells_p50_mae"] == -3.5
    assert summary["q6_value_p50_mae"] == 35
    assert summary["v3_resid_likelihood_rows"] == 1
    assert summary["v3_resid_q6_count_p50_mae"] == 0
    assert summary["v3_resid_delta_q6_count_p50_mae"] == -1
    assert summary["v3_resid_q6_cells_p50_mae"] == 0
    assert summary["v3_resid_delta_q6_cells_p50_mae"] == -3.5
    assert summary["v3_resid_q6_value_p50_mae"] == 0
    assert summary["v3_resid_delta_q6_value_p50_mae"] == -35
    assert summary["v3_cal_metric_rows"] == 1
    assert summary["v3_cal_active_rows"] == 1
    assert summary["v3_cal_formal_p50_mae"] == 20
    assert summary["v3_cal_delta_formal_p50_mae"] == -10


def test_v3_prebid_rows_separate_no_state_windows() -> None:
    module = _load_module()
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(SimpleNamespace(sort_id=10, kind="bid", session_id="2401:abc", value=1000),),
        states=(),
        statuses=(),
    )

    rows = module._round_rows_for_events(Path("sample.json"), events)

    assert len(rows) == 1
    assert rows[0]["status"] == "no_state"
    assert rows[0]["map_family"] == "unknown"
    assert rows[0]["numeric_constraints"] == 0
    assert rows[0]["constraint_ok"] is False
