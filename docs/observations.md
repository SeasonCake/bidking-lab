# bidking-lab · 项目观察日志

> 记录关键发现、设计决策、技术要点和阶段性成果。  
> TROUBLESHOOTING.md 记"踩坑"，这里记"收获"。  
> 按时间线从早到晚排列，每个 checkpoint 对应一次 git push。

---

## Checkpoint #1 — 解码器 + 基础设施（2026-05-14）

### 关键发现

1. **`Tables/*.txt` 的编码格式是纯 Base64 → UTF-8 TSV。** 没有 gzip、protobuf、
   自定义加密——初始怀疑的"加密"只是 Base64 后看不懂而已。  
   验证方法：`scripts/probe_tables.py` 逐个尝试 base64 / gzip / zlib / hex，
   只有 base64 成功且解出合法 UTF-8。

2. **全部 11 张表的列数在每行内一致（uniform）。** 这意味着可以放心用固定 schema
   模型（pydantic），不需要处理变长行。

### 使用技术

- **pydantic v2** BaseModel 做所有表的 schema（类型安全 + 自带 JSON 序列化）
- **pathlib** 统一路径处理，避免 Windows `\` 陷阱
- **io.TextIOWrapper** 包裹 stdout 解决 PowerShell UTF-8 显示问题

### 项目结构决策

- `src/bidking_lab/extract/` → 每张表一个模块（`tables.py` 通用解码，`drop_table.py`、
  `item_table.py` 等）
- `data/raw/` gitignore（版权），`data/processed/*.json` 可提交（派生数据）
- 参考项目（Jrinky908/bidking, nql1314/bidking-booooot）放 `external_references/`
  本地克隆（gitignore），不 vendor

---

## Checkpoint #2 — Drop/Item schema + 列名逆向（2026-05-14）

### 关键发现

1. **`Drop.txt` 结构简洁**：608 个池，每行 5 列 `[pool_id, name, desc, pool_type, entries_json]`。
   `pool_type=1` 是容器池（entry 引用其他 pool），`pool_type=2` 是叶子池（entry 引用真物品）。

2. **`Item.txt` 有 38 列**，大部分是 UI key / 模型名。核心有价值的列：
   - col[0] = item_id
   - col[1] = name
   - col[8] = quality（0=无色, 1=白, 2=绿, 3=蓝, 4=紫, 5=金, 6=红）
   - col[9] = value（银币价值，和游戏内完全对应）

3. **玩家手动验证**：金陵折扇/非洲之心=红色(quality=6)，废旧纸箱=白色(quality=1)，
   价值数字和游戏内显示一致。→ schema 可信。

### 使用技术

- **column profiler** 脚本（`scripts/profile_item_columns.py`）：对每列统计 distinct
  值数量 / 类型 / 样本，用于快速逆向未知 schema
- **交叉验证**：用 Drop.txt 的 item_id 列表过滤 Item.txt，得到"实际可掉落"子集
  （883/1132 件物品），确认 Drop 引用的 item 都存在

---

## Checkpoint #3 — BidMap 完整 schema + 第一版 MC（2026-05-15）

### 关键发现

1. **BidMap.txt 的 21 列完全解码**（详见 `docs/bid_map_schema.md`）。  
   最关键的一列：**col[16]** = `[9999, drop_pool_id, items_min, items_max]`
   —— 直接告诉了每张地图用哪个 Drop 池 + 单场物品数范围。

2. **Drop 池是 4 层嵌套的递归树：**
   ```
   map pool → 品质分布 → 分类×品质盲盒 → 叶子池（真物品）
   ```
   用 `DropEntry.category == 9999` 作为"继续递归"的哨兵值。  
   `flatten_pool()` 沿树走一遍，输出 `{item_id → 有效概率}` 的扁平分布。

3. **地图分 5 大类 × 最多 3 档难度**（共 105 张）：
   - 快递(7) / 仓库(5) / 集装箱(10) / 别墅(10) / 沉船(10)
   - 同主题不同档位 **共用同一个 drop pool**，只是经济参数不同

4. **第一版 MC 验证了设计直觉**：  
   沉船 ~71万 > 别墅 ~46万 > 集装箱 ~26万 > 仓库 ~10万 > 快递 ~5万  
   （mean session value，方差也按同顺序递增）

### 使用技术

- **numpy** 向量化 MC：单次 `simulate_map()` 20,000 trials 约 6 秒
- **递归展平**：`flatten_pool()` 深度限制 16 层，路径概率逐层相乘

---

## Checkpoint #4 — Bidding 模型 + 明暗拍区分（2026-05-15）

### 关键发现

1. **明拍(2xxx) / 暗拍(4xxx) / 训练(3xxx) 确认**：
   - col[17] mode_flag: 4=正式拍卖, 1=训练, 2=新手教学
   - col[18] bid_price_ladder: `[2000,1600,1300,1100,0]`（每轮起拍价阶梯）
   - 训练场全是 `[0,0,0,0,0]`，免费入场

2. **明暗拍的 drop pool 完全一样** → 物品分布和期望价值没有区别。  
   **唯一区别是 bidding 经济参数**（预算 / 入场费 / 信息可见性）。

3. **预算约束在绝大多数场景下不生效**：
   - 别墅 open 预算 200万，一场总物品价值 ~47万 → 预算消耗 <15%
   - 即使 bid_factor=0.50（出价一半），消耗也才 23%
   - 只有快递（预算 1万 vs 物品 5.4万）才出现预算紧张

4. **Bid factor 敏感度分析**：
   - 最佳区间 0.35~0.40（ROI 1.2~1.4x）
   - 超过 0.50 ROI 跌破 1x（付出 > 收益）
   - 低于 0.20 赢不到东西（仅 14% 胜率）

### 设计决策

- **简化方向**：既然明暗拍 drop pool 一样、预算几乎不瓶颈，后续模型
  **不再区分明暗拍**，减少复杂度。Budget 模型保留为可选工具，不进核心路径。
- **快递是票制**：1000 银币 = 10 张票，不是传统入场费。后续需要在 schema
  中标记这一点。

### 使用技术

- **BidPolicy 数据类**：参数化的出价策略（bid_factor + NPC 底价区间）
- **SessionSummary**：一次完整对比的聚合结果（gross / net / ROI / win rate / 
  budget utilization）

---

## 项目全景状态（截至 Checkpoint #4）

### 技术栈

| 层 | 组件 | 状态 |
|---|---|---|
| 语言 | Python 3.13 | ✅ |
| 包管理 | pip + pyproject.toml (editable install) | ✅ |
| Schema | pydantic v2 | ✅ |
| 数值计算 | numpy | ✅ |
| 测试 | pytest (46 tests) | ✅ |
| 数据层 | base64 解码 + TSV 解析 → JSON 导出 | ✅ |
| 计算层 | MC (basic + bidding) | ✅ v1 |
| 表现层 | notebooks / Streamlit | ❌ 未开始 |

### 已解码表

| 表 | 列数 | Schema | 状态 |
|---|---|---|---|
| Drop.txt | 5 | `DropPool` + `DropEntry` | ✅ 完成 |
| Item.txt | 38 | `Item`（11 字段已命名，27 列在 raw_row） | ✅ 可用 |
| BidMap.txt | 21 | `BidMap`（16 字段已命名） | ✅ 完成 |
| BattleItem.txt | 6 | `BattleItem` | ✅ 完成 |
| Hero.txt | 21 | `Hero`（基础 3 字段） | ✅ 基础 |
| Cabinet.txt | 14 | 未开始 | ❌ |
| Condition.txt | 13 | 未开始 | ❌ |
| Constant.txt | 4 | 未开始 | ❌ |
| Item_Type.txt | 8 | 未开始 | ❌ |
| ItemRestock.txt | 10 | 未开始 | ❌ |
| LevelUp.txt | 8 | 未开始 | ❌ |

### 进度估计

```
Layer 1 (数据层)：██████████████░░  ~90%  (剩 Cabinet + 其余次要表)
Layer 2 (计算层)：██████░░░░░░░░░░  ~35%  (basic MC + bidding 完成，英雄技能/装箱待做)
Layer 3 (表现层)：░░░░░░░░░░░░░░░░   0%
──────────────────────────────────────
总进度           ：██████░░░░░░░░░░  ~40%
```

### 下一步方向

1. **C-1 英雄技能边际价值**：Hero.txt 深层 schema → 技能效果建模 → 对照 MC
2. **Cabinet.txt schema**：柜子尺寸 + 物品形状 → 装箱可行性（Q3）
3. **第一个 notebook**：地图价值分布可视化（简历展示用）
