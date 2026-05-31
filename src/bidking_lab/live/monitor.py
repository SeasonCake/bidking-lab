"""Live monitor artifact builder and append-only evaluation logs.

The monitor layer is intentionally source-agnostic: today it can process a
Fatbeans JSON payload or file; later a true realtime source can feed the same
``FatbeansCaptureEvents`` object without changing inference, logging, or UI.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping, Sequence

from bidking_lab.config import project_root
from bidking_lab.extract.bid_map_table import BidMap, load_bid_map_table
from bidking_lab.extract.drop_table import DropPool, load_drop_table
from bidking_lab.extract.item_table import Item, load_item_table
from bidking_lab.inference.bid_strategy import recommend_bid_strategy
from bidking_lab.inference.diagnostics import layout_conflict_root
from bidking_lab.inference.v2 import (
    estimate_posterior_v2,
    evidence_store_from_fatbeans_events,
)
from bidking_lab.inference.map_likelihood import estimate_map_likelihood
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
from bidking_lab.live.replay import layout_replay_stages
from bidking_lab.live.state import (
    LiveSessionState,
    apply_observation_batch,
    live_state_to_session_obs,
)
from bidking_lab.live.types import LiveObservationBatch
from bidking_lab.live.fatbeans import live_batches_from_fatbeans_events
from bidking_lab.runtime import (
    layout_replay_rows_from_stages,
    tactical_panel_from_rows,
)


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


def _v2_posterior_rows(report: Any) -> list[dict[str, Any]]:
    if report is None:
        return []
    diagnostics = ";".join(getattr(report, "diagnostics", ()) or ())
    return [
        {
            "范围": f"{report.map_id} {report.map_name}",
            "匹配": f"{report.n_matched}/{report.n_total}",
            "价值口径": "decision_value",
            "决策价值 P10/P50/P90": _format_quantile_interval(report.decision_value),
            "原始价值 P10/P50/P90": _format_quantile_interval(report.total_value),
            "q6价值 P10/P50/P90": _format_quantile_interval(report.q6_value),
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
            "q6先验价值": (
                f"{report.q6_prior_expected_value:,.0f}"
                if report.q6_prior_expected_value is not None
                else ""
            ),
            "诊断": diagnostics,
        }
    ]


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


def _latest_map_id(events: FatbeansCaptureEvents) -> int | None:
    for state in reversed(events.states):
        if state.map_id is not None:
            return state.map_id
    return None


def _inventory_totals(events: FatbeansCaptureEvents) -> tuple[int | None, int | None]:
    for state in reversed(events.states):
        if state.inventory_items:
            return len(state.inventory_items), sum(item.cells for item in state.inventory_items)
    return None, None


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
            "探价(P10)": f"{thresholds.probe_bid:,}",
            "防守价": f"{thresholds.defend_bid:,}",
            "抢仓上限": f"{thresholds.attack_bid:,}",
            "停止价": f"{thresholds.stop_bid:,}",
            "依据": report.rationale,
            "补信息": report.next_info_hint,
            "后验诊断": ";".join(posterior_diagnostics),
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
                "探价(P10)": "",
                "防守价": "",
                "抢仓上限": "",
                "停止价": "",
                "依据": "",
                "补信息": "",
                "建议": "",
            }
        )
    return rows


def _parse_range_value(label: str, index: int) -> int | None:
    parts = [part.strip().replace(",", "") for part in label.split("/")]
    if len(parts) <= index or parts[index] in ("", "?"):
        return None
    try:
        return int(float(parts[index]))
    except ValueError:
        return None


def _parse_range_p50(label: str) -> int | None:
    return _parse_range_value(label, 1)


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


def _inventory_quality_breakdown(
    events: FatbeansCaptureEvents,
    items: Mapping[int, Item],
) -> dict[str, Any]:
    for state in reversed(events.states):
        if not state.inventory_items:
            continue
        counts: Counter[int] = Counter()
        cells: Counter[int] = Counter()
        values: defaultdict[int, int] = defaultdict(int)
        for inv_item in state.inventory_items:
            item = items.get(inv_item.item_id)
            quality = inv_item.quality
            if quality is None and item is not None:
                quality = item.quality
            if quality is None:
                continue
            q = int(quality)
            counts[q] += 1
            cells[q] += inv_item.cells
            values[q] += item.value if item is not None else 0
        return {
            "final_q5_count": counts.get(5, 0),
            "final_q5_cells": cells.get(5, 0),
            "final_q5_value": values.get(5, 0),
            "final_q6_count": counts.get(6, 0),
            "final_q6_cells": cells.get(6, 0),
            "final_q6_value": values.get(6, 0),
        }
    return {}


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
    layout_rows = artifact.get("layout_replay_rows") or []
    v2_rows = artifact.get("v2_posterior_rows") or []
    warehouse_p50 = None
    value_p50 = None
    decision_value_p50 = None
    decision_value_p90 = None
    raw_value_p50 = None
    raw_value_p90 = None
    q6_match_rate = None
    q6_prior_match_rate = None
    q6_prior_expected_value = None
    q6_value_p90 = None
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
        q6_match_rate = _parse_percent_text(v2_rows[0].get("q6样本率"))
        q6_prior_match_rate = _parse_percent_text(v2_rows[0].get("q6掉落先验"))
        q6_prior_expected_value = _parse_int_text(v2_rows[0].get("q6先验价值"))
        q6_value_p90 = _parse_range_value(
            str(v2_rows[0].get("q6价值 P10/P50/P90", "")),
            2,
        )
        posterior_diagnostics = str(v2_rows[0].get("诊断") or "")
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
    return {
        "ts": time.time(),
        "file": file,
        "hero": artifact.get("hero"),
        "map_id": artifact.get("map_id"),
        "round": artifact.get("round"),
        "final_value": final_value,
        "final_cells": final_cells,
        **dict(truth_breakdown or {}),
        "value_p50": value_p50,
        "decision_value_p50": decision_value_p50,
        "decision_value_p90": decision_value_p90,
        "decision_value_p50_error": (
            decision_value_p50 - final_value
            if decision_value_p50 is not None and final_value is not None
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
        "v2_q6_prior_expected_value": q6_prior_expected_value,
        "v2_q6_value_p90": q6_value_p90,
        "q6_p90_misses_truth": (
            q6_value_p90 < int((truth_breakdown or {}).get("final_q6_value") or 0)
            if q6_value_p90 is not None
            and int((truth_breakdown or {}).get("final_q6_value") or 0) > 0
            else None
        ),
        "q6_false_low_risk": (
            q6_match_rate < 0.10
            if q6_match_rate is not None
            and int((truth_breakdown or {}).get("final_q6_value") or 0) > 0
            else None
        ),
        "q6_below_drop_prior": "q6_below_drop_prior:" in posterior_diagnostics,
        "relaxed_exact_used": "relaxed_exact_bucket_targets:" in posterior_diagnostics,
        "layout_conflict": bool(layout_root),
        "layout_conflict_root": layout_root,
        "posterior_diagnostics": posterior_diagnostics,
        "stop_minus_final_value": (
            stop_bid - final_value
            if stop_bid is not None and final_value is not None
            else None
        ),
    }


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


def build_monitor_artifact_from_events(
    events: FatbeansCaptureEvents,
    *,
    file: str = "",
    tables: MonitorTables,
    n_trials: int = 500,
    roi_trials: int = 250,
    seed: int = 20260530,
) -> dict[str, Any]:
    """Build a JSON-serializable live monitor artifact from parsed events."""
    batches = live_batches_from_fatbeans_events(events)
    base_session, final_session, _, _ = _states_to_session(batches)
    latest_bids = latest_player_bids(events.states)
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
    tool_rows: list[dict[str, Any]] = []
    bid_rows: list[dict[str, Any]] = []
    evidence_label = "暂无"
    if base_session is not None:
        candidate_map_ids = _candidate_map_ids_for_likelihood(
            base_session.map_id,
            tables.maps,
        )
        evidence_label = "结算前最后状态"
        cells_tol = 8
        count_tol = 3
        without_warehouse = replace(
            base_session,
            warehouse_total_cells=None,
            warehouse_total_cells_approx=None,
            warehouse_total_cells_tolerance=None,
            total_item_count=None,
        )
        inference_session = without_warehouse
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
            relaxed_session = _relax_exact_bucket_constraints(without_warehouse)
            if relaxed_session is not without_warehouse:
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
                    evidence_label = "结算前最后状态（放宽精确桶约束）"
        map_rows = _map_likelihood_result_rows(base_results, evidence_label)
        warehouse_rows = _warehouse_estimate_rows(warehouse_estimate)
        v2_report = estimate_posterior_v2(
            inference_session.map_id,
            inference_session,
            evidence_store_from_fatbeans_events(events),
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
            n_trials=n_trials,
            seed=seed + 2,
            cells_tol=cells_tol,
            count_tol=count_tol,
        )
        v2_posterior_rows = _v2_posterior_rows(v2_report)
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
                round_no=_latest_round(events),
                posterior_samples=v2_report.n_matched,
                warehouse_estimate=warehouse_estimate,
                decision_value_summary=v2_report.decision_value,
                raw_value_summary=v2_report.total_value,
                posterior_diagnostics=v2_report.diagnostics,
            )

    panel = tactical_panel_from_rows(
        bid_rows=bid_rows,
        warehouse_rows=warehouse_rows,
        tool_rows=tool_rows,
        layout_stage_rows=layout_stage_rows,
        layout_note="",
    )
    inventory_count, inventory_cells = _inventory_totals(events)
    final_value = _inventory_value(events, tables.items)
    truth_breakdown = _inventory_quality_breakdown(events, tables.items)
    artifact: dict[str, Any] = {
        "schema_version": 1,
        "created_at": time.time(),
        "file": file,
        "packets": len(events.packets),
        "frames": len(events.frames),
        "states": len(events.states),
        "batches": len(batches),
        "hero": base_session.hero if base_session is not None else None,
        "map_id": _latest_map_id(events),
        "round": _latest_round(events),
        "inventory_count": inventory_count,
        "inventory_cells": inventory_cells,
        "known_value_sum": final_value,
        **truth_breakdown,
        "latest_bids": dict(latest_bids),
        "evidence_label": evidence_label,
        "map_rows": map_rows,
        "warehouse_rows": warehouse_rows,
        "v2_posterior_rows": v2_posterior_rows,
        "tool_rows": tool_rows,
        "bid_rows": bid_rows,
        "layout_replay_rows": layout_replay_rows,
        "layout_stage_rows": layout_stage_rows,
        "panel": asdict(panel),
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
    return artifact


def build_monitor_artifact_from_file(
    path: str | Path,
    *,
    tables: MonitorTables,
    n_trials: int = 500,
    roi_trials: int = 250,
    seed: int = 20260530,
) -> dict[str, Any]:
    path = Path(path)
    return build_monitor_artifact_from_events(
        parse_fatbeans_capture(path),
        file=path.name,
        tables=tables,
        n_trials=n_trials,
        roi_trials=roi_trials,
        seed=seed,
    )


def build_monitor_artifact_from_payload(
    payload: str | bytes,
    *,
    file: str = "stdin",
    tables: MonitorTables,
    n_trials: int = 500,
    roi_trials: int = 250,
    seed: int = 20260530,
) -> dict[str, Any]:
    return build_monitor_artifact_from_events(
        parse_fatbeans_capture_payload(payload),
        file=file,
        tables=tables,
        n_trials=n_trials,
        roi_trials=roi_trials,
        seed=seed,
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
    tmp.replace(path)


def write_monitor_logs(
    artifact: Mapping[str, Any],
    *,
    log_dir: str | Path | None = None,
) -> None:
    """Write latest snapshot and append long-running JSONL logs."""
    root = Path(log_dir) if log_dir is not None else project_root() / "data" / "logs" / "live"
    root.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(root / "latest_snapshot.json", artifact)
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
