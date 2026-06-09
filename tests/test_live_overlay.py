from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import time


ROOT = Path(__file__).resolve().parents[1]


def _overlay_module():
    path = ROOT / "scripts" / "run_live_overlay.py"
    spec = importlib.util.spec_from_file_location("run_live_overlay", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ahmad_overlay_module():
    path = ROOT / "external_references" / "ahmad_live_reference_lab" / "tools" / "ahmad_tk_overlay.py"
    spec = importlib.util.spec_from_file_location("ahmad_tk_overlay", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ahmad_server_module():
    path = ROOT / "external_references" / "ahmad_live_reference_lab" / "tools" / "ahmad_live_panel_server.py"
    spec = importlib.util.spec_from_file_location("ahmad_live_panel_server", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
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
                    "q6件数 P10/P50/P90": "0 / 1 / 2",
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
    assert any("件数 0 / 1 / 2" in line for line in lines)
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
    assert overlay._section_style("v3 实战参考", "低估风险")["badge"] == "V3"
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


def test_ahmad_tk_minimap_draws_explicit_marker_as_oval_even_with_shape() -> None:
    module = _ahmad_overlay_module()
    calls: list[tuple[str, tuple, dict]] = []

    class DummyCanvas:
        def delete(self, *args, **kwargs):
            calls.append(("delete", args, kwargs))

        def winfo_width(self):
            return 300

        def winfo_height(self):
            return 140

        def configure(self, **kwargs):
            calls.append(("configure", (), kwargs))

        def create_line(self, *args, **kwargs):
            calls.append(("line", args, kwargs))

        def create_rectangle(self, *args, **kwargs):
            calls.append(("rectangle", args, kwargs))

        def create_oval(self, *args, **kwargs):
            calls.append(("oval", args, kwargs))

        def create_text(self, *args, **kwargs):
            calls.append(("text", args, kwargs))

        def tag_bind(self, *args, **kwargs):
            calls.append(("tag_bind", args, kwargs))

    instance = module.AhmadTkOverlay.__new__(module.AhmadTkOverlay)
    module.AhmadTkOverlay._draw_minimap(
        instance,
        DummyCanvas(),
        {
            "status": "available",
            "columns": 10,
            "viewport_rows": 13,
            "items": [
                {
                    "row": 2,
                    "col": 5,
                    "width": 2,
                    "height": 2,
                    "quality": "q6",
                    "source": "public_info",
                    "layout_source": "public_info",
                    "render_mode": "marker",
                    "shape_key": "22",
                    "cells": 4,
                }
            ],
        },
        None,
    )

    assert any(
        kind == "oval" and kwargs.get("tags") == ("item_0",)
        for kind, _args, kwargs in calls
    )
    assert not any(
        kind == "rectangle" and kwargs.get("tags") == ("item_0",)
        for kind, _args, kwargs in calls
    )


def test_ahmad_footer_github_opens_project_link(monkeypatch) -> None:
    module = _ahmad_overlay_module()
    opened: list[tuple[str, int, bool]] = []

    def fake_open(url: str, *, new: int = 0, autoraise: bool = True) -> bool:
        opened.append((url, new, autoraise))
        return True

    monkeypatch.setattr(module.webbrowser, "open", fake_open)
    instance = module.AhmadTkOverlay.__new__(module.AhmadTkOverlay)

    module.AhmadTkOverlay._open_credit_github(instance)

    assert opened == [(module.CREDIT_GITHUB_URL, 2, True)]


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
        "红品数量",
    ]
    assert model["metrics"][3][1] == "件数 0 / 1 / 1"
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
                        "q6_count_range": "0 / 1 / 2",
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
                    "quality_reveal_counts": {"q2": 3, "q3": 3, "q4": 1, "q5": 1, "q6": 1},
                    "quality_reveal_unplaced_counts": {"q6": 1},
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
                    "public_info": {
                        "public_numeric_summary": "紫均格 2.90 / 随机9均价 15,296.33",
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
    assert "公共品质 Q2×3 / Q3×3 / Q4×1 / Q5×1 / Q6×1" in minimap_section[2]
    assert "未定位 Q6×1" in minimap_section[2]
    constraints_section = next(
        section for section in model["sections"] if section[0] == "输入约束"
    )
    assert "总件 42" in constraints_section[1]
    assert "总格 123" in constraints_section[1]
    assert "紫×10" in constraints_section[2]
    assert "红×1" in constraints_section[2]
    assert "反排1" in constraints_section[2]
    assert "紫均格 2.90" in constraints_section[2]
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
    assert model["minimap"]["capacity_text"] == "当前123格"
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
    assert model["metrics"][3][0] == "红品数量"
    assert model["metrics"][3][1] == "红品 1件"
    assert "样本 12.0%" in model["metrics"][3][2]
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
    posterior_section = next(
        section
        for section in interaction["hover"]["sections"]
        if section[0] == "后验概览"
    )
    assert "已知红品 1件" in posterior_section[2]
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


def test_overlay_model_hides_old_live_snapshot_when_capture_session_advances() -> None:
    overlay = _overlay_module()

    model = overlay._overlay_model(
        {
            "created_at": time.time() - 5,
            "phase": "bidding",
            "map_id": 2401,
            "round": 3,
            "ui_contract": {
                "context": {
                    "phase": "bidding",
                    "session_id": "2401:old-session",
                },
                "baseline": {
                    "decision": {
                        "action": "小幅进攻",
                        "current_highest": "玩家A 200,000",
                    },
                },
            },
            "_capture_source_status": {
                "ts": time.time() - 1,
                "source": "windivert",
                "active_flows": 1,
                "raw_packets": 240,
                "accepted_frames": 10,
                "active_session_id": "2407:1295018993925150",
            },
        }
    )

    assert model["decision"][0] == "新局监听中"
    assert model["subtitle"] == "监听中，已抓到新局 map 2407"
    assert not any("小幅进攻" in str(value) for value in model.values())


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


def test_overlay_constraints_section_shows_activity_map_alias() -> None:
    overlay = _overlay_module()

    section = overlay._ui_contract_constraints_section(
        {
            "constraints": {
                "summary": {
                    "known_grid_items": 2,
                    "map_alias_label": "活动图 2527->旧沉船 2507",
                }
            }
        }
    )

    assert section is not None
    assert section[0] == "输入约束"
    assert "已知 2 件" in section[1]
    assert "活动图 2527->旧沉船 2507" in section[2]


def test_overlay_surfaces_v3_practical_reference_without_changing_decision() -> None:
    overlay = _overlay_module()
    contract = {
        "context": {"hero": "ethan", "map_id": 2401, "round": 2},
        "baseline": {
            "decision": {
                "action": "可守不抢",
                "current_highest": "玩家A 320,000",
                "risk_band": "防守区",
                "defend_bid": "380,000",
                "stop_price": "520,000",
            },
            "posterior": {
                "decision_value_range": "200,000 / 420,000 / 650,000",
                "match_text": "18/80",
                "status": "matched",
            },
            "layout": {},
        },
        "diagnostics": {
            "v3_practical": {
                "available": True,
                "ready": False,
                "affects_bid": False,
                "active": False,
                "candidate": True,
                "source": "formal_value",
                "mode": "value_floor_watch",
                "status": "watch_raise_candidate",
                "recommendation": "raise_watch",
                "confidence": "medium",
                "source_lanes": "formal_value,underestimate_repair",
                "risk_flags": "value_floor_candidate,q6_under_candidate",
                "reason": "formal value floor lifts underestimation watch",
                "formal_decision_value_p50": 480000,
                "formal_decision_value_p90": 780000,
                "total_value_p90": 980000,
                "baseline_formal_decision_value_p50": 420000,
                "baseline_formal_decision_value_p90": 650000,
                "delta_formal_decision_value_p50": 60000,
                "delta_formal_decision_value_p90": 130000,
                "raw_total_gap_to_formal_p90": 200000,
                "q6_formal_decision_value_p50": 120000,
                "q6_formal_decision_value_p90": 260000,
                "baseline_q6_formal_decision_value_p90": 180000,
                "q6_value_p90": 420000,
                "delta_q6_formal_decision_value_p50": 40000,
                "delta_q6_formal_decision_value_p90": 80000,
                "q6_raw_gap_to_formal_p90": 160000,
            }
        },
    }

    model = overlay._overlay_model(
        {
            "hero": "ethan",
            "map_id": 2401,
            "round": 2,
            "ui_contract": contract,
        }
    )

    assert model["decision"][0] == "可守不抢"
    assert any(section[0] == "v3 实战参考" for section in model["sections"])
    assert any(
        section[0] == "v3 实战参考"
        and "低估风险" in section[1]
        and "正式P90 650,000 -> v3P90 780,000" in section[1]
        and "P90 780,000" in section[1]
        and "ΔP90 130,000" in section[1]
        and "仓库上限ΔP90 200,000" in section[1]
        and "q6上限ΔP90 160,000" in section[1]
        and "证据 formal_value,underestimate_repair" in section[2]
        and "风险 value_floor_candidate,q6_under_candidate" in section[2]
        and "置信 中" in section[2]
        and "不影响正式出价" in section[2]
        for section in model["interaction"]["hover"]["sections"]
    )
    assert any(
        section[0] == "v3 实战参考"
        and "正式P50 420,000" in section[1]
        and "正式q6P90 180,000" in section[1]
        and "仓库上限P90 980,000" in section[1]
        and "q6上限P90 420,000" in section[1]
        and "formal value floor" in section[2]
        for section in model["interaction"]["detail"]["sections"]
    )
    assert any("v3 实战参考提示低估风险" in alert[0] for alert in model["alerts"])
    assert any("正式P90 650,000 -> v3P90 780,000" in alert[0] for alert in model["alerts"])


def test_overlay_uses_v3_formal_decision_with_v2_reference_section() -> None:
    overlay = _overlay_module()
    contract = {
        "context": {"hero": "ethan", "map_id": 2401, "round": 3},
        "baseline": {
            "official": True,
            "affects_bid": True,
            "source": "v3_practical",
            "decision": {
                "action": "小幅进攻",
                "current_highest": "玩家A 500,000",
                "risk_band": "进攻区",
                "defend_bid": "560,000",
                "stop_price": "900,000",
                "evidence": "v3 practical formal",
            },
            "posterior": {
                "decision_value_range": "300,000 / 640,000 / 900,000",
                "match_text": "18/80",
                "status": "matched",
            },
        },
        "v2_reference": {
            "available": True,
            "affects_bid": False,
            "decision": {
                "action": "可守不抢",
                "current_highest": "玩家A 500,000",
                "risk_band": "防守区",
                "defend_bid": "420,000",
                "stop_price": "650,000",
                "evidence": "v2 decision_value",
            },
        },
    }

    model = overlay._overlay_model(
        {
            "hero": "ethan",
            "map_id": 2401,
            "round": 3,
            "ui_contract": contract,
        }
    )

    assert model["decision"][0] == "小幅进攻"
    hover_sections = model["interaction"]["hover"]["sections"]
    assert hover_sections[0][0] == "正式出价 v3"
    assert "来源 v3 practical" in hover_sections[0][2]
    v2_section = next(section for section in hover_sections if section[0] == "v2 对照")
    assert v2_section[1] == "可守不抢"
    assert "停止 650,000" in v2_section[2]
    assert "当前不影响正式出价" in v2_section[2]


def test_overlay_v3_practical_model_eval_contract_chain_labels_baseline_p90() -> None:
    overlay = _overlay_module()
    from bidking_lab.runtime.snapshot import ui_contract_from_artifact

    contract = ui_contract_from_artifact(
        {
            "model_eval": {
                "v3_practical_available": True,
                "v3_practical_ready": True,
                "v3_practical_affects_bid": False,
                "v3_practical_active": False,
                "v3_practical_candidate": True,
                "v3_practical_source": "q6_prior_floor",
                "v3_practical_mode": "q6_prior_floor_watch",
                "v3_practical_status": "watch_q6_prior_floor",
                "v3_practical_recommendation": "raise_watch",
                "v3_practical_confidence": "low_medium",
                "v3_practical_source_lanes": "formal_value+prior_q6_floor",
                "v3_practical_risk_flags": "q6_prior_floor_watch",
                "v3_practical_formal_decision_value_p50": 420000,
                "v3_practical_formal_decision_value_p90": 1399123,
                "v3_practical_baseline_formal_decision_value_p50": 210231,
                "v3_practical_baseline_formal_decision_value_p90": 504178,
                "v3_practical_delta_formal_decision_value_p50": 0,
                "v3_practical_delta_formal_decision_value_p90": 894945,
                "v3_practical_q6_formal_decision_value_p90": 1050000,
                "v3_practical_baseline_q6_formal_decision_value_p90": 300000,
                "v3_practical_delta_q6_formal_decision_value_p90": 750000,
                "v3_practical_total_value_p90": 1510000,
                "v3_practical_q6_value_p90": 1200000,
                "v3_practical_raw_total_gap_to_formal_p90": 110877,
                "v3_practical_q6_raw_gap_to_formal_p90": 150000,
            }
        }
    )

    hover = overlay._ui_contract_hover_sections(contract)
    practical = next(section for section in hover if section[0] == "v3 实战参考")

    assert "正式P90 504,178 -> v3P90 1,399,123" in practical[1]
    assert "ΔP90 894,945" in practical[1]
    assert "仓库上限ΔP90 110,877" in practical[1]
    assert "q6上限ΔP90 150,000" in practical[1]
    assert "证据 formal_value+prior_q6_floor" in practical[2]
    assert "风险 q6_prior_floor_watch" in practical[2]
    assert "置信 中低" in practical[2]
    assert "只读参考，不影响正式出价" in practical[2]


def test_overlay_labels_v3_practical_ceiling_watch() -> None:
    overlay = _overlay_module()
    contract = {
        "diagnostics": {
            "v3_practical": {
                "available": True,
                "ready": True,
                "affects_bid": False,
                "active": False,
                "candidate": True,
                "source": "q6_value_residual",
                "mode": "q6_value_ceiling_watch",
                "status": "watch_q6_value_ceiling",
                "recommendation": "ceiling_watch",
                "confidence": "low_medium",
                "source_lanes": "q6_value_residual",
                "risk_flags": "q6_value_ceiling_watch",
                "formal_decision_value_p50": 520000,
                "formal_decision_value_p90": 820000,
                "baseline_formal_decision_value_p50": 420000,
                "baseline_formal_decision_value_p90": 600000,
                "delta_formal_decision_value_p50": 100000,
                "delta_formal_decision_value_p90": 220000,
            }
        },
    }

    sections = overlay._ui_contract_hover_sections(contract)
    practical = next(section for section in sections if section[0] == "v3 实战参考")

    assert "参考上沿" in practical[1]
    assert "正式P90 600,000 -> v3P90 820,000" in practical[1]
    assert "P90 820,000" in practical[1]
    assert "ΔP90 220,000" in practical[1]
    assert "不影响正式出价" in practical[2]


def test_overlay_v3_practical_passthrough_stays_read_only() -> None:
    overlay = _overlay_module()
    contract = {
        "baseline": {
            "decision": {"action": "开局观察"},
            "posterior": {"decision_value_range": "100,000 / 240,000 / 380,000"},
        },
        "diagnostics": {
            "v3_practical": {
                "available": True,
                "ready": False,
                "affects_bid": False,
                "active": False,
                "candidate": False,
                "status": "baseline_passthrough",
                "recommendation": "baseline",
                "confidence": "low",
                "formal_decision_value_p50": 240000,
                "formal_decision_value_p90": 380000,
                "baseline_formal_decision_value_p50": 240000,
                "baseline_formal_decision_value_p90": 380000,
                "delta_formal_decision_value_p50": 0,
            }
        },
    }

    sections = overlay._ui_contract_hover_sections(contract)
    practical = next(section for section in sections if section[0] == "v3 实战参考")

    assert "未触发" in practical[1]
    assert "P50 240,000" in practical[1]
    assert "正式P90 380,000 -> v3P90 380,000" in practical[1]
    assert "只读参考，不影响正式出价" in practical[2]
    assert overlay._ui_contract_alerts(contract) == []


def test_ahmad_overlay_latest_result_text_falls_back_to_latest_sent() -> None:
    module = _ahmad_overlay_module()

    assert module.AhmadTkOverlay._latest_result_text(  # type: ignore[attr-defined]
        SimpleNamespace(),
        {"latest_result": {"tool": "宝光四鉴", "result": "12"}},
    ) == "宝光四鉴=12"
    assert module.AhmadTkOverlay._latest_result_text(  # type: ignore[attr-defined]
        SimpleNamespace(),
        {"latest_sent": {"tool": "普品扫描", "result": 9}},
    ) == "普品扫描=9"


def test_ahmad_manual_quality_cells_do_not_require_quality_count() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("ahmed"),
        "map_id": Entry("2401"),
        "total_count": Entry("39"),
        "q1_cells": Entry("16"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["total_count"] == 39
    assert ref_inputs["quality_cells"] == {"q1": 16}
    assert ref_inputs["fixed_counts"] == {}
    assert ref_inputs["avg_cells"] == {}


def test_ahmad_manual_values_from_live_summary_keep_victor_zero_and_total_avg() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    data = {
        "context": {"hero": "victor", "map_id": 2404},
        "ahmed_ref": {
            "evidence": {
                "hero": "victor",
                "map_id": 2404,
                "total_count": 21,
                "total_grid_target": 34,
                "avg_cells": {
                    "q1": 1.1428571428571428,
                    "q3": 2.0,
                    "q4": 1.8,
                    "q5": 0,
                    "q6": 1.0,
                },
                "fixed_counts": {"q1": 7, "q3": 8, "q4": 5, "q5": 0, "q6": 1},
                "count_sums": {"q4q5q6": 6},
            }
        },
    }

    values = module.AhmadTkOverlay._manual_values_from_summary(overlay, data)

    assert values["hero"] == "victor"
    assert values["map_id"] == 2404
    assert values["total_count"] == 21
    assert values["total_cells"] == 34
    assert values["total_avg"] == "1.619"
    assert values["q1_avg"] == "1.1429"
    assert values["q1_count"] == 7
    assert values["q1_cells"] == "8"
    assert values["q3_avg"] == "2"
    assert values["q3_count"] == 8
    assert values["q3_cells"] == "16"
    assert values["q4_avg"] == "1.8"
    assert values["q4_count"] == 5
    assert values["q4_cells"] == "9"
    assert values["q5_avg"] == "0"
    assert values["q5_count"] == 0
    assert values["q5_cells"] == "0"
    assert values["q6_avg"] == "1"
    assert values["q6_count"] == 1
    assert values["q6_cells"] == "1"
    assert values["q4q5_count"] == 6


def test_ahmad_manual_values_from_live_summary_derives_counts_from_avg_and_cells() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    data = {
        "context": {"hero": "维克托", "map_id": 2404},
        "ahmed_ref": {
            "evidence": {
                "hero": "victor",
                "map_id": 2404,
                "total_count": 21,
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
                "fixed_counts": {},
            }
        },
    }

    values = module.AhmadTkOverlay._manual_values_from_summary(overlay, data)

    assert values["hero"] == "维克托"
    assert values["q1_count"] == 7
    assert values["q3_count"] == 8
    assert values["q5_count"] == 4
    assert values["q1_cells"] == "8"
    assert values["q3_cells"] == "16"
    assert values["q5_cells"] == "24"


def test_ahmad_manual_values_from_live_summary_does_not_fill_lower_bounds_as_exact_counts() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    data = {
        "context": {"hero": "victor", "map_id": 2404},
        "ahmed_ref": {
            "evidence": {
                "hero": "victor",
                "map_id": 2404,
                "total_count": 21,
                "min_counts": {"q4": 2, "q5": 1},
                "fixed_counts": {},
            }
        },
    }

    values = module.AhmadTkOverlay._manual_values_from_summary(overlay, data)

    assert values["hero"] == "victor"
    assert "q4_count" not in values
    assert "q5_count" not in values


def test_ahmad_manual_values_from_live_summary_does_not_fill_split_lower_bound_as_exact_q1() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    data = {
        "context": {"hero": "aisha", "map_id": 2404},
        "ahmed_ref": {
            "evidence": {
                "hero": "aisha",
                "map_id": 2404,
                "total_count": 21,
                "min_counts": {"q1": 3},
                "fixed_counts": {},
                "split_counts": {"white": 3},
                "split_quality_cells": {"white": 5},
                "split_avg_cells": {"white": 5 / 3},
            }
        },
    }

    values = module.AhmadTkOverlay._manual_values_from_summary(overlay, data)

    assert values["hero"] == "aisha"
    assert values["white_count"] == 3
    assert values["white_cells"] == "5"
    assert "green_count" not in values
    assert "q1_count" not in values
    assert "q1_cells" not in values


def test_ahmad_manual_values_from_live_summary_prefills_aisha_split_low_quality() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    data = {
        "context": {"hero": "aisha", "map_id": 2401},
        "ahmed_ref": {
            "evidence": {
                "hero": "aisha",
                "map_id": 2401,
                "total_count": 33,
                "split_avg_cells": {"white": 1.6666666667, "green": 2.0},
                "split_quality_cells": {"white": 5, "green": 8},
                "split_counts": {"white": 3, "green": 4},
                "fixed_counts": {"q1": 7},
                "quality_cells": {"q1": 13},
            }
        },
    }

    values = module.AhmadTkOverlay._manual_values_from_summary(overlay, data)

    assert values["hero"] == "aisha"
    assert values["white_avg"] == "1.6667"
    assert values["white_count"] == 3
    assert values["white_cells"] == "5"
    assert values["green_avg"] == "2"
    assert values["green_count"] == 4
    assert values["green_cells"] == "8"
    assert values["q1_count"] == 7
    assert values["q1_cells"] == "13"


def test_ahmad_manual_values_from_live_summary_prefers_supported_evidence_hero() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    data = {
        "context": {"hero": "?", "map_id": 2404},
        "ahmed_ref": {
            "evidence": {
                "hero": "victor",
                "map_id": 2404,
            }
        },
    }

    values = module.AhmadTkOverlay._manual_values_from_summary(overlay, data)

    assert values["hero"] == "victor"


def test_ahmad_server_summary_prefers_ref_evidence_hero_when_context_unknown(tmp_path: Path) -> None:
    module = _ahmad_server_module()
    snapshot = {
        "created_at": time.time(),
        "ui_contract": {
            "context": {
                "hero": "?",
                "map_id": 2404,
                "phase": "bidding",
                "session_id": "2404:test",
            }
        },
        "structured_ref_inputs": {
            "hero": "victor",
            "total_count": 6,
            "count_sums": {"q4q5q6": 2},
            "fixed_counts": {"q4": 1, "q5": 0, "q6": 1},
            "avg_cells": {"q4": 1.0, "q5": 0.0, "q6": 3.0},
            "quality_cells": {"q4": 1, "q5": 0, "q6": 3},
        },
    }

    result = module.summarize_snapshot(snapshot, snapshot_path=tmp_path / "latest_snapshot.json")

    assert result["context"]["hero"] == "victor"
    assert result["context"]["is_supported_ref_hero"] is True


def test_ahmad_server_summary_keeps_public_info_marker_soft(tmp_path: Path) -> None:
    module = _ahmad_server_module()
    snapshot = {
        "created_at": time.time(),
        "ui_contract": {
            "context": {
                "hero": "aisha",
                "map_id": 2408,
                "phase": "bidding",
                "session_id": "2408:test",
            },
            "minimap": {
                "status": "available",
                "columns": 10,
                "viewport_rows": 13,
                "items": [
                    {
                        "row": 3,
                        "col": 4,
                        "width": 2,
                        "height": 2,
                        "quality": "q6",
                        "source": "public_info",
                        "layout_source": "public_info",
                        "render_mode": "marker",
                        "shape_key": "22",
                    }
                ],
            },
        },
    }

    result = module.summarize_snapshot(snapshot, snapshot_path=tmp_path / "latest_snapshot.json")

    assert result["minimap"]["items"][0]["render_mode"] == "marker"
    assert result["minimap"]["items"][0]["source"] == "public_info"
    assert result["minimap"]["items"][0]["shape_key"] == "22"


def test_ahmad_server_summary_keeps_old_settlement_review_until_next_session(tmp_path: Path) -> None:
    module = _ahmad_server_module()
    snapshot_path = tmp_path / "latest_snapshot.json"
    snapshot = {
        "created_at": time.time() - 600,
        "phase": "settled",
        "ui_contract": {
            "context": {
                "hero": "victor",
                "map_id": 2404,
                "phase": "settled",
                "session_id": "2404:done",
            },
            "baseline": {
                "decision": {"attack_bid": "450000"},
                "posterior": {},
            },
            "source": {"created_at": time.time() - 600},
            "truth": {
                "available": True,
                "total_value": 520000,
                "total_items": 21,
                "total_cells": 34,
                "q6": {"count": 1, "cells": 3, "value": 160000},
                "top_item": {"name": "test", "value": 160000},
            },
        },
        "structured_ref_inputs": {
            "hero": "victor",
            "total_count": 21,
            "total_cells": 34,
            "avg_cells": {"q4": 1.8, "q5": 0.0},
            "count_sums": {"q4q5q6": 6},
        },
    }

    result = module.summarize_snapshot(snapshot, snapshot_path=snapshot_path)

    assert result["status"] == "ok"
    assert result["reference"]["source"] == "settlement"
    assert result["reference"]["conservative"] != "450,000"
    assert result["reference"]["balanced"] == "520,000"
    assert result["reference"]["aggressive"].startswith("+")
    assert "last Hero Ref estimate" in result["reference"]["note"]
    assert result["truth"]["available"] is True


def test_ahmad_ref_input_summary_shows_quality_lower_bounds() -> None:
    module = _ahmad_server_module()
    summary = module._ref_input_summary(  # type: ignore[attr-defined]
        {
            "evidence": {
                "total_count": 21,
                "fixed_counts": {"q4": 7},
                "min_counts": {"q1": 4, "q3": 2, "q4": 7, "q5": 1},
            }
        }
    )

    assert "下界 白绿≥4，蓝≥2，金≥1" in summary
    assert "紫≥7" not in summary


def test_ahmad_ref_input_summary_shows_aisha_split_low_quality() -> None:
    module = _ahmad_server_module()
    summary = module._ref_input_summary(  # type: ignore[attr-defined]
        {
            "evidence": {
                "total_count": 33,
                "split_avg_cells": {"white": 1.6666666667, "green": 2.0},
                "split_quality_cells": {"white": 5, "green": 8},
                "split_counts": {"white": 3, "green": 4},
                "fixed_counts": {"q1": 7},
                "quality_cells": {"q1": 13},
            }
        }
    )

    assert "白均格 1.67" in summary
    assert "绿均格 2.00" in summary
    assert "分格 白格 5，绿格 8" in summary
    assert "分件 白件 3，绿件 4" in summary
    assert "件数 白绿件 7" in summary


def test_ahmad_manual_inline_derivation_covers_all_qualities_and_totals() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_vars = {}
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "total_count": Entry("20"),
        "total_cells": Entry(""),
        "total_avg": Entry("2.5"),
        "white_avg": Entry("1.5"),
        "white_count": Entry(""),
        "white_cells": Entry("3"),
        "green_avg": Entry("2"),
        "green_count": Entry(""),
        "green_cells": Entry("4"),
        "q1_avg": Entry("2"),
        "q1_count": Entry(""),
        "q1_cells": Entry("4"),
        "q3_avg": Entry("2"),
        "q3_count": Entry(""),
        "q3_cells": Entry("6"),
        "q4_avg": Entry("1.8"),
        "q4_count": Entry(""),
        "q4_cells": Entry("9"),
        "q5_avg": Entry("6"),
        "q5_count": Entry(""),
        "q5_cells": Entry("24"),
        "q6_avg": Entry("3"),
        "q6_count": Entry(""),
        "q6_cells": Entry("6"),
    }

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay)

    assert overlay.manual_entries["total_cells"].get() == "50"
    assert overlay.manual_entries["white_count"].get() == "2"
    assert overlay.manual_entries["green_count"].get() == "2"
    assert overlay.manual_entries["q1_count"].get() == "2"
    assert overlay.manual_entries["q3_count"].get() == "3"
    assert overlay.manual_entries["q4_count"].get() == "5"
    assert overlay.manual_entries["q5_count"].get() == "4"
    assert overlay.manual_entries["q6_count"].get() == "2"


def test_ahmad_manual_inline_derivation_merges_white_green_only_when_q1_is_empty() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_vars = {}
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "white_count": Entry("3"),
        "white_cells": Entry("5"),
        "green_count": Entry("4"),
        "green_cells": Entry("8"),
        "q1_avg": Entry(""),
        "q1_count": Entry(""),
        "q1_cells": Entry(""),
    }

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay)

    assert overlay.manual_entries["q1_count"].get() == "7"
    assert overlay.manual_entries["q1_cells"].get() == "13"
    assert overlay.manual_entries["q1_avg"].get() == "1.8571"

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_vars = {}
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "white_count": Entry("3"),
        "white_cells": Entry("5"),
        "green_count": Entry("4"),
        "green_cells": Entry("8"),
        "q1_avg": Entry("2"),
        "q1_count": Entry(""),
        "q1_cells": Entry(""),
    }

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay)

    assert overlay.manual_entries["q1_avg"].get() == "2"
    assert overlay.manual_entries["q1_count"].get() == ""
    assert overlay.manual_entries["q1_cells"].get() == ""


def test_ahmad_manual_inline_derivation_derives_avg_and_cells_without_overwriting_user_values() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_vars = {}
    overlay._manual_dirty_fields = {"q4_cells"}
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "q1_avg": Entry(""),
        "q1_count": Entry("4"),
        "q1_cells": Entry("8"),
        "q4_avg": Entry("1.8"),
        "q4_count": Entry("5"),
        "q4_cells": Entry("99"),
    }

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay)

    assert overlay.manual_entries["q1_avg"].get() == "2"
    assert overlay.manual_entries["q4_cells"].get() == "99"


def test_ahmad_manual_inline_derivation_accepts_display_rounded_avg() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_vars = {}
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "q3_avg": Entry("1.8462"),
        "q3_count": Entry("13"),
        "q3_cells": Entry(""),
        "q4_avg": Entry("5.3333"),
        "q4_count": Entry(""),
        "q4_cells": Entry("16"),
        "q5_avg": Entry("1.8"),
        "q5_count": Entry("6"),
        "q5_cells": Entry(""),
    }

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay)

    assert overlay.manual_entries["q3_cells"].get() == "24"
    assert overlay.manual_entries["q4_count"].get() == "3"
    assert overlay.manual_entries["q5_cells"].get() == ""


def test_ahmad_manual_state_auto_resets_on_settlement_and_session_change() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    class Status:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2404"),
        "q5_count": Entry("4"),
    }
    overlay.manual_vars = {}
    overlay.manual_buttons = {}
    overlay.manual_status = Status()
    overlay._manual_active = True
    overlay._manual_snapshot = {"hero": "victor"}
    overlay._manual_summary = {"status": "ok"}
    overlay._manual_dirty_fields = {"q5_count"}
    overlay._manual_autofill_values = {"hero": "victor", "map_id": "2404"}
    overlay._manual_live_session_id = "2404:old"
    overlay._manual_programmatic_update = False

    assert module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        {"status": "ok", "context": {"phase": "settled", "session_id": "2404:old"}},
    )
    module.AhmadTkOverlay._reset_manual_state(overlay, "auto")

    assert overlay._manual_active is False
    assert overlay._manual_snapshot == {}
    assert overlay._manual_live_session_id == ""
    assert overlay.manual_entries["hero"].get() == ""
    assert overlay.manual_entries["q5_count"].get() == ""
    assert overlay._manual_dirty_fields == set()
    assert overlay._manual_autofill_values == {}

    overlay.manual_entries["hero"].insert(0, "victor")
    overlay._manual_live_session_id = "2404:old"

    assert module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        {"status": "ok", "context": {"phase": "bidding", "session_id": "2404:new"}},
    )


def test_ahmad_prefill_manual_inputs_uses_derived_quality_counts() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    class Status:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry(),
        "map_id": Entry(),
        "total_count": Entry(),
        "total_cells": Entry(),
        "total_avg": Entry(),
        "q5_avg": Entry(),
        "q5_count": Entry(),
        "q5_cells": Entry(),
        "q4q5_count": Entry(),
    }
    overlay.manual_vars = {}
    overlay.manual_status = Status()
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay._last_summary = {}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {"hero": "victor", "map_id": 2404, "phase": "bidding", "session_id": "2404:live"},
        "ahmed_ref": {
            "evidence": {
                "hero": "victor",
                "map_id": 2404,
                "total_count": 21,
                "avg_cells": {"q5": 6.0},
                "quality_cells": {"q5": 24},
                "fixed_counts": {},
                "count_sums": {"q4q5q6": 6},
            }
        },
    }

    module.AhmadTkOverlay.prefill_manual_inputs(overlay)

    assert overlay.manual_entries["hero"].get() == "victor"
    assert overlay.manual_entries["q5_avg"].get() == "6"
    assert overlay.manual_entries["q5_cells"].get() == "24"
    assert overlay.manual_entries["q5_count"].get() == "4"
    assert overlay.manual_entries["q4q5_count"].get() == "6"
    assert overlay._manual_live_session_id == "2404:live"


def test_ahmad_manual_input_summary_shows_quality_lower_bounds() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)

    summary = module.AhmadTkOverlay._manual_input_summary(
        overlay,
        {
            "total_count": 21,
            "fixed_counts": {"q4": 7},
            "min_counts": {"q1": 4, "q3": 2, "q4": 7, "q6": 1},
        },
    )

    assert "下界 白绿≥4，蓝≥2，红≥1" in summary
    assert "紫≥7" not in summary


def test_ahmad_manual_snapshot_allows_total_avg_and_zero_gold() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
        "total_avg": Entry("1.619"),
        "q4_avg": Entry("1.8"),
        "q5_avg": Entry("0"),
        "q4q5_count": Entry("6"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["total_count"] == 21
    assert abs(ref_inputs["total_cells"] - 33.999) < 1e-9
    assert ref_inputs["avg_cells"] == {"q4": 1.8, "q5": 0.0}
    assert ref_inputs["count_sums"] == {"q4q5q6": 6}


def test_ahmad_manual_snapshot_derives_counts_from_avg_and_cells_and_normalizes_hero() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("维克托"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
        "q1_avg": Entry("1.1428571428571428"),
        "q1_cells": Entry("8"),
        "q3_avg": Entry("2"),
        "q3_cells": Entry("16"),
        "q5_avg": Entry("6"),
        "q5_cells": Entry("24"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    assert snapshot["hero"] == "victor"
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["fixed_counts"] == {"q1": 7, "q3": 8, "q5": 4}
    assert ref_inputs["quality_cells"] == {"q1": 8, "q3": 16, "q5": 24}
    assert ref_inputs["avg_cells"] == {"q1": 1.1428571428571428, "q3": 2.0, "q5": 6.0}


def test_ahmad_manual_snapshot_accepts_display_rounded_avg_when_count_and_cells_match() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("ahmed"),
        "map_id": Entry("2404"),
        "total_count": Entry("24"),
        "q3_avg": Entry("1.8462"),
        "q3_count": Entry("13"),
        "q3_cells": Entry("24"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["fixed_counts"] == {"q3": 13}
    assert ref_inputs["quality_cells"] == {"q3": 24}
    assert ref_inputs["avg_cells"] == {"q3": 24 / 13}


def test_ahmad_manual_snapshot_rejects_over_rounded_one_decimal_avg() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
        "q4_avg": Entry("1.8"),
        "q4_count": Entry("6"),
        "q4_cells": Entry("11"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "紫均格" in error
    assert "不一致" in error


def test_ahmad_manual_snapshot_accepts_aisha_split_and_merged_low_quality() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("艾莎"),
        "map_id": Entry("2401"),
        "total_count": Entry("33"),
        "white_count": Entry("3"),
        "white_cells": Entry("5"),
        "green_avg": Entry("2"),
        "green_cells": Entry("8"),
        "q1_count": Entry("7"),
        "q1_cells": Entry("13"),
        "q3_count": Entry("6"),
        "q3_cells": Entry("12"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    assert snapshot["hero"] == "aisha"
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["split_counts"] == {"white": 3, "green": 4}
    assert ref_inputs["split_quality_cells"] == {"white": 5, "green": 8}
    assert ref_inputs["split_avg_cells"] == {"white": 5 / 3, "green": 2.0}
    assert ref_inputs["fixed_counts"] == {"q1": 7, "q3": 6}
    assert ref_inputs["quality_cells"] == {"q1": 13, "q3": 12}


def test_ahmad_manual_snapshot_keeps_white_only_split_separate_from_q1_avg() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("aisha"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
        "white_count": Entry("3"),
        "white_cells": Entry("5"),
        "q1_avg": Entry("2"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["split_counts"] == {"white": 3}
    assert ref_inputs["split_quality_cells"] == {"white": 5}
    assert ref_inputs["split_avg_cells"] == {"white": 5 / 3}
    assert ref_inputs["avg_cells"] == {"q1": 2.0}
    assert ref_inputs["fixed_counts"] == {}
    assert "quality_cells" not in ref_inputs


def test_ahmad_manual_snapshot_rejects_impossible_avg_count_pair() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
        "q4_count": Entry("3"),
        "q4_avg": Entry("0"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "紫均格" in error
    assert "整数格数" in error


def test_ahmad_manual_snapshot_rejects_fractional_avg_count_product() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
        "q4_count": Entry("4"),
        "q4_avg": Entry("1.8"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "紫均格" in error
    assert "整数格数" in error


def test_ahmad_manual_snapshot_rejects_impossible_avg_cells_pair_without_count() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("维克托"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
        "q4_avg": Entry("1.8"),
        "q4_cells": Entry("8"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "紫均格与紫格" in error
    assert "整数件数" in error


def test_ahmad_manual_overlay_keeps_live_context_and_merges_inputs() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    live_snapshot = {
        "created_at": time.time(),
        "hero": "ahmed",
        "map_id": 2401,
        "round": 1,
        "phase": "bidding",
        "session_id": "2401:live",
        "structured_ref_inputs": {
            "avg_cells": {"q5": 4.6667},
            "fixed_counts": {"q5": 2},
        },
        "ui_contract": {
            "context": {
                "hero": "ahmed",
                "map_id": 2401,
                "round": 1,
                "phase": "bidding",
                "session_id": "2401:live",
            },
            "constraints": {},
            "baseline": {"decision": {}, "posterior": {}},
            "source": {"created_at": time.time()},
        },
    }
    manual_snapshot = {
        "structured_ref_inputs": {
            "total_count": 39,
            "quality_cells": {"q1": 16},
            "avg_cells": {"q3": 1.55},
            "fixed_counts": {},
        }
    }

    overlaid = module.AhmadTkOverlay._snapshot_with_manual_overlay(
        overlay,
        live_snapshot,
        manual_snapshot,
    )

    context = overlaid["ui_contract"]["context"]
    ref_inputs = overlaid["structured_ref_inputs"]
    assert context["session_id"] == "2401:live"
    assert context["round"] == 1
    assert ref_inputs["total_count"] == 39
    assert ref_inputs["quality_cells"] == {"q1": 16}
    assert ref_inputs["avg_cells"] == {"q5": 4.6667, "q3": 1.55}
    assert ref_inputs["fixed_counts"] == {"q5": 2}
    assert overlaid["ui_contract"]["constraints"]["structured_ref_inputs"] == ref_inputs


def test_ahmad_server_marks_sparse_exact_total_prior_as_fast_path(tmp_path: Path) -> None:
    module = _ahmad_server_module()
    snapshot = {
        "created_at": time.time(),
        "hero": "ahmed",
        "map_id": 2401,
        "phase": "bidding",
        "session_id": "2401:live",
        "structured_ref_inputs": {"total_count": 33},
        "ui_contract": {
            "context": {
                "hero": "ahmed",
                "map_id": 2401,
                "phase": "bidding",
                "session_id": "2401:live",
            },
            "constraints": {"public_info": {}},
            "baseline": {"decision": {}, "posterior": {}},
            "source": {"created_at": time.time()},
        },
    }

    result = module.summarize_snapshot(snapshot, snapshot_path=tmp_path / "latest_snapshot.json")

    assert result["reference"]["readiness"] == "sparse_exact_prior"
    assert result["reference"]["source"] == "ref_prior"
    assert any(flag["label"] == "宽约束快速" for flag in result["flags"])
    assert not any(flag["label"] == "总件估计" for flag in result["flags"])


def test_ahmad_overlay_user_close_runs_exit_cleanup_once(monkeypatch, tmp_path: Path) -> None:
    module = _ahmad_overlay_module()
    cleanup_calls: list[tuple[tuple[int, ...], tuple[Path, ...]]] = []
    destroyed: list[bool] = []

    monkeypatch.setattr(
        module,
        "_cleanup_exit_targets",
        lambda pids, lock_paths: cleanup_calls.append((tuple(pids), tuple(lock_paths))),
    )
    overlay = object.__new__(module.AhmadTkOverlay)
    lock_path = tmp_path / "monitor.lock"
    overlay._stop_pids_on_exit = (123,)
    overlay._cleanup_lock_paths = (lock_path,)
    overlay._exit_cleanup_done = False
    overlay._hide_minimap_popup = lambda: None
    overlay._hide_pinned_minimap = lambda: None
    overlay.root = SimpleNamespace(destroy=lambda: destroyed.append(True))

    module.AhmadTkOverlay._on_user_close(overlay)
    module.AhmadTkOverlay._run_exit_cleanup(overlay)

    assert cleanup_calls == [((123,), (lock_path,))]
    assert destroyed == [True]
