# 下个窗口交接 Prompt（复制给新会话）

把下面整段贴给新窗口的助手即可快速接手。

---

我在继续 `c:\xiangmuyunxing\biancheng\2026\bidking-lab` 里 **Hero Ref 艾莎（Aisha）专项优化** 的工作。上个窗口太长卡顿，换新窗口。请先读这两个文件再动手：

1. `handoff_2026-06-13.zh-CN.md`（当前唯一权威 checkpoint：已完成/未完成/待办/批测结论/红线）
2. `docs/hero_ref_aisha_strategy_2026-06-13.zh-CN.md`（主策略与批次路线图）

## 当前状态（简版）
- 艾莎 **Phase 1 已 live**：B1/B2 总格 + C1 报价门禁 + C2 **band** + **D1 shadow**（不改 balanced）+ R1–R5 防守倍数 UI。装配入口 `prepare_reference_engine_snapshot()`（仅 hero=aisha 注入 `layout=band`+`d1=shadow`；Ahmed/Victor 不变）。
- **格/件区间**：相对无优化有提升、零门禁退化（148 curated 总格 hit 34.5%→43.9%，+14/0）。
- **balanced 报价**：live 持平，~83% miss 是结构性问题，留 Phase 2。
- Git：`main` 本地 HEAD `7ea7ea6`，**ahead origin 1，未 push**；远程 `15fd2e2`。dist 仍是旧包 `v0.1.6-hotfix2.1`。
- 艾莎相关子集门禁绿（pytest -k aisha/layout/d1 等、layout isolation、band smoke、sample20 +4/0、hidden 2601 <2s）。
- ✅ **全量 pytest 已全绿**（`tests/` → 1542 passed / 25 skipped / 0 failed）。原 8 个 + 全量额外 2 个失败已全部修复：B1 高阶格 target 与 pinned sparse-prior 路径误泄漏到 ahmed → **gate 到 aisha**；minimap local_index 回退加 shape 条件；q5 note 测试欠债删不可达断言；tk 桩补 `update_idletasks`/`bind`；.bat 是本地 LF 漂移（`git checkout` 落地 CRLF，非代码）。详见 handoff §3。

## 已被批测否决、不要再 live
- C2 **target** 抬点估计（各 cohort 更差）。
- D1 **apply** 当前公式：模拟 balanced hit 18.9%→8.8%（恶化）；主因误差是 under 56%，压低 q6 方向反了。重做需按 over/under 分 cohort，并同时调 conservative/aggressive（apply 现只调 p50）。

## 红线
- 不在 14 exact-total / 173 curated 上扫权重；引擎改动 = 语义规则 + synthetic + 已 hit 不回归。
- 只动 Aisha，不碰 Ahmed/Victor 等。
- v0 不追求 80–90% 格准；追求区间可用 + 报价有参考 + 门禁不退化。
- 不全库扫描（`audit_aisha_round_cohorts.py`/`audit_data7_perf --hero aisha` >5min），用 `audit_aisha_round_cohorts_sample20.py`、`audit_aisha_perf.py --sample-limit 25`、`audit_aisha_c2_batch.py --audit-round N`。

## 可能的两件事（用户会指定其一）
A) **发版 v0.1.7**：跑全量 pytest → `external_references/ahmad_live_reference_lab/build_hero_ref_portable.ps1 -Version 0.1.7 -Zip`（full+public-safe）→ 写 `dist/RELEASE_NOTES_v0.1.7.zh-CN.md`（相对 hotfix2.1 变更 + SHA256）→ 干净目录 smoke（艾莎 R3+ 见「布局余量」「R?防守×?」）。**未经用户同意不要打包/不要 push。**
B) **继续 v0.2 艾莎**：优先 D1 按 over/under 重做 + cells 收束；其次 C3a 位置 hint（同 C2 批测框架）、count_prior 宽 combo 推理效率、扩样本 n。

## 已处理的小优化
- D1 shadow UI 噪音 → 已修（`_aisha_d1_flag_detail` 阈值 0.7 过滤；引擎保留完整 note 供 audit）。

## 发版前必须先做（A 路径的前置）
- v0.2：把 B1 `_apply_total_grid_target_from_known_high_tier_cells` 改成 floor-aware 后再考虑放开到全英雄（当前仅 aisha）。

先确认你已读上述两个文件，并告诉我你接手时打算先做 A 还是 B，再开始。
