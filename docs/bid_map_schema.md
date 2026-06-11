# `BidMap.txt` column schema

Reverse-engineered from `Tables/BidMap.txt`. The current schema uses
23-column rows in both the v300 table audited on 2026-06-06 and the local
v303 table synced on 2026-06-08; the parser still accepts the historical
21-column form. Confidence labels: ★ =
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
| 7 | `category` | int | ☆ | region/area class. v303 leaves this blank for old shipwreck `2501-2520` and old sealed shipwreck `4501-4520`; parser infers only those blanks as `105` / `305` from map family and still rejects other blank categories. |
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

The raw-column capacity candidate audit added on 2026-06-06 compares
count-sized BidMap numeric atoms against the 441-session settlement truth.
Among semantically plausible capacity columns, `col[14]` is still the
closest count candidate: it covers `unique_non_temp_item_id_count` in
420/441 rows and fails exactly the 21 `unique_round_cap_overflow_after_temp`
rows. `col[17]` drop-ref covers only 332/441 unique-count rows and fails
109 rows. Neither `col[14]` nor `col[17]` covers unique settlement cells
(`col[14]` covers 7/441, `col[17]` covers 0/441). Non-capacity columns
such as `category_id`, `entry_requirement`, and `round_category_hints`
can be numerically larger than item count, but they are schema ids/hints,
not settlement capacity fields, and still do not explain cells.

The sub-pool cohort audit added on 2026-06-06 classifies maps as
`leaf`, `weighted_parent`, or `self_only` from `sub_pool_weights`. Unique
round-cap overflow appears in both leaf maps (14 rows) and weighted
parents (7 rows), while self-only 2601 has none. Therefore the remaining
unique round overflow is not explained by an anthology parent/sub-map
routing mistake.

The source-semantics audit added on 2026-06-06 keeps `col[14]`
(`round_caps_candidate`) and `col[17]` (`drop_ref`) in audit-only status.
For the 21 `unique_round_cap_overflow_after_temp` rows, 0x002D payload
raw candidates and occupied slots match final inventory in 21/21 files,
non-zodiac Drop-universe missing count is 0/21, and the rows span multiple
days/sessions/maps. Three rows also have external source confirmation
(public total or direct full action). This supports server-side settlement
expansion / session-capacity source semantics over a hard local BidMap cap.
At that time the local v300 filelist listed `Tables/Activity.txt` while
the local table was absent, so an external overlay table remained a
minimal undecidable alternative, but not an observed non-zodiac
item-universe gap.

## 2026-06-08 v303 / 2026-06-11 v308 activity-table note

After rerunning `scripts/copy_game_tables.ps1` against the local game
install, raw local tables report `fileVersion=303`. `Activity.txt`,
`Map.txt`, and `RankMap.txt` are available and decode with the same
base64 table decoder. `Activity.txt` has 6 rows / 16 columns and appears
to describe activity entry/UI metadata, not the shipwreck red-conversion
drop odds.

After the 2026-06-11 game update, the original local game install under
`C:\xiangmuyunxing\steamapps\common\BidKing\BidKing_Data\StreamingAssets`
reports `fileVersion=308`. `Item.txt`, `BidMap.txt`, `Activity.txt`,
`Map.txt`, and `Condition.txt` differ from the previous repo raw snapshot.
`Item.txt` includes the 0611 red/item additions such as `1016007`
`决赛指定用球`, `1036006` `世界冠军奖杯`, `1036007` `“退钱”手举牌`,
`1036008` `传奇球星签名球衣`, and `1076007` `土豆服务器`.

The v303 `BidMap.txt` has 165 rows. It adds 40 rows, including
`2521-2530` and `4521-4530`. Those activity maps are present in BidMap and
use `drop_ref` pairs `22-44`, but their referenced `Drop` pools are still
missing from the unchanged `Drop.txt`:

```text
activity_range=2521-2530 bidmap_present=10 drop_present=0 drop_missing=10
activity_range=4521-4530 bidmap_present=10 drop_present=0 drop_missing=10
```

Therefore v303 removes the "missing BidMap" part of the activity-lane
uncertainty, but it does not provide the activity drop/overlay mechanism.
Until the corresponding `Drop` pools, remote overlay table, or server
source rule is recovered, 252x/452x activity rows must stay separated from
default prior calibration and formal promotion evidence.

The v308 audit keeps the same activity boundary: `BidMap.txt` and
`RankMap.txt` contain `2521-2530` / `4521-4530`, but `Drop.txt` is
unchanged and still lacks those activity pools. The parser therefore
applies a narrow family fallback when shipwreck-family `col[7]` is blank:
`2501-2530 -> 105` and `4501-4530 -> 305`. It does not treat activity
`drop_ref=252x` as a usable Drop prior; live replay keeps using the
explicit old-shipwreck activity alias when BidMap is present but Drop is
missing.

As of the 2026-06-11 v308 rebuild, `items_droppable.json` is generated
from item ids reachable by walking `BidMap.drop_pool_id` through
`DropEntry.category == 9999` pool references, then filtering to physical
auction collectibles (`quality > 0`, `value > 0`, `shape_w > 0`,
`shape_h > 0`). This keeps full `items.json` available for explicit
item_id settlement/replay lookup while preventing non-map-reachable or
non-physical table rows from entering MC priors. The audit example is
`120006-120009` (`青龙` / `白虎` / `朱雀` / `玄武`): they are present in
`Item.txt` and referenced by Drop pool `1001`, but have q0/cells0/value0
and are not map-reachable, so they remain outside `items_droppable.json`.
The five 0611 red/item additions are valid `Item.txt` rows but currently
have no local `Drop.txt` weight references; their activity probabilities
remain unresolved until a recovered overlay/server rule or later table
snapshot supplies that source.

`Activity.txt` row `10007` points to `activity_des_10007`; the decoded
`Language.txt` description names the eligible activity map families and
mentions the "Refund" placard, Official Final Match Ball, and "all four"
limited collectibles for higher-tier scenes. It does not provide numeric
drop weights and does not directly name `1076007` `土豆服务器`, so that row
is item/settlement lookup evidence only until a drop source is recovered.

The 2026-06-11 DLL audit found that `Scripts.dll.bytes` is a 4-byte XOR
(`ryrs`) encoded .NET assembly. After decoding, `GameServerDemo.Utils.DoDrop`
still resolves drops through `Table_Drop.getBygroup_id`, `weight_type`, and
`items_list`; no hard-coded v308 item ids or activity weight overlay were
found. `data/processed/activity_drop_shadow_prior.json` is therefore a
separate **shadow-only** fitted prior: it estimates candidate leaf weights from
current map-reachable q6 items using a log(value)->log(weight) fit plus
similar-item median weights. It is useful for replay/audit experiments, but it
is not formal Drop evidence and must not be merged into `items_droppable.json`.
Its `impact_guard` also keeps formal use and drop-rate validation disabled;
tests assert that the five fitted v308 targets remain absent from both
`items_droppable.json` and every map-level `flatten_pool()` formal prior.

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
