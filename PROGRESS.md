# BidKing Lab Progress Index

当前主线：v3 推理引擎重构。

## 当前记录

- v3 进度主记录：[`PROGRESS_V3.md`](PROGRESS_V3.md)
- v3 决策主记录：[`DECISIONS_V3.md`](DECISIONS_V3.md)
- v3 观察主记录：[`OBSERVATIONS_V3.md`](OBSERVATIONS_V3.md)
- v3 设计文档：[`docs/v3_inference_design_2026-06-04.zh-CN.md`](docs/v3_inference_design_2026-06-04.zh-CN.md)
- v3 结构索引：[`docs/PROJECT_STRUCTURE_V3.zh-CN.md`](docs/PROJECT_STRUCTURE_V3.zh-CN.md)
- 最新 handoff：[`handoff_2026-06-14.zh-CN.md`](handoff_2026-06-14.zh-CN.md)（Hero Ref / 全项目入口）

## Hero Ref 支线（与 v3 并行，不替代 promotion）

- 文件与文档总索引：[`docs/HERO_REF_FILE_AND_DOC_INDEX.zh-CN.md`](docs/HERO_REF_FILE_AND_DOC_INDEX.zh-CN.md)
- 执行主记录：[`external_references/ahmad_live_reference_lab/EXECUTION_NOTES_2026-06-10.zh-CN.md`](external_references/ahmad_live_reference_lab/EXECUTION_NOTES_2026-06-10.zh-CN.md)（§60–§62 艾莎 / §50）
- 样本索引：[`docs/hero_ref_settlement_sample_index_2026-06-11.zh-CN.md`](docs/hero_ref_settlement_sample_index_2026-06-11.zh-CN.md)（**§11 小地图 live 样本**）
- 最新 handoff：[`handoff_2026-06-14.zh-CN.md`](handoff_2026-06-14.zh-CN.md)（v0.1.8-hotfix + **dev 约束/布局**；**当前开发 v0.1.9**）
- **v0.1.8 之后变更流水**：[`CHANGELOG_HERO_REF_post-v0.1.8.zh-CN.md`](CHANGELOG_HERO_REF_post-v0.1.8.zh-CN.md)（含 hotfix + *dev/worktree*；**tier 总价→格子数待评估**）
- **hotfix 发布说明**：[`RELEASE_NOTES_v0.1.8-hotfix.zh-CN.md`](RELEASE_NOTES_v0.1.8-hotfix.zh-CN.md)
- 艾莎代表样本：[`docs/hero_ref_aisha_representative_samples_2026-06-13.zh-CN.md`](docs/hero_ref_aisha_representative_samples_2026-06-13.zh-CN.md)
- 诊断样本 catalog：[`data/samples/hero_ref/manifest.json`](data/samples/hero_ref/manifest.json)（含 `HR-20260614-6376` 结算页估价泄露样本）

## 历史记录

v1/v2 以及 2026-06-04 之前的长记录已归档到：

- [`archive/v2_legacy_2026-06-04/README.md`](archive/v2_legacy_2026-06-04/README.md)
- [`archive/v2_legacy_2026-06-04/records/PROGRESS.v2.md`](archive/v2_legacy_2026-06-04/records/PROGRESS.v2.md)
- [`archive/v2_legacy_2026-06-04/records/DECISIONS.v2.md`](archive/v2_legacy_2026-06-04/records/DECISIONS.v2.md)
- [`archive/v2_legacy_2026-06-04/records/OBSERVATIONS.v2.md`](archive/v2_legacy_2026-06-04/records/OBSERVATIONS.v2.md)

## 当前验证基线

- 最新 v3 功能 checkpoint commit：`8c585e1 Add v3 prior robustness slice audit`
- 新窗口交接入口：[`handoff_2026-06-06.zh-CN.md`](handoff_2026-06-06.zh-CN.md)
- 当前推荐测试/分析解释器：`C:\Users\shenc\anaconda3\python.exe`
- 最新重点验证见 `PROGRESS_V3.md` 末尾 2026-06-06 checkpoints；包括 prior/activity robustness、live/model_eval 字段对齐与 prior-stress 分片审计。
- 普通主库当前为 441 文件、1560 ready windows；0605 252x 沉船活动 cohort 已独立到 `data/samples/fatbeans_activity_20260605_shipwreck/`。

## 维护规则

- 根目录 `PROGRESS.md` 只保留索引，不再追加长篇流水账。
- v3 主线新增进展写入 `PROGRESS_V3.md`。
- v2 历史只在归档文件中查阅；v2 代码仍保持可运行，不删除。
