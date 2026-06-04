# BidKing Lab Progress Index

当前主线：v3 推理引擎重构。

## 当前记录

- v3 进度主记录：[`PROGRESS_V3.md`](PROGRESS_V3.md)
- v3 决策主记录：[`DECISIONS_V3.md`](DECISIONS_V3.md)
- v3 观察主记录：[`OBSERVATIONS_V3.md`](OBSERVATIONS_V3.md)
- v3 设计文档：[`docs/v3_inference_design_2026-06-04.zh-CN.md`](docs/v3_inference_design_2026-06-04.zh-CN.md)
- v3 结构索引：[`docs/PROJECT_STRUCTURE_V3.zh-CN.md`](docs/PROJECT_STRUCTURE_V3.zh-CN.md)

## 历史记录

v1/v2 以及 2026-06-04 之前的长记录已归档到：

- [`archive/v2_legacy_2026-06-04/README.md`](archive/v2_legacy_2026-06-04/README.md)
- [`archive/v2_legacy_2026-06-04/records/PROGRESS.v2.md`](archive/v2_legacy_2026-06-04/records/PROGRESS.v2.md)
- [`archive/v2_legacy_2026-06-04/records/DECISIONS.v2.md`](archive/v2_legacy_2026-06-04/records/DECISIONS.v2.md)
- [`archive/v2_legacy_2026-06-04/records/OBSERVATIONS.v2.md`](archive/v2_legacy_2026-06-04/records/OBSERVATIONS.v2.md)

## 当前验证基线

- 最新 checkpoint commit：`4d3aa9f Checkpoint v3 inference kickoff`
- 该 commit 前验证：`C:\Python313\python.exe -m pytest -q` 为 `882 passed`
- v3 evidence coverage：`C:\Python313\python.exe .\scripts\summarize_v3_evidence_coverage.py --fail-on-gaps` 通过，当前可解析 archive 无 unknown/pending evidence id

## 维护规则

- 根目录 `PROGRESS.md` 只保留索引，不再追加长篇流水账。
- v3 主线新增进展写入 `PROGRESS_V3.md`。
- v2 历史只在归档文件中查阅；v2 代码仍保持可运行，不删除。
