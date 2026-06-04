"""Evaluate v3 pre-bid constraint coverage for Fatbeans captures.

This is a shadow-only v3 scaffold. It does not estimate posterior value and it
does not affect live/formal bidding. The first contract is to prove that every
pre-bid window can produce an auditable ConstraintSet or a clear data-quality
status.
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
    compile_hard_constraints,
    events_from_fatbeans,
)
from bidking_lab.live.fatbeans import (  # noqa: E402
    FatbeansCaptureEvents,
    parse_fatbeans_capture,
)


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


def _round_rows_for_events(path: Path, events: FatbeansCaptureEvents) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    bid_sends = [send for send in events.sends if getattr(send, "kind", "") == "bid"]
    previous_bid_sort_id = 0
    for window_round, bid_send in enumerate(bid_sends, start=1):
        bid_sort_id = int(bid_send.sort_id)
        prefix = _events_before_sort(events, bid_sort_id)
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
                    "prior_state_count": 0,
                    "round_state_count": len(round_states),
                    "round_action_send_count": len(round_action_sends),
                    "numeric_constraints": 0,
                    "item_anchors": 0,
                    "shape_anchors": 0,
                    "quality_floor_anchors": 0,
                    "conflicts": 0,
                    "constraint_ok": False,
                }
            )
            previous_bid_sort_id = bid_sort_id
            continue
        constraints = compile_hard_constraints(events_from_fatbeans(prefix))
        rows.append(
            {
                "file": f"{path.name}#prebid_r{window_round}_sort{bid_sort_id}",
                "source": "fatbeans_archive_v3_prebid",
                "status": "ready" if constraints.feasible else "constraint_conflict",
                "round": window_round,
                "session_id": getattr(bid_send, "session_id", None),
                "bid_sort_id": bid_sort_id,
                "bid_value": getattr(bid_send, "value", None),
                "prior_state_count": len(prefix.states),
                "round_state_count": len(round_states),
                "round_action_send_count": len(round_action_sends),
                "numeric_constraints": len(constraints.numeric),
                "item_anchors": len(constraints.item_anchors),
                "shape_anchors": len(constraints.shape_anchors),
                "quality_floor_anchors": len(constraints.quality_floor_anchors),
                "conflicts": len(constraints.conflicts),
                "constraint_ok": constraints.feasible,
            }
        )
        previous_bid_sort_id = bid_sort_id
    return rows


def evaluate_paths(paths: Iterable[Path]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in _iter_paths(paths):
        try:
            events = parse_fatbeans_capture(path)
        except Exception as exc:
            errors.append({"file": str(path), "error": type(exc).__name__})
            continue
        rows.extend(_round_rows_for_events(path, events))
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
        "prior_state_count",
        "round_state_count",
        "round_action_send_count",
        "numeric_constraints",
        "item_anchors",
        "shape_anchors",
        "quality_floor_anchors",
        "conflicts",
        "constraint_ok",
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
    parser.add_argument("--fail-on-conflicts", action="store_true")
    parser.add_argument("--fail-on-parse-errors", action="store_true")
    args = parser.parse_args(argv)

    rows, errors = evaluate_paths(args.paths or _default_paths())
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
