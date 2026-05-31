"""Summarize live monitor ``model_eval.jsonl`` calibration logs."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.inference.diagnostics import layout_conflict_root  # noqa: E402


def _map_family(map_id: Any) -> str:
    try:
        mid = int(map_id)
    except (TypeError, ValueError):
        return "unknown"
    prefix = mid // 100
    if mid == 2601:
        return "hidden"
    if prefix in {24, 34, 44}:
        return "villa"
    if prefix in {25, 35, 45}:
        return "shipwreck"
    return f"map_{prefix}xx"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _round(value: float | int | None) -> int | None:
    if value is None:
        return None
    return int(round(float(value)))


def _mae(rows: list[dict[str, Any]], key: str) -> int | None:
    values = [
        abs(int(row[key]))
        for row in rows
        if row.get(key) is not None
    ]
    return _round(statistics.mean(values)) if values else None


def _median_abs(rows: list[dict[str, Any]], key: str) -> int | None:
    values = [
        abs(int(row[key]))
        for row in rows
        if row.get(key) is not None
    ]
    return _round(statistics.median(values)) if values else None


def _numeric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = _numeric(row, key)
        if value is not None:
            values.append(value)
    return values


def _median_value(rows: list[dict[str, Any]], key: str) -> int | None:
    values = _numeric_values(rows, key)
    return _round(statistics.median(values)) if values else None


def _p75_value(rows: list[dict[str, Any]], key: str) -> int | None:
    values = _numeric_values(rows, key)
    if len(values) < 4:
        return None
    return _round(statistics.quantiles(values, n=4)[2])


def _rate(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row.get(key) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return round(statistics.mean(1.0 if value else 0.0 for value in values), 4)


def _numeric(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe_latest_by_file(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in rows:
        key = str(row.get("file") or "")
        if not key:
            key = f"row:{len(order)}"
        if key not in selected:
            order.append(key)
        current = selected.get(key)
        if current is None or float(row.get("ts") or 0) >= float(current.get("ts") or 0):
            selected[key] = row
    return [selected[key] for key in order]


def _with_derived_layout_root(row: dict[str, Any]) -> dict[str, Any]:
    if not row.get("layout_conflict") or row.get("layout_conflict_root"):
        return row
    root = layout_conflict_root(
        row.get("posterior_diagnostics") or row.get("layout_diagnostics")
    )
    if not root:
        return row
    return {
        **row,
        "layout_conflict_root": root,
    }


def _q6_top_size_band(row: dict[str, Any]) -> str:
    if row.get("q6_top_size_band"):
        return str(row["q6_top_size_band"])
    if (
        int(row.get("final_q6_count") or 0) <= 0
        and int(row.get("final_q6_value") or 0) <= 0
    ):
        return "no_q6"
    if int(row.get("final_top_item_quality") or 0) != 6:
        return "q6_not_top_item"
    cells = row.get("final_top_item_cells")
    if cells is None:
        return "q6_top_unknown_cells"
    cells = int(cells)
    if cells <= 2:
        return "q6_top_small"
    if cells <= 4:
        return "q6_top_compact"
    if cells <= 9:
        return "q6_top_medium"
    if cells <= 12:
        return "q6_top_large"
    return "q6_top_huge"


def _q6_miss_root(row: dict[str, Any]) -> str:
    if row.get("q6_miss_root"):
        return str(row["q6_miss_root"])
    if row.get("q6_p90_misses_truth") is not True:
        return ""
    markers: list[str] = []
    if row.get("q6_false_low_risk"):
        markers.append("low_q6_sample_rate")
    if row.get("q6_below_drop_prior"):
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
    return ";".join(dict.fromkeys(markers))


def _with_derived_q6_fields(row: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if row.get("q6_top_size_band") is None:
        updates["q6_top_size_band"] = _q6_top_size_band(row)
    if row.get("q6_miss_root") is None:
        root = _q6_miss_root({**row, **updates})
        if root:
            updates["q6_miss_root"] = root
    if (
        row.get("v2_q6_value_p90_under_by") is None
        and row.get("v2_q6_value_p90") is not None
        and int(row.get("final_q6_value") or 0) > 0
    ):
        updates["v2_q6_value_p90_under_by"] = max(
            0,
            int(row.get("final_q6_value") or 0) - int(row["v2_q6_value_p90"]),
        )
    return {**row, **updates} if updates else row


def _group_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key) or "unknown"), []).append(row)
    out: list[dict[str, Any]] = []
    for value, group_rows in sorted(groups.items()):
        out.append(
            {
                key: value,
                "n": len(group_rows),
                "decision_value_mae": _mae(group_rows, "decision_value_p50_error"),
                "decision_value_median_abs_error": _median_abs(
                    group_rows,
                    "decision_value_p50_error",
                ),
                "warehouse_mae": _mae(group_rows, "warehouse_p50_error"),
                "layout_fit_mae": _mae(group_rows, "layout_fit_p50_error"),
                "q6_false_low_rate": _rate(group_rows, "q6_false_low_risk"),
                "q6_p90_miss_rate": _rate(group_rows, "q6_p90_misses_truth"),
                "raw_ceiling_gap_median": _median_value(
                    group_rows,
                    "raw_minus_decision_p90",
                ),
                "layout_conflict_rate": _rate(group_rows, "layout_conflict"),
                "layout_overlap_rate": _marker_rate(
                    group_rows,
                    "layout_conflict_root",
                    "footprint_overlap",
                ),
                "layout_overflow_rate": _marker_rate(
                    group_rows,
                    "layout_conflict_root",
                    "footprint_overflow",
                ),
                "relaxed_exact_rate": _rate(group_rows, "relaxed_exact_used"),
            }
        )
    return out


def _marker_rate(rows: list[dict[str, Any]], key: str, marker: str) -> float | None:
    values = [str(row.get(key) or "") for row in rows if row.get(key) is not None]
    if not values:
        return None
    return round(
        statistics.mean(1.0 if marker in value.split(";") else 0.0 for value in values),
        4,
    )


def _root_cause_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    examples: dict[str, list[str]] = {}
    for row in rows:
        raw = str(row.get(key) or "unclassified")
        markers = [part for part in raw.split(";") if part] or ["unclassified"]
        for marker in markers:
            counts[marker] = counts.get(marker, 0) + 1
            examples.setdefault(marker, [])
            if len(examples[marker]) < 5:
                examples[marker].append(str(row.get("file") or ""))
    return [
        {
            "cause": cause,
            "n": n,
            "examples": examples.get(cause, []),
        }
        for cause, n in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]


def _bid_gap_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key) or "unknown"), []).append(row)

    out: list[dict[str, Any]] = []
    for value, group_rows in sorted(groups.items()):
        bid_ratios: list[float] = []
        stop_minus_values: list[float] = []
        over_final = 0
        usable_bid_rows = 0
        for row in group_rows:
            highest = _numeric(row, "highest_bid")
            final_value = _numeric(row, "final_value")
            if highest is not None and final_value is not None and final_value > 0:
                usable_bid_rows += 1
                bid_ratios.append(highest / final_value)
                if highest > final_value:
                    over_final += 1
            stop_minus = _numeric(row, "stop_minus_final_value")
            if stop_minus is not None:
                stop_minus_values.append(stop_minus)
        out.append(
            {
                key: value,
                "n": len(group_rows),
                "bid_rows": usable_bid_rows,
                "highest_bid_over_final_median": (
                    round(statistics.median(bid_ratios), 3)
                    if bid_ratios
                    else None
                ),
                "highest_bid_over_final_p75": (
                    round(statistics.quantiles(bid_ratios, n=4)[2], 3)
                    if len(bid_ratios) >= 4
                    else None
                ),
                "highest_bid_over_final_rate": (
                    round(over_final / usable_bid_rows, 4)
                    if usable_bid_rows
                    else None
                ),
                "stop_minus_final_median": (
                    _round(statistics.median(stop_minus_values))
                    if stop_minus_values
                    else None
                ),
            }
        )
    return out


def _collection_readiness(
    rows: list[dict[str, Any]],
    *,
    target_per_hero_family: int,
    hidden_target_per_hero: int,
) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        hero = str(row.get("hero") or "unknown")
        family = _map_family(row.get("map_id"))
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


def _next_sampling_targets(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(readiness.get("priority_needs") or [])
    rows.sort(
        key=lambda row: (
            0 if row.get("map_family") == "hidden" else 1,
            -int(row.get("needed") or 0),
            str(row.get("hero") or ""),
        )
    )
    out: list[dict[str, Any]] = []
    for row in rows[:6]:
        family = str(row.get("map_family") or "unknown")
        out.append(
            {
                "hero": row.get("hero"),
                "map_family": family,
                "needed": row.get("needed"),
                "reason": (
                    "hidden_cold_start"
                    if family == "hidden"
                    else "coverage_gap"
                ),
            }
        )
    return out


def _log_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "missing_hero": sum(1 for row in rows if not row.get("hero")),
        "missing_final_value": sum(1 for row in rows if row.get("final_value") is None),
        "missing_final_cells": sum(1 for row in rows if row.get("final_cells") is None),
        "missing_decision_value": sum(
            1 for row in rows if row.get("decision_value_p50") is None
        ),
        "missing_q6_truth_fields": sum(
            1 for row in rows if row.get("final_q6_value") is None
        ),
    }


def summarize(
    rows: list[dict[str, Any]],
    *,
    dedupe: bool = True,
    target_per_hero_family: int = 30,
    hidden_target_per_hero: int = 10,
) -> dict[str, Any]:
    original_count = len(rows)
    if dedupe:
        rows = _dedupe_latest_by_file(rows)
    valid = [
        _with_derived_q6_fields(_with_derived_layout_root(row)) for row in rows
        if row.get("final_value") is not None or row.get("final_cells") is not None
    ]
    q6_truth = [row for row in valid if int(row.get("final_q6_value") or 0) > 0]
    collection_readiness = _collection_readiness(
        valid,
        target_per_hero_family=target_per_hero_family,
        hidden_target_per_hero=hidden_target_per_hero,
    )
    layout_conflict = [
        row for row in valid
        if row.get("layout_conflict") is True
    ]
    q6_p90_miss = [
        row for row in valid
        if row.get("q6_p90_misses_truth") is True
    ]
    return {
        "rows": len(rows),
        "raw_rows": original_count,
        "deduped_rows": original_count - len(rows),
        "valid": len(valid),
        "q6_truth_rows": len(q6_truth),
        "decision_value_mae": _mae(valid, "decision_value_p50_error"),
        "decision_value_median_abs_error": _median_abs(
            valid,
            "decision_value_p50_error",
        ),
        "raw_value_mae": _mae(valid, "value_p50_error"),
        "raw_ceiling_gap_median": _median_value(valid, "raw_minus_decision_p90"),
        "raw_ceiling_gap_p75": _p75_value(valid, "raw_minus_decision_p90"),
        "raw_ceiling_gap_250k_count": sum(
            1 for row in valid
            if (_numeric(row, "raw_minus_decision_p90") or 0) >= 250_000
        ),
        "raw_ceiling_gap_700k_count": sum(
            1 for row in valid
            if (_numeric(row, "raw_minus_decision_p90") or 0) >= 700_000
        ),
        "warehouse_mae": _mae(valid, "warehouse_p50_error"),
        "layout_fit_mae": _mae(valid, "layout_fit_p50_error"),
        "log_quality": _log_quality(valid),
        "collection_readiness": collection_readiness,
        "next_sampling_targets": _next_sampling_targets(collection_readiness),
        "q6_false_low_count": sum(
            1 for row in valid if row.get("q6_false_low_risk") is True
        ),
        "q6_below_drop_prior_count": sum(
            1 for row in valid if row.get("q6_below_drop_prior") is True
        ),
        "q6_p90_miss_count": sum(
            1 for row in valid if row.get("q6_p90_misses_truth") is True
        ),
        "q6_p90_under_by_median": (
            _round(
                statistics.median(
                    int(row["v2_q6_value_p90_under_by"])
                    for row in q6_p90_miss
                    if row.get("v2_q6_value_p90_under_by") is not None
                )
            )
            if any(
                row.get("v2_q6_value_p90_under_by") is not None
                for row in q6_p90_miss
            )
            else None
        ),
        "q6_miss_root_causes": _root_cause_summary(
            q6_p90_miss,
            "q6_miss_root",
        ),
        "layout_conflict_count": sum(
            1 for row in valid if row.get("layout_conflict") is True
        ),
        "layout_conflict_root_causes": _root_cause_summary(
            layout_conflict,
            "layout_conflict_root",
        ),
        "relaxed_exact_count": sum(
            1 for row in valid if row.get("relaxed_exact_used") is True
        ),
        "groups": {
            "hero": _group_summary(valid, "hero"),
            "map_family": _group_summary(
                [
                    {
                        **row,
                        "map_family": _map_family(row.get("map_id")),
                    }
                    for row in valid
                ],
                "map_family",
            ),
            "map_id": _group_summary(valid, "map_id"),
        },
        "bid_gap": {
            "hero": _bid_gap_summary(valid, "hero"),
            "map_family": _bid_gap_summary(
                [
                    {
                        **row,
                        "map_family": _map_family(row.get("map_id")),
                    }
                    for row in valid
                ],
                "map_family",
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize live monitor model_eval.jsonl logs.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(ROOT / "data" / "logs" / "live" / "model_eval.jsonl"),
        help="Path to model_eval.jsonl",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Do not collapse duplicate rows with the same file name",
    )
    parser.add_argument(
        "--target-per-hero-family",
        type=int,
        default=30,
        help="Readiness target for each hero x map-family bucket",
    )
    parser.add_argument(
        "--hidden-target-per-hero",
        type=int,
        default=10,
        help="Readiness target for each hero x hidden-auction bucket",
    )
    args = parser.parse_args()
    rows = _read_jsonl(Path(args.path))
    print(
        json.dumps(
            summarize(
                rows,
                dedupe=not args.no_dedupe,
                target_per_hero_family=args.target_per_hero_family,
                hidden_target_per_hero=args.hidden_target_per_hero,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
