from __future__ import annotations

import argparse
import copy
import colorsys
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import queue
import random
import re
import signal
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Any
import webbrowser
import zipfile


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
LAB_ROOT = TOOLS_DIR.parents[0]
LAB_SRC = LAB_ROOT / "src"
if str(LAB_SRC) not in sys.path:
    sys.path.insert(0, str(LAB_SRC))

from ahmad_live_panel_server import (  # noqa: E402
    SETTLED_STALE_SECONDS,
    STALE_SNAPSHOT_SECONDS,
    _aisha_d1_flag_detail,
    _aisha_defense_multiplier_hint,
    _candidate_summary,
    _display_range_text,
    _next_info_hint,
    _parse_int,
    _quality_uncertainty_summary,
    _red_display_ranges,
    _red_range_text,
    summarize_snapshot,
)

try:
    from ahmad_ref_engine import (  # noqa: E402
        HERO_ALIASES,
        SUPPORTED_REF_HERO_KEYS,
        can_compose_grid_total,
        is_supported_ref_hero,
        load_reference_static_data,
        normalize_hero_key,
        prepare_reference_engine_snapshot,
        run_reference_engine,
    )
except Exception:  # noqa: BLE001 - keep overlay usable if ref core is unavailable
    HERO_ALIASES = {
        "aisha": "aisha",
        "艾莎": "aisha",
        "ahmad": "ahmed",
        "ahmed": "ahmed",
        "ahamed": "ahmed",
        "艾哈": "ahmed",
        "艾哈迈德": "ahmed",
        "victor": "victor",
        "维克": "victor",
        "维克托": "victor",
    }
    SUPPORTED_REF_HERO_KEYS = frozenset({"aisha", "ahmed", "victor"})

    def normalize_hero_key(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        return HERO_ALIASES.get(text.lower(), HERO_ALIASES.get(text, text.lower()))

    def is_supported_ref_hero(value: Any) -> bool:
        return normalize_hero_key(value) in SUPPORTED_REF_HERO_KEYS

    can_compose_grid_total = None  # type: ignore[assignment]
    load_reference_static_data = None  # type: ignore[assignment]
    run_reference_engine = None  # type: ignore[assignment]

    def prepare_reference_engine_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SNAPSHOT = ROOT / "data" / "logs" / "live" / "latest_snapshot.json"
CREDIT_TEXT = "作者: 加菲_Barista · 协作: lemyes"
CREDIT_GITHUB_URL = "https://github.com/SeasonCake/bidking-lab"
GITHUB_TIP_TEXT = "如果觉得不错，就给一个免费的 Star 吧！"
DETAIL_TIP_TEXT = "展开 / 收起详情、小地图和手动填写区"
MANUAL_TIP_TEXT = "手动填写；断网或识别缺项时补总件、均格、件数、均价/总价；编辑时自动抓取不会覆盖当前输入"
MANUAL_RETURN_TIP_TEXT = "返回实时；手填内容保留，live 继续监测并可补齐空字段"
MANUAL_CLEAR_SETTLEMENT_TIP = "结算页手填时清掉自动带入的结算数字，保留英雄/地图；不删除 live 日志"
MANUAL_CLEAR_SETTLEMENT_INACTIVE_TIP = "只在当前停留结算页并进入手填时启用"
THEME_TIP_PREFIX = "切换配色"
SETTLEMENT_HIDE_TIP = "预设隐藏结算金额，想自己看结算时用；结算出现后生效，只影响界面，不影响计算"
SETTLEMENT_SHOW_TIP = "显示结算金额；关闭预设隐藏，只影响界面，不影响计算"
SETTLEMENT_INACTIVE_TIP = SETTLEMENT_HIDE_TIP
CLOSE_TIP_TEXT = "关闭 Hero Ref；若由启动脚本打开，会联动清理监控进程"
RESIZE_TIP_TEXT = "拖动缩放（实时）；横/竖拖都会放大，高度自动贴合内容"
SUMMARY_DIAGNOSTIC_LOG = "hero_ref_ui_summary.jsonl"
UI_HEALTH_LOG = "hero_ref_ui_health.jsonl"
UI_RUNTIME_STATUS = "hero_ref_ui_runtime_status.json"
UI_PREFS_FILENAME = "hero_ref_ui_prefs.json"
UI_PREFS_SCHEMA_VERSION = 1
UI_PREFS_SAVE_DEBOUNCE_MS = 400
UI_SCALE_LIVE_INTERVAL_MS = 48
UI_SCALE_LIVE_DELTA = 0.025
UI_STALL_SECONDS = 5.0
UI_STALL_LOG_INTERVAL_SECONDS = 5.0
UI_RUNTIME_STATUS_REPEAT_INTERVAL_SECONDS = 10.0
DIAGNOSTIC_PROFILES = ("engineering", "portable", "public-safe")
DIAGNOSTIC_PROFILE_ALIASES = {
    "engineering": "engineering",
    "portable": "portable",
    "stable": "portable",
    "public-safe": "public-safe",
    "public_safe": "public-safe",
}
DEFAULT_DIAGNOSTIC_PROFILE = "engineering"
TOPMOST_ON_TIP = "置顶中；点击切换为自由窗口"
TOPMOST_OFF_TIP = "自由窗口；点击恢复置顶"
MINIMAP_PINNED_FREE_SUFFIX = " · 自由"
MINIMAP_PINNED_DRAG_TIP = "拖动标题栏可自由移动；默认跟随主面板"
EXPORT_DIAGNOSTIC_TIP_TEMPLATE = "异常/卡住/结算不对时点这里；生成诊断 zip 到 {path}，把 zip 发群里作为 log 排查，避免反复发生"
REQUIRED_RAW_TABLES = ("BidMap.txt", "Drop.txt", "Item.txt")

FONT_UI = "Microsoft YaHei UI"
FONT_NUMERIC = "Segoe UI Semibold"
UI_SCALE_MIN = 0.85
UI_SCALE_MAX = 1.6
MINI_BASE_WIDTH = 440
MINI_BASE_HEIGHT = 397
MINI_WINDOW_CHROME_HEIGHT = 18
DETAILS_BASE_WIDTH = 700
DETAILS_BASE_HEIGHT = 700
HERO_BUTTON_PADDING_BASE = (8, 4)
HERO_BUTTON_FONT_SIZE = 8
MINIMAP_CELL_HINT_BASE = 13.0
MINIMAP_POPUP_CELL_HINT_BASE = 24.0
MINIMAP_DEFAULT_COLUMNS = 10
MINIMAP_DEFAULT_ROWS = 13


def canvas_draw_size(
    canvas: tk.Canvas,
    *,
    min_width: int,
    min_height: int,
) -> tuple[int, int]:
    """Use the canvas widget's laid-out size, not stale creation defaults."""
    try:
        canvas.update_idletasks()
    except tk.TclError:
        pass
    width = int(canvas.winfo_width() or 0)
    height = int(canvas.winfo_height() or 0)
    if width <= 1:
        width = int(min_width)
    if height <= 1:
        height = int(min_height)
    return max(int(min_width), width), max(int(min_height), height)

MANUAL_BASE_FIELDS = (
    ("hero", "英雄", ""),
    ("map_id", "地图", ""),
    ("total_count", "总件", ""),
    ("total_cells", "总格", ""),
    ("total_avg", "全均格", ""),
)
MANUAL_QUALITY_ROWS = (
    ("白", "white_avg", "white_count", "white_cells"),
    ("绿", "green_avg", "green_count", "green_cells"),
    ("白绿", "q1_avg", "q1_count", "q1_cells"),
    ("蓝", "q3_avg", "q3_count", "q3_cells"),
    ("紫", "q4_avg", "q4_count", "q4_cells"),
    ("金", "q5_avg", "q5_count", "q5_cells"),
    ("红", "q6_avg", "q6_count", "q6_cells"),
)
MANUAL_VALUE_ROWS = (
    ("白", "white_avg_value", "white_value_sum"),
    ("绿", "green_avg_value", "green_value_sum"),
    ("白绿", "q1_avg_value", "q1_value_sum"),
    ("蓝", "q3_avg_value", "q3_value_sum"),
    ("紫", "q4_avg_value", "q4_value_sum"),
    ("金", "q5_avg_value", "q5_value_sum"),
    ("红", "q6_avg_value", "q6_value_sum"),
)
MANUAL_EXTRA_FIELDS = (
    ("q4q5_count", "紫金红件", ""),
)
QUALITY_LABELS = {
    "q1": "白绿",
    "q3": "蓝",
    "q4": "紫",
    "q5": "金",
    "q6": "红",
}
QUALITY_INPUT_KEYS = ("q1", "q3", "q4", "q5", "q6")
SPLIT_QUALITY_LABELS = {
    "white": "白",
    "green": "绿",
}
SPLIT_QUALITY_INPUT_KEYS = ("white", "green")
def compute_ui_scale(
    width: int,
    height: int,
    *,
    base_width: int,
    base_height: int,
    min_scale: float = UI_SCALE_MIN,
    max_scale: float = UI_SCALE_MAX,
) -> float:
    """Scale mini UI typography from window size relative to a mode baseline."""
    safe_w = max(1, int(base_width))
    safe_h = max(1, int(base_height))
    ratio = min(int(width) / safe_w, int(height) / safe_h)
    return max(float(min_scale), min(float(max_scale), float(ratio)))


def scaled_font(
    family: str,
    size: int,
    *styles: str,
    scale: float = 1.0,
) -> tuple[Any, ...]:
    scaled_size = max(6, int(round(int(size) * float(scale))))
    if styles:
        return (family, scaled_size, *styles)
    return (family, scaled_size)


def font_spec_from_widget(widget: tk.Widget) -> tuple[Any, ...] | None:
    try:
        actual = tkfont.Font(font=widget.cget("font")).actual()
    except tk.TclError:
        return None
    family = str(actual.get("family") or FONT_UI)
    size = int(float(actual.get("size") or 0))
    if size <= 0:
        return None
    styles: list[str] = []
    if str(actual.get("weight") or "") == "bold":
        styles.append("bold")
    if str(actual.get("slant") or "") == "italic":
        styles.append("italic")
    if str(actual.get("underline") or "") == "1":
        styles.append("underline")
    return (family, size, *styles)


def compute_fitted_mini_height(
    shell_reqheight: int,
    *,
    chrome: int = MINI_WINDOW_CHROME_HEIGHT,
    min_height: int = 320,
    max_height: int = 1500,
) -> int:
    return max(min_height, min(max_height, int(shell_reqheight) + int(chrome)))


def compute_mini_ui_scale(
    width: int,
    *,
    base_width: int = MINI_BASE_WIDTH,
    min_scale: float = UI_SCALE_MIN,
    max_scale: float = UI_SCALE_MAX,
) -> float:
    """Mini overlay scale follows width; height is auto-fitted to content."""
    ratio = int(width) / max(1, int(base_width))
    return max(float(min_scale), min(float(max_scale), float(ratio)))


def mini_resize_growth(dx: int, dy: int) -> int:
    """Corner grip growth: enlarge on positive deltas, shrink on negative."""
    if dx >= 0 and dy >= 0:
        return max(dx, dy)
    if dx <= 0 and dy <= 0:
        return min(dx, dy)
    return dx if abs(dx) >= abs(dy) else dy


def ui_prefs_path_for_snapshot(snapshot_path: Path) -> Path:
    return Path(snapshot_path).parent / UI_PREFS_FILENAME


def _clamp_ui_pref_size(width: int, height: int) -> tuple[int, int]:
    return (
        max(430, min(1200, int(width))),
        max(320, min(1500, int(height))),
    )


def normalize_ui_prefs_payload(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    theme_name = raw.get("theme_name")
    if theme_name is not None and not isinstance(theme_name, str):
        return None
    normalized: dict[str, Any] = {
        "schema_version": UI_PREFS_SCHEMA_VERSION,
        "theme_name": str(theme_name or "dark"),
        "details_expanded": bool(raw.get("details_expanded")),
        "ui_scale": float(raw.get("ui_scale") or 1.0),
    }
    position = raw.get("window_position")
    if isinstance(position, (list, tuple)) and len(position) == 2:
        try:
            normalized["window_position"] = [
                int(position[0]),
                int(position[1]),
            ]
        except (TypeError, ValueError):
            pass
    for key in ("custom_mini_size", "custom_details_size"):
        value = raw.get(key)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            try:
                normalized[key] = list(_clamp_ui_pref_size(int(value[0]), int(value[1])))
            except (TypeError, ValueError):
                continue
        elif value is None:
            normalized[key] = None
    return normalized


def read_ui_prefs(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return normalize_ui_prefs_payload(payload)


def write_ui_prefs(path: Path, payload: dict[str, Any]) -> None:
    normalized = normalize_ui_prefs_payload(payload)
    if normalized is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


MANUAL_GENERIC_MAP_ALIASES = {
    "快递": 2101,
    "仓库": 2201,
    "集装箱": 2301,
    "箱子": 2301,
    "别墅": 2401,
    "残骸": 2501,
    "沉船": 2501,
    "船": 2501,
    "隐秘拍卖": 2601,
    "隐秘拍卖会": 2601,
    "拍卖会": 2601,
}
AUTO_REPLACE_MANUAL_FIELDS = {
    "hero",
    "map_id",
    "total_count",
    "total_cells",
    "total_avg",
    "q4q5_count",
}
MAINLINE_QUALITY_STYLE = {
    "q1": {"fill": "#cbd5e1", "outline": "#94a3b8", "unknown": False},
    "q2": {"fill": "#86efac", "outline": "#bbf7d0", "unknown": False},
    "q3": {"fill": "#60a5fa", "outline": "#bfdbfe", "unknown": False},
    "q4": {"fill": "#c084fc", "outline": "#e9d5ff", "unknown": False},
    "q5": {"fill": "#fbbf24", "outline": "#d97706", "unknown": False},
    "q6": {"fill": "#fb7185", "outline": "#e11d48", "unknown": False},
    "treasure": {"fill": "#fbbf24", "outline": "#d97706", "unknown": False},
    "unknown": {"fill": "#4a5d78", "outline": "#94a3b8", "unknown": True},
}

THEME_ORDER = ("blue", "dark", "light", "random")
THEMES: dict[str, dict[str, Any]] = {
    "blue": {
        "label": "蓝色",
        "BG": "#243b63",
        "PANEL": "#2d456d",
        "PANEL_SOFT": "#3d6090",
        "PANEL_MUTED": "#34446c",
        "BORDER": "#6f91c2",
        "TEXT": "#f7fbff",
        "MUTED": "#cbd9ee",
        "DIM": "#93a8c5",
        "GOOD": "#67e6bc",
        "WARN": "#ffd166",
        "BAD": "#ff6f91",
        "ACCENT": "#7ad7ff",
        "WARM": "#ffb86b",
        "MINIMAP_BG": "#1f3152",
        "MINIMAP_GRID": "#496b9a",
        "MINIMAP_TEXT": "#bdd1e8",
        "QUALITY_COLORS": {
            "q1": "#8d94a7",
            "q2": "#d8dce4",
            "q3": "#5bbff0",
            "q4": "#b894f6",
            "q5": "#ffd45a",
            "q6": "#ff747c",
            "unknown": "#455a78",
        },
        "HERO_BUTTON_ACTIVE": "#4e73a6",
        "SCROLL_LINE": "#5878a8",
        "TOOLTIP_BG": "#203659",
        "MANUAL_BG": "#30456d",
        "MANUAL_INPUT_BG": "#203659",
        "MANUAL_STATUS_BG": "#4b3a2a",
        "MANUAL_LABEL_FG": "#dfe9f8",
        "MINIMAP_ITEM_SHADOW": "#172641",
        "MINIMAP_ITEM_OUTLINE": "#172641",
        "BUTTON_DARK_FG": "#251f2b",
    },
    "dark": {
        "label": "暗色",
        "BG": "#141923",
        "PANEL": "#202838",
        "PANEL_SOFT": "#2b3548",
        "PANEL_MUTED": "#28283a",
        "BORDER": "#46536a",
        "TEXT": "#f4f7fb",
        "MUTED": "#bbc6d5",
        "DIM": "#8794aa",
        "GOOD": "#5fd39d",
        "WARN": "#f1c85f",
        "BAD": "#ef718f",
        "ACCENT": "#6bbde8",
        "WARM": "#f4b66a",
        "MINIMAP_BG": "#121927",
        "MINIMAP_GRID": "#2b3446",
        "MINIMAP_TEXT": "#aab6c9",
        "QUALITY_COLORS": {
            key: value["fill"] for key, value in MAINLINE_QUALITY_STYLE.items()
        },
        "HERO_BUTTON_ACTIVE": "#36445d",
        "SCROLL_LINE": "#3a465c",
        "TOOLTIP_BG": "#171d2a",
        "MANUAL_BG": "#28253d",
        "MANUAL_INPUT_BG": "#192132",
        "MANUAL_STATUS_BG": "#403326",
        "MANUAL_LABEL_FG": "#dce5f1",
        "MINIMAP_ITEM_SHADOW": "#0f1623",
        "MINIMAP_ITEM_OUTLINE": "#0f1623",
        "BUTTON_DARK_FG": "#251f2b",
    },
    "light": {
        "label": "亮色",
        "BG": "#eef5fb",
        "PANEL": "#ffffff",
        "PANEL_SOFT": "#dcebf9",
        "PANEL_MUTED": "#f6f1fb",
        "BORDER": "#95accb",
        "TEXT": "#17233a",
        "MUTED": "#425472",
        "DIM": "#7182a0",
        "GOOD": "#0f9f75",
        "WARN": "#b97900",
        "BAD": "#d83b66",
        "ACCENT": "#1677b7",
        "WARM": "#f2a642",
        "MINIMAP_BG": "#e7f0fa",
        "MINIMAP_GRID": "#bfd2e7",
        "MINIMAP_TEXT": "#586d89",
        "QUALITY_COLORS": {
            "q1": "#8f98a6",
            "q2": "#d4dae2",
            "q3": "#42aee2",
            "q4": "#a97fed",
            "q5": "#efbb35",
            "q6": "#ef5f6c",
            "unknown": "#bcc9d8",
        },
        "HERO_BUTTON_ACTIVE": "#c7def5",
        "SCROLL_LINE": "#aac2dd",
        "TOOLTIP_BG": "#ffffff",
        "MANUAL_BG": "#fff4e4",
        "MANUAL_INPUT_BG": "#edf4fb",
        "MANUAL_STATUS_BG": "#ffe5b8",
        "MANUAL_LABEL_FG": "#324460",
        "MINIMAP_ITEM_SHADOW": "#c5d1de",
        "MINIMAP_ITEM_OUTLINE": "#edf4fb",
        "BUTTON_DARK_FG": "#251f2b",
    },
}


def _hsl_color(hue: float, saturation: float, lightness: float) -> str:
    red, green, blue = colorsys.hls_to_rgb(hue % 1.0, lightness, saturation)
    return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"


def _random_theme() -> dict[str, Any]:
    hue = random.random()
    return {
        "label": "随机",
        "BG": _hsl_color(hue, 0.38, 0.25),
        "PANEL": _hsl_color(hue, 0.34, 0.33),
        "PANEL_SOFT": _hsl_color(hue, 0.38, 0.43),
        "PANEL_MUTED": _hsl_color(hue + 0.06, 0.30, 0.34),
        "BORDER": _hsl_color(hue, 0.28, 0.61),
        "TEXT": "#fbf8f2",
        "MUTED": _hsl_color(hue, 0.30, 0.80),
        "DIM": _hsl_color(hue, 0.25, 0.66),
        "GOOD": "#67e6bc",
        "WARN": "#ffd166",
        "BAD": "#ff6f91",
        "ACCENT": _hsl_color(hue + 0.43, 0.75, 0.70),
        "WARM": _hsl_color(hue + 0.11, 0.85, 0.70),
        "MINIMAP_BG": _hsl_color(hue, 0.42, 0.20),
        "MINIMAP_GRID": _hsl_color(hue, 0.32, 0.43),
        "MINIMAP_TEXT": _hsl_color(hue, 0.28, 0.78),
        "QUALITY_COLORS": THEMES["blue"]["QUALITY_COLORS"],
        "HERO_BUTTON_ACTIVE": _hsl_color(hue, 0.40, 0.48),
        "SCROLL_LINE": _hsl_color(hue, 0.30, 0.50),
        "TOOLTIP_BG": _hsl_color(hue, 0.42, 0.21),
        "MANUAL_BG": _hsl_color(hue + 0.08, 0.32, 0.32),
        "MANUAL_INPUT_BG": _hsl_color(hue, 0.40, 0.22),
        "MANUAL_STATUS_BG": "#4b3a2a",
        "MANUAL_LABEL_FG": _hsl_color(hue, 0.28, 0.84),
        "MINIMAP_ITEM_SHADOW": _hsl_color(hue, 0.45, 0.16),
        "MINIMAP_ITEM_OUTLINE": _hsl_color(hue, 0.45, 0.16),
        "BUTTON_DARK_FG": "#251f2b",
    }


def _theme_by_name(name: str) -> dict[str, Any]:
    if name == "random":
        return _random_theme()
    return THEMES.get(name, THEMES["dark"])


def _apply_theme_globals(theme: dict[str, Any]) -> None:
    globals_to_update = {
        key: value
        for key, value in theme.items()
        if key.isupper() and key != "QUALITY_COLORS"
    }
    globals().update(globals_to_update)
    globals()["QUALITY_COLORS"] = dict(theme["QUALITY_COLORS"])


_apply_theme_globals(THEMES["dark"])


def _flat_theme_colors(theme: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in theme.items():
        if isinstance(value, str) and value.startswith("#"):
            out[key] = value.lower()
    quality = theme.get("QUALITY_COLORS")
    if isinstance(quality, dict):
        for key, value in quality.items():
            if isinstance(value, str) and value.startswith("#"):
                out[f"QUALITY_{key}"] = value.lower()
    return out


def _theme_replacements(old_theme: dict[str, Any], new_theme: dict[str, Any]) -> dict[str, str]:
    old_flat = _flat_theme_colors(old_theme)
    new_flat = _flat_theme_colors(new_theme)
    replacements: dict[str, str] = {}
    for key, old_value in old_flat.items():
        new_value = new_flat.get(key)
        if new_value and new_value != old_value:
            replacements[old_value] = new_value
    return replacements


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _text(value: Any, fallback: str = "-") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _normalize_diagnostic_profile(value: Any) -> str:
    profile = str(value or DEFAULT_DIAGNOSTIC_PROFILE).strip().lower()
    normalized = DIAGNOSTIC_PROFILE_ALIASES.get(profile)
    if normalized not in DIAGNOSTIC_PROFILES:
        return DEFAULT_DIAGNOSTIC_PROFILE
    return normalized


def _parse_diagnostic_profile(value: str) -> str:
    profile = str(value or "").strip().lower()
    if profile not in DIAGNOSTIC_PROFILE_ALIASES:
        raise argparse.ArgumentTypeError(
            "expected one of: engineering, portable, public-safe"
        )
    return _normalize_diagnostic_profile(profile)


def _apply_taskbar_mode(root: tk.Tk, *, show_taskbar: bool) -> None:
    root.overrideredirect(not show_taskbar)


def _apply_windows_toolwindow(widget: tk.Misc, *, enabled: bool) -> None:
    if not enabled or os.name != "nt":
        return
    try:
        widget.attributes("-toolwindow", True)
    except tk.TclError:
        pass


def _hex_to_rgb(color: str) -> tuple[int, int, int] | None:
    text = str(color or "").strip()
    if not text.startswith("#") or len(text) != 7:
        return None
    try:
        red = int(text[1:3], 16)
        green = int(text[3:5], 16)
        blue = int(text[5:7], 16)
    except ValueError:
        return None
    return red, green, blue


def _blend_hex(color: str, other: str, ratio: float) -> str:
    left = _hex_to_rgb(color)
    right = _hex_to_rgb(other)
    if left is None or right is None:
        return color
    ratio = max(0.0, min(1.0, ratio))
    mixed = tuple(
        int(round(a * (1.0 - ratio) + b * ratio))
        for a, b in zip(left, right)
    )
    return f"#{mixed[0]:02x}{mixed[1]:02x}{mixed[2]:02x}"


def _short(value: Any, limit: int = 36) -> str:
    text = _text(value, "")
    if len(text) <= limit:
        return text or "-"
    return f"{text[: limit - 1]}..."


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _compact_flags(flags: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(flags, list):
        return out
    for flag in flags[:8]:
        if not isinstance(flag, dict):
            continue
        out.append(
            {
                "label": _text(flag.get("label"), ""),
                "level": _text(flag.get("level"), ""),
                "detail": _text(flag.get("detail"), ""),
            }
        )
    return out


def _summary_diagnostic_row(
    data: dict[str, Any],
    *,
    snapshot_path: Path,
    render_mode: str,
    manual_active: bool,
    settlement_values_hidden: bool,
) -> dict[str, Any]:
    context = _mapping(data.get("context"))
    reference = _mapping(data.get("reference"))
    red = _mapping(data.get("red"))
    evidence = _mapping(data.get("evidence"))
    ahmed_ref = _mapping(data.get("ahmed_ref"))
    ref_evidence = _mapping(ahmed_ref.get("evidence"))
    diagnostics = _mapping(data.get("diagnostics"))
    rare_signals = _mapping(diagnostics.get("rare_signals"))
    performance = _mapping(diagnostics.get("performance"))
    minimap = _mapping(data.get("minimap"))
    truth = _mapping(data.get("truth"))
    truth_q6 = _mapping(truth.get("q6"))
    stale = _mapping(data.get("stale"))
    latest_result = evidence.get("latest_result")
    if not isinstance(latest_result, dict):
        latest_result = evidence.get("latest_sent")
    if not isinstance(latest_result, dict):
        latest_result = {}
    return {
        "logged_at": time.time(),
        "snapshot_path": str(snapshot_path),
        "status": _text(data.get("status"), "ok"),
        "render_mode": render_mode,
        "manual_active": bool(manual_active),
        "settlement_values_hidden": bool(settlement_values_hidden),
        "updated_at_text": _text(data.get("updated_at_text"), ""),
        "stale_reason": _text(stale.get("reason"), ""),
        "snapshot_age_seconds": stale.get("age_seconds"),
        "context": {
            "hero": context.get("hero"),
            "map_id": context.get("map_id"),
            "round": context.get("round"),
            "phase": context.get("phase"),
            "session_id": context.get("session_id"),
        },
        "reference": {
            "source": reference.get("source"),
            "readiness": reference.get("readiness"),
            "action": reference.get("action"),
            "current_highest": reference.get("current_highest"),
            "conservative": reference.get("conservative"),
            "balanced": reference.get("balanced"),
            "aggressive": reference.get("aggressive"),
            "decision_range": reference.get("decision_range"),
            "total_grid_range": reference.get("total_grid_range"),
            "total_value_range": reference.get("total_value_range"),
            "v3_balanced": reference.get("v3_balanced"),
            "ref_minus_v3_balanced": reference.get("ref_minus_v3_balanced"),
            "note": reference.get("note"),
        },
        "red": {
            "count_range": red.get("count_range"),
            "cells_range": red.get("cells_range"),
            "value_range": red.get("value_range"),
            "quality_count_summary": red.get("quality_count_summary"),
            "uncertainty_summary": red.get("uncertainty_summary"),
            "risk_reference": red.get("risk_reference"),
        },
        "evidence": {
            "match_text": evidence.get("match_text"),
            "information_density": evidence.get("information_density"),
            "ref_input_summary": evidence.get("ref_input_summary"),
            "candidate_summary": evidence.get("candidate_summary"),
            "next_info_hint": evidence.get("next_info_hint"),
            "public_numeric_summary": evidence.get("public_numeric_summary"),
            "minimap_quality_summary": evidence.get("minimap_quality_summary"),
            "ref_combo_count": evidence.get("ref_combo_count"),
            "diagnostics": evidence.get("diagnostics"),
            "ref_notes": evidence.get("ref_notes"),
            "latest_result": latest_result,
            "manual_overlay": bool(evidence.get("manual_overlay")),
        },
        "ref_v0": {
            "status": ahmed_ref.get("status"),
            "source": ahmed_ref.get("source"),
            "notes": ahmed_ref.get("notes"),
            "combo_count": ahmed_ref.get("combo_count"),
            "quality_count_ranges": ahmed_ref.get("quality_count_ranges"),
            "total_grid_range": ahmed_ref.get("total_grid_range"),
            "value_range": {
                "p25": ahmed_ref.get("value_p25"),
                "p50": ahmed_ref.get("value_p50"),
                "p75": ahmed_ref.get("value_p75"),
            },
            "evidence": {
                "source_notes": ref_evidence.get("source_notes"),
                "total_count": ref_evidence.get("total_count"),
                "total_grid_target": ref_evidence.get("total_grid_target"),
                "fixed_counts": ref_evidence.get("fixed_counts"),
                "min_counts": ref_evidence.get("min_counts"),
                "avg_cells": ref_evidence.get("avg_cells"),
                "quality_cells": ref_evidence.get("quality_cells"),
                "avg_values": ref_evidence.get("avg_values"),
                "quality_values": ref_evidence.get("quality_values"),
            },
        },
        "minimap": {
            "summary_text": minimap.get("summary_text"),
            "quality_counts": minimap.get("quality_counts"),
            "items_count": len(minimap.get("items") or ()),
            "source": minimap.get("source"),
        },
        "truth": {
            "available": bool(truth.get("available")),
            "total_value": truth.get("total_value"),
            "total_items": truth.get("total_items"),
            "total_cells": truth.get("total_cells"),
            "q6": {
                "count": truth_q6.get("count"),
                "cells": truth_q6.get("cells"),
                "value": truth_q6.get("value"),
            },
        },
        "diagnostics": {
            "rare_signals": {
                "present": bool(rare_signals.get("present")),
                "summary": rare_signals.get("summary"),
                "role_counts": rare_signals.get("role_counts"),
                "actions": rare_signals.get("actions"),
                "public_info": rare_signals.get("public_info"),
            },
            "performance": {
                "summary_total_ms": performance.get("summary_total_ms"),
                "ref_engine_ms": performance.get("ref_engine_ms"),
                "settlement_ref_engine_ms": performance.get("settlement_ref_engine_ms"),
                "refresh_total_ms": performance.get("refresh_total_ms"),
                "export_ms": performance.get("export_ms"),
            },
        },
        "flags": _compact_flags(data.get("flags")),
    }


def _summary_diagnostic_signature(row: dict[str, Any]) -> str:
    stable = {
        key: value
        for key, value in row.items()
        if key not in {"logged_at", "snapshot_age_seconds", "updated_at_text"}
    }
    diagnostics = stable.get("diagnostics")
    if isinstance(diagnostics, dict):
        diagnostics = dict(diagnostics)
        diagnostics.pop("performance", None)
        stable["diagnostics"] = diagnostics
    return json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _diagnostic_export_dir(snapshot_path: Path) -> Path:
    return snapshot_path.parent / "exports"


def _diagnostic_export_tip(snapshot_path: Path) -> str:
    return EXPORT_DIAGNOSTIC_TIP_TEMPLATE.format(
        path=str(_diagnostic_export_dir(snapshot_path).resolve())
    )


def _candidate_package_roots(snapshot_path: Path) -> list[Path]:
    resolved = snapshot_path.resolve()
    roots = [resolved.parent]
    for parent in resolved.parents:
        if parent.name == "data":
            roots.append(parent.parent)
    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        try:
            resolved_root = str(root.resolve())
        except OSError:
            resolved_root = str(root)
        if resolved_root in seen:
            continue
        seen.add(resolved_root)
        out.append(root)
    return out


def _raw_tables_summary(snapshot_path: Path) -> dict[str, Any]:
    fallback: dict[str, Any] | None = None
    for root in _candidate_package_roots(snapshot_path):
        raw_dir = root / "data" / "raw" / "tables"
        files: list[dict[str, Any]] = []
        missing: list[str] = []
        for name in REQUIRED_RAW_TABLES:
            path = raw_dir / name
            if path.is_file():
                files.append(_diagnostic_file_summary(path))
            else:
                missing.append(name)
        summary = {
            "package_root": str(root.resolve()),
            "path": str(raw_dir.resolve()) if raw_dir.exists() else str(raw_dir),
            "present": raw_dir.is_dir(),
            "required_present": not missing,
            "files": files,
            "missing_required": missing,
        }
        if summary["present"] or summary["required_present"]:
            return summary
        if fallback is None:
            fallback = summary
    return fallback or {
        "package_root": str(snapshot_path.parent.resolve()),
        "path": str((snapshot_path.parent / "data" / "raw" / "tables").resolve()),
        "present": False,
        "required_present": False,
        "files": [],
        "missing_required": list(REQUIRED_RAW_TABLES),
    }


def _safe_export_name(path: Path, *, base_dir: Path) -> str:
    try:
        rel = path.resolve().relative_to(base_dir.resolve())
        return rel.as_posix()
    except (OSError, ValueError):
        return path.name


def _candidate_diagnostic_paths(
    snapshot: dict[str, Any],
    snapshot_path: Path,
    *,
    diagnostic_profile: str = DEFAULT_DIAGNOSTIC_PROFILE,
) -> list[Path]:
    diagnostic_profile = _normalize_diagnostic_profile(diagnostic_profile)
    base_dir = snapshot_path.parent
    candidates: list[Path] = [
        snapshot_path,
        base_dir / "capture_source_status.json",
        base_dir / UI_HEALTH_LOG,
        base_dir / UI_RUNTIME_STATUS,
        base_dir / "local_player_cache.json",
        base_dir / "monitor.lock",
        base_dir / "monitor.stdout.log",
        base_dir / "monitor.stderr.log",
    ]
    if diagnostic_profile == "engineering":
        candidates.extend(
            [
                base_dir / SUMMARY_DIAGNOSTIC_LOG,
                base_dir / "model_eval.jsonl",
                base_dir / "monitor_errors.jsonl",
            ]
        )
    if diagnostic_profile in {"engineering", "portable"}:
        candidates.extend(
            [
                base_dir / "fatbeans_webhook_live.json",
                base_dir / "raw" / "fatbeans_webhook_live.jsonl",
            ]
        )
        for key in ("raw_capture", "raw_capture_jsonl"):
            raw_value = snapshot.get(key)
            if not raw_value:
                continue
            path = Path(str(raw_value))
            if not path.is_absolute():
                path = base_dir / path
            candidates.append(path)
    seen: set[Path] = set()
    out: list[Path] = []
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        out.append(path)
    return out


def _diagnostic_file_summary(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError:
        return {"path": str(path), "exists": False}
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_at": stat.st_mtime,
    }


def _write_diagnostic_export(
    *,
    snapshot: dict[str, Any],
    snapshot_path: Path,
    current_summary: dict[str, Any] | None = None,
    diagnostic_profile: str = DEFAULT_DIAGNOSTIC_PROFILE,
    show_taskbar: bool = False,
) -> Path:
    export_started = time.perf_counter()
    diagnostic_profile = _normalize_diagnostic_profile(diagnostic_profile)
    export_dir = _diagnostic_export_dir(snapshot_path)
    export_dir.mkdir(parents=True, exist_ok=True)
    context = _mapping(current_summary.get("context") if current_summary else {})
    session_text = str(context.get("session_id") or snapshot.get("session_id") or "session")
    safe_session = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in session_text)[:48]
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    export_path = export_dir / f"HeroRefDiag-{timestamp}-{safe_session}.zip"
    base_dir = snapshot_path.parent
    current_reference = _mapping(current_summary.get("reference") if current_summary else {})
    current_evidence = _mapping(current_summary.get("evidence") if current_summary else {})
    current_diagnostics = _mapping(current_summary.get("diagnostics") if current_summary else {})
    raw_tables = _raw_tables_summary(snapshot_path)
    package_is_public_safe = not bool(raw_tables.get("required_present"))
    manifest = {
        "created_at": time.time(),
        "snapshot_path": str(snapshot_path),
        "session_id": session_text,
        "context": context,
        "version": {
            "schema_version": snapshot.get("schema_version"),
            "ui_contract_schema_version": _mapping(snapshot.get("ui_contract")).get("schema_version"),
            "source_file": snapshot.get("file"),
            "created_at": snapshot.get("created_at"),
        },
        "parameters": {
            "n_trials": snapshot.get("n_trials"),
            "roi_trials": snapshot.get("roi_trials"),
            "shadow_trials": snapshot.get("shadow_trials"),
            "formal_mode_requested": snapshot.get("formal_mode_requested"),
            "formal_mode": snapshot.get("formal_mode"),
            "formal_baseline_source": snapshot.get("formal_baseline_source"),
            "map_id": snapshot.get("map_id"),
            "model_map_id": snapshot.get("model_map_id"),
            "map_alias_mode": snapshot.get("map_alias_mode"),
            "hero": snapshot.get("hero"),
            "round": snapshot.get("round"),
            "phase": snapshot.get("phase"),
        },
        "startup": {
            "launch_mode": "taskbar" if show_taskbar else "floating",
            "show_taskbar": bool(show_taskbar),
            "diagnostic_profile": diagnostic_profile,
        },
        "package": {
            "is_public_safe": package_is_public_safe,
            "includes_raw_tables": bool(raw_tables.get("required_present")),
            "raw_tables_dir": raw_tables.get("path"),
            "raw_tables_root": raw_tables.get("package_root"),
            "raw_tables_missing_required": raw_tables.get("missing_required"),
        },
        "current_summary": {
            "status": current_summary.get("status") if current_summary else None,
            "reference_source": current_reference.get("source"),
            "readiness": current_reference.get("readiness"),
            "candidate_summary": current_evidence.get("candidate_summary"),
            "next_info_hint": current_evidence.get("next_info_hint"),
            "rare_signal_summary": _mapping(current_diagnostics.get("rare_signals")).get("summary"),
        },
        "source_files": {
            "file": snapshot.get("file"),
            "raw_capture": snapshot.get("raw_capture"),
            "raw_capture_jsonl": snapshot.get("raw_capture_jsonl"),
        },
        "log_summary": {
            "log_dir": str(base_dir.resolve()),
            "diagnostic_profile": diagnostic_profile,
            "continuous_ui_summary": diagnostic_profile == "engineering",
            "export_includes_raw": diagnostic_profile in {"engineering", "portable"},
            "export_includes_ui_summary": diagnostic_profile == "engineering",
            "latest_snapshot": _diagnostic_file_summary(snapshot_path),
            "ui_summary": _diagnostic_file_summary(base_dir / SUMMARY_DIAGNOSTIC_LOG),
            "ui_health": _diagnostic_file_summary(base_dir / UI_HEALTH_LOG),
            "ui_runtime_status": _diagnostic_file_summary(base_dir / UI_RUNTIME_STATUS),
            "monitor_stdout": _diagnostic_file_summary(base_dir / "monitor.stdout.log"),
            "monitor_stderr": _diagnostic_file_summary(base_dir / "monitor.stderr.log"),
            "model_eval": _diagnostic_file_summary(base_dir / "model_eval.jsonl"),
            "monitor_errors": _diagnostic_file_summary(base_dir / "monitor_errors.jsonl"),
            "raw_tables": raw_tables,
        },
        "included": [],
        "missing_optional": [],
        "note": "Hero Ref diagnostic package; no screenshots are included.",
    }
    with zipfile.ZipFile(export_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in _candidate_diagnostic_paths(
            snapshot,
            snapshot_path,
            diagnostic_profile=diagnostic_profile,
        ):
            arcname = _safe_export_name(path, base_dir=base_dir)
            archive.write(path, arcname)
            manifest["included"].append(arcname)
        manifest["log_summary"]["included_count"] = len(manifest["included"])
        if current_summary:
            archive.writestr(
                "hero_ref_current_summary.json",
                json.dumps(current_summary, ensure_ascii=False, indent=2),
            )
            manifest["included"].append("hero_ref_current_summary.json")
        manifest["performance"] = {
            "export_ms": round((time.perf_counter() - export_started) * 1000.0, 2),
        }
        archive.writestr(
            "BUILD_EXPORT_MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
    return export_path


def _status_int(payload: dict[str, Any], key: str) -> int:
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _capture_status_signature(status: dict[str, Any]) -> tuple[Any, ...]:
    if not status:
        return ()
    ignored = status.get("ignored_reasons")
    ignored_items: tuple[tuple[str, int], ...] = ()
    if isinstance(ignored, dict):
        ignored_items = tuple(
            sorted((str(key), _to_int(value, 0)) for key, value in ignored.items())
        )
    return (
        _text(status.get("source"), ""),
        _text(status.get("process_name"), ""),
        _text(status.get("filter"), ""),
        _status_int(status, "active_flows"),
        _status_int(status, "sniffed_packets"),
        _status_int(status, "raw_packets"),
        _status_int(status, "accepted_frames"),
        _status_int(status, "ignored_frames"),
        _status_int(status, "dropped_bytes"),
        _text(status.get("active_session_id"), ""),
        ignored_items,
    )


def _top_ignored_reason(status: dict[str, Any]) -> str:
    ignored = status.get("ignored_reasons")
    if not isinstance(ignored, dict) or not ignored:
        return "-"
    reason, count = max(
        ignored.items(),
        key=lambda item: _to_int(item[1], 0),
    )
    return f"{reason} x{_to_int(count, 0)}"


def _capture_wait_diagnostics(status: dict[str, Any]) -> dict[str, Any]:
    if not status:
        return {
            "subtitle": "等待 monitor 状态",
            "flags": [{"label": "无实时数据", "level": "watch", "detail": ""}],
            "action": "等待启动",
            "state": "no_capture_status",
            "recent": "-",
            "source": "-",
            "detail": "未看到 capture_source_status.json",
            "note": "确认已用管理员权限启动 Hero Ref",
        }
    active = _status_int(status, "active_flows")
    raw = _status_int(status, "raw_packets")
    accepted = _status_int(status, "accepted_frames")
    sniffed = _status_int(status, "sniffed_packets")
    session = _text(status.get("active_session_id"), "")
    source = _text(status.get("source"), "windivert")
    top_reason = _top_ignored_reason(status)
    detail = f"flow {active} / raw {raw} / accepted {accepted}"
    error_code = _text(status.get("error_code"), "")
    error_message = _text(status.get("error_message"), "")
    error_hint = _text(status.get("error_hint"), "")
    if error_code:
        subtitle = "monitor 底层抓包启动失败"
        action = "检查防火墙/安全软件"
        state = error_code
        note = error_hint or "重新解压 full 包，信任整个文件夹后用管理员入口启动"
        flags = [
            {
                "label": "抓包失败",
                "level": "risk",
                "detail": error_message or error_code,
            }
        ]
    elif active <= 0:
        subtitle = "monitor 已启动，等待 BidKing.exe 网络流"
        action = "等待游戏连接"
        state = "no_active_flow"
        note = "先进入对局；若 VPN/UU 开启，尝试备用启动"
        flags = [{"label": "等待连接", "level": "neutral", "detail": detail}]
    elif raw <= 0:
        subtitle = "已连接游戏流，等待对局包"
        action = "等待对局包"
        state = "no_raw_packets"
        note = "保持 UI 开启后进入新局或使用道具"
        flags = [{"label": "已连接", "level": "neutral", "detail": detail}]
    elif accepted <= 0:
        subtitle = "已抓到流量，但未解析到对局状态帧"
        action = "等待状态帧"
        state = "raw_no_game_frame"
        note = "monitor 未掉线；若一直如此，用 BroadSniff/IncludeLoopback 备用启动"
        flags = [{"label": "抓包未成帧", "level": "watch", "detail": top_reason}]
    else:
        subtitle = "已识别会话，等待估价状态帧"
        action = "等待估价帧"
        state = "session_waiting_snapshot"
        note = "开局状态可能已错过；下一次状态/道具结果会刷新"
        flags = [{"label": "会话已识别", "level": "neutral", "detail": session or detail}]
    return {
        "subtitle": subtitle,
        "flags": flags,
        "action": action,
        "state": state,
        "recent": top_reason,
        "source": source,
        "detail": f"{detail} / sniffed {sniffed}",
        "note": note,
        "session": session,
    }


def _compact_capture_runtime_status(status: dict[str, Any]) -> dict[str, Any]:
    diagnostics = _capture_wait_diagnostics(status)
    return {
        "present": bool(status),
        "source": _text(status.get("source"), "") if status else "",
        "process_name": _text(status.get("process_name"), "") if status else "",
        "filter": _text(status.get("filter"), "") if status else "",
        "active_flows": _status_int(status, "active_flows"),
        "sniffed_packets": _status_int(status, "sniffed_packets"),
        "raw_packets": _status_int(status, "raw_packets"),
        "accepted_frames": _status_int(status, "accepted_frames"),
        "ignored_frames": _status_int(status, "ignored_frames"),
        "dropped_bytes": _status_int(status, "dropped_bytes"),
        "active_session_id": _text(status.get("active_session_id"), "") if status else "",
        "top_ignored_reason": _top_ignored_reason(status) if status else "-",
        "wait_state": diagnostics.get("state"),
        "wait_action": diagnostics.get("action"),
        "wait_note": diagnostics.get("note"),
        "error_code": _text(status.get("error_code"), "") if status else "",
        "error_message": _text(status.get("error_message"), "") if status else "",
        "error_hint": _text(status.get("error_hint"), "") if status else "",
    }


def _to_int(value: Any, default: int) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _to_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def _to_manual_count(value: Any, label: str) -> tuple[int | None, str]:
    if value in (None, ""):
        return None, ""
    text = str(value).replace(",", "").strip()
    if not text:
        return None, ""
    parsed = _to_optional_float(text)
    if parsed is None:
        return None, f"{label}需要整数"
    if not parsed.is_integer():
        return None, f"{label}需要整数；{text} 像均格，请填到均格/总格"
    return int(parsed), ""


def _to_manual_nonnegative_float(value: Any, label: str) -> tuple[float | None, str]:
    if value in (None, ""):
        return None, ""
    text = str(value).replace(",", "").strip()
    if not text:
        return None, ""
    parsed = _to_optional_float(text)
    if parsed is None:
        return None, f"{label}需要数字"
    if parsed < 0:
        return None, f"{label}不能为负数"
    return parsed, ""


def _to_manual_value_sum(value: Any, label: str) -> tuple[int | None, str]:
    parsed, error = _to_manual_nonnegative_float(value, label)
    if error or parsed is None:
        return None, error
    if not parsed.is_integer():
        return None, f"{label}需要整数"
    return int(parsed), ""


def _manual_value_sum_matches_avg(avg: float, *, count: int, value_sum: float) -> bool:
    if count <= 0:
        return abs(float(value_sum)) <= 0.0001 and abs(float(avg)) <= 0.0001
    return abs(float(avg) * count - float(value_sum)) <= 0.5


def _normalize_manual_hero(value: Any) -> str:
    return normalize_hero_key(value)


def _supported_manual_hero_display(*values: Any) -> Any:
    for value in values:
        if is_supported_ref_hero(value):
            return value
    return None


def _normalize_manual_map_text(value: Any) -> str:
    text = str(value or "").replace("\u200b", "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"[\s_\-:：#()\[\]（）【】]+", "", text)
    for prefix in ("地图", "mapid", "map"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text


def _processed_maps_candidates() -> tuple[Path, ...]:
    candidates = [
        ROOT / "data" / "processed" / "maps.json",
        Path.cwd() / "data" / "processed" / "maps.json",
    ]
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / "data" / "processed" / "maps.json")
    return tuple(candidates)


@lru_cache(maxsize=1)
def _processed_map_name_rows() -> tuple[tuple[int, str], ...]:
    for path in _processed_maps_candidates():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, list):
            continue
        rows: list[tuple[int, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            map_id = _to_optional_int(item.get("map_id"))
            name = _text(item.get("name"), "").replace("\u200b", "").strip()
            if map_id is None or not name:
                continue
            rows.append((map_id, name))
        if rows:
            return tuple(rows)
    return ()


def _add_manual_map_alias(
    lookup: dict[str, tuple[int, str]],
    alias: Any,
    map_id: int,
    name: str,
) -> None:
    key = _normalize_manual_map_text(alias)
    if key:
        lookup.setdefault(key, (map_id, name))


def _manual_map_lookup() -> dict[str, tuple[int, str]]:
    lookup: dict[str, tuple[int, str]] = {}
    for map_id, name in _processed_map_name_rows():
        for alias in {str(map_id), name, f"{map_id}{name}", f"{name}{map_id}"}:
            _add_manual_map_alias(lookup, alias, map_id, name)

    data: dict[str, Any] = {}
    if callable(load_reference_static_data):
        try:
            loaded = load_reference_static_data()
            if isinstance(loaded, dict):
                data = loaded
        except Exception:  # noqa: BLE001 - manual fallback should not depend on static parsing
            data = {}
    map_nests = data.get("map_nests") if isinstance(data.get("map_nests"), dict) else {}
    for raw_map_id, raw_row in map_nests.items():
        map_id = _to_optional_int(raw_map_id)
        if map_id is None:
            continue
        name = ""
        if isinstance(raw_row, (list, tuple)) and len(raw_row) >= 2:
            name = _text(raw_row[1], "")
        for alias in {str(map_id), name, f"{map_id}{name}", f"{name}{map_id}"}:
            _add_manual_map_alias(lookup, alias, map_id, name)
    for alias, map_id in MANUAL_GENERIC_MAP_ALIASES.items():
        _add_manual_map_alias(lookup, alias, map_id, _manual_map_name(map_id, lookup=lookup))
    return lookup


def _manual_map_name(map_id: Any, *, lookup: dict[str, tuple[int, str]] | None = None) -> str:
    parsed = _to_optional_int(map_id)
    if parsed is None:
        return ""
    entries = lookup if lookup is not None else _manual_map_lookup()
    row = entries.get(str(parsed))
    return row[1] if row else ""


def _manual_map_display_value(value: Any) -> str:
    map_id = _to_optional_int(value)
    if map_id is None:
        return _text(value, "")
    name = _manual_map_name(map_id)
    return f"{map_id} {name}".strip() if name else str(map_id)


def _manual_map_id_from_text(value: Any) -> tuple[int | None, str]:
    text = str(value or "").strip()
    if not text:
        return None, ""
    parsed = _to_optional_int(text)
    if parsed is not None:
        return parsed, ""
    match = re.search(r"(?<!\d)(\d{4})(?!\d)", text.replace(",", ""))
    if match:
        return int(match.group(1)), ""
    lookup = _manual_map_lookup()
    row = lookup.get(_normalize_manual_map_text(text))
    if row is not None:
        return row[0], ""
    return None, f"地图无法识别：{text}"


def _minimap_quality_key(value: Any) -> str:
    if value in (None, ""):
        return "unknown"
    text = str(value).strip().lower()
    if text.startswith("q") and text[1:].isdigit():
        return text
    parsed = _to_optional_int(value)
    if parsed is not None:
        return f"q{parsed}"
    return text or "unknown"


def _to_optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _format_manual_number(value: Any) -> str:
    parsed = _to_optional_float(value)
    if parsed is None:
        return "" if value in (None, "") else str(value)
    if parsed.is_integer():
        return str(int(parsed))
    return f"{parsed:.4f}".rstrip("0").rstrip(".")


def _manual_quality_label(key: str) -> str:
    return SPLIT_QUALITY_LABELS.get(key, QUALITY_LABELS.get(key, key))


def _manual_avg_grid_options(count: int, avg: float) -> list[int]:
    if can_compose_grid_total is None:
        return []
    if count < 0:
        return []
    if count == 0:
        return [0] if avg == 0 else []
    low = count
    high = 18 * count
    target = avg * count
    tolerance = 0.0001
    candidates = {
        int(math.floor(target)),
        int(round(target)),
        int(math.ceil(target)),
    }
    options = [
        grid
        for grid in sorted(candidates)
        if low <= grid <= high
        and abs(grid - target) <= tolerance
        and can_compose_grid_total(count, grid)
    ]
    if options:
        return options
    return [
        grid
        for grid in range(low, high + 1)
        if abs(grid - target) <= tolerance
        and can_compose_grid_total(count, grid)
    ]


def _decimal_places(text: str) -> int:
    value = str(text or "").strip().replace(",", "")
    if not value:
        return 0
    if "e" in value.lower():
        return 6
    if "." not in value:
        return 0
    return max(0, len(value.split(".", 1)[1]))


def _manual_decimal_parts(text: str) -> tuple[str, str] | None:
    value = str(text or "").strip().replace(",", "")
    if not value or "e" in value.lower():
        return None
    if "." in value:
        int_part, frac_part = value.split(".", 1)
        if not frac_part:
            return None
    else:
        int_part, frac_part = value, ""
    if not int_part or not int_part.isdigit() or (frac_part and not frac_part.isdigit()):
        return None
    return str(int(int_part)), frac_part


def _manual_avg_uses_display_rule(avg_text: str) -> bool:
    parts = _manual_decimal_parts(avg_text)
    if parts is None:
        return False
    _int_part, frac_part = parts
    return len(frac_part) <= 3


def _format_manual_game_avg(total_cells: int, count: int, *, max_decimals: int) -> str:
    if count <= 0 or total_cells < 0:
        return ""
    decimals = max(2, max_decimals)
    scale = 10**decimals
    floored_scaled = (int(total_cells) * scale) // int(count)
    int_part, frac_value = divmod(floored_scaled, scale)
    digits = str(frac_value).zfill(decimals)
    if int(total_cells) * scale == floored_scaled * int(count):
        digits = digits.rstrip("0")
    return f"{int_part}.{digits}" if digits else str(int_part)


def _manual_avg_text_matches_grid(avg_text: str, *, count: int, cells: int) -> bool:
    parts = _manual_decimal_parts(avg_text)
    if parts is None or count <= 0:
        return False
    int_part, frac_part = parts
    normalized = f"{int_part}.{frac_part}" if frac_part else int_part
    max_decimals = max(2, len(frac_part))
    return _format_manual_game_avg(cells, count, max_decimals=max_decimals) == normalized


def _manual_avg_product_tolerance(avg_text: str, count: int) -> float:
    decimals = _decimal_places(avg_text)
    if decimals < 2:
        return 0.0001
    return max(0.0001, (0.5 * (10 ** -decimals) * max(1, int(count))) + 1e-9)


def _manual_avg_matches_cells(
    avg: float | None,
    *,
    avg_text: str,
    count: int,
    cells: int,
) -> bool:
    if avg is None:
        return True
    if int(count) == 0:
        return float(avg) == 0 and int(cells) == 0
    if _manual_avg_uses_display_rule(avg_text):
        return _manual_avg_text_matches_grid(avg_text, count=count, cells=cells)
    return abs(float(avg) * int(count) - int(cells)) <= _manual_avg_product_tolerance(
        avg_text,
        count,
    )


def _manual_avg_grid_options_from_text(count: int, avg: float, avg_text: str) -> list[int]:
    if can_compose_grid_total is None:
        return []
    if count < 0:
        return []
    if count == 0:
        return [0] if avg == 0 else []
    low = count
    high = 18 * count
    if _manual_avg_uses_display_rule(avg_text):
        return [
            grid
            for grid in range(low, high + 1)
            if _manual_avg_text_matches_grid(avg_text, count=count, cells=grid)
            and can_compose_grid_total(count, grid)
        ]
    target = avg * count
    tolerance = _manual_avg_product_tolerance(avg_text, count)
    candidates = {
        int(math.floor(target)),
        int(round(target)),
        int(math.ceil(target)),
    }
    options = [
        grid
        for grid in sorted(candidates)
        if low <= grid <= high
        and abs(grid - target) <= tolerance
        and can_compose_grid_total(count, grid)
    ]
    if options:
        return options
    return [
        grid
        for grid in range(low, high + 1)
        if abs(grid - target) <= tolerance
        and can_compose_grid_total(count, grid)
    ]


def _manual_avg_count_from_cells(avg: float | None, cells: Any) -> int | None:
    if can_compose_grid_total is None or avg is None or cells in (None, ""):
        return None
    try:
        cells_value = float(str(cells).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if cells_value < 0:
        return None
    cells_int = int(round(cells_value))
    if abs(cells_value - cells_int) > 0.0001:
        return None
    if avg == 0:
        return 0 if cells_int == 0 else None
    count = int(round(cells_int / avg))
    if count <= 0:
        return None
    if abs(avg * count - cells_int) > 0.0001:
        return None
    if not can_compose_grid_total(count, cells_int):
        return None
    return count


def _manual_avg_count_from_cells_text(avg: float | None, cells: Any, avg_text: str) -> int | None:
    if can_compose_grid_total is None or avg is None or cells in (None, ""):
        return None
    try:
        cells_value = float(str(cells).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if cells_value < 0:
        return None
    cells_int = int(round(cells_value))
    if abs(cells_value - cells_int) > 0.0001:
        return None
    if avg == 0:
        return 0 if cells_int == 0 else None
    if _manual_avg_uses_display_rule(avg_text):
        candidates = [
            count
            for count in range(1, cells_int + 1)
            if _manual_avg_text_matches_grid(avg_text, count=count, cells=cells_int)
            and can_compose_grid_total(count, cells_int)
        ]
        return candidates[0] if len(candidates) == 1 else None
    count = int(round(cells_int / avg))
    if count <= 0:
        return None
    if not _manual_avg_matches_cells(avg, avg_text=avg_text, count=count, cells=cells_int):
        return None
    if not can_compose_grid_total(count, cells_int):
        return None
    return count


def _money(value: Any, fallback: str = "-") -> str:
    if value in (None, ""):
        return fallback
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


def _flag_color(level: str) -> str:
    if level == "risk":
        return BAD
    if level == "watch":
        return WARN
    if level == "neutral":
        return ACCENT
    return MUTED


def _terminate_pid(pid: int) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        import psutil

        process = psutil.Process(pid)
        process.terminate()
        try:
            process.wait(timeout=3.0)
        except psutil.TimeoutExpired:
            process.kill()
            process.wait(timeout=3.0)
        return True
    except ImportError:
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except OSError:
            return False
    except Exception:
        return False


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        import psutil

        return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
    except ImportError:
        pass
    except Exception:
        return False
    if os.name == "nt":
        try:
            import ctypes

            process_query_limited_information = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                process_query_limited_information,
                False,
                int(pid),
            )
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _watched_pid_exited(pids: tuple[int, ...]) -> bool:
    return any(not _pid_running(int(pid)) for pid in pids if int(pid) > 0)


class SlimScrollbar(tk.Canvas):
    def __init__(self, parent: tk.Widget, *, command: Any, hide_when_full: bool = True) -> None:
        super().__init__(
            parent,
            width=8,
            height=1,
            bg=PANEL_MUTED,
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
        )
        self.command = command
        self.hide_when_full = hide_when_full
        self._pack_kwargs: dict[str, Any] | None = None
        self._grid_kwargs: dict[str, Any] | None = None
        self._hidden = False
        self._first = 0.0
        self._last = 1.0
        self._drag_anchor = 0
        self._dragging = False
        self._hover = False
        self.bind("<Configure>", self._redraw, add="+")
        self.bind("<ButtonPress-1>", self._begin_drag, add="+")
        self.bind("<B1-Motion>", self._drag, add="+")
        self.bind("<ButtonRelease-1>", self._end_drag, add="+")
        self.bind("<Enter>", self._enter, add="+")
        self.bind("<Leave>", self._leave, add="+")

    def pack(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self._pack_kwargs = kwargs.copy()
        self._grid_kwargs = None
        self._hidden = False
        super().pack(*args, **kwargs)

    def grid(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self._grid_kwargs = kwargs.copy()
        self._pack_kwargs = None
        self._hidden = False
        super().grid(*args, **kwargs)

    def set(self, first: Any, last: Any) -> None:
        try:
            self._first = max(0.0, min(1.0, float(first)))
            self._last = max(self._first, min(1.0, float(last)))
        except (TypeError, ValueError):
            return
        full = self._first <= 0.001 and self._last >= 0.999
        if full and self.hide_when_full:
            if not self._hidden:
                if self._grid_kwargs is not None:
                    self.grid_remove()
                elif self._pack_kwargs is not None:
                    self.pack_forget()
                self._hidden = True
            return
        if self._hidden:
            self._restore()
        self._redraw()

    def _restore(self) -> None:
        if self._grid_kwargs is not None:
            super().grid(**self._grid_kwargs)
        elif self._pack_kwargs is not None:
            super().pack(**self._pack_kwargs)
        self._hidden = False

    def _thumb_geometry(self) -> tuple[int, int, int]:
        height = max(1, self.winfo_height())
        visible = max(0.02, min(1.0, self._last - self._first))
        thumb_height = max(22, int(height * visible))
        thumb_height = min(height, thumb_height)
        max_top = max(0, height - thumb_height)
        max_first = max(0.001, 1.0 - visible)
        top = int((self._first / max_first) * max_top) if max_top else 0
        top = max(0, min(max_top, top))
        return top, top + thumb_height, thumb_height

    def _redraw(self, _event: tk.Event[Any] | None = None) -> None:
        if self._hidden:
            return
        self.delete("all")
        width = max(8, self.winfo_width())
        height = max(1, self.winfo_height())
        self.create_rectangle(width // 2 - 1, 0, width // 2 + 1, height, fill=SCROLL_LINE, outline="")
        top, bottom, _thumb_height = self._thumb_geometry()
        thumb_color = WARM if self._dragging else (ACCENT if self._hover else MUTED)
        self.create_rectangle(
            1,
            top + 1,
            width - 2,
            max(top + 22, bottom - 1),
            fill=thumb_color,
            outline="",
        )

    def _move_to_thumb_top(self, top: int) -> None:
        _old_top, _old_bottom, thumb_height = self._thumb_geometry()
        height = max(1, self.winfo_height())
        max_top = max(0, height - thumb_height)
        if max_top <= 0:
            return
        visible = max(0.02, min(1.0, self._last - self._first))
        max_first = max(0.001, 1.0 - visible)
        new_first = max(0.0, min(max_top, float(top))) / max_top * max_first
        self.command("moveto", new_first)

    def _begin_drag(self, event: tk.Event[Any]) -> str:
        top, bottom, thumb_height = self._thumb_geometry()
        if event.y < top or event.y > bottom:
            top = int(event.y - thumb_height / 2)
            self._move_to_thumb_top(top)
            top, _bottom, _thumb_height = self._thumb_geometry()
        self._drag_anchor = event.y - top
        self._dragging = True
        self._redraw()
        return "break"

    def _drag(self, event: tk.Event[Any]) -> str:
        if self._dragging:
            self._move_to_thumb_top(event.y - self._drag_anchor)
        return "break"

    def _end_drag(self, _event: tk.Event[Any]) -> str:
        self._dragging = False
        self._redraw()
        return "break"

    def _enter(self, _event: tk.Event[Any]) -> None:
        self._hover = True
        self._redraw()

    def _leave(self, _event: tk.Event[Any]) -> None:
        self._hover = False
        self._redraw()


def _slim_scrollbar(parent: tk.Widget, *, command: Any, hide_when_full: bool = True) -> SlimScrollbar:
    return SlimScrollbar(parent, command=command, hide_when_full=hide_when_full)


def _monitor_lock_path(snapshot_path: Path) -> Path:
    return snapshot_path.parent / "monitor.lock"


def _pid_from_monitor_lock(lock_path: Path) -> int | None:
    payload = _read_json(lock_path)
    try:
        pid = int(payload.get("pid"))
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def _cleanup_exit_targets(
    pids: tuple[int, ...] | list[int],
    lock_paths: tuple[Path, ...] | list[Path],
    *,
    terminate_fn: Any = _terminate_pid,
) -> None:
    seen: set[int] = set()
    for pid in pids:
        if pid in seen:
            continue
        seen.add(pid)
        terminate_fn(int(pid))
    for lock_path in lock_paths:
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


class HoverTip:
    def __init__(self, widget: tk.Widget, text: str = "") -> None:
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<Motion>", self._motion, add="+")

    def set_text(self, text: Any) -> None:
        self.text = _text(text, "")

    def show_at(self, event: tk.Event[Any], text: Any | None = None) -> None:
        if text is not None:
            self.set_text(text)
        if not self.text:
            return
        if self.tip is None:
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.tip.attributes("-topmost", True)
            label = tk.Label(
                self.tip,
                text=self.text,
                bg=TOOLTIP_BG,
                fg=TEXT,
                justify="left",
                wraplength=360,
                padx=8,
                pady=6,
                relief="solid",
                borderwidth=1,
                font=(FONT_UI, 9),
            )
            label.pack()
        else:
            label = self.tip.winfo_children()[0]
            if isinstance(label, tk.Label):
                label.configure(text=self.text)
        self.tip.geometry(f"+{event.x_root + 12}+{event.y_root + 10}")

    def hide(self, _event: tk.Event[Any] | None = None) -> None:
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None

    def _enter(self, event: tk.Event[Any]) -> None:
        self.show_at(event)

    def _motion(self, event: tk.Event[Any]) -> None:
        if self.tip is not None:
            self.tip.geometry(f"+{event.x_root + 12}+{event.y_root + 10}")


class AhmadTkOverlay:
    def __init__(
        self,
        root: tk.Tk,
        *,
        snapshot_path: Path,
        interval_ms: int,
        exit_when_pids: tuple[int, ...] = (),
        stop_pids_on_exit: tuple[int, ...] = (),
        cleanup_lock_paths: tuple[Path, ...] = (),
        keep_monitor_on_close: bool = False,
        load_existing_snapshot: bool = False,
        diagnostic_profile: str = DEFAULT_DIAGNOSTIC_PROFILE,
        show_taskbar: bool = False,
        ui_prefs_enabled: bool = False,
    ) -> None:
        self.root = root
        self.snapshot_path = snapshot_path
        self.interval_ms = max(300, int(interval_ms))
        self.diagnostic_profile = _normalize_diagnostic_profile(diagnostic_profile)
        self.show_taskbar = bool(show_taskbar)
        self.exit_when_pids = exit_when_pids
        self._stop_pids_on_exit = tuple(pid for pid in stop_pids_on_exit if pid > 0)
        self._cleanup_lock_paths = tuple(cleanup_lock_paths)
        self.keep_monitor_on_close = bool(keep_monitor_on_close)
        self._exit_cleanup_done = False
        self._last_ui_heartbeat_at = time.monotonic()
        self._last_ui_stall_bucket = 0
        self._last_signature: tuple[int, int] | None = None
        self._last_capture_status_signature: tuple[Any, ...] | None = None
        self._last_summary: dict[str, Any] = {}
        self._last_live_snapshot: dict[str, Any] = {}
        self._last_live_summary: dict[str, Any] = {}
        self._last_summary_log_signature: str | None = None
        self._summary_result_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._summary_worker_running = False
        self._summary_worker_seq = 0
        self._summary_worker_signature: tuple[int, int] | None = None
        self._summary_worker_pending: dict[str, Any] | None = None
        self._manual_result_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._manual_worker_running = False
        self._manual_worker_seq = 0
        self._manual_input_revision = 0
        self._manual_snapshot: dict[str, Any] = {}
        self._manual_summary: dict[str, Any] = {}
        self._manual_active = False
        self._manual_edit_enabled = False
        self._manual_live_session_id = ""
        self._manual_programmatic_update = False
        self._manual_dirty_fields: set[str] = set()
        self._manual_autofill_values: dict[str, str] = {}
        self._manual_settlement_edit_unlocked = False
        self._manual_auto_expanded_details = False
        self.settlement_values_hidden = False
        self.topmost_enabled = True
        self.last_diagnostic_export_path: Path | None = None
        self._minimap_data: dict[str, Any] = {}
        self._minimap_canvas_signatures: dict[int, tuple[Any, ...]] = {}
        self._canvas_tip: HoverTip | None = None
        self._popup_canvas_tip: HoverTip | None = None
        self._minimap_popup: tk.Toplevel | None = None
        self._popup_canvas: tk.Canvas | None = None
        self._popup_title: tk.Label | None = None
        self._popup_counts: tk.Label | None = None
        self._pinned_minimap_popup: tk.Toplevel | None = None
        self._pinned_canvas: tk.Canvas | None = None
        self._pinned_title: tk.Label | None = None
        self._pinned_counts: tk.Label | None = None
        self._pinned_canvas_tip: HoverTip | None = None
        self._pinned_offset: tuple[int, int] | None = None
        self._pinned_minimap_follow = True
        self._pinned_minimap_drag_offset: tuple[int, int] | None = None
        self._pinned_configure_after_id: str | None = None
        self._hide_minimap_after_id: str | None = None
        self.details_expanded = False
        self._load_existing_snapshot = load_existing_snapshot
        self._drag_offset: tuple[int, int] | None = None
        self._resize_anchor: tuple[int, int, int, int] | None = None
        self._custom_details_size: tuple[int, int] | None = None
        self._custom_mini_size: tuple[int, int] | None = None
        self._mini_layout_snapshot: tuple[
            tuple[int, int] | None,
            tuple[int, int],
            float,
        ] | None = None
        self._ui_prefs_enabled = bool(ui_prefs_enabled)
        self._ui_prefs_path = ui_prefs_path_for_snapshot(snapshot_path)
        self._ui_prefs_save_after_id: str | None = None
        self._pending_window_position: tuple[int, int] | None = None
        self._resize_active = False
        self._live_scale_pending: float | None = None
        self._live_scale_after_id: str | None = None
        self._live_scale_last_at = 0.0
        self._ui_scale = 1.0
        self._scaled_layout_specs: list[tuple[tk.Widget, dict[str, int]]] = []
        self.theme_name = "dark"
        self.theme_values = _theme_by_name(self.theme_name)

        root.title("Hero Ref")
        root.configure(bg=BG)
        root.attributes("-topmost", True)
        _apply_taskbar_mode(root, show_taskbar=self.show_taskbar)
        _apply_windows_toolwindow(root, enabled=not self.show_taskbar)
        root.resizable(True, True)
        root.minsize(430, 320)
        root.geometry(f"{self._mini_geometry()}+20+0")

        style = ttk.Style(root)
        self.style = style
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Hero.TButton",
            background=PANEL_SOFT,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=PANEL_SOFT,
            darkcolor=PANEL_SOFT,
            padding=(8, 4),
            borderwidth=0,
            relief="flat",
        )
        style.map("Hero.TButton", background=[("active", HERO_BUTTON_ACTIVE)])

        self.outer = tk.Frame(root, bg=BG)
        self.outer.pack(fill="both", expand=True)

        tk.Frame(self.outer, bg=WARM, width=2).pack(side="left", fill="y")
        self.shell = tk.Frame(self.outer, bg=BG, padx=9, pady=9)
        self.shell.pack(side="left", fill="both", expand=True)
        stripe = tk.Frame(self.shell, bg=BG)
        stripe.pack(fill="x", pady=(0, 7))
        tk.Frame(stripe, bg=ACCENT, height=1).pack(side="left", fill="x", expand=True)
        tk.Frame(stripe, bg=WARM, height=1, width=82).pack(side="right", padx=(6, 0))

        header = tk.Frame(self.shell, bg=BG)
        header.pack(fill="x")
        top_row = tk.Frame(header, bg=BG)
        top_row.pack(fill="x")
        title_box = tk.Frame(top_row, bg=BG)
        self.title = tk.Label(
            title_box,
            text="Hero Ref",
            bg=BG,
            fg=TEXT,
            font=(FONT_UI, 12, "bold"),
            anchor="w",
        )
        self.title.pack(fill="x")
        self.subtitle = tk.Label(
            title_box,
            text="等待实时包",
            bg=BG,
            fg=MUTED,
            font=(FONT_UI, 7),
            anchor="w",
        )
        self.subtitle.pack(fill="x")
        self.credit_top = tk.Label(
            title_box,
            text=CREDIT_TEXT,
            bg=BG,
            fg=DIM,
            font=(FONT_UI, 6),
            anchor="w",
        )
        self.title_tip = HoverTip(self.title, CREDIT_TEXT)
        header_actions = tk.Frame(top_row, bg=BG)
        header_actions.pack(side="right", padx=(6, 0))
        title_box.pack(side="left", fill="x", expand=True)
        self.close_button = tk.Button(
            header_actions,
            text="×",
            command=self._on_user_close,
            bg=BAD,
            fg="#ffffff",
            activebackground="#ff8aa0",
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=7,
            pady=2,
            font=(FONT_UI, 8, "bold"),
        )
        self.close_button.pack(side="right", padx=(5, 0))
        self.close_tip = HoverTip(self.close_button, CLOSE_TIP_TEXT)
        self.topmost_button = tk.Label(
            header_actions,
            text="T",
            bg=PANEL_SOFT,
            fg=WARM,
            padx=6,
            pady=2,
            font=(FONT_UI, 8, "bold"),
            highlightthickness=1,
            highlightbackground=WARM,
        )
        self.topmost_button.pack(side="right", padx=(4, 0))
        self.topmost_button.bind("<Button-1>", self.toggle_topmost, add="+")
        self.topmost_tip = HoverTip(self.topmost_button, TOPMOST_ON_TIP)
        self.top_resize_grip = tk.Label(
            header_actions,
            text="◢",
            bg=BG,
            fg=DIM,
            padx=2,
            pady=2,
            font=(FONT_UI, 9, "bold"),
            highlightthickness=0,
        )
        try:
            self.top_resize_grip.configure(cursor="sizing")
        except tk.TclError:
            pass
        self.top_resize_grip.pack(side="right", padx=(0, 2))
        self.top_resize_grip.bind("<ButtonPress-1>", self._begin_resize, add="+")
        self.top_resize_grip.bind("<B1-Motion>", self._resize_window, add="+")
        self.top_resize_grip.bind("<ButtonRelease-1>", self._end_resize, add="+")
        self.top_resize_tip = HoverTip(self.top_resize_grip, RESIZE_TIP_TEXT)
        control_row = tk.Frame(header, bg=BG)
        control_row.pack(fill="x", pady=(4, 0))
        self.status = tk.Label(
            control_row,
            text="--:--",
            bg=PANEL_SOFT,
            fg=MUTED,
            padx=7,
            pady=4,
            font=(FONT_UI, 8),
        )
        self.status.pack(side="left")
        header_right = tk.Frame(control_row, bg=BG)
        header_right.pack(side="right")
        self.mode_button = ttk.Button(
            header_right,
            text="迷你",
            style="Hero.TButton",
            command=self.toggle_details,
            width=4,
        )
        self.mode_button.pack(side="right", padx=(0, 5))
        self.mode_tip = HoverTip(self.mode_button, DETAIL_TIP_TEXT)
        self.manual_button = tk.Label(
            header_right,
            text="手填",
            bg=WARM,
            fg=BUTTON_DARK_FG,
            padx=8,
            pady=4,
            font=(FONT_UI, 8, "bold"),
            highlightthickness=1,
            highlightbackground=WARM,
        )
        self.manual_button.pack(side="right", padx=(0, 5))
        self.manual_button.bind("<Button-1>", self.toggle_manual_mode, add="+")
        self.manual_tip = HoverTip(self.manual_button, MANUAL_TIP_TEXT)
        self.theme_button = tk.Label(
            header_right,
            text="配色",
            bg=PANEL_SOFT,
            fg=ACCENT,
            padx=8,
            pady=4,
            font=(FONT_UI, 8, "bold"),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.theme_button.pack(side="right", padx=(0, 5))
        self.theme_button.bind("<Button-1>", self._show_theme_menu, add="+")
        self.theme_tip = HoverTip(self.theme_button, f"{THEME_TIP_PREFIX}：暗色")
        self.map_button = tk.Label(
            header_right,
            text="地图",
            bg=PANEL_SOFT,
            fg=ACCENT,
            padx=8,
            pady=4,
            font=(FONT_UI, 8, "bold"),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.map_button.pack(side="right", padx=(0, 5))
        self.map_button.bind("<Enter>", self._show_minimap_popup, add="+")
        self.map_button.bind("<Leave>", self._schedule_hide_minimap_popup, add="+")
        self.map_button.bind("<Button-1>", self.toggle_pinned_minimap, add="+")
        self.export_diag_button = tk.Label(
            header_right,
            text="导出",
            bg=PANEL_SOFT,
            fg=ACCENT,
            padx=8,
            pady=4,
            font=(FONT_UI, 8, "bold"),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.export_diag_button.pack(side="right", padx=(0, 5))
        self.export_diag_button.bind("<Button-1>", self.export_diagnostic_package, add="+")
        self.export_diag_tip = HoverTip(self.export_diag_button, _diagnostic_export_tip(self.snapshot_path))
        self.settlement_button = tk.Label(
            header_right,
            text="藏价",
            bg=PANEL_SOFT,
            fg=DIM,
            padx=8,
            pady=4,
            font=(FONT_UI, 8, "bold"),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.settlement_button.pack(side="right", padx=(0, 5))
        self.settlement_button.bind("<Button-1>", self.toggle_settlement_values, add="+")
        self.settlement_tip = HoverTip(self.settlement_button, SETTLEMENT_HIDE_TIP)
        self._bind_drag(header, top_row, title_box, self.title, self.subtitle, control_row)

        self.flags = tk.Frame(self.shell, bg=BG)
        self.flags.pack(fill="x", pady=(5, 4))

        prices = tk.Frame(self.shell, bg=BG)
        prices.pack(fill="x")
        self.price_labels: dict[str, tk.Label] = {}
        self.price_title_labels: dict[str, tk.Label] = {}
        self.default_price_titles = {
            "conservative": "保守",
            "balanced": "参考",
            "aggressive": "激进",
        }
        for idx, (key, label, color) in enumerate(
            (
                ("conservative", "保守", GOOD),
                ("balanced", "参考", WARN),
                ("aggressive", "激进", BAD),
            )
        ):
            card = self._card(prices, bg=PANEL, padx=7, pady=6)
            card.pack(side="left", fill="x", expand=True, padx=(0, 0 if idx == 2 else 4))
            tk.Frame(card, bg=color, height=2).pack(fill="x", pady=(0, 4))
            title_label = tk.Label(
                card,
                text=label,
                bg=PANEL,
                fg=MUTED,
                font=(FONT_UI, 7),
                anchor="w",
            )
            title_label.pack(fill="x")
            self.price_title_labels[key] = title_label
            price = tk.Label(
                card,
                text="-",
                bg=PANEL,
                fg=color,
                font=(FONT_NUMERIC, 15),
                anchor="w",
            )
            price.pack(fill="x", pady=(2, 0))
            self.price_labels[key] = price

        mid = tk.Frame(self.shell, bg=BG)
        mid.pack(fill="x", pady=(5, 0))
        self.red_rows = self._row_card(
            mid,
            "红品与价值",
            (
                "红件",
                "红格",
                "紫金件",
                "红值",
                "低品件",
            ),
        )
        self.action_rows = self._row_card(
            mid,
            "当前建议",
            (
                "动作",
                "最高",
                "最近",
                "候选",
                "下一步",
            ),
        )
        self.red_rows["_card"].pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.action_rows["_card"].pack(side="left", fill="x", expand=True)

        self.details_card = self._card(self.shell, bg=PANEL_MUTED, padx=6, pady=6)
        details_grid = tk.Frame(self.details_card, bg=PANEL_MUTED)
        details_grid.pack(fill="x")
        self._build_manual_panel(details_grid)
        details_top = tk.Frame(details_grid, bg=PANEL_MUTED)
        details_top.pack(fill="x", pady=(8, 0))
        details_top.columnconfigure(0, weight=1, uniform="detail_cards")
        details_top.columnconfigure(1, weight=1, uniform="detail_cards")
        details_top.rowconfigure(0, weight=1)
        self.evidence_rows = self._row_card(
            details_top,
            "证据",
            (
                "匹配",
                "密度",
                "输入",
                "组合",
                "最近",
                "诊断",
            ),
        )
        self.detail_rows = self._row_card(
            details_top,
            "参考",
            (
                "外援",
                "决策",
                "总格",
                "总值",
                "红值",
                "结算",
                "备注",
            ),
        )
        self.evidence_rows["_card"].grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.detail_rows["_card"].grid(row=0, column=1, sticky="nsew")

        self.minimap_card = self._card(self.shell, bg=PANEL, padx=6, pady=6)
        minimap_header = tk.Frame(self.minimap_card, bg=PANEL)
        minimap_header.pack(fill="x", pady=(0, 5))
        self.minimap_title = tk.Label(
            minimap_header,
            text="小地图",
            bg=PANEL,
            fg=MUTED,
            font=(FONT_UI, 8, "bold"),
            anchor="w",
        )
        self.minimap_title.pack(side="left", fill="x", expand=True)
        self.minimap_counts = tk.Label(
            minimap_header,
            text="-",
            bg=PANEL,
            fg=MUTED,
            font=(FONT_UI, 7),
            anchor="e",
        )
        self.minimap_counts.pack(side="right")
        minimap_body = tk.Frame(self.minimap_card, bg=PANEL)
        minimap_body.pack(fill="x")
        minimap_canvas_frame = tk.Frame(minimap_body, bg=PANEL)
        minimap_canvas_frame.pack(side="left")
        self.minimap_canvas = tk.Canvas(
            minimap_canvas_frame,
            width=300,
            height=160,
            bg=MINIMAP_BG,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.minimap_scrollbar = _slim_scrollbar(
            minimap_canvas_frame,
            command=self.minimap_canvas.yview,
            hide_when_full=False,
        )
        self.minimap_canvas.configure(yscrollcommand=self.minimap_scrollbar.set)
        self.minimap_canvas.grid(row=0, column=0, sticky="nsew")
        self.minimap_scrollbar.grid(row=0, column=1, sticky="ns")
        minimap_canvas_frame.columnconfigure(0, weight=1)
        minimap_canvas_frame.rowconfigure(0, weight=1)
        self.minimap_canvas.bind("<MouseWheel>", self._scroll_detail_minimap, add="+")
        self._canvas_tip = HoverTip(self.minimap_canvas)
        minimap_meta = tk.Frame(minimap_body, bg=PANEL, padx=8)
        minimap_meta.pack(side="left", fill="both", expand=True)
        self.minimap_meta_rows = {
            "件数": self._meta_row(minimap_meta, "件数"),
            "来源": self._meta_row(minimap_meta, "来源"),
            "品质": self._meta_row(minimap_meta, "品质"),
            "范围": self._meta_row(minimap_meta, "范围"),
        }
        self.details_card.pack(fill="x", pady=(5, 0))
        self.minimap_card.pack(fill="x", pady=(5, 0))
        self.footer_row = tk.Frame(self.shell, bg=BG)
        self.footer_row.pack(fill="x", pady=(1, 0))
        self.footer = tk.Label(
            self.footer_row,
            text=f"{CREDIT_TEXT} · ",
            bg=BG,
            fg=DIM,
            font=(FONT_UI, 6),
            anchor="w",
        )
        self.footer.pack(side="left")
        self.footer_github = tk.Label(
            self.footer_row,
            text="GitHub",
            bg=BG,
            fg=ACCENT,
            activeforeground=WARM,
            font=(FONT_UI, 6, "underline"),
            anchor="w",
            padx=0,
        )
        try:
            self.footer_github.configure(cursor="hand2")
        except tk.TclError:
            pass
        self.footer_github.pack(side="left", fill="x", expand=True)
        self.footer_github.bind("<Button-1>", self._open_credit_github, add="+")
        self.footer_github_tip = HoverTip(self.footer_github, GITHUB_TIP_TEXT)
        self.resize_grip = tk.Label(
            self.footer_row,
            text="◢",
            bg=BG,
            fg=BORDER,
            font=(FONT_UI, 8, "bold"),
            padx=2,
        )
        try:
            self.resize_grip.configure(cursor="sizing")
        except tk.TclError:
            pass
        self.resize_grip.pack(side="right")
        self.resize_grip.bind("<ButtonPress-1>", self._begin_resize, add="+")
        self.resize_grip.bind("<B1-Motion>", self._resize_window, add="+")
        self.resize_grip.bind("<ButtonRelease-1>", self._end_resize, add="+")

        self._bind_drag_recursive(
            self.outer,
            exclude={
                self.close_button,
                self.topmost_button,
                self.mode_button,
                self.manual_button,
                self.theme_button,
                self.map_button,
                self.settlement_button,
                self.export_diag_button,
                self.top_resize_grip,
                self.resize_grip,
                self.footer_github,
            },
        )
        self._set_topmost_button_state()
        self._scaled_layout_specs = [
            (self.shell, {"padx": 9, "pady": 9}),
        ]
        self._capture_ui_font_bases(self.outer)
        if self._ui_prefs_enabled and self._load_ui_prefs():
            pass
        else:
            self._set_details_mode(False)
        self._apply_pending_window_position()
        root.protocol("WM_DELETE_WINDOW", self._on_user_close)
        self._start_ui_health_watchdog()
        if self._load_existing_snapshot:
            self.refresh()
        else:
            self._last_signature = self._snapshot_signature()
            self.render_missing("等待新局实时包")
            self.root.after(self.interval_ms, self.refresh)

    def _details_geometry(self) -> str:
        if self._custom_details_size is not None:
            width, height = self._custom_details_size
            return f"{width}x{height}"
        width, height = self._details_content_size()
        return f"{width}x{height}"

    def _details_content_size(self, *, width: int | None = None) -> tuple[int, int]:
        work_w, work_h = self._screen_size()
        self.root.update_idletasks()
        if width is None:
            width, _ = self._current_window_size()
        requested_w = int(self.outer.winfo_reqwidth()) if hasattr(self, "outer") else int(width)
        width = min(760, max(430, int(width), requested_w + 12, int(work_w * 0.44)))
        width = min(width, max(430, work_w - 40))
        height = self._measure_window_height_for_width(width)
        height = min(height, max(320, work_h - 72))
        return width, height

    def _fit_details_window_to_content(self, *, width: int | None = None) -> None:
        if not hasattr(self, "root"):
            return
        if width is None:
            width, _ = self._current_window_size()
        width = max(430, min(1200, int(width)))
        # Apply details typography before measuring so height matches final scale.
        self._ui_scale = compute_ui_scale(
            width,
            DETAILS_BASE_HEIGHT,
            base_width=DETAILS_BASE_WIDTH,
            base_height=DETAILS_BASE_HEIGHT,
        )
        self._apply_ui_scale()
        self.root.update_idletasks()
        self._custom_details_size = None
        fitted_width, fitted_height = self._details_content_size(width=width)
        self._apply_window_geometry(f"{fitted_width}x{fitted_height}", flush=False)
        self._sync_ui_scale_from_window(force=True)
        self.root.update_idletasks()
        refined_width, refined_height = self._details_content_size(width=fitted_width)
        if abs(refined_height - fitted_height) > 4:
            self._apply_window_geometry(f"{refined_width}x{refined_height}")

    def _load_ui_prefs(self) -> bool:
        prefs = read_ui_prefs(self._ui_prefs_path)
        if prefs is None:
            return False
        self._apply_ui_prefs_payload(prefs)
        return True

    def _apply_ui_prefs_payload(self, prefs: dict[str, Any]) -> None:
        mini_size = prefs.get("custom_mini_size")
        if isinstance(mini_size, (list, tuple)) and len(mini_size) == 2:
            self._custom_mini_size = (int(mini_size[0]), int(mini_size[1]))
        details_size = prefs.get("custom_details_size")
        if isinstance(details_size, (list, tuple)) and len(details_size) == 2:
            self._custom_details_size = (int(details_size[0]), int(details_size[1]))
        position = prefs.get("window_position")
        if isinstance(position, (list, tuple)) and len(position) == 2:
            try:
                self._pending_window_position = (int(position[0]), int(position[1]))
            except (TypeError, ValueError):
                self._pending_window_position = None
        theme_name = str(prefs.get("theme_name") or "dark")
        if theme_name and theme_name != self.theme_name:
            self.apply_theme(theme_name)
        expanded = bool(prefs.get("details_expanded"))
        self._set_details_mode(expanded)

    def _apply_pending_window_position(self) -> None:
        pending = self._pending_window_position
        if pending is None:
            return
        width, height = self._current_window_size()
        self.root.geometry(f"{width}x{height}+{pending[0]}+{pending[1]}")
        self.root.update_idletasks()
        self._pending_window_position = None

    def _collect_ui_prefs_payload(self) -> dict[str, Any]:
        width, height = self._current_window_size()
        geo = str(self.root.geometry() or "")
        window_position: list[int] | None = None
        if "+" in geo:
            parts = geo.split("+")
            if len(parts) >= 3:
                try:
                    window_position = [int(parts[1]), int(parts[2])]
                except ValueError:
                    window_position = None
        return {
            "schema_version": UI_PREFS_SCHEMA_VERSION,
            "theme_name": str(getattr(self, "theme_name", "dark") or "dark"),
            "details_expanded": bool(self.details_expanded),
            "ui_scale": round(float(self._ui_scale), 4),
            "window_position": window_position,
            "custom_mini_size": list(self._custom_mini_size) if self._custom_mini_size else None,
            "custom_details_size": list(self._custom_details_size) if self._custom_details_size else None,
            "window_size": [width, height],
        }

    def _save_ui_prefs_if_enabled(self) -> None:
        if not getattr(self, "_ui_prefs_enabled", False):
            return
        self._ui_prefs_save_after_id = None
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            if not root.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            write_ui_prefs(self._ui_prefs_path, self._collect_ui_prefs_payload())
        except (OSError, tk.TclError):
            pass

    def _schedule_ui_prefs_save(self) -> None:
        if not getattr(self, "_ui_prefs_enabled", False) or not hasattr(self, "root"):
            return
        if self._ui_prefs_save_after_id is not None:
            try:
                self.root.after_cancel(self._ui_prefs_save_after_id)
            except tk.TclError:
                pass
        self._ui_prefs_save_after_id = self.root.after(
            UI_PREFS_SAVE_DEBOUNCE_MS,
            self._save_ui_prefs_if_enabled,
        )

    def _estimate_mini_content_height(self) -> int:
        self.root.update_idletasks()
        return compute_fitted_mini_height(int(self.shell.winfo_reqheight()))

    def _geometry_position_suffix(self) -> str:
        geo = str(self.root.geometry() or "")
        if "+" not in geo:
            return ""
        return "+" + geo.split("+", 1)[1]

    def _apply_window_geometry(self, size: str, *, flush: bool = True) -> None:
        self.root.geometry(f"{size}{self._geometry_position_suffix()}")
        if flush:
            self.root.update_idletasks()

    def _measure_window_height_for_width(self, width: int, *, probe_height: int | None = None) -> int:
        width = max(430, min(1200, int(width)))
        suffix = self._geometry_position_suffix()
        _, current_height = self._current_window_size()
        if probe_height is None:
            probe_height = max(320, current_height)
        else:
            probe_height = max(320, min(1500, int(probe_height)))
        self.root.geometry(f"{width}x{probe_height}{suffix}")
        self.root.update_idletasks()
        measured = max(320, int(self.root.winfo_reqheight()))
        return min(1500, measured)

    def _default_mini_size(self) -> tuple[int, int]:
        if hasattr(self, "outer"):
            self.root.update_idletasks()
            width = max(430, min(760, int(self.outer.winfo_reqwidth()) + 12))
            height = self._measure_window_height_for_width(width)
            return width, height
        return MINI_BASE_WIDTH, MINI_BASE_HEIGHT

    def _fit_mini_window_to_content(self) -> None:
        if self.details_expanded or not hasattr(self, "shell"):
            return
        width, _ = self._current_window_size()
        self._apply_mini_resize_layout(width)

    def _apply_mini_resize_layout(self, width: int, *, finalize: bool = False) -> None:
        if self.details_expanded or not hasattr(self, "shell"):
            return
        width = max(430, min(1200, int(width)))
        next_scale = compute_mini_ui_scale(width)
        self._queue_ui_scale(next_scale, force=finalize)
        if finalize:
            _, preserve_height = self._current_window_size()
            fitted_height = self._measure_window_height_for_width(width, probe_height=preserve_height)
        else:
            fitted_height = self._estimate_mini_content_height()
        self._custom_mini_size = (width, fitted_height)
        self._apply_window_geometry(
            f"{width}x{fitted_height}",
            flush=finalize or not getattr(self, "_resize_active", False),
        )

    def _remember_mini_layout_snapshot(self) -> None:
        width, height = self._current_window_size()
        self._mini_layout_snapshot = (
            self._custom_mini_size,
            (width, height),
            float(self._ui_scale),
        )

    def _reset_ui_scale_baseline(self) -> None:
        self._ui_scale = 1.0
        self._apply_ui_scale()

    def _restore_mini_layout_after_details(self) -> None:
        snapshot = self._mini_layout_snapshot
        self._custom_details_size = None
        if snapshot is not None:
            custom_size, saved_size, _saved_scale = snapshot
            self._custom_mini_size = custom_size
        else:
            custom_size = None
            saved_size = (MINI_BASE_WIDTH, MINI_BASE_HEIGHT)

        self.mode_button.configure(text="详情")
        self.root.minsize(430, 395)
        self.details_card.pack_forget()
        self.minimap_card.pack_forget()

        if custom_size is not None:
            width = int(custom_size[0])
        else:
            width = int(saved_size[0])
        self._apply_mini_resize_layout(width, finalize=True)

    def _mini_geometry(self) -> str:
        if self._custom_mini_size is not None:
            width, height = self._custom_mini_size
        else:
            width, height = self._default_mini_size()
        return f"{width}x{height}"

    def _screen_size(self) -> tuple[int, int]:
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                rect = wintypes.RECT()
                if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                    work_w = int(rect.right - rect.left)
                    work_h = int(rect.bottom - rect.top)
                    if work_w > 0 and work_h > 0:
                        return work_w, work_h
            except Exception:
                pass
        return max(1, int(self.root.winfo_screenwidth())), max(1, int(self.root.winfo_screenheight()))

    def _bind_drag(self, *widgets: tk.Widget) -> None:
        for widget in widgets:
            widget.bind("<ButtonPress-1>", self._begin_drag, add="+")
            widget.bind("<B1-Motion>", self._drag_window, add="+")
            widget.bind("<ButtonRelease-1>", self._end_drag, add="+")

    def _bind_drag_recursive(self, widget: tk.Widget, *, exclude: set[tk.Widget]) -> None:
        if widget in exclude:
            return
        interactive = (tk.Button, ttk.Button, tk.Entry, tk.Canvas, tk.Scale, tk.Scrollbar)
        if not isinstance(widget, interactive):
            self._bind_drag(widget)
        for child in widget.winfo_children():
            self._bind_drag_recursive(child, exclude=exclude)

    def _begin_drag(self, event: tk.Event[Any]) -> None:
        self._drag_offset = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def _drag_window(self, event: tk.Event[Any]) -> None:
        if self._drag_offset is None:
            return
        dx, dy = self._drag_offset
        next_x = event.x_root - dx
        next_y = event.y_root - dy
        self.root.geometry(f"+{next_x}+{next_y}")
        self._sync_pinned_minimap_position(root_x=next_x, root_y=next_y)

    def _end_drag(self, _event: tk.Event[Any]) -> None:
        self._drag_offset = None
        self._schedule_ui_prefs_save()

    def _begin_resize(self, event: tk.Event[Any]) -> str:
        self._resize_active = True
        width0, height0 = self._current_window_size()
        self._resize_anchor = (
            event.x_root,
            event.y_root,
            width0,
            height0,
        )
        return "break"

    def _resize_window(self, event: tk.Event[Any]) -> str:
        if self._resize_anchor is None:
            return "break"
        x0, y0, width0, height0 = self._resize_anchor
        dx = int(event.x_root - x0)
        dy = int(event.y_root - y0)
        if self.details_expanded:
            width = max(430, min(1200, width0 + dx))
            height = max(320, min(1500, height0 + dy))
            self._custom_details_size = (width, height)
            self._apply_window_geometry(f"{width}x{height}", flush=False)
            next_scale = compute_ui_scale(
                width,
                height,
                base_width=DETAILS_BASE_WIDTH,
                base_height=DETAILS_BASE_HEIGHT,
            )
            self._queue_ui_scale(next_scale, force=False)
        else:
            growth = mini_resize_growth(dx, dy)
            width = max(430, min(1200, width0 + growth))
            self._apply_mini_resize_layout(width)
        return "break"

    def _cancel_live_ui_scale_timer(self) -> None:
        after_id = getattr(self, "_live_scale_after_id", None)
        if after_id is not None:
            try:
                self.root.after_cancel(after_id)
            except tk.TclError:
                pass
            self._live_scale_after_id = None

    def _apply_pending_ui_scale(self, *, force: bool = False) -> None:
        self._live_scale_after_id = None
        pending = getattr(self, "_live_scale_pending", None)
        if pending is None and not force:
            return
        next_scale = float(pending if pending is not None else self._ui_scale)
        self._live_scale_pending = None
        if force or abs(next_scale - float(self._ui_scale)) >= UI_SCALE_LIVE_DELTA:
            self._ui_scale = next_scale
            self._apply_ui_scale()
            self._live_scale_last_at = time.monotonic()

    def _apply_pending_ui_scale_after(self) -> None:
        self._apply_pending_ui_scale(force=False)
        if getattr(self, "_live_scale_pending", None) is not None and getattr(self, "_resize_active", False):
            self._live_scale_after_id = self.root.after(
                UI_SCALE_LIVE_INTERVAL_MS,
                self._apply_pending_ui_scale_after,
            )

    def _queue_ui_scale(self, next_scale: float, *, force: bool = False) -> None:
        next_scale = float(next_scale)
        if force or not getattr(self, "_resize_active", False):
            self._live_scale_pending = None
            self._cancel_live_ui_scale_timer()
            if force or abs(next_scale - float(self._ui_scale)) >= UI_SCALE_LIVE_DELTA:
                self._ui_scale = next_scale
                self._apply_ui_scale()
                self._live_scale_last_at = time.monotonic()
            return
        self._live_scale_pending = next_scale
        elapsed_ms = (time.monotonic() - float(getattr(self, "_live_scale_last_at", 0.0))) * 1000.0
        if elapsed_ms >= UI_SCALE_LIVE_INTERVAL_MS:
            self._apply_pending_ui_scale(force=False)
            return
        if getattr(self, "_live_scale_after_id", None) is None:
            delay = max(1, int(UI_SCALE_LIVE_INTERVAL_MS - elapsed_ms))
            self._live_scale_after_id = self.root.after(
                delay,
                self._apply_pending_ui_scale_after,
            )

    def _end_resize(self, _event: tk.Event[Any]) -> str:
        self._resize_anchor = None
        self._resize_active = False
        self._cancel_live_ui_scale_timer()
        self._live_scale_pending = None
        self.root.update_idletasks()
        if self.details_expanded:
            self._sync_ui_scale_from_window(force=True)
        else:
            width, _ = self._current_window_size()
            self._apply_mini_resize_layout(width, finalize=True)
        self._schedule_ui_prefs_save()
        return "break"

    def _ui_scale_base_geometry(self) -> tuple[int, int]:
        if self.details_expanded:
            return DETAILS_BASE_WIDTH, DETAILS_BASE_HEIGHT
        return MINI_BASE_WIDTH, MINI_BASE_HEIGHT

    def _scaled_padding(self, value: int) -> int:
        return max(1, int(round(int(value) * float(self._ui_scale))))

    def _capture_ui_font_bases(self, widget: tk.Widget) -> None:
        font_widgets = (
            tk.Label,
            tk.Button,
            tk.Entry,
            tk.Text,
            tk.Checkbutton,
            tk.Radiobutton,
        )
        if isinstance(widget, font_widgets):
            if not hasattr(widget, "_ahmad_font_base"):
                spec = font_spec_from_widget(widget)
                if spec is not None:
                    widget._ahmad_font_base = spec  # type: ignore[attr-defined]
        for child in widget.winfo_children():
            self._capture_ui_font_bases(child)

    def _apply_font_scale(self, widget: tk.Widget) -> None:
        font_widgets = (
            tk.Label,
            tk.Button,
            tk.Entry,
            tk.Text,
            tk.Checkbutton,
            tk.Radiobutton,
        )
        if isinstance(widget, font_widgets):
            base = getattr(widget, "_ahmad_font_base", None)
            if base is None and abs(float(self._ui_scale) - 1.0) < 0.05:
                base = font_spec_from_widget(widget)
                if base is not None:
                    widget._ahmad_font_base = base  # type: ignore[attr-defined]
            base = getattr(widget, "_ahmad_font_base", None)
            if base is not None:
                family, size, *styles = base
                widget.configure(font=scaled_font(family, int(size), *styles, scale=self._ui_scale))
        for child in widget.winfo_children():
            if not self.details_expanded and hasattr(self, "details_card"):
                if child in (self.details_card, self.minimap_card):
                    continue
            self._apply_font_scale(child)

    def _apply_layout_scale(self) -> None:
        for widget, options in self._scaled_layout_specs:
            if not widget.winfo_exists():
                continue
            widget.configure(
                **{
                    key: self._scaled_padding(value)
                    for key, value in options.items()
                }
            )

    def _apply_button_style_scale(self) -> None:
        pad_x, pad_y = HERO_BUTTON_PADDING_BASE
        self.style.configure(
            "Hero.TButton",
            font=scaled_font(FONT_UI, HERO_BUTTON_FONT_SIZE, scale=self._ui_scale),
            padding=(self._scaled_padding(pad_x), self._scaled_padding(pad_y)),
        )

    def _apply_ui_scale(self) -> None:
        self._apply_layout_scale()
        self._apply_button_style_scale()
        self._apply_font_scale(self.outer)
        if self.details_expanded and self._minimap_data:
            self._render_minimap(self._minimap_data)

    def _current_window_size(self) -> tuple[int, int]:
        geo = str(self.root.geometry() or "")
        size_part = geo.split("+", 1)[0]
        if "x" in size_part:
            try:
                parsed_w, parsed_h = size_part.split("x", 1)
                return max(1, int(parsed_w)), max(1, int(parsed_h))
            except ValueError:
                pass
        width = max(1, int(self.root.winfo_width() or 0))
        height = max(1, int(self.root.winfo_height() or 0))
        if width >= 200 and height >= 200:
            return width, height
        if self.details_expanded:
            return DETAILS_BASE_WIDTH, DETAILS_BASE_HEIGHT
        return self._default_mini_size()

    def _sync_ui_scale_from_window(self, *, force: bool = False) -> None:
        if not hasattr(self, "root"):
            return
        width, height = self._current_window_size()
        if self.details_expanded:
            base_w, base_h = self._ui_scale_base_geometry()
            next_scale = compute_ui_scale(
                width,
                height,
                base_width=base_w,
                base_height=base_h,
            )
        else:
            next_scale = compute_mini_ui_scale(width)
        scale_changed = abs(next_scale - self._ui_scale) >= 0.02
        if force or scale_changed:
            self._queue_ui_scale(next_scale, force=force)

    def _configure_theme_style(self) -> None:
        self.style.configure(
            "Hero.TButton",
            background=PANEL_SOFT,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=PANEL_SOFT,
            darkcolor=PANEL_SOFT,
        )
        self.style.map("Hero.TButton", background=[("active", HERO_BUTTON_ACTIVE)])
        self._apply_button_style_scale()

    def _replace_theme_colors(self, widget: tk.Widget, replacements: dict[str, str]) -> None:
        for option in (
            "bg",
            "background",
            "fg",
            "foreground",
            "activebackground",
            "activeforeground",
            "highlightbackground",
            "highlightcolor",
            "insertbackground",
            "selectbackground",
            "selectforeground",
        ):
            try:
                current = str(widget.cget(option)).lower()
            except tk.TclError:
                continue
            replacement = replacements.get(current)
            if replacement:
                try:
                    widget.configure(**{option: replacement})
                except tk.TclError:
                    pass
        for child in widget.winfo_children():
            self._replace_theme_colors(child, replacements)

    def _show_theme_menu(self, event: tk.Event[Any] | None = None) -> str:
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL_SOFT,
            activeforeground=TEXT,
            borderwidth=0,
            activeborderwidth=0,
        )
        for name in THEME_ORDER:
            label = "随机抽色" if name == "random" else str(THEMES[name]["label"])
            menu.add_command(label=label, command=lambda choice=name: self.apply_theme(choice))
        x = self.theme_button.winfo_rootx()
        y = self.theme_button.winfo_rooty() + self.theme_button.winfo_height() + 2
        if event is not None:
            x = event.x_root
            y = event.y_root + 8
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
        return "break"

    def apply_theme(self, name: str) -> None:
        old_theme = self.theme_values
        new_theme = _theme_by_name(name)
        self.theme_name = name
        self.theme_values = new_theme
        _apply_theme_globals(new_theme)
        replacements = _theme_replacements(old_theme, new_theme)
        self._configure_theme_style()
        self._replace_theme_colors(self.root, replacements)
        if self._minimap_popup is not None:
            self._replace_theme_colors(self._minimap_popup, replacements)
        if self._pinned_minimap_popup is not None:
            self._replace_theme_colors(self._pinned_minimap_popup, replacements)
        label = "随机" if name == "random" else str(new_theme.get("label") or name)
        self.theme_tip.set_text(f"{THEME_TIP_PREFIX}：{label}")
        self._set_manual_button_state()
        self._set_topmost_button_state()
        data = self._last_summary or self._last_live_summary
        if data:
            if data.get("status") == "stale_snapshot":
                self.render_standby(data)
            else:
                self.render(data)
        else:
            self.render_missing("等待 latest_snapshot.json")
        self._redraw_minimap_popup()
        self._redraw_pinned_minimap()
        self._schedule_ui_prefs_save()

    def _on_user_close(self) -> None:
        self._hide_minimap_popup()
        self._hide_pinned_minimap()
        self._save_ui_prefs_if_enabled()
        self._run_exit_cleanup()
        self.root.destroy()

    def _apply_topmost_state_to_windows(self) -> None:
        enabled = bool(getattr(self, "topmost_enabled", True))
        for window in (self.root, self._minimap_popup, self._pinned_minimap_popup):
            if window is None:
                continue
            try:
                window.attributes("-topmost", enabled)
            except tk.TclError:
                pass

    def _set_topmost_button_state(self) -> None:
        if not hasattr(self, "topmost_button"):
            return
        enabled = bool(getattr(self, "topmost_enabled", True))
        self.topmost_button.configure(
            text="T",
            fg=WARM if enabled else DIM,
            bg=PANEL_MUTED if enabled else PANEL_SOFT,
            highlightbackground=WARM if enabled else BORDER,
        )
        if hasattr(self, "topmost_tip"):
            self.topmost_tip.set_text(TOPMOST_ON_TIP if enabled else TOPMOST_OFF_TIP)

    def toggle_topmost(self, _event: tk.Event[Any] | None = None) -> str:
        self.topmost_enabled = not bool(getattr(self, "topmost_enabled", True))
        self._apply_topmost_state_to_windows()
        self._set_topmost_button_state()
        return "break"

    def _open_credit_github(self, _event: tk.Event[Any] | None = None) -> None:
        webbrowser.open(CREDIT_GITHUB_URL, new=2, autoraise=True)

    def export_diagnostic_package(self, _event: tk.Event[Any] | None = None) -> str:
        export_started = time.perf_counter()
        snapshot = self._last_live_snapshot or _read_json(self.snapshot_path)
        if not snapshot:
            snapshot = {
                "schema_version": None,
                "created_at": time.time(),
                "session_id": "no_snapshot",
                "phase": "missing_snapshot",
                "file": None,
                "ui_contract": {
                    "context": {
                        "phase": "missing_snapshot",
                        "session_id": "no_snapshot",
                    },
                },
            }
        current_summary = self._last_summary or self._last_live_summary or {}
        try:
            export_path = _write_diagnostic_export(
                snapshot=snapshot,
                snapshot_path=self.snapshot_path,
                current_summary=current_summary,
                diagnostic_profile=getattr(
                    self,
                    "diagnostic_profile",
                    DEFAULT_DIAGNOSTIC_PROFILE,
                ),
                show_taskbar=bool(getattr(self, "show_taskbar", False)),
            )
            if isinstance(current_summary, dict):
                self._mark_summary_performance(
                    current_summary,
                    "export_ms",
                    export_started,
                )
        except Exception as exc:  # noqa: BLE001 - keep UI usable
            if hasattr(self, "export_diag_tip"):
                self.export_diag_tip.set_text(f"导出失败: {exc}")
            if hasattr(self, "status"):
                self.status.configure(text="导出失败")
            return "break"
        self.last_diagnostic_export_path = export_path
        if hasattr(self, "export_diag_tip"):
            self.export_diag_tip.set_text(f"已导出: {export_path.resolve()}")
        if hasattr(self, "status"):
            self.status.configure(text="已导出诊断")
        if hasattr(self, "manual_status"):
            self.manual_status.configure(text=f"诊断包: {export_path.name}", fg=ACCENT)
        return "break"

    def _run_exit_cleanup(self) -> None:
        if self._exit_cleanup_done:
            return
        self._exit_cleanup_done = True
        if getattr(self, "keep_monitor_on_close", False):
            return
        pids = list(getattr(self, "_stop_pids_on_exit", ()))
        lock_paths = list(getattr(self, "_cleanup_lock_paths", ()))
        monitor_lock = _monitor_lock_path(self.snapshot_path)
        fallback_pid = _pid_from_monitor_lock(monitor_lock)
        if fallback_pid and fallback_pid not in pids:
            pids.append(fallback_pid)
        if monitor_lock not in lock_paths:
            lock_paths.append(monitor_lock)
        _cleanup_exit_targets(tuple(pids), tuple(lock_paths))

    def _scroll_detail_minimap(self, event: tk.Event[Any]) -> str:
        delta = -1 if event.delta > 0 else 1
        self.minimap_canvas.yview_scroll(delta, "units")
        return "break"

    def _scroll_pinned_minimap(self, event: tk.Event[Any]) -> str:
        if self._pinned_canvas is None:
            return "break"
        delta = -1 if event.delta > 0 else 1
        self._pinned_canvas.yview_scroll(delta, "units")
        return "break"

    def _set_manual_button_state(self) -> None:
        if not hasattr(self, "manual_button"):
            return
        manual_mode = bool(self._manual_active or getattr(self, "_manual_edit_enabled", False))
        if manual_mode:
            self.manual_button.configure(
                text="实时",
                bg="#ffe1a8",
                fg=BUTTON_DARK_FG,
                highlightbackground="#fff0c4",
            )
            if hasattr(self, "manual_tip"):
                self.manual_tip.set_text(MANUAL_RETURN_TIP_TEXT)
        else:
            self.manual_button.configure(
                text="手填",
                bg=WARM,
                fg=BUTTON_DARK_FG,
                highlightbackground=WARM,
            )
            if hasattr(self, "manual_tip"):
                self.manual_tip.set_text(MANUAL_TIP_TEXT)

    def _set_manual_edit_enabled(self, enabled: bool) -> None:
        self._manual_edit_enabled = bool(enabled)
        if hasattr(self, "manual_entries"):
            state = "normal" if enabled else "disabled"
            for entry in self.manual_entries.values():
                try:
                    entry.configure(
                        state=state,
                        disabledbackground=PANEL_SOFT,
                        disabledforeground=DIM,
                    )
                except tk.TclError:
                    pass
                except AttributeError:
                    pass
        if hasattr(self, "manual_buttons"):
            for label, button in self.manual_buttons.items():
                target_state = "normal"
                if label in {"应用并启用", "填入当前"} and not enabled:
                    target_state = "disabled"
                if label == "清结算":
                    target_state = "disabled"
                try:
                    button.configure(state=target_state)
                except tk.TclError:
                    pass
                except AttributeError:
                    pass
        self._set_manual_settlement_button_state()
        self._set_manual_button_state()

    def _set_manual_settlement_button_state(self) -> None:
        if not hasattr(self, "manual_buttons"):
            return
        button = self.manual_buttons.get("清结算")
        if button is None:
            return
        data = self._last_summary or self._last_live_summary or {}
        active = self._is_settlement_summary(data)
        enabled = bool(active and getattr(self, "_manual_edit_enabled", False))
        try:
            button.configure(
                state="normal" if enabled else "disabled",
                fg=ACCENT if enabled else DIM,
                bg=MANUAL_BG,
                highlightbackground=ACCENT if enabled else BORDER,
            )
        except tk.TclError:
            pass
        except AttributeError:
            pass
        if hasattr(self, "manual_clear_settlement_tip"):
            self.manual_clear_settlement_tip.set_text(
                MANUAL_CLEAR_SETTLEMENT_TIP
                if active
                else MANUAL_CLEAR_SETTLEMENT_INACTIVE_TIP
            )

    def _is_settlement_summary(self, data: dict[str, Any]) -> bool:
        context = data.get("context") if isinstance(data.get("context"), dict) else {}
        truth = data.get("truth") if isinstance(data.get("truth"), dict) else {}
        return _text(context.get("phase"), "") == "settled" and bool(truth.get("available"))

    def _settlement_values_are_hidden(self, data: dict[str, Any]) -> bool:
        return bool(getattr(self, "settlement_values_hidden", False) and self._is_settlement_summary(data))

    def _settlement_display_value(self, data: dict[str, Any], value: Any) -> str:
        return "已隐藏" if self._settlement_values_are_hidden(data) else _text(value)

    def _set_settlement_button_state(self, data: dict[str, Any] | None = None) -> None:
        if not hasattr(self, "settlement_button"):
            return
        hidden = bool(getattr(self, "settlement_values_hidden", False))
        self.settlement_button.configure(
            text="显价" if hidden else "藏价",
            fg=WARM if hidden else ACCENT,
            bg=PANEL_MUTED if hidden else PANEL_SOFT,
            highlightbackground=WARM if hidden else BORDER,
        )
        if hasattr(self, "settlement_tip"):
            self.settlement_tip.set_text(SETTLEMENT_SHOW_TIP if hidden else SETTLEMENT_HIDE_TIP)

    def toggle_settlement_values(self, _event: tk.Event[Any] | None = None) -> str:
        data = self._last_summary or self._last_live_summary or {}
        self.settlement_values_hidden = not bool(getattr(self, "settlement_values_hidden", False))
        self._set_settlement_button_state(data)
        if self._is_settlement_summary(data):
            self.render(data)
        return "break"

    def toggle_manual_mode(self, _event: tk.Event[Any] | None = None) -> str:
        if self._manual_active or getattr(self, "_manual_edit_enabled", False):
            return self.return_to_live_mode()
        return self.open_manual_panel()

    def open_manual_panel(self, _event: tk.Event[Any] | None = None) -> str:
        # Remember whether entering manual auto-expanded the panel so that
        # returning to live can symmetrically collapse back to mini. If the user
        # had already expanded details on their own, leave that state untouched.
        auto_expanded = not self.details_expanded
        if auto_expanded:
            self.toggle_details()
        self._manual_auto_expanded_details = auto_expanded
        data = self._last_summary or self._last_live_summary or {}
        should_prefill_empty = (
            hasattr(self, "manual_entries")
            and not self._has_manual_inputs()
            and not bool(getattr(self, "_manual_dirty_fields", set()))
            and not bool(getattr(self, "_manual_autofill_values", {}))
            and any(
                value not in (None, "")
                for value in self._manual_values_from_summary(data).values()
            )
        )
        settlement_edit = self._is_settlement_summary(data)
        if settlement_edit:
            self._manual_settlement_edit_unlocked = True
            if not _text(getattr(self, "_manual_live_session_id", ""), "").strip():
                self._manual_live_session_id = self._summary_session_id(data)
        self._set_manual_edit_enabled(True)
        prefilled = False
        if should_prefill_empty:
            self.prefill_manual_inputs()
            prefilled = self._has_manual_inputs()
        if hasattr(self, "manual_status") and not prefilled:
            self.manual_status.configure(
                text="结算页手填，待填写" if settlement_edit else "手动模式，待填写",
                fg=WARM,
            )
        if hasattr(self, "manual_card"):
            self.manual_card.configure(highlightbackground=WARM, highlightthickness=2)
        self._set_manual_settlement_button_state()
        return "break"

    def return_to_live_mode(self, _event: tk.Event[Any] | None = None) -> str:
        self._manual_active = False
        self._manual_settlement_edit_unlocked = False
        self._manual_snapshot = {}
        self._manual_summary = {}
        self._set_manual_edit_enabled(False)
        if self._last_live_summary:
            self._auto_sync_manual_inputs(self._last_live_summary)
        if hasattr(self, "manual_status"):
            self.manual_status.configure(text="实时模式，手填保留", fg=DIM)
        self._restore_manual_card_border()
        # Collapse back to mini only if entering manual auto-expanded the panel
        # (mirrors open_manual_panel, which expands via toggle_details).
        if getattr(self, "_manual_auto_expanded_details", False):
            self._manual_auto_expanded_details = False
            if self.details_expanded:
                self.toggle_details()
        if self._last_live_summary:
            self._last_summary = self._last_live_summary
            if self._last_live_summary.get("status") == "stale_snapshot":
                self.render_standby(self._last_live_summary)
            else:
                self.render(self._last_live_summary)
        else:
            self._last_summary = {}
            self.render_missing("等待 latest_snapshot.json")
        return "break"

    def _restore_manual_card_border(self) -> None:
        if hasattr(self, "manual_card"):
            self.manual_card.configure(highlightbackground=BORDER, highlightthickness=1)

    def _meta_row(self, parent: tk.Widget, label: str) -> tk.Label:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=(0, 6))
        tk.Label(
            row,
            text=label,
            bg=PANEL,
            fg=DIM,
            font=(FONT_UI, 7),
            anchor="w",
            width=4,
        ).pack(side="left")
        value = tk.Label(
            row,
            text="-",
            bg=PANEL,
            fg=TEXT,
            font=(FONT_UI, 8, "bold"),
            anchor="w",
            justify="left",
            wraplength=230,
        )
        value.pack(side="left", fill="x", expand=True)
        return value

    def _build_manual_panel(self, parent: tk.Widget) -> None:
        manual_bg = MANUAL_BG
        manual_input_bg = MANUAL_INPUT_BG
        card = self._card(parent, bg=manual_bg, padx=7, pady=7)
        self.manual_card = card
        card.pack(fill="x", pady=(5, 0))
        tk.Frame(card, bg=WARM, height=2).pack(fill="x", pady=(0, 4))
        header = tk.Frame(card, bg=manual_bg)
        header.pack(fill="x", pady=(0, 4))
        title_box = tk.Frame(header, bg=manual_bg)
        title_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_box,
            text="手动填写 / 断网备用",
            bg=manual_bg,
            fg=WARM,
            font=(FONT_UI, 8, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_box,
            text="可只填总件/总格；补均格/件数/均价/总价会进一步锁定",
            bg=manual_bg,
            fg=MUTED,
            font=(FONT_UI, 6),
            anchor="w",
        ).pack(fill="x", pady=(1, 0))
        self.manual_status = tk.Label(
            header,
            text="未启用",
            bg=MANUAL_STATUS_BG,
            fg=WARM,
            padx=7,
            pady=2,
            font=(FONT_UI, 7),
            anchor="e",
        )
        self.manual_status.pack(side="right")

        self.manual_entries: dict[str, tk.Entry] = {}
        self.manual_vars: dict[str, tk.StringVar] = {}
        self.manual_buttons: dict[str, tk.Button] = {}
        buttons = tk.Frame(card, bg=manual_bg)
        buttons.pack(fill="x", pady=(0, 5))
        for text, command, color in (
            ("应用并启用", self.apply_manual_inputs, WARM),
            ("填入当前", self.prefill_manual_inputs, ACCENT),
            ("清空手动", self.clear_manual_inputs, DIM),
            ("清结算", self.clear_settlement_manual_values, DIM),
        ):
            is_primary = text == "应用并启用"
            button = tk.Button(
                buttons,
                text=text,
                command=command,
                bg=WARM if is_primary else manual_bg,
                fg=BUTTON_DARK_FG if is_primary else color,
                activebackground="#ffd08d" if is_primary else HERO_BUTTON_ACTIVE,
                activeforeground=BUTTON_DARK_FG if is_primary else TEXT,
                relief="flat",
                borderwidth=0,
                padx=9 if is_primary else 7,
                pady=3 if is_primary else 2,
                font=(FONT_UI, 8, "bold"),
                highlightthickness=1,
                highlightbackground=WARM if is_primary else BORDER,
            )
            button.pack(side="left", padx=(0, 6))
            self.manual_buttons[text] = button
            if text == "清结算":
                self.manual_clear_settlement_tip = HoverTip(
                    button,
                    MANUAL_CLEAR_SETTLEMENT_INACTIVE_TIP,
                )

        form = tk.Frame(card, bg=manual_bg)
        form.pack(fill="x")

        def add_manual_entry(parent: tk.Widget, key: str, default: str = "") -> tk.Entry:
            var = tk.StringVar(value=default)
            entry = tk.Entry(
                parent,
                width=6,
                textvariable=var,
                bg=manual_input_bg,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                borderwidth=0,
                font=(FONT_UI, 8),
                justify="center",
            )
            entry.pack(fill="x", expand=True)
            entry.bind(
                "<KeyRelease>",
                lambda event, field=key: self._mark_manual_pending(event, field=field),
                add="+",
            )
            entry.bind(
                "<FocusIn>",
                lambda event, field=key: self._focus_manual_entry(event, field=field),
                add="+",
            )
            entry.bind("<Return>", self._apply_manual_from_event, add="+")
            var.trace_add(
                "write",
                lambda *_args, overlay=self, field=key: overlay._on_manual_var_write(field),
            )
            self.manual_vars[key] = var
            self.manual_entries[key] = entry
            return entry

        base_grid = tk.Frame(form, bg=manual_bg)
        base_grid.pack(fill="x", pady=(0, 5))
        for col in range(len(MANUAL_BASE_FIELDS)):
            base_grid.columnconfigure(col, weight=1, uniform="manual_base")
        for col, (key, label, default) in enumerate(MANUAL_BASE_FIELDS):
            cell = tk.Frame(base_grid, bg=manual_bg)
            cell.grid(
                row=0,
                column=col,
                sticky="ew",
                padx=(0, 5 if col < len(MANUAL_BASE_FIELDS) - 1 else 0),
            )
            tk.Label(
                cell,
                text=label,
                bg=manual_bg,
                fg=MANUAL_LABEL_FG,
                font=(FONT_UI, 7, "bold" if key in {"total_count", "total_cells"} else "normal"),
                anchor="w",
            ).pack(fill="x", pady=(0, 1))
            add_manual_entry(cell, key, default)

        quality_table = tk.Frame(form, bg=manual_bg)
        quality_table.pack(fill="x")
        column_specs = (
            ("品质", 0, 54),
            ("均格", 1, 1),
            ("件", 1, 1),
            ("格", 1, 1),
            ("均价", 1, 1),
            ("总价", 1, 1),
        )
        for col, (_label, weight, minsize) in enumerate(column_specs):
            quality_table.columnconfigure(col, weight=weight, minsize=minsize)
        for col, (label, _weight, _minsize) in enumerate(column_specs):
            tk.Label(
                quality_table,
                text=label,
                bg=manual_bg,
                fg=WARM if col == 0 else DIM,
                font=(FONT_UI, 7, "bold"),
                anchor="center" if col else "w",
            ).grid(
                row=0,
                column=col,
                sticky="ew",
                padx=(0, 5 if col < len(column_specs) - 1 else 0),
                pady=(0, 2),
            )

        value_keys_by_label = {
            label: (avg_value_key, value_sum_key)
            for label, avg_value_key, value_sum_key in MANUAL_VALUE_ROWS
        }
        for row, (label, avg_key, count_key, cells_key) in enumerate(MANUAL_QUALITY_ROWS, start=1):
            tk.Label(
                quality_table,
                text=label,
                bg=manual_bg,
                fg=MANUAL_LABEL_FG,
                font=(FONT_UI, 7, "bold"),
                anchor="w",
            ).grid(row=row, column=0, sticky="ew", padx=(0, 5), pady=(0, 3))
            for col, key in enumerate((avg_key, count_key, cells_key), start=1):
                cell = tk.Frame(quality_table, bg=manual_bg)
                cell.grid(row=row, column=col, sticky="ew", padx=(0, 5), pady=(0, 3))
                add_manual_entry(cell, key)
            value_keys = value_keys_by_label.get(label)
            for col, key in enumerate(value_keys or ("", ""), start=4):
                cell = tk.Frame(quality_table, bg=manual_bg)
                cell.grid(
                    row=row,
                    column=col,
                    sticky="ew",
                    padx=(0, 5 if col < len(column_specs) - 1 else 0),
                    pady=(0, 3),
                )
                if key:
                    add_manual_entry(cell, key)

        extra_row = tk.Frame(form, bg=manual_bg)
        extra_row.pack(fill="x", pady=(2, 0))
        tk.Label(
            extra_row,
            text="合计",
            bg=manual_bg,
            fg=WARM,
            font=(FONT_UI, 7, "bold"),
            anchor="w",
            width=6,
        ).pack(side="left")
        for key, label, default in MANUAL_EXTRA_FIELDS:
            tk.Label(
                extra_row,
                text=label,
                bg=manual_bg,
                fg=MANUAL_LABEL_FG,
                font=(FONT_UI, 7),
                anchor="w",
            ).pack(side="left", padx=(0, 4))
            cell = tk.Frame(extra_row, bg=manual_bg)
            cell.pack(side="left", fill="x", expand=True)
            add_manual_entry(cell, key, default)
        self._set_manual_edit_enabled(False)

    def _has_manual_inputs(self) -> bool:
        for key, entry in self.manual_entries.items():
            value = entry.get().strip()
            if key == "hero" and value.lower() == "ahmed":
                continue
            if value:
                return True
        return False

    def _on_manual_var_write(self, field: str) -> None:
        if self._manual_programmatic_update:
            return
        self._manual_input_revision = int(getattr(self, "_manual_input_revision", 0)) + 1
        self._manual_dirty_fields.add(field)
        self._sync_manual_derived_fields(trigger_field=field)
        self._mark_manual_pending()

    def _can_autofill_manual_field(self, key: str, *, allow_dirty_empty: bool = False) -> bool:
        current = self._manual_entry_text(key)
        last_auto = self._manual_autofill_values.get(key)
        if not current:
            if allow_dirty_empty:
                return True
            return key not in self._manual_dirty_fields
        return last_auto is not None and current == last_auto

    def _focus_manual_entry(self, event: tk.Event[Any], *, field: str) -> str | None:
        if self._manual_programmatic_update:
            return None
        widget = getattr(event, "widget", None)
        if not isinstance(widget, tk.Entry):
            return None
        try:
            if str(widget.cget("state")) != "normal":
                return None
        except (tk.TclError, AttributeError):
            return None
        if not widget.get():
            return None
        widget.after_idle(lambda w=widget: self._select_manual_entry_all(w))
        return None

    def _select_manual_entry_all(self, widget: tk.Entry) -> None:
        try:
            widget.selection_range(0, "end")
            widget.icursor("end")
        except (tk.TclError, AttributeError):
            return

    def _set_manual_derived_entry(
        self,
        key: str,
        value: Any,
        *,
        allow_dirty_empty: bool = False,
    ) -> None:
        if value in (None, "") or not self._can_autofill_manual_field(
            key,
            allow_dirty_empty=allow_dirty_empty,
        ):
            return
        self._set_manual_entry(key, _format_manual_number(value), track_auto=True)

    def _set_empty_manual_entry_auto(self, key: str, value: Any) -> None:
        if self._manual_entry_text(key):
            return
        entry = self.manual_entries.get(key)
        if entry is None:
            return
        var = getattr(self, "manual_vars", {}).get(key)
        if var is None and not (hasattr(entry, "delete") and hasattr(entry, "insert")):
            return
        self._set_manual_entry(key, _format_manual_number(value), track_auto=True)

    def _manual_quality_zero_values(self, key: str) -> dict[str, float | int | None]:
        return {
            "avg": _to_optional_float(self._manual_entry_text(f"{key}_avg")),
            "count": _to_optional_int(self._manual_entry_text(f"{key}_count")),
            "cells": _to_optional_int(self._manual_entry_text(f"{key}_cells")),
            "avg_value": _to_optional_float(self._manual_entry_text(f"{key}_avg_value")),
            "value_sum": _to_optional_float(self._manual_entry_text(f"{key}_value_sum")),
        }

    def _sync_zero_quality_row(self, key: str) -> None:
        values = self._manual_quality_zero_values(key)
        has_zero = any(value == 0 for value in values.values())
        has_nonzero = any(value not in (None, 0) for value in values.values())
        if not has_zero or has_nonzero:
            return
        for suffix in ("avg", "count", "cells", "avg_value", "value_sum"):
            self._set_empty_manual_entry_auto(f"{key}_{suffix}", 0)

    def _sync_manual_derived_fields(self, *, trigger_field: str | None = None) -> None:
        if not hasattr(self, "manual_entries") or self._manual_programmatic_update:
            return
        total_count = _to_optional_int(self._manual_entry_text("total_count"))
        total_cells = _to_optional_float(self._manual_entry_text("total_cells"))
        total_avg_text = self._manual_entry_text("total_avg")
        total_avg = _to_optional_float(total_avg_text)
        if total_count is not None and total_count > 0:
            if total_avg is not None:
                grid_options = _manual_avg_grid_options_from_text(
                    total_count,
                    total_avg,
                    total_avg_text,
                )
                if len(grid_options) == 1:
                    self._set_manual_derived_entry(
                        "total_cells",
                        grid_options[0],
                        allow_dirty_empty=trigger_field in {"total_count", "total_avg"},
                    )
                    total_cells = _to_optional_float(self._manual_entry_text("total_cells"))
            if total_cells is not None:
                self._set_manual_derived_entry("total_avg", total_cells / total_count)

        for key in (*SPLIT_QUALITY_INPUT_KEYS, *QUALITY_INPUT_KEYS):
            self._sync_zero_quality_row(key)
            count = _to_optional_int(self._manual_entry_text(f"{key}_count"))
            cells = _to_optional_int(self._manual_entry_text(f"{key}_cells"))
            avg_text = self._manual_entry_text(f"{key}_avg")
            avg = _to_optional_float(avg_text)
            if avg == 0 and count in (None, 0) and cells in (None, 0):
                allow_dirty_empty = trigger_field == f"{key}_avg"
                if count is None:
                    self._set_manual_derived_entry(
                        f"{key}_count",
                        0,
                        allow_dirty_empty=allow_dirty_empty,
                    )
                    count = _to_optional_int(self._manual_entry_text(f"{key}_count"))
                if cells is None:
                    self._set_manual_derived_entry(
                        f"{key}_cells",
                        0,
                        allow_dirty_empty=allow_dirty_empty,
                    )
                    cells = _to_optional_int(self._manual_entry_text(f"{key}_cells"))
            if count is not None and cells is not None:
                if count == 0:
                    if cells == 0:
                        self._set_manual_derived_entry(f"{key}_avg", 0)
                else:
                    self._set_manual_derived_entry(f"{key}_avg", cells / count)
            if count is not None and avg is not None:
                grid_options = _manual_avg_grid_options_from_text(count, avg, avg_text)
                if len(grid_options) == 1:
                    self._set_manual_derived_entry(f"{key}_cells", grid_options[0])
            if count is None and avg is not None and cells is not None:
                derived_count = _manual_avg_count_from_cells_text(avg, cells, avg_text)
                if derived_count is not None:
                    self._set_manual_derived_entry(f"{key}_count", derived_count)
        for key in (*SPLIT_QUALITY_INPUT_KEYS, *QUALITY_INPUT_KEYS):
            self._sync_zero_quality_row(key)
            count = _to_optional_int(self._manual_entry_text(f"{key}_count"))
            avg_value = _to_optional_float(self._manual_entry_text(f"{key}_avg_value"))
            value_sum = _to_optional_float(self._manual_entry_text(f"{key}_value_sum"))
            if count is not None:
                if count > 0:
                    if value_sum is not None and avg_value is None:
                        self._set_manual_derived_entry(f"{key}_avg_value", value_sum / count)
                    if avg_value is not None and value_sum is None:
                        self._set_manual_derived_entry(f"{key}_value_sum", avg_value * count)
                elif count == 0:
                    if value_sum == 0 and avg_value is None:
                        self._set_manual_derived_entry(f"{key}_avg_value", 0)
                    if avg_value == 0 and value_sum is None:
                        self._set_manual_derived_entry(f"{key}_value_sum", 0)
        q1_has_user_value = False
        for field in ("q1_avg", "q1_count", "q1_cells"):
            value = self._manual_entry_text(field)
            if value and self._manual_autofill_values.get(field) != value:
                q1_has_user_value = True
                break
        if not q1_has_user_value:
            white_count = _to_optional_int(self._manual_entry_text("white_count"))
            green_count = _to_optional_int(self._manual_entry_text("green_count"))
            white_cells = _to_optional_int(self._manual_entry_text("white_cells"))
            green_cells = _to_optional_int(self._manual_entry_text("green_cells"))
            merged_count = None
            merged_cells = None
            if white_count is not None and green_count is not None:
                merged_count = white_count + green_count
                self._set_manual_derived_entry("q1_count", merged_count)
            if white_cells is not None and green_cells is not None:
                merged_cells = white_cells + green_cells
                self._set_manual_derived_entry("q1_cells", merged_cells)
            if merged_count is not None and merged_count > 0 and merged_cells is not None:
                self._set_manual_derived_entry("q1_avg", merged_cells / merged_count)
            elif merged_count == 0 and merged_cells == 0:
                self._set_manual_derived_entry("q1_avg", 0)

    def _mark_manual_pending(
        self,
        _event: tk.Event[Any] | None = None,
        *,
        field: str | None = None,
    ) -> None:
        if not hasattr(self, "manual_status"):
            return
        if field is not None and not self._manual_programmatic_update:
            self._manual_dirty_fields.add(field)
        if self._manual_active:
            self.manual_status.configure(text="已改动，待应用", fg=WARM)
        elif self._has_manual_inputs():
            self.manual_status.configure(text="待应用", fg=WARM)
        else:
            self.manual_status.configure(text="未启用", fg=WARM)

    def _apply_manual_from_event(self, _event: tk.Event[Any]) -> str:
        self.apply_manual_inputs()
        return "break"

    def _card(
        self,
        parent: tk.Widget,
        *,
        bg: str,
        padx: int = 9,
        pady: int = 8,
    ) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=bg,
            padx=padx,
            pady=pady,
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )

    def _row_card(
        self,
        parent: tk.Widget,
        title: str,
        labels: tuple[str, ...],
    ) -> dict[str, tk.Label]:
        card = self._card(parent, bg=PANEL, padx=7, pady=6)
        tk.Frame(card, bg=ACCENT if title in {"当前建议", "证据"} else BAD, height=1).pack(
            fill="x",
            pady=(0, 4),
        )
        tk.Label(
            card,
            text=title,
            bg=PANEL,
            fg=MUTED,
            font=(FONT_UI, 8, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 3))
        rows: dict[str, tk.Label] = {"_card": card}  # type: ignore[dict-item]
        for idx, label in enumerate(labels):
            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x")
            tk.Label(
                row,
                text=label,
                bg=PANEL,
                fg=DIM,
                font=(FONT_UI, 7),
                anchor="w",
                width=4,
            ).pack(side="left")
            value = tk.Label(
                row,
                text="-",
                bg=PANEL,
                fg=TEXT,
                font=(FONT_UI, 8, "bold" if label in {"动作", "红值"} else "normal"),
                anchor="e",
                justify="left",
                wraplength=0,
            )
            value.pack(side="right", fill="x", expand=True)
            rows[label] = value
        return rows

    def _render_flags(self, flags: list[dict[str, str]]) -> None:
        for child in self.flags.winfo_children():
            child.destroy()
        if not flags:
            flags = [{"label": "正常监测", "level": "neutral", "detail": ""}]
        for flag in flags[:4]:
            level = str(flag.get("level") or "")
            label = str(flag.get("label") or "watch")
            detail = str(flag.get("detail") or "")
            chip = tk.Label(
                self.flags,
                text=label,
                bg=PANEL_SOFT,
                fg=_flag_color(level),
                padx=5,
                pady=1,
                font=(FONT_UI, 7),
                highlightthickness=1,
                highlightbackground=BORDER,
            )
            chip.pack(side="left", padx=(0, 4), pady=1)
            if detail:
                HoverTip(chip, detail)
        self._apply_font_scale(self.flags)

    def _set_label(self, widget: tk.Label, value: Any, *, limit: int = 30) -> None:
        text = _text(value)
        display = _short(text, limit)
        widget.configure(text=display, height=1)
        tip = getattr(widget, "_hover_tip", None)
        if text and text != display:
            if tip is None:
                widget._hover_tip = HoverTip(widget, text)  # type: ignore[attr-defined]
            else:
                tip.set_text(text)
        elif tip is not None:
            tip.set_text("")

    def _set_summary_label(
        self,
        widget: tk.Label,
        value: Any,
        *,
        line_limit: int = 38,
        max_lines: int = 2,
    ) -> None:
        text = _text(value)
        if text in {"", "-"}:
            widget.configure(text="-", height=1)
            return
        parts = text.split(" · ")
        if len(parts) <= 1:
            widget.configure(text=_short(text, line_limit * max_lines), height=1)
            return
        lines: list[str] = []
        current = ""
        index = 0
        while index < len(parts):
            part = parts[index]
            candidate = part if not current else f"{current} · {part}"
            if len(candidate) <= line_limit or not current:
                current = candidate
                index += 1
                continue
            lines.append(current)
            current = ""
            if len(lines) >= max_lines - 1:
                rest = " · ".join(parts[index:])
                lines.append(_short(rest, line_limit))
                break
        else:
            if current:
                lines.append(current)
        if not lines:
            lines = [_short(text, line_limit)]
        lines = lines[:max_lines]
        widget.configure(text="\n".join(lines), height=len(lines), justify="right")

    def _manual_entry_text(self, key: str) -> str:
        entry = self.manual_entries.get(key)
        if entry is None:
            return ""
        return entry.get().strip()

    def _set_manual_entry(
        self,
        key: str,
        value: Any,
        *,
        track_auto: bool = False,
    ) -> None:
        entry = self.manual_entries.get(key)
        if entry is None:
            return
        var = getattr(self, "manual_vars", {}).get(key)
        text = "" if value in (None, "") else str(value)
        self._manual_programmatic_update = True
        previous_state: str | None = None
        try:
            try:
                previous_state = str(entry.cget("state"))
                if previous_state == "disabled":
                    entry.configure(state="normal")
            except (tk.TclError, AttributeError):
                previous_state = None
            if var is not None:
                var.set(text)
            else:
                entry.delete(0, "end")
                if text:
                    entry.insert(0, text)
        finally:
            if previous_state == "disabled":
                try:
                    entry.configure(state=previous_state)
                except (tk.TclError, AttributeError):
                    pass
            self._manual_programmatic_update = False
        if track_auto:
            if not hasattr(self, "_manual_autofill_values"):
                self._manual_autofill_values = {}
            if not hasattr(self, "_manual_dirty_fields"):
                self._manual_dirty_fields = set()
            self._manual_autofill_values[key] = text
            self._manual_dirty_fields.discard(key)

    def _summary_phase(self, data: dict[str, Any]) -> str:
        context = data.get("context") if isinstance(data.get("context"), dict) else {}
        return _text(context.get("phase") or data.get("phase"), "")

    def _summary_session_id(self, data: dict[str, Any]) -> str:
        context = data.get("context") if isinstance(data.get("context"), dict) else {}
        return _text(context.get("session_id") or data.get("session_id"), "").strip()

    def _should_reset_manual_for_summary(self, data: dict[str, Any]) -> bool:
        if not hasattr(self, "manual_entries"):
            return False
        has_manual_state = (
            self._manual_active
            or getattr(self, "_manual_edit_enabled", False)
            or self._has_manual_inputs()
            or bool(_text(getattr(self, "_manual_live_session_id", ""), "").strip())
            or bool(getattr(self, "_manual_snapshot", {}))
        )
        if not has_manual_state:
            return False
        stale = data.get("stale") if isinstance(data.get("stale"), dict) else {}
        reason = _text(stale.get("reason"), "")
        if reason in {"session_ahead", "settled_stale"}:
            return True
        truth = data.get("truth") if isinstance(data.get("truth"), dict) else {}
        if self._summary_phase(data) == "settled" and bool(truth.get("available")):
            if bool(getattr(self, "_manual_settlement_edit_unlocked", False)):
                current_session_id = self._summary_session_id(data)
                previous_session_id = _text(
                    getattr(self, "_manual_live_session_id", ""),
                    "",
                ).strip()
                if not previous_session_id or current_session_id == previous_session_id:
                    return False
            return True
        current_session_id = self._summary_session_id(data)
        previous_session_id = _text(getattr(self, "_manual_live_session_id", ""), "").strip()
        return bool(current_session_id and previous_session_id and current_session_id != previous_session_id)

    def _reset_manual_state(self, status_text: str = "已清空，回到实时", *, status_fg: str = DIM) -> None:
        self._manual_active = False
        self._manual_edit_enabled = False
        self._manual_settlement_edit_unlocked = False
        self._manual_snapshot = {}
        self._manual_summary = {}
        for key in tuple(getattr(self, "manual_entries", {})):
            self._set_manual_entry(key, "", track_auto=False)
        self._manual_dirty_fields.clear()
        self._manual_autofill_values.clear()
        self._manual_live_session_id = ""
        if hasattr(self, "manual_status"):
            self.manual_status.configure(text=status_text, fg=status_fg)
        if hasattr(self, "manual_buttons"):
            self._set_manual_edit_enabled(False)
            self._set_manual_button_state()

    def _manual_values_from_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        context = data.get("context") if isinstance(data.get("context"), dict) else {}
        ahmed_ref = data.get("ahmed_ref") if isinstance(data.get("ahmed_ref"), dict) else {}
        evidence = ahmed_ref.get("evidence") if isinstance(ahmed_ref.get("evidence"), dict) else {}
        values: dict[str, Any] = {}
        hero = _supported_manual_hero_display(context.get("hero"), evidence.get("hero"))
        if hero not in (None, ""):
            values["hero"] = hero
        map_id = context.get("map_id") or evidence.get("map_id")
        if map_id not in (None, ""):
            values["map_id"] = map_id
        if evidence.get("total_count") not in (None, ""):
            values["total_count"] = evidence.get("total_count")
        if evidence.get("total_grid_target") not in (None, ""):
            values["total_cells"] = _format_manual_number(evidence.get("total_grid_target"))
            total_count = _to_optional_float(evidence.get("total_count"))
            total_cells = _to_optional_float(evidence.get("total_grid_target"))
            if total_count is not None and total_count > 0 and total_cells is not None:
                values["total_avg"] = _format_manual_number(total_cells / total_count)
        avg_cells = evidence.get("avg_cells") if isinstance(evidence.get("avg_cells"), dict) else {}
        split_avg_cells = (
            evidence.get("split_avg_cells")
            if isinstance(evidence.get("split_avg_cells"), dict)
            else {}
        )
        quality_cells = (
            evidence.get("quality_cells")
            if isinstance(evidence.get("quality_cells"), dict)
            else {}
        )
        avg_values = evidence.get("avg_values") if isinstance(evidence.get("avg_values"), dict) else {}
        quality_values = (
            evidence.get("quality_values")
            if isinstance(evidence.get("quality_values"), dict)
            else {}
        )
        split_quality_cells = (
            evidence.get("split_quality_cells")
            if isinstance(evidence.get("split_quality_cells"), dict)
            else {}
        )
        quality_cell_ranges = (
            ahmed_ref.get("quality_cells_ranges")
            if isinstance(ahmed_ref.get("quality_cells_ranges"), dict)
            else {}
        )
        quality_count_ranges = (
            ahmed_ref.get("quality_count_ranges")
            if isinstance(ahmed_ref.get("quality_count_ranges"), dict)
            else {}
        )
        fixed_counts = evidence.get("fixed_counts") if isinstance(evidence.get("fixed_counts"), dict) else {}
        split_counts = evidence.get("split_counts") if isinstance(evidence.get("split_counts"), dict) else {}
        count_sums = evidence.get("count_sums") if isinstance(evidence.get("count_sums"), dict) else {}
        for split_key in SPLIT_QUALITY_INPUT_KEYS:
            avg_value = _to_optional_float(split_avg_cells.get(split_key))
            if avg_value not in (None, ""):
                values[f"{split_key}_avg"] = _format_manual_number(avg_value)
            cell_value = split_quality_cells.get(split_key)
            count_value = _to_optional_int(split_counts.get(split_key))
            if count_value is None and cell_value not in (None, "") and avg_value is not None:
                count_value = _manual_avg_count_from_cells(avg_value, cell_value)
            if count_value is not None:
                values[f"{split_key}_count"] = count_value
            if cell_value in (None, "") and count_value is not None and avg_value is not None:
                grid_options = _manual_avg_grid_options(count_value, avg_value)
                if len(grid_options) == 1:
                    cell_value = grid_options[0]
            if cell_value not in (None, ""):
                values[f"{split_key}_cells"] = _format_manual_number(cell_value)
        for quality in QUALITY_INPUT_KEYS:
            avg_value = _to_optional_float(avg_cells.get(quality))
            if avg_value not in (None, ""):
                values[f"{quality}_avg"] = _format_manual_number(avg_value)
            cell_value = quality_cells.get(quality)
            if cell_value in (None, ""):
                raw_range = quality_cell_ranges.get(quality)
                if isinstance(raw_range, (list, tuple)) and len(raw_range) >= 3:
                    first, middle, last = raw_range[0], raw_range[1], raw_range[2]
                    if first not in (None, "") and first == middle == last:
                        cell_value = middle
            count_value = _to_optional_int(fixed_counts.get(quality))
            if count_value is None and cell_value not in (None, "") and avg_value is not None:
                count_value = _manual_avg_count_from_cells(avg_value, cell_value)
            if count_value is None:
                raw_count_range = quality_count_ranges.get(quality)
                if isinstance(raw_count_range, (list, tuple)) and len(raw_count_range) >= 3:
                    first, middle, last = raw_count_range[0], raw_count_range[1], raw_count_range[2]
                    if first not in (None, "") and first == middle == last:
                        count_value = _to_optional_int(middle)
            if count_value is not None:
                values[f"{quality}_count"] = count_value
            if cell_value in (None, "") and count_value is not None and avg_value is not None:
                grid_options = _manual_avg_grid_options(count_value, avg_value)
                if len(grid_options) == 1:
                    cell_value = grid_options[0]
            if cell_value not in (None, ""):
                values[f"{quality}_cells"] = _format_manual_number(cell_value)
            if avg_values.get(quality) not in (None, ""):
                values[f"{quality}_avg_value"] = _format_manual_number(avg_values[quality])
            if quality_values.get(quality) not in (None, ""):
                values[f"{quality}_value_sum"] = _format_manual_number(quality_values[quality])
        count_sum_value = count_sums.get("q4q5q6")
        if count_sum_value in (None, ""):
            count_sum_value = count_sums.get("q4q5")
        if count_sum_value not in (None, ""):
            values["q4q5_count"] = count_sum_value
        return values

    def _manual_context_fallback_values(self) -> dict[str, Any]:
        for data in (
            getattr(self, "_last_live_summary", {}),
            getattr(self, "_last_summary", {}),
        ):
            if not isinstance(data, dict) or not data:
                continue
            if data.get("status") == "stale_snapshot":
                continue
            if self._summary_phase(data) == "manual":
                continue
            values = self._manual_values_from_summary(data)
            fallback: dict[str, Any] = {}
            hero = _normalize_manual_hero(values.get("hero"))
            if is_supported_ref_hero(hero):
                fallback["hero"] = hero
            map_id = _to_optional_int(values.get("map_id"))
            if map_id is not None:
                fallback["map_id"] = map_id
            if fallback:
                return fallback
        return {}

    def _auto_sync_manual_inputs(self, data: dict[str, Any]) -> None:
        if not hasattr(self, "manual_entries") or self._manual_active or getattr(self, "_manual_edit_enabled", False):
            return
        if data.get("status") == "stale_snapshot" or self._summary_phase(data) == "settled":
            return
        has_existing_manual_state = (
            bool(getattr(self, "_manual_dirty_fields", set()))
            or bool(getattr(self, "_manual_autofill_values", {}))
            or self._has_manual_inputs()
        )
        if not has_existing_manual_state:
            return
        values = self._manual_values_from_summary(data)
        for key, value in values.items():
            current = self._manual_entry_text(key)
            last_auto = self._manual_autofill_values.get(key)
            if key in self._manual_dirty_fields:
                continue
            if current and last_auto is not None and current != last_auto:
                self._manual_dirty_fields.add(key)
                continue
            if current and last_auto is None and key not in AUTO_REPLACE_MANUAL_FIELDS:
                continue
            display_value = _manual_map_display_value(value) if key == "map_id" else value
            self._set_manual_entry(key, display_value, track_auto=True)
        if self._has_manual_inputs() and not self._manual_active:
            self._manual_live_session_id = self._summary_session_id(data)
            self.manual_status.configure(text="实时已填入，可修改", fg=ACCENT)

    def _manual_inputs_snapshot(self) -> tuple[dict[str, Any] | None, str]:
        hero_text = self._manual_entry_text("hero")
        map_text = self._manual_entry_text("map_id")
        fallback_context = self._manual_context_fallback_values()
        fallback_sources: dict[str, str] = {}
        hero = _normalize_manual_hero(hero_text)
        if not hero and fallback_context.get("hero"):
            hero = _normalize_manual_hero(fallback_context.get("hero"))
            fallback_sources["hero"] = "live_context"
        if map_text:
            map_id, map_error = _manual_map_id_from_text(map_text)
        else:
            map_id = _to_optional_int(fallback_context.get("map_id"))
            map_error = ""
            if map_id is not None:
                fallback_sources["map_id"] = "live_context"
        if map_error:
            return None, map_error
        map_name = _manual_map_name(map_id)
        total_count, error = _to_manual_count(self._manual_entry_text("total_count"), "总件")
        if error:
            return None, error
        total_cells = _to_optional_float(self._manual_entry_text("total_cells"))
        total_avg_text = self._manual_entry_text("total_avg")
        total_avg = _to_optional_float(total_avg_text)
        if total_count is None:
            return None, "需要填写总件"
        if not hero:
            return None, "需要填写英雄，或先点填入当前"
        if map_id is None:
            return None, "需要填写地图，或先点填入当前"
        if total_cells is None and total_avg is not None:
            grid_options = _manual_avg_grid_options_from_text(
                total_count,
                total_avg,
                total_avg_text,
            )
            if len(grid_options) != 1:
                return None, "全均格与总件无法对应到整数总格"
            total_cells = grid_options[0]
        elif total_cells is not None:
            total_cells_int = int(round(total_cells))
            if abs(float(total_cells) - total_cells_int) > 0.0001:
                return None, "总格需要整数"
            if total_avg is not None and not _manual_avg_matches_cells(
                total_avg,
                avg_text=total_avg_text,
                count=total_count,
                cells=total_cells_int,
            ):
                return None, "全均格与总格/总件不一致"
            total_cells = total_cells_int
        avg_cells: dict[str, float] = {}
        quality_cells: dict[str, int] = {}
        avg_values: dict[str, float] = {}
        quality_values: dict[str, int] = {}
        fixed_counts: dict[str, int] = {}
        split_avg_cells: dict[str, float] = {}
        split_quality_cells: dict[str, int] = {}
        split_counts: dict[str, int] = {}
        split_avg_values: dict[str, float] = {}
        split_quality_values: dict[str, int] = {}
        count_sums: dict[str, int] = {}
        for key in (*SPLIT_QUALITY_INPUT_KEYS, *QUALITY_INPUT_KEYS):
            label = _manual_quality_label(key)
            avg_text = self._manual_entry_text(f"{key}_avg")
            avg = _to_optional_float(avg_text)
            count, error = _to_manual_count(
                self._manual_entry_text(f"{key}_count"),
                f"{label}件",
            )
            if error:
                return None, error
            cells, error = _to_manual_count(
                self._manual_entry_text(f"{key}_cells"),
                f"{label}格",
            )
            if error:
                return None, error
            avg_value, error = _to_manual_nonnegative_float(
                self._manual_entry_text(f"{key}_avg_value"),
                f"{label}均价",
            )
            if error:
                return None, error
            value_sum, error = _to_manual_value_sum(
                self._manual_entry_text(f"{key}_value_sum"),
                f"{label}总价",
            )
            if error:
                return None, error
            zero_fields: list[str] = []
            nonzero_fields: list[str] = []
            for value, field_label in (
                (avg, f"{label}均格"),
                (count, f"{label}件"),
                (cells, f"{label}格"),
                (avg_value, f"{label}均价"),
                (value_sum, f"{label}总价"),
            ):
                if value == 0:
                    zero_fields.append(field_label)
                elif value is not None:
                    nonzero_fields.append(field_label)
            if zero_fields:
                if nonzero_fields:
                    return None, (
                        f"{'/'.join(zero_fields)}为0时，"
                        f"{'和'.join(nonzero_fields)}也必须为0"
                    )
                if avg is None:
                    avg = 0.0
                    self._set_empty_manual_entry_auto(f"{key}_avg", 0)
                if count is None:
                    count = 0
                    self._set_empty_manual_entry_auto(f"{key}_count", 0)
                if cells is None:
                    cells = 0
                    self._set_empty_manual_entry_auto(f"{key}_cells", 0)
                if avg_value is None:
                    avg_value = 0.0
                    self._set_empty_manual_entry_auto(f"{key}_avg_value", 0)
                if value_sum is None:
                    value_sum = 0
                    self._set_empty_manual_entry_auto(f"{key}_value_sum", 0)
            if count is None and avg is not None and cells is not None:
                derived_count = _manual_avg_count_from_cells_text(avg, cells, avg_text)
                if derived_count is None:
                    if avg == 0:
                        return None, (
                            f"{label}均格为0时，{label}件和{label}格都必须为0"
                        )
                    return None, (
                        f"{label}均格与{label}格"
                        "无法对应到整数件数"
                    )
                count = derived_count
            if avg == 0:
                zero_parts: list[str] = []
                if count not in (None, 0):
                    zero_parts.append(f"{label}件")
                if cells not in (None, 0):
                    zero_parts.append(f"{label}格")
                if zero_parts:
                    return None, f"{label}均格为0时，{'和'.join(zero_parts)}也必须为0"
                if count is None:
                    count = 0
                    self._set_empty_manual_entry_auto(f"{key}_count", 0)
                if cells is None:
                    cells = 0
                    self._set_empty_manual_entry_auto(f"{key}_cells", 0)
            if count is not None:
                if key in SPLIT_QUALITY_INPUT_KEYS:
                    split_counts[key] = count
                else:
                    fixed_counts[key] = count
                if avg is not None and cells is None:
                    grid_options = _manual_avg_grid_options_from_text(count, avg, avg_text)
                    if not grid_options:
                        if avg == 0:
                            return None, f"{label}均格为0时，{label}件也必须为0"
                        return None, (
                            f"{label}均格与{label}件"
                            "无法对应到整数格数"
                        )
            if cells is not None:
                if key in SPLIT_QUALITY_INPUT_KEYS:
                    split_quality_cells[key] = cells
                else:
                    quality_cells[key] = cells
                if count is not None:
                    if count <= 0:
                        if cells != 0:
                            return None, f"{label}件为0时格数也必须为0"
                        derived_avg = 0.0
                    else:
                        derived_avg = cells / count
                    if avg is None:
                        avg = derived_avg
                    elif _manual_avg_matches_cells(
                        avg,
                        avg_text=avg_text,
                        count=count,
                        cells=cells,
                    ):
                        avg = derived_avg
                    else:
                        return None, (
                            f"{label}均格与{label}格/"
                            f"{label}件不一致"
                        )
            if avg is not None:
                if key in SPLIT_QUALITY_INPUT_KEYS:
                    split_avg_cells[key] = avg
                else:
                    avg_cells[key] = avg
            if count == 0:
                if avg_value not in (None, 0):
                    return None, f"{label}件为0时{label}均价也必须为0"
                if value_sum not in (None, 0):
                    return None, f"{label}件为0时{label}总价也必须为0"
            elif count is not None and avg_value is not None and value_sum is not None:
                if not _manual_value_sum_matches_avg(
                    avg_value,
                    count=count,
                    value_sum=value_sum,
                ):
                    return None, (
                        f"{label}均价与{label}总价/"
                        f"{label}件不一致"
                    )
            if key in SPLIT_QUALITY_INPUT_KEYS:
                if avg_value is not None:
                    split_avg_values[key] = avg_value
                if value_sum is not None:
                    split_quality_values[key] = value_sum
            else:
                if avg_value is not None:
                    avg_values[key] = avg_value
                if value_sum is not None:
                    quality_values[key] = value_sum
        split_value_inputs = {
            key
            for key, value in split_avg_values.items()
            if value not in (None, 0)
        } | {
            key
            for key, value in split_quality_values.items()
            if value not in (None, 0)
        }
        if split_value_inputs:
            missing = [
                SPLIT_QUALITY_LABELS[key]
                for key in SPLIT_QUALITY_INPUT_KEYS
                if key not in split_value_inputs and split_counts.get(key) != 0
            ]
            if missing:
                return None, f"白/绿价值需同时填写；缺少{'、'.join(missing)}，或改填白绿行"
            split_value_sums: dict[str, int] = {}
            for split_key in SPLIT_QUALITY_INPUT_KEYS:
                value_sum = split_quality_values.get(split_key)
                if value_sum is None and split_counts.get(split_key) == 0:
                    value_sum = 0
                if value_sum is None:
                    split_count = split_counts.get(split_key)
                    split_avg_value = split_avg_values.get(split_key)
                    if split_count is None or split_avg_value is None:
                        return None, (
                            f"{SPLIT_QUALITY_LABELS[split_key]}均价需要配合"
                            f"{SPLIT_QUALITY_LABELS[split_key]}件或总价"
                        )
                    value_sum = int(round(split_avg_value * split_count))
                split_value_sums[split_key] = value_sum
            q1_value_sum = sum(split_value_sums.values())
            existing_q1_value_sum = quality_values.get("q1")
            if (
                existing_q1_value_sum is not None
                and abs(float(existing_q1_value_sum) - float(q1_value_sum)) > 0.5
            ):
                return None, "白/绿总价合计与白绿总价不一致"
            quality_values["q1"] = q1_value_sum
            q1_count_for_value = fixed_counts.get("q1")
            if q1_count_for_value is None and all(key in split_counts for key in SPLIT_QUALITY_INPUT_KEYS):
                q1_count_for_value = sum(split_counts[key] for key in SPLIT_QUALITY_INPUT_KEYS)
            if q1_count_for_value is not None:
                if q1_count_for_value <= 0:
                    derived_q1_avg_value = 0.0 if q1_value_sum == 0 else None
                else:
                    derived_q1_avg_value = q1_value_sum / q1_count_for_value
                if derived_q1_avg_value is not None:
                    existing_q1_avg_value = avg_values.get("q1")
                    if (
                        existing_q1_avg_value is not None
                        and not _manual_value_sum_matches_avg(
                            existing_q1_avg_value,
                            count=q1_count_for_value,
                            value_sum=q1_value_sum,
                        )
                    ):
                        return None, "白/绿价值合计与白绿均价不一致"
                    avg_values["q1"] = derived_q1_avg_value
        q4q5_count, error = _to_manual_count(self._manual_entry_text("q4q5_count"), "紫金红件")
        if error:
            return None, error
        if q4q5_count is not None:
            count_sums["q4q5q6"] = q4q5_count
        ref_inputs: dict[str, Any] = {
            "total_count": total_count,
            "avg_cells": avg_cells,
            "fixed_counts": fixed_counts,
        }
        if quality_cells:
            ref_inputs["quality_cells"] = quality_cells
        if avg_values:
            ref_inputs["avg_values"] = avg_values
        if quality_values:
            ref_inputs["quality_values"] = quality_values
        if split_avg_cells:
            ref_inputs["split_avg_cells"] = split_avg_cells
        if split_quality_cells:
            ref_inputs["split_quality_cells"] = split_quality_cells
        if split_counts:
            ref_inputs["split_counts"] = split_counts
        if count_sums:
            ref_inputs["count_sums"] = count_sums
        if total_cells is not None:
            ref_inputs["total_cells"] = total_cells
        now = time.time()
        snapshot = {
            "created_at": now,
            "hero": hero,
            "map_id": map_id,
            "map_name": map_name or None,
            "phase": "manual",
            "structured_ref_inputs": ref_inputs,
            "ui_contract": {
                "context": {
                    "hero": hero,
                    "map_id": map_id,
                    "map_name": map_name or None,
                    "round": "手动",
                    "phase": "manual",
                    "session_id": "manual",
                },
                "constraints": {
                    "structured_ref_inputs": ref_inputs,
                },
                "baseline": {
                    "decision": {},
                    "posterior": {},
                },
                "source": {
                    "created_at": now,
                    "source_mode": "manual",
                    "manual_map_input": map_text,
                    "manual_context_fallback": fallback_sources,
                },
                "truth": {"available": False},
            },
        }
        return snapshot, ""

    def _manual_input_summary(self, evidence: dict[str, Any]) -> str:
        parts: list[str] = []
        total_parts: list[str] = []
        avg_parts: list[str] = []
        if evidence.get("total_count") not in (None, ""):
            total_parts.append(f"总件 {evidence['total_count']}")
        if evidence.get("total_grid_target") not in (None, ""):
            total_parts.append(f"总格 {_format_manual_number(evidence['total_grid_target'])}")
            total_count = _to_optional_float(evidence.get("total_count"))
            total_cells = _to_optional_float(evidence.get("total_grid_target"))
            if total_count is not None and total_count > 0 and total_cells is not None:
                avg_parts.append(f"全均格 {_format_manual_number(total_cells / total_count)}")
        else:
            estimated_total_grid = self._range_text(evidence.get("total_grid_range"), suffix="格")
            if estimated_total_grid != "-":
                total_parts.append(f"估总格 {estimated_total_grid}")
        avg_cells = evidence.get("avg_cells")
        avg_values = evidence.get("avg_values")
        quality_values = evidence.get("quality_values")
        quality_cells = evidence.get("quality_cells")
        split_avg_cells = evidence.get("split_avg_cells")
        split_quality_cells = evidence.get("split_quality_cells")
        split_counts = evidence.get("split_counts")
        if isinstance(split_avg_cells, dict):
            for key in SPLIT_QUALITY_INPUT_KEYS:
                if split_avg_cells.get(key) not in (None, ""):
                    avg_parts.append(
                        f"{SPLIT_QUALITY_LABELS[key]}均格 "
                        f"{_format_manual_number(split_avg_cells[key])}"
                    )
        if isinstance(avg_cells, dict):
            for key in QUALITY_INPUT_KEYS:
                if avg_cells.get(key) not in (None, ""):
                    avg_parts.append(f"{QUALITY_LABELS[key]}均格 {_format_manual_number(avg_cells[key])}")
        fixed_counts = evidence.get("fixed_counts")
        if isinstance(split_counts, dict):
            split_count_parts = [
                f"{SPLIT_QUALITY_LABELS[key]}件 {split_counts[key]}"
                for key in SPLIT_QUALITY_INPUT_KEYS
                if split_counts.get(key) not in (None, "")
            ]
            if split_count_parts:
                parts.append("分件 " + "，".join(split_count_parts))
        if isinstance(fixed_counts, dict):
            count_parts = [
                f"{QUALITY_LABELS[key]}件 {fixed_counts[key]}"
                for key in QUALITY_INPUT_KEYS
                if fixed_counts.get(key) not in (None, "")
            ]
            if count_parts:
                parts.append("件数 " + "，".join(count_parts))
        if isinstance(split_quality_cells, dict):
            split_cell_parts = [
                f"{SPLIT_QUALITY_LABELS[key]}格 {_format_manual_number(split_quality_cells[key])}"
                for key in SPLIT_QUALITY_INPUT_KEYS
                if split_quality_cells.get(key) not in (None, "")
            ]
            if split_cell_parts:
                parts.append("分格 " + "，".join(split_cell_parts))
        if isinstance(quality_cells, dict):
            cell_parts = [
                f"{QUALITY_LABELS[key]}格 {_format_manual_number(quality_cells[key])}"
                for key in QUALITY_INPUT_KEYS
                if quality_cells.get(key) not in (None, "")
            ]
            if cell_parts:
                parts.append("格数 " + "，".join(cell_parts))
        if isinstance(avg_values, dict):
            avg_value_parts = [
                f"{QUALITY_LABELS[key]}均价 {_format_manual_number(avg_values[key])}"
                for key in QUALITY_INPUT_KEYS
                if avg_values.get(key) not in (None, "")
            ]
            if avg_value_parts:
                parts.append("均价 " + "，".join(avg_value_parts))
        if isinstance(quality_values, dict):
            value_sum_parts = [
                f"{QUALITY_LABELS[key]}总价 {_format_manual_number(quality_values[key])}"
                for key in QUALITY_INPUT_KEYS
                if quality_values.get(key) not in (None, "")
            ]
            if value_sum_parts:
                parts.append("总价 " + "，".join(value_sum_parts))
        min_counts = evidence.get("min_counts")
        if isinstance(min_counts, dict):
            floor_parts = []
            for key in QUALITY_INPUT_KEYS:
                value = _to_optional_int(min_counts.get(key))
                fixed_value = (
                    _to_optional_int(fixed_counts.get(key))
                    if isinstance(fixed_counts, dict)
                    else None
                )
                if value is None or value <= 0 or fixed_value is not None and fixed_value >= value:
                    continue
                floor_parts.append(f"{QUALITY_LABELS[key]}≥{value}")
            if floor_parts:
                parts.append("下界 " + "，".join(floor_parts))
        count_sums = evidence.get("count_sums")
        if isinstance(count_sums, dict):
            if count_sums.get("q4q5q6") not in (None, ""):
                parts.append(f"紫金红件 {count_sums['q4q5q6']}")
            elif count_sums.get("q4q5") not in (None, ""):
                parts.append(f"紫金件 {count_sums['q4q5']}")
        ordered_parts = total_parts + parts + avg_parts
        return " · ".join(ordered_parts) if ordered_parts else "-"

    def _range_text(self, values: Any, *, money: bool = False, suffix: str = "") -> str:
        if not isinstance(values, (list, tuple)) or not values:
            return "-"
        parts: list[str]
        if money:
            parts = [_money(value, "?") for value in values]
        else:
            parts = ["?" if value is None else str(value) for value in values]
        text = " / ".join(parts)
        return f"{text}{suffix}" if suffix and text != "-" else text

    def _manual_result_summary(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        if run_reference_engine is None:
            raise RuntimeError("ref engine unavailable")
        result = run_reference_engine(prepare_reference_engine_snapshot(snapshot), max_combos=60000).as_dict()
        evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
        display_evidence = dict(evidence)
        display_evidence["total_grid_range"] = result.get("total_grid_range")
        candidate_summary = _candidate_summary(result)
        hero_key = normalize_hero_key(snapshot.get("hero") or "")
        next_info_hint = _next_info_hint(
            result,
            hero_key=hero_key,
            round_no=_parse_int(snapshot.get("round")),
        )
        notes = tuple(str(item) for item in (result.get("notes") or ()))
        fixed_counts = evidence.get("fixed_counts") if isinstance(evidence.get("fixed_counts"), dict) else {}
        avg_cells = evidence.get("avg_cells") if isinstance(evidence.get("avg_cells"), dict) else {}
        status = _text(result.get("status"), "unknown")
        display_ready = result.get("balanced") not in (None, "")
        if "manual_total_count_prior_enumeration" in notes:
            status = "manual_prior"
        elif "combo_cap_hit" in notes and "q6" not in fixed_counts and "q6" not in avg_cells:
            status = "manual_constraints_wide"
        ok = display_ready
        flags = [{"label": "手动输入", "level": "neutral", "detail": "manual reference mode"}]
        if status == "manual_prior":
            flags.append({"label": "手动先验", "level": "watch", "detail": ";".join(notes)})
        elif status == "manual_constraints_wide":
            flags.append({"label": "约束较宽", "level": "watch", "detail": ";".join(notes)})
        elif not ok:
            flags.append({"label": "约束不足", "level": "risk", "detail": ";".join(notes)})
        layout_notes = [note for note in notes if "aisha_layout" in note]
        if hero_key == "aisha" and layout_notes:
            flags.append({"label": "布局余量", "level": "neutral", "detail": "; ".join(layout_notes[:4])})
        defense_hint = _aisha_defense_multiplier_hint(_parse_int(snapshot.get("round")))
        if hero_key == "aisha" and defense_hint:
            flags.append(
                {"label": defense_hint, "level": "neutral", "detail": "产品参考倍数，不进引擎"},
            )
        d1_detail = _aisha_d1_flag_detail(list(notes)) if hero_key == "aisha" else ""
        if d1_detail:
            flags.append(
                {"label": "红品权重参考", "level": "watch", "detail": d1_detail},
            )
        red_count_range, red_cells_range = _red_display_ranges(result)
        return {
            "status": "ok",
            "snapshot_path": "manual",
            "updated_at_text": time.strftime("%H:%M:%S"),
            "context": {
                "hero": snapshot.get("hero") or "?",
                "is_supported_ref_hero": True,
                "map_id": snapshot.get("map_id"),
                "round": "手动",
                "phase": "manual",
                "session_id": "manual",
                "file": None,
            },
            "reference": {
                "label": "Hero Ref",
                "source": "manual_ref",
                "readiness": status,
                "note": "manual inputs",
                "conservative": _money(result.get("conservative")) if ok else "-",
                "balanced": _money(result.get("balanced")) if ok else "-",
                "aggressive": _money(result.get("aggressive")) if ok else "-",
                "raw_value_range": self._range_text(
                    (result.get("value_p25"), result.get("value_p50"), result.get("value_p75")),
                    money=True,
                ),
                "v3_conservative": "-",
                "v3_balanced": "-",
                "v3_aggressive": "-",
                "ref_minus_v3_balanced": "-",
                "ref_minus_v3_balanced_raw": None,
                "action": "手动参考" if ok else "约束不足",
                "risk_band": "manual",
                "current_highest": "-",
                "decision_range": self._range_text(
                    (result.get("conservative"), result.get("balanced"), result.get("aggressive")),
                    money=True,
                ),
                "total_grid_range": self._range_text(result.get("total_grid_range"), suffix="格"),
                "total_value_range": self._range_text(
                    (result.get("value_p25"), result.get("value_p50"), result.get("value_p75")),
                    money=True,
                ),
            },
            "red": {
                "count_range": _red_range_text(red_count_range),
                "cells_range": _red_range_text(red_cells_range),
                "value_range": self._range_text(result.get("red_value_range"), money=True),
                "quality_count_summary": self._quality_count_summary(result),
                "uncertainty_summary": _quality_uncertainty_summary(result),
                "prior_rate": "-",
                "sample_rate": "-",
                "risk_reference": "",
            },
            "evidence": {
                "match_text": "manual",
                "information_density": "手动",
                "diagnostics": ";".join(result.get("notes") or ()),
                "latest_sent": {},
                "latest_result": {},
                "source_mode": "manual_ref",
                "ref_status": status,
                "ref_readiness": status,
                "ref_combo_count": _text(result.get("combo_count"), ""),
                "ref_input_summary": self._manual_input_summary(display_evidence),
                "candidate_summary": candidate_summary,
                "next_info_hint": next_info_hint,
                "ref_notes": ";".join(result.get("notes") or ()),
            },
            "truth": {"available": False, "q6": {}, "top_item": {}},
            "ahmed_ref": result,
            "minimap": {
                "status": "unavailable",
                "summary_text": "手动模式无小地图",
                "layout_source": "manual",
                "columns": 10,
                "viewport_rows": 13,
                "known_items": 0,
                "drawable_items": 0,
                "final_total_items": None,
                "quality_counts": {},
                "items": [],
            },
            "flags": flags,
        }

    def _structured_input_candidates(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        uc = snapshot.get("ui_contract") if isinstance(snapshot.get("ui_contract"), dict) else {}
        constraints = uc.get("constraints") if isinstance(uc.get("constraints"), dict) else {}
        candidates: list[dict[str, Any]] = []
        for value in (
            snapshot.get("structured_ref_inputs"),
            uc.get("structured_ref_inputs"),
            constraints.get("structured_ref_inputs"),
            snapshot.get("hero_ref_inputs"),
            uc.get("hero_ref_inputs"),
            constraints.get("hero_ref_inputs"),
            snapshot.get("aisha_ref_inputs"),
            uc.get("aisha_ref_inputs"),
            constraints.get("aisha_ref_inputs"),
            snapshot.get("ahmad_ref_inputs"),
            uc.get("ahmad_ref_inputs"),
            constraints.get("ahmad_ref_inputs"),
            snapshot.get("victor_ref_inputs"),
            uc.get("victor_ref_inputs"),
            constraints.get("victor_ref_inputs"),
        ):
            if isinstance(value, dict):
                candidates.append(value)
        return candidates

    def _merge_ref_inputs(
        self,
        base: dict[str, Any],
        overlay: dict[str, Any],
    ) -> dict[str, Any]:
        merged = copy.deepcopy(base)
        for key, value in overlay.items():
            if value in (None, ""):
                continue
            if isinstance(value, dict):
                if not value:
                    continue
                current = merged.get(key)
                if isinstance(current, dict):
                    nested = copy.deepcopy(current)
                    nested.update(value)
                    merged[key] = nested
                else:
                    merged[key] = copy.deepcopy(value)
            elif isinstance(value, list):
                if value:
                    merged[key] = copy.deepcopy(value)
            else:
                merged[key] = value
        return merged

    def _merged_live_ref_inputs(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for candidate in self._structured_input_candidates(snapshot):
            merged = self._merge_ref_inputs(merged, candidate)
        return merged

    def _manual_ref_inputs(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        value = snapshot.get("structured_ref_inputs")
        return copy.deepcopy(value) if isinstance(value, dict) else {}

    def _snapshot_with_manual_overlay(
        self,
        live_snapshot: dict[str, Any],
        manual_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        overlaid = copy.deepcopy(live_snapshot)
        manual_inputs = self._manual_ref_inputs(manual_snapshot)
        merged_inputs = self._merge_ref_inputs(
            self._merged_live_ref_inputs(live_snapshot),
            manual_inputs,
        )
        overlaid["structured_ref_inputs"] = merged_inputs
        uc = overlaid.setdefault("ui_contract", {})
        if not isinstance(uc, dict):
            uc = {}
            overlaid["ui_contract"] = uc
        constraints = uc.setdefault("constraints", {})
        if not isinstance(constraints, dict):
            constraints = {}
            uc["constraints"] = constraints
        source = uc.setdefault("source", {})
        if not isinstance(source, dict):
            source = {}
            uc["source"] = source
        uc["structured_ref_inputs"] = merged_inputs
        constraints["structured_ref_inputs"] = merged_inputs
        source["manual_overlay"] = True
        source["manual_overlay_updated_at"] = time.time()
        return overlaid

    def _manual_overlay_summary(
        self,
        live_snapshot: dict[str, Any],
        manual_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        summary = summarize_snapshot(
            self._snapshot_with_manual_overlay(live_snapshot, manual_snapshot),
            snapshot_path=self.snapshot_path,
        )
        flags = summary.setdefault("flags", [])
        if isinstance(flags, list):
            flags.append(
                {
                    "label": "手动叠加",
                    "level": "neutral",
                    "detail": "manual structured inputs are merged into the latest live snapshot",
                }
            )
        evidence = summary.get("evidence")
        if isinstance(evidence, dict):
            evidence["manual_overlay"] = True
        reference = summary.get("reference")
        if isinstance(reference, dict):
            note = _text(reference.get("note"), "")
            if "manual overlay" not in note:
                reference["note"] = f"{note} manual overlay.".strip()
        return summary

    def apply_manual_inputs(self) -> None:
        snapshot, error = self._manual_inputs_snapshot()
        if snapshot is None:
            self.manual_status.configure(text=error, fg=BAD)
            return
        try:
            live_summary = self._last_live_summary if isinstance(self._last_live_summary, dict) else {}
            settlement_manual = bool(
                getattr(self, "_manual_settlement_edit_unlocked", False)
                and self._is_settlement_summary(live_summary)
            )
            live_session_id = self._summary_session_id(live_summary)
            revision = int(getattr(self, "_manual_input_revision", 0))
            if self._start_manual_summary_worker(
                snapshot=snapshot,
                settlement_manual=settlement_manual,
                live_session_id=live_session_id,
                revision=revision,
            ):
                return
            summary = self._manual_result_summary(snapshot)
        except Exception as exc:  # noqa: BLE001 - show calculation failure in UI
            self.manual_status.configure(text=f"计算失败: {exc}", fg=BAD)
            return
        self._manual_active = True
        self._set_manual_edit_enabled(True)
        self._manual_snapshot = snapshot
        self._manual_summary = summary
        self._last_summary = summary
        self._manual_live_session_id = live_session_id
        self.manual_status.configure(
            text="手动计算，结算页已脱离" if settlement_manual else "手动计算，实时后台",
            fg=WARM,
        )
        self._set_manual_button_state()
        if summary.get("status") == "stale_snapshot":
            self.render_standby(summary)
        else:
            self.render(summary)

    def _quality_count_summary(self, result: dict[str, Any]) -> str:
        ranges = result.get("quality_count_ranges")
        if not isinstance(ranges, dict):
            return "-"
        q4 = _display_range_text(ranges.get("q4"))
        q5 = _display_range_text(ranges.get("q5"))
        parts: list[str] = []
        if q4 != "-":
            parts.append(f"紫件 {q4}")
        if q5 != "-":
            parts.append(f"金件 {q5}")
        return " · ".join(parts) if parts else "-"

    def _settlement_cleared_manual_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        context = data.get("context") if isinstance(data.get("context"), dict) else {}
        values = self._manual_values_from_summary(data)
        hero = _normalize_manual_hero(values.get("hero") or context.get("hero")) or "?"
        map_id = _to_optional_int(values.get("map_id") or context.get("map_id"))
        map_name = _manual_map_name(map_id)
        session_id = self._summary_session_id(data) or "manual"
        input_summary_parts = []
        if hero != "?":
            input_summary_parts.append(f"英雄 {hero}")
        if map_id is not None:
            input_summary_parts.append(f"地图 {_manual_map_display_value(map_id)}")
        input_summary = " · ".join(input_summary_parts) if input_summary_parts else "结算已清，待填写"
        return {
            "status": "ok",
            "snapshot_path": "manual",
            "updated_at_text": time.strftime("%H:%M:%S"),
            "context": {
                "hero": hero,
                "is_supported_ref_hero": is_supported_ref_hero(hero),
                "map_id": map_id,
                "map_name": map_name or None,
                "round": "手动",
                "phase": "manual",
                "session_id": session_id,
                "file": None,
            },
            "reference": {
                "label": "Hero Ref",
                "source": "manual_ref",
                "readiness": "settlement_cleared",
                "note": "settlement cleared; waiting for manual inputs",
                "conservative": "-",
                "balanced": "-",
                "aggressive": "-",
                "raw_value_range": "-",
                "v3_conservative": "-",
                "v3_balanced": "-",
                "v3_aggressive": "-",
                "ref_minus_v3_balanced": "-",
                "ref_minus_v3_balanced_raw": None,
                "action": "待手填",
                "risk_band": "manual",
                "current_highest": "-",
                "decision_range": "-",
                "total_grid_range": "-",
                "total_value_range": "-",
            },
            "red": {
                "count_range": "-",
                "cells_range": "-",
                "value_range": "-",
                "quality_count_summary": "-",
                "uncertainty_summary": "结算已清，待输入",
                "prior_rate": "-",
                "sample_rate": "-",
                "risk_reference": "",
            },
            "evidence": {
                "match_text": "manual",
                "information_density": "结算已清",
                "diagnostics": "settlement_cleared",
                "latest_sent": {},
                "latest_result": {},
                "source_mode": "manual_ref",
                "ref_status": "settlement_cleared",
                "ref_readiness": "settlement_cleared",
                "ref_combo_count": "",
                "ref_input_summary": input_summary,
                "candidate_summary": "-",
                "next_info_hint": "补总件/总格或品质信息",
                "ref_notes": "settlement_cleared",
            },
            "truth": {"available": False, "q6": {}, "top_item": {}},
            "ahmed_ref": {
                "status": "settlement_cleared",
                "evidence": {},
                "notes": ("settlement_cleared",),
            },
            "minimap": {
                "status": "unavailable",
                "summary_text": "手动模式无小地图",
                "layout_source": "manual",
                "columns": 10,
                "viewport_rows": 13,
                "known_items": 0,
                "drawable_items": 0,
                "final_total_items": None,
                "quality_counts": {},
                "items": [],
            },
            "flags": [
                {
                    "label": "结算已清",
                    "level": "watch",
                    "detail": "settlement truth detached from manual edit view",
                }
            ],
        }

    def clear_settlement_manual_values(self) -> str:
        data = self._last_summary or self._last_live_summary or {}
        if not self._is_settlement_summary(data):
            self._set_manual_settlement_button_state()
            return "break"
        self._manual_settlement_edit_unlocked = True
        self._set_manual_edit_enabled(True)
        values = self._manual_values_from_summary(data)
        keep = {
            "hero": values.get("hero") or "",
            "map_id": (
                _manual_map_display_value(values.get("map_id"))
                if values.get("map_id") not in (None, "")
                else ""
            ),
        }
        for key in tuple(getattr(self, "manual_entries", {})):
            self._set_manual_entry(key, keep.get(key, ""), track_auto=key in keep)
        summary = self._settlement_cleared_manual_summary(data)
        self._manual_active = False
        self._manual_snapshot = {}
        self._manual_summary = summary
        self._last_summary = summary
        self._manual_dirty_fields.clear()
        self._manual_autofill_values = {key: value for key, value in keep.items() if value}
        self._manual_live_session_id = self._summary_session_id(data)
        if hasattr(self, "manual_status"):
            self.manual_status.configure(text="已清结算，可手动填写", fg=WARM)
        if hasattr(self, "manual_card"):
            self.manual_card.configure(highlightbackground=WARM, highlightthickness=2)
        self.render(summary)
        self._set_manual_settlement_button_state()
        return "break"

    def clear_manual_inputs(self) -> str:
        if not hasattr(self, "manual_entries"):
            return "break"
        self._manual_active = False
        self._manual_snapshot = {}
        self._manual_summary = {}
        self._manual_dirty_fields.clear()
        self._manual_autofill_values.clear()
        self._manual_live_session_id = ""
        for key in tuple(getattr(self, "manual_entries", {})):
            self._set_manual_entry(key, "", track_auto=False)
        if hasattr(self, "manual_status"):
            self.manual_status.configure(text="已清空，待填写", fg=DIM)
        self._set_manual_button_state()
        self._set_manual_settlement_button_state()
        return "break"

    def prefill_manual_inputs(self) -> None:
        data = self._last_live_summary or self._last_summary or {}
        values = self._manual_values_from_summary(data)
        self._set_manual_entry("hero", values.get("hero") or "", track_auto=True)
        self._set_manual_entry(
            "map_id",
            (
                _manual_map_display_value(values.get("map_id"))
                if values.get("map_id") is not None
                else ""
            ),
            track_auto=True,
        )
        self._set_manual_entry("total_count", values.get("total_count") if values.get("total_count") is not None else "", track_auto=True)
        self._set_manual_entry("total_cells", values.get("total_cells") if values.get("total_cells") is not None else "", track_auto=True)
        self._set_manual_entry("total_avg", values.get("total_avg") if values.get("total_avg") is not None else "", track_auto=True)
        for key in (*SPLIT_QUALITY_INPUT_KEYS, *QUALITY_INPUT_KEYS):
            self._set_manual_entry(
                f"{key}_avg",
                values.get(f"{key}_avg") if values.get(f"{key}_avg") is not None else "",
                track_auto=True,
            )
            self._set_manual_entry(
                f"{key}_count",
                values.get(f"{key}_count") if values.get(f"{key}_count") is not None else "",
                track_auto=True,
            )
            self._set_manual_entry(
                f"{key}_cells",
                values.get(f"{key}_cells") if values.get(f"{key}_cells") is not None else "",
                track_auto=True,
            )
            self._set_manual_entry(
                f"{key}_avg_value",
                values.get(f"{key}_avg_value") if values.get(f"{key}_avg_value") is not None else "",
                track_auto=True,
            )
            self._set_manual_entry(
                f"{key}_value_sum",
                values.get(f"{key}_value_sum") if values.get(f"{key}_value_sum") is not None else "",
                track_auto=True,
            )
        self._set_manual_entry(
            "q4q5_count",
            values.get("q4q5_count") if values.get("q4q5_count") is not None else "",
            track_auto=True,
        )
        self._manual_live_session_id = self._summary_session_id(data)
        self.manual_status.configure(text="已填入当前，待应用", fg=ACCENT)

    def _clear_values(self) -> None:
        self._set_price_titles({})
        for widget in self.price_labels.values():
            widget.configure(text="-")
        for row_group in (
            self.red_rows,
            self.action_rows,
            self.evidence_rows,
            self.detail_rows,
        ):
            for key, widget in row_group.items():
                if key == "_card":
                    continue
                self._set_label(widget, "-")

    def _set_price_titles(self, titles: dict[str, Any]) -> None:
        for key, default in self.default_price_titles.items():
            widget = self.price_title_labels.get(key)
            if widget is not None:
                widget.configure(text=_text(titles.get(key), default))

    def _minimap_count_text(self, minimap: dict[str, Any]) -> str:
        quality_counts = minimap.get("quality_counts")
        if not isinstance(quality_counts, dict) or not quality_counts:
            return "-"
        return "  ".join(
            f"{key.upper()}:{quality_counts[key]}"
            for key in ("q6", "q5", "q4", "q3")
            if key in quality_counts
        ) or "-"

    def _set_minimap_meta(self, minimap: dict[str, Any]) -> None:
        rows = getattr(self, "minimap_meta_rows", {})
        if not rows:
            return
        known = minimap.get("known_items") or minimap.get("drawable_items") or "-"
        total = minimap.get("final_total_items")
        item_text = f"{known}/{total}" if total not in (None, "", known) else _text(known)
        columns = _to_int(minimap.get("columns"), MINIMAP_DEFAULT_COLUMNS)
        viewport_rows = _to_int(minimap.get("viewport_rows"), MINIMAP_DEFAULT_ROWS)
        values = {
            "件数": item_text,
            "来源": minimap.get("layout_source") or "-",
            "品质": self._minimap_count_text(minimap),
            "范围": f"{columns}列 x {viewport_rows}行 · {columns * viewport_rows}格",
        }
        for key, value in values.items():
            if key in rows:
                rows[key].configure(text=_short(value, 32))

    def _render_minimap_header(
        self,
        *,
        title: tk.Label,
        counts: tk.Label,
        minimap: dict[str, Any],
    ) -> None:
        status = str(minimap.get("status") or "")
        summary = _text(minimap.get("summary_text"), "等待公开轮廓/小地图")
        title.configure(text=f"小地图 · {_short(summary, 22)}")
        counts.configure(text=self._minimap_count_text(minimap))
        available = status == "available" and isinstance(minimap.get("items"), list) and bool(minimap.get("items"))
        self.map_button.configure(text="地图", fg=ACCENT if available else DIM)

    def _render_minimap(self, minimap: dict[str, Any]) -> None:
        self._minimap_data = minimap
        self._render_minimap_header(
            title=self.minimap_title,
            counts=self.minimap_counts,
            minimap=minimap,
        )
        if self.details_expanded:
            self._draw_minimap(
                self.minimap_canvas,
                minimap,
                self._canvas_tip,
                min_width=300,
                min_height=160,
                allow_scroll=True,
                cell_hint=self._minimap_cell_hint(MINIMAP_CELL_HINT_BASE),
            )
            self._set_minimap_meta(minimap)
        if self._minimap_popup is not None and self._popup_canvas is not None:
            self._redraw_minimap_popup()
        if self._pinned_minimap_popup is not None and self._pinned_canvas is not None:
            self._redraw_pinned_minimap()

    def _round_rect(
        self,
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        **kwargs: Any,
    ) -> int:
        radius = max(1.0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
        points = (
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        )
        return int(canvas.create_polygon(points, smooth=True, splinesteps=8, **kwargs))

    def _minimap_quality_style(self, quality: str) -> dict[str, Any]:
        key = quality if quality in MAINLINE_QUALITY_STYLE else "unknown"
        style = dict(MAINLINE_QUALITY_STYLE[key])
        if key == "unknown":
            style["unknown"] = True
        return style

    def _draw_unknown_quality_fill(
        self,
        canvas: tk.Canvas,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        *,
        color: str,
        tag: str,
        base_fill: str | None = None,
    ) -> None:
        width = max(1, x1 - x0)
        height = max(1, y1 - y0)
        if base_fill:
            canvas.create_rectangle(
                x0,
                y0,
                x1,
                y1,
                fill=base_fill,
                outline="",
                width=0,
                tags=(tag,),
            )
        step = max(3, min(width, height) // 4)
        line_width = 2 if min(width, height) >= 14 else 1
        for start_x in range(x0 - height, x1 + height, step):
            clipped_start_x = max(x0, start_x)
            clipped_end_x = min(x1, start_x + height)
            start_y = y1 - (clipped_start_x - start_x)
            end_y = y1 - (clipped_end_x - start_x)
            if clipped_start_x < clipped_end_x and y0 <= end_y <= start_y <= y1:
                canvas.create_line(
                    clipped_start_x,
                    start_y,
                    clipped_end_x,
                    end_y,
                    fill=color,
                    width=line_width,
                    tags=(tag,),
                )

    def _draw_minimap(
        self,
        canvas: tk.Canvas,
        minimap: dict[str, Any],
        tip: HoverTip | None,
        *,
        min_width: int = 300,
        min_height: int = 104,
        allow_scroll: bool = False,
        cell_hint: float = 20.0,
    ) -> None:
        visible_width, visible_height = canvas_draw_size(
            canvas,
            min_width=min_width,
            min_height=min_height,
        )
        # Skip the clear+redraw when nothing that affects this canvas changed.
        # Live snapshots refresh ~1/s but the minimap content is usually identical;
        # redrawing unconditionally made the canvas flicker every cycle.
        cache = getattr(self, "_minimap_canvas_signatures", None)
        if cache is not None:
            signature = (
                int(visible_width),
                int(visible_height),
                round(float(cell_hint), 2),
                bool(allow_scroll),
                json.dumps(minimap, sort_keys=True, default=str),
            )
            if cache.get(id(canvas)) == signature:
                return
            cache[id(canvas)] = signature
        canvas.delete("all")
        width = visible_width
        height = visible_height
        status = str(minimap.get("status") or "")
        if status != "available" or not isinstance(minimap.get("items"), list) or not minimap.get("items"):
            canvas.configure(scrollregion=(0, 0, width, height))
            columns = MINIMAP_DEFAULT_COLUMNS
            rows = MINIMAP_DEFAULT_ROWS
            pad_x = 10
            pad_y = 8
            cell = max(4, int(min((width - pad_x * 2) / columns, (height - pad_y * 2) / rows)))
            grid_w = cell * columns
            grid_h = cell * rows
            x0 = int(max(pad_x, round((width - grid_w) / 2)))
            y0 = int(max(pad_y, round((height - grid_h) / 2)))
            canvas.create_rectangle(x0, y0, x0 + grid_w, y0 + grid_h, outline=BORDER, fill=MINIMAP_BG)
            grid_color = _blend_hex(MINIMAP_GRID, MINIMAP_BG, 0.18)
            for col in range(columns + 1):
                x = x0 + col * cell + 0.5
                canvas.create_line(x, y0, x, y0 + grid_h, fill=grid_color)
            for row in range(rows + 1):
                y = y0 + row * cell + 0.5
                canvas.create_line(x0, y, x0 + grid_w, y, fill=grid_color)
            canvas.create_text(
                width / 2,
                height / 2,
                text="等待公开轮廓/小地图",
                fill=MINIMAP_TEXT,
                font=(FONT_UI, 9),
            )
            return

        items = [item for item in minimap.get("items", []) if isinstance(item, dict)]
        columns = _to_int(minimap.get("columns"), MINIMAP_DEFAULT_COLUMNS)
        viewport_rows = _to_int(minimap.get("viewport_rows"), MINIMAP_DEFAULT_ROWS)
        max_row = 0
        max_col = 0
        for item in items:
            row = _to_int(item.get("row"), 1)
            col = _to_int(item.get("col"), 1)
            item_w = max(1, _to_int(item.get("width"), 1))
            item_h = max(1, _to_int(item.get("height"), 1))
            max_row = max(max_row, row + item_h - 1)
            max_col = max(max_col, col + item_w - 1)
        columns = max(MINIMAP_DEFAULT_COLUMNS, min(20, max(columns, max_col)))
        rows = max(MINIMAP_DEFAULT_ROWS, min(25, max(max_row, viewport_rows)))
        pad_x = 10
        pad_y = 8
        if allow_scroll:
            width = visible_width
            height = max(visible_height, int(rows * cell_hint + pad_y * 2))
        cell = max(4, int(min((width - pad_x * 2) / columns, (height - pad_y * 2) / rows)))
        grid_w = cell * columns
        grid_h = cell * rows
        x0 = int(max(pad_x, round((width - grid_w) / 2)))
        y0 = int(max(pad_y, round((height - grid_h) / 2)))
        canvas.configure(scrollregion=(0, 0, width, height))

        grid_color = _blend_hex(MINIMAP_GRID, MINIMAP_BG, 0.18)
        canvas.create_rectangle(x0, y0, x0 + grid_w, y0 + grid_h, outline=BORDER, fill=MINIMAP_BG)
        for col in range(columns + 1):
            x = x0 + col * cell + 0.5
            canvas.create_line(x, y0, x, y0 + grid_h, fill=grid_color)
        for row in range(rows + 1):
            y = y0 + row * cell + 0.5
            canvas.create_line(x0, y, x0 + grid_w, y, fill=grid_color)

        for idx, item in enumerate(items):
            row = _to_int(item.get("row"), 1)
            col = _to_int(item.get("col"), 1)
            item_w = max(1, _to_int(item.get("width"), 1))
            item_h = max(1, _to_int(item.get("height"), 1))
            if row < 1 or col < 1 or row > rows or col > columns:
                continue
            quality = _minimap_quality_key(item.get("quality"))
            item_value = _to_int(item.get("value"), 0)
            style = self._minimap_quality_style(quality)
            fill = str(style["fill"])
            if style.get("unknown"):
                outline = str(style["outline"])
            else:
                outline = _blend_hex(fill, MINIMAP_BG, 0.36)
            gap = 1
            x1 = x0 + (col - 1) * cell + gap
            y1 = y0 + (row - 1) * cell + gap
            x2 = min(x0 + grid_w - gap, x0 + (col - 1 + item_w) * cell - gap)
            y2 = min(y0 + grid_h - gap, y0 + (row - 1 + item_h) * cell - gap)
            tag = f"item_{idx}"
            source_text = str(item.get("source") or "").lower()
            render_mode = str(item.get("render_mode") or "").lower()
            item_layout_source = str(item.get("layout_source") or "").lower()
            shape_key = str(item.get("shape_key") or "").strip()
            item_id = item.get("item_id")
            has_item_identity = item_id not in (None, "", 0, "0")
            cells_value = _to_int(item.get("cells"), 0)
            explicit_marker = render_mode == "marker"
            has_hard_footprint = (
                render_mode == "footprint"
                or (
                    not explicit_marker
                    and (
                        bool(shape_key)
                        or has_item_identity
                        or source_text in {"packet", "settlement_inventory", "settlement"}
                    )
                )
            )
            marker_only = explicit_marker or (
                not has_hard_footprint
                and (
                    source_text in {
                        "quality_only",
                        "quality_reveal",
                        "public_quality",
                        "quality_marker",
                    }
                    or item_layout_source in {
                        "quality_only",
                        "quality_reveal",
                        "public_quality",
                    }
                    or cells_value <= 0
                )
            )
            if marker_only:
                marker_size = max(6, min(11, int(round(cell * 0.55))))
                if item_value > 0:
                    marker_size = max(marker_size, 8)
                dot_x = (x1 + x2) / 2
                dot_y = (y1 + y2) / 2
                marker_x1 = int(round(dot_x - marker_size / 2))
                marker_y1 = int(round(dot_y - marker_size / 2))
                marker_x2 = marker_x1 + marker_size
                marker_y2 = marker_y1 + marker_size
                marker_fill = (
                    _blend_hex(MINIMAP_BG, outline, 0.42)
                    if style.get("unknown")
                    else fill
                )
                canvas.create_oval(
                    marker_x1,
                    marker_y1,
                    marker_x2,
                    marker_y2,
                    fill=marker_fill,
                    outline=outline,
                    width=1,
                    tags=(tag,),
                )
            else:
                unknown_item = bool(style.get("unknown"))
                if unknown_item:
                    base_fill = _blend_hex(MINIMAP_BG, outline, 0.42)
                    canvas.create_rectangle(
                        x1,
                        y1,
                        x2,
                        y2,
                        fill=base_fill,
                        outline=outline,
                        width=1,
                        tags=(tag,),
                    )
                    self._draw_unknown_quality_fill(
                        canvas,
                        x1,
                        y1,
                        x2,
                        y2,
                        color=outline,
                        tag=tag,
                    )
                else:
                    canvas.create_rectangle(
                        x1,
                        y1,
                        x2,
                        y2,
                        fill=fill,
                        outline=outline,
                        width=1,
                        tags=(tag,),
                    )
            tooltip = _text(item.get("tooltip") or item.get("label") or quality, "")
            if tip is not None:
                canvas.tag_bind(tag, "<Enter>", lambda e, text=tooltip, hover=tip: hover.show_at(e, text))
                canvas.tag_bind(tag, "<Motion>", lambda e, text=tooltip, hover=tip: hover.show_at(e, text))
                canvas.tag_bind(tag, "<Leave>", lambda _e, hover=tip: hover.hide())

    def _cancel_hide_minimap_popup(self, _event: tk.Event[Any] | None = None) -> None:
        if self._hide_minimap_after_id is None:
            return
        try:
            self.root.after_cancel(self._hide_minimap_after_id)
        except tk.TclError:
            pass
        self._hide_minimap_after_id = None

    def _schedule_hide_minimap_popup(self, _event: tk.Event[Any] | None = None) -> None:
        self._cancel_hide_minimap_popup()
        self._hide_minimap_after_id = self.root.after(160, self._hide_minimap_popup)

    def _hide_minimap_popup(self) -> None:
        self._hide_minimap_after_id = None
        if self._popup_canvas is not None:
            self._minimap_canvas_signatures.pop(id(self._popup_canvas), None)
        if self._minimap_popup is not None:
            try:
                self._minimap_popup.destroy()
            except tk.TclError:
                pass
        self._minimap_popup = None
        self._popup_canvas = None
        self._popup_title = None
        self._popup_counts = None
        self._popup_canvas_tip = None

    def _show_minimap_popup(self, event: tk.Event[Any] | None = None) -> None:
        if self._pinned_minimap_popup is not None:
            return
        self._cancel_hide_minimap_popup()
        if self._minimap_popup is None:
            popup = tk.Toplevel(self.root)
            popup.withdraw()
            popup.overrideredirect(True)
            popup.attributes("-topmost", bool(getattr(self, "topmost_enabled", True)))
            _apply_windows_toolwindow(popup, enabled=not self.show_taskbar)
            popup.configure(bg=BG)
            shell = self._card(popup, bg=PANEL, padx=7, pady=7)
            shell.pack(fill="both", expand=True)
            header = tk.Frame(shell, bg=PANEL)
            header.pack(fill="x", pady=(0, 5))
            self._popup_title = tk.Label(
                header,
                text="小地图",
                bg=PANEL,
                fg=MUTED,
                font=(FONT_UI, 8, "bold"),
                anchor="w",
            )
            self._popup_title.pack(side="left", fill="x", expand=True)
            self._popup_counts = tk.Label(
                header,
                text="-",
                bg=PANEL,
                fg=MUTED,
                font=(FONT_UI, 7),
                anchor="e",
            )
            self._popup_counts.pack(side="right")
            self._popup_canvas = tk.Canvas(
                shell,
                width=206,
                height=248,
                bg=MINIMAP_BG,
                highlightthickness=1,
                highlightbackground=BORDER,
            )
            self._popup_canvas.pack(fill="both", expand=True)
            self._popup_canvas_tip = HoverTip(self._popup_canvas)
            popup.bind("<Enter>", self._cancel_hide_minimap_popup, add="+")
            popup.bind("<Leave>", self._schedule_hide_minimap_popup, add="+")
            self._popup_canvas.bind("<Enter>", self._cancel_hide_minimap_popup, add="+")
            self._popup_canvas.bind("<Leave>", self._schedule_hide_minimap_popup, add="+")
            self._minimap_popup = popup
        popup_w = 222
        popup_h = 292
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        popup_x = root_x + root_w + 8
        popup_y = root_y + 8
        if popup_x + popup_w > screen_w:
            popup_x = root_x
            popup_y = root_y + root_h + 8
        if popup_y + popup_h > screen_h:
            popup_y = root_y - popup_h - 8
        popup_x = max(0, min(popup_x, max(0, screen_w - popup_w)))
        popup_y = max(0, min(popup_y, max(0, screen_h - popup_h)))
        self._minimap_popup.geometry(f"{popup_w}x{popup_h}+{popup_x}+{popup_y}")
        self._redraw_minimap_popup()
        self._minimap_popup.deiconify()

    def _redraw_minimap_popup(self) -> None:
        if (
            self._minimap_popup is None
            or self._popup_canvas is None
            or self._popup_title is None
            or self._popup_counts is None
        ):
            return
        self._render_minimap_header(
            title=self._popup_title,
            counts=self._popup_counts,
            minimap=self._minimap_data,
        )
        self._draw_minimap(
            self._popup_canvas,
            self._minimap_data,
            self._popup_canvas_tip,
            min_width=206,
            min_height=248,
        )

    def _hide_pinned_minimap(self) -> None:
        if self._pinned_configure_after_id is not None:
            try:
                self.root.after_cancel(self._pinned_configure_after_id)
            except tk.TclError:
                pass
            self._pinned_configure_after_id = None
        if self._pinned_canvas is not None:
            self._minimap_canvas_signatures.pop(id(self._pinned_canvas), None)
        if self._pinned_minimap_popup is not None:
            try:
                self._pinned_minimap_popup.destroy()
            except tk.TclError:
                pass
        self._pinned_minimap_popup = None
        self._pinned_canvas = None
        self._pinned_title = None
        self._pinned_counts = None
        self._pinned_canvas_tip = None
        self._pinned_offset = None
        self._pinned_minimap_follow = True
        self._pinned_minimap_drag_offset = None
        if hasattr(self, "map_button"):
            self.map_button.configure(bg=PANEL_SOFT, fg=ACCENT)

    def _popup_geometry_bounds(
        self,
        *,
        popup_w: int,
        popup_h: int,
        root_x: int,
        root_y: int,
    ) -> tuple[int, int]:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = max(0, min(root_x, max(0, screen_w - popup_w)))
        y = max(0, min(root_y, max(0, screen_h - popup_h)))
        return x, y

    def _sync_pinned_minimap_position(
        self,
        *,
        root_x: int | None = None,
        root_y: int | None = None,
    ) -> None:
        if (
            self._pinned_minimap_popup is None
            or self._pinned_offset is None
            or not getattr(self, "_pinned_minimap_follow", True)
        ):
            return
        if root_x is None:
            root_x = self.root.winfo_x()
        if root_y is None:
            root_y = self.root.winfo_y()
        offset_x, offset_y = self._pinned_offset
        popup_w = max(1, self._pinned_minimap_popup.winfo_width() or 292)
        popup_h = max(1, self._pinned_minimap_popup.winfo_height() or 382)
        popup_x, popup_y = self._popup_geometry_bounds(
            popup_w=popup_w,
            popup_h=popup_h,
            root_x=root_x + offset_x,
            root_y=root_y + offset_y,
        )
        self._pinned_minimap_popup.geometry(f"+{popup_x}+{popup_y}")

    def _bind_pinned_minimap_drag(self, *widgets: tk.Widget) -> None:
        for widget in widgets:
            widget.bind("<ButtonPress-1>", self._begin_pinned_minimap_drag, add="+")
            widget.bind("<B1-Motion>", self._drag_pinned_minimap, add="+")
            widget.bind("<ButtonRelease-1>", self._end_pinned_minimap_drag, add="+")

    def _begin_pinned_minimap_drag(self, event: tk.Event[Any]) -> str:
        if self._pinned_minimap_popup is None:
            return ""
        self._pinned_minimap_drag_offset = (
            event.x_root - self._pinned_minimap_popup.winfo_x(),
            event.y_root - self._pinned_minimap_popup.winfo_y(),
        )
        return "break"

    def _drag_pinned_minimap(self, event: tk.Event[Any]) -> str:
        if self._pinned_minimap_popup is None or self._pinned_minimap_drag_offset is None:
            return ""
        dx, dy = self._pinned_minimap_drag_offset
        popup_w = max(1, self._pinned_minimap_popup.winfo_width() or 292)
        popup_h = max(1, self._pinned_minimap_popup.winfo_height() or 382)
        popup_x, popup_y = self._popup_geometry_bounds(
            popup_w=popup_w,
            popup_h=popup_h,
            root_x=event.x_root - dx,
            root_y=event.y_root - dy,
        )
        self._pinned_minimap_popup.geometry(f"+{popup_x}+{popup_y}")
        if getattr(self, "_pinned_minimap_follow", True):
            self._pinned_minimap_follow = False
            self._pinned_offset = None
            self._mark_pinned_minimap_detached()
        return "break"

    def _end_pinned_minimap_drag(self, _event: tk.Event[Any]) -> None:
        self._pinned_minimap_drag_offset = None

    def _mark_pinned_minimap_detached(self) -> None:
        if self._pinned_title is None:
            return
        current = str(self._pinned_title.cget("text") or "")
        if not current.endswith(MINIMAP_PINNED_FREE_SUFFIX):
            self._pinned_title.configure(text=f"{current}{MINIMAP_PINNED_FREE_SUFFIX}")

    def _on_pinned_minimap_configure(self, event: tk.Event[Any]) -> None:
        if self._pinned_canvas is None or event.widget is not self._pinned_canvas:
            return
        if self._pinned_configure_after_id is not None:
            try:
                self.root.after_cancel(self._pinned_configure_after_id)
            except tk.TclError:
                pass
        self._pinned_configure_after_id = self.root.after(80, self._redraw_pinned_minimap)

    def toggle_pinned_minimap(self, event: tk.Event[Any] | None = None) -> str:
        self._hide_minimap_popup()
        if self._pinned_minimap_popup is not None:
            self._hide_pinned_minimap()
            return "break"

        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", bool(getattr(self, "topmost_enabled", True)))
        _apply_windows_toolwindow(popup, enabled=not self.show_taskbar)
        popup.configure(bg=BG)
        shell = self._card(popup, bg=PANEL, padx=7, pady=7)
        shell.pack(fill="both", expand=True)
        header = tk.Frame(shell, bg=PANEL)
        header.pack(fill="x", pady=(0, 5))
        self._pinned_title = tk.Label(
            header,
            text="常驻地图",
            bg=PANEL,
            fg=TEXT,
            font=(FONT_UI, 8, "bold"),
            anchor="w",
        )
        self._pinned_title.pack(side="left", fill="x", expand=True)
        self._pinned_counts = tk.Label(
            header,
            text="-",
            bg=PANEL,
            fg=MUTED,
            font=(FONT_UI, 7),
            anchor="e",
        )
        self._pinned_counts.pack(side="left", padx=(6, 8))
        close = tk.Button(
            header,
            text="×",
            command=self._hide_pinned_minimap,
            bg=BAD,
            fg="#ffffff",
            activebackground="#ff8aa0",
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=5,
            pady=0,
            font=(FONT_UI, 8, "bold"),
        )
        close.pack(side="right")
        self._bind_pinned_minimap_drag(header, shell, self._pinned_title, self._pinned_counts)
        HoverTip(header, MINIMAP_PINNED_DRAG_TIP)

        canvas_frame = tk.Frame(shell, bg=PANEL)
        canvas_frame.pack(fill="both", expand=True)
        self._pinned_canvas = tk.Canvas(
            canvas_frame,
            width=260,
            height=320,
            bg=MINIMAP_BG,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        vbar = _slim_scrollbar(canvas_frame, command=self._pinned_canvas.yview)
        self._pinned_canvas.configure(yscrollcommand=vbar.set)
        self._pinned_canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        self._pinned_canvas_tip = HoverTip(self._pinned_canvas)
        self._pinned_canvas.bind("<MouseWheel>", self._scroll_pinned_minimap, add="+")
        self._pinned_canvas.bind("<Configure>", self._on_pinned_minimap_configure, add="+")

        popup_w = 292
        popup_h = 382
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        popup_x = root_x + root_w + 8
        popup_y = root_y + 8
        if popup_x + popup_w > screen_w:
            popup_x = root_x
            popup_y = root_y + root_h + 8
        if popup_y + popup_h > screen_h:
            popup_y = root_y - popup_h - 8
        popup_x = max(0, min(popup_x, max(0, screen_w - popup_w)))
        popup_y = max(0, min(popup_y, max(0, screen_h - popup_h)))
        popup.geometry(f"{popup_w}x{popup_h}+{popup_x}+{popup_y}")
        self._pinned_offset = (popup_x - root_x, popup_y - root_y)
        self._pinned_minimap_follow = True
        self._pinned_minimap_drag_offset = None
        self._pinned_minimap_popup = popup
        self.map_button.configure(bg=PANEL_MUTED, fg=WARM)
        popup.deiconify()
        popup.update_idletasks()
        self._redraw_pinned_minimap()
        return "break"

    def _redraw_pinned_minimap(self) -> None:
        self._pinned_configure_after_id = None
        if (
            self._pinned_minimap_popup is None
            or self._pinned_canvas is None
            or self._pinned_title is None
            or self._pinned_counts is None
        ):
            return
        self._render_minimap_header(
            title=self._pinned_title,
            counts=self._pinned_counts,
            minimap=self._minimap_data,
        )
        if not getattr(self, "_pinned_minimap_follow", True):
            self._mark_pinned_minimap_detached()
        self._draw_minimap(
            self._pinned_canvas,
            self._minimap_data,
            self._pinned_canvas_tip,
            min_width=260,
            min_height=320,
            allow_scroll=True,
            cell_hint=self._minimap_cell_hint(MINIMAP_POPUP_CELL_HINT_BASE),
        )

    def _snapshot_signature(self) -> tuple[int, int]:
        try:
            stat = self.snapshot_path.stat()
        except OSError:
            return (0, 0)
        return (stat.st_mtime_ns, stat.st_size)

    def _snapshot_file_age_seconds(self) -> float | None:
        try:
            return max(0.0, time.time() - self.snapshot_path.stat().st_mtime)
        except OSError:
            return None

    def _capture_status(self) -> dict[str, Any]:
        return _read_json(self.snapshot_path.parent / "capture_source_status.json")

    def _record_summary_diagnostic(
        self,
        data: dict[str, Any],
        *,
        render_mode: str,
    ) -> None:
        if (
            _normalize_diagnostic_profile(
                getattr(self, "diagnostic_profile", DEFAULT_DIAGNOSTIC_PROFILE)
            )
            != "engineering"
        ):
            return
        try:
            row = _summary_diagnostic_row(
                data,
                snapshot_path=self.snapshot_path,
                render_mode=render_mode,
                manual_active=bool(self._manual_active),
                settlement_values_hidden=bool(self.settlement_values_hidden),
            )
            raw_source_snapshot = getattr(self, "_last_live_snapshot", {})
            source_snapshot = raw_source_snapshot if isinstance(raw_source_snapshot, dict) else {}
            row["source_files"] = {
                "file": source_snapshot.get("file"),
                "raw_capture": source_snapshot.get("raw_capture"),
                "raw_capture_jsonl": source_snapshot.get("raw_capture_jsonl"),
            }
            signature = _summary_diagnostic_signature(row)
            if signature == self._last_summary_log_signature:
                return
            self._last_summary_log_signature = signature
            log_path = self.snapshot_path.parent / SUMMARY_DIAGNOSTIC_LOG
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
        except Exception:
            return

    def _record_ui_health(self, row: dict[str, Any]) -> None:
        try:
            log_path = self.snapshot_path.parent / UI_HEALTH_LOG
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                fh.write("\n")
        except Exception:
            return

    def _record_ui_runtime_status(
        self,
        event: str,
        *,
        snapshot_signature: tuple[int, int] | None = None,
        capture_status: dict[str, Any] | None = None,
        error: Any = None,
    ) -> None:
        try:
            status_path = self.snapshot_path.parent / UI_RUNTIME_STATUS
            status_path.parent.mkdir(parents=True, exist_ok=True)
            signature = snapshot_signature
            if signature is None:
                signature = self._snapshot_signature()
            last_signature = getattr(self, "_last_signature", None)
            summary = getattr(self, "_last_summary", {})
            if not isinstance(summary, dict):
                summary = {}
            context = summary.get("context") if isinstance(summary.get("context"), dict) else {}
            reference = summary.get("reference") if isinstance(summary.get("reference"), dict) else {}
            age = self._snapshot_file_age_seconds()
            summary_worker_running = bool(getattr(self, "_summary_worker_running", False))
            manual_worker_running = bool(getattr(self, "_manual_worker_running", False))
            manual_active = bool(getattr(self, "_manual_active", False))
            manual_edit_enabled = bool(getattr(self, "_manual_edit_enabled", False))
            status_key = (
                event,
                signature,
                _capture_status_signature(capture_status or {}),
                summary.get("status"),
                context.get("session_id"),
                context.get("phase"),
                reference.get("source"),
                summary_worker_running,
                manual_worker_running,
                manual_active,
                manual_edit_enabled,
                _text(error, ""),
            )
            now_monotonic = time.monotonic()
            last_status_key = getattr(self, "_last_ui_runtime_status_key", None)
            last_status_at = float(getattr(self, "_last_ui_runtime_status_at", 0.0))
            if (
                status_key == last_status_key
                and now_monotonic - last_status_at < UI_RUNTIME_STATUS_REPEAT_INTERVAL_SECONDS
            ):
                return
            payload: dict[str, Any] = {
                "logged_at": time.time(),
                "event": event,
                "snapshot_path": str(self.snapshot_path),
                "snapshot_exists": signature != (0, 0),
                "snapshot_signature": list(signature),
                "snapshot_age_seconds": None if age is None else round(age, 3),
                "last_applied_signature": list(last_signature)
                if isinstance(last_signature, tuple)
                else None,
                "diagnostic_profile": getattr(
                    self,
                    "diagnostic_profile",
                    DEFAULT_DIAGNOSTIC_PROFILE,
                ),
                "summary_worker_running": summary_worker_running,
                "manual_worker_running": manual_worker_running,
                "manual_active": manual_active,
                "manual_edit_enabled": manual_edit_enabled,
                "last_summary": {
                    "status": summary.get("status"),
                    "hero": context.get("hero"),
                    "map_id": context.get("map_id"),
                    "round": context.get("round"),
                    "phase": context.get("phase"),
                    "session_id": context.get("session_id"),
                    "reference_source": reference.get("source"),
                },
            }
            if capture_status is not None:
                payload["capture"] = _compact_capture_runtime_status(capture_status)
            if error is not None:
                payload["error"] = _text(error, "")
            tmp = status_path.with_name(
                f"{status_path.name}.{threading.get_ident()}.tmp"
            )
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(status_path)
            self._last_ui_runtime_status_key = status_key
            self._last_ui_runtime_status_at = now_monotonic
        except Exception:
            return

    def _start_ui_health_watchdog(self) -> None:
        def _watch() -> None:
            while not bool(getattr(self, "_exit_cleanup_done", True)):
                time.sleep(1.0)
                now = time.monotonic()
                last = float(getattr(self, "_last_ui_heartbeat_at", now))
                gap_seconds = max(0.0, now - last)
                if gap_seconds < UI_STALL_SECONDS:
                    continue
                bucket = int(gap_seconds // UI_STALL_LOG_INTERVAL_SECONDS)
                if bucket == int(getattr(self, "_last_ui_stall_bucket", 0)):
                    continue
                self._last_ui_stall_bucket = bucket
                self._record_ui_health(
                    {
                        "logged_at": time.time(),
                        "event": "ui_event_loop_stall_suspected",
                        "gap_seconds": round(gap_seconds, 3),
                        "snapshot_path": str(self.snapshot_path),
                        "diagnostic_profile": getattr(
                            self,
                            "diagnostic_profile",
                            DEFAULT_DIAGNOSTIC_PROFILE,
                        ),
                    }
                )

        self._ui_health_thread = threading.Thread(
            target=_watch,
            name="HeroRefUIHealthWatchdog",
            daemon=True,
        )
        self._ui_health_thread.start()

    def _needs_stale_refresh(self) -> bool:
        summary = self._last_live_summary if self._manual_active else self._last_summary
        if not summary or summary.get("status") == "stale_snapshot":
            return False
        context = summary.get("context") if isinstance(summary.get("context"), dict) else {}
        phase = _text(context.get("phase"), "")
        threshold = SETTLED_STALE_SECONDS if phase == "settled" else STALE_SNAPSHOT_SECONDS
        age = self._snapshot_file_age_seconds()
        return age is not None and age >= threshold

    def _mark_summary_performance(
        self,
        summary: dict[str, Any],
        key: str,
        started_at: float,
    ) -> None:
        diagnostics = summary.setdefault("diagnostics", {})
        if not isinstance(diagnostics, dict):
            diagnostics = {}
            summary["diagnostics"] = diagnostics
        performance = diagnostics.setdefault("performance", {})
        if not isinstance(performance, dict):
            performance = {}
            diagnostics["performance"] = performance
        performance[key] = round((time.perf_counter() - started_at) * 1000.0, 2)

    def _apply_live_summary(self, snapshot: dict[str, Any], summary: dict[str, Any]) -> None:
        self._last_live_snapshot = snapshot
        self._last_live_summary = summary
        if self._should_reset_manual_for_summary(summary):
            self._reset_manual_state("已自动清空，等待新局", status_fg=DIM)
        if self._manual_active:
            if not self._manual_live_session_id:
                self._manual_live_session_id = self._summary_session_id(summary)
            self.manual_status.configure(text="手动结果，实时后台", fg=WARM)
        elif getattr(self, "_manual_edit_enabled", False):
            self._set_manual_settlement_button_state()
        else:
            self._auto_sync_manual_inputs(summary)
            self._last_summary = summary
            if summary.get("status") == "stale_snapshot":
                self.render_standby(summary)
            else:
                self.render(summary)

    def _start_live_summary_worker(
        self,
        *,
        snapshot: dict[str, Any],
        signature: tuple[int, int],
        started_at: float,
    ) -> bool:
        if not hasattr(self, "_summary_result_queue"):
            return False
        if bool(getattr(self, "_summary_worker_running", False)):
            if getattr(self, "_summary_worker_signature", None) == signature:
                return True
            self._summary_worker_pending = {
                "snapshot": snapshot,
                "signature": signature,
                "started_at": started_at,
            }
            return True
        self._summary_worker_running = True
        self._summary_worker_signature = signature
        self._summary_worker_seq = int(getattr(self, "_summary_worker_seq", 0)) + 1
        seq = self._summary_worker_seq
        snapshot_path = self.snapshot_path
        result_queue = self._summary_result_queue

        def _worker() -> None:
            worker_started = time.perf_counter()
            try:
                summary = summarize_snapshot(snapshot, snapshot_path=snapshot_path)
                self._mark_summary_performance(summary, "refresh_worker_ms", worker_started)
                self._mark_summary_performance(summary, "refresh_total_ms", started_at)
                result_queue.put(
                    {
                        "seq": seq,
                        "signature": signature,
                        "snapshot": snapshot,
                        "summary": summary,
                    }
                )
            except Exception as exc:  # noqa: BLE001 - surface worker error in UI health
                result_queue.put(
                    {
                        "seq": seq,
                        "signature": signature,
                        "snapshot": snapshot,
                        "error": repr(exc),
                    }
                )

        threading.Thread(target=_worker, daemon=True, name="hero-ref-summary").start()
        return True

    def _maybe_start_pending_summary_worker(self) -> None:
        pending = getattr(self, "_summary_worker_pending", None)
        if not isinstance(pending, dict):
            return
        self._summary_worker_pending = None
        snapshot = pending.get("snapshot")
        signature = pending.get("signature")
        started_at = pending.get("started_at")
        if not isinstance(snapshot, dict) or not isinstance(signature, tuple):
            return
        if not isinstance(started_at, (int, float)):
            started_at = time.perf_counter()
        self._start_live_summary_worker(
            snapshot=snapshot,
            signature=signature,
            started_at=float(started_at),
        )

    def _drain_live_summary_results(self) -> None:
        if not hasattr(self, "_summary_result_queue"):
            return
        latest: dict[str, Any] | None = None
        while True:
            try:
                item = self._summary_result_queue.get_nowait()
            except queue.Empty:
                break
            if latest is None or int(item.get("seq") or 0) >= int(latest.get("seq") or 0):
                latest = item
        if latest is None:
            return
        seq = latest.get("seq")
        if seq != getattr(self, "_summary_worker_seq", None):
            return
        self._summary_worker_running = False
        signature = latest.get("signature")
        if signature != getattr(self, "_summary_worker_signature", None):
            return
        if latest.get("error"):
            self._record_ui_health(
                {
                    "logged_at": time.time(),
                    "event": "summary_worker_error",
                    "error": latest.get("error"),
                    "snapshot_path": str(self.snapshot_path),
                }
            )
            self._record_ui_runtime_status(
                "summary_worker_error",
                snapshot_signature=signature if isinstance(signature, tuple) else None,
                error=latest.get("error"),
            )
            self._summary_worker_signature = None
            self._maybe_start_pending_summary_worker()
            return
        summary = latest.get("summary")
        snapshot = latest.get("snapshot")
        if not isinstance(summary, dict) or not isinstance(snapshot, dict):
            self._summary_worker_signature = None
            self._maybe_start_pending_summary_worker()
            return
        if getattr(self, "_summary_worker_pending", None) is not None:
            self._summary_worker_signature = None
            self._maybe_start_pending_summary_worker()
            return
        self._last_signature = signature
        self._summary_worker_signature = None
        self._apply_live_summary(snapshot, summary)
        self._record_ui_runtime_status(
            "summary_applied",
            snapshot_signature=signature if isinstance(signature, tuple) else None,
        )
        self._maybe_start_pending_summary_worker()

    def _start_manual_summary_worker(
        self,
        *,
        snapshot: dict[str, Any],
        settlement_manual: bool,
        live_session_id: str,
        revision: int,
    ) -> bool:
        if not hasattr(self, "_manual_result_queue"):
            return False
        if bool(getattr(self, "_manual_worker_running", False)):
            if hasattr(self, "manual_status"):
                self.manual_status.configure(text="手动计算中，请稍候", fg=WARM)
            return True
        self._manual_worker_running = True
        self._manual_worker_seq = int(getattr(self, "_manual_worker_seq", 0)) + 1
        seq = self._manual_worker_seq
        result_queue = self._manual_result_queue

        def _worker() -> None:
            try:
                summary = self._manual_result_summary(snapshot)
                result_queue.put(
                    {
                        "seq": seq,
                        "snapshot": snapshot,
                        "summary": summary,
                        "settlement_manual": settlement_manual,
                        "live_session_id": live_session_id,
                        "revision": revision,
                    }
                )
            except Exception as exc:  # noqa: BLE001 - show calculation failure in UI
                result_queue.put(
                    {
                        "seq": seq,
                        "error": repr(exc),
                        "revision": revision,
                    }
                )

        threading.Thread(target=_worker, daemon=True, name="hero-ref-manual").start()
        if hasattr(self, "manual_status"):
            self.manual_status.configure(text="手动计算中...", fg=WARM)
        return True

    def _drain_manual_summary_results(self) -> None:
        if not hasattr(self, "_manual_result_queue"):
            return
        latest: dict[str, Any] | None = None
        while True:
            try:
                latest = self._manual_result_queue.get_nowait()
            except queue.Empty:
                break
        if latest is None:
            return
        self._manual_worker_running = False
        if latest.get("seq") != getattr(self, "_manual_worker_seq", None):
            return
        if latest.get("revision") != getattr(self, "_manual_input_revision", 0):
            if hasattr(self, "manual_status"):
                self.manual_status.configure(text="输入已改动，请重新应用", fg=WARM)
            return
        if latest.get("error"):
            if hasattr(self, "manual_status"):
                self.manual_status.configure(text=f"计算失败: {latest['error']}", fg=BAD)
            return
        summary = latest.get("summary")
        snapshot = latest.get("snapshot")
        if not isinstance(summary, dict) or not isinstance(snapshot, dict):
            return
        settlement_manual = bool(latest.get("settlement_manual"))
        self._manual_active = True
        self._set_manual_edit_enabled(True)
        self._manual_snapshot = snapshot
        self._manual_summary = summary
        self._last_summary = summary
        self._manual_live_session_id = _text(latest.get("live_session_id"), "")
        if hasattr(self, "manual_status"):
            self.manual_status.configure(
                text="手动计算，结算页已脱离" if settlement_manual else "手动计算，实时后台",
                fg=WARM,
            )
        self._set_manual_button_state()
        if summary.get("status") == "stale_snapshot":
            self.render_standby(summary)
        else:
            self.render(summary)

    def refresh(self) -> None:
        refresh_started = time.perf_counter()
        heartbeat_now = time.monotonic()
        heartbeat_gap = heartbeat_now - float(
            getattr(self, "_last_ui_heartbeat_at", heartbeat_now)
        )
        self._last_ui_heartbeat_at = heartbeat_now
        self._last_ui_stall_bucket = 0
        self._drain_live_summary_results()
        self._drain_manual_summary_results()
        if heartbeat_gap >= UI_STALL_SECONDS:
            self._record_ui_health(
                {
                    "logged_at": time.time(),
                    "event": "ui_event_loop_recovered",
                    "gap_seconds": round(heartbeat_gap, 3),
                    "snapshot_path": str(self.snapshot_path),
                    "diagnostic_profile": getattr(
                        self,
                        "diagnostic_profile",
                        DEFAULT_DIAGNOSTIC_PROFILE,
                    ),
                }
            )
        should_reschedule = True
        try:
            if self.exit_when_pids and _watched_pid_exited(self.exit_when_pids):
                should_reschedule = False
                self._record_ui_runtime_status("watched_monitor_exit")
                self._save_ui_prefs_if_enabled()
                self._run_exit_cleanup()
                self.root.destroy()
                return
            signature = self._snapshot_signature()
            capture_status = self._capture_status()
            capture_signature: tuple[Any, ...] = ()
            if signature == (0, 0):
                capture_signature = _capture_status_signature(capture_status)
            capture_changed = (
                signature == (0, 0)
                and capture_signature != self._last_capture_status_signature
            )
            if (
                signature != self._last_signature
                or capture_changed
                or self._needs_stale_refresh()
            ):
                snapshot = _read_json(self.snapshot_path)
                if snapshot:
                    self._last_capture_status_signature = None
                    if self._start_live_summary_worker(
                        snapshot=snapshot,
                        signature=signature,
                        started_at=refresh_started,
                    ):
                        self._record_ui_runtime_status(
                            "summary_worker_started",
                            snapshot_signature=signature,
                            capture_status=capture_status,
                        )
                    else:
                        summary = summarize_snapshot(snapshot, snapshot_path=self.snapshot_path)
                        self._mark_summary_performance(summary, "refresh_total_ms", refresh_started)
                        self._last_signature = signature
                        self._apply_live_summary(snapshot, summary)
                        self._record_ui_runtime_status(
                            "summary_applied",
                            snapshot_signature=signature,
                            capture_status=capture_status,
                        )
                else:
                    self._last_capture_status_signature = capture_signature
                    if not self._manual_active and not getattr(self, "_manual_edit_enabled", False):
                        self.render_missing("等待 latest_snapshot.json")
                    self._record_ui_runtime_status(
                        "waiting_for_snapshot",
                        snapshot_signature=signature,
                        capture_status=capture_status,
                    )
            else:
                self._record_ui_runtime_status(
                    "idle_no_change",
                    snapshot_signature=signature,
                    capture_status=capture_status,
                )
        finally:
            self._last_ui_heartbeat_at = time.monotonic()
            if should_reschedule and not bool(getattr(self, "_exit_cleanup_done", False)):
                self.root.after(self.interval_ms, self.refresh)

    def render_missing(self, message: str) -> None:
        capture_status = self._capture_status()
        diagnostics = _capture_wait_diagnostics(capture_status)
        self.title.configure(text="Hero Ref")
        self.subtitle.configure(text=diagnostics.get("subtitle") or message)
        self.status.configure(text=time.strftime("%H:%M:%S"))
        self._render_flags(diagnostics.get("flags") or [{"label": "无实时数据", "level": "watch", "detail": ""}])
        self._set_settlement_button_state({})
        self._clear_values()
        self._set_label(self.action_rows["动作"], diagnostics.get("action"), limit=18)
        self._set_label(self.action_rows["最近"], diagnostics.get("recent"), limit=20)
        self._set_label(self.action_rows["候选"], "-", limit=18)
        self._set_label(
            self.action_rows["下一步"],
            diagnostics.get("action") or diagnostics.get("state") or diagnostics.get("source"),
            limit=18,
        )
        self._set_label(self.evidence_rows["匹配"], diagnostics.get("state"), limit=28)
        self._set_label(self.evidence_rows["密度"], diagnostics.get("detail"), limit=34)
        self._set_label(self.evidence_rows["诊断"], diagnostics.get("recent"), limit=28)
        self._set_label(self.detail_rows["外援"], "waiting", limit=18)
        self._set_label(self.detail_rows["备注"], diagnostics.get("note"), limit=42)
        self._render_minimap({})
        self._record_summary_diagnostic(
            {
                "status": "missing_snapshot",
                "evidence": {
                    "diagnostics": diagnostics.get("recent"),
                    "ref_notes": diagnostics.get("note"),
                },
                "flags": diagnostics.get("flags") or [],
                "stale": {"reason": "missing_snapshot"},
            },
            render_mode="missing",
        )

    def render_standby(self, data: dict[str, Any]) -> None:
        stale = data.get("stale") if isinstance(data.get("stale"), dict) else {}
        age = stale.get("age_seconds")
        age_text = f"{int(age)}s" if isinstance(age, (int, float)) else "unknown"
        reason = _text(stale.get("reason"), "stale_snapshot")
        title = "Hero Ref · 新局等待" if reason == "session_ahead" else "Hero Ref · 待机"
        self.title.configure(text=title)
        self.subtitle.configure(text=f"snapshot age={age_text}; 等待首个实时估价")
        self.status.configure(text=_text(data.get("updated_at_text"), "--:--"))
        self._render_flags(data.get("flags") or [{"label": "待机", "level": "neutral", "detail": ""}])
        self._set_settlement_button_state(data)
        self._clear_values()
        self._set_label(self.action_rows["动作"], "等待新局", limit=18)
        self._set_label(self.action_rows["最近"], "-", limit=18)
        self._set_label(self.action_rows["候选"], "-", limit=18)
        self._set_label(self.action_rows["下一步"], "standby", limit=18)
        self._update_detail_rows(data)
        self._render_minimap(data.get("minimap") or {})
        self._record_summary_diagnostic(data, render_mode="standby")

    def render(self, data: dict[str, Any]) -> None:
        context = data.get("context") or {}
        reference = data.get("reference") or {}
        red = data.get("red") or {}
        evidence = data.get("evidence") or {}
        hero = _text(context.get("hero"), "?")
        map_id = _text(context.get("map_id"), "?")
        round_text = _text(context.get("round"), "?")
        phase = _text(context.get("phase"), "?")
        source = _text(reference.get("source"), "-")
        self.title.configure(text=f"{hero} · {map_id} · R{round_text}")
        self.subtitle.configure(
            text=f"{phase} · {source} · {context.get('session_id') or '-'}"
        )
        self.status.configure(text=_text(data.get("updated_at_text"), "--:--"))
        self._render_flags(data.get("flags") or [])
        self._set_settlement_button_state(data)
        price_titles = reference.get("price_titles") if isinstance(reference.get("price_titles"), dict) else {}
        self._set_price_titles(price_titles)

        for key in ("conservative", "balanced", "aggressive"):
            text = self._settlement_display_value(data, reference.get(key))
            self.price_labels[key].configure(text=text)

        self._set_label(self.red_rows["红件"], red.get("count_range"), limit=18)
        self._set_label(self.red_rows["红格"], red.get("cells_range"), limit=18)
        self._set_label(self.red_rows["紫金件"], red.get("quality_count_summary"), limit=30)
        self._set_label(self.red_rows["红值"], self._settlement_display_value(data, red.get("value_range")), limit=24)
        self._set_label(
            self.red_rows["低品件"],
            red.get("uncertainty_summary") or red.get("risk_reference") or reference.get("risk_band"),
            limit=38,
        )
        self._set_label(self.action_rows["动作"], reference.get("action"), limit=18)
        self._set_label(self.action_rows["最高"], self._settlement_display_value(data, reference.get("current_highest")), limit=20)
        self._set_label(self.action_rows["最近"], self._latest_result_text(evidence), limit=20)
        self._set_label(
            self.action_rows["候选"],
            self._mini_candidate_text(data),
            limit=30,
        )
        self._set_label(
            self.action_rows["下一步"],
            self._mini_next_info_text(data),
            limit=30,
        )
        self._update_detail_rows(data)
        self._render_minimap(data.get("minimap") or {})
        mode = "manual_overlay" if self._manual_active else "live"
        if self._is_settlement_summary(data):
            mode = f"{mode}_settled"
        self._record_summary_diagnostic(data, render_mode=mode)

    def _latest_result_text(self, evidence: dict[str, Any]) -> str:
        latest = evidence.get("latest_result")
        if not isinstance(latest, dict) or not latest:
            latest = evidence.get("latest_sent")
        if not isinstance(latest, dict) or not latest:
            return "-"
        tool = latest.get("tool") or latest.get("action_id") or latest.get("name") or ""
        result = latest.get("result")
        if result in (None, ""):
            return _text(tool, "-")
        result_text = _format_manual_number(result)
        return f"{tool}={result_text}" if tool else _text(result_text)

    def _mini_input_text(self, evidence: dict[str, Any]) -> str:
        summary = _text(evidence.get("ref_input_summary"), "")
        compact_parts: list[str] = []
        if summary and summary != "-":
            for part in summary.split(" · "):
                if part.startswith(("总件 ", "总格 ", "估总格 ")):
                    compact_parts.append(part)
                if len(compact_parts) >= 2:
                    break
        if compact_parts:
            return " · ".join(compact_parts)
        return _text(evidence.get("ref_readiness") or evidence.get("ref_status"), "-")

    def _mini_candidate_text(self, data: dict[str, Any]) -> str:
        evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
        candidate = _text(evidence.get("candidate_summary"), "").strip()
        if candidate and candidate != "-":
            return candidate
        return self._mini_input_text(evidence)

    def _mini_next_info_text(self, data: dict[str, Any]) -> str:
        evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
        hint = _text(evidence.get("next_info_hint"), "").strip()
        if hint and hint != "-":
            return hint
        ref_result = data.get("ahmed_ref") if isinstance(data.get("ahmed_ref"), dict) else {}
        context = data.get("context") if isinstance(data.get("context"), dict) else {}
        hero_key = normalize_hero_key(context.get("hero") or "")
        hint = _next_info_hint(
            ref_result,
            hero_key=hero_key,
            round_no=_parse_int(context.get("round")),
        )
        if hint and hint != "-":
            return hint
        return _text(evidence.get("ref_readiness") or evidence.get("ref_status"), "-")

    def _input_evidence_text(self, evidence: dict[str, Any]) -> str:
        parts = []
        for key in ("ref_input_summary", "public_numeric_summary", "minimap_quality_summary"):
            text = _text(evidence.get(key), "").strip()
            if text and text != "-" and text not in parts:
                parts.append(text)
        return " · ".join(parts) if parts else "-"

    def _truth_text(self, data: dict[str, Any]) -> str:
        truth = data.get("truth")
        if not isinstance(truth, dict) or not truth.get("available"):
            return "未结算"
        total_items = _text(truth.get("total_items"), "?")
        total_cells = _text(truth.get("total_cells"), "?")
        q6 = truth.get("q6") if isinstance(truth.get("q6"), dict) else {}
        q6_count = _text(q6.get("count"), "?")
        q6_cells = _text(q6.get("cells"), "?")
        if self._settlement_values_are_hidden(data):
            return f"价值隐藏 · {total_items}件/{total_cells}格 · 红{q6_count}件/{q6_cells}格"
        total = _text(truth.get("total_value"), "?")
        return f"{total} · {total_items}件/{total_cells}格 · 红{q6_count}件/{q6_cells}格"

    def _update_detail_rows(self, data: dict[str, Any]) -> None:
        reference = data.get("reference") if isinstance(data.get("reference"), dict) else {}
        red = data.get("red") if isinstance(data.get("red"), dict) else {}
        evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
        ahmed_ref = data.get("ahmed_ref") if isinstance(data.get("ahmed_ref"), dict) else {}

        self._set_label(self.evidence_rows["匹配"], evidence.get("match_text"), limit=26)
        self._set_label(self.evidence_rows["密度"], evidence.get("information_density"), limit=22)
        self._set_summary_label(self.evidence_rows["输入"], self._input_evidence_text(evidence))
        self._set_label(self.evidence_rows["组合"], evidence.get("ref_combo_count"), limit=22)
        self._set_label(self.evidence_rows["最近"], self._latest_result_text(evidence), limit=28)
        self._set_label(
            self.evidence_rows["诊断"],
            evidence.get("diagnostics") or evidence.get("ref_notes"),
            limit=34,
        )

        self._set_label(self.detail_rows["外援"], ahmed_ref.get("status") or reference.get("source"), limit=24)
        self._set_label(self.detail_rows["决策"], reference.get("decision_range"), limit=34)
        self._set_label(self.detail_rows["总格"], reference.get("total_grid_range"), limit=28)
        self._set_label(
            self.detail_rows["总值"],
            self._settlement_display_value(data, reference.get("total_value_range") or red.get("value_range")),
            limit=34,
        )
        self._set_label(self.detail_rows["红值"], self._settlement_display_value(data, red.get("value_range")), limit=34)
        self._set_label(self.detail_rows["结算"], self._truth_text(data), limit=38)
        self._set_label(self.detail_rows["备注"], reference.get("note") or evidence.get("ref_notes"), limit=38)

    def _set_details_mode(self, expanded: bool) -> None:
        was_expanded = self.details_expanded
        if expanded and not was_expanded:
            self._fit_mini_window_to_content()
            self._remember_mini_layout_snapshot()
        self.details_expanded = expanded
        if expanded:
            self.mode_button.configure(text="迷你")
            self.root.minsize(430, 360)
            if not self.details_card.winfo_ismapped():
                self.details_card.pack(fill="x", pady=(5, 0), before=self.footer_row)
            if not self.minimap_card.winfo_ismapped():
                self.minimap_card.pack(fill="x", pady=(5, 0), before=self.footer_row)
            self.root.update_idletasks()
            if self._custom_details_size is not None:
                self._apply_window_geometry(self._details_geometry(), flush=False)
                self._sync_ui_scale_from_window(force=True)
            else:
                current_w, _ = self._current_window_size()
                self._fit_details_window_to_content(width=current_w)
            self.root.update_idletasks()
        elif was_expanded:
            self._restore_mini_layout_after_details()
        else:
            self.mode_button.configure(text="详情")
            self.root.minsize(430, 395)
            self.details_card.pack_forget()
            self.minimap_card.pack_forget()
            self._reset_ui_scale_baseline()
            self._apply_window_geometry(self._mini_geometry())
            width, _ = self._current_window_size()
            self._apply_mini_resize_layout(width, finalize=True)
        self._schedule_ui_prefs_save()

    def toggle_details(self) -> None:
        self._set_details_mode(not self.details_expanded)

        def _refresh_details_panel() -> None:
            self._update_detail_rows(self._last_summary or {})
            if self.details_expanded:
                self._render_minimap(self._minimap_data)

        self.root.after_idle(_refresh_details_panel)

    def _minimap_cell_hint(self, base: float) -> float:
        return max(8.0, float(base) * float(self._ui_scale))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show isolated Ahmed reference Tk overlay.")
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT))
    parser.add_argument("--interval-ms", type=int, default=1000)
    parser.add_argument(
        "--load-existing",
        action="store_true",
        help="Render the current latest_snapshot.json immediately instead of starting in standby.",
    )
    parser.add_argument(
        "--show-taskbar",
        action="store_true",
        help="Use a normal taskbar/Alt-Tab window instead of the borderless floating overlay.",
    )
    parser.add_argument(
        "--diagnostic-profile",
        type=_parse_diagnostic_profile,
        metavar="{engineering,portable,public-safe}",
        default=_normalize_diagnostic_profile(
            os.environ.get(
                "BIDKING_HERO_REF_DIAGNOSTIC_PROFILE",
                DEFAULT_DIAGNOSTIC_PROFILE,
            )
        ),
        help=(
            "engineering writes full continuous UI diagnostics; portable skips "
            "continuous UI summary but keeps raw in manual exports; public-safe "
            "also omits raw from exports."
        ),
    )
    parser.add_argument(
        "--stop-pid-on-exit",
        type=int,
        action="append",
        default=[],
        help="Terminate this monitor PID when the Hero Ref overlay exits.",
    )
    parser.add_argument(
        "--cleanup-lock-on-exit",
        type=Path,
        action="append",
        default=[],
        help="Remove this monitor lock file after exit cleanup.",
    )
    parser.add_argument(
        "--exit-when-pid-exits",
        type=int,
        action="append",
        default=[],
        help="Close Hero Ref when this monitor PID exits.",
    )
    parser.add_argument(
        "--keep-monitor-on-close",
        action="store_true",
        help="Leave the live monitor running when Hero Ref exits.",
    )
    parser.add_argument(
        "--ui-prefs",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Load/save hero_ref_ui_prefs.json beside the snapshot log dir. "
            "Packaged Start-HeroRef enables this; dev scripts leave it off."
        ),
    )
    args = parser.parse_args(argv)

    root = tk.Tk()
    overlay = AhmadTkOverlay(
        root,
        snapshot_path=Path(args.snapshot),
        interval_ms=args.interval_ms,
        exit_when_pids=tuple(args.exit_when_pid_exits),
        stop_pids_on_exit=tuple(args.stop_pid_on_exit),
        cleanup_lock_paths=tuple(args.cleanup_lock_on_exit),
        keep_monitor_on_close=bool(args.keep_monitor_on_close),
        load_existing_snapshot=bool(args.load_existing),
        diagnostic_profile=args.diagnostic_profile,
        show_taskbar=bool(args.show_taskbar),
        ui_prefs_enabled=bool(args.ui_prefs),
    )
    try:
        root.mainloop()
    finally:
        overlay._save_ui_prefs_if_enabled()
        overlay._run_exit_cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
