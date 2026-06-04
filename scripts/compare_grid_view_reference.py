"""Compare local drop-derived quality priors with grid_view reference CSVs.

This is a read-only diagnostic for the external grid_view_v1.3.7 bundle under
external_references/. It does not touch inference weights or live logs.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")
elif sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bidking_lab.extract.bid_map_table import load_bid_map_table  # noqa: E402
from bidking_lab.extract.drop_table import load_drop_table  # noqa: E402
from bidking_lab.extract.item_table import load_item_table  # noqa: E402
from bidking_lab.inference.ground_truth import prepare_session_sampler  # noqa: E402


@dataclass(frozen=True)
class GridViewQualityReference:
    map_id: int
    quality: int
    prob_in_group: float
    p50_price_per_item: float
    p50_price_per_cell: float


@dataclass(frozen=True)
class QualityPriorComparison:
    map_id: int
    map_name: str
    quality: int
    local_draw_probability: float | None
    grid_view_probability: float | None
    probability_delta: float | None
    local_p50_price_per_item: float | None
    grid_view_p50_price_per_item: float | None
    p50_item_delta: float | None
    local_p50_price_per_cell: float | None
    grid_view_p50_price_per_cell: float | None
    p50_cell_delta: float | None


def _weighted_quantile(
    values: Iterable[float],
    weights: Iterable[float],
    quantile: float,
) -> float | None:
    value_arr = np.asarray(list(values), dtype=np.float64)
    weight_arr = np.asarray(list(weights), dtype=np.float64)
    if len(value_arr) == 0 or len(value_arr) != len(weight_arr):
        return None
    valid = weight_arr > 0
    if not np.any(valid):
        return None
    value_arr = value_arr[valid]
    weight_arr = weight_arr[valid]
    order = np.argsort(value_arr)
    value_arr = value_arr[order]
    weight_arr = weight_arr[order]
    cumulative = np.cumsum(weight_arr)
    target = float(cumulative[-1]) * quantile
    return float(np.interp(target, cumulative, value_arr))


def _load_grid_view_quality_refs(path: Path) -> dict[tuple[int, int], GridViewQualityReference]:
    refs: dict[tuple[int, int], GridViewQualityReference] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            quality_group = str(row.get("quality_group") or "")
            if not quality_group.startswith("q") or "+" in quality_group:
                continue
            quality = int(quality_group[1:])
            map_id = int(row["map_id"])
            refs[(map_id, quality)] = GridViewQualityReference(
                map_id=map_id,
                quality=quality,
                prob_in_group=float(row["prob_in_group"]),
                p50_price_per_item=float(row["p50_price_per_item"]),
                p50_price_per_cell=float(row["p50_price_per_cell"]),
            )
    return refs


def _local_quality_prior(
    map_id: int,
    quality: int,
    *,
    maps: dict,
    drops: dict,
    items: dict,
) -> tuple[float | None, float | None, float | None]:
    sampler = prepare_session_sampler(map_id, maps=maps, drops=drops, items=items)
    draw_probability = 0.0
    values: list[float] = []
    value_weights: list[float] = []
    values_per_cell: list[float] = []
    cell_weights: list[float] = []
    for pool, pool_weight in zip(sampler.pools, sampler.pool_weights):
        mask = pool.qualities == quality
        if not np.any(mask):
            continue
        weighted_probs = pool.probabilities[mask].astype(np.float64) * float(pool_weight)
        draw_probability += float(weighted_probs.sum())
        for item, prob, area in zip(
            np.asarray(pool.items, dtype=object)[mask],
            weighted_probs,
            pool.areas[mask],
        ):
            if prob <= 0:
                continue
            value = float(item.value)
            values.append(value)
            value_weights.append(float(prob))
            if int(area) > 0:
                values_per_cell.append(value / int(area))
                cell_weights.append(float(prob))
    if not values:
        return None, None, None
    return (
        draw_probability,
        _weighted_quantile(values, value_weights, 0.5),
        _weighted_quantile(values_per_cell, cell_weights, 0.5),
    )


def compare_quality_priors(
    *,
    grid_view_dir: Path,
    map_ids: Iterable[int],
    qualities: Iterable[int],
) -> list[QualityPriorComparison]:
    tables = ROOT / "data" / "raw" / "tables"
    maps = load_bid_map_table(tables / "BidMap.txt")
    drops = load_drop_table(tables / "Drop.txt")
    items = load_item_table(tables / "Item.txt")
    refs = _load_grid_view_quality_refs(
        grid_view_dir / "data" / "map_quality_p50_out.csv"
    )

    rows: list[QualityPriorComparison] = []
    for map_id in map_ids:
        if map_id not in maps:
            continue
        for quality in qualities:
            local_prob, local_p50_item, local_p50_cell = _local_quality_prior(
                map_id,
                quality,
                maps=maps,
                drops=drops,
                items=items,
            )
            ref = refs.get((map_id, quality))
            rows.append(
                QualityPriorComparison(
                    map_id=map_id,
                    map_name=maps[map_id].name,
                    quality=quality,
                    local_draw_probability=local_prob,
                    grid_view_probability=(
                        ref.prob_in_group if ref is not None else None
                    ),
                    probability_delta=(
                        local_prob - ref.prob_in_group
                        if local_prob is not None and ref is not None
                        else None
                    ),
                    local_p50_price_per_item=local_p50_item,
                    grid_view_p50_price_per_item=(
                        ref.p50_price_per_item if ref is not None else None
                    ),
                    p50_item_delta=(
                        local_p50_item - ref.p50_price_per_item
                        if local_p50_item is not None and ref is not None
                        else None
                    ),
                    local_p50_price_per_cell=local_p50_cell,
                    grid_view_p50_price_per_cell=(
                        ref.p50_price_per_cell if ref is not None else None
                    ),
                    p50_cell_delta=(
                        local_p50_cell - ref.p50_price_per_cell
                        if local_p50_cell is not None and ref is not None
                        else None
                    ),
                )
            )
    return rows


def _fmt(value: float | None, digits: int = 2) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def _write_markdown(rows: list[QualityPriorComparison]) -> None:
    print(
        "| map | q | local prob | grid prob | d prob | local p50/item | grid p50/item | d item | local p50/cell | grid p50/cell | d cell |"
    )
    print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        print(
            f"| {row.map_id} {row.map_name} | q{row.quality} | "
            f"{_fmt(row.local_draw_probability, 4)} | "
            f"{_fmt(row.grid_view_probability, 4)} | "
            f"{_fmt(row.probability_delta, 4)} | "
            f"{_fmt(row.local_p50_price_per_item, 0)} | "
            f"{_fmt(row.grid_view_p50_price_per_item, 0)} | "
            f"{_fmt(row.p50_item_delta, 0)} | "
            f"{_fmt(row.local_p50_price_per_cell, 0)} | "
            f"{_fmt(row.grid_view_p50_price_per_cell, 0)} | "
            f"{_fmt(row.p50_cell_delta, 0)} |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare local q priors with grid_view exported p50 CSV.",
    )
    parser.add_argument(
        "--grid-view-dir",
        type=Path,
        default=ROOT / "external_references" / "grid_view_v1.3.7",
    )
    parser.add_argument("--map", dest="maps", type=int, action="append")
    parser.add_argument("--quality", type=int, action="append")
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "csv"),
        default="markdown",
    )
    args = parser.parse_args()

    map_ids = args.maps or [2401, 2501, 2601, 4401, 4501]
    qualities = args.quality or [5, 6]
    rows = compare_quality_priors(
        grid_view_dir=args.grid_view_dir,
        map_ids=map_ids,
        qualities=qualities,
    )
    if args.format == "json":
        print(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2))
    elif args.format == "csv":
        if not rows:
            return 0
        writer = csv.DictWriter(sys.stdout, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    else:
        _write_markdown(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
