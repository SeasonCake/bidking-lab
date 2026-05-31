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

重点看 `collection_readiness.groups` 和 `priority_needs`。默认目标是主要英雄/地图族
30 份有效结算局，隐秘拍卖会先按每个英雄 10 份作为冷启动基线：

- Aisha + villa
- Aisha + shipwreck
- Ethan + villa
- Ethan + shipwreck
- Aisha + hidden
- Ethan + hidden

如果时间有限，优先补 `needed` 最大的桶。当前已有样本较多时，别墅桶通常不再是
第一优先级；沉船用于补足 30 份主桶，隐秘用于确认独立地图族的掉落/出价分布。
`next_sampling_targets` 会把这些缺口按优先级整理成可直接执行的采样目标。

截至 2026-05-31，别墅/沉船的 Aisha 和 Ethan 主桶都已经超过 30 份有效局；
短期最有价值的新样本是：

- Aisha + hidden：先采 10 份有效结算局。
- Ethan + hidden：先采 10 份有效结算局。
- Aisha + shipwreck：再补 10-15 份，优先保留 q6 低估、layout conflict、鉴影/抽检混合局。
- Ethan + shipwreck：再补 5-10 份，优先保留五轮伊森、优品估价、exact cells 较多的局。

hidden 对 q6 residual 有直接帮助，但不要和 villa/shipwreck 混成一个全局红货权重；
它应该作为独立地图族校准“高红先验下，后验应保留多少 q6 residual”的基线。

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

如果 10-15 份样本里 `category_target_count` / `category_exclusion_count` 普遍有值，
就可以进入下一步权重评估；如果普遍为 0，先修采集或解析链路，不急着调模型。
批量评估的 summary 会额外输出 `category_evidence`，列出 target/exclusion 总量、
no-pool-match 数量和最有代表性的样本文件。

短轮成交局不要删除。批量评估会输出 `sample_feasibility`：

- `early_1_2`：保留用于解析验证和实时早期提示。
- `mid_3_4` / `full_5`：优先用于稳定估价校准。
- `calibration_decision_value_mae`：只统计中后期有效局的决策价值误差。

`random_sample_avg_values` 会保留“随机 6/9 件藏品平均价值”这类 public info；
它们当前只做诊断，不作为全库均价或品质桶均价硬过滤。

## 看结果时重点关注

`model_eval.jsonl` 和汇总脚本会记录：

- `q6_false_low_risk`：真实有红货，但后验 q6 样本率过低。
- `q6_below_drop_prior`：原始 Drop 先验 q6 很高，但证据后验 q6 被压得明显过低。
- `q6_p90_misses_truth`：q6 P90 仍低于真实 q6 价值。
- `v2_q6_value_p90_under_by`：q6 P90 低估了多少。
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

现阶段不要用少量样本强行调红货概率。等每个主要英雄/地图族至少 30 份有效局后，再做 q6 residual、layout posterior 和 bid v2 阈值校准。
