from __future__ import annotations

import json
from pathlib import Path

from bidking_lab.extract.bid_map_table import BidMap
from bidking_lab.extract.drop_table import DropEntry, DropPool
from bidking_lab.extract.item_table import Item
from bidking_lab.live.fatbeans import (
    FatbeansCaptureEvents,
    FatbeansInventoryItem,
    FatbeansPlayerBid,
    FatbeansStateEvent,
)
from bidking_lab.live.monitor import (
    MonitorTables,
    build_monitor_artifact_from_events,
    write_monitor_logs,
)


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
    assert artifact["map_id"] == 2401
    assert artifact["known_value_sum"] == 20_000
    assert artifact["latest_bids"] == {"leader": 15_000}
    assert artifact["warehouse_rows"]
    assert artifact["v2_posterior_rows"]
    assert artifact["bid_rows"]
    assert artifact["bid_rows"][0]["价值口径"] == "decision_value"
    assert artifact["bid_rows"][0]["决策价值 P10/P50/P90"]
    assert artifact["bid_rows"][0]["原始价值 P10/P50/P90"]
    assert artifact["panel"]["summary_rows"]
    assert artifact["model_eval"]["final_value"] == 20_000
    assert artifact["model_eval"]["final_cells"] == 4
    assert artifact["model_eval"]["decision_value_p50"] == 20_000


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
