"""Audit v3 prior-stress capacity cases against raw BidMap/Drop tables."""

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

from evaluate_fatbeans_v3_samples import (  # noqa: E402
    _default_calibration_path,
    _default_paths,
    _default_tail_value_review_path,
    _default_underestimate_repair_path,
    _float_or_none,
    _mean,
    _round_metric,
    evaluate_paths,
    load_monitor_tables,
    load_prior_calibration_entries,
    load_tail_value_review_entries,
    load_underestimate_repair_entries,
)
from summarize_v3_prior_robustness_audit import (  # noqa: E402
    summarize_prior_stress_details,
)
from bidking_lab.inference.ground_truth import prepare_session_sampler  # noqa: E402
from bidking_lab.inference.v3.truth import settlement_truth_from_fatbeans  # noqa: E402
from bidking_lab.live.fatbeans import parse_fatbeans_capture  # noqa: E402
from bidking_lab.simulation.basic_mc import flatten_pool  # noqa: E402


DEFAULT_CASE = "direct_prior_max_conflict"
DEFAULT_SAMPLE_ROOT = ROOT / "data" / "samples" / "fatbeans"
_TEMPORARY_BLUE_ZODIAC_ITEM_IDS = frozenset(range(1306003, 1306015))


def _numeric_values(values: Iterable[Any]) -> tuple[float, ...]:
    out: list[float] = []
    for value in values:
        parsed = _float_or_none(value)
        if parsed is not None:
            out.append(parsed)
    return tuple(out)


def _numeric_summary(values: Iterable[Any], *, digits: int = 3) -> dict[str, Any]:
    seq = _numeric_values(values)
    if not seq:
        return {"n": 0, "avg": None, "p90": None, "max": None}
    ordered = sorted(seq)
    p90_index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.9)))
    return {
        "n": len(seq),
        "avg": _round_metric(_mean(seq), digits),
        "p90": _round_metric(ordered[p90_index], digits),
        "max": _round_metric(max(seq), digits),
    }


def _delta_counts(values: Iterable[Any]) -> dict[str, int]:
    counts = {"below": 0, "match": 0, "above": 0}
    for value in _numeric_values(values):
        if value < 0.0:
            counts["below"] += 1
        elif value > 0.0:
            counts["above"] += 1
        else:
            counts["match"] += 1
    return counts


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


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _strip_row_file_ref(file_ref: Any) -> str:
    return str(file_ref or "").split("#", 1)[0]


def _resolve_capture_path(file_ref: Any, sample_root: Path) -> Path | None:
    raw = _strip_row_file_ref(file_ref)
    if not raw:
        return None
    path = Path(raw)
    candidates = (
        path,
        ROOT / path,
        sample_root / path.name,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _reachable_drop_item_ids_for_map(
    map_id: int | None,
    *,
    tables: Any,
    cache: dict[int, frozenset[int]],
) -> frozenset[int]:
    if map_id is None:
        return frozenset()
    map_key = int(map_id)
    if map_key in cache:
        return cache[map_key]
    bid_map = tables.maps.get(map_key)
    if bid_map is None:
        cache[map_key] = frozenset()
        return cache[map_key]
    item_ids: set[int] = set()
    if getattr(bid_map, "sub_pool_weights", None):
        for sub_map_id, _weight in bid_map.sub_pool_weights:
            sub_map = tables.maps.get(int(sub_map_id))
            if sub_map is None:
                continue
            item_ids.update(
                flatten_pool(
                    int(sub_map.drop_pool_id),
                    tables.drops,
                    tables.items,
                ).item_ids
            )
    item_ids.update(
        flatten_pool(
            int(bid_map.drop_pool_id),
            tables.drops,
            tables.items,
        ).item_ids
    )
    cache[map_key] = frozenset(item_ids)
    return cache[map_key]


def _inventory_diagnostic_for_path(
    path: Path,
    *,
    tables: Any,
    drop_universe_cache: dict[int, frozenset[int]],
) -> dict[str, Any]:
    events = parse_fatbeans_capture(path)
    inventory_states = [
        state
        for state in tuple(getattr(events, "states", ()) or ())
        if tuple(getattr(state, "inventory_items", ()) or ())
    ]
    truth = settlement_truth_from_fatbeans(events, items=tables.items)
    if not inventory_states:
        return {
            "path": str(path),
            "file": path.name,
            "status": "no_inventory_state",
            "inventory_state_count": 0,
            "latest_sort_id": None,
            "latest_message_id": None,
            "latest_round_index": None,
            "latest_map_id": None,
            "latest_item_count": None,
            "latest_total_cells": None,
            "truth_item_count": getattr(truth, "item_count", None),
            "truth_matches_latest": False,
            "unique_runtime_id_count": None,
            "duplicate_runtime_id_count": None,
            "unique_item_id_count": None,
            "duplicate_item_id_count": None,
            "unique_runtime_item_pair_count": None,
            "duplicate_runtime_item_pair_count": None,
            "quality_counts": {},
            "cell_counts": {},
            "missing_from_drop_universe_count": None,
            "known_temp_zodiac_count": None,
            "non_zodiac_missing_from_drop_universe_count": None,
            "missing_from_drop_universe_examples": {},
            "drop_ref_excess_item_count": None,
            "drop_ref_excess_after_temp_zodiac_count": None,
            "round_cap_excess_item_count": None,
            "round_cap_excess_after_temp_zodiac_count": None,
        }

    latest = inventory_states[-1]
    items = tuple(getattr(latest, "inventory_items", ()) or ())
    runtime_ids = [getattr(item, "runtime_id", None) for item in items]
    item_ids = [getattr(item, "item_id", None) for item in items]
    runtime_item_pairs = [
        (getattr(item, "runtime_id", None), getattr(item, "item_id", None))
        for item in items
    ]
    quality_counts = Counter(str(getattr(item, "quality", None)) for item in items)
    cell_counts = Counter(str(getattr(item, "cells", None)) for item in items)
    truth_count = getattr(truth, "item_count", None)
    latest_count = len(items)
    latest_map_id = getattr(latest, "map_id", None)
    reachable_item_ids = _reachable_drop_item_ids_for_map(
        _safe_int(latest_map_id),
        tables=tables,
        cache=drop_universe_cache,
    )
    missing_item_ids = [
        int(item_id)
        for item_id in item_ids
        if item_id is not None and int(item_id) not in reachable_item_ids
    ]
    known_temp_zodiac_count = sum(
        1 for item_id in missing_item_ids if int(item_id) in _TEMPORARY_BLUE_ZODIAC_ITEM_IDS
    )
    bid_map = tables.maps.get(_safe_int(latest_map_id)) if latest_map_id is not None else None
    drop_ref_max = _safe_int(getattr(bid_map, "items_per_session_max", None))
    round_caps = _bidmap_round_caps(bid_map) if bid_map is not None else ()
    round_cap_max = max(round_caps) if round_caps else None
    non_temp_latest_count = latest_count - known_temp_zodiac_count
    return {
        "path": str(path),
        "file": path.name,
        "status": "ok",
        "inventory_state_count": len(inventory_states),
        "latest_sort_id": getattr(latest, "sort_id", None),
        "latest_message_id": getattr(latest, "message_id", None),
        "latest_round_index": getattr(latest, "round_index", None),
        "latest_map_id": latest_map_id,
        "latest_item_count": latest_count,
        "latest_total_cells": sum(_safe_int(getattr(item, "cells", None)) or 0 for item in items),
        "truth_item_count": truth_count,
        "truth_matches_latest": (
            truth_count is not None and int(truth_count) == latest_count
        ),
        "unique_runtime_id_count": len(set(runtime_ids)),
        "duplicate_runtime_id_count": len(runtime_ids) - len(set(runtime_ids)),
        "unique_item_id_count": len(set(item_ids)),
        "duplicate_item_id_count": len(item_ids) - len(set(item_ids)),
        "unique_runtime_item_pair_count": len(set(runtime_item_pairs)),
        "duplicate_runtime_item_pair_count": (
            len(runtime_item_pairs) - len(set(runtime_item_pairs))
        ),
        "quality_counts": dict(sorted(quality_counts.items())),
        "cell_counts": dict(sorted(cell_counts.items())),
        "missing_from_drop_universe_count": len(missing_item_ids),
        "known_temp_zodiac_count": known_temp_zodiac_count,
        "non_zodiac_missing_from_drop_universe_count": (
            len(missing_item_ids) - known_temp_zodiac_count
        ),
        "missing_from_drop_universe_examples": dict(
            sorted(
                Counter(str(item_id) for item_id in missing_item_ids).items(),
                key=lambda item: (-item[1], item[0]),
            )[:8]
        ),
        "drop_ref_excess_item_count": (
            max(0, latest_count - drop_ref_max)
            if drop_ref_max is not None
            else None
        ),
        "drop_ref_excess_after_temp_zodiac_count": (
            max(0, non_temp_latest_count - drop_ref_max)
            if drop_ref_max is not None
            else None
        ),
        "round_cap_excess_item_count": (
            max(0, latest_count - round_cap_max)
            if round_cap_max is not None
            else None
        ),
        "round_cap_excess_after_temp_zodiac_count": (
            max(0, non_temp_latest_count - round_cap_max)
            if round_cap_max is not None
            else None
        ),
    }


def _merge_counter_dicts(values: Iterable[Mapping[str, int]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for value in values:
        counts.update({str(key): int(count) for key, count in value.items()})
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _inventory_diagnostics_for_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    tables: Any,
    sample_root: Path,
    top: int,
) -> dict[str, Any]:
    seq = tuple(rows)
    resolved_by_ref: dict[str, Path | None] = {}
    diagnostics_by_path: dict[Path, dict[str, Any]] = {}
    drop_universe_cache: dict[int, frozenset[int]] = {}
    missing_refs: list[str] = []
    parse_errors: list[str] = []

    for row in seq:
        ref = _strip_row_file_ref(row.get("file"))
        if not ref or ref in resolved_by_ref:
            continue
        path = _resolve_capture_path(ref, sample_root)
        resolved_by_ref[ref] = path
        if path is None:
            missing_refs.append(ref)
            continue
        if path in diagnostics_by_path:
            continue
        try:
            diagnostics_by_path[path] = _inventory_diagnostic_for_path(
                path,
                tables=tables,
                drop_universe_cache=drop_universe_cache,
            )
        except Exception as exc:  # pragma: no cover - retained for CLI diagnostics.
            parse_errors.append(f"{path}:{exc}")

    detail_truth_match_rows = 0
    detail_truth_mismatch_rows = 0
    detail_truth_unchecked_rows = 0
    for row in seq:
        ref = _strip_row_file_ref(row.get("file"))
        path = resolved_by_ref.get(ref)
        diag = diagnostics_by_path.get(path) if path is not None else None
        latest_count = _float_or_none((diag or {}).get("latest_item_count"))
        capacity = row.get("item_count_capacity", {})
        truth_count = _float_or_none(capacity.get("truth_item_count"))
        if latest_count is None or truth_count is None:
            detail_truth_unchecked_rows += 1
        elif float(latest_count) == float(truth_count):
            detail_truth_match_rows += 1
        else:
            detail_truth_mismatch_rows += 1

    diagnostics = tuple(diagnostics_by_path.values())
    status = "verified_latest_inventory"
    if missing_refs:
        status = "missing_capture_file"
    elif parse_errors:
        status = "parse_error"
    elif any(diag.get("status") == "no_inventory_state" for diag in diagnostics):
        status = "no_inventory_state"
    elif detail_truth_mismatch_rows:
        status = "detail_truth_latest_mismatch"
    elif any(
        int(diag.get("duplicate_runtime_item_pair_count") or 0) > 0
        for diag in diagnostics
    ):
        status = "duplicate_runtime_item_pair"
    elif not diagnostics:
        status = "not_checked"

    return {
        "raw_inventory_status": status,
        "raw_inventory_file_count": len(diagnostics),
        "raw_inventory_missing_file_count": len(missing_refs),
        "raw_inventory_parse_error_count": len(parse_errors),
        "raw_inventory_state_count": _numeric_summary(
            diag.get("inventory_state_count") for diag in diagnostics
        ),
        "raw_latest_inventory_item_count": _numeric_summary(
            diag.get("latest_item_count") for diag in diagnostics
        ),
        "raw_latest_inventory_total_cells": _numeric_summary(
            diag.get("latest_total_cells") for diag in diagnostics
        ),
        "raw_latest_inventory_truth_item_count": _numeric_summary(
            diag.get("truth_item_count") for diag in diagnostics
        ),
        "raw_latest_inventory_truth_match_files": sum(
            1 for diag in diagnostics if diag.get("truth_matches_latest")
        ),
        "raw_detail_truth_latest_match_rows": detail_truth_match_rows,
        "raw_detail_truth_latest_mismatch_rows": detail_truth_mismatch_rows,
        "raw_detail_truth_latest_unchecked_rows": detail_truth_unchecked_rows,
        "raw_duplicate_runtime_id_count": _numeric_summary(
            diag.get("duplicate_runtime_id_count") for diag in diagnostics
        ),
        "raw_duplicate_item_id_count": _numeric_summary(
            diag.get("duplicate_item_id_count") for diag in diagnostics
        ),
        "raw_duplicate_runtime_item_pair_count": _numeric_summary(
            diag.get("duplicate_runtime_item_pair_count") for diag in diagnostics
        ),
        "raw_missing_from_drop_universe_count": _numeric_summary(
            diag.get("missing_from_drop_universe_count") for diag in diagnostics
        ),
        "raw_known_temp_zodiac_count": _numeric_summary(
            diag.get("known_temp_zodiac_count") for diag in diagnostics
        ),
        "raw_non_zodiac_missing_from_drop_universe_count": _numeric_summary(
            diag.get("non_zodiac_missing_from_drop_universe_count")
            for diag in diagnostics
        ),
        "raw_drop_ref_excess_item_count": _numeric_summary(
            diag.get("drop_ref_excess_item_count") for diag in diagnostics
        ),
        "raw_drop_ref_excess_after_temp_zodiac_count": _numeric_summary(
            diag.get("drop_ref_excess_after_temp_zodiac_count")
            for diag in diagnostics
        ),
        "raw_round_cap_excess_item_count": _numeric_summary(
            diag.get("round_cap_excess_item_count") for diag in diagnostics
        ),
        "raw_round_cap_excess_after_temp_zodiac_count": _numeric_summary(
            diag.get("round_cap_excess_after_temp_zodiac_count")
            for diag in diagnostics
        ),
        "raw_latest_inventory_message_ids": _counter_dict(
            f"0x{int(message_id):04X}" if message_id is not None else None
            for message_id in (diag.get("latest_message_id") for diag in diagnostics)
        ),
        "raw_latest_inventory_rounds": _counter_dict(
            diag.get("latest_round_index") for diag in diagnostics
        ),
        "raw_latest_inventory_quality_counts": _merge_counter_dicts(
            diag.get("quality_counts", {}) for diag in diagnostics
        ),
        "raw_missing_from_drop_universe_examples": _merge_counter_dicts(
            diag.get("missing_from_drop_universe_examples", {})
            for diag in diagnostics
        ),
        "raw_inventory_example_files": [
            str(diag.get("file")) for diag in sorted(
                diagnostics,
                key=lambda item: str(item.get("file") or ""),
            )[:top]
        ],
        "raw_inventory_error_examples": (
            [*missing_refs[:top], *parse_errors[:top]][:top]
        ),
    }


def _capacity_cases(row: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(case) for case in row.get("item_count_capacity", {}).get("cases", ()))


def _case_match(row: Mapping[str, Any], selected_case: str) -> bool:
    if selected_case == "all":
        return True
    return selected_case in _capacity_cases(row)


def _sampler_table_summary(map_id: int, tables: Any) -> dict[str, Any]:
    bid_map = tables.maps.get(int(map_id))
    if bid_map is None:
        return {
            "map_name": None,
            "drop_pool_id": None,
            "bidmap_items_per_session_min": None,
            "bidmap_items_per_session_max": None,
            "sub_pool_count": 0,
            "sampler_pool_count": 0,
            "sampler_max_count_per_draw": None,
            "sampler_possible_item_count_max": None,
            "sampler_entries_nmax_gt1": 0,
            "bidmap_raw_column_count": None,
            "bidmap_drop_ref_column_index": None,
            "bidmap_raw_drop_ref": None,
            "bidmap_raw_round_cap_min": None,
            "bidmap_raw_round_cap_max": None,
            "table_status": "missing_bidmap",
        }
    raw_column_count = len(getattr(bid_map, "raw_row", ()) or ())
    drop_ref_index = _bidmap_drop_ref_column_index(raw_column_count)
    round_caps = _bidmap_round_caps(bid_map)
    sampler = prepare_session_sampler(
        int(map_id),
        maps=tables.maps,
        drops=tables.drops,
        items=tables.items,
    )
    max_count_per_draw = 0
    entries_nmax_gt1 = 0
    pool_item_counts: list[int] = []
    for pool in sampler.pools:
        pool_item_counts.append(len(pool.items))
        n_max_values = [int(value) for value in pool.n_max]
        if n_max_values:
            max_count_per_draw = max(max_count_per_draw, max(n_max_values))
            entries_nmax_gt1 += sum(1 for value in n_max_values if value > 1)
    possible_max = (
        int(sampler.items_per_session_max) * int(max_count_per_draw)
        if max_count_per_draw > 0
        else None
    )
    return {
        "map_name": bid_map.name,
        "drop_pool_id": bid_map.drop_pool_id,
        "bidmap_items_per_session_min": bid_map.items_per_session_min,
        "bidmap_items_per_session_max": bid_map.items_per_session_max,
        "sub_pool_count": len(bid_map.sub_pool_weights),
        "sub_pool_weights": ",".join(
            f"{sub_map_id}:{weight}" for sub_map_id, weight in bid_map.sub_pool_weights[:8]
        ),
        "sampler_pool_count": len(sampler.pools),
        "sampler_pool_item_count_summary": _numeric_summary(pool_item_counts),
        "sampler_max_count_per_draw": max_count_per_draw or None,
        "sampler_possible_item_count_max": possible_max,
        "sampler_entries_nmax_gt1": entries_nmax_gt1,
        "bidmap_raw_column_count": raw_column_count,
        "bidmap_drop_ref_column_index": drop_ref_index,
        "bidmap_raw_drop_ref": (
            bid_map.raw_row[drop_ref_index]
            if len(bid_map.raw_row) > drop_ref_index
            else None
        ),
        "bidmap_raw_round_cap_min": min(round_caps) if round_caps else None,
        "bidmap_raw_round_cap_max": max(round_caps) if round_caps else None,
        "table_status": "ok",
    }


def summarize_capacity_table_audit(
    details: Iterable[dict[str, Any]],
    *,
    tables: Any,
    selected_case: str = DEFAULT_CASE,
    top: int = 8,
    sample_root: Path = DEFAULT_SAMPLE_ROOT,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in details:
        if not _case_match(row, selected_case):
            continue
        groups[str(row.get("map_id") if row.get("map_id") not in (None, "") else "none")].append(row)

    out: list[dict[str, Any]] = []
    for map_value, rows in groups.items():
        if map_value == "none":
            table = _sampler_table_summary(-1, tables)
        else:
            table = _sampler_table_summary(int(map_value), tables)
        capacity = tuple(row["item_count_capacity"] for row in rows)
        truth_counts = _numeric_values(row.get("truth_item_count") for row in capacity)
        possible_max = _float_or_none(table.get("sampler_possible_item_count_max"))
        round_cap_max = _float_or_none(table.get("bidmap_raw_round_cap_max"))
        truth_max = max(truth_counts) if truth_counts else None
        table_impossible_rows = 0
        if possible_max is not None:
            table_impossible_rows = sum(
                1
                for value in truth_counts
                if float(value) > possible_max
            )
        round_cap_impossible_rows = 0
        if round_cap_max is not None:
            round_cap_impossible_rows = sum(
                1
                for value in truth_counts
                if float(value) > round_cap_max
            )
        status = "pass"
        if table_impossible_rows:
            status = "table_possible_max_below_truth"
        elif any(
            float(row.get("truth_prior_max_delta") or 0.0) > 0.0
            for row in capacity
        ):
            status = "bidmap_prior_max_below_truth"
        case_counts = Counter(case for row in rows for case in _capacity_cases(row))
        out.append(
            {
                "map_id": map_value,
                "rows": len(rows),
                "status": status,
                "table_impossible_rows": table_impossible_rows,
                "round_cap_impossible_rows": round_cap_impossible_rows,
                "capacity_cases": dict(
                    sorted(case_counts.items(), key=lambda item: (-item[1], item[0]))[:top]
                ),
                "target_count": _numeric_summary(
                    row.get("total_count_target") for row in capacity
                ),
                "truth_item_count": _numeric_summary(
                    row.get("truth_item_count") for row in capacity
                ),
                "target_prior_max_delta": _numeric_summary(
                    row.get("target_prior_max_delta") for row in capacity
                ),
                "truth_prior_max_delta": _numeric_summary(
                    row.get("truth_prior_max_delta") for row in capacity
                ),
                "target_truth_delta_counts": _delta_counts(
                    row.get("target_truth_delta") for row in capacity
                ),
                "source_counts": _counter_dict(
                    (row.get("total_count_source") for row in capacity),
                    top=top,
                ),
                "top_profiles": _counter_dict(
                    (row.get("hero_map_evidence_profile") for row in rows),
                    top=top,
                ),
                "example_files": [
                    str(row.get("file"))
                    for row in sorted(rows, key=lambda item: str(item.get("file") or ""))[:3]
                ],
                **_inventory_diagnostics_for_rows(
                    rows,
                    tables=tables,
                    sample_root=sample_root,
                    top=top,
                ),
                **table,
            }
        )
    return sorted(
        out,
        key=lambda row: (
            0 if row["status"] == "table_possible_max_below_truth" else 1,
            -int(row["table_impossible_rows"]),
            -int(row["rows"]),
            -float(row["truth_item_count"]["max"] or 0.0),
            str(row["map_id"]),
        ),
    )


def _format_counts(counts: Mapping[str, int]) -> str:
    return ",".join(f"{key}:{value}" for key, value in counts.items()) or "-"


def _format_summary(summary: Mapping[str, Any]) -> str:
    return (
        f"n={summary['n']}"
        f"/avg={summary['avg']}"
        f"/p90={summary['p90']}"
        f"/max={summary['max']}"
    )


def _print_summary(rows: Iterable[Mapping[str, Any]], *, top: int) -> None:
    for row in tuple(rows)[:top]:
        print(
            " ".join(
                (
                    f"map_id={row['map_id']}",
                    f"map_name={json.dumps(row['map_name'], ensure_ascii=False)}",
                    f"status={row['status']}",
                    f"rows={row['rows']}",
                    f"table_impossible_rows={row['table_impossible_rows']}",
                    f"bidmap_items={row['bidmap_items_per_session_min']}-{row['bidmap_items_per_session_max']}",
                    f"bidmap_raw_cols={row['bidmap_raw_column_count']}",
                    f"drop_ref_col={row['bidmap_drop_ref_column_index']}",
                    f"round_cap={row['bidmap_raw_round_cap_min']}-{row['bidmap_raw_round_cap_max']}",
                    f"round_cap_impossible_rows={row['round_cap_impossible_rows']}",
                    f"sampler_possible_max={row['sampler_possible_item_count_max']}",
                    f"sampler_max_count_per_draw={row['sampler_max_count_per_draw']}",
                    f"sampler_nmax_gt1={row['sampler_entries_nmax_gt1']}",
                    f"sub_pool_count={row['sub_pool_count']}",
                    f"raw_inventory={row['raw_inventory_status']}",
                    f"raw_files={row['raw_inventory_file_count']}",
                    f"raw_states={_format_summary(row['raw_inventory_state_count'])}",
                    f"raw_latest_count={_format_summary(row['raw_latest_inventory_item_count'])}",
                    f"raw_truth_match_rows={row['raw_detail_truth_latest_match_rows']}/{row['rows']}",
                    f"raw_dup_runtime={_format_summary(row['raw_duplicate_runtime_id_count'])}",
                    f"raw_dup_pair={_format_summary(row['raw_duplicate_runtime_item_pair_count'])}",
                    f"raw_dup_item={_format_summary(row['raw_duplicate_item_id_count'])}",
                    f"raw_missing_drop={_format_summary(row['raw_missing_from_drop_universe_count'])}",
                    f"raw_temp_zodiac={_format_summary(row['raw_known_temp_zodiac_count'])}",
                    f"raw_non_zodiac_missing={_format_summary(row['raw_non_zodiac_missing_from_drop_universe_count'])}",
                    f"raw_drop_excess={_format_summary(row['raw_drop_ref_excess_item_count'])}",
                    f"raw_drop_excess_after_temp={_format_summary(row['raw_drop_ref_excess_after_temp_zodiac_count'])}",
                    f"raw_round_excess={_format_summary(row['raw_round_cap_excess_item_count'])}",
                    f"raw_round_excess_after_temp={_format_summary(row['raw_round_cap_excess_after_temp_zodiac_count'])}",
                    f"raw_msg={_format_counts(row['raw_latest_inventory_message_ids'])}",
                    f"raw_rounds={_format_counts(row['raw_latest_inventory_rounds'])}",
                    f"raw_q={_format_counts(row['raw_latest_inventory_quality_counts'])}",
                    f"raw_missing_items={_format_counts(row['raw_missing_from_drop_universe_examples'])}",
                    f"cases={_format_counts(row['capacity_cases'])}",
                    f"sources={_format_counts(row['source_counts'])}",
                    f"target_count={_format_summary(row['target_count'])}",
                    f"truth_count={_format_summary(row['truth_item_count'])}",
                    f"truth_prior_delta={_format_summary(row['truth_prior_max_delta'])}",
                    f"target_truth_counts={_format_counts(row['target_truth_delta_counts'])}",
                    f"profiles={_format_counts(row['top_profiles'])}",
                )
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit prior-stress capacity cases against raw BidMap/Drop tables.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to data/samples/fatbeans.",
    )
    parser.add_argument("--case", default=DEFAULT_CASE, help="Capacity case to audit, or all.")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--posterior-trials", type=int, default=64)
    parser.add_argument("--posterior-seed", type=int, default=0)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args(argv)

    tables = load_monitor_tables()
    rows, errors = evaluate_paths(
        args.paths or _default_paths(),
        tables=tables,
        calibration_entries=load_prior_calibration_entries(
            _default_calibration_path()
        ),
        underestimate_repair_entries=load_underestimate_repair_entries(
            _default_underestimate_repair_path()
        ),
        tail_value_review_entries=load_tail_value_review_entries(
            _default_tail_value_review_path()
        ),
        posterior_trials=args.posterior_trials,
        posterior_seed=args.posterior_seed,
    )
    details = summarize_prior_stress_details(rows)
    audit = summarize_capacity_table_audit(
        details,
        tables=tables,
        selected_case=args.case,
        top=args.top,
    )
    result = {
        "errors": errors,
        "case": args.case,
        "rows": audit,
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if errors:
            print(f"errors={len(errors)}")
        print(f"case={args.case} groups={len(audit)}")
        _print_summary(audit, top=args.top)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
