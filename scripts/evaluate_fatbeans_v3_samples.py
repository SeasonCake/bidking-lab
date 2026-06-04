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
from typing import Any, Iterable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.inference.v3 import (  # noqa: E402
    compile_feasible_summary,
    compile_hard_constraints,
    decision_truth_from_fatbeans,
    empty_decision_truth_flat_dict,
    empty_feasible_summary_flat_dict,
    empty_posterior_flat_dict,
    empty_truth_flat_dict,
    estimate_q6_posterior_from_truths,
    events_from_fatbeans,
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
            )
            if map_id is not None and tables is not None and posterior_trials > 0
            else None
        )
        posterior_fields = (
            posterior.to_flat_dict()
            if posterior is not None
            else empty_posterior_fields
        )
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
            }
        )
        previous_bid_sort_id = bid_sort_id
    return rows


def evaluate_paths(
    paths: Iterable[Path],
    *,
    tables: Any | None = None,
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
                posterior_trials=posterior_trials,
                posterior_seed=posterior_seed,
            )
        )
    return rows, errors


def summarize_rows(rows: list[dict[str, Any]], errors: list[dict[str, str]]) -> dict[str, Any]:
    statuses = Counter(str(row.get("status") or "unknown") for row in rows)
    round_counts = Counter(f"R{row.get('round')}" for row in rows)
    ready_rows = [row for row in rows if row.get("status") == "ready"]
    return {
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
        "numeric_constraints": sum(int(row.get("numeric_constraints") or 0) for row in ready_rows),
        "item_anchors": sum(int(row.get("item_anchors") or 0) for row in ready_rows),
        "shape_anchors": sum(int(row.get("shape_anchors") or 0) for row in ready_rows),
        "quality_floor_anchors": sum(int(row.get("quality_floor_anchors") or 0) for row in ready_rows),
        "errors": errors,
        "constraint_ok": statuses.get("constraint_conflict", 0) == 0,
        "parse_ok": not errors,
    }


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
                f"posterior_fallback={summary['posterior_fallback']}",
                f"posterior_no_match={summary['posterior_no_match']}",
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
        "v3_post_q6_count_p10",
        "v3_post_q6_count_p50",
        "v3_post_q6_count_p90",
        "v3_post_q6_cells_p10",
        "v3_post_q6_cells_p50",
        "v3_post_q6_cells_p90",
        "v3_post_q6_value_p10",
        "v3_post_q6_value_p50",
        "v3_post_q6_value_p90",
        "v3_post_diagnostics",
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
    parser.add_argument("--fail-on-conflicts", action="store_true")
    parser.add_argument("--fail-on-parse-errors", action="store_true")
    args = parser.parse_args(argv)

    tables = None if args.skip_table_report else load_monitor_tables()
    rows, errors = evaluate_paths(
        args.paths or _default_paths(),
        tables=tables,
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
