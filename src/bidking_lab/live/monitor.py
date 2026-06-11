"""Live monitor artifact builder and append-only evaluation logs.

The monitor layer is intentionally source-agnostic: today it can process a
Fatbeans JSON payload or file; later a true realtime source can feed the same
``FatbeansCaptureEvents`` object without changing inference, logging, or UI.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
import json
import os
from pathlib import Path
import re
import statistics
import tempfile
import time
from typing import Any, Mapping, Sequence

from bidking_lab.config import project_root
from bidking_lab.extract.bid_map_table import BidMap, load_bid_map_table
from bidking_lab.extract.drop_table import DropPool, load_drop_table
from bidking_lab.extract.item_table import Item, load_item_table
from bidking_lab.inference.bid_strategy import recommend_bid_strategy
from bidking_lab.inference.diagnostics import layout_conflict_root
from bidking_lab.inference.size_avg_evidence import size_bucket_eval_fields
from bidking_lab.inference.q6_residual import (
    AISHA_BOTTOM_ROW_RISK_THRESHOLD,
    AISHA_Q6_QUALITY_ONLY_DEEP_ROW_THRESHOLD,
    actionable_random_sample_avg_values,
    aisha_bottom_row_risk,
    aisha_q6_quality_only_deep_local_risk,
    evidence_profile_key_from_problem,
    q6_conditional_target_active_for_profile,
    q6_quality_only_local_diagnostics,
    q6_residual_boost_for_profile,
    q6_residual_prior_floor_ratio_for_profile,
)
from bidking_lab.inference.v2 import (
    ResidualProblem,
    build_residual_problem,
    estimate_posterior_v2,
    evidence_store_from_fatbeans_events,
    is_tail_supported_by_evidence,
)
from bidking_lab.inference.v3 import (
    assess_prior_robustness,
    compile_feasible_summary,
    compile_hard_constraints,
    capacity_source_expansion_entry_for,
    empty_capacity_source_expansion_flat_dict,
    empty_feasible_summary_flat_dict,
    empty_formal_value_sampler_flat_dict,
    empty_posterior_flat_dict,
    empty_practical_advisory_flat_dict,
    empty_prior_calibration_flat_dict,
    empty_prior_flat_dict,
    empty_prior_robustness_flat_dict,
    empty_residual_gate_flat_dict,
    empty_settlement_count_prior_flat_dict,
    empty_tail_value_review_flat_dict,
    empty_underestimate_repair_flat_dict,
    estimate_shadow_pipeline,
    events_from_fatbeans,
    load_capacity_source_expansion_entries,
    load_prior_calibration_entries,
    load_settlement_count_prior_entries,
    load_tail_value_review_entries,
    load_underestimate_repair_entries,
    ordinary_shape_replacement_values,
    sample_truth_bank,
    summarize_drop_prior_flat_dict,
    settlement_count_prior_entry_for,
    tail_value_review_entry_for,
    underestimate_entry_for,
)
from bidking_lab.inference.map_likelihood import (
    QuantileSummary,
    estimate_map_likelihood,
)
from bidking_lab.inference.tool_info_roi import estimate_tool_info_roi
from bidking_lab.inference.warehouse_estimator import estimate_warehouse_cells
from bidking_lab.live.evaluation import evaluate_fatbeans_layout_events
from bidking_lab.live.fatbeans import (
    FatbeansCaptureEvents,
    latest_player_bids,
    parse_fatbeans_capture,
    parse_fatbeans_capture_payload,
)
from bidking_lab.live.layout import SAMPLE_FIT_LAYOUT_ESTIMATE_POLICY
from bidking_lab.live.layout import latest_grid_batch
from bidking_lab.live.replay import layout_replay_stages
from bidking_lab.live.state import (
    LiveSessionState,
    apply_observation_batch,
    live_state_to_session_obs,
)
from bidking_lab.live.types import GridItemObservation, LiveObservationBatch
from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events
from bidking_lab.runtime import (
    layout_replay_rows_from_stages,
    tactical_panel_from_rows,
    ui_contract_from_artifact,
)
from bidking_lab.simulation.robust_value import (
    DEFAULT_VALUE_FLOOR,
    is_confusable_long_tail,
)
from bidking_lab.simulation.basic_mc import flatten_pool

_CATEGORY_LABELS = {
    101: "家具",
    102: "医疗",
    103: "时尚",
    104: "武器",
    105: "珠宝",
    106: "古董",
    107: "数码",
    108: "能源",
    109: "食饮",
    110: "书画",
}
DEFAULT_Q6_SHADOW_TRIALS_CAP = 80
LIVE_FORMAL_MODE_ENV = "BIDKING_LIVE_FORMAL_MODE"
LIVE_FORMAL_MODE_V2 = "v2"
LIVE_FORMAL_MODE_V3_PRACTICAL = "v3_practical"
_LIVE_FORMAL_MODE_ALIASES = {
    "v2": LIVE_FORMAL_MODE_V2,
    "baseline": LIVE_FORMAL_MODE_V2,
    "baseline_v2": LIVE_FORMAL_MODE_V2,
    "v3": LIVE_FORMAL_MODE_V3_PRACTICAL,
    "v3_practical": LIVE_FORMAL_MODE_V3_PRACTICAL,
    "v3-practical": LIVE_FORMAL_MODE_V3_PRACTICAL,
    "practical": LIVE_FORMAL_MODE_V3_PRACTICAL,
}
_LIVE_V3_PRIOR_ONLY_RAISE_GUARD_CONFIDENCES = {"low", "low_medium"}
_LIVE_V3_PRIOR_ONLY_RAISE_GUARD_FLAGS = {
    "q6_prior_floor_watch",
    "q6_prior_tail_ceiling",
    "settlement_count_prior_candidate",
    "capacity_source_candidate",
}
_LIVE_V3_STRONG_RAISE_EVIDENCE_FLAGS = {
    "value_floor_candidate",
    "underestimate_repair_candidate",
    "tail_value_candidate",
    "random_avg_value_floor_watch",
    "random_avg_high_signal_ceiling",
    "q6_value_ceiling_watch",
    "source_profile_q6_tail_ceiling",
}
_LIVE_V3_PRIOR_ONLY_RAISE_GUARD_MIN_GAP = 100_000.0
_LIVE_V3_PRIOR_ONLY_RAISE_GUARD_MAX_P50_MULTIPLIER = 1.25
_LIVE_V3_PRIOR_ONLY_RAISE_GUARD_MIN_HEADROOM = 75_000.0
_LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_MAX_ESS = 5.0
_LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_MIN_P50_GAP = 180_000.0
_LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_P50_KEEP_RATIO = 0.70
_LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_MIN_HEADROOM = 75_000.0
_LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_P90_MULTIPLIER = 1.35
_LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_P90_HEADROOM = 150_000.0
_TRUSTED_SESSION_TOTAL_CONFIDENCES = {"high", "exact"}
_SAFE_SESSION_TOTAL_FIELDS = (
    "warehouse_total_cells",
    "warehouse_total_cells_approx",
    "warehouse_total_cells_tolerance",
    "total_item_count",
)
_V3_PRIOR_CALIBRATION_CACHE: dict[int, Any] | None = None
_V3_UNDERESTIMATE_REPAIR_CACHE: dict[tuple[str, int], Any] | None = None
_V3_TAIL_VALUE_REVIEW_CACHE: dict[tuple[str, int], Any] | None = None
_V3_SETTLEMENT_COUNT_PRIOR_CACHE: dict[tuple[str, str], Any] | None = None
_V3_CAPACITY_SOURCE_EXPANSION_CACHE: dict[tuple[str, str], Any] | None = None


@dataclass(frozen=True)
class MonitorTables:
    """Loaded local game tables used by live monitor inference."""

    maps: Mapping[int, BidMap]
    drops: Mapping[int, DropPool]
    items: Mapping[int, Item]


def load_monitor_tables(
    *,
    tables_dir: str | Path | None = None,
) -> MonitorTables:
    """Load raw game tables from ``data/raw/tables`` or an explicit folder."""
    root = Path(tables_dir) if tables_dir is not None else (
        project_root() / "data" / "raw" / "tables"
    )
    return MonitorTables(
        maps=load_bid_map_table(root / "BidMap.txt"),
        drops=load_drop_table(root / "Drop.txt"),
        items=load_item_table(root / "Item.txt"),
    )


def _format_quantile_interval(summary: Any) -> str:
    if summary is None:
        return ""
    return f"{summary.p10:,.0f} / {summary.p50:,.0f} / {summary.p90:,.0f}"


def _format_quantile_interval_float(summary: Any, digits: int = 2) -> str:
    if summary is None:
        return ""
    return (
        f"{summary.p10:.{digits}f} / "
        f"{summary.p50:.{digits}f} / "
        f"{summary.p90:.{digits}f}"
    )


def _format_quantile_width(summary: Any) -> str:
    if summary is None:
        return ""
    return f"{summary.p90 - summary.p10:,.0f}"


def _raw_ceiling_risk_label(decision_summary: Any, raw_summary: Any) -> str:
    if decision_summary is None or raw_summary is None:
        return ""
    decision_p90 = getattr(decision_summary, "p90", None)
    raw_p90 = getattr(raw_summary, "p90", None)
    if decision_p90 is None or raw_p90 is None:
        return ""
    gap = int(round(raw_p90 - decision_p90))
    if gap <= 0:
        return "低"
    baseline = max(float(decision_p90), 1.0)
    ratio = gap / baseline
    if gap >= 700_000 or ratio >= 1.0:
        level = "高"
    elif gap >= 250_000 or ratio >= 0.45:
        level = "中"
    else:
        level = "低"
    return f"{level} / raw P90 +{gap:,.0f}"


def _candidate_map_ids_for_likelihood(
    map_id: int,
    maps: Mapping[int, BidMap],
) -> tuple[int, ...]:
    if map_id in maps:
        return (map_id,)
    return (map_id,)


def _activity_shipwreck_alias(
    map_id: Any,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
) -> dict[str, Any]:
    try:
        source_map_id = int(map_id)
    except (TypeError, ValueError):
        return {}
    source_map = maps.get(source_map_id)
    if source_map is not None and source_map.drop_pool_id in drops:
        return {}
    candidates: list[tuple[str, int]] = []
    if 2521 <= source_map_id <= 2530:
        candidates.append(("activity_shipwreck_minus20", source_map_id - 20))
        candidates.append(("activity_shipwreck_minus10", source_map_id - 10))
    elif 4521 <= source_map_id <= 4530:
        candidates.append(("activity_shipwreck_45xx_minus20", source_map_id - 20))
        candidates.append(("activity_shipwreck_45xx_minus10", source_map_id - 10))
    for mode, model_map_id in candidates:
        if model_map_id in maps and _map_family_from_id(model_map_id) == "shipwreck":
            return {
                "mode": mode,
                "source_map_id": source_map_id,
                "model_map_id": model_map_id,
                "family": "shipwreck",
                "confidence": "temporary_activity_alias",
                "reason": (
                    "missing_activity_drop_use_corresponding_old_shipwreck"
                    if source_map is not None
                    else "missing_activity_bidmap_use_corresponding_old_shipwreck"
                ),
                "candidate_model_map_ids": [
                    candidate
                    for _candidate_mode, candidate in candidates
                    if candidate in maps
                ],
            }
    return {}


def _relax_exact_bucket_constraints(obs: Any) -> Any:
    buckets = {}
    changed = False
    for quality, bucket in obs.buckets.items():
        total_cells_min = bucket.total_cells_min
        count_min = bucket.count_min
        if bucket.total_cells is not None:
            total_cells_min = max(total_cells_min or 0, bucket.total_cells)
            changed = True
        if bucket.count is not None:
            count_min = max(count_min or 0, bucket.count)
            changed = True
        buckets[quality] = replace(
            bucket,
            total_cells=None,
            count=None,
            total_cells_min=total_cells_min,
            count_min=count_min,
        )
    if not changed:
        return obs
    return replace(obs, buckets=buckets)


def _zero_match_fallback_session(obs: Any) -> Any:
    buckets = {}
    for quality, bucket in obs.buckets.items():
        if quality == 6 and (bucket.total_cells == 0 or bucket.count == 0):
            buckets[quality] = replace(
                bucket,
                total_cells=0,
                count=0,
                total_cells_min=0,
                count_min=0,
                value_sum=None,
                avg_value=None,
                value_range=None,
                huge_band="none",
                huge_cells_override=0,
            )
    return replace(
        obs,
        warehouse_total_cells=None,
        warehouse_total_cells_approx=None,
        warehouse_total_cells_tolerance=None,
        total_item_count=None,
        buckets=buckets,
        visible_outline_item_count_min=None,
        visible_outline_total_cells_min=None,
        visible_outline_bottom_row_min=None,
        category_items=(),
    )


def _map_likelihood_result_rows(
    results: Sequence[Any],
    label: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in results[:5]:
        rows.append(
            {
                "证据": label,
                "地图": f"{result.map_id} {result.map_name}",
                "匹配": f"{result.n_matched}/{result.n_total}",
                "后验": f"{result.posterior_probability:.1%}",
                "总格 P10/P50/P90": _format_quantile_interval(result.total_cells),
                "价值 P10/P50/P90": _format_quantile_interval(result.total_value),
            }
        )
    return rows


def _warehouse_estimate_rows(estimate: Any) -> list[dict[str, Any]]:
    if estimate is None:
        return []
    rows = [
        {
            "范围": "跨候选地图汇总",
            "匹配": f"{estimate.n_matched}/{estimate.n_total}",
            "置信度": estimate.confidence,
            "总格 P10/P50/P90": _format_quantile_interval(estimate.total_cells),
            "价值 P10/P50/P90": _format_quantile_interval(estimate.total_value),
            "说明": estimate.reason,
        }
    ]
    for row in estimate.map_contributions[:5]:
        rows.append(
            {
                "范围": f"{row.map_id} {row.map_name}",
                "匹配": f"{row.n_matched}/{row.n_total}",
                "置信度": f"地图后验 {row.posterior_probability:.1%}",
                "总格 P10/P50/P90": _format_quantile_interval(row.total_cells),
                "价值 P10/P50/P90": "",
                "说明": "",
            }
        )
    return rows


def _v2_posterior_rows(
    report: Any,
    *,
    q6_prior_gap: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if report is None:
        return []
    diagnostics = ";".join(getattr(report, "diagnostics", ()) or ())
    if q6_prior_gap is None:
        q6_prior_gap = _q6_prior_gap_summary(report)
    return [
        {
            "范围": f"{report.map_id} {report.map_name}",
            "匹配": f"{report.n_matched}/{report.n_total}",
            "价值口径": "decision_value",
            "决策价值 P10/P50/P90": _format_quantile_interval(report.decision_value),
            "替代决策价值 P10/P50/P90": _format_quantile_interval(
                getattr(report, "tail_replacement_decision_value", None)
            ),
            "原始价值 P10/P50/P90": _format_quantile_interval(report.total_value),
            "先验件数": (
                f"{report.prior_expected_count:.2f}"
                if getattr(report, "prior_expected_count", None) is not None
                else ""
            ),
            "先验格数": (
                f"{report.prior_expected_cells:.1f}"
                if getattr(report, "prior_expected_cells", None) is not None
                else ""
            ),
            "先验原始价值": (
                f"{report.prior_expected_value:,.0f}"
                if getattr(report, "prior_expected_value", None) is not None
                else ""
            ),
            "先验决策价值": (
                f"{report.prior_expected_decision_value:,.0f}"
                if getattr(report, "prior_expected_decision_value", None) is not None
                else ""
            ),
            "先验替代决策价值": (
                f"{report.prior_expected_tail_replacement_decision_value:,.0f}"
                if getattr(
                    report,
                    "prior_expected_tail_replacement_decision_value",
                    None,
                )
                is not None
                else ""
            ),
            "q6价值 P10/P50/P90": _format_quantile_interval(report.q6_value),
            "q6决策价值 P10/P50/P90": _format_quantile_interval(
                getattr(report, "q6_decision_value", None)
            ),
            "q6替代决策价值 P10/P50/P90": _format_quantile_interval(
                getattr(report, "q6_tail_replacement_decision_value", None)
            ),
            "q6件数 P10/P50/P90": _format_quantile_interval(
                getattr(report, "q6_count", None)
            ),
            "q6格数 P10/P50/P90": _format_quantile_interval(
                getattr(report, "q6_cells", None)
            ),
            "剩余空间 P10/P50/P90": _format_quantile_interval(
                getattr(report, "remaining_cells_after_layout", None)
            ),
            "q6空间压力 P10/P50/P90": _format_quantile_interval_float(
                getattr(report, "q6_space_pressure", None)
            ),
            "q6空间溢出率": (
                f"{report.q6_space_overflow_rate:.1%}"
                if getattr(report, "q6_space_overflow_rate", None) is not None
                else ""
            ),
            "q6样本率": (
                f"{report.q6_match_rate:.1%}"
                if report.q6_match_rate is not None
                else ""
            ),
            "q6掉落先验": (
                f"{report.q6_prior_match_rate:.1%}"
                if report.q6_prior_match_rate is not None
                else ""
            ),
            "q6先验件数": (
                f"{report.q6_prior_expected_count:.2f}"
                if getattr(report, "q6_prior_expected_count", None) is not None
                else ""
            ),
            "q6先验格数": (
                f"{report.q6_prior_expected_cells:.1f}"
                if getattr(report, "q6_prior_expected_cells", None) is not None
                else ""
            ),
            "q6先验价值": (
                f"{report.q6_prior_expected_value:,.0f}"
                if report.q6_prior_expected_value is not None
                else ""
            ),
            "q6先验缺口": q6_prior_gap["summary"],
            "q6先验风险参考": (
                f"{q6_prior_gap['floor_value']:,.0f}"
                if q6_prior_gap["floor_value"] is not None
                else ""
            ),
            "q6先验风险": "是" if q6_prior_gap["risk"] else "",
            "q6实战门控": q6_prior_gap["gate"],
            "q6实战参考P90": (
                f"{q6_prior_gap['practical_p90']:,.0f}"
                if q6_prior_gap["practical_p90"] is not None
                else ""
            ),
            "锚点数": getattr(report, "anchor_count", 0),
            "形状约束数": getattr(report, "shape_target_count", 0),
            "分类约束数": getattr(report, "category_target_count", 0),
            "分类反排数": getattr(report, "category_exclusion_count", 0),
            "随机样本均价": ";".join(
                f"n={sample_count}:avg={value:.2f}"
                for sample_count, value in getattr(
                    report,
                    "random_sample_avg_values",
                    (),
                )
            ),
            "随机样本均价信号": ";".join(
                f"n={sample_count}:avg={value:.2f}"
                for sample_count, value in actionable_random_sample_avg_values(
                    getattr(report, "random_sample_avg_values", ())
                )
            ),
            "诊断": diagnostics,
        }
    ]


def _q6_prior_gap_summary(report: Any) -> dict[str, Any]:
    parts: list[str] = []
    count_gap = _quantile_prior_gap(
        getattr(report, "q6_count", None),
        getattr(report, "q6_prior_expected_count", None),
    )
    cells_gap = _quantile_prior_gap(
        getattr(report, "q6_cells", None),
        getattr(report, "q6_prior_expected_cells", None),
    )
    if count_gap is not None and count_gap >= 0.25:
        parts.append(f"件数P90低{count_gap:.2f}")
    if cells_gap is not None and cells_gap >= 1.0:
        parts.append(f"格数P90低{cells_gap:.1f}")
    prior_gap_active = bool(parts)
    random_sample_signals = actionable_random_sample_avg_values(
        getattr(report, "random_sample_avg_values", ())
    )
    random_sample_floor = max(
        (
            int(round(float(sample_count) * float(value)))
            for sample_count, value in random_sample_signals
        ),
        default=None,
    )
    for sample_count, value in random_sample_signals:
        parts.append(f"随机{sample_count}件均价高{float(value):,.0f}")
    prior_floor = (
        getattr(report, "q6_prior_expected_value", None)
        if prior_gap_active
        else None
    )
    floor_candidates = [
        float(value)
        for value in (prior_floor, random_sample_floor)
        if value is not None
    ]
    floor_value = max(floor_candidates) if floor_candidates else None
    gate_parts: list[str] = []
    if prior_gap_active and _map_family_from_id(getattr(report, "map_id", None)) == "shipwreck":
        gate_parts.append("shipwreck_positive_net")
    if random_sample_signals:
        gate_parts.append("random_avg_signal")
    gate = "+".join(gate_parts)
    decision_p90 = _quantile_p90(getattr(report, "q6_decision_value", None))
    return {
        "risk": bool(parts),
        "summary": "；".join(parts),
        "floor_value": floor_value,
        "gate": gate,
        "practical_p90": (
            max(float(decision_p90 or 0), float(floor_value or 0))
            if floor_value is not None
            else None
        ),
    }


def _q6_risk_reference_text(q6_prior_gap: Mapping[str, Any] | None) -> str:
    if not q6_prior_gap or not q6_prior_gap.get("risk"):
        return ""
    parts = [str(q6_prior_gap.get("summary") or "").strip()]
    reference = q6_prior_gap.get("practical_p90")
    if reference is None:
        reference = q6_prior_gap.get("floor_value")
    if reference is not None:
        parts.append(f"参考P90 {float(reference):,.0f}")
    gate = str(q6_prior_gap.get("gate") or "").strip()
    if gate:
        parts.append(f"门控 {gate}")
    parts.append("q6单项风险只作参考；正式停止价由当前 formal_mode 统一重算")
    return "；".join(part for part in parts if part)


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _q6_reference_with_shadow(
    q6_prior_gap: Mapping[str, Any],
    *shadows: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(q6_prior_gap)
    summary_parts = [
        part
        for part in str(merged.get("summary") or "").split("；")
        if part.strip()
    ]
    gate_parts = [
        part
        for part in str(merged.get("gate") or "").split("+")
        if part.strip()
    ]
    practical_values = [
        value
        for value in (
            _float_or_none(merged.get("practical_p90")),
            _float_or_none(merged.get("floor_value")),
        )
        if value is not None
    ]
    for shadow in shadows:
        if not shadow or not shadow.get("active"):
            continue
        q6_p90 = _float_or_none(shadow.get("q6_decision_value_p90"))
        if q6_p90 is None or q6_p90 <= 0:
            continue
        label = str(shadow.get("label") or "").strip()
        gate = str(shadow.get("gate") or "").strip()
        summary = f"{label or gate or 'shadow'} q6P90 {q6_p90:,.0f}"
        summary_parts.append(summary)
        gate_parts.append(gate or label or "shadow")
        practical_values.append(q6_p90)
    merged["summary"] = "；".join(dict.fromkeys(summary_parts))
    merged["gate"] = "+".join(dict.fromkeys(gate_parts))
    if practical_values:
        merged["practical_p90"] = max(practical_values)
    merged["risk"] = bool(merged.get("risk") or practical_values)
    return merged


def _quantile_value(summary: Any, name: str) -> int | None:
    if summary is None:
        return None
    value = getattr(summary, name, None)
    if value is None:
        return None
    return int(round(float(value)))


def _q6_residual_boost_shadow_summary(
    report: Any | None,
    *,
    label: str,
    requested_boost: float,
    active_boost: float,
    gate: str,
    evidence_profile_key: str,
    trials: int,
    requested_prior_floor_ratio: float = 0.0,
    active_prior_floor_ratio: float = 0.0,
    requested_conditional_target_count: float = 0.0,
    active_conditional_target_count: float = 0.0,
    requested_conditional_target_cells: float = 0.0,
    active_conditional_target_cells: float = 0.0,
    requested_conditional_value_power: float = 0.0,
    active_conditional_value_power: float = 0.0,
) -> dict[str, Any]:
    active_conditional_target = (
        active_conditional_target_count > 0.0
        or active_conditional_target_cells > 0.0
    )
    return {
        "label": label,
        "gate": gate,
        "requested_boost": requested_boost,
        "active_boost": active_boost,
        "requested_prior_floor_ratio": requested_prior_floor_ratio,
        "active_prior_floor_ratio": active_prior_floor_ratio,
        "requested_conditional_target_count": requested_conditional_target_count,
        "active_conditional_target_count": active_conditional_target_count,
        "requested_conditional_target_cells": requested_conditional_target_cells,
        "active_conditional_target_cells": active_conditional_target_cells,
        "requested_conditional_value_power": requested_conditional_value_power,
        "active_conditional_value_power": active_conditional_value_power,
        "active": (
            active_boost > 1.0
            or active_prior_floor_ratio > 0.0
            or active_conditional_target
        ),
        "trials": trials,
        "evidence_profile_key": evidence_profile_key,
        "n_matched": getattr(report, "n_matched", None),
        "n_total": getattr(report, "n_total", None),
        "decision_value_p50": _quantile_value(
            getattr(report, "decision_value", None),
            "p50",
        ),
        "decision_value_p90": _quantile_value(
            getattr(report, "decision_value", None),
            "p90",
        ),
        "q6_decision_value_p90": _quantile_value(
            getattr(report, "q6_decision_value", None),
            "p90",
        ),
        "q6_count_p90": _quantile_value(getattr(report, "q6_count", None), "p90"),
        "q6_cells_p90": _quantile_value(getattr(report, "q6_cells", None), "p90"),
        "diagnostics": ";".join(getattr(report, "diagnostics", ()) or ()),
    }


def _q6_residual_shadow_rows(
    shadows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for shadow in shadows:
        if not shadow:
            continue
        rows.append(
            {
                "策略": shadow.get("label") or "",
                "门控": shadow.get("gate") or "",
                "激活": "是" if shadow.get("active") else "",
                "boost": shadow.get("active_boost"),
                "prior floor": shadow.get("active_prior_floor_ratio"),
                "target count": shadow.get("active_conditional_target_count"),
                "target cells": shadow.get("active_conditional_target_cells"),
                "value power": shadow.get("active_conditional_value_power"),
                "trials": shadow.get("trials"),
                "证据profile": shadow.get("evidence_profile_key") or "",
                "匹配": (
                    f"{shadow.get('n_matched')}/{shadow.get('n_total')}"
                    if shadow.get("n_total") is not None
                    else ""
                ),
                "q6决策P90": shadow.get("q6_decision_value_p90"),
                "q6件数P90": shadow.get("q6_count_p90"),
                "q6格数P90": shadow.get("q6_cells_p90"),
            }
        )
    return rows


def _map_family_from_id(map_id: Any) -> str:
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


def _live_information_density_score(
    round_no: Any,
    *,
    anchor_count: Any,
    shape_target_count: Any,
    category_target_count: Any,
    category_exclusion_count: Any,
) -> int:
    try:
        round_value = int(round_no)
    except (TypeError, ValueError):
        round_value = 0
    evidence_count = sum(
        _safe_int(value)
        for value in (
            anchor_count,
            shape_target_count,
            category_target_count,
            category_exclusion_count,
        )
    )
    return round_value * 2 + min(evidence_count, 6) * 2


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _information_density_band(score: int | None) -> str:
    if score is None:
        return "unknown"
    if score < 18:
        return "low"
    if score < 34:
        return "medium"
    return "high"


def _public_constraint_key(diagnostics: str) -> str:
    parts: list[str] = []
    if "public_max_quality:" in diagnostics:
        parts.append("max_quality")
    if "public_max_item_cells:" in diagnostics:
        parts.append("max_item_cells")
    return "+".join(parts) if parts else "none"


def _diagnostic_int(diagnostics: str, name: str) -> int | None:
    match = re.search(rf"(?:^|;){re.escape(name)}:(-?\d+)", diagnostics)
    if not match:
        return None
    return int(match.group(1))


def _zero_q6_proven_from_diagnostics(diagnostics: str) -> bool:
    max_quality = _diagnostic_int(diagnostics, "public_max_quality")
    return max_quality is not None and max_quality < 6


def _live_evidence_profile_key(
    *,
    public_constraint_key: str,
    random_sample_avg_values: str,
    category_target_count: Any,
    category_exclusion_count: Any,
    shape_target_count: Any,
) -> str:
    parts: list[str] = []
    if public_constraint_key != "none":
        parts.append(f"public:{public_constraint_key}")
    if random_sample_avg_values:
        parts.append("public:random_avg")
    if _safe_int(category_target_count) + _safe_int(category_exclusion_count) > 0:
        parts.append("tool:category")
    if _safe_int(shape_target_count) > 0:
        parts.append("shape")
    return "+".join(parts) if parts else "basic"


def _quantile_p90(quantile: Any) -> float | None:
    if quantile is None:
        return None
    p90 = getattr(quantile, "p90", None)
    if p90 is None:
        return None
    return float(p90)


def _quantile_prior_gap(quantile: Any, prior: Any) -> float | None:
    if quantile is None or prior is None:
        return None
    p90 = getattr(quantile, "p90", None)
    if p90 is None:
        return None
    return max(0.0, float(prior) - float(p90))


def _tool_info_roi_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows[:8]:
        out.append(
            {
                "道具": row.tool_name,
                "价格": f"{row.silver_cost:,}",
                "匹配样本": row.n_matched,
                "价值区间压缩": f"{row.value_width_gain:,.0f}",
                "仓储区间压缩": f"{row.cells_width_gain:,.0f}",
                "信息ROI": f"{row.roi_value:.2f}",
                "说明": row.note,
            }
        )
    return out


def _brief_layout_stage_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int = 4,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows[:limit]:
        estimate = row.get("样本拟合估计") or row.get("布局估计", "")
        confidence = row.get("样本拟合置信") or row.get("估计置信", "")
        out.append(
            {
                "阶段": f"R{row.get('R') or '?'} / sort {row.get('sort')}",
                "已知格": row.get("已知格", ""),
                "覆盖": row.get("已知覆盖", ""),
                "最深行": row.get("最深行", ""),
                "布局估计": estimate,
                "置信": confidence,
                "风险": row.get("风险", ""),
            }
        )
    return out


def _states_to_session(
    batches: Sequence[LiveObservationBatch],
) -> tuple[Any | None, Any | None, LiveSessionState, LiveSessionState]:
    final_state = LiveSessionState()
    pre_settlement_state = LiveSessionState()
    saw_pre_settlement = False
    for batch in batches:
        final_state = apply_observation_batch(final_state, batch)
        if batch.phase != "settled":
            pre_settlement_state = apply_observation_batch(
                pre_settlement_state,
                batch,
            )
            saw_pre_settlement = True
    base_session = (
        live_state_to_session_obs(pre_settlement_state)
        if saw_pre_settlement
        else None
    )
    if base_session is None:
        base_session = live_state_to_session_obs(final_state)
    return (
        base_session,
        live_state_to_session_obs(final_state),
        pre_settlement_state,
        final_state,
    )


def _trusted_pre_settlement_session_totals(
    state: LiveSessionState,
) -> dict[str, dict[str, Any]]:
    constraints: dict[str, dict[str, Any]] = {}
    for field in _SAFE_SESSION_TOTAL_FIELDS:
        observed = state.fields.get(("session", field))
        if observed is None:
            continue
        if observed.confidence not in _TRUSTED_SESSION_TOTAL_CONFIDENCES:
            continue
        value = _parse_int_text(observed.value)
        if value is None:
            continue
        constraints[field] = {
            "value": value,
            "source": observed.source,
            "confidence": observed.confidence,
            "sequence": observed.sequence,
        }
    return constraints


def _inference_session_with_safe_totals(
    base_session: Any,
    pre_settlement_state: LiveSessionState,
) -> tuple[Any, dict[str, Any]]:
    constraints = _trusted_pre_settlement_session_totals(pre_settlement_state)
    session = replace(
        base_session,
        warehouse_total_cells=(
            constraints.get("warehouse_total_cells", {}).get("value")
        ),
        warehouse_total_cells_approx=(
            constraints.get("warehouse_total_cells_approx", {}).get("value")
        ),
        warehouse_total_cells_tolerance=(
            constraints.get("warehouse_total_cells_tolerance", {}).get("value")
        ),
        total_item_count=constraints.get("total_item_count", {}).get("value"),
    )
    return (
        session,
        {
            "mode": (
                "pre_settlement_trusted_totals"
                if constraints
                else "session_totals_stripped"
            ),
            **constraints,
        },
    )


def _inventory_value(events: FatbeansCaptureEvents, items: Mapping[int, Item]) -> int | None:
    for state in reversed(events.states):
        if not state.inventory_items:
            continue
        total = 0
        for inv_item in state.inventory_items:
            item = items.get(inv_item.item_id)
            if item is not None:
                total += item.value
        return total
    return None


def _latest_round(events: FatbeansCaptureEvents) -> int | None:
    for state in reversed(events.states):
        if state.round_no is not None:
            return state.round_no
    return None


def _latest_state(events: FatbeansCaptureEvents) -> Any:
    return events.states[-1] if events.states else None


def _latest_phase(events: FatbeansCaptureEvents) -> str:
    state = _latest_state(events)
    if state is None:
        return "unknown"
    if state.message_id == 0x002D or state.inventory_items:
        return "settled"
    if state.message_id == 0x0021:
        return "reading"
    return "bidding"


def _action_round(events: FatbeansCaptureEvents) -> int | None:
    """Return the in-game round the user is about to act on.

    Packet round indices in ``0x0025`` are completed/revealed rounds. During
    bidding, the actionable UI has already advanced to the next round.
    """
    state = _latest_state(events)
    if state is None:
        return None
    if state.message_id == 0x002D or state.inventory_items:
        sent_bid_count = sum(1 for send in events.sends if send.kind == "bid")
        candidates = [
            candidate
            for candidate in (state.round_no, sent_bid_count or None)
            if candidate is not None
        ]
        return max(candidates) if candidates else None
    if state.message_id == 0x0021:
        return 1
    if state.round_no is None:
        sent_bid_count = sum(1 for send in events.sends if send.kind == "bid")
        return sent_bid_count + 1
    return state.round_no + 1


def _latest_map_id(events: FatbeansCaptureEvents) -> int | None:
    for state in reversed(events.states):
        if state.map_id is not None:
            return state.map_id
    return None


def _latest_session_id(events: FatbeansCaptureEvents) -> str | None:
    for state in reversed(events.states):
        if state.session_id:
            return state.session_id
    return None


def _inventory_totals(events: FatbeansCaptureEvents) -> tuple[int | None, int | None]:
    for state in reversed(events.states):
        if state.inventory_items:
            return len(state.inventory_items), sum(item.cells for item in state.inventory_items)
    return None, None


def _resolve_live_formal_mode(value: str | None = None) -> str:
    raw = value if value is not None else os.environ.get(
        LIVE_FORMAL_MODE_ENV,
        LIVE_FORMAL_MODE_V2,
    )
    text = str(raw or LIVE_FORMAL_MODE_V2).strip().casefold()
    text = text.replace("-", "_")
    return _LIVE_FORMAL_MODE_ALIASES.get(text, LIVE_FORMAL_MODE_V3_PRACTICAL)


def _summary_from_flat_quantiles(
    row: Mapping[str, Any],
    prefix: str,
) -> QuantileSummary | None:
    p10 = _parse_float_text(row.get(f"{prefix}_p10"))
    p50 = _parse_float_text(row.get(f"{prefix}_p50"))
    p90 = _parse_float_text(row.get(f"{prefix}_p90"))
    if p10 is None or p50 is None or p90 is None:
        return None
    return QuantileSummary(p10=float(p10), p50=float(p50), p90=float(p90))


def _v3_flag_set(value: Any) -> set[str]:
    text = str(value or "").strip()
    if not text:
        return set()
    return {part for part in re.split(r"[+;,/\s]+", text) if part}


def _diagnostic_float_value(diagnostics: Any, key: str) -> float | None:
    pattern = rf"(?:^|;){re.escape(key)}=([-+]?\d+(?:\.\d+)?)"
    match = re.search(pattern, str(diagnostics or ""))
    if match is None:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _live_guard_v3_low_support_baseline_summary(
    v3_shadow: Mapping[str, Any],
    value_summary: QuantileSummary,
) -> tuple[QuantileSummary, str]:
    if str(v3_shadow.get("v3_practical_status") or "") != "baseline_passthrough":
        return value_summary, ""
    if str(v3_shadow.get("v3_practical_recommendation") or "") != "baseline_reference":
        return value_summary, ""
    if str(v3_shadow.get("v3_post_match_scope") or "") != "summary_likelihood":
        return value_summary, ""
    if bool(v3_shadow.get("v3_post_strict_ready")):
        return value_summary, ""
    risk_flags = _v3_flag_set(v3_shadow.get("v3_practical_risk_flags"))
    if risk_flags.intersection(_LIVE_V3_STRONG_RAISE_EVIDENCE_FLAGS):
        return value_summary, ""
    effective_samples = _diagnostic_float_value(
        v3_shadow.get("v3_post_diagnostics"),
        "summary_likelihood_effective_samples",
    )
    if (
        effective_samples is None
        or effective_samples > _LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_MAX_ESS
    ):
        return value_summary, ""
    p10 = float(value_summary.p10)
    p50 = float(value_summary.p50)
    p90 = float(value_summary.p90)
    if p50 - p10 < _LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_MIN_P50_GAP:
        return value_summary, ""
    guarded_p50_cap = max(
        p10 + _LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_MIN_HEADROOM,
        p50 * _LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_P50_KEEP_RATIO,
    )
    guarded_p50 = max(p10, min(p50, guarded_p50_cap))
    if guarded_p50 >= p50:
        return value_summary, ""
    guarded_p90_cap = max(
        p50,
        guarded_p50 + _LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_P90_HEADROOM,
        guarded_p50 * _LIVE_V3_LOW_SUPPORT_BASELINE_GUARD_P90_MULTIPLIER,
    )
    guarded_p90 = max(guarded_p50, min(p90, guarded_p90_cap))
    guarded = QuantileSummary(
        p10=p10,
        p50=guarded_p50,
        p90=guarded_p90,
    )
    return (
        guarded,
        "live_low_support_baseline_guard:"
        f"ess={effective_samples:.3f};"
        f"p50 {p50:.0f}->{guarded_p50:.0f};"
        f"p90 {p90:.0f}->{guarded_p90:.0f}",
    )


def _live_guard_v3_practical_value_summary(
    v3_shadow: Mapping[str, Any],
    value_summary: QuantileSummary,
) -> tuple[QuantileSummary, str]:
    baseline_guarded, baseline_guard_reason = (
        _live_guard_v3_low_support_baseline_summary(v3_shadow, value_summary)
    )
    if baseline_guard_reason:
        return baseline_guarded, baseline_guard_reason
    if str(v3_shadow.get("v3_practical_recommendation") or "") != "raise_watch":
        return value_summary, ""
    confidence = str(v3_shadow.get("v3_practical_confidence") or "")
    if confidence not in _LIVE_V3_PRIOR_ONLY_RAISE_GUARD_CONFIDENCES:
        return value_summary, ""
    risk_flags = _v3_flag_set(v3_shadow.get("v3_practical_risk_flags"))
    if not risk_flags.intersection(_LIVE_V3_PRIOR_ONLY_RAISE_GUARD_FLAGS):
        return value_summary, ""
    if risk_flags.intersection(_LIVE_V3_STRONG_RAISE_EVIDENCE_FLAGS):
        return value_summary, ""
    p90_gap = float(value_summary.p90) - float(value_summary.p50)
    if p90_gap < _LIVE_V3_PRIOR_ONLY_RAISE_GUARD_MIN_GAP:
        return value_summary, ""
    p50 = float(value_summary.p50)
    baseline_p90 = _parse_float_text(
        v3_shadow.get("v3_practical_baseline_formal_decision_value_p90")
    )
    cap = p50 + max(
        _LIVE_V3_PRIOR_ONLY_RAISE_GUARD_MIN_HEADROOM,
        p50 * (_LIVE_V3_PRIOR_ONLY_RAISE_GUARD_MAX_P50_MULTIPLIER - 1.0),
    )
    guarded_p90 = max(
        p50,
        baseline_p90 if baseline_p90 is not None else p50,
        min(float(value_summary.p90), cap),
    )
    if guarded_p90 >= float(value_summary.p90):
        return value_summary, ""
    guarded = QuantileSummary(
        p10=float(value_summary.p10),
        p50=p50,
        p90=guarded_p90,
    )
    return (
        guarded,
        "live_prior_only_raise_guard:"
        f"p90 {float(value_summary.p90):.0f}->{guarded_p90:.0f};"
        f"confidence={confidence};flags={'+'.join(sorted(risk_flags))}",
    )


def _build_v3_practical_bid_rows(
    *,
    latest_bids: Mapping[str, int],
    v3_shadow: Mapping[str, Any],
    session: Any,
    round_no: int | None,
    posterior_samples: int,
    warehouse_estimate: Any,
    q6_prior_gap: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    if not v3_shadow.get("v3_practical_available"):
        return [], "v3_practical_unavailable"
    value_summary = _summary_from_flat_quantiles(
        v3_shadow,
        "v3_practical_formal_decision_value",
    )
    if value_summary is None:
        return [], "v3_practical_missing_formal_value"
    guarded_value_summary, live_guard_reason = _live_guard_v3_practical_value_summary(
        v3_shadow,
        value_summary,
    )
    raw_value_summary = _summary_from_flat_quantiles(
        v3_shadow,
        "v3_practical_total_value",
    )
    rows = _build_bid_rows(
        latest_bids=latest_bids,
        value_summary=guarded_value_summary,
        evidence_label="v3 practical formal",
        session=session,
        round_no=round_no,
        posterior_samples=posterior_samples,
        warehouse_estimate=warehouse_estimate,
        decision_value_summary=guarded_value_summary,
        raw_value_summary=raw_value_summary,
        posterior_diagnostics=(
            str(v3_shadow.get("v3_practical_diagnostics") or ""),
            live_guard_reason,
        ),
        q6_prior_gap=q6_prior_gap,
    )
    if not rows:
        return [], "v3_practical_no_bid_rows"
    recommendation = str(v3_shadow.get("v3_practical_recommendation") or "")
    for row in rows:
        row["formal_mode"] = LIVE_FORMAL_MODE_V3_PRACTICAL
        row["formal_mode_reason"] = (
            "v3_practical_ready_live_guarded"
            if live_guard_reason
            else "v3_practical_ready"
        )
        row["formal_baseline_source"] = LIVE_FORMAL_MODE_V3_PRACTICAL
        row["formal_override"] = "是"
        row["v3_practical_live_guard"] = "是" if live_guard_reason else "否"
        row["v3_practical_live_guard_reason"] = live_guard_reason
        if live_guard_reason:
            row["v3_practical_unguarded_decision_value"] = (
                _format_quantile_interval(value_summary)
            )
        row["v3_practical_recommendation"] = recommendation
        row["v3_practical_confidence"] = str(
            v3_shadow.get("v3_practical_confidence") or ""
        )
        row["v3_practical_source_lanes"] = str(
            v3_shadow.get("v3_practical_source_lanes") or ""
        )
        row["v3_practical_risk_flags"] = str(
            v3_shadow.get("v3_practical_risk_flags") or ""
        )
        row["v3_practical_reason"] = str(
            v3_shadow.get("v3_practical_reason") or ""
        )
    return (
        rows,
        "v3_practical_ready_live_guarded"
        if live_guard_reason
        else "v3_practical_ready",
    )


def _build_bid_rows(
    *,
    latest_bids: Mapping[str, int],
    value_summary: Any,
    evidence_label: str,
    session: Any,
    round_no: int | None,
    posterior_samples: int,
    warehouse_estimate: Any,
    decision_value_summary: Any = None,
    raw_value_summary: Any = None,
    posterior_diagnostics: Sequence[str] = (),
    q6_prior_gap: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    report = recommend_bid_strategy(
        latest_bids=latest_bids,
        value_summary=value_summary,
        evidence_label=evidence_label,
        session=session,
        round_no=round_no,
        total_rounds=5,
        posterior_samples=posterior_samples,
        warehouse_estimate=warehouse_estimate,
    )
    if report is None:
        return []
    thresholds = report.thresholds
    q6_risk_reference = _q6_risk_reference_text(q6_prior_gap)
    rows = [
        {
            "证据": report.evidence_label,
            "价值口径": "decision_value" if decision_value_summary is not None else "raw_value",
            "轮次": report.round_label,
            "信息强度": report.info_strength,
            "仓储": report.warehouse_status,
            "决策价值 P10/P50/P90": _format_quantile_interval(decision_value_summary),
            "原始价值 P10/P50/P90": _format_quantile_interval(raw_value_summary),
            "上界风险": _raw_ceiling_risk_label(
                decision_value_summary,
                raw_value_summary,
            ),
            "当前最高": f"{report.leader} {report.highest_bid:,}",
            "风险带": report.risk_band,
            "秒仓倍率": f"{thresholds.warehouse_multiplier:g}x",
            "探价(P10)": f"{thresholds.probe_bid:,}",
            "防守价": f"{thresholds.defend_bid:,}",
            "可追价(P90)": f"{thresholds.attack_bid:,}",
            "抢仓上限": f"{thresholds.attack_bid:,}",
            "停止价": f"{thresholds.stop_bid:,}",
            "依据": report.rationale,
            "补信息": report.next_info_hint,
            "后验诊断": ";".join(posterior_diagnostics),
            "红货风险参考": q6_risk_reference,
            "建议": report.action,
        }
    ]
    for player in report.player_risks:
        rows.append(
            {
                "证据": "玩家价位",
                "轮次": "",
                "信息强度": "",
                "仓储": "",
                "当前最高": f"{player.name} {player.bid:,}",
                "风险带": player.risk_band,
                "秒仓倍率": "",
                "探价(P10)": "",
                "防守价": "",
                "可追价(P90)": "",
                "抢仓上限": "",
                "停止价": "",
                "依据": "",
                "补信息": "",
                "建议": "",
                "红货风险参考": "",
            }
        )
    return rows


def _build_zero_match_fallback_rows(
    *,
    candidate_map_ids: Sequence[int],
    inference_session: Any,
    latest_bids: Mapping[str, int],
    round_no: int | None,
    maps: Mapping[int, BidMap],
    drops: Mapping[int, DropPool],
    items: Mapping[int, Item],
    n_trials: int,
    seed: int,
    cells_tol: int,
    count_tol: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    fallback_session = _zero_match_fallback_session(inference_session)
    fallback_cells_tol = max(cells_tol, 12)
    fallback_count_tol = max(count_tol, 3)
    fallback_results = estimate_map_likelihood(
        candidate_map_ids,
        fallback_session,
        maps=maps,
        drops=drops,
        items=items,
        n_trials=n_trials,
        seed=seed,
        cells_tol=fallback_cells_tol,
        count_tol=fallback_count_tol,
        warehouse_tol=fallback_cells_tol,
        total_item_count_tol=fallback_count_tol,
    )
    fallback_warehouse = estimate_warehouse_cells(
        candidate_map_ids,
        fallback_session,
        maps=maps,
        drops=drops,
        items=items,
        n_trials=n_trials,
        seed=seed,
        cells_tol=fallback_cells_tol,
        count_tol=fallback_count_tol,
        total_item_count_tol=fallback_count_tol,
    )
    fallback_map_rows = _map_likelihood_result_rows(
        fallback_results,
        "v1 fallback（v2无匹配，map prior）",
    )
    fallback_warehouse_rows = _warehouse_estimate_rows(fallback_warehouse)
    value_summary = next(
        (
            result.total_value
            for result in fallback_results
            if result.total_value is not None
        ),
        fallback_warehouse.total_value,
    )
    posterior_samples = max(
        [fallback_warehouse.n_matched]
        + [result.n_matched for result in fallback_results],
        default=0,
    )
    fallback_bid_rows: list[dict[str, Any]] = []
    if value_summary is not None:
        fallback_bid_rows = _build_bid_rows(
            latest_bids=latest_bids,
            value_summary=value_summary,
            evidence_label="v1 fallback（v2无匹配）",
            session=fallback_session,
            round_no=round_no,
            posterior_samples=posterior_samples,
            warehouse_estimate=fallback_warehouse,
            raw_value_summary=value_summary,
        )
        for row in fallback_bid_rows:
            row["fallback"] = "是"
            row["fallback_mode"] = "v1_map_prior_zero_match"
            row["fallback_note"] = (
                "v2 后验无匹配时的 map-prior 低置信参考；不替代 baseline v2"
            )
    return fallback_map_rows, fallback_warehouse_rows, fallback_bid_rows


def _parse_range_value(label: str, index: int) -> int | None:
    parts = [part.strip().replace(",", "") for part in label.split("/")]
    if len(parts) <= index or parts[index] in ("", "?"):
        return None
    try:
        return int(float(parts[index]))
    except ValueError:
        return None


def _parse_range_float_value(label: str, index: int) -> float | None:
    parts = [part.strip().replace(",", "") for part in label.split("/")]
    if len(parts) <= index or parts[index] in ("", "?"):
        return None
    try:
        return float(parts[index])
    except ValueError:
        return None


def _parse_range_p50(label: str) -> int | None:
    return _parse_range_value(label, 1)


def _parse_match_text(value: Any) -> tuple[int | None, int | None]:
    if value is None:
        return None, None
    text = str(value).strip()
    if not text or "/" not in text:
        return None, None
    left, right = text.split("/", 1)
    return _parse_int_text(left), _parse_int_text(right)


def _parse_percent_text(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    try:
        return float(text) / 100.0
    except ValueError:
        return None


def _parse_float_text(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _inventory_quality_breakdown(
    events: FatbeansCaptureEvents,
    items: Mapping[int, Item],
    *,
    problem: ResidualProblem | None = None,
    maps: Mapping[int, BidMap] | None = None,
    drops: Mapping[int, DropPool] | None = None,
    map_id: int | None = None,
) -> dict[str, Any]:
    resolved_map_id = map_id if map_id is not None else (
        problem.map_id if problem is not None else None
    )
    map_item_weights = _effective_item_weights_for_map(
        resolved_map_id,
        maps=maps,
        drops=drops,
        items=items,
    )
    for state in reversed(events.states):
        if not state.inventory_items:
            continue
        counts: Counter[int] = Counter()
        cells: Counter[int] = Counter()
        values: defaultdict[int, int] = defaultdict(int)
        top_item: dict[str, Any] = {}
        decision_value = 0
        trimmed_value = 0
        trimmed_items: list[str] = []
        q6_decision_value = 0
        q6_trimmed_value = 0
        q6_trimmed_items: list[str] = []
        q6_tail_replacement_value = 0
        q6_tail_replacement_count = 0
        q6_tail_replacement_items: list[str] = []
        q6_tail_replacement_sources: set[str] = set()
        exact_anchor_ids = set(problem.anchor_item_counts) if problem else set()
        for inv_item in state.inventory_items:
            item = items.get(inv_item.item_id)
            quality = inv_item.quality
            if quality is None and item is not None:
                quality = item.quality
            value = item.value if item is not None else 0
            if not top_item or value > int(top_item.get("value") or 0):
                top_item = {
                    "id": inv_item.item_id,
                    "name": item.name if item is not None else "",
                    "quality": quality,
                    "value": value,
                    "cells": inv_item.cells,
                }
            if quality is None:
                continue
            q = int(quality)
            trim_item = False
            if (
                item is not None
                and item.item_id not in exact_anchor_ids
                and is_confusable_long_tail(item)
            ):
                trim_item = True
            if (
                item is not None
                and problem is not None
                and item.value >= DEFAULT_VALUE_FLOOR
                and not is_tail_supported_by_evidence(item, problem)
            ):
                trim_item = True
            if item is not None and trim_item:
                trimmed_value += value
                if len(trimmed_items) < 4:
                    trimmed_items.append(f"{item.name}:{value}")
                if q == 6:
                    q6_trimmed_value += value
                    if len(q6_trimmed_items) < 4:
                        q6_trimmed_items.append(f"{item.name}:{value}")
                    replacement = _tail_replacement_for_item(
                        item,
                        items,
                        map_item_weights=map_item_weights,
                    )
                    if replacement["value"] > 0:
                        q6_tail_replacement_count += 1
                        q6_tail_replacement_value += int(replacement["value"])
                        if replacement["source"]:
                            q6_tail_replacement_sources.add(
                                str(replacement["source"])
                            )
                        if len(q6_tail_replacement_items) < 4:
                            q6_tail_replacement_items.append(
                                f"{item.name}:{value}->{replacement['value']}"
                            )
            else:
                decision_value += value
                if q == 6:
                    q6_decision_value += value
            counts[q] += 1
            cells[q] += inv_item.cells
            values[q] += value
        return {
            "final_quality_counts": _format_quality_map(counts),
            "final_quality_cells": _format_quality_map(cells),
            "final_quality_values": _format_quality_map(values),
            "final_q5_count": counts.get(5, 0),
            "final_q5_cells": cells.get(5, 0),
            "final_q5_value": values.get(5, 0),
            "final_q6_count": counts.get(6, 0),
            "final_q6_cells": cells.get(6, 0),
            "final_q6_value": values.get(6, 0),
            "final_q6_decision_value": q6_decision_value,
            "final_q6_trimmed_tail_value": q6_trimmed_value,
            "final_q6_trimmed_tail_items": ";".join(q6_trimmed_items),
            "final_q6_tail_replacement_value": q6_tail_replacement_value,
            "final_q6_tail_replacement_count": q6_tail_replacement_count,
            "final_q6_tail_replacement_items": ";".join(
                q6_tail_replacement_items
            ),
            "final_q6_tail_replacement_source": ";".join(
                sorted(q6_tail_replacement_sources)
            ),
            "final_q6_decision_value_with_tail_replacement": (
                q6_decision_value + q6_tail_replacement_value
            ),
            "final_decision_value": decision_value,
            "final_decision_value_with_tail_replacement": (
                decision_value + q6_tail_replacement_value
            ),
            "final_trimmed_tail_value": trimmed_value,
            "final_trimmed_tail_items": ";".join(trimmed_items),
            "final_top_item_id": top_item.get("id"),
            "final_top_item_name": top_item.get("name"),
            "final_top_item_quality": top_item.get("quality"),
            "final_top_item_value": top_item.get("value"),
            "final_top_item_cells": top_item.get("cells"),
        }
    return {}


def _effective_item_weights_for_map(
    map_id: int | None,
    *,
    maps: Mapping[int, BidMap] | None,
    drops: Mapping[int, DropPool] | None,
    items: Mapping[int, Item],
) -> dict[int, float]:
    if map_id is None or maps is None or drops is None:
        return {}
    bid_map = maps.get(map_id)
    if bid_map is None:
        return {}
    out: defaultdict[int, float] = defaultdict(float)
    try:
        if not bid_map.sub_pool_weights:
            flat = flatten_pool(bid_map.drop_pool_id, drops, items)
            for item_id, probability in zip(flat.item_ids, flat.probabilities):
                out[int(item_id)] += float(probability)
        else:
            total_weight = sum(
                weight
                for sub_map_id, weight in bid_map.sub_pool_weights
                if weight > 0 and sub_map_id in maps
            )
            if total_weight <= 0:
                return {}
            for sub_map_id, sub_weight in bid_map.sub_pool_weights:
                if sub_weight <= 0:
                    continue
                sub_map = maps.get(sub_map_id)
                if sub_map is None:
                    continue
                flat = flatten_pool(sub_map.drop_pool_id, drops, items)
                sub_probability = float(sub_weight) / float(total_weight)
                for item_id, probability in zip(flat.item_ids, flat.probabilities):
                    out[int(item_id)] += sub_probability * float(probability)
    except Exception:
        return {}
    return dict(out)


def _tail_replacement_for_item(
    item: Item,
    items: Mapping[int, Item],
    *,
    map_item_weights: Mapping[int, float] | None = None,
) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in items.values()
        if candidate.item_id != item.item_id
        and candidate.quality == item.quality
        and candidate.shape_w == item.shape_w
        and candidate.shape_h == item.shape_h
        and 0 < candidate.value < DEFAULT_VALUE_FLOOR
    ]
    if not candidates:
        return {"value": 0, "source": "", "candidate_count": 0}

    if map_item_weights:
        weighted = [
            (candidate.value, float(map_item_weights.get(candidate.item_id) or 0.0))
            for candidate in candidates
            if float(map_item_weights.get(candidate.item_id) or 0.0) > 0.0
        ]
        weighted_value = _weighted_median_value(weighted)
        if weighted_value is not None:
            return {
                "value": weighted_value,
                "source": "map_weighted_p50",
                "candidate_count": len(weighted),
            }
        return {"value": 0, "source": "", "candidate_count": 0}

    values = sorted(candidate.value for candidate in candidates)
    return {
        "value": int(round(statistics.median(values))),
        "source": "item_table_median",
        "candidate_count": len(values),
    }


def _weighted_median_value(values: Sequence[tuple[int, float]]) -> int | None:
    positive = [(int(value), float(weight)) for value, weight in values if weight > 0]
    if not positive:
        return None
    total = sum(weight for _, weight in positive)
    midpoint = total / 2.0
    running = 0.0
    for value, weight in sorted(positive, key=lambda row: row[0]):
        running += weight
        if running >= midpoint:
            return value
    return positive[-1][0]


def _format_quality_map(values: Mapping[int, int]) -> str:
    return ";".join(
        f"q{quality}={value}"
        for quality, value in sorted(values.items())
        if value
    )


def _parse_quality_count_total(value: Any) -> int | None:
    if value is None:
        return None
    total = 0
    matched = False
    for part in str(value).split(";"):
        if "=" not in part:
            continue
        _quality, raw_count = part.split("=", 1)
        parsed = _parse_int_text(raw_count)
        if parsed is None:
            continue
        total += parsed
        matched = True
    return total if matched else None


def _count_source_and_target(
    *,
    exact: int | None,
    floor: int | None,
) -> tuple[str, int | None]:
    if exact is not None and exact > 0:
        if floor is not None and floor > exact:
            return ("floor_over_exact", floor)
        return ("exact", exact)
    if floor is not None and floor > 0:
        return ("floor", floor)
    return ("none", None)


def _numeric_delta(left: int | float | None, right: int | float | None) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


def _numeric_ratio(left: int | float | None, right: int | float | None) -> float | None:
    if left is None or right is None or float(right) <= 0.0:
        return None
    return float(left) / float(right)


def _capacity_cases(
    *,
    total_count_source: str,
    target_prior_max_delta: float | None,
    truth_prior_max_delta: float | None,
    target_truth_delta: float | None,
) -> list[str]:
    target_above_prior = (
        target_prior_max_delta is not None and target_prior_max_delta > 0.0
    )
    truth_above_prior = (
        truth_prior_max_delta is not None and truth_prior_max_delta > 0.0
    )
    target_below_truth = target_truth_delta is not None and target_truth_delta < 0.0
    target_matches_truth = target_truth_delta is not None and target_truth_delta == 0.0
    target_above_truth = target_truth_delta is not None and target_truth_delta > 0.0
    cases: list[str] = []
    if target_above_prior and truth_above_prior and target_matches_truth:
        cases.append("direct_prior_max_conflict")
    if truth_above_prior and target_below_truth:
        cases.append("target_lower_bound_truth_above_prior")
    if target_above_prior and target_below_truth:
        cases.append("target_above_prior_but_below_truth")
    if target_above_prior and target_above_truth:
        cases.append("target_over_truth_capacity_risk")
    if truth_above_prior and total_count_source == "none":
        cases.append("truth_above_prior_without_count_target")
    if target_above_prior and not truth_above_prior:
        cases.append("target_above_prior_without_truth_support")
    if truth_above_prior and not target_above_prior and not target_below_truth:
        cases.append("truth_above_prior_without_target_prior_hit")
    if not cases:
        cases.append("no_capacity_prior_max_case")
    return cases


def _q6_top_size_band(truth_breakdown: Mapping[str, Any] | None) -> str:
    if int((truth_breakdown or {}).get("final_q6_count") or 0) <= 0:
        return "no_q6"
    top_quality = (truth_breakdown or {}).get("final_top_item_quality")
    if top_quality is None:
        return "q6_top_unknown_cells"
    if int(top_quality) != 6:
        return "q6_not_top_item"
    cells = (truth_breakdown or {}).get("final_top_item_cells")
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


def _model_eval_shadow_fields(
    prefix: str,
    shadow: Mapping[str, Any],
    *,
    baseline_q6_decision_value_p90: int | None,
    final_q6_decision_value: int,
    zero_q6_proven_control: bool,
) -> dict[str, Any]:
    active = bool(shadow.get("active"))
    shadow_q6_p90 = _parse_int_text(shadow.get("q6_decision_value_p90"))
    no_plannable_control = active and final_q6_decision_value <= 0
    no_plannable_positive = no_plannable_control and (shadow_q6_p90 or 0) > 0
    zero_q6_positive = (
        no_plannable_positive
        and zero_q6_proven_control
    )
    under_before = (
        active
        and baseline_q6_decision_value_p90 is not None
        and final_q6_decision_value > baseline_q6_decision_value_p90
    )
    covered_after = (
        active
        and shadow_q6_p90 is not None
        and final_q6_decision_value <= shadow_q6_p90
    )
    return {
        f"{prefix}_label": shadow.get("label"),
        f"{prefix}_gate": shadow.get("gate"),
        f"{prefix}_evidence_profile": shadow.get("evidence_profile_key"),
        f"{prefix}_active": active,
        f"{prefix}_trials": _parse_int_text(shadow.get("trials")),
        f"{prefix}_active_boost": _parse_float_text(shadow.get("active_boost")),
        f"{prefix}_active_prior_floor_ratio": _parse_float_text(
            shadow.get("active_prior_floor_ratio")
        ),
        f"{prefix}_active_conditional_target_count": _parse_float_text(
            shadow.get("active_conditional_target_count")
        ),
        f"{prefix}_active_conditional_target_cells": _parse_float_text(
            shadow.get("active_conditional_target_cells")
        ),
        f"{prefix}_active_conditional_value_power": _parse_float_text(
            shadow.get("active_conditional_value_power")
        ),
        f"{prefix}_decision_value_p50": _parse_int_text(
            shadow.get("decision_value_p50")
        ),
        f"{prefix}_decision_value_p90": _parse_int_text(
            shadow.get("decision_value_p90")
        ),
        f"{prefix}_q6_decision_value_p90": shadow_q6_p90,
        f"{prefix}_q6_count_p90": _parse_int_text(shadow.get("q6_count_p90")),
        f"{prefix}_q6_cells_p90": _parse_int_text(shadow.get("q6_cells_p90")),
        f"{prefix}_q6_p90_delta": (
            shadow_q6_p90 - baseline_q6_decision_value_p90
            if shadow_q6_p90 is not None
            and baseline_q6_decision_value_p90 is not None
            else None
        ),
        f"{prefix}_under_before": under_before,
        f"{prefix}_covered_after": covered_after,
        f"{prefix}_helped": under_before and covered_after,
        f"{prefix}_no_plannable_control": no_plannable_control,
        f"{prefix}_no_plannable_positive_proxy": no_plannable_positive,
        f"{prefix}_zero_q6_proven_control": (
            no_plannable_control and zero_q6_proven_control
        ),
        f"{prefix}_zero_q6_proven_false_positive": zero_q6_positive,
        f"{prefix}_false_positive_proxy": no_plannable_positive,
    }


def _model_eval_row(
    *,
    file: str,
    artifact: Mapping[str, Any],
    final_value: int | None,
    final_cells: int | None,
    truth_breakdown: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    if final_value is None and final_cells is None:
        return None
    warehouse_rows = artifact.get("warehouse_rows") or []
    bid_rows = artifact.get("bid_rows") or []
    bid_row = next((row for row in bid_rows if isinstance(row, Mapping)), {})
    v3_practical_unguarded_decision_value = bid_row.get(
        "v3_practical_unguarded_decision_value"
    )
    v3_practical_unguarded_p10 = _parse_range_value(
        str(v3_practical_unguarded_decision_value or ""),
        0,
    )
    v3_practical_unguarded_p50 = _parse_range_value(
        str(v3_practical_unguarded_decision_value or ""),
        1,
    )
    v3_practical_unguarded_p90 = _parse_range_value(
        str(v3_practical_unguarded_decision_value or ""),
        2,
    )
    layout_rows = artifact.get("layout_replay_rows") or []
    v2_rows = artifact.get("v2_posterior_rows") or []
    v3_shadow = (
        artifact.get("v3_posterior_shadow")
        if isinstance(artifact.get("v3_posterior_shadow"), Mapping)
        else {}
    )
    shadow = artifact.get("q6_residual_boost_shadow") or {}
    deep_floor_shadow = artifact.get("q6_residual_deep_floor_shadow") or {}
    deep11_floor_shadow = artifact.get("q6_residual_deep11_floor_shadow") or {}
    hidden_floor_shadow = artifact.get("q6_residual_hidden_floor_shadow") or {}
    villa_floor_shadow = artifact.get("q6_residual_villa_floor_shadow") or {}
    ethan_villa_random_floor_shadow = (
        artifact.get("q6_residual_ethan_villa_random_floor_shadow") or {}
    )
    ethan_shipwreck_layout_conditional_shadow = (
        artifact.get("q6_residual_ethan_shipwreck_layout_conditional_shadow") or {}
    )
    formal_prior_floor = artifact.get("q6_formal_prior_floor") or {}
    bottom_row_risk = artifact.get("q6_aisha_bottom_row_risk") or {}
    quality_only_local_risk = artifact.get("q6_quality_only_local_risk") or {}
    input_constraints = (
        artifact.get("inference_input_constraints")
        if isinstance(artifact.get("inference_input_constraints"), Mapping)
        else {}
    )
    warehouse_p50 = None
    value_p50 = None
    decision_value_p50 = None
    decision_value_p90 = None
    raw_value_p50 = None
    raw_value_p90 = None
    q6_match_rate = None
    q6_prior_match_rate = None
    q6_prior_expected_count = None
    q6_prior_expected_cells = None
    q6_prior_expected_value = None
    prior_expected_count = None
    prior_expected_cells = None
    prior_expected_value = None
    prior_expected_decision_value = None
    prior_expected_tail_replacement_decision_value = None
    q6_value_p90 = None
    q6_decision_value_p90 = None
    q6_tail_replacement_estimate_p90 = None
    q6_count_p90 = None
    q6_cells_p90 = None
    remaining_cells_after_layout_p10 = None
    remaining_cells_after_layout_p50 = None
    remaining_cells_after_layout_p90 = None
    q6_space_pressure_p50 = None
    q6_space_pressure_p90 = None
    q6_space_overflow_rate = None
    q6_prior_gap_summary = ""
    q6_prior_floor_value = None
    q6_practical_gate = ""
    q6_practical_p90 = None
    v3_post_available = bool(v3_shadow.get("v3_post_available"))
    v3_post_ready = bool(v3_shadow.get("v3_post_ready"))
    v3_post_strict_ready = bool(v3_shadow.get("v3_post_strict_ready"))
    v3_post_affects_bid = bool(v3_shadow.get("v3_post_affects_bid"))
    v3_post_match_scope = v3_shadow.get("v3_post_match_scope")
    v3_post_n_total = _parse_int_text(v3_shadow.get("v3_post_n_total"))
    v3_post_n_matched = _parse_int_text(v3_shadow.get("v3_post_n_matched"))
    v3_post_n_strict_matched = _parse_int_text(
        v3_shadow.get("v3_post_n_strict_matched")
    )
    v3_post_match_rate = _parse_float_text(v3_shadow.get("v3_post_match_rate"))
    v3_post_strict_match_rate = _parse_float_text(
        v3_shadow.get("v3_post_strict_match_rate")
    )
    v3_post_q6_present_rate = _parse_float_text(
        v3_shadow.get("v3_post_q6_present_rate")
    )
    v3_post_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_post_formal_decision_value_p50")
    )
    v3_post_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_post_formal_decision_value_p90")
    )
    v3_post_tail_replacement_p50 = _parse_int_text(
        v3_shadow.get("v3_post_tail_replacement_decision_value_p50")
    )
    v3_post_tail_replacement_p90 = _parse_int_text(
        v3_shadow.get("v3_post_tail_replacement_decision_value_p90")
    )
    v3_post_q6_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_post_q6_formal_decision_value_p50")
    )
    v3_post_q6_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_post_q6_formal_decision_value_p90")
    )
    v3_post_q6_count_p50 = _parse_int_text(v3_shadow.get("v3_post_q6_count_p50"))
    v3_post_q6_count_p90 = _parse_int_text(v3_shadow.get("v3_post_q6_count_p90"))
    v3_post_q6_cells_p50 = _parse_int_text(v3_shadow.get("v3_post_q6_cells_p50"))
    v3_post_q6_cells_p90 = _parse_int_text(v3_shadow.get("v3_post_q6_cells_p90"))
    v3_post_total_cells_p50 = _parse_int_text(
        v3_shadow.get("v3_post_total_cells_p50")
    )
    v3_post_total_cells_p90 = _parse_int_text(
        v3_shadow.get("v3_post_total_cells_p90")
    )
    v3_summary_known_count_floor = _parse_int_text(
        v3_shadow.get("v3_summary_known_count_floor")
    )
    v3_summary_known_cells_floor = _parse_int_text(
        v3_shadow.get("v3_summary_known_cells_floor")
    )
    v3_summary_known_value_floor = _parse_int_text(
        v3_shadow.get("v3_summary_known_value_floor")
    )
    v3_summary_session_total_count_exact = _parse_int_text(
        v3_shadow.get("v3_summary_session_total_count_exact")
    )
    v3_summary_session_total_cells_exact = _parse_int_text(
        v3_shadow.get("v3_summary_session_total_cells_exact")
    )
    v3_summary_q6_count_floor = _parse_int_text(
        v3_shadow.get("v3_summary_q6_count_floor")
    )
    v3_summary_q6_cells_floor = _parse_int_text(
        v3_shadow.get("v3_summary_q6_cells_floor")
    )
    v3_summary_q6_value_floor = _parse_int_text(
        v3_shadow.get("v3_summary_q6_value_floor")
    )
    v3_prior_available = bool(v3_shadow.get("v3_prior_available"))
    v3_prior_error = v3_shadow.get("v3_prior_error")
    v3_prior_map_id = _parse_int_text(v3_shadow.get("v3_prior_map_id"))
    v3_prior_map_name = v3_shadow.get("v3_prior_map_name")
    v3_prior_items_per_session_min = _parse_int_text(
        v3_shadow.get("v3_prior_items_per_session_min")
    )
    v3_prior_items_per_session_max = _parse_int_text(
        v3_shadow.get("v3_prior_items_per_session_max")
    )
    v3_prior_pool_count = _parse_int_text(v3_shadow.get("v3_prior_pool_count"))
    v3_prior_expected_draws = _parse_float_text(
        v3_shadow.get("v3_prior_expected_draws")
    )
    v3_prior_expected_count = _parse_float_text(
        v3_shadow.get("v3_prior_expected_count")
    )
    v3_prior_expected_cells = _parse_float_text(
        v3_shadow.get("v3_prior_expected_cells")
    )
    v3_prior_expected_value = _parse_float_text(
        v3_shadow.get("v3_prior_expected_value")
    )
    v3_prior_q6_draw_probability = _parse_float_text(
        v3_shadow.get("v3_prior_q6_draw_probability")
    )
    v3_prior_q6_session_probability = _parse_float_text(
        v3_shadow.get("v3_prior_q6_session_probability")
    )
    v3_prior_q6_expected_count = _parse_float_text(
        v3_shadow.get("v3_prior_q6_expected_count")
    )
    v3_prior_q6_expected_cells = _parse_float_text(
        v3_shadow.get("v3_prior_q6_expected_cells")
    )
    v3_prior_q6_expected_value = _parse_float_text(
        v3_shadow.get("v3_prior_q6_expected_value")
    )
    v3_capacity_total_count_source, v3_capacity_total_count_target = (
        _count_source_and_target(
            exact=v3_summary_session_total_count_exact,
            floor=v3_summary_known_count_floor,
        )
    )
    v3_capacity_truth_item_count = _parse_quality_count_total(
        (truth_breakdown or {}).get("final_quality_counts")
    )
    v3_capacity_target_prior_max_delta = _numeric_delta(
        v3_capacity_total_count_target,
        v3_prior_items_per_session_max,
    )
    v3_capacity_truth_prior_max_delta = _numeric_delta(
        v3_capacity_truth_item_count,
        v3_prior_items_per_session_max,
    )
    v3_capacity_target_truth_delta = _numeric_delta(
        v3_capacity_total_count_target,
        v3_capacity_truth_item_count,
    )
    v3_capacity_flags: list[str] = []
    if (
        v3_prior_items_per_session_max is not None
        and v3_capacity_total_count_target is not None
        and v3_capacity_total_count_target > v3_prior_items_per_session_max
    ):
        v3_capacity_flags.append("target_count_above_prior_max")
    if (
        v3_prior_items_per_session_max is not None
        and v3_capacity_truth_item_count is not None
        and v3_capacity_truth_item_count > v3_prior_items_per_session_max
    ):
        v3_capacity_flags.append("truth_count_above_prior_max")
    if (
        v3_prior_items_per_session_min is not None
        and v3_capacity_truth_item_count is not None
        and v3_capacity_truth_item_count < v3_prior_items_per_session_min
    ):
        v3_capacity_flags.append("truth_count_below_prior_min")
    v3_capacity_cases = _capacity_cases(
        total_count_source=v3_capacity_total_count_source,
        target_prior_max_delta=v3_capacity_target_prior_max_delta,
        truth_prior_max_delta=v3_capacity_truth_prior_max_delta,
        target_truth_delta=v3_capacity_target_truth_delta,
    )
    v3_robust_available = bool(v3_shadow.get("v3_robust_available"))
    v3_robust_affects_bid = bool(v3_shadow.get("v3_robust_affects_bid"))
    v3_robust_status = v3_shadow.get("v3_robust_status")
    v3_robust_prior_usable = bool(v3_shadow.get("v3_robust_prior_usable"))
    v3_robust_prior_trusted = bool(v3_shadow.get("v3_robust_prior_trusted"))
    v3_robust_fallback_mode = v3_shadow.get("v3_robust_fallback_mode")
    v3_robust_activity_candidate = bool(
        v3_shadow.get("v3_robust_activity_candidate")
    )
    v3_robust_prior_stress_score = _parse_int_text(
        v3_shadow.get("v3_robust_prior_stress_score")
    )
    v3_robust_reasons = v3_shadow.get("v3_robust_reasons")
    v3_ccv_available = bool(v3_shadow.get("v3_ccv_available"))
    v3_ccv_ready = bool(v3_shadow.get("v3_ccv_ready"))
    v3_ccv_affects_bid = bool(v3_shadow.get("v3_ccv_affects_bid"))
    v3_ccv_match_scope = v3_shadow.get("v3_ccv_match_scope")
    v3_ccv_n_matched = _parse_int_text(v3_shadow.get("v3_ccv_n_matched"))
    v3_ccv_q6_present_rate = _parse_float_text(
        v3_shadow.get("v3_ccv_q6_present_rate")
    )
    v3_ccv_q6_count_p50 = _parse_int_text(v3_shadow.get("v3_ccv_q6_count_p50"))
    v3_ccv_q6_count_p90 = _parse_int_text(v3_shadow.get("v3_ccv_q6_count_p90"))
    v3_ccv_q6_cells_p50 = _parse_int_text(v3_shadow.get("v3_ccv_q6_cells_p50"))
    v3_ccv_q6_cells_p90 = _parse_int_text(v3_shadow.get("v3_ccv_q6_cells_p90"))
    v3_ccv_q6_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_ccv_q6_formal_decision_value_p50")
    )
    v3_ccv_q6_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_ccv_q6_formal_decision_value_p90")
    )
    v3_resid_available = bool(v3_shadow.get("v3_resid_available"))
    v3_resid_ready = bool(v3_shadow.get("v3_resid_ready"))
    v3_resid_affects_bid = bool(v3_shadow.get("v3_resid_affects_bid"))
    v3_resid_match_scope = v3_shadow.get("v3_resid_match_scope")
    v3_resid_n_matched = _parse_int_text(v3_shadow.get("v3_resid_n_matched"))
    v3_resid_q6_present_rate = _parse_float_text(
        v3_shadow.get("v3_resid_q6_present_rate")
    )
    v3_resid_q6_count_p50 = _parse_int_text(
        v3_shadow.get("v3_resid_q6_count_p50")
    )
    v3_resid_q6_count_p90 = _parse_int_text(
        v3_shadow.get("v3_resid_q6_count_p90")
    )
    v3_resid_q6_cells_p50 = _parse_int_text(
        v3_shadow.get("v3_resid_q6_cells_p50")
    )
    v3_resid_q6_cells_p90 = _parse_int_text(
        v3_shadow.get("v3_resid_q6_cells_p90")
    )
    v3_resid_q6_value_p50 = _parse_int_text(
        v3_shadow.get("v3_resid_q6_value_p50")
    )
    v3_resid_q6_value_p90 = _parse_int_text(
        v3_shadow.get("v3_resid_q6_value_p90")
    )
    v3_resid_gate_available = bool(v3_shadow.get("v3_resid_gate_available"))
    v3_resid_gate_ready = bool(v3_shadow.get("v3_resid_gate_ready"))
    v3_resid_gate_affects_bid = bool(
        v3_shadow.get("v3_resid_gate_affects_bid")
    )
    v3_resid_gate_active = bool(v3_shadow.get("v3_resid_gate_active"))
    v3_resid_gate_status = v3_shadow.get("v3_resid_gate_status")
    v3_resid_gate_gate_reason = v3_shadow.get("v3_resid_gate_gate_reason")
    v3_resid_gate_source = v3_shadow.get("v3_resid_gate_source")
    v3_resid_gate_q6_count_p50 = _parse_int_text(
        v3_shadow.get("v3_resid_gate_q6_count_p50")
    )
    v3_resid_gate_q6_cells_p50 = _parse_int_text(
        v3_shadow.get("v3_resid_gate_q6_cells_p50")
    )
    v3_resid_gate_q6_value_p50 = _parse_int_text(
        v3_shadow.get("v3_resid_gate_q6_value_p50")
    )
    v3_resid_gate_q6_count_delta_p50 = _parse_float_text(
        v3_shadow.get("v3_resid_gate_q6_count_delta_p50")
    )
    v3_resid_gate_q6_cells_delta_p50 = _parse_float_text(
        v3_shadow.get("v3_resid_gate_q6_cells_delta_p50")
    )
    v3_resid_gate_q6_value_delta_p50 = _parse_float_text(
        v3_shadow.get("v3_resid_gate_q6_value_delta_p50")
    )
    v3_cal_available = bool(v3_shadow.get("v3_cal_available"))
    v3_cal_ready = bool(v3_shadow.get("v3_cal_ready"))
    v3_cal_active = bool(v3_shadow.get("v3_cal_active"))
    v3_cal_affects_bid = bool(v3_shadow.get("v3_cal_affects_bid"))
    v3_cal_status = v3_shadow.get("v3_cal_status")
    v3_cal_gate_reason = v3_shadow.get("v3_cal_gate_reason")
    v3_cal_scale = _parse_float_text(v3_shadow.get("v3_cal_scale"))
    v3_cal_archive_sessions = _parse_int_text(
        v3_shadow.get("v3_cal_archive_sessions")
    )
    v3_cal_median_ratio = _parse_float_text(v3_shadow.get("v3_cal_median_ratio"))
    v3_cal_p90_ratio = _parse_float_text(v3_shadow.get("v3_cal_p90_ratio"))
    v3_cal_baseline_formal_mae = _parse_float_text(
        v3_shadow.get("v3_cal_baseline_formal_p50_mae")
    )
    v3_cal_baseline_formal_bias = _parse_float_text(
        v3_shadow.get("v3_cal_baseline_formal_p50_bias")
    )
    v3_cal_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_cal_formal_decision_value_p50")
    )
    v3_cal_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_cal_formal_decision_value_p90")
    )
    v3_cal_q6_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_cal_q6_formal_decision_value_p50")
    )
    v3_cal_q6_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_cal_q6_formal_decision_value_p90")
    )
    v3_under_available = bool(v3_shadow.get("v3_under_available"))
    v3_under_ready = bool(v3_shadow.get("v3_under_ready"))
    v3_under_active = bool(v3_shadow.get("v3_under_active"))
    v3_under_candidate = bool(v3_shadow.get("v3_under_candidate"))
    v3_under_affects_bid = bool(v3_shadow.get("v3_under_affects_bid"))
    v3_under_status = v3_shadow.get("v3_under_status")
    v3_under_gate_reason = v3_shadow.get("v3_under_gate_reason")
    v3_under_scale = _parse_float_text(v3_shadow.get("v3_under_scale"))
    v3_under_hero_map_id = v3_shadow.get("v3_under_hero_map_id")
    v3_under_source = v3_shadow.get("v3_under_source")
    v3_under_archive_sessions = _parse_int_text(
        v3_shadow.get("v3_under_archive_sessions")
    )
    v3_under_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_under_formal_decision_value_p50")
    )
    v3_under_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_under_formal_decision_value_p90")
    )
    v3_under_q6_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_under_q6_formal_decision_value_p50")
    )
    v3_under_q6_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_under_q6_formal_decision_value_p90")
    )
    v3_tail_review_available = bool(v3_shadow.get("v3_tail_review_available"))
    v3_tail_review_ready = bool(v3_shadow.get("v3_tail_review_ready"))
    v3_tail_review_active = bool(v3_shadow.get("v3_tail_review_active"))
    v3_tail_review_candidate = bool(v3_shadow.get("v3_tail_review_candidate"))
    v3_tail_review_hurt_guard = bool(v3_shadow.get("v3_tail_review_hurt_guard"))
    v3_tail_review_affects_bid = bool(
        v3_shadow.get("v3_tail_review_affects_bid")
    )
    v3_tail_review_status = v3_shadow.get("v3_tail_review_status")
    v3_tail_review_gate_reason = v3_shadow.get("v3_tail_review_gate_reason")
    v3_tail_review_hero_map_id = v3_shadow.get("v3_tail_review_hero_map_id")
    v3_tail_review_source = v3_shadow.get("v3_tail_review_source")
    v3_tail_review_archive_sessions = _parse_int_text(
        v3_shadow.get("v3_tail_review_archive_sessions")
    )
    v3_tail_review_tail_delta = _parse_float_text(
        v3_shadow.get("v3_tail_review_tail_delta_p50_mae")
    )
    v3_tail_review_q6_tail_delta = _parse_float_text(
        v3_shadow.get("v3_tail_review_q6_tail_delta_p50_mae")
    )
    v3_tail_review_tail_p50 = _parse_int_text(
        v3_shadow.get("v3_tail_review_tail_replacement_decision_value_p50")
    )
    v3_tail_review_tail_p90 = _parse_int_text(
        v3_shadow.get("v3_tail_review_tail_replacement_decision_value_p90")
    )
    v3_tail_review_q6_tail_p50 = _parse_int_text(
        v3_shadow.get("v3_tail_review_q6_tail_replacement_decision_value_p50")
    )
    v3_tail_review_q6_tail_p90 = _parse_int_text(
        v3_shadow.get("v3_tail_review_q6_tail_replacement_decision_value_p90")
    )
    v3_fv_available = bool(v3_shadow.get("v3_fv_available"))
    v3_fv_ready = bool(v3_shadow.get("v3_fv_ready"))
    v3_fv_active = bool(v3_shadow.get("v3_fv_active"))
    v3_fv_candidate = bool(v3_shadow.get("v3_fv_candidate"))
    v3_fv_affects_bid = bool(v3_shadow.get("v3_fv_affects_bid"))
    v3_fv_status = v3_shadow.get("v3_fv_status")
    v3_fv_gate_reason = v3_shadow.get("v3_fv_gate_reason")
    v3_fv_source = v3_shadow.get("v3_fv_source")
    v3_fv_stress_class = v3_shadow.get("v3_fv_stress_class")
    v3_fv_capacity_flags = v3_shadow.get("v3_fv_capacity_flags")
    v3_fv_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_fv_formal_decision_value_p50")
    )
    v3_fv_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_fv_formal_decision_value_p90")
    )
    v3_fv_q6_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_fv_q6_formal_decision_value_p50")
    )
    v3_fv_q6_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_fv_q6_formal_decision_value_p90")
    )
    v3_scp_available = bool(v3_shadow.get("v3_scp_available"))
    v3_scp_ready = bool(v3_shadow.get("v3_scp_ready"))
    v3_scp_affects_bid = bool(v3_shadow.get("v3_scp_affects_bid"))
    v3_scp_active = bool(v3_shadow.get("v3_scp_active"))
    v3_scp_candidate = bool(v3_shadow.get("v3_scp_candidate"))
    v3_scp_missing_table = bool(v3_shadow.get("v3_scp_missing_table"))
    v3_scp_status = v3_shadow.get("v3_scp_status")
    v3_scp_gate_reason = v3_shadow.get("v3_scp_gate_reason")
    v3_scp_scope = v3_shadow.get("v3_scp_scope")
    v3_scp_group = v3_shadow.get("v3_scp_group")
    v3_scp_inventory_p95 = _parse_float_text(
        v3_shadow.get("v3_scp_inventory_count_p95")
    )
    v3_scp_inventory_max = _parse_float_text(
        v3_shadow.get("v3_scp_inventory_count_max")
    )
    v3_scp_non_temp_p95 = _parse_float_text(
        v3_shadow.get("v3_scp_non_temp_inventory_count_p95")
    )
    v3_scp_non_temp_max = _parse_float_text(
        v3_shadow.get("v3_scp_non_temp_inventory_count_max")
    )
    v3_scp_above_drop_after_temp = _parse_int_text(
        v3_shadow.get("v3_scp_above_drop_after_temp_zodiac_rows")
    )
    v3_scp_above_round_after_temp = _parse_int_text(
        v3_shadow.get("v3_scp_above_round_after_temp_zodiac_rows")
    )
    v3_scp_prior_p95_delta = _parse_float_text(
        v3_shadow.get("v3_scp_prior_max_to_observed_p95_delta")
    )
    v3_scp_prior_max_delta = _parse_float_text(
        v3_shadow.get("v3_scp_prior_max_to_observed_max_delta")
    )
    v3_scp_flags = v3_shadow.get("v3_scp_flags")
    v3_cse_available = bool(v3_shadow.get("v3_cse_available"))
    v3_cse_ready = bool(v3_shadow.get("v3_cse_ready"))
    v3_cse_affects_bid = bool(v3_shadow.get("v3_cse_affects_bid"))
    v3_cse_active = bool(v3_shadow.get("v3_cse_active"))
    v3_cse_candidate = bool(v3_shadow.get("v3_cse_candidate"))
    v3_cse_pressure_candidate = bool(
        v3_shadow.get("v3_cse_pressure_candidate")
    )
    v3_cse_status = v3_shadow.get("v3_cse_status")
    v3_cse_gate_reason = v3_shadow.get("v3_cse_gate_reason")
    v3_cse_scope = v3_shadow.get("v3_cse_scope")
    v3_cse_group = v3_shadow.get("v3_cse_group")
    v3_cse_source_context_classes = v3_shadow.get(
        "v3_cse_source_context_classes"
    )
    v3_cse_unique_round_rows = _parse_int_text(
        v3_shadow.get("v3_cse_unique_round_overflow_rows")
    )
    v3_cse_server_rows = _parse_int_text(
        v3_shadow.get("v3_cse_server_side_expansion_rows")
    )
    v3_cse_session_rows = _parse_int_text(
        v3_shadow.get("v3_cse_session_capacity_source_semantics_rows")
    )
    v3_cse_public_rows = _parse_int_text(
        v3_shadow.get("v3_cse_public_total_match_rows")
    )
    v3_cse_full_action_rows = _parse_int_text(
        v3_shadow.get("v3_cse_full_action_rows")
    )
    v3_cse_unique_p95 = _parse_float_text(
        v3_shadow.get("v3_cse_unique_non_temp_p95")
    )
    v3_cse_unique_max = _parse_float_text(
        v3_shadow.get("v3_cse_unique_non_temp_max")
    )
    v3_cse_target_count_source = v3_shadow.get("v3_cse_target_count_source")
    v3_cse_target_count = _parse_float_text(
        v3_shadow.get("v3_cse_target_count")
    )
    v3_cse_prior_items_per_session_max = _parse_float_text(
        v3_shadow.get("v3_cse_prior_items_per_session_max")
    )
    v3_cse_target_p95_delta = _parse_float_text(
        v3_shadow.get("v3_cse_target_to_unique_non_temp_p95_delta")
    )
    v3_cse_prior_p95_delta = _parse_float_text(
        v3_shadow.get("v3_cse_prior_max_to_unique_non_temp_p95_delta")
    )
    v3_cse_target_prior_delta = _parse_float_text(
        v3_shadow.get("v3_cse_target_prior_max_delta")
    )
    v3_cse_prior_max_delta = _parse_float_text(
        v3_shadow.get("v3_cse_prior_max_to_unique_non_temp_max_delta")
    )
    v3_cse_flags = v3_shadow.get("v3_cse_flags")
    v3_practical_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_practical_formal_decision_value_p50")
    )
    v3_practical_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_practical_formal_decision_value_p90")
    )
    v3_practical_q6_formal_p50 = _parse_int_text(
        v3_shadow.get("v3_practical_q6_formal_decision_value_p50")
    )
    v3_practical_q6_formal_p90 = _parse_int_text(
        v3_shadow.get("v3_practical_q6_formal_decision_value_p90")
    )
    posterior_samples = None
    posterior_total_samples = None
    q6_shadow_active = bool(shadow.get("active"))
    q6_shadow_active_boost = _parse_float_text(shadow.get("active_boost"))
    q6_shadow_decision_value_p50 = _parse_int_text(
        shadow.get("decision_value_p50")
    )
    q6_shadow_decision_value_p90 = _parse_int_text(
        shadow.get("decision_value_p90")
    )
    q6_shadow_q6_decision_value_p90 = _parse_int_text(
        shadow.get("q6_decision_value_p90")
    )
    q6_shadow_q6_count_p90 = _parse_int_text(shadow.get("q6_count_p90"))
    q6_shadow_q6_cells_p90 = _parse_int_text(shadow.get("q6_cells_p90"))
    anchor_count = None
    posterior_diagnostics = ""
    if warehouse_rows:
        warehouse_p50 = _parse_range_p50(
            str(warehouse_rows[0].get("总格 P10/P50/P90", ""))
        )
        value_p50 = _parse_range_p50(
            str(warehouse_rows[0].get("价值 P10/P50/P90", ""))
        )
    if bid_rows:
        decision_value_p50 = _parse_range_p50(
            str(bid_rows[0].get("决策价值 P10/P50/P90", ""))
        )
        decision_value_p90 = _parse_range_value(
            str(bid_rows[0].get("决策价值 P10/P50/P90", "")),
            2,
        )
        raw_value_p50 = _parse_range_p50(
            str(bid_rows[0].get("原始价值 P10/P50/P90", ""))
        )
        raw_value_p90 = _parse_range_value(
            str(bid_rows[0].get("原始价值 P10/P50/P90", "")),
            2,
        )
    if v2_rows:
        posterior_samples, posterior_total_samples = _parse_match_text(
            v2_rows[0].get("匹配")
        )
        if decision_value_p50 is None:
            decision_value_p50 = _parse_range_p50(
                str(v2_rows[0].get("决策价值 P10/P50/P90", ""))
            )
            decision_value_p90 = _parse_range_value(
                str(v2_rows[0].get("决策价值 P10/P50/P90", "")),
                2,
            )
        if raw_value_p50 is None:
            raw_value_p50 = _parse_range_p50(
                str(v2_rows[0].get("原始价值 P10/P50/P90", ""))
            )
            raw_value_p90 = _parse_range_value(
                str(v2_rows[0].get("原始价值 P10/P50/P90", "")),
                2,
            )
        q6_match_rate = _parse_percent_text(v2_rows[0].get("q6样本率"))
        q6_prior_match_rate = _parse_percent_text(v2_rows[0].get("q6掉落先验"))
        q6_prior_expected_count = _parse_float_text(v2_rows[0].get("q6先验件数"))
        q6_prior_expected_cells = _parse_float_text(v2_rows[0].get("q6先验格数"))
        q6_prior_expected_value = _parse_int_text(v2_rows[0].get("q6先验价值"))
        prior_expected_count = _parse_float_text(v2_rows[0].get("先验件数"))
        prior_expected_cells = _parse_float_text(v2_rows[0].get("先验格数"))
        prior_expected_value = _parse_int_text(v2_rows[0].get("先验原始价值"))
        prior_expected_decision_value = _parse_int_text(
            v2_rows[0].get("先验决策价值")
        )
        prior_expected_tail_replacement_decision_value = _parse_int_text(
            v2_rows[0].get("先验替代决策价值")
        )
        shape_target_count = _parse_int_text(v2_rows[0].get("形状约束数"))
        category_target_count = _parse_int_text(v2_rows[0].get("分类约束数"))
        category_exclusion_count = _parse_int_text(v2_rows[0].get("分类反排数"))
        random_sample_avg_values = str(v2_rows[0].get("随机样本均价") or "")
        random_sample_avg_signal_values = str(
            v2_rows[0].get("随机样本均价信号") or ""
        )
        q6_value_p90 = _parse_range_value(
            str(v2_rows[0].get("q6价值 P10/P50/P90", "")),
            2,
        )
        q6_decision_value_p90 = _parse_range_value(
            str(v2_rows[0].get("q6决策价值 P10/P50/P90", "")),
            2,
        )
        q6_tail_replacement_estimate_p90 = _parse_range_value(
            str(v2_rows[0].get("q6替代决策价值 P10/P50/P90", "")),
            2,
        )
        q6_count_p90 = _parse_range_value(
            str(v2_rows[0].get("q6件数 P10/P50/P90", "")),
            2,
        )
        q6_cells_p90 = _parse_range_value(
            str(v2_rows[0].get("q6格数 P10/P50/P90", "")),
            2,
        )
        remaining_label = str(v2_rows[0].get("剩余空间 P10/P50/P90", ""))
        remaining_cells_after_layout_p10 = _parse_range_value(remaining_label, 0)
        remaining_cells_after_layout_p50 = _parse_range_value(remaining_label, 1)
        remaining_cells_after_layout_p90 = _parse_range_value(remaining_label, 2)
        pressure_label = str(v2_rows[0].get("q6空间压力 P10/P50/P90", ""))
        q6_space_pressure_p50 = _parse_range_float_value(pressure_label, 1)
        q6_space_pressure_p90 = _parse_range_float_value(pressure_label, 2)
        q6_space_overflow_rate = _parse_percent_text(
            v2_rows[0].get("q6空间溢出率")
        )
        q6_prior_gap_summary = str(v2_rows[0].get("q6先验缺口") or "")
        q6_prior_floor_value = _parse_int_text(v2_rows[0].get("q6先验风险参考"))
        q6_practical_gate = str(v2_rows[0].get("q6实战门控") or "")
        q6_practical_p90 = _parse_int_text(v2_rows[0].get("q6实战参考P90"))
        anchor_count = _parse_int_text(v2_rows[0].get("锚点数"))
        posterior_diagnostics = str(v2_rows[0].get("诊断") or "")
    else:
        shape_target_count = None
        category_target_count = None
        category_exclusion_count = None
        anchor_count = None
        random_sample_avg_values = ""
        random_sample_avg_signal_values = ""
    layout_root = layout_conflict_root(posterior_diagnostics)
    latest_layout_fit = next(
        (
            row for row in reversed(layout_rows)
            if row.get("最终格") and row.get("样本拟合估计")
        ),
        {},
    )
    layout_p50 = _parse_range_p50(str(latest_layout_fit.get("样本拟合估计", "")))
    stop_bid = None
    attack_bid = None
    highest_bid = None
    if bid_rows:
        row = bid_rows[0]
        stop_bid = _parse_int_text(row.get("停止价"))
        attack_bid = _parse_int_text(row.get("抢仓上限"))
        current = str(row.get("当前最高", ""))
        highest_bid = _parse_int_text(current.split(" ")[-1] if current else None)
    final_q6_value = int((truth_breakdown or {}).get("final_q6_value") or 0)
    final_q6_decision_value = int(
        (
            (truth_breakdown or {}).get("final_q6_decision_value")
            if (truth_breakdown or {}).get("final_q6_decision_value") is not None
            else final_q6_value
        )
        or 0
    )
    final_q6_decision_value_with_tail_replacement = int(
        (
            (truth_breakdown or {}).get(
                "final_q6_decision_value_with_tail_replacement"
            )
            if (truth_breakdown or {}).get(
                "final_q6_decision_value_with_tail_replacement"
            )
            is not None
            else final_q6_decision_value
        )
        or 0
    )
    final_q6_tail_replacement_value = int(
        (truth_breakdown or {}).get("final_q6_tail_replacement_value") or 0
    )
    no_plannable_q6_control = final_q6_decision_value <= 0
    zero_q6_proven_control = (
        no_plannable_q6_control
        and _zero_q6_proven_from_diagnostics(posterior_diagnostics)
    )
    q6_shadow_under_before = (
        q6_shadow_active
        and q6_decision_value_p90 is not None
        and final_q6_decision_value > q6_decision_value_p90
    )
    q6_shadow_covered_after = (
        q6_shadow_active
        and q6_shadow_q6_decision_value_p90 is not None
        and final_q6_decision_value <= q6_shadow_q6_decision_value_p90
    )
    q6_practical_gate_hit = bool(q6_practical_gate)
    q6_practical_under_before = (
        q6_practical_gate_hit
        and q6_decision_value_p90 is not None
        and final_q6_decision_value > q6_decision_value_p90
    )
    q6_practical_covered_after = (
        q6_practical_gate_hit
        and q6_practical_p90 is not None
        and final_q6_decision_value <= q6_practical_p90
    )
    deep_floor_shadow_fields = _model_eval_shadow_fields(
        "q6_residual_deep_floor_shadow",
        deep_floor_shadow,
        baseline_q6_decision_value_p90=q6_decision_value_p90,
        final_q6_decision_value=final_q6_decision_value,
        zero_q6_proven_control=zero_q6_proven_control,
    )
    deep11_floor_shadow_fields = _model_eval_shadow_fields(
        "q6_residual_deep11_floor_shadow",
        deep11_floor_shadow,
        baseline_q6_decision_value_p90=q6_decision_value_p90,
        final_q6_decision_value=final_q6_decision_value,
        zero_q6_proven_control=zero_q6_proven_control,
    )
    hidden_floor_shadow_fields = _model_eval_shadow_fields(
        "q6_residual_hidden_floor_shadow",
        hidden_floor_shadow,
        baseline_q6_decision_value_p90=q6_decision_value_p90,
        final_q6_decision_value=final_q6_decision_value,
        zero_q6_proven_control=zero_q6_proven_control,
    )
    villa_floor_shadow_fields = _model_eval_shadow_fields(
        "q6_residual_villa_floor_shadow",
        villa_floor_shadow,
        baseline_q6_decision_value_p90=q6_decision_value_p90,
        final_q6_decision_value=final_q6_decision_value,
        zero_q6_proven_control=zero_q6_proven_control,
    )
    ethan_villa_random_floor_shadow_fields = _model_eval_shadow_fields(
        "q6_residual_ethan_villa_random_floor_shadow",
        ethan_villa_random_floor_shadow,
        baseline_q6_decision_value_p90=q6_decision_value_p90,
        final_q6_decision_value=final_q6_decision_value,
        zero_q6_proven_control=zero_q6_proven_control,
    )
    ethan_shipwreck_layout_conditional_shadow_fields = _model_eval_shadow_fields(
        "q6_residual_ethan_shipwreck_layout_conditional_shadow",
        ethan_shipwreck_layout_conditional_shadow,
        baseline_q6_decision_value_p90=q6_decision_value_p90,
        final_q6_decision_value=final_q6_decision_value,
        zero_q6_proven_control=zero_q6_proven_control,
    )
    eval_round = artifact.get("observed_round", artifact.get("round"))
    action_round = artifact.get("action_round", artifact.get("round"))
    truth_breakdown = truth_breakdown or {}
    has_formal_decision_truth = truth_breakdown.get("final_decision_value") is not None
    has_replacement_decision_truth = (
        truth_breakdown.get("final_decision_value_with_tail_replacement") is not None
    )
    final_formal_decision_value = (
        truth_breakdown.get("final_decision_value")
        if has_formal_decision_truth
        else None
    )
    final_replacement_decision_value = (
        truth_breakdown.get("final_decision_value_with_tail_replacement")
        if has_replacement_decision_truth
        else final_formal_decision_value
        if has_formal_decision_truth
        else final_value
    )
    if has_replacement_decision_truth and (
        not has_formal_decision_truth
        or final_replacement_decision_value != final_formal_decision_value
    ):
        decision_value_truth_source = "tail_replacement"
    elif has_formal_decision_truth:
        decision_value_truth_source = "formal"
    else:
        decision_value_truth_source = "raw"
    evidence_stage = _evidence_stage(eval_round)
    density_score = _live_information_density_score(
        eval_round,
        anchor_count=anchor_count,
        shape_target_count=shape_target_count,
        category_target_count=category_target_count,
        category_exclusion_count=category_exclusion_count,
    )
    density_band = _information_density_band(density_score)
    public_constraint_key = _public_constraint_key(posterior_diagnostics)
    evidence_profile_key = str(
        artifact.get("evidence_profile_key")
        or _live_evidence_profile_key(
            public_constraint_key=public_constraint_key,
            random_sample_avg_values=random_sample_avg_signal_values,
            category_target_count=category_target_count,
            category_exclusion_count=category_exclusion_count,
            shape_target_count=shape_target_count,
        )
    )
    return {
        "ts": time.time(),
        "file": file,
        "hero": artifact.get("hero"),
        "map_id": artifact.get("map_id"),
        "round": eval_round,
        "action_round": action_round,
        "formal_mode_requested": artifact.get("formal_mode_requested"),
        "formal_mode": artifact.get("formal_mode"),
        "formal_mode_reason": artifact.get("formal_mode_reason"),
        "formal_baseline_source": artifact.get("formal_baseline_source"),
        "v3_practical_live_guard": bid_row.get("v3_practical_live_guard"),
        "v3_practical_live_guard_reason": bid_row.get(
            "v3_practical_live_guard_reason"
        ),
        "v3_practical_unguarded_decision_value": bid_row.get(
            "v3_practical_unguarded_decision_value"
        ),
        "v3_practical_unguarded_decision_value_p10": (
            v3_practical_unguarded_p10
        ),
        "v3_practical_unguarded_decision_value_p50": (
            v3_practical_unguarded_p50
        ),
        "v3_practical_unguarded_decision_value_p90": (
            v3_practical_unguarded_p90
        ),
        "final_value": final_value,
        "final_cells": final_cells,
        **dict(truth_breakdown),
        "value_p50": value_p50,
        "decision_value_p50": decision_value_p50,
        "decision_value_p90": decision_value_p90,
        "decision_value_truth": final_replacement_decision_value,
        "decision_value_truth_source": decision_value_truth_source,
        "decision_value_p50_error": (
            decision_value_p50 - final_replacement_decision_value
            if decision_value_p50 is not None
            and final_replacement_decision_value is not None
            else None
        ),
        "decision_value_p90_error": (
            decision_value_p90 - final_replacement_decision_value
            if decision_value_p90 is not None
            and final_replacement_decision_value is not None
            else None
        ),
        "decision_value_p50_error_vs_formal": (
            decision_value_p50 - final_formal_decision_value
            if decision_value_p50 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "decision_value_p90_error_vs_formal": (
            decision_value_p90 - final_formal_decision_value
            if decision_value_p90 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "decision_value_p50_error_vs_raw": (
            decision_value_p50 - final_value
            if decision_value_p50 is not None and final_value is not None
            else None
        ),
        "decision_value_p90_error_vs_raw": (
            decision_value_p90 - final_value
            if decision_value_p90 is not None and final_value is not None
            else None
        ),
        "raw_value_p50": raw_value_p50,
        "raw_value_p90": raw_value_p90,
        "raw_minus_decision_p90": (
            raw_value_p90 - decision_value_p90
            if raw_value_p90 is not None and decision_value_p90 is not None
            else None
        ),
        "value_p50_error": (
            value_p50 - final_value
            if value_p50 is not None and final_value is not None
            else None
        ),
        "warehouse_p50": warehouse_p50,
        "warehouse_p50_error": (
            warehouse_p50 - final_cells
            if warehouse_p50 is not None and final_cells is not None
            else None
        ),
        "layout_fit_p50": layout_p50,
        "layout_fit_p50_error": (
            layout_p50 - final_cells
            if layout_p50 is not None and final_cells is not None
            else None
        ),
        "highest_bid": highest_bid,
        "attack_bid": attack_bid,
        "stop_bid": stop_bid,
        "v2_q6_match_rate": q6_match_rate,
        "v2_q6_prior_match_rate": q6_prior_match_rate,
        "v2_q6_prior_expected_count": q6_prior_expected_count,
        "v2_q6_prior_expected_cells": q6_prior_expected_cells,
        "v2_q6_prior_expected_value": q6_prior_expected_value,
        "v2_prior_expected_count": prior_expected_count,
        "v2_prior_expected_cells": prior_expected_cells,
        "v2_prior_expected_value": prior_expected_value,
        "v2_prior_expected_decision_value": prior_expected_decision_value,
        "v2_prior_expected_tail_replacement_decision_value": (
            prior_expected_tail_replacement_decision_value
        ),
        "v2_q6_value_p90": q6_value_p90,
        "v2_q6_decision_value_p90": q6_decision_value_p90,
        "v2_q6_tail_replacement_estimate_p90": q6_tail_replacement_estimate_p90,
        "v2_q6_count_p90": q6_count_p90,
        "v2_q6_cells_p90": q6_cells_p90,
        "v2_remaining_cells_after_layout_p10": remaining_cells_after_layout_p10,
        "v2_remaining_cells_after_layout_p50": remaining_cells_after_layout_p50,
        "v2_remaining_cells_after_layout_p90": remaining_cells_after_layout_p90,
        "v2_q6_space_pressure_p50": q6_space_pressure_p50,
        "v2_q6_space_pressure_p90": q6_space_pressure_p90,
        "v2_q6_space_overflow_rate": q6_space_overflow_rate,
        "v2_q6_count_p90_under_prior_by": (
            max(0.0, q6_prior_expected_count - q6_count_p90)
            if q6_prior_expected_count is not None
            and q6_count_p90 is not None
            else None
        ),
        "v2_q6_cells_p90_under_prior_by": (
            max(0.0, q6_prior_expected_cells - q6_cells_p90)
            if q6_prior_expected_cells is not None
            and q6_cells_p90 is not None
            else None
        ),
        "q6_count_cell_prior_risk": bool(q6_prior_gap_summary),
        "q6_count_cell_prior_gap": q6_prior_gap_summary,
        "q6_count_cell_prior_floor_value": q6_prior_floor_value,
        "q6_practical_gate": q6_practical_gate,
        "q6_practical_p90": q6_practical_p90,
        "q6_practical_gate_hit": q6_practical_gate_hit,
        "q6_no_plannable_control": no_plannable_q6_control,
        "q6_zero_q6_proven_control": zero_q6_proven_control,
        "q6_practical_gate_no_plannable_control": (
            q6_practical_gate_hit and no_plannable_q6_control
        ),
        "q6_practical_gate_no_plannable_positive_proxy": (
            q6_practical_gate_hit
            and no_plannable_q6_control
            and (q6_practical_p90 or 0) > 0
        ),
        "q6_practical_gate_zero_q6_proven_false_positive": (
            q6_practical_gate_hit
            and zero_q6_proven_control
            and (q6_practical_p90 or 0) > 0
        ),
        "q6_practical_gate_false_positive_proxy": (
            q6_practical_gate_hit
            and no_plannable_q6_control
            and (q6_practical_p90 or 0) > 0
        ),
        "q6_practical_gate_under_before": q6_practical_under_before,
        "q6_practical_gate_covered_after": q6_practical_covered_after,
        "q6_practical_gate_helped": (
            q6_practical_under_before and q6_practical_covered_after
        ),
        "q6_practical_p90_under_by": (
            max(0, final_q6_decision_value - q6_practical_p90)
            if q6_practical_p90 is not None
            else None
        ),
        "q6_formal_prior_floor_label": formal_prior_floor.get("label"),
        "q6_formal_prior_floor_gate": formal_prior_floor.get("gate"),
        "q6_formal_prior_floor_evidence_profile": formal_prior_floor.get(
            "evidence_profile_key"
        ),
        "q6_formal_prior_floor_active": bool(formal_prior_floor.get("active")),
        "q6_formal_prior_floor_active_prior_floor_ratio": _parse_float_text(
            formal_prior_floor.get("active_prior_floor_ratio")
        ),
        "v3_post_shadow_label": v3_shadow.get("label"),
        "v3_post_shadow_error": v3_shadow.get("error"),
        "v3_post_shadow_trials": _parse_int_text(v3_shadow.get("trials")),
        "v3_post_available": v3_post_available,
        "v3_post_ready": v3_post_ready,
        "v3_post_strict_ready": v3_post_strict_ready,
        "v3_post_affects_bid": v3_post_affects_bid,
        "v3_post_match_scope": v3_post_match_scope,
        "v3_post_n_total": v3_post_n_total,
        "v3_post_n_matched": v3_post_n_matched,
        "v3_post_n_strict_matched": v3_post_n_strict_matched,
        "v3_post_match_rate": v3_post_match_rate,
        "v3_post_strict_match_rate": v3_post_strict_match_rate,
        "v3_post_q6_present_rate": v3_post_q6_present_rate,
        "v3_post_numeric_constraints": _parse_int_text(
            v3_shadow.get("numeric_constraints")
        ),
        "v3_post_item_anchors": _parse_int_text(v3_shadow.get("item_anchors")),
        "v3_post_shape_anchors": _parse_int_text(v3_shadow.get("shape_anchors")),
        "v3_post_quality_floor_anchors": _parse_int_text(
            v3_shadow.get("quality_floor_anchors")
        ),
        "v3_post_conflicts": _parse_int_text(v3_shadow.get("conflicts")),
        "v3_summary_feasible": bool(v3_shadow.get("v3_summary_feasible")),
        "v3_summary_known_count_floor": v3_summary_known_count_floor,
        "v3_summary_known_cells_floor": v3_summary_known_cells_floor,
        "v3_summary_known_value_floor": v3_summary_known_value_floor,
        "v3_summary_session_total_count_exact": (
            v3_summary_session_total_count_exact
        ),
        "v3_summary_session_total_cells_exact": (
            v3_summary_session_total_cells_exact
        ),
        "v3_summary_q6_count_floor": v3_summary_q6_count_floor,
        "v3_summary_q6_cells_floor": v3_summary_q6_cells_floor,
        "v3_summary_q6_value_floor": v3_summary_q6_value_floor,
        "v3_post_formal_decision_value_p50": v3_post_formal_p50,
        "v3_post_formal_decision_value_p90": v3_post_formal_p90,
        "v3_post_tail_replacement_decision_value_p50": (
            v3_post_tail_replacement_p50
        ),
        "v3_post_tail_replacement_decision_value_p90": (
            v3_post_tail_replacement_p90
        ),
        "v3_post_q6_formal_decision_value_p50": v3_post_q6_formal_p50,
        "v3_post_q6_formal_decision_value_p90": v3_post_q6_formal_p90,
        "v3_post_q6_count_p50": v3_post_q6_count_p50,
        "v3_post_q6_count_p90": v3_post_q6_count_p90,
        "v3_post_q6_cells_p50": v3_post_q6_cells_p50,
        "v3_post_q6_cells_p90": v3_post_q6_cells_p90,
        "v3_post_total_cells_p50": v3_post_total_cells_p50,
        "v3_post_total_cells_p90": v3_post_total_cells_p90,
        "v3_post_diagnostics": v3_shadow.get("v3_post_diagnostics"),
        "v3_prior_available": v3_prior_available,
        "v3_prior_error": v3_prior_error,
        "v3_prior_map_id": v3_prior_map_id,
        "v3_prior_map_name": v3_prior_map_name,
        "v3_prior_items_per_session_min": v3_prior_items_per_session_min,
        "v3_prior_items_per_session_max": v3_prior_items_per_session_max,
        "v3_capacity_total_count_source": v3_capacity_total_count_source,
        "v3_capacity_total_count_target": v3_capacity_total_count_target,
        "v3_capacity_truth_item_count": v3_capacity_truth_item_count,
        "v3_capacity_prior_items_per_session_min": v3_prior_items_per_session_min,
        "v3_capacity_prior_items_per_session_max": v3_prior_items_per_session_max,
        "v3_capacity_target_prior_max_delta": v3_capacity_target_prior_max_delta,
        "v3_capacity_truth_prior_max_delta": v3_capacity_truth_prior_max_delta,
        "v3_capacity_target_truth_delta": v3_capacity_target_truth_delta,
        "v3_capacity_target_prior_max_ratio": _numeric_ratio(
            v3_capacity_total_count_target,
            v3_prior_items_per_session_max,
        ),
        "v3_capacity_truth_prior_max_ratio": _numeric_ratio(
            v3_capacity_truth_item_count,
            v3_prior_items_per_session_max,
        ),
        "v3_capacity_flags": "+".join(v3_capacity_flags),
        "v3_capacity_cases": "+".join(v3_capacity_cases),
        "v3_prior_pool_count": v3_prior_pool_count,
        "v3_prior_expected_draws": v3_prior_expected_draws,
        "v3_prior_expected_count": v3_prior_expected_count,
        "v3_prior_expected_cells": v3_prior_expected_cells,
        "v3_prior_expected_value": v3_prior_expected_value,
        "v3_prior_q6_draw_probability": v3_prior_q6_draw_probability,
        "v3_prior_q6_session_probability": v3_prior_q6_session_probability,
        "v3_prior_q6_expected_count": v3_prior_q6_expected_count,
        "v3_prior_q6_expected_cells": v3_prior_q6_expected_cells,
        "v3_prior_q6_expected_value": v3_prior_q6_expected_value,
        "v3_robust_available": v3_robust_available,
        "v3_robust_affects_bid": v3_robust_affects_bid,
        "v3_robust_status": v3_robust_status,
        "v3_robust_prior_usable": v3_robust_prior_usable,
        "v3_robust_prior_trusted": v3_robust_prior_trusted,
        "v3_robust_fallback_mode": v3_robust_fallback_mode,
        "v3_robust_activity_candidate": v3_robust_activity_candidate,
        "v3_robust_prior_stress_score": v3_robust_prior_stress_score,
        "v3_robust_reasons": v3_robust_reasons,
        "v3_ccv_available": v3_ccv_available,
        "v3_ccv_ready": v3_ccv_ready,
        "v3_ccv_affects_bid": v3_ccv_affects_bid,
        "v3_ccv_match_scope": v3_ccv_match_scope,
        "v3_ccv_n_matched": v3_ccv_n_matched,
        "v3_ccv_q6_present_rate": v3_ccv_q6_present_rate,
        "v3_ccv_q6_count_p50": v3_ccv_q6_count_p50,
        "v3_ccv_q6_count_p90": v3_ccv_q6_count_p90,
        "v3_ccv_q6_cells_p50": v3_ccv_q6_cells_p50,
        "v3_ccv_q6_cells_p90": v3_ccv_q6_cells_p90,
        "v3_ccv_q6_formal_decision_value_p50": v3_ccv_q6_formal_p50,
        "v3_ccv_q6_formal_decision_value_p90": v3_ccv_q6_formal_p90,
        "v3_ccv_diagnostics": v3_shadow.get("v3_ccv_diagnostics"),
        "v3_resid_available": v3_resid_available,
        "v3_resid_ready": v3_resid_ready,
        "v3_resid_affects_bid": v3_resid_affects_bid,
        "v3_resid_match_scope": v3_resid_match_scope,
        "v3_resid_n_matched": v3_resid_n_matched,
        "v3_resid_q6_present_rate": v3_resid_q6_present_rate,
        "v3_resid_q6_count_p50": v3_resid_q6_count_p50,
        "v3_resid_q6_count_p90": v3_resid_q6_count_p90,
        "v3_resid_q6_cells_p50": v3_resid_q6_cells_p50,
        "v3_resid_q6_cells_p90": v3_resid_q6_cells_p90,
        "v3_resid_q6_value_p50": v3_resid_q6_value_p50,
        "v3_resid_q6_value_p90": v3_resid_q6_value_p90,
        "v3_resid_diagnostics": v3_shadow.get("v3_resid_diagnostics"),
        "v3_resid_gate_available": v3_resid_gate_available,
        "v3_resid_gate_ready": v3_resid_gate_ready,
        "v3_resid_gate_affects_bid": v3_resid_gate_affects_bid,
        "v3_resid_gate_active": v3_resid_gate_active,
        "v3_resid_gate_status": v3_resid_gate_status,
        "v3_resid_gate_gate_reason": v3_resid_gate_gate_reason,
        "v3_resid_gate_source": v3_resid_gate_source,
        "v3_resid_gate_q6_count_p50": v3_resid_gate_q6_count_p50,
        "v3_resid_gate_q6_cells_p50": v3_resid_gate_q6_cells_p50,
        "v3_resid_gate_q6_value_p50": v3_resid_gate_q6_value_p50,
        "v3_resid_gate_q6_count_delta_p50": v3_resid_gate_q6_count_delta_p50,
        "v3_resid_gate_q6_cells_delta_p50": v3_resid_gate_q6_cells_delta_p50,
        "v3_resid_gate_q6_value_delta_p50": v3_resid_gate_q6_value_delta_p50,
        "v3_resid_gate_diagnostics": v3_shadow.get("v3_resid_gate_diagnostics"),
        "v3_cal_available": v3_cal_available,
        "v3_cal_ready": v3_cal_ready,
        "v3_cal_active": v3_cal_active,
        "v3_cal_affects_bid": v3_cal_affects_bid,
        "v3_cal_status": v3_cal_status,
        "v3_cal_gate_reason": v3_cal_gate_reason,
        "v3_cal_scale": v3_cal_scale,
        "v3_cal_archive_sessions": v3_cal_archive_sessions,
        "v3_cal_median_ratio": v3_cal_median_ratio,
        "v3_cal_p90_ratio": v3_cal_p90_ratio,
        "v3_cal_baseline_formal_p50_mae": v3_cal_baseline_formal_mae,
        "v3_cal_baseline_formal_p50_bias": v3_cal_baseline_formal_bias,
        "v3_cal_formal_decision_value_p50": v3_cal_formal_p50,
        "v3_cal_formal_decision_value_p90": v3_cal_formal_p90,
        "v3_cal_q6_formal_decision_value_p50": v3_cal_q6_formal_p50,
        "v3_cal_q6_formal_decision_value_p90": v3_cal_q6_formal_p90,
        "v3_cal_diagnostics": v3_shadow.get("v3_cal_diagnostics"),
        "v3_under_available": v3_under_available,
        "v3_under_ready": v3_under_ready,
        "v3_under_active": v3_under_active,
        "v3_under_candidate": v3_under_candidate,
        "v3_under_affects_bid": v3_under_affects_bid,
        "v3_under_status": v3_under_status,
        "v3_under_gate_reason": v3_under_gate_reason,
        "v3_under_scale": v3_under_scale,
        "v3_under_hero_map_id": v3_under_hero_map_id,
        "v3_under_source": v3_under_source,
        "v3_under_archive_sessions": v3_under_archive_sessions,
        "v3_under_formal_decision_value_p50": v3_under_formal_p50,
        "v3_under_formal_decision_value_p90": v3_under_formal_p90,
        "v3_under_q6_formal_decision_value_p50": v3_under_q6_formal_p50,
        "v3_under_q6_formal_decision_value_p90": v3_under_q6_formal_p90,
        "v3_under_diagnostics": v3_shadow.get("v3_under_diagnostics"),
        "v3_tail_review_available": v3_tail_review_available,
        "v3_tail_review_ready": v3_tail_review_ready,
        "v3_tail_review_active": v3_tail_review_active,
        "v3_tail_review_candidate": v3_tail_review_candidate,
        "v3_tail_review_hurt_guard": v3_tail_review_hurt_guard,
        "v3_tail_review_affects_bid": v3_tail_review_affects_bid,
        "v3_tail_review_status": v3_tail_review_status,
        "v3_tail_review_gate_reason": v3_tail_review_gate_reason,
        "v3_tail_review_hero_map_id": v3_tail_review_hero_map_id,
        "v3_tail_review_source": v3_tail_review_source,
        "v3_tail_review_archive_sessions": v3_tail_review_archive_sessions,
        "v3_tail_review_tail_delta_p50_mae": v3_tail_review_tail_delta,
        "v3_tail_review_q6_tail_delta_p50_mae": v3_tail_review_q6_tail_delta,
        "v3_tail_review_tail_replacement_decision_value_p50": (
            v3_tail_review_tail_p50
        ),
        "v3_tail_review_tail_replacement_decision_value_p90": (
            v3_tail_review_tail_p90
        ),
        "v3_tail_review_q6_tail_replacement_decision_value_p50": (
            v3_tail_review_q6_tail_p50
        ),
        "v3_tail_review_q6_tail_replacement_decision_value_p90": (
            v3_tail_review_q6_tail_p90
        ),
        "v3_tail_review_diagnostics": v3_shadow.get("v3_tail_review_diagnostics"),
        "v3_fv_available": v3_fv_available,
        "v3_fv_ready": v3_fv_ready,
        "v3_fv_active": v3_fv_active,
        "v3_fv_candidate": v3_fv_candidate,
        "v3_fv_affects_bid": v3_fv_affects_bid,
        "v3_fv_status": v3_fv_status,
        "v3_fv_gate_reason": v3_fv_gate_reason,
        "v3_fv_source": v3_fv_source,
        "v3_fv_stress_class": v3_fv_stress_class,
        "v3_fv_capacity_flags": v3_fv_capacity_flags,
        "v3_fv_formal_decision_value_p50": v3_fv_formal_p50,
        "v3_fv_formal_decision_value_p90": v3_fv_formal_p90,
        "v3_fv_q6_formal_decision_value_p50": v3_fv_q6_formal_p50,
        "v3_fv_q6_formal_decision_value_p90": v3_fv_q6_formal_p90,
        "v3_fv_diagnostics": v3_shadow.get("v3_fv_diagnostics"),
        "v3_fv_total_count_source": v3_shadow.get("v3_fv_total_count_source"),
        "v3_fv_total_count_target": _parse_float_text(
            v3_shadow.get("v3_fv_total_count_target")
        ),
        "v3_fv_total_count_prior_expected": _parse_float_text(
            v3_shadow.get("v3_fv_total_count_prior_expected")
        ),
        "v3_fv_total_count_target_prior_ratio": _parse_float_text(
            v3_shadow.get("v3_fv_total_count_target_prior_ratio")
        ),
        "v3_fv_total_cells_source": v3_shadow.get("v3_fv_total_cells_source"),
        "v3_fv_total_cells_target": _parse_float_text(
            v3_shadow.get("v3_fv_total_cells_target")
        ),
        "v3_fv_total_cells_prior_expected": _parse_float_text(
            v3_shadow.get("v3_fv_total_cells_prior_expected")
        ),
        "v3_fv_total_cells_target_prior_ratio": _parse_float_text(
            v3_shadow.get("v3_fv_total_cells_target_prior_ratio")
        ),
        "v3_fv_q6_count_source": v3_shadow.get("v3_fv_q6_count_source"),
        "v3_fv_q6_count_target": _parse_float_text(
            v3_shadow.get("v3_fv_q6_count_target")
        ),
        "v3_fv_q6_count_prior_expected": _parse_float_text(
            v3_shadow.get("v3_fv_q6_count_prior_expected")
        ),
        "v3_fv_q6_count_target_prior_ratio": _parse_float_text(
            v3_shadow.get("v3_fv_q6_count_target_prior_ratio")
        ),
        "v3_fv_q6_cells_source": v3_shadow.get("v3_fv_q6_cells_source"),
        "v3_fv_q6_cells_target": _parse_float_text(
            v3_shadow.get("v3_fv_q6_cells_target")
        ),
        "v3_fv_q6_cells_prior_expected": _parse_float_text(
            v3_shadow.get("v3_fv_q6_cells_prior_expected")
        ),
        "v3_fv_q6_cells_target_prior_ratio": _parse_float_text(
            v3_shadow.get("v3_fv_q6_cells_target_prior_ratio")
        ),
        "v3_fv_total_value_source": v3_shadow.get("v3_fv_total_value_source"),
        "v3_fv_total_value_target": _parse_float_text(
            v3_shadow.get("v3_fv_total_value_target")
        ),
        "v3_fv_total_value_prior_expected": _parse_float_text(
            v3_shadow.get("v3_fv_total_value_prior_expected")
        ),
        "v3_fv_total_value_target_prior_ratio": _parse_float_text(
            v3_shadow.get("v3_fv_total_value_target_prior_ratio")
        ),
        "v3_fv_q6_value_source": v3_shadow.get("v3_fv_q6_value_source"),
        "v3_fv_q6_value_target": _parse_float_text(
            v3_shadow.get("v3_fv_q6_value_target")
        ),
        "v3_fv_q6_value_prior_expected": _parse_float_text(
            v3_shadow.get("v3_fv_q6_value_prior_expected")
        ),
        "v3_fv_q6_value_target_prior_ratio": _parse_float_text(
            v3_shadow.get("v3_fv_q6_value_target_prior_ratio")
        ),
        "v3_scp_available": v3_scp_available,
        "v3_scp_ready": v3_scp_ready,
        "v3_scp_affects_bid": v3_scp_affects_bid,
        "v3_scp_active": v3_scp_active,
        "v3_scp_candidate": v3_scp_candidate,
        "v3_scp_missing_table": v3_scp_missing_table,
        "v3_scp_status": v3_scp_status,
        "v3_scp_gate_reason": v3_scp_gate_reason,
        "v3_scp_scope": v3_scp_scope,
        "v3_scp_group": v3_scp_group,
        "v3_scp_inventory_count_p95": v3_scp_inventory_p95,
        "v3_scp_inventory_count_max": v3_scp_inventory_max,
        "v3_scp_non_temp_inventory_count_p95": v3_scp_non_temp_p95,
        "v3_scp_non_temp_inventory_count_max": v3_scp_non_temp_max,
        "v3_scp_above_drop_after_temp_zodiac_rows": (
            v3_scp_above_drop_after_temp
        ),
        "v3_scp_above_round_after_temp_zodiac_rows": (
            v3_scp_above_round_after_temp
        ),
        "v3_scp_prior_max_to_observed_p95_delta": v3_scp_prior_p95_delta,
        "v3_scp_prior_max_to_observed_max_delta": v3_scp_prior_max_delta,
        "v3_scp_flags": v3_scp_flags,
        "v3_scp_diagnostics": v3_shadow.get("v3_scp_diagnostics"),
        "v3_cse_available": v3_cse_available,
        "v3_cse_ready": v3_cse_ready,
        "v3_cse_affects_bid": v3_cse_affects_bid,
        "v3_cse_active": v3_cse_active,
        "v3_cse_candidate": v3_cse_candidate,
        "v3_cse_pressure_candidate": v3_cse_pressure_candidate,
        "v3_cse_status": v3_cse_status,
        "v3_cse_gate_reason": v3_cse_gate_reason,
        "v3_cse_scope": v3_cse_scope,
        "v3_cse_group": v3_cse_group,
        "v3_cse_mechanism_classes": v3_shadow.get("v3_cse_mechanism_classes"),
        "v3_cse_source_evidence_classes": v3_shadow.get(
            "v3_cse_source_evidence_classes"
        ),
        "v3_cse_source_context_classes": v3_cse_source_context_classes,
        "v3_cse_unique_round_overflow_rows": v3_cse_unique_round_rows,
        "v3_cse_server_side_expansion_rows": v3_cse_server_rows,
        "v3_cse_session_capacity_source_semantics_rows": v3_cse_session_rows,
        "v3_cse_public_total_match_rows": v3_cse_public_rows,
        "v3_cse_full_action_rows": v3_cse_full_action_rows,
        "v3_cse_unique_non_temp_p95": v3_cse_unique_p95,
        "v3_cse_unique_non_temp_max": v3_cse_unique_max,
        "v3_cse_target_count_source": v3_cse_target_count_source,
        "v3_cse_target_count": v3_cse_target_count,
        "v3_cse_prior_items_per_session_max": v3_cse_prior_items_per_session_max,
        "v3_cse_target_prior_max_delta": v3_cse_target_prior_delta,
        "v3_cse_target_to_unique_non_temp_p95_delta": v3_cse_target_p95_delta,
        "v3_cse_prior_max_to_unique_non_temp_p95_delta": (
            v3_cse_prior_p95_delta
        ),
        "v3_cse_prior_max_to_unique_non_temp_max_delta": v3_cse_prior_max_delta,
        "v3_cse_flags": v3_cse_flags,
        "v3_cse_diagnostics": v3_shadow.get("v3_cse_diagnostics"),
        "v3_practical_available": bool(v3_shadow.get("v3_practical_available")),
        "v3_practical_ready": bool(v3_shadow.get("v3_practical_ready")),
        "v3_practical_affects_bid": bool(
            v3_shadow.get("v3_practical_affects_bid")
        ),
        "v3_practical_active": bool(v3_shadow.get("v3_practical_active")),
        "v3_practical_candidate": bool(v3_shadow.get("v3_practical_candidate")),
        "v3_practical_source": v3_shadow.get("v3_practical_source"),
        "v3_practical_mode": v3_shadow.get("v3_practical_mode"),
        "v3_practical_status": v3_shadow.get("v3_practical_status"),
        "v3_practical_recommendation": v3_shadow.get(
            "v3_practical_recommendation"
        ),
        "v3_practical_confidence": v3_shadow.get("v3_practical_confidence"),
        "v3_practical_source_lanes": v3_shadow.get("v3_practical_source_lanes"),
        "v3_practical_risk_flags": v3_shadow.get("v3_practical_risk_flags"),
        "v3_practical_reason": v3_shadow.get("v3_practical_reason"),
        "v3_practical_formal_decision_value_p50": v3_practical_formal_p50,
        "v3_practical_formal_decision_value_p90": v3_practical_formal_p90,
        "v3_practical_q6_formal_decision_value_p50": (
            v3_practical_q6_formal_p50
        ),
        "v3_practical_q6_formal_decision_value_p90": (
            v3_practical_q6_formal_p90
        ),
        "v3_practical_baseline_formal_decision_value_p50": _parse_int_text(
            v3_shadow.get("v3_practical_baseline_formal_decision_value_p50")
        ),
        "v3_practical_baseline_formal_decision_value_p90": _parse_int_text(
            v3_shadow.get("v3_practical_baseline_formal_decision_value_p90")
        ),
        "v3_practical_delta_formal_decision_value_p50": _parse_int_text(
            v3_shadow.get("v3_practical_delta_formal_decision_value_p50")
        ),
        "v3_practical_delta_formal_decision_value_p90": _parse_int_text(
            v3_shadow.get("v3_practical_delta_formal_decision_value_p90")
        ),
        "v3_practical_delta_q6_formal_decision_value_p50": _parse_int_text(
            v3_shadow.get("v3_practical_delta_q6_formal_decision_value_p50")
        ),
        "v3_practical_delta_q6_formal_decision_value_p90": _parse_int_text(
            v3_shadow.get("v3_practical_delta_q6_formal_decision_value_p90")
        ),
        "v3_practical_diagnostics": v3_shadow.get("v3_practical_diagnostics"),
        "v3_tail_review_tail_replacement_decision_value_p50_error": (
            v3_tail_review_tail_p50 - final_replacement_decision_value
            if v3_tail_review_tail_p50 is not None
            and final_replacement_decision_value is not None
            else None
        ),
        "v3_tail_review_tail_replacement_decision_value_p90_under_by": (
            max(0, final_replacement_decision_value - v3_tail_review_tail_p90)
            if v3_tail_review_tail_p90 is not None
            and final_replacement_decision_value is not None
            else None
        ),
        "v3_tail_review_q6_tail_replacement_decision_value_p50_error": (
            v3_tail_review_q6_tail_p50
            - final_q6_decision_value_with_tail_replacement
            if v3_tail_review_q6_tail_p50 is not None
            else None
        ),
        "v3_tail_review_q6_tail_replacement_decision_value_p90_under_by": (
            max(
                0,
                final_q6_decision_value_with_tail_replacement
                - v3_tail_review_q6_tail_p90,
            )
            if v3_tail_review_q6_tail_p90 is not None
            else None
        ),
        "v3_under_formal_decision_value_p50_error_vs_formal": (
            v3_under_formal_p50 - final_formal_decision_value
            if v3_under_formal_p50 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_under_formal_decision_value_p90_under_by": (
            max(0, final_formal_decision_value - v3_under_formal_p90)
            if v3_under_formal_p90 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_under_q6_formal_decision_value_p50_error": (
            v3_under_q6_formal_p50 - final_q6_decision_value
            if v3_under_q6_formal_p50 is not None
            else None
        ),
        "v3_under_q6_formal_decision_value_p90_under_by": (
            max(0, final_q6_decision_value - v3_under_q6_formal_p90)
            if v3_under_q6_formal_p90 is not None
            else None
        ),
        "v3_fv_formal_decision_value_p50_error_vs_formal": (
            v3_fv_formal_p50 - final_formal_decision_value
            if v3_fv_formal_p50 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_fv_formal_decision_value_p90_under_by": (
            max(0, final_formal_decision_value - v3_fv_formal_p90)
            if v3_fv_formal_p90 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_fv_q6_formal_decision_value_p50_error": (
            v3_fv_q6_formal_p50 - final_q6_decision_value
            if v3_fv_q6_formal_p50 is not None
            else None
        ),
        "v3_fv_q6_formal_decision_value_p90_under_by": (
            max(0, final_q6_decision_value - v3_fv_q6_formal_p90)
            if v3_fv_q6_formal_p90 is not None
            else None
        ),
        "v3_practical_formal_decision_value_p50_error_vs_formal": (
            v3_practical_formal_p50 - final_formal_decision_value
            if v3_practical_formal_p50 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_practical_formal_decision_value_p90_under_by": (
            max(0, final_formal_decision_value - v3_practical_formal_p90)
            if v3_practical_formal_p90 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_practical_q6_formal_decision_value_p50_error": (
            v3_practical_q6_formal_p50 - final_q6_decision_value
            if v3_practical_q6_formal_p50 is not None
            else None
        ),
        "v3_practical_q6_formal_decision_value_p90_under_by": (
            max(0, final_q6_decision_value - v3_practical_q6_formal_p90)
            if v3_practical_q6_formal_p90 is not None
            else None
        ),
        "v3_cal_formal_decision_value_p50_error_vs_formal": (
            v3_cal_formal_p50 - final_formal_decision_value
            if v3_cal_formal_p50 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_cal_formal_decision_value_p90_under_by": (
            max(0, final_formal_decision_value - v3_cal_formal_p90)
            if v3_cal_formal_p90 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_cal_q6_formal_decision_value_p50_error": (
            v3_cal_q6_formal_p50 - final_q6_decision_value
            if v3_cal_q6_formal_p50 is not None
            else None
        ),
        "v3_cal_q6_formal_decision_value_p90_under_by": (
            max(0, final_q6_decision_value - v3_cal_q6_formal_p90)
            if v3_cal_q6_formal_p90 is not None
            else None
        ),
        "v3_formal_decision_value_p50_error_vs_formal": (
            v3_post_formal_p50 - final_formal_decision_value
            if v3_post_formal_p50 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_formal_decision_value_p90_under_by": (
            max(0, final_formal_decision_value - v3_post_formal_p90)
            if v3_post_formal_p90 is not None
            and final_formal_decision_value is not None
            else None
        ),
        "v3_q6_formal_decision_value_p50_error": (
            v3_post_q6_formal_p50 - final_q6_decision_value
            if v3_post_q6_formal_p50 is not None
            else None
        ),
        "v3_q6_formal_decision_value_p90_under_by": (
            max(0, final_q6_decision_value - v3_post_q6_formal_p90)
            if v3_post_q6_formal_p90 is not None
            else None
        ),
        "q6_residual_boost_shadow_label": shadow.get("label"),
        "q6_residual_boost_shadow_gate": shadow.get("gate"),
        "q6_residual_boost_shadow_evidence_profile": shadow.get(
            "evidence_profile_key"
        ),
        "q6_residual_boost_shadow_active": q6_shadow_active,
        "q6_residual_boost_shadow_trials": _parse_int_text(shadow.get("trials")),
        "q6_residual_boost_shadow_active_boost": q6_shadow_active_boost,
        "q6_residual_boost_shadow_decision_value_p50": (
            q6_shadow_decision_value_p50
        ),
        "q6_residual_boost_shadow_decision_value_p90": (
            q6_shadow_decision_value_p90
        ),
        "q6_residual_boost_shadow_q6_decision_value_p90": (
            q6_shadow_q6_decision_value_p90
        ),
        "q6_residual_boost_shadow_q6_count_p90": q6_shadow_q6_count_p90,
        "q6_residual_boost_shadow_q6_cells_p90": q6_shadow_q6_cells_p90,
        "q6_residual_boost_shadow_q6_p90_delta": (
            q6_shadow_q6_decision_value_p90 - q6_decision_value_p90
            if q6_shadow_q6_decision_value_p90 is not None
            and q6_decision_value_p90 is not None
            else None
        ),
        "q6_residual_boost_shadow_under_before": q6_shadow_under_before,
        "q6_residual_boost_shadow_covered_after": q6_shadow_covered_after,
        "q6_residual_boost_shadow_helped": (
            q6_shadow_under_before and q6_shadow_covered_after
        ),
        "q6_residual_boost_shadow_no_plannable_control": (
            q6_shadow_active and no_plannable_q6_control
        ),
        "q6_residual_boost_shadow_no_plannable_positive_proxy": (
            q6_shadow_active
            and no_plannable_q6_control
            and (q6_shadow_q6_decision_value_p90 or 0) > 0
        ),
        "q6_residual_boost_shadow_zero_q6_proven_control": (
            q6_shadow_active and zero_q6_proven_control
        ),
        "q6_residual_boost_shadow_zero_q6_proven_false_positive": (
            q6_shadow_active
            and zero_q6_proven_control
            and (q6_shadow_q6_decision_value_p90 or 0) > 0
        ),
        "q6_residual_boost_shadow_false_positive_proxy": (
            q6_shadow_active
            and no_plannable_q6_control
            and (q6_shadow_q6_decision_value_p90 or 0) > 0
        ),
        **deep_floor_shadow_fields,
        **deep11_floor_shadow_fields,
        **hidden_floor_shadow_fields,
        **villa_floor_shadow_fields,
        **ethan_villa_random_floor_shadow_fields,
        **ethan_shipwreck_layout_conditional_shadow_fields,
        "q6_aisha_bottom_row_risk": bool(bottom_row_risk.get("active")),
        "layout_bottom_row": _parse_int_text(bottom_row_risk.get("bottom_row")),
        "layout_bottom_row_risk_threshold": _parse_int_text(
            bottom_row_risk.get("bottom_row_threshold")
        ),
        "q6_quality_only_local_count": _parse_int_text(
            quality_only_local_risk.get("count")
        ),
        "q6_quality_only_deepest_local_index": _parse_int_text(
            quality_only_local_risk.get("deepest_local_index")
        ),
        "q6_quality_only_deepest_start_row": _parse_int_text(
            quality_only_local_risk.get("deepest_start_row")
        ),
        "q6_quality_only_deep_local_risk": bool(
            quality_only_local_risk.get("active")
        ),
        "q6_quality_only_deep_row_threshold": _parse_int_text(
            quality_only_local_risk.get("deep_row_threshold")
        ),
        "v2_q6_value_p90_under_by": (
            max(0, final_q6_value - q6_value_p90)
            if q6_value_p90 is not None
            else None
        ),
        "v2_q6_decision_value_p90_under_by": (
            max(0, final_q6_decision_value - q6_decision_value_p90)
            if q6_decision_value_p90 is not None
            else None
        ),
        "q6_top_size_band": _q6_top_size_band(truth_breakdown),
        "q6_p90_misses_truth": (
            q6_value_p90 < final_q6_value
            if q6_value_p90 is not None
            and final_q6_value > 0
            else None
        ),
        "q6_plannable_p90_misses_truth": (
            q6_decision_value_p90 < final_q6_decision_value
            if q6_decision_value_p90 is not None
            and final_q6_decision_value > 0
            else None
        ),
        "v2_q6_tail_replacement_decision_value_p90_under_by": (
            max(
                0,
                final_q6_decision_value_with_tail_replacement
                - q6_decision_value_p90,
            )
            if q6_decision_value_p90 is not None
            and final_q6_tail_replacement_value > 0
            else None
        ),
        "v2_q6_tail_replacement_estimate_p90_under_by": (
            max(
                0,
                final_q6_decision_value_with_tail_replacement
                - q6_tail_replacement_estimate_p90,
            )
            if q6_tail_replacement_estimate_p90 is not None
            and final_q6_tail_replacement_value > 0
            else None
        ),
        "q6_tail_replacement_p90_misses_truth": (
            q6_decision_value_p90
            < final_q6_decision_value_with_tail_replacement
            if q6_decision_value_p90 is not None
            and final_q6_decision_value_with_tail_replacement > 0
            and final_q6_tail_replacement_value > 0
            else None
        ),
        "q6_tail_replacement_estimate_p90_misses_truth": (
            q6_tail_replacement_estimate_p90
            < final_q6_decision_value_with_tail_replacement
            if q6_tail_replacement_estimate_p90 is not None
            and final_q6_decision_value_with_tail_replacement > 0
            and final_q6_tail_replacement_value > 0
            else None
        ),
        "q6_false_low_risk": (
            q6_match_rate < 0.10
            if q6_match_rate is not None
            and final_q6_value > 0
            else None
        ),
        "q6_below_drop_prior": "q6_below_drop_prior:" in posterior_diagnostics,
        "relaxed_exact_used": "relaxed_exact_bucket_targets:" in posterior_diagnostics,
        "shape_target_count": shape_target_count,
        "category_target_count": category_target_count,
        "category_exclusion_count": category_exclusion_count,
        "anchor_count": anchor_count,
        "random_sample_avg_values": random_sample_avg_values,
        "random_sample_avg_signal_values": random_sample_avg_signal_values,
        "public_constraint_key": public_constraint_key,
        "evidence_profile_key": evidence_profile_key,
        "evidence_stage": evidence_stage,
        "information_density_score": density_score,
        "information_density_band": density_band,
        "hero_information_density": f"{artifact.get('hero')}|{density_band}",
        "posterior_samples": posterior_samples,
        "posterior_total_samples": posterior_total_samples,
        "layout_conflict": bool(layout_root),
        "layout_conflict_root": layout_root,
        "posterior_diagnostics": posterior_diagnostics,
        **size_bucket_eval_fields(
            posterior_diagnostics=posterior_diagnostics,
            action_result_rows=artifact.get("action_result_rows"),
        ),
        "stop_minus_final_value": (
            stop_bid - final_value
            if stop_bid is not None and final_value is not None
            else None
        ),
        "monitor_processing_seconds": artifact.get("processing_seconds"),
        "monitor_n_trials": artifact.get("n_trials"),
        "monitor_roi_trials": artifact.get("roi_trials"),
        "monitor_shadow_trials": artifact.get("shadow_trials"),
        "input_constraints_mode": input_constraints.get("mode"),
        "input_warehouse_total_cells": (
            (input_constraints.get("warehouse_total_cells") or {}).get("value")
            if isinstance(input_constraints.get("warehouse_total_cells"), Mapping)
            else None
        ),
        "input_warehouse_total_cells_approx": (
            (input_constraints.get("warehouse_total_cells_approx") or {}).get("value")
            if isinstance(
                input_constraints.get("warehouse_total_cells_approx"),
                Mapping,
            )
            else None
        ),
        "input_total_item_count": (
            (input_constraints.get("total_item_count") or {}).get("value")
            if isinstance(input_constraints.get("total_item_count"), Mapping)
            else None
        ),
    }


def _grid_item_name(
    item_id: int | None,
    items: Mapping[int, Item],
) -> str:
    if item_id is None:
        return ""
    item = items.get(int(item_id))
    return item.name if item is not None else ""


def _item_names(items: Mapping[int, Item]) -> dict[int, str]:
    return {
        int(item_id): item.name
        for item_id, item in items.items()
        if item.name
    }


def _action_send_rows(
    events: FatbeansCaptureEvents,
    items: Mapping[int, Item],
) -> list[dict[str, Any]]:
    item_names = _item_names(items)
    rows: list[dict[str, Any]] = []
    for send in events.sends:
        if send.kind != "action" or send.value is None:
            continue
        action_id = int(send.value)
        rows.append(
            {
                "sort": send.sort_id,
                "time": send.capture_time,
                "action_id": action_id,
                "tool": item_names.get(action_id, ""),
            }
        )
    return list(reversed(rows))


def _observed_action_summary(
    observed_items: Sequence[Any],
    item_names: Mapping[int, str],
) -> str:
    if not observed_items:
        return ""
    quality_counts = Counter(
        int(item.quality)
        for item in observed_items
        if getattr(item, "quality", None) is not None
    )
    parts = [
        f"Q{quality}x{count}"
        for quality, count in sorted(quality_counts.items(), reverse=True)
    ]
    named = [
        item_names.get(int(item.item_id), "")
        for item in observed_items
        if getattr(item, "item_id", None) is not None
    ]
    if named:
        parts.append("/".join(name for name in named[:3] if name))
    locals_ = [
        str(item.local_index)
        for item in observed_items
        if getattr(item, "local_index", None) is not None
    ]
    if locals_:
        parts.append("pos " + ",".join(locals_[:8]))
    return " / ".join(part for part in parts if part)


def _action_result_rows(
    events: FatbeansCaptureEvents,
    items: Mapping[int, Item],
    *,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    item_names = _item_names(items)
    latest_by_action: dict[int, tuple[int, dict[str, Any]]] = {}
    zero_implied_action_ids = {
        100104,
        100105,
        100106,
        100107,
        100108,
        100110,
        100111,
        100112,
        100113,
        100114,
        100116,
        100117,
        100118,
        100119,
        100120,
        100122,
        100123,
        100124,
        100125,
        100126,
    }

    def session_matches(candidate: str | None) -> bool:
        return session_id is None or candidate is None or candidate == session_id

    for state in events.states:
        if not session_matches(state.session_id):
            continue
        if state.message_id == 0x002D or state.inventory_items:
            continue
        priority = 2 if state.message_id == 0x0027 else 1
        for result in state.action_results:
            action_id = int(result.action_id)
            existing = latest_by_action.get(action_id)
            if existing is not None:
                existing_priority, existing_row = existing
                existing_sort = int(existing_row.get("sort") or 0)
                if priority < existing_priority:
                    continue
                if priority == existing_priority and state.sort_id < existing_sort:
                    continue
            latest_by_action[action_id] = (
                priority,
                {
                    "sort": state.sort_id,
                    "time": state.capture_time,
                    "action_id": action_id,
                    "tool": item_names.get(action_id, ""),
                    "result": result.result,
                    "result_field": result.result_field,
                    "revealed_items": len(result.observed_items),
                    "revealed_items_detail": _observed_items_detail(
                        result.observed_items,
                        item_names,
                    ),
                    "revealed_summary": _observed_action_summary(
                        result.observed_items,
                        item_names,
                    ),
                },
            )
    for send in sorted(events.sends, key=lambda item: item.sort_id, reverse=True):
        if send.kind != "action" or send.value is None:
            continue
        if not session_matches(send.session_id):
            continue
        action_id = int(send.value)
        if action_id not in zero_implied_action_ids:
            continue
        existing = latest_by_action.get(action_id)
        if existing is not None:
            _existing_priority, existing_row = existing
            has_numeric_result = existing_row.get("result") is not None
            has_revealed_items = int(existing_row.get("revealed_items") or 0) > 0
            if has_numeric_result or has_revealed_items:
                continue
        has_later_state = any(
            state.sort_id > send.sort_id
            and session_matches(state.session_id)
            and (
                send.session_id is None
                or state.session_id is None
                or state.session_id == send.session_id
            )
            for state in events.states
        )
        if not has_later_state:
            continue
        latest_by_action[action_id] = (
            0,
            {
                "sort": send.sort_id,
                "time": send.capture_time,
                "action_id": action_id,
                "tool": item_names.get(action_id, ""),
                "result": 0,
                "result_field": None,
                "inferred_zero": True,
                "result_inference": "sent_action_without_result_after_later_state",
                "revealed_items": 0,
                "revealed_items_detail": [],
                "revealed_summary": "",
            },
        )
    return sorted(
        (row for _priority, row in latest_by_action.values()),
        key=lambda row: int(row.get("sort") or 0),
        reverse=True,
    )


def _observed_items_detail(
    observed_items: Sequence[Any],
    item_names: Mapping[int, str] | None = None,
) -> list[dict[str, Any]]:
    names = item_names or {}
    rows: list[dict[str, Any]] = []
    for item in observed_items:
        item_id = getattr(item, "item_id", None)
        item_name = ""
        if item_id is not None:
            try:
                item_name = names.get(int(item_id), "")
            except (TypeError, ValueError):
                item_name = ""
        row = {
            "local_index": item.local_index,
            "runtime_id": item.runtime_id,
            "item_id": item_id,
            "item_name": item_name,
            "quality": item.quality,
            "value": item.value,
            "shape_code": item.shape_code,
            "cells": item.cells,
        }
        rows.append(row)
    return rows


def _public_info_rows(
    events: FatbeansCaptureEvents,
    items: Mapping[int, Item],
) -> list[dict[str, Any]]:
    item_names = _item_names(items)
    latest_by_info: dict[int, dict[str, Any]] = {}
    for state in events.states:
        for info in state.public_infos:
            info_id = int(info.info_id)
            latest_by_info[info_id] = {
                "sort": state.sort_id,
                "time": state.capture_time,
                "info_id": info_id,
                "map_id": info.map_id,
                "value": info.value,
                "value_field": info.value_field,
                "revealed_items": len(info.observed_items),
                "revealed_items_detail": _observed_items_detail(
                    info.observed_items,
                    item_names,
                ),
                "revealed_summary": _observed_action_summary(
                    info.observed_items,
                    item_names,
                ),
            }
    return sorted(
        latest_by_info.values(),
        key=lambda row: int(row.get("sort") or 0),
        reverse=True,
    )


def _ahmad_ref_inputs_from_batches(
    batches: Sequence[LiveObservationBatch],
    *,
    hero: str | None,
) -> dict[str, Any]:
    """Compact pre-settlement bridge for the isolated structured reference overlay."""

    if str(hero or "").lower() not in {
        "aisha",
        "艾莎",
        "ahmed",
        "ahmad",
        "艾哈迈德",
        "victor",
        "维克托",
    }:
        return {}
    field_updates: list[dict[str, Any]] = []
    latest_values: dict[tuple[str, ...], Any] = {}
    for batch in batches:
        if batch.phase == "settled" or batch.event_kind == "session_settled":
            continue
        split_paths_in_batch = {
            (str(update.path[1]), str(update.path[2]))
            for update in batch.field_updates
            if len(update.path) >= 3 and tuple(update.path[:1]) == ("bucket_split",)
        }
        for update in batch.field_updates:
            path = tuple(str(part) for part in update.path)
            if not path:
                continue
            if (
                path[0] == "bucket"
                and len(path) >= 3
                and path[1] in {"1", "2"}
                and (
                    ("white" if path[1] == "1" else "green"),
                    path[2],
                )
                in split_paths_in_batch
            ):
                continue
            if path[0] == "session":
                relevant = path[1:] in {
                    ("total_item_count",),
                    ("total_count",),
                    ("total_cells",),
                    ("warehouse_total_cells",),
                }
            elif path[0] == "bucket_group" and len(path) >= 3:
                relevant = path[2] == "count"
            elif path[0] == "bucket" and len(path) >= 3:
                relevant = path[2] in {
                    "avg_cells",
                    "count",
                    "cells",
                    "total_cells",
                    "avg_value",
                    "average_value",
                    "value",
                    "value_sum",
                    "total_value",
                }
            elif path[0] == "bucket_split" and len(path) >= 3:
                relevant = path[2] in {"avg_cells", "count", "cells", "total_cells"}
            else:
                relevant = False
            if not relevant:
                continue
            latest_values[path] = update.value
            field_updates.append(
                {
                    "path": list(path),
                    "value": update.value,
                    "source": update.source,
                    "confidence": update.confidence,
                    "sequence": update.sequence or batch.sequence,
                    "event_kind": batch.event_kind,
                    "phase": batch.phase,
                }
            )

    avg_cells: dict[str, Any] = {}
    counts: dict[str, Any] = {}
    quality_cells: dict[str, Any] = {}
    avg_values: dict[str, Any] = {}
    quality_values: dict[str, Any] = {}
    count_sums: dict[str, Any] = {}
    split_avg_cells: dict[str, Any] = {}
    split_counts: dict[str, Any] = {}
    split_quality_cells: dict[str, Any] = {}
    for path, value in sorted(latest_values.items()):
        if path[:1] == ("session",):
            continue
        if len(path) >= 3 and path[0] == "bucket_group":
            if path[2] == "count":
                count_sums[str(path[1])] = value
            continue
        if len(path) >= 3 and path[0] == "bucket_split":
            split_key = str(path[1])
            if path[2] == "avg_cells":
                split_avg_cells[split_key] = value
            elif path[2] == "count":
                split_counts[split_key] = value
            elif path[2] in {"cells", "total_cells"}:
                split_quality_cells[split_key] = value
            continue
        if len(path) < 3 or path[0] != "bucket":
            continue
        quality = str(path[1])
        if quality == "2":
            continue
        key = "q1" if quality == "1" else f"q{quality}"
        if path[2] == "avg_cells":
            avg_cells[key] = value
        elif path[2] == "count":
            counts[key] = value
        elif path[2] in {"cells", "total_cells"}:
            quality_cells[key] = value
        elif path[2] in {"avg_value", "average_value"}:
            avg_values[key] = value
        elif path[2] in {"value", "value_sum", "total_value"}:
            quality_values[key] = value

    total_count = latest_values.get(("session", "total_item_count"))
    if total_count is None:
        total_count = latest_values.get(("session", "total_count"))
    total_cells = latest_values.get(("session", "total_cells"))
    if total_cells is None:
        total_cells = latest_values.get(("session", "warehouse_total_cells"))
    return {
        "source": "monitor_pre_settlement_field_updates",
        "total_count": total_count,
        "total_cells": total_cells,
        "avg_cells": avg_cells,
        "counts": counts,
        "quality_cells": quality_cells,
        "avg_values": avg_values,
        "quality_values": quality_values,
        "count_sums": count_sums,
        "split_avg_cells": split_avg_cells,
        "split_counts": split_counts,
        "split_quality_cells": split_quality_cells,
        "field_updates": field_updates,
    }


def _grid_item_table_shape_key(
    item: GridItemObservation,
    items: Mapping[int, Item],
) -> str | None:
    if item.shape_key:
        return item.shape_key
    if item.local_index is None or item.item_id is None:
        return None
    table_item = items.get(int(item.item_id))
    if table_item is None or table_item.shape_w <= 0 or table_item.shape_h <= 0:
        return None
    if item.cells and table_item.shape_w * table_item.shape_h != item.cells:
        return None
    return f"{table_item.shape_w}{table_item.shape_h}"


def _grid_item_table_category(
    item: GridItemObservation,
    items: Mapping[int, Item],
) -> int | None:
    if item.category is not None:
        return item.category
    if item.item_id is None:
        return None
    table_item = items.get(int(item.item_id))
    if table_item is None:
        return None
    for tag in table_item.tags:
        if int(tag) in _CATEGORY_LABELS:
            return int(tag)
    return None


def _minimap_rows_from_batch(
    batch: LiveObservationBatch,
    items: Mapping[int, Item],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    layout_source = (
        "settlement_inventory" if batch.phase == "settled" else "live_grid"
    )
    for item in batch.grid_items:
        shape_key = _grid_item_table_shape_key(item, items)
        category = _grid_item_table_category(item, items)
        display_item = (
            item
            if shape_key == item.shape_key and category == item.category
            else replace(item, shape_key=shape_key, category=category)
        )
        footprint = display_item.footprint()
        rows.append(
            {
                "category": category,
                "category_label": (
                    _CATEGORY_LABELS.get(category, str(category))
                    if category is not None
                    else ""
                ),
                "quality": item.quality,
                "runtime_id": item.runtime_id,
                "item_id": item.item_id,
                "item_name": _grid_item_name(item.item_id, items),
                "local_index": item.local_index,
                "cells": item.cells,
                "shape_key": shape_key,
                "row": footprint.row if footprint is not None else None,
                "col": footprint.col if footprint is not None else None,
                "width": footprint.width if footprint is not None else None,
                "height": footprint.height if footprint is not None else None,
                "source": item.source,
                "layout_source": layout_source,
            }
        )
    return rows


def _category_grid_items(
    batches: Sequence[LiveObservationBatch],
    items: Mapping[int, Item],
) -> list[dict[str, Any]]:
    batch = latest_grid_batch(batches)
    if batch is None:
        return []
    rows: list[dict[str, Any]] = []
    for item in batch.grid_items:
        if item.category is None:
            continue
        footprint = item.footprint()
        rows.append(
            {
                "category": item.category,
                "category_label": _CATEGORY_LABELS.get(
                    item.category,
                    str(item.category),
                ),
                "quality": item.quality,
                "runtime_id": item.runtime_id,
                "item_id": item.item_id,
                "item_name": _grid_item_name(item.item_id, items),
                "local_index": item.local_index,
                "cells": item.cells,
                "shape_key": item.shape_key,
                "row": footprint.row if footprint is not None else None,
                "col": footprint.col if footprint is not None else None,
                "width": footprint.width if footprint is not None else None,
                "height": footprint.height if footprint is not None else None,
                "source": item.source,
            }
        )
    return rows


def _minimap_grid_items(
    batches: Sequence[LiveObservationBatch],
    items: Mapping[int, Item],
) -> list[dict[str, Any]]:
    for candidate in reversed(batches):
        if candidate.phase != "settled" or not candidate.grid_items:
            continue
        rows = _minimap_rows_from_batch(candidate, items)
        if any(row.get("row") is not None and row.get("col") is not None for row in rows):
            return rows

    batch = latest_grid_batch(batches)
    if batch is None:
        return []
    return _minimap_rows_from_batch(batch, items)


def _parse_int_text(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _resolve_shadow_trials(n_trials: int, shadow_trials: int | None) -> int:
    if shadow_trials is not None:
        return max(1, int(shadow_trials))
    return max(1, min(int(n_trials), DEFAULT_Q6_SHADOW_TRIALS_CAP))


def _empty_v3_posterior_shadow(
    *,
    trials: int,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "label": "v3_summary_likelihood",
        "affects_bid": False,
        "trials": max(0, int(trials)),
        "error": error,
        "numeric_constraints": 0,
        "item_anchors": 0,
        "shape_anchors": 0,
        "quality_floor_anchors": 0,
        "conflicts": 0,
        **empty_feasible_summary_flat_dict(),
        **empty_posterior_flat_dict(),
        **empty_posterior_flat_dict(prefix="v3_ccv_"),
        **empty_posterior_flat_dict(prefix="v3_resid_"),
        **empty_residual_gate_flat_dict(),
        **empty_prior_flat_dict(),
        **empty_prior_robustness_flat_dict(),
        **empty_prior_calibration_flat_dict(),
        **empty_underestimate_repair_flat_dict(),
        **empty_tail_value_review_flat_dict(),
        **empty_formal_value_sampler_flat_dict(),
        **empty_settlement_count_prior_flat_dict(),
        **empty_capacity_source_expansion_flat_dict(),
        **empty_practical_advisory_flat_dict(),
    }


def _default_v3_prior_calibration_entries() -> dict[int, Any]:
    global _V3_PRIOR_CALIBRATION_CACHE
    if _V3_PRIOR_CALIBRATION_CACHE is None:
        _V3_PRIOR_CALIBRATION_CACHE = load_prior_calibration_entries(
            project_root() / "data" / "processed" / "v3_prior_calibration_shadow.json"
        )
    return _V3_PRIOR_CALIBRATION_CACHE


def _default_v3_underestimate_repair_entries() -> dict[tuple[str, int], Any]:
    global _V3_UNDERESTIMATE_REPAIR_CACHE
    if _V3_UNDERESTIMATE_REPAIR_CACHE is None:
        _V3_UNDERESTIMATE_REPAIR_CACHE = load_underestimate_repair_entries(
            project_root()
            / "data"
            / "processed"
            / "v3_underestimate_repair_shadow.json"
        )
    return _V3_UNDERESTIMATE_REPAIR_CACHE


def _default_v3_tail_value_review_entries() -> dict[tuple[str, int], Any]:
    global _V3_TAIL_VALUE_REVIEW_CACHE
    if _V3_TAIL_VALUE_REVIEW_CACHE is None:
        _V3_TAIL_VALUE_REVIEW_CACHE = load_tail_value_review_entries(
            project_root()
            / "data"
            / "processed"
            / "v3_tail_value_review_shadow.json"
        )
    return _V3_TAIL_VALUE_REVIEW_CACHE


def _default_v3_settlement_count_prior_entries() -> dict[tuple[str, str], Any]:
    global _V3_SETTLEMENT_COUNT_PRIOR_CACHE
    if _V3_SETTLEMENT_COUNT_PRIOR_CACHE is None:
        _V3_SETTLEMENT_COUNT_PRIOR_CACHE = load_settlement_count_prior_entries(
            project_root()
            / "data"
            / "processed"
            / "v3_settlement_count_prior_shadow.json"
        )
    return _V3_SETTLEMENT_COUNT_PRIOR_CACHE


def _default_v3_capacity_source_expansion_entries() -> dict[tuple[str, str], Any]:
    global _V3_CAPACITY_SOURCE_EXPANSION_CACHE
    if _V3_CAPACITY_SOURCE_EXPANSION_CACHE is None:
        _V3_CAPACITY_SOURCE_EXPANSION_CACHE = load_capacity_source_expansion_entries(
            project_root()
            / "data"
            / "processed"
            / "v3_capacity_source_expansion_shadow.json"
        )
    return _V3_CAPACITY_SOURCE_EXPANSION_CACHE


def _v3_posterior_shadow_summary(
    events: FatbeansCaptureEvents,
    *,
    map_id: int | None,
    hero: str | None = None,
    tables: MonitorTables,
    trials: int,
    seed: int,
) -> dict[str, Any]:
    out = _empty_v3_posterior_shadow(trials=trials)
    prior_fields = summarize_drop_prior_flat_dict(
        map_id,
        maps=tables.maps,
        drops=tables.drops,
        items=tables.items,
    )
    out.update(prior_fields)

    def finish(summary: Any | None = None) -> dict[str, Any]:
        out.update(
            assess_prior_robustness(
                map_id=map_id,
                map_family=_map_family_from_id(map_id),
                summary=summary,
                prior_fields=prior_fields,
                posterior_fields=out,
            ).to_flat_dict()
        )
        return out

    if map_id is None:
        out["error"] = "missing_map_id"
        return finish()
    bid_map = tables.maps.get(int(map_id))
    if bid_map is None:
        out["error"] = "unknown_map_id"
        return finish()
    if trials <= 0:
        out["error"] = "no_trials"
        return finish()
    summary = None
    try:
        evidence_events = events_from_fatbeans(events)
        constraints = compile_hard_constraints(evidence_events)
        summary = compile_feasible_summary(constraints)
        truths = sample_truth_bank(
            int(map_id),
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
            n_trials=trials,
            seed=seed,
        )
        replacement_values = ordinary_shape_replacement_values(
            int(map_id),
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
        )
        calibration_entry = _default_v3_prior_calibration_entries().get(int(map_id))
        underestimate_entry = underestimate_entry_for(
            _default_v3_underestimate_repair_entries(),
            hero=hero,
            map_id=map_id,
        )
        tail_review_entry = tail_value_review_entry_for(
            _default_v3_tail_value_review_entries(),
            hero=hero,
            map_id=map_id,
        )
        settlement_count_prior_entry = settlement_count_prior_entry_for(
            _default_v3_settlement_count_prior_entries(),
            map_id=map_id,
        )
        capacity_source_expansion_entry = capacity_source_expansion_entry_for(
            _default_v3_capacity_source_expansion_entries(),
            map_id=map_id,
            map_family=_map_family_from_id(map_id),
        )
        pipeline = estimate_shadow_pipeline(
            map_id=int(map_id),
            map_name=bid_map.name,
            summary=summary,
            truths=truths,
            constraints=constraints,
            replacement_values=replacement_values,
            calibration_entry=calibration_entry,
            underestimate_entry=underestimate_entry,
            tail_review_entry=tail_review_entry,
            settlement_count_prior_entry=settlement_count_prior_entry,
            capacity_source_expansion_entry=capacity_source_expansion_entry,
            hero=hero,
            prior_fields=prior_fields,
            evidence_events=evidence_events,
        )
    except Exception as exc:
        out["error"] = type(exc).__name__
        return finish(summary)
    out.update(
        {
            "numeric_constraints": len(constraints.numeric),
            "item_anchors": len(constraints.item_anchors),
            "shape_anchors": len(constraints.shape_anchors),
            "quality_floor_anchors": len(constraints.quality_floor_anchors),
            "conflicts": len(constraints.conflicts),
        }
    )
    out.update(summary.to_flat_dict())
    out.update(pipeline.to_flat_dict())
    return finish(summary)


def build_monitor_artifact_from_events(
    events: FatbeansCaptureEvents,
    *,
    file: str = "",
    tables: MonitorTables,
    n_trials: int = 500,
    roi_trials: int = 250,
    shadow_trials: int | None = None,
    run_debug_shadows: bool = True,
    seed: int = 20260530,
    formal_mode: str | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable live monitor artifact from parsed events."""
    started_at = time.perf_counter()
    formal_mode_requested = _resolve_live_formal_mode(formal_mode)
    formal_mode_applied = LIVE_FORMAL_MODE_V2
    formal_mode_reason = "no_inference_session"
    batches = live_batches_from_fatbeans_events(events)
    (
        base_session,
        final_session,
        pre_settlement_state,
        _final_state,
    ) = _states_to_session(batches)
    latest_bids = latest_player_bids(events.states)
    observed_round = _latest_round(events)
    action_round = _action_round(events)
    phase = _latest_phase(events)
    layout_replay_rows = list(
        layout_replay_rows_from_stages(
            layout_replay_stages(events),
            comparison_policy=SAMPLE_FIT_LAYOUT_ESTIMATE_POLICY,
        )
    )
    layout_stage_rows = _brief_layout_stage_rows(layout_replay_rows)

    map_rows: list[dict[str, Any]] = []
    warehouse_rows: list[dict[str, Any]] = []
    v2_posterior_rows: list[dict[str, Any]] = []
    q6_residual_boost_shadow: dict[str, Any] = {}
    q6_formal_prior_floor: dict[str, Any] = {}
    q6_residual_deep_floor_shadow: dict[str, Any] = {}
    q6_residual_deep11_floor_shadow: dict[str, Any] = {}
    q6_residual_hidden_floor_shadow: dict[str, Any] = {}
    q6_residual_villa_floor_shadow: dict[str, Any] = {}
    q6_residual_ethan_villa_random_floor_shadow: dict[str, Any] = {}
    q6_residual_ethan_shipwreck_layout_conditional_shadow: dict[str, Any] = {}
    q6_residual_sampler_shadows: list[dict[str, Any]] = []
    q6_residual_boost_shadow_rows: list[dict[str, Any]] = []
    q6_aisha_bottom_row_risk: dict[str, Any] = {}
    q6_quality_only_local_risk: dict[str, Any] = {}
    tool_rows: list[dict[str, Any]] = []
    bid_rows: list[dict[str, Any]] = []
    v2_bid_rows: list[dict[str, Any]] = []
    v3_practical_bid_rows: list[dict[str, Any]] = []
    fallback_map_rows: list[dict[str, Any]] = []
    fallback_warehouse_rows: list[dict[str, Any]] = []
    fallback_bid_rows: list[dict[str, Any]] = []
    evidence_label = "暂无"
    evidence_profile_key = ""
    resolved_shadow_trials = _resolve_shadow_trials(n_trials, shadow_trials)
    v3_posterior_shadow: dict[str, Any] = _empty_v3_posterior_shadow(
        trials=resolved_shadow_trials,
    )
    inference_input_constraints: dict[str, Any] = {
        "mode": "no_inference_session",
    }
    problem: ResidualProblem | None = None
    model_map_id: int | None = None
    activity_map_alias: dict[str, Any] = {}
    if base_session is not None:
        activity_map_alias = _activity_shipwreck_alias(
            base_session.map_id,
            tables.maps,
            tables.drops,
        )
    if (
        base_session is not None
        and base_session.map_id not in tables.maps
        and not activity_map_alias
    ):
        evidence_label = f"unsupported_map:{base_session.map_id}"
        formal_mode_reason = "unsupported_map"
        inference_input_constraints = {
            "mode": "unsupported_map",
            "map_id": base_session.map_id,
        }
    elif base_session is not None:
        inference_base_session = base_session
        if activity_map_alias:
            model_map_id = int(activity_map_alias["model_map_id"])
            inference_base_session = replace(base_session, map_id=model_map_id)
        else:
            model_map_id = base_session.map_id
        candidate_map_ids = _candidate_map_ids_for_likelihood(
            inference_base_session.map_id,
            tables.maps,
        )
        evidence_label = "结算前最后状态"
        if activity_map_alias:
            evidence_label = (
                f"结算前最后状态（活动图按旧沉船 {model_map_id} 估）"
            )
        cells_tol = 8
        count_tol = 3
        inference_session, inference_input_constraints = (
            _inference_session_with_safe_totals(
                inference_base_session,
                pre_settlement_state,
            )
        )
        if activity_map_alias:
            inference_input_constraints = dict(inference_input_constraints)
            inference_input_constraints.update(
                {
                    "source_map_id": activity_map_alias["source_map_id"],
                    "model_map_id": activity_map_alias["model_map_id"],
                    "map_alias_mode": activity_map_alias["mode"],
                    "map_alias_reason": activity_map_alias["reason"],
                    "map_alias": activity_map_alias,
                }
            )
        base_results = estimate_map_likelihood(
            candidate_map_ids,
            inference_session,
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
            n_trials=n_trials,
            seed=seed,
            cells_tol=cells_tol,
            count_tol=count_tol,
        )
        warehouse_estimate = estimate_warehouse_cells(
            candidate_map_ids,
            inference_session,
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
            n_trials=n_trials,
            seed=seed,
            cells_tol=cells_tol,
            count_tol=count_tol,
        )
        if not any(result.n_matched for result in base_results):
            relaxed_session = _relax_exact_bucket_constraints(inference_session)
            if relaxed_session is not inference_session:
                relaxed_results = estimate_map_likelihood(
                    candidate_map_ids,
                    relaxed_session,
                    maps=tables.maps,
                    drops=tables.drops,
                    items=tables.items,
                    n_trials=n_trials,
                    seed=seed,
                    cells_tol=cells_tol,
                    count_tol=count_tol,
                )
                relaxed_warehouse_estimate = estimate_warehouse_cells(
                    candidate_map_ids,
                    relaxed_session,
                    maps=tables.maps,
                    drops=tables.drops,
                    items=tables.items,
                    n_trials=n_trials,
                    seed=seed,
                    cells_tol=cells_tol,
                    count_tol=count_tol,
                )
                if any(result.n_matched for result in relaxed_results):
                    inference_session = relaxed_session
                    base_results = relaxed_results
                    warehouse_estimate = relaxed_warehouse_estimate
                    evidence_label = f"{evidence_label}（放宽精确桶约束）"
        map_rows = _map_likelihood_result_rows(base_results, evidence_label)
        warehouse_rows = _warehouse_estimate_rows(warehouse_estimate)
        store = evidence_store_from_fatbeans_events(events)
        problem = build_residual_problem(
            inference_session.map_id,
            store,
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
            obs=inference_session,
        )
        evidence_profile_key = evidence_profile_key_from_problem(problem)
        q6_quality_only_local_risk = q6_quality_only_local_diagnostics(store)
        q6_quality_only_local_risk["active"] = (
            aisha_q6_quality_only_deep_local_risk(
                hero=inference_session.hero,
                map_family=_map_family_from_id(inference_session.map_id),
                evidence_profile_key=evidence_profile_key,
                deepest_start_row=q6_quality_only_local_risk.get(
                    "deepest_start_row"
                ),
            )
        )
        q6_quality_only_local_risk["deep_row_threshold"] = (
            AISHA_Q6_QUALITY_ONLY_DEEP_ROW_THRESHOLD
        )
        q6_aisha_bottom_row_risk = {
            "active": aisha_bottom_row_risk(
                hero=inference_session.hero,
                map_family=_map_family_from_id(inference_session.map_id),
                bottom_row=problem.layout.bottom_row,
            ),
            "bottom_row": problem.layout.bottom_row,
            "bottom_row_threshold": AISHA_BOTTOM_ROW_RISK_THRESHOLD,
        }
        active_shadow_boost = q6_residual_boost_for_profile(
            hero=inference_session.hero,
            map_family=_map_family_from_id(inference_session.map_id),
            evidence_profile_key=evidence_profile_key,
            requested_boost=5.0,
            gate="shipwreck_profile_v1",
            bottom_row=problem.layout.bottom_row,
        )
        active_deep_floor_ratio = q6_residual_prior_floor_ratio_for_profile(
            hero=inference_session.hero,
            map_family=_map_family_from_id(inference_session.map_id),
            evidence_profile_key=evidence_profile_key,
            requested_ratio=1.0,
            gate="aisha_shipwreck_deep_v1",
            bottom_row=problem.layout.bottom_row,
        )
        active_deep11_floor_ratio = q6_residual_prior_floor_ratio_for_profile(
            hero=inference_session.hero,
            map_family=_map_family_from_id(inference_session.map_id),
            evidence_profile_key=evidence_profile_key,
            requested_ratio=1.0,
            gate="aisha_shipwreck_deep11_v1",
            bottom_row=problem.layout.bottom_row,
        )
        active_hidden_floor_ratio = q6_residual_prior_floor_ratio_for_profile(
            hero=inference_session.hero,
            map_family=_map_family_from_id(inference_session.map_id),
            evidence_profile_key=evidence_profile_key,
            requested_ratio=1.5,
            gate="aisha_hidden_v1",
            bottom_row=problem.layout.bottom_row,
        )
        active_villa_floor_ratio = q6_residual_prior_floor_ratio_for_profile(
            hero=inference_session.hero,
            map_family=_map_family_from_id(inference_session.map_id),
            evidence_profile_key=evidence_profile_key,
            requested_ratio=0.5,
            gate="aisha_villa_shape_layout_v1",
            bottom_row=problem.layout.bottom_row,
        )
        active_ethan_villa_random_floor_ratio = (
            q6_residual_prior_floor_ratio_for_profile(
                hero=inference_session.hero,
                map_family=_map_family_from_id(inference_session.map_id),
                evidence_profile_key=evidence_profile_key,
                requested_ratio=1.0,
                gate="ethan_villa_random_avg_v1",
                bottom_row=problem.layout.bottom_row,
            )
        )
        active_ethan_shipwreck_layout_conditional = (
            q6_conditional_target_active_for_profile(
                hero=inference_session.hero,
                map_family=_map_family_from_id(inference_session.map_id),
                evidence_profile_key=evidence_profile_key,
                gate="ethan_shipwreck_layout_v1",
            )
        )
        active_ethan_shipwreck_layout_target_count = (
            4.0 if active_ethan_shipwreck_layout_conditional else 0.0
        )
        active_ethan_shipwreck_layout_target_cells = (
            15.0 if active_ethan_shipwreck_layout_conditional else 0.0
        )
        formal_prior_floor_ratio = active_deep_floor_ratio
        q6_formal_prior_floor = {
            "label": "aisha_deep_floor1",
            "gate": "aisha_shipwreck_deep_v1",
            "evidence_profile_key": evidence_profile_key,
            "active": formal_prior_floor_ratio > 0.0,
            "active_prior_floor_ratio": formal_prior_floor_ratio,
        }
        formal_prior_floor_kwargs = (
            {"q6_residual_prior_floor_ratio": formal_prior_floor_ratio}
            if formal_prior_floor_ratio > 0.0
            else {}
        )
        v2_report = estimate_posterior_v2(
            inference_session.map_id,
            inference_session,
            store,
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
            n_trials=n_trials,
            seed=seed + 2,
            cells_tol=cells_tol,
            count_tol=count_tol,
            **formal_prior_floor_kwargs,
        )
        shadow_report = None
        emitted_shadow_boost = active_shadow_boost if run_debug_shadows else 1.0
        if run_debug_shadows and active_shadow_boost > 1.0:
            shadow_report = estimate_posterior_v2(
                inference_session.map_id,
                inference_session,
                store,
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
                n_trials=resolved_shadow_trials,
                seed=seed + 2,
                cells_tol=cells_tol,
                count_tol=count_tol,
                q6_residual_boost=active_shadow_boost,
            )
        q6_residual_boost_shadow = _q6_residual_boost_shadow_summary(
            shadow_report,
            label="profile_b5",
            requested_boost=5.0,
            active_boost=emitted_shadow_boost,
            gate="shipwreck_profile_v1",
            evidence_profile_key=evidence_profile_key,
            trials=resolved_shadow_trials,
        )
        deep_floor_report = None
        if active_deep_floor_ratio > 0.0:
            deep_floor_report = estimate_posterior_v2(
                inference_session.map_id,
                inference_session,
                store,
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
                n_trials=resolved_shadow_trials,
                seed=seed + 2,
                cells_tol=cells_tol,
                count_tol=count_tol,
                q6_residual_prior_floor_ratio=active_deep_floor_ratio,
            )
        q6_residual_deep_floor_shadow = _q6_residual_boost_shadow_summary(
            deep_floor_report,
            label="aisha_deep_floor1",
            requested_boost=1.0,
            active_boost=1.0,
            requested_prior_floor_ratio=1.0,
            active_prior_floor_ratio=active_deep_floor_ratio,
            gate="aisha_shipwreck_deep_v1",
            evidence_profile_key=evidence_profile_key,
            trials=resolved_shadow_trials,
        )
        deep11_floor_report = None
        if active_deep11_floor_ratio > 0.0 and resolved_shadow_trials > 1:
            deep11_floor_report = estimate_posterior_v2(
                inference_session.map_id,
                inference_session,
                store,
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
                n_trials=resolved_shadow_trials,
                seed=seed + 2,
                cells_tol=cells_tol,
                count_tol=count_tol,
                q6_residual_prior_floor_ratio=active_deep11_floor_ratio,
            )
        q6_residual_deep11_floor_shadow = _q6_residual_boost_shadow_summary(
            deep11_floor_report,
            label="aisha_deep11_floor1",
            requested_boost=1.0,
            active_boost=1.0,
            requested_prior_floor_ratio=1.0,
            active_prior_floor_ratio=active_deep11_floor_ratio,
            gate="aisha_shipwreck_deep11_v1",
            evidence_profile_key=evidence_profile_key,
            trials=resolved_shadow_trials,
        )
        hidden_floor_report = None
        if active_hidden_floor_ratio > 0.0:
            hidden_floor_report = estimate_posterior_v2(
                inference_session.map_id,
                inference_session,
                store,
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
                n_trials=resolved_shadow_trials,
                seed=seed + 2,
                cells_tol=cells_tol,
                count_tol=count_tol,
                q6_residual_prior_floor_ratio=active_hidden_floor_ratio,
            )
        q6_residual_hidden_floor_shadow = _q6_residual_boost_shadow_summary(
            hidden_floor_report,
            label="aisha_hidden_floor15",
            requested_boost=1.0,
            active_boost=1.0,
            requested_prior_floor_ratio=1.5,
            active_prior_floor_ratio=active_hidden_floor_ratio,
            gate="aisha_hidden_v1",
            evidence_profile_key=evidence_profile_key,
            trials=resolved_shadow_trials,
        )
        villa_floor_report = None
        if active_villa_floor_ratio > 0.0:
            villa_floor_report = estimate_posterior_v2(
                inference_session.map_id,
                inference_session,
                store,
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
                n_trials=resolved_shadow_trials,
                seed=seed + 2,
                cells_tol=cells_tol,
                count_tol=count_tol,
                q6_residual_prior_floor_ratio=active_villa_floor_ratio,
            )
        q6_residual_villa_floor_shadow = _q6_residual_boost_shadow_summary(
            villa_floor_report,
            label="aisha_villa_floor05",
            requested_boost=1.0,
            active_boost=1.0,
            requested_prior_floor_ratio=0.5,
            active_prior_floor_ratio=active_villa_floor_ratio,
            gate="aisha_villa_shape_layout_v1",
            evidence_profile_key=evidence_profile_key,
            trials=resolved_shadow_trials,
        )
        ethan_villa_random_floor_report = None
        if (
            active_ethan_villa_random_floor_ratio > 0.0
            and resolved_shadow_trials > 1
        ):
            ethan_villa_random_floor_report = estimate_posterior_v2(
                inference_session.map_id,
                inference_session,
                store,
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
                n_trials=resolved_shadow_trials,
                seed=seed + 2,
                cells_tol=cells_tol,
                count_tol=count_tol,
                q6_residual_prior_floor_ratio=(
                    active_ethan_villa_random_floor_ratio
                ),
            )
        q6_residual_ethan_villa_random_floor_shadow = (
            _q6_residual_boost_shadow_summary(
                ethan_villa_random_floor_report,
                label="ethan_villa_random_avg_floor1",
                requested_boost=1.0,
                active_boost=1.0,
                requested_prior_floor_ratio=1.0,
                active_prior_floor_ratio=(
                    active_ethan_villa_random_floor_ratio
                ),
                gate="ethan_villa_random_avg_v1",
                evidence_profile_key=evidence_profile_key,
                trials=resolved_shadow_trials,
            )
        )
        ethan_shipwreck_layout_conditional_report = None
        if (
            active_ethan_shipwreck_layout_conditional
            and resolved_shadow_trials > 1
        ):
            ethan_shipwreck_layout_conditional_report = estimate_posterior_v2(
                inference_session.map_id,
                inference_session,
                store,
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
                n_trials=resolved_shadow_trials,
                seed=seed + 2,
                cells_tol=cells_tol,
                count_tol=count_tol,
                q6_conditional_target_count=(
                    active_ethan_shipwreck_layout_target_count
                ),
                q6_conditional_target_cells=(
                    active_ethan_shipwreck_layout_target_cells
                ),
            )
        q6_residual_ethan_shipwreck_layout_conditional_shadow = (
            _q6_residual_boost_shadow_summary(
                ethan_shipwreck_layout_conditional_report,
                label="ethan_shipwreck_layout_conditional_c4_cells15",
                requested_boost=1.0,
                active_boost=1.0,
                requested_conditional_target_count=4.0,
                active_conditional_target_count=(
                    active_ethan_shipwreck_layout_target_count
                ),
                requested_conditional_target_cells=15.0,
                active_conditional_target_cells=(
                    active_ethan_shipwreck_layout_target_cells
                ),
                gate="ethan_shipwreck_layout_v1",
                evidence_profile_key=evidence_profile_key,
                trials=resolved_shadow_trials,
            )
        )
        q6_residual_sampler_shadows = [
            q6_residual_boost_shadow,
            q6_residual_deep_floor_shadow,
            q6_residual_deep11_floor_shadow,
            q6_residual_hidden_floor_shadow,
            q6_residual_villa_floor_shadow,
            q6_residual_ethan_villa_random_floor_shadow,
            q6_residual_ethan_shipwreck_layout_conditional_shadow,
        ]
        q6_residual_boost_shadow_rows = _q6_residual_shadow_rows(
            q6_residual_sampler_shadows
        )
        q6_practical_reference = _q6_reference_with_shadow(
            _q6_prior_gap_summary(v2_report),
            q6_residual_ethan_shipwreck_layout_conditional_shadow,
        )
        v2_posterior_rows = _v2_posterior_rows(
            v2_report,
            q6_prior_gap=q6_practical_reference,
        )
        v3_posterior_shadow = _v3_posterior_shadow_summary(
            events,
            map_id=inference_session.map_id,
            hero=inference_session.hero,
            tables=tables,
            trials=resolved_shadow_trials,
            seed=seed + 6,
        )
        if roi_trials > 0:
            tool_rows = _tool_info_roi_rows(
                estimate_tool_info_roi(
                    candidate_map_ids,
                    inference_session,
                    maps=tables.maps,
                    drops=tables.drops,
                    items=tables.items,
                    n_trials=roi_trials,
                    seed=seed + 1,
                    cells_tol=cells_tol,
                    count_tol=count_tol,
                )
            )
        best_value_summary = v2_report.decision_value or (
            base_results[0].total_value
            if base_results and base_results[0].total_value is not None
            else None
        )
        if best_value_summary is not None:
            bid_rows = _build_bid_rows(
                latest_bids=latest_bids,
                value_summary=best_value_summary,
                evidence_label="v2 decision_value",
                session=inference_session,
                round_no=action_round,
                posterior_samples=v2_report.n_matched,
                warehouse_estimate=warehouse_estimate,
                decision_value_summary=v2_report.decision_value,
                raw_value_summary=v2_report.total_value,
                posterior_diagnostics=v2_report.diagnostics,
                q6_prior_gap=q6_practical_reference,
            )
        v2_bid_rows = [dict(row) for row in bid_rows]
        if formal_mode_requested == LIVE_FORMAL_MODE_V3_PRACTICAL:
            v3_practical_bid_rows, formal_mode_reason = _build_v3_practical_bid_rows(
                latest_bids=latest_bids,
                v3_shadow=v3_posterior_shadow,
                session=inference_session,
                round_no=action_round,
                posterior_samples=v2_report.n_matched,
                warehouse_estimate=warehouse_estimate,
                q6_prior_gap=q6_practical_reference,
            )
            if v3_practical_bid_rows:
                bid_rows = v3_practical_bid_rows
                formal_mode_applied = LIVE_FORMAL_MODE_V3_PRACTICAL
            else:
                formal_mode_applied = LIVE_FORMAL_MODE_V2
                formal_mode_reason = f"{formal_mode_reason}_fallback_v2"
        else:
            formal_mode_applied = LIVE_FORMAL_MODE_V2
            formal_mode_reason = "v2_mode_requested"
        if v2_report.n_matched <= 0:
            (
                fallback_map_rows,
                fallback_warehouse_rows,
                fallback_bid_rows,
            ) = _build_zero_match_fallback_rows(
                candidate_map_ids=candidate_map_ids,
                inference_session=inference_session,
                latest_bids=latest_bids,
                round_no=action_round,
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
                n_trials=n_trials,
                seed=seed + 4,
                cells_tol=cells_tol,
                count_tol=count_tol,
            )

    if bid_rows:
        for row in bid_rows:
            row.setdefault("formal_mode", formal_mode_applied)
            row.setdefault("formal_mode_reason", formal_mode_reason)
            row.setdefault("formal_baseline_source", formal_mode_applied)
            row.setdefault(
                "formal_override",
                "是" if formal_mode_applied == LIVE_FORMAL_MODE_V3_PRACTICAL else "否",
            )
    if v2_bid_rows:
        for row in v2_bid_rows:
            row.setdefault("formal_mode", LIVE_FORMAL_MODE_V2)
            row.setdefault("formal_mode_reason", "v2_reference")
            row.setdefault("formal_baseline_source", LIVE_FORMAL_MODE_V2)
            row.setdefault("formal_override", "否")

    panel = tactical_panel_from_rows(
        bid_rows=bid_rows,
        warehouse_rows=warehouse_rows,
        tool_rows=tool_rows,
        layout_stage_rows=layout_stage_rows,
        layout_note="",
    )
    inventory_count, inventory_cells = _inventory_totals(events)
    final_value = _inventory_value(events, tables.items)
    truth_breakdown = _inventory_quality_breakdown(
        events,
        tables.items,
        problem=problem,
        maps=tables.maps,
        drops=tables.drops,
        map_id=(
            problem.map_id
            if problem is not None
            else (
                model_map_id
                if model_map_id is not None
                else (base_session.map_id if base_session is not None else None)
            )
        ),
    )
    processing_seconds = round(time.perf_counter() - started_at, 4)
    structured_ref_inputs = _ahmad_ref_inputs_from_batches(
        batches,
        hero=base_session.hero if base_session is not None else None,
    )
    artifact: dict[str, Any] = {
        "schema_version": 1,
        "created_at": time.time(),
        "processing_seconds": processing_seconds,
        "n_trials": n_trials,
        "roi_trials": roi_trials,
        "shadow_trials": resolved_shadow_trials,
        "file": file,
        "packets": len(events.packets),
        "frames": len(events.frames),
        "states": len(events.states),
        "batches": len(batches),
        "session_id": _latest_session_id(events),
        "hero": base_session.hero if base_session is not None else None,
        "map_id": _latest_map_id(events),
        "model_map_id": model_map_id,
        "map_alias": activity_map_alias,
        "map_alias_mode": activity_map_alias.get("mode", ""),
        "round": action_round,
        "action_round": action_round,
        "observed_round": observed_round,
        "phase": phase,
        "inventory_count": inventory_count,
        "inventory_cells": inventory_cells,
        "known_value_sum": final_value,
        **truth_breakdown,
        "inference_input_constraints": inference_input_constraints,
        "formal_mode_requested": formal_mode_requested,
        "formal_mode": formal_mode_applied,
        "formal_mode_reason": formal_mode_reason,
        "formal_baseline_source": formal_mode_applied,
        "latest_bids": dict(latest_bids),
        "evidence_label": evidence_label,
        "map_rows": map_rows,
        "warehouse_rows": warehouse_rows,
        "v2_posterior_rows": v2_posterior_rows,
        "v2_bid_rows": v2_bid_rows,
        "v3_practical_bid_rows": v3_practical_bid_rows,
        "fallback_map_rows": fallback_map_rows,
        "fallback_warehouse_rows": fallback_warehouse_rows,
        "fallback_bid_rows": fallback_bid_rows,
        "v3_posterior_shadow": v3_posterior_shadow,
        "q6_residual_boost_shadow": q6_residual_boost_shadow,
        "q6_formal_prior_floor": q6_formal_prior_floor,
        "q6_residual_deep_floor_shadow": q6_residual_deep_floor_shadow,
        "q6_residual_deep11_floor_shadow": q6_residual_deep11_floor_shadow,
        "q6_residual_hidden_floor_shadow": q6_residual_hidden_floor_shadow,
        "q6_residual_villa_floor_shadow": q6_residual_villa_floor_shadow,
        "q6_residual_ethan_villa_random_floor_shadow": (
            q6_residual_ethan_villa_random_floor_shadow
        ),
        "q6_residual_ethan_shipwreck_layout_conditional_shadow": (
            q6_residual_ethan_shipwreck_layout_conditional_shadow
        ),
        "q6_residual_sampler_shadows": q6_residual_sampler_shadows,
        "q6_residual_boost_shadow_rows": q6_residual_boost_shadow_rows,
        "q6_aisha_bottom_row_risk": q6_aisha_bottom_row_risk,
        "q6_quality_only_local_risk": q6_quality_only_local_risk,
        "evidence_profile_key": evidence_profile_key,
        "tool_rows": tool_rows,
        "structured_ref_inputs": structured_ref_inputs,
        "ahmad_ref_inputs": structured_ref_inputs,
        "action_send_rows": _action_send_rows(events, tables.items),
        "action_result_rows": _action_result_rows(
            events,
            tables.items,
            session_id=_latest_session_id(events),
        ),
        "public_info_rows": _public_info_rows(events, tables.items),
        "bid_rows": bid_rows,
        "layout_replay_rows": layout_replay_rows,
        "layout_stage_rows": layout_stage_rows,
        "panel": asdict(panel),
        "category_grid_items": _category_grid_items(batches, tables.items),
        "minimap_grid_items": _minimap_grid_items(batches, tables.items),
        "layout_sample_rows": [
            row.as_dict()
            for row in evaluate_fatbeans_layout_events(events, file=file)
        ],
    }
    eval_row = _model_eval_row(
        file=file,
        artifact=artifact,
        final_value=final_value,
        final_cells=inventory_cells,
        truth_breakdown=truth_breakdown,
    )
    if eval_row is not None:
        artifact["model_eval"] = eval_row
    artifact["ui_contract"] = ui_contract_from_artifact(artifact)
    return artifact


def build_monitor_artifact_from_file(
    path: str | Path,
    *,
    tables: MonitorTables,
    n_trials: int = 500,
    roi_trials: int = 250,
    shadow_trials: int | None = None,
    run_debug_shadows: bool = True,
    seed: int = 20260530,
    formal_mode: str | None = None,
) -> dict[str, Any]:
    path = Path(path)
    return build_monitor_artifact_from_events(
        parse_fatbeans_capture(path),
        file=path.name,
        tables=tables,
        n_trials=n_trials,
        roi_trials=roi_trials,
        shadow_trials=shadow_trials,
        run_debug_shadows=run_debug_shadows,
        seed=seed,
        formal_mode=formal_mode,
    )


def build_monitor_artifact_from_payload(
    payload: str | bytes,
    *,
    file: str = "stdin",
    tables: MonitorTables,
    n_trials: int = 500,
    roi_trials: int = 250,
    shadow_trials: int | None = None,
    run_debug_shadows: bool = True,
    seed: int = 20260530,
    formal_mode: str | None = None,
    local_player_id_hint: int | None = None,
) -> dict[str, Any]:
    return build_monitor_artifact_from_events(
        parse_fatbeans_capture_payload(
            payload,
            local_player_id_hint=local_player_id_hint,
        ),
        file=file,
        tables=tables,
        n_trials=n_trials,
        roi_trials=roi_trials,
        shadow_trials=shadow_trials,
        run_debug_shadows=run_debug_shadows,
        seed=seed,
        formal_mode=formal_mode,
    )


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
        fh.write("\n")


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        tmp = Path(fh.name)
    try:
        for attempt in range(5):
            try:
                tmp.replace(path)
                return
            except PermissionError:
                if attempt >= 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if tmp.exists():
            tmp.unlink()


def write_monitor_logs(
    artifact: Mapping[str, Any],
    *,
    log_dir: str | Path | None = None,
    append_logs: bool = True,
) -> None:
    """Write latest snapshot and append long-running JSONL logs."""
    root = Path(log_dir) if log_dir is not None else project_root() / "data" / "logs" / "live"
    root.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(root / "latest_snapshot.json", artifact)
    if not append_logs:
        return
    _append_jsonl(root / "sessions.jsonl", artifact)
    eval_row = artifact.get("model_eval")
    if isinstance(eval_row, Mapping):
        _append_jsonl(root / "model_eval.jsonl", eval_row)
    for row in artifact.get("layout_sample_rows", ()) or ():
        if isinstance(row, Mapping):
            _append_jsonl(root / "layout_samples.jsonl", row)


__all__ = (
    "MonitorTables",
    "build_monitor_artifact_from_events",
    "build_monitor_artifact_from_file",
    "build_monitor_artifact_from_payload",
    "load_monitor_tables",
    "write_monitor_logs",
)
