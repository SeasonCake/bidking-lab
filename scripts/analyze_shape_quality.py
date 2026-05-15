"""Analyze shape × quality × category distribution in drop pools."""
from __future__ import annotations

import io
import sys
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bidking_lab.extract.bid_map_table import load_bid_map_table
from bidking_lab.extract.drop_table import load_drop_table
from bidking_lab.extract.item_table import load_item_table
from bidking_lab.simulation.basic_mc import flatten_pool

T = Path(__file__).resolve().parent.parent / "data" / "raw" / "tables"
items = load_item_table(T / "Item.txt")
drops = load_drop_table(T / "Drop.txt")
maps = load_bid_map_table(T / "BidMap.txt")

CAT_NAMES = {
    101: "古董", 102: "珠宝", 103: "时尚", 104: "数码", 105: "医疗",
    106: "武器", 107: "家居", 108: "食品", 109: "书画", 110: "能源",
}
QUAL_NAMES = {0: "无色", 1: "白", 2: "绿", 3: "蓝", 4: "紫", 5: "金", 6: "红"}

for map_id in [2407, 2505, 2301]:
    m = maps[map_id]
    fp = flatten_pool(m.drop_pool_id, drops, items)
    if not fp.item_ids:
        continue

    print(f"\n{'='*70}")
    print(f"Map {map_id}: {m.name}")
    print(f"{'='*70}")

    # Shape distribution
    shape_data: dict[tuple[int, int], dict] = defaultdict(
        lambda: {"prob": 0.0, "value_sum": 0.0, "count": 0}
    )
    for iid, prob in zip(fp.item_ids, fp.probabilities):
        it = items[iid]
        key = (it.shape_w, it.shape_h)
        shape_data[key]["prob"] += prob
        shape_data[key]["value_sum"] += prob * it.value
        shape_data[key]["count"] += 1

    print(f"\n--- Shape distribution ---")
    print(f"{'WxH':>5s} {'items':>5s} {'prob%':>7s} {'E[value]':>10s} {'area':>4s}")
    for (w, h), d in sorted(shape_data.items(), key=lambda x: -x[1]["prob"]):
        area = w * h
        ev = d["value_sum"] / d["prob"] if d["prob"] > 0 else 0
        print(f"{w}x{h}   {d['count']:>5d} {d['prob']*100:>6.1f}% {ev:>10,.0f} {area:>4d}")

    # Quality × area cross-tab
    q_shape: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for iid, prob in zip(fp.item_ids, fp.probabilities):
        it = items[iid]
        area = it.shape_w * it.shape_h
        q_shape[it.quality][area] += prob

    areas = sorted({items[i].shape_w * items[i].shape_h for i in fp.item_ids})
    print(f"\n--- Quality × Area (prob%) ---")
    header = f"{'qual':>6s}"
    for a in areas:
        header += f" {a:>5d}"
    print(header)
    for q in sorted(q_shape):
        line = f"{QUAL_NAMES.get(q, str(q)):>6s}"
        for a in areas:
            line += f" {q_shape[q][a]*100:>4.1f}%"
        print(line)

    # Category distribution
    cat_prob: dict[int, float] = defaultdict(float)
    for iid, prob in zip(fp.item_ids, fp.probabilities):
        it = items[iid]
        cat = it.tags[0] if it.tags else 0
        cat_prob[cat] += prob

    print(f"\n--- Category distribution ---")
    for cat, p in sorted(cat_prob.items(), key=lambda x: -x[1]):
        print(f"  {CAT_NAMES.get(cat, str(cat)):>4s}: {p*100:.1f}%")

    # Big items (area >= 6) by quality
    print(f"\n--- Big items (area >= 6) ---")
    big_items = []
    for iid, prob in zip(fp.item_ids, fp.probabilities):
        it = items[iid]
        if it.shape_w * it.shape_h >= 6:
            big_items.append((it, prob))
    big_items.sort(key=lambda x: -x[0].value)
    for it, prob in big_items[:10]:
        print(f"  {it.shape_w}x{it.shape_h} q={it.quality}({QUAL_NAMES[it.quality]}) "
              f"v={it.value:>8,} p={prob*100:.2f}% {it.name}")
