"""Audit candidate table mappings for 252x activity settlement rows."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from evaluate_fatbeans_v3_samples import _round_metric  # noqa: E402
from bidking_lab.inference.ground_truth import prepare_session_sampler  # noqa: E402
from bidking_lab.live.fatbeans import parse_fatbeans_capture  # noqa: E402
from bidking_lab.live.monitor import load_monitor_tables  # noqa: E402

DEFAULT_SAMPLE_ROOT = ROOT / "data" / "samples" / "fatbeans_activity_20260605_shipwreck"
DEFAULT_SCHEMES = ("minus10:-10", "minus20:-20")
_EPSILON = 1e-12


def _numeric_values(values: Iterable[Any]) -> tuple[float, ...]:
    out: list[float] = []
    for value in values:
        if isinstance(value, bool) or value is None:
            continue
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            continue
    return tuple(out)


def _numeric_summary(values: Iterable[Any], *, digits: int = 6) -> dict[str, Any]:
    seq = _numeric_values(values)
    if not seq:
        return {"n": 0, "avg": None, "min": None, "p50": None, "max": None}
    ordered = sorted(seq)
    p50_index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.5)))
    return {
        "n": len(seq),
        "avg": _round_metric(sum(seq) / len(seq), digits),
        "min": _round_metric(min(seq), digits),
        "p50": _round_metric(ordered[p50_index], digits),
        "max": _round_metric(max(seq), digits),
    }


def _counter_dict(values: Iterable[Any], *, top: int = 12) -> dict[str, int]:
    counts: Counter[str] = Counter(
        str(value) if value not in (None, "") else "none"
        for value in values
    )
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top])


def _format_counts(counts: Mapping[str, int]) -> str:
    return ",".join(f"{key}:{value}" for key, value in counts.items()) or "-"


def _format_summary(summary: Mapping[str, Any]) -> str:
    return (
        f"n={summary['n']}"
        f"/avg={summary['avg']}"
        f"/min={summary['min']}"
        f"/p50={summary['p50']}"
        f"/max={summary['max']}"
    )


def _resolve_paths(paths: Iterable[Path]) -> tuple[Path, ...]:
    seq = tuple(paths) or (DEFAULT_SAMPLE_ROOT,)
    out: list[Path] = []
    for path in seq:
        if path.is_dir():
            out.extend(sorted(path.glob("*.json")))
        elif path.exists():
            out.append(path)
    return tuple(out)


def _parse_schemes(values: Iterable[str]) -> tuple[tuple[str, int], ...]:
    out: list[tuple[str, int]] = []
    for raw in values:
        if ":" not in raw:
            raise ValueError(f"scheme must be label:delta, got {raw!r}")
        label, delta_text = raw.split(":", 1)
        label = label.strip()
        if not label:
            raise ValueError(f"scheme label is empty in {raw!r}")
        out.append((label, int(delta_text)))
    return tuple(out)


def _latest_inventory_state(path: Path) -> Any | None:
    events = parse_fatbeans_capture(path)
    states = [
        state
        for state in tuple(getattr(events, "states", ()) or ())
        if tuple(getattr(state, "inventory_items", ()) or ())
    ]
    return states[-1] if states else None


def _quality_for_item(item: Any, *, tables: Any) -> int | None:
    value = getattr(item, "quality", None)
    if value is not None:
        try:
            return int(value)
        except (TypeError, ValueError):
            pass
    item_id = getattr(item, "item_id", None)
    table_item = tables.items.get(int(item_id)) if item_id is not None else None
    if table_item is None:
        return None
    return int(getattr(table_item, "quality"))


def _observed_inventory(path: Path, *, tables: Any) -> dict[str, Any]:
    state = _latest_inventory_state(path)
    if state is None:
        return {
            "file": path.name,
            "status": "no_inventory_state",
            "map_id": None,
            "inventory_count": 0,
            "quality_counts": {},
            "item_ids": [],
            "missing_quality_items": 0,
        }
    items = tuple(getattr(state, "inventory_items", ()) or ())
    quality_counts: Counter[str] = Counter()
    item_ids: list[int] = []
    missing_quality = 0
    for item in items:
        item_id = getattr(item, "item_id", None)
        if item_id is not None:
            item_ids.append(int(item_id))
        quality = _quality_for_item(item, tables=tables)
        if quality is None:
            missing_quality += 1
        else:
            quality_counts[str(quality)] += 1
    return {
        "file": path.name,
        "status": "ok",
        "map_id": getattr(state, "map_id", None),
        "inventory_count": len(items),
        "quality_counts": dict(sorted(quality_counts.items())),
        "item_ids": item_ids,
        "missing_quality_items": missing_quality,
    }


def _candidate_prior(map_id: int, *, tables: Any) -> dict[str, Any]:
    if map_id not in tables.maps:
        return {
            "status": "missing_bidmap",
            "map_id": map_id,
            "drop_pool_id": None,
            "quality_probabilities": {},
            "item_probabilities": {},
            "pool_size": 0,
        }
    try:
        sampler = prepare_session_sampler(
            map_id,
            maps=tables.maps,
            drops=tables.drops,
            items=tables.items,
        )
    except Exception as exc:
        return {
            "status": f"sampler_error:{exc}",
            "map_id": map_id,
            "drop_pool_id": getattr(tables.maps[map_id], "drop_pool_id", None),
            "quality_probabilities": {},
            "item_probabilities": {},
            "pool_size": 0,
        }
    quality_probs: Counter[str] = Counter()
    item_probs: Counter[int] = Counter()
    pool_size = 0
    for pool, pool_weight in zip(sampler.pools, sampler.pool_weights):
        pool_size = max(pool_size, len(pool.items))
        for item, probability, quality in zip(
            pool.items,
            pool.probabilities,
            pool.qualities,
        ):
            weighted = float(probability) * float(pool_weight)
            quality_probs[str(int(quality))] += weighted
            item_probs[int(item.item_id)] += weighted
    quality_total = sum(quality_probs.values())
    item_total = sum(item_probs.values())
    return {
        "status": "ok" if quality_total > 0.0 else "empty_prior",
        "map_id": map_id,
        "drop_pool_id": getattr(tables.maps[map_id], "drop_pool_id", None),
        "quality_probabilities": (
            {
                key: value / quality_total
                for key, value in sorted(quality_probs.items())
            }
            if quality_total > 0.0
            else {}
        ),
        "item_probabilities": (
            {
                int(key): value / item_total
                for key, value in sorted(item_probs.items())
            }
            if item_total > 0.0
            else {}
        ),
        "pool_size": pool_size,
    }


def _score_candidate(
    observed: Mapping[str, Any],
    prior: Mapping[str, Any],
    *,
    scheme: str,
    candidate_map_id: int,
) -> dict[str, Any]:
    quality_probs = prior.get("quality_probabilities") or {}
    item_probs = prior.get("item_probabilities") or {}
    quality_counts = observed.get("quality_counts") or {}
    item_ids = tuple(int(value) for value in observed.get("item_ids") or ())
    inventory_count = int(observed.get("inventory_count") or 0)
    log_likelihood = 0.0
    zero_quality_items = 0
    for quality, count in quality_counts.items():
        probability = float(quality_probs.get(str(quality), 0.0) or 0.0)
        if probability <= 0.0:
            zero_quality_items += int(count)
            probability = _EPSILON
        log_likelihood += int(count) * math.log(probability)
    missing_item_count = sum(1 for item_id in item_ids if item_id not in item_probs)
    return {
        "scheme": scheme,
        "actual_map_id": observed.get("map_id"),
        "candidate_map_id": candidate_map_id,
        "status": prior.get("status"),
        "drop_pool_id": prior.get("drop_pool_id"),
        "pool_size": prior.get("pool_size"),
        "inventory_count": inventory_count,
        "quality_counts": dict(sorted(quality_counts.items())),
        "quality_probabilities": {
            key: _round_metric(value, 6)
            for key, value in sorted(quality_probs.items())
        },
        "log_likelihood": _round_metric(log_likelihood, 6),
        "log_likelihood_per_item": (
            _round_metric(log_likelihood / inventory_count, 6)
            if inventory_count > 0
            else None
        ),
        "zero_quality_items": zero_quality_items,
        "missing_item_count": missing_item_count,
        "missing_item_rate": (
            _round_metric(missing_item_count / inventory_count, 6)
            if inventory_count > 0
            else None
        ),
    }


def _best_scheme(rows: Sequence[Mapping[str, Any]]) -> tuple[str | None, float | None]:
    scored = [
        row
        for row in rows
        if row.get("status") == "ok"
        and row.get("log_likelihood_per_item") is not None
    ]
    if not scored:
        return None, None
    ordered = sorted(
        scored,
        key=lambda row: float(row["log_likelihood_per_item"]),
        reverse=True,
    )
    if len(ordered) == 1:
        return str(ordered[0]["scheme"]), None
    margin = float(ordered[0]["log_likelihood_per_item"]) - float(
        ordered[1]["log_likelihood_per_item"]
    )
    return str(ordered[0]["scheme"]), _round_metric(margin, 6)


def summarize_activity_mapping_likelihood(
    paths: Iterable[Path] = (),
    *,
    tables: Any | None = None,
    schemes: Iterable[str] = DEFAULT_SCHEMES,
    top: int = 12,
) -> dict[str, Any]:
    tables = tables or load_monitor_tables()
    parsed_schemes = _parse_schemes(schemes)
    prior_cache: dict[int, dict[str, Any]] = {}
    file_results: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in _resolve_paths(paths):
        try:
            observed = _observed_inventory(path, tables=tables)
            candidate_rows = []
            actual_map = observed.get("map_id")
            for scheme, delta in parsed_schemes:
                candidate_map_id = int(actual_map) + int(delta) if actual_map else None
                if candidate_map_id is None:
                    prior = {
                        "status": "missing_map",
                        "quality_probabilities": {},
                        "item_probabilities": {},
                    }
                else:
                    prior = prior_cache.setdefault(
                        candidate_map_id,
                        _candidate_prior(candidate_map_id, tables=tables),
                    )
                candidate_rows.append(
                    _score_candidate(
                        observed,
                        prior,
                        scheme=scheme,
                        candidate_map_id=(
                            int(candidate_map_id)
                            if candidate_map_id is not None
                            else -1
                        ),
                    )
                )
            winner, margin = _best_scheme(candidate_rows)
            file_results.append(
                {
                    **{key: value for key, value in observed.items() if key != "item_ids"},
                    "best_scheme": winner,
                    "best_margin_per_item": margin,
                    "candidates": candidate_rows,
                }
            )
        except Exception as exc:  # pragma: no cover - retained for CLI diagnostics.
            errors.append(f"{path}:{exc}")

    candidate_rows = [
        candidate
        for row in file_results
        for candidate in row.get("candidates", ())
    ]
    scheme_rows = []
    by_scheme: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        by_scheme[str(row.get("scheme"))].append(row)
    for scheme, rows in sorted(by_scheme.items()):
        scheme_rows.append(
            {
                "scheme": scheme,
                "rows": len(rows),
                "status_counts": _counter_dict(row.get("status") for row in rows),
                "candidate_map_ids": _counter_dict(
                    row.get("candidate_map_id") for row in rows
                ),
                "drop_pool_ids": _counter_dict(row.get("drop_pool_id") for row in rows),
                "log_likelihood_per_item": _numeric_summary(
                    row.get("log_likelihood_per_item") for row in rows
                ),
                "zero_quality_items": _numeric_summary(
                    row.get("zero_quality_items") for row in rows
                ),
                "missing_item_rate": _numeric_summary(
                    row.get("missing_item_rate") for row in rows
                ),
                "winner_rows": sum(
                    1 for file_row in file_results if file_row.get("best_scheme") == scheme
                ),
            }
        )

    map_rows = []
    by_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in file_results:
        by_map[str(row.get("map_id"))].append(row)
    for map_id, rows in sorted(by_map.items()):
        map_rows.append(
            {
                "map_id": map_id,
                "files": len(rows),
                "inventory_count": _numeric_summary(
                    row.get("inventory_count") for row in rows
                ),
                "winner_counts": _counter_dict(row.get("best_scheme") for row in rows),
                "best_margin_per_item": _numeric_summary(
                    row.get("best_margin_per_item") for row in rows
                ),
            }
        )
    return {
        "errors": errors,
        "files": len(file_results),
        "schemes": [label for label, _delta in parsed_schemes],
        "winner_counts": _counter_dict(row.get("best_scheme") for row in file_results),
        "candidate_status_counts": _counter_dict(
            row.get("status") for row in candidate_rows
        ),
        "file_results": file_results,
        "scheme_results": scheme_rows,
        "map_results": map_rows,
        "top_files": sorted(
            file_results,
            key=lambda row: (
                0 if row.get("best_margin_per_item") is not None else 1,
                -float(row.get("best_margin_per_item") or 0.0),
                str(row.get("file")),
            ),
        )[:top],
    }


def _print_summary(result: Mapping[str, Any], *, top: int) -> None:
    print(
        " ".join(
            (
                f"files={result['files']}",
                f"schemes={','.join(result['schemes'])}",
                f"winners={_format_counts(result['winner_counts'])}",
                f"candidate_statuses={_format_counts(result['candidate_status_counts'])}",
                f"errors={len(result['errors'])}",
            )
        )
    )
    for row in result["scheme_results"]:
        print(
            " ".join(
                (
                    f"scheme={row['scheme']}",
                    f"rows={row['rows']}",
                    f"winner_rows={row['winner_rows']}",
                    f"status={_format_counts(row['status_counts'])}",
                    f"candidate_maps={_format_counts(row['candidate_map_ids'])}",
                    f"drop_pools={_format_counts(row['drop_pool_ids'])}",
                    f"ll_per_item={_format_summary(row['log_likelihood_per_item'])}",
                    f"zero_quality={_format_summary(row['zero_quality_items'])}",
                    f"missing_item_rate={_format_summary(row['missing_item_rate'])}",
                )
            )
        )
    for row in result["map_results"][:top]:
        print(
            " ".join(
                (
                    f"map={row['map_id']}",
                    f"files={row['files']}",
                    f"winners={_format_counts(row['winner_counts'])}",
                    f"inventory_count={_format_summary(row['inventory_count'])}",
                    f"margin={_format_summary(row['best_margin_per_item'])}",
                )
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit candidate table mappings for 252x activity settlement rows.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to scan. Defaults to 2026-06-05 activity cohort.",
    )
    parser.add_argument(
        "--scheme",
        action="append",
        help="Candidate mapping as label:delta. Defaults to minus10:-10 and minus20:-20.",
    )
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    args = parser.parse_args(argv)

    result = summarize_activity_mapping_likelihood(
        args.paths,
        schemes=args.scheme or DEFAULT_SCHEMES,
        top=args.top,
    )
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _print_summary(result, top=args.top)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
