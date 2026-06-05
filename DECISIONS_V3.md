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

## D-v3-023：formal decision guard 与 q6 diagnostic guard 分离

v3 shadow 的 practical P50 guard 拆成两层：

- q6/count/cell/value diagnostic 继续使用地图分层 guard：
  - high-tail：P65。
  - low-tail：P55。
  - default：P60。
- formal/total/tail-replacement decision value 可使用更高的 map-specific decision guard：
  - `2501`：P75。
  - `2506`：P75。
  - `2601`：P85。

原因：

- `2501/2506/2601` 在 map audit 中表现为稳定系统性低估，且不是少数极端窗口拉高 MAE。
- 直接提高共同 guard 会污染 q6 standalone 指标；formal-only guard 能降低实战决策值低估，同时保持 q6 MAE 不变。
- 用户可接受适度激进的实战参考，但不应把 P90/tail 口径混入 q6 诊断。

边界：

- 该改动仍为 v3 shadow，`affects_bid=false`，不进入 v2 formal bid。
- diagnostics 必须在 override 生效时记录 `decision_p50_guard_quantile=*`。
- `2601` 样本仍少；P85 只是 shadow calibration，不作为 hidden promotion 依据。
- 后续如果新样本显示 high-over 上升，需要先按 map audit 回滚或下调 override，而不是继续加全局参数。

## D-v3-024：soft 均值证据进入 likelihood，但 random avg 暂不进 formal

v3 `ConstraintSet` 增加 `soft_numeric`，posterior likelihood 消费以下 soft 证据：

- `q4/q5/q6_avg_cells`：按对应质量桶 `cells / count` 进行软权重。
- `total_avg_cells`：按 `session.total_cells / session.total_count` 进行软权重。
- `q4/q5/q6_avg_value`：按对应质量桶 `value / count` 进行软权重。

暂不进入 formal likelihood 的证据：

- `random_*_avg_value`：保留为 diagnostic/random sample signal。
- `size_*_avg_value`：保留为 soft 事件，但本轮不用于 posterior。

原因：

- avg cells/value 是明确的质量桶或总量均值约束，适合作为 likelihood 权重。
- random avg 是抽样均值，不能等同于全仓或质量桶均值；v2 曾因把这类信号硬化而出现误判。
- size-bucket 均价需要按形状/格数桶建模，不能用质量桶均值逻辑替代。

边界：

- soft 证据只调整样本权重，不 hard reject。
- 重复状态中的同一 soft source 只保留最新 sort_id，避免同一证据被重复计权。
- diagnostics 记录 `soft_numeric_likelihood_weighted`，便于后续按证据类型切片。
- 该实现仍为 v3 shadow，`affects_bid=false`。

## D-v3-025：empirical prior calibration 必须同时满足 archive shift 与 baseline systemic-under

v3 新增 empirical prior calibration shadow，但激活条件收紧为：

- archive raw truth 相对表先验 median ratio 超过 neutral band。
- map/session 样本数达到最低门槛。
- hidden 低样本默认 watch-only。
- high-over map 不激活。
- 当前 v3 baseline 在该地图上必须满足 systemic-under：`formal_p50_bias <= -0.50 * formal_p50_mae`。

原因：

- 只看 archive/prior median ratio 会误激活 `2501/2504/2401`，导致整体 P50 MAE 恶化。
- `2506` 同时满足 archive shift 与 baseline systemic-under，校准后单图 MAE 有明确改善。
- `2507` 仍是 high-over 反例，不能把 shipwreck 家族整体抬高。

当前 active：

- `2506`：`scale=1.25`，`affects_bid=false`。

当前 watch-only：

- `2601`：hidden low sample。
- `2501/2504/2401`：archive median 偏高，但 baseline 不是强系统性低估。
- 其他少样本地图：low sample。

边界：

- calibration shadow 输出 `v3_cal_*` 字段，只进入 evaluator/live `model_eval` 诊断，不进入正式 `bid_rows`、停止价或抢仓上限。
- `data/processed/v3_prior_calibration_shadow.json` 是聚合派生表，不包含原始 Fatbeans capture。
- 后续 promotion 前必须用 holdout 或新增实战样本复核，不能用 in-sample archive 结果直接证明正式可用。

## D-v3-026：ccv bucket-likelihood shadow 保留审计，不作为 promotion 路线

`v3_ccv_*` 是 count/cell/value 条件采样的第一版审计候选，但当前决策是：不升级、不接正式出价、不替代 `v3_post_*` 或 `v3_cal_*`。

原因：

- 全量样本中 ccv 激活 329 个窗口，但整体 q6 count/cells P50 MAE 均小幅恶化：
  - count delta `+0.013`
  - cells delta `+0.005`
- 核心低估地图 `2506` 也恶化：
  - count delta `+0.03`
  - cells delta `+0.13`
- 局部受益地图如 `2502/2408` 不能证明该路线有普适 promotion 价值。
- 单纯强化 q6 bucket likelihood 仍是在调权重；它没有显式建模公共总格、非 q6 已知下界、q6 空间压力与 value per cell 的生成关系。

保留边界：

- `v3_ccv_affects_bid=false`。
- 只在 baseline 为 `summary_likelihood` 且有 q6 bucket evidence 时运行。
- hidden `2601` 默认禁用。
- 没有 q6 value evidence 时，不移动 q6 value/formal，也不移动 total/formal。
- 字段只用于 evaluator/live `model_eval`/map audit 对照。

下一步：

- 设计 residual/count-cell-value 生成模型，而不是继续调 ccv likelihood 温度。
- 该模型应把：
  - session total exact/floor
  - known non-q6 count/cells/value floor
  - q6 bucket count/cells/value evidence
  - item/shape/category anchors
  - map-level prior/calibration
  分层合成，先估 q6 count/cells，再估 value per cell。

## D-v3-027：residual sampler 进入 shadow，对 formal 保持非绑定

`v3_resid_*` 是当前 v3 residual/count-cell-value 生成模型候选，但决策是：保留 shadow，不覆盖 `v3_post_*`，不接 formal bid，不接 UI 主建议。

原因：

- 它比 `v3_ccv_*` 更接近目标结构：q6 component 与 non-q6 residual component 分开重组，能使用公共总格/总数和非 q6 已知下界推导 q6 capacity。
- `2506` 上出现有价值信号：q6 raw value delta `-29406.8`，count/cells 基本不恶化。
- 但全量 512-trial 默认激活结果仍不满足 promotion：
  - q6 count delta `-0.001`
  - q6 cells delta `+0.135`
  - q6 raw value delta `+5234.929`
- `2507` high-over 和 `2501` 非强系统性低估图显示无条件启用会污染整体口径。

边界：

- `v3_resid_affects_bid=false`。
- strict 窗口透传 baseline，仅 fallback 窗口运行。
- hidden `2601` 默认禁用。
- q6 capacity 使用硬上界：`session_total_exact - known_non_q6_floor`。
- 当前 total/formal/q6 formal 透传 baseline；residual raw value 只作为 shadow diagnostic。

下一步 promotion 前置条件：

- 先做 gated residual candidate，不做全局开关。
- 初始 gate 只考虑：
  - `2506` 或其它已证明 systemic-under 的地图。
  - fallback 窗口。
  - residual value delta 正向。
  - q6 cells delta 不恶化。
  - high-over 反例不启用。
- gate 通过后仍需 holdout 或新增实战样本验证，不能只用当前 in-sample archive。

## D-v3-028：residual gate 默认为 watch-only，等待 hero/evidence profile gate

`v3_resid_gate_*` 已接入 evaluator/live/map audit，但当前决策是：默认不 active。

原因：

- 只按 `2506` map-level systemic-under 启用 residual 会混合两种相反场景：
  - Aisha 2506 低估：residual 降 q6 count/cells/value 会加重错误。
  - Ethan 2506 过估：residual 降 q6 value 可能有帮助。
- 128-trial active candidate 已经显示三类指标均轻微恶化。
- 512-trial raw residual 也显示整体 cells/value 不稳定。

当前边界：

- `v3_resid_gate_active_rows=0`。
- `v3_resid_gate_active=false`。
- `v3_resid_gate_status=watch_only`。
- `v3_resid_gate_gate_reason=residual_gate_unproven`。
- `v3_resid_gate_source=baseline`。
- delta 字段仍保留，用于审计 residual 相对 baseline 的变化。

下一步必须先补：

- evaluator/live 行级 `hero` 或稳定 evidence profile。
- Aisha/Ethan 分片指标。
- Aisha 2506 tail/value 与 Ethan over-value residual 的独立 gate。

在这些完成前，不允许把 residual gate 接入 formal、calibration、UI 主建议或 v2 bid path。

## D-v3-029：residual promotion 必须先通过 hero/profile candidate gate

`v3_resid_*` 继续保持 shadow-only。下一版不允许按 map-level 或单行样本启用 residual，必须先通过 `hero_map_id` 或 `hero_map_evidence_profile` 候选审计。

原因：

- `2506` hero/map 分片显示 Aisha 与 Ethan 都仍系统性低估：
  - `aisha|2506`：`bias=-283924.6`，`below=0.790698`。
  - `ethan|2506`：`bias=-249550.4`，`below=0.678571`。
- residual 在 `ethan|2506` 上改善 q6 cells/value MAE，但 formal 仍低估，不能把 q6 raw value 下修误当作正式估值修复。
- profile 级别大多样本不足：128-trial candidate 表中 `blocked_low_sample=349`。
- 粗粒度 hero/map 出现的 2 个 over-correction 候选仍不满足 promotion：
  - `ethan|2601` 属 hidden，当前 residual 实际未运行。
  - `aisha|2504` high-over，但 q6 value delta 为正，仍可能伤害 value MAE。

硬边界：

- `v3_resid_gate_active_rows` 保持 0，除非后续 candidate table 同时满足：
  - 最小样本量。
  - 非 systemic-under，或有单独的上修型 formal calibration。
  - residual q6 count/cells/value MAE delta 不恶化。
  - public total / q6 floor 等证据足够解释切片。
  - hidden 单独验证，不与 shipwreck/villa 共用 gate。
- 任何 residual gate 仍必须 `affects_bid=false`，先进入 watch-only candidate，不进入 formal decision、UI 主建议或正式 stop/attack bid。

下一步：

- 把 candidate table 作为 v3 gate 的前置审计，不再盲目调 temperature/trials。
- 对 2506 的主方向改为 low-estimate repair：Aisha tail/value sampler、formal calibration、q6 value-per-cell 上修，而不是 residual 下修。

## D-v3-030：低估修复先走 bounded upshift shadow，不进入 formal

2026-06-05 起，`summarize_v3_underestimate_repair_candidates.py` 作为低估修复的候选审计入口。它只计算假设上修后的指标，不改变 evaluator/live 的正式 `v3_post_*` 字段。

当前决策：

- `hero_map_id` 可作为低估修复的第一层 shadow calibration 粒度。
- `hero_map_evidence_profile` 目前样本过稀，只作为诊断与 promotion 前复核，不作为上线 gate。
- `aisha|2506` 与 `ethan|2506` 可以进入 watch-only upshift candidate，但不得接 formal bid。
- hidden `2601` 即使 in-sample 改善，也必须单独验证，不与 shipwreck/villa 共用正式规则。

原因：

- 128-trial archive 显示 `aisha|2506` 小幅上修 scale `1.046065` 可把 formal MAE 从 `384517.7` 降到 `363546.8`。
- `ethan|2506` scale `1.045088` 可把 formal MAE 从 `416664.2` 降到 `404007.0`，并把 P90 coverage 从 `0.607143` 提到 `0.75`。
- profile 级候选仍是 `blocked_low_sample=349`，说明当前样本不足以证明细粒度规则。
- 这些结果仍是 in-sample archive 审计，没有 holdout/new-live 验证。

硬边界：

- bounded upshift 仍为 shadow/audit-only。
- 不改 formal decision value。
- 不改 UI 主建议。
- 不改正式 stop/attack bid。
- 不因为 hidden 2601 候选改善而放宽 hidden gate。

promotion 前置条件：

- 至少通过 paired archive/holdout 或新增实战样本验证。
- 同时观察 MAE、below rate、P90 coverage、over rate、pinball/极端过估，不只看 MAE。
- 公开总格/总数、q6 floor、shape/layout 等证据 profile 必须能解释上修，不允许纯 map 常数粗暴覆盖。

## D-v3-031：v3_under 进入 archive/live shadow，但保持 inactive

`v3_under_*` 作为 v3 低估上修候选的统一 shadow 命名空间。

当前决策：

- `data/processed/v3_underestimate_repair_shadow.json` 是默认 entry 表。
- `watch_only_upshift_candidate` 可以生成上修后的 shadow quantile。
- `watch_only_needs_evidence`、hidden、missing entry 只透传 baseline 并保留诊断。
- `v3_under_active=false` 固定保持。
- `v3_under_affects_bid=false` 固定保持。

原因：

- 128-trial 全库改善较小：formal MAE `312938.992 -> 312117.848`，delta `-821.144`。
- 2506 局部改善明显：map-level delta `-17692.3`，below `0.746479 -> 0.704225`，P90 coverage `0.619718 -> 0.704225`。
- 这说明它适合作为实战复核候选，但还不足以替换 formal。

硬边界：

- 不覆盖 `v3_post_*`。
- 不覆盖 `v3_cal_*`。
- 不进入 UI 主建议。
- 不进入正式 stop/attack bid。
- hidden 仍需单独验证，不因 entry 文件存在而上修。

下一步：

- 用新增 live/manual 样本复核 `aisha|2506`、`ethan|2506`、`ethan|2509` 的 scale 是否稳定。
- 若要 promotion，先做 holdout/paired comparison，并同时检查 MAE、below、P90 coverage、over、pinball。

## D-v3-032：低估上修 promotion 前必须通过 session holdout

`summarize_v3_underestimate_holdout.py` 成为 `v3_under` 从 watch-only 进入更高等级 candidate 的前置审计。

当前决策：

- promotion 不能再只看 in-sample archive candidate。
- holdout 必须按 `session_id` 切分，避免同一局不同窗口同时进入 train/test。
- 默认 gate 继续使用 `min_sessions=8`；`min_sessions=6` 只能作为敏感性分析，不作为正式晋级阈值。
- `hero_map_evidence_profile` 当前样本不足，不允许 profile 级正式上修。
- hidden `2601` 即使 holdout 正向，也仍需单独 hidden 样本规则，不与 shipwreck/villa 共用 promotion。

原因：

- 默认 `min_sessions=8` holdout 下，`aisha|2506` 稳定正向：MAE `384517.698 -> 362512.2`，delta `-22005.497`。
- `ethan|2506` 在默认 gate 下未稳定通过；放宽到 `min_sessions=6` 才出现正向，说明当前 Ethan 2506 样本不足以升级。
- 放宽 gate 同时会让 `ethan|2509` 进入并变差：MAE `419243.927 -> 420945.4`，证明低样本阈值会引入误判。
- profile holdout `candidate_rows=0`，说明细粒度证据 profile 还不能承载参数晋级。

硬边界：

- `v3_under_active=false`。
- `v3_under_affects_bid=false`。
- 不覆盖 `v3_post_*`、`v3_cal_*`、UI 主建议或正式 stop/attack bid。
- 新增样本只用于验证和候选筛选，不作为盲目扩大 trials 的替代。

样本策略：

- 当前 archive 足够继续 v3 架构重构、shadow 诊断和 Aisha 2506 方向判断。
- formal/live promotion 前需要定向新增样本，优先 `ethan|2506`，目标是新增约 `10-15` 个有效 complete sessions；`aisha|2506` 可补 `5-10` 个做 holdout 确认。

## D-v3-033：CCV sampler promotion 必须通过候选 gate

`estimate_count_cell_value_posterior_from_truths` 已接入 archive/live shadow，但它不能因为局部 count/cells 改善而进入 formal。2026-06-05 起，`summarize_v3_ccv_profile_candidates.py` 作为 CCV promotion 的前置审计。

当前决策：

- CCV 仍保持 shadow-only，`affects_bid=false`。
- 全局 CCV 不 promotion。
- `hero_map_id` 可用于发现候选，但 profile 级复核仍是 promotion 前置条件。
- 系统性低估切片中，如果 CCV 会继续下移 q6 count/cells，必须 block。
- 缺少公开总格/总数或 q6 floor 的正向切片只能进入 `watch_only_needs_evidence`。

原因：

- 128-trial 全库显示 CCV 对 count 几乎无收益，对 cells 有伤害：`count_delta=-0.001`，`cells_delta=+0.165`。
- `ethan|2502` 是当前唯一证据相对充分的 hero/map count-cell 候选：`count_delta=-0.11`，`cells_delta=-1.89`。
- `aisha|2409` 有局部正向信号，但 `public_total=0.0`，不能直接晋级。
- `ethan|2506` 虽有 `count_delta=-0.07`、`cells_delta=-1.22`，但 formal 仍系统性低估，且 `count_pred_delta=-0.07`、`cells_pred_delta=-2.22`，继续下移 q6 count/cells 的方向存在实战低估风险。
- profile 粒度仍然 `blocked_low_sample=349`，不支持细粒度正式规则。

硬边界：

- 不覆盖 `v3_post_*`。
- 不进入 `v3_cal_*`。
- 不进入 UI 主建议。
- 不进入正式 stop/attack bid。
- 不以 CCV count/cells 改善为理由绕过 formal MAE、below、P90 coverage、pinball 和 evidence coverage。

下一步：

- 用 candidate gate 观察 `ethan|2502` 是否能在 holdout 或新增样本中保持正向。
- 对 `aisha|2409` 优先补公开总格/总数覆盖审计，而不是直接调参数。
- `2506` 主线仍是低估修复与 value/tail sampler，不是 CCV 下移。

## D-v3-034：archive/live 必须复用同一个 v3 shadow pipeline

从 2026-06-05 起，archive evaluator 与 live monitor 不再各自手写 posterior/CCV/residual/calibration/underestimate 链路，统一调用 `estimate_shadow_pipeline()`。

当前决策：

- `src/bidking_lab/inference/v3/pipeline.py` 是 v3 shadow 链路的所有权边界。
- archive/live 只负责准备 source-specific 输入：events、constraints、summary、truth bank、replacement values、calibration entry、underestimate entry、hero。
- 任何新增 v3 shadow report、entry 表、字段命名或 gating 逻辑，必须先接入 pipeline，再由 archive/live 展开 flat fields。

原因：

- v3 当前已经有 `v3_post_*`、`v3_ccv_*`、`v3_resid_*`、`v3_resid_gate_*`、`v3_cal_*`、`v3_under_*` 多个命名空间；让 archive/live 各写一遍容易遗漏字段或参数。
- 用户实战已暴露过公开总格等输入遗漏风险，后续需要用共享入口减少路径分叉。
- 共享 pipeline 是 v2 -> v3 formal 迁移前的基础设施，先保证 shadow 一致，再讨论 promotion。

硬边界：

- pipeline 仍是 shadow-only。
- `affects_bid=false` 保持。
- 不改 UI 主建议。
- 不改正式 stop/attack bid。
- 不把 `v3_under`、`v3_ccv` 或 residual gate 自动提升到 formal。

下一步：

- 新增 sampler 或 calibration 时，优先给 pipeline 加 report，再更新 evaluator/live tests。
- 后续 v3 formal promotion 前，用 pipeline 作为唯一候选输出源，避免 archive 指标和 live 行为不同。

## D-v3-035：tail/value 只作为 review candidate，不接 formal

2026-06-05 起，`summarize_v3_tail_value_candidates.py` 作为 tail/value 问题的审计入口。它比较 formal truth 与 tail-replacement truth，但不改变正式估值口径。

当前决策：

- formal decision value 仍使用裁尾 plannable 口径。
- tail-replacement decision value 仍是 audit/helper 字段。
- tail/value candidate 只能进入 watch-only review，不进入 UI 主建议或正式出价。
- tail/value promotion 前必须同时看 formal MAE、tail-replacement MAE、P90 under、below/over、public total/q6 floor 和 profile 样本量。

原因：

- `aisha|2506` 与 `ethan|2506` 都出现 q6 tail/value review 信号：
  - `aisha|2506`：`tail_p90_under=0.372093`，`q6_tail_p90_under=0.325581`。
  - `ethan|2506`：`tail_p90_under=0.392857`，`q6_tail_p90_under=0.392857`。
- `ethan|2508` 显示 tail estimate 会伤害：`tail_delta=32201.7`，`q6_tail_delta=28270.1`。
- profile 粒度仍主要是 `blocked_low_sample=349`，不能把 hero/map 观察直接升级为细粒度规则。
- hidden `2601` 虽有明显 tail 信号，但 hidden 仍需单独样本规则。

硬边界：

- 不覆盖 `v3_post_formal_decision_value_*`。
- 不覆盖 `v3_cal_*` 或 `v3_under_*`。
- 不进入 UI 主建议。
- 不进入正式 stop/attack bid。
- 不把 raw long tail 直接算回 formal MAE。

下一步：

- 对 `2506` 保留 tail/q6-tail review，结合低估上修 holdout 继续看是否是正式低估或 tail audit gap。
- 对 `ethan|2508` 这类伤害切片保留 high-over/tail-hurts guard。
- 若后续做 tail/value sampler，只能先接入 pipeline 的新 shadow namespace，再通过 candidate/holdout 审计。

## D-v3-036：v3 formal promotion 以 readiness 总审计为入口

2026-06-05 起，`summarize_v3_promotion_readiness.py` 是判断 v3 是否可以进入 formal、以及 v2 是否可以 archive 的总入口。

当前决策：

- 不再用单个指标或单个候选脚本判断 promotion。
- readiness 必须同时汇总 archive 数据质量、shared pipeline、formal metrics、under holdout、CCV、tail/value、residual gate、profile depth 和 v2 archive readiness。
- `overall_status=not_ready` 时，不允许切换 v3 formal，也不允许 archive v2。

当前结果：

```text
overall_status=not_ready
blocked_gates=4
formal_baseline_metrics=blocked
ccv_sampler=blocked
residual_gate=blocked
profile_sample_depth=blocked
v2_archive_readiness=pending
```

原因：

- formal P50 仍偏低：`formal_below=0.51043`，P90 coverage `0.773794`。
- bounded upshift 有 holdout 候选，但仍 inactive。
- CCV cells 全局 delta 为正：`ccv_cells_delta=0.165`。
- residual active rows 必须保持 0。
- profile 粒度仍样本不足。

硬边界：

- readiness 脚本只审计，不改 pipeline。
- 不改变 UI。
- 不改变 formal bid。
- 不触发 v2 archive。

下一步：

- 每次新增样本或改 sampler 后优先跑 readiness。
- 只有 readiness 不再存在 blocked gate，且用户确认 promotion 策略后，才讨论 v3 formal 切换和 v2 归档。

## D-v3-037：CCV sampler promotion 必须通过 session holdout

2026-06-05 起，`summarize_v3_ccv_holdout.py` 是 CCV/count-cell-value sampler 从 watch-only 进入 formal 前的必要审计。

当前决策：

- `summarize_v3_ccv_profile_candidates.py` 只能发现候选，不足以证明可推广。
- 训练折识别出的 `watch_only_count_cell_candidate` 必须在 session 留出折上继续改善，才允许进入下一层 sampler 设计。
- 默认 `min_sessions=8` 不通过时，不用降低阈值绕过；放宽阈值只能作为灵敏度诊断。
- 当前 CCV 仍是 shadow/audit-only，`v3_ccv_affects_bid=false` 必须保持。

当前结果：

```text
hero_map_id min_sessions=8 candidate_rows=2 candidate_sessions=1 count_delta=0.0 cells_delta=0.0 q6_formal_delta=0.0
hero_map_evidence_profile min_sessions=8 candidate_rows=0 candidate_sessions=0
hero_map_id min_sessions=6 candidate_only cells_delta=+0.4 q6_formal_delta=+9288.7
```

原因：

- `ethan|2502` 的全量切片正向信号没有在 session holdout 中产生实际改善。
- profile 粒度全部被样本量或低活动挡住。
- 降低 session 门槛会引入看似候选但留出恶化的 group，说明 CCV 泛化不稳。

硬边界：

- 不把 CCV 接入 formal decision。
- 不把 CCV 接入 UI 主建议。
- 不用 `min_sessions=6` 结果做 promotion。
- 不用全量切片替代 holdout 证据。

下一步：

- 保留 CCV 作为诊断字段。
- 后续若实现条件 likelihood / count-cell-value sampler，必须先作为新 shadow namespace 或明确候选字段接入 pipeline，再跑 profile candidate 与 session holdout。
- `2506` 低估主线继续走 bounded upshift 与 tail/q6-tail review，不能用 q6 count/cells 下移修复。

## D-v3-038：tail/value review 需要 holdout 与 hurt guard 双门槛

2026-06-05 起，`summarize_v3_tail_value_holdout.py` 是 tail/value review 从候选进入任何 sampler 设计前的必要审计。readiness 的 `tail_value_review` gate 已接入该 holdout。

当前决策：

- tail replacement 仍只作为 audit/helper 字段，不进入 formal decision 或正式 bid。
- tail/value candidate 不能只看全量切片，必须看 session holdout。
- 即使 holdout aggregate 正向，也必须保留 hurt group guard。
- profile 粒度无 holdout candidate 时，不允许 profile-level promotion。

当前结果：

```text
hero_map_id candidate_only tail_delta=-718.0 q6_tail_delta=-4144.4
aisha|2506 tail_delta=-7935.2 q6_tail_delta=-5562.9
aisha|2601 tail_delta=-7367.3 q6_tail_delta=-32770.1
ethan|2601 tail_delta=+13339.4 q6_tail_delta=+24471.3
hero_map_evidence_profile candidate_rows=0
```

原因：

- `2506` 低估里确实有 q6-tail audit gap，tail review 对 Aisha 方向更稳定。
- `ethan|2601` 显示同一 tail mechanism 会严重伤害，不能全局启用。
- profile 粒度仍受样本量限制，无法把 hurt guard 下沉到更细 profile。

硬边界：

- 不覆盖 `v3_post_formal_decision_value_*`。
- 不覆盖 `v3_under_*` 或 `v3_cal_*`。
- 不进入 UI 主建议或正式出价。
- 不用 tail replacement truth 评估 formal MAE。

下一步：

- `2506` 低估主线继续并行看 bounded upshift 和 tail/q6-tail review。
- 若设计 tail/value sampler，先创建独立 shadow namespace，并内置 `ethan|2601` 这类 hurt guard。
- 补样应优先补 `2506` 与 `2601` 的 hero/map/profile 分层，而不是盲目增加 trials。

## D-v3-039：tail/value review 进入 shared pipeline，但保持 bid-safe

2026-06-05 起，tail/value review 不再只停留在离线脚本；`estimate_shadow_pipeline()` 输出 `v3_tail_review_*` namespace，archive evaluator 和 live monitor 使用同一 entry 表。

当前决策：

- `v3_tail_review_*` 是 shadow-only。
- `v3_tail_review_active=false` 恒成立。
- `v3_tail_review_affects_bid=false` 恒成立。
- `watch_only_q6_tail_value_candidate` 只表示 review candidate，不表示 formal promotion。
- `blocked_tail_estimate_hurts` 必须在 live/archive 字段中显式保留为 hurt guard。

当前 entry 表：

```text
aisha|2506 -> watch_only_q6_tail_value_candidate
aisha|2601 -> watch_only_needs_evidence, hidden_requires_separate_validation
ethan|2601 -> blocked_tail_estimate_hurts
```

原因：

- `aisha|2506` 是当前 tail/q6-tail 低估诊断最稳定的正向切片。
- `aisha|2601` 虽然 holdout 正向，但 hidden 仍需单独验证，不能直接标成 candidate。
- `ethan|2601` 明确 tail hurt，必须让 live/archive 都能看见该 guard。

硬边界：

- 不覆盖 `v3_post_*`。
- 不覆盖 `v3_under_*`。
- 不进入 UI 主建议。
- 不进入正式出价。
- 不用 tail replacement truth 替代 formal truth。

下一步：

- 在 `v3_tail_review_*` 上继续做 sampler/guard 设计。
- 若后续要展示给 UI，只能作为辅助审计提示，不能替代主估价。
- 每次更新 entry 表后必须跑 evaluator、readiness、live monitor tests。

## D-v3-040：under/tail 组合候选必须通过 hidden guard 与 applied-hurt guard

2026-06-05 起，`summarize_v3_tail_under_holdout.py` 是 under upshift 与 tail/value review 进入任何 sampler 设计前的组合审计。readiness 新增 `tail_under_combined_holdout` gate。

当前决策：

- `260x` hidden map 不允许在 under 或 tail candidate 生成器中直接成为可应用候选。
- hidden 切片统一降为 `watch_only_needs_evidence`，除非后续有单独 hidden holdout 证明并新增明确决策。
- `tail_under_combined_holdout` 必须检查 applied candidate 内部是否仍有 hurt group；只看总体 delta 不够。
- 若 holdout 中出现 tail candidate 应用后 `tail_delta` 或 `q6_tail_delta` 明显变差的 group，该组合 gate 保持 blocked。
- tail replacement 仍然只用于审计，不覆盖 formal truth 或 formal decision。

当前 128-trial 结果：

```text
v3_under_candidate_rows=43
under_rows=37 tail_rows=39 hurt_rows=11
candidate_only rows=39
under_groups=aisha|2506
tail_groups=aisha|2506,ethan|2502
tail_under_formal_delta=-24262.471
tail_under_p90_extreme_delta=0.0
tail_under_applied_hurts=
tail_under_combined_holdout=watch
```

原因：

- 放宽前的组合 holdout 会把 `ethan|2601` 部分训练折误判为 tail candidate，holdout 上 `tail_delta=+12001.7`、`q6_tail_delta=+25134.7`，属于明确 applied hurt。
- hidden `2601` 在现有样本里 Aisha/Ethan 方向不一致，不能和 shipwreck/villa 使用同一升级规则。
- 经过 hidden guard 后，`ethan|2601` 只保留 hurt guard，`aisha|2601` 不再通过 under/tail 可应用候选。
- `v3_underestimate_repair_shadow.json` 同步 guarded holdout 后，Ethan 2506/2509 保留记录但不再作为可应用 `watch_only_upshift_candidate`。

硬边界：

- 不修改 `v3_post_*`。
- 不修改正式 live bid 或 UI 主建议。
- 不把 hidden 2601 正向结果外推到 Ethan hidden 或其他 hidden。
- 不因为组合 gate 为 watch 就视为 formal promotion。

下一步：

- `aisha|2506` 可继续作为 guarded sampler 的主要设计对象。
- `ethan|2502` tail candidate 当前 holdout delta 为 0，应保持观察，不应因 candidate 名义进入正式策略。
- formal baseline 低估仍需从 likelihood/profile/sample-depth 继续修，不应只靠局部 upshift。

## D-v3-041：CCV promotion 必须通过多层 holdout，不能只看默认 hero/map

2026-06-05 起，CCV readiness 除默认 `hero_map_id` holdout 外，必须同时看 `map_id` 层 holdout。`summarize_v3_ccv_layer_audit.py` 用于并列审计 `hero_map_id`、`map_id`、`map_family`、`hero_map_evidence_profile`。

当前决策：

- `ccv_sampler` gate 保持 blocked，只要任一关键层级出现 applied hurt group。
- `map_id` 层出现 q6 count/cells/value/formal 明显伤害时，即使默认 `hero_map_id` 候选为空或中性，也不能 promotion。
- `hero_map_evidence_profile` 当前样本不足，不能作为放行层级。
- 不允许把 `map_id=2502` 的局部正向外推到同 family 或同 shipwreck 全局。

当前 128-trial 结果：

```text
hero_map_id candidate_rows=2 groups=ethan|2502 formal_delta=0.0 applied_hurts=
map_id candidate_rows=64 groups=2502,2503,2504 formal_delta=+21205.4 applied_hurts=2503
map_family candidate_rows=0
hero_map_evidence_profile candidate_rows=0
```

原因：

- 默认 `hero_map_id` 口径太窄，会让 CCV 看起来只是“无收益”。
- `map_id` 口径暴露训练折会误放 `2503/2504`，其中 `2503` 在 holdout 上 q6 formal 明显变差。
- CCV 当前问题是分层不稳定，不只是 trials 数不足。

下一步：

- CCV 需要重做条件 likelihood 或更强的 layer gate。
- 继续优先把公开总格、q6 floor、value evidence 显式纳入 likelihood，而不是按当前 CCV 候选直接接 formal。

## D-v3-042：CCV count/cell tail guard 只能作为审计开关，不能作为修复升级

2026-06-05 起，`count_cell_tail_guard`、`value_tail_guard`、`condition_temperature`、`relative_floor` 可以通过 `V3CcvOptions` 在 archive evaluator 中做 sensitivity 审计。默认 live/archive 调用保持原值。

当前决策：

- 默认 `v3_ccv_*` 不改变，仍为 shadow-only。
- `count_cell_tail_guard=False` 只能用于审计，不作为 promotion 候选。
- 不允许通过“关闭 count/cell guard”来规避 map-level applied hurt。
- 若要继续推进 CCV，必须改 likelihood/candidate layer，而不是只调 guard 开关。

当前 128-trial 结果：

```text
default cells_delta=+0.165 count_mae=1.44 cells_mae=7.008
count_cell_tail_guard=off cells_delta=+0.225 count_mae=1.482 cells_mae=7.068
count_below_delta=+0.025424 count_p90_cover_delta=-0.029335
cells_below_delta=+0.019557 cells_p90_cover_delta=-0.02412
default map hurt=2503
alternative map hurt=2502
```

原因：

- 关闭 guard 确实会压低 q6 count/cells 预测，但该压低并未提升准确性；它增加了 below-q6 风险并降低 P90 coverage。
- hurt group 从 `2503` 转移到 `2502`，说明风险来自 CCV 条件匹配/候选泛化，而不是单个 tail guard。
- 当前 CCV 修复方向应回到 evidence-conditioned likelihood：公开总格、q6 floor、value evidence、non-q6 residual capacity 需要以统一似然方式进入，而不是固定候选上修/下修。

硬边界：

- `V3CcvOptions` 不改变 formal decision、不改变 live bid、不改变 UI 主建议。
- readiness 仍以默认 `v3_ccv_*` 与 layer holdout 为准；sensitivity 结果只作为设计证据。

## D-v3-043：CCV promotion 必须通过 p50 directionality gate

2026-06-05 起，CCV 不仅要通过 session holdout 和 map-layer applied hurt 检查，还必须通过 p50 movement directionality 检查。`summarize_v3_ccv_direction_audit.py` 与 readiness 的 `ccv_directionality` gate 是正式 promotion 前的必要审计。

当前决策：

- 如果 CCV 在 map 层或 evidence profile 层出现 `blocked_directional_hurt`，`ccv_directionality` 保持 blocked。
- 方向性 hurt 包括：
  - baseline 已低估，CCV 继续下移。
  - baseline 已高估，CCV 继续上移。
  - CCV changed rows 中 hurt 比例过高。
- 不允许只用 `public_total_rate`、`layout` 或 `q6_floor_rate` 放行 CCV。
- `public:total+item+shape+layout` 当前必须视为风险 profile，不是安全 profile。

当前 128-trial 结果：

```text
map_id direction status_counts=blocked_directional_hurt:20,blocked_low_movement:13,watch_directional_candidate:9
2503 q6_count hurt_rate=0.733333 directional_error=0.466667 mae_delta=+0.127
2503 q6_cells hurt_rate=0.55 directional_error=0.25 mae_delta=+0.438
2502 q6_count watch hurt_rate=0.230769 mae_delta=-0.095
2502 q6_cells watch hurt_rate=0.36 mae_delta=-0.708

evidence_profile public:total+item+shape+layout:
q6_count hurt_rate=1.0 directional_error=0.75 mae_delta=+0.152
q6_cells hurt_rate=0.75 directional_error=0.333333 mae_delta=+0.505
```

原因：

- CCV 的失败不是单纯“是否上调/下调太多”，而是很多窗口的移动方向本身与真实误差相反。
- 这会解释“总体/局部 MAE 有时看起来可接受，但实战仍低估或乱跳”的现象。
- 后续新的 CCV likelihood 必须用 directionality gate 做第一层回归，防止重新引入旧问题。

## D-v3-044：directionality 通过 session holdout 前不能转成 sampler 规则

2026-06-05 起，`summarize_v3_ccv_direction_holdout.py` 作为 `ccv_directionality` 之后的二级验证。它不直接评估全量 CCV 输出，而是在每个 session fold 里只把训练折状态为 `watch_directional_candidate` 的 `(component, group)` 应用到验证折，检查这些“看起来方向正确”的移动能否跨 session 泛化。

当前决策：

- `directionality` 和 `direction_holdout` 都是 promotion blocker，不是正式 sampler。
- `map_id` direction holdout blocked 时，不允许把局部 map 候选接入 formal/live。
- `evidence_profile_key` 即使为 watch，也只能作为 likelihood 重构线索；收益过小或 q6 cells 不稳时不能升级。
- `summarize_v3_promotion_readiness.py` 的 `ccv_direction_holdout` gate blocked 时，v3 仍保持 `not_ready`。

当前 128-trial 结果：

```text
map_id:
overall_status=blocked_holdout_directional_hurt
candidate_rows=438
candidate_delta=+0.168
candidate_hurt_rate=0.086758
candidate_directional_error=0.06621
applied_hurts=q6_cells:2502,q6_cells:2506,q6_count:2501,q6_count:2409,q6_count:2506
component=q6_cells delta=+0.567
component=q6_count delta=+0.045

evidence_profile_key:
overall_status=watch
candidate_rows=348
candidate_delta=-0.057
candidate_hurt_rate=0.051724
candidate_directional_error=0.025862
applied_hurts=
component=q6_cells delta=-0.011
component=q6_count delta=-0.069
```

原因：

- map-level 候选在训练折看起来有方向性，但验证折仍会伤害 `2502/2506/2501/2409` 等 group。
- profile-level 候选只提供弱正向信号，不能替代真正的条件 likelihood。
- 下一步应重做 CCV likelihood/组件分解，让公开总格、q6 floor、value evidence、non-q6 capacity 共同决定 q6 count/cells/value 分布，而不是把 direction gate 输出当固定规则。

## D-v3-045：component likelihood 先作为 v3_ccvc_ shadow，不进入 formal

2026-06-05 起，第一版 evidence-conditioned CCV component likelihood 以 `v3_ccvc_` 前缀输出。它是 v3 core 重构候选，不替换现有 `v3_ccv_`、不进入 formal decision、不影响 live/UI 主建议。

当前决策：

- `v3_ccvc_` 必须通过 directionality + session holdout 后，才允许进入 readiness gate。
- 默认 evaluator/live pipeline 不运行 component likelihood；只有 `V3CcvOptions(component_likelihood=True)` 或 CLI `--ccv-component-likelihood` 显式开启。
- 组件后验允许用明确 `quality=6` 的 item/shape anchor 与 q6 avg soft numeric 影响 q6 component。
- 未标明质量的 anchors 暂不硬归入 q6 component，只记录 `ccvc_unassigned_anchor_count`，避免把无质量证据误当 hard footprint。

当前 128-trial 结果：

```text
v3_ccvc_component_likelihood_rows=1050
v3_ccvc_delta_q6_count_p50_mae=-0.033
v3_ccvc_delta_q6_cells_p50_mae=-0.168
v3_ccvc_delta_q6_value_p50_mae=-6864.3

map_id direction status_counts=blocked_directional_hurt:24,blocked_low_movement:7,watch_directional_candidate:11
evidence_profile direction status_counts=blocked_directional_hurt:16,blocked_low_movement:1,blocked_low_sample:44,watch_directional_candidate:9
```

原因：

- component likelihood 证明“q6 component + non-q6 residual capacity”的方向比旧 CCV 更接近 v3 目标。
- 但 changed rows 中仍有大量方向性 hurt；全局 MAE 改善不能证明实战可用。
- 下一步必须给 `v3_ccvc_` 增加 holdout candidate gate，并拆解哪些证据组合导致反向移动，尤其 `random_avg`、`item+shape`、`public:total+item+shape`。

## D-v3-046：v3_ccvc_ 通过 holdout 前不得推广，且不能靠简单收紧阈值推广

2026-06-05 起，`summarize_v3_ccv_direction_holdout.py --candidate-prefix v3_ccvc_` 作为 component likelihood promotion 前置审计。当前决策：

- `v3_ccvc_` q6_count/q6_cells 均保持 shadow-only。
- q6_cells 不允许进入 formal candidate；map/profile holdout 均有明确 applied hurt。
- q6_count 只能作为下一步 evidence contribution 分析对象，不能直接 promotion。
- 不采用“单纯降低 max hurt rate / directional error rate”的方式推广；严格 gate 在 profile q6_count holdout 上从 `-0.012` 变为 `+0.081`。

当前 128-trial 结果：

```text
map_id q6_count+q6_cells:
overall_status=blocked_holdout_directional_hurt
candidate_delta=+0.097
q6_count delta=-0.017
q6_cells delta=+0.354

evidence_profile_key q6_count+q6_cells:
overall_status=blocked_holdout_directional_hurt
candidate_delta=-0.030
q6_count delta=-0.012
q6_cells delta=-0.092

evidence_profile_key q6_count strict gate:
candidate_rows=99
candidate_delta=+0.081
```

原因：

- component likelihood 的全局改善主要说明骨架方向正确，不说明各证据组合的移动方向可靠。
- q6_cells 在 map holdout 上是主要伤害源。
- q6_count 的收益很小，容易被少数组的 wrong-direction move 抵消。
- 下一步必须拆 evidence contribution，而不是继续盲目调 threshold。

## D-v3-047：CCVC 下一步必须拆 count/cells 的证据 gate

2026-06-05 的 evidence contribution audit 后，v3 CCVC 后续设计采用 count/cells 分离策略：

- q6_count 可以继续作为 component likelihood 候选研究，但不能直接 promotion。
- q6_cells 不允许随 q6_count 一起移动；必须先有更强的 capacity/total consistency 或 holdout guard。
- `public_max_item_cells`、`tool_category`、`item_anchor` 不得作为 q6_cells 上调/下调的直接放行条件。
- `public_total`、`layout`、`public_random_avg` 对 q6_cells 只能作为高风险线索；即使 MAE 改善，也要先过 changed-row hurt gate。

当前 128-trial contribution 结果：

```text
q6_count:
overall delta=-0.033 hurt_rate=0.443730
unassigned_anchor delta=-0.115 present_minus_absent=-0.127
tool_category delta=-0.093 present_minus_absent=-0.072
q6_floor delta=-0.052 present_minus_absent=-0.030
public_total delta=-0.040 present_minus_absent=-0.009

q6_cells:
overall delta=-0.168 hurt_rate=0.495177
public_max_item_cells hurt_rate=0.653061 present_minus_absent=+0.129
tool_category hurt_rate=0.600000 present_minus_absent=+0.172
item_anchor hurt_rate=0.520803 present_minus_absent=+0.278
public_total hurt_rate=0.447236 present_minus_absent=-0.745
```

原因：

- count 和 cells 的证据方向不同，不能共用一个 CCVC movement gate。
- q6_cells 的 MAE 改善来自一部分高信息窗口，但 hurt rate 已接近或超过 blocker 阈值。
- 继续整体调权重会把有用的 count 信号和高风险 cells 信号混在一起，复现 v2/v3 的“局部改善但实战反向”问题。

## D-v3-048：CCVC freeze-cells 只能作为 count-only shadow，不进入 formal

2026-06-05 新增 `--ccv-component-freeze-cells` 后，v3 CCVC 允许在审计中冻结 q6_cells，仅移动 q6_count/q6_value。

当前决策：

- `component_move_cells=False` 只作为 shadow/audit 口径。
- formal live decision 不接入 freeze-cells、CCVC、tail replacement。
- q6_cells movement 在没有更强 capacity/total consistency 和 holdout guard 前保持冻结。
- q6_count movement 即使在 freeze-cells 下仍需要 profile holdout 通过后才可讨论 promotion。

当前 128-trial 结果：

```text
archive:
v3_ccvc_delta_q6_count_p50_mae=-0.033
v3_ccvc_delta_q6_cells_p50_mae=0.000
v3_ccvc_delta_q6_value_p50_mae=-6864.3

evidence_profile holdout:
overall_status=blocked_holdout_directional_hurt
q6_cells candidate_rows=0
q6_count delta=-0.012
q6_count hurt_rate=0.083673
q6_count directional_error=0.048980
```

原因：

- freeze-cells 消除了 q6_cells 误移动，但没有解决 q6_count 在部分 evidence profile 下的反向移动。
- 当前收益更像“可控 shadow 基线”，不是可上线推荐。
- v3 正式使用必须证明低估风险下降、normal absolute error 不恶化，并且 changed-row hurt 受控。

## D-v3-049：q6_count movement-policy 仍为审计候选，不作为低估修复推广

2026-06-05 的 movement-policy matrix 后，v3 暂不把 q6_count policy gate 接入 formal。

当前决策：

- `summarize_v3_ccv_direction_*` 的 `--movement-policy`、复合 group-field、candidate include/exclude 只作为 audit 工具。
- `down_only + evidence_profile_key + min_windows=30 + exclude ^q6_count:shape$` 可以作为 q6_count over-count 修正 shadow 候选。
- 该候选不得作为低估修复推广；它会提高 q6_count below-rate。
- `map_id,evidence_profile_key` 硬交叉在当前样本量下过稀疏，不作为 promotion gate。
- q6_count gate promotion 以后必须同时看 sampler stability、below-rate、map holdout 和 profile holdout。

当前结果：

```text
128-trial matrix:
all/up_only/down_only x map/profile/composite 均未整体通过。

256-trial profile down_only min_windows=30 exclude bare shape:
status=watch
candidate_rows=157
delta=-0.025
hurt_rate=0.025478
directional_error=0.006369
baseline_below=0.401274
candidate_below=0.420382
```

原因：

- `up_only` 更符合“低估修复”直觉，但 archive holdout 收益太弱且仍有 applied hurt。
- `down_only` 的 MAE 改善来自修正 q6_count 过高；它与实战低估问题方向不同。
- bare `shape` 在 128/256 trials 间不稳定，说明 promotion gate 必须包含 sampler stability。

## D-v3-050：residual q6-value under candidate 不作为 formal 低估修复

2026-06-05 新增 residual q6-value under holdout 后，当前决策：

- `summarize_v3_residual_under_value_holdout.py` 只作为 audit 工具。
- residual q6_value 上移不得接入 formal decision。
- 当前 residual posterior 保持 `resid_formal_passthrough`，不改变正式出价口径。
- `public:total+item+shape`、`public:total+shape` 只能继续观察，不能 promotion。
- formal 低估修复必须另做 value/formal sampler，而不是把 residual q6_value shadow 直接当出价修复。

当前结果：

```text
128-trial:
candidate_groups=public:total+item+shape,public:total+shape
q6_value_delta=+15187.3
blocked by public:total+item+shape

256-trial:
candidate_groups=public:total+item+shape,public:total+shape
q6_value_delta=-17189.8
blocked by public:total+shape

128-trial seed=1 min_windows=30:
candidate_rows=0
```

原因：

- 同一 profile 在不同 trials/seed 下 candidate 方向不稳定。
- formal_delta 始终为 `0.0` 是预期边界：residual report 当前 formal passthrough。
- 这条路线只能帮助定位 q6 component 问题，不能证明实战低估已修复。

## D-v3-051：q6 formal delta mapping 不接 formal，保留为 audit

2026-06-05 新增 `summarize_v3_formal_value_delta_holdout.py` 后，当前决策：

- `candidate_formal = baseline_formal + (candidate_q6_formal - baseline_q6_formal)` 只作为 audit 公式。
- `v3_ccv_`、`v3_ccvc_`、`v3_resid_` 均不得通过该公式接入 formal live decision。
- formal-value promotion 必须加入 high-over guard；候选 over-rate 高于 `0.60` 时，即使 MAE 小幅改善也不放行。
- `v3_resid_` / `v3_ccvc_` 当前没有 q6 formal delta，不具备 formal-value 修复能力。
- `v3_ccv_` 的 q6 formal delta 在 archive holdout 下不稳定且会伤害，不能推广。

当前结果：

```text
v3_resid_: candidate_rows=0
v3_ccvc_ freeze-cells: candidate_rows=0

v3_ccv_ profile 128-trial:
candidate_groups=item+shape+layout
formal_delta=+6633.5
applied_hurts=item+shape+layout

v3_ccv_ profile 256-trial:
candidate_rows=0

v3_ccv_ map 128-trial:
candidate_groups=2502
formal_delta=-1015.2
candidate_over=0.75
applied_hurts=2502
```

原因：

- formal 低估修复不能只看 q6 component delta；必须看整体 formal MAE、below-rate、over-rate、P90 和 trials stability。
- `2502` 例子说明轻微 MAE 改善可能来自已高过估窗口，不符合实战参考价值。

## D-v3-052：0605 后 252x 沉船活动样本独立 cohort，不混入旧沉船 prior 校准

2026-06-06 解析新增 manual inbox 后，当前决策：

- `2026-06-05 12:00 +08:00` 之后的 252x 沉船样本标记为活动 cohort。
- 在本地 `BidMap.txt` / `Drop.txt` 更新前，252x 活动沉船样本不得混入普通 250x 沉船 drop-prior/posterior 校准。
- 活动 cohort 归档路径为 `data/samples/fatbeans_activity_20260605_shipwreck/`；默认 evaluator 不自动扫描该路径。
- 这些样本可以用于：
  - parser/capture 兼容验证；
  - pre-bid window 边界验证；
  - settlement truth / formal decision truth 审计；
  - 后续活动映射或新表校验。
- 24xx 别墅样本不受沉船活动影响，可作为普通真实样本使用。

原因：

- 新增样本中有 15 个 `2521/2522/2524/2526/2528/2529` 沉船窗口。
- 当前 `data/processed/maps.json` 不包含这些 252x map id；`BidMap.txt` / `Drop.txt` 仍是旧表。
- 活动说明“白色藏品有概率变成红色藏品”会改变品质分布；用旧 250x drop prior 直接解释 252x 会把活动机制误记为模型误差。

## D-v3-053：prior robustness gate 是 v3 promotion 的前置边界

2026-06-06 起，archive evaluator 输出 `v3_robust_*` prior/activity 审计字段。当前决策：

- `v3_robust_affects_bid=false` 固定保持。
- `v3_robust_prior_trusted=true` 才能作为 formal promotion 的强证据分母。
- `v3_robust_prior_usable=true` 只能说明可做保守 shadow 参考，不等于可 promotion。
- `activity_candidate=true` 或 `fallback_mode=missing_prior_truth_only` 时，不得使用旧 drop prior 做普通校准。
- `summary_likelihood_conservative` 可保留为弱 fallback，但默认 `prior_trusted=false`。
- `q6_projection_audit_only` 不得作为 promotion 依据。
- `prior_stress_score>0` 的行必须单独分片报告，避免把活动、表漂移或 hard evidence 异常误当普通模型误差。
- `summarize_v3_promotion_readiness.py` 的 `prior_robustness` gate 必须通过后，才允许讨论 formal promotion。

原因：

- 游戏会出现持续一周的爆率/品质活动，旧先验可能临时失效。
- 0605 后 252x 沉船活动 cohort 已证明“样本可解析但本地 drop prior 缺失”是现实状态。
- v2/v3 之前的调参风险在于把不同数据质量、不同先验可信度混在同一指标分母里；v3 promotion 必须先隔离这种漂移。

## D-v3-054：prior robustness 必须在 archive/live/model_eval 同步输出

2026-06-06 起，`v3_prior_*` 与 `v3_robust_*` 是 archive/live 共享 shadow 字段：

- `src/bidking_lab/inference/v3/priors.py` 负责生成 `v3_prior_*` flat fields。
- archive evaluator 与 live monitor 不得各自维护不同的 prior field set。
- live `v3_posterior_shadow` 必须包含 `v3_robust_*`。
- live `model_eval.jsonl` 必须展开 `v3_prior_*` 与 `v3_robust_*`，用于实战后筛查活动、缺表、prior stress 和弱 fallback。
- `v3_robust_*` 不进入 UI 主建议、不影响停止价、抢仓价或 v2 formal bid。

原因：

- v3 的 promotion gate 依赖 `prior_robustness`，如果 live 缺字段，局后实战样本会和 archive 审计分母不一致。
- 活动爆率/品质调整通常先在实战 live 里出现；live 必须先记录 drift 信号，再决定是否纳入普通校准或单独建 activity overlay prior。

## D-v3-055：prior-stressed 行必须先分片审计，不进入普通 sampler 校准分母

2026-06-06 起，`summarize_v3_prior_robustness_audit.py` 是处理 `prior_stress_score>0` 的默认入口。当前决策：

- `prior_stressed` 行不得直接混入普通 formal/value sampler calibration 分母。
- sampler/holdout 报告必须至少分开：
  - trusted strict；
  - weak fallback；
  - prior-stressed；
  - activity/prior-unavailable。
- 如果压力原因是 `total_cells_above_prior` 或 `q6_cells_above_prior`，优先审计 evidence/capacity/cells 一致性，不直接调高 q6 value。
- 如果压力原因是 `q6_value_above_prior` / `total_value_above_prior`，可作为 formal/value sampler 候选审计分片，但仍需 holdout 与 high-over guard。
- activity/prior-unavailable 行只能用于鲁棒性、parser/window/truth 或 activity overlay prior 设计，不计普通模型准确率。

原因：

- 64-trial archive 中 `prior_stressed=94`，其中 `summary_likelihood=92`。
- `prior_stressed` 分片 `below=0.670213`、`p90_cover=0.595745`，明显比普通 weak fallback 更差。
- 最大压力来自 cells/count/capacity 证据，不是单纯 q6 count prior 问题。

## D-v3-056：formal/value sampler 必须拆分 prior-stress 明细维度

2026-06-06 的 `--details` 审计后，当前决策：

- formal/value sampler 第一阶段必须把 `prior_stressed` 至少拆成：
  - cells/capacity drift：total cells exact/floor、target/truth/posterior、item count 是否超过 prior max；
  - q6 cells floor/exact stress：q6 cells target/prior ratio 与 posterior-vs-truth delta；
  - value-floor stress：total/q6 value floor 相对 prior/truth/posterior 的 delta。
- sampler candidate、readiness、holdout 和 live shadow report 不能只用一个 `prior_stressed=true` 标签；必须报告 exact/floor source、target/prior ratio、target-vs-truth delta、posterior-vs-truth delta 和 capacity flags。
- cells/capacity drift 不得直接转成 q6 value 上修；需要先判断是旧表/capacity prior 漂移、地图/profile 特殊容量，还是 parser/window 映射异常。
- value-floor stress 可以进入 formal/value candidate 审计，但必须单独通过 below-rate、P90、pinball、high-over、trials/seed stability 和 map/profile holdout。
- activity/prior-unavailable cohort 仍不产生 prior-stress details，不进入普通 sampler calibration。

原因：

- 明细审计中存在 hard target 与 truth 一致且 item count 超出 prior max 的样本，例如 `ethan|2506|shape` 与 `ethan|2406|public:max_item_cells+item+shape+layout`。
- `q6_cells_above_prior` 的 target/prior ratio 很高，但部分行 posterior 已经高于 truth，统一 cells 上修会复现 high-over 风险。
- `q6_value_above_prior` / `total_value_above_prior` 的风险形态更接近 value floor 和 formal-value 建模问题，不能与 cells/capacity mismatch 混为一个 calibration 分母。

## D-v3-057：`v3_fv_*` formal/value sampler 第一阶段保持 shadow-only，promotion 前必须过专用 holdout

2026-06-06 起，formal/value sampler 第一阶段的当前决策：

- `v3_fv_active=false` 与 `v3_fv_affects_bid=false` 固定保持；不得影响停止价、抢仓价、formal bid 或 UI 主建议。
- sampler 输出必须同时包含：
  - `stress_class`：`capacity_cells_drift`、`q6_cells_floor_stress`、`value_floor_stress`；
  - exact/floor source、target、prior expected、target/prior ratio；
  - `capacity_flags`，特别是 item count target 超过 prior max 的情形。
- capacity/cells-only watch 行不得转成 formal value 上修；它们只能进入 evidence/capacity/prior 审计。
- value-floor stress 可以标记为 `v3_fv_candidate=true`，但仍然只作为 shadow candidate。
- promotion readiness 必须包含 `formal_value_sampler_holdout` gate；默认 session holdout 不通过时，不能讨论 v3 formal promotion 或 v2 archive。
- holdout 训练折只用 value-floor candidate 选择 group，验证折也必须要求该 holdout 行本身触发 `v3_fv_candidate`，避免把 group-level 信号错误套到 capacity/cells-only 行。

原因：

- 当前 archive 只有 `v3_fv_value_floor_candidate_rows=13`，默认 holdout 为 `sample_limited`。
- `v3_fv_delta_formal_p50_mae=0.0`，说明第一阶段没有可推广的 formal 改善证据。
- prior-stressed 明细已证明 cells/capacity drift 与 value-floor stress 风险不同；混合校准会重复 v2/v3 早期的 over/under 混淆风险。

## D-v3-058：capacity/table/evidence drift 必须作为独立 gate，不能由 formal/value sampler 隐式吸收

2026-06-06 `--detail-summary` 聚合后，当前决策：

- prior-stressed rows 中只要出现 `target_count_above_prior_max` 或 `truth_count_above_prior_max`，必须进入 capacity/table/evidence drift 审计分母。
- 这类行不得被 `v3_fv_*`、underestimate repair、tail/value review 或 CCV sampler 当成普通 formal 低估样本隐式吸收。
- promotion/readiness 报告必须保留 capacity flag counts、source counts 和 target/prior ratio 分布；不能只报告 MAE delta。
- 对 `total_cells_above_prior`，必须区分 exact hard evidence 与 floor evidence；exact 与旧 prior 冲突时优先检查表、map/profile capacity 或 capture/settlement 口径。
- 对 `q6_cells_above_prior`，必须单独检查 q6 cells directionality/over risk；不得直接推导为 q6 value 或 formal value 上修。
- 252x activity/prior-unavailable rows 仍不得进入普通 prior-stress/detail-summary calibration 分母。

原因：

- 当前 detail summary 显示 `truth_count_above_prior_max=68/94`、`target_count_above_prior_max=39/94`。
- `total_cells_above_prior` 中 `exact=32/48`，说明很多冲突来自 hard evidence 而非 sampler 随机误差。
- `q6_cells_above_prior` 中 `source=floor:32/32` 且 ratio max `4.001`，需要独立 cells guard。

## D-v3-059：capacity/table drift 后续必须按 map/profile 分片验证

2026-06-06 `--detail-summary-by` 聚合后，当前决策：

- prior-stressed 的 capacity/table/evidence drift 后续审计必须至少并列报告 `map_id`、`evidence_profile_key`、`hero_map_evidence_profile`。
- `capacity_flag_hits` 高的 group 优先进入 table/capacity/prior max 口径审计，不进入 formal/value promotion 分母。
- `max_value_ratio` 高但 capacity hits 不高的 group 可作为 formal/value sampler 候选分片，但仍需专用 holdout 和 high-over guard。
- readiness 报告需要继续把 global prior robustness 与这些 targeted group 分片区分开；global MAE 改善不能覆盖 map/profile drift 风险。
- activity/prior-unavailable cohort 仍保持独立，不使用旧表做 map/profile capacity 推断。

原因：

- 当前 top map groups 形态不同：`2501`、`2601` capacity hits 高；`2406` value ratio 高；`2404` cells ratio 高但 value ratio 不高。
- 单一 `prior_stressed=true` 标签无法指导是修表、修 capacity prior、修 q6 cells likelihood，还是设计 value-floor sampler。

## D-v3-060：`prior_stress_capacity_table_drift` 是 promotion readiness 的硬 blocker

2026-06-06 起，`summarize_v3_promotion_readiness.py` 必须输出 `prior_stress_capacity_table_drift` gate。当前决策：

- 只要 prior-stress detail summary 中存在 capacity/table/evidence drift rows，该 gate 为 `blocked`。
- 该 gate blocked 时，不允许用 formal/value sampler、under/tail、CCV 或 calibration 的局部改善讨论 v3 formal promotion。
- 该 gate 必须同时报告 total rows、capacity flag hits、top map groups、top profile groups、source counts 与 ratio summary。
- activity/prior-unavailable rows 不进入该 gate 的 detail 分母；它们继续由 prior robustness/activity gate 阻断。
- v2 archive 仍保持 `pending`，直到该 gate、formal baseline、holdout gates 和 live shadow consistency 全部满足。

原因：

- 默认 archive 当前 `prior_stress_detail_rows=94`、`prior_stress_capacity_hits=107`，不是小噪声。
- activity cohort 当前 `prior_stress_detail_rows=0`，说明该 gate 能区分缺表活动样本和普通 archive capacity drift。

## D-v3-061：live `model_eval` 必须保留 `v3_fv_*` source/target/prior 明细

2026-06-06 起，live 局后 `model_eval` 的 `v3_fv_*` 字段必须和 archive evaluator 保持同一复盘口径。当前决策：

- live `model_eval` 必须输出 total/q6 count、cells、value 的 source、target、prior expected、target/prior ratio。
- 这些字段只用于 shadow audit、readiness、holdout 和局后复盘，不进入 UI 主建议或正式出价。
- 如果后续新增 formal/value sampler detail 字段，archive CSV 和 live `model_eval` 必须同步更新测试。

原因：

- prior/capacity/table drift 很可能先在 live 实战样本中出现；如果 live 缺少 source/target/prior 字段，后续复盘会和 archive readiness 分母不一致。

## D-v3-062：prior-stress cells/capacity 审计优先查 prior/capacity 与 evidence absorption，不先削弱 hard/floor evidence

2026-06-06 target-vs-truth delta 聚合后，当前决策：

- 在当前 archive 证据下，不应把 prior-stressed cells/capacity 问题优先解释为 hard/floor evidence 过强。
- 后续优先审计：
  - prior table 的 items-per-session min/max；
  - map/profile capacity prior；
  - drop prior expected cells/count；
  - posterior 是否充分吸收 exact/floor evidence。
- 只有出现 target 高于 settlement truth 的稳定分片时，才讨论削弱对应 evidence compiler 或 floor rule。
- formal/value sampler 仍不得吸收这类 cells/capacity drift；它只处理 value-floor stress 的 shadow candidate。

原因：

- 当前 prior-stress cells target 聚合 `above=0`，total cells 为 `below=50/match=44/above=0`，q6 cells 为 `below=46/match=13/above=0`。

## D-v3-063：posterior-vs-target absorption 保留为审计指标，但不作为当前首要修复方向

2026-06-06 posterior-vs-target delta 聚合后，当前决策：

- `scripts/summarize_v3_prior_robustness_audit.py`、readiness 与后续 live/archive 复盘继续保留 posterior-vs-target absorption 指标。
- 在当前 archive 证据下，不把 prior-stressed cells/capacity blocker 首先解释为 posterior 没有吸收 compiled target。
- 后续优先审计：
  - prior/capacity table 的 item count max 与 cells max；
  - map/profile-specific capacity prior；
  - drop-prior 覆盖不足；
  - compiled target 是否只是 settlement truth 的下界。
- 只有出现 posterior p50/p90 稳定低于 compiled target 的分片，才把 evidence absorption 升级为首要修复项。
- formal/value sampler 继续保持 shadow-only；不得用 value-floor candidate 或 capacity/cells watch 绕过该 blocker。

原因：

- 当前 archive prior-stressed rows=94，但 `post50_target_delta_total_cells=below=0/match=54/above=40`。
- q6 cells 同样没有 posterior p50 低于 target 的聚合信号：`below=0/match=2/above=57`。
- 结合 target-vs-truth 的 `above=0`，更可能的问题是旧 prior/capacity/table 漂移或 target completeness，而不是 posterior 未吸收已经编译出的 target。

## D-v3-064：capacity prior-max gap 必须作为 archive/live/readiness 共同复盘口径

2026-06-06 起，当前决策：

- archive evaluator、live `model_eval` 与 prior-stress readiness 必须保留同名 `v3_capacity_*` / `capacity_count_summary` 字段。
- `prior_stress_capacity_table_drift` gate blocked 时，必须能看到：
  - total count source；
  - compiled target count；
  - settlement truth item count；
  - prior items-per-session min/max；
  - target/truth 相对 prior max 的 delta、ratio 与 flags。
- target/truth 高于 prior max 的行优先进入 table/capacity/prior max 审计，不进入 formal/value sampler promotion 分母。
- target 低于 truth 但 truth 高于 prior max 的行，视为 target completeness 或旧表 capacity drift 问题；不得用 sampler 的 value-floor candidate 隐式吸收。
- 只有当 map/profile capacity gap 已解释并通过 readiness/holdout/live shadow 验证后，才重新讨论 v3 formal promotion 与 v2 归档。

原因：

- 当前 archive `truth_count_above_prior_max=68`、`target_count_above_prior_max=39`，且 `capacity_target_truth_counts above=0`。
- readiness 仍为 `overall_status=not_ready`，`prior_stress_capacity_table_drift` 仍为 blocked。
- live `model_eval` 如果不输出同名 capacity gap 字段，实战样本会与 archive/readiness 分母不一致。

## D-v3-065：capacity cases 是 blocker 分流标准，不是 sampler promotion 信号

2026-06-06 起，当前决策：

- `v3_capacity_cases` / `capacity_count_summary.case_counts` 必须保留在 archive/live/readiness 复盘中。
- `direct_prior_max_conflict` 优先进入 BidMap/DropTable/session capacity 口径审计；不得进入 formal/value sampler、under/tail 或 CCV promotion 分母。
- `target_lower_bound_truth_above_prior` 优先进入 target completeness 与 capacity prior 覆盖审计；不得解释为 evidence overconstraint。
- `target_above_prior_but_below_truth` 说明 compiled target 虽超过 prior max，但仍低于 truth；它是 capacity drift 与 target lower-bound 的混合 case。
- 只有 `target_over_truth_capacity_risk` 出现稳定分片时，才讨论削弱 total-count evidence 或相关 floor/exact compiler。
- readiness 在 capacity cases 未解释前继续 blocked；v3 promotion 与 v2 archive 保持 pending。

原因：

- 当前 archive `capacity_cases=target_lower_bound_truth_above_prior:31,direct_prior_max_conflict:29,...`。
- `map_id=2601` 为 `direct_prior_max_conflict:8/8`，是表容量审计入口。
- `map_id=2501` 同时有 direct conflict 与 lower-bound case，说明不能用单一 sampler 或单一全局修正处理。

## D-v3-066：table possible-max 冲突解释前，不调整 sampler 或推进 promotion

2026-06-06 起，当前决策：

- `summarize_v3_capacity_table_audit.py` 是 prior-stress capacity/table blocker 的专用审计入口。
- 当 `status=table_possible_max_below_truth` 时，必须优先确认：
  - BidMap col[16] 的 `items_per_session_min/max` 是否真代表最终 item count；
  - DropEntry `n_min/n_max` 是否已完整表达多件掉落；
  - Fatbeans settlement inventory truth 是否包含本局以外或重复口径；
  - raw table 版本是否与 archive 样本版本一致。
- 在这些问题解释前，不得通过提高 posterior、formal/value sampler、under/tail、CCV 或 calibration 来绕过该 blocker。
- 不直接把 BidMap max 改大或在 sampler 中放宽 capacity；任何表/采样语义变更必须先 shadow-only，并通过 archive/activity/readiness/live 验证。
- v3 promotion 与 v2 archive 保持 pending。

原因：

- `2601` direct conflict rows 8/8 均为 `table_possible_max_below_truth`，truth count max=65，而 current sampler possible max=44。
- top direct/lower-bound groups 的 `sampler_max_count_per_draw=1`、`sampler_nmax_gt1=0`，不是 DropEntry 多件数导致。
- 该问题处在 table/sampler/truth 口径边界，比普通 posterior error 或 formal value low-bias 更基础。

## D-v3-067：raw inventory verified 后，capacity blocker 不再优先按 parser 重复处理

2026-06-06 起，当前决策：

- `summarize_v3_capacity_table_audit.py` 必须保留 raw inventory diagnostics，作为 capacity/table blocker 的固定证据：
  - latest settlement inventory state count；
  - latest item/cell count；
  - archive detail truth 与 latest inventory count 对齐；
  - runtime id 与 `(runtime_id,item_id)` duplicate count；
  - item id duplicate count 只作为同款多件信号，不单独视为 parser 重复。
- 对 `raw_inventory=verified_latest_inventory` 且 `raw_dup_pair=0` 的 group，不再优先按 Fatbeans parser 重复修复处理。
- 对这些 group，下一步必须优先验证：
  - BidMap `items_per_session_min/max` 是否是最终 item count 上限；
  - DropEntry `n_min/n_max` 是否表达一次抽中后的件数，还是另有表字段/版本控制；
  - current raw table 是否与 archive sample 采集版本一致；
  - settlement inventory 是否存在游戏内“额外生成/结算展开”语义。
- 在 raw inventory 已验证且 table semantics 未解释前，不得放宽 sampler capacity、调整 posterior/formal/value sampler，或推进 v3 promotion。

原因：

- `2601` direct conflict：`raw_files=4`、`raw_states=max=1`、`raw_truth_match_rows=8/8`、`raw_dup_runtime=max=0`、`raw_dup_pair=max=0`，但 truth count max 仍为 65，超过 sampler possible max 44。
- lower-bound top groups `2508/2504/2405` 同样是 `verified_latest_inventory` 且 detail truth 与 latest inventory 全匹配。
- parser 重复不是当前主解释；promotion blocker 继续归属于 capacity table/session/drop semantics。
