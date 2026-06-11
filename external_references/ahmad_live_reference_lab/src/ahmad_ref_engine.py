from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
from functools import lru_cache
import copy
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable


def _project_root() -> Path:
    env_root = os.environ.get("BIDKING_LAB_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def _static_data_candidates() -> tuple[Path, ...]:
    env_static = os.environ.get("BIDKING_AHMAD_STATIC_DATA")
    candidates: list[Path] = []
    if env_static:
        candidates.append(Path(env_static).expanduser())
    relative = Path(
        "external_references",
        "AuctionAnalyzer4.13.3",
        "_decompiled",
        "MapBidCalculator",
        "MapBidCalculator",
        "Models",
        "StaticData.cs",
    )
    candidates.append(ROOT / relative)
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / relative)
        candidates.append(Path(bundle_root) / "StaticData.cs")
    candidates.append(Path.cwd() / relative)
    return tuple(candidates)


def _resolve_static_data() -> Path:
    for candidate in _static_data_candidates():
        try:
            if candidate.exists():
                return candidate.resolve()
        except OSError:
            continue
    return _static_data_candidates()[0]


ROOT = _project_root()
STATIC_DATA = _resolve_static_data()

QUALITY_KEYS = ("q1", "q3", "q4", "q5", "q6")
LOW_SPLIT_KEYS = ("white", "green")
LOW_SPLIT_ALIASES = {
    "1": "white",
    "q1": "white",
    "white": "white",
    "白": "white",
    "2": "green",
    "q2": "green",
    "green": "green",
    "绿": "green",
}
DEFAULT_ITEM_VALUES = {
    "q1": 400.0,
    "q3": 2500.0,
    "q4": 9045.5,
    "q5": 40000.0,
    "q6": 160000.0,
}
VALUE_UNCERTAINTY_CV = {
    "q1": 0.10,
    "q3": 0.18,
    "q4": 0.24,
    "q5": 0.32,
    "q6": 0.45,
}
VALUE_DISTRIBUTION_POINTS = (
    (-1.0, 0.125),
    (-0.5, 0.25),
    (0.0, 0.25),
    (0.5, 0.25),
    (1.0, 0.125),
)
DEFAULT_GRID_MEANS = {
    "q1": 2.2,
    "q3": 2.2,
    "q4": 2.4,
    "q5": 2.8,
    "q6": 3.2,
}
DISPLAY_GRID_TOPK = 3
QUALITY_TO_INDEX = {"q1": (0, 1), "q3": (2,), "q4": (3,), "q5": (4,), "q6": (5,)}
QUALITY_TO_TIER_INDEX = {"q1": (0, 1), "q3": (2,), "q4": (3,), "q5": (4,), "q6": (5,)}
QUALITY_NUM_TO_KEY = {"1": "q1", "2": "q1", "3": "q3", "4": "q4", "5": "q5", "6": "q6"}
ACTION_AVG_CELLS = {
    "100110": "q1",
    "100111": "q3",
    "100112": "q4",
    "100113": "q5",
    "100114": "q6",
    "1002041": "q5",
    "1002042": "q4",
    "1002043": "q3",
}
ACTION_TOTAL_CELLS = {
    "100104": "q1",
    "100105": "q3",
    "100106": "q4",
    "100107": "q5",
    "100108": "q6",
}
ACTION_VALUE_SUM = {
    "100122": "q1",
    "100123": "q3",
    "100124": "q4",
    "100125": "q5",
    "100126": "q6",
}
ACTION_COUNTS = {
    "100116": "q1",
    "100117": "q3",
    "100118": "q4",
    "100119": "q5",
    "100120": "q6",
    "1002044": "q1",
}
ACTION_DIAGNOSTIC_ONLY = {
    "100121": "total_value",
    "100127": "all_items",
    "100134": "all_item_quality",
}
PUBLIC_AVG_CELLS = {
    "q4_avg_cells": "q4",
    "q5_avg_cells": "q5",
    "q6_avg_cells": "q6",
}
PUBLIC_COUNTS = {
    "q4_item_count": "q4",
    "q5_item_count": "q5",
    "q6_item_count": "q6",
}
PUBLIC_AVG_VALUES = {
    "q4_avg_value": "q4",
    "q5_avg_value": "q5",
    "q6_avg_value": "q6",
}
PUBLIC_BUCKET_OUTLINE_QUALITY = {
    200001: "q4",
    200002: "q5",
    200003: "q6",
}
HERO_BY_ID = {
    103: "aisha",
    204: "ahmed",
    209: "victor",
}
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


@dataclass(frozen=True)
class RefEvidence:
    hero: str
    map_id: int | None
    phase: str
    total_count: int | None
    fixed_counts: dict[str, int]
    min_counts: dict[str, int]
    count_sums: dict[str, int]
    avg_cells: dict[str, float]
    quality_cells: dict[str, float]
    avg_values: dict[str, float]
    quality_values: dict[str, float]
    split_counts: dict[str, int]
    split_quality_cells: dict[str, float]
    split_avg_cells: dict[str, float]
    random_value_floors: tuple[tuple[int, float], ...]
    total_grid_target: float | None
    v3_conservative: str
    v3_balanced: str
    v3_aggressive: str
    source_notes: tuple[str, ...]


@dataclass(frozen=True)
class RefCombo:
    counts: dict[str, int]
    grids: dict[str, float]
    value: float
    weight: float
    total_grid: float


@dataclass(frozen=True)
class RefResult:
    status: str
    source: str
    conservative: int | None
    balanced: int | None
    aggressive: int | None
    value_p25: int | None
    value_p50: int | None
    value_p75: int | None
    combo_count: int
    red_count_range: tuple[int | None, int | None, int | None]
    red_cells_range: tuple[int | None, int | None, int | None]
    red_value_range: tuple[int | None, int | None, int | None]
    quality_count_ranges: dict[str, tuple[int | None, int | None, int | None]]
    quality_cells_ranges: dict[str, tuple[int | None, int | None, int | None]]
    total_grid_range: tuple[int | None, int | None, int | None]
    notes: tuple[str, ...]
    evidence: RefEvidence

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "conservative": self.conservative,
            "balanced": self.balanced,
            "aggressive": self.aggressive,
            "value_p25": self.value_p25,
            "value_p50": self.value_p50,
            "value_p75": self.value_p75,
            "combo_count": self.combo_count,
            "red_count_range": list(self.red_count_range),
            "red_cells_range": list(self.red_cells_range),
            "red_value_range": list(self.red_value_range),
            "quality_count_ranges": {
                key: list(value) for key, value in self.quality_count_ranges.items()
            },
            "quality_cells_ranges": {
                key: list(value) for key, value in self.quality_cells_ranges.items()
            },
            "total_grid_range": list(self.total_grid_range),
            "notes": list(self.notes),
            "evidence": {
                "hero": self.evidence.hero,
                "map_id": self.evidence.map_id,
                "phase": self.evidence.phase,
                "total_count": self.evidence.total_count,
                "fixed_counts": dict(self.evidence.fixed_counts),
                "min_counts": dict(self.evidence.min_counts),
                "count_sums": dict(self.evidence.count_sums),
                "avg_cells": dict(self.evidence.avg_cells),
                "quality_cells": dict(self.evidence.quality_cells),
                "avg_values": dict(self.evidence.avg_values),
                "quality_values": dict(self.evidence.quality_values),
                "split_counts": dict(self.evidence.split_counts),
                "split_quality_cells": dict(self.evidence.split_quality_cells),
                "split_avg_cells": dict(self.evidence.split_avg_cells),
                "random_value_floors": [
                    [sample_count, value_floor]
                    for sample_count, value_floor in self.evidence.random_value_floors
                ],
                "total_grid_target": self.evidence.total_grid_target,
                "source_notes": list(self.evidence.source_notes),
            },
        }


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _hero_from_context(
    hero: Any,
    *hero_id_candidates: Any,
) -> str:
    text = str(hero or "").strip()
    if text and text.lower() not in {"?", "unknown", "none", "null"}:
        return HERO_ALIASES.get(text.lower(), HERO_ALIASES.get(text, text))
    for candidate in hero_id_candidates:
        hero_id = _safe_int(candidate)
        if hero_id in HERO_BY_ID:
            return HERO_BY_ID[hero_id]
    return text


def _is_unknown_hero(value: Any) -> bool:
    return str(value or "").strip().lower() in {"", "?", "unknown", "none", "null"}


def _dig(value: Any, *path: str, default: Any = None) -> Any:
    current = value
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _parse_quality_kv(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for part in str(text or "").split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parsed = _safe_int(value)
        if parsed is not None:
            out[key.strip()] = parsed
    return out


def _settlement_quality_truth(snapshot: dict[str, Any]) -> tuple[dict[str, int], dict[str, int]]:
    raw_counts = _parse_quality_kv(str(snapshot.get("final_quality_counts") or ""))
    if not raw_counts:
        return {}, {}
    counts = {
        "q1": (_safe_int(raw_counts.get("q1") or 0) or 0)
        + (_safe_int(raw_counts.get("q2") or 0) or 0),
        "q3": _safe_int(raw_counts.get("q3")) or 0,
        "q4": _safe_int(raw_counts.get("q4")) or 0,
        "q5": _safe_int(raw_counts.get("q5")) or 0,
        "q6": _safe_int(raw_counts.get("q6")) or 0,
    }
    raw_cells = _parse_quality_kv(str(snapshot.get("final_quality_cells") or ""))
    cells: dict[str, int] = {}
    if raw_cells:
        cells = {
            "q1": (_safe_int(raw_cells.get("q1") or 0) or 0)
            + (_safe_int(raw_cells.get("q2") or 0) or 0),
            "q3": _safe_int(raw_cells.get("q3")) or 0,
            "q4": _safe_int(raw_cells.get("q4")) or 0,
            "q5": _safe_int(raw_cells.get("q5")) or 0,
            "q6": _safe_int(raw_cells.get("q6")) or 0,
        }
    return counts, cells


def _apply_settlement_quality_truth(
    snapshot: dict[str, Any],
    *,
    fixed_counts: dict[str, int],
    min_counts: dict[str, int],
    avg_cells: dict[str, float],
    quality_cells: dict[str, float],
    source_notes: list[str],
) -> None:
    counts, cells = _settlement_quality_truth(snapshot)
    if not counts:
        return
    for key, value in counts.items():
        existing = fixed_counts.get(key)
        if existing is not None and int(existing) != int(value):
            source_notes.append("settlement_review_quality_counts_overrode_live")
        fixed_counts[key] = int(value)
        min_counts[key] = int(value)
    if cells:
        for key, value in cells.items():
            existing_cells = quality_cells.get(key)
            if existing_cells is not None and abs(float(existing_cells) - float(value)) > 0.0001:
                source_notes.append("settlement_review_quality_cells_overrode_live")
            quality_cells[key] = float(value)
            avg_cells.pop(key, None)
    source_notes.append("settlement_review_final_quality_truth")


def _append_source_note_once(source_notes: list[str], note: str) -> None:
    if note not in source_notes:
        source_notes.append(note)


def _hard_total_grid_target_from_notes(
    total_grid_target: float | None,
    source_notes: Iterable[str],
) -> int | None:
    if total_grid_target is None:
        return None
    notes = set(source_notes)
    if "public_total_avg_cells_target" in notes:
        exact_notes = {
            "structured_ref_bridge_total_cells",
            "field_update_total_cells",
            "public_total_cells",
            "action_100103_total_cells",
            "settlement_review_total_grid",
        }
        if not any(note in exact_notes for note in notes):
            return None
    rounded = int(round(float(total_grid_target)))
    if abs(float(total_grid_target) - rounded) > 0.25:
        return None
    return max(0, rounded)


def _apply_exact_count_residuals(
    *,
    total_count: int | None,
    fixed_counts: dict[str, int],
    min_counts: dict[str, int],
    count_sums: dict[str, int],
    avg_values: dict[str, float],
    quality_values: dict[str, float],
    quality_cells: dict[str, float],
    split_counts: dict[str, int],
    source_notes: list[str],
) -> None:
    def set_residual_count(
        key: str,
        residual: int,
        note: str,
        hard_conflict_note: str,
    ) -> bool:
        minimum = max(0, int(min_counts.get(key, 0)))
        if key == "q1":
            minimum = max(
                minimum,
                sum(
                    int(split_counts[split_key])
                    for split_key in LOW_SPLIT_KEYS
                    if split_counts.get(split_key) is not None
                ),
            )
        exact_cells_raw = quality_cells.get(key)
        exact_cells = None
        if exact_cells_raw is not None:
            exact_cells = int(round(float(exact_cells_raw)))
        if (
            residual < minimum
            or not _quality_count_matches_value_inputs(
                int(residual),
                avg_values.get(key),
                _safe_float(quality_values.get(key)),
            )
            or (
                exact_cells is not None
                and not can_compose_grid_total(int(residual), exact_cells)
            )
        ):
            _append_source_note_once(source_notes, f"{note}_conflict")
            _append_source_note_once(source_notes, f"hard_conflict:{hard_conflict_note}")
            return False
        fixed_counts[key] = int(residual)
        min_counts[key] = max(min_counts.get(key, 0), int(residual))
        _append_source_note_once(source_notes, note)
        return True

    for _ in range(len(QUALITY_KEYS)):
        changed = False
        for group_key, group_keys in (
            ("q4q5", ("q4", "q5")),
            ("q4q5q6", ("q4", "q5", "q6")),
        ):
            group_total = count_sums.get(group_key)
            if group_total is None:
                continue
            missing = [key for key in group_keys if fixed_counts.get(key) is None]
            known_total = sum(int(fixed_counts[key]) for key in group_keys if key not in missing)
            if len(missing) == 0:
                if known_total != int(group_total):
                    _append_source_note_once(source_notes, f"count_sum_{group_key}_conflict")
                    _append_source_note_once(source_notes, f"hard_conflict:count_sum_{group_key}")
                continue
            if len(missing) != 1:
                continue
            missing_key = missing[0]
            residual = int(group_total) - known_total
            changed = (
                set_residual_count(
                    missing_key,
                    residual,
                    f"count_sum_{group_key}_{missing_key}_count_from_residual",
                    f"count_sum_{group_key}_{missing_key}_count_residual",
                )
                or changed
            )

        if total_count is not None:
            missing = [key for key in QUALITY_KEYS if fixed_counts.get(key) is None]
            known_total = sum(
                int(fixed_counts[key]) for key in QUALITY_KEYS if key not in missing
            )
            if len(missing) == 0:
                if known_total != int(total_count):
                    _append_source_note_once(source_notes, "quality_count_total_count_conflict")
                    _append_source_note_once(source_notes, "hard_conflict:quality_count_total_count")
            elif len(missing) == 1:
                missing_key = missing[0]
                residual = int(total_count) - known_total
                changed = (
                    set_residual_count(
                        missing_key,
                        residual,
                        f"quality_count_{missing_key}_from_total_count_residual",
                        f"quality_count_{missing_key}_total_count_residual",
                    )
                    or changed
                )
        if not changed:
            break


def _apply_quality_cells_total_grid_residual(
    *,
    total_grid_target: float | None,
    fixed_counts: dict[str, int],
    avg_cells: dict[str, float],
    quality_cells: dict[str, float],
    source_notes: list[str],
) -> None:
    target = _hard_total_grid_target_from_notes(total_grid_target, source_notes)
    if target is None:
        return
    missing: list[str] = []
    known_cells: dict[str, int] = {}
    for key in QUALITY_KEYS:
        raw = quality_cells.get(key)
        if raw is None:
            missing.append(key)
            continue
        rounded = int(round(float(raw)))
        if abs(float(raw) - rounded) > 0.0001:
            return
        known_cells[key] = rounded
    if not missing:
        if sum(known_cells.values()) != target:
            _append_source_note_once(source_notes, "quality_cells_total_grid_conflict")
            _append_source_note_once(source_notes, "hard_conflict:quality_cells_total_grid")
        return
    if len(missing) != 1:
        return
    missing_key = missing[0]
    residual = target - sum(known_cells.values())
    note = f"quality_cells_{missing_key}_from_total_grid_residual"
    hard_conflict_note = f"quality_cells_{missing_key}_total_grid_residual"
    count = fixed_counts.get(missing_key)
    if residual < 0:
        _append_source_note_once(source_notes, f"{note}_conflict")
        _append_source_note_once(source_notes, f"hard_conflict:{hard_conflict_note}")
        return
    if count is not None:
        count_int = int(count)
        if not can_compose_grid_total(count_int, residual):
            _append_source_note_once(source_notes, f"{note}_conflict")
            _append_source_note_once(source_notes, f"hard_conflict:{hard_conflict_note}")
            return
        avg = avg_cells.get(missing_key)
        if not _avg_matches_exact_grid(count_int, avg, residual):
            _append_source_note_once(source_notes, f"{note}_avg_conflict")
            _append_source_note_once(source_notes, f"hard_conflict:{hard_conflict_note}")
            return
    quality_cells[missing_key] = float(residual)
    _append_source_note_once(source_notes, note)


def _parse_ranges(text: Any) -> tuple[float | None, float | None, float | None]:
    parts = [p.strip() for p in str(text or "").split("/") if p.strip()]
    parsed = [_safe_float(part) for part in parts[:3]]
    while len(parsed) < 3:
        parsed.append(None)
    return (parsed[0], parsed[1], parsed[2])


def _quality_key(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text in QUALITY_KEYS:
        return text
    if text.startswith("q") and text[1:] in QUALITY_NUM_TO_KEY:
        return QUALITY_NUM_TO_KEY[text[1:]]
    if text in QUALITY_NUM_TO_KEY:
        return QUALITY_NUM_TO_KEY[text]
    match = re.search(r"(?:bucket|quality)[._/-]?q?(?P<q>[1-6])", text)
    if match:
        return QUALITY_NUM_TO_KEY.get(match.group("q"))
    return None


def _quality_number_to_key(value: Any) -> str | None:
    parsed = _safe_int(value)
    if parsed is None:
        return _quality_key(value)
    return QUALITY_NUM_TO_KEY.get(str(parsed))


def _low_split_key(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    return LOW_SPLIT_ALIASES.get(text)


def _iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        return
    if isinstance(value, (list, tuple)):
        for row in value:
            if isinstance(row, dict):
                yield row


def _merge_quality_values(
    out: dict[str, float],
    raw: Any,
    *,
    note_prefix: str,
    source_notes: list[str],
) -> None:
    if not isinstance(raw, dict):
        return
    for raw_key, raw_value in raw.items():
        key = _quality_key(raw_key)
        value = _safe_float(raw_value)
        if key is None or value is None:
            continue
        out[key] = value
        source_notes.append(f"{note_prefix}_{key}")


def _merge_quality_counts(
    out: dict[str, int],
    raw: Any,
    *,
    note_prefix: str,
    source_notes: list[str],
) -> None:
    if not isinstance(raw, dict):
        return
    for raw_key, raw_value in raw.items():
        key = _quality_key(raw_key)
        value = _safe_int(raw_value)
        if key is None or value is None:
            continue
        out[key] = value
        source_notes.append(f"{note_prefix}_{key}")


def _merge_split_values(
    out: dict[str, float],
    raw: Any,
    *,
    note_prefix: str,
    source_notes: list[str],
) -> None:
    if not isinstance(raw, dict):
        return
    for raw_key, raw_value in raw.items():
        key = _low_split_key(raw_key)
        value = _safe_float(raw_value)
        if key is None or value is None:
            continue
        out[key] = value
        source_notes.append(f"{note_prefix}_{key}")


def _merge_split_counts(
    out: dict[str, int],
    raw: Any,
    *,
    note_prefix: str,
    source_notes: list[str],
) -> None:
    if not isinstance(raw, dict):
        return
    for raw_key, raw_value in raw.items():
        key = _low_split_key(raw_key)
        value = _safe_int(raw_value)
        if key is None or value is None:
            continue
        out[key] = value
        source_notes.append(f"{note_prefix}_{key}")


def _merge_count_sums(
    out: dict[str, int],
    raw: Any,
    *,
    note_prefix: str,
    source_notes: list[str],
) -> None:
    if not isinstance(raw, dict):
        return
    for raw_key, raw_value in raw.items():
        key = str(raw_key or "").strip().lower().replace("+", "")
        value = _safe_int(raw_value)
        if value is None:
            continue
        if key in {"q4q5", "45"}:
            out["q4q5"] = value
            source_notes.append(f"{note_prefix}_q4q5")
        elif key in {"q4q5q6", "456"}:
            out["q4q5q6"] = value
            source_notes.append(f"{note_prefix}_q4q5q6")


def _public_quality_reveal_min_counts(snapshot: dict[str, Any]) -> dict[str, int]:
    counts = {key: 0 for key in QUALITY_KEYS}
    seen: set[tuple[str, str]] = set()
    for row in _iter_dicts(snapshot.get("public_info_rows")):
        if _safe_int(row.get("info_id")) in PUBLIC_BUCKET_OUTLINE_QUALITY:
            continue
        for item in _iter_dicts(row.get("revealed_items_detail")):
            key = _quality_number_to_key(item.get("quality"))
            if key is None:
                continue
            identity = (
                str(item.get("runtime_id") or item.get("local_index") or id(item)),
                key,
            )
            if identity in seen:
                continue
            seen.add(identity)
            counts[key] += 1
    return {key: value for key, value in counts.items() if value > 0}


def _shape_cells(value: Any) -> int | None:
    parsed = _safe_int(value)
    if parsed is None:
        return None
    width = parsed // 10
    height = parsed % 10
    if width <= 0 or height <= 0:
        return None
    return width * height


def _public_bucket_outline_totals(snapshot: dict[str, Any]) -> dict[str, tuple[int, int | None]]:
    totals: dict[str, tuple[int, int | None]] = {}
    seen: set[tuple[str, str]] = set()
    for row in _iter_dicts(snapshot.get("public_info_rows")):
        key = PUBLIC_BUCKET_OUTLINE_QUALITY.get(_safe_int(row.get("info_id")) or -1)
        if key is None:
            continue
        count = 0
        cells = 0
        missing_cells = False
        for idx, item in enumerate(_iter_dicts(row.get("revealed_items_detail"))):
            item_key = _quality_number_to_key(item.get("quality")) or key
            if item_key != key:
                continue
            identity = (
                str(
                    item.get("runtime_id")
                    or item.get("local_index")
                    or item.get("item_id")
                    or f"row-{id(row)}-{idx}"
                ),
                key,
            )
            if identity in seen:
                continue
            seen.add(identity)
            count += 1
            item_cells = _safe_int(item.get("cells"))
            if item_cells is None or item_cells <= 0:
                item_cells = _shape_cells(item.get("shape_code") or item.get("shape_key"))
            if item_cells is None or item_cells <= 0:
                missing_cells = True
            else:
                cells += item_cells
        if count > 0:
            prev_count, prev_cells = totals.get(key, (0, 0))
            next_cells: int | None
            if missing_cells or prev_cells is None:
                next_cells = None
            else:
                next_cells = prev_cells + cells
            totals[key] = (prev_count + count, next_cells)
    return totals


def _random_avg_sample_count(row: dict[str, Any]) -> int | None:
    sample_count = _safe_int(row.get("sample_count"))
    if sample_count is not None:
        return sample_count
    semantic = str(row.get("semantic") or row.get("kind") or "")
    match = re.search(r"random[_-](?P<count>\d+)[_-]avg[_-]value", semantic)
    if match:
        return _safe_int(match.group("count"))
    return None


def _quality_key_from_avg_value_row(row: dict[str, Any]) -> str | None:
    quality = _quality_number_to_key(row.get("quality"))
    if quality in {"q4", "q5", "q6"}:
        return quality
    semantic = str(row.get("semantic") or "")
    return PUBLIC_AVG_VALUES.get(semantic)


def _public_quality_avg_values(public_info: dict[str, Any]) -> dict[str, float]:
    rows: list[dict[str, Any]] = []
    rows.extend(_iter_dicts(public_info.get("public_avg_values")))
    rows.extend(_iter_dicts(public_info.get("public_numeric_facts")))
    values: dict[str, float] = {}
    for row in rows:
        kind = str(row.get("kind") or "")
        semantic = str(row.get("semantic") or "")
        if kind != "avg_value" and semantic not in PUBLIC_AVG_VALUES:
            continue
        key = _quality_key_from_avg_value_row(row)
        value = _safe_float(row.get("value"))
        if key is None or value is None:
            continue
        values[key] = value
    return values


def _public_random_value_floors(public_info: dict[str, Any]) -> tuple[tuple[int, float], ...]:
    rows: list[dict[str, Any]] = []
    rows.extend(_iter_dicts(public_info.get("public_random_avg_values")))
    rows.extend(_iter_dicts(public_info.get("public_numeric_facts")))
    floors: dict[int, float] = {}
    for row in rows:
        kind = str(row.get("kind") or "")
        semantic = str(row.get("semantic") or "")
        if kind != "random_avg_value" and not re.match(
            r"random[_-]\d+[_-]avg[_-]value",
            semantic,
        ):
            continue
        sample_count = _random_avg_sample_count(row)
        avg_value = _safe_float(row.get("value"))
        if sample_count is None or sample_count <= 0 or avg_value is None or avg_value <= 0:
            continue
        floors[sample_count] = max(floors.get(sample_count, 0.0), sample_count * avg_value)
    return tuple(sorted(floors.items()))


def _candidate_structured_inputs(snapshot: dict[str, Any], ui_contract: dict[str, Any], constraints: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for value in (
        snapshot.get("structured_ref_inputs"),
        ui_contract.get("structured_ref_inputs"),
        constraints.get("structured_ref_inputs"),
        snapshot.get("hero_ref_inputs"),
        ui_contract.get("hero_ref_inputs"),
        constraints.get("hero_ref_inputs"),
        snapshot.get("aisha_ref_inputs"),
        ui_contract.get("aisha_ref_inputs"),
        constraints.get("aisha_ref_inputs"),
        snapshot.get("ahmad_ref_inputs"),
        ui_contract.get("ahmad_ref_inputs"),
        constraints.get("ahmad_ref_inputs"),
        snapshot.get("victor_ref_inputs"),
        ui_contract.get("victor_ref_inputs"),
        constraints.get("victor_ref_inputs"),
    ):
        if isinstance(value, dict):
            candidates.append(value)
    return candidates


def _path_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return tuple(part for part in re.split(r"[./]", value) if part)
    if isinstance(value, (list, tuple)):
        return tuple(str(part) for part in value)
    return ()


def _bridge_from_field_updates(
    inputs: dict[str, Any],
    *,
    fixed_counts: dict[str, int],
    min_counts: dict[str, int],
    count_sums: dict[str, int],
    avg_cells: dict[str, float],
    quality_cells: dict[str, float],
    avg_values: dict[str, float],
    quality_values: dict[str, float],
    split_counts: dict[str, int],
    split_quality_cells: dict[str, float],
    split_avg_cells: dict[str, float],
    source_notes: list[str],
) -> tuple[int | None, float | None]:
    total_count: int | None = None
    total_grid_target: float | None = None
    for row in inputs.get("field_updates") or ():
        if not isinstance(row, dict):
            continue
        path = _path_tuple(row.get("path") or row.get("field"))
        value = row.get("value")
        if len(path) >= 2 and path[0] == "session":
            if path[1] in {"total_count", "total_item_count"}:
                parsed = _safe_int(value)
                if parsed is not None:
                    total_count = parsed
                    source_notes.append("field_update_total_count")
            elif path[1] in {"total_cells", "warehouse_total_cells"}:
                parsed_float = _safe_float(value)
                if parsed_float is not None:
                    total_grid_target = parsed_float
                    source_notes.append("field_update_total_cells")
        elif len(path) >= 3 and path[0] == "bucket_group":
            parsed_count = _safe_int(value)
            group_key = str(path[1] or "").strip().lower().replace("+", "")
            if parsed_count is not None and path[2] == "count":
                if group_key in {"q4q5", "45"}:
                    count_sums["q4q5"] = parsed_count
                    source_notes.append("field_update_q4q5_count_sum")
                elif group_key in {"q4q5q6", "456"}:
                    count_sums["q4q5q6"] = parsed_count
                    source_notes.append("field_update_q4q5q6_count_sum")
        elif len(path) >= 3 and path[0] == "bucket":
            key = _quality_number_to_key(path[1])
            if key is None:
                continue
            parsed = _safe_float(value)
            if parsed is None:
                continue
            if path[2] == "avg_cells":
                avg_cells[key] = parsed
                source_notes.append(f"field_update_{key}_avg_cells")
            elif path[2] == "count":
                fixed_counts[key] = int(round(parsed))
                min_counts[key] = int(round(parsed))
                source_notes.append(f"field_update_{key}_count")
            elif path[2] in {"cells", "total_cells"}:
                quality_cells[key] = parsed
                source_notes.append(f"field_update_{key}_cells")
            elif path[2] in {"avg_value", "average_value"}:
                avg_values[key] = parsed
                source_notes.append(f"field_update_{key}_avg_value")
            elif path[2] in {"value", "value_sum", "total_value"}:
                quality_values[key] = parsed
                source_notes.append(f"field_update_{key}_value_sum")
        elif len(path) >= 3 and path[0] == "bucket_split":
            key = _low_split_key(path[1])
            if key is None:
                continue
            parsed = _safe_float(value)
            if parsed is None:
                continue
            if path[2] == "avg_cells":
                split_avg_cells[key] = parsed
                source_notes.append(f"field_update_split_{key}_avg_cells")
            elif path[2] == "count":
                split_counts[key] = int(round(parsed))
                source_notes.append(f"field_update_split_{key}_count")
            elif path[2] in {"cells", "total_cells"}:
                split_quality_cells[key] = parsed
                source_notes.append(f"field_update_split_{key}_cells")
    return total_count, total_grid_target


def _extract_structured_bridge_inputs(
    snapshot: dict[str, Any],
    ui_contract: dict[str, Any],
    constraints: dict[str, Any],
    *,
    fixed_counts: dict[str, int],
    min_counts: dict[str, int],
    count_sums: dict[str, int],
    avg_cells: dict[str, float],
    quality_cells: dict[str, float],
    avg_values: dict[str, float],
    quality_values: dict[str, float],
    split_counts: dict[str, int],
    split_quality_cells: dict[str, float],
    split_avg_cells: dict[str, float],
    source_notes: list[str],
) -> tuple[int | None, float | None]:
    total_count: int | None = None
    total_grid_target: float | None = None
    for inputs in _candidate_structured_inputs(snapshot, ui_contract, constraints):
        parsed_total = _safe_int(
            inputs.get("total_count")
            or inputs.get("total_item_count")
            or inputs.get("session_total_count")
            or inputs.get("session_total_item_count")
        )
        if parsed_total is not None:
            total_count = parsed_total
            source_notes.append("structured_ref_bridge_total_count")
        parsed_cells = _safe_float(
            inputs.get("total_cells")
            or inputs.get("total_grid")
            or inputs.get("warehouse_total_cells")
            or inputs.get("session_total_cells")
        )
        if parsed_cells is not None:
            total_grid_target = parsed_cells
            source_notes.append("structured_ref_bridge_total_cells")
        _merge_quality_values(
            avg_cells,
            inputs.get("avg_cells") or inputs.get("average_cells"),
            note_prefix="structured_ref_bridge_avg_cells",
            source_notes=source_notes,
        )
        _merge_quality_values(
            quality_cells,
            inputs.get("quality_cells") or inputs.get("cells"),
            note_prefix="structured_ref_bridge_cells",
            source_notes=source_notes,
        )
        _merge_quality_values(
            avg_values,
            inputs.get("avg_values") or inputs.get("average_values"),
            note_prefix="structured_ref_bridge_avg_value",
            source_notes=source_notes,
        )
        _merge_quality_values(
            quality_values,
            inputs.get("quality_values")
            or inputs.get("value_sums")
            or inputs.get("values"),
            note_prefix="structured_ref_bridge_value_sum",
            source_notes=source_notes,
        )
        _merge_split_values(
            split_avg_cells,
            inputs.get("split_avg_cells") or inputs.get("low_quality_avg_cells"),
            note_prefix="structured_ref_bridge_split_avg_cells",
            source_notes=source_notes,
        )
        _merge_split_values(
            split_quality_cells,
            (
                inputs.get("split_quality_cells")
                or inputs.get("split_cells")
                or inputs.get("low_quality_cells")
            ),
            note_prefix="structured_ref_bridge_split_cells",
            source_notes=source_notes,
        )
        _merge_quality_counts(
            fixed_counts,
            inputs.get("fixed_counts") or inputs.get("counts"),
            note_prefix="structured_ref_bridge_count",
            source_notes=source_notes,
        )
        _merge_split_counts(
            split_counts,
            inputs.get("split_counts") or inputs.get("low_quality_counts"),
            note_prefix="structured_ref_bridge_split_count",
            source_notes=source_notes,
        )
        _merge_quality_counts(
            min_counts,
            inputs.get("min_counts"),
            note_prefix="structured_ref_bridge_min_count",
            source_notes=source_notes,
        )
        _merge_count_sums(
            count_sums,
            inputs.get("count_sums") or inputs.get("countSums"),
            note_prefix="structured_ref_bridge_count_sum",
            source_notes=source_notes,
        )
        field_total, field_cells = _bridge_from_field_updates(
            inputs,
            fixed_counts=fixed_counts,
            min_counts=min_counts,
            count_sums=count_sums,
            avg_cells=avg_cells,
            quality_cells=quality_cells,
            avg_values=avg_values,
            quality_values=quality_values,
            split_counts=split_counts,
            split_quality_cells=split_quality_cells,
            split_avg_cells=split_avg_cells,
            source_notes=source_notes,
        )
        if field_total is not None:
            total_count = field_total
        if field_cells is not None:
            total_grid_target = field_cells
    return total_count, total_grid_target


def _parse_static_arrays(text: str, name: str) -> dict[str, list[float]]:
    anchor = f"{name} = new Dictionary"
    start = text.find(anchor)
    if start < 0:
        return {}
    end = text.find("};", start)
    if end < 0:
        return {}
    block = text[start:end]
    pattern = re.compile(
        r'\{\s*"(?P<key>[^"]+)"\s*,\s*new double\[\d+\]\s*\{(?P<values>[^}]+)\}\s*\}',
        re.MULTILINE,
    )
    result: dict[str, list[float]] = {}
    for match in pattern.finditer(block):
        values = [
            float(item.strip())
            for item in match.group("values").split(",")
            if item.strip()
        ]
        result[match.group("key")] = values
    return result


def _parse_map_nests(text: str) -> dict[int, tuple[str, str]]:
    result: dict[int, tuple[str, str]] = {}
    current_map: str | None = None
    current_name: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        map_match = re.search(r'MapId\s*=\s*"(?P<id>\d+)"', line)
        if map_match:
            current_map = map_match.group("id")
            current_name = None
            continue
        name_match = re.search(r'MapName\s*=\s*"(?P<name>[^"]*)"', line)
        if name_match and current_map is not None:
            current_name = name_match.group("name")
            continue
        nest_match = re.search(r'NestId\s*=\s*"(?P<nest>[^"]+)"', line)
        if nest_match and current_map is not None:
            result[int(current_map)] = (nest_match.group("nest"), current_name or "")
            current_map = None
            current_name = None
    return result


@lru_cache(maxsize=4)
def load_reference_static_data(path: Path = STATIC_DATA) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return {"drop_weights": {}, "nest_prices": {}, "map_nests": {}}
    return {
        "drop_weights": _parse_static_arrays(text, "DropWeights"),
        "nest_prices": _parse_static_arrays(text, "NestWeightedPrices"),
        "map_nests": _parse_map_nests(text),
    }


def _map_tier(map_id: int | None) -> str:
    if map_id is None:
        return "104"
    family = int(map_id) // 100
    if family == 21:
        return "101"
    if family == 22:
        return "102"
    if family == 23:
        return "103"
    if family == 24:
        return "104"
    if family in {25, 45}:
        return "105"
    if family == 26:
        return "106"
    return "104"


def _activity_price_alias_map_id(
    map_id: int | None,
    static_data: dict[str, Any],
) -> tuple[int | None, str]:
    if map_id is None:
        return None, ""
    map_nests: dict[int, tuple[str, str]] = static_data.get("map_nests", {})
    nest_prices: dict[str, list[float]] = static_data.get("nest_prices", {})
    current_nest_id = map_nests.get(int(map_id), ("", ""))[0]
    if current_nest_id and nest_prices.get(current_nest_id):
        return map_id, ""

    candidates: list[tuple[str, int]] = []
    if 2521 <= int(map_id) <= 2530:
        candidates.append(("activity_shipwreck_minus20", int(map_id) - 20))
        candidates.append(("activity_shipwreck_minus10", int(map_id) - 10))
    elif 4521 <= int(map_id) <= 4530:
        candidates.append(("activity_shipwreck_45xx_minus20", int(map_id) - 20))
        candidates.append(("activity_shipwreck_45xx_minus10", int(map_id) - 10))

    for mode, candidate in candidates:
        nest_id = map_nests.get(candidate, ("", ""))[0]
        prices = nest_prices.get(nest_id)
        if prices and len(prices) >= 6:
            return candidate, f"{mode}:{map_id}->{candidate}"
    return map_id, ""


def _quality_item_values(
    map_id: int | None,
    static_data: dict[str, Any],
) -> tuple[dict[str, float], str]:
    map_nests: dict[int, tuple[str, str]] = static_data.get("map_nests", {})
    nest_prices: dict[str, list[float]] = static_data.get("nest_prices", {})
    price_map_id, alias_note = _activity_price_alias_map_id(map_id, static_data)
    nest_id = map_nests.get(int(price_map_id or 0), ("", ""))[0]
    prices = nest_prices.get(nest_id)
    if not prices or len(prices) < 6:
        return dict(DEFAULT_ITEM_VALUES), "fallback_default_price"
    q1_indexes = QUALITY_TO_INDEX["q1"]
    values = {
        "q1": sum(prices[index] for index in q1_indexes) / len(q1_indexes),
        "q3": prices[2],
        "q4": prices[3],
        "q5": prices[4],
        "q6": prices[5],
    }
    note = f"nest_price:{nest_id}"
    if alias_note:
        note = f"{note};{alias_note}"
    return values, note


def _quality_probabilities(
    map_id: int | None,
    static_data: dict[str, Any],
) -> tuple[dict[str, float], str]:
    drop_weights: dict[str, list[float]] = static_data.get("drop_weights", {})
    tier = _map_tier(map_id)
    weights = drop_weights.get(tier) or drop_weights.get("104") or []
    if len(weights) < 6:
        return {key: 1.0 / len(QUALITY_KEYS) for key in QUALITY_KEYS}, "fallback_uniform_prob"
    collapsed = {
        "q1": weights[0] + weights[1],
        "q3": weights[2],
        "q4": weights[3],
        "q5": weights[4],
        "q6": weights[5],
    }
    total = sum(collapsed.values()) or 1.0
    return {key: max(1e-9, value / total) for key, value in collapsed.items()}, f"tier_prob:{tier}"


def _fit_grids_to_total_target(
    grids: dict[str, float],
    counts: dict[str, int],
    avg_cells: dict[str, float],
    target: float | None,
    fixed_grid_keys: set[str] | None = None,
) -> dict[str, float]:
    if target is None or target <= 0:
        return grids
    fixed_grid_keys = fixed_grid_keys or set()
    fixed_values = [
        grids[key]
        for key in QUALITY_KEYS
        if key in avg_cells or key in fixed_grid_keys or counts.get(key, 0) == 0
    ]
    scalable_keys = [
        key
        for key in QUALITY_KEYS
        if key not in avg_cells and key not in fixed_grid_keys and counts.get(key, 0) > 0
    ]
    target_int = int(round(target))
    if (
        scalable_keys
        and abs(float(target) - target_int) <= 0.25
        and all(abs(value - round(value)) <= 1e-6 for value in fixed_values)
    ):
        fixed_total_int = sum(int(round(value)) for value in fixed_values)
        remaining = target_int - fixed_total_int
        option_map = {
            key: tuple(
                option
                for option in _composable_grid_options(int(counts[key]))
                if option <= remaining
            )
            for key in scalable_keys
        }
        if remaining >= 0 and all(option_map.values()):
            states: dict[int, tuple[float, dict[str, int]]] = {0: (0.0, {})}
            for key in scalable_keys:
                default = grids[key]
                scale = max(1.0, abs(default))
                next_states: dict[int, tuple[float, dict[str, int]]] = {}
                for current_sum, (cost, assignment) in states.items():
                    for option in option_map[key]:
                        new_sum = current_sum + option
                        if new_sum > remaining:
                            continue
                        new_cost = cost + ((option - default) / scale) ** 2
                        existing = next_states.get(new_sum)
                        if existing is not None and existing[0] <= new_cost:
                            continue
                        next_assignment = dict(assignment)
                        next_assignment[key] = option
                        next_states[new_sum] = (new_cost, next_assignment)
                states = next_states
                if not states:
                    break
            exact = states.get(remaining)
            if exact is not None:
                fitted = dict(grids)
                for key, option in exact[1].items():
                    fitted[key] = float(option)
                return fitted

    fixed_total = sum(fixed_values)
    scalable_total = sum(grids[key] for key in scalable_keys)
    if not scalable_keys or scalable_total <= 0:
        return grids
    remaining = max(0.0, target - fixed_total)
    scale = remaining / scalable_total
    fitted = dict(grids)
    for key in scalable_keys:
        fitted[key] = max(float(counts[key]), grids[key] * scale)
    return fitted


def _apply_low_quality_split_evidence(
    *,
    total_count: int | None,
    split_counts: dict[str, int],
    split_quality_cells: dict[str, float],
    split_avg_cells: dict[str, float],
    fixed_counts: dict[str, int],
    min_counts: dict[str, int],
    avg_cells: dict[str, float],
    quality_cells: dict[str, float],
    source_notes: list[str],
) -> None:
    has_split_signal = bool(split_counts or split_quality_cells or split_avg_cells)
    if has_split_signal and fixed_counts.get("q1") is None and total_count is not None:
        other_keys = tuple(key for key in QUALITY_KEYS if key != "q1")
        if all(fixed_counts.get(key) is not None for key in other_keys):
            residual = int(total_count) - sum(int(fixed_counts[key]) for key in other_keys)
            known_split_count = sum(
                int(split_counts[key])
                for key in LOW_SPLIT_KEYS
                if split_counts.get(key) is not None
            )
            min_q1 = max(int(min_counts.get("q1", 0)), known_split_count)
            if residual < min_q1:
                source_notes.append("split_low_quality_q1_count_total_residual_conflict")
                source_notes.append("hard_conflict:split_low_quality_q1_count_total_residual")
            elif residual >= 0:
                fixed_counts["q1"] = residual
                min_counts["q1"] = max(min_counts.get("q1", 0), residual)
                source_notes.append("split_low_quality_q1_count_from_total_residual")

    if has_split_signal and fixed_counts.get("q1") is None and quality_cells.get("q1") is not None:
        derived_count = _avg_count_from_cells(avg_cells.get("q1"), quality_cells.get("q1"))
        if derived_count is not None:
            fixed_counts["q1"] = derived_count
            min_counts["q1"] = max(min_counts.get("q1", 0), derived_count)
            source_notes.append("split_low_quality_q1_count_from_avg_cells")

    if has_split_signal and quality_cells.get("q1") is None and fixed_counts.get("q1") is not None:
        options = _avg_grid_options(int(fixed_counts["q1"]), avg_cells.get("q1"))
        if len(options) == 1:
            quality_cells["q1"] = float(options[0])
            source_notes.append("split_low_quality_q1_cells_from_avg_count")

    if has_split_signal and fixed_counts.get("q1") is not None:
        missing_counts = [
            key for key in LOW_SPLIT_KEYS if split_counts.get(key) is None
        ]
        known_counts = [
            int(split_counts[key])
            for key in LOW_SPLIT_KEYS
            if split_counts.get(key) is not None
        ]
        if len(missing_counts) == 1 and len(known_counts) == 1:
            missing = int(fixed_counts["q1"]) - known_counts[0]
            if missing < 0:
                source_notes.append("split_low_quality_q1_count_complement_conflict")
                source_notes.append("hard_conflict:split_low_quality_q1_count_complement")
            else:
                split_counts[missing_counts[0]] = missing
                source_notes.append(f"split_low_quality_{missing_counts[0]}_count_from_q1_exact")

    if has_split_signal and quality_cells.get("q1") is not None:
        missing_cells = [
            key for key in LOW_SPLIT_KEYS if split_quality_cells.get(key) is None
        ]
        known_cells = [
            float(split_quality_cells[key])
            for key in LOW_SPLIT_KEYS
            if split_quality_cells.get(key) is not None
        ]
        if len(missing_cells) == 1 and len(known_cells) == 1:
            missing = float(quality_cells["q1"]) - known_cells[0]
            if missing < -0.0001:
                source_notes.append("split_low_quality_q1_cells_complement_conflict")
                source_notes.append("hard_conflict:split_low_quality_q1_cells_complement")
            else:
                split_quality_cells[missing_cells[0]] = max(0.0, missing)
                source_notes.append(f"split_low_quality_{missing_cells[0]}_cells_from_q1_exact")

    for split_key in LOW_SPLIT_KEYS:
        count = split_counts.get(split_key)
        cells = split_quality_cells.get(split_key)
        avg = split_avg_cells.get(split_key)
        if avg == 0 and count is None:
            split_counts[split_key] = 0
            count = 0
            source_notes.append(f"split_low_quality_{split_key}_zero_avg_count_zero")
        if count is None and avg is not None and cells is not None:
            derived_count = _avg_count_from_cells(avg, cells)
            if derived_count is None:
                source_notes.append(f"split_low_quality_{split_key}_avg_cells_conflict")
                source_notes.append(f"hard_conflict:split_low_quality_{split_key}_avg_cells")
            else:
                split_counts[split_key] = derived_count
                count = derived_count
                source_notes.append(f"split_low_quality_{split_key}_count_derived")
        if cells is None and count is not None and avg is not None:
            options = _avg_grid_options(int(count), avg)
            if len(options) == 1:
                split_quality_cells[split_key] = float(options[0])
                cells = float(options[0])
                source_notes.append(f"split_low_quality_{split_key}_cells_derived")
            elif not options:
                source_notes.append(f"split_low_quality_{split_key}_avg_count_conflict")
                source_notes.append(f"hard_conflict:split_low_quality_{split_key}_avg_count")
        if avg is None and count is not None and cells is not None:
            if not can_compose_grid_total(int(count), int(round(float(cells)))):
                source_notes.append(f"split_low_quality_{split_key}_count_cells_conflict")
                source_notes.append(f"hard_conflict:split_low_quality_{split_key}_count_cells")
                continue
            if int(count) == 0:
                if abs(float(cells)) > 0.0001:
                    source_notes.append(f"split_low_quality_{split_key}_count_cells_conflict")
                    source_notes.append(f"hard_conflict:split_low_quality_{split_key}_count_cells")
                else:
                    split_avg_cells[split_key] = 0.0
                    source_notes.append(f"split_low_quality_{split_key}_avg_derived")
            else:
                split_avg_cells[split_key] = float(cells) / float(count)
                source_notes.append(f"split_low_quality_{split_key}_avg_derived")
        elif avg is not None and count is not None and cells is not None:
            cells_int = int(round(float(cells)))
            if not can_compose_grid_total(int(count), cells_int) or not _avg_matches_exact_grid(
                int(count),
                avg,
                cells_int,
            ):
                source_notes.append(f"split_low_quality_{split_key}_avg_count_cells_conflict")
                source_notes.append(f"hard_conflict:split_low_quality_{split_key}_avg_count_cells")

    known_count_sum = sum(
        int(split_counts[key])
        for key in LOW_SPLIT_KEYS
        if split_counts.get(key) is not None
    )
    if known_count_sum > 0:
        min_counts["q1"] = max(min_counts.get("q1", 0), known_count_sum)
        source_notes.append("split_low_quality_q1_min_count")
    if _split_low_quality_q1_grid_extra_from_maps(split_counts, split_quality_cells) > 0:
        source_notes.append("split_low_quality_q1_grid_floor")

    have_all_counts = all(split_counts.get(key) is not None for key in LOW_SPLIT_KEYS)
    have_all_cells = all(split_quality_cells.get(key) is not None for key in LOW_SPLIT_KEYS)
    if have_all_counts:
        merged_count = sum(int(split_counts[key]) for key in LOW_SPLIT_KEYS)
        existing_count = fixed_counts.get("q1")
        if existing_count is not None and int(existing_count) != merged_count:
            source_notes.append("split_low_quality_q1_count_conflict")
            source_notes.append("hard_conflict:split_low_quality_q1_count")
        else:
            fixed_counts["q1"] = merged_count
            min_counts["q1"] = max(min_counts.get("q1", 0), merged_count)
            source_notes.append("split_low_quality_q1_count_merged")
    if have_all_cells:
        merged_cells = sum(float(split_quality_cells[key]) for key in LOW_SPLIT_KEYS)
        existing_cells = quality_cells.get("q1")
        if existing_cells is not None and abs(float(existing_cells) - merged_cells) > 0.0001:
            source_notes.append("split_low_quality_q1_cells_conflict")
            source_notes.append("hard_conflict:split_low_quality_q1_cells")
        else:
            quality_cells["q1"] = merged_cells
            source_notes.append("split_low_quality_q1_cells_merged")
    if fixed_counts.get("q1") is not None and quality_cells.get("q1") is not None and "q1" not in avg_cells:
        count = int(fixed_counts["q1"])
        cells = float(quality_cells["q1"])
        if count > 0:
            avg_cells["q1"] = cells / count
            source_notes.append("split_low_quality_q1_avg_derived")
        elif abs(cells) <= 0.0001:
            avg_cells["q1"] = 0.0
            source_notes.append("split_low_quality_q1_avg_derived")


def extract_evidence(snapshot: dict[str, Any]) -> RefEvidence:
    uc = snapshot.get("ui_contract") if isinstance(snapshot.get("ui_contract"), dict) else {}
    context = uc.get("context") if isinstance(uc.get("context"), dict) else {}
    baseline = uc.get("baseline") if isinstance(uc.get("baseline"), dict) else {}
    decision = baseline.get("decision") if isinstance(baseline.get("decision"), dict) else {}
    posterior = baseline.get("posterior") if isinstance(baseline.get("posterior"), dict) else {}
    constraints = uc.get("constraints") if isinstance(uc.get("constraints"), dict) else {}
    counts = constraints.get("counts") if isinstance(constraints.get("counts"), dict) else {}
    summary = constraints.get("summary") if isinstance(constraints.get("summary"), dict) else {}
    public_info = constraints.get("public_info") if isinstance(constraints.get("public_info"), dict) else {}
    actions = uc.get("actions") if isinstance(uc.get("actions"), dict) else {}
    truth = uc.get("truth") if isinstance(uc.get("truth"), dict) else {}
    source_notes: list[str] = []

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
        for candidate in _candidate_structured_inputs(snapshot, uc, constraints):
            structured_hero = _hero_from_context(candidate.get("hero"))
            if not _is_unknown_hero(structured_hero):
                hero = structured_hero
                source_notes.append("structured_hero")
                break
    map_id = _safe_int(context.get("map_id") or snapshot.get("map_id"))
    phase = str(context.get("phase") or snapshot.get("phase") or "")
    fixed_counts: dict[str, int] = {}
    min_counts: dict[str, int] = {}
    count_sums: dict[str, int] = {}
    avg_cells: dict[str, float] = {}
    quality_cells: dict[str, float] = {}
    avg_values: dict[str, float] = {}
    quality_values: dict[str, float] = {}
    split_counts: dict[str, int] = {}
    split_quality_cells: dict[str, float] = {}
    split_avg_cells: dict[str, float] = {}
    random_value_floors: tuple[tuple[int, float], ...] = ()

    bridge_total_count, bridge_total_cells = _extract_structured_bridge_inputs(
        snapshot,
        uc,
        constraints,
        fixed_counts=fixed_counts,
        min_counts=min_counts,
        count_sums=count_sums,
        avg_cells=avg_cells,
        quality_cells=quality_cells,
        avg_values=avg_values,
        quality_values=quality_values,
        split_counts=split_counts,
        split_quality_cells=split_quality_cells,
        split_avg_cells=split_avg_cells,
        source_notes=source_notes,
    )

    total_count = bridge_total_count
    if total_count is None:
        total_count = _safe_int(summary.get("input_total_item_count"))
    if total_count is None:
        total_count = _safe_int(counts.get("input_total_item_count"))

    def set_total_count(value: Any, note: str) -> None:
        nonlocal total_count
        parsed = _safe_int(value)
        if parsed is None:
            return
        if total_count is not None and int(total_count) != int(parsed):
            source_notes.append(f"{note}_conflicts_total_count:{total_count}->{parsed}")
        total_count = int(parsed)
        source_notes.append(note)

    settlement_total_count = _safe_int(truth.get("total_items"))
    if phase == "settled" and settlement_total_count is not None:
        if total_count is not None and int(total_count) != int(settlement_total_count):
            source_notes.append("settlement_review_total_count_overrode_bridge")
        total_count = settlement_total_count
        if "settlement_review_total_count" not in source_notes:
            source_notes.append("settlement_review_total_count")

    total_grid_target = bridge_total_cells
    if total_grid_target is None:
        total_grid_target = _safe_float(summary.get("input_warehouse_total_cells"))
    if total_grid_target is None:
        total_grid_target = _safe_float(counts.get("input_warehouse_total_cells"))

    def set_total_grid_target(value: Any, note: str) -> None:
        nonlocal total_grid_target
        parsed = _safe_float(value)
        if parsed is None:
            return
        if (
            total_grid_target is not None
            and abs(float(total_grid_target) - float(parsed)) > 0.0001
        ):
            source_notes.append(f"{note}_conflicts_total_grid:{total_grid_target}->{parsed}")
        total_grid_target = float(parsed)
        source_notes.append(note)

    if total_grid_target is None:
        public_constraints = public_info.get("input_constraints")
        if isinstance(public_constraints, dict):
            set_total_grid_target(
                public_constraints.get("total_cells")
                or public_constraints.get("warehouse_total_cells"),
                "public_total_cells",
            )
    settlement_total_cells = _safe_float(truth.get("total_cells"))
    if phase == "settled" and settlement_total_cells is not None:
        if (
            total_grid_target is not None
            and abs(float(total_grid_target) - float(settlement_total_cells)) > 0.0001
        ):
            source_notes.append("settlement_review_total_grid_overrode_bridge")
        total_grid_target = settlement_total_cells
        if "settlement_review_total_grid" not in source_notes:
            source_notes.append("settlement_review_total_grid")

    known_quality_counts: dict[str, int] = {}
    known_quality_source = ""
    if phase == "settled":
        known_quality_counts.update(_parse_quality_kv(str(snapshot.get("final_quality_counts") or "")))
        known_quality_source = "settlement"
    if not known_quality_counts:
        raw_known = counts.get("known_quality_counts")
        known_quality_source = "constraints"
        if isinstance(raw_known, dict):
            known_quality_counts.update(
                {str(k): int(v) for k, v in raw_known.items() if _safe_int(v) is not None}
            )
    q1_combined = (
        _safe_int(known_quality_counts.get("q1") or 0) or 0
    ) + (_safe_int(known_quality_counts.get("q2") or 0) or 0)
    quality_counts = {
        "q1": q1_combined,
        "q3": _safe_int(known_quality_counts.get("q3")) or 0,
        "q4": _safe_int(known_quality_counts.get("q4")) or 0,
        "q5": _safe_int(known_quality_counts.get("q5")) or 0,
        "q6": _safe_int(known_quality_counts.get("q6")) or 0,
    }
    if phase == "settled":
        known_quality_cells = _parse_quality_kv(str(snapshot.get("final_quality_cells") or ""))
        q1_cells_combined = (
            _safe_int(known_quality_cells.get("q1") or 0) or 0
        ) + (_safe_int(known_quality_cells.get("q2") or 0) or 0)
        for key, value in {
            "q1": q1_cells_combined,
            "q3": _safe_int(known_quality_cells.get("q3")) or 0,
            "q4": _safe_int(known_quality_cells.get("q4")) or 0,
            "q5": _safe_int(known_quality_cells.get("q5")) or 0,
            "q6": _safe_int(known_quality_cells.get("q6")) or 0,
        }.items():
            if value > 0:
                quality_cells[key] = float(value)
                avg_cells.pop(key, None)

    if known_quality_source == "settlement":
        for key in QUALITY_KEYS:
            fixed_counts.pop(key, None)
            min_counts.pop(key, None)

    for key, value in quality_counts.items():
        if value > 0:
            min_counts.setdefault(key, value)
    if total_count is not None and sum(quality_counts.values()) == total_count:
        fixed_counts.update(
            {
                key: value
                for key, value in quality_counts.items()
                if key not in fixed_counts
            }
        )
        if phase == "settled" or known_quality_source == "settlement":
            source_notes.append("settlement_review_known_quality_counts_sum_to_total")
        else:
            source_notes.append("known_quality_counts_sum_to_total")
    elif phase == "settled" and total_count is not None:
        fixed_counts.update(
            {
                key: value
                for key, value in quality_counts.items()
                if key not in fixed_counts
            }
        )
        source_notes.append("settlement_review_fixed_counts")

    if phase != "settled":
        public_quality_counts = _public_quality_reveal_min_counts(snapshot)
        if public_quality_counts:
            for key, value in public_quality_counts.items():
                min_counts[key] = max(min_counts.get(key, 0), value)
            source_notes.append("public_quality_reveal_min_counts")
        public_outline_totals = _public_bucket_outline_totals(snapshot)
        for key, (count, cells) in public_outline_totals.items():
            existing_count = fixed_counts.get(key)
            if existing_count is not None and int(existing_count) != int(count):
                source_notes.append(f"public_bucket_outline_{key}_count_conflict")
                continue
            fixed_counts[key] = count
            min_counts[key] = max(min_counts.get(key, 0), count)
            source_notes.append(f"public_bucket_outline_{key}_count")
            if cells is None:
                continue
            existing_cells = quality_cells.get(key)
            if existing_cells is not None and abs(float(existing_cells) - float(cells)) > 0.0001:
                source_notes.append(f"public_bucket_outline_{key}_cells_conflict")
                continue
            quality_cells[key] = float(cells)
            source_notes.append(f"public_bucket_outline_{key}_cells")

    for row in actions.get("results") or ():
        if not isinstance(row, dict):
            continue
        action_id = str(row.get("action_id") or "")
        diagnostic_semantic = ACTION_DIAGNOSTIC_ONLY.get(action_id)
        if diagnostic_semantic is not None:
            source_notes.append(f"action_{action_id}_{diagnostic_semantic}_diagnostic_only")
            revealed_count = _safe_int(row.get("revealed_items"))
            if revealed_count is not None and revealed_count > 0:
                source_notes.append(f"action_{action_id}_revealed_items:{revealed_count}")
        value = _safe_float(row.get("result"))
        if value is None:
            continue
        note_suffix = "_inferred_zero" if row.get("inferred_zero") else ""
        quality_for_avg = ACTION_AVG_CELLS.get(action_id)
        quality_for_cells = ACTION_TOTAL_CELLS.get(action_id)
        quality_for_value = ACTION_VALUE_SUM.get(action_id)
        quality_for_count = ACTION_COUNTS.get(action_id)
        if quality_for_avg is not None:
            avg_cells[quality_for_avg] = value
            source_notes.append(f"action_{action_id}_{quality_for_avg}_avg_cells{note_suffix}")
        elif quality_for_cells is not None:
            quality_cells[quality_for_cells] = value
            source_notes.append(f"action_{action_id}_{quality_for_cells}_cells{note_suffix}")
        elif quality_for_value is not None:
            quality_values[quality_for_value] = value
            source_notes.append(f"action_{action_id}_{quality_for_value}_value_sum{note_suffix}")
        elif quality_for_count is not None:
            fixed_counts[quality_for_count] = int(round(value))
            min_counts[quality_for_count] = int(round(value))
            source_notes.append(f"action_{action_id}_{quality_for_count}_count{note_suffix}")
        elif action_id in {"100115", "100204"}:
            set_total_count(value, f"action_{action_id}_total_count")
        elif action_id == "100103":
            set_total_grid_target(value, "action_100103_total_cells")

    for row in public_info.get("public_numeric_facts") or ():
        if not isinstance(row, dict):
            continue
        semantic = str(row.get("semantic") or "")
        value = _safe_float(row.get("value"))
        if value is None:
            continue
        if semantic == "total_item_count":
            set_total_count(value, "public_total_item_count")
        elif semantic == "total_cells":
            set_total_grid_target(value, "public_total_cells")
        elif semantic == "total_avg_cells" and total_count is not None:
            set_total_grid_target(value * total_count, "public_total_avg_cells_target")
        elif semantic == "total_avg_value":
            source_notes.append("public_total_avg_value_diagnostic_only")
        elif semantic in PUBLIC_AVG_CELLS:
            avg_cells[PUBLIC_AVG_CELLS[semantic]] = value
            source_notes.append(f"public_{PUBLIC_AVG_CELLS[semantic]}_avg_cells")
        elif semantic in PUBLIC_COUNTS:
            key = PUBLIC_COUNTS[semantic]
            fixed_counts[key] = int(round(value))
            min_counts[key] = int(round(value))
            source_notes.append(f"public_{key}_count")

    for key, value in _public_quality_avg_values(public_info).items():
        avg_values[key] = value
        source_notes.append(f"public_{key}_avg_value")

    if phase != "settled":
        random_value_floors = _public_random_value_floors(public_info)
        for sample_count, value_floor in random_value_floors:
            source_notes.append(
                f"public_random_avg_value_floor_{sample_count}:{int(round(value_floor))}"
            )

    if phase == "settled":
        _apply_settlement_quality_truth(
            snapshot,
            fixed_counts=fixed_counts,
            min_counts=min_counts,
            avg_cells=avg_cells,
            quality_cells=quality_cells,
            source_notes=source_notes,
        )

    _apply_exact_count_residuals(
        total_count=total_count,
        fixed_counts=fixed_counts,
        min_counts=min_counts,
        count_sums=count_sums,
        avg_values=avg_values,
        quality_values=quality_values,
        quality_cells=quality_cells,
        split_counts=split_counts,
        source_notes=source_notes,
    )
    _apply_quality_cells_total_grid_residual(
        total_grid_target=total_grid_target,
        fixed_counts=fixed_counts,
        avg_cells=avg_cells,
        quality_cells=quality_cells,
        source_notes=source_notes,
    )

    _apply_low_quality_split_evidence(
        total_count=total_count,
        split_counts=split_counts,
        split_quality_cells=split_quality_cells,
        split_avg_cells=split_avg_cells,
        fixed_counts=fixed_counts,
        min_counts=min_counts,
        avg_cells=avg_cells,
        quality_cells=quality_cells,
        source_notes=source_notes,
    )

    for key, avg in tuple(avg_cells.items()):
        if avg == 0 and key not in fixed_counts:
            fixed_counts[key] = 0
            min_counts[key] = 0
            source_notes.append(f"zero_avg_cells_{key}_count_zero")

    for key, avg in tuple(avg_values.items()):
        avg_fraction = _avg_value_fraction(avg)
        if avg_fraction == 0 and key not in fixed_counts:
            fixed_counts[key] = 0
            min_counts[key] = 0
            source_notes.append(f"zero_avg_value_{key}_count_zero")

    for key, value in tuple(quality_values.items()):
        if key in avg_values:
            continue
        count = fixed_counts.get(key)
        parsed_value = _safe_float(value)
        if count is None or parsed_value is None or parsed_value < 0:
            continue
        count_int = int(count)
        if count_int > 0:
            avg_values[key] = float(parsed_value) / float(count_int)
            source_notes.append(f"quality_value_{key}_avg_value_derived")
        elif abs(parsed_value) <= 0.0001:
            avg_values[key] = 0.0
            source_notes.append(f"quality_value_{key}_avg_value_derived")

    for key, avg in tuple(avg_values.items()):
        quality_value = quality_values.get(key)
        fixed_count = fixed_counts.get(key)
        if fixed_count is not None:
            if not _quality_count_matches_value_inputs(
                int(fixed_count),
                avg,
                _safe_float(quality_value),
            ):
                source_notes.append(f"quality_value_{key}_avg_count_conflict")
            continue
        if quality_value is None:
            continue
        derived_count = _avg_value_count_from_total(avg, quality_value)
        if derived_count is None:
            source_notes.append(f"quality_value_{key}_avg_value_conflict")
            continue
        fixed_counts[key] = derived_count
        min_counts[key] = derived_count
        source_notes.append(f"quality_value_{key}_count_derived")

    for key, cells in quality_cells.items():
        if key in avg_cells:
            continue
        count = fixed_counts.get(key)
        if count is not None and count > 0 and cells >= 0:
            avg_cells[key] = float(cells) / float(count)
            source_notes.append(f"quality_cells_{key}_avg_derived")

    for key, avg in tuple(avg_cells.items()):
        if key in fixed_counts or avg is None:
            continue
        cells = quality_cells.get(key)
        derived_count = _avg_count_from_cells(avg, cells)
        if derived_count is None:
            continue
        fixed_counts[key] = derived_count
        min_counts[key] = derived_count
        source_notes.append(f"quality_cells_{key}_count_derived")

    for key, avg in tuple(avg_cells.items()):
        cells = quality_cells.get(key)
        if cells is None:
            continue
        cells_int = int(round(float(cells)))
        fixed_count = fixed_counts.get(key)
        if fixed_count is not None:
            if not _avg_matches_exact_grid(int(fixed_count), avg, cells_int):
                source_notes.append(f"quality_cells_{key}_avg_count_conflict")
        elif _avg_count_from_cells(avg, cells) is None:
            source_notes.append(f"quality_cells_{key}_avg_cells_conflict")

    return RefEvidence(
        hero=hero,
        map_id=map_id,
        phase=phase,
        total_count=total_count,
        fixed_counts=fixed_counts,
        min_counts=min_counts,
        count_sums=count_sums,
        avg_cells=avg_cells,
        quality_cells=quality_cells,
        avg_values=avg_values,
        quality_values=quality_values,
        split_counts=split_counts,
        split_quality_cells=split_quality_cells,
        split_avg_cells=split_avg_cells,
        random_value_floors=random_value_floors,
        total_grid_target=total_grid_target,
        v3_conservative=str(decision.get("defend_bid") or ""),
        v3_balanced=str(decision.get("attack_bid") or ""),
        v3_aggressive=str(decision.get("stop_price") or ""),
        source_notes=tuple(dict.fromkeys(source_notes)),
    )


def can_compose_grid_total(count: int, grid: int) -> bool:
    if count == 0:
        return grid == 0
    if count < 0 or grid < count or grid > 18 * count:
        return False
    valid_sizes = (1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18)
    reachable = {0}
    for _ in range(count):
        reachable = {
            current + size
            for current in reachable
            for size in valid_sizes
            if current + size <= grid
        }
        if not reachable:
            return False
    return grid in reachable


@lru_cache(maxsize=4096)
def _composable_grid_options(count: int) -> tuple[int, ...]:
    if count < 0:
        return ()
    if count == 0:
        return (0,)
    return tuple(
        grid
        for grid in range(count, 18 * count + 1)
        if can_compose_grid_total(count, grid)
    )


def _avg_grid_options(count: int, avg: float | None) -> list[int]:
    if count < 0:
        return []
    if count == 0:
        return [0] if avg in (None, 0) else []
    low = count
    high = 18 * count
    if avg is None:
        return list(range(low, high + 1))
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


def _avg_count_from_cells(avg: float | None, cells: Any) -> int | None:
    if avg is None or cells in (None, ""):
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


def _avg_matches_exact_grid(count: int, avg: float | None, grid: int) -> bool:
    if avg is None:
        return True
    if count <= 0:
        return grid == 0 and abs(float(avg)) <= 0.0001
    return abs(float(avg) * count - grid) <= 0.0001


def _avg_value_fraction(avg: float | None) -> Fraction | None:
    if avg is None:
        return None
    value = float(avg)
    if not math.isfinite(value) or value < 0:
        return None
    return Fraction(value).limit_denominator(60)


def _avg_value_has_positive_signal(avg: float | None) -> bool:
    fraction = _avg_value_fraction(avg)
    return fraction is not None and fraction > 0


def _avg_value_count_matches(count: int, avg: float | None) -> bool:
    fraction = _avg_value_fraction(avg)
    if fraction is None:
        return True
    if fraction == 0:
        return count == 0
    if count <= 0:
        return False
    return (fraction.numerator * int(count)) % fraction.denominator == 0


def _avg_value_total_from_count(avg: float, count: int) -> float | None:
    fraction = _avg_value_fraction(avg)
    if fraction is None:
        return None
    return float(fraction * int(count))


def _avg_value_count_from_total(avg: float | None, total_value: Any) -> int | None:
    fraction = _avg_value_fraction(avg)
    value = _safe_float(total_value)
    if fraction is None or value is None or value < 0:
        return None
    total_fraction = Fraction(float(value)).limit_denominator(100)
    if fraction == 0:
        return 0 if total_fraction == 0 else None
    if total_fraction <= 0:
        return None
    count_fraction = total_fraction / fraction
    if count_fraction.denominator != 1 or count_fraction < 0:
        return None
    return int(count_fraction)


def _choose_avg_grid_option(
    count: int,
    avg: float | None,
    options: list[int],
) -> float | None:
    if not options:
        return None
    if count <= 0:
        return 0.0
    if avg is None:
        return float(options[len(options) // 2])
    target = avg * count
    return float(min(options, key=lambda grid: (abs(grid - target), grid)))


def _log_fact(n: int) -> float:
    return math.lgamma(n + 1)


def _weighted_quantile(rows: list[tuple[float, float]], q: float) -> float | None:
    if not rows:
        return None
    rows = sorted(rows)
    total = sum(weight for _, weight in rows)
    if total <= 0:
        return rows[len(rows) // 2][0]
    threshold = total * q
    cumulative = 0.0
    for value, weight in rows:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return rows[-1][0]


def _count_values(
    total_count: int,
    key: str,
    evidence: RefEvidence,
    reserve: int,
) -> list[int]:
    fixed = evidence.fixed_counts.get(key)
    if fixed is not None:
        fixed_int = int(fixed)
        if not _quality_count_matches_value_evidence(key, fixed_int, evidence):
            return []
        return [fixed_int]
    minimum = _effective_min_count(key, evidence)
    maximum = total_count - reserve
    if maximum < minimum:
        return []
    return [
        value
        for value in range(minimum, maximum + 1)
        if _quality_count_matches_value_evidence(key, value, evidence)
    ]


def _effective_min_count(key: str, evidence: RefEvidence) -> int:
    minimum = max(0, int(evidence.min_counts.get(key, 0)))
    if key == "q1":
        minimum = max(minimum, _split_low_quality_q1_count_floor(evidence))
    exact_cells = _quality_exact_cells(key, evidence)
    if exact_cells is not None and exact_cells > 0:
        minimum = max(minimum, int(math.ceil(exact_cells / 18.0)), 1)
    exact_value = _quality_exact_value(key, evidence)
    if exact_value is not None and exact_value > 0:
        minimum = max(minimum, 1)
    if (
        evidence.phase != "settled"
        and evidence.fixed_counts.get(key) is None
        and evidence.avg_cells.get(key) is not None
        and (evidence.avg_cells.get(key) or 0.0) > 0
    ):
        minimum = max(minimum, 1)
    if (
        evidence.phase != "settled"
        and evidence.fixed_counts.get(key) is None
        and evidence.avg_values.get(key) is not None
        and _avg_value_has_positive_signal(evidence.avg_values.get(key))
    ):
        minimum = max(minimum, 1)
    return minimum


def _quality_exact_cells(key: str, evidence: RefEvidence) -> int | None:
    value = evidence.quality_cells.get(key)
    if value is None:
        return None
    parsed = int(round(float(value)))
    return max(0, parsed)


def _quality_exact_value(key: str, evidence: RefEvidence) -> float | None:
    value = evidence.quality_values.get(key)
    if value is None:
        return None
    parsed = _safe_float(value)
    if parsed is None or parsed < 0:
        return None
    return parsed


def _quality_count_matches_value_inputs(
    count: int,
    avg: float | None,
    exact_value: float | None,
) -> bool:
    if not _avg_value_count_matches(count, avg):
        return False
    if exact_value is None:
        return True
    if count <= 0:
        return abs(float(exact_value)) <= 0.0001
    if avg is None:
        return exact_value > 0
    derived_total = _avg_value_total_from_count(float(avg), count)
    if derived_total is None:
        return False
    return abs(float(exact_value) - derived_total) <= 0.5


def _quality_count_matches_value_evidence(
    key: str,
    count: int,
    evidence: RefEvidence,
) -> bool:
    return _quality_count_matches_value_inputs(
        count,
        evidence.avg_values.get(key),
        _quality_exact_value(key, evidence),
    )


def _hard_total_grid_target_int(evidence: RefEvidence) -> int | None:
    return _hard_total_grid_target_from_notes(
        evidence.total_grid_target,
        evidence.source_notes,
    )


def _split_low_quality_q1_floor_parts_from_maps(
    split_counts: dict[str, int],
    split_quality_cells: dict[str, float],
) -> tuple[int, int, int]:
    count_floor = 0
    exact_count_for_cells = 0
    exact_cells = 0
    for split_key in LOW_SPLIT_KEYS:
        raw_count = split_counts.get(split_key)
        raw_cells = split_quality_cells.get(split_key)
        count = max(0, int(raw_count)) if raw_count is not None else None
        cells = None
        if raw_cells is not None:
            cells = max(0, int(round(float(raw_cells))))

        if count is not None:
            count_floor += count
        elif cells is not None and cells > 0:
            count_floor += max(1, int(math.ceil(cells / 18.0)))

        if cells is None:
            continue
        if count is None:
            count_for_cells = 0 if cells == 0 else max(1, int(math.ceil(cells / 18.0)))
        else:
            count_for_cells = count
        exact_count_for_cells += count_for_cells
        exact_cells += cells
    return count_floor, exact_count_for_cells, exact_cells


def _split_low_quality_q1_grid_extra_from_maps(
    split_counts: dict[str, int],
    split_quality_cells: dict[str, float],
) -> int:
    _count_floor, exact_count_for_cells, exact_cells = _split_low_quality_q1_floor_parts_from_maps(
        split_counts,
        split_quality_cells,
    )
    return max(0, exact_cells - exact_count_for_cells)


def _split_low_quality_q1_count_floor(evidence: RefEvidence) -> int:
    count_floor, _exact_count_for_cells, _exact_cells = _split_low_quality_q1_floor_parts_from_maps(
        evidence.split_counts,
        evidence.split_quality_cells,
    )
    return count_floor


def _split_low_quality_q1_grid_floor(count: int, evidence: RefEvidence) -> int:
    if count <= 0:
        return 0
    return int(count) + _split_low_quality_q1_grid_extra_from_maps(
        evidence.split_counts,
        evidence.split_quality_cells,
    )


def _split_low_quality_q1_grid_matches(
    count: int,
    grid: float,
    evidence: RefEvidence,
) -> bool:
    floor = _split_low_quality_q1_grid_floor(count, evidence)
    return float(grid) + 1e-6 >= float(floor)


def _default_total_count(map_id: int | None) -> int:
    if map_id is None:
        return 28
    family = int(map_id) // 100
    if family in {21, 22}:
        return 24
    if family == 23:
        return 27
    if family in {25, 45}:
        return 33
    if family == 24:
        return 28
    if family == 26:
        return 33
    return 28


def _known_count_floor(evidence: RefEvidence) -> int:
    fixed_total = sum(max(0, int(value)) for value in evidence.fixed_counts.values())
    min_total = sum(_effective_min_count(key, evidence) for key in QUALITY_KEYS)
    for group_key, keys in (
        ("q4q5", ("q4", "q5")),
        ("q4q5q6", ("q4", "q5", "q6")),
    ):
        group_total = evidence.count_sums.get(group_key)
        if group_total is None:
            continue
        fixed_group = sum(max(0, int(evidence.fixed_counts.get(key, 0))) for key in keys)
        min_total = max(min_total, max(0, int(group_total)) + fixed_total - fixed_group)
    return max(fixed_total, min_total)


def _should_use_sparse_exact_total_prior(evidence: RefEvidence) -> bool:
    if evidence.total_count is None or evidence.phase == "settled":
        return False
    if evidence.count_sums or evidence.quality_cells:
        return False
    nonzero_fixed_count = sum(1 for value in evidence.fixed_counts.values() if int(value) > 0)
    if nonzero_fixed_count > 1:
        return False
    if nonzero_fixed_count == 1 and len(evidence.avg_cells) > 2:
        return False
    # Exact total count alone still leaves the count split underdetermined. Use the
    # probability prior sampler instead of full nested enumeration so live/manual
    # sparse states stay responsive without relying on max_combos truncation order.
    return True


def _total_count_candidates(evidence: RefEvidence, notes: list[str]) -> tuple[list[int], int | None]:
    if evidence.total_count is not None:
        total_count = int(evidence.total_count)
        fixed_total = sum(max(0, int(value)) for value in evidence.fixed_counts.values())
        if evidence.phase == "manual" and fixed_total != total_count:
            notes.append("manual_total_count_prior_enumeration")
            return [total_count], total_count
        if _should_use_sparse_exact_total_prior(evidence):
            notes.append("sparse_exact_total_prior_enumeration")
            return [total_count], total_count
        return [total_count], None
    has_live_input = bool(
        evidence.source_notes
        or evidence.fixed_counts
        or evidence.min_counts
        or evidence.count_sums
        or evidence.avg_cells
        or evidence.avg_values
        or evidence.quality_values
        or evidence.total_grid_target
    )
    if not has_live_input:
        return [], None
    center = max(_default_total_count(evidence.map_id), _known_count_floor(evidence))
    if evidence.total_grid_target is not None and evidence.total_grid_target > 0:
        center = max(center, int(round(evidence.total_grid_target / 3.0)), 1)
    lower = max(_known_count_floor(evidence), center - 4, 1)
    upper = max(lower, center + 4)
    upper = min(60, upper)
    notes.append("total_count_from_ref_count_prior")
    notes.append(f"total_count_prior_center:{center}")
    return list(range(lower, upper + 1)), center


def _prior_count_values(
    total: int,
    key: str,
    evidence: RefEvidence,
    probs: dict[str, float],
) -> list[int]:
    fixed = evidence.fixed_counts.get(key)
    exact_cells = _quality_exact_cells(key, evidence)
    if fixed is not None:
        fixed_int = max(0, int(fixed))
        if exact_cells is not None and not can_compose_grid_total(fixed_int, exact_cells):
            return []
        if not _quality_count_matches_value_evidence(key, fixed_int, evidence):
            return []
        return [fixed_int]
    minimum = _effective_min_count(key, evidence)
    maximum = total
    if exact_cells is not None:
        maximum = min(maximum, exact_cells)
        if exact_cells == 0:
            maximum = 0
            minimum = max(minimum, 0)
    p = max(0.0, min(1.0, float(probs.get(key, 0.0))))
    expected = total * p
    sigma = math.sqrt(max(0.75, total * p * max(0.0, 1.0 - p)))
    radius = max(1, min(5, int(math.ceil(1.6 * sigma))))
    lower = max(minimum, int(math.floor(expected - radius)))
    upper = min(maximum, int(math.ceil(expected + radius)))
    anchors = {
        minimum,
        int(round(expected)),
        int(math.floor(expected)),
        int(math.ceil(expected)),
    }
    values = {value for value in range(lower, upper + 1)}
    values.update(value for value in anchors if minimum <= value <= maximum)
    avg = evidence.avg_cells.get(key)
    if avg is not None and avg > 0:
        avg_valid = [
            value
            for value in range(minimum, maximum + 1)
            if _avg_grid_options(value, avg)
        ]
        if avg_valid:
            values.update(avg_valid)
    avg_value = evidence.avg_values.get(key)
    if avg_value is not None and _avg_value_has_positive_signal(avg_value):
        avg_value_valid = [
            value
            for value in range(minimum, maximum + 1)
            if _quality_count_matches_value_evidence(key, value, evidence)
        ]
        if avg_value_valid:
            values.update(avg_value_valid)
    if exact_cells is not None:
        valid = [
            value
            for value in sorted(values)
            if can_compose_grid_total(value, exact_cells)
            and _quality_count_matches_value_evidence(key, value, evidence)
        ]
        if valid:
            return valid
        return [
            value
            for value in range(minimum, maximum + 1)
            if can_compose_grid_total(value, exact_cells)
            and _quality_count_matches_value_evidence(key, value, evidence)
        ]
    return [
        value
        for value in sorted(values)
        if _quality_count_matches_value_evidence(key, value, evidence)
    ]


def _prior_log_weight(
    counts: dict[str, int],
    grids: dict[str, float],
    *,
    total: int,
    total_prior_center: int,
    evidence: RefEvidence,
    probs: dict[str, float],
) -> float:
    logw = _log_fact(total)
    for key in QUALITY_KEYS:
        count = counts[key]
        logw -= _log_fact(count)
        if count:
            logw += count * math.log(max(1e-9, probs[key]))
    logw -= ((total - total_prior_center) ** 2) / (2 * 4.0 * 4.0)
    if evidence.total_grid_target is not None:
        diff = sum(grids.values()) - evidence.total_grid_target
        logw -= min(30.0, (diff * diff) / (2 * 6.0 * 6.0))
    for key, avg in evidence.avg_cells.items():
        count = counts.get(key, 0)
        if count <= 0 or avg is None or avg <= 0:
            continue
        sigma = {
            "q1": 0.35,
            "q3": 0.35,
            "q4": 0.45,
            "q5": 0.55,
            "q6": 0.70,
        }.get(key, 0.55) / max(1.0, math.sqrt(count))
        diff = grids.get(key, 0.0) / count - avg
        logw -= min(30.0, 0.5 * (diff * diff) / (sigma * sigma))
    return logw


def _count_sum_matches(counts: dict[str, int], evidence: RefEvidence) -> bool:
    q4q5 = evidence.count_sums.get("q4q5")
    if q4q5 is not None and counts.get("q4", 0) + counts.get("q5", 0) != int(q4q5):
        return False
    q4q5q6 = evidence.count_sums.get("q4q5q6")
    if (
        q4q5q6 is not None
        and counts.get("q4", 0) + counts.get("q5", 0) + counts.get("q6", 0)
        != int(q4q5q6)
    ):
        return False
    return True


def _random_value_floor(evidence: RefEvidence) -> float | None:
    floors = [
        float(value_floor)
        for _sample_count, value_floor in evidence.random_value_floors
        if value_floor > 0
    ]
    if not floors:
        return None
    return max(floors)


def _random_value_floor_log_weight(value: float, evidence: RefEvidence) -> float:
    floor = _random_value_floor(evidence)
    if floor is None or value >= floor:
        return 0.0
    scale = max(30_000.0, floor * 0.25)
    diff = (floor - value) / scale
    return -min(25.0, 0.5 * diff * diff)


def _quality_exact_value_log_weight(
    counts: dict[str, int],
    grids: dict[str, float],
    item_values: dict[str, float],
    evidence: RefEvidence,
) -> tuple[float, bool]:
    penalty = 0.0
    applied = False
    for key in QUALITY_KEYS:
        if key in evidence.avg_values:
            continue
        exact_value = _quality_exact_value(key, evidence)
        if exact_value is None or exact_value <= 0:
            continue
        count = int(counts.get(key, 0))
        if count <= 0:
            continue
        center = _quality_value_for_grid(
            key,
            count=count,
            grid=grids.get(key, count * DEFAULT_GRID_MEANS[key]),
            item_values=item_values,
        )
        cv = VALUE_UNCERTAINTY_CV.get(key, 0.20)
        scale = max(20_000.0, center * cv / math.sqrt(max(1, count)))
        diff = (float(exact_value) - center) / scale
        penalty -= min(25.0, 0.5 * diff * diff)
        applied = True
    return penalty, applied


def _enumerate_prior_count_combos(
    total: int,
    *,
    evidence: RefEvidence,
    probs: dict[str, float],
    total_prior_center: int,
    max_new: int,
) -> list[RefCombo]:
    if max_new <= 0:
        return []
    values = {
        key: _prior_count_values(total, key, evidence, probs)
        for key in QUALITY_KEYS
    }
    combos: list[RefCombo] = []
    q1_fixed = evidence.fixed_counts.get("q1")
    for q3 in values["q3"]:
        for q4 in values["q4"]:
            for q5 in values["q5"]:
                for q6 in values["q6"]:
                    q1 = total - q3 - q4 - q5 - q6
                    if q1_fixed is not None and q1 != int(q1_fixed):
                        continue
                    if q1 not in values["q1"]:
                        continue
                    counts = {"q1": q1, "q3": q3, "q4": q4, "q5": q5, "q6": q6}
                    if not _count_sum_matches(counts, evidence):
                        continue
                    if any(counts[key] < _effective_min_count(key, evidence) for key in QUALITY_KEYS):
                        continue
                    grids = _grids_for_counts(counts, evidence)
                    if grids is None:
                        continue
                    combos.append(
                        RefCombo(
                            counts=counts,
                            grids=grids,
                            value=0.0,
                            weight=_prior_log_weight(
                                counts,
                                grids,
                                total=total,
                                total_prior_center=total_prior_center,
                                evidence=evidence,
                                probs=probs,
                            ),
                            total_grid=sum(grids.values()),
                        )
                    )
                    if len(combos) >= max_new:
                        return combos
    return combos


def _allocate_integer_counts(total: int, weights: dict[str, float]) -> dict[str, int]:
    keys = list(weights)
    weight_total = sum(max(0.0, weights[key]) for key in keys) or 1.0
    raw = {key: total * max(0.0, weights[key]) / weight_total for key in keys}
    out = {key: int(math.floor(value)) for key, value in raw.items()}
    remainder = total - sum(out.values())
    order = sorted(keys, key=lambda key: raw[key] - out[key], reverse=True)
    for key in order[: max(0, remainder)]:
        out[key] += 1
    return out


def _prior_counts_for_total(
    total: int,
    evidence: RefEvidence,
    probs: dict[str, float],
) -> dict[str, int] | None:
    counts = {key: 0 for key in QUALITY_KEYS}
    fixed_keys: set[str] = set()
    for key, value in evidence.min_counts.items():
        counts[key] = max(counts[key], max(0, int(value)))
    for key, value in evidence.fixed_counts.items():
        counts[key] = max(0, int(value))
        fixed_keys.add(key)

    for group_key, group_keys_tuple in (
        ("q4q5", ("q4", "q5")),
        ("q4q5q6", ("q4", "q5", "q6")),
    ):
        group_sum = evidence.count_sums.get(group_key)
        if group_sum is None:
            continue
        group_total = max(0, int(group_sum))
        fixed_group = sum(counts[key] for key in group_keys_tuple)
        if fixed_group > group_total:
            return None
        missing_group = group_total - fixed_group
        group_keys = [key for key in group_keys_tuple if key not in fixed_keys]
        if group_keys and missing_group:
            group_alloc = _allocate_integer_counts(
                missing_group,
                {key: probs[key] for key in group_keys},
            )
            for key, value in group_alloc.items():
                counts[key] += value
                fixed_keys.add(key)
        elif missing_group:
            return None

    used = sum(counts.values())
    if used > total:
        return None
    free_keys = [key for key in QUALITY_KEYS if key not in fixed_keys]
    if free_keys:
        alloc = _allocate_integer_counts(total - used, {key: probs[key] for key in free_keys})
        for key, value in alloc.items():
            counts[key] += value
    elif used != total:
        return None
    if any(counts[key] < _effective_min_count(key, evidence) for key in QUALITY_KEYS):
        return None
    if any(
        not _quality_count_matches_value_evidence(key, counts[key], evidence)
        for key in QUALITY_KEYS
    ):
        return None
    if not _count_sum_matches(counts, evidence):
        return None
    return counts


def _grids_for_counts(
    counts: dict[str, int],
    evidence: RefEvidence,
) -> dict[str, float] | None:
    grids: dict[str, float] = {}
    for key in QUALITY_KEYS:
        count = counts[key]
        exact_cells = _quality_exact_cells(key, evidence)
        avg = evidence.avg_cells.get(key)
        if exact_cells is not None:
            if not can_compose_grid_total(count, exact_cells):
                return None
            if not _avg_matches_exact_grid(count, avg, exact_cells):
                return None
            grids[key] = float(exact_cells)
        elif count <= 0:
            grids[key] = 0.0
        elif avg is not None:
            options = _avg_grid_options(count, avg)
            selected = _choose_avg_grid_option(count, avg, options)
            if selected is None:
                return None
            grids[key] = selected
        else:
            grids[key] = count * DEFAULT_GRID_MEANS[key]
    fitted = _fit_grids_to_total_target(
        grids,
        counts,
        evidence.avg_cells,
        evidence.total_grid_target,
        fixed_grid_keys=set(evidence.quality_cells),
    )
    hard_total = _hard_total_grid_target_int(evidence)
    if hard_total is not None and abs(sum(fitted.values()) - hard_total) > 0.0001:
        return None
    if not _split_low_quality_q1_grid_matches(counts.get("q1", 0), fitted.get("q1", 0.0), evidence):
        return None
    return fitted


def _quality_value_for_grid(
    key: str,
    *,
    count: int,
    grid: float,
    item_values: dict[str, float],
) -> float:
    if count <= 0:
        return 0.0
    base_total = count * item_values[key]
    mean = max(1.0, DEFAULT_GRID_MEANS[key])
    avg = max(1.0, grid / count)
    impact_ratio = 0.03 if key == "q1" else 0.08
    adjustment = (avg - mean) * item_values[key] * impact_ratio * count
    cap = base_total * (0.20 if key == "q1" else 0.35)
    adjustment = max(-cap, min(cap, adjustment))
    return max(float(count), base_total + adjustment)


def _quality_value_for_evidence(
    key: str,
    *,
    count: int,
    grid: float,
    item_values: dict[str, float],
    evidence: RefEvidence,
) -> float:
    exact_value = _quality_exact_value(key, evidence)
    if exact_value is not None:
        return float(exact_value)
    avg_value = evidence.avg_values.get(key)
    if avg_value is not None:
        total = _avg_value_total_from_count(float(avg_value), int(count))
        if total is not None:
            return total
    return _quality_value_for_grid(
        key,
        count=count,
        grid=grid,
        item_values=item_values,
    )


def _combo_value(
    counts: dict[str, int],
    grids: dict[str, float],
    item_values: dict[str, float],
    evidence: RefEvidence,
) -> float:
    return sum(
        _quality_value_for_evidence(
            key,
            count=counts[key],
            grid=grids.get(key, counts[key] * DEFAULT_GRID_MEANS[key]),
            item_values=item_values,
            evidence=evidence,
        )
        for key in QUALITY_KEYS
    )


def _quality_value_uncertainty(
    key: str,
    *,
    count: int,
    grid: float,
    item_values: dict[str, float],
    evidence: RefEvidence,
) -> float:
    if count <= 0:
        return 0.0
    if _quality_exact_value(key, evidence) is not None:
        return 0.0
    avg_value = evidence.avg_values.get(key)
    if (
        avg_value is not None
        and _avg_value_total_from_count(float(avg_value), int(count)) is not None
    ):
        return 0.0
    center = _quality_value_for_grid(
        key,
        count=count,
        grid=grid,
        item_values=item_values,
    )
    cv = VALUE_UNCERTAINTY_CV.get(key, 0.20)
    return max(0.0, center * cv / math.sqrt(max(1, int(count))))


def _combo_value_uncertainty(
    counts: dict[str, int],
    grids: dict[str, float],
    item_values: dict[str, float],
    evidence: RefEvidence,
) -> float:
    variance = 0.0
    for key in QUALITY_KEYS:
        spread = _quality_value_uncertainty(
            key,
            count=counts[key],
            grid=grids.get(key, counts[key] * DEFAULT_GRID_MEANS[key]),
            item_values=item_values,
            evidence=evidence,
        )
        variance += spread * spread
    return math.sqrt(variance)


def _value_distribution_points(
    center: float,
    spread: float,
) -> tuple[tuple[float, float], ...]:
    if spread < 1.0:
        return ((center, 1.0),)
    return tuple(
        (max(0.0, center + offset * spread), weight)
        for offset, weight in VALUE_DISTRIBUTION_POINTS
    )


def _grid_display_signature(
    evidence: RefEvidence,
) -> tuple[tuple[int | None, ...], tuple[float | None, ...], int | None]:
    exact = tuple(_quality_exact_cells(key, evidence) for key in QUALITY_KEYS)
    avg = tuple(
        round(float(evidence.avg_cells[key]), 6)
        if key in evidence.avg_cells
        else None
        for key in QUALITY_KEYS
    )
    target_int = None
    if evidence.total_grid_target is not None:
        rounded = int(round(float(evidence.total_grid_target)))
        if abs(float(evidence.total_grid_target) - rounded) <= 0.25:
            target_int = rounded
    return exact, avg, target_int


def _cached_grid_constraint_options(
    count: int,
    exact_cells: int | None,
    avg: float | None,
) -> tuple[int, ...] | None:
    if exact_cells is not None:
        if not can_compose_grid_total(count, exact_cells):
            return ()
        if not _avg_matches_exact_grid(count, avg, exact_cells):
            return ()
        return (exact_cells,)
    if count <= 0:
        return (0,)
    if avg is not None:
        return tuple(_avg_grid_options(count, avg))
    return None


@lru_cache(maxsize=20000)
def _display_grid_options_cached(
    counts_tuple: tuple[int, ...],
    key: str,
    exact_tuple: tuple[int | None, ...],
    avg_tuple: tuple[float | None, ...],
    target_int: int | None,
) -> tuple[int, ...]:
    key_index = QUALITY_KEYS.index(key)
    count = counts_tuple[key_index]
    exact_cells = exact_tuple[key_index]
    avg = avg_tuple[key_index]
    constrained = _cached_grid_constraint_options(count, exact_cells, avg)
    if constrained is not None:
        return constrained
    candidates = _composable_grid_options(count)
    if target_int is not None:
        residual = target_int
        all_other_exact = True
        for idx, other_key in enumerate(QUALITY_KEYS):
            if other_key == key:
                continue
            other_options = _cached_grid_constraint_options(
                counts_tuple[idx],
                exact_tuple[idx],
                avg_tuple[idx],
            )
            if other_options is None or len(other_options) != 1:
                all_other_exact = False
                break
            residual -= other_options[0]
        if all_other_exact:
            candidates = tuple(option for option in candidates if option == residual)
    default = count * DEFAULT_GRID_MEANS[key]
    ranked = sorted(candidates, key=lambda option: (abs(option - default), option))
    return tuple(ranked[:DISPLAY_GRID_TOPK])


def _display_grid_options_for_quality(
    counts: dict[str, int],
    evidence: RefEvidence,
    key: str,
) -> tuple[int, ...]:
    exact, avg, target_int = _grid_display_signature(evidence)
    options = _display_grid_options_cached(
        tuple(int(counts[item]) for item in QUALITY_KEYS),
        key,
        exact,
        avg,
        target_int,
    )
    if key == "q1":
        count = int(counts.get(key, 0))
        floor = _split_low_quality_q1_grid_floor(count, evidence)
        if floor > 0:
            filtered = tuple(option for option in options if option >= floor)
            if filtered:
                return filtered
            if _quality_exact_cells(key, evidence) is not None or evidence.avg_cells.get(key) is not None:
                return ()
            candidates = tuple(option for option in _composable_grid_options(count) if option >= floor)
            default = count * DEFAULT_GRID_MEANS[key]
            ranked = sorted(candidates, key=lambda option: (abs(option - default), option))
            return tuple(ranked[:DISPLAY_GRID_TOPK])
    if options:
        return options
    fallback = int(round(counts.get(key, 0) * DEFAULT_GRID_MEANS[key]))
    if can_compose_grid_total(int(counts.get(key, 0)), fallback):
        return (fallback,)
    return _composable_grid_options(int(counts.get(key, 0)))[:1]


def _public_quality_avg_value_notes(notes: Iterable[str]) -> list[str]:
    return [
        str(note)
        for note in notes
        if re.fullmatch(r"public_q[456]_avg_value", str(note))
    ]


def _without_public_quality_avg_values(snapshot: dict[str, Any]) -> dict[str, Any]:
    cloned = copy.deepcopy(snapshot)
    ui_contract = cloned.get("ui_contract")
    if not isinstance(ui_contract, dict):
        return cloned
    constraints = ui_contract.get("constraints")
    if not isinstance(constraints, dict):
        return cloned
    public_info = constraints.get("public_info")
    if not isinstance(public_info, dict):
        return cloned

    def keep(row: Any) -> bool:
        if not isinstance(row, dict):
            return True
        semantic = str(row.get("semantic") or "")
        return semantic not in PUBLIC_AVG_VALUES

    for key in ("public_numeric_facts", "public_avg_values"):
        rows = public_info.get(key)
        if isinstance(rows, list):
            public_info[key] = [row for row in rows if keep(row)]
    return cloned


def _with_public_quality_avg_fallback_notes(
    result: RefResult,
    public_avg_notes: Iterable[str],
) -> RefResult:
    downgrade_notes = [
        "public_quality_avg_value_conflict_fallback",
        *[f"{note}_downgraded" for note in public_avg_notes],
    ]
    notes = tuple(dict.fromkeys([*result.notes, *downgrade_notes]))
    evidence = replace(
        result.evidence,
        source_notes=tuple(dict.fromkeys([*result.evidence.source_notes, *downgrade_notes])),
    )
    return replace(result, notes=notes, evidence=evidence)


def _retry_without_public_quality_avg_values(
    snapshot: dict[str, Any],
    *,
    public_avg_notes: Iterable[str],
    static_data: dict[str, Any],
    safety_factor: float,
    max_combos: int,
) -> RefResult | None:
    notes = list(public_avg_notes)
    if not notes:
        return None
    result = run_reference_engine(
        _without_public_quality_avg_values(snapshot),
        static_data=static_data,
        safety_factor=safety_factor,
        max_combos=max_combos,
        _allow_public_avg_fallback=False,
    )
    if result.status not in {"ok", "count_prior"}:
        return None
    return _with_public_quality_avg_fallback_notes(result, notes)


def run_reference_engine(
    snapshot: dict[str, Any],
    *,
    static_data: dict[str, Any] | None = None,
    safety_factor: float = 0.85,
    max_combos: int = 50000,
    _allow_public_avg_fallback: bool = True,
) -> RefResult:
    static_data = static_data or load_reference_static_data()
    evidence = extract_evidence(snapshot)
    notes = list(evidence.source_notes)
    supported_heroes = {
        "aisha",
        "艾莎",
        "ahmed",
        "ahmad",
        "艾哈迈德",
        "victor",
        "维克托",
    }
    if evidence.hero.lower() not in supported_heroes:
        return RefResult(
            status="not_structured_hero",
            source="ref_v0",
            conservative=None,
            balanced=None,
            aggressive=None,
            value_p25=None,
            value_p50=None,
            value_p75=None,
            combo_count=0,
            red_count_range=(None, None, None),
            red_cells_range=(None, None, None),
            red_value_range=(None, None, None),
            quality_count_ranges={},
            quality_cells_ranges={},
            total_grid_range=(None, None, None),
            notes=("current_hero_not_supported",),
            evidence=evidence,
        )

    if any(note.startswith("hard_conflict:") for note in notes):
        return RefResult(
            status="no_reachable_combo",
            source="ref_v0",
            conservative=None,
            balanced=None,
            aggressive=None,
            value_p25=None,
            value_p50=None,
            value_p75=None,
            combo_count=0,
            red_count_range=(None, None, None),
            red_cells_range=(None, None, None),
            red_value_range=(None, None, None),
            quality_count_ranges={},
            quality_cells_ranges={},
            total_grid_range=(None, None, None),
            notes=tuple(dict.fromkeys(notes + ["constraints_conflict_or_too_strict"])),
            evidence=evidence,
        )

    item_values, price_note = _quality_item_values(evidence.map_id, static_data)
    probs, prob_note = _quality_probabilities(evidence.map_id, static_data)
    notes.extend([price_note, prob_note])
    random_floor = _random_value_floor(evidence)
    if random_floor is not None:
        notes.append(f"random_value_floor_soft_weight:{int(round(random_floor))}")
    total_candidates, total_prior_center = _total_count_candidates(evidence, notes)
    if not total_candidates:
        return RefResult(
            status="missing_total_count",
            source="ref_v0",
            conservative=None,
            balanced=None,
            aggressive=None,
            value_p25=None,
            value_p50=None,
            value_p75=None,
            combo_count=0,
            red_count_range=(None, None, None),
            red_cells_range=(None, None, None),
            red_value_range=(None, None, None),
            quality_count_ranges={},
            quality_cells_ranges={},
            total_grid_range=(None, None, None),
            notes=tuple(notes + ["need_ahmed_r1_or_total_count"]),
            evidence=evidence,
        )

    combos: list[RefCombo] = []
    quality_value_soft_weight_applied = False
    q3_min = evidence.fixed_counts.get("q3", evidence.min_counts.get("q3", 0))
    q4_min = evidence.fixed_counts.get("q4", evidence.min_counts.get("q4", 0))
    q5_min = evidence.fixed_counts.get("q5", evidence.min_counts.get("q5", 0))
    q6_min = evidence.fixed_counts.get("q6", evidence.min_counts.get("q6", 0))

    if total_prior_center is not None:
        for total in total_candidates:
            prior_combos = _enumerate_prior_count_combos(
                total,
                evidence=evidence,
                probs=probs,
                total_prior_center=total_prior_center,
                max_new=max_combos - len(combos),
            )
            for combo in prior_combos:
                value = _combo_value(combo.counts, combo.grids, item_values, evidence)
                quality_value_weight, quality_value_weight_applied = _quality_exact_value_log_weight(
                    combo.counts,
                    combo.grids,
                    item_values,
                    evidence,
                )
                quality_value_soft_weight_applied = (
                    quality_value_soft_weight_applied or quality_value_weight_applied
                )
                combos.append(
                    RefCombo(
                        counts=combo.counts,
                        grids=combo.grids,
                        value=value,
                        weight=combo.weight
                        + quality_value_weight
                        + _random_value_floor_log_weight(value, evidence),
                        total_grid=combo.total_grid,
                    )
                )
            if len(combos) >= max_combos:
                notes.append("combo_cap_hit")
                break
        if combos:
            notes.append("count_prior_enumerated")
            notes.append("grid_conditioned_value_v1")
    else:
        for total in total_candidates:
            for q1 in _count_values(total, "q1", evidence, q3_min + q4_min + q5_min + q6_min):
                remaining_after_q1 = total - q1
                for q3 in _count_values(remaining_after_q1, "q3", evidence, q4_min + q5_min + q6_min):
                    remaining_after_q3 = remaining_after_q1 - q3
                    for q4 in _count_values(remaining_after_q3, "q4", evidence, q5_min + q6_min):
                        remaining_after_q4 = remaining_after_q3 - q4
                        for q5 in _count_values(remaining_after_q4, "q5", evidence, q6_min):
                            q6 = remaining_after_q4 - q5
                            if (
                                "q4q5" in evidence.count_sums
                                and q4 + q5 != evidence.count_sums["q4q5"]
                            ):
                                continue
                            if (
                                "q4q5q6" in evidence.count_sums
                                and q4 + q5 + q6 != evidence.count_sums["q4q5q6"]
                            ):
                                continue
                            if q6 < _effective_min_count("q6", evidence):
                                continue
                            fixed_q6 = evidence.fixed_counts.get("q6")
                            if fixed_q6 is not None and q6 != fixed_q6:
                                continue
                            if not _quality_count_matches_value_evidence("q6", q6, evidence):
                                continue
                            counts = {"q1": q1, "q3": q3, "q4": q4, "q5": q5, "q6": q6}
                            grids = _grids_for_counts(counts, evidence)
                            if grids is None:
                                continue
                            total_grid = sum(grids.values())
                            logw = _log_fact(total)
                            for key in QUALITY_KEYS:
                                count = counts[key]
                                logw -= _log_fact(count)
                                if count:
                                    logw += count * math.log(probs[key])
                            if evidence.total_grid_target is not None:
                                diff = total_grid - evidence.total_grid_target
                                logw -= min(30.0, (diff * diff) / (2 * 6.0 * 6.0))
                            value = _combo_value(counts, grids, item_values, evidence)
                            quality_value_weight, quality_value_weight_applied = _quality_exact_value_log_weight(
                                counts,
                                grids,
                                item_values,
                                evidence,
                            )
                            quality_value_soft_weight_applied = (
                                quality_value_soft_weight_applied or quality_value_weight_applied
                            )
                            combos.append(
                                RefCombo(
                                    counts=counts,
                                    grids=grids,
                                    value=value,
                                    weight=logw
                                    + quality_value_weight
                                    + _random_value_floor_log_weight(value, evidence),
                                    total_grid=total_grid,
                                )
                            )
                            if len(combos) >= max_combos:
                                notes.append("combo_cap_hit")
                                break
                        if len(combos) >= max_combos:
                            break
                    if len(combos) >= max_combos:
                        break
                if len(combos) >= max_combos:
                    break
            if len(combos) >= max_combos:
                break
    if quality_value_soft_weight_applied:
        notes.append("quality_value_soft_weight_v0")

    if not combos:
        public_avg_notes = _public_quality_avg_value_notes(notes)
        if _allow_public_avg_fallback and public_avg_notes:
            fallback = _retry_without_public_quality_avg_values(
                snapshot,
                public_avg_notes=public_avg_notes,
                static_data=static_data,
                safety_factor=safety_factor,
                max_combos=max_combos,
            )
            if fallback is not None:
                return fallback
        return RefResult(
            status="no_reachable_combo",
            source="ref_v0",
            conservative=None,
            balanced=None,
            aggressive=None,
            value_p25=None,
            value_p50=None,
            value_p75=None,
            combo_count=0,
            red_count_range=(None, None, None),
            red_cells_range=(None, None, None),
            red_value_range=(None, None, None),
            quality_count_ranges={},
            quality_cells_ranges={},
            total_grid_range=(None, None, None),
            notes=tuple(notes + ["constraints_conflict_or_too_strict"]),
            evidence=evidence,
        )

    max_logw = max(combo.weight for combo in combos)
    has_intra_quality_value_band = False
    weighted_values: list[tuple[float, float]] = []
    for combo in combos:
        combo_weight = math.exp(max(-745.0, combo.weight - max_logw))
        value_spread = _combo_value_uncertainty(
            combo.counts,
            combo.grids,
            item_values,
            evidence,
        )
        if value_spread >= 1.0:
            has_intra_quality_value_band = True
        for value, point_weight in _value_distribution_points(combo.value, value_spread):
            weighted_values.append((value, combo_weight * point_weight))
    weighted_red = [
        (float(combo.counts["q6"]), math.exp(max(-745.0, combo.weight - max_logw)))
        for combo in combos
    ]
    weighted_red_cells: list[tuple[float, float]] = []
    weighted_red_value: list[tuple[float, float]] = []
    for combo in combos:
        combo_weight = math.exp(max(-745.0, combo.weight - max_logw))
        red_options = _display_grid_options_for_quality(combo.counts, evidence, "q6")
        option_weight = combo_weight / max(1, len(red_options))
        for red_grid in red_options:
            weighted_red_cells.append((float(red_grid), option_weight))
            red_value = _quality_value_for_evidence(
                "q6",
                count=combo.counts["q6"],
                grid=float(red_grid),
                item_values=item_values,
                evidence=evidence,
            )
            red_value_spread = _quality_value_uncertainty(
                "q6",
                count=combo.counts["q6"],
                grid=float(red_grid),
                item_values=item_values,
                evidence=evidence,
            )
            for value, point_weight in _value_distribution_points(red_value, red_value_spread):
                weighted_red_value.append((value, option_weight * point_weight))
    if has_intra_quality_value_band:
        notes.append("intra_quality_value_band_v0")
    weighted_grid = [
        (combo.total_grid, math.exp(max(-745.0, combo.weight - max_logw)))
        for combo in combos
    ]
    quality_count_ranges: dict[str, tuple[int | None, int | None, int | None]] = {}
    quality_cells_ranges: dict[str, tuple[int | None, int | None, int | None]] = {}
    for key in QUALITY_KEYS:
        weighted_count = [
            (float(combo.counts[key]), math.exp(max(-745.0, combo.weight - max_logw)))
            for combo in combos
        ]
        weighted_cells: list[tuple[float, float]] = []
        for combo in combos:
            combo_weight = math.exp(max(-745.0, combo.weight - max_logw))
            options = _display_grid_options_for_quality(combo.counts, evidence, key)
            option_weight = combo_weight / max(1, len(options))
            weighted_cells.extend((float(option), option_weight) for option in options)
        count_q = tuple(_weighted_quantile(weighted_count, q) for q in (0.10, 0.50, 0.90))
        cells_q = tuple(_weighted_quantile(weighted_cells, q) for q in (0.10, 0.50, 0.90))
        quality_count_ranges[key] = tuple(
            int(round(value)) if value is not None else None for value in count_q
        )  # type: ignore[assignment]
        quality_cells_ranges[key] = tuple(
            int(round(value)) if value is not None else None for value in cells_q
        )  # type: ignore[assignment]
    p25 = _weighted_quantile(weighted_values, 0.25)
    p50 = _weighted_quantile(weighted_values, 0.50)
    p75 = _weighted_quantile(weighted_values, 0.75)
    r10 = _weighted_quantile(weighted_red, 0.10)
    r50 = _weighted_quantile(weighted_red, 0.50)
    r90 = _weighted_quantile(weighted_red, 0.90)
    rc10 = _weighted_quantile(weighted_red_cells, 0.10)
    rc50 = _weighted_quantile(weighted_red_cells, 0.50)
    rc90 = _weighted_quantile(weighted_red_cells, 0.90)
    rv10 = _weighted_quantile(weighted_red_value, 0.10)
    rv50 = _weighted_quantile(weighted_red_value, 0.50)
    rv90 = _weighted_quantile(weighted_red_value, 0.90)
    g10 = _weighted_quantile(weighted_grid, 0.10)
    g50 = _weighted_quantile(weighted_grid, 0.50)
    g90 = _weighted_quantile(weighted_grid, 0.90)

    return RefResult(
        status="count_prior" if total_prior_center is not None else "ok",
        source="ref_v0",
        conservative=int(round((p25 or 0) * safety_factor)),
        balanced=int(round((p50 or 0) * safety_factor)),
        aggressive=int(round((p75 or 0) * safety_factor)),
        value_p25=int(round(p25 or 0)),
        value_p50=int(round(p50 or 0)),
        value_p75=int(round(p75 or 0)),
        combo_count=len(combos),
        red_count_range=(
            int(round(r10)) if r10 is not None else None,
            int(round(r50)) if r50 is not None else None,
            int(round(r90)) if r90 is not None else None,
        ),
        red_cells_range=(
            int(round(rc10)) if rc10 is not None else None,
            int(round(rc50)) if rc50 is not None else None,
            int(round(rc90)) if rc90 is not None else None,
        ),
        red_value_range=(
            int(round(rv10)) if rv10 is not None else None,
            int(round(rv50)) if rv50 is not None else None,
            int(round(rv90)) if rv90 is not None else None,
        ),
        quality_count_ranges=quality_count_ranges,
        quality_cells_ranges=quality_cells_ranges,
        total_grid_range=(
            int(round(g10)) if g10 is not None else None,
            int(round(g50)) if g50 is not None else None,
            int(round(g90)) if g90 is not None else None,
        ),
        notes=tuple(dict.fromkeys(notes)),
        evidence=evidence,
    )


def run_reference_engine_from_path(path: Path) -> RefResult:
    return run_reference_engine(json.loads(path.read_text(encoding="utf-8-sig")))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run isolated Ahmed reference v0 on a snapshot.")
    parser.add_argument(
        "snapshot",
        nargs="?",
        default=str(ROOT / "data" / "logs" / "live" / "latest_snapshot.json"),
    )
    args = parser.parse_args()
    result = run_reference_engine_from_path(Path(args.snapshot))
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
