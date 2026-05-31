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
