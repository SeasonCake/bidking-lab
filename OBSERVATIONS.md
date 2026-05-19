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

> **项目全局进度与路线图已迁移至 [`PROGRESS.md`](PROGRESS.md)**。  
> 本文件专注于每个 checkpoint 的技术细节。
