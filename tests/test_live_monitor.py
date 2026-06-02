from __future__ import annotations

import json
from pathlib import Path

import pytest

import bidking_lab.live.monitor as monitor_module
from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropEntry, DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.live.fatbeans import (
    FatbeansActionResult,
    FatbeansCaptureEvents,
    FatbeansInventoryItem,
    FatbeansObservedItem,
    FatbeansPlayerBid,
    FatbeansStateEvent,
)
from bidking_lab.live.monitor import (
    DEFAULT_Q6_SHADOW_TRIALS_CAP,
    MonitorTables,
    _build_zero_match_fallback_rows,
    _model_eval_row,
    _resolve_shadow_trials,
    build_monitor_artifact_from_file,
    build_monitor_artifact_from_events,
    load_monitor_tables,
    write_monitor_logs,
)
from bidking_lab.inference.observation import QualityBucketObs, SessionObs


def _item() -> Item:
    return Item(
        item_id=1001,
        name="test_item",
        description="",
        name_key="test_item",
        desc_key="test_item_desc",
        quality=4,
        quality_color="purple",
        value=20_000,
        shape_w=2,
        shape_h=2,
        tags=[107],
        allowed_shelves=[],
        icon_name="",
        model_name="",
        raw_row=[],
    )


def _tables() -> MonitorTables:
    item = _item()
    return MonitorTables(
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
                items_per_session_min=1,
                items_per_session_max=1,
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
                entries=(
                    DropEntry(
                        category=107,
                        item_id=item.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    ),
                ),
            ),
        },
        items={item.item_id: item},
    )


def _two_item_tables() -> MonitorTables:
    first = Item(
        item_id=1001,
        name="test_item",
        description="",
        name_key="test_item",
        desc_key="test_item_desc",
        quality=4,
        quality_color="purple",
        value=20_000,
        shape_w=1,
        shape_h=1,
        tags=[107],
        allowed_shelves=[],
        icon_name="",
        model_name="",
        raw_row=[],
    )
    second = Item(
        item_id=1002,
        name="test_item_2",
        description="",
        name_key="test_item_2",
        desc_key="test_item_2_desc",
        quality=4,
        quality_color="purple",
        value=10_000,
        shape_w=1,
        shape_h=1,
        tags=[107],
        allowed_shelves=[],
        icon_name="",
        model_name="",
        raw_row=[],
    )
    return MonitorTables(
        maps={
            2401: BidMap(
                map_id=2401,
                name="two_item_map",
                description="",
                category=101,
                auction_mode="open",
                sub_pool_weights=[],
                rounds_total=5,
                entry_fee_silver=0,
                starting_budget_silver=100_000,
                drop_pool_id=9001,
                items_per_session_min=1,
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
                entries=(
                    DropEntry(
                        category=107,
                        item_id=first.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    ),
                    DropEntry(
                        category=107,
                        item_id=second.item_id,
                        n_min=1,
                        n_max=1,
                        weight=1,
                    ),
                ),
            ),
        },
        items={first.item_id: first, second.item_id: second},
    )


def _events() -> FatbeansCaptureEvents:
    return FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(),
        statuses=(),
        states=(
            FatbeansStateEvent(
                sort_id=1,
                capture_time="",
                message_id=0x002D,
                session_id="s1",
                map_id=2401,
                round_index=5,
                bids=(
                    FatbeansPlayerBid(
                        player_id=1,
                        name="leader",
                        hero_id=103,
                        values=(12_000, 15_000),
                    ),
                ),
                inventory_items=(
                    FatbeansInventoryItem(
                        runtime_id=101,
                        item_id=1001,
                        quality=4,
                        cells=4,
                    ),
                ),
            ),
        ),
    )


def test_build_monitor_artifact_includes_panel_and_eval() -> None:
    artifact = build_monitor_artifact_from_events(
        _events(),
        file="sample.json",
        tables=_tables(),
        n_trials=10,
        roi_trials=0,
    )

    assert artifact["file"] == "sample.json"
    assert artifact["n_trials"] == 10
    assert artifact["roi_trials"] == 0
    assert artifact["shadow_trials"] == 10
    assert artifact["processing_seconds"] >= 0
    assert artifact["hero"] == "aisha"
    assert artifact["map_id"] == 2401
    assert artifact["known_value_sum"] == 20_000
    assert artifact["final_q6_count"] == 0
    assert artifact["inference_input_constraints"]["mode"] == "session_totals_stripped"
    assert "total_item_count" not in artifact["inference_input_constraints"]
    assert artifact["latest_bids"] == {"leader": 15_000}
    assert artifact["warehouse_rows"]
    assert artifact["v2_posterior_rows"]
    assert artifact["q6_residual_boost_shadow"]["label"] == "profile_b5"
    assert artifact["q6_residual_boost_shadow"]["gate"] == "shipwreck_profile_v1"
    assert artifact["q6_residual_boost_shadow"]["trials"] == 10
    assert artifact["q6_residual_boost_shadow"]["active"] is False
    assert artifact["q6_residual_deep_floor_shadow"]["label"] == "aisha_deep_floor1"
    assert (
        artifact["q6_residual_deep_floor_shadow"]["gate"]
        == "aisha_shipwreck_deep_v1"
    )
    assert artifact["q6_residual_deep_floor_shadow"]["trials"] == 10
    assert artifact["q6_residual_deep_floor_shadow"]["active"] is False
    assert (
        artifact["q6_residual_hidden_floor_shadow"]["label"]
        == "aisha_hidden_floor15"
    )
    assert artifact["q6_residual_hidden_floor_shadow"]["gate"] == "aisha_hidden_v1"
    assert artifact["q6_residual_hidden_floor_shadow"]["trials"] == 10
    assert artifact["q6_residual_hidden_floor_shadow"]["active"] is False
    assert artifact["q6_residual_villa_floor_shadow"]["label"] == (
        "aisha_villa_floor05"
    )
    assert artifact["q6_residual_villa_floor_shadow"]["gate"] == (
        "aisha_villa_shape_layout_v1"
    )
    assert artifact["q6_residual_villa_floor_shadow"]["trials"] == 10
    assert artifact["q6_residual_villa_floor_shadow"]["active"] is False
    assert [row["策略"] for row in artifact["q6_residual_boost_shadow_rows"]] == [
        "profile_b5",
        "aisha_deep_floor1",
        "aisha_hidden_floor15",
        "aisha_villa_floor05",
    ]
    assert artifact["q6_residual_boost_shadow_rows"]
    assert "q6先验缺口" in artifact["v2_posterior_rows"][0]
    assert "q6先验风险参考" in artifact["v2_posterior_rows"][0]
    assert "q6先验风险" in artifact["v2_posterior_rows"][0]
    assert "q6实战门控" in artifact["v2_posterior_rows"][0]
    assert "q6实战参考P90" in artifact["v2_posterior_rows"][0]
    assert "category_grid_items" in artifact
    assert "minimap_grid_items" in artifact
    assert artifact["minimap_grid_items"][0]["item_name"] == "test_item"
    assert artifact["bid_rows"]
    assert artifact["bid_rows"][0]["价值口径"] == "decision_value"
    assert artifact["bid_rows"][0]["决策价值 P10/P50/P90"]
    assert artifact["bid_rows"][0]["原始价值 P10/P50/P90"]
    assert "上界风险" in artifact["bid_rows"][0]
    assert artifact["panel"]["summary_rows"]
    assert artifact["ui_contract"]["schema_version"] == 1
    assert artifact["ui_contract"]["mode"] == "baseline_first_shadow_reference"
    assert artifact["ui_contract"]["baseline"]["official"] is True
    assert artifact["ui_contract"]["baseline"]["affects_bid"] is True
    assert artifact["ui_contract"]["baseline"]["posterior"][
        "total_item_count_status"
    ] == "not_estimated_by_v2"
    assert artifact["ui_contract"]["q6_risk_reference"]["affects_bid"] is False
    assert [
        shadow["label"]
        for shadow in artifact["ui_contract"]["shadows"]
    ] == [
        "profile_b5",
        "aisha_deep_floor1",
        "aisha_hidden_floor15",
        "aisha_villa_floor05",
    ]
    assert all(
        shadow["affects_bid"] is False
        for shadow in artifact["ui_contract"]["shadows"]
    )
    assert artifact["model_eval"]["final_value"] == 20_000
    assert artifact["model_eval"]["final_cells"] == 4
    assert artifact["model_eval"]["hero"] == "aisha"
    assert artifact["model_eval"]["final_q6_count"] == 0
    assert artifact["model_eval"]["final_top_item_name"] == "test_item"
    assert artifact["model_eval"]["final_top_item_value"] == 20_000
    assert artifact["model_eval"]["decision_value_p50"] == 20_000
    assert artifact["model_eval"]["monitor_n_trials"] == 10
    assert artifact["model_eval"]["monitor_roi_trials"] == 0
    assert artifact["model_eval"]["monitor_shadow_trials"] == 10
    assert artifact["model_eval"]["monitor_processing_seconds"] >= 0
    assert artifact["model_eval"]["input_constraints_mode"] == (
        "session_totals_stripped"
    )
    assert artifact["model_eval"]["input_total_item_count"] is None
    assert artifact["model_eval"]["q6_top_size_band"] == "no_q6"
    assert "v2_q6_value_p90_under_by" in artifact["model_eval"]
    assert "q6_count_cell_prior_risk" in artifact["model_eval"]
    assert "q6_count_cell_prior_gap" in artifact["model_eval"]
    assert "q6_count_cell_prior_floor_value" in artifact["model_eval"]
    assert "q6_practical_gate" in artifact["model_eval"]
    assert "q6_practical_p90" in artifact["model_eval"]
    assert "q6_practical_gate_hit" in artifact["model_eval"]
    assert "q6_practical_gate_false_positive_proxy" in artifact["model_eval"]
    assert "q6_practical_gate_under_before" in artifact["model_eval"]
    assert "q6_practical_gate_covered_after" in artifact["model_eval"]
    assert "q6_practical_gate_helped" in artifact["model_eval"]
    assert "q6_practical_p90_under_by" in artifact["model_eval"]
    assert "q6_residual_boost_shadow_active" in artifact["model_eval"]
    assert "q6_residual_boost_shadow_q6_p90_delta" in artifact["model_eval"]
    assert artifact["model_eval"]["q6_residual_boost_shadow_active"] is False
    assert artifact["model_eval"]["q6_residual_boost_shadow_trials"] == 10
    assert "q6_residual_deep_floor_shadow_active" in artifact["model_eval"]
    assert artifact["model_eval"]["q6_residual_deep_floor_shadow_trials"] == 10
    assert "q6_residual_deep_floor_shadow_q6_p90_delta" in artifact["model_eval"]
    assert artifact["model_eval"]["q6_residual_deep_floor_shadow_active"] is False
    assert "q6_residual_hidden_floor_shadow_active" in artifact["model_eval"]
    assert artifact["model_eval"]["q6_residual_hidden_floor_shadow_trials"] == 10
    assert (
        "q6_residual_hidden_floor_shadow_q6_p90_delta"
        in artifact["model_eval"]
    )
    assert artifact["model_eval"]["q6_residual_hidden_floor_shadow_active"] is False
    assert "q6_residual_villa_floor_shadow_active" in artifact["model_eval"]
    assert artifact["model_eval"]["q6_residual_villa_floor_shadow_trials"] == 10
    assert (
        "q6_residual_villa_floor_shadow_q6_p90_delta"
        in artifact["model_eval"]
    )
    assert artifact["model_eval"]["q6_residual_villa_floor_shadow_active"] is False
    assert "raw_minus_decision_p90" in artifact["model_eval"]
    assert "layout_conflict_root" in artifact["model_eval"]
    assert "shape_target_count" in artifact["model_eval"]
    assert "category_target_count" in artifact["model_eval"]
    assert "category_exclusion_count" in artifact["model_eval"]
    assert "anchor_count" in artifact["model_eval"]
    assert "random_sample_avg_values" in artifact["model_eval"]
    assert "random_sample_avg_signal_values" in artifact["model_eval"]
    assert "public_constraint_key" in artifact["model_eval"]
    assert "evidence_profile_key" in artifact["model_eval"]
    assert "q6_aisha_bottom_row_risk" in artifact["model_eval"]
    assert "layout_bottom_row" in artifact["model_eval"]
    assert artifact["model_eval"]["evidence_stage"] == "full_5"
    assert artifact["model_eval"]["information_density_band"] in {
        "low",
        "medium",
        "high",
    }
    assert "hero_information_density" in artifact["model_eval"]
    assert artifact["model_eval"]["relaxed_exact_used"] is False


def test_model_eval_uses_problem_evidence_profile_when_available() -> None:
    row = _model_eval_row(
        file="sample.json",
        artifact={
            "file": "sample.json",
            "hero": "aisha",
            "map_id": 2501,
            "round": 3,
            "evidence_profile_key": "shape+layout",
            "bid_rows": [
                {
                    "决策价值 P10/P50/P90": "100 / 200 / 300",
                    "原始价值 P10/P50/P90": "100 / 200 / 300",
                },
            ],
            "warehouse_rows": [{"价值 P10/P50/P90": "100 / 200 / 300"}],
            "v2_posterior_rows": [
                {
                    "形状约束数": 2,
                    "分类约束数": 0,
                    "分类反排数": 0,
                    "诊断": "",
                },
            ],
        },
        final_value=200,
        final_cells=10,
        truth_breakdown={},
    )

    assert row is not None
    assert row["evidence_profile_key"] == "shape+layout"


def test_debug_shadow_can_be_skipped_without_suppressing_baseline(monkeypatch) -> None:
    original_estimate = monitor_module.estimate_posterior_v2
    calls: list[dict] = []

    def wrapped_estimate(*args, **kwargs):
        calls.append(dict(kwargs))
        return original_estimate(*args, **kwargs)

    monkeypatch.setattr(
        monitor_module,
        "q6_residual_boost_for_profile",
        lambda **_kwargs: 5.0,
    )
    monkeypatch.setattr(
        monitor_module,
        "estimate_posterior_v2",
        wrapped_estimate,
    )

    artifact = build_monitor_artifact_from_events(
        _events(),
        file="sample.json",
        tables=_tables(),
        n_trials=10,
        roi_trials=0,
        run_debug_shadows=False,
    )

    assert artifact["q6_residual_boost_shadow"]["active"] is False
    assert artifact["q6_residual_boost_shadow"]["active_boost"] == 1.0
    assert any(
        "q6_residual_boost" not in call
        and "q6_residual_prior_floor_ratio" not in call
        for call in calls
    )
    assert not any(float(call.get("q6_residual_boost", 1.0)) > 1.0 for call in calls)


def test_zero_match_fallback_rows_use_relaxed_v1_reference() -> None:
    tables = _tables()
    session = SessionObs(
        map_id=2401,
        hero="aisha",
        warehouse_total_cells=4,
        total_item_count=1,
        buckets={
            6: QualityBucketObs(
                quality=6,
                total_cells=99,
            ),
        },
        visible_outline_item_count_min=5,
        visible_outline_total_cells_min=99,
    )

    map_rows, warehouse_rows, bid_rows = _build_zero_match_fallback_rows(
        candidate_map_ids=(2401,),
        inference_session=session,
        latest_bids={"leader": 15_000},
        round_no=4,
        maps=tables.maps,
        drops=tables.drops,
        items=tables.items,
        n_trials=10,
        seed=1,
        cells_tol=2,
        count_tol=1,
    )

    assert map_rows[0]["匹配"] == "10/10"
    assert warehouse_rows[0]["匹配"] == "10/10"
    assert bid_rows[0]["fallback"] == "是"
    assert bid_rows[0]["fallback_mode"] == "v1_map_prior_zero_match"
    assert bid_rows[0]["价值口径"] == "raw_value"
    assert bid_rows[0]["原始价值 P10/P50/P90"]
    assert bid_rows[0]["建议"]


def test_ethan_sample37_residual_does_not_break_exact_bucket_targets() -> None:
    sample = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "samples"
        / "fatbeans"
        / "ethan_shipwreck_test_sample37_5rounds.json"
    )
    if not sample.exists():
        pytest.skip("local Fatbeans sample37 capture is unavailable")
    artifact = build_monitor_artifact_from_file(
        sample,
        tables=load_monitor_tables(),
        n_trials=80,
        roi_trials=0,
        shadow_trials=20,
    )

    assert artifact["v2_posterior_rows"][0]["匹配"] != "0/80"
    assert artifact["bid_rows"]
    assert not artifact["fallback_bid_rows"]


def test_monitor_preserves_pre_settlement_full_outline_totals() -> None:
    events = FatbeansCaptureEvents(
        packets=(),
        frames=(),
        sends=(),
        statuses=(),
        states=(
            FatbeansStateEvent(
                sort_id=1,
                capture_time="",
                message_id=0x0025,
                session_id="s1",
                map_id=2401,
                round_index=4,
                bids=(
                    FatbeansPlayerBid(
                        player_id=1,
                        name="leader",
                        hero_id=103,
                        values=(12_000,),
                    ),
                ),
                action_results=(
                    FatbeansActionResult(
                        action_id=100100,
                        result=None,
                        result_field=None,
                        observed_items=(
                            FatbeansObservedItem(
                                local_index=0,
                                runtime_id=101,
                                item_id=None,
                                quality=None,
                                value=None,
                                shape_code=11,
                                cells=None,
                            ),
                            FatbeansObservedItem(
                                local_index=1,
                                runtime_id=102,
                                item_id=None,
                                quality=None,
                                value=None,
                                shape_code=11,
                                cells=None,
                            ),
                        ),
                    ),
                ),
            ),
            FatbeansStateEvent(
                sort_id=2,
                capture_time="",
                message_id=0x002D,
                session_id="s1",
                map_id=2401,
                round_index=5,
                inventory_items=(
                    FatbeansInventoryItem(
                        runtime_id=101,
                        item_id=1001,
                        quality=4,
                        cells=1,
                    ),
                    FatbeansInventoryItem(
                        runtime_id=102,
                        item_id=1002,
                        quality=4,
                        cells=1,
                    ),
                ),
            ),
        ),
    )

    artifact = build_monitor_artifact_from_events(
        events,
        file="full_outline.json",
        tables=_two_item_tables(),
        n_trials=20,
        roi_trials=0,
    )

    constraints = artifact["inference_input_constraints"]
    assert constraints["mode"] == "pre_settlement_trusted_totals"
    assert constraints["warehouse_total_cells"]["value"] == 2
    assert constraints["total_item_count"]["value"] == 2
    assert artifact["model_eval"]["input_warehouse_total_cells"] == 2
    assert artifact["model_eval"]["input_total_item_count"] == 2
    assert artifact["ui_contract"]["baseline"]["posterior"][
        "total_item_count_status"
    ] == "exact_input_constraint"
    assert artifact["ui_contract"]["constraints"]["summary"][
        "input_total_item_count"
    ] == 2


def test_shadow_trials_defaults_to_live_cap() -> None:
    assert DEFAULT_Q6_SHADOW_TRIALS_CAP == 80
    assert _resolve_shadow_trials(500, None) == 80
    assert _resolve_shadow_trials(20, None) == 20
    assert _resolve_shadow_trials(500, 120) == 120
    assert _resolve_shadow_trials(500, 0) == 1


def test_write_monitor_logs_updates_latest_and_jsonl(tmp_path: Path) -> None:
    artifact = build_monitor_artifact_from_events(
        _events(),
        file="sample.json",
        tables=_tables(),
        n_trials=10,
        roi_trials=0,
    )

    write_monitor_logs(artifact, log_dir=tmp_path)

    latest = json.loads((tmp_path / "latest_snapshot.json").read_text(encoding="utf-8"))
    assert latest["file"] == "sample.json"
    assert (tmp_path / "sessions.jsonl").read_text(encoding="utf-8")
    assert (tmp_path / "model_eval.jsonl").read_text(encoding="utf-8")
