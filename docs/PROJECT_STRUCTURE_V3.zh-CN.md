# BidKing Lab v3 项目结构索引

日期：2026-06-04  
用途：把当前主线、历史归档、脚本、样本、测试和外部参考的职责分清。

## 当前主线文件

| 路径 | 作用 |
| --- | --- |
| `PROGRESS.md` | 根进度索引 |
| `PROGRESS_V3.md` | v3 当前进度 |
| `DECISIONS.md` | 根决策索引 |
| `DECISIONS_V3.md` | v3 当前决策 |
| `OBSERVATIONS.md` | 根观察索引 |
| `OBSERVATIONS_V3.md` | v3 当前观察 |
| `docs/v3_inference_design_2026-06-04.zh-CN.md` | v3 设计文档 |
| `src/bidking_lab/inference/v3/` | v3 推理引擎新包 |
| `scripts/summarize_v3_evidence_coverage.py` | v3 evidence coverage 检查 |
| `scripts/summarize_v3_constraints.py` | v3 hard constraint compiler 摘要 |
| `scripts/evaluate_fatbeans_v3_samples.py` | v3 archive pre-bid ConstraintSet evaluator |
| `tests/test_inference_v3_evidence_registry.py` | v3 registry/constraint 骨架测试 |
| `tests/test_evaluate_fatbeans_v3_samples.py` | v3 evaluator skeleton 测试 |

## v2 保留路径

| 路径 | 保留原因 |
| --- | --- |
| `src/bidking_lab/inference/v2.py` | 当前 formal baseline 与 v3 对照 |
| `src/bidking_lab/inference/q6_residual.py` | v2 q6 residual/shadow 逻辑，v3 迁移参考 |
| `scripts/evaluate_fatbeans_v2_samples.py` | archive 对照评估仍需要 |
| `scripts/compare_q6_residual_boost.py` | v2 q6 候选对照工具 |
| `tests/test_inference_v2.py` 等 v2 tests | 防止 v3 重构时破坏现有路径 |

v2 历史记录归档在 `archive/v2_legacy_2026-06-04/`。

## live/UI/archive 路径

| 路径 | 作用 | 当前策略 |
| --- | --- | --- |
| `scripts/run_live_overlay.py` | 当前 UI overlay | UI 设计冻结，不做视觉重做 |
| `scripts/run_windivert_live_monitor.py` | WinDivert live monitor | 保持当前路径 |
| `scripts/start_live_windivert_overlay.ps1` | live monitor/overlay 启动 | 保持当前路径 |
| `scripts/post_game_live.ps1` | 局后归档 | 保持当前路径 |
| `scripts/summarize_live_windivert_brief.py` | live/archive brief | 后续可加 v3 shadow columns |
| `data/logs/live/` | 本地 live 日志 | ignored，本地运行态 |
| `data/samples/fatbeans/` | 本地 archive 样本 | 355 份 JSON，默认脚本路径，不移动 |

## 数据目录

| 路径 | 作用 | 版本策略 |
| --- | --- | --- |
| `data/processed/` | 可提交的派生表和本地表缓存 | 保持现状 |
| `data/raw/` | 本地原始游戏表 | ignored |
| `data/review/` | 本地审计输出 | ignored |
| `data/tmp/` | 临时输出 | 已移动到 ignored local archive |
| `data/samples/synthetic_v2/` | 合成样本 | 保留 |
| `data/samples/fatbeans/` | 实机 Fatbeans archive | 保留原路径 |

## 脚本与测试

当前脚本规模：

- Python scripts：71
- PowerShell scripts：13
- test files：69

策略：

- 可运行脚本暂不移动。
- v3 新脚本使用 `*_v3_*` 或 `v3_*` 命名。
- v2 脚本保留 `*_v2_*` 命名，作为 paired compare。
- 大规模脚本目录重组必须先加 alias/wrapper，再跑测试。

## 外部参考

外部参考只读存放：

| 路径 | 说明 |
| --- | --- |
| `external_references/grid_view_v1.3.7/` | grid_view 外部参考 |
| `external_references/AuctionAnalyzer4.13.3.zip` | AuctionAnalyzer 压缩包 |
| `external_references/AuctionAnalyzer4.13.3/` | AuctionAnalyzer 解包/反编译参考 |
| `external_references/bidking-booooot/` | 外部 repo 参考 |
| `external_references/jrinky-bidking/` | 外部 repo 参考 |

这些路径在 `.gitignore` 下，不作为项目源码提交。

## 本地 ignored 清理策略

| 路径 | 策略 |
| --- | --- |
| `.pytest_cache/` | 已移动到 `archive/local_ignored/2026-06-04/.pytest_cache/` |
| `.tmp/` | 已移动到 `archive/local_ignored/2026-06-04/.tmp/` |
| `data/tmp/` | 已移动到 `archive/local_ignored/2026-06-04/data_tmp/` |
| `dist/` | 已移动到 `archive/local_ignored/2026-06-04/dist/` |
| `tools/ilspycmd` | 已移动到 `archive/local_ignored/2026-06-04/tools/` |

`archive/local_ignored/` 是本地 ignored 归档，不参与 git 提交。
