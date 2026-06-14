# 下个窗口交接 Prompt（复制给新会话）

把下面整段贴给新窗口的助手即可快速接手。

---

我在继续 `c:\xiangmuyunxing\biancheng\2026\bidking-lab` 里 **Hero Ref** 的工作（艾莎专项 + 拉文 hotfix）。请先读：

1. **`handoff_2026-06-14.zh-CN.md`**（**当前唯一权威 checkpoint**：Git/发布/本窗口 delta/待办）
2. **`CHANGELOG_HERO_REF_post-v0.1.8.zh-CN.md`**（v0.1.8 之后逐条流水）
3. **`handoff_2026-06-13.zh-CN.md`** + **`docs/hero_ref_aisha_strategy_2026-06-13.zh-CN.md`**（艾莎 Phase 1 技术细节与路线图）

## 当前状态（简版，2026-06-14）

- **对外群公告**：v0.1.8 @ `a706bd5`（夸克已发）。
- **本地 hotfix 包**：**v0.1.8-hotfix** 已重建并**替换**旧包（同一标签名，非 hotfix2）@ **`69bc9fd`**，含：
  - 拉文 R5 全品质：缺档 0/0/0、已出现档精确锁（`b9b4ab0`）
  - 结算页「估价」不再泄露 `ui_contract.constraints`（`b94c474`，**仅显示，不影响 live 竞价**）
- **Git**：`main` HEAD **`69bc9fd`**，**领先 origin 2 commit**；**本地 tag `v0.1.8-hotfix` @ `69bc9fd`，远程 tag 仍为旧 `4a51598`**（push/force-push 待用户决定）。
- **未 commit**：样本归档 `HR-20260614-6376`（manifest + zip）；工作区根 **AGENTS.md / .cursor rules** 已改（备份在 `2026_design/backup_2026-06-14_AGENTS_and_rules/`）。
- **艾莎 Phase 1 仍 live**（B1/B2/C1/C2 band/D1 shadow + UI）；本窗口**未改** count_prior 主路径。
- **发布策略**：默认不打包；下一对外 **v0.2.0**；hotfix 为用户要求的一次性替换。

## 待办（按优先级）

1. 用户确认后：**push main**；是否 **force-push tag** + 替换 GitHub release zip。
2. **commit 样本归档**（`data/samples/hero_ref/...`）。
3. 艾莎 **R1→R2 跳水**：需 session `2404:…559959` 的 r01/r02 导出（手头 `…906376` 无跳水）。
4. **v0.2.0**：count_prior 中心标定（架构级，勿轻改）；开局给总格「卡结尾」；拉文 R5 闪退待复现。

## 红线

- 不在 14 exact-total / 173 curated 上扫权重；C2 target / D1 apply 已否决。
- 未经用户明确要求不要 commit/push/打包。
- 改引擎后跑：`pytest tests/test_live_overlay.py -k pre_settlement_clone` + 艾莎/aisha 子集。

先确认你已读 **handoff_2026-06-14**，再动手。
