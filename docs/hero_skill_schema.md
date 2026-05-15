# Hero Skill Classification (for MC modeling)

Each hero reveals partial information about session items. For the
**marginal value model**, what matters is: how much information does
a hero provide that helps a rational player *avoid overpaying for junk*
and *identify high-value items to bid on*?

## Information types

| Code | Meaning | Value to player |
|---|---|---|
| `outline` | 显示轮廓 — shows the item's shape/silhouette | Medium: lets you estimate size/category |
| `quality` | 显示品质 — shows quality color (白/绿/蓝/紫/金/红) | **High**: quality strongly correlates with value |
| `value` | 显示价值/总价值 — shows actual silver value | **Very high**: directly reveals what matters |
| `count` | 显示数量 — shows how many items of some filter | Low-medium: narrows expectations |
| `avg_cells` | 显示平均格数 — shows average grid cells per quality | Low: indirect shape proxy |
| `full_info` | 显示完整信息 — outline + quality + value | **Maximum** |

## Per-hero skill breakdown

### Tier 1 (col[4]=1) — 10 heroes

| ID | Name | Timing | Category filter | Info revealed | Items affected |
|---|---|---|---|---|---|
| 101 | 法蒂玛 | R1-R5 progressive | 文玩古董 | R1: top-value outline+quality; R2-R5: 3 outline/quality alternating | ~13 items over 5 rounds |
| 102 | 陈美 | Start | 珠宝矿藏 + 时尚潮流 | outline (all) | All items in 2 categories |
| 103 | 艾莎 | R1-R3 progressive | All (by quality) | R1: blue outline; R2: green outline; R3: white outline | All blue+green+white items |
| 104 | 加布里埃拉 | Per-round | Random unknown | outline + quality (2/round) | ~2×rounds = 10-60 items |
| 105 | 塔蒂安娜 | Start | 时尚潮流 | quality + outline (all) | All items in 1 category |
| 106 | 娜奥米 | Start | 时尚潮流 + 数码电子 | outline (all) + gold/red count sum | All in 2 categories + count hint |
| 107 | 索菲 | Start + per-round | Random | R1: 5 quality; then 2 quality/round | 5+2×(rounds-1) items |
| 108 | 玛丽亚 | Start | 白/绿/蓝 quality items | total value (per quality) + quality shown | Very high: value of 3 quality tiers |
| 109 | 海琳娜 | Start + per-round | 医疗药品 | quality (all) + 2 outline/round | All medical quality + progressive outlines |
| 110 | 伊莎贝拉 | Start | Best-1 + 珠宝矿藏 | top-1 outline + 4 珠宝 outline | 5 items total |

### Tier 2 (col[4]=2) — 9 heroes

| ID | Name | Timing | Category filter | Info revealed | Items affected |
|---|---|---|---|---|---|
| 201 | 乔治 | Start | 武器装备 | quality + outline (all) | All weapons |
| 202 | 卡洛斯 | Start + per-round | 家居日用 + 数码电子 | outline (all) + 2 quality/round | All in 2 categories progressive |
| 203 | 莱昂纳德 | Start | 食品烹饪 + 文玩古董(2) | quality (all food) + 2 antique quality | All food + 2 antiques |
| **204** | **艾哈迈德** | **R1-R5** | **All (by quality)** | **R1: total count; R2: gold avg cells; R3: purple avg cells; R4: blue avg cells; R5: green+white total count** | **Statistical aggregates** |
| 205 | 伊万 | Start | 武器装备 + 能源交通 | outline (all) | All in 2 categories |
| 206 | 武田宏志 | Start + per-round | 书籍绘画 | outline (all) + 2 quality/round | All books progressive |
| 207 | 吴起灵 | R1-R4 progressive | 文玩古董 | R1: count; R2: outline; R3: quality; R4: 1/3 full info | Deep focus on 1 category |
| 208 | 伊森 | Start + per-round + R5 | Random types | R1: 5 random type outlines; per-round: known-quality→outline; R5: ALL outlines | Wide late-game reveal |
| 209 | 维克托 | Start | All (紫+金) | count of purple + gold combined | Single aggregate number |

### Tier 0 (col[4]=0) — 1 hero (free/starter)

| ID | Name | Timing | Info | Notes |
|---|---|---|---|---|
| 301 | 拉文 | R5 only | quality (all) | Very late, limited decision value |

## Modeling approach for MC

For a first-pass model, we don't simulate per-round decisions.
Instead we model the **information advantage** as: given what a hero
reveals, how well can the player distinguish high-value items from
low-value ones?

**Proxy metric**: for each hero, compute the fraction of total session
value that falls within items the hero can identify (via quality or
value revelation). A hero who reveals quality of ALL items lets the
player perfectly rank by expected value per quality tier. A hero who
only reveals outlines has less decision power.

**Scoring weights** (for v1):
- `value` revealed → 1.0 (perfect info on that item)
- `quality` revealed → 0.7 (quality is strongly correlated with value)
- `outline` revealed → 0.3 (helps but doesn't distinguish within quality)
- `count` / `avg_cells` → 0.1 (weak statistical hints)
- `full_info` → 1.0
