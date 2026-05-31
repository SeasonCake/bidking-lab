# bidking-lab · 决策记录

> 本文件记录项目推进中的工程/建模决策：背景、推荐方案、用户选择、取舍和后续复查点。
> 详细实验数据仍放在 `OBSERVATIONS.md`，总体路线仍放在 `PROGRESS.md`。

---

## 2026-05-30 · v2 推理主干采用 evidence-first 渐进替换

**背景**：Fatbeans JSON 已能提供 runtime/local/item_id/shape/category 等高信息证据，旧 MC 主要靠全局采样后过滤，容易在高信息局出现零匹配或无法表达“已知 item 必须存在”。

**推荐**：不一次性重写全部实时链路，先旁路新增 v2：`EvidenceStore`、`KnownItemAnchor`、`ResidualProblem`、`ConditionalSampler`、`PosteriorReport`。

**用户选择**：认可逐步更换主干，先保存工程 checkpoint，再继续增强约束。

**取舍**：v1 保留作为对照；v2 优先表达证据结构，不立即承诺实战精度。

**复查点**：当 v2 批量评估稳定优于 v1 后，再切换主出价策略默认输入。

## 2026-05-30 · 极端小红货不进入常规实战决策价值

**背景**：批量评估显示部分极端误差来自未被证据命中的 1x1/1x2 百万级红货，例如超跑钥匙。这类物品低概率且形状混杂，若强行推高后验，会让常规出价偏移。

**推荐**：保留 raw `total_value` 作为真实价值后验和风险诊断；新增 `decision_value` 作为实战推荐价值，裁掉未明确识别的 small-and-rare 极端尾部。若抽检或 public item-level 已确认具体 `item_id`，仍计入真实价值。

**用户选择**：认可降低极端低概率物品影响，不把非洲之心、折扇、超跑钥匙等作为常规规划基础。

**取舍**：常规建议更稳健，但如果真实出了极端小红货，`decision_value` 会低于结算真值；这应作为“不可规划收益”，而不是模型错误强行校准。

**复查点**：当实时日志足够多后，检查 `decision_value` 是否更贴近玩家可行动收益。

## 2026-05-30 · 大形状/分类明确的高价值红货不裁尾

**背景**：4x4 屏风/车身、3x4 雷达、3x3 医疗设备等候选能被形状和分类明显收窄，和 1x1 极端红货不同。

**推荐**：不全局压低红货；对 shape+category 明确的证据进入条件采样，提高符合候选被采到的概率。

**用户选择**：认可对 4x4、3x4、3x3 等明确形状做更积极的候选权重。

**取舍**：条件采样会让相关证据影响更强，因此必须保留 `category_target_no_pool_match` 诊断，避免错误分类或不可掉落物品污染后验。

**复查点**：用合成规格和真实 Fatbeans 样本分别评估医疗 3x3、古董/家具 4x4、武器 3x4 对后验的影响。

## 2026-05-30 · 活动兑换物品不作为普通地图候选

**背景**：`1306001` 双蟾纳宝、`1306002` 聚财金盆、`1306003..1306014` 十二生肖类物品会出现在 Item/部分 Drop 条目或活动数据中，但普通地图采样链路不可达。

**推荐**：候选诊断和合成样本默认使用“map-reachable”物品集合，而不是全 Item 表或 raw Drop 引用集合。

**用户选择**：明确要求这些活动兑换/不可掉落物品不加入常规候选。

**取舍**：避免把活动藏品误判为拍卖可出；如果未来活动地图真实接入，需要按地图池重新验证可达性。

**复查点**：若新活动地图上线，重新跑 map-reachable 检查，而不是凭 item_id 前缀永久排除。

## 2026-05-30 · exact bucket 上界先进入 v2 条件采样，但需要回退层

**背景**：`QualityBucketObs.total_cells/count` 在旧过滤层已经按 exact 检查，但 v2 条件采样阶段之前只把它们当 floor 填充，导致先过采样再被过滤，浪费 trials。

**推荐**：把 `total_cells/count` 拆成 `total_cells_exact/count_exact`，`total_cells_min/count_min` 继续作为 lower bound。条件采样填 exact 桶时，只在不越过剩余件数/格数的候选里抽样。

**用户选择**：认可逐步把可信上界接入，而不是所有证据都只按下界处理。

**取舍**：strict exact 让已匹配样本的决策价值误差下降，但 zero-match 变多；这是采样器表达力还不够，而不是 exact 语义错误。

**更新**：已增加 “strict exact 零匹配时降级为 floor” 的 posterior fallback，并在报告里用 `relaxed_exact_bucket_targets:*` 标明哪些约束被放宽。

**更新**：已加入 exact 桶组合采样：当同一品质同时有 exact 件数和 exact 格数时，先求可达组合再采样，降低走进不可达剩余状态的概率。69 份样本 `--trials 300` 下 `relaxed_exact` 从 18 降到 11，`zero_match` 从 7 降到 5。

**更新**：分类/形状 target 现在先于 bucket target 采样，让已知类别轮廓计入 exact 桶已占用量。69 份样本 `--trials 300` 下 `relaxed_exact` 进一步降到 9。

**更新**：layout footprint count 现在会前移为 total draws 下限，减少已知轮廓很多时的无效样本。69 份样本 `--trials 300` 下 `relaxed_exact` 降到 6，decision P50 MAE 约 34.4 万；代价是 `zero_match` 从 5 升到 6。

**复查点**：fallback 使用率已下降；下一轮重点转向 q6 residual、shape-category 条件采样和 layout posterior。layout overlap/重复 footprint 要做可信度分层，避免 Ethan 高约束局被过硬过滤。

## 2026-05-30 · 实时出价主口径切到 decision_value

**背景**：raw `total_value` 保留真实结算价值风险，但会被超低概率小红货和不可规划尾部影响。用户实际出价更需要“当前证据下可行动的稳健价值”。

**推荐**：monitor/bid hint 的主阈值使用 v2 `decision_value`；raw `total_value` 保留在诊断字段中，用来提示爆尾风险。

**用户选择**：认可 UI/出价主显示切到 `decision_value`，同时保留 raw 后验和放宽诊断。

**取舍**：常规追价更稳健；如果真实出了未确认极端尾部，主建议不会为了它追高，但 raw 诊断仍能看到风险。

**复查点**：后续用 `model_eval.jsonl` 同时评估 `decision_value_p50_error` 与 raw `value_p50_error`，再决定 bid v2 阈值。

## 2026-05-30 · 样本规模先服务工程诊断，实时日志再服务校准

**背景**：当前 69 份 Fatbeans 样本已经能暴露主要瓶颈：q6 高价值漏估、layout conflict、fallback 后零匹配。但这些样本覆盖仍偏手工、偏高信息局，不适合直接拟合激进权重。

**推荐**：现阶段用现有样本做工程回归和失败分类；不要为了追 MAE 手动抬高红货概率。等实时/半实时日志持续写入 `model_eval.jsonl` 后，再按英雄、地图族、轮次、证据类型分层校准 q6 residual、layout posterior 和 bid v2 阈值。

**用户选择**：继续推进可用主干，同时考虑后续实时日志自动收集。

**取舍**：短期精度不会靠少量样本硬拟合；长期可避免把手工样本偏差写进实战策略。

**复查点**：当 `model_eval.jsonl` 累积到每个主要英雄/地图族至少 30 份有效结算局，再开始做参数化校准。

## 2026-05-30 · 自动采样先做稳定 JSON watcher，真实时 feed 后续替换

**背景**：用户希望开游戏后自动积累每局日志，而不是每次手动把导出文件交给项目。当前项目已有 source-agnostic monitor，但缺少长期采样所需的稳定文件检测、去重和原始包归档。

**推荐**：短期先把 Fatbeans JSON 目录 watcher 做扎实：游戏前启动 monitor/overlay，Fatbeans 或未来抓包 feed 只要持续写 JSON，项目自动生成 snapshot、session/model/layout logs。真实时网络 feed 后续只要喂同一个 monitor artifact builder，不改日志 schema。

**用户选择**：希望尽可能多采集 100+ 份样本，用于降低极端样本对估计的拉偏。

**取舍**：这不是完整网络直连实时监听，但能先解决“批量打局自动入库”和“日志可恢复”的问题；避免在推理主干还没稳定时同时引入网络抓包复杂度。

**复查点**：如果后续确认 Fatbeans/抓包工具能在游戏运行中自动写增量 JSON，再把 watcher 的处理粒度从“文件完成”扩展到“session 增量 snapshot”。

## 2026-05-31 · 普通 2x2 生肖临时放回 v2 候选

**背景**：用户确认普通 2x2 十二生肖活动仍剩约一周，蓝色品质普通生肖在短期实战中仍可能出现；此前为避免活动兑换污染，已把生肖整体排除出普通候选。

**推荐**：只临时放回 `1306003..1306014` 这批 q3、2x2、低价值普通生肖，并以很小 pool mass 注入基础 MC sampler，让 v2、地图似然和仓库估计共用同一候选口径；`1306001` 双蟾纳宝、`1306002` 聚财金盆、`1306015` 御制祥云生肖盘继续排除。

**用户选择**：认可蓝色品质普通生肖先加入回去，高价值/兑换类生肖仍不作为常规掉落候选。

**取舍**：短期能减少真实抽到普通生肖时的不可达诊断，且低权重/低价值不会明显拉偏估价；代价是活动结束后如果不复查，会让普通 2x2 低价值候选残留在 v2 采样里。

**复查点**：活动结束后一周内复核 `1306003..1306014` 是否仍可实战掉落；如果已取消，移除临时 pool 注入和相关测试口径。

## 2026-05-31 · 唯一形状可升级为 hard anchor，非唯一形状保持软约束

**背景**：新增样本确认 Ethan/公开信息能看到 local+shape；部分质量+形状在当前普通掉落池中唯一，例如 q3 5x4 墙面涂鸦墙、q5 6x3 单人郊游快艇。另一些形状仍有多个候选，例如 q6 4x4 屏风/车身、q6 3x4 外骨骼/雷达。

**推荐**：只在当前 map pool 内 `quality+shape` 或 `quality+shape+category` 唯一时升级为 `KnownItemAnchor`；非唯一形状仍进入条件采样或软评分，不硬锁 item_id。

**用户选择**：认可把墙面涂鸦、金色游艇这类明显唯一物品加入下界/锚点约束，同时避免复杂形状约束扰乱现行推理。

**取舍**：唯一形状能提高确定物品的价值/格数置信度；非唯一形状不硬锁可避免把 4x4 屏风/车身、3x4 雷达/外骨骼误判成单一高价值物。

**复查点**：每次游戏表更新后重新跑 map-reachable 唯一形状扫描；若新增同质量同形状候选，自动锚点应退回软约束。

## 2026-05-31 · 估价类道具按 exact-ish 评分，不作为纯下界

**背景**：Ethan 样本中 `100124` 优品估价出现频繁。旧 v2 把 `value_sum` 当成 value floor，会允许远高于估价值的 q4 样本保留满权重，容易放大价值尾部。

**推荐**：采样阶段继续用 value floor 保证不低估工具读数，后验评分阶段按与估价值的相对偏差降权；暂不做 hard exact，因为离散采样和已知 anchor 组合可能导致真实局被误杀。

**用户选择**：希望优品估价能更准确服务格子/价值估计，先做稳健软约束。

**取舍**：过高样本会降权，Ethan 局价值分布更受估价读数约束；它仍不是完整的“估价反推格子数”模型，后续可基于更多 Ethan 样本做 q4 value+cells 联合校准。

**复查点**：等 Ethan villa/shipwreck 每桶 30+ 有效局后，单独评估 `100124` 读数局的 value P50/P90 覆盖与 zero-match，再决定是否加入更强的 value exact 组合采样。

## 2026-05-31 · 样本缺口按统一地图族口径追踪

**背景**：部分旧样本文件名没有 `villa/shipwreck`，批评估脚本会把 240x/250x 误归为
`map_24xx/map_25xx`，而 live 日志按 `map_id` 归类，导致样本缺口统计不一致。

**推荐**：统一用 `map_id` 判断地图族：240x/340x/440x 归 villa，250x/350x/450x
归 shipwreck，2601 单独归 hidden。主要英雄的 villa/shipwreck 仍以每桶 30 份为校准
门槛；hidden 先按每个英雄 10 份冷启动，不立刻参与主阈值拟合。

**用户选择**：继续补沉船数据，并询问别墅和隐秘是否还需要采样。

**取舍**：别墅样本当前已足够工程诊断，不作为第一优先；沉船主要补 Ethan 缺口；
hidden 样本少但可能是独立地图族，先采少量用于确认分布，而不是直接混入 villa/shipwreck
校准。

**复查点**：当 `collection_readiness.priority_needs` 里 hidden 每英雄达到 10 份后，再决定
隐秘是否需要提高到 30 份，或只作为独立策略分支。

## 2026-05-31 · 实时接入先保留 Fatbeans watcher，不重写监听主干

**背景**：用户希望悬浮窗更像实战工具，并询问是继续接 Fatbeans 实时监测，还是自己写一套
实时监测以便后续迁移。

**推荐**：当前不另写一套并行监听主干。`run_fatbeans_live_monitor.py` 已支持
file / watch-dir / stdin 三种入口，推理边界在 `build_monitor_artifact_from_events` 和
`write_monitor_logs`；后续真实时 feed 只要产出同等 Fatbeans/packet events 或直接喂
stdin payload，就可以复用 snapshot、JSONL 日志和 overlay。短期投入应放在 overlay 可读性、
日志 schema 稳定、以及 feed adapter 契约，而不是再造一个 monitor。

**用户选择**：先美化悬浮窗并接一部分现有 Fatbeans 实时监测，之后再逐步转真实时项目。

**取舍**：继续沿用 watcher 可以马上实战验证 UI 和日志；代价是仍依赖 Fatbeans 导出文件，
不是最终直连。因为 artifact/log schema 已源无关，后续切到真实时 feed 的迁移点集中在
source adapter，不会影响推理层和悬浮窗。

**复查点**：当拿到可稳定增量输出的实时 feed 后，优先实现 `events -> build_monitor_artifact_from_events`
适配器；只有 Fatbeans 输出不再可靠或无法增量化时，才考虑替换 watcher 进程。

## 2026-05-31 · public item-level 上界只接已验证语义

**背景**：新增样本覆盖更多 public-info。用户确认关注“显示站位/占格最高物品”、
“显示品质最高藏品”、随机抽检/展示若干件，以及总件数/总格数等信息是否都进入过滤。

**推荐**：只把跨样本已验证的 item-level public info 升级为全局上界：
`200048` 作为最高品质物品，写入 `max_quality`；`200050` 作为最大占格物品，写入
`max_item_cells`。随机 2/4/6 件展示继续作为具体 item/quality/shape anchor 与
bucket/layout 下界，不把它们携带的均格 value 当整局统计。未确认语义的 public numeric
只保留事实和软诊断，暂不硬写总件数/总格数。

**用户选择**：希望能加入过滤的公开信息都加入，同时避免不确定语义扰乱当前推理。

**取舍**：`max_quality` / `max_item_cells` 能排除明显不可能的样本；不确定 public 数值暂缓硬化，
避免把“随机展示若干件的均格/均价”误当成全局统计导致 zero-match。

**复查点**：后续 hidden 或更多地图族出现新 public-info id 时，先用结算 truth 做语义验证，
再决定 hard/soft 等级。
