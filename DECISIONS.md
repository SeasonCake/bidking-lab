# bidking-lab · 决策记录

> 本文件记录项目推进中的工程/建模决策：背景、推荐方案、用户选择、取舍和后续复查点。
> 详细实验数据仍放在 `OBSERVATIONS.md`，总体路线仍放在 `PROGRESS.md`。

---

## 2026-05-30 · v2 推理主干采用 evidence-first 渐进替换

**背景**：Fatbeans JSON 已能提供 runtime/local/item_id/shape/category 等高信息证据，旧 MC 主要靠全局采样后过滤，容易在高信息局出现零匹配或无法表达“已知 item 必须存在”。

**推荐**：不一次性重写全部实时链路，先旁路新增 v2：`EvidenceStore`、`KnownItemAnchor`、`ResidualProblem`、`ConditionalSampler`、`PosteriorReport`。

**用户选择**：认可逐步更换主干，先保存工程 checkpoint，再继续增强约束。

**取舍**：v1 保留作为对照；v2 优先表达证据结构，不立即承诺实战精度。

**复查点**：当 v2 批量评估稳定优于 v1 后，再切换主出价策略默认输入。

## 2026-05-30 · 极端小红货不进入常规实战决策价值

**背景**：批量评估显示部分极端误差来自未被证据命中的 1x1/1x2 百万级红货，例如超跑钥匙。这类物品低概率且形状混杂，若强行推高后验，会让常规出价偏移。

**推荐**：保留 raw `total_value` 作为真实价值后验和风险诊断；新增 `decision_value` 作为实战推荐价值，裁掉未明确识别的 small-and-rare 极端尾部。若抽检或 public item-level 已确认具体 `item_id`，仍计入真实价值。

**用户选择**：认可降低极端低概率物品影响，不把非洲之心、折扇、超跑钥匙等作为常规规划基础。

**取舍**：常规建议更稳健，但如果真实出了极端小红货，`decision_value` 会低于结算真值；这应作为“不可规划收益”，而不是模型错误强行校准。

**复查点**：当实时日志足够多后，检查 `decision_value` 是否更贴近玩家可行动收益。

## 2026-05-30 · 大形状/分类明确的高价值红货不裁尾

**背景**：4x4 屏风/车身、3x4 雷达、3x3 医疗设备等候选能被形状和分类明显收窄，和 1x1 极端红货不同。

**推荐**：不全局压低红货；对 shape+category 明确的证据进入条件采样，提高符合候选被采到的概率。

**用户选择**：认可对 4x4、3x4、3x3 等明确形状做更积极的候选权重。

**取舍**：条件采样会让相关证据影响更强，因此必须保留 `category_target_no_pool_match` 诊断，避免错误分类或不可掉落物品污染后验。

**复查点**：用合成规格和真实 Fatbeans 样本分别评估医疗 3x3、古董/家具 4x4、武器 3x4 对后验的影响。

## 2026-05-30 · 活动兑换物品不作为普通地图候选

**背景**：`1306001` 双蟾纳宝、`1306002` 聚财金盆、`1306003..1306014` 十二生肖类物品会出现在 Item/部分 Drop 条目或活动数据中，但普通地图采样链路不可达。

**推荐**：候选诊断和合成样本默认使用“map-reachable”物品集合，而不是全 Item 表或 raw Drop 引用集合。

**用户选择**：明确要求这些活动兑换/不可掉落物品不加入常规候选。

**取舍**：避免把活动藏品误判为拍卖可出；如果未来活动地图真实接入，需要按地图池重新验证可达性。

**复查点**：若新活动地图上线，重新跑 map-reachable 检查，而不是凭 item_id 前缀永久排除。

## 2026-05-30 · exact bucket 上界先进入 v2 条件采样，但需要回退层

**背景**：`QualityBucketObs.total_cells/count` 在旧过滤层已经按 exact 检查，但 v2 条件采样阶段之前只把它们当 floor 填充，导致先过采样再被过滤，浪费 trials。

**推荐**：把 `total_cells/count` 拆成 `total_cells_exact/count_exact`，`total_cells_min/count_min` 继续作为 lower bound。条件采样填 exact 桶时，只在不越过剩余件数/格数的候选里抽样。

**用户选择**：认可逐步把可信上界接入，而不是所有证据都只按下界处理。

**取舍**：strict exact 让已匹配样本的决策价值误差下降，但 zero-match 变多；这是采样器表达力还不够，而不是 exact 语义错误。

**更新**：已增加 “strict exact 零匹配时降级为 floor” 的 posterior fallback，并在报告里用 `relaxed_exact_bucket_targets:*` 标明哪些约束被放宽。

**更新**：已加入 exact 桶组合采样：当同一品质同时有 exact 件数和 exact 格数时，先求可达组合再采样，降低走进不可达剩余状态的概率。69 份样本 `--trials 300` 下 `relaxed_exact` 从 18 降到 11，`zero_match` 从 7 降到 5。

**更新**：分类/形状 target 现在先于 bucket target 采样，让已知类别轮廓计入 exact 桶已占用量。69 份样本 `--trials 300` 下 `relaxed_exact` 进一步降到 9。

**更新**：layout footprint count 现在会前移为 total draws 下限，减少已知轮廓很多时的无效样本。69 份样本 `--trials 300` 下 `relaxed_exact` 降到 6，decision P50 MAE 约 34.4 万；代价是 `zero_match` 从 5 升到 6。

**复查点**：fallback 使用率已下降；下一轮重点转向 q6 residual、shape-category 条件采样和 layout posterior。layout overlap/重复 footprint 要做可信度分层，避免 Ethan 高约束局被过硬过滤。

## 2026-05-30 · 实时出价主口径切到 decision_value

**背景**：raw `total_value` 保留真实结算价值风险，但会被超低概率小红货和不可规划尾部影响。用户实际出价更需要“当前证据下可行动的稳健价值”。

**推荐**：monitor/bid hint 的主阈值使用 v2 `decision_value`；raw `total_value` 保留在诊断字段中，用来提示爆尾风险。

**用户选择**：认可 UI/出价主显示切到 `decision_value`，同时保留 raw 后验和放宽诊断。

**取舍**：常规追价更稳健；如果真实出了未确认极端尾部，主建议不会为了它追高，但 raw 诊断仍能看到风险。

**复查点**：后续用 `model_eval.jsonl` 同时评估 `decision_value_p50_error` 与 raw `value_p50_error`，再决定 bid v2 阈值。

## 2026-05-30 · 样本规模先服务工程诊断，实时日志再服务校准

**背景**：当前 69 份 Fatbeans 样本已经能暴露主要瓶颈：q6 高价值漏估、layout conflict、fallback 后零匹配。但这些样本覆盖仍偏手工、偏高信息局，不适合直接拟合激进权重。

**推荐**：现阶段用现有样本做工程回归和失败分类；不要为了追 MAE 手动抬高红货概率。等实时/半实时日志持续写入 `model_eval.jsonl` 后，再按英雄、地图族、轮次、证据类型分层校准 q6 residual、layout posterior 和 bid v2 阈值。

**用户选择**：继续推进可用主干，同时考虑后续实时日志自动收集。

**取舍**：短期精度不会靠少量样本硬拟合；长期可避免把手工样本偏差写进实战策略。

**复查点**：当 `model_eval.jsonl` 累积到每个主要英雄/地图族至少 30 份有效结算局，再开始做参数化校准。
