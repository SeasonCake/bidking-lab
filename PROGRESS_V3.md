# BidKing Lab v3 Progress

日期：2026-06-04  
主线：v3 推理引擎重构，v2 保持可运行基线。

## 当前状态

- 最新 checkpoint：`4d3aa9f Checkpoint v3 inference kickoff`
- v3 设计完成：[`docs/v3_inference_design_2026-06-04.zh-CN.md`](docs/v3_inference_design_2026-06-04.zh-CN.md)
- v3 evidence registry 骨架已进入源码：`src/bidking_lab/inference/v3/`
- v3 coverage 脚本已可运行：`scripts/summarize_v3_evidence_coverage.py`
- v2 正式估值、live formal、UI 当前设计暂时保持，不做视觉重做。

## 已完成

### Phase 0：设计与 checkpoint

- 明确停止把 v2 调参作为主线。
- 记录 v2 已确认问题：输入覆盖缺机制、q6 sampler 耦合、hard exact rejection、软证据语义分散、五窗口数据质量混杂。
- 提交前全量验证：`C:\Python313\python.exe -m pytest -q` 为 `882 passed`。
- 建立 checkpoint commit：`4d3aa9f Checkpoint v3 inference kickoff`。

### Phase 1：Evidence registry

- 新增 `EvidenceSpec`、`EvidenceEvent`、`EvidenceCoverageReport`。
- public info 语义迁入 `src/bidking_lab/inference/v3/evidence_registry.py`。
- `scripts/evaluate_fatbeans_v2_samples.py` 已改为调用 v3 public registry，避免 v2 evaluator 和 v3 registry 分叉。
- 当前 350 个可解析 archive 样本无 unknown/pending public/action/skill id。

### Phase 2 起步：Hard numeric constraint compiler

- 新增 `compile_hard_constraints()`。
- 已支持 exact numeric target 编译和冲突报告。
- 已记录 item/shape/quality-floor anchor events，下一步继续编译成可行空间。

### Phase 2 追加：Item/shape/quality-floor anchor 编译

- `EvidenceEvent.payload` 现在保留每个 observed item 的结构化字段：
  runtime_id、local_index、item_id、quality、value、shape_key、cells。
- `compile_hard_constraints()` 现在输出：
  - `item_anchors`
  - `shape_anchors`
  - `quality_floor_anchors`
  - exact numeric `conflicts`
- quality-only / 宝光类证据继续只生成 `quality_floor_anchors`；没有 shape/cells 时不生成 footprint。
- category outline 会把 category id 保留到 item anchor，避免后续可行空间丢类别条件。
- 新增复跑脚本：`scripts/summarize_v3_constraints.py`。
- 当前 355 archive 扫描：
  - parsed_files `350`
  - numeric constraints `549`
  - item anchors `1,851`
  - shape anchors `10,083`
  - quality-floor anchors `1,384`
  - hard conflicts `0`
  - 5 个旧样本 parse error 继续按数据质量问题单独处理。
- 验证：
  - `C:\Python313\python.exe .\scripts\summarize_v3_constraints.py --fail-on-conflicts` 通过。
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_evidence_registry.py tests\test_evaluate_fatbeans_v2_samples.py -q`
    为 `47 passed`。

### Phase 3 起步：Archive pre-bid ConstraintSet evaluator skeleton

- 新增 `scripts/evaluate_fatbeans_v3_samples.py`。
- 该脚本是 shadow-only skeleton，不计算 posterior value，不影响 live/formal bid。
- 复用当前五窗口合同：每个 `SEND 0x0022` 报价前的 prefix 作为 pre-bid window。
- 每个窗口输出：
  - `ready`
  - `no_state`
  - `constraint_conflict`
  - parse error 作为文件级 data quality
  - numeric/item/shape/quality-floor anchor 数量
- 当前 355 archive 扫描：
  - windows `1,262`
  - ready `1,247`
  - no_state `15`
  - constraint_conflict `0`
  - parse_errors `5`
  - prebid numeric constraints `1,386`
  - prebid item anchors `5,137`
  - prebid shape anchors `27,549`
  - prebid quality-floor anchors `4,678`
- 新增测试：`tests/test_evaluate_fatbeans_v3_samples.py`。
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_evidence_registry.py -q`
    为 `10 passed`。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts` 通过。

### Phase 3 增量：v3 prior/truth shadow report skeleton

- 新增 `src/bidking_lab/inference/v3/priors.py`：
  - 复用 `prepare_session_sampler()` 的 map/drop/item 解析结果。
  - 用解析式输出 drop prior，不依赖随机 trials。
  - 输出 total 与 q6 的 expected count/cells/value、draw probability、session probability。
- 新增 `src/bidking_lab/inference/v3/truth.py`：
  - 从 Fatbeans settlement inventory 提取 raw truth。
  - 输出 total/q6 raw value、count、cells。
  - 当前不复刻 v2 formal/tail-replacement truth，不改变正式口径。
- `scripts/evaluate_fatbeans_v3_samples.py` 已接入 shadow 字段：
  - 默认加载本地 tables，输出 `v3_prior_*` 与 `v3_truth_*`。
  - 新增 `--skip-table-report` 保留纯 constraint 轻量路径。
- 当前 355 archive 扫描：
  - windows `1,262`
  - ready `1,247`
  - no_state `15`
  - constraint_conflict `0`
  - parse_errors `5`
  - prior_ready `1,247`
  - truth_ready `1,262`
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_priors_truth.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_evidence_registry.py -q`
    为 `13 passed`。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts` 通过。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --skip-table-report --fail-on-conflicts` 通过。

### Phase 3 增量：per-window formal/replacement truth

- 扩展 `src/bidking_lab/inference/v3/truth.py`：
  - `DecisionTruthReport`
  - `decision_truth_from_fatbeans()`
  - `empty_decision_truth_flat_dict()`
- 扩展 `src/bidking_lab/inference/v3/priors.py`：
  - `ordinary_shape_replacement_values()`，按 map/drop 权重输出同品质同形状普通物品 P50 replacement。
- 裁尾口径：
  - confusable long tail 必须 exact item anchor 才进入 formal。
  - 其他 `>= DEFAULT_VALUE_FLOOR` 高价值物品需要 exact item anchor 或 category evidence 支持。
  - tail replacement 仍是 audit/helper truth，不进入 formal。
- `scripts/evaluate_fatbeans_v3_samples.py` 现在输出：
  - raw truth：`v3_truth_raw_total_value` 等。
  - formal truth：`v3_truth_formal_decision_value`、`v3_truth_q6_formal_decision_value`。
  - replacement truth：`v3_truth_tail_replacement_decision_value`、`v3_truth_q6_tail_replacement_decision_value`。
- 当前 355 archive 扫描：
  - windows `1,262`
  - ready `1,247`
  - no_state `15`
  - prior_ready `1,247`
  - truth_ready `1,262`
  - decision_truth_ready `1,247`
  - constraint_conflict `0`
  - parse_errors `5`
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_priors_truth.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_evidence_registry.py -q`
    为 `15 passed`。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts` 通过。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --skip-table-report --fail-on-conflicts` 通过。

### Phase 3 增量：feasible summary generator

- 新增 `src/bidking_lab/inference/v3/summary.py`：
  - `BucketFeasibleSummary`
  - `FeasibleSummaryReport`
  - `compile_feasible_summary()`
  - `empty_feasible_summary_flat_dict()`
- summary 负责把 hard numeric exact 与 deduped item/shape/quality anchors 合成 per-quality floors：
  - exact：session total count/cells，bucket count/cells/value。
  - floor：anchor count/cells/value。
  - residual exact：例如 q6 exact count/cells/value 扣掉已知 floor 后的剩余。
  - conflict：`floor > exact`、bucket exact sum 超过 session exact 等。
- 同时修复 `compile_hard_constraints()`：
  - 带 `shape_anchors` 且有 observed_items 的 outline/full-outline 事件，count/cells exact 从 observed_items 派生。
  - 不再把同一个 payload value 同时套到 count 和 cells。
- `scripts/evaluate_fatbeans_v3_samples.py` 现在输出 `v3_summary_*`。
- 当前 355 archive 扫描：
  - windows `1,262`
  - ready `1,247`
  - no_state `15`
  - summary_ready `1,247`
  - summary_conflict `0`
  - constraint_conflict `0`
  - parse_errors `5`
  - prebid numeric constraints `4,818`
- 全文件 constraint summary：
  - numeric `1,908`
  - item anchors `1,851`
  - shape anchors `10,083`
  - quality-floor anchors `1,384`
  - conflicts `0`
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_evidence_registry.py -q`
    为 `18 passed`。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts` 通过。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --skip-table-report --fail-on-conflicts` 通过。
  - `C:\Python313\python.exe .\scripts\summarize_v3_constraints.py --fail-on-conflicts` 通过。

### Phase 3 增量：q6 count-cell-value posterior shadow skeleton

- 新增 `src/bidking_lab/inference/v3/posterior.py`：
  - `V3PosteriorReport`
  - `sample_truth_bank()`
  - `truth_matches_feasible_summary()`
  - `estimate_q6_posterior_from_truths()`
  - `empty_posterior_flat_dict()`
- `scripts/evaluate_fatbeans_v3_samples.py` 新增：
  - `v3_post_*` shadow 字段。
  - `--posterior-trials`，默认 `512`；`0` 可关闭。
  - `--posterior-seed`。
- 当前 sampler 是两层 shadow：
  - `match_scope=strict`：完整 `FeasibleSummaryReport` exact/floor 全部命中。
  - `match_scope=q6_projection`：strict 无命中时，只按 q6 bucket exact/floor 过滤，明确标记 fallback。
  - `v3_post_affects_bid=False`。
- 当前 355 archive 扫描，默认 `512` prior samples/map：
  - windows `1,262`
  - ready `1,247`
  - posterior_ready `1,247`
  - posterior_strict_ready `359`
  - posterior_fallback `888`
  - posterior_no_match `0`
  - summary_conflict `0`
  - constraint_conflict `0`
- 2048 samples/map 对照：
  - posterior_strict_ready `422`
  - 说明 strict no-match 主要不是 trials 不足，而是需要更好的条件 proposal / feasible generator。
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_evidence_registry.py -q`
    为 `21 passed`。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts` 通过。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --skip-table-report --posterior-trials 0 --fail-on-conflicts` 通过。
  - `C:\Python313\python.exe .\scripts\summarize_v3_constraints.py --fail-on-conflicts` 通过。

### Phase 3 增量：posterior formal/replacement value fields

- `src/bidking_lab/inference/v3/truth.py` 新增 `decision_truth_from_session_truth()`。
- settlement truth 与 sampled `SessionTruth` 共用同一套 plannable/tail-replacement 规则。
- `V3PosteriorReport` 新增 quantiles：
  - `v3_post_formal_decision_value_*`
  - `v3_post_tail_replacement_decision_value_*`
  - `v3_post_q6_formal_decision_value_*`
  - `v3_post_q6_tail_replacement_decision_value_*`
- 当前 archive smoke 与上一阶段一致：
  - posterior_ready `1,247`
  - posterior_strict_ready `359`
  - posterior_fallback `888`
  - posterior_no_match `0`
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_evidence_registry.py -q`
    为 `22 passed`。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts` 通过。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --skip-table-report --posterior-trials 0 --fail-on-conflicts` 通过。

### Phase 3 增量：archive paired metrics

- `scripts/evaluate_fatbeans_v3_samples.py` summary 新增默认 paired metrics：
  - `formal_p50_mae`
  - `formal_p50_bias`
  - `formal_p50_below_rate`
  - `formal_p50_pinball`
  - `formal_p90_coverage`
  - `formal_p90_pinball`
  - `q6_formal_p50_mae`
  - `q6_formal_p50_bias`
  - `q6_formal_p50_below_rate`
  - `q6_formal_p90_coverage`
  - `q6_formal_p90_pinball`
  - strict/fallback 分拆：`*_strict`、`*_fallback`
- 默认 metric 口径：
  - prediction：`v3_post_formal_decision_value_p50`
  - truth：`v3_truth_formal_decision_value`
- 当前 355 archive、512 samples/map：
  - metric_rows `1,247`
  - formal_p50_mae `347,622.463`
  - formal_p50_mae_strict `359,635.128`
  - formal_p50_mae_fallback `342,765.991`
  - formal_p90_coverage `0.768244`
  - q6_formal_p50_mae `304,356.084`
  - q6_formal_p50_mae_strict `321,732.513`
  - q6_formal_p50_mae_fallback `297,331.154`
- 结论：当前 posterior skeleton 只提供可评估基线，不可 promotion；strict 命中也不是质量保证。
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_evidence_registry.py -q`
    为 `23 passed`。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts` 通过。

### Phase 3 增量：Fatbeans sample manifest

- 新增 `scripts/summarize_fatbeans_sample_manifest.py`，输出文件级样本清单，不移动或改写原始 capture。
- 已生成当前清单：`data/sample_manifests/fatbeans_archive_v3_2026-06-04.json`。
- manifest 明确区分：
  - 真实 capture 文件数。
  - 从 `SEND 0x0022` 派生的 pre-bid 窗口数。
  - `valid`、`mixed`、`invalid` 文件级状态。
  - `ready`、`no_state`、`constraint_conflict` 窗口级状态。
  - public info/action/skill 证据出现次数。
- 当前 355 archive 分层：
  - `parsed_files=350`
  - `valid_files=335`
  - `mixed_files=15`
  - `invalid_files=5`
  - `usable_metric_files=350`
  - `bid_windows=1262`
  - `ready_windows=1247`
  - `no_state_windows=15`
  - `constraint_conflict_windows=0`
- `mixed` 文件保留可用 ready 窗口，但 no-state 缺口窗口不计入模型准确率。
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_summarize_fatbeans_sample_manifest.py tests\test_evaluate_fatbeans_v3_samples.py -q`
    为 `6 passed`。
  - `C:\Python313\python.exe .\scripts\summarize_fatbeans_sample_manifest.py`
    通过。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --skip-table-report --posterior-trials 0 --fail-on-conflicts`
    通过。

### Phase 3 增量：manual inbox 样本审查

- `data/samples/fatbeans_manual_inbox` 收到 77 份手动导出 JSON，非 78 份。
- 修正 `scripts/rename_manual_fatbeans_samples.py`：
  - 占位名如 `hero_map_rounds`、`ethan_map_rounds` 不再误判为已命名。
  - 新增 `--renumber-all`，按文件修改时间连续编号。
  - 应用重命名时使用两阶段 rename，避免目标名与现有文件互相占用。
- 已对 inbox 执行连续重命名，当前范围为 `manual_2026-06-04_001_...json` 到
  `manual_2026-06-04_077_...json`。
- 单独 inbox 质量：
  - `files=77`
  - `parsed_files=77`
  - `valid_files=77`
  - `ready_windows=264`
  - `parse_errors=0`
  - `no_state_windows=0`
  - `constraint_conflict_windows=0`
- 与主样本库合并的轻量口径：
  - `files=432`
  - `parsed_files=427`
  - `usable_metric_files=427`
  - `ready_windows=1511`
  - 仅保留旧主库 5 个 parse error。
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_rename_manual_fatbeans_samples.py tests\test_summarize_fatbeans_sample_manifest.py -q`
    为 `7 passed`。
  - `C:\Python313\python.exe .\scripts\summarize_fatbeans_sample_manifest.py .\data\samples\fatbeans_manual_inbox`
    通过。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py .\data\samples\fatbeans .\data\samples\fatbeans_manual_inbox --skip-table-report --posterior-trials 0 --fail-on-conflicts`
    通过。

### Phase 3 增量：真实样本 canonical archive

- 新增 `scripts/organize_fatbeans_real_samples.py`，统一整理真实 Fatbeans 样本。
- 已执行 canonical 整理：
  - `data/samples/fatbeans` 主样本库改为统一命名。
  - `data/samples/fatbeans_manual_inbox` 的 77 份样本已并入主样本库。
  - `data/logs/live/raw/archive/complete` 中 6 个未入库完整局已复制进主样本库。
  - 4 个 live complete 重复 session 保留在 live 日志，不重复并入。
  - 5 个旧 parse error 样本已移至 `data/samples/fatbeans_invalid/parse_error`。
- 新 current manifest：
  - `data/sample_manifests/fatbeans_archive_v3_2026-06-05.json`
  - `data/sample_manifests/fatbeans_organize_plan_2026-06-05.json`
- 当前默认主样本库：
  - `files=433`
  - `parsed_files=433`
  - `valid_files=416`
  - `mixed_files=17`
  - `parse_errors=0`
  - `ready_windows=1534`
  - `no_state_windows=17`
  - `constraint_conflict_windows=0`
- v3 coverage：
  - `events=12473`
  - `coverage_ok=True`
  - `unknown=none`
  - `pending=none`
- v3 constraints：
  - `numeric=2172`
  - `item_anchors=2429`
  - `shape_anchors=11572`
  - `quality_floor_anchors=1803`
  - `conflicts=0`
- 当前 512 samples/map v3 posterior skeleton：
  - `metric_rows=1534`
  - `posterior_strict_ready=513`
  - `posterior_fallback=1021`
  - `formal_p50_mae=335,384.256`
  - `formal_p50_mae_strict=330,542.046`
  - `formal_p50_mae_fallback=337,817.217`
  - `formal_p90_coverage=0.767927`
  - `q6_formal_p50_mae=295,848.365`
- 验证：
  - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_organize_fatbeans_real_samples.py tests\test_rename_manual_fatbeans_samples.py tests\test_summarize_fatbeans_sample_manifest.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py::test_ethan_sample37_residual_does_not_break_exact_bucket_targets -q`
    为 `14 passed`。
  - `C:\Python313\python.exe .\scripts\summarize_fatbeans_sample_manifest.py .\data\samples\fatbeans`
    通过。
  - `C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts`
    通过。
  - `C:\Python313\python.exe .\scripts\summarize_v3_evidence_coverage.py --fail-on-gaps`
    通过。
  - `C:\Python313\python.exe .\scripts\summarize_v3_constraints.py --fail-on-conflicts`
    通过。

### 记录整理

- 根目录大记录已改为索引：
  - `PROGRESS.md`
  - `DECISIONS.md`
  - `OBSERVATIONS.md`
- v2 历史大记录已归档：
  - `archive/v2_legacy_2026-06-04/records/PROGRESS.v2.md`
  - `archive/v2_legacy_2026-06-04/records/DECISIONS.v2.md`
  - `archive/v2_legacy_2026-06-04/records/OBSERVATIONS.v2.md`
- v2 handoff 已归档到 `archive/v2_legacy_2026-06-04/handoffs/`；根目录保留 `handoff_2026-06-04.zh-CN.md`
  指针。
- 本地 ignored 的 `.pytest_cache/`、`.tmp/`、`data/tmp/`、`dist/`、`tools/ilspycmd` 已移到
  `archive/local_ignored/2026-06-04/`，不参与 git。

## 当前数据基线

- Fatbeans 本地样本：`data/samples/fatbeans`，当前 433 份 canonical JSON。
- v3 coverage 可解析样本：433 份。
- Fatbeans invalid 样本：`data/samples/fatbeans_invalid/parse_error`，当前 5 份旧 parse error。
- `data/samples/fatbeans_manual_inbox` 当前为空，用于后续手动导出 staging。
- v3 canonical evidence events：12,473。
- 当前 coverage：`coverage_ok=True`，unknown/pending 均为 `none`。

复跑命令：

```powershell
C:\Python313\python.exe .\scripts\summarize_v3_evidence_coverage.py --fail-on-gaps
```

## 下一步

1. 按 hero/map/round/match_scope 拆分 v3 metrics，定位 2601、2506、2501 等当前高 MAE 地图。
2. 继续校准 summary-likelihood 的 q6/value tail；重点看 q6 presence 只有低信息量时的保守低估。
3. 接 live/UI/archive 的 v3 shadow 字段，默认 `affects_bid=false`。

## 不做事项

- 不重做 UI 视觉。当前 UI 设计冻结保留。
- 不接 Fatbeans 会员 WebHook 路线。
- 不把 tail replacement 接入正式出价。
- 不直接把 v3 shadow 改成 formal decision。

## 2026-06-05 checkpoint：v3 summary-likelihood posterior 第一版

已完成：

- `match_scope=strict` 保持原硬命中语义。
- strict 无命中时，新增 `match_scope=summary_likelihood`：
  - 消费 `FeasibleSummaryReport`，不绕过 compiler 直接解释 raw payload。
  - session total count/cells exact、known floors、各品质 count/cells/value exact/floor 全部进入 likelihood。
  - q6 证据有轻量 boost，但不会把 q6 projection 直接升为正式路径。
  - P50 使用 evidence-weighted posterior，并加温和 lower guard，减少实战低估。
  - P90 使用 tail guard，从 likelihood support 保留长尾，不让 P50 校准压掉覆盖。
- evaluator 新增 scope 计数：
  - `posterior_summary_likelihood`
  - `posterior_q6_projection`
  - `metric_summary_likelihood_rows`
  - `metric_q6_projection_rows`
  - `posterior_scope_counts`

433 canonical 样本、512 samples/map 当前指标：

```text
windows=1551
ready=1534
no_state=17
constraint_conflict=0
parse_errors=0
posterior_ready=1534
posterior_strict_ready=513
posterior_summary_likelihood=1021
posterior_q6_projection=0
metric_rows=1534
formal_p50_mae=329399.887
formal_p50_mae_strict=330542.046
formal_p50_mae_fallback=328826.011
formal_p50_bias=-188482.821
formal_p50_below_rate=0.632986
formal_p90_coverage=0.769883
q6_formal_p50_mae=295957.275
q6_formal_p50_mae_fallback=294703.346
q6_formal_p50_bias=-133583.532
q6_formal_p50_below_rate=0.582790
q6_formal_p90_coverage=0.815515
```

相对 canonical skeleton 基线：

- `formal_p50_mae`：`335384.256 -> 329399.887`，下降约 `5,984`。
- `formal_p50_mae_fallback`：`337817.217 -> 328826.011`，下降约 `8,991`。
- `formal_p90_coverage`：`0.767927 -> 0.769883`，小幅上升。
- `q6_formal_p50_mae`：`295848.365 -> 295957.275`，基本持平，fallback 略优于旧 fallback。

按轮次 formal P50：

```text
R1 n=416 mae=351780.1 bias=-194490.4 below=0.640 p90cover=0.730
R2 n=407 mae=320266.2 bias=-190904.0 below=0.640 p90cover=0.770
R3 n=360 mae=310245.8 bias=-167713.0 below=0.610 p90cover=0.800
R4 n=248 mae=333422.1 bias=-194834.7 below=0.620 p90cover=0.790
R5 n=103 mae=332362.8 bias=-211951.8 below=0.690 p90cover=0.780
```

当前高 MAE 地图：

```text
2601 n=86 mae=614055.0 bias=-467064.5 below=0.77
2506 n=71 mae=502413.1 bias=-444963.9 below=0.82
2509 n=40 mae=414159.0 bias=-167713.2 below=0.57
2503 n=37 mae=372821.0 bias=-199747.8 below=0.70
2501 n=310 mae=367176.4 bias=-274498.7 below=0.70
```

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_organize_fatbeans_real_samples.py tests\test_rename_manual_fatbeans_samples.py tests\test_summarize_fatbeans_sample_manifest.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_posterior.py tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_inference_v3_evidence_registry.py tests\test_live_monitor.py::test_ethan_sample37_residual_does_not_break_exact_bucket_targets -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
```

结果：`33 passed`，全样本 evaluator 通过。

### 新增诊断工具

新增：

```powershell
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_id --top 8
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by round --by v3_post_match_scope
```

用途：按固定字段输出 paired formal/q6 MAE、bias、below rate、P90 coverage，以及 strict / summary-likelihood
计数，避免后续 sampler 调参只看全局均值。

当前 `--by map_id --top 8` 显示：

```text
2601 n=86 mae=614055.0 bias=-467064.5 p90_cover=0.569767 q6_mae=540020.2
2506 n=71 mae=502413.1 bias=-444963.9 p90_cover=0.605634 q6_mae=456777.5
2509 n=40 mae=414159.0 bias=-167713.2 p90_cover=0.725000 q6_mae=373788.5
2503 n=37 mae=372821.0 bias=-199747.8 p90_cover=0.783784 q6_mae=327518.5
2501 n=310 mae=367176.4 bias=-274498.7 p90_cover=0.696774 q6_mae=328573.6
```

结论：下一轮不是全局调高，而是优先解释 2601、2506、2501 为什么在 formal/q6 上都系统低估。

## 2026-06-05 checkpoint：posterior 硬约束下界 guard

问题：

- 诊断 2501 top miss 时发现一个窗口 `q6_value_floor=1,553,900`，但
  `v3_post_q6_formal_decision_value_p90=1,210,464`。
- 这不是 sampler 权重问题，而是 posterior 输出没有把 `FeasibleSummaryReport` 中已经确定的
  floor/exact 重新投影到 quantile 字段。

修复：

- raw posterior 字段守住硬约束：
  - `total_cells` 使用 `session_total_cells_exact` 或 `known_cells_floor`。
  - `total_value` 使用 `known_value_floor`。
  - `q6_count/q6_cells/q6_value` 使用 q6 bucket exact/floor。
- formal/tail-replacement decision 字段守住 item-anchor 汇总出的 `known_value_floor`：
  - `formal_decision_value`
  - `tail_replacement_decision_value`
  - `q6_formal_decision_value`
  - `q6_tail_replacement_decision_value`
- 不把公开 aggregate `value_exact` 直接当作 formal plannable 值；它只约束 raw bucket value。

433 canonical 样本、512 samples/map 当前指标：

```text
formal_p50_mae=325128.627
formal_p50_mae_strict=325206.588
formal_p50_mae_fallback=325089.455
formal_p50_bias=-184211.561
formal_p50_below_rate=0.632986
formal_p90_coverage=0.769883
q6_formal_p50_mae=289689.021
q6_formal_p50_mae_strict=291964.226
q6_formal_p50_mae_fallback=288545.847
q6_formal_p50_bias=-127315.277
q6_formal_p50_below_rate=0.580834
q6_formal_p90_coverage=0.815515
```

相对 summary-likelihood 第一版：

- `formal_p50_mae`：`329399.887 -> 325128.627`，下降约 `4,271`。
- `q6_formal_p50_mae`：`295957.275 -> 289689.021`，下降约 `6,268`。
- `formal_p50_bias`：`-188482.821 -> -184211.561`，低估略缓解。
- `P90 coverage` 保持不变。

分片变化：

- 2501 明显改善：`formal_mae 367176.4 -> 362810.8`，`q6_mae 328573.6 -> 320906.7`。
- 2601、2506 基本不动，说明它们不是 floor 投影缺口，而是 q6/tail prior 条件建模不足。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_organize_fatbeans_real_samples.py tests\test_rename_manual_fatbeans_samples.py tests\test_summarize_fatbeans_sample_manifest.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_posterior.py tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_inference_v3_evidence_registry.py tests\test_live_monitor.py::test_ethan_sample37_residual_does_not_break_exact_bucket_targets tests\test_summarize_v3_metric_slices.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_id --top 8
```

结果：`36 passed`，全样本 evaluator 通过。

## 2026-06-05 checkpoint：anchor-aware posterior likelihood

问题：

- 2601/2506 修复 hard floor 后仍系统低估。
- 进一步审查发现 v3 summary 只保留 quality count/cell/value，丢掉了 item/category/shape anchor 对
  formal plannable 判断的影响。
- `decision_truth_from_*` 会用 exact/category support 决定高值 item 是否进入 formal decision；posterior
  sampler 若不按 anchor 匹配加权，就会低估这些被道具支持的高值红品。

修复：

- posterior likelihood 新增 anchor match 权重：
  - `ItemAnchor`：按 item_id、value、category、shape/cells、quality 匹配样本 item。
  - `ShapeAnchor`：对未被 item anchor 覆盖的 shape/cell/quality 做匹配。
  - strict matched 样本集合也会按 anchor 权重重排；summary-likelihood fallback 会把 anchor log-likelihood
    叠加到 summary log-likelihood。
- 仍不改变 hard summary，不改变正式出价，`affects_bid=false`。

433 canonical 样本、512 samples/map 当前指标：

```text
formal_p50_mae=323364.373
formal_p50_mae_strict=324863.640
formal_p50_mae_fallback=322611.068
formal_p50_bias=-170223.445
formal_p50_below_rate=0.622555
formal_p90_coverage=0.780965
q6_formal_p50_mae=289531.125
q6_formal_p50_mae_strict=293163.116
q6_formal_p50_mae_fallback=287706.237
q6_formal_p50_bias=-114997.727
q6_formal_p50_below_rate=0.567145
q6_formal_p90_coverage=0.828553
```

相对 hard-bound guard：

- `formal_p50_mae`：`325128.627 -> 323364.373`，继续下降约 `1,764`。
- `formal_p90_coverage`：`0.769883 -> 0.780965`。
- `q6_formal_p50_mae`：`289689.021 -> 289531.125`，基本持平略好。
- `q6_formal_p90_coverage`：`0.815515 -> 0.828553`。
- `formal_p50_bias`：`-184211.561 -> -170223.445`，低估继续缓解。

分片：

```text
2601 n=86 mae=594835.6 bias=-438014.8 p90_cover=0.581395 q6_mae=533650.4
2506 n=71 mae=497158.7 bias=-425473.2 p90_cover=0.605634 q6_mae=453468.5
2501 n=310 mae=363304.4 bias=-256607.5 p90_cover=0.709677 q6_mae=321219.2
2507 n=74 mae=324716.0 bias=-42013.3 p90_cover=0.837838 q6_mae=323266.1
```

结论：

- anchor-aware likelihood 对全局、2601、2506 是正向，但 2507 分片回退。
- 2601/2506 仍明显低估，下一步需要 map-tail / q6 value 条件 proposal，而不是继续只靠重权。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_organize_fatbeans_real_samples.py tests\test_rename_manual_fatbeans_samples.py tests\test_summarize_fatbeans_sample_manifest.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_posterior.py tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_inference_v3_evidence_registry.py tests\test_live_monitor.py::test_ethan_sample37_residual_does_not_break_exact_bucket_targets tests\test_summarize_v3_metric_slices.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_id --top 8
```

结果：`37 passed`，全样本 evaluator 通过。

## 2026-06-05 checkpoint：practical P50 support guard

问题：

- 2601/2506 的剩余 top miss 多数不是 hard floor 缺失，而是 q6 count/cell/value 的真实值落在地图厚尾。
- 用户实战反馈长期偏低估，允许适度更激进，但不能牺牲整体 MAE。
- 当前 weighted P50 即使用 support median guard，仍对厚尾地图保守。

修复：

- 将 likelihood-weighted posterior 的 P50 support guard 从未加权 P50 提升到未加权 P60。
- 只在已有 likelihood weights 的窗口生效；无 evidence weights 的 strict prior 不受影响。
- P90 tail guard 不变。
- evaluator 和 slice 诊断新增：
  - `formal_p50_over_rate`
  - `q6_formal_p50_over_rate`

433 canonical 样本、512 samples/map 当前指标：

```text
formal_p50_mae=316976.209
formal_p50_mae_strict=320981.105
formal_p50_mae_fallback=314963.955
formal_p50_bias=-129378.797
formal_p50_below_rate=0.582790
formal_p50_over_rate=0.417210
formal_p90_coverage=0.780965
q6_formal_p50_mae=287225.034
q6_formal_p50_mae_strict=294466.555
q6_formal_p50_mae_fallback=283586.543
q6_formal_p50_bias=-70104.765
q6_formal_p50_below_rate=0.505867
q6_formal_p50_over_rate=0.490222
q6_formal_p90_coverage=0.828553
```

相对 anchor-aware likelihood：

- `formal_p50_mae`：`323364.373 -> 316976.209`，下降约 `6,388`。
- `formal_p50_bias`：`-170223.445 -> -129378.797`，低估明显缓解。
- `formal_p50_below_rate`：`0.622555 -> 0.582790`。
- `q6_formal_p50_mae`：`289531.125 -> 287225.034`，下降约 `2,306`。
- `q6_formal_p50_below_rate`：`0.567145 -> 0.505867`，q6 P50 接近平衡。

分片：

```text
2601 n=86 mae=579876.3 bias=-409070.1 below=0.755814 over=0.244186 q6_mae=504121.7
2506 n=71 mae=472738.8 bias=-394345.0 below=0.746479 over=0.253521 q6_mae=435284.4
2501 n=310 mae=348661.3 bias=-206859.0 below=0.638710 over=0.361290 q6_mae=311027.5
2507 n=74 mae=331450.1 bias=5958.6 below=0.378378 over=0.621622 q6_mae=333991.3
2508 n=54 mae=275955.0 bias=21238.3 below=0.537037 over=0.462963 q6_mae=234905.1
```

结论：

- 全局 MAE/bias 继续改善，且 q6 P50 below/over 接近平衡。
- 2601/2506 仍低估，但比前一版明显缓解。
- 2507/2508/2505 已出现正 bias 或 over-rate 偏高，下一步若继续激进必须做 map/证据条件化，而不是继续全局提高 guard。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_organize_fatbeans_real_samples.py tests\test_rename_manual_fatbeans_samples.py tests\test_summarize_fatbeans_sample_manifest.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_posterior.py tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_inference_v3_evidence_registry.py tests\test_live_monitor.py::test_ethan_sample37_residual_does_not_break_exact_bucket_targets tests\test_summarize_v3_metric_slices.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_id --top 12
```

结果：`38 passed`，全样本 evaluator 通过。

## 2026-06-05 checkpoint：map-calibrated practical guard

问题：

- 全局 support P60 guard 改善了低估，但 2507/2508/2505 等地图开始出现正 bias 或 over-rate 偏高。
- 继续全局抬高不可取；需要让 guard 根据地图风险分层。

修复：

- v3 shadow posterior 的 practical P50 guard 改为地图校准：
  - high-tail maps：support P65，当前 `2404/2501/2503/2506/2601`。
  - low-tail maps：support P55，当前 `2407/2410/2505/2507/2508`。
  - 其他地图：support P60。
- 每个 weighted posterior 会在 diagnostics 中记录 `practical_p50_guard_quantile=...`。
- 仍只在已有 likelihood weights 的窗口生效，`affects_bid=false`。

433 canonical 样本、512 samples/map 当前指标：

```text
formal_p50_mae=313387.992
formal_p50_bias=-122240.706
formal_p50_below_rate=0.573012
formal_p50_over_rate=0.426988
formal_p90_coverage=0.780965
q6_formal_p50_mae=283903.670
q6_formal_p50_bias=-63074.925
q6_formal_p50_below_rate=0.487614
q6_formal_p50_over_rate=0.508475
q6_formal_p90_coverage=0.828553
```

相对全局 P60 guard：

- `formal_p50_mae`：`316976.209 -> 313387.992`，下降约 `3,588`。
- `q6_formal_p50_mae`：`287225.034 -> 283903.670`，下降约 `3,321`。
- `formal_p50_bias`：`-129378.797 -> -122240.706`。
- `q6_formal_p50_bias`：`-70104.765 -> -63074.925`。

分片：

```text
2601 n=86 mae=563274.2 bias=-379658.3 below=0.755814 over=0.244186 q6_mae=486057.4
2506 n=71 mae=459734.9 bias=-369867.9 below=0.746479 over=0.253521 q6_mae=418095.1
2501 n=310 mae=342930.5 bias=-171589.7 below=0.612903 over=0.387097 q6_mae=310317.5
2507 n=74 mae=327570.1 bias=-23952.7 below=0.378378 over=0.621622 q6_mae=326468.0
2508 n=54 mae=275920.0 bias=-6400.3 below=0.537037 over=0.462963 q6_mae=230400.0
2505 n=39 mae=270463.7 bias=-4161.5 below=0.487179 over=0.512821 q6_mae=252458.5
```

结论：

- 地图校准比全局 P60 更稳，同时继续降低 2601/2506/2501 低估。
- 2507 仍有 high over-rate，2601/2506 仍有 high below-rate；下一步要做真正的 q6 count/cell/value 条件 proposal。
- 该表来自当前 433 canonical 样本，是 v3 shadow calibration，不可直接作为 formal promotion 证明。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_organize_fatbeans_real_samples.py tests\test_rename_manual_fatbeans_samples.py tests\test_summarize_fatbeans_sample_manifest.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_posterior.py tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_inference_v3_evidence_registry.py tests\test_live_monitor.py::test_ethan_sample37_residual_does_not_break_exact_bucket_targets tests\test_summarize_v3_metric_slices.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_id --top 14
```

结果：`39 passed`，全样本 evaluator 通过。

## 2026-06-05 checkpoint：live artifact 接入 v3 posterior shadow

目标：

- 让实时监测产物能同步记录 v3 shadow posterior，方便后续实战样本直接做 v2/v3 对照。
- 不改变 v2 formal baseline、停止价、抢仓价或 UI 第一屏合同。

实现：

- `build_monitor_artifact_from_events` 新增 `v3_posterior_shadow`。
- shadow 使用当前 Fatbeans events 编译 v3 `ConstraintSet` / `FeasibleSummaryReport`，再用 `shadow_trials` 小样本 truth bank 生成 `V3PosteriorReport`。
- `model_eval` 新增 `v3_post_*`、`v3_summary_*`、v3 formal/q6 p50 error 与 p90 under-by 字段。
- `v3_post_affects_bid` 固定为 `False`；当前不进入 `ui_contract.shadows`，避免前端或实战读数误当正式建议。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_live_monitor.py -q
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_posterior.py tests\test_inference_v3_summary.py tests\test_inference_v3_priors_truth.py tests\test_inference_v3_evidence_registry.py tests\test_summarize_v3_metric_slices.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_id --top 14
```

结果：

- `tests/test_live_monitor.py`：`26 passed`。
- v3 核心测试：`29 passed`。
- 全样本 evaluator 仍为 `windows=1551 ready=1534 no_state=17 constraint_conflict=0 parse_errors=0`。
- 核心指标未因 live 接入变化：
  - `formal_p50_mae=313387.992`
  - `formal_p50_below_rate=0.573012`
  - `formal_p90_coverage=0.780965`
  - `q6_formal_p50_mae=283903.670`
  - `q6_formal_p50_below_rate=0.487614`
  - `q6_formal_p90_coverage=0.828553`
- 真实 canonical sample smoke：`v3_post_ready=True`、`v3_post_affects_bid=False`、`match_scope=summary_likelihood`。

后续：

- live JSONL 已具备记录 v3 shadow 的字段，后续新增实战样本可直接比较 v2 formal 与 v3 shadow。
- 下一步仍是 q6 count/cell/value 条件 proposal，而不是继续提高 global/map guard。

## 2026-06-05 checkpoint：q6 bucket-conditioned proposal

问题：

- 当前 v3 posterior 的 `summary_likelihood` fallback 会软匹配全局 summary。
- 对 q6 floor/exact 证据，旧实现多半只靠输出层 floor guard；如果 prior support 中未严格命中完整 summary，q6 分布容易贴着 floor，导致 fallback 负 bias。

实现：

- 当 `match_scope=summary_likelihood` 且 q6 bucket 有 count/cell/value 约束时，新增 q6 bucket-conditioned subset。
- q6 count/cells 使用满足 q6 bucket 约束的候选集。
- 只有存在 q6 value floor/exact 时，才用 q6-conditioned value/formal 分量替换原 fallback q6 value；避免只有 count/cells 证据时过度抬高价值。
- formal/raw 总值用“原 fallback 非 q6 分量 + conditioned q6 分量”重组。
- diagnostics 增加：
  - `q6_bucket_conditioned_samples=N`
  - `q6_bucket_conditioned_formal_adjustment`
  - anchor 权重命中时记录 `q6_bucket_conditioned_anchor_likelihood_weighted`。

当前 433 canonical 样本、512 samples/map 指标：

```text
formal_p50_mae=309872.088
formal_p50_mae_strict=315835.395
formal_p50_mae_fallback=306875.832
formal_p50_below_rate=0.544980
formal_p50_over_rate=0.455020
formal_p90_coverage=0.799870
q6_formal_p50_mae=282939.074
q6_formal_p50_mae_strict=289113.803
q6_formal_p50_mae_fallback=279836.591
q6_formal_p50_below_rate=0.462190
q6_formal_p50_over_rate=0.535854
```

相对 map-calibrated guard：

- `formal_p50_mae`：`313387.992 -> 309872.088`，下降约 `3,516`。
- `formal_p50_below_rate`：`0.573012 -> 0.544980`。
- `formal_p90_coverage`：`0.780965 -> 0.799870`。
- `q6_formal_p50_mae`：`283903.670 -> 282939.074`，下降约 `965`。
- `q6_formal_p50_below_rate`：`0.487614 -> 0.462190`，但 `over_rate` 升至 `0.535854`。

分片观察：

- summary-likelihood fallback：formal MAE `312158.3 -> 306875.8`，q6 MAE `281285.8 -> 279836.6`。
- round 3-5 的 formal MAE 与 P90 coverage 均改善。
- 2506/2501/2401 改善明显；2601 formal/q6 MAE 回退，仍是下一步重点。
- 2507/2505/2410 over-rate 仍偏高，后续不能继续全局加 aggressive guard。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_live_monitor.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_id --top 14
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by v3_post_match_scope --top 10
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by round --top 10
```

结果：`40 passed`，全样本 evaluator 通过。

结论：

- 这是比继续调高 guard 更合理的 v3 方向：让 q6 证据决定 q6 分布移动。
- 当前仍是 shadow calibration，不满足 formal promotion。
- 下一步应针对 2601 与 high-over maps 做 map/evidence gate，而不是继续扩大 q6-conditioned 强度。

## 2026-06-05 checkpoint：hidden cold-start gate + map_family slices

问题：

- q6 bucket-conditioned proposal 在整体和沉船上收益明确，但 hidden `2601` 样本少、truth 厚尾强，套用同一 q6-conditioned 逻辑会让 hidden MAE 回退。
- 后续需要稳定按 `shipwreck/villa/hidden` 分片，而不是每次用临时分析脚本推断地图族。

实现：

- v3 posterior 对 `2601` 暂停 q6 bucket-conditioned proposal，诊断记录：
  - `q6_bucket_conditioned=disabled_hidden_cold_start`
- `scripts/evaluate_fatbeans_v3_samples.py` 输出 `map_family` 字段：
  - `24xx/34xx/44xx -> villa`
  - `25xx/35xx/45xx -> shipwreck`
  - `26xx/36xx/46xx -> hidden`
- `scripts/summarize_v3_metric_slices.py --by map_family` 可直接输出 family 指标。

当前 433 canonical 样本、512 samples/map 指标：

```text
formal_p50_mae=308876.090
formal_p50_mae_strict=315835.395
formal_p50_mae_fallback=305379.397
formal_p50_below_rate=0.546936
formal_p50_over_rate=0.453064
formal_p90_coverage=0.799218
q6_formal_p50_mae=281387.105
q6_formal_p50_mae_strict=289113.803
q6_formal_p50_mae_fallback=277504.837
q6_formal_p50_below_rate=0.462842
q6_formal_p50_over_rate=0.535202
```

相对未 gate 的 q6-conditioned proposal：

- `formal_p50_mae`：`309872.088 -> 308876.090`，下降约 `996`。
- `q6_formal_p50_mae`：`282939.074 -> 281387.105`，下降约 `1,552`。
- `formal_p90_coverage` 小幅 `0.799870 -> 0.799218`，可接受。

`map_family` 分片：

```text
hidden    n=86  formal_mae=563274.2 q6_mae=486057.4
shipwreck n=833 formal_mae=326650.0 q6_mae=299233.0
villa     n=615 formal_mae=249227.5 q6_mae=228594.8
```

结论：

- hidden 目前应保持 cold-start shadow，不参与 q6-conditioned proposal 的主校准。
- 主要优化对象仍是 shipwreck 的低估，尤其 `2506/2501`。
- high-over maps 仍需后续保护 gate；本 checkpoint 只处理已确认的 hidden 回退问题。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_live_monitor.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_family --top 10
```

结果：`41 passed`，全样本 evaluator 通过。

## 2026-06-05 checkpoint：map audit + formal-only decision guard

实现：

- 新增 `scripts/summarize_v3_map_audit.py`：
  - 按 map 输出 sessions/windows/ready/no_state/rounds。
  - 同时输出 strict/fallback、formal/q6 MAE、bias、below/over、P90 coverage。
  - 标记 `few_sessions`、`few_windows`、`top3_heavy`、`mostly_fallback`、`little_public_total`、`systemic_under`、`high_over_rate`、`weak_q6_evidence`。
- 新增 `tests/test_summarize_v3_map_audit.py` 固定审计口径。
- v3 posterior 将 formal/total/tail-replacement decision guard 与 q6 diagnostic guard 分离：
  - q6 diagnostic 仍使用 D-v3-019 的地图分层 guard。
  - formal decision override：`2501=P75`、`2506=P75`、`2601=P85`。
  - override 生效时输出 `decision_p50_guard_quantile=*`。

当前指标：

```text
windows=1551 ready=1534 no_state=17 constraint_conflict=0 parse_errors=0
formal_p50_mae=301000.312
formal_p50_mae_strict=308631.749
formal_p50_mae_fallback=297165.908
formal_p50_below_rate=0.522164
formal_p50_over_rate=0.477836
formal_p90_coverage=0.799218
q6_formal_p50_mae=281387.105
q6_formal_p50_below_rate=0.462842
q6_formal_p50_over_rate=0.535202
```

分片：

```text
hidden    n=86  formal_mae=473580.9 q6_mae=486057.4
shipwreck n=833 formal_mae=321406.5 q6_mae=299233.0
villa     n=615 formal_mae=249227.5 q6_mae=228594.8
```

关键结论：

- `2601/2506/2501` 是系统性低估，不是少数极端样本问题。
- `2503/2505/2509/2408/2510` 当前样本偏少，先列 watchlist。
- `2507/2407` 属于 high-over 风险，后续保护 gate 要和低估地图分开。
- formal-only guard 降低 formal MAE 且 q6 MAE 完全不变，符合“实战参考可适度激进，但 q6 诊断不能被带偏”的边界。
- 下一步仍应做真正的 count/cell/value 条件 proposal，尤其针对 `2506` 的 mostly-fallback + little-public-total 低估。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_live_monitor.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_metric_slices.py --by map_family --top 10
C:\Python313\python.exe .\scripts\summarize_v3_map_audit.py --top 12
```

结果：`43 passed`，全样本 evaluator 通过。

## 2026-06-05 checkpoint：soft numeric likelihood + prior/archive calibration

实现：

- `ConstraintSet` 增加 `soft_numeric`：
  - 同一 soft source 重复出现时只保留最新 sort_id。
  - hard exact 与 item/shape/quality floor 逻辑不变。
- v3 posterior likelihood 消费：
  - `q4/q5/q6_avg_cells`
  - `q4/q5/q6_avg_value`
  - `total_avg_cells`
- 暂不消费：
  - `random_*_avg_value`
  - `size_*_avg_value`
- 新增 `scripts/summarize_v3_prior_archive_calibration.py`：
  - 对比 archive raw settlement truth 与表先验 `sample_truth_bank` 分布。
  - 输出 actual/prior P50/P90 和 ratio。

当前指标：

```text
windows=1551 ready=1534 no_state=17 constraint_conflict=0 parse_errors=0
formal_p50_mae=300553.241
formal_p50_mae_strict=307116.002
formal_p50_mae_fallback=297255.791
formal_p50_below_rate=0.521512
formal_p50_over_rate=0.478488
formal_p90_coverage=0.797914
q6_formal_p50_mae=281273.209
q6_formal_p50_below_rate=0.460887
q6_formal_p50_over_rate=0.537158
```

对比上一 checkpoint：

```text
formal_p50_mae 301000.312 -> 300553.241
q6_formal_p50_mae 281387.105 -> 281273.209
```

prior/archive calibration 发现：

```text
2506 median_ratio=1.843 p90_ratio=1.908
2501 median_ratio=1.571 p90_ratio=1.316
2601 median_ratio=1.626 p90_ratio=1.151
2401 median_ratio=1.418 p90_ratio=1.554
2507 median_ratio≈0.95
```

结论：

- soft avg likelihood 是 v3 必要输入补全，但只能带来小幅收益。
- `2506` 几乎不受 soft avg 影响，低估主因更像表先验与真实 archive 分布偏差。
- 下一步应做 empirical prior/calibration layer 的 shadow 设计：按 map/session 样本数、median/p90 ratio、high-over 风险决定是否校准；不能直接把所有 ratio 接入 formal。

验证：

```powershell
C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_evidence_registry.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_live_monitor.py -q
C:\Python313\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Python313\python.exe .\scripts\summarize_v3_map_audit.py --top 8
C:\Python313\python.exe .\scripts\summarize_v3_prior_archive_calibration.py --prior-trials 10000 --top 10
```

结果：`55 passed`，全样本 evaluator 通过。

## 2026-06-05 checkpoint：empirical prior calibration shadow

实现：

- 新增 `src/bidking_lab/inference/v3/calibration.py`
  - `PriorCalibrationEntry`
  - `V3PriorCalibrationReport`
  - `propose_prior_calibration()`
  - `calibrate_posterior_report()`
- 新增 `scripts/build_v3_prior_calibration_shadow.py`
  - 从 canonical archive 生成聚合派生表。
  - 输出 `data/processed/v3_prior_calibration_shadow.json`。
- evaluator 接入：
  - `v3_cal_*` shadow 字段。
  - `v3_cal_formal_p50_mae / below / over / p90_coverage / delta` 指标。
- live monitor 接入：
  - artifact/model_eval 增加 `v3_cal_*` 字段。
  - 保持 `v3_cal_affects_bid=false`。
  - 不改变 `bid_rows`、停止价、抢仓上限或 UI 视觉布局。
- map audit 接入：
  - 输出 `cal_active / cal_mae / cal_delta`。

当前 gate：

```text
active: 2506 scale=1.25
watch-only: 2601 hidden_low_sample
watch-only: 2501/2504/2401 not_systemic_under
watch-only: low-sample maps
```

关键指标：

```text
baseline formal_p50_mae=300553.241
v3_cal_active_rows=71
v3_cal_formal_p50_mae=298567.199
v3_cal_delta_formal_p50_mae=-1986.042
v3_cal_formal_p50_below_rate=0.510430
v3_cal_formal_p50_over_rate=0.489570
v3_cal_formal_p90_coverage=0.804433
```

map audit：

```text
2506 mae=409096.7 cal_mae=366187.0 cal_delta=-42909.7
2501 cal_active=0.0
2507 cal_active=0.0
2601 cal_active=0.0
```

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_calibration.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_map_audit.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\build_v3_prior_calibration_shadow.py --prior-trials 10000 --posterior-trials 512 --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_map_audit.py --top 8
```

结果：`36 passed`；全样本 evaluator 和 map audit 通过。

说明：

- 本轮是在沙箱用户下运行，`C:\Python313` 缺少 `numpy/pytest`，因此验证使用 `C:\Users\shenc\anaconda3\python.exe`。
- 初版 ratio-only calibration 会提升 P90 coverage 但恶化 P50 MAE；已收紧为 archive shift + baseline systemic-under 双 gate。
- 当前仍是 in-sample shadow，不作为 promotion 依据。

## 2026-06-05 checkpoint：count/cell/value conditioned shadow sampler

实现：

- 新增 `estimate_count_cell_value_posterior_from_truths()`。
  - 输出统一 `v3_ccv_*` flat fields。
  - 只在 baseline 为 `summary_likelihood` 且存在 q6 bucket evidence 时运行强化 likelihood。
  - `2601 hidden` 默认禁用，记录 `ccv_conditioned=disabled_hidden_cold_start`。
  - 没有 q6 value evidence 时，q6 value/formal 和 total/formal 均透传 baseline，不用 count/cells 证据硬推 value。
- evaluator 接入：
  - 样本行增加 `v3_ccv_*`。
  - 汇总增加 q6 count/cells P50 MAE、P90 coverage、`v3_ccv_delta_*`。
- live monitor 接入：
  - `v3_posterior_shadow` 和 `model_eval` 增加 `v3_ccv_*`。
  - `v3_ccv_affects_bid=false`，不进入正式出价或 UI 视觉层。
- map audit 接入：
  - 输出 `q6_count_mae / q6_cells_mae / ccv_rate / ccv_*_delta`。

全量 evaluator：

```text
windows=1551 ready=1534 no_state=17 parse_errors=0
posterior_ready=1534 posterior_strict_ready=513 posterior_summary_likelihood=1021
formal_p50_mae=300553.241
q6_count_p50_mae=1.404
q6_cells_p50_mae=6.674
v3_ccv_likelihood_rows=329
v3_ccv_q6_count_p50_mae=1.418
v3_ccv_delta_q6_count_p50_mae=+0.013
v3_ccv_q6_cells_p50_mae=6.679
v3_ccv_delta_q6_cells_p50_mae=+0.005
v3_cal_formal_p50_mae=298567.199
```

map audit 结论：

```text
2506 ccv_count_delta=+0.03 ccv_cells_delta=+0.13
2501 ccv_count_delta=+0.02 ccv_cells_delta=+0.15
2502 ccv_count_delta=-0.01 ccv_cells_delta=-0.78
2408 ccv_count_delta=-0.07 ccv_cells_delta=-0.08
2601 ccv_rate=0.0 disabled hidden
```

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_map_audit.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_map_audit.py --top 10
```

结果：`46 passed`；全量 evaluator 和 map audit 通过。

说明：

- ccv 候选能形成可复跑审计字段，但当前默认实现对整体 q6 count/cells P50 MAE 没有收益，且对 `2506` 负向。
- 后续不能把“强化 q6 bucket likelihood”作为 v3 主修复；下一步应做真正 residual/count-cell-value 生成模型，显式建模公共总格、已知非 q6 下界、q6 空间分布和 value per cell，而不是只调 likelihood 温度。

## 2026-06-05 checkpoint：residual count/cell/value shadow sampler

实现：

- 新增 `estimate_residual_count_cell_value_posterior_from_truths()`。
  - 输出 `v3_resid_*` shadow fields。
  - 只在非 strict fallback 窗口运行；strict 透传 baseline。
  - hidden `2601` 默认禁用。
  - 将 q6 component `(count,cells,value)` 与非 q6 residual component 分开重组。
  - 使用 session total exact/floor、known non-q6 floor、非 q6 bucket likelihood 计算 q6 component compatibility mass。
  - 对 `session_total_*_exact - non_q6_floor` 推导出的 q6 capacity 使用硬上界。
  - total/formal/q6 formal 仍透传 baseline，避免未验证 value-per-cell 直接进入决策口径。
- evaluator 接入：
  - 样本行增加 `v3_resid_*`。
  - 汇总增加 residual q6 count/cells/raw value P50 MAE 与 delta。
- live monitor 接入：
  - artifact/model_eval 增加 `v3_resid_*`。
  - `v3_resid_affects_bid=false`。
- map audit 接入：
  - 输出 `resid_rate / resid_count_delta / resid_cells_delta / resid_value_delta`。

全量 512-trial evaluator：

```text
metric_rows=1534
posterior_summary_likelihood=1021
q6_count_p50_mae=1.404
q6_cells_p50_mae=6.674
v3_resid_likelihood_rows=976
v3_resid_q6_count_p50_mae=1.403
v3_resid_delta_q6_count_p50_mae=-0.001
v3_resid_q6_cells_p50_mae=6.809
v3_resid_delta_q6_cells_p50_mae=+0.135
v3_resid_q6_value_p50_mae=379692.572
v3_resid_delta_q6_value_p50_mae=+5234.929
```

128-trial smoke 曾显示正向：

```text
v3_resid_delta_q6_count_p50_mae=-0.030
v3_resid_delta_q6_cells_p50_mae=-0.107
v3_resid_delta_q6_value_p50_mae=-6794.229
```

512-trial map audit：

```text
2506 resid_count_delta=-0.01 resid_cells_delta=0.00 resid_value_delta=-29406.8
2503 resid_count_delta=-0.16 resid_cells_delta=-0.55 resid_value_delta=-28308.7
2408 resid_count_delta=-0.02 resid_cells_delta=-0.20 resid_value_delta=+31381.4
2501 resid_count_delta=-0.01 resid_cells_delta=+0.15 resid_value_delta=+3111.5
2507 resid_count_delta=-0.03 resid_cells_delta=+0.37 resid_value_delta=+9908.4
```

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_map_audit.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 128 --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_map_audit.py --top 10
```

当前结论：

- residual 结构比 ccv 更接近 v3 目标：它确实能用 residual capacity 约束 q6 component，并在 `2506/2503` 的 q6 raw value 上给出正向信号。
- 但默认全局激活会恶化整体 q6 cells/raw value MAE，不能 promotion，也不能接 formal。
- 下一步应做 map/evidence gate：优先 `2506` systemic-under + fallback + residual value positive；排除 high-over、少样本和 cells 恶化切片。

## 2026-06-05 checkpoint：residual gate watch-only

实现：

- 新增 `src/bidking_lab/inference/v3/residual_gate.py`。
  - 输出 `v3_resid_gate_*`。
  - 复用 `v3_cal_*` 的 map-level active/systemic-under 信息。
  - candidate 需要 residual fallback、q6 count/cells/value P50 不高于 baseline。
  - 当前全局 `active` 关闭，状态为 `watch_only`，原因 `residual_gate_unproven`。
- evaluator/live/map audit 均接入 `v3_resid_gate_*`。
- `model_eval` 增加 gate status、reason、source、q6 delta 字段。

关键审计：

- 128-trial 下，初版 active 11 行，但仍恶化：

```text
v3_resid_gate_active_rows=11
v3_resid_gate_delta_q6_count_p50_mae=+0.003
v3_resid_gate_delta_q6_cells_p50_mae=+0.009
v3_resid_gate_delta_q6_value_p50_mae=+423.747
```

- active row 明细显示同一个 2506 gate 分裂：
  - Ethan 2506 过估样本中，residual 降 q6 value 有帮助。
  - Aisha 2506 低估样本中，residual 会把 q6 count/cells/value 进一步压低，例如 q6 truth `8/38/1,313,498` 的窗口被压到 `3/15/711,060`。
- 因此当前 gate 不能按 map-level `2506` 直接启用，必须引入 hero/evidence-specific gate。

最终默认 512-trial：

```text
v3_resid_gate_active_rows=0
v3_resid_gate_delta_q6_count_p50_mae=0.0
v3_resid_gate_delta_q6_cells_p50_mae=0.0
v3_resid_gate_delta_q6_value_p50_mae=0.0
```

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 128 --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_map_audit.py --top 10
```

结果：`68 passed`；全量 evaluator 和 map audit 通过。

## 2026-06-05 checkpoint：hero/profile audit 与 residual candidate 表

实现：

- `evaluate_fatbeans_v3_samples.py` 每个 archive pre-bid 窗口增加：
  - `hero`
  - `evidence_stage`
  - `evidence_profile_key`
  - `information_density_score`
  - `information_density_band`
  - `hero_map_id`
  - `hero_map_evidence_stage`
  - `hero_map_evidence_profile`
- `fatbeans.py` 暴露 `hero_mode_from_state()`，避免 v3 evaluator 复制 hero id 映射。
- `summarize_v3_metric_slices.py` 默认支持 hero/profile 分片，并输出 ccv/residual/gate q6 count/cells/value delta。
- `summarize_v3_map_audit.py` map 行追加 `heroes`、`evidence_stages`、`information_density`、`evidence_profiles`、`hero_map_evidence_profiles`。
- 新增 `summarize_v3_residual_profile_candidates.py`，按 profile 或 hero/map 输出 residual 候选状态：
  - `watch_only_over_correction_candidate`
  - `watch_only_neutral`
  - `blocked_systemic_under`
  - `blocked_under_value_downshift`
  - `blocked_residual_hurts`
  - `blocked_low_sample`

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_residual_profile_candidates.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 128 --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_metric_slices.py --posterior-trials 128 --by hero_map_id --by hero_map_evidence_profile --top 16
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_map_audit.py --posterior-trials 128 --top 12
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_residual_profile_candidates.py --posterior-trials 128 --top 30
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_residual_profile_candidates.py --posterior-trials 128 --by hero_map_id --top 24
```

结果：

- `68 passed`，candidate script `2 passed`。
- 512-trial 主审计：

```text
windows=1551 ready=1534 no_state=17 parse_errors=0 constraint_conflict=0
formal_p50_mae=300553.241
q6_count_p50_mae=1.404
q6_cells_p50_mae=6.674
v3_ccv_delta_q6_count_p50_mae=+0.013
v3_ccv_delta_q6_cells_p50_mae=+0.005
v3_resid_delta_q6_count_p50_mae=-0.001
v3_resid_delta_q6_cells_p50_mae=+0.135
v3_resid_delta_q6_value_p50_mae=+5234.929
v3_resid_gate_active_rows=0
v3_cal_delta_formal_p50_mae=-1986.042
```

- 128-trial 2506 map audit：

```text
map_id=2506 sessions=21 ready=71/73 heroes=aisha:43,ethan:28
mae=397195.2 bias=-270368.6 below=0.746479 p90_cover=0.619718
public_total=0.084507 q6_floor=0.28169
flags=mostly_fallback+little_public_total+systemic_under
```

- 128-trial `hero_map_id` residual candidate：

```text
status_counts=blocked_low_sample:71,blocked_residual_hurts:3,blocked_systemic_under:8,blocked_under_value_downshift:1,watch_only_neutral:4,watch_only_over_correction_candidate:2
ethan|2506 status=blocked_systemic_under n=28 bias=-249550.4 below=0.678571 q6_cells_delta=-1.49 q6_value_delta=-117480.2
aisha|2506 status=blocked_systemic_under n=43 bias=-283924.6 below=0.790698 q6_cells_delta=+0.31 q6_value_delta=+20915.1
```

结论：

- hero/profile 分片证明 `2506` 不能作为单一 gate：Aisha/Ethan 都系统性低估，但 residual 对两者 q6 cells/value 的影响不同。
- profile 级别目前 349 个切片因样本不足 blocked，不能用过细 profile 直接 promotion。
- hero/map 粗粒度有 2 个 over-correction 候选，但都不满足直接启用条件：
  - `ethan|2601` 是 hidden，residual 当前没有实际 likelihood rows。
  - `aisha|2504` high-over，但 q6 value delta 仍为正。
- 下一步 gate 必须先有低估保护：若切片 formal bias 明显为负或 below rate 偏高，禁止 residual 降 formal/value。

## 2026-06-05 checkpoint：低估上修候选审计

实现：

- 新增 `scripts/summarize_v3_underestimate_repair_candidates.py`。
- 新增 `tests/test_summarize_v3_underestimate_repair_candidates.py`。
- 该脚本按 `hero_map_id` 或 `hero_map_evidence_profile` 汇总 ready 窗口，计算 formal P50 MAE/bias/below/over、formal P90 coverage、q6 formal P50 MAE，以及 bounded upshift 后的 delta。
- 上修 scale 使用 truth/pred median ratio、session shrink 与 `max_upshift=1.25`，用于候选审计，不写回正式估值。
- 候选状态包括：`watch_only_upshift_candidate`、`watch_only_needs_evidence`、`blocked_repair_hurts`、`blocked_high_over`、`blocked_not_systemic_under`、`blocked_low_sample`。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_underestimate_repair_candidates.py --posterior-trials 128 --by hero_map_id --top 30
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_underestimate_repair_candidates.py --posterior-trials 128 --by hero_map_evidence_profile --top 30
```

结果：

- `72 passed`。
- `hero_map_id`：`blocked_low_sample=71`，`blocked_not_systemic_under=10`，`watch_only_needs_evidence=4`，`watch_only_upshift_candidate=4`。
- `hero_map_evidence_profile`：`blocked_low_sample=349`，`blocked_not_systemic_under=3`，`watch_only_needs_evidence=2`。

主要候选：

```text
aisha|2506 scale=1.046065 mae=384517.7 -> 363546.8 delta=-20970.9 below=0.790698 -> 0.744186 p90_cover=0.627907 -> 0.674419
ethan|2506 scale=1.045088 mae=416664.2 -> 404007.0 delta=-12657.1 below=0.678571 -> 0.642857 p90_cover=0.607143 -> 0.75
aisha|2601 scale=1.05287 mae=541556.3 -> 507628.8 delta=-33927.5
ethan|2509 scale=1.019059 mae=419243.9 -> 419127.9 delta=-116.0
```

结论：

- `2506` Aisha/Ethan 的低估修复方向得到 shadow 候选支持：小幅上修可改善 in-sample MAE，并略改善 below/P90。
- 该上修不能直接进入 formal/live，因为它仍是 in-sample archive 假设修复，且 profile 粒度样本不足。
- hidden `2601` 虽然出现在候选中，但 hidden 样本少，不能和 shipwreck/villa 共用 promotion 口径。
- 下一步应把上修候选变成独立 shadow 字段或 calibration candidate，继续使用 holdout/new-live 样本验证，而不是再调 residual 下修。

## 2026-06-05 checkpoint：v3_under 低估上修 shadow 链路

实现：

- 新增 `src/bidking_lab/inference/v3/underestimate_repair.py`。
- 新增 `data/processed/v3_underestimate_repair_shadow.json`，记录当前 hero/map 低估候选 entry。
- archive evaluator 输出 `v3_under_*` 字段，并在 summary 中追加：
  - `v3_under_candidate_rows`
  - `v3_under_formal_p50_mae`
  - `v3_under_delta_formal_p50_mae`
  - `v3_under_formal_p50_below_rate`
  - `v3_under_formal_p90_coverage`
- `summarize_v3_metric_slices.py` 和 `summarize_v3_map_audit.py` 加入 under candidate/delta 字段。
- live monitor artifact 和局后 `model_eval` row 输出同一组 `v3_under_*` 字段。
- 新增 `tests/test_inference_v3_underestimate_repair.py`。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_inference_v3_underestimate_repair.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 128 --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_metric_slices.py --posterior-trials 128 --by hero_map_id --top 12
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_map_audit.py --posterior-trials 128 --top 12
```

结果：

- `77 passed`。
- evaluator 128-trial：

```text
v3_under_candidate_rows=101
formal_p50_mae=312938.992
v3_under_formal_p50_mae=312117.848
v3_under_delta_formal_p50_mae=-821.144
formal_p50_below_rate=0.51043
v3_under_formal_p50_below_rate=0.508475
formal_p90_coverage=0.773794
v3_under_formal_p90_coverage=0.777705
```

- 2506 map audit：

```text
map_id=2506 sessions=21 ready=71/73 paired=71
mae=397195.2 bias=-270368.6 below=0.746479 p90_cover=0.619718
under_candidate=1.0 under_delta=-17692.3 under_below=0.704225 under_p90_cover=0.704225
```

结论：

- `v3_under_*` 已经成为 archive/live 共用 shadow 链路。
- 全局 MAE 改善很小，不能证明 formal promotion。
- `2506` 的局部改善明确，支持下一步用新增实战样本/holdout 复核 hero-map scale 稳定性。
- `v3_under_active=false`，`v3_under_affects_bid=false`；没有改 UI 主建议、正式估值或正式出价。

## 2026-06-05 checkpoint：v3_under session holdout 审计

实现：

- 新增 `scripts/summarize_v3_underestimate_holdout.py`。
- 新增 `tests/test_summarize_v3_underestimate_holdout.py`。
- holdout 按 `session_id` 做 deterministic fold：训练折只用于生成低估上修 candidate，holdout 折才应用候选 scale 并计算指标。
- evaluator 在 holdout 中显式禁用默认 `v3_under` entry 表，避免全库 entry 泄漏到验证结果。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_underestimate_holdout.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_inference_v3_underestimate_repair.py -q
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_inference_v3_underestimate_repair.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_summarize_v3_underestimate_holdout.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_underestimate_holdout.py --posterior-trials 128 --folds 5 --by hero_map_id --top 12
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_underestimate_holdout.py --posterior-trials 128 --folds 5 --by hero_map_id --min-sessions 6 --top 12
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_underestimate_holdout.py --posterior-trials 128 --folds 5 --by hero_map_evidence_profile --top 12
```

结果：

- focused：`8 passed`。
- v3 core/live path：`79 passed`。
- 默认 `hero_map_id` holdout：全库 `1534` ready windows / `433` sessions，候选 holdout 行 `61`，整体 MAE `312938.992 -> 312068.688`，delta `-870.304`。
- 默认 gate 下候选只剩 `aisha|2506` 与 `aisha|2601`：

```text
aisha|2506 rows=43 sessions=13 delta=-22005.497 mae=384517.698 -> 362512.2 below=0.790698 -> 0.767442 p90_cover=0.627907 -> 0.651163
aisha|2601 rows=38 sessions=11 delta=-10231.829 mae=541556.274 -> 531324.445 below=0.684211 -> 0.684211 p90_cover=0.315789 -> 0.368421
```

- 放宽到 `min_sessions=6` 后，`ethan|2506` 出现正向 holdout 信号，但同时 `ethan|2509` 变差：

```text
ethan|2506 rows=28 sessions=8 delta=-10401.162 mae=416664.161 -> 406262.999 below=0.678571 -> 0.642857
ethan|2509 rows=30 sessions=8 delta=1701.474 mae=419243.927 -> 420945.4
```

- `hero_map_evidence_profile` 粒度 holdout 仍无候选：`candidate_rows=0`，主要原因是 profile 级样本量不足。

结论：

- 当前样本足够继续 v3 架构、shadow 链路和 Aisha 2506 诊断。
- 当前样本不足以把 Ethan 2506 或 profile 级上修正式升级。
- 不需要盲目冲到 400+ 样本；如果新增实战样本，优先定向补 `ethan|2506`，其次补 `aisha|2506` holdout 确认。
- `v3_under` 仍保持 `affects_bid=false`。

## 2026-06-05 checkpoint：CCV sampler candidate gate

实现：

- 新增 `scripts/summarize_v3_ccv_profile_candidates.py`。
- 新增 `tests/test_summarize_v3_ccv_profile_candidates.py`。
- 该脚本按 `hero_map_id` 或 `hero_map_evidence_profile` 汇总 CCV shadow 相对 baseline 的 q6 count/cells/value/formal delta。
- candidate gate 记录：
  - `watch_only_count_cell_candidate`
  - `watch_only_needs_evidence`
  - `watch_only_neutral`
  - `blocked_under_count_cell_downshift`
  - `blocked_ccv_hurts`
  - `blocked_low_ccv_activity`
  - `blocked_low_sample`
- 缺少公开总格/总数或 q6 证据不足的正向切片只进 needs-evidence，不和证据充分候选混在一起。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_ccv_profile_candidates.py -q
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_inference_v3_underestimate_repair.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_summarize_v3_underestimate_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 128 --fail-on-conflicts
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_profile_candidates.py --posterior-trials 128 --by hero_map_id --top 16
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_profile_candidates.py --posterior-trials 128 --by hero_map_evidence_profile --top 20
```

结果：

- 新增测试：`3 passed`。
- v3 core/live path：`82 passed`。
- 全库 evaluator 显示 CCV 不能全局 promotion：

```text
v3_ccv_likelihood_rows=347
v3_ccv_q6_count_p50_mae=1.440 delta=-0.001
v3_ccv_q6_cells_p50_mae=7.008 delta=+0.165
```

- `hero_map_id` candidate gate：

```text
status_counts=blocked_ccv_hurts:5,blocked_low_ccv_activity:8,blocked_low_sample:71,blocked_under_count_cell_downshift:2,watch_only_count_cell_candidate:1,watch_only_needs_evidence:1,watch_only_neutral:1
ethan|2502 watch_only_count_cell_candidate n=36 sessions=9 ccv_rate=0.444444 count_delta=-0.11 cells_delta=-1.89 value_delta=-61348.8 formal_delta=-2991.4
aisha|2409 watch_only_needs_evidence n=32 sessions=9 ccv_rate=0.375 count_delta=-0.06 cells_delta=+0.01 formal_delta=-36155.1 public_total=0.0
ethan|2506 blocked_under_count_cell_downshift n=28 sessions=8 count_delta=-0.07 cells_delta=-1.22 formal_delta=-13330.6 count_pred_delta=-0.07 cells_pred_delta=-2.22
```

- `hero_map_evidence_profile` 粒度仍不足：

```text
status_counts=blocked_ccv_hurts:2,blocked_low_ccv_activity:3,blocked_low_sample:349
```

结论：

- CCV 的当前实现不是全局收益项，尤其 cells MAE 全局变差。
- Ethan 2506 虽然 q6 count/cells MAE 有改善，但 formal 仍系统性低估，且 CCV 会继续下移 count/cells，因此不能作为正式 sampler gate。
- 下一步如果要推进结构性 sampler，应该优先研究 `ethan|2502` 这种证据较充分的正向切片，以及 Aisha 2409 缺公开总格的 needs-evidence 切片；不要把 CCV 直接推广到 2506。

## 2026-06-05 checkpoint：archive/live 共用 v3 shadow pipeline

实现：

- 新增 `src/bidking_lab/inference/v3/pipeline.py`。
- 新增 `tests/test_inference_v3_pipeline.py`。
- `estimate_shadow_pipeline()` 统一生成：
  - `v3_post_*`
  - `v3_ccv_*`
  - `v3_resid_*`
  - `v3_resid_gate_*`
  - `v3_cal_*`
  - `v3_under_*`
- `scripts/evaluate_fatbeans_v3_samples.py` 和 `src/bidking_lab/live/monitor.py` 改为调用同一 pipeline，不再各自手写 posterior/CCV/residual/calibration/underestimate 链路。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_pipeline.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_pipeline.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_inference_v3_underestimate_repair.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_summarize_v3_underestimate_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 32 --fail-on-conflicts
```

结果：

- pipeline/archive/live focused：`33 passed`。
- v3 core/live path：`83 passed`。
- 32-trial archive smoke：`windows=1551 ready=1534 constraint_conflict=0 parse_errors=0 constraint_ok=True`。
- `evaluate_fatbeans_v3_samples.py` 与 `live/monitor.py` 已无直接手写 `estimate_q6_posterior_from_truths` / `estimate_count_cell_value_posterior_from_truths` / `estimate_residual_count_cell_value_posterior_from_truths` / `calibrate_posterior_report` / `gate_residual_posterior_report` / `repair_underestimate_posterior_report` 链路调用。

结论：

- v3 archive/live 的 shadow 字段生成路径已收敛到同一核心函数，降低后续参数、entry、field 命名不一致风险。
- 该改动不改变 UI 主建议、不改变 formal decision、不进入正式出价。

## 2026-06-05 checkpoint：tail/value review candidate audit

实现：

- 新增 `scripts/summarize_v3_tail_value_candidates.py`。
- 新增 `tests/test_summarize_v3_tail_value_candidates.py`。
- 该脚本按 `hero_map_id` 或 `hero_map_evidence_profile` 对比：
  - formal P50 vs formal truth。
  - formal P50 vs tail-replacement truth。
  - tail-replacement P50/P90 vs tail-replacement truth。
  - q6 formal/tail-replacement 同口径指标。
- candidate 状态包括：
  - `watch_only_q6_tail_value_candidate`
  - `watch_only_tail_value_candidate`
  - `watch_only_needs_evidence`
  - `watch_only_neutral`
  - `blocked_tail_estimate_hurts`
  - `blocked_no_tail_signal`
  - `blocked_low_sample`

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_tail_value_candidates.py -q
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_pipeline.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_inference_v3_underestimate_repair.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_summarize_v3_underestimate_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py tests\test_summarize_v3_tail_value_candidates.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_tail_value_candidates.py --posterior-trials 128 --by hero_map_id --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_tail_value_candidates.py --posterior-trials 128 --by hero_map_evidence_profile --top 20
```

结果：

- 新增测试：`3 passed`。
- v3 core/live path：`86 passed`。
- `hero_map_id` tail/value gate：

```text
status_counts=blocked_low_sample:71,blocked_no_tail_signal:9,blocked_tail_estimate_hurts:1,watch_only_needs_evidence:2,watch_only_neutral:1,watch_only_q6_tail_value_candidate:4,watch_only_tail_value_candidate:1
aisha|2506 status=watch_only_q6_tail_value_candidate n=43 sessions=13 tail_rate=0.162791 tail_delta=-11433.7 tail_p90_under=0.372093 q6_tail_delta=-9603.3 q6_tail_p90_under=0.325581
ethan|2506 status=watch_only_q6_tail_value_candidate n=28 sessions=8 tail_rate=0.142857 tail_delta=-2096.4 tail_p90_under=0.392857 q6_tail_delta=-8614.5 q6_tail_p90_under=0.392857
ethan|2502 status=watch_only_tail_value_candidate n=36 sessions=9 tail_rate=0.222222 tail_delta=-418.3 tail_p90_under=0.305556
ethan|2508 status=blocked_tail_estimate_hurts n=28 sessions=9 tail_delta=32201.7 q6_tail_delta=28270.1
```

- hidden `2601` 也出现 tail/q6-tail 候选，但仍按 hidden 单独验证：

```text
aisha|2601 q6_tail_delta=-57702.7 q6_tail_p90_under=0.578947
ethan|2601 q6_tail_delta=-11678.5 q6_tail_p90_under=0.3
```

- `hero_map_evidence_profile` 粒度仍不足：

```text
status_counts=blocked_low_sample:349,blocked_no_tail_signal:4,watch_only_needs_evidence:1
```

结论：

- `2506` 的低估确实有 tail/q6-tail review 信号，尤其 P90 tail under rate 偏高。
- tail-replacement 字段仍是审计/辅助口径，不进入 formal decision 或正式出价。
- `ethan|2508` 说明 tail estimate 可能伤害 tail truth MAE，后续不能全局启用 tail 上修。
- profile 粒度样本不足，不能直接按 profile promotion。

## 2026-06-05 checkpoint：v3 promotion readiness 总审计

实现：

- 新增 `scripts/summarize_v3_promotion_readiness.py`。
- 新增 `tests/test_summarize_v3_promotion_readiness.py`。
- readiness 脚本一次性复用：
  - `evaluate_fatbeans_v3_samples.summarize_rows`
  - `summarize_v3_underestimate_holdout`
  - `summarize_v3_ccv_profile_candidates`
  - `summarize_v3_tail_value_candidates`
  - `summarize_v3_residual_profile_candidates`
- 输出 gate：
  - `archive_data_quality`
  - `shared_shadow_pipeline`
  - `formal_baseline_metrics`
  - `underestimate_repair_holdout`
  - `ccv_sampler`
  - `tail_value_review`
  - `residual_gate`
  - `profile_sample_depth`
  - `v2_archive_readiness`

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_promotion_readiness.py -q
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_pipeline.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_inference_v3_underestimate_repair.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_summarize_v3_underestimate_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py tests\test_summarize_v3_tail_value_candidates.py tests\test_summarize_v3_promotion_readiness.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_promotion_readiness.py --posterior-trials 128
```

结果：

- 新增测试：`2 passed`。
- v3 core/live path：`88 passed`。
- readiness 128-trial：

```text
overall_status=not_ready
blocked_gates=4
windows=1551 ready=1534
formal_mae=312938.992
formal_below=0.51043
formal_p90_cover=0.773794
under_delta=-821.144
ccv_cells_delta=0.165
resid_gate_active=0
```

gate 结果：

```text
archive_data_quality=watch
shared_shadow_pipeline=pass
formal_baseline_metrics=blocked
underestimate_repair_holdout=watch
ccv_sampler=blocked
tail_value_review=watch
residual_gate=blocked
profile_sample_depth=blocked
v2_archive_readiness=pending
```

结论：

- v3 现在有统一的 formal promotion readiness 入口。
- 当前不能切 formal，也不能 archive v2。
- 阻塞项是 formal baseline 仍偏低、CCV 全局不稳、residual gate 仍禁用、profile 样本不足。
- 下一步继续围绕 `2506` bounded upshift + tail/q6-tail review 做 shadow/holdout，而不是全局启用 CCV/residual/tail replacement。

## 2026-06-05 checkpoint：v3 CCV session holdout 审计

实现：

- 新增 `scripts/summarize_v3_ccv_holdout.py`。
- 新增 `tests/test_summarize_v3_ccv_holdout.py`。
- holdout 口径：
  - 按 `session_id` stable hash 分 fold。
  - 每个 fold 只用训练折运行 `summarize_v3_ccv_profile_candidates.py`。
  - 只把训练折中的 `watch_only_count_cell_candidate` group 应用到留出折。
  - 输出 overall 与 candidate_only 两层指标，避免小覆盖候选被总体均值稀释。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_ccv_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_holdout.py --posterior-trials 128 --folds 5 --by hero_map_id --top 12
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_holdout.py --posterior-trials 128 --folds 5 --by hero_map_evidence_profile --top 12
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_holdout.py --posterior-trials 128 --folds 5 --by hero_map_id --min-sessions 6 --top 12
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_pipeline.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_inference_v3_underestimate_repair.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_summarize_v3_underestimate_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py tests\test_summarize_v3_tail_value_candidates.py tests\test_summarize_v3_promotion_readiness.py tests\test_summarize_v3_ccv_holdout.py tests\test_live_monitor.py -q
```

结果：

- focused CCV tests：`5 passed`。
- v3 core/live path：`90 passed`。
- `hero_map_id` 默认阈值：

```text
rows=1534 sessions=433 candidate_rows=2 candidate_sessions=1
count_delta=0.0 cells_delta=0.0 q6_formal_delta=0.0
candidate_only rows=2 sessions=1 groups=ethan|2502
```

- `hero_map_evidence_profile` 默认阈值：

```text
candidate_rows=0 candidate_sessions=0
status_counts=blocked_ccv_hurts:9,blocked_low_ccv_activity:12,blocked_low_sample:1524
```

- `hero_map_id --min-sessions 6` 灵敏度：

```text
candidate_rows=14 candidate_sessions=4
cells_delta=+0.004 q6_formal_delta=+84.8
candidate_only cells_delta=+0.4 q6_formal_delta=+9288.7
groups=aisha|2504,aisha|2508,ethan|2502
```

结论：

- `ethan|2502` 的全量切片候选信号在 session holdout 中没有复现改善。
- 放宽 session 阈值会引入 `aisha|2504/aisha|2508`，candidate_only 指标反而恶化。
- CCV 继续保持 shadow/audit，不进入 formal sampler。
- 下一步的 count/cell/value sampler 不能继续靠固定 threshold 升级，必须改成证据条件 likelihood 的可验证候选，并先过 holdout。

## 2026-06-05 checkpoint：v3 tail/value session holdout 与 readiness 接入

实现：

- 新增 `scripts/summarize_v3_tail_value_holdout.py`。
- 新增 `tests/test_summarize_v3_tail_value_holdout.py`。
- `scripts/summarize_v3_promotion_readiness.py` 接入：
  - `summarize_v3_ccv_holdout.summarize_holdout`
  - `summarize_v3_tail_value_holdout.summarize_holdout`
- readiness 的 `ccv_sampler` gate 现在同时看全局 delta 和 session holdout。
- readiness 的 `tail_value_review` gate 现在同时看候选切片、session holdout 和 hurt groups。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_tail_value_holdout.py tests\test_summarize_v3_tail_value_candidates.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_tail_value_holdout.py --posterior-trials 128 --folds 5 --by hero_map_id --top 12
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_tail_value_holdout.py --posterior-trials 128 --folds 5 --by hero_map_evidence_profile --top 12
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_promotion_readiness.py tests\test_summarize_v3_ccv_holdout.py tests\test_summarize_v3_tail_value_holdout.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_promotion_readiness.py --posterior-trials 128
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_pipeline.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_inference_v3_underestimate_repair.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_summarize_v3_underestimate_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py tests\test_summarize_v3_ccv_holdout.py tests\test_summarize_v3_tail_value_candidates.py tests\test_summarize_v3_tail_value_holdout.py tests\test_summarize_v3_promotion_readiness.py tests\test_live_monitor.py -q
```

结果：

- focused tail tests：`5 passed`。
- readiness/holdout tests：`6 passed`。
- v3 core/live path：`92 passed`。
- tail/value hero/map holdout：

```text
candidate_rows=122 candidate_sessions=36
tail_delta=-57.1 q6_tail_delta=-329.6
candidate_only tail_delta=-718.0 q6_tail_delta=-4144.4
groups=aisha|2401,aisha|2506,aisha|2601,ethan|2502,ethan|2601
```

- tail/value profile holdout：

```text
candidate_rows=0 candidate_sessions=0
status_counts=blocked_low_sample:1524,blocked_no_tail_signal:15,watch_only_needs_evidence:6
```

- 重点 hero/map group：

```text
aisha|2506 tail_delta=-7935.2 q6_tail_delta=-5562.9
aisha|2601 tail_delta=-7367.3 q6_tail_delta=-32770.1
ethan|2601 tail_delta=+13339.4 q6_tail_delta=+24471.3
```

- readiness 128-trial：

```text
overall_status=not_ready blocked_gates=4
ccv_holdout_rows=2
tail_holdout_q6_delta=-4144.4
tail_value_review=watch
ccv_sampler=blocked
```

结论：

- tail/q6-tail review 的 session holdout 方向比 CCV 更有用，特别是 `aisha|2506` 和 `aisha|2601`。
- `ethan|2601` 是明确 hurt group，tail/value sampler 不能全局启用。
- profile 粒度仍无可用 holdout 候选，不能按 profile promotion。
- tail replacement 继续是 audit/helper，不进入 formal decision 或正式出价。

## 2026-06-05 checkpoint：v3 tail/value review shadow namespace

实现：

- 新增 `src/bidking_lab/inference/v3/tail_value_review.py`。
- 新增 `tests/test_inference_v3_tail_value_review.py`。
- 新增 `data/processed/v3_tail_value_review_shadow.json`。
- `src/bidking_lab/inference/v3/pipeline.py` 新增 `tail_review` report，并输出 `v3_tail_review_*`。
- `scripts/evaluate_fatbeans_v3_samples.py`：
  - 默认读取 tail review entry 表。
  - 新增 `--tail-value-review` / `--no-tail-value-review`。
  - summary 输出 `v3_tail_review_candidate_rows`、`v3_tail_review_hurt_guard_rows`、`v3_tail_review_active_rows`。
- `src/bidking_lab/live/monitor.py`：
  - live v3 shadow 读取同一 entry 表。
  - `model_eval` 归档 tail review candidate/hurt/status 与 tail/q6-tail p50/p90 对照字段。
- `.gitignore` 明确允许提交 `v3_underestimate_repair_shadow.json` 与 `v3_tail_value_review_shadow.json`。

entry 表当前只启用保守三类：

```text
aisha|2506 status=watch_only_q6_tail_value_candidate q6_tail_delta=-5562.9
aisha|2601 status=watch_only_needs_evidence q6_tail_delta=-32770.1 hidden_requires_separate_validation
ethan|2601 status=blocked_tail_estimate_hurts q6_tail_delta=+24471.3
```

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_tail_value_review.py tests\test_inference_v3_pipeline.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 128
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_promotion_readiness.py --posterior-trials 128
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_pipeline.py tests\test_inference_v3_evidence_registry.py tests\test_inference_v3_calibration.py tests\test_inference_v3_underestimate_repair.py tests\test_inference_v3_tail_value_review.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_metric_slices.py tests\test_summarize_v3_map_audit.py tests\test_summarize_v3_prior_archive_calibration.py tests\test_summarize_v3_residual_profile_candidates.py tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_summarize_v3_underestimate_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py tests\test_summarize_v3_ccv_holdout.py tests\test_summarize_v3_tail_value_candidates.py tests\test_summarize_v3_tail_value_holdout.py tests\test_summarize_v3_promotion_readiness.py tests\test_live_monitor.py -q
```

结果：

- archive/live related tests：`37 passed`。
- v3 core/live path：`96 passed`。
- archive 128-trial：

```text
windows=1551 ready=1534 parse_errors=0
v3_tail_review_candidate_rows=43
v3_tail_review_hurt_guard_rows=40
v3_tail_review_active_rows=0
```

- readiness 128-trial：

```text
overall_status=not_ready blocked_gates=4
tail_review_candidate_rows=43 tail_review_hurt_guard_rows=40
tail_holdout_q6_delta=-4144.4
```

结论：

- tail/value review 已从离线审计推进到 archive/live 共享 shadow namespace。
- `v3_tail_review_active=false`、`v3_tail_review_affects_bid=false`，不改变 formal/live 出价。
- readiness 与 evaluator 现在都能看到 candidate/hurt 行数，避免 archive/live 字段漂移。
- 下一步可以在该 namespace 下设计更精细的 tail/value sampler 或 guard，不需要碰 UI 主建议。

## 2026-06-05 checkpoint：v3 guarded tail/under holdout gate

实现：

- 新增 `scripts/summarize_v3_tail_under_holdout.py`。
- 新增 `tests/test_summarize_v3_tail_under_holdout.py`。
- `summarize_v3_promotion_readiness.py` 接入 `tail_under_combined_holdout` gate。
- `summarize_v3_tail_value_candidates.py`：
  - 新增 `weak_tail_under_context` guard，避免仅凭 in-sample tail_delta 把非系统性低估切片升级为 tail candidate。
  - `260x` hidden map 统一标记 `hidden_requires_separate_validation`，降为 `watch_only_needs_evidence`，不进入可应用 tail candidate。
- `summarize_v3_underestimate_repair_candidates.py`：
  - 同步 `260x` hidden guard，避免 under holdout 和 live entry 表分叉。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_underestimate_repair_candidates.py tests\test_summarize_v3_underestimate_holdout.py tests\test_summarize_v3_tail_value_candidates.py tests\test_summarize_v3_tail_value_holdout.py tests\test_summarize_v3_tail_under_holdout.py tests\test_summarize_v3_promotion_readiness.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_tail_under_holdout.py --posterior-trials 128 --top 10
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_promotion_readiness.py --posterior-trials 128
```

结果：

- 聚焦测试：`15 passed`。
- guarded tail/under holdout 128-trial：

```text
rows=1534 sessions=433
under_rows=37 tail_rows=39 hurt_rows=11
formal_mae=312938.992 guarded_formal_mae=312322.149 formal_delta=-616.842
below=0.51043 guarded_below=0.509778
p90_cover=0.773794 guarded_p90_cover=0.774446
p90_extreme=0.313559 guarded_p90_extreme=0.313559
q6_miss=0.193611 guarded_q6_miss=0.193611

candidate_only rows=39
under_groups=aisha|2506
tail_groups=aisha|2506,ethan|2502
formal_delta=-24262.471
p90_cover=0.615385 guarded_p90_cover=0.641026
q6_tail_delta=-6133.4
```

- `ethan|2601` 现在只保留 hurt guard，不再被 tail candidate 应用：

```text
group=ethan|2601 under_rows=0 tail_rows=0 hurt_rows=9 tail_delta=0.0 q6_tail_delta=0.0
```

- readiness 128-trial：

```text
overall_status=not_ready blocked_gates=4
v3_under_candidate_rows=43
v3_under_delta_formal_p50_mae=-587.844
tail_under_rows=39
tail_under_formal_delta=-24262.471
tail_under_p90_extreme_delta=0.0
tail_under_applied_hurts=
gate=tail_under_combined_holdout status=watch
```

结论：

- 这一步解决的是候选安全性和评估一致性，不是正式精度大幅提升。
- hidden `2601` 继续只作单独观察；不进入 under/tail 可应用候选。
- `aisha|2506` 是当前最稳定的组合候选，候选切片收益明显，但全局覆盖太小。
- `data/processed/v3_underestimate_repair_shadow.json` 已同步 guarded holdout：Ethan 2506/2509 从可应用 upshift 降为 `watch_only_needs_evidence`，live/archive shadow 不再把它们显示为 under candidate。
- 当前 v3 仍不能正式替换：formal baseline 低估、CCV、residual gate、profile sample depth 仍卡住。

## 2026-06-05 checkpoint：v3 CCV layer stability audit

实现：

- 新增 `scripts/summarize_v3_ccv_layer_audit.py`。
- 新增 `tests/test_summarize_v3_ccv_layer_audit.py`。
- `summarize_v3_promotion_readiness.py` 默认接入 `map_id` 层 CCV holdout：
  - summary 输出 `ccv_map_rows` 与 `ccv_map_applied_hurts`。
  - `ccv_sampler` gate 输出 `map_applied_ccv_hurts_groups`。
  - 即使默认 `hero_map_id` 没有 applied hurt，map 层出现 hurt group 也会保持 blocked。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp'); $env:TEMP=$env:TMP
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_ccv_layer_audit.py tests\test_summarize_v3_ccv_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py tests\test_summarize_v3_promotion_readiness.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_layer_audit.py --posterior-trials 128
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_promotion_readiness.py --posterior-trials 128
```

结果：

- 聚焦测试：`8 passed`。
- CCV layer audit 128-trial：

```text
overall_status=blocked_applied_hurt
group_field=hero_map_id status=blocked_holdout_delta candidate_rows=2 groups=ethan|2502 count_delta=0.0 cells_delta=0.0 formal_delta=0.0 applied_hurts=
group_field=map_id status=blocked_applied_hurt candidate_rows=64 groups=2502,2503,2504 count_delta=0.062 cells_delta=0.053 formal_delta=21205.4 applied_hurts=2503
group_field=map_family status=sample_limited candidate_rows=0
group_field=hero_map_evidence_profile status=sample_limited candidate_rows=0
```

- readiness 128-trial：

```text
overall_status=not_ready blocked_gates=4
ccv_holdout_rows=2 ccv_applied_hurts=
ccv_map_rows=64 ccv_map_applied_hurts=2503
next_actions=... | tighten CCV map-layer guard; map holdout applies hurting groups | redesign CCV likelihood; current holdout is not promotion-ready
```

结论：

- 默认 `hero_map_id` CCV holdout 会漏掉 map-level applied hurt。
- `map_id` 层训练折会把 `2503/2504` 放入 candidate，验证折中 `2503` q6 formal 明显变差。
- CCV 当前不是“样本不够所以可以先放”的状态，而是分层不稳定；下一步需要重做条件 likelihood 或更严格的 layer gate。

## 2026-06-05 checkpoint：v3 CCV count/cell guard sensitivity audit

实现：

- `estimate_count_cell_value_posterior_from_truths()` 增加审计参数：
  - `count_cell_tail_guard`
  - `value_tail_guard`
  - `condition_temperature`
  - `relative_floor`
- 新增 `V3CcvOptions`，由 `estimate_shadow_pipeline()` 和 archive evaluator 透传。
- 默认值完全保持现状：live/archive 默认 `v3_ccv_*` 不变，仍是 shadow-only。
- 新增 `scripts/summarize_v3_ccv_guard_sensitivity.py`，同一 archive 上并列比较默认 CCV 与实验 CCV。
- 新增 `tests/test_summarize_v3_ccv_guard_sensitivity.py`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_pipeline.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_ccv_guard_sensitivity.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_guard_sensitivity.py --posterior-trials 128
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_layer_audit.py --posterior-trials 128
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_promotion_readiness.py --posterior-trials 128
```

结果：

- 聚焦测试：`25 passed`。
- count/cell tail guard sensitivity 128-trial：

```text
default count_delta=-0.001 cells_delta=0.165 count_mae=1.44 cells_mae=7.008
alternative count_cell_tail_guard=off count_delta=0.041 cells_delta=0.225 count_mae=1.482 cells_mae=7.068
paired_diff rows=1534 count_changed=108 count_pred_delta=-0.075 count_mae_delta=0.042 count_below_delta=0.025424 count_p90_cover_delta=-0.029335 cells_changed=146 cells_pred_delta=-0.368 cells_mae_delta=0.06 cells_below_delta=0.019557 cells_p90_cover_delta=-0.02412
layers default_status=blocked_applied_hurt alternative_status=blocked_applied_hurt
map_id default_hurts=2503 alternative_hurts=2502 alternative_rows=44 alternative_cells_delta=1.136
```

- 默认 layer audit 与 readiness 仍保持上一 checkpoint 结论：

```text
ccv_map_rows=64 ccv_map_applied_hurts=2503
overall_status=not_ready blocked_gates=4
```

结论：

- 关闭 count/cell tail guard 不是修复方向；它会降低预测值，但同时提高 below-rate、降低 P90 coverage，并使 q6 count/cells MAE 变差。
- `2503` hurt 不是由 guard 单独造成的；关闭 guard 后 hurt group 转移到 `2502`，说明 CCV likelihood/candidate layer 本身不稳。
- 下一步应重做 CCV 条件 likelihood 或新增更严格的 map/profile layer gate，而不是把 guard 作为可调开关升级。

## 2026-06-05 checkpoint：v3 CCV p50 directionality audit

实现：

- 新增 `scripts/summarize_v3_ccv_direction_audit.py`。
  - 按 `map_id` / `evidence_profile_key` / 任意 group field 审计 CCV p50 移动方向。
  - 对 `q6_count`、`q6_cells`、`q6_value`、`q6_formal` 统计：
    - changed/helped/hurt rows。
    - baseline under/over 后 CCV 上移/下移是否方向错误。
    - `hurt_rate_changed`、`directional_error_rate_changed`、`mae_delta`。
- 新增 `tests/test_summarize_v3_ccv_direction_audit.py`。
- `summarize_v3_promotion_readiness.py` 新增 `ccv_directionality` gate：
  - map 层或 evidence profile 层存在方向性 hurt 时保持 blocked。
  - readiness summary 输出 `ccv_direction_hurts`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_ccv_direction_audit.py tests\test_summarize_v3_promotion_readiness.py tests\test_summarize_v3_ccv_guard_sensitivity.py tests\test_summarize_v3_ccv_layer_audit.py tests\test_summarize_v3_ccv_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_audit.py --posterior-trials 128 --group-field map_id --component q6_count --component q6_cells --top 40
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_audit.py --posterior-trials 128 --group-field evidence_profile_key --component q6_count --component q6_cells --top 40
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_promotion_readiness.py --posterior-trials 128
```

结果：

- 聚焦测试：`11 passed`。
- map-level 方向性审计：

```text
status_counts=blocked_directional_hurt:20,blocked_low_movement:13,watch_directional_candidate:9
map_id=2503 q6_count blocked_directional_hurt changed=15 helped=4 hurt=11 hurt_rate=0.733333 directional_error=0.466667 mae_delta=+0.127
map_id=2503 q6_cells blocked_directional_hurt changed=20 helped=9 hurt=11 hurt_rate=0.55 directional_error=0.25 mae_delta=+0.438
map_id=2502 q6_count watch_directional_candidate changed=13 helped=10 hurt=3 hurt_rate=0.230769 mae_delta=-0.095
map_id=2502 q6_cells watch_directional_candidate changed=25 helped=13 hurt=9 hurt_rate=0.36 mae_delta=-0.708
```

- evidence-profile 方向性审计：

```text
status_counts=blocked_directional_hurt:11,blocked_low_movement:7,blocked_low_sample:44,watch_directional_candidate:7,watch_neutral:1
public:total+item+shape+layout q6_count blocked_directional_hurt changed=8 helped=0 hurt=8 hurt_rate=1.0 directional_error=0.75 mae_delta=+0.152
public:total+item+shape+layout q6_cells blocked_directional_hurt changed=12 helped=3 hurt=9 hurt_rate=0.75 mae_delta=+0.505
public:total+item+shape q6_count watch_directional_candidate changed=10 helped=7 hurt=3 mae_delta=-0.067
```

- readiness 128-trial：

```text
overall_status=not_ready blocked_gates=5
ccv_map_applied_hurts=2503
ccv_direction_hurts=q6_count:2404,q6_cells:2406,q6_count:2403,q6_count:2401,q6_cells:2510,q6_count:2406,q6_cells:2404,q6_count:2503
gate=ccv_directionality status=blocked
```

结论：

- 方向性审计解释了为什么不能把 `2502` 的正向结果外推：同一 CCV 机制在多个 map/profile 上会把 p50 推向错误方向。
- `public:total+item+shape+layout` 不能被当作“公开总格 + layout 足够可靠”的放行信号；该 profile 当前方向性 hurt 非常强。
- 下一步 CCV likelihood 必须先解决“移动方向判断”，再谈 count/cells MAE 或 formal promotion。

## 2026-06-05 checkpoint：v3 CCV direction holdout

实现：

- 新增 `scripts/summarize_v3_ccv_direction_holdout.py`。
  - 每个 session fold 中，用训练折运行 `summarize_v3_ccv_direction_audit.py`。
  - 只把训练折状态为 `watch_directional_candidate` 的 `(component, group)` 应用到验证折。
  - 输出 `candidate_only_delta_p50_mae`、hurt rate、directional error rate、`applied_direction_hurts_groups`。
- 新增 `tests/test_summarize_v3_ccv_direction_holdout.py`。
- `summarize_v3_promotion_readiness.py` 新增 `ccv_direction_holdout` gate。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_ccv_direction_holdout.py tests\test_summarize_v3_ccv_direction_audit.py tests\test_summarize_v3_promotion_readiness.py tests\test_summarize_v3_ccv_guard_sensitivity.py tests\test_summarize_v3_ccv_layer_audit.py tests\test_summarize_v3_ccv_holdout.py tests\test_summarize_v3_ccv_profile_candidates.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_holdout.py --posterior-trials 128 --group-field map_id --component q6_count --component q6_cells --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_holdout.py --posterior-trials 128 --group-field evidence_profile_key --component q6_count --component q6_cells --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_promotion_readiness.py --posterior-trials 128
```

结果：

- 聚焦测试：`13 passed`。
- `map_id` direction holdout：

```text
overall_status=blocked_holdout_directional_hurt
candidate_rows=438
candidate_delta=+0.168
candidate_hurt_rate=0.086758
candidate_directional_error=0.06621
applied_hurts=q6_cells:2502,q6_cells:2506,q6_count:2501,q6_count:2409,q6_count:2506
component=q6_cells delta=+0.567
component=q6_count delta=+0.045
```

- `evidence_profile_key` direction holdout：

```text
overall_status=watch
candidate_rows=348
candidate_delta=-0.057
candidate_hurt_rate=0.051724
candidate_directional_error=0.025862
applied_hurts=
component=q6_cells delta=-0.011
component=q6_count delta=-0.069
```

- readiness 128-trial：

```text
overall_status=not_ready blocked_gates=6
gate=ccv_direction_holdout status=blocked
ccv_direction_holdout=blocked_holdout_directional_hurt
```

结论：

- directionality 可以作为 blocker，但不能直接作为 sampler promotion 规则。
- map-level 方向候选在 session holdout 上仍会伤，尤其 q6 cells 对 `2502/2506` 不稳定。
- profile-level direction holdout 虽然是 watch，但收益很小，且 q6 cells 几乎没有实质改善，不能替代 likelihood 重构。
- 下一步仍应重做 CCV likelihood/组件分解，而不是把 direction gate 结果接进正式估值。

## 2026-06-05 checkpoint：v3 CCV component likelihood skeleton

实现：

- 新增可选 `v3_ccvc_` shadow posterior。
  - `estimate_component_count_cell_value_posterior_from_truths` 将 q6 component 与 non-q6 residual capacity 分开计分。
  - public total / known floors 作用在 recombined total 上。
  - 明确 `quality=6` 的 item/shape anchor 和 q6 avg soft numeric 作用在 q6 component 上。
  - unqualified anchors 暂不强行归入 q6 component，会在 diagnostics 中记录 `ccvc_unassigned_anchor_count`。
- `V3CcvOptions(component_likelihood=True)` 显式开启；默认 live/archive/UI 行为不变。
- `evaluate_fatbeans_v3_samples.py` 新增 `--ccv-component-likelihood`，输出 `v3_ccvc_*` 字段和 summary 指标。
- `summarize_v3_ccv_direction_audit.py` 新增 `--candidate-prefix`，可用同一方向性口径审计 `v3_ccv_` 与 `v3_ccvc_`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_pipeline.py tests\test_evaluate_fatbeans_v3_samples.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 128 --ccv-component-likelihood
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_audit.py --posterior-trials 128 --candidate-prefix v3_ccvc_ --group-field map_id --component q6_count --component q6_cells --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_audit.py --posterior-trials 128 --candidate-prefix v3_ccvc_ --group-field evidence_profile_key --component q6_count --component q6_cells --top 20
```

结果：

```text
focused tests: 27 passed

v3_ccvc_component_likelihood_rows=1050
v3_ccvc_delta_q6_count_p50_mae=-0.033
v3_ccvc_delta_q6_cells_p50_mae=-0.168
v3_ccvc_delta_q6_value_p50_mae=-6864.3

map_id direction:
blocked_directional_hurt=24
blocked_low_movement=7
watch_directional_candidate=11

evidence_profile_key direction:
blocked_directional_hurt=16
blocked_low_movement=1
blocked_low_sample=44
watch_directional_candidate=9
```

结论：

- `v3_ccvc_` 是比旧 `v3_ccv_` 更合理的 v3 CCV 重构骨架：覆盖更多 fallback 窗口，q6 count/cells/value 全局 MAE 都是正向。
- 但 map/profile directionality 仍 blocked，说明“组件重组”解决了均值问题的一部分，还没有解决逐窗口移动方向问题。
- 当前不能接 formal/live，也不能替代 readiness gate；下一步需要对 `v3_ccvc_` 做 holdout candidate gate，并拆分 random_avg、public total、q6 floor、unqualified anchors 的方向性贡献。

## 2026-06-05 checkpoint：v3 CCVC direction holdout

实现：

- `scripts/summarize_v3_ccv_direction_holdout.py` 新增 `--candidate-prefix`。
- 默认仍审计 `v3_ccv_`；传 `--candidate-prefix v3_ccvc_` 时会自动启用 `V3CcvOptions(component_likelihood=True)` 并审计 `v3_ccvc_*` 字段。
- 新增测试确认 holdout 确实按 candidate prefix 读取组件后验字段。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_ccv_direction_audit.py tests\test_summarize_v3_ccv_direction_holdout.py tests\test_summarize_v3_promotion_readiness.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_holdout.py --posterior-trials 128 --candidate-prefix v3_ccvc_ --group-field map_id --component q6_count --component q6_cells --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_holdout.py --posterior-trials 128 --candidate-prefix v3_ccvc_ --group-field evidence_profile_key --component q6_count --component q6_cells --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_holdout.py --posterior-trials 128 --candidate-prefix v3_ccvc_ --group-field evidence_profile_key --component q6_count --max-hurt-rate 0.25 --max-directional-error-rate 0.2 --top 20
```

结果：

```text
focused tests: 7 passed

map_id q6_count+q6_cells:
overall_status=blocked_holdout_directional_hurt
candidate_rows=793
candidate_delta=+0.097
q6_count delta=-0.017
q6_cells delta=+0.354
applied_hurts=q6_cells:2505,q6_cells:2408,q6_cells:2508,q6_cells:2405,q6_count:2508,...

evidence_profile_key q6_count+q6_cells:
overall_status=blocked_holdout_directional_hurt
candidate_rows=628
candidate_delta=-0.030
q6_count delta=-0.012
q6_cells delta=-0.092
applied_hurts=q6_cells:public:total+item+shape,q6_cells:public:random_avg+shape,...

evidence_profile_key q6_count strict gate:
overall_status=blocked_holdout_directional_hurt
candidate_rows=99
candidate_delta=+0.081
```

结论：

- `v3_ccvc_` 的 q6_count 是弱正向候选，但按当前 direction candidate 放行仍会误放多个 map/profile。
- q6_cells 是主要风险源；map holdout 下 cells delta `+0.354`，不能进入 formal。
- 简单收紧 hurt/directional threshold 不可行，会缩小覆盖但让 q6_count holdout 变差。
- 下一步需要拆 evidence contribution：public total、random_avg、q6 floor、explicit q6 anchor、unqualified anchor 分别如何影响 count/cells，而不是继续调候选阈值。

## 2026-06-05 checkpoint：v3 CCVC evidence contribution audit

实现：

- 新增 `scripts/summarize_v3_ccvc_evidence_contribution.py`。
  - 对 `v3_ccvc_` p50 movement 按证据特征拆分贡献。
  - 输出每个 component/feature 的 `mae_delta`、`present_minus_absent_mae_delta`、changed hurt rate、directional error rate。
  - 当前特征包括 `public_total`、`public_random_avg`、`public_max_item_cells`、`tool_category`、`item_anchor`、`shape_anchor`、`layout`、`q6_floor`、`explicit_q6_anchor`、`unassigned_anchor` 及常见组合。
- 新增 `tests/test_summarize_v3_ccvc_evidence_contribution.py`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_ccvc_evidence_contribution.py tests\test_summarize_v3_ccv_direction_audit.py tests\test_summarize_v3_ccv_direction_holdout.py tests\test_evaluate_fatbeans_v3_samples.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccvc_evidence_contribution.py --posterior-trials 128 --top 40
```

结果：

```text
focused tests: 13 passed

component=q6_count delta=-0.033 pred_delta=+0.139 hurt_rate=0.443730 directional_error=0.292605
component=q6_cells delta=-0.168 pred_delta=-0.074 hurt_rate=0.495177 directional_error=0.428725

q6_count positive:
unassigned_anchor delta=-0.115 present_minus_absent=-0.127 hurt_rate=0.327485
tool_category delta=-0.093 present_minus_absent=-0.072 hurt_rate=0.275862
q6_floor delta=-0.052 present_minus_absent=-0.030 hurt_rate=0.438596
public_total delta=-0.040 present_minus_absent=-0.009 hurt_rate=0.421875

q6_cells blocked:
public_max_item_cells hurt_rate=0.653061 present_minus_absent=+0.129
tool_category hurt_rate=0.600000 present_minus_absent=+0.172
item_anchor hurt_rate=0.520803 present_minus_absent=+0.278
public_random_avg hurt_rate=0.516129 present_minus_absent=-0.265
public_total hurt_rate=0.447236 present_minus_absent=-0.745
```

结论：

- q6_count 的有用信号主要来自 `unassigned_anchor`、`tool_category`、`q6_floor`、`public_total`，但 hurt rate 仍不能支撑 promotion。
- q6_cells 全局 MAE 改善主要来自 public total/layout/random_avg 等高信息窗口；但 changed-row hurt rate 太高，不能直接移动 cells p50。
- `public_max_item_cells`、`tool_category`、`item_anchor` 对 q6_cells 是风险特征：它们 presence 下 hurt rate 高，且相对 absent 更差。
- 下一步 likelihood 应先把 count 和 cells 拆成不同 gate：count 可以继续研究证据上移/下移，cells 暂时需要更强的 capacity/total consistency 或 holdout guard。

## 2026-06-05 checkpoint：v3 CCVC freeze-cells count-only audit

实现：

- `V3CcvOptions` 新增 `component_move_cells`，默认保持旧 shadow 行为。
- `v3_ccvc_` component likelihood 新增 `move_cells=False` 路径：
  - q6_count 和 q6_value 继续使用 CCVC component posterior。
  - q6_cells p50/p90 直接透传 baseline posterior cells，不再随 component likelihood 移动。
  - diagnostics 输出 `ccvc_move_cells=off` 和 `ccvc_cells_passthrough`。
- archive evaluator、direction audit、direction holdout、evidence contribution audit 均新增 `--ccv-component-freeze-cells`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_inference_v3_posterior.py tests\test_inference_v3_pipeline.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_ccv_direction_audit.py tests\test_summarize_v3_ccv_direction_holdout.py tests\test_summarize_v3_ccvc_evidence_contribution.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 128 --ccv-component-freeze-cells
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_holdout.py --posterior-trials 128 --candidate-prefix v3_ccvc_ --ccv-component-freeze-cells --group-field evidence_profile_key --component q6_count --component q6_cells --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccvc_evidence_contribution.py --posterior-trials 128 --ccv-component-freeze-cells --top 40
```

结果：

```text
focused tests: 36 passed
v3/live focused suite: 115 passed

archive freeze-cells:
q6_count_p50_mae=1.441
q6_cells_p50_mae=6.843
v3_ccvc_q6_count_p50_mae=1.408
v3_ccvc_delta_q6_count_p50_mae=-0.033
v3_ccvc_q6_cells_p50_mae=6.843
v3_ccvc_delta_q6_cells_p50_mae=0.000
v3_ccvc_q6_value_p50_mae=380540.4
v3_ccvc_delta_q6_value_p50_mae=-6864.3

profile holdout freeze-cells:
overall_status=blocked_holdout_directional_hurt
candidate_rows=490
candidate_delta=-0.012
q6_cells candidate_rows=0
q6_count delta=-0.012 hurt_rate=0.083673 directional_error=0.048980

contribution freeze-cells:
q6_count changed=311 delta=-0.033 hurt_rate=0.443730 directional_error=0.292605
q6_cells changed=0 delta=0.000
```

结论：

- freeze-cells 成功隔离了 CCVC 当前最大的 q6_cells 误移动风险。
- count/value 的全局收益仍存在：q6_count MAE `-0.033`，q6_value MAE `-6864.3`。
- 但 q6_count 的 holdout directional hurt 仍未清除，尤其 `item+shape+layout`、`public:total+item+shape`、`public:max_item_cells+item+shape`。
- 该路径可作为 v3 下一步 count-only shadow baseline，但不能进入 formal live 出价。
- 距离正式使用的主要缺口不是 UI 或归档，而是 evidence profile 下 q6_count movement 的稳定性与 promotion gate。

## 2026-06-05 checkpoint：v3 CCVC q6_count movement-policy matrix

实现：

- `summarize_v3_ccv_direction_audit.py` 新增 `--movement-policy all|up_only|down_only`。
- `summarize_v3_ccv_direction_holdout.py` 新增：
  - `--movement-policy`
  - 复合 `--group-field`，例如 `map_id,evidence_profile_key`
  - `--candidate-include-pattern` / `--candidate-exclude-pattern`
  - 摘要输出 candidate below-rate。
- 新增 `scripts/summarize_v3_ccvc_count_policy_matrix.py`，一次加载 archive 后批量比较 group-field x movement-policy。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_ccv_direction_audit.py tests\test_summarize_v3_ccv_direction_holdout.py tests\test_summarize_v3_ccvc_count_policy_matrix.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccvc_count_policy_matrix.py --posterior-trials 128 --ccv-component-freeze-cells
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_ccv_direction_holdout.py --posterior-trials 256 --candidate-prefix v3_ccvc_ --ccv-component-freeze-cells --group-field evidence_profile_key --component q6_count --movement-policy down_only --min-windows 30 --candidate-exclude-pattern "^q6_count:shape$" --top 20
```

结果：

```text
tests: 11 passed

128-trial policy matrix:
evidence_profile_key all       delta=-0.012 blocked
evidence_profile_key up_only   delta=-0.004 blocked
evidence_profile_key down_only delta=-0.041 blocked by item+shape+layout
map_id all                     delta=-0.017 blocked by 2508,2405,2506,2401
map_id up_only                 delta=-0.020 blocked by 2508,2405
map_id down_only               delta=+0.020 blocked by 2506,2401
map_id,evidence_profile_key    sparse and harmful; not viable at current sample size

128-trial profile down_only min_windows=30:
status=watch
candidate_rows=331
delta=-0.045
hurt_rate=0.003021
directional_error=0.003021

256-trial profile down_only min_windows=30:
status=blocked_holdout_directional_hurt
candidate_rows=214
delta=-0.004
applied_hurts=q6_count:shape

256-trial profile down_only min_windows=30 exclude bare shape:
status=watch
candidate_rows=157
delta=-0.025
hurt_rate=0.025478
directional_error=0.006369
baseline_below=0.401274
candidate_below=0.420382
```

结论：

- 单纯 `up_only` 不能解决当前 q6_count；收益太弱且仍有 holdout hurt。
- `down_only` 在 profile 维度最稳定，但它主要修正过高 q6_count，不是低估修复。
- bare `shape` profile 对 sampler trials 不稳定：128-trial 可过，256-trial 变成 applied hurt。
- `down_only + min_windows=30 + exclude ^q6_count:shape$` 是当前最稳的 q6_count movement-policy shadow 候选，但会把 below-rate 从 `0.401274` 提到 `0.420382`。
- 该候选只适合继续作为审计/过高修正实验，不应进入 formal live；下一步低估修复仍应看 q6 value/cells/value sampler 与 public total/capacity consistency，而不是把 q6_count 继续下修。

## 2026-06-05 checkpoint：v3 residual q6-value under holdout

实现：

- 新增 `scripts/summarize_v3_residual_under_value_holdout.py`。
  - 训练侧按 group 识别系统性低估、public total/q6 floor 证据、residual q6_value 上移、count/cells/value/formal 不伤害。
  - holdout 侧只把通过训练的 group 作为 candidate 评估。
  - 显式输出 `formal_passthrough=True`，因为当前 residual posterior 不改变 formal decision value。
- 新增 `tests/test_summarize_v3_residual_under_value_holdout.py`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_residual_under_value_holdout.py tests\test_summarize_v3_residual_profile_candidates.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_residual_under_value_holdout.py --posterior-trials 128 --by evidence_profile_key --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_residual_under_value_holdout.py --posterior-trials 256 --by evidence_profile_key --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_residual_under_value_holdout.py --posterior-trials 128 --posterior-seed 1 --by evidence_profile_key --min-windows 30 --top 20
```

结果：

```text
focused tests: 5 passed

128-trial evidence_profile:
overall_status=blocked_holdout_hurt
candidate_rows=40
candidate_groups=public:total+item+shape,public:total+shape
formal_delta=0.0
q6_value_delta=+15187.3
applied_hurts=public:total+item+shape

256-trial evidence_profile:
overall_status=blocked_holdout_hurt
candidate_rows=70
candidate_groups=public:total+item+shape,public:total+shape
formal_delta=0.0
q6_value_delta=-17189.8
applied_hurts=public:total+shape

256-trial evidence_profile min_windows=30:
overall_status=watch
candidate_groups=public:total+item+shape
q6_value_delta=-23608.6

128-trial evidence_profile min_windows=30:
overall_status=blocked_holdout_hurt
candidate_groups=public:total+item+shape
q6_value_delta=+15631.3

128-trial seed=1 min_windows=30:
overall_status=sample_limited
candidate_rows=0
```

结论：

- residual q6-value under candidate 目前不能 promotion。
- `public:total+item+shape` 在 128/256 trials 间方向相反；seed=1 又没有候选，说明 sampler stability 未过关。
- `public:total+shape` 在 256-trial holdout 下伤害 q6_value。
- 当前 residual posterior 是 `resid_formal_passthrough`，所以它不能直接修复正式出价低估，只能诊断 q6 component。
- 下一步需要真正的 formal/value sampler 设计：要把 q6 value/cells 的上修映射到 formal decision candidate，并同时过 trials stability、below-rate、P90 over 和 holdout hurt。

## 2026-06-05 checkpoint：v3 formal-value delta mapping audit

实现：

- 新增 `scripts/summarize_v3_formal_value_delta_holdout.py`。
  - 支持 `--candidate-prefix v3_ccv_|v3_ccvc_|v3_resid_`。
  - 用 audit-only 公式 `candidate_formal = baseline_formal + (candidate_q6_formal - baseline_q6_formal)`。
  - 训练侧要求系统性低估、public total/q6 floor 证据、q6 formal 上移、MAE/P90 不伤害。
  - holdout 侧检查 formal MAE、q6 formal MAE、below-rate、over-rate、P90 coverage/pinball。
  - 增加 high-over guard：候选过估率高于 `0.60` 不放行。
- 新增 `tests/test_summarize_v3_formal_value_delta_holdout.py`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest -p no:cacheprovider tests\test_summarize_v3_formal_value_delta_holdout.py -q
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_formal_value_delta_holdout.py --posterior-trials 128 --candidate-prefix v3_ccv_ --by evidence_profile_key --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_formal_value_delta_holdout.py --posterior-trials 128 --candidate-prefix v3_ccv_ --by map_id --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_formal_value_delta_holdout.py --posterior-trials 256 --candidate-prefix v3_ccv_ --by evidence_profile_key --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_formal_value_delta_holdout.py --posterior-trials 128 --candidate-prefix v3_ccvc_ --ccv-component-freeze-cells --by evidence_profile_key --top 20
C:\Users\shenc\anaconda3\python.exe .\scripts\summarize_v3_formal_value_delta_holdout.py --posterior-trials 128 --candidate-prefix v3_resid_ --by evidence_profile_key --top 20
```

结果：

```text
focused tests: 4 passed
v3/live focused suite: 128 passed

v3_resid_ evidence_profile:
overall_status=sample_limited
candidate_rows=0

v3_ccvc_ freeze-cells evidence_profile:
overall_status=sample_limited
candidate_rows=0

v3_ccv_ evidence_profile 128-trial:
overall_status=blocked_holdout_hurt
candidate_groups=item+shape+layout
formal_delta=+6633.5
q6_formal_delta=+8512.5
candidate_below=0.583333
applied_hurts=item+shape+layout

v3_ccv_ evidence_profile 256-trial:
overall_status=sample_limited
candidate_rows=0

v3_ccv_ map_id 128-trial:
overall_status=blocked_holdout_hurt
candidate_groups=2502
formal_delta=-1015.2
q6_formal_delta=-1015.2
candidate_over=0.75
applied_hurts=2502
```

结论：

- `v3_resid_` 和 `v3_ccvc_` 当前没有 q6 formal delta，因此无法作为 formal-value 修复来源。
- `v3_ccv_` 能产生 q6 formal delta，但 profile holdout 会伤害 MAE/低估，map holdout 的 `2502` 虽小幅降 MAE，却处在高过估窗口，不能推广。
- 该 audit 证明“component delta 映射 formal”这条最小路径目前也不能 promotion。
- 下一步若继续 formal 低估修复，不能只复用现有 q6 component shadow；需要设计新的 formal/value sampler 或校准层，并把 high-over guard 与 sampler stability 作为硬门槛。

## 2026-06-06 checkpoint：0605 活动样本解析与沉船 cohort 分层

背景：

- 用户在 2026-06-05 晚间新增 23 个 manual inbox 样本。
- 游戏在 2026-06-05 12:00 后更新沉船活动：白色藏品有概率变成红色藏品。
- 该活动会改变沉船生成/品质分布，不能和旧沉船 drop prior 混作同一校准口径。

修复：

- `src/bidking_lab/live/fatbeans.py`
  - `reconstruct_fatbeans_frames()` 改为按 TCP flow 分流重建 frame。
  - 遇到无效 frame length 时按字节 resync，而不是直接让整文件 parse error。
  - 兼容 0605 manual 导出中不同 TCP flow 交错、捕获起点含半帧/脏字节的情况。
- `scripts/organize_fatbeans_real_samples.py`
  - 保留已有 archive canonical 文件名，不再因新增样本插入排序而重排旧 `_0001/_0002` 后缀。
  - 新增样本仍可通过 dry-run/apply 进入 canonical archive。
- 新增回归测试：
  - `test_fatbeans_parser_reconstructs_interleaved_tcp_streams`
  - `test_fatbeans_parser_resyncs_after_leading_partial_frame_bytes`
  - `test_plan_keeps_existing_archive_name_when_new_samples_shift_order`

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_organize_fatbeans_real_samples.py tests\test_live_fatbeans.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_fatbeans_sample_manifest.py data\samples\fatbeans data\samples\fatbeans_manual_inbox --output .tmp\sample_manifest_20260606_after_parser.json
C:\Users\shenc\anaconda3\python.exe scripts\organize_fatbeans_real_samples.py --manifest-output .tmp\organize_20260606_stable_names.json
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py data\samples\fatbeans_manual_inbox --posterior-trials 0 --format summary
```

结果：

```text
parser/organizer focused tests:
65 passed, 25 skipped

manifest archive + manual inbox:
files=456 parsed_files=456 parse_errors=0
valid_files=439 mixed_files=17 invalid_files=0
ready_windows=1618 no_state_windows=17

organizer dry-run:
input_files=466 unique_files=456 duplicates=10
move=23 keep=433 errors=0
valid=439 mixed=17 invalid=0
ready_windows=1618

manual inbox v3 window audit:
windows=84 ready=84 no_state=0 constraint_conflict=0 parse_errors=0
prior_ready=26 truth_ready=84 decision_truth_ready=84
```

0605 manual inbox 分布：

```text
files=23
by_family: villa=8, shipwreck=15
by_map:
2401=2, 2404=2, 2405=1, 2407=1, 2408=1, 2410=1,
2521=5, 2522=1, 2524=3, 2526=2, 2528=1, 2529=3
by_hero:
aisha=10, ethan=9, gabriela=1, sophie=1, tatiana=1, wuqilin=1
```

本地表状态：

- `data/raw/tables/BidMap.txt` 与 `Drop.txt` 仍是 2026-05-26 时间戳。
- `data/processed/maps.json` 生成于 2026-06-05 11:50，但不包含 `2521/2522/2524/2526/2528/2529`。
- 外部参考目录未搜到这些 252x map id。

当前处理策略：

- 8 个 24xx 别墅样本可作为普通真实样本使用。
- 15 个 252x 沉船样本可用于 capture/window/truth 审计。
- 15 个 252x 沉船样本暂不进入普通沉船 prior/posterior 校准；需要等待新表，或显式建模“0605 白转红活动”映射后再纳入。

## 2026-06-06 checkpoint：0605 样本归档完成

归档动作：

- 8 个 24xx 别墅样本已从 `data/samples/fatbeans_manual_inbox/` 移入默认主库 `data/samples/fatbeans/`。
- 15 个 252x 沉船活动样本已移入独立 cohort：
  `data/samples/fatbeans_activity_20260605_shipwreck/`。
- `data/samples/fatbeans_manual_inbox/` 当前无待处理 JSON。
- `.gitignore` 已加入活动 cohort JSON 规则，样本本体继续保持本地 ignored。

提交的 manifest：

- `data/sample_manifests/fatbeans_archive_v3_2026-06-06.json`
- `data/sample_manifests/fatbeans_activity_shipwreck_2026-06-05.json`

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe scripts\summarize_fatbeans_sample_manifest.py data\samples\fatbeans --output data\sample_manifests\fatbeans_archive_v3_2026-06-06.json
C:\Users\shenc\anaconda3\python.exe scripts\summarize_fatbeans_sample_manifest.py data\samples\fatbeans_activity_20260605_shipwreck --output data\sample_manifests\fatbeans_activity_shipwreck_2026-06-05.json
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 0 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 0 --format summary
```

结果：

```text
main archive:
files=441 parsed_files=441 parse_errors=0
valid_files=424 mixed_files=17 invalid_files=0
ready_windows=1560 no_state_windows=17

activity shipwreck cohort:
files=15 parsed_files=15 parse_errors=0
valid_files=15 mixed_files=0 invalid_files=0
ready_windows=58 no_state_windows=0

default v3 evaluator:
windows=1577 ready=1560 parse_errors=0
prior_ready=1560 truth_ready=1577 decision_truth_ready=1560

activity cohort v3 evaluator:
windows=58 ready=58 parse_errors=0
prior_ready=0 truth_ready=58 decision_truth_ready=58
```

结论：

- 默认 archive/evaluator 现在只使用 441 份普通样本；新增别墅已纳入默认校准候选。
- 252x 沉船活动样本被保留为独立鲁棒性 cohort；没有新 drop table 前不参与普通沉船 prior/posterior 校准。
- 后续 v3 可用该 cohort 检查“模型遇到活动机制/旧表缺失时是否能保持保守、不误用旧先验”。

## 2026-06-06 checkpoint：v3 prior/activity 鲁棒性审计接入

完成内容：

- 新增 `src/bidking_lab/inference/v3/prior_robustness.py`。
- `scripts/evaluate_fatbeans_v3_samples.py` 输出 `v3_robust_*` 字段和 summary counters。
- `scripts/summarize_v3_promotion_readiness.py` 新增 `prior_robustness` gate，formal promotion 前必须排除活动、缺表、prior stress 和弱 fallback。
- `v3_robust_affects_bid=false` 固定保持；该层只用于审计和后续 promotion gate。
- 252x 沉船活动候选在缺少本地 drop table 时标记为 `activity_candidate=true`、`prior_usable=false`、`fallback_mode=missing_prior_truth_only`。
- 普通 archive 中 `summary_likelihood` fallback 标记为 `prior_usable=true` 但 `prior_trusted=false`，避免弱 fallback 被误当正式 promotion 证据。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_inference_v3_prior_robustness.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_pipeline.py
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
```

结果：

```text
focused tests:
16 passed

activity cohort:
windows=58 ready=58 parse_errors=0
prior_ready=0
robust_prior_usable=0
robust_prior_trusted=0
robust_activity_candidate=58
posterior_ready=0 posterior_no_match=58

main archive 64-trial:
windows=1577 ready=1560 no_state=17 parse_errors=0
prior_ready=1560
robust_prior_usable=1560
robust_prior_trusted=359
robust_activity_candidate=0
robust_prior_stressed=94
posterior_ready=1560 posterior_strict_ready=361 posterior_summary_likelihood=1199
formal_p50_mae=318635.858
formal_p50_below_rate=0.51859
formal_p90_coverage=0.750641
```

结论：

- v3 现在能把“活动/新表缺失”与“普通模型误差”分开。
- 当前普通 archive 的弱 fallback 覆盖面大，但可信 promotion 分母仍主要是 strict/非 stress 行；后续不能只看全量 fallback 指标。
- 0605 沉船活动 cohort 可继续用于鲁棒性回归，不进入普通 prior tuning。

## 2026-06-06 checkpoint：v3 prior robustness 对齐 live/model_eval

完成内容：

- `src/bidking_lab/inference/v3/priors.py` 新增共享 `empty_prior_flat_dict()` 与 `summarize_drop_prior_flat_dict()`。
- `scripts/evaluate_fatbeans_v3_samples.py` 改为使用共享 prior flat helper，不再维护私有字段集合。
- `src/bidking_lab/live/monitor.py` 的 `v3_posterior_shadow` 现在输出：
  - `v3_prior_*`
  - `v3_robust_*`
- `model_eval.jsonl` 行同步展开 `v3_prior_*` 与 `v3_robust_*`，便于局后审计 activity/prior-drift。
- 未知 252x 活动地图在 live v3 shadow 中 fail-closed：保留 `error=unknown_map_id`，同时标记 `v3_robust_activity_candidate=true` 与 `fallback_mode=missing_prior_truth_only`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_inference_v3_priors_truth.py tests\test_inference_v3_prior_robustness.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 0 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 0 --format summary
```

结果：

```text
focused tests:
63 passed

default archive 0-trial:
windows=1577 ready=1560 parse_errors=0
prior_ready=1560
robust_prior_usable=1560
robust_activity_candidate=0

activity cohort 0-trial:
windows=58 ready=58 parse_errors=0
prior_ready=0
robust_prior_usable=0
robust_prior_trusted=0
robust_activity_candidate=58
```

结论：

- archive/live/model_eval 现在使用同一套 prior flat 字段与 robustness 语义。
- live 不会把活动期/缺表地图静默当成普通 prior；这只进入 shadow artifact 和 model_eval，不改变 v2 formal 出价或 UI 主建议。

## 2026-06-06 checkpoint：prior-stress 分片审计

完成内容：

- 新增 `scripts/summarize_v3_prior_robustness_audit.py`。
- 新增 `tests/test_summarize_v3_prior_robustness_audit.py`。
- 审计脚本支持按 `v3_robust_status`、`v3_robust_reason`、`fallback_mode`、`map_id`、`hero_map_evidence_profile` 分组。
- 输出 ready/posterior-ready/metric rows、trusted/activity/stressed 计数、reason/fallback/scope 分布、formal/q6 指标，以及 hard evidence target 相对 prior expected 的 ratio。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_summarize_v3_prior_robustness_audit.py tests\test_inference_v3_prior_robustness.py tests\test_evaluate_fatbeans_v3_samples.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --by v3_robust_status --by v3_robust_reason --by map_id --top 6
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --by v3_robust_status --by map_id --top 4
```

结果：

```text
focused tests:
11 passed

main archive prior_stressed:
ready=94 post_ready=94 metric=94 trusted=0/94
summary_likelihood=92 strict=2
mae=381373.9 bias=-124899.4 below=0.670213 p90_cover=0.595745
q6_count_mae=1.58 q6_cells_mae=8.01 q6_value_mae=484855.1
top reasons:
total_cells_above_prior=48
q6_cells_above_prior=32
total_count_above_prior=15
q6_value_above_prior=13
total_value_above_prior=13

activity cohort:
prior_unavailable ready=58 post_ready=0 metric=0
trusted=0/58 activity=58
fallback=missing_prior_truth_only
```

结论：

- prior-stressed 行不是少量噪声：它们 MAE、below-rate、P90 coverage 都明显差于弱 fallback 总体。
- 主要压力来自 total/q6 cells 高于旧 prior，而不是 q6 count；下一步更应审计 capacity/cells/value evidence，而不是继续改 q6 count prior。
- 252x 活动 cohort 已明确没有 posterior-ready/metric rows，不会混入普通准确率。

## 2026-06-06 checkpoint：新窗口交接整理

完成内容：

- 新增 `handoff_2026-06-06.zh-CN.md`，作为下一窗口首读入口。
- 根索引 `PROGRESS.md`、`DECISIONS.md`、`OBSERVATIONS.md` 已指向 0606 handoff 和当前 v3 记录。
- `docs/PROJECT_STRUCTURE_V3.zh-CN.md` 已登记 0606 handoff。
- handoff 中整理了：
  - 当前 v3 主线边界；
  - 普通样本库与 0605 沉船活动 cohort；
  - 最新 archive/prior-stress 指标；
  - 已确认核心问题；
  - 下一步 prior-stressed cells/capacity/evidence 审计；
  - formal/value sampler 第一阶段建议；
  - 可复制的新窗口 prompt；
  - 推荐 goal 文案。

结论：

- 本 checkpoint 只改变文档和交接入口，不改变 v2 formal/live/UI，也不改变 v3 shadow 推理行为。
- 新窗口应从 `handoff_2026-06-06.zh-CN.md` 继续，不需要翻长聊天记录。

## 2026-06-06 checkpoint：prior-stress cells/capacity/evidence 明细审计

完成内容：

- `scripts/summarize_v3_prior_robustness_audit.py` 新增 `--details` 与 `--details-reason`。
- details 行现在输出：
  - total/q6 cells 的 exact/floor source、target、prior expected、truth、posterior p50/p90、target/prior ratio、target-vs-truth delta、posterior-vs-truth delta；
  - total/q6 value floor 相对 prior/truth/posterior 的同口径明细；
  - numeric/item/shape/quality-floor evidence 计数；
  - item count capacity proxy：target/truth item count 是否超过 `v3_prior_items_per_session_max`。
- `tests/test_summarize_v3_prior_robustness_audit.py` 覆盖 details 输出、reason filter、activity reason 不产生 prior-stress details。

验证：

```powershell
$env:TMP=(Join-Path (Get-Location) '.tmp')
$env:TEMP=$env:TMP
New-Item -ItemType Directory -Force -Path $env:TMP | Out-Null
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_summarize_v3_prior_robustness_audit.py tests\test_inference_v3_prior_robustness.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --by v3_robust_status --by v3_robust_reason --by map_id --top 6 --details 6
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --by v3_robust_status --by map_id --top 4 --details 4
```

结果：

```text
focused tests:
14 passed

main archive prior_stressed:
ready=94 post_ready=94 metric=94 trusted=0/94
summary_likelihood=92 strict=2
mae=381373.9 bias=-124899.4 below=0.670213 p90_cover=0.595745
top reasons:
total_cells_above_prior=48
q6_cells_above_prior=32
total_count_above_prior=15
q6_value_above_prior=13
total_value_above_prior=13

activity cohort:
prior_unavailable ready=58 post_ready=0 metric=0 activity=58
prior_stress_details: empty
```

明细审计结论：

- `total_cells_above_prior` 中存在多行 hard target 与 truth 一致，并且 truth/target item count 超过 prior max，例如 `ethan|2506|shape`：`total_cells floor=216 prior=91.086 truth=216`、`q6_cells floor=37 prior=10.109 truth=37`、`item_count truth=58 prior_max=44`。这更像旧 prior/capacity 表低估或 profile-specific capacity drift，不是 q6_count 单点问题。
- `q6_cells_above_prior` 的 target/prior ratio 可达 3-4 倍，但 posterior 有时已经高于 truth；这类行不能直接转成统一 q6 cells/value 上修。
- `q6_value_above_prior` / `total_value_above_prior` 主要是 value floor 远高于 prior 的分片，且同时存在 posterior over 和 under；后续只能作为 formal/value sampler 的独立候选分片，并保留 high-over guard。
- 252x 活动 cohort 没有 prior-stress details，继续只作为 activity/prior-unavailable 鲁棒性分母。

下一步：

- formal/value sampler 第一阶段应先把 prior-stressed 行拆成 capacity/cells drift、q6 cells floor、value floor stress 三类 shadow 分片，再做 candidate 输出和 holdout；不要把这些行混入普通 calibration，也不要直接调高 q6_count 或固定 prior。

## 2026-06-06 checkpoint：shadow-only formal/value sampler 第一阶段

完成内容：

- 新增 `src/bidking_lab/inference/v3/formal_value_sampler.py`，输出 `v3_fv_*` shadow namespace。
- sampler 将 prior-stress 明细拆成：
  - `capacity_cells_drift`：total count/cells 超 prior 或 item count 超 prior max；
  - `q6_cells_floor_stress`：q6 cells exact/floor 明显高于 q6 prior；
  - `value_floor_stress`：total/q6 value floor 明显高于 prior。
- `v3_fv_active=false`、`v3_fv_affects_bid=false` 固定保持；capacity/cells-only watch 不做价值上修，只有 value-floor stress 标记为 shadow candidate。
- archive evaluator、shared v3 pipeline、live artifact/model_eval 已接入 `v3_fv_*`。
- 新增 `scripts/summarize_v3_formal_value_sampler_holdout.py`，按 session fold 验证 `v3_fv_candidate`；训练折只选择有足够 value-floor 候选的 group，验证折只在 holdout 行本身也触发 value-floor candidate 时应用 `v3_fv_*`。
- `scripts/summarize_v3_promotion_readiness.py` 新增 `formal_value_sampler_holdout` gate。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_inference_v3_formal_value_sampler.py tests\test_inference_v3_pipeline.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_formal_value_sampler_holdout.py --posterior-trials 64 --folds 5 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --folds 5 --format summary
```

结果：

```text
focused tests:
46 passed

main archive:
v3_fv_candidate_rows=13
v3_fv_capacity_watch_rows=126
v3_fv_value_floor_candidate_rows=13
v3_fv_formal_p50_mae=318635.858
v3_fv_delta_formal_p50_mae=0.0
v3_fv_formal_p90_coverage=0.750641

activity cohort:
posterior_ready=0
metric_rows=0
v3_fv_candidate_rows=0
v3_fv_capacity_watch_rows=0

formal/value sampler holdout:
overall_status=sample_limited
candidate_rows=0
train_status_counts=blocked_low_sample:414

promotion readiness:
overall_status=not_ready
gate=formal_value_sampler_holdout status=blocked
formal_value_rows=0
formal_value_delta=None
```

结论：

- `v3_fv_*` 已形成 archive/live/readiness/holdout 一致的 shadow-only 分母，但默认 session holdout 下 value-floor candidate 样本不足，不能 promotion。
- 当前 archive 上 `v3_fv_delta_formal_p50_mae=0.0`，说明第一阶段 candidate 主要用于显式分母和诊断；baseline posterior 已经吸收这些 hard floors。
- v2 formal/live/UI 不变；v3 promotion 与 v2 archive 仍然不讨论，直到 prior robustness、formal baseline、holdout gates 通过。

## 2026-06-06 checkpoint：prior-stress detail summary 聚合一致性审计

完成内容：

- `scripts/summarize_v3_prior_robustness_audit.py` 新增 `--detail-summary` / `--detail-summary-top`。
- JSON 输出新增 `detail_summary`，包含：
  - overall 与 by-reason 聚合；
  - total/q6 cells/value source counts；
  - capacity flag counts；
  - detail flag counts；
  - target-vs-truth match counts；
  - target/prior ratio avg/p90/max；
  - evidence count avg/p90/max；
  - map/profile/scope/fallback/reason counts。
- `tests/test_summarize_v3_prior_robustness_audit.py` 覆盖 detail summary 的 source、capacity flag、detail flag、ratio 和 by-reason 聚合。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_summarize_v3_prior_robustness_audit.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 4
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --top 2 --detail-summary --detail-summary-top 4
```

结果：

```text
focused tests:
8 passed

main archive detail_summary:
rows=94
capacity_flags=truth_count_above_prior_max:68,target_count_above_prior_max:39
sources_total_cells=floor:57,exact:37
sources_q6_cells=floor:59,none:35
ratio_total_cells avg=1.328 p90=2.126 max=2.371
ratio_q6_cells avg=1.898 p90=2.881 max=4.001
ratio_q6_value avg=1.917 p90=3.309 max=4.825

reason=total_cells_above_prior:
rows=48
truth_count_above_prior_max=44
target_count_above_prior_max=30
sources_total_cells=exact:32,floor:16

reason=q6_cells_above_prior:
rows=32
sources_q6_cells=floor:32
ratio_q6_cells avg=2.791 p90=3.66 max=4.001

activity cohort detail_summary:
rows=0
```

结论：

- prior-stressed 的主风险已经更明确：大量 truth/target item count 超出旧 prior max，且 total cells 有 37 行 exact hard evidence、57 行 floor evidence；这支持继续把 capacity/table/evidence drift 和 value-floor stress 分开审计。
- q6 cells stress 是 floor 驱动，且 target/prior ratio 可到 `4.001`；但它不能直接转为 q6 value/formal 上修，仍需要 changed-row hurt 与 high-over guard。
- 活动 cohort 仍不进入 prior-stress detail 分母，避免把缺表活动样本误计入普通校准。

## 2026-06-06 checkpoint：prior-stress map/profile 热点聚合

完成内容：

- `scripts/summarize_v3_prior_robustness_audit.py` 新增 `--detail-summary-by`，可按 `map_id`、`evidence_profile_key`、`hero_map_evidence_profile` 等 detail 字段聚合。
- `detail_summary.by_group` 现在输出：
  - `field` / `value`；
  - `rows`；
  - `capacity_flag_hits`；
  - `max_cells_ratio` / `max_value_ratio`；
  - reason/source/capacity/evidence/profile counts；
  - cells/value target-prior ratio summary。
- `tests/test_summarize_v3_prior_robustness_audit.py` 覆盖 `by_group` 的 map/profile 聚合。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_summarize_v3_prior_robustness_audit.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 5 --detail-summary-by map_id --detail-summary-by hero_map_evidence_profile
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 3 --detail-summary-by map_id
```

结果：

```text
unit:
1 passed

top map groups:
map_id=2401 rows=12 capacity_hits=9 max_cells_ratio=4.001 max_value_ratio=3.309
map_id=2501 rows=10 capacity_hits=16 max_cells_ratio=3.36 max_value_ratio=3.194
map_id=2404 rows=10 capacity_hits=7 max_cells_ratio=2.881 max_value_ratio=1.017
map_id=2406 rows=10 capacity_hits=6 max_cells_ratio=2.381 max_value_ratio=4.825
map_id=2601 rows=8 capacity_hits=16 max_cells_ratio=2.157 max_value_ratio=0.142

activity cohort:
prior_stress_detail_summary rows=0
```

结论：

- capacity/table drift 不是单一 map 问题；2401、2501、2404、2406、2601 都进入热点，但风险形态不同。
- `2501` 与 `2601` capacity hits 高，优先看 drop table capacity/prior max 与 session item count 口径。
- `2406` max value ratio 高，属于 value-floor stress 与 capacity/cells drift 混合热点；仍不能直接 promotion。
- 下一步应把这些 group 作为 targeted audit/readiness 分片，而不是继续只看全局 prior_stressed。

## 2026-06-06 checkpoint：readiness 接入 prior-stress capacity/table drift gate

完成内容：

- `scripts/summarize_v3_promotion_readiness.py` 接入 prior-stress details summary。
- readiness 新增 gate：`prior_stress_capacity_table_drift`。
- readiness JSON 新增 `prior_stress_detail_summary`，包含：
  - `rows`；
  - `capacity_flag_hits`；
  - capacity/source/ratio summary；
  - top `map_id` groups；
  - top `hero_map_evidence_profile` groups。
- `tests/test_summarize_v3_promotion_readiness.py` 覆盖：
  - 无 prior-stress 时该 gate 为 `pass`；
  - prior-stressed capacity row 会触发 blocked gate；
  - top map/profile group 进入 readiness 输出。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --folds 5 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --folds 5 --format summary
```

结果：

```text
readiness tests:
4 passed

main archive readiness:
gate=prior_stress_capacity_table_drift status=blocked
prior_stress_detail_rows=94
prior_stress_capacity_hits=107
top_map_group=2401 rows=12 capacity_flag_hits=9

activity readiness:
gate=prior_stress_capacity_table_drift status=pass
prior_stress_detail_rows=0
prior_stress_capacity_hits=0
```

结论：

- v3 promotion readiness 现在不再只看到 `robust_prior_stressed=94`；它能直接报告 capacity/table drift 热点。
- 活动 cohort 不产生 prior-stress capacity drift gate，仍由 prior-unavailable/activity gate 处理。
- 在该 gate blocked 前，不能把 v3 formal/value sampler 或其它 sampler 的局部改善用于 promotion，也不能讨论 v2 archive。

## 2026-06-06 checkpoint：live model_eval 补齐 `v3_fv_*` detail 字段

完成内容：

- `src/bidking_lab/live/monitor.py` 的 `model_eval` 现在展开 `v3_fv_*` detail 字段：
  - total/q6 count source、target、prior expected、target/prior ratio；
  - total/q6 cells source、target、prior expected、target/prior ratio；
  - total/q6 value source、target、prior expected、target/prior ratio。
- `tests/test_live_monitor.py` 增加断言，防止 live 局后复盘丢失这些字段。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_evaluate_fatbeans_v3_samples.py
```

结果：

```text
36 passed
```

结论：

- archive CSV 与 live `model_eval.jsonl` 现在都能保留 `v3_fv_*` capacity/cells/value detail 复盘口径。
- 这仍然是 shadow-only 记录路径，不改变 v2 formal/live/UI，也不改变正式出价。

## 2026-06-06 checkpoint：prior-stress target-vs-truth delta 聚合

完成内容：

- `scripts/summarize_v3_prior_robustness_audit.py` 的 detail summary 新增：
  - `target_truth_delta_counts`；
  - `target_truth_delta_summary`；
  - `post_p50_truth_delta_summary`。
- summary 输出现在显示 total/q6 cells 的 target delta counts：
  - `below`：target 低于 settlement truth；
  - `match`：target 等于 settlement truth；
  - `above`：target 高于 settlement truth。
- `tests/test_summarize_v3_prior_robustness_audit.py` 覆盖 target-vs-truth delta counts 和 delta summary。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_summarize_v3_prior_robustness_audit.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 3 --detail-summary-by map_id
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 3 --detail-summary-by map_id
```

结果：

```text
unit:
1 passed

main archive detail_summary:
rows=94
target_delta_total_cells=below=50/match=44/above=0
target_delta_q6_cells=below=46/match=13/above=0

reason=total_cells_above_prior:
target_delta_total_cells=below=9/match=39/above=0
target_delta_q6_cells=below=10/match=8/above=0

reason=q6_cells_above_prior:
target_delta_total_cells=below=25/match=7/above=0
target_delta_q6_cells=below=24/match=8/above=0

activity cohort:
prior_stress_detail_summary rows=0
```

结论：

- 当前 prior-stressed cells/capacity 问题不是 hard target 高于 settlement truth；聚合上 `above=0`。
- 更像旧 prior/capacity/table 低估，或 posterior 对已经存在的 hard/floor evidence 仍然偏低。
- 因此下一步应优先查 prior/capacity 表与 posterior evidence absorption，而不是把 floor 规则当作过强约束去削弱。

## 2026-06-06 checkpoint：prior-stress posterior-vs-target absorption 聚合

完成内容：

- `scripts/summarize_v3_prior_robustness_audit.py` 的 detail summary 新增 posterior-vs-target delta：
  - `post_p50_target_delta_counts`；
  - `post_p50_target_delta_summary`；
  - `post_p90_target_delta_summary`。
- prior-stress detail flags 新增：
  - `posterior_total_cells_below_target`；
  - `posterior_q6_cells_below_target`。
- summary 输出现在显示 total/q6 cells 的 `post50_target_delta_*` counts，用于判断 posterior 是否没有吸收到 already-compiled target。
- `tests/test_summarize_v3_prior_robustness_audit.py` 覆盖 posterior-vs-target delta counts 与 delta summary。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest tests\test_summarize_v3_prior_robustness_audit.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 3 --detail-summary-by map_id
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 3 --detail-summary-by map_id
```

结果：

```text
unit:
1 passed

main archive detail_summary:
rows=94
target_delta_total_cells=below=50/match=44/above=0
target_delta_q6_cells=below=46/match=13/above=0
post50_target_delta_total_cells=below=0/match=54/above=40
post50_target_delta_q6_cells=below=0/match=2/above=57

activity cohort:
prior_stress_detail_summary rows=0
post50_target_delta_total_cells=below=0/match=0/above=0
post50_target_delta_q6_cells=below=0/match=0/above=0
```

结论：

- 当前 archive 中 posterior p50 没有低于 compiled cells target 的聚合信号，说明 evidence absorption 不是第一嫌疑。
- `target <= truth` 且 `posterior >= target` 的组合更支持：旧 prior/capacity/table 覆盖不足，或 target 只是 settlement truth 的下界。
- 下一步优先把 prior/capacity 表、map/profile capacity max、drop prior 覆盖口径作为 blocker 审计，而不是先改正式出价或削弱 evidence compiler。

## 2026-06-06 checkpoint：capacity prior-max gap archive/live/readiness 复盘口径

完成内容：

- `scripts/summarize_v3_prior_robustness_audit.py` 的 detail summary 新增 `capacity_count_summary`：
  - total count source counts；
  - target/truth/prior min/max summary；
  - target/truth 相对 prior max 的 delta、ratio 与 counts；
  - target-vs-truth count delta counts。
- `scripts/evaluate_fatbeans_v3_samples.py` archive rows 新增同名 `v3_capacity_*` 字段：
  - `v3_capacity_total_count_source`；
  - `v3_capacity_total_count_target`；
  - `v3_capacity_truth_item_count`；
  - `v3_capacity_prior_items_per_session_min/max`；
  - target/truth prior-max delta、ratio；
  - `v3_capacity_flags`。
- `src/bidking_lab/live/monitor.py` 的 `model_eval` 也输出同名 `v3_capacity_*` 字段，保持 archive/live 局后复盘口径一致。
- `scripts/summarize_v3_promotion_readiness.py` 的 `prior_stress_capacity_table_drift` gate 与 `prior_stress_detail_summary` 现在携带 overall/top group 的 `capacity_count_summary`。
- 相关测试覆盖 archive row、live model_eval、prior detail summary 与 readiness gate。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.pytest-tmp tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 3 --detail-summary-by map_id
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 3 --detail-summary-by map_id
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --folds 5 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_formal_value_sampler_holdout.py --posterior-trials 64 --folds 5 --format summary
```

结果：

```text
focused tests:
41 passed

main archive prior_stress_detail_summary:
rows=94
capacity_flags=truth_count_above_prior_max:68,target_count_above_prior_max:39
capacity_count_sources=floor:62,exact:24,none:8
capacity_prior_max=n=94/avg=41.872/p90=44.0/max=44.0
capacity_target_prior_max_delta=n=86/avg=-7.419/p90=16.0/max=22.0
capacity_truth_prior_max_delta=n=94/avg=6.032/p90=20.0/max=22.0
capacity_target_truth_delta=n=86/avg=-13.047/p90=0.0/max=0.0
capacity_target_prior_counts=below=47/match=0/above=39
capacity_truth_prior_counts=below=25/match=1/above=68
capacity_target_truth_counts=below=56/match=30/above=0

activity cohort:
prior_stress_detail_summary rows=0
capacity_target_prior_counts=below=0/match=0/above=0

readiness:
overall_status=not_ready
gate=prior_stress_capacity_table_drift status=blocked
prior_stress_detail_rows=94
prior_stress_capacity_hits=107

formal/value sampler holdout:
overall_status=sample_limited
candidate_rows=0
```

结论：

- prior-stress capacity blocker 现在能直接回答“target/truth 比 prior max 高多少”，不再只靠 flag 数。
- target count 没有高于 settlement truth；`target_truth_counts above=0`，但 truth 高于 prior max 的样本很多，支持 capacity/table drift 或 target 下界不完整。
- archive/live/readiness 已有同名字段，后续 live 实战样本可以直接进入同一复盘口径；正式出价、v2 formal、UI 主建议未改变。

## 2026-06-06 checkpoint：capacity prior-max case 分类

完成内容：

- `scripts/summarize_v3_prior_robustness_audit.py` 的 item-count capacity detail 新增 `cases`。
- `capacity_count_summary` 新增 `case_counts`，并在 summary 输出中显示 `capacity_cases=`。
- `scripts/evaluate_fatbeans_v3_samples.py` archive rows 与 `src/bidking_lab/live/monitor.py` live `model_eval` 新增同名 `v3_capacity_cases`。
- readiness 的 `prior_stress_capacity_table_drift` gate 通过 `capacity_count_summary.case_counts` 携带 overall/top group case 分布。
- 测试覆盖 direct prior-max conflict、archive/live `v3_capacity_cases` 与 readiness group case counts。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.pytest-tmp tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 5 --detail-summary-by map_id
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --top 1 --detail-summary --detail-summary-top 3 --detail-summary-by map_id
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --folds 5 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_formal_value_sampler_holdout.py --posterior-trials 64 --folds 5 --format summary
```

结果：

```text
focused tests:
41 passed

main archive prior_stress_detail_summary:
rows=94
capacity_cases=target_lower_bound_truth_above_prior:31,direct_prior_max_conflict:29,no_capacity_prior_max_case:26,target_above_prior_but_below_truth:10,truth_above_prior_without_count_target:8

reason=total_count_above_prior:
capacity_cases=direct_prior_max_conflict:15

map_id=2601:
rows=8
capacity_hits=16
capacity_cases=direct_prior_max_conflict:8

map_id=2501:
rows=10
capacity_hits=16
capacity_cases=direct_prior_max_conflict:6,target_lower_bound_truth_above_prior:4

activity cohort:
prior_stress_detail_summary rows=0
capacity_cases=-

readiness:
overall_status=not_ready
gate=prior_stress_capacity_table_drift status=blocked

formal/value sampler holdout:
overall_status=sample_limited
candidate_rows=0
```

结论：

- capacity blocker 已拆成两条可执行路线：
  - `direct_prior_max_conflict`：target/truth 同时高于 prior max 且 target 匹配 truth，优先查表容量或 prior max；
  - `target_lower_bound_truth_above_prior`：truth 高于 prior max 但 target 是下界，优先查 target completeness 与表容量。
- `2601` 是最干净的 direct conflict 热点，适合下一步追 BidMap/DropTable/session capacity 口径。
- `2501` 混合 direct conflict 与 lower-bound，不能用单一 sampler 处理。

## 2026-06-06 checkpoint：capacity table possible-max 审计

完成内容：

- 新增 `scripts/summarize_v3_capacity_table_audit.py`。
- 该脚本把 prior-stress capacity case rows 与 raw BidMap/Drop sampler 表侧容量合并审计：
  - BidMap `items_per_session_min/max`；
  - sampler pool count 与 sub-pool count；
  - DropEntry 最大 `n_max`；
  - `sampler_possible_item_count_max = items_per_session_max * max(n_max)`；
  - archive target/truth count 分布；
  - `table_possible_max_below_truth` 状态。
- 新增 `tests/test_summarize_v3_capacity_table_audit.py`，覆盖 direct conflict 的表侧 impossible 状态与 case filter。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.pytest-tmp tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --posterior-trials 64 --case direct_prior_max_conflict --top 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --posterior-trials 64 --case target_lower_bound_truth_above_prior --top 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --case direct_prior_max_conflict --top 8
```

结果：

```text
focused tests:
7 passed

direct_prior_max_conflict:
case=direct_prior_max_conflict groups=10
map_id=2601 status=table_possible_max_below_truth rows=8 table_impossible_rows=8 bidmap_items=22-44 sampler_possible_max=44 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=65
map_id=2501 status=table_possible_max_below_truth rows=6 table_impossible_rows=6 bidmap_items=22-44 sampler_possible_max=44 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=60
map_id=2506 status=table_possible_max_below_truth rows=4 table_impossible_rows=4 bidmap_items=22-44 sampler_possible_max=44 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=58

target_lower_bound_truth_above_prior:
case=target_lower_bound_truth_above_prior groups=10
map_id=2508 status=table_possible_max_below_truth rows=6 table_impossible_rows=6 bidmap_items=22-44 sampler_possible_max=44 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=64
map_id=2504 status=table_possible_max_below_truth rows=4 table_impossible_rows=4 bidmap_items=22-44 sampler_possible_max=44 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=64
map_id=2405 status=table_possible_max_below_truth rows=4 table_impossible_rows=4 bidmap_items=20-40 sampler_possible_max=40 sampler_max_count_per_draw=1 sampler_nmax_gt1=0 truth_count=max=60

activity cohort:
case=direct_prior_max_conflict groups=0
```

结论：

- 当前 direct conflict 不是 DropEntry `n_max>1` 造成的；top groups 的 `sampler_max_count_per_draw=1`。
- 在当前 raw table + sampler 语义下，`2601` 这类 settlement truth item count 高于 sampler possible max，是表容量/采样语义/settlement truth 口径冲突。
- 这进一步强化 `prior_stress_capacity_table_drift` blocker；不能把该问题交给 formal/value sampler 或 promotion holdout。

## 2026-06-06 checkpoint：raw settlement inventory 去重诊断

完成内容：

- `scripts/summarize_v3_capacity_table_audit.py` 新增 raw capture inventory diagnostics：
  - per-group raw capture file count；
  - settlement inventory state count；
  - latest inventory item/cell count；
  - `settlement_truth_from_fatbeans` truth count 与 latest inventory count 对齐；
  - detail row truth count 与 latest inventory count 对齐；
  - duplicate runtime id、duplicate `(runtime_id,item_id)`、duplicate item id；
  - latest message id、round 与 quality count 聚合。
- `tests/test_summarize_v3_capacity_table_audit.py` 新增 raw inventory diagnostic 单元测试，覆盖同款 item 多件但 runtime/pair 不重复的口径。
- 该诊断只服务 prior-stress capacity/table audit；不改变 v2 formal/live/UI 或正式出价。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.pytest-tmp tests\test_summarize_v3_capacity_table_audit.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case direct_prior_max_conflict --posterior-trials 64 --top 4
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case target_lower_bound_truth_above_prior --posterior-trials 64 --top 3
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.pytest-tmp tests\test_summarize_v3_capacity_table_audit.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
```

结果：

```text
capacity audit test:
3 passed

focused archive/live/readiness/formal-value tests:
48 passed

direct_prior_max_conflict:
case=direct_prior_max_conflict groups=10
map_id=2601 status=table_possible_max_below_truth rows=8 table_impossible_rows=8 bidmap_items=22-44 sampler_possible_max=44 raw_inventory=verified_latest_inventory raw_files=4 raw_states=max=1.0 raw_latest_count=max=65.0 raw_truth_match_rows=8/8 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0 raw_dup_item=max=12.0 raw_msg=0x002D:4
map_id=2501 status=table_possible_max_below_truth rows=6 table_impossible_rows=6 bidmap_items=22-44 sampler_possible_max=44 raw_inventory=verified_latest_inventory raw_files=2 raw_truth_match_rows=6/6 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0
map_id=2506 status=table_possible_max_below_truth rows=4 table_impossible_rows=4 bidmap_items=22-44 sampler_possible_max=44 raw_inventory=verified_latest_inventory raw_files=1 raw_truth_match_rows=4/4 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0

target_lower_bound_truth_above_prior:
map_id=2508 status=table_possible_max_below_truth rows=6 raw_inventory=verified_latest_inventory raw_truth_match_rows=6/6 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0
map_id=2504 status=table_possible_max_below_truth rows=4 raw_inventory=verified_latest_inventory raw_truth_match_rows=4/4 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0
map_id=2405 status=table_possible_max_below_truth rows=4 raw_inventory=verified_latest_inventory raw_truth_match_rows=4/4 raw_dup_runtime=max=0.0 raw_dup_pair=max=0.0

readiness:
overall_status=not_ready
gate=prior_stress_capacity_table_drift status=blocked
gate=formal_value_sampler_holdout status=blocked
gate=v2_archive_readiness status=pending
```

结论：

- `2601` direct conflict 的 4 个 raw capture 文件全部只有 1 个 latest settlement inventory state，`raw_truth_match_rows=8/8`，runtime id 与 `(runtime_id,item_id)` 均无重复。
- duplicate item id 只是同款物品多件；由于 runtime/pair 不重复，不能解释为 parser 重复。
- lower-bound top groups 也显示 latest inventory 与 archive truth 对齐，进一步排除 settlement inventory parser 作为主要原因。
- 下一步应继续确认 BidMap drop-ref / round-cap capacity 语义、DropEntry count 语义与 raw table/archive 样本版本；在解释前不调整 sampler、不推进 promotion。

## 2026-06-06 checkpoint：BidMap v300 column 与 drop-universe capacity 语义审计

完成内容：

- `scripts/summarize_v3_capacity_table_audit.py` 追加 audit-only 字段：
  - current raw BidMap column count；
  - current drop-ref column index；
  - raw drop-ref blob；
  - raw round-cap candidate min/max；
  - settlement truth 超过 round-cap candidate 的行数；
  - latest settlement inventory item id 相对 reachable Drop universe 的缺口；
  - known temporary blue zodiac activity item id 与 non-zodiac missing item 分流。
- `docs/bid_map_schema.md` 从旧 21-column 说明更新为 current fileVersion 300 / 23-column 事实：
  - current `col[17]` 是 `drop_ref`；
  - current `col[16]` 是空占位；
  - current `col[14]` 是 round-cap candidate，但仍未确认为最终 settlement item-count cap。
- 未调整 formal/value sampler 参数，未改变 v2 formal/live/UI 或正式出价路径。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.pytest-tmp tests\test_summarize_v3_capacity_table_audit.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case direct_prior_max_conflict --posterior-trials 64 --top 4
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case target_lower_bound_truth_above_prior --posterior-trials 64 --top 4
```

结果摘录：

```text
capacity audit test:
3 passed

focused parser/archive/live/readiness/formal-value tests:
62 passed

raw table:
data/raw/fileVersion=300
data/raw/tables/fileVersion=300
BidMap rows=125 column_counts={23:125}

direct_prior_max_conflict:
map_id=2601 rows=8 bidmap_raw_cols=23 drop_ref_col=17 bidmap_items=22-44 round_cap=60-60 table_impossible_rows=8 round_cap_impossible_rows=3 raw_missing_drop=max=7 raw_temp_zodiac=max=7 raw_non_zodiac_missing=max=0
map_id=2501 rows=6 bidmap_raw_cols=23 drop_ref_col=17 bidmap_items=22-44 round_cap=50-50 table_impossible_rows=6 round_cap_impossible_rows=5 raw_missing_drop=max=3 raw_temp_zodiac=max=3 raw_non_zodiac_missing=max=0
map_id=2506 rows=4 bidmap_raw_cols=23 drop_ref_col=17 bidmap_items=22-44 round_cap=50-50 table_impossible_rows=4 round_cap_impossible_rows=4 raw_missing_drop=max=1 raw_temp_zodiac=max=1 raw_non_zodiac_missing=max=0

target_lower_bound_truth_above_prior:
map_id=2508 rows=6 bidmap_raw_cols=23 drop_ref_col=17 bidmap_items=22-44 round_cap=50-50 table_impossible_rows=6 round_cap_impossible_rows=6 raw_missing_drop=max=8 raw_temp_zodiac=max=8 raw_non_zodiac_missing=max=0
map_id=2405 rows=4 bidmap_raw_cols=23 drop_ref_col=17 bidmap_items=20-40 round_cap=50-50 table_impossible_rows=4 round_cap_impossible_rows=4 raw_missing_drop=max=2 raw_temp_zodiac=max=2 raw_non_zodiac_missing=max=0
```

结论：

- blocker 不是 current parser 仍读旧 `BidMap.col[16]`：current raw v300 的 drop-ref 在 `col[17]`，parser 已按 23-column schema 读取。
- blocker 也不是 top prior-stressed slices 的 DropEntry 多件数遗漏：reachable Drop graph 的 leaf/container edges 当前 `n_max=1`，sampler theoretical max 仍等于 drop-ref max。
- latest settlement inventory 相对 Drop universe 的 item-id 缺口只落在已知 temporary blue zodiac activity id `1306003..1306014`；没有 non-zodiac missing item 信号。
- zodiac extras 与 `col[14]` round-cap candidate 能解释一部分语义差异，但不能完整解释真实 settlement item-count 超过 `drop_ref.items_max` / `round_cap` 的冲突。
- 下一步优先查 settlement inventory 是否存在额外展开/活动生成机制，以及 archive 样本与 raw table v300 的版本时序关系；在解释前继续禁止 sampler/promotion 调参绕过。

## 2026-06-06 checkpoint：zodiac residual gap 与 archive/table timing 审计

完成内容：

- `scripts/summarize_v3_capacity_table_audit.py` 新增 raw inventory residual gap 字段：
  - `raw_drop_ref_excess_item_count`；
  - `raw_drop_ref_excess_after_temp_zodiac_count`；
  - `raw_round_cap_excess_item_count`；
  - `raw_round_cap_excess_after_temp_zodiac_count`。
- `tests/test_summarize_v3_capacity_table_audit.py` 新增扣除 zodiac 后 residual gap 单元测试。
- 新增 `scripts/summarize_v3_archive_table_timing.py`，输出 raw `fileVersion`、filelist BidMap/Drop entry、raw file metadata、archive/activity capture time range 与 capture JSON version/hash key 探测。
- 新增 `tests/test_summarize_v3_archive_table_timing.py`。
- 未调整 formal/value sampler 参数，未改变 v2 formal/live/UI 或正式出价路径。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.pytest-tmp tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case direct_prior_max_conflict --posterior-trials 64 --top 4
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case target_lower_bound_truth_above_prior --posterior-trials 64 --top 4
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_archive_table_timing.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_archive_table_timing.py data\samples\fatbeans_activity_20260605_shipwreck
```

结果：

```text
focused tests:
5 passed

broader parser/archive/live/readiness/formal-value tests:
64 passed

direct_prior_max_conflict:
2601 raw_drop_excess_after_temp=max=20 raw_round_excess_after_temp=max=4
2501 raw_drop_excess_after_temp=max=13 raw_round_excess_after_temp=max=7
2506 raw_drop_excess_after_temp=max=13 raw_round_excess_after_temp=max=7

target_lower_bound_truth_above_prior:
2508 raw_drop_excess_after_temp=max=14 raw_round_excess_after_temp=max=8
2504 raw_drop_excess_after_temp=max=17 raw_round_excess_after_temp=max=11
2405 raw_drop_excess_after_temp=max=18 raw_round_excess_after_temp=max=8

all default archive sessions:
above_drop_sessions=196
above_drop_after_temp_sessions=172
above_round_sessions=81
above_round_after_temp_sessions=59

timing:
raw_file_version=300 raw_tables_file_version=300
filelist_header=Ver:300|FileCount:4299
default_capture_min=2026-05-27T22:13:58+08:00
default_capture_max=2026-06-05T23:25:48+08:00
activity_capture_min=2026-06-05T23:05:05+08:00
activity_capture_max=2026-06-05T23:56:58+08:00
capture_version_like_keys=-
parse_errors=0
```

结论：

- zodiac extras 不能作为 capacity gap 的完整解释；扣除后 top groups 仍明显超过 drop-ref max 与 round-cap candidate。
- capture JSON 未携带 table version/hash 字段；当前 table timing 只能作为弱证据，不能解除 raw table/archive version blocker。
- 下一步应查 settlement inventory 协议或额外生成/展开字段，继续保持 `prior_stress_capacity_table_drift` blocked。

## 2026-06-06 checkpoint：0x002D settlement payload slot/candidate 审计

完成内容：

- 新增 `scripts/summarize_v3_settlement_payload_audit.py`：
  - 直接读取 raw 0x002D frames；
  - 审计 state payload field counts；
  - 审计 payload `field[4]` inventory block 的 top-level slot count；
  - 统计 occupied slots、raw item candidates、duplicate `(runtime_id,item_id)`；
  - 对照 parser dedup 后 `inventory_items`；
  - 统计 full observed actions 是否镜像 final inventory。
- 新增 `tests/test_summarize_v3_settlement_payload_audit.py`，覆盖 slot/candidate/duplicate pair helper。
- 未调整 formal/value sampler 参数，未改变 v2 formal/live/UI 或正式出价路径。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_payload_audit.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_payload_audit.py --top 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_payload_audit.py data\samples\fatbeans_activity_20260605_shipwreck --top 8
```

结果：

```text
unit:
1 passed

broader parser/archive/live/readiness/formal-value tests:
65 passed

default archive:
files=441 settlement_rows=441
raw_candidate_match_rows=439
occupied_slot_match_rows=439
slot_counts=300:251,250:186,232:1,252:1,253:1,254:1
raw_candidate_delta=max=1
raw_dup_pair=max=1
full_observed_action_rows=18

2601:
files=22 inventory_count=max=65 slot_counts=300:22
raw_candidate_match_rows=22/22 occupied_slot_match_rows=22/22
full_actions=none:15,100100:4,100134:3

2501:
files=87 inventory_count=max=65 slot_counts=300:86,232:1
raw_candidate_match_rows=86/87 occupied_slot_match_rows=86/87
full_actions=none:85,100100:2

activity cohort:
files=15 settlement_rows=15
raw_candidate_match_rows=15
occupied_slot_match_rows=15
slot_counts=300:15
raw_candidate_delta=max=0
raw_dup_pair=max=0
```

结论：

- 0x002D payload `field[4]` 支持“archive truth 是最终 occupied settlement slots”，不是 parser 重复。
- slot_count 与 map family 相关：24xx 多为 250，25xx/26xx/252x 多为 300；这不是当前 `drop_ref.items_max`。
- 0x002D payload 尚未暴露 base Drop / activity overlay / extra generation source split，不能直接解除 capacity blocker。
- 下一步优先继续查 server generation/source 字段；若找不到，需要设计 shadow-only settlement occupancy count prior 候选，再经 archive/activity/live/readiness 验证。

## 2026-06-06 checkpoint：settlement occupancy count prior shadow 候选审计

完成内容：

- 新增 `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 以 final settlement inventory/0x002D payload 为事实口径；
  - 按 `map_id`、`map_prefix3` 或 `map_family` 聚合 observed inventory count；
  - 输出 known temporary blue zodiac 扣除后的 residual count；
  - 对照 current BidMap `items_per_session_max` 与 `col[14]` round-cap candidate；
  - 标记 `observed_exceeds_table_caps_shadow_only`、`missing_table_shadow_only` 与 `insufficient_samples_shadow_only`。
- 新增 `tests/test_summarize_v3_settlement_count_prior_candidates.py`，覆盖 residual gap、missing table 与 group-by 参数校验。
- `docs/PROJECT_STRUCTURE_V3.zh-CN.md` 新增脚本/测试条目，并记录 Codex 临时文件统一使用 `.tmp/codex/`、pytest 使用 `.tmp/codex/pytest`。
- 未生成 sampler 配置，未调整 formal/value sampler 参数，未改变 v2 formal/live/UI 或正式出价路径。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_candidates.py --top 10 --min-samples 10
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_candidates.py data\samples\fatbeans_activity_20260605_shipwreck --top 10 --min-samples 3
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_candidates.py --group-by map_prefix3 --top 12 --min-samples 10
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_candidates.py data\samples\fatbeans_activity_20260605_shipwreck --group-by map_prefix3 --top 8 --min-samples 3
```

结果：

```text
unit:
3 passed

broader parser/archive/live/readiness/formal-value tests:
68 passed

default archive:
files=441 settlement_rows=441 groups=21
inventory_count p50=41 p90=54 p95=57 max=66
non_temp_count max=64 temp_zodiac max=8
slot_counts=300:251,250:186,232:1,252:1,253:1,254:1
above_drop=196 above_drop_after_temp=172
above_round=81 above_round_after_temp=59
missing_table_rows=0 payload_mismatch_rows=2
candidate_statuses=observed_exceeds_table_caps_shadow_only:19,insufficient_samples_shadow_only:2

default map highlights:
2501 files=87 above_drop_after_temp=39/87 above_round_after_temp=19/87 non_temp_count max=62
2601 files=22 above_drop_after_temp=11/22 above_round_after_temp=1/22 non_temp_count max=64
2504 files=22 above_drop_after_temp=11/22 above_round_after_temp=6/22 non_temp_count max=61
2506 files=21 above_drop_after_temp=11/21 above_round_after_temp=6/21 non_temp_count max=59
2401 files=72 above_drop_after_temp=21/72 above_round_after_temp=3/72 non_temp_count max=54

default prefix highlights:
250 files=217 above_drop_after_temp=94/217 above_round_after_temp=42/217 non_temp_count max=62
240 files=169 above_drop_after_temp=56/169 above_round_after_temp=11/169 non_temp_count max=58
260 files=22 above_drop_after_temp=11/22 above_round_after_temp=1/22 non_temp_count max=64
241 files=19 above_drop_after_temp=6/19 above_round_after_temp=2/19 non_temp_count max=56
251 files=14 above_drop_after_temp=5/14 above_round_after_temp=3/14 non_temp_count max=60

activity cohort:
files=15 settlement_rows=15 slot_counts=300:15
inventory_count p50=51 p90=54 p95=54 max=67
temp_zodiac max=0 missing_table_rows=15 payload_mismatch_rows=0
candidate_statuses=missing_table_shadow_only:6
map_prefix3=252 files=15 status=missing_table_shadow_only maps=2521:5,2524:3,2529:3,2526:2,2522:1,2528:1
```

结论：

- final settlement occupancy count 可以作为下一步 shadow-only count prior 候选的事实分布来源，但目前只允许进入审计/候选，不进入 sampler cap 或 promotion。
- 默认 archive 的 24xx/25xx/2601 多数分片在扣除临时生肖后仍超过 current BidMap drop-ref max；该信号与前面的 capacity residual blocker 一致。
- 252x activity cohort 全部缺 current BidMap 表项，且无临时生肖；它应先作为 missing-table/activity cohort 单独处理，不得并入默认 count prior。
- formal/value sampler promotion、v2 archive 继续等待 capacity/table semantics 或 shadow-only count prior 的 archive/activity/live/readiness 验证。

## 2026-06-06 checkpoint：settlement count-prior shadow artifact 接入 archive/live/readiness

完成内容：

- 新增 `src/bidking_lab/inference/v3/settlement_count_prior.py`：
  - 定义 `SettlementCountPriorEntry` 与 `V3SettlementCountPriorReport`；
  - 输出 `v3_scp_*` flat fields；
  - 只按 exact `map_id` 或 `map_prefix3` 匹配，不做 `map_family` fallback；
  - `active=False`、`affects_bid=False`，不改变 posterior、formal/value sampler 或正式出价。
- `src/bidking_lab/inference/v3/pipeline.py` 接入 `settlement_count_prior` report，使 archive/live 共用同一 shadow pipeline 字段。
- `scripts/evaluate_fatbeans_v3_samples.py` 默认读取 `data/processed/v3_settlement_count_prior_shadow.json`，输出 `v3_scp_*` 并汇总 `v3_scp_ready_rows`、`candidate_rows`、`missing_table_rows`、`active_rows`。
- `src/bidking_lab/live/monitor.py` 默认读取同一 processed artifact，并在 `v3_posterior_shadow` 与 `model_eval` 输出关键 `v3_scp_*` 字段。
- `scripts/summarize_v3_promotion_readiness.py` 新增 `settlement_count_prior_shadow` gate：
  - fields 可见且 inactive 时为 `watch`；
  - 不替代、不降低 `prior_stress_capacity_table_drift` gate。
- 新增 `scripts/build_v3_settlement_count_prior_shadow.py`，生成 `data/processed/v3_settlement_count_prior_shadow.json`。
- 新增测试：
  - `tests/test_inference_v3_settlement_count_prior.py`；
  - `tests/test_build_v3_settlement_count_prior_shadow.py`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_summarize_v3_promotion_readiness.py tests\test_live_monitor.py
C:\Users\shenc\anaconda3\python.exe scripts\build_v3_settlement_count_prior_shadow.py
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
```

结果：

```text
targeted tests:
44 passed

focused parser/archive/live/readiness/formal-value tests:
72 passed

artifact:
entries=27 cohorts=2 affects_bid=False active=False
default_archive candidate_statuses:
observed_exceeds_table_caps_shadow_only=19
insufficient_samples_shadow_only=2
activity_20260605_shipwreck candidate_statuses:
missing_table_shadow_only=6

default archive evaluator:
windows=1577 ready=1560
v3_scp_ready_rows=1560
v3_scp_candidate_rows=1488
v3_scp_missing_table_rows=0
v3_scp_active_rows=0

activity evaluator:
windows=58 ready=58
posterior_ready=0
robust_activity_candidate=58
v3_scp_ready_rows=58
v3_scp_candidate_rows=0
v3_scp_missing_table_rows=58
v3_scp_active_rows=0

readiness:
overall_status=not_ready
gate=settlement_count_prior_shadow status=watch
gate=prior_stress_capacity_table_drift status=blocked
gate=formal_value_sampler_holdout status=blocked
gate=v2_archive_readiness status=pending
```

结论：

- settlement occupancy count prior 已经进入 archive/live/readiness 共同观测面，且 `active_rows=0`，不影响正式出价。
- default archive 中 count-prior shadow candidate 覆盖 1488/1560 ready windows；activity cohort 58/58 以 missing-table evidence 暴露，未混入 default 250x prior。
- readiness 能看见该 evidence，但 promotion 仍为 `not_ready`；capacity/table drift、formal baseline、formal/value sampler holdout 等 gate 继续阻塞。
- 下一步可以围绕 `v3_scp_*` 做 holdout/readiness 分片审计，评估它是否能作为后续 shadow-only formal/value sampler 的 count prior 输入；仍不得提升为 sampler cap。

## 2026-06-06 checkpoint：settlement count-prior session holdout 审计

完成内容：

- 新增 `scripts/summarize_v3_settlement_count_prior_holdout.py`：
  - 按 stable session fold 做 holdout；
  - 支持 `--group-by map_id|map_prefix3`；
  - 比较 current `BidMap.items_per_session_max`、raw round-cap candidate、train p95/max 与 validation settlement truth 的 coverage；
  - 输出 `watch_settlement_count_prior_candidate`、`blocked_low_sample`、`missing_table_shadow_only` 等 shadow-only 状态。
- 新增 `tests/test_summarize_v3_settlement_count_prior_holdout.py`：
  - 覆盖 p95 under-coverage blocker；
  - 覆盖 252x `missing_bidmap` 保持 shadow-only。
- 项目临时验证输出继续统一使用 `.tmp\codex\`；pytest 使用 `.tmp\codex\pytest`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_holdout.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_holdout.py --top 10 --min-train-sessions 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_holdout.py --group-by map_prefix3 --top 10 --min-train-sessions 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_holdout.py data\samples\fatbeans_activity_20260605_shipwreck --top 8 --min-train-sessions 2
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_holdout.py data\samples\fatbeans_activity_20260605_shipwreck --group-by map_prefix3 --top 8 --min-train-sessions 2
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
```

结果：

```text
targeted tests:
2 passed

focused parser/archive/live/readiness/formal-value tests:
74 passed

default map_id holdout:
sessions=441 groups=21 candidate_rows=389 sample_limited_rows=52 missing_table_rows=0
prior_coverage=0.609977 round_coverage=0.866213
holdout_p95_coverage=0.907455 holdout_max_coverage=0.948586
status_counts=blocked_low_sample:7,watch_settlement_count_prior_candidate:14

default map_prefix3 holdout:
sessions=441 groups=5 candidate_rows=441 sample_limited_rows=0 missing_table_rows=0
prior_coverage=0.609977 round_coverage=0.866213
holdout_p95_coverage=0.945578 holdout_max_coverage=0.986395
status_counts=watch_settlement_count_prior_candidate:5

activity map_id holdout:
sessions=15 groups=6 candidate_rows=0 missing_table_rows=15
holdout_p95_coverage=0.857143
status_counts=missing_table_shadow_only:6

activity map_prefix3 holdout:
sessions=15 groups=1 candidate_rows=0 missing_table_rows=15
holdout_p95_coverage=0.933333
status_counts=missing_table_shadow_only:1

readiness:
overall_status=not_ready
gate=settlement_count_prior_shadow status=watch
gate=prior_stress_capacity_table_drift status=blocked
gate=formal_value_sampler_holdout status=blocked
gate=v2_archive_readiness status=pending
```

结论：

- session holdout 支持 default current-table cohort 的 settlement count-prior shadow 候选，但 exact-map 仍有 7 个 group 样本不足。
- prefix 聚合能提升 sample-depth 与 coverage，但仍不能替代 BidMap 表版本、字段语义或活动 mapping 解释。
- 252x activity cohort 仍是 missing-table evidence；不得 fallback 到 250x default prior。
- 当前 checkpoint 不改变 formal/value sampler、不改变 posterior sampler cap、不改变正式出价；v3 promotion 与 v2 archive 继续 pending。

## 2026-06-06 checkpoint：settlement count-prior 到 formal/value stress 关联审计

完成内容：

- 新增 `scripts/summarize_v3_scp_formal_value_link.py`：
  - 以 `v3_scp_ready` 为 settlement count-prior evidence 分母；
  - 只在 `v3_post_ready + v3_fv_ready + truth` 的子集上计算 formal metrics；
  - 量化 `scp_candidate` 与 `value_floor_stress`、`capacity_cells_drift`、capacity cases、formal MAE/p90 coverage 的交集；
  - activity/no-posterior rows 保留为 missing-table evidence，不进入 formal metric 分母。
- 新增 `tests/test_summarize_v3_scp_formal_value_link.py`，覆盖：
  - `scp + value_floor` / `scp + capacity` overlap；
  - `missing_bidmap` 不进入 formal metrics。
- `scripts/summarize_v3_promotion_readiness.py` 新增 `settlement_count_formal_value_link` gate：
  - 如果 `scp_candidate` 不能桥接到 value-floor 且改善 formal shadow metrics，则 blocked；
  - 该 gate 不改变正式出价，只暴露 promotion blocker。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_formal_value_link.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_formal_value_link.py --posterior-trials 64 --top 10
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_formal_value_link.py --by v3_fv_stress_class --posterior-trials 64 --top 10
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_formal_value_link.py --by v3_scp_group --posterior-trials 64 --top 12
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_formal_value_link.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --top 10
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_summarize_v3_scp_formal_value_link.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
```

结果：

```text
targeted tests:
6 passed

focused parser/archive/live/readiness/formal-value tests:
76 passed

default scp/formal link:
scp_rows=1560 formal_rows=1560
scp_candidate_rows=1488
scp_candidate_formal_rows=1488
scp_candidate_value_floor_rows=8
scp_candidate_capacity_watch_rows=124
fv_value_floor_rows=13
fv_capacity_watch_rows=126
formal_mae=318635.858
fv_delta_mae=0.0
formal_below=0.51859
formal_p90_cover=0.750641

activity scp/formal link:
scp_rows=58
formal_rows=0
scp_candidate_rows=0
scp_missing_table_rows=58
status_counts=missing_table_shadow_only:1

readiness:
overall_status=not_ready
blocked_gates=11
gate=settlement_count_prior_shadow status=watch
gate=settlement_count_formal_value_link status=blocked
gate=prior_stress_capacity_table_drift status=blocked
gate=formal_value_sampler_holdout status=blocked
scp_value_link_rows=8
scp_capacity_link_rows=124
scp_value_link_delta=0.0
```

结论：

- `v3_scp_candidate` 已经能作为 archive/live/readiness 可观测 evidence，但尚未形成 formal/value sampler 的可用 value bridge。
- 现有 `v3_fv` 与 `v3_scp` 的交集太小，且 formal MAE delta 为 0；不得据此恢复 sampler tuning 或 promotion。
- 下一步应设计 shadow-only count->cells/value bridge：先解释 `scp + capacity_only` 如何转化为 cells/value distribution，再进入 holdout。
- v2 formal/live/UI 与正式出价路径未改；v3 promotion、v2 archive 继续 pending。

## 2026-06-06 checkpoint：settlement count-prior count->cells/value bridge 审计

完成内容：

- 新增 `scripts/summarize_v3_scp_count_value_bridge.py`：
  - 以 `v3_scp_ready` 为 evidence 分母；
  - 只在 posterior/truth metric-ready rows 上审计；
  - 量化 `scp_p95 > target_count`、truth/target/prior count gap、cells p90 undercoverage、formal p90 undercoverage；
  - 输出 `watch_count_cells_value_bridge`、`watch_count_cells_only_bridge`、`missing_table_shadow_only` 等状态。
- 新增 `tests/test_summarize_v3_scp_count_value_bridge.py`，覆盖：
  - count gap + cells/formal undercoverage 的 bridge candidate；
  - activity/missing-table 不进入 metric 分母。
- `scripts/summarize_v3_promotion_readiness.py` 新增 `settlement_count_cells_value_bridge` gate：
  - archive bridge candidate 存在时为 `watch`；
  - 明确 holdout 仍是后续 required step；
  - 不改变 posterior、formal/value sampler 或正式出价。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_count_value_bridge.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge.py --posterior-trials 64 --top 12
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge.py --by v3_fv_stress_class --posterior-trials 64 --top 10
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --top 8
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_count_value_bridge.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_summarize_v3_scp_formal_value_link.py tests\test_summarize_v3_scp_count_value_bridge.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
```

结果：

```text
targeted bridge tests:
2 passed

targeted bridge/readiness tests:
6 passed

focused parser/archive/live/readiness/formal-value tests:
78 passed

default bridge:
scp_rows=1560
metric_rows=1560
scp_candidate_rows=1488
scp_candidate_metric_rows=1488
scp_p95_above_target_rows=1276
truth_above_prior_rows=711
target_below_truth_rows=1225
cells_p90_under_rows=635
formal_p90_under_rows=389
count_cells_bridge_rows=516
count_value_bridge_rows=315
count_cells_value_bridge_rows=201
cells_per_item p50=2.658 p90=3.14 p95=3.34
formal_per_item p50=16850.545 p90=32231.194 p95=41419.737

bridge top groups:
2501 count_cells_value=54
2401 count_cells_value=29
2601 count_cells_value=26
2506 count_cells_value=19
2504 count_cells_value=15

by v3_fv_stress_class:
none count_cells_value=185
capacity_cells_drift count_cells_value=15
value_floor_stress count_cells_value=1

activity bridge:
scp_rows=58
metric_rows=0
missing_table_rows=58
status_counts=missing_table_shadow_only:6

readiness:
overall_status=not_ready
blocked_gates=11
gate=settlement_count_prior_shadow status=watch
gate=settlement_count_formal_value_link status=blocked
gate=settlement_count_cells_value_bridge status=watch
gate=formal_value_sampler_holdout status=blocked
scp_count_cells_value_bridge_rows=201
scp_count_cells_bridge_rows=516
scp_count_value_bridge_rows=315
```

结论：

- count->cells/value bridge 候选存在，且 2601/2506 等 prior-stressed slices 有明确 bridge rows；这为下一步 shadow-only sampler 设计提供了候选分母。
- 大多数 full bridge rows 当前 `v3_fv_stress_class=none`，说明现有 formal/value stress detector 不足以消费 `v3_scp` evidence。
- 当前 bridge 是 archive-only、truth-derived 审计；promotion 前必须做 session holdout/shadow sampler，不能直接把 per-item cells/value 统计写成 sampler 参数。
- v2 formal/live/UI 和正式出价未改；v3 promotion、v2 archive 继续 pending。

## 2026-06-06 checkpoint：settlement count-prior bridge session holdout

完成内容：

- 新增 `scripts/summarize_v3_scp_count_value_bridge_holdout.py`：
  - 按 session stable fold 做 holdout；
  - 训练折估计同 group truth `cells_per_item` 与 `formal_value_per_item`；
  - 验证折只在 `v3_scp_candidate` 且 `scp_p95 > target_count` 时应用 shadow floor；
  - 输出 candidate/apply/sample-limited rows、formal MAE delta、p90 coverage delta、over-rate、group hurt。
- 新增 `tests/test_summarize_v3_scp_count_value_bridge_holdout.py`：
  - 覆盖 train-only bridge floor；
  - 覆盖无 candidate/sample-limited 状态。
- `scripts/summarize_v3_promotion_readiness.py` 新增 `settlement_count_cells_value_bridge_holdout` gate：
  - holdout 失败时 blocked；
  - readiness summary 显示 `scp_bridge_holdout_delta` 与 `scp_bridge_holdout_over`。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_count_value_bridge_holdout.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --posterior-trials 64 --top 12
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --ratio-source bridge --posterior-trials 64 --top 12
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --top 8
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_summarize_v3_scp_formal_value_link.py tests\test_summarize_v3_scp_count_value_bridge.py tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
```

结果：

```text
targeted holdout tests:
2 passed

targeted holdout/readiness tests:
6 passed

focused parser/archive/live/readiness/formal-value tests:
80 passed

default ratio_source=all:
overall_status=blocked_holdout_hurt
candidate_rows=1276
applied_rows=1173
sample_limited_rows=59
candidate_delta_mae=50956.632
candidate_delta_p90=0.219096
candidate_over=0.712702
overall_delta_mae=38315.468
overall_delta_p90=0.164744
status_counts=blocked_holdout_hurt:18,blocked_holdout_over_risk:1,sample_limited:2

default ratio_source=bridge:
overall_status=blocked_holdout_hurt
candidate_rows=1276
applied_rows=1120
sample_limited_rows=122
candidate_delta_mae=53663.766
candidate_delta_p90=0.225
candidate_over=0.708036

activity:
overall_status=sample_limited
rows=0
candidate_rows=0
applied_rows=0

readiness:
overall_status=not_ready
blocked_gates=12
gate=settlement_count_cells_value_bridge status=watch
gate=settlement_count_cells_value_bridge_holdout status=blocked
gate=settlement_count_formal_value_link status=blocked
gate=formal_value_sampler_holdout status=blocked
scp_bridge_holdout_delta=50956.632
scp_bridge_holdout_over=0.712702
```

结论：

- naive count->cells/value bridge floor 被 session holdout 否掉：它能提升 p90 coverage，但 formal p50 MAE 与 over-rate 风险不可接受。
- `ratio_source=bridge` 仍然 blocked，说明需要 guard/redesign，而不是简单缩小训练分母。
- 2506 是后续 guarded bridge 的优先 slice，但当前 over-rate 仍超 guard，不能作为 promotion evidence。
- v2 formal/live/UI 和正式出价未改；v3 promotion、v2 archive 继续 pending。

## 2026-06-06 checkpoint：guarded settlement count->value bridge probe

本轮继续收口 `v3_scp` count->cells/value bridge blocker，保持 v2 formal/live/UI 与正式出价不变。

改动：

- `scripts/summarize_v3_scp_count_value_bridge_holdout.py`：
  - 新增 audit-only `--floor-mode total|extra`；
  - 新增 audit-only `--formal-lift-cap`，只 cap shadow formal p50/p90 floor 相对 baseline 的抬升；
  - summary 输出 `floor_mode` 与 `formal_lift_cap`。
- `tests/test_summarize_v3_scp_count_value_bridge_holdout.py`：
  - 覆盖 `floor_mode=extra` 只补 `scp_p95-target_count` count gap；
  - 覆盖 `formal_lift_cap` 限制 formal value lift。
- `DECISIONS_V3.md` 新增 D-v3-077；`OBSERVATIONS_V3.md` 新增 O-v3-082；`docs/PROJECT_STRUCTURE_V3.zh-CN.md` 更新脚本/测试职责。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --formal-lift-cap 5000 --posterior-trials 64 --top 6
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --formal-lift-cap 10000 --posterior-trials 64 --top 6
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --formal-lift-cap 15000 --posterior-trials 64 --top 6
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --formal-lift-cap 25000 --posterior-trials 64 --top 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --formal-lift-cap 50000 --posterior-trials 64 --top 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --floor-mode extra --posterior-trials 64 --top 6
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --floor-mode extra --formal-lift-cap 5000 --posterior-trials 64 --top 6
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py --ratio-source bridge --formal-lift-cap 5000 --posterior-trials 64 --top 6
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_count_value_bridge_holdout.py data\processed\fatbeans_v3_activity_evaluation.jsonl --formal-lift-cap 5000 --posterior-trials 64 --top 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
git -c safe.directory=C:/xiangmuyunxing/biancheng/2026/bidking-lab diff --check
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_summarize_v3_scp_formal_value_link.py tests\test_summarize_v3_scp_count_value_bridge.py tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
```

结果：

```text
targeted holdout/readiness tests:
8 passed

focused parser/archive/live/readiness/formal-value tests:
82 passed

diff --check:
passed

total floor + formal_lift_cap=5000:
overall_status=blocked_holdout_hurt
candidate_delta_mae=-288.656
candidate_delta_p90=0.00341
candidate_over=0.495311
applied_hurts=2507,2407,2409

total floor + formal_lift_cap=25000:
overall_status=blocked_holdout_hurt
candidate_delta_mae=-890.956
candidate_delta_p90=0.018755
candidate_over=0.522592
applied_hurts=2507,2410,2403,2407,2409

extra floor uncapped:
overall_status=blocked_holdout_hurt
candidate_delta_mae=344324.441
candidate_delta_p90=0.234182
candidate_over=0.873459

extra floor + formal_lift_cap=5000:
overall_status=blocked_holdout_hurt
candidate_delta_mae=-63.063
candidate_delta_p90=0.003287
candidate_over=0.497124
applied_hurts=2507,2407,2409

ratio_source=bridge + formal_lift_cap=5000:
overall_status=blocked_holdout_hurt
candidate_delta_mae=-368.818
candidate_delta_p90=0.003571
candidate_over=0.490179
applied_hurts=2507,2407,2409

activity + formal_lift_cap=5000:
overall_status=sample_limited
rows=0
candidate_rows=0
applied_rows=0

readiness default:
overall_status=not_ready
blocked_gates=12
settlement_count_cells_value_bridge_holdout=blocked
scp_bridge_holdout_delta=50956.632
scp_bridge_holdout_over=0.712702
```

结论：

- `formal_lift_cap` 能缓解 naive bridge 的 formal MAE hurt，但不能解除 applied hurt groups；仍只能作为 audit guard probe。
- `floor_mode=extra` uncapped 明显过冲；加低 cap 后仍 blocked。
- `ratio_source=bridge` 加 cap 仍 blocked，说明 blocker 不只是训练分母，而是 table/capacity/settlement item-count 语义未收口。
- 下一步优先解释 `BidMap` capacity、`DropEntry n_min/n_max`、raw 表版本与 settlement inventory item-count 上限冲突；formal/value sampler 参数调优继续暂停。

## 2026-06-06 checkpoint：BidMap/Drop capacity semantic probe

本轮继续审计 prior-stressed capacity/table blocker，保持 v2 formal/live/UI 与正式出价不变。

改动：

- `scripts/summarize_v3_capacity_table_audit.py` 增强 direct capacity conflict 输出：
  - raw BidMap `col[14]`/`col[16]`/`col[17]`；
  - flattened leaf `n_min/n_max` summary；
  - 0x002D inventory slot count、occupied slot count、raw candidate count；
  - raw candidate/occupied slot 对 latest inventory delta；
  - slot headroom、full observed action ids、public total-count values。
- `tests/test_summarize_v3_capacity_table_audit.py` 覆盖 payload slot/headroom、full mirror action 与 public count 聚合。
- `DECISIONS_V3.md` 新增 D-v3-078；`OBSERVATIONS_V3.md` 新增 O-v3-083；`docs/PROJECT_STRUCTURE_V3.zh-CN.md` 更新 capacity audit 描述。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_table_audit.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py --case direct_prior_max_conflict --posterior-trials 64 --top 12
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_capacity_table_audit.py data\samples\fatbeans_activity_20260605_shipwreck --case all --posterior-trials 64 --top 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_payload_audit.py --top 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_archive_table_timing.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_candidates.py --group-by map_id --top 8
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_settlement_count_prior_candidates.py data\samples\fatbeans_activity_20260605_shipwreck --group-by map_prefix3 --top 8
git -c safe.directory=C:/xiangmuyunxing/biancheng/2026/bidking-lab diff --check
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_summarize_v3_scp_formal_value_link.py tests\test_summarize_v3_scp_count_value_bridge.py tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
```

结果：

```text
capacity audit tests:
4 passed

focused parser/archive/live/readiness/formal-value tests:
82 passed

diff --check:
passed

direct_prior_max_conflict:
groups=10

2601:
raw_col16="[[]]"
raw_col17="[9999,2601,22,44]"
sampler_leaf_nmax=max=1
raw_slots=max=300
raw_latest_count=max=65
raw_candidate_delta=max=0
raw_occupied_delta=max=0
raw_drop_excess_after_temp=max=20

2501:
raw_col16="[[]]"
raw_col17="[9999,2501,22,44]"
sampler_leaf_nmax=max=1
raw_slots=max=300
raw_latest_count=max=60
raw_candidate_delta=max=0
raw_occupied_delta=max=0
raw_public_count=60:1

2506:
raw_col16="[[]]"
raw_col17="[9999,2506,22,44]"
sampler_leaf_nmax=max=1
raw_slots=max=300
raw_latest_count=max=58
raw_candidate_delta=max=0
raw_occupied_delta=max=0

payload audit:
files=441
raw_candidate_match_rows=439
occupied_slot_match_rows=439
slot_counts=300:251,250:186,232:1,252:1,253:1,254:1

settlement count prior candidates:
above_drop_after_temp=172
above_round_after_temp=59
payload_mismatch_rows=2

activity 252x:
table=missing_bidmap:15
inventory_count max=67
slots=300:15
payload_mismatch=0/15

table timing:
raw_file_version=300
raw_tables_file_version=300
filelist_header="Ver:300|FileCount:4299"
capture_version_like_keys=-

readiness:
overall_status=not_ready
blocked_gates=12
prior_stress_capacity_table_drift=blocked
settlement_count_cells_value_bridge_holdout=blocked
formal_value_sampler_holdout=blocked
```

结论：

- current raw v300 BidMap 中 `col[16]` 是空占位，drop-ref 在 `col[17]`；旧 `col[16]` 口径不能用于 current 表。
- direct conflict maps 的 flattened Drop leaf `n_max` 全为 1；`DropEntry n_min/n_max` 不能解释 final inventory count 超过 sampler possible max。
- 0x002D raw candidate/occupied slot 与 final inventory 基本匹配，direct conflict rows truth/latest inventory 全匹配；parser 重复不是主因。
- final inventory 远低于 250/300 slot capacity，说明 `items_per_session_max` 更像 sampler prior max，不是 final settlement inventory hard cap。
- 252x activity 仍是 missing table cohort；不能用 default 250x 表强行解释。
- 下一步应基于 settlement occupancy count prior 设计 shadow-only guard，或继续查额外生成/活动机制；formal/value sampler promotion 仍暂停。

## 2026-06-06 checkpoint：nested train-only guarded count->value bridge

本轮在不改 v2 formal/live/UI 与正式出价的前提下，把 settlement count->cells/value bridge 从手工 cap probe 收口为独立 nested train-only shadow holdout。

改动：

- 新增 `scripts/summarize_v3_scp_guarded_bridge_holdout.py`：
  - outer session folds 评估未见 holdout；
  - outer-train 内使用 salted inner session folds crossfit；
  - group 必须通过 aggregate、全部 inner fold、最低样本数与 zero train over-rate increase guard；
  - 未被 train guard 选中的 group 保持 baseline，不应用 bridge。
- readiness 新增 `settlement_count_guarded_bridge_holdout` 信息 gate；原始 bridge、formal value sampler 与 prior-stress blocker 不降级。
- 新增 guarded holdout 测试，并更新 v3 项目结构索引。
- Codex/pytest 临时输出统一保留在 `.tmp/codex/`，项目优化完成前不逐次清理。

关键验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_summarize_v3_promotion_readiness.py

C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_holdout.py --posterior-trials 64 --posterior-seed 0 --formal-lift-cap 10000
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_holdout.py --posterior-trials 64 --posterior-seed 1 --formal-lift-cap 10000
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_holdout.py --posterior-trials 256 --posterior-seed 0 --formal-lift-cap 10000
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_holdout.py --posterior-trials 256 --posterior-seed 1 --formal-lift-cap 10000
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_holdout.py --posterior-trials 256 --posterior-seed 7 --formal-lift-cap 10000
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_summarize_v3_scp_formal_value_link.py tests\test_summarize_v3_scp_count_value_bridge.py tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
git -c safe.directory=C:/xiangmuyunxing/biancheng/2026/bidking-lab diff --check
```

结果：

```text
targeted tests:
10 passed

focused parser/archive/live/readiness/formal-value tests:
84 passed

diff --check:
passed

64 trials / seed 0:
overall=watch
selected_groups=2506:3
applied_rows=20
delta_mae=-6000.0
applied_hurts=-

64 trials / seed 1:
overall=blocked
selected_groups=2501:1,2506:2
applied_rows=62
delta_mae=+378.95
applied_hurts=2501

256 trials / seeds 0,1,7:
overall=watch
selected_groups=2506:2
applied_rows=9
delta_mae=-4602.026,-5555.556,-3333.333
applied_hurts=-

readiness:
overall_status=not_ready
blocked_gates=12
settlement_count_guarded_bridge_holdout=watch
settlement_count_cells_value_bridge_holdout=blocked
formal_value_sampler_holdout=blocked
```

结论：

- nested guard 已把“全量 bridge 不可用”收缩为“2506 可继续 shadow 采样”的窄候选。
- 方向性已在 256-trial 多 seed 下稳定，但有效 outer holdout 只有 9 条；64-trial seed 仍会出现 2501 false selection。
- 当前距离 promotion 的主要差距是 2506 样本深度、posterior seed/trial 稳定性、live cohort 验证与 252x missing-table 覆盖，不是继续调正式 sampler 参数。
- v3 仍不得影响正式出价；v2 继续作为 formal/live/UI production baseline。

## 2026-06-06 checkpoint：guarded bridge trial/seed stability matrix

本轮继续推进 guarded count->value bridge 的 promotion 前验证，不改 v2 formal/live/UI、live decision 或正式出价。

改动：

- 新增 `scripts/summarize_v3_scp_guarded_bridge_stability.py`：
  - 对多个 posterior trial/seed 组合运行 guarded bridge holdout；
  - 汇总 `overall_status`、selected groups、applied rows、MAE delta、p90 delta、over-rate 与 applied hurts；
  - 默认 smoke 为 `64 trials x seeds 0/1`，用于快速暴露 seed instability；
  - promotion 前长跑可显式传 `--posterior-trials 256 --posterior-seed 0 --posterior-seed 1 --posterior-seed 7`；
  - per-run cache 放在 `.tmp/codex/v3_scp_guarded_bridge_stability`。
- 新增 `tests/test_summarize_v3_scp_guarded_bridge_stability.py`，覆盖 exact 2506 稳定、hurt run、low support 三类判定。
- `docs/PROJECT_STRUCTURE_V3.zh-CN.md` 更新脚本/测试索引与数量。
- `DECISIONS_V3.md` 新增 D-v3-080；`OBSERVATIONS_V3.md` 新增 O-v3-085。

验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_guarded_bridge_stability.py tests\test_summarize_v3_scp_guarded_bridge_holdout.py
C:\Users\shenc\anaconda3\python.exe -m py_compile scripts\summarize_v3_scp_guarded_bridge_stability.py scripts\summarize_v3_scp_guarded_bridge_holdout.py
git -c safe.directory=C:/xiangmuyunxing/biancheng/2026/bidking-lab diff --check
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_stability.py --formal-lift-cap 10000
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_summarize_v3_scp_formal_value_link.py tests\test_summarize_v3_scp_count_value_bridge.py tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_stability.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
```

结果：

```text
targeted tests:
5 passed

focused parser/archive/live/readiness/formal-value tests:
87 passed

diff --check:
passed

stability smoke:
overall_status=blocked_applied_hurt
reasons=applied_hurts_present,non_watch_run,selected_group_drift
runs=2
watch_runs=1
trials=64
seeds=0,1
stable_groups=2506
union_groups=2501,2506
min_applied=20

seed0:
status=watch
selected=2506
applied_rows=20
delta_mae=-6000.0
bridge_over=0.25

seed1:
status=blocked_holdout_hurt
selected=2501,2506
applied_rows=62
delta_mae=378.95
bridge_over=0.580645
applied_hurts=2501

cache rerun:
cache_hit=True
runtime约4s
```

限制：

- 256-trial seeds 0/1/7 矩阵初跑超过 300 秒，本轮未形成新的完整矩阵输出；O-v3-084 的单跑结果仍是高 trial 方向性证据。
- stability smoke 证明当前低 trial 配置不稳定；不能用 readiness 单 seed watch 解释为 promotion-ready。

结论：

- guarded bridge 的当前状态从“2506 可见候选”进一步收紧为“2506 候选必须通过 stability matrix 后才可讨论 sampler shadow design”。
- 下一步优先用 cache 长跑 256-trial 多 seed 矩阵，或增加 2506 live/archive support 后复跑；formal/value active path 继续暂停。

## 2026-06-06 checkpoint：multi-agent stability and activity mapping audit

本轮按 4-agent 分工推进 v3 promotion 前置证据，保持 v2 formal/live/UI 与正式出价不变。

子 agent 结果：

- Agent 1 / Stability Runner：
  - 完成 `256 trials x seeds 0/1/7` guarded bridge stability matrix；
  - 全部 run 为 `watch`，selected group 精确为 `2506`，无 applied hurts；
  - overall 仍为 `blocked_low_support`，因为 `min_applied=9 < min_required=20`。
- Agent 2 / Table Activity Semantics：
  - 确认 252x 是真实 missing-table：当前 raw v300 有 `2511-2520`，没有 `2521+`；
  - 当前 raw Drop 包含 `2520->2150` 链，与 grid_view v1.3.7 一致；
  - 252x settlement StockBoxes 与 final inventory 字段级一致，排除 parser duplication、full-action mirror、temp zodiac replacement。
- Agent 3 / Mechanism Synthetic Probe：
  - 源码/参考侧最强线索是 Drop leaf `n_max=1` 只是单次 leaf entry 数量，不是 final settlement inventory hard cap；
  - 252x 更像 activity/table-version/overlay 缺口；
  - 合成脚本可用于机制假设，但不能作为 promotion evidence。

改动：

- 新增 `scripts/summarize_v3_activity_mapping_likelihood.py`，比较 252x activity settlement 在 `252x->251x` 与 `252x->250x` 候选映射下的 quality likelihood。
- 新增 `tests/test_summarize_v3_activity_mapping_likelihood.py`。
- `DECISIONS_V3.md` 新增 D-v3-081、D-v3-082；`OBSERVATIONS_V3.md` 新增 O-v3-086、O-v3-087；项目结构索引更新。

关键验证：

```powershell
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 256 --posterior-seed 0 --posterior-seed 1 --posterior-seed 7 --formal-lift-cap 10000
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_activity_mapping_likelihood.py
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_activity_mapping_likelihood.py
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_summarize_v3_activity_mapping_likelihood.py tests\test_summarize_v3_scp_formal_value_link.py tests\test_summarize_v3_scp_count_value_bridge.py tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_stability.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
```

结果：

```text
256-trial stability:
overall_status=blocked_low_support
runs=3
watch_runs=3
stable_groups=2506
union_groups=2506
min_applied=9
min_required=20
applied_hurts=-

activity mapping:
files=15
winners=minus10:11,minus20:4
candidate_statuses=ok:30
minus10 ll_per_item avg=-1.676415
minus20 ll_per_item avg=-1.691183
missing_item_rate avg=0.0 for both schemes

new tests:
2 passed

focused parser/archive/live/readiness/formal-value tests:
89 passed

readiness:
overall_status=not_ready
blocked_gates=12
settlement_count_guarded_bridge_holdout=watch
settlement_count_cells_value_bridge_holdout=blocked
formal_value_sampler_holdout=blocked
```

结论：

- 2506 guarded bridge 已通过 high-trial seed stability 的方向性检查，但 sample depth 仍不足，不能 promotion。
- 252x activity 更偏向 `252x->251x` activity/up table 解释，但仍缺少 `2521+` 服务端映射强证据；继续 missing-table cohort。
- 下一步优先采集更多 2506 archive/live support，并继续查 252x activity overlay 或 table-version 强字段；formal/value active sampler 继续暂停。

## 2026-06-06 checkpoint：2506 support gap and item-level activity mapping

本轮继续按并行审计推进 v3 promotion 前置证据，不改 v2 formal/live/UI、readiness gate 或正式出价。

子 agent 结果：

- Support Gap Explorer：
  - 2506 default archive 并非总样本过少：21 sessions、71 metric rows、59 bridge candidate rows；
  - high-trial guard 只选择 outer folds 0 和 4，实际 applied rows 为 `3+6=9`；
  - 本地没有可直接纳入 default archive 的新增 2506 support；
  - 仅有 1 个 invalid parse_error 2506 样本可人工审查，不能直接计入 promotion support。
- Activity Mapping Evidence Explorer：
  - exact item likelihood 值得加入，能比较同一 item 在候选映射下的权重；
  - value/cell bucket 只是 projection diagnostics，不应作为定表或 promotion evidence；
  - 不应构造 naive combined score，避免 quality 与 item 双重计数。

改动：

- `scripts/summarize_v3_activity_mapping_likelihood.py` 新增 exact item-level likelihood 输出：
  - `item_log_likelihood`；
  - `item_log_likelihood_per_item`；
  - `best_item_scheme` / `best_item_margin_per_item`；
  - `item_winner_counts`；
  - zero/missing/low-probability item diagnostics。
- `tests/test_summarize_v3_activity_mapping_likelihood.py` 新增 quality tie 但 exact item 权重分出 winner 的覆盖。
- `DECISIONS_V3.md` 新增 D-v3-083、D-v3-084；`OBSERVATIONS_V3.md` 新增 O-v3-088、O-v3-089。

关键验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_activity_mapping_likelihood.py
C:\Users\shenc\anaconda3\python.exe -m py_compile scripts\summarize_v3_activity_mapping_likelihood.py
git -c safe.directory=C:/xiangmuyunxing/biancheng/2026/bidking-lab diff --check
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_activity_mapping_likelihood.py
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_other_tables.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_archive_table_timing.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_count_prior_holdout.py tests\test_summarize_v3_activity_mapping_likelihood.py tests\test_summarize_v3_scp_formal_value_link.py tests\test_summarize_v3_scp_count_value_bridge.py tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_stability.py tests\test_inference_v3_settlement_count_prior.py tests\test_build_v3_settlement_count_prior_shadow.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
```

结果：

```text
activity mapping tests:
3 passed

focused parser/archive/live/readiness/formal-value tests:
90 passed

activity mapping real run:
files=15
quality_winners=minus10:11,minus20:4
item_winners=minus10:11,minus20:4
candidate_statuses=ok:30
minus10 item_ll_per_item avg=-5.965943
minus20 item_ll_per_item avg=-5.981787
zero_item avg=0.0 for both schemes
missing_item_rate avg=0.0 for both schemes

2506 support gap:
canonical_sessions=21
metric_rows=71
bridge_candidate_rows=59
selected_folds=0,4
selected_fold_bridge_candidates=3+6
applied_rows=9
min_required=20
directly_addable_local_samples=0
manual_review_invalid_parse_error_candidates=1

readiness:
overall_status=not_ready
blocked_gates=12
settlement_count_guarded_bridge_holdout=watch
settlement_count_cells_value_bridge_holdout=blocked
formal_value_sampler_holdout=blocked
```

结论：

- 252x mapping 的 exact item evidence 与 quality evidence 同向，但仍只是 `252x->251x` 略优的语义线索，不足以定表或进入 default prior。
- 2506 的当前 promotion blocker 是 selected-fold support depth；下一步应采集 10-15 个真实 complete 2506 sessions，尤其补 Ethan/Aisha 2506，再复跑 high-trial stability。
- formal/value active sampler 继续暂停；v3 仍保持 shadow-only。

## 2026-06-06 checkpoint：readiness dependency lanes for parallel v3 work

本轮为后续多 agent 并行推进增加 readiness blocker dependency view，不改任何 gate 判定、不改 v2 formal/live/UI、不改正式出价。

改动：

- `scripts/summarize_v3_promotion_readiness.py` 新增 `gate_dependencies`：
  - `lane_status_counts`；
  - `blocked_or_pending_lanes`；
  - `blocked_or_pending_gates`；
  - `watch_gates`。
- summary 输出新增 `gate_dependency_lanes=...`。
- `tests/test_summarize_v3_promotion_readiness.py` 覆盖：
  - formal baseline / guarded bridge / v2 archive 的 lane 分类；
  - 252x activity candidate 进入 `table_activity_capacity`；
  - prior-stress capacity drift focus 保留 `detail_rows` 与 `capacity_flag_hits`。
- `DECISIONS_V3.md` 新增 D-v3-085；`OBSERVATIONS_V3.md` 新增 O-v3-090。

关键验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe -m py_compile scripts\summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format json
```

结果：

```text
readiness tests:
4 passed

readiness real run:
overall_status=not_ready
blocked_gates=12
gate_dependency_lanes=formal_value_shadow_sampler,profile_sample_depth,sampler_safety_holdout,settlement_bridge_support,table_activity_capacity,v2_archive_after_promotion

lane_status_counts:
archive_pipeline_quality pass=1 watch=1
table_activity_capacity blocked=2 watch=1
settlement_bridge_support blocked=1 watch=2
formal_value_shadow_sampler blocked=3
sampler_safety_holdout blocked=5 watch=2
profile_sample_depth blocked=1
v2_archive_after_promotion pending=1
```

结论：

- readiness dependency lanes 只作为调度/审计视图，不减少 `blocked_gates`，也不改变 promotion readiness。
- 下一步并行推进应按 lane 拆分：table/activity/capacity 审计、2506 settlement bridge support、formal/value shadow sampler 设计、sampler safety/profile depth 验证。
- formal/value active sampler 继续暂停；v3 promotion 和 v2 archive 仍未满足。

## 2026-06-06 checkpoint：scripted 2506 guarded support gap audit

本轮把 2506 selected-fold support gap 从手工记录固化为 guarded bridge 脚本输出，不改 v2 formal/live/UI、不改正式出价、不改变 readiness gate。

改动：

- `scripts/summarize_v3_scp_guarded_bridge_holdout.py` 新增：
  - `selected_group_fold_support`；
  - `selected_group_support`。
- `scripts/summarize_v3_scp_guarded_bridge_stability.py` 新增：
  - per-run selected support passthrough；
  - `selected_group_support_gap`；
  - summary 行 `support_gap=group:min_applied=.../required=.../gap=...`。
- `tests/test_summarize_v3_scp_guarded_bridge_holdout.py` 覆盖 selected fold support 明细。
- `tests/test_summarize_v3_scp_guarded_bridge_stability.py` 覆盖 low-support gap。
- `DECISIONS_V3.md` 新增 D-v3-086；`OBSERVATIONS_V3.md` 新增 O-v3-091。

关键验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_stability.py
C:\Users\shenc\anaconda3\python.exe -m py_compile scripts\summarize_v3_scp_guarded_bridge_holdout.py scripts\summarize_v3_scp_guarded_bridge_stability.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --no-cache
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 256 --posterior-seed 0 --posterior-seed 1 --posterior-seed 7
```

结果：

```text
guarded bridge tests:
5 passed

64-trial seed0 no-cache:
overall_status=watch
support_gap=2506:min_applied=20/required=20/gap=0
fold0 sessions=1 metric_rows=3 candidate_rows=3 applied_rows=3
fold3 sessions=4 metric_rows=11 candidate_rows=11 applied_rows=11
fold4 sessions=3 metric_rows=9 candidate_rows=6 applied_rows=6

256-trial seeds 0/1/7 cached:
overall_status=blocked_low_support
runs=3
watch_runs=3
stable_groups=2506
union_groups=2506
min_applied=9
min_required=20
support_gap=2506:min_applied=9/required=20/gap=11
```

结论：

- 2506 support blocker 现在可由脚本复核，下一步采集真实 complete 2506 sessions 后直接用同一 stability matrix 验证 gap 是否关闭。
- 64 单 seed support 达标不改变 promotion 边界；high-trial 多 seed仍是 `blocked_low_support`。
- formal/value active sampler 继续暂停；v3 仍保持 shadow-only。

## 2026-06-06 checkpoint：prior-stress consistency bucket audit

本轮把 `prior_stressed` 的 cells/capacity/evidence 不一致拆成可复核的 consistency classes 与互斥 bucket，方便后续多 agent 按 blocker 类型并行推进。该改动只影响审计和 readiness 展示，不改 v2 formal/live/UI、不改正式出价、不改变 promotion gate。

改动：

- `scripts/summarize_v3_prior_robustness_audit.py` 新增：
  - row-level `consistency_classes`；
  - row-level `consistency_bucket`；
  - summary-level `consistency_class_counts` / `consistency_bucket_counts`；
  - bucket 覆盖 `hard_capacity_conflict`、`lower_bound_under_truth`、`evidence_floor_only`、`target_over_truth_risk`、`no_capacity_prior_conflict`。
- `scripts/summarize_v3_promotion_readiness.py` 在 `prior_stress_capacity_table_drift` gate 与 prior stress detail summary 中透传 bucket/class counts。
- `tests/test_summarize_v3_prior_robustness_audit.py` 覆盖 bucket 主类分流与 class counts。
- `tests/test_summarize_v3_promotion_readiness.py` 覆盖 readiness gate 中的 consistency counts。
- `DECISIONS_V3.md` 新增 D-v3-087；`OBSERVATIONS_V3.md` 新增 O-v3-092。

关键验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_prior_robustness_audit.py tests\test_summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe -m py_compile scripts\summarize_v3_prior_robustness_audit.py scripts\summarize_v3_promotion_readiness.py
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_prior_robustness_audit.py --detail-summary --format json
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format json
```

结果：

```text
prior/readiness tests:
6 passed

real prior-stress bucket split:
rows=94
hard_capacity_conflict=29
lower_bound_under_truth=39
evidence_floor_only=26
target_over_truth_risk=0

readiness real run:
overall_status=not_ready
blocked_gates=12
prior_stress_capacity_table_drift buckets=hard_capacity_conflict=29,lower_bound_under_truth=39,evidence_floor_only=26
```

结论：

- prior-stress blocker 不是单一 formal/value 问题：硬容量冲突、truth 超 prior 低界、floor evidence 不足必须分开处理。
- formal/value sampler 继续只允许 shadow-only value-floor candidate；不能用它吸收 capacity/cells drift。
- readiness 仍是 `not_ready`，`blocked_gates=12`；下一步优先沿 table/capacity/evidence 与 count->cells/value bridge 解释三类 bucket。

## 2026-06-06 checkpoint：bucketed capacity table audit

本轮把 capacity/table audit 接到上一轮的 `consistency_bucket`，用于按 blocker 类型直接复核 raw BidMap/Drop、sampler possible max 与 raw settlement inventory。该改动只增加 audit/readiness-adjacent diagnostics，不改 v2 formal/live/UI、不改正式出价、不改变 promotion gate。

改动：

- `scripts/summarize_v3_capacity_table_audit.py` 新增：
  - `--bucket` 过滤；
  - per-map `consistency_bucket_counts` / `consistency_class_counts`；
  - `bidmap_raw_col8` / `bidmap_v300_flag_a` 输出；
  - summary 行显示 bucket/class 与 col8。
- `tests/test_summarize_v3_capacity_table_audit.py` 覆盖 bucket 过滤、bucket/class counts 与 col8 输出。
- `docs/bid_map_schema.md` 补充 current v300 col[8] 全表分布。
- `DECISIONS_V3.md` 新增 D-v3-088；`OBSERVATIONS_V3.md` 新增 O-v3-093。

关键验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_table_audit.py
C:\Users\shenc\anaconda3\python.exe -m py_compile scripts\summarize_v3_capacity_table_audit.py
```

真实 64-trial bucketed audit：

```text
details=94 errors=0

hard_capacity_conflict:
groups=10 rows=29 table_impossible=29 round_impossible=16 verified_rows=29 col8_rows={'1': 29}

lower_bound_under_truth:
groups=11 rows=39 table_impossible=39 round_impossible=22 verified_rows=39 col8_rows={'1': 39}

evidence_floor_only:
groups=6 rows=26 table_impossible=0 round_impossible=0 verified_rows=26 col8_rows={'1': 26}
```

BidMap col[8] 全表复核：

```text
rows=125
col8_counts={'0': 20, '1': 105}
col8_zero_maps=2511-2520,4511-4520
```

结论：

- `hard_capacity_conflict` 与 `lower_bound_under_truth` 68 rows 全部为真实 table/sampler possible max gap，且 raw inventory 已 verified；继续查 table/session-capacity/settlement-source split。
- `evidence_floor_only` 26 rows table cap pass，下一步查 evidence/floor 编译口径。
- current col[16] 仍是 `[[]]` 空占位，drop-ref 在 col[17]；col[8] 不解释当前 94 行，但保留作后续 activity/overlay 表线索。
- formal/value active sampler 继续暂停；v3 promotion/v2 archive 不推进。

## 2026-06-06 checkpoint：evidence-floor-only component summary

本轮把 `evidence_floor_only` bucket 的 source/target/truth 形态固化到 prior robustness detail summary，继续保持 audit-only。该改动不接入 posterior sampler、不接入 formal/value sampler、不改变 readiness gate，也不触碰 v2 formal/live/UI 或正式出价。

改动：

- `scripts/summarize_v3_prior_robustness_audit.py` 新增：
  - `evidence_floor_only_summary`；
  - per-component `component_issue_counts`；
  - floor-only subset 的 source counts、target/truth delta counts、evidence count summary。
- `tests/test_summarize_v3_prior_robustness_audit.py` 覆盖：
  - floor below truth；
  - exact matches truth；
  - q6/value target missing；
  - floor-only summary row count 与 evidence count summary。
- `DECISIONS_V3.md` 新增 D-v3-089；`OBSERVATIONS_V3.md` 新增 O-v3-094。

关键验证：

```powershell
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_prior_robustness_audit.py
C:\Users\shenc\anaconda3\python.exe -m py_compile scripts\summarize_v3_prior_robustness_audit.py
```

真实 64-trial evidence-floor summary：

```text
details=94 errors=0
bucket_counts=hard_capacity_conflict=29,lower_bound_under_truth=39,evidence_floor_only=26

evidence_floor_only rows=26
maps=2401:5,2406:5,2409:5,2404:4,2502:4,2402:3

component_issue_counts:
total_cells floor_below_truth=21 exact_matches_truth=5
total_value floor_below_truth=22 target_missing=4
q6_cells floor_below_truth=17 floor_matches_truth=5 target_missing=4
q6_value floor_below_truth=17 floor_matches_truth=5 target_missing=4
```

结论：

- `evidence_floor_only` 不是 table capacity blocker；它的主因是 cells/value floor 低界低于 final truth，以及 q6/value target missing。
- `2502` 这类 rows 已有 total cells exact matches truth，但 q6/value target 缺失，不能靠 BidMap/Drop cap 或 formal/value sampler 调参解决。
- floor source 优先查 `item_anchors` 与 `shape_anchors`；`numeric_constraints` 是 exact 入口，不是 floor 入口。
- 下一步应查 evidence compiler 的 anchor/floor source 与 summary-likelihood fallback；formal/value active sampler 继续暂停。

## 2026-06-06 checkpoint：formal/value mixed candidate guard

本轮把 formal/value sampler 的 candidate 边界从“包含 `value_floor_stress`”收紧为 pure `value_floor_stress`。同时带 `capacity_cells_drift` 或 `q6_cells_floor_stress` 的 rows 现在进入 `watch_mixed_value_floor_guarded`，只做 shadow diagnostics，不参与 candidate holdout，不改变正式出价。

改动：

- `src/bidking_lab/inference/v3/formal_value_sampler.py`：
  - `v3_fv_candidate` 排除 capacity/cells stress；
  - 新增 `v3_fv_mixed_value_floor_watch`；
  - mixed rows 保持 `source=baseline`、`active=False`、`affects_bid=False`。
- `scripts/summarize_v3_formal_value_sampler_holdout.py`：
  - holdout candidate 只接受 pure value-floor；
  - 输出 `mixed_value_floor_watch_rows`。
- `scripts/summarize_v3_promotion_readiness.py`：
  - formal/value sampler gate/result 暴露 `mixed_value_floor_watch_rows`。
- 新增/更新测试覆盖 mixed row 不应用 shadow floor、holdout 不把 mixed row 计为 candidate、readiness 输出 mixed watch 字段。

关键验证：

```powershell
pytest --basetemp=.tmp\codex\pytest tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_formal_value_sampler_holdout.py tests\test_summarize_v3_promotion_readiness.py tests\test_live_monitor.py tests\test_evaluate_fatbeans_v3_samples.py
python -m py_compile src\bidking_lab\inference\v3\formal_value_sampler.py scripts\summarize_v3_formal_value_sampler_holdout.py scripts\summarize_v3_promotion_readiness.py
git -c safe.directory=C:/xiangmuyunxing/biancheng/2026/bidking-lab diff --check
```

真实 64-trial 复核：

```text
formal/value archive:
  pure_candidates=12
  mixed_value_floor_watch=1
  watch_only_value_floor_candidate=12
  watch_mixed_value_floor_guarded=1

holdout:
  overall_status=sample_limited
  candidate_rows=0
  mixed_value_floor_watch_rows=1
  train_candidate_status_counts={"blocked_low_sample":414}

readiness:
  overall_status=not_ready
  blocked_gates=12
  formal_value_sampler_holdout.status=blocked
  formal_value_sampler_holdout.candidate_rows=0
  formal_value_sampler_holdout.mixed_value_floor_watch_rows=1
```

结论：

- 13 个 value-floor stress rows 中只有 12 个是 safe pure candidate；1 个 mixed row 必须先回到 cells/capacity/evidence blocker 语义层解释。
- formal/value sampler 仍是 shadow-only；active sampler 与 promotion readiness 继续暂停。
- 下一步继续查 evidence compiler floor source、q6/value target missing，以及 hard/lower-bound capacity conflict 的 table/session/source split。

## 2026-06-06 checkpoint：evidence-floor target-missing pattern summary

本轮把 `evidence_floor_only` bucket 的 component pattern 固化为 audit-only summary，继续只用于解释 evidence compiler blocker。该改动不接入 posterior sampler、不接入 formal/value sampler、不改变 readiness gate，也不触碰 v2 formal/live/UI 或正式出价。

改动：

- `scripts/summarize_v3_prior_robustness_audit.py`：
  - 新增 `target_missing_pattern_counts`；
  - 新增 `floor_below_truth_pattern_counts`；
  - 新增 `exact_with_target_missing_pattern_counts`；
  - summary 文本输出展示 evidence-floor-only pattern。
- `tests/test_summarize_v3_prior_robustness_audit.py` 覆盖 `total_cells exact + q6/value target missing` 形态。
- `DECISIONS_V3.md` 新增 D-v3-091 / D-v3-092；`OBSERVATIONS_V3.md` 新增 O-v3-096。

关键验证：

```powershell
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_prior_robustness_audit.py
python -m py_compile scripts\summarize_v3_prior_robustness_audit.py
python scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --detail-summary --format json
```

真实 64-trial pattern summary：

```text
evidence_floor_only rows=26

target_missing_pattern_counts:
  none=22
  q6_cells+total_value+q6_value=4

floor_below_truth_pattern_counts:
  total_cells+q6_cells+total_value+q6_value=16
  total_cells+total_value=5
  none=4
  q6_cells+total_value+q6_value=1

exact_with_target_missing_pattern_counts:
  none=21
  total_cells+q6_cells+total_value+q6_value=4
  total_cells=1
```

合成样本结论：

- 可以后续做一个 diagnostics-only synthetic settlement mechanism probe，用来 falsify 明显不可能的 settlement 假设。
- 该 probe 不能写入 promotion/readiness/v2 archive 输入，不能伪造 raw `0x002D` 或真实 capture/source/table evidence，缓存只放 `.tmp/codex/`。

结论：

- `evidence_floor_only` 需要继续拆成两条线：22 行 floor below truth 主体、4 行 `total_cells exact + q6/value target missing`。
- `2502` 形态不是 table capacity 问题，也不是 formal/value sampler 参数问题；下一步查 q6/value allocation target 缺失。
- hard/lower-bound capacity conflict 仍等待 table/session/source split 审计；promotion/readiness 继续不推进。

## 2026-06-06 checkpoint：capacity conflict source split summary

本轮把 hard/lower capacity conflict 的 source split 固化到 capacity table audit，继续保持 audit-only。该改动不接入 posterior sampler、不接入 formal/value sampler、不改变 readiness gate，也不触碰 v2 formal/live/UI 或正式出价。

改动：

- `scripts/summarize_v3_capacity_table_audit.py` 新增 `source_split_summary`：
  - map prefix3 / map family；
  - capture day；
  - total count target source；
  - target/truth delta 与 truth/prior max delta；
  - raw 0x002D message counts；
  - drop-ref / round-cap residual after temp zodiac；
  - non-zodiac drop-universe residual；
  - full observed action 与 public total count。
- summary 文本输出展示 source split 关键字段。
- `tests/test_summarize_v3_capacity_table_audit.py` 覆盖 source split 聚合、date token、0x002D message、drop/round residual 与 full action/public count。
- `DECISIONS_V3.md` 新增 D-v3-093；`OBSERVATIONS_V3.md` 新增 O-v3-097。

关键验证：

```powershell
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_table_audit.py
python -m py_compile scripts\summarize_v3_capacity_table_audit.py
python scripts\summarize_v3_capacity_table_audit.py --case all --bucket hard_capacity_conflict --format json
python scripts\summarize_v3_capacity_table_audit.py --case all --bucket lower_bound_under_truth --format json
```

真实 64-trial source split：

```text
hard_capacity_conflict:
  groups=10 rows=29 table_impossible_rows=29 round_impossible_rows=16
  drop_after_temp_positive_files=14
  round_after_temp_positive_files=6
  non_zodiac_missing_positive_files=0

lower_bound_under_truth:
  groups=11 rows=39 table_impossible_rows=39 round_impossible_rows=22
  drop_after_temp_positive_files=18
  round_after_temp_positive_files=6
  non_zodiac_missing_positive_files=0
```

结论：

- 当前 hard/lower conflict 的 final items 仍在 drop universe 内；不是非 drop-universe item 或临时生肖完全解释。
- drop-ref / round-cap residual after temp 仍存在，说明 blocker 仍在 session capacity、activity overlay 或 settlement expansion 机制层。
- 下一步可按 map family、target source、full observed action/public total count 分线审计；formal/value sampler 与 promotion readiness 继续暂停。

## 2026-06-06 checkpoint：q6/value target-missing attribution

本轮把 `evidence_floor_only` 中 target-missing rows 的 attribution 固化到 prior robustness detail summary，继续保持 audit-only。该改动不接入 posterior sampler、不接入 formal/value sampler、不改变 readiness gate，也不触碰 v2 formal/live/UI 或正式出价。

改动：

- `scripts/summarize_v3_prior_robustness_audit.py` 新增：
  - `target_missing_attribution_summary`；
  - target-missing rows 的 map/profile counts；
  - missing component pattern；
  - evidence count summary；
  - source counts；
  - 多标签 attribution counts。
- summary 文本输出展示 `evidence_target_missing_rows/maps/attribution`。
- `tests/test_summarize_v3_prior_robustness_audit.py` 覆盖 `total_cells exact + q6/value targets missing` 的 attribution。
- `DECISIONS_V3.md` 新增 D-v3-094；`OBSERVATIONS_V3.md` 新增 O-v3-098。

关键验证：

```powershell
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_prior_robustness_audit.py
python -m py_compile scripts\summarize_v3_prior_robustness_audit.py
python scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --detail-summary --detail-summary-top 20 --format summary
```

真实 64-trial attribution：

```text
evidence_target_missing_rows=4
evidence_target_missing_maps=2502:4

attribution_counts:
  item_anchors_present=4
  item_anchors_present_value_targets_missing=4
  numeric_constraints_present=4
  q6_and_value_targets_missing=4
  q6_cells_target_missing=4
  q6_value_target_missing=4
  shape_anchors_present=4
  shape_anchors_present_q6_cells_target_missing=4
  total_cells_exact_matches_truth=4
  total_cells_exact_q6_value_targets_missing=4
  total_value_target_missing=4
```

结论：

- 2502 target-missing rows 不是 evidence 缺失；numeric/item/shape anchors 都存在。
- evidence compiler 已能得到 total cells exact，但没有得到 q6 cells、total value、q6 value targets。
- 下一步应查 2502 evidence event target set 与 anchor payload，尤其是 shape anchors 是否缺 quality/value、item anchors 是否缺 value，以及 q6 quality floor 是否只产生 count。

## 2026-06-06 checkpoint：capacity residual mode classifier

本轮把 hard/lower capacity conflict 的 residual mode 固化到 capacity table audit，继续保持 audit-only。该改动不接入 posterior sampler、不接入 formal/value sampler、不改变 readiness gate，也不触碰 v2 formal/live/UI 或正式出价。

改动：

- `scripts/summarize_v3_capacity_table_audit.py` 新增 `residual_mode_summary`：
  - `within_drop_ref`；
  - `drop_ref_only_overflow`；
  - `round_cap_overflow`；
  - `drop_universe_gap`。
- 每个 residual mode 输出 file count、latest item count、drop-ref residual、round-cap residual、non-zodiac missing、0x002D message、full observed action 与 public total count。
- summary 文本输出展示 `residual_modes` 与 compact by-mode detail。
- `tests/test_summarize_v3_capacity_table_audit.py` 覆盖四种 residual mode，以及真实 audit group 的 drop-ref-only output。
- `DECISIONS_V3.md` 新增 D-v3-095；`OBSERVATIONS_V3.md` 新增 O-v3-099。

关键验证：

```powershell
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_table_audit.py
python -m py_compile scripts\summarize_v3_capacity_table_audit.py
python scripts\summarize_v3_capacity_table_audit.py --case all --bucket hard_capacity_conflict --format json
python scripts\summarize_v3_capacity_table_audit.py --case all --bucket lower_bound_under_truth --format json
```

真实 64-trial residual modes：

```text
hard_capacity_conflict:
  rows=29
  table_impossible_rows=29
  round_impossible_rows=16
  residual_modes=drop_ref_only_overflow=8,round_cap_overflow=6,within_drop_ref=1

lower_bound_under_truth:
  rows=39
  table_impossible_rows=39
  round_impossible_rows=22
  residual_modes=drop_ref_only_overflow=12,round_cap_overflow=6,within_drop_ref=2
```

结论：

- hard/lower conflict 中 `drop_ref_only_overflow` 多于 `round_cap_overflow`，且 `drop_universe_gap=0`。
- 下一步优先解释 `BidMap col[17] max` / session-cap 与 final settlement count 的语义差异；round-cap overflow 子集再查 settlement expansion 或 activity overlay。
- promotion/readiness 继续不推进，formal/value sampler 继续 shadow-only。

## 2026-06-06 checkpoint：target-missing event audit

本轮新增独立 target-missing event audit，用于回放 prior-stressed detail 中 target-missing rows 的 Fatbeans prebid prefix，并解释 2502 q6/value target 缺口。该改动保持 audit-only，不改变 v2 formal/live/UI、不改变正式出价、不接入 sampler 或 readiness gate。

改动：

- 新增 `scripts/summarize_v3_target_missing_event_audit.py`：
  - 复用 `evaluate_paths` 和 `summarize_prior_stress_details` 筛选 target-missing rows；
  - 对选中行重新解析 capture，按 `< bid_sort_id` 回放 prebid prefix；
  - 输出 event target counts、numeric target values、anchor source ids、payload completeness、constraint anchors 与 summary exact/floor；
  - 支持 `--map-id`、`--consistency-bucket`、`--sample-root`、`--format summary/json`。
- 新增 `tests/test_summarize_v3_target_missing_event_audit.py`：
  - 覆盖 disjoint shape + quality evidence 不会自动生成 q6/value target；
  - 覆盖从 prior-stress source row 到 prebid prefix replay 的端到端诊断。
- `DECISIONS_V3.md` 新增 D-v3-096；`OBSERVATIONS_V3.md` 新增 O-v3-100。

关键验证：

```powershell
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_target_missing_event_audit.py tests\test_summarize_v3_prior_robustness_audit.py
python -m py_compile scripts\summarize_v3_target_missing_event_audit.py scripts\summarize_v3_prior_robustness_audit.py
python scripts\summarize_v3_target_missing_event_audit.py --posterior-trials 64 --format summary
python scripts\summarize_v3_capacity_table_audit.py --case all --bucket hard_capacity_conflict --posterior-trials 64 --format summary
```

真实 64-trial target-missing event audit：

```text
selected_rows=4
audited_rows=4
errors=0
maps=2502:4
missing_patterns=q6_cells+total_value+q6_value:4
key_target_presence=session.total_count:0/4,session.total_cells:4/4,bucket.q6.count:0/4,bucket.q6.cells:0/4,bucket.q6.value:0/4
```

结论：

- 2502 target-missing rows 均有 `session.total_cells=156` exact，但没有任何 `bucket.q6.*` target。
- 当前 evidence 主要来自 Aisha q1-q5/category/shape reveal；shape/item anchors 有 cells/shape，但没有 q6/value payload，`known_value_floor=0`。
- capacity 复核确认 current BidMap 是 v300/23 列，`col[16]=[[]]`、drop ref 在 `col[17]`；Drop leaf `n_max=1`，settlement inventory 与 0x002D payload 基本匹配，remaining blocker 是 `col[17] max` / final settlement count 语义差异。
- 下一步先不要调 formal/value sampler 参数；应先为 q6/value allocation target 设计 shadow-only 诊断，或明确这些 rows 继续 out-of-scope，然后再恢复 promotion readiness 验证。

## 2026-06-06 checkpoint：q6 residual target candidate audit

本轮扩展 target-missing event audit，增加 q6 residual target candidate 诊断。该改动仍保持 audit-only，不改变 `compile_feasible_summary`、posterior、formal/value sampler、readiness gate、v2 formal/live/UI 或正式出价。

改动：

- `scripts/summarize_v3_target_missing_event_audit.py` 新增 `q6_residual_target_candidate`：
  - count/cells/value 分别输出 `status`、candidate value、session total exact、non-q6 exact sum、missing non-q6 qualities；
  - 只有 session total exact 与 q1-q5 exact 完整且 residual 非负时，才标记 `derived`；
  - 对真实 detail row 附加 q6 truth 与 truth delta，方便 archive 审计。
- summary 文本新增：
  - `q6_residual_patterns`；
  - `q6_residual_cells` status counts；
  - per-row compact `q6_residual=` 输出。
- `tests/test_summarize_v3_target_missing_event_audit.py` 覆盖：
  - 非 q6 exact 不完整时不派生；
  - q1-q5 count/cells/value 与 session total 完整时可派生 q6 residual exact；
  - Fatbeans prebid replay row 会保留 truth delta。
- `DECISIONS_V3.md` 新增 D-v3-097；`OBSERVATIONS_V3.md` 新增 O-v3-101。

关键验证：

```powershell
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_target_missing_event_audit.py tests\test_summarize_v3_prior_robustness_audit.py
pytest --basetemp=.tmp\codex\pytest tests\test_inference_v3_summary.py tests\test_inference_v3_posterior.py tests\test_inference_v3_formal_value_sampler.py tests\test_inference_v3_evidence_registry.py tests\test_summarize_v3_target_missing_event_audit.py tests\test_summarize_v3_prior_robustness_audit.py -q
python -m py_compile src\bidking_lab\inference\v3\summary.py src\bidking_lab\inference\v3\posterior.py src\bidking_lab\inference\v3\formal_value_sampler.py scripts\summarize_v3_target_missing_event_audit.py scripts\summarize_v3_prior_robustness_audit.py
python scripts\summarize_v3_target_missing_event_audit.py --posterior-trials 64 --format summary
```

真实 64-trial residual candidate：

```text
selected_rows=4
audited_rows=4
q6_residual_patterns=none:3,cells:1
q6_residual_cells=missing_non_q6_exact:3,derived:1

prebid_r4:
  cells=derived
  total_cells_exact=156
  non_q6_cells_exact_sum=134
  derived_q6_cells=22
  truth_delta=0
```

结论：

- 2502 r4 可以 shadow-only 派生 `q6_cells=22`，但 r1-r3 缺非 q6 cells exact，不能派生。
- 2502 四行均不能派生 q6 count 或 q6 value；value/formal-value sampler 仍不能用这些 rows 做 candidate。
- 下一步如果继续推进，应把 q6 cells residual candidate 设计成 shadow-only diagnostic/conditioning input，并继续保持 formal/value promotion blocked，直到 capacity 与 value evidence 都有真实 archive/live/holdout 支持。

## 2026-06-06 checkpoint：q6 residual target candidate 接入 v3 pipeline/evaluate

本轮把前一轮 target-missing audit 中确认的 q6 residual exact 候选提升为通用 v3 shadow pipeline 诊断。该改动仍然是 shadow-only/report-only，不写回 `compile_feasible_summary`，不改变 posterior、residual gate、formal/value sampler、readiness gate、v2 formal/live/UI 或正式出价。

改动：

- 新增 `src/bidking_lab/inference/v3/residual_targets.py`：
  - `assess_q6_residual_targets(summary)` 输出 q6 count/cells/value 三类 residual candidate status；
  - 仅在 summary feasible、session total exact 存在、q1-q5 exact 完整、residual 非负且不低于 q6 floor 时标记 `derived`；
  - `active=False`、`affects_bid=False` 固定为 shadow-only 边界。
- `src/bidking_lab/inference/v3/pipeline.py` 的 `V3ShadowPipelineReport` 增加 `residual_targets`，flat fields 使用 `v3_rtc_*` namespace。
- `scripts/evaluate_fatbeans_v3_samples.py` 在 no-state 与 normal prebid rows 都输出 `v3_rtc_*`，CSV fieldnames 与 summary 增加 `v3_rtc_candidate_rows`、`v3_rtc_active_rows`。
- tests 新增/更新：
  - `tests/test_inference_v3_residual_targets.py`
  - `tests/test_inference_v3_pipeline.py`
  - `tests/test_evaluate_fatbeans_v3_samples.py`
- `DECISIONS_V3.md` 新增 D-v3-098；`OBSERVATIONS_V3.md` 新增 O-v3-102。

关键验证：

```powershell
python -m py_compile src\bidking_lab\inference\v3\residual_targets.py src\bidking_lab\inference\v3\pipeline.py scripts\evaluate_fatbeans_v3_samples.py
pytest --basetemp=.tmp\codex\pytest tests\test_inference_v3_residual_targets.py tests\test_inference_v3_pipeline.py tests\test_evaluate_fatbeans_v3_samples.py -q
pytest --basetemp=.tmp\codex\pytest tests\test_inference_v3_residual_targets.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_inference_v3_summary.py tests\test_inference_v3_posterior.py tests\test_inference_v3_formal_value_sampler.py tests\test_summarize_v3_target_missing_event_audit.py -q
python scripts\evaluate_fatbeans_v3_samples.py data\samples\fatbeans\fatbeans_valid_aisha_2502_4rounds_2502_1295018709694048_0149.json --posterior-trials 64 --format summary
```

真实 2502 64-trial archive smoke：

```text
windows=4
ready=4
v3_rtc_candidate_rows=1
v3_rtc_active_rows=0

prebid_r1:
  candidate=False
  count_status=missing_total_exact
  cells_status=missing_non_q6_exact
  value_status=missing_total_exact

prebid_r4:
  candidate=True
  active=False
  affects_bid=False
  derived_fields=cells
  cells_status=derived
  cells_value=22
  truth_q6_cells=22
```

结论：

- 2502 r4 的 `q6_cells=22` 现在可在通用 archive evaluate 输出中被稳定观测，且仍不参与任何 sampler 或 bidding 行为。
- r1-r3 继续因为非 q6 cells exact 不完整而不能派生；count/value 继续缺少必要 exact 分区，不能派生。
- 这一步收口了 q6 cells residual diagnostic 的 pipeline 出口；下一步仍应先围绕 capacity/table 语义与 value evidence blocker 推进，再恢复 formal/value sampler promotion readiness。

## 2026-06-06 checkpoint：guarded settlement bridge stability 纳入 readiness blocker

本轮修正 promotion readiness 的 settlement bridge 证据出口：此前 `settlement_count_guarded_bridge_holdout` 只表达单 posterior seed 的 nested holdout 结果，summary 文本虽然提示“seed stability remain required”，但 readiness gates 没有独立承载 multi-seed 稳定性证据。现在新增独立 stability gate，使 seed-0 watch 不会被误读为 promotion 支持。

改动：

- `scripts/summarize_v3_promotion_readiness.py` 新增 gate：
  - `settlement_count_guarded_bridge_stability`
  - lane 归属 `settlement_bridge_support`
  - 没有 stability matrix 时固定 blocked，`overall_status=not_evaluated`
  - 传入 stability JSON 后，只有 `overall_status=watch` 才进入 watch；其余状态保持 blocked。
- readiness CLI 新增：
  - `--guarded-bridge-stability-json`
  - 用于消费 `scripts/summarize_v3_scp_guarded_bridge_stability.py --format json` 的结果。
- summary 文本新增：
  - `scp_guarded_stability`
  - `scp_guarded_stable_groups`
- `tests/test_summarize_v3_promotion_readiness.py` 覆盖：
  - 默认未传 stability matrix 时 gate blocked；
  - 传入 `blocked_applied_hurt` matrix 时 gate blocked，并保留 hurt group 证据。
- `DECISIONS_V3.md` 新增 D-v3-099；`OBSERVATIONS_V3.md` 新增 O-v3-103。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_promotion_readiness.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_promotion_readiness.py tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_stability.py -q
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_promotion_readiness.py tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_stability.py tests\test_summarize_v3_scp_count_value_bridge_holdout.py tests\test_summarize_v3_scp_count_value_bridge.py -q
python scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --posterior-seed 1 --format summary
python scripts\summarize_v3_promotion_readiness.py data\samples\fatbeans\fatbeans_valid_aisha_2502_4rounds_2502_1295018709694048_0149.json --posterior-trials 64 --guarded-bridge-stability-json .tmp\codex\v3_readiness\scp_guarded_stability_64_s0_s1.json --format summary
```

真实 64-trial guarded bridge stability：

```text
overall_status=blocked_applied_hurt
reasons=applied_hurts_present,non_watch_run,selected_group_drift
runs=2
watch_runs=1
required_groups=2506
stable_groups=2506
union_groups=2501,2506
min_applied=20
min_required=20
signatures=2501:1,2506:2=1;2506:3=1

seed=0:
  status=watch
  selected=2506
  applied_rows=20
  delta_mae=-6000.0
  bridge_over=0.25
  applied_hurts=-

seed=1:
  status=blocked_holdout_hurt
  selected=2501,2506
  applied_rows=62
  delta_mae=378.95
  bridge_over=0.580645
  applied_hurts=2501
```

结论：

- `2506` guarded bridge 的 seed-0 watch 不能作为 promotion 支持；seed-1 引入 `2501` 且 hurt，multi-seed matrix 当前是 blocked。
- readiness 现在能显式表达这个 blocker：无 matrix 为 `not_evaluated` blocked，传入真实 matrix 为 `blocked_applied_hurt` blocked。
- 本轮不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价；只是把 settlement bridge stability gate 前移到 readiness 证据链。

## 2026-06-06 checkpoint：guarded bridge stability support 诊断与 cache schema

本轮继续收口 guarded settlement bridge stability blocker。上一轮 readiness 已能接入 multi-seed matrix，但 stability summary 仍可能复用旧 cache，且当旧 run 缺少 `selected_group_support` 时，summary 会漏掉 seed drift 中的多组选入 support 明细。现在把 cache schema 与 support 明细固化到 stability 输出。

改动：

- `scripts/summarize_v3_scp_guarded_bridge_stability.py`：
  - 新增 `CACHE_SCHEMA_VERSION=2` 并纳入 cache key，避免旧结构缓存被误用；
  - `run_result` 写入 `cache_schema_version`；
  - 新增 `selected_group_support_summary`，聚合每个 selected group 的 run count、fold count、min/max applied rows、hurt run count、missing support runs；
  - `selected_group_support_gap` 只保留 support 不足或 support 缺失的 group；
  - 旧 cache / run 缺少多组选入 support 时标记 `selected_group_support_missing`，并返回 `blocked_missing_support`；
  - summary 文本新增 `selected_support=...`。
- `scripts/summarize_v3_promotion_readiness.py`：
  - `settlement_count_guarded_bridge_stability` gate 透传 `selected_group_support_summary`。
- tests 更新：
  - `tests/test_summarize_v3_scp_guarded_bridge_stability.py`
  - `tests/test_summarize_v3_promotion_readiness.py`
- `DECISIONS_V3.md` 新增 D-v3-100；`OBSERVATIONS_V3.md` 新增 O-v3-104。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_scp_guarded_bridge_stability.py scripts\summarize_v3_promotion_readiness.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_guarded_bridge_stability.py tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_summarize_v3_promotion_readiness.py -q
python scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --posterior-seed 1 --format summary
python scripts\summarize_v3_promotion_readiness.py data\samples\fatbeans\fatbeans_valid_aisha_2502_4rounds_2502_1295018709694048_0149.json --posterior-trials 64 --guarded-bridge-stability-json .tmp\codex\v3_readiness\scp_guarded_stability_64_s0_s1_schema2.json --format summary
```

真实 64-trial stability support：

```text
overall_status=blocked_applied_hurt
reasons=applied_hurts_present,non_watch_run,selected_group_drift
stable_groups=2506
union_groups=2501,2506

selected_support:
  2501: runs=1 folds=1 min_applied=53 max_applied=53 hurts=1 missing_support=0
  2506: runs=2 folds=5 min_applied=9 max_applied=20 hurts=0 missing_support=0

support_gap:
  2506 min_applied=9 required=20 gap=11
```

结论：

- seed drift 现在可直接归因：`2501` 是 hurt group，且不是 support 缺失误报；`2506` 虽是 stable intersection，但跨 seed applied support 不足。
- 当前 guarded bridge 仍不能进入 promotion 支持；下一步若继续这条线，应调整 guard/selection，避免 `2501` 进入，并提升 `2506` support 稳定性。
- 本轮仍不改变 sampler、不改变 readiness 放行条件、不改变 v2 formal/live/UI 或正式出价。

## 2026-06-06 checkpoint：guarded bridge train-guard metrics 解释 2501 seed drift

本轮继续解释 seed1 为什么会选入 `2501`。上一轮已经能看到 selected support 与 hurt，但还缺少“内层 train guard 当时为什么通过”的证据。现在把 selected group 的 train-guard metrics 从 guarded holdout 输出到 stability matrix。

改动：

- `scripts/summarize_v3_scp_guarded_bridge_holdout.py`：
  - 新增 `selected_group_guard_summary`；
  - 对每个外层 fold 中被选中的 group 记录：
    - `guard_status`
    - `guard_applied_sessions`
    - `guard_delta_formal_p50_mae`
    - `guard_delta_formal_p90_coverage`
    - `guard_bridge_formal_p50_over_rate`
    - `guard_inner_status_counts`
    - 对应外层 holdout support counts。
- `scripts/summarize_v3_scp_guarded_bridge_stability.py`：
  - cache schema 升到 `CACHE_SCHEMA_VERSION=3`；
  - 汇总 `selected_group_guard_summary`；
  - summary 文本新增 `selected_guard=...`。
- `scripts/summarize_v3_promotion_readiness.py`：
  - `settlement_count_guarded_bridge_stability` gate 透传 `selected_group_guard_summary`。
- tests 更新：
  - `tests/test_summarize_v3_scp_guarded_bridge_holdout.py`
  - `tests/test_summarize_v3_scp_guarded_bridge_stability.py`
  - `tests/test_summarize_v3_promotion_readiness.py`
- `DECISIONS_V3.md` 新增 D-v3-101；`OBSERVATIONS_V3.md` 新增 O-v3-105。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_scp_guarded_bridge_holdout.py scripts\summarize_v3_scp_guarded_bridge_stability.py scripts\summarize_v3_promotion_readiness.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_guarded_bridge_holdout.py tests\test_summarize_v3_scp_guarded_bridge_stability.py tests\test_summarize_v3_promotion_readiness.py -q
python scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --posterior-seed 1 --format summary
python scripts\summarize_v3_promotion_readiness.py data\samples\fatbeans\fatbeans_valid_aisha_2502_4rounds_2502_1295018709694048_0149.json --posterior-trials 64 --guarded-bridge-stability-json .tmp\codex\v3_readiness\scp_guarded_stability_64_s0_s1_schema3.json --format summary
```

真实 64-trial train guard 解释：

```text
selected_guard:
  2501:
    runs=1
    folds=1
    statuses=watch_train_guard=1
    min_guard_sessions=59
    max_guard_delta=-1707.317
    max_guard_over=0.414634

  2506:
    runs=2
    folds=5
    statuses=watch_train_guard=5
    min_guard_sessions=14
    max_guard_delta=-3387.097
    max_guard_over=0.370968

selected_support:
  2501:
    min_applied=53
    hurts=1

  2506:
    min_applied=9
    support_gap=11
```

结论：

- `2501` 不是误选或缺 support：它在内层 train guard 看起来安全，但外层 holdout 仍出现 over-risk/hurt。
- `2506` 的 train guard 选择更稳定，但外层最小 applied support 仍不足。
- 当前下一步应优先设计更严格的 train/holdout stability criterion 或 group exclusion diagnostics；不能把 seed0/inner-guard watch 当成 promotion 支持。

## 2026-06-06 checkpoint：guarded bridge selected-group instability 分类

本轮把 guarded settlement bridge 的 selected group 风险从人工解读转为机器可读分类。该改动仍保持 readiness/shadow-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_scp_guarded_bridge_stability.py` 新增 `selected_group_instability_summary`：
  - `blocked_train_holdout_instability`
  - `blocked_holdout_hurt`
  - `blocked_support_depth_gap`
  - `blocked_missing_support`
  - `watch_train_guard_stable`
  - `watch_support_only`
- summary 文本新增 `selected_instability=...`。
- `scripts/summarize_v3_promotion_readiness.py` 的 `settlement_count_guarded_bridge_stability` gate 透传该分类。
- tests 更新：
  - `tests/test_summarize_v3_scp_guarded_bridge_stability.py`
  - `tests/test_summarize_v3_promotion_readiness.py`

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_scp_guarded_bridge_stability.py scripts\summarize_v3_promotion_readiness.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_scp_guarded_bridge_stability.py tests\test_summarize_v3_promotion_readiness.py -q
python scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --posterior-seed 1 --format summary
python scripts\summarize_v3_promotion_readiness.py data\samples\fatbeans\fatbeans_valid_aisha_2502_4rounds_2502_1295018709694048_0149.json --posterior-trials 64 --guarded-bridge-stability-json .tmp\codex\v3_readiness\scp_guarded_stability_64_s0_s1_instability.json --format summary
```

真实 64-trial selected instability：

```text
selected_instability:
  2501:
    status=blocked_train_holdout_instability
    reason=train_guard_watch_but_holdout_hurt
    gap=0
    hurts=1
    watch_guard=1

  2506:
    status=blocked_support_depth_gap
    reason=min_applied_rows_below_required
    gap=11
    hurts=0
    watch_guard=5
```

结论：

- `2501` 下一步应查 train/holdout selection instability 或加入 explicit exclusion diagnostic。
- `2506` 下一步应优先补支持深度或调 stable support criterion；它当前不是 hurt group。
- readiness 仍 blocked，v3 promotion 仍不能推进，formal/value sampler 仍保持 shadow-only。

## 2026-06-06 checkpoint：capacity/table semantic status 收口

本轮继续推进 prior-stressed cells/capacity/evidence 一致性审计，把 capacity table audit 的长字段归纳成机器可读 `capacity_semantic_summary`。该改动仍是 v3 audit/readiness 解释，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_capacity_table_audit.py` 新增 `capacity_semantic_summary`：
  - `blocked_round_cap_overflow_after_temp`
  - `blocked_drop_ref_overflow_after_temp`
  - `blocked_drop_universe_gap_after_temp`
  - `watch_activity_extras_explain_drop_ref_gap`
  - `needs_raw_inventory_verification`
  - `pass_table_caps_cover_verified_inventory`
- summary 文本新增：
  - `semantic_status=...`
  - `semantic_blockers=...`
  - `semantic_findings=...`
- `tests/test_summarize_v3_capacity_table_audit.py` 覆盖 after-temp drop-ref blocker 与 activity-only watch 分类。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_capacity_table_audit.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_table_audit.py -q
python scripts\summarize_v3_capacity_table_audit.py --case direct_prior_max_conflict --bucket hard_capacity_conflict --posterior-trials 64 --top 8 --format summary
```

真实 direct/hard 输出要点：

```text
2601 semantic_status=blocked_round_cap_overflow_after_temp
2501 semantic_status=blocked_round_cap_overflow_after_temp
2506 semantic_status=blocked_round_cap_overflow_after_temp
2502 semantic_status=blocked_drop_ref_overflow_after_temp
2401 semantic_status=watch_activity_extras_explain_drop_ref_gap
```

共同 findings：

```text
raw_latest_inventory_matches_detail_truth
current_v300_drop_ref_col17
current_v300_col16_unused
drop_entry_nmax_not_multi_count_driver
raw_candidate_count_matches_parsed_inventory
occupied_slot_count_matches_parsed_inventory
drop_universe_covered_after_temp_zodiac
```

结论：

- 当前 blocker 已从“是不是 BidMap col[16] 或 DropEntry n_max 解释”推进到“server settlement expansion/session-cap semantics 或 table/version overlay 如何解释 after-temp final inventory count”。
- 2501/2506/2601 的 direct hard conflict 不能通过调 formal/value sampler 参数解决。
- 下一步应围绕 settlement generation/round-cap semantics 做 shadow-only 证据或合成/源码审计；promotion/readiness 仍保持 blocked。

## 2026-06-06 checkpoint：capacity semantic matrix 聚合

本轮在 per-map `capacity_semantic_summary` 之上新增 matrix 视图，按 evidence/source/action/public-total 组合拆开 prior-stressed capacity blocker。该改动仍是 v3 audit/readiness 解释，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_capacity_table_audit.py` 新增 `capacity_semantic_matrix`：
  - `consistency_bucket`
  - `residual_mode`
  - `map_family`
  - `total_count_source`
  - `full_action_signal`
  - `public_total_signal`
  - `capture_day`
- top-level JSON 增加合并后的 `semantic_matrix`。
- summary 输出新增 `semantic_matrix_all=...` 与 per-map `semantic_matrix=...`。
- matrix 的 `semantic_status_counts` 改为 cell-level status，避免 `within_drop_ref` 子集继承 map-level blocked。
- tests 更新 `tests/test_summarize_v3_capacity_table_audit.py`，覆盖 matrix key、global merge 与 activity-only watch cell。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_capacity_table_audit.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_table_audit.py -q
python scripts\summarize_v3_capacity_table_audit.py --case direct_prior_max_conflict --bucket hard_capacity_conflict --posterior-trials 64 --top 8 --format summary
python scripts\summarize_v3_capacity_table_audit.py --case all --bucket lower_bound_under_truth --posterior-trials 64 --top 8 --format summary
```

真实 hard matrix 要点：

```text
hard/round_cap_overflow/shipwreck/exact/no_full_action/has_public_total:
  rows=5 maps=2501 status=blocked_round_cap_overflow_after_temp

hard/round_cap_overflow/shipwreck/floor/has_full_action/no_public_total:
  rows=4 maps=2506 status=blocked_round_cap_overflow_after_temp

hard/drop_ref_only_overflow/hidden/exact/has_full_action/no_public_total:
  rows=3 maps=2601 status=blocked_drop_ref_overflow_after_temp
```

真实 lower matrix 要点：

```text
lower/drop_ref_only_overflow/villa/floor/no_full_action/no_public_total:
  rows=8 maps=2406:4,2401:3,2404:1 status=blocked_drop_ref_overflow_after_temp

lower/round_cap_overflow/shipwreck/floor/no_full_action/no_public_total:
  rows=6 maps=2508:5,2504:1 status=blocked_round_cap_overflow_after_temp

within_drop_ref cells:
  status=watch_activity_extras_explain_drop_ref_gap
```

结论：

- hard bucket 的 highest-signal cells 分别指向 public-total exact、full-action floor、hidden-map action evidence，不应合并成单一 capacity 修正。
- lower bucket 主要是 floor/no-action/no-public 的 drop-ref/round-cap overflow，应优先查 target completeness 与 settlement expansion 分离。
- 下一步可以按 matrix cell 设计更窄的 shadow-only source/expansion diagnostic；formal/value sampler 参数调优继续暂停。

## 2026-06-06 checkpoint：capacity source/expansion file-level 下钻

本轮新增 file-level 下钻脚本，把 capacity semantic matrix cell 落到具体 capture、public total、full observed action 与 latest settlement inventory 的 delta。该改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- 新增 `scripts/summarize_v3_capacity_source_expansion_audit.py`：
  - 输入 prior-stress details 与 raw inventory diagnostics。
  - 按 semantic matrix cell 聚合。
  - 输出 `public_total_latest_delta`、`action_latest_delta`、drop/round after-temp excess。
  - 输出每个 cell 的 file-level examples。
- 新增 `tests/test_summarize_v3_capacity_source_expansion_audit.py`，覆盖 public-total cell 与 full-action cell 拆分。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_capacity_source_expansion_audit.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_source_expansion_audit.py -q
python scripts\summarize_v3_capacity_source_expansion_audit.py --case direct_prior_max_conflict --bucket hard_capacity_conflict --posterior-trials 64 --top 5 --format summary
python scripts\summarize_v3_capacity_source_expansion_audit.py --case all --bucket lower_bound_under_truth --posterior-trials 64 --top 5 --format summary
```

真实 hard cell 要点：

```text
2501 public-total cell:
  latest=60
  public=60
  public_delta=0
  round_after=7
  action_delta=-42

2506 full-action cell:
  latest=58
  full_actions=100134
  action_delta=0
  round_after=7

2601 full-action cells:
  action_delta=0
  drop_ref_only latest=55/60
  round_cap latest=65
```

真实 lower cell 要点：

```text
villa floor/no-public/no-full-action:
  rows=8
  action_delta avg=-43.25

shipwreck round-cap floor/no-public/no-full-action:
  rows=6
  latest avg=63
  round_after avg=8.33
  action_delta avg=-56.67
```

结论：

- hard bucket 的 public/action evidence 与 latest settlement inventory 一致，支持继续查 session-cap/settlement expansion 语义。
- lower bucket 多数缺 public/full-action，不能用 hard evidence 直接解释；下一步应拆 target completeness 与 expansion。
- formal/value sampler 参数调优继续暂停，promotion/readiness 仍 blocked。

## 2026-06-06 checkpoint：prior-stressed lower-bound target completeness 下钻

本轮增强 prior robustness detail summary，把 `lower_bound_under_truth` 从笼统 capacity bucket 拆成可行动的 target completeness 分支。该改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_prior_robustness_audit.py`：
  - 新增 `lower_bound_target_completeness_summary`。
  - 拆分 `floor_count_target_below_prior_and_truth`、`count_target_above_prior_but_below_truth`、`missing_count_target_truth_above_prior`。
  - summary 输出 lower-bound 的 capacity cases、count source、target-vs-truth delta、missing/floor-below patterns。
- `tests/test_summarize_v3_prior_robustness_audit.py` 新增三类 lower-bound target completeness 单测。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_prior_robustness_audit.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_prior_robustness_audit.py -q
python scripts\summarize_v3_prior_robustness_audit.py --posterior-trials 64 --detail-summary --detail-summary-top 8 --detail-summary-by consistency_bucket --format summary
```

真实 lower-bound 要点：

```text
lower_bound_rows=39
target completeness:
  floor_count_target_below_prior_and_truth=21
  count_target_above_prior_but_below_truth=10
  missing_count_target_truth_above_prior=8
count_sources=floor:31,none:8
target_truth_delta=n=31/avg=-25.968/p90=-9.0/max=-8.0
target_truth_counts=below=31/match=0/above=0
```

结论：

- lower bucket 的 31 条 count target 全部低于真实 settlement item count，且 8 条没有 count target。
- 这进一步支持先查 table/source/settlement expansion 语义，不恢复 formal/value sampler 参数调优。
- promotion/readiness 仍 blocked；下一步优先查 BidMap/Drop/session settlement expansion 语义与 raw 表版本。

## 2026-06-06 checkpoint：table timing smoke 覆盖 BidMap col[16]/col[17] 与 Drop leaf count range

本轮增强 archive/table timing 审计，让 raw table version smoke 同时回答字段口径与 DropEntry `n_min/n_max`。该改动仍是 v3 audit-only，不改变 parser 行为、不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_archive_table_timing.py`：
  - 输出 BidMap row/column counts、col[16] value counts、col[16]/col[17] drop-ref-like counts。
  - 输出 priority maps 的 col[14] round-cap candidate、col[16]、col[17] drop-ref pair。
  - 输出 Drop 全局 ref/leaf `n_min/n_max` range，以及 priority maps reachable leaf range。
- `tests/test_summarize_v3_archive_table_timing.py` 增加 23-column BidMap + two-level Drop pool 语义测试。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_archive_table_timing.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_archive_table_timing.py -q
python scripts\summarize_v3_archive_table_timing.py --format summary
```

真实 table smoke 要点：

```text
raw_file_version=300
raw_tables_file_version=300
bidmap_rows=125
bidmap_column_counts=23:125
bidmap_col16_values=[[]]:125
bidmap_col16_drop_ref_like=0
bidmap_col17_drop_ref_like=125
capture_version_like_keys=-
```

priority maps：

```text
2401/2404/2406: drop_ref_pair=20-40, round_caps=[50,50,50,50,50], col16=[[]]
2501/2506/2508: drop_ref_pair=22-44, round_caps=[50,50,50,50,50], col16=[[]]
2601: drop_ref_pair=22-44, round_caps=[60,60,60,60,60], col16=[[]]
all priority reachable Drop leaf_n_ranges=1-1 only, leaf_n_max_max=1
```

结论：

- 当前 blocker 不能再归因于误读 `BidMap.col[16]` 或 Drop leaf `n_max` 多件数。
- 本地 raw v300 与 capture window 兼容，但 capture 缺 version/hash-like 字段；不能证明每条 session 的服务端表版本。
- 下一步继续查 settlement expansion/session-capacity/server-side overlay，formal/value sampler 参数调优继续暂停。

## 2026-06-06 checkpoint：settlement residual-mode payload/evidence 下钻

本轮增强 settlement count prior candidate 审计，把 final inventory 相对 current table cap 的 residual 拆成可复核模式，并把 payload slot headroom、full observed action、public total evidence 合并到同一输出。该改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 新增 `--group-by residual_mode`。
  - residual mode 拆为 `within_drop_ref_after_temp`、`activity_extras_only_drop_ref_gap`、`drop_ref_only_overflow_after_temp`、`round_cap_overflow_after_temp`。
  - 输出 `slot_headroom_after_temp`、`full_action_rows`、`public_total_rows`、`public_total_match_rows` 与 `public_total_delta`。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 增加 residual-mode 覆盖。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 8 --format summary
```

真实 residual-mode 要点：

```text
residual_modes:
  within_drop_ref_after_temp=245
  activity_extras_only_drop_ref_gap=24
  drop_ref_only_overflow_after_temp=113
  round_cap_overflow_after_temp=59
payload_mismatch_rows=2/441
full_action_rows=18/441
public_total_rows=26/441
public_total_match_rows=26/26
public_total_delta=0 throughout when present
```

Over-cap rows：

```text
drop_ref_only_overflow_after_temp:
  files=113
  payload_mismatch=0/113
  public_total_match=11/11 when present

round_cap_overflow_after_temp:
  files=59
  payload_mismatch=0/59
  public_total_match=4/4 when present
```

结论：

- over-cap rows 不是 payload 解析膨胀；0x002D raw candidates/occupied slots 与 final inventory 对齐。
- public total 出现时也与 final inventory 对齐，但覆盖率不足，不能作为 promotion evidence。
- 当前剩余解释仍在 settlement expansion/session-capacity/server-side overlay/source semantics；formal/value sampler 参数调优继续暂停。

## 2026-06-06 checkpoint：settlement over-cap round/session 维度下钻

本轮继续增强 settlement count prior candidate 审计，加入 round/session 维度分组，判断 over-cap 是否只是 late-round、capture length 或 BidMap session length 造成。该改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 新增 `capture_rounds` 文件名解析。
  - 输出 `round_indices`、`capture_rounds`、`bidmap_rounds_total` 分布。
  - 新增 `--group-by round_index`、`--group-by capture_rounds`、`--group-by bidmap_rounds_total`。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 覆盖新增 group-by。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by round_index --min-samples 1 --top 8 --format summary
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by capture_rounds --min-samples 1 --top 8 --format summary
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by bidmap_rounds_total --min-samples 1 --top 8 --format summary
```

真实 round/session 要点：

```text
capture_rounds=1: above_drop_after_temp=12/27, above_round_after_temp=8/27
capture_rounds=2: above_drop_after_temp=15/48, above_round_after_temp=4/48
capture_rounds=3: above_drop_after_temp=33/115, above_round_after_temp=7/115
capture_rounds=4: above_drop_after_temp=72/146, above_round_after_temp=24/146
capture_rounds=5: above_drop_after_temp=40/105, above_round_after_temp=16/105

bidmap_rounds_total=30: above_drop_after_temp=110/253, above_round_after_temp=46/253
bidmap_rounds_total=25: above_drop_after_temp=62/188, above_round_after_temp=13/188
```

结论：

- over-cap 不是单纯 late-round effect；1/2-round captures 也存在 after-temp overflow。
- 30-round map 更重，但 25-round villa 同样存在 after-temp overflow。
- 下一步仍需查 server-side expansion/source semantics 或 per-session table-version 机制；formal/value sampler 参数调优继续暂停。

## 2026-06-06 checkpoint：settlement payload field-shape residual 下钻

本轮继续增强 settlement count prior candidate 审计，把 0x002D settlement payload 的 top-level field shape 与 semiknown child signatures 接入 residual-mode 分组。该改动仍是 v3 audit-only，不改变 parser、不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 输出 top-level `payload_field_shape`；
  - 输出 payload field 5/6/7/8 count、field20 presence/value；
  - 输出 field 5/6/7/8 child signature 聚合，用于按 residual mode 比较 semiknown payload blocks。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 增加 payload field shape、field20 value、child signature 覆盖。
- `tests/test_bid_map_table.py` 增加 current 23-column BidMap parser 直接测试，确认 `col[16]=[[]]` 不作为 drop-ref，`col[17]=[9999,map,min,max]` 才解析为 drop pool 与 item range。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_bid_map_table.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
```

真实 payload field-shape 要点：

```text
files=441 settlement_rows=441
payload_f5 max=4
payload_f6 max=5
payload_f7 max=2
payload_f8 max=5
payload_f20_rows=436/441

drop_ref_only_overflow_after_temp:
  files=113
  payload_mismatch=0/113
  payload_f20_rows=113/113
  payload_f5 max=4
  payload_f8 max=5

round_cap_overflow_after_temp:
  files=59
  payload_mismatch=0/59
  payload_f20_rows=59/59
  payload_f5 max=4
  payload_f8 max=5

within_drop_ref_after_temp:
  files=245
  payload_mismatch=2/245
  payload_f20_rows=240/245
  payload_f5 max=4
  payload_f8 max=5
```

解读：

- over-cap rows 与 within-cap rows 共享相同类型的 settlement payload top-level shape 与 field 5/8 child signatures；没有看到只在 over-cap rows 出现的额外 payload block。
- field20 在绝大多数 rows 出现，但 value 呈每局唯一/近唯一分布，不像稳定 source/expansion classifier。
- 这进一步排除 “over-cap 是特殊 payload 字段或 parser 膨胀” 的简单解释；当前 blocker 仍在 server-side settlement occupancy/source semantics 或 per-session table/version overlay。
- formal/value sampler 参数调优继续暂停，promotion/readiness 不能放宽。

## 2026-06-06 checkpoint：v303 activity overlay table timing smoke

本轮增强 archive/table timing 审计，让同一脚本可复核本机 v303 StreamingAssets 中 252x/452x activity map 的 BidMap/Drop presence。该改动仍是 v3 audit-only，不改变 parser 正式路径、不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_archive_table_timing.py`：
  - 新增 `activity_overlay` summary；
  - 输出 `2521-2530` / `4521-4530` BidMap present/missing、Drop present/missing 与 drop-ref pair 分布。
- `tests/test_summarize_v3_archive_table_timing.py` 增加 `2521` BidMap present but Drop missing 覆盖。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_archive_table_timing.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_archive_table_timing.py -q
python scripts\summarize_v3_archive_table_timing.py data\samples\fatbeans_activity_20260605_shipwreck --raw-root C:\xiangmuyunxing\steamapps\common\BidKing\BidKing_Data\StreamingAssets --format summary
```

真实 v303 smoke 要点：

```text
raw_file_version=303
filelist_header="Ver:303|FileCount:4550"
bidmap_rows=165
bidmap_col16_values=[[]]:165
bidmap_col17_drop_ref_like=165

priority maps:
  2401 col17=[9999,2401,20,40], round_caps=[50,50,50,50,50]
  2501 col17=[9999,2501,22,44], round_caps=[50,50,50,50,50]
  2506 col17=[9999,2506,22,44], round_caps=[50,50,50,50,50]
  2508 col17=[9999,2508,22,44], round_caps=[50,50,50,50,50]
  2601 col17=[9999,2601,22,44], round_caps=[60,60,60,60,60]

activity_range=2521-2530 bidmap_present=10 bidmap_missing=0 drop_present=0 drop_missing=10 drop_ref_pairs=22-44:10
activity_range=4521-4530 bidmap_present=10 bidmap_missing=0 drop_present=0 drop_missing=10 drop_ref_pairs=22-44:10

activity capture:
  capture_min=2026-06-05T23:05:05.4056732+08:00
  capture_max=2026-06-05T23:56:58.9596734+08:00
```

解读：

- 本机游戏源已从项目 raw v300 变为 v303，且 v303 BidMap 新增 `2521-2530` / `4521-4530`。
- v303 的 default priority maps `2401/2501/2506/2508/2601` drop-ref 与 round-cap 未相对 v300 变化，reachable Drop leaf `n_max` 仍为 1；因此 v303 不能直接解释 default 24xx/25xx/2601 after-temp over-cap。
- v303 中 252x/452x BidMap 存在但 Drop pool 仍缺失，说明 activity cohort 仍应保留为独立 missing-drop/activity overlay lane，不能 fallback 到 default 250x prior，也不能进入 promotion/readiness 分母。

## 2026-06-06 checkpoint：settlement slot/source shape residual 下钻

本轮继续增强 settlement raw payload 与 count-prior candidate 审计，把 field[4] inventory block 内每个 slot 的 occupied/empty shape、slot 顶层 int fields、item candidate path 接入 residual-mode 聚合。该改动仍是 v3 audit-only，不改变 parser 正式路径、不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_payload_audit.py`：
  - item candidate 增加递归 field path；
  - inventory block metrics 增加 occupied/empty slot field shapes；
  - inventory block metrics 增加 occupied/empty slot 顶层 int field 与 `field=value` 摘要；
  - summary 输出聚合后的 candidate path 与 slot/source shape。
- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - residual-mode/round/session 分组复用上述 slot/source metrics；
  - summary 在 payload field-shape 前输出 occupied/empty slot shape、slot int fields 与 candidate paths。
- `tests/test_summarize_v3_settlement_payload_audit.py` 增加 occupied/empty slot shape、slot int fields、candidate path 覆盖。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_payload_audit.py scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
```

真实 residual-mode smoke 要点：

```text
files=441 settlement_rows=441
slot_counts=300:251,250:186,232:1,252:1
candidate_paths=3:18310
residual_modes=within_drop_ref_after_temp:245,drop_ref_only_overflow_after_temp:113,round_cap_overflow_after_temp:59,activity_extras_only_drop_ref_gap:24
above_drop_after_temp=172
above_round_after_temp=59

drop_ref_only_overflow_after_temp:
  files=113
  payload_mismatch=0/113
  occupied_slot_shapes=1:0:i,2:2:b,3:2:b:5355,2:2:b,3:2:b:113
  empty_slot_shapes=1:0:i,2:2:b,3:2:b:25982
  occupied_slot_int_fields=1:5355
  empty_slot_int_fields=1:25982
  candidate_paths=3:5468

round_cap_overflow_after_temp:
  files=59
  payload_mismatch=0/59
  occupied_slot_shapes=1:0:i,2:2:b,3:2:b:3263,2:2:b,3:2:b:59
  empty_slot_shapes=1:0:i,2:2:b,3:2:b:13728
  occupied_slot_int_fields=1:3263
  empty_slot_int_fields=1:13728
  candidate_paths=3:3322

within_drop_ref_after_temp:
  files=245
  payload_mismatch=2/245
  occupied_slot_shapes=1:0:i,2:2:b,3:2:b:8210,2:2:b,3:2:b:244,1:0:i,2:2:b,2:0:i,3:2:b,3:2:b:1
  empty_slot_shapes=1:0:i,2:2:b,3:2:b:59232,:2,1:0:i,2:2:b,2:0:i:1,1:0:i,2:2:b,4:2:b,6:0:i,9:0:i,3:2:b,3:2:b,3:2:b:1
  occupied_slot_int_fields=1:8211,2:1
  empty_slot_int_fields=1:59234,2:1,6:1,9:1
  candidate_paths=3:8455
```

解读：

- 所有 residual groups 的 item candidates 都位于 slot child path `3`；over-cap groups 没有出现不同的 candidate path。
- over-cap groups 的 dominant occupied/empty slot shapes 与 within-cap groups 相同；slot 顶层 int field 主要是 `1`，更像 local index，不像 source/activity/expansion marker。
- 少量额外 int fields `2/6/9` 只出现在 within-cap/overall，不出现在 over-cap groups，不能解释 over-cap。
- 当前 field[4] slot/source shape 继续排除 parser 膨胀或 over-cap 专属 slot marker；blocker 仍在 server-side settlement occupancy/source semantics 或外部 overlay table 机制。
- formal/value sampler 参数调优继续暂停，readiness/promotion gate 不放宽。

## 2026-06-06 checkpoint：settlement outer wrapper residual 下钻

本轮继续收窄 settlement inventory expansion/source blocker，把 0x002D frame body 的 outer wrapper shape、field3/4/5 presence 与 field6 count 接入 settlement payload audit 和 count-prior residual summary。该改动仍是 v3 audit-only，不改变 parser 正式路径、不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_payload_audit.py`：
  - 新增 `_settlement_wrapper_metrics()`；
  - 输出 `settlement_outer_field_shape`、field3/4/5 presence/value tuple 与 field6 count；
  - payload summary 输出 outer wrapper shape、field3/4/5 rows 与 field6 numeric summary。
- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - residual-mode/round/session 分组同步输出 0x002D outer wrapper metrics。
- `tests/test_summarize_v3_settlement_payload_audit.py` 增加 wrapper metrics parser 覆盖。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 增加 wrapper metrics 聚合覆盖。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_payload_audit.py scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
python scripts\summarize_v3_settlement_payload_audit.py --top 4 --format summary
```

真实 residual-mode smoke 要点：

```text
overall:
  files=441 settlement_rows=441
  outer_shapes=1:0:ix1,2:2:bx1,5:0:ix1,6:2:bx4:193,1:0:ix1,2:2:bx1,6:2:bx4:109,1:0:ix1,2:2:bx1,3:0:ix1,4:0:ix1,5:0:ix1,6:2:bx4:80,1:0:ix1,2:2:bx1,3:0:ix1,4:0:ix1,6:2:bx4:53
  outer_f3_rows=134
  outer_f4_rows=134
  outer_f5_rows=276
  outer_f6=n=441/avg=3.998/p50=4.0/p90=4.0/p95=4.0/max=8.0

drop_ref_only_overflow_after_temp:
  files=113
  outer_f3_rows=34/113
  outer_f4_rows=34/113
  outer_f5_rows=70/113
  outer_f6=n=113/avg=4.009/p50=4.0/p90=4.0/p95=4.0/max=5.0

round_cap_overflow_after_temp:
  files=59
  outer_f3_rows=20/59
  outer_f4_rows=20/59
  outer_f5_rows=31/59
  outer_f6=n=59/avg=4.0/p50=4.0/p90=4.0/p95=4.0/max=4.0

within_drop_ref_after_temp:
  files=245
  outer_f3_rows=74/245
  outer_f4_rows=74/245
  outer_f5_rows=162/245
  outer_f6=n=245/avg=3.992/p50=4.0/p90=4.0/p95=4.0/max=8.0
```

解读：

- over-cap groups 与 within-cap group 共享同一组 dominant 0x002D outer wrapper shapes。
- field3/4 成对出现，且在 over-cap 与 within-cap 中都混合存在；field5/loss_units presence 也不是 over-cap 专属。
- field6 count 基本为 4，少量异常 max=5/8 分散在 drop-only/within-cap，不形成 round-cap overflow 或 drop-only overflow 专属 marker。
- 这继续排除“capacity 冲突来自 0x002D wrapper 专属 source/expansion marker”的简单解释；blocker 仍应放在 server-side settlement occupancy/source semantics、per-session table/version 或外部 overlay table 机制。
- formal/value sampler 参数调优继续暂停，readiness/promotion gate 不放宽。

## 2026-06-06 checkpoint：settlement capture/session cohort residual 下钻

本轮继续排查剩余 capacity blocker 中的 per-session table/version 或 capture cohort 假设，把 `capture_day`、`session_token_prefix6` 与 `session_token_prefix8` 接入 settlement count-prior residual summary。该改动仍是 v3 audit-only，不改变 parser 正式路径、不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 从 `state.capture_time` 或路径提取 `capture_day`；
  - 从 `state.session_id` 或文件名提取 session token，并输出 prefix6/prefix8；
  - 支持 `--group-by capture_day`、`--group-by session_token_prefix6`、`--group-by session_token_prefix8`；
  - overall 与 group rows 同步输出 capture/session cohort 分布。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 增加 capture/session cohort 聚合与 group-by 覆盖。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by capture_day --min-samples 1 --top 8 --format summary
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by session_token_prefix6 --min-samples 1 --top 8 --format summary
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by session_token_prefix8 --min-samples 1 --top 8 --format summary
```

真实 cohort smoke 要点：

```text
overall:
  files=441 settlement_rows=441
  capture_days=20260531:165,20260601:91,20260605:75,20260530:55,20260604:33,20260528:8,20260529:6,20260602:6
  session_p6=129501:369,127412:64,136751:8
  residual_modes=within_drop_ref_after_temp:245,drop_ref_only_overflow_after_temp:113,round_cap_overflow_after_temp:59,activity_extras_only_drop_ref_gap:24
  above_drop_after_temp=172
  above_round_after_temp=59

capture_day:
  20260531 files=165 above_drop_after=65 above_round_after=22 session_p6=129501:165
  20260601 files=91 above_drop_after=41 above_round_after=14 session_p6=129501:91
  20260605 files=75 above_drop_after=30 above_round_after=10 session_p6=129501:67,136751:8
  20260530 files=55 above_drop_after=19 above_round_after=6 session_p6=127412:48,129501:7
  20260604 files=33 above_drop_after=11 above_round_after=4 session_p6=129501:33

session_token_prefix6:
  129501 files=369 above_drop_after=146 above_round_after=49 capture_days=20260531:165,20260601:91,20260605:67,20260604:33,20260530:7,20260602:6
  127412 files=64 above_drop_after=21 above_round_after=9 capture_days=20260530:48,20260528:8,20260529:6,20260527:2
  136751 files=8 above_drop_after=5 above_round_after=1 capture_days=20260605:8
```

解读：

- after-temp over-cap 横跨多个 capture days 与 session token families；不是单一采集日、单一 session token family 或一次性 cohort switch。
- `136751` prefix 样本少且 overflow 较重，但只有 8 条 villa rows，不能解释 default 24xx/25xx/2601 的主要 blocker。
- `127412` 与 `129501` 都存在 drop/round overflow，继续削弱“一个表版本/会话族导致全部 over-cap”的简单解释。
- 该结果仍不能证明真实生成机制；它只排除 cohort/version 简化假设，blocker 继续集中在 server-side settlement occupancy/source semantics 或可复核外部 overlay table。
- formal/value sampler 参数调优继续暂停，readiness/promotion gate 不放宽。

## 2026-06-06 checkpoint：settlement Drop universe residual 下钻

本轮把 reachable Drop item-universe 覆盖接入 settlement count-prior residual summary，用同一个分组面板确认 over-cap 是否来自 current BidMap/Drop 之外的未知物品。该改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 复用 `flatten_pool()` 计算每个 map 当前 reachable Drop item universe；
  - 对每条 settlement row 输出 `missing_from_drop_universe_count`、`known_temp_zodiac_missing_from_drop_universe_count`、`non_zodiac_missing_from_drop_universe_count` 与 missing item examples；
  - overall/group summary 和 CLI summary 同步输出上述 coverage。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 补最小 Drop/Item fixture，覆盖“临时生肖缺口存在、非生肖缺口为 0”的聚合语义。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
```

真实 residual smoke 要点：

```text
overall:
  files=441 settlement_rows=441
  missing_drop=n=441/avg=1.658/p50=1.0/p90=4.0/p95=4.0/max=8.0
  non_zodiac_missing=n=441/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0
  missing_positive=337
  non_zodiac_positive=0

drop_ref_only_overflow_after_temp:
  files=113
  above_drop_after=113 above_round_after=0
  missing_drop=n=113/avg=1.761/p50=2.0/p90=4.0/p95=4.0/max=7.0
  non_zodiac_missing=n=113/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0

round_cap_overflow_after_temp:
  files=59
  above_drop_after=59 above_round_after=59
  missing_drop=n=59/avg=1.78/p50=1.0/p90=3.0/p95=4.0/max=8.0
  non_zodiac_missing=n=59/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0

activity_extras_only_drop_ref_gap:
  files=24
  above_drop_after=0 above_round_after=0
  missing_drop=n=24/avg=2.833/p50=3.0/p90=4.0/p95=4.0/max=6.0
  non_zodiac_missing=n=24/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0

within_drop_ref_after_temp:
  files=245
  above_drop_after=0 above_round_after=0
  missing_drop=n=245/avg=1.465/p50=1.0/p90=4.0/p95=4.0/max=5.0
  non_zodiac_missing=n=245/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0
```

解读：

- 所有 residual groups、capture days 与 session token prefixes 的 `non_zodiac_missing_from_drop_universe_count` 均为 0。
- 已知临时蓝色生肖 id 是当前唯一 item-universe gap；它解释 `activity_extras_only_drop_ref_gap` 和一部分 raw count gap，但不能解释 after-temp drop/round overflow。
- 剩余 blocker 不再是“有未知非生肖 item 从外部 overlay pool 混入”，而是 current reachable Drop universe 内部的 settlement 件数/占用扩展、session-capacity 或服务端 source semantics。
- 该证据仍不是 promotion evidence；它只是把后续调查从 item-universe 缺表转向 count/occupancy 生成机制。
- formal/value sampler 参数调优继续暂停，readiness/promotion gate 不放宽。

## 2026-06-06 checkpoint：settlement duplicate/unique-count residual 下钻

本轮继续排查“同一 Drop universe 内为什么会超过 current cap”，把 runtime/item duplicate 与 unique non-temp item count cap coverage 接入 settlement count-prior residual summary。该改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 输出 `unique_runtime_id_count`、`duplicate_runtime_id_count`、`unique_runtime_item_pair_count`、`duplicate_runtime_item_pair_count`；
  - 输出 `unique_item_id_count`、`duplicate_item_id_count`、`unique_non_temp_item_id_count`、`duplicate_non_temp_item_id_count`；
  - 额外计算 `unique_drop_ref_excess_after_temp_zodiac_count` 与 `unique_round_cap_excess_after_temp_zodiac_count`，用于判断按 unique item_id 去重后是否仍超 cap；
  - overall/group summary 与 CLI summary 同步输出高信号 duplicate/unique 字段。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 给 fixture 增加稳定 runtime id，并覆盖 unique/duplicate 与 unique cap excess 聚合。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by residual_mode --min-samples 1 --top 4 --format summary
```

真实 residual smoke 要点：

```text
overall:
  files=441 settlement_rows=441
  dup_runtime=n=441/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0
  dup_pair=n=441/avg=0.0/p50=0.0/p90=0.0/p95=0.0/max=0.0
  dup_item=n=441/avg=2.814/p50=2.0/p90=6.0/p95=7.0/max=12.0
  unique_non_temp=n=441/avg=37.15/p50=37.0/p90=48.0/p95=51.0/max=58.0
  unique_above_drop=109
  unique_above_round=21

drop_ref_only_overflow_after_temp:
  files=113
  count_above_drop=113 count_above_round=0
  unique_above_drop=51 unique_above_round=0
  unique_non_temp=n=113/avg=43.009/p50=43.0/p90=47.0/p95=48.0/max=53.0
  dup_item=n=113/avg=3.77/p50=4.0/p90=6.0/p95=7.0/max=12.0
  dup_runtime=max=0.0 dup_pair=max=0.0

round_cap_overflow_after_temp:
  files=59
  count_above_drop=59 count_above_round=59
  unique_above_drop=58 unique_above_round=21
  unique_non_temp=n=59/avg=49.831/p50=49.0/p90=54.0/p95=57.0/max=58.0
  dup_item=n=59/avg=4.831/p50=5.0/p90=7.0/p95=8.0/max=10.0
  dup_runtime=max=0.0 dup_pair=max=0.0

activity_extras_only_drop_ref_gap:
  files=24
  unique_above_drop=0 unique_above_round=0

within_drop_ref_after_temp:
  files=245
  unique_above_drop=0 unique_above_round=0
```

解读：

- `duplicate_runtime_id_count` 与 `duplicate_runtime_item_pair_count` 全局 max 都是 0，排除 parser/runtime 重复导致 count overflow。
- item_id 多实例化确实解释一部分 drop-only overflow：`drop_ref_only_overflow_after_temp` 从 113 条 count overflow 降为 51 条 unique non-temp overflow。
- 但 `round_cap_overflow_after_temp` 仍有 58/59 条 unique non-temp item count 超 drop-ref，21/59 条 unique non-temp item count 仍超 round cap。
- 因此 blocker 不能简化为“重复 item_id 实例导致统计口径偏高”；仍存在 unique item 层面的 over-cap，后续应查服务端 count/session-capacity、round/category 生成机制或 cap 字段语义。
- formal/value sampler 参数调优继续暂停，readiness/promotion gate 不放宽。

## 2026-06-06 checkpoint：settlement category/hint residual 下钻

本轮继续排查 unique item 层面的 over-cap 是否来自 BidMap `round_category_hints` 或 item primary-category 口径误读。改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 输出 `bidmap_round_category_hint_key` 与 `bidmap_round_category_hint_count`；
  - 支持 `--group-by bidmap_round_category_hint_key`；
  - 输出 settlement item primary-category distribution、unique non-temp category count、hinted/unhinted non-temp item count；
  - CLI summary 同步输出 `hint_keys`、`unique_cats`、`unique_hinted`、`unique_unhinted` 与 `unique_cat_counts`。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 给 fixture 增加 `round_category_hints` 与 item `tags`，覆盖 category/hint 聚合。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`、`DECISIONS_V3.md` 与 `OBSERVATIONS_V3.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py scripts\summarize_v3_settlement_payload_audit.py scripts\summarize_v3_capacity_table_audit.py scripts\summarize_v3_capacity_source_expansion_audit.py scripts\summarize_v3_promotion_readiness.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_capacity_source_expansion_audit.py tests\test_summarize_v3_promotion_readiness.py -q
```

真实 residual smoke 要点：

```text
overall:
  files=441 settlement_rows=441 hint_keys={'103': 441}
  unique_cats=n=441/avg=9.476/p50=10.0/p90=10.0/p95=10.0/max=10.0
  unique_hinted=n=441/avg=4.748/p50=4.0/p90=8.0/p95=9.0/max=14.0
  unique_unhinted=n=441/avg=32.401/p50=32.0/p90=42.0/p95=45.0/max=52.0

round_cap_overflow_after_temp:
  files=59 hint_keys={'103': 59}
  unique_cats=n=59/avg=9.797/p50=10.0/p90=10.0/p95=10.0/max=10.0
  unique_hinted=n=59/avg=6.051/p50=6.0/p90=8.0/p95=10.0/max=12.0
  unique_unhinted=n=59/avg=43.780/p50=43.0/p90=48.0/p95=51.0/max=52.0

within_drop_ref_after_temp:
  files=245 hint_keys={'103': 245}
  unique_cats=n=245/avg=9.265/p50=9.0/p90=10.0/p95=10.0/max=10.0
  unique_unhinted=n=245/avg=27.110/p50=27.0/p90=33.0/p95=34.0/max=39.0
```

解读：

- 所有真实 settlement rows 的 `bidmap_round_category_hint_key` 都是 `103`，不能区分 over-cap 与 within-cap。
- over-cap rows 的 unique non-temp item 覆盖接近全量 primary categories，且大量 item 落在 unhinted categories。
- 因此 `round_category_hints` 不能解释当前 unique item 层面的 after-temp over-cap；后续 blocker 仍是 settlement count/session-capacity、round/category 生成机制或 cap 字段语义。
- formal/value sampler 参数调优继续暂停，readiness/promotion gate 不放宽。

## 2026-06-06 checkpoint：settlement quality/cells residual 下钻

本轮继续排查 unique item 层面的 over-cap 是否能降级为 quality/cells 或 q6 value 问题。改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 输出 `unique_residual_mode`，区分 unique/instance drop/round overflow 与 within unique caps；
  - 支持 `--group-by unique_residual_mode`；
  - 输出 non-temp 与 unique non-temp 的 quality counts、quality cells、inventory cells、q6 item count 与 q6 cells；
  - `inventory_cells` 统一使用 settlement item cells，并在缺失时回退到 Item table shape cells。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 增加 item quality/shape fixture，并覆盖 quality/cells 聚合和 `unique_residual_mode` group-by。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`、`DECISIONS_V3.md` 与 `OBSERVATIONS_V3.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by unique_residual_mode --min-samples 1 --top 6 --format summary
```

真实 residual smoke 要点：

```text
unique_residual_modes:
  activity_extras_only_drop_ref_gap=201
  within_unique_caps_after_temp=68
  instance_drop_ref_only_overflow_after_temp=62
  unique_drop_ref_only_overflow_after_temp=51
  instance_round_cap_overflow_after_temp=38
  unique_round_cap_overflow_after_temp=21

unique_round_cap_overflow_after_temp:
  unique_non_temp=n=21/avg=53.143/p50=52.0/p90=57.0/p95=57.0/max=57.0
  unique_non_temp_cells=n=21/avg=152.143/p50=153.0/p90=175.0/p95=176.0/max=206.0
  unique_q6_count=n=21/avg=3.429/p50=3.0/p90=5.0/p95=6.0/max=8.0
  unique_q6_cells=n=21/avg=16.857/p50=16.0/p90=31.0/p95=34.0/max=37.0
  unique_quality_counts=q4:298,q2:241,q3:234,q5:170,q1:101,q6:72

within_unique_caps_after_temp:
  unique_non_temp_cells=n=68/avg=83.559/p50=84.0/p90=110.0/p95=115.0/max=126.0
  unique_q6_count=n=68/avg=1.985/p50=2.0/p90=4.0/p95=4.0/max=6.0
  unique_q6_cells=n=68/avg=7.279/p50=6.0/p90=15.0/p95=25.0/max=39.0
```

解读：

- unique item 层面的 round-cap blocker 从 59 条 count overflow 收窄到 21 条 unique overflow，但仍没有消失。
- `unique_round_cap_overflow_after_temp` 是 broad inventory/cells expansion，quality 分布不支持把它简化为单一 q6 value-floor 问题。
- q6 cells tail 与 within-cap rows 有重叠；capacity/cells watch 不能直接转为 formal value 上修。
- formal/value sampler 参数调优继续暂停，readiness/promotion gate 不放宽。

## 2026-06-06 checkpoint：BidMap raw capacity column coverage 下钻

本轮继续排查是否存在被遗漏的 BidMap raw numeric column 可以解释 settlement unique count/cells over-cap。改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- 新增 `scripts/summarize_v3_bidmap_raw_capacity_candidates.py`：
  - 复用 settlement count-prior audit rows；
  - 对 BidMap raw numeric atoms 做 coverage summary；
  - 默认输出语义 capacity columns：`rounds_total`、`round_caps_candidate`、`drop_ref`；
  - `--include-non-capacity` 可输出 count-sized 但非 capacity 的 id/category/hint/requirement 字段，防止误读。
- 新增 `tests/test_summarize_v3_bidmap_raw_capacity_candidates.py`，覆盖 `drop_ref` 中 `9999` sentinel 与 pool id 不会被误当作 cap。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`、`docs/bid_map_schema.md`、`DECISIONS_V3.md`、`OBSERVATIONS_V3.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_bidmap_raw_capacity_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_bidmap_raw_capacity_candidates.py -q
python scripts\summarize_v3_bidmap_raw_capacity_candidates.py --top 6 --format summary
python -m py_compile scripts\summarize_v3_bidmap_raw_capacity_candidates.py scripts\summarize_v3_settlement_count_prior_candidates.py scripts\summarize_v3_settlement_payload_audit.py scripts\summarize_v3_capacity_table_audit.py scripts\summarize_v3_capacity_source_expansion_audit.py scripts\summarize_v3_promotion_readiness.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_bidmap_raw_capacity_candidates.py tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_capacity_source_expansion_audit.py tests\test_summarize_v3_promotion_readiness.py -q
```

真实 residual smoke 要点：

```text
col=14 role=round_caps_candidate:
  candidate_values=50:419,60:22
  unique_count_cover=420/441 unique_count_over=21
  unique_count_over_modes=unique_round_cap_overflow_after_temp:21
  unique_cells_cover=7/441 unique_cells_over=434

col=17 role=drop_ref:
  candidate_values=44:253,40:188
  unique_count_cover=332/441 unique_count_over=109
  unique_cells_cover=0/441

non-capacity count-sized examples:
  category_id and round_category_hints cover item count numerically,
  but they are schema ids/hints and still fail many cells rows.
```

解读：

- 当前 BidMap raw schema 中没有可复核的 hidden final count/cells cap。
- `round_caps_candidate` 仍是 best-known count proxy，但失败 21 条 unique round overflow；它不能解释 cells。
- 其他数字列不能被当作 sampler cap 或 promotion evidence。
- formal/value sampler 参数调优继续暂停，readiness/promotion gate 不放宽。

## 2026-06-06 checkpoint：BidMap sub-pool / cohort residual 下钻

本轮继续排查 unique round overflow 是否来自未知母图、子池路由或单一 capture cohort。改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- `scripts/summarize_v3_settlement_count_prior_candidates.py`：
  - 输出 `bidmap_sub_pool_kind`：`leaf`、`weighted_parent`、`self_only`；
  - 输出 `bidmap_sub_pool_count` 与 `bidmap_sub_pool_weight_total`；
  - 支持 `--group-by bidmap_sub_pool_kind` 与 `--group-by bidmap_sub_pool_count`；
  - CLI summary 输出 sub-pool kind/count。
- `tests/test_summarize_v3_settlement_count_prior_candidates.py` 覆盖 sub-pool kind/count 聚合与 group-by。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`、`docs/bid_map_schema.md`、`DECISIONS_V3.md` 与 `OBSERVATIONS_V3.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py -q
python scripts\summarize_v3_settlement_count_prior_candidates.py --group-by bidmap_sub_pool_kind --min-samples 1 --top 6 --format summary
python -m py_compile scripts\summarize_v3_settlement_count_prior_candidates.py scripts\summarize_v3_bidmap_raw_capacity_candidates.py scripts\summarize_v3_settlement_payload_audit.py scripts\summarize_v3_capacity_table_audit.py scripts\summarize_v3_capacity_source_expansion_audit.py scripts\summarize_v3_promotion_readiness.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_count_prior_candidates.py tests\test_summarize_v3_bidmap_raw_capacity_candidates.py tests\test_summarize_v3_settlement_payload_audit.py tests\test_summarize_v3_capacity_table_audit.py tests\test_summarize_v3_capacity_source_expansion_audit.py tests\test_summarize_v3_promotion_readiness.py -q
```

真实 residual smoke 要点：

```text
leaf:
  files=260
  unique_round_cap_overflow_after_temp=14
  unique_drop_ref_only_overflow_after_temp=24
  instance_round_cap_overflow_after_temp=22

weighted_parent:
  files=159
  unique_round_cap_overflow_after_temp=7
  unique_drop_ref_only_overflow_after_temp=21
  instance_round_cap_overflow_after_temp=15

self_only:
  files=22
  unique_round_cap_overflow_after_temp=0
  unique_drop_ref_only_overflow_after_temp=6
  instance_round_cap_overflow_after_temp=1

map_family:
  shipwreck unique_round=19
  villa unique_round=2
  hidden unique_round=0
```

解读：

- unique round overflow 同时存在于 leaf 和 weighted_parent maps，不能归因于单一母图/子池路由错误。
- self-only 2601 没有 unique round overflow，因此不能解释 default 25xx/24xx 的 unique round blocker。
- 现有证据把下一步继续推向 map-family/session-capacity 或 server-side settlement expansion，而不是恢复 sampler 参数调优。
- formal/value sampler 参数调优继续暂停，readiness/promotion gate 不放宽。

## 2026-06-06 checkpoint：settlement source semantics / capacity blocker 收口

本轮把当前阶段目标收窄到 settlement over-cap / capacity blocker 收口。改动仍是 v3 audit-only，不改变 sampler、不改变 v2 formal/live/UI、不改变正式出价。

改动：

- 新增 `scripts/summarize_v3_settlement_source_semantics_audit.py`：
  - 复用 settlement count-prior audit 的 final inventory / Drop universe / BidMap cap 口径；
  - 遍历同一 capture 的全部 state，输出 message id、0x002D settlement state、0x0027 direct action、public total、full action 与 latest inventory delta；
  - 输出 `source_evidence_class` 与 `mechanism_class`，把 `public_total_matches_inventory`、`direct_action_matches_inventory`、`settlement_payload_verified_only` 区分开；
  - 输出 local raw/table version、filelist 中 `Tables/Activity.txt` 是否列出、local Activity table 是否存在。
- 新增 `tests/test_summarize_v3_settlement_source_semantics_audit.py`，覆盖 overlay metadata、source evidence/mechanism 分类与 unique round blocker 聚合。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`、`docs/bid_map_schema.md`、`DECISIONS_V3.md` 与 `OBSERVATIONS_V3.md`。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_source_semantics_audit.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_settlement_source_semantics_audit.py -q
python scripts\summarize_v3_settlement_source_semantics_audit.py --group-by unique_residual_mode --top 8 --format summary
python scripts\summarize_v3_settlement_source_semantics_audit.py --group-by mechanism_class --top 8 --format summary
python scripts\summarize_v3_settlement_source_semantics_audit.py --group-by source_evidence_class --top 8 --format summary
```

真实 source-semantics smoke 要点：

```text
table_raw_version=300 tables_version=300
activity_present=False activity_listed=True
overlay_status=v300_activity_listed_missing_locally

unique_round_cap_overflow_after_temp:
  files=21
  maps=2501:7,2503:3,2504:2,2506:2,2508:2,2510:2,2408:1,2410:1
  families=shipwreck:19,villa:2
  capture_days=20260601:8,20260531:6,20260530:3,20260604:2,20260529:1,20260605:1
  session_p6=129501:17,127412:4
  evidence=settlement_payload_verified_only:18,direct_action_matches_inventory:2,public_total_matches_inventory:1
  mechanisms=session_capacity_source_semantics:18,server_side_settlement_expansion:3
  unique_non_temp=max 57, round_cap=max 50
  non_zodiac_missing=max 0
  payload_mismatch=0/21
  raw_candidate_delta=max 0
  occupied_delta=max 0
  inventory_state_delta=max 0
  public_match_rows=1/21
  full_action_rows=2/21
```

解读：

- 21 条 unique non-temp over round-cap 的主因可复核地收口为：current local v300 BidMap `round_caps_candidate=50`/`drop_ref<=44` 不是 final settlement item-count hard cap；final 0x002D settlement inventory 由 server-side settlement expansion / session-capacity source semantics 产生，且仍落在 current reachable Drop universe 内。
- 该解释对应机制类：`server_side_settlement_expansion`（3 条有 public total 或 direct full action 外部确认）与 `session_capacity_source_semantics`（18 条由 0x002D payload raw/occupied slot 自证）。
- per-session table version 目前不是强解释：over-cap 跨 6 个 capture day、2 个 session prefix、8 个 map，local raw/table version 均为 300；当前无法从旧 CDN URL 取回远端 current table 验证，只保留为弱假设。
- external overlay table 只保留为最小不可判定假设：local v300 filelist 列出 `Tables/Activity.txt` 但本地缺表；不过 21 条的 non-zodiac Drop-universe missing 为 0，因此 overlay 若存在，更像影响件数/活动机制，不是引入未知非生肖 item universe。
- 本阶段不恢复 formal/value sampler 参数调优，不讨论 v3 promotion；下一阶段建议先补 source parser / table acquisition 或扩大样本确认 18 条 payload-only rows，再决定是否恢复 shadow-only formal/value sampler。

## 2026-06-06 checkpoint：capacity/source expansion shadow 层与 session holdout

本轮把 settlement source-semantics 结论固化为 v3 audit-only shadow 层，并用 session holdout 验证其覆盖边界。改动仍不改变 v2 formal/live/UI，不改变正式出价，不恢复 formal/value sampler 参数调优。

改动：

- 新增 `src/bidking_lab/inference/v3/capacity_source_expansion.py`：
  - 输出 `v3_cse_*` flat fields；
  - 固定 `affects_bid=False`、`active=False`；
  - 只表达 capacity/source expansion evidence 是否可见、是否 candidate、对应机制/evidence/source group。
- `src/bidking_lab/inference/v3/pipeline.py`、`scripts/evaluate_fatbeans_v3_samples.py` 与 `src/bidking_lab/live/monitor.py` 接入同一 shadow report：
  - archive rows 输出 `v3_cse_*`；
  - live `model_eval` 输出核心 `v3_cse_*`；
  - 不参与 posterior/formal/live bid decision。
- 新增 `scripts/build_v3_capacity_source_expansion_shadow.py`，生成 `data/processed/v3_capacity_source_expansion_shadow.json`，合并 default archive 与 0605 activity cohort 的 map_id/map_family entries。
- 新增 `scripts/summarize_v3_capacity_source_expansion_holdout.py`：
  - 按 session/file stable fold 验证 source-semantics 候选；
  - 分开输出 recall、precision、false positive、payload mismatch 与 non-zodiac overlay rows；
  - payload/overlay blocker 状态只按 truth rows 判定，避免 broad group 中非 blocker 行误阻塞。
- `scripts/summarize_v3_promotion_readiness.py` 新增 `capacity_source_expansion_shadow` gate：
  - 只证明 `v3_cse_*` 可见且 inactive；
  - 不放宽 `prior_stress_capacity_table_drift`、formal baseline、formal/value sampler 或 promotion gates。
- 更新 `.gitignore` 允许提交 `data/processed/v3_capacity_source_expansion_shadow.json`。

关键验证：

```powershell
python -m py_compile src\bidking_lab\inference\v3\capacity_source_expansion.py src\bidking_lab\inference\v3\pipeline.py src\bidking_lab\inference\v3\__init__.py scripts\build_v3_capacity_source_expansion_shadow.py scripts\evaluate_fatbeans_v3_samples.py src\bidking_lab\live\monitor.py
pytest --basetemp=.tmp\codex\pytest tests\test_inference_v3_capacity_source_expansion.py tests\test_build_v3_capacity_source_expansion_shadow.py tests\test_inference_v3_pipeline.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py -q
python scripts\build_v3_capacity_source_expansion_shadow.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_source_expansion_holdout.py tests\test_summarize_v3_promotion_readiness.py -q
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_family --top 8 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id --top 8 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py data\samples\fatbeans_activity_20260605_shipwreck --group-by map_family --top 8 --min-train-sessions 2 --format summary
python scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
python scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary
```

真实 holdout / readiness 要点：

```text
default archive, group_by=map_family:
  sessions=441
  truth_unique_round_rows=21
  truth_source_semantics_rows=21
  covered_unique_round_rows=21
  missed_unique_round_rows=0
  unique_round_recall=1.0
  candidate_precision=0.050119
  false_positive_candidate_rows=398
  truth_payload_mismatch_rows=0
  truth_non_zodiac_missing_rows=0
  status_counts=watch_capacity_source_expansion_holdout:2,within_capacity_source_semantics_shadow_only:1

default archive, group_by=map_id:
  truth_unique_round_rows=21
  covered_unique_round_rows=18
  missed_unique_round_rows=3
  unique_round_recall=0.857143
  candidate_precision=0.089109
  status_counts=blocked_holdout_under_recall:3,watch_capacity_source_expansion_holdout:6,within_capacity_source_semantics_shadow_only:12

activity_20260605_shipwreck, group_by=map_family:
  truth_unique_round_rows=0
  non_zodiac_missing_rows=15
  status_counts=within_capacity_source_semantics_shadow_only:1

archive evaluator:
  v3_cse_ready_rows=1560
  v3_cse_candidate_rows=752
  v3_cse_active_rows=0

readiness:
  capacity_source_expansion_shadow=watch
  overall_status=not_ready
```

解读：

- 对 21 条 unique non-temp over round-cap 的可复核解释已收口：它们是 server-side settlement expansion / session-capacity source semantics 下的 final settlement inventory，不是 parser/slot/duplicate/item-universe 错误。
- map-family holdout 能覆盖全部 21 条 blocker，但 precision 极低，说明它只能作为 broad watch prior，不能作为 formal/value sampler 或 promotion evidence。
- map_id holdout 更精确但漏 3 条单例/稀疏 map blocker，因此如果下一阶段恢复 sampler 设计，仍需要 source parser、活动/远端表 acquisition 或更细的 expansion prior。
- activity 0605 cohort 当前没有 unique round-cap truth rows，但 15 条 non-zodiac missing 继续支持外部 overlay/source-parser 作为旁路假设。
- readiness/promotion gate 未放宽；下一阶段建议先做 source parser/table acquisition 或追加样本，再由用户确认是否恢复 shadow-only formal/value sampler。

## 2026-06-07 checkpoint：source-aware CSE holdout matrix / map-id miss audit

本轮继续从 `6a9442b` 的 `v3_cse_*` broad watch prior 往可复核 source-aware expansion prior 收窄。改动仍是 v3 audit-only，只扩展 holdout 审计，不改变 CSE pipeline 默认 matching，不改变 v2 formal/live/UI，不改变正式出价，不恢复 formal/value sampler 参数调优。

改动：

- `scripts/summarize_v3_capacity_source_expansion_holdout.py`：
  - 新增 composite group 支持：
    - `map_id_capture_rounds`
    - `map_id_round_index`
    - `map_id_last_round_flag`
    - `map_family_capture_rounds`
    - `map_family_sub_pool_kind`
    - `map_family_outer_shape`
    - `map_family_payload_shape`
    - `map_family_action_count`
    - `map_id_payload_shape`
  - 新增 `--fallback-group-by`，只在 primary group 训练折没有 source-semantics support 时尝试 fallback；
  - summary 输出 `candidate_source_counts`，区分 `primary` 与 `fallback` candidate 来源。
- `tests/test_summarize_v3_capacity_source_expansion_holdout.py`：
  - 增加 fallback group 覆盖，验证 map_id 无 train support 时可以审计 fallback candidate 来源。
- 使用多 agent 只读审查：
  - map-id miss / false-positive 审查；
  - payload/source parser 可用字段审查；
  - 均未修改文件，结论由主窗口整合。

关键验证：

```powershell
python -m py_compile scripts\summarize_v3_capacity_source_expansion_holdout.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_source_expansion_holdout.py -q
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id --fallback-group-by map_family_sub_pool_kind --top 8 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id_capture_rounds --top 6 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id_last_round_flag --top 6 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_family_outer_shape --top 6 --min-train-sessions 4 --format summary
```

真实 holdout 要点：

```text
map_id baseline:
  truth=21 covered=18 missed=3 candidate=202 fp=184
  recall=0.857143 precision=0.089109

missed map_id rows:
  2408: fatbeans_valid_aisha_2408_5rounds_2408_1274128129457532_0081.json
  2410: fatbeans_valid_ethan_2410_1rounds_2410_1295019008815241_0283.json
  2509: fatbeans_valid_ethan_2509_5rounds_2509_1295018712615152_0360.json

map_id -> map_family_sub_pool_kind fallback:
  truth=21 covered=21 missed=0 candidate=347 fp=326
  candidate_sources=primary:202,fallback:145
  recall=1.0 precision=0.060519

map_id_capture_rounds:
  truth=21 covered=11 missed=10 candidate=85 fp=74
  recall=0.52381 precision=0.129412

map_id_last_round_flag:
  truth=21 covered=17 missed=4 candidate=178 fp=161
  recall=0.809524 precision=0.095506

map_family_outer_shape:
  truth=21 covered=19 missed=2 candidate=257 fp=238
  recall=0.904762 precision=0.07393
```

解读：

- 3 条 map-id miss 都是 singleton truth fold：该 map_id 只有 1 条 source-semantics truth，且 truth 落在 test fold，训练折没有 source support。
- `map_family_sub_pool_kind` fallback 能补全 recall，但 candidate/false-positive 明显变多，不能作为“收窄 prior”的默认策略。
- `map_id_capture_rounds`、`map_id_round_index`、`map_id_payload_shape` 等更窄 signature 能提高局部 precision，但 sample-limited 与 recall 损失太大。
- payload/source 字段可用于 post-settlement source signature audit，但现有 payload shape、outer wrapper、action count 都与 within-cap rows 混用，不能单独解释 over-cap。
- 当前最保守默认仍应是 exact `map_id` support；fallback/source-signature 只保留为 audit matrix。下一步若要真正提升 prior，需要 source parser/table acquisition 或更多样本，而不是把 broad fallback 接入默认 CSE。

## 2026-06-07 checkpoint：252x activity cohort 归入调参参考 / source-table reference

用户澄清“252xx 那组”后，本轮复核 0605 沉船活动样本与本机 v303 表。结论：252x activity cohort 可以作为后续 source parser、table acquisition、activity overlay 与 shadow-only tuning 的参考集，但不能替代原版沉船样本，也不能进入 default prior、readiness/promotion 或正式出价。

改动：

- `scripts/summarize_fatbeans_sample_manifest.py` 新增可选 manifest 元数据：
  - `--cohort-role`
  - `--metric-scope`
  - `--cohort-note`
  - 显式带 cohort 元数据时写入 `affects_bid=false`；
  - 默认 archive manifest 输出不变。
- `data/sample_manifests/fatbeans_activity_shipwreck_2026-06-05.json` 重新生成为：
  - `cohort_role=activity_tuning_reference`
  - `metric_scope=source_parser_table_acquisition_and_shadow_tuning_reference_only`
  - `affects_bid=false`
- `tests/test_summarize_fatbeans_sample_manifest.py` 增加 reference cohort metadata 覆盖。
- 更新 `DECISIONS_V3.md`、`OBSERVATIONS_V3.md` 与 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`。

复核命令：

```powershell
python scripts\summarize_fatbeans_sample_manifest.py data\samples\fatbeans_activity_20260605_shipwreck
python scripts\summarize_v3_activity_mapping_likelihood.py
python scripts\summarize_v3_archive_table_timing.py data\samples\fatbeans_activity_20260605_shipwreck --raw-root C:\xiangmuyunxing\steamapps\common\BidKing\BidKing_Data\StreamingAssets --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py data\samples\fatbeans_activity_20260605_shipwreck --group-by map_id --top 10 --min-train-sessions 1 --format summary
python scripts\summarize_v3_prior_robustness_audit.py data\samples\fatbeans_activity_20260605_shipwreck --posterior-trials 64 --format summary
```

关键事实：

```text
activity captures:
  files=15 parsed=15 valid=15 bid_windows=58 ready_windows=58
  captured maps=2521:5,2522:1,2524:3,2526:2,2528:1,2529:3

v303 table source:
  activity_range=2521-2530 bidmap_present=10 drop_present=0 drop_missing=10 drop_ref_pairs=22-44:10
  activity_range=4521-4530 bidmap_present=10 drop_present=0 drop_missing=10 drop_ref_pairs=22-44:10

activity mapping likelihood:
  files=15
  winners=minus10:11,minus20:4
  item_winners=minus10:11,minus20:4
  missing_item_rate=0 for both schemes

prior robustness:
  v3_robust_status=prior_unavailable
  ready=58 post_ready=0 metric=0 trusted=0/58 activity=58 stressed=0

CSE holdout on activity cohort:
  sessions=15 truth_unique_round_rows=0 candidate_rows=0
  non_zodiac_missing_rows=15 truth_non_zodiac_missing_rows=0
  status_counts=within_capacity_source_semantics_shadow_only:6
```

解读：

- 当前仓库可复核的 252x capture 是 15 份，不是 16 份；若“16 个活动地图”来自旧窗口口径，当前项目内没有能复现该数字的 source。
- `2521-2530` 在本机 v303 中是 10 个 BidMap rows，但 Drop 仍缺失；它们能指向需要 acquisition/source parser 的表侧范围。
- `252x->251x` likelihood 略优于 `252x->250x`，但 margin 小，不能证明 official mapping。
- 252x cohort 继续用于调参参考和 activity/source-table 审计；在 verified `2521+` Drop/source overlay 前，不进入 default archive baseline、formal/value sampler promotion、readiness 或 official bidding。

## 2026-06-07 checkpoint：CSE source-context 解释与 live/model_eval 字段对齐

本轮继续收窄 `v3_cse_*` capacity/source expansion shadow：把 source-semantics 从 broad evidence class 进一步拆成可复核的 `source_context_class`，并同步 archive evaluator、processed artifact 与 live `model_eval` 字段。v3 仍为 audit/shadow-only，`active=false`、`affects_bid=false` 不变。

改动：

- `scripts/summarize_v3_settlement_source_semantics_audit.py`：
  - 新增 `source_context_class` 分组；
  - 输出 action coverage gap/ratio；
  - 区分 `public_total_confirmed`、`direct_action_full_confirmed`、`payload_verified_partial_action_only`、`payload_verified_empty_action_results`、`payload_unverified_or_mismatch`、`payload_verified_no_external_source`。
- `scripts/summarize_v3_capacity_source_expansion_holdout.py`：
  - holdout row/summary 输出 `source_context_class` 与 truth context 分布；
  - 输出 `missed_examples`，直接列出 map-id 漏召回样本、fold、train support、evidence/context/mechanism。
- `src/bidking_lab/inference/v3/capacity_source_expansion.py`：
  - `CapacitySourceExpansionEntry` / flat dict 新增 `source_context_classes` / `v3_cse_source_context_classes`；
  - artifact loader 兼容 compact artifact 与 source-summary row，避免 reload 后丢失 string counts 与 p95/max 数值。
- `scripts/build_v3_capacity_source_expansion_shadow.py`：
  - processed artifact 写入 `source_context_classes`，`generated_at=2026-06-07`。
- `scripts/evaluate_fatbeans_v3_samples.py` 与 `src/bidking_lab/live/monitor.py`：
  - archive CSV 与 live `model_eval` 同步输出 `v3_cse_source_context_classes`。
- 测试覆盖 source-context 分类、artifact build、entry round-trip、archive row 与 live model_eval 字段。

验证：

```powershell
python -m py_compile scripts\summarize_v3_settlement_source_semantics_audit.py scripts\summarize_v3_capacity_source_expansion_holdout.py scripts\build_v3_capacity_source_expansion_shadow.py scripts\evaluate_fatbeans_v3_samples.py src\bidking_lab\inference\v3\capacity_source_expansion.py src\bidking_lab\live\monitor.py
pytest --basetemp=.tmp\codex\pytest tests\test_inference_v3_capacity_source_expansion.py tests\test_build_v3_capacity_source_expansion_shadow.py tests\test_summarize_v3_settlement_source_semantics_audit.py tests\test_summarize_v3_capacity_source_expansion_holdout.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py -q
python scripts\build_v3_capacity_source_expansion_shadow.py
python scripts\summarize_v3_settlement_source_semantics_audit.py --group-by source_context_class --top 8 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id --top 12 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_family --top 12 --min-train-sessions 4 --format summary
python scripts\summarize_v3_capacity_source_expansion_holdout.py --group-by map_id --fallback-group-by map_family_sub_pool_kind --top 12 --min-train-sessions 4 --format summary
python scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
python scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary
```

关键结果：

```text
source_context overall:
  payload_verified_partial_action_only:339
  payload_verified_empty_action_results:55
  public_total_confirmed:27
  direct_action_full_confirmed:17
  payload_unverified_or_mismatch:2
  payload_verified_no_external_source:1

truth unique-round rows by context:
  payload_verified_partial_action_only:15
  payload_verified_empty_action_results:3
  direct_action_full_confirmed:2
  public_total_confirmed:1

map_id holdout:
  truth=21 covered=18 missed=3 candidate=202 fp=184
  recall=0.857143 precision=0.089109

missed examples:
  2509 fatbeans_valid_ethan_2509_5rounds_2509_1295018712615152_0360.json context=payload_verified_empty_action_results train_source=0 excess=7
  2410 fatbeans_valid_ethan_2410_1rounds_2410_1295019008815241_0283.json context=payload_verified_empty_action_results train_source=0 excess=3
  2408 fatbeans_valid_aisha_2408_5rounds_2408_1274128129457532_0081.json context=payload_verified_partial_action_only train_source=0 excess=2

map_family holdout:
  truth=21 covered=21 missed=0 candidate=419 fp=398
  recall=1.0 precision=0.050119

map_id -> map_family_sub_pool_kind fallback:
  truth=21 covered=21 missed=0 candidate=347 fp=326
  candidate_sources=primary:202,fallback:145
  recall=1.0 precision=0.060519

archive/readiness:
  v3_cse_ready_rows=1560
  v3_cse_candidate_rows=752
  v3_cse_active_rows=0
  readiness overall_status=not_ready
  capacity_source_expansion_shadow=watch
```

解读：

- 21 条 unique non-temp over round-cap 的最强当前解释仍是 server-side settlement expansion / session-capacity source semantics；其中 3 条已有 public/direct full source confirmation，18 条仍主要依赖 payload-verified settlement rows。
- payload-only truth rows 不能一概视作强 external source confirmation：15 条是 partial action only，3 条 action result 存在但 observed item 为 0；这解释了为什么仍需要 source parser/table acquisition，而不是直接调 sampler。
- 3 条 map-id miss 是 holdout support gap：test fold 中出现 singleton truth，而 train folds 没有同 map source-semantics support。
- map-family/fallback 能补 recall，但 false positive 过宽；当前不能作为 default source-aware expansion prior 或 readiness/promotion 证据。
- 下一步应继续补 source parser、活动/远端表 acquisition、payload-only 外部 source 解释和更精细的可证伪 prior；仍不恢复 formal/value sampler 参数调优。

## 2026-06-07 checkpoint：CSE prebid pressure guard 审计

本轮把 CSE 从 group-level broad watch 进一步拆出一个 prebid 可见的 high-precision pressure tier：当 `v3_cse_candidate=true` 且当前窗口的 target count 已超过 table prior max 时，输出 `v3_cse_pressure_candidate=true`。该字段只用于 archive/live/readiness 审计，不改变 `active=false`、`affects_bid=false`。

改动：

- `src/bidking_lab/inference/v3/capacity_source_expansion.py`：
  - 新增 `v3_cse_pressure_candidate`；
  - 新增 `v3_cse_target_prior_max_delta`；
  - `v3_cse_flags` 在 pressure tier 中增加 `target_count_above_prior_max`。
- `scripts/evaluate_fatbeans_v3_samples.py`：
  - CSV header 与 summary 增加 `v3_cse_pressure_candidate_rows`；
  - 保留原 `v3_cse_candidate_rows` 作为 broad watch 分母。
- `src/bidking_lab/live/monitor.py`：
  - live `model_eval` 增加 `v3_cse_pressure_candidate`、`v3_cse_target_count_source`、`v3_cse_target_count`、`v3_cse_prior_items_per_session_max`、`v3_cse_target_prior_max_delta`、`v3_cse_target_to_unique_non_temp_p95_delta`。
- `scripts/summarize_v3_capacity_source_expansion_prebid_guard.py`：
  - 新增 archive prebid guard 汇总脚本；
  - 将 prebid evaluator rows 与 settlement source-semantics truth 按 capture file 合并；
  - 同时输出 window-level 和 session-level recall/precision。
- `scripts/summarize_v3_promotion_readiness.py`：
  - readiness summary 与 `capacity_source_expansion_shadow` gate 展开 `pressure_candidate_rows`，但 gate 状态不因此放宽。
- 新增/更新测试覆盖 CSE pressure flat dict、archive row、live model_eval、readiness count 与 prebid guard summary。

验证：

```powershell
python -m py_compile scripts\summarize_v3_capacity_source_expansion_prebid_guard.py scripts\evaluate_fatbeans_v3_samples.py scripts\summarize_v3_promotion_readiness.py src\bidking_lab\inference\v3\capacity_source_expansion.py src\bidking_lab\live\monitor.py
pytest --basetemp=.tmp\codex\pytest tests\test_inference_v3_capacity_source_expansion.py tests\test_evaluate_fatbeans_v3_samples.py tests\test_live_monitor.py tests\test_summarize_v3_capacity_source_expansion_prebid_guard.py tests\test_summarize_v3_promotion_readiness.py -q
python scripts\summarize_v3_capacity_source_expansion_prebid_guard.py --posterior-trials 64 --format summary
python scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
python scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary
```

关键结果：

```text
CSE prebid guard:
  ready_rows=1560 truth_rows=81 truth_sessions=21

cse_candidate:
  selected_rows=752 covered_rows=81 fp_rows=671
  row_recall=1.0 row_precision=0.107713
  session_recall=1.0 session_precision=0.098131

pressure_candidate / target_above_prior_max:
  selected_rows=61 covered_rows=24 fp_rows=37
  row_recall=0.296296 row_precision=0.393443
  selected_sessions=31 covered_sessions=11 fp_sessions=20
  session_recall=0.52381 session_precision=0.354839

target_near_source_p95_5:
  selected_rows=56 covered_rows=23 fp_rows=33
  row_recall=0.283951 row_precision=0.410714
  session_recall=0.52381 session_precision=0.392857

archive/readiness:
  v3_cse_candidate_rows=752
  v3_cse_pressure_candidate_rows=61
  v3_cse_active_rows=0
  readiness overall_status=not_ready
```

解读：

- `pressure_candidate` 能把 CSE broad watch 的 precision 从约 0.108 提到约 0.393，但只覆盖 11/21 truth sessions；它是 high-precision watch tier，不是 source-aware prior 的完整替代。
- 这个 guard 使用 prebid 可见 target/prior max，不依赖 settlement-only `source_context_class` 或 final unique count，适合进入 live `model_eval` 做实战复盘。
- 由于 recall 仍不足，不能恢复 formal/value sampler 调参，也不能作为 promotion/readiness 放行条件。

## 2026-06-07 checkpoint：payload-only CSE truth/miss/pressure 交叉审计

本轮新增 payload-only 专项审计，把 settlement source-semantics truth rows 与 map-id holdout 覆盖、prebid CSE pressure windows 合并，避免继续把 18 条 payload-only truth 混成同一种证据。

改动：

- `scripts/summarize_v3_capacity_source_expansion_payload_only_audit.py`：
  - 聚焦 `source_context_class` 为 `payload_verified_*` / `payload_unverified_*` 且满足 source-semantics truth 的 rows；
  - 按 capture file join map-id holdout eval rows，输出是否被 exact map-id train support 覆盖；
  - 按 capture file join archive prebid evaluator rows，输出 `v3_cse_candidate` / `v3_cse_pressure_candidate` window 覆盖；
  - 汇总 action observed max、inventory gap、ratio、unique round excess 和 example rows。
- `tests/test_summarize_v3_capacity_source_expansion_payload_only_audit.py` 覆盖 payload truth、external truth、holdout miss 与 prebid pressure join。

验证：

```powershell
python -m py_compile scripts\summarize_v3_capacity_source_expansion_payload_only_audit.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_source_expansion_payload_only_audit.py -q
python scripts\summarize_v3_capacity_source_expansion_payload_only_audit.py --posterior-trials 64 --top 8 --format summary
```

真实结果：

```text
settlement_rows=441 truth_rows=21 payload_truth_rows=18 external_truth_rows=3
payload_contexts=payload_verified_partial_action_only:15,payload_verified_empty_action_results:3
payload_map_id_missed_rows=3
payload_prebid_candidate_rows=18
payload_prebid_pressure_rows=8

payload_verified_empty_action_results:
  rows=3 maps=2410:1,2501:1,2509:1
  missed=2 prebid_candidate=3 prebid_pressure=1
  action_max=0 action_gap avg=60 max=66

payload_verified_partial_action_only:
  rows=15 maps=2501:5,2503:2,2504:2,2508:2,2510:2,2408:1,2506:1
  missed=1 prebid_candidate=15 prebid_pressure=7
  action_max avg=5.867 max=25
  action_gap avg=53.467 max=62
```

关键 examples：

```text
empty-action miss:
  2509 fatbeans_valid_ethan_2509_5rounds_2509_1295018712615152_0360.json
    covered=False train_source=0 pressure=1 action_max=0 action_gap=66 excess=7
  2410 fatbeans_valid_ethan_2410_1rounds_2410_1295019008815241_0283.json
    covered=False train_source=0 pressure=0 action_max=0 action_gap=57 excess=3

partial-action miss:
  2408 fatbeans_valid_aisha_2408_5rounds_2408_1274128129457532_0081.json
    covered=False train_source=0 pressure=2 action_max=4 action_gap=52 excess=2
```

解读：

- 18 条 payload-only truth 全部至少被 broad `v3_cse_candidate` prebid windows 看到，但只有 8 条进入 pressure tier；pressure 有复盘价值，但不能作为完整召回 prior。
- 3 条 exact map-id miss 全在 payload-only：2 条 empty-action、1 条 partial-action；这更支持下一步优先查 action-result parser/source acquisition 与 support-depth，而不是调 formal/value sampler。
- empty-action rows 的 action observed max 全为 0、action gap 很大，是最强的 source parser/table acquisition 目标；partial-action rows 至少有少量 action observed items，但仍存在大 gap。

## 2026-06-07 checkpoint：payload-only action payload shape 审计

本轮在 payload-only CSE 审计中加入 action-result raw payload shape 分类，确认 empty-action 与 partial-action 的真实差异，避免把 numeric source 误判成 item parser 漏解。

改动：

- `scripts/summarize_v3_capacity_source_expansion_payload_only_audit.py`：
  - 对 payload-only truth rows 对应 capture 解析 action-result raw blocks；
  - 新增 `source_action_payload_shape_class`，区分 `numeric_only_result`、`item_reveal_payload`、`unparsed_item_payload` 等；
  - 输出 action ids、result fields、item payload block 数、单 action block 最大 item 数与 observed item max；
  - 保持 audit-only，不改变 CSE artifact、archive evaluator、live `model_eval` 的出价语义。
- `tests/test_summarize_v3_capacity_source_expansion_payload_only_audit.py`：
  - 覆盖 source shape 注入、context 分组与 numeric/item payload 汇总。

验证：

```powershell
python -m py_compile scripts\summarize_v3_capacity_source_expansion_payload_only_audit.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_source_expansion_payload_only_audit.py -q
python scripts\summarize_v3_capacity_source_expansion_payload_only_audit.py --posterior-trials 64 --top 8 --format summary
```

真实结果：

```text
payload_truth_rows=18
payload_source_shapes=item_reveal_payload:15,numeric_only_result:3
parse_errors=0 source_shape_parse_errors=0

payload_verified_empty_action_results:
  rows=3 maps=2410:1,2501:1,2509:1
  source_shapes=numeric_only_result:3
  source_action_ids=100105:13,100104:9,100124:6,100107:3
  source_result_fields=14:25,12:6
  source_item_payload_block_max=0
  source_observed_item_max=0

payload_verified_partial_action_only:
  rows=15 maps=2501:5,2503:2,2504:2,2508:2,2510:2,2408:1,2506:1
  source_shapes=item_reveal_payload:15
  source_action_ids=100136:43,100129:42,100128:24,100107:17,100158:13,100105:13,100104:10,100152:9
  source_item_payload_block_max avg=5.867 max=25
  source_observed_item_max avg=5.867 max=25
```

解读：

- 3 条 empty-action truth 不是 item reveal parser 漏解；它们的 direct action payload 只有 numeric result fields，没有 field 8 item list。
- empty-action 的 blocker 应改写为 numeric action source semantics / table support-depth / server-side settlement expansion 解释，而不是继续找 item payload parser。
- 15 条 partial-action truth 均为 item reveal payload，但 observed item max 仍远低于 settlement inventory；这支持 session-capacity/source semantics 的弱线索，仍不能作为 full external confirmation。
- exact map-id miss 中的 2509、2410 属于 numeric-only support-depth 缺口，2408 属于 item-reveal partial support-depth 缺口；下一步仍应做 source/table acquisition 或更细 source semantics，不恢复 formal/value sampler 调参。

## 2026-06-07 checkpoint：CSE source-key holdout 矩阵

本轮新增 source-key holdout 审计，验证 action payload shape / numeric action signature 是否能把 broad CSE watch 收窄成更高质量 source-aware prior key。

改动：

- `scripts/summarize_v3_capacity_source_expansion_source_key_holdout.py`：
  - 复用 settlement source-semantics rows 与 action payload shape 解析；
  - 对 `map_id`、`map_family`、`source_shape`、`map_family_source_shape`、`map_id_source_shape`、`source_shape_signature`、`map_family_source_shape_signature`、`map_id_source_shape_signature` 做 session holdout；
  - 输出每个 key 的 candidate rows、covered rows、missed rows、false positives、recall、precision 与 missed examples。
- `tests/test_summarize_v3_capacity_source_expansion_source_key_holdout.py` 覆盖 source shape 注入、fold train support、candidate precision 与 map-id singleton 不覆盖场景。

验证：

```powershell
python -m py_compile scripts\summarize_v3_capacity_source_expansion_source_key_holdout.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_source_expansion_source_key_holdout.py -q
python scripts\summarize_v3_capacity_source_expansion_source_key_holdout.py --top 8 --format summary
python scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary
```

真实结果：

```text
sessions=441 folds=5 min_train_sessions=4
source_shapes=item_reveal_payload:384,numeric_only_result:56,no_action_results:1
truth_source_shapes=item_reveal_payload:18,numeric_only_result:3
source_shape_parse_errors=0

map_family:
  candidate_rows=419 covered=21 missed=0 fp=398
  recall=1.0 precision=0.050119

source_shape:
  candidate_rows=440 covered=21 missed=0 fp=419
  recall=1.0 precision=0.047727

map_family_source_shape:
  candidate_rows=378 covered=19 missed=2 fp=359
  recall=0.904762 precision=0.050265

map_id:
  candidate_rows=202 covered=18 missed=3 fp=184
  recall=0.857143 precision=0.089109

map_id_source_shape_signature:
  candidate_rows=152 covered=17 missed=4 fp=135
  recall=0.809524 precision=0.111842

readiness:
  overall_status=not_ready
  capacity_source_expansion_shadow=watch
  cse_candidate_rows=752
  cse_pressure_candidate_rows=61
  cse_active_rows=0
```

解读：

- `source_shape` 单独不能提升 precision，甚至低于 `map_family`。
- `map_id_source_shape` / `map_id_source_shape_signature` 只有小幅 precision 改善，但召回从 18/21 降到 17/21，并引入更多 sample-limited groups。
- 2509、2410、2408 仍是 train source support=0 的漏召回样本；shape/signature 不能解决 singleton/support-depth blocker。
- 当前不能把 action payload shape 或 numeric signature 接入默认 source-aware prior；下一步仍需要 source/table acquisition、更多同 source support 样本，或更强的 prebid 可见 pressure/source signal。

## 2026-06-07 checkpoint：CSE support-depth fallback holdout 矩阵

本轮新增 support-depth holdout 审计，验证“训练折 source-semantics 支持条数”和“source evidence 类型”是否能让 map-id/fallback CSE candidate 更接近可复核 source-aware prior。

改动：

- `scripts/summarize_v3_capacity_source_expansion_support_depth_holdout.py`：
  - 以 `map_id` 为 primary group，支持可选 fallback group（默认 `none,map_family`）；
  - 支持 source filter pairs：`all:all`、`external:external`、`payload:payload`、`partial_payload:partial_payload`、`all:external`、`external:all`；
  - 对 `min_train_source_rows=1..5` 做 session holdout，输出 primary/fallback candidate rows、covered/missed/false-positive、recall、precision、train source depth 与 missed examples。
- `tests/test_summarize_v3_capacity_source_expansion_support_depth_holdout.py` 覆盖 fallback support 阈值、fold train exclusion 与 external filter 不计 payload source。

验证：

```powershell
python -m py_compile scripts\summarize_v3_capacity_source_expansion_support_depth_holdout.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_capacity_source_expansion_support_depth_holdout.py -q
python scripts\summarize_v3_capacity_source_expansion_support_depth_holdout.py --top 12 --format summary
python scripts\summarize_v3_capacity_source_expansion_support_depth_holdout.py --fallback-group-by none --source-filter-pair all --min-train-source-rows 1 --min-train-source-rows 2 --min-train-source-rows 3 --top 8 --format summary
python scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary
```

真实结果：

```text
pure map_id / all source:
  min_source=1 candidate_rows=202 covered=18 missed=3 fp=184
  recall=0.857143 precision=0.089109
  min_source=2 candidate_rows=139 covered=10 missed=11 fp=129
  recall=0.47619 precision=0.071942
  min_source=3 candidate_rows=90 covered=7 missed=14 fp=83
  recall=0.333333 precision=0.077778

map_id primary + map_family fallback / all:all:
  min_source=1 candidate_rows=419 covered=21 missed=0 fp=398
  recall=1.0 precision=0.050119
  min_source=3 candidate_rows=231 covered=19 missed=2 fp=212
  recall=0.904762 precision=0.082251

map_id primary + map_family fallback / external:external:
  min_source=1 candidate_rows=231 covered=19 missed=2 fp=212
  recall=0.904762 precision=0.082251

readiness:
  overall_status=not_ready
  capacity_source_expansion_shadow=watch
  cse_candidate_rows=752
  cse_pressure_candidate_rows=61
  cse_active_rows=0
```

missed examples for support-depth candidate：

```text
2410 numeric-only:
  primary_group=2410 primary_train_source=0
  fallback_group=villa fallback_train_source=1
  excess=3

2408 partial-action:
  primary_group=2408 primary_train_source=0
  fallback_group=villa fallback_train_source=1
  excess=2
```

解读：

- 对 pure `map_id` candidate 提高 train source 阈值会显著降低 recall，且 precision 不升；不能作为默认收窄策略。
- 对 fallback 限流有价值：`map_id -> map_family` 且 `min_source>=3` 将 broad fallback precision 从 `0.050119` 提到 `0.082251`，仍覆盖 19/21。
- 该 support-depth fallback 仍低于 pure `map_id` precision，且继续漏 2410/2408；只能作为下一轮 source-aware prior candidate 审计，不得接入 formal/live。

## 2026-06-07 checkpoint：策略切换与 guarded bridge stability 固化

背景：

- CSE/support-depth 已经验证很久，最新 `f659d64` 仍显示 CSE 只能作为 watch prior。
- 用户明确要求避免继续耗在同一类审计，策略应转向更实质的 v3 formal/value 工作台。

本轮动作：

- 新增 `docs/v3_strategy_pivot_2026-06-07.zh-CN.md`，记录新目标、stop-loss 和下一阶段允许/禁止事项。
- 生成并提交 `data/processed/v3_scp_guarded_bridge_stability_shadow.json`。
- 用该 JSON 复跑 readiness，确认 `settlement_count_guarded_bridge_stability` 不再是 `not_evaluated`，而是已评估且 blocked。
- 新增 `scripts/summarize_v3_promotion_workbench.py`，消费 readiness JSON 并输出 lane-level `blocked/watch/stop_loss` 与 `next_mode`，不重新跑模型。

验证命令：

```powershell
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_scp_guarded_bridge_stability.py --posterior-trials 64 --posterior-seed 0 --posterior-seed 1 --posterior-seed 7 --format summary
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --guarded-bridge-stability-json data\processed\v3_scp_guarded_bridge_stability_shadow.json --format summary
C:\Users\shenc\anaconda3\python.exe scripts\summarize_v3_promotion_workbench.py .tmp\codex\v3_readiness_with_stability.json --format summary
```

结果：

```text
guarded bridge stability:
overall_status=blocked_applied_hurt
reasons=applied_hurts_present,non_watch_run,selected_group_drift,low_applied_rows
watch_runs=2/3
stable_groups=2506
union_groups=2501,2506
min_applied=9
required=20
seed=1 applied_hurts=2501
seed=7 selected=2506 applied_rows=9

readiness with stability json:
overall_status=not_ready
settlement_count_guarded_bridge_stability=blocked
scp_guarded_stability=blocked_applied_hurt
cse_candidate_rows=752
cse_pressure_candidate_rows=61
cse_active_rows=0
formal_value_sampler_holdout=blocked

promotion workbench:
overall_status=not_ready
blocked_gates=13
verdicts=blocked:2,stop_loss:4,usable_watch:1
next_mode=build_shadow_formal_value_workbench
```

新策略：

- CSE 继续保留为 watch/support lane，不再继续无限新增 key/support-depth 审计。
- Guarded bridge lane 由于 seed stability 失败，近期不得作为 promotion path。
- 下一步转入 v3 formal/value promotion workbench：先统一候选 lane、分母、support、holdout、seed stability、MAE/below/P90/pinball/high-over 和 `affects_bid=false`，再选择最小 shadow-only interface slice。
- v2 formal/live/UI 与正式出价仍不改；v3 promotion 仍不讨论。

## 2026-06-07 checkpoint：v3 practical advisory 实战入口落地

背景：

- 用户明确要求停止继续围绕 CSE/SCP 边缘审计空转，优先形成有实战意义、可在 live/archive 中复盘的 v3 落地入口。
- 当前仍不能把 v3 lane 接入正式出价；但可以把已有 formal/value、underestimate、tail、SCP、CSE 信号汇成 shadow-only advisory，先服务实战观察和局后归因。

本轮动作：

- 新增 `src/bidking_lab/inference/v3/practical_advisory.py`：
  - 输出 `v3_practical_*` 字段；
  - 固定 `affects_bid=false`、`active=false`；
  - formal value / underestimate 候选可以提供 advisory posterior；
  - CSE/SCP broad candidate 只记录 risk，不单独触发 raise-watch；
  - CSE pressure、value/capacity guard、tail candidate 才触发 watch recommendation。
- 将 practical advisory 接入共享 `estimate_shadow_pipeline()`，archive evaluator、live `v3_posterior_shadow`、live `model_eval.jsonl` 与 UI contract diagnostics。
- archive summary 新增：
  - `v3_practical_candidate_rows`
  - `v3_practical_raise_watch_rows`
  - `v3_practical_formal_p50_mae`
  - `v3_practical_delta_formal_p50_mae`
  - `v3_practical_formal_p50_below_rate`
  - `v3_practical_formal_p90_coverage`
- 修正早期 broad risk 误用：首次 smoke 显示 SCP broad candidate 会导致 1495/1560 ready rows 都变成 `raise_watch`，已收窄为 risk-only 记录。
- `scripts/summarize_live_windivert_brief.py` group 表尾部新增 practical candidate/raise-watch rate、practical MAE、delta MAE 与 under-rate，便于局后快速看实战参考效果。

验证命令：

```powershell
C:\Users\shenc\anaconda3\python.exe -m py_compile src\bidking_lab\inference\v3\practical_advisory.py src\bidking_lab\inference\v3\pipeline.py scripts\evaluate_fatbeans_v3_samples.py src\bidking_lab\live\monitor.py src\bidking_lab\runtime\snapshot.py
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_inference_v3_pipeline.py tests\test_evaluate_fatbeans_v3_samples.py::test_v3_prebid_rows_include_prior_and_truth_shadow_fields tests\test_evaluate_fatbeans_v3_samples.py::test_v3_summary_metrics_use_formal_truth_and_prediction tests\test_live_monitor.py::test_build_monitor_artifact_includes_panel_and_eval tests\test_runtime_snapshot.py -q
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_live_windivert_brief.py -q
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
```

验证结果：

```text
py_compile: passed
focused tests: 21 passed
live brief tests: 10 passed

archive smoke:
windows=1577 ready=1560 parse_errors=0
formal_p50_mae=318635.858
formal_p50_below_rate=0.51859
formal_p90_coverage=0.750641
v3_practical_candidate_rows=175
v3_practical_raise_watch_rows=175
v3_practical_active_rows=0
v3_practical_formal_p50_mae=318217.101
v3_practical_delta_formal_p50_mae=-418.757
v3_practical_formal_p50_below_rate=0.517949
v3_practical_formal_p90_coverage=0.751282
```

解读：

- 这是 practical landing slice，不是 promotion；它已经让 v3 在 live/archive/UI contract 中形成可见实战参考。
- 当前 archive 整体提升很小，但方向是正的，且不会破坏正式出价。
- 后续优先用实战样本检查 `v3_practical_recommendation/mode/risk_flags` 是否命中用户感知低估局；若有效，再考虑把 UI 显示进一步前置或做更强 sampler。
- 若后续继续优化，应以 practical candidate 的实战命中率和 low-estimate 修复为主，不再回到 CSE/SCP 单 lane 无限审计。

## 2026-06-07 checkpoint：overlay 显示 v3 practical 实战参考

目标：

- 将已接入 UI contract/model_eval 的 `v3_practical_*` 从“后台字段”推进到实战 overlay 可见层。
- 继续保持正式 baseline 出价卡不变，避免把 shadow-only 参考误认为正式推荐。

本轮动作：

- `scripts/run_live_overlay.py` 新增 `v3 实战参考` section：
  - hover/detail 中显示 recommendation、P50/P90、baseline P50、ΔP50、q6 P50/P90、source lanes、risk flags、confidence 与 reason；
  - `raise_watch` 时进入 alert，提示“低估风险/参考上沿”，但明确“不改正式出价”；
  - `baseline_passthrough` 也保留只读状态，便于确认 v3 当前未触发。
- compact 主决策卡仍只使用 `baseline.decision` 或 fallback 低置信参考，不使用 `v3_practical_*`。
- 补充 overlay/runtime snapshot 单元测试，确保 `active=false`、`affects_bid=false` 的 shadow-only 语义不被 UI 误用。

验证命令：

```powershell
C:\Users\shenc\anaconda3\python.exe -m py_compile scripts\run_live_overlay.py scripts\summarize_live_windivert_brief.py scripts\evaluate_fatbeans_v3_samples.py src\bidking_lab\runtime\snapshot.py src\bidking_lab\live\monitor.py
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_live_overlay.py tests\test_runtime_snapshot.py -q
C:\Users\shenc\anaconda3\python.exe -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_live_windivert_brief.py tests\test_live_monitor.py::test_build_monitor_artifact_includes_panel_and_eval -q
C:\Users\shenc\anaconda3\python.exe scripts\evaluate_fatbeans_v3_samples.py --posterior-trials 64 --format summary
```

验证结果：

```text
py_compile: passed
overlay/runtime snapshot tests: 47 passed
live brief/live monitor focused tests: 11 passed

archive smoke:
windows=1577 ready=1560 parse_errors=0
formal_p50_mae=318635.858
formal_p50_below_rate=0.51859
formal_p90_coverage=0.750641
v3_practical_candidate_rows=175
v3_practical_raise_watch_rows=175
v3_practical_active_rows=0
v3_practical_formal_p50_mae=318217.101
v3_practical_delta_formal_p50_mae=-418.757
v3_practical_formal_p50_below_rate=0.517949
v3_practical_formal_p90_coverage=0.751282
```

解读：

- 本 checkpoint 是实战 UI 可见性推进，不是 sampler promotion。
- 现在实战时可以在 overlay hover/detail 和 alert 中看到 v3 practical 的低估风险提示、证据来源和只读边界。
- 下一步应围绕用户新增实战样本核对 `raise_watch` 的命中率/误导率，并决定是否把更强 sampler 接入 `v3_practical_*`，而不是继续做无落地的边缘审计。

## 2026-06-07 checkpoint：v3 practical q6 prior-floor 上沿 watch

目标：

- 针对 live brief 暴露的持续低估问题，先做一个可落地的 shadow-only 上沿修复：P50 不动，P90 用 q6 先验期望值补一条低估风险上沿。
- 对应实战诉求：不能继续大面积严重低估；但也不能把长尾/先验直接带偏正式 MAE 或正式出价。

本轮动作：

- `src/bidking_lab/inference/v3/practical_advisory.py` 新增 `q6_prior_floor_watch`：
  - 当 `v3_prior_q6_expected_value - baseline q6 formal P90 >= 100,000` 时触发；
  - practical `formal_decision_value_p50` 保持 baseline，不改 MAE；
  - practical `formal_decision_value_p90` 增加 q6 prior gap；
  - practical `q6_formal_decision_value_p90` floor 到 `v3_prior_q6_expected_value`；
  - 固定 `active=false`、`affects_bid=false`，只输出 `raise_watch`/上沿参考。
- 补充 pipeline 单测，覆盖 q6 prior-floor 只抬 P90、不动 P50、不影响正式出价。

验证结果：

```text
pipeline tests: 6 passed
archive/evaluator/live/UI focused tests: 50 passed

archive smoke:
formal_p50_mae=318635.858
formal_p50_below_rate=0.51859
formal_p90_coverage=0.750641
v3_practical_candidate_rows=238
v3_practical_raise_watch_rows=238
v3_practical_active_rows=0
v3_practical_formal_p50_mae=318217.101
v3_practical_delta_formal_p50_mae=-418.757
v3_practical_formal_p50_below_rate=0.517949
v3_practical_formal_p90_coverage=0.764103
```

对比上一 checkpoint：

- `raise_watch_rows`: 175 -> 238。
- `formal P90 coverage`: 0.751282 -> 0.764103。
- `formal P50 MAE`: 318217.101 不变。
- `active_rows`: 0 不变。

解读：

- 这是一个低风险 practical 上沿补强，不是正式 promotion。
- 它明显增加了对 q6 gate inactive / q6 prior-low 一类低估局的提示覆盖，同时避免 P50 MAE 被长尾带偏。
- 仍不足以解决全部实战低估；下一步应继续把 “random_avg floor insufficient / q6 tail value / warehouse underestimated” 这几类转成 practical-only 上沿或 sampler，而不是只改 UI。

## 2026-06-07 checkpoint：v3 practical tail-replacement P90 watch

目标：

- 延续 P90-only practical 策略，把 formal 裁尾后的 `tail_replacement_decision_value_p90` 用作实战上沿参考。
- 继续保持 P50 不动、正式出价不动。

本轮动作：

- `src/bidking_lab/inference/v3/practical_advisory.py` 新增 `tail_replacement_p90_watch`：
  - 当 `tail_replacement_decision_value_p90 - formal_decision_value_p90 >= 50,000` 时触发；
  - practical `formal_decision_value_p90` floor 到 tail replacement P90；
  - practical P50 保持 baseline；
  - 输出 `risk_flags=tail_replacement_p90_watch`，固定 `active=false`、`affects_bid=false`。
- 补充 pipeline 单测，用 confusable q6 long-tail + replacement value 验证该 watch 只抬 P90。

验证结果：

```text
pipeline tests: 7 passed

archive smoke:
formal_p50_mae=318635.858
formal_p90_coverage=0.750641
v3_practical_candidate_rows=347
v3_practical_raise_watch_rows=347
v3_practical_active_rows=0
v3_practical_formal_p50_mae=318217.101
v3_practical_delta_formal_p50_mae=-418.757
v3_practical_formal_p50_below_rate=0.517949
v3_practical_formal_p90_coverage=0.76859
```

对比 q6 prior-floor checkpoint：

- `raise_watch_rows`: 238 -> 347。
- `formal P90 coverage`: 0.764103 -> 0.768590。
- `formal P50 MAE`: 318217.101 不变。
- `active_rows`: 0 不变。

解读：

- tail replacement watch 的收益小于 q6 prior-floor，但能覆盖一批非 prior-gap 的 tail/value 低估风险。
- 当前 practical 仍是实战提示层：P90 更可见，P50 不被长尾带偏。
- 下一步更有价值的方向是 random_avg floor / warehouse under / source-aware sampler，而不是继续扩大所有 weak risk trigger。

## 2026-06-07 checkpoint：v3 practical raise-watch 复盘指标

目标：

- 让 archive 和 live brief 能直接回答 `raise_watch` 是否真的补到低估，而不是只统计触发数量。
- 继续保持 v2 formal、正式出价和 UI baseline 不变。

本轮动作：

- `scripts/evaluate_fatbeans_v3_samples.py` 新增 practical raise-watch 质量指标：
  - `hit`: baseline P90 漏真值，practical P90 覆盖真值；
  - `miss`: baseline P90 漏真值，practical P90 仍漏；
  - `false_alarm`: baseline P90 本来已覆盖，但 practical 仍触发；
  - `extreme_over`: practical P90 超过真值一个 normalized denominator；
  - `misleading`: false alarm 且 extreme over。
- `scripts/summarize_live_windivert_brief.py` 在所有分组表输出同一组 hit/miss/false-alarm/extreme-over/misleading rate。
- 增加 focused 单测，覆盖 hit、miss、false alarm、misleading 场景。

验证结果：

```text
py_compile: passed
focused tests: 12 passed
archive smoke:
v3_practical_raise_watch_rows=347
v3_practical_raise_watch_evaluable_rows=347
v3_practical_raise_watch_hit_rate=0.080692
v3_practical_raise_watch_miss_rate=0.317003
v3_practical_raise_watch_false_alarm_rate=0.602305
v3_practical_raise_watch_extreme_over_rate=0.242075
v3_practical_raise_watch_misleading_rate=0.230548
v3_practical_formal_p90_coverage=0.76859
```

最近 72 小时 live brief：

```text
windivert_rows=59
prebid ready=52 no_state=7
p50_under_rate=0.92
p90_coverage=0.38
v3_practical_raise_watch_evaluable_rows=39
v3_practical_raise_watch_hit_rate=0.15
v3_practical_raise_watch_miss_rate=0.41
v3_practical_raise_watch_false_alarm_rate=0.44
v3_practical_raise_watch_extreme_over_rate=0.0
```

解读：

- 当前 practical P90 watch 能提高覆盖，但补漏命中率偏低，false alarm 和 misleading rate 过高，不能 promotion 到正式出价。
- live 最近样本显示 formal 仍严重偏低，尤其 p50 under-rate 高；下一步应做 source-aware / random_avg / q6 tail-value practical sampler，而不是继续扩大 weak watch。
- 新指标将作为后续 sampler 的 stop-loss：实战可用候选必须降低 miss，并控制 false_alarm/misleading，不能只提高 P90 coverage。

## 2026-06-07 checkpoint：v3 practical random-avg value floor

目标：

- 把此前只作为 diagnostic 的 `public random_n_avg_value` 证据接入 v3 practical，而不是继续遗漏有用公开信息。
- 只作为 practical reference；不改 v2 formal、不改正式出价。

本轮动作：

- `estimate_shadow_pipeline(..., evidence_events=...)` 新增可选 evidence events 输入，只传给 practical advisory。
- `v3_practical` 新增 `random_avg_value_floor_watch`：
  - 从 `random_n_avg_value` 读取样本数和均价；
  - 计算样本总值下界 `n * avg`；
  - 若超过 practical P90 50,000 以上，触发 `raise_watch`；
  - 若只超过 practical P50 100,000 以上，只给 `ceiling_watch`，不制造 alert。
- live monitor 和 archive evaluator 都传入同一 canonical evidence events。
- 增加 pipeline 单测，覆盖 P90 alert 与 P50-only ceiling 两条路径。

验证结果：

```text
py_compile: passed
focused pipeline tests: 4 passed
archive smoke:
v3_practical_candidate_rows=348
v3_practical_raise_watch_rows=347
v3_practical_raise_watch_hit_rate=0.080692
v3_practical_raise_watch_false_alarm_rate=0.602305
v3_practical_formal_p50_mae=317899.874
v3_practical_delta_formal_p50_mae=-735.984
v3_practical_formal_p50_below_rate=0.517949
v3_practical_formal_p90_coverage=0.76859
```

对比上一 checkpoint：

- `candidate_rows`: 347 -> 348。
- `raise_watch_rows`: 347 -> 347，未增加 alert 负担。
- `P50 MAE`: 318217.101 -> 317899.874，小幅改善。
- `P90 coverage`: 0.768590 不变。

解读：

- 该改动主要修复“公开 random avg 证据未进入 v3 practical”的输入遗漏，不是强 sampler。
- 默认 archive 中该信号大多与 q6 prior-floor 重叠，所以全局收益小；但它让后续 live 样本中 random avg 低估局有可见 practical P50/P90 下界。
- 下一步仍需更实质的 q6 tail-value / count-cell-value practical sampler，才能明显降低严重低估。

## 2026-06-07 checkpoint：v3 practical q6 residual ceiling/raise 分层

目标：

- 把现有 residual count-cell-value shadow 中较有价值的 q6 value 上抬信号接入 `v3_practical_*`，形成可见实战参考。
- 同时降低 weak watch 的告警等级，避免把 tail/risk broad signal 伪装成强 `raise_watch`。
- 继续保持 v2 formal、正式 bid、正式出价不变。

本轮动作：

- `advise_practical_report` 新增接收 `residual_posterior` / `ccv_component_posterior`。
- 新增 `q6_value_ceiling_watch`：
  - 默认用 residual/component 相对 baseline 的 q6 value P50/P90 差额；
  - `P50 gap >= 100,000` 且 `P90 gap >= 100,000` 时给 practical 数值上沿；
  - `P50 gap >= 200,000` 且 `P90 gap >= 200,000` 时才作为强 `raise_watch`；
  - practical delta cap 为 `400,000`，避免单个长尾把 UI 上沿拉飞；
  - 固定 `active=false`、`affects_bid=false`。
- 将 tail replacement P90 watch 从 `raise_watch` 降为 `ceiling_watch`。
- 将 capacity/value 无数值 broad risk 从 `raise_watch` 降为 `risk_watch`。
- 将 archive-learned underestimate repair 从 `raise_watch` 降为 `ceiling_watch`。
- overlay 文案区分：
  - `raise_watch`: “低估风险”；
  - `ceiling_watch`: “参考上沿”；
  - `risk_watch`: “证据/容量风险”。

验证结果：

```text
py_compile: passed
focused tests: 66 passed
archive smoke (--posterior-trials 64):
v3_practical_candidate_rows=389
v3_practical_raise_watch_rows=82
v3_practical_raise_watch_evaluable_rows=82
v3_practical_raise_watch_hit_rate=0.280488
v3_practical_raise_watch_miss_rate=0.536585
v3_practical_raise_watch_false_alarm_rate=0.182927
v3_practical_raise_watch_extreme_over_rate=0.146341
v3_practical_raise_watch_misleading_rate=0.097561
v3_practical_active_rows=0
v3_practical_formal_p50_mae=316904.870
v3_practical_delta_formal_p50_mae=-1730.988
v3_practical_formal_p50_below_rate=0.502564
v3_practical_formal_p90_coverage=0.772436
```

对比 random_avg checkpoint：

- `candidate_rows`: 348 -> 389。
- `raise_watch_rows`: 347 -> 82，强提醒显著收窄。
- `raise_watch_hit_rate`: 0.080692 -> 0.280488。
- `raise_watch_false_alarm_rate`: 0.602305 -> 0.182927。
- `raise_watch_misleading_rate`: 0.230548 -> 0.097561。
- `P50 MAE`: 317899.874 -> 316904.870。
- `P50 below-rate`: 0.517949 -> 0.502564。
- `P90 coverage`: 0.768590 -> 0.772436。

解读：

- 这是 v3 practical 第一轮实质性“实战落地”改进：不是提高所有 alert，而是把强提醒和参考上沿分开。
- residual q6 value 对全局 MAE/低估率有小幅正收益，但还不能进入 formal；false/miss 仍高，必须继续 shadow-only。
- 下一步应围绕 `q6_tail_value`、`q6_gate_inactive`、Ethan villa random_avg/layout 与 Aisha shipwreck deep/tail 做更具体的 source-aware sampler，不再扩大 weak broad watch。

## 2026-06-07 checkpoint：v3 practical P90 extreme-over stop-loss

目标：

- 给 `ceiling_watch` / risk reference 增加整体 P90 过宽监控，避免后续只看 coverage 上升。
- 保持 v2 formal、正式出价、UI baseline 不变。

本轮动作：

- `scripts/evaluate_fatbeans_v3_samples.py` 新增：
  - `formal_p90_extreme_over_rate`
  - `q6_formal_p90_extreme_over_rate`
  - `v3_practical_formal_p90_extreme_over_rate`
  - `v3_practical_q6_formal_p90_extreme_over_rate`
- `scripts/summarize_live_windivert_brief.py` 新增分组输出：
  - `v3_practical_p90_coverage`
  - `v3_practical_p90_extreme_over_rate`
- focused tests 覆盖 archive 与 live brief 新字段。

验证结果：

```text
py_compile: passed
focused tests: 3 passed
archive smoke (--posterior-trials 64):
formal_p90_coverage=0.750641
formal_p90_extreme_over_rate=0.305128
v3_practical_formal_p90_coverage=0.772436
v3_practical_formal_p90_extreme_over_rate=0.319231

live brief (--since-hours 72):
overall v3_practical_p90_coverage=0.5
overall v3_practical_p90_extreme_over_rate=0.06
```

解读：

- 当前 v3 practical 提高了 P90 coverage，但 archive practical P90 extreme-over 也从 formal 的 0.305128 升到 0.319231。
- 这说明后续 q6 tail/value ceiling 必须先看 extreme-over，不得只因为 coverage 上升就接入 UI 或 promotion。
- 同步模拟的 q6 pressure multiplier 候选 hit 低且 false/extreme 偏高，暂不实装；下一步应做更具体的 source-aware 条件 sampler。

## 2026-06-07 checkpoint：v3 practical random_avg high-signal P90 ceiling

目标：

- 利用已验证较干净的公开 `random_n_avg_value` 高均值信号，减少实战中使用普品/随机均值信息后 practical P90 仍严重低估的问题。
- 只作为 v3 practical shadow-only 上沿提示，不改变 P50、v2 formal、正式出价或 q6 字段归因。

本轮动作：

- `src/bidking_lab/inference/v3/practical_advisory.py` 新增 `random_avg_high_signal_ceiling_watch`：
  - 触发条件：公开 random avg 单次均值至少 `80,000`；
  - 目标上沿：`n * avg * 2.5`；
  - 最小 P90 gap：`100,000`；
  - 单次 P90 delta cap：`400,000`；
  - 只抬 `total/formal/tail_replacement` 的 practical P90，不抬 P50，不抬 q6 子字段。
- 该信号可与 q6 prior floor、random_avg floor、q6 value ceiling 组合，但自身只输出 `ceiling_watch`，不新增强 `raise_watch`。
- 新增 focused test，锁住 `active=false`、`affects_bid=false`、P50 delta 为 0、q6 delta 为 0。

验证结果：

```text
py_compile: passed
focused tests: 16 passed
archive smoke (--posterior-trials 64):
v3_practical_candidate_rows=397
v3_practical_raise_watch_rows=82
v3_practical_raise_watch_hit_rate=0.280488
v3_practical_raise_watch_misleading_rate=0.097561
v3_practical_formal_p50_mae=316904.870
v3_practical_delta_formal_p50_mae=-1730.988
v3_practical_formal_p50_below_rate=0.502564
v3_practical_formal_p90_coverage=0.776282
v3_practical_formal_p90_extreme_over_rate=0.319231

live brief (--since-hours 72): passed
overall v3_practical_p90_coverage=0.5
overall v3_practical_p90_extreme_over_rate=0.06
```

对比上一 checkpoint：

- `candidate_rows`: 389 -> 397。
- `raise_watch_rows`: 82 -> 82。
- `P50 MAE`: 316904.870 -> 316904.870。
- `P50 below-rate`: 0.502564 -> 0.502564。
- `P90 coverage`: 0.772436 -> 0.776282。
- `P90 extreme-over`: 0.319231 -> 0.319231。

解读：

- 该候选是小幅但干净的实战参考改进：覆盖率提升，没有增加 P50 MAE、强提醒数量或 extreme-over。
- 由于新增覆盖只有 8 个窗口，不能作为 promotion 依据；但可以作为 UI 里的“参考上沿/低估风险”来源。
- 后续核心仍应推进条件化 q6 tail/value sampler：让 random_avg、layout、hero/map/round 与 q6 component likelihood 共同决定是否上移 q6 分布，而不是继续扩大 broad prior。

## 2026-06-07 checkpoint：v3 practical low-support q6 raw-tail ceiling

目标：

- 针对 strict 匹配样本数过少时 q6 formal P90 被单个近邻压低的问题，增加一个受限的 q6 tail/value practical 上沿。
- 继续保持 P90-only、shadow-only，不改变 v2 formal、正式出价或 P50 MAE。

本轮动作：

- `src/bidking_lab/inference/v3/practical_advisory.py` 新增 `q6_raw_tail_low_support_ceiling_watch`：
  - 仅在 `match_scope == strict` 且 `n_matched <= 2` 时触发；
  - 必须已有 tail/value 支持：tail replacement P90 gap 或 formal value floor stress；
  - 使用 raw `q6_value.p90 - q6_formal_decision_value.p90` 作为 tail gap；
  - 最小 gap `200,000`，单次 P90 delta cap `600,000`；
  - 只抬 practical total/formal/tail/q6 formal 的 P90，不抬 P50。
- 与 q6 prior floor、random_avg floor/high-signal、q6 value ceiling 可组合；自身只输出 `ceiling_watch`。
- `scripts/run_live_overlay.py` 的 v3 实战参考区补充显示 `ΔP90` 与 `Δq6P90`，让 P90-only ceiling 在实战 UI 上可见。
- 新增/更新 focused tests，覆盖：
  - low-support raw q6 tail 触发；
  - broad/summary posterior 不触发；
  - overlay ceiling_watch 显示 `ΔP90`。

验证结果：

```text
py_compile: passed
focused tests: 19 passed
archive smoke (--posterior-trials 64):
v3_practical_candidate_rows=397
v3_practical_raise_watch_rows=82
v3_practical_raise_watch_hit_rate=0.353659
v3_practical_raise_watch_miss_rate=0.463415
v3_practical_raise_watch_false_alarm_rate=0.182927
v3_practical_raise_watch_extreme_over_rate=0.146341
v3_practical_raise_watch_misleading_rate=0.097561
v3_practical_formal_p50_mae=316904.870
v3_practical_delta_formal_p50_mae=-1730.988
v3_practical_formal_p50_below_rate=0.502564
v3_practical_formal_p90_coverage=0.780769
v3_practical_formal_p90_extreme_over_rate=0.319231

live brief (--since-hours 72): passed
overall v3_practical_p90_coverage=0.5
overall v3_practical_p90_extreme_over_rate=0.06
```

对比上一 checkpoint：

- `candidate_rows`: 397 -> 397。
- `raise_watch_rows`: 82 -> 82。
- `raise_watch_hit_rate`: 0.280488 -> 0.353659。
- `raise_watch_miss_rate`: 0.536585 -> 0.463415。
- `P50 MAE`: 316904.870 -> 316904.870。
- `P90 coverage`: 0.776282 -> 0.780769。
- `P90 extreme-over`: 0.319231 -> 0.319231。

解读：

- 这是比 broad q6 multiplier 更实用的 sampler：只在 low-support strict posterior 且已有 tail/value 证据时补 P90，不增加强提醒数量或 extreme-over。
- 它不能解决全部 `q6_tail_value` / `q6_gate_inactive` top miss；live brief 仍有 Ethan 2501 layout 与 villa q6 inactive severe miss。
- 下一步应继续把 q6 count/cells 的条件 likelihood 做成 source-aware sampler，重点处理 layout/random_avg 证据下 q6 gate inactive，而不是提升全局 q6 prior。

## 2026-06-07 checkpoint：v3 practical value-stress q6 raw-tail ceiling 与 raw 上限显示

目标：

- 针对 `value_floor_stress` 下 raw q6 value P90 明显高于 formal q6 P90 的窗口，补一个更明确的 P90-only 上沿。
- 同时把 raw total / q6 raw 相对 formal 的 P90 gap 暴露到 `v3_practical_*` 与 overlay，避免实战只看到被裁尾口径压低的 formal P90。
- 继续保持 v2 formal、正式出价、compact 主决策不变。

本轮动作：

- `src/bidking_lab/inference/v3/practical_advisory.py` 新增 `q6_raw_tail_value_stress_ceiling_watch`：
  - 仅在 `formal_value.stress_classes` 含 `value_floor_stress` 时触发；
  - 要求 `q6_value.p90 - q6_formal_decision_value.p90 >= 300,000`；
  - practical P90 delta cap=`300,000`；
  - 只抬 total/formal/tail/q6 formal 的 P90，不抬 P50，不改变 raw q6 value。
- `v3_practical_*` flat contract 新增 raw 上限差值字段：
  - `raw_total_gap_to_formal_p90`
  - `baseline_raw_total_gap_to_formal_p90`
  - `q6_raw_gap_to_formal_p90`
  - `baseline_q6_raw_gap_to_formal_p90`
  - 同步补出 baseline/delta total/q6 raw P90 字段。
- `scripts/run_live_overlay.py` 的 `v3 实战参考` 区增加：
  - hover：`rawΔP90`、`q6rawΔP90`
  - detail：`rawP90`、`q6rawP90`
  - 仍明确显示“只读参考，不影响正式出价”。

验证结果：

```text
py_compile: passed
focused tests: 3 passed
broader focused tests: 21 passed
archive smoke (--posterior-trials 64):
v3_practical_candidate_rows=397
v3_practical_raise_watch_rows=82
v3_practical_raise_watch_hit_rate=0.45122
v3_practical_raise_watch_miss_rate=0.365854
v3_practical_raise_watch_false_alarm_rate=0.182927
v3_practical_raise_watch_extreme_over_rate=0.146341
v3_practical_raise_watch_misleading_rate=0.097561
v3_practical_active_rows=0
v3_practical_formal_p50_mae=316904.870
v3_practical_delta_formal_p50_mae=-1730.988
v3_practical_formal_p50_below_rate=0.502564
v3_practical_formal_p90_coverage=0.785897
v3_practical_formal_p90_extreme_over_rate=0.319231

live brief (--since-hours 72): passed
overall v3_practical_p90_coverage=0.5
overall v3_practical_p90_extreme_over_rate=0.06
```

对比上一 checkpoint：

- `candidate_rows`: 397 -> 397。
- `raise_watch_rows`: 82 -> 82。
- `raise_watch_hit_rate`: 0.353659 -> 0.451220。
- `raise_watch_miss_rate`: 0.463415 -> 0.365854。
- `false_alarm/misleading`: 保持 `0.182927` / `0.097561`。
- `P50 MAE`: 316904.870 -> 316904.870。
- `P90 coverage`: 0.780769 -> 0.785897。
- `P90 extreme-over`: 0.319231 -> 0.319231。

解读：

- 该规则是一个小而实用的补漏：改善强提醒命中和 P90 coverage，不带偏 P50，也不新增正式出价风险。
- 更激进地把 raw/total P90 直接作为 formal P90 的模拟能多覆盖部分 severe miss，但 false/extreme 过高；因此本轮只把 raw 上限作为 UI 可见参考，不把它包装成推荐价。
- 当前最大剩余问题仍是 `q6_gate_inactive`、`q6_tail_value`、summary-likelihood 下 q6 count/cells/value 偏低；下一步应推进 source-aware q6 component sampler，而不是继续调宽 broad capacity/raw 上限。

## 2026-06-07 checkpoint：v3 practical q6 prior tail ceiling

目标：

- 针对 `q6_prior_floor_watch` 已经说明 formal q6 P90 低于先验期望、且别墅/沉船 q6 present 证据很强的窗口，补一个 P90-only tail ceiling。
- 继续不改 P50、不改 v2 formal、不改正式出价；该输出仅作为 `v3_practical_*` 实战风险上限。

本轮动作：

- `src/bidking_lab/inference/v3/practical_advisory.py` 新增 `q6_prior_tail_ceiling_watch` 组合规则：
  - 只在已有 `q6_prior_floor_watch` 后组合；
  - map family 限定为 `villa` / `shipwreck`；
  - 要求 `q6_present_rate >= 0.90`；
  - target=`v3_prior_q6_expected_value * 2.5`；
  - formal q6 P90 gap 至少 `100,000`；
  - practical P90 delta cap=`500,000`；
  - 只抬 total/formal/tail/q6 formal 的 P90，不抬 P50，不改变 raw q6 value。
- 测试补充：
  - 沉船/别墅 q6 prior floor 可组合 tail ceiling；
  - hidden/非目标地图不触发该 tail ceiling；
  - `active=false`、`affects_bid=false` 不变。

验证结果：

```text
py_compile: passed
pytest tests/test_inference_v3_pipeline.py tests/test_live_overlay.py -q:
51 passed

archive smoke (--posterior-trials 64):
v3_practical_candidate_rows=397
v3_practical_raise_watch_rows=82
v3_practical_raise_watch_hit_rate=0.646341
v3_practical_raise_watch_miss_rate=0.170732
v3_practical_raise_watch_false_alarm_rate=0.182927
v3_practical_raise_watch_extreme_over_rate=0.268293
v3_practical_raise_watch_misleading_rate=0.134146
v3_practical_active_rows=0
v3_practical_formal_p50_mae=316904.870
v3_practical_delta_formal_p50_mae=-1730.988
v3_practical_formal_p50_below_rate=0.502564
v3_practical_formal_p90_coverage=0.796154
v3_practical_formal_p90_extreme_over_rate=0.325641

live brief (--since-hours 72):
overall v3_practical_p90_coverage=0.67
overall v3_practical_p90_extreme_over_rate=0.19
```

对比上一 checkpoint：

- `raise_watch_hit_rate`: 0.451220 -> 0.646341。
- `raise_watch_miss_rate`: 0.365854 -> 0.170732。
- `false_alarm_rate`: 保持 `0.182927`。
- `misleading_rate`: 0.097561 -> 0.134146。
- `P50 MAE`: 316904.870 -> 316904.870。
- `P90 coverage`: 0.785897 -> 0.796154。
- `P90 extreme-over`: 0.319231 -> 0.325641。

解读：

- 这是目前最直接改善“实战持续低估”的 P90-only 补漏：强提醒命中明显上升，miss rate 明显下降，P50 不被带偏。
- 代价是 raise-watch extreme-over 与 misleading 上升，尤其 live brief 的 practical extreme-over 从上一轮低位上升；因此它只能作为 UI/审计上的偏保守上限提示，不能 promotion 到正式出价。
- 下一步仍应推进 source-aware q6 count/cells/value sampler：让 layout/random_avg/shape/round 证据决定 q6 分布移动，而不是继续叠加 broad P90 delta。

## 2026-06-07 checkpoint：v3 practical source-profile q6 tail ceiling

目标：

- 从当前 archive top miss 中选一个最窄、可复核且不提高整体 extreme-over 的 source-aware profile，推进到 live/archive 共享 practical 层。
- 本轮只处理 `ethan|2501|public:random_avg+shape`，不做 broad hero/map multiplier。

本轮动作：

- `advise_practical_report()` 增加只读 source context：
  - `hero`
  - `evidence_profile_key`
  - 若未传 profile，则从 canonical evidence events 重建 profile。
- `estimate_shadow_pipeline()` 透传 `hero` 与 `evidence_profile_key`。
- archive evaluator 将已计算的 `evidence_profile_key` 传入 pipeline。
- 新增 `source_profile_q6_tail_ceiling_watch`：
  - rule=`ethan|2501|public:random_avg+shape`；
  - `q6_present_rate >= 0.85`；
  - `total_value.p90 - formal_decision_value.p90 >= 100,000`；
  - practical P90 delta=`400,000`；
  - 只抬 total/formal/tail/q6 formal P90，不抬 P50，不改变 raw q6 value；
  - `active=false`、`affects_bid=false`。

验证结果：

```text
py_compile: passed
pytest tests/test_inference_v3_pipeline.py tests/test_live_overlay.py -q:
53 passed

archive smoke (--posterior-trials 64):
v3_practical_candidate_rows=409
v3_practical_raise_watch_rows=97
v3_practical_raise_watch_hit_rate=0.649485
v3_practical_raise_watch_miss_rate=0.175258
v3_practical_raise_watch_false_alarm_rate=0.175258
v3_practical_raise_watch_extreme_over_rate=0.226804
v3_practical_raise_watch_misleading_rate=0.113402
v3_practical_active_rows=0
v3_practical_formal_p50_mae=316904.870
v3_practical_delta_formal_p50_mae=-1730.988
v3_practical_formal_p50_below_rate=0.502564
v3_practical_formal_p90_coverage=0.802564
v3_practical_formal_p90_extreme_over_rate=0.325641

live brief (--since-hours 72):
overall v3_practical_p90_coverage=0.67
overall v3_practical_p90_extreme_over_rate=0.19
```

对比上一 checkpoint：

- `candidate_rows`: 397 -> 409。
- `raise_watch_rows`: 82 -> 97。
- `raise_watch_hit_rate`: 0.646341 -> 0.649485。
- `raise_watch_miss_rate`: 0.170732 -> 0.175258，因新增 raise-watch 分母扩大而小幅回升。
- `false_alarm_rate`: 0.182927 -> 0.175258。
- `raise_watch_extreme_over_rate`: 0.268293 -> 0.226804。
- `misleading_rate`: 0.134146 -> 0.113402。
- `P50 MAE`: 316904.870 -> 316904.870。
- `P90 coverage`: 0.796154 -> 0.802564。
- `P90 extreme-over`: 保持 `0.325641`。

解读：

- 该规则是第一个落到 shared pipeline 的 source-profile practical sampler：收益不大但非常干净，整体 P90 coverage 提升且 extreme-over 不恶化。
- 它没有改善 72h live brief，因为最近 live top miss 不包含这个具体 archive profile；这说明规则足够窄，不会在无关局里乱抬。
- 下一步可按同样方式处理 `Aisha 2506 item+shape/shape` 或 `Ethan 2401 item+shape/layout`，但必须逐个 profile 用 coverage/extreme/misleading 评估，避免 broad 规则回潮。

## 2026-06-07 checkpoint：v3 practical Ethan 2506 shape source-profile ceiling

目标：

- 继续按单 profile 方式推进 source-aware practical sampler，避免回到 broad q6 multiplier。
- 复核 `Aisha 2506` 与 `Ethan 2401` 后，只接入当前更干净的 `ethan|2506|shape`；Aisha 2506/Ethan 2401 暂不接入。

候选复核：

- `Aisha 2506 item+shape`：20 行、9 miss，raw/q6 gap 明显，但 false/misleading 随 P90 delta 明显上升，不适合直接做 raise-watch。
- `Aisha 2506 shape`：4 行、2 miss，只有一个 raw-gap 严格条件下的干净补点，样本太少，收益太小，暂不接入。
- `Ethan 2401 item+shape`：27 行、8 miss，under 很大，但 raw/q6 gap 多数为 0；用 P90 delta 硬抬会制造大量 false/misleading，说明它更需要 q6 count/cells 条件化，不适合 source-profile ceiling。
- `Ethan 2506 shape`：13 行、8 miss；条件 `raw_total_gap >= 100,000` 且 `q6_present_rate >= 0.85` 命中 8 行，覆盖约 7 个 miss，false 约 1，整体 extreme-over 不增加。

本轮动作：

- 在 `source_profile_q6_tail_ceiling_watch` 规则表新增：
  - key=`ethan|2506|shape`；
  - `q6_present_rate >= 0.85`；
  - `total_value.p90 - formal_decision_value.p90 >= 100,000`；
  - practical P90 delta=`500,000`；
  - 只抬 practical total/formal/tail/q6 formal P90，不抬 P50，不改变 raw q6 value；
  - `active=false`、`affects_bid=false`。
- 新增测试覆盖该 source profile 的 500,000 P90 delta 与 P50/正式状态不变。

验证结果：

```text
py_compile: passed
pytest tests/test_inference_v3_pipeline.py tests/test_live_overlay.py -q:
54 passed

archive smoke (--posterior-trials 64):
v3_practical_candidate_rows=413
v3_practical_raise_watch_rows=105
v3_practical_raise_watch_hit_rate=0.666667
v3_practical_raise_watch_miss_rate=0.161905
v3_practical_raise_watch_false_alarm_rate=0.171429
v3_practical_raise_watch_extreme_over_rate=0.209524
v3_practical_raise_watch_misleading_rate=0.104762
v3_practical_active_rows=0
v3_practical_formal_p50_mae=316904.870
v3_practical_delta_formal_p50_mae=-1730.988
v3_practical_formal_p50_below_rate=0.502564
v3_practical_formal_p90_coverage=0.807051
v3_practical_formal_p90_extreme_over_rate=0.325641

live brief (--since-hours 72):
overall v3_practical_p90_coverage=0.67
overall v3_practical_p90_extreme_over_rate=0.19
```

对比上一 checkpoint：

- `candidate_rows`: 409 -> 413。
- `raise_watch_rows`: 97 -> 105。
- `raise_watch_hit_rate`: 0.649485 -> 0.666667。
- `raise_watch_miss_rate`: 0.175258 -> 0.161905。
- `false_alarm_rate`: 0.175258 -> 0.171429。
- `raise_watch_extreme_over_rate`: 0.226804 -> 0.209524。
- `misleading_rate`: 0.113402 -> 0.104762。
- `P50 MAE`: 316904.870 -> 316904.870。
- `P90 coverage`: 0.802564 -> 0.807051。
- `P90 extreme-over`: 保持 `0.325641`。

解读：

- 该规则是更实用的 source-profile 补漏：小幅提升 coverage，同时 raise-watch 质量整体改善。
- live 72h 仍未变化，说明当前新增 profile 没有命中最近 live 样本；后续实战遇到 Ethan 2506 shape 时应观察 v3 practical 上沿是否有帮助。
- Aisha 2506/Ethan 2401 暂不落规则本身也是结论：它们需要更真实的 q6 count/cells/value 条件 sampler，而不是继续 P90 delta 硬补。

## 2026-06-07 checkpoint：v3 practical Ethan 2401 dense-shape source-profile ceiling

目标：

- 继续处理别墅 `Ethan 2401 item+shape` 的严重低估，但不做 broad `Ethan 2401` 或 broad q6 multiplier。
- 先用可解释的 shape evidence density 作为 shadow-only practical 上沿，验证是否能改善 miss 而不放大误导。

候选复核：

- 现有 `v3_ccv`、`v3_resid`、`v3_cal`、`v3_under`、`v3_tail_review`、`v3_fv` 对当前 `Ethan 2401 item+shape` top miss 基本没有帮助，P90 仍维持低位。
- 该 profile 共 27 行、8 个 practical P90 miss；多数 raw total gap 与 q6 raw gap 为 0，所以不适合继续用 raw-gap ceiling。
- 条件 `shape_anchors >= 33` 命中 6 行，6 行全部是 miss，0 个非 miss；这说明问题更像 dense shape evidence 下 q6 count/cells/value posterior 被压低，而不是通用 tail gap。

本轮动作：

- 在 `source_profile_q6_tail_ceiling_watch` 规则表新增：
  - key=`ethan|2401|item+shape`；
  - `shape_anchors >= 33`；
  - 不要求 `q6_present_rate` 或 raw total gap；
  - practical P90 delta=`1,000,000`；
  - 只抬 practical total/formal/tail/q6 formal P90，不抬 P50，不改变 raw q6 value；
  - `active=false`、`affects_bid=false`。
- shared v3 pipeline 透传 `shape_anchor_count`，archive/live 共用同一 practical 层。
- 新增测试覆盖 `shape_anchors=33` 命中和 `shape_anchors=32` 不命中，防止规则退化成 broad profile。

验证结果：

```text
py_compile: passed
pytest tests/test_inference_v3_pipeline.py tests/test_live_overlay.py -q:
56 passed

archive smoke (--posterior-trials 64):
v3_practical_candidate_rows=419
v3_practical_raise_watch_rows=111
v3_practical_raise_watch_hit_rate=0.684685
v3_practical_raise_watch_miss_rate=0.153153
v3_practical_raise_watch_false_alarm_rate=0.162162
v3_practical_raise_watch_extreme_over_rate=0.198198
v3_practical_raise_watch_misleading_rate=0.099099
v3_practical_active_rows=0
v3_practical_formal_p50_mae=316904.870
v3_practical_delta_formal_p50_mae=-1730.988
v3_practical_formal_p50_below_rate=0.502564
v3_practical_formal_p90_coverage=0.810897
v3_practical_formal_p90_extreme_over_rate=0.325641

live brief (--since-hours 72):
overall v3_practical_p90_coverage=0.67
overall v3_practical_p90_extreme_over_rate=0.19
```

对比上一 checkpoint：

- `candidate_rows`: 413 -> 419。
- `raise_watch_rows`: 105 -> 111。
- `raise_watch_hit_rate`: 0.666667 -> 0.684685。
- `raise_watch_miss_rate`: 0.161905 -> 0.153153。
- `false_alarm_rate`: 0.171429 -> 0.162162。
- `raise_watch_extreme_over_rate`: 0.209524 -> 0.198198。
- `misleading_rate`: 0.104762 -> 0.099099。
- `P50 MAE`: 316904.870 -> 316904.870。
- `P90 coverage`: 0.807051 -> 0.810897。
- `P90 extreme-over`: 保持 `0.325641`。

解读：

- 这是第一个 evidence-density source-profile ceiling：它利用 shape anchor 数量，而不是只看 hero/map/profile。
- 指标表现符合实战目标：P90 coverage 提升，raise-watch 各项质量改善，P50 MAE 不变，整体 P90 extreme-over 不变。
- 该规则仍然只是 practical shadow 上沿；真正 v3 sampler 仍应把 q6 count/cells/value posterior 条件化，而不是继续叠加固定 delta。

## 2026-06-07 checkpoint：v3 practical Aisha 2506 dense item+shape ceiling

目标：

- 针对当前非 hidden 剩余低估簇继续落地 practical 上沿，优先处理 `Aisha 2506 item+shape`。
- 避免接入噪音更大的 `Aisha 2501 item+shape` broad 规则；先选择 false/misleading 更可控的沉船 profile。

候选复核：

- 当前 practical 后剩余 top clusters 中，非 hidden 主要包括：
  - `Aisha 2501 item+shape`：75 行、22 miss，但 broad delta 会带来 misleading；
  - `Aisha 2506 item+shape`：20 行、9 miss，其中 dense item+shape 子集更干净；
  - hidden `Aisha 2601` 暂不作为主优化目标。
- 对 `Aisha 2506 item+shape` 扫描后，条件 `shape_anchors >= 28` 且 `item_anchors >= 4` 命中 4 行：
  - 3 行是 practical P90 miss；
  - `500,000` P90 delta 覆盖这 3 行；
  - 1 行 false alarm；
  - 0 个新增 extreme-over，0 个 misleading。

本轮动作：

- 在 `source_profile_q6_tail_ceiling_watch` 规则表新增：
  - key=`aisha|2506|item+shape`；
  - `shape_anchors >= 28`；
  - `item_anchors >= 4`；
  - 不要求 `q6_present_rate` 或 raw total gap；
  - practical P90 delta=`500,000`；
  - 只抬 practical total/formal/tail/q6 formal P90，不抬 P50，不改变 raw q6 value；
  - `active=false`、`affects_bid=false`。
- shared v3 pipeline 新增透传 `item_anchor_count`。
- `bounded_underestimate_repair` 分支现在可以组合 source-profile ceiling；命中 source-profile 时 recommendation 升级为 `raise_watch`，否则保持原 `ceiling_watch`。
- 新增测试覆盖 Aisha 2506 dense item+shape 命中、item anchors 不足不命中、underestimate 分支叠加 source-profile。

验证结果：

```text
py_compile: passed
pytest tests/test_inference_v3_pipeline.py tests/test_live_overlay.py -q:
58 passed

archive smoke (--posterior-trials 64):
v3_practical_candidate_rows=419
v3_practical_raise_watch_rows=115
v3_practical_raise_watch_hit_rate=0.686957
v3_practical_raise_watch_miss_rate=0.147826
v3_practical_raise_watch_false_alarm_rate=0.165217
v3_practical_raise_watch_extreme_over_rate=0.191304
v3_practical_raise_watch_misleading_rate=0.095652
v3_practical_active_rows=0
v3_practical_formal_p50_mae=316904.870
v3_practical_delta_formal_p50_mae=-1730.988
v3_practical_formal_p50_below_rate=0.502564
v3_practical_formal_p90_coverage=0.812821
v3_practical_formal_p90_extreme_over_rate=0.325641

live brief (--since-hours 72):
overall v3_practical_p90_coverage=0.67
overall v3_practical_p90_extreme_over_rate=0.19
```

对比上一 checkpoint：

- `candidate_rows`: 419 -> 419。
- `raise_watch_rows`: 111 -> 115。
- `raise_watch_hit_rate`: 0.684685 -> 0.686957。
- `raise_watch_miss_rate`: 0.153153 -> 0.147826。
- `false_alarm_rate`: 0.162162 -> 0.165217。
- `raise_watch_extreme_over_rate`: 0.198198 -> 0.191304。
- `misleading_rate`: 0.099099 -> 0.095652。
- `P50 MAE`: 316904.870 -> 316904.870。
- `P90 coverage`: 0.810897 -> 0.812821。
- `P90 extreme-over`: 保持 `0.325641`。

解读：

- 这条规则的收益是小而实用：coverage 继续提升，miss/extreme/misleading 降低，但 false alarm 率小幅上升。
- 因为它会把部分 underestimate-only ceiling 升级为 raise-watch，所以只适合 v3 practical shadow，不适合 formal 或正式出价。
- 下一个主线仍应是 q6 count/cells/value 条件 sampler；继续加固定 delta 的边际收益正在下降。

## 2026-06-07 checkpoint：v3 practical UI contract 上沿字段补齐

目标：

- 让 live overlay 实际看到 v3 practical 已经计算出的上沿和 gap 字段。
- 明确区分正式 baseline 与 v3 practical shadow 参考，避免用户只看到正式裁尾值而错过低估风险/仓库上沿。

发现：

- `run_live_overlay.py` 的 v3 practical section 已经会显示：
  - `ΔP90`
  - `rawΔP90`
  - `q6rawΔP90`
  - detail hover 中的 `rawP90` / `q6rawP90`
- 但 `runtime.snapshot.ui_contract_from_artifact()` 只透传了部分 `v3_practical_*` 字段：
  - 有 `formal_decision_value_p90`、`delta_formal_decision_value_p50`；
  - 缺少 `delta_formal_decision_value_p90`、raw/total/q6 raw gap、baseline P90、q6 baseline/delta P90 等。
- 结果是 archive/live 已经算出的 practical 上沿无法完整进入 overlay UI contract。

本轮动作：

- `diagnostics.v3_practical` 新增透传：
  - formal baseline P90 与 delta P90；
  - total raw P90、baseline raw P90、delta raw P90；
  - raw total gap 相对 formal P90；
  - q6 formal baseline P50/P90 与 delta P90；
  - q6 raw value P90、baseline q6 raw P90、delta q6 raw P90；
  - q6 raw gap 相对 q6 formal P90。
- 更新 runtime snapshot 测试，确保这些字段不会再被 UI contract 丢弃。

验证结果：

```text
py_compile: passed
pytest tests/test_runtime_snapshot.py tests/test_live_overlay.py -q:
48 passed

archive smoke (--posterior-trials 64):
v3_practical_raise_watch_rows=115
v3_practical_raise_watch_hit_rate=0.686957
v3_practical_raise_watch_miss_rate=0.147826
v3_practical_raise_watch_false_alarm_rate=0.165217
v3_practical_raise_watch_extreme_over_rate=0.191304
v3_practical_raise_watch_misleading_rate=0.095652
v3_practical_formal_p50_mae=316904.870
v3_practical_formal_p90_coverage=0.812821
v3_practical_formal_p90_extreme_over_rate=0.325641

live brief (--since-hours 72):
overall v3_practical_p90_coverage=0.67
overall v3_practical_p90_extreme_over_rate=0.19
```

解读：

- 这是实战落地层面的修复：不改变任何 formal/v2/正式出价，也不改变 practical 数值，只保证 UI contract 能完整携带 practical 上沿信息。
- overlay 已有 shadow-only 文案和 `active/affects_bid` 检查；补齐字段后，用户能同时看到正式 baseline 与 v3 上沿/仓库风险。
- 后续新增 practical sampler 时，必须同步检查 `to_flat_dict()`、`model_eval`、`runtime snapshot`、overlay section 四段字段是否贯通。

## 2026-06-07 checkpoint：live brief top miss 区分 baseline 与 v3 practical P90

目标：

- 修正 `top_p90_misses` 的诊断口径，避免只看正式 baseline P90 而误判 v3 practical 没有生效。
- 保持 v2 formal、正式出价、v3 practical 数值和 UI 行为不变，只增强评估/brief 输出。

发现：

- live 72h top miss 中，部分行的正式 baseline P90 极低，但 v3 practical 已经把 P90 抬高到接近真实值。
- 原 brief 只输出 `decision_value_p90`，没有并排输出 `v3_practical_formal_decision_value_p90`，容易把“practical 已修但仍有残余 under”误读成“practical 完全没覆盖”。

本轮动作：

- `top_p90_misses` 新增：
  - `v3_practical_p90`
  - `v3_practical_under_by`
  - `v3_practical_delta_p90`
  - `v3_practical_recommendation`
  - `v3_practical_source`
  - `v3_practical_risk_flags`
- 文本 brief 的 top miss CSV 也同步输出这些字段。
- 测试覆盖 baseline P90 miss 但 practical P90 已覆盖的样例。

验证结果：

```text
py_compile: passed
pytest tests/test_summarize_live_windivert_brief.py -q:
10 passed

live brief --since-hours 72 --format json: passed
live brief --since-hours 72: passed
```

当前解读：

- 72h live top miss 的 Ethan 2501 layout 行，baseline P90 约 19-21 万，但 v3 practical P90 已抬到约 116.9 万；真实仍约 133.8 万，残余 under 约 16.9 万。
- Aisha 2404 / Ethan 2401 的若干 top miss 也从“baseline severe miss”变成“practical 已抬高但仍有 9-19 万残余 under”。
- 下一步 sampler 不应只继续加 broad fixed delta；更有价值的是针对 practical 残余缺口做 q6 tail/value 的 source-aware 小幅上沿，或把这类残余以 UI 低估风险提示表达。

## 2026-06-07 checkpoint：q6 prior tail practical 上限收口到实战可用

目标：

- 不再继续做过细参数搜索；只落地一个对实战低估有明确收益、仍保持 shadow-only 的 practical 改动。
- 解决 live 72h 中 Ethan 2501 layout 已被 practical 抬高但仍残余 under 的问题。

本轮动作：

- 将 `q6_prior_tail_ceiling` 的单次 P90 delta cap 从 `500,000` 提高到 `750,000`。
- 触发条件不放宽：
  - 仍要求 `q6_prior_floor_watch` 已触发；
  - 仍只限 villa / shipwreck；
  - 仍要求 q6 present rate 达到门槛；
  - 仍然 `active=false`、`affects_bid=false`，不进入 formal 或正式出价。

验证结果：

```text
pytest tests/test_inference_v3_pipeline.py -q:
24 passed

archive smoke (--posterior-trials 64):
v3_practical_raise_watch_hit_rate=0.704348
v3_practical_raise_watch_miss_rate=0.130435
v3_practical_raise_watch_false_alarm_rate=0.165217
v3_practical_raise_watch_extreme_over_rate=0.200000
v3_practical_raise_watch_misleading_rate=0.095652
v3_practical_formal_p50_mae=316904.870
v3_practical_formal_p90_coverage=0.814103
v3_practical_formal_p90_extreme_over_rate=0.326282

live brief (--since-hours 72):
overall v3_practical_p90_coverage=0.75
overall v3_practical_p90_extreme_over_rate=0.19
```

对比上一 checkpoint：

- archive `raise_watch_miss_rate`: `0.147826` -> `0.130435`。
- archive `P90 coverage`: `0.812821` -> `0.814103`。
- archive `P50 MAE`: 不变。
- archive `false_alarm_rate` 与 `misleading_rate`: 不变。
- archive `raise_watch_extreme_over_rate`: `0.191304` -> `0.200000`，小幅上升。
- live 72h `v3_practical_p90_coverage`: `0.67` -> `0.75`，`v3_practical_p90_extreme_over_rate` 保持 `0.19`。

当前解读：

- 这不是 promotion，也不是正式估价重写；它只是让实战 UI 的 v3 practical 上沿更少持续低估。
- Ethan 2501 layout 的 4 个 top miss 从 residual under 约 `168,754` 变为 practical P90 覆盖。
- 剩余 top miss 主要是 Aisha 2404 / Ethan 2401 的 q6 gate / q6 undercovered 残余，不建议继续盲目 broad delta；后续优先通过 UI 风险表达和实战观察决定是否再加窄口径规则。

## 2026-06-07 checkpoint：overlay 明确并排显示 formal baseline 与 v3 practical P90

目标：

- 推进实战落地，不继续细调 sampler 参数。
- 让用户在 overlay 中直接看到“正式 baseline P90”和“v3 practical 上沿 P90”的区别，避免把 v3 practical 误认为正式出价。

本轮动作：

- `v3 实战参考` hover/detail 文案改为并排展示：
  - `正式P90 ... -> v3P90 ...`
  - `ΔP90 ...`
  - `rawΔP90` / `q6rawΔP90`
  - detail 中的 `正式P50`、`正式q6P90`、`仓库rawP90`、`q6rawP90`
- v3 practical alert 也同步显示 `正式P90 -> v3P90`。
- 新增集成测试，覆盖 `model_eval.v3_practical_* -> ui_contract -> overlay`，确保不是只测手写 UI contract。

验证结果：

```text
py_compile: passed
pytest tests/test_live_overlay.py tests/test_runtime_snapshot.py tests/test_summarize_live_windivert_brief.py -q:
59 passed

live brief --since-hours 72 --format json: passed
overall v3_practical_p90_coverage=0.75
overall v3_practical_p90_extreme_over_rate=0.19
```

当前解读：

- 这是纯 UI/contract 可读性改动，不改变 v2 formal、正式出价或 v3 practical 数值。
- 实战面板现在更符合当前阶段目标：第一屏/hover 可以同时看正式 baseline、v3 practical 上沿、delta、来源和只读状态。
- 后续优先继续做链路稳定和用户可读提示；除非新增实战样本显示系统性偏差，不再围绕小参数做连续细搜。

## 2026-06-07 checkpoint：post_game brief 增加 v3 practical shadow 汇总

目标：

- 继续推进实战落地，不改变 v2 formal、正式出价或 v3 practical 数值。
- 让 `post_game_live.ps1` 调用的 `summarize_live_model_eval.py --brief` 能直接显示 v3 practical 的实战参考价值和边界。

本轮动作：

- `summarize_live_model_eval.py` 新增 `v3_practical` 聚合块：
  - rows / available / ready / candidate；
  - active_rows / affects_bid_rows，用于确认 shadow-only 边界；
  - recommendation / confidence / source / source_lanes / risk_flags 计数；
  - formal P90 与 q6 formal P90 的 baseline vs practical 覆盖、残余 under、helped/still_missed、extreme-over；
  - raise_watch 的 hit / miss / false_alarm / extreme_over / misleading。
- `brief_summary()` 保留该聚合块；当当前日志没有 v3 practical 字段时，输出 `status=no_v3_practical_fields` 与中文 note，并只保留 rows 与 shadow 边界，避免 post-game brief 被空子结构刷屏。
- 新增单元测试覆盖 synthetic `raise_watch` hit、false alarm、misleading、q6 residual under 与 `brief_summary` 透传。

验证结果：

```text
py_compile scripts/summarize_live_model_eval.py tests/test_summarize_live_model_eval.py: passed
pytest tests/test_summarize_live_model_eval.py -q:
19 passed

summarize_live_model_eval.py --brief: passed
current model_eval v3_practical.rows=0  (当前日志为旧字段集，没有 v3_practical)

summarize_live_windivert_brief.py --since-hours 72 --format json: passed
overall v3_practical_p90_coverage=0.69
overall v3_practical_p90_extreme_over_rate=0.07
```

当前解读：

- 这是 post-game 可读性和 contract 汇总改动，不是 sampler 调参，也不接入正式出价。
- 当前 `model_eval.jsonl` 去重有效行没有 v3 practical 字段，所以新 brief 块为空；72h windivert/prebid archive 路径仍能看到 practical 指标。
- 后续用最新 monitor 采集的新局会自然进入 `model_eval --brief` 的 v3 practical 汇总，便于实战后快速判断：正式 baseline 是否低估、v3 practical 是否覆盖、是否有 misleading/extreme-over 风险。

## 2026-06-07 checkpoint：overlay v3 practical 标签改为实战可读口径

目标：

- 保持 v2 formal、正式出价、UI 布局和 v3 practical 数值不变。
- 让 overlay 的 v3 practical 提示更容易在实战中扫读，避免内部字段名影响理解。

本轮动作：

- `v3 实战参考` 区块将内部标签改为中文语义：
  - `confidence low_medium` -> `置信 中低`；
  - `rawΔP90` -> `仓库上限ΔP90`；
  - `q6rawΔP90` -> `q6上限ΔP90`；
  - detail 中的 `rawP90/q6rawP90` -> `仓库上限P90/q6上限P90`；
  - source/risk 增加 `证据` / `风险` 前缀。
- 不修改 UI contract 字段名，不改变 model_eval、sampler、formal 或 bid path。

验证结果：

```text
py_compile scripts/run_live_overlay.py tests/test_live_overlay.py: passed
pytest tests/test_live_overlay.py tests/test_runtime_snapshot.py -q:
49 passed
```

当前解读：

- 这是纯展示语义修复，目标是让实战用户更快分清：正式 baseline、v3 上沿、低估风险、证据来源、置信度、仓库上限和只读边界。
- 后续如果新增 practical 字段，应同步检查“字段是否贯通”和“展示标签是否能被非开发视角理解”。

## 2026-06-07 checkpoint：post_game model_eval brief 使用同一时间窗口

目标：

- 保持 v2 formal、正式出价、UI 基线和 v3 practical 数值不变。
- 让 post-game 复盘的 windivert brief 与 model_eval brief 使用相同 `SinceHours`，避免全量旧日志干扰新局判断。

本轮动作：

- `summarize_live_model_eval.py` 新增 `--since-hours`：
  - 同时过滤 `model_eval.jsonl` 与 `monitor_errors.jsonl`；
  - brief 输出 `window.since_hours`、输入行数、选中行数；
  - v3 practical 状态区分 `no_evaluable_rows` 与 `no_v3_practical_fields`。
- `post_game_live.ps1` 将同一个 `$SinceHours` 传给 `summarize_live_model_eval.py --brief --since-hours`。

验证结果：

```text
py_compile scripts/summarize_live_model_eval.py tests/test_summarize_live_model_eval.py: passed
pytest tests/test_summarize_live_model_eval.py -q:
22 passed

summarize_live_model_eval.py --brief --since-hours 72: passed
window.selected_rows=0
v3_practical.status=no_evaluable_rows
```

当前解读：

- 这是实战复盘口径修复，不改变任何估值结果。
- 当前 72h model_eval 窗口没有可评估行，所以 post-game 输出会明确提示 `no_evaluable_rows`；等最新 live monitor 采集新局后，该窗口才会反映新局的 v3 practical 字段。

## 2026-06-07 checkpoint：model_eval brief 增加 v3 practical 具体行复盘

目标：

- 保持 v2 formal、正式出价、UI 基线和 v3 practical 数值不变。
- 让 post-game model_eval brief 在有 v3 practical 数据时，不只显示聚合率，也能定位到具体窗口。

本轮动作：

- `v3_practical` 聚合新增：
  - `latest_rows`：最近 v3 practical 行；
  - `top_under_rows`：v3 practical P90 仍低于 formal truth 的最大残余 under 行。
- 每行包含 file、hero、map_id、round、recommendation、confidence、source/risk、baseline P90、practical P90、delta、残余 under、q6 P90/under、active/affects_bid。
- brief 中保留最多 5 条，避免 post-game 输出过载。

验证结果：

```text
py_compile scripts/summarize_live_model_eval.py tests/test_summarize_live_model_eval.py: passed
pytest tests/test_summarize_live_model_eval.py -q:
22 passed

summarize_live_model_eval.py --brief --since-hours 72: passed
window.selected_rows=0
v3_practical.status=no_evaluable_rows
```

当前解读：

- 当前真实 72h 窗口仍没有 model_eval 行，所以实测不会显示 latest/top rows；synthetic test 覆盖了有数据时的行级复盘。
- 这能让下一批实战样本采完后，post-game 直接回答“哪一轮触发了 v3 practical，抬了多少，还剩多少低估”，不需要再手动翻 JSONL。

## 2026-06-07 checkpoint：model_eval brief CLI 窗口过滤纳入端到端测试

目标：

- 确认 `post_game_live.ps1` 实际调用的 CLI 路径可以正确应用 `--since-hours`，而不只是在 helper 层通过测试。

本轮动作：

- 新增测试使用临时 `model_eval.jsonl` 与 `monitor_errors.jsonl`：
  - 通过 `main()` 运行 `--brief --since-hours 1`；
  - 固定当前时间，验证边界行、新行、旧行过滤；
  - 验证 monitor error 也使用同一窗口；
  - 验证输出的 `v3_practical.latest_rows` 能落到选中的新行。

验证结果：

```text
py_compile tests/test_summarize_live_model_eval.py scripts/summarize_live_model_eval.py: passed
pytest tests/test_summarize_live_model_eval.py -q:
23 passed

summarize_live_model_eval.py --brief --since-hours 72: passed
window.selected_rows=0
v3_practical.status=no_evaluable_rows
```

当前解读：

- 这是实战复盘脚本入口的防回归测试，不改变任何运行时估值或 UI。
- 后续如果修改 argparse、默认 log path、error log 或 post_game 参数，这个测试能更早发现窗口过滤断层。

## 2026-06-07 checkpoint：post_game 默认复盘窗口改为 72h

目标：

- 与当前 v3 practical 验证口径保持一致：archive + 72h live/实战样本。
- 减少局后忘记手动传 `-SinceHours 72` 导致复盘窗口变窄的风险。

本轮动作：

- `scripts/post_game_live.ps1` 默认 `$SinceHours` 从 `24.0` 改为 `72.0`。
- 显式传参仍然可覆盖，例如 `.\scripts\post_game_live.ps1 -SinceHours 24`。

当前解读：

- 这是操作默认值调整，不改变任何 Python summarizer 默认、估值、UI 或正式出价。
- post-game 现在默认与当前 v3 practical readiness/live review 口径一致。

## 2026-06-07 checkpoint：live formal 进入 v3 practical 实战试用

目标：

- 用户明确要求先把 UI/正式建议接到 v3 practical，实战观察具体效果；不继续消耗在非必要细粒度审计。
- 保留 v2 回退能力，避免 v3 practical 在实战中出现 misleading/extreme-over 时无法快速回滚。

对照结论：

- `summarize_live_windivert_brief.py --since-hours 72 --archive-n-trials 10 --archive-shadow-trials 1 --format text` 的最新 24 个 72h prebid 窗口中：
  - v2 formal `estimate_rows=21`，`decision_value_mae=392789.3`；
  - v3 practical `v3_practical_mae=338340.5`，MAE 改善约 54,449；
  - v2 P90 coverage `0.29`，v3 practical P90 coverage `0.62`；
  - P90 extreme-over 从 `0.05` 升到 `0.14`；
  - raise-watch misleading rate `0.11`。
- `summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary` 仍为 `overall_status=not_ready`，所以这不是 v3 全量 promotion。

本轮动作：

- live runner 默认 formal mode 改为 `v3_practical`：
  - `scripts/run_fatbeans_live_monitor.py`
  - `scripts/run_fatbeans_webhook_monitor.py`
  - `scripts/run_windivert_live_monitor.py`
  - `scripts/start_live_windivert_overlay.ps1`
- 底层 `build_monitor_artifact_from_*` 默认仍保持 v2，避免 archive/brief 离线对照口径被污染；live runner 会显式传 `formal_mode=v3_practical`。
- `artifact["bid_rows"]` 现在表示当前正式 UI/建议使用的行：
  - v3 实战试用时来自 `v3 practical formal`；
  - v2 原建议保留在 `artifact["v2_bid_rows"]`；
  - v3 生成行保留在 `artifact["v3_practical_bid_rows"]`。
- `ui_contract` 新增/暴露：
  - `mode=v3_practical_formal_with_v2_reference`；
  - `baseline.source=v3_practical`；
  - `v2_reference` 对照区。
- overlay hover/detail 显示 `正式出价 v3` 与 `v2 对照`；`live_status` 输出 baseline source/formal mode。

验证结果：

```text
py_compile live/runtime/overlay/status runners: passed
pytest tests/test_live_monitor.py tests/test_runtime_snapshot.py tests/test_live_overlay.py tests/test_live_status.py -q:
92 passed

真实 2401 raw capture smoke:
formal_mode=v3_practical
formal_mode_reason=v3_practical_ready
bid_evidence=v3 practical formal
decision_range=214,470 / 396,895 / 886,701
stop=682,078
v2_rows=5
v3_rows=5
contract_mode=v3_practical_formal_with_v2_reference
v2_reference=True
```

当前解读：

- 实战 UI/正式建议现在会按 v3 practical 重算防守价、可追价和停止价。
- 如果实战表现不好，可用 `.\scripts\start_live_windivert_overlay.ps1 -Restart -FormalMode v2 -PortOnly -PythonPath C:\Python313\python.exe` 回退。
- 由于 readiness 仍 not_ready，本阶段后续重点是实战观察和局后复盘，而不是宣称 v3 已可 archive v2。

## 2026-06-07 checkpoint：公共随机品质 reveal 显示补齐

实战反馈：

- map 2404 / Gabriela 局中公共信息给出 `随机显示9件藏品的品质`，用户在小地图上没有看到对应信息。

复核结论：

- 最新 snapshot 中 `public_info_rows` 已解析 `info_id=200028`，包含 9 个 quality-only item：
  - `Q6x1 / Q5x1 / Q4x1 / Q3x3 / Q2x3`。
- v3 约束已利用该输入：
  - `quality_floor_anchors=12`；
  - `v3_summary_q6_count_floor=1`。
- UI 问题不是模型漏用，而是小地图只显示可定位 marker/footprint；已被完整物品覆盖的品质项不再单独画 marker，无坐标项也不能硬画到格子。

修复：

- `ui_contract.minimap` 新增 quality-only reveal 汇总：
  - `quality_reveal_counts`；
  - `quality_reveal_unplaced_counts`；
  - marker/covered/placeable 计数。
- overlay MiniMap 文案显示 `公共品质 ...`；如存在无坐标红货，会显示 `未定位 Q6×N`。

验证：

```text
pytest tests/test_runtime_snapshot.py tests/test_live_overlay.py -q
51 passed

pytest tests/test_live_monitor.py tests/test_runtime_snapshot.py tests/test_live_overlay.py tests/test_live_status.py -q
92 passed
```

## 2026-06-07 checkpoint：public numeric UI 与 live v3 guard

实战反馈：

- Aisha 开局公共信息给出 `紫色品质藏品平均占用格数 2.90`，UI 未展示。
- Gabriela 2407 一局结算约 `226,486`，但 live v3 practical 低置信 raise-watch 曾把 P90 拉到 `495,084`、停止价 `380,835`。
- 当前会话进入 map `2527` 时，本地 BidMap 缺表导致 live monitor 连续 `KeyError: 2527`，snapshot 退成空白。

修复：

- `ui_contract.constraints.public_info` 新增 public numeric soft facts：
  - `public_avg_cells`；
  - `public_avg_values`；
  - `public_random_avg_values`；
  - `public_numeric_summary`。
- overlay “输入约束”行现在显示 `紫均格 2.90`、`金均价 ...`、`随机9均价 ...` 等摘要。
- live monitor 对未知地图改为不中断：
  - `formal_mode_reason=unsupported_map`；
  - `inference_input_constraints.mode=unsupported_map`；
  - 保留 hero/map/session/公开信息等状态，但不生成估值。
- live formal v3 practical 增加低置信 prior-only raise guard：
  - 只在 `raise_watch + low/low_medium + q6_prior/settlement_count/capacity_source 风险 + P90-P50 >= 100k` 且没有强证据旗标时触发；
  - 不改变 v3 audit 原始 practical 字段，只限制 live bid row 的正式 `decision_value P90/stop`；
  - 行内保留 `v3_practical_unguarded_decision_value` 和 `v3_practical_live_guard_reason`。

真实复算：

```text
Gabriela 2407 reset/settled:
truth known_value_sum=226,486
before guard: decision P90=495,084, stop=380,835
after guard:  decision P90=283,240, stop=217,877
formal_mode_reason=v3_practical_ready_live_guarded
```

样本归档：

- `fatbeans_valid_aisha_2405_4rounds_2405_1367517775504199_0002.json`
- `fatbeans_valid_aisha_2410_4rounds_2410_1367517775778076_0003.json`
- `fatbeans_mixed_gabriela_2407_4rounds_2407_1367517776000836_0001.json`

验证：

```text
pytest tests/test_live_monitor.py -q
32 passed

pytest tests/test_runtime_snapshot.py tests/test_live_overlay.py -q
52 passed
```

## 2026-06-07 checkpoint：活动沉船缺表按旧沉船显式别名估值

实战反馈：

- 0607 后几天暂时只有新活动沉船图，本地 BidMap 缺少 `2527` 等新图。
- 只输出 `unsupported_map` 虽然不会崩溃，但实战上会完全没有估值参考；用户希望默认按对应旧 shipwreck 估，不至于空白。

依据：

- `summarize_v3_activity_mapping_likelihood.py --format summary` 对当前活动样本显示 `minus10` 胜出更多：
  - `minus10: 11`；
  - `minus20: 4`。
- 但 0607 实战 valuation replay 显示 `252x->251x` 在 Gabriela 2521/2524 明显过高；live fallback 改为优先 `252x->250x`，再尝试 `251x`。
- `4521-4530` 同理优先映射到 `4501-4510`，再尝试 `4511-4520`。

修复：

- live artifact 构建阶段新增 temporary activity alias：
  - 原始 `map_id` 保留为新图，例如 `2527`；
  - 推理 `model_map_id` 使用旧沉船表，例如 `2507`；
  - `map_alias.mode=activity_shipwreck_minus20`；
  - `inference_input_constraints.map_alias` 记录 source/model/reason。
- UI contract/overlay “输入约束”行显示：
  - `活动图 2527->旧沉船 2507`。
- 直接调用 v3 shadow 传入未知图仍保持 `prior_unavailable`，避免审计口径把别名隐式当成正式表。

边界：

- 这是 live 实战 fallback，不代表已经拿到活动图真实远端表。
- 一般未知地图仍保持 `unsupported_map`，不自动借非同族地图估。
- 后续拿到 `Tables/Activity.txt` 或远端 BidMap 后，应优先替换为真实表口径。

验证：

```text
pytest tests/test_live_monitor.py::test_build_monitor_artifact_does_not_crash_on_unknown_map \
       tests/test_live_monitor.py::test_build_monitor_artifact_uses_activity_shipwreck_alias \
       tests/test_runtime_snapshot.py::test_ui_contract_exposes_activity_map_alias \
       tests/test_live_overlay.py::test_overlay_constraints_section_shows_activity_map_alias -q
4 passed

pytest tests/test_live_monitor.py tests/test_runtime_snapshot.py tests/test_live_overlay.py tests/test_live_status.py -q
98 passed
```

## 2026-06-08 checkpoint：v3 数值下界与活动沉船别名修正

实战反馈：

- `极品估价` 后 UI 价格看起来没有按金色总价变化。
- 活动 Gabriela 2521/2524 在只看到很小仓位时出现 100w+ 估价。

诊断：

- `极品估价` 为 `action_id=100125`，语义是 `q5_value_sum`；live/v2 已能读到这个 exact bucket value。
- v3 feasible summary 之前只把 item-anchor value floor 计入 `known_value_floor`，没有把 hard numeric `bucket.q5.value` / `bucket.q6.value` 的 exact value 计入全局价值下界。
- 这导致 v3 practical 可能给出低于已知 q5 总价的 P50/P90。
- 活动图别名 `252x->251x` 虽有轻微 likelihood 优势，但 valuation replay 明显过高：
  - 2521 R1 `minus10` P50 `1,248,068`，`minus20` P50 `598,804`，truth `462,218`；
  - 2524 R1 `minus10` P50 `1,074,637`，`minus20` P50 `631,348`，truth `457,128`。

修复：

- v3 summary 将 bucket value exact 计入 `known_value_floor`。
- live activity shipwreck alias 改为优先 `252x->250x` / `452x->450x`，再尝试 `251x` / `451x`。

真实复算：

```text
Aisha 2406 R4 after 极品估价:
before: v3 known_floor=4,934, P50=114,279, P90=436,320
after:  v3 known_floor=157,331, P50=157,331, P90=479,372
truth=471,410; q5_value=152,397
```

72h archive brief 复跑：

```text
before this checkpoint:
decision_mae=210,846.9
median_abs_p50_err=162,814
p90_extreme_over_rate=0.34
v3_practical_p90_coverage=0.73
v3_practical_p90_extreme_over_rate=0.49

after:
decision_mae=167,907.4
median_abs_p50_err=126,963
p90_extreme_over_rate=0.27
v3_practical_p90_coverage=0.76
v3_practical_p90_extreme_over_rate=0.37
```

## 2026-06-08 checkpoint：v3 practical 低支持 baseline 实战 guard

实战反馈：

- 最新两局 live v3 practical 低估明显减少，但 Aisha villa 出现 P50/停止价过冲。
- 代表窗口：
  - Aisha 2401 R3：truth `190,143`，v3 practical `266,601 / 484,763 / 632,296`，stop `486,382`；
  - Aisha 2402 R3：truth `341,687`，v3 practical `239,873 / 526,121 / 678,393`，stop `521,841`。

诊断：

- 两局都不是 public/action value floor 直接异常，而是 `summary_likelihood` 低有效样本 baseline passthrough：
  - 2401 R3 ESS `2.156`；
  - 2402 R3 ESS `2.737`。
- `v3_practical_status=baseline_passthrough`，因此此前 live guard 没触发；已有 guard 只覆盖低置信 `raise_watch` prior-only P90。
- archive brief 默认未显式传 `formal_mode=v3_practical` 时仍会按 v2 formal 重放，不能直接代表当前 UI 实战值；复盘 v3 实战需显式使用 `formal_mode=v3_practical`。

修复：

- live v3 practical bid row 新增低支持 baseline guard：
  - 仅在 `baseline_passthrough + baseline_reference + summary_likelihood + strict_ready=false` 时考虑；
  - `summary_likelihood_effective_samples <= 5`；
  - 无 `value_floor_candidate`、`underestimate_repair_candidate`、`random_avg_high_signal_ceiling` 等强证据；
  - `P50-P10 >= 180k`；
  - P50 cap 为 `max(P10+75k, P50*0.70)`；
  - P90 cap 为 `max(original P50, guarded P50+150k, guarded P50*1.35)`。
- 保留 v3 audit 原字段；只保护 live/UI 正式 bid row 的决策区间和停止价。
- prior-only raise-watch P90 guard 同时补充“不低于 baseline P90”的保护，避免小幅 q6 prior watch 反向压窄 baseline P90。

最新两局复算：

```text
Aisha 2401 R3:
before 266,601 / 484,763 / 632,296, stop 486,382
after  266,601 / 341,601 / 491,601, stop 378,155

Aisha 2402 R3:
before 239,873 / 526,121 / 678,393, stop 521,841
after  239,873 / 368,285 / 526,121, stop 404,709
```

72h complete archive v3-practical replay（shadow=20，formal_mode=v3_practical）：

```text
no_guard: rows=34 mae=186,031.3 median_abs=184,195.5 bias=11,818.1 p90_coverage=0.765 p90_extreme_over_rate=0.588
guard:    rows=34 mae=164,325.7 median_abs=132,609.0 bias=-9,887.4 p90_coverage=0.765 p90_extreme_over_rate=0.500
```

验证：

```text
python -m py_compile src\bidking_lab\live\monitor.py
pytest tests\test_live_monitor.py -q
34 passed
```

## 2026-06-08 checkpoint：promotion hardening handoff 与长期路线

背景：

- 用户暂停继续实战采样，希望先整理交接、长期项目项、goal 与 prompt，让另一个审计窗口继续推进。
- 当前 v3 practical 已接 live/UI 实战试用，但 readiness 仍 `overall_status=not_ready`。
- 继续实战反馈可以延后；离线可推进评估口径、promotion hardening、CSE/SCP 稳定性与 shadow-only sampler 重构。

新增：

- 新增 `handoff_2026-06-08.zh-CN.md`：
  - 最新读取顺序；
  - 当前 live/UI/v3 practical/v2 fallback 状态；
  - 0608 实战修复；
  - readiness snapshot；
  - 样本状态；
  - 防过拟合原则；
  - 长期项目项；
  - 推荐 goal；
  - 给审计窗口的续接 prompt；
  - 实战恢复命令。
- 更新 `docs/PROJECT_STRUCTURE_V3.zh-CN.md`：
  - 主入口改为 0608 handoff；
  - 更新 fatbeans 样本数；
  - 修正 `v3_practical` 仍是 shadow report 但 live/UI 可显式使用 guarded bid rows 的描述；
  - 标注 brief 后续需要显式 formal mode 与 guarded/unguarded 分组。
- 新增 D-v3-160：
  - promotion 不以小样本拟合为目标；
  - sampler 重构必须先 shadow-only；
  - 未过 archive/session/map-family/seed holdout 前不替换正式出价。

最新 readiness 复跑：

```text
overall_status=not_ready
blocked_gates=14
windows=1616
ready=1598
formal_mae=317199.529
formal_below=0.51221
formal_p90_cover=0.753914
```

下一阶段长期顺序：

1. 统一 v3 practical guarded/unguarded/v2 评估合同。
2. 补 live guard 结构化指标和 readiness 分组。
3. 收口 prior/activity/table drift。
4. 收口 CSE/SCP settlement bridge seed/session stability。
5. 设计并实现 evidence-driven count/cell/value sampler shadow-only 原型。
6. 通过 holdout/readiness 后再讨论 promotion 与 v2 archive。

## 2026-06-08 checkpoint：v303 activity table acquisition 与 prior-drift 分流收口

背景：

- 用户询问 0605 后沉船活动表是否能找到，还是需要额外解码/远端获取。
- 此前 v3 记录停留在 local v300 filelist 列出 `Tables/Activity.txt` 但项目 raw 缺表；活动沉船只能走 live fallback / prior-drift lane。

完成：

- 查到本机游戏安装目录已包含：
  - `BidKing_Data\StreamingAssets\Tables\Activity.txt`；
  - `Tables\BidMap.txt`；
  - `Tables\Drop.txt`；
  - root `fileVersion=303` / `filelist.txt`。
- 使用现有 `bidking_lab.extract.tables.decode_table_text()` 解码成功：
  - `Activity.txt`：6 rows / 16 cols；
  - `BidMap.txt`：165 rows / 23 cols；
  - `Drop.txt`：629 rows / 5 cols；
  - `Map.txt`：9 rows / 21 cols；
  - `RankMap.txt`：103 rows / 7 cols。
- 更新 `scripts/copy_game_tables.ps1`，同步 key tables 时新增：
  - `Tables\Activity.txt`；
  - `Tables\Map.txt`；
  - `Tables\RankMap.txt`。
- 更新 `scripts/summarize_v3_archive_table_timing.py`：
  - summary 输出 `Activity.txt` filelist entry；
  - raw file metadata 增加 `activity` / `map` / `rankmap`。
- 本地 ignored raw 已用新版脚本同步到 v303；未重建/提交 `data/processed/maps.json`。

关键结论：

```text
raw_file_version=303
raw_tables_file_version=303
BidMap.txt rows=165
Drop.txt rows=629
activity_range=2521-2530 bidmap_present=10 drop_present=0 drop_missing=10
activity_range=4521-4530 bidmap_present=10 drop_present=0 drop_missing=10
```

- `Activity.txt` 是活动入口/UI 配置表，不是“白品概率变红品”的 drop odds 表。
- v303 `BidMap.txt` 已新增 `2521-2530` / `4521-4530`，所以活动图不再是纯 missing BidMap。
- 但 `Drop.txt` 没有新增 `2521-2530` 对应 drop pools，活动红转机制仍未从普通表恢复。
- 因此 252x/452x 仍必须作为 activity/prior-drift lane 分流；不能直接进入 default prior calibration、formal/value sampler promotion 或 v2 archive 依据。

验证：

```text
C:\Python313\python.exe -m py_compile scripts\summarize_v3_archive_table_timing.py
pytest --basetemp=.tmp\codex\pytest tests\test_summarize_v3_archive_table_timing.py -q
2 passed

C:\Python313\python.exe scripts\decode_all_tables.py --rows 0 --col-width 40
C:\Python313\python.exe scripts\summarize_v3_archive_table_timing.py --format summary
```

## 2026-06-08 checkpoint：archive/live formal-mode evaluation contract 补齐

背景：

- live runner 当前显式使用 `formal_mode=v3_practical` 作为 guarded practical trial；
- 但 `summarize_live_windivert_brief.py` 的 archive replay 仍走底层 builder 默认值，即 v2 formal；
- 因此局后 brief 的 `decision_value_p50/p90` 可能被误读为当前 UI/v3 practical 实战值。

完成：

- `scripts/summarize_live_windivert_brief.py` 新增 `--archive-formal-mode {v2,v3_practical}`：
  - 默认仍不传 formal mode，保持 builder 默认 v2 paired 对照口径；
  - 显式传 `v3_practical` 时，archive full/prebid replay 都会把该 formal mode 传入 `build_monitor_artifact_from_file()` / `build_monitor_artifact_from_events()`。
- archive replay 行新增/补齐：
  - `replay_formal_mode_requested`；
  - `replay_formal_mode`；
  - `replay_formal_mode_reason`；
  - 若 `model_eval` 行缺少 `formal_mode*`，用 replay artifact 的 formal-mode 字段补齐。
- summary/group stats 新增：
  - `formal_mode_counts`；
  - `formal_mode_reason_counts`；
  - `v3_practical_formal_rows`；
  - `v3_practical_live_guard_rows`；
  - `v3_practical_live_guard_rate`；
  - `v3_practical_live_guard_reason_counts`。
- 文本 brief 的 overall/prebid/group 表同步输出 v3 practical formal 行数与 guard rate。
- `tests/test_summarize_live_windivert_brief.py` 覆盖：
  - summary formal-mode / guard counts；
  - archive full replay formal-mode 传参与行字段；
  - archive prebid replay formal-mode 传参与行字段。

验证：

```text
python -m py_compile scripts\summarize_live_windivert_brief.py
python -m pytest --basetemp=.tmp\codex\pytest tests\test_summarize_live_windivert_brief.py -q
10 passed

python scripts\summarize_live_windivert_brief.py --since-hours 72 --no-archive --format json
passed; 输出新增 formal_mode / guard 字段，当前 72h model_eval rows=0
```

真实 archive replay 仍被当前 v303 `BidMap.txt` parser/schema drift 阻断：

```text
python scripts\summarize_live_windivert_brief.py --since-hours 72 --archive-n-trials 10 --archive-shadow-trials 1 --archive-formal-mode v3_practical --format json
failed: ValueError: failed to parse bid map row index 32: invalid literal for int() with base 10: ''
```

解码审计显示：

```text
BidMap rows=165 cols=[23]
idx=32 map=2501 col[7]='' col[17]='[9999,2501,22,44]'
idx=145 map=2521 col[7]='105' col[17]='[9999,2521,22,44]'
```

结论：

- archive/live formal-mode evaluation contract 已补齐；
- 当前无法用 v303 raw table 跑真实 archive replay，不应回到 sampler 调参；
- 下一步应先由 table/schema 或 live/app 侧确认 v303 `BidMap.col[7]` 空值语义、category fallback/推断规则，或提供可解析的 v300 table root；
- readiness/promotion gate 不放宽，v3 仍是 audit/shadow/guarded practical trial，不是 promotion。

## 2026-06-08 checkpoint：v303 BidMap parser drift 与 activity missing-drop alias 收口

背景：

- 上一 checkpoint 已补齐 archive/live formal-mode contract，但真实 `--archive-formal-mode v3_practical` replay 被 v303 `BidMap.col[7]` 空值阻断。
- 修复 category parser 后，archive replay 又暴露 `2521-2530` / `4521-4530` missing Drop pool 被临时 zodiac 1% mass 注入导致概率和为 `0.01`。
- 这说明 v303 的 activity BidMap present 不能等价于 activity Drop prior 可用。

完成：

- `src/bidking_lab/extract/bid_map_table.py`
  - 对 v303 旧沉船 `2501-2520` blank category 推断为 `105`；
  - 对 v303 旧暗拍沉船 `4501-4520` blank category 推断为 `305`；
  - 其他 blank category 仍报错。
- `src/bidking_lab/live/monitor.py`
  - activity alias 不再只看 “BidMap missing”；
  - 当 `252x/452x` BidMap present 但对应 `drop_pool_id` 缺失时，仍显式 alias 到旧沉船 `minus20` 优先；
  - alias reason 区分为 `missing_activity_drop_use_corresponding_old_shipwreck`。
- `src/bidking_lab/inference/ground_truth.py`
  - 临时蓝生肖 pool 补丁不再注入到空 Drop pool；
  - missing-drop raw map 直接保持 empty pool，避免概率和不为 1 的崩溃，也避免把 zodiac 当成 activity prior。
- `src/bidking_lab/live/monitor.py` 的 `model_eval` 行新增：
  - `v3_practical_live_guard`；
  - `v3_practical_live_guard_reason`；
  - `v3_practical_unguarded_decision_value`。
- `scripts/summarize_live_windivert_brief.py`
  - archive replay 行从 artifact bid row 补齐 guard 字段；
  - 旧日志中 `formal_mode_reason=v3_practical_ready_live_guarded` 也计为 guarded。

验证：

```text
python -m pytest --basetemp=.tmp\codex\pytest tests\test_bid_map_table.py tests\test_ground_truth.py tests\test_live_monitor.py::test_build_monitor_artifact_uses_activity_shipwreck_alias tests\test_live_monitor.py::test_build_monitor_artifact_aliases_activity_bidmap_with_missing_drop tests\test_live_monitor.py::test_live_formal_mode_v3_practical_guards_low_confidence_prior_only_raise tests\test_live_monitor.py::test_live_formal_mode_v3_practical_guards_low_support_baseline tests\test_summarize_live_windivert_brief.py -q
42 passed

python -m py_compile src\bidking_lab\extract\bid_map_table.py src\bidking_lab\inference\ground_truth.py src\bidking_lab\live\monitor.py scripts\summarize_live_windivert_brief.py

load_monitor_tables smoke:
maps=165 drops=629 items=1187
2501 category=105 drop=2501 min=22 max=44
2521 category=105 drop=2521 min=22 max=44
4501 category=305 drop=2501 min=22 max=44
4521 category=305 drop=2521 min=22 max=44
prepared sampler bad_probability_pools=0
```

72h archive v3-practical replay smoke：

```text
total_rows=49
source_counts={'windivert_archive_prebid': 49}
estimate_rows=47
formal_mode_counts={'v2': 15, 'v3_practical': 34}
formal_mode_reason_counts={
  'no_inference_session': 2,
  'v3_practical_no_bid_rows_fallback_v2': 13,
  'v3_practical_ready': 11,
  'v3_practical_ready_live_guarded': 23
}
v3_practical_formal_rows=34
v3_practical_live_guard_rows=23
v3_practical_live_guard_rate=0.68
decision_value_mae=182623.0
v3_practical_mae=176490.1
v3_practical_delta_mae=-6132.9
v3_practical_p90_coverage=0.79
v3_practical_p90_extreme_over_rate=0.38
prebid_windows=49 ready_windows=47 sessions=15
```

Readiness smoke：

```text
python scripts\summarize_v3_promotion_readiness.py --posterior-trials 64 --format summary
overall_status=not_ready
blocked_gates=13
windows=1616
ready=1598
formal_mae=317290.279
formal_below=0.512516
formal_p90_cover=0.753442
```

结论：

- archive/live formal-mode 和 guard metric 合同现在能在当前 v303 raw table 状态下跑通；
- activity `252x/452x` 仍是 `BidMap present / Drop missing`，只允许显式 alias/live fallback，不进入 default prior、sampler promotion 或 v2 archive 分母；
- readiness 仍是 `not_ready`，promotion/readiness gate 未放宽；
- 下一步可以继续做 guarded/unguarded/v2 archive-live 分组对照和 CSE/SCP bridge stability，而不是回到 formal/value sampler 参数调优。

## 2026-06-08 checkpoint：v3 practical guarded vs unguarded brief metrics

背景：

- archive/live formal-mode 口径已能在 v303 表状态下跑通；
- 但 `v3_practical_ready_live_guarded` 只在 bid row 中保留 `v3_practical_unguarded_decision_value` 字符串，`model_eval`/brief 缺少结构化 guard 前后对照；
- promotion/readiness 需要在同一批 guarded rows 上比较 guarded 与 unguarded，而不是混入 v2 fallback 或无 bid rows。

完成：

- `src/bidking_lab/live/monitor.py`
  - `model_eval` 新增 `v3_practical_unguarded_decision_value_p10/p50/p90`；
  - 继续保留 `v3_practical_unguarded_decision_value` 原始区间字符串。
- `scripts/summarize_live_windivert_brief.py`
  - 对已有字符串字段做 fallback parse；
  - summary/group stats 新增：
    - `v3_practical_unguarded_rows`；
    - `v3_practical_unguarded_mae`；
    - `v3_practical_unguarded_under_rate`；
    - `v3_practical_unguarded_p90_coverage`；
    - `v3_practical_unguarded_p90_extreme_over_rate`；
    - `v3_practical_guard_comparison_rows`；
    - `v3_practical_guarded_mae_on_comparison`；
    - `v3_practical_unguarded_mae_on_comparison`；
    - `v3_practical_guarded_minus_unguarded_mae`；
    - `v3_practical_guarded_minus_unguarded_median_p50`；
    - `v3_practical_guarded_minus_unguarded_median_p90`；
    - guarded/unguarded P90 coverage 与 P90 extreme-over paired deltas。
- 文本 brief 的 overall/prebid/group 表也输出核心 guard deltas。

验证：

```text
python -m pytest --basetemp=.tmp\codex\pytest tests\test_live_monitor.py tests\test_summarize_live_windivert_brief.py -q
46 passed

python -m py_compile src\bidking_lab\live\monitor.py scripts\summarize_live_windivert_brief.py
python -m pytest --basetemp=.tmp\codex\pytest tests\test_live_monitor.py::test_live_formal_mode_v3_practical_guards_low_confidence_prior_only_raise tests\test_live_monitor.py::test_live_formal_mode_v3_practical_guards_low_support_baseline tests\test_summarize_live_windivert_brief.py -q
13 passed
```

72h archive v3-practical replay 新指标：

```text
rows=49
estimate_rows=47
formal_mode_counts={'v2': 15, 'v3_practical': 34}
v3_practical_formal_rows=34
v3_practical_live_guard_rows=23
v3_practical_live_guard_rate=0.68
v3_practical_unguarded_rows=23
v3_practical_unguarded_mae=121571.7
v3_practical_unguarded_under_rate=0.74
v3_practical_unguarded_p90_coverage=0.91
v3_practical_unguarded_p90_extreme_over_rate=0.48
v3_practical_guard_comparison_rows=23
v3_practical_guarded_mae_on_comparison=121571.7
v3_practical_unguarded_mae_on_comparison=121571.7
v3_practical_guarded_minus_unguarded_mae=0.0
v3_practical_guarded_minus_unguarded_median_p50=0.0
v3_practical_guarded_minus_unguarded_median_p90=-388962.0
v3_practical_guarded_p90_coverage_on_comparison=0.48
v3_practical_unguarded_p90_coverage_on_comparison=0.91
v3_practical_guarded_minus_unguarded_p90_coverage=-0.43
v3_practical_guarded_p90_extreme_over_on_comparison=0.0
v3_practical_unguarded_p90_extreme_over_on_comparison=0.48
v3_practical_guarded_minus_unguarded_p90_extreme_over=-0.48
```

Readiness smoke 未放宽：

```text
overall_status=not_ready
blocked_gates=13
windows=1616
ready=1598
formal_mae=317290.279
formal_below=0.512516
formal_p90_cover=0.753442
```

结论：

- 这批 live guard 主要压 P90，不改 P50；paired comparison 的 MAE delta 为 0；
- guard 将 extreme-over 从 0.48 压到 0.0，但 P90 coverage 从 0.91 降到 0.48；
- 该 tradeoff 说明 v3 practical guard 是实战稳定性保护，不是 promotion 证据；
- 下一步应继续把这些 paired guard metrics 纳入 archive/live 分组与 CSE/SCP stability 判断。
