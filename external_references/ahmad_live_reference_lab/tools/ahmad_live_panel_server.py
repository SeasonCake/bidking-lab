from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import time
from typing import Any
from urllib.parse import urlparse


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SNAPSHOT = Path("data/logs/live/latest_snapshot.json")
STALE_SNAPSHOT_SECONDS = 60.0
SETTLED_STALE_SECONDS = 60.0
LAB_ROOT = Path(__file__).resolve().parents[1]
LAB_SRC = LAB_ROOT / "src"
if str(LAB_SRC) not in sys.path:
    sys.path.insert(0, str(LAB_SRC))
QUALITY_LABELS = {
    "q1": "白绿",
    "q3": "蓝",
    "q4": "紫",
    "q5": "金",
    "q6": "红",
}
QUALITY_DISPLAY_ORDER = ("q1", "q3", "q4", "q5", "q6")
SPLIT_QUALITY_LABELS = {
    "white": "白",
    "green": "绿",
}
SPLIT_QUALITY_DISPLAY_ORDER = ("white", "green")

try:
    from ahmad_ref_engine import run_reference_engine
except Exception:  # noqa: BLE001 - keep debug server usable without ref core
    run_reference_engine = None  # type: ignore[assignment]


def _dig(value: Any, *path: str, default: Any = None) -> Any:
    current = value
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "是"}
    return bool(value)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _flag(label: str, level: str = "watch", detail: str = "") -> dict[str, str]:
    return {"label": label, "level": level, "detail": detail}


def _money(value: Any, fallback: str = "-") -> str:
    if value in (None, ""):
        return fallback
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


def _parse_money(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(round(float(str(value).replace(",", "").strip())))
    except (TypeError, ValueError):
        return None


def _signed_money(value: Any, fallback: str = "-") -> str:
    parsed = _parse_money(value)
    if parsed is None:
        return fallback
    sign = "+" if parsed > 0 else ""
    return f"{sign}{parsed:,}"


def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


HERO_BY_ID = {
    103: "aisha",
    204: "ahmed",
    209: "victor",
}


def _hero_from_context(hero: Any, *hero_id_candidates: Any) -> str:
    text = _text(hero, "").strip()
    if text and text.lower() not in {"?", "unknown", "none", "null"}:
        return text
    for candidate in hero_id_candidates:
        hero_id = _parse_int(candidate)
        if hero_id in HERO_BY_ID:
            return HERO_BY_ID[hero_id]
    return text or "?"


def _is_unknown_hero(value: Any) -> bool:
    return _text(value, "").strip().lower() in {"", "?", "unknown", "none", "null"}


def _clean_range_text(value: Any) -> str:
    text = _text(value, "").strip()
    return text if text and text != "-" else ""


def _format_range(values: tuple[Any, Any, Any]) -> str:
    return " / ".join(_money(value, "?") for value in values)


def _parse_range_numbers(value: Any) -> list[int | None]:
    text = _text(value, "").strip()
    if not text or text == "-":
        return []
    parts = [part.strip() for part in text.split("/") if part.strip()]
    out: list[int | None] = []
    for part in parts[:3]:
        out.append(_parse_money(part))
    while len(out) < 3:
        out.append(None)
    return out


def _range_mid(value: Any) -> int | None:
    numbers = _parse_range_numbers(value)
    if len(numbers) >= 2:
        return numbers[1]
    if numbers:
        return numbers[0]
    return None


def _floor_range_text(value: str, floor: int | None) -> str:
    if floor is None or floor <= 0:
        return value
    numbers = _parse_range_numbers(value)
    if len(numbers) < 3:
        return value
    floored = [
        max(number, floor) if number is not None else None
        for number in numbers[:3]
    ]
    return " / ".join(_money(number, "?") for number in floored)


def _join_notes(*parts: str) -> str:
    cleaned: list[str] = []
    for part in parts:
        text = _text(part, "").strip()
        if text and text != "-" and text not in cleaned:
            cleaned.append(text)
    return "；".join(cleaned)


def _shadow_range_text(
    shadow: dict[str, Any],
    keys: tuple[str, str, str],
    *,
    money: bool = False,
) -> str:
    values = tuple(shadow.get(key) for key in keys)
    if all(value in (None, "") for value in values):
        return ""
    if money:
        return _format_range(values)
    out: list[str] = []
    for value in values:
        if value in (None, ""):
            out.append("?")
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            out.append(str(value))
            continue
        out.append(str(int(round(number))))
    return " / ".join(out)


def _posterior_or_shadow_range(
    posterior: dict[str, Any],
    shadow: dict[str, Any],
    posterior_key: str,
    shadow_keys: tuple[str, str, str],
    *,
    money: bool = False,
) -> str:
    return (
        _clean_range_text(posterior.get(posterior_key))
        or _shadow_range_text(shadow, shadow_keys, money=money)
        or "-"
    )


def _red_risk_reference(
    decision: dict[str, Any],
    q6_ref: dict[str, Any],
    posterior: dict[str, Any],
) -> str:
    parts: list[str] = []
    decision_text = _text(decision.get("q6_risk_reference"), "").strip()
    if decision_text:
        parts.append(decision_text)
    else:
        prior_gap = _text(q6_ref.get("prior_gap"), "").strip()
        if prior_gap:
            parts.append(prior_gap)
        reference_p90 = _text(
            q6_ref.get("practical_reference_p90") or q6_ref.get("prior_reference_p90"),
            "",
        ).strip()
        if reference_p90:
            parts.append(f"参考P90 {reference_p90}")
    prior_rate = _text(posterior.get("q6_prior_rate"), "").strip()
    sample_rate = _text(posterior.get("q6_sample_rate"), "").strip()
    if prior_rate or sample_rate:
        parts.append(f"先验/样本 {prior_rate or '-'} / {sample_rate or '-'}")
    return "；".join(parts)


def _quality_key(value: Any) -> str:
    if value in (None, ""):
        return "unknown"
    text = str(value).strip().lower()
    if text.startswith("q") and text[1:].isdigit():
        return text
    parsed = _parse_int(value)
    if parsed is not None:
        return f"q{parsed}"
    return text or "unknown"


def _ref_input_summary(ref_result: dict[str, Any]) -> str:
    evidence = ref_result.get("evidence")
    if not isinstance(evidence, dict):
        return "-"
    parts: list[str] = []
    total_count = evidence.get("total_count")
    if total_count not in (None, ""):
        parts.append(f"总件 {total_count}")
    total_grid = evidence.get("total_grid_target")
    if total_grid not in (None, ""):
        parts.append(f"总格 {total_grid}")
        parsed_count = _parse_int(total_count)
        try:
            parsed_grid = float(total_grid)
        except (TypeError, ValueError):
            parsed_grid = None
        if parsed_count and parsed_grid is not None:
            parts.append(f"全均格 {parsed_grid / parsed_count:.2f}")
    avg_cells = evidence.get("avg_cells")
    split_avg_cells = evidence.get("split_avg_cells")
    if isinstance(split_avg_cells, dict):
        for key in SPLIT_QUALITY_DISPLAY_ORDER:
            value = split_avg_cells.get(key)
            if value in (None, ""):
                continue
            try:
                parts.append(f"{SPLIT_QUALITY_LABELS.get(key, key)}均格 {float(value):.2f}")
            except (TypeError, ValueError):
                parts.append(f"{SPLIT_QUALITY_LABELS.get(key, key)}均格 {value}")
    if isinstance(avg_cells, dict):
        for key in QUALITY_DISPLAY_ORDER:
            value = avg_cells.get(key)
            if value in (None, ""):
                continue
            try:
                parts.append(f"{QUALITY_LABELS.get(key, key)}均格 {float(value):.2f}")
            except (TypeError, ValueError):
                parts.append(f"{QUALITY_LABELS.get(key, key)}均格 {value}")
    quality_cells = evidence.get("quality_cells")
    split_quality_cells = evidence.get("split_quality_cells")
    if isinstance(split_quality_cells, dict):
        split_cell_parts = [
            f"{SPLIT_QUALITY_LABELS.get(key, key)}格 {split_quality_cells[key]}"
            for key in SPLIT_QUALITY_DISPLAY_ORDER
            if split_quality_cells.get(key) not in (None, "")
        ]
        if split_cell_parts:
            parts.append("分格 " + "，".join(split_cell_parts))
    if isinstance(quality_cells, dict):
        cell_parts = [
            f"{QUALITY_LABELS.get(key, key)}格 {quality_cells[key]}"
            for key in QUALITY_DISPLAY_ORDER
            if quality_cells.get(key) not in (None, "")
        ]
        if cell_parts:
            parts.append("格数 " + "，".join(cell_parts))
    fixed_counts = evidence.get("fixed_counts")
    split_counts = evidence.get("split_counts")
    if isinstance(split_counts, dict):
        split_count_parts = [
            f"{SPLIT_QUALITY_LABELS.get(key, key)}件 {split_counts[key]}"
            for key in SPLIT_QUALITY_DISPLAY_ORDER
            if split_counts.get(key) not in (None, "")
        ]
        if split_count_parts:
            parts.append("分件 " + "，".join(split_count_parts))
    if isinstance(fixed_counts, dict):
        count_parts = [
            f"{QUALITY_LABELS.get(key, key)}件 {fixed_counts[key]}"
            for key in QUALITY_DISPLAY_ORDER
            if fixed_counts.get(key) not in (None, "")
        ]
        if count_parts:
            parts.append("件数 " + "，".join(count_parts))
    min_counts = evidence.get("min_counts")
    if isinstance(min_counts, dict):
        floor_parts = []
        for key in QUALITY_DISPLAY_ORDER:
            value = _parse_int(min_counts.get(key))
            fixed_value = _parse_int(fixed_counts.get(key)) if isinstance(fixed_counts, dict) else None
            if value is None or value <= 0 or fixed_value is not None and fixed_value >= value:
                continue
            floor_parts.append(f"{QUALITY_LABELS.get(key, key)}≥{value}")
        if floor_parts:
            parts.append("下界 " + "，".join(floor_parts))
    count_sums = evidence.get("count_sums")
    if isinstance(count_sums, dict):
        if count_sums.get("q4q5q6") not in (None, ""):
            parts.append(f"紫金红件 {count_sums['q4q5q6']}")
        elif count_sums.get("q4q5") not in (None, ""):
            parts.append(f"紫金件 {count_sums['q4q5']}")
    return " · ".join(parts) if parts else "-"


def _minimap_summary(snapshot: dict[str, Any], uc: dict[str, Any]) -> dict[str, Any]:
    minimap = uc.get("minimap") if isinstance(uc.get("minimap"), dict) else {}
    context = uc.get("context") if isinstance(uc.get("context"), dict) else {}
    phase = _text(context.get("phase") or snapshot.get("phase"), "")
    root_items = snapshot.get("minimap_grid_items")
    if not isinstance(root_items, list):
        root_items = []

    status = _text(minimap.get("status"), "")
    raw_items = minimap.get("items") if isinstance(minimap.get("items"), list) else []
    layout_source = _text(minimap.get("layout_source"), "")
    if phase == "settled" and root_items:
        raw_items = root_items
        status = "available"
        layout_source = layout_source or "settlement_inventory"
    if status != "available" and root_items:
        status = "available"
        raw_items = root_items
        layout_source = layout_source or "minimap_grid_items"

    columns = _parse_int(minimap.get("columns")) or 10
    rows_hint = (
        _parse_int(minimap.get("viewport_rows"))
        or _parse_int(minimap.get("rows_hint"))
        or _parse_int(minimap.get("max_rows"))
        or 13
    )
    known_items = _parse_int(minimap.get("known_items"))
    drawable_items = _parse_int(minimap.get("drawable_items"))
    final_total_items = _parse_int(minimap.get("final_total_items"))
    quality_counts = minimap.get("quality_counts") if isinstance(minimap.get("quality_counts"), dict) else {}
    quality_reveal_counts = (
        minimap.get("quality_reveal_counts")
        if isinstance(minimap.get("quality_reveal_counts"), dict)
        else {}
    )

    items: list[dict[str, Any]] = []
    max_row = 0
    max_col = 0
    observed_quality_counts: dict[str, int] = {}
    public_shapes = _public_shape_by_local(snapshot)
    if status == "available":
        for raw in raw_items[:120]:
            if not isinstance(raw, dict):
                continue
            row = _parse_int(raw.get("row"))
            col = _parse_int(raw.get("col"))
            if row is None or col is None:
                continue
            local_index = _parse_int(raw.get("local_index"))
            shape_code = _parse_int(raw.get("shape_key") or raw.get("shape_code"))
            if shape_code is None and local_index is not None:
                shape_code = public_shapes.get(local_index)
            dims = _shape_dims(shape_code)
            if dims is not None:
                width, height = dims
            else:
                width = max(1, _parse_int(raw.get("width")) or 1)
                height = max(1, _parse_int(raw.get("height")) or 1)
            source_text = _text(raw.get("source") or raw.get("layout_source"), "")
            render_mode = _text(raw.get("render_mode") or "")
            if dims is not None and source_text == "public_info" and render_mode == "marker":
                render_mode = "footprint"
            quality_key = _quality_key(raw.get("quality"))
            observed_quality_counts[quality_key] = observed_quality_counts.get(quality_key, 0) + 1
            max_row = max(max_row, row + height - 1)
            max_col = max(max_col, col + width - 1)
            items.append(
                {
                    "row": row,
                    "col": col,
                    "width": width,
                    "height": height,
                    "quality": quality_key,
                    "local_index": local_index,
                    "item_id": raw.get("item_id"),
                    "shape_key": _text(shape_code or ""),
                    "label": _text(
                        raw.get("display_label")
                        or raw.get("item_name")
                        or raw.get("category_label"),
                        "",
                    ),
                    "tooltip": _text(raw.get("tooltip") or raw.get("item_name"), ""),
                    "cells": width * height if dims is not None else _parse_int(raw.get("cells")),
                    "source": source_text,
                    "layout_source": _text(raw.get("layout_source") or ""),
                    "render_mode": render_mode,
                }
            )
    if not isinstance(quality_counts, dict) or not quality_counts:
        quality_counts = quality_reveal_counts
    if not isinstance(quality_counts, dict) or not quality_counts:
        quality_counts = observed_quality_counts
    settlement_quality_counts = _quality_counts_from_text(snapshot.get("final_quality_counts"))
    if phase == "settled" and settlement_quality_counts:
        quality_counts = settlement_quality_counts
    columns = max(columns, max_col, 1)
    rows_hint = max(rows_hint, max_row, 1)
    if status != "available" or not items:
        return {
            "status": "unavailable",
            "summary_text": "等待公开轮廓/小地图",
            "layout_source": layout_source or "-",
            "columns": 10,
            "viewport_rows": 13,
            "known_items": 0,
            "drawable_items": 0,
            "final_total_items": final_total_items,
            "quality_counts": {},
            "items": [],
        }

    known = known_items if known_items is not None else len(items)
    drawable = drawable_items if drawable_items is not None else len(items)
    total = final_total_items if final_total_items is not None else known
    if phase == "settled" and total and drawable:
        known = drawable
    source_text = layout_source or "live_grid"
    if total and known != total:
        summary_text = f"{known}/{total} 件 · {source_text}"
    else:
        summary_text = f"{drawable} 件 · {source_text}"
    return {
        "status": "available",
        "summary_text": summary_text,
        "layout_source": source_text,
        "columns": columns,
        "viewport_rows": rows_hint,
        "known_items": known,
        "drawable_items": drawable,
        "final_total_items": final_total_items,
        "quality_counts": quality_counts,
        "items": items,
    }


def _quality_counts_from_text(text: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for part in _text(text, "").split(";"):
        if "=" not in part:
            continue
        key, raw_value = part.split("=", 1)
        quality = _quality_key(key.strip())
        value = _parse_int(raw_value)
        if value is not None:
            counts[quality] = value
    return counts


def _shape_dims(shape_code: Any) -> tuple[int, int] | None:
    code = _parse_int(shape_code)
    if code is None:
        return None
    width = code // 10
    height = code % 10
    if width <= 0 or height <= 0:
        return None
    return width, height


def _public_shape_by_local(snapshot: dict[str, Any]) -> dict[int, int]:
    out: dict[int, int] = {}
    rows = snapshot.get("public_info_rows")
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        for item in row.get("revealed_items_detail") or ():
            if not isinstance(item, dict):
                continue
            local = _parse_int(item.get("local_index"))
            shape = _parse_int(item.get("shape_code") or item.get("shape_key"))
            if local is not None and shape is not None and _shape_dims(shape) is not None:
                out[local] = shape
    return out


def _known_quality_footprint(
    minimap_summary: dict[str, Any],
    quality_key: str,
) -> tuple[int, int]:
    count = 0
    cells = 0
    items = minimap_summary.get("items")
    if not isinstance(items, list):
        return (0, 0)
    for item in items:
        if not isinstance(item, dict):
            continue
        if _quality_key(item.get("quality")) != quality_key:
            continue
        render_mode = _text(item.get("render_mode"), "")
        if render_mode != "footprint":
            continue
        item_cells = _parse_int(item.get("cells"))
        if item_cells is None or item_cells <= 0:
            width = _parse_int(item.get("width"))
            height = _parse_int(item.get("height"))
            if width is not None and height is not None:
                item_cells = width * height
        if item_cells is None or item_cells <= 0:
            continue
        count += 1
        cells += item_cells
    return (count, cells)


def _purple_gold_count_summary(counts: dict[str, Any]) -> str:
    if not isinstance(counts, dict) or not counts:
        return "-"
    parts: list[str] = []
    q4 = _parse_int(counts.get("q4"))
    q5 = _parse_int(counts.get("q5"))
    if q4 is not None:
        parts.append(f"紫件 {q4}")
    if q5 is not None:
        parts.append(f"金件 {q5}")
    return " · ".join(parts) if parts else "-"


def _known_purple_gold_summary(constraints: dict[str, Any]) -> str:
    if not isinstance(constraints, dict) or not constraints:
        return "-"
    summary = constraints.get("summary") if isinstance(constraints.get("summary"), dict) else {}
    counts = constraints.get("counts") if isinstance(constraints.get("counts"), dict) else {}
    known_counts = (
        counts.get("known_quality_counts")
        if isinstance(counts.get("known_quality_counts"), dict)
        else {}
    )
    q4 = _parse_int(summary.get("known_purple_item_count"))
    if q4 is None:
        q4 = _parse_int(known_counts.get("q4"))
    q5 = _parse_int(summary.get("known_gold_item_count"))
    if q5 is None:
        q5 = _parse_int(known_counts.get("q5"))
    return _purple_gold_count_summary({"q4": q4, "q5": q5})


def _snapshot_age_seconds(
    snapshot: dict[str, Any],
    snapshot_path: Path,
    source: dict[str, Any],
) -> float | None:
    candidates: list[float] = []
    for value in (snapshot.get("created_at"), source.get("created_at")):
        if value in (None, ""):
            continue
        try:
            candidates.append(time.time() - float(value))
        except (TypeError, ValueError):
            pass
    try:
        candidates.append(time.time() - snapshot_path.stat().st_mtime)
    except OSError:
        pass
    if not candidates:
        return None
    return max(0.0, min(candidates))


def _capture_status(snapshot_path: Path) -> dict[str, Any]:
    status_path = snapshot_path.parent / "capture_source_status.json"
    try:
        payload = _read_json(status_path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _capture_status_age_seconds(capture_status: dict[str, Any]) -> float | None:
    try:
        return time.time() - float(capture_status.get("ts"))
    except (TypeError, ValueError):
        return None


def _capture_session_id(capture_status: dict[str, Any]) -> str:
    return _text(capture_status.get("active_session_id"), "").strip()


def _monitor_lock(snapshot_path: Path) -> dict[str, Any]:
    lock_path = snapshot_path.parent / "monitor.lock"
    try:
        payload = _read_json(lock_path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _monitor_started_after_snapshot(
    lock_payload: dict[str, Any],
    snapshot_path: Path,
    snapshot: dict[str, Any],
    source: dict[str, Any],
) -> bool:
    try:
        started_at = float(lock_payload.get("started_at"))
    except (TypeError, ValueError):
        return False
    snapshot_markers: list[float] = []
    for value in (snapshot.get("created_at"), source.get("created_at")):
        try:
            snapshot_markers.append(float(value))
        except (TypeError, ValueError):
            pass
    try:
        snapshot_markers.append(snapshot_path.stat().st_mtime)
    except OSError:
        pass
    return bool(snapshot_markers) and started_at > max(snapshot_markers) + 1.0


def _stale_snapshot_payload(
    *,
    snapshot_path: Path,
    age_seconds: float | None,
    phase: str,
    context: dict[str, Any],
    snapshot: dict[str, Any],
    uc: dict[str, Any],
    reason: str = "stale_snapshot",
) -> dict[str, Any]:
    age_text = f"{int(age_seconds)}s" if age_seconds is not None else "unknown"
    return {
        "status": "stale_snapshot",
        "snapshot_path": str(snapshot_path),
        "updated_at_text": time.strftime("%H:%M:%S"),
        "context": {
            "hero": context.get("hero") or snapshot.get("hero") or "?",
            "is_ahmed": False,
            "is_supported_ref_hero": False,
            "map_id": context.get("map_id") or snapshot.get("map_id"),
            "model_map_id": context.get("model_map_id"),
            "round": context.get("round") or snapshot.get("round"),
            "action_round": context.get("action_round") or snapshot.get("action_round"),
            "phase": phase or "?",
            "session_id": context.get("session_id") or snapshot.get("session_id"),
            "file": None,
        },
        "reference": {
            "label": "Hero Ref",
            "source": "standby",
            "readiness": "standby",
            "note": (
                "new live session detected; waiting for first inference snapshot."
                if reason == "session_ahead"
                else "monitor restarted; waiting for first fresh inference snapshot."
                if reason == "monitor_restarted"
                else f"latest_snapshot is stale ({age_text}); waiting for the next live packet."
            ),
            "conservative": "-",
            "balanced": "-",
            "aggressive": "-",
            "raw_value_range": "-",
            "v3_conservative": "-",
            "v3_balanced": "-",
            "v3_aggressive": "-",
            "ref_minus_v3_balanced": "-",
            "ref_minus_v3_balanced_raw": None,
            "action": "等待新局",
            "risk_band": "-",
            "current_highest": "-",
            "decision_range": "-",
            "total_value_range": "-",
        },
        "red": {
            "count_range": "-",
            "cells_range": "-",
            "value_range": "-",
            "quality_count_summary": "-",
            "prior_rate": "-",
            "sample_rate": "-",
            "risk_reference": "",
        },
        "evidence": {
            "match_text": "-",
            "information_density": "-",
            "diagnostics": "",
            "latest_sent": {},
            "latest_result": {},
            "public_constraint_key": "",
            "evidence_profile_key": "",
            "source_mode": "standby",
            "ref_status": "standby",
            "ref_readiness": "standby",
            "ref_combo_count": "",
            "ref_input_summary": "-",
            "ref_notes": "",
        },
        "truth": {
            "available": False,
            "total_value": None,
            "total_items": None,
            "total_cells": None,
            "q6": {},
            "top_item": {},
        },
        "ahmed_ref": {"status": "standby", "source": "standby", "notes": []},
        "minimap": _minimap_summary({}, {}),
        "flags": [
            _flag("待机", "neutral", "waiting for next live packet"),
            _flag(
                "新局等待"
                if reason == "session_ahead"
                else "等待首包"
                if reason == "monitor_restarted"
                else "旧快照",
                "watch",
                f"phase={phase or '?'} age={age_text}",
            ),
        ],
        "stale": {
            "age_seconds": age_seconds,
            "phase": phase,
            "reason": reason,
        },
    }


def summarize_snapshot(snapshot: dict[str, Any], *, snapshot_path: Path) -> dict[str, Any]:
    uc = snapshot.get("ui_contract") if isinstance(snapshot.get("ui_contract"), dict) else {}
    context = uc.get("context") if isinstance(uc.get("context"), dict) else {}
    baseline = uc.get("baseline") if isinstance(uc.get("baseline"), dict) else {}
    decision = baseline.get("decision") if isinstance(baseline.get("decision"), dict) else {}
    posterior = baseline.get("posterior") if isinstance(baseline.get("posterior"), dict) else {}
    diagnostics = uc.get("diagnostics") if isinstance(uc.get("diagnostics"), dict) else {}
    constraints = uc.get("constraints") if isinstance(uc.get("constraints"), dict) else {}
    public_info = constraints.get("public_info") if isinstance(constraints.get("public_info"), dict) else {}
    truth = uc.get("truth") if isinstance(uc.get("truth"), dict) else {}
    actions = uc.get("actions") if isinstance(uc.get("actions"), dict) else {}
    source = uc.get("source") if isinstance(uc.get("source"), dict) else {}
    phase = _text(context.get("phase") or snapshot.get("phase"), "?")
    snapshot_session_id = _text(context.get("session_id") or snapshot.get("session_id"), "").strip()
    capture_status = _capture_status(snapshot_path)
    capture_session_id = _capture_session_id(capture_status)
    capture_age = _capture_status_age_seconds(capture_status)
    capture_recent = capture_age is not None and capture_age <= 20.0
    lock_payload = _monitor_lock(snapshot_path)
    monitor_restarted = _monitor_started_after_snapshot(
        lock_payload,
        snapshot_path,
        snapshot,
        source,
    )
    capture_session_ahead = (
        capture_recent
        and bool(capture_session_id)
        and bool(snapshot_session_id)
        and capture_session_id != snapshot_session_id
    )
    age_seconds = _snapshot_age_seconds(snapshot, snapshot_path, source)
    is_age_stale = (
        age_seconds is not None
        and age_seconds >= STALE_SNAPSHOT_SECONDS
        and not (phase == "settled" and capture_session_id == snapshot_session_id)
    )
    is_settled_stale = (
        phase == "settled"
        and age_seconds is not None
        and age_seconds >= SETTLED_STALE_SECONDS
    )
    if capture_session_ahead or monitor_restarted or is_age_stale or is_settled_stale:
        return _stale_snapshot_payload(
            snapshot_path=snapshot_path,
            age_seconds=age_seconds,
            phase=phase,
            context=context,
            snapshot=snapshot,
            uc=uc,
            reason=(
                "session_ahead"
                if capture_session_ahead
                else "monitor_restarted"
                if monitor_restarted
                else "stale_snapshot"
                if not is_settled_stale
                else "settled_stale"
            ),
        )
    if run_reference_engine is not None:
        try:
            ref_result = run_reference_engine(snapshot).as_dict()
        except Exception as exc:  # noqa: BLE001 - prototype diagnostics
            ref_result = {
                "status": "error",
                "source": "ref_v0",
                "notes": [str(exc)],
            }
    else:
        ref_result = {"status": "unavailable", "source": "ref_v0", "notes": []}
    ref_evidence = ref_result.get("evidence") if isinstance(ref_result.get("evidence"), dict) else {}

    hero = _hero_from_context(
        context.get("hero") or snapshot.get("hero"),
        context.get("hero_id"),
        context.get("player_hero_id"),
        context.get("current_player_hero_id"),
        snapshot.get("hero_id"),
        snapshot.get("player_hero_id"),
        snapshot.get("current_player_hero_id"),
    )
    if _is_unknown_hero(hero):
        evidence_hero = _hero_from_context(ref_evidence.get("hero"))
        if not _is_unknown_hero(evidence_hero):
            hero = evidence_hero
    hero_key = hero.lower()
    is_supported_ref_hero = hero_key in {
        "aisha",
        "艾莎",
        "ahmed",
        "ahmad",
        "艾哈迈德",
        "victor",
        "维克托",
    }

    info_band = _text(
        public_info.get("information_density_band")
        or _dig(snapshot, "model_eval", "information_density_band"),
        "",
    )
    flags: list[dict[str, str]] = []
    replay = snapshot.get("replay_carousel") if isinstance(snapshot.get("replay_carousel"), dict) else {}
    if replay.get("active"):
        replay_detail_parts = [
            _text(replay.get("sample"), "-"),
            _text(replay.get("label"), "-"),
            f"state_sort={_text(replay.get('sort_id'), '-')}",
        ]
        if replay.get("bid_sort_id") not in (None, ""):
            replay_detail_parts.append(f"bid_sort={_text(replay.get('bid_sort_id'), '-')}")
        if replay.get("observed_round") not in (None, ""):
            replay_detail_parts.append(f"observed=R{_text(replay.get('observed_round'), '-')}")
        flags.append(
            _flag(
                f"轮播 {replay.get('step_index', '?')}/{replay.get('step_total', '?')}",
                "neutral",
                "; ".join(replay_detail_parts),
            )
        )
    if not is_supported_ref_hero:
        flags.append(_flag("等待结构英雄", "neutral", f"当前英雄 {hero}"))
    if phase == "settled":
        flags.append(_flag("已结算", "neutral"))
    if _text(context.get("map_alias_mode") or source.get("map_alias_mode")):
        flags.append(_flag("地图 fallback", "watch", _text(context.get("map_alias_mode") or source.get("map_alias_mode"))))
    if info_band in {"low", "低"}:
        flags.append(_flag("证据低", "watch"))
    ref_ok = ref_result.get("status") in {"ok", "count_prior"}
    ref_notes = tuple(str(item) for item in ref_result.get("notes") or ())
    ref_sparse_exact_prior = "sparse_exact_total_prior_enumeration" in ref_notes
    ref_combo_cap_hit = "combo_cap_hit" in ref_notes
    ref_count_sums = ref_evidence.get("count_sums") if isinstance(ref_evidence.get("count_sums"), dict) else {}
    victor_missing_q456 = (
        hero_key in {"victor", "维克托"}
        and phase != "settled"
        and "q4q5q6" not in ref_count_sums
        and "q4q5" not in ref_count_sums
    )
    ref_review_only = any(note.startswith("settlement_review") for note in ref_notes)
    if ref_ok and ref_review_only:
        ref_readiness = "review_only"
    elif ref_ok and victor_missing_q456:
        ref_readiness = "victor_q456_prior"
    elif ref_result.get("status") == "count_prior" and ref_sparse_exact_prior:
        ref_readiness = "sparse_exact_prior"
    elif ref_result.get("status") == "count_prior":
        ref_readiness = "count_prior"
    elif ref_ok:
        ref_readiness = "live_ready"
    else:
        ref_readiness = _text(ref_result.get("status"), "unavailable")
    ref_display_ready = (
        ref_ok
        and not ref_review_only
        and phase != "settled"
    )
    ref_balanced = _parse_money(ref_result.get("balanced")) if ref_ok else None
    v3_balanced = _parse_money(decision.get("attack_bid"))
    display_source = (
        "ref_prior"
        if ref_readiness in {"count_prior", "sparse_exact_prior", "victor_q456_prior"}
        else "ref_v0"
        if ref_display_ready
        else "ref_waiting"
    )
    ref_minus_v3 = (
        ref_balanced - v3_balanced
        if ref_balanced is not None and v3_balanced is not None
        else None
    )
    ref_status = _text(ref_result.get("status"), "")
    if is_supported_ref_hero and ref_status == "missing_total_count":
        flags.append(_flag("缺总件数", "watch"))
        flags.append(_flag("等待外援输入", "neutral"))
    if victor_missing_q456:
        flags.append(_flag("缺紫金红件数", "watch", "Victor 100209 not captured; using prior"))
    if ref_readiness == "sparse_exact_prior":
        flags.append(_flag("宽约束快速", "watch", "exact total count with probability-prior quality split"))
    if ref_readiness == "count_prior":
        flags.append(_flag("总件估计", "watch", "ref count prior; no exact total count"))
    if ref_combo_cap_hit:
        flags.append(_flag("组合截断", "watch", f"ref combos={_text(ref_result.get('combo_count'), '?')}"))
    if ref_review_only:
        flags.append(_flag("回放口径", "watch", "ref_v0 used settlement review fields"))
    if ref_ok:
        flags.append(_flag("外援 ref_v0", "neutral"))
    elif is_supported_ref_hero:
        flags.append(_flag("外援未就绪", "watch", _text(ref_result.get("status"))))
    public_numeric_summary = _text(public_info.get("public_numeric_summary"), "").strip()
    if public_numeric_summary:
        flags.append(_flag("公开信息", "neutral", public_numeric_summary))

    latest_result = actions.get("latest_result") if isinstance(actions.get("latest_result"), dict) else {}
    latest_sent = actions.get("latest_sent") if isinstance(actions.get("latest_sent"), dict) else {}
    ref_red_count_range = (
        " / ".join(_money(v, "?") for v in ref_result.get("red_count_range", ()))
        if ref_display_ready
        else ""
    )
    ref_red_cells_range = (
        " / ".join(_money(v, "?") for v in ref_result.get("red_cells_range", ()))
        if ref_display_ready
        else ""
    )
    ref_red_value_range = (
        " / ".join(_money(v, "?") for v in ref_result.get("red_value_range", ()))
        if ref_display_ready
        else ""
    )
    quality_count_ranges = (
        ref_result.get("quality_count_ranges")
        if isinstance(ref_result.get("quality_count_ranges"), dict)
        else {}
    )
    q4_count_range = (
        " / ".join(_money(v, "?") for v in quality_count_ranges.get("q4", ()))
        if ref_display_ready
        else ""
    )
    q5_count_range = (
        " / ".join(_money(v, "?") for v in quality_count_ranges.get("q5", ()))
        if ref_display_ready
        else ""
    )

    minimap_summary = _minimap_summary(snapshot, uc)
    minimap_quality_summary = ""
    quality_counts = minimap_summary.get("quality_counts")
    if isinstance(quality_counts, dict) and quality_counts:
        minimap_quality_summary = " ".join(
            f"{key.upper()}:{quality_counts[key]}"
            for key in ("q6", "q5", "q4", "q3", "q2", "q1")
            if key in quality_counts
        )
        if minimap_quality_summary:
            flags.append(_flag("品质标记", "neutral", minimap_quality_summary))

    display_red_count_range = ref_red_count_range or "-"
    display_red_cells_range = ref_red_cells_range or "-"
    display_red_value_range = ref_red_value_range or "-"
    display_quality_count_summary = (
        f"紫件 {q4_count_range or '?'} · 金件 {q5_count_range or '?'}"
        if ref_display_ready
        else "-"
    )
    if ref_display_ready and ref_readiness == "count_prior":
        display_red_risk_reference = "总件先验"
    elif ref_display_ready and ref_readiness == "sparse_exact_prior":
        display_red_risk_reference = "总件已知，品质先验"
    elif ref_display_ready and ref_readiness == "victor_q456_prior":
        display_red_risk_reference = "紫金红先验"
    elif ref_display_ready:
        display_red_risk_reference = "ref_v0 估计"
    else:
        display_red_risk_reference = "等待总件/品质输入"
    v3_assist_notes: list[str] = []
    known_q6_count, known_q6_cells = _known_quality_footprint(
        minimap_summary,
        "q6",
    )
    if ref_display_ready and phase != "settled" and known_q6_count > 0:
        display_red_count_range = _floor_range_text(
            display_red_count_range,
            known_q6_count,
        )
        display_red_cells_range = _floor_range_text(
            display_red_cells_range,
            known_q6_cells,
        )
        known_note = f"已见红{known_q6_count}件/{known_q6_cells}格"
        v3_assist_notes.append(known_note)
        flags.append(
            _flag(
                "已见红",
                "neutral",
                f"known q6 footprint lower bound: {known_q6_count} item(s), {known_q6_cells} cells",
            )
        )
    ref_q6_mid = _range_mid(ref_red_count_range)
    v3_q6_mid = _range_mid(posterior.get("q6_count_range"))
    if (
        ref_display_ready
        and phase != "settled"
        and ref_q6_mid is not None
        and v3_q6_mid is not None
        and abs(ref_q6_mid - v3_q6_mid) >= 1
    ):
        flags.append(
            _flag(
                "v3红件对照",
                "watch",
                f"ref median q6={ref_q6_mid}; v3 median q6={v3_q6_mid}; display keeps ref",
            )
        )
        v3_assist_notes.append(f"v3红中位{v3_q6_mid}仅对照")
    if ref_display_ready and ref_minus_v3 is not None and abs(ref_minus_v3) >= 120_000:
        flags.append(
            _flag(
                "v3价差",
                "watch",
                f"ref-v3 balanced={ref_minus_v3:+,}; main quote keeps ref",
            )
        )
    display_red_risk_reference = _join_notes(
        display_red_risk_reference,
        *v3_assist_notes,
    )
    main_conservative = (
        _money(ref_result.get("conservative"))
        if ref_display_ready
        else "-"
    )
    main_balanced = (
        _money(ref_result.get("balanced"))
        if ref_display_ready
        else "-"
    )
    main_aggressive = (
        _money(ref_result.get("aggressive"))
        if ref_display_ready
        else "-"
    )
    main_action = (
        "估计参考"
        if ref_readiness in {"count_prior", "sparse_exact_prior", "victor_q456_prior"} and ref_display_ready
        else "参考可用"
        if ref_display_ready
        else "等待外援输入"
    )
    main_current_highest = _text(decision.get("current_highest"), "-")
    price_titles = {
        "conservative": "保守",
        "balanced": "参考",
        "aggressive": "激进",
    }
    reference_note = (
        "External ref_v0 count/cells/value engine; total count estimated from ref prior."
        if ref_readiness == "count_prior"
        else "External ref_v0 count/cells/value engine; exact total count with probability-prior quality split."
        if ref_readiness == "sparse_exact_prior"
        else "External ref_v0 count/cells/value engine; Victor q4+q5+q6 count missing, using prior."
        if ref_readiness == "victor_q456_prior"
        else "External ref_v0 count/cells/value engine; not promoted."
        if ref_display_ready
        else (
            "ref_v0 needs exact total count; main quote is held."
            if ref_status == "missing_total_count"
            else "External ref_v0 is not live-ready; main quote is held."
        )
    )
    truth_available = bool(truth.get("available"))
    settlement_total = _parse_money(truth.get("total_value"))
    settlement_estimate = ref_balanced
    if phase == "settled" and truth_available:
        truth_q6 = truth.get("q6") if isinstance(truth.get("q6"), dict) else {}
        display_red_count_range = f"{_text(truth_q6.get('count'), '?')} 件"
        display_red_cells_range = f"{_text(truth_q6.get('cells'), '?')} 格"
        display_red_value_range = _money(truth_q6.get("value"))
        settlement_quality_counts = _quality_counts_from_text(snapshot.get("final_quality_counts"))
        if settlement_quality_counts:
            settlement_quality_counts.setdefault("q4", 0)
            settlement_quality_counts.setdefault("q5", 0)
        settlement_quality_summary = _purple_gold_count_summary(settlement_quality_counts)
        minimap_settlement_summary = _purple_gold_count_summary(quality_counts)
        known_purple_gold_summary = _known_purple_gold_summary(constraints)
        if known_purple_gold_summary != "-":
            display_quality_count_summary = known_purple_gold_summary
        elif settlement_quality_summary != "-":
            display_quality_count_summary = settlement_quality_summary
        elif minimap_settlement_summary != "-":
            display_quality_count_summary = minimap_settlement_summary
        red_review_parts = ["真实结算"]
        decision_value = _parse_money(truth_q6.get("decision_value"))
        replacement_value = _parse_money(truth_q6.get("tail_replacement_value"))
        trimmed_tail = _parse_money(truth_q6.get("trimmed_tail_value"))
        if trimmed_tail:
            red_review_parts.append(f"裁尾{_money(decision_value)}")
            red_review_parts.append(f"替换{_money(replacement_value)}")
        display_red_risk_reference = "；".join(red_review_parts)
        price_titles = {
            "conservative": "估价",
            "balanced": "结算",
            "aggressive": "差值",
        }
        display_source = "settlement"
        main_conservative = _money(settlement_estimate)
        main_balanced = _money(settlement_total)
        main_aggressive = (
            _signed_money(settlement_total - settlement_estimate)
            if settlement_total is not None and settlement_estimate is not None
            else "-"
        )
        main_action = "结算完成"
        main_current_highest = f"总值 {_money(settlement_total)}"
        reference_note = "Settlement review: top cards show ref replay estimate, final total, and final-minus-estimate delta."

    ref_decision_range = (
        f"{_money(ref_result.get('conservative'))} / "
        f"{_money(ref_result.get('balanced'))} / "
        f"{_money(ref_result.get('aggressive'))}"
        if ref_ok
        else "-"
    )
    ref_total_value_range = (
        f"{_money(ref_result.get('value_p25'))} / "
        f"{_money(ref_result.get('value_p50'))} / "
        f"{_money(ref_result.get('value_p75'))}"
        if ref_ok
        else "-"
    )

    return {
        "status": "ok",
        "snapshot_path": str(snapshot_path),
        "updated_at": snapshot.get("created_at") or source.get("created_at"),
        "updated_at_text": time.strftime(
            "%H:%M:%S",
            time.localtime(float(snapshot.get("created_at") or source.get("created_at") or time.time())),
        ),
        "context": {
            "hero": hero,
            "is_ahmed": hero_key in {"ahmed", "ahmad", "艾哈迈德"},
            "is_supported_ref_hero": is_supported_ref_hero,
            "map_id": context.get("map_id") or snapshot.get("map_id"),
            "model_map_id": context.get("model_map_id") or source.get("model_map_id"),
            "round": context.get("round") or snapshot.get("round"),
            "action_round": context.get("action_round") or snapshot.get("action_round"),
            "phase": phase,
            "session_id": context.get("session_id") or snapshot.get("session_id"),
            "file": source.get("file") or snapshot.get("file"),
        },
        "reference": {
            "label": "Hero Ref",
            "source": display_source,
            "readiness": ref_readiness,
            "note": reference_note,
            "price_titles": price_titles,
            "conservative": main_conservative,
            "balanced": main_balanced,
            "aggressive": main_aggressive,
            "raw_value_range": ref_total_value_range,
            "v3_conservative": _text(decision.get("defend_bid"), "-"),
            "v3_balanced": _text(decision.get("attack_bid"), "-"),
            "v3_aggressive": _text(decision.get("stop_price"), "-"),
            "ref_minus_v3_balanced": (
                _money(ref_minus_v3)
                if ref_minus_v3 is not None
                else "-"
            ),
            "ref_minus_v3_balanced_raw": ref_minus_v3,
            "action": main_action,
            "risk_band": _text(decision.get("risk_band"), "-"),
            "current_highest": main_current_highest,
            "decision_range": ref_decision_range,
            "total_value_range": ref_total_value_range,
        },
        "red": {
            "count_range": display_red_count_range,
            "cells_range": display_red_cells_range,
            "value_range": display_red_value_range,
            "quality_count_summary": display_quality_count_summary,
            "prior_rate": _text(posterior.get("q6_prior_rate"), "-"),
            "sample_rate": _text(posterior.get("q6_sample_rate"), "-"),
            "risk_reference": display_red_risk_reference,
        },
        "evidence": {
            "match_text": ref_readiness,
            "information_density": _text(decision.get("information_density") or info_band, "-"),
            "diagnostics": ";".join(ref_notes),
            "latest_sent": latest_sent,
            "latest_result": latest_result,
            "public_constraint_key": _text(public_info.get("public_constraint_key"), ""),
            "evidence_profile_key": _text(public_info.get("evidence_profile_key"), ""),
            "public_numeric_summary": public_numeric_summary,
            "minimap_quality_summary": minimap_quality_summary,
            "source_mode": display_source,
            "ref_status": _text(ref_result.get("status"), ""),
            "ref_readiness": ref_readiness,
            "ref_combo_count": _text(ref_result.get("combo_count"), ""),
            "ref_input_summary": _ref_input_summary(ref_result),
            "ref_notes": ";".join(ref_notes),
        },
        "truth": {
            "available": bool(truth.get("available")),
            "total_value": truth.get("total_value"),
            "total_items": truth.get("total_items"),
            "total_cells": truth.get("total_cells"),
            "q6": truth.get("q6") if isinstance(truth.get("q6"), dict) else {},
            "top_item": truth.get("top_item") if isinstance(truth.get("top_item"), dict) else {},
        },
        "ahmed_ref": ref_result,
        "minimap": minimap_summary,
        "flags": flags,
    }


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Ahmed Live Reference</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101316;
      --panel: #171b1f;
      --line: #2b3238;
      --text: #edf1f2;
      --muted: #9aa6ad;
      --green: #54c58a;
      --amber: #e7b75f;
      --red: #ef7771;
      --blue: #7fb7ff;
      --chip: #232a30;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      letter-spacing: 0;
    }
    main {
      width: min(760px, calc(100vw - 20px));
      margin: 10px auto;
    }
    .shell {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      overflow: hidden;
      box-shadow: 0 12px 34px rgba(0,0,0,.32);
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      align-items: center;
    }
    .title {
      font-size: 18px;
      font-weight: 700;
      white-space: nowrap;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
    }
    .chip {
      background: var(--chip);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      line-height: 1.25;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      padding: 10px 12px;
    }
    .tile {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px;
      min-height: 70px;
      background: #12171b;
    }
    .tile label {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }
    .price {
      font-size: 24px;
      font-weight: 800;
      line-height: 1.1;
      white-space: nowrap;
    }
    .safe .price { color: var(--green); }
    .mid .price { color: var(--amber); }
    .hot .price { color: var(--red); }
    .section {
      display: grid;
      grid-template-columns: 1.15fr .85fr;
      gap: 8px;
      padding: 0 12px 10px;
    }
    .box {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px;
      background: #12171b;
      min-height: 96px;
    }
    h2 {
      margin: 0 0 8px;
      font-size: 13px;
      color: var(--muted);
      font-weight: 700;
    }
    .row {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 3px 0;
      font-size: 13px;
      border-bottom: 1px solid rgba(255,255,255,.04);
    }
    .row:last-child { border-bottom: 0; }
    .row span:first-child { color: var(--muted); }
    .row span:last-child { text-align: right; overflow-wrap: anywhere; }
    .flags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 6px;
    }
    .flag {
      border-radius: 999px;
      padding: 4px 8px;
      font-size: 12px;
      background: var(--chip);
      border: 1px solid var(--line);
    }
    .flag.risk { color: #ffd4d1; border-color: rgba(239,119,113,.55); }
    .flag.watch { color: #ffe2a8; border-color: rgba(231,183,95,.55); }
    .flag.neutral { color: #d4e6ff; border-color: rgba(127,183,255,.5); }
    footer {
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 11px;
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }
    code { color: #d8e6ef; }
    @media (max-width: 640px) {
      .grid, .section { grid-template-columns: 1fr; }
      header { align-items: flex-start; flex-direction: column; }
      .meta { justify-content: flex-start; }
      .price { font-size: 22px; }
    }
  </style>
</head>
<body>
<main>
  <div class="shell">
    <header>
      <div>
        <div class="title" id="title">Ahmed Live Reference</div>
        <div class="flags" id="flags"></div>
      </div>
      <div class="meta">
        <span class="chip" id="phase">phase</span>
        <span class="chip" id="session">session</span>
        <span class="chip" id="updated">--:--:--</span>
      </div>
    </header>
    <div class="grid">
      <div class="tile safe"><label>保守</label><div class="price" id="safe">-</div></div>
      <div class="tile mid"><label>参考</label><div class="price" id="mid">-</div></div>
      <div class="tile hot"><label>激进</label><div class="price" id="hot">-</div></div>
    </div>
    <div class="section">
      <div class="box">
        <h2>红品与价值</h2>
        <div class="row"><span>红品件数</span><span id="redCount">-</span></div>
        <div class="row"><span>红品格数</span><span id="redCells">-</span></div>
        <div class="row"><span>红品价值</span><span id="redValue">-</span></div>
        <div class="row"><span>决策区间</span><span id="decisionRange">-</span></div>
        <div class="row"><span>总值区间</span><span id="totalRange">-</span></div>
      </div>
      <div class="box">
        <h2>证据</h2>
        <div class="row"><span>匹配</span><span id="match">-</span></div>
        <div class="row"><span>密度</span><span id="density">-</span></div>
        <div class="row"><span>来源</span><span id="sourceMode">-</span></div>
        <div class="row"><span>最近结果</span><span id="latestResult">-</span></div>
        <div class="row"><span>诊断</span><span id="diag">-</span></div>
      </div>
    </div>
    <div class="section">
      <div class="box">
        <h2>当前建议</h2>
        <div class="row"><span>动作</span><span id="action">-</span></div>
        <div class="row"><span>风险</span><span id="riskBand">-</span></div>
        <div class="row"><span>当前最高</span><span id="highest">-</span></div>
        <div class="row"><span>q6 提醒</span><span id="q6Note">-</span></div>
      </div>
      <div class="box">
        <h2>结算对照</h2>
        <div class="row"><span>状态</span><span id="truthState">-</span></div>
        <div class="row"><span>总值/件/格</span><span id="truthTotal">-</span></div>
        <div class="row"><span>红品 truth</span><span id="truthQ6">-</span></div>
        <div class="row"><span>最高物</span><span id="truthTop">-</span></div>
      </div>
    </div>
    <footer>
      <span>原作：猫饭团子uu · UI/计算优化：加菲_barista · 不接正式出价。</span>
      <span><code id="path"></code></span>
    </footer>
  </div>
</main>
<script>
const $ = (id) => document.getElementById(id);
function text(v, fallback='-') {
  if (v === null || v === undefined || v === '') return fallback;
  return String(v);
}
function latestAction(v) {
  if (!v || typeof v !== 'object') return '-';
  const tool = v.tool || v.action_id || '';
  const result = v.result ? ` = ${v.result}` : '';
  return `${tool}${result}` || '-';
}
function renderFlags(flags) {
  const root = $('flags');
  root.innerHTML = '';
  if (!flags || !flags.length) {
    const el = document.createElement('span');
    el.className = 'flag neutral';
    el.textContent = '正常监测';
    root.appendChild(el);
    return;
  }
  for (const flag of flags) {
    const el = document.createElement('span');
    el.className = `flag ${flag.level || 'watch'}`;
    el.title = flag.detail || '';
    el.textContent = flag.label || 'watch';
    root.appendChild(el);
  }
}
function render(data) {
  const c = data.context || {};
  const r = data.reference || {};
  const red = data.red || {};
  const ev = data.evidence || {};
  const truth = data.truth || {};
  $('title').textContent = `${text(c.hero, '?')} · ${text(c.map_id, '?')} · R${text(c.round, '?')}`;
  $('phase').textContent = text(c.phase);
  $('session').textContent = text(c.session_id);
  $('updated').textContent = text(data.updated_at_text);
  $('safe').textContent = text(r.conservative);
  $('mid').textContent = text(r.balanced);
  $('hot').textContent = text(r.aggressive);
  $('redCount').textContent = text(red.count_range);
  $('redCells').textContent = text(red.cells_range);
  $('redValue').textContent = text(red.value_range);
  $('decisionRange').textContent = text(r.decision_range);
  $('totalRange').textContent = text(r.total_value_range);
  $('match').textContent = text(ev.match_text);
  $('density').textContent = text(ev.information_density);
  $('sourceMode').textContent = text(ev.source_mode);
  const latestResult = latestAction(ev.latest_result);
  $('latestResult').textContent = latestResult !== '-' ? latestResult : latestAction(ev.latest_sent);
  $('diag').textContent = text(ev.diagnostics);
  $('action').textContent = text(r.action);
  $('riskBand').textContent = text(r.risk_band);
  $('highest').textContent = text(r.current_highest);
  $('q6Note').textContent = text(red.risk_reference);
  $('truthState').textContent = truth.available ? 'available' : 'not settled';
  $('truthTotal').textContent = truth.available ? `${text(truth.total_value)} / ${text(truth.total_items)}件 / ${text(truth.total_cells)}格` : '-';
  const q6 = truth.q6 || {};
  $('truthQ6').textContent = truth.available ? `${text(q6.count)}件 / ${text(q6.cells)}格 / ${text(q6.value)}` : '-';
  const top = truth.top_item || {};
  $('truthTop').textContent = truth.available ? `${text(top.name)} ${text(top.value)}` : '-';
  $('path').textContent = text(data.snapshot_path, '');
  renderFlags(data.flags || []);
}
async function refresh() {
  try {
    const response = await fetch('/api/latest', {cache: 'no-store'});
    const data = await response.json();
    if (data.status === 'ok') render(data);
  } catch (err) {
    renderFlags([{label: '读取失败', level: 'risk', detail: String(err)}]);
  }
}
refresh();
setInterval(refresh, 1000);
</script>
</body>
</html>
"""


@dataclass(frozen=True)
class ServerConfig:
    project_root: Path
    snapshot: Path

    @property
    def snapshot_path(self) -> Path:
        if self.snapshot.is_absolute():
            return self.snapshot
        return self.project_root / self.snapshot


def make_handler(config: ServerConfig) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "AhmadLiveReference/0.1"

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self) -> None:
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - stdlib API
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                self._send_html()
                return
            if parsed.path == "/api/health":
                self._send_json(
                    {
                        "status": "ok",
                        "snapshot_path": str(config.snapshot_path),
                        "exists": config.snapshot_path.exists(),
                    }
                )
                return
            if parsed.path == "/api/latest":
                try:
                    snapshot = _read_json(config.snapshot_path)
                    self._send_json(
                        summarize_snapshot(snapshot, snapshot_path=config.snapshot_path)
                    )
                except FileNotFoundError:
                    self._send_json(
                        {
                            "status": "missing_snapshot",
                            "snapshot_path": str(config.snapshot_path),
                        },
                        status=404,
                    )
                except Exception as exc:  # noqa: BLE001 - expose prototype diagnostics
                    self._send_json(
                        {
                            "status": "error",
                            "error": str(exc),
                            "snapshot_path": str(config.snapshot_path),
                        },
                        status=500,
                    )
                return
            self._send_json({"status": "not_found", "path": parsed.path}, status=404)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the isolated Ahmed live reference panel.")
    parser.add_argument("--project-root", default=str(DEFAULT_PROJECT_ROOT))
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args(argv)

    config = ServerConfig(
        project_root=Path(args.project_root).resolve(),
        snapshot=Path(args.snapshot),
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(config))
    print(f"Ahmed live reference panel: http://{args.host}:{args.port}", flush=True)
    print(f"Snapshot: {config.snapshot_path}", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
