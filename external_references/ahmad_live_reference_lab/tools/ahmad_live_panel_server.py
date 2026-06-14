from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import permutations
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
LAB_TOOLS = Path(__file__).resolve().parent
if str(LAB_SRC) not in sys.path:
    sys.path.insert(0, str(LAB_SRC))
if str(LAB_TOOLS) not in sys.path:
    sys.path.insert(0, str(LAB_TOOLS))
QUALITY_LABELS = {
    "q1": "白绿",
    "q3": "蓝",
    "q4": "紫",
    "q5": "金",
    "q6": "红",
}
QUALITY_DISPLAY_ORDER = ("q1", "q3", "q4", "q5", "q6")
LOW_QUALITY_DISPLAY_ORDER = ("q1", "q3")
SPLIT_QUALITY_LABELS = {
    "white": "白",
    "green": "绿",
}
SPLIT_QUALITY_DISPLAY_ORDER = ("white", "green")

try:
    from ahmad_ref_engine import (
        AISHA_EARLY_ROUND_MAX_COMBOS,
        HERO_ALIASES,
        HERO_BY_ID,
        STRUCTURED_REF_HERO_KEYS,
        is_supported_ref_hero,
        normalize_hero_key,
        prepare_reference_engine_snapshot,
        run_reference_engine,
    )
except Exception:  # noqa: BLE001 - keep debug server usable without ref core
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
    HERO_BY_ID = {
        103: "aisha",
        204: "ahmed",
        209: "victor",
    }
    STRUCTURED_REF_HERO_KEYS = frozenset({"aisha", "ahmed", "victor"})

    def normalize_hero_key(hero: Any) -> str:
        text = _text(hero, "").strip()
        if not text or text.lower() in {"?", "unknown", "none", "null"}:
            return ""
        return HERO_ALIASES.get(text.lower(), HERO_ALIASES.get(text, text.lower()))

    def is_supported_ref_hero(hero: Any) -> bool:
        return normalize_hero_key(hero) in set(HERO_BY_ID.values())

    run_reference_engine = None  # type: ignore[assignment,misc]
    AISHA_EARLY_ROUND_MAX_COMBOS = 2500  # type: ignore[misc]

    def prepare_reference_engine_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot)

try:
    from hero_ref_live_schedule import (
        EARLY_ROUND_ENGINE_FLAG,
        hero_max_combos_for_round,
        hero_quote_ready,
        hero_ref_wait_hint,
        hero_ref_waiting_result,
        hero_should_run_scheduled_inference,
        hero_uses_dual_pass,
    )
except Exception:  # noqa: BLE001 - schedule optional when panel runs standalone
    EARLY_ROUND_ENGINE_FLAG = "audit_aisha_early_round"

    def hero_should_run_scheduled_inference(hero_key: str, round_no: int | None, phase: str) -> bool:
        return False

    def hero_uses_dual_pass(hero_key: str, round_no: int | None, phase: str) -> bool:
        return hero_key == "aisha" and phase not in ("settled", "manual") and round_no is not None and 1 <= int(round_no) <= 5

    def hero_max_combos_for_round(hero_key: str, round_no: int | None) -> int:
        if hero_key == "aisha" and round_no is not None and int(round_no) < 3:
            return AISHA_EARLY_ROUND_MAX_COMBOS
        return 20_000

    def hero_quote_ready(
        snapshot: dict[str, Any],
        hero_key: str,
        round_no: int,
        public_info: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        del snapshot, hero_key, round_no, public_info
        return True, ""

    def hero_ref_waiting_result(*, hero_key: str, wait_hint: str, category: Any = None) -> dict[str, Any]:
        del hero_key, category
        return {"status": "missing_total_count", "source": "ref_v0", "notes": [f"hero_ref_wait:{wait_hint}"]}

    def hero_ref_wait_hint(ref_notes: list[str]) -> str:
        for note in ref_notes:
            text = str(note)
            if text.startswith("hero_ref_wait:"):
                return text.split(":", 1)[1]
        return ""


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


def _mask_player_display_name(name: str) -> str:
    """UI privacy: keep first/last character, mask the rest."""
    text = str(name or "").strip()
    if len(text) <= 1:
        return text
    if len(text) == 2:
        return f"{text[0]}*{text[1]}"
    return f"{text[0]}{'*' * (len(text) - 2)}{text[-1]}"


def _mask_bidder_display_text(value: Any) -> str:
    """Mask player name in 'name bid' readouts; leave settlement totals untouched."""
    text = _text(value, "-").strip()
    if text in ("", "-"):
        return text
    if text.startswith("总值"):
        return text
    name_part, separator, tail = text.rpartition(" ")
    if separator and any(ch.isdigit() for ch in tail):
        return f"{_mask_player_display_name(name_part)} {tail}"
    return _mask_player_display_name(text)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "是"}
    return bool(value)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clone_as_pre_settlement_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    cloned = json.loads(json.dumps(snapshot, ensure_ascii=False))
    cloned["phase"] = "bidding"
    # The settled-view "估价" card must reproduce the last live (pre-settlement)
    # estimate, not re-estimate with settlement truth. Flipping phase alone is not
    # enough: settlement-grade evidence stays in the snapshot body and ui_contract
    # (notably ui_contract.constraints, which carries exact settlement counts), so
    # the engine would read it back and inflate the estimate. Strip those so the
    # engine falls back to the pre-settlement live evidence stream
    # (structured_ref_inputs / monitor field updates).
    for key in list(cloned.keys()):
        if key.startswith("final_"):
            cloned.pop(key, None)
    for key in (
        "inventory_count",
        "inventory_cells",
        "known_value_sum",
        "minimap_grid_items",
        "model_eval",
    ):
        cloned.pop(key, None)
    uc = cloned.get("ui_contract") if isinstance(cloned.get("ui_contract"), dict) else {}
    cloned["ui_contract"] = uc
    for key in ("constraints", "minimap"):
        uc.pop(key, None)
    context = uc.get("context") if isinstance(uc.get("context"), dict) else {}
    uc["context"] = context
    context["phase"] = "bidding"
    truth = uc.get("truth") if isinstance(uc.get("truth"), dict) else {}
    uc["truth"] = truth
    truth["available"] = False
    return cloned


def _pre_settlement_ref_result(snapshot: dict[str, Any]) -> dict[str, Any]:
    if run_reference_engine is None:
        return {}
    try:
        result = run_reference_engine(
            prepare_reference_engine_snapshot(_clone_as_pre_settlement_snapshot(snapshot))
        ).as_dict()
    except Exception:
        return {}
    if result.get("status") not in {"ok", "count_prior"}:
        return {}
    return result


def _flag(label: str, level: str = "watch", detail: str = "") -> dict[str, str]:
    return {"label": label, "level": level, "detail": detail}


def _money(value: Any, fallback: str = "-") -> str:
    if value in (None, ""):
        return fallback
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return str(value)


def _compact_float(value: Any, *, max_decimals: int = 4) -> str:
    if value in (None, ""):
        return "-"
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return str(value)
    if parsed.is_integer():
        return str(int(parsed))
    return f"{parsed:.{max_decimals}f}".rstrip("0").rstrip(".")


def _compact_grid_cells(value: Any) -> str:
    """Warehouse grid counts are whole cells; layout hints may carry float noise."""
    if value in (None, ""):
        return "-"
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(round(parsed)))


def _range_text(value: Any, *, money: bool = False, suffix: str = "") -> str:
    if not isinstance(value, (list, tuple)) or not value:
        return "-"
    parts: list[str] = []
    for item in value[:3]:
        if item in (None, ""):
            parts.append("-")
        elif money:
            parts.append(_money(item))
        else:
            parsed = _parse_int(item)
            parts.append(str(parsed) if parsed is not None else str(item))
    if not parts or all(part == "-" for part in parts):
        return "-"
    text = " / ".join(parts)
    return f"{text}{suffix}" if suffix else text


def _locked_range_value(value: Any) -> int | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    parsed = [_parse_int(item) for item in value[:3]]
    if any(item is None for item in parsed):
        return None
    first = parsed[0]
    if all(item == first for item in parsed):
        return first
    return None


def _floored_range_values(value: Any, floor: int | None) -> list[Any]:
    if not isinstance(value, (list, tuple)):
        return []
    if floor is None or floor <= 0:
        return list(value[:3])
    out: list[Any] = []
    for item in value[:3]:
        parsed = _parse_int(item)
        out.append(max(parsed, floor) if parsed is not None else item)
    return out


def _locked_low_quality_tier_text(
    key: str,
    count_locked: int,
    *,
    cells_ranges: dict[str, Any] | None,
    evidence: dict[str, Any],
) -> str:
    """Compact locked tier readout: count, or count/cells when grid is also known."""
    label = QUALITY_LABELS.get(key, key)
    cells_locked = None
    if isinstance(cells_ranges, dict):
        cells_locked = _locked_range_value(cells_ranges.get(key))
    if cells_locked is None:
        quality_cells = evidence.get("quality_cells")
        if isinstance(quality_cells, dict):
            cells_locked = _parse_int(quality_cells.get(key))
    if cells_locked is not None:
        return f"{label}{count_locked}/{cells_locked}"
    return f"{label}{count_locked}"


def _quality_uncertainty_summary(
    ref_result: dict[str, Any],
    *,
    count_floors: dict[str, int] | None = None,
    display_order: tuple[str, ...] = LOW_QUALITY_DISPLAY_ORDER,
) -> str:
    ranges = ref_result.get("quality_count_ranges")
    if not isinstance(ranges, dict):
        return "-"
    evidence = ref_result.get("evidence") if isinstance(ref_result.get("evidence"), dict) else {}
    min_counts = evidence.get("min_counts") if isinstance(evidence.get("min_counts"), dict) else {}
    cells_ranges = ref_result.get("quality_cells_ranges")
    if not isinstance(cells_ranges, dict):
        cells_ranges = {}
    unlocked: list[str] = []
    locked: list[str] = []
    for key in display_order:
        floor = _parse_int(min_counts.get(key)) if isinstance(min_counts, dict) else None
        if count_floors and key in count_floors:
            explicit_floor = _parse_int(count_floors.get(key))
            if explicit_floor is not None:
                floor = max(floor or 0, explicit_floor)
        range_values = _floored_range_values(ranges.get(key), floor)
        text = _range_text(range_values).replace(" / ", "/")
        if text == "-":
            continue
        label = QUALITY_LABELS.get(key, key)
        locked_value = _locked_range_value(range_values)
        if locked_value is None:
            unlocked.append(f"{label}{text}")
        else:
            locked.append(
                _locked_low_quality_tier_text(
                    key,
                    locked_value,
                    cells_ranges=cells_ranges,
                    evidence=evidence,
                )
            )
    if unlocked:
        suffix = f" 等{len(unlocked)}项" if len(unlocked) > 3 else ""
        return "未锁 " + " ".join(unlocked[:3]) + suffix
    if locked:
        suffix = f" 等{len(locked)}项" if len(locked) > 4 else ""
        return "已锁 " + " ".join(locked[:4]) + suffix
    return "-"


def _compact_range_text(values: Any, *, suffix: str = "") -> str:
    text = _range_text(values, suffix=suffix)
    return text.replace(" / ", "/") if text != "-" else text


def _display_range_text(values: Any) -> str:
    locked = _locked_range_value(values)
    if locked is not None:
        return _money(locked)
    return _range_text(values)


def _red_range_text(values: Any) -> str:
    """Keep red item/grid columns visible; do not collapse locked triplets."""
    return _range_text(values)


def _range_triplet_ints(values: Any) -> list[int] | None:
    if not isinstance(values, (list, tuple)) or len(values) < 3:
        return None
    parsed = [_parse_int(value) for value in values[:3]]
    if any(value is None for value in parsed):
        return None
    return [int(value) for value in parsed]


def _paired_complement_range(
    total: int | None,
    base_range: Any,
    existing_range: Any,
) -> list[int] | None:
    if total is None or total < 0:
        return None
    base_values = _range_triplet_ints(base_range)
    if base_values is None:
        return None
    paired = [total - value for value in base_values]
    if any(value < 0 for value in paired):
        return None
    existing_values = _range_triplet_ints(existing_range)
    if existing_values is not None and sorted(existing_values) != sorted(paired):
        return None
    return paired


def _permutation_to_match_values(source: list[int], target: list[int]) -> list[int] | None:
    if len(source) != len(target):
        return None
    used: set[int] = set()
    out: list[int] = []
    for value in target:
        match = None
        for index, candidate in enumerate(source):
            if index in used:
                continue
            if candidate == value:
                match = index
                break
        if match is None:
            return None
        used.add(match)
        out.append(match)
    return out


def _valid_count_cells_pairs(counts: list[int], cells: list[int]) -> bool:
    if len(counts) != len(cells):
        return False
    for count, cell in zip(counts, cells):
        if count < 0 or cell < 0:
            return False
        if count == 0 and cell != 0:
            return False
        if count > 0 and cell < count:
            return False
    return True


def _align_cells_to_count_display(
    display_counts: Any,
    original_counts: Any,
    original_cells: Any,
) -> list[int] | None:
    counts = _range_triplet_ints(display_counts)
    cells = _range_triplet_ints(original_cells)
    source_counts = _range_triplet_ints(original_counts)
    if counts is None or cells is None:
        return None
    if source_counts is not None:
        permutation = _permutation_to_match_values(source_counts, counts)
        if permutation is not None:
            reordered = [cells[index] for index in permutation]
            if _valid_count_cells_pairs(counts, reordered):
                return reordered
    if _valid_count_cells_pairs(counts, cells):
        return cells
    for candidate in dict.fromkeys(permutations(cells, 3)):
        reordered = list(candidate)
        if _valid_count_cells_pairs(counts, reordered):
            return reordered
    return None


def _infer_q5q6_count_total(ref_result: dict[str, Any]) -> int | None:
    ranges = ref_result.get("quality_count_ranges")
    if not isinstance(ranges, dict):
        return None
    evidence = ref_result.get("evidence") if isinstance(ref_result.get("evidence"), dict) else {}
    count_sums = evidence.get("count_sums") if isinstance(evidence.get("count_sums"), dict) else {}
    q456_total = _parse_int(count_sums.get("q4q5q6"))
    q4_count = _locked_range_value(ranges.get("q4"))
    if q456_total is not None and q4_count is not None:
        total = q456_total - q4_count
        return total if total >= 0 else None

    total_count = _parse_int(evidence.get("total_count"))
    locked_known = [_locked_range_value(ranges.get(key)) for key in ("q1", "q3", "q4")]
    if total_count is not None and all(value is not None for value in locked_known):
        total = total_count - sum(int(value) for value in locked_known if value is not None)
        return total if total >= 0 else None
    return None


def _red_display_ranges(ref_result: dict[str, Any]) -> tuple[Any, Any]:
    count_ranges = ref_result.get("quality_count_ranges")
    red_count_range = ref_result.get("red_count_range")
    red_cells_range = ref_result.get("red_cells_range")
    if isinstance(count_ranges, dict):
        paired_counts = _paired_complement_range(
            _infer_q5q6_count_total(ref_result),
            count_ranges.get("q5"),
            red_count_range,
        )
        if paired_counts is not None:
            aligned_cells = _align_cells_to_count_display(
                paired_counts,
                red_count_range,
                red_cells_range,
            )
            if aligned_cells is not None:
                red_count_range = paired_counts
                red_cells_range = aligned_cells
    return red_count_range, red_cells_range


def _summed_quality_count_candidates(ref_result: dict[str, Any]) -> list[int]:
    ranges = ref_result.get("quality_count_ranges")
    if not isinstance(ranges, dict):
        return []
    candidates: list[int] = []
    for index in range(3):
        total = 0
        for key in QUALITY_DISPLAY_ORDER:
            values = ranges.get(key)
            if not isinstance(values, (list, tuple)) or len(values) <= index:
                return []
            parsed = _parse_int(values[index])
            if parsed is None:
                return []
            total += parsed
        candidates.append(total)
    return candidates


def _candidate_summary(ref_result: dict[str, Any]) -> str:
    evidence = ref_result.get("evidence")
    if not isinstance(evidence, dict):
        return "-"
    parts: list[str] = []
    total_count = evidence.get("total_count")
    if total_count not in (None, ""):
        parts.append(f"总件 {total_count}")
    else:
        count_candidates = _summed_quality_count_candidates(ref_result)
        if count_candidates:
            parts.append(f"估总件 {_compact_range_text(count_candidates)}")
    total_grid = evidence.get("total_grid_target")
    if total_grid not in (None, ""):
        parts.append(f"总格 {_compact_grid_cells(total_grid)}")
    else:
        total_grid_candidates = _compact_range_text(
            ref_result.get("total_grid_range"),
            suffix="格",
        )
        if total_grid_candidates != "-":
            parts.append(f"估总格 {total_grid_candidates}")
    return " · ".join(parts) if parts else "-"


def _range_is_unlocked(values: Any, floor: int | None = None) -> bool:
    range_values = _floored_range_values(values, floor)
    parsed = [_parse_int(value) for value in range_values]
    known = [value for value in parsed if value is not None]
    return len(known) >= 2 and len(set(known)) > 1


def _q6_grid_needs_direct_info(ref_result: dict[str, Any], evidence: dict[str, Any]) -> bool:
    if evidence.get("total_grid_target") not in (None, ""):
        return False
    quality_cells = evidence.get("quality_cells")
    if isinstance(quality_cells, dict) and quality_cells.get("q6") not in (None, ""):
        return False
    avg_cells = evidence.get("avg_cells")
    if isinstance(avg_cells, dict) and avg_cells.get("q6") not in (None, ""):
        return False
    ranges = ref_result.get("quality_count_ranges")
    if not isinstance(ranges, dict):
        return False
    return _locked_range_value(ranges.get("q6")) is not None


def _unlocked_quality_labels(
    ref_result: dict[str, Any],
    evidence: dict[str, Any],
    quality_order: tuple[str, ...],
) -> list[str]:
    ranges = ref_result.get("quality_count_ranges")
    if not isinstance(ranges, dict):
        return []
    min_counts = evidence.get("min_counts") if isinstance(evidence.get("min_counts"), dict) else {}
    labels: list[str] = []
    for key in quality_order:
        floor = _parse_int(min_counts.get(key))
        if _range_is_unlocked(ranges.get(key), floor):
            labels.append(QUALITY_LABELS.get(key, key))
    return labels


def _evidence_exact_quality_field(
    evidence: dict[str, Any],
    bucket: str,
    quality_key: str,
) -> bool:
    payload = evidence.get(bucket)
    if not isinstance(payload, dict):
        return False
    return payload.get(quality_key) not in (None, "")


def _aisha_tier_needs_tool_info(
    ref_result: dict[str, Any],
    evidence: dict[str, Any],
    quality_key: str,
) -> bool:
    has_count = _evidence_exact_quality_field(evidence, "fixed_counts", quality_key)
    has_cells = _evidence_exact_quality_field(evidence, "quality_cells", quality_key)
    has_avg = _evidence_exact_quality_field(evidence, "avg_cells", quality_key)
    if quality_key == "q5" and has_count and (has_cells or has_avg):
        return False
    if quality_key in {"q3", "q4"} and has_count and (has_cells or has_avg):
        return False
    ranges = ref_result.get("quality_count_ranges")
    min_counts = evidence.get("min_counts") if isinstance(evidence.get("min_counts"), dict) else {}
    floor = _parse_int(min_counts.get(quality_key))
    if isinstance(ranges, dict) and _range_is_unlocked(ranges.get(quality_key), floor):
        return True
    if has_count or (isinstance(ranges, dict) and not _range_is_unlocked(ranges.get(quality_key), floor)):
        if quality_key == "q5":
            return not (has_cells or has_avg)
        return not (has_cells or has_avg)
    return True


def _aisha_green_needs_info(ref_result: dict[str, Any], evidence: dict[str, Any]) -> bool:
    """Green (q1/白绿) is low value, so treat it as known once its count is locked.

    Unlike blue/purple/gold, we do not also require cells/avg for green: waiting on
    green cells would otherwise keep it pinned in the hint for the whole match.
    """
    if _evidence_exact_quality_field(evidence, "fixed_counts", "q1"):
        return False
    ranges = ref_result.get("quality_count_ranges")
    if not isinstance(ranges, dict) or ranges.get("q1") in (None, ""):
        return False
    min_counts = evidence.get("min_counts") if isinstance(evidence.get("min_counts"), dict) else {}
    floor = _parse_int(min_counts.get("q1"))
    return _range_is_unlocked(ranges.get("q1"), floor)


def _aisha_missing_total_count(ref_result: dict[str, Any], evidence: dict[str, Any]) -> bool:
    status = _text(ref_result.get("status"), "")
    if status == "missing_total_count":
        return True
    return evidence.get("total_count") in (None, "")


AISHA_LIVE_ENGINE_MIN_ROUND = 3
AISHA_DUAL_PASS_MAX_ROUND = 5
AISHA_HERO_ID = 103
AISHA_ENGINE_PASS_SKILL = "skill"
AISHA_ENGINE_PASS_ITEM = "item"
# Live monitor: R1–R4 outline skills; R5 has no dedicated skill frame.
AISHA_ROUND_SKILL_IDS: dict[int, int] = {
    1: 1001034,
    2: 1001033,
    3: 1001032,
    4: 1001031,
}
AISHA_ROUND_SKILL_LABELS: dict[int, str] = {
    1: "白品技能帧",
    2: "绿品技能帧",
    3: "蓝品技能帧",
    4: "紫品技能帧",
}
# Player prop frames for item-pass detection (engine mapping optional).
# Keep in sync with monitor zero_implied_action_ids + ahmad_ref_engine ACTION_* tables.
AISHA_PROP_ACTION_IDS: frozenset[str] = frozenset(
    {
        str(action_id)
        for action_id in (
            100103,
            100104,
            100105,
            100106,
            100107,
            100108,
            100109,
            100110,
            100111,
            100112,
            100113,
            100114,
            100115,
            100116,
            100117,
            100118,
            100119,
            100120,
            100121,
            100122,
            100123,
            100124,
            100125,
            100126,
            100127,
            100134,
            100135,
            100136,
            100137,
            100138,
            100139,
            100140,
            100163,
            100204,
            1002041,
            1002042,
            1002043,
            1002044,
        )
    }
)
AISHA_SKILL_ACTION_IDS: frozenset[str] = frozenset(
    str(skill_id) for skill_id in AISHA_ROUND_SKILL_IDS.values()
)

AISHA_DEFENSE_MULTIPLIERS: dict[int, str] = {
    1: "2.0",
    2: "1.6",
    3: "1.3",
    4: "1.1",
    5: "1.1",
}


def _aisha_defense_multiplier_hint(round_no: int | None) -> str:
    """Product-only round defense reference; not applied inside ref_v0."""
    if round_no is None or round_no < 1:
        return ""
    clamped = min(int(round_no), 5)
    multiplier = AISHA_DEFENSE_MULTIPLIERS.get(clamped, "1.1")
    return f"R{clamped}防守×{multiplier}"


def _infer_hero_from_skill_reveals(snapshot: dict[str, Any]) -> str:
    """Backfill hero when monitor session binding lags but skill frames already landed."""
    for row in _iter_snapshot_skill_reveal_rows(snapshot):
        hero_id = _parse_int(row.get("hero_id"))
        if hero_id in HERO_BY_ID:
            return HERO_BY_ID[hero_id]
    return ""


def _snapshot_hero_key(snapshot: dict[str, Any], context: dict[str, Any]) -> str:
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
        structured = snapshot.get("structured_ref_inputs")
        if isinstance(structured, dict):
            structured_hero = _hero_from_context(structured.get("hero"))
            if not _is_unknown_hero(structured_hero):
                hero = structured_hero
    if _is_unknown_hero(hero):
        inferred = _infer_hero_from_skill_reveals(snapshot)
        if inferred:
            hero = inferred
    return normalize_hero_key(hero)


def _aisha_should_dual_pass(
    hero_key: str,
    round_no: int | None,
    phase: str,
) -> bool:
    """Aisha R1–R5: skill-frame pass then optional item-frame pass."""
    return hero_uses_dual_pass(hero_key, round_no, phase)


def _aisha_pass_max_combos(round_no: int) -> int:
    return hero_max_combos_for_round("aisha", round_no)


def _iter_snapshot_skill_reveal_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for key in ("skill_reveal_rows", "skill_reveals"):
        payload = snapshot.get(key)
        if not isinstance(payload, list):
            continue
        for row in payload:
            if not isinstance(row, dict):
                continue
            row_id = id(row)
            if row_id in seen:
                continue
            seen.add(row_id)
            rows.append(row)
    return rows


def _skill_reveal_row_has_signal(row: dict[str, Any]) -> bool:
    revealed = _parse_int(row.get("revealed_items"))
    if revealed is not None and revealed > 0:
        return True
    result_val = row.get("result")
    if result_val not in (None, ""):
        try:
            if float(result_val) != 0.0:
                return True
        except (TypeError, ValueError):
            pass
    items = row.get("observed_items") or row.get("revealed_items_detail") or ()
    if isinstance(items, list) and items:
        return True
    return False


def _aisha_round_skill_frame_ready(snapshot: dict[str, Any], round_no: int) -> bool:
    expected_skill = AISHA_ROUND_SKILL_IDS.get(int(round_no))
    if expected_skill is None:
        return True
    for row in _iter_snapshot_skill_reveal_rows(snapshot):
        if _parse_int(row.get("hero_id")) != AISHA_HERO_ID:
            continue
        if _parse_int(row.get("skill_id")) != expected_skill:
            continue
        if _skill_reveal_row_has_signal(row):
            return True
    return False


def _public_info_row_has_signal(row: dict[str, Any]) -> bool:
    if _parse_int(row.get("info_id")) not in (None, 0):
        return True
    if _skill_reveal_row_has_signal(row):
        return True
    summary = _text(row.get("revealed_summary") or row.get("summary"), "").strip()
    return bool(summary)


def _aisha_round_public_info_ready(
    snapshot: dict[str, Any],
    round_no: int,
) -> bool:
    """Public info landing at or after the current round skill anchor."""
    floor = _aisha_round_skill_sort(snapshot, round_no)
    rows = snapshot.get("public_info_rows")
    if not isinstance(rows, list):
        return False
    for row in rows:
        if not isinstance(row, dict) or not _public_info_row_has_signal(row):
            continue
        row_sort = _action_row_sort(row)
        if floor is not None:
            if row_sort is None or row_sort < floor:
                continue
        return True
    return False


def _aisha_public_info_ready(
    snapshot: dict[str, Any],
    public_info: dict[str, Any],
) -> bool:
    """Any public info in snapshot (cumulative); used for diagnostics only."""
    rows = snapshot.get("public_info_rows")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and _public_info_row_has_signal(row):
                return True
    if isinstance(public_info.get("public_numeric_facts"), list) and public_info["public_numeric_facts"]:
        return True
    if _text(public_info.get("public_numeric_summary"), "").strip():
        return True
    input_constraints = public_info.get("input_constraints")
    if isinstance(input_constraints, dict) and input_constraints:
        return True
    return False


def _aisha_early_round_quote_ready(
    snapshot: dict[str, Any],
    round_no: int,
    public_info: dict[str, Any],
) -> tuple[bool, str]:
    """Skill frame is required; public info is optional and may be absent some rounds."""
    del public_info
    skill_ready = _aisha_round_skill_frame_ready(snapshot, round_no)
    skill_label = AISHA_ROUND_SKILL_LABELS.get(int(round_no), "技能帧")
    if skill_ready:
        return True, ""
    return False, f"等待{skill_label}"


def _snapshot_action_result_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    top = snapshot.get("action_result_rows")
    if isinstance(top, list):
        rows.extend(row for row in top if isinstance(row, dict))
    uc = snapshot.get("ui_contract") if isinstance(snapshot.get("ui_contract"), dict) else {}
    actions = uc.get("actions") if isinstance(uc.get("actions"), dict) else {}
    for row in actions.get("results") or ():
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _action_row_sort(row: dict[str, Any]) -> int | None:
    return _parse_int(row.get("sort"))


def _aisha_round_skill_sort(snapshot: dict[str, Any], round_no: int) -> int | None:
    """Sort anchor for the current round; props at or after this sort belong to this round."""
    expected_skill = AISHA_ROUND_SKILL_IDS.get(int(round_no))
    if expected_skill is None and int(round_no) >= 5:
        expected_skill = AISHA_ROUND_SKILL_IDS.get(4)
    if expected_skill is None:
        return None
    anchor: int | None = None
    for row in _iter_snapshot_skill_reveal_rows(snapshot):
        if _parse_int(row.get("hero_id")) != AISHA_HERO_ID:
            continue
        if _parse_int(row.get("skill_id")) != expected_skill:
            continue
        row_sort = _action_row_sort(row)
        if row_sort is None:
            continue
        if anchor is None or row_sort > anchor:
            anchor = row_sort
    return anchor


def _aisha_is_prop_action_row(row: dict[str, Any]) -> bool:
    action_id = _text(row.get("action_id"), "").strip()
    if not action_id or action_id in AISHA_SKILL_ACTION_IDS:
        return False
    if action_id in AISHA_PROP_ACTION_IDS:
        return True
    if row.get("inferred_zero"):
        return True
    detail = row.get("revealed_items_detail") or row.get("observed_items") or ()
    return isinstance(detail, list) and bool(detail)


def _prop_action_row_has_signal(row: dict[str, Any]) -> bool:
    action_id = _text(row.get("action_id"), "").strip()
    if not action_id:
        return False
    if row.get("inferred_zero"):
        return True
    if action_id in AISHA_PROP_ACTION_IDS and (
        row.get("result") is not None or row.get("result_field") is not None
    ):
        return True
    if _skill_reveal_row_has_signal(row):
        return True
    items = row.get("revealed_items_detail") or row.get("observed_items") or ()
    return isinstance(items, list) and bool(items)


def _aisha_item_frame_ready(snapshot: dict[str, Any], round_no: int) -> bool:
    """Prop/item frame for the current round only; public info is handled by the skill pass."""
    floor = _aisha_round_skill_sort(snapshot, round_no)
    if floor is None:
        return False
    for row in _snapshot_action_result_rows(snapshot):
        if not _aisha_is_prop_action_row(row):
            continue
        row_sort = _action_row_sort(row)
        if row_sort is not None and row_sort < floor:
            continue
        if _prop_action_row_has_signal(row):
            return True
    return False


def _aisha_clone_for_engine_pass(snapshot: dict[str, Any], pass_kind: str) -> dict[str, Any]:
    """Skill pass omits prop action rows only; full snapshot still feeds minimap UI."""
    if pass_kind != AISHA_ENGINE_PASS_SKILL:
        return snapshot
    cloned = json.loads(json.dumps(snapshot, ensure_ascii=False))
    cloned["action_result_rows"] = []
    uc = cloned.get("ui_contract") if isinstance(cloned.get("ui_contract"), dict) else {}
    cloned["ui_contract"] = uc
    actions = uc.get("actions") if isinstance(uc.get("actions"), dict) else {}
    uc["actions"] = actions
    actions["results"] = []
    return cloned


def _aisha_prepare_pass_snapshot(snapshot: dict[str, Any], *, pass_kind: str, round_no: int) -> dict[str, Any]:
    base = _aisha_clone_for_engine_pass(snapshot, pass_kind)
    prepared = prepare_reference_engine_snapshot(base)
    prepared["audit_aisha_engine_pass"] = pass_kind
    if int(round_no) < AISHA_LIVE_ENGINE_MIN_ROUND:
        prepared["audit_aisha_early_round"] = True
    return prepared


def _aisha_run_engine_pass(snapshot: dict[str, Any], *, pass_kind: str, round_no: int) -> dict[str, Any]:
    if run_reference_engine is None:
        return {"status": "unavailable", "source": "ref_v0", "notes": ["ref_engine_unavailable"]}
    prepared = _aisha_prepare_pass_snapshot(snapshot, pass_kind=pass_kind, round_no=round_no)
    try:
        return run_reference_engine(
            prepared,
            max_combos=_aisha_pass_max_combos(round_no),
        ).as_dict()
    except Exception as exc:  # noqa: BLE001 - prototype diagnostics
        return {
            "status": "error",
            "source": "ref_v0",
            "notes": [f"aisha_engine_pass:{pass_kind}", str(exc)],
        }


def _aisha_append_quote_pass_note(result: dict[str, Any], pass_kind: str) -> dict[str, Any]:
    notes = list(result.get("notes") or [])
    marker = f"aisha_quote_pass:{pass_kind}"
    if marker not in notes:
        notes.append(marker)
    result["notes"] = notes
    return result


def _aisha_append_skill_only_pass_notes(
    result: dict[str, Any],
    *,
    snapshot: dict[str, Any],
    round_no: int,
) -> dict[str, Any]:
    result = _aisha_append_quote_pass_note(result, AISHA_ENGINE_PASS_SKILL)
    notes = list(result.get("notes") or [])
    if not _aisha_round_public_info_ready(snapshot, round_no):
        marker = "aisha_quote_pass:skill_no_public_this_round"
        if marker not in notes:
            notes.append(marker)
    if not _aisha_item_frame_ready(snapshot, round_no):
        marker = "aisha_quote_pass:skill_no_items_this_round"
        if marker not in notes:
            notes.append(marker)
    result["notes"] = notes
    return result


def _aisha_skill_only_flag_detail(ref_notes: list[str]) -> str:
    no_items = "aisha_quote_pass:skill_no_items_this_round" in ref_notes
    no_public = "aisha_quote_pass:skill_no_public_this_round" in ref_notes
    if no_items and no_public:
        return "本轮无新公开信息、未用道具；仍按技能帧估价"
    if no_public:
        return "本轮无新公开信息；仍按技能帧估价"
    if no_items:
        return "本轮未用道具；下轮仍按技能帧估价"
    return "道具帧未到；小地图仍显示全部道具"


def _aisha_dual_pass_ref_result(
    snapshot: dict[str, Any],
    *,
    round_no: int,
    public_info: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, float | None]]:
    """Run skill+public pass, then full item pass when prop frame lands."""
    timing: dict[str, float | None] = {"skill": None, "item": None}
    ready, wait_hint = _aisha_early_round_quote_ready(snapshot, round_no, public_info)
    if not ready:
        return _aisha_early_round_waiting_result(wait_hint=wait_hint), timing

    skill_started = time.perf_counter()
    skill_result = _aisha_run_engine_pass(
        snapshot,
        pass_kind=AISHA_ENGINE_PASS_SKILL,
        round_no=round_no,
    )
    timing["skill"] = round((time.perf_counter() - skill_started) * 1000.0, 2)

    if not _aisha_item_frame_ready(snapshot, round_no):
        return _aisha_append_skill_only_pass_notes(
            skill_result,
            snapshot=snapshot,
            round_no=round_no,
        ), timing

    item_started = time.perf_counter()
    item_result = _aisha_run_engine_pass(
        snapshot,
        pass_kind=AISHA_ENGINE_PASS_ITEM,
        round_no=round_no,
    )
    timing["item"] = round((time.perf_counter() - item_started) * 1000.0, 2)
    return _aisha_append_quote_pass_note(item_result, AISHA_ENGINE_PASS_ITEM), timing


def _hero_single_pass_ref_result(
    snapshot: dict[str, Any],
    *,
    hero_key: str,
    round_no: int,
    public_info: dict[str, Any],
) -> dict[str, Any]:
    """Scheduled single-pass ref for Ahmed/Victor/sparse heroes."""
    if run_reference_engine is None:
        return {"status": "unavailable", "source": "ref_v0", "notes": ["ref_engine_unavailable"]}
    ready, wait_hint = hero_quote_ready(snapshot, hero_key, round_no, public_info)
    if not ready:
        return hero_ref_waiting_result(hero_key=hero_key, wait_hint=wait_hint)
    prepared = prepare_reference_engine_snapshot(snapshot)
    spec_boundary = 3
    try:
        from hero_ref_live_schedule import get_hero_schedule

        spec = get_hero_schedule(hero_key)
        if spec is not None:
            spec_boundary = spec.early_round_boundary
    except Exception:  # noqa: BLE001
        pass
    if int(round_no) < spec_boundary:
        prepared[EARLY_ROUND_ENGINE_FLAG] = True
    try:
        return run_reference_engine(
            prepared,
            max_combos=hero_max_combos_for_round(hero_key, round_no),
        ).as_dict()
    except Exception as exc:  # noqa: BLE001 - prototype diagnostics
        return {
            "status": "error",
            "source": "ref_v0",
            "notes": [f"hero_ref_pass:{hero_key}", str(exc)],
        }


def _aisha_quote_pass_kind(ref_notes: list[str]) -> str:
    for note in ref_notes:
        text = str(note)
        if text.startswith("aisha_quote_pass:"):
            return text.split(":", 1)[1]
    return ""


def _aisha_early_round_waiting_result(*, wait_hint: str) -> dict[str, Any]:
    return {
        "status": "missing_total_count",
        "source": "ref_v0",
        "conservative": None,
        "balanced": None,
        "aggressive": None,
        "value_p25": None,
        "value_p50": None,
        "value_p75": None,
        "combo_count": 0,
        "red_count_range": [None, None, None],
        "red_cells_range": [None, None, None],
        "red_value_range": [None, None, None],
        "quality_count_ranges": {},
        "quality_cells_ranges": {},
        "total_grid_range": [None, None, None],
        "notes": ["aisha_early_round_waiting", f"aisha_early_wait:{wait_hint}"],
        "evidence": {"hero": "aisha"},
    }


def _aisha_early_wait_hint(ref_notes: list[str]) -> str:
    return hero_ref_wait_hint(ref_notes)


AISHA_D1_FLAG_DISCOUNT_THRESHOLD = 0.7


def _parse_aisha_d1_discount(note: str) -> float | None:
    """Parse the suggested discount from notes like aisha_d1_shadow_q6_discount=0.62@r3."""
    if "=" not in note:
        return None
    tail = note.split("=", 1)[1]
    value = tail.split("@", 1)[0].strip()
    try:
        return float(value)
    except ValueError:
        return None


def _aisha_d1_flag_detail(ref_notes: list[str]) -> str:
    """Surface red-weight reference only when meaningful, to avoid per-round flag spam.

    apply notes always surface (they change the bid); shadow notes only when the
    suggested discount is below the threshold (most rows emit a near-1.0 shadow note).
    """
    relevant: list[str] = []
    for note in ref_notes:
        text = str(note)
        is_apply = "aisha_d1_apply" in text
        is_shadow = "aisha_d1_shadow" in text
        if not (is_apply or is_shadow):
            continue
        if is_apply:
            relevant.append(text)
            continue
        discount = _parse_aisha_d1_discount(text)
        if discount is not None and discount < AISHA_D1_FLAG_DISCOUNT_THRESHOLD:
            relevant.append(text)
    return "; ".join(relevant[:2])


def _aisha_next_info_hint(
    ref_result: dict[str, Any],
    evidence: dict[str, Any],
    *,
    round_no: int | None = None,
) -> str:
    # Frame Aisha's next step as the info still worth waiting for, instead of a
    # generic "open this tool" prompt. Show the two lowest quality tiers that are
    # still unknown (green < blue < purple < gold); once <=1 quality tier remains
    # open, fold in the outstanding total-cells / total-count needs. Red (q6) is
    # not a waited tier here because it arrives via public / villa reveals.
    quality_tiers = (("q3", "蓝"), ("q4", "紫"), ("q5", "金"))
    unknown: list[str] = []
    if _aisha_green_needs_info(ref_result, evidence):
        unknown.append("绿")
    unknown.extend(
        label
        for key, label in quality_tiers
        if _aisha_tier_needs_tool_info(ref_result, evidence, key)
    )
    total_grid_range = ref_result.get("total_grid_range")
    # Only wait on total cells when the grid count is genuinely uncertain. A range
    # locked to a single value means the grid is effectively known even if no
    # explicit target was chosen yet.
    grid_missing = evidence.get("total_grid_target") in (None, "") and _range_is_unlocked(
        total_grid_range
    )
    total_bits: list[str] = []
    if grid_missing:
        total_bits.append("总格")
    if _aisha_missing_total_count(ref_result, evidence):
        total_bits.append("总件")
    total_text = "、".join(total_bits)

    if len(unknown) >= 2:
        return f"等待{unknown[0]}品和{unknown[1]}品信息"
    if len(unknown) == 1:
        if total_text:
            # Gold (q5) is the top scannable tier and cannot be back-solved from
            # totals, so it is needed together with them ("和"). A lower tier can
            # be derived once the totals + higher tiers are known, so either path
            # helps ("或").
            connector = "和" if unknown[0] == "金" else "信息或"
            return f"等待{unknown[0]}品{connector}{total_text}信息"
        return f"等待{unknown[0]}品信息"
    if total_text:
        return f"等待{total_text}信息"
    return "信息已足够，观察出价"


def _ref_notes_list(ref_result: dict[str, Any]) -> list[str]:
    notes = ref_result.get("notes")
    if isinstance(notes, str):
        return [part.strip() for part in notes.split(";") if part.strip()]
    if isinstance(notes, (list, tuple)):
        return [str(part) for part in notes if str(part).strip()]
    return []


def _ref_not_ready_flag_detail(ref_result: dict[str, Any]) -> str:
    status = _text(ref_result.get("status"), "")
    notes = _ref_notes_list(ref_result)
    if status == "no_reachable_combo":
        if "public_quality_avg_cells_conflict_fallback" in notes:
            return "公开均格与锁定冲突，已降级后重算"
        if any("public_q4_avg_cells_soft_pending_count" in note for note in notes):
            return "紫均格作软约束，待紫件数锁定后收紧"
        if "constraints_conflict_or_too_strict" in notes:
            if any("public_q" in note and "avg_cells" in note for note in notes):
                return "公开均格与当前锁定冲突，暂无可行组合"
            return "约束冲突，暂无可行组合"
    return status


def _ref_waiting_grid_only(ref_result: dict[str, Any]) -> bool:
    return any(note == "waiting_total_count:grid_only" for note in _ref_notes_list(ref_result))


def _ref_waiting_display_text(
    hero_key: str,
    ref_result: dict[str, Any],
    *,
    round_no: int | None = None,
) -> str:
    ref_status = _text(ref_result.get("status"), "")
    schedule_wait = hero_ref_wait_hint(_ref_notes_list(ref_result))
    if schedule_wait:
        return schedule_wait
    if ref_status != "missing_total_count":
        return "等待总件/品质输入"
    if hero_key == "ahmed" and _ref_waiting_grid_only(ref_result):
        return "等待总件数"
    if hero_key == "victor":
        return "等待总件/紫金红"
    if hero_key == "aisha":
        early_wait = _aisha_early_wait_hint(_ref_notes_list(ref_result))
        if early_wait:
            return early_wait
        ref_evidence = ref_result.get("evidence")
        if not isinstance(ref_evidence, dict):
            ref_evidence = {}
        hint = _aisha_next_info_hint(ref_result, ref_evidence, round_no=round_no)
        if hint and hint not in {"-", "信息已足够，观察出价"}:
            return hint
        return "等待总件"
    if hero_key == "ethan":
        return "等待公开输入"
    hint = _next_info_hint(ref_result, hero_key=hero_key)
    if hint and hint != "-":
        return hint
    return "等待外援输入"


def _ref_waiting_flag_label(
    hero_key: str,
    ref_result: dict[str, Any],
    *,
    round_no: int | None = None,
) -> str:
    ref_status = _text(ref_result.get("status"), "")
    if ref_status != "missing_total_count":
        return ""
    return _ref_waiting_display_text(hero_key, ref_result, round_no=round_no)


def _next_info_hint(
    ref_result: dict[str, Any],
    *,
    hero_key: str = "",
    round_no: int | None = None,
) -> str:
    evidence = ref_result.get("evidence")
    if not isinstance(evidence, dict):
        return "-"
    status = _text(ref_result.get("status"), "")
    if hero_key == "aisha":
        return _aisha_next_info_hint(ref_result, evidence, round_no=round_no)
    if status == "missing_total_count":
        if hero_key == "ahmed" and _ref_waiting_grid_only(ref_result):
            return "先补总件"
        if hero_key == "victor":
            return "先补总件/紫金红"
        if hero_key == "ethan":
            return "先补公开总件"
    if status == "missing_total_count" or evidence.get("total_count") in (None, ""):
        return "先补总件"
    total_grid_missing = evidence.get("total_grid_target") in (None, "")
    unlocked_low = _unlocked_quality_labels(ref_result, evidence, LOW_QUALITY_DISPLAY_ORDER)
    if unlocked_low:
        return f"优先补{'/'.join(unlocked_low[:2])}件数或均格"
    unlocked_high = _unlocked_quality_labels(ref_result, evidence, ("q4", "q5"))
    if unlocked_high:
        return f"补{'/'.join(unlocked_high[:2])}件数或均格"
    if total_grid_missing and (
        _range_is_unlocked(ref_result.get("total_grid_range"))
        or _q6_grid_needs_direct_info(ref_result, evidence)
    ):
        return "优先补总格/全均格"
    if total_grid_missing and _compact_range_text(ref_result.get("total_grid_range"), suffix="格") != "-":
        return "补总格/全均格"
    return "信息已足够，观察出价"


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


def _hero_from_context(hero: Any, *hero_id_candidates: Any) -> str:
    text = _text(hero, "").strip()
    if text and text.lower() not in {"?", "unknown", "none", "null"}:
        normalized = normalize_hero_key(text)
        return normalized or text
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
    total_parts: list[str] = []
    avg_parts: list[str] = []
    total_count = evidence.get("total_count")
    if total_count not in (None, ""):
        total_parts.append(f"总件 {total_count}")
    total_grid = evidence.get("total_grid_target")
    if total_grid not in (None, ""):
        total_parts.append(f"总格 {_compact_grid_cells(total_grid)}")
        parsed_count = _parse_int(total_count)
        try:
            parsed_grid = float(total_grid)
        except (TypeError, ValueError):
            parsed_grid = None
        if parsed_count and parsed_grid is not None:
            avg_parts.append(f"全均格 {_compact_float(parsed_grid / parsed_count)}")
    estimated_total_grid = _range_text(ref_result.get("total_grid_range"), suffix="格")
    if estimated_total_grid != "-" and total_grid in (None, ""):
        total_parts.append(f"估总格 {estimated_total_grid}")
    avg_cells = evidence.get("avg_cells")
    split_avg_cells = evidence.get("split_avg_cells")
    if isinstance(split_avg_cells, dict):
        for key in SPLIT_QUALITY_DISPLAY_ORDER:
            value = split_avg_cells.get(key)
            if value in (None, ""):
                continue
            avg_parts.append(f"{SPLIT_QUALITY_LABELS.get(key, key)}均格 {_compact_float(value)}")
    if isinstance(avg_cells, dict):
        for key in QUALITY_DISPLAY_ORDER:
            value = avg_cells.get(key)
            if value in (None, ""):
                continue
            avg_parts.append(f"{QUALITY_LABELS.get(key, key)}均格 {_compact_float(value)}")
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
    ordered_parts = total_parts + parts + avg_parts
    return " · ".join(ordered_parts) if ordered_parts else "-"


def _quality_lower_bound_text(quality_key: str) -> str:
    label = QUALITY_LABELS.get(quality_key)
    if label:
        return f"{label}品≥1"
    if quality_key and quality_key != "unknown":
        return f"{quality_key.upper()}≥1"
    return "品质≥1"


def _minimap_source_label(source_text: str, layout_source: str) -> str:
    source = (source_text or layout_source or "").strip().lower()
    if source == "public_info":
        return "公共抽检"
    if source in {"packet", "quality_reveal", "quality_only", "quality_marker"}:
        return "抽检"
    if source == "skill_reveal":
        return "英雄技能"
    if source in {"settlement", "settlement_inventory"}:
        return "结算"
    return source_text or layout_source or ""


def _shape_text(shape_code: Any, width: int, height: int, cells: Any) -> str:
    parsed_cells = _parse_int(cells)
    if _parse_int(shape_code) is not None and width > 0 and height > 0:
        total = parsed_cells or width * height
        return f"轮廓 {width}x{height}/{total}格"
    if parsed_cells is not None and parsed_cells > 0:
        return f"已知 {parsed_cells}格"
    return ""


def _minimap_item_display_text(
    raw: dict[str, Any],
    *,
    quality_key: str,
    shape_code: Any,
    width: int,
    height: int,
    source_text: str,
) -> tuple[str, str]:
    item_name = _text(raw.get("item_name") or raw.get("name"), "").strip()
    item_id = raw.get("item_id")
    category = _text(raw.get("category_label"), "").strip()
    fallback_label = _quality_lower_bound_text(quality_key)
    label = _text(raw.get("display_label"), "").strip() or item_name or category or fallback_label
    quality_label = QUALITY_LABELS.get(quality_key, quality_key.upper() if quality_key else "品质")
    if item_name:
        primary = item_name
    elif item_id not in (None, "", 0, "0"):
        primary = f"ID {item_id}"
    else:
        primary = fallback_label
    quality_part = (
        ""
        if primary == fallback_label
        else f"{quality_label}品"
        if quality_label and "品" not in quality_label
        else quality_label
    )
    tooltip = _join_notes(
        primary,
        quality_part,
        _shape_text(shape_code, width, height, raw.get("cells")),
        (
            f"价值 {_parse_int(raw.get('value')):,}"
            if _parse_int(raw.get("value")) not in (None, 0)
            else ""
        ),
        _minimap_source_label(source_text, _text(raw.get("layout_source"), "")),
        f"local {raw.get('local_index')}" if raw.get("local_index") not in (None, "") else "",
    )
    explicit_tooltip = _text(raw.get("tooltip"), "").strip()
    return label, explicit_tooltip or tooltip or _text(raw.get("tooltip"), "").strip()


def _minimap_summary(snapshot: dict[str, Any], uc: dict[str, Any]) -> dict[str, Any]:
    minimap = uc.get("minimap") if isinstance(uc.get("minimap"), dict) else {}
    context = uc.get("context") if isinstance(uc.get("context"), dict) else {}
    phase = _text(context.get("phase") or snapshot.get("phase"), "")
    root_items = snapshot.get("minimap_grid_items")
    if not isinstance(root_items, list):
        root_items = []

    status = _text(minimap.get("status"), "")
    contract_items = minimap.get("items") if isinstance(minimap.get("items"), list) else []
    raw_items = contract_items
    layout_source = _text(minimap.get("layout_source"), "")
    if phase == "settled" and root_items:
        raw_items = root_items
        status = "available"
        layout_source = layout_source or "settlement_inventory"
    elif contract_items:
        status = "available"
    elif root_items:
        raw_items = root_items
        status = "available"
        layout_source = layout_source or "minimap_grid_items"
    else:
        raw_items = []

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
            local_index = _parse_int(raw.get("local_index"))
            if (row is None or col is None) and local_index is not None:
                row = local_index // columns + 1
                col = local_index % columns + 1
            if row is None or col is None:
                continue
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
            item_value = _parse_int(raw.get("value"))
            if (
                not render_mode
                and item_value not in (None, 0)
                and shape_code is None
                and _parse_int(raw.get("item_id")) is None
            ):
                shape_code = 11
                width = max(1, width or 1)
                height = max(1, height or 1)
                render_mode = "footprint"
            quality_key = _quality_key(raw.get("quality"))
            label, tooltip = _minimap_item_display_text(
                raw,
                quality_key=quality_key,
                shape_code=shape_code,
                width=width,
                height=height,
                source_text=source_text,
            )
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
                    "label": label,
                    "display_label": _text(raw.get("display_label"), "").strip() or label,
                    "tooltip": tooltip,
                    "value": item_value,
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


def _purple_gold_tier_display_text(
    key: str,
    *,
    count_range: Any,
    cells_ranges: dict[str, Any] | None,
    evidence: dict[str, Any],
) -> str | None:
    """Purple/gold readout: locked top3 → count/cells when grid known; else count or range."""
    label = QUALITY_LABELS.get(key, key)
    locked_count = _locked_range_value(count_range)
    if locked_count is not None:
        cells_locked = None
        if isinstance(cells_ranges, dict):
            cells_locked = _locked_range_value(cells_ranges.get(key))
        if cells_locked is None:
            quality_cells = evidence.get("quality_cells")
            if isinstance(quality_cells, dict):
                cells_locked = _parse_int(quality_cells.get(key))
        if cells_locked is not None:
            return f"{label}{locked_count}/{cells_locked}"
        return f"{label}{locked_count}"
    text = _range_text(count_range).replace(" / ", "/")
    if text == "-":
        return None
    return f"{label}件 {text}"


def _purple_gold_quality_summary(ref_result: dict[str, Any]) -> str:
    ranges = ref_result.get("quality_count_ranges")
    if not isinstance(ranges, dict):
        return "-"
    evidence = ref_result.get("evidence") if isinstance(ref_result.get("evidence"), dict) else {}
    cells_ranges = ref_result.get("quality_cells_ranges")
    if not isinstance(cells_ranges, dict):
        cells_ranges = {}
    parts: list[str] = []
    for key in ("q4", "q5"):
        tier_text = _purple_gold_tier_display_text(
            key,
            count_range=ranges.get(key),
            cells_ranges=cells_ranges,
            evidence=evidence,
        )
        if tier_text:
            parts.append(tier_text)
    return " · ".join(parts) if parts else "-"


def _purple_gold_count_summary(
    counts: dict[str, Any],
    cells: dict[str, Any] | None = None,
) -> str:
    if not isinstance(counts, dict) or not counts:
        return "-"
    cell_map = cells if isinstance(cells, dict) else {}
    parts: list[str] = []
    for key, label in (("q4", "紫"), ("q5", "金")):
        count = _parse_int(counts.get(key))
        if count is None:
            continue
        cell_count = _parse_int(cell_map.get(key))
        if cell_count is not None:
            parts.append(f"{label}{count}/{cell_count}")
        else:
            parts.append(f"{label}{count}")
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
            "uncertainty_summary": "-",
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
    summary_started = time.perf_counter()
    ref_engine_ms: float | None = None
    ref_engine_skill_pass_ms: float | None = None
    ref_engine_item_pass_ms: float | None = None
    settlement_ref_engine_ms: float | None = None
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
        and phase != "settled"
    )
    if capture_session_ahead or monitor_restarted or is_age_stale:
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
            ),
        )
    hero_key_early = _snapshot_hero_key(snapshot, context)
    round_no_early = _parse_int(context.get("round") or snapshot.get("round"))
    aisha_dual_pass = _aisha_should_dual_pass(
        hero_key_early,
        round_no_early,
        phase,
    )
    hero_scheduled_pass = (
        not aisha_dual_pass
        and hero_should_run_scheduled_inference(hero_key_early, round_no_early, phase)
    )
    if aisha_dual_pass:
        ref_started = time.perf_counter()
        ref_result, pass_timing = _aisha_dual_pass_ref_result(
            snapshot,
            round_no=int(round_no_early),
            public_info=public_info,
        )
        ref_engine_skill_pass_ms = pass_timing.get("skill")
        ref_engine_item_pass_ms = pass_timing.get("item")
        ref_engine_ms = round((time.perf_counter() - ref_started) * 1000.0, 2)
    elif hero_scheduled_pass and round_no_early is not None:
        ref_started = time.perf_counter()
        ref_result = _hero_single_pass_ref_result(
            snapshot,
            hero_key=hero_key_early,
            round_no=int(round_no_early),
            public_info=public_info,
        )
        ref_engine_ms = round((time.perf_counter() - ref_started) * 1000.0, 2)
    elif run_reference_engine is not None:
        ref_started = time.perf_counter()
        try:
            ref_result = run_reference_engine(
                prepare_reference_engine_snapshot(snapshot),
                max_combos=hero_max_combos_for_round(hero_key_early, round_no_early),
            ).as_dict()
        except Exception as exc:  # noqa: BLE001 - prototype diagnostics
            ref_result = {
                "status": "error",
                "source": "ref_v0",
                "notes": [str(exc)],
            }
        finally:
            ref_engine_ms = round((time.perf_counter() - ref_started) * 1000.0, 2)
    else:
        ref_result = {"status": "unavailable", "source": "ref_v0", "notes": []}
    ref_evidence = ref_result.get("evidence") if isinstance(ref_result.get("evidence"), dict) else {}

    hero_key = _snapshot_hero_key(snapshot, context)
    hero = hero_key or _hero_from_context(context.get("hero") or snapshot.get("hero"))
    if _is_unknown_hero(hero):
        evidence_hero = _hero_from_context(ref_evidence.get("hero"))
        if not _is_unknown_hero(evidence_hero):
            hero = evidence_hero
            hero_key = normalize_hero_key(hero)
    is_supported = is_supported_ref_hero(hero)
    round_no = _parse_int(context.get("round") or snapshot.get("round"))

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
    if not is_supported:
        flags.append(_flag("未识别英雄", "neutral", f"当前英雄 {hero}"))
    elif hero_key not in STRUCTURED_REF_HERO_KEYS:
        flags.append(_flag("通用 Ref", "neutral", f"当前英雄 {hero_key or hero}"))
    if phase == "settled":
        flags.append(_flag("已结算", "neutral"))
    if _text(context.get("map_alias_mode") or source.get("map_alias_mode")):
        flags.append(_flag("地图 fallback", "watch", _text(context.get("map_alias_mode") or source.get("map_alias_mode"))))
    if info_band in {"low", "低"}:
        flags.append(_flag("证据低", "watch"))
    ref_ok = ref_result.get("status") in {"ok", "count_prior"}
    ref_notes = tuple(str(item) for item in ref_result.get("notes") or ())
    aisha_early_round_waiting = "aisha_early_round_waiting" in ref_notes
    hero_ref_waiting = "hero_ref_waiting" in ref_notes
    ref_trigger_waiting = aisha_early_round_waiting or hero_ref_waiting
    aisha_quote_pass = _aisha_quote_pass_kind(ref_notes)
    aisha_early_round_lightweight = (
        hero_key == "aisha"
        and not ref_trigger_waiting
        and aisha_quote_pass in {AISHA_ENGINE_PASS_SKILL, AISHA_ENGINE_PASS_ITEM}
        and round_no is not None
        and int(round_no) < AISHA_LIVE_ENGINE_MIN_ROUND
    )
    rare_signals = (
        diagnostics.get("rare_signals")
        if isinstance(diagnostics.get("rare_signals"), dict)
        else {}
    )
    ref_sparse_exact_prior = "sparse_exact_total_prior_enumeration" in ref_notes
    ref_combo_cap_hit = "combo_cap_hit" in ref_notes
    ref_count_sums = ref_evidence.get("count_sums") if isinstance(ref_evidence.get("count_sums"), dict) else {}
    victor_missing_q456 = (
        hero_key == "victor"
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
    waiting_flag = _ref_waiting_flag_label(hero_key, ref_result, round_no=round_no)
    if is_supported and waiting_flag:
        flags.append(_flag(waiting_flag, "watch"))
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
    elif is_supported:
        flags.append(_flag("外援未就绪", "watch", _ref_not_ready_flag_detail(ref_result)))
    public_numeric_summary = _text(public_info.get("public_numeric_summary"), "").strip()
    if public_numeric_summary:
        flags.append(_flag("公开信息", "neutral", public_numeric_summary))
    layout_notes = [note for note in ref_notes if "aisha_layout" in note]
    if hero_key == "aisha" and layout_notes:
        flags.append(_flag("布局余量", "neutral", "; ".join(layout_notes[:4])))
    defense_hint = _aisha_defense_multiplier_hint(round_no)
    if hero_key == "aisha" and defense_hint:
        flags.append(_flag(defense_hint, "neutral", "产品参考倍数，不进引擎"))
    if hero_key == "aisha" and ref_trigger_waiting:
        wait_hint = _aisha_early_wait_hint(ref_notes)
        flags.append(
            _flag(
                wait_hint or "等待技能帧",
                "watch",
                "技能帧就绪后再估价",
            )
        )
    elif hero_key == "aisha" and aisha_quote_pass == AISHA_ENGINE_PASS_ITEM:
        detail = "技能帧+道具帧双 pass"
        if ref_engine_skill_pass_ms is not None and ref_engine_item_pass_ms is not None:
            detail = (
                f"技能 {ref_engine_skill_pass_ms:g}ms + 道具 {ref_engine_item_pass_ms:g}ms"
            )
        flags.append(_flag("道具帧估计", "watch", detail))
    elif hero_key == "aisha" and aisha_quote_pass == AISHA_ENGINE_PASS_SKILL:
        flags.append(
            _flag(
                "技能帧估计",
                "watch",
                _aisha_skill_only_flag_detail(ref_notes),
            )
        )
    if hero_key == "aisha" and aisha_early_round_lightweight:
        flags.append(
            _flag(
                "R1–R2轻量",
                "watch",
                "早轮 capped combos；R3+ 全量",
            )
        )
    d1_detail = _aisha_d1_flag_detail(ref_notes) if hero_key == "aisha" else ""
    if d1_detail:
        flags.append(_flag("红品权重参考", "watch", d1_detail))

    latest_result = actions.get("latest_result") if isinstance(actions.get("latest_result"), dict) else {}
    latest_sent = actions.get("latest_sent") if isinstance(actions.get("latest_sent"), dict) else {}
    red_count_display_range, red_cells_display_range = _red_display_ranges(ref_result)
    ref_red_count_range = (
        _red_range_text(red_count_display_range)
        if ref_display_ready
        else ""
    )
    ref_red_cells_range = (
        _red_range_text(red_cells_display_range)
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
        _purple_gold_quality_summary(ref_result)
        if ref_display_ready
        else "-"
    )
    waiting_display = _ref_waiting_display_text(hero_key, ref_result, round_no=round_no)
    display_uncertainty_summary = (
        _quality_uncertainty_summary(ref_result)
        if ref_display_ready
        else waiting_display
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
        display_red_risk_reference = waiting_display
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
        display_uncertainty_summary = _quality_uncertainty_summary(
            ref_result,
            count_floors={"q6": known_q6_count},
        )
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
    main_current_highest = _mask_bidder_display_text(decision.get("current_highest"))
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
    settlement_ref_result: dict[str, Any] = {}
    if phase == "settled" and truth_available:
        settlement_ref_started = time.perf_counter()
        settlement_ref_result = _pre_settlement_ref_result(snapshot)
        settlement_ref_engine_ms = round(
            (time.perf_counter() - settlement_ref_started) * 1000.0,
            2,
        )
    settlement_ref_estimate = _parse_money(settlement_ref_result.get("balanced"))
    posterior_decision_values = _parse_range_numbers(posterior.get("decision_value_range"))
    posterior_decision_p90 = (
        posterior_decision_values[2]
        if len(posterior_decision_values) >= 3
        else None
    )
    settlement_estimate = (
        settlement_ref_estimate
        or _parse_money(decision.get("attack_bid"))
        or posterior_decision_p90
        or ref_balanced
    )
    if phase == "settled" and truth_available:
        truth_q6 = truth.get("q6") if isinstance(truth.get("q6"), dict) else {}
        display_red_count_range = f"{_text(truth_q6.get('count'), '?')} 件"
        display_red_cells_range = f"{_text(truth_q6.get('cells'), '?')} 格"
        display_red_value_range = _money(truth_q6.get("value"))
        settlement_quality_counts = _quality_counts_from_text(snapshot.get("final_quality_counts"))
        settlement_quality_cells = _quality_counts_from_text(snapshot.get("final_quality_cells"))
        if settlement_quality_counts:
            settlement_quality_counts.setdefault("q4", 0)
            settlement_quality_counts.setdefault("q5", 0)
        settlement_quality_summary = _purple_gold_count_summary(
            settlement_quality_counts,
            settlement_quality_cells,
        )
        minimap_settlement_summary = _purple_gold_count_summary(quality_counts)
        known_purple_gold_summary = _known_purple_gold_summary(constraints)
        # Settlement truth carries count+cells; constraints summary is count-only.
        if settlement_quality_summary != "-" and settlement_quality_cells:
            display_quality_count_summary = settlement_quality_summary
        elif known_purple_gold_summary != "-":
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
        display_uncertainty_summary = "已结算"
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
        reference_note = (
            "Settlement review: top cards show last Hero Ref estimate, final total, and final-minus-estimate delta."
            if settlement_ref_estimate is not None
            else "Settlement review: top cards show last formal estimate, final total, and final-minus-estimate delta."
        )

    range_ref_result = settlement_ref_result or ref_result
    range_ref_ok = range_ref_result.get("status") in {"ok", "count_prior"}
    ref_decision_range = (
        f"{_money(range_ref_result.get('conservative'))} / "
        f"{_money(range_ref_result.get('balanced'))} / "
        f"{_money(range_ref_result.get('aggressive'))}"
        if range_ref_ok
        else "-"
    )
    ref_total_value_range = (
        f"{_money(range_ref_result.get('value_p25'))} / "
        f"{_money(range_ref_result.get('value_p50'))} / "
        f"{_money(range_ref_result.get('value_p75'))}"
        if range_ref_ok
        else "-"
    )

    performance = {
        "summary_total_ms": round((time.perf_counter() - summary_started) * 1000.0, 2),
        "ref_engine_ms": ref_engine_ms,
        "ref_engine_skill_pass_ms": ref_engine_skill_pass_ms,
        "ref_engine_item_pass_ms": ref_engine_item_pass_ms,
        "settlement_ref_engine_ms": settlement_ref_engine_ms,
    }

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
            "is_ahmed": hero_key == "ahmed",
            "is_supported_ref_hero": is_supported,
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
            "total_grid_range": _range_text(ref_result.get("total_grid_range"), suffix="格"),
        },
        "red": {
            "count_range": display_red_count_range,
            "cells_range": display_red_cells_range,
            "value_range": display_red_value_range,
            "quality_count_summary": display_quality_count_summary,
            "uncertainty_summary": display_uncertainty_summary,
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
            "candidate_summary": _candidate_summary(ref_result),
            "next_info_hint": _next_info_hint(
                ref_result,
                hero_key=hero_key,
                round_no=round_no,
            ),
            "ref_notes": ";".join(ref_notes),
        },
        "diagnostics": {
            "rare_signals": rare_signals,
            "performance": performance,
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
    footer a { color: var(--accent); }
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
        <div class="row"><span>低品件</span><span id="q6Note">-</span></div>
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
      <span>作者：加菲_Barista · 协作：lemyes · <a href="https://github.com/SeasonCake/bidking-lab" target="_blank" rel="noreferrer">GitHub</a></span>
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
  $('q6Note').textContent = text(red.uncertainty_summary || red.risk_reference);
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
