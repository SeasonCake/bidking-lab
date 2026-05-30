"""Summarize live monitor ``model_eval.jsonl`` calibration logs."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


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


def summarize(rows: list[dict[str, Any]], *, dedupe: bool = True) -> dict[str, Any]:
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
            "map_id": _group_summary(valid, "map_id"),
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
    args = parser.parse_args()
    rows = _read_jsonl(Path(args.path))
    print(json.dumps(summarize(rows, dedupe=not args.no_dedupe), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
