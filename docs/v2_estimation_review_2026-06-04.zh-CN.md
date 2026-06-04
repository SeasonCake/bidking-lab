# v2 估值审查与未来 v3 输入

日期：2026-06-04

本文档用于固定当前估值问题、评估窗口合同、v2 继续修复边界和未来 v3 的重构输入。它不是 v3
启动决定；当前正式主线仍是 v2 live/pre-bid 准确性，所有不确定改动先走离线或 shadow。

## 1. 五个评估窗口的合同

正式实战准确性评估以每轮玩家报价前的最后状态为准，总共最多 5 个窗口：

| 窗口 | 精确定义 |
|---|---|
| R1 | 第 1 次用户 `SEND 0x0022` 报价之前的全部已收到状态 |
| R2 | 第 2 次用户报价之前，包含 R1 后新增信息和已返回的本轮道具结果 |
| R3 | 第 3 次用户报价之前，包含此前累计证据和本轮道具结果 |
| R4 | 第 4 次用户报价之前，包含此前累计证据和本轮道具结果 |
| R5 | 第 5 次用户报价之前，包含此前累计证据和本轮道具结果 |

窗口重放只使用 `sort_id < 当前 bid sort_id` 的事件，不包含本次报价本身。若本轮发出了道具
`SEND 0x0026`，只有对应状态结果已经在报价前返回，窗口才算 ready。提前结束的局只评估真实存在的窗口，
不虚构 R4/R5；报价前没有任何状态或没有估值的窗口计入采集质量缺口，不计入模型准确率。

字段语义：

- `observed_round`：协议里已经完成/揭示的轮次。
- `action_round` / `eval_window_round`：玩家即将报价的轮次，正式五轮评估按它分组。
- `window_ready_for_accuracy`：有报价前状态、有估值、道具结果已返回、轮次没有冲突。
- `final_decision_value`：正式裁尾 plannable truth，仍是正式出价链路的口径。
- `final_decision_value_with_tail_replacement`：主评估 truth；未被证据支持的 q6 极端尾部不按 raw 原值计入，
  而是按当前地图池权重的同品质同形状普通红 P50 替代，缺权重时退回 Item 表中位。
- `final_value`：原始结算总值，只用于 raw ceiling/tail 审计。

2026-06-04 审查发现旧 live `decision_value_p50_error` 曾用 formal P50 减 raw `final_value`，会把刻意裁掉的
极端尾部重新惩罚到 MAE。现已统一为
`decision_value_p50 - final_decision_value_with_tail_replacement`，并保留
`decision_value_p50_error_vs_formal` / `decision_value_p50_error_vs_raw` 作裁尾和原始结算对照。因此本 checkpoint
之前部分 live P50 MAE 历史数字混入了 raw tail，不应直接用于版本升级判断。

## 2. 数据集职责

两类样本不能混为同一种准确性证据：

1. `data/samples/fatbeans` 的 338 份静态样本适合检查解析、约束、hero/map/profile 分组、no-q6 control、
   sampler 候选和结算态条件推理；多数不是同一局五轮完整 pre-bid 序列。
2. WinDivert complete archive 的逐报价 prefix 重放才是 R1-R5 实战推荐准确性主证据。

静态样本可以证明候选没有大面积副作用，但不能单独证明 R1-R5 推荐随信息增加而变准。

## 3. 分轮验收指标

正式候选必须同时看 P50、P90、control 和同局 progression，不能只看单一 coverage。

核心指标：

- `decision_value_mae`：正式 baseline `decision_value` P50 对 replacement-adjusted truth 的平均绝对误差。
- `median_normalized_abs_p50_error`：`abs(P50 - replacement-adjusted truth) / max(replacement-adjusted truth, 100000)` 的中位数。
- `p50_under_rate`：检查系统性低估；足够样本后应接近 `0.5`，不能长期接近 `0` 或 `1`。
- `p90_coverage`：正式 baseline `decision_value` P90 覆盖 replacement-adjusted truth 的比例。
- `p90_pinball_loss`：P90 分位损失；漏覆盖会比过高估计受到更重惩罚，适合和 coverage 一起判断 P90 是否校准。
- `median_p90_covered_excess_ratio`：已覆盖样本中 P90 高出 truth 的比例，检查 P90 是否虚高。
- `p90_extreme_over_rate`：P90 高出 truth 超过一个 truth denominator 的比例。
- `prebid_session_progression`：同一局从前轮到后轮，P50 误差是否缩小、P90 是否丢覆盖、区间是否收窄。

MAE 的定位：

- MAE 适合作为 P50 中心估值的主指标之一，因为它比 RMSE 更不容易被单个极端尾部主导。
- MAE 不能单独代表准确性；它必须和 normalized P50 error、under-rate、P90 coverage、P90 under/excess、
  extreme-over 与 P90 pinball loss 一起看。
- P90 coverage 也不能单独作为升级依据；若 coverage 靠抬高 sampler floor 获得，但 P50 MAE、normalized
  P50 error 或 extreme-over 明显恶化，该候选只能作为 risk/shadow，不应进入 formal baseline。
- RMSE 暂不作为主指标；它会过度放大少数百万级尾部，和“P90 可以包含长尾，但不能带偏整体中心估值”的目标冲突。

以下是有足够样本后的暂定验收线，不是当前小样本下的调参目标：

| 窗口 | median normalized P50 error | P90 coverage 下限 | P90 extreme-over 上限 |
|---|---:|---:|---:|
| R1 | `<= 0.45` | `>= 0.80` | `<= 0.35` |
| R2 | `<= 0.35` | `>= 0.85` | `<= 0.30` |
| R3 | `<= 0.30` | `>= 0.88` | `<= 0.25` |
| R4 | `<= 0.25` | `>= 0.90` | `<= 0.20` |
| R5 | `<= 0.20` | `>= 0.90` | `<= 0.15` |

候选升级还必须满足：

- 同一批窗口 paired 对照，不用不同样本集合制造改善。
- 受影响轮次的主评估 P50 MAE 不恶化超过 `5%`，同时必须观察 `*_vs_formal` 和 `*_vs_raw`。
- P90 coverage 的提升不能靠显著增加 no-q6 positive 或 P90 extreme-over 换取。
- q6、no-q6、normal、tail、hero/map/profile 必须分别看；总体均值不能掩盖分组回归。
- 后轮信息增加后，progression 不应系统性扩大误差或区间。
- R1-R5 每轮至少有 `30` 个 ready 窗口后再做稳定升级判断；主要 hero/map/q6 regime 至少有 `10` 个。

## 4. 当前实测基线

最新 72h pre-bid archive：

- `6` 局、`25` 个真实报价窗口、`23` 个 ready accuracy 窗口。
- 只有 `2` 局包含完整 5 个报价窗口。
- `2` 个 R1 窗口在第一条 bid 前没有状态，也没有估值，属于采集缺口。
- 所有有本轮 action send 的窗口，其 action result 都在报价前返回；窗口边界实现符合设计。

| 轮次 | ready/总窗口 | replacement-adjusted P50 MAE | median normalized P50 error | P90 coverage | P90 extreme-over |
|---|---:|---:|---:|---:|---:|
| R1 | `4/6` | `319,209` | `0.585` | `0.50` | `0.50` |
| R2 | `6/6` | `416,462` | `0.393` | `0.67` | `0.50` |
| R3 | `6/6` | `387,329` | `0.397` | `0.50` | `0.50` |
| R4 | `5/5` | `411,358` | `0.548` | `0.60` | `0.20` |
| R5 | `2/2` | `515,695` | `0.392` | `1.00` | `0.00` |

R5 样本只有 2 个，不能据此校准；其中 Aisha 2506 从 R4 的低估转为 R5 明显过估，说明“后轮更多信息”
目前并不自动等于“更准确”。

同局 progression：

- `17` 个相邻轮次 transition 中，P50 误差缩小或持平比例 `0.76`，仍有 `4` 次后轮变差。
- R4 -> R5 只有 `2` 次 transition，P50 误差都缩小；整体相邻轮次的中位 P50 绝对误差变化为 `-45,255`。
- P90 区间缩小或持平比例只有 `0.53`；后轮信息尚未稳定转化为更窄、更准的 posterior。

当前最重要的校准分裂：

| 分组 | replacement-adjusted P50 MAE | P50 under rate | P90 coverage | P90 extreme-over |
|---|---:|---:|---:|---:|
| q6=0 | `86,802` | `0.50` | `1.00` | `0.83` |
| q6>0 | `679,784` | `0.92` | `0.25` | `0.00` |

这说明 v2 不是简单“整体估低”：它对无 q6 局的 P90 经常过高，同时对真实 q6 局严重低估。统一抬高
P90、扩大 profile gate 或继续增加 trials 都无法同时解决两边。

2026-06-04 追加分量诊断：

- `summarize_live_windivert_brief.py` 的 top miss 已拆出 q6 presence/count/cells/value/tail replacement 分量。
- Aisha 2506 R2/R3/R4 的共同缺口是 q6 count/cells P90 过低，不是单纯 tail replacement：
  - R2 truth q6 count/cells `6/57`，P90 `4/12`，q6 replacement truth `1,673,605`，q6 P90 `697,163`。
  - R3 truth `6/57`，P90 `5/27`，q6 replacement truth `1,673,605`，q6 P90 `996,086`。
  - R4 truth `6/57`，P90 `4/19`，q6 replacement truth `1,673,605`，q6 P90 `771,750`。
- Ethan 2401 `public:random_avg+layout` 的 live miss 同样以 count/cells under 为主，且伴随 `warehouse_under<-20`；
  R3 truth q6 count/cells `3/21`，P90 `1/4`，q6 P90 低估 `284,963`。
- 338 静态样本复核支持该结论：Aisha shipwreck q6 plannable miss `62/101`，其中 count under `56`、
  cells under `55`、count below prior `49`、cells below prior `44`；整体 q6 miss 中 low-space-pressure 占
  `124/161 = 0.7702`。简单 tail replacement candidate 在 bottom-row `9..13` 阈值下 `q6_helped_rows=0`。

338 份静态样本、`trials=20` baseline：

- replacement-adjusted decision MAE `408,675`，regular MAE `397,031`，tail-event MAE `588,566`。
- q6 plannable coverage `0.4505`，q6 misses `161`。
- evidence stage：early R1-R2 MAE `414,854`，mid R3-R4 MAE `427,225`，full R5 MAE `264,776`。
- 静态 full-R5 条件推理方向较好，但不能替代真实 R5 pre-bid 序列验证。

2026-06-04 追加 count/cell P90-only 窄门控对照：

- `q6_count_cell_prior_narrow_gate_p90_sweep` 只作为离线/shadow 审计字段，明确不动 posterior、P50、formal
  `decision_value`、bid hint、停止价或 tail replacement 接线。
- raw baseline 上，Aisha deep gate active `46` 行且 active no-q6 为 `0`；ratio `1.0/1.25/1.5/2.0`
  分别修复 `12/17/21/26` 个 q6 plannable P90 miss，coverage 从 `0.4505` 提到
  `0.4915/0.5085/0.5222/0.5392`。
- Ethan villa random_avg 仍只有 `2` 个 active q6 样本、active no-q6 为 `0`；ratio `1.5/2.0` 修复 `1` 个 miss。
  方向为正，但样本量太低，只能继续 shadow 收数。
- 以 Aisha deep sampler floor1 作为当前正式候选基线时，MAE `369,462`、q6 coverage `0.5408`，同一
  count/cell-under-prior trigger 下 P90-only 包络没有额外 eligible Aisha deep 行。继续提高全 sampler floor 到
  `1.5/2.0` 可把 coverage 提到 `0.5646/0.5748`，但 MAE 回退到 `374,538/389,537`。
- 结论：Aisha deep 的历史门控边界仍安全，但继续抬正式 sampler floor 不符合 MAE 目标；P90-only 包络适合保留为
  risk audit / shadow 输出，不应变成正式出价。剩余问题更像 q6 count/cells/value 的条件 likelihood，而不是
  tail replacement 或 trial 数不足。

2026-06-04 追加指标复核：

- 静态 evaluator 新增 `decision_value_accuracy`，输出中心误差、归一化误差、under-rate、P90 coverage、
  P90 under/excess、extreme-over 和 P50/P90 pinball loss。
- 338 raw baseline：MAE `408,675`，median normalized abs P50 error `0.491`，P50 under-rate `0.8419`，
  P90 coverage `0.4377`，P90 pinball loss `251,190`。
- Aisha deep floor1：MAE `369,462`，normalized P50 error `0.439`，P90 coverage `0.5152`，
  P90 pinball loss `212,368`。
- Aisha deep floor1.5/2.0：P90 coverage 小幅升到 `0.5273/0.5394`，P90 pinball loss小幅降到
  `209,652/208,731`，但 MAE 回退到 `374,538/389,537`，normalized P50 error 回退到 `0.458/0.467`。
  因此 floor1 仍是当前 formal P50 baseline 的较均衡点，更高 floor 只适合 risk/shadow。

2026-06-04 追加参数审计：

- 新增 `evidence_parameter_audit`，集中记录 random sample avg、public info、均格、Aisha 位置阈值和 q6 gate activity。
- random sample avg 当前分布为 `signal=19`、`low_filtered=44`、`none=270`。`signal` 组 q6 风险明显但没有
  no-q6 control，因此不能仅凭该组直接放宽正式 q6 gate。
- `--random-sample-avg-profile-floor` 只影响 evidence-profile routing；posterior value floor 仍用代码内默认
  signal floor。若后续要调整随机均价阈值，必须先确认是只改 profile，还是同步改 value floor hard/soft 逻辑。
- public avg-cells 只有 `4` 行唯一、`50` 行多解；均格仍主要是 soft evidence/diagnostic，不应硬化。
- Aisha bottom-row risk 阈值为 `16`，formal deep gate 阈值为 `13`，quality-only deep row 为 `13`。quality-only
  仍是 review-only soft risk，不生成 hard footprint，不移动已有轮廓。

2026-06-04 追加条件审计：

- live `top_p90_misses` 已补齐 gate/gap/random floor 字段，便于区分“gate 未激活”和“gate 已激活但 posterior
  仍低估”。
- Aisha 2506 R2 是 `layout_bottom_row=11`、deep threshold `13`、gap `2` 的 inactive 边界；R3/R4
  是 `layout_bottom_row=15`、formal prior floor active、ratio `1.0`，但仍然 count/cells/value under。
- Ethan 2401 villa random_avg 的 R1 为 hard random floor，R2-R4 为 soft random floor，仍伴随 q6
  count/cells under 与 `warehouse_under<-20`；因此 random avg 不能只当总值 floor，需要表达 q6 件数/占格/价值
  的条件似然。
- 静态 `q6_condition_audit`、338 份、`trials=20`：
  - q6 plannable truth `293`，miss `161`，coverage `0.4505`。
  - `q6_count_under_truth`：truth `161`、miss `142`、coverage `0.118`。
  - `q6_cells_under_truth`：truth `151`、miss `142`、coverage `0.0596`。
  - `low_space_pressure`：truth `195`、miss `126`、coverage `0.3538`。
  - `q6_count_below_prior` / `q6_cells_below_prior`：miss `125` / `118`。
  - `aisha_deep_gate_active`：truth `46`、miss `37`、coverage `0.1957`。
  - `aisha_shipwreck_deep_gate_inactive`：truth `54`、miss `25`、coverage `0.537`。
  - `random_avg_signal`：truth `19`、miss `14`、coverage `0.2632`。
  - `ethan_villa_random_avg_gate_active`：truth `2`、miss `2`、coverage `0.0`。
- `aisha_shipwreck_deep_threshold_p90_sweep` 进一步检查 Aisha R2 的 `bottom_row=11` 边界：
  - 当前 formal threshold `13`：active `46`、active no-q6 `0`、修复 `12` 个 q6 miss。
  - threshold `12`：active `57`、修复 `13` 个，但 `1` 个 no-q6 P90 被抬高。
  - threshold `11`：active `69`、修复 `14` 个，但 `2` 个 no-q6 P90 被抬高。
  - threshold `9/10` 修复更多，但 no-q6 P90 increased 都为 `5`；所有阈值下 no-q6 new positive 都是 `0`。
  这说明下调 threshold 有 P90 audit 价值，但相对 `13` 的保守净收益没有更好，不能直接升级 formal。
- actual sampler 复核修正了这个判断的力度：`aisha_deep11_floor1` 在 338 静态样本、`trials=20`、两个 seed
  下都比当前 `aisha_deep_floor1` 有更低 MAE 和更高 q6 coverage，且 no-q6 new positive 仍为 0；副作用是
  no-q6 P90 positive median 上升，active no-q6 control 从 0 变为 2。
- 补充完整 accuracy 对照后，seed 1 的 `aisha_deep11_floor1` 相对 baseline 仍然是正向：MAE `359,733`
  vs `408,675`，median normalized P50 `0.415` vs `0.491`，P90 coverage `0.5455` vs `0.4377`，
  P90 pinball `203,308` vs `251,190`；但 P90 extreme-over 也从 `0.0851` 升到 `0.1303`。这就是它只进
  shadow、不进 formal 的核心原因。
- 因此 deep11 已接为 live/debug shadow：默认只记录 active metadata，`shadow_trials>1` 才跑 posterior。
  72h archive、`shadow_trials=10` 显示它能覆盖 Aisha 2501 R1，但 Aisha 2506 R2/R3/R4 仍 active_miss。
  结论是 deep11 值得继续收数，但不是 formal baseline。
- 72h archive 的 top miss shadow label 已能区分 active/miss：Aisha 2506 R2 是 `aisha_deep11_floor1`
  active_miss；R3/R4 是 `aisha_deep_floor1;aisha_deep11_floor1` active_miss。三轮 q6 truth 都是
  `6` 件/`57` 格，而 q6 P90 只有 R2 `4` 件/`12` 格、R3 `5` 件/`27` 格、R4 `4` 件/`19` 格。
  这说明继续放 gate 不能解决主缺口，下一步应做 active gate 内 count/cells/value 条件分布。
- tail/value replacement sampler 审计也排除了一个方向：338 样本下各 Aisha shipwreck threshold 的
  `q6_helped_rows` 都是 `0`，因为 replacement P90 通常没有高过 formal q6 P90。tail replacement 仍是
  truth/audit，不是当前 active-miss 的修复点。
- q6 prior count/cell 拆分进一步确认 cells 是有效信号但不能粗暴倍增：`aisha_deep11_cell2_floor1`
  把 q6 coverage 提到 `0.6088`、paired helped 到 `46`，但 MAE 从 deep11 floor1 的 `359,733`
  回退到 `378,097`，P90 extreme-over 从 `0.1303` 升到 `0.1545`；cell3/cell4 的 MAE 与 over
  继续恶化。结论是需要条件 likelihood，而不是固定 cells multiplier。
- 诊断结论：q6 count/cells under 是主瓶颈，tail replacement 只是 truth/audit 层；继续提高 sampler floor 会把
  P90 coverage 与 P50 MAE 拉向冲突。下一步 v2 只能做条件 likelihood / count-cell-value sampler；若继续依赖
  专用 gate 和 floor 小调，则进入 v3 评审。

## 5. v2 审查

### 已确认的优点

- 保留 v1 的 map/drop 白盒先验、简单 fallback 和可解释性；无约束或 zero-match 时仍能给出可审计参考。
- v2 已有统一 `SessionObs` / live evidence 输入、hard/soft 约束、shape/category/layout 合并和完整诊断字段。
- formal decision、replacement-adjusted truth、raw ceiling 已分口径，适合把正式出价、常规校准与长尾风险分开。
- shadow/evaluator/paired compare 已形成安全试验链路，不必直接污染正式出价。
- quality-only 不生成 hard footprint、已有 footprint 不被宝光位置移动等边界已固定。

### 已确认的问题

1. q6 presence、件数、占格和价值仍在同一个 residual sampler 中耦合。当前 miss 需要靠 prior floor、boost、
   value tilt 和 profile gate 局部补偿，难以解释“为什么这条证据应改变 q6 的哪一个维度”。
   count/cell floor 拆分实验说明 cells 维度确实可动，但固定倍数会把 P50 与 P90 over 带坏。
2. `random_sample_avg` 主要作为全仓 value floor/profile signal，不能表达“这个均价对 q6 出现、q6 件数、
   大件概率和普通高价值尾部的条件似然”。
3. profile gate 数量持续增加，且 Aisha deep、hidden、villa、Ethan random_avg 等规则互相独立。继续加 gate
   会让行为难以组合、难以按轮次校准。
4. P50 与 P90 来自同一采样分布；当前 q6/no-q6 分裂意味着只调 sampler 权重容易同时移动常规中心和长尾上界。
5. 静态样本充足，但五轮 pre-bid 序列稀少；旧评估又曾混用 formal P50 与 raw truth，容易导致调参目标漂移。
   当前主校准改用 replacement-adjusted truth，但 formal/raw 辅助轴必须一起保留。
6. 后轮新增证据没有稳定缩小 posterior，说明 evidence likelihood、残差空间或采样顺序仍可能让信息价值被稀释。

### 当前不支持的结论

- 不能因为 Aisha/Ethan 几个 top miss 就直接重写 v3。
- 不能把 tail replacement 接入正式 `decision_value`；它没有修复 q6 occurrence/count/cells 根因。
- 不能靠增加 trials 解决当前偏差；已有 10/80/200 trials 对照显示主问题是模型偏差，不是 MC 方差。
- 不能放宽 Aisha deep threshold 或 profile-wide floor；历史 no-q6 control 已证明副作用。

## 6. v2 下一步诊断顺序

1. 先以五轮 pre-bid 合同为唯一 live 准确性入口，持续检查 window ready、分轮指标和 progression。
2. 已完成 top miss 的 q6 occurrence/count/cells/ordinary value/tail replacement 分量输出；下一步候选必须以这些
   分量作 paired 指标，不能只看一个总 P90 coverage。
3. Aisha 2506：优先研究 q6 count-cell residual sampler 或条件 likelihood；tail replacement 继续只作评估 truth。
4. Ethan villa random_avg：研究条件 likelihood，而不是继续 prior-floor；重点看 random avg 对 q6/no-q6 control
   的可分性。
5. 优先补完整五窗口 archive，尤其 R5 和目标 hero/map/q6 regime；收数服务于明确验收缺口，不盲目增加 trials。

### 6.1 新增 q6 cell-gap 分组诊断

- `evaluate_fatbeans_v2_samples.py` 已新增 `q6_cell_gap_by_feature`，用于把 q6 plannable miss 拆到
  count/cells/value gap、prior gap、bottom-row、evidence profile、random_avg、stage/density 和 no-q6
  controls。它只作为条件 sampler 的选桶和验收入口，不改变正式估值。
- 默认 338 样本、`trials=20`：q6 plannable truth `293`、miss `161`，其中 `131` 是 count 与 cells
  同时 under。当前 formal Aisha deep gate 后 miss 降到 `135`，deep11 shadow 后降到 `125`。
- Aisha shipwreck ge13 `shape+layout` 说明 floor 对门内 count/cells under 有效：raw 为 `32` truth /
  `25` miss / `24` count+cells under；formal deep floor 后为 `33` truth / `9` miss / `1`
  count+cells under。
- deep11 shadow 主要修 11-12 行门控缺口；它不能解释 ge13 剩余 value miss、bottom 9-10、Aisha/Ethan
  villa 或 Ethan shipwreck layout 桶。
- 下一步条件 likelihood 应优先生成可复跑的 count/cell/value target，而不是固定乘 prior cells；每个候选必须
  同时报告本表、paired helped/no-q6 control、MAE、normalized P50、P90 extreme-over 和 pinball。

### 6.2 条件 target 上界实验

- `q6_conditional_target_experiment` 已作为 in-sample upper-bound audit 接入 evaluator。它从证据组中估计
  收缩后的 q6 `target_count`、`target_cells`、`target_value`，只在当前 q6 count/cells P90 低于组目标时
  做 P90 what-if；它不是 posterior，也不是可部署策略。
- raw baseline 下 `hero_map_profile` 可将 q6 miss `161 -> 88`，但 no-q6 P90 increased `21`，
  new positive `4`，说明 profile 目标有信号但过宽。
- current formal Aisha deep baseline 下，`hero_map_bottom_profile` 的副作用更小：`135 -> 107`，
  helped `28`，no-q6 increased `6`，new positive `0`。但 Aisha deep-only profile 只剩 helped `8` /
  no-q6 increased `4`。
- deep11 shadow baseline 下，Aisha deep-only profile 只剩 helped `2` / no-q6 increased `2`，净收益 `0`。
  因此 deep11 已基本吃掉 Aisha 11-12 的门控收益，Aisha bottom 9-10 不应继续统一抬。
- 最干净的下一步候选转到 Ethan shipwreck layout：current formal baseline 下
  `hero=ethan|map_family=shipwreck|evidence_profile_key=layout` 为 helped `15` / no-q6 increased `0`；
  `q6_prior_gap_kind=count_and_cells_below_prior` 子桶同样 helped `15` / no-q6 increased `0`。这更适合写
  shadow-only q6 likelihood，而不是继续 Aisha threshold/floor 调参。

### 6.3 Ethan shipwreck 条件 sampler 复跑结论

- 已实现默认关闭的真实 sampler 参数：`q6_conditional_target_count`、`q6_conditional_target_cells`、
  `q6_conditional_value_power`，并用 `ethan_shipwreck_layout_v1` gate 将首个候选限制在 Ethan shipwreck
  `layout` / `public:random_avg+layout`。正式 `decision_value`、bid hint、stop price 和 tail replacement
  均不使用该 sampler。
- 338 样本、`trials=20`、seed `1`：当前 formal `aisha_deep_floor1` baseline 的 q6 miss 为 `135`，
  decision MAE `369,462`，P90 extreme-over `0.1152`。叠加
  `ethan_shipwreck_layout_conditional_c4_cells15` 后，q6 miss 降为 `112`，paired q6 helped `23`，
  no-q6 new positive `0`，MAE 降为 `341,354`，但 P90 extreme-over 升到 `0.1394`。
- `value_power=0.25/0.5` 多救 `1` 个 q6 miss，但 MAE 分别为 `342,897` / `342,012`，P90 extreme-over
  升到 `0.1424` / `0.1485`。因此当前更合理的“适度激进”是只抬 count/cells，不做 value tilt。
- 该候选已接 live/debug shadow：`q6_residual_ethan_shipwreck_layout_conditional_shadow`，UI role 为
  `shipwreck_layout_q6_likelihood_shadow`，`affects_bid=false`。后续实机验证应看 active rows、no-q6 control、
  P90 excess、pinball 和 five-window ready，而不是只看 q6 coverage。

### 6.4 公开 exact numeric 与 cells-only residual sampler

- 实机公开信息审计发现 v2 之前漏掉一组强 hard evidence：`200009-200012` 的 exact cells 位于 protobuf
  field `14`，`200017-200020` 的 exact count 位于 field `7`。接入后，当前 348 样本已观察的
  `23` 个 public info id 均已归类，`pending_model_ids=[]`、`unknown_ids=[]`。
- 受 exact numeric 影响的 `128` 样本中，启用 exact 相对剥离 exact 的 decision MAE
  `404,953 -> 300,145`、median abs `258,920 -> 179,112`、q6 plannable coverage
  `0.4505 -> 0.5321`；paired P50 abs 为 `79` improved / `29` worsened，q6 coverage
  为 `16` helped / `6` lost。说明公开 exact 总体价值明确，不能因少量冲突而退回估计值。
- 同时确认一个 v2 结构问题：只有 total cells、没有 total count 时，旧 residual sampler 没有按精确剩余格数
  构造可行组合，只能随机采样后 rejection。新增 exact-cells residual fill 后，全量 zero-match
  `10 -> 6`、decision MAE `378,114 -> 369,956`、q6 plannable coverage `0.453 -> 0.4784`。
- 剩余 `6` 个 zero-match 主要包含多个 exact bucket cells、exact value、shape/layout 的组合，已经不是
  cells-only 总格数缺口。下一步应拆解这些约束的联合可行性和 action/value 语义，不应通过忽略 hard exact
  或增加 trials 来掩盖。
- 这次修复说明 v2 仍有值得优先修的结构缺陷：先保证公开 hard evidence 能被正确解析和条件采样，再评估
  q6 likelihood 调参收益。它暂不构成启动 v3 的充分条件，但应计入 v3 的 likelihood/constraint 模块设计。

## 7. v2 停止条件与 v3 启动条件

满足以下条件后，局部调参应停止并进入 v3 设计评审：

- 某个主要 miss regime 已有至少 `30` 个 ready pre-bid 窗口，连续 3 个有明确假设的 v2 候选都无法在不恶化
  control/P50 MAE 的前提下把该组 P90 coverage 提高至少 `10` 个百分点。
- 同一根因在 R3-R5 高信息窗口仍重复出现，且增加信息没有稳定缩小 posterior。
- 新修复必须继续新增 hero/map/profile 专用 gate，规则交互已经难以通过现有 paired tests 解释。
- q6/no-q6 校准分裂长期存在：修 q6 miss 必然显著抬高 no-q6 P90，或压 no-q6 又必然漏 q6。

## 8. 未来 v3 必须继承与重构的内容

必须继承：

- v1 的 map/drop 白盒先验、快速 fallback、可解释输出。
- v2 的 canonical evidence、hard/soft 边界、formal/raw/tail 分口径、shadow 升级流程和现有 fixtures。

针对性重构方向：

1. 显式拆分 latent state：`q6_presence`、`q6_count`、`q6_cells`、`q6_ordinary_value`、
   `exceptional_tail_scenario`，避免一个 residual 权重承担全部问题。
2. 每类公开信息和道具结果作为独立 likelihood 模块，明确它影响哪个 latent state；random_avg 不再只是总值 floor。
3. 按 R1-R5 做 sequential update，同局新增证据应可审计地缩小或移动 posterior。
4. baseline `decision_value` P50/P90、replacement-adjusted truth、formal plannable truth、raw/tail risk 使用清晰的输出合同；
   P90 长尾风险不能通过抬高常规 P50 获得。
5. v3 先接现有 evaluator/live archive 为 shadow，必须用同一批五轮窗口与 v2 paired 对照，未过验收前不接正式出价。

## 9. 复跑命令

```powershell
C:\Python313\python.exe .\scripts\summarize_live_windivert_brief.py --since-hours 72 --archive-n-trials 10 --archive-shadow-trials 1
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v2_samples.py --trials 20 --format summary
```

实机采样前仍先重启：

```powershell
.\scripts\start_live_windivert_overlay.ps1 -Restart -PortOnly
```
