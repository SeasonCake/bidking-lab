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
