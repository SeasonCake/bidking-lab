from bidking_lab.runtime import (
    action_result_rows_from_results,
    import_overview_from_summary,
    layout_replay_rows_from_stages,
    packet_action_rows_from_sends,
    player_bid_candidate_rows_from_bids,
    tactical_panel_from_rows,
    tactical_snapshot_from_rows,
    tactical_summary_rows,
)
from bidking_lab.live.layout import (
    LayoutEstimatePolicy,
    LayoutEvidence,
    LayoutItemEvidence,
)


def test_import_overview_from_summary_keeps_packet_metadata() -> None:
    overview = import_overview_from_summary(
        {
            "file": "sample.json",
            "packets": 103,
            "frames": 118,
            "states": 5,
            "batches": 5,
            "map_id": 2408,
            "round": 4,
            "inventory_count": 42,
            "inventory_cells": 114,
            "known_value_sum": 753522,
        }
    )

    assert overview.file == "sample.json"
    assert overview.packets == "103"
    assert overview.frames == "118"
    assert overview.states == "5"
    assert overview.live_batches == "5"
    assert overview.map_id == "2408"
    assert overview.round_no == "4"
    assert overview.settlement_items == "42"
    assert overview.settlement_cells == "114"
    assert overview.known_loot_value == "753522"


def test_fatbeans_diagnostic_rows_are_frontend_neutral() -> None:
    sends = [
        {"kind": "heartbeat", "value": 100136},
        {
            "kind": "action",
            "value": 100136,
            "sort_id": 65,
            "capture_time": "2026-05-29T11:19:08.979+08:00",
        },
    ]
    results = [
        {
            "action_id": 100136,
            "result": None,
            "observed_items": ("a", "b", "c", "d"),
        }
    ]
    bids = [
        {"name": "玩家A", "values": (288888, 750000, 444444)},
        {"name": "无出价", "values": ()},
    ]
    item_names = {100136: "宝光四鉴"}

    assert packet_action_rows_from_sends(sends, item_names) == (
        {
            "sort": "65",
            "时间": "19:08.979+08:00",
            "action_id": "100136",
            "道具": "宝光四鉴",
        },
    )
    assert action_result_rows_from_results(results, item_names) == (
        {
            "action_id": "100136",
            "道具": "宝光四鉴",
            "结果": "",
            "揭示物品数": "4",
        },
    )
    assert player_bid_candidate_rows_from_bids(bids) == (
        {
            "玩家": "玩家A",
            "最大出价候选": "750000",
            "values": "288888,750000,444444",
        },
    )


def test_tactical_snapshot_from_rows_keeps_summary_frontend_neutral() -> None:
    snapshot = tactical_snapshot_from_rows(
        bid_rows=[
            {
                "建议": "小幅进攻，等新信息确认",
                "当前最高": "爆米花 723,333",
                "风险带": "进攻区",
                "仓储": "后验 55/76/101 (中)",
                "停止价": "1,148,540",
                "证据": "结算前最后状态+总仓储",
            }
        ],
        warehouse_rows=[
            {
                "价值 P10/P50/P90": "144,190 / 380,266 / 872,719",
                "总格 P10/P50/P90": "55 / 76 / 101",
                "置信度": "中",
                "说明": "匹配样本或区间宽度仍有不确定性",
            }
        ],
        tool_rows=[
            {
                "道具": "随机抽检（2）",
                "信息ROI": 274.05,
                "价值区间压缩": "685,137",
                "仓储区间压缩": 45,
            }
        ],
        layout_stage_rows=[
            {
                "阶段": "R2 / sort 45",
                "已知格": 157,
                "覆盖": "100%",
                "最深行": 17,
                "布局估计": "157",
                "置信": "高",
                "风险": "低",
            }
        ],
    )

    assert snapshot.price_decision == "小幅进攻，等新信息确认"
    assert snapshot.highest_bid == "爆米花 723,333"
    assert snapshot.risk_band == "进攻区"
    assert snapshot.stop_price == "1,148,540"
    assert snapshot.evidence == "结算前最后状态+总仓储"
    assert snapshot.warehouse_note == "中；匹配样本或区间宽度仍有不确定性"
    assert snapshot.value_range == "144,190 / 380,266 / 872,719"
    assert snapshot.warehouse_range == "55 / 76 / 101"
    assert snapshot.next_tool_hint == (
        "随机抽检（2），ROI 274.05；价值压缩 685,137，仓储压缩 45"
    )
    assert len(snapshot.layout_stages) == 1
    assert snapshot.layout_stages[0].stage == "R2 / sort 45"


def test_tactical_summary_rows_match_compact_panel_shape() -> None:
    snapshot = tactical_snapshot_from_rows(
        bid_rows=[
            {
                "建议": "可守不抢",
                "当前最高": "玩家A 300,000",
                "风险带": "防守区",
                "停止价": "420,000",
                "证据": "R2 MC 后验",
            }
        ],
        warehouse_rows=[
            {
                "价值 P10/P50/P90": "200,000 / 350,000 / 500,000",
                "总格 P10/P50/P90": "80 / 100 / 125",
                "置信度": "中",
                "说明": "仓储区间仍宽",
            }
        ],
        tool_rows=[],
    )

    rows = tactical_summary_rows(snapshot)

    assert [row.topic for row in rows] == [
        "当前最高价是否可追",
        "当前价值区间",
        "当前仓储区间",
        "下一次优先使用道具",
    ]
    assert rows[0].conclusion == "可守不抢"
    assert rows[0].detail == "玩家A 300,000 / 防守区 / 停止价 420,000"
    assert rows[1].detail == "R2 MC 后验"
    assert rows[2].detail == "中；仓储区间仍宽"
    assert rows[3].conclusion == "暂无建议"


def test_tactical_snapshot_prefers_decision_value_and_keeps_raw_detail() -> None:
    snapshot = tactical_snapshot_from_rows(
        bid_rows=[
            {
                "建议": "可守不抢",
                "证据": "v2 decision_value",
                "决策价值 P10/P50/P90": "180,000 / 260,000 / 420,000",
                "原始价值 P10/P50/P90": "180,000 / 260,000 / 1,200,000",
                "上界风险": "高 / raw P90 +780,000",
                "后验诊断": "relaxed_exact_bucket_targets:q4:count=3:cells=9",
            }
        ],
        warehouse_rows=[
            {
                "价值 P10/P50/P90": "200,000 / 350,000 / 500,000",
                "总格 P10/P50/P90": "80 / 100 / 125",
            }
        ],
    )

    assert snapshot.value_range == "180,000 / 260,000 / 420,000"
    assert snapshot.evidence == (
        "v2 decision_value；raw 180,000 / 260,000 / 1,200,000；"
        "上界 高 / raw P90 +780,000；"
        "relaxed_exact_bucket_targets:q4:count=3:cells=9"
    )


def test_tactical_panel_from_rows_keeps_render_sections_together() -> None:
    panel = tactical_panel_from_rows(
        bid_rows=[
            {
                "建议": "小幅进攻",
                "当前最高": "玩家A 500,000",
                "风险带": "进攻区",
                "停止价": 650000,
            },
            {
                "建议": "",
                "当前最高": "玩家B 480,000",
            },
        ],
        warehouse_rows=[
            {
                "总格 P10/P50/P90": "90 / 120 / 150",
                "价值 P10/P50/P90": "300k / 500k / 800k",
                "置信度": "中",
            }
        ],
        tool_rows=[
            {
                "道具": "随机抽检（2）",
                "信息ROI": 12.5,
                "价值压缩": 100000,
                "仓储压缩": 8,
            }
        ],
        layout_stage_rows=[
            {
                "阶段": "R1 / sort 10",
                "已知格": 40,
                "覆盖": "33%",
                "最深行": 12,
                "布局估计": "弱",
                "置信": "低",
                "风险": "中",
            }
        ],
        layout_note="底部稀疏，只作布局深度证据",
    )

    assert [row.topic for row in panel.summary_rows] == [
        "当前最高价是否可追",
        "当前价值区间",
        "当前仓储区间",
        "下一次优先使用道具",
    ]
    assert panel.layout_stages[0].stage == "R1 / sort 10"
    assert panel.warehouse_rows == (
        {
            "总格 P10/P50/P90": "90 / 120 / 150",
            "价值 P10/P50/P90": "300k / 500k / 800k",
            "置信度": "中",
        },
    )
    assert panel.tool_rows[0]["信息ROI"] == "12.5"
    assert panel.bid_rows == (
        {
            "建议": "小幅进攻",
            "当前最高": "玩家A 500,000",
            "风险带": "进攻区",
            "停止价": "650000",
        },
    )
    assert panel.layout_note == "底部稀疏，只作布局深度证据"


def test_layout_replay_rows_from_stages_are_frontend_neutral() -> None:
    layout = LayoutEvidence(
        sequence=12,
        items=(
            LayoutItemEvidence(
                cells=4,
                row=1,
                col=1,
                width=2,
                height=2,
                bottom_row=2,
                right_col=2,
                quality=4,
                shape_key="22",
                local_index=0,
            ),
        ),
        max_row=2,
        total_cells=4,
        bounding_cells=20,
        sparsity_ratio=0.8,
        bottom_tail_item_count=1,
        known_quality_count=1,
        unknown_quality_count=0,
    )
    stage = {
        "sort_id": 99,
        "round_no": 2,
        "phase": "reading",
        "layout": layout,
        "final_total_cells": 40,
        "known_cell_ratio": 0.1,
        "bounding_cell_error": -20,
    }

    rows = layout_replay_rows_from_stages((stage,))

    assert rows == (
        {
            "sort": "99",
            "R": "2",
            "phase": "reading",
            "已知件": "1",
            "已知格": "4",
            "最深行": "2",
            "边界格": "20",
            "空洞率": "80%",
            "最终格": "40",
            "已知覆盖": "10%",
            "边界误差": "-20",
            "布局估计": "4/?/?",
            "估计置信": "低",
            "风险": "低：底部证据稀疏，仓储可能被高估或低估",
        },
    )


def test_layout_replay_rows_can_include_sample_fit_estimate() -> None:
    layout = LayoutEvidence(
        sequence=12,
        items=(
            LayoutItemEvidence(
                cells=30,
                row=1,
                col=1,
                width=5,
                height=6,
                bottom_row=6,
                right_col=5,
                quality=4,
                shape_key="56",
                local_index=0,
            ),
            LayoutItemEvidence(
                cells=6,
                row=9,
                col=1,
                width=3,
                height=2,
                bottom_row=10,
                right_col=3,
                quality=3,
                shape_key="32",
                local_index=80,
            ),
        ),
        max_row=10,
        total_cells=36,
        bounding_cells=100,
        sparsity_ratio=0.40,
        bottom_tail_item_count=2,
        known_quality_count=2,
        unknown_quality_count=0,
    )
    stage = {
        "sort_id": 99,
        "round_no": 2,
        "phase": "reading",
        "layout": layout,
        "final_total_cells": 95,
        "known_cell_ratio": 36 / 95,
        "bounding_cell_error": 5,
    }

    rows = layout_replay_rows_from_stages(
        (stage,),
        comparison_policy=LayoutEstimatePolicy(
            name="sample-fit-test",
            medium_p50_margin=6,
        ),
    )

    assert rows[0]["布局估计"] == "36/80/100"
    assert rows[0]["样本拟合估计"] == "36/94/100"


def test_tactical_snapshot_from_rows_has_empty_state_defaults() -> None:
    snapshot = tactical_snapshot_from_rows()

    assert snapshot.price_decision == "暂无出价后验"
    assert snapshot.value_range == "暂无后验"
    assert snapshot.warehouse_range == "暂无后验"
    assert snapshot.next_tool_hint == "暂无建议"
    assert snapshot.layout_stages == ()
