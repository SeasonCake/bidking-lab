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
├── tests/                # 222 tests (pytest)
├── docs/                 # project_vision.md, bid_map_schema.md, hero_skill_schema.md
├── PROGRESS.md           # ← 本文件
├── OBSERVATIONS.md       # 技术发现日志 (12个checkpoint)
└── TROUBLESHOOTING.md    # 踩坑记录 (28条)
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

### 当前聚焦的 2 英雄（Phase 1A 测试范围，2026-05-15 截图校准后）

| 英雄 | 技能名 | 信息维度 | 道具协同方向 |
|---|---|---|---|
| **艾莎(103)** | 遗珍慧眼 | 4 级渐进：R1=白, R2=绿, R3=蓝, R4=紫；**每轮揭示该品质全部物品的轮廓+品质** | 配 X品均格 + X品估价 反推价值（轮廓+品质已固定，缺的是 value） |
| **伊森(208)** | 空间觉知 | R1=随机 5 个 category 的全部物品轮廓（**无品质无 hover 提示**）；R5=全部轮廓 | 配**珍品均格 + 珍品估价** 联立反算红物件数；用地图爆率猜分类 |

**为什么只 2 个**：艾莎/伊森都是 OUTLINE 系（艾莎额外带 QUALITY），都依赖"看到形状后再用道具补 value"，共用同一套推断引擎。玛丽亚/索菲（直接报价 + 品质揭示）暂停。

**校准后的 v2 ranking 变化**：
- **伊森从 A 飙到 S**（别墅 +13.7% → **+20.5%**；沉船跳到 #2 +15.3%）——5 categories 修正后覆盖率翻倍
- **艾莎从 S 略微下调**（+22.4% → +20.3%）——OUTLINE_QUALITY 升档但 R1=白品价值低、R4=紫品 timing 衰减重

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

## 当前剩余工作（用户视角的"还差多少")

| 模块 | 状态 | 备注 |
|---|---|---|
| **艾莎/伊森 核心建模** | ✅ ~95% | 4 级渐进轮廓 + R1/R5 + timing-aware MC 全到位 |
| **推断引擎** | ✅ ~95% | Joint posterior + 仓库剪枝 + 总件数约束 + 巨物分级 + 截断显示规则 |
| **道具 Observation** | ✅ ~90% | 11 件道具登记完整（普良优极珍 × 扫描/估价/均格 + 总仓储）；per-item 接口（抽检/宝光）按用户要求 skip |
| **地图自带信息** | ✅ ~80% | 静态字段（件数 / 预算 / 梯度 / R1+R3 类别提示）已抓取并在 UI 侧边栏展示；动态 hint 由玩家手动填 |
| **可视化 / UI** | ✅ ~90% | Streamlit：价值区间 + bucket 后验 + ROI；**秒/放仓卡片已下线（实验）**；未知形状巨物仍仅记录 |
| **游戏 patch 兼容** | ~0% | 2026-05-15 patch BidMap 21→23 列；parser 还没改；processed maps.json 仍是 patch 前的；runtime 不受影响 |
| **README / 简历包装** | ~30% | PROGRESS / OBSERVATIONS / TROUBLESHOOTING 三件套齐全；缺一份顶层 README pitch + 架构图 + 截图 |

**整体 ~92%**（剩余主要是简历包装而非工程）。

### 用户聚焦：别墅 + 沉船优先（2026-05-15）

- **主玩**：别墅 2407 / 沉船 2510 —— Phase 2 contrast MC 只跑这两张
- **集装箱**：**引擎不细做**，用预算的均值回落即可。玩家选集装箱时 UI 直接显示"E[session] ≈ 26 万银币（从 baseline MC 取均）"；不跑推断引擎、不算英雄边际值
- **快递 / 仓库**：略过（入门图，不是简历亮点目标）
- **网吧（极客改造屋）**：实际是 col[7]=104（别墅类别），drop_pool 跟别墅同源，所以本来就在别墅覆盖范围内

### 2026-05-15 patch 事件图（5 天后下线）

用户 2026-05-15 实测确认：
- 沉船 (2501 等) 是 **drop rate up 的活动图**，**5 天后自动下线**
- 别墅可能有暗改（明面无 up 标识）
- → **不为活动图重写 BidMap parser**，等下线后再判断是否要支持 23-col 重抽取
- 推断引擎本来就跟"具体地图 ID"解耦，玩家在活动期玩这些图也能正常用（手动 hint 输入流程已覆盖）

### 艾莎/伊森 标准道具组合（2026-05-15 校准后）

| 英雄 | 5-tool 标准 | 备注 |
|---|---|---|
| **伊森** | 普品扫描 + 良品扫描 + 精品估价 + 精品均格 + 珍品估价 | 4 便宜 + 1 金；估价道具比扫描便宜，但扫描信息密度更高 |
| **伊森 alt** | 普品扫描 + 良品扫描 + **随机抽检(1)** + 精品均格 + 珍品估价 | 用抽检替换精品估价，换 1 个 category 信息（帮 brute force 估价剪枝）|
| **艾莎** | 抽检2 + 抽检1 + 宝光四鉴 + 珍品估价（或扫描）+ 总仓储空间 | 艾莎技能本身已 pin 死 q=1..4 的轮廓+品质，所以道具偏 reveal-个体型；金品估价或扫描看玩家偏好 |

### 下一开工的优先序

**已完成（C-1 ~ C-26 期间一次性补齐）**：
- ✅ Streamlit UI 完整版（11 件道具 / 6 品质 / 巨物 / 价值分布图 / 秒仓放仓 / ROI / 候选预览 / 地图静态信息面板）
- ✅ Joint posterior（DFS + 仓库剪枝 + 总件数交叉约束）— 替代了 greedy
- ✅ 道具命名修正（优品 / 极品 / 珍品 与游戏一致；新增 q=6 红品道具）
- ✅ ROI 引擎 + 玩家眼估噪声模型（修复总仓储 ROI = 0 的假信号）
- ✅ Snipe gate low-confidence fallback（小仓 / 稀采样不再静默失败）
- ✅ 03_inference_demo + 04_roi_and_snipe + **05_end_to_end_case** 三册 notebook
- ✅ BidMap col 调研结论：动态 hint 不在表里，静态字段（件数 / 预算 / 梯度 / 分类提示）已侧边栏暴露

### 下一步推进 TODO（2026-05-17 用户拍板）

| 状态 | 项 | 说明 |
|------|-----|------|
| ✅ 已完成（C-32） | **P0-B**：`adaptive_filter` fallback 保留 `huge_cells_override` | `_fallback_hard_buckets` + 单测；234 tests |
| **▶ 下一项** | **顶层 README 重写**（可选） | 简历友好 pitch + 架构图 + 一键运行 |
| ⏸ 暂缓 | **P0-A**：秒/放仓（tier / 小红仓门控 / 重开 UI） | 用户决定暂不投入；`_ENABLE_SNIPE_PASS_HINTS=False` 保持；`snipe.py` 仅保留 |
| ✅ 已完成 | P1 文案 + 联合约束枚举放宽 | C-31b |
| ✅ 已完成 | MC 默认 1500、`width` 弃用修复、语法 `\uff08` 修复 | C-31 / c5ceb43 / 029fd29 |
| ✅ 已完成 | 秒/放仓 UI 实验下线 + 参数审计文档 | C-31 |
| ❌ 不做 | P2 均价进 MC | 设计分层，见 OBS #31 / TROUBLESHOOTING #31 |
| ⏸ 暂缓 | P2 ★具体巨物进 MC、P3 未知形状巨物、P3 紫/金 huge 进秒放仓 | 依赖 P0-A 或工作量大 |

**C-32 验收标准（动工后）**：

1. `hard_buckets` 重建 `QualityBucketObs` 时拷贝 `huge_cells_override`（及已有 `huge_band` / `value_sum`）。
2. `tests/` 新增：fallback 路径下 override 不丢失。
3. `pytest` 全绿；实战：小仓 + 仅选 ★金/紫巨物时，激活约束文案仍含 huge 信息（若触发 fallback）。

---

### 推断引擎 backlog（C-31 审计归档）

| 优先级 | 项 | 状态 |
|--------|-----|------|
| P0-A | 秒/放仓 tier / 小红仓 / 重开 UI | ⏸ **用户暂缓** |
| P0-B | fallback 保留 `huge_cells_override` | ✅ **C-32** |
| P1 | 字段作用范围 UI 文案 | ✅ C-31b |
| P1 | 联合约束 ≥4 项枚举放宽 | ✅ C-31b |
| P2 | 均价进 MC | ❌ 不建议 |
| P2 | ★巨物格数进 MC | ⏸ 暂缓 |
| P3 | 未知形状巨物 | ⏸ 暂缓 |
| P3 | 秒/放仓加紫/金 huge | ⏸ 随 P0-A |

**已做（C-31）**：秒/放仓 UI 实验下线；OBSERVATIONS / TROUBLESHOOTING #30–31。

**已做（C-31b）**：P1 字段作用范围 UI 文案；联合约束 ≥4 项时仅放宽枚举 `avg_value` 容差（MC 不变）。

---

**剩余可选项（按性价比降序）**：

1. **顶层 README.md 重写**（简历友好，~1h）
   - 30 秒项目 pitch + 架构图 + Streamlit 截图 + 一键运行
2. **TROUBLESHOOTING.md 补 C-22~C-26 条目**（已在做，~15 min）
3. **per-item Observation 接口**：抽检 N / 宝光 N 鉴
   - 用户明确说"不要做，过度复杂化"。**Skip**。
4. **23 列 BidMap parser**：等 2026-05-15 patch 活动图下线后再判断；不影响 runtime
5. **joint posterior 改 belief propagation**：学术优化，工程价值不高
6. **抽检 ROI 建模**：用户：\"不必要的复杂度\"。**Skip**。

---

## 提交历史

> 每次 commit 之后追加（append-only，不删改旧条目）。最新在最上面。  
> 用 `git log --oneline` 看简明列表；下面的展开版用于回顾设计决策。

### C-32: P0-B fallback 保留 huge_cells_override (2026-05-17)

- `posterior._fallback_hard_buckets`：重建 `QualityBucketObs` 时拷贝 `huge_cells_override`（`value_sum` / `huge_band` 分支）。
- `tests/test_posterior.py::TestFallbackHardBuckets`；`pytest` 234 passed。

### docs: 推进 TODO 拍板 — P0-A 暂缓，下一项 C-32 仅 P0-B (2026-05-17)

- 用户确认：秒/放仓（P0-A）**暂不开发**；`_ENABLE_SNIPE_PASS_HINTS` 保持 `False`。
- 下一里程碑 **C-32**：`adaptive_filter` hard_buckets 保留 `huge_cells_override`（小改，主 MC fallback 一致性）。
- PROGRESS「下一步推进 TODO」+ OBS #31 用户拍板；MC spinner 文案恢复完整表述。
- **本 commit 不含 C-32 代码实现**（文档与规划先行）。

### C-31: 参数审计 + 秒/放仓 UI 实验下线 + MC 默认 1500 (2026-05-17)

- **审计**：紫/金/红 `huge_band` 进 MC；`huge_cells_override` / `avg_cells` / `avg_value` 主要进枚举与分析估算（设计分层，见 TROUBLESHOOTING #31）。
- **UI**：`_ENABLE_SNIPE_PASS_HINTS=False`，与未知巨物同策略；后端 `snipe.py` 保留。
- **UI**：Streamlit `use_container_width` → `width`；MC 默认 **1500**（实战速度与精度平衡）。
- **文档**：OBSERVATIONS Checkpoint #31、PROGRESS backlog 表、TROUBLESHOOTING #30–31。

### C-30: 放仓红约束 + Item-DB boost + ratio 守卫 (2026-05-16)

（见 OBSERVATIONS Checkpoint #N 与 commit `e0c7e47`。）

### C-29: 紫品/金品均价输入 + 紫色 huge 阈值放宽 + MC 滑块三档说明 (2026-05-16)

实战使用反馈三项功能性优化，每项都是"有现成基础设施 + 用户场景频繁但 UI 没暴露"的典型补丁。

**(1) 均价输入字段（`avg_value`）**

游戏里 R3 提示偶尔会直接给「紫品均价 X silver」「金品均价 Y silver」——这是一份独立信息：跟 `value_sum`、`count`、`avg_cells` 都不一样，但能跟它们联立。比如玩家填了 `avg_value=6178 + value_sum=86,490`，引擎能立刻反推 `count ≈ 14`。

实现：
- `QualityBucketObs` 新增 `avg_value: int | None = None` 字段
- `candidates_for_bucket` 加硬过滤层：候选 `(total_cells, count)` 推得的 `implied_avg_value` 需在 ±10%（同时填 `value_sum`）或 ±25%（仅有先验估算）内
- UI 紫品 / 金品 section 6 列布局：cells / count / avg_cells / value_sum / **avg_value** / huge_band
- 全链路自动消费——预览面板、`_build_session` 红品残差、`compute_analytical_estimate` 通过 `candidates_for_bucket` 自动用上

新增测试 3 条（`test_avg_value_filter_with_value_sum_pins_count` / `test_avg_value_filter_rejects_off_target` / `test_avg_value_without_value_sum_uses_loose_pcv_filter`）。

**(2) 紫色 huge 阈值 12 → 10**

实战里玩家提到游戏中能识别为"大件"的紫色物品不止防护盾。查了 `Item.txt` 全表，紫品 ≥12 格物品**只有 1 件**（防护盾 3×4=12, 20,082），但 5×2=10 格的 `加特林重机枪` (31,688) 也是常见的"大紫"且形状唯一可识别。

修法：
- `HUGE_CELLS_PER_QUALITY[4] = 10`（金/红 仍 ≥12）
- `BIG_ITEMS_BY_SHAPE` 新增 `5×2 = 10 格` 行，含 `加特林重机枪` (q=4, unique purple) + `巴雷特狙击枪` (q=5, 67,600)
- `_items_for_quality(q)` 新增 per-quality 阈值过滤：金品下拉**不会**显示 5×2=10 的巴雷特（金品阈值 12），紫品下拉**会**显示 5×2=10 的加特林——保持品质阈值差异下的语义一致
- UI 文案重写「什么算 巨物 / 大件」expander，按品质拆分阈值说明

测试同步：原假设"全部 12 格"的 3 条测试改为反映新阈值（紫 ≥ 10）。

**(3) MC 滑块改 step 200 + 三档说明**

`st.slider` 参数 `(500, 5000, 1000, step=250)` 改为 `step=200`，help 文本拆三档：

- **500** = 快速估算，精度偏低（尾部分布的仓库组合可能匹配不足）
- **1000** = 默认平衡点
- **2000** = 高精度，安静倒可接受（推荐大仓 + 强约束场景）
- **3000-5000** = 冷门大仓 / 严重尾部场景备选

代码改动：`src/bidking_lab/inference/observation.py` (~30 行：avg_value 字段 + 过滤层 + 阈值常量) · `app/streamlit_app.py` (~80 行：UI 6-列布局 + state 接入 + huge 阈值导入 + caption 重写) · `tests/test_observation.py` (3 新测试 + 3 既有测试更新阈值)

测试：222 单测全绿（+3 from C-28）。

---

### C-28: 出价 hint 实战回归一连串修复 + 已识别具体巨物 (2026-05-16)

实战测试一晚发现 5 个独立但互相加强的"上游字段没被消费"bug，以及 1 个新功能。修完整个出价 hint 模块的实战准确度有质变。详细技术分析见 [`OBSERVATIONS.md` Checkpoint #11](OBSERVATIONS.md#checkpoint-11--出价-hint-鲁棒化--已识别具体巨物2026-05-16)，每个 bug 单独入 [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) `#23-#28`。

**Bug 链（一处错引发下游连环错）**：

1. **#23**：`compute_analytical_estimate` 的红品自动推断没检查"非红 bucket 是否填全"——金品没填时残差全部归红 → 估值×5-10 飞天。修法：加 `all_non_red_filled` gate，未填全时按"全金到全红"区间显示。

2. **#24**：7 个数值字段默认 `value=0` 让"未提供"和"确认为零"无法区分。修法：全改 `value=None` + `placeholder="可选"`，配合后端 `if x is not None` 判断。

3. **#25**：`compute_analytical_estimate` 没用 `candidates_for_bucket` 枚举器——紫品 `value_sum=86,490 + huge_band=1` 被估成 12 格，而枚举能算出 35 格。修法：加二次 pass，对 `total_cells is None` 但有其它字段的 bucket 调枚举取 top-1。

4. **#26**：`_build_session` 红品残差也没用枚举——"金品仅填件数=5"贡献 0 格 → 红品错算 32 格 → 后续金品被红品挤光彻底消失。修法：跟 #25 对称，从源头修。

5. **#27**：`HUGE_CELLS_PER_QUALITY` 跟 UI 文案漂移（UI 说 ≥12 格，常量是 16/18）。修成 `{4:12, 5:12, 6:12}`，金品 huge per-cell value 同步上调到 7,000/格。

**新功能：已识别具体巨物**

`huge_cells_override` 字段早就在数据模型里，但 UI 上「巨物数量」选项只有数量段。新版从 `BIG_ITEMS_BY_SHAPE` 自动派生具体物品选项：

```
紫品下拉框：[无 / 1个 / 2-3个 / 4+个 / ★ 防护盾 (12格·20,082) / ★ 雷达 (...)]
金品下拉框：[... / ★ 单人郊游快艇 (18格·106,500) / ★ 重型防弹衣 (12格·74,745) / ...]
```

零额外接线——`huge_cells_override` 已被 `huge_cells_per_item()` 消费，下游推断模块全部自动用上。

「未确认品质巨物」(按形状) 区块明确改为 `🧪 测试功能，暂未接入推断接口` 横幅，避免玩家以为这部分会参与推断。

**实战收益**：

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 仓库 80，未填金品 | 红=19 格、估值 ~100 万 | 「未分配 9 格（金未填）」350K-1M 区间，明确提示 |
| 紫品 value_sum=86,490, huge=1 | 紫=12 格 | 紫=35 格（用户估价直接用） |
| 金品仅填件数=5 | 金=0 格、红=32 格 | 金=22 格、红=10 格 |
| 紫品识别为防护盾 | 紫=12 格 generic | 引擎知道是具体物品 |

代码改动：`src/bidking_lab/inference/posterior.py` (~70 行净增) · `src/bidking_lab/inference/observation.py` (`HUGE_CELLS_PER_QUALITY` 常量) · `src/bidking_lab/inference/quality_priors.py` (`PER_CELL_VALUE_HUGE[5]` 6,000→7,000) · `app/streamlit_app.py` (~150 行：value=None pattern + `_huge_options_for_quality` + `_resolve_huge_selection` + bucket 构造调整 + 未确认巨物 warning)

测试：219 单测继续绿，无新增（修复都是行为正确性，覆盖在既有 dataclass / candidates / posterior 测试里），TROUBLESHOOTING.md 新增 6 条踩坑入档。

---

### C-26: 项目尾巴一次性清理（地图先验面板 + snipe 兜底 + 端到端 notebook + 路线图刷新）(2026-05-15)

用户 23:36 问"项目已经很完善了，后续步骤是什么"。盘点后 4 件可一次清理的"尾巴"打包做掉，全程不引入新依赖、不破坏既有 API。

**(1) BidMap 静态先验调研 + UI 侧边栏面板**

probe `BidMap.txt` 105 行全表后确认：所有有用的**静态**字段（`items_per_session_min/max`, `starting_budget_silver`, `bid_price_ladder`, `round_category_hints`, `value_tier_ui`）pydantic parser 早已抓全，但 Streamlit UI 一个都没显示。**动态**hint（"X 件均价 Y"）则确实如用户先前判断不在表里。

在侧边栏地图选择下方加 `st.expander("📍 地图静态信息（仅参考）")`，一个面板就展示了：
- 件数范围 / 起步预算 / 入场费 / 价值档次
- 轮号分类提示（"R1=武器 / R3=时尚"等）
- 出价梯度

零成本暴露既有信息，玩家选完地图能马上看到地图设定参数。

**(2) Snipe / Pass gate 低置信兜底（fixes 场景 A 痛点）**

之前 `min_matching_samples=30` 是硬阈值，差 1 个样本就静默 return None。用户原话："场景 A 只差 1 个样本就触发"。新增三阶 fallback：
1. purple + warehouse, ≥ min_matching_samples（30）→ 高置信
2. warehouse only, ≥ min_matching_samples（30）→ 正常
3. warehouse only, ≥ `min_matching_samples_relaxed`（默认 10）→ **`low_confidence=True` + rationale 里挂 ⚠️ 警告**
4. 仍不足 → return None

`SnipeRecommendation` / `PassRecommendation` 加 `low_confidence: bool` 字段。Streamlit 出价 tab 在低置信场景把 `st.success()` 替换成 `st.warning()` 显式提醒"样本不稳"。新增 3 个单测（low-conf trigger / 真不足返回 None / pass-rec 对称行为）。

实测场景 A（沉船 145 格仓 + ±8 容差，n=3000）：之前返回 None，现在返回 `snipe_max=1,761,306, samples=29, ⚠️LOW-CONF`——既不静默丢失，也老实告知玩家可靠性。

**(3) `notebooks/05_end_to_end_case.ipynb` 长期保留产出**

把 `demo_scenarios.py` 三个场景包装成可视化 notebook：
- **场景 A**：伊森 + 沉船 145 格 + 优品均格 2.90（尾零）+ 1 红巨物 → 演示截断显示规则锁死 (cells, count) 候选
- **场景 B**：伊森 + 沉船 95 格 + 优品均格 4（整数）+ 无巨物 → 演示低品占比 + 小仓 + 全 bucket 多约束
- **场景 C**：艾莎 + 别墅 128 格 + R1-R4 轮廓 + 优品估价 89,400 + 紫巨物 2-3 → 演示信息密度最高场景

每场景三块：联合推断 top-3 + MC 价值分布直方图（matplotlib，全图 vs 仓库匹配子集 + P25/P50/P75 竖线）+ 秒仓 / 放仓推荐。`jupyter nbconvert --execute` 通过 152 KB 完成产物，3 张分布图，全场景无报错。

附带修一个 bug：`demo_scenarios.py` 之前用过 stale API `snipe.snipe_price` / `pass_rec.walk_away_price`（实际字段是 `snipe_max_bid` / `pass_max_bid`），直接 `python scripts/demo_scenarios.py` 会 AttributeError 崩溃。统一修正，端到端跑通。

**(4) PROGRESS.md "下一开工优先序" 刷新**

之前的列表停留在 C-12 之前的 stale 版本（列了已经做完的"Streamlit UI"、"per-item 接口"等）。按 C-26 现状重写：
- 把已完成的 6 项打上 ✅ + 简短结论
- 剩余 6 项按性价比排序，明确标注哪些是用户拍板 Skip 的（per-item 接口、抽检 ROI 建模）
- 项目整体进度从 67% 提到 92%——剩下主要是简历包装，工程基本完工

测试：205 单测继续绿（snipe 新加 3 个 fallback case）；demo_scenarios.py 三场景端到端跑通；05 notebook 执行无错；Streamlit smoke import 跑过模块加载阶段。

### C-25: 道具命名修正 + 总仓储 ROI 引入玩家眼估噪声 (2026-05-15)

用户 23:14 指出两个关键问题：(1) 道具命名混淆，"优品"才是紫品工具、"极品"是金品、"珍品"是红品；之前代码里叫"精品/珍品"是错的；(2) 总仓储 ROI = 0 不真实，因为玩家眼估格数是有 ±10 误差的，引擎应该建模这层噪声而不是默认精确。

**(1) 解码 `BattleItem.txt` 锁定真值**：

| 前缀 | 操作品质 | 之前代码里叫 |
|---|---|---|
| 普品 | white+green q=1+2 | ✓ 对 |
| 良品 | blue q=3 | ✓ 对 |
| **优品** | **purple q=4** | ❌ 之前叫 "精品" |
| **极品** | **gold q=5** | ❌ 之前叫 "珍品" |
| **珍品** | **red q=6** | ❌ 没建模 |

`scripts/_decode_battle_items` (一次性 probe) 解出 100100~100135 全表，证实 100126 珍品估价的描述是"显示红色品质藏品总价值" → 红品工具，不是金品。

**(2) 系统重命名 + 新增 q=6 红品工具**：

- `synth_readings.TOOL_SPECS`：重命名 6 条（精→优、珍→极），新增 3 条（珍品扫描/估价/均格 → q=6），共 11 条道具。
- `observation.{ETHAN_DEFAULT_LOADOUT, ETHAN_ALT_LOADOUT, AISHA_DEFAULT_LOADOUT, TOOL_PRICE_BY_RARITY}` 同步重命名 + 注释解释品质映射。
- `app/streamlit_app.py`：`ETHAN_KIT / AISHA_KIT / ALL_TOOLS / TOOL_EN_LABEL / TOOL_DEFAULT_PRICE / TOOL_PRICE_OVERRIDABLE` 全部跟进 + UI 文案改"精品估价→优品估价"等。
- `tests/`、`scripts/demo_outline_joint.py`、`scripts/compute_tool_roi.py`、`scripts/demo_scenarios.py` 一次性 batch 替换，全部 202 单测继续绿。

**(3) 玩家眼估噪声模型 (`compute_tool_roi(..., player_warehouse_noise_std=10.0)`)**：

之前 `_run_inference` 没把 "总仓储不在 kit 里" 这种场景配上玩家的近似估计，导致引擎走 `warehouse_capacity()` 的 159-cell 兜底——这个数对中小仓离谱地大，让 LOO 时引擎反而比 truth 多了一堆乱猜的格子。修正：每 trial 抽一次玩家眼估 `approx_capacity = truth_cells + N(0, σ)`，所有 LOO run（包括"撤掉总仓储"）都用这个 `warehouse_total_cells_approx`，full run 在带总仓储时仍用真值。

端到端验证 (Aisha + 别墅 2407 + R1-R4 轮廓加料, n=80 trials)：

| σ (cells) | 总仓储 value-gain | 总仓储 ROI | 极品估价 value-gain | 极品估价 ROI |
|---|---|---|---|---|
|  0.0 |        +0 | +0.000 | +79,336 | +2.267 |
|  5.0 |    +4,379 | +0.080 | +79,429 | +2.269 |
| 10.0 |   +24,511 | +0.446 | +79,429 | +2.269 |
| 15.0 |   +50,824 | +0.924 | +79,429 | +2.269 |

**两点新结论**：

- **总仓储 ROI 在现实噪声下是显著正的**：默认 σ=10 时回收 24,511 silver 值误差、ROI=+0.446（折回 45% 售价）；新手玩家 σ=15 时基本回本 (+0.924)。**老玩家 σ≈5 时 ROI 才接近 0**——这解释了为啥艾莎玩家偏好带总仓储：不是为了挽回 value 误差，而是为了在不确定格数下守住 cells 锁。
- **极品估价 ROI 稳如老狗在 +2.27**：仓库噪声不影响它的 value-pinning 行为（紫价的方差是艾莎最大的盲区，跟仓库总格数无关）。这印证了 C-24 那条"+3.09"读数其实就是极品估价（被误标成珍品估价）。

**(4) UI 配套**：

- ROI tab 新增 "仓库格数眼估误差 σ" 滑块（0-20，默认 10），缓存 key 加 σ 维度（参数变才重跑 MC）。
- `st.info` 顶部加 ⚠️ 说明：σ=0 → 总仓储 ROI 趋零；σ=10 → 真实 ROI 浮现。
- 紫品均格输入下方加 `st.info`，把 "2.9 vs 2.90 区别" 从 tooltip 升级到可见 caption（用户反馈"注释要表明"）。
- 全 UI 把"精品估价/精品均格"改成"优品估价/优品均格"、"珍品估价"改成"极品估价"等；q=6 红品输入区的 help 里加"珍品扫描"参考（这次是正确语义）。

**关于艾莎英文名**：用户问"是不是 Elsa 不是 Aisha"。grep 全仓库 0 个 Elsa 命中，所有 hero_value / streamlit / progress 历史都是 "艾莎 (Aisha)" → 一直就是 Aisha，没改过。

测试：202 单测 + ROI 新断言（noise=0 → 总仓储 cells-gain=0；noise>0 → cells-gain≥0）继续绿。

### C-24: ROI tab 接入艾莎 + 轮廓加料开关 (2026-05-15)

用户 23:02 问"有没有艾莎的 ROI"。引擎其实早就支持 (`compute_tool_roi(hero="aisha", include_aisha_outline=True)`)，只是 UI 把 hero 硬编码成 `"ethan"`。这一轮：

- 新增 `AISHA_KIT = (珍品估价, 总仓储空间)` — 艾莎免费拿白绿蓝紫轮廓，所以"道具"专门加在 q=4 价值 + 仓库 cells 两个紧缺信息上。
- ROI tab 顶部 `roi_hero` 改成跟着主侧边栏走，标题显示 "伊森 Ethan" / "艾莎 Aisha"。Aisha 模式下加一段 caption 解释"R1-R4 轮廓免费"。
- multiselect 默认 kit 跟着 hero 走（Ethan → ETHAN_KIT，Aisha → AISHA_KIT）。
- Aisha 模式下多出一个复选框 `加料 艾莎 R1-R4 轮廓信息（0 silver）`，默认勾选；底层就是 `include_aisha_outline=True`。
- `_cached_tool_roi` 缓存 key 加 `include_aisha_outline`，缓存仍然安全。

端到端验证（n_trials=40, seed=42, 别墅 2407）：
| Tool | Cost | ROI | info_gain_value |
|---|---|---|---|
| 珍品估价 | 35,000 | +3.091 | 108,185 |
| 总仓储空间 | 55,000 | +0.000 | 0 |

**两个发现**：
1. 珍品估价对艾莎极高 — 因为轮廓只给 cells/count 不给价值，紫价是她唯一缺口。
2. 总仓储空间 ROI ≈ 0 — 在轮廓加料场景下，cells 已经被 outline 死锁，仓库总数边际为零。这不是 bug 而是真信号：**艾莎玩家如果带轮廓没必要再买总仓储**。这种 finding 正好就是 ROI tab 的设计目标。

测试：202 单测继续绿；Streamlit smoke launch 无报错。

### C-23: ROI tab 道具自选 + 价格覆盖 + 图表英文标签 (2026-05-15)

用户 22:53 反馈 3 件事：

1. **seed 默认不勾选** — 上轮 C-22 默认勾选，用户怀疑会让结果"假性固定"。改默认 `False`：每次点击 OS 熵重新随机；勾上才锁定。
2. **ROI 道具自选 + 价格覆盖** — 之前硬编码 `ETHAN_KIT`。这一轮：
   - 加 `ALL_TOOLS` 注册表（8 个道具：白扫、绿扫、蓝扫/估/均、紫扫/估、总仓储）
   - UI 加 `st.multiselect`，默认还是 ETHAN_KIT 但用户可勾选
   - 蓝品及以上道具加价格覆盖输入（折叠 expander），默认价复用 `TOOL_PRICE_BY_RARITY`
   - **价格覆盖通过显示层 `dataclasses.replace` 实现** — 因为 `info_gain` 只取决于 (map, hero, kit, MC) 与价格无关，所以缓存继续命中，仅 ROI 比值在显示层重算。改价 → 瞬发更新。
   - 选道具少于 2 个时禁用按钮（LOO 需要≥2）。
3. **ROI 图表英文标签** — 中文在 matplotlib 字体回退中容易变方块。所有道具加 `TOOL_EN_LABEL` 映射（"精品估价" → "Blue Appraise" 等），图表用英文，下面的详细表保留中英对照。

代码改动：
- `app/streamlit_app.py`：
  - `seed_lock` 默认 `False`
  - 顶部新增 `ALL_TOOLS / TOOL_EN_LABEL / TOOL_DEFAULT_PRICE / TOOL_PRICE_OVERRIDABLE`
  - ROI tab 整段重写，加 multiselect + 折叠价格覆盖 + 图表英文化
  - `_override` helper 用 `dataclasses.replace` 修改 silver_cost + roi_value

测试：202 单测继续绿；Streamlit smoke launch 无报错。

### C-22: 地图必选 / 仓库去默认 / seed 可选 / 巨物定义 (2026-05-15)

用户 22:38 反馈 4 件事，配合截图：

1. **"改了数据还是一个解，是有什么问题吗"** — 实际是误会。截图里他同时填了 `紫品总格数=58 + 紫品均格=2.9`，58/x=2.9 数学上 x=20 唯一，候选预览正确返回 "✅ 已唯一锁定 58/20"。回答：候选预览**完全不依赖 MC seed**，是确定性的算术枚举；想看多解，只填 avg / 只填 cells 就行。借此机会把 MC seed 改成可选 — 加 `seed_lock` 复选框（默认勾选），取消后每次点击用 OS 熵重新随机，p25/p50/p75 会浮动 ±几个百分点。
2. **地图必选 placeholder** — `selectbox(index=None, placeholder="请选择具体地图...")`，未选则 `st.stop()` + 友好提示。
3. **仓库总格数仍有默认 140** — 改 `value=0`；help 文案说明 "留空 (=0) 时引擎回退到地图默认上限 159 格"。
4. **巨物定义** — 紫品 section 上方加 expander："巨物 = 占 ≥ 12 格 (4×3) 的藏品（屏风/涂鸦墙/游艇/护甲/石狮子）；引擎按品质用不同标准面积：紫红=16 格，金=18 格；可见性：Ethan 可见三色，Aisha 仅紫"。

代码改动：
- `app/streamlit_app.py`：上述 4 处 UI 调整。`seed` 在 `seed_lock=False` 时用 `time.time_ns()` 当 OS 熵，缓存自动失效。

测试：202 单测继续绿；Streamlit smoke launch 无报错。

### C-21: 件数 / 均格 Reading 修复 / 候选预览 / 总藏品数 / 文案优化 (2026-05-15)

用户 22:00 反馈一连串问题，里面**藏着一个真 bug**：

1. **UI 的 `avg_cells` 实际从未生效** — 用 `st.number_input(..., format="%.2f")` 收的是 `float`，`2.90` 在 UI 内部就塌成了 `2.9`，尾零信息丢了。更糟的是 `QualityBucketObs.avg_cells` 期望 `Reading`，引擎调用 `enumerate_candidates(bucket.avg_cells)` 会触发 `AttributeError: 'float' object has no attribute 'raw'`。这个 bug 之前被两件事盖住了：(a) 实验性联合推断 tab 上轮被隐藏；(b) snipe MC 不用 avg_cells。这一轮修了。
2. **均格多解处理** — 单独输入 `2.90` 时引擎能枚举 10 个解（32/11, 61/21, 64/22, 90/31, ...），UI 没把这个暴露给玩家。新增 `_render_candidate_preview` 在紫品 / 金品输入下方显示当前约束下的 top-3 候选 + 仓深加权 composite，玩家可以根据 "32 格 vs 64 格" 两种解的占比决定要不要继续填 cells / count。
3. **艾莎件数 UI 缺失** — 之前 UI **完全没有 count 输入**，但艾莎玩家依赖 R1-R4 轮廓自己数件数。本轮加了 `white_count / green_count / blue_count / purple_count / gold_count` 字段；伊森只在紫品 + 金品加 count（低品质段他用扫描，不需要数）。
4. **总藏品数量** — 别墅地图的 R1 hint / 艾莎金品工具能透露 "本仓 X 件藏品"。新增 `SessionObs.total_item_count` 字段；`joint_top_k_for_session` DFS 用它做硬剪枝（`running_count > total → return`）+ 软罚（`missing × 0.02`）。Sidebar 加了对应输入。
5. **p25/p50/p75 文案** — 改成 "悲观估值 / 中位估值 / 偏乐观 / 乐观上限"，metric tooltip 解释每个分位代表多大概率。matplotlib 图 legend 同步改成 Pessimistic / Median / Optimistic / Upside（避免中文字体问题）。
6. **placeholder + 切换地图清空** — 紫品/金品的均格改成 `st.text_input(placeholder="例 2.90 或 3.43")`；其它 number_input 的默认值改 0 表示"未提供"。新增 map-change 监听：`map_id` 变化时清掉所有读数字段（不清仓库格数 / 总件数），并弹 `st.toast` 提示。

引擎侧改动：
- `src/bidking_lab/inference/observation.py`：`SessionObs` 加 `total_item_count: int | None = None`。
- `src/bidking_lab/inference/joint.py`：DFS 多传 `running_count`，硬过滤 + 软罚分。

UI 侧改动（`app/streamlit_app.py`）：
- 加 `from bidking_lab.inference.display import Reading, parse_reading` + helper `_try_parse_reading`，所有 avg_cells 经由 Reading 进入引擎，尾零得以保留。
- 紫品/金品改 `text_input`，5 列布局（cells / count / avg_raw / value / huge_band）。
- 艾莎拆分模式额外暴露 white/green/blue 的件数输入。
- 紫品 / 金品下面挂候选预览块，实时显示 top-3 (cells, count) + composite。

测试：全量 202 单测继续绿；smoke compile + import 通过；端到端 demo_scenarios.py 3 个场景全部一致输出。新增 1 个端到端验证（terminal 内）：joint 加 `total_item_count=6` 约束后，top-5 假设都收敛到 `sum(count)==6`。

发现 / 教训：
- **UI 数据类型不匹配是隐形 bug** — `number_input` 永远返回 float，跟 dataclass 标注的 `Reading | None` 不兼容但 Python 不抓。每一个非平凡字段都该有 round-trip 单测（用户填了 → 引擎能消费 → 结果合理）。已记录到 `TROUBLESHOOTING.md` 的下一条。
- 候选预览是"半透明"的引擎窗口，让玩家**直观看到约束如何收紧** — 比单纯一个 top-3 表更有教学价值。
- 总藏品数硬约束很强：从 5 个 hypothesis 变成"全部 sum=6"，是 cells 之外的第二条独立信息。值得在 UI 里强调。

### C-20: 收敛核心流程 — 隐藏联合推断表 / ROI 加图表 / MC 默认 1000 (2026-05-15)

用户 21:43 反馈 4 件事：

1. **填巨物 / 估值后秒仓·放仓输出不变** — 怀疑共享采样改坏了。
   - 排查后确认这不是 bug：`compute_snipe_recommendation` 只用 `(warehouse_cells, purple_cells)` 做 conditioning（见 `snipe.py:147-166`），huge_band / value_sum / avg_cells 一直没参与。
   - 进一步收窄会让匹配样本不够 — 当前设计是 "宁可放宽也要有 sample"。
   - 修法：**出价 tab 加一条 `st.warning`** 明确告知 conditioning 集合，避免被当 bug。
2. **采样数 2000 过多**，大仓很慢。改默认 1000，仍然支持 500-5000，并在 help 里写明"大仓低匹配率可调高，重复点击有缓存"。
3. **联合推断表三个结果一样、没区分意义** — 用户明确说"如果没必要，先删掉 / 注释 / 迁到 undefined_toolkit"。
   - 砍掉是对的：当 user 已经填了 `total_cells`，top-3 只在 `count` 上有微小差异。
   - 处理：**把整段渲染搬到 `app/experimental_tabs.py::render_joint_inference_tab`**，侧边栏加 `show_experimental` 复选框，默认关。等以后 `unconfirmed_huge_shapes` 真的让 bucket 有自由度时再打开。
4. **ROI 慢 + 表意不清 + 不知道是否依赖输入**：
   - 加大段说明（"在这张地图上，哪个道具的价值推断提升最值"）。
   - 明确告诉用户 **ROI 与读数输入完全无关**（`compute_tool_roi` 不读 `SessionObs`）。
   - 加 `@st.cache_data` 包了一层 `_cached_tool_roi(map_id, tools, hero, n_trials, seed)`，重复点击瞬发。
   - 加 matplotlib 条形图（横向、正负配色），让 ROI 排序一目了然。
   - 新增"排序方式"下拉（ROI / 价值贡献 / 售价）方便不同视角阅读。

代码改动：
- `app/streamlit_app.py`：拆 tabs（默认 3 个，开关开启变 4 个）；ROI tab 重写为 说明 + 排序 + 图表 + 表格；MC slider 默认 1000；出价 tab 加 conditioning warning。
- `app/experimental_tabs.py`（新增）：搬走联合推断表全部渲染逻辑，配独立 docstring 说明何时该恢复。
- 移除 `streamlit_app.py` 里不再用到的 `joint_top_k_for_session` / `PER_CELL_VALUE_DEFAULT` import。

测试：全量 202 单测继续绿；smoke compile + import 通过。

### C-19: 均格输入 + 6 行联合表 + 采样共享提速 (2026-05-15)

用户 21:18 反馈 4 件事：

1. **联合推断表"价值一致度 0.0000"看不出意义**，而且只有用户填过的 bucket 出现 — 应该 6 个品质都列出来（白 / 绿 / 蓝 / 紫 / 金 / 红）。
2. **均格概念漏了** — 精品均格、珍品均格是核心道具读数（含小数点泄露：2.5 vs 2.90），UI 完全没有这个字段。
3. **价值分布图过大**，挤掉了下面的秒仓 / 放仓推荐，得下滑。
4. **采样还是慢** — 即使小仓 65 格的 case，也要等好几秒。

**Profile**（命令行直测）：

```
== OLD path: 3 independent samplings (distribution + snipe + pass) ==
  total: 5.61s
== NEW path: sample once, reuse via truths= param ==
  total: 2.84s
```

旧 bidding tab 在一次按钮点击里**采样 3 次**（分布图 1 次 + `compute_snipe_recommendation` 内部 1 次 + `compute_pass_recommendation` 内部 1 次），每次 2000 truths × 1.4ms = ~3s，总共 ~6-9s。这就是用户感受到的卡。

**改动**：

| 模块 | 变化 |
|---|---|
| `inference/snipe.py` | `compute_snipe_recommendation` / `compute_pass_recommendation` 新增 `truths: list[SessionTruth] \| None = None` 参数；若提供则跳过内部采样循环。21 单测无变动全过。 |
| `app/streamlit_app.py` 数据层 | 新增 `_sample_truths_cached(map_id, n_trials, seed)` 用 `@st.cache_data(max_entries=8)` 缓存；同一 (map, n_trials, seed) 三元组第二次点击瞬间返回 |
| `app/streamlit_app.py` UI | 出价 tab 改成"采样一次→三处复用"（分布图、snipe、pass）；首次 ~3s，重复点击 ~0s |
| `app/streamlit_app.py` 紫品/金品 section | 列数 3 → 4，新增 `purple_avg` / `gold_avg`（`step=0.01, format="%.2f"`），对接 `QualityBucketObs.avg_cells` |
| `app/streamlit_app.py` 联合推断表 | 固定 6 行（q=1..6），未观察的填 `—`；列扩到「品质 / 总格数 / 件数 / 均格 / 每格估值 / 价值一致度」；价值一致度保留 3 位小数；表下方加 "已确认 X 格 · 未记录 Y 格" caption |
| `app/streamlit_app.py` 价值分布图 | `figsize` 9×4.0 → 7×2.6；字体 size 7/8；`use_container_width=False` 防止被拉伸 |

**实测加速**：

- 单次点击「运行出价 hint」：5.6s → 2.8s（2× 加速）
- 重复点击同地图：2.8s → ~0.1s（cache hit）
- 切换地图也只重新采样一次

**测试**：202 单测全过；Streamlit `--server.port 8503` 起来 HTTP 200。

**下一步候选**：
- C-20: `SessionObs.unconfirmed_huge_shapes` 字段 + 引擎 bucket 锁定（接 UI 里 `seen_shapes`）
- C-21: 地图动态信息字段（数量/均格/总价 hint 等手动输入） + `notebooks/05_end_to_end_case.ipynb`

---

### C-18-hotfix: 形状字典改为"按形状数量"避免 widget 爆炸 (2026-05-15)

用户 21:00 反馈跑 UI 时"推理时间特别长，等了一会还在推理"。截图显示：Ethan / 沉船 2503 / 仓库 140 / 白绿=24 / 蓝=16 / 紫=50 + 2-3 巨物。

**性能 profile**（命令行直接跑）：

- `joint_top_k_for_session` 这个 case = **1.7 ms**
- `sample_session_truth` × 2000 = **2.77 s**

两边都不可能让用户等"很久"。真正的瓶颈是 **Streamlit 前端 widget 数量爆炸**：上一轮 C-18 在形状字典每个 unique 物品行加了 `[+1]` + `[↻]` button + `metric` 共 3 个 widget，5 个 shape × 23 件物品 = **~70 个新 widget**。每次任意 widget 变化 / `st.rerun()` 都会**重建整个页面所有 widget**，浏览器端渲染就到秒级，给用户造成"还在推理"错觉。

**同时用户反馈**：

> 不能要求用户明确给出是什么物品，而是一般可以让用户给出大致的几乘几的形状的数量，这个是比较泛用的

——非常对。看到 4×5 巨物时，玩家通常只能说"我看到 1 个 4×5"，**不可能**精确到"我看到 1 个墙面涂鸦"（除非品质道具锁定了）。所以"按 unique 物品 +1"的设计本身就不实用。

**修法**（一举两得）：

- 删除所有 `[+1]` `[↻]` button + 每行 metric（~70 widget → 0）
- 改成 5 个 `number_input`：每个 shape 一个，例 "3×4 = 12 格 = 2"
- 候选物品列表放进 expander，用纯 `st.markdown` 渲染（不占 widget 配额）
- state key 从 `confirmed_items[name]` 改成 `seen_shapes[shape]`，下一轮 C-19 接 `SessionObs.unconfirmed_huge_shapes` 时也更顺

**测试**：本地 Streamlit `--server.headless true --server.port 8502` 起来 HTTP 200；202 单测仍全绿（仅改 UI）。

**教训**：Streamlit widget 数量 > 50 时就要警惕。能用 `st.markdown` 表达的信息不要塞进 widget；交互复杂的列表优先考虑"折叠到一个聚合 widget（slider / select_slider / number_input）"，而不是每行一个 button。

---

### C-18: UI 价值分布图 + 金品格数 + 形状字典 +1 按钮 (2026-05-15)

用户 20:38 反馈 C-17 三件小事：

1. **形状反查字典加点击 +1**：每个 unique / 大件候选行旁边给 button，让玩家"看到这件物品"时直接 +1 计数（一局最多几件，按钮比 number_input 更顺手）。
2. **联合推断结果不只是 top-3 表，要给"仓库价值可能区间 + 范围分布图"**，参考 `notebooks/04_roi_and_snipe.ipynb` 中的 conditional-MC histogram，让玩家直观看到价值的 P25/P50/P75/P90。
3. **金品 q=5 只有"总估值"输入，漏了"金品总格数"**——某些地图会直接给出"金色藏品格数"提示。

**改动**（仅 `app/streamlit_app.py`，约 80 行）：

| 模块 | 变化 |
|---|---|
| imports | 加 `matplotlib` + `bidking_lab.inference.ground_truth.sample_session_truth` |
| 金品 section | 由 2 列改为 3 列，新增 `state["gold_cells"]`；`_maybe_gold_bucket` 把 `total_cells` 也传给 `QualityBucketObs`（既有支持） |
| 出价 tab | 顶部加 conditional-MC histogram：`n_trials` 次 `sample_session_truth` 采样，按 `warehouse_cells ± warehouse_tol` 过滤后画图，4 列 metric 显示 P25/P50/P75/P90；snipe/pass 推荐卡片下移到底部（符合用户"先看价格区间，再做决策"的心智模型） |
| 形状字典 expander | 每行从 `st.table` 单行展开成 6 列布局：品质 / 唯一性 / 名称 / 估值 / 当前计数 / [+1] [↻] 双按钮；底部汇总"已确认物品"表 |

**UI 占位策略**：`confirmed_items` 存在 `st.session_state` 但暂不传入 `SessionObs`——下一轮 C-19 加 SessionObs 字段 + 引擎 bucket 锁定时再接通，避免"填了没下游"。

**Chart 备注**：matplotlib 在 anaconda 环境里 Chinese 字体可能缺失，所以 axes label 用 English（图例值是数字 + 中文 metric 卡片在图下方补足）。

**测试**：202 → 202 passed；语法 `python -m ast` OK；lint 0。

**下一步候选**：
- C-19: `SessionObs.confirmed_items` + `unconfirmed_huge_shapes` 字段 + bucket 锁定逻辑（这一轮 UI 占位的真正接入）
- C-20: 地图动态信息字段（数量/均格/总价 等手动 hint）+ `notebooks/05_end_to_end_case.ipynb`

---

### C-17: 修 pyarrow bug + 形状反查字典升级 (2026-05-15)

用户 20:23 反馈 streamlit 在 anaconda 环境跑挂了：

```
ImportError: numpy.core.multiarray failed to import
pyarrow.lib import failed under numpy 2.2.6
```

根因：用户 anaconda 里 pyarrow 是 numpy 1.x 时代编译的，与现在 numpy 2.2.6 不兼容。`st.dataframe` 内部 import pyarrow 导致 crash。

**修法**：把所有 `st.dataframe` 改成 `st.table`（纯 HTML，不走 pyarrow）。3 处全替换。

**附带升级**：用户同时提议把唯一物品字典扩成"形状反查 / 大件物品字典"——按形状（不按品质）组织，给出每个形状下所有候选物品，并标 ☆唯一 / 多候选。让玩家"看到形状但不确定品质"时能快速划出候选集。

**数据调研**（`Item.txt` >=12 格 + quality 聚合）：

| 形状 | 候选数 | unique 物品 | 多候选品质 |
|---|---|---|---|
| 3×4 = 12 格 | 9 | 电动三轮车(绿) / 防护盾(紫) | 金 ×4 / 红 ×3 |
| 3×5 = 15 格 | 7 | 小型面包车(蓝) / 服务器机柜(金) | 红 ×5 |
| 4×4 = 16 格 | 5 | 石狮子(蓝) / 轻量化锂电池(金) | 红 ×3（红木屏风 / 翡翠屏风 / 碳纤维车身） |
| 3×6 = 18 格 | 1 | 单人郊游快艇=游艇(金) | — |
| 4×5 = 20 格 | 1 | 墙面涂鸦墙(蓝) | — |

涵盖了用户之前提到的所有典型 decoy / 巨物（游艇、屏风、石狮子、面包车、涂鸦）。

**未做（defer 到 C-18）**：用户还提到"未确认品质的巨物分级输入"。当前引擎 `SessionObs.QualityBucketObs.huge_band` 是按 quality 存的，没"未分类巨物"字段。如果纯 UI 加输入但不接引擎，用户填了没下游 \u2014 反而误导。所以 C-18 会和 unique 物品 checkbox 一起做引擎层改造。

**测试**：202 → 202 passed；streamlit HTTP 200，浏览器截图确认 5 张 shape 表全部渲染（st.table 不依赖 pyarrow）。

**下一步候选**：
- C-18: SessionObs 增加 `confirmed_items` + `unconfirmed_huge_shapes` 字段，UI 加 checkbox/分级输入，引擎可据此锁定 bucket
- C-19: 地图动态信息字段（数量/均格/总价 等手动 hint）

---

### C-16: UI 完善 — 地图二段式 / 巨物语义 / 全中文化 / 唯一物品字典 (2026-05-15)

用户 20:00 反馈 C-15 的 UI 几个问题：
1. "红品 巨物" 标签暗示已限定红色，但实际玩家看到巨物未必能立即确定颜色 → 改成 **"红品巨物数量（已确认为红色）"** 等明确语义；
2. 墙面涂鸦、游艇等唯一物品没有提示 → 加 **唯一物品字典 expander**；
3. 地图选项只有 9 张，太少 → 改成 **两段式：先选别墅 / 沉船，再选具体地图（全 60 张可选）**；
4. UI 大量英文术语（value_sum / cells / huge_band） → **全中文化，英文以辅助形式跟随**；
5. 还顺手修了一个 typo 文案"挭回量"→"挽回量"。

**主要改动**（`app/streamlit_app.py` +120 LOC）：

| 区块 | 改动 |
|---|---|
| 地图选择 | `_filter_priority_maps` → `_maps_for_category(maps, category)`，按 ID 前缀（24/34/44 = 别墅，25/35/45 = 沉船）分类，每张显示 `[Tier] map_id - name` |
| 侧边栏 | 顶部加 `radio("地图类型", options=["mansion","shipwreck"])`，下方下拉框依此过滤；选项 60 张全可见 |
| 英雄标签 | "ethan" → "伊森 (Ethan)"，"aisha" → "艾莎 (Aisha)" 通过 `format_func` 渲染 |
| 巨物标签 | "紫品 巨物" → **"紫品巨物数量（已确认为紫色）"**；金 / 红同；并加 help tooltip 解释何时该填 |
| HUGE_BAND_LABELS | "none/1/2-3/4+" → "无/1个/2-3个/4个及以上" 通过 `format_func` 渲染 |
| 唯一物品字典 | 新 `UNIQUE_ITEMS_BY_QUALITY` 常量 + expander，按 q=3/4/5/6 列出 9 件常见 unique（墙面涂鸦/石狮子/防护盾/游艇/防弹衣/波斯毯/红木屏风/翡翠屏风等），含形状、格数、估值、说明 |
| 子标题 caption | 每个 section 加一行说明它的语义（"提供紫品 cells 后 MC 会额外加一层过滤"、"红品几乎不会被估价道具准确读出"等） |
| 联合推断表格 | 列名 quality / total_cells → "品质 / 总格数 / 件数 / 价值一致度" |
| 出价 hint | "matching" → "匹配样本"，"safe_floor" → "保底价"，加 cond_label 显式标注是否含紫品条件 |
| ROI 表格 | 列名英文 → "道具 / 道具售价 / value 贡献 / cells 贡献 / ROI" |
| Tab 名 | "出价 hint" → "出价推荐" |

**唯一物品字典数据**（基于 Item.txt 调研）：

| 品质 | 唯一形状 | 物品 | 估值 |
|---|---|---|---|
| 蓝 q=3 | 5×4 = 20 格 | 墙面涂鸦墙 | 8,880 |
| 蓝 q=3 | 4×4 = 16 格 | 石狮子（与红屏风同形，需排除） | 9,168 |
| 紫 q=4 | 3×4 = 12 格 | 可折叠高韧性防护盾 | 20,082 |
| 金 q=5 | 6×3 = 18 格 | 单人郊游快艇（即"游艇"） | 106,500 |
| 红 q=6 | 4×4 = 16 格 | 红木屏风 / 翡翠屏风 | 361,000 / 844,000 |

下迭代会把这些 unique items 接入 `SessionObs.confirmed_items`，让引擎在玩家勾选后锁定对应 bucket。

**烟测**：`streamlit run` HTTP 200；浏览器全屏截图确认：
- 侧边栏：地图类型 button（🏛️ 别墅 / 🚢 沉船）+ 60 张下拉地图，含 Tier 标识
- 主面板：所有 section title / caption / 字段标签全中文
- 唯一物品 expander：4 张表格按品质列全 9 件

**测试**：202 → 202 passed（UI 无新单测；C-15 留下的 typo bug 在 C-16-pre 已修）。

**下一步**：
- C-17 候选：地图动态信息字段（数量 / 均格 / 总价 等手动 hint）注入 SessionObs
- C-18 候选：唯一物品 checkbox → SessionObs.confirmed_items 接入推断引擎

---

### C-15: Streamlit UI scaffold — 4 个 tab 串联推断/出价/ROI (2026-05-15)

用户 18:28 决定开 Streamlit，并明确：**Ethan 用普品扫描 → 白绿合并一个输入；Aisha 靠 R1/R2 轮廓 → 白/绿可拆开（也允许合并）**。同时把巨物形状识别正式删除（与 outline.py 重叠，边际效用低）。

**交付**：`app/streamlit_app.py`（~330 行）含 4 个 tab：

| Tab | 功能 | 调用 |
|---|---|---|
| 📝 读数输入 | hero/map/仓库 + 各品质 cells / value / 巨物 band；Ethan 合并白绿，Aisha 拆白绿 | `SessionObs` |
| 🔍 联合推断 | top-3 joint posterior，含 composite/total_cells/warehouse_gap | `joint_top_k_for_session` |
| 🎯 出价 hint | snipe + pass 两张卡片，含 P50/P75/P90/safe_floor，标注是否启用紫品条件 | `compute_snipe/pass_recommendation` |
| 💰 道具 ROI | Ethan default kit 的 LOO ROI 表 | `compute_tool_roi` |

**Aisha 输入分流细节**：
- 默认勾选 "拆分白/绿轮廓" → 白(q=1)/绿(q=2)/蓝(q=3) 三个分开输入
- 取消勾选 → 合并白+绿到 q=1（Ethan 风格）
- 金品/红品巨物 band 在 Aisha 视角自动 disabled（她看不到金红巨物，只能看紫巨）— 通过 `disabled=(hero=="aisha")` 实现

**侧边栏**：英雄、地图（仅 priority maps = 别墅 240x/340x/440x + 沉船 25xx/35xx/45xx）、仓库格数、可展开的 MC 高级参数（trials / 仓库容差 / 紫品容差 / search width / seed）。

**配套小修**：`demo_snipe.py` 的 None-fallback 文案分三档显示原因（warehouse<80 / 80-120 / >120），让用户看到具体哪步 gate 失败，而不是笼统说"both returned None"。

**烟测**：`streamlit run` 启动正常（HTTP 200，5.4 KB 首屏）；浏览器渲染验证 Ethan 单输入 / Aisha 三输入切换 + 金红巨物正确 disabled。

**依赖**：`pyproject.toml` 新增 `[project.optional-dependencies]` 的 `ui` extra（`streamlit>=1.30` + `matplotlib>=3.7`）。本地用 `pip install -e ".[ui]"`。

**用户问题 "warehouse=140 / 100 都返回 None 是对的吗"** 已澄清：
- 140：snipe 门控通过，但 MC 在别墅 2407 上 140±8 cells 落在 0.7% 尾部，匹配样本不足 → 应换沉船 2510
- 100：处于 80–120 的 no-hint 死区，gate 结构性失败 — 这是设计意图

**测试**：202 → 202 passed（无回归；UI 不带新单测）。

**下一步**：
- C-16 候选：把 `ROI` tab 改成读 `docs/tool_roi_table.md` 缓存（瞬时）+ 全量重算按钮（30-60s）
- C-17 候选：地图动态信息字段输入（数量 / 均格 / 总价 等手动数字 hint）

---

### C-14: 紫色 cells 条件细化 — 分段精度的秒仓/放仓 (2026-05-15)

用户 18:14 提议："秒仓放仓系数可以分段式考虑——一般是在白绿蓝给出后有提示，但是如果用户有给出紫色，那么也可以有更准确的提示"。同时把巨物形状识别延后（与 outline.py 重叠，下迭代再做）。

**做法**：MC 过滤增加一层 optional 紫色 cells 约束，**tight filter 优先 + fallback 透明**：

1. 收集 `cond_warehouse`（仅过滤仓库大小）和 `cond_purple`（同时过滤紫色 cells, ±`purple_tolerance` 默认 4 格）两份样本
2. 若 `len(cond_purple) >= min_matching_samples` → 用 tighter filter，`purple_conditioned = True`
3. 否则 fallback 到 `cond_warehouse`，rationale 里显式标 "（紫品样本不足, fallback）"

**新字段**：`SnipeRecommendation.purple_conditioned` + `PassRecommendation.purple_conditioned`（bool），UI 可据此区分"粗 hint"和"精 hint"。

**真实数据效果**（沉船 2510, 140 格仓库, n=4000, tol=±10/±4）：

| 紫色 cells | P50 | snipe_max | conditioned | n |
|---|---|---|---|---|
| None       | 1,088,876 | 1,611,158 | False | 102 |
| 10 / 22    | 1,088,876 | 1,611,158 | False (fallback) | 102 |
| **35**     | 1,294,920 | **1,797,730** (+12%) | **True** | 30 |

紫色 35 格 → 系统识别为"价值偏高仓库" → snipe_max 自动上调 12%。语义合理：紫色多 = 整仓价值高。Fallback 也透明（rationale 里能看到）。

**测试**：4 新单测，198 → **202 passed**：
- `test_snipe_purple_conditioned_when_purple_cells_given` — 命中条件
- `test_snipe_falls_back_when_purple_tolerance_too_tight` — fallback 路径
- `test_snipe_purple_conditioned_field_defaults_false_when_no_purple_obs` — 无紫品默认 False
- `test_pass_purple_conditioned_when_purple_cells_given` — pass 镜像

**延后项目**：巨物形状识别（用户提议"明确车壳/屏风/大鱼形状或排除墙面涂鸦/游艇..."）—— 这部分与现有 `outline.py` 高度重叠，需要重新设计 conditional 接口。等 Streamlit 上线后再做。

### C-13: 放仓推荐（秒仓镜像）+ notebook 04 三段式收尾 (2026-05-15)

用户 18:01 review C-12 反馈：数字与体感一致 (`snipe_max ≈ 1.6M` 合理)、措辞可接受、图表清晰。新提议：**对称加一个"放仓"hint**——小仓 (≤80) + 白绿蓝占比高 → 期望值低于均值时给"超过 X 就放"提示。

**`snipe.py` 加 `compute_pass_recommendation`**（6 新测试，合计 17 snipe+pass 测试）

设计上完全对称：

| Hint | warehouse | 低品门控 | 输出 |
|---|---|---|---|
| **snipe (C-11/12)** | `>= 120` | 低品扫齐 | `snipe_max_bid = P75 × 1.15`（高风险溢价） |
| **pass (新)** | `<= 80` | 低品扫齐 **AND** `low_cells/warehouse >= 0.40` | `pass_max_bid = 条件 P50`，`safe_entry_bid = 条件 P25` |

`PassRecommendation` 多出两个字段：
- `unconditional_p50`：全图 MC 均值（不带 warehouse 过滤），作为对比基准
- `value_ratio = expected / unconditional_p50`：这个仓库比全图均值低多少。tooltip 直接显示 "预期仓价仅是全图均值的 79%"

**`scripts/demo_snipe.py`** 升级为"双 hint demo"，自动跑 snipe + pass 两套。  
**别墅 2407 (60 格仓, 白绿 22 + 蓝 8 = 50% 低品占比)** 实数据 demo 输出：
- 850 匹配样本
- 条件 P25 / P50 / P75 = 175k / **276k** / 438k 银币
- 全图 P50 = 350k
- 这个仓库 = 79% × 全图均值
- **pass_max_bid = 276k 银币**（超过就放）
- safe_entry_bid = 175k（P25 安全入场）

**Notebook 04 (`04_roi_and_snipe.ipynb` + `.html`) 升级为三段式**：

第三段加 `## 3. Symmetric Hint: 放仓` 章节 + 1 markdown (对比表) + 1 code cell (real-data demo)。Summary 改成三个 actionable surfaces：buy (ROI) / bid (snipe) / fold (pass)。

HTML 重新执行导出：155 KB ipynb / 470 KB HTML。

**测试数**：192 → **198 passed**（+6 pass 测试）。

### C-12: Aisha R3 对称秒仓 + notebook 04 ROI/秒仓可视化 HTML 产出 (2026-05-15)

用户 17:34 反馈："3 个方向都不错，按推荐做"。我的推荐：**做 3+2 (Aisha 对称秒仓 + notebook 04 HTML)，把 Streamlit (1) 留到下轮专门做**——理由：1 需要本地 `streamlit run`，不能给文件链接；2 可以导出单文件 HTML 直接交付。

**任务 3：snipe.py 扩展 Aisha R3 分支**（3 新测试，合计 11 snipe 测试）

- `compute_snipe_recommendation` 现支持 hero in {ethan, aisha}：
  - **Ethan @ R2**：门控仍是 `q=1 (普品扫描合并) + q=3 (良品扫描)`，3700 银币扫描成本
  - **Aisha @ R3**：门控变成 `q=1 + q=2 + q=3` 全部观察（她 R1→R3 轮廓积累），**0 银币扫描成本**
- `SnipeRecommendation` 加 2 字段：`hero` + `round_window` ("R2"/"R3")
- 推荐数值（safe_floor/expected/snipe_max）两个英雄相同——MC 分布只依赖地图+仓库大小，不依赖英雄；差别在 rationale 文本：
  - Ethan: "白绿(普品扫描) 24 + 蓝(良品扫描) 18 ... R2 是秒仓黄金窗口（对手还未锁价）"
  - Aisha: "白(轮廓 R1) 14 + 绿(轮廓 R2) 10 + 蓝(轮廓 R3) 18 ... R3 轮廓叠加后低品信息全齐（0 银币扫描成本），对手可能已开始抬价但你以零成本拿到同等信息"
- Tooltip 加上 round_window 前缀："高风险操作 (R2): 可秒仓, 推荐价格 X 以内"

**任务 2：notebooks/04_roi_and_snipe.ipynb + .html**（执行+导出，2 张图）

10 个 cell，结构：
1. Intro markdown：项目背景 + 两个产出概述
2. Setup：sys.path hack + imports + load 真实数据
3. ROI section markdown：解释 LOO metric + 精品均格 caveat
4. Code：`compute_tool_roi` 跑 Ethan default × {别墅 2407, 沉船 2510} × 60 trials
5. Code：grouped horizontal bar chart（双地图 ROI 对比）→ `fig_tool_roi.png`
6. Takeaway markdown：良品扫描 ROI ≈ 6× 最优、精品均格 = 0 caveat
7. Snipe section markdown：表格对比 Ethan@R2 vs Aisha@R3 信息渠道与成本
8. Code：snipe rec for 两个英雄（沉船 2510, 140 格仓库）
9. Code：MC value distribution histogram（unconditional vs warehouse-filtered）+ 4 条 marker 线（safe_floor / expected / snipe_max / P90）→ `fig_snipe_distribution.png`，x 轴 P98 clip + Million-format
10. Summary markdown：项目闭环（buy + bid 双产出）

**最终数字**（沉船 2510, 140±10 格仓库, n=89 matching）：
- safe_floor = 762,213 (P50 × 0.70)
- expected  = 1,088,876 (P50)
- snipe_max = 1,611,158 (P75 × 1.15)
- P90      = 1,889,298

**交付物**：
- `notebooks/04_roi_and_snipe.ipynb` (151 KB，含 baked outputs)
- `notebooks/04_roi_and_snipe.html` (460 KB，单文件 HTML，简历附件直接打开)
- `notebooks/fig_tool_roi.png` (49 KB)
- `notebooks/fig_snipe_distribution.png` (73 KB)

**`inference/__init__.py`** 已 re-export `SnipeRecommendation` + `compute_snipe_recommendation`（C-11 已加）。

测试数：189 → **192 passed**（+3 Aisha snipe 分支测试）。

### C-11: Ethan R2 秒仓推荐模块 + 精品均格 ROI caveat note (2026-05-15)

用户 17:25 反馈两点：

1. **跳过抽检/宝光建模**——只是简要推荐，不增加项目复杂度
2. **新功能**：Ethan 玩家在给出白绿+蓝 cells + 仓库格数 ≥ 120 后，UI 应弹出"高风险操作：可秒仓，推荐价格 xxx 以内"——R2 是秒仓黄金窗口，对手还没开始抬价
3. **修正 ROI 解读**：精品均格 ROI≈0 不等于无用——整数/2.5 这种均格读数会通过截断显示规则 pin 死紫色 (total_cells, count) 配对，这是 cells 精度而非 value 精度

**新模块 `inference/snipe.py`**（8 单测，全绿）

- `SnipeRecommendation` dataclass：`expected_value` (P50) / `p25_value` / `p75_value` / `p90_value` / `safe_floor_bid` / `snipe_max_bid` / 多行 `rationale` + 单行 `as_ui_tooltip()`
- `compute_snipe_recommendation(session, *, maps, drops, items, ...)` 硬门控：
  - hero == "ethan"
  - warehouse_total_cells >= 120
  - q=1 (白+绿合并) total_cells 已知
  - q=3 (蓝) total_cells 已知
  - MC 匹配样本数 >= `min_matching_samples` (默认 30)
- 算法：对地图采样 `n_trials=2000` 次 ground truth，过滤 `|truth.warehouse_cells - obs.warehouse_cells| <= tolerance` (默认 ±8 格)，取剩余分布的分位数。`snipe_max_bid = P75 × snipe_premium (1.15)` 体现高风险溢价（低于 P75 是对手出价默认区，超过 = 拓宽胜面）
- 任何门控失败返回 `None`（UI 该 hint 不弹出）

**`scripts/demo_snipe.py`** 在沉船 2510 (140 格仓库, 白绿 24 + 蓝 18) 跑出实例：
- P50 仓价 ≈ 99 万银币、P75 = 125 万、P90 = 160 万
- 推荐区间：safe_floor 69 万 (P50 × 0.7) → snipe_max 144 万 (P75 × 1.15)
- 4000 trials 里匹配窗口的样本数 = 90，可信
- Rationale 是多行中文，可直接喂 Streamlit tooltip

**为什么 R2 是秒仓窗口**：游戏内 R1 出价多数玩家保守（信息不全），R3 同行已经摸清局势开始抬价。R2 是 Ethan 信息优势最大且对手价格未锁定的黄金 1 轮。所以推荐区间偏激进（P75 × 1.15）而非保守均值。

**`docs/tool_roi_table.md` 补充 caveat**：在表头下加 ⚠️ block 说明精品均格 value-ROI=0 不等于无用——它的核心价值是通过整数/2.5 这种 avg 的截断显示规则 pin 死 (cells, count) 对，这是 cells 精度收益不在当前 metric 里。Phase 2.1 可补一列 "cells-error ROI"。

**inference/__init__.py** 同步 re-export `SnipeRecommendation` + `compute_snipe_recommendation`。

测试数：181 → **189 passed**（+8 snipe）。

### C-10: Phase 2 tool-ROI infra — ground truth + synth readings + LOO ROI + 真实地图表 (2026-05-15)

终于把 ROI 表跑出来了。三个新模块 + 一个脚本，落地 25 新单测，再加 `docs/tool_roi_table.md` 把别墅 2407 与沉船 2510 的 ROI 数字 baked-in。

**`inference/ground_truth.py`**（11 单测）

- `BucketTruth(quality, count, total_cells, value_sum, huge_count, items)` + `SessionTruth(map_id, map_name, warehouse_total_cells, buckets)` 数据类
- `sample_session_truth(map_id, *, maps, drops, items, rng)`：复用 `flatten_pool` 抽 K 件 + 展开 n_min..n_max，按 quality 分桶。复刻 `simulation.basic_mc` 的统计分布，但保留 raw `Item` 对象方便下游合成读数
- `is_huge_item(item)`：仅对 q=4 / q=5 / q=6 判定，按 `HUGE_CELLS_PER_QUALITY` 阈值（其他品质永远 False —— 游戏内白绿蓝无 "巨物" 概念）

**`inference/synth_readings.py`**（14 单测）

- `TOOL_SPECS` 静态表登记 7 件已建模道具（普品/良品/精品/珍品 扫描 + 精品 估价/均格 + 珍品估价）；`SESSION_TOOL_SPECS` 单独放 `总仓储空间`（写 SessionObs.warehouse_total_cells）
- `apply_tool(truth, name) → ToolEffect`：每件道具产出 `bucket_patches: dict[q, dict[field, value]]` + 可选 `session_patch`。`普品扫描` 把白+绿合并写到 q=1（沿用 demo_shipwreck 约定）；`精品均格` 调用 `format_value` → `parse_reading` 复刻游戏 2 位截断显示
- `build_session_obs(truth, *, hero, tools, include_aisha_outline, huge_band_inputs) → (SessionObs, total_silver)`：把多件道具读数合并成一个 SessionObs。huge_band 自动按 hero 可见性导出（伊森紫/金/红，艾莎只紫）；可选地把艾莎 R1-R3 outline 当作 free 信息源，pin q=1..4 的 count + total_cells
- 抽检 / 宝光四鉴等 random-item reveal 未建模（Phase 2.1 follow-up）

**`inference/roi.py`**（5 单测）

- LOO 算法核心：每 trial 抽一个 ground truth → 全 kit 推断一次 → 对每件道具 `t`，去掉它再推断一次 → 比较 `|truth_value − inferred_value|`，差值就是 `t` 的 info gain。除以银币价 = ROI
- `_inferred_total_value(top1, obs)`：每个 bucket 优先用 `bucket.value_sum`（exact），其次 `value_range` midpoint，最后才 fallback 到 `cand.total_cells × per_cell_prior`（含 huge 拆分以避免双重计价）
- `compute_tool_roi(map_id, tool_kit, *, ..., per_bucket_top=8) → list[ToolROI]`：参数化的 search width 让单测能 4-5 跑快、生产脚本用 6-8 跑准
- 测试发现：薄 kit 下 ROI 可能为负——道具真值替换掉了"凑巧准"的 prior 导致整体误差变大。这是有意保留的诊断信号而非 bug

**`scripts/compute_tool_roi.py` + `docs/tool_roi_table.md`**

跑别墅 2407 + 沉船 2510 × {Ethan default, Ethan +warehouse, Aisha minimal}，落地真实 ROI 表（n=60 trials/cell, per_bucket_top=6）。**结论非常 actionable**：

| 排名 | 道具 | 银币 | 别墅 ROI | 沉船 ROI | 备注 |
|---|---|---|---|---|---|
| 🥇 | **良品扫描** | 2,500 | +6.6 | +7.3 | **性价比最高**，蓝品扫描每银币挽回 6-7 银币的估值误差 |
| 🥈 | 珍品估价 | 35,000 | +1.6 | +3.3 | 绝对信息量最大（金品估值方差大，单件就值数十万） |
| 🥉 | 普品扫描 | 1,200 | +0.8 | +1.8 | 便宜实用，沉船更值 |
| 4 | 精品估价 | 20,000 | +0.5 | +0.4 | 中规中矩 |
| 5 | 精品均格 | 20,000 | **+0.0** | **+0.0** | **冗余**——给定其他 4 件已在 kit，再加均格不再贡献 value 精度 |
| — | 总仓储空间 | 55,000 | +0.0 (value) | +0.0 (value) | 值无增益，但 cells-side info_gain > 0（薄 kit 下能锚定 cells 预算） |

UI 推荐 hint 直接可挂："本次跑别墅，buy 良品扫描 (ROI≈6.6) 而不是 精品均格 (ROI≈0)，因为后者在你现有 kit 下不再补充信息。"  
艾莎极简 kit (3 件道具) 也跑出 `珍品估价 ROI = +2.3 ~ +3.7`，验证她的 outline pin 是真正的 free 信息源 —— 不用花扫描银币就能让 value-side 推断收紧。

**为何精品均格 ROI = 0**：在已有 `精品估价` (pin 紫品 value_sum) + `普品/良品扫描` (pin 低端 cells) 的前提下，均格读数的"约束作用"已被其它读数覆盖；DSL 的 `value_consistency_score` 与 `is_compatible` 两侧都不再因均格收紧。这反过来也确认了引擎的 joint posterior 不是 over-engineered。

测试数：151 → **181 passed**（+11 ground_truth, +14 synth_readings, +5 roi, -1 合并清理）。

### `6adb7c2` — C-9: notebook 03 outline-术语澄清 + 总仓储 5.5w override + map-fields scope cut (2026-05-15)

用户 2026-05-15 16:40 反馈梳理：

1. **澄清: 03 notebook 的 "outlines" 是艾莎技能**：用户看图后误以为 outline 指道具扫描。加 markdown cell 显式列三类信息来源对比表（艾莎技能 vs 扫描道具 vs 地图提示）并把图标题改成 "Aisha hero skill (free R1-R3 outline reveal) shrinks the warehouse coverage gap by 74% — no tool silver spent in either scenario"。重新 `jupyter nbconvert --execute`，新图 (69KB) 落地。
2. **总仓储空间 = 55_000 银币**（用户之前忘说）：新增 `TOOL_PRICE_OVERRIDES` 字典放工具级精确价 + `tool_price(name, rarity)` helper（先查 override 再 fallback 到 rarity tier）。1 个新单测 pin 55k 数字 + override 行为。
3. **地图字段范围收窄**：用户确认 "9件均价 / 几件总价 / 最高格数藏品 / 最高品质藏品" 这些**对推断没帮助**（指代模糊，没法定位具体物件），引擎不建模。已支持的 count / avg_cells / total_cells / value_sum / value_range / huge_band 字段就够覆盖玩家手输需求。无新代码，省时间。
4. **Phase 2 ROI metric 选 value-error**：用户确认"仓位价格准确性"是核心，metric = `|true_value_sum - inferred_value_sum| 的减小量 / 工具银币成本`；cell-error 作辅助诊断。`ROI = 1` 意味"花 1 银币的工具，估值精度提升 1 银币"——超过 1 就值得买。

测试数：150 → **151 passed**。

### `b70b412` — C-6+C-7+C-8: seal hero skills + loadout refresh + joint posterior + outline-joint demo (2026-05-15)

**C-8 新增 (outline-joint demo + 紫色 huge per-cell 校准)**：

跑 outline + joint 联立 demo 时发现：`estimate_total_cells(quality=4, huge_cells=16)` 会**双重计算**——因为 `PER_CELL_VALUE_HUGE` 没有 key 4，函数 fallback 到"不减 huge_value"，结果 38 non-huge + 16 huge = 54（应该 = 38）。修复：
- `PER_CELL_VALUE_HUGE[4] = 2500`（紫色 4×4 屏风/雷达/防弹衣 均 ~40k, 即 2500/cell；和 default 一致但显式声明可让 estimator 干净减去 huge_value）
- 顺手修了 gold huge 注释/常量不一致：值从 18000 改为 6000（单人郊游快艇 108k/18 ≈ 6000，原值 18000 是 typo）
- 加 1 个新单测 `test_estimate_total_cells_purple_with_huge_avoids_double_count` pin 住正确行为
- 已有测试 `test_per_cell_value_huge_flag` 中"Purple has no huge override" 注释更新（行为不变，但语义现在显式）

新脚本 `scripts/demo_outline_joint.py` 展示 Aisha 的 R1-R3 outline 信息收益（别墅 2407, 109 格仓库 scenario）：
- 不用 outline：joint top-1 总 67 格，仓储 coverage gap = 42 格（white/green/blue 完全没建模，"隐形"占 109 中的 42 格）
- 用 outline：joint top-1 总 98 格，coverage gap = 11 格（剩下的 11 格留给 red 的 value range 弹性）
- **gap shrink 73.8%** —— 这是简历可用的 headline 数字

注意：rare bucket per-bucket cell spread 在这个场景下没变（value reading 太精确已经 pin 死），outline 的价值体现在"low-tier 的诚实记账让 downstream value-density 估算更可靠"。后续可以做更紧凑的场景把 spread shrink 也露出来。

测试数：148 → **149 passed**（+1 purple-huge bug fix test）。

**C-8 后补（per 用户 2026-05-15 16:30 反馈）**：
- 加 `TOOL_PRICE_BY_RARITY` 常量到 `observation.py`：白 1200 / 绿 2500 / 蓝 20000 / 紫 35000 / 金 50000（占位，珍品估价/扫描/总仓储空间精确价后续 probe）。用户提示这些会动态波动，Phase 2 ROI 表应给 ±30% sensitivity band
- 加 1 单测 pin 价格单调递增 + 用户给出的具体数字
- **地图动态信息字段盘点**（关于 "BidMap 给出哪些有用数据"）：
  - `BidMap.col[20]` 是"提示槽位调度器"——它声明"哪轮放什么类型的提示"，**不是**具体数值
  - 具体数值（count / avg_cells / total_cells / value_sum / value_range）是开局后**动态生成**的
  - 4 张截图归纳：地图通常给紫品/金品的 `数量` 或 `均格` 或 `总价` 中的 1-2 个
  - **这些字段全部已经被 `QualityBucketObs` 覆盖**，玩家手输即可，引擎无需新代码；UI 那边可以做 per-map preset 暴露"R1 通常会给紫品 count / R3 通常会给紫品 avg_cells"（未来 UI 工作）
- **澄清: hero ROI ≠ tool ROI**：v2 hero ranking 已交付（hero marginal value），Phase 2 的 ROI 表对比的是**工具组合**（Ethan default vs alt vs Aisha default 的"每银币信息收益"），跟英雄选择解耦。

测试数：149 → **150 passed**（+1 TOOL_PRICE_BY_RARITY 单测）。

**附**: `notebooks/03_inference_demo.ipynb` 通过 `jupyter nbconvert --execute` 预先跑过，所有输出 + 图片已 baked 进文件，用户打开直接看即可，不需要本地重跑（除非要改 scenario 参数）。

**C-7 新增 (joint posterior, 多 bucket 联立收紧)**：

为推断引擎补上跨 bucket 一致性约束。原 `top_k_for_session` 是 greedy：q=6 top-1 一旦选错，后面的 q=5 / q=4 budget 估算连环错。新 `inference/joint.py`：

- `JointHypothesis` dataclass：捕获一组跨 bucket 的 `(quality → BucketCandidate)` 联合赋值，含 `total_cells / bucket_composite / warehouse_penalty / composite`
- `joint_top_k_for_session(session, k=5, per_bucket_top=8, warehouse_slack=10, warehouse_over_weight=0.05)` —— DFS over cartesian of per-bucket top-N + running cells-sum pruning + 软仓储约束。typical 3-5 buckets × top-8 → 远小于 10^4 探索路径，sub-ms 收敛
- `inference/__init__.py` 把核心 surface 都 re-export 出来，外部调用 `from bidking_lab.inference import joint_top_k_for_session` 即可

7 个 joint 单测覆盖：
- 空 buckets → 空结果
- 单 bucket → joint top-1 ≡ per-bucket top-1
- warehouse slack 切掉超出 budget 的 combo
- 等分情况下偏好不超 capacity 的（warehouse_penalty=0）
- **关键场景**：greedy top-1 在仓储紧张时会冲突，joint 必须 demote 那个 top-1 改选第二顺位（仿真 50 格仓 + 30 格蓝扫 + 紫均格 2.5 + 紫估价 37500 的场景）
- 3 bucket × top-8 性能：< 1s
- 输出按 composite 升序

**C-6（同 commit）：seal 英雄技能 + 道具组合常量校准**：

1. 补 6 个 hero_skills 单测覆盖 C-5 的新机制：
   - `InfoType.OUTLINE_QUALITY` 位于 `OUTLINE (0.3) < OUTLINE_QUALITY (0.85) < FULL (1.0)` 之间
   - 艾莎 4 stages 各自 fire OUTLINE_QUALITY on q=1..4（disable timing 测）
   - 艾莎紫色 R4 因 timing weight 急剧下降，确认 R4 > R3 > R2 > R1 的 timing 折扣阶梯
   - 伊森 R1 random_categories=5：固定 rng seed 重现 5 个被命中 / 5 个 R5-only 的精确 split
   - 伊森 R1 无 rng → 取 first-5 sorted category id 的确定性 fallback
   - OUTLINE_QUALITY 同时命中时优于 OUTLINE 的 max 行为
2. 道具组合常量校准 (按用户 2026-05-15 最新口径)：
   - `ETHAN_DEFAULT_LOADOUT = (普品扫描, 良品扫描, 精品估价, 精品均格, 珍品估价)` —— 5 slot, 4 cheap + 1 gold
   - 新增 `ETHAN_ALT_LOADOUT`：把精品估价换成 `随机抽检(1)` 给 category 信息（让 brute force 估价可以先按 category 剪枝）
   - `AISHA_DEFAULT_LOADOUT = (随机抽检(2), 随机抽检(1), 宝光四鉴, 珍品估价, 总仓储空间)` —— 5 slot
   - 新增 `STANDARD_LOADOUTS: dict[HeroMode, tuple[str, ...]]` 便于 Phase 2 contrast MC 自动取
3. **集装箱降级**：PROGRESS.md "用户聚焦" 章节标注：集装箱不进推断引擎，UI 直接显示 baseline MC 均值即可
4. **事件图策略**：明确不为 5.15 patch 临时事件图改 BidMap parser（5 天后下线）；推断引擎跟具体 map_id 解耦，玩家手动 hint 输入流程已覆盖

测试数：132 → **148 passed**（+6 hero skills, +2 loadout, +1 alt-loadout, +7 joint posterior）。

**用户后续指示**（直接影响后续开发优先序）：
- 宝光四鉴 / 抽检：**不进入推断引擎模型**。宝光是用户为不空过轮次的自主选择；抽检主要为提升穷举效率，非必输入。引擎主要推断"格子数和地图"
- commit 节奏：不必频繁 commit，大进展再来；进度有 PROGRESS.md 记录

### `28ecfef` — docs+probe: detect 2026-05-15 game patch, document map-info DSL analysis (2026-05-15)

游戏 2026-05-15 patch 实测发现：
- BidMap 21 列 → 23 列，105 行 → 125 行（+20 张事件图）
- Item 1132 → 1134，Drop 608 → 629
- 旧 col[10] 在新 schema 里去到 col[11]，整体右移 1
- 新 col[8] 和 col[22] 是 patch 加的 flag

加 3 个 probe 脚本：
- `probe_table_column_drift.py`：一键检测各表实际列数 vs 预期
- `probe_bidmap_new_layout.py`：对照新旧 schema 逐列 dump
- `probe_map_info_columns.py`：按地图名字定位截图里的 4 张事件图记录

关键认知更正：截图里的 "金品 count=3", "紫品均格 2.54" 等具体数值**不在 BidMap 任何静态列里**，是 **session 开局后基于实际抽样动态算出来**的。BidMap col[20] (旧 round_category_hints) 实际是"提示槽位调度器"——告诉游戏"哪轮放提示、风格类型代码"，具体数值游戏跑时算。这意味着 inference engine 不需要等 BidMap 改完——玩家手动把看到的数值输入 QualityBucketObs 字段即可。

`parse_bid_map_row` 改为遇到 != 21 列时显式报错并提示 patch 信息，避免静默错误解析。`_parse_drop_ref` 回滚到严格 4-元素检查（之前为了过 23-col 试错放松了）。

OBSERVATIONS.md 新增 Checkpoint #10 完整记录 patch 细节、动态生成假说、4 张事件图归属、下次开工优先序。PROGRESS.md 新增"当前剩余工作"章节给项目状态盘点 + "用户聚焦：别墅 + 沉船优先"明确 Phase 2 范围收窄。

132 tests 仍全绿；纯文档+probe 增量。

### `bbbdd40` — C-5: hero skill rewrite — Aisha 4-stage outline+quality, Ethan 5-categories (2026-05-15)

2026-05-15 用户提供 5 张游戏内截图（沉船 R4 / 集装箱 R4 / 网吧 R2 / 别墅 R3 / 沉船 R2 round info panel），逐条解读后实锤了之前怀疑的两个建模偏差，并发现地图自带信息 DSL 比 `round_category_hints` 丰富得多。详见 OBSERVATIONS.md Checkpoint #9。

`hero_skills.py` 关键改动：
- **新增 `InfoType.OUTLINE_QUALITY = 0.85`**：介于 QUALITY (0.7) 和 FULL (1.0) 之间，对应"轮廓+品质"复合信号
- **新增 `SkillEffect.random_categories: int = 0`**：替代 max_items 的不正确硬编码，per-trial 真正随机抽 N 个分类
- **艾莎 (103) 重写为 4 stages**：R1=白, R2=绿, R3=蓝, R4=紫，每轮一个 OUTLINE_QUALITY effect，技能名"遗珍慧眼"（截图实锤；游戏 Hero.txt col[2] 描述的"R1=蓝, R2=绿, R3=白"3 轮是基础等级，col[10] 的 4 个 effect_id 对应 4 级升级）
- **伊森 (208) R1 改为 `random_categories=5`**：替代旧的 max_items=5（之前误以为是 5 件物品），现在反映"5 of 10 random categories"语义；技能名"空间觉知"
- `compute_info_score` 新增可选 `rng: random.Random` 参数，hero_value MC 每 trial 用 numpy rng 派生 python rng 传入，保 reproducibility

v2 ranking 大改：
- **别墅 2407**：伊森从 +13.7% (A) 跃到 **+20.5% (#3, S-tier)**；艾莎从 +22.4% 微调到 +20.3%
- **沉船 2510**：伊森 **+15.3% (#2)**；艾莎 +15.5% (#4)；玛丽亚 +15.3% (#3)；索菲 +16.9% (#1)；都进 S-tier

Phase 1A 文档（`PROGRESS.md` 英雄表 + OBSERVATIONS.md）同步更新。

待做（已记 TODO）：probe BidMap.txt 找剩下 4 种地图信息列（gold count / gold total_cells / purple avg_cells / random_reveal），伊森 R2-R4 条件触发建模留 Phase 2。

132 tests 仍全绿（无新增测试；下次校准时为 OUTLINE_QUALITY + random_categories 补单测）。

### `a823a21` — docs: append commit log to PROGRESS.md + Checkpoint #8 to OBSERVATIONS.md (2026-05-15)

按 2026-05-15 用户要求，PROGRESS.md 长出一个 append-only "提交历史" 章节，让每次 commit 的设计 rationale 留在 in-repo 备查。覆盖从初始 scaffold 到 C-4.2 的所有 commit，反时间序。

OBSERVATIONS.md 新增 Checkpoint #8，记录 Phase 1A 推断引擎 MVP 发现（截断显示规则确认、per-cell 价值 prior 校准、沉船 R4 demo 通过、巨物 band UX、英雄不对称规则、标准道具组合、Phase 2 ROI 题目），外加用户 2026-05-15 实测确认的两个事实：

- 伊森 outline UI **没有** category-on-hover 提示；玩家必须用地图爆率先验猜分类。验证 Ethan outline 应建模为 `quality_hint=None`（纯形状信号）
- 艾莎实战 4 轮（白起）和 Hero.txt col[2] 的 3 轮（蓝起）不一致；col[10] 4 个 effect id 对应 4 级升级。`hero_skills.py` 和 v2 ranking 留待截图证据再改

纯文档变更；tests 不动（132 passed）。

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
