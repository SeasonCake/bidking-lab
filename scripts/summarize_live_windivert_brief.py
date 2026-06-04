"""Brief WinDivert live session summary: rounds, match count, bid error."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.live.monitor import (  # noqa: E402
    _model_eval_row,
    build_monitor_artifact_from_events,
    build_monitor_artifact_from_file,
    load_monitor_tables,
)
from bidking_lab.live.fatbeans import (  # noqa: E402
    FatbeansCaptureEvents,
    parse_fatbeans_capture,
)


def _num(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_windivert_row(row: dict[str, Any]) -> bool:
    if str(row.get("source") or "").lower() == "windivert":
        return True
    file_name = str(row.get("file") or "")
    return "windivert" in file_name.lower()


def _load_rows(path: Path, *, since_ts: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or not _is_windivert_row(row):
            continue
        if float(row.get("ts") or 0) < since_ts:
            continue
        rows.append(row)
    return rows


def _archive_complete_dir(archive_dir: Path) -> Path:
    if archive_dir.name == "complete":
        return archive_dir
    complete = archive_dir / "complete"
    return complete if complete.exists() else archive_dir


def _load_archive_rows(
    archive_dir: Path,
    *,
    since_ts: float,
    n_trials: int,
    roi_trials: int,
    shadow_trials: int | None,
    run_debug_shadows: bool,
    window: str,
) -> list[dict[str, Any]]:
    complete_dir = _archive_complete_dir(archive_dir)
    if not complete_dir.exists():
        return []
    paths = sorted(
        complete_dir.glob("*.json"),
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    selected = [
        path
        for path in paths
        if path.stat().st_mtime >= since_ts
        and "windivert" in path.name.lower()
    ]
    if not selected:
        return []

    tables = load_monitor_tables()
    rows: list[dict[str, Any]] = []
    for path in selected:
        if window == "full":
            rows.extend(
                _load_archive_full_rows(
                    path,
                    tables=tables,
                    n_trials=n_trials,
                    roi_trials=roi_trials,
                    shadow_trials=shadow_trials,
                    run_debug_shadows=run_debug_shadows,
                )
            )
        else:
            rows.extend(
                _load_archive_prebid_rows(
                    path,
                    tables=tables,
                    n_trials=n_trials,
                    roi_trials=roi_trials,
                    shadow_trials=shadow_trials,
                    run_debug_shadows=run_debug_shadows,
                )
            )
    return rows


def _annotate_archive_row(
    row: dict[str, Any],
    *,
    path: Path,
    artifact: dict[str, Any],
    n_trials: int,
    roi_trials: int,
    shadow_trials: int | None,
    source: str,
) -> dict[str, Any]:
    row["ts"] = path.stat().st_mtime
    row["source"] = row.get("source") or source
    row["archive_path"] = str(path)
    row["session_id"] = artifact.get("session_id")
    row["snapshot_mode"] = row.get("snapshot_mode") or "archive_fast"
    row["replay_n_trials"] = n_trials
    row["replay_roi_trials"] = roi_trials
    row["replay_shadow_trials"] = shadow_trials
    return row


def _load_archive_full_rows(
    path: Path,
    *,
    tables: Any,
    n_trials: int,
    roi_trials: int,
    shadow_trials: int | None,
    run_debug_shadows: bool,
) -> list[dict[str, Any]]:
    artifact = build_monitor_artifact_from_file(
        path,
        tables=tables,
        n_trials=n_trials,
        roi_trials=roi_trials,
        shadow_trials=shadow_trials,
        run_debug_shadows=run_debug_shadows,
    )
    eval_row = artifact.get("model_eval")
    if not isinstance(eval_row, dict):
        return []
    row = _annotate_archive_row(
        dict(eval_row),
        path=path,
        artifact=artifact,
        n_trials=n_trials,
        roi_trials=roi_trials,
        shadow_trials=shadow_trials,
        source="windivert_archive",
    )
    row["eval_window"] = "full"
    return [row]


def _events_before_sort(
    events: FatbeansCaptureEvents,
    sort_id: int,
) -> FatbeansCaptureEvents:
    return FatbeansCaptureEvents(
        packets=tuple(row for row in events.packets if int(row.sort_id) < sort_id),
        frames=tuple(row for row in events.frames if int(row.sort_id) < sort_id),
        sends=tuple(row for row in events.sends if int(row.sort_id) < sort_id),
        states=tuple(row for row in events.states if int(row.sort_id) < sort_id),
        statuses=tuple(row for row in events.statuses if int(row.sort_id) < sort_id),
    )


def _truth_breakdown_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key.startswith("final_")
    }


def _load_archive_prebid_rows(
    path: Path,
    *,
    tables: Any,
    n_trials: int,
    roi_trials: int,
    shadow_trials: int | None,
    run_debug_shadows: bool,
) -> list[dict[str, Any]]:
    events = parse_fatbeans_capture(path)
    full_artifact = build_monitor_artifact_from_events(
        events,
        file=path.name,
        tables=tables,
        n_trials=n_trials,
        roi_trials=roi_trials,
        shadow_trials=shadow_trials,
        run_debug_shadows=run_debug_shadows,
    )
    final_value = full_artifact.get("known_value_sum")
    final_cells = full_artifact.get("inventory_cells")
    if final_value is None and final_cells is None:
        return []
    truth_breakdown = _truth_breakdown_from_artifact(full_artifact)
    rows: list[dict[str, Any]] = []
    bid_sends = [send for send in events.sends if getattr(send, "kind", "") == "bid"]
    for window_round, bid_send in enumerate(bid_sends, start=1):
        prefix_events = _events_before_sort(events, int(bid_send.sort_id))
        prefix_artifact = build_monitor_artifact_from_events(
            prefix_events,
            file=f"{path.name}#prebid_r{window_round}_sort{bid_send.sort_id}",
            tables=tables,
            n_trials=n_trials,
            roi_trials=roi_trials,
            shadow_trials=shadow_trials,
            run_debug_shadows=run_debug_shadows,
        )
        eval_row = _model_eval_row(
            file=f"{path.name}#prebid_r{window_round}_sort{bid_send.sort_id}",
            artifact=prefix_artifact,
            final_value=final_value,
            final_cells=final_cells,
            truth_breakdown=truth_breakdown,
        )
        if not isinstance(eval_row, dict):
            continue
        row = _annotate_archive_row(
            dict(eval_row),
            path=path,
            artifact=full_artifact,
            n_trials=n_trials,
            roi_trials=roi_trials,
            shadow_trials=shadow_trials,
            source="windivert_archive_prebid",
        )
        row["eval_window"] = "pre_bid"
        row["eval_window_round"] = window_round
        row["window_bid_sort_id"] = int(bid_send.sort_id)
        row["window_bid_value"] = getattr(bid_send, "value", None)
        row["artifact_round"] = eval_row.get("round")
        row["artifact_action_round"] = eval_row.get("action_round")
        row["round"] = window_round
        row["action_round"] = window_round
        rows.append(row)
    return rows


def _row_key(row: dict[str, Any]) -> tuple[str, ...]:
    window = str(row.get("eval_window") or "")
    window_round = str(row.get("eval_window_round") or "")
    session_id = row.get("session_id")
    if session_id:
        return ("session", str(session_id), window, window_round)
    archive_path = row.get("archive_path")
    if archive_path:
        return ("archive", Path(str(archive_path)).name, window, window_round)
    file_name = row.get("file")
    if file_name:
        return ("file", Path(str(file_name)).name, window, window_round)
    return ("id", str(id(row)), window, window_round)


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = _row_key(row)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _source_label(row: dict[str, Any]) -> str:
    source = str(row.get("source") or "")
    if source:
        return source
    if row.get("archive_path"):
        return "windivert_archive"
    return "model_eval"


def _round_bucket(row: dict[str, Any], key: str) -> str:
    try:
        round_no = int(row.get(key) or 0)
    except (TypeError, ValueError):
        return "?"
    if round_no <= 0:
        return "?"
    if round_no <= 1:
        return "R1"
    if round_no == 2:
        return "R2"
    if round_no == 3:
        return "R3"
    return "R4+"


def _q6_truth_bucket(row: dict[str, Any]) -> str:
    value = _num(row, "final_q6_value")
    count = _num(row, "final_q6_count")
    if (value is not None and value > 0) or (count is not None and count > 0):
        return "q6>0"
    if value == 0 or count == 0:
        return "q6=0"
    return "unknown"


def _random_avg_bucket(row: dict[str, Any]) -> str:
    if str(row.get("random_sample_avg_signal_values") or "").strip():
        return "signal"
    if str(row.get("random_sample_avg_values") or "").strip():
        return "retained_only"
    return "none"


def _warehouse_error_bucket(row: dict[str, Any]) -> str:
    error = _num(row, "warehouse_p50_error")
    if error is None:
        return "unknown"
    if error < -20:
        return "under<-20"
    if error > 20:
        return "over>20"
    return "within±20"


def _random_floor_mode_bucket(row: dict[str, Any]) -> str:
    diagnostics = str(row.get("posterior_diagnostics") or "")
    for chunk in diagnostics.split(";"):
        token = chunk.strip()
        prefix = "public_random_sample_value_floor_mode:"
        if token.startswith(prefix):
            mode = token[len(prefix) :].split(":", 1)[0].strip()
            return mode or "unknown"
    return "none"


def _hero_bucket(row: dict[str, Any]) -> str:
    hero = str(row.get("hero") or row.get("local_hero") or "").strip()
    return hero or "unknown"


def _evidence_profile_bucket(row: dict[str, Any]) -> str:
    profile = str(row.get("evidence_profile_key") or "").strip()
    return profile or "unknown"


def _public_constraint_bucket(row: dict[str, Any]) -> str:
    public = str(row.get("public_constraint_key") or "").strip()
    if public and public != "none":
        return public
    return "none"


def _information_density_bucket(row: dict[str, Any]) -> str:
    band = str(row.get("information_density_band") or "").strip()
    return band or "unknown"


def _constraint_density_bucket(row: dict[str, Any]) -> str:
    count = 0
    for key in (
        "anchor_count",
        "shape_target_count",
        "category_target_count",
        "category_exclusion_count",
    ):
        value = _num(row, key)
        if value is not None:
            count += int(value)
    if _random_avg_bucket(row) == "signal":
        count += 1
    if _public_constraint_bucket(row) != "none":
        count += 1
    if row.get("size_bucket_active"):
        count += 1
    if count <= 0:
        return "none"
    if count <= 2:
        return "low_1_2"
    if count <= 5:
        return "medium_3_5"
    return "high_6_plus"


def _sample_space_bucket(row: dict[str, Any]) -> str:
    matched = _first_num(row, "posterior_samples", "matched_samples", "v2_n_matched")
    total = _first_num(row, "posterior_total_samples", "n_trials", "monitor_n_trials")
    if matched is None:
        return "unknown"
    if matched <= 0:
        return "zero_match"
    if matched <= 3:
        return "sparse_1_3"
    if total is not None and total > 0 and matched / total < 0.20:
        return "low_rate_lt20pct"
    if matched <= 10:
        return "limited_4_10"
    return "enough_gt10"


def _space_pressure_bucket(row: dict[str, Any]) -> str:
    if _q6_truth_bucket(row) != "q6>0":
        return "no_q6"
    pressure = _num(row, "v2_q6_space_pressure_p90")
    overflow = _num(row, "v2_q6_space_overflow_rate")
    if pressure is None and overflow is None:
        return "unknown"
    if (pressure is not None and pressure >= 1.0) or (
        overflow is not None and overflow > 0.10
    ):
        return "space_overflow"
    if pressure is not None and pressure < 0.50 and (overflow or 0.0) <= 0.0:
        return "low_space_pressure"
    return "space_constrained"


def _tail_bucket(row: dict[str, Any]) -> str:
    if _q6_truth_bucket(row) != "q6>0":
        if (_num(row, "final_trimmed_tail_value") or 0) > 0:
            return "non_q6_tail"
        return "no_q6_tail"
    if (_num(row, "final_q6_tail_replacement_value") or 0) > 0:
        return "q6_tail_replacement"
    top_band = str(row.get("q6_top_size_band") or "").strip()
    if top_band in {"q6_top_large", "q6_top_huge"}:
        return top_band
    if top_band:
        return "q6_non_large"
    return "q6_tail_unknown"


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "是"}


def _q6_shadow_bucket(row: dict[str, Any]) -> str:
    covered_keys = (
        "q6_residual_boost_shadow_covered_after",
        "q6_residual_deep_floor_shadow_covered_after",
        "q6_residual_hidden_floor_shadow_covered_after",
        "q6_residual_villa_floor_shadow_covered_after",
    )
    active_keys = (
        "q6_residual_boost_shadow_active",
        "q6_residual_deep_floor_shadow_active",
        "q6_residual_hidden_floor_shadow_active",
        "q6_residual_villa_floor_shadow_active",
    )
    if any(_truthy(row.get(key)) for key in covered_keys):
        return "covered"
    if any(_truthy(row.get(key)) for key in active_keys):
        return "active_miss"
    if _q6_truth_bucket(row) == "q6>0":
        return "inactive_q6"
    return "none"


def _truth_value(row: dict[str, Any]) -> float | None:
    return _first_num(row, "final_decision_value", "final_value")


def _p90_under_by(row: dict[str, Any]) -> float | None:
    p90 = _num(row, "decision_value_p90")
    truth = _truth_value(row)
    if p90 is None or truth is None:
        return None
    return max(0.0, truth - p90)


def _p90_covers(row: dict[str, Any]) -> bool | None:
    under = _p90_under_by(row)
    if under is None:
        return None
    return under <= 0


def _q6_p90_under(row: dict[str, Any]) -> bool:
    if _truthy(row.get("q6_plannable_p90_misses_truth")):
        return True
    q6_truth = _first_num(row, "final_q6_decision_value", "final_q6_value")
    q6_p90 = _num(row, "v2_q6_decision_value_p90")
    return q6_truth is not None and q6_truth > 0 and q6_p90 is not None and q6_p90 < q6_truth


def _primary_error_bucket(row: dict[str, Any]) -> str:
    covered = _p90_covers(row)
    if covered is None:
        return "no_estimate"
    if covered:
        return "p90_covered"
    if _hero_bucket(row) == "unknown" or row.get("map_id") in (None, ""):
        return "missing_opening_context"
    q6_shadow = _q6_shadow_bucket(row)
    if _q6_truth_bucket(row) == "q6>0" and _q6_p90_under(row):
        if q6_shadow == "inactive_q6":
            return "q6_gate_inactive"
        space = _space_pressure_bucket(row)
        if space == "space_overflow":
            return "q6_space_constrained"
        if _tail_bucket(row) in {"q6_tail_replacement", "q6_top_large", "q6_top_huge"}:
            return "q6_tail_value"
        if space == "low_space_pressure":
            return "q6_value_distribution"
        return "q6_undercovered"
    if _random_avg_bucket(row) == "signal":
        return "random_avg_floor_insufficient"
    if _warehouse_error_bucket(row) == "under<-20":
        return "warehouse_underestimated"
    if _sample_space_bucket(row) in {"zero_match", "sparse_1_3", "low_rate_lt20pct"}:
        return "sample_space_sparse"
    if row.get("layout_conflict") or _constraint_density_bucket(row) == "high_6_plus":
        return "constraint_or_layout_conflict"
    if _information_density_bucket(row) == "low" or _round_bucket(row, "action_round") in {"R1", "R2"}:
        return "low_information_window"
    if _public_constraint_bucket(row) != "none":
        return "public_constraint_interaction"
    return "other_value_under"


def _diagnostic_tags(row: dict[str, Any]) -> tuple[str, ...]:
    tags: list[str] = []
    covered = _p90_covers(row)
    if covered is None:
        tags.append("no_estimate")
    elif covered:
        tags.append("p90_covered")
    else:
        tags.append("p90_under")
    if _hero_bucket(row) == "unknown" or row.get("map_id") in (None, ""):
        tags.append("missing_opening_context")
    if _round_bucket(row, "action_round") in {"R1", "R2"}:
        tags.append("early_round")
    if _information_density_bucket(row) in {"low", "unknown"}:
        tags.append(f"info_{_information_density_bucket(row)}")
    if _q6_truth_bucket(row) == "q6>0":
        tags.append("q6_truth")
        if _q6_p90_under(row):
            tags.append("q6_p90_under")
        tags.append(f"q6_shadow_{_q6_shadow_bucket(row)}")
        tags.append(f"q6_space_{_space_pressure_bucket(row)}")
        tail = _tail_bucket(row)
        if tail not in {"q6_non_large", "q6_tail_unknown"}:
            tags.append(tail)
    else:
        tags.append("q6_absent_or_unknown")
    random_avg = _random_avg_bucket(row)
    if random_avg != "none":
        tags.append(f"random_avg_{random_avg}")
        tags.append(f"random_floor_{_random_floor_mode_bucket(row)}")
    public = _public_constraint_bucket(row)
    if public != "none":
        tags.append(f"public_{public}")
    warehouse = _warehouse_error_bucket(row)
    if warehouse != "within±20":
        tags.append(f"warehouse_{warehouse}")
    sample_space = _sample_space_bucket(row)
    if sample_space != "enough_gt10":
        tags.append(f"sample_{sample_space}")
    constraint_density = _constraint_density_bucket(row)
    if constraint_density != "none":
        tags.append(f"constraints_{constraint_density}")
    if row.get("layout_conflict"):
        tags.append("layout_conflict")
    if row.get("size_bucket_active"):
        tags.append("size_bucket_active")
    if (_num(row, "shape_target_count") or 0) > 0:
        tags.append("shape_constraint")
    if (
        (_num(row, "category_target_count") or 0) > 0
        or (_num(row, "category_exclusion_count") or 0) > 0
    ):
        tags.append("category_tool_constraint")
    return tuple(dict.fromkeys(tags))


def _first_num(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _num(row, key)
        if value is not None:
            return value
    return None


def _top_p90_miss_examples(
    rows: list[dict[str, Any]],
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    misses = [
        (under, row)
        for row in rows
        if (under := _p90_under_by(row)) is not None and under > 0
    ]
    misses.sort(key=lambda item: item[0], reverse=True)
    examples: list[dict[str, Any]] = []
    for under, row in misses[:limit]:
        examples.append(
            {
                "under_by": int(under),
                "primary_error": _primary_error_bucket(row),
                "hero": _hero_bucket(row),
                "map_id": row.get("map_id"),
                "round": row.get("action_round") or row.get("round"),
                "truth": _truth_value(row),
                "p90": _num(row, "decision_value_p90"),
                "q6_truth": _first_num(row, "final_q6_decision_value", "final_q6_value"),
                "q6_p90": _num(row, "v2_q6_decision_value_p90"),
                "q6_shadow": _q6_shadow_bucket(row),
                "space": _space_pressure_bucket(row),
                "warehouse": _warehouse_error_bucket(row),
                "sample": _sample_space_bucket(row),
                "evidence_profile": _evidence_profile_bucket(row),
                "file": row.get("file"),
                "session_id": row.get("session_id"),
            }
        )
    return examples


def _group_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [_num(row, "decision_value_p50_error") for row in rows]
    signed = [v for v in errors if v is not None]
    clean = [abs(v) for v in signed]
    matched = [
        _first_num(row, "posterior_samples", "matched_samples", "v2_n_matched")
        for row in rows
    ]
    matched_clean = [v for v in matched if v is not None]
    trials = []
    for row in rows:
        prof = row.get("inference_profile") or {}
        if isinstance(prof, dict) and prof.get("n_trials") is not None:
            trials.append(float(prof["n_trials"]))
        elif row.get("monitor_n_trials") is not None:
            trials.append(float(row["monitor_n_trials"]))
        elif row.get("n_trials") is not None:
            trials.append(float(row["n_trials"]))
    p90_coverage_values: list[float] = []
    for row in rows:
        p90 = _num(row, "decision_value_p90")
        truth = _first_num(row, "final_decision_value", "final_value")
        if p90 is not None and truth is not None:
            p90_coverage_values.append(1.0 if p90 >= truth else 0.0)
    return {
        "rows": len(rows),
        "median_matched": int(statistics.median(matched_clean)) if matched_clean else None,
        "median_p50_error": round(statistics.median(signed), 1) if signed else None,
        "median_abs_p50_error": round(statistics.median(clean), 1) if clean else None,
        "p50_under_rate": round(
            statistics.mean(1.0 if value < 0 else 0.0 for value in signed),
            2,
        )
        if signed
        else None,
        "p90_coverage": round(statistics.mean(p90_coverage_values), 2)
        if p90_coverage_values
        else None,
        "median_n_trials": int(statistics.median(trials)) if trials else None,
        "size_bucket_active_rate": round(
            statistics.mean(1.0 if row.get("size_bucket_active") else 0.0 for row in rows),
            2,
        )
        if rows
        else None,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_observed_round: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_action_round: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_q6_truth: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_random_avg: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_random_floor_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_q6_shadow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_warehouse_error: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_primary_error: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_diagnostic_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_hero: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_evidence_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_public_constraint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_information_density: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_constraint_density: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_sample_space: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_space_pressure: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_tail: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_observed_round[_round_bucket(row, "round")].append(row)
        by_action_round[_round_bucket(row, "action_round")].append(row)
        by_q6_truth[_q6_truth_bucket(row)].append(row)
        by_random_avg[_random_avg_bucket(row)].append(row)
        by_random_floor_mode[_random_floor_mode_bucket(row)].append(row)
        by_q6_shadow[_q6_shadow_bucket(row)].append(row)
        by_warehouse_error[_warehouse_error_bucket(row)].append(row)
        by_primary_error[_primary_error_bucket(row)].append(row)
        for tag in _diagnostic_tags(row):
            by_diagnostic_tag[tag].append(row)
        by_hero[_hero_bucket(row)].append(row)
        by_evidence_profile[_evidence_profile_bucket(row)].append(row)
        by_public_constraint[_public_constraint_bucket(row)].append(row)
        by_information_density[_information_density_bucket(row)].append(row)
        by_constraint_density[_constraint_density_bucket(row)].append(row)
        by_sample_space[_sample_space_bucket(row)].append(row)
        by_space_pressure[_space_pressure_bucket(row)].append(row)
        by_tail[_tail_bucket(row)].append(row)
    return {
        "total_rows": len(rows),
        "source_counts": dict(Counter(_source_label(row) for row in rows)),
        "overall": _group_stats(rows),
        "by_observed_round": {
            label: _group_stats(group)
            for label, group in sorted(by_observed_round.items())
        },
        "by_action_round": {
            label: _group_stats(group)
            for label, group in sorted(by_action_round.items())
        },
        "by_round": {
            label: _group_stats(group)
            for label, group in sorted(by_action_round.items())
        },
        "by_q6_truth": {
            label: _group_stats(group)
            for label, group in sorted(by_q6_truth.items())
        },
        "by_random_avg": {
            label: _group_stats(group)
            for label, group in sorted(by_random_avg.items())
        },
        "by_random_floor_mode": {
            label: _group_stats(group)
            for label, group in sorted(by_random_floor_mode.items())
        },
        "by_q6_shadow": {
            label: _group_stats(group)
            for label, group in sorted(by_q6_shadow.items())
        },
        "by_warehouse_error": {
            label: _group_stats(group)
            for label, group in sorted(by_warehouse_error.items())
        },
        "by_primary_error": {
            label: _group_stats(group)
            for label, group in sorted(by_primary_error.items())
        },
        "by_diagnostic_tag": {
            label: _group_stats(group)
            for label, group in sorted(by_diagnostic_tag.items())
        },
        "by_hero": {
            label: _group_stats(group)
            for label, group in sorted(by_hero.items())
        },
        "by_evidence_profile": {
            label: _group_stats(group)
            for label, group in sorted(by_evidence_profile.items())
        },
        "by_public_constraint": {
            label: _group_stats(group)
            for label, group in sorted(by_public_constraint.items())
        },
        "by_information_density": {
            label: _group_stats(group)
            for label, group in sorted(by_information_density.items())
        },
        "by_constraint_density": {
            label: _group_stats(group)
            for label, group in sorted(by_constraint_density.items())
        },
        "by_sample_space": {
            label: _group_stats(group)
            for label, group in sorted(by_sample_space.items())
        },
        "by_space_pressure": {
            label: _group_stats(group)
            for label, group in sorted(by_space_pressure.items())
        },
        "by_tail": {
            label: _group_stats(group)
            for label, group in sorted(by_tail.items())
        },
        "top_p90_misses": _top_p90_miss_examples(rows),
    }


def _print_report(
    summary: dict[str, Any],
    *,
    detail_groups: bool = False,
) -> None:
    print(f"windivert_rows={summary['total_rows']}")
    source_counts = summary.get("source_counts") or {}
    if source_counts:
        print(
            "sources: "
            + " ".join(
                f"{label}={count}"
                for label, count in sorted(source_counts.items())
            )
        )
    overall = summary["overall"]
    print(
        "overall: "
        f"median_matched={overall.get('median_matched')} "
        f"median_p50_err={overall.get('median_p50_error')} "
        f"median_abs_p50_err={overall.get('median_abs_p50_error')} "
        f"p50_under_rate={overall.get('p50_under_rate')} "
        f"p90_coverage={overall.get('p90_coverage')} "
        f"median_n_trials={overall.get('median_n_trials')} "
        f"size_bucket_rate={overall.get('size_bucket_active_rate')}"
    )
    print()
    _print_round_groups("observed_round", summary["by_observed_round"])
    print()
    _print_round_groups("action_round", summary["by_action_round"])
    print()
    _print_round_groups("q6_truth", summary["by_q6_truth"])
    print()
    _print_round_groups("random_avg", summary["by_random_avg"])
    print()
    _print_round_groups("random_floor_mode", summary["by_random_floor_mode"])
    print()
    _print_round_groups("q6_shadow", summary["by_q6_shadow"])
    print()
    _print_round_groups("warehouse_p50_error", summary["by_warehouse_error"])
    print()
    _print_round_groups("primary_error", summary["by_primary_error"])
    print()
    if detail_groups:
        _print_round_groups("diagnostic_tag_multi", summary["by_diagnostic_tag"])
        print()
        _print_round_groups("hero", summary["by_hero"])
        print()
        _print_round_groups("evidence_profile", summary["by_evidence_profile"])
        print()
        _print_round_groups("public_constraint", summary["by_public_constraint"])
        print()
        _print_round_groups("information_density", summary["by_information_density"])
        print()
        _print_round_groups("constraint_density", summary["by_constraint_density"])
        print()
        _print_round_groups("sample_space", summary["by_sample_space"])
        print()
        _print_round_groups("q6_space_pressure", summary["by_space_pressure"])
        print()
        _print_round_groups("tail", summary["by_tail"])
        print()
    _print_miss_examples(summary.get("top_p90_misses") or [])


def _print_round_groups(label: str, groups: dict[str, Any]) -> None:
    print(
        f"{label},rows,median_matched,median_p50_err,"
        "median_abs_p50_err,p50_under_rate,p90_coverage,median_n_trials,"
        "size_bucket_rate"
    )
    for round_label, group in groups.items():
        print(
            f"{round_label},"
            f"{group['rows']},"
            f"{group.get('median_matched')},"
            f"{group.get('median_p50_error')},"
            f"{group.get('median_abs_p50_error')},"
            f"{group.get('p50_under_rate')},"
            f"{group.get('p90_coverage')},"
            f"{group.get('median_n_trials')},"
            f"{group.get('size_bucket_active_rate')}"
        )


def _print_miss_examples(examples: list[dict[str, Any]]) -> None:
    print(
        "top_p90_misses,under_by,primary_error,hero,map_id,round,"
        "truth,p90,q6_truth,q6_p90,q6_shadow,space,warehouse,sample,"
        "evidence_profile,file"
    )
    for index, row in enumerate(examples, start=1):
        print(
            f"{index},"
            f"{row.get('under_by')},"
            f"{row.get('primary_error')},"
            f"{row.get('hero')},"
            f"{row.get('map_id')},"
            f"{row.get('round')},"
            f"{row.get('truth')},"
            f"{row.get('p90')},"
            f"{row.get('q6_truth')},"
            f"{row.get('q6_p90')},"
            f"{row.get('q6_shadow')},"
            f"{row.get('space')},"
            f"{row.get('warehouse')},"
            f"{row.get('sample')},"
            f"{row.get('evidence_profile')},"
            f"{Path(str(row.get('file') or '')).name}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log",
        type=Path,
        default=ROOT / "data" / "logs" / "live" / "model_eval.jsonl",
    )
    parser.add_argument(
        "--since-hours",
        type=float,
        default=24.0,
        help="Only include rows newer than this many hours (default 24)",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=ROOT / "data" / "logs" / "live" / "raw" / "archive",
        help="Also replay recent WinDivert archives from this archive root/complete dir",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Only read model_eval.jsonl; do not replay archived captures",
    )
    parser.add_argument("--archive-n-trials", type=int, default=10)
    parser.add_argument("--archive-roi-trials", type=int, default=0)
    parser.add_argument("--archive-shadow-trials", type=int, default=1)
    parser.add_argument(
        "--archive-debug-shadows",
        action="store_true",
        help="Enable debug shadows while replaying archives for this brief summary",
    )
    parser.add_argument(
        "--archive-window",
        choices=("prebid", "full"),
        default="prebid",
        help=(
            "Archive replay window: prebid evaluates each round immediately before "
            "the user's bid SEND 0x0022; full keeps the previous one-row whole-game view"
        ),
    )
    parser.add_argument(
        "--detail-groups",
        action="store_true",
        help=(
            "Print detailed diagnostic groups such as hero, evidence profile, "
            "sample space, q6 space pressure, and multi-tag buckets."
        ),
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    if not args.log.exists():
        print(f"Missing log: {args.log}", file=sys.stderr)
        return 1
    since_ts = time.time() - max(0.0, args.since_hours) * 3600.0
    rows = _load_rows(args.log, since_ts=since_ts)
    if not args.no_archive:
        rows.extend(
            _load_archive_rows(
                args.archive_dir,
                since_ts=since_ts,
                n_trials=max(1, int(args.archive_n_trials)),
                roi_trials=max(0, int(args.archive_roi_trials)),
                shadow_trials=max(1, int(args.archive_shadow_trials)),
                run_debug_shadows=bool(args.archive_debug_shadows),
                window=args.archive_window,
            )
        )
    rows = _dedupe_rows(rows)
    summary = summarize(rows)
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=True, indent=2))
    else:
        _print_report(summary, detail_groups=bool(args.detail_groups))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
