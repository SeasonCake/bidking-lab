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
  - BidMap drop-ref（current v300 `col[17]`，historical `col[16]`）的 `items_per_session_min/max` 是否真代表最终 item count；
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

## D-v3-068：current v300 BidMap drop-ref 与 activity extras 不能单独解除 capacity blocker

2026-06-06 起，当前决策：

- capacity/table audit 必须按 current raw `fileVersion=300` / 23-column BidMap schema 解释：
  - current `col[17]` 是 `drop_ref=[9999,drop_pool_id,items_min,items_max]`；
  - current `col[16]` 是空占位，不再作为当前表的 drop-ref 文档口径；
  - current `col[14]` 作为 round-cap candidate 记录，但不得直接提升为 sampler/promotion 上限。
- 对 prior-stressed capacity groups，reachable Drop universe 缺口必须分流 known temporary blue zodiac activity ids 与 non-zodiac missing items。
- 如果 `raw_non_zodiac_missing=0`，不得把 blocker 首先解释为当前 Drop 表缺 item；应继续查 settlement activity/extra generation、session capacity field semantics 与 archive/table version timing。
- `drop_ref.items_max` 继续作为 current sampler possible max 的来源，但在真实 settlement inventory count 已超过该 max 的 slices 中，不得视为最终 settlement item-count cap。
- 在解释 `drop_ref`、`col[14]`、activity extras 与 settlement inventory 展开关系前，不调整 formal/value sampler 参数，不放宽 sampler capacity，不推进 v3 promotion 或 v2 archive。

原因：

- 当前 raw `data/raw/fileVersion=300`、`data/raw/tables/fileVersion=300`，`BidMap.txt` 125 行全部为 23 列。
- 2601/2501/2508 等 prior-stressed rows 当前解析为 `drop_ref_col=17`，不是旧 `col[16]`。
- 2601 `drop_ref.items_max=44`，`col[14] round_cap=60`，但 raw latest settlement truth 仍可到 65。
- audited missing-from-drop item ids 全部是 known temporary blue zodiac ids `1306003..1306014`，`raw_non_zodiac_missing=max=0`；这说明 item universe gap 是活动额外项信号，但不足以解除 count-cap 冲突。

## D-v3-069：zodiac extras 与本地 table timing 线索不足以解除 capacity blocker

2026-06-06 起，当前决策：

- `raw_known_temp_zodiac_count` 只能解释 reachable Drop universe 的 activity item-id 缺口，不得直接解释为 item-count cap 放宽。
- capacity/table audit 必须继续保留扣除 zodiac 后的 residual gap：
  - `raw_drop_ref_excess_after_temp_zodiac_count`；
  - `raw_round_cap_excess_after_temp_zodiac_count`。
- 如果扣除 zodiac 后 residual gap 仍大于 0，继续把该 slice 归入 settlement expansion/session capacity/table semantics blocker，不进入 formal/value sampler promotion 分母。
- `summarize_v3_archive_table_timing.py` 用于记录 raw `fileVersion`、filelist BidMap/Drop entries、table file metadata 与 capture time range，但 capture JSON 没有 table version/hash 字段时，只能作为弱时序线索，不能单独证明 archive 与 raw table version 完全一致。
- 在拿到更强 table-version 证据或 settlement extra-generation 机制前，不调整 sampler capacity、不恢复 formal/value sampler tuning、不推进 v3 promotion/v2 archive。

原因：

- 默认 441-session archive：超过 `drop_ref.items_max` 的 sessions 为 196；扣除 zodiac 后仍有 172。超过 `round_caps_candidate` 的 sessions 为 81；扣除 zodiac 后仍有 59。
- `direct_prior_max_conflict` top groups 扣除 zodiac 后仍超 cap：2601 `raw_drop_excess_after_temp=max=20`、`raw_round_excess_after_temp=max=4`；2501 分别为 13/7；2506 分别为 13/7。
- `target_lower_bound_truth_above_prior` top groups 同样仍超 cap：2508 分别为 14/8；2504 分别为 17/11；2405 分别为 18/8。
- timing audit 显示 current raw `fileVersion=300`、filelist 包含当前 BidMap/Drop entries，默认 archive capture time 为 2026-05-27 到 2026-06-05，activity cohort 为 2026-06-05；但 capture JSON 中没有 version/hash 字段。

## D-v3-070：0x002D field[4] 证明 final inventory 是 slot occupancy，不提供 base/activity source split

2026-06-06 起，当前决策：

- `summarize_v3_settlement_payload_audit.py` 作为 0x002D settlement raw payload 的专用审计入口。
- 当前把 0x002D payload `field[4]` 视为 final settlement grid/slot block：
  - top-level `field[3]` 是 slot-like records；
  - occupied slots/raw item candidates 与 parser inventory item count 应大体一致；
  - raw duplicate `(runtime_id,item_id)` 只作为 parser/dedup 异常诊断，不作为 capacity 放宽信号。
- 该 payload 证明 archive truth 是最终 occupied settlement slots，但尚未提供 base Drop、temporary activity item 或额外生成机制的 source split。
- 因此，不得把 0x002D slot_count 直接改成 sampler count cap，也不得把 full observed action（如 `100100`/`100134`）当成独立生成来源；它们目前只是最终 inventory 的镜像或阅读结果。
- 下一步若要修 capacity prior，必须继续 shadow-only：要么找到 server generation/source 字段，要么把 session-count prior 从 raw settlement occupancy 做分 cohort 校准，并通过 archive/activity/live/readiness 验证。

原因：

- 默认 441-session archive：`raw_candidate_match_rows=439`、`occupied_slot_match_rows=439`，slot counts 主要为 `300:251,250:186`；activity cohort 15/15 完全匹配且 slot count 全为 300。
- 2601：22/22 raw candidates 与 parsed inventory 匹配，slot count 全为 300，inventory count max=65。
- 2501：86/87 匹配，唯一差异是 duplicate raw candidate pair 造成的 dedup delta=1，不是 prior-stressed top conflict 的主因。
- full observed actions 只出现在少数 rows（默认 18/441），不能解释全局 count-cap gap。

## D-v3-071：settlement occupancy count prior 只能 shadow-only 且必须 cohort-gated

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 作为 settlement occupancy count prior 的候选审计入口，只读 archive/activity final inventory 与 0x002D payload。
- 该脚本输出的 observed count 分布、p50/p90/p95/max、temporary zodiac residual 与 table-cap excess 只能用于 shadow-only 候选和 readiness 证据，不得直接写入 live/formal sampler cap。
- 24xx/25xx/2601 default archive 分片可作为 current-table cohort 的 count-prior 候选来源，但必须继续标记 `observed_exceeds_table_caps_shadow_only`，直到 table/session capacity 语义解释清楚并通过 holdout/live/readiness。
- 252x activity 分片当前全部是 `missing_bidmap`，必须作为 activity/missing-table cohort 单独处理；不得把 252x settlement count 直接并入 250x BidMap prior，也不得用它推导 current v300 BidMap cap。
- 如果后续找不到更强 server source split 字段，允许基于 settlement occupancy count 设计 shadow-only formal/value sampler，但 promotion 前必须同时通过 archive、activity、live shadow、readiness 与 holdout 验证。
- v3 promotion 与 v2 archive 继续 pending；不得因 count-prior 候选存在而降低 `prior_stress_capacity_table_drift` gate。

原因：

- 默认 441-session archive：`inventory_count max=66`、`non_temp_count max=64`，扣除 temporary zodiac 后仍有 `above_drop_after_temp=172`、`above_round_after_temp=59`。
- prefix 聚合显示 default current-table cohort 仍大面积超 cap：250 为 94/217、240 为 56/169、260 为 11/22。
- activity cohort 15/15 为 `missing_bidmap`，map_prefix3=252，slot_count 全 300，inventory_count max=67，不能与 current 250x table cap 混用。
- payload mismatch 仅 2/441，不支持把 observed count prior 问题重新归因于 parser/payload 重复。

## D-v3-072：v3_scp 是可观测 shadow evidence，不是 sampler cap 或 promotion bypass

2026-06-06 起，当前决策：

- `v3_scp_*` 字段族表示 settlement occupancy count-prior shadow evidence，来源为 `data/processed/v3_settlement_count_prior_shadow.json`。
- `SettlementCountPriorEntry` 只允许 exact `map_id` 与 `map_prefix3` 匹配；禁止按 `map_family` fallback 混用 250x 与 252x activity cohort。
- `v3_scp_active` 必须保持 `False`，`v3_scp_affects_bid` 必须保持 `False`；任何 active 或 affects-bid 行都应视为 regression。
- `settlement_count_prior_shadow` readiness gate 只能证明 evidence 可见且 inactive；不得把该 gate 的 `watch` 解释为 capacity blocker 解除。
- `v3_scp_candidate=True` 表示 observed settlement count 超过 current table caps 的 shadow 候选，不得直接改写 `drop_ref.items_max`、posterior sampler count cap、formal/value sampler 或正式出价。
- 252x activity rows 必须继续以 `missing_table_shadow_only` 分流；在补齐活动表项或 mapping 前，不进入 default archive count prior 或 formal promotion 分母。

原因：

- default archive evaluator：`v3_scp_candidate_rows=1488/1560`、`v3_scp_active_rows=0`。
- activity evaluator：`v3_scp_missing_table_rows=58/58`、`v3_scp_active_rows=0`、`posterior_ready=0`。
- readiness：`settlement_count_prior_shadow=watch`，但 `prior_stress_capacity_table_drift=blocked`、`formal_value_sampler_holdout=blocked`、overall 仍 `not_ready`。
- 这说明 settlement count-prior evidence 已可供 archive/live/readiness 共同审计，但还不是 promotion 证据或 sampler 参数。

## D-v3-073：settlement count-prior 必须先过 session holdout，prefix 聚合不能替代表语义

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_holdout.py` 是 `v3_scp_*` 用作后续 shadow-only formal/value sampler count-prior 输入前的必跑审计之一。
- holdout 只比较 shadow evidence 的泛化性：current `BidMap.items_per_session_max`、raw round-cap candidate、同 group train p95/max 与 validation settlement truth 的 coverage；它不修改 sampler cap。
- `map_id` 口径保留为首要审计口径；样本不足的 exact-map group 继续标记 `blocked_low_sample`，不得用少量 session 推 sampler 参数。
- `map_prefix3` 聚合可以作为 sample-depth/泛化性补充证据，但不能替代 BidMap 表版本、字段语义或 activity mapping 解释；尤其不能把 252x activity fallback 到 250x default prior。
- 只要 252x activity 仍是 `missing_bidmap`，它就只能作为 missing-table/activity cohort shadow evidence；不进入 default archive count prior、formal/value sampler promotion 或 v2 archive 分母。
- readiness 中 `settlement_count_prior_shadow=watch` 继续只代表 evidence 可见且 inactive；`prior_stress_capacity_table_drift` 和 `formal_value_sampler_holdout` blocker 不得因此降级。

原因：

- default `map_id` holdout：441 settlement sessions，21 groups，`candidate_rows=389`，`sample_limited_rows=52`，`prior_coverage=0.609977`，`round_coverage=0.866213`，`holdout_p95_coverage=0.907455`，status 为 `watch_settlement_count_prior_candidate=14`、`blocked_low_sample=7`。
- default `map_prefix3` holdout：441 sessions，5 groups，`candidate_rows=441`，`sample_limited_rows=0`，`holdout_p95_coverage=0.945578`，但这只是跨 exact-map 的聚合 evidence。
- activity 252x holdout：15 sessions，`missing_table_rows=15`；`map_prefix3=252` 的 p95 holdout coverage 虽为 `0.933333`，但 table/mapping 仍缺失。
- focused parser/archive/live/readiness/formal-value tests 74 passed；readiness 仍为 `overall_status=not_ready`。

## D-v3-074：v3_scp 到 formal/value sampler 必须先建立 count->cells/value bridge

2026-06-06 起，当前决策：

- `summarize_v3_scp_formal_value_link.py` 是 `v3_scp_*` 与 formal/value sampler 之间的 archive 关联审计入口。
- `v3_scp_candidate=True` 只能表示 settlement count-prior shadow evidence；不得直接等价为 `value_floor_stress`、formal/value sampler candidate 或 count cap promotion。
- formal/value sampler 设计前必须先证明 count-prior evidence 如何映射到 cells/value：至少要区分 `scp + value_floor`、`scp + capacity_only`、`scp + no formal stress` 与 `missing_table`。
- readiness 新增 `settlement_count_formal_value_link` gate；该 gate blocked 时，不得恢复 formal/value sampler tuning，也不得讨论 v3 promotion/v2 archive。
- 252x activity rows 在 no posterior/formal metric 情况下仍只计入 missing-table evidence，不进入 formal MAE/p90 分母。
- 当前 `v3_fv_active=False`、`v3_fv_affects_bid=False`、`v3_scp_active=False`、`v3_scp_affects_bid=False` 必须保持；任何 active/affects-bid 都是 regression。

原因：

- default archive：`v3_scp_candidate_formal_rows=1488`，但 `scp_candidate_value_floor_rows=8`，`scp_candidate_capacity_watch_rows=124`，当前 `v3_fv_delta_p50_mae=0.0`。
- 按 `v3_fv_stress_class` 看，`value_floor_stress` 只有 12 rows，其中 7 rows 与 `v3_scp_candidate` 重叠；capacity watch overlap 明显更大。
- 按 `map_id` 看，2401/2402/2501 有少量 `scp + value_floor` overlap；2506/2601 等 prior-stressed group 主要是 `scp + capacity_only`，formal baseline 仍偏弱。
- readiness 新 gate `settlement_count_formal_value_link=blocked`，`overall_status=not_ready`，blocked gates 增至 11。

## D-v3-075：count->cells/value bridge 是 archive 候选，不是 sampler 参数

2026-06-06 起，当前决策：

- `summarize_v3_scp_count_value_bridge.py` 是 settlement count-prior 到 cells/value 的 archive-only bridge 审计入口。
- 该脚本只量化 `scp_p95 > target_count`、total cells p90 undercoverage、formal value p90 undercoverage 的交集；不得把 `truth_cells_per_item` 或 `truth_formal_per_item` 直接写入 sampler。
- `settlement_count_cells_value_bridge` readiness gate 只说明 bridge candidate 可见；它的 `watch` 不代表 promotion-ready。
- 在进入 formal/value sampler 前，必须新增 session-level holdout 或 shadow sampler，验证 count->cells/value bridge 不造成 formal MAE、below-rate、p90 coverage、over-rate regression。
- `v3_scp + v3_fv_stress_class=none` 出现 bridge candidates 时，只能视为“当前 value stress 检测漏掉了 count/cells/value 桥信号”的审计线索，不能直接启用 value floor。
- activity 252x 继续 missing-table/no-posterior 分流；没有 formal metric rows 时不得参与 bridge 校准。

原因：

- default archive bridge 审计：`scp_candidate_metric_rows=1488`、`scp_p95_above_target_rows=1276`、`cells_p90_under_rows=635`、`formal_p90_under_rows=389`、`count_cells_value_bridge_rows=201`。
- `v3_fv_stress_class=none` 下仍有 `count_cells_value_bridge_rows=185`，说明 bridge signal 与现有 formal/value stress class 不一致。
- high-priority groups 中 2501/2401/2601/2506 分别有 `count_cells_value_bridge_rows=54/29/26/19`；2601、2506 仍是 prior-stressed/capacity-heavy slices。
- readiness：`settlement_count_cells_value_bridge=watch`，但 `settlement_count_formal_value_link=blocked`、`formal_value_sampler_holdout=blocked`、overall 仍 `not_ready`。

## D-v3-076：naive count->cells/value bridge floor 未通过 holdout

2026-06-06 起，当前决策：

- `summarize_v3_scp_count_value_bridge_holdout.py` 是 settlement count-prior bridge 进入 formal/value sampler 前的必跑 session holdout。
- 当前 naive bridge floor 口径为：同 group 训练折估计 truth cells/formal value per item，验证折在 `scp_p95 > target_count` 时将 `scp_p95 * train_ratio` 作为 shadow floor。
- 该口径只能用于 falsify/guard，不得写入 posterior sampler、formal/value sampler 或正式出价。
- 因 holdout 显示 formal p50 MAE 与 over-rate 风险显著上升，当前 count->cells/value bridge 不得 promotion，也不得作为 `v3_fv` active path。
- 后续若继续设计 shadow-only sampler，必须先加更强 guard：例如只在 bounded under slices、低 over-risk groups、tail/underestimate guard 通过、或更低 quantile/value cap 下测试。
- readiness 新增 `settlement_count_cells_value_bridge_holdout` gate；该 gate blocked 时，v3 promotion/v2 archive 继续 pending。

原因：

- default `ratio_source=all` holdout：`candidate_rows=1276`、`applied_rows=1173`、`candidate_delta_mae=+50956.632`、`candidate_delta_p90=+0.219096`、`candidate_over=0.712702`、overall `blocked_holdout_hurt`。
- strict `ratio_source=bridge` holdout：`candidate_rows=1276`、`applied_rows=1120`、`candidate_delta_mae=+53663.766`、`candidate_delta_p90=+0.225`、`candidate_over=0.708036`、overall `blocked_holdout_hurt`。
- 2506 是少数 MAE 改善 slice（`delta_mae=-30309.955` in all-source），但 `bridge_over=0.647887` 仍超过当前 over-risk guard。
- readiness：`settlement_count_cells_value_bridge_holdout=blocked`，`scp_bridge_holdout_delta=+50956.632`，`scp_bridge_holdout_over=0.712702`，overall 仍 `not_ready`。

## D-v3-077：formal lift cap 只能作为 bridge holdout guard probe

2026-06-06 起，当前决策：

- `summarize_v3_scp_count_value_bridge_holdout.py --formal-lift-cap` 只限制 audit holdout 中 shadow formal value floor 相对 baseline 的抬升幅度。
- `--floor-mode extra` 只用于验证“只补 scp count gap 增量”的假设；它不是 sampler policy。
- 上述参数不得进入 evaluator default、posterior sampler、formal/value sampler active path、live monitor active path 或正式出价。
- readiness 默认继续使用 uncapped total-floor holdout；`settlement_count_cells_value_bridge_holdout=blocked` 不得因 capped probe 的局部改善降级。
- capped probe 可作为后续 guard 设计输入，但在 applied hurt groups 未消失前，不能作为 promotion readiness 或 v2 archive evidence。
- 下一步优先回到 table/capacity 语义审计：解释 `BidMap` capacity、`DropEntry n_min/n_max` 与 settlement inventory item-count 上限冲突，再恢复 shadow-only formal/value sampler 设计。

原因：

- `formal_lift_cap=5000` 把 candidate MAE delta 从 uncapped `+50956.632` 降到 `-288.656`，但 overall 仍 `blocked_holdout_hurt`，applied hurt groups 仍包含 `2507,2407,2409`。
- `formal_lift_cap=25000` 与 `50000` 虽仍为负 MAE delta，但 over-rate 升至 `0.522592`/`0.541347`，且 hurt groups 增加。
- `floor_mode=extra` uncapped 明显恶化：`candidate_delta_mae=+344324.441`、`candidate_over=0.873459`。
- `floor_mode=extra --formal-lift-cap=5000` 与 `ratio_source=bridge --formal-lift-cap=5000` 仍 blocked，说明简单 cap 或训练分母调整不能解决 capacity/table 语义 blocker。

## D-v3-078：BidMap drop-ref max 不能再视为 final settlement inventory 硬上限

2026-06-06 起，当前决策：

- current raw v300 `BidMap` 的 drop-ref 仍按 `col[17]=[9999,drop_pool_id,items_per_session_min,items_per_session_max]` 解析；`col[16]` 是空占位，不参与 current drop-ref。
- `DropEntry n_min/n_max` 在当前 sampler 中仍表示 leaf entry 被抽中后的单次数量范围；direct conflict maps 的 flattened leaf `n_max` 全为 1。
- 因 raw 0x002D settlement inventory 已验证 final occupied slot count 可超过 `items_per_session_max`，`items_per_session_max` 不得继续被解释为 final settlement inventory 的硬上限。
- 在 v3 审计中继续称它为 `prior_items_per_session_max` / sampler prior max，而不是 true inventory capacity。
- 这不代表可以直接放开 formal/value sampler：在额外生成/展开机制或活动机制解释前，`prior_stress_capacity_table_drift`、`settlement_count_cells_value_bridge_holdout` 和 v3 promotion blocker 继续保持。
- 下一步应基于 settlement occupancy count prior 与 slot-capacity evidence 设计 shadow-only count/cells/value guard，而不是调正式出价或把 `items_per_session_max` 当 hard cap 修正。

原因：

- direct conflict archive rows：`raw_candidate_delta=0`、`raw_occupied_delta=0`、`raw_truth_match_rows` 全匹配，排除了 parser 把工具镜像重复计入的主因。
- top conflict maps 的 `raw_slots` 为 250 或 300，`raw_slot_headroom` 仍很大；final inventory count 超过 drop-ref max 但远低于 settlement slot capacity。
- 2601/2501/2506 等 map 的 `raw_col16="[[]]"`、`raw_col17="[9999,map_id,min,max]"`、`sampler_leaf_nmax=max=1`，说明当前 raw table 与 sampler 解释一致，但该解释不是 final inventory hard cap。
- 252x activity 仍是 `missing_bidmap`，不能用 250x default table 代替。

## D-v3-079：nested train-only guarded bridge 仅作为 2506 shadow watch candidate

2026-06-06 起，当前决策：

- `summarize_v3_scp_guarded_bridge_holdout.py` 是 count->cells/value bridge 的独立 nested holdout：outer session folds 只用于最终验证，group 是否可用必须由 outer-train 内的 inner crossfit 决定。
- 当前 guard 要求 inner aggregate 与各 inner fold 均通过、每折有最低 applied session、且 train formal p50 over-rate increase 不得大于 0；readiness probe 使用 `formal_lift_cap=10000`。
- 该 guard 只产生 shadow/readiness evidence，不得进入 evaluator default、posterior/formal sampler active path、live decision 或正式出价。
- 原始 uncapped bridge gate 继续保持 blocked；guarded bridge 的 watch 不能替代 `settlement_count_cells_value_bridge_holdout`、`formal_value_sampler_holdout` 或 prior-stress blocker。
- 当前仅把 2506 视为可继续采样的 shadow candidate。256 posterior trials 下 seeds 0/1/7 均只选择 2506，但每个 seed 的 outer holdout applied rows 只有 9，仍是 sample-limited。
- 64 posterior trials 下 seed 1 会误选并伤害 2501，证明低 trial/seed 稳定性不足；在更多 live/archive support 与多 seed holdout 前不得 promotion。
- activity 252x 仍无可评估 metric rows，继续作为 missing-table cohort，不进入 guarded bridge promotion 分母。

原因：

- aggregate-only train guard 会放行 2401/2502 等 hurt groups；只加 all-inner-fold 稳定性仍会放行 2504/2405。
- all-inner-fold + zero train over-increase + 10000 lift cap 在 64-trial seed 0 下只选择 2506，`applied_rows=20`、`delta_formal_p50_mae=-6000.0`、无 hurt group，但不同 seed 不稳定。
- 256-trial seeds 0/1/7 均只选择 2506，`applied_rows=9`，MAE delta 分别为 `-4602.026/-5555.556/-3333.333`，无 hurt group。
- readiness 仍为 `overall_status=not_ready`、`blocked_gates=12`；新增 guarded gate 只为 `watch` 信息，不减少 blocker。

## D-v3-080：guarded bridge 必须通过 trial/seed stability 矩阵，不得用单 seed watch 代替

2026-06-06 起，当前决策：

- `summarize_v3_scp_guarded_bridge_stability.py` 是 guarded bridge promotion 前的显式 trial/seed stability 审计入口。
- 默认 smoke 使用 `64 trials x seeds 0/1`，用于快速 falsify seed stability；它不是 promotion evidence。
- promotion 前必须运行更高 trial 的多 seed 矩阵，例如 `256 trials x seeds 0/1/7`，并同时满足：
  - 每个 run 都是 `watch`；
  - selected group 精确保持为 2506；
  - 无 applied hurt group；
  - outer holdout applied support 达到最低样本门槛。
- readiness 的 `settlement_count_guarded_bridge_holdout=watch` 只代表单 seed 可见候选；不得替代 stability 矩阵。
- stability 矩阵使用 `.tmp/codex/v3_scp_guarded_bridge_stability` 保存 per-run cache，便于长跑断点复用；该 cache 是本地临时证据，不提交。
- 在 64-trial seed 1 仍会误选 2501 的情况下，guarded bridge 不能进入 active sampler、live decision 或正式出价。

原因：

- 默认 stability smoke 复现：seed 0 只选 2506 且 watch，seed 1 选择 `2501,2506` 且 2501 applied hurt。
- 单 seed readiness 当前只覆盖 seed 0；它不能证明 posterior seed 稳定。
- 256-trial 多 seed 的历史单跑证据方向较好，但本轮三 seed 矩阵首次运行超过 300 秒；必须依赖 cache/长跑完成矩阵化复核后才能作为 promotion 证据。

## D-v3-081：2506 guarded bridge 已 seed-stable 但因 support depth 继续 blocked

2026-06-06 起，当前决策：

- `256 trials x seeds 0/1/7` guarded bridge stability matrix 是当前 2506 候选的主证据入口。
- 当前三 seed 均为 `watch`、selected group 精确为 `2506`、无 applied hurt，说明 64-trial seed drift 已被高 trial 配置压下。
- 但每个 seed 的 outer holdout `applied_rows=9`，低于当前 `min_applied_rows=20` 门槛；因此 overall 必须保持 `blocked_low_support`。
- 该结果只能支持继续收集 2506 archive/live shadow evidence，不得进入 active sampler、live decision、正式出价或 v2 archive。
- 下一步必须补足 2506 support 后复跑同一 stability matrix；不得用低样本三 seed watch 直接设计 promotion policy。

原因：

- stability matrix 输出：`runs=3`、`watch_runs=3`、`stable_groups=2506`、`union_groups=2506`、`signatures=2506:2=3`。
- seed 0/1/7 的 `delta_mae` 分别为 `-4602.026/-5555.556/-3333.333`，`bridge_over=0.222222/0.222222/0.333333`，`applied_hurts=-`。
- `min_applied=9` 小于 `min_required=20`，promotion evidence 仍 sample-limited。

## D-v3-082：252x activity mapping likelihood 只作为语义线索，不进入 default prior

2026-06-06 起，当前决策：

- `summarize_v3_activity_mapping_likelihood.py` 是 252x missing-table 的 audit-only candidate mapping 审计入口。
- 该脚本只比较真实 252x settlement inventory 在候选映射下的 quality likelihood，例如 `252x->251x` 与 `252x->250x`。
- 当前结果支持 `252x->251x` 更像 activity/up table，但不能证明服务端正式映射；尤其 item universe 在 250x/251x 下均覆盖 100%，质量分布证据不足以单独定表。
- 在缺少 `2521+` raw BidMap/Drop 或服务端 activity overlay 强字段前，252x 不得 fallback 到 250x default，也不得进入 default archive prior、formal/value sampler promotion 分母或正式出价。
- 该审计可用于后续 table/activity 语义收口和 synthetic mechanism hypothesis 验证，但合成/likelihood 证据不能替代 archive/live holdout。

原因：

- 当前 raw v300 有 `2511-2520` 与 `2520->2150` 链，但无 `2521+` BidMap/Drop 顶层池。
- activity 15 rows 对照：`minus10` winner 11/15，`minus20` winner 4/15；两边 candidate 均 `ok` 且 missing item rate 为 0。
- `minus10` 平均 log likelihood per item 为 `-1.676415`，`minus20` 为 `-1.691183`，方向性存在但 margin 较小。

## D-v3-083：2506 support blocker 来自 selected outer folds，不是本地漏样本

2026-06-06 起，当前决策：

- 2506 guarded bridge high-trial blocker 继续解释为 selected outer holdout support depth，不解释为 parser 漏样本或 default archive 缺少 2506。
- 当前 default archive 有 21 个 2506 canonical sessions、71 个 metric rows、59 个 bridge candidate rows、20 个 count/cells/value bridge rows。
- high-trial guard 只在 outer folds 0 和 4 选择 2506，因此实际 applied rows 只有 `3 + 6 = 9`。
- 本地没有可直接纳入 default archive 的新增 2506 support；`data/logs/live/raw` 中 2506 是 canonical session 的重复/reset/complete 副本。
- `data/samples/fatbeans_invalid/parse_error/fatbeans_invalid_parse_error_aisha_shipwreck_test_sample60_5rounds_7fc668a5b9_0438.json` 只能列为人工审查候选，不得直接纳入 promotion support。
- 后续必须采集新的真实 complete 2506 sessions，再复跑 manifest、bridge summary 和 `256 trials x seeds 0/1/7` stability matrix。

原因：

- 2506 fold 分布：fold0 `sessions=1/bridge_candidates=3/selected=yes`，fold1 `8/23/no`，fold2 `5/16/no`，fold3 `4/11/no`，fold4 `3/6/yes`。
- support 门槛当前为 `min_applied_rows=20`；现有 selected-fold support 只有 9，缺口至少 11 applied rows。
- invalid parse_error 样本当前 parser 可读且含 5 ready rows，但历史错误为 `SEND invalid frame length`，需先确认原始包完整性和 parser 行为变化。

## D-v3-084：252x exact item likelihood 不改变 missing-table 边界

2026-06-06 起，当前决策：

- `summarize_v3_activity_mapping_likelihood.py` 可同时输出 quality-level 与 exact item-level likelihood；`best_scheme` 继续保留 quality winner，`best_item_scheme` 只作为更细粒度审计线索。
- exact item likelihood 可以比较同一 item 在候选映射下的权重差异，但仍不能证明 `2521+` 服务端正式映射。
- 不增加 naive combined score；quality 是 item distribution 的边际，直接相加会双重计数。
- value/cell bucket likelihood 可作为后续解释性 projection diagnostic，但不能作为定表或 promotion evidence。
- 252x 继续保持 missing-table/activity cohort，不进入 default prior、formal/value sampler promotion 分母或正式出价。

原因：

- activity 15 rows：quality winners 与 item winners 均为 `minus10:11, minus20:4`。
- exact item log likelihood per item 仅小幅偏向 `minus10`：`-5.965943` vs `-5.981787`。
- 两个候选族的 missing item rate 与 zero item probability 都为 0；证据仍是权重偏好，不是 universe 区分。

## D-v3-085：readiness dependency lanes 只用于调度，不改变 promotion gate

2026-06-06 起，当前决策：

- `summarize_v3_promotion_readiness.py` 输出 `gate_dependencies`，把 gate 映射到推进 lane，便于多 agent 并行拆分 blocker。
- lane 只解释当前 gate 依赖，不参与 `status`、`blocked_gates`、`overall_status` 或 `next_actions` 判定。
- `pending` 的 `v2_archive_readiness` 在 dependency view 中仍算 blocker/pending lane，但不计入原有 `blocked_gates`。
- 2506 support、252x table/activity/capacity、formal/value shadow sampler、sampler safety/profile depth 必须继续分开推进；任一 lane 的 watch 都不能替代其它 lane 的 blocked evidence。
- 该输出不得作为 promotion evidence；promotion 仍必须依赖 archive/live/readiness/holdout/stability 的原 gate。

原因：

- 当前 readiness 已有 20 个 gate，`blocked_gates=12`，但 next action 混合了 table/activity、bridge support、formal sampler、CCV/tail/profile 等不同 blocker。
- 多 agent 并行时需要稳定的 gate->lane 映射，避免把 2506 support depth 当作 formal/value sampler 已可调参，或把 252x likelihood 当作 default prior 证据。
- 新字段只从既有 gate 派生，单测覆盖 blocked/pending lane、activity candidate focus 与 capacity drift focus。

## D-v3-086：2506 selected-fold support gap 必须由 guarded stability 输出复核

2026-06-06 起，当前决策：

- `summarize_v3_scp_guarded_bridge_holdout.py` 输出 `selected_group_fold_support` 与 `selected_group_support`，用于复核每个 selected outer fold 的 holdout sessions、metric rows、bridge candidate rows 与 applied rows。
- `summarize_v3_scp_guarded_bridge_stability.py` 输出 `selected_group_support_gap`，按 required applied rows 汇总多 seed/run 的最小 support 缺口。
- 这些字段只用于 support-depth 审计，不改变 guarded bridge 的 `overall_status`、selected group 判定、readiness gate 或 formal/live 行为。
- 64-trial seed 0 可显示 `2506` applied rows 达到 20，但 promotion 仍必须看 high-trial 多 seed matrix；当前 `256 trials x seeds 0/1/7` 仍是 `support_gap=11`。
- cached matrix 允许用旧 run summary fallback 计算 group-level gap；若要看 selected fold 的具体 sessions/metric/candidate 分布，必须重新跑 no-cache 或刷新对应 cache。

原因：

- 2506 blocker 的本质是 selected outer folds 的 support depth，而不是 default archive 完全缺 2506。
- 之前 fold 分布是手工记录，容易在多窗口/多 agent 推进时丢失；现在脚本能直接输出 `support_gap=2506:min_applied=9/required=20/gap=11`。
- 该改动把“采集 10-15 个真实 complete 2506 sessions 后复跑 stability matrix”的下一步变成可验证闭环。

## D-v3-087：prior-stress consistency bucket 是审计分流，不是 sampler 许可

2026-06-06 起，当前决策：

- `summarize_v3_prior_robustness_audit.py` 输出 `consistency_classes` 与互斥主类 `consistency_bucket`，用于分流 prior-stressed cells/capacity/evidence blocker。
- 当前 bucket 包含 `hard_capacity_conflict`、`lower_bound_under_truth`、`evidence_floor_only`、`target_over_truth_risk`、`no_capacity_prior_conflict`。
- `summarize_v3_promotion_readiness.py` 只展示 `consistency_bucket_counts` / `consistency_class_counts`，不改变 `prior_stress_capacity_table_drift` gate 判定。
- `hard_capacity_conflict`、`lower_bound_under_truth`、`evidence_floor_only` 都不能由 formal/value sampler 吸收；它们必须继续走 table/capacity/evidence 或 count->cells/value bridge 审计。
- formal/value sampler 仍只允许 shadow-only value-floor candidate；`v3_fv_active=False` / `v3_fv_affects_bid=False` 必须保持。

原因：

- 当前 `prior_stressed` 94 行并非同一种问题：有 target/truth 同时超过 prior max 的硬容量冲突，也有 truth 超 prior 但 target 只是低界，还有纯 floor evidence 不足。
- 64-trial readiness 复核显示 bucket 为 `hard_capacity_conflict=29`、`lower_bound_under_truth=39`、`evidence_floor_only=26`。
- 这些分类让后续 sampler 设计可以避开 capacity/cells drift，防止用 value floor 局部改善绕过 promotion blocker。

## D-v3-088：capacity table audit 必须按 consistency bucket 分流

2026-06-06 起，当前决策：

- `summarize_v3_capacity_table_audit.py` 支持 `--bucket`，按 `consistency_bucket` 过滤 prior-stress rows，并在每个 map group 输出 bucket/class counts。
- capacity table audit 输出 `bidmap_raw_col8` / `bidmap_v300_flag_a`，但该字段只作为表语义线索，不参与 sampler、readiness gate 或正式出价。
- 当前 94 个 prior-stressed rows 的 `v300_flag_a` 全为 `1`；因此 col[8] 不能解释本轮 hard/lower-bound capacity conflict。
- `hard_capacity_conflict` 和 `lower_bound_under_truth` 的真实 rows 必须继续解释为 table/session-capacity/settlement-source split blocker；不得用 formal/value sampler 调参吸收。
- `evidence_floor_only` 在 capacity table audit 中 table cap pass，应转向 evidence/floor 编译口径审计，而不是 table cap 修复。

原因：

- 64-trial bucketed audit 显示 `hard_capacity_conflict=29` 与 `lower_bound_under_truth=39` 全部为 `table_possible_max_below_truth` 且 `raw_inventory=verified_latest_inventory`。
- 同一 audit 显示 `evidence_floor_only=26` 的 `table_impossible_rows=0`、`round_impossible_rows=0`。
- current v300 全表 col[8] 分布为 `1=105`、`0=20`，`0` 集中于 `2511-2520` / `4511-4520`；当前 prior-stress 94 rows 不属于该 col[8]=0 cohort。

## D-v3-089：evidence-floor-only 是 evidence/floor 编译审计，不是 capacity 修复或 sampler 许可

2026-06-06 起，当前决策：

- `summarize_v3_prior_robustness_audit.py` 输出 `evidence_floor_only_summary`，只用于解释 `evidence_floor_only` bucket 的 component source 与 target/truth gap。
- 该 summary 不改变 `prior_robustness`、`prior_stress_capacity_table_drift`、readiness gate、posterior sampler、formal/value sampler 或正式出价。
- `evidence_floor_only` rows table cap 已 pass，后续优先查 evidence compiler 的 floor/missing target 口径，而不是 BidMap/Drop capacity。
- `evidence_floor_only` 不得进入 formal/value sampler promotion 分母；它只能作为 shadow-only formal/value sampler 设计前的 blocker 分流证据。
- floor source 审计优先级为 `item_anchors` -> `shape_anchors` -> `quality_floor_anchors` -> `numeric_constraints`；其中 numeric constraints 只产 exact，不产 floor。

原因：

- 64-trial default archive 复核显示 `evidence_floor_only=26`，其中 `total_cells floor_below_truth=21`、`total_value floor_below_truth=22`、`q6_cells/q6_value floor_below_truth=17/17`。
- 同一批 rows 还有 `q6_cells/q6_value/total_value target_missing=4/4/4`，对应 `2502` 这类 total cells exact 但 q6/value target 缺失的形态。
- 这些 rows 的 capacity audit 为 `table_impossible_rows=0`、`round_impossible_rows=0`，说明它们与 hard/lower-bound capacity conflict 是不同 blocker。
- `item_anchors` 是 value floor 的核心来源，`shape_anchors` 是 cells floor 的核心来源，`quality_floor_anchors` 只补 quality/count；因此 floor below truth 不能直接按 formal/value sampler 参数问题处理。

## D-v3-090：mixed value-floor + cells/capacity stress 必须 guard，不进入 formal/value candidate

2026-06-06 起，当前决策：

- `v3_fv_candidate` 只允许 pure `value_floor_stress`，不得同时带有 `capacity_cells_drift` 或 `q6_cells_floor_stress`。
- mixed `value_floor_stress + cells/capacity` rows 归入 `watch_mixed_value_floor_guarded`，并输出 `v3_fv_mixed_value_floor_watch`。
- guarded mixed rows 继续使用 `source=baseline`，`v3_fv_active=False`、`v3_fv_affects_bid=False` 必须保持。
- holdout/readiness 只把 pure value-floor rows 计入 formal/value candidate；mixed rows 单独统计为 `mixed_value_floor_watch_rows`。
- 该 guard 不改变 v2 formal/live/UI，不改变正式出价，不放宽 promotion gate。

原因：

- 64-trial archive 复核显示 value-floor stress 共 13 行，但其中 1 行同时带 `q6_cells_floor_stress`。
- 该 mixed row 与 prior-stressed cells/capacity/evidence blocker 相交；若继续算作 formal/value candidate，会把 table/capacity/evidence 语义问题误归因给 value sampler。
- readiness 仍要求 archive/live/holdout 支持；当前 formal/value sampler holdout 仍为 `sample_limited`，gate 仍 blocked。

## D-v3-091：evidence-floor-only pattern summary 只用于 evidence compiler 分流

2026-06-06 起，当前决策：

- `evidence_floor_only_summary` 输出 target-missing、floor-below-truth、exact-with-missing 的 component pattern counts。
- 这些 pattern 只用于解释 evidence compiler 的 floor/target 缺口，不改变 `prior_robustness`、readiness gate、posterior sampler、formal/value sampler 或正式出价。
- `total_cells exact + q6/value target missing` 形态必须与“全组件 floor below truth”分开处理；前者优先查 q6/value allocation target，后者优先查 item/shape floor source。
- pattern summary 不能作为 promotion evidence，也不能让 `evidence_floor_only` 进入 formal/value sampler candidate 分母。

原因：

- 64-trial archive 中 `evidence_floor_only=26`，但不是单一故障：22 行没有 target missing，4 行是 `q6_cells+total_value+q6_value` missing。
- 这 4 行同时满足 total cells exact matches truth，对应 `2502` 形态；它不是 BidMap/Drop capacity blocker，也不能靠 value sampler 参数修复。
- 固化 pattern counts 后，多 agent 可以分别审计 q6/value target 缺失和 floor below truth，而不会把两类 evidence compiler 问题混在一起。

## D-v3-092：synthetic settlement probe 只能作为 diagnostics-only falsifier

2026-06-06 起，当前决策：

- 可以投入小型 synthetic/simulator probe 来排除明显不可能的 settlement mechanism 假设，但必须标记 `diagnostics_only`，不得写入 readiness/promotion/v2 archive 输入。
- synthetic probe 不得伪造 raw `0x002D` payload、runtime id、sort id、capture timestamp、public/action event source 或 raw table version evidence。
- 若需要缓存，只能放在 `.tmp/codex/`；不得生成 `data/samples` 或 `data/processed` promotion artifacts。
- promotion 仍必须依赖真实 archive/live/holdout/readiness/stability；synthetic 拟合不能替代 table/capacity/source split 证据。

原因：

- 当前仓库没有能从游戏源码或 raw 表权威推导 final settlement inventory 的服务端机制。
- 现有 table sampler、`sample_session_truth`、`basic_mc` 都不是服务端最终结算复刻；`0x002D` 只能证明 final inventory 真实存在，不能解释其生成机制。
- synthetic probe 的价值在于缩小假设空间和生成诊断 fixture，风险在于误把拟合当作机制证明，因此必须隔离。

## D-v3-093：capacity source split summary 是 table/source 审计，不是 blocker 降级条件

2026-06-06 起，当前决策：

- `summarize_v3_capacity_table_audit.py` 输出 `source_split_summary`，聚合 map prefix/family、target source、capture day、0x002D message、drop/round residual、drop-universe residual、full observed action 与 public total count。
- 该 summary 只解释 hard/lower capacity conflict 的 source split，不改变 `prior_stress_capacity_table_drift` gate、posterior sampler、formal/value sampler 或正式出价。
- `source_split_summary.non_zodiac_missing_positive_files=0` 只能说明当前超 cap rows 的 final items 仍在 drop universe 内，不能证明服务端结算机制已复刻。
- hard/lower bucket 仍必须保持 blocked，直到 table/session/source split 有真实 archive/live/holdout 证据闭环。

原因：

- 64-trial hard/lower bucket 仍分别为 `table_impossible_rows=29/39`，且 raw latest inventory verified。
- 扣除临时生肖后仍有 drop-ref residual 与 round-cap residual；这排除“非 drop-universe item 或临时生肖完全解释冲突”，但不解释额外 occupied slots 的生成机制。
- 该字段让后续审计可以按 map family、target source 与 raw residual 分线推进，避免继续围绕 BidMap col[16]/DropEntry `n_max` 重复排查。

## D-v3-094：q6/value target-missing attribution 只定位 evidence compiler 缺口

2026-06-06 起，当前决策：

- `evidence_floor_only_summary.target_missing_attribution_summary` 输出 target-missing rows 的 map/profile、missing component pattern、evidence counts、source counts 与多标签 attribution。
- attribution 只表示已有 evidence 与 missing targets 的共现关系，不证明因果，不改变 `prior_robustness`、readiness gate、posterior sampler、formal/value sampler 或正式出价。
- `total_cells_exact_q6_value_targets_missing` rows 必须走 q6/value allocation target 审计；不能交给 capacity table 修复或 formal/value sampler 参数吸收。
- promotion evidence 仍必须来自真实 archive/live/holdout/readiness；target-missing attribution 只是 blocker 分流证据。

原因：

- 64-trial archive 显示 target-missing evidence-floor-only rows 全部集中在 `2502:4`。
- 这 4 行同时有 numeric/item/shape anchors 且 total cells exact matches truth，但 `q6_cells`、`total_value`、`q6_value` target 仍 missing。
- 该形态说明 evidence compiler 已能得到 total cells exact，却没有把现有 anchors 转成 q6/value allocation target。

## D-v3-095：capacity residual mode classifier 只用于 session-cap 语义分流

2026-06-06 起，当前决策：

- `summarize_v3_capacity_table_audit.py` 输出 `residual_mode_summary`，把 raw diagnostics 分为 `within_drop_ref`、`drop_ref_only_overflow`、`round_cap_overflow`、`drop_universe_gap`。
- residual mode 只用于定位 capacity/table/source blocker，不改变 `prior_stress_capacity_table_drift` gate、posterior sampler、formal/value sampler 或正式出价。
- `drop_ref_only_overflow` 优先指向 `BidMap col[17]` / session-cap 语义或同 drop-universe 追加抽样；`round_cap_overflow` 才进一步指向 settlement expansion/activity overlay。
- hard/lower bucket 仍必须保持 blocked；residual mode 不能作为 promotion evidence。

原因：

- 64-trial hard/lower bucket 均没有 `drop_universe_gap`，说明当前冲突不由非 drop-universe item 主导。
- hard bucket residual modes 为 `drop_ref_only_overflow=8`、`round_cap_overflow=6`、`within_drop_ref=1`；lower bucket 为 `drop_ref_only_overflow=12`、`round_cap_overflow=6`、`within_drop_ref=2`。
- drop-ref-only rows 多于 round-cap rows，说明下一步最小证据应先查 session-cap/drop-ref 语义，再查 settlement expansion。

## D-v3-096：target-missing event audit 只用于 q6/value compiler 分流

2026-06-06 起，当前决策：

- `summarize_v3_target_missing_event_audit.py` 只重放 target-missing prior-stress rows 的 prebid prefix，输出 event target、numeric exact、anchor payload 与 feasible summary 诊断。
- 该脚本不得改变 `events_from_fatbeans`、`compile_hard_constraints`、posterior sampler、formal/value sampler、readiness gate、v2 formal/live/UI 或正式出价。
- 2502 target-missing rows 在修复前继续视为 evidence compiler / allocation target blocker；不得用 formal/value sampler 参数吸收。
- event audit 的 JSON/summary 输出可作为下一步设计 q6/value allocation target 的输入，但不能作为 promotion evidence。

原因：

- 真实 64-trial archive 显示 4 行 target-missing 全部是 `2502`，且 `session.total_cells` target 存在、`bucket.q6.count/cells/value` target 均不存在。
- 这些 rows 的 shape/category evidence 很充分，但 anchor payload 没有 q6/value 字段：`item_anchors.with_value=0`、`shape_anchors.q6_count=0`、`known_value_floor=0`。
- 因此 blocker 不是“没有 evidence”，而是现有 evidence 没有被编译成 q6/value allocation target。

## D-v3-097：q6 residual exact 派生先保持 audit-only

2026-06-06 起，当前决策：

- q6 residual exact 只能先作为 `summarize_v3_target_missing_event_audit.py` 的诊断字段输出，不写入 `compile_feasible_summary`。
- count/cells residual 只有在 session total exact 且 q1-q5 对应 exact 全部存在、residual 非负、summary 无冲突时，才标记为 `derived` candidate。
- value/formal-value residual 仍保持 out-of-scope；没有 `session.total_value` hard exact 与 q1-q5 value exact 完整分区时，不得派生 q6 value。
- residual candidate 不能改变 posterior、CCV/residual sampler、formal/value sampler、readiness gate、v2 formal/live/UI 或正式出价。

原因：

- `summary.bucket(6)` 会被 posterior/formal-value 直接消费，直接把 residual 写成 hard exact 会改变 v3 shadow 全链路。
- 当前 2502 只有 r4 满足 q1-q5 cells exact 完整分区，可派生 `q6_cells=22`；r1-r3 仍缺 q2-q5/q3-q5/q4-q5 cells exact。
- 2502 四行均没有 session count exact，也没有 session value exact，因此 q6 count/value 不能派生。

## D-v3-098：q6 residual target candidate 可以进入 pipeline/evaluate，但仍不得参与 sampler

2026-06-06 起，当前决策：

- `assess_q6_residual_targets(summary)` 可以作为 v3 shadow pipeline 的通用诊断节点输出 `v3_rtc_*` fields。
- `v3_rtc_*` 只能表示 q6 count/cells/value 是否存在 residual exact candidate；它不得写回 `FeasibleSummaryReport`，不得改变 posterior、residual gate、formal/value sampler、readiness gate、v2 formal/live/UI 或正式出价。
- `v3_rtc_active` 与 `v3_rtc_affects_bid` 必须保持 false；即使 `v3_rtc_candidate=True`，也只能作为后续 shadow conditioning 设计输入。
- promotion/readiness 仍不能把 residual candidate 当作真实 sampler improvement evidence；真实证据仍必须来自 archive/live/holdout。

原因：

- 前一轮 audit 已证明 2502 r4 可由 `session.total_cells=156` 与 q1-q5 cells exact 完整分区派生 `q6_cells=22`，但这只覆盖 cells，不覆盖 count/value/formal value。
- 若直接写入 summary，会被 v3 posterior/formal-value 等消费者当作 hard exact，改变整条 shadow 链路，混淆“诊断证据”和“模型行为”。
- 在 evaluate 输出中统一暴露 `v3_rtc_*`，可以让 archive/readiness/holdout 后续审计稳定观察 candidate 覆盖率，同时保留 promotion gate 的严格边界。

## D-v3-099：guarded settlement bridge 需要独立 multi-seed stability gate

2026-06-06 起，当前决策：

- `settlement_count_guarded_bridge_holdout` 只证明单 posterior seed / 单 run 的 nested train-only holdout，不足以作为 promotion 支持。
- `summarize_v3_promotion_readiness.py` 必须单独输出 `settlement_count_guarded_bridge_stability` gate，用于承载 `summarize_v3_scp_guarded_bridge_stability.py` 的多 seed 结果。
- 没有 stability matrix 时，该 gate 必须 blocked，`overall_status=not_evaluated`；传入 matrix 后，只有 matrix `overall_status=watch` 才能进入 watch。
- seed drift、selected group drift、applied hurt、low applied support 任一存在时，该 gate 必须 blocked。
- 该 gate 仍是 shadow/readiness 证据，不改变 settlement count prior、formal/value sampler、v2 formal/live/UI 或正式出价。

原因：

- 当前 64-trial matrix 显示 seed 0 单独可 watch，但 seed 1 选择了 `2501,2506`，且 `2501` 出现 applied hurt。
- 因此 seed-0 的 `2506` bounded bridge 不能作为 promotion 支持；它只能作为后续继续收样本或重设 guard 的候选线索。
- 将 stability 显式接入 readiness 可以防止“单 seed watch”绕过 archive/live/holdout 稳定性要求。

## D-v3-100：guarded bridge stability cache/support 必须可审计

2026-06-06 起，当前决策：

- `summarize_v3_scp_guarded_bridge_stability.py` 的 cache key 必须包含 schema version；当输出结构新增 critical support 字段时，不得复用旧 cache。
- stability matrix 必须输出 `selected_group_support_summary`，至少包含 selected group、run count、selected folds、min/max applied rows、hurt run count、missing support runs。
- 如果 run 选择了多个 group 但缺少 group-level support 明细，stability 不能视为完整证据；必须标记 `selected_group_support_missing` 并保持 blocked。
- `selected_group_support_gap` 只用于 support 不足或 support 缺失的 group，不能把 gap=0 的 group 混作 blocker。
- 这些字段仍是 readiness/shadow 审计证据，不改变 formal/value sampler、settlement count prior、v2 formal/live/UI 或正式出价。

原因：

- 当前 seed drift 的关键解释不是只有 selected signature，而是 `2501` 的 hurt support 与 `2506` 的跨 seed support gap。
- 旧 cache 缺少 `selected_group_support` 时会让 summary 漏掉多组选入的 support 细节，造成 blocker 不可审计。
- promotion gate 需要证明稳定性证据完整；缺少 group-level support 本身就是不能 promotion 的证据缺口。

## D-v3-101：guarded bridge train-guard watch 不等于外层 holdout 安全

2026-06-06 起，当前决策：

- `summarize_v3_scp_guarded_bridge_holdout.py` 必须输出 selected group 的 train-guard metrics；只看外层 selected group 或 selected support 不足以解释 seed drift。
- 如果某 group 在 inner train guard 中为 `watch_train_guard`，但外层 holdout 出现 hurt/over-risk，则该 group 必须视为 train/holdout instability blocker。
- `2501` 当前属于该 blocker：inner guard watch，但外层 holdout hurt。
- `2506` 当前属于 support-depth blocker：train guard 选择稳定，但跨 seed min applied support 低于要求。
- 两类 blocker 都不能通过放宽 guard、降低 `min_applied_rows`、或只取 seed0 结果来变成 promotion evidence。

原因：

- 64-trial seed1 中 `2501` 在 fold4 的 train guard 指标为 `watch_train_guard`，训练侧 delta/over 看起来安全，但外层 53 applied rows 出现 p50 MAE hurt 与 over-risk。
- 这说明 bridge 的 group selection 对 posterior seed / fold split 仍敏感。
- promotion 要求 archive/live/holdout 稳定，而不是单一训练 guard 中看起来安全。

## D-v3-102：guarded bridge selected group 必须分类后再讨论下一步

2026-06-06 起，当前决策：

- `summarize_v3_scp_guarded_bridge_stability.py` 必须输出 `selected_group_instability_summary`，把 selected groups 分成 train/holdout instability、holdout hurt、support depth gap、missing support 或 stable watch。
- `2501` 当前分类为 `blocked_train_holdout_instability`，不能通过降低 over/hurt 门槛或只看 train guard 放行。
- `2506` 当前分类为 `blocked_support_depth_gap`，不能和 `2501` hurt 混为同一类失败。
- readiness 可以展示这些分类，但不能用它们放宽 gate；分类只是为了明确下一步修复/审计路径。
- selected instability 分类不改变 formal/value sampler、settlement count prior、v2 formal/live/UI 或正式出价。

原因：

- 同一个 multi-seed failure 中同时存在两种不同问题：`2501` 是 train guard watch 后外层 hurt，`2506` 是 stable intersection 但 applied support 不足。
- 如果只输出 selected groups 或 overall status，后续容易把 support-depth 问题和 holdout-hurt 问题混在一起。
- promotion 前需要可复核的 failure taxonomy，而不是只知道“matrix blocked”。

## D-v3-103：capacity/table 冲突必须按 semantic status 拆分

2026-06-06 起，当前决策：

- `summarize_v3_capacity_table_audit.py` 必须输出 `capacity_semantic_summary`，把 direct capacity conflict 拆成：
  - `blocked_round_cap_overflow_after_temp`
  - `blocked_drop_ref_overflow_after_temp`
  - `blocked_drop_universe_gap_after_temp`
  - `watch_activity_extras_explain_drop_ref_gap`
  - `needs_raw_inventory_verification`
- `blocked_round_cap_overflow_after_temp` 说明扣除已知临时 zodiac extras 后，verified raw settlement inventory 仍超过 `BidMap.col[14]` round-cap candidate；这比单纯 drop-ref overflow 更强，不能用 `BidMap.col[17]` max 或 DropEntry `n_max` 解释。
- `watch_activity_extras_explain_drop_ref_gap` 只能说明该 map/session 的 drop-ref gap 可被已知临时 activity item 解释；它不能解除其它 map 的 round-cap/drop-ref blocker。
- 这些 semantic status 只用于 audit/readiness 解释，不改变 sampler、formal/value shadow、v2 formal/live/UI 或正式出价。

原因：

- current raw v300 中 `col[16]` 是 `[[]]`，drop-ref 是 `col[17]`；重复围绕旧 `col[16]` 口径会浪费验证时间。
- prior-stressed top maps 的 flattened leaf `n_max=1`，不是多件 DropEntry 遗漏导致 settlement count 超过 sampler possible max。
- 真实 0x002D settlement inventory 与 detail truth 对齐，且部分 map 扣除 zodiac 后仍超过 round-cap candidate；后续必须查 server settlement expansion/session-cap semantics 或 table/version overlay，而不是调 formal/value sampler 参数。

## D-v3-104：capacity semantic matrix 用 cell status，不继承 map status

2026-06-06 起，当前决策：

- `summarize_v3_capacity_table_audit.py` 必须输出 `capacity_semantic_matrix`，按 `consistency_bucket × residual_mode × map_family × total_count_source × full_action_signal × public_total_signal × capture_day` 聚合。
- matrix cell 的 `semantic_status_counts` 必须由该 cell 内 raw diagnostics 计算，不能继承整张 map 的 `capacity_semantic_summary.status`。
- `within_drop_ref` cell 如果扣除临时 zodiac extras 后已被解释，只能标为 `watch_activity_extras_explain_drop_ref_gap` 或 pass；不能因为同 map 其它 session overflow 而标成 blocked。
- top-level JSON 增加 `semantic_matrix`，summary 增加 `semantic_matrix_all=...`；这仍是 audit/readiness 解释，不改变 sampler、formal/value shadow、v2 formal/live/UI 或正式出价。

原因：

- 同一 map 内可以同时存在 `drop_ref_only_overflow`、`round_cap_overflow` 和 `within_drop_ref` 子集。
- 后续要判断 session-cap/drop-ref 语义、settlement expansion、activity overlay，应按 cell 追 evidence/source/action/public-total，而不是把 map-level blocked 当成所有子集的原因。

## D-v3-105：capacity source/expansion 下钻只作为证据分流

2026-06-06 起，当前决策：

- `summarize_v3_capacity_source_expansion_audit.py` 用于把 capacity semantic matrix cell 下钻到 file-level examples，比较 public total、full observed action、latest settlement inventory 与 drop/round excess。
- 当 `public_total_latest_delta=0` 或 `action_latest_delta=0` 时，只说明该 evidence source 与 final settlement inventory 同向支持 count；它不是 promotion 证据，也不能直接修正 sampler cap。
- hard bucket 中带 public/full-action 的 after-temp overflow 优先作为 settlement/session expansion 语义证据。
- lower bucket 中 no-public/no-full-action 的 after-temp overflow 优先作为 target completeness 与 expansion 分离证据，不应和 hard exact/action/public cell 合并调 formal/value sampler。
- 该脚本固定 audit-only，不改变 v2 formal/live/UI、不改变正式出价、不启用 formal/value sampler。

原因：

- hard 2501 的 public total 与 latest inventory 对齐，hard 2506/2601 的 full action 与 latest inventory 对齐，说明 parser/truth 与这些外部 evidence source 一致。
- lower bucket 多数缺 public/full-action，不能用 hard bucket 的强证据强行解释；它需要单独查 floor target completeness。

## D-v3-106：lower-bound bucket 必须单独拆 target completeness

2026-06-06 起，当前决策：

- `summarize_v3_prior_robustness_audit.py --detail-summary` 必须输出 `lower_bound_target_completeness_summary`，只聚焦 `consistency_bucket=lower_bound_under_truth`。
- lower-bound rows 必须拆成：
  - `floor_count_target_below_prior_and_truth`
  - `count_target_above_prior_but_below_truth`
  - `missing_count_target_truth_above_prior`
- `lower_bound_under_truth` 中 `target_truth_delta<0` 的 count target 不能当作 sampler cap truth；它说明当前 target 是 floor/incomplete evidence，必须与 hard bucket 的 exact/public/full-action evidence 分开解释。
- lower-bound target completeness 仍是 audit/readiness 解释，不改变 formal/value sampler、不改变 v2 formal/live/UI、不改变正式出价。

原因：

- 真实 prior-stressed detail 中 lower bucket 为 39 行：21 行 floor count target 低于 prior 与 truth，10 行 count target 已超过 prior 但仍低于 truth，8 行缺 count target 但 truth 超过 prior。
- 31 条有 count target 的 lower rows 全部 `target_truth_delta<0`，平均为 `-25.968`；这不是“调高/调低 sampler 参数”的信号，而是 target completeness 与 settlement expansion/source semantics 的分离信号。

## D-v3-107：table/version smoke 不能替代 settlement expansion 语义证明

2026-06-06 起，当前决策：

- `summarize_v3_archive_table_timing.py` 必须同时输出 raw table timing、BidMap 23 列/col[16]/col[17] 语义、以及 priority maps reachable Drop `n_min/n_max` 摘要。
- 当前 raw v300 中，BidMap `col[16]` 不是 drop-ref，`col[17]` 是 drop-ref；priority maps 的 reachable Drop leaf `n_max=1` 不能解释 settlement item-count 超过 `drop_ref.items_max`。
- archive capture 中没有 version/hash-like 字段时，raw table mtime/fileVersion 只能作为“本地表与采集窗口兼容”的证据，不能证明每条 session 的服务端表版本。
- 该 smoke 仍是 audit-only；不能用它放宽 readiness/promotion gate，也不能恢复 formal/value sampler 参数调优。

原因：

- 真实 smoke 显示 `BidMap.txt` 为 125 行、全部 23 列，`col16=[[]]` 125/125，`col17_drop_ref_like=125/125`。
- 2401/2404/2406/2501/2506/2508/2601 的 reachable Drop leaf 全部 `leaf_n_ranges=1-1`，因此 DropEntry 多件数不是当前 capacity 冲突解释。
- 剩余 blocker 更可能在 settlement expansion/session-capacity/server-side overlay/table-version-per-session 语义层，而不是本地字段索引或 leaf count range。

## D-v3-108：settlement residual-mode 只能证明 final inventory，不证明 expansion 机制

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 必须支持 `--group-by residual_mode`，把 settlement count 相对 current table caps 拆为 `within_drop_ref_after_temp`、`activity_extras_only_drop_ref_gap`、`drop_ref_only_overflow_after_temp`、`round_cap_overflow_after_temp`。
- residual-mode summary 必须同时输出 payload slot headroom、payload candidate/occupied mismatch、full observed action rows、public total rows 与 public-total delta。
- 0x002D payload candidate/occupied 与 public total 匹配 final inventory 时，只能证明 final settlement inventory 解析稳定；不能说明 items 来自 BidMap/Drop base sampler、server-side expansion、activity overlay 或 per-session table version。
- 因此 residual-mode smoke 不能作为 v3 promotion evidence，也不能恢复 formal/value sampler 参数调优；它只把下一步集中到 settlement expansion/session-capacity/source semantics。

原因：

- 真实 archive 中 after-temp residual modes 为 `within_drop_ref_after_temp=245`、`activity_extras_only_drop_ref_gap=24`、`drop_ref_only_overflow_after_temp=113`、`round_cap_overflow_after_temp=59`。
- over-cap rows 的 payload raw candidate / occupied slot delta 均为 0；出现 public total 时 delta 也为 0。
- 这些信号确认 “truth 是 final inventory”，但没有给出可用于 sampler/readiness promotion 的生成机制。

## D-v3-109：round/session 维度不能单独解释 settlement over-cap

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 必须支持 `--group-by round_index`、`--group-by capture_rounds` 与 `--group-by bidmap_rounds_total`，用于判断 over-cap 是否只是 late-round 或 map-session-length 问题。
- 如果 after-temp overflow 同时出现在 1-5 capture rounds 与 `bidmap_rounds_total=25/30` 两类 map，则不能把 blocker 简化为“晚轮数容量”或“30-round map 专属容量”。
- round/session 维度只能作为 settlement expansion/source semantics 的分流证据；不能作为 sampler cap 修正、readiness 放行或 promotion evidence。

原因：

- 真实 archive 中 `capture_rounds=1` 仍有 `above_drop_after_temp=12/27` 与 `above_round_after_temp=8/27`，`capture_rounds=2` 也有 `15/48` 与 `4/48`。
- `bidmap_rounds_total=30` over-cap 更重，但 `bidmap_rounds_total=25` 也有 `above_drop_after_temp=62/188` 与 `above_round_after_temp=13/188`。
- over-cap 跨 round/session 维度存在，说明仍需查更底层的 server-side expansion、source semantics 或 table-version-per-session 机制。

## D-v3-110：payload field-shape 不能作为 over-cap 解释或 promotion evidence

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 必须在 residual-mode 审计中输出 0x002D settlement payload top-level shape、field 5/6/7/8 count、field20 presence/value、以及 field 5/6/7/8 child signatures。
- 如果 over-cap rows 与 within-cap rows 共享同类 payload field shape/child signatures，且 raw candidate/occupied slot 与 final inventory 对齐，则不能再把 blocker 归因于特殊 payload block 或 parser 膨胀。
- field20 value 在当前 archive 中呈每局唯一/近唯一分布；在没有稳定语义映射前，不能把 field20 当作 source id、activity id、table version 或 expansion classifier。
- payload field-shape 审计只能缩小排查范围；不能作为 sampler cap 修正、readiness 放行或 promotion evidence。
- formal/value sampler 参数调优继续暂停，直到 server-side settlement occupancy/source semantics 或 per-session table/version overlay 有可复核解释。

原因：

- 真实 residual smoke 中 `drop_ref_only_overflow_after_temp` 为 113 files、`round_cap_overflow_after_temp` 为 59 files，两者 `payload_mismatch=0`。
- over-cap 与 within-cap rows 都有 field 5/8 child signature 的同类结构，field 5 max=4、field 8 max=5；没有 over-cap 专属字段形态。
- field20 在 over-cap rows 中 100% 出现，但 within-cap rows 也有 240/245 出现，且 value 不形成稳定分类。

## D-v3-111：v303 activity table smoke 不能解除 default capacity blocker

2026-06-06 起，当前决策：

- `summarize_v3_archive_table_timing.py` 必须输出 `2521-2530` 与 `4521-4530` 的 BidMap/Drop presence，用于区分 raw table update、activity overlay 与 default cohort。
- 本机 v303 StreamingAssets 可作为 activity table timing 线索，但不能自动替换项目 raw v300 或证明每条 archive session 的服务端表版本。
- 即使 v303 BidMap 新增 `2521-2530` / `4521-4530`，只要对应 Drop pool 仍缺失，252x activity cohort 仍必须保留为 missing-drop/activity-overlay lane。
- 252x/452x activity cohort 不得 fallback 到 default 250x prior，不得进入 default archive prior、formal/value sampler promotion 分母或正式出价。
- v303 priority maps 的 `col[17]` drop-ref、`col[14]` round-cap 与 reachable Drop leaf `n_max=1` 未相对 v300 改变时，不能用 table drift 解释 default 24xx/25xx/2601 after-temp settlement over-cap。

原因：

- v303 smoke 显示 `raw_file_version=303`、`BidMap rows=165`、`col16=[[]]`、`col17_drop_ref_like=165`。
- `2521-2530` 与 `4521-4530` 均为 `bidmap_present=10`、`drop_present=0`、`drop_ref_pairs=22-44:10`。
- `2401/2501/2506/2508/2601` 的 v303 drop-ref/round-cap 与 v300 相同，且 Drop target leaf `n_max=1`；default over-cap 仍需查 server-side settlement occupancy/source semantics。

## D-v3-112：slot/source shape 不能作为 over-cap 解释或 promotion evidence

2026-06-06 起，当前决策：

- `summarize_v3_settlement_payload_audit.py` 必须在 inventory block metrics 中输出 occupied/empty slot field shapes、occupied/empty slot 顶层 int fields、candidate paths，并保留 raw candidate/occupied/dedup mismatch 摘要。
- `summarize_v3_settlement_count_prior_candidates.py` 必须把上述 slot/source metrics 接入 residual-mode/round/session 分组，和 payload field-shape、public-total、full-action evidence 一起比较。
- 如果 over-cap groups 与 within-cap groups 共享 dominant slot shape、candidate path 与 slot int-field 形态，则不能把 capacity blocker 归因于 field[4] 内部的 over-cap 专属 source、award、activity 或 expansion marker。
- 这些 slot/source metrics 只能排除 parser/slot marker 类解释，不能作为 sampler cap 修正、readiness 放行或 promotion evidence。
- formal/value sampler 参数调优继续暂停，直到 server-side settlement occupancy/source semantics、per-session table version 或外部 overlay table 机制有可复核解释。

原因：

- 真实 residual smoke 中所有 item candidates 都位于 slot child path `3`，overall 为 `candidate_paths=3:18310`。
- `drop_ref_only_overflow_after_temp` 与 `round_cap_overflow_after_temp` 的 occupied/empty slot dominant shapes 与 `within_drop_ref_after_temp` 相同。
- over-cap groups 的 slot 顶层 int field 主要只有 field `1`；少量 field `2/6/9` 只在 within-cap/overall 出现，不是 over-cap 专属 marker。
- 这说明当前 0x002D field[4] slot structure 没有暴露可直接用于 sampler/readiness 的 over-cap source 语义。

## D-v3-113：0x002D outer wrapper 不能作为 capacity blocker 解释或 promotion evidence

2026-06-06 起，当前决策：

- `summarize_v3_settlement_payload_audit.py` 必须输出 0x002D frame body 的 outer wrapper shape、field3/4/5 presence/value tuple 与 field6 count。
- `summarize_v3_settlement_count_prior_candidates.py` 必须把 outer wrapper metrics 接入 residual-mode/round/session 分组，和 payload/slot/public-total/full-action evidence 一起比较。
- 如果 over-cap groups 与 within-cap groups 共享 dominant outer wrapper shape，且 field3/4/5 presence 与 field6 count 都不形成 over-cap 专属 marker，则不能把 capacity blocker 归因于 0x002D wrapper 的 source、activity、award 或 expansion 字段。
- outer wrapper metrics 只能排除 wrapper-marker 类解释；不能作为 sampler cap 修正、readiness 放行或 promotion evidence。
- formal/value sampler 参数调优继续暂停，直到 server-side settlement occupancy/source semantics、per-session table version 或外部 overlay table 机制有可复核解释。

原因：

- 真实 residual smoke 中 `drop_ref_only_overflow_after_temp`、`round_cap_overflow_after_temp` 与 `within_drop_ref_after_temp` 共享 `1:0:i,2:2:b,5:0:i,6:2:b×4`、`1:0:i,2:2:b,6:2:b×4`、`1:0:i,2:2:b,3:0:i,4:0:i,5:0:i,6:2:b×4` 等 dominant outer shapes。
- field3/4 在 overall 中均为 134 rows，且按 residual mode 混合分布；field5/loss_units 为 276 rows，也不是 over-cap 专属。
- field6 count 基本为 4；少量 max=5/8 分散在 drop-only/within-cap，不形成 round-cap/drop-only 专属 source marker。
- 因此当前 0x002D outer wrapper 没有暴露可直接用于 sampler/readiness 的 capacity expansion 语义。

## D-v3-114：capture/session cohort 分组不能作为 capacity blocker 解释或 promotion evidence

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 必须输出 `capture_day`、`session_token_prefix6` 与 `session_token_prefix8`，并支持按这些 cohort 维度分组。
- 如果 over-cap 横跨多个 capture days 与 session token prefixes，不能把 capacity blocker 简化为一个采集日、一个 session family 或一次性 table-version switch。
- capture/session cohort summary 只能用于排除或分流 table/version 假设；不能作为 sampler cap 修正、readiness 放行或 promotion evidence。
- formal/value sampler 参数调优继续暂停，直到 server-side settlement occupancy/source semantics、per-session table version 或外部 overlay table 机制有可复核解释。

原因：

- 真实 archive 中 after-temp over-cap 横跨 `20260531/20260601/20260605/20260530/20260604` 等多个 capture days。
- `129501` 为 369 files，`above_drop_after=146`、`above_round_after=49`；`127412` 为 64 files，`above_drop_after=21`、`above_round_after=9`，两个主要 session prefix 都存在 overflow。
- `136751` 只有 8 files，虽然 overflow-heavy，但不足以解释 default 24xx/25xx/2601 的主要 capacity blocker。
- 因此 cohort 分组进一步排除了简单 table/capture 切换解释，但没有提供可直接用于 promotion 的生成机制。

## D-v3-115：Drop item-universe coverage 不能作为 after-temp over-cap 解释或 promotion evidence

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 必须在 residual/capture/session 分组中输出 reachable Drop item-universe coverage，并分开统计已知临时生肖 missing 与非生肖 missing。
- 如果 `non_zodiac_missing_from_drop_universe_count` 在 over-cap groups 中为 0，不能再把 capacity blocker 归因于 current BidMap/Drop 之外的非生肖 item pool 缺失。
- 临时生肖 overlay 仍应作为 activity extra 单独扣除；它不能解释 after-temp drop/round overflow，也不能进入 default sampler promotion 证据。
- Drop item-universe coverage 只能排除 item-pool 缺表类解释；不能作为 sampler cap 修正、readiness 放行或 promotion evidence。
- formal/value sampler 参数调优继续暂停，直到 current Drop universe 内的 settlement count/occupancy 扩展、session-capacity 或服务端 source semantics 有可复核解释。

原因：

- 真实 archive 441 条 settlement rows 中 `missing_drop` 平均为 1.658，但全部 missing 都是已知临时蓝色生肖 id；`non_zodiac_missing` overall max 为 0。
- `drop_ref_only_overflow_after_temp` 113 files 与 `round_cap_overflow_after_temp` 59 files 的 `non_zodiac_missing` max 均为 0。
- 因此 after-temp over-cap 是“同一 item universe 内的件数/占用问题”，不是未知非生肖物品池混入。

## D-v3-116：runtime/item duplicate 不能作为 capacity blocker 充分解释或 promotion evidence

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 必须输出 runtime/item duplicate metrics 与 unique non-temp item count cap coverage。
- 如果 `duplicate_runtime_id_count` 和 `duplicate_runtime_item_pair_count` 为 0，不能把 over-cap 归因于 parser 或 runtime 重复。
- 如果按 unique non-temp item id 去重后仍存在 over-cap，不能把 blocker 简化为“同一 item_id 多实例化导致 count 口径偏高”。
- duplicate/unique audit 只能缩小 capacity 语义范围；不能作为 sampler cap 修正、readiness 放行或 promotion evidence。
- formal/value sampler 参数调优继续暂停，直到 unique item 层面的 settlement count/session-capacity、round/category 生成机制或 cap 字段语义有可复核解释。

原因：

- 真实 archive 441 条 settlement rows 的 duplicate runtime 与 duplicate runtime-item pair max 都为 0。
- `drop_ref_only_overflow_after_temp` 113 rows 中按 unique non-temp item id 后仍有 51 rows 超 drop-ref。
- `round_cap_overflow_after_temp` 59 rows 中按 unique non-temp item id 后仍有 58 rows 超 drop-ref、21 rows 超 round cap。
- 因此 item_id 多实例化只解释部分 overflow，不能解除 v3 capacity blocker。

## D-v3-117：BidMap round-category hint 不能作为 capacity blocker 解释或 promotion evidence

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 必须输出 BidMap `round_category_hints` key/count，并统计 settlement item primary-category、hinted/unhinted non-temp item coverage。
- 如果真实 archive 中 over-cap 与 within-cap groups 共享同一 hint key，且 unique non-temp item 大量落在 unhinted categories 中，不能把 `round_category_hints` 解释为 settlement item-count 上限或 per-round global category filter。
- category/hint audit 只能排除一种 cap 字段误读；不能作为 sampler cap 修正、readiness 放行或 promotion evidence。
- formal/value sampler 参数调优继续暂停，直到 unique item 层面的 settlement count/session-capacity、round/category 生成机制或 cap 字段语义有可复核解释。

原因：

- 真实 archive 441 条 settlement rows 的 `bidmap_round_category_hint_key` 全部为 `103`。
- `round_cap_overflow_after_temp` 59 rows 的 unique non-temp item 平均覆盖 9.797 个 primary categories，`unique_unhinted_non_temp_item_count` 平均 43.780、最高 52。
- `within_drop_ref_after_temp` 同样共享 hint key `103`，且也覆盖 9-10 个 primary categories；hint key 不是 over-cap 专属 marker。
- 因此 `round_category_hints` 不能解释当前 unique item 层面的 after-temp over-cap。

## D-v3-118：quality/cells residual 下钻不能把 capacity blocker 降级为 formal value evidence

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 必须输出 `unique_residual_mode`，区分 unique round-cap overflow、instance-only round overflow、unique drop overflow、instance-only drop overflow、activity extras 与 within unique caps。
- 同一审计必须输出 non-temp/unique non-temp 的 quality counts、quality cells、total cells、q6 count 与 q6 cells。
- 如果 unique round-cap overflow 的 quality 分布以 q2-q4 等 broad inventory 为主，且 q6/cells tail 与 within-cap rows 有重叠，不能把该 blocker 直接解释为 q6 value-floor 或 formal value 上修证据。
- capacity/cells watch 仍只能进入 table/capacity/evidence consistency 审计；formal/value sampler 只允许在 shadow-only value-floor 路径中继续设计与验证。

原因：

- `unique_residual_mode` smoke 将 441 rows 拆成：activity extras 201、within unique caps 68、instance drop overflow 62、unique drop overflow 51、instance round overflow 38、unique round overflow 21。
- 21 条 `unique_round_cap_overflow_after_temp` 的 unique non-temp item 平均 53.143、unique cells 平均 152.143、最高 206，说明仍有真实 unique item/cells 层面的 capacity conflict。
- 这些 rows 的 unique quality 分布为 q4=298、q2=241、q3=234、q5=170、q1=101、q6=72；q6 有 tail risk，但不是主导来源。
- `within_unique_caps_after_temp` 仍有 q6 cells max 39，和 unique round overflow 的 q6 cells max 37 重叠；因此 q6/cells tail 不能单独作为 promotion evidence。

## D-v3-119：BidMap raw numeric columns 不能绕过 settlement capacity blocker

2026-06-06 起，当前决策：

- `summarize_v3_bidmap_raw_capacity_candidates.py` 是 BidMap raw numeric column 与 settlement unique count/cells truth 的审计入口。
- 语义上可作为 capacity 候选的 raw columns 暂限 `rounds_total`、`round_caps_candidate` 与 `drop_ref`；其他 count-sized numeric columns 必须按 schema role 审查，不能因为数字覆盖 item count 就当作 cap。
- 如果 count-sized non-capacity columns 是 category id、hero requirement、round category hint、sub-pool weight 或 mode flag，不得用它们修正 sampler cap、readiness 或 promotion gate。
- `round_caps_candidate` 仍只能作为 audit-only best-known count candidate；它不是 final settlement item/cells cap，也不是 formal/value sampler promotion evidence。

原因：

- 真实 archive 441 rows 中，`round_caps_candidate` 覆盖 unique non-temp item count 420/441，失败的 21 rows 正是 `unique_round_cap_overflow_after_temp`。
- `drop_ref` 只覆盖 unique non-temp item count 332/441，失败 109 rows；`rounds_total` 只覆盖 71/441。
- 对 unique settlement cells，`round_caps_candidate` 只覆盖 7/441，`drop_ref` 覆盖 0/441，不能解释 cells/capacity stress。
- 非 capacity 数字列中 `category_id`、`entry_requirement`、`round_category_hints` 可在数字上覆盖 item count，但它们是 schema ids/hints，不是 count/cells cap。

## D-v3-120：BidMap sub-pool routing 不能作为 capacity blocker 充分解释或 promotion evidence

2026-06-06 起，当前决策：

- `summarize_v3_settlement_count_prior_candidates.py` 必须输出 `bidmap_sub_pool_kind`、`bidmap_sub_pool_count` 与 `bidmap_sub_pool_weight_total`，并支持按 sub-pool kind/count 分组。
- 如果 unique round overflow 同时出现在 leaf maps 与 weighted parent maps，则不能把 blocker 简化为“未知母图/子图路由导致 cap 使用错误”。
- 如果 self-only 2601 没有 unique round overflow，只能把 2601 作为 drop-ref/instance overflow 线索，不能用它解释 default shipwreck/villa unique round blocker。
- sub-pool/cohort audit 只能排除 routing 类解释；不能作为 sampler cap 修正、readiness 放行或 promotion evidence。

原因：

- 真实 archive 中 leaf maps 有 260 rows，其中 `unique_round_cap_overflow_after_temp=14`；weighted parents 有 159 rows，其中 unique round overflow=7。
- self-only 2601 有 22 rows，unique round overflow=0，但仍有 unique drop overflow=7。
- unique round overflow 更集中于 map family：shipwreck 19、villa 2、hidden 0；这说明后续应查 map-family/session-capacity 或 server-side settlement expansion，而不是只查母图路由。
- capture/round 分布也不是单一 cohort：capture rounds 1/2/4/5 均有 unique round overflow，round_index 1/3/4/5/none 均出现，不能解释为单一采集轮次错误。

## D-v3-121：settlement over-cap blocker 收口为 server/source capacity semantics，仍不得恢复 sampler 调参

2026-06-06 起，当前决策：

- `summarize_v3_settlement_source_semantics_audit.py` 是 settlement over-cap / capacity blocker 的 source-semantics 收口入口。
- 当前 local v300 BidMap `round_caps_candidate` 与 `drop_ref` 仍只能作为 audit-only candidate；不得当作 final settlement hard cap、sampler cap 修正、readiness 放行或 promotion evidence。
- 21 条 `unique_round_cap_overflow_after_temp` 的主解释归类为 server-side settlement expansion / session-capacity source semantics。
- per-session table version 与 external overlay table 只保留为最小不可判定假设：前者目前没有 day/session/map 集中证据，后者有 Activity table listed-but-missing 的 local metadata，但没有 non-zodiac Drop-universe gap。
- 本阶段 goal 到 capacity blocker 收口为止；不恢复 formal/value sampler 参数调优，不接入 live/formal，不放宽 readiness/promotion gate。

原因：

- 21 条 unique round overflow 的 0x002D raw candidate 与 occupied slot 对 final inventory delta 均为 0，payload mismatch 为 0/21。
- 21 条 non-zodiac missing from reachable Drop universe 均为 0；因此不是解析重复、slot 误计或未知非生肖 item pool 混入。
- 其中 3 条有 external source confirmation：2 条 direct full action、1 条 public total；其余 18 条由 settlement payload 自证。
- 这些 rows 横跨 `shipwreck:19/villa:2`、6 个 capture day、2 个 session prefix、8 个 map；不支持单一 per-session table version 或单一 cohort 解释。
- local raw/table version 均为 300，filelist 列出 `Tables/Activity.txt` 而本地缺表；这只支持保留 overlay 作为件数/活动机制的未判定假设，不足以直接修正 sampler。

## D-v3-122：capacity/source expansion 只能作为 shadow-only audit layer，不得作为 promotion 放行

2026-06-06 起，当前决策：

- `src/bidking_lab/inference/v3/capacity_source_expansion.py` 是 settlement capacity/source expansion 的 v3 shadow-only 层，字段族为 `v3_cse_*`。
- `v3_cse_*` 必须固定 `affects_bid=False`、`active=False`；不得改变 v2 formal/live/UI、posterior sampling、formal decision value 或正式出价。
- `data/processed/v3_capacity_source_expansion_shadow.json` 可提交，作为 archive/live/model_eval 的可复核 evidence artifact；它的存在只表示 source/capacity blocker 解释可见。
- `capacity_source_expansion_shadow` readiness gate 只能证明 CSE evidence 可见且 inactive；不得把该 gate 的 `watch` 解释为 v3 promotion ready。
- map-family source expansion prior 因 false positive 过宽，只能用于 audit/watch；map_id prior 虽更精确但漏掉单例/稀疏 blocker，不能单独恢复 formal/value sampler。
- 下一阶段如需恢复 shadow-only formal/value sampler，必须先补 source parser、活动/远端表 acquisition、更多样本，或设计能同时解释 map-family recall 与 map_id precision 缺口的可证伪 expansion prior。

原因：

- default archive `map_family` session holdout 对 21 条 unique round-cap blocker 的 recall 为 1.0，但 candidate precision 只有 0.050119，false positive 为 398 rows。
- default archive `map_id` holdout recall 为 0.857143，覆盖 18/21，漏 3 条稀疏/单例 map blocker。
- truth rows 的 payload mismatch 与 non-zodiac missing 均为 0；当前 blocker 不是 parser/slot/unknown non-zodiac item-universe 问题。
- archive evaluator smoke 显示 `v3_cse_ready_rows=1560`、`v3_cse_candidate_rows=752`、`v3_cse_active_rows=0`；readiness 中 `capacity_source_expansion_shadow=watch` 但 overall 仍 `not_ready`。

## D-v3-123：source-aware CSE signatures / fallback 只能作为 holdout matrix，不得默认接入 CSE prior

2026-06-07 起，当前决策：

- `summarize_v3_capacity_source_expansion_holdout.py` 可以审计 composite source signatures 与 `--fallback-group-by`，但这些策略默认只作为 audit matrix。
- exact `map_id` 仍是当前最保守的 CSE group-support baseline；它 recall 不满，但 precision 高于 map-family/fallback broad watch。
- `map_family_sub_pool_kind` fallback 可以解释 map-id singleton miss，但会扩大 candidate/false-positive，不得作为默认 source-aware expansion prior。
- `map_id_capture_rounds`、`map_id_round_index`、`map_id_last_round_flag`、`map_family_outer_shape`、`map_family_payload_shape`、`map_family_action_count`、`map_id_payload_shape` 只能用于分片审计；不能单独作为 sampler/readiness/promotion 证据。
- `mechanism_class` 由 unique-overflow/source-semantics truth 派生，只能用于诊断与标签，不得作为 prior key 或 train-time feature。
- 若后续要把 CSE 从 broad watch 变成更精确 prior，必须获得更强 source parser、活动/远端表 acquisition 或新增样本支持；不得用 fallback 满召回来替代 precision 证明。

原因：

- `map_id` holdout：21 truth 覆盖 18，miss 3，candidate 202，false positive 184，precision 0.089109。
- 3 条 miss 分别是 2408、2410、2509 的 singleton truth fold；训练折同 map 没有 source-semantics support。
- `map_id -> map_family_sub_pool_kind` fallback：覆盖 21/21，但 candidate 增至 347，false positive 增至 326，precision 降至 0.060519。
- `map_id_capture_rounds` precision 升至 0.129412，但 recall 降至 0.52381；`map_family_outer_shape` recall 0.904762，但 precision 0.07393，仍比 map_id 宽。

## D-v3-124：252x activity cohort 统一作为调参参考，不作为 default/promotion evidence

2026-06-07 起，当前决策：

- `data/samples/fatbeans_activity_20260605_shipwreck/` 与 `data/sample_manifests/fatbeans_activity_shipwreck_2026-06-05.json` 统一标记为 `activity_tuning_reference`。
- 该 cohort 的 metric scope 是 `source_parser_table_acquisition_and_shadow_tuning_reference_only`；只能用于：
  - 2521+ activity/source table acquisition 目标确认；
  - activity overlay / source parser 假设审计；
  - 后续 shadow-only formal/value sampler 的参考分片；
  - 验证系统能把缺表活动样本标为 prior unavailable。
- 在 verified `2521+` Drop/source overlay 或服务端映射前，252x activity cohort 不得进入 default archive baseline、default count prior、formal/value sampler promotion、readiness 放行或正式出价。
- `usable_metric_files=15` 只表示 capture 文件本身可解析、ready windows 可生成；不等于可用于普通沉船准确率或 promotion 分母。
- 当前仓库可复核口径是 15 份 252x capture，覆盖 6 个 map id；本机 v303 表侧有 `2521-2530` 10 个 BidMap rows。未找到项目内可复现的“16 个 252x capture/map”口径。

原因：

- 15 个 activity captures 全部 valid，58 个 ready windows 可用于 parser/window/truth 和活动鲁棒性审计。
- 本机 v303 新增 `2521-2530` / `4521-4530` BidMap，但对应 Drop pool 仍缺失；表侧证据仍是 missing-drop/source-overlay，而不是完整 prior。
- activity mapping likelihood 显示 `252x->251x` 比 `252x->250x` 略优，且两个候选族 missing item rate 均为 0；margin 不足以证明 official mapping。
- prior robustness 仍为 `prior_unavailable`：ready=58、post_ready=0、metric=0、trusted=0/58、activity=58。
- CSE activity holdout 无 unique round-cap truth rows；其 non-zodiac missing 是 overlay/source-parser 线索，不是 default 21 条 over round-cap blocker 的解释。

## D-v3-125：CSE source-context 是解释维度，不是 promotion key

2026-06-07 起，当前决策：

- `source_context_class` 是 post-settlement audit context，用于解释 source support 强弱；不得作为 train-time prior key、sampler cap 修正、readiness 放行或 promotion evidence。
- `v3_cse_source_context_classes` 必须和 `v3_cse_source_evidence_classes` 一起进入 archive CSV、processed artifact 与 live `model_eval`，保证实战后能复盘 payload-only、public-total、direct-action 的差异。
- exact `map_id` 继续作为 CSE 最保守默认 support baseline；`map_family` 与 `map_family_sub_pool_kind` fallback 只作为 holdout counterfactual，不默认接入 source-aware expansion prior。
- payload-verified rows 必须继续拆分：partial action、empty action、no external source 与 mismatch 不能混同为 external source confirmation。
- 在 fallback precision 没有改善、payload-only rows 没有更强 source/parser/table 解释前，不恢复 formal/value sampler 参数调优，不放宽 readiness/promotion gate，不改变 v2 formal/live/UI 或正式出价。

原因：

- 441 个 settlement rows 的 source context 分布为 `payload_verified_partial_action_only:339`、`payload_verified_empty_action_results:55`、`public_total_confirmed:27`、`direct_action_full_confirmed:17`、`payload_unverified_or_mismatch:2`、`payload_verified_no_external_source:1`。
- 21 条 unique round-cap truth 中，15 条是 partial action only、3 条是 empty action results、2 条 direct action full confirmed、1 条 public total confirmed。
- map-id holdout 召回 18/21、precision 0.089109；3 条 miss 都是 train fold 无同 map source support 的 singleton/sparse blocker。
- map-family holdout 可召回 21/21，但 precision 只有 0.050119；`map_id -> map_family_sub_pool_kind` fallback 也召回 21/21，但 candidate 增至 347、false positive 326、precision 0.060519。
- archive/readiness 仍显示 `v3_cse_active_rows=0`、`capacity_source_expansion_shadow=watch`、overall `not_ready`；该证据只能支持 blocker 审计继续推进，不能支持 promotion。

## D-v3-126：CSE pressure tier 只能作为 high-precision watch，不是默认 prior

2026-06-07 起，当前决策：

- `v3_cse_pressure_candidate` 定义为：`v3_cse_candidate=true` 且 prebid target count 已超过 `v3_prior_items_per_session_max`。
- pressure tier 是 source-aware expansion 的 audit-only 子层，用于区分“group 曾出现 over-cap”与“当前窗口已出现 capacity pressure”。
- pressure tier 必须固定 `active=false`、`affects_bid=false`，不得改变 v2 formal/live/UI、posterior sampler、formal/value sampler 或正式出价。
- archive CSV、live `model_eval` 与 readiness summary 必须输出 pressure tier 与 target/prior delta 字段，便于实战后按 pressure/non-pressure 分片复盘。
- pressure tier precision 虽明显高于 broad CSE candidate，但 recall 不足；不得把它作为 promotion/readiness 放行或默认 source-aware prior。

原因：

- archive prebid guard 显示 broad `v3_cse_candidate` 覆盖 752 rows、81 truth windows，row precision 0.107713，session precision 0.098131。
- `v3_cse_pressure_candidate` / `target_above_prior_max` 只选 61 rows，覆盖 24 truth windows，row precision 0.393443；session 侧覆盖 11/21 truth sessions，session recall 0.52381。
- `target_near_source_p95_5` 的 row precision 为 0.410714，但 row recall 只有 0.283951，仍不足以替代 broad candidate。
- 因此 pressure tier 是后续提升 precision 的有效线索，但还不能解决 map-id 漏召回、payload-only rows 或 promotion blocker。

## D-v3-127：payload-only CSE truth 必须拆成 empty-action 与 partial-action 两条审计路径

2026-06-07 起，当前决策：

- payload-only CSE truth 不能再作为单一证据桶处理；至少拆成：
  - `payload_verified_empty_action_results`：action result 存在，但 observed item max 为 0；
  - `payload_verified_partial_action_only`：有部分 action observed items，但远低于 settlement inventory。
- empty-action rows 是 source parser / action-result decode / table acquisition 的优先目标；不能用 sampler 调参解释。
- partial-action rows 可以作为 session-capacity source semantics 的较弱支持，但仍不等同于 full external source confirmation。
- exact map-id miss 全部落在 payload-only 内；在补齐 empty-action/partial-action parser 或新增 support-depth 前，不得把 broad fallback 或 pressure tier接入默认 prior。
- `v3_cse_pressure_candidate` 可用于区分当前 prebid window 是否已有 capacity pressure，但不能替代 payload-only source 解释。

原因：

- 21 条 CSE truth 中有 18 条 payload-only，3 条 full external confirmation。
- 18 条 payload-only 中，15 条是 partial-action，3 条是 empty-action。
- map-id holdout 的 3 条 miss 全在 payload-only：2509/2410 是 empty-action，2408 是 partial-action。
- 18 条 payload-only 全部有 broad prebid CSE candidate window，但只有 8 条有 pressure window；pressure 对 recall 不足。
- empty-action 3 条 action max 全为 0、action gap 平均 60；partial-action 15 条 action max 平均 5.867、action gap 平均 53.467，二者都仍需要 source parser/table evidence。

## D-v3-128：empty-action CSE truth 归类为 numeric-only source semantics，不再优先按 item parser 漏解处理

2026-06-07 起，当前决策：

- `payload_verified_empty_action_results` 的 3 条 CSE truth 归类为 `numeric_only_result` action source。
- 这些 rows 的 action result payload 没有 field 8 item list；不得继续把它们描述成 item reveal parser 未解码。
- empty-action 后续检查重点改为 numeric action source semantics、table/support-depth、server-side settlement expansion 或 per-session/external overlay 机制。
- `payload_verified_partial_action_only` 仍作为 item reveal payload 的弱外部线索；它能证明部分 item 被 action/source 暴露，但不能证明完整 inventory。
- 该分类只用于 audit/readiness 解释，不得作为 formal/value sampler 参数、默认 CSE prior、promotion gate 或正式出价输入。

原因：

- payload-only action shape 审计显示 18 条 payload-only truth 中 `item_reveal_payload:15`、`numeric_only_result:3`。
- 3 条 empty-action rows 全部 `source_item_payload_block_max=0`、`source_observed_item_max=0`，action ids 为 `100105/100104/100124/100107` 等 numeric cells/value result。
- 15 条 partial-action rows 全部 `item_reveal_payload`，其 `source_observed_item_max` 与既有 `action_max` 一致，平均 5.867、最大 25，仍显著低于 settlement inventory。
- exact map-id miss 的 2509、2410 是 numeric-only support-depth 缺口；2408 是 item-reveal partial support-depth 缺口。
- 因此当前 blocker 仍未达到恢复 formal/value sampler 调参或 v3 promotion 的条件。

## D-v3-129：action payload shape/signature 不能作为默认 CSE source-aware prior key

2026-06-07 起，当前决策：

- `source_action_payload_shape_class` 与 numeric action id signature 只能用于 audit matrix，不得接入默认 `v3_cse_*` prior、sampler cap、readiness gate、promotion gate 或正式出价。
- `map_id` 仍是当前最保守的 default support baseline；shape/signature 只能作为后续 source/parser/table acquisition 的解释字段。
- 若后续要把 shape/signature 用成 live/prebid source key，必须先证明它来自 prebid 可见 action/source state，并在 archive/live `model_eval` 中同时提升 recall 与 precision。
- 当前不要为了 shape/signature 小幅 precision 改善牺牲 CSE truth recall，也不要把 post-settlement shape 当作 train-time prior key。

原因：

- source-key holdout 显示 `source_shape` recall 1.0、precision 0.047727，低于 `map_family` precision 0.050119。
- `map_family_source_shape` precision 0.050265，几乎无改善，且 recall 降至 0.904762。
- `map_id_source_shape_signature` precision 提到 0.111842，但 recall 降至 0.809524，miss 从 3 增至 4。
- 2509、2410、2408 仍是 train source support=0 的漏召回样本；shape/signature 不解决 singleton/support-depth blocker。
- 因此当前 blocker 的下一步仍是 source/table acquisition、同 source support 补样或 prebid pressure/source signal，而不是 shape/signature prior 化。

## D-v3-130：CSE support-depth 只能用于 fallback 限流审计，不能直接作为默认 prior

2026-06-07 起，当前决策：

- 对 pure `map_id` CSE candidate，不得简单提高 `min_train_source_rows` 作为默认收窄策略；真实 holdout 显示这会大幅降低 recall 且不提升 precision。
- `map_id -> map_family` fallback 可以增加 support-depth 阈值做 audit-only candidate；当前最有价值的候选是 `all:all min_source>=3` 或 `external:external min_source=1`，覆盖 19/21，precision 0.082251。
- 该候选仍不得接入 `v3_cse_*` 默认 artifact、sampler cap、readiness/promotion gate 或正式出价；后续若要推进，必须先结合 prebid 可见 signal/live model_eval 与更多 support 样本验证。
- 2410 与 2408 仍是 fallback support-depth miss；它们需要新增 source/table acquisition 或同 source support 样本，而不是继续调阈值。

原因：

- pure `map_id all`：`min_source=1` recall 0.857143 / precision 0.089109；`min_source=2` recall 0.47619 / precision 0.071942；`min_source=3` recall 0.333333 / precision 0.077778。
- `map_id -> map_family all:all`：`min_source=1` recall 1.0 / precision 0.050119；`min_source=3` recall 0.904762 / precision 0.082251。
- `external:external min_source=1` 也得到 recall 0.904762 / precision 0.082251，但仍漏 2410 numeric-only 与 2408 partial-action。
- 该矩阵说明 support-depth 有助于限制 broad fallback false positives，但还没有达到可推广 source-aware prior 的证据强度。

## D-v3-131：停止继续扩张 CSE 审计，转入 formal/value promotion workbench

2026-06-07 起，当前决策：

- CSE/source-depth/source-shape 审计已达到 stop-loss 点；除非有新 source parser、活动/远端表或新增实战样本，不再继续盲目添加 CSE key 组合。
- `v3_cse_*` 继续作为 `watch` / support lane，固定 `active=false`、`affects_bid=false`。
- `settlement_count_guarded_bridge_stability` 已通过 `data/processed/v3_scp_guarded_bridge_stability_shadow.json` 固化为已评估状态；当前结论是 `blocked_applied_hurt`，不得作为近期 promotion path。
- 下一阶段主线改为 v3 formal/value promotion workbench：
  - 汇总 CSE、SCP bridge、guarded bridge、tail/under、CCV、residual 等 shadow lanes；
  - 为每条 lane 明确 candidate scope、support depth、holdout status、seed stability、MAE/below/P90/pinball/high-over；
  - 只允许设计 shadow-only formal/value interface 和评估口径；
  - 不恢复正式参数调优、不接入 live/formal、不讨论 promotion。
- 如果 workbench 显示所有候选都 blocked 或 sample-limited，则后续应转向补 targeted samples / source parser / table acquisition，而不是继续参数搜索。

原因：

- CSE `map_family` recall=1.0 但 precision=0.050119，过宽。
- CSE `map_id` recall=0.857143，漏 3 条稀疏/单例。
- support-depth fallback 最好只到 recall=0.904762、precision=0.082251，仍不足以接 sampler。
- Guarded bridge stability 在 seeds 0/1/7 下为 `blocked_applied_hurt`：seed 1 选入 `2501` 并 hurt，seed 7 的 `2506` support 只有 9 applied rows。
- 继续 CSE 微分组不太可能解锁 v3 formal readiness；需要切到候选 lane 组合、stop-loss 和 formal/value shadow interface。

## D-v3-132：v3 practical advisory 作为实战落地入口，先于 formal promotion

2026-06-07 起，当前决策：

- 新增 `v3_practical_*` 作为 v3 的第一层实战落地接口；它必须固定 `active=false`、`affects_bid=false`。
- `v3_practical_*` 只能输出 advisory/reference，不得改变 v2 formal、live UI baseline、正式 bid 或正式出价。
- formal value / underestimate lane 可以在 practical advisory 中提供数值候选 posterior；CSE/SCP broad candidate 只能记录 risk，不得单独触发 `raise_watch`。
- `raise_watch` 只允许由更具体的实战信号触发：formal value candidate、underestimate candidate、CSE pressure、value/capacity guard 或其他明确 guarded candidate。
- UI contract 只能把 `v3_practical` 放在 diagnostics/shadow reference 区域，不能放入 baseline decision 或 official bid 区域。
- 后续 v3 推进先看 practical advisory 在实战样本中的命中/误导情况，再决定是否做更强 sampler 或 promotion readiness；不再继续围绕 CSE/SCP 单 lane 扩审计。

原因：

- 用户已明确要求减少边缘审计，把工作推进到实战可见和可复盘。
- 真实 archive smoke 显示 broad SCP candidate 若直接触发 recommendation，会让 1495/1560 ready rows 都变成 `raise_watch`，实战不可用。
- 收窄后 `v3_practical_candidate_rows=175`、`active_rows=0`，整体 MAE 小幅改善 `-418.757`，below-rate 与 P90 coverage 也微幅正向。
- 该层的价值不是当前立即大幅提精度，而是建立统一实战参考和复盘入口，让后续样本能直接回答“v3 是否真的帮用户避开低估局”。

## D-v3-133：overlay 可显示 v3 practical，但不得替代正式出价卡

2026-06-07 起，当前决策：

- `v3_practical_*` 可以在 live overlay 的 hover/detail 和 alert 中显示，作为“v3 实战参考/低估风险/证据利用”入口。
- compact 主决策卡仍只展示正式 baseline decision 或既有 fallback 低置信参考；不得用 `v3_practical_formal_decision_value_*` 改写正式建议、停止价、防守价或可追价。
- `raise_watch` 可以触发 warning alert，但 alert 文案必须包含“不改正式出价/不影响正式出价”的边界。
- `baseline_passthrough` 状态也应可见，用来说明当前 v3 practical 未触发，而不是字段缺失或 UI 漏显示。
- 若未来要把 v3 practical 从 hover/detail 前置到 compact metrics，仍必须保持 `active=false`、`affects_bid=false`，并单独验证误导率。

原因：

- 用户需要实战可见的低估风险提示，但目前 v3 还没有通过 promotion/readiness gate。
- overlay 是用户实战第一入口；如果 practical 只停留在 `model_eval.jsonl`，无法改善实战决策体验。
- 同时，低估风险提示不能伪装成正式估值，否则会破坏 v2 formal/live/UI 稳定边界，也会让后续指标归因混乱。

## D-v3-134：q6 prior-floor 只能作为 v3 practical P90 上沿 watch

2026-06-07 起，当前决策：

- 当 `v3_prior_q6_expected_value` 显著高于 baseline q6 formal P90 时，可以触发 `v3_practical` 的 `q6_prior_floor_watch`。
- 该 watch 只允许提升 practical P90 / q6 practical P90，不得提升 practical P50，不得影响 formal decision_value，不得影响正式 bid。
- 默认触发阈值为 `prior_q6_expected_value - q6_formal_P90 >= 100,000`。
- 输出必须保持 `active=false`、`affects_bid=false`，recommendation 可为 `raise_watch`，语义是“低估风险/参考上沿”，不是正式加价命令。
- 若未来要把 q6 prior-floor 用作 P50 或正式策略，必须重新做 holdout、误导率、P90 over、实战样本复盘和 promotion gate。

原因：

- archive 对照显示 P90-only prior-floor 能把 practical P90 coverage 从 0.751282 提升到 0.764103，同时 P50 MAE 不变。
- 该信号专门覆盖 q6 gate inactive / q6 prior-low 类低估风险，符合“P90 可承接长尾，但不能带偏整体 MAE”的原则。
- 它也会轻微增加极端上沿风险，因此必须停留在 practical/shadow 显示层。

## D-v3-135：tail replacement 只能作为 practical P90 上沿，不得进入 formal

2026-06-07 起，当前决策：

- `tail_replacement_decision_value_p90` 可以用于 `v3_practical` 的 P90 上沿 watch。
- 默认触发阈值为 `tail_replacement_decision_value_p90 - formal_decision_value_p90 >= 50,000`。
- 该 watch 只允许提升 practical P90，不得提升 practical P50，不得改 formal decision_value，不得进入正式 bid。
- 输出必须保持 `active=false`、`affects_bid=false`；recommendation 可为 `raise_watch`，语义是“长尾替换上沿/低估风险提示”。
- 若后续要使用 tail replacement 影响正式估值，必须另开 promotion gate，并重新验证 MAE、below-rate、P90 over、pinball 和实战误导率。

原因：

- archive smoke 显示加入 tail replacement P90 watch 后，practical P90 coverage 从 0.764103 提升到 0.768590，P50 MAE 不变。
- 这符合此前边界：formal decision_value 仍是裁尾 plannable 口径，tail replacement 是审计/辅助字段。

## D-v3-136：raise-watch 必须用 hit/miss/false-alarm/misleading 作为落地门槛

2026-06-07 起，当前决策：

- `v3_practical_raise_watch_*` 不能只用触发数或 P90 coverage 判断价值。
- 后续所有 practical sampler / watch 候选至少要报告：
  - `hit`: baseline P90 漏，practical P90 覆盖；
  - `miss`: baseline P90 漏，practical P90 仍漏；
  - `false_alarm`: baseline P90 已覆盖但 practical 仍提醒；
  - `extreme_over`: practical P90 相对真值过宽；
  - `misleading`: false alarm 且 extreme over。
- 当前 q6 prior-floor + tail replacement P90 watch 仍只能作为 advisory/reference；不得接入正式出价。
- promotion 讨论必须同时看 MAE、below-rate、P90 coverage、pinball、高估/误导率和 live 样本复盘，不能只看 P90 coverage。

原因：

- 默认 archive smoke 显示当前 practical `raise_watch_rows=347`，P90 coverage 提升到 `0.768590`，但：
  - `hit_rate=0.080692`；
  - `miss_rate=0.317003`；
  - `false_alarm_rate=0.602305`；
  - `misleading_rate=0.230548`。
- 最近 72 小时 live brief 也显示 p50 under-rate 仍高，`raise_watch` 有补漏但不够稳定。
- 因此下一步应转向更具体的 source-aware / random_avg / q6 tail-value practical sampler，而不是扩大 weak watch 或提前 promotion。

## D-v3-137：公开 random avg 作为 v3 practical 下界输入，不进入 formal

2026-06-07 起，当前决策：

- `public random_n_avg_value` 这类公开随机样本均价不能只停留在 diagnostic/UI 字符串；v3 practical 必须能显式读取 canonical evidence event。
- 该信息可用于 practical lower-bound reference：
  - 若 `n * avg` 超过 practical P90 明显阈值，可触发 `raise_watch`；
  - 若只超过 practical P50，则只输出 `ceiling_watch`，不触发 alert。
- 该信号不得改 v2 formal、正式 bid、正式出价，也不得绕过 promotion gate。

原因：

- 用户实战反馈显示使用部分公开/道具信息后估值会严重偏低；审查发现 random avg 在 v3 evidence registry 中是 diagnostic，原 practical 层没有显式消费。
- archive smoke 显示 random avg floor 当前只带来小幅 P50 MAE 改善，不足以 promotion，但不会增加 `raise_watch` 数量。
- 后续所有 source-aware sampler 都应走显式 context 参数或 typed evidence event，不应从 UI 文案或 diagnostics 字符串反推。

## D-v3-138：v3 practical recommendation 必须区分强提醒、上沿和风险

2026-06-07 起，当前决策：

- `raise_watch` 只用于较具体、可给出数值上抬且补漏质量相对更高的实战信号。
- `ceiling_watch` 用于“可显示上沿但不建议直接加价”的 shadow reference，例如 tail replacement P90、archive-learned underestimate repair、random avg P50-only floor、普通 q6 residual value ceiling。
- `risk_watch` 用于无数值移动的 broad risk，例如 capacity/source pressure 或 missing table/value guard；它只能提示证据/容量风险，不应计入强低估提醒。
- `q6_value_ceiling_watch` 可使用 residual/component q6 value 相对 baseline 的差额：
  - 普通阈值：P50/P90 gap 均至少 `100,000`；
  - 强提醒阈值：P50/P90 gap 均至少 `200,000`；
  - practical delta cap 为 `400,000`。
- 以上全部固定 `active=false`、`affects_bid=false`；不得进入 v2 formal、正式 bid 或正式出价。
- 该决策覆盖 D-v3-132/D-v3-135 中把 broad tail/risk 直接标为 `raise_watch` 的早期语义；历史段落保留为演进记录。

原因：

- raise-watch 质量复盘显示旧语义下 `raise_watch_rows=347`，但 hit-rate 只有 `0.080692`，false-alarm rate `0.602305`，misleading rate `0.230548`。
- 新分层后 64-trial archive smoke 显示 `raise_watch_rows=82`，hit-rate `0.280488`，false-alarm rate `0.182927`，misleading rate `0.097561`。
- practical P50 MAE 与 below-rate 同时小幅改善，说明该分层更符合实战：让用户看到上沿和风险，但不把弱证据包装成强加价建议。

## D-v3-139：所有 practical 上沿候选必须报告整体 P90 extreme-over

2026-06-07 起，当前决策：

- 后续任何 `ceiling_watch`、tail/value sampler、q6 prior/tail upshift，都必须同时复盘：
  - `v3_practical_formal_p90_coverage`
  - `v3_practical_formal_p90_extreme_over_rate`
  - `v3_practical_formal_p50_mae`
  - `v3_practical_formal_p50_below_rate`
  - `v3_practical_raise_watch_hit/miss/false_alarm/misleading_rate`
- 若候选只提升 P90 coverage，但显著提高 practical P90 extreme-over，默认不得接入 UI 前台，也不得 promotion。
- q6 pressure multiplier / global q6 tail prior 这类 broad upshift 只能在 source-aware 子集证明收益后再实现；不得全局接入。
- 该规则不影响 v2 formal 或正式出价；它是 v3 practical/shadow 的 stop-loss。

原因：

- 当前 archive smoke 显示 practical P90 coverage 从 formal `0.750641` 提升到 `0.772436`，但 practical P90 extreme-over 也从 `0.305128` 升到 `0.319231`。
- 用户接受合理偏激进上沿，但不能被过宽 P90 持续误导；因此必须把 coverage 和 extreme-over 绑定评估。

## D-v3-140：公开 random avg 高均值只作为 P90 上沿提示

2026-06-07 起，当前决策：

- 当公开 `random_n_avg_value` 的单次均值达到高信号阈值时，v3 practical 可以给出 P90-only ceiling：
  - `avg >= 80,000`；
  - target=`n * avg * 2.5`；
  - formal P90 gap 至少 `100,000`；
  - 单次 practical P90 delta cap=`400,000`。
- 该信号只抬 practical 的 `total_value`、`formal_decision_value`、`tail_replacement_decision_value` P90。
- 不抬 P50，不抬 q6 子字段，不新增 `raise_watch`，不进入 v2 formal、正式 bid 或正式出价。
- 若与 q6 prior floor、random_avg floor、q6 value ceiling 同时出现，可以组合成同一个 practical advisory，但 recommendation 仍按更强的来源决定；高 random avg 自身保持 `ceiling_watch`。

原因：

- archive 对照显示该候选带来小幅干净收益：`v3_practical_formal_p90_coverage` 从 `0.772436` 到 `0.776282`，`v3_practical_formal_p90_extreme_over_rate` 保持 `0.319231`，P50 MAE 不变。
- 高 random avg 证明“当前窗口存在更高价值尾部风险”，但不能证明该风险一定来自 q6，不能直接当作正式出价或 q6 分布移动。
- 该规则服务实战 UI 的参考上沿，避免道具后仍严重低估；promotion 仍需要后续 source-aware sampler 和 holdout 复核。

## D-v3-141：low-support q6 raw-tail ceiling 可进入 v3 practical shadow

2026-06-07 起，当前决策：

- 当 strict posterior 的支持行数过少时，允许 v3 practical 使用 raw q6 value tail 作为 P90-only ceiling：
  - `match_scope == strict`；
  - `n_matched <= 2`；
  - 已存在 tail/value 支持：tail replacement P90 gap 或 formal value floor stress；
  - `q6_value.p90 - q6_formal_decision_value.p90 >= 200,000`；
  - 单次 practical P90 delta cap=`600,000`。
- 该候选可抬 practical total/formal/tail/q6 formal 的 P90，但不得抬 P50。
- recommendation 固定为 `ceiling_watch`，除非它组合在已有 `raise_watch` 来源后；它自身不得新增强提醒行。
- 继续固定 `active=false`、`affects_bid=false`；不得进入 v2 formal、正式 bid 或正式出价。

原因：

- broad q6 pressure/prior multiplier 的 false/extreme 过高，不适合作为实战 sampler。
- low-support raw-tail 条件更贴近真实问题：严格匹配只有 1-2 行时，formal q6 P90 可能被局部近邻裁得过低，而 raw q6 value P90 已经暴露 tail 风险。
- archive 对照显示该候选把 `raise_watch_hit_rate` 从 `0.280488` 提到 `0.353659`，`raise_watch_miss_rate` 从 `0.536585` 降到 `0.463415`，同时 P50 MAE 与 P90 extreme-over 不变。

## D-v3-142：value-stress raw q6 tail 只做受限 P90 ceiling，raw/total 上限只做 UI 参考

2026-06-07 起，当前决策：

- 当 `formal_value` 已判定 `value_floor_stress`，且 raw q6 value P90 明显高于 formal q6 P90 时，允许 v3 practical 追加受限 P90-only ceiling：
  - `q6_value.p90 - q6_formal_decision_value.p90 >= 300,000`；
  - practical P90 delta cap=`300,000`；
  - 只抬 practical total/formal/tail/q6 formal 的 P90；
  - 不抬 P50，不改变 raw q6 value，不进入 v2 formal、正式 bid 或正式出价。
- `v3_practical_*` 必须显式输出 raw/total 上限相对 formal 的差值：
  - `raw_total_gap_to_formal_p90`
  - `q6_raw_gap_to_formal_p90`
  - 对应 baseline gap 与 delta 字段。
- overlay 可以显示 `rawΔP90` / `q6rawΔP90` / `rawP90` / `q6rawP90`，但这些字段只能作为“尾部/仓库上限参考”，不得替换 compact 主决策、defend bid、stop price 或 attack bid。
- 不得把 broad capacity drift、generic raw total P90、generic q6 raw P90 直接 promotion 成 formal recommendation；除非后续 source-aware holdout 同时证明 hit 提升、false/misleading 可控、P90 extreme-over 不恶化。

原因：

- 受限 value-stress ceiling 在 archive smoke 中把 `v3_practical_raise_watch_hit_rate` 从 `0.353659` 提到 `0.451220`，`miss_rate` 从 `0.463415` 降到 `0.365854`，P50 MAE 与 P90 extreme-over 不变。
- 直接把 raw/total P90 当 formal P90 的模拟虽然能覆盖部分 severe miss，但 false/extreme 过高，不适合伪装为实战推荐价。
- 用户实战需要“不要只看到明显偏低的裁尾值”；正确落点是把 raw 上限显示出来，并清楚标注不影响正式出价。

## D-v3-143：q6 prior tail ceiling 只允许作为强 q6 证据下的 practical P90 上限

2026-06-07 起，当前决策：

- 当 `q6_prior_floor_watch` 已触发，且窗口满足以下条件时，v3 practical 可以追加 `q6_prior_tail_ceiling`：
  - map family 为 `villa` 或 `shipwreck`；
  - `q6_present_rate >= 0.90`；
  - `v3_prior_q6_expected_value` 可用；
  - target=`v3_prior_q6_expected_value * 2.5`；
  - target 相对当前 formal q6 P90 的 gap 至少 `100,000`；
  - 单次 practical P90 delta cap=`500,000`。
- 该规则只抬 practical total/formal/tail/q6 formal 的 P90，不抬 P50，不改变 raw q6 value。
- 该规则只组合在已有 `q6_prior_floor_watch` 内，不新增独立 raise-watch 行。
- 继续固定 `active=false`、`affects_bid=false`；不得进入 v2 formal、正式 bid 或正式出价。
- hidden/非目标地图不触发该规则，避免在样本不足地图上放大长尾。

原因：

- archive smoke 中该规则把 `raise_watch_hit_rate` 从 `0.451220` 提到 `0.646341`，`miss_rate` 从 `0.365854` 降到 `0.170732`，P50 MAE 不变。
- 代价是 `raise_watch_extreme_over_rate` 从 `0.146341` 升到 `0.268293`，`misleading_rate` 从 `0.097561` 升到 `0.134146`，整体 practical P90 extreme-over 从 `0.319231` 升到 `0.325641`。
- 因此它符合“实战可以看偏保守上限，但不能当正式报价”的定位；下一步正式 sampler 仍应做 source-aware q6 count/cells/value posterior，而不是继续叠加 broad P90 delta。

## D-v3-144：source-profile practical sampler 必须窄口径逐项接入

2026-06-07 起，当前决策：

- v3 practical 可以基于 `hero + map_id + evidence_profile_key` 接入 source-profile P90-only ceiling，但必须逐条 profile 审核。
- 当前允许规则：
  - key=`ethan|2501|public:random_avg+shape`；`q6_present_rate >= 0.85`；`total_value.p90 - formal_decision_value.p90 >= 100,000`；practical P90 delta=`400,000`。
  - key=`ethan|2506|shape`；`q6_present_rate >= 0.85`；`total_value.p90 - formal_decision_value.p90 >= 100,000`；practical P90 delta=`500,000`。
  - key=`ethan|2401|item+shape`；`shape_anchors >= 33`；practical P90 delta=`1,000,000`；该规则不要求 raw gap 或 q6 present gate，因为当前问题表现为 dense shape evidence 下 q6 posterior 被压低。
  - key=`aisha|2506|item+shape`；`shape_anchors >= 28`；`item_anchors >= 4`；practical P90 delta=`500,000`；该规则用于 dense item+shape 下的 Aisha 沉船低估补漏。
- source-profile rule 只抬 practical total/formal/tail/q6 formal P90，不抬 P50，不改变 raw q6 value。
- source-profile rule 可以叠加在 `bounded_underestimate_repair` 分支上；命中时可把 recommendation 从 `ceiling_watch` 升级为 `raise_watch`，但仍只影响 v3 practical shadow。
- `estimate_shadow_pipeline()` 负责透传 source context，archive/live 不能各自绕过 practical 层实现 profile 规则。
- 所有 source-profile rule 继续固定 `active=false`、`affects_bid=false`，不得进入 v2 formal、正式 bid 或正式出价。

原因：

- 当前规则在 archive smoke 中把 practical P90 coverage 从 `0.796154` 提到 `0.802564`，P50 MAE 不变，整体 practical P90 extreme-over 保持 `0.325641`。
- 规则命中范围窄，72h live brief 不变，说明不会在无关 live 窗口里乱抬。
- 更宽的 profile 集合虽然能覆盖更多 miss，但会引入更多 misleading；因此后续必须按单 profile promotion 到 practical shadow，而不是一次性 broad hero/map multiplier。
- `ethan|2506|shape` 追加后，archive smoke 的 practical P90 coverage 继续从 `0.802564` 提到 `0.807051`，P50 MAE 不变，整体 practical P90 extreme-over 仍保持 `0.325641`；raise-watch hit/miss/false/extreme/misleading 均改善。
- `ethan|2401|item+shape` 的 broad 规则会制造 false/misleading，但 `shape_anchors >= 33` 只命中 6 行且全部是 miss；接入后 archive smoke 的 practical P90 coverage 从 `0.807051` 提到 `0.810897`，P50 MAE 不变，整体 practical P90 extreme-over 仍保持 `0.325641`，raise-watch hit/miss/false/extreme/misleading 继续改善。
- `aisha|2506|item+shape` 的 dense gate 接入后，archive smoke 的 practical P90 coverage 从 `0.810897` 提到 `0.812821`，P50 MAE 不变，整体 practical P90 extreme-over 仍保持 `0.325641`；代价是 `raise_watch_false_alarm_rate` 从 `0.162162` 小幅升到 `0.165217`，但 miss/extreme/misleading 均下降。

## D-v3-145：v3 practical 上沿字段必须贯通 UI contract

2026-06-07 起，当前决策：

- `v3_practical_*` 只要在 model_eval 中计算出来，UI contract 必须保留用于实战判断的上沿字段：
  - baseline/formal `p50/p90` 与 `delta_formal_decision_value_p50/p90`；
  - total raw `p90`、baseline raw `p90`、`delta_total_value_p90`；
  - `raw_total_gap_to_formal_p90` 与 baseline gap；
  - q6 formal `p50/p90`、baseline q6 formal `p50/p90`、q6 formal delta；
  - q6 raw value `p90`、baseline q6 raw `p90`、q6 raw delta；
  - `q6_raw_gap_to_formal_p90` 与 baseline gap。
- overlay 可以显示这些字段为“v3 实战参考 / 低估风险 / 仓库上限”，但必须继续显示 `只读参考，不影响正式出价`。
- `active=true` 或 `affects_bid=true` 仍应在 overlay 中被标为异常；不得因为 UI 展示字段变多而接入正式出价。
- 后续新增 practical sampler 或 flat field 时，必须同步检查：
  - `V3PracticalAdvisoryReport.to_flat_dict()`
  - live/archive `model_eval`
  - `runtime.snapshot.ui_contract_from_artifact()`
  - `scripts/run_live_overlay.py`

原因：

- `run_live_overlay.py` 已支持显示 `ΔP90`、`rawΔP90`、`q6rawΔP90`、detail hover 的 `rawP90/q6rawP90`，但 runtime snapshot 之前只透传了部分字段。
- 这会造成“模型已经算出上沿，但实战 UI 看不到”的断层，违背 v3 practical 的落地目标。
- 本决策只修字段贯通，不改变 v2 formal、正式出价或 practical 数值。

## D-v3-146：top miss 诊断必须并排报告 baseline 与 v3 practical P90

2026-06-07 起，当前决策：

- `summarize_live_windivert_brief.py` 的 `top_p90_misses` 必须同时输出：
  - 正式 baseline `decision_value_p90`；
  - `v3_practical_formal_decision_value_p90`；
  - practical 相对 truth 的残余 under；
  - practical P90 delta、recommendation、source/risk flags。
- 后续调参或复盘不得用 baseline-only top miss 作为“v3 practical 完全失败”的证据；必须区分：
  - formal baseline severe miss；
  - practical 已覆盖；
  - practical 已改善但仍有残余 under；
  - practical 未触发。
- 该口径只影响诊断输出，不改变 v2 formal、正式出价、v3 practical 数值或 promotion gate。

原因：

- 当前 practical shadow 已经会抬高部分严重低估行，但旧 brief 只显示 baseline P90，导致实战复盘时难以判断 practical 的真实贡献。
- 对实战落地更有用的下一步不是重复修已经覆盖的 baseline miss，而是收敛 practical 残余 under、误导率和 extreme-over。

## D-v3-147：q6 prior tail ceiling 采用 75 万 practical P90 delta cap

2026-06-07 起，当前决策：

- `q6_prior_tail_ceiling` 的 shadow-only P90 delta cap 从 `500,000` 调整为 `750,000`。
- 不放宽触发条件：
  - map family 仍必须是 `villa` 或 `shipwreck`；
  - q6 present rate 仍必须达到既有门槛；
  - prior q6 expected value 与 P90 gap 仍必须可用且达标；
  - 仍只抬 v3 practical P90，不抬 P50。
- 该字段只用于 `v3_practical_*` 实战参考，不得接入 v2 formal、正式 bid、defend/attack/stop price 或正式出价。
- 后续不再围绕该 cap 做连续小步精调；除非新增实战样本暴露系统性严重高估或低估，否则把精力转向 UI 信息表达、链路稳定性和更结构化的 source-aware sampler。

原因：

- archive 64-trial smoke 显示：P50 MAE 不变，P90 coverage 小幅提升，raise-watch miss 降低，false_alarm/misleading 不变，extreme-over 只小幅上升。
- 72h live brief 显示：v3 practical P90 coverage 从 `0.67` 提到 `0.75`，extreme-over 保持 `0.19`；Ethan 2501 layout 的 residual under 被覆盖。
- 该改动符合用户当前目标：实战中宁可给出可解释的偏保守上限，也不要长期严重低估；但仍不能把该上限当正式报价。

## D-v3-148：overlay 必须并排展示 formal baseline 与 v3 practical 上沿

2026-06-07 起，当前决策：

- overlay 的 `v3 实战参考` 区块必须用并排口径展示 `正式P90 -> v3P90`，不能只显示 v3 practical P90。
- detail/hover 可以继续显示 `ΔP50/ΔP90/q6P90/rawΔP90/q6rawΔP90`，但必须保留“只读参考，不影响正式出价”。
- alert 中如果出现 v3 practical 低估风险或参考上沿，也必须明确它不改正式出价。
- 后续新增 practical 字段时，至少需要一条链路测试覆盖 `model_eval -> ui_contract -> overlay`。

原因：

- 当前阶段目标是实战可用性，而不是继续细调参数；用户需要快速分清正式出价依据和 v3 practical 风险参考。
- 只显示 v3 practical P90 会放大误读风险：它是上沿/低估风险参考，不是 defend/attack/stop price。
- 并排显示 formal baseline 与 v3 上沿，可以让实战中“模型正式建议偏低，但 v3 提醒低估风险”的场景更可解释。

## D-v3-149：post-game model_eval brief 必须报告 v3 practical shadow 边界与收益

2026-06-07 起，当前决策：

- `summarize_live_model_eval.py --brief` 必须保留 `v3_practical` 聚合块，至少包含：
  - practical rows / available / ready / candidate；
  - `active_rows` 与 `affects_bid_rows`；
  - recommendation、source lane、risk flag 计数；
  - formal P90 与 q6 formal P90 的 baseline vs practical 覆盖变化；
  - raise_watch 的 hit / miss / false_alarm / extreme_over / misleading。
- 该 brief 只服务 post-game 复盘和实战可读性，不改变 v2 formal、正式出价、v3 practical 数值或 promotion gate。
- 如果当前 `model_eval.jsonl` 是旧字段集，`v3_practical.rows=0` 只表示该日志没有对应字段，不得据此判断 v3 practical 失效。
- 旧字段集或空数据时，brief 应保持紧凑，显示 `status=no_v3_practical_fields`、中文 note、rows / available / ready / candidate / active / affects_bid，不打印大段空 P90 子结构。

原因：

- `post_game_live.ps1` 已调用 `summarize_live_model_eval.py --brief`，但旧 brief 只突出 q6 shadow 旧候选，缺少 v3 practical 的正式 baseline vs 上沿对照。
- 当前阶段重点是实战可用性和链路稳定：每局后应能快速看出 practical 是否仍为 shadow-only、是否减少低估、是否引入 misleading/extreme-over。
- 这与 overlay 并排显示 formal baseline / v3 practical 的决策保持一致。

## D-v3-150：overlay v3 practical 字段必须使用实战可读标签

2026-06-07 起，当前决策：

- overlay 可以保留 `v3_practical_*` 内部字段名和 UI contract 结构，但展示文案必须面向实战扫读：
  - confidence 显示为 `置信 高/中/中低/低`；
  - raw total upper gap 显示为 `仓库上限ΔP90`；
  - q6 raw upper gap 显示为 `q6上限ΔP90`；
  - detail 中 raw upper P90 显示为 `仓库上限P90` / `q6上限P90`；
  - source/risk 必须有 `证据` / `风险` 前缀。
- 该决策只改变展示标签，不改变 model_eval、UI contract 字段名、v2 formal、v3 practical 数值或正式出价。

原因：

- 当前目标是实战可用性；`confidence low_medium`、`rawΔP90` 这类内部标签会降低用户判断速度。
- v3 practical 是 shadow-only 上沿参考，显示层必须更清楚地区分证据来源、置信度、仓库上限和只读边界。

## D-v3-151：post-game model_eval brief 必须支持 SinceHours 窗口

2026-06-07 起，当前决策：

- `summarize_live_model_eval.py --brief` 必须支持 `--since-hours`，并在 brief 中输出窗口元数据。
- `post_game_live.ps1` 调用 model_eval brief 时必须传入同一个 `$SinceHours`，与 windivert brief 保持同一复盘窗口。
- v3 practical brief 必须区分：
  - `no_evaluable_rows`：当前窗口没有可评估 model_eval 行；
  - `no_v3_practical_fields`：当前窗口有行，但日志字段集旧或缺少 `v3_practical_*`；
  - `fields_present`：可以聚合 v3 practical。

原因：

- 只对 windivert brief 使用时间窗口、model_eval brief 却读全量日志，会让 post-game 复盘混入旧日志。
- 当前阶段重点是实战链路稳定；窗口不一致会直接干扰“新局是否已进入 v3 practical model_eval 链路”的判断。

## D-v3-152：model_eval brief 必须能定位 v3 practical 具体窗口

2026-06-07 起，当前决策：

- 当 `v3_practical.status=fields_present` 时，brief 除聚合指标外必须保留少量行级复盘：
  - 最近 v3 practical 行；
  - v3 practical P90 仍低估最多的行。
- 行级字段必须包含足够复盘信息：file / hero / map_id / round、recommendation、confidence、source/risk、baseline P90、practical P90、delta、残余 under、q6 P90/under、active/affects_bid。
- 该输出只用于 post-game 诊断，不改变 sampler、formal、UI contract 或正式出价。

原因：

- 聚合指标能说明整体方向，但实战落地需要快速定位“哪一局哪一轮触发、抬了多少、是否仍低估”。
- 这能减少手动翻 `model_eval.jsonl` 的成本，也能更早发现 UI/brief/model_eval 字段断层。

## D-v3-153：post-game CLI 行为必须有端到端测试覆盖

2026-06-07 起，当前决策：

- 对 `post_game_live.ps1` 依赖的 CLI 行为，不能只测试内部 helper。
- `summarize_live_model_eval.py --brief --since-hours` 至少需要测试覆盖：
  - model_eval 行过滤；
  - monitor error 行过滤；
  - window 元数据；
  - v3 practical 行级复盘是否来自选中窗口。

原因：

- 当前实战链路依赖 PowerShell 调 CLI；helper 通过不代表 argparse、默认 error log、窗口过滤和 JSON 输出都正确。
- 该测试覆盖能防止后续维护时再次出现 post-game 两个 brief 窗口不一致。

## D-v3-154：post_game 默认复盘窗口采用 72h

2026-06-07 起，当前决策：

- `scripts/post_game_live.ps1` 默认 `$SinceHours=72.0`。
- 该默认值只影响 post-game 聚合命令；单独运行 `summarize_live_windivert_brief.py` 或 `summarize_live_model_eval.py` 时仍可显式指定窗口。
- 显式传入 `-SinceHours` 必须继续覆盖默认值。

原因：

- 当前 v3 practical 落地判断一直以 72h live/实战窗口作为主要短期复盘口径。
- post-game 默认 24h 容易让用户局后看到的窗口和我们讨论/记录的 72h 指标不一致。

## D-v3-155：live formal 默认进入 v3 practical 实战试用，但不等同 v3 promotion

2026-06-07 起，当前决策：

- live/UI 的正式建议展示默认使用 `formal_mode=v3_practical`。
- v3 practical 通过现有 `recommend_bid_strategy` 统一重算探价、防守价、可追价和停止价，不直接把 tail/risk 单项字段塞进停止价。
- `artifact["bid_rows"]` 表示当前正式建议；v2 原建议必须保留在 `artifact["v2_bid_rows"]`，v3 生成行保留在 `artifact["v3_practical_bid_rows"]`。
- UI contract 必须标明来源：
  - `baseline.source=v3_practical`；
  - `mode=v3_practical_formal_with_v2_reference`；
  - `v2_reference` 可见且 `affects_bid=false`。
- 底层 `build_monitor_artifact_from_*` 默认仍保持 v2，只有 live runner / env / 显式参数才切 v3，避免 archive/brief 离线 paired 对照被默认行为污染。
- 回退方式必须保持简单：`-FormalMode v2` 或 `BIDKING_LIVE_FORMAL_MODE=v2`。

原因：

- 最新 72h prebid 对照显示 v3 practical 改善当前 v2 低估问题：MAE 约 `393k -> 338k`，P90 coverage `0.29 -> 0.62`。
- v3 practical 仍有 over-risk：P90 extreme-over `0.05 -> 0.14`，raise-watch misleading rate `0.11`。
- `summarize_v3_promotion_readiness.py` 仍为 `overall_status=not_ready`，因此只能作为实战试用切换，不能视为 v3 全量 promotion 或 v2 archive 条件满足。

## D-v3-156：live v3 practical 必须对低置信 prior-only raise-watch 做出价 guard

2026-06-07 起，当前决策：

- v3 practical 的 audit 原始字段继续保留，不因 live guard 改写。
- live formal bid row 使用 v3 practical 时，若满足以下条件，必须限制正式 P90/停止价：
  - `recommendation=raise_watch`；
  - `confidence in {low, low_medium}`；
  - 风险旗标来自 `q6_prior_floor_watch`、`q6_prior_tail_ceiling`、`settlement_count_prior_candidate` 或 `capacity_source_candidate`；
  - 没有 `value_floor_candidate`、`random_avg_value_floor_watch`、`q6_value_ceiling_watch`、`source_profile_q6_tail_ceiling` 等更强证据；
  - `P90-P50 >= 100k`。
- guard 后的 row 必须显式记录：
  - `formal_mode_reason=v3_practical_ready_live_guarded`；
  - `v3_practical_live_guard=是`；
  - `v3_practical_unguarded_decision_value`；
  - `v3_practical_live_guard_reason`。

原因：

- 实战发现 Gabriela 2407 低信息局仅由 `q6_prior_floor + settlement_count_prior` 触发时，未保护 P90 会明显过冲。
- 该路径是为减少低估设计的，但在低置信、无强证据场景下不应直接推高正式停止价。
- 保留 audit 原字段可以继续分析低估风险；live guard 只保护用户实战出价。

## D-v3-157：未知/活动地图缺表时 live 不能崩溃

2026-06-07 起，当前决策：

- 当当前 `map_id` 不在本地 BidMap 表中时，live monitor 不进入估值，也不抛出 `KeyError`。
- artifact 必须保留当前状态并标注：
  - `evidence_label=unsupported_map:<map_id>`；
  - `formal_mode_reason=unsupported_map`；
  - `inference_input_constraints.mode=unsupported_map`。
- 不生成正式 bid row，避免未知图表误用旧先验。

原因：

- 0607 实战遇到 map `2527`，本地表缺失导致连续 `KeyError: 2527`，snapshot 退成空白。
- 活动图/新版本地图可能临时出现；缺表时应给出明确状态，而不是打断后续跨局 live 链路。

## D-v3-158：缺表活动沉船可显式借对应旧 shipwreck 表做 live fallback

2026-06-07 起，当前决策：

- 一般未知地图仍按 D-v3-157 输出 `unsupported_map`，不生成估值。
- 对可对齐到旧沉船的活动地图，live 可以使用 explicit temporary alias：
  - `2521-2530 -> 2511-2520` 优先；
  - 如对应 `251x` 本地缺表，再尝试 `2501-2510`；
  - `4521-4530 -> 4511-4520` 优先；
  - 如对应 `451x` 本地缺表，再尝试 `4501-4510`。
- artifact 必须保留原始 `map_id`，并新增：
  - `model_map_id`；
  - `map_alias`；
  - `map_alias_mode`；
  - `inference_input_constraints.map_alias`。
- UI 必须显示映射标签，例如 `活动图 2527->旧沉船 2517`。
- 该 alias 只用于 live artifact 构建；直接 v3 shadow/audit 传入未知 map_id 时仍应报告 prior unavailable。

原因：

- 当前活动样本 likelihood 对比显示 `minus10` 更符合现有观测，且用户实战需要在活动期间有可用参考。
- 直接空白会降低实战价值；但把别名藏在内部又会污染后续调参和审计。
- 显式记录 source/model map 可以让局后复盘区分“真实新表估值”和“借旧沉船表估值”。
