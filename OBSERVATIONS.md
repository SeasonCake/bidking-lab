# BidKing Lab Observation Index

当前主线观察写入 [`OBSERVATIONS_V3.md`](OBSERVATIONS_V3.md)。

## 当前观察入口

- v3 主线观察：[`OBSERVATIONS_V3.md`](OBSERVATIONS_V3.md)
- v3 进度主记录：[`PROGRESS_V3.md`](PROGRESS_V3.md)
- v3 evidence coverage 脚本：[`scripts/summarize_v3_evidence_coverage.py`](scripts/summarize_v3_evidence_coverage.py)
- 最新 handoff：[`handoff_2026-06-12.zh-CN.md`](handoff_2026-06-12.zh-CN.md)

## Hero Ref 观察入口

- 样本与机制观察：[`docs/hero_ref_settlement_sample_index_2026-06-11.zh-CN.md`](docs/hero_ref_settlement_sample_index_2026-06-11.zh-CN.md)（§8 SEND-no-REV；§9 待补金为零 live 样本）
- 调查结论：EXECUTION_NOTES §53（金均格 0 UI）、§55（现象 vs 落地对照）
- 索引：[`docs/HERO_REF_FILE_AND_DOC_INDEX.zh-CN.md`](docs/HERO_REF_FILE_AND_DOC_INDEX.zh-CN.md)

## 当前重点观察

- O-v3-057：0605 新样本已分成普通别墅样本与 252x 沉船活动 cohort。
- O-v3-058：prior robustness 能区分普通 archive、弱 fallback 与 252x 活动 cohort。
- O-v3-059：live/model_eval 已具备 activity/prior-drift 审计字段。
- O-v3-060：prior-stressed 分片集中在 cells/capacity mismatch。

## 历史观察

- v2 历史观察归档：[`archive/v2_legacy_2026-06-04/records/OBSERVATIONS.v2.md`](archive/v2_legacy_2026-06-04/records/OBSERVATIONS.v2.md)
- v2 估值审查归档：[`archive/v2_legacy_2026-06-04/docs/v2_estimation_review_2026-06-04.zh-CN.md`](archive/v2_legacy_2026-06-04/docs/v2_estimation_review_2026-06-04.zh-CN.md)

## 维护规则

- 根目录 `OBSERVATIONS.md` 只保留索引。
- v3 新观察写入 `OBSERVATIONS_V3.md`。
- 数据质量问题、模型误差、UI/采集问题必须分开记录。
