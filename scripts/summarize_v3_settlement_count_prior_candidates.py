"""Audit shadow-only settlement occupancy count prior candidates."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from bidking_lab.live.fatbeans import _first, _parse_fields, parse_fatbeans_capture  # noqa: E402
from bidking_lab.live.monitor import load_monitor_tables  # noqa: E402
from summarize_v3_settlement_payload_audit import (  # noqa: E402
    _inventory_block_metrics,
    _latest_settlement_payload,
)


DEFAULT_SAMPLE_ROOT = ROOT / "data" / "samples" / "fatbeans"
_TEMPORARY_BLUE_ZODIAC_ITEM_IDS = frozenset(range(1306003, 1306015))


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _numeric_values(values: Iterable[Any]) -> tuple[float, ...]:
    out: list[float] = []
    for value in values:
        if isinstance(value, bool) or value is None:
            continue
        try:
            out.append(float(value))
        except (TypeError, ValueError, OverflowError):
            continue
    return tuple(out)


def _percentile(sorted_values: tuple[float, ...], pct: float) -> float:
    if not sorted_values:
        raise ValueError("sorted_values must not be empty")
    index = min(
        len(sorted_values) - 1,
        max(0, int(round((len(sorted_values) - 1) * pct))),
    )
    return sorted_values[index]


def _numeric_summary(values: Iterable[Any], *, digits: int = 3) -> dict[str, Any]:
    seq = _numeric_values(values)
    if not seq:
        return {"n": 0, "avg": None, "p50": None, "p90": None, "p95": None, "max": None}
    ordered = tuple(sorted(seq))
    return {
        "n": len(seq),
        "avg": round(sum(seq) / len(seq), digits),
        "p50": round(_percentile(ordered, 0.5), digits),
        "p90": round(_percentile(ordered, 0.9), digits),
        "p95": round(_percentile(ordered, 0.95), digits),
        "max": round(max(seq), digits),
    }


def _counter_dict(values: Iterable[Any], *, top: int = 8) -> dict[str, int]:
    counts: Counter[str] = Counter(
        str(value) if value not in (None, "") else "none"
        for value in values
    )
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top])


def _int_list_from_json_blob(blob: Any) -> tuple[int, ...]:
    if not isinstance(blob, str) or blob in ("", "[]", "[[]]"):
        return ()
    try:
        parsed = json.loads(blob)
    except (TypeError, ValueError):
        return ()
    if not isinstance(parsed, list):
        return ()
    out: list[int] = []
    for value in parsed:
        if isinstance(value, bool):
            continue
        try:
            out.append(int(value))
        except (TypeError, ValueError):
            continue
    return tuple(out)


def _bidmap_drop_ref_column_index(raw_column_count: int) -> int:
    return 17 if raw_column_count == 23 else 16


def _bidmap_round_cap_column_index(raw_column_count: int) -> int:
    return 14 if raw_column_count == 23 else 13


def _bidmap_round_caps(bid_map: Any) -> tuple[int, ...]:
    raw_row = tuple(getattr(bid_map, "raw_row", ()) or ())
    if not raw_row:
        return ()
    index = _bidmap_round_cap_column_index(len(raw_row))
    return _int_list_from_json_blob(raw_row[index] if len(raw_row) > index else None)


def _resolve_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    seq = tuple(paths)
    if not seq:
        seq = (DEFAULT_SAMPLE_ROOT,)
    out: list[Path] = []
    for path in seq:
        if path.is_dir():
            out.extend(path.rglob("*.json"))
        elif path.exists():
            out.append(path)
    return tuple(sorted(set(out)))


def _table_caps_for_map(map_id: int | None, tables: Any) -> dict[str, Any]:
    if map_id is None:
        return {
            "table_status": "missing_map_id",
            "map_name": None,
            "drop_pool_id": None,
            "bidmap_items_per_session_min": None,
            "bidmap_items_per_session_max": None,
            "bidmap_raw_column_count": None,
            "bidmap_drop_ref_column_index": None,
            "bidmap_raw_drop_ref": None,
            "bidmap_raw_round_cap_min": None,
            "bidmap_raw_round_cap_max": None,
        }
    bid_map = tables.maps.get(int(map_id))
    if bid_map is None:
        return {
            "table_status": "missing_bidmap",
            "map_name": None,
            "drop_pool_id": None,
            "bidmap_items_per_session_min": None,
            "bidmap_items_per_session_max": None,
            "bidmap_raw_column_count": None,
            "bidmap_drop_ref_column_index": None,
            "bidmap_raw_drop_ref": None,
            "bidmap_raw_round_cap_min": None,
            "bidmap_raw_round_cap_max": None,
        }
    raw_row = tuple(getattr(bid_map, "raw_row", ()) or ())
    raw_column_count = len(raw_row)
    drop_ref_index = _bidmap_drop_ref_column_index(raw_column_count)
    round_caps = _bidmap_round_caps(bid_map)
    return {
        "table_status": "ok",
        "map_name": getattr(bid_map, "name", None),
        "drop_pool_id": getattr(bid_map, "drop_pool_id", None),
        "bidmap_items_per_session_min": getattr(bid_map, "items_per_session_min", None),
        "bidmap_items_per_session_max": getattr(bid_map, "items_per_session_max", None),
        "bidmap_raw_column_count": raw_column_count,
        "bidmap_drop_ref_column_index": drop_ref_index,
        "bidmap_raw_drop_ref": raw_row[drop_ref_index] if len(raw_row) > drop_ref_index else None,
        "bidmap_raw_round_cap_min": min(round_caps) if round_caps else None,
        "bidmap_raw_round_cap_max": max(round_caps) if round_caps else None,
    }


def _latest_settlement_state(events: Any) -> Any | None:
    states = [
        state
        for state in tuple(getattr(events, "states", ()) or ())
        if getattr(state, "message_id", None) == 0x002D
        or tuple(getattr(state, "inventory_items", ()) or ())
    ]
    return states[-1] if states else None


def _audit_file(path: Path, *, tables: Any) -> dict[str, Any]:
    events = parse_fatbeans_capture(path)
    state = _latest_settlement_state(events)
    if state is None:
        return {"file": path.name, "path": str(path), "status": "no_settlement_state"}

    items = tuple(getattr(state, "inventory_items", ()) or ())
    item_ids = tuple(_safe_int(getattr(item, "item_id", None)) for item in items)
    inventory_count = len(items)
    known_temp_zodiac_count = sum(
        1 for item_id in item_ids if item_id in _TEMPORARY_BLUE_ZODIAC_ITEM_IDS
    )
    non_temp_inventory_count = inventory_count - known_temp_zodiac_count
    map_id = _safe_int(getattr(state, "map_id", None))
    table = _table_caps_for_map(map_id, tables)
    drop_ref_max = _safe_int(table.get("bidmap_items_per_session_max"))
    round_cap_max = _safe_int(table.get("bidmap_raw_round_cap_max"))

    payload, loss_units, frame_meta = _latest_settlement_payload(path)
    payload_fields = _parse_fields(payload) if isinstance(payload, bytes) else []
    inventory_block = _first(payload_fields, 4) if payload_fields else None
    inventory_metrics = _inventory_block_metrics(inventory_block)
    occupied_slot_count = inventory_metrics["occupied_slot_count"]
    raw_candidate_count = inventory_metrics["raw_item_candidate_count"]
    action_observed_counts = [
        (
            _safe_int(getattr(action, "action_id", None)),
            len(tuple(getattr(action, "observed_items", ()) or ())),
        )
        for action in tuple(getattr(state, "action_results", ()) or ())
    ]
    full_observed_action_ids = [
        action_id
        for action_id, observed_count in action_observed_counts
        if action_id is not None and inventory_count > 0 and observed_count == inventory_count
    ]
    public_total_count_values = [
        getattr(info, "value", None)
        for info in tuple(getattr(state, "public_infos", ()) or ())
        if getattr(info, "info_id", None) == 200017
    ]

    return {
        "file": path.name,
        "path": str(path),
        "status": "ok",
        "map_id": map_id,
        "map_prefix3": int(map_id) // 10 if map_id is not None else None,
        "map_family": _map_family(map_id),
        "round_index": getattr(state, "round_index", None),
        "message_id": getattr(state, "message_id", None),
        "inventory_count": inventory_count,
        "non_temp_inventory_count": non_temp_inventory_count,
        "known_temp_zodiac_count": known_temp_zodiac_count,
        "inventory_cells": sum(
            _safe_int(getattr(item, "cells", None)) or 0
            for item in items
        ),
        "settlement_loss_units": loss_units,
        "action_result_count": len(action_observed_counts),
        "action_observed_item_count_max": (
            max((count for _action_id, count in action_observed_counts), default=0)
        ),
        "full_observed_action_ids": full_observed_action_ids,
        "public_total_count_values": public_total_count_values,
        "raw_candidate_inventory_delta": (
            raw_candidate_count - inventory_count
            if raw_candidate_count is not None
            else None
        ),
        "occupied_slot_inventory_delta": (
            occupied_slot_count - inventory_count
            if occupied_slot_count is not None
            else None
        ),
        "drop_ref_excess_item_count": (
            max(0, inventory_count - drop_ref_max)
            if drop_ref_max is not None
            else None
        ),
        "drop_ref_excess_after_temp_zodiac_count": (
            max(0, non_temp_inventory_count - drop_ref_max)
            if drop_ref_max is not None
            else None
        ),
        "round_cap_excess_item_count": (
            max(0, inventory_count - round_cap_max)
            if round_cap_max is not None
            else None
        ),
        "round_cap_excess_after_temp_zodiac_count": (
            max(0, non_temp_inventory_count - round_cap_max)
            if round_cap_max is not None
            else None
        ),
        **frame_meta,
        **inventory_metrics,
        **table,
    }


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


def _group_key(row: Mapping[str, Any], group_by: str) -> str:
    value = row.get(group_by)
    return str(value) if value not in (None, "") else "none"


def _positive_rows(rows: Iterable[Mapping[str, Any]], field: str) -> int:
    count = 0
    for row in rows:
        value = _safe_int(row.get(field))
        if value is not None and value > 0:
            count += 1
    return count


def _residual_mode(row: Mapping[str, Any]) -> str:
    round_after = _safe_int(row.get("round_cap_excess_after_temp_zodiac_count"))
    drop_after = _safe_int(row.get("drop_ref_excess_after_temp_zodiac_count"))
    if round_after is not None and round_after > 0:
        return "round_cap_overflow_after_temp"
    if drop_after is not None and drop_after > 0:
        return "drop_ref_only_overflow_after_temp"
    if _safe_int(row.get("drop_ref_excess_item_count")):
        return "activity_extras_only_drop_ref_gap"
    return "within_drop_ref_after_temp"


def _candidate_status(rows: tuple[Mapping[str, Any], ...], *, min_samples: int) -> str:
    if any(row.get("table_status") in ("missing_map_id", "missing_bidmap") for row in rows):
        return "missing_table_shadow_only"
    if len(rows) < min_samples:
        return "insufficient_samples_shadow_only"
    if (
        _positive_rows(rows, "drop_ref_excess_after_temp_zodiac_count")
        or _positive_rows(rows, "round_cap_excess_after_temp_zodiac_count")
    ):
        return "observed_exceeds_table_caps_shadow_only"
    return "table_caps_cover_observed_shadow_only"


def _examples(rows: Iterable[Mapping[str, Any]], *, top: int) -> list[str]:
    return [
        str(row.get("file"))
        for row in sorted(
            rows,
            key=lambda item: (
                -int(item.get("inventory_count") or 0),
                str(item.get("file") or ""),
            ),
        )[:top]
    ]


def _public_total_deltas(rows: Iterable[Mapping[str, Any]]) -> tuple[int, ...]:
    out: list[int] = []
    for row in rows:
        inventory_count = _safe_int(row.get("inventory_count"))
        if inventory_count is None:
            continue
        for value in tuple(row.get("public_total_count_values", ()) or ()):
            parsed = _safe_int(value)
            if parsed is not None:
                out.append(parsed - inventory_count)
    return tuple(out)


def _public_total_match_rows(rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    for row in rows:
        inventory_count = _safe_int(row.get("inventory_count"))
        values = tuple(row.get("public_total_count_values", ()) or ())
        if inventory_count is not None and any(
            _safe_int(value) == inventory_count for value in values
        ):
            count += 1
    return count


def summarize_settlement_count_prior_candidates(
    paths: Iterable[Path] = (),
    *,
    tables: Any | None = None,
    group_by: str = "map_id",
    min_samples: int = 10,
    top: int = 12,
) -> dict[str, Any]:
    if group_by not in {"map_id", "map_prefix3", "map_family", "residual_mode"}:
        raise ValueError(f"unsupported group_by: {group_by}")
    tables = tables or load_monitor_tables()
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in _resolve_paths(paths):
        try:
            rows.append(_audit_file(path, tables=tables))
        except Exception as exc:  # pragma: no cover - retained for CLI diagnostics.
            errors.append(f"{path}:{type(exc).__name__}:{exc}")

    ready = [row for row in rows if row.get("status") == "ok"]
    for row in ready:
        row["residual_mode"] = _residual_mode(row)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ready:
        groups[_group_key(row, group_by)].append(row)

    group_rows: list[dict[str, Any]] = []
    for key, seq_list in groups.items():
        seq = tuple(seq_list)
        group_rows.append(
            {
                "group_by": group_by,
                "group": key,
                "files": len(seq),
                "candidate_status": _candidate_status(seq, min_samples=min_samples),
                "map_ids": _counter_dict((row.get("map_id") for row in seq), top=top),
                "map_families": _counter_dict((row.get("map_family") for row in seq), top=top),
                "residual_modes": _counter_dict((row.get("residual_mode") for row in seq), top=top),
                "table_statuses": _counter_dict((row.get("table_status") for row in seq), top=top),
                "bidmap_items_per_session_max": _numeric_summary(
                    row.get("bidmap_items_per_session_max") for row in seq
                ),
                "bidmap_raw_round_cap_max": _numeric_summary(
                    row.get("bidmap_raw_round_cap_max") for row in seq
                ),
                "inventory_count": _numeric_summary(row.get("inventory_count") for row in seq),
                "non_temp_inventory_count": _numeric_summary(
                    row.get("non_temp_inventory_count") for row in seq
                ),
                "known_temp_zodiac_count": _numeric_summary(
                    row.get("known_temp_zodiac_count") for row in seq
                ),
                "inventory_cells": _numeric_summary(row.get("inventory_cells") for row in seq),
                "inventory_slot_count": _counter_dict(
                    (row.get("inventory_slot_count") for row in seq),
                    top=top,
                ),
                "inventory_slot_headroom_after_temp_zodiac": _numeric_summary(
                    (
                        (
                            _safe_int(row.get("inventory_slot_count"))
                            - _safe_int(row.get("non_temp_inventory_count"))
                        )
                        if _safe_int(row.get("inventory_slot_count")) is not None
                        and _safe_int(row.get("non_temp_inventory_count")) is not None
                        else None
                    )
                    for row in seq
                ),
                "raw_candidate_inventory_delta": _numeric_summary(
                    row.get("raw_candidate_inventory_delta") for row in seq
                ),
                "occupied_slot_inventory_delta": _numeric_summary(
                    row.get("occupied_slot_inventory_delta") for row in seq
                ),
                "drop_ref_excess_item_count": _numeric_summary(
                    row.get("drop_ref_excess_item_count") for row in seq
                ),
                "drop_ref_excess_after_temp_zodiac_count": _numeric_summary(
                    row.get("drop_ref_excess_after_temp_zodiac_count") for row in seq
                ),
                "round_cap_excess_item_count": _numeric_summary(
                    row.get("round_cap_excess_item_count") for row in seq
                ),
                "round_cap_excess_after_temp_zodiac_count": _numeric_summary(
                    row.get("round_cap_excess_after_temp_zodiac_count") for row in seq
                ),
                "above_drop_ref_rows": _positive_rows(seq, "drop_ref_excess_item_count"),
                "above_drop_ref_after_temp_zodiac_rows": _positive_rows(
                    seq,
                    "drop_ref_excess_after_temp_zodiac_count",
                ),
                "above_round_cap_rows": _positive_rows(seq, "round_cap_excess_item_count"),
                "above_round_cap_after_temp_zodiac_rows": _positive_rows(
                    seq,
                    "round_cap_excess_after_temp_zodiac_count",
                ),
                "payload_inventory_mismatch_rows": sum(
                    1
                    for row in seq
                    if (
                        row.get("raw_candidate_inventory_delta") not in (0, None)
                        or row.get("occupied_slot_inventory_delta") not in (0, None)
                    )
                ),
                "full_observed_action_rows": sum(
                    1 for row in seq if row.get("full_observed_action_ids")
                ),
                "public_total_rows": sum(
                    1 for row in seq if row.get("public_total_count_values")
                ),
                "public_total_match_rows": _public_total_match_rows(seq),
                "public_total_inventory_delta": _numeric_summary(
                    _public_total_deltas(seq)
                ),
                "examples": _examples(seq, top=3),
            }
        )

    group_rows = sorted(
        group_rows,
        key=lambda row: (
            0
            if row["candidate_status"] == "observed_exceeds_table_caps_shadow_only"
            else 1,
            -int(row["above_drop_ref_after_temp_zodiac_rows"]),
            -int(row["above_round_cap_after_temp_zodiac_rows"]),
            -float(row["inventory_count"]["max"] or 0.0),
            str(row["group"]),
        ),
    )
    status_counts = Counter(row["candidate_status"] for row in group_rows)
    return {
        "errors": errors,
        "files": len(rows),
        "settlement_rows": len(ready),
        "group_by": group_by,
        "min_samples": min_samples,
        "overall": {
            "inventory_count": _numeric_summary(row.get("inventory_count") for row in ready),
            "non_temp_inventory_count": _numeric_summary(
                row.get("non_temp_inventory_count") for row in ready
            ),
            "known_temp_zodiac_count": _numeric_summary(
                row.get("known_temp_zodiac_count") for row in ready
            ),
            "inventory_slot_count": _counter_dict(
                (row.get("inventory_slot_count") for row in ready),
                top=top,
            ),
            "inventory_slot_headroom_after_temp_zodiac": _numeric_summary(
                (
                    (
                        _safe_int(row.get("inventory_slot_count"))
                        - _safe_int(row.get("non_temp_inventory_count"))
                    )
                    if _safe_int(row.get("inventory_slot_count")) is not None
                    and _safe_int(row.get("non_temp_inventory_count")) is not None
                    else None
                )
                for row in ready
            ),
            "residual_modes": _counter_dict(
                (row.get("residual_mode") for row in ready),
                top=top,
            ),
            "above_drop_ref_rows": _positive_rows(ready, "drop_ref_excess_item_count"),
            "above_drop_ref_after_temp_zodiac_rows": _positive_rows(
                ready,
                "drop_ref_excess_after_temp_zodiac_count",
            ),
            "above_round_cap_rows": _positive_rows(ready, "round_cap_excess_item_count"),
            "above_round_cap_after_temp_zodiac_rows": _positive_rows(
                ready,
                "round_cap_excess_after_temp_zodiac_count",
            ),
            "missing_table_rows": sum(
                1
                for row in ready
                if row.get("table_status") in ("missing_map_id", "missing_bidmap")
            ),
            "payload_inventory_mismatch_rows": sum(
                1
                for row in ready
                if (
                    row.get("raw_candidate_inventory_delta") not in (0, None)
                    or row.get("occupied_slot_inventory_delta") not in (0, None)
                )
            ),
            "candidate_statuses": dict(
                sorted(status_counts.items(), key=lambda item: (-item[1], item[0]))
            ),
            "full_observed_action_rows": sum(
                1 for row in ready if row.get("full_observed_action_ids")
            ),
            "public_total_rows": sum(
                1 for row in ready if row.get("public_total_count_values")
            ),
            "public_total_match_rows": _public_total_match_rows(ready),
            "public_total_inventory_delta": _numeric_summary(
                _public_total_deltas(ready)
            ),
        },
        "rows": group_rows,
    }


def _format_counts(counts: Mapping[str, int]) -> str:
    return ",".join(f"{key}:{value}" for key, value in counts.items()) or "-"


def _format_summary(summary: Mapping[str, Any]) -> str:
    return (
        f"n={summary['n']}"
        f"/avg={summary['avg']}"
        f"/p50={summary['p50']}"
        f"/p90={summary['p90']}"
        f"/p95={summary['p95']}"
        f"/max={summary['max']}"
    )


def _print_summary(result: Mapping[str, Any], *, top: int) -> None:
    overall = result["overall"]
    print(
        " ".join(
            (
                f"files={result['files']}",
                f"settlement_rows={result['settlement_rows']}",
                f"group_by={result['group_by']}",
                f"groups={len(result['rows'])}",
                f"min_samples={result['min_samples']}",
                f"inventory_count={_format_summary(overall['inventory_count'])}",
                f"non_temp_count={_format_summary(overall['non_temp_inventory_count'])}",
                f"temp_zodiac={_format_summary(overall['known_temp_zodiac_count'])}",
                f"slot_counts={_format_counts(overall['inventory_slot_count'])}",
                f"slot_headroom_after_temp={_format_summary(overall['inventory_slot_headroom_after_temp_zodiac'])}",
                f"residual_modes={_format_counts(overall['residual_modes'])}",
                f"above_drop={overall['above_drop_ref_rows']}",
                f"above_drop_after_temp={overall['above_drop_ref_after_temp_zodiac_rows']}",
                f"above_round={overall['above_round_cap_rows']}",
                f"above_round_after_temp={overall['above_round_cap_after_temp_zodiac_rows']}",
                f"missing_table_rows={overall['missing_table_rows']}",
                f"payload_mismatch_rows={overall['payload_inventory_mismatch_rows']}",
                f"candidate_statuses={_format_counts(overall['candidate_statuses'])}",
                f"full_action_rows={overall['full_observed_action_rows']}",
                f"public_total_rows={overall['public_total_rows']}",
                f"public_total_match_rows={overall['public_total_match_rows']}",
                f"public_total_delta={_format_summary(overall['public_total_inventory_delta'])}",
            )
        )
    )
    for row in result["rows"][:top]:
        print(
            " ".join(
                (
                    f"{row['group_by']}={row['group']}",
                    f"status={row['candidate_status']}",
                    f"files={row['files']}",
                    f"maps={_format_counts(row['map_ids'])}",
                    f"families={_format_counts(row['map_families'])}",
                    f"residual_modes={_format_counts(row['residual_modes'])}",
                    f"table={_format_counts(row['table_statuses'])}",
                    f"bidmap_max={_format_summary(row['bidmap_items_per_session_max'])}",
                    f"round_cap={_format_summary(row['bidmap_raw_round_cap_max'])}",
                    f"inventory_count={_format_summary(row['inventory_count'])}",
                    f"non_temp_count={_format_summary(row['non_temp_inventory_count'])}",
                    f"temp_zodiac={_format_summary(row['known_temp_zodiac_count'])}",
                    f"cells={_format_summary(row['inventory_cells'])}",
                    f"slots={_format_counts(row['inventory_slot_count'])}",
                    f"slot_headroom_after_temp={_format_summary(row['inventory_slot_headroom_after_temp_zodiac'])}",
                    f"drop_excess_after_temp={_format_summary(row['drop_ref_excess_after_temp_zodiac_count'])}",
                    f"round_excess_after_temp={_format_summary(row['round_cap_excess_after_temp_zodiac_count'])}",
                    f"above_drop_after_temp={row['above_drop_ref_after_temp_zodiac_rows']}/{row['files']}",
                    f"above_round_after_temp={row['above_round_cap_after_temp_zodiac_rows']}/{row['files']}",
                    f"raw_candidate_delta={_format_summary(row['raw_candidate_inventory_delta'])}",
                    f"occupied_delta={_format_summary(row['occupied_slot_inventory_delta'])}",
                    f"payload_mismatch={row['payload_inventory_mismatch_rows']}/{row['files']}",
                    f"full_action_rows={row['full_observed_action_rows']}/{row['files']}",
                    f"public_total_rows={row['public_total_rows']}/{row['files']}",
                    f"public_total_match_rows={row['public_total_match_rows']}/{row['files']}",
                    f"public_total_delta={_format_summary(row['public_total_inventory_delta'])}",
                    f"examples={','.join(row['examples'])}",
                )
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit shadow-only settlement occupancy count prior candidates.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument(
        "--group-by",
        choices=("map_id", "map_prefix3", "map_family", "residual_mode"),
        default="map_id",
    )
    parser.add_argument("--min-samples", type=int, default=10)
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args(argv)

    result = summarize_settlement_count_prior_candidates(
        args.paths,
        group_by=args.group_by,
        min_samples=args.min_samples,
        top=args.top,
    )
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if result["errors"]:
            print(f"errors={len(result['errors'])}")
        _print_summary(result, top=args.top)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
