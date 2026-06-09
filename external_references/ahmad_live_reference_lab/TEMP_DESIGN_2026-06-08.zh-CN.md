# Ahmed Live Reference Engine Design

日期：2026-06-08

## 背景

当前 v3 已经能通过 Fatbeans/live packet 获取 Ahmed 技能结果，但完整 v3 promotion 仍在另一个窗口推进。Ahmed 本身的技能输入更结构化，比 Aisha/Ethan 的 tail/q6 判断更适合先做一条轻量、解释性强的参考推理器。

本设计把外援 `AuctionAnalyzer4.13.3 / MapBidCalculator` 当作计算器参考，而不是整套替换 bidking-lab：

- 外援强项：组合枚举、均格可达性、品质概率权重、保守/均衡/激进三档输出；
- v3 强项：packet 实时输入、道具/公开信息优先级、q6 风险标签、活动图和 prior drift guard；
- 第一版只在 `external_references/ahmad_live_reference_lab` 内实现或记录，不改主线。

## 输入模型

第一版实时输入只读已有 live 输出，不直接抓包、不注入、不控制游戏：

```text
live monitor / post_game
  -> data/logs/live/latest_snapshot.json
  -> data/logs/live/model_eval.jsonl
  -> ahmad_live_reference_lab reader
```

必须支持的 Ahmed 字段：

| 来源 | 语义 | 目标约束 |
|---|---|---|
| `100204` | 总藏品数量 | `session.total_item_count` |
| `1002041` | 金/橙平均格数 | `bucket.q5.avg_cells` |
| `1002042` | 紫平均格数 | `bucket.q4.avg_cells` |
| `1002043` | 蓝平均格数 | `bucket.q3.avg_cells` |
| `1002044` | 绿白合并件数 | `bucket.q1.count` |

支线内部新增一个稳定 bridge：

```json
{
  "ahmad_ref_inputs": {
    "total_count": 24,
    "total_cells": 88,
    "avg_cells": {"q5": 3.2, "q4": 2.3333333, "q3": 1.8461538},
    "counts": {"q1": 1},
    "field_updates": [
      {"path": ["session", "total_item_count"], "value": 24},
      {"path": ["bucket", "5", "avg_cells"], "value": 3.2}
    ]
  }
}
```

后续若主线合并，应优先由 live snapshot/UI contract 显式写入这个结构，外援核心只读该结构和公开摘要，不直接依赖主线内部类。

可选吸收的 v3/live 字段：

- map id / map family / round / hero；
- public total count/cells/value/avg；
- scan result：品质、轮廓、总价、均价；
- known red item count 或 q6 count posterior；
- activity/prior drift 标签；
- q6 under-risk / extreme-over guard 标签。

## 推理核心

第一版采用“解析组合枚举 + 轻量 value band”，先不做完整 v3 sampler。

### 1. Count vector enumeration

枚举 `(q1, q3, q4, q5, q6)` 件数组合：

- q1 表示绿白合并；
- q3 蓝，q4 紫，q5 金/橙，q6 红；
- 若 Ahmed R1 给出 `total_item_count`，则所有品质件数之和必须匹配；
- 若 R5 给出 q1 件数，则 q1 固定；
- 其他 scan/public exact count 作为 hard 约束；
- 没有 exact count 时按地图品质概率给先验权重。

### 2. Avg-cells reachability

参考 MapBidCalculator 的 `AvgMatch` / `CanComposeGridTotal` 思路，但实现时优先用 bidking-lab 已有的有理数/截断显示口径：

- 对每个品质，根据 `count` 与显示均格推导可达总格集合；
- 如果可达集合唯一，可作为强约束；
- 如果集合很窄，可作为 soft likelihood；
- 如果不可达，UI 标记为 `输入冲突`，不直接清空其他证据。

### 3. Value band

第一版输出三档，不直接取代 v3 formal：

| 档位 | 含义 | 初始计算 |
|---|---|---|
| 保守 | 防低估但不过分抢 | weighted P35 或外援 P25 × safety |
| 参考 | 常规建议价 | weighted P50 × safety |
| 激进 | 接受一定过冲 | weighted P75/P90 guard cap |

价值来源优先级：

1. 已知 item/value exact；
2. v3/live 已有 bucket value evidence；
3. 外援 MapBidCalculator 的 quality price stats / beam search 思路；
4. 当前 decoded table 的 per-quality per-cell fallback；
5. map-family fallback，例如新沉船活动图先用旧 shipwreck family，但 UI 标记 `prior_drift_watch`。

### 4. Red/q6 handling

Ahmed UI 必须一线显示红品数量：

- 有 exact red count：显示 `红品 N 件`；
- 没有 exact：显示 `红品件数 P10/P50/P90`；
- 若 q6 tail/value risk 明显，显示 `红品尾部偏保守`；
- 如果活动图或缺表图导致 prior 不可靠，红品 band 必须加宽而不是强行压低。

## 鲁棒性策略

本实验线不追求样本拟合，而追求实战解释性：

- 新地图默认按 map family fallback，优先 shipwreck/villa，而不是 unknown；
- 活动图、缺 Drop overlay、table drift 时降低置信度并拓宽 P75/P90；
- packet/public/tool exact evidence 必须压过 OCR 和 prior；
- 如果道具读数没有改变估值，UI 必须说明“该读数只改变约束但未改变候选排序”或“未进入当前参考模型”，避免用户误判；
- 估值过冲时优先检查证据来源和 prior drift，而不是只调 safety factor。

## 当前真实样本结论

`tools/smoke_ahmed_ref_samples.py` 已确认：

- 2404 Ahmed 样本在出价前窗口存在总件数和 q5/q4/q3 均格，`ref_v0` 可直接输出；
- 2406/2407 Ahmed 样本早期缺总件数字段，即使已有均格也应保持 `missing_total_count` / `等待外援输入`，不要走未完成 v3 fallback；
- 这类缺口应作为采集/bridge 问题处理，不应通过价格 safety factor 掩盖；
- settlement 后的 bucket count 不能无脑当 Ahmed q1 绿白合并 count，因为 final quality q1/q2 与 Ahmed 低品质合并口径可能不同。

## 不做的事

第一版不做：

- OCR 作为默认入口；
- 自动出价或键鼠控制；
- 改主线 v3/live/UI；
- 直接把外援价格模型接 formal；
- 只针对 2406/2407 两三个样本调参。
