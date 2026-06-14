# 艾莎 R1→R2「跳水」调查 — session `2404:1425860640559959`

**来源**：`C:\Users\shenc\Desktop\recordings\data10\logs\live\`（WinDivert reset 归档）  
**地图**：2404 养生学家居所  
**审计脚本**：`scripts/audit_aisha_r1_r2_dive_session.py`  
**报告**：`data/reports/audit_aisha_r1_r2_dive_559959.json`

## 群友描述

R1 约 30W → R2 约 11W 参考价「跳水」（疑白绿合并/约束变化）。

## 当前引擎复现（dev @ 2026-06-14，`ceb6300` 前基线 + R3 门控）

| 轮次 | ref 状态 | balanced | combo | 耗时（cap=2500） |
|------|----------|----------|-------|------------------|
| R1 | `no_reachable_combo` | — | 0 | ~900ms（约束冲突，枚举前失败） |
| R2 | `count_prior` | **486,231** | 15 | ~10ms |
| R3 | `count_prior` | **486,231** | 15 | ~10ms |

**结论（本样本）**：**未复现 30W→11W 的 Hero Ref 三档跳水**；R2 起稳定在 ~48.6W（count_prior，无 exact 总件）。

R1 证据：仅白绿 split（q1=7 件），`total_grid_target=77` 来自 layout hint，与 q1 格数冲突 → 0 combo。

R2 新增：q3/q4 各 18 件/格锁定 → 15 个 count_prior combo，报价跳至 ~48W（相对 R1 无报价是「从无到有」，非 30→11）。

## v3 正式模型（sessions.jsonl，同 session）

R1 bidding P50 ≈ **604k**；R2 bidding P50 ≈ **649k** — **v3 无跳水**。

## 待核对

- 群友截图是否同一 session / 是否旧版 v0.1.8 UI（防守倍数 × 三档、或 v3 字段误读）
- 是否有 overlay `hero_ref_ui_summary` 未归档（本 recordings 目录无）

## 与产品改动的关系

- **R3+ 才算 / R1–R2 不跑引擎**（`ceb6300`）可避免 R1 ~900ms 白算与误导性中间价。
- 若仍见 R2 count_prior 大幅波动，优先查 **bridge 锁 q3/q4** 与 **总件 prior** 路径，而非 combo cap。
