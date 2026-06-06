"""Audit shadow-only settlement occupancy count prior candidates."""

from __future__ import annotations

import argparse
import json
import re
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
    _field_signature,
    _inventory_block_metrics,
    _latest_settlement_payload,
    _payload_field_counts,
)


DEFAULT_SAMPLE_ROOT = ROOT / "data" / "samples" / "fatbeans"
_TEMPORARY_BLUE_ZODIAC_ITEM_IDS = frozenset(range(1306003, 1306015))
_CAPTURE_ROUNDS_RE = re.compile(r"_(\d+)rounds(?:_|$)")
_DATE_TOKEN_RE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")
_SESSION_TOKEN_RE = re.compile(r"_(\d{12,})(?=_|\.)")


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


def _payload_count(field_counts: Mapping[str, int], field_no: int) -> int:
    return sum(
        int(count)
        for key, count in field_counts.items()
        if key.split(":", 1)[0] == str(field_no)
    )


def _payload_shape(field_counts: Mapping[str, int]) -> str:
    if not field_counts:
        return "none"

    def sort_key(item: tuple[str, int]) -> tuple[int, int]:
        field_text, _, wire_text = item[0].partition(":")
        return (_safe_int(field_text) or 0, _safe_int(wire_text) or 0)

    return ",".join(
        f"{key}x{count}" for key, count in sorted(field_counts.items(), key=sort_key)
    )


def _payload_child_signatures(
    payload_fields: Iterable[tuple[int, int, Any]],
    field_no: int,
    *,
    top: int = 8,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item_field_no, _wire_type, value in payload_fields:
        if item_field_no != field_no or not isinstance(value, bytes):
            continue
        counts[_field_signature(_parse_fields(value))] += 1
    return dict(counts.most_common(top))


def _payload_int_values(
    payload_fields: Iterable[tuple[int, int, Any]],
    field_no: int,
) -> tuple[int, ...]:
    return tuple(
        int(value)
        for item_field_no, _wire_type, value in payload_fields
        if item_field_no == field_no and isinstance(value, int)
    )


def _merge_count_mappings(
    mappings: Iterable[Mapping[str, int]],
    *,
    top: int = 8,
) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for mapping in mappings:
        counts.update({str(key): int(value) for key, value in mapping.items()})
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


def _capture_rounds_from_name(path: Path) -> int | None:
    match = _CAPTURE_ROUNDS_RE.search(path.name)
    return _safe_int(match.group(1)) if match else None


def _capture_day_from_state_or_path(state: Any, path: Path) -> str | None:
    for raw in (
        getattr(state, "capture_time", None),
        str(path),
    ):
        if raw in (None, ""):
            continue
        match = _DATE_TOKEN_RE.search(str(raw))
        if match is not None:
            return "".join(match.groups())
    return None


def _session_token_from_state_or_path(state: Any, path: Path) -> str | None:
    session_id = str(getattr(state, "session_id", "") or "")
    if ":" in session_id:
        token = session_id.rsplit(":", 1)[1]
        if token.isdigit():
            return token
    match = _SESSION_TOKEN_RE.search(path.name)
    return match.group(1) if match is not None else None


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
            "bidmap_rounds_total": None,
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
            "bidmap_rounds_total": None,
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
        "bidmap_rounds_total": getattr(bid_map, "rounds_total", None),
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
    capture_day = _capture_day_from_state_or_path(state, path)
    session_token = _session_token_from_state_or_path(state, path)
    table = _table_caps_for_map(map_id, tables)
    drop_ref_max = _safe_int(table.get("bidmap_items_per_session_max"))
    round_cap_max = _safe_int(table.get("bidmap_raw_round_cap_max"))

    payload, loss_units, frame_meta = _latest_settlement_payload(path)
    payload_fields = _parse_fields(payload) if isinstance(payload, bytes) else []
    payload_field_counts = _payload_field_counts(payload)
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
        "capture_rounds": _capture_rounds_from_name(path),
        "capture_day": capture_day,
        "session_token_prefix6": (
            session_token[:6] if session_token is not None and len(session_token) >= 6 else None
        ),
        "session_token_prefix8": (
            session_token[:8] if session_token is not None and len(session_token) >= 8 else None
        ),
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
        "payload_field_shape": _payload_shape(payload_field_counts),
        "payload_field5_count": _payload_count(payload_field_counts, 5),
        "payload_field6_count": _payload_count(payload_field_counts, 6),
        "payload_field7_count": _payload_count(payload_field_counts, 7),
        "payload_field8_count": _payload_count(payload_field_counts, 8),
        "payload_field20_present": _payload_count(payload_field_counts, 20) > 0,
        "payload_field5_child_signatures": _payload_child_signatures(payload_fields, 5),
        "payload_field6_child_signatures": _payload_child_signatures(payload_fields, 6),
        "payload_field7_child_signatures": _payload_child_signatures(payload_fields, 7),
        "payload_field8_child_signatures": _payload_child_signatures(payload_fields, 8),
        "payload_field20_values": _payload_int_values(payload_fields, 20),
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
    if group_by not in {
        "map_id",
        "map_prefix3",
        "map_family",
        "residual_mode",
        "round_index",
        "capture_rounds",
        "capture_day",
        "session_token_prefix6",
        "session_token_prefix8",
        "bidmap_rounds_total",
    }:
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
                "round_indices": _counter_dict((row.get("round_index") for row in seq), top=top),
                "capture_rounds": _counter_dict((row.get("capture_rounds") for row in seq), top=top),
                "capture_days": _counter_dict((row.get("capture_day") for row in seq), top=top),
                "session_token_prefix6_counts": _counter_dict(
                    (row.get("session_token_prefix6") for row in seq),
                    top=top,
                ),
                "session_token_prefix8_counts": _counter_dict(
                    (row.get("session_token_prefix8") for row in seq),
                    top=top,
                ),
                "bidmap_rounds_total_counts": _counter_dict(
                    (row.get("bidmap_rounds_total") for row in seq),
                    top=top,
                ),
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
                "settlement_outer_field_shapes": _counter_dict(
                    (row.get("settlement_outer_field_shape") for row in seq),
                    top=top,
                ),
                "settlement_outer_field3_present_rows": sum(
                    1 for row in seq if row.get("settlement_outer_field3_present")
                ),
                "settlement_outer_field4_present_rows": sum(
                    1 for row in seq if row.get("settlement_outer_field4_present")
                ),
                "settlement_outer_field5_present_rows": sum(
                    1 for row in seq if row.get("settlement_outer_field5_present")
                ),
                "settlement_outer_field6_count": _numeric_summary(
                    row.get("settlement_outer_field6_count") for row in seq
                ),
                "occupied_slot_field_shapes": _merge_count_mappings(
                    (row.get("occupied_slot_field_shapes", {}) for row in seq),
                    top=top,
                ),
                "empty_slot_field_shapes": _merge_count_mappings(
                    (row.get("empty_slot_field_shapes", {}) for row in seq),
                    top=top,
                ),
                "occupied_slot_int_field_counts": _merge_count_mappings(
                    (row.get("occupied_slot_int_field_counts", {}) for row in seq),
                    top=top,
                ),
                "empty_slot_int_field_counts": _merge_count_mappings(
                    (row.get("empty_slot_int_field_counts", {}) for row in seq),
                    top=top,
                ),
                "candidate_path_counts": _merge_count_mappings(
                    (row.get("candidate_path_counts", {}) for row in seq),
                    top=top,
                ),
                "payload_field_shapes": _counter_dict(
                    (row.get("payload_field_shape") for row in seq),
                    top=top,
                ),
                "payload_field5_count": _numeric_summary(
                    row.get("payload_field5_count") for row in seq
                ),
                "payload_field6_count": _numeric_summary(
                    row.get("payload_field6_count") for row in seq
                ),
                "payload_field7_count": _numeric_summary(
                    row.get("payload_field7_count") for row in seq
                ),
                "payload_field8_count": _numeric_summary(
                    row.get("payload_field8_count") for row in seq
                ),
                "payload_field20_present_rows": sum(
                    1 for row in seq if row.get("payload_field20_present")
                ),
                "payload_field20_values": _counter_dict(
                    (
                        value
                        for row in seq
                        for value in tuple(row.get("payload_field20_values", ()) or ())
                    ),
                    top=top,
                ),
                "payload_field5_child_signatures": _merge_count_mappings(
                    (row.get("payload_field5_child_signatures", {}) for row in seq),
                    top=top,
                ),
                "payload_field6_child_signatures": _merge_count_mappings(
                    (row.get("payload_field6_child_signatures", {}) for row in seq),
                    top=top,
                ),
                "payload_field7_child_signatures": _merge_count_mappings(
                    (row.get("payload_field7_child_signatures", {}) for row in seq),
                    top=top,
                ),
                "payload_field8_child_signatures": _merge_count_mappings(
                    (row.get("payload_field8_child_signatures", {}) for row in seq),
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
            "capture_days": _counter_dict((row.get("capture_day") for row in ready), top=top),
            "session_token_prefix6_counts": _counter_dict(
                (row.get("session_token_prefix6") for row in ready),
                top=top,
            ),
            "session_token_prefix8_counts": _counter_dict(
                (row.get("session_token_prefix8") for row in ready),
                top=top,
            ),
            "inventory_slot_count": _counter_dict(
                (row.get("inventory_slot_count") for row in ready),
                top=top,
            ),
            "settlement_outer_field_shapes": _counter_dict(
                (row.get("settlement_outer_field_shape") for row in ready),
                top=top,
            ),
            "settlement_outer_field3_present_rows": sum(
                1 for row in ready if row.get("settlement_outer_field3_present")
            ),
            "settlement_outer_field4_present_rows": sum(
                1 for row in ready if row.get("settlement_outer_field4_present")
            ),
            "settlement_outer_field5_present_rows": sum(
                1 for row in ready if row.get("settlement_outer_field5_present")
            ),
            "settlement_outer_field6_count": _numeric_summary(
                row.get("settlement_outer_field6_count") for row in ready
            ),
            "occupied_slot_field_shapes": _merge_count_mappings(
                (row.get("occupied_slot_field_shapes", {}) for row in ready),
                top=top,
            ),
            "empty_slot_field_shapes": _merge_count_mappings(
                (row.get("empty_slot_field_shapes", {}) for row in ready),
                top=top,
            ),
            "occupied_slot_int_field_counts": _merge_count_mappings(
                (row.get("occupied_slot_int_field_counts", {}) for row in ready),
                top=top,
            ),
            "empty_slot_int_field_counts": _merge_count_mappings(
                (row.get("empty_slot_int_field_counts", {}) for row in ready),
                top=top,
            ),
            "candidate_path_counts": _merge_count_mappings(
                (row.get("candidate_path_counts", {}) for row in ready),
                top=top,
            ),
            "payload_field_shapes": _counter_dict(
                (row.get("payload_field_shape") for row in ready),
                top=top,
            ),
            "payload_field5_count": _numeric_summary(
                row.get("payload_field5_count") for row in ready
            ),
            "payload_field6_count": _numeric_summary(
                row.get("payload_field6_count") for row in ready
            ),
            "payload_field7_count": _numeric_summary(
                row.get("payload_field7_count") for row in ready
            ),
            "payload_field8_count": _numeric_summary(
                row.get("payload_field8_count") for row in ready
            ),
            "payload_field20_present_rows": sum(
                1 for row in ready if row.get("payload_field20_present")
            ),
            "payload_field20_values": _counter_dict(
                (
                    value
                    for row in ready
                    for value in tuple(row.get("payload_field20_values", ()) or ())
                ),
                top=top,
            ),
            "payload_field5_child_signatures": _merge_count_mappings(
                (row.get("payload_field5_child_signatures", {}) for row in ready),
                top=top,
            ),
            "payload_field6_child_signatures": _merge_count_mappings(
                (row.get("payload_field6_child_signatures", {}) for row in ready),
                top=top,
            ),
            "payload_field7_child_signatures": _merge_count_mappings(
                (row.get("payload_field7_child_signatures", {}) for row in ready),
                top=top,
            ),
            "payload_field8_child_signatures": _merge_count_mappings(
                (row.get("payload_field8_child_signatures", {}) for row in ready),
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
            "round_indices": _counter_dict(
                (row.get("round_index") for row in ready),
                top=top,
            ),
            "capture_rounds": _counter_dict(
                (row.get("capture_rounds") for row in ready),
                top=top,
            ),
            "bidmap_rounds_total_counts": _counter_dict(
                (row.get("bidmap_rounds_total") for row in ready),
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
                f"capture_days={_format_counts(overall['capture_days'])}",
                f"session_p6={_format_counts(overall['session_token_prefix6_counts'])}",
                f"slot_counts={_format_counts(overall['inventory_slot_count'])}",
                f"outer_shapes={_format_counts(overall['settlement_outer_field_shapes'])}",
                f"outer_f3_rows={overall['settlement_outer_field3_present_rows']}",
                f"outer_f4_rows={overall['settlement_outer_field4_present_rows']}",
                f"outer_f5_rows={overall['settlement_outer_field5_present_rows']}",
                f"outer_f6={_format_summary(overall['settlement_outer_field6_count'])}",
                f"occupied_slot_shapes={_format_counts(overall['occupied_slot_field_shapes'])}",
                f"empty_slot_shapes={_format_counts(overall['empty_slot_field_shapes'])}",
                f"occupied_slot_int_fields={_format_counts(overall['occupied_slot_int_field_counts'])}",
                f"empty_slot_int_fields={_format_counts(overall['empty_slot_int_field_counts'])}",
                f"candidate_paths={_format_counts(overall['candidate_path_counts'])}",
                f"payload_shapes={_format_counts(overall['payload_field_shapes'])}",
                f"payload_f5={_format_summary(overall['payload_field5_count'])}",
                f"payload_f6={_format_summary(overall['payload_field6_count'])}",
                f"payload_f7={_format_summary(overall['payload_field7_count'])}",
                f"payload_f8={_format_summary(overall['payload_field8_count'])}",
                f"payload_f20_rows={overall['payload_field20_present_rows']}",
                f"payload_f20_values={_format_counts(overall['payload_field20_values'])}",
                f"payload_f5_child={_format_counts(overall['payload_field5_child_signatures'])}",
                f"payload_f8_child={_format_counts(overall['payload_field8_child_signatures'])}",
                f"slot_headroom_after_temp={_format_summary(overall['inventory_slot_headroom_after_temp_zodiac'])}",
                f"residual_modes={_format_counts(overall['residual_modes'])}",
                f"round_indices={_format_counts(overall['round_indices'])}",
                f"capture_rounds={_format_counts(overall['capture_rounds'])}",
                f"bidmap_rounds_total={_format_counts(overall['bidmap_rounds_total_counts'])}",
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
                    f"round_indices={_format_counts(row['round_indices'])}",
                    f"capture_rounds={_format_counts(row['capture_rounds'])}",
                    f"capture_days={_format_counts(row['capture_days'])}",
                    f"session_p6={_format_counts(row['session_token_prefix6_counts'])}",
                    f"bidmap_rounds_total={_format_counts(row['bidmap_rounds_total_counts'])}",
                    f"residual_modes={_format_counts(row['residual_modes'])}",
                    f"table={_format_counts(row['table_statuses'])}",
                    f"bidmap_max={_format_summary(row['bidmap_items_per_session_max'])}",
                    f"round_cap={_format_summary(row['bidmap_raw_round_cap_max'])}",
                    f"inventory_count={_format_summary(row['inventory_count'])}",
                    f"non_temp_count={_format_summary(row['non_temp_inventory_count'])}",
                    f"temp_zodiac={_format_summary(row['known_temp_zodiac_count'])}",
                    f"cells={_format_summary(row['inventory_cells'])}",
                    f"slots={_format_counts(row['inventory_slot_count'])}",
                    f"outer_shapes={_format_counts(row['settlement_outer_field_shapes'])}",
                    f"outer_f3_rows={row['settlement_outer_field3_present_rows']}/{row['files']}",
                    f"outer_f4_rows={row['settlement_outer_field4_present_rows']}/{row['files']}",
                    f"outer_f5_rows={row['settlement_outer_field5_present_rows']}/{row['files']}",
                    f"outer_f6={_format_summary(row['settlement_outer_field6_count'])}",
                    f"occupied_slot_shapes={_format_counts(row['occupied_slot_field_shapes'])}",
                    f"empty_slot_shapes={_format_counts(row['empty_slot_field_shapes'])}",
                    f"occupied_slot_int_fields={_format_counts(row['occupied_slot_int_field_counts'])}",
                    f"empty_slot_int_fields={_format_counts(row['empty_slot_int_field_counts'])}",
                    f"candidate_paths={_format_counts(row['candidate_path_counts'])}",
                    f"payload_shapes={_format_counts(row['payload_field_shapes'])}",
                    f"payload_f5={_format_summary(row['payload_field5_count'])}",
                    f"payload_f6={_format_summary(row['payload_field6_count'])}",
                    f"payload_f7={_format_summary(row['payload_field7_count'])}",
                    f"payload_f8={_format_summary(row['payload_field8_count'])}",
                    f"payload_f20_rows={row['payload_field20_present_rows']}/{row['files']}",
                    f"payload_f20_values={_format_counts(row['payload_field20_values'])}",
                    f"payload_f5_child={_format_counts(row['payload_field5_child_signatures'])}",
                    f"payload_f8_child={_format_counts(row['payload_field8_child_signatures'])}",
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
        choices=(
            "map_id",
            "map_prefix3",
            "map_family",
            "residual_mode",
            "round_index",
            "capture_rounds",
            "capture_day",
            "session_token_prefix6",
            "session_token_prefix8",
            "bidmap_rounds_total",
        ),
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
