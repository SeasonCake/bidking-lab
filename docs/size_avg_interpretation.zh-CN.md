# N 格均价解读与推理阈值（100169–100173）

本文档供 live/人工对照；代码实现在 `bidking_lab.inference.size_avg_evidence`。

## 信号下界（是否参与推理）

| 占格 | 道具 ID | 下界（银） |
|------|---------|-----------|
| 1 | 100169 | 2,000 |
| 2 | 100170 | 2,000 |
| 3 | 100171 | 3,000 |
| 4 | 100172 | 5,000 |
| 6 | 100173 | 4,000 |

低于下界：忽略，不当证据。

## 仓位分档（总仓储格数）

| 档位 | 格数范围 | 典型 4 格件数 | 典型 2 格件数 |
|------|----------|---------------|---------------|
| 小仓 | ≤94 | ~7 | ~5 |
| 中仓 | 95–127 | ~10 | ~7 |
| 大仓 | ≥128 | ~13 | ~9 |

前期未知总仓时：只按读数绝对档位解释；有 `100103` 或全库轮廓后可选用上表。

## 锚点单价（Item 表）

| 名称 | 占格 | 单价（约） |
|------|------|------------|
| 黑王子红宝石 | 1 | 300 万 |
| 羊脂白玉籽和田玉 | 2 | 252 万 |
| 百年人参 | 2 | 104 万 |
| 私人直升机黑匣子 | 4 | 169 万 |
| 永乐大典残本 | 4 | 149–155 万 |
| 豪宅管理用黑盒 | 4 | 740 万 |

注意：口语「羊脂玉 ~270 万」指 **羊脂白玉籽（2 格）**，不是 4 格「羊脂玉璧」（~2.7 万）。

## 表 A：锚点 ÷ 件数（稀释后均价）

| n | 飞机匣 | 永乐 | 黑盒 |
|---|--------|------|------|
| 1 | 169 万 | 150 万 | 740 万 |
| 7（小仓） | 24 万 | 21 万 | 106 万 |
| 10（中仓） | 17 万 | 15 万 | 74 万 |
| 13（大仓） | 13 万 | 12 万 | 57 万 |

| n | 羊脂白玉籽 | 百年人参 |
|---|------------|----------|
| 1 | 252 万 | 104 万 |
| 7 | 36 万 | 15 万 |

## 表 B：4 格读数分层（解读用）

| 4 格均价 | 置信度 | 含义 |
|----------|--------|------|
| <3 万 | 高 | 普通填充 |
| 3–8 万 | 中 | 略富 |
| 8–30 万 | 低～中 | 可能 1 飞机/永乐 + 多件便宜货（小仓更可信） |
| 30–80 万 | 中 | 小仓：较像少量顶红；大仓：富池 |
| 150–250 万 | 高 | 很像 1 飞机/永乐（n≤2） |
| ≥500 万 | 高 | 很可能含黑盒主导 |
| ≥650 万 | 很高 | 极像 1 黑盒 |

**不是**「只有 ≥500 万才有黑盒」——黑盒可被稀释到几十万；≥500 万是在 **猜种类** 时偏向黑盒。

## 表 C：2 格 / 1 格读数分层

**2 格**：<8 万常态；80–120 万偏人参；200–350 万偏羊脂白玉籽。

**1 格**：<20 万常态；≥250 万偏黑王子单机（多件时可稀释到十几万仍可能有黑王子）。

## 代码中的强度

| 条件 | 行为 |
|------|------|
| 读数 < filler 上限（4 格 30 万等） | 仅软加权 |
| 全库透视 / Ethan 1002085 轮廓齐全 + 件数对齐 | `count_exact`，均价+件数联合约束 |
| 高价 + `count_exact` + 锚点匹配或高档位 | `hard_floor`：该占格 `value_sum` 下界（仍不进 quality bucket） |

诊断字段示例：`size_bucket:4:avg=120000:tier=plane_yongle_singleton:strength=hard_floor:wh=small:count_exact=2:anchor=plane_box:value_floor=...`

## 采样策略评估（2026-06）

| 策略 | 做法 | 结论 |
|------|------|------|
| **score_only**（默认） | 整仓 MC，trial 后用占格均价/件数打分 | 有全库轮廓+总件数时匹配率可达 100%；**不会**改变布局/总格抽样结构 |
| **prefill**（实验） | 先在 sampler 内放入 `count_exact` 占格件，再抽剩余 | 与 score_only 在「有轮廓」场景下总价 MAE 接近；件数更稳 |
| **pool_mask**（实验） | 残差阶段把该占格从池子概率清零 | 易破坏「件数+总格」联合填充，无轮廓时匹配率仍很低；**不推荐**默认 |

**不要**：从掉落池永久删除某占格再单独估总价——会扭曲品级 bucket、布局 footprint、总仓储格数等联合约束。

对比脚本：`python scripts/compare_size_bucket_sampling_modes.py --footprint 4 --n-trials 120`

实验开关：`estimate_posterior_v2(..., size_bucket_prefill=True)` 或 `size_bucket_mask_residual_pool=True`（仅试验）。

## Live 验收（P1）

- 后验诊断应含 `size_bucket:4:avg=...:tier=...`（见 `model_eval.posterior_diagnostics` 或 overlay **N格均价** 区）。
- 汇总对比（有/无四格均价道具 `100172` 的 P50 误差）：

```powershell
python scripts/summarize_size_bucket_live.py
python scripts/summarize_size_bucket_live.py --log data/logs/live/model_eval.jsonl --format json
```

## 相关脚本

```powershell
python scripts/analyze_size_avg_value_thresholds.py --mc-trials 400
python scripts/compare_size_bucket_sampling_modes.py --footprint 4 --n-trials 120
python scripts/summarize_size_bucket_live.py
```
