# BidKing Lab v3 Strategy Pivot - 2026-06-07

本文件记录 2026-06-07 的执行策略切换。目标是避免继续在 CSE/support-depth 审计里无限细分，同时不把尚未稳定的 shadow 信号提前 promotion。

## 当前新目标

```text
继续推进 BidKing Lab v3 推理引擎重构：保持 v2 formal/live/UI 和正式出价不变，停止继续扩张 CSE/support-depth 审计；把已验证的 v3_cse_* capacity/source expansion、settlement count-prior bridge、guarded bridge stability、tail/under/CCV 等 shadow lanes 统一纳入 v3 formal/value promotion workbench。下一阶段只做 shadow-only formal/value 接口、候选分片、stop-loss gate 和评估口径，不接正式参数、不影响 live/formal。只有候选在 archive/session/map/profile holdout、seed stability、MAE/below/P90/pinball/high-over、prior robustness 和 live model_eval 对齐后，才讨论 v3 promotion 或 v2 归档。
```

## 为什么切换

已确认：

- CSE 能解释 settlement over-cap / capacity blocker，但还不能作为 promotion prior：
  - `map_family` recall `21/21`，precision `0.050119`，太宽；
  - `map_id` recall `18/21`，precision `0.089109`，漏 3 条稀疏/单例；
  - support-depth fallback 可到 recall `19/21`、precision `0.082251`，仍不足以接 sampler。
- payload-only rows 已拆到 empty-action / partial-action：
  - empty-action 是 numeric-only source semantics，不是 item payload parser 漏解；
  - partial-action 只证明部分 source 可见，不能证明 full inventory。
- guarded settlement bridge seed stability 已实测失败：
  - overall `blocked_applied_hurt`；
  - seed 1 选入 `2501` 并 hurt；
  - seed 7 的 `2506` applied rows 只有 9，低于 20。

继续增加 CSE key、support-depth、shape/signature 组合，大概率只会增加审计复杂度，不能解锁 readiness。

## 已冻结为 watch/blocked 的 lane

| Lane | 当前状态 | 处理 |
| --- | --- | --- |
| `v3_cse_*` broad map-family | recall 高、precision 极低 | 保留 watch，不接 sampler |
| `v3_cse_*` map-id | precision 较高但漏召回 | 保留默认 support baseline，不 promotion |
| CSE support-depth fallback | 19/21 recall、precision 0.082251 | 作为候选分片，不默认启用 |
| source shape/signature | precision 小幅提升但 recall 下降 | 不作为 prior key |
| settlement count->cells/value bridge | holdout over-risk 高 | blocked，不推广 |
| guarded bridge | single-seed watch | 必须看 stability |
| guarded bridge stability | `blocked_applied_hurt` | blocked，不作为近期 promotion path |

## 下一阶段允许做什么

允许：

- 设计 shadow-only formal/value sampler 接口和评估口径。
- 建立 promotion workbench，把现有 lanes 的候选、支持度、分母和 stop-loss 放在同一个报告里。
- 小范围生成候选分片，但只输出 shadow fields / audit rows。
- 明确每条候选的进入条件、退出条件和需要的样本。
- 继续补 live `model_eval` 字段一致性，方便实战后复盘。

不允许：

- 不改 v2 formal/live/UI。
- 不改正式出价。
- 不把 `v3_cse_*`、SCP bridge、tail/under、CCV、residual 接入 formal bid。
- 不因为单一指标改善而放宽 high-over、P90、pinball 或 seed-stability guard。
- 不继续无限新增 CSE 分组审计，除非有新外部表、source parser 或实战样本。

## 下一步最小执行单元

1. 固化 guarded bridge stability evidence 到 processed shadow artifact。
2. 让 readiness 引用该 artifact，明确 stability 已评估且 blocked。
3. 新增/整理 promotion workbench 的字段定义：
   - candidate lane；
   - candidate scope；
   - train support；
   - holdout status；
   - seed stability；
   - formal MAE/below/P90/pinball/high-over；
   - whether affects_bid。
4. 从 workbench 选一个最小、低风险、样本足够的 shadow-only formal/value interface slice。

## 当前 stop condition

如果 promotion workbench 仍显示所有 candidate lane 都 blocked 或 sample-limited，则本阶段不要再继续调参；应转向：

- 追加 targeted samples；
- source parser / table acquisition；
- 或明确 v3 formal/value sampler 需要更大架构改动。
