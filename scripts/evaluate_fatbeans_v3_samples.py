"""Evaluate v3 pre-bid constraint coverage for Fatbeans captures.

This is a shadow-only v3 scaffold. It emits auditable ConstraintSet,
FeasibleSummary, truth, prior, and small summary-conditioned posterior fields.
None of these fields affect live/formal bidding.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.inference.v3 import (  # noqa: E402
    PriorCalibrationEntry,
    calibrate_posterior_report,
    compile_feasible_summary,
    compile_hard_constraints,
    decision_truth_from_fatbeans,
    empty_decision_truth_flat_dict,
    empty_feasible_summary_flat_dict,
    empty_posterior_flat_dict,
    empty_prior_calibration_flat_dict,
    empty_truth_flat_dict,
    estimate_q6_posterior_from_truths,
    events_from_fatbeans,
    load_prior_calibration_entries,
    ordinary_shape_replacement_values,
    sample_truth_bank,
    settlement_truth_from_fatbeans,
    summarize_drop_prior,
)
from bidking_lab.live.fatbeans import (  # noqa: E402
    FatbeansCaptureEvents,
    parse_fatbeans_capture,
)
from bidking_lab.live.monitor import load_monitor_tables  # noqa: E402


def _default_paths() -> tuple[Path, ...]:
    root = ROOT / "data" / "samples" / "fatbeans"
    return (root,) if root.exists() else ()


def _default_calibration_path() -> Path:
    return ROOT / "data" / "processed" / "v3_prior_calibration_shadow.json"


def _iter_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(path.rglob("*.json"))
        elif path.exists():
            expanded.append(path)
    return tuple(sorted(set(expanded)))


def _events_before_sort(events: FatbeansCaptureEvents, sort_id: int) -> FatbeansCaptureEvents:
    return FatbeansCaptureEvents(
        packets=tuple(row for row in events.packets if int(row.sort_id) < sort_id),
        frames=tuple(row for row in events.frames if int(row.sort_id) < sort_id),
        sends=tuple(row for row in events.sends if int(row.sort_id) < sort_id),
        states=tuple(row for row in events.states if int(row.sort_id) < sort_id),
        statuses=tuple(row for row in events.statuses if int(row.sort_id) < sort_id),
    )


def _latest_map_id(events: FatbeansCaptureEvents) -> int | None:
    for state in reversed(events.states):
        map_id = getattr(state, "map_id", None)
        if map_id is not None:
            return int(map_id)
    return None


def _map_family(map_id: int | None) -> str:
    if map_id is None:
        return "unknown"
    family = int(map_id) // 100
    if family in (24, 34, 44):
        return "villa"
    if family in (25, 35, 45):
        return "shipwreck"
    if family in (26, 36, 46):
        return "hidden"
    return "other"


def _empty_prior_flat_dict() -> dict[str, Any]:
    return {
        "v3_prior_available": False,
        "v3_prior_error": None,
        "v3_prior_map_id": None,
        "v3_prior_map_name": None,
        "v3_prior_items_per_session_min": None,
        "v3_prior_items_per_session_max": None,
        "v3_prior_pool_count": None,
        "v3_prior_expected_draws": None,
        "v3_prior_expected_count": None,
        "v3_prior_expected_cells": None,
        "v3_prior_expected_value": None,
        "v3_prior_q6_draw_probability": None,
        "v3_prior_q6_session_probability": None,
        "v3_prior_q6_expected_count": None,
        "v3_prior_q6_expected_cells": None,
        "v3_prior_q6_expected_value": None,
    }


def _prior_flat_dict(
    map_id: int | None,
    *,
    tables: Any | None,
    cache: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    if map_id is None or tables is None:
        return _empty_prior_flat_dict()
    if map_id in cache:
        return cache[map_id]
    try:
        prior = summarize_drop_prior(
            int(map_id),
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
        )
    except Exception as exc:
        row = _empty_prior_flat_dict()
        row["v3_prior_error"] = type(exc).__name__
    else:
        row = {"v3_prior_available": True, "v3_prior_error": None}
        row.update(prior.to_flat_dict())
    cache[map_id] = row
    return row


def _replacement_values(
    map_id: int | None,
    *,
    tables: Any | None,
    cache: dict[int, dict[tuple[int, int, int], int]],
) -> dict[tuple[int, int, int], int]:
    if map_id is None or tables is None:
        return {}
    if map_id not in cache:
        try:
            cache[map_id] = ordinary_shape_replacement_values(
                int(map_id),
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
            )
        except Exception:
            cache[map_id] = {}
    return cache[map_id]


def _truth_bank(
    map_id: int | None,
    *,
    tables: Any | None,
    cache: dict[int, tuple[Any, ...]],
    n_trials: int,
    seed: int,
) -> tuple[Any, ...]:
    if map_id is None or tables is None or n_trials <= 0:
        return ()
    if map_id not in cache:
        try:
            cache[map_id] = sample_truth_bank(
                int(map_id),
                maps=tables.maps,
                drops=tables.drops,
                items=tables.items,
                n_trials=n_trials,
                seed=seed,
            )
        except Exception:
            cache[map_id] = ()
    return cache[map_id]


def _round_rows_for_events(
    path: Path,
    events: FatbeansCaptureEvents,
    *,
    tables: Any | None = None,
    calibration_entries: Mapping[int, PriorCalibrationEntry] | None = None,
    posterior_trials: int = 512,
    posterior_seed: int = 0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prior_cache: dict[int, dict[str, Any]] = {}
    replacement_cache: dict[int, dict[tuple[int, int, int], int]] = {}
    truth_bank_cache: dict[int, tuple[Any, ...]] = {}
    truth = (
        settlement_truth_from_fatbeans(events, items=tables.items)
        if tables is not None
        else None
    )
    truth_fields = truth.to_flat_dict() if truth is not None else empty_truth_flat_dict()
    empty_decision_truth_fields = empty_decision_truth_flat_dict()
    empty_summary_fields = empty_feasible_summary_flat_dict()
    empty_posterior_fields = empty_posterior_flat_dict()
    empty_calibration_fields = empty_prior_calibration_flat_dict()
    bid_sends = [send for send in events.sends if getattr(send, "kind", "") == "bid"]
    previous_bid_sort_id = 0
    for window_round, bid_send in enumerate(bid_sends, start=1):
        bid_sort_id = int(bid_send.sort_id)
        prefix = _events_before_sort(events, bid_sort_id)
        map_id = _latest_map_id(prefix)
        prior_fields = _prior_flat_dict(map_id, tables=tables, cache=prior_cache)
        round_states = [
            state
            for state in events.states
            if previous_bid_sort_id < int(state.sort_id) < bid_sort_id
        ]
        round_action_sends = [
            send
            for send in events.sends
            if getattr(send, "kind", "") == "action"
            and previous_bid_sort_id < int(send.sort_id) < bid_sort_id
        ]
        if not prefix.states:
            rows.append(
                {
                    "file": f"{path.name}#prebid_r{window_round}_sort{bid_sort_id}",
                    "source": "fatbeans_archive_v3_prebid",
                    "status": "no_state",
                    "round": window_round,
                    "session_id": getattr(bid_send, "session_id", None),
                    "bid_sort_id": bid_sort_id,
                    "bid_value": getattr(bid_send, "value", None),
                    "map_id": map_id,
                    "map_family": _map_family(map_id),
                    "prior_state_count": 0,
                    "round_state_count": len(round_states),
                    "round_action_send_count": len(round_action_sends),
                    "numeric_constraints": 0,
                    "item_anchors": 0,
                    "shape_anchors": 0,
                    "quality_floor_anchors": 0,
                    "conflicts": 0,
                    "constraint_ok": False,
                    **prior_fields,
                    **truth_fields,
                    **empty_decision_truth_fields,
                    **empty_summary_fields,
                    **empty_posterior_fields,
                    **empty_calibration_fields,
                }
            )
            previous_bid_sort_id = bid_sort_id
            continue
        constraints = compile_hard_constraints(events_from_fatbeans(prefix))
        feasible_summary = compile_feasible_summary(constraints)
        replacement_values = _replacement_values(
            map_id,
            tables=tables,
            cache=replacement_cache,
        )
        decision_truth = (
            decision_truth_from_fatbeans(
                events,
                items=tables.items,
                constraints=constraints,
                replacement_values=replacement_values,
            )
            if tables is not None
            else None
        )
        decision_truth_fields = (
            decision_truth.to_flat_dict()
            if decision_truth is not None
            else empty_decision_truth_fields
        )
        posterior_truths = _truth_bank(
            map_id,
            tables=tables,
            cache=truth_bank_cache,
            n_trials=posterior_trials,
            seed=posterior_seed,
        )
        posterior = (
            estimate_q6_posterior_from_truths(
                map_id=int(map_id),
                map_name=str(prior_fields.get("v3_prior_map_name") or ""),
                summary=feasible_summary,
                truths=posterior_truths,
                constraints=constraints,
                replacement_values=replacement_values,
            )
            if map_id is not None and tables is not None and posterior_trials > 0
            else None
        )
        posterior_fields = (
            posterior.to_flat_dict()
            if posterior is not None
            else empty_posterior_fields
        )
        calibration_entry = (
            calibration_entries.get(int(map_id))
            if calibration_entries is not None and map_id is not None
            else None
        )
        calibration = calibrate_posterior_report(posterior, calibration_entry)
        calibration_fields = calibration.to_flat_dict()
        rows.append(
            {
                "file": f"{path.name}#prebid_r{window_round}_sort{bid_sort_id}",
                "source": "fatbeans_archive_v3_prebid",
                "status": "ready" if constraints.feasible else "constraint_conflict",
                "round": window_round,
                "session_id": getattr(bid_send, "session_id", None),
                "bid_sort_id": bid_sort_id,
                "bid_value": getattr(bid_send, "value", None),
                "map_id": map_id,
                "map_family": _map_family(map_id),
                "prior_state_count": len(prefix.states),
                "round_state_count": len(round_states),
                "round_action_send_count": len(round_action_sends),
                "numeric_constraints": len(constraints.numeric),
                "item_anchors": len(constraints.item_anchors),
                "shape_anchors": len(constraints.shape_anchors),
                "quality_floor_anchors": len(constraints.quality_floor_anchors),
                "conflicts": len(constraints.conflicts),
                "constraint_ok": constraints.feasible,
                **prior_fields,
                **truth_fields,
                **decision_truth_fields,
                **feasible_summary.to_flat_dict(),
                **posterior_fields,
                **calibration_fields,
            }
        )
        previous_bid_sort_id = bid_sort_id
    return rows


def evaluate_paths(
    paths: Iterable[Path],
    *,
    tables: Any | None = None,
    calibration_entries: Mapping[int, PriorCalibrationEntry] | None = None,
    posterior_trials: int = 512,
    posterior_seed: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in _iter_paths(paths):
        try:
            events = parse_fatbeans_capture(path)
        except Exception as exc:
            errors.append({"file": str(path), "error": type(exc).__name__})
            continue
        rows.extend(
            _round_rows_for_events(
                path,
                events,
                tables=tables,
                calibration_entries=calibration_entries,
                posterior_trials=posterior_trials,
                posterior_seed=posterior_seed,
            )
        )
    return rows, errors


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _mean(values: Iterable[float]) -> float | None:
    seq = tuple(values)
    if not seq:
        return None
    return sum(seq) / len(seq)


def _round_metric(value: float | None, digits: int = 3) -> float | None:
    return round(value, digits) if value is not None else None


def _pinball_loss(truth: float, prediction: float, quantile: float) -> float:
    delta = truth - prediction
    if delta >= 0:
        return quantile * delta
    return (1.0 - quantile) * (-delta)


def _paired_metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    paired = [
        row
        for row in rows
        if row.get("status") == "ready"
        and row.get("v3_truth_decision_available")
        and row.get("v3_post_ready")
        and _float_or_none(row.get("v3_post_formal_decision_value_p50")) is not None
        and _float_or_none(row.get("v3_truth_formal_decision_value")) is not None
    ]
    calibrated = [
        row
        for row in rows
        if row.get("status") == "ready"
        and row.get("v3_truth_decision_available")
        and row.get("v3_cal_ready")
        and _float_or_none(row.get("v3_cal_formal_decision_value_p50")) is not None
        and _float_or_none(row.get("v3_truth_formal_decision_value")) is not None
    ]

    def pred_truth(
        pred_key: str,
        truth_key: str,
        *,
        scope: str | None = None,
        source_rows: Iterable[dict[str, Any]] | None = None,
    ) -> tuple[tuple[float, float], ...]:
        pairs: list[tuple[float, float]] = []
        iter_rows = tuple(source_rows) if source_rows is not None else paired
        for row in iter_rows:
            if scope == "strict" and row.get("v3_post_match_scope") != "strict":
                continue
            if scope == "fallback" and row.get("v3_post_match_scope") == "strict":
                continue
            pred = _float_or_none(row.get(pred_key))
            truth = _float_or_none(row.get(truth_key))
            if pred is None or truth is None:
                continue
            pairs.append((pred, truth))
        return tuple(pairs)

    formal_p50 = pred_truth(
        "v3_post_formal_decision_value_p50",
        "v3_truth_formal_decision_value",
    )
    formal_p50_strict = pred_truth(
        "v3_post_formal_decision_value_p50",
        "v3_truth_formal_decision_value",
        scope="strict",
    )
    formal_p50_fallback = pred_truth(
        "v3_post_formal_decision_value_p50",
        "v3_truth_formal_decision_value",
        scope="fallback",
    )
    formal_p90 = pred_truth(
        "v3_post_formal_decision_value_p90",
        "v3_truth_formal_decision_value",
    )
    formal_p90_strict = pred_truth(
        "v3_post_formal_decision_value_p90",
        "v3_truth_formal_decision_value",
        scope="strict",
    )
    formal_p90_fallback = pred_truth(
        "v3_post_formal_decision_value_p90",
        "v3_truth_formal_decision_value",
        scope="fallback",
    )
    q6_p50 = pred_truth(
        "v3_post_q6_formal_decision_value_p50",
        "v3_truth_q6_formal_decision_value",
    )
    q6_p50_strict = pred_truth(
        "v3_post_q6_formal_decision_value_p50",
        "v3_truth_q6_formal_decision_value",
        scope="strict",
    )
    q6_p50_fallback = pred_truth(
        "v3_post_q6_formal_decision_value_p50",
        "v3_truth_q6_formal_decision_value",
        scope="fallback",
    )
    q6_p90 = pred_truth(
        "v3_post_q6_formal_decision_value_p90",
        "v3_truth_q6_formal_decision_value",
    )
    cal_formal_p50 = pred_truth(
        "v3_cal_formal_decision_value_p50",
        "v3_truth_formal_decision_value",
        source_rows=calibrated,
    )
    cal_formal_p90 = pred_truth(
        "v3_cal_formal_decision_value_p90",
        "v3_truth_formal_decision_value",
        source_rows=calibrated,
    )
    cal_q6_p50 = pred_truth(
        "v3_cal_q6_formal_decision_value_p50",
        "v3_truth_q6_formal_decision_value",
        source_rows=calibrated,
    )
    cal_q6_p90 = pred_truth(
        "v3_cal_q6_formal_decision_value_p90",
        "v3_truth_q6_formal_decision_value",
        source_rows=calibrated,
    )

    def mae(pairs: tuple[tuple[float, float], ...]) -> float | None:
        return _mean(abs(pred - truth) for pred, truth in pairs)

    def bias(pairs: tuple[tuple[float, float], ...]) -> float | None:
        return _mean(pred - truth for pred, truth in pairs)

    def below_rate(pairs: tuple[tuple[float, float], ...]) -> float | None:
        return _mean(1.0 if pred < truth else 0.0 for pred, truth in pairs)

    def over_rate(pairs: tuple[tuple[float, float], ...]) -> float | None:
        return _mean(1.0 if pred > truth else 0.0 for pred, truth in pairs)

    def coverage_rate(pairs: tuple[tuple[float, float], ...]) -> float | None:
        return _mean(1.0 if truth <= pred else 0.0 for pred, truth in pairs)

    def pinball(pairs: tuple[tuple[float, float], ...], quantile: float) -> float | None:
        return _mean(_pinball_loss(truth, pred, quantile) for pred, truth in pairs)

    metric_scope_counts = Counter(
        str(row.get("v3_post_match_scope") or "none")
        for row in paired
        if row.get("v3_post_ready")
    )
    formal_p50_mae = mae(formal_p50)
    cal_formal_p50_mae = mae(cal_formal_p50)
    q6_formal_p50_mae = mae(q6_p50)
    cal_q6_formal_p50_mae = mae(cal_q6_p50)
    return {
        "metric_rows": len(paired),
        "metric_strict_rows": sum(
            1 for row in paired if row.get("v3_post_match_scope") == "strict"
        ),
        "metric_summary_likelihood_rows": metric_scope_counts.get(
            "summary_likelihood",
            0,
        ),
        "metric_q6_projection_rows": metric_scope_counts.get("q6_projection", 0),
        "metric_fallback_rows": sum(
            1
            for row in paired
            if row.get("v3_post_match_scope") != "strict"
        ),
        "formal_p50_mae": _round_metric(formal_p50_mae),
        "formal_p50_mae_strict": _round_metric(mae(formal_p50_strict)),
        "formal_p50_mae_fallback": _round_metric(mae(formal_p50_fallback)),
        "formal_p50_bias": _round_metric(bias(formal_p50)),
        "formal_p50_below_rate": _round_metric(below_rate(formal_p50), 6),
        "formal_p50_over_rate": _round_metric(over_rate(formal_p50), 6),
        "formal_p50_pinball": _round_metric(pinball(formal_p50, 0.5)),
        "formal_p90_coverage": _round_metric(coverage_rate(formal_p90), 6),
        "formal_p90_coverage_strict": _round_metric(
            coverage_rate(formal_p90_strict),
            6,
        ),
        "formal_p90_coverage_fallback": _round_metric(
            coverage_rate(formal_p90_fallback),
            6,
        ),
        "formal_p90_pinball": _round_metric(pinball(formal_p90, 0.9)),
        "q6_formal_p50_mae": _round_metric(q6_formal_p50_mae),
        "q6_formal_p50_mae_strict": _round_metric(mae(q6_p50_strict)),
        "q6_formal_p50_mae_fallback": _round_metric(mae(q6_p50_fallback)),
        "q6_formal_p50_bias": _round_metric(bias(q6_p50)),
        "q6_formal_p50_below_rate": _round_metric(below_rate(q6_p50), 6),
        "q6_formal_p50_over_rate": _round_metric(over_rate(q6_p50), 6),
        "q6_formal_p90_coverage": _round_metric(coverage_rate(q6_p90), 6),
        "q6_formal_p90_pinball": _round_metric(pinball(q6_p90, 0.9)),
        "v3_cal_metric_rows": len(calibrated),
        "v3_cal_active_rows": sum(1 for row in calibrated if row.get("v3_cal_active")),
        "v3_cal_formal_p50_mae": _round_metric(cal_formal_p50_mae),
        "v3_cal_formal_p50_bias": _round_metric(bias(cal_formal_p50)),
        "v3_cal_formal_p50_below_rate": _round_metric(
            below_rate(cal_formal_p50),
            6,
        ),
        "v3_cal_formal_p50_over_rate": _round_metric(
            over_rate(cal_formal_p50),
            6,
        ),
        "v3_cal_formal_p50_pinball": _round_metric(pinball(cal_formal_p50, 0.5)),
        "v3_cal_formal_p90_coverage": _round_metric(
            coverage_rate(cal_formal_p90),
            6,
        ),
        "v3_cal_formal_p90_pinball": _round_metric(pinball(cal_formal_p90, 0.9)),
        "v3_cal_q6_formal_p50_mae": _round_metric(cal_q6_formal_p50_mae),
        "v3_cal_q6_formal_p50_bias": _round_metric(bias(cal_q6_p50)),
        "v3_cal_q6_formal_p50_below_rate": _round_metric(
            below_rate(cal_q6_p50),
            6,
        ),
        "v3_cal_q6_formal_p50_over_rate": _round_metric(
            over_rate(cal_q6_p50),
            6,
        ),
        "v3_cal_q6_formal_p90_coverage": _round_metric(
            coverage_rate(cal_q6_p90),
            6,
        ),
        "v3_cal_delta_formal_p50_mae": _round_metric(
            cal_formal_p50_mae - formal_p50_mae
            if cal_formal_p50_mae is not None and formal_p50_mae is not None
            else None
        ),
        "v3_cal_delta_q6_formal_p50_mae": _round_metric(
            cal_q6_formal_p50_mae - q6_formal_p50_mae
            if cal_q6_formal_p50_mae is not None
            and q6_formal_p50_mae is not None
            else None
        ),
    }


def summarize_rows(rows: list[dict[str, Any]], errors: list[dict[str, str]]) -> dict[str, Any]:
    statuses = Counter(str(row.get("status") or "unknown") for row in rows)
    round_counts = Counter(f"R{row.get('round')}" for row in rows)
    posterior_scope_counts = Counter(
        str(row.get("v3_post_match_scope") or "none")
        for row in rows
        if row.get("v3_post_ready")
    )
    ready_rows = [row for row in rows if row.get("status") == "ready"]
    summary = {
        "windows": len(rows),
        "ready": statuses.get("ready", 0),
        "no_state": statuses.get("no_state", 0),
        "constraint_conflict": statuses.get("constraint_conflict", 0),
        "parse_errors": len(errors),
        "prior_ready": sum(1 for row in rows if row.get("v3_prior_available")),
        "truth_ready": sum(1 for row in rows if row.get("v3_truth_available")),
        "decision_truth_ready": sum(
            1 for row in rows if row.get("v3_truth_decision_available")
        ),
        "summary_ready": sum(1 for row in rows if row.get("v3_summary_available")),
        "summary_conflict": sum(
            1
            for row in rows
            if int(row.get("v3_summary_conflict_count") or 0) > 0
        ),
        "posterior_ready": sum(1 for row in rows if row.get("v3_post_ready")),
        "posterior_strict_ready": sum(
            1 for row in rows if row.get("v3_post_strict_ready")
        ),
        "posterior_summary_likelihood": posterior_scope_counts.get(
            "summary_likelihood",
            0,
        ),
        "posterior_q6_projection": posterior_scope_counts.get("q6_projection", 0),
        "posterior_fallback": sum(
            1
            for row in rows
            if row.get("v3_post_ready")
            and str(row.get("v3_post_match_scope") or "") != "strict"
        ),
        "posterior_no_match": sum(
            1
            for row in rows
            if row.get("v3_post_available")
            and not row.get("v3_post_ready")
        ),
        "status_counts": dict(sorted(statuses.items())),
        "round_counts": dict(sorted(round_counts.items())),
        "posterior_scope_counts": dict(sorted(posterior_scope_counts.items())),
        "numeric_constraints": sum(int(row.get("numeric_constraints") or 0) for row in ready_rows),
        "item_anchors": sum(int(row.get("item_anchors") or 0) for row in ready_rows),
        "shape_anchors": sum(int(row.get("shape_anchors") or 0) for row in ready_rows),
        "quality_floor_anchors": sum(int(row.get("quality_floor_anchors") or 0) for row in ready_rows),
        "errors": errors,
        "constraint_ok": statuses.get("constraint_conflict", 0) == 0,
        "parse_ok": not errors,
    }
    summary.update(_paired_metric_summary(rows))
    return summary


def _print_summary(summary: dict[str, Any]) -> None:
    print(
        " ".join(
            (
                f"windows={summary['windows']}",
                f"ready={summary['ready']}",
                f"no_state={summary['no_state']}",
                f"constraint_conflict={summary['constraint_conflict']}",
                f"parse_errors={summary['parse_errors']}",
                f"prior_ready={summary['prior_ready']}",
                f"truth_ready={summary['truth_ready']}",
                f"decision_truth_ready={summary['decision_truth_ready']}",
                f"summary_ready={summary['summary_ready']}",
                f"summary_conflict={summary['summary_conflict']}",
                f"posterior_ready={summary['posterior_ready']}",
                f"posterior_strict_ready={summary['posterior_strict_ready']}",
                f"posterior_summary_likelihood={summary['posterior_summary_likelihood']}",
                f"posterior_q6_projection={summary['posterior_q6_projection']}",
                f"posterior_fallback={summary['posterior_fallback']}",
                f"posterior_no_match={summary['posterior_no_match']}",
                f"metric_rows={summary['metric_rows']}",
                f"formal_p50_mae={summary['formal_p50_mae']}",
                f"formal_p50_mae_strict={summary['formal_p50_mae_strict']}",
                f"formal_p50_mae_fallback={summary['formal_p50_mae_fallback']}",
                f"formal_p50_below_rate={summary['formal_p50_below_rate']}",
                f"formal_p50_over_rate={summary['formal_p50_over_rate']}",
                f"formal_p90_coverage={summary['formal_p90_coverage']}",
                f"q6_formal_p50_mae={summary['q6_formal_p50_mae']}",
                f"q6_formal_p50_mae_strict={summary['q6_formal_p50_mae_strict']}",
                f"q6_formal_p50_mae_fallback={summary['q6_formal_p50_mae_fallback']}",
                f"q6_formal_p50_below_rate={summary['q6_formal_p50_below_rate']}",
                f"q6_formal_p50_over_rate={summary['q6_formal_p50_over_rate']}",
                f"v3_cal_active_rows={summary['v3_cal_active_rows']}",
                f"v3_cal_formal_p50_mae={summary['v3_cal_formal_p50_mae']}",
                f"v3_cal_delta_formal_p50_mae={summary['v3_cal_delta_formal_p50_mae']}",
                f"v3_cal_formal_p50_below_rate={summary['v3_cal_formal_p50_below_rate']}",
                f"v3_cal_formal_p50_over_rate={summary['v3_cal_formal_p50_over_rate']}",
                f"v3_cal_formal_p90_coverage={summary['v3_cal_formal_p90_coverage']}",
                f"numeric_constraints={summary['numeric_constraints']}",
                f"item_anchors={summary['item_anchors']}",
                f"shape_anchors={summary['shape_anchors']}",
                f"quality_floor_anchors={summary['quality_floor_anchors']}",
                f"constraint_ok={summary['constraint_ok']}",
            )
        )
    )
    if summary["errors"]:
        examples = ";".join(
            f"{item['file']}:{item['error']}"
            for item in summary["errors"][:5]
        )
        print("parse_error_examples=" + examples)


def _write_csv(rows: list[dict[str, Any]]) -> None:
    fieldnames = (
        "file",
        "source",
        "status",
        "round",
        "session_id",
        "bid_sort_id",
        "bid_value",
        "map_id",
        "map_family",
        "prior_state_count",
        "round_state_count",
        "round_action_send_count",
        "numeric_constraints",
        "item_anchors",
        "shape_anchors",
        "quality_floor_anchors",
        "conflicts",
        "constraint_ok",
        "v3_prior_available",
        "v3_prior_error",
        "v3_prior_map_id",
        "v3_prior_map_name",
        "v3_prior_items_per_session_min",
        "v3_prior_items_per_session_max",
        "v3_prior_pool_count",
        "v3_prior_expected_draws",
        "v3_prior_expected_count",
        "v3_prior_expected_cells",
        "v3_prior_expected_value",
        "v3_prior_q6_draw_probability",
        "v3_prior_q6_session_probability",
        "v3_prior_q6_expected_count",
        "v3_prior_q6_expected_cells",
        "v3_prior_q6_expected_value",
        "v3_truth_available",
        "v3_truth_session_id",
        "v3_truth_map_id",
        "v3_truth_sort_id",
        "v3_truth_item_count",
        "v3_truth_total_cells",
        "v3_truth_raw_total_value",
        "v3_truth_q6_count",
        "v3_truth_q6_cells",
        "v3_truth_q6_raw_value",
        "v3_truth_decision_available",
        "v3_truth_formal_decision_value",
        "v3_truth_tail_replacement_decision_value",
        "v3_truth_tail_replacement_value",
        "v3_truth_trimmed_tail_value",
        "v3_truth_trimmed_tail_count",
        "v3_truth_q6_formal_decision_value",
        "v3_truth_q6_tail_replacement_decision_value",
        "v3_truth_q6_tail_replacement_value",
        "v3_truth_q6_trimmed_tail_value",
        "v3_truth_q6_trimmed_tail_count",
        "v3_summary_available",
        "v3_summary_feasible",
        "v3_summary_conflict_count",
        "v3_summary_conflicts",
        "v3_summary_session_total_count_exact",
        "v3_summary_session_total_cells_exact",
        "v3_summary_known_count_floor",
        "v3_summary_known_cells_floor",
        "v3_summary_known_value_floor",
        "v3_summary_q6_count_exact",
        "v3_summary_q6_cells_exact",
        "v3_summary_q6_value_exact",
        "v3_summary_q6_count_floor",
        "v3_summary_q6_cells_floor",
        "v3_summary_q6_value_floor",
        "v3_summary_q6_residual_count_exact",
        "v3_summary_q6_residual_cells_exact",
        "v3_summary_q6_residual_value_exact",
        "v3_post_available",
        "v3_post_ready",
        "v3_post_strict_ready",
        "v3_post_affects_bid",
        "v3_post_map_id",
        "v3_post_map_name",
        "v3_post_match_scope",
        "v3_post_n_total",
        "v3_post_n_matched",
        "v3_post_n_strict_matched",
        "v3_post_match_rate",
        "v3_post_strict_match_rate",
        "v3_post_q6_present_rate",
        "v3_post_total_cells_p10",
        "v3_post_total_cells_p50",
        "v3_post_total_cells_p90",
        "v3_post_total_value_p10",
        "v3_post_total_value_p50",
        "v3_post_total_value_p90",
        "v3_post_formal_decision_value_p10",
        "v3_post_formal_decision_value_p50",
        "v3_post_formal_decision_value_p90",
        "v3_post_tail_replacement_decision_value_p10",
        "v3_post_tail_replacement_decision_value_p50",
        "v3_post_tail_replacement_decision_value_p90",
        "v3_post_q6_count_p10",
        "v3_post_q6_count_p50",
        "v3_post_q6_count_p90",
        "v3_post_q6_cells_p10",
        "v3_post_q6_cells_p50",
        "v3_post_q6_cells_p90",
        "v3_post_q6_value_p10",
        "v3_post_q6_value_p50",
        "v3_post_q6_value_p90",
        "v3_post_q6_formal_decision_value_p10",
        "v3_post_q6_formal_decision_value_p50",
        "v3_post_q6_formal_decision_value_p90",
        "v3_post_q6_tail_replacement_decision_value_p10",
        "v3_post_q6_tail_replacement_decision_value_p50",
        "v3_post_q6_tail_replacement_decision_value_p90",
        "v3_post_diagnostics",
        "v3_cal_available",
        "v3_cal_ready",
        "v3_cal_strict_ready",
        "v3_cal_affects_bid",
        "v3_cal_active",
        "v3_cal_status",
        "v3_cal_gate_reason",
        "v3_cal_scale",
        "v3_cal_archive_sessions",
        "v3_cal_prior_trials",
        "v3_cal_median_ratio",
        "v3_cal_p90_ratio",
        "v3_cal_formal_p50_over_rate",
        "v3_cal_baseline_formal_p50_mae",
        "v3_cal_baseline_formal_p50_bias",
        "v3_cal_source",
        "v3_cal_match_scope",
        "v3_cal_n_total",
        "v3_cal_n_matched",
        "v3_cal_n_strict_matched",
        "v3_cal_match_rate",
        "v3_cal_strict_match_rate",
        "v3_cal_total_value_p10",
        "v3_cal_total_value_p50",
        "v3_cal_total_value_p90",
        "v3_cal_formal_decision_value_p10",
        "v3_cal_formal_decision_value_p50",
        "v3_cal_formal_decision_value_p90",
        "v3_cal_tail_replacement_decision_value_p10",
        "v3_cal_tail_replacement_decision_value_p50",
        "v3_cal_tail_replacement_decision_value_p90",
        "v3_cal_q6_value_p10",
        "v3_cal_q6_value_p50",
        "v3_cal_q6_value_p90",
        "v3_cal_q6_formal_decision_value_p10",
        "v3_cal_q6_formal_decision_value_p50",
        "v3_cal_q6_formal_decision_value_p90",
        "v3_cal_q6_tail_replacement_decision_value_p10",
        "v3_cal_q6_tail_replacement_decision_value_p50",
        "v3_cal_q6_tail_replacement_decision_value_p90",
        "v3_cal_diagnostics",
    )
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate v3 pre-bid constraint coverage for Fatbeans captures.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument(
        "--format",
        choices=("summary", "json", "jsonl", "csv"),
        default="summary",
    )
    parser.add_argument(
        "--skip-table-report",
        action="store_true",
        help="Skip v3 prior/truth fields and only audit pre-bid constraints.",
    )
    parser.add_argument(
        "--posterior-trials",
        type=int,
        default=512,
        help="Prior sample bank size per map for v3 shadow posterior. Use 0 to disable.",
    )
    parser.add_argument("--posterior-seed", type=int, default=0)
    parser.add_argument(
        "--calibration",
        type=Path,
        default=_default_calibration_path(),
        help="Optional v3 prior calibration table. Defaults to data/processed/v3_prior_calibration_shadow.json when present.",
    )
    parser.add_argument(
        "--no-calibration",
        action="store_true",
        help="Disable v3 prior calibration shadow fields.",
    )
    parser.add_argument("--fail-on-conflicts", action="store_true")
    parser.add_argument("--fail-on-parse-errors", action="store_true")
    args = parser.parse_args(argv)

    tables = None if args.skip_table_report else load_monitor_tables()
    calibration_entries = (
        {}
        if args.no_calibration or args.skip_table_report
        else load_prior_calibration_entries(args.calibration)
    )
    rows, errors = evaluate_paths(
        args.paths or _default_paths(),
        tables=tables,
        calibration_entries=calibration_entries,
        posterior_trials=args.posterior_trials,
        posterior_seed=args.posterior_seed,
    )
    summary = summarize_rows(rows, errors)
    if args.format == "json":
        print(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.format == "jsonl":
        for row in rows:
            print(json.dumps(row, ensure_ascii=False, sort_keys=True))
    elif args.format == "csv":
        _write_csv(rows)
    else:
        _print_summary(summary)

    if args.fail_on_conflicts and not summary["constraint_ok"]:
        return 1
    if args.fail_on_parse_errors and not summary["parse_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
