"""Live ref inference schedule: hero skill-round categories and compute triggers.

Each hero is assigned a category that defines when ref_v0 runs (skill frame vs
public/prop/layout) and how many combos to enumerate per round. Overlay/panel
code imports this module; engine semantics stay in ahmad_ref_engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

# Combo caps — global defaults; per-category overrides in hero_max_combos_for_round.
REF_SPARSE_MAX_COMBOS = 1500
REF_EARLY_MAX_COMBOS = 2500
REF_MID_MAX_COMBOS = 8000
REF_LATE_MAX_COMBOS = 12000
REF_FULL_MAX_COMBOS = 20000

EARLY_ROUND_ENGINE_FLAG = "audit_aisha_early_round"


class HeroInferenceCategory(str, Enum):
    """Skill-round pattern buckets for live ref scheduling."""

    MULTI_ROUND_SKILL = "multi_round_skill"
    PROGRESSIVE_COUNT = "progressive_count"
    EARLY_SINGLE_SKILL = "early_single_skill"
    LATE_SINGLE_SKILL = "late_single_skill"
    EARLY_LATE_SKILL = "early_late_skill"
    R1_BURST = "r1_burst"
    R1_STATIC = "r1_static"
    STAGED_ROUNDS = "staged_rounds"
    SPARSE_PUBLIC_PROP = "sparse_public_prop"


CATEGORY_LABELS_ZH: dict[HeroInferenceCategory, str] = {
    HeroInferenceCategory.MULTI_ROUND_SKILL: "多轮技能帧（每轮触发）",
    HeroInferenceCategory.PROGRESSIVE_COUNT: "渐进件数/均格（每轮技能）",
    HeroInferenceCategory.EARLY_SINGLE_SKILL: "首轮单技能（R1 触发，其后公开/道具）",
    HeroInferenceCategory.LATE_SINGLE_SKILL: "末期单技能（前期公开/布局）",
    HeroInferenceCategory.EARLY_LATE_SKILL: "首末双技能",
    HeroInferenceCategory.R1_BURST: "首轮/跨轮技能爆发",
    HeroInferenceCategory.R1_STATIC: "首轮固定信息",
    HeroInferenceCategory.STAGED_ROUNDS: "分阶段递进（多轮不同技能）",
    HeroInferenceCategory.SPARSE_PUBLIC_PROP: "公开/道具/手填驱动",
}

# Live ref tuning priority — engine/overlay schedule changes focus here first.
PRIORITY_MANAGED_HERO_KEYS = frozenset(
    {"aisha", "ahmed", "raven", "wuqilin", "sophie", "gabriela"}
)


@dataclass(frozen=True)
class HeroRefSchedule:
    hero_key: str
    hero_id: int
    category: HeroInferenceCategory
    skill_rounds: dict[int, int]
    skill_round_labels: dict[int, str]
    dual_pass_max_round: int | None = None
    early_round_boundary: int = 3
    alt_total_action_ids: frozenset[str] = frozenset({"100115", "100204"})
    focus_managed: bool = False


def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


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
    return isinstance(items, list) and bool(items)


def _round_skill_frame_ready(
    snapshot: dict[str, Any],
    *,
    hero_id: int,
    skill_id: int,
) -> bool:
    for row in _iter_snapshot_skill_reveal_rows(snapshot):
        if _parse_int(row.get("hero_id")) != hero_id:
            continue
        if _parse_int(row.get("skill_id")) != skill_id:
            continue
        if _skill_reveal_row_has_signal(row):
            return True
    return False


def _public_info_row_has_signal(row: dict[str, Any]) -> bool:
    if _parse_int(row.get("info_id")) not in (None, 0):
        return True
    if _skill_reveal_row_has_signal(row):
        return True
    summary = _text(row.get("revealed_summary") or row.get("summary"))
    return bool(summary)


def _snapshot_has_public_info(snapshot: dict[str, Any]) -> bool:
    rows = snapshot.get("public_info_rows")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and _public_info_row_has_signal(row):
                return True
    uc = snapshot.get("ui_contract") if isinstance(snapshot.get("ui_contract"), dict) else {}
    constraints = uc.get("constraints") if isinstance(uc.get("constraints"), dict) else {}
    public_info = constraints.get("public_info") if isinstance(constraints.get("public_info"), dict) else {}
    if isinstance(public_info.get("public_numeric_facts"), list) and public_info["public_numeric_facts"]:
        return True
    if _text(public_info.get("public_numeric_summary")):
        return True
    input_constraints = public_info.get("input_constraints")
    return isinstance(input_constraints, dict) and bool(input_constraints)


def _prop_action_row_has_signal(row: dict[str, Any]) -> bool:
    action_id = _text(row.get("action_id"))
    if not action_id:
        return False
    if row.get("inferred_zero"):
        return True
    detail = row.get("revealed_items_detail") or row.get("observed_items") or ()
    if isinstance(detail, list) and detail:
        return True
    result_val = row.get("result")
    if result_val in (None, ""):
        return False
    try:
        return float(result_val) != 0.0
    except (TypeError, ValueError):
        return True


def _snapshot_has_prop_signal(snapshot: dict[str, Any]) -> bool:
    for row in _snapshot_action_result_rows(snapshot):
        if _prop_action_row_has_signal(row):
            return True
    return False


def _snapshot_has_alt_total_signal(snapshot: dict[str, Any], action_ids: frozenset[str]) -> bool:
    for row in _snapshot_action_result_rows(snapshot):
        action_id = _text(row.get("action_id"))
        if action_id not in action_ids:
            continue
        if _prop_action_row_has_signal(row) or _parse_int(row.get("result")) not in (None, 0):
            return True
    for row in _iter_snapshot_skill_reveal_rows(snapshot):
        skill_id = _text(row.get("skill_id"))
        if skill_id in action_ids and _skill_reveal_row_has_signal(row):
            return True
    return False


def _snapshot_has_manual_structured_inputs(snapshot: dict[str, Any]) -> bool:
    structured = snapshot.get("structured_ref_inputs")
    if not isinstance(structured, dict):
        return False
    for key in ("total_count", "count_sums", "fixed_counts", "min_counts", "avg_cells"):
        value = structured.get(key)
        if isinstance(value, dict) and value:
            return True
        if value not in (None, ""):
            return True
    manual = snapshot.get("manual_ref_inputs")
    if isinstance(manual, dict):
        for value in manual.values():
            if value not in (None, ""):
                return True
    return False


def _snapshot_has_layout_signal(snapshot: dict[str, Any]) -> bool:
    for key in ("minimap",):
        block = snapshot.get(key)
        if not isinstance(block, dict):
            continue
        items = block.get("items")
        if isinstance(items, list) and items:
            return True
        if block.get("quality_counts"):
            return True
    uc = snapshot.get("ui_contract") if isinstance(snapshot.get("ui_contract"), dict) else {}
    mm = uc.get("minimap")
    if isinstance(mm, dict):
        items = mm.get("items")
        if isinstance(items, list) and items:
            return True
        if mm.get("quality_counts"):
            return True
    return False


def _round_skill_sort(snapshot: dict[str, Any], *, hero_id: int, skill_id: int) -> int | None:
    anchor: int | None = None
    for row in _iter_snapshot_skill_reveal_rows(snapshot):
        if _parse_int(row.get("hero_id")) != hero_id:
            continue
        if _parse_int(row.get("skill_id")) != skill_id:
            continue
        row_sort = _parse_int(row.get("sort"))
        if row_sort is None:
            continue
        if anchor is None or row_sort > anchor:
            anchor = row_sort
    return anchor


def _round_public_or_prop_ready(
    snapshot: dict[str, Any],
    *,
    round_no: int,
    hero_id: int,
    skill_id: int | None,
) -> bool:
    floor = _round_skill_sort(snapshot, hero_id=hero_id, skill_id=skill_id) if skill_id else None
    rows = snapshot.get("public_info_rows")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict) or not _public_info_row_has_signal(row):
                continue
            row_sort = _parse_int(row.get("sort"))
            if floor is not None and (row_sort is None or row_sort < floor):
                continue
            return True
    for row in _snapshot_action_result_rows(snapshot):
        if not _prop_action_row_has_signal(row):
            continue
        row_sort = _parse_int(row.get("sort"))
        if floor is not None and (row_sort is None or row_sort < floor):
            continue
        return True
    return False


def _sparse_early_ready(snapshot: dict[str, Any]) -> bool:
    return (
        _snapshot_has_public_info(snapshot)
        or _snapshot_has_prop_signal(snapshot)
        or _snapshot_has_manual_structured_inputs(snapshot)
        or _snapshot_has_layout_signal(snapshot)
    )


HERO_REF_SCHEDULES: dict[str, HeroRefSchedule] = {
    "aisha": HeroRefSchedule(
        hero_key="aisha",
        hero_id=103,
        category=HeroInferenceCategory.MULTI_ROUND_SKILL,
        skill_rounds={1: 1001034, 2: 1001033, 3: 1001032, 4: 1001031},
        skill_round_labels={
            1: "白品技能帧",
            2: "绿品技能帧",
            3: "蓝品技能帧",
            4: "紫品技能帧",
        },
        dual_pass_max_round=5,
        early_round_boundary=3,
        focus_managed=True,
    ),
    "ahmed": HeroRefSchedule(
        hero_key="ahmed",
        hero_id=204,
        category=HeroInferenceCategory.PROGRESSIVE_COUNT,
        skill_rounds={
            1: 100204,
            2: 1002041,
            3: 1002042,
            4: 1002043,
            5: 1002044,
        },
        skill_round_labels={
            1: "总件技能帧",
            2: "金均格技能帧",
            3: "紫均格技能帧",
            4: "蓝均格技能帧",
            5: "白绿件技能帧",
        },
        early_round_boundary=2,
        focus_managed=True,
    ),
    "victor": HeroRefSchedule(
        hero_key="victor",
        hero_id=209,
        category=HeroInferenceCategory.EARLY_SINGLE_SKILL,
        skill_rounds={1: 100209},
        skill_round_labels={1: "紫金红件技能帧"},
        early_round_boundary=2,
    ),
    "raven": HeroRefSchedule(
        hero_key="raven",
        hero_id=301,
        category=HeroInferenceCategory.LATE_SINGLE_SKILL,
        skill_rounds={5: 100301},
        skill_round_labels={5: "全品质技能帧"},
        early_round_boundary=5,
        focus_managed=True,
    ),
    "ethan": HeroRefSchedule(
        hero_key="ethan",
        hero_id=208,
        category=HeroInferenceCategory.EARLY_LATE_SKILL,
        skill_rounds={1: 1002081, 5: 1002085},
        skill_round_labels={1: "五类轮廓技能帧", 5: "全仓轮廓技能帧"},
        early_round_boundary=3,
    ),
    "fatima": HeroRefSchedule(
        hero_key="fatima",
        hero_id=101,
        category=HeroInferenceCategory.R1_BURST,
        skill_rounds={1: 1001011},
        skill_round_labels={1: "R1品质技能帧"},
    ),
    "gabriela": HeroRefSchedule(
        hero_key="gabriela",
        hero_id=104,
        category=HeroInferenceCategory.R1_BURST,
        skill_rounds={1: 1001041},
        skill_round_labels={1: "R1起跨轮品质(2件/轮)"},
        focus_managed=True,
    ),
    "sophie": HeroRefSchedule(
        hero_key="sophie",
        hero_id=107,
        category=HeroInferenceCategory.R1_BURST,
        skill_rounds={1: 1001071, 2: 1001072},
        skill_round_labels={1: "R1五件品质", 2: "R2起跨轮品质(2件/轮)"},
        focus_managed=True,
    ),
    "helena": HeroRefSchedule(
        hero_key="helena",
        hero_id=109,
        category=HeroInferenceCategory.R1_BURST,
        skill_rounds={1: 1001091},
        skill_round_labels={1: "R1医疗品质/轮廓"},
    ),
    "carlos": HeroRefSchedule(
        hero_key="carlos",
        hero_id=202,
        category=HeroInferenceCategory.R1_BURST,
        skill_rounds={1: 1002021, 2: 1002022},
        skill_round_labels={1: "R1轮廓", 2: "R2跨轮品质"},
    ),
    "takeda": HeroRefSchedule(
        hero_key="takeda",
        hero_id=206,
        category=HeroInferenceCategory.R1_BURST,
        skill_rounds={1: 1002061, 2: 1002062},
        skill_round_labels={1: "R1书籍轮廓", 2: "R2跨轮品质"},
    ),
    "wuqilin": HeroRefSchedule(
        hero_key="wuqilin",
        hero_id=207,
        category=HeroInferenceCategory.STAGED_ROUNDS,
        skill_rounds={1: 1002071, 2: 1002072, 3: 1002073, 4: 1002074},
        skill_round_labels={
            1: "R1古董件数",
            2: "R2古董轮廓",
            3: "R3古董品质",
            4: "R4古董1/3完整信息",
        },
        focus_managed=True,
    ),
    "chenmei": HeroRefSchedule(
        hero_key="chenmei",
        hero_id=102,
        category=HeroInferenceCategory.EARLY_SINGLE_SKILL,
        skill_rounds={1: 1001021},
        skill_round_labels={1: "R1珠宝时尚轮廓"},
        early_round_boundary=2,
    ),
    "tatiana": HeroRefSchedule(
        hero_key="tatiana",
        hero_id=105,
        category=HeroInferenceCategory.EARLY_SINGLE_SKILL,
        skill_rounds={1: 1001051},
        skill_round_labels={1: "R1时尚品质/轮廓"},
        early_round_boundary=2,
    ),
    "naomi": HeroRefSchedule(
        hero_key="naomi",
        hero_id=106,
        category=HeroInferenceCategory.R1_STATIC,
        skill_rounds={1: 1001061},
        skill_round_labels={1: "R1轮廓+红金件数"},
    ),
    "maria": HeroRefSchedule(
        hero_key="maria",
        hero_id=108,
        category=HeroInferenceCategory.EARLY_SINGLE_SKILL,
        skill_rounds={1: 1001081},
        skill_round_labels={1: "R1白绿蓝价值/品质"},
        early_round_boundary=2,
    ),
    "isabella": HeroRefSchedule(
        hero_key="isabella",
        hero_id=110,
        category=HeroInferenceCategory.R1_STATIC,
        skill_rounds={1: 1001101},
        skill_round_labels={1: "R1轮廓"},
    ),
    "george": HeroRefSchedule(
        hero_key="george",
        hero_id=201,
        category=HeroInferenceCategory.EARLY_SINGLE_SKILL,
        skill_rounds={1: 1002011},
        skill_round_labels={1: "R1武器品质/轮廓"},
        early_round_boundary=2,
    ),
    "leonard": HeroRefSchedule(
        hero_key="leonard",
        hero_id=203,
        category=HeroInferenceCategory.R1_STATIC,
        skill_rounds={1: 1002031},
        skill_round_labels={1: "R1食品/古董品质"},
    ),
    "ivan": HeroRefSchedule(
        hero_key="ivan",
        hero_id=205,
        category=HeroInferenceCategory.EARLY_SINGLE_SKILL,
        skill_rounds={1: 1002051},
        skill_round_labels={1: "R1武器能源轮廓"},
        early_round_boundary=2,
    ),
}


def get_hero_schedule(hero_key: str) -> HeroRefSchedule | None:
    key = _text(hero_key).lower()
    return HERO_REF_SCHEDULES.get(key)


def hero_inference_category(hero_key: str) -> HeroInferenceCategory | None:
    spec = get_hero_schedule(hero_key)
    return spec.category if spec else None


def hero_category_label_zh(hero_key: str) -> str:
    spec = get_hero_schedule(hero_key)
    if spec is None:
        return CATEGORY_LABELS_ZH[HeroInferenceCategory.SPARSE_PUBLIC_PROP]
    return CATEGORY_LABELS_ZH[spec.category]


def hero_should_run_scheduled_inference(
    hero_key: str,
    round_no: int | None,
    phase: str,
) -> bool:
    if phase in ("settled", "manual"):
        return False
    if round_no is None or not (1 <= int(round_no) <= 5):
        return False
    return get_hero_schedule(hero_key) is not None


def hero_uses_dual_pass(hero_key: str, round_no: int | None, phase: str) -> bool:
    spec = get_hero_schedule(hero_key)
    if spec is None or spec.dual_pass_max_round is None:
        return False
    if phase in ("settled", "manual"):
        return False
    if round_no is None:
        return False
    return 1 <= int(round_no) <= int(spec.dual_pass_max_round)


def hero_max_combos_for_round(hero_key: str, round_no: int | None) -> int:
    spec = get_hero_schedule(hero_key)
    r = int(round_no) if round_no is not None else 1
    if spec is None:
        return REF_MID_MAX_COMBOS

    cat = spec.category
    if cat is HeroInferenceCategory.MULTI_ROUND_SKILL:
        if r < 3:
            return REF_EARLY_MAX_COMBOS
        if r < 5:
            return REF_MID_MAX_COMBOS
        return REF_LATE_MAX_COMBOS

    if cat is HeroInferenceCategory.PROGRESSIVE_COUNT:
        if r == 1:
            return REF_EARLY_MAX_COMBOS
        if r <= 3:
            return REF_MID_MAX_COMBOS
        return REF_LATE_MAX_COMBOS

    if cat is HeroInferenceCategory.EARLY_SINGLE_SKILL:
        return REF_EARLY_MAX_COMBOS if r == 1 else REF_MID_MAX_COMBOS

    if cat is HeroInferenceCategory.LATE_SINGLE_SKILL:
        return REF_SPARSE_MAX_COMBOS if r < 5 else REF_LATE_MAX_COMBOS

    if cat is HeroInferenceCategory.EARLY_LATE_SKILL:
        if r == 1:
            return REF_EARLY_MAX_COMBOS
        if r < 5:
            return REF_SPARSE_MAX_COMBOS
        return REF_LATE_MAX_COMBOS

    if cat in {
        HeroInferenceCategory.R1_BURST,
        HeroInferenceCategory.R1_STATIC,
        HeroInferenceCategory.STAGED_ROUNDS,
    }:
        if r == 1:
            return REF_EARLY_MAX_COMBOS
        if r <= 3:
            return REF_MID_MAX_COMBOS
        return REF_LATE_MAX_COMBOS

    return REF_SPARSE_MAX_COMBOS


def _quote_ready_multi_round(
    snapshot: dict[str, Any],
    spec: HeroRefSchedule,
    round_no: int,
) -> tuple[bool, str]:
    skill_id = spec.skill_rounds.get(round_no)
    if skill_id is None:
        return True, ""
    if _round_skill_frame_ready(snapshot, hero_id=spec.hero_id, skill_id=skill_id):
        return True, ""
    label = spec.skill_round_labels.get(round_no, "技能帧")
    return False, f"等待{label}"


def _quote_ready_progressive_count(
    snapshot: dict[str, Any],
    spec: HeroRefSchedule,
    round_no: int,
) -> tuple[bool, str]:
    skill_id = spec.skill_rounds.get(round_no)
    if skill_id is not None and _round_skill_frame_ready(
        snapshot, hero_id=spec.hero_id, skill_id=skill_id
    ):
        return True, ""
    if round_no == 1 and (
        _snapshot_has_alt_total_signal(snapshot, spec.alt_total_action_ids)
        or _snapshot_has_public_info(snapshot)
        or _snapshot_has_manual_structured_inputs(snapshot)
    ):
        return True, ""
    if skill_id is not None and _round_public_or_prop_ready(
        snapshot,
        round_no=round_no,
        hero_id=spec.hero_id,
        skill_id=skill_id,
    ):
        return True, ""
    if round_no > 1 and _sparse_early_ready(snapshot):
        return True, ""
    label = spec.skill_round_labels.get(round_no, "技能帧")
    return False, f"等待{label}或公开/道具"


def _quote_ready_early_single(
    snapshot: dict[str, Any],
    spec: HeroRefSchedule,
    round_no: int,
) -> tuple[bool, str]:
    if round_no == 1:
        skill_id = spec.skill_rounds.get(1)
        if skill_id and _round_skill_frame_ready(snapshot, hero_id=spec.hero_id, skill_id=skill_id):
            return True, ""
        if _snapshot_has_manual_structured_inputs(snapshot) or _snapshot_has_public_info(snapshot):
            return True, ""
        return False, spec.skill_round_labels.get(1, "等待首轮技能帧")
    if _sparse_early_ready(snapshot):
        return True, ""
    return False, "等待公开/道具/手填"


def _quote_ready_late_single(
    snapshot: dict[str, Any],
    spec: HeroRefSchedule,
    round_no: int,
) -> tuple[bool, str]:
    if round_no >= 5:
        skill_id = spec.skill_rounds.get(5)
        if skill_id and _round_skill_frame_ready(snapshot, hero_id=spec.hero_id, skill_id=skill_id):
            return True, ""
        if _sparse_early_ready(snapshot):
            return True, ""
        return False, spec.skill_round_labels.get(5, "等待R5技能帧")
    if _sparse_early_ready(snapshot):
        return True, ""
    return False, "等待公开/道具/布局"


def _quote_ready_early_late(
    snapshot: dict[str, Any],
    spec: HeroRefSchedule,
    round_no: int,
) -> tuple[bool, str]:
    skill_id = spec.skill_rounds.get(round_no)
    if skill_id and _round_skill_frame_ready(snapshot, hero_id=spec.hero_id, skill_id=skill_id):
        return True, ""
    if round_no in spec.skill_rounds:
        return False, spec.skill_round_labels.get(round_no, "等待技能帧")
    if _sparse_early_ready(snapshot):
        return True, ""
    return False, "等待公开/道具/布局"


def _quote_ready_round_skill_or_sparse(
    snapshot: dict[str, Any],
    spec: HeroRefSchedule,
    round_no: int,
) -> tuple[bool, str]:
    skill_id = spec.skill_rounds.get(round_no)
    if skill_id and _round_skill_frame_ready(snapshot, hero_id=spec.hero_id, skill_id=skill_id):
        return True, ""
    if round_no in spec.skill_rounds:
        if round_no == 1 and _sparse_early_ready(snapshot):
            return True, ""
        label = spec.skill_round_labels.get(round_no, "技能帧")
        return False, f"等待{label}"
    if _sparse_early_ready(snapshot):
        return True, ""
    return False, "等待公开/道具/手填"


_QUOTE_READY_HANDLERS: dict[
    HeroInferenceCategory,
    Callable[[dict[str, Any], HeroRefSchedule, int], tuple[bool, str]],
] = {
    HeroInferenceCategory.MULTI_ROUND_SKILL: _quote_ready_multi_round,
    HeroInferenceCategory.PROGRESSIVE_COUNT: _quote_ready_progressive_count,
    HeroInferenceCategory.EARLY_SINGLE_SKILL: _quote_ready_early_single,
    HeroInferenceCategory.LATE_SINGLE_SKILL: _quote_ready_late_single,
    HeroInferenceCategory.EARLY_LATE_SKILL: _quote_ready_early_late,
    HeroInferenceCategory.R1_BURST: _quote_ready_round_skill_or_sparse,
    HeroInferenceCategory.R1_STATIC: _quote_ready_round_skill_or_sparse,
    HeroInferenceCategory.STAGED_ROUNDS: _quote_ready_round_skill_or_sparse,
    HeroInferenceCategory.SPARSE_PUBLIC_PROP: lambda s, _spec, _r: (
        (True, "") if _sparse_early_ready(s) else (False, "等待公开/道具/手填")
    ),
}


def hero_quote_ready(
    snapshot: dict[str, Any],
    hero_key: str,
    round_no: int,
    public_info: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    del public_info
    spec = get_hero_schedule(hero_key)
    if spec is None:
        return (_sparse_early_ready(snapshot), "等待公开/道具/手填")
    handler = _QUOTE_READY_HANDLERS[spec.category]
    return handler(snapshot, spec, int(round_no))


def hero_ref_waiting_result(
    *,
    hero_key: str,
    wait_hint: str,
    category: HeroInferenceCategory | None = None,
) -> dict[str, Any]:
    cat = category or hero_inference_category(hero_key)
    cat_value = cat.value if cat else HeroInferenceCategory.SPARSE_PUBLIC_PROP.value
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
        "notes": [
            "hero_ref_waiting",
            f"hero_ref_wait:{wait_hint}",
            f"hero_ref_category:{cat_value}",
        ],
        "evidence": {"hero": hero_key},
    }


def hero_ref_wait_hint(ref_notes: list[str]) -> str:
    for note in ref_notes:
        text = str(note)
        if text.startswith("hero_ref_wait:"):
            return text.split(":", 1)[1]
        if text.startswith("aisha_early_wait:"):
            return text.split(":", 1)[1]
    return ""


def hero_classification_table() -> list[dict[str, Any]]:
    """Exportable schedule summary for tuning."""
    rows: list[dict[str, Any]] = []
    for key in sorted(HERO_REF_SCHEDULES):
        spec = HERO_REF_SCHEDULES[key]
        rows.append(
            {
                "hero_key": spec.hero_key,
                "hero_id": spec.hero_id,
                "category": spec.category.value,
                "category_label_zh": CATEGORY_LABELS_ZH[spec.category],
                "skill_rounds": dict(spec.skill_rounds),
                "skill_round_labels": dict(spec.skill_round_labels),
                "dual_pass": spec.dual_pass_max_round is not None,
                "focus_managed": spec.focus_managed,
                "max_combos_r1": hero_max_combos_for_round(key, 1),
                "max_combos_r3": hero_max_combos_for_round(key, 3),
                "max_combos_r5": hero_max_combos_for_round(key, 5),
            }
        )
    return rows
