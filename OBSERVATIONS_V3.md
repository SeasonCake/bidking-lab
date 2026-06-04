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

## O-v3-012：初版 v3 posterior skeleton 指标仍不可用

当前 355 archive、512 samples/map 的 formal paired metrics：

```text
metric_rows=1247
formal_p50_mae=347622.463
formal_p50_mae_strict=359635.128
formal_p50_mae_fallback=342765.991
formal_p90_coverage=0.768244
q6_formal_p50_mae=304356.084
q6_formal_p50_mae_strict=321732.513
q6_formal_p50_mae_fallback=297331.154
```

结论：

- 当前 skeleton 的主要价值是让 v3 有稳定 paired metric，不是估值质量已经过关。
- strict 样本只是 prior bank 恰好命中完整 summary，不代表条件 proposal 已经正确。
- 下一步优化必须直接降低 formal/q6 MAE，并提高 P90 coverage；否则不能进入 live formal。

## O-v3-013：样本库需要文件级 manifest，不能把窗口数当新增样本

`scripts/summarize_fatbeans_sample_manifest.py` 当前 archive 结果：

```text
files=355 parsed_files=350 parse_errors=5 valid_files=335 mixed_files=15 invalid_files=5 usable_metric_files=350
bid_windows=1262 ready_windows=1247 no_state_windows=15 constraint_conflict_windows=0
```

结论：

- `355` 是真实 Fatbeans capture 文件数；`1262` 是从这些真实文件按玩家报价前边界派生的 pre-bid 窗口数，不是生成样本。
- `335` 份文件所有 pre-bid 窗口均可用；`15` 份 mixed 文件有可用窗口，也有 no-state 采集缺口；`5` 份旧样本 parse error。
- mixed 文件不能整局丢弃，否则浪费有效窗口；但 no-state 窗口不能进入 MAE/coverage/pinball 分母。
- 当前 manifest 还统计 public info/action/skill 出现次数，可作为“数据里有但 pipeline 未消费”的审查入口。
- 当前公开 exact 信息出现次数包括：`200009` 总格 `118` 次、`200017` 总件数 `74` 次、`200010/200011/200018/200019` 分品质格数/件数若干次。后续 v3 registry/UI/archive 审查应优先确认这些信息全链路消费。

## O-v3-014：manual inbox 77 份新增样本质量高，可作为下一轮校准候选

2026-06-05 复核 `data/samples/fatbeans_manual_inbox`：

```text
files=77 parsed_files=77 parse_errors=0 valid_files=77 mixed_files=0 invalid_files=0
bid_windows=264 ready_windows=264 no_state_windows=0 constraint_conflict_windows=0
```

分布：

- hero：Ethan `20`、Aisha `20`、Gabriela `10`、Sophie `10`、Wuqilin `17`。
- round：R1 `8`、R2 `7`、R3 `19`、R4 `30`、R5 `13`。
- 高频 map：`2501` 19、`2401` 13、`2504` 8、`2507` 6、`2408` 6。

结论：

- 新增样本没有 parse error、no-state 或 constraint conflict，质量明显好于早期 live capture。
- 与当前主样本库无重复 session。
- 若作为 v3 校准输入，整体 ready 窗口会从 `1247` 增至 `1511`。
- 这批样本偏 Ethan/Aisha/Wuqilin 与 R4，适合补充 q6/tail/value sampler 诊断；但还不能替代按地图/英雄均衡采样。

## O-v3-015：canonical archive 后默认样本库 parse error 清零

2026-06-05 已把主库、manual inbox、未重复 live complete 统一整理为 canonical 样本库：

```text
files=433 parsed_files=433 parse_errors=0 valid_files=416 mixed_files=17
bid_windows=1551 ready_windows=1534 no_state_windows=17 constraint_conflict_windows=0
```

5 个旧 parse error 已移到 `data/samples/fatbeans_invalid/parse_error`；默认 evaluator 不再把坏包混进主分母。

当前 512 samples/map posterior skeleton：

```text
metric_rows=1534
posterior_strict_ready=513
posterior_fallback=1021
formal_p50_mae=335384.256
formal_p90_coverage=0.767927
q6_formal_p50_mae=295848.365
```

结论：

- 样本增加与清理后，formal/q6 P50 MAE 较 355 样本口径有小幅下降。
- P90 coverage 基本仍停在 `~0.768`，说明主要瓶颈仍是 posterior proposal/sampler，不是样本数量。
- `mixed` 文件仍有 17 个 no-state 窗口；它们只作为数据质量记录，不进入模型准确率分母。
- 后续 v3 调参默认使用 433 canonical 样本；旧 06-04 manifest 仅作历史映射参考。

## O-v3-016：summary-likelihood 需要保留 tail guard，否则会复现低估

2026-06-05 在 433 canonical 样本上对比了 strict 缺口的第一版 likelihood fallback。

直接用未展平的 evidence likelihood 会明显恶化：

```text
posterior_summary_likelihood=1021
formal_p50_mae=344718.493
formal_p50_mae_fallback=351841.429
formal_p90_coverage=0.653194
q6_formal_p50_mae=315351.666
```

原因：

- strict 无命中窗口中，证据经常只有低信息量 q6 presence、少量 floor 或局部格数。
- 如果 likelihood 权重过尖，effective samples 常压到 `1-5` 个，P90 也变成“最像证据的一小撮样本”，长尾直接消失。
- 这和实战低估反馈一致，不能作为 v3 promotion 方向。

加入 temperature 后，P50 变好但 P90 仍偏窄：

```text
temperature=4
formal_p50_mae=332122.447
formal_p90_coverage=0.747066
q6_formal_p50_mae=299595.192
```

最终当前版本采用：

- P50：evidence-weighted likelihood + likelihood support 未加权 P50 lower guard。
- P90：likelihood support 未加权 P90 tail guard。

当前指标：

```text
formal_p50_mae=329399.887
formal_p50_mae_fallback=328826.011
formal_p50_bias=-188482.821
formal_p50_below_rate=0.632986
formal_p90_coverage=0.769883
q6_formal_p50_mae=295957.275
q6_formal_p50_mae_fallback=294703.346
q6_formal_p50_bias=-133583.532
q6_formal_p50_below_rate=0.582790
q6_formal_p90_coverage=0.815515
```

结论：

- v3 的下一步不是继续盲目加 prior trials，而是让条件 proposal 能构造满足 count/cell/value summary 的样本。
- 在 proposal 完成前，likelihood fallback 必须保留 tail guard；否则 P90 coverage 会被中位数校准一起压坏。
- 当前版本降低 formal P50 MAE，但仍有明显低估 bias；2601、2506、2501 是下一轮地图级校准重点。

## O-v3-017：posterior quantile 曾违反已知 value floor

2501 top miss 诊断发现：

```text
q6_value_floor=1553900
v3_post_q6_formal_decision_value_p50=628300
v3_post_q6_formal_decision_value_p90=1210464
```

这个窗口已有 q6 item-anchor value floor，但 posterior formal q6 quantile 仍低于 floor。原因是：

- strict/summary-likelihood 只用 constraints 影响样本筛选和单个样本的 formal decision 计算。
- 当 prior bank 没有抽到同一个已知高值 item 时，样本 formal decision 可以低于已知 floor。
- 输出 quantile 没有再投影 `FeasibleSummaryReport` 的 lower bounds。

修复后指标：

```text
formal_p50_mae=325128.627
formal_p50_bias=-184211.561
q6_formal_p50_mae=289689.021
q6_formal_p50_bias=-127315.277
```

对比修复前：

```text
formal_p50_mae=329399.887
q6_formal_p50_mae=295957.275
```

结论：

- v3 posterior 输出层必须做 hard-constraint projection；不能只靠 sampler 恰好抽中已知证据。
- 这类修复直接降低 q6/formal MAE，并减少低估 bias。
- 2601、2506 在该修复后仍是高误差地图，说明下一步应做 map-tail / q6 value 条件 proposal，而不是继续找 floor 投影问题。

## O-v3-018：summary-only posterior 会丢掉 category/shape 对 formal value 的支持

2601/2506 在 hard floor guard 后仍大幅低估。核心原因之一：

- `FeasibleSummaryReport` 只表达 quality count/cell/value exact/floor。
- formal decision truth 还依赖 item/category/shape anchor 判断高值 item 是否 plannable。
- 如果 posterior 样本只按 summary 过滤，不按 anchor 匹配加权，样本里的高值红品会被裁尾或低权重，导致 formal P50/P90 偏低。

新增 anchor-aware likelihood 后：

```text
formal_p50_mae=323364.373
formal_p50_bias=-170223.445
formal_p90_coverage=0.780965
q6_formal_p50_mae=289531.125
q6_formal_p50_bias=-114997.727
q6_formal_p90_coverage=0.828553
```

对比 hard-bound guard：

```text
formal_p50_mae=325128.627
formal_p90_coverage=0.769883
q6_formal_p50_mae=289689.021
q6_formal_p90_coverage=0.815515
```

分片结果：

- 2601 formal MAE `614055.0 -> 594835.6`，P90 coverage `0.569767 -> 0.581395`。
- 2506 formal MAE `502413.1 -> 497158.7`。
- 2501 bias `-270133.2 -> -256607.5`。
- 2507 q6 MAE 回退，说明 anchor weighting 需要继续做分片监控。

结论：

- v3 sampler 不能只消费 summary；必须保留 anchor-aware 层。
- 但 anchor weighting 仍是 likelihood 层，不是最终 proposal。2601/2506 的剩余低估需要专门的 map-tail/q6 value proposal。

## O-v3-019：P50 support guard 提到 P60 后，整体 MAE 改善但部分地图开始偏高

2026-06-05 将 likelihood-weighted posterior 的 P50 support guard 从 support P50 提到 support P60。

整体结果：

```text
formal_p50_mae=316976.209
formal_p50_bias=-129378.797
formal_p50_below_rate=0.582790
formal_p50_over_rate=0.417210
formal_p90_coverage=0.780965
q6_formal_p50_mae=287225.034
q6_formal_p50_bias=-70104.765
q6_formal_p50_below_rate=0.505867
q6_formal_p50_over_rate=0.490222
q6_formal_p90_coverage=0.828553
```

对比 anchor-aware 版本：

```text
formal_p50_mae=323364.373
formal_p50_bias=-170223.445
q6_formal_p50_mae=289531.125
q6_formal_p50_bias=-114997.727
```

分片观察：

- 2601/2506/2501 的低估继续缓解。
- 2507、2508、2505 开始出现正 bias 或较高 over-rate。

结论：

- P60 是当前全局 practical guard 的合理上限；继续全局提高会伤害已接近平衡或偏高地图。
- 下一步需要 map/证据条件化的 proposal，而不是全局 P65/P70。
- over-rate 必须和 below-rate 一起报告，否则会只追求“少低估”而忽略实战过激风险。

## O-v3-020：map-calibrated practical guard 优于全局 P60

2026-06-05 在当前 433 canonical 样本上测试地图分层 guard：

- high-tail：P65，`2404/2501/2503/2506/2601`。
- low-tail：P55，`2407/2410/2505/2507/2508`。
- default：P60。

结果：

```text
formal_p50_mae=313387.992
formal_p50_bias=-122240.706
formal_p50_below_rate=0.573012
formal_p50_over_rate=0.426988
q6_formal_p50_mae=283903.670
q6_formal_p50_bias=-63074.925
q6_formal_p50_below_rate=0.487614
q6_formal_p50_over_rate=0.508475
```

对比全局 P60：

```text
formal_p50_mae=316976.209
formal_p50_bias=-129378.797
q6_formal_p50_mae=287225.034
q6_formal_p50_bias=-70104.765
```

分片观察：

- 2601/2506/2501 继续改善。
- 2507/2508/2505 的正 bias 比全局 P60 缩小。
- 2507 的 over-rate 仍高，2601/2506 的 below-rate 仍高。

结论：

- 地图分层 guard 是当前 v3 shadow 的更好校准口径。
- 但该分层来自当前真实样本，仍需要后续新样本或 holdout 复核。
- 该策略不能替代 q6 count/cell/value 条件 proposal；它只是减少全局 practical guard 的副作用。
