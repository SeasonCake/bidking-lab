"""Summarize map value tiers from local BidKing data tables.

This is a lightweight offline report for player-facing map baselines:
expected loot value, value percentiles, warehouse cells, and red/gold
appearance rates. It intentionally does not touch the live inference path.
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

from bidking_lab.extract.bid_map_table import BidMap, load_bid_map_table  # noqa: E402
from bidking_lab.extract.drop_table import load_drop_table  # noqa: E402
from bidking_lab.extract.item_table import load_item_table  # noqa: E402
from bidking_lab.inference.ground_truth import prepare_session_sampler  # noqa: E402


@dataclass(frozen=True)
class MapValueSummary:
    map_id: int
    name: str
    category: int
    tier: str
    items_per_session: str
    entry_fee: int
    starting_budget: int
    value_mean: int
    value_p50: int
    value_p90: int
    value_p95: int
    cells_p50: int
    cells_p90: int
    item_count_p50: int
    red_mean: float
    red_ge1_rate: float
    gold_mean: float
    gold_ge1_rate: float


def _percentile(values: list[int], pct: float) -> int:
    return int(np.percentile(values, pct))


def _selected_maps(
    maps: dict[int, BidMap],
    map_ids: list[int] | None,
    categories: list[int] | None,
    include_sealed: bool,
) -> list[int]:
    if map_ids:
        return [map_id for map_id in map_ids if map_id in maps]

    out: list[int] = []
    for map_id, bid_map in maps.items():
        if bid_map.auction_mode != "open" and not include_sealed:
            continue
        if bid_map.mode_flag != 4:
            continue
        if categories and bid_map.category not in categories:
            continue
        out.append(map_id)
    return sorted(out)


def summarize_maps(
    map_ids: Iterable[int],
    *,
    samples: int,
    seed: int,
) -> list[MapValueSummary]:
    tables = ROOT / "data" / "raw" / "tables"
    maps = load_bid_map_table(tables / "BidMap.txt")
    drops = load_drop_table(tables / "Drop.txt")
    items = load_item_table(tables / "Item.txt")
    rng = np.random.default_rng(seed)

    summaries: list[MapValueSummary] = []
    for map_id in map_ids:
        bid_map = maps[map_id]
        sampler = prepare_session_sampler(
            map_id,
            maps=maps,
            drops=drops,
            items=items,
        )
        values: list[int] = []
        cells: list[int] = []
        counts: list[int] = []
        red_counts: list[int] = []
        gold_counts: list[int] = []
        for _ in range(samples):
            truth = sampler.sample(rng)
            values.append(truth.total_value())
            cells.append(truth.warehouse_total_cells)
            counts.append(sum(bucket.count for bucket in truth.buckets.values()))
            red_counts.append(
                truth.buckets.get(6).count if truth.buckets.get(6) else 0
            )
            gold_counts.append(
                truth.buckets.get(5).count if truth.buckets.get(5) else 0
            )

        summaries.append(
            MapValueSummary(
                map_id=map_id,
                name=bid_map.name,
                category=bid_map.category,
                tier=bid_map.value_tier_ui,
                items_per_session=(
                    f"{bid_map.items_per_session_min}-{bid_map.items_per_session_max}"
                ),
                entry_fee=bid_map.entry_fee_silver,
                starting_budget=bid_map.starting_budget_silver,
                value_mean=int(np.mean(values)),
                value_p50=_percentile(values, 50),
                value_p90=_percentile(values, 90),
                value_p95=_percentile(values, 95),
                cells_p50=_percentile(cells, 50),
                cells_p90=_percentile(cells, 90),
                item_count_p50=_percentile(counts, 50),
                red_mean=round(float(np.mean(red_counts)), 3),
                red_ge1_rate=round(float(np.mean([count >= 1 for count in red_counts])), 4),
                gold_mean=round(float(np.mean(gold_counts)), 3),
                gold_ge1_rate=round(
                    float(np.mean([count >= 1 for count in gold_counts])), 4
                ),
            )
        )
    return summaries


def _write_markdown(rows: list[MapValueSummary], top: int) -> None:
    print(
        "| 地图 | 品级 | 件数 | EV | P50 | P90 | P95 | 总格 P50/P90 | 红>=1 | 金>=1 |"
    )
    print(
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    for row in rows[:top]:
        print(
            f"| {row.map_id} {row.name} | {row.tier} | {row.items_per_session} | "
            f"{row.value_mean:,} | {row.value_p50:,} | {row.value_p90:,} | "
            f"{row.value_p95:,} | {row.cells_p50}/{row.cells_p90} | "
            f"{row.red_ge1_rate:.0%} | {row.gold_ge1_rate:.0%} |"
        )


def _write_csv(rows: list[MapValueSummary], top: int) -> None:
    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=list(asdict(rows[0]).keys()) if rows else [],
        lineterminator="\n",
    )
    if not rows:
        return
    writer.writeheader()
    for row in rows[:top]:
        writer.writerow(asdict(row))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MC summary of map loot value tiers from local data tables.",
    )
    parser.add_argument("--samples", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument(
        "--map",
        dest="maps",
        type=int,
        action="append",
        help="Specific map_id to include; may be repeated.",
    )
    parser.add_argument(
        "--category",
        type=int,
        action="append",
        help="Map category to include when --map is omitted; may be repeated.",
    )
    parser.add_argument("--include-sealed", action="store_true")
    parser.add_argument(
        "--sort",
        choices=("mean", "p50", "p90", "id"),
        default="mean",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "csv", "json"),
        default="markdown",
    )
    args = parser.parse_args()

    tables = ROOT / "data" / "raw" / "tables"
    maps = load_bid_map_table(tables / "BidMap.txt")
    map_ids = _selected_maps(maps, args.maps, args.category, args.include_sealed)
    rows = summarize_maps(map_ids, samples=args.samples, seed=args.seed)
    sort_keys = {
        "mean": lambda row: row.value_mean,
        "p50": lambda row: row.value_p50,
        "p90": lambda row: row.value_p90,
        "id": lambda row: -row.map_id,
    }
    rows.sort(key=sort_keys[args.sort], reverse=True)

    if args.format == "csv":
        _write_csv(rows, args.top)
    elif args.format == "json":
        print(
            json.dumps(
                [asdict(row) for row in rows[: args.top]],
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    else:
        _write_markdown(rows, args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
