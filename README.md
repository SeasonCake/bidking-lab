# bidking-lab

> **一个把游戏「竞拍之王（The Bid King）」当成概率推断 / 蒙特卡洛模拟实验室的本地工具链。**
> A local probabilistic inference engine + Streamlit dashboard for the auction game *The Bid King*, with a focus on quantifying information value (hero skills, battle items, map hints) and producing actionable bid recommendations.

<!-- TODO: 一张顶部 hero 截图（推荐：Streamlit 主页 + 一个读数输入示例 + 出价分布图，1280×640 左右），文件放到 docs/assets/hero.png 后取消下面这行注释 -->
<!-- ![bidking-lab Streamlit dashboard](docs/assets/hero.png) -->

<!-- TODO: 演示视频链接（建议用 GitHub Issue 上传 .mp4 后把那个 URL 粘到下面） -->
<!-- 📹 **[完整演示视频（30 秒）](https://github.com/<user>/<repo>/issues/X#issuecomment-XXX)** -->

---

## 这个项目是什么 · TL;DR

游戏《竞拍之王》的核心玩法是**信息不完美下的密封式拍卖**：玩家用银币买道具揭示部分藏品信息（"紫品总格 35"、"金品均价 9400/格"），再据此决定每场仓库出多少钱。

**bidking-lab 把这个决策过程数学化**：

- **数据层**：解码游戏的 `Tables/*.txt`（base64 + TSV）→ 1132 件藏品 / 64 件道具 / 105 张地图 / 20 个英雄 全部入 schema
- **推断层**：玩家输入观测 → 联合后验推断每个品质 bucket 的 `(总格数, 件数)` top-3 候选；条件 MC 输出出价分布 P25/P50/P75/P90 + 秒仓 / 放仓推荐
- **价值评估层**：Leave-one-out 量化每件道具的"每银币挽回价值"，给出在指定地图 / 英雄下的道具性价比榜
- **交付层**：Streamlit 中文 UI + 5 册 Jupyter notebook + 端到端 CLI 脚本

非官方爱好项目，**不附带任何游戏资源**——只解码玩家本地安装的数据，并产出*推导后的 JSON*。

---

## 演示画廊 · Screenshots

<!-- TODO: 下面每个 placeholder 对应一张截图。建议尺寸 1100×620，PNG，放到 docs/assets/ -->

### 1. 读数输入与候选预览
<!-- ![读数输入](docs/assets/01_inputs.png) -->
> 玩家把游戏里看到的每一个数填进对应品质 bucket（总格 / 件数 / 均格 / 总价 / 巨物档），UI 实时给出 top-3 候选预览，越填越收紧。

### 2. 出价分布图 + 秒仓 / 放仓推荐
<!-- ![出价分布](docs/assets/02_bidding.png) -->
> 条件 MC 1000 样本 → P25/P50/P75/P90 分位 → 秒仓上限 / 放仓阈值。小样本场景自动走"低置信"兜底（⚠️ 标记）而非静默失败。

### 3. 道具 ROI 性价比榜
<!-- ![道具 ROI](docs/assets/03_roi.png) -->
> 每件道具的 leave-one-out 价值挽回 ÷ 银币售价。新增玩家眼估格数噪声模型——总仓储工具在 σ=10 cells 下 ROI ≈ +0.45（恢复 24.5K 价值 ÷ 55K 售价）。

### 4. 联合推断 top-3 候选（实验性）
<!-- ![联合推断](docs/assets/04_joint.png) -->
> DFS + 仓库剪枝 + 总件数交叉约束。信息丰富场景能把 top-1 composite 拉到 0.342，其他候选差距明显，证明引擎确实"用上了"每个 bucket 的硬约束。

---

## 为什么做这个 · Why

| 玩家原始痛点 | 数学化形态 | bidking-lab 给出的答案 |
|---|---|---|
| 道具读数到底有没有用？带哪几件最划算？ | Tool value attribution under partial observation | LOO ROI engine（道具 ROI 排行 + 价格/英雄/噪声敏感性） |
| 看到"紫品均格 2.90"，我能推回紫品到底几格几件？ | Decimal-precision leakage from truncated UI display | `display.py` 截断显示规则 + 候选枚举，能区分 2.9（精确）vs 2.90（尾零→约的） |
| 这个仓应该出多少？秒还是放？ | Conditional Monte Carlo on observed warehouse cells | 秒仓 / 放仓 dual gate + 三阶 fallback（含低置信兜底） |
| 不同地图、不同英雄，最优配置一样吗？ | Hero × Map × Tool-kit contrast experiments | 4 册分析 notebook + Streamlit 自由组合界面 |

---

## 30 秒上手 · Quick start

```powershell
cd bidking-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# 1) 跑测试（205 个单测）
pytest -q

# 2) 启动 Streamlit 主界面
streamlit run app/streamlit_app.py

# 3) 终端跑三场景端到端 demo（看不到图，看数）
python scripts/demo_scenarios.py

# 4) 浏览端到端案例 notebook（含分布直方图）
jupyter notebook notebooks/05_end_to_end_case.ipynb
```

> Windows / PowerShell + Python 3.13 验证过；macOS / Linux 应该也行（路径要相应改）。

设置游戏根目录（可选，仅 re-extract 游戏表时需要）：

```powershell
$env:BIDKING_GAME_ROOT = "C:\path\to\steamapps\common\BidKing"
.\scripts\copy_game_tables.ps1               # 拷 Tables/*.txt 到 data/raw/
python scripts\build_processed_data.py       # 重新生成 data/processed/*.json
```

---

## 架构 · Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 3 · Surface                                                   │
│   app/streamlit_app.py           — 4-tab UI（中文）                 │
│   notebooks/01..05_*.ipynb       — 探索 + 端到端 case               │
│   scripts/demo_*.py              — CLI 端到端校验                   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────┐
│ Layer 2 · Compute                                                   │
│   inference/                                                        │
│     ├── display.py             — 游戏 2-dp 截断显示规则 + 候选枚举  │
│     ├── observation.py         — SessionObs / QualityBucketObs DSL  │
│     ├── joint.py               — DFS 联合后验 + 仓库剪枝            │
│     ├── synth_readings.py      — 11 件道具 → 读数 DSL               │
│     ├── snipe.py               — 秒仓/放仓 gate + 三阶 fallback     │
│     ├── roi.py                 — LOO 道具 ROI + 眼估噪声模型        │
│     └── ground_truth.py        — 地图采样器（drop pool 加权）        │
│   simulation/                                                       │
│     ├── basic_mc.py            — 全图 MC                            │
│     ├── hero_value.py          — Timing-aware 英雄技能价值          │
│     ├── bidding.py             — 出价经济模型                       │
│     └── robust_value.py        — 长尾稀有红物降权                   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────┐
│ Layer 1 · Data                                                      │
│   extract/                                                          │
│     ├── bid_map_table.py       — 105 张地图 schema (21 列)          │
│     ├── drop_table.py          — 掉落池 (item_id × weight)          │
│     ├── item_table.py          — 1132 件藏品                        │
│     └── battle_item.py         — 64 件道具（已 verify 中文命名）    │
│   data/raw/tables/*.txt         — 玩家本地游戏文件（gitignored）    │
│   data/processed/*.json         — 我们生成的 schema 化 JSON         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 关键技术亮点 · Engineering Highlights

### 1. 把"游戏 UI 显示精度"做成信息源
玩家看到「紫品均格 2.90」时，**尾零携带信息**——意味着真实值被截断在 `[2.90, 2.91)` 区间，分母（件数）大概率不整除 10。`inference/display.py` 实现了游戏的 floor-at-2dp 显示规则反推，能用 `parse_reading("2.90")` 区分精确值 vs 截断近似。在场景 A 实测中，这一条约束把 q=4 候选从 ~20 个收紧到 1 个。

### 2. Leave-one-out 道具 ROI + 玩家眼估噪声模型
原始 ROI 实现把"不带总仓储工具"翻译成"capacity = 159 fallback"，结果一件 55K silver 的工具 ROI 显示为 0。引入 `player_warehouse_noise_std` 后：

| σ (cells) | 总仓储 ROI | 解读 |
|---|---|---|
| 0  | 0.000 | 玩家完美眼力 → 工具确实无价值 |
| 10 | **0.446** | 默认现实玩家 → 回收 24.5K 价值 ÷ 55K 售价 |
| 15 | 0.924 | 新手 → 几乎回本 |

ROI tab 把 σ 暴露成滑块，灵敏度图玩家自己拉。

### 3. 三阶 fallback 的秒仓 / 放仓 gate
小仓 / 稀采样场景下，硬阈值 `min_matching_samples=30` 会让 29 个样本静默丢失。新方案：
1. 严格阈值 → 高置信推荐
2. warehouse-only 子集 ≥ 严格阈值 → 正常
3. **warehouse-only ≥ 放宽阈值 10 → 返回带 `low_confidence=True` 的推荐 + ⚠️ rationale**
4. 仍不足 → 才 return None

UI 在低置信场景把 `st.success()` 替换为 `st.warning()`，玩家一眼看到"这个数仅供参考"。

### 4. 工程化的 schema-first 数据层
所有游戏表先 decode 成 TSV → pydantic schema 校验 → typed JSON。命名跟原始数据源对齐（C-25 修过一次重大命名错位：游戏的"优品=紫、极品=金、珍品=红"，跟我代码里早期的"精品/珍品"完全错位；统一重命名后 202 单测继续绿）。

### 5. 4 段式 TROUBLESHOOTING.md（22 条踩坑）
所有非显然的踩坑（Base64 表 / GBK 编码 / `pyarrow` × `numpy 2.x` / `st.number_input` 吃尾零 / matplotlib 中文字体回退 / ROI baseline 漏洞 ……）都按 **症状 / 原因 / 修法 / 教训** 四段式归档，便于复盘和给协作者交接。

---

## 量化产出 · Findings

完整结论看 [`PROGRESS.md`](PROGRESS.md) 和 [`OBSERVATIONS.md`](OBSERVATIONS.md)，简表：

| 维度 | 数字 |
|---|---|
| 解析的游戏表 | 6 张（BidMap / Drop / Item / BattleItem / Hero / Item_Type） |
| schema 化的实体 | 1132 件藏品 · 64 件道具 · 105 张地图 · 20 个英雄 |
| 单测数 | **205**，全绿 |
| Streamlit UI tabs | 4（读数输入 / 出价推荐 / 道具 ROI / 联合推断·实验性） |
| Notebook | 5 册（map 价值分布 / 英雄排名 / 推断 demo / ROI snipe / 端到端 case） |
| 项目完成度 | ~92%（剩余主要是简历包装） |
| Commit 历史 | C-1 ~ C-26，每条都有展开版设计决策记录 |

---

## 目录 · Layout

| 路径 | 用途 |
|---|---|
| `src/bidking_lab/extract/` | 6 张游戏表的解码 + schema |
| `src/bidking_lab/inference/` | 推断引擎：display / observation / joint / snipe / roi |
| `src/bidking_lab/simulation/` | MC 模型：basic_mc / hero_value / bidding / robust_value |
| `app/streamlit_app.py` | Streamlit 中文主界面 |
| `notebooks/` | 5 册分析 + 端到端 case notebook |
| `scripts/` | 数据生成 / 端到端 demo / 一次性 probe |
| `tests/` | 205 单测 |
| `data/raw/` | 玩家本地游戏文件（gitignored） |
| `data/processed/` | 我们生成的 schema 化 JSON（入 git，便于无游戏的人也能跑） |
| `docs/project_vision.md` | 原始三层架构设计 |
| **`PROGRESS.md`** | **新协作者起点**：项目全貌 + 当前状态 + 路线图 |
| **`OBSERVATIONS.md`** | **技术发现日志**：每个 checkpoint 的关键发现 |
| **`TROUBLESHOOTING.md`** | **22 条踩坑**：四段式（症状/原因/修法/教训） |

### 我们 ship 的数据 vs 我们不 ship 的

`data/processed/*.json` 是我们**生成的**派生数据（字段名我们选、过滤过、schema 校验过），不是游戏原文件的字节副本——所以无游戏的人也能跑模拟器。`data/raw/tables/*.txt` 跟游戏内文件字节一致，**不入 git**。

| File (in repo) | What | Size |
|---|---|---|
| `data/processed/items.json` | 1132 items: id, name, quality (0–6), value, shape, tags … | ~520 KB |
| `data/processed/items_droppable.json` | 883 actually drop-able items（去掉系统物品） | ~425 KB |
| `data/processed/battle_items.json` | 64 battle items with quality_color + effect | ~18 KB |
| `data/processed/heroes.json` | 20 heroes with skill descriptions | ~4 KB |
| `data/processed/maps.json` | 105 maps (summary form) | ~25 KB |

---

## 技术栈 · Tech Stack

- **Python 3.13** · pydantic（schema 校验）· numpy / scipy（MC + 后验）· matplotlib（分布图）
- **Streamlit**（UI）· Jupyter（分析交付物）
- **pytest**（205 单测，覆盖解码 / 推断 / ROI / snipe / hero_value）
- **PowerShell**（数据同步脚本；macOS/Linux 等价 bash 已留接口）

---

## 法律 · Attribution & License

非官方爱好项目，**未授权也不附属**于游戏或 Steam。游戏资源版权归原作者所有，**不分发**任何 ripped binary。

仓库**源码** MIT License（见 [`LICENSE`](LICENSE)）。LICENSE 不授予游戏资源、商标、或本地拷贝在 `data/raw/` 下的游戏数据文件任何权利。

灵感与前期工作：
- [Jrinky908/bidking](https://github.com/Jrinky908/bidking)（Monte Carlo 摘要、OCR notebook）
- [nql1314/bidking-booooot](https://github.com/nql1314/bidking-booooot)（Apache-2.0；架构 / 日志解析 / 网格视图参考）— 详见 [`docs/upstream_references.md`](docs/upstream_references.md)

---

## 路线图 · Roadmap

完整路线图在 [`PROGRESS.md`](PROGRESS.md)。短版：

**已完成**（C-1 ~ C-26）
- ✅ 6 张游戏表解码 + schema
- ✅ 推断引擎 v2（joint posterior + 仓库剪枝 + 截断显示规则 + 巨物分级）
- ✅ Streamlit 中文 UI（4 tab + 地图静态信息面板）
- ✅ LOO 道具 ROI + 玩家眼估噪声模型
- ✅ 秒仓 / 放仓 dual gate + 三阶 fallback
- ✅ 5 册分析 notebook + 端到端 case
- ✅ 205 单测全绿 · 22 条 TROUBLESHOOTING

**剩余**（可选）
- ⏳ 顶层简历向 README（**就是这份**，本次完工）
- ⏳ Streamlit 实操截图 + 演示视频（待补图）
- ⏳ BidMap 23-列兼容（2026-05-15 活动图 patch；不影响 runtime）

**明确 skip**（用户拍板）
- per-item observation 接口（抽检 N / 宝光 N 鉴）
- 抽检 ROI 建模

---

<sub>Made with too much coffee · 2026-05-15</sub>
