# bidking-lab · 项目进度与路线图

> **用途**：新对话/新协作者的起点文件。阅读本文即可了解项目全貌、当前状态、下一步方向。  
> **相关文件**：`OBSERVATIONS.md`（技术发现日志）、`TROUBLESHOOTING.md`（踩坑记录）、`docs/project_vision.md`（原始架构设计）。

---

## 项目定位

`bidking-lab` 是 Steam 游戏 **The Bid King**（竞拍之王）的**本地数据驱动概率分析库**。

### 双重目标

| 维度 | 目标 | 当前状态 |
|---|---|---|
| **实际游玩价值** | 量化"选哪张图、用哪个英雄、带什么道具"的最优策略 | ✅ 地图期望值、英雄排名已完成；装箱/道具搭配待做 |
| **简历/GitHub 展示** | 展示数据工程 + 概率模型 + 可视化能力 | ✅ 2个notebook已完成，可在GitHub直接渲染 |

### 不做的事

- **不是外挂/自动化**（那是 nql1314/bidking-booooot 在做的）
- **不做 OCR/ML 拟合**（掉率在 Drop.txt 里是白盒，直接抽样）
- **不重新分发游戏资源**（`data/raw/` 永远 gitignore）

---

## 架构概览

```
Layer 3 (表现层)  notebooks / Streamlit UI        [~25%]
       ↑
Layer 2 (计算层)  MC / 英雄模型 / 鲁棒估价 / 推断引擎 / 装箱模型  [~62% Phase 1A MVP ✅]
       ↑
Layer 1 (数据层)  Base64解码 → pydantic schema    [~95%]
```

### 目录结构

```
bidking-lab/
├── src/bidking_lab/
│   ├── extract/          # 每张表一个模块：tables.py, item_table.py, drop_table.py, bid_map_table.py
│   ├── simulation/       # basic_mc.py, bidding.py, hero_skills.py, hero_value.py, robust_value.py
│   ├── inference/        # ✅ display.py, quality_priors.py, observation.py (Phase 1A MVP)
│   ├── data/             # quality.py 等辅助
│   └── config.py
├── data/
│   ├── raw/tables/       # 游戏原始 Tables/*.txt (gitignored)
│   └── processed/        # 派生 JSON (committed): items.json, maps.json, heroes.json 等
├── notebooks/            # 01_map_value_distribution, 02_hero_ranking
├── scripts/              # 探查/分析/demo 脚本
├── tests/                # 105 tests (pytest)
├── docs/                 # project_vision.md, bid_map_schema.md, hero_skill_schema.md
├── PROGRESS.md           # ← 本文件
├── OBSERVATIONS.md       # 技术发现日志 (6个checkpoint)
└── TROUBLESHOOTING.md    # 踩坑记录
```

### 技术栈

Python 3.13 · pydantic v2 · numpy · matplotlib + seaborn + pandas · pytest · pip editable install

---

## 已完成的核心模块

### 1. 数据层（Layer 1）

**游戏数据格式**：`Tables/*.txt` = Base64 编码的 UTF-8 TSV，全部 11 张表列数一致。

| 表 | 列 | Schema | 关键字段 |
|---|---|---|---|
| Drop.txt | 5 | `DropPool` + `DropEntry` | 608个池，4层嵌套递归树 |
| Item.txt | 38 | `Item`（13字段） | id, name, quality(0-6), value, **shape_w, shape_h** |
| BidMap.txt | 21 | `BidMap`（17字段） | 105张图，drop_pool_id, 经济参数, **round_category_hints** |
| BattleItem.txt | 6 | `BattleItem` | 64个道具 |
| Hero.txt | 21 | `Hero`（基础） | 20个英雄 |
| Cabinet.txt | 14 | 已探查 | 6×7网格，12种柜子 |

**关键机制**：Drop 池是 4 层嵌套：`map pool → 品质分布 → 分类×品质盲盒 → 叶子池`。  
`flatten_pool()` 递归展平为 `{item_id → 有效概率}` 扁平分布。

### 2. 计算层（Layer 2）

#### Monte Carlo 基础模型
- `simulate_map()`：单场物品价值期望/方差/分位数
- 结果：沉船(~71万) > 别墅(~46万) > 集装箱(~26万) > 仓库(~10万) > 快递(~5万)
- 同主题不同难度档位**共用同一drop pool**，只是经济参数（入场费/预算/轮次）不同

#### Bidding 经济模型
- `simulate_session()`：含预算、入场费、NPC底价、bid_factor
- **简化决策**：明暗拍 drop pool 完全一样、预算约束在绝大多数场景不生效 → 核心模型不区分明暗

#### 英雄技能模型 v2（timing-aware）
- 20个英雄的技能 → `SkillEffect` DSL（信息类型 × 分类过滤 × 品质过滤 × 时间）
- **核心改进**：v2 加入 `available_at_round` + `TIMING_WEIGHTS`（R1=1.0 → R5=0.05）
- 估算公式：非线性三段（≥0.5 → 80%真值, ≥0.2 → 40%真值, <0.2 → 均值）

#### Robust 估价（Checkpoint #7）
- `robust_value.robust_session_value` 默认剔除 **value ≥ 100万 且 area ≤ 3** 的"小而贵陷阱"
- 别墅高仓 -4.8% / 沉船大仓 -5.2% / 快递集装箱 0%
- 长尾红物名单（14 件 > 100 万）+ 形状指纹字典已就绪
- `winsorize` 工具用于 notebook 视觉去尾

### 3. 表现层（Layer 3）

- `notebooks/01_map_value_distribution.ipynb`：5主题 session value 小提琴图 + 分档对比 + 品质分布
- `notebooks/02_hero_ranking.ipynb`：20英雄×5地图 热力图 + v1/v2对比 + Top-5 柱状图

---

## 核心分析结论

### 当前聚焦的 2 英雄（Phase 1A 测试范围，2026-05-15 进一步收窄）

| 英雄 | 信息维度 | 道具协同方向 |
|---|---|---|
| **艾莎(103)** | 轮廓**渐进**（R1蓝→R2绿→R3白） | 配 X品均格 + X品估价 反推品质/价值 |
| **伊森(208)** | 轮廓**全品质**（R1 五件 + 每轮渐进） | 配**珍品均格 + 珍品估价** 联立反算红物件数 |

**为什么只 2 个**：艾莎/伊森都是 OUTLINE 系，"看到形状但不知品质/价值"——意味着两人共用同一套推断引擎（差别只在 R1 揭示物品的子集大小）。这让 Phase 1A 的实现路径单一、可复用。  
玛丽亚/索菲（直接报价 + 品质揭示）路线**暂停**，等 Phase 1A 跑通后再回来扩展。

**实战道具搭配（用户提供）**：
- 默认：3 张白绿 + 1 张蓝
- 伊森专属：珍品均格 + 珍品估价（联立反算红物件数）
- 绿色均格类：便宜但**显示整数时几乎白用**（信息量瞬间归零）

### 地图自带先验（Checkpoint #7）

`BidMap.round_category_hints` 是 5 元素列表，每轮拍卖前 UI 预告的分类（`0` = 无提示）：

| 主题 | 提示数 | 模式 |
|---|---|---|
| 21xx 快递 / 22xx 仓库 | 5 个 | 全提示，入门 |
| 23xx 集装箱 | 3 个 | R1/R3/R5 |
| 24xx 别墅 | 2 个 | R1+R3 |
| 25xx 沉船 | 1 个 | 仅 R1，道具/英雄价值最高 |

- R1 100% 给提示；值域只有 `{102医疗, 103时尚, 104武器, 105珠宝}`
- 明拍 / 暗拍提示完全一致（再次印证物品分布无差异）

### 形状指纹字典（Phase 1A 直接可用）

```
5×4  → 唯一: 墙面涂鸦墙 (蓝, 8880)         ★ 单点识别
6×3  → 唯一: 单人郊游快艇 (金, 10.7万)      ★ 单点识别
4×4  → 5 件 (4 红/金 + 1 蓝石狮子)         ★ 80% 红/金
3×4 / 3×5 / 5×3 / 6×1 → 全是金红, 无混淆
```

详见 `scripts/probe_distinctive_shapes.py`。

### 长尾红物降权（Checkpoint #7）

14 件 value > 100 万的红物中，**9 件形状 1×1 / 1×2 / 2×1 / 1×3**（金陵折扇1937万、非洲之心1314万、黑王子300万、羊脂玉251万、超级跑车钥匙、百年人参 …）。  
这些物品池里数百件便宜物共存，**形状不可识别** → `robust_session_value` 默认归零。

**保留**的"大而贵"红物（形状强信号）：复苏呼吸机3×3、相控阵雷达3×4、蓝鳍金枪鱼3×5、翡翠屏风4×4、永乐大典2×2 等。

### 仓库大小先验

| 仓库 | 总格数 | 决策含义 |
|---|---|---|
| 小仓 | < 70 | 极保守，几乎不上道具 |
| 中仓 | < 110 | 白绿道具为主 |
| 大仓 | > 130 | 才考虑金道具 |

玩家用 `总仓储空间` 道具（金色）可直接读总格数；推断引擎把它作为强先验。

**形状特例**：看到 5×4 时 → 总格数减 20（这格属于已知的低价值蓝物"墙面涂鸦墙"）。

### 英雄排名（v2 timing-aware，别墅2407为代表）

| Tier | 英雄 | marginal% | 核心能力 | 实战评价 |
|---|---|---|---|---|
| **S** | 玛丽亚(108) | +23.6% | R1 白绿蓝 VALUE | "老奶奶"，直接报价覆盖70%+物品 |
| **S** | 艾莎(103) | +22.4% | R1蓝→R2绿→R3白 OUTLINE | 渐进覆盖所有低品质轮廓 |
| **S** | 索菲(107) | +21.6% | R1 5品质 + 每轮2品质 | 通用型品质渐进 |
| **S** | 加布里埃拉(104) | +20.2% | 每轮随机2品质 | 通用型品质渐进 |
| A | 伊森(208) | +13.7% | R1 5轮廓 + 渐进 | "扫格子"，R5全轮廓来太晚 |
| A | 伊万(205) | +12.5% | 武器+能源 OUTLINE | 沉船上更强 |
| A | 娜奥米(106) | +11.6% | 时尚+数码 OUTLINE | 分类特化 |
| ... | ... | ... | ... | ... |
| **D** | 艾哈迈德(204) | -0.4% | COUNT_HINT | 统计量不帮选品，但有"场次筛选"价值 |
| **D** | 拉文(301) | -0.6% | R5全品质 | 太晚，模型正确反映了 |
| **D** | 维克托(209) | -0.8% | 金紫计数 | 仅场次级信息 |

**重要发现**：
- 玛丽亚只覆盖白/绿/蓝，但这些占物品70%+，高覆盖率弥补了"只看低端"的局限
- 艾莎的 OUTLINE（0.3分）看似弱，但结合**形状→价值强相关**的发现，实际信息量可能接近0.5-0.6
- 伊森的"扫格子"策略在形状→价值映射下比模型预估更有价值（模型待升级）

### 形状→价值映射（Checkpoint #6 新发现）

```
Item.txt col[7] = WH编码（十位=宽, 个位=高）
Cabinet grid = 6列 × 7行 (42格)

形状面积 → 平均价值（别墅池）:
  1格(1×1):  8,000   占52.6%   ← 大量低价白绿物品
  4格(2×2): 19,000   占20.4%
  9格(3×3): 34,000   占 2.6%
 16格(4×4):218,000   占 0.3%   ← 几乎全是紫金红
  ≥6格的大物品: 几乎全是红色品质, 价值10万-155万
```

**结论**：**看到轮廓就能估价**。4×4 = 必拍，1×1 = 大概率白绿，3×3 = 可能蓝紫金。  
这让伊森和艾莎的 OUTLINE 能力比当前模型估算的更强。

### 分类分布（因地图而异）

- 别墅：医疗(20.8%) > 武器(13.7%) > 时尚(12.7%)
- 沉船：武器(19.3%) > 能源(17.0%) > 医疗(13.3%)
- 集装箱：比较均匀，每类 8-12%

### 战斗道具（64个）

关键道具类型：
- **随机抽检(N)**：完全揭示N件随机物品（N=1/2/4/6/8/10）
- **宝光N鉴**：随机N件品质（N=2/4/6/8/10/15）
- **分类鉴影**：特定分类全部轮廓（10种分类各一个）
- **至宝系列**：最高品质1件的轮廓/格数/价值/完整信息
- **巨物系列**：格子最多1件的轮廓/品质/价值/完整信息
- **N格均价**：占位N格物品的平均价值（N=1/2/3/4/6）

---

## 下一步路线图（优先级排序）

### Phase 1A：信息推断引擎（MVP 完成 2026-05-15，沉船 R4 demo 复现 35/14 ✓）

**核心问题（2 英雄聚焦版）**：

```
给定 N 个 shape 已知的占位物品 (来自艾莎/伊森的 OUTLINE)
    + K 个道具读数 (X品均格 / X品扫描 / X品估价 / 等)
    + 仓库大小先验
    + drop pool 先验
→ 反推每个占位的 (quality, value)，输出 top-3 候选
```

**关键洞察（用户提供，已验证）**：
- 均格类道具的小数显示泄漏分母信息（"2.9" 精确除尽，"2.90" 含尾零 = 约到的，分母不整除10）→ 反推 (品质×件数×总格数)。
- 游戏显示**最多 3 位小数**，偶尔会显示 3 位（如 "2.345"）。
- **显示整数 = 几乎白用**（多解空间巨大），故绿色均格道具的边际价值期望要计入"显示整数概率"折扣。
- 多解时用仓库大小先验排序，给玩家 **top-3 候选**。

**MVP 现状（已落地）**：
- ✅ `display.py`：截断显示规则（floor at 2dp，尾零按精确除尽规则保留）+ 候选枚举 + 仓库剪枝（26 tests）
- ✅ `quality_priors.py`：per-cell value 中位数常量（紫 2500 / 金 9400 / 红 50000；红巨物 30000 分流）+ `estimate_total_cells`（15 tests）
- ✅ `observation.py`：`SessionObs` / `QualityBucketObs` UI dataclass + 暴力枚举引擎 + 巨物优先剪枝 + composite ranking
- ✅ `scripts/demo_shipwreck_r4_inference.py`：复现"均格 2.5 + 估价 86,490 → 35 格 14 件"top-3 推断

**Phase 1A 余下**：
- ⏳ 巨物数量分级输入（1 / 2-3 / 4+）+ 品质级可见性规则（艾莎只能看紫色巨物，伊森可看全部）
- ⏳ `OutlineObservation`（艾莎/伊森看到 N 个形状）
- ⏳ Quality / RoundCategory / HeroSkill observation
- ⏳ joint posterior（当前是按品质 greedy，存在多 bucket 相互制约的精度损失）
- ⏳ `notebooks/03_inference_demo.ipynb` 可视化

**地基（已完成）**：
- ✅ `BidMap.round_category_hints` 入 schema
- ✅ `robust_session_value` 长尾降权
- ✅ 形状指纹字典数据就绪

### Phase 1B：形状→价值估价模型

**目标**：利用 shape→value 的强相关性，升级英雄模型。  
**做什么**：
- 建 `shape_value_prior`：给定 (shape_w, shape_h, map_id) → value 分布
- 升级 `compute_info_score()`：OUTLINE 信息类型的得分从固定 0.3 改为查表
- 重跑英雄排名，观察伊森/艾莎是否上升

Phase 1A 的 `OutlineObservation` 实质上就是 shape→value 的"使用方"，1A 完成后 1B 大部分顺带落地。

### Phase 2：英雄+道具组合优化

**目标**：量化"英雄X + 道具A + 道具B"的最优搭配。  
**做什么**：
- 建道具效果模型（类似 SkillEffect 但一次性）
- 交叉模拟：对每个英雄 × 热门道具组合 × 地图，跑 contrast MC
- 输出推荐表：给定地图，推荐英雄+道具组合

**道具约束（实战经济性）**：
- 默认配置：**3 张白绿 + 1 张蓝**（成本低）
- 金色道具仅在确认是大仓时才用（蓝及以上道具是动态定价）
- 鉴影（分类轮廓蓝）实战性价比低，搜索时降低优先级

**重点组合**（用户讨论确认）：
- 玛丽亚 + 至宝估价 + 随机抽检(2)：精确估价路线
- 艾莎 + 至宝寻踪 + 宝光四鉴：轮廓+品质交叉路线
- 伊森 + 宝光四鉴 + 随机抽检(2)：格子扫描+品质补充路线

### Phase 3：装箱模型

**目标**：回答"这些物品能不能装进 6×7 柜子"。  
**做什么**：
- 6×7 网格 + 矩形物品的 2D bin packing
- 贪心/启发式放置（玩家也不可能算最优解）
- 让伊森/艾哈迈德的"格数"信息有量化价值

**可行性**：✅ 物品形状数据已在 Item.txt col[7]，不需要 Unity 逆向。

### Phase 4：交互 UI（Streamlit）

**目标**：下拉框选地图/英雄/道具 → 实时MC + 推荐。  
**价值**：简历展示的终极形态；玩家可直接使用。

### Phase 5：模型精化（低优先）

- Sampling-without-replacement 修正（当前 with-replacement 高估方差）
- 艾哈迈德"场次筛选"独立指标（不改选品模型，单独算"避免亏本局"概率）
- 条件概率："已经看到了 [A, B, C]，剩下出 X 的概率？"（Q2）

---

## 关键设计决策记录

| 决策 | 理由 | Checkpoint |
|---|---|---|
| 不区分明暗拍 | drop pool 完全一样、预算不瓶颈 | #4 |
| 快递是票制 | 1000银币=10张票，不是传统入场费 | #4 |
| 英雄模型用 timing discount | R5信息几乎无价值，v1高估了拉文 | #5 |
| 估算用非线性三段而非线性插值 | 线性让低分全覆盖英雄（艾哈迈德）不合理地高 | #5 |
| 物品形状用 WH 两位数编码 | Item.txt col[7] 直接存储，无需逆向 | #6 |
| 装箱用贪心不用精确算法 | 在线决策场景，玩家不可能算最优解 | #6 |
| 聚焦 4 英雄（玛丽亚/索菲/艾莎/伊森）| 加布里埃拉与索菲重叠；伊森在 shape→value 后潜力高 | #7 |
| col[19] 入 schema（round_category_hints）| 地图自带 1–5 个免费分类约束，是推断引擎的零成本先验 | #7 |
| robust_value 默认剔小贵 | 9 件 ≤3 格红物形状不可识别，纳入只污染估价 | #7 |
| 推断引擎用拒绝采样 | 玩家观测维度多但样本量小，REJECT 直观且可调采样数 | #7 |
| 均格小数尾零=约的 | 用户实测：2.90 暗示分母不整除10（如 32/11）| #7 |

---

## 提交历史

> 每次 commit 之后追加（append-only，不删改旧条目）。最新在最上面。  
> 用 `git log --oneline` 看简明列表；下面的展开版用于回顾设计决策。

### `16f2191` — C-4.2: Outline observation module — Aisha-style bucket pinning (2026-05-15)

新增 `inference/outline.py`，覆盖艾莎和伊森 outline 技能（按 2026-05-15 用户口述：艾莎 R1=白, R2=绿, R3=蓝, R4=紫；伊森 R1 揭示 5 个随机分类的轮廓，R5 揭示全部）。

- `OutlineObs(shape, round_seen, quality_hint, hero)`：UI 输出的单位类型，每个 cabinet 轮廓一个。
- `make_aisha_outlines` / `make_ethan_outlines`：每英雄构造器；艾莎的 quality_hint 自动从 `AISHA_ROUND_QUALITY` 取，伊森的 quality_hint=None（无品质信息，**hover 也不显示分类**——用户实测确认）。
- `build_shape_index({item_id: Item}) → {(quality, w, h): [Item]}`：shape → 候选物品反查表。
- `candidates_for_outline`：给定 outline + shape index → 兼容 shape+quality 约束的物品集。
- `derive_bucket_from_outlines(quality, outlines, shape_index)`：艾莎模式——她揭示某品质全部轮廓时，可以**精确**锁定 count、total_cells，并从每形状候选物的 min/max value 推出 tight value_range。

**警示**：本模块**不动** `hero_skills.py`。用户的实战艾莎（4 轮，白起）与 `heroes.json` 描述（3 轮，蓝起）不一致；先保留旧的 SkillEffect ranking，等游戏内截图验证后再统一改。详见 OBSERVATIONS.md Checkpoint #8。

11 个新单测，总 132（之前 121）。

### `b07940c` — C-4.1: refine huge-item input — band system + hero visibility rules (2026-05-15)

2026-05-15 设计 session 中用户提的 UX 细化：

- `HugeBand`：离散桶输入（`"none"` / `"1"` / `"2-3"` / `"4+"`），让玩家从下拉里选，不用算清精确件数。
- `HUGE_CELLS_PER_QUALITY`：每品质巨物面积常量（紫 16, 金 18 只此一件, 红 16）。
- `aisha_can_observe_huge()`：编码英雄不对称——艾莎只看紫色巨物，伊森看全部。session validator 在艾莎模式下检测到金/红 band 时报警。
- `ETHAN_DEFAULT_LOADOUT` / `AISHA_DEFAULT_LOADOUT`：标准道具组合常量，给将来 UI 默认值用（伊森 4 便宜+1 金；艾莎 2 便宜+2 金，偏估价类）。
- `QualityBucketObs.{huge_count_range, huge_cells_per_item, min/max_huge_cells}`：驱动暴力枚举过滤的 helper。
- 引擎：huge-band 过滤的实现是"存在整数 h ∈ [min, max] 使 h ≤ count 且 h × huge_per_item ≤ total_cells"——比硬编码 huge_count 更灵活。

16 个新单测，总 121（之前 105）。

### `4a56555` — C-4: Phase 1A inference engine MVP — display rule + priors + demo (2026-05-15)

- `inference/display.py`：truncate-at-2dp 显示模型 + 候选枚举 + 仓库剪枝，已用截图观察校准（26 单测）。
- `inference/quality_priors.py`：per-cell 价值中位数（紫 2500, 金 9400, 红 50000 默认 / 30000 巨物），用沉船 drop-weighted p50 验证；红色巨物分流（15 单测）。
- `inference/observation.py`：UI 形状的 `SessionObs` + `QualityBucketObs` dataclass + 暴力候选枚举器，按 capacity / huge-floor / avg-cells display rule 三层剪枝，按品质 top-K 复合排序输出。
- `scripts/demo_shipwreck_r4_inference.py`：端到端 demo，从 2026-05-15 截图（avg=2.5, 估价=86,490）复原紫品 (35 cells / 14 items)。
- `scripts/probe_value_per_cell.py`：drop-weighted p50 探针，验证用户启发式数字。
- `PROGRESS.md`：测试数上调到 105，Phase 1A 标记 MVP 完成。

### `f7176b3` — C-3: Phase 1A foundation — round category hints, robust value, hero v2 polish (2026-05-15)

跨 Checkpoint #5/#6/#7 的整合 commit。

- **#5**：SkillEffect / hero_skills.py timing 模型 + hero_value.py contrast MC 精化
- **#6**：`notebooks/01_map_value_distribution.ipynb` + `02_hero_ranking.ipynb`；Item.txt shape_w/shape_h 字段（col[7] WH 编码）；`scripts/probe_item_shapes.py` / `analyze_shape_quality.py`
- **#7**：
  - `BidMap.col[19]` 入 schema 为 `round_category_hints`，用 `probe_round_categories.py` 验证（R1 100%, R3 ~67%, R5 ~35%, R2/R4 ~18%；明暗拍提示一致；密度与难度对应：快递/仓库 5 → 沉船 1）
  - `simulation/robust_value.py`：剔除"小而贵"长尾（value ≥ 100 万 AND area ≤ 3）；影响：别墅 -4.8%, 沉船 -5.2%, 快递/集装箱 0%
  - 形状指纹字典：5×4 = 唯一蓝物（涂鸦墙，8880），6×3 = 唯一金物（游艇，10.7 万），4×4 = 4 红/金 + 1 蓝石狮子（唯一混淆）
  - `compare_raw_vs_robust.py`：side-by-side raw vs robust E[session]
  - `PROGRESS.md`：项目全局入口，当前聚焦 4 英雄（玛丽亚/索菲/艾莎/伊森），道具预算（3 白绿 + 1 蓝），仓库分档，Phase 1A 推断引擎路线图

用户决策固化：英雄 scope 排除加布里埃拉（与索菲重叠），保留伊森（与形状信息协同）；道具预算默认 3 白绿+1 蓝，仅大仓 >130 才考虑金道具；均格小数尾零=约的（用户实测：2.90 暗示分母不整除 10，如 32/11），打开均格类道具的小数 leakage 反推路径。

测试 53 → 64。

### `9430bcc` — C-1: hero skill marginal value model + contrast MC (2026-05-14)

- `simulation.hero_skills`：DSL 风格的 SkillEffect 模型覆盖全部 20 英雄。每个英雄技能拆为 `SkillEffect(info_type, category 过滤, quality 过滤, max_items, per_round, rounds)`。`compute_info_score()` 给特定英雄+场局返回 [0,1] 的 per-item info 分。
- `simulation.hero_value`：contrast MC，对比英雄存在 vs 不存在。每个 trial 抽一场物品，测理性玩家在英雄给信息后比随机出价多赚多少。`HeroValueResult` 报 baseline_mean / hero_mean / marginal_value / %。
- `docs/hero_skill_schema.md`：全部 20 英雄技能按 info type / category 过滤 / 时间分类。

关键发现（10K 试验, 4 地图）：
- 玛丽亚（108, 白/绿/蓝 value 揭示）稳居 top-3，marginal +23–116%
- 艾莎（103, 渐进品质揭示）+ 伊万（208, 广轮廓）是通用型强者
- 艾哈迈德（204, 计数/均值）+0% — 统计聚合对选品几乎无用
- 维克托（209, 计数提示）所有地图最弱
- 英雄价值在快递最高（+100%，rounds << items），沉船最低（+15%，rounds ≈ items）

测试 46 → 52。

### `ce455a6` — Add observations.md project log + simplification decisions (2026-05-14)

新增 `docs/observations.md`：按 checkpoint 记录关键发现、设计决策、所用技术、项目状态。覆盖 Checkpoint 1-4：drop pool 递归、BidMap schema 拆解、MC 验证结果、出价模型发现。

关键简化决策固化：明拍/暗拍共享 drop pool，预算约束极少触发，所以核心模型不区分拍卖模式。

后续 `a6554a4` 把它从 docs/ 挪到 repo root。

### `1d424cf` — C-2: budget-aware bidding model + auction_mode (open/sealed/training) (2026-05-14)

BidMap schema v2：
- `auction_mode`（open/sealed/training）从 map_id 前缀 + col[17] mode_flag 派生。用户确认：2xxx=open, 4xxx=sealed, 3xxx=training
- `mode_flag` (col[17]) + `bid_price_ladder` (col[18]) 入 schema
- maps.json 重新生成

`simulation.bidding` 模块：
- `BidPolicy`：可配 bid_factor + NPC 底价区间
- `simulate_session()`：每 trial 循环，玩家出 bid_factor*value，bid ≥ NPC 底价就赢，从预算扣
- `SessionSummary`：gross mean / net profit (mean/std/quantile) / win rate / 预算使用率 / ROI
- 关键发现：别墅明暗拍（200 万 vs 100 万预算）在典型 bid_factor 下 net profit 几乎一致——预算约束只在 bid_factor ≥ 0.50 的暗拍侧触发。沉船预算两边一样所以明暗拍数字 identical。

脚本：`demo_bidding_compare.py`, `sensitivity_bid_factor.py`, `compare_map_tiers.py`

测试 41 → 46。

### `60de342` — Layer 2 kickoff: full BidMap schema + first working Monte Carlo (2026-05-14)

Layer 1 收尾：
- 把 `BidMap` 从 3 字段 summary 扩到 13 字段 schema，覆盖 drop_pool 路由、入场费、起始预算、items-per-session 范围、轮数、合集子池权重（完整列映射见 `docs/bid_map_schema.md`）
- 用新字段重新生成 `data/processed/maps.json`

Layer 2 v1：
- 发现 Drop.txt 池是多级嵌套（顶层 → 品质 → 盲盒 → 叶子），`category == 9999` 表示"这条 entry 引用另一个池，递归"；写入 `docs/bid_map_schema.md`
- 新增 `bidking_lab.simulation.flatten_pool(pool_id, drops, items)` 遍历池图，返回扁平 `{leaf_item_id → 有效概率}` 分布
- 新增 `bidking_lab.simulation.simulate_map(map_id, n_trials=10_000)` Monte Carlo：每 trial 抽 K ~ Uniform[min, max] 件，从扁平池有放回采样，返回 mean / std / q05 / q50 / q95
- 内联记录 caveat：with-replacement、无英雄技能、无出价机制

测试 35 → 39。

Demo：`scripts/demo_simulate_maps.py` 给 13 张地图排序——沉船 > 别墅 > 集装箱 > 仓库 > 快递（期望值递减，变异系数单调递增）匹配设计直觉。

依赖：加 `numpy>=1.26`。

### `1f39cc4` — Publish derived JSON datasets so the package runs without the game (2026-05-14)

Plan A 落地：克隆这个 repo 的人立刻拿到可用的 items / battle_items / heroes / maps 数据。原始游戏文件保持 gitignored。

新增 Layer 1 解析器：
- `data/quality.py`：共享 `Quality` 枚举 (0..6 → 白绿蓝紫金红) + 中英文颜色名 helper
- `extract/item_table.py`：`Item` pydantic 模型 + parser；命名 11 个已确认列，保留 raw_row 给 27 个未定列。quality 验证 0..6
- `extract/battle_item_table.py`：`BattleItem` 带 quality_color + effect_type_label 派生字段
- `extract/hero_table.py`：`Hero`（id / name / skill 文本 + raw_row）
- `extract/bid_map_table.py`：`BidMapSummary`（id / name / desc + raw_row）。完整子池解析等里程碑 B

新脚本 `scripts/build_processed_data.py`：从 `data/raw/tables/*.txt` 读，写派生 JSON；raw_row 不入 JSON 以减小体积。

提交进 git 的产出（`data/processed/*.json`）：
- `items.json` — 1132 件 ~520 KB
- `items_droppable.json` — 883 件 ~425 KB
- `battle_items.json` — 64 个 ~18 KB
- `heroes.json` — 20 个 ~4 KB
- `maps.json` — 105 张 ~25 KB

.gitignore：保持 `data/raw/**` 和 `data/processed/tables/**` 在外（字节等价游戏文件），但显式允许派生 JSON。README "Data sources" 节说清边界。

测试 → 28。

### `df9b7dc` — Confirm Item.txt quality (col[8]) and value (col[9]) via cross-check (2026-05-14)

Drop.txt entries 交叉验证 Item.txt 找到 883 物品的 loot universe，然后用玩家给的游戏内观察验证 quality + value 映射：

- col[8] = quality。7 档 (0..6)，0 是"无品质 / 系统物"，1..6 映射白绿蓝紫金红。每升一档中位 value 是上一档的 ~5-10 倍，单调
- col[9] = item value（游戏显示的"X 万" = col[9] / 10000）。验证案例：1006001 金陵折扇 → 19,371,213（游戏内 1900w）；1056013 非洲之心 → 13,145,200（游戏 1314w）
- Drop entry category 字段也搞清：1=货币, 6=柜子, 7=礼盒, 8/19=英雄试用卡, 11=战斗道具, 12/14/15=头像/皮肤变种, 101-110 是 Layer-2 真正关心的 10 类家具/文物分类, 9999 = 跨池元分类别名

- `scripts/analyze_loot_universe.py`：可复用 Join Drop × Item；打印 loot universe 大小、品质直方图、每品质 value 统计、每品质样本物品、category → item_ids 拆分
- `docs/item_table_schema.md`：col[8] / col[9] 由"较可能"提升为"确定"；附上正式品质颜色表 + category 含义表
- `docs/project_vision.md`：交叉验证步骤标 done；下一步 `parse_item_table()` v1 + `data/processed/items.json` 导出

### `017e0d1` — Add dump_processed_tables.py (2026-05-14)

产出本地 artifacts（gitignored），表能直接在 Excel / VS Code 打开不用重跑解码器：

- `data/processed/tables/<Name>.tsv`：每张 `Tables/*.txt` 解码到 UTF-8（BOM 前缀让 Excel 正确渲染中文），每表一个 TSV
- `data/processed/tables/_with_headers/{Drop,Item}.tsv`：同样行但加表头（来自 `docs/item_table_schema.md` 暂定名）；`_?` 后缀标未确认列
- `data/processed/drop_entries.csv`：Drop.txt entries 摊平到每 (pool_id, entry_idx, category, item_id, n_min, n_max, weight) + weight_share_in_pool 一行，方便 join Item 行交叉检查

可重跑：`copy_game_tables.ps1` 之后再跑一次就刷新。

### `33c15c5` — Add Drop.txt schema parser + Item.txt column profiler (2026-05-14)

Layer 1 进度：drop 池完全 typed，item 表 schema 映射到只用数据本身就能站得住脚的程度（暂无游戏 UI 交叉检查）。

- `extract/drop_table.py`：`DropEntry`, `DropPool` pydantic 模型；`parse_drop_row` / `parse_drop_table` / `load_drop_table`。容忍空 `[]` 和退化 `[[]]` entry。原始 weight 不归一化，留给模拟侧合并
- `tests/test_drop_table.py`：7 单测，覆盖 happy path / 空池 / 重复 pool_id 检测 / JSON 畸形 entry / 列数错
- `scripts/summarize_drop_table.py`：真实 Drop.txt 烟雾测试（608 池, 类型直方图 {1: 48, 2: 560}, top category=11 有 4402 entry）
- `scripts/profile_item_columns.py`：Item.txt 每列 distinct / type / range / 样本，给 schema 逆向当指南
- `docs/item_table_schema.md`：暂定列映射，三级置信度（certain / probable / unknown）。指出**网格形状不在 Item.txt**（col[14] 全 1132 行只有 3 个 distinct 值，所以 footprint 住在别处——估计是模型 prefab）
- `docs/project_vision.md`：checklist 更新，下一步是 Item.txt 列交叉验证（用 Drop.txt item_id join）

测试 → 16。

### `133cd74` — Add Tables/*.txt decoder (Base64 → UTF-8 TSV) + project vision doc (2026-05-14)

`BidKing_Data/StreamingAssets/Tables/*.txt` 原来是纯 Base64 包裹 UTF-8 TSV，不是加密 blob。Layer 1（数据层）不用任何逆向即可达成。

- `extract/tables.py`：`decode_table_text`, `iter_table_rows`, `load_table_rows`, `assert_uniform_columns`, `discover_tables`
- `tests/test_tables.py`：7 单测（base64 往返 / UTF-8 / 锯齿性）
- `scripts/probe_tables.py`：hex+base64+解压三件套烟雾探针
- `scripts/decode_table_preview.py`：单表 TSV 预览（Windows 上 stdout 走 UTF-8）
- `scripts/decode_all_tables.py`：全表扫，每表打印行/列形状
- `docs/project_vision.md`：3 层架构, KPI 问题 Q1-Q5, 明确反目标（不做 OCR / 自动化 / ML 拟合 drop 表）
- `docs/upstream_references.md`：外部 repo 笔记，保持本地不入 vendor
- `README.md`：指向 `project_vision.md` 而非内联 stub
- `TROUBLESHOOTING.md`：节 7（解码结果）+ 节 8（PS UTF-8 控制台）
- `.gitignore`：`external_references/**` 不入仓

### `10539c8` — Initial commit: bidking-lab scaffold (2026-05-14)

仓库骨架：config / extract stubs / scripts / docs 基础结构。

---

## 对话历史摘要

本项目在一个长对话中完成（约 6 个 checkpoint），对话中涉及：

1. **数据解码**（Base64→TSV, 列名逆向, schema 建模）
2. **MC 模型演进**（basic → bidding → hero v1 → hero v2 timing）
3. **用户提供的游戏知识**：
   - 明暗拍物品分布相同
   - 预算约束极少生效（除快递外）
   - 快递是票制
   - 艾哈迈德在实战中"很垃圾"（模型验证了这一点）
   - 伊森的"扫格子"策略、艾莎的渐进轮廓、玛丽亚("老奶奶")的估价能力
4. **用户的战略方向**：
   - 筛选到 3-5 个核心英雄（玛丽亚/艾莎/伊森 + 索菲/加布里埃拉）
   - 结合格子大小形状和品质来估价
   - 英雄+道具组合优化（限1金+1蓝）
   - 最终做成简历可放的 GitHub 项目

---

## 本地路径

### 项目仓库

```
c:\xiangmuyunxing\biancheng\2026\bidking-lab\
```

### 游戏安装路径

```
C:\xiangmuyunxing\steamapps\common\BidKing\
├── BidKing.exe
└── BidKing_Data\
    └── StreamingAssets\
        ├── Tables\               ← 所有游戏数据表 (Base64 编码的 TSV)
        │   ├── Drop.txt          ← 掉落池 (608池, 4层嵌套)
        │   ├── Item.txt          ← 物品 (1132件, 38列)
        │   ├── BidMap.txt        ← 地图 (105张, 21列)
        │   ├── Hero.txt          ← 英雄 (20人, 21列)
        │   ├── BattleItem.txt    ← 战斗道具 (64个, 6列)
        │   ├── Cabinet.txt       ← 柜子 (12种, 14列)
        │   ├── Condition.txt     ← 条件 (未解析)
        │   ├── Constant.txt      ← 常量 (未解析)
        │   ├── Item_Type.txt     ← 物品分类 (未解析)
        │   ├── ItemRestock.txt   ← 补货 (未解析)
        │   └── LevelUp.txt       ← 升级 (未解析)
        ├── filelist.txt
        └── fileVersion
```

**配置**：代码通过 `bidking_lab.config.get_game_root()` 自动检测，也可设 `$env:BIDKING_GAME_ROOT` 覆盖。  
**同步**：`.\scripts\copy_game_tables.ps1` 将 Tables/*.txt 复制到 `data/raw/tables/`（gitignored）。

### 已复制到项目中的数据

```
data/raw/tables/         ← 游戏原始表 (gitignored, 需本地游戏)
data/processed/          ← 派生 JSON (committed, 无需游戏即可用)
├── items.json           ← 全部 1132 物品
├── items_droppable.json ← 883 件可掉落物品
├── battle_items.json    ← 64 个战斗道具
├── heroes.json          ← 20 个英雄
└── maps.json            ← 105 张地图
```

---

## 快速恢复指南（给新对话）

```powershell
# 环境
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
pip install -e .
pytest -q  # 应该 105 passed

# 关键入口
python scripts/demo_hero_value.py --trials 10000        # 英雄排名
python scripts/demo_simulate_maps.py                    # 地图价值
python scripts/analyze_shape_quality.py                 # 形状×品质分析
python scripts/compare_raw_vs_robust.py                 # raw vs robust 估价对比
python scripts/probe_round_categories.py                # col[19] 提示密度全扫描
python scripts/probe_rare_red_items.py                  # 长尾红物概率
python scripts/probe_distinctive_shapes.py              # 形状指纹字典
python scripts/probe_value_per_cell.py                  # 每格价值中位数（priors 校准）
python scripts/demo_shipwreck_r4_inference.py           # Phase 1A 推断 demo

# 需要先读的文件
# 1. 本文件 (PROGRESS.md)
# 2. OBSERVATIONS.md                              — 7个 checkpoint 技术细节
# 3. src/bidking_lab/simulation/hero_skills.py    — 英雄技能DSL
# 4. src/bidking_lab/simulation/hero_value.py     — 对照MC
# 5. src/bidking_lab/simulation/basic_mc.py       — 基础MC + flatten_pool
# 6. src/bidking_lab/simulation/robust_value.py   — 长尾降权 (新)
# 7. src/bidking_lab/extract/bid_map_table.py     — BidMap schema (含 round_category_hints)
# 8. src/bidking_lab/extract/item_table.py        — Item schema (含 shape)
```
