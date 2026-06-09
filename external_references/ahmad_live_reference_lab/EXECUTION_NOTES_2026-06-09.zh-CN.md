# Ahmad Live Reference Lab Execution Notes

日期：2026-06-09

本文是 Ahmad/Victor 外援参考支线的执行归纳。目的不是替代主线 `PROGRESS_V3.md`，而是把最近实战、UI 调试、回放审查、样本质量和 v3 promotion 可复用经验先收在支线，后续再择要归并到主线。

当前最新口径以 `HANDOFF_2026-06-09.zh-CN.md` 为准。本文前半段保留了一些按时间记录的旧假设，例如早期把 Victor `100209` 记为 `q4+q5`；该旧假设已被后续实战文本推翻，当前语义统一为 `q4+q5+q6`，字段为 `count_sums.q4q5q6`。

## 分层定位

### L0 主线正式路径

- `src/bidking_lab/**`、主线 live monitor、formal decision、v3 promotion gate 属于主线。
- 本支线不应直接改变正式出价策略，也不应把未完成的 v3 sampler 结论写成 promotion-ready。
- 主线需要吸收的是证据链、UI contract 经验、样本质量标签和 promotion guard，不是外援 UI 的临时实现细节。

### L1 实战可用层

- `Hero Ref` Tk overlay 已可作为 Ahmad/Victor 的实战参考窗口。
- 主三档显示优先来自外援式 `ref_v0` / `ref_prior` / `manual_ref` / `settlement review`。
- 未完成 v3 不进入 Ahmad 主报价、红品区间或风险说明。
- `ref_prior` 可用但必须显式标记：它是缺关键输入时的实用兜底，不是完整 live-ready。

### L2 审计与回放层

- 支线可使用 `.tmp/codex/ahmad_ui_replay/round_carousel.py` 做 round-by-round replay。
- 回放应按出价前窗口标注 `R1 prebid`、`R2 prebid` 等，而不是按 Fatbeans `observed_round` 命名。
- 回放工具只服务审查，不作为正式功能；若后续保留，应迁移为受测脚本并加测试。

### L3 v3 Promotion 借鉴层

- Ahmad/Victor 支线证明了“结构化输入 + 清晰 readiness + 显式 fallback 标识”比盲调 sampler 更容易形成实战信任。
- v3 promotion 应吸收这种分层：formal 值、参考值、回放 review、manual override、settlement truth 必须明确区分。
- 样本数有限，不能把几百局样本的拟合当成主线 promotion 充分条件；需要 guard、holdout、漂移处理和实战解释性。

## 当前可用结论

### UI / Live

- 启动推荐：

```powershell
.\scripts\start_live_windivert_overlay.ps1 -Restart -PortOnly -NoOverlay -PythonPath C:\Python313\python.exe
.\external_references\ahmad_live_reference_lab\start_ahmad_overlay.ps1 -Restart -PythonPath C:\Python313\python.exe
```

- 如果只调试回放，可用 `-Snapshot <path> -LoadExisting -KeepMonitorOnClose`，避免关闭 Hero Ref 时误停 live monitor。
- `start_ahmad_overlay.ps1` 会用 `pythonw.exe` 启 UI，正常情况下不会弹控制台。
- `external_references/**` 被 `.gitignore` 忽略；支线文件改动不会出现在普通 `git status` 中。若要正式留版本，需要后续决定是否 `git add -f` 或迁移到主线可跟踪目录。

### 参考引擎

- Ahmad:
  - `100204` / 等价公开总件是高价值输入；
  - `1002041/1002042/1002043` 是金/紫/蓝均格；
  - `1002044` 是低品质合并件数。
- Victor:
  - `100209` 是紫+金+红件数和，进入 `count_sums.q4q5q6`；
  - 缺 `100209` 时可显示带标记的 `victor_q456_prior` / `ref_prior`，但必须标记先验。
- 手填：
  - 件数字段只接受整数；
  - 均格/总格字段允许小数；
  - 用户填写后应实时更新参考，但不应停掉 live monitor；
  - live 自动刷新不应清空用户已改动的手填值。

### Minimap

- 有真实 shape / footprint / item identity / settlement packet 的项画方块。
- 只有 quality-only、public quality marker、无 shape 的 local/quality 线索画圆点。
- `public_info` 不能一律当 marker：实战中部分公开信息带 shape，应回填 local shape 后画完整 footprint。
- 结算态 summary 和 ref review 优先使用 final settlement truth，避免 public marker 或 bridge 累计证据污染最终件数。

### Stale / Session

- 旧 snapshot 超过 60 秒进入 standby，不继续显示上局价格。
- `phase=settled` 也只短时复盘，不能长期占住主界面。
- VPN/UU 可能导致开局状态或个别 round 缺失。样本评估必须把 no-state capture gap 和模型误差分开。

## 已确认的 Source -> Transform -> Output 映射

### Round / Window 语义

| 概念 | 来源 | 语义 | UI 用途 |
| --- | --- | --- | --- |
| `state.round_no` | Fatbeans state payload | 最新收到/揭示的状态轮次 | 诊断字段，不直接当 prebid 标题 |
| `observed_round` | monitor `_latest_round` | 当前 prefix 里最新可见 state round | 回放审计对照 |
| `action_round` | monitor `_action_round` | 用户即将报价的轮次 | 实战标题和策略轮次 |
| replay `R# prebid` | bid send ordinal | 第 # 次报价之前的推荐窗口 | 回放轮播标签 |

关键纠正：

- 之前临时轮播用 `observed_round` 命名，导致 `R1 prebid` 实际对应 UI `R2`。
- 复查事件流后确认 monitor 的 `action_round = observed_round + 1` 是合理的：例如 state round=1 的道具结果到达后，用户将进行第 2 次报价。
- 轮播脚本已修为按 bid ordinal 命名，并保留 `observed_round` 作为 hover/detail 对照。

验证样本：

- `02_fatbeans_valid_ahmed_2527_5rounds_2527_1388889386641609_0002.json`
- 修复后可轮播：
  - `R1 prebid`: action round 1, observed none
  - `R2 prebid`: action round 2, observed R1
  - `R3 prebid`: action round 3, observed R2
  - `R4 prebid`: action round 4, observed R3
  - `R5 prebid`: action round 5, observed R4
  - `settlement`: settled review

### Settlement Review 语义

- `final_quality_counts` 是结算 truth，优先级高于 public/bridge 累计 constraints。
- settlement review 可以显示 ref replay estimate、final total、final-minus-estimate delta。
- settlement review 不应反向污染 live-ready 输入，不应用作出价前真实窗口。

### Manual Input 语义

- `q5_avg=5.75` 必须进入 `avg_cells.q5`。
- `q5_count=5.75` 必须拒绝，不能截断成 `5`。
- 输出里的 `紫件/金件` 是推断件数范围，不等于用户输入的 `紫均格/金均格`。

## 最近未完全记录的问题

### Detail Scrollbar 抖动

现象：

- 加入小地图 scrollbar 后 detail 窗口出现抖动、底部 footer 被挤压或裁切。

根因：

- 自定义 `SlimScrollbar` 继承 `Canvas`，未设置 `height` 时默认请求高度约 265px，会把 detail minimap 区域撑高。
- detail scrollbar 还会在内容满时自动隐藏/显示，形成 `yscrollcommand -> grid_remove/grid_restore -> layout -> yscrollcommand` 的反馈环。

修复：

- `SlimScrollbar(height=1)`；
- detail 内嵌 minimap scrollbar 使用 `hide_when_full=False`，常驻细 scrollbar；
- detail minimap canvas 高度收敛到 160px，内容内部滚动。

验证：

- 40 次 Tk 刷新只有 1 个布局状态；
- detail 窗口几何稳定；
- footer 显示正常。

### 截图 DPI 误导

现象：

- 用窗口 bbox 截图时，经常只截到一部分 UI，看起来像底部被裁。

原因：

- Tk 逻辑坐标与 Windows 高 DPI 物理像素不一定 1:1。

处理：

- UI 裁切类问题优先用全屏截图 + 几何 introspection 双重验证；
- 不要只凭 bbox 截图下结论。

### 回放进程清理自杀

现象：

- 启动轮播时 PowerShell 命令无输出、进程没启动。

根因：

- 清理旧 `round_carousel.py` 进程时用 `CommandLine -like '*round_carousel.py*'`，当前 PowerShell 命令文本本身也包含这个字符串，把自己杀掉了。

处理：

- 进程清理必须加 `ProcessId -ne $PID`；
- 后续脚本化清理应避免按过宽 CommandLine pattern 杀进程。

### External Reference 改动不可见

现象：

- `git diff` 对 `external_references/ahmad_live_reference_lab/tools/*.py` 无输出。

原因：

- `.gitignore` 第 40 行忽略 `external_references/**`。

后续要求：

- 需要正式保留支线时，先决定是 `git add -f external_references/ahmad_live_reference_lab/**`，还是把最终可维护代码迁移到 tracked 目录。
- 在此之前，支线记录本身也可能不进 git，不能把“写了文档”误认为“已经版本化”。

## 样本质量与评估边界

- 当前样本库存在 valid / mixed / no-state windows 的区别。
- mixed 样本多为 R1 缺状态、R2+ 可用，不应手工伪造 R1。
- VPN/UU 导致的抓包缺口不应计入模型误差。
- 回放工具应按每个 prebid window 检查，而不是只看 final settlement session。
- 只用最终结算样本调价会掩盖“哪一轮、哪条输入导致偏差”的问题。

## 对 v3 Promotion 的启发

### 可迁移

- UI contract 应显式保留 `observed_round`、`action_round`、`phase`、`source_mode`。
- 每个推荐值必须能追溯来源：formal、external ref、prior fallback、manual、settlement review。
- Minimap 需要保留 render mode / layout source / shape_key / local_index，不能在摘要层丢失。
- Public info、tool result、settlement truth 应分阶段使用，不能双计。
- Activity map / prior drift 必须显式打标，fallback 可用于实战但不能自动 promotion。
- 样本评估应按 window 分组：R1-R5 的要求不同，后期窗口应更准，早期窗口应更强调不误导和风险标记。

### 不应迁移

- 不应把 `ref_prior` 作为 v3 sampler 的 formal 替代。
- 不应把支线 UI 的临时布局代码直接合入主线。
- 不应把 Ahmed/Victor 结构化英雄的好表现推广到 Aisha/Ethan 等 tail/q6 难题。
- 不应针对 2527/2409 等单个实战局继续微调参数。

### Promotion 前建议 gate

- `source_mapping_complete`: 公共信息、道具结果、英雄技能、manual、settlement truth 都有字段级 mapping 测试。
- `window_replay_consistent`: 回放窗口标签与 `action_round` 一致，且 settlement 不污染 prebid。
- `fallback_labeled`: 活动图、缺总件、缺 q4q5q6、count prior、map alias 都在 UI 和 evaluator 中明确标记。
- `sample_quality_split`: valid/mixed/no-state 分层评估，capture gap 不算模型误差。
- `overfit_guard`: 不因单个样本改善而提升 formal；需要 map family/session holdout 与 live replay 双验证。

## 2026-06-09 逐轮 UI/ref 映射审计

范围：

- `.tmp/codex/ahmad_ui_replay/watch` 中 6 个 Ahmad/Victor 回放样本；
- 28 个窗口，包括 prebid 和 settlement review；
- 对比对象是当前隔离 `ref_v0/ref_prior/manual_ref` direct engine 输出与 `ahmad_live_panel_server.summarize_snapshot` 的 UI contract。

结果：

- `price_mismatch=0`：prebid 主三档与 direct reference 输出一致；
- settlement review 顶部三卡使用 `估价 / 结算 / 差值`，不是普通三档报价；
- 修复 `0x0027` 等 roundless bidding state 的 `action_round`：无 `round_no` 时按已发送 bid 数推断下一次待出价轮次，Victor 2401 R1 不再显示 `R?`；
- 手填语义抽查通过：`5.75` 放入件数字段会拒绝，放入均格字段会进入 `avg_cells` 并参与 `manual_ref`。

当前 UI 相对 direct reference 更详细：

- 增加 readiness/source 标识：`ref_v0`、`ref_prior`、`ref_waiting`、`settlement`；
- 增加红件、红格、红值、紫/金件数范围；
- 增加小地图 summary、公开信息、品质标记、地图 fallback、轮播标签；
- 增加 settlement truth 与 ref replay estimate 的差值。

不能误判为完整原版一致：

- 当前 `ref_v0` 只是外援式 first-pass reference；
- 尚未完整移植 MapBidCalculator 的 `PopulateComboValues` / `ComposeItemsForQuality` beam search、map-conditioned item composition 和 variance 展宽；
- 因此只能说 UI 与当前 direct `ref_v0/ref_prior` 一致，不能说已经与原版 MapBidCalculator 完全同价。

本轮暴露的推理优化点：

- `count_prior/ref_prior` 在部分局中对新增均格证据不敏感，例如 2527、2407、2410 多轮价格不动；
- 2408 一红高价值尾部严重低估，说明当前按品质均值估红值不足以覆盖高价值单红；
- 2410 结算 review 高估，说明红件 count/cells prior 与实际分布仍需 guard；
- Victor 缺 `100209` 时只能走带标记的 `victor_q456_prior` / `ref_prior`，需要继续验证 live bridge 是否稳定捕获紫+金+红件数。

## 2026-06-09 ref_prior 轻量优化

目标：

- 不重新混入 v3；
- 不追高 2408 这类高价值单红尾部；
- 优先让常规均格、总格、件数证据能温和移动报价、红件/红格、紫金件数/格数显示。

处理：

- 默认格均值对齐原 MapBidCalculator fallback：
  - q1=2.2, q3=2.2, q4=2.4, q5=2.8, q6=3.2；
  - 之前 q4/q5/q6 使用 5/9/12，会把红格和高品格数显示明显放大。
- `count_prior/ref_prior` 不再每个总件数只生成一个固定品质分配：
  - 在品质概率期望附近做窄范围枚举；
  - 固定件数、最小件数、Victor `q4q5q6` 合计继续作为硬约束；
  - prebid 窗口里出现某品质均格时，该品质至少 1 件，settlement replay 仍允许固定 0 件避免历史均格冲突。
- 增加温和的 grid-conditioned value v1：
  - 价值仍以品质均价为主；
  - 已知/拟合均格只按每格约 8% 的品质均价进行上下修正；
  - q1 使用更低 3% 修正；
  - 单品质修正有 cap，避免手填或异常均格导致跳值。

验证：

- 28 个逐轮 UI/ref 窗口：`price_mismatch=0`；
- `combo_cap_hit=0`；
- 单窗口 direct ref 计算最慢约 1.1s，平均约 0.45s；
- 手填字段回归：
  - `金件=5` 接受；
  - `金件=5.75` 拒绝并提示应填均格；
  - `金均格=5.75` 进入 `avg_cells.q5` 并参与 `manual_ref`。

效果摘要：

- 2527 prebid balanced 从 R1 到 R4/R5 变为 `573,752 -> 579,384`，新增均格不再完全钝化；
- 2410 prebid balanced 在新增 q3/q4/q5 均格和总格后从 `349,386 -> 450,605`；
- 红格显示回到更接近实战的数量级，例如 3 红默认约 10 格，而不是旧的 36 格；
- 2408 高价值单红仍低估，这是当前支线刻意不追的尾部风险，应保持显式结算复盘，不作为本次优化目标。

## 2026-06-09 v3 低风险辅助接入

原则：

- v3 不覆盖 `ref_v0/ref_prior` 主三档报价；
- v3 不覆盖 ref 红件数 P10/P50/P90；
- 已确认 footprint / 小地图只作为硬下界和提示；
- v3 posterior 只作为分歧提醒，不参与数值融合。

实现：

- 已知红 footprint 下界：
  - 从 minimap summary 中统计 `quality=q6` 且 `render_mode=footprint` 的 item；
  - 红件数、红格显示只做下界 floor；
  - 例如 2527 R4 已见红 `1件/4格`，ref 红格 `3/6/13` 显示为 `4/6/13`，主报价不变。
- v3 红件/报价分歧：
  - 若 v3 posterior `q6_count_range` 中位数与 ref 红件中位数相差至少 1，只加 `v3红件对照` flag；
  - 若 ref/v3 balanced 价差超过 120,000，只加 `v3价差` flag；
  - q6 提醒会显式写 `仅对照`，避免误以为 v3 已进入报价。

验证：

- 28 个逐轮 UI/ref 窗口：`price_mismatch=0`；
- 2527 R4/R5：
  - price 仍为 ref `579,384`；
  - red count 仍为 ref `1/2/4`；
  - red cells 从 direct ref `3/6/13` 经过已知 footprint floor 显示为 `4/6/13`；
  - risk note: `总件先验；已见红1件/4格`。
- 2410 R4：
  - price 仍为 ref `450,605`；
  - v3 只提示 `ref-v3 balanced=+140,153; main quote keeps ref`。

## 2026-06-09 UI 与手填实时性复核

本轮复核目标：

- 不只检查“能打开”，而是检查 source -> transform -> output 映射；
- 覆盖默认空载、mini、detail、手填启用、手填清空、live 自动填入、常驻小地图跟随；
- 确认外援 ref 主报价仍不被 v3 对照值覆盖。

确认结果：

- 逐轮回放仍为 `28 rows, price_mismatch=0`：
  - prebid 主三档与 direct `run_reference_engine` 输出一致；
  - settlement 三卡仍是 `估价 / 结算 / 差值`，不伪装成 prebid 报价；
  - 右侧 `当前建议` 已增加 `最近` 行，用于显示最近道具/抓包结果，例如 `极品扫描=9`。
- 主线 bridge/round/minimap 回归测试通过 `6 passed`：
  - `action_round` 可处理 roundless bidding state；
  - settlement round lag 不再导致 UI `R?`；
  - Ahmad/Victor structured ref bridge 只采 pre-settlement fields；
  - minimap table shape 仍要求 cell count match。
- UI 状态脚本复核通过：
  - 默认启动为 mini + 空载待机；
  - detail 中手填、证据、参考、小地图、footer 均可见；
  - 手填 dirty 字段不会被 live auto-fill 覆盖；
  - 手填启用后 live monitor 仍可继续更新 `_last_live_summary`，但当前显示保持 manual；
  - 清空手填后回到最新 live summary；
  - 常驻小地图会随主窗口移动。
- Windows DPI 截图注意：
  - 当前环境 Tk 逻辑分辨率与截图物理分辨率比例为 `1.5`；
  - 未缩放 bbox 截图会误裁 UI，视觉 QA 应用缩放后的 bbox 或全屏截图复核。

修复：

- 手填宽约束曾存在两个问题：
  - `total_count + 单个均格` 会跑完整组合枚举，`max_combos=10k` 时可能 cap 偏高；
  - UI 遇到 `combo_cap_hit` 会隐藏报价，用户看起来像“手填无效”。
- 现在 `phase=manual` 且没有填满全部品质件数时，使用 manual-only prior 枚举：
  - 仍保留用户填写的 `total_count` 硬约束；
  - 仍使用用户填写的均格、件数和 `q4q5q6` 约束；
  - 状态显示为 `manual_prior`，flags 显示 `手动输入 / 手动先验`。
- 现在 live 侧如果只有总件数、但没有非零品质件数/品质总格/count-sum 等硬分割证据，会进入 `sparse_exact_prior`，仍是概率先验分裂，不是 `combo_cap_hit` 截断。
- 当前一次基准里，`total_count=33` 约 `0.66s`、`total_count=38 + q5_avg=9.0` 约 `1.12s`、再加 `q3=13` 约 `0.03s`；`manual total_count=21 + total_cells=34 + q4_avg=1.8` 约 `0.08s`，已回到可交互范围。
- 代表验证：
  - 输入 `map=2527, total_count=33, q5_avg=5.75`；
  - 输出 `balanced=577,102`，红件 `1/2/4`；
  - 组合数 `5,223`，耗时约 `0.106s`；
  - 对比完整 58,905 组合的 `balanced=575,791`，差异可接受且满足交互实时性。

仍需注意：

- `ref_prior/count_prior/manual_prior/sparse_exact_prior` 是实战参考，不是完整原版 MapBidCalculator promotion；
- 若用户只填很少信息，UI 应显示 `手动先验`、`总件估计` 或 `宽约束快速`，不能暗示结果已经完全确定；
- 外援支线文件仍在 `external_references/**` 下，被 `.gitignore` 忽略，后续正式留版本需要 `git add -f` 或迁移到 tracked 目录。

## 2026-06-09 活动沉船映射与报价复核

目标：

- 确认 252x 活动沉船是否按对应旧 25xx 沉船取价和估计；
- 确认 UI/ref 输出不是因为活动图缺表而使用错误默认价；
- 区分“映射错误”和“活动先验漂移/白转红导致的真实偏差”。

确认结果：

- 外援 ref 静态映射：
  - `2521..2530` 均映射到 `2501..2510`；
  - 例如 `2527 -> 2507`，price note 为 `nest_price:2047;activity_shipwreck_minus20:2527->2507`；
  - 同一结构化输入下 `2527` 与 `2507` 输出完全一致，`balanced=546,893`、红件 `1/2/4`、红格 `3/6/13`；
  - `2521` 与 `2501` 同样一致，说明活动图取价路径不是低估来源。
- 主线 monitor 活动样本复核：
  - `data/samples/fatbeans_activity_20260605_shipwreck` 下 15 个 252x 活动样本均成功构建；
  - 15/15 都有 `map_alias_mode=activity_shipwreck_minus20`；
  - 无 parse/build error；
  - manifest 已标注该 cohort `affects_bid=false`，只作 activity tuning/reference。
- Ahmad 2527 真实样本：
  - monitor artifact: `map_id=2527`、`model_map_id=2507`、`map_alias_mode=activity_shipwreck_minus20`；
  - R1-R5 外援价约 `573,752 -> 579,384`；
  - 结算总值 `1,005,362`；
  - 结算红品 `3件 / 6格 / 835,750`；
  - prebid 红件范围 `1/2/4` 覆盖最终 `3件`；
  - prebid 红格范围经已见 footprint 下界后为 `4/6/13`，覆盖最终 `6格`。

判断：

- 活动图映射是正确的；当前 2527 报价低估不是“没映射到旧图”造成。
- 红件/红格估计在 Ahmad 2527 样本上没有明显错位，问题主要在红品价值尾部和活动白转红带来的高红总值。
- 活动 252x 样本整体结算红件明显偏高，很多普通主线 q6 range 无法覆盖最终红件；这支持“活动先验漂移”判断，不能把这批样本混进普通沉船 baseline 调参。

边界：

- `4521..4530` 在外援 `AuctionAnalyzer4.13.3` 静态表中没有对应 450x 价表，本轮只确认 252x；若后续出现 45xx 活动图，需要单独补表或确认可否安全降级到 25xx 对应旧沉船。
- 现阶段不为活动高红局追价：Hero Ref 仍以红件/红格和三档参考为主，活动高尾风险通过 `地图 fallback`、`总件估计`、`v3价差/对照` 等标签提示。

## 后续支线待办

1. 将 `round_carousel.py` 从 `.tmp` 临时工具整理成可维护脚本，或明确删除并只保留文档结论。
2. 给 `round_carousel` 增加最小测试：2527 R1-R5 prebid label 与 `action_round` 对齐。
3. 做一次 Ahmad/Victor 回放 UI 截图矩阵：
   - empty/standby；
   - R1 prebid；
   - later prebid；
   - manual active；
   - settlement review；
   - stale snapshot。
4. 若准备打包 exe，先解决 external ignored 与依赖/表文件/UAC/monitor lifecycle 的版本化问题。
5. 后续归并主线时，优先迁移 mapping/gate 文档和测试思想，而不是迁移 UI 具体样式。

## 2026-06-09 手填品质格数与 2401 R5 复核

触发问题：

- 实战 2401 R5 结算态显示红 `5件/20格`，但出价前过程只显示约 `0/1/3` 红件；
- 手填面板只有各品质均格和件数，没有各品质总格；
- `q1` 在外援引擎中是白+绿合并口径，UI 只写“白”容易误解。

复核结论：

- 归档文件：
  `data/logs/live/raw/archive/complete/windivert_2026-06-09_101943_complete_ahmed_2401_2401_1388889417487600.json`
- 该局有 `R1..R5 prebid + settlement` 共 6 个回放窗口；
- R1-R5 出价前没有 Ahmad 英雄技能 `100204` 的 total count，也没有普通道具 `100115 库存清点` 或公开总件数；
- 出价前普通道具可用证据包括金均格、普品均格、普品扫描、极品扫描、蓝/紫/金均格等；
- 由于没有总件数，外援 ref 因此保持 `count_prior`，红件范围 `0/1/3`；
- 蓝件 23、红件 5、红格 20、总件 50、总格 122 是 settlement inventory 后才出现；
- 所以“第五轮仍只有 3 件红”不是 UI 漏用了 exact 红件，而是该样本出价前没有 exact 红件/总件证据。

修复：

- 手填面板新增各品质总格字段：
  - `白绿格 / 蓝格 / 紫格 / 金格 / 红格`
  - `白` 标签改为 `白绿`，和 q1/q2 合并口径一致；
- 手填应用时：
  - `品质件数 + 品质总格` 会自动换算为该品质均格并进入 ref engine；
  - 单独填写品质总格但不填对应件数也有效，作为 exact cells 约束进入 ref engine；
  - 只有同时填写件数与总格时，才派生均格并做一致性校验；
  - 均格与 `总格/件数` 明显矛盾会提示，不静默吞掉；
- ref engine 增加 `quality_cells` evidence：
  - 手填输入可追踪；
  - settlement 的 `final_quality_cells` 会进入 ref evidence；
  - 结算态 direct ref 红格修正为真实 `20/20/20`，不再只靠总格拟合。
- 补充普通道具扫描 action 映射：
  - `100104 普品扫描 -> 白绿总格`；
  - `100105 良品扫描 -> 蓝总格`；
  - `100106 优品扫描 -> 紫总格`；
  - `100107 极品扫描 -> 金总格`；
  - `100108 珍品扫描 -> 红总格`；
  - 这些 exact 总格现在会限制组合枚举，不只是展示。
- 注意来源分层：
  - 普通道具 action：`100104..100120`，包括扫描、均格、库存清点、存量；
  - Ahmad 英雄技能 reveal：`100204/1002041..1002044`，R1 给总件，R2 金均格，R3 紫均格，R4 蓝均格，R5 白绿件；
  - 两者会合并成同类 evidence，但 UI/文档不得把 Ahmad R1 英雄技能叫成 `库存清点` 或 `存量` 道具。

2401 复跑后的修正结论：

- R3 `普品扫描=14` 已进入 `quality_cells.q1=14`；
- R4/R5 `极品扫描=7` 已进入 `quality_cells.q5=7`；
- R5 prebid balanced 从旧口径约 `333,384` 调整为 `328,476`；
- 该局仍没有 Ahmad R1 `100204`、普通道具 `100115 库存清点` 或公开总件数，因此总件数仍走 `count_prior`；
- 所以准确表述应是：该局没有总件数证据，但普通道具给出的品质总格证据已经被使用。

验证：

- 语义正例：
  `蓝件 23 + 蓝格 58 -> 蓝均格 2.521739...`，进入 `avg_cells.q3`；
- 语义反例：
  `蓝件 0 + 蓝格 58` 会返回 `蓝件为0时格数也必须为0`；
  `蓝件 23 + 蓝格 58 + 蓝均格 3.0` 会返回不一致提示；
- UI 截图复核：
  `.tmp/codex/ahmad_ui_manual_cells/detail_manual_cells.png`
  显示 20 个手填字段、footer、小地图和详情面板均未裁切；
- 回放一致性：
  `audit_ui_ref_rounds.py` 对上述 2401 样本 `rows=6 price_mismatch=0`。

## 2026-06-09 Ahmad R1 总件数与手填叠加修正

触发问题：

- 实战 2401 R1 UI 显示 `总件估计/ref_prior`，没有抓到 Ahmad R1 总件数；
- 用户手填后 UI 切到 `manual/manual_ref/manual`，后续实时抓包仍在写 snapshot，但界面不再渲染 live session；
- 手填品质总格被错误要求必须同时填写该品质件数。

复核结论：

- 当前 live raw `data/logs/live/raw/windivert_live.jsonl` 的开局 `0x0021` 帧里实际存在 Ahmad R1 总件数：
  - `state.field6(skill).field1=100204`
  - `field2=204`
  - `field7=39`
- 旧 `_parse_skill_reveal()` 只识别整数字段 `14/12` 与浮点字段 `11/9/10`，漏掉了 `field7`，所以不是 UI 没用该字段，而是 parser 没把 R1 结果解析出来；
- 同局普通道具 `100117 良品存量` 有 send，但没有对应 result 行；这属于该道具结果包缺失/未解析，不能和 Ahmad R1 英雄技能混为一谈；
- `1002041/1002042/1002043` 已正常解析为金/紫/蓝均格。

修复：

- `src/bidking_lab/live/fatbeans.py` 的 `_parse_skill_reveal()` 整数字段候选增加 `field7`；
- 手填品质总格不再要求对应品质件数：
  - 只有 `白绿格=16` 这类输入会进入 `quality_cells.q1=16`；
  - 若同时有 `白绿件`，才派生/校验均格；
- Ahmad Tk overlay 改为 manual overlay：
  - 有 live snapshot 时，手填 structured inputs 合并到最新 live snapshot；
  - 保留当前 hero/map/round/session/minimap/live 状态；
  - 后续 refresh 继续渲染 live+manual overlay，不再卡在孤立 `R手动`；
  - 没有 live snapshot 时才退回纯手动 fallback。

验证：

- focused tests：
  - `test_parse_ahmad_total_count_skill_reveal_from_field7`
  - `test_ahmad_manual_quality_cells_do_not_require_quality_count`
  - `test_ahmad_manual_overlay_keeps_live_context_and_merges_inputs`
- 当前 live raw 复跑：
  - sort 1 reading 解析出 `100204 result=39 field=7`；
  - live batch sort 1 产生 `('session', 'total_item_count')=39`；
  - sort 8/16/24/30 后续 state 也保留该 reveal；
- 手填叠加语义 smoke：
  - `总件 39 + 金均格 4.6667 + 白绿格 16` 输出仍为 `ahmed 2401 R1 bidding session=2401:live`；
  - ref input summary 显示 `总件 39 · 金均格 4.67 · 格数 白绿格 16.0`。

待复核：

- 当前正在运行的 monitor/UI 进程不会自动加载代码改动；下一轮实战前必须重启主 monitor 与 Ahmad overlay；
- 旧归档样本如果需要重新评估 Ahmad R1，需要用新 parser 重跑 archive/post-game 流水线。

## 2026-06-09 Ahmad overlay 生命周期修正

触发问题：

- 用户关闭 Ahmad UI 后，`data/logs/live/monitor.lock` 中的 monitor PID 仍在运行；
- 当前启动方式是主 monitor 使用 `start_live_windivert_overlay.ps1 -NoOverlay`，生命周期应由 Ahmad overlay 接管。

复核结论：

- `start_ahmad_overlay.ps1` 原本只在启动瞬间读取 `monitor.lock`，如果连续运行两条启动命令，存在 monitor.lock 尚未写入的 race，导致 Ahmad UI 没拿到 `--stop-pid-on-exit`；
- Ahmad Tk overlay 原本主要依赖 `root.mainloop()` 退出后的 `finally` 执行清理，关闭按钮没有直接执行清理；
- 如果主 monitor 是管理员进程，而 Ahmad overlay 从普通 PowerShell 启动，关闭 UI 时会因为权限不足无法停止 monitor；当前 PID `7196` 的停止尝试已复现 `AccessDenied`。

修复：

- `start_ahmad_overlay.ps1` 新增默认等待 `monitor.lock` 最多 5 秒，避免连续启动 race；
- 如果发现 monitor lock 且需要关闭 UI 联动停止 monitor，但当前脚本不是管理员，会自动用 UAC 重新以管理员方式启动 Ahmad overlay；
- Ahmad Tk overlay 增加 `_run_exit_cleanup()`，关闭按钮会直接清理 `stop_pids_on_exit` 和 lock，`finally` 只作为兜底且不会重复清理；
- 保留 `-KeepMonitorOnClose`：指定后不接管 monitor 生命周期。

验证：

- PowerShell 脚本语法检查通过；
- `test_ahmad_overlay_user_close_runs_exit_cleanup_once` 覆盖关闭按钮只清理一次；
- focused overlay/manual tests 通过。

## 2026-06-09 普通道具 field7 与 UI 卡死链路

触发问题：

- 实战 2401 R1 使用 `良品存量` 后，游戏内显示“蓝色品质藏品的总数量为13”，但 Ahmad UI 手填区没有填入 `蓝件 13`；
- 随后到 R2 UI 出现 Windows `Python is not responding`；
- 用户确认未开加速器。

复核结论：

- 当前 raw `data/logs/live/raw/windivert_live.jsonl` 中，`100117 良品存量` 的结果实际存在于 state action result：
  - `field8(action).field4=100117`
  - `field7=13`
- 旧 `_parse_action_result()` 只识别整数字段 `14/12` 和浮点字段 `11/9/10`，漏掉了普通道具 action 的 `field7`；
- 因为 `蓝件 13` 没进入 evidence，R1/R2 只剩 `总件38 + 金均格9.0` 这类弱约束，ref engine 枚举空间暴涨；
- 同一 synthetic 证据计时：
  - `总件38 + 金均格9.0`：约 `15-17s`，足以让 Tk 主线程被 Windows 判定未响应；
  - `总件38 + 金均格9.0 + 蓝件13`：约 `0.5s`。

修复：

- `_parse_action_result()` 整数字段候选增加 `field7`；
- 新增 `test_parse_action_count_result_from_field7`；
- 当前 raw 复跑确认：
  - state sort 8/17/25/33 都能解析出 `(100117, 13, field7)`；
  - live batch 产生 `('bucket','3','count')=13`；
  - Ahmad bridge 输出 `counts {'q3': 13}`。

后续防线：

- 不应简单降低 `max_combos`，实测低 cap 会因枚举顺序偏置把 R1 价格拉到 100 万以上；
- 现在优先使用 `manual_prior` / `sparse_exact_prior` 这类可解释的概率先验快路径；如果仍然卡顿，再做 Tk 后台线程/异步 summary，而不是砍组合数。

## 2026-06-09 Victor 100209 与 0 均格口径修正

触发问题：

- 实战 `victor 2404 R3` 中，游戏文本为“紫色、金色、红色藏品6件”“优品均格1.8”“极品均格0”“全均格1.61”；
- 旧 UI/engine 手填仍默认 `ahmed`，且 `100209` 按旧记录进入 `count_sums.q4q5`，导致紫/金/红范围放宽；
- `100113 极品均格` 的 SEND 存在，但原始 REV 0x0027 里没有结果块，导致 UI 未显示金均格 0。

修复口径：

- 以实战文本为准，Victor `100209` 改为 `q4+q5+q6` 合计，进入 `count_sums.q4q5q6`；旧 `q4q5` 仍作为历史兼容输入；
- action/skill result 解析支持 varint `0` 作为合法均格结果，不能再把 0 当缺失；
- 对“已发送数值道具、后续已有状态、但同 action_id 完全无结果行”的情况，生成 `inferred_zero` action result，并在 notes 中标为 `action_<id>_<quality>_*_inferred_zero`；
- `avg_cells.q5=0` 会在 ref engine 中转为 `fixed_counts.q5=0`，避免金件仍出现 `0/2/3`；
- 手填区不再默认 `ahmed`，实时同步可覆盖未手改的 hero/map/total/全均格/紫金红件字段；新增/显示 `全均格`，可由 `全均格 * 总件` 推导总格。

验证：

- 当前 raw `2404:1388889423239322` 前缀重放到 sort 17：
  - `latest_sent=100113 极品均格`；
  - `latest_result=100113 result 0 inferred_zero=True`；
  - `ref_input_summary` 包含 `总件21 · 总格34.00000047683716 · 全均格1.62 · 金均格0.00 · 紫均格1.80 · 件数 金件0 · 紫金红件6`；
  - bidding 态金件范围为 `0 / 0 / 0`，红件范围为 `0 / 1 / 2`；
- 完整结算重放：
  - `count_sums={"q4q5q6": 6}`；
  - 结算回放固定 `q4=5, q5=0, q6=1`；
  - `public_total_avg_cells_target` 被使用并显示；
- focused tests：`tests/test_live_fatbeans.py tests/test_live_monitor.py tests/test_live_overlay.py tests/test_ahmad_ref_engine_public_info.py` 共 `161 passed, 25 skipped`。

后续修正：

- 均格对应规则收紧为“必须对应到可组成的整数总格”，不能再把 `件数 * 均格` 的小数结果直接当作格数；
- 例如 `紫均格=1.8`：
  - `5件` 只允许 `9格`；
  - `4件` / `6件` 不合法，因为 `4 × 1.8 = 7.2`、`6 × 1.8 = 10.8` 不是整数格；
- ref engine 在 count-prior 和 exact-total 两条枚举路径都改为要求 `avg × count` 直接接近整数格，不再接受“一位小数看起来像 1.8”的宽松候选；
- 手填预填只在均格+件数能唯一对应整数格数时才填 `*格`，多解或不确定时保留空格数；手填应用时会拒绝无法对应整数格数的 `均格+件数` 组合；
- ref summary 的均格/件数/格数显示顺序统一为 `白绿 -> 蓝 -> 紫 -> 金 -> 红`。

复验：

- 当前 raw `2404:1388889423239322` 前缀重放到 sort 17：
  - 紫件范围 `5 / 5 / 5`；
  - 紫格范围 `9 / 9 / 9`；
  - 金件/金格固定 `0 / 0 / 0`；
  - 总格范围固定 `34 / 34 / 34`；
- focused tests 更新后：`163 passed, 25 skipped`。

## 最近验证命令

```powershell
C:\Python313\python.exe -m py_compile `
  .tmp\codex\ahmad_ui_replay\round_carousel.py `
  external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py `
  external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py
```

```powershell
C:\Python313\python.exe external_references\ahmad_live_reference_lab\tools\smoke_ahmed_ref_samples.py --format summary `
  .tmp\codex\ahmad_ui_replay\watch\01_fatbeans_valid_ahmed_2403_2rounds_2403_1388889391900123_0022.json `
  .tmp\codex\ahmad_ui_replay\watch\03_fatbeans_valid_victor_2401_4rounds_2401_1388889392145087_0450.json `
  .tmp\codex\ahmad_ui_replay\watch\05_fatbeans_valid_ahmed_2408_3rounds_2408_1388889380928035_0002.json
```

回放轮播：

```powershell
C:\Python313\python.exe .tmp\codex\ahmad_ui_replay\round_carousel.py `
  .tmp\codex\ahmad_ui_replay\watch\02_fatbeans_valid_ahmed_2527_5rounds_2527_1388889386641609_0002.json `
  --snapshot .tmp\codex\ahmad_ui_replay\live\latest_snapshot.json `
  --duration-seconds 60 `
  --step-seconds 10 `
  --n-trials 64 `
  --roi-trials 0 `
  --shadow-trials 0
```

## 2026-06-09 支线窗口收口 checkpoint

本窗口最后一次收口已新增：

- `HANDOFF_2026-06-09.zh-CN.md`：当前 Hero Ref 支线的最新交接、映射表、验证结果、风险和新窗口 prompt；
- `README.zh-CN.md`：已把当前状态从旧 `Victor q4+q5` 口径修正为 `Victor 100209 = q4+q5+q6`，并补充 `field7`、`inferred_zero`、整数格均格约束和当前主线接点说明。

当前支线结论：

- Ahmad/Victor Hero Ref 已具备继续实战验证的基础；
- 关键映射边界已记录：`100204`、`1002041..1002044`、`100209=q4q5q6`、普通道具 `100104..100120`、公开全均格、`field7`、零均格、手填整数/小数和均格到整数格；
- 仍需在新窗口复跑视觉/交互验证，尤其是最新映射修正后的 mini/detail/manual/minimap/live/settlement 状态；
- 另一个窗口的主线 v3 dirty work 不应由本支线窗口清理或回滚；
- 历史上支线目录曾被 `.gitignore` 整体忽略；当前已改为可版本化支线代码，但提交前仍应检查 `git status --short --ignored external_references\ahmad_live_reference_lab`，避免误加 build/dist/cache。

## 2026-06-09 Hero Ref 版本化与 audit 窗口状态复核

本轮复核目标：

- 只推进 Ahmad/Victor Hero Ref 支线；
- 不推进主线 v3 promotion；
- 不回滚另一个窗口的主线改动；
- 把支线从纯 ignored 外部参考调整为可版本化项目代码。

版本化整理：

- `.gitignore` 已放开：
  - `external_references/ahmad_live_reference_lab/*.md`
  - `external_references/ahmad_live_reference_lab/*.ps1`
  - `external_references/ahmad_live_reference_lab/src/*.py`
  - `external_references/ahmad_live_reference_lab/tools/*.py`
- 仍保持 ignored：
  - `external_references/ahmad_live_reference_lab/build/`
  - `external_references/ahmad_live_reference_lab/dist/`
  - `__pycache__/`
  - `*.pyc`
  - 打包 exe 与 PyInstaller 中间产物。
- `docs/upstream_references.md` 与 `docs/PROJECT_STRUCTURE_V3.zh-CN.md` 已区分：
  - 原始外部包仍是 local-only reference；
  - Hero Ref lab 是隔离支线代码，可版本化。

Hero Ref 当前可用状态：

- `field7` 已覆盖 Ahmad skill reveal 与普通 action numeric result；
- Ahmad `100204` R1 总件、`1002041/2/3` 金/紫/蓝均格、`1002044` 白绿件数已进入 structured ref bridge；
- Victor `100209` 语义固定为 `q4+q5+q6`，写入 `count_sums.q4q5q6`；
- 手填 UI 内部控件 key 仍叫 `q4q5_count`，这是历史命名；用户语义和文档必须显示“紫金红件”；
- 品质总格、品质件数、均格、全均格、整数格可达性和 manual overlay 已有测试覆盖；
- 旧 snapshot/settled snapshot 超过约 60 秒应进入 standby，不显示旧局报价；
- 关闭 Hero Ref 时应接管并停止 `monitor.lock` 中的 monitor PID，除非启动时指定 `-KeepMonitorOnClose`。

仍需注意：

- Tk overlay 仍在主线程内运行 ref summary；如果后续再复现 sparse evidence 卡 UI，应做后台 worker/summary cache，或把总件已知但品质分裂稀疏的场景路由到 `sparse_exact_prior`，不应简单降低 `max_combos`；
- `ref_v0/ref_prior/manual_prior` 是 Hero Ref 实战参考，不是主线 v3 promotion；
- 若准备推广 exe，先做依赖冻结、UAC/WinDivert/pydivert 打包、版本署名和全流程 smoke。

另一个 audit 窗口的总体状态：

- 主线 v3 当前仍是 `not_ready`；
- 最新 dirty docs 显示 blocker 已从 CSE/SCP 扩张审计收敛到 source/table/parser requirements；
- 2410 相关链路已经排除：
  - `100105` numeric action 是 q3 total cells，不是 session-capacity；
  - 唯一 session-capacity blocker 缺 exact event source；
  - 0x002D payload 已验证最终库存，但不解释 table cap；
  - payload outer fields 是 metadata-only，不是隐藏 capacity source。
- 下一步主线应查 per-session table version、external overlay table 或 server-side settlement expansion/source transform；
- 不应把这些 audit-only artifact 当成 sampler 参数或 promotion support；
- 本支线提交时可包含这些记录整理，但不要在 Hero Ref 目标里继续展开主线 v3 promotion。

## 2026-06-09 Victor 0 均格与整数格二次复核

本轮针对实战反馈复核：

- Victor `100209` 当前源码语义仍为 `q4+q5+q6`，进入 `count_sums.q4q5q6`；
- `100113` 极品/金均格为 `0` 时会通过 `ui_contract.actions.results` 进入 ref engine，带 `inferred_zero` 的来源标记；
- ref engine 会把 `q5_avg=0` 转成 `fixed_counts.q5=0`，因此金件/金格输出为 `0/0/0`；
- `紫均格=1.8` 当前按精确 `avg × count -> 整数格` 处理，只有 `5件 -> 9格` 合法；`4件` 和 `6件` 会被拒绝；
- `均格 + 格数` 如果能唯一对应整数件数，也会自动回填件数到手填面板并进入 `fixed_counts`；白绿、蓝、紫、金、红都适用；
- 修正 `_fit_grids_to_total_target`：总格 fitting 现在优先用整数可达格数分配给未直接约束的品质；只有找不到精确整数解时才退回旧比例缩放；
- 未直接观测格数/均格的品质，显示用可组成形状 top-3 候选展开，并用总格可行性过滤，避免把 top1 当唯一真实格数；
- 端到端烟测确认 `100209=6 + q4_avg=1.8 + q5_avg=0 + total=21/34` 输出：
  - 紫件 `5/5/5`、紫格 `9/9/9`；
  - 金件/金格 `0/0/0`；
  - 红件 `1/1/1`、红格 top-3 `2/3/4`；
  - 总格 `34/34/34`。

注意：旧 `latest_snapshot.json` 的写入时间早于本轮源码修复，仍可看到历史 `q4q5` 字段和缺 actions contract 的状态。实战前需要重启 monitor 与 Hero Ref overlay，不能用旧运行态判断当前版本。

## 2026-06-09 手动面板跨局清理修复

实战反馈显示，主面板进入结算/待机后手动面板仍保留上一局值，下一局 Victor 开局可能被旧手填或旧自动填充值污染。本轮修复：

- 进入 `settled`、`settled_stale`、`session_ahead`、`monitor_restarted`，或检测到 live `session_id` 变化时，自动取消 manual overlay 并清空手动面板；
- 同一局内不因单条包缺少字段就清空用户手填，避免 live 抖动时丢输入；
- `填入当前` 统一使用 `_manual_values_from_summary`，因此 `均格 + 格数 -> 件数` 推导出的白绿/蓝/紫/金/红件数也会自动填入；
- `context.hero=?` 但 structured/ref evidence 已有 `victor/ahmed` 时，ref engine 和 summary context 都会回填对应英雄，避免首页标题和英雄专属约束走 `?`。

## 2026-06-09 公开品质轮廓约束

复核 post-game 后的当前 `latest_snapshot.json`：顶层 `public_info_rows` 只看到 `200028` 随机 9 件品质 reveal 和 `200009`；其中 `200028` 给出 `Q4x5/Q3x2/Q2x2`，但不带 shape，因此只能作为品质件数下界，不能算紫色总格。

扩大到 raw/archive 后确认用户判断正确：真实样本里确实有 `200001` 全紫轮廓，且带 `shape/local`：

- `20260530_231725_aisha_villa_test_sample21_2rounds_reveal_all_purpleitemscontour.json`：`200001` 全紫 18 件，q4 total cells 46；
- `windivert_2026-06-09_001253_complete_victor_2409_2409_1388889394594492.json`：`200001` 全紫 7 件，q4 total cells 16。

主 live parser 已会把这些 public outline 转成 `field_updates bucket.4.count/total_cells`；本轮 Hero Ref 额外补 `public_info_rows` 兜底，防止支线独立回放或缺 field_updates 时漏用。

冲突处理规则已固定：

- `field_updates` / structured exact 输入优先；
- `public_info_rows` 全桶轮廓只在 exact count/cells 缺失或一致时补充；
- 如果 public outline 与 structured exact count/cells 不一致，只记录 `public_bucket_outline_q*_count_conflict` / `cells_conflict`，不覆盖 exact 值，也不把下界抬到超过 exact 件数；
- `200001/200002/200003` 不再走随机品质 reveal 下界路径，避免同一全桶轮廓被重复解释。

本轮补上全桶轮廓解析边界：

- `200001` 全紫轮廓 -> `fixed_counts.q4`、`min_counts.q4`、`quality_cells.q4`；
- `200002` 全金轮廓 -> `fixed_counts.q5`、`min_counts.q5`、`quality_cells.q5`；
- `200003` 全红轮廓 -> `fixed_counts.q6`、`min_counts.q6`、`quality_cells.q6`；
- 只有全桶轮廓会把 shape/cells 汇总成品质总格；`200026-200029` 随机品质 reveal 即使未来带 shape，也不当作该品质总格，只作为 reveal 下界。
- 随机品质 reveal 的 `min_counts` 已进入 ref evidence，并在输入摘要显示为“下界 白绿≥x，蓝≥x，紫≥x，金≥x，红≥x”；已有 exact 件数的品质不重复显示下界。

这样 UI 手填/自动填入可以拿到对应品质的件数和格数，ref engine 也会把 `quality_cells + fixed_counts` 推导出均格并进入组合约束。

## 2026-06-09 品质件数/总格/均格冲突防护

继续复核“已有紫色 bucket，又收到紫色均格、件数或总格”时发现：手填路径已经会拒绝 `件数 + 总格 + 均格` 不一致，但 ref engine 枚举层在 exact total cells 存在时没有同时校验 avg cells，可能导致冲突证据被静默忽略。

本轮修复为严格交集口径：

- 同一品质如果同时有 `fixed_counts`、`quality_cells`、`avg_cells`，必须满足 `avg * count == total_cells`，且 total cells 必须是可组成格数；
- 同一品质如果只有 `quality_cells + avg_cells`，必须能唯一推出整数件数，否则不再继续给价；
- 冲突会进入 `no_reachable_combo`，并记录 `quality_cells_q*_avg_count_conflict` 或 `quality_cells_q*_avg_cells_conflict`；
- 正常路径不受影响：`count + cells -> avg`、`avg + cells -> count`、`avg + count -> cells` 仍按唯一整数/可达格数推导；
- UI 手填路径仍先在 `_manual_inputs_snapshot` 拒绝冲突，不会把下界 `min_counts` 填成 exact 件数，也不会覆盖用户已手改字段。

语义烟测结果：

- `q4 count=7, cells=14, avg=2.0` -> ok，紫件/紫格固定 `7/14`；
- `q4 count=7, cells=15, avg=2.0` -> `no_reachable_combo`；
- `q4 cells=14, avg=2.0` -> 自动推导 `q4 count=7`；
- `q4 cells=15, avg=2.0` -> `no_reachable_combo`。

验证：

```powershell
C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py
C:\Python313\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_live_fatbeans.py tests\test_live_monitor.py tests\test_live_overlay.py tests\test_ahmad_ref_engine_public_info.py -q
```

最近一次结果：`188 passed, 25 skipped`。

## 2026-06-09 Aisha 白/绿 split 接入

本轮按实战备用工具方向把 Aisha 接入 Hero Ref，但保持估值核心仍为外援 `q1/q3/q4/q5/q6` 五桶模型，不改主线 v3 promotion。

关键口径：

- Aisha 技能 `1001034/1001033/1001032/1001031` 分别对应白、绿、蓝、紫的轮廓+品质；
- 主线 Fatbeans 仍保留原 `bucket.1/2/3/4 count/total_cells` 更新给现有 live state 使用；
- 额外新增 `bucket_split.white/green count/total_cells` 只作为 Hero Ref split 输入，避免 `bucket 1` 在普通道具里表示“白绿合并”、在 Aisha 技能里表示“白色单桶”的语义混淆；
- monitor structured bridge 支持 `hero=aisha/艾莎`，读取 `bucket_split` 到 `split_counts/split_quality_cells/split_avg_cells`；
- white-only 只提升 `q1` 下界，不生成白绿合并 exact；
- white+green 两边都已知时，才折叠成 `fixed_counts.q1` 和 `quality_cells.q1`；
- 如果 split 白/绿与手填或 live 的白绿合并 exact 冲突，进入 `hard_conflict` / `no_reachable_combo`，不继续给价；
- 手填面板新增白/绿均格、件数、格数，同时保留白绿合并字段；白/绿和白绿合并都可填写，冲突由 engine 拒绝；
- `aisha_ref_inputs` 作为 structured 输入别名保留，推荐新路径仍是 `structured_ref_inputs`。

验证覆盖：

- Fatbeans synthetic Aisha 技能输出 `bucket_split.white`；
- monitor bridge 不把同批 Aisha `bucket.1` 重复当作白绿合并 exact；
- ref engine：white-only 为 q1 lower bound；white+green 折叠为 q1 exact；split/merged 冲突为 hard conflict；
- Tk 手填：live summary 可回填白/绿；手填提交会生成 `split_*` 字段；6 列 5 行布局 smoke 字段齐全。

最近一次支线 broad suite：`196 passed, 25 skipped`。

## 2026-06-09 Aisha split floor 与手填合并收口

继续按用户实战反馈复核 Aisha 白/绿拆分输入，重点排查“只知道白色时又填白绿均格”“白绿都已知时是否自动填白绿合计”“旧下界是否干扰新增 split 字段”。

最新口径：

- `bucket_split.white/green` 仍是 Hero Ref 专用 split 输入，不改变主线 `bucket.1` 的白绿合并语义；
- white-only / green-only 不折叠为 `q1` exact，只形成 `q1` 件数下界；
- split 已知格数也会形成 q1 总格下界：如果白色已知 3 件 5 格，而白绿总件数候选为 `C`，则 q1 总格至少是 `5 + (C - 3)`，也就是 `C + 2`；
- 因此 `white_count=3, white_cells=5, q1_avg=1.0` 应为无解，不允许出现白绿总格小于已知白格的组合；
- `white_count=3, white_cells=5, q1_avg=2.0` 可继续走稀疏先验枚举，q1 格数候选会被 split floor 过滤；
- split 自身 `count + cells` 也必须是可组成格数，例如 3 件 2 格直接 hard conflict；
- white+green 两边的 count/cells 都齐全时，engine 才折叠成 `fixed_counts.q1` / `quality_cells.q1` / `avg_cells.q1`；
- 手填 UI 中，如果 q1 合计栏为空或仍是自动填入值，white+green 会自动合并填入 q1 件/格/均格；如果用户已经手填 q1 任一字段，则不覆盖用户输入，冲突交给 engine 在应用时拒绝；
- 下界 `min_counts.q1` 不会被 UI 回填成 q1 exact，也不会填成 white/green exact；只有实际 `split_counts` / `split_quality_cells` 会填入白/绿栏。

Aisha 无总件/总格时保持轻量策略：不把支线 UI 扩成 v3 级别复杂界面，只用 ref engine 现有 `total_count_from_ref_count_prior` 简单先验枚举，作为实战参考并在状态中标记 `count_prior`。

详情窗口做了轻微高度收口：自动详情高度从 `requested_h + 16 / work_h - 40` 调整到 `requested_h + 8 / work_h - 72`，本机 smoke 从 `760x1038` 降到 `760x1030`，不改变布局结构。

验证：

```powershell
C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py src\bidking_lab\live\fatbeans.py src\bidking_lab\live\monitor.py
C:\Python313\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_ahmad_ref_engine_public_info.py tests\test_live_overlay.py -q
C:\Python313\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_live_fatbeans.py tests\test_live_monitor.py tests\test_live_overlay.py tests\test_ahmad_ref_engine_public_info.py -q
```

最近一次结果：focused `87 passed`；支线 broad suite `203 passed, 25 skipped`。Tk 可见窗口 smoke：mini `440x397`，detail `760x1030`，手填字段 27 个，关键字段无缺失。

## 2026-06-09 真实样本回放与 mixed 隔离

继续按 source -> transform -> output 复核 Hero Ref 三英雄路径，并修正一个手填显示精度问题。

新增口径：

- `data/logs/live/raw/archive/complete` 只表示抓包局结算完整，不等于该局可作为正常回归样本；
- 样本校准与正常回归以 `data/samples/fatbeans/fatbeans_valid_*` 或 manifest strict 口径为准；
- `fatbeans_mixed_*` 和已知语义矛盾的 raw complete 同 session 只作为隔离负例，不能拿来调参或证明 Hero Ref 估值错误；
- 手填 UI 与提交路径统一“显示精度容差”：例如真实样本中 `24/13` 显示成 `1.8462`，当同时有 `count=13, cells=24` 时会归一成精确 `24/13`；但一位小数过度四舍五入的 `1.8 * 6 -> 11` 仍会被拒绝，不会静默凑整；
- 该容差同时作用于手填提交和手填栏位的即时自动推导，避免 UI 显示值能提交但不能自动补格/件。

真实回放分层：

- Victor 正例：
  - `fatbeans_valid_victor_2401_4rounds_2401_1388889392145087_0450.json` -> ref ok，manual roundtrip ok；
  - `windivert_2026-06-08_234125_complete_victor_2401_2401_1388889392145087.json` -> ref ok，manual roundtrip ok；
  - `windivert_2026-06-09_142811_complete_victor_2403_2403_1388889432555869.json` -> ref ok，manual roundtrip ok；
  - `windivert_2026-06-09_150827_complete_victor_2404_2404_1388889435016810.json` -> ref ok，manual roundtrip ok。
- Victor 隔离负例：
  - `fatbeans_mixed_victor_2409_3rounds_2409_1388889394594492_0451.json` -> ref `no_reachable_combo`；
  - 同 session raw complete `windivert_2026-06-09_001253_complete_victor_2409_2409_1388889394594492.json` -> ref `no_reachable_combo`；
  - 这局公开/技能路径给出 `q4 count/cells` 与 `q4q5q6 count`，但 settlement truth 不一致，应按 mixed 隔离。
- Ahmad 正例：
  - `windivert_2026-06-09_150304_complete_ahmed_2403_2403_1388889434708260.json` -> ref ok，manual roundtrip ok；
  - `windivert_2026-06-09_143505_complete_ahmed_2404_2404_1388889432974563.json` -> ref ok，manual roundtrip ok；
  - `fatbeans_valid_ahmed_2401_4rounds_2401_1388889378674485_0001.json` -> ref ok，manual roundtrip ok。
- Aisha 正例：
  - `fatbeans_valid_aisha_2404_3rounds_2404_1295018992793264_0056.json` -> split 白/绿、q1 合并、manual roundtrip ok。
- Aisha 隔离提醒：
  - `windivert_2026-06-08_114032_complete_aisha_2401_2401_1367586310770395.json` 对应样本库中的 `fatbeans_mixed_aisha_2401_3rounds_2401_1367586310770395_0035.json`，回放为 `no_reachable_combo`，不能按 raw complete 正例使用。

样本库总览（已在 2026-06-09 从 `data/logs/live/raw` 补齐漏网 unique session 后刷新）：

```text
canonical baseline:
  data/samples/fatbeans
  files=491 parsed_files=491 parse_errors=0 valid_files=461 mixed_files=30 invalid_files=0 usable_metric_files=479 bid_windows=1754 ready_windows=1734 no_state_windows=20 constraint_conflict_windows=0
  activity_range_files=0

canonical + activity reference:
  data/samples/fatbeans + data/samples/fatbeans_activity_20260605_shipwreck
  files=509 parsed_files=509 parse_errors=0 valid_files=479 mixed_files=30 invalid_files=0 usable_metric_files=497 bid_windows=1823 ready_windows=1803 no_state_windows=20 constraint_conflict_windows=0
```

对应 manifest：

- `data/sample_manifests/fatbeans_archive_v3_2026-06-09.json`
- `data/sample_manifests/fatbeans_all_usable_with_activity_2026-06-09.json`
- `data/sample_manifests/fatbeans_organize_plan_2026-06-09.json`
- `data/sample_manifests/fatbeans_activity_organize_plan_2026-06-09.json`
- `data/sample_manifests/fatbeans_activity_shipwreck_2026-06-09.json`
- `data/sample_manifests/fatbeans_discovery_all_sources_2026-06-09.json`

后续新增样本整理顺序：

1. 先运行 `scripts/organize_fatbeans_real_samples.py` 补齐 raw/manual unique session；
2. 再运行 `scripts/organize_fatbeans_activity_samples.py --apply`，把 2521-2530 / 4521-4530 活动图移入 activity cohort；
3. 最后复跑 manifest，确认 default baseline 的 `activity_range_files=0` 或 evaluator 的 `robust_activity_candidate=0`。

strict evaluator 分层烟测：

- 默认 strict：Victor valid + mixed 两文件只进入 `4` 个 ready 窗口；
- 加 `--include-mixed-samples` 后进入 `7` 个 ready 窗口；
- 因此工具层已有 valid/mixed 隔离能力，后续 Hero Ref 回归应默认沿用 strict。

验证：

```powershell
C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py src\bidking_lab\live\monitor.py src\bidking_lab\live\fatbeans.py
C:\Python313\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_live_overlay.py tests\test_ahmad_ref_engine_public_info.py -q
C:\Python313\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_live_fatbeans.py tests\test_live_monitor.py tests\test_live_overlay.py tests\test_ahmad_ref_engine_public_info.py -q
C:\Python313\python.exe scripts\summarize_fatbeans_sample_manifest.py
```

最近一次结果：focused `90 passed`；支线 broad suite `206 passed, 25 skipped`。

## 2026-06-09 全量 Hero Ref valid 样本映射审查

在整理后的 `fatbeans_all_usable_with_activity_2026-06-09.json` 上，针对 Hero Ref 支持的三类英雄重新做 source -> transform -> output 回放审查。口径仍是：默认只把 `fatbeans_valid_*` 当正常回归；`fatbeans_mixed_*` 和同 session 语义矛盾 raw complete 只作隔离负例。

真实样本覆盖：

- valid 支持英雄样本合计 `249`：Ahmad `20`、Aisha `225`、Victor `4`；
- ref 状态：
  - Ahmad：`ok=18`，`no_reachable_combo=2`；
  - Aisha：`ok=224`，`count_prior=1`；
  - Victor：`ok=3`，`no_reachable_combo=1`；
- 3 个 `no_reachable_combo` 都来自 settlement review 后的矛盾约束，不能作为 live 手填/估值失败；Aisha 的 `count_prior=1` 是缺总件数，只能作为缺总件参考态。

字段映射覆盖：

- Ahmad `20/20` 覆盖 `total_count`、`total_grid_target`、`avg_cells`、`quality_cells`、`fixed_counts`、`min_counts`；
- Aisha `224/225` 覆盖 `total_count`、`total_grid_target`、`split_counts`、`split_quality_cells`、`split_avg_cells`；第 `225` 个是缺总件的 `count_prior`；
- Victor `4/4` 覆盖 `total_count`、`total_grid_target`、`avg_cells`、`quality_cells`、`fixed_counts`、`min_counts`、`count_sums.q4q5q6`；
- 当前 valid 支持英雄样本未命中 `200001/200002/200003` 全桶轮廓公开信息，公开轮廓与随机品质 reveal 仍以 focused tests 覆盖，不能声称已被真实支线样本充分覆盖。

手填/UI 状态审查：

- 对所有 `ok` valid 样本，`_manual_values_from_summary -> _sync_manual_derived_fields -> _manual_inputs_snapshot` roundtrip 通过；
- Victor `q5_avg=0` 可正确回填为金件 `0`、金格 `0`，`100209` 正确显示为 `紫金红件`；
- Aisha `bucket_split.white/green` 可回填白/绿分栏；white+green 两边齐全时会自动合并到 q1，但用户已手填 q1 时不覆盖；
- 同一 live `session_id` 的刷新不会覆盖用户 dirty 字段；新 `session_id`、`settled`、`session_ahead`、`settled_stale`、`monitor_restarted` 都会清空 manual overlay 与手填栏；
- context hero 为 `?` 时，server summary 与手填预填都可从 ref evidence 恢复 `victor/aisha/ahmed`。

验证命令：

```powershell
C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py src\bidking_lab\live\fatbeans.py src\bidking_lab\live\monitor.py
C:\Python313\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_ahmad_ref_engine_public_info.py tests\test_live_fatbeans.py::test_victor_numeric_skill_reveal_updates_q4_q5_q6_count_sum tests\test_live_fatbeans.py::test_fatbeans_aisha_skill_emits_split_low_quality_updates tests\test_live_monitor.py::test_structured_ref_inputs_bridge_supports_aisha_split_low_quality tests\test_live_monitor.py::test_structured_ref_inputs_bridge_supports_victor_count_sum tests\test_live_overlay.py::test_ahmad_manual_values_from_live_summary_keep_victor_zero_and_total_avg tests\test_live_overlay.py::test_ahmad_manual_values_from_live_summary_prefills_aisha_split_low_quality tests\test_live_overlay.py::test_ahmad_manual_values_from_live_summary_prefers_supported_evidence_hero tests\test_live_overlay.py::test_ahmad_server_summary_prefers_ref_evidence_hero_when_context_unknown tests\test_live_overlay.py::test_ahmad_manual_inline_derivation_covers_all_qualities_and_totals tests\test_live_overlay.py::test_ahmad_manual_inline_derivation_merges_white_green_only_when_q1_is_empty tests\test_live_overlay.py::test_ahmad_manual_inline_derivation_accepts_display_rounded_avg tests\test_live_overlay.py::test_ahmad_manual_state_auto_resets_on_settlement_and_session_change tests\test_live_overlay.py::test_ahmad_prefill_manual_inputs_uses_derived_quality_counts tests\test_live_overlay.py::test_ahmad_manual_snapshot_allows_total_avg_and_zero_gold tests\test_live_overlay.py::test_ahmad_manual_snapshot_derives_counts_from_avg_and_cells_and_normalizes_hero tests\test_live_overlay.py::test_ahmad_manual_snapshot_accepts_display_rounded_avg_when_count_and_cells_match tests\test_live_overlay.py::test_ahmad_manual_snapshot_rejects_over_rounded_one_decimal_avg tests\test_live_overlay.py::test_ahmad_manual_snapshot_accepts_aisha_split_and_merged_low_quality tests\test_live_overlay.py::test_ahmad_manual_snapshot_keeps_white_only_split_separate_from_q1_avg tests\test_live_overlay.py::test_ahmad_manual_snapshot_rejects_impossible_avg_count_pair tests\test_live_overlay.py::test_ahmad_manual_snapshot_rejects_fractional_avg_count_product tests\test_live_overlay.py::test_ahmad_manual_snapshot_rejects_impossible_avg_cells_pair_without_count tests\test_live_overlay.py::test_ahmad_manual_overlay_keeps_live_context_and_merges_inputs -q
```

结果：focused `46 passed`；全量 valid 支持英雄样本回放无异常，单个样本构建没有超过 2 秒的慢例。未做新的可见 Tk 截图，因为本轮没有修改布局或样式。

## 2026-06-09 收尾：最新实战样本、公开品质 marker 与生命周期检查

最新实战样本已按 strict manifest 口径归并到 `data/samples/fatbeans`：

- `fatbeans_valid_ahmed_2401_3rounds_2401_1402770679435098_0033.json`
- `fatbeans_valid_aisha_2408_4rounds_2408_1402770680577927_0127.json`
- `fatbeans_valid_aisha_2401_5rounds_2401_1402770682839152_0084.json`
- `fatbeans_valid_ahmed_2403_5rounds_2403_1402770683094022_0040.json`
- `fatbeans_valid_victor_2401_5rounds_2401_1402770683332914_0488.json`

定向 manifest：

```text
files=5 parsed_files=5 parse_errors=0 valid_files=5 mixed_files=0 invalid_files=0 usable_metric_files=5
ready_windows=22 no_state_windows=0 constraint_conflict_windows=0 multi_session_files=0
```

当前 `data/samples/fatbeans` 汇总：

```text
files=496 parsed_files=496 parse_errors=0 valid_files=466 mixed_files=30 invalid_files=0 usable_metric_files=484
ready_windows=1756 no_state_windows=20 constraint_conflict_windows=0
```

公开品质 / 宝光软线索小地图口径：

- `public_info + render_mode=marker` 不再因为带有 `shape_key` 被 server 改成 `footprint`；
- Tk 绘制层以显式 `render_mode=marker` 为优先级，画圆点；
- 真实结算、packet item、settlement inventory 仍按 hard footprint 画方块；
- 用最新 Victor 样本 `2401 R3 bidding` 回放确认：`6` 个 `public_info marker`，小地图弹窗显示圆点，不是方块。

生命周期检查：

- 正常 live 启动链路仍是：

```powershell
.\scripts\start_live_windivert_overlay.ps1 -Restart -PortOnly -NoOverlay -PythonPath C:\Python313\python.exe
.\external_references\ahmad_live_reference_lab\start_ahmad_overlay.ps1 -Restart -PythonPath C:\Python313\python.exe
```

- 只有用 `-KeepMonitorOnClose` 启动 Hero Ref 时，关闭 Hero Ref 不会停止 WinDivert monitor；这适合回放/调试，不适合用户正常联动关闭路径；
- 本轮回放窗口使用了 `-KeepMonitorOnClose`，因此不会联动 monitor；
- 收尾检查时 `monitor.lock` 不存在，WinDivert/live monitor 进程不存在，`ahmad_overlay.pid` 是 stale 文件并已清理；`live_status` 仍显示旧 `capture_source_status.json`，只是最后一次状态残留，不代表 monitor 正在运行。

验证：

```powershell
C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py
C:\Python313\python.exe -m pytest --basetemp=.tmp\codex\pytest_hero_ref_overlay_full tests\test_live_overlay.py tests\test_ahmad_ref_engine_public_info.py -q
C:\Python313\python.exe scripts\summarize_fatbeans_sample_manifest.py data\samples\fatbeans\fatbeans_valid_aisha_2401_5rounds_2401_1402770682839152_0084.json data\samples\fatbeans\fatbeans_valid_ahmed_2403_5rounds_2403_1402770683094022_0040.json data\samples\fatbeans\fatbeans_valid_victor_2401_5rounds_2401_1402770683332914_0488.json data\samples\fatbeans\fatbeans_valid_aisha_2408_4rounds_2408_1402770680577927_0127.json data\samples\fatbeans\fatbeans_valid_ahmed_2401_3rounds_2401_1402770679435098_0033.json --json
```

结果：Hero Ref overlay/public-info focused suite `96 passed`；最新五局 manifest 全部 `ready_only`、`valid`。
