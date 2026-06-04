from __future__ import annotations

import importlib.util
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parents[1]


def _overlay_module():
    path = ROOT / "scripts" / "run_live_overlay.py"
    spec = importlib.util.spec_from_file_location("run_live_overlay", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_overlay_summary_lines_include_q6_and_diagnostics() -> None:
    overlay = _overlay_module()
    lines = overlay._summary_lines(
        {
            "hero": "ethan",
            "map_id": 2401,
            "round": 3,
            "known_value_sum": 801824,
            "panel": {
                "summary_rows": (
                    {
                        "topic": "当前最高价是否可追",
                        "conclusion": "可守不抢",
                        "detail": "停止价 587,459",
                    },
                ),
                "layout_stages": (
                    {
                        "stage": "R3 / sort 20",
                        "known_cells": "90",
                        "estimate": "120/140/160",
                        "confidence": "中",
                        "risk": "中",
                    },
                ),
            },
            "v2_posterior_rows": (
                {
                    "q6样本率": "12.0%",
                    "q6价值 P10/P50/P90": "0 / 120,000 / 360,000",
                    "q6先验缺口": "件数P90低1.00",
                    "q6先验风险参考": "486,510",
                    "q6实战参考P90": "486,510",
                    "诊断": "footprint_overlap_cells:2",
                },
            ),
            "model_eval": {
                "q6_p90_misses_truth": True,
                "layout_conflict": True,
                "decision_value_p50_error": -442506,
                "warehouse_p50_error": 8,
            },
        }
    )

    assert lines[0].startswith("ETHAN  |  map 2401")
    assert any(line.startswith("决策:") for line in lines)
    assert any(line.startswith("红货:") for line in lines)
    assert any("先验缺口" in line for line in lines)
    assert any("实战参考P90" in line for line in lines)
    assert any("q6 P90" in line for line in lines)
    assert any("footprint" in line for line in lines)
    assert any("决策P50误差" in line for line in lines)


def test_overlay_warns_when_snapshot_is_stale() -> None:
    overlay = _overlay_module()

    lines = overlay._summary_lines(
        {
            "created_at": time.time() - 180,
            "map_id": 2401,
            "round": 1,
            "panel": {"summary_rows": ()},
        }
    )

    assert any("超过 120 秒未更新" in line for line in lines)


def test_overlay_warns_when_latest_inference_is_slow() -> None:
    overlay = _overlay_module()

    lines = overlay._summary_lines(
        {
            "created_at": time.time(),
            "map_id": 2401,
            "round": 1,
            "processing_seconds": 18.25,
            "panel": {"summary_rows": ()},
        }
    )

    assert any("本次推理耗时 18.2s" in line for line in lines)


def test_overlay_window_geometry_uses_compact_default() -> None:
    overlay = _overlay_module()

    geometry = overlay._default_window_geometry(1920, 1080)

    assert geometry.startswith("480x420")


def test_overlay_hover_position_stays_inside_screen_edges() -> None:
    overlay = _overlay_module()

    x, y = overlay._bounded_popup_position(
        pointer_x=1880,
        pointer_y=1030,
        popup_width=420,
        popup_height=360,
        screen_width=1920,
        screen_height=1080,
    )

    assert x + 420 + overlay.HOVER_MARGIN <= 1920
    assert y + 360 + overlay.HOVER_MARGIN <= 1080
    assert x < 1880
    assert y < 1030


def test_overlay_detail_window_size_expands_within_screen() -> None:
    overlay = _overlay_module()

    assert overlay._detail_window_size(
        1920,
        1080,
        requested_width=1200,
        requested_height=1200,
    ) == (980, 860)
    assert overlay._detail_window_size(
        900,
        700,
        requested_width=300,
        requested_height=300,
    ) == (820, 620)


def test_overlay_snapshot_signature_changes_when_file_changes(tmp_path: Path) -> None:
    overlay = _overlay_module()
    snapshot = tmp_path / "latest_snapshot.json"
    snapshot.write_text('{"a": 1}', encoding="utf-8")
    first = overlay._snapshot_file_signature(snapshot)

    snapshot.write_text('{"a": 1, "b": 2}', encoding="utf-8")
    second = overlay._snapshot_file_signature(snapshot)

    assert first != second


def test_capture_status_signature_ignores_timestamp_only_changes() -> None:
    overlay = _overlay_module()
    first = {
        "ts": 1000.0,
        "source": "windivert",
        "process_name": "BidKing.exe",
        "active_flows": 1,
        "sniffed_packets": 100,
        "raw_packets": 1,
        "accepted_frames": 0,
        "ignored_frames": 1,
        "dropped_bytes": 0,
        "active_session_id": None,
    }
    second = dict(first)
    second["ts"] = 1002.0
    second["sniffed_packets"] = 120

    assert overlay._capture_status_signature(first) == overlay._capture_status_signature(second)

    second["raw_packets"] = 2
    second["ignored_frames"] = 2
    second["dropped_bytes"] = 1
    assert overlay._capture_status_signature(first) == overlay._capture_status_signature(second)

    first["raw_packets"] = 0
    assert overlay._capture_status_signature(first) != overlay._capture_status_signature(second)


def test_overlay_scroll_fraction_is_clamped() -> None:
    overlay = _overlay_module()

    assert overlay._clamp_scroll_fraction(None) == 0.0
    assert overlay._clamp_scroll_fraction("bad") == 0.0
    assert overlay._clamp_scroll_fraction(-0.25) == 0.0
    assert overlay._clamp_scroll_fraction(0.4) == 0.4
    assert overlay._clamp_scroll_fraction(1.25) == 1.0


def test_overlay_exit_cleanup_terminates_unique_pids_and_removes_locks(
    tmp_path: Path,
) -> None:
    overlay = _overlay_module()
    lock_path = tmp_path / "monitor.lock"
    lock_path.write_text('{"pid": 123}', encoding="utf-8")
    terminated: list[int] = []

    overlay._cleanup_exit_targets(
        [123, 123, 456],
        [lock_path],
        terminate_fn=terminated.append,
    )

    assert terminated == [123, 456]
    assert not lock_path.exists()


def test_overlay_exit_cleanup_is_not_gated_on_user_close() -> None:
    overlay = _overlay_module()

    terminated: list[int] = []

    overlay._cleanup_exit_targets(
        [321],
        [],
        terminate_fn=terminated.append,
    )

    assert terminated == [321]


def test_overlay_detects_watched_monitor_pid_exit() -> None:
    overlay = _overlay_module()

    running = {111: True, 222: False}

    assert (
        overlay._watched_pid_exited(
            [111],
            running_fn=lambda pid: running[pid],
        )
        is False
    )
    assert (
        overlay._watched_pid_exited(
            [111, 222],
            running_fn=lambda pid: running[pid],
        )
        is True
    )


def test_overlay_section_style_classifies_key_topics() -> None:
    overlay = _overlay_module()

    assert overlay._section_style("MiniMap")["badge"] == "地图"
    assert overlay._section_style("q6 风险参考", "已触发")["tag"] == "warn"
    assert overlay._section_style("Fallback 出价参考")["badge"] == "兜底"
    assert overlay._section_style("下一步道具")["tag"] == "good"


def test_overlay_draw_minimap_renders_quality_only_markers() -> None:
    overlay = _overlay_module()
    calls: list[tuple[str, tuple, dict]] = []

    class DummyCanvas:
        def configure(self, **kwargs):
            calls.append(("configure", (), kwargs))

        def create_line(self, *args, **kwargs):
            calls.append(("line", args, kwargs))

        def create_rectangle(self, *args, **kwargs):
            calls.append(("rectangle", args, kwargs))

        def create_oval(self, *args, **kwargs):
            calls.append(("oval", args, kwargs))

    instance = overlay.Overlay.__new__(overlay.Overlay)
    overlay.Overlay._draw_minimap(
        instance,
        DummyCanvas(),
        {
            "columns": 10,
            "viewport_rows": 13,
            "max_rows": 25,
            "rows_hint": 8,
            "items": [
                {
                    "row": 2,
                    "col": 5,
                    "width": 2,
                    "height": 2,
                    "quality": 5,
                    "render_mode": "footprint",
                },
                {
                    "row": 8,
                    "col": 7,
                    "width": 1,
                    "height": 1,
                    "quality": 2,
                    "render_mode": "marker",
                },
            ],
        },
    )

    assert any(kind == "rectangle" for kind, *_ in calls)
    assert any(kind == "oval" for kind, *_ in calls)
    assert overlay._section_style("正式出价", "停止追价")["tag"] == "bad"


def test_overlay_quality_style_distinguishes_white_and_unknown() -> None:
    overlay = _overlay_module()

    unknown = overlay._quality_style(None)
    white = overlay._quality_style(1)

    assert unknown["fill"] != white["fill"]
    assert unknown["fill"] == ""
    assert unknown["unknown"] == "1"
    assert unknown["hatch"] == "///"
    assert unknown["stipple"] == ""
    assert white["unknown"] == ""
    assert white["stipple"] == ""
    assert white["fill"].lower() == "#f8fafc"
    assert white["outline"].lower() == "#cbd5e1"


def test_demo_snapshot_has_compact_overlay_sections() -> None:
    overlay = _overlay_module()

    lines = overlay._summary_lines(overlay._demo_snapshot())
    model = overlay._overlay_model(overlay._demo_snapshot())

    assert any(line.startswith("决策:") for line in lines)
    assert any(line.startswith("价值:") for line in lines)
    assert any(line.startswith("仓储:") for line in lines)
    assert any(line.startswith("红货:") for line in lines)
    assert any(line.startswith("布局:") for line in lines)
    assert any(line.startswith("道具:") for line in lines)
    assert model["title"].startswith("ETHAN")
    assert model["decision"][0] == "可守不抢"
    assert [row[0] for row in model["metrics"]] == [
        "P50估值",
        "防守价",
        "当前最高",
        "红货 q6",
    ]
    assert any(section[0] == "鉴影命中" for section in model["sections"])
    assert any(alert[0].startswith("q6 P90") for alert in model["alerts"])
    assert any(alert[0].startswith("q6 件数/格数低于先验") for alert in model["alerts"])
    assert model["interaction"]["hover"]["enabled"] is True
    assert model["interaction"]["detail"]["enabled"] is True
    assert model["interaction"]["mini"]["sections"] == model["sections"][:4]


def test_overlay_model_uses_ui_contract_shadow_reference() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "hero": "aisha",
            "map_id": 2501,
            "round": 4,
            "known_value_sum": 800000,
            "bid_rows": [
                {
                    "建议": "可守不抢",
                    "当前最高": "玩家A 500,000",
                    "风险带": "防守区",
                    "停止价": "680,000",
                }
            ],
            "v2_posterior_rows": [
                {
                    "q6样本率": "12.0%",
                    "q6决策价值 P10/P50/P90": "0 / 100,000 / 300,000",
                }
            ],
            "ui_contract": {
                "context": {
                    "hero": "aisha",
                    "map_id": 2501,
                    "round": 4,
                    "known_value_sum": 800000,
                },
                "source": {"file": "sample.json"},
                "baseline": {
                    "decision": {
                        "action": "可守不抢",
                        "current_highest": "玩家A 500,000",
                        "risk_band": "防守区",
                        "defend_bid": "450,000",
                        "stop_price": "680,000",
                    },
                    "posterior": {
                        "decision_value_range": "300,000 / 500,000 / 700,000",
                        "raw_value_range": "300,000 / 540,000 / 900,000",
                        "q6_sample_rate": "12.0%",
                        "q6_decision_value_range": "0 / 100,000 / 300,000",
                    },
                    "layout": {
                        "known_cells": "108",
                        "estimate": "108/120/140",
                        "confidence": "中",
                        "risk": "中",
                    },
                },
                "q6_risk_reference": {
                    "risk": True,
                    "prior_gap": "件数P90低1.00",
                    "practical_reference_p90": "486,510",
                },
                "minimap": {
                    "status": "available",
                    "known_items": 2,
                    "default_cells": 130,
                    "max_cells": 250,
                    "viewport_rows": 13,
                    "max_rows": 25,
                    "scrollable": False,
                    "quality_counts": {"q5": 1, "q6": 1},
                    "category_counts": {"能源": 1, "古董": 1},
                    "columns": 10,
                    "rows_hint": 20,
                    "items": [
                        {
                            "row": 2,
                            "col": 4,
                            "width": 4,
                            "height": 4,
                            "quality": 6,
                            "shape_key": "44",
                            "item_name": "民用垂直起降飞行器",
                            "display_label": "",
                            "local_index": 14,
                        },
                        {
                            "row": 18,
                            "col": 1,
                            "width": 2,
                            "height": 2,
                            "quality": 5,
                            "shape_key": "22",
                            "item_name": "青铜古镜",
                            "display_label": "",
                            "local_index": 170,
                        },
                    ],
                },
                "constraints": {
                    "summary": {
                        "input_total_item_count": 42,
                        "input_warehouse_total_cells": 123,
                        "known_purple_item_count": 10,
                        "known_gold_item_count": 3,
                        "known_red_item_count": 1,
                        "anchor_count": 4,
                        "shape_target_count": 12,
                        "category_target_count": 2,
                        "category_exclusion_count": 1,
                        "public_constraint_key": "max_item_cells",
                    },
                },
                "truth": {
                    "available": True,
                    "source": "settlement_or_sample_replay",
                    "total_value": 800000,
                    "total_items": 42,
                    "total_cells": 123,
                    "q6": {"count": 1, "cells": 16, "value": 320000},
                    "top_item": {
                        "name": "民用垂直起降飞行器",
                        "quality": 6,
                        "cells": 16,
                        "value": 320000,
                    },
                },
                "actions": {
                    "latest_result": {
                        "tool": "宝光四鉴",
                        "result": "12",
                        "revealed_items": "0",
                    },
                    "results": (
                        {
                            "tool": "宝光四鉴",
                            "result": "12",
                            "revealed_items": "0",
                        },
                    ),
                    "sent": (),
                },
                "diagnostics": {
                    "posterior": "q6_below_drop_prior:0.12<prior:0.80",
                    "layout": {
                        "conflict": False,
                        "bottom_row": 18,
                        "bottom_row_risk": True,
                        "bottom_row_risk_threshold": 12,
                    },
                    "q6": {
                        "p90_misses_truth": True,
                        "below_drop_prior": True,
                        "top_size_band": "large",
                    },
                    "sampling": {
                        "relaxed_exact_used": False,
                        "n_trials": 500,
                        "shadow_trials": 80,
                        "processing_seconds": 1.2,
                    },
                },
                "interaction": {
                    "compact": {
                        "purpose": "always_on_top_core_tips",
                        "fields": ("baseline.decision.action",),
                    },
                    "hover": {
                        "purpose": "expanded_quick_context",
                        "fields": ("constraints.summary", "minimap"),
                    },
                    "detail": {
                        "purpose": "click_to_open_full_reasoning",
                        "fields": ("truth", "shadows", "diagnostics"),
                        "collapsible": True,
                        "renderers": (),
                    },
                },
                "shadows": [
                    {
                        "label": "profile_b5",
                        "display_mode": "debug_only",
                        "active": True,
                        "q6_decision_value_p90": 420000,
                        "q6_p90_delta": 120000,
                        "trials": 80,
                    },
                    {
                        "label": "aisha_deep_floor1",
                        "display_mode": "risk_reference_candidate",
                        "active": True,
                        "q6_decision_value_p90": 486510,
                        "q6_p90_delta": 186510,
                        "trials": 80,
                    },
                ],
            },
        }
    )

    shadow_sections = [
        section for section in model["sections"] if section[0] == "Shadow 风险参考"
    ]
    assert shadow_sections
    assert "aisha_deep_floor1" in shadow_sections[0][1]
    assert "profile_b5" not in shadow_sections[0][1]
    minimap_section = next(section for section in model["sections"] if section[0] == "MiniMap")
    assert "已知 2 件" in minimap_section[1]
    assert "能源×1" in minimap_section[2]
    constraints_section = next(
        section for section in model["sections"] if section[0] == "输入约束"
    )
    assert "总件 42" in constraints_section[1]
    assert "总格 123" in constraints_section[1]
    assert "紫×10" in constraints_section[2]
    assert "反排1" in constraints_section[2]
    action_section = next(
        section for section in model["sections"] if section[0] == "最近道具"
    )
    assert "宝光四鉴: 12" in action_section[1]
    geometry = overlay._minimap_canvas_geometry(model["minimap"])
    assert geometry["rows"] == 20
    assert geometry["visible_rows"] == 13
    assert geometry["height"] > geometry["visible_height"]
    assert all(
        not str(item.get("display_label") or "").strip()
        for item in model["minimap"]["items"]
    )
    assert model["minimap"]["known_items"] == 2
    assert model["minimap"]["default_cells"] == 130
    assert model["minimap"]["max_cells"] == 250
    assert model["minimap"]["capacity_text"] == "估格 108/120/140"
    assert "最高" not in model["minimap"]["capacity_text"]
    assert model["title"] == "AISHA  ·  map 2501  ·  R4"
    assert model["decision"][0] == "可守不抢"
    assert model["metrics"][0] == (
        "P50估值",
        "500,000",
        "P10/P50/P90 300,000 / 500,000 / 700,000",
        "normal",
    )
    assert model["metrics"][1][0] == "防守价"
    assert model["metrics"][1][1] == "450,000"
    assert model["metrics"][2][0] == "当前最高"
    assert any("UI契约 q6 风险参考" in alert[0] for alert in model["alerts"])
    assert any("aisha_deep_floor1 tail-risk shadow" in alert[0] for alert in model["alerts"])
    interaction = model["interaction"]
    assert interaction["mini"]["purpose"] == "always_on_top_core_tips"
    assert interaction["mini"]["metrics"][0][0] == "P50估值"
    assert interaction["hover"]["enabled"] is True
    assert interaction["hover"]["sections"][0][0] == "正式出价"
    assert any(section[0] == "MiniMap" for section in interaction["hover"]["sections"])
    assert any(section[0] == "输入约束" for section in interaction["hover"]["sections"])
    assert any(section[0] == "q6 风险参考" for section in interaction["hover"]["sections"])
    round_section = next(
        section for section in interaction["hover"]["sections"] if section[0] == "轮次仓位参考"
    )
    assert round_section[1] == "R4 参考 454,546"
    assert "P50 500,000 ÷ 1.1" in round_section[2]
    assert "不改变正式出价" in round_section[2]
    assert interaction["detail"]["enabled"] is True
    assert interaction["detail"]["collapsible"] is True
    assert interaction["detail"]["renderers"] == ()
    assert any(section[0] == "结算/Truth" for section in interaction["detail"]["sections"])
    assert any(section[0] == "Shadow 明细" for section in interaction["detail"]["sections"])
    assert any(section[0] == "诊断明细" for section in interaction["detail"]["sections"])


def test_overlay_model_surfaces_live_health_warnings() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "file": "slow.json",
            "created_at": time.time(),
            "hero": "aisha",
            "map_id": 2501,
            "round": 4,
            "ui_contract": {
                "context": {
                    "hero": "aisha",
                    "map_id": 2501,
                    "round": 4,
                    "known_value_sum": 800000,
                },
                "source": {
                    "file": "slow.json",
                    "processing_seconds": 18.25,
                },
                "baseline": {
                    "decision": {
                        "action": "可守不抢",
                        "current_highest": "玩家A 500,000",
                        "risk_band": "防守区",
                        "stop_price": "680,000",
                    },
                    "posterior": {
                        "status": "matched",
                        "match_text": "80/80",
                        "decision_value_range": "300,000 / 500,000 / 700,000",
                    },
                },
                "q6_risk_reference": {
                    "risk": True,
                    "prior_gap": "件数P90低1.00",
                    "practical_reference_p90": "486,510",
                    "affects_bid": True,
                    "bid_floor_applied": True,
                },
            },
        }
    )

    assert model["status"] == ("慢", "warn")
    assert "推理 18.2s" in model["subtitle"]
    assert any("本次推理耗时 18.2s" in alert[0] for alert in model["alerts"])
    assert any("q6 风险参考不应影响正式出价" in alert[0] for alert in model["alerts"])


def test_overlay_model_switches_to_settlement_view_when_settled() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "file": "settled.json",
            "hero": "ethan",
            "map_id": 2401,
            "round": 5,
            "phase": "settled",
            "known_value_sum": 801824,
            "ui_contract": {
                "context": {
                    "hero": "ethan",
                    "map_id": 2401,
                    "round": 5,
                    "phase": "settled",
                    "known_value_sum": 801824,
                    "inventory_count": 38,
                    "inventory_cells": 112,
                },
                "source": {"file": "settled.json"},
                "baseline": {
                    "decision": {
                        "action": "仍在可防守区",
                        "current_highest": "玩家A 500,000",
                        "risk_band": "防守区",
                        "defend_bid": "650,000",
                        "stop_price": "900,000",
                    },
                    "posterior": {
                        "decision_value_range": "500,000 / 750,000 / 900,000",
                    },
                },
                "truth": {
                    "available": True,
                    "source": "settlement_or_sample_replay",
                    "total_value": 801824,
                    "total_items": 38,
                    "total_cells": 112,
                    "q6": {"count": 1, "cells": 9, "value": 320000},
                    "top_item": {
                        "name": "永乐大典",
                        "quality": 6,
                        "cells": 9,
                        "value": 320000,
                    },
                },
            },
        }
    )

    assert model["decision"][0] == "结算 801,824"
    assert "总件 38" in model["decision"][1]
    assert [metric[0] for metric in model["metrics"]] == [
        "结算总值",
        "总件/总格",
        "红货 q6",
        "最高货",
    ]
    assert model["metrics"][0][1] == "801,824"
    assert any(section[0] == "结算/Truth" for section in model["sections"])


def test_overlay_model_hides_old_settlement_after_retention_window() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "created_at": time.time() - 90,
            "file": "settled.json",
            "phase": "settled",
            "ui_contract": {
                "context": {"phase": "settled", "known_value_sum": 801824},
                "truth": {
                    "available": True,
                    "total_value": 801824,
                },
            },
        }
    )

    assert model["status"] == ("待机", "dim")
    assert model["decision"][0] == "等待对局开始"
    assert model["decision"][1] == "上一局结算已结束"
    assert model["subtitle"] == "等待下一局开始"
    assert [metric[0] for metric in model["metrics"]] == [
        "P50估值",
        "防守价",
        "当前最高",
        "q6风险",
    ]
    assert any(section[0] == "监听状态" for section in model["sections"])
    assert model["interaction"]["hover"]["enabled"] is False
    assert model["interaction"]["detail"]["enabled"] is False


def test_overlay_model_review_snapshot_keeps_stale_settlement() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "created_at": time.time() - 90,
            "file": "settled.json",
            "phase": "settled",
            "ui_contract": {
                "context": {"phase": "settled", "known_value_sum": 801824},
                "truth": {
                    "available": True,
                    "total_value": 801824,
                },
            },
        },
        review_snapshot=True,
    )

    assert model["decision"][0] == "结算 801,824"
    assert any(metric[0] == "结算总值" for metric in model["metrics"])
    assert model["interaction"]["detail"]["enabled"] is True


def test_overlay_model_retains_recent_settlement_when_capture_session_is_stale() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "created_at": time.time() - 5,
            "phase": "settled",
            "map_id": 2409,
            "round": 4,
            "ui_contract": {
                "context": {"phase": "settled", "session_id": "2409:old-session"},
                "truth": {"available": True, "total_value": 500000},
            },
            "_capture_source_status": {
                "ts": time.time() - 30,
                "source": "windivert",
                "active_flows": 1,
                "raw_packets": 120,
                "accepted_frames": 6,
                "active_session_id": "2504:1295018884127153",
            },
        }
    )

    assert model["decision"][0] == "结算 500,000"
    assert any(metric[0] == "结算总值" for metric in model["metrics"])


def test_overlay_model_shows_new_session_loading_for_recent_settlement() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "created_at": time.time() - 5,
            "phase": "settled",
            "map_id": 2409,
            "round": 4,
            "ui_contract": {
                "context": {"phase": "settled", "session_id": "2409:old-session"},
                "truth": {"available": True, "total_value": 500000},
            },
            "_capture_source_status": {
                "ts": time.time() - 1,
                "source": "windivert",
                "active_flows": 1,
                "raw_packets": 120,
                "accepted_frames": 6,
                "active_session_id": "2504:1295018884127153",
            },
        }
    )

    assert model["decision"][0] == "新局监听中"
    assert model["subtitle"] == "监听中，已抓到新局 map 2504"


def test_overlay_model_shows_new_session_loading_after_settlement() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "created_at": time.time() - 90,
            "file": "settled.json",
            "phase": "settled",
            "_capture_source_status": {
                "ts": time.time() - 1,
                "source": "windivert",
                "active_flows": 1,
                "raw_packets": 120,
                "accepted_frames": 8,
                "active_session_id": "2401:new-session-id",
            },
            "ui_contract": {
                "context": {"phase": "settled", "known_value_sum": 801824},
                "truth": {
                    "available": True,
                    "total_value": 801824,
                },
            },
        }
    )

    assert model["decision"][0] == "新局监听中"
    assert model["subtitle"] == "监听中，已抓到新局 map 2401"
    assert any(section[0] == "当前会话" for section in model["sections"])
    assert any(
        section[0] == "当前地图" and section[1] == "2401"
        for section in model["sections"]
    )


def test_overlay_model_hides_stale_non_settlement_snapshot() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "created_at": time.time() - 180,
            "hero": "ethan",
            "map_id": 2401,
            "round": 3,
            "ui_contract": {
                "context": {"hero": "ethan", "map_id": 2401, "round": 3},
                "baseline": {
                    "decision": {
                        "action": "小幅进攻",
                        "current_highest": "玩家A 200,000",
                    },
                    "posterior": {
                        "decision_value_range": "100,000 / 200,000 / 300,000",
                    },
                },
            },
        }
    )

    assert model["status"] == ("待机", "dim")
    assert model["decision"][0] == "等待对局开始"
    assert model["decision"][1] == "不显示过期旧局出价"
    assert model["subtitle"] == "等待新的实时对局状态"
    assert model["metrics"][0][1] == "--"
    assert not any("小幅进攻" in str(value) for value in model.values())


def test_overlay_model_uses_capture_status_for_stale_snapshot_waiting_copy() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "created_at": time.time() - 180,
            "hero": "ethan",
            "map_id": 2401,
            "round": 3,
            "_capture_source_status": {
                "ts": time.time() - 1,
                "source": "windivert",
                "active_flows": 1,
                "raw_packets": 0,
                "accepted_frames": 0,
            },
            "ui_contract": {
                "context": {"hero": "ethan", "map_id": 2401, "round": 3},
                "baseline": {
                    "decision": {"action": "小幅进攻"},
                },
            },
        }
    )

    assert model["status"] == ("待机", "dim")
    assert model["subtitle"] == "监听中，等待对局数据"
    assert model["decision"][1] == "已连接游戏服务器，等待下一条对局状态包"
    assert any(section[0] == "抓包状态" for section in model["sections"])


def test_overlay_model_empty_snapshot_uses_standby_copy() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model({})

    assert model["empty"] is True
    assert model["status"] == ("待机", "dim")
    assert model["decision"][0] == "等待对局开始"
    assert model["decision"][1] == "等待实时数据"
    assert model["subtitle"] == "等待实时对局状态"
    assert model["metrics"][0][0] == "P50估值"
    assert model["sections"][0][0] == "监听状态"


def test_overlay_model_surfaces_zero_match_baseline() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "file": "zero_match.json",
            "hero": "aisha",
            "map_id": 2601,
            "round": 3,
            "known_value_sum": 1200000,
            "ui_contract": {
                "context": {
                    "hero": "aisha",
                    "map_id": 2601,
                    "round": 3,
                    "known_value_sum": 1200000,
                },
                "source": {"file": "zero_match.json"},
                "baseline": {
                    "decision": {
                        "action": "",
                    },
                    "posterior": {
                        "match_text": "0/80",
                        "status": "zero_match",
                    },
                    "layout": {},
                },
            },
        }
    )

    assert model["decision"] == (
        "后验无匹配",
        "匹配 0/80  |  复核公开约束/布局解析",
        "bad",
    )
    assert any("baseline 后验无匹配" in alert[0] for alert in model["alerts"])


def test_overlay_model_uses_zero_match_fallback_reference() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "file": "zero_match.json",
            "hero": "aisha",
            "map_id": 2601,
            "round": 3,
            "known_value_sum": 1200000,
            "ui_contract": {
                "context": {
                    "hero": "aisha",
                    "map_id": 2601,
                    "round": 3,
                    "known_value_sum": 1200000,
                },
                "source": {"file": "zero_match.json"},
                "baseline": {
                    "decision": {
                        "action": "",
                    },
                    "posterior": {
                        "match_text": "0/80",
                        "status": "zero_match",
                    },
                    "layout": {},
                },
                "fallback": {
                    "active": True,
                    "affects_bid": False,
                    "decision": {
                        "action": "停止追价",
                        "current_highest": "玩家A 500,000",
                        "risk_band": "过热区",
                        "probe_bid": "180,000",
                        "defend_bid": "196,000",
                        "attack_bid": "252,000",
                        "stop_price": "420,000",
                        "next_info_hint": "优先补轮廓或具体物品",
                        "rationale": "低信息阶段按地图后验保守折价",
                        "player_risks": [
                            {
                                "current_bid": "玩家A 500,000",
                                "risk_band": "过热区",
                            }
                        ],
                    },
                    "posterior": {
                        "raw_value_range": "180,000 / 280,000 / 420,000",
                        "match_text": "22/80",
                    },
                },
            },
        }
    )

    assert model["decision"] == (
        "低置信参考：停止追价",
        "v2匹配 0/80  |  最高 玩家A 500,000  |  停止 420,000  |  过热区",
        "bad",
    )
    assert model["metrics"][0] == (
        "fallback P50",
        "280,000",
        "v1低置信 / 22/80",
        "warn",
    )
    fallback_section = next(
        section for section in model["sections"] if section[0] == "Fallback 出价参考"
    )
    assert "探价 180,000" in fallback_section[1]
    assert "防守 196,000" in fallback_section[1]
    assert "可追(P90) 252,000" in fallback_section[1]
    assert "停止 420,000" in fallback_section[1]
    assert "对手：玩家A 500,000 过热区" in fallback_section[2]
    assert "补信息：优先补轮廓或具体物品" in fallback_section[2]
    assert any("v1 fallback 已生成低置信参考" in alert[0] for alert in model["alerts"])
    assert any(
        section[0] == "Fallback 出价参考"
        for section in model["interaction"]["hover"]["sections"]
    )
    assert any(
        section[0] == "Fallback 出价参考"
        for section in model["interaction"]["detail"]["sections"]
    )


def test_overlay_hover_surfaces_size_bucket_section() -> None:
    overlay = _overlay_module()
    from bidking_lab.runtime.snapshot import ui_contract_from_artifact

    contract = ui_contract_from_artifact(
        {
            "action_result_rows": [
                {
                    "action_id": 100172,
                    "tool": "四格均价",
                    "result": 135000,
                    "sort": 3,
                }
            ],
            "v2_posterior_rows": [
                {
                    "诊断": (
                        "size_bucket:4:avg=135000:tier=rich_pool:strength=soft"
                    ),
                }
            ],
        }
    )
    sections = overlay._ui_contract_hover_sections(contract)
    size_section = next(section for section in sections if section[0] == "N格均价")
    assert "四格均价" in size_section[1]
    assert "tier=rich_pool" in size_section[2]
