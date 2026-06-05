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
