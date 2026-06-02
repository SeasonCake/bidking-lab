"""Summarize live monitor ``model_eval.jsonl`` calibration logs."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.inference.diagnostics import layout_conflict_root  # noqa: E402


_Q6_SHADOW_SAMPLING_TARGETS: tuple[tuple[str, str, int], ...] = (
    ("aisha", "shipwreck", 20),
    ("ethan", "shipwreck", 20),
    ("aisha", "hidden", 10),
    ("ethan", "hidden", 5),
)
_Q6_DEEP_FLOOR_SHADOW_SAMPLING_TARGETS: tuple[tuple[str, str, int], ...] = (
    ("aisha", "shipwreck", 20),
)
_Q6_HIDDEN_FLOOR_SHADOW_SAMPLING_TARGETS: tuple[tuple[str, str, int], ...] = (
    ("aisha", "hidden", 10),
)
_Q6_VILLA_FLOOR_SHADOW_SAMPLING_TARGETS: tuple[tuple[str, str, int], ...] = (
    ("aisha", "villa", 20),
)


def _map_family(map_id: Any) -> str:
    try:
        mid = int(map_id)
    except (TypeError, ValueError):
        return "unknown"
    prefix = mid // 100
    if mid == 2601:
        return "hidden"
    if prefix in {24, 34, 44}:
        return "villa"
    if prefix in {25, 35, 45}:
        return "shipwreck"
    return f"map_{prefix}xx"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _round(value: float | int | None) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def _mae(rows: list[dict[str, Any]], key: str) -> int | None:
    values = [
        abs(int(row[key]))
        for row in rows
        if row.get(key) is not None
    ]
    return _round(statistics.mean(values)) if values else None


def _median_abs(rows: list[dict[str, Any]], key: str) -> int | None:
    values = [
        abs(int(row[key]))
        for row in rows
        if row.get(key) is not None
    ]
    return _round(statistics.median(values)) if values else None


def _numeric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = _numeric(row, key)
        if value is not None:
            values.append(value)
    return values


def _median_value(rows: list[dict[str, Any]], key: str) -> int | None:
    values = _numeric_values(rows, key)
    return _round(statistics.median(values)) if values else None


def _median_float_value(
    rows: list[dict[str, Any]],
    key: str,
    *,
    digits: int = 3,
) -> float | None:
    values = _numeric_values(rows, key)
    return round(statistics.median(values), digits) if values else None


def _p75_value(rows: list[dict[str, Any]], key: str) -> int | None:
    values = _numeric_values(rows, key)
    if len(values) < 4:
        return None
    return _round(statistics.quantiles(values, n=4)[2])


def _p75_float_value(
    rows: list[dict[str, Any]],
    key: str,
    *,
    digits: int = 3,
) -> float | None:
    values = _numeric_values(rows, key)
    if len(values) < 4:
        return None
    return round(statistics.quantiles(values, n=4)[2], digits)


def _numeric_distribution(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: Counter[int] = Counter()
    for row in rows:
        value = _numeric(row, key)
        if value is not None:
            counts[int(round(value))] += 1
    return {
        str(value): count
        for value, count in sorted(counts.items())
    }


def _rate(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row.get(key) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return round(statistics.mean(1.0 if value else 0.0 for value in values), 4)


def _numeric(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe_latest_by_file(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in rows:
        key = str(row.get("file") or "")
        if not key:
            key = f"row:{len(order)}"
        if key not in selected:
            order.append(key)
        current = selected.get(key)
        if current is None or float(row.get("ts") or 0) >= float(current.get("ts") or 0):
            selected[key] = row
    return [selected[key] for key in order]


def _with_derived_layout_root(row: dict[str, Any]) -> dict[str, Any]:
    if not row.get("layout_conflict") or row.get("layout_conflict_root"):
        return row
    root = layout_conflict_root(
        row.get("posterior_diagnostics") or row.get("layout_diagnostics")
    )
    if not root:
        return row
    return {
        **row,
        "layout_conflict_root": root,
    }


def _q6_top_size_band(row: dict[str, Any]) -> str:
    if row.get("q6_top_size_band"):
        return str(row["q6_top_size_band"])
    if (
        int(row.get("final_q6_count") or 0) <= 0
        and int(row.get("final_q6_value") or 0) <= 0
    ):
        return "no_q6"
    if row.get("final_top_item_quality") is None:
        return "q6_top_unknown_cells"
    if int(row.get("final_top_item_quality") or 0) != 6:
        return "q6_not_top_item"
    cells = row.get("final_top_item_cells")
    if cells is None:
        return "q6_top_unknown_cells"
    cells = int(cells)
    if cells <= 2:
        return "q6_top_small"
    if cells <= 4:
        return "q6_top_compact"
    if cells <= 9:
        return "q6_top_medium"
    if cells <= 12:
        return "q6_top_large"
    return "q6_top_huge"


def _q6_miss_root(row: dict[str, Any]) -> str:
    if row.get("q6_miss_root"):
        return str(row["q6_miss_root"])
    if row.get("q6_p90_misses_truth") is not True:
        return ""
    markers: list[str] = []
    if row.get("q6_false_low_risk"):
        markers.append("low_q6_sample_rate")
    if row.get("q6_below_drop_prior"):
        markers.append("below_drop_prior")
    markers.append(_q6_top_size_band(row))
    if row.get("layout_conflict"):
        markers.append("layout_conflict")
        markers.extend(
            part
            for part in str(row.get("layout_conflict_root") or "").split(";")
            if part
        )
    if row.get("relaxed_exact_used"):
        markers.append("relaxed_exact_fallback")
    return ";".join(dict.fromkeys(markers))


def _with_derived_q6_fields(row: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if row.get("q6_top_size_band") is None:
        updates["q6_top_size_band"] = _q6_top_size_band(row)
    if row.get("q6_miss_root") is None:
        root = _q6_miss_root({**row, **updates})
        if root:
            updates["q6_miss_root"] = root
    if (
        row.get("v2_q6_value_p90_under_by") is None
        and row.get("v2_q6_value_p90") is not None
        and int(row.get("final_q6_value") or 0) > 0
    ):
        updates["v2_q6_value_p90_under_by"] = max(
            0,
            int(row.get("final_q6_value") or 0) - int(row["v2_q6_value_p90"]),
        )
    return {**row, **updates} if updates else row


def _evidence_stage(round_no: Any) -> str:
    try:
        value = int(round_no)
    except (TypeError, ValueError):
        return "unknown"
    if value <= 2:
        return "early_1_2"
    if value <= 4:
        return "mid_3_4"
    return "full_5"


def _information_density_score(row: dict[str, Any]) -> int:
    round_no = _numeric(row, "round") or 0
    evidence_count = sum(
        int(_numeric(row, key) or 0)
        for key in (
            "anchor_count",
            "shape_target_count",
            "category_target_count",
            "category_exclusion_count",
        )
    )
    return int(round_no) * 2 + min(evidence_count, 6) * 2


def _information_density_band(score: int | None) -> str:
    if score is None:
        return "unknown"
    if score < 18:
        return "low"
    if score < 34:
        return "medium"
    return "high"


def _with_derived_information_density(row: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if row.get("evidence_stage") is None:
        updates["evidence_stage"] = _evidence_stage(row.get("round"))
    if row.get("information_density_score") is None:
        updates["information_density_score"] = _information_density_score(row)
    if row.get("information_density_band") is None:
        score = int(
            updates.get("information_density_score")
            or row.get("information_density_score")
            or 0
        )
        updates["information_density_band"] = _information_density_band(
            score
        )
    density = str(
        updates.get("information_density_band")
        or row.get("information_density_band")
        or "unknown"
    )
    if row.get("hero_information_density") is None:
        updates["hero_information_density"] = f"{row.get('hero') or 'unknown'}|{density}"
    if row.get("evidence_profile_key") is None:
        updates["evidence_profile_key"] = _evidence_profile_key(row)
    return {**row, **updates} if updates else row


def _evidence_profile_key(row: dict[str, Any]) -> str:
    parts: list[str] = []
    public_key = str(row.get("public_constraint_key") or "none")
    if public_key != "none":
        parts.append(f"public:{public_key}")
    random_sample_avg_values = (
        row.get("random_sample_avg_signal_values")
        if "random_sample_avg_signal_values" in row
        else row.get("random_sample_avg_values")
    )
    if str(random_sample_avg_values or ""):
        parts.append("public:random_avg")
    if (
        int(_numeric(row, "category_target_count") or 0)
        + int(_numeric(row, "category_exclusion_count") or 0)
        > 0
    ):
        parts.append("tool:category")
    if int(_numeric(row, "shape_target_count") or 0) > 0:
        parts.append("shape")
    return "+".join(parts) if parts else "basic"


def _group_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key) or "unknown"), []).append(row)
    out: list[dict[str, Any]] = []
    for value, group_rows in sorted(groups.items()):
        out.append(
            {
                key: value,
                "n": len(group_rows),
                "decision_value_mae": _mae(group_rows, "decision_value_p50_error"),
                "decision_value_median_abs_error": _median_abs(
                    group_rows,
                    "decision_value_p50_error",
                ),
                "warehouse_mae": _mae(group_rows, "warehouse_p50_error"),
                "layout_fit_mae": _mae(group_rows, "layout_fit_p50_error"),
                "q6_false_low_rate": _rate(group_rows, "q6_false_low_risk"),
                "q6_prior_risk_rate": _rate(
                    group_rows,
                    "q6_count_cell_prior_risk",
                ),
                "q6_practical_gate_rate": _rate(
                    group_rows,
                    "q6_practical_gate_hit",
                ),
                "q6_practical_false_positive_rate": _rate(
                    [
                        row for row in group_rows
                        if row.get("q6_practical_gate_hit")
                    ],
                    "q6_practical_gate_false_positive_proxy",
                ),
                "q6_practical_helped_rate": _rate(
                    [
                        row for row in group_rows
                        if row.get("q6_practical_gate_under_before")
                    ],
                    "q6_practical_gate_helped",
                ),
                "q6_residual_boost_shadow_active_rate": _rate(
                    group_rows,
                    "q6_residual_boost_shadow_active",
                ),
                "q6_residual_boost_shadow_false_positive_rate": _rate(
                    [
                        row for row in group_rows
                        if row.get("q6_residual_boost_shadow_active")
                    ],
                    "q6_residual_boost_shadow_false_positive_proxy",
                ),
                "q6_residual_boost_shadow_helped_rate": _rate(
                    [
                        row for row in group_rows
                        if row.get("q6_residual_boost_shadow_under_before")
                    ],
                    "q6_residual_boost_shadow_helped",
                ),
                "q6_residual_deep_floor_shadow_active_rate": _rate(
                    group_rows,
                    "q6_residual_deep_floor_shadow_active",
                ),
                "q6_residual_deep_floor_shadow_false_positive_rate": _rate(
                    [
                        row for row in group_rows
                        if row.get("q6_residual_deep_floor_shadow_active")
                    ],
                    "q6_residual_deep_floor_shadow_false_positive_proxy",
                ),
                "q6_residual_deep_floor_shadow_helped_rate": _rate(
                    [
                        row for row in group_rows
                        if row.get("q6_residual_deep_floor_shadow_under_before")
                    ],
                    "q6_residual_deep_floor_shadow_helped",
                ),
                "q6_p90_miss_rate": _rate(group_rows, "q6_p90_misses_truth"),
                "raw_ceiling_gap_median": _median_value(
                    group_rows,
                    "raw_minus_decision_p90",
                ),
                "layout_conflict_rate": _rate(group_rows, "layout_conflict"),
                "layout_overlap_rate": _marker_rate(
                    group_rows,
                    "layout_conflict_root",
                    "footprint_overlap",
                ),
                "layout_overflow_rate": _marker_rate(
                    group_rows,
                    "layout_conflict_root",
                    "footprint_overflow",
                ),
                "relaxed_exact_rate": _rate(group_rows, "relaxed_exact_used"),
            }
        )
    return out


def _marker_rate(rows: list[dict[str, Any]], key: str, marker: str) -> float | None:
    values = [str(row.get(key) or "") for row in rows if row.get(key) is not None]
    if not values:
        return None
    return round(
        statistics.mean(1.0 if marker in value.split(";") else 0.0 for value in values),
        4,
    )


def _root_cause_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    examples: dict[str, list[str]] = {}
    for row in rows:
        raw = str(row.get(key) or "unclassified")
        markers = [part for part in raw.split(";") if part] or ["unclassified"]
        for marker in markers:
            counts[marker] = counts.get(marker, 0) + 1
            examples.setdefault(marker, [])
            if len(examples[marker]) < 5:
                examples[marker].append(str(row.get("file") or ""))
    return [
        {
            "cause": cause,
            "n": n,
            "examples": examples.get(cause, []),
        }
        for cause, n in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]


def _bid_gap_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key) or "unknown"), []).append(row)

    out: list[dict[str, Any]] = []
    for value, group_rows in sorted(groups.items()):
        bid_ratios: list[float] = []
        stop_minus_values: list[float] = []
        over_final = 0
        usable_bid_rows = 0
        for row in group_rows:
            highest = _numeric(row, "highest_bid")
            final_value = _numeric(row, "final_value")
            if highest is not None and final_value is not None and final_value > 0:
                usable_bid_rows += 1
                bid_ratios.append(highest / final_value)
                if highest > final_value:
                    over_final += 1
            stop_minus = _numeric(row, "stop_minus_final_value")
            if stop_minus is not None:
                stop_minus_values.append(stop_minus)
        out.append(
            {
                key: value,
                "n": len(group_rows),
                "bid_rows": usable_bid_rows,
                "highest_bid_over_final_median": (
                    round(statistics.median(bid_ratios), 3)
                    if bid_ratios
                    else None
                ),
                "highest_bid_over_final_p75": (
                    round(statistics.quantiles(bid_ratios, n=4)[2], 3)
                    if len(bid_ratios) >= 4
                    else None
                ),
                "highest_bid_over_final_rate": (
                    round(over_final / usable_bid_rows, 4)
                    if usable_bid_rows
                    else None
                ),
                "stop_minus_final_median": (
                    _round(statistics.median(stop_minus_values))
                    if stop_minus_values
                    else None
                ),
            }
        )
    return out


def _q6_practical_gate_summary(
    rows: list[dict[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key) or "unknown"), []).append(row)

    out: list[dict[str, Any]] = []
    for value, group_rows in sorted(groups.items()):
        gated = [row for row in group_rows if row.get("q6_practical_gate_hit")]
        under_before = [
            row for row in gated
            if row.get("q6_practical_gate_under_before")
        ]
        out.append(
            {
                key: value,
                "n": len(group_rows),
                "gated_rows": len(gated),
                "under_before_rows": len(under_before),
                "helped_rows": sum(
                    1 for row in under_before
                    if row.get("q6_practical_gate_helped")
                ),
                "false_positive_proxy_rows": sum(
                    1 for row in gated
                    if row.get("q6_practical_gate_false_positive_proxy")
                ),
                "practical_p90_under_by_median": _median_value(
                    gated,
                    "q6_practical_p90_under_by",
                ),
            }
        )
    return out


def _q6_shadow_summary(
    rows: list[dict[str, Any]],
    key: str,
    *,
    prefix: str,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key) or "unknown"), []).append(row)

    out: list[dict[str, Any]] = []
    for value, group_rows in sorted(groups.items()):
        active = [
            row for row in group_rows
            if row.get(f"{prefix}_active")
        ]
        under_before = [
            row for row in active
            if row.get(f"{prefix}_under_before")
        ]
        out.append(
            {
                key: value,
                "n": len(group_rows),
                "active_rows": len(active),
                "under_before_rows": len(under_before),
                "helped_rows": sum(
                    1 for row in under_before
                    if row.get(f"{prefix}_helped")
                ),
                "false_positive_proxy_rows": sum(
                    1 for row in active
                    if row.get(f"{prefix}_false_positive_proxy")
                ),
                "q6_p90_delta_median": _median_value(
                    active,
                    f"{prefix}_q6_p90_delta",
                ),
            }
        )
    return out


def _q6_residual_boost_shadow_summary(
    rows: list[dict[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    return _q6_shadow_summary(
        rows,
        key,
        prefix="q6_residual_boost_shadow",
    )


def _q6_residual_deep_floor_shadow_summary(
    rows: list[dict[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    return _q6_shadow_summary(
        rows,
        key,
        prefix="q6_residual_deep_floor_shadow",
    )


def _q6_residual_hidden_floor_shadow_summary(
    rows: list[dict[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    return _q6_shadow_summary(
        rows,
        key,
        prefix="q6_residual_hidden_floor_shadow",
    )


def _q6_residual_villa_floor_shadow_summary(
    rows: list[dict[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    return _q6_shadow_summary(
        rows,
        key,
        prefix="q6_residual_villa_floor_shadow",
    )


def _collection_readiness(
    rows: list[dict[str, Any]],
    *,
    target_per_hero_family: int,
    hidden_target_per_hero: int,
    hidden_target_by_hero: dict[str, int] | None = None,
) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        hero = str(row.get("hero") or "unknown")
        family = _map_family(row.get("map_id"))
        groups.setdefault((hero, family), []).append(row)

    rows_out: list[dict[str, Any]] = []
    for hero in ("aisha", "ethan"):
        for family in ("villa", "shipwreck", "hidden"):
            target = (
                int((hidden_target_by_hero or {}).get(hero, hidden_target_per_hero))
                if family == "hidden"
                else target_per_hero_family
            )
            count = len(groups.get((hero, family), ()))
            rows_out.append(
                {
                    "hero": hero,
                    "map_family": family,
                    "n": count,
                    "target": target,
                    "needed": max(0, target - count),
                    "ready": count >= target,
                }
            )
    missing = sum(row["needed"] for row in rows_out)
    return {
        "target_per_hero_family": target_per_hero_family,
        "hidden_target_per_hero": hidden_target_per_hero,
        "hidden_target_by_hero": dict(hidden_target_by_hero or {}),
        "ready": missing == 0,
        "total_needed": missing,
        "groups": rows_out,
        "priority_needs": [
            row for row in rows_out
            if row["needed"] > 0
        ],
    }


def _next_sampling_targets(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(readiness.get("priority_needs") or [])
    rows.sort(
        key=lambda row: (
            0 if row.get("map_family") == "hidden" else 1,
            -int(row.get("needed") or 0),
            str(row.get("hero") or ""),
        )
    )
    out: list[dict[str, Any]] = []
    for row in rows[:6]:
        family = str(row.get("map_family") or "unknown")
        out.append(
            {
                "hero": row.get("hero"),
                "map_family": family,
                "needed": row.get("needed"),
                "reason": (
                    "hidden_cold_start"
                    if family == "hidden"
                    else "coverage_gap"
                ),
            }
        )
    return out


def _q6_shadow_sampling_progress_for_label(
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    label: str,
    sample_scope: str,
    targets_config: tuple[tuple[str, str, int], ...],
) -> dict[str, Any]:
    shadow_rows = [
        row
        for row in rows
        if row.get(label_key) == label
    ]
    counts = Counter(
        (
            str(row.get("hero") or "unknown"),
            _map_family(row.get("map_id")),
        )
        for row in shadow_rows
    )
    targets = [
        {
            "hero": hero,
            "map_family": family,
            "n": counts[(hero, family)],
            "target": target,
            "needed": max(0, target - counts[(hero, family)]),
            "ready": counts[(hero, family)] >= target,
        }
        for hero, family, target in targets_config
    ]
    return {
        "sample_scope": sample_scope,
        "tracked_rows": len(shadow_rows),
        "ready": all(row["ready"] for row in targets),
        "total_needed": sum(row["needed"] for row in targets),
        "targets": targets,
        "priority_needs": [row for row in targets if row["needed"] > 0],
    }


def _q6_shadow_sampling_progress(rows: list[dict[str, Any]]) -> dict[str, Any]:
    profile_b5 = _q6_shadow_sampling_progress_for_label(
        rows,
        label_key="q6_residual_boost_shadow_label",
        label="profile_b5",
        sample_scope="live_profile_b5_logs",
        targets_config=_Q6_SHADOW_SAMPLING_TARGETS,
    )
    aisha_deep_floor1 = _q6_shadow_sampling_progress_for_label(
        rows,
        label_key="q6_residual_deep_floor_shadow_label",
        label="aisha_deep_floor1",
        sample_scope="live_aisha_deep_floor1_logs",
        targets_config=_Q6_DEEP_FLOOR_SHADOW_SAMPLING_TARGETS,
    )
    aisha_hidden_floor15 = _q6_shadow_sampling_progress_for_label(
        rows,
        label_key="q6_residual_hidden_floor_shadow_label",
        label="aisha_hidden_floor15",
        sample_scope="live_aisha_hidden_floor15_logs",
        targets_config=_Q6_HIDDEN_FLOOR_SHADOW_SAMPLING_TARGETS,
    )
    aisha_villa_floor05 = _q6_shadow_sampling_progress_for_label(
        rows,
        label_key="q6_residual_villa_floor_shadow_label",
        label="aisha_villa_floor05",
        sample_scope="live_aisha_villa_floor05_logs",
        targets_config=_Q6_VILLA_FLOOR_SHADOW_SAMPLING_TARGETS,
    )
    return {
        **profile_b5,
        "candidates": {
            "profile_b5": profile_b5,
            "aisha_deep_floor1": aisha_deep_floor1,
            "aisha_hidden_floor15": aisha_hidden_floor15,
            "aisha_villa_floor05": aisha_villa_floor05,
        },
    }


def _q6_shadow_candidate_readiness(
    rows: list[dict[str, Any]],
    *,
    prefix: str,
    label_key: str,
    label: str,
    progress: dict[str, Any],
) -> dict[str, Any]:
    tracked = [
        row for row in rows
        if row.get(label_key) == label
    ]
    active = [
        row for row in tracked
        if row.get(f"{prefix}_active")
    ]
    active_no_q6 = [
        row for row in active
        if int(row.get("final_q6_value") or 0) <= 0
    ]
    under_before = [
        row for row in active
        if row.get(f"{prefix}_under_before")
    ]
    helped = [
        row for row in under_before
        if row.get(f"{prefix}_helped")
    ]
    still_missed = [
        row for row in under_before
        if not row.get(f"{prefix}_helped")
    ]
    false_positive = [
        row for row in active
        if row.get(f"{prefix}_false_positive_proxy")
    ]
    target_ready = bool(progress.get("ready"))
    if not target_ready:
        status = "needs_live_samples"
    elif false_positive:
        status = "blocked_false_positive"
    elif under_before and not helped:
        status = "no_observed_help"
    elif helped:
        status = "candidate_for_review"
    else:
        status = "monitoring"
    return {
        "label": label,
        "sample_scope": progress.get("sample_scope"),
        "status": status,
        "target_ready": target_ready,
        "target_total_needed": progress.get("total_needed"),
        "tracked_rows": len(tracked),
        "active_rows": len(active),
        "active_no_q6_rows": len(active_no_q6),
        "under_before_rows": len(under_before),
        "helped_rows": len(helped),
        "still_missed_rows": len(still_missed),
        "helped_rate": (
            round(len(helped) / len(under_before), 4)
            if under_before
            else None
        ),
        "still_missed_rate": (
            round(len(still_missed) / len(under_before), 4)
            if under_before
            else None
        ),
        "false_positive_proxy_rows": len(false_positive),
        "false_positive_proxy_rate_active": (
            round(len(false_positive) / len(active), 4)
            if active
            else None
        ),
        "false_positive_proxy_rate_active_no_q6": (
            round(len(false_positive) / len(active_no_q6), 4)
            if active_no_q6
            else None
        ),
        "q6_p90_delta_median": _median_value(active, f"{prefix}_q6_p90_delta"),
        "priority_needs": progress.get("priority_needs") or [],
    }


def _q6_shadow_candidate_readiness_summary(
    rows: list[dict[str, Any]],
    progress: dict[str, Any],
) -> dict[str, Any]:
    candidates = progress.get("candidates") or {}
    return {
        "profile_b5": _q6_shadow_candidate_readiness(
            rows,
            prefix="q6_residual_boost_shadow",
            label_key="q6_residual_boost_shadow_label",
            label="profile_b5",
            progress=candidates.get("profile_b5") or {},
        ),
        "aisha_deep_floor1": _q6_shadow_candidate_readiness(
            rows,
            prefix="q6_residual_deep_floor_shadow",
            label_key="q6_residual_deep_floor_shadow_label",
            label="aisha_deep_floor1",
            progress=candidates.get("aisha_deep_floor1") or {},
        ),
        "aisha_hidden_floor15": _q6_shadow_candidate_readiness(
            rows,
            prefix="q6_residual_hidden_floor_shadow",
            label_key="q6_residual_hidden_floor_shadow_label",
            label="aisha_hidden_floor15",
            progress=candidates.get("aisha_hidden_floor15") or {},
        ),
        "aisha_villa_floor05": _q6_shadow_candidate_readiness(
            rows,
            prefix="q6_residual_villa_floor_shadow",
            label_key="q6_residual_villa_floor_shadow_label",
            label="aisha_villa_floor05",
            progress=candidates.get("aisha_villa_floor05") or {},
        ),
    }


def _log_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "missing_hero": sum(1 for row in rows if not row.get("hero")),
        "missing_final_value": sum(1 for row in rows if row.get("final_value") is None),
        "missing_final_cells": sum(1 for row in rows if row.get("final_cells") is None),
        "missing_decision_value": sum(
            1 for row in rows if row.get("decision_value_p50") is None
        ),
        "missing_q6_truth_fields": sum(
            1 for row in rows if row.get("final_q6_value") is None
        ),
    }


def _monitor_error_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    type_counts: Counter[str] = Counter()
    fingerprint_keys: set[str] = set()
    latest: list[dict[str, Any]] = []
    for row in rows:
        error_type = str(row.get("error_type") or "unknown")
        type_counts[error_type] += 1
        fingerprint = row.get("fingerprint") or {}
        if isinstance(fingerprint, dict):
            key = "|".join(
                str(part)
                for part in (
                    row.get("path") or row.get("name") or "",
                    fingerprint.get("size"),
                    fingerprint.get("mtime_ns"),
                )
            )
        else:
            key = str(row.get("path") or row.get("name") or row.get("ts") or "")
        if key:
            fingerprint_keys.add(key)
        latest.append(
            {
                "ts": row.get("ts"),
                "name": row.get("name"),
                "error_type": error_type,
                "error": str(row.get("error") or "")[:240],
            }
        )
    latest.sort(key=lambda row: float(row.get("ts") or 0), reverse=True)
    return {
        "rows": len(rows),
        "unique_file_fingerprints": len(fingerprint_keys),
        "error_type_counts": dict(sorted(type_counts.items())),
        "latest": latest[:5],
    }


def summarize(
    rows: list[dict[str, Any]],
    *,
    dedupe: bool = True,
    target_per_hero_family: int = 30,
    hidden_target_per_hero: int = 10,
    hidden_target_by_hero: dict[str, int] | None = None,
    monitor_error_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    original_count = len(rows)
    if dedupe:
        rows = _dedupe_latest_by_file(rows)
    valid = [
        _with_derived_information_density(
            _with_derived_q6_fields(_with_derived_layout_root(row))
        )
        for row in rows
        if row.get("final_value") is not None or row.get("final_cells") is not None
    ]
    q6_truth = [row for row in valid if int(row.get("final_q6_value") or 0) > 0]
    collection_readiness = _collection_readiness(
        valid,
        target_per_hero_family=target_per_hero_family,
        hidden_target_per_hero=hidden_target_per_hero,
        hidden_target_by_hero=hidden_target_by_hero,
    )
    layout_conflict = [
        row for row in valid
        if row.get("layout_conflict") is True
    ]
    q6_p90_miss = [
        row for row in valid
        if row.get("q6_p90_misses_truth") is True
    ]
    q6_shadow_sampling_progress = _q6_shadow_sampling_progress(valid)
    return {
        "rows": len(rows),
        "raw_rows": original_count,
        "deduped_rows": original_count - len(rows),
        "valid": len(valid),
        "q6_truth_rows": len(q6_truth),
        "decision_value_mae": _mae(valid, "decision_value_p50_error"),
        "decision_value_median_abs_error": _median_abs(
            valid,
            "decision_value_p50_error",
        ),
        "raw_value_mae": _mae(valid, "value_p50_error"),
        "raw_ceiling_gap_median": _median_value(valid, "raw_minus_decision_p90"),
        "raw_ceiling_gap_p75": _p75_value(valid, "raw_minus_decision_p90"),
        "raw_ceiling_gap_250k_count": sum(
            1 for row in valid
            if (_numeric(row, "raw_minus_decision_p90") or 0) >= 250_000
        ),
        "raw_ceiling_gap_700k_count": sum(
            1 for row in valid
            if (_numeric(row, "raw_minus_decision_p90") or 0) >= 700_000
        ),
        "warehouse_mae": _mae(valid, "warehouse_p50_error"),
        "layout_fit_mae": _mae(valid, "layout_fit_p50_error"),
        "monitor_processing_seconds_median": _median_float_value(
            valid,
            "monitor_processing_seconds",
        ),
        "monitor_processing_seconds_p75": _p75_float_value(
            valid,
            "monitor_processing_seconds",
        ),
        "monitor_n_trials_values": _numeric_distribution(valid, "monitor_n_trials"),
        "monitor_shadow_trials_values": _numeric_distribution(
            valid,
            "monitor_shadow_trials",
        ),
        "monitor_roi_trials_values": _numeric_distribution(
            valid,
            "monitor_roi_trials",
        ),
        "category_target_rows": sum(
            1 for row in valid
            if (_numeric(row, "category_target_count") or 0) > 0
        ),
        "category_exclusion_rows": sum(
            1 for row in valid
            if (_numeric(row, "category_exclusion_count") or 0) > 0
        ),
        "category_target_total": sum(
            int(_numeric(row, "category_target_count") or 0)
            for row in valid
        ),
        "category_exclusion_total": sum(
            int(_numeric(row, "category_exclusion_count") or 0)
            for row in valid
        ),
        "log_quality": _log_quality(valid),
        "monitor_errors": _monitor_error_summary(monitor_error_rows or []),
        "collection_readiness": collection_readiness,
        "q6_shadow_sampling_progress": q6_shadow_sampling_progress,
        "q6_shadow_candidate_readiness": _q6_shadow_candidate_readiness_summary(
            valid,
            q6_shadow_sampling_progress,
        ),
        "next_sampling_targets": _next_sampling_targets(collection_readiness),
        "q6_false_low_count": sum(
            1 for row in valid if row.get("q6_false_low_risk") is True
        ),
        "q6_below_drop_prior_count": sum(
            1 for row in valid if row.get("q6_below_drop_prior") is True
        ),
        "q6_count_cell_prior_risk_count": sum(
            1 for row in valid if row.get("q6_count_cell_prior_risk") is True
        ),
        "q6_count_cell_prior_floor_median": _median_value(
            [
                row for row in valid
                if row.get("q6_count_cell_prior_risk") is True
            ],
            "q6_count_cell_prior_floor_value",
        ),
        "q6_practical_gate_count": sum(
            1 for row in valid if row.get("q6_practical_gate")
        ),
        "q6_practical_p90_median": _median_value(
            [
                row for row in valid
                if row.get("q6_practical_gate")
            ],
            "q6_practical_p90",
        ),
        "q6_practical_gate_under_before_count": sum(
            1 for row in valid if row.get("q6_practical_gate_under_before")
        ),
        "q6_practical_gate_helped_count": sum(
            1 for row in valid if row.get("q6_practical_gate_helped")
        ),
        "q6_practical_gate_false_positive_proxy_count": sum(
            1 for row in valid
            if row.get("q6_practical_gate_false_positive_proxy")
        ),
        "q6_practical_p90_under_by_median": _median_value(
            [
                row for row in valid
                if row.get("q6_practical_gate_hit")
            ],
            "q6_practical_p90_under_by",
        ),
        "q6_residual_boost_shadow_active_count": sum(
            1 for row in valid
            if row.get("q6_residual_boost_shadow_active")
        ),
        "q6_residual_boost_shadow_under_before_count": sum(
            1 for row in valid
            if row.get("q6_residual_boost_shadow_under_before")
        ),
        "q6_residual_boost_shadow_helped_count": sum(
            1 for row in valid
            if row.get("q6_residual_boost_shadow_helped")
        ),
        "q6_residual_boost_shadow_false_positive_proxy_count": sum(
            1 for row in valid
            if row.get("q6_residual_boost_shadow_false_positive_proxy")
        ),
        "q6_residual_boost_shadow_q6_p90_delta_median": _median_value(
            [
                row for row in valid
                if row.get("q6_residual_boost_shadow_active")
            ],
            "q6_residual_boost_shadow_q6_p90_delta",
        ),
        "q6_residual_deep_floor_shadow_active_count": sum(
            1 for row in valid
            if row.get("q6_residual_deep_floor_shadow_active")
        ),
        "q6_residual_deep_floor_shadow_under_before_count": sum(
            1 for row in valid
            if row.get("q6_residual_deep_floor_shadow_under_before")
        ),
        "q6_residual_deep_floor_shadow_helped_count": sum(
            1 for row in valid
            if row.get("q6_residual_deep_floor_shadow_helped")
        ),
        "q6_residual_deep_floor_shadow_false_positive_proxy_count": sum(
            1 for row in valid
            if row.get("q6_residual_deep_floor_shadow_false_positive_proxy")
        ),
        "q6_residual_deep_floor_shadow_q6_p90_delta_median": _median_value(
            [
                row for row in valid
                if row.get("q6_residual_deep_floor_shadow_active")
            ],
            "q6_residual_deep_floor_shadow_q6_p90_delta",
        ),
        "q6_residual_hidden_floor_shadow_active_count": sum(
            1 for row in valid
            if row.get("q6_residual_hidden_floor_shadow_active")
        ),
        "q6_residual_hidden_floor_shadow_under_before_count": sum(
            1 for row in valid
            if row.get("q6_residual_hidden_floor_shadow_under_before")
        ),
        "q6_residual_hidden_floor_shadow_helped_count": sum(
            1 for row in valid
            if row.get("q6_residual_hidden_floor_shadow_helped")
        ),
        "q6_residual_hidden_floor_shadow_false_positive_proxy_count": sum(
            1 for row in valid
            if row.get("q6_residual_hidden_floor_shadow_false_positive_proxy")
        ),
        "q6_residual_hidden_floor_shadow_q6_p90_delta_median": _median_value(
            [
                row for row in valid
                if row.get("q6_residual_hidden_floor_shadow_active")
            ],
            "q6_residual_hidden_floor_shadow_q6_p90_delta",
        ),
        "q6_residual_villa_floor_shadow_active_count": sum(
            1 for row in valid
            if row.get("q6_residual_villa_floor_shadow_active")
        ),
        "q6_residual_villa_floor_shadow_under_before_count": sum(
            1 for row in valid
            if row.get("q6_residual_villa_floor_shadow_under_before")
        ),
        "q6_residual_villa_floor_shadow_helped_count": sum(
            1 for row in valid
            if row.get("q6_residual_villa_floor_shadow_helped")
        ),
        "q6_residual_villa_floor_shadow_false_positive_proxy_count": sum(
            1 for row in valid
            if row.get("q6_residual_villa_floor_shadow_false_positive_proxy")
        ),
        "q6_residual_villa_floor_shadow_q6_p90_delta_median": _median_value(
            [
                row for row in valid
                if row.get("q6_residual_villa_floor_shadow_active")
            ],
            "q6_residual_villa_floor_shadow_q6_p90_delta",
        ),
        "q6_aisha_bottom_row_risk_count": sum(
            1 for row in valid if row.get("q6_aisha_bottom_row_risk")
        ),
        "q6_p90_miss_count": sum(
            1 for row in valid if row.get("q6_p90_misses_truth") is True
        ),
        "q6_p90_under_by_median": (
            _round(
                statistics.median(
                    int(row["v2_q6_value_p90_under_by"])
                    for row in q6_p90_miss
                    if row.get("v2_q6_value_p90_under_by") is not None
                )
            )
            if any(
                row.get("v2_q6_value_p90_under_by") is not None
                for row in q6_p90_miss
            )
            else None
        ),
        "q6_miss_root_causes": _root_cause_summary(
            q6_p90_miss,
            "q6_miss_root",
        ),
        "layout_conflict_count": sum(
            1 for row in valid if row.get("layout_conflict") is True
        ),
        "layout_conflict_root_causes": _root_cause_summary(
            layout_conflict,
            "layout_conflict_root",
        ),
        "relaxed_exact_count": sum(
            1 for row in valid if row.get("relaxed_exact_used") is True
        ),
        "groups": {
            "hero": _group_summary(valid, "hero"),
            "map_family": _group_summary(
                [
                    {
                        **row,
                        "map_family": _map_family(row.get("map_id")),
                    }
                    for row in valid
                ],
                "map_family",
            ),
            "map_id": _group_summary(valid, "map_id"),
            "evidence_stage": _group_summary(valid, "evidence_stage"),
            "information_density": _group_summary(valid, "information_density_band"),
            "hero_information_density": _group_summary(
                valid,
                "hero_information_density",
            ),
            "evidence_profile": _group_summary(valid, "evidence_profile_key"),
        },
        "bid_gap": {
            "hero": _bid_gap_summary(valid, "hero"),
            "map_family": _bid_gap_summary(
                [
                    {
                        **row,
                        "map_family": _map_family(row.get("map_id")),
                    }
                    for row in valid
                ],
                "map_family",
            ),
        },
        "q6_practical_gate": {
            "hero": _q6_practical_gate_summary(valid, "hero"),
            "hero_map_family": _q6_practical_gate_summary(
                [
                    {
                        **row,
                        "hero_map_family": (
                            f"hero={row.get('hero') or 'unknown'}|"
                            f"map_family={_map_family(row.get('map_id'))}"
                        ),
                    }
                    for row in valid
                ],
                "hero_map_family",
            ),
            "map_family": _q6_practical_gate_summary(
                [
                    {
                        **row,
                        "map_family": _map_family(row.get("map_id")),
                    }
                    for row in valid
                ],
                "map_family",
            ),
            "evidence_stage": _q6_practical_gate_summary(valid, "evidence_stage"),
            "information_density": _q6_practical_gate_summary(
                valid,
                "information_density_band",
            ),
        },
        "q6_residual_boost_shadow": {
            "hero": _q6_residual_boost_shadow_summary(valid, "hero"),
            "hero_map_family": _q6_residual_boost_shadow_summary(
                [
                    {
                        **row,
                        "hero_map_family": (
                            f"hero={row.get('hero') or 'unknown'}|"
                            f"map_family={_map_family(row.get('map_id'))}"
                        ),
                    }
                    for row in valid
                ],
                "hero_map_family",
            ),
            "map_family": _q6_residual_boost_shadow_summary(
                [
                    {
                        **row,
                        "map_family": _map_family(row.get("map_id")),
                    }
                    for row in valid
                ],
                "map_family",
            ),
            "evidence_stage": _q6_residual_boost_shadow_summary(
                valid,
                "evidence_stage",
            ),
            "information_density": _q6_residual_boost_shadow_summary(
                valid,
                "information_density_band",
            ),
        },
        "q6_residual_deep_floor_shadow": {
            "hero": _q6_residual_deep_floor_shadow_summary(valid, "hero"),
            "hero_map_family": _q6_residual_deep_floor_shadow_summary(
                [
                    {
                        **row,
                        "hero_map_family": (
                            f"hero={row.get('hero') or 'unknown'}|"
                            f"map_family={_map_family(row.get('map_id'))}"
                        ),
                    }
                    for row in valid
                ],
                "hero_map_family",
            ),
            "map_family": _q6_residual_deep_floor_shadow_summary(
                [
                    {
                        **row,
                        "map_family": _map_family(row.get("map_id")),
                    }
                    for row in valid
                ],
                "map_family",
            ),
            "evidence_stage": _q6_residual_deep_floor_shadow_summary(
                valid,
                "evidence_stage",
            ),
            "information_density": _q6_residual_deep_floor_shadow_summary(
                valid,
                "information_density_band",
            ),
        },
        "q6_residual_hidden_floor_shadow": {
            "hero": _q6_residual_hidden_floor_shadow_summary(valid, "hero"),
            "hero_map_family": _q6_residual_hidden_floor_shadow_summary(
                [
                    {
                        **row,
                        "hero_map_family": (
                            f"hero={row.get('hero') or 'unknown'}|"
                            f"map_family={_map_family(row.get('map_id'))}"
                        ),
                    }
                    for row in valid
                ],
                "hero_map_family",
            ),
            "map_family": _q6_residual_hidden_floor_shadow_summary(
                [
                    {
                        **row,
                        "map_family": _map_family(row.get("map_id")),
                    }
                    for row in valid
                ],
                "map_family",
            ),
            "evidence_stage": _q6_residual_hidden_floor_shadow_summary(
                valid,
                "evidence_stage",
            ),
            "information_density": _q6_residual_hidden_floor_shadow_summary(
                valid,
                "information_density_band",
            ),
        },
        "q6_residual_villa_floor_shadow": {
            "hero": _q6_residual_villa_floor_shadow_summary(valid, "hero"),
            "hero_map_family": _q6_residual_villa_floor_shadow_summary(
                [
                    {
                        **row,
                        "hero_map_family": (
                            f"hero={row.get('hero') or 'unknown'}|"
                            f"map_family={_map_family(row.get('map_id'))}"
                        ),
                    }
                    for row in valid
                ],
                "hero_map_family",
            ),
            "map_family": _q6_residual_villa_floor_shadow_summary(
                [
                    {
                        **row,
                        "map_family": _map_family(row.get("map_id")),
                    }
                    for row in valid
                ],
                "map_family",
            ),
            "evidence_stage": _q6_residual_villa_floor_shadow_summary(
                valid,
                "evidence_stage",
            ),
            "information_density": _q6_residual_villa_floor_shadow_summary(
                valid,
                "information_density_band",
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize live monitor model_eval.jsonl logs.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(ROOT / "data" / "logs" / "live" / "model_eval.jsonl"),
        help="Path to model_eval.jsonl",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Do not collapse duplicate rows with the same file name",
    )
    parser.add_argument(
        "--target-per-hero-family",
        type=int,
        default=30,
        help="Readiness target for each hero x map-family bucket",
    )
    parser.add_argument(
        "--hidden-target-per-hero",
        type=int,
        default=10,
        help="Fallback readiness target for each hero x hidden-auction bucket",
    )
    parser.add_argument(
        "--aisha-hidden-target",
        type=int,
        default=10,
        help="Readiness target for Aisha x hidden-auction",
    )
    parser.add_argument(
        "--ethan-hidden-target",
        type=int,
        default=5,
        help="Readiness target for Ethan x hidden-auction",
    )
    parser.add_argument(
        "--error-log",
        default=None,
        help=(
            "Path to monitor_errors.jsonl. Defaults to monitor_errors.jsonl next "
            "to the selected model_eval.jsonl."
        ),
    )
    args = parser.parse_args()
    path = Path(args.path)
    rows = _read_jsonl(path)
    error_log = Path(args.error_log) if args.error_log else path.with_name(
        "monitor_errors.jsonl"
    )
    monitor_errors = _read_jsonl(error_log)
    print(
        json.dumps(
            summarize(
                rows,
                dedupe=not args.no_dedupe,
                target_per_hero_family=args.target_per_hero_family,
                hidden_target_per_hero=args.hidden_target_per_hero,
                hidden_target_by_hero={
                    "aisha": args.aisha_hidden_target,
                    "ethan": args.ethan_hidden_target,
                },
                monitor_error_rows=monitor_errors,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
