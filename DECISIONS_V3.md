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

## D-v3-012：archive 样本治理先用 manifest，不直接移动原始样本

Fatbeans archive 默认保留 `data/samples/fatbeans` 原始文件位置，v3 通过 manifest 标记数据质量：

- `valid`：所有报价前窗口均 ready，可整体用于指标。
- `mixed`：同一文件内既有 ready 窗口，也有 no-state/冲突窗口；只使用 ready 窗口。
- `invalid`：parse error、无可用 pre-bid 窗口或仅有不可评估窗口；不进入模型准确率。

原因：

- 样本文件目前是 live/archive/debug 多路径共同使用的本地资料，直接移动会制造路径断裂风险。
- 文件数和窗口数必须长期分开报告，避免把 posterior fallback 或 pre-bid window 当作新增真实样本。
- parse error 和 no-state 是数据质量或采集缺口，不是估值模型误差。
- manifest 可作为后续迁移/归档依据；只有当脚本全部支持 manifest include/exclude 后，才考虑物理 quarantine。

## D-v3-013：manual inbox 是 staging，不自动改变默认 baseline

`data/samples/fatbeans_manual_inbox` 用于接收手动导出的新样本。该目录下 JSON 默认不进 git，也不自动改变
`data/samples/fatbeans` 默认 baseline。

使用规则：

- 新样本先在 inbox 内重命名、manifest 审查和去重。
- 需要比较新旧口径时，显式把 inbox 作为第二个路径传给 evaluator。
- 只有完成分布审查并明确要升级 baseline 时，才把样本迁入主样本库或调整 evaluator 默认路径。

原因：手动采样批次可能偏向某些英雄/地图/轮次；先 staging 可以避免 baseline 悄悄漂移，也方便回溯新样本对指标的影响。

## D-v3-014：v3 默认样本库改为 canonical real archive

2026-06-05 起，v3 默认 archive baseline 使用整理后的 `data/samples/fatbeans`：

- 主样本库保留为脚本默认路径，不改 evaluator 默认参数。
- 可解析 `valid` 与 `mixed` 真实样本都放在主样本库，用 canonical 文件名标识 `sample_class/hero/map/round/session`。
- 旧 parse error 样本移到 `data/samples/fatbeans_invalid/parse_error`，不再进入默认 evaluator。
- 新手动样本仍先进入 `data/samples/fatbeans_manual_inbox`，审查后再用 organizer 并入主库。
- live raw archive 保留原日志；只复制未重复 complete 局进主样本库。

原因：

- 默认 baseline 应该 parse-clean，避免每次评估都混入已知坏包。
- 文件名应能直接识别 hero/map/round/session，降低后续定位 top miss 的成本。
- 保留默认路径可减少脚本/UI/live/archive 引用断裂风险。

## D-v3-015：summary-likelihood fallback 可作为 v3 shadow，不作为 formal promotion

2026-06-05 起，strict 无命中时的 v3 posterior fallback 从 `q6_projection` 升级为
`summary_likelihood`：

- 输入只来自 `FeasibleSummaryReport`。
- session total count/cells exact、known floors、各品质 count/cells/value exact/floor 都参与 likelihood。
- likelihood 权重必须 temperature 展平，避免少数近邻样本压掉全部长尾。
- P50 可使用 support guard 适度降低低估；P90 必须使用 tail guard 保留长尾覆盖。
- `q6_projection` 只保留为极端 no-weight fallback，目前 canonical 样本中计数为 `0`。

边界：

- `summary_likelihood` 仍然是 shadow posterior，`affects_bid=false`。
- 它可以作为 v3 诊断和 live shadow 展示候选，但不能直接替代正式 v2 decision_value。
- promotion 前必须继续拆分 hero/map/round/scope 指标，并解释 2601、2506、2501 等高 MAE 地图的低估来源。

原因：

- 直接 q6 projection 会丢掉大量公开总格、总件数、分品质 exact/floor 证据。
- 直接尖锐 likelihood 又会把 P90 长尾压掉，复现实战低估。
- 当前带 guard 的 summary-likelihood 在 433 canonical 样本上降低 formal P50 MAE，并保持 P90 coverage 小幅高于旧基线，但低估 bias 仍未解决。

## D-v3-016：posterior 输出必须投影 hard summary bounds

v3 posterior 的 quantile 输出层必须守住 `FeasibleSummaryReport` 中已经确定的 hard bounds：

- raw session/bucket 字段：
  - exact 优先。
  - 没有 exact 时使用 floor。
- formal/tail-replacement decision 字段：
  - 使用 item-anchor 汇总出的 `known_value_floor` / bucket `value_floor` 作为下界。
  - 不把公开 aggregate `value_exact` 直接当作 formal plannable value。

原因：

- sampler 是有限 prior/proposal bank，不能保证抽到每一个已知高值 item。
- 已知 item-anchor value 是实战可用证据，posterior 输出低于它会直接制造低估。
- aggregate exact value 只说明 raw bucket total，不一定证明每个高尾 item 都是 formal plannable；因此它只约束 raw value 字段。

边界：

- 这是输出一致性 guard，不是正式出价升级。
- 仍保持 `affects_bid=false`。
- 后续如果 formal plannable 规则调整，必须同步更新 `decision_truth_from_*` 与 posterior guard，不能只改 evaluator。

## D-v3-017：v3 posterior sampler 必须消费 anchor 证据

后续 v3 posterior/proposal 的证据层级调整为：

1. `EvidenceEvent`
2. `ConstraintSet`
3. `FeasibleSummaryReport`
4. anchor-aware likelihood / proposal
5. posterior quantile + hard-bound guard

`FeasibleSummaryReport` 仍是 hard numeric summary，但不能作为 sampler 的唯一输入。原因：

- summary 会丢掉 item_id、category、shape_key、runtime/local anchor 等信息。
- formal decision value 是否裁尾依赖 exact/category support。
- 只按 quality count/cell/value summary 过滤，会让被道具支持的高值红品在 posterior 中被低估。

当前实现：

- strict matched samples 也按 anchor likelihood 加权。
- summary-likelihood fallback 把 anchor log-likelihood 叠加到 summary log-likelihood。
- item anchor 与 shape anchor 匹配只影响 shadow posterior 权重，不生成新的 hard footprint。

边界：

- quality-only/宝光无轮廓点仍只作软线索；不因 anchor likelihood 生成 hard footprint。
- anchor-aware posterior 仍为 shadow，`affects_bid=false`。
- promotion 前必须继续用 map/round/scope slice 验证，尤其关注 2507 回退和 2601/2506 残余低估。

## D-v3-018：v3 shadow P50 使用 practical support P60 guard

2026-06-05 起，v3 likelihood-weighted posterior 的 P50 support guard 使用 support P60：

- 只在已有 likelihood weights 的窗口生效。
- P90 tail guard 仍使用 support P90。
- 这是 v3 shadow 的实战参考口径，不改变 v2 formal 出价。

原因：

- 真实样本与实战反馈都显示 P50 低估长期偏多。
- support P50 guard 仍对 2601/2506 等厚尾地图过保守。
- support P60 在 433 canonical 样本上降低 formal/q6 MAE，并把 q6 below/over 拉近均衡。

边界：

- 不继续全局提高到 P65/P70；2507、2508、2505 已出现正 bias 或 over-rate 升高。
- 后续更激进只能做 map/证据条件化 proposal。
- evaluator 与 slice 报表必须同时报告 below-rate 与 over-rate。
- 仍保持 `affects_bid=false`，不得直接接入正式出价。

## D-v3-019：practical P50 guard 采用地图分层校准

v3 shadow practical P50 guard 从全局 P60 改为地图分层：

- high-tail：P65，当前 `2404/2501/2503/2506/2601`。
- low-tail：P55，当前 `2407/2410/2505/2507/2508`。
- default：P60。

边界：

- 该分层只作用于 likelihood-weighted posterior。
- diagnostics 必须记录实际使用的 `practical_p50_guard_quantile`。
- 这是基于当前 canonical 样本的 shadow calibration，不作为 formal promotion 依据。
- 新增样本后必须复跑 map/round/scope slices；如果 low-tail/high-tail 分组不稳定，应退回 default 或改为显式校准文件。
- 后续更高收益方向仍是 q6 count/cell/value 条件 proposal，不是继续扩大地图表。

原因：

- 全局 P60 降低低估，但对部分地图带来正 bias。
- 地图分层在当前样本上同时降低 formal/q6 MAE，并缓解低尾地图的过激。

## D-v3-020：live v3 posterior 先进入 artifact/model_eval，不进入正式 UI contract

v3 posterior shadow 在 live monitor 中的接入边界：

- 写入完整 artifact：`v3_posterior_shadow`。
- 写入评估日志：`model_eval.v3_post_*` / `model_eval.v3_summary_*`。
- `v3_post_affects_bid=False` 必须固定输出。
- 暂不加入 `ui_contract.shadows`，不参与第一屏 UI 推荐、停止价、抢仓价或 baseline posterior 文案。

原因：

- 当前 v3 仍处于 shadow calibration 阶段，尚未达到 formal promotion gate。
- 用户已要求 UI 设计暂时冻结；把 v3 放进 UI contract 容易造成实战读数混淆。
- `model_eval.jsonl` 已足够支撑后续实战样本的 v2/v3 paired compare。

边界：

- live artifact 构建失败时 v3 shadow 应 fail closed：记录 `error`，保持 `affects_bid=false`，不影响 v2 live baseline。
- 后续若要展示 v3，只能作为明确标注的只读诊断/影子参考，且仍不得影响正式 bid rows。
- promotion 前必须用 canonical archive + 新实战样本同时验证 formal MAE、below/over、P90 coverage、q6 under-by 与 pinball。

## D-v3-021：q6 bucket-conditioned proposal 不把 count/cells 证据直接升级为 value 证据

v3 `summary_likelihood` fallback 的 q6 条件化规则：

- q6 bucket 有 count/cell/value 约束时，可以用只满足 q6 bucket 的候选集修正 q6 count/cells 分布。
- 只有 q6 bucket 存在 `value_floor` 或 `value_exact` 时，才允许修正 q6 value、q6 formal decision value、formal/raw total value 的 q6 分量。
- 只有 count/cells 证据时，不移动 q6 value/formal 分量。

原因：

- q6 count/cells floor 说明红品数量/占格下界，但不证明红品价值水平。
- 在实测样本中，count+cells floor 但无 value floor 的窗口如果直接替换 q6 value，会产生偏高 q6 bias。
- 带 value floor 的窗口才是这类 proposal 的主要收益来源，能降低 fallback 负 bias。

边界：

- 该 proposal 仍为 v3 shadow，`affects_bid=false`。
- 该实现不生成新 hard footprint，也不改变 quality-only/宝光边界。
- diagnostics 必须记录 q6-conditioned 样本量，后续 map/evidence gate 需要依赖这个字段。
- 2601 与 high-over maps 后续需要单独 gate/校准；不能用这个结果证明 v3 已可 promotion。

## D-v3-022：hidden 作为 cold-start family，不参与当前 q6-conditioned 主校准

当前 v3 shadow 中，`2601` hidden map 禁用 q6 bucket-conditioned proposal：

- 仍允许 summary likelihood、anchor likelihood、hard-bound guard。
- 不使用 q6 bucket-conditioned subset 替换 hidden 的 q6 count/cells/value/formal 分量。
- diagnostics 记录 `q6_bucket_conditioned=disabled_hidden_cold_start`。

原因：

- hidden 当前只有 `86` 个 ready 窗口，样本量远少于 shipwreck/villa。
- q6-conditioned proposal 在 hidden 上造成 MAE 回退，但在 shipwreck/villa 上仍有整体收益。
- hidden 的 truth P50/P90 明显更高，不能和 shipwreck/villa 混成一个全局红货权重。

边界：

- hidden 后续只做独立 shadow/cold-start 观察；有更多样本后再单独校准。
- 当前 v3 主校准以 shipwreck/villa 为主，尤其 `2506/2501` 的低估。
- `map_family` 是后续 v3 指标的正式分片字段，archive evaluator 必须输出。
