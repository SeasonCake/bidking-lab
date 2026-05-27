<p align="right">🌐 <a href="./README.md">English</a> · <strong>中文</strong></p>

# bidking-lab

> **一个把游戏《竞拍之王》当成概率推断 / 蒙特卡洛模拟实验室的本地工具链——把英雄技能、道具读数、地图先验全部量化成可执行的出价建议。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/tests-431_passing-2ea043)](./tests)
[![Status](https://img.shields.io/badge/status-Phase_1A_推断稳定-blueviolet)](./PROGRESS.md)

---

## 演示 · Demo

https://github.com/user-attachments/assets/9fb463dc-ca85-4fc0-b10e-56b81091a5a8

> 30 秒走查：选地图 → 手填或侧栏 OCR 抓屏填入读数 → 切到「出价推荐」看价值分布、各品质后验与分析估算。

### 截图

<table>
<tr>
<td width="50%" align="center"><strong>1. 读数输入 + OCR 侧栏 + 实时候选预览</strong><br/><img src="./docs/assets/01-inputs.png" alt="读数输入" /></td>
<td width="50%" align="center"><strong>2. 出价推荐 — MC 直方图 + 各品质后验表</strong><br/><img src="./docs/assets/02-bidding.png" alt="出价建议" /></td>
</tr>
</table>

> **左**：三个主 tab（读数输入 / 出价推荐 / 道具 ROI）。读数页各字段旁标注作用域（MC / 枚举 / 仅分析估算）；侧栏可 OCR 抓屏预填；下方候选预览即使显示 ⚠️ **无合法候选**，也不阻断上方 MC 推理（硬字段仍在 `state` 里）。
> **右**：默认 **3000** 次 MC（滑块 500–5000），条件分布直方图 + P25/P50/P75/P90、各品质 bucket 后验卡片与分析估算区间。秒仓/放仓仍为**实验功能且默认隐藏**。

---

## 这个项目是什么 · TL;DR

游戏《竞拍之王》的核心玩法是**信息不完美下的密封式拍卖**：玩家用银币买道具揭示部分藏品信息（"紫品总格 35"、"金品均价 9400/格"），再据此决定每场仓库出多少钱。

**bidking-lab 把这个决策过程数学化**：

- **数据层**：解码游戏的 `Tables/*.txt`（base64 + TSV）→ 1132 件藏品 / 64 件道具 / 105 张地图 / 20 个英雄 全部入 schema
- **推断层**：玩家输入观测 → 联合后验推断每个品质 bucket 的 `(总格数, 件数)` top-3 候选；条件 MC 输出出价分布 P25/P50/P75/P90 + 秒仓 / 放仓推荐
- **价值评估层**：Leave-one-out 量化每件道具的"每银币挽回价值"，给出指定地图 / 英雄下的道具性价比榜
- **交付层**：Streamlit 中文 UI + 5 册 Jupyter notebook + 端到端 CLI 脚本

非官方爱好项目，**不附带任何游戏资源**——只解码玩家本地安装的数据，并产出*推导后的 JSON*。

当前优化路线见 [`docs/optimization_roadmap.zh-CN.md`](docs/optimization_roadmap.zh-CN.md)。

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

### 玩家 · Release 包（推荐）

1. 打开 [GitHub Releases](https://github.com/SeasonCake/bidking-lab/releases) 下载 **`bidking-lab-v1.0.0.zip`**
2. 解压后双击 **`start_ui.ps1`**
3. 浏览器打开 http://localhost:8501

详见 [`RELEASE_QUICKSTART.zh-CN.md`](RELEASE_QUICKSTART.zh-CN.md)。

### 开发者 · 从源码

```powershell
cd bidking-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

# 1) 日常 smoke test（跳过真实 OCR 图片回归，约 10 秒）
.\scripts\test_smoke.ps1

# 2) 跑全量测试（431 个单测，含真实 OCR 图片回归）
pytest -q

# 3) 启动 Streamlit 主界面
streamlit run app/streamlit_app.py

# 4) 终端跑三场景端到端 demo（看不到图，看数）
python scripts/demo_scenarios.py

# 5) 浏览端到端案例 notebook（含分布直方图）
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
│   notebooks/01..07_*.ipynb       — 探索 + 端到端 + 读数/MC 性能       │
│   scripts/demo_*.py              — CLI 端到端校验                   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────┐
│ Layer 2 · Compute                                                   │
│   inference/                                                        │
│     ├── display.py             — 游戏 2-dp 截断显示规则 + 候选枚举  │
│     ├── observation.py         — SessionObs / QualityBucketObs DSL  │
│     ├── joint.py               — DFS 联合后验 + 仓库剪枝            │
│     ├── posterior.py           — 自适应 per-bucket MC filter +      │
│     │                            后验分位（2026-05-16）             │
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

### 3. Per-bucket MC filter（2026-05-16 修复）
2026-05-16 一次实操发现出价 hint 的 MC 滤波**只看仓库总格**，用户填的其他字段（每品质 cells / count / value / 巨物档）全部被静默忽略，导致信息充分场景下 2× 过估。新增的 `inference/posterior.py`（260 行）做自适应多约束滤波：

- 5 类观测（`cells / count / value_sum / value_range / huge_band`）全部成为 MC filter
- 三阶 tolerance（±2 → ±4 → ±8 cells），样本不足 30 时自动放宽并标 `low_confidence`
- **`total_cells = 0` / `count = 0` 视为精确断言**——任何 widen 档都不放宽，保证"确认无红"是硬约束
- 新增"各 bucket 后验估计"面板：每个品质的 cells / count / value 的 P10/P50/P90 + 该 bucket 空概率

地图 T2 2405（仓库 72 cells）实测：
- 修复前：median = 369K silver（vs 实测 ~150K 高估 2.5×）
- 修复后：median = 146K silver，n=16/2500（低置信），P(红空) = 100%

### 4. 工程化的 schema-first 数据层
所有游戏表先 decode 成 TSV → pydantic schema 校验 → typed JSON。命名跟原始数据源对齐（C-25 修过一次重大命名错位：游戏的"优品=紫、极品=金、珍品=红"，跟我代码里早期的"精品/珍品"完全错位；统一重命名后 202 单测继续绿）。

### 5. Capture：主屏抓屏 → OCR 预填读数（C-35~39）

- 侧栏 **抓取当前屏幕**（`mss` + 信息区 ROI）；识别结果写入读数 tab，**不**自动填仓库格数。
- 换图/换类别会 **清空读数** 并取消进行中的后台 MC（C-39）；OCR 残留导致预览 ⚠️ 见 **#42**。
- 推断慢多为 **MC 采样冷缓存**（`sample_ms`），见 [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) **#41**；启动已改为 OCR 首次使用时按需加载，见 **#40**。
- 演示 notebook：[`07_capture_readings_and_mc_perf.ipynb`](notebooks/07_capture_readings_and_mc_perf.ipynb)。

### 6. 42 条 TROUBLESHOOTING.md，四段式踩坑归档
所有非显然的踩坑都按 **症状 / 原因 / 修法 / 教训** 四段式归档。若「填了一项 MC 分位或候选突然变了」，先查 [**#33 — MC 与枚举影响矩阵**](TROUBLESHOOTING.md#33-各字段对-mc--枚举的影响矩阵设计预期)。

### 7. 把已识别具体巨物变成一等 observation
`BIG_ITEMS_BY_SHAPE`（紫/金/红 ~20 件唯一形状巨物）直接喂进每个品质的"巨物数量"下拉框：玩家能选 `★ 单人郊游快艇 (18格·106,500)` 精确锁定格数。`huge_cells_override` 主要服务**枚举 + 分析估算**（`min_huge_cells()` → `candidates_for_bucket` → `compute_analytical_estimate`）。MC 仍只按 **巨物件数 band** 过滤（设计分层，见 TROUBLESHOOTING #31）。

### 8. 推断字段分层 + 低风险 backlog 收口（2026-05-17）
- **MC**：cells / count / value_sum / value_range / huge_band。
- **枚举**：另加 avg_cells、avg_value、★ override、Item-DB boost、物理格数上限。
- **≥4 项联合读数**：仅枚举路径放宽 `avg_value` 容差（C-31b）。
- **P0-B（C-32）**：MC fallback 时 `_fallback_hard_buckets` 保留 `huge_cells_override`（罕见路径一致性，见 OBS #32）。
- **暂缓**：秒/放仓 UI（P0-A）、均价/★格数进 MC（P2/P3）。

### 9. 哪些输入会动 MC？哪些只动枚举？（[TROUBLESHOOTING #33](TROUBLESHOOTING.md#33-各字段对-mc--枚举的影响矩阵设计预期)）

| 输入 / 改动 | MC 仓库 P25–P90 | 候选预览 / 分析估算 |
|---|---|---|
| 紫/金/红 `cells`、`value_sum`、巨物 **件数 band** | ✅ 会 | ✅ 会 |
| 红 `total_cells=0` / 勾选「已确认无红」 | ✅ **硬约束**，P50 明显下降（正常） | ✅ 会 |
| 红 `huge_band` | ✅ 会（仅件数） | ✅ 会 |
| 均格、均价 | ❌ 不会 | ✅ 仅枚举/分析 |
| ★ 具体巨物（`huge_cells_override`） | ❌ 不会（MC 只看件数） | ✅ 会 — 精确格数（如游艇 18） |
| 只选「1个」不选 ★ | MC 只过滤件数 | 占格下限：紫 **10**、金/红 **12**；游艇须选 ★ |
| Item-DB 单品加速（总价+件数=1 命中） | ❌ 不会 | ✅ 只重排候选 |
| C-32 fallback 保留 override | 仅罕见 fallback | 完整 session 不变 |

**巨物默认（设计拍板）**：占格用该品质**最小标准巨物**；估值用 `PER_CELL_VALUE_HUGE`（金≈7000/格、红≈30000/格），与占格分开。完整表见 [TROUBLESHOOTING #33](TROUBLESHOOTING.md#33-各字段对-mc--枚举的影响矩阵设计预期)。

---

## 量化产出 · Findings

完整结论看 [`PROGRESS.md`](PROGRESS.md) 和 [`OBSERVATIONS.md`](OBSERVATIONS.md)，简表：

| 维度 | 数字 |
|---|---|
| 解析的游戏表 | 6 张（BidMap / Drop / Item / BattleItem / Hero / Item_Type） |
| schema 化的实体 | 1132 件藏品 · 64 件道具 · 105 张地图 · 20 个英雄 |
| 单测数 | **431**，全绿 |
| Streamlit UI tabs | 4（读数输入 / 出价推荐 / 联合筛选 / 道具 ROI） |
| Notebook | 5 册（map 价值分布 / 英雄排名 / 推断 demo / ROI snipe / 端到端 case） |
| Phase 1A 推断 | **稳定** — 低风险项已落地；秒/放仓 UI 关闭 |
| Commit 历史 | C-1 ~ C-44，详见 PROGRESS 提交历史 |

---

## 目录 · Layout

| 路径 | 用途 |
|---|---|
| `src/bidking_lab/extract/` | 6 张游戏表的解码 + schema |
| `src/bidking_lab/inference/` | 推断引擎：display / observation / joint / posterior / snipe / roi |
| `src/bidking_lab/simulation/` | MC 模型：basic_mc / hero_value / bidding / robust_value |
| `app/streamlit_app.py` | Streamlit 中文主界面 |
| `notebooks/` | 7 册（含 `07_capture_readings_and_mc_perf`） |
| `scripts/` | 数据生成 / 端到端 demo / 一次性 probe |
| `tests/` | 234 单测 |
| `data/raw/` | 玩家本地游戏文件（gitignored） |
| `data/processed/` | 我们生成的 schema 化 JSON（入 git，便于无游戏的人也能跑） |
| `docs/project_vision.md` | 原始三层架构设计 |
| **`PROGRESS.md`** | **新协作者起点**：项目全貌 + 当前状态 + 路线图 |
| **`OBSERVATIONS.md`** | **技术发现日志**：每个 checkpoint 的关键发现 |
| **`docs/INSTRUCTIONS.zh-CN.md`** | **玩家操作说明**（流程图、四 Tab、抓屏顺序） |
| **`TROUBLESHOOTING.md`** | **39 条** — 踩坑归档 + [#33 影响矩阵](TROUBLESHOOTING.md#33-各字段对-mc--枚举的影响矩阵设计预期) + [#37–40 Capture/UI](TROUBLESHOOTING.md#37-紫品均格-ocr-有数但输入框为空) |

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
- **pytest**（360 单测，覆盖解码 / 推断 / ROI / snipe / capture / hero_value）
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

**已完成**（C-1 ~ C-37）
- ✅ 6 张游戏表解码 + schema · 推断引擎 v2 · Streamlit 中文 UI（MC 默认 **3000**）
- ✅ Per-bucket MC filter（2026-05-16）· 分析估算 + ★ 具体巨物（C-28~29）· 紫品均价输入
- ✅ 放仓红约束后端（C-30）· 秒/放仓 **UI 隐藏**（C-31）· 字段作用范围文案 + 联合约束枚举放宽（C-31b）
- ✅ P0-B：fallback 保留 `huge_cells_override`（C-32）
- ✅ 主屏抓屏 + OCR 预填 + 地图纠偏（C-35~36）· UI 稳定与实机 OCR 性能（C-37）
- ✅ LOO 道具 ROI + 眼估噪声 · 5 册 notebook · **360** 单测 · **39** 条 TROUBLESHOOTING
- ✅ 双语 README + 演示视频 + 截图

**启动体验（C-56）**
- ✅ **操作说明** — [`docs/INSTRUCTIONS.zh-CN.md`](docs/INSTRUCTIONS.zh-CN.md) + Streamlit「操作说明」子页
- ✅ **启动去阻塞** — 首屏不初始化 OCR；首次 OCR 操作按需加载模型
- ✅ **不再需要暖机等待占位** — 手填与 tab 浏览可立即开始

**暂缓 / 可选**
- ⏸ 秒/放仓 UI 与 tier 调参（P0-A）
- ⏸ 均价 / ★ 格数进 MC（P2，见 #31）
- ⏳ Progressive UI · BidMap 23 列 · **[GitHub Release v1.0.0](https://github.com/SeasonCake/bidking-lab/releases)** 一站式 zip

**明确不做**
- per-item observation · 抽检 ROI 建模

---

<sub>Made with too much coffee · 2026-05-17</sub>
