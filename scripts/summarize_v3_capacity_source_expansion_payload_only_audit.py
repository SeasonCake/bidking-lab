"""Audit payload-only v3 capacity/source expansion truth rows.

This script is diagnostic-only. It explains settlement source-semantics truth
rows that lack full public-total/direct-action confirmation, and joins them
with map-id holdout coverage plus pre-bid CSE pressure windows.
"""

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
    _default_capacity_source_expansion_path,
    _default_paths,
    _default_settlement_count_prior_path,
    _default_tail_value_review_path,
    _default_underestimate_repair_path,
    evaluate_paths,
    load_capacity_source_expansion_entries,
    load_monitor_tables,
    load_prior_calibration_entries,
    load_settlement_count_prior_entries,
    load_tail_value_review_entries,
    load_underestimate_repair_entries,
)
from summarize_v3_capacity_source_expansion_holdout import (  # noqa: E402
    _eval_rows,
    _float_or_none,
    _format_counts,
    _format_summary,
    _numeric_summary,
    _rows_for_paths,
    _source_semantics_truth,
)

PAYLOAD_CONTEXT_PREFIXES = ("payload_verified_", "payload_unverified_")


def _base_file(row: Mapping[str, Any]) -> str:
    return str(row.get("file") or "").split("#", 1)[0]


def _is_payload_context(row: Mapping[str, Any]) -> bool:
    context = str(row.get("source_context_class") or "")
    return context.startswith(PAYLOAD_CONTEXT_PREFIXES)


def _is_payload_truth(row: Mapping[str, Any]) -> bool:
    return _source_semantics_truth(row) and _is_payload_context(row)


def _counter_dict(values: Iterable[Any], *, top: int) -> dict[str, int]:
    counter = Counter(str(value) for value in values if value not in (None, ""))
    return dict(counter.most_common(top))


def _pressure_by_file(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "candidate_windows": 0,
            "pressure_windows": 0,
            "pressure_rounds": Counter(),
            "pressure_target_sources": Counter(),
            "pressure_target_prior_max_delta": [],
            "pressure_target_to_source_p95_delta": [],
        }
    )
    for row in rows:
        if row.get("status") != "ready" or not row.get("v3_cse_ready"):
            continue
        file = _base_file(row)
        if not file:
            continue
        if row.get("v3_cse_candidate"):
            out[file]["candidate_windows"] += 1
        if row.get("v3_cse_pressure_candidate"):
            out[file]["pressure_windows"] += 1
            out[file]["pressure_rounds"][str(row.get("round") or "none")] += 1
            out[file]["pressure_target_sources"][
                str(row.get("v3_cse_target_count_source") or "none")
            ] += 1
            target_prior = _float_or_none(row.get("v3_cse_target_prior_max_delta"))
            if target_prior is not None:
                out[file]["pressure_target_prior_max_delta"].append(target_prior)
            target_p95 = _float_or_none(
                row.get("v3_cse_target_to_unique_non_temp_p95_delta")
            )
            if target_p95 is not None:
                out[file]["pressure_target_to_source_p95_delta"].append(target_p95)
    return dict(out)


def _holdout_by_file(rows: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not row.get("truth_unique_round_overflow"):
            continue
        file = str(row.get("example_file") or "")
        if file:
            out[file] = row
    return out


def _row_details(
    row: Mapping[str, Any],
    *,
    holdout: Mapping[str, Any] | None,
    pressure: Mapping[str, Any] | None,
) -> dict[str, Any]:
    pressure = pressure or {}
    holdout = holdout or {}
    pressure_rounds = pressure.get("pressure_rounds") or Counter()
    pressure_target_sources = pressure.get("pressure_target_sources") or Counter()
    return {
        "file": row.get("file"),
        "map_id": row.get("map_id"),
        "map_family": row.get("map_family"),
        "source_context_class": row.get("source_context_class"),
        "source_evidence_class": row.get("source_evidence_class"),
        "mechanism_class": row.get("mechanism_class"),
        "unique_round_excess_after_temp": _float_or_none(
            row.get("unique_round_cap_excess_after_temp_zodiac_count")
        ),
        "event_action_result_count_all": row.get("event_action_result_count_all"),
        "event_action_observed_item_count_max": row.get(
            "event_action_observed_item_count_max"
        ),
        "event_action_observed_item_inventory_gap_min": row.get(
            "event_action_observed_item_inventory_gap_min"
        ),
        "event_action_observed_item_ratio_max": row.get(
            "event_action_observed_item_ratio_max"
        ),
        "map_id_holdout_covered": bool(
            holdout.get("covered_unique_round_overflow")
        ),
        "map_id_holdout_candidate_source": holdout.get("candidate_source"),
        "map_id_holdout_train_source_semantics_rows": holdout.get(
            "train_source_semantics_rows"
        ),
        "map_id_holdout_fold": holdout.get("fold"),
        "prebid_cse_candidate_windows": int(pressure.get("candidate_windows") or 0),
        "prebid_pressure_windows": int(pressure.get("pressure_windows") or 0),
        "prebid_pressure_rounds": dict(sorted(pressure_rounds.items())),
        "prebid_pressure_target_sources": dict(
            sorted(pressure_target_sources.items())
        ),
        "prebid_pressure_target_prior_max_delta": _numeric_summary(
            pressure.get("pressure_target_prior_max_delta") or ()
        ),
        "prebid_pressure_target_to_source_p95_delta": _numeric_summary(
            pressure.get("pressure_target_to_source_p95_delta") or ()
        ),
    }


def _summarize_group(
    rows: Iterable[Mapping[str, Any]],
    *,
    top: int,
) -> dict[str, Any]:
    seq = tuple(rows)
    return {
        "rows": len(seq),
        "map_ids": _counter_dict((row.get("map_id") for row in seq), top=top),
        "contexts": _counter_dict(
            (row.get("source_context_class") for row in seq),
            top=top,
        ),
        "map_id_missed_rows": sum(
            1 for row in seq if not row.get("map_id_holdout_covered")
        ),
        "prebid_candidate_rows": sum(
            1 for row in seq if int(row.get("prebid_cse_candidate_windows") or 0) > 0
        ),
        "prebid_pressure_rows": sum(
            1 for row in seq if int(row.get("prebid_pressure_windows") or 0) > 0
        ),
        "action_max": _numeric_summary(
            row.get("event_action_observed_item_count_max") for row in seq
        ),
        "action_gap": _numeric_summary(
            row.get("event_action_observed_item_inventory_gap_min") for row in seq
        ),
        "action_ratio": _numeric_summary(
            row.get("event_action_observed_item_ratio_max") for row in seq
        ),
        "unique_round_excess": _numeric_summary(
            row.get("unique_round_excess_after_temp") for row in seq
        ),
        "examples": [
            {
                "file": row.get("file"),
                "map_id": row.get("map_id"),
                "context": row.get("source_context_class"),
                "covered": row.get("map_id_holdout_covered"),
                "train_source": row.get("map_id_holdout_train_source_semantics_rows"),
                "pressure_windows": row.get("prebid_pressure_windows"),
                "action_max": row.get("event_action_observed_item_count_max"),
                "action_gap": row.get("event_action_observed_item_inventory_gap_min"),
                "excess": row.get("unique_round_excess_after_temp"),
            }
            for row in sorted(
                seq,
                key=lambda item: (
                    not bool(item.get("prebid_pressure_windows")),
                    bool(item.get("map_id_holdout_covered")),
                    -float(item.get("unique_round_excess_after_temp") or 0.0),
                    str(item.get("file") or ""),
                ),
            )[:top]
        ],
    }


def summarize_payload_only(
    paths: Iterable[Path] = (),
    *,
    rows: Iterable[Mapping[str, Any]] | None = None,
    eval_rows: Iterable[Mapping[str, Any]] | None = None,
    prebid_rows: Iterable[Mapping[str, Any]] | None = None,
    folds: int = 5,
    min_train_sessions: int = 4,
    posterior_trials: int = 64,
    top: int = 8,
) -> dict[str, Any]:
    selected_paths = tuple(paths) or _default_paths()
    if rows is None:
        rows = _rows_for_paths(selected_paths)
    settlement_rows = tuple(row for row in rows if row.get("status") == "ok")
    if eval_rows is None:
        eval_rows = _eval_rows(
            settlement_rows,
            group_by="map_id",
            fallback_group_by=None,
            folds=folds,
            min_train_sessions=min_train_sessions,
        )
    if prebid_rows is None:
        tables = load_monitor_tables()
        prebid_rows, errors = evaluate_paths(
            selected_paths,
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
            settlement_count_prior_entries=load_settlement_count_prior_entries(
                _default_settlement_count_prior_path()
            ),
            capacity_source_expansion_entries=load_capacity_source_expansion_entries(
                _default_capacity_source_expansion_path()
            ),
            posterior_trials=posterior_trials,
        )
    else:
        errors = []
    holdout_by_file = _holdout_by_file(eval_rows)
    pressure_by_file = _pressure_by_file(prebid_rows)
    truth_rows = [row for row in settlement_rows if _source_semantics_truth(row)]
    payload_rows = [row for row in truth_rows if _is_payload_context(row)]
    external_rows = [row for row in truth_rows if not _is_payload_context(row)]
    detailed = [
        _row_details(
            row,
            holdout=holdout_by_file.get(str(row.get("file") or "")),
            pressure=pressure_by_file.get(str(row.get("file") or "")),
        )
        for row in payload_rows
    ]
    by_context: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in detailed:
        by_context[str(row.get("source_context_class") or "none")].append(row)
    return {
        "settlement_rows": len(settlement_rows),
        "truth_rows": len(truth_rows),
        "payload_truth_rows": len(payload_rows),
        "external_truth_rows": len(external_rows),
        "payload_contexts": _counter_dict(
            (row.get("source_context_class") for row in payload_rows),
            top=top,
        ),
        "payload_map_id_missed_rows": sum(
            1 for row in detailed if not row.get("map_id_holdout_covered")
        ),
        "payload_prebid_candidate_rows": sum(
            1 for row in detailed if int(row.get("prebid_cse_candidate_windows") or 0) > 0
        ),
        "payload_prebid_pressure_rows": sum(
            1 for row in detailed if int(row.get("prebid_pressure_windows") or 0) > 0
        ),
        "parse_errors": len(errors),
        "groups": {
            context: _summarize_group(group_rows, top=top)
            for context, group_rows in sorted(by_context.items())
        },
        "rows": sorted(
            detailed,
            key=lambda item: (
                str(item.get("source_context_class") or ""),
                not bool(item.get("prebid_pressure_windows")),
                bool(item.get("map_id_holdout_covered")),
                -float(item.get("unique_round_excess_after_temp") or 0.0),
                str(item.get("file") or ""),
            ),
        ),
    }


def _print_summary(result: Mapping[str, Any], *, top: int) -> None:
    print(
        " ".join(
            (
                f"settlement_rows={result['settlement_rows']}",
                f"truth_rows={result['truth_rows']}",
                f"payload_truth_rows={result['payload_truth_rows']}",
                f"external_truth_rows={result['external_truth_rows']}",
                f"payload_contexts={_format_counts(result['payload_contexts'])}",
                f"payload_map_id_missed_rows={result['payload_map_id_missed_rows']}",
                f"payload_prebid_candidate_rows={result['payload_prebid_candidate_rows']}",
                f"payload_prebid_pressure_rows={result['payload_prebid_pressure_rows']}",
                f"parse_errors={result['parse_errors']}",
            )
        )
    )
    for context, row in result["groups"].items():
        print(
            " ".join(
                (
                    f"context={context}",
                    f"rows={row['rows']}",
                    f"maps={_format_counts(row['map_ids'])}",
                    f"missed={row['map_id_missed_rows']}",
                    f"prebid_candidate={row['prebid_candidate_rows']}",
                    f"prebid_pressure={row['prebid_pressure_rows']}",
                    f"action_max={_format_summary(row['action_max'])}",
                    f"action_gap={_format_summary(row['action_gap'])}",
                    f"action_ratio={_format_summary(row['action_ratio'])}",
                    f"excess={_format_summary(row['unique_round_excess'])}",
                )
            )
        )
        for example in row["examples"][:top]:
            print(
                " ".join(
                    (
                        "  example",
                        f"file={example['file']}",
                        f"map_id={example['map_id']}",
                        f"covered={example['covered']}",
                        f"train_source={example['train_source']}",
                        f"pressure={example['pressure_windows']}",
                        f"action_max={example['action_max']}",
                        f"action_gap={example['action_gap']}",
                        f"excess={example['excess']}",
                    )
                )
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit payload-only v3 CSE truth rows.",
    )
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-train-sessions", type=int, default=4)
    parser.add_argument("--posterior-trials", type=int, default=64)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args(argv)
    result = summarize_payload_only(
        args.paths,
        folds=args.folds,
        min_train_sessions=args.min_train_sessions,
        posterior_trials=args.posterior_trials,
        top=args.top,
    )
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_summary(result, top=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
