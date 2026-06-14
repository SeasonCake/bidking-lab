# 下个窗口交接 Prompt（复制给新会话）

把下面整段贴给新窗口的助手即可快速接手。

---

我在继续 `c:\xiangmuyunxing\biancheng\2026\bidking-lab` 里 **Hero Ref** 的工作（艾莎专项 + 拉文 hotfix + 约束/布局 dev）。请先读：

1. **`handoff_2026-06-14.zh-CN.md`**（**当前唯一权威 checkpoint**：Git/发布/本窗口 delta/待办）
2. **`CHANGELOG_HERO_REF_post-v0.1.8.zh-CN.md`**（v0.1.8 之后逐条流水 + dev/worktree 条目）
3. **`OBSERVATIONS_V3.md` → O-v3-193**（**四项 #1–#4** + promote 家族 + 实验线；勿合并成「P0 已做」一句）
4. **`handoff_2026-06-13.zh-CN.md`** + **`docs/hero_ref_aisha_strategy_2026-06-13.zh-CN.md`**（艾莎 Phase 1 技术细节与路线图）

## 当前状态（简版，2026-06-14 晚）

- **对外群公告**：v0.1.8 @ `a706bd5`（夸克已发）。
- **本地 hotfix 包**：**v0.1.8-hotfix** @ **`69bc9fd`**（拉文 R5 + 结算页估价修复）。
- **Git**：`main` HEAD **`69bc9fd`**，**领先 origin 2 commit**；远程 tag 仍为旧 `4a51598`（push/force-push 待用户决定）。
- **dev 工作树（未 commit）**：
  - O-v3-193 **#1/#2** 均价 soft + combo 权重；**#3** wire float（更早）；均格 soft + exact avg_cells
  - Quote Top3 分档 safety（0.90/0.85/0.80）
  - `layout_depth_policy.py`（Aisha full + sparse 英雄 early band）
  - `hero_ref_live_schedule.py`（分档 combo cap + 推理门控）
  - 验证：**392 passed**（public_info + avg_value_wire + live_overlay）
- **暂缓**：**#4** 均格 soft promote；soft 均价 promote（未立项）；**tier subset 枚举 experimental_deferred**（见 O-v3-193 / CHANGELOG）。
- **发布策略**：默认不打包；**当前开发目标 v0.1.9**（艾莎 / 效率 / UI）。

## v0.1.9 范围（进行中，未打包）

- 艾莎：计算器 **R3+ 才算**、指标收窄、卡顿/效率
- UI：版本号、紫金件格、对局体验（含隐藏最高出价者等）
- 调查：R1→R2 跳水、开局总格「卡结尾」、拉文 R5 闪退
- **引擎 dev 待合入**：见 CHANGELOG *dev/worktree* 四条

## O-v3-193 四项 + 暂缓（勿与 #1–#3 混做）

| # | 项 | 状态 |
|---|-----|------|
| 1–3 | 均价 soft / combo 权重 / wire float | ✅ dev |
| 4 | 均格 soft promote → derive | ⏸ 暂缓 |
| — | soft 均价 promote | ⏸ 未立项 |
| — | tier subset 枚举 | experimental_deferred |
| — | 100113/100114 soft 族；Top3 safety 按 hero 再调 | 观察中 |

## 待办（按优先级）

1. 用户确认后：**push main**；是否 **force-push tag** + 替换 GitHub release zip。
2. **commit 样本归档** + **commit dev 引擎**（用户明确要求时）。
3. 艾莎 **R1→R2 跳水**：需 session `2404:…559959` 的 r01/r02 导出。
4. **#4 / subset / promote 家族**：价表对齐前不接入；主路径仍是 soft + derive + count_prior。

## 本窗口已做（dev @ v0.1.9，未打包）

- UI：版本号 `v0.1.9`、紫金件格、最高出价者首尾+`*`
- 引擎：约束 P0、LayoutDepthPolicy、hero schedule、Quote safety tier

## 红线

- 不在 14 exact-total / 173 curated 上扫权重；C2 target / D1 apply 已否决。
- 未经用户明确要求不要 commit/push/打包。
- 改引擎后跑：`pytest tests/test_ahmad_ref_engine_public_info.py tests/test_ahmad_ref_engine_avg_value_wire_samples.py tests/test_live_overlay.py -q`

先确认你已读 **handoff_2026-06-14** 与 **O-v3-193**，再动手。
