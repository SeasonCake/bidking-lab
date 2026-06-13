from __future__ import annotations

import ast
import importlib.util
import json
import queue
from pathlib import Path
import sys
from types import SimpleNamespace
import time
import zipfile


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


def _class_method_ast(module, class_name: str, method_name: str) -> ast.FunctionDef:
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method_name:
                    return child
    raise AssertionError(f"{class_name}.{method_name} not found")


def test_ahmad_summary_diagnostic_log_records_display_ref_inputs(tmp_path: Path) -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.snapshot_path = tmp_path / "latest_snapshot.json"
    overlay._manual_active = True
    overlay.settlement_values_hidden = True
    overlay._last_summary_log_signature = None
    summary = {
        "status": "ok",
        "context": {
            "hero": "ahmed",
            "map_id": 2401,
            "round": 3,
            "phase": "settled",
            "session_id": "s1",
        },
        "reference": {
            "source": "ref_v0",
            "balanced": "685,641",
            "v3_balanced": "477,562",
            "ref_minus_v3_balanced": "+208,079",
        },
        "red": {"uncertainty_summary": "未锁 白绿10/15/15"},
        "evidence": {
            "ref_input_summary": "总件 38 · 总格 83 · 金均价 34288.75",
            "candidate_summary": "总件 38 · 总格 83",
            "next_info_hint": "优先补白绿件数或均格",
            "public_numeric_summary": "金均价 34288.75",
            "diagnostics": "public_q5_avg_value;quality_value_q5_count_derived",
            "manual_overlay": True,
        },
        "ahmed_ref": {
            "status": "ok",
            "combo_count": 12,
            "evidence": {
                "source_notes": [
                    "public_q5_avg_value",
                    "quality_value_q5_count_derived",
                ],
                "fixed_counts": {"q5": 4},
                "avg_values": {"q5": 34288.75},
                "quality_values": {"q5": 137155},
            },
        },
        "minimap": {"summary_text": "4 件 · public_info", "quality_counts": {"q6": 1}},
        "diagnostics": {
            "rare_signals": {
                "present": True,
                "summary": "终极审计:diagnostic_only / 金均价:ref_v0_constraint",
                "role_counts": {"diagnostic_only": 1, "ref_v0_constraint": 1},
                "actions": [
                    {
                        "action_id": 100121,
                        "label": "终极审计",
                        "semantic": "total_value",
                        "ref_v0_role": "diagnostic_only",
                        "result": 728211,
                    }
                ],
                "public_info": [
                    {
                        "info_id": 200037,
                        "label": "金均价",
                        "semantic": "q5_avg_value",
                        "ref_v0_role": "ref_v0_constraint",
                        "value": 34288.75,
                    }
                ],
            },
        },
        "truth": {
            "available": True,
            "total_value": 728211,
            "total_items": 38,
            "total_cells": 83,
            "q6": {"count": 3, "cells": 7, "value": 301000},
        },
        "flags": [{"label": "公开信息", "level": "neutral", "detail": "金均价 34288.75"}],
    }

    module.AhmadTkOverlay._record_summary_diagnostic(
        overlay,
        summary,
        render_mode="manual_overlay_settled",
    )
    module.AhmadTkOverlay._record_summary_diagnostic(
        overlay,
        summary,
        render_mode="manual_overlay_settled",
    )

    rows = (tmp_path / module.SUMMARY_DIAGNOSTIC_LOG).read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    row = json.loads(rows[0])
    assert row["render_mode"] == "manual_overlay_settled"
    assert row["manual_active"] is True
    assert row["settlement_values_hidden"] is True
    assert row["reference"]["balanced"] == "685,641"
    assert row["evidence"]["public_numeric_summary"] == "金均价 34288.75"
    assert row["evidence"]["candidate_summary"] == "总件 38 · 总格 83"
    assert row["evidence"]["next_info_hint"] == "优先补白绿件数或均格"
    assert row["ref_v0"]["evidence"]["avg_values"] == {"q5": 34288.75}
    assert row["ref_v0"]["evidence"]["fixed_counts"] == {"q5": 4}
    assert row["truth"]["total_value"] == 728211
    assert row["diagnostics"]["rare_signals"]["present"] is True
    assert row["diagnostics"]["rare_signals"]["role_counts"] == {
        "diagnostic_only": 1,
        "ref_v0_constraint": 1,
    }
    assert row["diagnostics"]["rare_signals"]["actions"][0]["action_id"] == 100121


def test_ahmad_portable_diagnostic_profile_skips_continuous_ui_summary(tmp_path: Path) -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.snapshot_path = tmp_path / "latest_snapshot.json"
    overlay.diagnostic_profile = "portable"
    overlay._manual_active = False
    overlay.settlement_values_hidden = False
    overlay._last_summary_log_signature = None

    module.AhmadTkOverlay._record_summary_diagnostic(
        overlay,
        {"status": "ok", "context": {"session_id": "s1"}},
        render_mode="live",
    )

    assert not (tmp_path / module.SUMMARY_DIAGNOSTIC_LOG).exists()
    assert module._normalize_diagnostic_profile("stable") == "portable"


def test_ahmad_topmost_toggle_updates_root_and_popups() -> None:
    module = _ahmad_overlay_module()

    class Window:
        def __init__(self) -> None:
            self.attrs: list[tuple[str, bool]] = []

        def attributes(self, key: str, value: bool) -> None:
            self.attrs.append((key, value))

    class Button:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Tip:
        def __init__(self) -> None:
            self.text = ""

        def set_text(self, text: str) -> None:
            self.text = text

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = Window()
    overlay._minimap_popup = Window()
    overlay._pinned_minimap_popup = Window()
    overlay.topmost_button = Button()
    overlay.topmost_tip = Tip()
    overlay.topmost_enabled = True

    assert module.AhmadTkOverlay.toggle_topmost(overlay) == "break"

    assert overlay.topmost_enabled is False
    assert overlay.root.attrs[-1] == ("-topmost", False)
    assert overlay._minimap_popup.attrs[-1] == ("-topmost", False)
    assert overlay._pinned_minimap_popup.attrs[-1] == ("-topmost", False)
    assert overlay.topmost_button.kwargs["text"] == "T"
    assert overlay.topmost_tip.text == module.TOPMOST_OFF_TIP


def test_pinned_minimap_sync_skips_when_user_detached() -> None:
    module = _ahmad_overlay_module()

    class Popup:
        def __init__(self) -> None:
            self.x = 120
            self.y = 80
            self.geometry_calls: list[str] = []

        def winfo_x(self) -> int:
            return self.x

        def winfo_y(self) -> int:
            return self.y

        def winfo_width(self) -> int:
            return 292

        def winfo_height(self) -> int:
            return 382

        def geometry(self, value: str) -> None:
            self.geometry_calls.append(value)

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = type(
        "Root",
        (),
        {
            "winfo_screenwidth": lambda self: 1920,
            "winfo_screenheight": lambda self: 1080,
        },
    )()
    popup = Popup()
    overlay._pinned_minimap_popup = popup
    overlay._pinned_offset = (40, 12)
    overlay._pinned_minimap_follow = False

    module.AhmadTkOverlay._sync_pinned_minimap_position(overlay, root_x=0, root_y=0)

    assert popup.geometry_calls == []


def test_pinned_minimap_drag_detaches_from_main_window() -> None:
    module = _ahmad_overlay_module()

    class Popup:
        def __init__(self) -> None:
            self.x = 100
            self.y = 200
            self.geometry_calls: list[str] = []

        def winfo_x(self) -> int:
            return self.x

        def winfo_y(self) -> int:
            return self.y

        def winfo_width(self) -> int:
            return 292

        def winfo_height(self) -> int:
            return 382

        def geometry(self, value: str) -> None:
            self.geometry_calls.append(value)
            if value.startswith("+"):
                parts = value.split("+")
                self.x = int(parts[1])
                self.y = int(parts[2])

    class Title:
        def __init__(self) -> None:
            self.text = "常驻地图"
            self.updates: list[str] = []

        def cget(self, key: str) -> str:
            if key == "text":
                return self.text
            raise KeyError(key)

        def configure(self, **kwargs: str) -> None:
            if "text" in kwargs:
                self.text = str(kwargs["text"])
                self.updates.append(self.text)

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = type(
        "Root",
        (),
        {
            "winfo_screenwidth": lambda self: 1920,
            "winfo_screenheight": lambda self: 1080,
        },
    )()
    popup = Popup()
    overlay._pinned_minimap_popup = popup
    overlay._pinned_offset = (50, 10)
    overlay._pinned_minimap_follow = True
    overlay._pinned_minimap_drag_offset = (5, 5)
    overlay._pinned_title = Title()

    class Event:
        x_root = 150
        y_root = 250

    assert module.AhmadTkOverlay._drag_pinned_minimap(overlay, Event()) == "break"
    assert overlay._pinned_minimap_follow is False
    assert overlay._pinned_offset is None
    assert popup.geometry_calls == ["+145+245"]
    assert overlay._pinned_title.text.endswith(module.MINIMAP_PINNED_FREE_SUFFIX)


def test_ahmad_taskbar_mode_switches_borderless_flag() -> None:
    module = _ahmad_overlay_module()

    class Root:
        def __init__(self) -> None:
            self.overrideredirect_values: list[bool] = []

        def overrideredirect(self, value: bool) -> None:
            self.overrideredirect_values.append(value)

    root = Root()

    module._apply_taskbar_mode(root, show_taskbar=False)  # type: ignore[attr-defined]
    module._apply_taskbar_mode(root, show_taskbar=True)  # type: ignore[attr-defined]

    assert root.overrideredirect_values == [True, False]


def test_ahmad_windows_toolwindow_enabled_for_floating_overlay(monkeypatch) -> None:
    module = _ahmad_overlay_module()

    class Widget:
        def __init__(self) -> None:
            self.attrs: list[tuple[str, bool]] = []

        def attributes(self, key: str, value: bool) -> None:
            self.attrs.append((key, value))

    widget = Widget()
    monkeypatch.setattr(module.os, "name", "nt", raising=False)

    module._apply_windows_toolwindow(widget, enabled=True)  # type: ignore[attr-defined]
    module._apply_windows_toolwindow(widget, enabled=False)  # type: ignore[attr-defined]

    assert widget.attrs == [("-toolwindow", True)]


def test_ahmad_compute_ui_scale_uses_min_ratio_and_clamps() -> None:
    module = _ahmad_overlay_module()

    assert module.compute_ui_scale(
        440,
        397,
        base_width=module.MINI_BASE_WIDTH,
        base_height=module.MINI_BASE_HEIGHT,
    ) == 1.0
    enlarged = module.compute_ui_scale(
        880,
        794,
        base_width=module.MINI_BASE_WIDTH,
        base_height=module.MINI_BASE_HEIGHT,
    )
    assert enlarged == module.UI_SCALE_MAX
    mid = module.compute_ui_scale(
        500,
        450,
        base_width=module.MINI_BASE_WIDTH,
        base_height=module.MINI_BASE_HEIGHT,
    )
    assert mid == min(500 / module.MINI_BASE_WIDTH, 450 / module.MINI_BASE_HEIGHT)


def test_ahmad_scaled_font_rounds_with_floor() -> None:
    module = _ahmad_overlay_module()

    assert module.scaled_font(module.FONT_UI, 12, "bold", scale=1.25) == (
        module.FONT_UI,
        15,
        "bold",
    )
    assert module.scaled_font(module.FONT_NUMERIC, 15, scale=0.5) == (
        module.FONT_NUMERIC,
        8,
    )


def test_ahmad_compute_fitted_mini_height_clamps() -> None:
    module = _ahmad_overlay_module()

    assert module.compute_fitted_mini_height(300) == 320
    assert module.compute_fitted_mini_height(10) == 320
    assert module.compute_fitted_mini_height(2000) == 1500
    assert module.compute_fitted_mini_height(302) == 320
    assert module.compute_fitted_mini_height(303) == 321


def test_ahmad_compute_mini_ui_scale_follows_width_only() -> None:
    module = _ahmad_overlay_module()

    assert module.compute_mini_ui_scale(440) == 1.0
    assert module.compute_mini_ui_scale(550) == 550 / module.MINI_BASE_WIDTH
    assert module.compute_mini_ui_scale(880) == module.UI_SCALE_MAX


def test_ahmad_mini_resize_growth_shrinks_on_negative_deltas() -> None:
    module = _ahmad_overlay_module()

    assert module.mini_resize_growth(40, 10) == 40
    assert module.mini_resize_growth(10, 40) == 40
    assert module.mini_resize_growth(-40, -10) == -40
    assert module.mini_resize_growth(-10, -40) == -40
    assert module.mini_resize_growth(-30, 5) == -30


def test_ahmad_end_resize_syncs_ui_scale() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.details_expanded = False
    overlay._ui_scale = 1.0
    overlay._minimap_data = {}
    overlay._scaled_layout_specs = []
    overlay.style = SimpleNamespace(configure=lambda **kwargs: None)
    overlay.outer = SimpleNamespace(winfo_children=lambda: [])
    applied: list[tuple[int, bool]] = []
    overlay.root = SimpleNamespace(geometry=lambda: "520x360+0+0", update_idletasks=lambda: None, after_cancel=lambda _id: None)
    overlay._apply_mini_resize_layout = lambda width, finalize=False: applied.append((width, finalize))  # type: ignore[method-assign]

    assert module.AhmadTkOverlay._end_resize(overlay, SimpleNamespace()) == "break"
    assert applied == [(520, True)]


def test_ahmad_apply_mini_resize_layout_uses_estimate_during_drag() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.details_expanded = False
    overlay._ui_scale = 1.0
    overlay._minimap_data = {}
    overlay._scaled_layout_specs = []
    overlay.style = SimpleNamespace(configure=lambda **kwargs: None)
    overlay.outer = SimpleNamespace(winfo_children=lambda: [])
    overlay.shell = SimpleNamespace(winfo_reqheight=lambda: 330)
    overlay.root = SimpleNamespace(
        update_idletasks=lambda: None,
        geometry=lambda: "520x348+0+0",
    )
    applied: list[str] = []
    measured: list[int] = []

    overlay._apply_ui_scale = lambda: None  # type: ignore[method-assign]
    overlay._apply_window_geometry = lambda size, flush=True: applied.append(size)  # type: ignore[method-assign]
    overlay._measure_window_height_for_width = lambda width, probe_height=None: measured.append(width) or 400  # type: ignore[method-assign]

    module.AhmadTkOverlay._apply_mini_resize_layout(overlay, 520, finalize=False)
    module.AhmadTkOverlay._apply_mini_resize_layout(overlay, 520, finalize=True)

    assert applied == ["520x348", "520x400"]
    assert measured == [520]


def test_ahmad_ui_prefs_roundtrip(tmp_path) -> None:
    module = _ahmad_overlay_module()
    prefs_path = tmp_path / module.UI_PREFS_FILENAME
    snapshot_path = tmp_path / "latest_snapshot.json"
    payload = {
        "schema_version": module.UI_PREFS_SCHEMA_VERSION,
        "theme_name": "dark",
        "details_expanded": False,
        "ui_scale": 1.12,
        "window_position": [120, 40],
        "custom_mini_size": [520, 360],
        "custom_details_size": None,
    }
    module.write_ui_prefs(prefs_path, payload)
    loaded = module.read_ui_prefs(prefs_path)
    assert loaded == {
        "schema_version": module.UI_PREFS_SCHEMA_VERSION,
        "theme_name": "dark",
        "details_expanded": False,
        "ui_scale": 1.12,
        "window_position": [120, 40],
        "custom_mini_size": [520, 360],
        "custom_details_size": None,
    }
    assert module.ui_prefs_path_for_snapshot(snapshot_path) == prefs_path


def test_ahmad_ui_prefs_clamps_invalid_sizes() -> None:
    module = _ahmad_overlay_module()

    normalized = module.normalize_ui_prefs_payload(
        {
            "custom_mini_size": [200, 100],
            "custom_details_size": [2000, 5000],
        }
    )
    assert normalized is not None
    assert normalized["custom_mini_size"] == [430, 320]
    assert normalized["custom_details_size"] == [1200, 1500]


def test_ahmad_canvas_draw_size_uses_layout_not_stale_default() -> None:
    module = _ahmad_overlay_module()
    canvas = SimpleNamespace(
        update_idletasks=lambda: None,
        winfo_width=lambda: 400,
        winfo_height=lambda: 360,
    )

    assert module.canvas_draw_size(canvas, min_width=260, min_height=320) == (400, 360)


def test_ahmad_draw_minimap_empty_state_centers_in_visible_canvas() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    rects: list[tuple[int, int, int, int]] = []
    texts: list[tuple[float, float]] = []

    class Canvas:
        def update_idletasks(self) -> None:
            return None

        def winfo_width(self) -> int:
            return 400

        def winfo_height(self) -> int:
            return 360

        def delete(self, _tag: str) -> None:
            return None

        def configure(self, **_kwargs: Any) -> None:
            return None

        def create_rectangle(self, x0: int, y0: int, x1: int, y1: int, **_kwargs: Any) -> int:
            rects.append((x0, y0, x1, y1))
            return 1

        def create_line(self, *_args: Any, **_kwargs: Any) -> int:
            return 1

        def create_text(self, x: float, y: float, **_kwargs: Any) -> int:
            texts.append((x, y))
            return 1

    module.AhmadTkOverlay._draw_minimap(
        overlay,
        Canvas(),
        {},
        None,
        min_width=260,
        min_height=320,
    )
    x0, y0, x1, y1 = rects[0]
    grid_w = x1 - x0
    grid_h = y1 - y0
    assert x0 == round((400 - grid_w) / 2)
    assert y0 == round((360 - grid_h) / 2)
    assert texts[0] == (200.0, 180.0)


def test_ahmad_current_window_size_prefers_geometry_over_winfo() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.details_expanded = False
    overlay.root = SimpleNamespace(
        geometry=lambda: "440x360+20+0",
        winfo_width=lambda: 920,
        winfo_height=lambda: 880,
        update_idletasks=lambda: None,
    )
    overlay.shell = SimpleNamespace(winfo_reqwidth=lambda: 420, winfo_reqheight=lambda: 342)

    assert module.AhmadTkOverlay._current_window_size(overlay) == (440, 360)


def test_ahmad_set_details_mode_mini_restores_saved_size_and_scale() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.details_expanded = True
    overlay._mini_layout_snapshot = ((480, 360), (480, 360), 0.91)
    overlay._custom_mini_size = (480, 360)
    overlay._ui_scale = 1.6
    overlay._minimap_data = {}
    overlay._scaled_layout_specs = []
    overlay.mode_button = SimpleNamespace(configure=lambda **kwargs: None)
    overlay.details_card = SimpleNamespace(pack_forget=lambda: None)
    overlay.minimap_card = SimpleNamespace(pack_forget=lambda: None)
    overlay.outer = SimpleNamespace(winfo_children=lambda: [])
    overlay.style = SimpleNamespace(configure=lambda **kwargs: None)
    applied: list[str] = []
    scales: list[float] = []
    geometry_state = {"value": "920x880+20+0"}

    def _geometry(value: str | None = None) -> str:
        if value is not None:
            geometry_state["value"] = value
        return geometry_state["value"]

    overlay.root = SimpleNamespace(
        minsize=lambda *args: None,
        update_idletasks=lambda: None,
        geometry=_geometry,
        winfo_reqheight=lambda: 348,
        after_cancel=lambda _id: None,
    )

    def _apply(size: str, flush: bool = True) -> None:
        applied.append(size)
        geometry_state["value"] = f"{size}+20+0"

    overlay._apply_window_geometry = _apply  # type: ignore[method-assign]
    overlay._apply_layout_scale = lambda: None  # type: ignore[method-assign]
    overlay._apply_button_style_scale = lambda: None  # type: ignore[method-assign]
    overlay._apply_font_scale = lambda widget: None  # type: ignore[method-assign]
    overlay.shell = SimpleNamespace(winfo_reqheight=lambda: 330)
    overlay.details_expanded = False

    module.AhmadTkOverlay._restore_mini_layout_after_details(overlay)
    scales.append(float(overlay._ui_scale))

    assert applied == ["480x348"]
    assert overlay._custom_mini_size == (480, 348)
    assert scales[-1] == module.compute_mini_ui_scale(480)
    assert scales[-1] < 1.6


def test_ahmad_export_button_is_mini_visible_and_map_button_keeps_preview_hover() -> None:
    module = _ahmad_overlay_module()
    init = _class_method_ast(module, "AhmadTkOverlay", "__init__")

    export_parent = None
    map_tip_assigned = False
    map_button_binds: list[str] = []
    for node in ast.walk(init):
        if (
            isinstance(node, ast.Assign)
            and node.targets
            and isinstance(node.targets[0], ast.Attribute)
            and isinstance(node.targets[0].value, ast.Name)
            and node.targets[0].value.id == "self"
            and node.targets[0].attr == "export_diag_button"
            and isinstance(node.value, ast.Call)
            and node.value.args
            and isinstance(node.value.args[0], ast.Name)
        ):
            export_parent = node.value.args[0].id
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "bind"
            and isinstance(node.func.value, ast.Attribute)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "self"
            and node.func.value.attr == "map_button"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            map_button_binds.append(str(node.args[0].value))
        if (
            isinstance(node, ast.Assign)
            and node.targets
            and isinstance(node.targets[0], ast.Attribute)
            and isinstance(node.targets[0].value, ast.Name)
            and node.targets[0].value.id == "self"
            and node.targets[0].attr == "map_tip"
        ):
            map_tip_assigned = True

    assert export_parent == "header_right"
    assert "<Enter>" in map_button_binds
    assert "<Leave>" in map_button_binds
    assert "<Button-1>" in map_button_binds
    assert map_tip_assigned is False


def test_ahmad_export_diagnostic_tip_tells_users_to_send_zip_for_abnormal_cases(tmp_path: Path) -> None:
    module = _ahmad_overlay_module()
    text = module._diagnostic_export_tip(tmp_path / "latest_snapshot.json")  # type: ignore[attr-defined]

    assert "异常" in text
    assert "生成诊断 zip" in text
    assert "发群里" in text
    assert "log 排查" in text


def test_ahmad_ui_runtime_status_dedupes_repeated_state(tmp_path: Path) -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.snapshot_path = tmp_path / "latest_snapshot.json"
    overlay._last_signature = (1, 2)
    overlay._last_summary = {
        "status": "ok",
        "context": {"session_id": "2401:test", "phase": "bidding"},
        "reference": {"source": "ref_v0"},
    }

    overlay._record_ui_runtime_status(
        "idle_no_change",
        snapshot_signature=(1, 2),
        capture_status={"source": "windivert", "raw_packets": 1},
    )
    status_path = tmp_path / module.UI_RUNTIME_STATUS
    first = status_path.read_text(encoding="utf-8")

    overlay._record_ui_runtime_status(
        "idle_no_change",
        snapshot_signature=(1, 2),
        capture_status={"source": "windivert", "raw_packets": 1},
    )
    assert status_path.read_text(encoding="utf-8") == first

    overlay._record_ui_runtime_status(
        "idle_no_change",
        snapshot_signature=(1, 2),
        capture_status={"source": "windivert", "raw_packets": 2},
    )
    updated = json.loads(status_path.read_text(encoding="utf-8"))
    assert updated["capture"]["raw_packets"] == 2


def test_ahmad_export_diagnostic_package_collects_snapshot_raw_and_ui_log(tmp_path: Path) -> None:
    module = _ahmad_overlay_module()
    snapshot_path = tmp_path / "latest_snapshot.json"
    raw_json = tmp_path / "fatbeans_webhook_live.json"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_tables_dir = tmp_path / "data" / "raw" / "tables"
    raw_tables_dir.mkdir(parents=True)
    raw_jsonl = raw_dir / "fatbeans_webhook_live.jsonl"
    ui_log = tmp_path / module.SUMMARY_DIAGNOSTIC_LOG
    ui_runtime = tmp_path / module.UI_RUNTIME_STATUS
    monitor_stderr = tmp_path / "monitor.stderr.log"
    raw_json.write_text('[{"SortID":1}]', encoding="utf-8")
    raw_jsonl.write_text('{"SortID":1}\n', encoding="utf-8")
    ui_log.write_text('{"render_mode":"live"}\n', encoding="utf-8")
    ui_runtime.write_text('{"event":"idle_no_change"}', encoding="utf-8")
    monitor_stderr.write_text("[listen] ok\n", encoding="utf-8")
    for name in ("BidMap.txt", "Drop.txt", "Item.txt"):
        (raw_tables_dir / name).write_text(name, encoding="utf-8")
    snapshot = {
        "schema_version": 1,
        "created_at": 123456.0,
        "session_id": "2401:test",
        "hero": "ahmed",
        "map_id": 2401,
        "round": 2,
        "phase": "bidding",
        "n_trials": 500,
        "roi_trials": 250,
        "shadow_trials": 80,
        "formal_mode": "v3_practical",
        "raw_capture": str(raw_json),
        "raw_capture_jsonl": str(raw_jsonl),
    }
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Tip:
        def __init__(self) -> None:
            self.text = ""

        def set_text(self, text: str) -> None:
            self.text = text

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.snapshot_path = snapshot_path
    overlay._last_live_snapshot = snapshot
    overlay._last_summary = {
        "status": "ok",
        "context": {"session_id": "2401:test", "hero": "ahmed"},
        "reference": {"source": "ref_v0", "readiness": "live_ready"},
        "evidence": {
            "candidate_summary": "总件 38 · 总格 83",
            "next_info_hint": "优先补白绿件数或均格",
        },
    }
    overlay._last_live_summary = {}
    overlay.status = Widget()
    overlay.manual_status = Widget()
    overlay.export_diag_tip = Tip()
    overlay.show_taskbar = True

    assert module.AhmadTkOverlay.export_diagnostic_package(overlay) == "break"

    export_path = overlay.last_diagnostic_export_path
    assert export_path is not None
    assert export_path.is_file()
    assert str(export_path.resolve()) in overlay.export_diag_tip.text
    assert overlay.status.kwargs["text"] == "已导出诊断"
    with zipfile.ZipFile(export_path) as archive:
        names = set(archive.namelist())
        assert "latest_snapshot.json" in names
        assert "fatbeans_webhook_live.json" in names
        assert "raw/fatbeans_webhook_live.jsonl" in names
        assert module.SUMMARY_DIAGNOSTIC_LOG in names
        assert module.UI_RUNTIME_STATUS in names
        assert "monitor.stderr.log" in names
        assert "hero_ref_current_summary.json" in names
        assert "BUILD_EXPORT_MANIFEST.json" in names
        manifest = json.loads(archive.read("BUILD_EXPORT_MANIFEST.json").decode("utf-8"))
        assert manifest["version"]["schema_version"] == 1
        assert manifest["parameters"]["formal_mode"] == "v3_practical"
        assert manifest["parameters"]["n_trials"] == 500
        assert manifest["current_summary"]["candidate_summary"] == "总件 38 · 总格 83"
        assert manifest["current_summary"]["next_info_hint"] == "优先补白绿件数或均格"
        assert manifest["startup"]["launch_mode"] == "taskbar"
        assert manifest["startup"]["show_taskbar"] is True
        assert manifest["package"]["is_public_safe"] is False
        assert manifest["package"]["includes_raw_tables"] is True
        assert manifest["log_summary"]["raw_tables"]["present"] is True
        assert manifest["log_summary"]["raw_tables"]["required_present"] is True
        assert manifest["log_summary"]["diagnostic_profile"] == "engineering"
        assert manifest["log_summary"]["continuous_ui_summary"] is True
        assert manifest["log_summary"]["export_includes_raw"] is True
        assert manifest["log_summary"]["export_includes_ui_summary"] is True
        assert manifest["log_summary"]["latest_snapshot"]["exists"] is True
        assert "ui_health" in manifest["log_summary"]
        assert manifest["log_summary"]["ui_runtime_status"]["exists"] is True
        assert manifest["log_summary"]["monitor_stderr"]["exists"] is True
        assert manifest["log_summary"]["ui_summary"]["exists"] is True
        assert manifest["log_summary"]["included_count"] >= 4


def test_ahmad_diagnostic_export_works_without_latest_snapshot(tmp_path: Path) -> None:
    module = _ahmad_overlay_module()
    snapshot_path = tmp_path / "latest_snapshot.json"
    ui_runtime = tmp_path / module.UI_RUNTIME_STATUS
    monitor_stderr = tmp_path / "monitor.stderr.log"
    monitor_lock = tmp_path / "monitor.lock"
    ui_runtime.write_text(
        json.dumps({"event": "waiting_for_snapshot", "capture": {"wait_state": "no_capture_status"}}),
        encoding="utf-8",
    )
    monitor_stderr.write_text("[error] pydivert is not installed\n", encoding="utf-8")
    monitor_lock.write_text('{"pid":1234}', encoding="utf-8")

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Tip:
        def __init__(self) -> None:
            self.text = ""

        def set_text(self, text: str) -> None:
            self.text = text

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.snapshot_path = snapshot_path
    overlay._last_live_snapshot = {}
    overlay._last_summary = {}
    overlay._last_live_summary = {}
    overlay.status = Widget()
    overlay.manual_status = Widget()
    overlay.export_diag_tip = Tip()
    overlay.show_taskbar = False
    overlay.diagnostic_profile = "portable"

    assert module.AhmadTkOverlay.export_diagnostic_package(overlay) == "break"

    export_path = overlay.last_diagnostic_export_path
    assert export_path is not None
    with zipfile.ZipFile(export_path) as archive:
        names = set(archive.namelist())
        assert "latest_snapshot.json" not in names
        assert module.UI_RUNTIME_STATUS in names
        assert "monitor.stderr.log" in names
        assert "monitor.lock" in names
        manifest = json.loads(archive.read("BUILD_EXPORT_MANIFEST.json").decode("utf-8"))
        assert manifest["session_id"] == "no_snapshot"
        assert manifest["version"]["source_file"] is None
        assert manifest["log_summary"]["latest_snapshot"]["exists"] is False
        assert manifest["log_summary"]["ui_runtime_status"]["exists"] is True
        assert manifest["log_summary"]["monitor_stderr"]["exists"] is True
    assert overlay.status.kwargs["text"] == "已导出诊断"


def test_ahmad_public_safe_diagnostic_export_omits_raw_and_ui_log(tmp_path: Path) -> None:
    module = _ahmad_overlay_module()
    snapshot_path = tmp_path / "latest_snapshot.json"
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    raw_jsonl = raw_dir / "windivert_live.jsonl"
    ui_log = tmp_path / module.SUMMARY_DIAGNOSTIC_LOG
    ui_health = tmp_path / module.UI_HEALTH_LOG
    ui_runtime = tmp_path / module.UI_RUNTIME_STATUS
    capture_status = tmp_path / "capture_source_status.json"
    raw_jsonl.write_text('{"SortID":1}\n', encoding="utf-8")
    ui_log.write_text('{"render_mode":"live"}\n', encoding="utf-8")
    ui_health.write_text('{"event":"ui_event_loop_stall_suspected"}\n', encoding="utf-8")
    ui_runtime.write_text('{"event":"waiting_for_snapshot"}', encoding="utf-8")
    capture_status.write_text('{"source":"windivert"}', encoding="utf-8")
    snapshot = {
        "schema_version": 1,
        "created_at": 123456.0,
        "session_id": "2401:test",
        "hero": "ahmed",
        "map_id": 2401,
        "round": 2,
        "phase": "bidding",
        "formal_mode": "v3_practical",
        "raw_capture": str(raw_jsonl),
        "raw_capture_jsonl": str(raw_jsonl),
    }
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    export_path = module._write_diagnostic_export(
        snapshot=snapshot,
        snapshot_path=snapshot_path,
        current_summary={"status": "ok", "context": {"session_id": "2401:test"}},
        diagnostic_profile="public-safe",
    )

    with zipfile.ZipFile(export_path) as archive:
        names = set(archive.namelist())
        assert "latest_snapshot.json" in names
        assert "capture_source_status.json" in names
        assert "hero_ref_current_summary.json" in names
        assert "BUILD_EXPORT_MANIFEST.json" in names
        assert module.UI_HEALTH_LOG in names
        assert module.UI_RUNTIME_STATUS in names
        assert module.SUMMARY_DIAGNOSTIC_LOG not in names
        assert "raw/windivert_live.jsonl" not in names
        manifest = json.loads(archive.read("BUILD_EXPORT_MANIFEST.json").decode("utf-8"))
        assert manifest["startup"]["launch_mode"] == "floating"
        assert manifest["startup"]["show_taskbar"] is False
        assert manifest["package"]["is_public_safe"] is True
        assert manifest["package"]["includes_raw_tables"] is False
        assert manifest["log_summary"]["raw_tables"]["present"] is False
        assert manifest["log_summary"]["diagnostic_profile"] == "public-safe"
        assert manifest["log_summary"]["ui_runtime_status"]["exists"] is True
        assert manifest["log_summary"]["continuous_ui_summary"] is False
        assert manifest["log_summary"]["export_includes_raw"] is False
        assert manifest["log_summary"]["export_includes_ui_summary"] is False


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


def test_ahmad_overlay_waiting_diagnostics_use_capture_status() -> None:
    overlay = _ahmad_overlay_module()
    status = {
        "ts": time.time(),
        "source": "windivert",
        "process_name": "BidKing.exe",
        "active_flows": 1,
        "sniffed_packets": 211,
        "raw_packets": 211,
        "accepted_frames": 0,
        "ignored_frames": 66,
        "ignored_reasons": {"rev_not_game_frame": 63},
        "active_session_id": "",
    }

    diagnostics = overlay._capture_wait_diagnostics(status)

    assert diagnostics["subtitle"] == "已抓到流量，但未解析到对局状态帧"
    assert diagnostics["action"] == "等待状态帧"
    assert diagnostics["recent"] == "rev_not_game_frame x63"
    assert "备用启动" in diagnostics["note"]

    status["accepted_frames"] = 3
    status["active_session_id"] = "2405:1402770697021587"
    diagnostics = overlay._capture_wait_diagnostics(status)

    assert diagnostics["subtitle"] == "已识别会话，等待估价状态帧"
    assert diagnostics["state"] == "session_waiting_snapshot"
    assert diagnostics["session"] == "2405:1402770697021587"


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


def test_ahmad_tk_minimap_unknown_footprint_uses_stripes_without_permanent_text() -> None:
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
                    "row": 4,
                    "col": 5,
                    "width": 2,
                    "height": 1,
                    "quality": None,
                    "category_label": "古董",
                    "shape_key": "21",
                    "render_mode": "footprint",
                    "tooltip": "技能 10002071 / 品质? / 21 / 古董",
                }
            ],
        },
        None,
    )

    item_calls = [entry for entry in calls if entry[2].get("tags") == ("item_0",)]
    assert any(kind == "rectangle" for kind, *_ in item_calls)
    assert any(kind == "line" for kind, *_ in item_calls)
    assert not any(kind == "text" for kind, *_ in calls)


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
    assert module.AhmadTkOverlay._latest_result_text(  # type: ignore[attr-defined]
        SimpleNamespace(),
        {"latest_result": {"tool": "普品均格", "result": "1.7999999523162842"}},
    ) == "普品均格=1.8"


def test_ahmad_overlay_mini_input_text_keeps_compact_totals() -> None:
    module = _ahmad_overlay_module()

    assert module.AhmadTkOverlay._mini_input_text(  # type: ignore[attr-defined]
        SimpleNamespace(),
        {
            "ref_input_summary": (
                "总件 38 · 总格 83.0 · 件数 白绿件 15，蓝件 9，紫件 8，金件 4，红件 2 "
                "· 格数 白绿格 27，蓝格 14，紫格 33，金格 7，红格 2"
            ),
            "ref_status": "ok",
        },
    ) == "总件 38 · 总格 83.0"
    assert module.AhmadTkOverlay._mini_input_text(  # type: ignore[attr-defined]
        SimpleNamespace(),
        {"ref_input_summary": "-", "ref_status": "missing_total_count"},
    ) == "missing_total_count"


def test_ahmad_overlay_mini_candidate_and_next_info_use_actionable_fields() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    data = {
        "evidence": {
            "candidate_summary": "总件 38 · 总格 83",
            "next_info_hint": "优先补白绿/蓝件数或均格",
            "ref_input_summary": "总件 38 · 总格 83 · 件数 白绿件 15",
        },
        "ahmed_ref": {},
    }

    assert module.AhmadTkOverlay._mini_candidate_text(overlay, data) == "总件 38 · 总格 83"
    assert module.AhmadTkOverlay._mini_next_info_text(overlay, data) == "优先补白绿/蓝件数或均格"


def test_ahmad_server_candidate_summary_and_next_info_hint() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "ok",
        "total_grid_range": [70, 82, 94],
        "quality_count_ranges": {
            "q1": [10, 15, 15],
            "q3": [8, 11, 13],
            "q4": [4, 4, 4],
            "q5": [2, 2, 2],
            "q6": [1, 1, 1],
        },
        "evidence": {"total_count": 38},
    }

    assert module._candidate_summary(result) == "总件 38 · 估总格 70/82/94格"  # type: ignore[attr-defined]
    assert module._next_info_hint(result) == "优先补白绿/蓝件数或均格"  # type: ignore[attr-defined]

    result["evidence"]["total_grid_target"] = 120.00000476837158
    assert module._candidate_summary(result) == "总件 38 · 总格 120"  # type: ignore[attr-defined]
    assert module._next_info_hint(result) == "优先补白绿/蓝件数或均格"  # type: ignore[attr-defined]


def test_ahmad_server_ref_waiting_text_is_hero_specific() -> None:
    module = _ahmad_server_module()
    ahmed_grid_only = {
        "status": "missing_total_count",
        "notes": ["waiting_total_count", "waiting_total_count:grid_only"],
        "evidence": {"total_grid_target": 152, "total_count": None},
    }
    ethan_grid_only = dict(ahmed_grid_only)
    assert module._ref_waiting_display_text("ahmed", ahmed_grid_only) == "等待总件数"  # type: ignore[attr-defined]
    assert module._ref_waiting_display_text("ethan", ethan_grid_only) == "等待公开输入"  # type: ignore[attr-defined]
    assert module._ref_waiting_flag_label("ethan", ethan_grid_only) == "等待公开输入"  # type: ignore[attr-defined]
    assert module._next_info_hint(ahmed_grid_only, hero_key="ahmed") == "先补总件"  # type: ignore[attr-defined]
    assert module._next_info_hint(ethan_grid_only, hero_key="ethan") == "先补公开总件"  # type: ignore[attr-defined]


def test_ahmad_server_aisha_d1_flag_detail_filters_weak_shadow_discounts() -> None:
    module = _ahmad_server_module()

    # Near-1.0 shadow discount is noise — do not surface a flag.
    assert module._aisha_d1_flag_detail(["aisha_d1_shadow_q6_discount=0.9@r5"]) == ""  # type: ignore[attr-defined]
    # Meaningful shadow discount surfaces.
    assert (
        module._aisha_d1_flag_detail(["aisha_d1_shadow_q6_discount=0.55@r2"])  # type: ignore[attr-defined]
        == "aisha_d1_shadow_q6_discount=0.55@r2"
    )
    # apply notes always surface (they change the bid).
    assert (
        module._aisha_d1_flag_detail(["aisha_d1_apply_q6_discount=0.85@r4"])  # type: ignore[attr-defined]
        == "aisha_d1_apply_q6_discount=0.85@r4"
    )
    # Non-d1 notes ignored.
    assert module._aisha_d1_flag_detail(["aisha_layout_band_widen_applied"]) == ""  # type: ignore[attr-defined]


def test_ahmad_server_aisha_defense_multiplier_hint_by_round() -> None:
    module = _ahmad_server_module()

    assert module._aisha_defense_multiplier_hint(1) == "R1防守×2.0"  # type: ignore[attr-defined]
    assert module._aisha_defense_multiplier_hint(2) == "R2防守×1.6"  # type: ignore[attr-defined]
    assert module._aisha_defense_multiplier_hint(3) == "R3防守×1.3"  # type: ignore[attr-defined]
    assert module._aisha_defense_multiplier_hint(4) == "R4防守×1.1"  # type: ignore[attr-defined]
    assert module._aisha_defense_multiplier_hint(5) == "R5防守×1.1"  # type: ignore[attr-defined]
    assert module._aisha_defense_multiplier_hint(None) == ""  # type: ignore[attr-defined]


def test_ahmad_server_aisha_next_info_hint_r1_prefers_blue_tools_not_white_green() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "ok",
        "quality_count_ranges": {
            "q1": [8, 12, 16],
            "q3": [6, 10, 14],
            "q4": [4, 6, 8],
            "q5": [2, 3, 4],
            "q6": [0, 1, 1],
        },
        "evidence": {"total_count": 32},
    }

    hint = module._next_info_hint(result, hero_key="aisha", round_no=1)  # type: ignore[attr-defined]

    assert hint == "R1先开良品扫描或良品存量"
    assert "白绿" not in hint
    assert "总件" not in hint


def test_ahmad_server_aisha_missing_total_count_r1_prefers_blue_before_total() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "missing_total_count",
        "notes": ["waiting_total_count"],
        "quality_count_ranges": {
            "q1": [6, 12, 18],
            "q3": [4, 10, 16],
        },
        "evidence": {"total_count": None, "total_grid_target": 140},
    }

    hint = module._next_info_hint(result, hero_key="aisha", round_no=1)  # type: ignore[attr-defined]

    assert hint == "R1先开良品扫描或良品存量"
    assert module._ref_waiting_display_text("aisha", result, round_no=1) == hint  # type: ignore[attr-defined]


def test_ahmad_server_aisha_next_info_hint_puts_total_count_last() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "ok",
        "total_grid_range": [120, 120, 120],
        "quality_count_ranges": {
            "q1": [10, 10, 10],
            "q3": [9, 9, 9],
            "q4": [6, 6, 6],
            "q5": [3, 3, 3],
            "q6": [0, 1, 1],
        },
        "evidence": {
            "total_count": None,
            "total_grid_target": 120,
            "fixed_counts": {"q3": 9, "q4": 6, "q5": 3},
            "quality_cells": {"q3": 14, "q4": 18},
            "avg_cells": {"q5": 2.5},
        },
    }

    hint = module._next_info_hint(result, hero_key="aisha")  # type: ignore[attr-defined]

    assert hint == "最后补总件"


def test_ahmad_server_aisha_next_info_hint_gold_value_alone_still_suggests_scan() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "ok",
        "total_grid_range": [120, 120, 120],
        "quality_count_ranges": {
            "q1": [10, 10, 10],
            "q3": [9, 9, 9],
            "q4": [6, 6, 6],
            "q5": [3, 3, 3],
            "q6": [0, 1, 1],
        },
        "evidence": {
            "total_count": 33,
            "fixed_counts": {"q3": 9, "q4": 6, "q5": 3},
            "quality_cells": {"q3": 14, "q4": 18},
            "avg_values": {"q5": 26730},
        },
    }

    hint = module._next_info_hint(result, hero_key="aisha")  # type: ignore[attr-defined]

    assert hint == "开极品均格或极品扫描"
    assert "估价" not in hint


def test_ahmad_server_aisha_next_info_hint_moves_to_purple_after_blue_locked() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "ok",
        "quality_count_ranges": {
            "q1": [8, 12, 16],
            "q3": [9, 9, 9],
            "q4": [4, 8, 12],
            "q5": [2, 3, 4],
            "q6": [0, 1, 1],
        },
        "evidence": {
            "total_count": 32,
            "fixed_counts": {"q3": 9},
            "quality_cells": {"q3": 14},
        },
    }

    hint = module._next_info_hint(result, hero_key="aisha", round_no=3)  # type: ignore[attr-defined]

    assert hint == "开优品均格/优品存量/优品扫描"


def test_ahmad_server_aisha_next_info_hint_moves_to_gold_then_warehouse() -> None:
    module = _ahmad_server_module()
    purple_done = {
        "status": "ok",
        "total_grid_range": [90, 110, 130],
        "quality_count_ranges": {
            "q1": [10, 10, 10],
            "q3": [9, 9, 9],
            "q4": [6, 6, 6],
            "q5": [2, 4, 6],
            "q6": [0, 1, 1],
        },
        "evidence": {
            "total_count": 33,
            "fixed_counts": {"q3": 9, "q4": 6},
            "quality_cells": {"q3": 14, "q4": 18},
        },
    }
    gold_done = {
        **purple_done,
        "quality_count_ranges": {
            **purple_done["quality_count_ranges"],
            "q5": [3, 3, 3],
        },
        "evidence": {
            **purple_done["evidence"],
            "fixed_counts": {**purple_done["evidence"]["fixed_counts"], "q5": 3},
            "avg_cells": {"q5": 2.5},
        },
    }

    assert (
        module._next_info_hint(purple_done, hero_key="aisha")  # type: ignore[attr-defined]
        == "开极品均格或极品扫描"
    )
    assert (
        module._next_info_hint(gold_done, hero_key="aisha")  # type: ignore[attr-defined]
        == "开总仓储看总格，必要时全库透视"
    )


def test_ahmad_server_next_info_hint_prefers_gold_before_total_grid() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "ok",
        "total_grid_range": [80, 96, 112],
        "quality_count_ranges": {
            "q1": [14, 14, 14],
            "q3": [9, 9, 9],
            "q4": [6, 6, 6],
            "q5": [3, 3, 6],
            "q6": [1, 1, 1],
        },
        "evidence": {
            "total_count": 33,
        },
    }

    hint = module._next_info_hint(result)  # type: ignore[attr-defined]

    assert hint == "补金件数或均格"
    assert "总格" not in hint
    assert "红" not in hint


def test_ahmad_server_next_info_hint_targets_q6_grid_when_red_count_locked() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "ok",
        "total_grid_range": [113, 113, 113],
        "quality_count_ranges": {
            "q1": [9, 9, 9],
            "q3": [15, 15, 15],
            "q4": [8, 8, 8],
            "q5": [6, 6, 6],
            "q6": [1, 1, 1],
        },
        "evidence": {
            "total_count": 39,
            "avg_cells": {"q1": 20 / 9, "q3": 40 / 15, "q4": 2.5, "q5": 5.0},
            "quality_cells": {"q4": 20, "q5": 30},
        },
    }

    assert module._next_info_hint(result) == "优先补总格/全均格"  # type: ignore[attr-defined]


def test_ahmad_server_next_info_hint_never_recommends_red_or_known_gold_value() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "ok",
        "total_grid_range": [100, 100, 100],
        "quality_count_ranges": {
            "q1": [12, 12, 12],
            "q3": [10, 10, 10],
            "q4": [8, 8, 8],
            "q5": [1, 2, 3],
            "q6": [0, 1, 2],
        },
        "evidence": {
            "total_count": 35,
            "total_grid_target": 100,
            "avg_values": {"q5": 26730},
        },
    }

    hint = module._next_info_hint(result)  # type: ignore[attr-defined]

    assert hint == "补金件数或均格"
    assert "红" not in hint
    assert "均价" not in hint


def test_ahmad_server_next_info_hint_does_not_use_red_as_only_remaining_input() -> None:
    module = _ahmad_server_module()
    result = {
        "status": "ok",
        "total_grid_range": [100, 100, 100],
        "quality_count_ranges": {
            "q1": [12, 12, 12],
            "q3": [10, 10, 10],
            "q4": [8, 8, 8],
            "q5": [3, 3, 3],
            "q6": [0, 1, 2],
        },
        "evidence": {
            "total_count": 35,
            "total_grid_target": 100,
        },
    }

    hint = module._next_info_hint(result)  # type: ignore[attr-defined]

    assert hint == "信息已足够，观察出价"
    assert "红" not in hint


def test_ahmad_settlement_hide_masks_values_but_keeps_counts() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.settlement_values_hidden = True
    data = {
        "context": {"phase": "settled"},
        "truth": {
            "available": True,
            "total_value": 520000,
            "total_items": 21,
            "total_cells": 34,
            "q6": {"count": 1, "cells": 3, "value": 160000},
        },
    }

    assert module.AhmadTkOverlay._settlement_values_are_hidden(overlay, data) is True
    assert module.AhmadTkOverlay._settlement_display_value(overlay, data, "520,000") == "已隐藏"
    truth_text = module.AhmadTkOverlay._truth_text(overlay, data)
    assert "价值隐藏" in truth_text
    assert "21件/34格" in truth_text
    assert "红1件/3格" in truth_text
    assert "520000" not in truth_text


def test_ahmad_settlement_hide_toggle_can_be_preset_before_settlement() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    settled = {"context": {"phase": "settled"}, "truth": {"available": True}}
    not_settled = {"context": {"phase": "bidding"}, "truth": {"available": False}}
    rendered: list[dict] = []
    overlay.settlement_values_hidden = False
    overlay._last_summary = not_settled
    overlay._last_live_summary = {}
    overlay._set_settlement_button_state = lambda data: None  # type: ignore[method-assign]
    overlay.render = lambda data: rendered.append(data)  # type: ignore[method-assign]

    assert module.AhmadTkOverlay.toggle_settlement_values(overlay) == "break"
    assert overlay.settlement_values_hidden is True
    assert rendered == []

    overlay._last_summary = settled
    rendered.clear()
    assert module.AhmadTkOverlay.toggle_settlement_values(overlay) == "break"
    assert overlay.settlement_values_hidden is False
    assert rendered == [settled]


def test_ahmad_hover_copy_keeps_settlement_and_github_clear() -> None:
    module = _ahmad_overlay_module()

    assert "http" not in module.GITHUB_TIP_TEXT.lower()
    assert "Star" in module.GITHUB_TIP_TEXT
    assert "只影响界面，不影响计算" in module.SETTLEMENT_HIDE_TIP
    assert "只影响界面，不影响计算" in module.SETTLEMENT_SHOW_TIP
    assert "不删除 live 日志" in module.MANUAL_CLEAR_SETTLEMENT_TIP

    class Button:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Tip:
        def __init__(self) -> None:
            self.text = ""

        def set_text(self, text: str) -> None:
            self.text = text

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.settlement_button = Button()
    overlay.settlement_tip = Tip()
    overlay.settlement_values_hidden = False
    settled = {"context": {"phase": "settled"}, "truth": {"available": True}}
    module.AhmadTkOverlay._set_settlement_button_state(overlay, settled)

    assert overlay.settlement_button.kwargs["text"] == "藏价"
    assert overlay.settlement_tip.text == module.SETTLEMENT_HIDE_TIP

    overlay.settlement_values_hidden = True
    module.AhmadTkOverlay._set_settlement_button_state(overlay, settled)
    assert overlay.settlement_button.kwargs["text"] == "显价"
    assert overlay.settlement_tip.text == module.SETTLEMENT_SHOW_TIP

    module.AhmadTkOverlay._set_settlement_button_state(overlay, {"context": {"phase": "bidding"}})
    assert overlay.settlement_button.kwargs["text"] == "显价"
    assert overlay.settlement_tip.text == module.SETTLEMENT_SHOW_TIP

    overlay.settlement_values_hidden = False
    module.AhmadTkOverlay._set_settlement_button_state(overlay, {"context": {"phase": "bidding"}})
    assert overlay.settlement_button.kwargs["text"] == "藏价"
    assert overlay.settlement_tip.text == module.SETTLEMENT_HIDE_TIP


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
                "total_grid_target": 34.00000476837158,
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
    assert values["total_cells"] == "34"
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


def test_ahmad_manual_values_from_live_summary_prefills_quality_value_fields() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    data = {
        "context": {"hero": "ahmed", "map_id": 2401},
        "ahmed_ref": {
            "quality_count_ranges": {
                "q4": [8, 8, 8],
                "q5": [4, 4, 4],
            },
            "evidence": {
                "hero": "ahmed",
                "map_id": 2401,
                "total_count": 30,
                "avg_values": {"q4": 6328.75, "q5": 34288.75},
                "quality_values": {"q4": 50630, "q5": 137155},
            }
        },
    }

    values = module.AhmadTkOverlay._manual_values_from_summary(overlay, data)

    assert values["q4_avg_value"] == "6328.75"
    assert values["q4_value_sum"] == "50630"
    assert values["q4_count"] == 8
    assert values["q5_avg_value"] == "34288.75"
    assert values["q5_value_sum"] == "137155"
    assert values["q5_count"] == 4


def test_ahmad_manual_values_do_not_promote_estimated_total_grid_to_input() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    data = {
        "context": {"hero": "ahmed", "map_id": 2405},
        "ahmed_ref": {
            "total_grid_range": [70, 82, 94],
            "evidence": {
                "hero": "ahmed",
                "map_id": 2405,
                "total_count": 33,
            },
        },
    }

    values = module.AhmadTkOverlay._manual_values_from_summary(overlay, data)

    assert values["hero"] == "ahmed"
    assert values["map_id"] == 2405
    assert values["total_count"] == 33
    assert "total_cells" not in values
    assert "total_avg" not in values


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


def test_ahmad_server_summary_locks_zero_gold_avg_in_mini(tmp_path: Path) -> None:
    module = _ahmad_server_module()
    snapshot = {
        "created_at": time.time(),
        "ui_contract": {
            "context": {
                "hero": "victor",
                "map_id": 2404,
                "phase": "bidding",
                "session_id": "2404:zero-gold",
            },
            "baseline": {"decision": {}, "posterior": {}},
            "source": {"created_at": time.time()},
        },
        "structured_ref_inputs": {
            "hero": "victor",
            "total_count": 21,
            "total_cells": 34,
            "avg_cells": {"q4": 1.8, "q5": 0.0},
            "count_sums": {"q4q5q6": 6},
        },
    }

    result = module.summarize_snapshot(snapshot, snapshot_path=tmp_path / "latest_snapshot.json")

    assert result["status"] == "ok"
    ref = result["ahmed_ref"]
    assert ref["evidence"]["fixed_counts"]["q5"] == 0
    assert ref["quality_count_ranges"]["q5"] == [0, 0, 0]
    assert ref["quality_cells_ranges"]["q5"] == [0, 0, 0]
    assert result["red"]["quality_count_summary"] == "紫件 5 · 金件 0"
    assert "金件 0" in result["red"]["quality_count_summary"]


def test_ahmad_server_summary_pairs_red_candidates_with_gold_candidates(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _ahmad_server_module()

    class FakeRefResult:
        def as_dict(self) -> dict[str, object]:
            return {
                "status": "ok",
                "source": "ref_v0",
                "notes": [],
                "conservative": 100000,
                "balanced": 120000,
                "aggressive": 140000,
                "red_count_range": [2, 3, 4],
                "red_cells_range": [4, 6, 8],
                "red_value_range": [30000, 40000, 50000],
                "total_grid_range": [30, 30, 30],
                "quality_count_ranges": {
                    "q1": [7, 7, 7],
                    "q3": [4, 4, 4],
                    "q4": [5, 5, 5],
                    "q5": [2, 3, 4],
                    "q6": [2, 3, 4],
                },
                "quality_cells_ranges": {
                    "q1": [5, 5, 5],
                    "q3": [6, 6, 6],
                    "q4": [7, 7, 7],
                    "q5": [4, 6, 8],
                    "q6": [4, 6, 8],
                },
                "evidence": {
                    "hero": "victor",
                    "total_count": 20,
                    "count_sums": {"q4q5q6": 11},
                    "total_grid_target": 30,
                },
            }

    monkeypatch.setattr(module, "run_reference_engine", lambda snapshot: FakeRefResult())
    snapshot = {
        "created_at": time.time(),
        "ui_contract": {
            "context": {
                "hero": "victor",
                "map_id": 2404,
                "phase": "bidding",
                "session_id": "2404:red-pair",
            },
            "baseline": {"decision": {}, "posterior": {}},
            "source": {"created_at": time.time()},
        },
        "structured_ref_inputs": {"hero": "victor", "total_count": 20},
    }

    result = module.summarize_snapshot(snapshot, snapshot_path=tmp_path / "latest_snapshot.json")

    assert result["red"]["quality_count_summary"] == "紫件 5 · 金件 2 / 3 / 4"
    assert result["red"]["count_range"] == "4 / 3 / 2"
    assert result["red"]["cells_range"] == "8 / 6 / 4"


def test_ahmad_server_red_display_keeps_count_and_cells_physically_paired() -> None:
    module = _ahmad_server_module()
    result = {
        "red_count_range": [0, 1, 3],
        "red_cells_range": [0, 4, 9],
        "quality_count_ranges": {
            "q1": [10, 10, 10],
            "q3": [9, 9, 9],
            "q4": [12, 12, 12],
            "q5": [1, 3, 4],
            "q6": [0, 1, 3],
        },
        "evidence": {
            "total_count": 35,
            "count_sums": {"q4q5q6": 16},
        },
    }

    red_count_range, red_cells_range = module._red_display_ranges(result)  # type: ignore[attr-defined]

    assert red_count_range == [3, 1, 0]
    assert red_cells_range == [9, 4, 0]


def test_ahmad_server_summary_keeps_locked_red_triplet_with_minimap_floor(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _ahmad_server_module()

    class FakeRefResult:
        def as_dict(self) -> dict[str, object]:
            return {
                "status": "ok",
                "source": "ref_v0",
                "notes": [],
                "conservative": 648829,
                "balanced": 703823,
                "aggressive": 758817,
                "red_count_range": [3, 3, 3],
                "red_cells_range": [9, 10, 11],
                "red_value_range": [368557, 485120, 595000],
                "quality_count_ranges": {
                    "q4": [12, 12, 12],
                    "q5": [5, 5, 5],
                    "q6": [3, 3, 3],
                },
                "evidence": {
                    "hero": "victor",
                    "total_count": 47,
                    "count_sums": {"q4q5q6": 20},
                },
            }

    monkeypatch.setattr(module, "run_reference_engine", lambda snapshot: FakeRefResult())
    snapshot = {
        "created_at": time.time(),
        "ui_contract": {
            "context": {
                "hero": "victor",
                "map_id": 2404,
                "phase": "bidding",
                "session_id": "2404:locked-red-floor",
            },
            "baseline": {"decision": {}, "posterior": {}},
            "constraints": {"summary": {}, "counts": {}, "public_info": {}},
            "minimap": {
                "status": "available",
                "columns": 10,
                "items": [
                    {
                        "row": 0,
                        "col": 0,
                        "quality": 6,
                        "render_mode": "footprint",
                        "width": 3,
                        "height": 3,
                        "cells": 9,
                    },
                    {
                        "row": 0,
                        "col": 4,
                        "quality": 6,
                        "render_mode": "footprint",
                        "width": 1,
                        "height": 1,
                        "cells": 1,
                    },
                    {
                        "row": 1,
                        "col": 4,
                        "quality": 6,
                        "render_mode": "footprint",
                        "width": 1,
                        "height": 1,
                        "cells": 1,
                    },
                ],
            },
        },
        "structured_ref_inputs": {"hero": "victor", "total_count": 47},
    }

    result = module.summarize_snapshot(snapshot, snapshot_path=tmp_path / "latest_snapshot.json")

    assert result["red"]["count_range"] == "3 / 3 / 3"
    assert result["red"]["cells_range"] == "11 / 11 / 11"


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
    assert result["minimap"]["items"][0]["label"] == "红品≥1"
    assert "红品≥1" in result["minimap"]["items"][0]["tooltip"]
    assert "轮廓 2x2/4格" in result["minimap"]["items"][0]["tooltip"]
    assert "公共抽检" in result["minimap"]["items"][0]["tooltip"]
    assert "item" not in result["minimap"]["items"][0]["tooltip"].lower()


def test_ahmad_server_summary_keeps_public_info_item_name(tmp_path: Path) -> None:
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
                        "item_id": 1001,
                        "item_name": "民用垂直起降飞行器",
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
    item = result["minimap"]["items"][0]

    assert item["label"] == "民用垂直起降飞行器"
    assert "民用垂直起降飞行器" in item["tooltip"]
    assert "红品" in item["tooltip"]
    assert "红品≥1" not in item["tooltip"]


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


def test_ahmad_server_summary_settlement_truth_overrides_stale_live_actions(tmp_path: Path) -> None:
    module = _ahmad_server_module()
    snapshot_path = tmp_path / "latest_snapshot.json"
    snapshot = {
        "created_at": time.time(),
        "phase": "settled",
        "final_quality_counts": "q2=3;q3=2;q4=4;q5=2;q6=3",
        "final_quality_cells": "q2=6;q3=10;q4=12;q5=8;q6=7",
        "structured_ref_inputs": {
            "hero": "ahmed",
            "total_count": 21,
            "fixed_counts": {"q1": 3, "q3": 9, "q5": 2},
            "quality_cells": {"q1": 25},
            "avg_cells": {"q1": 1.6666666269302368},
        },
        "ui_contract": {
            "context": {
                "hero": "ahmed",
                "map_id": 4521,
                "phase": "settled",
                "session_id": "4521:settled",
            },
            "baseline": {
                "decision": {"attack_bid": "450000"},
                "posterior": {},
            },
            "actions": {
                "results": [
                    {"action_id": 100117, "result": 9},
                    {"action_id": 100104, "result": 25},
                    {"action_id": 100110, "result": 1.6666666269302368},
                ]
            },
            "truth": {
                "available": True,
                "total_value": 867739,
                "total_items": 14,
                "total_cells": 43,
                "q6": {"count": 3, "cells": 7, "value": 420000},
                "top_item": {"name": "test", "value": 250000},
            },
        },
    }

    result = module.summarize_snapshot(snapshot, snapshot_path=snapshot_path)
    ref_evidence = result["ahmed_ref"]["evidence"]

    assert result["status"] == "ok"
    assert result["reference"]["source"] == "settlement"
    assert result["reference"]["balanced"] == "867,739"
    assert result["truth"]["total_items"] == 14
    assert result["truth"]["total_cells"] == 43
    assert result["ahmed_ref"]["status"] == "ok"
    assert result["ahmed_ref"]["combo_count"] == 1
    assert ref_evidence["total_count"] == 14
    assert ref_evidence["total_grid_target"] == 43.0
    assert ref_evidence["fixed_counts"] == {"q1": 3, "q3": 2, "q4": 4, "q5": 2, "q6": 3}
    assert ref_evidence["quality_cells"] == {"q1": 6.0, "q3": 10.0, "q4": 12.0, "q5": 8.0, "q6": 7.0}


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


def test_ahmad_ref_input_summary_shows_estimated_total_grid_without_hard_target() -> None:
    module = _ahmad_server_module()
    summary = module._ref_input_summary(  # type: ignore[attr-defined]
        {
            "total_grid_range": [70, 82, 94],
            "evidence": {
                "total_count": 33,
            },
        }
    )

    assert "总件 33" in summary
    assert "估总格 70 / 82 / 94格" in summary
    assert "总格 82" not in summary


def test_ahmad_ref_input_summary_uses_compact_exact_avg_display() -> None:
    module = _ahmad_server_module()
    summary = module._ref_input_summary(  # type: ignore[attr-defined]
        {
            "evidence": {
                "total_count": 55,
                "avg_cells": {
                    "q1": 1.8095238208770752,
                    "q4": 2.9000000953674316,
                },
            }
        }
    )

    assert "白绿均格 1.8095" in summary
    assert "紫均格 2.9" in summary
    assert "白绿均格 1.81" not in summary
    assert "紫均格 2.90" not in summary


def test_ahmad_ref_input_summary_prioritizes_counts_and_cells_before_avg() -> None:
    module = _ahmad_server_module()
    summary = module._ref_input_summary(  # type: ignore[attr-defined]
        {
            "evidence": {
                "total_count": 38,
                "total_grid_target": 83.00000476837158,
                "avg_cells": {"q1": 1.8, "q3": 1.5556, "q4": 4.125},
                "quality_cells": {"q1": 27, "q3": 14, "q4": 33},
                "fixed_counts": {"q1": 15, "q3": 9, "q4": 8},
            }
        }
    )

    assert summary.startswith("总件 38 · 总格 83 · 件数 白绿件 15")
    assert summary.find("格数 白绿格 27") < summary.find("白绿均格 1.8")
    assert summary.find("紫均格 4.125") > summary.find("格数 白绿格 27")


def test_ahmad_manual_input_summary_prioritizes_counts_and_cells_before_avg() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)
    summary = module.AhmadTkOverlay._manual_input_summary(
        overlay,
        {
            "total_count": 38,
            "total_grid_target": 83.00000476837158,
            "avg_cells": {"q1": 1.8, "q3": 1.5556, "q4": 4.125},
            "quality_cells": {"q1": 27, "q3": 14, "q4": 33},
            "fixed_counts": {"q1": 15, "q3": 9, "q4": 8},
        },
    )

    assert summary.startswith("总件 38 · 总格 83 · 件数 白绿件 15")
    assert summary.find("格数 白绿格 27") < summary.find("白绿均格 1.8")
    assert summary.find("紫均格 4.125") > summary.find("格数 白绿格 27")


def test_ahmad_tk_summary_label_splits_long_input_summary() -> None:
    module = _ahmad_overlay_module()

    class Label:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    label = Label()
    overlay = object.__new__(module.AhmadTkOverlay)

    module.AhmadTkOverlay._set_summary_label(
        overlay,
        label,
        (
            "总件 38 · 总格 83.0 · 全均格 2.1842 · 白绿均格 1.8 · "
            "蓝均格 1.5556 · 紫均格 4.125 · 金均格 1.75 · 红均格 1 · "
            "格数 白绿格 27.0，蓝格 14.0，紫格 33.0，金格 7.0，红格 2.0"
        ),
        line_limit=42,
    )

    assert "\n" in label.kwargs["text"]
    assert label.kwargs["height"] == 2
    assert label.kwargs["justify"] == "right"
    assert "总件 38" in label.kwargs["text"]
    assert "白绿均格 1.8" in label.kwargs["text"]


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

    assert "白均格 1.6667" in summary
    assert "绿均格 2" in summary
    assert "分格 白格 5，绿格 8" in summary
    assert "分件 白件 3，绿件 4" in summary
    assert "件数 白绿件 7" in summary


def test_ahmad_quality_uncertainty_summary_prioritizes_unlocked_counts() -> None:
    module = _ahmad_server_module()
    summary = module._quality_uncertainty_summary(  # type: ignore[attr-defined]
        {
            "quality_count_ranges": {
                "q1": [10, 15, 15],
                "q3": [13, 13, 13],
                "q4": [9, 9, 9],
                "q5": [4, 4, 8],
                "q6": [0, 3, 5],
            }
        }
    )

    assert summary == "未锁 白绿10/15/15"
    assert "蓝13" not in summary
    assert "金4" not in summary
    assert "红0" not in summary


def test_ahmad_quality_uncertainty_summary_applies_lower_bounds() -> None:
    module = _ahmad_server_module()
    summary = module._quality_uncertainty_summary(  # type: ignore[attr-defined]
        {
            "quality_count_ranges": {
                "q1": [0, 2, 2],
                "q3": [0, 1, 4],
            },
            "evidence": {"min_counts": {"q1": 1, "q3": 2}},
        },
        count_floors={"q3": 3},
    )

    assert "白绿1/2/2" in summary
    assert "蓝3/3/4" in summary


def test_ahmad_quality_uncertainty_summary_shows_locked_counts() -> None:
    module = _ahmad_server_module()
    summary = module._quality_uncertainty_summary(  # type: ignore[attr-defined]
        {
            "quality_count_ranges": {
                "q1": [10, 10, 10],
                "q3": [13, 13, 13],
                "q4": [9, 9, 9],
                "q5": [4, 4, 4],
                "q6": [3, 3, 3],
            }
        }
    )

    assert summary.startswith("已锁 ")
    assert "白绿10" in summary
    assert "蓝13" in summary
    assert "紫9" not in summary
    assert "金4" not in summary


def test_ahmad_quality_uncertainty_summary_shows_locked_count_and_cells() -> None:
    module = _ahmad_server_module()
    summary = module._quality_uncertainty_summary(  # type: ignore[attr-defined]
        {
            "quality_count_ranges": {
                "q1": [10, 10, 10],
                "q3": [13, 13, 13],
            },
            "quality_cells_ranges": {
                "q1": [27, 27, 27],
                "q3": [18, 18, 18],
            },
        }
    )

    assert summary == "已锁 白绿10/27 蓝13/18"


def test_ahmad_quality_uncertainty_summary_uses_evidence_cells_when_range_open() -> None:
    module = _ahmad_server_module()
    summary = module._quality_uncertainty_summary(  # type: ignore[attr-defined]
        {
            "quality_count_ranges": {
                "q1": [10, 10, 10],
                "q3": [13, 13, 13],
            },
            "quality_cells_ranges": {
                "q1": [20, 30, 30],
            },
            "evidence": {
                "quality_cells": {"q1": 27, "q3": 18},
            },
        }
    )

    assert "白绿10/27" in summary
    assert "蓝13/18" in summary


def test_ahmad_manual_field_layout_preserves_input_contract() -> None:
    module = _ahmad_overlay_module()
    base_keys = [key for key, _label, _default in module.MANUAL_BASE_FIELDS]  # type: ignore[attr-defined]
    quality_keys = [
        key
        for _label, avg_key, count_key, cells_key in module.MANUAL_QUALITY_ROWS  # type: ignore[attr-defined]
        for key in (avg_key, count_key, cells_key)
    ]
    value_keys = [
        key
        for _label, avg_value_key, value_sum_key in module.MANUAL_VALUE_ROWS  # type: ignore[attr-defined]
        for key in (avg_value_key, value_sum_key)
    ]
    extra_keys = [key for key, _label, _default in module.MANUAL_EXTRA_FIELDS]  # type: ignore[attr-defined]
    keys = [*base_keys, *quality_keys, *value_keys, *extra_keys]

    assert [label for label, *_keys in module.MANUAL_QUALITY_ROWS] == [  # type: ignore[attr-defined]
        "白",
        "绿",
        "白绿",
        "蓝",
        "紫",
        "金",
        "红",
    ]
    assert [label for label, *_keys in module.MANUAL_VALUE_ROWS] == [  # type: ignore[attr-defined]
        "白",
        "绿",
        "白绿",
        "蓝",
        "紫",
        "金",
        "红",
    ]
    assert keys == [
        "hero",
        "map_id",
        "total_count",
        "total_cells",
        "total_avg",
        "white_avg",
        "white_count",
        "white_cells",
        "green_avg",
        "green_count",
        "green_cells",
        "q1_avg",
        "q1_count",
        "q1_cells",
        "q3_avg",
        "q3_count",
        "q3_cells",
        "q4_avg",
        "q4_count",
        "q4_cells",
        "q5_avg",
        "q5_count",
        "q5_cells",
        "q6_avg",
        "q6_count",
        "q6_cells",
        "white_avg_value",
        "white_value_sum",
        "green_avg_value",
        "green_value_sum",
        "q1_avg_value",
        "q1_value_sum",
        "q3_avg_value",
        "q3_value_sum",
        "q4_avg_value",
        "q4_value_sum",
        "q5_avg_value",
        "q5_value_sum",
        "q6_avg_value",
        "q6_value_sum",
        "q4q5_count",
    ]
    assert len(keys) == len(set(keys))


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


def test_ahmad_manual_inline_derivation_covers_quality_values() -> None:
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
        "white_avg_value": Entry(""),
        "white_value_sum": Entry("300"),
        "green_count": Entry("4"),
        "green_avg_value": Entry("200"),
        "green_value_sum": Entry(""),
        "q5_count": Entry("4"),
        "q5_avg_value": Entry(""),
        "q5_value_sum": Entry("137155"),
        "q4_count": Entry("8"),
        "q4_avg_value": Entry("6328.75"),
        "q4_value_sum": Entry(""),
    }

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay)

    assert overlay.manual_entries["white_avg_value"].get() == "100"
    assert overlay.manual_entries["green_value_sum"].get() == "800"
    assert overlay.manual_entries["q5_avg_value"].get() == "34288.75"
    assert overlay.manual_entries["q4_value_sum"].get() == "50630"


def test_ahmad_manual_inline_derivation_refreshes_total_avg_after_total_cells_change() -> None:
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
    overlay._manual_dirty_fields = {"total_cells"}
    overlay._manual_autofill_values = {"total_cells": "10", "total_avg": "0.3125"}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "total_count": Entry("32"),
        "total_cells": Entry("100"),
        "total_avg": Entry("0.3125"),
    }

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay)

    assert overlay.manual_entries["total_cells"].get() == "100"
    assert overlay.manual_entries["total_avg"].get() == "3.125"


def test_ahmad_manual_inline_derivation_refreshes_auto_total_cells_after_avg_change() -> None:
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
    overlay._manual_dirty_fields = {"total_avg"}
    overlay._manual_autofill_values = {"total_cells": "90"}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "total_count": Entry("45"),
        "total_cells": Entry("90"),
        "total_avg": Entry("2.86"),
    }

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay)

    assert overlay.manual_entries["total_cells"].get() == "129"
    assert overlay.manual_entries["total_avg"].get() == "2.86"


def test_ahmad_manual_inline_derivation_keeps_just_cleared_total_cells_empty() -> None:
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
    overlay._manual_autofill_values = {"total_avg": "2.5"}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "total_count": Entry("40"),
        "total_cells": Entry(""),
        "total_avg": Entry("2.5"),
    }

    module.AhmadTkOverlay._on_manual_var_write(overlay, "total_cells")

    assert overlay.manual_entries["total_cells"].get() == ""


def test_ahmad_manual_inline_derivation_refills_total_cells_after_avg_reentered() -> None:
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
    overlay._manual_dirty_fields = {"total_cells", "total_count"}
    overlay._manual_autofill_values = {"total_avg": "2.439"}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "total_count": Entry("40"),
        "total_cells": Entry(""),
        "total_avg": Entry("2.5"),
    }

    module.AhmadTkOverlay._on_manual_var_write(overlay, "total_avg")

    assert overlay.manual_entries["total_cells"].get() == "100"
    assert "total_cells" not in overlay._manual_dirty_fields


def test_ahmad_manual_inline_derivation_keeps_user_cleared_field_empty() -> None:
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
    overlay._manual_dirty_fields = {"q3_count"}
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay.manual_entries = {
        "q3_avg": Entry("2.5"),
        "q3_count": Entry(""),
        "q3_cells": Entry("290"),
    }

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay)

    assert overlay.manual_entries["q3_count"].get() == ""
    assert overlay.manual_entries["q3_cells"].get() == "290"


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


def test_ahmad_manual_focus_selects_existing_text_for_easy_replace(monkeypatch) -> None:
    module = _ahmad_overlay_module()

    class FakeEntry:
        def __init__(self, value: str = "116") -> None:
            self.value = value
            self.state = "normal"
            self.selected: tuple[int, str] | None = None
            self.cursor: str | None = None

        def cget(self, key: str) -> str:
            return self.state if key == "state" else ""

        def get(self) -> str:
            return self.value

        def after_idle(self, callback) -> None:
            callback()

        def selection_range(self, start: int, end: str) -> None:
            self.selected = (start, end)

        def icursor(self, pos: str) -> None:
            self.cursor = pos

    monkeypatch.setattr(module.tk, "Entry", FakeEntry)
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay._manual_programmatic_update = False
    entry = FakeEntry()

    module.AhmadTkOverlay._focus_manual_entry(overlay, SimpleNamespace(widget=entry), field="q3_count")

    assert entry.selected == (0, "end")
    assert entry.cursor == "end"


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
        {
            "status": "ok",
            "context": {"phase": "settled", "session_id": "2404:old"},
            "truth": {"available": True},
        },
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


def test_ahmad_manual_state_does_not_reset_on_live_refresh_or_monitor_restart() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "q5_count": Entry("4"),
    }
    overlay._manual_active = True
    overlay._manual_edit_enabled = True
    overlay._manual_snapshot = {"hero": "victor"}
    overlay._manual_summary = {"status": "ok"}
    overlay._manual_dirty_fields = {"q5_count"}
    overlay._manual_autofill_values = {}
    overlay._manual_live_session_id = "2404:live"

    same_live_update = {
        "status": "ok",
        "context": {"phase": "bidding", "session_id": "2404:live"},
    }
    monitor_restarted = {
        "status": "stale_snapshot",
        "context": {"phase": "bidding", "session_id": "2404:live"},
        "stale": {"reason": "monitor_restarted"},
    }
    settled_without_truth = {
        "status": "ok",
        "context": {"phase": "settled", "session_id": "2404:live"},
        "truth": {"available": False},
    }

    assert not module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        same_live_update,
    )
    assert not module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        monitor_restarted,
    )
    assert not module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        settled_without_truth,
    )


def test_ahmad_manual_state_resets_on_session_ahead_or_settlement_truth() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {"hero": Entry("victor")}
    overlay._manual_active = True
    overlay._manual_edit_enabled = True
    overlay._manual_snapshot = {"hero": "victor"}
    overlay._manual_summary = {"status": "ok"}
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_live_session_id = "2404:live"

    assert module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        {
            "status": "stale_snapshot",
            "context": {"phase": "bidding", "session_id": "2404:live"},
            "stale": {"reason": "session_ahead"},
        },
    )
    assert module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        {
            "status": "ok",
            "context": {"phase": "settled", "session_id": "2404:live"},
            "truth": {"available": True},
        },
    )


def test_ahmad_manual_settlement_unlock_keeps_same_settlement_editable() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {"hero": Entry("ahmed")}
    overlay._manual_active = False
    overlay._manual_edit_enabled = True
    overlay._manual_settlement_edit_unlocked = True
    overlay._manual_snapshot = {}
    overlay._manual_summary = {}
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_live_session_id = "2404:live"

    same_settlement = {
        "status": "ok",
        "context": {"phase": "settled", "session_id": "2404:live"},
        "truth": {"available": True},
    }
    next_settlement = {
        "status": "ok",
        "context": {"phase": "settled", "session_id": "2404:new"},
        "truth": {"available": True},
    }

    assert not module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        same_settlement,
    )
    assert module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        next_settlement,
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
    assert overlay.manual_entries["map_id"].get() == "2404 养生学家居所"
    assert overlay.manual_entries["q5_avg"].get() == "6"
    assert overlay.manual_entries["q5_cells"].get() == "24"
    assert overlay.manual_entries["q5_count"].get() == "4"
    assert overlay.manual_entries["q4q5_count"].get() == "6"
    assert overlay._manual_live_session_id == "2404:live"


def test_ahmad_open_manual_panel_prefills_empty_live_context() -> None:
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

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.details_expanded = True
    overlay.manual_entries = {
        "hero": Entry(),
        "map_id": Entry(),
        "total_count": Entry(),
    }
    overlay.manual_vars = {}
    overlay.manual_status = Widget()
    overlay.manual_card = Widget()
    overlay._manual_active = False
    overlay._manual_edit_enabled = False
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay._manual_live_session_id = ""
    overlay._last_summary = {}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {"hero": "aisha", "map_id": 2521, "phase": "bidding", "session_id": "2521:live"},
        "ahmed_ref": {"evidence": {"total_count": 38}},
    }
    overlay._set_manual_edit_enabled = lambda enabled: setattr(overlay, "_manual_edit_enabled", enabled)  # type: ignore[method-assign]
    overlay._set_manual_settlement_button_state = lambda: None  # type: ignore[method-assign]

    assert module.AhmadTkOverlay.open_manual_panel(overlay) == "break"

    assert overlay.manual_entries["hero"].get() == "aisha"
    assert overlay.manual_entries["map_id"].get() == "2521 未知残骸"
    assert overlay.manual_entries["total_count"].get() == "38"
    assert overlay.manual_status.kwargs["text"] == "已填入当前，待应用"


def test_ahmad_open_manual_panel_does_not_overwrite_existing_inputs() -> None:
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

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.details_expanded = True
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
    }
    overlay.manual_vars = {}
    overlay.manual_status = Widget()
    overlay.manual_card = Widget()
    overlay._manual_active = False
    overlay._manual_edit_enabled = False
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay._manual_live_session_id = ""
    overlay._last_summary = {}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {"hero": "aisha", "map_id": 2521, "phase": "bidding", "session_id": "2521:live"},
        "ahmed_ref": {"evidence": {"total_count": 38}},
    }
    overlay._set_manual_edit_enabled = lambda enabled: setattr(overlay, "_manual_edit_enabled", enabled)  # type: ignore[method-assign]
    overlay._set_manual_settlement_button_state = lambda: None  # type: ignore[method-assign]

    assert module.AhmadTkOverlay.open_manual_panel(overlay) == "break"

    assert overlay.manual_entries["hero"].get() == "victor"
    assert overlay.manual_entries["map_id"].get() == "2404"
    assert overlay.manual_entries["total_count"].get() == "21"
    assert overlay.manual_status.kwargs["text"] == "手动模式，待填写"


def test_ahmad_clear_settlement_manual_values_keeps_hero_map_and_unlocks_edit() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value
            self.kwargs = {}

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

        def cget(self, key: str) -> str:
            return str(self.kwargs.get(key, "normal"))

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Tip:
        def __init__(self) -> None:
            self.text = ""

        def set_text(self, text: str) -> None:
            self.text = text

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("ahmed"),
        "map_id": Entry("2404"),
        "total_count": Entry("25"),
        "total_cells": Entry("50"),
        "q5_count": Entry("4"),
    }
    overlay.manual_vars = {}
    overlay.manual_buttons = {"清结算": Widget()}
    overlay.manual_clear_settlement_tip = Tip()
    overlay.manual_status = Widget()
    overlay.manual_card = Widget()
    overlay._manual_active = False
    overlay._manual_edit_enabled = False
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_snapshot = {}
    overlay._manual_summary = {}
    overlay._manual_dirty_fields = {"q5_count"}
    overlay._manual_autofill_values = {"total_count": "25"}
    overlay._manual_programmatic_update = False
    overlay._manual_live_session_id = ""
    rendered: list[dict] = []
    overlay.render = lambda summary: rendered.append(summary)
    settled = {
        "status": "ok",
        "context": {"hero": "ahmed", "map_id": 2404, "phase": "settled", "session_id": "2404:live"},
        "truth": {"available": True},
        "ahmed_ref": {
            "evidence": {
                "hero": "ahmed",
                "map_id": 2404,
                "total_count": 25,
                "total_grid_target": 50,
                "fixed_counts": {"q5": 4},
            }
        },
    }
    overlay._last_summary = settled
    overlay._last_live_summary = settled

    assert module.AhmadTkOverlay.clear_settlement_manual_values(overlay) == "break"

    assert overlay._manual_edit_enabled is True
    assert overlay._manual_settlement_edit_unlocked is True
    assert overlay.manual_entries["hero"].get() == "ahmed"
    assert "2404" in overlay.manual_entries["map_id"].get()
    assert overlay.manual_entries["total_count"].get() == ""
    assert overlay.manual_entries["q5_count"].get() == ""
    assert overlay._last_summary["context"]["phase"] == "manual"
    assert overlay._last_summary["truth"]["available"] is False
    assert overlay._last_summary["reference"]["readiness"] == "settlement_cleared"
    assert rendered == [overlay._last_summary]
    assert overlay.manual_buttons["清结算"].kwargs["state"] == "disabled"
    assert "清结算" in overlay.manual_status.kwargs["text"]


def test_ahmad_manual_toggle_returns_to_live_without_clearing_inputs() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value
            self.kwargs = {"state": "disabled"}

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

        def cget(self, key: str) -> str:
            return str(self.kwargs.get(key, ""))

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Tip:
        def __init__(self) -> None:
            self.text = ""

        def set_text(self, text: str) -> None:
            self.text = text

    render_calls: list[dict] = []
    standby_calls: list[dict] = []
    missing_calls: list[str] = []

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.details_expanded = False
    overlay.toggle_details = lambda: setattr(overlay, "details_expanded", True)
    overlay.manual_entries = {
        "hero": Entry(),
        "map_id": Entry(),
        "total_count": Entry(),
        "q5_count": Entry(),
    }
    overlay.manual_vars = {}
    overlay.manual_buttons = {
        "应用并启用": Widget(),
        "填入当前": Widget(),
        "清空手动": Widget(),
    }
    overlay.manual_button = Widget()
    overlay.manual_tip = Tip()
    overlay.manual_status = Widget()
    overlay.manual_card = Widget()
    overlay._manual_active = False
    overlay._manual_edit_enabled = False
    overlay._manual_snapshot = {}
    overlay._manual_summary = {}
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay._manual_live_session_id = ""
    overlay._last_summary = {}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {
            "hero": "victor",
            "map_id": 2404,
            "phase": "bidding",
            "session_id": "2404:live",
        },
        "ahmed_ref": {
            "evidence": {
                "hero": "victor",
                "map_id": 2404,
                "total_count": 21,
                "fixed_counts": {"q5": 4},
            }
        },
    }
    overlay.render = lambda data: render_calls.append(data)
    overlay.render_standby = lambda data: standby_calls.append(data)
    overlay.render_missing = lambda message: missing_calls.append(message)

    assert module.AhmadTkOverlay.toggle_manual_mode(overlay) == "break"

    assert overlay.details_expanded is True
    assert overlay._manual_edit_enabled is True
    assert overlay.manual_entries["hero"].get() == "victor"
    assert overlay.manual_entries["map_id"].get() == "2404 养生学家居所"
    assert overlay.manual_entries["total_count"].get() == "21"
    assert overlay.manual_entries["hero"].kwargs["state"] == "normal"
    assert overlay.manual_button.kwargs["text"] == "实时"
    assert overlay.manual_tip.text == module.MANUAL_RETURN_TIP_TEXT

    overlay._manual_active = True
    overlay._manual_snapshot = {"hero": "victor"}
    overlay._manual_summary = {"status": "ok"}
    overlay.manual_entries["hero"].value = "victor"
    overlay._manual_dirty_fields.add("hero")

    assert module.AhmadTkOverlay.toggle_manual_mode(overlay) == "break"

    assert overlay._manual_active is False
    assert overlay._manual_edit_enabled is False
    assert overlay._manual_snapshot == {}
    assert overlay.manual_entries["hero"].get() == "victor"
    assert overlay.manual_entries["hero"].kwargs["state"] == "disabled"
    assert overlay.manual_button.kwargs["text"] == "手填"
    assert overlay.manual_tip.text == module.MANUAL_TIP_TEXT
    assert "不会覆盖当前输入" in overlay.manual_tip.text
    assert render_calls == [overlay._last_live_summary]
    assert standby_calls == []
    assert missing_calls == []


def test_ahmad_clear_manual_inputs_keeps_manual_edit_mode() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value
            self.kwargs = {"state": "normal"}

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

        def cget(self, key: str) -> str:
            return str(self.kwargs.get(key, ""))

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    render_calls: list[dict] = []
    standby_calls: list[dict] = []
    missing_calls: list[str] = []

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2404 养生学家居所"),
        "total_count": Entry("21"),
        "q5_count": Entry("4"),
        "white_value_sum": Entry("300"),
        "q5_avg_value": Entry("34288.75"),
        "q5_value_sum": Entry("137155"),
    }
    overlay.manual_vars = {}
    overlay.manual_buttons = {"清结算": Widget()}
    overlay.manual_status = Widget()
    overlay.manual_card = Widget()
    overlay._manual_active = True
    overlay._manual_edit_enabled = True
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_snapshot = {"hero": "victor"}
    overlay._manual_summary = {"status": "ok"}
    overlay._manual_dirty_fields = {"hero", "q5_count"}
    overlay._manual_autofill_values = {"total_count": "21"}
    overlay._manual_programmatic_update = False
    overlay._manual_live_session_id = "2404:live"
    overlay._last_summary = {"status": "ok"}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {"phase": "bidding", "session_id": "2404:live"},
    }
    overlay.render = lambda data: render_calls.append(data)
    overlay.render_standby = lambda data: standby_calls.append(data)
    overlay.render_missing = lambda message: missing_calls.append(message)
    overlay._set_manual_settlement_button_state = lambda: None

    assert module.AhmadTkOverlay.clear_manual_inputs(overlay) == "break"

    assert overlay._manual_active is False
    assert overlay._manual_edit_enabled is True
    assert overlay._manual_snapshot == {}
    assert overlay._manual_summary == {}
    assert overlay._manual_live_session_id == ""
    assert overlay.manual_entries["hero"].get() == ""
    assert overlay.manual_entries["q5_count"].get() == ""
    assert overlay.manual_entries["white_value_sum"].get() == ""
    assert overlay.manual_entries["q5_avg_value"].get() == ""
    assert overlay.manual_entries["q5_value_sum"].get() == ""
    assert overlay.manual_status.kwargs["text"] == "已清空，待填写"
    assert render_calls == []
    assert standby_calls == []
    assert missing_calls == []


def test_ahmad_manual_return_to_live_autofills_missing_fields_from_cached_live() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value
            self.kwargs = {"state": "normal"}

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

        def cget(self, key: str) -> str:
            return str(self.kwargs.get(key, ""))

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    render_calls: list[dict] = []

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("ahmed"),
        "map_id": Entry("2403 科学家居所"),
        "total_count": Entry("30"),
        "q5_count": Entry("manual-same"),
        "q6_count": Entry(""),
    }
    overlay.manual_vars = {}
    overlay.manual_buttons = {}
    overlay.manual_button = Widget()
    overlay.manual_status = Widget()
    overlay.manual_card = Widget()
    overlay._manual_active = False
    overlay._manual_edit_enabled = True
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_snapshot = {}
    overlay._manual_summary = {}
    overlay._manual_dirty_fields = {"q5_count"}
    overlay._manual_autofill_values = {
        "hero": "ahmed",
        "map_id": "2403 科学家居所",
        "total_count": "30",
    }
    overlay._manual_programmatic_update = False
    overlay._manual_live_session_id = "2403:live"
    overlay._last_summary = {}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {
            "hero": "ahmed",
            "map_id": 2403,
            "phase": "bidding",
            "session_id": "2403:live",
        },
        "ahmed_ref": {
            "evidence": {
                "hero": "ahmed",
                "map_id": 2403,
                "total_count": 30,
                "fixed_counts": {"q5": 0, "q6": 1},
            }
        },
    }
    overlay.render = lambda data: render_calls.append(data)
    overlay.render_standby = lambda data: None
    overlay.render_missing = lambda message: None

    assert module.AhmadTkOverlay.return_to_live_mode(overlay) == "break"

    assert overlay._manual_edit_enabled is False
    assert overlay.manual_entries["q5_count"].get() == "manual-same"
    assert overlay.manual_entries["q6_count"].get() == "1"
    assert overlay.manual_entries["q6_count"].kwargs["state"] == "disabled"
    assert "q5_count" in overlay._manual_dirty_fields
    assert render_calls == [overlay._last_live_summary]


def test_ahmad_auto_sync_does_not_prefill_fresh_blank_manual_form() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self) -> None:
            self.value = ""
            self.kwargs = {"state": "disabled"}

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

        def cget(self, key: str) -> str:
            return str(self.kwargs.get(key, ""))

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

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
        "q5_count": Entry(),
    }
    overlay.manual_vars = {}
    overlay.manual_status = Status()
    overlay._manual_active = False
    overlay._manual_edit_enabled = False
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay._manual_live_session_id = ""
    live_summary = {
        "status": "ok",
        "context": {
            "hero": "victor",
            "map_id": 2404,
            "phase": "bidding",
            "session_id": "2404:live",
        },
        "ahmed_ref": {
            "evidence": {
                "hero": "victor",
                "map_id": 2404,
                "total_count": 21,
                "fixed_counts": {"q5": 4},
            },
        },
    }

    module.AhmadTkOverlay._auto_sync_manual_inputs(overlay, live_summary)

    assert overlay.manual_entries["hero"].get() == ""
    assert overlay.manual_entries["map_id"].get() == ""
    assert overlay.manual_entries["total_count"].get() == ""
    assert overlay.manual_entries["q5_count"].get() == ""
    assert overlay._manual_live_session_id == ""


def test_ahmad_manual_state_does_not_reset_when_first_live_frame_arrives() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {"hero": Entry("victor")}
    overlay._manual_active = True
    overlay._manual_edit_enabled = True
    overlay._manual_snapshot = {"hero": "victor"}
    overlay._manual_summary = {"status": "ok"}
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_live_session_id = ""

    assert not module.AhmadTkOverlay._should_reset_manual_for_summary(
        overlay,
        {
            "status": "ok",
            "context": {"phase": "bidding", "session_id": "2404:live"},
        },
    )


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


def test_ahmad_manual_input_summary_shows_quality_value_inputs() -> None:
    module = _ahmad_overlay_module()
    overlay = object.__new__(module.AhmadTkOverlay)

    summary = module.AhmadTkOverlay._manual_input_summary(
        overlay,
        {
            "total_count": 30,
            "avg_values": {"q5": 34288.75},
            "quality_values": {"q5": 137155},
        },
    )

    assert "金均价 34288.75" in summary
    assert "金总价 137155" in summary


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
    assert ref_inputs["total_cells"] == 34
    assert ref_inputs["avg_cells"] == {"q4": 1.8, "q5": 0.0}
    assert ref_inputs["fixed_counts"]["q5"] == 0
    assert ref_inputs["quality_cells"]["q5"] == 0
    assert ref_inputs["count_sums"] == {"q4q5q6": 6}


def test_ahmad_manual_zero_avg_autofills_empty_count_and_cells_on_edit() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "q5_avg": Entry("0"),
        "q5_count": Entry(""),
        "q5_cells": Entry(""),
        "q5_avg_value": Entry(""),
        "q5_value_sum": Entry(""),
    }
    overlay.manual_vars = {}
    overlay._manual_programmatic_update = False
    overlay._manual_dirty_fields = {"q5_avg", "q5_count", "q5_cells"}
    overlay._manual_autofill_values = {}

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay, trigger_field="q5_avg")

    assert overlay.manual_entries["q5_count"].get() == "0"
    assert overlay.manual_entries["q5_cells"].get() == "0"
    assert overlay.manual_entries["q5_avg_value"].get() == "0"
    assert overlay.manual_entries["q5_value_sum"].get() == "0"
    assert overlay._manual_autofill_values["q5_count"] == "0"
    assert overlay._manual_autofill_values["q5_cells"] == "0"
    assert overlay._manual_autofill_values["q5_avg_value"] == "0"
    assert overlay._manual_autofill_values["q5_value_sum"] == "0"


def test_ahmad_manual_zero_avg_does_not_autofill_over_conflict() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "q5_avg": Entry("0"),
        "q5_count": Entry("4"),
        "q5_cells": Entry(""),
        "q5_avg_value": Entry(""),
        "q5_value_sum": Entry(""),
    }
    overlay.manual_vars = {}
    overlay._manual_programmatic_update = False
    overlay._manual_dirty_fields = {"q5_avg", "q5_count"}
    overlay._manual_autofill_values = {}

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay, trigger_field="q5_avg")

    assert overlay.manual_entries["q5_count"].get() == "4"
    assert overlay.manual_entries["q5_cells"].get() == ""
    assert overlay.manual_entries["q5_avg_value"].get() == ""
    assert overlay.manual_entries["q5_value_sum"].get() == ""


def test_ahmad_manual_zero_avg_apply_fills_empty_count_and_cells() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
        "q5_avg": Entry("0"),
        "q5_count": Entry(""),
        "q5_cells": Entry(""),
        "q5_avg_value": Entry(""),
        "q5_value_sum": Entry(""),
    }
    overlay.manual_vars = {}
    overlay._manual_autofill_values = {}
    overlay._manual_dirty_fields = set()

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    assert overlay.manual_entries["q5_count"].get() == "0"
    assert overlay.manual_entries["q5_cells"].get() == "0"
    assert overlay.manual_entries["q5_avg_value"].get() == "0"
    assert overlay.manual_entries["q5_value_sum"].get() == "0"
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["fixed_counts"]["q5"] == 0
    assert ref_inputs["quality_cells"]["q5"] == 0
    assert ref_inputs["avg_values"]["q5"] == 0
    assert ref_inputs["quality_values"]["q5"] == 0


def test_ahmad_manual_zero_avg_value_autofills_quality_absent() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "q5_avg": Entry(""),
        "q5_count": Entry(""),
        "q5_cells": Entry(""),
        "q5_avg_value": Entry("0"),
        "q5_value_sum": Entry(""),
    }
    overlay.manual_vars = {}
    overlay._manual_programmatic_update = False
    overlay._manual_dirty_fields = {"q5_avg_value"}
    overlay._manual_autofill_values = {}

    module.AhmadTkOverlay._sync_manual_derived_fields(overlay, trigger_field="q5_avg_value")

    assert overlay.manual_entries["q5_avg"].get() == "0"
    assert overlay.manual_entries["q5_count"].get() == "0"
    assert overlay.manual_entries["q5_cells"].get() == "0"
    assert overlay.manual_entries["q5_value_sum"].get() == "0"


def test_ahmad_manual_zero_value_sum_apply_feeds_engine_exact_zero() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def delete(self, _start: int, _end: str) -> None:
            self.value = ""

        def insert(self, _index: int, value: str) -> None:
            self.value = value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2404"),
        "total_count": Entry("21"),
        "q5_avg": Entry(""),
        "q5_count": Entry(""),
        "q5_cells": Entry(""),
        "q5_avg_value": Entry(""),
        "q5_value_sum": Entry("0"),
    }
    overlay.manual_vars = {}
    overlay._manual_autofill_values = {}
    overlay._manual_dirty_fields = set()

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["avg_cells"]["q5"] == 0
    assert ref_inputs["fixed_counts"]["q5"] == 0
    assert ref_inputs["quality_cells"]["q5"] == 0
    assert ref_inputs["avg_values"]["q5"] == 0
    assert ref_inputs["quality_values"]["q5"] == 0

    result = module.run_reference_engine(snapshot, max_combos=60000).as_dict()
    assert result["evidence"]["fixed_counts"]["q5"] == 0
    assert result["evidence"]["quality_cells"]["q5"] == 0


def test_ahmad_manual_table_keeps_quality_and_value_field_order() -> None:
    module = _ahmad_overlay_module()

    assert module.MANUAL_QUALITY_ROWS == (
        ("白", "white_avg", "white_count", "white_cells"),
        ("绿", "green_avg", "green_count", "green_cells"),
        ("白绿", "q1_avg", "q1_count", "q1_cells"),
        ("蓝", "q3_avg", "q3_count", "q3_cells"),
        ("紫", "q4_avg", "q4_count", "q4_cells"),
        ("金", "q5_avg", "q5_count", "q5_cells"),
        ("红", "q6_avg", "q6_count", "q6_cells"),
    )
    assert module.MANUAL_VALUE_ROWS == (
        ("白", "white_avg_value", "white_value_sum"),
        ("绿", "green_avg_value", "green_value_sum"),
        ("白绿", "q1_avg_value", "q1_value_sum"),
        ("蓝", "q3_avg_value", "q3_value_sum"),
        ("紫", "q4_avg_value", "q4_value_sum"),
        ("金", "q5_avg_value", "q5_value_sum"),
        ("红", "q6_avg_value", "q6_value_sum"),
    )


def test_ahmad_manual_snapshot_keeps_quality_avg_value_and_value_sum() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("ahmed"),
        "map_id": Entry("4406"),
        "total_count": Entry("10"),
        "q5_avg_value": Entry("34288.75"),
        "q5_value_sum": Entry("137155"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["avg_values"] == {"q5": 34288.75}
    assert ref_inputs["quality_values"] == {"q5": 137155}

    result = module.run_reference_engine(snapshot, max_combos=60000).as_dict()
    assert result["evidence"]["fixed_counts"]["q5"] == 4
    assert result["quality_count_ranges"]["q5"] == [4, 4, 4]


def test_ahmad_manual_snapshot_combines_white_green_value_inputs_as_q1() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("aisha"),
        "map_id": Entry("2401"),
        "total_count": Entry("12"),
        "white_count": Entry("3"),
        "white_value_sum": Entry("300"),
        "green_count": Entry("4"),
        "green_avg_value": Entry("200"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["split_counts"] == {"white": 3, "green": 4}
    assert ref_inputs["quality_values"] == {"q1": 1100}
    assert ref_inputs["avg_values"] == {"q1": 1100 / 7}


def test_ahmad_manual_snapshot_rejects_single_side_white_green_value() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("aisha"),
        "map_id": Entry("2401"),
        "total_count": Entry("12"),
        "white_value_sum": Entry("300"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "白/绿价值需同时填写" in error
    assert "缺少绿" in error


def test_ahmad_manual_snapshot_rejects_mismatched_quality_avg_value_and_sum() -> None:
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
        "total_count": Entry("10"),
        "q5_count": Entry("4"),
        "q5_avg_value": Entry("34288.75"),
        "q5_value_sum": Entry("999999"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "金均价与金总价/金件不一致" in error


def test_ahmad_manual_snapshot_rejects_zero_avg_with_nonzero_quality_inputs() -> None:
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
        "q5_avg": Entry("0"),
        "q5_count": Entry("4"),
        "q5_cells": Entry("1"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "金均格为0时" in error
    assert "金件" in error or "金格" in error


def test_ahmad_manual_snapshot_accepts_total_only_with_live_context_fallback() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry(""),
        "map_id": Entry(""),
        "total_count": Entry("35"),
        "total_cells": Entry("105"),
    }
    overlay._last_summary = {}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {
            "hero": "ahmed",
            "map_id": 2403,
            "phase": "bidding",
            "session_id": "2403:live",
        },
        "ahmed_ref": {"evidence": {"hero": "ahmed", "map_id": 2403}},
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    assert snapshot["hero"] == "ahmed"
    assert snapshot["map_id"] == 2403
    assert snapshot["structured_ref_inputs"] == {
        "total_count": 35,
        "avg_cells": {},
        "fixed_counts": {},
        "total_cells": 105,
    }
    source = snapshot["ui_contract"]["source"]
    assert source["manual_map_input"] == ""
    assert source["manual_context_fallback"] == {
        "hero": "live_context",
        "map_id": "live_context",
    }

    result = module.run_reference_engine(snapshot, max_combos=60000).as_dict()
    assert result["status"] == "count_prior"
    assert result["balanced"] not in (None, "")
    assert result["total_grid_range"] == [105, 105, 105]


def test_ahmad_manual_snapshot_uses_quality_avg_after_total_only_fallback() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry(""),
        "map_id": Entry(""),
        "total_count": Entry("35"),
        "total_cells": Entry("105"),
        "q4_avg": Entry("3.5"),
    }
    overlay._last_summary = {}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {"hero": "ahmed", "map_id": 2403, "phase": "bidding"},
        "ahmed_ref": {"evidence": {"hero": "ahmed", "map_id": 2403}},
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    assert snapshot["structured_ref_inputs"]["avg_cells"] == {"q4": 3.5}

    result = module.run_reference_engine(snapshot, max_combos=60000).as_dict()
    assert result["status"] == "count_prior"
    assert result["balanced"] not in (None, "")
    assert result["quality_count_ranges"]["q4"][0] > 0


def test_ahmad_manual_snapshot_accepts_chinese_map_name() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("维克托"),
        "map_id": Entry("养生学家居所"),
        "total_count": Entry("21"),
        "q5_count": Entry("4"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    assert snapshot["map_id"] == 2404
    assert snapshot["map_name"] == "养生学家居所"
    assert snapshot["ui_contract"]["context"]["map_id"] == 2404
    assert snapshot["ui_contract"]["context"]["map_name"] == "养生学家居所"
    assert snapshot["ui_contract"]["source"]["manual_map_input"] == "养生学家居所"


def test_ahmad_manual_snapshot_accepts_all_chinese_hero_aliases() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    for hero_text, expected in (
        ("艾哈迈德", "ahmed"),
        ("维克托", "victor"),
        ("艾莎", "aisha"),
    ):
        overlay = object.__new__(module.AhmadTkOverlay)
        overlay.manual_entries = {
            "hero": Entry(hero_text),
            "map_id": Entry("养生学家居所"),
            "total_count": Entry("21"),
            "q5_count": Entry("4"),
        }

        snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

        assert error == ""
        assert snapshot is not None
        assert snapshot["hero"] == expected
        assert snapshot["map_id"] == 2404
        assert snapshot["map_name"] == "养生学家居所"


def test_ahmad_manual_snapshot_accepts_project_processed_map_id_and_name() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("维克托"),
        "map_id": Entry("3101 未知快递"),
        "total_count": Entry("21"),
        "q5_count": Entry("4"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    assert snapshot["map_id"] == 3101
    assert snapshot["map_name"] == "未知快递"


def test_ahmad_manual_snapshot_rejects_unknown_chinese_map_name() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("维克托"),
        "map_id": Entry("不存在地图"),
        "total_count": Entry("21"),
        "q5_count": Entry("4"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "地图无法识别" in error


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


def test_ahmad_manual_display_avg_keeps_trailing_zero_semantics() -> None:
    module = _ahmad_overlay_module()

    assert module._manual_avg_grid_options_from_text(21, 1.8, "1.80") == [38]
    assert module._manual_avg_grid_options_from_text(5, 1.8, "1.80") == []
    assert module._manual_avg_grid_options_from_text(5, 1.8, "1.8") == [9]
    assert module._manual_avg_grid_options_from_text(11, 2.9, "2.90") == [32]
    assert module._manual_avg_grid_options_from_text(10, 2.9, "2.90") == []


def test_ahmad_manual_snapshot_accepts_trailing_zero_display_avg() -> None:
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
        "total_count": Entry("55"),
        "q1_avg": Entry("1.80"),
        "q1_cells": Entry("38"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    ref_inputs = snapshot["structured_ref_inputs"]
    assert ref_inputs["fixed_counts"] == {"q1": 21}
    assert ref_inputs["quality_cells"] == {"q1": 38}
    assert ref_inputs["avg_cells"] == {"q1": 38 / 21}


def test_ahmad_manual_snapshot_uses_display_avg_for_total_avg() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2401"),
        "total_count": Entry("21"),
        "total_avg": Entry("1.619"),
        "q4_avg": Entry("1.8"),
        "q4_count": Entry("5"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert error == ""
    assert snapshot is not None
    assert snapshot["structured_ref_inputs"]["total_cells"] == 34


def test_ahmad_manual_snapshot_rejects_trimmed_exact_ratio_for_total_avg() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("victor"),
        "map_id": Entry("2401"),
        "total_count": Entry("10"),
        "total_avg": Entry("2.90"),
        "q4_avg": Entry("1.8"),
        "q4_count": Entry("5"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "全均格" in error


def test_ahmad_manual_snapshot_rejects_conflicting_total_cells_and_avg() -> None:
    module = _ahmad_overlay_module()

    class Entry:
        def __init__(self, value: str) -> None:
            self.value = value

        def get(self) -> str:
            return self.value

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.manual_entries = {
        "hero": Entry("艾哈迈德"),
        "map_id": Entry("设计师居所"),
        "total_count": Entry("45"),
        "total_cells": Entry("90"),
        "total_avg": Entry("2.86"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "全均格与总格/总件不一致" in error


def test_ahmad_manual_snapshot_rejects_trimmed_exact_ratio_for_trailing_zero_avg() -> None:
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
        "total_count": Entry("55"),
        "q4_avg": Entry("2.90"),
        "q4_count": Entry("10"),
        "q4_cells": Entry("29"),
    }

    snapshot, error = module.AhmadTkOverlay._manual_inputs_snapshot(overlay)

    assert snapshot is None
    assert "紫均格" in error
    assert "不一致" in error


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
    assert "紫件" in error


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


def test_ahmad_apply_manual_from_settlement_uses_standalone_manual_result() -> None:
    module = _ahmad_overlay_module()

    class Status:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    overlay = object.__new__(module.AhmadTkOverlay)
    manual_snapshot = {"structured_ref_inputs": {"total_count": 25}}
    manual_summary = {"status": "ok", "context": {"phase": "manual"}}
    rendered: list[dict] = []
    overlay._manual_inputs_snapshot = lambda: (manual_snapshot, "")  # type: ignore[method-assign]
    overlay._manual_result_summary = lambda snapshot: manual_summary  # type: ignore[method-assign]
    overlay._manual_overlay_summary = lambda *_args: (_ for _ in ()).throw(AssertionError("overlay path should not run"))  # type: ignore[method-assign]
    overlay._set_manual_edit_enabled = lambda enabled: setattr(overlay, "_manual_edit_enabled", enabled)  # type: ignore[method-assign]
    overlay._set_manual_button_state = lambda: None  # type: ignore[method-assign]
    overlay.render = lambda summary: rendered.append(summary)  # type: ignore[method-assign]
    overlay.render_standby = lambda summary: rendered.append(summary)  # type: ignore[method-assign]
    overlay.manual_status = Status()
    overlay._manual_active = False
    overlay._manual_edit_enabled = True
    overlay._manual_settlement_edit_unlocked = True
    overlay._manual_snapshot = {}
    overlay._manual_summary = {}
    overlay._last_summary = {}
    overlay._last_live_snapshot = {"phase": "settled"}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {"phase": "settled", "session_id": "2404:live"},
        "truth": {"available": True},
    }

    module.AhmadTkOverlay.apply_manual_inputs(overlay)

    assert overlay._manual_active is True
    assert overlay._manual_snapshot == manual_snapshot
    assert overlay._last_summary == manual_summary
    assert rendered == [manual_summary]
    assert "结算页已脱离" in overlay.manual_status.kwargs["text"]


def test_ahmad_apply_manual_uses_standalone_result_while_live_continues() -> None:
    module = _ahmad_overlay_module()

    class Status:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    manual_snapshot = {
        "hero": "ahmed",
        "map_id": 2403,
        "structured_ref_inputs": {"total_count": 35, "total_cells": 105},
    }
    manual_summary = {"status": "ok", "context": {"phase": "manual"}}
    rendered: list[dict] = []

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay._manual_inputs_snapshot = lambda: (manual_snapshot, "")  # type: ignore[method-assign]
    overlay._manual_result_summary = lambda snapshot: manual_summary  # type: ignore[method-assign]
    overlay._manual_overlay_summary = lambda *_args: (_ for _ in ()).throw(AssertionError("manual apply must not merge live snapshot"))  # type: ignore[method-assign]
    overlay._set_manual_edit_enabled = lambda enabled: setattr(overlay, "_manual_edit_enabled", enabled)  # type: ignore[method-assign]
    overlay._set_manual_button_state = lambda: None  # type: ignore[method-assign]
    overlay.render = lambda summary: rendered.append(summary)  # type: ignore[method-assign]
    overlay.render_standby = lambda summary: rendered.append(summary)  # type: ignore[method-assign]
    overlay.manual_status = Status()
    overlay._manual_active = False
    overlay._manual_edit_enabled = True
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_snapshot = {}
    overlay._manual_summary = {}
    overlay._last_summary = {}
    overlay._last_live_snapshot = {
        "structured_ref_inputs": {"fixed_counts": {"q5": 99}},
    }
    overlay._last_live_summary = {
        "status": "ok",
        "context": {"phase": "bidding", "session_id": "live-session"},
        "truth": {"available": False},
    }

    module.AhmadTkOverlay.apply_manual_inputs(overlay)

    assert overlay._manual_active is True
    assert overlay._manual_snapshot == manual_snapshot
    assert overlay._last_summary == manual_summary
    assert rendered == [manual_summary]
    assert "实时后台" in overlay.manual_status.kwargs["text"]


def test_ahmad_apply_manual_uses_background_worker_when_available() -> None:
    module = _ahmad_overlay_module()

    class Status:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    manual_snapshot = {
        "hero": "ahmed",
        "map_id": 2403,
        "structured_ref_inputs": {"total_count": 35, "total_cells": 105},
    }
    manual_summary = {"status": "ok", "context": {"phase": "manual"}}
    rendered: list[dict] = []

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay._manual_inputs_snapshot = lambda: (manual_snapshot, "")  # type: ignore[method-assign]
    overlay._manual_result_summary = lambda snapshot: manual_summary  # type: ignore[method-assign]
    overlay._set_manual_edit_enabled = lambda enabled: setattr(overlay, "_manual_edit_enabled", enabled)  # type: ignore[method-assign]
    overlay._set_manual_button_state = lambda: None  # type: ignore[method-assign]
    overlay.render = lambda summary: rendered.append(summary)  # type: ignore[method-assign]
    overlay.render_standby = lambda summary: rendered.append(summary)  # type: ignore[method-assign]
    overlay.manual_status = Status()
    overlay._manual_result_queue = queue.Queue()
    overlay._manual_worker_running = False
    overlay._manual_worker_seq = 0
    overlay._manual_input_revision = 7
    overlay._manual_active = False
    overlay._manual_edit_enabled = True
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_snapshot = {}
    overlay._manual_summary = {}
    overlay._last_summary = {}
    overlay._last_live_summary = {
        "status": "ok",
        "context": {"phase": "bidding", "session_id": "live-session"},
        "truth": {"available": False},
    }

    module.AhmadTkOverlay.apply_manual_inputs(overlay)

    assert rendered == []
    assert overlay._manual_worker_running is True
    assert overlay.manual_status.kwargs["text"] == "手动计算中..."

    for _ in range(50):
        module.AhmadTkOverlay._drain_manual_summary_results(overlay)
        if rendered:
            break
        time.sleep(0.01)

    assert overlay._manual_worker_running is False
    assert overlay._manual_active is True
    assert overlay._manual_snapshot == manual_snapshot
    assert overlay._last_summary == manual_summary
    assert rendered == [manual_summary]


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
    assert result["red"]["uncertainty_summary"].startswith("未锁 ")
    assert any(flag["label"] == "宽约束快速" for flag in result["flags"])
    assert not any(flag["label"] == "总件估计" for flag in result["flags"])


def test_ahmad_server_preserves_rare_signal_diagnostics(tmp_path: Path) -> None:
    module = _ahmad_server_module()
    rare_signals = {
        "present": True,
        "summary": "终极审计:diagnostic_only",
        "role_counts": {"diagnostic_only": 1},
        "actions": [
            {
                "action_id": 100121,
                "label": "终极审计",
                "semantic": "total_value",
                "ref_v0_role": "diagnostic_only",
                "result": 728211,
            }
        ],
        "public_info": [],
    }
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
            "diagnostics": {"rare_signals": rare_signals},
            "source": {"created_at": time.time()},
        },
    }

    result = module.summarize_snapshot(snapshot, snapshot_path=tmp_path / "latest_snapshot.json")

    assert result["diagnostics"]["rare_signals"] == rare_signals


def test_ahmad_refresh_does_not_reschedule_after_watched_pid_exit(monkeypatch, tmp_path: Path) -> None:
    module = _ahmad_overlay_module()

    class Root:
        def __init__(self) -> None:
            self.destroyed = False
            self.after_calls: list[tuple[int, object]] = []

        def destroy(self) -> None:
            self.destroyed = True

        def after(self, interval: int, callback: object) -> None:
            self.after_calls.append((interval, callback))

    monkeypatch.setattr(module, "_watched_pid_exited", lambda _pids: True)
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = Root()
    overlay.interval_ms = 1000
    overlay.exit_when_pids = (123,)
    overlay._exit_cleanup_done = False
    overlay._last_ui_heartbeat_at = time.monotonic()
    overlay._last_ui_stall_bucket = 0
    overlay.snapshot_path = tmp_path / "latest_snapshot.json"
    overlay.diagnostic_profile = "portable"

    module.AhmadTkOverlay.refresh(overlay)

    assert overlay.root.destroyed is True
    assert overlay.root.after_calls == []


def test_ahmad_render_missing_uses_action_text_for_next_step() -> None:
    module = _ahmad_overlay_module()

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.title = Widget()
    overlay.subtitle = Widget()
    overlay.status = Widget()
    overlay.action_rows = {
        "动作": Widget(),
        "最近": Widget(),
        "候选": Widget(),
        "下一步": Widget(),
    }
    overlay.evidence_rows = {
        "匹配": Widget(),
        "密度": Widget(),
        "诊断": Widget(),
    }
    overlay.detail_rows = {
        "外援": Widget(),
        "备注": Widget(),
    }
    overlay._render_flags = lambda *args, **kwargs: None
    overlay._set_settlement_button_state = lambda *args, **kwargs: None
    overlay._clear_values = lambda *args, **kwargs: None
    overlay._render_minimap = lambda *args, **kwargs: None
    overlay._record_summary_diagnostic = lambda *args, **kwargs: None
    overlay._capture_status = lambda: {
        "source": "windivert",
        "active_flows": 1,
        "sniffed_packets": 0,
        "raw_packets": 0,
        "accepted_frames": 0,
    }

    module.AhmadTkOverlay.render_missing(overlay, "等待 latest_snapshot.json")

    assert overlay.action_rows["下一步"].kwargs["text"] == "等待对局包"
    assert overlay.evidence_rows["匹配"].kwargs["text"] == "no_raw_packets"


def test_ahmad_render_missing_surfaces_windivert_open_error() -> None:
    module = _ahmad_overlay_module()

    class Widget:
        def __init__(self) -> None:
            self.kwargs = {}

        def configure(self, **kwargs) -> None:
            self.kwargs.update(kwargs)

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.title = Widget()
    overlay.subtitle = Widget()
    overlay.status = Widget()
    overlay.action_rows = {
        "动作": Widget(),
        "最近": Widget(),
        "候选": Widget(),
        "下一步": Widget(),
    }
    overlay.evidence_rows = {
        "匹配": Widget(),
        "密度": Widget(),
        "诊断": Widget(),
    }
    overlay.detail_rows = {
        "外援": Widget(),
        "备注": Widget(),
    }
    rendered_flags = []
    overlay._render_flags = rendered_flags.extend
    overlay._set_settlement_button_state = lambda *args, **kwargs: None
    overlay._clear_values = lambda *args, **kwargs: None
    overlay._render_minimap = lambda *args, **kwargs: None
    overlay._record_summary_diagnostic = lambda *args, **kwargs: None
    overlay._capture_status = lambda: {
        "source": "windivert",
        "active_flows": 2,
        "sniffed_packets": 0,
        "raw_packets": 0,
        "accepted_frames": 0,
        "error_code": "windivert_dependency_missing",
        "error_message": "[WinError 2]",
        "error_hint": "重新解压 full 包，信任整个文件夹后用管理员入口启动。",
    }

    module.AhmadTkOverlay.render_missing(overlay, "等待 latest_snapshot.json")

    assert overlay.action_rows["下一步"].kwargs["text"] == "检查防火墙/安全软件"
    assert overlay.evidence_rows["匹配"].kwargs["text"] == "windivert_dependency_missing"
    assert rendered_flags[0]["level"] == "risk"
    assert "WinError 2" in rendered_flags[0]["detail"]


def test_ahmad_refresh_writes_runtime_status_while_waiting_for_packets(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _ahmad_overlay_module()

    class Root:
        def __init__(self) -> None:
            self.after_calls: list[tuple[int, object]] = []

        def after(self, interval: int, callback: object) -> None:
            self.after_calls.append((interval, callback))

    snapshot_path = tmp_path / "latest_snapshot.json"
    missing_calls: list[str] = []

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = Root()
    overlay.interval_ms = 1000
    overlay.exit_when_pids = ()
    overlay._exit_cleanup_done = False
    overlay._last_ui_heartbeat_at = time.monotonic()
    overlay._last_ui_stall_bucket = 0
    overlay.snapshot_path = snapshot_path
    overlay.diagnostic_profile = "portable"
    overlay._last_signature = None
    overlay._last_capture_status_signature = None
    overlay._last_summary = {}
    overlay._last_live_summary = {}
    overlay._last_live_snapshot = {}
    overlay._summary_result_queue = queue.Queue()
    overlay._summary_worker_running = False
    overlay._summary_worker_seq = 0
    overlay._summary_worker_signature = None
    overlay._manual_result_queue = queue.Queue()
    overlay._manual_worker_running = False
    overlay._manual_worker_seq = 0
    overlay._manual_active = False
    overlay._manual_edit_enabled = False
    overlay.render_missing = lambda message: missing_calls.append(message)
    overlay._capture_status = lambda: {
        "source": "windivert",
        "process_name": "BidKing.exe",
        "active_flows": 1,
        "sniffed_packets": 12,
        "raw_packets": 0,
        "accepted_frames": 0,
        "ignored_frames": 0,
    }

    monkeypatch.setattr(module, "_watched_pid_exited", lambda _pids: False)

    module.AhmadTkOverlay.refresh(overlay)

    runtime_path = tmp_path / module.UI_RUNTIME_STATUS
    payload = json.loads(runtime_path.read_text(encoding="utf-8"))
    assert missing_calls == ["等待 latest_snapshot.json"]
    assert payload["event"] == "waiting_for_snapshot"
    assert payload["snapshot_exists"] is False
    assert payload["capture"]["wait_state"] == "no_raw_packets"
    assert payload["capture"]["active_flows"] == 1
    assert payload["capture"]["raw_packets"] == 0
    assert overlay.root.after_calls == [(1000, overlay.refresh)]


def test_ahmad_refresh_summarizes_snapshot_in_background_worker(monkeypatch, tmp_path: Path) -> None:
    module = _ahmad_overlay_module()

    class Root:
        def __init__(self) -> None:
            self.destroyed = False
            self.after_calls: list[tuple[int, object]] = []

        def destroy(self) -> None:
            self.destroyed = True

        def after(self, interval: int, callback: object) -> None:
            self.after_calls.append((interval, callback))

    snapshot_path = tmp_path / "latest_snapshot.json"
    snapshot_path.write_text('{"file": "snapshot"}', encoding="utf-8")
    rendered: list[dict] = []
    summary = {
        "status": "ok",
        "updated_at_text": "12:34:56",
        "context": {"phase": "bidding", "session_id": "2404:new"},
        "reference": {},
        "evidence": {},
        "red": {},
        "ahmed_ref": {"evidence": {}},
        "diagnostics": {"rare_signals": {}},
        "minimap": {},
        "truth": {"available": False},
    }

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = Root()
    overlay.interval_ms = 1000
    overlay.exit_when_pids = ()
    overlay._exit_cleanup_done = False
    overlay._last_ui_heartbeat_at = time.monotonic()
    overlay._last_ui_stall_bucket = 0
    overlay.snapshot_path = snapshot_path
    overlay.diagnostic_profile = "portable"
    overlay._last_signature = (0, 0)
    overlay._last_capture_status_signature = None
    overlay._last_summary = {}
    overlay._last_live_summary = {}
    overlay._last_live_snapshot = {}
    overlay._summary_result_queue = queue.Queue()
    overlay._summary_worker_running = False
    overlay._summary_worker_seq = 0
    overlay._summary_worker_signature = None
    overlay._manual_result_queue = queue.Queue()
    overlay._manual_worker_running = False
    overlay._manual_worker_seq = 0
    overlay._manual_active = False
    overlay._manual_edit_enabled = False
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_live_session_id = ""
    overlay.render = lambda data: rendered.append(data)
    overlay.render_standby = lambda data: rendered.append(data)
    overlay.render_missing = lambda message: None
    overlay._record_ui_health = lambda row: None
    overlay._capture_status = lambda: {}

    monkeypatch.setattr(module, "_watched_pid_exited", lambda _pids: False)
    monkeypatch.setattr(module, "_read_json", lambda path: {"file": "snapshot"})
    monkeypatch.setattr(module, "summarize_snapshot", lambda snapshot, snapshot_path: dict(summary))

    module.AhmadTkOverlay.refresh(overlay)

    assert rendered == []
    assert overlay._summary_worker_running is True

    for _ in range(50):
        module.AhmadTkOverlay.refresh(overlay)
        if rendered:
            break
        time.sleep(0.01)

    assert overlay._summary_worker_running is False
    assert overlay._last_live_summary["context"]["session_id"] == "2404:new"
    assert rendered == [overlay._last_live_summary]


def test_ahmad_refresh_coalesces_summary_worker_to_latest_snapshot(
    monkeypatch, tmp_path: Path
) -> None:
    module = _ahmad_overlay_module()

    class Root:
        def __init__(self) -> None:
            self.after_calls: list[tuple[int, object]] = []

        def after(self, interval: int, callback: object) -> None:
            self.after_calls.append((interval, callback))

    snapshot_path = tmp_path / "latest_snapshot.json"
    snapshot_path.write_text('{"file": "snapshot"}', encoding="utf-8")
    rendered: list[dict] = []
    summarize_calls: list[str] = []

    def _summarize(snapshot: dict, snapshot_path: Path) -> dict:
        session_id = snapshot.get("session_id", "?")
        summarize_calls.append(str(session_id))
        if session_id == "2404:slow":
            time.sleep(0.05)
        return {
            "status": "ok",
            "updated_at_text": "12:34:56",
            "context": {"phase": "bidding", "session_id": session_id},
            "reference": {},
            "evidence": {},
            "red": {},
            "ahmed_ref": {"evidence": {}},
            "diagnostics": {"rare_signals": {}},
            "minimap": {},
            "truth": {"available": False},
        }

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = Root()
    overlay.interval_ms = 1000
    overlay.exit_when_pids = ()
    overlay._exit_cleanup_done = False
    overlay._last_ui_heartbeat_at = time.monotonic()
    overlay._last_ui_stall_bucket = 0
    overlay.snapshot_path = snapshot_path
    overlay.diagnostic_profile = "portable"
    overlay._last_signature = None
    overlay._last_capture_status_signature = None
    overlay._last_summary = {}
    overlay._last_live_summary = {}
    overlay._last_live_snapshot = {}
    overlay._summary_result_queue = queue.Queue()
    overlay._summary_worker_running = False
    overlay._summary_worker_seq = 0
    overlay._summary_worker_signature = None
    overlay._summary_worker_pending = None
    overlay._manual_result_queue = queue.Queue()
    overlay._manual_worker_running = False
    overlay._manual_worker_seq = 0
    overlay._manual_active = False
    overlay._manual_edit_enabled = False
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_live_session_id = ""
    overlay.render = lambda data: rendered.append(data)
    overlay.render_standby = lambda data: rendered.append(data)
    overlay.render_missing = lambda message: None
    overlay._record_ui_health = lambda row: None
    overlay._capture_status = lambda: {}
    overlay._should_reset_manual_for_summary = lambda summary: False
    overlay._auto_sync_manual_inputs = lambda summary: None

    def _apply_live_summary(snapshot: dict, summary: dict) -> None:
        overlay._last_live_snapshot = snapshot
        overlay._last_live_summary = summary
        overlay._last_summary = summary
        overlay.render(summary)

    overlay._apply_live_summary = _apply_live_summary
    signature_state = {"value": 0}

    def _signature() -> tuple[int, int]:
        return (signature_state["value"], 0)

    overlay._snapshot_signature = _signature

    read_queue: list[dict] = [
        {"session_id": "2404:slow"},
        {"session_id": "2404:latest"},
    ]

    def _read_json(path: Path) -> dict:
        if read_queue:
            signature_state["value"] += 1
            return read_queue.pop(0)
        return {"session_id": "2404:latest"}

    monkeypatch.setattr(module, "_watched_pid_exited", lambda _pids: False)
    monkeypatch.setattr(module, "_read_json", _read_json)
    monkeypatch.setattr(module, "summarize_snapshot", _summarize)

    module.AhmadTkOverlay.refresh(overlay)
    module.AhmadTkOverlay.refresh(overlay)

    for _ in range(100):
        module.AhmadTkOverlay.refresh(overlay)
        if (
            not overlay._summary_worker_running
            and overlay._summary_worker_pending is None
            and overlay._last_live_summary.get("context", {}).get("session_id")
            == "2404:latest"
        ):
            break
        time.sleep(0.01)

    assert overlay._last_live_summary["context"]["session_id"] == "2404:latest"
    assert summarize_calls[-1] == "2404:latest"
    assert "2404:slow" in summarize_calls


def test_ahmad_refresh_skips_stale_worker_result_when_pending_snapshot(
    monkeypatch, tmp_path: Path
) -> None:
    module = _ahmad_overlay_module()

    class Root:
        def after(self, interval: int, callback: object) -> None:
            return None

    snapshot_path = tmp_path / "latest_snapshot.json"
    rendered_sessions: list[str] = []

    def _summarize(snapshot: dict, snapshot_path: Path) -> dict:
        session_id = str(snapshot.get("session_id", "?"))
        if session_id == "2404:slow":
            time.sleep(0.06)
        return {
            "status": "ok",
            "updated_at_text": "12:34:56",
            "context": {"phase": "bidding", "session_id": session_id},
            "reference": {},
            "evidence": {},
            "red": {},
            "ahmed_ref": {"evidence": {}},
            "diagnostics": {"rare_signals": {}},
            "minimap": {},
            "truth": {"available": False},
        }

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = Root()
    overlay.interval_ms = 1000
    overlay.exit_when_pids = ()
    overlay._exit_cleanup_done = False
    overlay._last_ui_heartbeat_at = time.monotonic()
    overlay._last_ui_stall_bucket = 0
    overlay.snapshot_path = snapshot_path
    overlay.diagnostic_profile = "portable"
    overlay._last_signature = None
    overlay._last_capture_status_signature = None
    overlay._last_summary = {}
    overlay._last_live_summary = {}
    overlay._last_live_snapshot = {}
    overlay._summary_result_queue = queue.Queue()
    overlay._summary_worker_running = False
    overlay._summary_worker_seq = 0
    overlay._summary_worker_signature = None
    overlay._summary_worker_pending = None
    overlay._manual_result_queue = queue.Queue()
    overlay._manual_worker_running = False
    overlay._manual_active = False
    overlay._manual_edit_enabled = False
    overlay.render = lambda data: rendered_sessions.append(
        str(data.get("context", {}).get("session_id"))
    )
    overlay.render_standby = lambda data: None
    overlay.render_missing = lambda message: None
    overlay._record_ui_health = lambda row: None
    overlay._capture_status = lambda: {}
    overlay._should_reset_manual_for_summary = lambda summary: False
    overlay._auto_sync_manual_inputs = lambda summary: None

    def _apply_live_summary(snapshot: dict, summary: dict) -> None:
        overlay._last_live_snapshot = snapshot
        overlay._last_live_summary = summary
        overlay._last_summary = summary
        overlay.render(summary)

    overlay._apply_live_summary = _apply_live_summary
    signature_state = {"value": 0}

    def _signature() -> tuple[int, int]:
        return (signature_state["value"], 0)

    overlay._snapshot_signature = _signature

    read_queue = [{"session_id": "2404:slow"}, {"session_id": "2404:latest"}]

    def _read_json(path: Path) -> dict:
        if read_queue:
            signature_state["value"] += 1
            return read_queue.pop(0)
        return {"session_id": "2404:latest"}

    monkeypatch.setattr(module, "_watched_pid_exited", lambda _pids: False)
    monkeypatch.setattr(module, "_read_json", _read_json)
    monkeypatch.setattr(module, "summarize_snapshot", _summarize)

    module.AhmadTkOverlay.refresh(overlay)
    module.AhmadTkOverlay.refresh(overlay)

    for _ in range(120):
        module.AhmadTkOverlay.refresh(overlay)
        if (
            not overlay._summary_worker_running
            and overlay._summary_worker_pending is None
            and overlay._last_live_summary.get("context", {}).get("session_id")
            == "2404:latest"
        ):
            break
        time.sleep(0.01)

    assert overlay._last_live_summary["context"]["session_id"] == "2404:latest"
    assert "2404:slow" not in rendered_sessions


def test_ahmad_refresh_freezes_view_while_manual_edit_is_open(monkeypatch, tmp_path: Path) -> None:
    module = _ahmad_overlay_module()

    class Root:
        def __init__(self) -> None:
            self.destroyed = False
            self.after_calls: list[tuple[int, object]] = []

        def destroy(self) -> None:
            self.destroyed = True

        def after(self, interval: int, callback: object) -> None:
            self.after_calls.append((interval, callback))

    snapshot_path = tmp_path / "latest_snapshot.json"
    snapshot_path.write_text('{"file": "snapshot"}', encoding="utf-8")
    render_calls: list[dict] = []
    standby_calls: list[dict] = []
    missing_calls: list[str] = []

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = Root()
    overlay.interval_ms = 1000
    overlay.exit_when_pids = ()
    overlay._exit_cleanup_done = False
    overlay._last_ui_heartbeat_at = time.monotonic()
    overlay._last_ui_stall_bucket = 0
    overlay.snapshot_path = snapshot_path
    overlay.diagnostic_profile = "portable"
    overlay._last_signature = (0, 0)
    overlay._last_capture_status_signature = None
    overlay._last_summary = {
        "status": "ok",
        "context": {"phase": "bidding", "session_id": "2404:old"},
    }
    overlay._last_live_summary = {
        "status": "ok",
        "context": {"phase": "bidding", "session_id": "2404:old"},
    }
    overlay._manual_active = False
    overlay._manual_edit_enabled = True
    overlay._manual_settlement_edit_unlocked = False
    overlay._manual_snapshot = {}
    overlay._manual_summary = {}
    overlay._manual_dirty_fields = set()
    overlay._manual_autofill_values = {}
    overlay._manual_programmatic_update = False
    overlay._manual_live_session_id = ""
    overlay.render = lambda data: render_calls.append(data)
    overlay.render_standby = lambda data: standby_calls.append(data)
    overlay.render_missing = lambda message: missing_calls.append(message)
    overlay._set_manual_settlement_button_state = lambda: None

    monkeypatch.setattr(module, "_watched_pid_exited", lambda _pids: False)
    monkeypatch.setattr(
        module,
        "summarize_snapshot",
        lambda snapshot, snapshot_path: {
            "status": "ok",
            "updated_at_text": "12:34:56",
            "context": {"phase": "bidding", "session_id": "2404:new"},
            "reference": {},
            "evidence": {},
            "red": {},
            "ahmed_ref": {"evidence": {}},
            "diagnostics": {"rare_signals": {}},
            "minimap": {},
            "truth": {"available": False},
        },
    )

    module.AhmadTkOverlay.refresh(overlay)

    assert render_calls == []
    assert standby_calls == []
    assert missing_calls == []
    assert overlay._last_live_summary["context"]["session_id"] == "2404:new"
    assert overlay._last_summary["context"]["session_id"] == "2404:old"
    assert overlay.root.after_calls == [(1000, overlay.refresh)]


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
    overlay.snapshot_path = tmp_path / "latest_snapshot.json"
    overlay._stop_pids_on_exit = (123,)
    overlay._cleanup_lock_paths = (lock_path,)
    overlay.keep_monitor_on_close = False
    overlay._exit_cleanup_done = False
    overlay._hide_minimap_popup = lambda: None
    overlay._hide_pinned_minimap = lambda: None
    overlay.root = SimpleNamespace(destroy=lambda: destroyed.append(True))

    module.AhmadTkOverlay._on_user_close(overlay)
    module.AhmadTkOverlay._run_exit_cleanup(overlay)

    assert cleanup_calls == [((123,), (lock_path,))]
    assert destroyed == [True]


def test_ahmad_cleanup_exit_targets_terminates_unique_pids_and_removes_locks(
    tmp_path: Path,
) -> None:
    module = _ahmad_overlay_module()
    lock_path = tmp_path / "monitor.lock"
    lock_path.write_text('{"pid": 123}', encoding="utf-8")
    terminated: list[int] = []

    module._cleanup_exit_targets(
        [123, 123, 456],
        [lock_path],
        terminate_fn=terminated.append,
    )

    assert terminated == [123, 456]
    assert not lock_path.exists()


def test_ahmad_run_exit_cleanup_falls_back_to_monitor_lock(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _ahmad_overlay_module()
    snapshot_path = tmp_path / "latest_snapshot.json"
    snapshot_path.write_text("{}", encoding="utf-8")
    lock_path = snapshot_path.parent / "monitor.lock"
    lock_path.write_text('{"pid": 4321}', encoding="utf-8")
    cleanup_calls: list[tuple[tuple[int, ...], tuple[Path, ...]]] = []
    monkeypatch.setattr(
        module,
        "_cleanup_exit_targets",
        lambda pids, lock_paths, **kwargs: cleanup_calls.append(
            (tuple(pids), tuple(lock_paths))
        ),
    )

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.snapshot_path = snapshot_path
    overlay._stop_pids_on_exit = ()
    overlay._cleanup_lock_paths = ()
    overlay.keep_monitor_on_close = False
    overlay._exit_cleanup_done = False

    module.AhmadTkOverlay._run_exit_cleanup(overlay)

    assert cleanup_calls == [((4321,), (lock_path,))]


def test_ahmad_run_exit_cleanup_skips_when_keep_monitor_on_close(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _ahmad_overlay_module()
    snapshot_path = tmp_path / "latest_snapshot.json"
    snapshot_path.write_text("{}", encoding="utf-8")
    lock_path = snapshot_path.parent / "monitor.lock"
    lock_path.write_text('{"pid": 4321}', encoding="utf-8")
    cleanup_calls: list[tuple[tuple[int, ...], tuple[Path, ...]]] = []
    monkeypatch.setattr(
        module,
        "_cleanup_exit_targets",
        lambda pids, lock_paths, **kwargs: cleanup_calls.append(
            (tuple(pids), tuple(lock_paths))
        ),
    )

    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.snapshot_path = snapshot_path
    overlay._stop_pids_on_exit = ()
    overlay._cleanup_lock_paths = ()
    overlay.keep_monitor_on_close = True
    overlay._exit_cleanup_done = False

    module.AhmadTkOverlay._run_exit_cleanup(overlay)

    assert cleanup_calls == []
    assert lock_path.exists()


def test_ahmad_refresh_runs_exit_cleanup_on_watched_pid_exit(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _ahmad_overlay_module()
    cleanup_calls: list[bool] = []

    class Root:
        def __init__(self) -> None:
            self.destroyed = False
            self.after_calls: list[tuple[int, object]] = []

        def destroy(self) -> None:
            self.destroyed = True

        def after(self, interval: int, callback: object) -> None:
            self.after_calls.append((interval, callback))

    monkeypatch.setattr(module, "_watched_pid_exited", lambda _pids: True)
    overlay = object.__new__(module.AhmadTkOverlay)
    overlay.root = Root()
    overlay.interval_ms = 1000
    overlay.exit_when_pids = (123,)
    overlay._exit_cleanup_done = False
    overlay.keep_monitor_on_close = False
    overlay._stop_pids_on_exit = ()
    overlay._cleanup_lock_paths = ()
    overlay.snapshot_path = tmp_path / "latest_snapshot.json"
    overlay.diagnostic_profile = "portable"
    overlay._last_ui_heartbeat_at = time.monotonic()
    overlay._last_ui_stall_bucket = 0
    overlay._run_exit_cleanup = lambda: cleanup_calls.append(True)

    module.AhmadTkOverlay.refresh(overlay)

    assert cleanup_calls == [True]
    assert overlay.root.destroyed is True
