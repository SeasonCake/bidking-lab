# Ahmad Live Reference Lab

日期：2026-06-08

## 定位

这是一个隔离的 Ahmed 实时推理与 UI 优化实验目录，全部放在 `external_references/` 下。

当前目标不是替换主线 v3，也不是改正式出价，而是先做一条可快速验证的外援计算器路线：

- 主要参考 `external_references/AuctionAnalyzer4.13.3` 的组合枚举、均格可达性、价格区间与三档建议；
- 原作者/参考来源：B站猫饭团子uu `https://space.bilibili.com/1981353429`；
- 本支线 UI 修改与计算优化：B站加菲_barista `https://space.bilibili.com/88048665`；
- 可局部吸收 bidking-lab 已验证的实时 packet 输入通道和归档流程；
- 默认放弃 OCR 作为主入口，实时输入优先来自现有 live/Fatbeans packet 输出；
- OCR 只保留为第三级高级/人工补录入口，不参与默认实时推荐；
- 所有新增代码、文档和临时记录先留在本目录，后续经样本验证再决定是否迁移到主线。

2026-06-09 当前可用状态：

- 主线 monitor artifact root 已新增 `ahmad_ref_inputs` 辅助字段；
- 同时新增更通用的 `structured_ref_inputs`，`ahmad_ref_inputs` 作为旧名兼容；
- 字段只汇总 settlement 前 live batch updates，不写 formal，不改正式出价；
- 本支线 Tk overlay 直接读取 `latest_snapshot.json` root 的结构化输入；
- 有 `100204` 总件数或等价公开/手填总件时显示外援参考价；
- 缺总件或 Victor 关键件数组合时会进入带标记的 `ref_prior/count_prior` 兜底，UI 必须保留 `总件估计`、`缺紫金红件数` 等标识；若总件已知但品质分裂过于稀疏，会进入 `sparse_exact_prior` 快路径并标记 `宽约束快速`，这不是截断结果；
- Victor 已按实战文本修正 `100209`：紫色 + 金色 + 红色件数之和，显示为 `紫金红件 N`，桥接字段为 `count_sums.q4q5q6`；
- 旧 `count_sums.q4q5` 只作为历史样本/旧手填兼容，不再作为当前 live 语义；
- action/skill 结果解析支持 `field7`，覆盖 Ahmad `100204` 总件数和普通道具件数结果；
- `100113` 等均格类 action 支持 `0` 作为合法结果；若已发送数值道具、后续同局状态继续推进但缺对应结果包，会生成带 `inferred_zero` 标记的 0 值兜底，真实结果包优先；
- 手动面板支持 `紫金红件` 输入，对应 Victor 的 q4+q5+q6 件数和 `count_sums.q4q5q6`；件数字段只接受整数，`总格/均格` 字段可填小数；
- `均格 + 件数` 会校验 `均格 * 件数` 能否直接对应整数总格；如果 `均格 + 格数` 已经唯一，也会自动回填件数并参与约束，例如 `紫均格=1.8` 时只有 `5件 -> 9格` 合法，`4件 -> 7.2格` 与 `6件 -> 10.8格` 会被拒绝；
- `全总格` fitting 优先使用整数可达格数分配给未直接约束的品质，找不到精确整数解时才退回比例缩放。
- 未直接观测格数/均格的品质，UI 格数范围按可组成形状的 top-3 候选显示，并用总格可行性过滤；不要把该字段理解为唯一真实格数。
- 地图族兼容已覆盖快递/仓库、集装箱、别墅、沉船/活动沉船和 hidden：快递/仓库/集装箱会读取外援 StaticData 对应 tier 与 nest price；hidden 当前本地外援表只有 tier=106，缺专属 nest price 时会明确标记 `fallback_default_price`，不伪造 hidden 价格表。缺总件早期帧的默认中心为快递/仓库 24、集装箱 27、别墅 28、沉船/hidden 33。
- 手填英雄支持 `ahmed/ahmad/ahamed/艾哈/艾哈迈德` 与 `victor/维克/维克托` 别名。
- Aisha 已作为 Hero Ref 参考层接入：`aisha/艾莎` 支持运行 ref_v0；白/绿技能证据用 `split_counts/split_quality_cells/split_avg_cells` 保留原始分桶，只有白+绿两边都齐全且一致时才折叠为 `q1` 白绿合并 exact。
- 手填面板支持白、绿、白绿合并三套输入；white-only 只作为 q1 件数和格子下界，white+green 齐全且 q1 合计栏未被用户手填时才自动填入白绿合计；白/绿 split 与白绿合并 exact 冲突时会返回约束冲突，不静默猜测。
- 手填宽约束使用 `manual_prior` 快速先验枚举：保留用户总件硬约束，避免完整组合枚举卡住 UI；会明确标记 `手动先验`。总件已知但其余证据稀疏时，live 也会走 `sparse_exact_prior` 概率先验快路径，而不是依赖 `max_combos` 截断。
- Tk overlay 已接入主线 `ui_contract.minimap` 只读小地图：有公开轮廓/小地图/结算轮廓时显示品质分布；没有轮廓时显示待机占位。
- 旧 `latest_snapshot.json` 会进入待机：普通快照或已结算快照超过 60 秒，均不再显示旧价格。
- 本目录已从“纯 ignored 外部参考”调整为可版本化支线代码：源码、脚本、文档应提交；`build/`、`dist/`、`__pycache__` 和打包 exe 仍保持 ignored。
- 手填 UI 内部字段名 `q4q5_count` 是历史控件 key；当前用户语义和输出标签均为 Victor `紫金红件 = q4+q5+q6`，写入 `count_sums.q4q5q6`。
- 最新交接与待办以 `HANDOFF_2026-06-09.zh-CN.md` 为准；`HANDOFF_2026-06-08.zh-CN.md` 和 `PROGRESS_2026-06-08.zh-CN.md` 保留历史上下文。

## 边界

本目录原则上不直接修改：

- `src/bidking_lab/**`
- `scripts/run_live_overlay.py`
- `scripts/run_fatbeans_webhook_monitor.py`
- `PROGRESS_V3.md`、`DECISIONS_V3.md`、`OBSERVATIONS_V3.md`

主线 v3 sampler/promotion 变更由另一个窗口继续推进。本支线目前已经使用的主线接点应保持窄而可回滚：

- `src/bidking_lab/live/monitor.py` root artifact 字段 `ahmad_ref_inputs`；
- `src/bidking_lab/live/fatbeans.py` 对 Ahmad/Victor action/skill result 的解析；
- `src/bidking_lab/simulation/hero_skills.py` 对 Victor `100209` 的 q4+q5+q6 语义；
- `tests/test_live_fatbeans.py`、`tests/test_live_monitor.py`、`tests/test_live_overlay.py`、`tests/test_ahmad_ref_engine_public_info.py` 对 bridge、manual 和 ref engine 的回归测试；
- 不改 formal decision、不改 v3 promotion gate、不改主 UI 默认布局。

本目录主要只读主线已有输出，例如：

- `data/logs/live/latest_snapshot.json`
- `data/logs/live/model_eval.jsonl`
- `data/logs/live/raw/archive/complete/*.json`
- `data/samples/fatbeans/*.json`

## 临时文档

- `TEMP_DESIGN_2026-06-08.zh-CN.md`：Ahmed 推理器设计草案。
- `UI_SPEC_2026-06-08.zh-CN.md`：实时 UI 分层与信息密度方案。
- `ATTRIBUTION_AND_BOUNDARIES_2026-06-08.zh-CN.md`：外援来源、署名和代码边界。
- `HANDOFF_2026-06-08.zh-CN.md`：给后续窗口/合并阶段使用的交接记录。
- `EXECUTION_NOTES_2026-06-09.zh-CN.md`：最近实战、UI 调试、轮次语义、样本质量和 v3 promotion 铺垫归纳。
- `HANDOFF_2026-06-09.zh-CN.md`：当前窗口收口交接、最新映射口径、验证结果和新窗口 prompt。

## 当前 prototype

- `src/ahmad_ref_engine.py`
  - 隔离的外援式 `ref_v0` 核心；
  - 解析 `AuctionAnalyzer4.13.3` 反编译 `StaticData.cs` 中的 map->nest、nest price、tier weights；
  - 实现 count vector enumeration、avg-cells reachability skeleton、三档 safety output；
  - 支持 `ahmad_ref_inputs` bridge 与 live batch `field_updates`，可读取 `100204x`、普通道具和公开信息数值；
  - 当前是 first-pass reference，不是完整 MapBidCalculator beam/value 移植。
- `tools/ahmad_tk_overlay.py`
  - 与主线 overlay 同方向的 Tkinter 桌面悬浮窗；
  - 只读 `data/logs/live/latest_snapshot.json`；
  - 主三档优先显示 `ref_v0` 外援参考值；
  - 详情区只显示外援状态、ref 决策/总值/红值、结算与备注；不把 v3 对照值放进主显示；
  - 显示只读小地图、品质计数和无轮廓待机状态。
- `tools/ahmad_live_panel_server.py`
  - 纯 Python stdlib HTTP 服务；
  - 只读 `data/logs/live/latest_snapshot.json`；
  - 提供 `/api/latest` 与浏览器预览；
  - 不 import 主线代码，不写回任何主线状态；
  - 只作为调试/临时验证，不作为目标 UI。
- `tools/smoke_ahmed_ref_samples.py`
  - 只读 `data/samples/fatbeans/fatbeans_valid_ahmed_*.json`；
  - 通过主线 Fatbeans parser 生成 live-like batch state；
  - 用于确认 Ahmed `100204x` / field update 是否能进入隔离 ref_v0；
  - 默认排除结算批次，避免 settlement bucket count 与 Ahmed 绿白合并口径混淆。

启动：

```powershell
.\scripts\start_live_windivert_overlay.ps1 -Restart -PortOnly -PythonPath C:\Python313\python.exe -NoOverlay
.\external_references\ahmad_live_reference_lab\start_ahmad_overlay.ps1 -Restart
```

说明：`-NoOverlay` 会只启动后台 monitor，不启动主线 overlay；随后本脚本启动独立 Hero Ref 小窗。这样只会看到一个 Hero Ref 前端窗口。默认关闭 Hero Ref 会停止 `monitor.lock` 记录的后台 monitor 并清理 lock；如果只是调试/回放，不想关闭 monitor，可给 Hero Ref 启动脚本加 `-KeepMonitorOnClose`。

一键实战启动：

```powershell
.\external_references\ahmad_live_reference_lab\start_ahmad_live.ps1
```

该脚本等价于“后台 WinDivert monitor + 只打开 Hero Ref UI”，不会打开主线 v3 overlay。默认会自动请求管理员权限并重启旧 monitor/旧 Hero Ref；VPN/UU 场景可加 `-BroadSniff -IncludeLoopback`。

等价长命令：

```powershell
C:\Python313\python.exe external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py --snapshot data\logs\live\latest_snapshot.json
```

UI-only exe 打包：

```powershell
.\external_references\ahmad_live_reference_lab\build_ahmad_ref_ui_exe.ps1 -InstallPyInstaller
```

输出位置默认是 `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef\BidKingHeroRef.exe`。这一版 exe 只负责 Hero Ref UI，读取已有 `data\logs\live\latest_snapshot.json`；开发/实战仍推荐用 `start_ahmad_live.ps1` 同时启动后台抓包。完整推广版还需要把 WinDivert monitor、pydivert/psutil 依赖、表文件和 UAC 启动器打进同一个 portable 包。

Portable 应用包：

```powershell
.\external_references\ahmad_live_reference_lab\build_hero_ref_portable.ps1 -PythonPath C:\Python313\python.exe
```

默认输出到 `external_references\ahmad_live_reference_lab\dist\BidKingHeroRefPortable`，其中包含 Hero Ref UI exe、一键启动脚本、WinDivert monitor 脚本、运行代码、processed JSON 和本机 raw tables。该目录用于本机测试；公开传输前请先阅读包内 `TRUST_AND_SECURITY.zh-CN.md`，并谨慎处理 `data\raw\tables`、`data\logs`、样本和截图。若要生成不含 raw tables 的公开安全骨架，可加 `-PublicSafe`，但用户需要自行补齐本地表文件。

真实样本 smoke：

```powershell
C:\Python313\python.exe external_references\ahmad_live_reference_lab\tools\smoke_ahmed_ref_samples.py
```

样本校准默认使用 `data/samples/fatbeans/fatbeans_valid_*` 或 manifest/evaluator strict 口径。`data/logs/live/raw/archive/complete` 只表示结算归档完整，不代表语义可用于正常回归；`fatbeans_mixed_*` 以及同 session 语义矛盾的 raw complete 只作隔离负例。

新增实战样本入库时，先运行主 organizer 补齐 raw/manual unique session，再运行 `scripts/organize_fatbeans_activity_samples.py --apply` 把 2521-2530 / 4521-4530 活动沉船样本移入 `data/samples/fatbeans_activity_20260605_shipwreck`。默认 baseline 应保持无活动图。

当前结论：

- `fatbeans_valid_ahmed_2404_4rounds_2404_1388889349937960_0001.json`：prebid 批次存在 `session.total_item_count=24` 和 q5/q4/q3 avg-cells，`ref_v0` 可 live-ready 输出；
- `fatbeans_valid_ahmed_2406_5rounds_2406_1388889350539399_0001.json`：早期批次有 q5/q4/q3 avg-cells，但缺 `100204` 总件数，`ref_v0` 正确保持 `missing_total_count`；
- `fatbeans_valid_ahmed_2407_2rounds_2407_1388889350416994_0002.json`：同样缺早期总件数，适合用于验证 UI “缺总件数/等待外援输入”提示；
- 这说明 `100204x` 真实样本已经存在，当前关键不是继续调 safety factor，而是保证总件数/均格/公开信息 bridge 不丢字段。

当前 2406 settled snapshot smoke：

```text
ref_v0 status=ok
ref_v0 readiness=review_only
ref_v0 三档=641,005 / 641,005 / 641,005
ref_v0 raw value=754,123
主显示不再使用 v3 fallback 或 ref-v3 差值
红品件数=3 / 3 / 3
notes=settlement_review_total_count;settlement_review_total_grid;settlement_review_known_quality_counts_sum_to_total;nest_price:2047;activity_shipwreck_minus20:2527->2507;tier_prob:105
```

调试 API 可选：

```powershell
C:\Python313\python.exe external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py --project-root C:\xiangmuyunxing\biancheng\2026\bidking-lab --host 127.0.0.1 --port 8788
```

## 第一版成功标准

第一版只要求成为“实战可看的 Ahmed 参考层”，不要求 promotion：

- 能读取现有 live snapshot 或 archive replay，实时识别 Ahmed 局；
- 能把 Ahmad `100204x` 技能结果转成 count/avg-cells 约束；
- 能显示红品数量或红品数量区间，而不是只显示 q6 概率；
- 能给出保守/参考/激进三个估值档，并标明依据来自外援计算器路线；
- 能暴露“低估风险、先验漂移、活动图 fallback、证据不足”等 guard 标签；
- 不接正式出价，不写回主线 v3 状态。
