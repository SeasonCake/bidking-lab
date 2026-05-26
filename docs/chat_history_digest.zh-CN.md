# bidking-lab 聊天记录精简版（2026-05-26 协作纪要）

> **文件作用**：浓缩并保留 2026-05-26 与 AI 助手协作期间的**关键决策点、用户原始诉求、设计争论与后续待办**。去掉重复的执行细节和大段浏览器自动测试输出，便于新对话或新协作者快速恢复上下文，不再需要翻 2300 行的原始聊天记录。
>
> **原始聊天**：`C:\Users\shenc\Desktop\bid_king_project_chat_history.txt`（约 2300 行 / 466 KB，含大量浏览器 DOM/Playwright 验证输出，可参考但不必精读，跳读指南见文末附录）。
>
> **配套工程文档**（如果本文件某节内容只是简介，详情请直接看这些文件）：
> - [`PROGRESS.md`](../PROGRESS.md) — 项目全貌 + C-44 ~ C-58 Checkpoint 摘要
> - [`docs/optimization_roadmap.zh-CN.md`](optimization_roadmap.zh-CN.md) — 当前优化路线图（P0 / P0.5 / P1 / P2 / Research 分级）
> - [`docs/realtime_monitoring_design.zh-CN.md`](realtime_monitoring_design.zh-CN.md) — 实时观测 / 状态机专项设计
> - [`OBSERVATIONS.md`](../OBSERVATIONS.md) — 技术发现日志（含 MC 采样基准等量化数据）
> - [`TROUBLESHOOTING.md`](../TROUBLESHOOTING.md) — 踩坑记录（含 OCR → 预览空等具体 bug）

---

## 1. 会话出发点（原文 line 7）

用户请求：阅读 `bidking-lab`，建立结构认知，准备帮忙做后续优化；同时确认 karpathy rule 是否会被重复处理。

助手澄清：

- 实际目录名是 `bidking-lab`（不是 `bid_king_lab`）。
- 项目是 Python 包 + Streamlit UI，核心在 `src/bidking_lab/`，UI 在 `app/`。
- karpathy rule 作为持续约束加载一次，不会每条消息重复处理。
- Windows 上 `git status` 报 `dubious ownership`，不影响读代码；要看 diff/commit 时用 `git -c safe.directory=...`。

---

## 2. 用户的原始优化想法清单（原文 line 39）⭐

用户一次性给出的优化方向，按聊天原话保留：

- **帕累托最优 + 多级评估**
- **开头等待界面的小游戏 canvas jump**
- **UI 切换效率**：把整块读数 UI（含容器）放进 fragment，废弃共享 `_tab_pane`
- **推理并行**
- **枚举引擎优化**
- **综合仓库大小优化均格 / 均价**
- **ProtoHub 网络抓包直接读取游戏数据**（看直播时主播在用），动态评估当前仓位情况，比视觉抓取更快更准

这份清单是后续路线图的源头。已被结构化记录在 `optimization_roadmap.zh-CN.md` 的"优先级"表中。本节仅作为"用户原始诉求"留档，避免后续迭代忘记初衷。

---

## 3. 第一次运行体检 & MC 采样瓶颈（原文 line 43~99）

助手做"运行体检"后定位到第一个明确性能瓶颈：

- `sample_session_truth()` 每次都对地图 drop pool 重复 `flatten_pool()`。
- anthology 地图（2401/2501）200 次采样 ~3s，其中 ~2.8s 全花在 flatten。
- 普通地图（2405）200 次采样 ~0.3s。

→ 第一刀优化：新增 `SessionTruthSampler` / `prepare_session_sampler()`，每张地图只 flatten 一次。

→ **详情和实测数据**见 [`optimization_roadmap.zh-CN.md` "已完成：MC 采样预编译"](optimization_roadmap.zh-CN.md) 和 `OBSERVATIONS.md` Checkpoint #36。

---

## 4. 用户决定：先整理路线图（原文 line 128）

用户原话："你先把我们目前可以优化的部分整理一下，写一些关键决策和 todo 点到各个 md 里面，之后我们开始的时候能够有清晰的参考和方向"。

落地结果：新增 `docs/optimization_roadmap.zh-CN.md` 作为后续优化入口；同时同步 `PROGRESS.md` / `OBSERVATIONS.md` / `TROUBLESHOOTING.md` / 中英 README。

---

## 5. P0 第一阶段：UI fragment 化第一刀（原文 line 214~273）

用户决定开始 P0。助手采用渐进式而非一次性重构：

- **不**一次性移动 600+ 行读数 UI；先把读数 tab 整块包进 `@st.fragment`，断开它和 `_tab_pane` 的共享。
- `_tab_pane` 暂时只保留给 hint/joint 旧路径，ROI 本来就不依赖它。
- 后续（用户 line 419 "继续 P0 todo" 后）hint tab 也脱离 `_tab_pane`，改为独立 `st.container()`。

→ **详情**见 [`optimization_roadmap.zh-CN.md` "P0：UI Fragment 化"](optimization_roadmap.zh-CN.md) / `PROGRESS.md` C-45、C-48。

---

## 6. pytest 时间问题（原文 line 275~321）

用户痛点："pytest 总时间太长，做 smoke 测试每次都要等很久"。

诊断 + 决策：

- pytest collection 只占 0.38s；慢的是 `tests/test_ocr_regression_normalize.py` 单文件就贡献 ~30s。
- 给真实 OCR 图片测试加 `slow` marker；在 OCR 回归里加模块级 OCR 缓存；新增 `scripts/test_smoke.ps1` 默认 `-m "not slow"`。
- **效果**：smoke 从 ~43s → ~4s（热缓存）；全量从 ~40s → ~26s。

**约定**：日常用 `.\scripts\test_smoke.ps1`；release / 重要回归用 `pytest -q`。

---

## 7. 用户实测发现的 Bug（原文 line 349）

用户反馈（含一张截图）：
> 填紫/金均格均价、切 hint、切回，候选预览和 MC bundle 都不丢。这个部分仍旧是有问题的：在使用 OCR 进行推理之后，切回会错误显示"无法约束成为候选"，而推理前是能正确显示的。

定位过程：

- 截图里紫品 `avg_raw=3.90`，理论上 43 格 / 11 件 这类候选应当存在。
- 真正原因：读数预览的 `_warehouse_capacity()` 只读 `st.session_state["obs_warehouse_cells"]`；OCR → hint 推理 → 切回这条路径中该 key 容易拿到 0。
- hint 页早有 `session_state 或 state` fallback，读数预览没有 → 修复时给它加上同样的 fallback。
- 顺手修了一处误导文案：预览仓库容量为 0 时，不再提示"均格可能填错"，而是直接提示"仓库总格数未生效"。

→ 落档：`TROUBLESHOOTING.md` 已新增条目 / `PROGRESS.md` C-47。

---

## 8. 阶段性优化清单（原文 line 471~518，保留原文用词）

用户反馈："从 OCR 识别到推理部分总体速度快了很多，UI 切换也不会存在明显问题"。

助手当时给出的"已完成"清单（保留原文，方便回顾这轮优化的整体面貌）：

**1. MC 采样冷启动优化**
- `SessionTruthSampler` / `prepare_session_sampler`
- anthology 地图实测：2401 `2.951s → 0.012s`，2501 `3.002s → 0.013s`

**2. Pytest 日常反馈优化**
- 真实 OCR 图片回归打 `slow` 标记 + 模块级 OCR 缓存 + `scripts/test_smoke.ps1`
- smoke ~4s，全量 ~26s

**3. 读数页 UI fragment 化**
- 读数 tab 整块包进 `@st.fragment`，脱离共享 `_tab_pane`
- 保留原 widget key 和 hydrate/sync 顺序，降低回归风险

**4. Hint tab 脱离共享 pane**
- hint tab 改为独立 `st.container()` 渲染
- `_tab_pane` 只剩 joint 实验 tab 使用

**5. OCR → 切回读数页 预览误空修复**
- `_warehouse_capacity()` fallback 到 `state["warehouse_cells"]`
- 0 容量时不再误导成"均格填错"

**6. 文档与路线整理**
- 新增 `optimization_roadmap.zh-CN.md`
- 同步 PROGRESS / OBSERVATIONS / TROUBLESHOOTING / README

整体效果：**推理冷启动更快、tab 切换更稳、日常验证更快**。

---

## 9. 关键授权：可以动推理内核（原文 line 520）⭐

用户原话（重要授权，完整保留）：
> 关于之前避免引擎优化和动内核的提示你可以适当忽略，之后如果需要进一步提升推理效果和精确度，你可以做，并且修改。

意义：这条授权是后续 P1「session-level 联合候选 / 仓库大小综合均格均价」**直接改写 `compute_analytical_estimate()`** 的前提。在此之前，按 karpathy rule 倾向于不动核心；此后允许动核，但仍按小步可验证推进，每一步用测试固定行为。

---

## 10. P1 第一刀：分析估算接入联合候选（原文 line 524~603）

技术决策（详情见 `optimization_roadmap.zh-CN.md` "P1：Session-level 联合候选"）：

- `compute_analytical_estimate()` 优先调用 `joint_top_k_for_session(k=1, per_bucket_top=16, warehouse_slack=5)`。
- joint 覆盖到的非白绿、非显式格数 bucket 直接回填 `known_cells` 和 `inferred_count`。
- 单 bucket 路径保留为兜底（joint 无结果或未覆盖时）。
- 新增回归测试：60 格仓库里紫 / 金局部 top-1 各 35 格 → 全局组合必须是 30+30。

→ 落档：`PROGRESS.md` C-49 / 测试基线 `28 passed`（test_joint.py + test_posterior.py）。

---

## 11. 联合筛选 UI 恢复 + 改造（原文 line 608~1535）

用户原话：
> 之前有个模块就是联合筛选的，但是我们之前设计的时候把这个 UI 关闭了，你现在帮忙重新打开一下，然后优化一下内容表现，因为之前实在看不出有什么具体意义。

发现：联合推断不是被删除，而是被侧栏 `show_experimental_tab` 默认隐藏。

改造（详情见 `app/experimental_tabs.py` 和 `PROGRESS.md` C-50）：

- 改为常驻主 tab，去掉侧栏实验开关。
- top-3 → top-5，并展示：联合 top-1 格数 / 独立 top-1 合计 / 组合评分 / 过仓罚分。
- 每个 hypothesis 展开后显示每个品质：输入约束 / 联合结果 / 独立 top1 / value-cells-local 评分拆解 / 是否被仓库约束修正。
- 按读数 fingerprint 缓存，读数没变不重算。
- 未选地图 / 未填 bucket 时给友好空态，不再 traceback `map_id is required`（浏览器测试时发现并修了）。

> 这一节在原 txt 里占了 ~900 行，**其中大约 800 行是浏览器 Playwright 自动化测试的 DOM 快照**，用来验证 tab 可见、空态正确、错误信息符合预期、top-5 表格正确渲染等。这部分对理解决策没有信息量，可以跳过。

---

## 12. 联合筛选 vs 秒仓/放仓的边界（原文 line 1571~1603）⭐

用户问："那这个部分是不是和秒放放仓是一起的，还是更加独立一些，秒放仓是更详细的部分？"

约定（**这是后续 Pareto / 秒放仓的关键设计前提，必须留档**）：

```text
读数输入
  ↓
候选枚举 / joint 联合筛选        ← 推理依据层（当前 P1 已完成）
  ↓
仓库组成解释（紫多少格、金多少格、红是否可能、哪里被容量约束）
  ↓
MC / 期望价值 / 收益分布
  ↓
出价建议（价值区间 + bucket 后验）
  ↓
秒仓 / 放仓 / 保守-均衡-激进 等动作建议  ← 动作建议层（Pareto 完成后才接）
```

- **联合筛选 = 底层、解释型、"为什么系统这么估"**：直接给原始读数不变形，只做容量解释。
- **秒仓 / 放仓 = 上层、操作型、"我现在该秒还是该放"**：要等 MC / Pareto / 置信度 / 道具协同稳定后再恢复，不能直接消费原始读数。

→ P0 / P1 阶段秒仓 / 放仓 UI 暂停（代码保留在 `inference/snipe.py`，UI 由 `_ENABLE_SNIPE_PASS_HINTS` 关闭）。开发者可手动改 flag 临时恢复。

实施（用户 line 1605 "可以，那开始吧"）：在出价推荐页插入折叠的「推理依据：联合筛选摘要」，复用 `experimental_tabs.py` 的 joint 渲染，不展开秒仓/放仓动作建议。

---

## 13. 长期目标转向：实时监控（原文 line 2284）⭐⭐

用户原话（关键决策，完整保留）：
> 我希望最终的版本是实时监控游戏进展情况的，然后有状态机，信息更新的时候能自动检测并且重新计算推荐结果。
>
> 后续我们可能会涉及到 ProtoHub 这种抓包信息，可以直接获取伊森技能中未知品质的格子情况信息，和大致仓库大小的信息，而这些对于我们后续的未知巨物或者藏品估计是有帮助的。所以整个设计我希望你帮我修改一下 road_map 并且在必要部分我们先留着接口和冗余空间。

设计决策（**完整设计**见 [`docs/realtime_monitoring_design.zh-CN.md`](realtime_monitoring_design.zh-CN.md)）：

1. **抓包不直接进 `SessionObs`**。新增 source-agnostic 观测层：

   ```text
   manual / ocr / packet / derived
           ↓
   LiveObservationBatch
           ↓
   LiveSessionState reducer
           ↓
   SessionObs adapter
           ↓
   joint / MC / Pareto
   ```

2. 来源优先级固定：`packet > manual > ocr > derived`。
3. 状态机：`UNKNOWN → MAP_READY → READING_READY → RECOMMENDATION_READY ↔ STALE → RECALCULATING → SETTLED / RESET`。
4. **路线图重排**：实时观测接口优先于 Pareto 多级评估。

落地接口（line 2300）：新增 `bidking_lab.live` 薄接口层（`FieldUpdate` / `GridItemObservation` / `LiveObservationBatch`），不接入运行路径，仅契约层。

ProtoHub 边界（**关键约束**）：

- 只做本机只读观察，**不注入、不改包、不自动竞价**。
- 离线 fixture（pcap/json）→ `LiveObservationBatch` parser 优先；不直接连接游戏进程。
- 协议加密或需要绕过保护 → **停止该方向**。

---

## 14. P0.5 reducer + adapter（原文 line 2403~2434）

用户 line 2403 "可以，继续推进项目吧" 后，下一步做的是纯函数层：

- `apply_observation_batch()`：按来源 / 时间合并字段。
- `live_state_to_session_obs()`：把当前 live state 转成推理用 `SessionObs`。
- 测试覆盖：packet 覆盖 manual / OCR、同源新序号覆盖旧值、低优先级不能覆盖高优先级、live state → SessionObs round-trip。

基线：smoke `403 passed / 13 deselected`，全量 `416 passed`。

→ 落档：`optimization_roadmap.zh-CN.md` "P0.5 观测事件接口与实时状态机" TODO 状态 / `realtime_monitoring_design.zh-CN.md` "P0.5"。

---

## 15. 当前下一次开工建议

**直接同步**自 [`optimization_roadmap.zh-CN.md` "下一次开工建议"](optimization_roadmap.zh-CN.md)，避免双写：

1. 把手填 / OCR apply 逐步迁移到 `LiveObservationBatch` 入口（避免 OCR / 手填直接散写 state key）。
2. 做枚举 / joint fingerprint cache（支撑实时刷新，减少重复枚举）。
3. 自动重算状态机：dirty → running → ready，取消陈旧任务。
4. Pareto 出价评估（保守 / 均衡 / 激进 + EV / 亏损率 / 胜率 / 置信度）。
5. ProtoHub 走离线 fixture 验证，**与主线并行**，不阻塞当前手填 / OCR 路径。

---

## 16. 已确认的不做项

- 不把 ProtoHub 直接写进 Streamlit 页面。
- 不让抓包结果直接覆盖 `SessionObs`。
- 不恢复旧秒仓 / 放仓 UI（等 Pareto 完成后作为动作建议层再做）。
- 不做自动竞价、自动点击、改包或注入。
- 不全局做推理并行（先缓存 + 向量化，只有独立分支仍慢时再考虑线程池）。
- 不重新分发游戏资源（`data/raw/` 永远 gitignore）。

---

## 附录：原始聊天的去重映射

如果想看某个话题的"完整对话原文"，原 txt 行号位置如下（基于约 2300 行的原文件）：

| 主题 | 原文行号 | 已落档位置 |
|---|---|---|
| 项目初读 + karpathy rule | 7~37 | 本文件 §1 |
| 用户原始优化清单 | 39 | 本文件 §2 / roadmap "优先级" |
| MC 采样预编译 + 实测数据 | 43~99 | roadmap "已完成：MC 采样预编译" / OBSERVATIONS #36 |
| 路线图整理 | 128~212 | roadmap 整体 + PROGRESS C-44 |
| P0 fragment 第一刀 | 214~273 | roadmap "P0：UI Fragment 化" / PROGRESS C-45 |
| pytest smoke 优化 | 275~321 | roadmap "P0 Pytest smoke 加速" / PROGRESS C-46 |
| OCR → 切回 预览空 bug | 349~417 | TROUBLESHOOTING #51 / PROGRESS C-47 |
| P0 第二刀（hint tab 脱离 pane）| 419~470 | PROGRESS C-48 |
| 阶段性优化清单 | 471~518 | 本文件 §8（保留原列表）|
| **可动内核授权** | 520 | 本文件 §9（关键授权，必须留档）|
| P1 分析估算接入联合候选 | 524~603 | roadmap "P1 Session-level 联合候选" / PROGRESS C-49 |
| 联合筛选 UI 恢复 + 改造 | 608~1535 | roadmap "P1 已完成" / PROGRESS C-50 |
| **浏览器自动化验证 DOM 快照** | 644~1495, 1635~2280 | **大段冗余，可直接跳过** |
| **联合筛选 vs 秒放仓 边界** | 1571~1603 | 本文件 §12（设计层决策，必须留档）|
| 出价页插入 joint 摘要 | 1605~1632 | roadmap "P1 已完成" / PROGRESS C-51 |
| **实时监控转向 + ProtoHub 留接口** | 2284~2330 | 本文件 §13 / realtime_monitoring_design 整体 |
| LiveSessionState reducer + adapter | 2403~2434 | roadmap "P0.5" / 本文件 §14 |

> **跳读提示**：原 txt 中 `line 644 ~ 1495` 和 `line 1635 ~ 2280` 是浏览器 Playwright 自动化测试的 DOM 快照（启动 Streamlit → `domSnapshot()` → 文本比对），用于验证联合筛选 tab 和出价页 joint 摘要。这部分对**理解项目决策没有信息量**，只是验证步骤。如果未来想复用同样的浏览器验证方法（启动 Streamlit + Playwright 抓 DOM），代码示例集中在那两段里，可按需翻。
