# 下个窗口交接 Prompt（复制给新会话）

把下面整段贴给新窗口的助手即可快速接手。

---

我在继续 `c:\xiangmuyunxing\biancheng\2026\bidking-lab` 里 **Hero Ref 艾莎（Aisha）专项优化** 的工作。上个窗口太长卡顿，换新窗口。请先读这两个文件再动手：

1. `handoff_2026-06-13.zh-CN.md`（当前唯一权威 checkpoint：已完成/未完成/待办/批测结论/红线）
2. `docs/hero_ref_aisha_strategy_2026-06-13.zh-CN.md`（主策略与批次路线图）

## 当前状态（简版，2026-06-13 晚）
- **Hero Ref v0.1.8 已发布并 push**：full + public-safe @ `a706bd5`（干净树）。公告/说明/release note 已交付。
- 本轮（Phase 1 之后）修复：**白绿件数随机揭示不再误锁 q1（floor-only）**、空闲 fast→full 升级、每轮滚动快照诊断、UI 重开覆盖、小地图锚点/闪烁、静默启动/关闭崩溃/WinDivert 卸载、艾莎下一步动态文案、全 20 英雄识别。详见 handoff §1.5。
- 艾莎 **Phase 1 仍 live**：B1/B2 总格 + C1 报价门禁 + C2 **band** + **D1 shadow**（不改 balanced）+ R1–R5 防守倍数 UI。装配入口 `prepare_reference_engine_snapshot()`（仅 hero=aisha 注入；Ahmed/Victor 不变）。格/件区间有提升、零门禁退化；balanced ~83% miss 留 v0.2。
- Git：`main` @ `2d51012`，**已与 origin 同步**。对外最后发布 **v0.1.8** @ `a706bd5`。
- **发布策略**：v0.1.8 之后改动写入 [`CHANGELOG_HERO_REF_post-v0.1.8.zh-CN.md`](CHANGELOG_HERO_REF_post-v0.1.8.zh-CN.md)；**默认不打包**，除非重大线上问题；下一对外版计划 **v0.2.0**。
- ✅ **全量 pytest 全绿**，含本轮新增白绿 floor 回归测试。
- 🔴 **v0.2 头号遗留**：无「总件揭示」英雄（艾莎）偏大局早轮估价系统性偏低（count_prior 中心标定，V3 架构级，风险高）。已定位、未改，详见 handoff §6。

## 已被批测否决、不要再 live
- C2 **target** 抬点估计（各 cohort 更差）。
- D1 **apply** 当前公式：模拟 balanced hit 18.9%→8.8%（恶化）；主因误差是 under 56%，压低 q6 方向反了。重做需按 over/under 分 cohort，并同时调 conservative/aggressive（apply 现只调 p50）。

## 红线
- 不在 14 exact-total / 173 curated 上扫权重；引擎改动 = 语义规则 + synthetic + 已 hit 不回归。
- 只动 Aisha，不碰 Ahmed/Victor 等。
- v0 不追求 80–90% 格准；追求区间可用 + 报价有参考 + 门禁不退化。
- 不全库扫描（`audit_aisha_round_cohorts.py`/`audit_data7_perf --hero aisha` >5min），用 `audit_aisha_round_cohorts_sample20.py`、`audit_aisha_perf.py --sample-limit 25`、`audit_aisha_c2_batch.py --audit-round N`。

## 下一步（v0.2.0 线，默认不打包）
- 读 [`CHANGELOG_HERO_REF_post-v0.1.8.zh-CN.md`](CHANGELOG_HERO_REF_post-v0.1.8.zh-CN.md) 再动手；**每完成一项 meaningful 改动就追加一行**。
- **未经用户明确要求不要打包**（除非算错钱/闪退/完全不可用级 hotfix）。
- **P0/P1 count_prior 中心标定**：艾莎等无总件揭示英雄偏大局早轮低估。根因 = map 家族默认 total（如 24xx=28）+ 窄枚举窗，被已知低品占满后高价品无空间。**V3 架构级、影响全英雄/全图、风险高**，需大量验证，不要轻改；先设计 + 分片审计。
- 其次：D1 按 over/under 重做 + cells 收束；B1 改 floor-aware 后再放开全英雄；C3a 位置 hint；count_prior 宽 combo 推理效率；扩样本（已 637）。
- **红线照旧**：未经用户同意不要打包/不要 push；只动 Aisha，不碰 Ahmed/Victor。

## 已处理的小优化
- D1 shadow UI 噪音 → 已修（`_aisha_d1_flag_detail` 阈值 0.7 过滤；引擎保留完整 note 供 audit）。

## 发版前必须先做（A 路径的前置）
- v0.2：把 B1 `_apply_total_grid_target_from_known_high_tier_cells` 改成 floor-aware 后再考虑放开到全英雄（当前仅 aisha）。

先确认你已读上述两个文件，并告诉我你接手时打算先做 A 还是 B，再开始。
