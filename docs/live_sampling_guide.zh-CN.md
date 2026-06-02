# 实时日志采样指南

本指南用于收集后续 q6 residual、layout posterior、bid v2 校准所需日志。

## 启动顺序

建议先清理旧 monitor，再启动监听和悬浮窗：

```powershell
cd C:\xiangmuyunxing\biancheng\2026\bidking-lab
.\scripts\stop_live_monitor.ps1
.\scripts\start_live_monitor_overlay.ps1 -WatchDir "C:\Users\shenc\Desktop\bid_king_packages"
```

默认只处理启动后新增或变化的 JSON。需要回放旧目录时才加 `-ProcessExisting`。

如果只想先看悬浮窗样式，不启动监听，可打开内置 demo snapshot：

```powershell
python scripts\run_live_overlay.py --demo
```

当前链路仍需要 Fatbeans 或未来 feed 写出 JSON：

```text
Fatbeans JSON -> monitor watcher -> latest_snapshot.json / model_eval.jsonl / layout_samples.jsonl
```

watch 模式遇到 malformed capture 时会写入 `monitor_errors.jsonl`，并把该文件当前
size/mtime 指纹标到 `processed_files.json` 的 `status=error`，避免同一个坏包在轮询中
反复阻塞队列。文件内容变化后会按新指纹重试；如果要强制重跑旧失败文件，使用 `--reprocess`。
调试采集器时如果希望保留旧的反复重试行为，可加 `--retry-errors`。
`summarize_live_model_eval.py` 默认会读取同目录的 `monitor_errors.jsonl`，在
`monitor_errors` 中汇总错误总数、唯一坏文件指纹、错误类型和最近错误。

## 每局需要保留的信息

- 结算 inventory 必须保留，否则不能算真实价值/q6 误差。
- 尽量保留从 R1 到结算的完整包，尤其是使用鉴影、抽检、明镜、全库透视时。
- 文件名尽量包含英雄、地图族、轮次和主要道具，例如：

```text
ethan_shipwreck_sample31_5rounds_eye_of_clarity.json
aisha_villa_sample32_4rounds_medical_antique_inspection.json
```

## 优先采样缺口

用下面命令查看当前覆盖：

```powershell
python scripts\summarize_live_model_eval.py
```

日常只看 readiness、性能和 q6 shadow 候选状态时可用 compact 输出：

```powershell
python scripts\summarize_live_model_eval.py --brief
```

当候选进入 `candidate_for_review` 后，可直接从现有 live 日志导出 active 样本清单，
不需要重新跑推理：

```powershell
python scripts\summarize_live_model_eval.py --brief `
  --export-shadow-review-dir data\review\q6_shadow_candidates `
  --shadow-review-candidate aisha_deep_floor1 `
  --shadow-review-candidate aisha_hidden_floor15
```

导出目录会包含每个候选的 CSV/JSONL 和 `q6_shadow_candidate_review_summary.json`。
`review_class` 会把 active 行拆成 `active_helped`、`active_still_missed`、
`active_false_positive`、`active_no_q6_control` 和普通 observation，便于逐样本复核。

重点看 `collection_readiness.groups` 和 `priority_needs`。默认目标是主要英雄/地图族
30 份有效结算局；隐秘拍卖会冷启动目标为 Aisha 10 份、Ethan 5 份：

- Aisha + villa
- Aisha + shipwreck
- Ethan + villa
- Ethan + shipwreck
- Aisha + hidden
- Ethan + hidden

如果时间有限，优先补 `needed` 最大的桶。当前已有样本较多时，别墅桶通常不再是
第一优先级；沉船用于补足 30 份主桶，隐秘用于确认独立地图族的掉落/出价分布。
`next_sampling_targets` 会把这些缺口按优先级整理成可直接执行的采样目标。

截至 2026-06-01 晚间，采样目标按 q6 residual boost / live shadow 的新需求调整为：

- Aisha + shipwreck：补 20 份有效结算局，优先保留 q6 低估、layout conflict、鉴影/抽检混合局。
- Ethan + shipwreck：补 20 份有效结算局，优先保留五轮伊森、优品估价、exact cells 较多的局。
- Aisha + hidden：补 10 份有效结算局，用作 hidden 高红先验冷启动基线。
- Ethan + hidden：补 5 份有效结算局，用作 hidden 高红先验冷启动基线。

hidden 对 q6 residual 有直接帮助，但不要和 villa/shipwreck 混成一个全局红货权重；
它应该作为独立地图族校准“高红先验下，后验应保留多少 q6 residual”的基线。

注意区分两个统计块：

- 批评估的 `q6_shadow_reference_coverage` 统计全部可用 JSON，只说明离线参考样本是否覆盖目标。
- live 汇总的 `q6_shadow_sampling_progress` 只统计带 `profile_b5` shadow 字段的新日志，用于判断 shadow 上线后的实战收数进度；旧日志不会计入。
- 新版 live monitor 会同时写三套 shadow：`q6_residual_boost_shadow_*` 继续表示
  `profile_b5`，`q6_residual_deep_floor_shadow_*` 表示 `aisha_deep_floor1`，
  `q6_residual_hidden_floor_shadow_*` 表示 `aisha_hidden_floor15`。
  后两者分别跟踪 Aisha + shipwreck 的深布局 prior-floor 候选、Aisha + hidden 的高红先验候选，
  不改变正式估价或出价。
  汇总脚本的 `q6_shadow_sampling_progress.candidates.aisha_deep_floor1` 会单独统计该候选的
  Aisha shipwreck 收数进度；`candidates.aisha_hidden_floor15` 会单独统计 Aisha hidden
  收数进度。为了避免实时监控过慢，shadow 默认 trials 为
  `min(--n-trials, 80)`；需要更稳定的 shadow P90 时可显式传 `--shadow-trials`。

性能口径也要分清：当前 monitor 是“新 JSON 文件落盘后，同步生成完整 artifact 和日志”，
不是每一帧 UI 都阻塞推理。两套 shadow 都激活的 Aisha shipwreck 样本上，`--n-trials 80`
约 2 秒，`--n-trials 500` 且 shadow cap 80 约 10 秒；其中大头是主路径 500 trials，
shadow 额外约 2-3 秒。实战收数建议先用默认 cap；若要更接近即时 UI，可把 `--n-trials`
降到 80-200，并保留 shadow cap。异步/分批适合后续 UI 需要“先显示 baseline、再补 shadow”
时再做。

后续正式 UI 的推荐方向是分批输出：先同步显示 baseline v2 posterior / bid rows，随后后台补
`profile_b5`、`aisha_deep_floor1` 和 `aisha_hidden_floor15` shadow 结果，并在面板上标记“shadow 更新中/已更新”。
这能保留高质量 shadow 证据，又不会让首屏提示等待完整 shadow。

`latest_snapshot.json` 现在额外提供 `ui_contract`，作为 UI 优先读取的稳定字段边界：

- `ui_contract.baseline`：正式显示与正式出价口径，来自 baseline v2 `decision_value` / `bid_rows`。
- `ui_contract.q6_risk_reference`：q6 先验缺口、实战参考 P90 等黄色风险参考，不改变出价。
- `ui_contract.shadows`：三套 q6 shadow 的只读状态、trials 和 q6 P90；`affects_bid=false`。
- `ui_contract.minimap`：最新 grid batch 的轻量地图数据，包含已知物品位置、尺寸、品质和分类。
- `ui_contract.interaction`：预留 compact / hover / detail 三层交互边界。

UI 可以继续读取完整 artifact 做 debug，但首屏正式决策应优先使用 `ui_contract.baseline`。
shadow 区域只展示为风险参考或诊断状态，不能直接覆盖 `decision_value`、停止价或抢仓上限。
当前 overlay 已能绘制简化 minimap。minimap 默认按游戏近似展示 `10` 列、`130`
格视口，并在契约里预留最高 `250` 格；mini / hover / click detail 继续基于同一契约扩展。
当前 compact MiniMap 只显示品质颜色和空间占位，不显示物品短名、形状编号或局部序号；物品
`item_id` / `item_name` / `shape_key` 仍保留在契约里，后续用于详情与推理审计。
matplotlib MiniMap 当前暂时关闭，工程版 overlay 只保留 Tk MiniMap，避免实时交互引入额外渲染成本；后续若需要图像化分布/地图，可作为异步 detail renderer 重新评估。

人工复核 UI 契约时可导出 compact review：

```powershell
python scripts\export_ui_contract_review.py
```

默认读取 `data/logs/live/latest_snapshot.json`，输出
`data/review/ui_contract/ui_contract_review.csv`、`.jsonl` 和
`ui_contract_review_summary.json`。也可以直接传 Fatbeans 原始样本或目录，例如：

```powershell
python scripts\export_ui_contract_review.py data\samples\fatbeans\aisha_hidden_test_sample1_5rounds.json --n-trials 20 --roi-trials 0 --shadow-trials 20
```

复核时优先看 `review_flags` / `manual_review_focus`、`hero/map_id/round`、
`baseline_*`、`truth_*`、`input_*`、`minimap_*`、`shadow_*` 和性能字段。
`zero_posterior_match` 表示 baseline posterior 采样 `0/N`，overlay 会显示“后验无匹配”，
不能当作正式出价建议。
若 `fallback_active=true`，说明系统额外生成了 `v1_map_prior_zero_match` 低置信参考：
它只按地图先验 MC 和当前出价给一个临时区间/建议，用于引擎优化阶段兜底；不要把它当成
v2 baseline，也不要据此升级 shadow 或调 q6 参数。

判断 shadow 是否可升级，优先看汇总脚本的 `q6_shadow_candidate_readiness`：

- `needs_live_samples`：样本数还没到目标，继续收数。
- `blocked_false_positive`：已有无 q6 误抬，不升级。
- `no_observed_help`：没有观察到修复低估，不升级。
- `candidate_for_review`：样本目标已到、没有 false-positive、且观察到 helped；进入人工复核，不代表自动升级。复核时要看 `helped_rows/helped_rate`、`still_missed_rows/still_missed_rate`、`false_positive_proxy_rows`、激活范围和对应局面截图/事件是否可信。

截至 2026-06-02，`aisha_deep_floor1` 已冻结为正式接入前的风险参考候选：
历史 Aisha shipwreck replay 和定向高 trials 对照都显示正净收益，但它仍只写 shadow，
不修改 baseline posterior、`decision_value` 或 bid hint。`aisha_hidden_floor15` 也继续保持
shadow-only，但 hidden 基本不可能出现 q6=0，不再等待 no-q6 对照；复核重点改为
helped/still-missed、plannable gap band、tail 裁剪、性能和事件/截图可信度。Isabella/Wuqilin 技能细化和鉴影反推暂列
UI 接入阶段支线。

current-schema replay 复核时优先使用隔离日志目录，并在历史样本重放时显式加
`--stable-seconds 0 --process-delay-seconds 0`。默认 `stable-seconds=1` 是为了真实 watch
避免半写入文件，会给每个文件增加等待；它适合实时监听，不适合判断批量 replay 推理性能。
截至 2026-06-02 的低 trials 健康检查：338 份样本中 333 成功、5 个 malformed；
`aisha_hidden_floor15` active 11 行全部 covered，`aisha_deep_floor1` 仍有 10 个
active still-missed，`aisha_villa_floor05` 因 4 个 active no-q6 false-positive 继续 blocked。

若 review 出现 `q6_quality_only_deep_local_risk`，表示系统看到了较深位置的 q6 品质点，
但该红货形状仍未知。此时件数 floor 已能利用该证据，格数尾部仍可能偏保守；优先人工复核
`q6_quality_only_local_count`、`q6_quality_only_deepest_local_index`、
`q6_quality_only_deepest_start_row` 和对应截图/事件。该 flag 只用于收证，不会自动抬高
baseline 或 shadow 出价。

判断是否需要降 trials 或异步化，优先看汇总脚本的性能字段：

- `monitor_processing_seconds_median`
- `monitor_processing_seconds_p75`
- `monitor_n_trials_values`
- `monitor_shadow_trials_values`
- `monitor_roi_trials_values`

## 建议样本类型

每个英雄/地图族里尽量混合以下局面：

- 低信息局：少用道具，只保留自然 public info。
- 常规鉴影局：能源交通、医疗、武器、古董、时尚、数码电子等分类轮廓。
- 抽检局：随机抽检 2 / 4，尽量覆盖 item_id 明确的局。
- 高信息局：明镜之眼、全库透视、品质/格数较完整的局。
- 大仓/小仓局：避免只采中等仓位。

## 鉴影采样优先级

Fatbeans 当前识别的分类鉴影 action 共 10 类：

| action_id | 类别 | 采样优先级 | 主要用途 |
| --- | --- | --- | --- |
| 100158 | 能源交通 | P0 | 超跑钥匙、直升机黑匣子、碳纤维车身、飞行器等 q6 风险 |
| 100156 | 文物古董 | P0 | 永乐、富春山居图、屏风、羊脂玉等 q6/高价值候选 |
| 100160 | 书画古籍 | P0 | 永乐、富春山居图、红木屏风等与古董重叠候选 |
| 100152 | 医疗药品 | P0 | 3x3 呼吸机/诊断仪、1x2 人参、医疗外骨骼 |
| 100154 | 兵装军火 | P0 | 3x4 雷达/外骨骼、2x1 高斯匕首等形状强候选 |
| 100151 | 家具物品 | P1 | 黑盒、屏风、电视等多标签高价值候选 |
| 100157 | 数码娱乐 | P1 | 呼吸机、AI 服务器、GPU 柜、摄影机等重叠候选 |
| 100155 | 珠宝矿藏 | P1 | 黑王子、非洲之心、羊脂玉等尾部风险，更多用于 ceiling |
| 100153 | 时尚潮流 | P2 | 超跑钥匙/摩托/轿跑等尾部和能源交叉验证 |
| 100159 | 食饮珍馐 | P2 | 金枪鱼、人参、冬虫夏草等，优先级低于上面类别 |

第一批有效鉴影样本不用平均覆盖所有类别。建议目标：

- 高质量多鉴影局 10-15 份：用于确认解析、正向 category target 和反向排除是否生效。
- 其中 P0 组合至少 8-10 份：能源、古董/书画、医疗、兵装优先。
- P1 组合 4-6 份：家具+数码、珠宝+古董/医疗，用于黑盒和高尾部候选。
- P2 组合 2-3 份即可：主要作为补充，不要挤占 P0 样本。

推荐每局用 2-3 个鉴影，尽量形成“正向命中 + 反向未命中”的交集。最有价值的组合：

- 能源交通 + 时尚潮流：验证超跑钥匙、摩托、轿跑、能源大件是否被正确收窄。
- 能源交通 + 家具物品/数码娱乐：验证车身、黑匣子、电视/服务器类多标签候选。
- 文物古董 + 书画古籍：验证永乐、富春山居图、屏风、书画古籍交叉候选。
- 文物古董 + 医疗药品/珠宝矿藏：验证“竖 2 格红不是医疗，所以更像羊脂玉/古董珠宝”的反排。
- 医疗药品 + 数码娱乐：验证 3x3 呼吸机/诊断仪这类高价值医疗/数码重叠候选。
- 兵装军火 + 能源交通：验证 3x4 雷达、外骨骼、交通/军火大件候选。
- 家具物品 + 数码娱乐 + 文物古董：验证“家具命中、数码/古董未命中，再结合品质/shape 推黑盒”的黑盒场景。

2026-06-01 新增的两组多鉴影样本可以作为后续对照基线：

- 别墅组合：时尚潮流 + 能源交通 + 家具物品 + 文物古董 + 数码娱乐。
- 沉船组合：医疗药品 + 文物古董 + 时尚潮流 + 能源交通 + 兵装军火。

这两组都属于高价值组合，但如果样本只到 1-2 轮，主要用于验证解析、target/exclusion 是否生成，
不直接参与稳定权重拟合。

采样时优先保留这些形状/品质场景：

- q6 3x3：医疗/数码优先，呼吸机和诊断仪价值差异大。
- q6 3x4：兵装/能源优先，雷达、外骨骼是关键。
- q6 4x4：能源/家具/古董/书画优先，车身和屏风类会影响大局估价。
- q6 2x2：家具/能源/古董/书画/珠宝，候选很多，适合测试多标签交集。
- q6 1x2 或 2x1：医疗/古董/珠宝/兵装，适合测试反向排除。

采样命名建议把用过的鉴影写进文件名，例如：

```text
aisha_villa_sample70_energy_fashion_3rounds.json
aisha_shipwreck_sample71_antique_book_medical_4rounds.json
ethan_shipwreck_sample72_weapon_energy_5rounds.json
```

判断这批鉴影样本是否“够用”，不要只看 MAE，先看日志字段：

- `category_target_count`：大于 0 表示分类命中进入 v2 target。
- `category_exclusion_count`：大于 0 表示同一 known item 的反向排除被记录。
- `shape_target_count`：表示非唯一 shape 约束数量。
- `category_target_no_pool_match`：如果增加，优先检查 action→category 映射或物品 tags。

同一物品被多个鉴影命中时，v2 会按“交集”建模，例如能源+时尚要求候选物品同时具备两个分类；
不会把它当成两件不同物品。

如果 10-15 份样本里 `category_target_count` / `category_exclusion_count` 普遍有值，
就可以进入下一步权重评估；如果普遍为 0，先修采集或解析链路，不急着调模型。
批量评估的 summary 会额外输出 `category_evidence`，列出 target/exclusion 总量、
no-pool-match 数量和最有代表性的样本文件。

短轮成交局不要删除。批量评估会输出 `sample_feasibility`：

- `early_1_2`：保留用于解析验证和实时早期提示。
- `mid_3_4` / `full_5`：优先用于稳定估价校准。
- `calibration_decision_value_mae`：只统计中后期有效局的决策价值误差。

`random_sample_avg_values` 会保留“随机 3/6/9/12 件藏品平均价值”这类 public info；
它们当前不作为全库均价或品质桶均价硬过滤。低于 `20000` 的随机均价仍保留在日志中，
但会从 q6 evidence-profile 路由降为低信号，避免几千银币的噪音让沉船 shadow gate 绕路。
`200036` 已作为紫色品质藏品平均价值的 soft target 接入，不做硬过滤。

## 看结果时重点关注

`model_eval.jsonl` 和汇总脚本会记录：

- `q6_false_low_risk`：真实有红货，但后验 q6 样本率过低。
- `q6_below_drop_prior`：原始 Drop 先验 q6 很高，但证据后验 q6 被压得明显过低。
- `q6_p90_misses_truth`：q6 P90 仍低于真实 q6 价值。
- `v2_q6_value_p90_under_by`：q6 P90 低估了多少。
- `final_q6_decision_value`：裁掉未证据支持极端尾部后的可规划红货 truth。
- `final_q6_trimmed_tail_value` / `final_q6_trimmed_tail_items`：被裁掉的 raw 尾部红货，用于尾部风险复核。
- `final_q6_tail_replacement_value` / `final_q6_tail_replacement_items`：review-only 的同品质同形状普通红替代值；不会进入正式出价。
- `final_q6_decision_value_with_tail_replacement`：`final_q6_decision_value + final_q6_tail_replacement_value`，用于复核“裁 0 是否过保守”。
- `q6_plannable_p90_misses_truth`：q6 decision P90 是否低于可规划红货 truth；shadow 升级优先看这个字段。
- `v2_q6_decision_value_p90_under_by`：q6 decision P90 对可规划红货的低估金额。
- `q6_tail_replacement_p90_misses_truth`：q6 decision P90 是否低于 replacement truth；这是第二审计轴，不直接代表正式出价应提高。
- `v2_q6_tail_replacement_estimate_p90`：实验性 posterior replacement q6 P90，用于看“替代估计口径”本身是否覆盖 truth；正式出价不读它。
- `q6_tail_replacement_estimate_p90_misses_truth`：实验性 replacement estimate 是否仍低于 replacement truth。
- `q6_top_size_band`：最终最高价值物品是否为 q6，以及它是 small/compact/medium/large/huge。
- `layout_conflict`：存在 footprint overlap/overflow。
- `layout_conflict_root`：拆分 `footprint_overlap`、`footprint_overflow`、
  `footprint_count_relaxed` 等空间冲突根因。
  对旧日志，如果保留了 `posterior_diagnostics`，汇总脚本会尽量反推该字段。
- `category_target_count`：分类鉴影/分类证据进入 v2 target 的数量。
- `category_exclusion_count`：分类反向排除的数量。
- `shape_target_count`：非唯一形状约束数量。
- `raw_minus_decision_p90`：raw 上界 P90 比常规 decision P90 高多少，用于识别尾部风险局。
- `relaxed_exact_used`：exact 桶约束被放宽。
- `decision_value_p50_error`：实战决策价值误差。
- `stop_minus_final_value`：停止价和最终价值的差距。

批评估里的 `regular_decision_value_mae` 会排除未被证据支持的极端 tail event，
更接近常规局估价质量；`tail_event_decision_value_mae` 单独观察超跑钥匙、永乐、
黑王子等黑天鹅局，主要用于 ceiling / 风险提示，不直接校准常规 P50。

q6 residual floor 仍是离线实验，不会影响正式悬浮窗估价。补齐 hidden/shipwreck 后可用：

```powershell
python scripts\evaluate_fatbeans_v2_samples.py --trials 80 --q6-residual-floor-ratio 0.5
```

重点看 `q6_residual_floor_experiment.q6_value_p90_coverage` 和 `eligible_no_q6_rows`；
如果覆盖提升明显且误伤无 q6 局很少，再考虑把它转成正式、分地图族的 residual 逻辑。

`summarize_live_model_eval.py` 会输出 `q6_miss_root_causes` 和
`q6_p90_under_by_median`。这两个字段用于判断下一步应该优先调 q6 residual、
shape/category 条件采样，还是先修 layout/root 约束。
如果旧 live 日志缺少 `final_q6_decision_value`，汇总里的 `q6_plannable_*` 会显示为
`null`；需要用新版 monitor 重新采集或重放后再做 shadow 升级判断。

现阶段不要用少量样本强行调红货概率。等每个主要英雄/地图族至少 30 份有效局后，再做 q6 residual、layout posterior 和 bid v2 阈值校准。
