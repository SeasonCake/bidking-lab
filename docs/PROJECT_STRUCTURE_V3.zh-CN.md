# BidKing Lab v3 项目结构索引

日期：2026-06-07
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
| `handoff_2026-06-06.zh-CN.md` | v3 新窗口交接入口、prompt 与推荐 goal |
| `docs/v3_inference_design_2026-06-04.zh-CN.md` | v3 设计文档 |
| `src/bidking_lab/inference/v3/` | v3 推理引擎新包 |
| `src/bidking_lab/inference/v3/pipeline.py` | archive/live 共用 v3 shadow 推理链路 |
| `src/bidking_lab/inference/v3/priors.py` | v3 drop-prior summary 与共享 flat fields |
| `src/bidking_lab/inference/v3/prior_robustness.py` | v3 drop-prior 漂移、活动期、fallback 鲁棒性审计 |
| `src/bidking_lab/inference/v3/formal_value_sampler.py` | v3 formal/value sampler 第一阶段 shadow report，拆分 capacity/cells/value-floor stress，固定不影响出价 |
| `src/bidking_lab/inference/v3/settlement_count_prior.py` | v3 settlement occupancy count-prior shadow evidence，输出 `v3_scp_*`，固定 inactive/不影响出价 |
| `src/bidking_lab/inference/v3/capacity_source_expansion.py` | v3 capacity/source expansion shadow evidence，输出含 `v3_cse_source_context_classes` 的 `v3_cse_*`，固定 inactive/不影响出价 |
| `src/bidking_lab/inference/v3/underestimate_repair.py` | v3 低估上修 shadow report |
| `src/bidking_lab/inference/v3/tail_value_review.py` | v3 tail/value review shadow report 与 hurt guard |
| `data/processed/v3_settlement_count_prior_shadow.json` | v3 settlement count-prior shadow entry 表，合并 default archive 与 0605 activity cohort |
| `data/processed/v3_capacity_source_expansion_shadow.json` | v3 capacity/source expansion shadow entry 表，合并 default archive 与 0605 activity cohort，并保留 source evidence/context/mechanism counts |
| `data/processed/v3_underestimate_repair_shadow.json` | v3 hero/map 低估上修 shadow entry 表 |
| `data/processed/v3_tail_value_review_shadow.json` | v3 tail/value review shadow entry 表 |
| `scripts/summarize_v3_evidence_coverage.py` | v3 evidence coverage 检查 |
| `scripts/summarize_v3_constraints.py` | v3 hard constraint compiler 摘要 |
| `scripts/evaluate_fatbeans_v3_samples.py` | v3 archive pre-bid ConstraintSet evaluator，支持 `v3_robust_*` prior/activity 审计、`v3_capacity_*` capacity prior-max gap/cases、`v3_fv_*` formal/value sampler shadow 字段、`v3_scp_*` settlement count-prior shadow evidence、含 `v3_cse_source_context_classes` 的 `v3_cse_*` capacity/source expansion shadow evidence、可选 `v3_ccvc_` component likelihood 与 freeze-cells audit |
| `scripts/summarize_v3_metric_slices.py` | v3 round/map/hero/profile 分片指标 |
| `scripts/summarize_v3_map_audit.py` | v3 map 主键审计，附 hero/profile 分布 |
| `scripts/summarize_v3_prior_robustness_audit.py` | v3 prior/activity/prior-stress 分片审计，支持 `--details`、`--detail-summary` 与 `--detail-summary-by` 输出 cells/capacity/evidence 明细、target-vs-truth delta、posterior-vs-target absorption、capacity prior-max gap/cases、lower-bound target completeness 和 map/profile 聚合一致性摘要 |
| `scripts/summarize_v3_capacity_table_audit.py` | v3 prior-stress capacity cases 对 raw BidMap/Drop sampler possible-max、v300 23 列 BidMap/drop-ref、round-cap 候选、leaf `n_min/n_max`、settlement slot capacity、full mirror action 与 drop-universe 覆盖审计，并输出 raw settlement inventory/latest truth 去重诊断 |
| `scripts/summarize_v3_capacity_source_expansion_audit.py` | v3 capacity semantic matrix 的 file-level source/expansion 下钻审计，按 public total、full observed action、latest inventory、drop/round excess 与 example capture 拆解 hard/lower capacity blocker |
| `scripts/summarize_v3_archive_table_timing.py` | v3 raw table version/filelist/BidMap/Drop metadata、BidMap col[16]/col[17] 语义、priority maps reachable Drop `n_min/n_max`、252x/452x activity overlay BidMap/Drop presence 与 Fatbeans archive/activity capture timing 诊断，用于区分 table-version 强证据与本地 mtime 弱线索 |
| `scripts/summarize_v3_bidmap_raw_capacity_candidates.py` | v3 BidMap raw numeric columns 对 settlement unique count/cells truth 的 coverage 审计，区分语义 capacity columns 与非 capacity 的 count-sized id/category/hint 字段 |
| `scripts/summarize_v3_settlement_payload_audit.py` | v3 0x002D settlement raw payload 审计，核对 outer wrapper shape、field3/4/5 presence、field6 count、inventory block slot count、occupied/empty slot shape、candidate path、slot int field/source-shape、raw item candidates、dedup 后 inventory count、payload fields 与 full observed action 镜像 |
| `scripts/summarize_v3_settlement_count_prior_candidates.py` | v3 settlement occupancy count prior shadow-only 候选审计，按 map/prefix/family/residual-mode/unique-residual-mode/BidMap sub-pool kind/round/session/capture-day/session-token-prefix/BidMap round-category-hint 维度统计 final inventory count、临时生肖扣除 residual、runtime/item duplicate、unique non-temp item cap coverage、item primary-category/hinted coverage、quality/count/cells coverage、reachable Drop item-universe 覆盖、0x002D outer wrapper、payload field-shape、occupied/empty slot shape、candidate path、slot headroom、public-total/full-action evidence 与 current BidMap/round-cap 覆盖 |
| `scripts/summarize_v3_settlement_source_semantics_audit.py` | v3 settlement over-cap / capacity blocker source semantics 审计，遍历 capture 全部 state，按 public total、direct/full action、0x002D payload match、source context/action coverage、local v300 filelist/Activity overlay metadata、mechanism class 汇总 unique round overflow 收口证据 |
| `scripts/summarize_v3_settlement_count_prior_holdout.py` | v3 settlement occupancy count prior session-level holdout 审计，比较 current table cap、round-cap 与 train p95/max coverage |
| `scripts/summarize_v3_capacity_source_expansion_holdout.py` | v3 capacity/source expansion session-level holdout 审计，验证 map-family/map_id/composite source signature/fallback candidate 对 unique round-cap blocker 的 recall、precision、false positive、source context 分布与 missed examples |
| `scripts/summarize_v3_activity_mapping_likelihood.py` | v3 252x activity missing-table 候选映射审计，比较 `252x->251x` 与 `252x->250x` 的 settlement quality likelihood，只作为 table/activity 语义证据 |
| `scripts/summarize_v3_scp_formal_value_link.py` | v3 settlement count-prior evidence 与 formal/value stress 的 archive 关联审计，量化 `v3_scp` candidate 与 value-floor/capacity watch 的交集 |
| `scripts/summarize_v3_scp_count_value_bridge.py` | v3 settlement count-prior count->cells/value bridge archive 审计，量化 count gap、cells p90 undercoverage 与 formal p90 undercoverage 的交集 |
| `scripts/summarize_v3_scp_count_value_bridge_holdout.py` | v3 settlement count-prior count->cells/value bridge session holdout，验证 bridge floor 对 formal MAE/p90/over-rate 的影响，并支持 audit-only `floor_mode`/`formal_lift_cap` guard probe |
| `scripts/summarize_v3_scp_guarded_bridge_holdout.py` | v3 settlement count-prior nested train-only guarded bridge holdout，要求 inner crossfit 各折稳定且 train over-rate 不增加，只输出 shadow readiness evidence |
| `scripts/summarize_v3_scp_guarded_bridge_stability.py` | v3 guarded bridge posterior trial/seed stability 矩阵审计，汇总 selected group drift、applied hurt、support depth，并使用 `.tmp/codex/` per-run cache |
| `scripts/build_v3_settlement_count_prior_shadow.py` | 从 default archive 与 activity cohort 构建 `data/processed/v3_settlement_count_prior_shadow.json` |
| `scripts/build_v3_capacity_source_expansion_shadow.py` | 从 settlement source-semantics 审计构建 `data/processed/v3_capacity_source_expansion_shadow.json` |
| `scripts/summarize_v3_promotion_readiness.py` | v3 formal promotion readiness 总审计，包含携带 `capacity_count_summary`/case counts 的 `prior_stress_capacity_table_drift`、`settlement_count_formal_value_link`、`capacity_source_expansion_shadow`、原始/guarded `settlement_count_cells_value_bridge` holdout 与 `formal_value_sampler_holdout` gate |
| `scripts/summarize_v3_ccv_profile_candidates.py` | v3 count/cell/value sampler 候选审计 |
| `scripts/summarize_v3_ccv_holdout.py` | v3 CCV/count-cell-value 候选 session holdout 审计 |
| `scripts/summarize_v3_ccv_layer_audit.py` | v3 CCV 多层 holdout 稳定性审计 |
| `scripts/summarize_v3_ccv_guard_sensitivity.py` | v3 CCV count/cell tail guard sensitivity 审计 |
| `scripts/summarize_v3_ccv_direction_audit.py` | v3 CCV p50 移动方向性审计，支持 movement-policy 与复合 group-field |
| `scripts/summarize_v3_ccv_direction_holdout.py` | v3 CCV 方向候选 session holdout 审计，支持 movement-policy、复合 group-field 与候选 include/exclude |
| `scripts/summarize_v3_ccvc_count_policy_matrix.py` | v3 CCVC q6_count policy/group-field 矩阵审计 |
| `scripts/summarize_v3_ccvc_evidence_contribution.py` | v3 CCVC count/cells 证据贡献审计，支持 freeze-cells 口径 |
| `scripts/summarize_v3_formal_value_delta_holdout.py` | v3 q6 formal delta 映射 formal decision 的 session holdout 审计 |
| `scripts/summarize_v3_formal_value_sampler_holdout.py` | v3 formal/value sampler value-floor candidate session holdout 审计，capacity/cells-only watch 不参与价值上修 |
| `scripts/summarize_v3_residual_profile_candidates.py` | v3 residual profile 候选审计 |
| `scripts/summarize_v3_residual_under_value_holdout.py` | v3 residual q6-value 低估上修 session holdout 审计 |
| `scripts/summarize_v3_tail_value_candidates.py` | v3 tail/value review 候选审计 |
| `scripts/summarize_v3_tail_value_holdout.py` | v3 tail/value review 候选 session holdout 审计 |
| `scripts/summarize_v3_underestimate_repair_candidates.py` | v3 低估上修候选审计 |
| `scripts/summarize_v3_underestimate_holdout.py` | v3 低估上修 session holdout 审计 |
| `scripts/summarize_fatbeans_sample_manifest.py` | Fatbeans 样本 manifest/质量分层；支持可选 `cohort_role`/`metric_scope` 元数据，用于把 activity reference cohort 与 default baseline 分开 |
| `scripts/organize_fatbeans_real_samples.py` | 真实样本 canonical archive 整理 |
| `tests/test_inference_v3_evidence_registry.py` | v3 registry/constraint 骨架测试 |
| `tests/test_inference_v3_pipeline.py` | v3 archive/live 共享推理 pipeline 测试 |
| `tests/test_inference_v3_prior_robustness.py` | v3 prior/activity 鲁棒性审计测试 |
| `tests/test_inference_v3_formal_value_sampler.py` | v3 formal/value sampler shadow-only 与 stress 分流测试 |
| `tests/test_inference_v3_settlement_count_prior.py` | v3 settlement count-prior shadow report/entry/matching 测试 |
| `tests/test_inference_v3_capacity_source_expansion.py` | v3 capacity/source expansion shadow report/entry/matching 测试 |
| `tests/test_inference_v3_underestimate_repair.py` | v3 低估上修 shadow report 测试 |
| `tests/test_inference_v3_tail_value_review.py` | v3 tail/value review shadow report 测试 |
| `tests/test_evaluate_fatbeans_v3_samples.py` | v3 evaluator skeleton 测试 |
| `tests/test_summarize_v3_prior_robustness_audit.py` | v3 prior robustness 分片审计测试 |
| `tests/test_summarize_v3_capacity_table_audit.py` | v3 capacity table possible-max 审计测试 |
| `tests/test_summarize_v3_archive_table_timing.py` | v3 archive/table timing metadata 审计测试 |
| `tests/test_summarize_v3_settlement_payload_audit.py` | v3 settlement payload slot/candidate 审计测试 |
| `tests/test_summarize_v3_settlement_count_prior_candidates.py` | v3 settlement count-prior candidate 审计测试 |
| `tests/test_summarize_v3_settlement_source_semantics_audit.py` | v3 settlement source semantics 审计测试，覆盖 overlay metadata、source evidence/context/mechanism class 与 unique round blocker 聚合 |
| `tests/test_summarize_v3_settlement_count_prior_holdout.py` | v3 settlement count-prior session holdout 审计测试 |
| `tests/test_summarize_v3_capacity_source_expansion_holdout.py` | v3 capacity/source expansion session holdout 审计测试，覆盖 source-semantics recall、source context、missed examples 与低样本 blocker |
| `tests/test_summarize_v3_activity_mapping_likelihood.py` | v3 252x activity candidate mapping likelihood 审计测试 |
| `tests/test_summarize_v3_scp_formal_value_link.py` | v3 settlement count-prior 到 formal/value stress 关联审计测试 |
| `tests/test_summarize_v3_scp_count_value_bridge.py` | v3 settlement count-prior count->cells/value bridge 审计测试 |
| `tests/test_summarize_v3_scp_count_value_bridge_holdout.py` | v3 settlement count-prior count->cells/value bridge holdout 测试，覆盖 train-only floor、extra floor 与 formal lift cap |
| `tests/test_summarize_v3_scp_guarded_bridge_holdout.py` | v3 nested train-only guarded bridge holdout 测试，覆盖 inner crossfit group selection 与无指标样本分流 |
| `tests/test_summarize_v3_scp_guarded_bridge_stability.py` | v3 guarded bridge trial/seed stability 矩阵测试，覆盖 exact group 稳定、hurt run 与 low-support blocker |
| `tests/test_build_v3_settlement_count_prior_shadow.py` | v3 settlement count-prior processed artifact builder 测试 |
| `tests/test_build_v3_capacity_source_expansion_shadow.py` | v3 capacity/source expansion processed artifact builder 测试 |
| `tests/test_summarize_v3_promotion_readiness.py` | v3 formal promotion readiness 总审计测试 |
| `tests/test_summarize_v3_ccv_profile_candidates.py` | v3 CCV 候选审计测试 |
| `tests/test_summarize_v3_ccv_holdout.py` | v3 CCV session holdout 审计测试 |
| `tests/test_summarize_v3_ccv_layer_audit.py` | v3 CCV 多层 holdout 审计测试 |
| `tests/test_summarize_v3_ccv_guard_sensitivity.py` | v3 CCV guard sensitivity 审计测试 |
| `tests/test_summarize_v3_ccv_direction_audit.py` | v3 CCV p50 方向性审计测试 |
| `tests/test_summarize_v3_ccv_direction_holdout.py` | v3 CCV 方向候选 session holdout 审计测试 |
| `tests/test_summarize_v3_ccvc_count_policy_matrix.py` | v3 CCVC q6_count policy matrix 测试 |
| `tests/test_summarize_v3_ccvc_evidence_contribution.py` | v3 CCVC 证据贡献审计测试 |
| `tests/test_summarize_v3_formal_value_delta_holdout.py` | v3 q6 formal delta 映射 holdout 测试 |
| `tests/test_summarize_v3_formal_value_sampler_holdout.py` | v3 formal/value sampler holdout 测试 |
| `tests/test_summarize_v3_residual_profile_candidates.py` | v3 residual profile 候选审计测试 |
| `tests/test_summarize_v3_residual_under_value_holdout.py` | v3 residual q6-value 低估 holdout 测试 |
| `tests/test_summarize_v3_tail_value_candidates.py` | v3 tail/value review 候选审计测试 |
| `tests/test_summarize_v3_tail_value_holdout.py` | v3 tail/value holdout 审计测试 |
| `tests/test_summarize_v3_underestimate_repair_candidates.py` | v3 低估上修候选审计测试 |
| `tests/test_summarize_v3_underestimate_holdout.py` | v3 低估上修 holdout 审计测试 |

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
| `scripts/run_windivert_live_monitor.py` | WinDivert live monitor | 保持当前路径；v3 shadow artifact/model_eval 输出 `v3_robust_*`、`v3_capacity_*`/cases、`v3_fv_*`、`v3_scp_*` 与含 source context 的 `v3_cse_*` |
| `scripts/start_live_windivert_overlay.ps1` | live monitor/overlay 启动 | 保持当前路径 |
| `scripts/post_game_live.ps1` | 局后归档 | 保持当前路径 |
| `scripts/summarize_live_windivert_brief.py` | live/archive brief | 后续可加 v3 shadow columns |
| `data/logs/live/` | 本地 live 日志 | ignored，本地运行态 |
| `data/samples/fatbeans/` | 本地 canonical archive 样本 | 441 份 JSON，默认脚本路径 |
| `data/samples/fatbeans_activity_20260605_shipwreck/` | 2026-06-05 沉船白转红活动 cohort | 15 份 JSON，manifest role=`activity_tuning_reference`；用于 source/table 与 shadow 调参参考，不进默认校准 |
| `data/samples/fatbeans_invalid/` | 旧 parse error/无效样本 | ignored，不进默认 evaluator |

## 数据目录

| 路径 | 作用 | 版本策略 |
| --- | --- | --- |
| `data/processed/` | 可提交的派生表和本地表缓存 | 保持现状 |
| `data/raw/` | 本地原始游戏表 | ignored |
| `data/review/` | 本地审计输出 | ignored |
| `data/tmp/` | 临时输出 | 已移动到 ignored local archive |
| `data/samples/synthetic_v2/` | 合成样本 | 保留 |
| `data/samples/fatbeans/` | 实机 Fatbeans canonical archive | 默认 baseline |
| `data/sample_manifests/fatbeans_activity_shipwreck_2026-06-05.json` | 252x activity cohort manifest | `activity_tuning_reference`；scope=`source_parser_table_acquisition_and_shadow_tuning_reference_only`；`affects_bid=false` |
| `data/samples/fatbeans_activity_20260605_shipwreck/` | 0605 后 252x 沉船活动样本 | 后续用于鲁棒性/活动映射、source parser/table acquisition 与 shadow-only 调参参考，不混入默认 baseline |
| `data/samples/fatbeans_manual_inbox/` | 手动导出样本 staging | 审查后并入 canonical archive 或独立 cohort |
| `data/samples/fatbeans_invalid/` | 无效真实样本隔离区 | 不计模型准确率 |

## 脚本与测试

当前脚本规模：

- Python scripts：111
- PowerShell scripts：13
- test files：117

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
| `.tmp/codex/` | Codex/pytest/审计临时输出统一目录；项目优化完成前保留，不逐次删除 |
| `.tmp/` 其他历史内容 | 已移动到 `archive/local_ignored/2026-06-04/.tmp/` |
| `data/tmp/` | 已移动到 `archive/local_ignored/2026-06-04/data_tmp/` |
| `dist/` | 已移动到 `archive/local_ignored/2026-06-04/dist/` |
| `tools/ilspycmd` | 已移动到 `archive/local_ignored/2026-06-04/tools/` |

`archive/local_ignored/` 是本地 ignored 归档，不参与 git 提交。

后续 Codex 临时验证输出统一放在 `.tmp/codex/`，pytest 使用 `.tmp/codex/pytest`，阶段结束后再统一清理。
