# BidKing Lab Decision Index

当前主线决策写入 [`DECISIONS_V3.md`](DECISIONS_V3.md)。

## 当前有效决策入口

- v3 主线决策：[`DECISIONS_V3.md`](DECISIONS_V3.md)
- v3 设计文档：[`docs/v3_inference_design_2026-06-04.zh-CN.md`](docs/v3_inference_design_2026-06-04.zh-CN.md)
- 项目结构与归档索引：[`docs/PROJECT_STRUCTURE_V3.zh-CN.md`](docs/PROJECT_STRUCTURE_V3.zh-CN.md)
- 最新 handoff：[`handoff_2026-06-06.zh-CN.md`](handoff_2026-06-06.zh-CN.md)

## 当前重点决策

- D-v3-052：0605 后 252x 沉船活动样本独立 cohort，不混入旧沉船 prior 校准。
- D-v3-053：prior robustness gate 是 v3 promotion 的前置边界。
- D-v3-054：prior robustness 必须在 archive/live/model_eval 同步输出。
- D-v3-055：prior-stressed 行必须先分片审计，不进入普通 sampler 校准分母。

## 历史决策

- v2 历史决策归档：[`archive/v2_legacy_2026-06-04/records/DECISIONS.v2.md`](archive/v2_legacy_2026-06-04/records/DECISIONS.v2.md)
- v2 归档总索引：[`archive/v2_legacy_2026-06-04/README.md`](archive/v2_legacy_2026-06-04/README.md)

## 维护规则

- 根目录 `DECISIONS.md` 只保留索引。
- v3 新决策写入 `DECISIONS_V3.md`。
- 若 v3 决策改变 v2/live/UI/archive 的运行边界，必须同时写明迁移路径和回归验证命令。
