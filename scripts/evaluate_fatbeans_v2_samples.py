"""Batch-evaluate Fatbeans captures with the evidence-first v2 posterior."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.inference.diagnostics import layout_conflict_root  # noqa: E402
from bidking_lab.inference.v2 import (  # noqa: E402
    build_residual_problem,
    estimate_posterior_v2,
    evidence_store_from_fatbeans_events,
    is_tail_supported_by_evidence,
)
from bidking_lab.live.fatbeans import (  # noqa: E402
    latest_player_bids,
    live_batches_from_fatbeans_events,
    parse_fatbeans_capture,
)
from bidking_lab.live.monitor import (  # noqa: E402
    _inventory_totals,
    _inventory_value,
    _states_to_session,
    load_monitor_tables,
)
from bidking_lab.simulation.robust_value import (  # noqa: E402
    DEFAULT_VALUE_FLOOR,
    is_confusable_long_tail,
)


def _default_paths() -> list[Path]:
    paths: list[Path] = []
    for root in (
        Path(r"C:\Users\shenc\Desktop\bid_king_packages"),
        ROOT / "data" / "samples" / "fatbeans",
    ):
        if root.exists():
            paths.extend(sorted(root.glob("*.json")))
    return paths


def _iter_unique(paths: Iterable[Path]) -> Iterable[Path]:
    seen: set[str] = set()
    for path in paths:
        if path.name in seen:
            continue
        seen.add(path.name)
        yield path


def _round(value: float | int | None) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def _map_family(file: str, map_id: int | None) -> str:
    if map_id is not None:
        prefix = map_id // 100
        if map_id == 2601:
            return "hidden"
        if prefix in {24, 34, 44}:
            return "villa"
        if prefix in {25, 35, 45}:
            return "shipwreck"
        return f"map_{prefix}xx"
    lower = file.lower()
    if "hidden" in lower or "secret" in lower:
        return "hidden"
    if "villa" in lower:
        return "villa"
    if "shipwreck" in lower:
        return "shipwreck"
    if map_id is None:
        return "unknown"
    return f"map_{map_id // 100}xx"


def _value_tier(value: int | None) -> str:
    if value is None:
        return "unknown"
    if value < 300_000:
        return "<300k"
    if value < 800_000:
        return "300k-800k"
    if value < 1_200_000:
        return "800k-1.2m"
    return ">=1.2m"


def _format_bucket_targets(problem: Any) -> str:
    parts: list[str] = []
    for quality, target in sorted(problem.bucket_targets.items()):
        fields: list[str] = []
        if target.count_exact is not None:
            fields.append(f"count={target.count_exact}")
        if target.total_cells_exact is not None:
            fields.append(f"cells={target.total_cells_exact}")
        if target.count_floor is not None and target.count_exact is None:
            fields.append(f"count>={target.count_floor}")
        if target.total_cells_floor is not None and target.total_cells_exact is None:
            fields.append(f"cells>={target.total_cells_floor}")
        if target.value_floor is not None:
            if getattr(target, "value_exact", None) is not None:
                fields.append(f"value={target.value_exact}")
            else:
                fields.append(f"value>={target.value_floor}")
        if target.avg_value is not None:
            fields.append(f"avg={target.avg_value:.2f}")
        if fields:
            parts.append(f"q{quality}:" + ",".join(fields))
    return ";".join(parts)


def _format_quality_map(values: Any) -> str:
    return ";".join(
        f"q{quality}={value}"
        for quality, value in sorted(values.items())
        if value
    )


def _inventory_truth_breakdown(
    events: Any,
    items: Any,
    *,
    problem: Any | None = None,
) -> dict[str, Any]:
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
        for inv_item in state.inventory_items:
            item = items.get(inv_item.item_id)
            quality = inv_item.quality
            if quality is None and item is not None:
                quality = item.quality
            if quality is None:
                continue
            value = item.value if item is not None else 0
            trim_item = False
            if item is not None and is_confusable_long_tail(item):
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
            else:
                decision_value += value
            counts[int(quality)] += 1
            cells[int(quality)] += inv_item.cells
            values[int(quality)] += value
            if not top_item or value > int(top_item.get("value") or 0):
                top_item = {
                    "id": inv_item.item_id,
                    "name": item.name if item is not None else "",
                    "quality": int(quality),
                    "value": value,
                    "cells": inv_item.cells,
                }
        return {
            "final_quality_counts": _format_quality_map(counts),
            "final_quality_cells": _format_quality_map(cells),
            "final_quality_values": _format_quality_map(values),
            "final_q5_count": counts.get(5, 0),
            "final_q5_value": values.get(5, 0),
            "final_q6_count": counts.get(6, 0),
            "final_q6_value": values.get(6, 0),
            "final_decision_value": decision_value,
            "final_trimmed_tail_value": trimmed_value,
            "final_trimmed_tail_items": ";".join(trimmed_items),
            "final_top_item_id": top_item.get("id"),
            "final_top_item_name": top_item.get("name"),
            "final_top_item_quality": top_item.get("quality"),
            "final_top_item_value": top_item.get("value"),
            "final_top_item_cells": top_item.get("cells"),
        }
    return {}


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _anchor_band(anchor_count: Any) -> str:
    count = _int_or_none(anchor_count)
    if count is None:
        return "unknown"
    if count == 0:
        return "0"
    if count <= 2:
        return "1-2"
    if count <= 5:
        return "3-5"
    return "6+"


def _q6_top_size_band(row: dict[str, Any]) -> str:
    if int(row.get("final_q6_count") or 0) <= 0:
        return "no_q6"
    if _int_or_none(row.get("final_top_item_quality")) != 6:
        return "q6_not_top_item"
    cells = _int_or_none(row.get("final_top_item_cells"))
    if cells is None:
        return "q6_top_unknown_cells"
    if cells <= 2:
        return "q6_top_small"
    if cells <= 4:
        return "q6_top_compact"
    if cells <= 8:
        return "q6_top_medium"
    if cells <= 12:
        return "q6_top_large"
    return "q6_top_huge"


def _public_constraint_key(row: dict[str, Any]) -> str:
    parts: list[str] = []
    if row.get("public_max_quality_used"):
        parts.append("max_quality")
    if row.get("public_max_item_cells_used"):
        parts.append("max_item_cells")
    return "+".join(parts) if parts else "none"


def _exact_bucket_markers(bucket_targets: Any) -> list[str]:
    text = str(bucket_targets or "")
    markers: list[str] = []
    for match in re.finditer(r"q(?P<q>\d+):(?P<fields>[^;]+)", text):
        quality = match.group("q")
        fields = match.group("fields")
        has_count = "count=" in fields
        has_cells = "cells=" in fields
        has_value = "value=" in fields
        if has_count and has_cells:
            markers.append(f"q{quality}_exact_count_cells")
        elif has_count:
            markers.append(f"q{quality}_exact_count")
        elif has_cells:
            markers.append(f"q{quality}_exact_cells")
        if has_value:
            markers.append(f"q{quality}_exact_value")
        if "avg=" in fields:
            markers.append(f"q{quality}_avg_value")
    return markers


def _zero_match_root(row: dict[str, Any]) -> str:
    if row.get("v2_matched"):
        return ""
    markers: list[str] = []
    if row.get("layout_conflict"):
        markers.append("layout_conflict")
        markers.extend(
            part
            for part in str(row.get("layout_conflict_root") or "").split(";")
            if part
        )
    if row.get("relaxed_exact_used"):
        markers.append("relaxed_exact_fallback")
    if row.get("public_max_quality_used"):
        markers.append("public_max_quality")
    if row.get("public_max_item_cells_used"):
        markers.append("public_max_item_cells")
    markers.extend(_exact_bucket_markers(row.get("bucket_targets")))
    if not markers:
        markers.append("unclassified")
    return ";".join(dict.fromkeys(markers))


def _q6_miss_root(row: dict[str, Any]) -> str:
    if not row.get("q6_p90_misses_truth"):
        return ""
    markers: list[str] = []
    if row.get("q6_false_low_risk"):
        markers.append("low_q6_sample_rate")
    if "q6_below_drop_prior:" in str(row.get("diagnostics") or ""):
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
    if row.get("public_max_quality_used"):
        markers.append("public_max_quality")
    if row.get("public_max_item_cells_used"):
        markers.append("public_max_item_cells")
    markers.extend(
        marker
        for marker in _exact_bucket_markers(row.get("bucket_targets"))
        if marker.startswith("q6_")
    )
    return ";".join(dict.fromkeys(markers))


def evaluate_path(
    path: Path,
    *,
    tables: Any,
    n_trials: int,
    seed: int,
    cells_tol: int,
    count_tol: int,
) -> dict[str, Any]:
    try:
        events = parse_fatbeans_capture(path)
        batches = live_batches_from_fatbeans_events(events)
        base_session, *_ = _states_to_session(batches)
        final_value = _inventory_value(events, tables.items)
        inventory_count, final_cells = _inventory_totals(events)
        latest_bids = latest_player_bids(events.states)
        highest_bid = max(latest_bids.values()) if latest_bids else None
        if base_session is None:
            return {"file": path.name, "status": "skip", "reason": "no_session_obs"}
        if final_value is None:
            return {"file": path.name, "status": "skip", "reason": "no_inventory_truth"}

        store = evidence_store_from_fatbeans_events(events)
        problem = build_residual_problem(
            base_session.map_id,
            store,
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
            obs=base_session,
        )
        truth_breakdown = _inventory_truth_breakdown(
            events,
            tables.items,
            problem=problem,
        )
        report = estimate_posterior_v2(
            base_session.map_id,
            base_session,
            store,
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
            n_trials=n_trials,
            seed=seed,
            cells_tol=cells_tol,
            count_tol=count_tol,
        )
        value_p10 = _round(report.total_value.p10 if report.total_value else None)
        value_p50 = _round(report.total_value.p50 if report.total_value else None)
        value_p90 = _round(report.total_value.p90 if report.total_value else None)
        decision_p10 = _round(report.decision_value.p10 if report.decision_value else None)
        decision_p50 = _round(report.decision_value.p50 if report.decision_value else None)
        decision_p90 = _round(report.decision_value.p90 if report.decision_value else None)
        q6_value_p50 = _round(report.q6_value.p50 if report.q6_value else None)
        q6_value_p90 = _round(report.q6_value.p90 if report.q6_value else None)
        cells_p10 = _round(report.total_cells.p10 if report.total_cells else None)
        cells_p50 = _round(report.total_cells.p50 if report.total_cells else None)
        cells_p90 = _round(report.total_cells.p90 if report.total_cells else None)
        diagnostics = ";".join(report.diagnostics)
        layout_diagnostics = ";".join(report.layout_diagnostics)
        layout_root = layout_conflict_root(
            layout_diagnostics,
            footprint_count=problem.layout.footprint_count,
            trusted_footprint_count=problem.layout.trusted_footprint_count,
        )
        final_q6_value = int(truth_breakdown.get("final_q6_value") or 0)
        row = {
            "file": path.name,
            "status": "ok",
            "hero": base_session.hero,
            "map_id": base_session.map_id,
            "map_family": _map_family(path.name, base_session.map_id),
            "value_tier": _value_tier(final_value),
            "inventory_count": inventory_count,
            "final_value": final_value,
            "final_cells": final_cells,
            "highest_bid": highest_bid,
            "highest_bid_over_final": (
                highest_bid / final_value
                if highest_bid is not None and final_value > 0
                else None
            ),
            "highest_bid_minus_final": (
                highest_bid - final_value if highest_bid is not None else None
            ),
            **truth_breakdown,
            "v2_matched": report.n_matched,
            "v2_match_rate": report.n_matched / max(1, report.n_total),
            "v2_value_p10": value_p10,
            "v2_value_p50": value_p50,
            "v2_value_p90": value_p90,
            "v2_decision_value_p10": decision_p10,
            "v2_decision_value_p50": decision_p50,
            "v2_decision_value_p90": decision_p90,
            "v2_decision_value_p50_error": (
                decision_p50 - truth_breakdown["final_decision_value"]
                if decision_p50 is not None and "final_decision_value" in truth_breakdown
                else None
            ),
            "v2_decision_value_p90_error": (
                decision_p90 - truth_breakdown["final_decision_value"]
                if decision_p90 is not None and "final_decision_value" in truth_breakdown
                else None
            ),
            "v2_q6_match_rate": report.q6_match_rate,
            "v2_q6_prior_match_rate": report.q6_prior_match_rate,
            "v2_q6_prior_expected_value": _round(report.q6_prior_expected_value),
            "v2_q6_value_p50": q6_value_p50,
            "v2_q6_value_p90": q6_value_p90,
            "v2_q6_value_p90_error": (
                q6_value_p90 - final_q6_value if q6_value_p90 is not None else None
            ),
            "v2_q6_value_p90_under_by": (
                max(0, final_q6_value - q6_value_p90)
                if q6_value_p90 is not None
                else None
            ),
            "v2_value_p50_error": (
                value_p50 - final_value if value_p50 is not None else None
            ),
            "v2_value_p90_error": (
                value_p90 - final_value if value_p90 is not None else None
            ),
            "v2_value_p90_covers_final": (
                value_p90 >= final_value if value_p90 is not None else None
            ),
            "v2_cells_p10": cells_p10,
            "v2_cells_p50": cells_p50,
            "v2_cells_p90": cells_p90,
            "v2_cells_p50_error": (
                cells_p50 - final_cells
                if cells_p50 is not None and final_cells is not None
                else None
            ),
            "v2_cells_p90_error": (
                cells_p90 - final_cells
                if cells_p90 is not None and final_cells is not None
                else None
            ),
            "anchor_count": report.anchor_count,
            "known_value": report.known_value,
            "layout_score": report.layout_score,
            "layout_diagnostics": layout_diagnostics,
            "diagnostics": diagnostics,
            "relaxed_exact_used": "relaxed_exact_bucket_targets:" in diagnostics,
            "public_max_quality_used": "public_max_quality:" in diagnostics,
            "public_max_item_cells_used": "public_max_item_cells:" in diagnostics,
            "q6_below_drop_prior": "q6_below_drop_prior:" in diagnostics,
            "layout_conflict": bool(layout_root),
            "layout_conflict_root": layout_root,
            "q6_false_low_risk": (
                final_q6_value > 0
                and report.q6_match_rate is not None
                and report.q6_match_rate < 0.10
            ),
            "q6_p90_misses_truth": (
                final_q6_value > 0
                and q6_value_p90 is not None
                and q6_value_p90 < final_q6_value
            ),
            "bucket_targets": _format_bucket_targets(problem),
            "shape_target_count": len(problem.shape_targets),
            "footprint_count": problem.layout.footprint_count,
            "trusted_footprint_count": problem.layout.trusted_footprint_count,
            "footprint_occupied_cells": problem.layout.occupied_cells,
            "footprint_bottom_row": problem.layout.bottom_row,
        }
        row["anchor_band"] = _anchor_band(row.get("anchor_count"))
        row["q6_top_size_band"] = _q6_top_size_band(row)
        row["public_constraint_key"] = _public_constraint_key(row)
        row["zero_match_root"] = _zero_match_root(row)
        row["q6_miss_root"] = _q6_miss_root(row)
        return row
    except Exception as exc:
        return {
            "file": path.name,
            "status": "error",
            "reason": f"{type(exc).__name__}: {str(exc)[:160]}",
        }


def _q6_residual_floor_value(
    row: dict[str, Any],
    *,
    floor_ratio: float,
) -> int | None:
    if floor_ratio <= 0:
        return None
    if not row.get("q6_below_drop_prior"):
        return None
    if row.get("public_max_quality_used"):
        return None
    prior_value = row.get("v2_q6_prior_expected_value")
    if prior_value is None:
        return None
    return max(0, _round(float(prior_value) * floor_ratio) or 0)


def _q6_residual_floor_experiment(
    rows: list[dict[str, Any]],
    *,
    floor_ratio: float,
) -> dict[str, Any] | None:
    if floor_ratio <= 0:
        return None
    q6_truth = [
        row for row in rows
        if int(row.get("final_q6_value") or 0) > 0
        and row.get("v2_q6_value_p90") is not None
    ]
    if not q6_truth:
        return {
            "enabled": True,
            "floor_ratio": floor_ratio,
            "q6_truth_files": 0,
            "eligible_rows": 0,
            "q6_value_p90_coverage": None,
            "q6_p90_misses_truth": 0,
        }
    eligible_rows = 0
    adjusted_misses = 0
    floors: list[int] = []
    for row in q6_truth:
        q6_p90 = int(row.get("v2_q6_value_p90") or 0)
        floor_value = _q6_residual_floor_value(row, floor_ratio=floor_ratio)
        if floor_value is not None:
            eligible_rows += 1
            floors.append(floor_value)
            q6_p90 = max(q6_p90, floor_value)
        if q6_p90 < int(row.get("final_q6_value") or 0):
            adjusted_misses += 1
    return {
        "enabled": True,
        "floor_ratio": floor_ratio,
        "q6_truth_files": len(q6_truth),
        "eligible_rows": eligible_rows,
        "eligible_no_q6_rows": sum(
            1 for row in rows
            if int(row.get("final_q6_value") or 0) <= 0
            and _q6_residual_floor_value(row, floor_ratio=floor_ratio) is not None
        ),
        "floor_median": _round(statistics.median(floors)) if floors else None,
        "q6_value_p90_coverage": round(
            1.0 - adjusted_misses / len(q6_truth),
            4,
        ),
        "q6_p90_misses_truth": adjusted_misses,
    }


def _summary(
    rows: list[dict[str, Any]],
    *,
    q6_residual_floor_ratio: float = 0.0,
) -> dict[str, Any]:
    ok = [row for row in rows if row.get("status") == "ok"]
    valued = [
        row for row in ok
        if row.get("v2_value_p50_error") is not None
    ]
    zero = [
        row for row in ok
        if not row.get("v2_matched")
    ]
    relaxed = [
        row for row in ok
        if row.get("relaxed_exact_used")
    ]
    layout_conflict = [row for row in ok if row.get("layout_conflict")]
    q6_false_low = [row for row in ok if row.get("q6_false_low_risk")]
    q6_below_prior = [row for row in ok if row.get("q6_below_drop_prior")]
    q6_p90_miss = [row for row in ok if row.get("q6_p90_misses_truth")]
    high_value_undercovered = [
        row for row in ok
        if row.get("value_tier") == ">=1.2m"
        and row.get("v2_value_p90_covers_final") is False
    ]
    abs_errors = [abs(int(row["v2_value_p50_error"])) for row in valued]
    decision_valued = [
        row for row in ok
        if row.get("v2_decision_value_p50_error") is not None
    ]
    regular_decision_valued = [
        row for row in decision_valued
        if int(row.get("final_trimmed_tail_value") or 0) == 0
    ]
    tail_event_decision_valued = [
        row for row in decision_valued
        if int(row.get("final_trimmed_tail_value") or 0) > 0
    ]
    decision_abs_errors = [
        abs(int(row["v2_decision_value_p50_error"])) for row in decision_valued
    ]
    regular_decision_abs_errors = [
        abs(int(row["v2_decision_value_p50_error"]))
        for row in regular_decision_valued
    ]
    tail_event_decision_abs_errors = [
        abs(int(row["v2_decision_value_p50_error"]))
        for row in tail_event_decision_valued
    ]
    p90_valued = [
        row for row in ok
        if row.get("v2_value_p90_error") is not None
    ]
    p90_abs_errors = [abs(int(row["v2_value_p90_error"])) for row in p90_valued]
    q6_rows = [row for row in valued if int(row.get("final_q6_count") or 0) > 0]
    summary = {
        "files": len(rows),
        "ok": len(ok),
        "valued": len(valued),
        "zero_match": len(zero),
        "relaxed_exact": len(relaxed),
        "zero_match_after_relax": sum(1 for row in zero if row.get("relaxed_exact_used")),
        "layout_conflict": len(layout_conflict),
        "zero_match_with_layout_conflict": sum(
            1 for row in zero if row.get("layout_conflict")
        ),
        "q6_false_low_risk": len(q6_false_low),
        "q6_below_drop_prior": len(q6_below_prior),
        "q6_p90_misses_truth": len(q6_p90_miss),
        "high_value_p90_undercovered": len(high_value_undercovered),
        "skip_or_error": len(rows) - len(ok),
        "value_mae": _round(statistics.mean(abs_errors)) if abs_errors else None,
        "value_median_abs_error": (
            _round(statistics.median(abs_errors)) if abs_errors else None
        ),
        "decision_value_mae": (
            _round(statistics.mean(decision_abs_errors)) if decision_abs_errors else None
        ),
        "regular_decision_value_mae": (
            _round(statistics.mean(regular_decision_abs_errors))
            if regular_decision_abs_errors
            else None
        ),
        "tail_event_decision_value_mae": (
            _round(statistics.mean(tail_event_decision_abs_errors))
            if tail_event_decision_abs_errors
            else None
        ),
        "tail_event_count": len(tail_event_decision_valued),
        "decision_value_median_abs_error": (
            _round(statistics.median(decision_abs_errors))
            if decision_abs_errors
            else None
        ),
        "tail_event_trimmed_value_median": (
            _round(
                statistics.median(
                    int(row.get("final_trimmed_tail_value") or 0)
                    for row in tail_event_decision_valued
                )
            )
            if tail_event_decision_valued
            else None
        ),
        "value_p90_mae": (
            _round(statistics.mean(p90_abs_errors)) if p90_abs_errors else None
        ),
        "value_p90_median_abs_error": (
            _round(statistics.median(p90_abs_errors)) if p90_abs_errors else None
        ),
        "value_p90_coverage": (
            round(
                statistics.mean(
                    1.0 if row["v2_value_p90_covers_final"] else 0.0
                    for row in p90_valued
                ),
                4,
            )
            if p90_valued
            else None
        ),
        "mean_match_rate": (
            round(statistics.mean(row["v2_match_rate"] for row in valued), 4)
            if valued
            else None
        ),
        "q6_truth_files": len(q6_rows),
        "q6_value_p90_coverage": (
            round(
                statistics.mean(
                    0.0 if row.get("q6_p90_misses_truth") else 1.0
                    for row in q6_rows
                    if row.get("v2_q6_value_p90") is not None
                ),
                4,
            )
            if any(row.get("v2_q6_value_p90") is not None for row in q6_rows)
            else None
        ),
        "q6_truth_p90_coverage": (
            round(
                statistics.mean(
                    1.0 if row["v2_value_p90_covers_final"] else 0.0
                    for row in q6_rows
                ),
                4,
            )
            if q6_rows
            else None
        ),
        "worst_value_errors": sorted(
            (
                {
                    "file": row["file"],
                    "hero": row.get("hero"),
                    "map_id": row.get("map_id"),
                    "map_family": row.get("map_family"),
                    "value_tier": row.get("value_tier"),
                    "final_value": row.get("final_value"),
                    "v2_value_p50": row.get("v2_value_p50"),
                    "v2_value_p90": row.get("v2_value_p90"),
                    "final_decision_value": row.get("final_decision_value"),
                    "v2_decision_value_p50": row.get("v2_decision_value_p50"),
                    "v2_decision_value_p90": row.get("v2_decision_value_p90"),
                    "v2_value_p50_error": row.get("v2_value_p50_error"),
                    "v2_value_p90_error": row.get("v2_value_p90_error"),
                    "v2_decision_value_p50_error": row.get(
                        "v2_decision_value_p50_error"
                    ),
                    "v2_matched": row.get("v2_matched"),
                    "anchor_count": row.get("anchor_count"),
                    "v2_q6_match_rate": row.get("v2_q6_match_rate"),
                    "v2_q6_value_p90": row.get("v2_q6_value_p90"),
                    "final_q6_count": row.get("final_q6_count"),
                    "final_q6_value": row.get("final_q6_value"),
                    "final_top_item_name": row.get("final_top_item_name"),
                    "final_top_item_value": row.get("final_top_item_value"),
                    "layout_score": row.get("layout_score"),
                    "diagnostics": row.get("diagnostics"),
                }
                for row in valued
            ),
            key=lambda row: abs(int(row["v2_value_p50_error"])),
            reverse=True,
        )[:12],
        "zero_match_details": [
            {
                "file": row["file"],
                "hero": row.get("hero"),
                "map_id": row.get("map_id"),
                "map_family": row.get("map_family"),
                "final_value": row.get("final_value"),
                "bucket_targets": row.get("bucket_targets"),
                "zero_match_root": row.get("zero_match_root"),
                "diagnostics": row.get("diagnostics"),
            }
            for row in zero[:12]
        ],
        "q6_false_low_details": [
            {
                "file": row["file"],
                "hero": row.get("hero"),
                "map_id": row.get("map_id"),
                "final_q6_count": row.get("final_q6_count"),
                "final_q6_value": row.get("final_q6_value"),
                "v2_q6_match_rate": row.get("v2_q6_match_rate"),
                "v2_q6_value_p90": row.get("v2_q6_value_p90"),
                "v2_q6_value_p90_under_by": row.get("v2_q6_value_p90_under_by"),
                "q6_top_size_band": row.get("q6_top_size_band"),
                "q6_miss_root": row.get("q6_miss_root"),
                "diagnostics": row.get("diagnostics"),
            }
            for row in q6_false_low[:12]
        ],
        "zero_match_root_causes": _root_cause_summary(zero, "zero_match_root"),
        "layout_conflict_root_causes": _root_cause_summary(
            layout_conflict,
            "layout_conflict_root",
        ),
        "q6_miss_root_causes": _root_cause_summary(q6_p90_miss, "q6_miss_root"),
        "q6_calibration_priority": _q6_calibration_priority(ok),
        "q6_risk_groups": {
            "hero_map_family": _q6_group_summary(ok, ("hero", "map_family")),
            "map_family_value_tier": _q6_group_summary(
                ok,
                ("map_family", "value_tier"),
            ),
            "anchor_band": _q6_group_summary(ok, ("anchor_band",)),
            "public_constraint": _q6_group_summary(ok, ("public_constraint_key",)),
            "top_item_size": _q6_group_summary(ok, ("q6_top_size_band",)),
        },
        "groups": {
            "hero": _group_summary(ok, "hero"),
            "map_family": _group_summary(ok, "map_family"),
            "value_tier": _group_summary(ok, "value_tier"),
        },
        "collection_readiness": _collection_readiness(
            ok,
            target_per_hero_family=30,
            hidden_target_per_hero=10,
        ),
        "bid_gap": {
            "hero": _bid_gap_summary(ok, "hero"),
            "map_family": _bid_gap_summary(ok, "map_family"),
        },
    }
    experiment = _q6_residual_floor_experiment(
        ok,
        floor_ratio=q6_residual_floor_ratio,
    )
    if experiment is not None:
        summary["q6_residual_floor_experiment"] = experiment
    return summary


def _root_cause_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        raw = str(row.get(key) or "unclassified")
        markers = [part for part in raw.split(";") if part] or ["unclassified"]
        for marker in markers:
            counts[marker] += 1
            if len(examples[marker]) < 5:
                examples[marker].append(str(row.get("file") or ""))
    return [
        {
            "cause": cause,
            "n": n,
            "examples": examples[cause],
        }
        for cause, n in counts.most_common()
    ]


def _group_key(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    return "|".join(f"{key}={row.get(key) or 'unknown'}" for key in keys)


def _q6_group_summary(
    rows: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(_group_key(row, keys), []).append(row)

    out: list[dict[str, Any]] = []
    for group, group_rows in groups.items():
        q6_truth = [row for row in group_rows if int(row.get("final_q6_value") or 0) > 0]
        if not q6_truth:
            continue
        q6_misses = [row for row in q6_truth if row.get("q6_p90_misses_truth")]
        under_by = [
            int(row["v2_q6_value_p90_under_by"])
            for row in q6_misses
            if row.get("v2_q6_value_p90_under_by") is not None
        ]
        q6_p90_errors = [
            int(row["v2_q6_value_p90_error"])
            for row in q6_truth
            if row.get("v2_q6_value_p90_error") is not None
        ]
        out.append(
            {
                "group": group,
                "n": len(group_rows),
                "q6_truth": len(q6_truth),
                "q6_p90_misses_truth": len(q6_misses),
                "q6_false_low_risk": sum(
                    1 for row in q6_truth if row.get("q6_false_low_risk")
                ),
                "q6_below_drop_prior": sum(
                    1 for row in q6_truth if row.get("q6_below_drop_prior")
                ),
                "q6_miss_rate": round(len(q6_misses) / len(q6_truth), 4),
                "median_q6_under_by": (
                    _round(statistics.median(under_by)) if under_by else None
                ),
                "median_q6_p90_error": (
                    _round(statistics.median(q6_p90_errors))
                    if q6_p90_errors
                    else None
                ),
                "zero_match": sum(1 for row in group_rows if not row.get("v2_matched")),
                "layout_conflict": sum(
                    1 for row in group_rows if row.get("layout_conflict")
                ),
            }
        )
    return sorted(
        out,
        key=lambda row: (
            int(row["q6_p90_misses_truth"]),
            int(row["median_q6_under_by"] or 0),
            int(row["q6_truth"]),
        ),
        reverse=True,
    )


def _q6_calibration_priority(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = _q6_group_summary(rows, ("hero", "map_family"))
    return [
        {
            **row,
            "priority_reason": (
                "q6_p90_undercoverage"
                if row["q6_p90_misses_truth"]
                else "low_q6_truth_coverage"
            ),
        }
        for row in primary
        if row["q6_p90_misses_truth"] or row["q6_truth"] < 10
    ][:10]


def _collection_readiness(
    rows: list[dict[str, Any]],
    *,
    target_per_hero_family: int,
    hidden_target_per_hero: int,
) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        hero = str(row.get("hero") or "unknown")
        family = str(row.get("map_family") or "unknown")
        groups.setdefault((hero, family), []).append(row)

    rows_out: list[dict[str, Any]] = []
    for hero in ("aisha", "ethan"):
        for family in ("villa", "shipwreck", "hidden"):
            target = (
                hidden_target_per_hero
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
        "ready": missing == 0,
        "total_needed": missing,
        "groups": rows_out,
        "priority_needs": [
            row for row in rows_out
            if row["needed"] > 0
        ],
    }


def _bid_gap_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key) or "unknown"), []).append(row)
    summary: list[dict[str, Any]] = []
    for value, group_rows in sorted(groups.items()):
        ratios = [
            float(row["highest_bid_over_final"])
            for row in group_rows
            if row.get("highest_bid_over_final") is not None
        ]
        gaps = [
            int(row["highest_bid_minus_final"])
            for row in group_rows
            if row.get("highest_bid_minus_final") is not None
        ]
        summary.append(
            {
                key: value,
                "n": len(group_rows),
                "bid_rows": len(ratios),
                "highest_bid_over_final_median": (
                    round(statistics.median(ratios), 3) if ratios else None
                ),
                "highest_bid_over_final_p75": (
                    round(statistics.quantiles(ratios, n=4)[2], 3)
                    if len(ratios) >= 4
                    else None
                ),
                "highest_bid_over_final_rate": (
                    round(
                        statistics.mean(1.0 if ratio > 1.0 else 0.0 for ratio in ratios),
                        4,
                    )
                    if ratios
                    else None
                ),
                "highest_bid_minus_final_median": (
                    _round(statistics.median(gaps)) if gaps else None
                ),
            }
        )
    return summary


def _group_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key) or "unknown"), []).append(row)
    summary: list[dict[str, Any]] = []
    for value, group_rows in sorted(groups.items()):
        p50_abs = [
            abs(int(row["v2_value_p50_error"]))
            for row in group_rows
            if row.get("v2_value_p50_error") is not None
        ]
        decision_p50_abs = [
            abs(int(row["v2_decision_value_p50_error"]))
            for row in group_rows
            if row.get("v2_decision_value_p50_error") is not None
        ]
        p90_abs = [
            abs(int(row["v2_value_p90_error"]))
            for row in group_rows
            if row.get("v2_value_p90_error") is not None
        ]
        p90_rows = [
            row for row in group_rows
            if row.get("v2_value_p90_covers_final") is not None
        ]
        summary.append(
            {
                key: value,
                "n": len(group_rows),
                "zero_match": sum(1 for row in group_rows if not row.get("v2_matched")),
                "value_mae": _round(statistics.mean(p50_abs)) if p50_abs else None,
                "value_median_abs_error": (
                    _round(statistics.median(p50_abs)) if p50_abs else None
                ),
                "decision_value_mae": (
                    _round(statistics.mean(decision_p50_abs))
                    if decision_p50_abs
                    else None
                ),
                "value_p90_mae": (
                    _round(statistics.mean(p90_abs)) if p90_abs else None
                ),
                "value_p90_coverage": (
                    round(
                        statistics.mean(
                            1.0 if row["v2_value_p90_covers_final"] else 0.0
                            for row in p90_rows
                        ),
                        4,
                    )
                    if p90_rows
                    else None
                ),
                "mean_match_rate": round(
                    statistics.mean(row["v2_match_rate"] for row in group_rows),
                    4,
                ),
            }
        )
    return summary


def _write_csv(rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate Fatbeans JSON captures with v2 posterior.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="JSON files or directories. Defaults to desktop package dir + data/samples/fatbeans.",
    )
    parser.add_argument(
        "--format",
        choices=("summary", "jsonl", "csv"),
        default="summary",
    )
    parser.add_argument("--trials", type=int, default=300)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--cells-tol", type=int, default=8)
    parser.add_argument("--count-tol", type=int, default=3)
    parser.add_argument(
        "--q6-residual-floor-ratio",
        type=float,
        default=0.0,
        help=(
            "Offline what-if only: floor q6 P90 for q6_below_drop_prior rows "
            "to this fraction of q6 prior expected value in the summary."
        ),
    )
    args = parser.parse_args()

    paths: list[Path] = []
    if args.paths:
        for raw in args.paths:
            path = Path(raw)
            if path.is_dir():
                paths.extend(sorted(path.glob("*.json")))
            else:
                paths.append(path)
    else:
        paths = _default_paths()

    tables = load_monitor_tables()
    rows = [
        evaluate_path(
            path,
            tables=tables,
            n_trials=args.trials,
            seed=args.seed,
            cells_tol=args.cells_tol,
            count_tol=args.count_tol,
        )
        for path in _iter_unique(paths)
    ]

    if args.format == "jsonl":
        for row in rows:
            print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
    elif args.format == "csv":
        _write_csv(rows)
    else:
        print(
            json.dumps(
                _summary(
                    rows,
                    q6_residual_floor_ratio=args.q6_residual_floor_ratio,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
