"""Analyze per-footprint average item values for size-avg tool threshold tuning.

Uses:
- Fatbeans settlement inventories (338 historical samples) as truth for
  ``size_avg = sum(value) / count`` per footprint (1/2/3/4/6 cells).
- Map drop-pool MC samples as a simple prior on footprint counts and values.
- Named anchor items (永乐, 羊脂, 人参, 飞机匣, 黑王子, 黑盒, etc.).

Stdout only; does not change inference. Human tables:
docs/size_avg_interpretation.zh-CN.md
"""

from __future__ import annotations

import argparse
import io
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from bidking_lab.inference.ground_truth import prepare_session_sampler
from bidking_lab.live.fatbeans import _ACTION_SIZE_AVG_VALUE, parse_fatbeans_capture
from bidking_lab.live.monitor import load_monitor_tables

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SIZE_BUCKETS = tuple(sorted(set(_ACTION_SIZE_AVG_VALUE.values())))

ANCHOR_NAME_SUBSTRINGS = (
    "永乐大典",
    "羊脂白玉籽",  # ~252万，1x2=2格（口语「羊脂玉/270万」指此物，非羊脂玉璧）
    "百年人参",
    "私人直升机黑匣子",
    "黑王子红宝石",
    "豪宅管理用黑盒",
)


@dataclass(frozen=True)
class SizeSessionStats:
    map_id: int
    file_name: str
    counts: dict[int, int]
    avgs: dict[int, float]


def _default_sample_paths() -> tuple[Path, ...]:
    root = ROOT / "data" / "samples" / "fatbeans"
    if not root.exists():
        return ()
    return tuple(sorted(root.rglob("*.json")))


def _size_stats_from_inventory(
    inventory: tuple,
    items: dict,
) -> tuple[dict[int, int], dict[int, float]]:
    by_size: dict[int, list[int]] = defaultdict(list)
    for inv in inventory:
        item = items.get(int(inv.item_id))
        if item is None:
            continue
        cells = int(inv.cells) if inv.cells else item.shape_w * item.shape_h
        by_size[cells].append(int(item.value))
    counts = {cells: len(vals) for cells, vals in by_size.items()}
    avgs = {
        cells: sum(vals) / len(vals)
        for cells, vals in by_size.items()
        if vals
    }
    return counts, avgs


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    arr = np.asarray(values, dtype=np.float64)
    return float(np.percentile(arr, p))


def _summarize_values(values: list[float]) -> str:
    if not values:
        return "n=0"
    values = sorted(values)
    return (
        f"n={len(values)} "
        f"p10={_percentile(values, 10):,.0f} "
        f"p50={_percentile(values, 50):,.0f} "
        f"p90={_percentile(values, 90):,.0f} "
        f"max={values[-1]:,.0f}"
    )


def _collect_settlement_stats(
    paths: tuple[Path, ...],
    items: dict,
) -> tuple[list[SizeSessionStats], Counter[str]]:
    sessions: list[SizeSessionStats] = []
    skip = Counter()
    for path in paths:
        try:
            events = parse_fatbeans_capture(path)
        except Exception as exc:
            skip[f"parse_error:{type(exc).__name__}"] += 1
            continue
        settlement = None
        map_id = None
        for state in events.states:
            if state.map_id is not None:
                map_id = int(state.map_id)
            if state.inventory_items:
                settlement = state
        if settlement is None or map_id is None:
            skip["no_settlement"] += 1
            continue
        counts, avgs = _size_stats_from_inventory(settlement.inventory_items, items)
        if not avgs:
            skip["empty_inventory"] += 1
            continue
        sessions.append(
            SizeSessionStats(
                map_id=map_id,
                file_name=path.name,
                counts=counts,
                avgs=avgs,
            )
        )
    return sessions, skip


def _mc_prior_by_map(
    *,
    maps,
    drops,
    items,
    n_trials: int,
) -> dict[int, dict[int, list[float]]]:
    """Per map_id: lists of per-session avg value per footprint from MC."""
    by_map_avgs: dict[int, dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    by_map_counts: dict[int, dict[int, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for map_id in sorted(maps):
        try:
            sampler = prepare_session_sampler(
                map_id,
                maps=maps,
                drops=drops,
                items=items,
            )
        except Exception:
            continue
        rng = np.random.default_rng(map_id)
        for _ in range(n_trials):
            truth = sampler.sample(rng=rng)
            by_size: dict[int, list[int]] = defaultdict(list)
            for bucket in truth.buckets.values():
                for item in bucket.items:
                    area = item.shape_w * item.shape_h
                    by_size[area].append(int(item.value))
            for cells, vals in by_size.items():
                if not vals:
                    continue
                by_map_counts[map_id][cells].append(len(vals))
                by_map_avgs[map_id][cells].append(sum(vals) / len(vals))
    return dict(by_map_avgs), dict(by_map_counts)


def _anchor_rows(items: dict) -> list[str]:
    rows = ["anchor_items,name,cells,value,quality"]
    for item in sorted(items.values(), key=lambda it: it.value, reverse=True):
        if not any(sub in item.name for sub in ANCHOR_NAME_SUBSTRINGS):
            continue
        cells = item.shape_w * item.shape_h
        rows.append(
            f"{item.item_id},{item.name},{cells},{item.value},{item.quality}"
        )
    return rows


def _recommend_floors(
    settlement_avgs: dict[int, list[float]],
) -> dict[int, float]:
    """Low floor from settlement p10: keep typical sessions, drop near-zero noise."""
    floors: dict[int, float] = {}
    for cells in SIZE_BUCKETS:
        values = settlement_avgs.get(cells, [])
        if not values:
            floors[cells] = 3_000.0
            continue
        p10 = _percentile(values, 10) or 3_000.0
        floors[cells] = float(max(2_000.0, min(12_000.0, p10 * 0.45)))
    return floors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze size-bucket avg values for threshold tuning.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional sample JSON files/dirs (default: data/samples/fatbeans).",
    )
    parser.add_argument(
        "--mc-trials",
        type=int,
        default=400,
        help="MC trials per map for drop-pool prior (default 400).",
    )
    parser.add_argument(
        "--current-floor",
        type=float,
        default=20_000.0,
        help="Current SIZE_AVG_VALUE_SIGNAL_FLOOR for comparison.",
    )
    args = parser.parse_args()

    if args.paths:
        paths: tuple[Path, ...] = ()
        for p in args.paths:
            if p.is_dir():
                paths += tuple(sorted(p.rglob("*.json")))
            elif p.exists():
                paths += (p,)
        paths = tuple(sorted(set(paths)))
    else:
        paths = _default_sample_paths()

    tables = load_monitor_tables()
    items = tables.items
    maps = tables.maps
    drops = tables.drops

    sessions, skip = _collect_settlement_stats(paths, items)
    settlement_avgs: dict[int, list[float]] = defaultdict(list)
    settlement_counts: dict[int, list[int]] = defaultdict(list)
    by_map_settlement: dict[int, dict[int, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for sess in sessions:
        for cells, avg in sess.avgs.items():
            settlement_avgs[cells].append(avg)
            by_map_settlement[sess.map_id][cells].append(avg)
        for cells, count in sess.counts.items():
            settlement_counts[cells].append(count)

    print("=" * 72)
    print("SIZE AVG VALUE THRESHOLD ANALYSIS")
    print("=" * 72)
    print(f"Sample files scanned     : {len(paths)}")
    print(f"Settlement sessions      : {len(sessions)}")
    print(f"Skipped                  : {dict(skip)}")
    print(f"Current signal floor     : {args.current_floor:,.0f}")
    print()

    print("=" * 72)
    print("ANCHOR ITEMS (Item table)")
    print("=" * 72)
    for line in _anchor_rows(items):
        print(line)
    print()

    print("=" * 72)
    print("SETTLEMENT — per-footprint item count per session")
    print("=" * 72)
    for cells in SIZE_BUCKETS:
        print(f"  {cells}cell  {_summarize_values([float(c) for c in settlement_counts[cells]])}")
    print()

    print("=" * 72)
    print("SETTLEMENT — per-footprint avg value (truth size_avg semantics)")
    print("=" * 72)
    for cells in SIZE_BUCKETS:
        vals = settlement_avgs[cells]
        below = sum(1 for v in vals if v < args.current_floor)
        print(
            f"  {cells}cell  {_summarize_values(vals)}  "
            f"below_current_floor={below}/{len(vals)}"
        )
    print()

    print("=" * 72)
    print("SETTLEMENT — tier bands (4cell / 2cell / 1cell)")
    print("=" * 72)
    bands = (
        ("4cell", 4, [(0, 30_000), (30_000, 80_000), (80_000, 500_000), (500_000, 2e9)]),
        ("2cell", 2, [(0, 15_000), (15_000, 50_000), (50_000, 300_000), (300_000, 2e9)]),
        ("1cell", 1, [(0, 10_000), (10_000, 40_000), (40_000, 200_000), (200_000, 2e9)]),
    )
    for label, cells, thresholds in bands:
        vals = settlement_avgs.get(cells, [])
        if not vals:
            continue
        parts = []
        for lo, hi in thresholds:
            n = sum(1 for v in vals if lo <= v < hi)
            parts.append(f"{lo/1e4:.0f}w-{hi/1e4:.0f}w:{n}")
        print(f"  {label}  " + "  ".join(parts))
    print()

    print("=" * 72)
    print(f"MC DROP PRIOR — {args.mc_trials} trials/map (count + avg value)")
    print("=" * 72)
    mc_avgs, mc_counts = _mc_prior_by_map(
        maps=maps,
        drops=drops,
        items=items,
        n_trials=args.mc_trials,
    )
    pooled_mc_avgs: dict[int, list[float]] = defaultdict(list)
    pooled_mc_counts: dict[int, list[int]] = defaultdict(list)
    for map_avgs in mc_avgs.values():
        for cells, vals in map_avgs.items():
            pooled_mc_avgs[cells].extend(vals)
    for map_counts in mc_counts.values():
        for cells, vals in map_counts.items():
            pooled_mc_counts[cells].extend(vals)
    for cells in SIZE_BUCKETS:
        print(
            f"  {cells}cell count/session  "
            f"{_summarize_values([float(c) for c in pooled_mc_counts[cells]])}"
        )
    for cells in SIZE_BUCKETS:
        vals = pooled_mc_avgs[cells]
        print(f"  {cells}cell avg (all maps)  {_summarize_values(vals)}")
    print()

    print("=" * 72)
    print("TOP MAPS — settlement 4cell avg (sessions with 4cell items)")
    print("=" * 72)
    map_4 = [
        (map_id, vals)
        for map_id, by_cells in sorted(by_map_settlement.items())
        if (vals := by_cells.get(4))
    ]
    map_4.sort(key=lambda row: statistics.median(row[1]), reverse=True)
    for map_id, vals in map_4[:12]:
        name = maps[map_id].name if map_id in maps else str(map_id)
        print(f"  map {map_id} {name}  {_summarize_values(vals)}")
    print()

    recommended = _recommend_floors(settlement_avgs)
    print("=" * 72)
    print("REFERENCE TIERS (4cell avg — soft scoring bands, not hard floors)")
    print("=" * 72)
    print("  <30k     mostly cheap 4-cell filler (普通紫/金4格，常被多件稀释)")
    print("  80k-500k plane box / 永乐级 when signal not diluted by many items")
    print("  2cell: 羊脂白玉籽~252万、百年人参~104万 — 用「两格均价」道具，不是四格")
    print("  500k+    black box / ultra (黑盒 ~740万；MC max 4cell avg 可达此档)")
    print()
    print("=" * 72)
    print("RECOMMENDED SIGNAL FLOORS (max(2k, min(12k, settlement_p10*0.45)))")
    print("=" * 72)
    for cells in SIZE_BUCKETS:
        vals = settlement_avgs.get(cells, [])
        kept = sum(1 for v in vals if v >= recommended[cells])
        print(
            f"  {cells}cell  floor={recommended[cells]:,.0f}  "
            f"keeps {kept}/{len(vals)} settlement sessions"
        )
    print()
    print("Suggested Python dict for v2:")
    print("SIZE_AVG_VALUE_SIGNAL_FLOORS = {")
    for cells in SIZE_BUCKETS:
        print(f"    {cells}: {recommended[cells]:.1f},")
    print("}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
