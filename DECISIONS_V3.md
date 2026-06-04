# BidKing Lab v3 Decisions

日期：2026-06-04  
状态：v3 重构主线生效。

## D-v3-001：v2 停止作为主调参路线

v2 保留为可运行基线和对照，不删除、不立即物理移动核心代码。后续 v2 只接受低风险 parser/live/archive/UI 防误导修复，以及为了 v3 对照所需的兼容改动。

原因：v2 在 q6 presence/count/cells/value/tail 上长期系统性低估，局部门控和 floor 的收益已经不足以支撑继续作为主线。

## D-v3-002：所有有意义输入必须先进入 registry

public info、action result、skill reveal、state/settlement 证据必须登记为 hard、soft、partial、diagnostic、pending、ignored 或 unknown。unknown/pending 不允许在 v3 coverage 中静默通过。

当前执行：

- `PUBLIC_INFO_SPECS`
- `ACTION_RESULT_SPECS`
- `SKILL_REVEAL_SPECS`
- `scripts/summarize_v3_evidence_coverage.py --fail-on-gaps`

## D-v3-003：hard constraints 先编译，再采样

v3 不再把 hard exact 当作采样后的 rejection 条件。第一阶段先编译 exact numeric 和 anchor events；后续扩展到 shape/item 可行空间。

当前执行：

- `compile_hard_constraints()`
- exact numeric 冲突显式报告 `ConstraintConflict`

## D-v3-004：v3 先 shadow，不改变 formal bid

v3 进入正式候选前必须先以 offline/shadow 运行。当前 formal decision 仍由 v2 live 路径提供。

保持边界：

- formal decision_value 仍是裁尾 plannable 口径。
- tail replacement 只做审计/辅助字段。
- q6 risk reference 若存在，必须标明 `affects_bid=false`，除非后续单独决策升级。

## D-v3-005：UI 当前设计冻结

当前 live overlay/UI 设计可继续保留。v3 重构阶段不做视觉优化、不换布局、不重复设计。

允许改动：

- 字段兼容。
- 防误导状态。
- v3 shadow 诊断字段显示。

不允许改动：

- 纯视觉重做。
- 改出价含义但不改字段名。
- 隐式把风险参考接入停止价。

## D-v3-006：记录文件分主线管理

根目录 `PROGRESS.md`、`DECISIONS.md`、`OBSERVATIONS.md` 改为索引。v3 当前记录写入：

- `PROGRESS_V3.md`
- `DECISIONS_V3.md`
- `OBSERVATIONS_V3.md`

v2 历史大记录归档到 `archive/v2_legacy_2026-06-04/`。

## D-v3-007：v3 archive report 先并列 raw/prior，不替代 formal truth

v3 evaluator 可以默认输出 `v3_prior_*` 与 `v3_truth_*`，但这些字段当前只用于 shadow 诊断：

- `v3_prior_*` 是 map/drop/item 的确定性先验，不是 posterior。
- `v3_truth_*` 当前是 settlement raw truth，不是 formal decision truth。
- P50/MAE 后续必须默认对齐 formal decision truth；raw truth 只作为明确命名的对照。
- tail replacement 仍只能作为 audit/helper truth，并列输出，不进入正式 bid/stop price。

原因：v2 曾经出现 raw 长尾 truth 与 formal decision estimate 混算，导致“正式估值严重低估”的诊断被放大。v3 不允许再次混淆指标口径。

## D-v3-008：准确率分母默认使用 ready 窗口 formal truth

后续 v3 offline metrics 的默认分母为：

- pre-bid window status 为 `ready`。
- `v3_truth_decision_available=True`。
- 比较目标为 `v3_truth_formal_decision_value`。

raw settlement truth 和 tail-replacement truth 必须以独立字段或独立 metric 名称显式使用：

- raw：用于检查长尾和实际结算总值差异。
- replacement：用于审计“同形状普通替代”是否可改善 P90/coverage。
- no-state：只记数据质量，不计模型误差。

## D-v3-009：posterior sampler 消费 feasible summary，不直接解释 raw numeric payload

v3 后续 sampler 的 hard 输入层级为：

1. `EvidenceEvent`
2. `ConstraintSet`
3. `FeasibleSummaryReport`
4. posterior proposal / likelihood

outline/full-outline 事件的 count/cells exact 由 compiler 根据 observed_items 派生。posterior sampler 不再自己猜测 public/action payload value 的含义。

原因：Aisha q4 outline 曾暴露 payload value 表示 count、不是 cells。如果 sampler 绕过 compiler 直接使用 raw numeric，会复现 v2 式路径分叉和 hidden input bug。

## D-v3-010：v3 posterior fallback 必须显式标记且不作为 promotion 依据

当前 `V3PosteriorReport` 支持：

- `match_scope=strict`：完整 `FeasibleSummaryReport` 命中。
- `match_scope=q6_projection`：strict 无命中时，只按 q6 bucket exact/floor 过滤。

`q6_projection` 的用途是让 archive/live shadow 字段不断档，帮助定位 q6 count/cell/value 方向；它不能作为正式估值或 promotion gate 的证明。

promotion 前必须显著提高 strict-ready 覆盖，或实现等价的条件 proposal，并在 metrics 中单独报告 strict 与 fallback。

## D-v3-011：v3 posterior 默认指标对齐 formal decision value

`V3PosteriorReport` 同时输出 raw value、formal decision value、tail-replacement decision value。后续默认准确率指标使用：

- 预测：`v3_post_formal_decision_value_p50`
- 真值：`v3_truth_formal_decision_value`

其他字段只能作为显式命名的对照：

- raw 对照：`v3_post_total_value_*` vs `v3_truth_raw_total_value`
- replacement 对照：`v3_post_tail_replacement_decision_value_*` vs `v3_truth_tail_replacement_decision_value`
- q6 对照：必须区分 raw q6 与 formal q6。
