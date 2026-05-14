# `BidMap.txt` column schema

Reverse-engineered from the 21-column TSV. Confidence labels: ★ = confirmed
by cross-reference with another table; ☆ = inferred from row patterns,
not yet cross-checked.

| col | name (ours) | type | confidence | notes |
|---:|---|---|:---:|---|
| 0 | `map_id` | int | ★ | PK |
| 1 | `name` | str | ★ | display name |
| 2 | `description` | str | ★ | flavour text |
| 3 | `name_key` | str | ☆ | i18n key, `bid_map_N_{id}` |
| 4 | `area_icon_key` | str | ☆ | `ui_map_icon_area_{nn}` (43 distinct) |
| 5 | `name_key_alt` | str | ☆ | duplicate of col 3 |
| 6 | `desc_key` | str | ☆ | i18n key, `bid_map_D_{id}` |
| 7 | `category` | int | ☆ | 9 distinct values (101–105, 201, ...); likely region/area class |
| **8** | `sub_pool_weights` | list[[map_id, weight]] | ★ | only the "未知" anthology maps have entries; leaf maps store `[[]]`. Routing: pick a sub-map weighted by these, use that map's `drop_pool_id`. |
| 9 | `value_tier_ui` | str | ☆ | `ui_value_{low,lower,medium,higher,high}` — 5 tiers |
| 10 | `rounds_total` | int | ☆ | 10/15/20/25/30 — monotonic with tier |
| **11** | `entry_fee_silver` | int | ★ | `[1, 1, N]` where (1, 1) = currency(银币), N silver cost; 0 = free |
| 12 | `entry_requirement` | json | ☆ | `[[1, hero_id, 1]]` — possibly required hero unlock |
| 13 | `round_caps` | list[int] | ☆ | 5 numbers, all equal per row (40/50/60); per-round cap of *something* |
| **14** | `starting_budget_silver` | int | ★ | `[[1, 1, N]]` — bidding budget granted on entry |
| 15 | (unused) | — | ★ | always `[[]]` |
| **16** | `drop_ref` | `[9999, drop_pool_id, items_min, items_max]` | ★ | **the critical column.** Top-level Drop pool id + items-per-session range. |
| 17 | `mode_flag` | int | ☆ | 1/2/4 (3 distinct) |
| 18 | `bid_price_ladder` | list[int] | ☆ | `[2000,1600,1300,1100,0]` or `[0,0,0,0,0]` — per-round price tiers |
| 19 | `round_categories` | list[int] | ☆ | `[102,103,103,104,105]` — per-round category hint |
| 20 | `icon_id` | str | ☆ | `iconmap_{n}` |

## Tier structure

The same map theme appears at up to 3 difficulty tiers:

| theme prefix | tier 2 (low) | tier 3 (mid) | tier 4 (high) |
|---|---|---|---|
| 21xx 快递 | ✓ (7 maps) | ✓ (7) | — |
| 22xx 仓库 | ✓ (5) | ✓ (5) | — |
| 23xx 集装箱 | ✓ (10) | ✓ (10) | — |
| 24xx 别墅 | ✓ (10) | ✓ (10) | ✓ (10) |
| 25xx 沉船 | ✓ (10) | ✓ (10) | ✓ (10) |
| 26xx 隐秘拍卖会 | ✓ (1) | — | — |

Total: **105 maps**. Different tiers of the same theme share their
**`drop_pool_id`** (so they pull from the same loot universe) but
differ in `entry_fee_silver`, `starting_budget_silver`, `rounds_total`,
and `items_per_session_*`.

## Drop pool indirection (important!)

A map's `drop_pool_id` rarely points directly to a leaf pool of real
items. The Drop graph is multi-level:

```
BidMap.col[16].drop_pool_id  ──►  top container pool (type=1)
                                  │
                                  ▼ entry.category == 9999 (recurse)
                                  ▼
                              quality-distribution pool
                                  │
                                  ▼
                              category × quality blind-box
                                  │
                                  ▼
                              leaf pool: entry.category != 9999
                                          (real Item.txt id)
```

Concrete trace for map **2101** (`未知快递`):

```
map 2101  drop_pool_id = 2101  (col[16])
  pool 2101  "未知品质掉落"  type=1  4 entries → pool 2001 (weights 5000/3000/2000/1000)
    pool 2001  "未知品质筛选"  6 entries → pools 101101..101501 (quality 1–5+)
      pool 101101  "未知品质1"  10 entries → pools 1011..1081 (category × quality 1)
        pool 1011  "家具品质1"  52 leaf entries → real items (cat=101)
```

`bidking_lab.simulation.basic_mc.flatten_pool` walks this graph and
returns a flat `{leaf_item_id → effective_probability}` distribution
for MC sampling.
