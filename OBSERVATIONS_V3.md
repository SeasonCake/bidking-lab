# BidKing Lab v3 Observations

日期：2026-06-04  
用途：记录 v3 重构期间的新观察，和 v2 历史观察分开。

## O-v3-001：v2 的核心问题不是 trials 数不足

历史 live/archive 对照显示，单纯增加 sampler trials 或扩大 q6 floor 不能稳定解决严重低估。主要问题是证据到 q6 latent variables 的条件化不足：

- q6 presence
- q6 count
- q6 cells
- q6 ordinary value
- exceptional tail scenario

这些变量在 v2 中被残差 sampler 和多个 profile gate 混在一起，难以用局部参数稳定修复。

## O-v3-002：输入覆盖必须成为可执行检查

公开总格数 `200009` 曾经已在实机首屏存在，但没有进入模型和 UI。这个问题说明 parser 成功不等于 evidence 被建模。

当前 v3 coverage 结果：

```text
files=355 parsed_files=350 parse_errors=5 events=10164 coverage_ok=True ok=False
by_kind=action_result:4075;public_info:1922;settlement:350;skill_reveal:3817
unknown=none
pending=none
```

结论：registry gap 当前已清零；`ok=False` 来自 5 个旧样本 parse error，需要按数据质量单独处理。

## O-v3-003：样本和脚本暂不移动

`data/samples/fatbeans` 当前 355 份样本是 v3 coverage、v2/v3 paired compare 和后续 sampler 验收的主数据源。该目录虽然在 `.gitignore` 中属于本地样本，但不能为了整理目录而移动，否则会破坏现有脚本默认路径。

同理，当前 `scripts/` 与 `tests/` 仍是活跃工具，不做物理归档。归档的是历史记录，不是可运行入口。

## O-v3-004：外部参考目录已和源码分离

外部参考在 `external_references/`，当前不属于项目源码：

- `external_references/grid_view_v1.3.7/`
- `external_references/AuctionAnalyzer4.13.3.zip`
- `external_references/AuctionAnalyzer4.13.3/`
- 其他外部 repo/reference clone

这些路径在 `.gitignore` 下本地保留，不作为 v3 源码路径引用。需要引用时由脚本显式指向 `external_references/`。

## O-v3-005：UI 设计当前可保留

用户确认当前 UI 设计可以保存，不需要重复设计。v3 期间只应维护字段兼容和风险提示准确性，不做视觉重构。

## O-v3-006：Phase 2 anchor 编译已证明 archive 可跑

v3 hard constraint compiler 从 numeric exact 扩展到了结构化 anchors。当前 350 个可解析 archive 样本扫描结果：

```text
numeric=549 item_anchors=1851 shape_anchors=10083 quality_floor_anchors=1384 conflicts=0
```

关键边界仍成立：quality-only/宝光类证据没有 shape/cells 时只进入 `quality_floor_anchors`，不生成 hard footprint。category outline 的 category id 已随 item anchor 保留，后续可行空间不能丢掉该条件。

5 个 parse error 仍是旧样本数据质量问题，不是 hard constraint 冲突。

## O-v3-007：五窗口 constraint skeleton 已把 no-state 和冲突分开

`scripts/evaluate_fatbeans_v3_samples.py` 当前只做 pre-bid window ConstraintSet，不做估值。355 个 archive 样本扫描结果：

```text
windows=1262 ready=1247 no_state=15 constraint_conflict=0 parse_errors=5
numeric_constraints=1386 item_anchors=5137 shape_anchors=27549 quality_floor_anchors=4678
```

这说明 v3 下一步可以在 1,247 个 ready 窗口上接 shadow posterior；15 个 no-state 窗口和 5 个 parse error 应继续作为采集/数据质量，不进入模型准确率分母。

## O-v3-008：prior/truth 可先作为 shadow 诊断接入

v3 evaluator 已能在每个 pre-bid window 上附加确定性 drop prior 与 settlement raw truth：

```text
windows=1262 ready=1247 no_state=15 constraint_conflict=0 parse_errors=5 prior_ready=1247 truth_ready=1262
```

含义：

- `prior_ready=1247` 对齐 ready 窗口；no-state 窗口没有 map state，因此不能生成 prior。
- `truth_ready=1262` 来自完整 archive 的最终 inventory，可用于窗口级 paired evaluation，但不能把 no-state 计入模型精度。
- 当前 truth 是 raw settlement truth，不是 v2 formal decision truth，也不含 tail replacement。

下一步需要把 formal/replacement truth 并列输出，之后再接 posterior，否则 raw 长尾会再次污染 P50/MAE 诊断。

## O-v3-009：formal truth 已按 pre-bid 窗口和 ready 分母对齐

v3 evaluator 现在同时输出 raw settlement truth、formal decision truth、tail-replacement audit truth。355 个 archive 样本扫描结果：

```text
windows=1262 ready=1247 no_state=15 prior_ready=1247 truth_ready=1262 decision_truth_ready=1247
```

结论：

- raw truth 可以挂到所有有最终 inventory 的窗口，包括 no-state，用于数据质量追踪。
- formal/replacement truth 只在 ready 窗口输出，因此 MAE/P50 的分母可以直接对齐可评估窗口。
- tail replacement 字段已经有独立命名；后续 metrics 必须显式选择 formal、raw 或 replacement，不能混用。
- 当前 formal truth 是 truth 口径迁移，不是 posterior；它只定义“应该比较到什么真值”。

## O-v3-010：outline numeric 必须从 observed_items 派生

feasible summary 初跑暴露 `43` 个 `q4.cells_floor_gt_exact`，集中在 Aisha shipwreck。复核样本显示：

- `public_info 200001` 的 payload value 是 q4 outline 数量。
- registry 目标同时包含 `bucket.q4.count` 与 `bucket.q4.cells`。
- 旧 compiler 把同一个 value 同时写入 count/cells，导致 cells exact 被错误压低。

修复后：

```text
evaluate_fatbeans_v3_samples: summary_ready=1247 summary_conflict=0 numeric_constraints=4818
summarize_v3_constraints: numeric=1908 conflicts=0
```

结论：outline/full-outline 这类带 `shape_anchors` 的事件，count/cells exact 必须从 observed_items 派生，而不是复用 payload value。后续 sampler 只能消费派生后的 exact/floor summary。

## O-v3-011：strict summary rejection 仍不足，需要条件 proposal

v3 q6 posterior shadow skeleton 用 `FeasibleSummaryReport` 过滤地图先验样本。当前 archive 结果：

```text
512 samples/map:  posterior_ready=1247 posterior_strict_ready=359 posterior_fallback=888 posterior_no_match=0
2048 samples/map: posterior_strict_ready=422
```

结论：

- q6 projection fallback 让所有 ready 窗口都有 q6 count/cell/value shadow 字段，但它不是完整 posterior。
- posterior 现在已并列输出 raw、formal decision、tail-replacement decision quantiles，默认指标必须选 formal。
- strict 命中从 512 到 2048 只增加 `63` 个窗口，继续盲目加 trials 收益低。
- 下一步应该做条件 proposal / count-cell-value constructor，让样本先满足 summary exact/floor，再估 q6 分布。
- v3 metrics 必须区分 `match_scope=strict` 与 `match_scope=q6_projection`，不能把 fallback 当作 promotion-ready。
