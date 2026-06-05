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
