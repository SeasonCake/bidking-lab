# bidking-lab · 项目地图

> 这个文档回答一个问题：**最终我们要做出什么东西？**  
> 任何时候自己迷路了，回来看一眼这里。代码、README、PR 描述都应该和这份地图对齐。

## 一句话定位

`bidking-lab` 是一个 **本地数据驱动的概率/价值分析库**，针对 Steam 游戏 *The Bid King*（《竞拍之王》）的玩家。
**不是**外挂、不是自动化、不是游戏内注入。

---

## 三层架构

```
                +------------------------------------------+
   Layer 3 →    |  表现层  notebooks / Streamlit / Gradio  |
                +-------------------↑----------------------+
                                    |
                +-------------------+----------------------+
   Layer 2 →    |  计算层  Monte Carlo / 卷积 / 条件概率    |
                +-------------------↑----------------------+
                                    |
                +-------------------+----------------------+
   Layer 1 →    |  数据层  Tables/*.txt → 结构化 JSON / DF |
                +------------------------------------------+
```

任何一层的代码都**只依赖下层**，不反向跨层。

### Layer 1 · 数据层 — 让游戏数据"可读"

| 输入 | 输出 |
|------|------|
| `BidKing_Data/StreamingAssets/Tables/*.txt` （Base64 + TSV） | `bidking_lab.extract` 的解码函数 + 每张表的 pydantic schema |

**已完成**
- 解码器：`extract.tables.decode_table_text` / `load_table_rows`
- 全表 shape 报告：`scripts/decode_all_tables.py`

**待做**
- 每张关键表的列名映射（先 `Drop.txt`，再 `Item.txt`，再 `BidMap.txt`，再 `Cabinet.txt` / `Hero.txt`）
- 一键导出 `data/processed/{items,drops,maps,cabinets,heroes}.json`

**完成标准**
- `pytest` 全绿
- `python -m bidking_lab.export` 一条命令产出 5 个 JSON
- README 里有一份"表字段说明"

### Layer 2 · 计算层 — 回答玩家真正关心的问题

我们要回答的问题集合（**核心 KPI**）：

| ID | 问题 | 用到的方法 |
|----|------|----------|
| Q1 | 选地图 X、英雄 Y，这一局总价值的期望 / 分位数？ | 蒙特卡洛 N 次抽样 |
| Q2 | 已经开了 [A, B, C] 这几件物品，剩下出 X 的概率？ | 条件概率 + 重采样 |
| Q3 | 给定柜子尺寸 [21, 11] 和一组掉落物，**装得下的概率**？ | 物品形状卷积 + 启发式装箱 |
| Q4 | 英雄 Y 的技能在地图 X 上的"期望加成"是多少？ | 对照组 MC（有技能 - 无技能） |
| Q5 | 哪个英雄/地图组合期望收益最高？ | 全网格扫描 + 排序 |

**实现原则**
- 概率分布直接读 `Drop.txt` 里的权重——**不拟合**、不引入 sklearn。
- 单次 MC 用 numpy 向量化，目标 50 万次/秒 量级。
- 网格可行性用 2D 卷积验证（参考 `docs/upstream_references.md` 中的设计评论）。

### Layer 3 · 表现层 — 让别人能看懂

先做 notebook（最低成本，简历可直接附链接）：
- `notebooks/01_data_overview.ipynb`：物品/地图/英雄的描述性统计
- `notebooks/02_map_value_distribution.ipynb`：地图 × 期望价值的小提琴图
- `notebooks/03_hero_skill_value.ipynb`：英雄技能的边际价值排行

再做交互（可选，做完上面再考虑）：
- Streamlit：下拉框选地图/英雄，按钮跑 MC，柱状图实时刷新。

---

## **不做** 的事（明确划掉）

| 不做 | 为什么 |
|------|--------|
| OCR 识别游戏画面 | 那是 `Jrinky908/bidking` 在做的；本项目的优势是直接读源数据 |
| 自动点击/抢拍 | 那是 `nql1314/bidking-booooot` 在做的；和"分析"是不同的项目 |
| 训练 ML 模型去"预测"已知的掉率 | 掉率在 `Drop.txt` 里是白盒，拟合等于杀鸡用牛刀（详见下） |
| 重新分发游戏资源文件 | 版权问题；`data/raw/**` 永远在 `.gitignore` |

---

## sklearn 在本项目里的角色

**默认：不用。** 概率是已知的，直接抽样即可。

未来若 Layer 2 的 MC 因为搜索空间太大而慢，**可以**考虑：
- 用 sklearn 训一个 surrogate model：`(map, hero, partial_state) → E[value]`，给 UI 实时响应用。
- 物品聚类（KMeans）作为可视化辅助。

这些是**优化手段**，不是核心；等核心做完再评估是否真的需要。

---

## 当前进度（同步更新）

- [x] 仓库脚手架 + `pip install -e .[dev]` 可跑
- [x] 复制游戏 `Tables/*.txt` 到 `data/raw/tables/`（脚本化）
- [x] 解码器（Base64 → UTF-8 TSV）+ 单元测试
- [x] 全表 shape 报告（10 张表都 uniform）
- [x] `Drop.txt` schema + `parse_drop_table()`（608 池全通过）
- [x] `Item.txt` 列名 profiler + 初版 schema 文档（`docs/item_table_schema.md`）
- [x] **Item.txt 交叉验证**：col[8]=quality（0=无 / 1–6=白绿蓝紫金红）、col[9]=value 已确认；category 1–110/9999 含义已确认
- [x] `parse_item_table()` v1 + `parse_battle_item_table()` + `parse_hero_table()` + `parse_bid_map_table()`（summary only）
- [x] **派生 JSON 进 Git**：`items.json` / `items_droppable.json` / `battle_items.json` / `heroes.json` / `maps.json`（无需游戏即可用）
- [x] **`BidMap.txt` 完整 schema**（21 列，含 sub-pool 路由 / 入场费 / 起始预算 / 物品数范围 / drop pool 引用）
- [x] **Drop pool 多层嵌套机制破解**：`cat=9999` 表示池子引用，叶子条目用真实 category（参见 `simulation.basic_mc.flatten_pool`）
- [x] **第一版 MC**：`simulate_map(map_id, n=100_000)` → mean / std / q05 / q50 / q95；已通过 `scripts/demo_simulate_maps.py` 在 13 张图上跑过，结果符合"高难度 = 高期望+高方差"的设计直觉
- [ ] **下一步（C）**：英雄技能的边际价值（Q4）—— 给每个英雄一个 "skill effect" 模型，对比 MC
- [ ] `Cabinet.txt` schema（Q3 需要：物品形状 + 柜子尺寸 → 装箱可行性）
- [ ] 第一个 notebook：地图价值分布小提琴图
- [ ] Sampling-without-replacement 修正（目前 with-replacement 高估了方差）

> 这个清单**就是路线图**，每完成一项就来这里勾一下。
