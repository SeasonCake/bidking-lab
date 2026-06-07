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

## O-v3-021：live artifact 可以安全记录 v3 shadow，且不改变 archive 指标

2026-06-05 将 v3 posterior shadow 接入 live monitor artifact 后验证：

- `tests/test_live_monitor.py`：`26 passed`。
- v3 核心测试：`29 passed`。
- 全 archive evaluator 指标与 map-calibrated guard checkpoint 一致：

```text
windows=1551 ready=1534 no_state=17 constraint_conflict=0 parse_errors=0
posterior_ready=1534 posterior_strict_ready=513 posterior_summary_likelihood=1021 posterior_q6_projection=0
formal_p50_mae=313387.992 formal_p50_below_rate=0.573012 formal_p90_coverage=0.780965
q6_formal_p50_mae=283903.670 q6_formal_p50_below_rate=0.487614 q6_formal_p90_coverage=0.828553
```

真实 canonical sample smoke：

```text
fatbeans_mixed_aisha_2401_4rounds_2401_1295018992993210_0001.json
v3_ready=True affects_bid=False scope=summary_likelihood trials=10 error=None
```

结论：

- live artifact/model_eval 现在能携带 v3 shadow 字段，可用于后续实战样本 paired compare。
- 当前接入没有污染 offline archive evaluator，也没有改变 v2 formal baseline。
- `ui_contract` 暂不暴露 v3 shadow 是合理边界，避免实战 UI 把 shadow 误当正式建议。

## O-v3-022：q6-conditioned proposal 改善 fallback，但 2601 仍需单独处理

2026-06-05 在 `summary_likelihood` fallback 中加入 q6 bucket-conditioned proposal 后：

整体：

```text
formal_p50_mae=309872.088
formal_p50_below_rate=0.544980
formal_p50_over_rate=0.455020
formal_p90_coverage=0.799870
q6_formal_p50_mae=282939.074
q6_formal_p50_below_rate=0.462190
q6_formal_p50_over_rate=0.535854
```

对比 map-calibrated guard：

```text
formal_p50_mae 313387.992 -> 309872.088
q6_formal_p50_mae 283903.670 -> 282939.074
formal_p90_coverage 0.780965 -> 0.799870
```

分片：

```text
scope=summary_likelihood formal_mae=306875.8 q6_mae=279836.6
map_id=2601 formal_mae=581040.0 q6_mae=513740.1
map_id=2506 formal_mae=451709.5 q6_mae=411316.2
map_id=2501 formal_mae=337374.6 q6_mae=305785.5
```

结论：

- q6-conditioned proposal 的方向成立：fallback 负 bias 明显下降，overall formal/q6 MAE 均改善。
- 只有 q6 value floor/exact 时才移动 value/formal 分量是必要 gate；否则 count+cells 证据会把 q6 value 推高。
- 2601 在该 proposal 下 MAE 回退，说明它的问题不是简单 q6 floor 残差，后续需要 map/evidence 条件 gate 或专门 proposal。
- high-over 地图仍要跟 below-rate 一起监控，不能为了降低低估而无限提高 aggressive 程度。

## O-v3-023：禁用 hidden q6-conditioned 后，整体 MAE 改善且 family 分片更清楚

2026-06-05 对 hidden `2601` 禁用 q6 bucket-conditioned proposal，并为 archive evaluator 增加 `map_family` 后：

整体：

```text
formal_p50_mae=308876.090
formal_p50_below_rate=0.546936
formal_p90_coverage=0.799218
q6_formal_p50_mae=281387.105
q6_formal_p50_below_rate=0.462842
q6_formal_p50_over_rate=0.535202
```

对比未 gate 的 q6-conditioned proposal：

```text
formal_p50_mae 309872.088 -> 308876.090
q6_formal_p50_mae 282939.074 -> 281387.105
```

`map_family` 分片：

```text
hidden    n=86  formal_mae=563274.2 bias=-379658.3 q6_mae=486057.4
shipwreck n=833 formal_mae=326650.0 bias=-111275.0 q6_mae=299233.0
villa     n=615 formal_mae=249227.5 bias=-50832.8  q6_mae=228594.8
```

结论：

- hidden 当前不适合和 shipwreck/villa 共用 q6-conditioned 主逻辑。
- 禁用 hidden 后，overall formal/q6 MAE 均优于上一 checkpoint。
- hidden 仍严重低估，但这是独立 cold-start 问题，不能用全局参数修。
- 后续主线应继续解决 shipwreck `2506/2501` 低估，同时给 `2507/2508/2407` 等 high-over maps 做保护。

## O-v3-024：map audit 将坏地图拆成样本问题、信息问题和系统性低估

新增可复跑审计：

```powershell
C:\Python313\python.exe .\scripts\summarize_v3_map_audit.py --top 12
```

当前 433 canonical 样本观察：

```text
2601 hidden    sessions=22 ready=86  mae=563274.2 bias=-379658.3 p90_cover=0.581 top3_abs=0.085
2506 shipwreck sessions=21 ready=71  mae=451709.5 bias=-350723.4 p90_cover=0.606 top3_abs=0.107
2501 shipwreck sessions=87 ready=310 mae=337374.6 bias=-145110.1 p90_cover=0.735 top3_abs=0.050
2507 shipwreck sessions=21 ready=74  mae=320540.5 bias=-15943.9  over_rate=0.622
2408 villa     sessions=12 ready=46  mae=333065.1 bias=-115943.1 flags=few_sessions
2503 shipwreck sessions=10 ready=37  mae=312308.2 top3_abs=0.284 flags=few_sessions+top3_heavy
```

结论：

- `2601/2506/2501` 不是少数极端窗口导致的坏指标；它们是 v3 当前系统性低估的主要对象。
- `2503/2505/2509/2408/2510` 样本少，先列 watchlist，不应据此做强 map-specific 参数。
- `2507/2407` 是高 over-rate 风险，不能和低估地图用同一个激进策略。
- public total 在多数差地图窗口中仍偏少，后续 sampler 不能依赖单一公开总格证据。

## O-v3-025：formal-only decision guard 降低低估且不污染 q6 指标

在 q6 diagnostic guard 不变的前提下，对 formal/total/tail-replacement decision value 启用 map-specific guard：

- `2501`：P75。
- `2506`：P75。
- `2601`：P85。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_live_monitor.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_family --top 10
C:\Python313\python.exe .\scripts\summarize_v3_map_audit.py --top 12
```

结果：

```text
43 passed
formal_p50_mae=301000.312
formal_p50_below_rate=0.522164
formal_p50_over_rate=0.477836
formal_p90_coverage=0.799218
q6_formal_p50_mae=281387.105
q6_formal_p50_below_rate=0.462842
q6_formal_p50_over_rate=0.535202
```

对比上一 checkpoint：

```text
formal_p50_mae 308876.090 -> 301000.312
q6_formal_p50_mae 281387.105 -> 281387.105
```

分片：

```text
hidden    formal_mae=473580.9 bias=-119930.6 q6_mae=486057.4
shipwreck formal_mae=321406.5 bias=-67943.6  q6_mae=299233.0
villa     formal_mae=249227.5 bias=-50832.8  q6_mae=228594.8
```

结论：

- formal-only guard 是有效的实战参考修正：降低整体低估，不改变 q6 standalone 诊断。
- `2506` 仍严重低估，下一步不能只靠 guard，需要 count/cell/value 条件 proposal 或更强 evidence likelihood。
- `2601` P85 让 below/over 接近平衡，但样本仍少，后续必须用新增 hidden 样本复核。

## O-v3-026：soft avg cells/value 接入后小幅改善，但不是 2506 主因

2026-06-05 将 soft 均格/均价证据接入 posterior likelihood：

- `q4/q5/q6_avg_cells`
- `q4/q5/q6_avg_value`
- `total_avg_cells`

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_evidence_registry.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_live_monitor.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_map_audit.py --top 8
```

结果：

```text
55 passed
formal_p50_mae=300553.241
formal_p50_below_rate=0.521512
formal_p50_over_rate=0.478488
formal_p90_coverage=0.797914
q6_formal_p50_mae=281273.209
q6_formal_p50_below_rate=0.460887
q6_formal_p50_over_rate=0.537158
```

对比上一 checkpoint：

```text
formal_p50_mae 301000.312 -> 300553.241
q6_formal_p50_mae 281387.105 -> 281273.209
```

分片观察：

- `2501`：formal MAE `333038.8 -> 331341.2`，小幅改善。
- `2506`：formal MAE `409121.6 -> 409096.7`，基本不动。
- `2601`：formal MAE `473580.9 -> 471295.4`，小幅改善。
- `2507`：formal MAE 不变，high-over 风险未加重。

结论：

- soft avg 接入是必要的 v3 输入补全，但收益有限。
- `2506` 的主因不是 soft avg 缺失，而是表先验/真实样本分布偏差或更深的先验建模问题。
- `random_*_avg_value` 暂不进入 formal 是合理的；其分组表现不稳定，后续需单独建抽样均值 likelihood。

## O-v3-027：archive raw truth 显示多张差地图高于表先验

新增可复跑校准报表：

```powershell
C:\Python313\python.exe .\scripts\summarize_v3_prior_archive_calibration.py --prior-trials 10000 --top 10
```

当前结果：

```text
2404 sessions=15 actual_p50=695440.0  prior_p50=356392.5 median_ratio=1.951
2506 sessions=21 actual_p50=1133996.0 prior_p50=615435.5 median_ratio=1.843 p90_ratio=1.908
2601 sessions=22 actual_p50=2250424.5 prior_p50=1384152.5 median_ratio=1.626
2501 sessions=87 actual_p50=910535.0  prior_p50=579558.0 median_ratio=1.571
2401 sessions=70 actual_p50=526176.5  prior_p50=371144.0 median_ratio=1.418
```

对照：

- `2507` actual/prior median ratio 约 `0.95`，不是所有 shipwreck 都偏高。
- 无放回抽样只能提升 median 约 `3-7%`，不能解释 `2506` 的 `1.84x` 偏差。
- item value 与 grid_view 外参一致，未发现价格表漂移。

结论：

- `2506/2501/2601/2404` 的系统性低估不能只靠窗口证据 likelihood 解决。
- v3 下一步需要显式 empirical prior/calibration layer，且必须按样本数和 high-over 风险 gate。
- 该 layer 不应直接从少样本地图学习强参数；`2506/2501/2401` 的样本量更适合先做 shadow 校准，`2404/2601` 需保守。

## O-v3-028：游戏源表与差地图样本审计

2026-06-05 复核本机游戏源文件：

- 源目录：`C:\xiangmuyunxing\steamapps\common\BidKing\BidKing_Data\StreamingAssets`
- 推理目录：`data/raw/tables`
- `Drop.txt / BidMap.txt / Item.txt / Hero.txt / Item_Type.txt / Constant.txt / BattleItem.txt / Cabinet.txt / Condition.txt / ItemRestock.txt / LevelUp.txt` 与本机游戏源 SHA256 全部一致。
- 游戏源 `fileVersion=300`，本地 raw 元信息已同步；关键表内容未发现落后。
- 用 `scripts/build_processed_data.py` 重建派生 JSON 后 git 仍干净，说明 committed processed 数据与当前 raw 表一致。
- `grid_view_v1.3.7` 外参对 `2506/2501/2601/2401/2507` 的 Q5/Q6 概率和价格中位数与本地白盒解析基本一致，未见足以解释大低估的价格/爆率漂移。

差地图样本和证据覆盖：

```text
2601 hidden sessions=22 ready=86/86 R1:22,R2:21,R3:21,R4:16,R5:6
  public_total=0.314 q6_exact=0.093 q6_floor=0.756 raw_p50=2250424 raw_p90=3099931
  formal_mae=471295.4 p90_cover=0.581

2506 shipwreck sessions=21 ready=71/73 R1:19,R2:20,R3:18,R4:10,R5:4
  public_total=0.085 q6_exact=0.000 q6_floor=0.282 raw_p50=1133996 raw_p90=2441715
  formal_mae=409096.7 bias=-246686.8 p90_cover=0.620

2501 shipwreck sessions=87 ready=310/311 R1:86,R2:79,R3:69,R4:54,R5:22
  public_total=0.055 q6_exact=0.000 q6_floor=0.381 raw_p50=910535 raw_p90=1604734
  formal_mae=331341.2 p90_cover=0.735

2401 villa sessions=70 ready=248/251 R1:67,R2:66,R3:61,R4:39,R5:15
  public_total=0.085 q6_exact=0.000 q6_floor=0.266 raw_p50=526176 raw_p90=1330116
  formal_mae=275890.1 p90_cover=0.806
```

补充验证：

```text
scripts/summarize_v3_evidence_coverage.py
  files=433 parsed_files=433 parse_errors=0 unknown=none pending=none

scripts/summarize_v3_constraints.py
  files=433 parsed_files=433 conflicts=0
```

结论：

- 当前差地图问题不是本机游戏表未更新，也不是本地 Drop/Item 与 grid_view 外参明显不一致。
- `2601 hidden` 样本只有 22 局，P90 coverage 很差，但不适合作为第一优先级强校准；后续按用户要求以 shipwreck/villa 为主。
- `2506` 是更明确的系统性低估：ready 窗口基本可用，但公开总格低、R4/R5 样本少、q6 exact 缺失，且 archive truth 明显高于表先验。
- `2501/2401` 样本量相对足，更适合用来验证 empirical prior/calibration layer 是否能改善低估而不制造 high-over。
- `2507` 仍应作为反例 guard：它不是系统性低估地图，不能把 shipwreck 家族整体无条件抬高。

## O-v3-029：calibration ratio 不能单独作为 P50 放大依据

2026-06-05 实现 empirical prior calibration shadow 后，先用 archive/prior median ratio + session gate 激活了 `2506/2501/2504/2401` 四张图。全量 evaluator 结果：

```text
v3_cal_active_rows=708
formal_p50_mae=300553.241
v3_cal_formal_p50_mae=309563.653
v3_cal_delta_formal_p50_mae=+9010.411
v3_cal_formal_p50_below_rate=0.438070
v3_cal_formal_p90_coverage=0.856584
```

分图结果显示：

```text
2506 mae 409096.7 -> 366187.0 delta=-42909.7
2501 mae 331341.2 -> 372896.4 delta=+41555.2
2504 mae 247366.8 -> 262630.6 delta=+15263.8
2401 mae 275890.1 -> 287102.2 delta=+11212.1
```

结论：

- archive/prior ratio 能说明表先验与真实样本分布有偏差，但不能单独证明当前 posterior P50 需要放大。
- `2501/2504/2401` 的 baseline bias 不够系统性，直接放大 P50 会转为过估。
- P90 coverage 提升不等于实战参考变好；P50 MAE 被带偏时必须收紧 gate。

修正后增加 baseline systemic-under gate，只激活 `2506`：

```text
v3_cal_active_rows=71
formal_p50_mae=300553.241
v3_cal_formal_p50_mae=298567.199
v3_cal_delta_formal_p50_mae=-1986.042
v3_cal_formal_p50_below_rate=0.510430
v3_cal_formal_p50_over_rate=0.489570
v3_cal_formal_p90_coverage=0.804433
```

map audit：

```text
2506 cal_active=1.0 mae=409096.7 cal_mae=366187.0 cal_delta=-42909.7
2501 cal_active=0.0
2507 cal_active=0.0
2601 cal_active=0.0
```

当前判断：

- `2506` calibration shadow 有实战参考价值，但仍为 in-sample shadow。
- hidden/少样本和非系统性低估地图只保留 watch-only。
- 下一步应做 holdout/new-live validation，并继续推进真正的 count/cell/value 条件 sampler，而不是扩大 map-level scale。

## O-v3-030：强化 q6 bucket likelihood 不是 count/cell/value sampler 的主解

2026-06-05 新增 `v3_ccv_*` shadow，用更低温度和更高 relative floor 对 summary-likelihood 下的 q6 bucket evidence 做 count/cell/value 条件化。默认触发收窄为：

- baseline 为 `summary_likelihood`。
- 存在 q6 bucket evidence。
- hidden `2601` 禁用。
- 无 q6 value evidence 时 value/formal 只透传 baseline。

全量 evaluator：

```text
metric_rows=1534
posterior_summary_likelihood=1021
q6_count_p50_mae=1.404
q6_cells_p50_mae=6.674
v3_ccv_likelihood_rows=329
v3_ccv_q6_count_p50_mae=1.418
v3_ccv_delta_q6_count_p50_mae=+0.013
v3_ccv_q6_cells_p50_mae=6.679
v3_ccv_delta_q6_cells_p50_mae=+0.005
```

地图审计：

```text
2506 ccv_count_delta=+0.03 ccv_cells_delta=+0.13
2501 ccv_count_delta=+0.02 ccv_cells_delta=+0.15
2509 ccv_count_delta=+0.12 ccv_cells_delta=+0.70
2503 ccv_count_delta=+0.03 ccv_cells_delta=+0.60
2502 ccv_count_delta=-0.01 ccv_cells_delta=-0.78
2408 ccv_count_delta=-0.07 ccv_cells_delta=-0.08
2508 ccv_count_delta=0.00 ccv_cells_delta=-0.11
```

结论：

- 该候选能改善少数地图的 cells MAE，但对整体和当前核心低估图 `2506` 都不是正收益。
- 继续调 likelihood 温度/relative floor 大概率会重复 v2 的调参陷阱：局部切片改善、整体 MAE 或核心地图恶化。
- 真正需要的是 residual/count-cell-value 生成模型：先由公共总格/总数、已知非 q6 下界、q6 桶证据决定 q6 count/cells 的后验，再基于 q6 count/cells 与地图/品质/形状分布估 value per cell。
- `v3_ccv_*` 保留为审计字段，用于对照未来 residual sampler；不应作为 promotion 候选。

## O-v3-031：residual sampler 结构有效，但默认全局激活仍会伤害 cells/value MAE

2026-06-05 新增 `v3_resid_*` shadow。它不再只强化 q6 bucket likelihood，而是把 q6 component 与非 q6 residual component 分开重组：

- q6 component：`q6_count/q6_cells/q6_value`。
- non-q6 component：总量减去 q6 后的 count/cells/value。
- residual evidence：session total exact/floor、known non-q6 floor、非 q6 bucket constraints。
- capacity guard：`q6_capacity = session_total_exact - non_q6_floor`，超出则排除。

全量 512-trial evaluator：

```text
v3_resid_likelihood_rows=976
q6_count_p50_mae=1.404 -> 1.403 delta=-0.001
q6_cells_p50_mae=6.674 -> 6.809 delta=+0.135
q6_value_p50_mae=374457.643 -> 379692.572 delta=+5234.929
```

128-trial smoke 显示正向：

```text
count delta=-0.030
cells delta=-0.107
value delta=-6794.229
```

512-trial map audit 显示分化：

```text
2506 resid_count_delta=-0.01 resid_cells_delta=0.00 resid_value_delta=-29406.8
2503 resid_count_delta=-0.16 resid_cells_delta=-0.55 resid_value_delta=-28308.7
2502 resid_count_delta=-0.05 resid_cells_delta=+0.08 resid_value_delta=-7559.5
2408 resid_count_delta=-0.02 resid_cells_delta=-0.20 resid_value_delta=+31381.4
2501 resid_count_delta=-0.01 resid_cells_delta=+0.15 resid_value_delta=+3111.5
2507 resid_count_delta=-0.03 resid_cells_delta=+0.37 resid_value_delta=+9908.4
```

结论：

- residual factorization 能抓到 `2506` 的 q6 raw value 低估方向，是比 ccv 更有用的结构候选。
- 但全局默认激活会牺牲整体 cells/value MAE；尤其 `2507` high-over 反例和 `2501` 非强系统性低估图不能无条件启用。
- 512 与 128 方向不一致，说明该 sampler 对 truth bank 方差/组件分布敏感；后续必须增加 gate 或稳定化，而不是直接把它放进 formal。
- 下一步应优先研究 `2506` gate：systemic-under + fallback + residual value improves + no cells degradation，再扩展到 holdout/new-live 验证。

## O-v3-032：2506 residual gate 不能只按地图启用，Aisha/Ethan 方向相反

2026-06-05 对 `v3_resid_gate_*` 做第一版 gated candidate：

- map gate：复用 `v3_cal_*` active，即当前只会考虑 `2506`。
- evidence gate：fallback residual。
- safety gate：q6 count/cells/value P50 不高于 baseline。

128-trial 初版 active 11 行，仍然恶化：

```text
v3_resid_gate_delta_q6_count_p50_mae=+0.003
v3_resid_gate_delta_q6_cells_p50_mae=+0.009
v3_resid_gate_delta_q6_value_p50_mae=+423.747
```

active row 审计：

```text
Aisha 2506: truth 8/38/1,313,498
  baseline 5/24/1,171,789
  residual 3/15/711,060
  结论：进一步压低，明显错误。

Ethan 2506: truth 2/8/330,562
  baseline 3/14/729,976
  residual 3/12/585,617
  结论：降低过估，有一定帮助但仍偏高。
```

结论：

- `2506` map-level systemic-under 与 q6 residual value 修正不是同一个问题。
- residual 降 value 对 Ethan 过估切片可能有用，但对 Aisha 低估切片危险。
- 没有 hero/evidence-specific gate 前，`v3_resid_gate_*` 不应 active。
- 当前默认改为 watch-only：`v3_resid_gate_active_rows=0`，保留 delta 字段用于后续 gate 设计。

下一步：

- evaluator/live 需要显式带出 hero 或等价 evidence profile，避免只能按 file name 审计。
- gate 需要区分 Aisha deep/tail-value 与 Ethan over-value/random/layout 场景。
- 对 Aisha 2506 的主要方向仍应是 tail/value sampler 或 formal calibration，而不是 residual 降 q6 raw value。

## O-v3-033：hero/profile 分片显示 residual 不是当前低估主修复

2026-06-05 新增 archive v3 行级 `hero/evidence_profile/information_density` 后，128-trial 分片审计显示：

```text
2506 map:
  sessions=21 ready=71/73 heroes=aisha:43,ethan:28
  mae=397195.2 bias=-270368.6 below=0.746479 p90_cover=0.619718
  public_total=0.084507 q6_floor=0.28169

aisha|2506:
  n=43 formal_mae=384517.7 bias=-283924.6 below=0.790698
  resid_count_delta=+0.13 resid_cells_delta=+0.31 resid_value_delta=+20915.1

ethan|2506:
  n=28 formal_mae=416664.2 bias=-249550.4 below=0.678571
  resid_count_delta=-0.10 resid_cells_delta=-1.49 resid_value_delta=-117480.2
```

解读：

- `ethan|2506` residual 对 q6 cells/value MAE 有正向信号，但 formal P50 仍明显低估，不能直接用 residual 作为正式 value 下修。
- `aisha|2506` residual 对 q6 count/cells/value 都伤害，直接证实 Aisha 方向应走 tail/value 上修或 calibration。
- 公开总格/总数证据在 2506 ready 窗口中只有约 8.45%，q6 floor 约 28.17%，说明很多低估仍是证据不足 + fallback 的组合，不是单纯 sampler 参数问题。

candidate table 额外显示：

```text
profile-level status_counts:
blocked_low_sample=349
blocked_residual_hurts=2
blocked_systemic_under=2
watch_only_neutral=1

hero-map status_counts:
blocked_low_sample=71
blocked_residual_hurts=3
blocked_systemic_under=8
blocked_under_value_downshift=1
watch_only_neutral=4
watch_only_over_correction_candidate=2
```

结论：

- profile 级别样本量仍不足以直接升级 gate。
- hero/map 级别可以用于发现候选，但必须回到 profile 和证据强度复核。
- 当前 v3 下一步应优先补“低估保护 + value 上修模型”，而不是把 residual 下修接入 formal。

## O-v3-034：hero/map 低估上修有信号，profile 粒度仍不足

2026-06-05 新增 `summarize_v3_underestimate_repair_candidates.py` 后，128-trial archive 审计显示：

```text
hero_map_id status_counts:
blocked_low_sample=71
blocked_not_systemic_under=10
watch_only_needs_evidence=4
watch_only_upshift_candidate=4

hero_map_evidence_profile status_counts:
blocked_low_sample=349
blocked_not_systemic_under=3
watch_only_needs_evidence=2
```

主要 hero/map 候选：

```text
aisha|2506 n=43 sessions=13 scale=1.046065
  formal_mae=384517.7 -> 363546.8 delta=-20970.9
  below=0.790698 -> 0.744186
  p90_cover=0.627907 -> 0.674419

ethan|2506 n=28 sessions=8 scale=1.045088
  formal_mae=416664.2 -> 404007.0 delta=-12657.1
  below=0.678571 -> 0.642857
  p90_cover=0.607143 -> 0.75

aisha|2601 n=38 sessions=11 scale=1.05287
  formal_mae=541556.3 -> 507628.8 delta=-33927.5

ethan|2509 n=30 sessions=8 scale=1.019059
  formal_mae=419243.9 -> 419127.9 delta=-116.0
```

解读：

- `2506` 的低估不是 residual 下修问题；小幅 upshift 更符合当前错误方向。
- `aisha|2506` 和 `ethan|2506` 都显示约 4.5% 的 bounded upshift 可改善 in-sample MAE，并降低 below rate。
- profile 级别仍太稀疏，`ethan|2506|shape`、`aisha|2506|item+shape` 等关键切片尚未达到稳定样本量。
- `aisha|2601` 是 hidden 候选，不能用当前结果证明 hidden 正式上修；hidden 仍需单独样本和 gate。

下一步：

- 把 bounded upshift 保留为 shadow candidate。
- 对新增实战样本跑相同候选表，观察 `2506` scale 是否稳定。
- promotion 前必须同时看 MAE、below、P90 coverage、over rate 与 pinball，防止通过上修修低估但制造极端过估。

## O-v3-035：v3_under shadow 全局轻微改善，2506 局部改善明显

2026-06-05 将 bounded upshift 候选接入 `v3_under_*` 后，128-trial archive evaluator 显示：

```text
v3_under_candidate_rows=101
formal_p50_mae=312938.992
v3_under_formal_p50_mae=312117.848
v3_under_delta_formal_p50_mae=-821.144
formal_p50_below_rate=0.510430 -> 0.508475
formal_p90_coverage=0.773794 -> 0.777705
```

map audit 中 `2506`：

```text
mae=397195.2
bias=-270368.6
below=0.746479
p90_cover=0.619718
under_candidate=1.0
under_delta=-17692.3
under_below=0.704225
under_p90_cover=0.704225
```

解读：

- 全局收益小，说明 hero/map 上修不应全局 promotion。
- `2506` 局部收益明显，符合当前低估主问题。
- `ethan|2509` 虽然 candidate_rate 高，但 `under_delta` 很小，应当继续 watch-only。
- hidden `2601` 仍未生成 candidate，上修 entry 只记录 needs-evidence。

下一步：

- 新增实战样本后优先复跑 `evaluate_fatbeans_v3_samples.py` 与 map/hero slice，观察 `v3_under_delta_formal_p50_mae` 是否稳定。
- 若 `2506` holdout 仍正向，再考虑把 entry 从 watch-only candidate 升级到更严格的 calibration candidate；promotion 前仍保持 `affects_bid=false`。

## O-v3-036：当前样本足够诊断，但不足以正式推广 Ethan/profile 上修

2026-06-05 用 `summarize_v3_underestimate_holdout.py` 做 5-fold session holdout：

```text
rows=1534 sessions=433
default hero_map_id holdout candidate_rows=61 candidate_sessions=18
mae=312938.992 -> 312068.688 delta=-870.304
below=0.510430 -> 0.509778
p90_cover=0.773794 -> 0.775750
```

默认 `min_sessions=8` 的候选：

```text
aisha|2506 rows=43 sessions=13 delta=-22005.497 below=0.790698 -> 0.767442 p90_cover=0.627907 -> 0.651163
aisha|2601 rows=38 sessions=11 delta=-10231.829 below=0.684211 -> 0.684211 p90_cover=0.315789 -> 0.368421
```

敏感性分析 `min_sessions=6`：

```text
ethan|2506 rows=28 sessions=8 delta=-10401.162 below=0.678571 -> 0.642857
ethan|2509 rows=30 sessions=8 delta=1701.474
```

profile 粒度：

```text
hero_map_evidence_profile candidate_rows=0
status_counts=blocked_low_sample:1524,blocked_not_systemic_under:14,watch_only_needs_evidence:7
```

解读：

- 当前真实样本量足够支撑 v3 设计、archive/live shadow 链路、Aisha 2506 低估修复方向判断。
- Ethan 2506 当前只有 `28` ready windows / `8` sessions，只有放宽阈值才显正向，因此不能正式升级。
- profile 级样本明显不足，不能用来承载正式规则；公开总格、shape/layout、q6 floor 等证据仍应进入 profile，但 promotion 需要更多样本。
- 不建议盲目追求固定总数 `400`；更有价值的是补足高风险切片。优先新增 `ethan|2506`，其次 `aisha|2506` holdout 确认；hidden 继续单独看。

## O-v3-037：CCV 全局不稳定，2506 不适合直接用 count/cell 下移修复

2026-06-05 新增 `summarize_v3_ccv_profile_candidates.py` 后，128-trial archive 显示：

```text
v3_ccv_likelihood_rows=347
v3_ccv_q6_count_p50_mae=1.440 delta=-0.001
v3_ccv_q6_cells_p50_mae=7.008 delta=+0.165
```

`hero_map_id` gate：

```text
status_counts=blocked_ccv_hurts:5,blocked_low_ccv_activity:8,blocked_low_sample:71,blocked_under_count_cell_downshift:2,watch_only_count_cell_candidate:1,watch_only_needs_evidence:1,watch_only_neutral:1
```

主要切片：

```text
ethan|2502 candidate n=36 sessions=9 ccv_rate=0.444444 count_delta=-0.11 cells_delta=-1.89 value_delta=-61348.8 formal_delta=-2991.4
aisha|2409 needs_evidence n=32 sessions=9 ccv_rate=0.375 count_delta=-0.06 cells_delta=+0.01 formal_delta=-36155.1 public_total=0.0
ethan|2506 blocked_under_count_cell_downshift n=28 sessions=8 count_delta=-0.07 cells_delta=-1.22 count_pred_delta=-0.07 cells_pred_delta=-2.22
```

profile 粒度：

```text
status_counts=blocked_ccv_hurts:2,blocked_low_ccv_activity:3,blocked_low_sample:349
```

解读：

- 当前 CCV 更像局部诊断工具，不是稳定的 formal sampler。
- `ethan|2506` 的 count/cells MAE 改善容易误导；它 formal 仍低估，继续下移 q6 count/cells 与用户实战低估问题方向相冲突。
- `ethan|2502` 是目前更适合研究条件 sampler 的正向对象，因为 count/cells 同向改善且 evidence 比较充分。
- `aisha|2409` 提示公开总格覆盖仍是关键证据缺口，不能把缺证据的改善当作结构性成功。

## O-v3-038：archive/live v3 链路已统一，后续字段漂移风险下降

2026-06-05 新增 `estimate_shadow_pipeline()` 后，archive evaluator 和 live monitor 均复用同一 v3 shadow 链路。

验证结果：

```text
focused pipeline/archive/live tests: 33 passed
v3 core/live tests: 83 passed
32-trial archive smoke: windows=1551 ready=1534 constraint_conflict=0 parse_errors=0 constraint_ok=True
```

代码搜索确认：

```text
evaluate_fatbeans_v3_samples.py / live/monitor.py 不再直接调用 posterior/CCV/residual/cal/under 的单步函数链。
```

解读：

- v3 后续改 sampler、gate、entry 或 flat field 时，有单一接入点可测。
- 这不是精度提升本身，但它是避免 archive 指标和 live 实战展示不一致的必要结构改动。
- 当前仍保持 shadow-only，formal/live 主决策未切换。

## O-v3-039：2506 有 tail/q6-tail review 信号，但不是 formal 口径替换

2026-06-05 使用 `summarize_v3_tail_value_candidates.py` 对 128-trial archive 审计：

```text
status_counts=blocked_low_sample:71,blocked_no_tail_signal:9,blocked_tail_estimate_hurts:1,watch_only_needs_evidence:2,watch_only_neutral:1,watch_only_q6_tail_value_candidate:4,watch_only_tail_value_candidate:1
```

重点切片：

```text
aisha|2506 n=43 sessions=13 tail_rate=0.162791 tail_delta=-11433.7 tail_p90_under=0.372093 q6_tail_delta=-9603.3 q6_tail_p90_under=0.325581
ethan|2506 n=28 sessions=8 tail_rate=0.142857 tail_delta=-2096.4 tail_p90_under=0.392857 q6_tail_delta=-8614.5 q6_tail_p90_under=0.392857
ethan|2502 n=36 sessions=9 tail_rate=0.222222 tail_delta=-418.3 tail_p90_under=0.305556
ethan|2508 n=28 sessions=9 tail_delta=32201.7 q6_tail_delta=28270.1
```

profile 粒度：

```text
status_counts=blocked_low_sample:349,blocked_no_tail_signal:4,watch_only_needs_evidence:1
```

解读：

- `2506` 的低估里有 tail/q6-tail audit gap，P90 tail under rate 偏高。
- 该信号解释“为什么 P90 可以看长尾”，但不代表要把 tail replacement 接正式出价。
- `ethan|2508` 证明 tail estimate 也会伤害，需要 guard。
- profile 粒度仍不足，后续不能按细 profile 直接 promotion。

## O-v3-040：readiness 总审计显示 v3 仍未达到 formal 条件

2026-06-05 使用 `summarize_v3_promotion_readiness.py --posterior-trials 128`：

```text
overall_status=not_ready blocked_gates=4
windows=1551 ready=1534
formal_mae=312938.992 formal_below=0.51043 formal_p90_cover=0.773794
under_delta=-821.144 ccv_cells_delta=0.165 resid_gate_active=0
```

gate 结果：

```text
archive_data_quality=watch
shared_shadow_pipeline=pass
formal_baseline_metrics=blocked
underestimate_repair_holdout=watch
ccv_sampler=blocked
tail_value_review=watch
residual_gate=blocked
profile_sample_depth=blocked
v2_archive_readiness=pending
```

解读：

- shared pipeline 已经可用，但 v3 formal 尚未 ready。
- 当前可推进项是 `2506` bounded upshift/tail-value shadow validation。
- 当前禁止项是全局 CCV、residual formal、tail replacement formal。
- profile 级 promotion 需要更多定向样本或更强证据。

## O-v3-041：CCV candidate 的全量切片收益未通过 session holdout

2026-06-05 使用 `summarize_v3_ccv_holdout.py` 对 128-trial archive 审计。

默认 hero/map holdout：

```text
group_field=hero_map_id folds=5 min_sessions=8
rows=1534 sessions=433 candidate_rows=2 candidate_sessions=1
count_delta=0.0 cells_delta=0.0 q6_formal_delta=0.0
candidate_only rows=2 sessions=1 groups=ethan|2502
```

默认 profile holdout：

```text
group_field=hero_map_evidence_profile folds=5 min_sessions=8
candidate_rows=0 candidate_sessions=0
status_counts=blocked_ccv_hurts:9,blocked_low_ccv_activity:12,blocked_low_sample:1524
```

放宽阈值灵敏度：

```text
group_field=hero_map_id min_sessions=6
candidate_rows=14 candidate_sessions=4
cells_delta=+0.004 q6_formal_delta=+84.8
candidate_only cells_delta=+0.4 q6_formal_delta=+9288.7
groups=aisha|2504,aisha|2508,ethan|2502
```

解读：

- CCV 的全量 `ethan|2502` 候选目前只是 watch-only，holdout 没有证明实际收益。
- 放宽 session 门槛会让 candidate_only 变差，说明样本不足不是唯一问题，候选泛化本身不稳。
- profile 粒度仍然完全不足，不支持 profile-level CCV promotion。
- CCV 不应作为 v3 近期 formal 化方向；下一步应研究证据条件 likelihood，让公开总格、q6 floor、value evidence 决定 q6 分布，而不是直接启用当前 CCV 后验。

## O-v3-042：tail/value holdout 支持 Aisha 2506 review，但暴露 Ethan 2601 hurt guard

2026-06-05 使用 `summarize_v3_tail_value_holdout.py` 对 128-trial archive 审计。

hero/map holdout：

```text
rows=1534 sessions=433 candidate_rows=122 candidate_sessions=36
tail_delta=-57.1 q6_tail_delta=-329.6
candidate_only tail_delta=-718.0 q6_tail_delta=-4144.4
groups=aisha|2401,aisha|2506,aisha|2601,ethan|2502,ethan|2601
```

重点 group：

```text
aisha|2506 rows=43 sessions=13 tail_delta=-7935.2 q6_tail_delta=-5562.9
aisha|2601 rows=38 sessions=11 tail_delta=-7367.3 q6_tail_delta=-32770.1
ethan|2601 rows=40 sessions=11 tail_delta=+13339.4 q6_tail_delta=+24471.3
```

profile holdout：

```text
candidate_rows=0 candidate_sessions=0
status_counts=blocked_low_sample:1524,blocked_no_tail_signal:15,watch_only_needs_evidence:6
```

readiness 接入后：

```text
overall_status=not_ready blocked_gates=4
ccv_sampler=blocked
tail_value_review=watch
tail_holdout_q6_delta=-4144.4
next_actions=continue 2506 bounded upshift/tail-value shadow validation | collect targeted profile samples before profile-level promotion | keep tail-hurts guard before any tail/value sampler | redesign CCV likelihood; current holdout is not promotion-ready
```

解读：

- tail/q6-tail review 是当前比 CCV 更有实战解释力的低估诊断线。
- `aisha|2506` 的正向 holdout 支持继续做 review/sampler 设计，但不能直接接 formal。
- `ethan|2601` 必须作为 hurt guard；否则 tail/value 会把一部分 hidden/long-tail 场景带偏。
- profile 样本仍不够，当前只能做 hero/map 级观察和 targeted sampling 建议。

## O-v3-043：tail/value review 已进入 archive/live 共享 shadow 字段

2026-06-05 新增 `v3_tail_review_*` pipeline namespace 后，archive evaluator 和 live monitor 都会输出 tail review 的 candidate/hurt/status 字段。

archive 128-trial：

```text
windows=1551 ready=1534 parse_errors=0
v3_tail_review_candidate_rows=43
v3_tail_review_hurt_guard_rows=40
v3_tail_review_active_rows=0
```

readiness 128-trial：

```text
overall_status=not_ready blocked_gates=4
tail_review_candidate_rows=43
tail_review_hurt_guard_rows=40
tail_holdout_q6_delta=-4144.4
```

entry 表解读：

```text
aisha|2506 candidate rows=43
ethan|2601 hurt guard rows=40
aisha|2601 marked needs_evidence, not candidate, because hidden still needs separate validation
```

解读：

- 现在 live 归档能区分 “Aisha 2506 tail review candidate” 与 “Ethan 2601 tail hurt guard”。
- 这解决的是审计/诊断一致性，不是正式精度提升；formal 估值仍未切换。
- `v3_tail_review_active_rows=0` 证明该 namespace 未进入正式出价。
- 后续 tail sampler 可以在这个 namespace 下迭代，不必再直接挤进 `v3_post_*`。

## O-v3-044：组合 holdout 证明 hidden guard 必须前置，Aisha 2506 仍是主候选

2026-06-05 新增 guarded tail/under holdout 后，先跑未加 hidden guard 的版本发现：

```text
under_rows=61 tail_rows=122 hurt_rows=11
candidate_only rows=122
tail_under_formal_delta=-10942.999
tail_under_applied_hurts=ethan|2601
group=ethan|2601 tail_rows=31 hurt_rows=9 tail_delta=+13339.4 q6_tail_delta=+24471.3
```

解读：

- 总体 formal delta 看起来正向，但 `ethan|2601` 仍在部分训练折被误放为 tail candidate。
- 这说明 “总体改善” 会掩盖 applied hurt group，不能作为 promotion 依据。
- in-sample tail candidate 表对 `ethan|2601` 会误判为正向，session holdout 才能暴露伤害。

加入 `weak_tail_under_context` 与 hidden `260x` guard 后：

```text
v3_under_candidate_rows=43
under_rows=37 tail_rows=39 hurt_rows=11
formal_delta=-616.842
below=0.51043 -> 0.509778
p90_cover=0.773794 -> 0.774446
p90_extreme=0.313559 -> 0.313559
candidate_only rows=39
under_groups=aisha|2506
tail_groups=aisha|2506,ethan|2502
candidate_only formal_delta=-24262.471
q6_tail_delta=-6133.4
group=ethan|2601 under_rows=0 tail_rows=0 hurt_rows=9
```

解读：

- hidden guard 消除了 `ethan|2601` applied hurt，但也把全局收益压回很小。
- 同步 under shadow entry 表后，archive/live `v3_under_candidate_rows` 从 101 降到 43；更保守，但避免 Ethan 2506/2509 这类 holdout 不稳切片误导实时审计。
- `aisha|2506` 的局部收益仍稳定：formal/q6/tail/q6-tail 都同向改善。
- `ethan|2502` 目前只是 tail candidate 名义，holdout delta 为 0，不足以支持升级。
- v3 离正式可用还不是“差一个参数”：需要扩大有效覆盖并修复 formal baseline/CCV/profile depth。

下一步重点：

- 继续围绕 `aisha|2506` 做 bounded sampler 设计。
- hidden 单独观察，不和 shipwreck/villa 合并升级。
- readiness 必须继续输出 `tail_under_applied_hurts`，防止候选总体改善掩盖局部伤害。

## O-v3-045：CCV 的主要问题是分层不稳定，map-level 会暴露 applied hurt

2026-06-05 新增 CCV layer audit 后，128-trial archive 对比：

```text
hero_map_id:
candidate_rows=2
groups=ethan|2502
count_delta=0.0 cells_delta=0.0 formal_delta=0.0
applied_hurts=

map_id:
candidate_rows=64
groups=2502,2503,2504
count_delta=+0.062 cells_delta=+0.053 formal_delta=+21205.4
applied_hurts=2503

map_family:
candidate_rows=0

hero_map_evidence_profile:
candidate_rows=0
```

解读：

- 只看 `hero_map_id` 会低估 CCV 风险，因为候选太窄且几乎没有效果。
- `map_id` 层显示 CCV 训练折会把 `2503/2504` 误放进 candidate，holdout 后 `2503` 明显 hurt。
- `map_family` 与 profile 层没有可用 candidate，说明样本层级和泛化层级都还没准备好。
- 当前 CCV 不能靠“先接 shadow candidate 再看”推进；需要重做 likelihood 或新增明确 layer gate。

## O-v3-046：关闭 CCV count/cell tail guard 会增加低估风险，不能修复 map-level hurt

2026-06-05 新增 `summarize_v3_ccv_guard_sensitivity.py`，用同一 archive 对比默认 CCV 与 `count_cell_tail_guard=off`。

128-trial 结果：

```text
default:
ccv_likelihood_rows=347
count_delta=-0.001
cells_delta=+0.165
count_mae=1.44
cells_mae=7.008

count_cell_tail_guard=off:
ccv_likelihood_rows=347
count_delta=+0.041
cells_delta=+0.225
count_mae=1.482
cells_mae=7.068

paired_diff:
rows=1534
count_changed=108
count_pred_delta=-0.075
count_mae_delta=+0.042
count_below_delta=+0.025424
count_p90_cover_delta=-0.029335
cells_changed=146
cells_pred_delta=-0.368
cells_mae_delta=+0.060
cells_below_delta=+0.019557
cells_p90_cover_delta=-0.024120
```

分层结果：

```text
default map_id applied_hurts=2503 candidate_rows=64
count_cell_tail_guard=off map_id applied_hurts=2502 candidate_rows=44 cells_delta=+1.136
```

解读：

- 关闭 guard 后预测整体下移，但不是“更准确”；q6 count/cells MAE 变差，below-rate 上升，P90 coverage 下降。
- 默认 hurt 的 `2503` 没有被真正解决，只是风险切换到 `2502`。
- 这说明 CCV 的当前核心问题是 likelihood/candidate layer 不稳，而不是 p50 tail guard 单点参数过强。

下一步重点：

- 不再把 `count_cell_tail_guard` 作为调参修复方向。
- 设计新的 CCV likelihood 时，需要让证据决定 q6 cells/count 分布移动，并在 map/profile layer 同时过 holdout。

## O-v3-047：CCV 的主要风险是 p50 移动方向不稳定

2026-06-05 新增 `summarize_v3_ccv_direction_audit.py` 后，128-trial archive 显示：

```text
map_id:
blocked_directional_hurt=20
blocked_low_movement=13
watch_directional_candidate=9

evidence_profile_key:
blocked_directional_hurt=11
blocked_low_movement=7
blocked_low_sample=44
watch_directional_candidate=7
watch_neutral=1
```

关键切片：

```text
2503 q6_count changed=15 helped=4 hurt=11 hurt_rate=0.733333 directional_error=0.466667 mae_delta=+0.127
2503 q6_cells changed=20 helped=9 hurt=11 hurt_rate=0.55 directional_error=0.25 mae_delta=+0.438
2502 q6_count changed=13 helped=10 hurt=3 hurt_rate=0.230769 mae_delta=-0.095
2502 q6_cells changed=25 helped=13 hurt=9 hurt_rate=0.36 mae_delta=-0.708
```

证据 profile：

```text
public:total+item+shape+layout q6_count changed=8 helped=0 hurt=8 hurt_rate=1.0 directional_error=0.75 mae_delta=+0.152
public:total+item+shape+layout q6_cells changed=12 helped=3 hurt=9 hurt_rate=0.75 mae_delta=+0.505
public:total+item+shape q6_count changed=10 helped=7 hurt=3 mae_delta=-0.067
```

解读：

- `2502` 的 CCV 方向性确实相对正向，但不能外推到同 family 或同 shipwreck。
- `2503` 的错误方向足以解释 map-level holdout applied hurt。
- “公开总格 + item + shape + layout”并不自动可靠；在当前样本里它反而是明确 blocked profile。
- 后续 CCV 重做不能只看有无公开信息，而要看公开信息与 q6 floor、非 q6 capacity、道具证据之间是否形成同向约束。

## O-v3-048：CCV 方向候选在 session holdout 上仍不够稳定

2026-06-05 新增 `summarize_v3_ccv_direction_holdout.py` 后，用训练折 direction audit 选择 candidate，再在验证折应用。128-trial archive 结果：

```text
map_id:
overall_status=blocked_holdout_directional_hurt
candidate_rows=438
candidate_delta=+0.168
candidate_hurt_rate=0.086758
candidate_directional_error=0.06621
applied_hurts=q6_cells:2502,q6_cells:2506,q6_count:2501,q6_count:2409,q6_count:2506

evidence_profile_key:
overall_status=watch
candidate_rows=348
candidate_delta=-0.057
candidate_hurt_rate=0.051724
candidate_directional_error=0.025862
applied_hurts=
```

分量观察：

```text
map_id q6_cells candidate_delta=+0.567
map_id q6_count candidate_delta=+0.045
profile q6_cells candidate_delta=-0.011
profile q6_count candidate_delta=-0.069
```

解读：

- direction audit 可以解释 CCV 风险，但不能直接生成可靠修正规则。
- map-level 方向选择仍会在 holdout 中把 q6 cells/count 往错误方向推。
- profile-level q6 count 有弱改善，但 q6 cells 几乎无实质收益；这不足以支撑正式估值。
- 当前 readiness blocked 是正确的，下一步要做条件 likelihood/组件分解，而不是继续堆叠候选 gate。

## O-v3-049：component likelihood 全局正向，但方向性仍不过关

2026-06-05 新增可选 `v3_ccvc_` 后，128-trial archive 初步结果：

```text
v3_ccvc_component_likelihood_rows=1050
v3_ccvc_delta_q6_count_p50_mae=-0.033
v3_ccvc_delta_q6_cells_p50_mae=-0.168
v3_ccvc_delta_q6_value_p50_mae=-6864.3
```

对比旧 `v3_ccv_`：

```text
v3_ccv_likelihood_rows=347
v3_ccv_delta_q6_count_p50_mae=-0.001
v3_ccv_delta_q6_cells_p50_mae=+0.165
```

方向性审计：

```text
map_id:
blocked_directional_hurt=24
blocked_low_movement=7
watch_directional_candidate=11

evidence_profile_key:
blocked_directional_hurt=16
blocked_low_movement=1
blocked_low_sample=44
watch_directional_candidate=9
```

解读：

- `v3_ccvc_` 的全局 MAE 比旧 CCV 明显更合理，说明组件化是正确方向。
- 但 map/profile 的 changed rows hurt rate 仍高；例如 `public:random_avg+...`、`item+shape`、`public:total+item+shape` 仍会把一部分窗口推向错误方向。
- `public:total+item+shape+layout` 在 component skeleton 下 q6 cells MAE 有改善，但 q6 count 仍有方向性问题，不能简单放行。
- 下一步重点是对 component likelihood 做 session holdout 与 evidence contribution audit，而不是把全局均值改善直接接 formal。

## O-v3-050：v3_ccvc_ holdout 显示 q6_cells 是主要风险源

2026-06-05 将 direction holdout 参数化到 `v3_ccvc_` 后，128-trial archive 结果：

```text
map_id q6_count+q6_cells:
candidate_rows=793
candidate_delta=+0.097
q6_count delta=-0.017
q6_cells delta=+0.354

evidence_profile_key q6_count+q6_cells:
candidate_rows=628
candidate_delta=-0.030
q6_count delta=-0.012
q6_cells delta=-0.092
```

主要 applied hurt：

```text
map q6_cells:2505,2408,2508,2405,2502,2403,2404,2410
profile q6_cells:public:total+item+shape,public:random_avg+shape
profile q6_count:item+shape+layout,public:total+item+shape,public:max_item_cells+item+shape
```

严格 q6_count profile gate：

```text
candidate_rows=99
candidate_delta=+0.081
```

解读：

- map 层 q6_cells 不能 promotion；它是 component likelihood 当前最明显的反向来源。
- profile 层 q6_count 是弱正向，但不能用简单 gate 放行。
- `public:total` 与 `random_avg` 同时出现时不自动可靠；需要拆它们分别对 count 和 cells 的贡献。
- 下一步应做 evidence contribution audit，识别哪些证据组合应提高/降低 count，哪些应完全不动 cells。

## O-v3-051：CCVC contribution 显示 count 与 cells 不能共用 gate

2026-06-05 新增 `summarize_v3_ccvc_evidence_contribution.py` 后，128-trial archive 显示：

```text
q6_count overall:
delta=-0.033
pred_delta=+0.139
hurt_rate=0.443730
directional_error=0.292605

q6_cells overall:
delta=-0.168
pred_delta=-0.074
hurt_rate=0.495177
directional_error=0.428725
```

q6_count 较有用的特征：

```text
unassigned_anchor delta=-0.115 present_minus_absent=-0.127 hurt_rate=0.327485
tool_category delta=-0.093 present_minus_absent=-0.072 hurt_rate=0.275862
q6_floor delta=-0.052 present_minus_absent=-0.030 hurt_rate=0.438596
public_total delta=-0.040 present_minus_absent=-0.009 hurt_rate=0.421875
```

q6_cells 风险特征：

```text
public_max_item_cells hurt_rate=0.653061 present_minus_absent=+0.129
tool_category hurt_rate=0.600000 present_minus_absent=+0.172
item_anchor hurt_rate=0.520803 present_minus_absent=+0.278
public_random_avg hurt_rate=0.516129 present_minus_absent=-0.265
public_total hurt_rate=0.447236 present_minus_absent=-0.745
```

解读：

- `public_total` 对 q6_cells 的 MAE 改善很大，但 hurt rate 仍接近 blocker，不能直接放行。
- `tool_category` 对 q6_count 有贡献，但对 q6_cells 是风险项。
- `item_anchor`/`shape_anchor` 不能被解释为 q6 cells 可靠证据；它们更像 q6 component 候选空间约束，而不是 cells p50 移动方向。
- 下一步应在 CCVC likelihood 中输出 count/cells 分离 diagnostics，并让 cells movement 需要更强的 total/capacity consistency。

## O-v3-052：freeze-cells 能隔离 cells 风险，但 q6_count 仍未达到 promotion

2026-06-05 对 `v3_ccvc_` 增加 `--ccv-component-freeze-cells` 后，128-trial archive 显示：

```text
archive:
v3_ccvc_delta_q6_count_p50_mae=-0.033
v3_ccvc_delta_q6_cells_p50_mae=0.000
v3_ccvc_delta_q6_value_p50_mae=-6864.3

profile holdout:
overall_status=blocked_holdout_directional_hurt
q6_cells candidate_rows=0
q6_count candidate_rows=490
q6_count delta=-0.012
q6_count hurt_rate=0.083673
q6_count directional_error=0.048980
```

解读：

- q6_cells 已确认是可冻结的独立风险面；冻结后不会再把 cells p50 推错。
- q6_count 的平均改善仍然存在，但有多个 evidence profile 在 holdout 下伤害明显。
- 这说明 v3 需要的是 profile-aware count likelihood/gate，而不是继续放宽固定 prior 或整体调权重。
- 正式可用前至少还需要：count movement 稳定、低估风险下降、P90 over 控制、live shadow 与 archive 一致。

## O-v3-053：q6_count policy matrix 显示 down_only 可控但不解决低估

2026-06-05 新增 movement-policy matrix 后，128-trial 结果显示所有基础组合仍 blocked：

```text
evidence_profile_key all       delta=-0.012 blocked
evidence_profile_key up_only   delta=-0.004 blocked
evidence_profile_key down_only delta=-0.041 blocked by item+shape+layout
map_id all                     delta=-0.017 blocked by 2508,2405,2506,2401
map_id up_only                 delta=-0.020 blocked by 2508,2405
map_id down_only               delta=+0.020 blocked by 2506,2401
map_id,evidence_profile_key    candidate_rows low and harmful
```

提高 `min_windows=30` 后，128-trial 的 profile down_only 可过，但 256-trial 复验显示 bare `shape` 不稳定：

```text
256-trial profile down_only min_windows=30:
status=blocked_holdout_directional_hurt
applied_hurts=q6_count:shape
```

排除 bare `shape` 后，256-trial 可过：

```text
status=watch
candidate_rows=157
delta=-0.025
hurt_rate=0.025478
directional_error=0.006369
baseline_below=0.401274
candidate_below=0.420382
```

解读：

- sampler trials 会改变部分 profile gate 结论；promotion 必须有 stability check。
- `down_only` 降低 MAE，但增加 below-rate，和“实战低估修复”目标相冲突。
- `tool:category+item+shape` 与 `public:max_item_cells+item+shape` 比 bare `shape` 更稳定，但仍只能作为 shadow。
- 下一步应转向 q6 value/cells 的公共总格、容量一致性和 value sampler，而不是继续把 q6_count 下修。

## O-v3-054：residual q6-value under holdout 暴露 value sampler 不稳定

2026-06-05 新增 residual q6-value under holdout 后，archive 结果：

```text
128-trial evidence_profile:
overall_status=blocked_holdout_hurt
candidate_groups=public:total+item+shape,public:total+shape
q6_value_delta=+15187.3
applied_hurts=public:total+item+shape

256-trial evidence_profile:
overall_status=blocked_holdout_hurt
candidate_groups=public:total+item+shape,public:total+shape
q6_value_delta=-17189.8
applied_hurts=public:total+shape

256-trial min_windows=30:
status=watch
candidate_groups=public:total+item+shape
q6_value_delta=-23608.6

128-trial min_windows=30:
status=blocked_holdout_hurt
candidate_groups=public:total+item+shape
q6_value_delta=+15631.3

128-trial seed=1 min_windows=30:
candidate_rows=0
```

解读：

- `public:total+item+shape` 是最值得继续研究的低估 profile，但当前 q6_value residual sampler 不稳定。
- `public:total+shape` 在 256-trial holdout 下明确伤害 q6_value。
- 当前 residual report 是 formal passthrough，所以 formal_delta=0 不能说明正式估值改善。
- 低估修复下一步必须做 formal/value candidate：把 q6 value/cells 的上修如何影响 formal decision 作为显式候选，而不是只看 component shadow。

## O-v3-055：formal delta mapping 证明现有 component shadow 不足以修复 formal

2026-06-05 新增 formal-value delta holdout 后，archive 显示：

```text
v3_resid_:
candidate_rows=0

v3_ccvc_ freeze-cells:
candidate_rows=0

v3_ccv_ evidence_profile 128-trial:
candidate_groups=item+shape+layout
formal_delta=+6633.5
q6_formal_delta=+8512.5
candidate_below=0.583333
applied_hurts=item+shape+layout

v3_ccv_ evidence_profile 256-trial:
candidate_rows=0

v3_ccv_ map_id 128-trial:
candidate_groups=2502
formal_delta=-1015.2
candidate_over=0.75
applied_hurts=2502
```

解读：

- `v3_resid_` 和 `v3_ccvc_` 只动 component value/count/cells，不动 q6 formal，因此不能用 delta mapping 修 formal。
- `v3_ccv_` 有 q6 formal delta，但 profile 伤害、map 高过估，无法 promotion。
- high-over guard 是必要的；否则 `2502` 会被小幅 MAE 改善误放行。
- 下一步如果做 formal/value sampler，需要直接建模 formal candidate，而不是依赖现有 component shadow 的附带字段。

## O-v3-056：0605 manual 样本可解析，但 252x 活动沉船缺少本地 drop 表

2026-06-06 对 `data/samples/fatbeans_manual_inbox` 的 23 个新增样本复核：

```text
manual_files=23
by_family: villa=8, shipwreck=15
by_map:
2401=2, 2404=2, 2405=1, 2407=1, 2408=1, 2410=1,
2521=5, 2522=1, 2524=3, 2526=2, 2528=1, 2529=3
by_hero:
aisha=10, ethan=9, gabriela=1, sophie=1, tatiana=1, wuqilin=1
```

解析修复后：

```text
manifest archive + manual inbox:
files=456 parsed_files=456 parse_errors=0
valid_files=439 mixed_files=17 invalid_files=0
ready_windows=1618

manual inbox v3 evaluator:
windows=84 ready=84
prior_ready=26 truth_ready=84 decision_truth_ready=84
```

解读：

- 旧 parser 的 parse error 不是样本废弃问题，而是 archive parser 没按 TCP flow 重建 frame。
- 8 个别墅样本已有 prior，可进入普通样本使用。
- 15 个沉船活动样本为 252x，当前本地 `maps.json` / `BidMap.txt` / `Drop.txt` 缺少对应地图与活动爆率。
- 252x 样本现在能提供 window/truth 证据，但不能证明 v3 对普通沉船 prior 的准确性。

## O-v3-057：0605 样本已分层归档，默认校准与活动鲁棒性路径分离

2026-06-06 已将 manual inbox 清空并分层归档：

```text
main archive:
path=data/samples/fatbeans
files=441 parsed_files=441 parse_errors=0
valid_files=424 mixed_files=17
ready_windows=1560 no_state_windows=17

activity shipwreck cohort:
path=data/samples/fatbeans_activity_20260605_shipwreck
files=15 parsed_files=15 parse_errors=0
valid_files=15 mixed_files=0
ready_windows=58 no_state_windows=0
```

v3 evaluator 口径：

```text
default path:
windows=1577 ready=1560 parse_errors=0
prior_ready=1560 truth_ready=1577 decision_truth_ready=1560

activity path:
windows=58 ready=58 parse_errors=0
prior_ready=0 truth_ready=58 decision_truth_ready=58
```

解读：

- 8 个 24xx 别墅样本已进入默认主库，后续普通校准自动使用。
- 15 个 252x 沉船活动样本保留在独立目录，后续需要显式传路径。
- `prior_ready=0` 是预期结果：本地表缺少 252x 活动 drop prior，v3 不应把它们映射到旧 250x 普通沉船先验。
- 该 cohort 后续适合做鲁棒性测试：旧表缺失/活动机制变化时，模型应暴露 prior 缺口并保持保守。

## O-v3-058：prior robustness 能区分普通 archive、弱 fallback 与 252x 活动 cohort

2026-06-06 接入 `v3_robust_*` 后复跑：

```text
activity cohort 64-trial:
windows=58 ready=58
prior_ready=0
robust_prior_usable=0
robust_prior_trusted=0
robust_activity_candidate=58
posterior_ready=0 posterior_no_match=58

main archive 64-trial:
windows=1577 ready=1560 no_state=17
prior_ready=1560
robust_prior_usable=1560
robust_prior_trusted=359
robust_activity_candidate=0
robust_prior_stressed=94
posterior_ready=1560
posterior_strict_ready=361
posterior_summary_likelihood=1199
```

解读：

- 252x 活动 cohort 全部被识别为活动/缺 prior 候选，没有被错误映射到普通 250x 沉船先验。
- main archive 没有活动候选；先验可用覆盖 1560 个 ready 窗口。
- 只有 359 个窗口在当前 64-trial 路径下属于强可信 prior/pipeline 分母；1199 个 `summary_likelihood` 是保守 fallback，应继续作为 shadow 观察，不应直接 promotion。
- 94 个 `prior_stressed` 行值得后续分片审计，重点看 hard evidence 是否反映真实长尾、表漂移、活动机制或 parser 证据异常。
- readiness 现在会把 `prior_trusted < ready`、`activity_candidate > 0` 或 `prior_stress_score > 0` 判为 `prior_robustness=blocked`，防止这些行被整体 MAE 掩盖。

## O-v3-059：live/model_eval 已具备 activity/prior-drift 审计字段

2026-06-06 对 live monitor 增加 `v3_robust_*` 后，测试覆盖：

```text
tests/test_live_monitor.py:
- 正常 2401 live artifact 包含 v3_prior_* 与 v3_robust_*。
- model_eval 展开 v3_prior_* 与 v3_robust_*。
- 未知 2526 live v3 shadow 标记：
  error=unknown_map_id
  v3_prior_error=KeyError
  v3_robust_status=prior_unavailable
  v3_robust_activity_candidate=True
  v3_robust_fallback_mode=missing_prior_truth_only
```

解读：

- 后续实战样本如果遇到一周活动或新表缺失，live 日志会直接暴露 prior 不可信，而不是只留下“估值低/高”的结果。
- 该实现仍是 shadow/audit-only；当前 UI 主建议和 formal bid 未改。

## O-v3-060：prior-stressed 分片集中在 cells/capacity mismatch

2026-06-06 使用 `summarize_v3_prior_robustness_audit.py --posterior-trials 64` 审计默认 archive：

```text
prior_stressed:
ready=94
post_ready=94
metric=94
trusted=0/94
summary_likelihood=92
strict=2
mae=381373.9
bias=-124899.4
below=0.670213
p90_cover=0.595745
q6_count_mae=1.58
q6_cells_mae=8.01
q6_value_mae=484855.1

reason counts:
total_cells_above_prior=48
q6_cells_above_prior=32
total_count_above_prior=15
q6_value_above_prior=13
total_value_above_prior=13
q6_count_above_prior=1
```

对照：

```text
weak_prior_fallback:
ready=1107
mae=310604.9
below=0.506775
p90_cover=0.793135

ok/trusted:
ready=359
mae=326972.7
below=0.515320
p90_cover=0.660167
```

活动 cohort：

```text
prior_unavailable ready=58
post_ready=0
metric=0
activity=58
fallback=missing_prior_truth_only
```

解读：

- `prior_stressed` 是特殊风险分片，不是普通 fallback 行；它会同时拉高 below 与 P90 miss 风险。
- 主要问题更像 cells/capacity/evidence-prior mismatch：`total_cells_above_prior` 和 `q6_cells_above_prior` 占主导。
- q6 count alone 不是主因，只有 `q6_count_above_prior=1`。
- 下一步 formal/value sampler 设计应把 prior-stressed 行单独 holdout，不应把它们当普通低估样本直接上修。

## O-v3-061：prior-stress details 显示 capacity drift、q6-cells floor 与 value-floor stress 需要拆开

2026-06-06 扩展 `summarize_v3_prior_robustness_audit.py --details` 后，默认 archive 64-trial 明细显示：

```text
prior_stressed:
ready=94 post_ready=94 metric=94 trusted=0
summary_likelihood=92 strict=2

total_cells_above_prior:
ready=48
mae=406353.3
below=0.75
p90_cover=0.5

q6_cells_above_prior:
ready=32
mae=264904.3
below=0.625
p90_cover=0.8125

q6_value_above_prior / total_value_above_prior:
ready=13
mae=436218.2
below=0.769231
p90_cover=0.307692
```

代表性明细：

```text
ethan|2506|shape:
total_cells floor=216 prior=91.086 truth=216 post50=216
q6_cells floor=37 prior=10.109 truth=37 post50=48
item_count truth=58 prior_max=44

ethan|2406|public:max_item_cells+item+shape+layout:
total_cells exact=157 prior=81.487 truth=157 post50=157
q6_cells floor=15 prior=6.299 truth=17 post50=18.6
item_count truth=47 prior_max=40

ethan|2406|item+shape:
total_value floor=1622990 prior=503544.083 truth=1859009 post50=1622990
q6_value floor=1553900 prior=322041.293 truth=1729400 post50=1858600
```

解读：

- 多个 `total_cells_above_prior` 明细的 exact/floor target 与 truth 一致，且 truth/target item count 超过 prior max；这是有效 hard evidence 与旧 prior/capacity 表不一致的信号，不能按普通模型误差处理。
- `q6_cells_above_prior` 不等于“统一上修 q6 cells 就安全”：有些行 posterior 已经高于 truth，说明需要 changed-row hurt 和 high-over guard。
- `q6_value_above_prior` / `total_value_above_prior` 是 value-floor stress，和 cells/capacity drift 的风险形态不同；后续 formal/value sampler 必须单独报告，不应与 cells 行合并校准。
- 活动 cohort 在 `--details` 下仍为空，因为 `prior_stress_score=0` 且 `post_ready=0`，符合“不计普通准确率”的边界。

## O-v3-062：`v3_fv_*` 第一阶段只形成 shadow 分母，默认 holdout 仍 sample-limited

2026-06-06 新增 formal/value sampler 第一阶段后，64-trial archive 显示：

```text
v3_fv_candidate_rows=13
v3_fv_capacity_watch_rows=126
v3_fv_value_floor_candidate_rows=13
v3_fv_formal_p50_mae=318635.858
v3_fv_delta_formal_p50_mae=0.0
v3_fv_formal_p50_below_rate=0.51859
v3_fv_formal_p90_coverage=0.750641
```

活动 cohort 仍为：

```text
posterior_ready=0
metric_rows=0
v3_fv_candidate_rows=0
v3_fv_capacity_watch_rows=0
```

新增 session holdout 默认阈值下：

```text
overall_status=sample_limited
candidate_rows=0
train_status_counts=blocked_low_sample:414
```

readiness 总审计：

```text
overall_status=not_ready
gate=formal_value_sampler_holdout status=blocked
formal_value_rows=0
formal_value_delta=None
```

解读：

- archive 中 value-floor stress 只有 13 行，进入默认 session holdout 后每个 group 的训练折样本不足，不能作为 promotion 证据。
- `v3_fv_delta_formal_p50_mae=0.0` 表明第一阶段 floor candidate 当前没有改善全局 formal MAE；它的价值是把 value-floor stress 从 capacity/cells drift 中拆出来，形成可审计分母。
- 126 个 capacity watch 行不应被当成 formal value 上修候选；它们更像 prior/capacity/evidence mismatch 的后续审计入口。
- live/model_eval 已能记录 `v3_fv_*`，但 `active=false` 与 `affects_bid=false` 是关键边界。

## O-v3-063：prior-stress 聚合显示 capacity/table drift 是主要一致性风险

2026-06-06 新增 `--detail-summary` 后，默认 archive 64-trial 的 prior-stress 聚合：

```text
rows=94
capacity_flags=truth_count_above_prior_max:68,target_count_above_prior_max:39
sources_total_cells=floor:57,exact:37
sources_q6_cells=floor:59,none:35
ratio_total_cells avg=1.328 p90=2.126 max=2.371
ratio_q6_cells avg=1.898 p90=2.881 max=4.001
ratio_q6_value avg=1.917 p90=3.309 max=4.825
```

按 reason：

```text
total_cells_above_prior:
rows=48
truth_count_above_prior_max=44
target_count_above_prior_max=30
sources_total_cells=exact:32,floor:16

q6_cells_above_prior:
rows=32
sources_q6_cells=floor:32
ratio_q6_cells avg=2.791 p90=3.66 max=4.001

total_count_above_prior:
rows=15
target_count_above_prior_max=15
truth_count_above_prior_max=15
```

活动 cohort：

```text
prior_stress_detail_summary rows=0
```

解读：

- 68/94 prior-stressed 行的 settlement truth item count 超过旧 prior max，39/94 的 hard target count 也超过旧 prior max；这更像 capacity/table drift 或旧 drop prior 覆盖不足，不是 formal/value sampler 可以直接修正的误差。
- `total_cells_above_prior` 中 exact hard evidence 占 32/48，说明相当一部分不是 floor 估计噪声，而是公开/解析证据与旧 prior 直接冲突。
- `q6_cells_above_prior` 全部是 floor source，ratio 上限 4.001；它需要单独 cells 方向性/over guard，而不是和 value-floor 候选合并。
- 252x 活动样本继续只作为 prior-unavailable/activity 分母，未进入 prior-stress 聚合。

## O-v3-064：prior-stress 热点按 map/profile 分布，风险形态不同

2026-06-06 使用 `--detail-summary-by map_id --detail-summary-by hero_map_evidence_profile` 后，默认 archive 64-trial 的 top map groups：

```text
map_id=2401 rows=12 capacity_hits=9 max_cells_ratio=4.001 max_value_ratio=3.309
map_id=2501 rows=10 capacity_hits=16 max_cells_ratio=3.36 max_value_ratio=3.194
map_id=2404 rows=10 capacity_hits=7 max_cells_ratio=2.881 max_value_ratio=1.017
map_id=2406 rows=10 capacity_hits=6 max_cells_ratio=2.381 max_value_ratio=4.825
map_id=2601 rows=8 capacity_hits=16 max_cells_ratio=2.157 max_value_ratio=0.142
```

代表性差异：

- `2401` 同时有高 q6 cells ratio 与 value ratio，capacity hits 中等偏高。
- `2501` / `2601` capacity hits 很高，更像 capacity/table/prior max 口径问题。
- `2406` max value ratio 最高，属于 value-floor stress 与 capacity/cells drift 叠加热点。
- `2404` 以 cells ratio 为主，value ratio 不高。

活动 cohort：

```text
prior_stress_detail_summary rows=0
```

解读：

- prior-stressed 不应再只作为一个整体看；map/profile 的风险形态不同，后续 sampler/readiness 必须能报告这些分片。
- capacity hits 高的 map 优先审计表与 session item count 口径；value ratio 高的 map 才进入 formal/value sampler 候选讨论。
- 当前信息仍然支持 shadow-only，不支持 v3 promotion。

## O-v3-065：readiness 已显式阻断 prior-stress capacity/table drift

2026-06-06 将 detail summary 接入 `summarize_v3_promotion_readiness.py` 后，默认 archive 64-trial：

```text
gate=prior_stress_capacity_table_drift status=blocked
prior_stress_detail_rows=94
prior_stress_capacity_hits=107
top_map_group=2401 rows=12 capacity_flag_hits=9
```

活动 cohort：

```text
gate=prior_stress_capacity_table_drift status=pass
prior_stress_detail_rows=0
prior_stress_capacity_hits=0
```

解读：

- readiness 现在能把 prior-stress capacity/table drift 作为独立 blocker 暴露，不再只依赖 `prior_robustness` 的总数。
- 主 archive blocked 是因为存在可解释的 capacity/table/evidence drift 风险；活动 cohort pass 是因为缺表活动样本没有进入 prior-stress detail 分母。
- 这进一步支持：v3 promotion 前必须先处理 targeted map/profile drift，不允许 sampler 局部指标绕过该问题。

## O-v3-066：live model_eval 需要与 archive 保持 `v3_fv_*` detail 字段一致

2026-06-06 补齐 live `model_eval` 后，局后复盘可以直接读取：

```text
v3_fv_total_count_source
v3_fv_total_count_target
v3_fv_total_count_prior_expected
v3_fv_total_count_target_prior_ratio
v3_fv_total_cells_source
v3_fv_total_cells_target
v3_fv_total_cells_prior_expected
v3_fv_total_cells_target_prior_ratio
v3_fv_q6_cells_source
v3_fv_q6_cells_target
v3_fv_q6_cells_prior_expected
v3_fv_q6_cells_target_prior_ratio
v3_fv_total_value_source
v3_fv_total_value_target
v3_fv_q6_value_source
v3_fv_q6_value_target
```

解读：

- 如果 live 局后出现 prior/capacity drift，`model_eval.jsonl` 不需要回头重跑 archive evaluator 才能定位 source/target/prior ratio。
- 这让 activity/prior drift 的实战样本与 archive 审计字段一致，减少 promotion 前分母不一致的风险。

## O-v3-067：prior-stress cells target 未出现高于 settlement truth 的聚合信号

2026-06-06 为 detail summary 增加 target-vs-truth delta 后，默认 archive 64-trial：

```text
prior_stress rows=94
target_delta_total_cells=below=50/match=44/above=0
target_delta_q6_cells=below=46/match=13/above=0

total_cells_above_prior:
target_delta_total_cells=below=9/match=39/above=0
target_delta_q6_cells=below=10/match=8/above=0

q6_cells_above_prior:
target_delta_total_cells=below=25/match=7/above=0
target_delta_q6_cells=below=24/match=8/above=0
```

活动 cohort：

```text
prior_stress_detail_summary rows=0
```

解读：

- `above=0` 说明当前 prior-stressed cells target 没有系统性超过 settlement truth；问题不是 hard/floor evidence 普遍过强。
- `match` 与 `below` 占主导，说明很多 hard/floor target 是可信下界或真实值，冲突主要来自旧 prior/capacity/table 低估或 posterior 对证据吸收不足。
- 后续应优先检查 prior table/capacity max、drop prior 生成和 posterior evidence absorption，而不是削弱 evidence compiler。

## O-v3-068：prior-stress posterior p50 未出现低于 compiled target 的聚合信号

2026-06-06 为 detail summary 增加 posterior-vs-target delta 后，默认 archive 64-trial：

```text
prior_stress rows=94
target_delta_total_cells=below=50/match=44/above=0
target_delta_q6_cells=below=46/match=13/above=0
post50_target_delta_total_cells=below=0/match=54/above=40
post50_target_delta_q6_cells=below=0/match=2/above=57
```

活动 cohort：

```text
prior_stress_detail_summary rows=0
post50_target_delta_total_cells=below=0/match=0/above=0
post50_target_delta_q6_cells=below=0/match=0/above=0
```

解读：

- prior-stressed 行中没有出现 posterior p50 低于 compiled cells target 的聚合信号；posterior evidence absorption 目前不是第一嫌疑。
- 结合 O-v3-067 的 `target above truth=0`，当前 under-truth 风险更像 target 只是下界，或旧 prior/capacity/table 覆盖不足。
- 后续仍应保留 posterior-vs-target absorption 指标，但 promotion blocker 的优先级应放在 prior/capacity table drift 与 map/profile target completeness 上。

## O-v3-069：capacity gap 显示 truth/prior-max drift 强于 target 过约束

2026-06-06 增加 `capacity_count_summary` 后，默认 archive 64-trial：

```text
prior_stress rows=94
capacity_flags=truth_count_above_prior_max:68,target_count_above_prior_max:39
capacity_count_sources=floor:62,exact:24,none:8
capacity_prior_max=n=94/avg=41.872/p90=44.0/max=44.0
capacity_target_prior_max_delta=n=86/avg=-7.419/p90=16.0/max=22.0
capacity_truth_prior_max_delta=n=94/avg=6.032/p90=20.0/max=22.0
capacity_target_truth_delta=n=86/avg=-13.047/p90=0.0/max=0.0
capacity_target_prior_counts=below=47/match=0/above=39
capacity_truth_prior_counts=below=25/match=1/above=68
capacity_target_truth_counts=below=56/match=30/above=0
```

代表性 map group：

```text
map_id=2501 rows=10 capacity_hits=16
capacity_prior_max=44
capacity_target_prior_counts=below=4/match=0/above=6
capacity_truth_prior_counts=below=0/match=0/above=10
capacity_target_truth_counts=below=4/match=6/above=0

map_id=2401 rows=12 capacity_hits=9
capacity_target_prior_counts=below=9/match=0/above=2
capacity_truth_prior_counts=below=4/match=1/above=7
capacity_target_truth_counts=below=9/match=2/above=0
```

活动 cohort：

```text
prior_stress_detail_summary rows=0
capacity_target_prior_counts=below=0/match=0/above=0
```

解读：

- `truth_count_above_prior_max=68` 明显高于 `target_count_above_prior_max=39`，说明很多 capacity drift 在 settlement truth 中更强，compiled target 只是下界。
- `capacity_target_truth_counts above=0` 再次确认当前没有 target count 高于 truth 的聚合信号。
- 优先级应继续放在 map/profile capacity table、prior max 覆盖和 target completeness，而不是削弱 total-count evidence 或把该问题交给 formal/value sampler。

## O-v3-070：capacity cases 将 direct table conflict 与 target lower-bound 分开

2026-06-06 增加 `capacity_cases` 后，默认 archive 64-trial：

```text
prior_stress rows=94
capacity_cases=target_lower_bound_truth_above_prior:31,direct_prior_max_conflict:29,no_capacity_prior_max_case:26,target_above_prior_but_below_truth:10,truth_above_prior_without_count_target:8

reason=total_count_above_prior:
capacity_cases=direct_prior_max_conflict:15

map_id=2601:
rows=8
capacity_hits=16
capacity_cases=direct_prior_max_conflict:8

map_id=2501:
rows=10
capacity_hits=16
capacity_cases=direct_prior_max_conflict:6,target_lower_bound_truth_above_prior:4
```

活动 cohort：

```text
prior_stress_detail_summary rows=0
capacity_cases=-
```

解读：

- `direct_prior_max_conflict` 是最强表容量信号：compiled target、settlement truth 都超过 prior max，且 target 匹配 truth。
- `target_lower_bound_truth_above_prior` 说明 target 不是过约束，而是低于 truth 的下界；这类分片需要 target completeness 与 capacity table 一起查。
- `2601` 的 8/8 direct conflict 是当前最干净的表容量审计入口；`2501` 是 mixed case，不能直接用 sampler 或统一表改动解释。

## O-v3-071：direct conflict 在当前 BidMap/Drop sampler 下超过理论 item-count 上限

2026-06-06 使用 `summarize_v3_capacity_table_audit.py` 对 capacity cases 追加 raw table 审计后：

```text
direct_prior_max_conflict:
case=direct_prior_max_conflict groups=10
map_id=2601 status=table_possible_max_below_truth rows=8 table_impossible_rows=8 bidmap_items=22-44 sampler_possible_max=44 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=65
map_id=2501 status=table_possible_max_below_truth rows=6 table_impossible_rows=6 bidmap_items=22-44 sampler_possible_max=44 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=60
map_id=2506 status=table_possible_max_below_truth rows=4 table_impossible_rows=4 bidmap_items=22-44 sampler_possible_max=44 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=58

target_lower_bound_truth_above_prior:
map_id=2508 status=table_possible_max_below_truth rows=6 table_impossible_rows=6 bidmap_items=22-44 sampler_possible_max=44 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=64
map_id=2405 status=table_possible_max_below_truth rows=4 table_impossible_rows=4 bidmap_items=20-40 sampler_possible_max=40 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=60

activity cohort:
case=direct_prior_max_conflict groups=0
```

解读：

- BidMap drop-ref 的 `items_per_session_max` 目前被 sampler 当作抽取次数上限；后续 v300 审计确认 current raw 表中该字段在 `col[17]`，这些 top groups 的 DropEntry `n_max` 全部为 1，因此 sampler 理论 item-count max 等于 BidMap max。
- archive settlement truth 直接超过该 theoretical max，不是 evidence compiler 或 posterior absorption 能解释的问题。
- 当前最可能的原因是 BidMap/session capacity 语义、表版本、或 settlement inventory truth 口径与 sampler 假设不一致；这必须在 promotion 前单独解释。

## O-v3-072：raw settlement inventory 诊断排除 2601 parser 重复主因

2026-06-06 将 raw inventory diagnostics 接入 `summarize_v3_capacity_table_audit.py` 后，默认 archive 64-trial：

```text
direct_prior_max_conflict:
map_id=2601 rows=8 raw_inventory=verified_latest_inventory raw_files=4 raw_states=max=1.0 raw_latest_count=max=65.0 raw_truth_match_rows=8/8 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0 raw_dup_item=max=12.0 raw_msg=0x002D:4
map_id=2501 rows=6 raw_inventory=verified_latest_inventory raw_files=2 raw_truth_match_rows=6/6 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0
map_id=2506 rows=4 raw_inventory=verified_latest_inventory raw_files=1 raw_truth_match_rows=4/4 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0

target_lower_bound_truth_above_prior:
map_id=2508 rows=6 raw_inventory=verified_latest_inventory raw_truth_match_rows=6/6 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0
map_id=2504 rows=4 raw_inventory=verified_latest_inventory raw_truth_match_rows=4/4 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0
map_id=2405 rows=4 raw_inventory=verified_latest_inventory raw_truth_match_rows=4/4 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0
```

代表性 2601 raw capture 直接解析：

```text
fatbeans_valid_aisha_2601_3rounds_2601_1295018740835056_0215.json:
inventory_states=1 truth_count=65 latest_count=65 unique_runtime=65 dup_runtime=0 unique_pair=65 dup_pair=0

fatbeans_valid_aisha_2601_5rounds_2601_1295018737442914_0223.json:
inventory_states=1 truth_count=60 latest_count=60 unique_runtime=60 dup_runtime=0 unique_pair=60 dup_pair=0
```

解读：

- `settlement_truth_from_fatbeans` 与 latest inventory state item count 对齐，detail row truth count 也与 latest inventory 对齐。
- raw latest inventory 中 runtime id 与 `(runtime_id,item_id)` 均无重复；duplicate item id 是同款物品多件，不是 parser 重复。
- 2601 direct conflict 不是 settlement inventory 重复解析导致；当前 blocker 继续指向 BidMap/session capacity 语义、DropEntry count 语义或 raw table/archive 版本不一致。
- 这支持继续保持 `prior_stress_capacity_table_drift` blocked，并禁止用 formal/value sampler 或 posterior 上修绕过该问题。

## O-v3-073：v300 BidMap 23 列与 zodiac activity extras 只解释部分 capacity gap

2026-06-06 对 current raw tables 与 prior-stressed top groups 继续审计：

```text
raw table:
data/raw/fileVersion=300
data/raw/tables/fileVersion=300
filelist=Ver:300|FileCount:4299
BidMap rows=125 column_counts={23:125}
BidMap.txt entry=Tables/BidMap.txt|XGrDTpKIl6MsintjOgFp9yy2NmI=$62148
Drop.txt entry=Tables/Drop.txt|GF8kBPZ3zi0zgO3mn/pNEfb5HIw=$294160

representative columns:
map 2601 col[14]=[60,60,60,60,60] col[16]=[[]] col[17]=[9999,2601,22,44]
map 2501 col[14]=[50,50,50,50,50] col[16]=[[]] col[17]=[9999,2501,22,44]
map 2405 col[14]=[50,50,50,50,50] col[16]=[[]] col[17]=[9999,2405,20,40]

direct_prior_max_conflict:
map_id=2601 rows=8 table_impossible_rows=8 round_cap_impossible_rows=3 raw_missing_drop=max=7 raw_temp_zodiac=max=7 raw_non_zodiac_missing=max=0
map_id=2501 rows=6 table_impossible_rows=6 round_cap_impossible_rows=5 raw_missing_drop=max=3 raw_temp_zodiac=max=3 raw_non_zodiac_missing=max=0

target_lower_bound_truth_above_prior:
map_id=2508 rows=6 table_impossible_rows=6 round_cap_impossible_rows=6 raw_missing_drop=max=8 raw_temp_zodiac=max=8 raw_non_zodiac_missing=max=0
map_id=2405 rows=4 table_impossible_rows=4 round_cap_impossible_rows=4 raw_missing_drop=max=2 raw_temp_zodiac=max=2 raw_non_zodiac_missing=max=0
```

解读：

- 当前 raw BidMap 是 v300 23-column schema；drop-ref 已从历史 `col[16]` 移到 current `col[17]`，current `col[16]` 是空占位。
- `col[14]` 的 `[50..]/[60..]` 与 settlement count 更接近，但仍有 rows 超过该候选 cap，因此不能直接把它当作最终 item-count cap。
- settlement inventory 中不在 reachable Drop universe 的 item id 全部落在 known temporary blue zodiac activity id `1306003..1306014`；没有 non-zodiac missing item。
- activity extras 能解释 item-universe 差异，但不能完整解释 24xx/25xx/2601 settlement count 超过 sampler possible max 的冲突。
- 下一步应验证 settlement inventory 是否有额外展开/活动生成机制，以及 archive capture 与 current raw v300 table 的版本时序；formal/value sampler 与 promotion 继续暂停在该 blocker 后面。

## O-v3-074：扣除 zodiac extras 后 capacity gap 仍存在，capture 缺少 table version/hash

2026-06-06 扩展 `summarize_v3_capacity_table_audit.py`，新增扣除 zodiac 后的 residual gap 字段，并新增 `summarize_v3_archive_table_timing.py`：

```text
default archive direct_prior_max_conflict:
map_id=2601 raw_drop_excess=max=21 raw_drop_excess_after_temp=max=20 raw_round_excess=max=5 raw_round_excess_after_temp=max=4
map_id=2501 raw_drop_excess=max=16 raw_drop_excess_after_temp=max=13 raw_round_excess=max=10 raw_round_excess_after_temp=max=7
map_id=2506 raw_drop_excess=max=14 raw_drop_excess_after_temp=max=13 raw_round_excess=max=8 raw_round_excess_after_temp=max=7

default archive target_lower_bound_truth_above_prior:
map_id=2508 raw_drop_excess=max=20 raw_drop_excess_after_temp=max=14 raw_round_excess=max=14 raw_round_excess_after_temp=max=8
map_id=2504 raw_drop_excess=max=20 raw_drop_excess_after_temp=max=17 raw_round_excess=max=14 raw_round_excess_after_temp=max=11
map_id=2405 raw_drop_excess=max=20 raw_drop_excess_after_temp=max=18 raw_round_excess=max=10 raw_round_excess_after_temp=max=8

default archive all sessions:
sessions=441
above_drop_sessions=196
above_drop_after_temp_sessions=172
above_round_sessions=81
above_round_after_temp_sessions=59
temp_sessions=337
temp_max=8

timing/default archive:
raw_file_version=300
raw_tables_file_version=300
filelist_header=Ver:300|FileCount:4299
BidMap.txt entry=Tables/BidMap.txt|XGrDTpKIl6MsintjOgFp9yy2NmI=$62148
Drop.txt entry=Tables/Drop.txt|GF8kBPZ3zi0zgO3mn/pNEfb5HIw=$294160
BidMap mtime=2026-05-26T11:08:52+08:00
Drop mtime=2026-05-26T11:03:53+08:00
fileVersion/filelist mtime=2026-06-03T20:02+08:00
capture_min=2026-05-27T22:13:58+08:00
capture_max=2026-06-05T23:25:48+08:00
capture_version_like_keys=-
parse_errors=0

timing/activity cohort:
sample_files=15
capture_min=2026-06-05T23:05:05+08:00
capture_max=2026-06-05T23:56:58+08:00
capture_version_like_keys=-
parse_errors=0
```

解读：

- zodiac extras 大量存在，但扣除后仍保留明显 residual item-count gap；它不能单独解释 drop-ref max 或 round-cap candidate 冲突。
- 默认 archive 与 activity cohort 的 capture JSON 均未发现 version/hash 字段；当前只能用 raw fileVersion/filelist 与本地 mtime 做弱时序判断。
- BidMap/Drop 内容文件 mtime 早于所有默认 archive capture，但 fileVersion/filelist mtime 是 2026-06-03，说明不能仅凭本地 mtime 完成 table-version 证明。
- 下一步应继续查 settlement inventory 是否有额外生成/展开字段或协议消息，而不是调整 formal/value sampler。

## O-v3-075：0x002D settlement field[4] 是 final slot block，未暴露 source split

2026-06-06 新增 `summarize_v3_settlement_payload_audit.py`，对 default archive 与 0605 activity cohort 的 0x002D raw payload 审计：

```text
default archive:
files=441
settlement_rows=441
raw_candidate_match_rows=439
occupied_slot_match_rows=439
payload_f20_rows=436
full_observed_action_rows=18
slot_counts=300:251,250:186,232:1,252:1,253:1,254:1
raw_candidate_delta=max=1
occupied_slot_delta=max=1
raw_dup_pair=max=1

default top groups:
map_id=2601 files=22 inventory_count=max=65 slot_counts=300:22 raw_candidate_match_rows=22/22 occupied_slot_match_rows=22/22 full_actions=none:15,100100:4,100134:3
map_id=2501 files=87 inventory_count=max=65 slot_counts=300:86,232:1 raw_candidate_match_rows=86/87 occupied_slot_match_rows=86/87 full_actions=none:85,100100:2
map_id=2508 files=17 inventory_count=max=64 slot_counts=300:17 raw_candidate_match_rows=17/17 occupied_slot_match_rows=17/17 full_actions=none:17
map_id=2405 files=15 inventory_count=max=60 slot_counts=250:15 raw_candidate_match_rows=15/15 occupied_slot_match_rows=15/15 full_actions=none:15

activity cohort:
files=15
settlement_rows=15
raw_candidate_match_rows=15
occupied_slot_match_rows=15
slot_counts=300:15
raw_candidate_delta=max=0
raw_dup_pair=max=0
map_id=2521 inventory_count=max=67 slot_counts=300:5
```

解读：

- 0x002D payload `field[4]` 不是 parser 重复来源；它表现为 final settlement grid/slot block，occupied slots/raw item candidates 基本等于 parsed final inventory。
- 24xx settlement slot count 多为 250，25xx/26xx/252x 多为 300；这更像 final grid capacity，不是 BidMap `drop_ref.items_max`。
- 少数 full observed actions（`100100`/`100134`）会镜像整局 inventory，但只覆盖 18/441，不能作为普遍额外生成机制。
- 当前协议层证据支持“truth count 是最终 occupied settlement slots”，但仍没找到 base Drop、activity overlay 或额外展开的 source split 字段。
- capacity blocker 下一步应转向 server generation/source 字段继续反查，或在 shadow-only 分支做 settlement occupancy count prior 校准候选；formal/value sampler promotion 仍暂停。

## O-v3-076：settlement occupancy count prior 候选复现 capacity residual，252x 是 missing-table cohort

2026-06-06 新增 `summarize_v3_settlement_count_prior_candidates.py`，直接从 final settlement inventory/0x002D payload 统计 count prior 候选分布：

```text
default archive:
files=441
settlement_rows=441
groups=21
inventory_count p50=41 p90=54 p95=57 max=66
non_temp_count max=64
temp_zodiac max=8
slot_counts=300:251,250:186,232:1,252:1,253:1,254:1
above_drop=196
above_drop_after_temp=172
above_round=81
above_round_after_temp=59
payload_mismatch_rows=2
candidate_statuses=observed_exceeds_table_caps_shadow_only:19,insufficient_samples_shadow_only:2

map highlights:
2501 above_drop_after_temp=39/87 above_round_after_temp=19/87 non_temp_count max=62
2601 above_drop_after_temp=11/22 above_round_after_temp=1/22 non_temp_count max=64
2504 above_drop_after_temp=11/22 above_round_after_temp=6/22 non_temp_count max=61
2506 above_drop_after_temp=11/21 above_round_after_temp=6/21 non_temp_count max=59
2401 above_drop_after_temp=21/72 above_round_after_temp=3/72 non_temp_count max=54

prefix highlights:
250 above_drop_after_temp=94/217 above_round_after_temp=42/217 non_temp_count max=62
240 above_drop_after_temp=56/169 above_round_after_temp=11/169 non_temp_count max=58
260 above_drop_after_temp=11/22 above_round_after_temp=1/22 non_temp_count max=64
241 above_drop_after_temp=6/19 above_round_after_temp=2/19 non_temp_count max=56
251 above_drop_after_temp=5/14 above_round_after_temp=3/14 non_temp_count max=60

activity cohort:
files=15
slot_counts=300:15
inventory_count p50=51 p90=54 p95=54 max=67
temp_zodiac max=0
missing_table_rows=15
map_prefix3=252 status=missing_table_shadow_only files=15
```

解读：

- settlement occupancy count 分布与 capacity residual blocker 方向一致：默认 archive 中扣除临时生肖后仍有 172/441 超过 `drop_ref.items_max`，59/441 超过 `col[14]` round-cap candidate。
- 这不是 parser duplicate 或 payload mismatch 主导，payload mismatch 仅 2/441，且前一轮 payload audit 已证明 final inventory 与 occupied slots 基本对齐。
- 252x activity cohort 没有 current BidMap 表项，且 temp zodiac 为 0；它应作为 missing-table/activity cohort 单独建 shadow evidence，不能和默认 250x shipwreck 表项直接合并。
- 当前结果支持设计 shadow-only settlement occupancy count prior，但仍不支持修改 formal sampler cap、promotion readiness 或 v2 归档。

## O-v3-077：v3_scp settlement count-prior evidence 已进入 archive/live/readiness，且保持 inactive

2026-06-06 新增 `settlement_count_prior.py` 与 `v3_scp_*` 字段族，并生成 `data/processed/v3_settlement_count_prior_shadow.json`：

```text
artifact:
entries=27
cohorts=2
affects_bid=False
active=False
default_archive:
  observed_exceeds_table_caps_shadow_only=19
  insufficient_samples_shadow_only=2
activity_20260605_shipwreck:
  missing_table_shadow_only=6

default archive evaluator:
windows=1577
ready=1560
v3_scp_ready_rows=1560
v3_scp_candidate_rows=1488
v3_scp_missing_table_rows=0
v3_scp_active_rows=0

activity evaluator:
windows=58
ready=58
posterior_ready=0
robust_activity_candidate=58
v3_scp_ready_rows=58
v3_scp_candidate_rows=0
v3_scp_missing_table_rows=58
v3_scp_active_rows=0

readiness:
overall_status=not_ready
gate=settlement_count_prior_shadow status=watch
gate=prior_stress_capacity_table_drift status=blocked
gate=formal_value_sampler_holdout status=blocked
```

解读：

- `v3_scp_*` 已经进入 archive evaluator、live monitor `v3_posterior_shadow`/`model_eval` 与 readiness gate，archive/live 字段来源一致。
- default archive 的 settlement count-prior candidate 大量覆盖 ready windows，但全部 `active=False`/`affects_bid=False`，不会改变正式出价。
- 252x activity cohort 以 `missing_table_shadow_only` 暴露，58/58 windows 均为 missing-table evidence；没有按 shipwreck family 混入 250x prior。
- 新 gate 只说明 settlement count-prior evidence 可见且 inactive；它不解除 `prior_stress_capacity_table_drift`，也不让 formal/value sampler promotion 通过。

## O-v3-078：settlement count-prior session holdout 支持 default shadow 候选，但暴露 exact-map 样本深度与 252x 表缺失

2026-06-06 新增 `summarize_v3_settlement_count_prior_holdout.py`，按 session stable fold 对 settlement occupancy count prior 做 holdout：

```text
default map_id:
sessions=441
groups=21
candidate_rows=389
sample_limited_rows=52
missing_table_rows=0
prior_coverage=0.609977
round_coverage=0.866213
holdout_p95_coverage=0.907455
holdout_max_coverage=0.948586
status_counts=blocked_low_sample:7,watch_settlement_count_prior_candidate:14

default map_prefix3:
sessions=441
groups=5
candidate_rows=441
sample_limited_rows=0
missing_table_rows=0
prior_coverage=0.609977
round_coverage=0.866213
holdout_p95_coverage=0.945578
holdout_max_coverage=0.986395
status_counts=watch_settlement_count_prior_candidate:5

activity map_id:
sessions=15
groups=6
candidate_rows=0
missing_table_rows=15
prior_coverage=None
round_coverage=None
holdout_p95_coverage=0.857143
status_counts=missing_table_shadow_only:6

activity map_prefix3:
sessions=15
groups=1
candidate_rows=0
missing_table_rows=15
prior_coverage=None
round_coverage=None
holdout_p95_coverage=0.933333
status_counts=missing_table_shadow_only:1
```

解读：

- default archive 中，settlement count-prior train p95 明显提高 coverage，且仍低于 train max；这支持继续把 `v3_scp_*` 作为 shadow evidence 审计。
- exact `map_id` 口径仍有 7 个 group 样本不足，不能仅凭 prefix 聚合推广成 sampler cap。
- prefix 聚合消除了 default sample-limited，但它混合了同 prefix 的 exact maps；只能作为 holdout 补充证据，不能替代 BidMap/DropEntry 字段语义确认。
- 252x activity cohort 即便 prefix holdout coverage 较高，仍然 15/15 缺 current BidMap；activity table/mapping blocker 未解除。
- readiness 保持 `overall_status=not_ready`，因此 formal/value sampler tuning、v3 promotion 与 v2 archive 继续暂停。

## O-v3-079：v3_scp 与 formal/value stress 的交集很小，count-prior 尚未形成 value bridge

2026-06-06 新增 `summarize_v3_scp_formal_value_link.py`，将 `v3_scp_*` settlement count-prior evidence 与 `v3_fv_*` formal/value stress 做 archive 关联审计：

```text
default by v3_scp_status:
scp_rows=1560
formal_rows=1560
scp_candidate_rows=1488
scp_candidate_formal_rows=1488
scp_candidate_value_floor_rows=8
scp_candidate_capacity_watch_rows=124
fv_value_floor_rows=13
fv_capacity_watch_rows=126
formal_mae=318635.858
fv_delta_mae=0.0
formal_below=0.51859
formal_p90_cover=0.750641
status_counts=no_scp_candidate_formal_rows:1,watch_scp_value_floor_overlap:1

default by v3_fv_stress_class:
groups=7
value_floor_stress rows=12 scp_candidate=7 p90_cover=0.25
capacity_cells_drift rows=118 scp_candidate=117 p90_cover=0.652542
none rows=1398 scp_candidate=1337 p90_cover=0.761803

default by map_id highlights:
2401 scp_candidate=257 scp_value_floor=3 scp_capacity=16 formal_mae=300158.618 p90_cover=0.782101
2402 scp_candidate=34 scp_value_floor=3 scp_capacity=1 formal_mae=192657.229 p90_cover=0.794118
2501 scp_candidate=310 scp_value_floor=2 scp_capacity=19 formal_mae=354779.263 p90_cover=0.674194
2506 scp_candidate=71 scp_value_floor=0 scp_capacity=15 formal_mae=429762.518 p90_cover=0.56338
2601 scp_candidate=86 scp_value_floor=0 scp_capacity=10 formal_mae=530111.384 p90_cover=0.465116

activity:
scp_rows=58
formal_rows=0
scp_candidate_rows=0
scp_missing_table_rows=58
status_counts=missing_table_shadow_only:1

readiness:
gate=settlement_count_formal_value_link status=blocked
scp_value_link_rows=8
scp_capacity_link_rows=124
scp_value_link_delta=0.0
overall_status=not_ready
```

解读：

- `v3_scp_candidate` 覆盖大量 formal-ready rows，但与现有 `value_floor_stress` 的交集只有 8/1488；它更多是 capacity-only/no-value-stress evidence。
- 2506、2601 等 prior-stressed heavy groups formal baseline 明显偏弱，但没有 value-floor overlap；直接把 count-prior 当 value-floor 会跳过 cells/value bridge。
- 当前 `v3_fv` 对 default archive formal MAE 的 delta 仍为 0；这说明现有 formal/value sampler 不是 count-prior 的可用 promotion path。
- 252x activity 仍没有 posterior/formal metric rows，只能留在 missing-table evidence；不能用 activity count-prior 推导 formal/value promotion。

## O-v3-080：count->cells/value bridge 候选存在，但与现有 v3_fv stress class 不一致

2026-06-06 新增 `summarize_v3_scp_count_value_bridge.py`，量化 `v3_scp` count gap 与 total cells/formal value undercoverage 的 bridge 候选：

```text
default by v3_scp_group:
scp_rows=1560
metric_rows=1560
scp_candidate_rows=1488
scp_candidate_metric_rows=1488
scp_p95_above_target_rows=1276
truth_above_prior_rows=711
target_below_truth_rows=1225
cells_p90_under_rows=635
formal_p90_under_rows=389
count_cells_bridge_rows=516
count_value_bridge_rows=315
count_cells_value_bridge_rows=201
cells_per_item avg=2.668 p50=2.658 p90=3.14 p95=3.34 max=3.957
formal_per_item avg=18712.836 p50=16850.545 p90=32231.194 p95=41419.737 max=74360.36
status_counts=no_scp_candidate_metric_rows:2,watch_count_cells_only_bridge:2,watch_count_cells_value_bridge:17

map highlights:
2501 count_cells_value=54 cells_under=151 formal_under=101 cells_per_item_p95=3.34 formal_per_item_p95=33378.123
2401 count_cells_value=29 cells_under=84 formal_under=56 cells_per_item_p95=3.204 formal_per_item_p95=33516.188
2601 count_cells_value=26 cells_under=34 formal_under=46 cells_per_item_p95=3.362 formal_per_item_p95=56041.8
2506 count_cells_value=19 cells_under=32 formal_under=31 cells_per_item_p95=3.421 formal_per_item_p95=36444.157
2504 count_cells_value=15 cells_under=32 formal_under=21 cells_per_item_p95=2.828 formal_per_item_p95=24758.17

by v3_fv_stress_class:
none count_cells_value=185 count_cells=460 count_value=280
capacity_cells_drift count_cells_value=15 count_cells=45 count_value=28
value_floor_stress count_cells_value=1 count_cells=1 count_value=4

activity:
scp_rows=58
metric_rows=0
missing_table_rows=58
status_counts=missing_table_shadow_only:6

readiness:
gate=settlement_count_cells_value_bridge status=watch
scp_count_cells_value_bridge_rows=201
scp_count_cells_bridge_rows=516
scp_count_value_bridge_rows=315
overall_status=not_ready
```

解读：

- count->cells/value bridge 候选在 default archive 中真实存在，尤其 2501、2401、2601、2506 是后续 holdout/sampler design 的优先 slice。
- 185/201 个 full bridge rows 当前 `v3_fv_stress_class=none`，说明现有 value-floor stress detection 没有捕捉大部分 count/cells/value bridge 信号。
- `truth_cells_per_item` 与 `truth_formal_per_item` 是 archive truth 派生量，只能用于审计和后续 holdout 设计，不能直接作为 live/formal sampler 参数。
- activity 252x 继续没有 metric rows，不能参与 bridge 校准。

## O-v3-081：naive count->cells/value bridge holdout 提高 coverage 但造成 over-risk/MAE hurt

2026-06-06 新增 `summarize_v3_scp_count_value_bridge_holdout.py`，用 session stable fold 验证 count->cells/value bridge floor：

```text
default ratio_source=all:
overall_status=blocked_holdout_hurt
rows=1560
candidate_rows=1276
applied_rows=1173
sample_limited_rows=59
candidate_delta_mae=50956.632
candidate_delta_p90=0.219096
candidate_over=0.712702
overall_delta_mae=38315.468
overall_delta_p90=0.164744
status_counts=blocked_holdout_hurt:18,blocked_holdout_over_risk:1,sample_limited:2

top groups:
2501 delta_mae=33301.56 delta_p90=0.209677 bridge_over=0.654839
2401 delta_mae=45527.445 delta_p90=0.171206 bridge_over=0.657588
2601 delta_mae=17434.051 delta_p90=0.5 bridge_over=0.744186
2506 delta_mae=-30309.955 delta_p90=0.323944 bridge_over=0.647887
2504 delta_mae=2269.879 delta_p90=0.227848 bridge_over=0.683544

default ratio_source=bridge:
overall_status=blocked_holdout_hurt
candidate_rows=1276
applied_rows=1120
sample_limited_rows=122
candidate_delta_mae=53663.766
candidate_delta_p90=0.225
candidate_over=0.708036

activity:
overall_status=sample_limited
rows=0
candidate_rows=0
applied_rows=0

readiness:
gate=settlement_count_cells_value_bridge_holdout status=blocked
scp_bridge_holdout_delta=50956.632
scp_bridge_holdout_over=0.712702
overall_status=not_ready
```

解读：

- naive bridge floor 能显著提高 formal p90 coverage 和 cells p90 coverage，但代价是 formal p50 MAE 上升与 over-rate 过高。
- 2506 有 MAE 改善信号，但 over-rate 仍超过 guard；它适合作为后续 guarded/bounded bridge 的优先实验 slice，而不是直接 promotion。
- `ratio_source=bridge` 仍无法消除 over-risk，说明问题不是单纯由训练 ratio 分母过宽造成。
- activity 252x 仍没有 metric rows，因此 bridge holdout 不提供 activity promotion evidence。

## O-v3-082：guarded count->value cap 缓解 MAE 但没有解除 holdout blocker

2026-06-06 在 `summarize_v3_scp_count_value_bridge_holdout.py` 增加 audit-only `floor_mode` 与 `formal_lift_cap` probe 后，archive 64 posterior trials 实测：

```text
total floor + formal_lift_cap=5000:
overall_status=blocked_holdout_hurt
candidate_rows=1276
applied_rows=1173
sample_limited_rows=59
candidate_delta_mae=-288.656
candidate_delta_p90=0.00341
candidate_over=0.495311
applied_hurts=2507,2407,2409

total floor + formal_lift_cap=10000:
overall_status=blocked_holdout_hurt
candidate_delta_mae=-516.888
candidate_delta_p90=0.004263
candidate_over=0.501279
applied_hurts=2507,2410,2407,2409

total floor + formal_lift_cap=25000:
overall_status=blocked_holdout_hurt
candidate_delta_mae=-890.956
candidate_delta_p90=0.018755
candidate_over=0.522592
applied_hurts=2507,2410,2403,2407,2409

total floor + formal_lift_cap=50000:
overall_status=blocked_holdout_hurt
candidate_delta_mae=-921.456
candidate_delta_p90=0.032396
candidate_over=0.541347
applied_hurts=2507,2502,2410,2509,2403,2407,2409

extra floor uncapped:
overall_status=blocked_holdout_hurt
candidate_delta_mae=344324.441
candidate_delta_p90=0.234182
candidate_over=0.873459

extra floor + formal_lift_cap=5000:
overall_status=blocked_holdout_hurt
candidate_delta_mae=-63.063
candidate_delta_p90=0.003287
candidate_over=0.497124
applied_hurts=2507,2407,2409

ratio_source=bridge + formal_lift_cap=5000:
overall_status=blocked_holdout_hurt
candidate_rows=1276
applied_rows=1120
sample_limited_rows=122
candidate_delta_mae=-368.818
candidate_delta_p90=0.003571
candidate_over=0.490179
applied_hurts=2507,2407,2409

activity + formal_lift_cap=5000:
overall_status=sample_limited
rows=0
candidate_rows=0
applied_rows=0
```

Readiness 默认口径未改：

```text
overall_status=not_ready
blocked_gates=12
gate=settlement_count_cells_value_bridge_holdout status=blocked
scp_bridge_holdout_delta=50956.632
scp_bridge_holdout_over=0.712702
```

解读：

- formal lift cap 能把 naive bridge 的 formal p50 MAE hurt 压成小幅改善，但不能消除 applied hurt groups。
- cap 越高，formal p90 coverage 改善更大，但 over-rate 与 hurt groups 随之上升。
- `floor_mode=extra` uncapped 是反证：按 count gap 增量补 floor 会严重过冲；加 cap 后仍 blocked。
- strict `ratio_source=bridge` 加 cap 仍 blocked，说明 blocker 不只是 train ratio source，而是 capacity/table/settlement item-count 语义还没有解释清楚。
- 该结果支持继续暂停 formal/value sampler 参数调优，优先审计 BidMap/Drop/capacity 与 settlement inventory 的 item-count 上限冲突。

## O-v3-083：capacity conflict 指向 sampler prior-max 语义，而不是 settlement parser 重复

2026-06-06 增强 `summarize_v3_capacity_table_audit.py`，把 raw BidMap col[14]/[16]/[17]、flattened leaf `n_min/n_max`、0x002D inventory slot count、raw candidate/occupied slot delta、full observed actions 与 public total-count 一并输出。

default archive `direct_prior_max_conflict`：

```text
case=direct_prior_max_conflict groups=10

2601:
rows=8 table_impossible_rows=8
bidmap_items=22-44
bidmap_raw_cols=23
drop_ref_col=17
round_cap=60-60
raw_col14="[60,60,60,60,60]"
raw_col16="[[]]"
raw_col17="[9999,2601,22,44]"
sampler_possible_max=44
sampler_max_count_per_draw=1
sampler_leaf_nmax=max=1
raw_slots=max=300
raw_latest_count=max=65
raw_slot_headroom=max=251
raw_candidate_delta=max=0
raw_occupied_delta=max=0
raw_full_actions=100100:3,100134:1
raw_drop_excess_after_temp=max=20
raw_round_excess_after_temp=max=4

2501:
rows=6 table_impossible_rows=6
raw_col16="[[]]"
raw_col17="[9999,2501,22,44]"
sampler_leaf_nmax=max=1
raw_slots=max=300
raw_latest_count=max=60
raw_slot_headroom=max=253
raw_candidate_delta=max=0
raw_occupied_delta=max=0
raw_public_count=60:1
raw_drop_excess_after_temp=max=13
raw_round_excess_after_temp=max=7

2506:
rows=4 table_impossible_rows=4
raw_col16="[[]]"
raw_col17="[9999,2506,22,44]"
sampler_leaf_nmax=max=1
raw_slots=max=300
raw_latest_count=max=58
raw_slot_headroom=max=242
raw_candidate_delta=max=0
raw_occupied_delta=max=0
raw_full_actions=100134:1
raw_drop_excess_after_temp=max=13
raw_round_excess_after_temp=max=7
```

全 archive settlement payload 复核：

```text
files=441
settlement_rows=441
raw_candidate_match_rows=439
occupied_slot_match_rows=439
slot_counts=300:251,250:186,232:1,252:1,253:1,254:1
raw_candidate_delta=max=1
occupied_slot_delta=max=1
raw_dup_pair=max=1
```

settlement count prior candidates：

```text
default:
files=441
inventory_count max=66
non_temp_count max=64
above_drop_after_temp=172
above_round_after_temp=59
payload_mismatch_rows=2

activity 252x:
files=15
table=missing_bidmap:15
inventory_count max=67
non_temp_count max=67
temp_zodiac max=0
slots=300:15
payload_mismatch=0/15
```

raw table timing：

```text
raw_file_version=300
raw_tables_file_version=300
filelist_header="Ver:300|FileCount:4299"
BidMap.txt entry=Tables/BidMap.txt|XGrDTpKIl6MsintjOgFp9yy2NmI=$62148
Drop.txt entry=Tables/Drop.txt|GF8kBPZ3zi0zgO3mn/pNEfb5HIw=$294160
capture_min=2026-05-27T22:13:58.2127532+08:00
capture_max=2026-06-05T23:25:48.3624321+08:00
capture_version_like_keys=-
```

解读：

- current v300 BidMap 列语义已复核：`col[16]` 是空占位，`col[17]` 才是 drop-ref；旧 `col[16]` 口径不得用于 current 表。
- Drop flattened leaf `n_max` 全为 1，不能解释超过 `items_per_session_max` 的 final inventory count。
- 0x002D payload raw candidate 与 occupied slots 基本逐项匹配 final inventory，且 direct conflict rows 的 truth 与 latest inventory 全匹配；parser 重复不是主因。
- final inventory count 远低于 250/300 slot capacity，说明 settlement inventory 的自然 capacity 更像 slot occupancy，而不是 BidMap drop-ref max。
- known temp zodiac 只解释 missing drop-universe item id，不足以解释 after-temp count gap。
- 仍缺少每个 archive capture 的表版本强字段，因此不能完全排除历史 table/version 或活动机制，但现有证据足以把 blocker 从“parser 重复”转为“sampler prior max/额外生成机制语义未解释”。

## O-v3-084：nested guard 将候选收缩到 2506，但有效 holdout 仍只有 9 条

2026-06-06 对 default 441-session archive 运行 nested train-only guarded bridge：

```text
aggregate-only / 64 trials / seed 0 / cap 5000:
overall=blocked
applied_rows=587
delta_mae=-577.339
hurts=2401,2502

all-inner-fold / zero-over / 64 trials / seed 0 / cap 10000:
overall=watch
selected_groups=2506:3
applied_rows=20
delta_mae=-6000.0
delta_p90=0
bridge_over=0.25
applied_hurts=-

64 trials / seed 1 / cap 10000:
overall=blocked
selected_groups=2501:1,2506:2
applied_rows=62
delta_mae=+378.95
applied_hurts=2501

256 trials / seed 0 / cap 10000:
overall=watch
selected_groups=2506:2
applied_rows=9
delta_mae=-4602.026
bridge_over=0.222222
applied_hurts=-

256 trials / seed 1 / cap 10000:
overall=watch
selected_groups=2506:2
applied_rows=9
delta_mae=-5555.556
bridge_over=0.222222
applied_hurts=-

256 trials / seed 7 / cap 10000:
overall=watch
selected_groups=2506:2
applied_rows=9
delta_mae=-3333.333
bridge_over=0.333333
applied_hurts=-

activity 252x:
overall=sample_limited
metric_rows=0
```

解读：

- 简单 aggregate guard 不能排除 group-level hurt；必须使用 outer holdout + inner crossfit，并要求各 inner fold 稳定。
- zero train over-increase 与 10000 lift cap 的组合能把高 trial 候选稳定收缩到 2506；cap 在这里同时参与 guard selection，不能被解释为可直接启用的正式参数。
- 64-trial seed 1 的 2501 false selection 是明确反例；readiness 中 64-trial seed 0 的 watch 只能表示候选可见，不能表示 seed-stable。
- 256-trial 多 seed 已给出方向性证据，但 9 条 outer holdout support 远低于 promotion 所需样本深度。
- 当前可进入下一阶段的只有 2506 shadow live/archive accumulation；formal/value active sampler、正式出价和 v2 归档仍无依据。

## O-v3-085：64-trial stability smoke 明确捕捉 seed1 的 2501 false selection

2026-06-06 运行 guarded bridge stability 矩阵默认 smoke：

```powershell
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_stability.py --formal-lift-cap 10000
```

首次真实 archive run：

```text
overall_status=blocked_applied_hurt
reasons=applied_hurts_present,non_watch_run,selected_group_drift
runs=2
watch_runs=1
trials=64
seeds=0,1
required_groups=2506
stable_groups=2506
union_groups=2501,2506
min_applied=20
min_required=20
signatures=2501:1,2506:2=1;2506:3=1

seed=0:
status=watch
selected=2506
applied_rows=20
delta_mae=-6000.0
bridge_over=0.25
applied_hurts=-

seed=1:
status=blocked_holdout_hurt
selected=2501,2506
applied_rows=62
delta_mae=378.95
bridge_over=0.580645
applied_hurts=2501
```

同配置 cache 复跑：

```text
runtime约4s
cache_hit=True for seed 0/1
```

解读：

- stability smoke 与 O-v3-084 的手工审计一致，能自动把 seed1 的 2501 false selection 标为 blocker。
- `stable_groups=2506` 只是交集仍包含 2506；`union_groups=2501,2506` 和 `applied_hurts=2501` 证明当前低 trial 配置不稳定。
- `.tmp/codex/v3_scp_guarded_bridge_stability` cache 已验证可用，后续可用于 256-trial 多 seed 长跑断点复用。
- 本轮 256-trial seeds 0/1/7 矩阵初跑超过 300 秒，尚未形成新的矩阵化证据；promotion 仍依赖后续长跑和样本扩充。

## O-v3-086：256-trial stability matrix 将 2506 收敛为 stable 但 low-support

2026-06-06 复跑 guarded bridge stability matrix：

```powershell
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 256 --posterior-seed 0 --posterior-seed 1 --posterior-seed 7 --formal-lift-cap 10000
```

结果：

```text
overall_status=blocked_low_support
reasons=low_applied_rows
runs=3
watch_runs=3
trials=256
seeds=0,1,7
required_groups=2506
stable_groups=2506
union_groups=2506
min_applied=9
min_required=20
signatures=2506:2=3

seed=0:
status=watch
selected=2506
applied_rows=9
delta_mae=-4602.026
delta_p90=0.0
bridge_over=0.222222
applied_hurts=-

seed=1:
status=watch
selected=2506
applied_rows=9
delta_mae=-5555.556
delta_p90=0.111111
bridge_over=0.222222
applied_hurts=-

seed=7:
status=watch
selected=2506
applied_rows=9
delta_mae=-3333.333
delta_p90=0.0
bridge_over=0.333333
applied_hurts=-
```

解读：

- 高 trial 多 seed 已修复 O-v3-085 的低 trial selected group drift；`2501` 不再被选中。
- 当前 blocker 从 seed stability 转为 support depth：outer holdout applied rows 只有 9，未达到 20。
- 该结果支持继续采集 2506 shadow support，但不支持 promotion 或 formal/value active sampler。

## O-v3-087：252x activity 候选映射更偏向 251x，但证据仍不足以定表

2026-06-06 运行 activity mapping likelihood 审计：

```powershell
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_activity_mapping_likelihood.py
```

结果：

```text
files=15
schemes=minus10,minus20
winners=minus10:11,minus20:4
candidate_statuses=ok:30
errors=0

minus10:
rows=15
winner_rows=11
candidate_maps=2511:5,2514:3,2519:3,2516:2,2512:1,2518:1
ll_per_item avg=-1.676415
missing_item_rate avg=0.0

minus20:
rows=15
winner_rows=4
candidate_maps=2501:5,2504:3,2509:3,2506:2,2502:1,2508:1
ll_per_item avg=-1.691183
missing_item_rate avg=0.0
```

按 activity map：

```text
2521: minus10 4 / minus20 1
2522: minus10 1
2524: minus10 2 / minus20 1
2526: minus10 2
2528: minus20 1
2529: minus10 2 / minus20 1
```

解读：

- `252x->251x` 的 quality likelihood 略优于 `252x->250x`，与 `2511-2520`/`2520->2150` activity/up table 线索一致。
- 但两个候选族的 missing item rate 都是 0，说明 item universe 相同；当前 likelihood 只能比较权重，不足以证明服务端映射。
- 252x 继续保持 missing-table/activity cohort，不进入 default prior 或 promotion 分母。

## O-v3-088：2506 selected-fold support 只有 9 rows，本地无可直接纳入新增样本

2026-06-06 只读调查 2506 support gap：

```text
default archive 2506:
canonical_sessions=21
metric_rows=71
bridge_candidate_rows=59
count_cells_value_bridge_rows=20

selected outer folds:
fold0 selected=yes sessions=1 metric_rows=3 bridge_candidates=3
fold1 selected=no  sessions=8 metric_rows=30 bridge_candidates=23
fold2 selected=no  sessions=5 metric_rows=18 bridge_candidates=16
fold3 selected=no  sessions=4 metric_rows=11 bridge_candidates=11
fold4 selected=yes sessions=3 metric_rows=9 bridge_candidates=6

applied_rows=3+6=9
min_required=20
```

本地新增候选：

```text
directly_addable=0
manual_review=1
manual_review_file=data/samples/fatbeans_invalid/parse_error/fatbeans_invalid_parse_error_aisha_shipwreck_test_sample60_5rounds_7fc668a5b9_0438.json
manual_review_session=2506:1295018649037100
manual_review_ready_rows=5
manual_review_bridge_candidates=5
manual_review_count_cells_value_bridge_rows=4
reason=historical SEND invalid frame length parse_error
```

不能纳入：

```text
data/logs/live/raw: 40 个 2506 文件，但唯一 sessions 已在 canonical archive，均为重复/reset/complete 副本
data/samples/fatbeans_manual_inbox: empty
data/samples/fatbeans_activity_20260605_shipwreck: 0 个 2506
data/logs/live_replay_*: replay derived output
data/review: derived audit output
data/samples/synthetic_v2: synthetic, not promotion support
```

解读：

- 2506 low-support blocker 的主因是 guard 只选择 folds 0/4，而这两个 holdout fold 的 bridge candidate rows 少。
- 本地没有可直接补入 default archive 的真实 2506 support。
- 下一步应采集新的完整 2506 sessions，目标至少补足 `+11` applied rows；实际建议采集 10-15 个真实 complete sessions 后复跑 stability matrix。

## O-v3-089：exact item likelihood 与 quality likelihood 同向，但仍不足以证明 252x 映射

2026-06-06 增强 `summarize_v3_activity_mapping_likelihood.py`，新增 exact item likelihood：

```text
files=15
quality_winners=minus10:11,minus20:4
item_winners=minus10:11,minus20:4
candidate_statuses=ok:30
errors=0

minus10:
quality_ll_per_item_avg=-1.676415
item_ll_per_item_avg=-5.965943
zero_item_avg=0.0
missing_item_rate_avg=0.0

minus20:
quality_ll_per_item_avg=-1.691183
item_ll_per_item_avg=-5.981787
zero_item_avg=0.0
missing_item_rate_avg=0.0
```

按 map：

```text
2521: quality minus10 4 / minus20 1; item minus10 4 / minus20 1
2522: quality minus10 1; item minus10 1
2524: quality minus10 2 / minus20 1; item minus10 2 / minus20 1
2526: quality minus10 2; item minus10 2
2528: quality minus20 1; item minus20 1
2529: quality minus10 2 / minus20 1; item minus10 2 / minus20 1
```

解读：

- exact item likelihood 与 quality likelihood 完全同向，说明更细粒度权重没有推翻 `252x->251x` 略优的结论。
- item-level margin 只是小幅增强，不足以把 `2521+` 定为 `2511+` official mapping。
- 两个候选族的 item universe 仍完全覆盖 observed settlement；252x 继续作为 missing-table/activity cohort。

## O-v3-090：readiness blocker lanes 显示当前仍是多维阻塞，不是单一 2506 问题

2026-06-06 对 `summarize_v3_promotion_readiness.py --posterior-trials 64` 增加 dependency lanes 后复跑：

```text
overall_status=not_ready
blocked_gates=12
blocked_or_pending_lanes=formal_value_shadow_sampler,profile_sample_depth,sampler_safety_holdout,settlement_bridge_support,table_activity_capacity,v2_archive_after_promotion
```

lane status counts：

```text
archive_pipeline_quality: pass=1 watch=1
table_activity_capacity: blocked=2 watch=1
settlement_bridge_support: blocked=1 watch=2
formal_value_shadow_sampler: blocked=3
sampler_safety_holdout: blocked=5 watch=2
profile_sample_depth: blocked=1
v2_archive_after_promotion: pending=1
```

重点 gate：

```text
prior_robustness=blocked
prior_stress_capacity_table_drift=blocked
settlement_count_cells_value_bridge_holdout=blocked
settlement_count_guarded_bridge_holdout=watch
formal_baseline_metrics=blocked
formal_value_sampler_holdout=blocked
v2_archive_readiness=pending
```

解读：

- 当前不是单一 2506 support blocker；2506 只对应 settlement bridge support lane 的 guarded candidate。
- table/activity/capacity lane 仍由 prior robustness 与 prior-stress drift 阻塞，252x missing-table 仍不能进入 default prior。
- formal/value shadow sampler lane 三个 gate 全 blocked，因此 formal/value active sampler 参数调优仍应暂停。
- v2 archive 继续 pending，必须等 v3 formal path promoted and verified 后再讨论。

## O-v3-091：guarded stability 现在可直接输出 2506 support gap

2026-06-06 给 guarded bridge holdout/stability 增加 selected support 审计后复跑：

```powershell
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --no-cache
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 256 --posterior-seed 0 --posterior-seed 1 --posterior-seed 7
```

64-trial seed 0 no-cache：

```text
overall_status=watch
selected_signature=2506:3
applied_rows=20
support_gap=2506:min_applied=20/required=20/gap=0

fold_support:
fold0 sessions=1 metric_rows=3 candidate_rows=3 applied_rows=3
fold3 sessions=4 metric_rows=11 candidate_rows=11 applied_rows=11
fold4 sessions=3 metric_rows=9 candidate_rows=6 applied_rows=6
```

256-trial seeds 0/1/7 cached matrix：

```text
overall_status=blocked_low_support
reasons=low_applied_rows
runs=3
watch_runs=3
stable_groups=2506
union_groups=2506
signatures=2506:2=3
min_applied=9
min_required=20
support_gap=2506:min_applied=9/required=20/gap=11
```

解读：

- low-support blocker 现在可由 stability 脚本直接复核。
- 64 单 seed support 达标不代表 high-trial 多 seed达标；promotion 仍以 high-trial matrix 为准。
- cached 256 matrix 能输出 group-level gap；若需要具体 selected fold support，需要刷新 no-cache high-trial run。

## O-v3-092：prior-stress consistency buckets 把 94 行拆成三类 blocker

2026-06-06 给 prior robustness audit 增加 consistency class/bucket 后复跑：

```powershell
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --detail-summary --format json
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format json
```

prior-stress detail summary：

```text
rows=94
consistency_bucket_counts:
  hard_capacity_conflict=29
  lower_bound_under_truth=39
  evidence_floor_only=26
  target_over_truth_risk=0

capacity_case_counts:
  direct_prior_max_conflict=29
  no_capacity_prior_max_case=26
  target_above_prior_but_below_truth=10
  target_lower_bound_truth_above_prior=31
  truth_above_prior_without_count_target=8
  truth_above_prior_without_target_prior_hit=8

selected consistency classes:
  capacity_truth_above_prior_not_targeted=39
  total_cells_floor_below_truth=50
  q6_cells_floor_below_truth=46
  q6_value_floor_below_truth=42
  total_cells_exact_matches_truth=37
  q6_cells_target_missing=35
  q6_value_target_missing=47
```

readiness 复核：

```text
overall_status=not_ready
blocked_gates=12
prior_stress_capacity_table_drift buckets:
  hard_capacity_conflict=29
  lower_bound_under_truth=39
  evidence_floor_only=26
```

解读：

- `hard_capacity_conflict` 是 target/truth 同时超过 prior max 的硬容量冲突，不能靠 formal/value sampler 调参关闭。
- `lower_bound_under_truth` 表示 target 只是低界或未命中，但真实 settlement 已超过 prior max，优先查 count->cells/value bridge 与结算展开语义。
- `evidence_floor_only` 是 floor/target evidence 不足或缺失，不是 promotion evidence。
- 本轮只增加审计分流和 readiness 展示；gate 数不变，v3 仍是 shadow-only。

## O-v3-093：bucketed capacity audit 显示 hard/lower-bound 是真实 table-cap gap，evidence-only 不是

2026-06-06 给 capacity table audit 增加 `--bucket` 与 `bidmap_raw_col8` 后复跑 64-trial default archive：

```powershell
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case all --bucket hard_capacity_conflict
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case all --bucket lower_bound_under_truth
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case all --bucket evidence_floor_only
```

聚合结果：

```text
details=94 errors=0

hard_capacity_conflict:
  groups=10 rows=29 table_impossible=29 round_impossible=16 verified_rows=29 col8_rows={'1': 29}
  top maps:
    2601 rows=8 col16=[[]] col17=[9999,2601,22,44] bidmap_max=44 round_cap=60 sampler_max=44 truth_max=65 raw_latest_max=65 slot_max=300
    2501 rows=6 col16=[[]] col17=[9999,2501,22,44] bidmap_max=44 round_cap=50 sampler_max=44 truth_max=60 raw_latest_max=60 slot_max=300
    2506 rows=4 col16=[[]] col17=[9999,2506,22,44] bidmap_max=44 round_cap=50 sampler_max=44 truth_max=58 raw_latest_max=58 slot_max=300

lower_bound_under_truth:
  groups=11 rows=39 table_impossible=39 round_impossible=22 verified_rows=39 col8_rows={'1': 39}
  top maps:
    2508 rows=6 col16=[[]] col17=[9999,2508,22,44] bidmap_max=44 round_cap=50 sampler_max=44 truth_max=64 raw_latest_max=64 slot_max=300
    2401 rows=5 col16=[[]] col17=[9999,2401,20,40] bidmap_max=40 round_cap=50 sampler_max=40 truth_max=53 raw_latest_max=53 slot_max=250
    2404 rows=5 col16=[[]] col17=[9999,2404,20,40] bidmap_max=40 round_cap=50 sampler_max=40 truth_max=50 raw_latest_max=50 slot_max=250

evidence_floor_only:
  groups=6 rows=26 table_impossible=0 round_impossible=0 verified_rows=26 col8_rows={'1': 26}
  top maps:
    2401 rows=5 col16=[[]] col17=[9999,2401,20,40] bidmap_max=40 round_cap=50 sampler_max=40 truth_max=40 raw_latest_max=40 slot_max=250
    2409 rows=5 col16=[[]] col17=[9999,2409,20,40] bidmap_max=40 round_cap=50 sampler_max=40 truth_max=29 raw_latest_max=29 slot_max=250
    2406 rows=5 col16=[[]] col17=[9999,2406,20,40] bidmap_max=40 round_cap=50 sampler_max=40 truth_max=25 raw_latest_max=25 slot_max=250
```

BidMap col[8] 全表复核：

```text
rows=125
col8_counts={'0': 20, '1': 105}
col8_zero_maps=2511,2512,2513,2514,2515,2516,2517,2518,2519,2520,4511,4512,4513,4514,4515,4516,4517,4518,4519,4520
```

解读：

- hard/lower-bound 68 rows 的 raw latest inventory 与 detail truth 对齐，且全部超过 current sampler possible max；这不是 parser 重复或 DropEntry `n_max` 多件数导致。
- current v300 `col[16]` 在这些 rows 均为 `[[]]`，drop-ref 是 `col[17]`；`col[17]` 的 max 是 sampler draw range，不是 final settlement inventory hard cap。
- `evidence_floor_only` 没有 table/round cap impossible，下一步应查 evidence compiler/floor source，而不是 table capacity。
- col[8] 的 `0` cohort 是后续 activity/overlay 线索，但不解释当前 94 个 prior-stressed rows。

## O-v3-094：evidence-floor-only 主要是 floor below truth 与 q6/value target missing

2026-06-06 给 prior robustness detail summary 增加 `evidence_floor_only_summary` 后复跑 64-trial default archive：

```text
details=94
bucket_counts:
  hard_capacity_conflict=29
  lower_bound_under_truth=39
  evidence_floor_only=26

evidence_floor_only rows=26
map_counts:
  2401=5
  2406=5
  2409=5
  2404=4
  2502=4
  2402=3

reason_counts:
  summary_likelihood_fallback=26
  q6_cells_above_prior=12
  q6_value_above_prior=11
  total_value_above_prior=11
  total_cells_above_prior=4
```

component issue counts：

```text
total_cells:
  floor_below_truth=21
  exact_matches_truth=5

total_value:
  floor_below_truth=22
  target_missing=4

q6_cells:
  floor_below_truth=17
  floor_matches_truth=5
  target_missing=4

q6_value:
  floor_below_truth=17
  floor_matches_truth=5
  target_missing=4
```

evidence count summary：

```text
numeric_constraints n=26 avg=5.346 p90=9 max=10
item_anchors n=26 avg=7.423 p90=10 max=20
shape_anchors n=26 avg=23.077 p90=33 max=39
quality_floor_anchors n=26 avg=2.077 p90=4 max=6
```

floor source 口径：

```text
item_anchors -> value/cells/quality floor
shape_anchors -> cells floor, optional quality
quality_floor_anchors -> quality/count only
numeric_constraints -> exact only, not floor
```

解读：

- `evidence_floor_only` 不是单一 value sampler 缺口；大多数是 cells/value floor 作为低界低于 final truth。
- `2502` 形态更具体：total cells exact matches truth，但 q6/value target missing，不能用 table cap 修复。
- 这 26 行继续保持 promotion blocker；下一步查 evidence compiler 的 floor anchor source、q6/value target 缺失与 summary-likelihood fallback。

## O-v3-095：formal/value mixed guard 后 candidate 从 13 收口到 12，holdout 仍 sample-limited

2026-06-06 对 formal/value sampler 增加 mixed value-floor guard 后，复跑真实 64-trial archive / holdout / readiness：

```text
archive rows:
  paired=1560
  formal_value_rows=1560
  pure_candidates=12
  mixed_value_floor_watch=1

status_counts:
  baseline_passthrough=1398
  watch_capacity_cells_drift=126
  watch_q6_cells_floor=23
  watch_only_value_floor_candidate=12
  watch_mixed_value_floor_guarded=1

stress_counts:
  none=1398
  capacity_cells_drift=118
  q6_cells_floor_stress=23
  value_floor_stress=12
  capacity_cells_drift+q6_cells_floor_stress=6
  q6_cells_floor_stress+capacity_cells_drift=2
  q6_cells_floor_stress+value_floor_stress=1
```

holdout 关键结果：

```text
overall_status=sample_limited
candidate_rows=0
mixed_value_floor_watch_rows=1
capacity_watch_rows=150
train_candidate_status_counts={"blocked_low_sample":414}
```

readiness 关键结果：

```text
overall_status=not_ready
blocked_gates=12
formal_value_sampler_holdout.status=blocked
formal_value_sampler_holdout.reason=formal/value sampler lacks enough safe holdout support
formal_value_sampler_holdout.candidate_rows=0
formal_value_sampler_holdout.mixed_value_floor_watch_rows=1

summary.v3_fv_candidate_rows=12
summary.v3_fv_value_floor_candidate_rows=13
summary.v3_fv_capacity_watch_rows=126
summary.v3_fv_delta_formal_p50_mae=0.0
```

解读：

- 以前看起来的 13 个 value-floor candidate 中，只有 12 个是 pure value-floor；另 1 个是 `q6_cells_floor_stress+value_floor_stress` mixed row。
- mixed row 已从 candidate 分母移出，但保留 watch 计数，避免后续 promotion 误把 cells/capacity blocker 当成 formal/value sampler 样本。
- formal/value sampler 仍缺 safe holdout support；promotion/readiness 不推进，v2 archive 也不推进。

## O-v3-096：evidence-floor-only pattern 拆出 22 个 floor 主体和 4 个 total-exact/missing-target rows

2026-06-06 给 `evidence_floor_only_summary` 增加 component pattern counts 后，复跑真实 64-trial prior robustness detail summary：

```text
evidence_floor_only rows=26

target_missing_pattern_counts:
  none=22
  q6_cells+total_value+q6_value=4

floor_below_truth_pattern_counts:
  total_cells+q6_cells+total_value+q6_value=16
  total_cells+total_value=5
  none=4
  q6_cells+total_value+q6_value=1

exact_with_target_missing_pattern_counts:
  none=21
  total_cells+q6_cells+total_value+q6_value=4
  total_cells=1
```

component issue counts 保持：

```text
total_cells:
  floor_below_truth=21
  exact_matches_truth=5
q6_cells:
  floor_below_truth=17
  floor_matches_truth=5
  target_missing=4
total_value:
  floor_below_truth=22
  target_missing=4
q6_value:
  floor_below_truth=17
  floor_matches_truth=5
  target_missing=4
```

解读：

- `evidence_floor_only` 的主体是 22 行 floor below truth，不是 target missing。
- 4 行 target missing 的模式完全一致：`q6_cells+total_value+q6_value` missing，并且同时有 total cells exact matches truth；这是 `2502` 形态。
- 后续应把 q6/value allocation target 缺失与 item/shape floor below truth 分线审计；这仍不改变 readiness、sampler 或正式出价。

## O-v3-097：capacity source split 显示 hard/lower 超 cap items 仍在 drop universe 内

2026-06-06 给 capacity table audit 增加 `source_split_summary` 后，复跑真实 64-trial hard/lower buckets：

```text
hard_capacity_conflict:
  groups=10
  rows=29
  table_impossible_rows=29
  round_impossible_rows=16
  drop_after_temp_positive_files=14
  round_after_temp_positive_files=6
  non_zodiac_missing_positive_files=0

lower_bound_under_truth:
  groups=11
  rows=39
  table_impossible_rows=39
  round_impossible_rows=22
  drop_after_temp_positive_files=18
  round_after_temp_positive_files=6
  non_zodiac_missing_positive_files=0
```

top split examples：

```text
hard map=2601 rows=8 table_impossible=8 round_impossible=3
  family=hidden prefix3=260 target_source=exact:6,floor:2
  drop_after_temp n=4 avg=9.75 p90=20 max=20
  round_after_temp n=4 avg=1 p90=4 max=4
  non_zodiac_missing max=0
  full_actions=100100:3,100134:1

hard map=2501 rows=6 table_impossible=6 round_impossible=5
  family=shipwreck prefix3=250 target_source=exact:6
  drop_after_temp n=2 avg=7 p90=13 max=13
  round_after_temp n=2 avg=3.5 p90=7 max=7
  non_zodiac_missing max=0
  public_total_count=60:1

lower map=2508 rows=6 table_impossible=6 round_impossible=6
  family=shipwreck prefix3=250 target_source=floor:6
  drop_after_temp n=3 avg=10.667 p90=14 max=14
  round_after_temp n=3 avg=4.667 p90=8 max=8
  non_zodiac_missing max=0
```

解读：

- hard/lower capacity conflict 不是 BidMap `col[16]` 读错，也不是 DropEntry `n_max>1`，也不是非 drop-universe item 或临时生肖完全解释。
- `non_zodiac_missing_positive_files=0` 表示 observed final items 属于 current drop universe；剩余 blocker 更像 session capacity / activity overlay / settlement expansion 机制，而不是 item universe 错配。
- `target_source` 在 hard bucket 中 exact/floor 均存在，在 lower bucket 中以 floor/none 为主；下一步继续按 map family 与 target source 拆 session/source split。

## O-v3-098：q6/value target missing 全部集中于 2502 且有 numeric/item/shape evidence

2026-06-06 给 `evidence_floor_only_summary` 增加 `target_missing_attribution_summary` 后，复跑真实 64-trial prior robustness detail summary：

```text
evidence_target_missing_rows=4
evidence_target_missing_maps=2502:4
evidence_floor_only_missing_patterns:
  none=22
  q6_cells+total_value+q6_value=4
```

target-missing attribution：

```text
item_anchors_present=4
item_anchors_present_value_targets_missing=4
numeric_constraints_present=4
q6_and_value_targets_missing=4
q6_cells_target_missing=4
q6_value_target_missing=4
shape_anchors_present=4
shape_anchors_present_q6_cells_target_missing=4
total_cells_exact_matches_truth=4
total_cells_exact_q6_value_targets_missing=4
total_value_target_missing=4
```

解读：

- 这 4 行不是“没有 evidence”：numeric/item/shape anchors 都存在。
- total cells exact 已经命中 truth，但 q6 cells、total value、q6 value 都没有 target；问题集中在 q6/value allocation target 编译，而不是 table capacity 或 formal/value sampler 参数。
- 下一步应查 2502 相关 evidence events 的 target set 与 anchor payload：是否存在 shape anchors 无 quality/value、item anchors 无 value，或 q6 quality floor 只产生 count 不产生 value/cells。

## O-v3-099：capacity residual modes 显示 drop-ref-only overflow 多于 round-cap overflow

2026-06-06 给 capacity table audit 增加 `residual_mode_summary` 后，复跑真实 64-trial hard/lower buckets：

```text
hard_capacity_conflict:
  groups=10
  rows=29
  table_impossible_rows=29
  round_impossible_rows=16
  residual_modes:
    drop_ref_only_overflow=8
    round_cap_overflow=6
    within_drop_ref=1

lower_bound_under_truth:
  groups=11
  rows=39
  table_impossible_rows=39
  round_impossible_rows=22
  residual_modes:
    drop_ref_only_overflow=12
    round_cap_overflow=6
    within_drop_ref=2
```

top split examples：

```text
hard map=2601:
  drop_ref_only_overflow=3
  round_cap_overflow=1
  round overflow max=4

hard map=2501:
  drop_ref_only_overflow=1
  round_cap_overflow=1
  public_total_count=60:1 on round-cap overflow row

lower map=2508:
  drop_ref_only_overflow=1
  round_cap_overflow=2
  round overflow max=8

lower map=2401:
  drop_ref_only_overflow=3
  within_drop_ref=1
```

解读：

- hard/lower conflict 中可验证 raw files 多数是 `drop_ref_only_overflow`，不是全部都超过 round cap。
- `drop_universe_gap=0` 保持，说明这些 rows 不由非 drop-universe items 主导。
- 下一步应优先解释 `col[17] max` 与 final settlement count 的语义差异；round-cap overflow 子集再单独查 settlement expansion / activity overlay。

## O-v3-100：2502 target-missing event audit 显示 q6/value targets 未进入 prebid constraints

2026-06-06 新增 target-missing event audit 后，复跑真实 64-trial archive：

```powershell
python scripts\summarize_v3_target_missing_event_audit.py --posterior-trials 64 --format summary
```

结果：

```text
selected_rows=4
audited_rows=4
errors=0
maps=2502:4
missing_patterns=q6_cells+total_value+q6_value:4
key_target_presence:
  session.total_count=0/4
  session.total_cells=4/4
  bucket.q6.count=0/4
  bucket.q6.cells=0/4
  bucket.q6.value=0/4
anchor_source_ids:
  action_result:100153=10
  skill_reveal:1001034=10
  action_result:100158=6
  skill_reveal:1001033=6
  action_result:100154=3
  skill_reveal:1001032=3
  skill_reveal:1001031=1
```

逐行解读：

```text
prebid_r1:
  total_cells_exact=156
  known_count_floor=6
  known_cells_floor=14
  known_value_floor=0
  q6_count/cells/value exact=None
  q6_count/cells/value floor=0

prebid_r2:
  known_count_floor=8
  known_cells_floor=18
  q6_count/cells/value floor=0

prebid_r3:
  known_count_floor=25
  known_cells_floor=83
  q6_count/cells/value floor=0

prebid_r4:
  known_count_floor=36
  known_cells_floor=115
  q6_count/cells/value floor=0
```

解读：

- 2502 target-missing rows 均有 `session.total_cells=156` exact，但没有 `bucket.q6.*` target。
- item anchors 与 shape anchors 都有形状/格子信息，但 `item_anchors.with_value=0`，`shape_anchors.q6_count=0`，`quality_floor_anchors=0`。
- 事件来源集中在 Aisha q1-q5/category/shape reveal；没有 q6 或 value exact/floor payload 能支撑 `q6_cells`、`total_value`、`q6_value` target。
- 下一步如果恢复 sampler 设计，必须先设计 shadow-only q6/value allocation target 或明确保持这些 rows out-of-scope；不能把它们作为 formal/value sampler candidate。

## O-v3-101：2502 只有 r4 可由 q1-q5 cells residual 派生 q6 cells

2026-06-06 给 target-missing event audit 增加 `q6_residual_target_candidate` 后，复跑真实 64-trial archive：

```powershell
python scripts\summarize_v3_target_missing_event_audit.py --posterior-trials 64 --format summary
```

结果：

```text
selected_rows=4
audited_rows=4
q6_residual_patterns=none:3,cells:1
q6_residual_cells=missing_non_q6_exact:3,derived:1
```

逐行 residual status：

```text
prebid_r1:
  cells=missing_non_q6_exact
  missing_non_q6_qualities=2,3,4,5

prebid_r2:
  cells=missing_non_q6_exact
  missing_non_q6_qualities=3,4,5

prebid_r3:
  cells=missing_non_q6_exact
  missing_non_q6_qualities=4,5

prebid_r4:
  cells=derived
  total_cells_exact=156
  non_q6_cells_exact_sum=134
  derived_q6_cells=22
  truth_delta=0
```

解读：

- 2502 r4 的 Aisha q1-q5 cells exact 与 session total cells exact 构成完整 cells residual，可派生 q6 cells exact candidate。
- r1-r3 只能证明部分非 q6 buckets，不能把 remaining cells 全部归给 q6。
- 四行都缺 session count exact，所以 q6 count 不能 residual 派生；四行都缺 session value exact/q1-q5 value exact 完整分区，所以 q6 value 与 formal value 不能 residual 派生。
- 这支持下一步做 shadow-only q6 cells residual candidate，但不支持 formal/value promotion 或 value sampler 上调。

## O-v3-102：v3 pipeline/evaluate 可稳定输出 2502 r4 的 q6 cells residual candidate

2026-06-06 将 q6 residual target candidate 接入 `estimate_shadow_pipeline` 与 archive evaluate 后，复跑真实 2502 capture：

```powershell
python scripts\evaluate_fatbeans_v3_samples.py data\samples\fatbeans\fatbeans_valid_aisha_2502_4rounds_2502_1295018709694048_0149.json --posterior-trials 64 --format summary
```

summary 输出：

```text
windows=4
ready=4
v3_rtc_candidate_rows=1
v3_rtc_active_rows=0
```

逐行诊断：

```text
prebid_r1:
  candidate=False
  active=False
  affects_bid=False
  count_status=missing_total_exact
  cells_status=missing_non_q6_exact
  value_status=missing_total_exact

prebid_r2:
  candidate=False
  cells_status=missing_non_q6_exact

prebid_r3:
  candidate=False
  cells_status=missing_non_q6_exact

prebid_r4:
  candidate=True
  active=False
  affects_bid=False
  derived_fields=cells
  count_status=missing_total_exact
  cells_status=derived
  cells_value=22
  truth_q6_cells=22
  value_status=missing_total_exact
```

解读：

- pipeline/evaluate 与单独 target-missing audit 的结论一致：只有 r4 满足 q1-q5 cells residual 条件。
- `v3_rtc_active_rows=0` 确认该诊断没有进入 sampler 或 bidding 行为。
- CSV header 已包含 `v3_rtc_available`、`v3_rtc_candidate`、`v3_rtc_q6_cells_value`，后续 archive/live/readiness 统计可以直接消费这些字段。

## O-v3-103：guarded settlement bridge seed-0 watch 不具备多 seed 稳定性

2026-06-06 复跑 guarded settlement bridge stability matrix：

```powershell
python scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --posterior-seed 1 --format summary
```

结果：

```text
overall_status=blocked_applied_hurt
reasons=applied_hurts_present,non_watch_run,selected_group_drift
runs=2
watch_runs=1
required_groups=2506
stable_groups=2506
union_groups=2501,2506
min_applied=20
min_required=20
signatures=2501:1,2506:2=1;2506:3=1
```

逐 seed：

```text
seed=0:
  status=watch
  selected=2506
  applied_rows=20
  delta_mae=-6000.0
  delta_p90=0.0
  bridge_over=0.25
  applied_hurts=-

seed=1:
  status=blocked_holdout_hurt
  selected=2501,2506
  applied_rows=62
  delta_mae=378.95
  delta_p90=0.016129
  bridge_over=0.580645
  applied_hurts=2501
```

readiness 接入验证：

```powershell
python scripts\summarize_v3_promotion_readiness.py data\samples\fatbeans\fatbeans_valid_aisha_2502_4rounds_2502_1295018709694048_0149.json --posterior-trials 64 --guarded-bridge-stability-json .tmp\codex\v3_readiness\scp_guarded_stability_64_s0_s1.json --format summary
```

关键输出：

```text
scp_guarded_stability=blocked_applied_hurt
scp_guarded_stable_groups=2506
gate=settlement_count_guarded_bridge_stability status=blocked reason="guarded settlement bridge is not stable across posterior seeds"
```

解读：

- `2506` 仍是稳定交集，但 seed 1 的 union group 引入 `2501` 且发生 hurt，说明 guard selection 尚不稳定。
- 当前 settlement count-prior bridge 只能保持 shadow/readiness blocker；不能进入 formal/value promotion 支持。
- readiness 已能区分“未评估 stability”与“已评估但 multi-seed failed”，减少后续误读。

## O-v3-104：guarded bridge stability 的 hurt 与 support gap 可直接定位到 2501/2506

2026-06-06 给 stability audit 增加 cache schema 与 selected support summary 后，重算真实 64-trial seed0/seed1 matrix：

```powershell
python scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --posterior-seed 1 --format summary
```

结果：

```text
overall_status=blocked_applied_hurt
reasons=applied_hurts_present,non_watch_run,selected_group_drift
runs=2
watch_runs=1
required_groups=2506
stable_groups=2506
union_groups=2501,2506
min_applied=20
min_required=20
signatures=2501:1,2506:2=1;2506:3=1
```

逐 seed：

```text
seed=0:
  status=watch
  selected=2506
  selected_signature=2506:3
  cache_hit=False
  applied_rows=20
  delta_mae=-6000.0
  bridge_over=0.25
  applied_hurts=-

seed=1:
  status=blocked_holdout_hurt
  selected=2501,2506
  selected_signature=2501:1,2506:2
  cache_hit=False
  applied_rows=62
  delta_mae=378.95
  bridge_over=0.580645
  applied_hurts=2501
```

selected support：

```text
2501:
  runs=1
  folds=1
  min_applied=53
  max_applied=53
  hurts=1
  missing_support=0

2506:
  runs=2
  folds=5
  min_applied=9
  max_applied=20
  hurts=0
  missing_support=0
  support_gap=11
```

解读：

- `2501` 是真实 hurt group，不是 stale cache 或缺 support 造成的假象。
- `2506` 是 stable intersection，但跨 seed 最小 applied support 只有 9，低于当前 required 20。
- 当前 guarded bridge blocker 分成两条：排除/解释 `2501` hurt selection，以及提升 `2506` 的多 seed applied support。
- 该结果继续支持 shadow-only / readiness blocked，不支持 formal/value promotion。

## O-v3-105：2501 在 train guard 中通过，但外层 holdout 出现 over-risk/hurt

2026-06-06 给 guarded bridge holdout/stability 增加 train-guard metrics 后，复跑真实 64-trial seed0/seed1 matrix：

```powershell
python scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --posterior-seed 1 --format summary
```

结果：

```text
overall_status=blocked_applied_hurt
reasons=applied_hurts_present,non_watch_run,selected_group_drift
stable_groups=2506
union_groups=2501,2506
```

selected guard：

```text
2501:
  runs=1
  folds=1
  statuses=watch_train_guard=1
  min_guard_sessions=59
  max_guard_delta=-1707.317
  max_guard_over=0.414634

2506:
  runs=2
  folds=5
  statuses=watch_train_guard=5
  min_guard_sessions=14
  max_guard_delta=-3387.097
  max_guard_over=0.370968
```

selected support：

```text
2501:
  runs=1
  folds=1
  min_applied=53
  max_applied=53
  hurts=1
  missing_support=0

2506:
  runs=2
  folds=5
  min_applied=9
  max_applied=20
  hurts=0
  missing_support=0
  support_gap=11
```

解读：

- `2501` 的问题不是 guard 没有跑，也不是 support 缺失；它在训练 guard 中看起来安全，但外层 holdout 仍然 hurt。
- `2506` 的问题不是 hurt，而是跨 seed applied support 不足。
- 因此 guarded settlement bridge 下一步应分两线：收紧/解释 `2501` train-holdout instability，继续累积或重设 `2506` support；当前不能作为 formal/value promotion evidence。

## O-v3-106：selected instability 将 2501 hurt 与 2506 support gap 分开

2026-06-06 给 guarded bridge stability 增加 `selected_group_instability_summary` 后，复跑真实 64-trial seed0/seed1 matrix：

```powershell
python scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --posterior-seed 1 --format summary
```

关键输出：

```text
overall_status=blocked_applied_hurt
stable_groups=2506
union_groups=2501,2506

selected_instability=2501:blocked_train_holdout_instability/gap=0/hurts=1/watch_guard=1;2506:blocked_support_depth_gap/gap=11/hurts=0/watch_guard=5
```

JSON 分类：

```text
2501:
  status=blocked_train_holdout_instability
  reasons=train_guard_watch_but_holdout_hurt

2506:
  status=blocked_support_depth_gap
  reasons=min_applied_rows_below_required
```

解读：

- `2501` 的下一步是解释为什么 train guard watch 但外层 holdout over-risk/hurt，或给它建立 explicit exclusion/diagnostic。
- `2506` 的下一步是增加或验证支持深度；它当前不是 hurt group。
- 该分类使 settlement bridge blocker 可拆解，但不提供 promotion 证据。

## O-v3-107：capacity semantic status 确认 2501/2506/2601 是 after-temp round-cap overflow

2026-06-06 给 `summarize_v3_capacity_table_audit.py` 增加 `capacity_semantic_summary` 后，复跑真实 direct/hard capacity conflict：

```powershell
python scripts\summarize_v3_capacity_table_audit.py --case direct_prior_max_conflict --bucket hard_capacity_conflict --posterior-trials 64 --top 8 --format summary
```

关键输出：

```text
case=direct_prior_max_conflict bucket=hard_capacity_conflict groups=10

2601:
  raw_inventory=verified_latest_inventory
  raw_truth_match_rows=8/8
  drop_ref_col=17 raw_col16="[[]]" raw_col17="[9999,2601,22,44]"
  sampler_nmax_gt1=0 sampler_leaf_nmax=max=1.0
  raw_drop_excess_after_temp=max=20
  raw_round_excess_after_temp=max=4
  semantic_status=blocked_round_cap_overflow_after_temp

2501:
  raw_truth_match_rows=6/6
  raw_drop_excess_after_temp=max=13
  raw_round_excess_after_temp=max=7
  semantic_status=blocked_round_cap_overflow_after_temp

2506:
  raw_truth_match_rows=4/4
  raw_drop_excess_after_temp=max=13
  raw_round_excess_after_temp=max=7
  semantic_status=blocked_round_cap_overflow_after_temp

2401:
  raw_drop_excess_after_temp=max=0
  raw_round_excess_after_temp=max=0
  semantic_status=watch_activity_extras_explain_drop_ref_gap
```

解读：

- `2601` / `2501` / `2506` 不是旧 `BidMap.col[16]` 误读，也不是 DropEntry `n_max>1` 遗漏；current v300 drop-ref 是 `col[17]`，leaf `n_max=1`。
- 0x002D raw candidate count 与 occupied slot count 均匹配 parsed inventory，detail truth 也匹配 latest inventory；这支持 settlement truth count 是真实 final occupied inventory count。
- 这些 top blocker 扣除临时 zodiac extras 后仍超过 `col[14]` round-cap candidate，因此 `items_per_session_max` 与 round-cap candidate 都不能当作 final settlement inventory hard cap。
- `2401` 展示了另一类情况：该 map 的 drop-ref gap 可被临时 zodiac extras 解释，应作为 watch，不应和 after-temp blocker 混为一类。

## O-v3-108：capacity semantic matrix 拆出 source/action/public-total cell

2026-06-06 给 `summarize_v3_capacity_table_audit.py` 增加 `capacity_semantic_matrix` 后，复跑 hard 与 lower bucket：

```powershell
python scripts\summarize_v3_capacity_table_audit.py --case direct_prior_max_conflict --bucket hard_capacity_conflict --posterior-trials 64 --top 8 --format summary
python scripts\summarize_v3_capacity_table_audit.py --case all --bucket lower_bound_under_truth --posterior-trials 64 --top 8 --format summary
```

hard bucket 关键 matrix cells：

```text
hard_capacity_conflict/round_cap_overflow/shipwreck/exact/no_full_action/has_public_total/none:
  rows=5 files=1 maps=2501:5 status=blocked_round_cap_overflow_after_temp

hard_capacity_conflict/round_cap_overflow/shipwreck/floor/has_full_action/no_public_total/none:
  rows=4 files=1 maps=2506:4 status=blocked_round_cap_overflow_after_temp

hard_capacity_conflict/drop_ref_only_overflow/hidden/exact/has_full_action/no_public_total/none:
  rows=3 files=2 maps=2601:3 status=blocked_drop_ref_overflow_after_temp

hard_capacity_conflict/within_drop_ref/villa/exact/has_full_action/no_public_total/none:
  rows=2 files=1 maps=2401:2 status=watch_activity_extras_explain_drop_ref_gap
```

lower bucket 关键 matrix cells：

```text
lower_bound_under_truth/drop_ref_only_overflow/villa/floor/no_full_action/no_public_total/none:
  rows=8 files=4 maps=2406:4,2401:3,2404:1 status=blocked_drop_ref_overflow_after_temp

lower_bound_under_truth/drop_ref_only_overflow/villa/none/no_full_action/no_public_total/none:
  rows=8 files=3 maps=2404:4,2410:3,2401:1 status=blocked_drop_ref_overflow_after_temp

lower_bound_under_truth/round_cap_overflow/shipwreck/floor/no_full_action/no_public_total/none:
  rows=6 files=3 maps=2508:5,2504:1 status=blocked_round_cap_overflow_after_temp

lower_bound_under_truth/within_drop_ref/shipwreck/floor/no_full_action/no_public_total/none:
  rows=1 files=1 maps=2501:1 status=watch_activity_extras_explain_drop_ref_gap
```

解读：

- hard 2501 的 strongest cell 带 `public_total` 且仍 round-cap overflow，优先查 public-total/settlement truth 与 round-cap semantics。
- hard 2506 的 strongest cell 是 floor + full action + round-cap overflow，优先查 action mirror / settlement expansion，而不是公开总数。
- lower bucket 的 villa/shipwreck 主要是 floor/no-action/no-public 的 drop-ref overflow，和 hard bucket 的 direct exact/public/action 证据形态不同。
- `within_drop_ref` cell 已按 cell-level status 标为 activity watch，未再继承 map-level blocked；这避免把可解释子集误当成 promotion blocker。

## O-v3-109：source/expansion 下钻确认 hard cell 的 public/action 与 latest inventory 对齐

2026-06-06 新增 `summarize_v3_capacity_source_expansion_audit.py` 后，复跑 hard direct cell：

```powershell
python scripts\summarize_v3_capacity_source_expansion_audit.py --case direct_prior_max_conflict --bucket hard_capacity_conflict --posterior-trials 64 --top 5 --format summary
```

关键输出：

```text
2501 hard/public-total cell:
  latest=60
  non_temp=57
  drop_after=13
  round_after=7
  public=60
  public_delta=0
  action_delta=-42
  file=fatbeans_valid_aisha_2501_5rounds_2501_1295018669960456_0139.json

2506 hard/full-action cell:
  latest=58
  non_temp=57
  drop_after=13
  round_after=7
  full_actions=100134
  action_delta=0
  file=fatbeans_valid_ethan_2506_4rounds_2506_1274128029648919_0336.json

2601 hard/drop-ref-only full-action cell:
  latest=55/60
  non_temp=52/53
  drop_after=8/9
  round_after=0
  full_actions=100100
  action_delta=0

2601 hard/round-cap full-action cell:
  latest=65
  non_temp=64
  drop_after=20
  round_after=4
  full_actions=100100
  action_delta=0
```

lower bucket 对照：

```powershell
python scripts\summarize_v3_capacity_source_expansion_audit.py --case all --bucket lower_bound_under_truth --posterior-trials 64 --top 5 --format summary
```

关键输出：

```text
lower/drop-ref-only/villa/floor/no-public/no-full-action:
  rows=8 files=4
  action_delta avg=-43.25
  public_delta none

lower/round-cap/shipwreck/floor/no-public/no-full-action:
  rows=6 files=3
  latest avg=63
  non_temp avg=58.33
  round_after avg=8.33
  action_delta avg=-56.67
```

解读：

- hard 2501 public total 与 latest settlement inventory 完全一致，但扣除 zodiac 后仍超过 round-cap；这支持继续查 round-cap/session expansion semantics。
- hard 2506/2601 的 full observed action 覆盖 latest inventory，说明 action mirror 支持 final count，不是 parser 重复或 partial action 误读。
- lower bucket 多数 no-public/no-full-action，action max 远低于 latest inventory；它应作为 floor target completeness / expansion 分离问题，不应直接套用 hard cell 结论。

## O-v3-110：lower-bound target completeness summary 将 39 行拆成 21/10/8

2026-06-06 增强 `summarize_v3_prior_robustness_audit.py --detail-summary` 后，复跑：

```powershell
python -m py_compile scripts\summarize_v3_prior_robustness_audit.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_prior_robustness_audit.py -q
python scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --detail-summary --detail-summary-top 8 --detail-summary-by consistency_bucket --format summary
```

测试结果：

```text
4 passed in 0.90s
```

真实 lower-bound summary 关键输出：

```text
lower_bound_rows=39
lower_bound_target_completeness=
  floor_count_target_below_prior_and_truth:21
  count_target_above_prior_but_below_truth:10
  missing_count_target_truth_above_prior:8
lower_bound_capacity_cases=
  target_lower_bound_truth_above_prior:31
  target_above_prior_but_below_truth:10
  truth_above_prior_without_count_target:8
  truth_above_prior_without_target_prior_hit:8
lower_bound_count_sources=floor:31,none:8
lower_bound_target_truth_delta=n=31/avg=-25.968/p90=-9.0/max=-8.0
lower_bound_target_truth_counts=below=31/match=0/above=0
```

解读：

- lower bucket 不是单一 “capacity conflict”；其中 21 行的 count floor 甚至低于 prior 与 truth，10 行虽超过 prior 但仍低于 truth，8 行缺 count target。
- 31 条有 count target 的 lower rows 全部低于 truth，因此 lower bucket 应继续查 target completeness、table/source semantics 与 settlement expansion 分离。
- 该观察不支持恢复 formal/value sampler 参数调优，也不是 promotion evidence。

## O-v3-111：table timing smoke 确认 col[17] 与 Drop leaf `n_max=1`

2026-06-06 增强 `summarize_v3_archive_table_timing.py` 后，复跑：

```powershell
python -m py_compile scripts\summarize_v3_archive_table_timing.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_archive_table_timing.py -q
python scripts\summarize_v3_archive_table_timing.py --format summary
```

测试结果：

```text
2 passed in 1.79s
```

真实 raw/table timing 关键输出：

```text
raw_file_version=300
raw_tables_file_version=300
bidmap_rows=125
bidmap_column_counts=23:125
bidmap_col16_values=[[]]:125
bidmap_col16_drop_ref_like=0
bidmap_col17_drop_ref_like=125
bidmap_drop_ref_pairs=22-44:41,20-40:30,16-32:22,18-36:20,12-24:7,14-28:5
capture_version_like_keys=-
```

priority maps：

```text
2401/2404/2406: col17=[9999,map,20,40], round_caps=[50,50,50,50,50], col16=[[]]
2501/2506/2508: col17=[9999,map,22,44], round_caps=[50,50,50,50,50], col16=[[]]
2601: col17=[9999,2601,22,44], round_caps=[60,60,60,60,60], col16=[[]]
```

Drop reachability：

```text
2401/2404/2406/2501/2506/2508:
  visited_pools=68
  leaf_entries=924
  leaf_n_ranges=1-1:924
  leaf_n_max_max=1

2601:
  visited_pools=14
  leaf_entries=587
  leaf_n_ranges=1-1:587
  leaf_n_max_max=1
```

解读：

- 当前 raw v300 字段口径确认：drop-ref 在 `BidMap.col[17]`，`col[16]` 是空占位。
- priority maps 的 Drop leaf count range 全部 `n_max=1`，不能解释 settlement item-count 高于 `drop_ref.items_max`。
- archive capture 没有 version/hash-like 字段，因此 table timing 仍不能证明每条 session 的服务端表版本；剩余 blocker 指向 settlement expansion/session-capacity/server-side overlay 语义。

## O-v3-112：settlement residual-mode smoke 证明 final inventory 稳定但不解释 expansion 来源

2026-06-06 增强 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 8 --format summary
```

测试结果：

```text
3 passed in 0.58s
```

真实 residual-mode 输出：

```text
files=441
settlement_rows=441
slot_counts=300:251,250:186,232:1,252:1,253:1,254:1
slot_headroom_after_temp=n=441/avg=238.58/p50=247.0/p90=268.0/p95=271.0/max=277.0
residual_modes=
  within_drop_ref_after_temp:245
  drop_ref_only_overflow_after_temp:113
  round_cap_overflow_after_temp:59
  activity_extras_only_drop_ref_gap:24
above_drop_after_temp=172
above_round_after_temp=59
payload_mismatch_rows=2
full_action_rows=18
public_total_rows=26
public_total_match_rows=26
public_total_delta=n=26/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0
```

Over-cap residual groups：

```text
drop_ref_only_overflow_after_temp:
  files=113
  drop_excess_after_temp avg=4.363 p90=8 max=12
  round_excess_after_temp max=0
  payload_mismatch=0/113
  full_action_rows=7/113
  public_total_rows=11/113
  public_total_match_rows=11/113

round_cap_overflow_after_temp:
  files=59
  drop_excess_after_temp avg=11.407 p90=16 max=20
  round_excess_after_temp avg=4.356 p90=9 max=12
  payload_mismatch=0/59
  full_action_rows=3/59
  public_total_rows=4/59
  public_total_match_rows=4/59
```

解读：

- after-temp over-cap rows 的 payload candidate/occupied 与 final inventory 对齐，且 public total 出现时也完全对齐。
- 这证明 parser/truth 是 final settlement inventory，不支持 “payload 重复/解析膨胀”。
- 但 full action/public total 覆盖率很低，且 payload slot headroom 是大容量 grid/slot 背景，不是生成机制；仍需查 server-side expansion/session-capacity/source semantics。

## O-v3-113：round/session 分组显示 over-cap 跨早晚轮与 25/30-round map 存在

2026-06-06 增强 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by round_index --min-samples 1 --top 8 --format summary
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by capture_rounds --min-samples 1 --top 8 --format summary
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by bidmap_rounds_total --min-samples 1 --top 8 --format summary
```

整体分布：

```text
round_indices=3:147,2:114,4:104,1:49,none:26,5:1
capture_rounds=4:146,3:115,5:105,2:48,1:27
bidmap_rounds_total=30:253,25:188
residual_modes=within_drop_ref_after_temp:245,drop_ref_only_overflow_after_temp:113,round_cap_overflow_after_temp:59,activity_extras_only_drop_ref_gap:24
```

按 capture rounds：

```text
capture_rounds=1:
  above_drop_after_temp=12/27
  above_round_after_temp=8/27

capture_rounds=2:
  above_drop_after_temp=15/48
  above_round_after_temp=4/48

capture_rounds=3:
  above_drop_after_temp=33/115
  above_round_after_temp=7/115

capture_rounds=4:
  above_drop_after_temp=72/146
  above_round_after_temp=24/146

capture_rounds=5:
  above_drop_after_temp=40/105
  above_round_after_temp=16/105
```

按 BidMap `rounds_total`：

```text
bidmap_rounds_total=30:
  files=253
  above_drop_after_temp=110/253
  above_round_after_temp=46/253

bidmap_rounds_total=25:
  files=188
  above_drop_after_temp=62/188
  above_round_after_temp=13/188
```

解读：

- over-cap 并非只发生在 late-round capture；1/2-round captures 也存在扣除临时 zodiac 后的 drop-ref/round-cap overflow。
- 30-round map 的 overflow 更重，但 25-round villa 也有稳定 overflow，因此不能把 blocker 归为 30-round map 专属容量。
- round/session 维度目前只能排除简单解释，不能提供 promotion-ready sampler cap。

## O-v3-114：payload field-shape 不显示 over-cap 专属展开块

2026-06-06 增强 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
```

整体 payload field 分布：

```text
files=441 settlement_rows=441
payload_f5 max=4
payload_f6 max=5
payload_f7 max=2
payload_f8 max=5
payload_f20_rows=436/441
payload_mismatch_rows=2/441
```

按 residual mode：

```text
drop_ref_only_overflow_after_temp:
  files=113
  payload_mismatch=0/113
  payload_f20_rows=113/113
  payload_f5 max=4
  payload_f8 max=5

round_cap_overflow_after_temp:
  files=59
  payload_mismatch=0/59
  payload_f20_rows=59/59
  payload_f5 max=4
  payload_f8 max=5

within_drop_ref_after_temp:
  files=245
  payload_mismatch=2/245
  payload_f20_rows=240/245
  payload_f5 max=4
  payload_f8 max=5
```

解读：

- field 5/6/7/8 count 与 field 5/8 child signatures 在 over-cap 与 within-cap rows 中共享同类结构；当前没有 over-cap 专属的 payload block 证据。
- field20 几乎总存在，但 value 呈每局唯一/近唯一分布，不像稳定 source id、activity id 或 expansion classifier。
- 结合 over-cap rows `raw_candidate_delta=0` 与 `occupied_delta=0`，当前更像服务端正常 final settlement occupancy 高于 BidMap drop-ref prior max，而不是 parser 把额外字段重复算进 inventory。

## O-v3-115：本机 v303 新增 252x/452x BidMap 但不解释 default overflow

2026-06-06 增强 `summarize_v3_archive_table_timing.py` 后，对本机游戏源复跑：

```powershell
python scripts\summarize_v3_archive_table_timing.py data\samples\fatbeans_activity_20260605_shipwreck --raw-root C:\xiangmuyunxing\steamapps\common\BidKing\BidKing_Data\StreamingAssets --format summary
```

关键输出：

```text
raw_file_version=303
filelist_header="Ver:303|FileCount:4550"
bidmap_rows=165
bidmap_col16_values=[[]]:165
bidmap_col17_drop_ref_like=165

activity_range=2521-2530 bidmap_present=10 bidmap_missing=0 drop_present=0 drop_missing=10 drop_ref_pairs=22-44:10
activity_range=4521-4530 bidmap_present=10 bidmap_missing=0 drop_present=0 drop_missing=10 drop_ref_pairs=22-44:10
```

priority map 对比：

```text
2401: v303 col17=[9999,2401,20,40], round_caps=[50,50,50,50,50]
2501: v303 col17=[9999,2501,22,44], round_caps=[50,50,50,50,50]
2506: v303 col17=[9999,2506,22,44], round_caps=[50,50,50,50,50]
2508: v303 col17=[9999,2508,22,44], round_caps=[50,50,50,50,50]
2601: v303 col17=[9999,2601,22,44], round_caps=[60,60,60,60,60]
```

解读：

- 本机游戏源已更新到 v303，项目 `data/raw` 仍是 v300；0605 晚间 activity capture 与 v303 时间相容。
- v303 BidMap 新增 `2521-2530` / `4521-4530`，但对应 Drop pool 仍不存在；activity cohort 仍是 missing-drop/source-overlay 问题。
- v303 对 default priority maps 的 drop-ref/round-cap 未改变，Drop reachable leaf `n_max=1` 仍不变，因此不能用 v303 table drift 解释默认 24xx/25xx/2601 settlement count overflow。

## O-v3-116：field[4] slot/source shape 不显示 over-cap 专属 marker

2026-06-06 增强 `summarize_v3_settlement_payload_audit.py` 与 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
```

整体 slot/source shape：

```text
files=441 settlement_rows=441
slot_counts=300:251,250:186,232:1,252:1
candidate_paths=3:18310
residual_modes=within_drop_ref_after_temp:245,drop_ref_only_overflow_after_temp:113,round_cap_overflow_after_temp:59,activity_extras_only_drop_ref_gap:24
```

按 residual mode：

```text
drop_ref_only_overflow_after_temp:
  files=113
  occupied_slot_shapes=1:0:i,2:2:b,3:2:b:5355,2:2:b,3:2:b:113
  empty_slot_shapes=1:0:i,2:2:b,3:2:b:25982
  occupied_slot_int_fields=1:5355
  empty_slot_int_fields=1:25982
  candidate_paths=3:5468

round_cap_overflow_after_temp:
  files=59
  occupied_slot_shapes=1:0:i,2:2:b,3:2:b:3263,2:2:b,3:2:b:59
  empty_slot_shapes=1:0:i,2:2:b,3:2:b:13728
  occupied_slot_int_fields=1:3263
  empty_slot_int_fields=1:13728
  candidate_paths=3:3322

within_drop_ref_after_temp:
  files=245
  occupied_slot_shapes=1:0:i,2:2:b,3:2:b:8210,2:2:b,3:2:b:244,1:0:i,2:2:b,2:0:i,3:2:b,3:2:b:1
  empty_slot_shapes=1:0:i,2:2:b,3:2:b:59232,:2,1:0:i,2:2:b,2:0:i:1,1:0:i,2:2:b,4:2:b,6:0:i,9:0:i,3:2:b,3:2:b,3:2:b:1
  occupied_slot_int_fields=1:8211,2:1
  empty_slot_int_fields=1:59234,2:1,6:1,9:1
  candidate_paths=3:8455
```

解读：

- item candidates 在所有 residual groups 中都走 slot child path `3`，over-cap groups 没有不同的递归路径。
- over-cap 与 within-cap 共享 dominant occupied/empty slot shapes；over-cap slot 顶层 int field 只有 field `1`，更像本地 slot index。
- 少量额外 int fields `2/6/9` 出现在 within-cap/overall，不在 over-cap groups 中，因此不是 over-cap source/award/activity marker。
- 当前 evidence 继续支持“final settlement inventory 解析稳定，但生成/占用机制仍未解释”；不能据此恢复 sampler 参数调优或 promotion readiness。

## O-v3-117：0x002D outer wrapper 不显示 over-cap 专属 source/expansion marker

2026-06-06 增强 `summarize_v3_settlement_payload_audit.py` 与 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
python scripts\summarize_v3_settlement_payload_audit.py --top 4 --format summary
```

整体 outer wrapper 分布：

```text
files=441 settlement_rows=441
outer_shapes=1:0:ix1,2:2:bx1,5:0:ix1,6:2:bx4:193,1:0:ix1,2:2:bx1,6:2:bx4:109,1:0:ix1,2:2:bx1,3:0:ix1,4:0:ix1,5:0:ix1,6:2:bx4:80,1:0:ix1,2:2:bx1,3:0:ix1,4:0:ix1,6:2:bx4:53
outer_f3_rows=134
outer_f4_rows=134
outer_f5_rows=276
outer_f6=n=441/avg=3.998/p50=4.0/p90=4.0/p95=4.0/max=8.0
```

按 residual mode：

```text
drop_ref_only_overflow_after_temp:
  files=113
  outer_f3_rows=34/113
  outer_f4_rows=34/113
  outer_f5_rows=70/113
  outer_f6=n=113/avg=4.009/p50=4.0/p90=4.0/p95=4.0/max=5.0

round_cap_overflow_after_temp:
  files=59
  outer_f3_rows=20/59
  outer_f4_rows=20/59
  outer_f5_rows=31/59
  outer_f6=n=59/avg=4.0/p50=4.0/p90=4.0/p95=4.0/max=4.0

within_drop_ref_after_temp:
  files=245
  outer_f3_rows=74/245
  outer_f4_rows=74/245
  outer_f5_rows=162/245
  outer_f6=n=245/avg=3.992/p50=4.0/p90=4.0/p95=4.0/max=8.0
```

解读：

- dominant 0x002D outer wrapper shapes 同时出现在 over-cap 与 within-cap rows。
- field3/4 成对出现，field5/loss_units 混合出现，均不是 over-cap 专属。
- field6 count 基本为 4，异常值分散，不是稳定 source、activity、award 或 expansion classifier。
- 当前 settlement wrapper/context evidence 仍只能证明 parser/truth 稳定，不能解释生成机制或支持 sampler cap promotion。

## O-v3-118：capture day/session prefix 不能单独解释 settlement over-cap

2026-06-06 增强 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by capture_day --min-samples 1 --top 8 --format summary
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by session_token_prefix6 --min-samples 1 --top 8 --format summary
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by session_token_prefix8 --min-samples 1 --top 8 --format summary
```

整体 cohort 分布：

```text
files=441 settlement_rows=441
capture_days=20260531:165,20260601:91,20260605:75,20260530:55,20260604:33,20260528:8,20260529:6,20260602:6
session_p6=129501:369,127412:64,136751:8
residual_modes=within_drop_ref_after_temp:245,drop_ref_only_overflow_after_temp:113,round_cap_overflow_after_temp:59,activity_extras_only_drop_ref_gap:24
above_drop_after_temp=172
above_round_after_temp=59
```

按 capture day：

```text
20260531 files=165 above_drop_after=65 above_round_after=22 session_p6=129501:165
20260601 files=91 above_drop_after=41 above_round_after=14 session_p6=129501:91
20260605 files=75 above_drop_after=30 above_round_after=10 session_p6=129501:67,136751:8
20260530 files=55 above_drop_after=19 above_round_after=6 session_p6=127412:48,129501:7
20260604 files=33 above_drop_after=11 above_round_after=4 session_p6=129501:33
```

按 session token prefix6：

```text
129501 files=369 above_drop_after=146 above_round_after=49 capture_days=20260531:165,20260601:91,20260605:67,20260604:33,20260530:7,20260602:6
127412 files=64 above_drop_after=21 above_round_after=9 capture_days=20260530:48,20260528:8,20260529:6,20260527:2
136751 files=8 above_drop_after=5 above_round_after=1 capture_days=20260605:8
```

解读：

- after-temp over-cap 分布在多个 capture days 和 session token prefix families 中，不是单一 capture cohort 或单一 session family 的现象。
- `127412` 与 `129501` 两个主要 prefix 都有 drop/round overflow；`136751` 样本量太小，不能解释 default blocker。
- 该证据继续削弱“简单 per-session table/version switch”解释，但仍不能证明真实 settlement expansion/source 机制。
- 当前 blocker 仍需查 server-side settlement occupancy/source semantics 或可复核外部 overlay table；不能恢复 sampler 参数调优。

## O-v3-119：after-temp settlement over-cap 不来自非生肖 Drop-universe 缺口

2026-06-06 增强 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
```

整体 Drop universe coverage：

```text
files=441 settlement_rows=441
missing_drop=n=441/avg=1.658/p50=1.0/p90=4.0/p95=4.0/max=8.0
non_zodiac_missing=n=441/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0
missing_positive=337
non_zodiac_positive=0
```

按 residual mode：

```text
drop_ref_only_overflow_after_temp:
  files=113
  missing_drop=n=113/avg=1.761/p50=2.0/p90=4.0/p95=4.0/max=7.0
  non_zodiac_missing=n=113/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0

round_cap_overflow_after_temp:
  files=59
  missing_drop=n=59/avg=1.78/p50=1.0/p90=3.0/p95=4.0/max=8.0
  non_zodiac_missing=n=59/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0

activity_extras_only_drop_ref_gap:
  files=24
  missing_drop=n=24/avg=2.833/p50=3.0/p90=4.0/p95=4.0/max=6.0
  non_zodiac_missing=n=24/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0

within_drop_ref_after_temp:
  files=245
  missing_drop=n=245/avg=1.465/p50=1.0/p90=4.0/p95=4.0/max=5.0
  non_zodiac_missing=n=245/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0
```

解读：

- 所有 after-temp over-cap rows 的非生肖 item id 都落在 current reachable Drop universe 内。
- 唯一稳定 missing item examples 是 `1306003..1306014` 临时蓝色生肖 id；这些被扣除后仍有 172 条 drop overflow 与 59 条 round-cap overflow。
- 因此 capacity blocker 不是 item-universe 缺表或非生肖 overlay pool 混入，而是同一 Drop universe 内的 settlement count/occupancy 扩展或服务端 session-capacity 语义。

## O-v3-120：runtime/pair duplicate 不解释 over-cap，unique item 仍有残余冲突

2026-06-06 增强 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
```

整体 duplicate/unique 分布：

```text
files=441 settlement_rows=441
dup_runtime=n=441/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0
dup_pair=n=441/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0
dup_item=n=441/avg=2.814/p50=2.0/p90=6.0/p95=7.0/max=12.0
unique_non_temp=n=441/avg=37.15/p50=37.0/p90=48.0/p95=51.0/max=58.0
unique_above_drop=109
unique_above_round=21
```

按 residual mode：

```text
drop_ref_only_overflow_after_temp:
  files=113
  count_above_drop=113 count_above_round=0
  unique_above_drop=51 unique_above_round=0
  unique_non_temp=n=113/avg=43.009/p50=43.0/p90=47.0/p95=48.0/max=53.0
  dup_item=n=113/avg=3.77/p50=4.0/p90=6.0/p95=7.0/max=12.0
  dup_runtime=max=0.0 dup_pair=max=0.0

round_cap_overflow_after_temp:
  files=59
  count_above_drop=59 count_above_round=59
  unique_above_drop=58 unique_above_round=21
  unique_non_temp=n=59/avg=49.831/p50=49.0/p90=54.0/p95=57.0/max=58.0
  dup_item=n=59/avg=4.831/p50=5.0/p90=7.0/p95=8.0/max=10.0
  dup_runtime=max=0.0 dup_pair=max=0.0
```

解读：

- parser/runtime 层没有重复：所有 rows 的 duplicate runtime 和 duplicate `(runtime_id,item_id)` pair 都为 0。
- item_id 多实例化会解释部分 drop-only count overflow，但不能解释 round-cap overflow。
- 仍有 21 条 row 在 unique non-temp item_id 层面超过 round cap，因此 capacity blocker 不是单纯“同一 item 多份实例化”的统计口径问题。

## O-v3-121：BidMap round-category hint 不解释 unique item over-cap

2026-06-06 增强 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑真实 archive smoke：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 8 --format summary
```

关键结果：

```text
overall:
  files=441 settlement_rows=441
  hint_keys={'103': 441}
  unique_cats=n=441/avg=9.476/p50=10.0/p90=10.0/p95=10.0/max=10.0
  unique_hinted=n=441/avg=4.748/p50=4.0/p90=8.0/p95=9.0/max=14.0
  unique_unhinted=n=441/avg=32.401/p50=32.0/p90=42.0/p95=45.0/max=52.0

round_cap_overflow_after_temp:
  files=59
  hint_keys={'103': 59}
  unique_cats=n=59/avg=9.797/p50=10.0/p90=10.0/p95=10.0/max=10.0
  unique_hinted=n=59/avg=6.051/p50=6.0/p90=8.0/p95=10.0/max=12.0
  unique_unhinted=n=59/avg=43.780/p50=43.0/p90=48.0/p95=51.0/max=52.0

within_drop_ref_after_temp:
  files=245
  hint_keys={'103': 245}
  unique_cats=n=245/avg=9.265/p50=9.0/p90=10.0/p95=10.0/max=10.0
  unique_unhinted=n=245/avg=27.110/p50=27.0/p90=33.0/p95=34.0/max=39.0
```

解读：

- 真实 archive 中所有 rows 的 BidMap round-category hint key 都是 `103`，不能区分 over-cap 与 within-cap。
- over-cap rows 的 unique non-temp item primary-category 覆盖接近全量 10 类，且大量 item 落在 unhinted categories。
- 因此 `round_category_hints` 不是 settlement item-count cap，也不是可直接用于 v3 sampler/readiness 的 promotion evidence。

## O-v3-122：unique cap 分层后，剩余 round-cap 冲突仍是 broad inventory/cells 问题

2026-06-06 增强 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by unique_residual_mode --min-samples 1 --top 6 --format summary
```

`unique_residual_mode` 分层：

```text
activity_extras_only_drop_ref_gap=201
within_unique_caps_after_temp=68
instance_drop_ref_only_overflow_after_temp=62
unique_drop_ref_only_overflow_after_temp=51
instance_round_cap_overflow_after_temp=38
unique_round_cap_overflow_after_temp=21
```

关键 quality/cells 结果：

```text
unique_round_cap_overflow_after_temp:
  files=21
  unique_non_temp=n=21/avg=53.143/p50=52.0/p90=57.0/p95=57.0/max=57.0
  unique_non_temp_cells=n=21/avg=152.143/p50=153.0/p90=175.0/p95=176.0/max=206.0
  unique_q6_count=n=21/avg=3.429/p50=3.0/p90=5.0/p95=6.0/max=8.0
  unique_q6_cells=n=21/avg=16.857/p50=16.0/p90=31.0/p95=34.0/max=37.0
  unique_quality_counts=q4:298,q2:241,q3:234,q5:170,q1:101,q6:72

instance_round_cap_overflow_after_temp:
  files=38
  unique_round_excess_after_temp=max=0.0
  unique_drop_excess_after_temp=n=38/avg=5.158/p50=5.0/p90=9.0/p95=10.0/max=14.0
  unique_q6_count=n=38/avg=3.658/p50=4.0/p90=6.0/p95=7.0/max=10.0
  unique_q6_cells=n=38/avg=12.132/p50=11.0/p90=23.0/p95=24.0/max=40.0

within_unique_caps_after_temp:
  files=68
  unique_non_temp_cells=n=68/avg=83.559/p50=84.0/p90=110.0/p95=115.0/max=126.0
  unique_q6_count=n=68/avg=1.985/p50=2.0/p90=4.0/p95=4.0/max=6.0
  unique_q6_cells=n=68/avg=7.279/p50=6.0/p90=15.0/p95=25.0/max=39.0
```

解读：

- unique item 层面的 round-cap blocker 从 59 条 count overflow 收窄到 21 条 unique overflow，但没有消失。
- `unique_round_cap_overflow_after_temp` 的 quality 分布以 q2-q4/q5 broad inventory 为主，q6 只是其中一部分；这不是单一 q6 value-floor 问题。
- q6 cells tail 与 within-cap rows 有重叠，不能直接转成 formal value 上修或 promotion evidence。
- 后续仍应先解释 settlement count/session-capacity 或 cap 字段语义，再恢复 formal/value sampler 参数设计。

## O-v3-123：BidMap raw capacity columns 没有隐藏的 final count/cells cap

2026-06-06 新增 `summarize_v3_bidmap_raw_capacity_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_bidmap_raw_capacity_candidates.py --top 6 --format summary
python scripts\summarize_v3_bidmap_raw_capacity_candidates.py --include-non-capacity --top 4 --format summary
```

语义 capacity columns：

```text
col=11 role=rounds_total
  candidate_values=30:253,25:188
  unique_count_cover=71/441 unique_count_over=370
  unique_cells_cover=0/441

col=14 role=round_caps_candidate
  candidate_values=50:419,60:22
  unique_count_cover=420/441 unique_count_over=21
  unique_count_over_modes=unique_round_cap_overflow_after_temp:21
  unique_cells_cover=7/441 unique_cells_over=434

col=17 role=drop_ref
  candidate_values=44:253,40:188
  unique_count_cover=332/441 unique_count_over=109
  unique_cells_cover=0/441
```

非 capacity 的 count-sized columns：

```text
col=7  role=category_id          unique_count_cover=441/441 unique_cells_cover=270/441
col=9  role=sub_pool_weights     unique_count_cover=181/181 unique_cells_cover=97/181
col=13 role=entry_requirement    unique_count_cover=260/260 unique_cells_cover=168/260
col=20 role=round_category_hints unique_count_cover=441/441 unique_cells_cover=263/441
```

解读：

- `round_caps_candidate` 是目前最接近 settlement unique item count 的 BidMap raw 候选，但仍失败 21 条 unique round overflow。
- `drop_ref` 更弱，不能解释 109 条 unique count overflow。
- 语义 capacity columns 都不能解释 settlement cells；这与 prior-stressed cells/capacity blocker 保持一致。
- category id、sub-pool weight、entry requirement、round category hint 等列不能被重新解释为 cap；它们数字上较大只是 schema id/weight/hint。

## O-v3-124：unique round overflow 不来自单一 BidMap sub-pool 路由或 capture cohort

2026-06-06 增强 `summarize_v3_settlement_count_prior_candidates.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by bidmap_sub_pool_kind --min-samples 1 --top 6 --format summary
```

Sub-pool 分层：

```text
leaf:
  files=260
  unique_residual_modes={activity_extras_only_drop_ref_gap:117, within_unique_caps_after_temp:42, instance_drop_ref_only_overflow_after_temp:41, unique_drop_ref_only_overflow_after_temp:24, instance_round_cap_overflow_after_temp:22, unique_round_cap_overflow_after_temp:14}
  unique_above_round=14 unique_above_drop=59

weighted_parent:
  files=159
  unique_residual_modes={activity_extras_only_drop_ref_gap:73, within_unique_caps_after_temp:26, unique_drop_ref_only_overflow_after_temp:21, instance_drop_ref_only_overflow_after_temp:17, instance_round_cap_overflow_after_temp:15, unique_round_cap_overflow_after_temp:7}
  unique_above_round=7 unique_above_drop=43

self_only:
  files=22
  unique_residual_modes={activity_extras_only_drop_ref_gap:11, unique_drop_ref_only_overflow_after_temp:6, instance_drop_ref_only_overflow_after_temp:4, instance_round_cap_overflow_after_temp:1}
  unique_above_round=0 unique_above_drop=7
```

补充 cohort 分布：

```text
map_family:
  shipwreck unique_round=19 unique_drop=64
  villa     unique_round=2  unique_drop=38
  hidden    unique_round=0  unique_drop=7

capture_rounds:
  4 unique_round=9
  5 unique_round=8
  2 unique_round=1
  1 unique_round=3
```

解读：

- unique round overflow 同时存在于 leaf 与 weighted parent maps；不是单一“未知母图 sub-pool 路由 cap 使用错误”。
- self-only 2601 没有 unique round overflow，但仍有 unique drop overflow，说明 2601 不能解释 default shipwreck/villa 的 unique round blocker。
- unique round overflow 主要集中在 shipwreck family，但横跨多个 capture rounds/round_index；后续应继续查 map-family/session-capacity 或 server-side settlement expansion。

## O-v3-125：source semantics 审计把 21 条 unique round over-cap 收口到 settlement expansion / session-capacity

2026-06-06 新增 `summarize_v3_settlement_source_semantics_audit.py` 后，复跑：

```powershell
python scripts\summarize_v3_settlement_source_semantics_audit.py --group-by unique_residual_mode --top 8 --format summary
python scripts\summarize_v3_settlement_source_semantics_audit.py --group-by mechanism_class --top 8 --format summary
python scripts\summarize_v3_settlement_source_semantics_audit.py --group-by source_evidence_class --top 8 --format summary
```

全量 441 rows：

```text
table_raw_version=300 tables_version=300
activity_present=False activity_listed=True
overlay_status=v300_activity_listed_missing_locally
evidence=settlement_payload_verified_only:395,public_total_matches_inventory:27,direct_action_matches_inventory:17,source_ambiguous:2
mechanisms=not_unique_round_cap_blocker:420,session_capacity_source_semantics:18,server_side_settlement_expansion:3
non_zodiac_missing=max 0
inventory_state_delta=max 0
```

21 条 `unique_round_cap_overflow_after_temp`：

```text
files=21
maps=2501:7,2503:3,2504:2,2506:2,2508:2,2510:2,2408:1,2410:1
families=shipwreck:19,villa:2
capture_days=20260601:8,20260531:6,20260530:3,20260604:2,20260529:1,20260605:1
session_p6=129501:17,127412:4
evidence=settlement_payload_verified_only:18,direct_action_matches_inventory:2,public_total_matches_inventory:1
mechanisms=session_capacity_source_semantics:18,server_side_settlement_expansion:3
unique_non_temp=max 57
round_cap=max 50
non_zodiac_missing=max 0
payload_mismatch=0/21
raw_candidate_delta=max 0
occupied_delta=max 0
inventory_state_delta=max 0
public_match_rows=1/21
full_action_rows=2/21
```

解读：

- 21 条 unique non-temp over round-cap 不是 payload parser/slot 误计，也不是 duplicate runtime/item pair 导致；0x002D latest inventory 与 payload raw/occupied slot 一致。
- 这些 rows 的 item id 均在 current reachable Drop universe 内，外部 overlay 若存在，当前证据只支持它影响件数/活动机制，而不是引入未知非生肖 item pool。
- `server_side_settlement_expansion` 有 3 条外部确认；18 条只能判为 `session_capacity_source_semantics`，仍需要 source parser/table acquisition 才能进一步拆开。
- per-session table version 仍是弱假设：over-cap 横跨多个 day/session/map，且本地 raw/table version 均为 300；当前旧 CDN URL 无法验证远端 current table。
- 下一阶段不应直接恢复 formal/value sampler 参数调优；优先做 source parser、远端/活动表获取，或追加样本确认 payload-only rows 的生成机制。

## O-v3-126：capacity/source expansion shadow holdout 覆盖 21 条 blocker，但只能作为 broad watch

2026-06-06 新增 `capacity_source_expansion.py`、`build_v3_capacity_source_expansion_shadow.py` 与 `summarize_v3_capacity_source_expansion_holdout.py` 后，复跑：

```powershell
python scripts\build_v3_capacity_source_expansion_shadow.py
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_family --top 8 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id --top 8 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py data\samples\fatbeans_activity_20260605_shipwreck --group-by map_family --top 8 --min-train-sessions 2 --format summary
python scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
python scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary
```

artifact：

```text
output=data/processed/v3_capacity_source_expansion_shadow.json
entries=30
cohorts=4
group_bys=map_id,map_family
affects_bid=False
active=False
```

default archive，`group_by=map_family`：

```text
sessions=441
truth_unique_round_rows=21
truth_source_semantics_rows=21
candidate_rows=419
covered_unique_round_rows=21
missed_unique_round_rows=0
false_positive_candidate_rows=398
sample_limited_rows=0
payload_mismatch_rows=2
truth_payload_mismatch_rows=0
non_zodiac_missing_rows=0
truth_non_zodiac_missing_rows=0
unique_round_recall=1.0
source_semantics_recall=1.0
candidate_precision=0.050119
status_counts=watch_capacity_source_expansion_holdout:2,within_capacity_source_semantics_shadow_only:1
```

default archive，`group_by=map_id`：

```text
sessions=441
truth_unique_round_rows=21
truth_source_semantics_rows=21
candidate_rows=202
covered_unique_round_rows=18
missed_unique_round_rows=3
false_positive_candidate_rows=184
sample_limited_rows=0
truth_payload_mismatch_rows=0
truth_non_zodiac_missing_rows=0
unique_round_recall=0.857143
source_semantics_recall=0.857143
candidate_precision=0.089109
status_counts=blocked_holdout_under_recall:3,watch_capacity_source_expansion_holdout:6,within_capacity_source_semantics_shadow_only:12
```

activity 20260605 shipwreck：

```text
sessions=15
truth_unique_round_rows=0
truth_source_semantics_rows=0
candidate_rows=0
non_zodiac_missing_rows=15
truth_non_zodiac_missing_rows=0
status_counts=within_capacity_source_semantics_shadow_only:1
```

archive evaluator / readiness：

```text
v3_cse_ready_rows=1560
v3_cse_candidate_rows=752
v3_cse_active_rows=0

gate=capacity_source_expansion_shadow status=watch
overall_status=not_ready
```

解读：

- 21 条 unique non-temp over round-cap 的主因已经可复核解释为 final settlement/source semantics：`server_side_settlement_expansion` 3 条，`session_capacity_source_semantics` 18 条。
- `map_family` 口径能覆盖全部 blocker，但把 398 个非 blocker windows 一起标成 candidate；它只适合 broad watch，不适合 sampler/promotion。
- `map_id` 口径减少 broadness，但漏掉 3 条 blocker；说明仅靠现有 archive map_id prior 还不足以恢复 formal/value sampler。
- activity cohort 的 non-zodiac missing 是 overlay/source-parser 线索，但不是 default 21 条 unique round-cap blocker 的 item-universe 解释。
- `v3_cse_*` 已进入 archive/live/model_eval 的 shadow 字段，且 `active_rows=0`；v2 formal/live/UI 与正式出价保持不变。

## O-v3-127：source-aware CSE signature matrix 暂未找到可同时提升 recall/precision 的 prior

2026-06-07 增强 `summarize_v3_capacity_source_expansion_holdout.py` 后，复跑：

```powershell
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id --fallback-group-by map_family_sub_pool_kind --top 8 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id_capture_rounds --top 6 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id_last_round_flag --top 6 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_family_outer_shape --top 6 --min-train-sessions 4 --format summary
```

map-id baseline 漏召回：

```text
map_id=2408
  file=fatbeans_valid_aisha_2408_5rounds_2408_1274128129457532_0081.json
  fold=1 train_sessions=7 train_source_semantics_rows=0

map_id=2410
  file=fatbeans_valid_ethan_2410_1rounds_2410_1295019008815241_0283.json
  fold=0 train_sessions=16 train_source_semantics_rows=0

map_id=2509
  file=fatbeans_valid_ethan_2509_5rounds_2509_1295018712615152_0360.json
  fold=2 train_sessions=8 train_source_semantics_rows=0
```

signature matrix：

```text
map_id:
  covered=18/21 missed=3 candidate=202 fp=184
  recall=0.857143 precision=0.089109

map_id -> map_family_sub_pool_kind:
  covered=21/21 missed=0 candidate=347 fp=326
  candidate_sources=primary:202,fallback:145
  recall=1.0 precision=0.060519

map_id_capture_rounds:
  covered=11/21 missed=10 candidate=85 fp=74 sample_limited=179
  recall=0.52381 precision=0.129412

map_id_last_round_flag:
  covered=17/21 missed=4 candidate=178 fp=161 sample_limited=21
  recall=0.809524 precision=0.095506

map_family_outer_shape:
  covered=19/21 missed=2 candidate=257 fp=238 sample_limited=12
  recall=0.904762 precision=0.07393
```

payload/source parser review：

```text
18 payload-only rows by map:
  2408:1, 2410:1, 2501:6, 2503:2, 2504:2, 2506:1, 2508:2, 2509:1, 2510:2

source_evidence_class overlap:
  TP payload-only dominates, but FP rows are also mostly settlement_payload_verified_only.

payload/source field risk:
  payload_field_shape, settlement_outer_field_shape, action count and message counts
  all overlap with within-cap rows; exact payload_field20_values/session/item ids are high-cardinality
  or leakage-prone and should not be prior keys.
```

解读：

- map-id miss 不是 table/source parser 错，而是 holdout support gap：singleton truth row 在 test fold 中，train folds 没有同 map source support。
- fallback 能补 recall，但会显著降低 precision；因此它是 useful audit counterfactual，不是 default prior。
- 更窄的 source signatures 会遇到 sample-limited 与 recall collapse；当前没有 non-leaky signature 同时优于 map-id baseline。
- 下一步要真正收窄 CSE prior，需要新增 source parser/table acquisition 或更多样本，而不是在现有 fields 上继续组合过拟合。

## O-v3-128：252x activity cohort 可作为调参参考，但仍是 missing-drop/source-overlay lane

2026-06-07 复核 252x activity 样本、mapping likelihood、v303 表侧状态、CSE holdout 与 prior robustness。

manifest：

```powershell
python scripts\summarize_fatbeans_sample_manifest.py data\samples\fatbeans_activity_20260605_shipwreck
```

```text
files=15 parsed_files=15 parse_errors=0 valid_files=15 mixed_files=0 invalid_files=0 usable_metric_files=15 bid_windows=58 ready_windows=58 no_state_windows=0 constraint_conflict_windows=0
captured_maps=2521:5,2522:1,2524:3,2526:2,2528:1,2529:3
manifest_role=activity_tuning_reference
metric_scope=source_parser_table_acquisition_and_shadow_tuning_reference_only
affects_bid=false
```

activity mapping likelihood：

```powershell
python scripts\summarize_v3_activity_mapping_likelihood.py
```

```text
files=15 schemes=minus10,minus20 winners=minus10:11,minus20:4 item_winners=minus10:11,minus20:4 candidate_statuses=ok:30 errors=0
scheme=minus10 ll_per_item_avg=-1.676415 item_ll_per_item_avg=-5.965943 missing_item_rate_avg=0.0
scheme=minus20 ll_per_item_avg=-1.691183 item_ll_per_item_avg=-5.981787 missing_item_rate_avg=0.0
```

v303 table timing：

```powershell
python scripts\summarize_v3_archive_table_timing.py data\samples\fatbeans_activity_20260605_shipwreck --raw-root C:\xiangmuyunxing\steamapps\common\BidKing\BidKing_Data\StreamingAssets --format summary
```

```text
raw_file_version=303
bidmap_rows=165
activity_range=2521-2530 bidmap_present=10 bidmap_missing=0 drop_present=0 drop_missing=10 drop_ref_pairs=22-44:10
activity_range=4521-4530 bidmap_present=10 bidmap_missing=0 drop_present=0 drop_missing=10 drop_ref_pairs=22-44:10
sample_files=15 capture_min=2026-06-05T23:05:05.4056732+08:00 capture_max=2026-06-05T23:56:58.9596734+08:00
```

CSE holdout / prior robustness：

```powershell
python scripts\summarize_v3_capacity_source_expansion_holdout.py data\samples\fatbeans_activity_20260605_shipwreck --group-by map_id --top 10 --min-train-sessions 1 --format summary
python scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --format summary
```

```text
CSE activity holdout:
  sessions=15 groups=6 truth_unique_round_rows=0 truth_source_semantics_rows=0 candidate_rows=0
  non_zodiac_missing_rows=15 truth_non_zodiac_missing_rows=0
  status_counts=within_capacity_source_semantics_shadow_only:6

prior robustness:
  v3_robust_status=prior_unavailable
  ready=58 post_ready=0 metric=0 trusted=0/58 activity=58 stressed=0 avg_stress=0.0
  reasons=activity_map_id_candidate:58,prior_error=KeyError:58
```

解读：

- 252x 当前样本能作为调参参考，是因为 capture/window/truth 完整、且 v303 表侧确认 `2521-2530` BidMap 存在；它能帮助设计 source parser、activity overlay 与后续 shadow-only sampler 分片。
- 252x 当前不能作为 promotion evidence，是因为 Drop/source overlay 仍缺，prior robustness 明确为 prior unavailable，metric rows 为 0。
- `252x->251x` likelihood 略优但不是强映射证据；missing item rate 为 0 只说明两个候选旧表族都能覆盖 observed item universe。
- 当前项目内未找到“16 个 252x capture/map”的可复核来源；本轮记录使用 15 capture / 6 captured map ids / 10 v303 table-side map ids 的口径。

## O-v3-129：CSE source-context 拆分后，payload-only 是主要剩余解释缺口

2026-06-07 对 settlement source semantics、CSE holdout、archive evaluator 与 readiness 重新验证。

source-context audit：

```powershell
python scripts\summarize_v3_settlement_source_semantics_audit.py --group-by source_context_class --top 8 --format summary
```

```text
files=441 settlement_rows=441 groups=6
context=payload_verified_partial_action_only:339,payload_verified_empty_action_results:55,public_total_confirmed:27,direct_action_full_confirmed:17,payload_unverified_or_mismatch:2,payload_verified_no_external_source:1
mechanisms=not_unique_round_cap_blocker:420,session_capacity_source_semantics:18,server_side_settlement_expansion:3
unique_round_rows=21/441 payload_mismatch=2/441 non_zodiac_missing_max=0

payload_verified_partial_action_only:
  files=339 unique_round_rows=15
  action_max avg=4.442 p95=11 max=25
  action_gap avg=36.31 max=62
  action_ratio avg=0.113 max=0.417

payload_verified_empty_action_results:
  files=55 unique_round_rows=3
  action_max=0 action_ratio=0

direct_action_full_confirmed:
  files=17 unique_round_rows=2 action_gap=0 action_ratio=1.0

public_total_confirmed:
  files=27 unique_round_rows=1 public_delta=0
```

map-id holdout：

```powershell
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id --top 12 --min-train-sessions 4 --format summary
```

```text
truth_unique_round_rows=21 candidate_rows=202 covered_unique_round_rows=18 missed_unique_round_rows=3 false_positive_candidate_rows=184
unique_round_recall=0.857143 source_semantics_recall=0.857143 candidate_precision=0.089109
truth_source_context_classes=payload_verified_partial_action_only:15,payload_verified_empty_action_results:3,direct_action_full_confirmed:2,public_total_confirmed:1

missed_example file=fatbeans_valid_ethan_2509_5rounds_2509_1295018712615152_0360.json map_id=2509 fold=2 train_source=0 context=payload_verified_empty_action_results mechanism=session_capacity_source_semantics excess=7.0
missed_example file=fatbeans_valid_ethan_2410_1rounds_2410_1295019008815241_0283.json map_id=2410 fold=0 train_source=0 context=payload_verified_empty_action_results mechanism=session_capacity_source_semantics excess=3.0
missed_example file=fatbeans_valid_aisha_2408_5rounds_2408_1274128129457532_0081.json map_id=2408 fold=1 train_source=0 context=payload_verified_partial_action_only mechanism=session_capacity_source_semantics excess=2.0
```

map-family / fallback counterfactual：

```powershell
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_family --top 12 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id --fallback-group-by map_family_sub_pool_kind --top 12 --min-train-sessions 4 --format summary
```

```text
map_family:
  covered=21/21 missed=0 candidate=419 fp=398
  recall=1.0 precision=0.050119

map_id -> map_family_sub_pool_kind:
  covered=21/21 missed=0 candidate=347 fp=326
  candidate_sources=primary:202,fallback:145
  recall=1.0 precision=0.060519
```

archive/readiness smoke：

```powershell
python scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
python scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary
```

```text
archive:
  windows=1577 ready=1560
  v3_cse_ready_rows=1560
  v3_cse_candidate_rows=752
  v3_cse_active_rows=0

readiness:
  overall_status=not_ready
  capacity_source_expansion_shadow status=watch
  cse_candidate_rows=752
  cse_active_rows=0
```

解读：

- `source_context_class` 让 payload-only rows 的缺口更清晰：truth rows 中 18/21 仍不是 full external source confirmation，其中 3 条甚至是 action result 存在但 observed item count 为 0。
- 3 条 map-id miss 不是解析/slot/drop-universe 错误，而是训练折没有同 map source support；这属于 support-depth 问题。
- map-family/fallback 能补召回但扩大 false positives，仍是 broad watch prior；默认 CSE prior 不能因 recall=1.0 自动切换。
- processed artifact 已重建为 `generated_at=2026-06-07`、`entries=30`、`affects_bid=false`、`active=false`，map_id=2501 的 `source_context_classes` 可复核为 `direct_action_full_confirmed:2,payload_unverified_or_mismatch:1,payload_verified_empty_action_results:16,payload_verified_partial_action_only:65,public_total_confirmed:3`。

## O-v3-130：prebid pressure guard 提高 CSE 精度但召回不足

2026-06-07 新增 `summarize_v3_capacity_source_expansion_prebid_guard.py`，将 archive prebid evaluator rows 与 settlement source-semantics truth 按 capture file 合并，只评估 prebid 可见的 CSE guard。

验证命令：

```powershell
python scripts\summarize_v3_capacity_source_expansion_prebid_guard.py --posterior-trials 64 --format summary
python scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
python scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary
```

guard 结果：

```text
files=441 ready_rows=1560 truth_rows=81 truth_sessions=21 parse_errors=0

cse_candidate:
  selected_rows=752 covered_rows=81 missed_rows=0 fp_rows=671
  row_recall=1.0 row_precision=0.107713
  selected_sessions=214 covered_sessions=21 missed_sessions=0 fp_sessions=193
  session_recall=1.0 session_precision=0.098131

pressure_candidate:
  selected_rows=61 covered_rows=24 missed_rows=57 fp_rows=37
  row_recall=0.296296 row_precision=0.393443
  selected_sessions=31 covered_sessions=11 missed_sessions=10 fp_sessions=20
  session_recall=0.52381 session_precision=0.354839
  rounds=1:7,2:7,3:9,4:21,5:17
  target_sources=exact:36,floor:25

target_near_source_p95_5:
  selected_rows=56 covered_rows=23 missed_rows=58 fp_rows=33
  row_recall=0.283951 row_precision=0.410714
  selected_sessions=28 covered_sessions=11 missed_sessions=10 fp_sessions=17
  session_recall=0.52381 session_precision=0.392857
```

archive/readiness：

```text
archive:
  v3_cse_candidate_rows=752
  v3_cse_pressure_candidate_rows=61
  v3_cse_active_rows=0

readiness:
  overall_status=not_ready
  capacity_source_expansion_shadow status=watch
  cse_candidate_rows=752
  cse_pressure_candidate_rows=61
  cse_active_rows=0
```

解读：

- pressure guard 使用 prebid target/prior max gap，不依赖 final settlement unique count 或 `source_context_class`，因此可进入 live `model_eval` 作为实战复盘字段。
- precision 提升明显，但 session recall 只有 11/21；剩余 10 个 truth sessions 没有在 prebid 窗口触发 target-above-prior pressure。
- 当前最合适的策略是保留 broad `v3_cse_candidate` 做 full-recall watch，同时用 `v3_cse_pressure_candidate` 做 high-precision 子分片；两者都不能接入 formal/live 出价。

## O-v3-131：payload-only CSE truth 的剩余缺口集中在 empty-action 与 no-train-support

2026-06-07 新增 payload-only 专项审计。

验证命令：

```powershell
python scripts\summarize_v3_capacity_source_expansion_payload_only_audit.py --posterior-trials 64 --top 8 --format summary
```

总体：

```text
settlement_rows=441 truth_rows=21 payload_truth_rows=18 external_truth_rows=3
payload_contexts=payload_verified_partial_action_only:15,payload_verified_empty_action_results:3
payload_map_id_missed_rows=3
payload_prebid_candidate_rows=18
payload_prebid_pressure_rows=8
parse_errors=0
```

按 context：

```text
payload_verified_empty_action_results:
  rows=3 maps=2410:1,2501:1,2509:1
  missed=2 prebid_candidate=3 prebid_pressure=1
  action_max=n=3/avg=0/max=0
  action_gap=n=3/avg=60/max=66
  excess=n=3/avg=3.667/max=7

payload_verified_partial_action_only:
  rows=15 maps=2501:5,2503:2,2504:2,2508:2,2510:2,2408:1,2506:1
  missed=1 prebid_candidate=15 prebid_pressure=7
  action_max=n=15/avg=5.867/max=25
  action_gap=n=15/avg=53.467/max=62
  action_ratio=n=15/avg=0.098/max=0.417
  excess=n=15/avg=3.2/max=7
```

map-id miss examples：

```text
2509 empty-action:
  file=fatbeans_valid_ethan_2509_5rounds_2509_1295018712615152_0360.json
  covered=False train_source=0 pressure=1 action_max=0 action_gap=66 excess=7

2410 empty-action:
  file=fatbeans_valid_ethan_2410_1rounds_2410_1295019008815241_0283.json
  covered=False train_source=0 pressure=0 action_max=0 action_gap=57 excess=3

2408 partial-action:
  file=fatbeans_valid_aisha_2408_5rounds_2408_1274128129457532_0081.json
  covered=False train_source=0 pressure=2 action_max=4 action_gap=52 excess=2
```

解读：

- payload-only 不再是单一 blocker：empty-action 更像 source parser/action-result decode 问题，partial-action 更像 session-capacity source semantics 的弱外部线索。
- 3 条 exact map-id miss 全部是 `train_source=0` 的 support-depth 问题；pressure 能覆盖 2509/2408，但覆盖不了 2410。
- 下一步要优先拆 action-result payload / source parser，而不是在现有 fields 上继续组合 fallback。

## O-v3-132：payload-only action shape 显示 empty-action 是 numeric-only，不是 item payload 缺解

2026-06-07 对 payload-only CSE truth rows 增加 action-result payload shape 审计。

验证命令：

```powershell
python scripts\summarize_v3_capacity_source_expansion_payload_only_audit.py --posterior-trials 64 --top 8 --format summary
```

总体：

```text
payload_truth_rows=18
payload_source_shapes=item_reveal_payload:15,numeric_only_result:3
parse_errors=0
source_shape_parse_errors=0
```

empty-action：

```text
payload_verified_empty_action_results:
  rows=3 maps=2410:1,2501:1,2509:1
  missed=2 prebid_candidate=3 prebid_pressure=1
  source_shapes=numeric_only_result:3
  source_action_ids=100105:13,100104:9,100124:6,100107:3
  source_result_fields=14:25,12:6
  source_item_payload_block_max=0
  source_observed_item_max=0
```

partial-action：

```text
payload_verified_partial_action_only:
  rows=15 maps=2501:5,2503:2,2504:2,2508:2,2510:2,2408:1,2506:1
  missed=1 prebid_candidate=15 prebid_pressure=7
  source_shapes=item_reveal_payload:15
  source_item_payload_block_max avg=5.867 max=25
  source_observed_item_max avg=5.867 max=25
```

复核样本：

```text
2509 empty-action miss:
  source_shape=numeric_only_result
  source_action_ids=100105:6,100104:5,100124:4,100107:3
  source_item_payload_block_max=0
  source_observed_item_max=0

2410 empty-action miss:
  source_shape=numeric_only_result
  source_action_ids=100105:2
  source_item_payload_block_max=0
  source_observed_item_max=0

2408 partial-action miss:
  source_shape=item_reveal_payload
  source_action_ids=100136:6,100129:5,100128:4,100107:3
  source_item_payload_block_max=4
  source_observed_item_max=4
```

解读：

- empty-action rows 的 raw action payload 没有 item list，因此不是当前 Fatbeans item parser 漏掉 field 8。
- 这些 rows 的核心冲突是 numeric action source 与 settlement inventory/drop-cap 的语义关系，仍需 table/support-depth、server expansion 或 per-session overlay 解释。
- partial-action rows 的 item parser 路径可工作，但最多只解释部分 inventory；不能作为 full source confirmation。
