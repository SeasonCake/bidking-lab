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
Layer 2 (计算层)  MC / 英雄模型 / 鲁棒估价 / 推断引擎 / 装箱模型  [~55%]
       ↑
Layer 1 (数据层)  Base64解码 → pydantic schema    [~95%]
```

### 目录结构

```
bidking-lab/
├── src/bidking_lab/
│   ├── extract/          # 每张表一个模块：tables.py, item_table.py, drop_table.py, bid_map_table.py
│   ├── simulation/       # basic_mc.py, bidding.py, hero_skills.py, hero_value.py, robust_value.py
│   ├── inference/        # (Phase 1A 待建) display.py, observation.py, inference.py
│   ├── data/             # quality.py 等辅助
│   └── config.py
├── data/
│   ├── raw/tables/       # 游戏原始 Tables/*.txt (gitignored)
│   └── processed/        # 派生 JSON (committed): items.json, maps.json, heroes.json 等
├── notebooks/            # 01_map_value_distribution, 02_hero_ranking
├── scripts/              # 探查/分析/demo 脚本
├── tests/                # 53 tests (pytest)
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

### 当前聚焦的 4 英雄（Phase 1A+ 测试范围）

| 英雄 | 信息维度 | 道具协同方向 |
|---|---|---|
| **玛丽亚(108)** | 直接报价（低品质 70%+ 覆盖） | 缺高品质 → 配 X品估价 / 至宝估价 |
| **索菲(107)** | 品质渐进（R1 全 + 每轮 2） | 缺形状/价值 → 配 X品均格 / 至宝估价 |
| **艾莎(103)** | 轮廓渐进（蓝→绿→白） | 形状强相关下变强 → 配宝光 X 鉴 |
| **伊森(208)** | 全品质轮廓扫格子 | 看到所有形状 → 配 X品均格 / N格均价 做精确估价 |

去掉了原 S 级的加布里埃拉(104)：与索菲功能重叠，且伊森在形状→价值生效后潜力更高。

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

### Phase 1A：信息推断引擎（最高优先，地基已完成 2026-05-15）

**核心思想**：把每个**道具读数 / 英雄技能揭示 / 地图自带提示**都视为隐变量"真实物品集"的约束条件，做贝叶斯反推。

```
真实物品集 X ← drop pool [先验]
        + 多个观测：道具读数 / 英雄揭示 / round_category_hints
        ↓
后验 P(X | 观测) → 估价 / 决策
```

**关键洞察（用户提供，已验证）**：均格类道具的小数显示泄漏分母信息（"2.9" 精确除尽，"2.90" 含尾零 = 约到的，分母不整除10）→ 可以反推 (品质×件数×总格数)。

**实现路径**：
- `display.py` 显示模拟器（实数 ↔ 游戏字符串，处理尾零规则）
- `readings.py` 字符串解析为 `Reading(value, exact, precision)`
- `observation.py` 统一接口 + 各类 Observation（ScanCells / Count / AvgCells / Value / AvgValuePerCell / Outline / Quality / RoundCategory / HeroSkill）
- `inference.py` 拒绝采样器
- `evaluate.py` 后验估价 + 决策建议

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
pytest -q  # 应该 64 passed

# 关键入口
python scripts/demo_hero_value.py --trials 10000   # 英雄排名
python scripts/demo_simulate_maps.py               # 地图价值
python scripts/analyze_shape_quality.py            # 形状×品质分析
python scripts/compare_raw_vs_robust.py            # raw vs robust 估价对比
python scripts/probe_round_categories.py           # col[19] 提示密度全扫描
python scripts/probe_rare_red_items.py             # 长尾红物概率
python scripts/probe_distinctive_shapes.py         # 形状指纹字典

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
