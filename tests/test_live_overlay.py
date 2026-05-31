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


def test_demo_snapshot_has_compact_overlay_sections() -> None:
    overlay = _overlay_module()

    lines = overlay._summary_lines(overlay._demo_snapshot())

    assert any(line.startswith("决策:") for line in lines)
    assert any(line.startswith("价值:") for line in lines)
    assert any(line.startswith("仓储:") for line in lines)
    assert any(line.startswith("红货:") for line in lines)
    assert any(line.startswith("布局:") for line in lines)
    assert any(line.startswith("道具:") for line in lines)
