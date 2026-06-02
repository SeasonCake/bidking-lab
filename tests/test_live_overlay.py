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


def test_overlay_window_geometry_scales_above_old_small_default() -> None:
    overlay = _overlay_module()

    geometry = overlay._default_window_geometry(1920, 1080)

    assert geometry.startswith("920x680")


def test_overlay_snapshot_signature_changes_when_file_changes(tmp_path: Path) -> None:
    overlay = _overlay_module()
    snapshot = tmp_path / "latest_snapshot.json"
    snapshot.write_text('{"a": 1}', encoding="utf-8")
    first = overlay._snapshot_file_signature(snapshot)

    snapshot.write_text('{"a": 1, "b": 2}', encoding="utf-8")
    second = overlay._snapshot_file_signature(snapshot)

    assert first != second


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
        "决策价值",
        "仓储",
        "红货 q6",
        "布局",
    ]
    assert any(section[0] == "鉴影命中" for section in model["sections"])
    assert any(alert[0].startswith("q6 P90") for alert in model["alerts"])
    assert any(alert[0].startswith("q6 件数/格数低于先验") for alert in model["alerts"])


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
    assert model["title"] == "AISHA  ·  map 2501  ·  R4"
    assert model["decision"][0] == "可守不抢"
    assert model["metrics"][0][1] == "300,000 / 500,000 / 700,000"
    assert any("UI契约 q6 风险参考" in alert[0] for alert in model["alerts"])
    assert any("aisha_deep_floor1 tail-risk shadow" in alert[0] for alert in model["alerts"])


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
        "fallback价值",
        "180,000 / 280,000 / 420,000",
        "v1低置信 / 22/80",
        "warn",
    )
    fallback_section = next(
        section for section in model["sections"] if section[0] == "Fallback 出价参考"
    )
    assert "探价 180,000" in fallback_section[1]
    assert "防守 196,000" in fallback_section[1]
    assert "抢仓 252,000" in fallback_section[1]
    assert "停止 420,000" in fallback_section[1]
    assert "对手：玩家A 500,000 过热区" in fallback_section[2]
    assert "补信息：优先补轮廓或具体物品" in fallback_section[2]
    assert any("v1 fallback 已生成低置信参考" in alert[0] for alert in model["alerts"])
