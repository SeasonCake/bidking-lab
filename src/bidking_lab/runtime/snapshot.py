"""Compact tactical snapshots for UI frontends."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from bidking_lab.inference.size_avg_evidence import (
    format_size_bucket_target_label,
    parse_size_bucket_diagnostics,
    size_avg_readings_from_action_rows,
)

_MINIMAP_COLUMNS = 10
_MINIMAP_DEFAULT_CELLS = 130
_MINIMAP_MAX_CELLS = 250
_MINIMAP_DEFAULT_ROWS = _MINIMAP_DEFAULT_CELLS // _MINIMAP_COLUMNS
_MINIMAP_MAX_ROWS = _MINIMAP_MAX_CELLS // _MINIMAP_COLUMNS


@dataclass(frozen=True)
class LayoutStageSnapshot:
    """One compact layout-progress row for tactical UIs."""

    stage: str
    known_cells: str
    coverage: str
    deepest_row: str
    estimate: str
    confidence: str
    risk: str


@dataclass(frozen=True)
class TacticalSnapshot:
    """Small frontend-neutral summary for the current auction state."""

    price_decision: str
    value_range: str
    warehouse_range: str
    next_tool_hint: str
    highest_bid: str = ""
    risk_band: str = ""
    stop_price: str = ""
    evidence: str = ""
    warehouse_note: str = ""
    layout_stages: tuple[LayoutStageSnapshot, ...] = ()


@dataclass(frozen=True)
class TacticalSummaryRow:
    """One compact key/value row for small tactical panels."""

    topic: str
    conclusion: str
    detail: str = ""


@dataclass(frozen=True)
class TacticalPanelSnapshot:
    """Compact tactical panel shared by Streamlit and future overlays."""

    summary_rows: tuple[TacticalSummaryRow, ...]
    layout_stages: tuple[LayoutStageSnapshot, ...] = ()
    warehouse_rows: tuple[dict[str, str], ...] = ()
    tool_rows: tuple[dict[str, str], ...] = ()
    bid_rows: tuple[dict[str, str], ...] = ()
    layout_note: str = ""


@dataclass(frozen=True)
class ImportOverviewSnapshot:
    """Compact overview for one imported packet/live session."""

    file: str = ""
    packets: str = ""
    frames: str = ""
    states: str = ""
    live_batches: str = ""
    map_id: str = ""
    round_no: str = ""
    settlement_items: str = ""
    settlement_cells: str = ""
    known_loot_value: str = ""


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _first(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return rows[0] if rows else {}


def _first_mapping(rows: Any) -> Mapping[str, Any]:
    if isinstance(rows, Sequence) and not isinstance(rows, str | bytes) and rows:
        row = rows[0]
        if isinstance(row, Mapping):
            return row
    return {}


def _string_row(row: Mapping[str, Any]) -> dict[str, str]:
    return {str(key): _text(value) for key, value in row.items()}


def _string_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int | None = None,
) -> tuple[dict[str, str], ...]:
    selected = rows if limit is None else rows[:limit]
    return tuple(_string_row(row) for row in selected)


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _constraint_value(
    constraints: Mapping[str, Any],
    name: str,
) -> Any:
    row = constraints.get(name)
    if isinstance(row, Mapping):
        return row.get("value")
    return None


def _exact_quantile_range(value: Any) -> str:
    text = _text(value)
    return f"{text} / {text} / {text}" if text else ""


def _match_counts(value: Any) -> tuple[int | None, int | None]:
    text = _text(value).strip()
    if "/" not in text:
        return None, None
    left, right = text.split("/", 1)
    return _int_or_none(left.strip()), _int_or_none(right.strip())


def _posterior_status(
    matched: int | None,
    total: int | None,
) -> str:
    if matched == 0 and (total or 0) > 0:
        return "zero_match"
    if matched is not None and total is not None:
        return "matched"
    return "unknown"


def import_overview_from_summary(
    summary: Mapping[str, Any],
) -> ImportOverviewSnapshot:
    """Build a frontend-neutral import overview from a stored summary."""
    return ImportOverviewSnapshot(
        file=_text(summary.get("file")),
        packets=_text(summary.get("packets")),
        frames=_text(summary.get("frames")),
        states=_text(summary.get("states")),
        live_batches=_text(summary.get("batches")),
        map_id=_text(summary.get("map_id")),
        round_no=_text(summary.get("round")),
        settlement_items=_text(summary.get("inventory_count")),
        settlement_cells=_text(summary.get("inventory_cells")),
        known_loot_value=_text(summary.get("known_value_sum")),
    )


def packet_action_rows_from_sends(
    sends: Sequence[Any],
    item_names: Mapping[int, str],
) -> tuple[dict[str, str], ...]:
    """Build compact action rows from Fatbeans send events."""
    rows: list[dict[str, str]] = []
    for send in sends:
        if _field(send, "kind") != "action":
            continue
        action_id = _field(send, "value")
        if action_id is None:
            continue
        capture_time = _text(_field(send, "capture_time"))[-15:]
        rows.append(
            {
                "sort": _text(_field(send, "sort_id")),
                "时间": capture_time,
                "action_id": _text(action_id),
                "道具": _text(item_names.get(int(action_id), "")),
            }
        )
    return tuple(rows)


def action_result_rows_from_results(
    results: Sequence[Any],
    item_names: Mapping[int, str],
) -> tuple[dict[str, str], ...]:
    """Build compact action result rows from the latest packet state."""
    rows: list[dict[str, str]] = []
    for result in results:
        action_id = _field(result, "action_id")
        observed_items = _field(result, "observed_items", ()) or ()
        rows.append(
            {
                "action_id": _text(action_id),
                "道具": _text(
                    item_names.get(int(action_id), "")
                    if action_id is not None
                    else ""
                ),
                "结果": _text(_field(result, "result")),
                "揭示物品数": _text(len(observed_items)),
            }
        )
    return tuple(rows)


def player_bid_candidate_rows_from_bids(
    bids: Sequence[Any],
) -> tuple[dict[str, str], ...]:
    """Build diagnostic player bid rows from one packet state."""
    rows: list[dict[str, str]] = []
    for bid in bids:
        values = tuple(_field(bid, "values", ()) or ())
        if not values:
            continue
        rows.append(
            {
                "玩家": _text(_field(bid, "name")),
                "最大出价候选": _text(max(values)),
                "values": ",".join(str(value) for value in values),
            }
        )
    return tuple(rows)


def _estimate_range_label(estimate: Any) -> str:
    if _field(estimate, "locked"):
        return "锁定"
    p50 = _field(estimate, "p50_guess")
    p90 = _field(estimate, "p90_guess")
    return (
        f"{_text(_field(estimate, 'min_reasonable_cells'))}/"
        f"{_text(p50) if p50 is not None else '?'}/"
        f"{_text(p90) if p90 is not None else '?'}"
    )


def layout_replay_rows_from_stages(
    stages: Sequence[Any],
    *,
    comparison_policy: Any = None,
) -> tuple[dict[str, str], ...]:
    """Build frontend-neutral layout replay rows from live replay stages."""
    from bidking_lab.live.layout import (
        estimate_warehouse_from_layout,
        layout_risk_label,
    )

    rows: list[dict[str, str]] = []
    for stage in stages:
        layout = _field(stage, "layout")
        if layout is None:
            continue
        final_total_cells = _field(stage, "final_total_cells")
        estimate = estimate_warehouse_from_layout(
            layout,
            final_total_cells=final_total_cells,
        )
        comparison_estimate = (
            estimate_warehouse_from_layout(
                layout,
                final_total_cells=final_total_cells,
                policy=comparison_policy,
            )
            if comparison_policy is not None
            else None
        )
        known_cell_ratio = _field(stage, "known_cell_ratio")
        bounding_cell_error = _field(stage, "bounding_cell_error")
        row = {
            "sort": _text(_field(stage, "sort_id")),
            "R": _text(_field(stage, "round_no")),
            "phase": _text(_field(stage, "phase")),
            "已知件": _text(len(_field(layout, "items", ()))),
            "已知格": _text(_field(layout, "total_cells")),
            "最深行": _text(_field(layout, "max_row")),
            "边界格": _text(_field(layout, "bounding_cells")),
            "空洞率": f"{_field(layout, 'sparsity_ratio'):.0%}",
            "最终格": _text(final_total_cells),
            "已知覆盖": (
                f"{known_cell_ratio:.0%}"
                if known_cell_ratio is not None
                else ""
            ),
            "边界误差": _text(bounding_cell_error),
            "布局估计": _estimate_range_label(estimate),
            "估计置信": _text(_field(estimate, "confidence")),
            "风险": layout_risk_label(layout),
        }
        if comparison_estimate is not None:
            row["样本拟合估计"] = _estimate_range_label(comparison_estimate)
            row["样本拟合置信"] = _text(
                _field(comparison_estimate, "confidence")
            )
        rows.append(row)
    return tuple(rows)


def _layout_stage_from_row(row: Mapping[str, Any]) -> LayoutStageSnapshot:
    return LayoutStageSnapshot(
        stage=_text(row.get("阶段")),
        known_cells=_text(row.get("已知格")),
        coverage=_text(row.get("覆盖")),
        deepest_row=_text(row.get("最深行")),
        estimate=_text(row.get("布局估计")),
        confidence=_text(row.get("置信")),
        risk=_text(row.get("风险")),
    )


def _join_nonempty(parts: Sequence[str], *, sep: str = " / ") -> str:
    return sep.join(part for part in parts if part)


def tactical_snapshot_from_rows(
    *,
    bid_rows: Sequence[Mapping[str, Any]] = (),
    warehouse_rows: Sequence[Mapping[str, Any]] = (),
    tool_rows: Sequence[Mapping[str, Any]] = (),
    layout_stage_rows: Sequence[Mapping[str, Any]] = (),
) -> TacticalSnapshot:
    """Build a UI-neutral tactical snapshot from existing summary rows.

    This is intentionally a thin adapter: it does not run inference and does
    not know about Streamlit. Future overlays can consume this same object.
    """
    bid = _first(bid_rows)
    warehouse = _first(warehouse_rows)
    tool = _first(tool_rows)
    tool_name = _text(tool.get("道具"))
    tool_hint = ""
    if tool_name:
        tool_hint = (
            f"{tool_name}，ROI {_text(tool.get('信息ROI'))}；"
            f"价值压缩 {_text(tool.get('价值压缩') or tool.get('价值区间压缩'))}，"
            f"仓储压缩 {_text(tool.get('仓储压缩') or tool.get('仓储区间压缩'))}"
        )
    else:
        tool_hint = _text(bid.get("补信息") or "暂无建议")

    return TacticalSnapshot(
        price_decision=_text(bid.get("建议") or "暂无出价后验"),
        value_range=_text(
            bid.get("决策价值 P10/P50/P90")
            or warehouse.get("价值 P10/P50/P90")
            or "暂无后验"
        ),
        warehouse_range=_text(
            warehouse.get("总格 P10/P50/P90")
            or bid.get("仓储")
            or "暂无后验"
        ),
        next_tool_hint=tool_hint,
        highest_bid=_text(bid.get("当前最高")),
        risk_band=_text(bid.get("风险带")),
        stop_price=_text(bid.get("停止价")),
        evidence=_join_nonempty(
            (
                _text(bid.get("证据") or warehouse.get("匹配")),
                (
                    f"raw {_text(bid.get('原始价值 P10/P50/P90'))}"
                    if bid.get("原始价值 P10/P50/P90")
                    else ""
                ),
                (
                    f"上界 {_text(bid.get('上界风险'))}"
                    if bid.get("上界风险")
                    else ""
                ),
                _text(bid.get("后验诊断")),
            ),
            sep="；",
        ),
        warehouse_note=_join_nonempty(
            (
                _text(warehouse.get("置信度")),
                _text(warehouse.get("说明")),
            ),
            sep="；",
        ),
        layout_stages=tuple(
            _layout_stage_from_row(row) for row in layout_stage_rows
        ),
    )


def tactical_summary_rows(
    snapshot: TacticalSnapshot,
) -> tuple[TacticalSummaryRow, ...]:
    """Return the four-row summary shared by Streamlit and future overlays."""
    return (
        TacticalSummaryRow(
            topic="当前最高价是否可追",
            conclusion=snapshot.price_decision,
            detail=_join_nonempty(
                (
                    snapshot.highest_bid,
                    snapshot.risk_band,
                    f"停止价 {snapshot.stop_price}" if snapshot.stop_price else "",
                )
            ),
        ),
        TacticalSummaryRow(
            topic="当前价值区间",
            conclusion=snapshot.value_range,
            detail=snapshot.evidence,
        ),
        TacticalSummaryRow(
            topic="当前仓储区间",
            conclusion=snapshot.warehouse_range,
            detail=snapshot.warehouse_note,
        ),
        TacticalSummaryRow(
            topic="下一次优先使用道具",
            conclusion=snapshot.next_tool_hint,
        ),
    )


def tactical_panel_from_rows(
    *,
    bid_rows: Sequence[Mapping[str, Any]] = (),
    warehouse_rows: Sequence[Mapping[str, Any]] = (),
    tool_rows: Sequence[Mapping[str, Any]] = (),
    layout_stage_rows: Sequence[Mapping[str, Any]] = (),
    layout_note: Any = "",
) -> TacticalPanelSnapshot:
    """Build the compact tactical panel without depending on Streamlit."""
    snapshot = tactical_snapshot_from_rows(
        bid_rows=bid_rows,
        warehouse_rows=warehouse_rows,
        tool_rows=tool_rows,
        layout_stage_rows=layout_stage_rows,
    )
    return TacticalPanelSnapshot(
        summary_rows=tactical_summary_rows(snapshot),
        layout_stages=snapshot.layout_stages,
        warehouse_rows=_string_rows(warehouse_rows),
        tool_rows=_string_rows(tool_rows),
        bid_rows=_string_rows(bid_rows, limit=1),
        layout_note=_text(layout_note),
    )


def ui_contract_from_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Build the stable UI contract from a live monitor artifact.

    The full monitor artifact intentionally keeps diagnostics, raw rows, and
    experimental shadow outputs. UI frontends should prefer this smaller
    contract for first-screen rendering and treat shadows as read-only risk
    references, not as formal bid inputs.
    """
    bid = _first_mapping(artifact.get("bid_rows"))
    v2_bid = _first_mapping(artifact.get("v2_bid_rows")) or (
        bid if _text(artifact.get("formal_mode")) == "v2" else {}
    )
    v2 = _first_mapping(artifact.get("v2_posterior_rows"))
    warehouse = _first_mapping(artifact.get("warehouse_rows"))
    panel = artifact.get("panel") if isinstance(artifact.get("panel"), Mapping) else {}
    layout = _first_mapping(panel.get("layout_stages") if panel else ())
    model_eval = (
        artifact.get("model_eval")
        if isinstance(artifact.get("model_eval"), Mapping)
        else {}
    )
    input_constraints = (
        artifact.get("inference_input_constraints")
        if isinstance(artifact.get("inference_input_constraints"), Mapping)
        else {}
    )
    minimap = _ui_minimap_contract(artifact)
    shadows = [
        _ui_shadow_contract(shadow, model_eval)
        for shadow in artifact.get("q6_residual_sampler_shadows", ()) or ()
        if isinstance(shadow, Mapping)
    ]
    q6_risk = {
        "risk": bool(v2.get("q6先验风险")),
        "prior_gap": _text(v2.get("q6先验缺口")),
        "prior_reference_p90": _text(v2.get("q6先验风险参考")),
        "practical_gate": _text(v2.get("q6实战门控")),
        "practical_reference_p90": _text(v2.get("q6实战参考P90")),
        "display_mode": "risk_reference",
        "affects_bid": False,
        "bid_floor_applied": False,
        "minimum_bid_floor": "",
        "note": (
            "q6 risk is displayed as a reference only; formal bid thresholds "
            "are recomputed from the current formal_mode."
        ),
    }
    posterior_matched, posterior_total = _match_counts(v2.get("匹配"))
    exact_total_cells = _constraint_value(
        input_constraints,
        "warehouse_total_cells",
    )
    exact_total_items = _constraint_value(input_constraints, "total_item_count")
    formal_mode = _text(artifact.get("formal_mode") or "v2")
    contract_mode = (
        "v3_practical_formal_with_v2_reference"
        if formal_mode == "v3_practical"
        else "baseline_first_shadow_reference"
    )
    return {
        "schema_version": 1,
        "mode": contract_mode,
        "source": {
            "file": _text(artifact.get("file")),
            "created_at": artifact.get("created_at"),
            "processing_seconds": artifact.get("processing_seconds"),
            "snapshot_mode": _text(artifact.get("snapshot_mode")),
            "n_trials": artifact.get("n_trials"),
            "roi_trials": artifact.get("roi_trials"),
            "shadow_trials": artifact.get("shadow_trials"),
            "formal_mode_requested": _text(
                artifact.get("formal_mode_requested") or formal_mode
            ),
            "formal_mode": formal_mode,
            "formal_mode_reason": _text(artifact.get("formal_mode_reason")),
            "formal_baseline_source": _text(
                artifact.get("formal_baseline_source") or formal_mode
            ),
            "inference_profile": (
                artifact.get("inference_profile")
                if isinstance(artifact.get("inference_profile"), Mapping)
                else {}
            ),
        },
        "actions": _ui_actions_contract(artifact),
        "context": {
            "session_id": artifact.get("session_id"),
            "hero": artifact.get("hero"),
            "map_id": artifact.get("map_id"),
            "round": artifact.get("round"),
            "action_round": artifact.get("action_round", artifact.get("round")),
            "observed_round": artifact.get("observed_round"),
            "phase": artifact.get("phase"),
            "known_value_sum": artifact.get("known_value_sum"),
            "inventory_count": artifact.get("inventory_count"),
            "inventory_cells": artifact.get("inventory_cells"),
        },
        "baseline": {
            "official": True,
            "affects_bid": True,
            "source": formal_mode,
            "mode_reason": _text(artifact.get("formal_mode_reason")),
            "decision": {
                "action": _text(bid.get("建议")),
                "current_highest": _text(bid.get("当前最高")),
                "risk_band": _text(bid.get("风险带")),
                "warehouse_multiplier": _text(bid.get("秒仓倍率")),
                "probe_bid": _text(bid.get("探价(P10)")),
                "defend_bid": _text(bid.get("防守价")),
                "attack_bid": _text(bid.get("可追价(P90)") or bid.get("抢仓上限")),
                "stop_price": _text(bid.get("停止价")),
                "evidence": _text(bid.get("证据")),
                "round": _text(bid.get("轮次")),
                "information_density": _text(bid.get("信息强度")),
                "q6_risk_reference": _text(bid.get("红货风险参考")),
            },
            "posterior": {
                "value_basis": _text(
                    bid.get("价值口径") or v2.get("价值口径") or "decision_value"
                ),
                "match_text": _text(v2.get("匹配")),
                "matched": posterior_matched,
                "total": posterior_total,
                "status": _posterior_status(posterior_matched, posterior_total),
                "total_value_range": _text(warehouse.get("价值 P10/P50/P90")),
                "total_cells_range": (
                    _text(warehouse.get("总格 P10/P50/P90"))
                    or _exact_quantile_range(exact_total_cells)
                ),
                "total_item_count_range": _exact_quantile_range(exact_total_items),
                "total_item_count_status": (
                    "exact_input_constraint"
                    if exact_total_items is not None
                    else "not_estimated_by_v2"
                ),
                "input_total_item_count": exact_total_items,
                "input_warehouse_total_cells": exact_total_cells,
                "input_warehouse_total_cells_approx": _constraint_value(
                    input_constraints,
                    "warehouse_total_cells_approx",
                ),
                "decision_value_range": _text(
                    bid.get("决策价值 P10/P50/P90")
                    or v2.get("决策价值 P10/P50/P90")
                ),
                "raw_value_range": _text(
                    bid.get("原始价值 P10/P50/P90")
                    or v2.get("原始价值 P10/P50/P90")
                ),
                "q6_sample_rate": _text(v2.get("q6样本率")),
                "q6_prior_rate": _text(v2.get("q6掉落先验")),
                "q6_prior_expected_count": _text(v2.get("q6先验件数")),
                "q6_prior_expected_cells": _text(v2.get("q6先验格数")),
                "q6_prior_expected_value": _text(v2.get("q6先验价值")),
                "q6_decision_value_range": _text(v2.get("q6决策价值 P10/P50/P90")),
                "q6_count_range": _text(v2.get("q6件数 P10/P50/P90")),
                "q6_cells_range": _text(v2.get("q6格数 P10/P50/P90")),
                "remaining_cells_after_layout_range": _text(
                    v2.get("剩余空间 P10/P50/P90")
                ),
                "q6_space_pressure_range": _text(v2.get("q6空间压力 P10/P50/P90")),
                "q6_space_overflow_rate": _text(v2.get("q6空间溢出率")),
                "diagnostics": _text(v2.get("诊断")),
            },
            "layout": {
                "stage": _text(layout.get("stage")),
                "known_cells": _text(layout.get("known_cells")),
                "estimate": _text(layout.get("estimate")),
                "confidence": _text(layout.get("confidence")),
                "risk": _text(layout.get("risk")),
            },
        },
        "v2_reference": {
            "available": bool(v2_bid),
            "affects_bid": formal_mode == "v2",
            "decision": {
                "action": _text(v2_bid.get("建议")),
                "current_highest": _text(v2_bid.get("当前最高")),
                "risk_band": _text(v2_bid.get("风险带")),
                "warehouse_multiplier": _text(v2_bid.get("秒仓倍率")),
                "probe_bid": _text(v2_bid.get("探价(P10)")),
                "defend_bid": _text(v2_bid.get("防守价")),
                "attack_bid": _text(v2_bid.get("可追价(P90)") or v2_bid.get("抢仓上限")),
                "stop_price": _text(v2_bid.get("停止价")),
                "evidence": _text(v2_bid.get("证据")),
                "round": _text(v2_bid.get("轮次")),
                "information_density": _text(v2_bid.get("信息强度")),
            },
        },
        "q6_risk_reference": q6_risk,
        "shadows": shadows,
        "fallback": _ui_fallback_contract(artifact),
        "minimap": minimap,
        "truth": _ui_truth_contract(artifact, model_eval),
        "constraints": _ui_constraints_contract(
            v2,
            model_eval,
            minimap,
            input_constraints,
        ),
        "diagnostics": _ui_diagnostics_contract(v2, model_eval, artifact),
        "interaction": {
            "compact": {
                "purpose": "always_on_top_core_tips",
                "fields": (
                    "baseline.decision.action",
                    "baseline.decision.current_highest",
                    "baseline.decision.risk_band",
                    "baseline.decision.defend_bid",
                    "baseline.decision.stop_price",
                    "baseline.posterior.decision_value_range",
                    "baseline.posterior.total_cells_range",
                    "actions.latest_result",
                    "q6_risk_reference.risk",
                    "fallback.active",
                ),
            },
            "hover": {
                "purpose": "expanded_quick_context",
                "fields": (
                    "baseline.decision",
                    "baseline.posterior",
                    "baseline.layout",
                    "fallback",
                    "q6_risk_reference",
                    "constraints.summary",
                    "diagnostics.v3_practical",
                    "actions",
                    "diagnostics.size_bucket",
                    "minimap",
                ),
            },
            "detail": {
                "purpose": "click_to_open_full_reasoning",
                "fields": (
                    "truth",
                    "baseline.posterior",
                    "baseline.layout",
                    "constraints",
                    "actions",
                    "q6_risk_reference",
                    "fallback",
                    "shadows",
                    "minimap.items",
                    "diagnostics",
                    "model_eval",
                ),
                "collapsible": True,
                "renderers": (),
            },
        },
    }


def _ui_actions_contract(artifact: Mapping[str, Any]) -> dict[str, Any]:
    sent = _string_rows(artifact.get("action_send_rows", ()) or (), limit=8)
    results = _string_rows(
        [
            {
                key: value
                for key, value in row.items()
                if key != "revealed_items_detail"
            }
            for row in artifact.get("action_result_rows", ()) or ()
            if isinstance(row, Mapping)
        ],
        limit=8,
    )
    return {
        "sent": sent,
        "results": results,
        "latest_sent": sent[0] if sent else {},
        "latest_result": results[0] if results else {},
    }


def _ui_truth_contract(
    artifact: Mapping[str, Any],
    model_eval: Mapping[str, Any],
) -> dict[str, Any]:
    total_items = _first_non_empty(
        artifact.get("inventory_count"),
    )
    total_cells = _first_non_empty(
        model_eval.get("final_cells"),
        artifact.get("inventory_cells"),
    )
    total_value = _first_non_empty(
        model_eval.get("final_value"),
        artifact.get("known_value_sum"),
    )
    available = any(
        value is not None
        for value in (total_items, total_cells, total_value)
    )
    return {
        "available": available,
        "source": (
            "settlement_or_sample_replay"
            if available
            else "not_available_live_pre_settlement"
        ),
        "total_value": total_value,
        "total_items": total_items,
        "total_cells": total_cells,
        "q5": {
            "count": _first_non_empty(
                model_eval.get("final_q5_count"),
                artifact.get("final_q5_count"),
            ),
            "cells": _first_non_empty(
                model_eval.get("final_q5_cells"),
                artifact.get("final_q5_cells"),
            ),
            "value": _first_non_empty(
                model_eval.get("final_q5_value"),
                artifact.get("final_q5_value"),
            ),
        },
        "q6": {
            "count": _first_non_empty(
                model_eval.get("final_q6_count"),
                artifact.get("final_q6_count"),
            ),
            "cells": _first_non_empty(
                model_eval.get("final_q6_cells"),
                artifact.get("final_q6_cells"),
            ),
            "value": _first_non_empty(
                model_eval.get("final_q6_value"),
                artifact.get("final_q6_value"),
            ),
            "decision_value": _first_non_empty(
                model_eval.get("final_q6_decision_value"),
                artifact.get("final_q6_decision_value"),
            ),
            "trimmed_tail_value": _first_non_empty(
                model_eval.get("final_q6_trimmed_tail_value"),
                artifact.get("final_q6_trimmed_tail_value"),
            ),
            "tail_replacement_value": _first_non_empty(
                model_eval.get("final_q6_tail_replacement_value"),
                artifact.get("final_q6_tail_replacement_value"),
            ),
            "decision_value_with_tail_replacement": _first_non_empty(
                model_eval.get(
                    "final_q6_decision_value_with_tail_replacement"
                ),
                artifact.get("final_q6_decision_value_with_tail_replacement"),
            ),
        },
        "top_item": {
            "id": _first_non_empty(
                model_eval.get("final_top_item_id"),
                artifact.get("final_top_item_id"),
            ),
            "name": _text(
                _first_non_empty(
                    model_eval.get("final_top_item_name"),
                    artifact.get("final_top_item_name"),
                )
            ),
            "quality": _first_non_empty(
                model_eval.get("final_top_item_quality"),
                artifact.get("final_top_item_quality"),
            ),
            "value": _first_non_empty(
                model_eval.get("final_top_item_value"),
                artifact.get("final_top_item_value"),
            ),
            "cells": _first_non_empty(
                model_eval.get("final_top_item_cells"),
                artifact.get("final_top_item_cells"),
            ),
        },
    }


def _ui_constraints_contract(
    v2: Mapping[str, Any],
    model_eval: Mapping[str, Any],
    minimap: Mapping[str, Any],
    input_constraints: Mapping[str, Any],
) -> dict[str, Any]:
    quality_counts = (
        minimap.get("quality_counts")
        if isinstance(minimap.get("quality_counts"), Mapping)
        else {}
    )
    anchor_count = _first_non_empty(
        model_eval.get("anchor_count"),
        v2.get("锚点数"),
    )
    shape_target_count = _first_non_empty(
        model_eval.get("shape_target_count"),
        v2.get("形状约束数"),
    )
    category_target_count = _first_non_empty(
        model_eval.get("category_target_count"),
        v2.get("分类约束数"),
    )
    category_exclusion_count = _first_non_empty(
        model_eval.get("category_exclusion_count"),
        v2.get("分类反排数"),
    )
    public_constraint_key = _text(model_eval.get("public_constraint_key"))
    evidence_profile_key = _text(model_eval.get("evidence_profile_key"))
    random_sample_avg_values = _text(
        _first_non_empty(
            model_eval.get("random_sample_avg_values"),
            v2.get("随机样本均价"),
        )
    )
    random_sample_avg_signal_values = _text(
        _first_non_empty(
            model_eval.get("random_sample_avg_signal_values"),
            v2.get("随机样本均价信号"),
        )
    )
    summary = {
        "anchor_count": anchor_count,
        "shape_target_count": shape_target_count,
        "category_target_count": category_target_count,
        "category_exclusion_count": category_exclusion_count,
        "input_total_item_count": _constraint_value(
            input_constraints,
            "total_item_count",
        ),
        "input_warehouse_total_cells": _constraint_value(
            input_constraints,
            "warehouse_total_cells",
        ),
        "input_warehouse_total_cells_approx": _constraint_value(
            input_constraints,
            "warehouse_total_cells_approx",
        ),
        "known_grid_items": minimap.get("known_items"),
        "known_purple_item_count": quality_counts.get("q4", 0),
        "known_gold_item_count": quality_counts.get("q5", 0),
        "known_red_item_count": quality_counts.get("q6", 0),
        "public_constraint_key": public_constraint_key,
        "evidence_profile_key": evidence_profile_key,
        "information_density_band": _text(
            model_eval.get("information_density_band")
        ),
    }
    return {
        "summary": summary,
        "counts": {
            "anchor_count": anchor_count,
            "shape_target_count": shape_target_count,
            "category_target_count": category_target_count,
            "category_exclusion_count": category_exclusion_count,
            "known_quality_counts": dict(quality_counts),
            "input_total_item_count": _constraint_value(
                input_constraints,
                "total_item_count",
            ),
            "input_warehouse_total_cells": _constraint_value(
                input_constraints,
                "warehouse_total_cells",
            ),
        },
        "public_info": {
            "input_constraints_mode": _text(input_constraints.get("mode")),
            "input_constraints": input_constraints,
            "public_constraint_key": public_constraint_key,
            "evidence_profile_key": evidence_profile_key,
            "evidence_stage": _text(model_eval.get("evidence_stage")),
            "information_density_score": model_eval.get(
                "information_density_score"
            ),
            "information_density_band": _text(
                model_eval.get("information_density_band")
            ),
            "random_sample_avg_values": random_sample_avg_values,
            "random_sample_avg_signal_values": random_sample_avg_signal_values,
        },
        "exclusions": {
            "category_exclusion_count": category_exclusion_count,
            "note": (
                "specific_category_ids_are_in_posterior_diagnostics"
                if (_int_or_none(category_exclusion_count) or 0) > 0
                else ""
            ),
        },
    }


def _ui_size_bucket_contract(
    artifact: Mapping[str, Any],
    posterior: str,
) -> dict[str, Any]:
    targets = parse_size_bucket_diagnostics(posterior)
    readings = size_avg_readings_from_action_rows(
        artifact.get("action_result_rows")
    )
    target_labels = [
        format_size_bucket_target_label(target) for target in targets
    ]
    reading_labels = [
        f"{row.get('tool') or row.get('action_id')}: {row.get('avg_label')}"
        for row in readings
    ]
    latest_reading = readings[0] if readings else None
    latest_target = targets[0] if targets else None
    return {
        "active": bool(targets),
        "reading_active": bool(readings),
        "targets": targets,
        "target_labels": target_labels,
        "readings": readings,
        "reading_labels": reading_labels,
        "latest_reading": latest_reading,
        "latest_target": latest_target,
        "latest_reading_label": reading_labels[0] if reading_labels else "",
        "latest_target_label": target_labels[0] if target_labels else "",
        "inference_matches_reading": (
            latest_target is not None
            and latest_reading is not None
            and int(latest_target.get("cells") or 0)
            == int(latest_reading.get("footprint_cells") or 0)
            and abs(
                float(latest_target.get("avg_value") or 0)
                - float(latest_reading.get("avg_value") or 0)
            )
            < 1.0
        ),
    }


def _ui_diagnostics_contract(
    v2: Mapping[str, Any],
    model_eval: Mapping[str, Any],
    artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    posterior = _text(
        _first_non_empty(
            model_eval.get("posterior_diagnostics"),
            v2.get("诊断"),
        )
    )
    return {
        "posterior": posterior,
        "size_bucket": _ui_size_bucket_contract(artifact or {}, posterior),
        "layout": {
            "conflict": bool(model_eval.get("layout_conflict")),
            "conflict_root": _text(model_eval.get("layout_conflict_root")),
            "bottom_row": model_eval.get("layout_bottom_row"),
            "bottom_row_risk": bool(model_eval.get("q6_aisha_bottom_row_risk")),
            "bottom_row_risk_threshold": model_eval.get(
                "layout_bottom_row_risk_threshold"
            ),
        },
        "q6": {
            "no_plannable_control": model_eval.get("q6_no_plannable_control"),
            "zero_q6_proven_control": model_eval.get(
                "q6_zero_q6_proven_control"
            ),
            "p90_misses_truth": model_eval.get("q6_p90_misses_truth"),
            "plannable_p90_misses_truth": model_eval.get(
                "q6_plannable_p90_misses_truth"
            ),
            "tail_replacement_p90_misses_truth": model_eval.get(
                "q6_tail_replacement_p90_misses_truth"
            ),
            "tail_replacement_p90_under_by": model_eval.get(
                "v2_q6_tail_replacement_decision_value_p90_under_by"
            ),
            "tail_replacement_estimate_p90": model_eval.get(
                "v2_q6_tail_replacement_estimate_p90"
            ),
            "tail_replacement_estimate_p90_misses_truth": model_eval.get(
                "q6_tail_replacement_estimate_p90_misses_truth"
            ),
            "tail_replacement_estimate_p90_under_by": model_eval.get(
                "v2_q6_tail_replacement_estimate_p90_under_by"
            ),
            "tail_replacement_count": model_eval.get(
                "final_q6_tail_replacement_count"
            ),
            "tail_replacement_items": _text(
                model_eval.get("final_q6_tail_replacement_items")
            ),
            "tail_replacement_source": _text(
                model_eval.get("final_q6_tail_replacement_source")
            ),
            "false_low_risk": model_eval.get("q6_false_low_risk"),
            "below_drop_prior": bool(model_eval.get("q6_below_drop_prior")),
            "top_size_band": _text(model_eval.get("q6_top_size_band")),
            "quality_only_local_count": model_eval.get(
                "q6_quality_only_local_count"
            ),
            "quality_only_deepest_local_index": model_eval.get(
                "q6_quality_only_deepest_local_index"
            ),
            "quality_only_deepest_start_row": model_eval.get(
                "q6_quality_only_deepest_start_row"
            ),
            "quality_only_deep_local_risk": bool(
                model_eval.get("q6_quality_only_deep_local_risk")
            ),
            "quality_only_deep_row_threshold": model_eval.get(
                "q6_quality_only_deep_row_threshold"
            ),
        },
        "v3_practical": {
            "available": bool(model_eval.get("v3_practical_available")),
            "ready": bool(model_eval.get("v3_practical_ready")),
            "affects_bid": bool(model_eval.get("v3_practical_affects_bid")),
            "active": bool(model_eval.get("v3_practical_active")),
            "candidate": bool(model_eval.get("v3_practical_candidate")),
            "source": _text(model_eval.get("v3_practical_source")),
            "mode": _text(model_eval.get("v3_practical_mode")),
            "status": _text(model_eval.get("v3_practical_status")),
            "recommendation": _text(
                model_eval.get("v3_practical_recommendation")
            ),
            "confidence": _text(model_eval.get("v3_practical_confidence")),
            "source_lanes": _text(model_eval.get("v3_practical_source_lanes")),
            "risk_flags": _text(model_eval.get("v3_practical_risk_flags")),
            "reason": _text(model_eval.get("v3_practical_reason")),
            "formal_decision_value_p50": model_eval.get(
                "v3_practical_formal_decision_value_p50"
            ),
            "formal_decision_value_p90": model_eval.get(
                "v3_practical_formal_decision_value_p90"
            ),
            "baseline_formal_decision_value_p50": model_eval.get(
                "v3_practical_baseline_formal_decision_value_p50"
            ),
            "baseline_formal_decision_value_p90": model_eval.get(
                "v3_practical_baseline_formal_decision_value_p90"
            ),
            "delta_formal_decision_value_p50": model_eval.get(
                "v3_practical_delta_formal_decision_value_p50"
            ),
            "delta_formal_decision_value_p90": model_eval.get(
                "v3_practical_delta_formal_decision_value_p90"
            ),
            "total_value_p90": model_eval.get(
                "v3_practical_total_value_p90"
            ),
            "baseline_total_value_p90": model_eval.get(
                "v3_practical_baseline_total_value_p90"
            ),
            "delta_total_value_p90": model_eval.get(
                "v3_practical_delta_total_value_p90"
            ),
            "raw_total_gap_to_formal_p90": model_eval.get(
                "v3_practical_raw_total_gap_to_formal_p90"
            ),
            "baseline_raw_total_gap_to_formal_p90": model_eval.get(
                "v3_practical_baseline_raw_total_gap_to_formal_p90"
            ),
            "q6_formal_decision_value_p50": model_eval.get(
                "v3_practical_q6_formal_decision_value_p50"
            ),
            "q6_formal_decision_value_p90": model_eval.get(
                "v3_practical_q6_formal_decision_value_p90"
            ),
            "baseline_q6_formal_decision_value_p50": model_eval.get(
                "v3_practical_baseline_q6_formal_decision_value_p50"
            ),
            "baseline_q6_formal_decision_value_p90": model_eval.get(
                "v3_practical_baseline_q6_formal_decision_value_p90"
            ),
            "delta_q6_formal_decision_value_p50": model_eval.get(
                "v3_practical_delta_q6_formal_decision_value_p50"
            ),
            "delta_q6_formal_decision_value_p90": model_eval.get(
                "v3_practical_delta_q6_formal_decision_value_p90"
            ),
            "q6_value_p90": model_eval.get("v3_practical_q6_value_p90"),
            "baseline_q6_value_p90": model_eval.get(
                "v3_practical_baseline_q6_value_p90"
            ),
            "delta_q6_value_p90": model_eval.get(
                "v3_practical_delta_q6_value_p90"
            ),
            "q6_raw_gap_to_formal_p90": model_eval.get(
                "v3_practical_q6_raw_gap_to_formal_p90"
            ),
            "baseline_q6_raw_gap_to_formal_p90": model_eval.get(
                "v3_practical_baseline_q6_raw_gap_to_formal_p90"
            ),
        },
        "sampling": {
            "relaxed_exact_used": bool(model_eval.get("relaxed_exact_used")),
            "processing_seconds": model_eval.get(
                "monitor_processing_seconds"
            ),
            "n_trials": model_eval.get("monitor_n_trials"),
            "roi_trials": model_eval.get("monitor_roi_trials"),
            "shadow_trials": model_eval.get("monitor_shadow_trials"),
        },
    }


def _ui_minimap_quality_markers(
    artifact: Mapping[str, Any],
    *,
    known_runtime_ids: set[int],
    known_local_indexes: set[int],
) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    seen: set[tuple[int | None, int, int]] = set()
    row_sources = (
        ("packet", artifact.get("action_result_rows", ()) or ()),
        ("public_info", artifact.get("public_info_rows", ()) or ()),
    )
    for source, rows in row_sources:
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            details = row.get("revealed_items_detail")
            if not isinstance(details, Sequence) or isinstance(details, (str, bytes)):
                continue
            source_label = _text(row.get("tool"))
            if not source_label and source == "public_info":
                info_id = _int_or_none(row.get("info_id"))
                source_label = f"公共信息 {info_id}" if info_id is not None else "公共信息"
            for item in details:
                if not isinstance(item, Mapping):
                    continue
                quality = _int_or_none(item.get("quality"))
                item_id = _int_or_none(item.get("item_id"))
                local_index = _int_or_none(item.get("local_index"))
                runtime_id = _int_or_none(item.get("runtime_id"))
                if quality is None or item_id is not None or local_index is None:
                    continue
                if runtime_id is not None and runtime_id in known_runtime_ids:
                    continue
                if local_index in known_local_indexes:
                    continue
                marker_key = (runtime_id, local_index, quality)
                if marker_key in seen:
                    continue
                seen.add(marker_key)
                row_no = local_index // _MINIMAP_COLUMNS + 1
                col_no = local_index % _MINIMAP_COLUMNS + 1
                markers.append(
                    {
                        "row": row_no,
                        "col": col_no,
                        "width": 1,
                        "height": 1,
                        "quality": quality,
                        "category": None,
                        "category_label": "",
                        "item_id": None,
                        "item_name": "",
                        "display_label": f"Q{quality}",
                        "tooltip": _join_nonempty(
                            [source_label, f"Q{quality}", f"local {local_index}"],
                            sep=" / ",
                        ),
                        "shape_key": "",
                        "cells": 1,
                        "local_index": local_index,
                        "source": source,
                        "render_mode": "marker",
                    }
                )
                known_local_indexes.add(local_index)
                if runtime_id is not None:
                    known_runtime_ids.add(runtime_id)
    return markers


def _ui_minimap_quality_reveal_summary(
    artifact: Mapping[str, Any],
    *,
    known_runtime_ids: set[int],
    known_local_indexes: set[int],
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    unplaced_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    covered_count = 0
    placeable_count = 0
    row_sources = (
        ("packet", artifact.get("action_result_rows", ()) or ()),
        ("public_info", artifact.get("public_info_rows", ()) or ()),
    )
    for source, rows in row_sources:
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            details = row.get("revealed_items_detail")
            if not isinstance(details, Sequence) or isinstance(details, (str, bytes)):
                continue
            source_label = _text(row.get("tool"))
            if not source_label and source == "public_info":
                info_id = _int_or_none(row.get("info_id"))
                source_label = (
                    f"公共信息 {info_id}" if info_id is not None else "公共信息"
                )
            source_label = source_label or source
            for item in details:
                if not isinstance(item, Mapping):
                    continue
                quality = _int_or_none(item.get("quality"))
                item_id = _int_or_none(item.get("item_id"))
                if quality is None or item_id is not None:
                    continue
                local_index = _int_or_none(item.get("local_index"))
                runtime_id = _int_or_none(item.get("runtime_id"))
                label = f"q{quality}"
                counts[label] += 1
                source_counts[source_label] += 1
                known_runtime = (
                    runtime_id is not None and runtime_id in known_runtime_ids
                )
                known_local = local_index is not None and local_index in known_local_indexes
                if known_runtime or known_local:
                    covered_count += 1
                elif local_index is None:
                    unplaced_counts[label] += 1
                else:
                    placeable_count += 1
    total = sum(counts.values())
    if not total:
        return {}
    return {
        "quality_reveal_count": total,
        "quality_reveal_counts": dict(sorted(counts.items())),
        "quality_reveal_unplaced_count": sum(unplaced_counts.values()),
        "quality_reveal_unplaced_counts": dict(sorted(unplaced_counts.items())),
        "quality_reveal_covered_count": covered_count,
        "quality_reveal_placeable_count": placeable_count,
        "quality_reveal_sources": dict(sorted(source_counts.items())),
    }


def _ui_minimap_contract(artifact: Mapping[str, Any]) -> dict[str, Any]:
    raw_items = [
        item
        for item in (
            artifact.get("minimap_grid_items")
            or artifact.get("category_grid_items")
            or ()
        )
        if isinstance(item, Mapping)
    ]
    items: list[dict[str, Any]] = []
    quality_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    known_runtime_ids: set[int] = set()
    known_local_indexes: set[int] = set()
    layout_source_counts: Counter[str] = Counter()
    drawable_items = 0
    settlement_items = 0
    settlement_drawable_items = 0
    max_row = 0
    for item in raw_items:
        row = _int_or_none(item.get("row"))
        col = _int_or_none(item.get("col"))
        width = _int_or_none(item.get("width")) or 1
        height = _int_or_none(item.get("height")) or 1
        if row is not None:
            max_row = max(max_row, row + height - 1)
        quality = item.get("quality")
        runtime_id = _int_or_none(item.get("runtime_id"))
        local_index = _int_or_none(item.get("local_index"))
        category_label = _text(item.get("category_label") or item.get("category"))
        item_name = _text(item.get("item_name") or item.get("name"))
        shape_key = _text(item.get("shape_key"))
        layout_source = _text(item.get("layout_source")) or "live_grid"
        layout_source_counts[layout_source] += 1
        if layout_source == "settlement_inventory":
            settlement_items += 1
        if row is not None and col is not None:
            drawable_items += 1
            if layout_source == "settlement_inventory":
                settlement_drawable_items += 1
        q_label = f"Q{quality}" if quality is not None else "Q?"
        tooltip = _join_nonempty(
            [
                item_name,
                q_label,
                shape_key,
                category_label,
            ],
            sep=" / ",
        )
        if quality is not None:
            quality_counts[f"q{quality}"] += 1
        if category_label:
            category_counts[category_label] += 1
        if runtime_id is not None:
            known_runtime_ids.add(runtime_id)
        if local_index is not None:
            known_local_indexes.add(local_index)
        items.append(
            {
                "row": row,
                "col": col,
                "width": width,
                "height": height,
                "quality": quality,
                "category": item.get("category"),
                "category_label": category_label,
                "item_id": item.get("item_id"),
                "item_name": item_name,
                "display_label": "",
                "tooltip": tooltip,
                "shape_key": shape_key,
                "cells": item.get("cells"),
                "local_index": local_index,
                "source": _text(item.get("source")),
                "layout_source": layout_source,
                "render_mode": "footprint",
            }
        )
    quality_reveal_summary = _ui_minimap_quality_reveal_summary(
        artifact,
        known_runtime_ids=set(known_runtime_ids),
        known_local_indexes=set(known_local_indexes),
    )
    quality_markers = _ui_minimap_quality_markers(
        artifact,
        known_runtime_ids=known_runtime_ids,
        known_local_indexes=known_local_indexes,
    )
    for marker in quality_markers:
        row = _int_or_none(marker.get("row"))
        height = _int_or_none(marker.get("height")) or 1
        if row is not None:
            max_row = max(max_row, row + height - 1)
        quality = marker.get("quality")
        if quality is not None:
            quality_counts[f"q{quality}"] += 1
        items.append(marker)
    if quality_reveal_summary:
        quality_reveal_summary["quality_reveal_marker_count"] = len(quality_markers)
    rows_hint = min(
        _MINIMAP_MAX_ROWS,
        max(_MINIMAP_DEFAULT_ROWS, max_row),
    )
    final_total_items = _int_or_none(artifact.get("inventory_count"))
    layout_source = (
        "settlement_inventory"
        if layout_source_counts.get("settlement_inventory")
        else "live_known"
    )
    layout_complete = bool(
        artifact.get("phase") == "settled"
        and final_total_items is not None
        and final_total_items > 0
        and settlement_drawable_items >= final_total_items
    )
    return {
        "schema_version": 1,
        "status": "available",
        "layout_source": layout_source,
        "layout_complete": layout_complete,
        "drawable_items": drawable_items,
        "settlement_items": settlement_items,
        "settlement_drawable_items": settlement_drawable_items,
        "final_total_items": final_total_items,
        "columns": _MINIMAP_COLUMNS,
        "default_cells": _MINIMAP_DEFAULT_CELLS,
        "max_cells": _MINIMAP_MAX_CELLS,
        "viewport_rows": _MINIMAP_DEFAULT_ROWS,
        "max_rows": _MINIMAP_MAX_ROWS,
        "rows_hint": rows_hint,
        "scrollable": rows_hint > _MINIMAP_DEFAULT_ROWS,
        "known_items": len(items),
        "quality_counts": dict(sorted(quality_counts.items())),
        "category_counts": dict(category_counts.most_common()),
        **quality_reveal_summary,
        "items": items,
    }


def _ui_fallback_contract(artifact: Mapping[str, Any]) -> dict[str, Any]:
    bid = _first_mapping(artifact.get("fallback_bid_rows"))
    map_row = _first_mapping(artifact.get("fallback_map_rows"))
    warehouse = _first_mapping(artifact.get("fallback_warehouse_rows"))
    player_risks = [
        {
            "current_bid": _text(row.get("当前最高")),
            "risk_band": _text(row.get("风险带")),
        }
        for row in artifact.get("fallback_bid_rows", ()) or ()
        if isinstance(row, Mapping) and row.get("证据") == "玩家价位"
    ]
    active = bool(bid)
    return {
        "active": active,
        "mode": _text(bid.get("fallback_mode") or "v1_map_prior_zero_match")
        if active
        else "",
        "display_mode": "low_confidence_reference" if active else "",
        "affects_bid": False,
        "reason": "baseline_zero_match" if active else "",
        "note": _text(
            bid.get("fallback_note")
            or "v2 后验无匹配时的低置信参考；不替代 baseline v2"
        )
        if active
        else "",
        "decision": {
            "action": _text(bid.get("建议")),
            "current_highest": _text(bid.get("当前最高")),
            "risk_band": _text(bid.get("风险带")),
            "warehouse_multiplier": _text(bid.get("秒仓倍率")),
            "probe_bid": _text(bid.get("探价(P10)")),
            "defend_bid": _text(bid.get("防守价")),
            "attack_bid": _text(bid.get("可追价(P90)") or bid.get("抢仓上限")),
            "stop_price": _text(bid.get("停止价")),
            "evidence": _text(bid.get("证据")),
            "round": _text(bid.get("轮次")),
            "information_density": _text(bid.get("信息强度")),
            "warehouse_status": _text(bid.get("仓储")),
            "rationale": _text(bid.get("依据")),
            "next_info_hint": _text(bid.get("补信息")),
            "player_risks": player_risks,
        },
        "posterior": {
            "value_basis": _text(bid.get("价值口径") or "raw_value"),
            "raw_value_range": _text(
                bid.get("原始价值 P10/P50/P90")
                or warehouse.get("价值 P10/P50/P90")
                or map_row.get("价值 P10/P50/P90")
            ),
            "total_cells_range": _text(
                warehouse.get("总格 P10/P50/P90")
                or map_row.get("总格 P10/P50/P90")
            ),
            "match_text": _text(map_row.get("匹配") or warehouse.get("匹配")),
            "confidence": _text(warehouse.get("置信度")),
        },
    }


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ui_shadow_contract(
    shadow: Mapping[str, Any],
    model_eval: Mapping[str, Any],
) -> dict[str, Any]:
    label = _text(shadow.get("label"))
    prefix_by_label = {
        "profile_b5": "q6_residual_boost_shadow",
        "aisha_deep_floor1": "q6_residual_deep_floor_shadow",
        "aisha_deep11_floor1": "q6_residual_deep11_floor_shadow",
        "aisha_hidden_floor15": "q6_residual_hidden_floor_shadow",
        "aisha_villa_floor05": "q6_residual_villa_floor_shadow",
        "ethan_villa_random_avg_floor1": (
            "q6_residual_ethan_villa_random_floor_shadow"
        ),
        "ethan_shipwreck_layout_conditional_c4_cells15": (
            "q6_residual_ethan_shipwreck_layout_conditional_shadow"
        ),
    }
    prefix = prefix_by_label.get(label, "")
    active = bool(shadow.get("active"))
    role_by_label = {
        "profile_b5": "diagnostic_shadow",
        "aisha_deep_floor1": "tail_risk_reference_candidate",
        "aisha_deep11_floor1": "aisha_deep11_tail_risk_shadow",
        "aisha_hidden_floor15": "hidden_tail_risk_shadow",
        "aisha_villa_floor05": "villa_tail_risk_shadow",
        "ethan_villa_random_avg_floor1": "villa_random_avg_tail_risk_shadow",
        "ethan_shipwreck_layout_conditional_c4_cells15": (
            "shipwreck_layout_q6_likelihood_shadow"
        ),
    }
    display_by_label = {
        "profile_b5": "debug_only",
        "aisha_deep_floor1": "risk_reference_candidate",
        "aisha_deep11_floor1": "shadow_only_aisha_deep11_review",
        "aisha_hidden_floor15": "shadow_only_hidden_tail_review",
        "aisha_villa_floor05": "shadow_only_pending_no_q6_controls",
        "ethan_villa_random_avg_floor1": (
            "shadow_only_ethan_villa_random_avg_review"
        ),
        "ethan_shipwreck_layout_conditional_c4_cells15": (
            "shadow_only_ethan_shipwreck_q6_likelihood_review"
        ),
    }
    return {
        "label": label,
        "role": role_by_label.get(label, "shadow"),
        "display_mode": display_by_label.get(label, "debug_only"),
        "affects_bid": False,
        "active": active,
        "status": "active" if active else "inactive",
        "gate": _text(shadow.get("gate")),
        "evidence_profile": _text(shadow.get("evidence_profile_key")),
        "trials": shadow.get("trials"),
        "q6_decision_value_p90": shadow.get("q6_decision_value_p90"),
        "q6_count_p90": shadow.get("q6_count_p90"),
        "q6_cells_p90": shadow.get("q6_cells_p90"),
        "q6_p90_delta": (
            model_eval.get(f"{prefix}_q6_p90_delta")
            if prefix
            else None
        ),
        "helped": (
            bool(model_eval.get(f"{prefix}_helped"))
            if prefix
            else False
        ),
        "false_positive_proxy": (
            bool(model_eval.get(f"{prefix}_false_positive_proxy"))
            if prefix
            else False
        ),
    }


__all__ = (
    "ImportOverviewSnapshot",
    "LayoutStageSnapshot",
    "TacticalPanelSnapshot",
    "TacticalSummaryRow",
    "TacticalSnapshot",
    "action_result_rows_from_results",
    "import_overview_from_summary",
    "layout_replay_rows_from_stages",
    "packet_action_rows_from_sends",
    "player_bid_candidate_rows_from_bids",
    "tactical_panel_from_rows",
    "tactical_summary_rows",
    "tactical_snapshot_from_rows",
    "ui_contract_from_artifact",
)
