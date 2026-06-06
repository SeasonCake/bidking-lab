# `BidMap.txt` column schema

Reverse-engineered from `Tables/BidMap.txt`. Current raw game data
(`fileVersion=300`, checked 2026-06-06) uses 23-column rows; the parser
still accepts the historical 21-column form. Confidence labels: ★ =
confirmed by cross-reference with another table; ☆ = inferred from row
patterns, not yet cross-checked.

Historical 21-column rows map old `col[8]` to current `col[9]`, and old
`col[9+]` to current `col[10+]`. In the current 23-column schema,
`drop_ref` is `col[17]`; current `col[16]` is an empty placeholder in the
audited rows.

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
| 8 | `v300_flag_a` | int | ☆ | current v300 has `1` in 105 rows and `0` in 20 rows; `0` is concentrated in `2511-2520` and `4511-4520`. Parser ignores it. |
| **9** | `sub_pool_weights` | list[[map_id, weight]] | ★ | only the "未知" anthology maps have entries; leaf maps store `[[]]`. Routing: pick a sub-map weighted by these, use that map's `drop_pool_id`. |
| 10 | `value_tier_ui` | str | ☆ | `ui_value_{low,lower,medium,higher,high}` — 5 tiers |
| 11 | `rounds_total` | int | ☆ | 10/15/20/25/30 — monotonic with tier |
| **12** | `entry_fee_silver` | int | ★ | `[1, 1, N]` where (1, 1) = currency(银币), N silver cost; 0 = free |
| 13 | `entry_requirement` | json | ☆ | `[[1, hero_id, 1]]` — possibly required hero unlock |
| 14 | `round_caps_candidate` | list[int] | ☆ | 5 numbers, all equal per row (40/50/60). 2026-06-06 audit: correlates with settlement item count better than `drop_ref` max, but is not confirmed as the final item-count cap. |
| **15** | `starting_budget_silver` | int | ★ | `[[1, 1, N]]` — bidding budget granted on entry |
| 16 | (unused) | — | ★ | observed as `[[]]` in audited v300 rows |
| **17** | `drop_ref` | `[9999, drop_pool_id, items_min, items_max]` | ★ | Top-level Drop pool id + sampler item draw range. Current evidence shows this max is not the final settlement inventory item-count cap for prior-stressed 24xx/25xx/2601 slices. |
| 18 | `mode_flag` | int | ☆ | 1/2/4 (3 distinct) |
| 19 | `bid_price_ladder` | list[int] | ☆ | `[2000,1600,1300,1100,0]` or `[0,0,0,0,0]` — per-round price tiers |
| 20 | `round_categories` | list[int] | ☆ | `[102,103,103,104,105]` — per-round category hint |
| 21 | `icon_id` | str | ☆ | `iconmap_{n}` |
| 22 | `v300_flag_b` | int | ☆ | observed as `0` in audited rows; parser ignores it |

## 2026-06-06 capacity audit notes

Current `data/raw/fileVersion`, `data/raw/tables/fileVersion`, and
`filelist.txt` all report version `300`; all 125 current `BidMap.txt`
rows have 23 columns. Representative prior-stressed rows:

```text
map 2601: col[14]=[60,60,60,60,60], col[17]=[9999,2601,22,44]
map 2501: col[14]=[50,50,50,50,50], col[17]=[9999,2501,22,44]
map 2405: col[14]=[50,50,50,50,50], col[17]=[9999,2405,20,40]
```

`DropEntry.n_min/n_max` does not currently explain the conflict: audited
reachable Drop graph edges for the top prior-stressed 24xx/25xx/2601 maps
have `n_min=n_max=1`, so the current sampler possible item-count max
remains equal to `drop_ref.items_max`.

Raw latest settlement inventory item ids are covered by the reachable
Drop universe except for known temporary blue zodiac activity ids
`1306003..1306014` in the audited slices. These activity extras explain a
small item-universe gap but not the full count gap, because settlement
truth still exceeds both `drop_ref.items_max` and sometimes the
`round_caps_candidate`. The 2026-06-06 after-zodiac audit confirms this:
in the default 441-session archive, sessions above `drop_ref.items_max`
drop from 196 to 172 after subtracting zodiac extras, and sessions above
`round_caps_candidate` drop from 81 to 59. The remaining gap still needs
settlement expansion/session-capacity semantics or version timing evidence.

The 2026-06-06 settlement payload audit adds one protocol-level clue:
0x002D payload `field[4]` behaves like the final settlement grid/slot
block. In the default archive, its top-level slot count is usually 250 for
24xx maps and 300 for 25xx/26xx maps; occupied slots/raw item candidates
match the parsed final inventory count in 439/441 files. That supports the
parser/truth count as final occupied settlement slots, but it still does
not identify which slots came from base Drop, activity overlay, or another
server-side expansion mechanism.

The bucketed capacity audit added on 2026-06-06 shows the prior-stressed
94-row set all has `v300_flag_a=1`; therefore col[8] does not explain the
current `hard_capacity_conflict` / `lower_bound_under_truth` rows. It
remains a useful activity/overlay clue for the 2511-2520 and 4511-4520
rows, not a promotion signal.

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

The historical v1 profile counted **105 maps**; current fileVersion 300
has 125 rows. Different tiers of the same theme share their
**`drop_pool_id`** (so they pull from the same loot universe) but
differ in `entry_fee_silver`, `starting_budget_silver`, `rounds_total`,
and `items_per_session_*`.

## Drop pool indirection (important!)

A map's `drop_pool_id` rarely points directly to a leaf pool of real
items. The Drop graph is multi-level:

```
BidMap.col[17].drop_pool_id  ──►  top container pool (type=1)
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
map 2101  drop_pool_id = 2101  (current col[17])
  pool 2101  "未知品质掉落"  type=1  4 entries → pool 2001 (weights 5000/3000/2000/1000)
    pool 2001  "未知品质筛选"  6 entries → pools 101101..101501 (quality 1–5+)
      pool 101101  "未知品质1"  10 entries → pools 1011..1081 (category × quality 1)
        pool 1011  "家具品质1"  52 leaf entries → real items (cat=101)
```

`bidking_lab.simulation.basic_mc.flatten_pool` walks this graph and
returns a flat `{leaf_item_id → effective_probability}` distribution
for MC sampling.
