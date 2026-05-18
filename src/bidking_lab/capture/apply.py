"""Apply capture parse results to Streamlit session state (UI layer only)."""

from __future__ import annotations

from typing import Any, Mapping

from bidking_lab.capture.types import CaptureParseResult

# map_id prefix → MAP_CATEGORIES key in streamlit_app
_MAP_PREFIX_TO_CATEGORY: dict[str, str] = {
    "24": "mansion",
    "34": "mansion",
    "44": "mansion",
    "25": "shipwreck",
    "35": "shipwreck",
    "45": "shipwreck",
}

READING_KEYS: tuple[str, ...] = (
    "wg_cells", "white_cells", "white_count", "green_cells", "green_count",
    "blue_cells", "blue_count",
    "purple_cells", "purple_count", "purple_value", "purple_avg_value",
    "purple_huge_band",
    "gold_cells", "gold_count", "gold_value", "gold_avg_value",
    "gold_huge_band",
    "red_cells_total", "red_value_lo", "red_value_hi", "red_huge_band",
)

# Streamlit number_input keys — must match streamlit_app.py (apply runs before widgets).
READING_WIDGET_KEYS: dict[str, str] = {
    "wg_cells": "obs_reading_wg_cells",
    "white_cells": "obs_reading_white_cells",
    "white_count": "obs_reading_white_count",
    "green_cells": "obs_reading_green_cells",
    "green_count": "obs_reading_green_count",
    "blue_cells": "obs_reading_blue_cells",
    "blue_count": "obs_reading_blue_count",
    "purple_cells": "obs_reading_purple_cells",
    "purple_count": "obs_reading_purple_count",
    "purple_value": "obs_reading_purple_value",
    "purple_avg_value": "obs_reading_purple_avg_value",
    "gold_cells": "obs_reading_gold_cells",
    "gold_count": "obs_reading_gold_count",
    "gold_value": "obs_reading_gold_value",
    "gold_avg_value": "obs_reading_gold_avg_value",
    "red_cells_total": "obs_reading_red_cells_total",
    "red_value_lo": "obs_reading_red_value_lo",
    "red_value_hi": "obs_reading_red_value_hi",
}

AVG_RAW_WIDGET_KEYS: dict[str, str] = {
    "purple_avg_raw": "purple_avg_raw_widget",
    "gold_avg_raw": "gold_avg_raw_widget",
}

AVG_RAW_OBS_KEYS: tuple[str, ...] = tuple(AVG_RAW_WIDGET_KEYS.keys())


def reading_widget_key(base: str, ui_state: Any) -> str:
    """Versioned Streamlit key so map-change reset recreates inputs."""
    rev = int(ui_state.get("obs_readings_rev", 0))
    return f"{base}__r{rev}"


def hydrate_reading_widgets_from_obs(
    obs: dict[str, Any],
    ui_state: Any,
) -> None:
    """Pre-fill versioned widget keys from ``obs`` before ``number_input`` renders."""
    for obs_key, base_wkey in READING_WIDGET_KEYS.items():
        val = obs.get(obs_key)
        if val is None:
            continue
        wkey = reading_widget_key(base_wkey, ui_state)
        if wkey not in ui_state or ui_state[wkey] is None:
            ui_state[wkey] = _coerce_widget_value(obs_key, val)
    for obs_key, base_wkey in AVG_RAW_WIDGET_KEYS.items():
        val = obs.get(obs_key)
        if not val:
            continue
        wkey = reading_widget_key(base_wkey, ui_state)
        # Empty string = user cleared; do not re-hydrate from obs.
        if wkey not in ui_state:
            ui_state[wkey] = str(val)


def sync_obs_from_reading_widgets(
    obs: dict[str, Any],
    ui_state: Any,
) -> None:
    """Merge widget keys into ``obs``; do not use ``number_input`` return values."""
    for obs_key, base_wkey in READING_WIDGET_KEYS.items():
        wkey = reading_widget_key(base_wkey, ui_state)
        if wkey in ui_state and ui_state[wkey] is not None:
            obs[obs_key] = ui_state[wkey]
        else:
            obs.pop(obs_key, None)
    for obs_key, base_wkey in AVG_RAW_WIDGET_KEYS.items():
        wkey = reading_widget_key(base_wkey, ui_state)
        raw = ui_state.get(wkey)
        if raw:
            obs[obs_key] = str(raw)
        else:
            obs.pop(obs_key, None)


def _coerce_widget_value(key: str, val: Any) -> Any:
    if key.endswith("_avg_raw"):
        return str(val)
    if isinstance(val, float):
        return int(val) if val == int(val) else val
    return val


def category_for_map_id(map_id: int) -> str | None:
    prefix = str(map_id)[:2]
    return _MAP_PREFIX_TO_CATEGORY.get(prefix)


def apply_capture_result(
    result: CaptureParseResult,
    obs: dict[str, Any],
    ui_state: Any,
    *,
    map_names: Mapping[int, str] | None = None,
) -> list[str]:
    """Write suggestions into ``obs`` and Streamlit widget keys.

    Returns human-readable log lines for the UI.
    """
    log: list[str] = []
    map_names = map_names or {}

    # 英雄由玩家手动选择（OCR 常混入其他玩家「艾莎/伊森」名字）

    if result.map_id is not None:
        prev = obs.get("map_id")
        new_mid = int(result.map_id)
        cat = category_for_map_id(new_mid)
        prev_cat = category_for_map_id(int(prev)) if prev is not None else None
        if cat:
            ui_state["obs_map_category"] = cat
        # 类别切换时先清 selectbox，避免仍显示上一类地图（如别墅→沉船）
        if cat and prev_cat and cat != prev_cat:
            ui_state["obs_map_select_rev"] = (
                int(ui_state.get("obs_map_select_rev", 0)) + 1
            )
        rev = int(ui_state.get("obs_map_select_rev", 0))
        ui_state[f"obs_map_select__r{rev}"] = new_mid
        obs["map_id"] = new_mid
        name = result.map_name or map_names.get(new_mid, "")
        log.append(f"地图 → {new_mid} {name}".strip())
        if prev is not None and int(prev) != new_mid:
            log.append("（OCR 已切换地图；读数已在导入前清空）")
    elif result.suggestions:
        log.append("（未识别地图名，请手动选地图）")

    for sug in result.suggestions:
        key = sug.key
        val = sug.value
        if key.endswith("_avg_raw"):
            base_wkey = AVG_RAW_WIDGET_KEYS.get(
                key, f"{key.replace('_avg_raw', '')}_avg_raw_widget",
            )
            ui_state[reading_widget_key(base_wkey, ui_state)] = str(val)
            obs[key] = str(val)
        else:
            obs[key] = val
            base_wkey = READING_WIDGET_KEYS.get(key)
            if base_wkey is not None:
                ui_state[reading_widget_key(base_wkey, ui_state)] = _coerce_widget_value(
                    key, val,
                )
            if key == "warehouse_cells":
                ui_state["obs_warehouse_cells"] = int(val)
            elif key == "total_item_count":
                ui_state["obs_total_item_count"] = int(val)
        log.append(f"{sug.label} → {val}")

    return log


def mark_ocr_map_applied_to_ui(
    ui_state: Any,
    map_id: int,
    *,
    category: str | None = None,
) -> None:
    """After OCR sets map selectbox, avoid manual map-change reset on same rerun."""
    ui_state["_tracked_map_id"] = int(map_id)
    ui_state["_suppress_map_change_reset"] = True
    if category is not None:
        ui_state["_tracked_map_category"] = category


def ocr_should_clear_readings(
    result: CaptureParseResult,
    map_id_before: int | None,
) -> bool:
    """Clear scan readings only when OCR resolves a *different* map than before."""
    if result.map_id is None:
        return False
    if map_id_before is None:
        return False
    return int(result.map_id) != int(map_id_before)


def clear_readings_for_map_change(obs: dict[str, Any], ui_state: Any) -> None:
    """Clear obs readings and bump widget revision (orphans old Streamlit keys)."""
    for k in READING_KEYS:
        obs.pop(k, None)
    for k in AVG_RAW_OBS_KEYS:
        obs.pop(k, None)
    ui_state["obs_readings_rev"] = int(ui_state.get("obs_readings_rev", 0)) + 1


_MAP_RESET_EXTRA_OBS: tuple[str, ...] = (
    "purple_huge_band",
    "gold_huge_band",
    "red_huge_band",
    "red_confirmed_none",
    "small_warehouse_confirmed",
    "aisha_split",
)

_MAP_RESET_WIDGET_DEFAULTS: dict[str, Any] = {
    "obs_purple_huge_band": "none",
    "obs_gold_huge_band": "none",
    "obs_red_huge_band": "none",
    "obs_red_confirmed_none": False,
    "obs_small_warehouse_confirmed": False,
}


def reset_obs_for_manual_map_change(
    obs: dict[str, Any],
    ui_state: Any,
    *,
    new_map_id: int | None,
) -> None:
    """Clear scan readings, warehouse/total, flags; keep hero + new map."""
    clear_readings_for_map_change(obs, ui_state)
    obs.pop("warehouse_cells", None)
    ui_state["obs_warehouse_cells"] = None
    obs.pop("total_item_count", None)
    ui_state["obs_total_item_count"] = None
    for k in _MAP_RESET_EXTRA_OBS:
        obs.pop(k, None)
    for wkey, default in _MAP_RESET_WIDGET_DEFAULTS.items():
        ui_state[wkey] = default
    if new_map_id is not None:
        obs["map_id"] = int(new_map_id)
    else:
        obs.pop("map_id", None)
