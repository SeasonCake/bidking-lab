# v2 Legacy Archive 2026-06-04

归档日期：2026-06-04  
归档原因：v3 推理引擎重构启动，根目录记录切换为 v3 主线索引。

## 归档文件映射

| 原路径 | 归档路径 | 作用 | 当前状态 |
| --- | --- | --- | --- |
| `PROGRESS.md` | `archive/v2_legacy_2026-06-04/records/PROGRESS.v2.md` | v1/v2 长进度、checkpoint、历史验证命令 | 历史查阅 |
| `DECISIONS.md` | `archive/v2_legacy_2026-06-04/records/DECISIONS.v2.md` | v1/v2 决策记录 | 历史查阅 |
| `OBSERVATIONS.md` | `archive/v2_legacy_2026-06-04/records/OBSERVATIONS.v2.md` | v1/v2 技术观察和实测现象 | 历史查阅 |
| `docs/v2_estimation_review_2026-06-04.zh-CN.md` | `archive/v2_legacy_2026-06-04/docs/v2_estimation_review_2026-06-04.zh-CN.md` | v2 估值审查、指标、停止条件 | v3 设计参考 |
| `handoff_2026-05-30.zh-CN.md` | `archive/v2_legacy_2026-06-04/handoffs/handoff_2026-05-30.zh-CN.md` | 历史交接 | 历史查阅 |
| `handoff_2026-06-02.zh-CN.md` | `archive/v2_legacy_2026-06-04/handoffs/handoff_2026-06-02.zh-CN.md` | 历史交接 | 历史查阅 |
| `handoff_2026-06-03.zh-CN.md` | `archive/v2_legacy_2026-06-04/handoffs/handoff_2026-06-03.zh-CN.md` | 历史交接 | 历史查阅 |
| `handoff_2026-06-04.zh-CN.md` | `archive/v2_legacy_2026-06-04/handoffs/handoff_2026-06-04.zh-CN.md` | v2 到 v3 前交接 | 根目录保留指针 |

## 当前对应入口

| 主题 | 当前入口 |
| --- | --- |
| v3 进度 | `PROGRESS_V3.md` |
| v3 决策 | `DECISIONS_V3.md` |
| v3 观察 | `OBSERVATIONS_V3.md` |
| v3 设计 | `docs/v3_inference_design_2026-06-04.zh-CN.md` |
| 项目结构 | `docs/PROJECT_STRUCTURE_V3.zh-CN.md` |

## 未物理归档的活跃路径

这些路径仍被脚本、测试或 live 路径使用，暂不移动：

| 路径 | 作用 | 说明 |
| --- | --- | --- |
| `src/bidking_lab/inference/v2.py` | v2 formal baseline | 后续作为 v3 paired compare 基线 |
| `src/bidking_lab/inference/q6_residual.py` | v2 q6 residual / shadow logic | v3 迁移时参考，不删除 |
| `scripts/evaluate_fatbeans_v2_samples.py` | v2 archive evaluator | 当前仍用于对照 |
| `scripts/summarize_live_windivert_brief.py` | live/archive brief | 当前仍用于实机复核 |
| `scripts/run_live_overlay.py` | 当前 UI overlay | UI 设计冻结保留 |
| `data/samples/fatbeans` | 本地 Fatbeans 样本 | 355 份 JSON，本地 ignored，不移动 |
| `tests/` | 当前回归测试 | 继续作为 v2/v3 共享验证 |

## 本地 ignored 产物

以下本地 ignored 产物已移到 `archive/local_ignored/2026-06-04/`，不参与 git：

- `.pytest_cache/`
- `.tmp/`
- `data/tmp/`
- `dist/`
- `tools/ilspycmd`

## 外部参考映射

外部参考统一放在 `external_references/`，不属于项目源码：

| 旧/易混路径 | 当前路径 |
| --- | --- |
| `src/grid_view_v1.3.7` | `external_references/grid_view_v1.3.7/` |
| `src/AuctionAnalyzer4.13.3.zip` | `external_references/AuctionAnalyzer4.13.3.zip` |
| `src/AuctionAnalyzer4.13.3/` | `external_references/AuctionAnalyzer4.13.3/` |
| `src/bidking_lab.egg-info` | 构建产物，按 `.gitignore` 排除 |

## 注意

- v2 归档不等于删除 v2 运行能力。
- 若后续物理移动 v2 代码，必须先补 compatibility wrapper，并跑 full pytest 和 live/archive smoke。
