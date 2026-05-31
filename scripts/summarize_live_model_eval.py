"""Summarize live monitor ``model_eval.jsonl`` calibration logs."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _map_family(map_id: Any) -> str:
    try:
        mid = int(map_id)
    except (TypeError, ValueError):
        return "unknown"
    if 2400 <= mid < 2500:
        return "villa"
    if 2500 <= mid < 2600:
        return "shipwreck"
    return f"map_{mid // 100}xx"


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
                "layout_conflict_rate": _rate(group_rows, "layout_conflict"),
                "relaxed_exact_rate": _rate(group_rows, "relaxed_exact_used"),
            }
        )
    return out


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
) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        hero = str(row.get("hero") or "unknown")
        family = _map_family(row.get("map_id"))
        groups.setdefault((hero, family), []).append(row)

    rows_out: list[dict[str, Any]] = []
    for hero in ("aisha", "ethan"):
        for family in ("villa", "shipwreck"):
            count = len(groups.get((hero, family), ()))
            rows_out.append(
                {
                    "hero": hero,
                    "map_family": family,
                    "n": count,
                    "target": target_per_hero_family,
                    "needed": max(0, target_per_hero_family - count),
                    "ready": count >= target_per_hero_family,
                }
            )
    missing = sum(row["needed"] for row in rows_out)
    return {
        "target_per_hero_family": target_per_hero_family,
        "ready": missing == 0,
        "total_needed": missing,
        "groups": rows_out,
    }


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
) -> dict[str, Any]:
    original_count = len(rows)
    if dedupe:
        rows = _dedupe_latest_by_file(rows)
    valid = [
        row for row in rows
        if row.get("final_value") is not None or row.get("final_cells") is not None
    ]
    q6_truth = [row for row in valid if int(row.get("final_q6_value") or 0) > 0]
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
        "warehouse_mae": _mae(valid, "warehouse_p50_error"),
        "layout_fit_mae": _mae(valid, "layout_fit_p50_error"),
        "log_quality": _log_quality(valid),
        "collection_readiness": _collection_readiness(
            valid,
            target_per_hero_family=target_per_hero_family,
        ),
        "q6_false_low_count": sum(
            1 for row in valid if row.get("q6_false_low_risk") is True
        ),
        "q6_p90_miss_count": sum(
            1 for row in valid if row.get("q6_p90_misses_truth") is True
        ),
        "layout_conflict_count": sum(
            1 for row in valid if row.get("layout_conflict") is True
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
    args = parser.parse_args()
    rows = _read_jsonl(Path(args.path))
    print(
        json.dumps(
            summarize(
                rows,
                dedupe=not args.no_dedupe,
                target_per_hero_family=args.target_per_hero_family,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
