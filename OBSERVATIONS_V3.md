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
