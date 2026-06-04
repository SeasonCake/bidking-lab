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
