"""Warehouse layout / footroom depth policy shared across heroes.

Aisha uses the full profile (early viewport + R3+ footroom band). Sparse lottery
heroes (Raven, Sophie, Gabriela) use early-band-only hints with tighter caps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

WAREHOUSE_ROWS = 18
GRID_COLUMNS = 10
DEEPEST_ROW_THRESHOLD = 12
LAYOUT_MIN_ROUND = 3
WHITE_ONLY_MAX_ROUND = 3

LAYOUT_MODE_OFF = "off"
LAYOUT_MODE_BAND = "band"
LAYOUT_MODE_TARGET = "target"
LAYOUT_MODE_SHADOW = "shadow"

# Notes — aisha-prefixed notes kept for backward-compatible UI/diagnostics.
AISHA_EARLY_VIEWPORT_GRID_HINT_NOTE = "aisha_early_viewport_grid_hint"
AISHA_LAYOUT_GRID_HINT_NOTE = "aisha_layout_grid_hint_shadow"
AISHA_LAYOUT_FOOTROOM_NOTE = "aisha_layout_grid_footroom_below_deepest"
AISHA_LAYOUT_FOOTROOM_MULT_NOTE = "aisha_layout_footroom_mult"
AISHA_LAYOUT_FOOTROOM_CAP_NOTE = "aisha_layout_footroom_capped"
AISHA_LAYOUT_FOOTROOM_SKIP_NOTE = "aisha_layout_footroom_skipped_not_undershoot"
AISHA_LAYOUT_FOOTROOM_SPARSE_NOTE = "aisha_layout_footroom_sparse_viewport"
AISHA_LAYOUT_BAND_WIDEN_DELTA_NOTE = "aisha_layout_band_widen_delta"
AISHA_LAYOUT_BAND_WIDEN_APPLIED_NOTE = "aisha_layout_band_widen_applied"
AISHA_LAYOUT_APPLICATION_MODE_NOTE = "aisha_layout_application_mode"

LAYOUT_SPARSE_EARLY_HINT_NOTE = "layout_sparse_early_viewport_hint"
LAYOUT_SPARSE_BAND_WIDEN_DELTA_NOTE = "layout_sparse_band_widen_delta"
LAYOUT_SPARSE_PROFILE_NOTE = "layout_sparse_profile"

REF_QUOTE_SAFETY_TIER = (0.90, 0.85, 0.80)
REF_QUOTE_SAFETY_BASE = 0.85
REF_QUOTE_SAFETY_TIER_NOTE = "ref_quote_safety_tier_v1"


@dataclass(frozen=True)
class LayoutDepthSpec:
    profile_id: str
    early_max_round: int
    footroom_min_round: int
    footroom_max_round: int
    footroom_mult_r1: float
    footroom_mult_r2: float
    early_soft_target_cap: float
    footroom_raise_cap_r3: int
    footroom_raise_cap_r4: int
    footroom_raise_cap_r5: int
    use_quality_blended_deepest: bool
    skip_white_only_through_round: int
    sparse_footroom_boost_floor: float


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _append_note_once(notes: list[str], marker: str) -> None:
    if marker not in notes:
        notes.append(marker)


def _item_bottom_row(item: dict[str, Any], *, columns: int = GRID_COLUMNS) -> int | None:
    row = _safe_int(item.get("row"))
    height = _safe_int(item.get("height")) or 1
    if row is None:
        local_index = _safe_int(item.get("local_index"))
        if local_index is not None and columns > 0:
            row = local_index // columns + 1
    if row is None:
        y = _safe_int(item.get("y"))
        if y is None:
            return None
        cell_h = _safe_int(item.get("cell_h")) or 1
        row = int(y // max(1, cell_h)) + 1
    return int(row) + max(1, int(height)) - 1


def _deepest_minimap_bottom_row(items: list[dict[str, Any]], *, columns: int = GRID_COLUMNS) -> int | None:
    bottoms = [value for item in items if (value := _item_bottom_row(item, columns=columns)) is not None]
    return max(bottoms) if bottoms else None


def _known_minimap_cells(items: list[dict[str, Any]]) -> int:
    total = 0
    for item in items:
        cells = _safe_int(item.get("cells"))
        if cells is not None and cells > 0:
            total += int(cells)
            continue
        width = _safe_int(item.get("width")) or 1
        height = _safe_int(item.get("height")) or 1
        total += max(1, int(width) * int(height))
    return total


def _max_minimap_quality(items: list[dict[str, Any]]) -> int | None:
    qualities = [
        int(value)
        for item in items
        if (value := _safe_int(item.get("quality"))) is not None and int(value) > 0
    ]
    return max(qualities) if qualities else None


def _viewport_fill_ratio(*, known_cells: int, deepest: int, columns: int = GRID_COLUMNS) -> float:
    viewport_cells = max(1, int(deepest) * int(columns))
    return min(1.0, max(0.0, float(known_cells) / float(viewport_cells)))


def _sparsity_boost(fill_ratio: float, *, floor: float) -> float:
    return max(floor, min(0.85, 1.0 - float(fill_ratio)))


def _effective_deepest_row(
    items: list[dict[str, Any]],
    *,
    round_no: int,
    spec: LayoutDepthSpec,
    columns: int = GRID_COLUMNS,
) -> int | None:
    deepest = _deepest_minimap_bottom_row(items, columns=columns)
    if deepest is None or not spec.use_quality_blended_deepest:
        return deepest
    if int(round_no) >= 4:
        return deepest
    low_bottoms: list[int] = []
    high_bottoms: list[int] = []
    for item in items:
        quality = _safe_int(item.get("quality"))
        bottom = _item_bottom_row(item, columns=columns)
        if bottom is None or quality is None:
            continue
        if int(quality) <= 1:
            low_bottoms.append(int(bottom))
        elif int(quality) >= 3:
            high_bottoms.append(int(bottom))
    if not low_bottoms or not high_bottoms:
        return deepest
    low_ref = max(low_bottoms)
    high_ref = max(high_bottoms)
    blended = int(round(0.35 * low_ref + 0.65 * high_ref))
    return max(DEEPEST_ROW_THRESHOLD, min(deepest, blended))


def _footroom_raise_cap(spec: LayoutDepthSpec, round_no: int) -> int:
    if int(round_no) <= 3:
        return spec.footroom_raise_cap_r3
    if int(round_no) == 4:
        return spec.footroom_raise_cap_r4
    return spec.footroom_raise_cap_r5


def _footroom_balanced_mult(round_no: int, *, full_profile: bool) -> float:
    if not full_profile:
        return 0.65
    if int(round_no) <= 3:
        return 0.75
    if int(round_no) == 4:
        return 1.0
    return 1.25


def _footroom_multipliers(round_no: int, *, full_profile: bool) -> tuple[float, float, float]:
    if not full_profile:
        return (0.35, 0.65, 0.95)
    if int(round_no) <= 3:
        return (0.5, 0.75, 1.0)
    if int(round_no) == 4:
        return (0.75, 1.0, 1.35)
    return (1.0, 1.25, 1.5)


def _target_looks_undershot(
    *,
    total_grid_target: float | None,
    known_cells: int,
    rows_below: int,
    round_no: int,
    full_profile: bool,
) -> bool:
    if total_grid_target is None:
        return True
    baseline = float(total_grid_target)
    if baseline <= float(known_cells) + 0.5:
        return True
    round_scale = 0.45 if int(round_no) <= 3 else (0.35 if int(round_no) == 4 else 0.28)
    if not full_profile:
        round_scale *= 0.85
    implied_ceiling = float(known_cells) + float(rows_below) * float(GRID_COLUMNS) * round_scale
    return baseline + 0.5 < implied_ceiling


LAYOUT_DEPTH_SPECS: dict[str, LayoutDepthSpec] = {
    "aisha": LayoutDepthSpec(
        profile_id="full",
        early_max_round=2,
        footroom_min_round=LAYOUT_MIN_ROUND,
        footroom_max_round=5,
        footroom_mult_r1=1.45,
        footroom_mult_r2=1.20,
        early_soft_target_cap=52.0,
        footroom_raise_cap_r3=15,
        footroom_raise_cap_r4=22,
        footroom_raise_cap_r5=28,
        use_quality_blended_deepest=True,
        skip_white_only_through_round=WHITE_ONLY_MAX_ROUND,
        sparse_footroom_boost_floor=0.2,
    ),
    "raven": LayoutDepthSpec(
        profile_id="sparse_early",
        early_max_round=4,
        footroom_min_round=99,
        footroom_max_round=0,
        footroom_mult_r1=1.10,
        footroom_mult_r2=1.05,
        early_soft_target_cap=24.0,
        footroom_raise_cap_r3=8,
        footroom_raise_cap_r4=10,
        footroom_raise_cap_r5=12,
        use_quality_blended_deepest=False,
        skip_white_only_through_round=4,
        sparse_footroom_boost_floor=0.35,
    ),
    "sophie": LayoutDepthSpec(
        profile_id="sparse_early",
        early_max_round=4,
        footroom_min_round=99,
        footroom_max_round=0,
        footroom_mult_r1=1.12,
        footroom_mult_r2=1.06,
        early_soft_target_cap=26.0,
        footroom_raise_cap_r3=8,
        footroom_raise_cap_r4=10,
        footroom_raise_cap_r5=12,
        use_quality_blended_deepest=False,
        skip_white_only_through_round=3,
        sparse_footroom_boost_floor=0.35,
    ),
    "gabriela": LayoutDepthSpec(
        profile_id="sparse_early",
        early_max_round=4,
        footroom_min_round=99,
        footroom_max_round=0,
        footroom_mult_r1=1.12,
        footroom_mult_r2=1.06,
        early_soft_target_cap=26.0,
        footroom_raise_cap_r3=8,
        footroom_raise_cap_r4=10,
        footroom_raise_cap_r5=12,
        use_quality_blended_deepest=False,
        skip_white_only_through_round=3,
        sparse_footroom_boost_floor=0.35,
    ),
}


def layout_depth_spec_for_hero(hero_key: str) -> LayoutDepthSpec | None:
    return LAYOUT_DEPTH_SPECS.get(str(hero_key or "").strip().lower())


def quote_safety_multipliers(safety_factor: float = REF_QUOTE_SAFETY_BASE) -> tuple[float, float, float]:
    scale = float(safety_factor) / REF_QUOTE_SAFETY_BASE if safety_factor else 1.0
    return tuple(min(1.0, tier * scale) for tier in REF_QUOTE_SAFETY_TIER)


def _apply_early_viewport_hint(
    *,
    spec: LayoutDepthSpec,
    round_no: int,
    total_grid_target: float | None,
    source_notes: list[str],
    items: list[dict[str, Any]],
) -> float | None:
    if int(round_no) > spec.early_max_round:
        return total_grid_target
    if not items:
        return total_grid_target
    known_cells = _known_minimap_cells(items)
    if known_cells <= 0:
        return total_grid_target
    deepest = _effective_deepest_row(items, round_no=int(round_no), spec=spec)
    if deepest is None or deepest < DEEPEST_ROW_THRESHOLD:
        return total_grid_target

    rows_below = max(0, WAREHOUSE_ROWS - int(deepest))
    fill_ratio = _viewport_fill_ratio(known_cells=known_cells, deepest=int(deepest))
    sparsity_boost = _sparsity_boost(fill_ratio, floor=spec.sparse_footroom_boost_floor)
    footroom_mult = spec.footroom_mult_r1 if int(round_no) <= 1 else spec.footroom_mult_r2
    footroom = rows_below * GRID_COLUMNS * footroom_mult * sparsity_boost
    hinted = float(known_cells + footroom)
    max_quality = _max_minimap_quality(items)

    if spec.profile_id == "sparse_early":
        _append_note_once(source_notes, LAYOUT_SPARSE_PROFILE_NOTE)
        _append_note_once(source_notes, LAYOUT_SPARSE_EARLY_HINT_NOTE)
        baseline = float(total_grid_target if total_grid_target is not None else known_cells)
        delta = max(0, int(round(hinted - baseline)))
        if delta > 0:
            _append_note_once(source_notes, f"{LAYOUT_SPARSE_BAND_WIDEN_DELTA_NOTE}:{delta}")
        if total_grid_target is None:
            capped = min(hinted, float(known_cells) + spec.early_soft_target_cap)
            rounded = float(int(round(capped)))
            _append_note_once(source_notes, f"layout_sparse_early_soft_target:{int(round(rounded))}")
            return rounded
        return total_grid_target

    _append_note_once(source_notes, AISHA_EARLY_VIEWPORT_GRID_HINT_NOTE)
    if int(round_no) <= 1 and max_quality is not None and max_quality <= 1:
        _append_note_once(source_notes, f"aisha_early_viewport_band_low:{int(round(hinted))}")
        return total_grid_target
    if total_grid_target is not None and hinted <= float(total_grid_target) + 0.5:
        return total_grid_target
    if total_grid_target is None:
        capped = min(hinted, float(known_cells) + spec.early_soft_target_cap)
        rounded = float(int(round(capped)))
        _append_note_once(source_notes, f"aisha_early_viewport_soft_target:{int(round(rounded))}")
        return rounded
    return total_grid_target


def _apply_footroom_hint(
    *,
    spec: LayoutDepthSpec,
    round_no: int,
    total_grid_target: float | None,
    source_notes: list[str],
    items: list[dict[str, Any]],
    layout_mode: str,
) -> float | None:
    if spec.profile_id != "full":
        return total_grid_target
    if layout_mode == LAYOUT_MODE_OFF:
        return total_grid_target
    if int(round_no) < spec.footroom_min_round:
        return total_grid_target

    max_quality = _max_minimap_quality(items)
    if (
        max_quality is not None
        and max_quality <= 1
        and int(round_no) <= spec.skip_white_only_through_round
    ):
        return total_grid_target

    deepest = _effective_deepest_row(items, round_no=int(round_no), spec=spec)
    if deepest is None or deepest < DEEPEST_ROW_THRESHOLD:
        return total_grid_target

    known_cells = _known_minimap_cells(items)
    rows_below = max(0, WAREHOUSE_ROWS - int(deepest))
    if not _target_looks_undershot(
        total_grid_target=total_grid_target,
        known_cells=known_cells,
        rows_below=rows_below,
        round_no=int(round_no),
        full_profile=True,
    ):
        _append_note_once(source_notes, AISHA_LAYOUT_FOOTROOM_SKIP_NOTE)
        return total_grid_target

    fill_ratio = _viewport_fill_ratio(known_cells=known_cells, deepest=int(deepest))
    sparsity_boost = _sparsity_boost(fill_ratio, floor=spec.sparse_footroom_boost_floor)
    base_footroom = rows_below * GRID_COLUMNS
    conservative_mult, balanced_mult, aggressive_mult = _footroom_multipliers(
        int(round_no),
        full_profile=True,
    )
    footroom = base_footroom * balanced_mult * sparsity_boost
    raw_hinted = float(known_cells + footroom)
    baseline = float(total_grid_target if total_grid_target is not None else known_cells)
    raise_cap = _footroom_raise_cap(spec, int(round_no))
    capped_hinted = min(raw_hinted, baseline + float(raise_cap))
    hinted = capped_hinted
    if hinted <= baseline + 0.5:
        return total_grid_target

    if raw_hinted > capped_hinted + 0.5:
        _append_note_once(source_notes, AISHA_LAYOUT_FOOTROOM_CAP_NOTE)
    if sparsity_boost >= 0.55:
        _append_note_once(source_notes, AISHA_LAYOUT_FOOTROOM_SPARSE_NOTE)
    _append_note_once(source_notes, AISHA_LAYOUT_GRID_HINT_NOTE)
    _append_note_once(source_notes, AISHA_LAYOUT_FOOTROOM_NOTE)
    _append_note_once(
        source_notes,
        f"{AISHA_LAYOUT_FOOTROOM_MULT_NOTE}:"
        f"{conservative_mult:g}/{balanced_mult:g}/{aggressive_mult:g}@r{int(round_no)}",
    )
    _append_note_once(source_notes, f"{AISHA_LAYOUT_APPLICATION_MODE_NOTE}:{layout_mode}")
    delta = int(round(hinted - baseline))
    if layout_mode == LAYOUT_MODE_SHADOW:
        return total_grid_target
    if layout_mode == LAYOUT_MODE_BAND:
        _append_note_once(source_notes, f"{AISHA_LAYOUT_BAND_WIDEN_DELTA_NOTE}:{delta}")
        return total_grid_target
    if total_grid_target is not None:
        _append_note_once(
            source_notes,
            f"total_grid_target_raised:{int(round(float(total_grid_target)))}->{int(round(hinted))}",
        )
    return hinted


def layout_band_widen_delta(source_notes: Iterable[str], *, sparse: bool = False) -> int | None:
    prefixes = (
        LAYOUT_SPARSE_BAND_WIDEN_DELTA_NOTE,
        AISHA_LAYOUT_BAND_WIDEN_DELTA_NOTE,
    )
    if sparse:
        prefixes = (LAYOUT_SPARSE_BAND_WIDEN_DELTA_NOTE, AISHA_LAYOUT_BAND_WIDEN_DELTA_NOTE)
    for note in source_notes:
        text = str(note)
        for prefix in prefixes:
            if text.startswith(f"{prefix}:"):
                try:
                    return max(0, int(text.split(":", 1)[1]))
                except ValueError:
                    return None
    return None


def apply_layout_band_widen_to_range(
    grid_range: tuple[int | None, int | None, int | None],
    source_notes: list[str],
) -> tuple[int | None, int | None, int | None]:
    delta = layout_band_widen_delta(source_notes)
    if delta is None or delta <= 0:
        return grid_range
    low, mid, high = grid_range
    if mid is None and high is None:
        return grid_range
    anchor = int(mid if mid is not None else high or 0)
    new_high = max(int(high or 0), anchor + int(delta))
    if low is not None:
        new_high = max(int(low), new_high)
    _append_note_once(source_notes, AISHA_LAYOUT_BAND_WIDEN_APPLIED_NOTE)
    return (low, mid, new_high)


def apply_layout_depth_hints(
    *,
    hero_key: str,
    round_no: int | None,
    total_grid_target: float | None,
    source_notes: list[str],
    items: list[dict[str, Any]],
    layout_mode: str,
    hard_total_locked: bool,
) -> float | None:
    spec = layout_depth_spec_for_hero(hero_key)
    if spec is None or round_no is None or hard_total_locked:
        return total_grid_target
    if not items:
        return total_grid_target

    updated = _apply_early_viewport_hint(
        spec=spec,
        round_no=int(round_no),
        total_grid_target=total_grid_target,
        source_notes=source_notes,
        items=items,
    )
    updated = _apply_footroom_hint(
        spec=spec,
        round_no=int(round_no),
        total_grid_target=updated,
        source_notes=source_notes,
        items=items,
        layout_mode=layout_mode,
    )
    return updated
