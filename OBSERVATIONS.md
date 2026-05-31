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

## Checkpoint #8 — Phase 1A 推断引擎 MVP（2026-05-15）

### 关键发现

1. **显示规则锁死：truncate at 2dp**。  
   用户截图比对确认：游戏里 `X品均格` 类道具的数值显示是**地板截断**到 2 位小数（不是四舍五入），并且如果**精确除尽**末尾零会被去掉。  
   例：32/11 = 2.9090… → 显示 `"2.90"`；29/10 = 2.9 → 显示 `"2.9"`。**这给了反推分母奇偶性的关键信息**——尾零=约的=分母不整除 10。

2. **小数 leakage 的关键检验是字符串等价比对**。  
   `is_compatible(reading, total_cells, count)` 不是数值匹配，而是**模拟游戏显示**后字符串相等：
   ```
   format_value(m, n) == reading.raw   # e.g. "2.90"
   ```
   这一行替代了所有"先转 float 再比较"的浮点陷阱。

3. **per-cell 价值 prior（drop-weighted p50）**与用户启发式吻合：
   - 紫 ≈ 2560（用户经验 2500）
   - 金 ≈ 9800（用户经验 9400）
   - 红 ≈ 50000 默认 / 30000 巨物（4×4 红屏风/车壳：84万-36万/16格 ≈ 2.5-5.3万）

   **红色"巨物分流"**：≥16 格的红物 per-cell 价值显著低于 ≤6 格红物（前者 ~3万/格，后者 ~8.6万/格），引擎里要拆 prior。

4. **沉船 R4 截图反推一次性通过验证**：玩家用 优品均格 = `"2.5"` + 优品估价 = 86,490 → 推断引擎 top-1 = `(35 cells, 14 件)`，cells_score=0、value_score=0 全部完美匹配。这一案例固化为单测和 demo 脚本。

5. **伊森 outline 无 hover category 提示**（用户在 2026-05-15 实测确认）。  
   伊森 R1 看到 5 个 category 的轮廓，但 UI **不告诉你这些 outline 来自哪个 category**。玩家只能用**地图 drop pool 先验**（flatten_pool 已有）猜测各分类的概率分布。这与我们 `OutlineObs(quality_hint=None)` 的建模一致——伊森 outline 是"只知形状"的弱信号。

6. **艾莎技能数据不一致**：游戏 `Hero.txt` col[2] 描述是 "R1=蓝, R2=绿, R3=白"（3 轮），但用户实战观察是 "R1=白, R2=绿, R3=蓝, R4=紫"（4 轮）。最可能解释：艾莎升满级（col[10] 显示她有 4 个技能效果 id `[1001031, 1001032, 1001033, 1001034]`）后扩展为 4 轮。`Hero.txt` 文本只描述了基础等级。  
   决策：`inference/outline.py` 采用**用户实战版本**；`hero_skills.py`（v2 排名所依赖）暂不动，留 TODO 等玩家进游戏拍技能升级面板截图后统一修订。

### 巨物输入设计

| 字段 | 类型 | 说明 |
|---|---|---|
| `huge_band` | `"none" \| "1" \| "2-3" \| "4+"` | UI 下拉，避免玩家算清楚件数 |
| `huge_cells_per_item` | int | 紫=16, 金=18（仅游艇）, 红=16 |
| `huge_cells_override` | int | 玩家精确数到的总格数（可选） |

**可见性规则**：艾莎只能看紫色巨物，金红巨物由她**猜**；伊森看全部品质巨物。`aisha_can_observe_huge(quality)` 编码这条规则，session validator 在艾莎模式下检测金/红巨物输入会发警告。

### 标准道具组合（用户提供）

- **伊森**（5 件，4 便宜+1 金）：普品扫描 + 良品扫描 + 优品均格 + 优品估价 + 珍品估价/扫描
- **艾莎**（4 件，2 便宜+2 金）：珍品估价 + 抽检二 + 宝光四鉴 + 总仓储空间（轮廓已经给她格数直觉，所以更偏估价类）

### 开放问题：估价 vs 扫描 ROI（Phase 2 首题）

用户洞察：估价**便宜**但只给 Σvalue（要穷举推 count/cells），扫描**贵**但给精确 total_cells。  
量化：`ROI(tool) = ΔVar(session_value估计) / cost(tool)`。直觉是估价 ROI 更高（一般场景），但红品方差大、紫品有巨物时扫描可能反超。Phase 2 第一个产出就是这张 ROI 对照表。

### 使用技术

- **整数除法控制截断**：`(m * scale) // n`（不是 `int(m/n * scale)`，浮点会引入 ±1ULP 误差）
- **暴力枚举 + 复合排序**：`composite = 0.7 * value_score + 0.3 * cells_score + 0.001 * count`（Occam 项防止"等价好"的高 count 解胜出）
- **Greedy bucket-by-bucket**：按 q=6→1 顺序解每个品质，每解完一个就把它的 top-1 cells 从仓库容量里扣掉，给下一个品质让位。不是 joint posterior，但实战足够（待 Phase 1B 升级）

---

## Checkpoint #9 — 截图校准：艾莎=OUTLINE+QUALITY，伊森=5 分类（2026-05-15）

### 关键发现（5 张截图溯源）

1. **艾莎技能名 "遗珍慧眼"，每轮揭示 OUTLINE+QUALITY 双信息**。  
   截图 1（沉船 R4 round panel）显示 4 个 `艾莎-遗珍慧眼` 条目同时存在，文本一致地写："**显示所有 X 色品质道具的轮廓和品质**"。这跟我们之前把艾莎建模为纯 OUTLINE（0.3 分）严重偏差——她实际上同时给形状和品质，应该归到 0.85 这档（OUTLINE+QUALITY 复合）。

2. **艾莎是 4 级技能、白→绿→蓝→紫**。  
   截图 4（别墅 R3）只 fire 3 个艾莎条目（白+绿+蓝）；截图 1（R4）fire 4 个（多了紫）；截图 3（网吧 R2）只 fire 2 个（白+绿）。**完美佐证 R1=白, R2=绿, R3=蓝, R4=紫 的进度链**。`Hero.txt` col[2] 描述的"R1=蓝, R2=绿, R3=白"应是基础等级（level 1），实际游戏内升满级到 4 后扩展为 4 级递进——和 col[10] = `[1001031, 1001032, 1001033, 1001034]` 的 4 个升级 effect_id 完全对应。

3. **伊森技能名 "空间觉知"，R1=5 种分类，R2=条件触发**。  
   截图 5（沉船 R2 round panel）显示两条伊森条目：
   - `伊森-空间觉知: 随机显示 5 种类型藏品各自的轮廓` (R1 fired)
   - `伊森-空间觉知: 显示所有已知品质的藏品各自的轮廓` (R2 fired, 条件触发)

   "**5 种类型**"是 category 不是 item。在 10 个分类里随机选 5 个，把那 5 个分类的全部物品轮廓暴露——平均覆盖 ~50% 的物品（地图分类分布越集中覆盖越高）。这比"5 件随机物"强得多。R2-R4 的 "已知品质" 条件触发我们暂不建模，留为 v2 的保守低估。R5 仍然是揭示全部。

4. **伊森 outline UI 不显示分类提示**（用户实测确认）。  
   就算 R1 暴露了 5 个分类，玩家也**无法 hover 看到分类名**。只能用地图爆率先验（flatten_pool 的分类分布）猜每个轮廓所属 category。这意味着 `OutlineObs(quality_hint=None)` 是正确建模。

5. **地图自带信息 DSL 比 `round_category_hints` 丰富得多**。  
   5 张截图里抓到至少 4 种新的地图信息类型：

   | 截图来源 | 地图 | 轮次 | 提示内容 |
   |---|---|---|---|
   | 截图 2 | 集装箱 末日庇护所 | R1 | "本场拍卖共有金色品质道具 **3** 件" → `gold count = 3` |
   | 截图 3 | 网吧 极客改造屋 | R1 | "金色品质总占用的格子数量为 **14** 格" → `gold total_cells = 14` |
   | 截图 4 | 别墅 未知别墅 | R1 | "本场拍卖共有金色品质道具 **4** 件" → `gold count = 4` |
   | 截图 4 | 别墅 未知别墅 | R3 | "紫色品质道具平均占用的格子数量约为 **2.54** 格" → `purple avg_cells = 2.54` |
   | 截图 5 | 沉船 未知残骸 | R2 | "随机显示 **6** 件藏品" → `random_reveal = 6` |

   **结构化形式**：
   ```
   MapInfo[round][quality] = QuantityRecord
     QuantityRecord.kind ∈ {COUNT, TOTAL_CELLS, AVG_CELLS, CATEGORY, RANDOM_REVEAL}
   ```

   `round_category_hints` 是其中 CATEGORY 一种。其它的还住在 BidMap.txt 未解析列里（待 probe）。

6. **用户口述："第一轮信息确实是地图会给，但是第三轮一般只有别墅有"**。  
   即 R1 给信息密度最高（每张图都给），R3 仅别墅给，其它图 R2/R3 缺。与 col[19] round_category_hints 的密度模式一致（快递 5/仓库 5 / 集装箱 3 / 别墅 2 / 沉船 1）。

### 模型修正（已落地）

`src/bidking_lab/simulation/hero_skills.py`：

- 新增 `InfoType.OUTLINE_QUALITY = 0.85`（介于 QUALITY 0.7 和 FULL 1.0 之间）
- 新增 `SkillEffect.random_categories: int = 0`（取代 max_items=5 的硬编码，per-trial 真正随机选 N 个分类）
- 艾莎 (103) 改为 4 个 OUTLINE_QUALITY effects，R1→R4 依次 quality=1/2/3/4
- 伊森 (208) R1 改为 `random_categories=5`（替代 max_items=5），保留 R5 全揭示
- `compute_info_score(rng=...)` 新增可选 RNG 参数；hero_value MC 每 trial 用 numpy rng 派生 python `random.Random` 传入 → 每场局真随机抽 5 个分类

### v2 ranking 新结果（5000 trials）

**别墅 2407 私人金库** (rounds=25, items=20-40)：

| Rank | Hero | 改前 % | 改后 % | 变化 |
|---|---|---|---|---|
| 1 | 加布里埃拉 104 | +20.2% | **+24.3%** | ↑ |
| 2 | 玛丽亚 108 | +23.6% | +22.7% | ≈ |
| 3 | **伊森 208** | **+13.7%** | **+20.5%** | **↑ A→S** |
| 4 | 索菲 107 | +21.6% | +21.3% | ≈ |
| 5 | 艾莎 103 | +22.4% | +20.3% | ↓ slightly |

**沉船 2510 现代货轮娱乐库** (rounds=30, items=22-44)：

| Rank | Hero | % |
|---|---|---|
| 1 | 索菲 107 | +16.9% |
| 2 | **伊森 208** | **+15.3%** |
| 3 | 玛丽亚 108 | +15.3% |
| 4 | 艾莎 103 | +15.5% |
| 5 | 加布里埃拉 104 | +15.0% |

**解读**：
- **伊森从 A 飙到 S**：5 categories ≈ 50% items 覆盖 >> 旧模型的 5 items（约 12-25% 覆盖）。富图 + 多分类（沉船）尤其受益。
- **艾莎略下移**：表面违反直觉，但解释合理——OUTLINE_QUALITY 0.85 比 OUTLINE 0.3 强，但
  - R1 从蓝(高价值)改为白(最低价值)→ R1 timing=1.0 但白品对决策贡献小
  - R4 紫(高价值)虽强但 timing=0.3 衰减重
  - 综合下来略低于旧建模的"R1 蓝品出现就揭示形状"
  - 这其实**更贴近实战**：玩家普遍反映艾莎 R1 看到一堆白色形状没什么决策价值

### 使用技术

- **Python `random.Random` + numpy `Generator` 桥接**：hero_value 用 numpy（向量化抽样），hero_skills 想保持 numpy 无依赖。MC 循环里 `py_rng = random.Random(int(np_rng.integers(0, 2**31)))` 每 trial 生一个 Python rng 传给 `compute_info_score(rng=py_rng)`——既保证 reproducibility（numpy 种子链下来），又不污染 hero_skills 的导入树
- **deterministic-fallback**：`compute_info_score` 在没拿到 rng 时退回 `present[: N]`，便于单测固定输出
- **`InfoType.OUTLINE_QUALITY = 0.85`** 的取值：在我们的 non-linear 三段 blend (`>=0.5 → 80% true`, `>=0.2 → 40%`) 里恰好落到强档（0.85 > 0.5），让"形状+品质"被识别为"接近真值"——比单 quality 略强、比 value 略弱，符合实战体感

### 待做（已记 TODO）

- **probe BidMap.txt 找新 map info 列**：4 种新提示一定存在结构化字段，需要逐列试解析。预期会在 col[20] 或 col[13] 附近
- **伊森 R2-R4 条件触发建模**：当其他来源（如宝光四鉴）揭示了某物品品质时，伊森才会在下轮揭示该物品轮廓。Phase 2 道具组合优化时合并考虑
- **OutlineObs docstring 更新**：现在已经支持 quality_hint，注释里说明艾莎的 outline 自带品质信息（实际上代码层面没变化，只是文档对齐）

---

## Checkpoint #10 — 游戏补丁检测 + map-info 动态生成假说（2026-05-15）

### 关键发现

1. **游戏 2026-05-15 patch 改了表结构**。`scripts/probe_table_column_drift.py` 实测：

   | 表 | 旧 | 新 | 变化 |
   |---|---|---|---|
   | BidMap.txt | 105 行 × 21 列 | **125 行 × 23 列** | +20 张地图 + 2 列 + 列序重排 |
   | Item.txt | 1132 × 38 | **1134 × 38** | +2 件物品 |
   | Drop.txt | 608 × 5 | **629 × 5** | +21 个池 |
   | Hero / BattleItem / Cabinet | — | — | 不变 |

   **列序漂移**：旧 col[10] 在新表里去到 col[11]，整体右移 1；新 col[8] 是新加的 flag；新 col[16] 是空占位（旧 col[16] drop_ref 跑到新 col[17]）；新 col[22] 是新加的尾部 flag。

2. **截图里的"动态信息"不是 BidMap 静态字段**。  
   我以为 `gold count = 3`、`purple avg cells = 2.54`、`gold total cells = 14`、`random reveal = 6` 是地图 schema 里某列直接编码，但 probe 之后发现：**这 4 个具体数值在 BidMap.txt 任意列里都查不到**。最合理解释——**它们是 session-level 动态生成**，游戏开局抽完那场物品后立刻算出对应统计量（紫品当前总价 / 总格数 / 平均格数等）作为提示推给玩家。

3. **`round_category_hints` (新 col[20]) 大概率是"提示槽位调度器"，不是类别名**。  
   旧 probe 把它命名为 round_category_hints 是因为值域恰好是 `{0, 102, 103, 104, 105}` 像极了 category id。但截图证据下：
   - 未知别墅 (2401) col[20] = `[103, 0, 103, 0, 0]`，实际玩家 R1 看到 "金品 count = 4"，R3 看到 "紫品均格 2.54"——**都是品质提示**，不是分类提示  
   - 末日庇护所 (2409) col[20] = `[103, 0, 103, 0, 0]`，R1 看到 "金品 count = 3"——也是品质提示

   即"103" 这个数字本身可能含义是**"用一个数量类提示"**，具体提示哪个品质/哪种统计量由地图主题决定（事件别墅永远紫品均格 R3、集装箱永远金品 count R1 等）。值 102/104/105 各对应不同提示模式。Phase 2 道具组合优化前需要 probe 一下不同主题的 col[20] 值是否对应不同提示风格。

4. **截图里 4 张地图都是 2026-05-15 patch 新加的事件图**：

   | 截图 | 地图 ID | 类型 |
   |---|---|---|
   | gold count 3 | 2409 末日庇护所 | 别墅事件 (col[7]=104) |
   | gold total cells 14 | 2410 极客改造屋 | 别墅事件 (col[7]=104) |
   | purple avg 2.54 + gold count 4 | 2401 未知别墅 | 别墅事件 anthology 主图 |
   | random reveal 6 | 2501 未知残骸 | 沉船事件 anthology 主图 |

   注意 2401 和 2501 都是 **anthology 主图**（col[9] 有 sub_pool_weights 列表，把 2402-2410 各以权重 20 包进 2401，2502-2520 各以权重 20 包进 2501）。这是事件玩法的"随机主题"模式——选 2401 进去玩，系统随机把你扔进 2401-2410 中的某张。

### 设计决策

- **不立刻重写 BidMap parser**。当前提交的 `data/processed/maps.json` 仍是 patch 前的 21-col 抽取，simulation / bidding / hero ranking / inference 模块全部依赖它，**项目仍能正常跑（132 tests 全绿）**。重抽取需要等 BidMap 23-col parser 写好——这事比想象的工作量大，因为 7 个列含义都得重新校准，留作下次开工的第一件事
- **parser 显式拒绝 23-col 输入**：`parse_bid_map_row` 收到不是 21 列就报错并提示是 patch 后的新 schema，避免误判
- **截图里的"动态信息"先走 ManualObservation 路径**：玩家自己把"金品 count = 4"输进 UI 即可（QualityBucketObs 已经支持 count / total_cells / avg_cells / value_sum 四种字段）。不需要等 BidMap parser 写好

### 使用技术

- **`scripts/probe_table_column_drift.py`**：一键检测 6 张主表的实际列数 vs 预期，输出 drift 提示
- **`scripts/probe_bidmap_new_layout.py`**：对照新旧 schema 逐列 dump，找哪些列移位了
- **`scripts/probe_map_info_columns.py`**：按截图里的 4 张地图名字快速定位 BidMap 记录

### 下一开工节奏

1. 重写 BidMap parser 兼容 23 列（半天工程量）
2. 重抽取 maps.json + 全 11 张表 → 更新 processed JSONs
3. 重跑 hero v2 ranking（看新加 20 张事件图的英雄表现）
4. probe col[20] 在不同主题下的提示风格 → 接入 inference engine 作为 "round map hint" prior

---

## Checkpoint #11 — 出价 hint 鲁棒化 + 已识别具体巨物（2026-05-16）

### 关键发现

**实战回归测试暴露了一连串"上游字段没被消费"的 bug 链**——5 个独立但互相加强的问题，全部集中在「玩家填了字段但分析估算/MC 把它当装饰」上。修完这一轮整个出价 hint 模块的实战准确度有质变。

#### 1. 红品自动推断的双重路径漂移

`compute_analytical_estimate` 和 `_build_session` 都做"红品 = 仓库 - 其它"自动推断，但前者**没有**"非红 bucket 全填才推断"的 gate。结果：玩家没填金品 → 系统把残差全推给红品（×50,000/格）→ 估值飙升 5-10×。

修法：两条路径用同一个 `all_non_red_filled` 检查；未填全时把残差按"全金到全红"区间显示，明确告知玩家"金品未填，区间宽，填了能收紧"。

#### 2. `value=0` 默认值的语义模糊

7 个可选数值字段（gold_cells / gold_count / purple_cells / purple_count / red_cells_total / red_value_lo/hi / wg_cells / blue_cells / purple_value / gold_value）默认值 `0` 让"未提供"和"确认为零"无法区分。Streamlit 的 `value=None` + `placeholder="可选"` 是标准做法，配合 `if x is not None` 后端判断。本来一直没改是因为"看起来能用"，实战才暴露——金品=0 这种合法场景在游戏里真实存在（玩家通过技能确认），UI 必须支持"显式断言无金品"。

#### 3. 分析估算没用枚举

`compute_analytical_estimate` 早就有 `min_huge_cells()` 这种简化推断，但 `candidates_for_bucket`（暴力枚举器，综合 value_sum / count / avg_cells / huge_band / 仓库容量）从未被它调用。结果紫品 `value_sum=86,490 + huge_band=1` 被估成 12 格（仅 huge floor），而枚举能算出 35 格。

修法：在 `compute_analytical_estimate` 里加二次 pass，对 `total_cells is None` 但有任意其它字段的 bucket 调 `candidates_for_bucket` 取 top-1。明细文本标注「（用户估价）」「（由枚举推算→N件）」，让数据来源可追溯。

#### 4. `_build_session` 红品残差的同样问题

`_build_session` 算红品残差时只看 `total_cells` 和 `huge_band`，**漏掉了"只填件数"或"只填估价"的 bucket**。金品填 count=5 → 它对 known_sum 贡献 0 → 红品被错计为 32 格 → 后续 `compute_analytical_estimate` 二次枚举时容量被红品挤光，金品在最终明细里彻底消失。

修法：`_build_session` 也调 `candidates_for_bucket` 估格数，再算红品残差。和 #3 形成对称，从源头修。

#### 5. `HUGE_CELLS_PER_QUALITY` 阈值跟 UI 文案漂移

UI 写"≥ 12 格算巨物"，常量 `HUGE_CELLS_PER_QUALITY = {4:16, 5:18, 6:16}`。结果 12 格的紫色防护盾、12-15 格的金品（防弹衣/波斯毯）按代码不算巨物。修成 `{4:12, 5:12, 6:12}` 跟 `BIG_ITEMS_BY_SHAPE` 里最小巨物形状对齐，金品 huge per-cell value 同步从 6,000 上调到 7,000/格。

### 新功能：已识别具体巨物（精确锁定）

`QualityBucketObs.huge_cells_override` 字段早就在数据模型里，但 UI 上「巨物数量」选项只有 `无 / 1个 / 2-3个 / 4+个`——能填模糊数量段，不能告诉引擎"这个 1 个具体是 18 格的游艇"。

新做法：UI 端的 huge_band 选择器从 `BIG_ITEMS_BY_SHAPE` 自动派生具体物品选项：

```
紫品下拉框：[无 / 1个 / 2-3个 / 4+个 / ★ 防护盾 (12格·20,082) / ★ 雷达 (...)]
金品下拉框：[... / ★ 单人郊游快艇 (18格·106,500) / ★ 重型防弹衣 (12格·74,745) / ...]
红品下拉框：[... / ★ 翡翠屏风 (16格·844,000) / ★ 蓝鳍金枪鱼 (15格·1,552,500) / ...]
```

内部 helper：

```python
def _resolve_huge_selection(raw, quality):
    if raw.startswith("item:"):
        item = lookup(raw[5:], quality)
        return ("1", item.cells)  # → huge_band, huge_cells_override
    return (raw, 0)  # 通用档原样返回
```

设计要点：

- **零额外推断接线**——`huge_cells_override` 已被 `huge_cells_per_item()` 消费，下游 `min_huge_cells()` → `candidates_for_bucket` → `_build_session.derived_sum` → `compute_analytical_estimate` 全自动用上，不需要碰任何推断模块
- **数据驱动选项**——选项列表从 `BIG_ITEMS_BY_SHAPE` 自动派生，未来加新物品零工程量
- **视觉前缀 `★`**——一眼区分"通用档"和"精确档"

### 「未确认品质巨物」明确标记为测试功能

UI 上的"未确认品质巨物（按形状）"区块，玩家可以填"看到 X 个 12 格物体不知道什么品质"。但这区的输入**从来没被任何推断模块消费**——实现起来要在 MC 每个 trial 里枚举品质组合（12 格物体可能是紫紫/紫金/紫红 ...），复杂度过高。本次明确改成 `st.warning` 横幅：

> 🧪 **测试功能，暂未接入推断接口**。本区仅记录你看到的形状数量，不会被推断引擎使用。若能确认品质，请在上方对应 bucket 的「巨物数量」下拉框选择「★ 具体物品」。

### 实战收益（修复前 vs 修复后）

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 仓库 80，未填金品 | 红品=19 格、估值 ~100 万 | 「未分配 9 格（金未填）」估值 350K-1M 区间，明确提示 |
| 紫品 value_sum=86,490, huge=1 | 紫=12 格×2,500 = 30K | 紫=35 格×2,471 = 86K（用户估价直接用） |
| 金品仅填件数=5 | 金=0 格、红=32 格 | 金=22 格、红=10 格（枚举估出 5 件 ≈ 4.4 格/件）|
| 紫品识别为防护盾 | 紫=12 格 generic | 紫至少 12 格，引擎知道是具体物品（精确数据） |

### 使用技术

- **数据驱动的 UI 选项派生**：`_huge_options_for_quality(q)` 把 `BIG_ITEMS_BY_SHAPE` 按品质过滤、生成 `(option_key, label)` 对；新增物品自动出现在下拉框
- **Streamlit `value=None` + `placeholder` 模式**：替换全部 `value=0`，配合后端 `if x is not None` 判断
- **二次枚举 pass**：`compute_analytical_estimate` 和 `_build_session` 共用 `candidates_for_bucket`，消费 `value_sum / count / avg_cells / huge_band / 仓库容量` 联合约束
- **明细文本数据来源标注**：「（用户估价）」「（由枚举推算→N件）」让玩家能追溯每个数字的来源

### TROUBLESHOOTING.md 新增条目

`#23 ~ #28` 共 6 条新踩坑，全部按"症状 / 原因 / 修法 / 教训"四段式归档。

### 下一开工节奏

- 进一步优化「混合形状巨物组合」（玩家同时识别游艇 + 防弹衣）— 当前 `huge_cells_override` 单值只能取平均，未来可升级到 `confirmed_huge_cells/value` 双字段精确表达
- "未确认品质巨物" 接入推断引擎（按形状枚举品质组合 → 联合后验）— 复杂度大，留作 v2

---

## Checkpoint #12 — 紫品/金品均价输入 + 紫色 huge 阈值放宽（2026-05-16）

### 关键发现

实战回归后玩家又反馈了三个使用层面的精度 / 易用性差距，都是"基础设施已经在 + 但 UI 不曝露"的典型半成品。

#### 1. 均价（`avg_value`）是独立信息源

游戏里 R3 提示有时直接给「紫品均价 6,000 silver」「金品均价 9,400 silver」。之前 UI 只接受 `avg_cells`（均格 = total_cells/count）和 `value_sum`（总价），没有"每件均价"通道。但 `avg_value` 跟另两者**信息独立**：

- 同时填 `avg_value` + `value_sum` → 引擎反推 `count`（硬约束，tol ±10%）
- 同时填 `avg_value` + `count` → 反推 `value_sum`
- 仅填 `avg_value` → 用 per-cell prior 估总价后再除 `count`，软约束（tol ±25%）

实测：`value_sum=86,490 + avg_value=6,178` 让紫品候选直接锁到 `(total_cells=35, count=14)`，跟之前需要 `avg_cells=2.5` 才能锁的效果接近——但 `avg_value` 是 R3 提示能直接读到的，比"凑均格 2.50 的小数尾"更接地气。

数据架构：

```python
# observation.py
@dataclass
class QualityBucketObs:
    ...
    value_sum: int | None = None
    avg_value: int | None = None    # NEW: per-item average price
    ...

# candidates_for_bucket inner loop
if bucket.avg_value:
    if bucket.value_sum:
        implied = value_sum / count       # tight: tol = 10%
    else:
        implied = pcv * total_cells / count  # loose: tol = 25%
    if abs(implied - avg_value) / avg_value > tol:
        skip candidate
```

UI 端紫品 / 金品 section 改成 6 列：cells / count / avg_cells / value_sum / **avg_value** / huge_band。下游全链路（`_build_session` 红品残差 / `compute_analytical_estimate` 二次枚举 / 候选预览面板）通过 `candidates_for_bucket` 自动消费，零额外接线——这是 C-28 那次"暴力枚举器贯穿全链路"重构的直接红利。

#### 2. 紫品 huge 阈值的数据真相

实战中玩家问「紫色巨物为什么只有 1 个，能否补充」。直接 query `Item.txt` 全表得到事实：

| 品质 | ≥12 格物品 | 名单 |
|---|---|---|
| 紫品 (q=4) | **1 件** | 可折叠高韧性防护盾 (3×4=12, 20,082) |
| 金品 (q=5) | 7 件 | 防弹衣 / 波斯毯 / 生化分析仪 / 无人作战车 / 服务器机柜 / 锂电池 / 单人郊游快艇 |
| 红品 (q=6) | 12 件 | 屏风 / 雷达 / 金枪鱼 / 跑车等 |

**紫品 ≥12 格游戏里就这一件**——不是漏收录。但 query 8-11 格紫品发现：5×2=10 的 `加特林重机枪` (31,688) 是紫品独占该形状（同 5×2 还有金品 q=5 巴雷特，但玩家可凭颜色区分）。

设计决策：放宽紫品 huge 阈值到 ≥10 格，纳入加特林；金 / 红保持 ≥12。

```python
HUGE_CELLS_PER_QUALITY: dict[int, int] = {
    4: 10,   # 紫品大件: 5×2 加特林 / 3×4 防护盾
    5: 12,   # 金品: 3×4 防弹衣等
    6: 12,   # 红品: 3×4 单兵外骨骼等
}
```

UI 端「什么算 巨物 / 大件」expander 拆分按品质说明阈值差异：

> - **紫品：≥ 10 格** 算大件。游戏里紫品 ≥ 12 格只有 1 件（防护盾），但 5×2=10 格的加特林重机枪玩家容易识别，所以阈值放宽到 10。
> - **金品 / 红品：≥ 12 格** (3×4)。

#### 3. `_items_for_quality(q)` 的 per-quality 过滤

当 `BIG_ITEMS_BY_SHAPE` 里存在跨品质同形状物品（5×2 同时有紫加特林 + 金巴雷特），原 `_items_for_quality(5)` 不看 cells 阈值会把巴雷特列入"金品大件"下拉——但金品阈值 12，5×2=10 不到。

修法：

```python
def _items_for_quality(q: int) -> list[dict]:
    threshold = HUGE_CELLS_PER_QUALITY.get(q, 12)
    out = []
    for shape, cands in BIG_ITEMS_BY_SHAPE.items():
        cells = _shape_to_cells(shape)
        if cells < threshold:           # NEW: per-quality cell gate
            continue
        for c in cands:
            if c["q"] == q:
                out.append(...)
    return out
```

带来一个有用的副作用：未来加任何新形状到 `BIG_ITEMS_BY_SHAPE`，每个品质的下拉自动按各自阈值过滤，不需要在 dict 里手动维护"哪些是 huge / 哪些不是"。

#### 4. MC 滑块三档说明

之前 `(500, 5000, 1000, step=250)`，help 只写了"大仓采样不足时调高"。实际玩家场景是：

- 快速试错 → 500 够用（接受 ±10% 浮动）
- 实战决策 → 1000 平衡
- 大仓 + 强约束（紫 cells + huge + value_sum 全填）→ 2000 推荐
- 冷门大仓 / 严重尾部 → 3000-5000

step 改 200 让常用区间 (500/700/900/1100/...) 选档更细；help 列出三档说明。

### v2 ranking / hero models 不受影响

本 checkpoint 全在 `inference` 层，没动 simulation / hero_value / robust_value。所有英雄排名 / map MC / ROI 数字保持稳定。

### 待做（已记 TODO）

- 「未确认品质巨物」按形状枚举品质组合接入推断（C-28 已标记为 v2 后续）
- 多个 `huge_cells_override` 同时确认（玩家同时识别"游艇 + 防弹衣"两件）需要双字段 API

### 测试

`tests/test_observation.py` 新增 3 条：

- `test_avg_value_filter_with_value_sum_pins_count`：value_sum + avg_value 联立锁 (35,14)
- `test_avg_value_filter_rejects_off_target`：avg_value=20K 跟 value_sum/count 不符 → 候选被砍
- `test_avg_value_without_value_sum_uses_loose_pcv_filter`：仅 avg_value 用 ±25% 软约束

阈值改动同步更新 3 条既有测试（`test_huge_cells_per_quality` / `test_bucket_huge_methods_defaults` / `test_bucket_huge_band_purple_2_to_3`）。总测试数 219 → 222 全绿。

---

## Checkpoint #N — 放仓推荐红约束接入 + MC 默认升档 (2026-05-16)

### 关键发现

`compute_pass_recommendation` / `compute_snipe_recommendation` 之前的 MC 过滤只考虑 `warehouse ± tol` 和 `purple_cells ± tol`，**完全忽略玩家填的红/金 bucket 信息**（`huge_band` / `value_range`）。

具体后果（H29 量化证据，map_id=2403, warehouse=80, purple=24）：

| 过滤层级 | n | p25 | p50（放仓阈值） |
|---|---|---|---|
| 仅 warehouse | 288 | 244K | 371K |
| **当前**：warehouse + purple | 104 | 243K | **358K** |
| **应该**：+ red_huge≥1 | 12 | 527K | **616K** |

红 huge=1 这条信息让中位仓价从 358K 抬到 616K（+72%）。当前引擎完全丢弃 → 用平均仓价当阈值 → 用户给"红有大件"提示时仍按低价仓建议放仓。

### 修复

1. `compute_pass_recommendation` / `compute_snipe_recommendation` 增 4 段 tier：
   - **cond_red**（warehouse + purple + red huge_band + red value_range）≥ min_matching_samples → 用
   - cond_red ≥ min_matching_samples_relaxed → 用 + 标 `low_confidence`
   - 否则 fall back 到 cond_purple / cond_warehouse / 宽松 cond_warehouse
2. 新增 `suppress_above_ratio: float = 1.0` 参数：当 `conditional p50 / unconditional p50 > 1.0`（仓库价值已高于全图均值）时，**整个放仓推荐返回 None**——这种场景下"超过 X 就放"的提示是误导。

End-to-end 验证：用户原 case（红 huge=1）的放仓阈值从 405K → "未触发"（被 suppress）；不给红约束的对照组仍正常触发（370K，n=78）。

### MC 默认从 1000 → 2000

实战反馈：1000 次的随机抖动有时让放仓 / 红 cells 后验跨阈值。默认升到 2000 后：

- 跑批耗时 ~10s（缓存命中后零开销）
- 中位估值的 run-to-run jitter 降到 ±2-3%
- help 文案重新分档：500=快速、1000=轻量、2000=默认推荐、3000-5000=尾部场景

### 已知遗留 — 待下个 checkpoint

放仓 / 秒仓 还有偶发问题（**未修**，记录在此供后续迭代）：

1. **同输入两次跑结果不同**：未固定种子时，n_matching_samples 在边界附近会跨阈值（30 / relaxed=10），导致放仓有时返回有时 None。**根因**：tier 选择是硬阈值；红约束样本本身就稀（典型 10-20）。**改进方向**：tier 切换用平滑权重（连续置信度），或给红约束做单独的 bootstrap CI。
2. **小红仓漏报**：79 格 / 红 1-2 cells / 全仓 22w 的低价红仓未触发放仓。**根因**：当前逻辑只在 `low_fraction ≥ 0.4` 时才进入 pass 分支，但红 cells 很少时低品占比可能不到 40%。**改进方向**：把"红 cells ≤ 2"也作为可选触发条件，或在 expected_value < threshold% × unc_p50 时直接进 pass 推荐分支。
3. **ratio 守卫粗糙**：当前简单按 `> 1.0` 判 suppress，没有平滑过渡。下次可改成 `0.85 < ratio < 1.05` 时显示 "中等仓位、自由发挥"，外侧才进 pass / snipe。

### 测试

`tests/test_snipe.py` 新增 2 条（229 → 231 全绿）：

- `test_pass_suppressed_when_conditional_value_above_unconditional_median`：ratio>阈值 → return None
- `test_pass_red_huge_filters_truths_when_active`：红约束启用时 cond_red 路径不抛异常（含空集 fallback）

---

## Checkpoint #31 — 参数接线审计 + 秒/放仓 UI 下线 (2026-05-17)

### 巨物 / 均格 / 均价：各走哪条路？

| 输入字段 | MC `filter_truths_by_obs` | 枚举 `candidates_for_bucket` | 分析估算 | 秒/放仓 `snipe.py` |
|----------|---------------------------|------------------------------|----------|-------------------|
| `huge_band`（紫/金/红） | ✅ 校验 truth `huge_count` | ✅ 格数下限 + 评分 | ✅ `min_huge_cells` | 仅 **红** huge + value_range（C-30） |
| `huge_cells_override`（★具体物品） | ❌ | ✅ `huge_cells_per_item()` | ✅ 同左 | ❌ |
| `avg_cells` | ❌ | ✅ 强约束（display 规则） | ✅ 经枚举 | ❌ |
| `avg_value` | ❌ | ✅ ±10%（有 value_sum）或 ±25%（无） | ❌ 不参与估值公式 | ❌ |
| `value_sum` | ✅ ±容差 | ✅ + Item-DB boost | ✅ 直接当中位 | ❌ |
| 未知品质形状巨物 | ❌ | ❌ | ❌ | ❌ |

**设计结论（非 bug）**：`avg_cells` / `avg_value` **故意不进 MC**，只在「枚举候选 + UI 预览 + 分析估算推格数」里收紧；避免地图 R3 均价 hint 与 MC 样本分布打架。若要让 MC 分位也受均价约束，属于 **Phase 2 增强**，需单独设计容差。

**已知缺口（算设计债，非废弃字段）**：

1. `huge_cells_override` 不进 MC —— 「★游艇 18 格」只帮枚举/分析，不过滤「样本里是否真有 18 格金巨物」。
2. ~~`adaptive_filter` fallback 重建 bucket 时丢失 `huge_cells_override`~~ → **已修 C-32**（见 Checkpoint #32）。
3. 紫/金 `huge_band` 不进秒/放仓 cond 链（仅紫 cells + 红 huge）。

### 秒仓 / 放仓 UI 下线

与「未知品质巨物」同策略：`_ENABLE_SNIPE_PASS_HINTS = False`，展示实验性说明；`inference/snipe.py` 与 `tests/test_snipe.py` **保留**。待办见 PROGRESS「推断引擎 backlog」。

### P1 已落地（2026-05-17）

- UI：紫品 info 框 + 金/红 caption + 出价 tab 说明 —— **均格/均价不进 MC**。
- 枚举：`active_reading_constraint_count` ≥ 4 时 `avg_value` 容差 10%→18%（有总价）或 25%→35%（无总价）；**不改 MC、不增加 MC 采样**。
- 预览：多字段时 caption 提示「仅影响下方枚举」。

### P2 建议（暂不实现）

| 项 | 建议 | 理由 |
|----|------|------|
| **均价进 MC** | **不做**；不必加侧边勾选 | P1 已说明分工；进 MC 易「过滤后零匹配」，与地图 hint 分布不一致 |
| **★具体巨物进 MC** | **暂缓** | 现 MC 只过滤 `huge_count` band；override 格数只服务枚举。若进 MC 需按 truth 最大单件格数或物品表匹配，**会显著减少匹配样本**、小图更常 fallback，收益待 snipe/pass 修好后再评估 |
| **秒/放仓** | UI 已关，后端保留 | 见 TROUBLESHOOTING #30 |

### 用户拍板（2026-05-17）

- **P0-A 秒/放仓**：暂缓，UI 保持关闭；方案已写在 PROGRESS「下一步推进 TODO」供日后恢复。
- **C-32 已完成**：P0-B — `_fallback_hard_buckets` 保留 `huge_cells_override`。

### 后续可选优化

见 PROGRESS.md「下一步推进 TODO」与 backlog 归档 — P2/P3、P0-A 仍暂缓。

---

## Checkpoint #32 — P0-B：`fallback` 保留 `huge_cells_override` (2026-05-17)

### 触发场景

`adaptive_filter` 在三级 cells 容差仍凑不满 `min_samples`（默认 30）时，进入 **warehouse-only fallback**：只放宽仓库总格，但保留「硬断言」bucket（红=0、红 cells、正 `value_sum`、`huge_band` 等）。重建 `QualityBucketObs` 时若只拷贝 `huge_band`、丢掉 `huge_cells_override`，★ 具体巨物（如 18 格游艇）会 silently 退回品质默认格数（金 12）。

### 修法

`posterior._fallback_hard_buckets(obs)`：在 `value_sum` / `huge_band` 两条重建分支均带上 `huge_cells_override=b.huge_cells_override`。`tests/test_posterior.py::TestFallbackHardBuckets`。

### 实际作用域（重要）

| 路径 | 是否用 `fallback_obs` | override 是否影响行为 |
|------|----------------------|------------------------|
| MC `filter_truths_by_obs` | ✅ fallback 时 | **否** — 只校验 `huge_count` 落在 band，不按单件格数过滤 |
| 枚举 / 分析估算（Streamlit） | ❌ 用完整 `session` | **否** — 本来就不经过 hard_buckets |
| `constraints_applied` 文案 | ✅ | 间接 — hard 描述仍只写 `huge=band` |

**结论**：C-32 是 **数据一致性 / 防回归** 修复，避免 fallback 路径上对象残缺；对多数对局的 MC 分位、枚举、分析估算 **几乎无可见变化**。真正让 ★ 巨物影响推断的仍是枚举链上的 `huge_cells_per_item()`（完整 session）。

### 风险

| 风险 | 级别 | 说明 |
|------|------|------|
| 行为突变 | **极低** | 仅多拷贝已有 int 字段；单测锁定 |
| 过严过滤 | 无 | 未改 `filter_truths_by_obs` 逻辑 |
| 与 P2「★进 MC」混淆 | 注意 | 进 MC 会显著减样本，属 Phase 2，未做 |

---

## Checkpoint #33 — C-35 面板 OCR + 地图切换状态机 (2026-05-17)

### 问题与修法（Streamlit 侧栏）

| 现象 | 根因 | 修法 |
|------|------|------|
| 点地图 × 不清读数/截图 | `_on_map_context_changed` 在 `new_mid is None` 时早退 | 仅当 `prev_mid is None` 或同 ID 时跳过；清空地图走完整 reset |
| 上传截图后换图 → toast 闪烁、地图锁死 | 换图 `obs_map_select_rev+1` 后未写入新 widget key → `resolved=null` 触发 post-sync 二次 reset 循环 | `_sync_map_select_widget_value`；`_map_change_toast` 屏蔽 post-sync；去掉 toast 后 `st.rerun()` |
| OCR 只填 wg/蓝 | 「优品」误匹配蓝品规则；「总点位数」未匹配 | `patterns` 紫/金/蓝顺序 + `ocr_normalize` 纠错 |
| 仓库 `int(None)` | `number_input(value=None)` 与 tab 里 `int(warehouse_cells)` | `_warehouse_capacity()` / `_session_int()` |
| 上传区单独 × | 用户拍板：与读数一致，**仅换图自动清** | 移除独立清除按钮；`_clear_capture_upload()` 仍在 `_on_map_context_changed` |

### 使用技术

- **版本化 widget key**：`obs_map_select__r{N}`、`capture_file_uploader_{rev}`、`obs_reading_*__r{N}` — bump 即强制 Streamlit 丢弃旧 state。
- **OCR 暖机**：后台线程 `warm_ocr_engine()` 用 1920×1080 哑图走完整 crop+OCR 路径（~2.8s），不阻塞首屏。
- **capture 与 inference 解耦**：`apply_capture_result` 只写 session / widget keys；MC 仍由 `bg_inference.py` 触发。

### C-36 接口（已接 UI）

- `capture/screen.py`：`INFO_PANEL_CROP_FRAC = (0.30, 0.07, 0.59, 0.72)`；`capture_monitor_panel()` + 多显示器。
- 参考分辨率 `1920×1080` 用于文档与暖机；实机按该屏宽高比例裁剪。

---

## Checkpoint #34 — C-37 Streamlit 稳定性 + 实机 OCR 性能 (2026-05-18)

### 背景

C-36 接通主屏抓屏后，用户反馈：**诊断里 OCR 有数但紫品均格框为空**、**切 tab 读数被清**、**MC 莫名取消**、**实机 OCR 比早期「几秒变快」前更慢**。本轮不改 MC/枚举核心，只收口 UI 状态机与 capture 热路径。

### Streamlit / widget 修法

| 现象 | 根因 | 修法 |
|------|------|------|
| 紫均格 OCR 有、输入框空 | `text_input(value="")` + session `obs` 空串挡住 hydrate | 去掉固定 `value=""`；`reconcile_avg_raw_widget_return`；观测 tab `force_avg_raw` |
| 切到「出价推荐」再回来读数没了 | `sync_obs_from_reading_widgets(allow_clear=True)` | 读数 tab 上 `allow_clear=False` |
| 后台 MC 被取消 | Ethan 观测字段污染 fingerprint | 仅在**地图上下文**变更时 `cancel_bg_inference` |
| hint 下出现幽灵读数块 | 条件渲染 + 额外 DOM rerun | 四 tab `st.empty()` 槽位；删 `_hint_tab_dom_refresh` |
| 抓屏时整页卡死 | OCR 在 sidebar spinner 同步跑 | `_deferred_capture_job` + `st.status`；`apply_capture_result` 提到 sidebar 渲染前 |
| 误提示「请打开出价推荐」 | 抓屏后自动切 tab | 按 `_main_tab` 区分 toast/banner |

### 实机 OCR 变慢（回归）与修复

**体感慢**常是「抓屏 + 预处理 + OCR + 诊断缩略图」整段，而不只是 ONNX：

1. `prepare_image_for_ocr` 对已裁面板仍 **PNG 再编码**，RapidOCR 再解码 — 双倍 IO。
2. 每次抓屏生成 **4K 全屏 ROI 预览**（复制 + JPEG）。
3. 上传路径 **先 `crop_info_panel` 再 OCR** — 双解码。

**修复**：

- `panel_rgb_array_for_ocr` → `uint8` RGB ndarray 直推理。
- `include_monitor_preview=False`（默认）；暖机抓屏同样关闭预览。
- 上传/剪贴板单次解码；`prepare_image_for_ocr` 无 crop/resize 时 **early return**。
- 诊断区展示：`抓屏 XXms · OCR XXms · 诊断图 XXms`（`_png_for_debug_store` 在 OCR 之后，不阻塞推理本身）。

用户验收：实机速度恢复正常。

### 配置与调试

- `data/ui_prefs.json`：`screen_ocr_warmup`（高级 MC 区勾选，**改后需重启**）。
- `BIDKING_AGENT_DEBUG=1` → `app/agent_debug_log.py`；默认关闭。
- MC 默认仍 **1500**（未再 cap 到 1000）。

### 暂缓 / 下一迭代

- **启动等待界面**（C-38）：首屏加载 UX，与侧栏暖机 spinner 分工。
- **Canvas 跳跃小游戏**：后台暖机时玩；用户暂缓。
- 完整 OCR×手填×换图 **状态机矩阵** + 单测：见 PROGRESS「C-37 边界」；C-39 已补桶级清理与预览 relax。

---

## Checkpoint #35 — 读数三条路径、OCR 残留与 MC 采样耗时（2026-05-19）

### 三条数据路径（必须区分）

| 路径 | 模块 | 消费字段 | 不消费 |
|------|------|----------|--------|
| **MC 后验** | `posterior.adaptive_filter` / `hint_pipeline` | `total_cells`, `count`, `value_sum`, `value_range`, `huge_band`, 仓库, `total_item_count` | `avg_cells`, `avg_value`（设计分层，#31） |
| **分析估算** | `compute_analytical_estimate` | 上列 + 经 `candidates_for_bucket` 用 `avg_value` 推格 | — |
| **候选预览** | `_render_candidate_preview` + `relax_bucket_for_enumeration_preview` | 枚举全部约束；可 **放宽** OCR 脏字段 | **不参与 MC** |

用户问「数据有没有废弃」：否。OCR 与手填写入同一 `state` 后走路径相同；差异多在 **预览层** 残留键（`gold_cells=0` + `gold_avg_value=35100`）导致 0 候选或退化为 `(0,1)`。

### OCR vs 手填：金品均格案例

- **手填** `gold_cells=26`（无均价）→ 约 25 种 `(cells,count)`，预览 💡。
- **OCR** 常写入 `gold_avg_value` / `gold_count`；若 session 残留 `gold_cells=0`，严格枚举无解；`relax_bucket` 去掉均价后若仍 `total_cells=0` → 预览退化为 0格/1件（已用 `effective_number_field_for_preview` + 仅均价时清 `gold_cells` 缓解）。

### 地图清空 vs 读数残留

仅 `pop("map_id")`（例如类别筛选不匹配）**不会**清空 `obs` 读数字段 → UI 出现「地图空、读数仍在」。修法：`reset_obs_for_manual_map_change` + 取消后台 MC（`readings_rev` fingerprint）。

### MC 性能（`debug-*.log` → `MC timing`）

| 环节 | 典型耗时 | 备注 |
|------|----------|------|
| `sample_ms` | 7s（热缓存）~ 108s（冷缓存 2401/1500 trials） | `_sample_truths_cached(map_id, n_trials, seed)` |
| `filter_ms` | 1–15 ms | 可忽略 |
| OCR 抓屏 | 5–8 s | 在 MC 之前 |
| 启动暖机 | ~45 s | `screen_ocr_warmup`，仅首启 |

**慢的主因**：换地图 cache miss、侧栏 1500 trials、读数变更触发 `bg hint cancelled by fingerprint` 重跑。

### 演示

`notebooks/07_capture_readings_and_mc_perf.ipynb`

---

## Checkpoint #36 — 优化路线盘点 + MC 采样预编译（2026-05-26）

### 关键发现

1. **后台 MC 慢的首个明确瓶颈不是 filter，而是重复 flatten drop pool。**
   2401 / 2501 这类 anthology 地图有 10 个 sub-pool；旧 `_sample_truths_cached`
   每次调用 `sample_session_truth()` 都会重新走 `_resolve_sub_pool()` → `flatten_pool()`。
   200 次采样实测约 3 秒，其中约 2.8 秒花在 flatten loop。

2. **普通地图也受益，但 anthology 地图收益最大。**
   2405 单池地图旧 200 次采样约 0.3 秒；新 sampler 后约 0.01 秒。
   anthology 地图从约 3 秒降到约 0.01 秒，准备 sampler 本身约 0.016 秒。

3. **UI 慢点和 MC 慢点需要分开处理。**
   采样预编译解决的是 cold MC sampling；`_tab_pane` + Streamlit rerun + widget
   hydrate/sync 仍是 UI 切换效率的下一阶段问题，适合单独做 fragment 化。

### 使用技术

- `SessionTruthSampler`：预先把 `FlattenedPool` 转成 numpy arrays + item tuple。
- `prepare_session_sampler()`：每张地图只 flatten 一次；保留旧 `sample_session_truth()`
  作为单次采样兼容入口。
- 回归测试：单池地图与 anthology 地图同 seed 下保持 sampling semantics。

### 实测

| 地图 | 旧 200 次采样 | 新 200 次采样 | sampler prepare |
|------|---------------|---------------|-----------------|
| 2401 未知别墅 | 2.951s | 0.012s | 0.016s |
| 2405 望族居所 | 0.307s | 0.011s | 0.002s |
| 2501 未知残骸 | 3.002s | 0.013s | 0.017s |

### 优化路线决策

详见 `docs/optimization_roadmap.zh-CN.md`。当前排序：

1. P0：UI fragment 化（先拆函数，再移动到 fragment）。
2. P1：Session-level 联合候选（beam search 综合仓库大小、均格、均价、总价）。
3. P1：多级评估 + Pareto 出价建议。
4. P1：枚举引擎 fingerprint cache。
5. Research：网络抓包/ProtoHub 只读验证，先确认协议和合规边界。

### 验证

```powershell
python -m pytest tests/test_ground_truth.py tests/test_bg_inference.py tests/test_posterior.py -q
python -m pytest -q
python scripts/demo_scenarios.py
```

---

## Checkpoint #37 — P0 UI fragment first cut（2026-05-26）

### 关键决策

先切断读数 tab 对共享 `_tab_pane` 的依赖，不做大规模 UI 搬家：

1. `_main_tab == "obs"` 时定义并调用 `_render_obs_tab_fragment()`。
2. 读数 UI 整块包进 `@st.fragment`，内部使用 `st.container()`。
3. `_tab_pane` 只在 hint / joint 旧路径创建，ROI 继续走原本的直渲染。
4. 读数页内部 widget key、hydrate/sync 顺序、文案全部保持不变。

### 为什么不一步抽 `render_obs_tab`

读数块仍有 600+ 行，闭包依赖 `state`、`hero`、`maps`、`_rwk`、`_cells_budget_err`
等大量上下文。一次性移动成独立函数/模块风险高，且很容易引入 widget key 或
session_state 清空回归。first cut 的目标是先让 fragment 边界生效，再逐步抽函数。

### 验证

```powershell
python -m py_compile app\streamlit_app.py
python -m pytest tests/test_bg_inference.py tests/test_capture.py tests/test_posterior.py tests/test_ground_truth.py -q
python -m pytest tests/test_inference_display.py tests/test_observation.py -q
```

---

## Checkpoint #38 — Pytest smoke 分层（2026-05-26）

### 关键发现

`pytest --collect-only -q` 只需约 0.38 秒，说明慢点不在 collection / import。
`pytest -q --durations=30` 显示慢点高度集中在 `tests/test_ocr_regression_normalize.py`：

- repo sample OCR：约 4 秒。
- 6 张用户截图 OCR：每张约 2.4–3.2 秒。
- 旧实现对同一图片在 smoke / parse / map-name 测试中重复 OCR，导致全量约 40 秒。

### 决策

1. 真实 OCR 图片回归属于 release 前检查，不属于每次代码改动的 smoke test。
2. 给真实 OCR 图片测试标记 `@pytest.mark.slow`。
3. 增加模块级 `ocr_text_cache`，同一图片在同一次 pytest 进程里只 OCR 一次。
4. 新增 `scripts/test_smoke.ps1`，默认跑 `python -m pytest -q -m "not slow"`。

### 实测

| 命令 | 结果 | 时间 |
|------|------|------|
| `.\scripts\test_smoke.ps1` | 395 passed, 13 deselected | 3.94s（热）/ 约 9.8s（冷） |
| `python -m pytest -q` | 408 passed | 25.83s |

### 使用约定

- 日常改 UI / 推理 / 文档：先跑 `.\scripts\test_smoke.ps1`。
- 改 OCR、normalize、release 前：跑 `python -m pytest -q`。

---

## Checkpoint #39 — 分析估算接入联合候选（2026-05-26）

### 关键发现

`candidates_for_bucket()` 的单桶 top-1 局部最优不一定是 session 全局最优。
例如 60 格仓库里，紫品和金品均格/总价各自的局部 top-1 都可能是 `35格/14件`，
但两者合计 70 格，物理上不可能同时成立。旧 `compute_analytical_estimate()` 会分别取
两个局部 top-1，导致分析估算过仓。

### 决策

1. 分析估算优先调用 `joint_top_k_for_session(k=1, per_bucket_top=16, warehouse_slack=5)`。
2. joint 命中的非白绿、非显式格数 bucket，直接回填 `known_cells` 和 `inferred_count`。
3. joint 无结果或未覆盖的 bucket 保留原单桶枚举兜底。
4. `avg_value` 的整数泄漏件数逻辑继续沿用，避免回归「均价是每件」的修复。

### 验证

新增 `test_analytical_uses_joint_bucket_capacity_constraint`：

- 输入：60 格仓库，紫/金都只有均格 `2.5` + 总价。
- 期望：分析估算明细使用 `紫 30格` 与 `金 30格`，而不是两个局部 `35格`。

```powershell
python -m pytest tests/test_joint.py tests/test_posterior.py -q
.\scripts\test_smoke.ps1
```

---

## Checkpoint #40 — 联合筛选 tab 恢复与解释型 UI（2026-05-26）

### 背景

C-20 曾把联合推断 tab 隐藏到侧栏实验开关后面。原因是当玩家已经填了所有
`total_cells` 时，top-3 只在件数上有很小差异，旧表格看不出实际价值。

C-49 后，联合候选已经能修正分析估算里的局部 top-1 过仓问题，所以 UI 也有必要恢复：
它可以解释“为什么紫/金各自看最优，但合在一起不成立”。

### 改动

1. 主导航常驻显示「联合筛选」，移除 `show_experimental_tab` 开关。
2. 结果从单张表改为 top-5 hypothesis expander。
3. 顶部对比 `联合 top-1 格数` 与 `独立 top-1 合计`，直接暴露容量冲突。
4. 每个品质显示输入约束、联合结果、独立 top-1、评分拆解和调整原因。
5. 结果按当前读数 fingerprint 缓存，读数变化后自动刷新。

### 设计判断

这个 tab 不替代出价推荐。它的定位是“推理依据面板”：

- 出价推荐回答“这仓值多少钱、该不该拍”。
- 联合筛选回答“当前读数如何约束紫/金/红的格数和件数，为什么这样推”。

---

## Checkpoint #41 — 出价页接入 joint 摘要（2026-05-26）

### 决策

joint 摘要接到出价页，但保持折叠显示。原因：

1. 它解释推理依据，不是直接动作建议。
2. 出价页主任务仍是价值区间、MC 样本量和风险信息。
3. 秒仓/放仓应在 Pareto 多级评估之后再恢复，避免把“结构推理”和“下注动作”混在一起。

### 实现

- `experimental_tabs.py` 增加 `render_joint_reasoning_summary()`。
- 出价页 hint bundle 有效时，在价值区间卡片前渲染 joint 摘要。
- 摘要复用 full tab 的 `_joint_context()` 和独立 top-1 对比逻辑。

### 用户可见信息

- 联合 top-1 vs 独立 top-1 的仓库容量差异。
- 哪些 bucket 被 joint 为了满足仓库约束而修正。
- 每个 bucket 的输入约束、joint 结果、独立 top-1 和评分拆解。

---

## Checkpoint #42 — 实时监控路线与 live 观测接口（2026-05-26）

### 关键判断

未来如果接入 ProtoHub / 抓包直读，最大收益不是单纯替代 OCR，而是获得更稳定的实时状态：

- 地图 / 仓库总格数。
- 当前轮次 / 当前阶段。
- 伊森技能看到的未知品质 footprint。
- 可能的物品 quality / item_id / value。

这些信息不应该直接写入 `SessionObs`。`SessionObs` 是推理输入，不是实时世界状态。

### 决策

新增一层 `bidking_lab.live` 观测接口：

```text
manual / ocr / packet / derived
        ↓
LiveObservationBatch
        ↓
LiveSessionState reducer
        ↓
SessionObs adapter
        ↓
joint / MC / Pareto
```

当前落地：

- `FieldUpdate`：逻辑字段更新。
- `GridItemObservation`：未知品质 footprint / 已知 item_id 的预留接口。
- `LiveObservationBatch`：一次轮询或一次 UI 操作产生的一组观测。
- 来源优先级：`packet > manual > ocr > derived`。
- `LiveSessionState` reducer：合并字段、保留 grid item、维护 version/dirty。
- `live_state_to_session_obs()` adapter：把当前 live state 转成推理层 `SessionObs`。

### 优先级变化

1. 先做 reducer + adapter，统一手填 / OCR / packet 输入。
2. 再做枚举 / joint cache，支撑高频状态刷新。
3. 再做自动重算状态机。
4. 最后做 Pareto 和秒仓/放仓动作层。

### 边界

ProtoHub 方向先做离线 fixture，不连接游戏进程；不注入、不改包、不自动竞价。

---

## Checkpoint #43 — 枚举缓存与离散重算事件（2026-05-26）

### 决策

1. `candidates_for_bucket()` 保持原排序与约束逻辑，仅在外层增加 fingerprint LRU cache。
2. fingerprint 包含 bucket 全部有效读数、仓库容量、已占用格数和 `max_count`，避免不同预算错误复用结果。
3. cache 保存不可变 tuple，对外返回新 list，避免候选预览修改共享对象列表。
4. 实时输入不按 packet tick 重算：`round_changed`、`tool_revealed`、`public_info_changed` 等语义事件置 dirty；`heartbeat` 只更新元数据。

### 实测与验证

- 紫品 `均格=2.5 + 总价=86490`：cold 枚举约 `22.1ms`，相同约束 1000 次 cache hit 总计约 `0.39ms`。
- 新增候选 cache 命中、列表隔离、剩余预算区分测试。
- 新增语义事件门控与 heartbeat 不置 dirty 测试。
- 聚焦回归：`79 passed`；smoke：`408 passed, 13 deselected`；全量：`421 passed`。

---

## Checkpoint #44 — OCR/手填 shadow live bridge（2026-05-26）

### 决策

1. 新增 `live.legacy` 适配器，以 `obs` 快照差异生成 `manual_update` / `ocr_update` batch。
2. OCR apply 和手填 sync 均镜像写入 `LiveSessionState`，但当前 hint / MC 继续消费 legacy `obs`。
3. 该桥接先固定映射与事件语义，不在同一步改变用户可见推荐或 OCR 覆盖行为。

### 需要在 canonical 切换前解决的边界

现有界面中，重新 OCR 可覆盖已有手填字段；live reducer 的目标优先级是
`packet > manual > ocr > derived`。若直接把推理输入切到 live state，屏幕输入框与
推荐依据可能不一致。因此下一步应先显示关键字段来源，并提供明确的“接受 OCR 覆盖”
或“保留手填”交互。

### 验证

- 新增 legacy OCR 映射、手填清空、艾莎 split 分桶测试。
- 聚焦回归：`76 passed`；smoke：`411 passed, 13 deselected`；全量：`424 passed`。
- Streamlit headless health/page：HTTP `200`。

---

## Checkpoint #45 — shadow bridge 与现有构建器等价性审计（2026-05-26）

### 发现的问题

`LiveSessionState` 还没有驱动当前 hint/MC，因此 C-54 不会立即影响玩家可见结果；
但逐字段比对 `_build_session()` 后发现 bridge 不能直接用于下一阶段切换：

1. 巨物下拉框可产生 `item:<name>`，现有 UI 会解析为 `huge_band="1"` 加精确
   `huge_cells_override`，shadow 事件原本只保留了原始 selector 值。
2. 低品、件数和总件数的默认 `0` 在现有构建器中表示“未提供”，shadow adapter
   原本会把它们创建为显式零值 bucket。
3. 小仓红品上限和 Aisha 无法观察金/红巨物的规则尚未在 bridge 中复刻。

### 修复

- 在 Streamlit 发送 shadow batch 的边界解析巨物具体物品，写入有效 band 与
  `huge_cells_override`。
- `live.legacy` 对显式字段执行与现有 session 构建器一致的零值、角色可见性和
  小仓红品映射；均价文本支持千分位输入。
- `live.state` 对非法 `huge_band` 防御性回退为 `none`。

### 边界与验证

本轮仍不切换 canonical input：当前推荐继续消费 legacy `obs`。后续仍需先完成
字段来源展示和 `manual > ocr` 的显式覆盖交互。

- 新增 5 条 bridge 等价性测试。
- 聚焦回归：`157 passed`。
- smoke：`416 passed, 13 deselected`。
- 全量：`429 passed in 25.04s`。
- `python scripts/demo_scenarios.py`：正常。

---

## Checkpoint #46 — 启动暖机改为首次 OCR 按需加载（2026-05-26）

### 发现

旧主页面在任何侧栏或主 tab 出现前，都会同步创建 OCR 引擎并运行样例图暖机；
启用实屏暖机时还会追加真实抓屏路径。这会让只想手填、查看联合筛选或浏览已有
状态的玩家也承担 OCR 初始化等待。

### 改动与取舍

- `_cached_ocr_engine()` 保持每个 Streamlit 进程一个引擎，但改为仅在已有 OCR
  请求时调用；首次请求直接处理真实输入，不另跑启动样例/实屏暖机。
- 抓屏、剪贴板和上传图片 OCR 不再因为启动暖机未完成而被禁用。
- 删除只服务于阻塞启动路径的等待页、进度条和 `screen_ocr_warmup` 设置入口。
- 首屏和手填路径立即可用；第一次实际 OCR 可能更慢，后续会复用已创建的引擎。

### 验证

- `py_compile app/streamlit_app.py app/ui_loading.py` 与 `git diff --check` 通过。
- 聚焦回归：`160 passed`；smoke：`416 passed, 13 deselected`；全量：`429 passed in 25.74s`。
- `python scripts/demo_scenarios.py`：三个场景正常。
- 全新 Streamlit 进程首屏约 `2.8s` 出现完整界面；浏览器检查确认抓屏与剪贴板 OCR
  按钮可用，`OCR 引擎加载中` / `正在准备推断台` 均未出现。

---

## Checkpoint #47 — 观测输入不应被 60/80 这类 UI 小上限截断（2026-05-26）

### 发现

`总藏品件数` 使用 `max_value=60`，部分品质格数使用 `max_value=60/80`。这会让
Streamlit 在前端直接拒绝玩家输入 `90`，错误信息为
`Value must be less than or equal to 60`。

### 结论

这些上限是 UI 旧假设，不是推理层规则。游戏表中的 `items_per_session_max`
目前最大为 44，但这是地图抽样件数范围；它不能作为玩家手填/OCR 读数的前端硬帽。
截图回归中也能解析到 `warehouse_cells=89` 和多组 40-54 格的品质读数。

### 修复与验证

- 移除仓库格数、总藏品件数、各品质总格数/件数输入框的小型 `max_value`。
- 保留下游容量校验、joint 总件数约束和 MC 过滤，由推理层判断输入是否矛盾。
- 新增回归：parser 接受 `本仓共有90件藏品`；主 UI 源码不再保留 `max_value=60/80`。
- `Pictures\\Bidking*.png` 13 张截图 OCR/解析完成；浏览器验证 `总藏品件数=90`
  可输入并应用，旧错误不出现。
- 聚焦测试：`109 passed`；smoke：`418 passed, 13 deselected`；全量：`431 passed`。

---

## Checkpoint #48 — 第一份真实 TCP 抓包样本进入离线分析（2026-05-27）

### 关键判断

FatbeansCreater 底栏显示的“已捕获 741”不是本轮真正需要的范围。用户按 TCP 与
`BidKing.exe` 主连接过滤后导出的 `220` 条 packet，全部集中在
`127.0.0.1:59685 <-> 8.133.195.27:10000`，已经排除了公告、登录、HTTP 文本等
噪声。对 packet adapter 来说，这种筛选后的主会话比“全部包”更适合作为第一份
fixture。

### 技术发现

- Fatbeans JSON 同时保存 `HexData` 和 Base64 `Data`，解码后长度与 `DataLength`
  一致，说明不是 UI 文本复制，也没有明显截断。
- 应用协议使用 4 字节大端长度前缀。当前样本可重组为 `193` 条完整 frame：
  上行 `73` 条，下行 `120` 条，无尾部残片。
- 上行 frame 头部形态为 `length + 32 d2 55 xx + message_id + body`。
- 下行 frame 头部形态为 `length + server_seq + request_tag + message_id + body`。
  当 `request_tag=0` 时，看起来是服务器主动 push。
- 已定位候选业务消息：
  - `SEND msg=0x0022`：字段 2 为 session id，字段 3 像出价值。
  - `SEND msg=0x0026`：字段 2 为 session id，字段 3 像道具或局内动作 id。
  - `REV push msg=0x0025`：疑似每轮状态同步，嵌套字段可读 `map=2401`、
    `round=1..4`，并有玩家/结果/公开信息重复字段。
  - `REV push msg=0x002d`：疑似 R5 / 结算 / 技能结果大包，包含同一 session、
    `map=2401`、`round=4` 和多组玩家/结果块。

第二份样本 `bidking_package3.json` 进一步验证了消息结构稳定性：

- `map=2404`、session `2404:1274127889621635`，3 轮对局。
- `SEND msg=0x0026` 的字段 3 是道具/动作 id，例如 `100105`、`100104`、
  `100124`。
- `REV push msg=0x0025` / `0x002d` 的 field8 里能找到动作结果：
  `100105 -> 51`（蓝品总格）、`100104 -> 10`（白绿总格）、
  `100124 -> 36798`（紫品总价）。
- `REV push msg=0x0025/0x002d` 的 field7 能表示地图公开信息，例如
  `map=2404 -> 8`（金品总格）。
- 等待时收到的 `REV push msg=0x0077` 小包包含玩家 id 与 session id，但当前没有
  看到可直接解释为“对手出价金额”的字段；更可能是玩家已行动/状态同步通知。

第三份样本 `bid_king_project4.json` 把截图/人工备注对齐到更细字段：

- `map=2401`，session `2401:1274127923736451`，3 轮未知别墅局。
- 地图公开信息可读为 fixed32 小端浮点：`200014 -> 2.965517`（平均格数），
  `200033 -> 3765.0`（随机 9 件平均价值）。
- 道具结果仍在 `0x0027` 直接响应和 `0x0025/0x002d` 状态包中复现：
  `100105 -> 48`、`100104 -> 8`、`100124 -> 45778`。
- `0x0025/0x002d` 的玩家块能读出揭示价序列：我方 `290000 -> 290000 -> 290000`、
  梦色幻想 `288888 -> 288888 -> 188888`、折翼的奇美拉 `220000 -> 220000 -> 220000`、
  设计师 lcjeremy `153299 -> 145555 -> 417779`。
- 结算包 `0x002d` 顶层 field5 为 `16566`，对应用户截图亏损 `165,660` 的
  10 倍显示关系；最终状态嵌套字段能找到仓库总格 `86` 与物品数 `29`。

第四份样本 `bid_king_packages_5.json` 进一步确认了 item 级字段：

- `100136` 是宝光四鉴。它的 action block 不返回整数结果，而是返回 4 条
  `runtime id + quality`：两紫两金。该包不直接给 item_id。
- `100129` 是随机抽检（2）。它的 action block 直接返回 item_id、品质、价值、
  shape code 和 cells：`1021005 医用一次性口罩`（白，2 格，207）与
  `1023009 静脉注射用人免疫球蛋白`（蓝，1 格，1313）。
- `100112` 是优品均格，结果在 fixed32 field11 中，本样本为 `2.3076923`。
- 结算 `0x002d` 的 inventory block 可用 runtime id 还原完整战利品清单，并把宝光
  的 4 条品质结果对回具体物品：输液泵、单兵水下推进器、和田玉原石、机械腕表。
- package5 的完整 inventory 为 `42` 件、`114` 格、表内价值 `753522`；用户手动记的
  `114` 格与 `753522` 对齐，手动 `41` 件应以 packet 的 `42` 件为准。
- 结算玩家 values 序列不保证按时间顺序排列；例如赢家 `九千年之梦` 的 `750000`
  出现在 values 序列开头，因此不能简单用“最后一个 values”当最终成交价。
- 用户实测 VPN / UU 加速器会干扰 Fatbeans 抓包；后续采样应关闭加速器，筛选主 TCP
  会话后导出 JSON。

第五份样本 `bidking_package6.json` 验证了艾莎路线：

- 艾莎技能 reveal block 可解析为 `runtime_id + quality + shape_code`，R1-R4 累积给出
  白/绿/蓝/紫轮廓，能直接生成对应品质的 cells 与 count。
- 该样本结算 inventory 为 `53` 件、`137` 格；品质件数/格数分别为
  白 `6/11`、绿 `13/24`、蓝 `14/28`、紫 `9/32`、金 `7/29`、红 `4/13`。
- 公开信息 `200026` 能给出若干物品的 `runtime_id + quality`，但不一定给 shape/name；
  要靠后续技能 reveal 或结算 inventory 回填。

第六/七份样本 `bid_king_packages7.json` 与 `bidking_package8.json` 继续验证艾莎和
分类鉴影：

- 两份包里没有 `100107 极品扫描`。实际 action 为：
  - package7：`100129 随机抽检（2）`、`100136 宝光四鉴`。
  - package8：`100136 宝光四鉴`、`100129 随机抽检（2）`、
    `100157 【数码娱乐】鉴影`。
- `100157` 返回数码娱乐轮廓 item observation；当前样本为 3 件，shape code
  `13`、`11`、`11`。
- package7 结算：`33` 件、`85` 格、价值 `292428`；品质件数
  白/绿/蓝/紫/金/红 = `8/7/8/4/5/1`，品质格数 = `18/11/27/9/19/1`。
- package8 结算：`37` 件、`101` 格、价值 `483668`；品质件数
  白/绿/蓝/紫/金/红 = `5/3/14/8/4/3`，品质格数 = `7/4/44/35/7/4`。
- package8 里缺失的 `1306006/1306007/1306011/1306013` 来自 5.27 活动表：
  十二生肖藏品 `1306003..1306014`，均为蓝色品质、`2x2`、价值 `8888`。
  同步游戏源表并重建 processed 后，战利品价值可完整计算。
- 同步源表时确认当前 `BidMap.txt` 为 23 列、125 张地图。`bid_map_table`
  已兼容旧 21 列和新 23 列，保持原 `BidMap` public schema 不变。

### 工程取舍

本轮只把语义已经稳定的字段接入 `LiveObservationBatch`：地图、轮次、道具结果、
公开信息、技能/道具揭示 item shape、结算 inventory 的总格/件数/品质桶。对手出价
先只做诊断，因为结算 values 不保证按时间顺序。Fatbeans JSON 现在可通过
`bidking_lab.live.fatbeans` 离线解析，也可在 Streamlit 侧边栏导入到 live shadow。

艾莎 reveal 已从诊断信息升级为正式 live 约束：`1001034/1001033/1001032/1001031`
分别映射为白/绿/蓝/紫 bucket 的 `count + total_cells`。这意味着导入一局艾莎
Fatbeans JSON 后，白/绿/蓝/紫轮廓不再需要手填即可进入 `SessionObs`。

保留通用检查脚本 `scripts/inspect_fatbeans_capture.py` / `scripts/inspect_fatbeans_events.py`
和多份报告，后续继续用新样本验证 message id 与字段位置稳定性，再考虑把 live shadow
切为默认输入。

### 简历叙事价值

这是项目第一次把“概率推理 / OCR UI”延展到网络协议分析：用户从零开始完成抓包，
项目侧完成主连接筛选、payload 校验、应用层 frame 重组、protobuf wire 级字段探查
和事件候选表生成。这个链路适合后续写成“从黑盒网络样本到实时观测接口”的项目亮点。

---

## Checkpoint #49 — 地图似然 first cut：未知仓储不再误当 159（2026-05-28）

### 背景

艾莎/Fatbeans 路线能稳定给出白/绿/蓝/紫 bucket 的 `count + total_cells`，
分类鉴影和抽检也能给出部分 item 形状/品质/价值。但很多实时阶段还没有总仓储格数。
如果直接复用 `posterior.filter_truths_by_obs()`，`SessionObs.warehouse_capacity()`
会把未知仓储 fallback 成 `159`，从而错误地按大型仓库过滤地图样本。

### 改动

- 新增 `bidking_lab.inference.map_likelihood`：
  - `truth_matches_obs()`：只在观测里存在精确或近似仓储格数时才启用仓储过滤。
  - `summarize_map_truths()`：对单地图 MC truth 计算匹配率，并输出总格/总价值 P10/P50/P90。
  - `estimate_map_likelihood()`：对多个候选地图采样、匹配、归一化 posterior probability。
- 新增 `tests/test_map_likelihood.py`，覆盖：
  - 未知仓储时不会使用 `159` fallback。
  - 提供仓储时正常约束。
  - 单地图匹配率与分位数。
  - 两张确定性地图按 bucket 证据排序。
- Fatbeans 导入 UI 已接入地图似然诊断：
  - 导入 JSON 后展示同前缀候选地图的匹配率、后验概率、总格/价值 P10/P50/P90。
  - 使用结算总格模拟“总仓储空间”道具读数，对比加入总仓储前后的 top 后验和价值区间宽度。
  - 诊断层使用较宽探索容差 `cells±8, count±3`，避免艾莎 q1-q4 多桶精确约束在小样本 MC 下全零匹配。
- 实时出价建议 v1 已接入 Fatbeans 导入诊断：解析当前玩家最高价，并按地图似然的
  `P50/P90` 价值区间标记“防守区 / 进攻区 / 过热区”，停止价暂取 `P90 × 1.05`。
  这是只读诊断，不自动出价。
- Fatbeans JSON 导入成功后会自动打开 live canonical 输入；主出价 hint 面板已能优先使用
  本页 MC 条件后验生成实时出价建议，没有本页后验时回退到 Fatbeans 导入诊断估值。
- 出价策略已从 Streamlit UI 抽到 `bidking_lab.inference.bid_strategy`：当前不预测玩家心理价位，
  只按轮次、信息强度、仓储状态和后验样本数调整探价/防守/抢仓/停止阈值。R1 或仓储未知时
  策略会显式降级为保守，并在依据中提示“不确定性来自仓储/低信息阶段”。
- 仓储估计已抽到 `bidking_lab.inference.warehouse_estimator`：估计时会主动移除
  `warehouse_total_cells` / approximate warehouse 字段，避免把结算总格或 UI 估计反灌进结果。
  它只用地图、品质桶、道具/公开信息证据筛选 MC truth，输出跨候选地图的总格 P10/P50/P90、
  价值区间、匹配样本数、置信度和各地图贡献。
- 主出价策略现在会消费仓储估计后验：若仓储未知但后验区间窄且置信度高，可提高信息强度；
  若区间宽或无匹配，则继续保守。补信息建议加入成本意识：R1 不默认推荐总仓储空间或高品质扫描，
  优先提示宝光四鉴、抽检二这类低成本常态道具；总仓储/高价扫描只在高价值局或折扣时考虑。
- 补信息 ROI 已抽到 `bidking_lab.inference.tool_info_roi`：它从当前匹配 truth 集合出发，
  对每个候选道具模拟“使用后会看到的信号”，再按信号分组计算价值/仓储区间的期望压缩。
  首批覆盖常规扫描/估价/均格、总仓储空间、随机抽检（2）、宝光四鉴、四象/十方窥视和全库透视。
  其中宝光四鉴当前只按“品质信号”估算；全库/窥视只按“轮廓格数”估算，尚未把屏幕位置和堆叠坐标计入收益。
- UI 信息密度调整：Fatbeans 导入和主 hint 面板默认只展示决策摘要，详细地图似然、仓储明细、
  补信息 ROI 全表、inventory、轮次审计、道具结果和玩家 values 放入折叠区。已知 `map_id` 的
  Fatbeans 包默认只采样本地图，不再把同前缀 10 张地图都作为候选；默认 MC 采样从每图 1000
  降到 500，补信息 ROI 从 500 降到 250，以改善导入等待。
- 决策摘要面板新增：从现有出价建议、仓储估计和补信息 ROI 表中提取 4 行，不触发新推理：
  当前最高价是否可追、当前价值区间、当前仓储区间、下一次优先使用道具及原因。
- 本地 Fatbeans JSON 已复制到 `data/samples/fatbeans/` 供回归复用；该目录的 JSON 已加入 `.gitignore`，不提交原始抓包。

### 轮次审计

状态包顶层 `round` 字段是 1 基游戏轮次；package5 第四轮状态为 `round=4`，
用户第四轮使用道具的判断是对的。艾莎技能块内部字段不能当作展示轮次：q1 reveal
没有 inner round，q2/q3/q4 分别带 `1/2/3`。后续 UI 展示统一使用状态包顶层轮次，
技能轮次语义只按 skill id 映射品质。

### 策略含义

`总仓储空间` 在新路线里的价值上升：它不只是一个后验过滤字段，而是会直接压缩
地图似然和总价值 posterior。尤其在艾莎 R1-R3 只确认低/中品质轮廓时，总仓储能约束
剩余金/红格数，从而更早给出防守价和进攻价。若已经有完整艾莎 reveal、金/红扫描或
结算 inventory，它的边际价值会下降。

### 验证

- `python -m py_compile app/streamlit_app.py src/bidking_lab/live/fatbeans.py src/bidking_lab/inference/map_likelihood.py src/bidking_lab/inference/bid_strategy.py src/bidking_lab/inference/warehouse_estimator.py`
- `PYTHONPATH=src python -m pytest tests/test_map_likelihood.py`：`4 passed`
- `PYTHONPATH=src python -m pytest tests/test_live_fatbeans.py tests/test_map_likelihood.py tests/test_snipe.py`：`42 passed`
- `PYTHONPATH=src python -m pytest tests/test_bid_strategy.py tests/test_live_fatbeans.py tests/test_map_likelihood.py tests/test_bg_inference.py`：`28 passed`
- `PYTHONPATH=src python -m pytest tests/test_warehouse_estimator.py tests/test_map_likelihood.py tests/test_live_fatbeans.py tests/test_bid_strategy.py`：`23 passed`
- `PYTHONPATH=src python -m pytest tests/test_bid_strategy.py tests/test_warehouse_estimator.py tests/test_map_likelihood.py tests/test_live_fatbeans.py`：`24 passed`
- `PYTHONPATH=src python -m pytest tests/test_tool_info_roi.py tests/test_roi.py tests/test_bid_strategy.py tests/test_warehouse_estimator.py tests/test_live_fatbeans.py`：`28 passed`
- `PYTHONPATH=src python -m pytest -m "not slow"`：`487 passed, 13 deselected`

---

## Checkpoint #50 — 明镜之眼 + 位置校准 first cut（2026-05-29）

### 背景

用户新增两份高价值 Fatbeans 样本：

- `bidking_package12_wholebucktperspection_scan_publicinfo_basicitems_aisha.json`：艾莎局，包含宝光、抽检、全库透视、极品扫描、公开信息和最终结算。
- `bidking_package13_eye_of_clarity_ethan.json`：伊森局，只使用 `100134 明镜之眼`，用于验证“全库品质 + 伊森轮廓”是否能合并。

### 机制确认

package12 验证了艾莎与全库透视：

- `100100 全库透视` 在结算前返回 `42` 个完整轮廓，shape 面积合计 `123` 格。
- 结算 inventory 同样为 `42` 件、`123` 格，表内价值 `1,295,769`。
- 结算品质件数/格数：白 `3/6`、绿 `4/11`、蓝 `15/41`、紫 `10/27`、金 `4/15`、红 `6/23`。
- 艾莎技能块仍稳定映射为白/绿/蓝/紫累计轮廓：
  - `1001034` → 白 `3/6`
  - `1001033` → 绿 `4/11`
  - `1001032` → 蓝 `15/41`
  - `1001031` → 紫 `10/27`

package13 验证了伊森 + 明镜之眼：

- `100134 明镜之眼` 返回全库 `58` 件品质，品质件数为白/绿/蓝/紫/金/红 = `1/13/12/20/7/5`。
- 伊森 `1002082/1002083/1002084` 返回同一批 `58` 件形状，shape 面积合计 `216` 格。
- 结算 inventory 同样为 `58` 件、`216` 格，表内价值 `2,448,112`。
- 合并后的品质格数为白 `1`、绿 `37`、蓝 `29`、紫 `75`、金 `37`、红 `37`。
- 因此“R1 明镜之眼 + 伊森已知品质轮廓”可在结算前锁定全库品质 + 形状 + 总格/总件数。这个样本主要用于机制验证；由于明镜成本高，默认策略不把它当常态推荐道具。

### 代码改动

- `bidking_lab.live.fatbeans`：
  - 新增明镜品质 runtime 集合与伊森已知品质轮廓集合的匹配逻辑。
  - 当 `100134` 的 runtime ids 与伊森 `1002082/1002083/1002084` 的轮廓 runtime ids 完全一致时，结算前写入精确 `session.warehouse_total_cells` 与 `session.total_item_count`。
- `GridItemObservation`：
  - 新增 `local_index: int | None`，防止后续位置/堆叠校准丢失包内坐标。
- pytest 环境：
  - `pyproject.toml` 增加 `pythonpath = ["src"]`，裸 `pytest` 可直接导入本地包。
  - `scripts/build_map_fragment_fixes.py` 自行插入 repo `src` 路径，修复 pytest 子进程脚本导入失败。

### 位置校准结论

带 `shape_code` 的包内位置已和用户截图标注对齐，当前规则为：

```text
local_index = (行 - 1) * 10 + (列 - 1)
```

也就是 10 列、0 基左上角索引。已验证样本：

- 银丝笔筒：第 3 列、第 1-2 行 → `local_index=2`、shape `12`。
- 弹性绷带：第 9-10 列、第 4 行 → `local_index=38`、shape `21`。
- 可调式尾翼：第 3-5 列、第 10-11 行 → `local_index=92`、shape `32`。

注意：部分左上角物品的 `local_index=None` 很可能是 protobuf 默认值 `0` 未编码，
即第 1 行第 1 列。这一条还需要后续用完整顶部截图继续确认。

### 后续采样需求

下一批样本不需要再堆普通对局，优先做位置/滚动校准：

1. 使用全库透视或伊森全轮廓。
2. 同局导出 Fatbeans JSON。
3. 截仓库顶部、向下滚一屏、中部、底部。
4. 每张截图标注滚动位置。
5. 备注 3-5 个显眼物品，特别是左上角、底部附近、4x4 / 3x4 / 5x3 大物品。

目标是验证：

- `local_index=None` 是否稳定代表 `0`。
- 滚动页下 local index 是否连续。
- 屏幕行号与包内行号是否保持 `row * 10 + col`。
- 仓库底部可见物品能否转化为更强仓储下限。

### 验证

- `pytest -q tests/test_live_fatbeans.py -k "package12 or package13"`：`2 passed, 19 deselected`
- `pytest -q -m "not slow"`：`499 passed, 13 deselected`

### 2026-05-29 追加：package14-17 坐标校准

用户继续提供 4 份新样本：

- package14：艾莎，含宝光、抽检、公开信息。
- package15/16：伊森，含宝光、抽检、扫描。
- package17：伊森 + 明镜之眼，含上下滚动截图。

新增确认：

- package14：
  - 泡泡水弹：`local_index=69`、shape `11`，对应第 7 行第 10 列。
  - 章丘铁锅：`local_index=75`、shape `21`，对应第 8 行第 6 列。
  - 蓝纹奶酪：公开信息 `200050`，`local_index=94`、shape `33`，对应第 10-12 行、第 5-7 列。
- package15：
  - 印花雨伞：`local_index=100`、shape `22`，对应第 11-12 行、第 1-2 列。
  - 玛瑙棋：`local_index=23`、shape `22`，对应第 3-4 行、第 4-5 列。
  - 宝光红品 runtime 与伊森轮廓合并后：`local_index=114`、shape `22`，对应第 12-13 行、第 5-6 列。
- package16：
  - 黄唇鱼鱼胶：`local_index=85`、shape `22`，对应第 9-10 行、第 6-7 列。
  - 宗教壁画残片：伊森轮廓 `local_index=None`、shape `23`；用户截图标注为第 1-3 行、第 1-2 列，支持 `None == 0`。
- package17：
  - 满分斯诺克纪念球杆：`local_index=60`、shape `61`，对应第 7 行、第 1-6 列。
  - 赛车座椅：`local_index=105`、shape `33`，对应第 11-13 行、第 6-8 列。
  - 单兵水下推进器：`local_index=140`、shape `23`，对应第 15-17 行、第 1-2 列。
  - 智能手表：`local_index=None`、shape `11`，再次支持左上角默认值省略。

关键修正：

- 宝光/明镜这类 quality-only 结果的 `local_index` 不能直接当作形状左上角。package16 中宗教壁画残片的品质记录 local 为 `10`，但伊森轮廓 local 为 `None`，截图也表明真实左上角是第 1 行第 1 列。
- 因此坐标锚点只信带 `shape_code` 的轮廓项；品质、item_id、value 仍按 runtime id 合并。
- `GridItemObservation.local_index` 改为只保留轮廓自身 local，不再用 metadata local fallback 覆盖。

验证更新：

- `pytest -q tests/test_live_fatbeans.py -k "package12 or package13 or package14 or package15 or package16 or package17"`：`6 passed, 19 deselected`
- `pytest -q -m "not slow"`：`503 passed, 13 deselected`

### 2026-05-29 追加：坐标工具与仓储约束边界

新增 `grid_footprint(local_index, shape_key)`，统一把 Fatbeans 轮廓项转换为
1-based `row/col/width/height/bottom_row`，并接入 Fatbeans 导入诊断：

- `shape_key` 按 `width * 10 + height` 解析，例如 `33 = 3x3`、`61 = 6x1`。
- `local_index=None` 在有 shape 时按 `0` 处理，用于 protobuf 默认值省略的左上角物品。
- `SessionObs.visible_outline_bottom_row_min` 记录当前 live 轮廓证据的最深布局行，只作诊断字段。
- Fatbeans 明细表新增“轮廓坐标证据”，显示状态、品质、item、local、形状、行列范围和格数。
- Fatbeans 明细表新增“仓位证据图”：用 10 列网格把当前已确认坐标的轮廓画出来。该图是证据可视化，不是完整仓库预测；空白格只表示当前包内没有确认坐标，不能解释为真实为空。
- `live.layout` 已抽成纯模块，输出 `LayoutEvidence`：当前批次、已放置物品、最深行、已确认格数、边界空洞率、底部尾部物品数、已知/未知品质计数。Streamlit 现在消费这个结构渲染证据图；后续仓储软似然也应直接消费这个结构，不再从 UI 表格反推。

重要边界：最深行不能直接当作总格数硬约束。package17 中
`local_index=140`、shape `23` 的物品到第 17 行，但结算总格为 157，小于 `17*10=170`。
这说明 10 列布局存在空洞或排布留白。当前实现只展示“布局深度证据”，不把
`bottom_row * 10` 注入 MC 过滤，避免误杀真实样本。后续如果要使用位置增强仓储估计，
应基于多局全库样本拟合软约束，例如“最深行、已知轮廓总格、空洞率、地图类型”共同估计。

验证：

- `pytest -q tests/test_live_fatbeans.py -k "grid_footprint or package12 or package13 or package14 or package15 or package16 or package17"`：
  `8 passed, 19 deselected`
- `pytest -q -m "not slow"`：`505 passed, 13 deselected`
- 追加 `live.layout` 后：`pytest -q -m "not slow"`：`506 passed, 13 deselected`
- 追加 `live.replay` 后：`pytest -q -m "not slow"`：`510 passed, 13 deselected`
- 追加 `LayoutGridView` 后：`pytest -q -m "not slow"`：`511 passed, 13 deselected`
- 追加 `ImportOverviewSnapshot` 后：`pytest -q -m "not slow"`：`512 passed, 13 deselected`
- 追加 Fatbeans 诊断 rows runtime 化后：`pytest -q -m "not slow"`：`513 passed, 13 deselected`
- 追加 `TacticalPanelSnapshot` 后：`pytest -q -m "not slow"`：`514 passed, 13 deselected`
- 追加布局回放 rows runtime 化后：`pytest -q -m "not slow"`：`515 passed, 13 deselected`
- 追加 `LayoutEstimatePolicy` 后：`pytest -q -m "not slow"`：`516 passed, 13 deselected`
- 追加 Fatbeans layout 样本批量评估器后：`pytest -q -m "not slow"`：`518 passed, 13 deselected`
- 追加评估 summary 后：`pytest -q -m "not slow"`：`519 passed, 13 deselected`
- 追加文件名过滤与 policy 拟合输出后：`pytest -q -m "not slow"`：`521 passed, 13 deselected`

### 2026-05-29 追加：仓位证据图 View Model

`live.layout` 新增 `LayoutGridView` / `LayoutGridItemView` 与 `layout_grid_view()`：

- `LayoutEvidence` 继续表示布局证据和风险指标。
- `LayoutGridView` 表示可渲染网格：行数、列数、物品位置、label、tooltip、z-index、摘要文案。
- Streamlit 证据图现在只消费 `LayoutGridView`，不再从 `LayoutEvidence` 内部重新拼 label / tooltip。

设计决策：这一步不做新的仓库预测，只把“证据图是什么”从“如何用 HTML 画出来”里拆开。
后续做 PySide/Qt 悬浮窗或桌面小窗时，可以复用同一个 view model，用原生控件或 canvas 渲染，
而不是把 Streamlit HTML 迁过去。

### 2026-05-29 追加：JSON 回放评估 first cut

新增 `live.replay`，用于把单局 Fatbeans JSON 按状态切片，评估每个阶段的布局证据相对最终结算真值的差距：

- `final_truth_from_events(events)`：提取最终结算总格数和总件数。
- `layout_replay_stages(events)`：对每个有 `grid_items` 的阶段输出 `LayoutReplayStage`。
- 阶段字段包括：sort、round、phase、布局证据、最终总格、最终件数、已知格覆盖率、`max_row * 10` 边界误差、已知格误差。

注意：`bounding_cell_error` 不是预测误差，只是布局深度诊断。它用于观察“最深行乘 10”与最终格数的偏离，帮助后续拟合软约束。

package17 回放示例：

- sort 26 / R1：已知 66 格，最终 157 格，覆盖约 42%。
- sort 45 / R2：明镜 + 伊森后已知 157 格，覆盖 100%。
- sort 60/74：继续维持 157 格。

Streamlit Fatbeans 详细诊断已新增“布局回放评估”表。后续你只提供 JSON 时，我们可以直接看各轮证据如何收敛，以及什么类型的底部稀疏会导致估计风险上升。

### 2026-05-29 追加：布局仓储估计接口骨架

新增 `LayoutWarehouseEstimate` 与 `estimate_warehouse_from_layout()`。这是保守接口骨架，不是正式预测模型：

- 若布局已知格数覆盖最终结算格数，则标记 `locked=True`，P50/P90 均为最终格数。
- 若底部稀疏且空洞率高，则只给 `min_reasonable_cells = 已知格数`，不输出 P50/P90 点估计。
- 若底部较密，则允许给一个弱诊断点估计，但文案明确“仍需样本拟合校准”。

Streamlit 布局回放表现在显示 `布局估计` 与 `估计置信`。这一步的目标是打接口和 UI 链路，
等后续积累更多 JSON 后，把规则替换为基于样本的软似然。

### 2026-05-29 追加：布局阶段摘要

Fatbeans 导入默认区域新增“布局阶段摘要”，从完整回放中压缩出最多 4 行：

- 阶段：`R?/sort`
- 已知格、覆盖率、最深行
- 布局估计、估计置信、风险

完整 `布局回放评估` 表仍保留在详细诊断折叠项里。这样默认 UI 更接近实战视角，
同时不丢工程阶段需要的细节。

### 2026-05-29 追加：Fatbeans 实战摘要块

Fatbeans 导入默认区域进一步整理为“Fatbeans 实战摘要”：

- 决策小结
- 仓位证据图
- 布局阶段摘要
- 仓储估计摘要
- 补信息 ROI Top 3
- 实时出价建议摘要

地图似然、inventory、轮次审计、道具结果、玩家 values、完整布局回放仍保留在折叠诊断里。
这一步只调整 UI 结构，不改变推理逻辑。

### 2026-05-29 追加：Runtime Snapshot 边界

新增 `bidking_lab.runtime.TacticalSnapshot`，把默认小结面板从 Streamlit 表格里拆出来：

- `price_decision`：当前最高价是否可追。
- `value_range`：当前价值 P10/P50/P90。
- `warehouse_range`：当前仓储 P10/P50/P90 或后验文案。
- `next_tool_hint`：当前已携带/可用道具里的下一张优先使用建议。
- `layout_stages`：压缩后的布局阶段摘要。

后续补充：`tactical_summary_rows()` 也已放进 runtime 层，主 hint 面板与 Fatbeans 导入摘要
都复用同一组“四行小结”行格式。Streamlit 只做表格渲染，不再各自拼接“当前最高价 /
价值区间 / 仓储区间 / 道具建议”的文案。

再次补充：`ImportOverviewSnapshot` 也已放进 runtime 层，用于承接 Fatbeans 导入概览：
文件名、packets、frames、states、live batches、地图、轮次、结算件数、结算格数和已知战利品价值。
Streamlit 顶部导入概览表现在只消费该 snapshot，避免后续悬浮窗或桌面小窗再次手写 summary 字段映射。

同一方向继续推进：Fatbeans 明细里的本局道具动作、最新道具结果、玩家出价候选也已抽到
runtime 层。Streamlit 仍负责展示，但不再在 UI 代码里直接拼接这三类诊断行。

再进一步：`TacticalPanelSnapshot` 已把 Fatbeans 默认实战摘要块整体收口到 runtime 层，
包括四行小结、布局阶段、仓储摘要、ROI 摘要、出价摘要和布局提示文案。Streamlit 当前只负责
把该 panel 渲染成表格；后续悬浮 UI 可以直接复用同一个对象。

布局回放评估也已 runtime 化：`layout_replay_rows_from_stages()` 接收 live replay stages，
输出包含已知格、最深行、空洞率、最终覆盖、布局估计、估计置信和风险的前端无关 rows。
这让后续“布局深度 → 总格数软估计”模型可以只替换估计函数，UI 与悬浮窗展示层不需要改。

`live.layout` 新增 `LayoutEstimatePolicy`。默认仍是保守 `conservative-v0`，不会把最深行当硬下界；
但 sparse/dense 阈值和 P50 margin 已经可替换。后续 20 份伊森 + 20 份艾莎样本主要用于拟合这个
policy，而不是重写 UI。索菲/加布里每类 2 份可先做兼容性 smoke，暂不用于统计建模。

新增 `bidking_lab.live.evaluation` 和 `scripts/evaluate_fatbeans_layout_samples.py`，用于把目录里的
Fatbeans JSON 批量转成布局拟合日志。每行对应一个 layout-bearing stage，字段包括文件名、地图、
轮次、已知件/格、最深行、边界格、空洞率、底部物品数、最终总格/件数、覆盖率、边界误差、
最终格误差、当前估计区间、policy 和风险文案。脚本支持 CSV 与 JSONL，显式 UTF-8 输出。
现在也支持 `--format summary`，用于快速判断样本是否够拟合。

示例：

```powershell
python scripts\evaluate_fatbeans_layout_samples.py data\samples\fatbeans --format jsonl
python scripts\evaluate_fatbeans_layout_samples.py data\samples\fatbeans --format summary
```

当前本地 16 份样本 summary：

- files=16, rows=47, errors=0
- sparse_rows=3, dense_rows=12
- large_warehouse_files=1, max_final_total_cells=216
- fit_readiness=样本不足
- 缺口：总文件数不足 40，sparse 底部样本不足 5

### 2026-05-30 追加：48 份新样本批量评估

用户提供目录 `C:\Users\shenc\Desktop\bid_king_packages`，其中包含 48 份新命名样本：

- 伊森 20 份、艾莎 20 份、索菲 4 份、加布里 4 份。
- 别墅 24 份、沉船 24 份。
- 文件名已有 dense/sparse/big/huge/small/medium/unknown 初始备注。

评估脚本新增 `--name-regex`，避免把目录里的旧包和历史包混入新批次：

```powershell
python scripts\evaluate_fatbeans_layout_samples.py C:\Users\shenc\Desktop\bid_king_packages --format summary --name-regex "^(ethan|aisha|sophine|gabriela)_"
```

新批次 summary：

- files=48, files_with_rows=45, rows=128, errors=0
- rows_with_final_truth=128
- sparse_rows=29, dense_rows=22
- large_warehouse_files=3, max_final_total_cells=184
- mean_abs_bounding_error≈11.59
- fit_readiness=可拟合v1

缺布局 rows 的 3 份：

- `aisha_shipwreck_test_sample10_sparse_1rounds.json`
- `ethan_villa_test_sample2_dense_1rounds.json`
- `sophine_villa_test_sample1_unknown_2rounds.json`

这三份都有最终结算 inventory，可用于价值/总格真值，但缺少 shape-bearing 坐标阶段，
因此不进入布局拟合。主要原因是低轮次或英雄技能只给品质/抽样，不给完整轮廓。

`aisha_shipwreck_test_sample2_dense_3rounds.json` 的 Fatbeans 列表序号最高到 322，
但主 TCP 解析只有 67 个 packet、72 个 frame、3 个 state。判断是 Fatbeans 捕获列表里存在
非主会话/无效包序号空洞，不是业务状态异常膨胀；解析层没有缺帧。

公开信息新增观察：

- `200001` 仍稳定表示“紫色全轮廓”，已经接入 live bucket/shape 约束。
- 新批次中 `200050/200022/200023/200021/200048` 也携带 shape/local，可作为后续
  public-info item-level 轮廓扩展目标。
- `200026/200027/200028` 多数是 quality-only runtime 信息，可合并品质，但不能单独当坐标锚点。

Policy 拟合：

```powershell
python scripts\evaluate_fatbeans_layout_samples.py C:\Users\shenc\Desktop\bid_king_packages --format policy --name-regex "^(ethan|aisha|sophine|gabriela)_"
```

输出 first cut：

- dense_samples=22, medium_samples=77, sparse_samples=29
- dense_p50_margin=6
- medium_p50_margin=6
- notes=[]

当前默认保守 policy 的 P50 误差：MAE≈12.72，bias≈-12.11（偏低）。
用该样本拟合 policy 重新估算非 sparse 行：MAE≈7.81，bias≈-0.43。
但 sparse 行仍不应给强 P50 点估计，因为误差分布多峰，可能隐藏深部物品。

这个日志结构对后续版本很有价值：实时 Fatbeans 接口接入后，每局都可以自动追加同样的 rows。
我们可以用这些 logs 做三类长期优化：

- 拟合 `LayoutEstimatePolicy`，判断 sparse/dense 底部在什么条件下可靠。
- 校准补信息 ROI，比较“用了某道具前后价值/仓储区间实际压缩多少”。
- 校准出价策略，按玩家行为和最终盈亏回放防守价、抢仓上限、停止价是否过激。

设计决策：先保留 Streamlit 作为实验台，但新增前端无关 snapshot 边界。后续如果做 PySide/Qt
悬浮窗、桌面小窗、甚至“宠物式”提示 UI，只消费同一个 snapshot，不直接绑定 Streamlit HTML
结构，也不把推理逻辑搬进 UI 层。

简历价值：这把项目叙事从“做了一个网页分析器”提升到“抓包协议解析 → 状态归一化 →
概率推理 → 实时策略 snapshot → 多前端展示”的完整工程链路。技术点覆盖网络数据解析、
逆向字段校准、概率建模、状态机、可视化与前端解耦。

### 何时需要新样本

当前不需要更多样本来验证坐标公式；坐标和 UI 渲染已可继续工程化。下一次需要样本是在做
“布局深度 → 总格数软估计”时，最有价值的数据是：

- 伊森 R1 技能截图 + R2 全库透视截图 + 同局 Fatbeans JSON。
- 至少包含 1 张底部稀疏局、1 张底部较密局、1 张仓库很大的局。
- 第一批拟合量级：伊森约 20 份、艾莎约 20 份足够做 v1；索菲/加布里各 2 份只做解析兼容验证。
- 如果需要滚动，顶部/中部/底部分段截图，并备注滚动位置。
- 最终结算 JSON 已足够；最终截图只在需要核对成交价/盈亏 UI 时再补。

### 2026-05-30 追加：公开信息与地图价值分层

新增 `scripts/summarize_map_value_tiers.py`，用于从本地 `BidMap/Drop/Item` 表直接跑地图价值基线。
它只做离线报表，不影响 live shadow 或实时出价逻辑。

示例：

```powershell
python scripts\summarize_map_value_tiers.py --map 2401 --map 2501 --map 2601 --samples 1200
python scripts\summarize_map_value_tiers.py --category 105 --samples 1200 --top 12
```

当前本地 MC 观察：

- 别墅 24xx：P50 大多约 35-41 万，P90 大多约 80-95 万，红色出现率约 76-79%。
- 沉船 25xx：P50 大多约 52-63 万，P90 大多约 109-136 万，红色出现率约 90-92%。
- `2601 隐秘拍卖会` 已存在于本地地图表，且明显是超高价值图：P50≈143 万，P90≈282 万，
  红/金出现率在当前表下接近 100%。

按 2000 次 MC、P50 排序的当前推荐 Top5：

- 别墅：`2409 末日庇护所`、`2403 科学家居所`、`2406 学者居所`、`2401 未知别墅`、
  `2405 望族居所`。
- 沉船：`2503 军用舰艇保险库`、`2509 私掠船军火舱`、`2506 探险家座舰资料库`、
  `2501 未知残骸`、`2505 殖民商船宝库`。

`2601` 原始掉落池已包含 `非洲之心`、`金陵折扇`、`豪宅管理用黑盒`、`黑王子红宝石`、
`羊脂白玉籽和田玉` 等超稀有红货。当前报表按游戏表原样计算；若后续要做“玩家体验场景”
（例如暂不计入非洲之心/金陵折扇，只看黑盒/黑王子/羊脂玉等），应新增 scenario filter，
不要改原始数据表。

公开信息 ID 观察：

- `200001`：稳定作为“紫色全轮廓”使用，已接入 live bucket/shape 约束。
- `200050`：携带单个或少量 item-level shape/local，样本表现接近“显示占位格最高物品”类公开信息。
- `200022/200023/200021/200048`：也携带 shape/local，可作为后续 item-level public outline 扩展目标。
- `200026/200027/200028`：多数是 quality-only runtime 信息，可用于品质存在性/数量线索，但不能单独作为坐标锚点。

结论：`2000xxx` 可以继续靠包内结构自动归类，不需要每个编号都人工标注；人工备注主要用于确认中文语义，
例如“占位格最高”“随机显示 N 件”“显示某品质全部轮廓”。均值类公开信息也已经能读到精确小数，
但只有在样本值明显偏高、或与当前道具证据形成强约束时，才应显著影响出价建议。

代码更新：item-level 轮廓现在会转成对应品质的下界，而不是整桶总量。例如公开信息只显示
一个 3x3 蓝色物品时，live state 会生成“蓝色至少 1 件 / 9 格”。这样 `map_likelihood`
和仓储估计可以消费它，但不会把单件公开信息误当成“全部蓝色只有 1 件 / 9 格”。

鉴影/分类约束的实现边界：

- 当前 parser 已能把鉴影类结果作为“已知物品/已知轮廓/已知品质”证据进入 grid items。
- 下一步可以把 `Item.tags` 或分类字段作为软约束加入 MC：例如“已知一个能源交通类金色 4x4”
  会比单纯“金色 16 格”更窄。
- 暂不把分类约束做成硬过滤，直到确认各鉴影道具的 action id 与类别语义足够稳定；否则容易因为
  物品标签映射不完整误杀真实解。

### 2026-05-30 追加：分类鉴影软约束 v1

`100151..100159` 分类鉴影已作为软约束接入 live shadow 与 MC：

- action → Item.tags 分类码映射：
  `100151=101 家具物品`、`100152=102 医疗药品`、`100153=103 时尚潮流`、
  `100154=104 兵装军火`、`100155=105 珠宝矿藏`、`100156=106 文物古董`、
  `100157=107 数码娱乐`、`100158=108 能源交通`、`100159=109 食饮珍馐`。
- `GridItemObservation` 新增 `category`，`live_state_to_session_obs` 会把这类轮廓写入
  `SessionObs.category_items`。若同 runtime 已经通过宝光/抽检/公开信息补到品质或 item_id，
  也会一起带入分类 item observation。
- `map_likelihood` 新增 `category_observation_soft_score()`：对 truth 中的 `Item.tags + quality +
  cells + item_id` 做多重集匹配。命中给满权重，未命中只降权到 `0.35`，不做硬拒绝。
- `warehouse_estimator` 使用同一软权重计算每张候选图的 likelihood；当前总仓储分位数仍以硬匹配样本
  为主体，后续可升级为完整加权分位数。

设计边界不变：分类鉴影 v1 只影响 MC 后验权重和诊断排序，不替代已有品质桶精确约束，也不把
“某分类显示了 N 个轮廓”误解释为整局只存在 N 个该分类物品。最新回归：

```powershell
pytest -q -m "not slow"
# 530 passed, 13 deselected
```

### 2026-05-30 追加：布局 sample-fit v1 评估收口

布局样本拟合不再只输出 policy 参数，也会输出 conservative 与 fitted 的分组误差：

```powershell
python scripts\evaluate_fatbeans_layout_samples.py C:\Users\shenc\Desktop\bid_king_packages --format policy --name-regex "^(ethan|aisha|sophine|gabriela)_"
```

48 份命名样本下当前结果：

- `sample-fit-v1`: `dense_p50_margin=6`，`medium_p50_margin=6`。
- conservative 非 sparse：`rows=99, MAE≈12.72, bias≈-12.11`，整体偏低。
- sample-fit 非 sparse：`rows=99, MAE≈7.61, bias≈-0.64`，偏差基本消掉。
- dense：`MAE≈3.45, bias≈0.09`。
- medium：`MAE≈8.79, bias≈-0.84`。
- sparse：`rows=29`，继续全部跳过 P50 点估计，不输出误导性中位数。

因此 UI 的 Fatbeans 实战摘要可以优先展示 sample-fit 估计；详细诊断继续保留 conservative
与 sample-fit 两列对照，方便后续样本扩充后回看策略是否过拟合。

### 2026-05-30 追加：public-info item-level 样本扫描

对 48 份命名样本只读扫描 `200050/200022/200023/200021/200048`：

- `200050`：5 个文件、18 次事件，每次 1 件，均携带 `item_id + quality + shape/local`；
  继续像“显示单件最高/关键物品”。
- `200048`：1 个文件、5 次事件，每次 1 件，携带完整 item-level shape/local。
- `200021`：1 个文件、5 次事件，每次 2 件，携带完整 item-level shape/local。
- `200022`：3 个文件、11 次事件，每次 4 件，携带完整 item-level shape/local。
- `200023`：2 个文件、6 次事件，每次 6 件，携带完整 item-level shape/local。
- `200026/200027/200028`：分别表现为 3/6/9 件 quality-only runtime 信息，仍不作为坐标锚点。

当前可先把 `200021/200022/200023/200048/200050` 统一归为“public item-level reveal”
写入诊断/ROI 文案；是否带有“最高格/最高价值/随机 N 件”的中文语义，还需要结合截图或道具/地图提示文案确认。

### 2026-05-30 追加：live monitor 与悬浮 UI first cut

新增 `bidking_lab.live.monitor`，把 “Fatbeans capture → 推理摘要 → 长期日志” 从 Streamlit 中抽出来：

- `build_monitor_artifact_from_file/payload/events()`：生成 JSON-serializable artifact。
- `write_monitor_logs()`：写入：
  - `latest_snapshot.json`：悬浮窗/未来桌面 UI 读取的当前态。
  - `sessions.jsonl`：每次处理的完整 snapshot 回放日志。
  - `model_eval.jsonl`：最终真值存在时追加模型误差。
  - `layout_samples.jsonl`：布局拟合 rows，长期扩样用。
- `scripts/run_fatbeans_live_monitor.py`：
  - `--file some.json` 处理单个文件。
  - `--watch-dir dir` 轮询目录。
  - `--stdin` 从标准输入读一个 JSON payload，给未来实时 feed 预留接口。
- `scripts/run_live_overlay.py`：tkinter always-on-top 小窗，每秒读取 `latest_snapshot.json`。

当前 model_eval 字段包含：

- `value_p50_error`
- `warehouse_p50_error`
- `layout_fit_p50_error`
- `highest_bid`
- `attack_bid`
- `stop_bid`
- `stop_minus_final_value`

用 `ethan_shipwreck_test_sample20_dense_4rounds.json` 做 smoke：

- 最终价值 `330,282`，价值 P50 `690,878`，`value_p50_error=360,596`。
- 最终仓储 `76`，仓储 P50 `100`，`warehouse_p50_error=24`。
- layout sample-fit P50 `74`，`layout_fit_p50_error=-2`。

这说明当前布局拟合在该局表现很好，但价值/出价侧仍明显偏乐观，正好需要长期实时日志回放来校准出价策略 v2。

### 2026-05-30 追加：样本 21-25 对照与推理层风险

`C:\Users\shenc\Desktop\bid_king_packages` 新增 21-25 中，手记编号与文件名存在整体错位：

- 手记“样本 21”对应文件 `sample22_4rounds_2timesofitemreveal_3imagedetectiontools.json`：
  `200027` 给 6 件品质（三紫一红一绿一蓝），随后医疗/文物古董/数码娱乐鉴影。
- 手记“样本 22”对应文件 `sample23_4rounds_1timesofitemrevealand1qualityreveal_3imagedetectiontools.json`：
  `200022` 给 4 件完整 item-level，家具/珠宝矿藏/时尚潮流鉴影，结算前还有 `100129` 抽检 2 件。
- 手记“样本 23”对应文件 `sample24_2rounds_1timeofgoldenavgvalue_2imagedetectiontools.json`：
  `200037=28714.25`，能源交通与兵装军火鉴影。
- 手记“样本 24”对应文件 `sample25_4rounds_1timeofbiggestitemreveal1timeofgolditemnum_2imagedetectiontools.json`：
  `200050` 确认为 `碳纤维单体壳车身`，随后食饮珍馐/书画古籍鉴影，`100129` 抽检出 `木梭子`、`骨笛`。
- 文件 `sample21_2rounds_reveal_all_purpleitemscontour.json` 只看到 `200001` 全紫轮廓、宝光四鉴、抽检 2 件，像早停/残缺捕获或另一局。

字段语义边界：

- `100129` 抽检与 `200021/200022/200023/200048/200050` public item-level 都能解析出
  `item_id + quality + shape/local + cells + value`，在当前项目里可以确定具体道具，不只是位置。
- `200026/200027/200028` 仍是 quality-only runtime 信息；除非后续同 runtime 被形状源连接，否则不能当坐标锚点。
- 分类鉴影 `100151..100160` 给 `category + shape/local/runtime`，不是价格或 item_id；已补齐
  `100160 -> 110 书画古籍`，并修正同 runtime 分类信息被去重丢失的问题。

推理层风险：

- 高信息 Fatbeans 样本里，Aisha/公共信息会给大量精确桶总格/件数和形状事实；当前 MC 仍主要靠 rejection sampling，
  采样不到完全兼容组合时会出现 `0/N` 匹配。加 trials 不能根治，需要条件采样/已知 item 锚定。
- live monitor 增加了一个保守 fallback：严格匹配为 0 时，把精确桶总格/件数降级为同等下界再采样，并在证据标签标注
  “放宽精确桶约束”。这只是避免面板空白，不代表准确性保证。
- `category_observation_soft_score` 已改为支持多 tag 藏品，避免 `JK制服 [103,101]` 这类交叉分类只匹配第一个 tag。

### 2026-05-30 追加：Evidence-first v2 推理内核起步

新增 `bidking_lab.inference.v2` 作为旁路内核，不替换 v1：

- `EvidenceStore` / `RuntimeEvidence`：按 runtime/local 合并 public、action、skill 证据。
- `KnownItemAnchor`：从 `item_id` 明确的 public item-level / 抽检事实中提取必须存在的锚点。
- `ResidualProblem`：记录锚点数量、已知格、已知价值、锚点 item 计数和诊断。
- `ConditionalSampler`：每个样本先强制加入锚点，再采剩余未知部分。
- `PosteriorReport`：输出 `n_matched`、总格/总价值分位数、锚点已知价值和诊断。

第一版故意不做“同类型物品概率加权”。比如抽检出古董后提高其他古董权重，这类 bias 可能与分类鉴影、
地图权重、后续空间组合重复计权；现阶段只把分类和 item-level 作为证据保存，等有 `model_eval.jsonl`
长日志后再做校准。

新样本 smoke：

- `sample22/23/25` 可以正确抽取 6/5/3 个 known item anchors。
- `sample24` 无 item anchor，v2 以 500 trials 有 27 个匹配样本，价值 P50 约 `406,677`。
- 第二步加入 per-quality residual targets 后，同样 500 trials：
  - `sample22`：6 anchors，`167/500` 匹配，价值 P50 约 `166,432`。
  - `sample23`：5 anchors，`40/500` 匹配，价值 P50 约 `154,366`。
  - `sample24`：0 anchors，`76/500` 匹配，价值 P50 约 `214,339`。
  - `sample25`：3 anchors，`169/500` 匹配，价值 P50 约 `507,135`。

这说明 per-quality 条件采样能缓解高信息样本 `0/N` 问题；但 `sample22/23`
价值仍偏低，下一步要把 public exact item value、aggregate avg-value、layout 空间约束和地图长尾权重一起校准。

quality-only runtime 证据现在也会提升对应品质的 count floor，但不猜格子/价值：

- `sample22` 的红色 quality-only 进入 `q6 count_floor=1` 后，500 trials 下价值 P50 从约
  `166,432` 提到约 `267,831`。
- 这仍低于最终 `443,951`，说明红/金长尾价值还需要通过 exact item/空间/聚合均值进一步校准。

空间约束 v2 起步：

- `KnownFootprint` 从 `local+shape` 生成 10 列 grid footprint。
- `LayoutFeasibility` 输出 footprint count、occupied cells、bottom row、overlap/overflow diagnostics 和 soft score。
- 当前只硬拒绝样本总格/件数低于已知 footprint 的情况；overlap/overflow 先降权和诊断，不硬杀。
- 新样本 500 trials smoke：
  - `sample22`：43 footprints，96 occupied cells，bottom row 12，layout score `0.897`，`160/500` 匹配。
  - `sample23`：43 footprints，118 occupied cells，bottom row 14，layout score `0.836`，`40/500` 匹配。
  - `sample24`：10 footprints，29 occupied cells，bottom row 8，layout score `1.0`，`76/500` 匹配。
  - `sample25`：28 footprints，74 occupied cells，bottom row 8，layout score `1.0`，`169/500` 匹配。

价值约束 v2 起步：

- 已知 `item_id` 的 evidence 会形成 per-quality `value_floor`，例如 `sample25` 红品 floor `444,000`。
- `200037` 暂映射为金色品质平均价值 soft target，不直接硬过滤。
- 新样本 500 trials smoke：
  - `sample22`：记录 q2/q3/q4/q5 exact value floors，`160/500` 匹配，价值 P50 约 `267,835`。
  - `sample23`：记录 q2/q3/q4 exact value floors，`40/500` 匹配，价值 P50 约 `154,380`。
  - `sample24`：`q5 avg_value=28,714.25` 后，`71/500` 匹配，价值 P50 从约 `241,285` 提到约 `267,066`。
  - `sample25`：记录红品 exact floor `444,000`，`169/500` 匹配，价值 P50 约 `507,135`。

下一步 v2 重点不是加 trials，而是继续增强 residual target 和 posterior 权重：

- 接入 exact item value / aggregate avg-value 作为价值下界或软约束。
- 把 sample-fit layout rows 与 v2 footprint score 汇总为布局 posterior。
- 继续确认 overlap/overflow 诊断是否来自真实重叠、累计快照，还是 local 解析细节。

全目录 v2 批量评估基线：

- 新增 `scripts/evaluate_fatbeans_v2_samples.py`，默认扫描桌面
  `C:\Users\shenc\Desktop\bid_king_packages` 与项目内 `data/samples/fatbeans`，
  按文件名去重，输出 summary/jsonl/csv。
- 当前 `--trials 300` 基线：`files=69, ok=67, valued=55, zero_match=12`。
- 价值 P50 `MAE≈375,239`，P90 覆盖率约 `50.9%`。这不是可上线精度；
  主要问题是高价值长尾系统性低估。
- 按最终价值分组，`>=1.2m` 档 `n=10, zero_match=3, P50 MAE≈1,090,745,
  P90 coverage≈14.3%`；说明当前白盒掉落池 + 现有 evidence floors 仍不足以把红/金高尾推上来。
- 评估器现在输出最终品质分布和最高价值物品；55 份有后验样本里 49 份最终含 q6 红货，
  但 q6 truth 的 P90 覆盖约 `49.0%`。最坏样本 `aisha_villa_test_sample20_dense_3rounds`
  的真实主要误差来自未被证据命中的 1 格红货 `超级跑车钥匙=1,495,000`。
- Aisha 样本 P90 覆盖明显低于 Ethan；Ethan 则更多出现零匹配，说明下一步要分开处理：
  Aisha 优先校准长尾价值权重，Ethan 优先降低已知轮廓/桶约束下的 zero-match。
- 结论：v2 工程主干可继续替换旧 rejection 推理，但不能声称实战准确性有保证。
  下一步应先做分层诊断和尾部校准，再接 Bid v2 阈值。
- v2 `PosteriorReport` 已新增 `q6_match_rate` 和 `q6_value` 分位数，并在“没有 q6 证据且
  匹配样本 q6 率过低”时写入 `q6_unconstrained_low_sample_rate:*` 诊断。这个诊断不改变后验，
  只用于提醒 UI/出价层：当前 P90 可能漏掉未观测红货长尾。
- v2 `PosteriorReport` 进一步新增 `decision_value`：沿用 `simulation.robust_value`
  的 small-and-rare 规则，未明确识别的 1x1/1x2 等百万级小红货不进入实战决策价值；
  如果抽检/public item-level 已确认具体 item_id，则仍按真实价值计入。全样本 `--trials 300`
  下 raw P50 MAE 约 `375,997`，decision P50 MAE 约 `349,291`；`sample20`
  的超跑钥匙尾部从最终值里裁掉后，P50 误差从约 `-1,611,528` 缩小到约 `-116,528`。
- 分类鉴影 soft score 现在保留 `shape_key`，从“分类+格数”升级为“分类+格数+方向形状”匹配。
  这会让 3x4/4x3、3x3 等明确轮廓更准确地抬高对应候选，而不是只按面积相同就视作命中。
  当前表中示例：能源交通 4x4 主要是碳纤维单体壳车身/轻量化锂电池；医疗 3x3 是
  复苏呼吸机/超声波诊断仪；红色 3x4 是相控阵雷达/单兵外骨骼助力系统。
- `1306001` 双蟾纳宝、`1306002` 聚财金盆、`1306003..1306012` 十二生肖在当前普通地图
  `prepare_session_sampler` 可达池中均不可达；候选诊断应使用 map-reachable 口径，不能仅凭
  `items.json` 或 raw Drop 引用判断可掉落。
- 2026-05-31 用户确认普通 2x2 十二生肖活动仍剩约一周，因此临时放回
  `1306003..1306014`：这些物品是 q3、2x2、价值 `8,888`、tags `[100]`，会以很小候选质量
  注入基础 MC pool；v2、地图似然和仓库估计共用同一口径，观测到这些 item anchor 时不再报
  `anchors_not_in_flattened_pool`。`1306001`
  双蟾纳宝、`1306002` 聚财金盆和 `1306015` 御制祥云生肖盘仍保持不加入普通候选。
- v2 条件采样已消费 shape+category target：`CategoryItemObservation(item_id=None)` 会在
  residual 采样前按 category/quality/cells/shape_key 从当前地图池中抽一个匹配候选；无候选时
  诊断为 `category_target_no_pool_match:*`。新增合成 spec：
  - `data/samples/synthetic_v2/medical_3x3_q6.json`：候选为复苏呼吸机/超声波诊断仪。
  - `data/samples/synthetic_v2/weapon_3x4_q6.json`：候选为相控阵雷达/单兵外骨骼助力系统。
  - `data/samples/synthetic_v2/antique_4x4_q6.json`：候选为翡翠屏风/红木屏风。
  `python scripts\evaluate_synthetic_v2_specs.py --trials 500` 可对比 baseline 与 conditioned 后验。
- v2 bucket target 现在区分 exact 与 floor：`QualityBucketObs.total_cells/count` 进入
  `total_cells_exact/count_exact`，`total_cells_min/count_min` 和 item-level evidence 仍是 lower bound。
  exact 填充时会按剩余件数/格数过滤可行候选，尽量避免先过采样再被过滤。
- 全样本 `--trials 300` strict exact v1：`files=69, ok=67, valued=48, zero_match=19`，
  raw P50 MAE 约 `319,018`，decision P50 MAE 约 `287,858`。相比上一版，已匹配样本更准，
  但 zero-match 增多；下一步需要 posterior fallback，在 strict exact 零匹配时把 exact 降级为 floor
  并在 diagnostics 标注放宽。
- posterior fallback 已加入：strict exact 没有匹配时，自动把 exact `total_cells/count` 降级到
  `total_cells_min/count_min` 并重跑，diagnostics 写 `relaxed_exact_bucket_targets:*`。
  全样本 `--trials 300` 变为 `valued=60, zero_match=7, relaxed_exact=18`，raw P50 MAE 约
  `348,145`，decision P50 MAE 约 `324,622`。这比 strict exact 更适合实时 UI：不空窗，
  但仍保留放宽诊断。
- live monitor 已消费 v2 posterior：出价阈值主口径切到 `decision_value`，并在 `bid_rows`
  输出 raw `total_value`、`q6`/放宽诊断。runtime panel 的“当前价值区间”优先显示决策价值；
  `model_eval.jsonl` 增加 `decision_value_p50` / `decision_value_p50_error`，用于后续 bid v2 校准。
- exact bucket 组合采样已从“逐件随机补到不越界”升级为“先求件数+格数可达组合，再按权重抽取路径”。
  这主要解决 `count` 与 `total_cells` 同时 exact 时，贪心随机采样容易走进不可达剩余状态的问题。
  全样本 `--trials 300` 变为 `valued=62, zero_match=5, relaxed_exact=11`；相对 fallback 版
  `valued=60, zero_match=7, relaxed_exact=18`，strict 命中明显改善。当前代价是 P50 价值误差波动：
  raw P50 MAE 约 `372,111`，decision P50 MAE 约 `349,166`。误差仍主要集中在缺少明确红货证据的
  高价值局，因此下一步不应继续只调 exact sampler，而应强化 q6 residual / shape-category / layout posterior。
- 分类/形状 target 的采样顺序已前移到 bucket target 之前。这样 `q6 exact 1 件 12 格` 与
  `武器 3x4` 这类证据会先把 3x4 候选作为已存在物品，再让 exact bucket 填剩余量，避免先填桶、
  后追加分类候选造成过采样。全样本 `--trials 300` 的 `relaxed_exact` 进一步降到 `9`，
  `zero_match` 维持 `5`，decision P50 MAE 约 `350,073`。
- layout footprint count 现在也会作为 v2 `total_draws` 的下限之一，而不是只在
  `layout_feasibility_score` 里事后过滤。全样本 `--trials 300`：`valued=61, zero_match=6,
  relaxed_exact=6`，raw P50 MAE 约 `367,910`，decision P50 MAE 约 `343,503`，P90 覆盖约
  `60.7%`。这降低了 fallback 与价值误差，但多出 1 个 zero-match，说明 Ethan 高约束样本里的
  overlap/重复 footprint 需要可信度分层，不能永远当作同等硬数量证据。
- v2 批评估器新增校准诊断：
  - `q6_false_low_risk=5`：真实有 q6，但后验 q6 出现率低于 10%。
  - `q6_p90_misses_truth=21`：真实有 q6，但 q6 P90 仍低于最终 q6 价值。
  - `layout_conflict=40`，且 6 个 zero-match 全部带 layout conflict。
  - `zero_match_after_relax=5`：exact fallback 后仍无解，说明问题不只在 exact 上界。
  这些计数会比单个 MAE 更适合后续实时日志校准；当前样本足够支撑工程方向判断，但不够支撑激进调参。
- live monitor 目录轮询已增强为长期采样入口：
  - `--stable-seconds` 等待 Fatbeans JSON 写稳定，避免半截文件。
  - `processed_files.json` 记录 path/size/mtime，重启后不重复写日志；`--reprocess` 可强制重跑。
  - `--ignore-existing` 可在启动时把现有 JSON 标记为已处理；`start_live_monitor_overlay.ps1`
    默认启用它，只处理启动后的新文件。需要回放旧文件时传 `-ProcessExisting`。
  - watch 模式默认写 `monitor.lock`，避免多个隐藏 monitor 同时写同一个 log dir 导致重复日志；
    异常退出后如锁文件残留，可手动删除 `data/logs/live/monitor.lock`。
  - `scripts/stop_live_monitor.ps1` 可停止后台 monitor 并清理 lock，适合测试前重置监听状态。
  - 默认把处理过的原始 JSON 复制到 `data/logs/live/raw/`，后续可回放或批评估。
  - `scripts/start_live_monitor_overlay.ps1` 透传 `StableSeconds`，可在游戏前先启动监控和悬浮窗。
- live `model_eval.jsonl` 已补充后续校准必需字段：`hero`、q5/q6 结算 count/cells/value、
  `v2_q6_match_rate`、`v2_q6_value_p90`、`q6_false_low_risk`、`q6_p90_misses_truth`、
  `relaxed_exact_used`、`layout_conflict`、`posterior_diagnostics`。新增
  `scripts/summarize_live_model_eval.py` 可直接汇总 live 日志；旧日志缺少这些字段时会按空值处理。
  汇总默认按 `file` 保留最新记录，今晚多 monitor 进程造成的重复行会自动折叠；当前日志
  `raw_rows=140`、去重后 `rows=71`。
- `summarize_live_model_eval.py` 现在输出 `collection_readiness` 和 `log_quality`：按
  Aisha/Ethan × villa/shipwreck 统计有效结算局数量、距离每桶 30 局目标的缺口，并统计缺 hero、
  缺 decision value、缺 q6 真值等日志质量问题。当前去重日志按 30 局目标还差 51 局。
- 新增 `docs/live_sampling_guide.zh-CN.md`，沉淀采样启动顺序、文件命名、优先采样桶和诊断字段。
- `scripts/run_live_overlay.py` 已从纯文本摘要扩展为风险高亮面板：header 显示 hero/map/round/结算价值，
  主体显示战术摘要、q6 样本率/价值区间、后验诊断、布局阶段和回测误差；q6 明显低估用红色，
  q6 P90 漏真值、layout conflict、exact fallback 用黄色。若 snapshot 超过 120 秒未更新，
  面板会提示检查 Fatbeans 导出或 monitor 进程，减少“看起来没动”的误判。
- 2026-05-31 新增样本检查：
  - `C:\Users\shenc\Desktop\bid_king_packages` 中最近新增 Ethan villa/shipwreck 与 Aisha shipwreck
    样本均已进入 `processed_files.json`；当前源目录 + 项目 copy 共 174 个唯一 JSON，批评估
    `ok=168, valued=158`。
  - Fatbeans 解析层统计到 170 个可解析文件、4 个坏包：`aisha_villa_test_sample26..29` 报
    `SEND invalid frame length`，后续如需使用应重新导出。
  - 鉴影 action 覆盖：家具 6、医疗 3、时尚 3、武器 1、矿物 3、古董 2、数码 3、能源 3、
    饮食 5、书画 4；文件名备注中的 Ethan 三把鉴影已能从 action id 读到。
  - q3 5x4 在普通掉落池中唯一对应 `1103005 墙面涂鸦墙`，q5 6x3 唯一对应
    `1085009 单人郊游快艇`；v2 已把这类 quality+shape 唯一证据升级为 hard anchor。
    q6 4x4、q6 3x4、q6 3x3 仍非唯一，只能作为条件采样/软约束。
  - `100124` 优品估价出现 40 次，`100112` 优品均格目前仅 1 次；v2 已把估价类 `value_sum`
    从单纯下界改为 exact-ish 软评分，过高样本降权。
  - `summarize_live_model_eval.py` 的 bid_gap 统计支持用户观察：去重 live log 下 Ethan
    最高价/结算中位比约 1.169，Aisha 约 1.013；沉船约 1.154，别墅约 1.013。
- 2026-05-31 PowerShell/monitor 进程检查：当前只有一个 `run_fatbeans_live_monitor.py`
  进程在监听桌面 JSON 目录，PID 与 `monitor.lock` 一致；未发现正在运行的 `run_live_overlay.py`。
  闪窗更可能来自重复运行 start 脚本时 overlay 用 `python.exe` 打开控制台或 monitor 因 lock 退出。
  已将 start 脚本改为幂等复用已有 monitor，并用 `pythonw.exe` 启动 overlay；stop 脚本同步停止 overlay。
- `evaluate_fatbeans_v2_samples.py` 也已输出 bid_gap，因此可以用当前代码直接重扫源 JSON 判断出价激进度。
  174 份源 JSON、`--trials 50` 快速验证下：Ethan 最高价/结算中位比约 1.169，Aisha 约 1.026；
  shipwreck 约 1.113，villa 约 1.047。
- 采样缺口统计已统一地图族口径：批评估和 live 汇总都按 `map_id` 归类，240x/340x/440x
  为 villa，250x/350x/450x 为 shipwreck，2601 为 hidden。源 JSON 174 份、`--trials 30`
  快速扫下：Aisha villa 52、Aisha shipwreck 53、Ethan villa 38、Ethan shipwreck 25、
  hidden 0；因此短期优先级是 Ethan shipwreck 补约 5 份，hidden 先每英雄 10 份冷启动，
  别墅暂时不是主要缺口。
- 2026-05-31 下午新增源 JSON 已复制到本地 `data/samples/fatbeans/`（gitignored），
  源目录当前 194 份唯一 JSON，解析 `ok=188`，仍有 4 个坏包为
  `aisha_villa_test_sample26..29`。主要桶已够：Aisha shipwreck 61、Ethan shipwreck 37、
  Aisha villa 52、Ethan villa 38；除 hidden 外不再被样本数卡住。
- public-info 语义新增硬约束：
  - `200048`：显示最高品质物品。当前可验证 22 条，观测物品质量均等于最终最高质量；
    v2 现在写入 `public_max_quality:*`，过滤更高品质样本。
  - `200050`：显示最大占格物品。58 条中观测物品格数均等于最终单件最大格数；
    v2 现在写入 `public_max_item_cells:*`，过滤包含更大单件 footprint 的样本。
  - `200021/200022/200023` 等随机展示 2/4/6 件 item-level 信息已通过已知 item/quality/shape
    进入 anchor、bucket floor 和 layout footprint；不会额外把它们的均格 `value` 当整局约束。
  - 总件数/总格数目前主要来自全库透视、明镜+伊森全轮廓、结算 inventory 等完整轮廓路径；
    未确认语义的 public numeric 暂不硬写全局总量。
- `evaluate_fatbeans_v2_samples.py` 新增 q6/zero-match 分层诊断：
  - 每行输出 `v2_q6_value_p90_error`、`v2_q6_value_p90_under_by`、`anchor_band`、
    `q6_top_size_band`、`public_constraint_key`、`zero_match_root`、`q6_miss_root`。
  - summary 新增 `q6_value_p90_coverage`、`zero_match_root_causes`、
    `q6_miss_root_causes`、`q6_calibration_priority`、`q6_risk_groups`。
  - 194 份唯一 JSON、`--trials 80` 快速扫：`ok=188`、`valued=175`、
    `zero_match=13`、`relaxed_exact=22`、`layout_conflict=84`、
    `q6_false_low_risk=14`、`q6_p90_misses_truth=77`、`q6_value_p90_coverage≈51.3%`、
    `decision_value_mae≈40.4万`、`value_p90_coverage≈46.3%`。
  - q6 优先级排序：Aisha shipwreck 最重（56 个 q6 truth、34 个 q6 P90 miss），
    其次 Aisha villa、Ethan villa、Ethan shipwreck。zero-match root 主要是
    `q3_exact_cells`、`relaxed_exact_fallback`、`layout_conflict`、`q4_exact_value`。
  - 当前结论：下一步不应单纯增加 trials 或全局抬红货权重；应分别处理
    Aisha q6 residual、Ethan exact bucket 可达性、layout footprint 可信度分层。
- v2 layout / exact-bucket 小步优化：
  - `LayoutFeasibility` 新增 `trusted_footprint_count` 和 `footprint_count_relaxed:*` 诊断，用来记录
    overlap/overflow 时理论上可降级的 footprint 数量；当前不让它影响 `draw_min`，因为 194 份样本
    试跑显示直接扣硬件数没有降低 zero-match，且 q6 覆盖略降。
  - `ConditionalSampler` 新增 cells-only exact bucket 组合采样：当只有 `total_cells_exact`
    而没有 `count_exact` 时，先用 DP 检查可达格数组合并采样，而不是完全依赖后续随机 while。
  - 194 份唯一 JSON、`--trials 80` 快速扫：`relaxed_exact` 从 22 降到 19，`zero_match` 维持 13，
    `decision_value_mae≈40.4万` 基本不变；说明 Ethan exact bucket 可达性有改善，但 q6 低估仍需
    后续 residual/形状条件采样专门处理。
- `decision_value` 口径扩展为 plannable value：
  - raw `total_value` 不变，仍保留超级跑车钥匙、永乐大典残本、相控阵雷达等百万级尾部作为上界风险。
  - `decision_value_for_truth` 现在裁掉未被 exact anchor 或 shape+category target 支持的百万级尾部；
    批评估的 `final_decision_value` 同步使用该口径。
  - 194 份唯一 JSON、`--trials 80` 快速扫：整体 `decision_value_mae≈39.4万`，高价值档
    `decision_value_mae≈80.0万`。相比旧口径不是大幅调参，而是把“常规可规划价值”和 raw 结算尾部拆清楚。
- 非唯一 quality+shape 证据已接入 v2 条件采样：
  - 新增 `ShapeTarget`，把没有 item_id、没有分类标签、但有 quality+shape/cells 的证据转成“至少存在一个同形状物品”。
  - 唯一 quality+shape 仍升级为 `KnownItemAnchor`；shape+category 鉴影仍走 `CategoryItemObservation`，
    避免同一证据重复采样。
  - 194 份唯一 JSON、`--trials 80` 快速扫：`ok=188`、`valued=177`、`zero_match=11`、
    `relaxed_exact=18`、`layout_conflict=84`、`q6_false_low_risk=16`、`q6_p90_misses_truth=77`、
    `q6_value_p90_coverage≈51.9%`、`decision_value_mae≈38.9万`。
  - 改动改善了形状约束可达性和总体 decision MAE，但没有解决 q6 P90 低估；Aisha shipwreck 仍是
    q6 residual 的第一优先级。
- q6 样本率已改成 evidence-weighted：
  - `report.q6_match_rate` 现在按分类、布局、估价、public 上界后的样本权重计算，而不是简单命中数。
  - 194 份唯一 JSON、`--trials 80` 快速扫下，覆盖与 MAE 不变；变化体现在单局 q6 样本率更贴近有效后验，
    例如部分 Ethan/Aisha 高约束样本的 q6 rate 会因权重略调。
  - 该改动只修正诊断/UI 口径，不直接抬高 q6 P90；后续 q6 residual 仍需单独设计。
- q6 Drop 先验对照已接入：
  - `QualityDropPrior` 直接使用 `Drop.txt` 的多层权重、地图子池权重、每局件数范围和掉落数量区间，
    计算指定品质在原始掉落模型下的每局出现率与期望价值。
  - live monitor 的 v2 行新增 `q6掉落先验` 和 `q6先验价值`，`model_eval.jsonl` / 批评估新增
    `v2_q6_prior_match_rate` 与 `v2_q6_prior_expected_value`。
  - `q6_below_drop_prior` 已作为结构化布尔字段进入 live `model_eval.jsonl` 和批评估行，
    `summarize_live_model_eval.py` 会直接统计 `q6_below_drop_prior_count`。
  - 194 份唯一 JSON、`--trials 80` 快速扫：总体 `zero_match=11`、`relaxed_exact=18`、
    `q6_value_p90_coverage≈51.9%` 不变；新增归因 `below_drop_prior=29`，说明 q6 低估里有一批不是
    Drop 爆率低，而是 evidence/layout/value 过滤后 residual q6 被压得过低。
  - 该诊断支持下一步做 q6 residual floor / 分层校准，但当前仍不直接改变出价口径。
- 2026-06-01 新增 Aisha imaging 样本 30 份：
  - villa 15 份、shipwreck 15 份；`--trials 40` 批评估全部解析成功，`zero_match=0`。
  - 修正多鉴影交集 target 后，30/30 有 category target，27/30 有 negative category，
    合计 `target_total=511`、`exclusion_total=739`；`category_target_no_pool_match=0`。
  - 按可见轮次覆盖分层：`early_1_2=7`、`mid_3_4=19`、`full_5=4`；
    其中 23 份可进入中后期稳定校准，7 份短轮样本保留用于早期实时提示与解析验证。
  - 30 份快速评估：`decision_value_mae≈37.1万`，中后期校准子集
    `calibration_decision_value_mae≈36.4万`，`value_p90_coverage=0.40`。
    q6 P90 低估仍存在：`q6_p90_misses_truth=16`，villa 与 shipwreck 都需要后续 residual 优化。
  - villa imaging sample15 的 public info `200032=96897.6640625` 已确认是
    “随机 6 件藏品平均价值约为 96897.66”；当前结构化保留，不作为全库或品质桶硬约束。
  - 全量 271 份唯一 Fatbeans JSON、`--trials 40` 快速扫：`ok=264`、`valued=255`、
    `zero_match=9`、`decision_value_mae≈39.3万`、`regular_decision_value_mae≈39.8万`、
    `q6_p90_misses_truth=117`、`q6_value_p90_coverage≈48.5%`；带分类证据行 38 份，
    其中 32 份有反排，`category_target_no_pool_match=0`。
- 外部参考项目 `src/grid_view_v1.3.7/` 只读初查：
  - 当前目录由 `grid_view.exe`、configs 和预计算 data 构成，没有可直接审查的源码；暂不纳入 git。
  - 可参考结构包括：按地图拆分 pricing override、`infer_vacant_rect_phantoms` 空矩形未知物品估计、
    `tier_combo_presolve_q456.json` 品质组合预计算、`map_quality_p50_out.csv` 品质分位、
    `drop_table_weights.csv` 掉落权重和 `board_snapshot.json` 实时快照输出。
  - 这些结构和我们的 layout posterior、remaining-space feasibility、ConditionalSampler 提速、
    overlay snapshot 有交集；后续按需对照，不直接复制其参数或自动点击逻辑。
- 2026-06-01 q6 target 内部价值倾斜与 public random avg 扩展：
  - 外部参考项目 `Skill_export.csv` 明确 `200031/200032/200033/200034` 为随机
    3/6/9/12 件藏品平均价值；v2 已把四者都保留为 `random_sample_avg_values` 软证据，
    仍不作为全库均价或品质桶硬过滤。其中 200032 已由 sample15 复核，200033 已由旧样本复核。
  - `ShapeTarget` / `CategoryItemObservation` 明确 `quality=6` 时，target 候选内部增加保守
    value tilt；非 q6 和无 target 的 residual 采样不变，因此不会全局抬红货概率。
  - 全量 271 份、`--trials 40` 快速扫：`ok=264`、`valued=255`、`zero_match=9`、
    `decision_value_mae≈39.2万`、`regular_decision_value_mae≈39.7万`、
    `q6_p90_misses_truth=115`、`q6_value_p90_coverage≈49.3%`。
  - `--q6-residual-floor-ratio 0.5` 离线 what-if：eligible 44 行，其中无 q6 真值 13 行，
    q6 覆盖仅升到约 51.1%；当前不适合直接把 floor 写入正式估价，后续应做分英雄/地图族、
    分证据类型的 residual 校准或风险上界提示。
  - floor what-if 现在输出分组明细；`floor_ratio=0.5` 下只有 Aisha shipwreck 有实质改善：
    q6 miss 从 54 降到 50，但同组也有 3 个无 q6 eligible。Ethan/villa 组几乎没有改善，
    因此不应做全局 floor，最多后续尝试 Aisha shipwreck 专门风险提示或更细证据门控。
- 2026-06-01 overlay 鉴影数据契约：
  - live snapshot 新增 `category_grid_items`，从最新带 grid 的 batch 中提取带 category 的
    local/shape/quality/row/col 数据。
  - `run_live_overlay.py` demo 与 model 已显示“鉴影命中”摘要；当前仍是文本摘要，不是可点击 minimap。
    后续桌面小窗或 Streamlit 可以直接用 `category_grid_items` 做按鉴影类别筛选/高亮。
- 2026-06-01 q4/q5/q6 组合预计算：
  - 新增 `quality_combo_presolve_for_map()` 和 `scripts/build_quality_combo_presolve.py`，用本项目
    Drop/Item/BidMap 表生成每个 map 的 q4/q5/q6 `count -> reachable total_cells`。
  - 本地全量 125 张地图、`--max-count 40` 生成约 15.7MB JSON，耗时约 5 秒；适合做本地缓存，
    暂不把缓存文件作为必须提交物。
  - 当前只提供 `is_quality_combo_reachable()` 查询函数，后续先接 batch 诊断，再决定是否进入
    `ConditionalSampler` exact bucket 快路径。
  - batch evaluator 已接 `presolve_unreachable_exact_buckets`。271 份、`--trials 20` 快速扫下
    unreachable exact bucket 为 0，说明当前 `relaxed_exact` / `zero_match` 主因不是 q4/q5/q6
    count/cells 数学不可达，而更可能是 sampler 命中率、layout/value 过滤、证据时序或低品质桶约束。
- 2026-06-01 q6 可规划口径拆分：
  - posterior 现在输出 `q6_decision_value`；batch evaluator 同时记录 raw `final_q6_value` 和裁尾后的
    `final_q6_decision_value`。`final_q6_trimmed_tail_value` 用于把未被证据确认的百万级红货视为
    ceiling/risk，而不是常规出价主线。
  - 全量 271 份唯一 Fatbeans JSON、`--trials 40` 快速扫：`q6_truth_files=227`、
    `q6_p90_misses_truth=115`、`q6_value_p90_coverage≈49.3%`；可规划口径下
    `q6_plannable_truth_files=224`、`q6_plannable_p90_misses_truth=116`、
    `q6_plannable_value_p90_coverage≈48.2%`。
  - q6 尾部事件 13 份，裁掉的 q6 尾部中位值约 `123.7万`。这说明黑天鹅尾部确实会污染 raw
    coverage；但改用 `q6_decision_value` 后，可规划 q6 本身仍偏低，Aisha shipwreck 仍是第一优先级。
  - `q6_plannable_calibration_priority` 当前排序：Aisha shipwreck miss rate 约 `68.4%`，
    Aisha villa 约 `47.3%`，Ethan shipwreck 约 `39.6%`，Ethan villa 约 `37.5%`。
    后续应按该分层做 residual/条件采样优化，不做全局红货抬权。
- 2026-06-01 外部 grid_view 数据对照：
  - 新增 `scripts/compare_grid_view_reference.py`，读取外部 `map_quality_p50_out.csv` 并用本项目
    Drop/Item/BidMap 同口径计算 quality draw probability、p50 price per item、p50 price per cell。
  - 2401/4401 villa：q5 `0.1000` vs `0.1010`，q6 `0.0499` vs `0.0504`；p50/item 完全一致，
    q6 p50/cell 只差约 `75`。
  - 2501/4501 shipwreck：q5 `0.1251` vs `0.1263`，q6 `0.0729` vs `0.0736`；p50/item 完全一致，
    q6 p50/cell 只差约 `75`。
  - 2601 hidden：q5/q6 probability 差约 `0.002`，p50/item 差约 `760/1658`；属于小差异，
    不构成“外部项目有另一套基础爆率”的证据。
  - 外部 pricing override 值得参考的是 `infer_vacant_rect_phantoms=true`、沉船/别墅分地图出价比例和
    q56 空位单元价配置；这些更像 UI/策略层启发，不应直接覆盖当前 q6 posterior。
- 2026-06-01 q6 可规划低估根因继续拆分：
  - batch evaluator 新增 `q6_plannable_miss_root` 与 `q6_plannable_miss_root_causes`，把“红货没采到”
    和“红货采到了但价值/件数组合偏低”分开。
  - 271 份、`--trials 20` 快速扫中，可规划 q6 低估根因前列为：
    `low_q6_value_distribution=56`、`mixed_q6_sample_value=44`、`layout_conflict=44`、
    `below_drop_prior=35`。这说明下一步不能只提高 q6 出现率；还要处理 q6 value distribution、
    layout footprint 可信度和剩余空间/件数组合。
  - Aisha shipwreck 仍是第一优先级：`q6_plannable_truth=79`、miss `57`、
    miss rate 约 `72.2%`、median under-by 约 `35.1万`。其中不少样本 `q6_match_rate=1.0`
    但 `q6_decision_value_p90` 仍低，说明应该优先做 shape/category/space 条件采样和剩余 q6
    件数组合，而不是全局红货概率 floor。

---

> **项目全局进度与路线图已迁移至 [`PROGRESS.md`](PROGRESS.md)**。  
> 本文件专注于每个 checkpoint 的技术细节。
