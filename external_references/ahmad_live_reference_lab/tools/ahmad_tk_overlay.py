from __future__ import annotations

import argparse
import copy
import colorsys
import json
import math
import os
from pathlib import Path
import random
import signal
import sys
import time
import tkinter as tk
from tkinter import ttk
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
LAB_ROOT = TOOLS_DIR.parents[0]
LAB_SRC = LAB_ROOT / "src"
if str(LAB_SRC) not in sys.path:
    sys.path.insert(0, str(LAB_SRC))

from ahmad_live_panel_server import SETTLED_STALE_SECONDS, STALE_SNAPSHOT_SECONDS, summarize_snapshot  # noqa: E402

try:
    from ahmad_ref_engine import can_compose_grid_total, run_reference_engine  # noqa: E402
except Exception:  # noqa: BLE001 - keep overlay usable if ref core is unavailable
    can_compose_grid_total = None  # type: ignore[assignment]
    run_reference_engine = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SNAPSHOT = ROOT / "data" / "logs" / "live" / "latest_snapshot.json"

FONT_UI = "Microsoft YaHei UI"
FONT_NUMERIC = "Segoe UI Semibold"
MINIMAP_DEFAULT_COLUMNS = 10
MINIMAP_DEFAULT_ROWS = 13
MANUAL_FORM_COLUMNS = 6
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
    "unknown": {"fill": "#172033", "outline": "#64748b", "unknown": False},
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
        "BG": "#161a2b",
        "PANEL": "#232a43",
        "PANEL_SOFT": "#303a5e",
        "PANEL_MUTED": "#2d2945",
        "BORDER": "#596485",
        "TEXT": "#f8fbff",
        "MUTED": "#c8d2e4",
        "DIM": "#8fa0bd",
        "GOOD": "#61e6ad",
        "WARN": "#ffd166",
        "BAD": "#ff6f91",
        "ACCENT": "#69c7ff",
        "WARM": "#ffb86b",
        "MINIMAP_BG": "#111827",
        "MINIMAP_GRID": "#263244",
        "MINIMAP_TEXT": "#aebbd2",
        "QUALITY_COLORS": {
            key: value["fill"] for key, value in MAINLINE_QUALITY_STYLE.items()
        },
        "HERO_BUTTON_ACTIVE": "#3f4d79",
        "SCROLL_LINE": "#465476",
        "TOOLTIP_BG": "#151a2b",
        "MANUAL_BG": "#2b2947",
        "MANUAL_INPUT_BG": "#1b2136",
        "MANUAL_STATUS_BG": "#4a372b",
        "MANUAL_LABEL_FG": "#e0e6f3",
        "MINIMAP_ITEM_SHADOW": "#101525",
        "MINIMAP_ITEM_OUTLINE": "#101525",
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


def _normalize_manual_hero(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return HERO_ALIASES.get(text.lower(), HERO_ALIASES.get(text, text))


def _supported_manual_hero_display(*values: Any) -> Any:
    for value in values:
        normalized = _normalize_manual_hero(value)
        if normalized in {"aisha", "ahmed", "victor"}:
            return value
    return None


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
    return max(0, len(value.split(".", 1)[1].rstrip()))


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


def _cleanup_exit_targets(pids: tuple[int, ...], lock_paths: tuple[Path, ...]) -> None:
    seen: set[int] = set()
    for pid in pids:
        if pid in seen:
            continue
        seen.add(pid)
        _terminate_pid(int(pid))
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
        load_existing_snapshot: bool = False,
    ) -> None:
        self.root = root
        self.snapshot_path = snapshot_path
        self.interval_ms = max(300, int(interval_ms))
        self.exit_when_pids = exit_when_pids
        self._stop_pids_on_exit = tuple(pid for pid in stop_pids_on_exit if pid > 0)
        self._cleanup_lock_paths = tuple(cleanup_lock_paths)
        self._exit_cleanup_done = False
        self._last_signature: tuple[int, int] | None = None
        self._last_summary: dict[str, Any] = {}
        self._last_live_snapshot: dict[str, Any] = {}
        self._last_live_summary: dict[str, Any] = {}
        self._manual_snapshot: dict[str, Any] = {}
        self._manual_summary: dict[str, Any] = {}
        self._manual_active = False
        self._manual_live_session_id = ""
        self._manual_programmatic_update = False
        self._manual_dirty_fields: set[str] = set()
        self._manual_autofill_values: dict[str, str] = {}
        self._minimap_data: dict[str, Any] = {}
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
        self._hide_minimap_after_id: str | None = None
        self.details_expanded = False
        self._load_existing_snapshot = load_existing_snapshot
        self._drag_offset: tuple[int, int] | None = None
        self._resize_anchor: tuple[int, int, int, int] | None = None
        self._custom_details_size: tuple[int, int] | None = None
        self.theme_name = "dark"
        self.theme_values = _theme_by_name(self.theme_name)

        root.title("Hero Ref")
        root.configure(bg=BG)
        root.attributes("-topmost", True)
        root.overrideredirect(True)
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
            padding=(6, 3),
        )
        style.map("Hero.TButton", background=[("active", HERO_BUTTON_ACTIVE)])

        self.outer = tk.Frame(root, bg=BG)
        self.outer.pack(fill="both", expand=True)

        tk.Frame(self.outer, bg=WARM, width=3).pack(side="left", fill="y")
        self.shell = tk.Frame(self.outer, bg=BG, padx=7, pady=7)
        self.shell.pack(side="left", fill="both", expand=True)
        stripe = tk.Frame(self.shell, bg=BG)
        stripe.pack(fill="x", pady=(0, 6))
        tk.Frame(stripe, bg=ACCENT, height=2).pack(side="left", fill="x", expand=True)
        tk.Frame(stripe, bg=WARM, height=2, width=82).pack(side="right", padx=(6, 0))

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
            font=(FONT_UI, 13, "bold"),
            anchor="w",
        )
        self.title.pack(fill="x")
        self.subtitle = tk.Label(
            title_box,
            text="等待实时包",
            bg=BG,
            fg=MUTED,
            font=(FONT_UI, 8),
            anchor="w",
        )
        self.subtitle.pack(fill="x")
        self.credit_top = tk.Label(
            title_box,
            text="原作: 猫饭团子uu · UI/计算引擎优化: 加菲_barista",
            bg=BG,
            fg=DIM,
            font=(FONT_UI, 7),
            anchor="w",
        )
        self.title_tip = HoverTip(self.title, "原作: 猫饭团子uu · UI/计算引擎优化: 加菲_barista")
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
            padx=6,
            pady=1,
            font=(FONT_UI, 8, "bold"),
        )
        self.close_button.pack(side="right", padx=(5, 0))
        self.top_resize_grip = tk.Label(
            header_actions,
            text="◢",
            bg=BG,
            fg=DIM,
            padx=2,
            pady=1,
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
        self.top_resize_tip = HoverTip(self.top_resize_grip, "拖动边角缩放窗口")
        control_row = tk.Frame(header, bg=BG)
        control_row.pack(fill="x", pady=(4, 0))
        self.status = tk.Label(
            control_row,
            text="--:--",
            bg=PANEL_SOFT,
            fg=MUTED,
            padx=6,
            pady=3,
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
        self.manual_button = tk.Label(
            header_right,
            text="手填",
            bg=WARM,
            fg=BUTTON_DARK_FG,
            padx=7,
            pady=3,
            font=(FONT_UI, 8, "bold"),
            highlightthickness=1,
            highlightbackground=WARM,
        )
        self.manual_button.pack(side="right", padx=(0, 5))
        self.manual_button.bind("<Button-1>", self.open_manual_panel, add="+")
        self.manual_tip = HoverTip(self.manual_button, "展开手动填写 / 断网备用")
        self.theme_button = tk.Label(
            header_right,
            text="配色",
            bg=PANEL_SOFT,
            fg=ACCENT,
            padx=6,
            pady=3,
            font=(FONT_UI, 8, "bold"),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.theme_button.pack(side="right", padx=(0, 5))
        self.theme_button.bind("<Button-1>", self._show_theme_menu, add="+")
        self.theme_tip = HoverTip(self.theme_button, "选择配色：暗色")
        self.map_button = tk.Label(
            header_right,
            text="地图",
            bg=PANEL_SOFT,
            fg=ACCENT,
            padx=6,
            pady=3,
            font=(FONT_UI, 8, "bold"),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.map_button.pack(side="right", padx=(0, 5))
        self.map_button.bind("<Enter>", self._show_minimap_popup, add="+")
        self.map_button.bind("<Leave>", self._schedule_hide_minimap_popup, add="+")
        self.map_button.bind("<Button-1>", self.toggle_pinned_minimap, add="+")
        self.map_tip = HoverTip(self.map_button, "悬停显示小地图，点击常驻")
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
            card = self._card(prices, bg=PANEL, padx=6, pady=5)
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
                "风险",
            ),
        )
        self.action_rows = self._row_card(
            mid,
            "当前建议",
            (
                "动作",
                "最高",
                "最近",
                "来源",
                "状态",
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
                "总值",
                "红值",
                "结算",
                "备注",
            ),
        )
        self.evidence_rows["_card"].pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.detail_rows["_card"].pack(side="left", fill="x", expand=True)

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
            text="原作: 猫饭团子uu · UI/计算引擎优化: 加菲_barista",
            bg=BG,
            fg=DIM,
            font=(FONT_UI, 6),
            anchor="w",
        )
        self.footer.pack(side="left", fill="x", expand=True)
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
                self.mode_button,
                self.manual_button,
                self.theme_button,
                self.map_button,
                self.top_resize_grip,
                self.resize_grip,
            },
        )
        self._set_details_mode(False)
        root.protocol("WM_DELETE_WINDOW", self._on_user_close)
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
        work_w, work_h = self._screen_size()
        requested_w = self.shell.winfo_reqwidth() if hasattr(self, "shell") else 0
        requested_h = self.shell.winfo_reqheight() if hasattr(self, "shell") else 0
        width = min(760, max(700, requested_w + 28, int(work_w * 0.44)))
        height = max(700, requested_h + 8)
        width = min(width, max(430, work_w - 40))
        height = min(height, max(320, work_h - 72))
        return f"{width}x{height}"

    def _mini_geometry(self) -> str:
        return "440x397"

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

    def _begin_resize(self, event: tk.Event[Any]) -> str:
        self._resize_anchor = (
            event.x_root,
            event.y_root,
            self.root.winfo_width(),
            self.root.winfo_height(),
        )
        return "break"

    def _resize_window(self, event: tk.Event[Any]) -> str:
        if self._resize_anchor is None:
            return "break"
        x0, y0, width0, height0 = self._resize_anchor
        width = max(430, min(1200, width0 + event.x_root - x0))
        height = max(320, min(1500, height0 + event.y_root - y0))
        if self.details_expanded:
            self._custom_details_size = (width, height)
        self.root.geometry(f"{width}x{height}")
        return "break"

    def _end_resize(self, _event: tk.Event[Any]) -> str:
        self._resize_anchor = None
        return "break"

    def _configure_theme_style(self) -> None:
        self.style.configure(
            "Hero.TButton",
            background=PANEL_SOFT,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=PANEL_SOFT,
            darkcolor=PANEL_SOFT,
            padding=(6, 3),
        )
        self.style.map("Hero.TButton", background=[("active", HERO_BUTTON_ACTIVE)])

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
        self.theme_tip.set_text(f"选择配色：{label}")
        self._set_manual_button_state()
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

    def _on_user_close(self) -> None:
        self._hide_minimap_popup()
        self._hide_pinned_minimap()
        self._run_exit_cleanup()
        self.root.destroy()

    def _run_exit_cleanup(self) -> None:
        if self._exit_cleanup_done:
            return
        self._exit_cleanup_done = True
        _cleanup_exit_targets(self._stop_pids_on_exit, self._cleanup_lock_paths)

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
        if self._manual_active:
            self.manual_button.configure(bg="#ffe1a8", fg=BUTTON_DARK_FG, highlightbackground="#fff0c4")
        else:
            self.manual_button.configure(bg=WARM, fg=BUTTON_DARK_FG, highlightbackground=WARM)

    def open_manual_panel(self, _event: tk.Event[Any] | None = None) -> str:
        if not self.details_expanded:
            self.toggle_details()
        if hasattr(self, "manual_card"):
            self.manual_card.configure(highlightbackground=WARM, highlightthickness=2)
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
        card = self._card(parent, bg=manual_bg, padx=6, pady=6)
        self.manual_card = card
        card.pack(fill="x", pady=(5, 0))
        tk.Frame(card, bg=WARM, height=3).pack(fill="x", pady=(0, 4))
        header = tk.Frame(card, bg=manual_bg)
        header.pack(fill="x", pady=(0, 4))
        title_box = tk.Frame(header, bg=manual_bg)
        title_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_box,
            text="手动填写 / 断网备用",
            bg=manual_bg,
            fg=WARM,
            font=(FONT_UI, 9, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_box,
            text="填总件，并至少补一个品质均格/件数/格数",
            bg=manual_bg,
            fg=MUTED,
            font=(FONT_UI, 7),
            anchor="w",
        ).pack(fill="x", pady=(1, 0))
        self.manual_status = tk.Label(
            header,
            text="未启用",
            bg=MANUAL_STATUS_BG,
            fg=WARM,
            padx=6,
            pady=1,
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
                padx=8 if is_primary else 6,
                pady=2 if is_primary else 1,
                font=(FONT_UI, 8, "bold"),
                highlightthickness=1,
                highlightbackground=WARM if is_primary else BORDER,
            )
            button.pack(side="left", padx=(0, 6))
            self.manual_buttons[text] = button

        form = tk.Frame(card, bg=manual_bg)
        form.pack(fill="x")
        fields = (
            ("hero", "英雄", ""),
            ("map_id", "地图", ""),
            ("total_count", "总件", ""),
            ("total_cells", "总格", ""),
            ("total_avg", "全均格", ""),
            ("white_avg", "白均格", ""),
            ("green_avg", "绿均格", ""),
            ("q1_avg", "白绿均格", ""),
            ("q3_avg", "蓝均格", ""),
            ("q4_avg", "紫均格", ""),
            ("q5_avg", "金均格", ""),
            ("q6_avg", "红均格", ""),
            ("white_count", "白件", ""),
            ("green_count", "绿件", ""),
            ("q1_count", "白绿件", ""),
            ("q3_count", "蓝件", ""),
            ("q4_count", "紫件", ""),
            ("q5_count", "金件", ""),
            ("q6_count", "红件", ""),
            ("white_cells", "白格", ""),
            ("green_cells", "绿格", ""),
            ("q1_cells", "白绿格", ""),
            ("q3_cells", "蓝格", ""),
            ("q4_cells", "紫格", ""),
            ("q5_cells", "金格", ""),
            ("q6_cells", "红格", ""),
            ("q4q5_count", "紫金红件", ""),
        )
        for idx, (key, label, default) in enumerate(fields):
            row = idx // MANUAL_FORM_COLUMNS
            col = idx % MANUAL_FORM_COLUMNS
            cell = tk.Frame(form, bg=manual_bg)
            cell.grid(row=row, column=col, sticky="ew", padx=(0, 5), pady=(0, 3))
            form.columnconfigure(col, weight=1)
            tk.Label(
                cell,
                text=label,
                bg=manual_bg,
                fg=MANUAL_LABEL_FG if idx < 4 else DIM,
                font=(FONT_UI, 7),
                anchor="w",
            ).pack(side="left")
            var = tk.StringVar(value=default)
            entry = tk.Entry(
                cell,
                width=6,
                textvariable=var,
                bg=manual_input_bg,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                borderwidth=0,
                font=(FONT_UI, 8),
            )
            entry.pack(side="right", fill="x", expand=True, padx=(4, 0))
            entry.bind(
                "<KeyRelease>",
                lambda event, field=key: self._mark_manual_pending(event, field=field),
                add="+",
            )
            entry.bind("<Return>", self._apply_manual_from_event, add="+")
            var.trace_add(
                "write",
                lambda *_args, overlay=self, field=key: overlay._on_manual_var_write(field),
            )
            self.manual_vars[key] = var
            self.manual_entries[key] = entry

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
        self._manual_dirty_fields.add(field)
        self._sync_manual_derived_fields()
        self._mark_manual_pending()

    def _can_autofill_manual_field(self, key: str) -> bool:
        current = self._manual_entry_text(key)
        last_auto = self._manual_autofill_values.get(key)
        if not current:
            return True
        return last_auto is not None and current == last_auto

    def _set_manual_derived_entry(self, key: str, value: Any) -> None:
        if value in (None, "") or not self._can_autofill_manual_field(key):
            return
        self._set_manual_entry(key, _format_manual_number(value), track_auto=True)

    def _sync_manual_derived_fields(self) -> None:
        if not hasattr(self, "manual_entries") or self._manual_programmatic_update:
            return
        total_count = _to_optional_int(self._manual_entry_text("total_count"))
        total_cells = _to_optional_float(self._manual_entry_text("total_cells"))
        total_avg = _to_optional_float(self._manual_entry_text("total_avg"))
        if total_count is not None and total_count > 0:
            if total_cells is None and total_avg is not None:
                self._set_manual_derived_entry("total_cells", total_count * total_avg)
            elif total_avg is None and total_cells is not None:
                self._set_manual_derived_entry("total_avg", total_cells / total_count)

        for key in (*SPLIT_QUALITY_INPUT_KEYS, *QUALITY_INPUT_KEYS):
            count = _to_optional_int(self._manual_entry_text(f"{key}_count"))
            cells = _to_optional_int(self._manual_entry_text(f"{key}_cells"))
            avg_text = self._manual_entry_text(f"{key}_avg")
            avg = _to_optional_float(avg_text)
            if count is not None and cells is not None and avg is None:
                if count == 0:
                    if cells == 0:
                        self._set_manual_derived_entry(f"{key}_avg", 0)
                else:
                    self._set_manual_derived_entry(f"{key}_avg", cells / count)
            elif count is not None and avg is not None and cells is None:
                grid_options = _manual_avg_grid_options_from_text(count, avg, avg_text)
                if len(grid_options) == 1:
                    self._set_manual_derived_entry(f"{key}_cells", grid_options[0])
            elif count is None and avg is not None and cells is not None:
                derived_count = _manual_avg_count_from_cells_text(avg, cells, avg_text)
                if derived_count is not None:
                    self._set_manual_derived_entry(f"{key}_count", derived_count)
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
        card = self._card(parent, bg=PANEL, padx=6, pady=5)
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

    def _set_label(self, widget: tk.Label, value: Any, *, limit: int = 30) -> None:
        text = _text(value)
        widget.configure(text=_short(text, limit))

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
        try:
            if var is not None:
                var.set(text)
            else:
                entry.delete(0, "end")
                if text:
                    entry.insert(0, text)
        finally:
            self._manual_programmatic_update = False
        if track_auto:
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
            or self._has_manual_inputs()
            or bool(_text(getattr(self, "_manual_live_session_id", ""), "").strip())
            or bool(getattr(self, "_manual_snapshot", {}))
        )
        if not has_manual_state:
            return False
        stale = data.get("stale") if isinstance(data.get("stale"), dict) else {}
        reason = _text(stale.get("reason"), "")
        if reason in {"session_ahead", "settled_stale", "monitor_restarted"}:
            return True
        if self._summary_phase(data) == "settled":
            return True
        current_session_id = self._summary_session_id(data)
        previous_session_id = _text(getattr(self, "_manual_live_session_id", ""), "").strip()
        return bool(current_session_id and previous_session_id and current_session_id != previous_session_id)

    def _reset_manual_state(self, status_text: str = "已清空，回到实时", *, status_fg: str = DIM) -> None:
        self._manual_active = False
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
            values["total_cells"] = evidence.get("total_grid_target")
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
            if count_value is not None:
                values[f"{quality}_count"] = count_value
            if cell_value in (None, "") and count_value is not None and avg_value is not None:
                grid_options = _manual_avg_grid_options(count_value, avg_value)
                if len(grid_options) == 1:
                    cell_value = grid_options[0]
            if cell_value not in (None, ""):
                values[f"{quality}_cells"] = _format_manual_number(cell_value)
        count_sum_value = count_sums.get("q4q5q6")
        if count_sum_value in (None, ""):
            count_sum_value = count_sums.get("q4q5")
        if count_sum_value not in (None, ""):
            values["q4q5_count"] = count_sum_value
        return values

    def _auto_sync_manual_inputs(self, data: dict[str, Any]) -> None:
        if not hasattr(self, "manual_entries") or self._manual_active:
            return
        if data.get("status") == "stale_snapshot" or self._summary_phase(data) == "settled":
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
            self._set_manual_entry(key, value, track_auto=True)
        if self._has_manual_inputs() and not self._manual_active:
            self._manual_live_session_id = self._summary_session_id(data)
            self.manual_status.configure(text="实时已填入，可修改", fg=ACCENT)

    def _manual_inputs_snapshot(self) -> tuple[dict[str, Any] | None, str]:
        hero = _normalize_manual_hero(self._manual_entry_text("hero"))
        map_id = _to_optional_int(self._manual_entry_text("map_id"))
        total_count, error = _to_manual_count(self._manual_entry_text("total_count"), "总件")
        if error:
            return None, error
        total_cells = _to_optional_float(self._manual_entry_text("total_cells"))
        total_avg = _to_optional_float(self._manual_entry_text("total_avg"))
        if total_count is None:
            return None, "需要填写总件"
        if not hero:
            return None, "需要填写英雄"
        if total_cells is None and total_avg is not None:
            total_cells = total_avg * total_count
        avg_cells: dict[str, float] = {}
        quality_cells: dict[str, int] = {}
        fixed_counts: dict[str, int] = {}
        split_avg_cells: dict[str, float] = {}
        split_quality_cells: dict[str, int] = {}
        split_counts: dict[str, int] = {}
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
            if count is None and avg is not None and cells is not None:
                derived_count = _manual_avg_count_from_cells_text(avg, cells, avg_text)
                if derived_count is None:
                    return None, (
                        f"{label}均格与{label}格"
                        "无法对应到整数件数"
                    )
                count = derived_count
            if count is not None:
                if key in SPLIT_QUALITY_INPUT_KEYS:
                    split_counts[key] = count
                else:
                    fixed_counts[key] = count
                if avg is not None and cells is None:
                    grid_options = _manual_avg_grid_options_from_text(count, avg, avg_text)
                    if not grid_options:
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
        q4q5_count, error = _to_manual_count(self._manual_entry_text("q4q5_count"), "紫金红件")
        if error:
            return None, error
        if q4q5_count is not None:
            count_sums["q4q5q6"] = q4q5_count
        if (
            not avg_cells
            and not fixed_counts
            and not count_sums
            and not quality_cells
            and not split_avg_cells
            and not split_counts
            and not split_quality_cells
        ):
            return None, "需补品质均格/件数/格数"
        ref_inputs: dict[str, Any] = {
            "total_count": total_count,
            "avg_cells": avg_cells,
            "fixed_counts": fixed_counts,
        }
        if quality_cells:
            ref_inputs["quality_cells"] = quality_cells
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
            "phase": "manual",
            "structured_ref_inputs": ref_inputs,
            "ui_contract": {
                "context": {
                    "hero": hero,
                    "map_id": map_id,
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
                },
                "truth": {"available": False},
            },
        }
        return snapshot, ""

    def _manual_input_summary(self, evidence: dict[str, Any]) -> str:
        parts: list[str] = []
        if evidence.get("total_count") not in (None, ""):
            parts.append(f"总件 {evidence['total_count']}")
        if evidence.get("total_grid_target") not in (None, ""):
            parts.append(f"总格 {evidence['total_grid_target']}")
            total_count = _to_optional_float(evidence.get("total_count"))
            total_cells = _to_optional_float(evidence.get("total_grid_target"))
            if total_count is not None and total_count > 0 and total_cells is not None:
                parts.append(f"全均格 {_format_manual_number(total_cells / total_count)}")
        avg_cells = evidence.get("avg_cells")
        quality_cells = evidence.get("quality_cells")
        split_avg_cells = evidence.get("split_avg_cells")
        split_quality_cells = evidence.get("split_quality_cells")
        split_counts = evidence.get("split_counts")
        if isinstance(split_avg_cells, dict):
            for key in SPLIT_QUALITY_INPUT_KEYS:
                if split_avg_cells.get(key) not in (None, ""):
                    parts.append(
                        f"{SPLIT_QUALITY_LABELS[key]}均格 "
                        f"{_format_manual_number(split_avg_cells[key])}"
                    )
        if isinstance(avg_cells, dict):
            for key in QUALITY_INPUT_KEYS:
                if avg_cells.get(key) not in (None, ""):
                    parts.append(f"{QUALITY_LABELS[key]}均格 {_format_manual_number(avg_cells[key])}")
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
        return " · ".join(parts) if parts else "-"

    def _range_text(self, values: Any, *, money: bool = False) -> str:
        if not isinstance(values, (list, tuple)) or not values:
            return "-"
        if money:
            return " / ".join(_money(value, "?") for value in values)
        return " / ".join("?" if value is None else str(value) for value in values)

    def _manual_result_summary(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        if run_reference_engine is None:
            raise RuntimeError("ref engine unavailable")
        result = run_reference_engine(snapshot, max_combos=60000).as_dict()
        evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
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
                "total_value_range": self._range_text(
                    (result.get("value_p25"), result.get("value_p50"), result.get("value_p75")),
                    money=True,
                ),
            },
            "red": {
                "count_range": self._range_text(result.get("red_count_range")),
                "cells_range": self._range_text(result.get("red_cells_range")),
                "value_range": self._range_text(result.get("red_value_range"), money=True),
                "quality_count_summary": self._quality_count_summary(result),
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
                "ref_input_summary": self._manual_input_summary(evidence),
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
            if self._last_live_snapshot and self._last_live_summary.get("status") != "stale_snapshot":
                summary = self._manual_overlay_summary(self._last_live_snapshot, snapshot)
            else:
                summary = self._manual_result_summary(snapshot)
        except Exception as exc:  # noqa: BLE001 - show calculation failure in UI
            self.manual_status.configure(text=f"计算失败: {exc}", fg=BAD)
            return
        self._manual_active = True
        self._manual_snapshot = snapshot
        self._manual_summary = summary
        self._last_summary = summary
        self._manual_live_session_id = self._summary_session_id(self._last_live_summary) or "manual"
        self.manual_status.configure(text="手动叠加，实时继续", fg=WARM)
        self._set_manual_button_state()
        if summary.get("status") == "stale_snapshot":
            self.render_standby(summary)
        else:
            self.render(summary)

    def _quality_count_summary(self, result: dict[str, Any]) -> str:
        ranges = result.get("quality_count_ranges")
        if not isinstance(ranges, dict):
            return "-"
        q4 = self._range_text(ranges.get("q4"))
        q5 = self._range_text(ranges.get("q5"))
        parts: list[str] = []
        if q4 != "-":
            parts.append(f"紫件 {q4}")
        if q5 != "-":
            parts.append(f"金件 {q5}")
        return " · ".join(parts) if parts else "-"

    def clear_manual_inputs(self) -> None:
        self._reset_manual_state("已清空，回到实时", status_fg=DIM)
        if self._last_live_summary:
            self._last_summary = self._last_live_summary
            if self._last_live_summary.get("status") == "stale_snapshot":
                self.render_standby(self._last_live_summary)
            else:
                self.render(self._last_live_summary)
        else:
            self._last_summary = {}
            self.render_missing("等待 latest_snapshot.json")

    def prefill_manual_inputs(self) -> None:
        data = self._last_live_summary or self._last_summary or {}
        values = self._manual_values_from_summary(data)
        self._set_manual_entry("hero", values.get("hero") or "", track_auto=True)
        self._set_manual_entry("map_id", values.get("map_id") if values.get("map_id") is not None else "", track_auto=True)
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
                cell_hint=13.0,
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
        return dict(MAINLINE_QUALITY_STYLE.get(quality, MAINLINE_QUALITY_STYLE["unknown"]))

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
    ) -> None:
        width = max(1, x1 - x0)
        height = max(1, y1 - y0)
        step = max(4, min(width, height) // 3)
        for start_x in range(x0 - height, x1, step):
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
                    width=1,
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
        canvas.delete("all")
        visible_width = max(min_width, canvas.winfo_width() or min_width)
        visible_height = max(min_height, canvas.winfo_height() or min_height)
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
            style = self._minimap_quality_style(quality)
            fill = str(style["fill"])
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
            has_hard_footprint = (
                render_mode == "footprint"
                or bool(shape_key)
                or has_item_identity
                or source_text in {"packet", "settlement_inventory", "settlement"}
            )
            marker_only = not has_hard_footprint and (
                render_mode == "marker"
                or source_text in {
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
            if marker_only:
                marker_size = max(5, min(9, int(round(cell * 0.50))))
                dot_x = (x1 + x2) / 2
                dot_y = (y1 + y2) / 2
                marker_x1 = int(round(dot_x - marker_size / 2))
                marker_y1 = int(round(dot_y - marker_size / 2))
                marker_x2 = marker_x1 + marker_size
                marker_y2 = marker_y1 + marker_size
                canvas.create_oval(
                    marker_x1,
                    marker_y1,
                    marker_x2,
                    marker_y2,
                    fill=fill,
                    outline=outline,
                    width=1,
                    tags=(tag,),
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
                if style.get("unknown"):
                    self._draw_unknown_quality_fill(
                        canvas,
                        x1,
                        y1,
                        x2,
                        y2,
                        color=outline,
                        tag=tag,
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
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
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
        if self._pinned_minimap_popup is None or self._pinned_offset is None:
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

    def toggle_pinned_minimap(self, event: tk.Event[Any] | None = None) -> str:
        self._hide_minimap_popup()
        if self._pinned_minimap_popup is not None:
            self._hide_pinned_minimap()
            return "break"

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
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
        self._pinned_minimap_popup = popup
        self.map_button.configure(bg=PANEL_MUTED, fg=WARM)
        self._redraw_pinned_minimap()
        return "break"

    def _redraw_pinned_minimap(self) -> None:
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
        self._draw_minimap(
            self._pinned_canvas,
            self._minimap_data,
            self._pinned_canvas_tip,
            min_width=260,
            min_height=320,
            allow_scroll=True,
            cell_hint=24.0,
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

    def _needs_stale_refresh(self) -> bool:
        summary = self._last_live_summary if self._manual_active else self._last_summary
        if not summary or summary.get("status") == "stale_snapshot":
            return False
        context = summary.get("context") if isinstance(summary.get("context"), dict) else {}
        phase = _text(context.get("phase"), "")
        threshold = SETTLED_STALE_SECONDS if phase == "settled" else STALE_SNAPSHOT_SECONDS
        age = self._snapshot_file_age_seconds()
        return age is not None and age >= threshold

    def refresh(self) -> None:
        try:
            if self.exit_when_pids and _watched_pid_exited(self.exit_when_pids):
                self.root.destroy()
                return
            signature = self._snapshot_signature()
            if signature != self._last_signature or self._needs_stale_refresh():
                self._last_signature = signature
                snapshot = _read_json(self.snapshot_path)
                if snapshot:
                    summary = summarize_snapshot(snapshot, snapshot_path=self.snapshot_path)
                    self._last_live_snapshot = snapshot
                    self._last_live_summary = summary
                    if self._should_reset_manual_for_summary(summary):
                        self._reset_manual_state("已自动清空，等待新局", status_fg=DIM)
                    if self._manual_active:
                        self.manual_status.configure(text="手动叠加，实时继续", fg=WARM)
                        if summary.get("status") == "stale_snapshot":
                            self._last_summary = summary
                            self.render_standby(summary)
                        elif self._manual_snapshot:
                            try:
                                overlay_summary = self._manual_overlay_summary(snapshot, self._manual_snapshot)
                            except Exception as exc:  # noqa: BLE001 - keep live usable
                                self.manual_status.configure(text=f"叠加失败: {exc}", fg=BAD)
                                overlay_summary = summary
                            self._manual_summary = overlay_summary
                            self._last_summary = overlay_summary
                            if overlay_summary.get("status") == "stale_snapshot":
                                self.render_standby(overlay_summary)
                            else:
                                self.render(overlay_summary)
                        else:
                            self._last_summary = summary
                            self.render(summary)
                    else:
                        self._auto_sync_manual_inputs(summary)
                        self._last_summary = summary
                        if summary.get("status") == "stale_snapshot":
                            self.render_standby(summary)
                        else:
                            self.render(summary)
                else:
                    if not self._manual_active:
                        self.render_missing("等待 latest_snapshot.json")
        finally:
            self.root.after(self.interval_ms, self.refresh)

    def render_missing(self, message: str) -> None:
        self.title.configure(text="Hero Ref")
        self.subtitle.configure(text=message)
        self.status.configure(text=time.strftime("%H:%M:%S"))
        self._render_flags([{"label": "无实时数据", "level": "watch", "detail": ""}])
        self._clear_values()
        self._render_minimap({})

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
        self._clear_values()
        self._set_label(self.action_rows["动作"], "等待新局", limit=18)
        self._set_label(self.action_rows["最近"], "-", limit=18)
        self._set_label(self.action_rows["来源"], "standby", limit=18)
        self._update_detail_rows(data)
        self._render_minimap(data.get("minimap") or {})

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
        price_titles = reference.get("price_titles") if isinstance(reference.get("price_titles"), dict) else {}
        self._set_price_titles(price_titles)

        for key in ("conservative", "balanced", "aggressive"):
            text = _text(reference.get(key))
            self.price_labels[key].configure(text=text)

        self._set_label(self.red_rows["红件"], red.get("count_range"), limit=18)
        self._set_label(self.red_rows["红格"], red.get("cells_range"), limit=18)
        self._set_label(self.red_rows["紫金件"], red.get("quality_count_summary"), limit=30)
        self._set_label(self.red_rows["红值"], red.get("value_range"), limit=24)
        self._set_label(self.red_rows["风险"], red.get("risk_reference") or reference.get("risk_band"), limit=28)
        self._set_label(self.action_rows["动作"], reference.get("action"), limit=18)
        self._set_label(self.action_rows["最高"], reference.get("current_highest"), limit=20)
        self._set_label(self.action_rows["最近"], self._latest_result_text(evidence), limit=20)
        self._set_label(self.action_rows["来源"], source, limit=18)
        self._set_label(
            self.action_rows["状态"],
            evidence.get("ref_status") or reference.get("readiness"),
            limit=18,
        )
        self._update_detail_rows(data)
        self._render_minimap(data.get("minimap") or {})

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
        return f"{tool}={result}" if tool else _text(result)

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
        total = _text(truth.get("total_value"), "?")
        total_items = _text(truth.get("total_items"), "?")
        total_cells = _text(truth.get("total_cells"), "?")
        q6 = truth.get("q6") if isinstance(truth.get("q6"), dict) else {}
        q6_count = _text(q6.get("count"), "?")
        q6_cells = _text(q6.get("cells"), "?")
        return f"{total} · {total_items}件/{total_cells}格 · 红{q6_count}件/{q6_cells}格"

    def _update_detail_rows(self, data: dict[str, Any]) -> None:
        reference = data.get("reference") if isinstance(data.get("reference"), dict) else {}
        red = data.get("red") if isinstance(data.get("red"), dict) else {}
        evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
        ahmed_ref = data.get("ahmed_ref") if isinstance(data.get("ahmed_ref"), dict) else {}

        self._set_label(self.evidence_rows["匹配"], evidence.get("match_text"), limit=26)
        self._set_label(self.evidence_rows["密度"], evidence.get("information_density"), limit=22)
        self._set_label(self.evidence_rows["输入"], self._input_evidence_text(evidence), limit=46)
        self._set_label(self.evidence_rows["组合"], evidence.get("ref_combo_count"), limit=22)
        self._set_label(self.evidence_rows["最近"], self._latest_result_text(evidence), limit=28)
        self._set_label(
            self.evidence_rows["诊断"],
            evidence.get("diagnostics") or evidence.get("ref_notes"),
            limit=34,
        )

        self._set_label(self.detail_rows["外援"], ahmed_ref.get("status") or reference.get("source"), limit=24)
        self._set_label(self.detail_rows["决策"], reference.get("decision_range"), limit=34)
        self._set_label(
            self.detail_rows["总值"],
            reference.get("total_value_range") or red.get("value_range"),
            limit=34,
        )
        self._set_label(self.detail_rows["红值"], red.get("value_range"), limit=34)
        self._set_label(self.detail_rows["结算"], self._truth_text(data), limit=38)
        self._set_label(self.detail_rows["备注"], reference.get("note") or evidence.get("ref_notes"), limit=38)

    def _set_details_mode(self, expanded: bool) -> None:
        self.details_expanded = expanded
        if expanded:
            self.mode_button.configure(text="迷你")
            self.root.minsize(430, 360)
            if not self.details_card.winfo_ismapped():
                self.details_card.pack(fill="x", pady=(5, 0), before=self.footer_row)
            if not self.minimap_card.winfo_ismapped():
                self.minimap_card.pack(fill="x", pady=(5, 0), before=self.footer_row)
            self.root.update_idletasks()
            self.root.geometry(self._details_geometry())
        else:
            self.mode_button.configure(text="详情")
            self.root.minsize(430, 395)
            self.details_card.pack_forget()
            self.minimap_card.pack_forget()
            self.root.geometry(self._mini_geometry())

    def toggle_details(self) -> None:
        self._set_details_mode(not self.details_expanded)
        self._update_detail_rows(self._last_summary or {})
        self._render_minimap(self._minimap_data)

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
    args = parser.parse_args(argv)

    root = tk.Tk()
    overlay = AhmadTkOverlay(
        root,
        snapshot_path=Path(args.snapshot),
        interval_ms=args.interval_ms,
        exit_when_pids=tuple(args.exit_when_pid_exits),
        stop_pids_on_exit=tuple(args.stop_pid_on_exit),
        cleanup_lock_paths=tuple(args.cleanup_lock_on_exit),
        load_existing_snapshot=bool(args.load_existing),
    )
    try:
        root.mainloop()
    finally:
        overlay._run_exit_cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
