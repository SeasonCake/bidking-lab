# Hero Ref 变更记录（v0.1.8 之后 → 待 v0.1.9）

> **发布策略（2026-06-14 起）**  
> - **已发布基线**：`v0.1.8` @ `a706bd5`（`RELEASE_NOTES_v0.1.8.zh-CN.md` / `SHA256SUMS-v0.1.8.txt`）。  
> - **v0.1.8 之后**：每条有意义的改动写入本文件；**默认不打包**，除非线上有「算错钱 / 闪退 / 完全不能用」级问题。  
> - **下一版对外发布**：**v0.1.9**（艾莎 / 计算效率 / UI）；**WinDivert 更换**不进 0.1.9（下次计划）。架构级 count_prior 仍留 **v0.2.0**。  
> - **hotfix 包**：`v0.1.8-hotfix` 为用户要求的一次性替换；之后走 0.1.9 主线。

**维护规则**：完成一项就追加一行（或更新同一主题的条目），字段尽量填全：`日期 | commit | 类型 | 摘要 | 验证 | 打包`。

---

## 基线

| 项 | 值 |
|---|---|
| 最后对外发布 | v0.1.8 full + public-safe @ `a706bd5`（2026-06-13） |
| 本文件起点 | `a706bd5` 之后的 `main` 提交 |

---

## 变更条目（新在上）

| 日期 | Commit | 类型 | 摘要 | 验证 | 已打包 |
|---|---|---|---|---|---|
| 2026-06-14 | *dev/worktree* | **feat** | **约束分层 P0**：公开 q4/q5/q6 均价件数未锁 → `soft_avg_value_keys` + combo 级软权重（prior + exact）；exact 枚举补齐 grid target + avg_cells 高斯（`_evidence_grid_avg_cells_log_penalties`）。prop `100114` 红均格仍硬。 | `test_ahmad_ref_engine_public_info.py` + `test_ahmad_ref_engine_avg_value_wire_samples.py` | 否 |
| 2026-06-14 | *dev/worktree* | **feat** | **Quote Top3 分档 safety**：P25×0.90 / P50×0.85 / P75×0.80；note `ref_quote_safety_tier_v1`（`layout_depth_policy.quote_safety_multipliers`）。 | `test_ref_engine_tiered_quote_safety_factors` | 否 |
| 2026-06-14 | *dev/worktree* | **refactor** | **LayoutDepthPolicy 抽层**：`src/layout_depth_policy.py`；Aisha full（early + R3+ footroom band）；Raven/Sophie/Gabriela `sparse_early`（R1–4 band only）；Ahmed 不接入。`prepare_reference_engine_snapshot` 对 sparse 默认 `layout=band`。 | aisha/raven layout pytest；392 passed 全量子集 | 否 |
| 2026-06-14 | *dev/worktree* | **feat** | **Hero 推理调度**：`hero_ref_live_schedule.py` — 20 英雄分类、分档 combo cap（1500–12000）、Category C 早轮单技能门控；接入 `ahmad_live_panel_server` scheduled pass。 | `test_live_overlay.py` schedule 相关 | 否 |
| 2026-06-14 | `b94c474` | **fix** | **结算页「估价」不再泄露结算证据**（艾莎/通用）：结算页三档卡的「估价」由 `_pre_settlement_ref_result` 重建以复现末轮 live 估价，但 `_clone_as_pre_settlement_snapshot` 仅翻 `phase/truth`，未清结算级证据（元凶 `ui_contract.constraints` 携带精确结算件数），引擎回读抬高估价（样本 639k vs 真实 live 402k；群友截图 91 万 vs 末轮 40/50/60 万）。现剥离 `final_*`/`inventory`/`known_value_sum`/`minimap_grid_items`/`model_eval` 与 `ui_contract.constraints/minimap`。**仅影响结算页显示，不影响 live 竞价。** | 样本 `2404:…906376` 估价 639,131→402,958，q6 `[3,3,4]`→`[1,2,3]`；`test_live_overlay.py` 209 passed（新增 `test_pre_settlement_clone_strips_settlement_grade_evidence`） | **并入 `v0.1.8-hotfix`**（替换旧包）@ `b94c474`，full SHA256 `45D46FC1…E77FD`、public-safe `7AD3AE9D…6CFD8`；`bidking-lab/dist/` |
| 2026-06-14 | `b9b4ab0` | **fix** | **拉文 R5 全品质缺档锁 0**：技能 `100301` / 公开 `200030`/`200004` 扫全后，未出现档（如无红）→ `fixed_counts=0`，红件 `0/0/0`，不再 0/1/2 抬价。partial 随机揭示仍只 floor。引擎 `_apply_all_item_quality_exact_counts`。 | 群导出 replay + UI 目视；`data 10` 3 红 → 3/3/3（旧版仅下限会 3/3/4）；`test_ahmad_ref_engine_public_info.py` 141 passed | **`v0.1.8-hotfix-full` 已发群** @ `0ad6a97`，SHA256 `C463B7FB…100C5`；发布物统一在 `bidking-lab/dist/` |
| 2026-06-13 | `66a2da2` | docs | v0.1.8 release note + `SHA256SUMS-v0.1.8.txt` | — | — |
| 2026-06-13 | `b93c890` | docs | handoff / PROGRESS 索引更新为 v0.1.8 已发布 | — | — |

---

## 调查中 / 未合入（记在这里，避免丢）

| 日期 | 来源 | 摘要 | 状态 |
|---|---|---|---|
| 2026-06-14 | 群友导出 `Desktop\data (2)` | 拉文 map 2410 session `…4986842`，**R5 UI 闪退**；导出仅到 R4，无 `r05` snapshot / 无 `summary_worker_error` | **待复现**：需 R5 当下导出包 |
| 2026-06-14 | 群友反馈 + 截图（艾莎 2404 R4） | **R1≈30W→R2≈11W 跳水**（疑白绿合并）；手头样本 `2404:…906376` 引擎为 R1 390k→R2 403k，**无跳水**，复现不了 | **待样本**：需截图那局 `2404:…559959` 的 r01/r02 导出 |
| — | 已知 v0.2 项 | 艾莎等无总件揭示英雄的 **count_prior 中心标定**（偏大局早轮偏保守；白蓝阶段数值低/抖属此） | 计划 v0.2.0，勿轻改 |
| 2026-06-14 | 群友/朋友反馈 | **UI 版本号**：标题旁显示 `v*`（`hero_ref_version.py` + 打包 manifest 回读） | **已做**（dev 未打包） |
| 2026-06-14 | 群友/朋友反馈 | **紫金件数+格子**：top3 锁定时显示 `紫N/M · 金N/M`（对齐低品「已锁」格式；红仍分行） | **已做** |
| 2026-06-14 | 群友反馈 | **艾莎计算器**：指标收窄为格/件/红/金；不算最终价 vs 推荐价差；**R3 起才算**（下一步推荐仍给） | 计划 **v0.1.9** |
| 2026-06-14 | 群友反馈 | **对局 UI 隐藏最高出价者名字** | **已做** @ dev（首尾+`*`） |
| — | 群友反馈 | **开局给总格数卡到结尾** | 调查中 |
| 2026-06-14 | 产品口径 | **开发目标定为 v0.1.9**（艾莎 / 效率 / UI）；`hero_ref_version.py` → `0.1.9` | dev |
| 2026-06-14 | 产品口径 | **WinDivert 底层更换** | **下次计划**，不进 0.1.9 |
| 2026-06-14 | 引擎 / 实验 | **tier 价 subset 枚举 audit** | **experimental_deferred**：算力可行、价表未对齐；不接入 live。`tier_value_subset.py` + `data/fixtures/tier_value_subset_audit_cases.json` |
| 2026-06-14 | 引擎 / 规划 | **#4 + soft 均价 promote** | **planning_deferred** — `data/fixtures/soft_promote_count_planning.json` |

---

## v0.1.9 范围（当前开发，未打包）

- 艾莎：R3+ 才算、指标收窄、summary worker / combo 性能
- UI：版本号、紫金件格、对局体验（含隐藏最高出价者等）
- 调查：R1→R2 跳水、总格卡结尾、拉文 R5 闪退
- **引擎 dev（待合入）**：约束分层 P0、LayoutDepthPolicy、hero schedule、Quote 分档 safety — 见变更表 *dev/worktree*

## 约束 / 格数 — O-v3-193 四项 + 关联

**已做（dev/worktree）**

| # | 项 |
|---|-----|
| 1 | 公开均价 soft |
| 2 | combo 级均价软权重 |
| 3 | wire float 规范化（更早） |
| — | public 均格 soft + exact avg_cells 高斯 |
| — | derive 硬路径保留；Quote 分档 safety |

**暂缓 / 实验 / 观察**

| 项 | 状态 |
|----|------|
| **#4** 均格 soft promote | **planning_deferred** |
| soft 均价 promote（#4 镜像） | **planning_deferred** |
| tier 价 subset 枚举 | **experimental_deferred** — 见下表 |
| prop 100113/100114 均格 soft 族 | 观察中 |
| Top3 safety 按 hero/轮次再调；registry 全表 | 观察中 |

## 约束 / 格数 — 实验线详情（**暂缓，已记录**）

| 项 | 状态 | 说明 |
|---|---|---|
| tier 价 → (count,cells) subset 枚举 | **experimental_deferred** | 原型 + audit；Item.txt ≠ session 价 |
| #4 均格 soft promote + soft 均价 promote | **planning_deferred** | `data/fixtures/soft_promote_count_planning.json` |
| prop 100113/100114 均格是否 soft 族 | 观察中 | 待 live 样本 |

Audit（仅抽数值，~2.5s）：`python scripts/audit_tier_value_subset_enumeration.py`

## 下次计划（不进 v0.1.9）

- **WinDivert 底层更换**

## v0.2.0 候选（架构级，与 0.1.9 分开）

- count_prior 地图/局面标定（艾莎早轮低估，架构级）
- D1 按 over/under cohort 重做（apply 当前公式已否决）
- B1 floor-aware 后再考虑放开全英雄
- C3 位置 hint

---

## 打包备忘（仅在实际发版时更新）

| 版本标签 | Commit | 说明 |
|---|---|---|
| v0.1.8 | `a706bd5` | 对外已发 |
| v0.1.8-hotfix | `b94c474` | **GitHub release** full + public-safe @ `dist/`；含拉文 R5 + 艾莎结算页估价修复（替换原 `3fc9271` 包，标签不变） |
| **v0.1.9** | — | **当前开发目标**（艾莎 / 效率 / UI）；未打包 |
| v0.2.0 | — | count_prior 等架构项；未开始 |
