"""Compact tactical snapshots for UI frontends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


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


def _string_row(row: Mapping[str, Any]) -> dict[str, str]:
    return {str(key): _text(value) for key, value in row.items()}


def _string_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int | None = None,
) -> tuple[dict[str, str], ...]:
    selected = rows if limit is None else rows[:limit]
    return tuple(_string_row(row) for row in selected)


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
        value_range=_text(warehouse.get("价值 P10/P50/P90") or "暂无后验"),
        warehouse_range=_text(
            warehouse.get("总格 P10/P50/P90")
            or bid.get("仓储")
            or "暂无后验"
        ),
        next_tool_hint=tool_hint,
        highest_bid=_text(bid.get("当前最高")),
        risk_band=_text(bid.get("风险带")),
        stop_price=_text(bid.get("停止价")),
        evidence=_text(bid.get("证据") or warehouse.get("匹配")),
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
)
