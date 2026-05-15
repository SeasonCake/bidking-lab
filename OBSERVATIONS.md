# bidking-lab · 技术发现日志

> 记录每个 checkpoint 的**技术发现、设计决策、使用技术**。  
> 项目全局进度和路线图请看 **`PROGRESS.md`**；踩坑记录看 `TROUBLESHOOTING.md`。  
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

## Checkpoint #5 — Timing-aware 英雄模型 v2（2026-05-15）

### 关键发现

1. **v1 模型的 bug 确认**：把 R1 信息和 R5 信息等价对待，导致拉文(301)
   被严重高估（R5 才揭示所有物品品质，但好东西早被抢了）。

2. **修复方案**：在 `SkillEffect` 里增加 `available_at_round` 字段，
   配合 `TIMING_WEIGHTS` 时间衰减：
   ```
   R1=1.0, R2=0.75, R3=0.50, R4=0.30, R5=0.05
   ```
   每个效果的信息分数 = raw_info × timing_weight。

3. **估算公式改为非线性三段**：
   - 得分 ≥ 0.5 → 80% 真实价值 + 20% 均值（"强知识"）
   - 得分 ≥ 0.2 → 40% 真实价值 + 60% 均值（"部分知识"）
   - 得分 < 0.2 → 纯均值（"未知"）
   
   原因：线性插值让全覆盖低分英雄（如艾哈迈德的 COUNT_HINT）累积出
   不合理的排名优势。非线性模型正确反映"场次级统计量不能帮助选品"。

4. **修正后英雄排名（别墅代表图 2407）**：
   ```
   #1 玛丽亚(108)   R1 VALUE 低品质 → +23.6%
   #2 艾莎(103)     R1-3 渐进 OUTLINE  → +22.4%
   #3 索菲(107)     R1+R2 渐进 QUALITY → +21.6%
   #4 加布里埃拉(104) R1 渐进 QUALITY   → +20.2%
   …
   #18 艾哈迈德(204) COUNT_HINT 无选品能力 → -0.4%
   #19 拉文(301)    R5 全品质 太晚      → -0.6%
   #20 维克托(209)  COUNT_HINT 金紫计数  → -0.8%
   ```

5. **关键洞察**：
   - 玛丽亚的 VALUE 信息实际上只覆盖白/绿/蓝（低品质），但因为这些
     占物品总量 70%+，高覆盖率弥补了"只看低端"的局限。
   - 艾莎的 OUTLINE 虽然信息质量低（0.3），但 R1-R3 渐进覆盖所有品质
     等级，在高物品数地图上表现强劲。
   - 艾哈迈德的价值在"场次筛选"而非"选品"——模型暂不包含此维度。

### 设计决策

- 保留 `use_timing` 参数允许 v1/v2 对比
- 不对估算公式做更复杂的建模（已经足够准确反映游戏直觉）
- 艾哈迈德的"场次筛选价值"作为未来独立指标，不混入选品模型

### 使用技术

- `TIMING_WEIGHTS` dict 可被 `bid_price_ladder` 覆盖（未来支持不同地图的自定义衰减）
- `np.where` 向量化三段估算，避免 Python for 循环

---

## Checkpoint #6 — Notebooks + Cabinet/Item shape probe（2026-05-15）

### 关键发现

1. **Item.txt col[7] 是物品形状编码**：两位数 WH 格式，十位=宽(W)，个位=高(H)。
   - 11=1×1 (248件), 22=2×2 (184件), 33=3×3 (31件)
   - 最大 63=6×3（单人郊游快艇，金色，106,500银币）
   - 0=非实体物品（440件：成就、头像、皮肤等）
   - 692 件实体物品有真实形状

2. **Cabinet.txt 完全解码**（12 柜子 × 14 列）：
   - 所有柜子共享 6×7 网格（42 格）
   - col[4] = 接受的物品分类（通用柜 vs 专类柜）
   - col[9] = 升级费用（0 或 500）
   - 1 通用柜(6001) + 10 专类柜(6101-6110) + 1 高级柜(6002)

3. **装箱可行性评估：✅ 完全可行，不需要 Unity 逆向。**
   - 所有必要数据已在 TSV 表中
   - 网格是简单的矩形（6 列 × 7 行），物品也是矩形（W × H）
   - 这是经典 2D strip packing 的简化版本

4. **Notebook 可视化完成**：
   - `01_map_value_distribution.ipynb`：5 大主题 session value 小提琴图 + 分档对比
   - `02_hero_ranking.ipynb`：20 英雄 × 5 地图热力图 + v1/v2 对比 + Top-5 柱状图

### 设计决策

- 物品形状是**矩形**（W×H），不是任意多边形 — 简化装箱算法
- 装箱模型可以用贪心/启发式而非精确求解，因为在线决策场景下
  玩家也不可能计算最优解

### 使用技术

- matplotlib + seaborn + pandas 构建 notebook 可视化
- `scripts/probe_item_shapes.py`：Item.txt 形状列分析
- 形状分布：1×1(36%) > 2×2(27%) > 1×2(8%) > 2×1(7%)

---

## Checkpoint #7 — 地图轮次提示 + 长尾鲁棒估价（2026-05-15）

### 关键发现

1. **`BidMap.col[19]` 是"每轮分类提示"**，不是"每轮实际分类"。  
   长度 5 对应 5 轮拍卖，每个元素是 Item 分类码或 `0`（无提示）。  
   验证脚本：`scripts/probe_round_categories.py`。
   
   **提示密度与难度递增完美对应**：

   | 主题 | 提示数 | 模式 |
   |---|---|---|
   | 21xx 快递 / 22xx 仓库 | 5（全提示）| 入门，UI 完全揭示 |
   | 23xx 集装箱 | 3（R1/R3/R5）| 中等 |
   | 24xx 别墅 | 2（R1+R3）| 难 |
   | 25xx 沉船 | 1（仅 R1）| 极难，道具/英雄价值最高 |

   **R1 100% 给提示**（55/55 leaf 地图），R3 ~67%。  
   值域只有 `{0, 102医疗, 103时尚, 104武器, 105珠宝}` —— 游戏对家具/文物/数码/能源/食饮/书画 6 类**从不**预告。  
   明拍(2xxx) / 暗拍(4xxx) 提示**完全一致**（如 2407 和 4407 都是 `[103,0,103,0,0]`）→ 再次印证"明暗拍信息源相同"。

2. **"小而贵"长尾污染了基础估价**。  
   14 件 value > 100 万的红物在别墅/沉船贡献 11–12% 的 raw E[session]，  
   但**其中 9 件形状是 1×1 / 1×2 / 2×1 / 1×3**（金陵折扇、非洲之心、黑王子、羊脂玉、超级跑车钥匙、百年人参 …）—— 它们的池里有数百件便宜物，玩家看到形状**完全分辨不出**。

3. **大物品有形状指纹**（脚本：`scripts/probe_distinctive_shapes.py`）。
   - **5×4 → 唯一物品**：墙面涂鸦墙（蓝，8880 银）—— 形状即"知道是这件"
   - **6×3 → 唯一物品**：单人郊游快艇（金，10.7 万）
   - **4×4** 5 件：3 红屏风/车壳 + 1 金锂电池 + 1 蓝**石狮子**（唯一混淆）
   - **3×4 / 3×5 / 5×3**：全是金红，无混淆
   
   形状字典是 Phase 1A `OutlineObservation` 的天然先验。

4. **robust_session_value 量化结果**：
   - 别墅高仓（2407/4407）：46.2万 → 44.0万（**-4.8%**）
   - 沉船大仓（2507/4507）：67.6万 → 64.0万（**-5.2%**）
   - 快递/集装箱：0% 影响（这些图本就没小贵红物）

### 设计决策

- **`round_category_hints` 入 schema**（`BidMap.round_category_hints: list[int]`）。Phase 1A 把它视为"零成本 Observation"——每张地图天生带 1–5 个 RoundCategory 约束，免费降低先验不确定性。
- **`robust_session_value` 默认策略**：value ≥ 100万 且 area ≤ 3 归零。这是个一刀切启发式，不引入"可见形状参数"——shape 条件的反推留给 Phase 1A 推断引擎做，这里保持简单。
- **`Winsorize` 工具函数**保留为可选，用于 notebook 里画分布图时"压尾"避免视觉污染。

### 仓库大小先验（用户提供）

| 仓库 | 总格数 | 道具策略 |
|---|---|---|
| 小仓 | < 70 | 极度保守 |
| 中仓 | < 110 | 白绿道具为主 |
| 大仓 | > 130 | 才考虑金道具 |

这是 Phase 1A `ScanCellsObservation` 的强先验：玩家**事先就能看到**总格数（用 `总仓储空间` 道具），所以可以根据仓库大小动态调整道具组合。

**仓库大小特例**：看到 5×4 形状时**总格数要减 20** —— 因为 5×4 唯一物品就是低价值蓝物，剔除它的格数后再用剩余总格数估"高价值部分"。Phase 1A 会把这种"形状识别 → 减去已知物品贡献"的逻辑作为推断步骤自动处理。

### 使用技术

- **pydantic ValidationError 防御**：`json.loads("0")` 返回 int 而非 list → parser 用 `isinstance(parsed, list) else []` 兜底，避免后续 `int()` 迭代失败
- **GBK 控制台兼容**：所有新 probe 脚本在 stdout 非 utf-8 时主动 `io.TextIOWrapper` 重包，避免中文物品名打印崩溃

---

> **项目全局进度与路线图已迁移至 [`PROGRESS.md`](PROGRESS.md)**。  
> 本文件专注于每个 checkpoint 的技术细节。
