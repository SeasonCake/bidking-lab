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

- Fatbeans 本地样本：`data/samples/fatbeans`，当前 355 份 JSON。
- v3 coverage 可解析样本：350 份。
- 已知 parse error：5 份旧样本，作为数据质量问题，不计为 registry gap。
- v3 canonical evidence events：10,164。
- 当前 coverage：`coverage_ok=True`，unknown/pending 均为 `none`。

复跑命令：

```powershell
C:\Python313\python.exe .\scripts\summarize_v3_evidence_coverage.py --fail-on-gaps
```

## 下一步

1. 用条件 proposal 替换/减少 `q6_projection` fallback，让更多窗口 strict-ready。
2. 在 v3 archive report 上新增 formal MAE / below-q6 / pinball 等 paired metrics。
3. 接 live/UI/archive 的 v3 shadow 字段，默认 `affects_bid=false`。

## 不做事项

- 不重做 UI 视觉。当前 UI 设计冻结保留。
- 不接 Fatbeans 会员 WebHook 路线。
- 不把 tail replacement 接入正式出价。
- 不直接把 v3 shadow 改成 formal decision。
