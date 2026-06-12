# Hero Ref 结算样本索引 - 2026-06-11

用途：记录 Hero Ref 支线排查“结算异常 / 结算展示不完整 / 价格表漂移”时优先回放的本地样本路径。这里不把样本结论提升为主线 v3 truth；主线 v3 仍保持 shadow-only / audit-only。

## 1. 搜索范围

- 项目当前 live raw：`C:\xiangmuyunxing\biancheng\2026\bidking-lab\data\logs\live\raw\archive\reset`
  - WinDivert reset 文件：8 个
  - 含 settlement frame：8 个
- 项目 Ahmad 2026-06-10 raw：`C:\xiangmuyunxing\biancheng\2026\bidking-lab\data\logs\live_2026.06.10_ahmed\live\raw\archive\reset`
  - WinDivert reset 文件：35 个
  - 含 settlement frame：21 个
- 朋友实测 recordings raw：`C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset`
  - WinDivert reset 文件：26 个
  - 含 settlement frame：25 个
- 朋友手动导出：`C:\Users\shenc\Desktop\recordings\data\logs\live\exports`
  - 导出包：1 个

粗筛命令使用项目解析器读取 WinDivert rows，并按 `state.message_id == 0x002D or inventory_items` 判断 settlement frame；只记录路径和汇总，不打印原始包内容。

## 1.1 当前批量复放结果

2026-06-11 使用当前工作树代码对上述 54 个含 settlement frame 的 raw WinDivert 样本执行：

1. `build_monitor_artifact_from_file(...)` 生成 monitor artifact；
2. 将 artifact 直接输入 `run_reference_engine(..., max_combos=60000)`；
3. 检查 ref_v0 `status`、`combo_count`、`hard_conflict:*` 和 settlement review notes。

结果：

- settlement artifacts replayed：54
- ref_v0 status：`ok=54`
- problem count：0
- hard conflict：0
- 4406 四个样本均 `status=ok`、`combo_count=1`
- 朋友 recordings 中 4521 两个 raw 样本均 `status=ok`、`combo_count=1`

同一批 artifact 继续输入 `summarize_snapshot(...)` 做 UI summary 层检查：

- summaries checked：54
- summary status：`ok=54`
- reference source：`settlement=54`
- ahmed_ref/ref_v0 status：`ok=54`
- problem count：0
- 4406 四个样本的 summary 均对齐 settlement truth；
- 朋友 recordings 中 4521 两个 raw 样本的 summary 均对齐 settlement truth。

这说明当前补丁对“raw artifact -> ui_contract / settlement truth -> ref_v0”链路已经覆盖了已索引 settlement raw 样本；仍未覆盖的是真实 UI 运行过程中的时序显示问题、打包后版本差异、以及用户肉眼看到的结算金额是否来自同一张价格表。

## 2. 4406 结算差价优先样本

这些样本来自项目内 `live_2026.06.10_ahmed`，全部解析为 Ahmad，且都有 settlement frame。4406 类问题优先按价格表 / 活动版本 / 外部表漂移、settlement truth 覆盖、UI 展示链路查，不优先当作 missing settlement block。

| 样本 | session | 结算件数 | 结算格数 | 品质件数 |
| --- | --- | ---: | ---: | --- |
| `data\logs\live_2026.06.10_ahmed\live\raw\archive\reset\windivert_live_2026-06-10_055753_4406_1402770723998745_reset.json` | `4406:1402770723998745` | 35 | 107 | q1=1, q2=10, q3=9, q4=8, q5=3, q6=4 |
| `data\logs\live_2026.06.10_ahmed\live\raw\archive\reset\windivert_live_2026-06-10_060929_4406_1402770724242732_reset.json` | `4406:1402770724242732` | 24 | 62 | q1=1, q2=4, q3=9, q4=6, q5=2, q6=2 |
| `data\logs\live_2026.06.10_ahmed\live\raw\archive\reset\windivert_live_2026-06-10_063220_4406_1402770724722031_reset.json` | `4406:1402770724722031` | 50 | 146 | q1=4, q2=11, q3=17, q4=12, q5=3, q6=3 |
| `data\logs\live_2026.06.10_ahmed\live\raw\archive\reset\windivert_live_2026-06-10_063912_4406_1402770724864228_reset.json` | `4406:1402770724864228` | 25 | 47 | q1=1, q2=5, q3=11, q4=3, q5=4, q6=1 |

已知关键样本：`060929_4406_1402770724242732` 曾出现 pre-settlement bridge total `39`，settlement truth 为 `24` 件 / `62` 格；当前 Hero Ref 补丁应让 settlement `truth.total_items/total_cells` 与 `final_quality_counts/final_quality_cells` 覆盖 stale live/action 输入。

## 3. 朋友 recordings 中的 452x 活动图样本

这些样本在桌面 recordings 目录，不在 repo 内。它们适合复核活动图价格表 / 外部表漂移 / settlement truth 覆盖范围。

| 样本 | session | 结算件数 | 结算格数 | 品质件数 |
| --- | --- | ---: | ---: | --- |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_012408_4530_1402770786508830_reset.json` | `4530:1402770786508830` | 46 | 129 | q1=1, q2=5, q3=12, q4=13, q5=2, q6=13 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_012742_4524_1402770786676452_reset.json` | `4524:1402770786676452` | 39 | 88 | q1=2, q2=7, q3=13, q4=11, q5=4, q6=2 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_013131_4521_1402770786856860_reset.json` | `4521:1402770786856860` | 47 | 136 | q2=11, q3=17, q4=7, q5=8, q6=4 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_013432_4525_1402770786995095_reset.json` | `4525:1402770786995095` | 47 | 138 | q1=1, q2=7, q3=15, q4=8, q5=12, q6=4 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_013624_4529_1402770787081298_reset.json` | `4529:1402770787081298` | 50 | 152 | q1=1, q2=8, q3=10, q4=11, q5=8, q6=12 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_014055_4522_1402770787280138_reset.json` | `4522:1402770787280138` | 47 | 137 | q1=1, q2=9, q3=11, q4=12, q5=7, q6=7 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_014635_4524_1402770787522844_reset.json` | `4524:1402770787522844` | 42 | 126 | q1=1, q2=10, q3=6, q4=14, q5=7, q6=4 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_015007_4527_1402770787671378_reset.json` | `4527:1402770787671378` | 44 | 117 | q2=9, q3=15, q4=9, q5=8, q6=3 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_015355_4524_1402770787828187_reset.json` | `4524:1402770787828187` | 48 | 125 | q1=1, q2=11, q3=17, q4=11, q5=3, q6=5 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_015802_4524_1402770787975231_reset.json` | `4524:1402770787975231` | 50 | 111 | q1=4, q2=17, q3=9, q4=12, q5=3, q6=5 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_020243_4524_1402770788175871_reset.json` | `4524:1402770788175871` | 48 | 106 | q1=1, q2=11, q3=13, q4=14, q5=6, q6=3 |
| `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_020526_4521_1402770788280922_reset.json` | `4521:1402770788280922` | 54 | 127 | q1=5, q2=14, q3=16, q4=11, q5=2, q6=6 |

## 4. 朋友手动导出的异常复放包

- 导出包：`C:\Users\shenc\Desktop\recordings\data\logs\live\exports\HeroRefDiag-20260611-021539-4521_1402770788450965.zip`
- 对应 latest snapshot：`C:\Users\shenc\Desktop\recordings\data\logs\live\latest_snapshot.json`
- session：`4521:1402770788450965`
- 当前复放结论：旧代码曾被 stale live/action q3 count 和 q1 cells 带偏到 `no_reachable_combo`；补丁后 `status=ok`、`combo_count=1`、settlement truth 为 `14` 件 / `43` 格。
- 注意：在 `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset` 中没有找到同 session 的 raw reset 文件；该局以后优先用 zip / latest_snapshot 复放。

## 5. partial / 无 settlement 的样本提示

项目 `live_2026.06.10_ahmed` 下有一批 4405 附近的 reset 文件只有少量 state/sends 或无 parsed state，桌面 recordings 也有 `windivert_live_2026-06-11_010507_4409_1402770785576203_reset.json` 无 settlement frame。它们适合排查采集 reset 边界，不适合直接当“结算 truth 异常”样本。

## 6. 金均格 0 / 金件 `0/1/1` 时序样本

- 新导出包：`C:\Users\shenc\Downloads\HeroRefDiag-20260611-133716-4405_1425860427403590.zip`
- 本地解压：`C:\xiangmuyunxing\biancheng\2026\bidking-lab\.tmp\diag_4405_1425860427403590`
- 当前 latest session：`4405:1425860427403590`
  - `latest_snapshot.json` / `hero_ref_current_summary.json` 显示 4405 settled 已对齐真实结算；
  - `final_q5_count=0`、`final_q5_cells=0`、`final_q6_count=1`、`final_q6_cells=1`；
  - 该 latest snapshot 没有复现“金均格 0 进入 evidence 后仍显示金件 0/1/1”。
- 疑似金件 `0/1/1` 历史帧：
  - `.tmp\diag_4405_1425860427403590\hero_ref_ui_summary.jsonl:297`
  - `.tmp\diag_4405_1425860427403590\hero_ref_ui_summary.jsonl:298`
  - `.tmp\diag_4405_1425860427403590\hero_ref_ui_summary.jsonl:471`
  - `.tmp\diag_4405_1425860427403590\hero_ref_ui_summary.jsonl:472`
  - `.tmp\diag_4405_1425860427403590\hero_ref_ui_summary.jsonl:473`
  - session：`4401:1402770796456825`
  - 另有 session：`4405:1425860427403590`
  - UI 显示 `金件 0 / 1 / 1`；
  - 对应证据只有 `100110` 白绿均格、`100117` 蓝件数和公开/小地图约束，没有抓到 `100113` 金均格 0 或 `inferred_zero`，因此只能作为“金均格未进 evidence 时先验仍允许 1 金”的时序样本。
- 已补 monitor 时序风险：
  - `src\bidking_lab\live\monitor.py::_action_result_rows(...)` 现在 artifact 构建时按 latest session 生成 action results；
  - 旧局同 action 的历史结果不会挡住当前局 `sent_action_without_result_after_later_state` 的 inferred zero；
  - 空结果占位且无揭示物时也允许 zero fallback；
  - 有数值结果、有揭示物、或没有后续 state 时不猜 0。

## 7. 2026-06-11 晚间 recordings data2 / data3 反馈

### 7.1 data2：已由用户截图确认为防火墙 / 安全软件拦截

- 路径：`C:\Users\shenc\Desktop\recordings\data2`
- 本地日志观察：
  - `logs\live\capture_source_status.json` 显示 `active_flows=2`、`raw_packets=0`、`accepted_frames=0`；
  - `logs\live\monitor.stderr.log` 是 `FileNotFoundError: [WinError 2]`，发生在 `pydivert.WinDivert(...).__enter__` / `open`；
  - `latest_snapshot.json` 不存在。
- 用户随后补充截图，确认该局是防火墙 / 安全软件杀掉底层抓包，不再作为协议解析问题继续深挖。
- 代码侧已补诊断：后续 monitor 打不开 WinDivert 时，会把 `windivert_dependency_missing` / `windivert_open_failed` 写入 `capture_source_status.json`；UI 会显示“检查防火墙/安全软件”，不再只表现成普通 `no_raw_packets`。

### 7.2 data3-logsdeficit：多数结算完整，唯一 partial 样本缺 `0x002D`

- 路径：`C:\Users\shenc\Desktop\recordings\data3-logsdeficit`
- 有效 monitor 日志：`logs\live\monitor.stdout (1).log`
- 当前 latest：`logs\live\latest_snapshot.json`
  - session：`4401:1425860450521121`
  - `phase=settled`
  - `ui_contract.truth.available=true`
  - `total_value=507630`、`total_items=33`、`total_cells=73`
  - minimap `layout_source=settlement_inventory`、`layout_complete=true`
- `logs\live\raw\windivert_live.jsonl` 里当前局也有 `0x002D`，33 件 settlement inventory，与 latest 对齐。

`raw\archive\reset` 复放结果：

| 样本 | session | 是否有 `0x002D` | 结论 |
| --- | --- | --- | --- |
| `windivert_live_2026-06-11_184537_4402_1425860449130260_reset.json` | `4402:1425860449130260` | 是 | `truth.available=true`，45 件 / 111 格 / 510620 |
| `windivert_live_2026-06-11_184701_4407_1425860449234245_reset.json` | `4407:1425860449234245` | 是 | `truth.available=true`，50 件 / 140 格 / 1501573 |
| `windivert_live_2026-06-11_185038_4404_1425860449497317_reset.json` | `4404:1425860449497317` | 是 | `truth.available=true`，32 件 / 73 格 / 128900 |
| `windivert_live_2026-06-11_185230_4401_1425860449638527_reset.json` | `4401:1425860449638527` | 是 | `truth.available=true`，36 件 / 106 格 / 910258 |
| `windivert_live_2026-06-11_185557_4401_1425860449894597_reset.json` | `4401:1425860449894597` | 否 | partial capture，只到 R2/R3 bidding；不能当结算 truth 异常样本 |
| `windivert_live_2026-06-11_185832_4408_1425860450045771_reset.json` | `4408:1425860450045771` | 是 | `truth.available=true`，28 件 / 77 格 / 503564 |
| `windivert_live_2026-06-11_190114_4408_1425860450283781_reset.json` | `4408:1425860450283781` | 是 | `truth.available=true`，26 件 / 61 格 / 234885 |

结论：这批 `data3-logsdeficit` 里没有发现“已拿到 settlement block 但 UI/summary 漏结算”的证据；唯一缺失是 partial raw 本身没有 `0x002D` 结算帧。

### 7.3 两个旧导出 zip：一个是新物品价格表漂移，不是缺 settlement

- `C:\Users\shenc\Desktop\recordings\HeroRefDiag-20260611-171256-4402_1425860441516292.zip`
  - session：`4402:1425860441516292`
  - raw 有 `0x002D`，latest 有 settlement truth，49 件 / 124 格；
  - zip 内旧 latest 总值为 `666861`；
  - 用当前 v308 表复放同一 raw 为 `1222416`；
  - 差值 `555555` 来自 item `1036007` “退钱”手举牌，旧 latest 中该 item 名称/价值缺失，当前 v308 `Item.txt` 已有价格；
  - 结论：价格表 / 新物品版本漂移，不是 missing settlement block。
- `C:\Users\shenc\Desktop\recordings\HeroRefDiag-20260611-171943-4410_1425860442951286.zip`
  - session：`4410:1425860442951286`
  - raw 有 `0x002D`，latest 与当前复放均为 32 件 / 75 格 / `370645`；
  - hero 为 Gabriela，不是 Hero Ref structured hero，ref readiness 为 `not_structured_hero`，但 settlement truth 本身完整。

## 8. 2026-06-12 Desktop recordings 金均格 / SEND-no-REV 审计

### 8.1 扫描范围

- 路径：`C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset`
- 方法：125 个 reset JSON 复放 monitor artifact 构建逻辑，统计 bidding、action sends、public numeric、inferred_zero。

### 8.2 摘要

| 项 | 数量 |
|---|---|
| reset 总数 | 125 |
| 含 bidding phase | 4 |
| `100113`（金均格）或 `100114`（红均格）SEND | 0 |
| 仅见其他 avg skill（如 `100110` 白绿均格） | 是 |
| 显式 gold-zero（`200011/200015=0`、`100113 result=0`、inferred_zero@100113） | 0 |

### 8.3 机制（与 §6 互补）

- 用户反馈：界面「金均格 = 0」常对应 **SEND `100113` 无 REV `0x0027`**，不是正常 result packet。
- `monitor._action_result_rows` 的 inferred_zero 需要同 session **后续 state**（`sort_id > send`）；仅 SEND 或尚无 later state 时不写入 zero evidence。
- 因此 recordings 批量结果与「金均格未进 evidence、count prior 仍允许 1 金 → UI 金件 0/1/1」一致，**不能**用该批数据直接验收「zero 已进 engine 仍显示错」。

### 8.4 仍有效的时序样本

- §6 中 `HeroRefDiag-20260611-133716` / `hero_ref_ui_summary.jsonl` 行：仅有 `100110` 等，无 `100113` / inferred_zero。
- Settlement truth 例：`2309:1425860477317545` — `q5=[0,0,0]` 来自 `final_q5_count=0`，非金均格观测。

### 8.5 仍缺样本

- 同 session：`100113` SEND →（无 REV 或 REV=0）→ 有 later state → UI 仍非零。
- 或：手动填金均格/金件 0 + 「应用并启用」后仍与 live 冲突。

详细分批修复计划：`EXECUTION_NOTES_2026-06-10.zh-CN.md` §54；checkpoint handoff：`handoff_2026-06-12.zh-CN.md`。
