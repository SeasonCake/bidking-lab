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
