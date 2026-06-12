# Hero Ref 文件与文档索引

日期：2026-06-12  
基线 commit：`32f4bb3`（文档增补 commit 见 git log）  
用途：说明 Hero Ref 支线**代码 + 文档**各自干什么、如何串联、**什么情况下才更新**，避免「该记的文档长期不动、临时笔记散落各处」或「同一事实重复写多份却不同步」。

## 1. 与主线 PROGRESS / OBS / DECISION 的对照

主线 v3 采用 **根索引 + 专题正文**：

| 层级 | 主线 v3 | Hero Ref 支线 |
| --- | --- | --- |
| 根索引（只指向，不长写） | `PROGRESS.md` → `PROGRESS_V3.md` | 根 `PROGRESS.md` Hero Ref 小节 → 本文件 |
| 观察（现象、样本、未决） | `OBSERVATIONS.md` → `OBSERVATIONS_V3.md` | `OBSERVATIONS.md` Hero Ref 小节 → `docs/hero_ref_settlement_sample_index_*.md` + EXECUTION_NOTES 调查段 |
| 决策（口径、边界、选型） | `DECISIONS.md` → `DECISIONS_V3.md` | `DECISIONS.md` Hero Ref 小节 → EXECUTION_NOTES §46–§51、§56 + handoff |
| 进度 / 执行流水 | `PROGRESS_V3.md`（checkpoint 级） | `EXECUTION_NOTES_2026-06-10.zh-CN.md`（§ 编号条目） |
| 会话交接 | `handoff_YYYY-MM-DD.zh-CN.md` | 同左 + `external_references/.../HANDOFF_*.md`（支线内历史） |
| 成果 / 落地核对 | — | **EXECUTION_NOTES §55**（聊天与 commit 对照表） |
| 结构 / 路径职责 | `docs/PROJECT_STRUCTURE_V3.zh-CN.md` | **本文件** + `docs/hero_ref_branch_2026-06-09.zh-CN.md` |

**维护原则（与 AGENTS.md 一致）：**

- 根目录 `PROGRESS.md` / `OBSERVATIONS.md` / `DECISIONS.md` **只更新索引行**，不粘贴长段落。
- **同一事实只在一处写「正文」**：样本路径 → sample index；发版 hash → EXECUTION_NOTES 发版 §；会话增量 → 最新 handoff。
- **checkpoint / 合并前**：更新 §55 一行 + 最新 handoff；大块调查结论进 EXECUTION_NOTES 新 § 或 sample index §。
- **不要**每改一行代码就改 EXECUTION_NOTES；**要**在行为/口径/发版/样本索引变化时更新。

## 2. 实时数据流（代码联系）

```text
[Capture 层 — 计划迁移 §56]
  scripts/run_windivert_live_monitor.py  (WinDivert + pydivert，当前默认)
       │  raw jsonl / reset
       ▼
[Parse 层 — 主线 src]
  src/bidking_lab/live/fatbeans.py      帧 → state / field_updates / skill_reveals
       │
       ▼
[Artifact 层 — 主线 src]
  src/bidking_lab/live/monitor.py       events → monitor artifact + ui_contract
  src/bidking_lab/runtime/snapshot.py   summarize_snapshot / minimap 契约
       │  data/logs/live/latest_snapshot.json
       ▼
[Ref 层 — 支线 src]
  external_references/.../ahmad_ref_engine.py   extract_evidence → run_reference_engine (ref_v0)
       │
       ▼
[UI 层 — 支线 tools]
  tools/ahmad_tk_overlay.py             Tk mini / 手填 / 读 snapshot
  tools/ahmad_live_panel_server.py      HTTP summary（调试）；红/金/紫显示格式化
       │
       ▼
[打包 / 启动 — apps + 支线脚本]
  apps/hero_ref/Start-HeroRef.ps1       便携包入口
  external_references/.../start_ahmad_live.ps1   开发仓库入口
```

**边界：** ref_v0 与 UI **不写**主线 formal decision / v3 promotion；可改主线 **窄接点**（fatbeans、monitor artifact 字段、snapshot 契约、共享 tests）。

## 3. 文档文件：功能、联系、何时更新

| 文件 | 功能 | 与谁联系 | 何时更新 |
| --- | --- | --- | --- |
| `docs/HERO_REF_FILE_AND_DOC_INDEX.zh-CN.md` | **本索引**；代码+文档总表 | 所有 Hero Ref 文档入口 | 新增重要目录/分层、或维护规则变化时 |
| `docs/hero_ref_branch_2026-06-09.zh-CN.md` | 支线定位、主线接点、边界 | README、主线 PROJECT_STRUCTURE | 接点字段或边界变化时（低频） |
| `docs/hero_ref_settlement_sample_index_2026-06-11.zh-CN.md` | **样本 catalog**：session、路径、能否当 truth、机制结论 | EXECUTION_NOTES 调查 §、§55 | 新样本归档、批量 audit、缺样本清单变化时 |
| `data/samples/hero_ref/README.zh-CN.md` | **归档目录说明** + 复放命令 | manifest.json、§10 | 归档布局变化时 |
| `data/samples/hero_ref/manifest.json` | 机器可读 export catalog | `scripts/organize_hero_ref_samples.py` | 执行 `--apply` 后自动刷新 |
| `handoff_2026-06-12.zh-CN.md` | **最新会话** checkpoint、分批计划、git 基线 | §55、§54–§58 | 每个 checkpoint / 新窗口交接 |
| `handoff_2026-06-11.zh-CN.md` 及更早 | 历史 handoff | 仅回溯 | **不再追加**；新内容写新日期 handoff |
| `external_references/.../EXECUTION_NOTES_2026-06-10.zh-CN.md` | **执行主记录**：反馈、修复、发版、规划 § | §55 索引、§57–§58、dist RELEASE | 发版、重大修复、规划决策、批量 audit 结论 |
| `external_references/.../EXECUTION_NOTES_2026-06-09.zh-CN.md` | 历史执行记录 | — | **只读** |
| `external_references/.../HANDOFF_2026-06-10.zh-CN.md` 等 | 支线内历史交接 | — | 只读；新交接写根目录 `handoff_*` 或最新 HANDOFF |
| `external_references/.../README.zh-CN.md` | 支线对外说明、启动方式 | 本索引、CLOSEOUT | 用户可见能力/启动变化时 |
| `external_references/.../dist/RELEASE_NOTES_*.md` | **发版说明**（随 zip） | EXECUTION_NOTES 发版 § | 每次打 zip 时 |
| `apps/hero_ref/*.zh-CN.md` | 便携包信任、清单、说明 | PACKAGE_MANIFEST | 打包模板或信任边界变化时 |
| `PROGRESS.md` / `OBSERVATIONS.md` / `DECISIONS.md` | 根 **索引** | 本文件、最新 handoff | 换最新 handoff 指针或重点 bullet 时 |

## 4. 代码文件：功能、联系、何时更新

### 4.1 抓包与启动（变更频率：低 → 计划 E 批重构）

| 文件 | 功能 | 上游/下游 | 何时更新 |
| --- | --- | --- | --- |
| `scripts/run_windivert_live_monitor.py` | WinDivert 抓包、写 jsonl、`capture_source_status.json` | → fatbeans 解析 | 抓包过滤、错误诊断、backend 抽象（§56） |
| `scripts/organize_hero_ref_samples.py` | HeroRefDiag zip → `data/samples/hero_ref/archive` + manifest | sample index §9–§10 | 新 export 后 `--apply` |
| `scripts/start_live_windivert_overlay.ps1` | 启动 monitor ± 主线 overlay | 调用 run_windivert | 启动参数、formal_mode 默认 |
| `external_references/.../start_ahmad_live.ps1` | 开发：Hero Ref UI + monitor | apps 模板同源逻辑 | 启动/工程 profile 变化 |
| `apps/hero_ref/Start-HeroRef.ps1` | 便携包启动 | dist 打包输入 | 与 start_ahmad 对齐时 |

### 4.2 解析与 artifact（变更频率：中 — 新 skill / public id）

| 文件 | 功能 | 上游/下游 | 何时更新 |
| --- | --- | --- | --- |
| `src/bidking_lab/live/fatbeans.py` | 协议解析、field_updates、hero skill | raw 帧 → monitor | 新 action/skill/public id、Maria/Raven 等 hero 解析 |
| `src/bidking_lab/live/monitor.py` | artifact 构建、action results、inferred_zero | fatbeans events → snapshot | 证据行语义、session 时序、新 artifact 字段 |
| `src/bidking_lab/runtime/snapshot.py` | `summarize_snapshot`、`ui_contract`、minimap | monitor artifact → JSON | 契约字段；**§57** `_apply_treasure_value_reveals`、shape footprint marker |

### 4.3 Ref 引擎（变更频率：中 — 约束/性能/hero）

| 文件 | 功能 | 上游/下游 | 何时更新 |
| --- | --- | --- | --- |
| `external_references/.../src/ahmad_ref_engine.py` | ref_v0：证据提取、枚举、三档输出 | snapshot → UI summary | 新约束、均格/公开精确、hero 特化、性能路由 |
| `src/bidking_lab/simulation/hero_skills.py` | 英雄技能语义（Victor 等） | fatbeans 共用 | 技能 ID 语义变更 |

### 4.4 UI（变更频率：中 — 显示/手填；产品 polish 见 §46）

| 文件 | 功能 | 上游/下游 | 何时 update |
| --- | --- | --- | --- |
| `external_references/.../tools/ahmad_tk_overlay.py` | Tk 主 UI、手填、capture 状态展示 | snapshot + ref summary | 交互、手填校验；**§57** minimap 斜条纹/无格子常驻字 |
| `external_references/.../tools/ahmad_live_panel_server.py` | summary 格式化、红/金/紫 range 显示 | ref_result dict | 显示 bug；**§57** minimap contract 优先与 footprint |

### 4.5 测试（变更频率：随功能 — 必须与改动的层同 PR）

| 文件 | 覆盖 |
| --- | --- |
| `tests/test_live_fatbeans.py` | fatbeans 解析、Maria skill updates |
| `tests/test_live_monitor.py` | artifact、inferred_zero、skill_reveal_rows |
| `tests/test_ahmad_ref_engine_public_info.py` | ref 引擎公开信息、均格、hero、200048 |
| `tests/test_live_overlay.py` | UI summary、红显示、手填、WinDivert 错误文案 |
| `tests/test_windivert_live_monitor.py` | capture_source_status 错误路径 |
| `tests/test_runtime_snapshot.py` | ui_contract / minimap（**§57** 至宝、shape footprint） |

**规则：** 改 fatbeans → 至少 fatbeans tests；改 engine → public_info tests；改 panel/overlay → overlay tests。

### 4.6 打包产物（变更频率：发版时 — 不手改 dist）

| 路径 | 说明 |
| --- | --- |
| `external_references/.../dist/*.zip` | 本地构建；hash 记入 EXECUTION_NOTES + SHA256.txt |
| `external_references/.../build/` | 构建缓存；**不提交** |

## 5. 更新频率指南（避免边界混乱）

| 类型 | 典型频率 | 写到哪里 |
| --- | --- | --- |
| 单行 bugfix、测试绿 | 随 commit | 仅当改用户可见行为 → EXECUTION_NOTES 一条或 §55 表 |
| 会话结束 checkpoint | 每 1–3 天或一批功能 | handoff 新日期 + §55 + git push |
| 新样本/audit | 有路径可复现 | `hero_ref_settlement_sample_index` 新 § |
| 发版 zip | 群友可装包 | EXECUTION_NOTES 发版 § + RELEASE_NOTES + SHA256 |
| 口径/架构决策 | Rare | EXECUTION_NOTES 规划 §（§46+）+ 根 DECISIONS 索引一行 |
| 长期不变 | — | `hero_ref_branch`、`CLOSEOUT_2026-06-09`、旧 handoff |

## 6. 当前 open 样本需求

**金为零（公开信息）**：已由 **HR-20260612-4653** 覆盖（§9）；parser fix 待源码重启 / 重打包后 UI 验收。

**仍缺**：§54 **A 批** — `100113` SEND-no-REV + later state 时序样本（§8 recordings 无）。

**小地图 / 至宝估价**：§11 四局 live 样本；加布里 **HR-MINI-20260612-GAB** 已用户验收（§57）。

**归档**：新 export 后运行 `python scripts/organize_hero_ref_samples.py --apply`。

## 7. 快速入口

- 最新 handoff：[`handoff_2026-06-12.zh-CN.md`](../handoff_2026-06-12.zh-CN.md)
- 执行主记录：[`external_references/ahmad_live_reference_lab/EXECUTION_NOTES_2026-06-10.zh-CN.md`](../external_references/ahmad_live_reference_lab/EXECUTION_NOTES_2026-06-10.zh-CN.md)
- 落地核对表：**§55**、**§58**
- 小地图 / 至宝估价：**§57**
- 抓包迁移规划：**§56**
- 样本索引：[`docs/hero_ref_settlement_sample_index_2026-06-11.zh-CN.md`](hero_ref_settlement_sample_index_2026-06-11.zh-CN.md)（§9 金为零、§10 归档）
- 归档目录：[`data/samples/hero_ref/README.zh-CN.md`](../data/samples/hero_ref/README.zh-CN.md)
