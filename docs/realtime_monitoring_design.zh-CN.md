# 实时监控与状态机设计草案

> 目标：为未来 ProtoHub / 抓包直读、OCR、手填三种信息源预留统一接口。
> 当前阶段只做数据契约和路线设计，不连接游戏进程、不抓包、不做自动竞价。

---

## 目标形态

最终 UI 应该从“手动填读数后点击推理”演进为：

1. 监听当前游戏局状态。
2. 自动识别地图、英雄、仓库总格、当前轮次、已揭示道具信息。
3. 信息变化时增量更新 session state。
4. 自动触发 joint / MC / Pareto 重算。
5. UI 标明每条信息来源：手填、OCR、抓包、推导。

---

## 核心原则

### 1. 抓包不是 `SessionObs`

`SessionObs` 是推理层输入，不应该直接绑定 ProtoHub 或 OCR。
所有来源先输出统一事件：

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

这样以后就算 ProtoHub 失败，OCR 和手填仍然能工作。

### 2. 来源优先级明确

冲突时默认优先级：

```text
packet > manual > ocr > derived
```

原因：

- `packet` 是游戏状态直读，理论上最准确。
- `manual` 用于玩家覆盖错误。
- `ocr` 可能误识别，需要低于手填。
- `derived` 是系统推导，永远不能覆盖硬观测。

### 3. 状态机驱动重算

不要让每个 UI 控件各自决定是否重算。未来应由状态机产生事件：

```text
UNKNOWN
  ↓ 识别地图/英雄
MAP_READY
  ↓ 获得仓库大小 / 格子状态
READING_READY
  ↓ 推荐已计算
RECOMMENDATION_READY
  ↓ 新事件到达
STALE → RECALCULATING → RECOMMENDATION_READY
  ↓ 竞拍结束/换图
SETTLED / RESET
```

### 4. 只由离散语义事件触发重算

游戏状态变化应被建模为有限事件，而不是每个抓包 tick 或心跳都重跑推理。
`LiveObservationBatch.event_kind` 当前预留以下边界：

| 事件 | 是否重算 | 含义 |
|---|---:|---|
| `session_started` | 是 | 新一局或地图上下文建立 |
| `round_changed` | 是 | 轮次/阶段改变，公开池可能改变 |
| `tool_revealed` | 是 | 道具使用后产生新的读数或 footprint |
| `public_info_changed` | 是 | 仓库大小、公开品质/物品等硬信息变化 |
| `manual_update` / `ocr_update` | 是 | 当前手填/OCR 路径的兼容入口 |
| `session_settled` | 是 | 结算或清理当前推荐 |
| `heartbeat` | 否 | 仅连接存活、时间戳等传输元数据 |

reducer 仍可以存储 `heartbeat` 元数据并增加 state version，但不会把推理结果标成
过期。未来 packet emitter 必须在游戏事实发生变化时发语义事件，并对重复 payload
按 fingerprint 去重。

### 5. 兼容桥接阶段

当前 Streamlit 仍以 legacy `obs` 字典作为推荐计算输入，同时把变更镜像到
`LiveSessionState`：

```text
现有 OCR apply / 手填 sync → legacy obs（当前 UI / 推理仍使用）
                         ↘ legacy adapter → LiveObservationBatch → shadow LiveSessionState
```

这样可以先验证字段映射、清空事件和来源冲突策略，而不改变已经稳定的 OCR / hint
行为。切换为 live state 驱动推理前必须处理一个行为差异：现有 UI 中重新 OCR 会覆盖
已有手填值，而 live reducer 的目标规则是 `manual > ocr`。届时应让界面明确显示来源
并提供用户确认/解除手填覆盖的操作，而不是静默改变读数。

当前 shadow UI 已显示字段赢家来源，并会列出最近一次被更高优先级来源挡住的更新；
读数页顶部也会显示关键读数字段的来源摘要。这些都只是诊断层，不改变 legacy obs
推理输入。后续 canonical input 切换前仍需要在读数输入区提供明确的“允许 OCR 覆盖手填”交互。

---

## ProtoHub / 抓包方向可行性评估

### 当前参考材料判断（2026-05-26）

- `data/raw/tables` 和 `data/processed` 已覆盖游戏静态表：地图、掉落、物品、英雄、道具仍作为推理主数据源。
- `src/AuctionAnalyzer4.13.3` 是他人的 OCR + 出价计算器，适合参考 OCR ROI、正则解析、均格可达规则和解析枚举；它本身没有 ProtoHub / packet parser。
- 用户提供的视频截图中的 ProtoHub 叠层看起来是离散游戏状态：轮次、估值、品质格/件数、footprint 网格、道具揭示结果。因此后续 packet 接入应发 `round_changed`、`tool_revealed`、`public_info_changed` 等语义事件，而不是按网络 tick 或 heartbeat 重算。

### 可能高价值字段

| 字段 | 对推理价值 | 备注 |
|---|---:|---|
| 地图 ID / 当前地图 | 高 | 可替代 OCR 地图识别 |
| 仓库总格数 | 高 | 当前所有推理的根约束 |
| 当前轮次 / 阶段 | 中 | 用于状态机和自动刷新 |
| 物品 footprint / cells | 高 | 特别适合伊森未知品质轮廓 |
| 物品 quality | 极高 | 若能拿到，可大幅降低不确定性 |
| 物品 item_id / value | 极高 | 若能拿到，接近白盒估价 |
| 道具读数结果 | 高 | 可替代面板 OCR |
| 仓库总格近似值 + 容差 | 高 | 伊森 R1-R4 从底部站位估格数时保留冗余；R5 精确值覆盖 |

### 风险与边界

- 只做本机只读观察。
- 不注入、不改包、不自动竞价。
- 不依赖绕过保护、hook 游戏进程或修改内存。
- 如果协议加密、需要绕过保护、或账号风险不可控，停止该方向。

### 复杂度估计

| 阶段 | 可行性 | 复杂度 | 风险 |
|---|---|---:|---:|
| 离线 pcap/json → `LiveObservationBatch` | 高 | M | 低 |
| 本机只读监听 → 事件流 | 中 | L | 中 |
| 与 Streamlit 状态机联动 | 高 | M | 低 |
| 直接获得 item_id/value | 未知 | ? | 取决于协议 |
| 自动竞价 / 自动点击 | 不做 | - | 高 |

---

## 分阶段路线

### P0.5：观测事件接口（当前已开始）

- [x] 新增 `bidking_lab.live` 薄接口层。
- [x] 定义 `FieldUpdate`、`GridItemObservation`、`LiveObservationBatch`。
- [x] 定义来源优先级：`packet > manual > ocr > derived`。
- [x] 增加 `LiveSessionState` reducer：事件批次 → 当前状态。
- [x] 增加 adapter：`LiveSessionState` → `SessionObs`。
- [x] 定义离散 `event_kind` 与重算门控；`heartbeat` 不置 dirty。
- [x] 增加 legacy snapshot adapter：当前 `obs` 差异 → `LiveObservationBatch`。
- [x] Streamlit 的 OCR apply / 手填 sync 同步写入 shadow `LiveSessionState`。
- [x] 使 shadow 显式字段与现有构建器一致：巨物 override、小仓红品、Aisha 可见性和零值规则。
- [ ] 将 `LiveSessionState` 切为推理 canonical input，并处理 `manual > ocr` 的 UI 交互。

### P1：自动重算状态机

- [x] 定义 `InferenceStatus`: `idle / dirty / running / ready / error`。
- [x] 所有观测变化先标记 dirty；已有 ready 结果后允许受控排队重算。
- [x] 复用后台 worker：live dirty 且已武装时只排队一次，不在初次打开 app 暖机。
- [x] UI 显示“当前结果是否过期、来自哪一版观测”。

### P1：枚举与 joint cache

- [x] `candidates_for_bucket()` fingerprint cache；联合筛选与分析估算自动复用。
- [ ] `joint_top_k_for_session()` cache。
- [ ] 让实时刷新只重算受影响分支。

### P1：Pareto 多级评估

- [ ] 在稳定状态机后接入保守/均衡/激进出价。
- [ ] 输出 EV、亏损概率、胜率、置信度。
- [ ] 秒仓/放仓只作为 Pareto 后的动作建议层，不直接消费原始读数。

### Research：ProtoHub 离线验证

- [ ] 明确 ProtoHub 工具来源、输出格式、是否支持本机只读。
- [x] 抓一段离线样本，保存为本机 JSON 导出并只记录结构化分析结果；原始抓包不提交。
- [x] 写第一版宽松 parser：JSON-like fixture → `LiveObservationBatch`。
- [ ] 对比同一局 OCR / 手填 / packet 的字段一致性。

第一版 parser 位于 `bidking_lab.live.packet`，暂不绑定具体抓包工具。它接受普通
dict/JSON fixture，并提取 session、bucket 汇总、公开/可见 item footprint、
round/tool/public event 等字段。真实 ProtoHub 样本拿到后，优先在这个 adapter
中补字段别名，而不是改推理引擎。

2026-05-27 已拿到第一份 Fatbeans JSON 主会话样本：筛选后 `220` 条 TCP packet
可重组为 `193` 条完整应用层 frame。初步识别出 `msg=0x0022` 出价候选、
`msg=0x0026` 道具/动作候选、`msg=0x0025` 每轮状态同步候选，以及
`msg=0x002d` R5/结算/技能结果候选。详见
`docs/fatbeans_capture_analysis_2026-05-27.zh-CN.md`。

第二份 Fatbeans 样本已验证主要消息稳定，并用截图对齐了道具结果：
`100105 -> 蓝品总格 51`、`100104 -> 白绿总格 10`、`100124 -> 紫品总价 36798`，
以及地图公开信息 `map=2404 -> 金品总格 8`。详见
`docs/fatbeans_capture_analysis_2026-05-27_package3.zh-CN.md`。下一步应把这套
Fatbeans frame 解析沉淀为 normalized packet fixture，再转换为 `LiveObservationBatch`。

伊森模式额外支持 `warehouse_estimated_cells` 与
`warehouse_estimate_tolerance`：R1-R4 底部站位推测不作为严格容量上限，joint
剪枝按近似值加容差留余量；R5 若获得 `warehouse_total_cells`，精确值优先。
R1-R4 不从部分轮廓自动猜 `total_item_count`；R5 若 packet/OCR 已给出完整轮廓、
准确物品列表或总件数，则可以写入 `total_item_count` 作为精确跨桶约束。

获取样本的用户操作步骤见 `docs/protohub_fixture_guide.zh-CN.md`。

### 2026-05-29 Fatbeans live 状态

Fatbeans 方向已经从“离线验证”推进到可用 live shadow 输入：

- 已稳定解析：地图、轮次、英雄、出价候选、道具 action、公开信息、技能 reveal、全库透视、明镜之眼、结算 inventory。
- 已接入 `LiveObservationBatch`：地图/轮次/英雄、扫描/估价/均格结果、艾莎白绿蓝紫轮廓、伊森全轮廓、全库透视总格/总件数、结算品质桶、可见 `grid_items`。
- `100100 全库透视` 可结算前锁定全库 `count + cells`。
- `100134 明镜之眼` 可给全库品质；若同局有伊森已知品质轮廓，runtime ids 完全一致时可合并成全库 `quality + shape + cells`。
- `GridItemObservation.local_index` 已保留，用于后续坐标校准。当前样本支持 10 列规则：

```text
local_index = (row - 1) * 10 + (col - 1)
```

package14-17 进一步确认：只有带 `shape_code` 的轮廓 local 能作为左上角坐标。
宝光/明镜等 quality-only 结果的 local 可能是内部格或高亮格，品质应按 runtime id
合并到轮廓，不能拿 quality-only local 覆盖轮廓 local。`local_index=None`
已由左上角宗教壁画残片、智能手表样本支持为 protobuf 默认值 `0`。

当前仍未完成：

- 滚动仓库时 screen row 与 packet row 的连续性校准。
- 物品底部位置如何转化为仓库高度/仓储下限。
- 堆叠与可滚动视图的 UI 坐标映射。

### 2026-06-02 接入策略更新

实时接入从“等待外部写 JSON 文件”推进到本机包流监听。Fatbeans WebHook
如果账号可用可以继续使用；若 WebHook 需要会员，则不破解 Fatbeans，改走自有 WinDivert
只读抓包入口：

```text
WinDivert sniff
        ↓
run_windivert_live_monitor.py
        ↓
process flow match by BidKing.exe
        ↓
auction frame gate
        ↓
Fatbeans-compatible capture rows in memory
        ↓
build_monitor_artifact_from_payload
        ↓
latest_snapshot.json / sessions.jsonl / model_eval.jsonl / layout_samples.jsonl
        ↓
overlay / Streamlit / future desktop UI
```

WinDivert 路线的关键边界：

- 使用 sniff 模式做只读包观察，不改包、不注入、不自动竞价。
- NETWORK 层 packet 本身没有 PID；用 Windows TCP 连接表把 4-tuple 归因到
  `BidKing.exe`。这也能覆盖 system proxy / TUN / UU 中“端口未知”的情况，只要
  `BidKing.exe` 自身仍建立 TCP 连接。若 UU 完全把游戏流量转入另一个本地代理进程，
  需要实测 `capture_source_status.json` 中是否出现 active flow。
- 默认 broad filter 捕获所有 TCP payload 后只保留 `BidKing.exe` flow；若确认端口稳定，
  可用 `-PortOnly` 降低系统范围。
- 进程级 flow 之后还有对局 frame gate：先按应用层长度重组，再只放行
  `REV push 0x0021`、`SEND 0x0022`、`SEND 0x0026`、`REV push 0x0025`、
  `REV push 0x002d`，并要求有效 session id。商店/账号/设置 JSON、界面交互、
  心跳等待包、非当前局 session 的发送帧会被过滤在推理输入之前。
- `capture_source_status.json` 中 `raw_packets` 表示归因到目标 flow 的 TCP payload，
  `accepted_frames` 表示通过对局 gate 的 frame；`accepted_packets` 是旧兼容别名。
  未进入对局时 raw 增长但 accepted 为 0 属于正常状态。
- `REV 0x0021` 已接入为 `session_started` 初始状态；历史样本显示它通常是点击开始对局后
  第一个有效对局 frame，可提前提供 map、hero、公开信息和部分布局。
- 依赖 `pydivert>=3.0` 和管理员权限；缺依赖时脚本会明确报错，不影响旧 JSON watcher。

Fatbeans WebHook 备用链路：

```text
Fatbeans WebHook POST
        ↓
run_fatbeans_webhook_monitor.py
        ↓
Fatbeans export rows in memory
        ↓
build_monitor_artifact_from_payload
        ↓
latest_snapshot.json / sessions.jsonl / model_eval.jsonl / layout_samples.jsonl
        ↓
overlay / Streamlit / future desktop UI
```

Fatbeans WebHook 关键边界：

- WebHook 请求线程只接收包、转换字段并立即返回 `OpCode=0` 放行，推理在后台 worker 中 debounce 后执行，避免触发 Fatbeans 4 秒超时。
- 仍复用现有 Fatbeans parser、v2 推理、日志 schema 和 overlay；没有新增 OCR 入口，也没有直接 hook 游戏进程或内存。
- 旧 `run_fatbeans_live_monitor.py --watch-dir` 保留用于历史 JSON 回放和样本重跑，不再作为实战实时入口优先项。
- PowerShell 可启动本项目 receiver/overlay，并可选启动 Fatbeans 程序；Fatbeans 的 WebHook URL 和抓包开关目前仍需在 Fatbeans UI 中配置一次，除非后续确认可用 CLI/MCP 控制。

### 2026-05-31 接入策略

短期继续使用 Fatbeans JSON watcher 作为实战采样入口，不再另写一套并行 monitor 主干。
原因是现有脚本已经把来源入口和推理/日志边界拆开：

```text
file / watch-dir / stdin
        ↓
FatbeansCaptureEvents
        ↓
build_monitor_artifact_from_events
        ↓
latest_snapshot.json / sessions.jsonl / model_eval.jsonl / layout_samples.jsonl
        ↓
overlay / Streamlit / future desktop UI
```

后续真实时 feed 的推荐迁移方式是新增 source adapter，让它输出
`FatbeansCaptureEvents` 等价对象，或直接向 `run_fatbeans_live_monitor.py --stdin`
写入同 schema payload。这样可以继续复用现有 artifact、日志、悬浮窗和评估脚本。

只有在 Fatbeans 无法稳定增量导出、或实时 feed 的数据结构与 Fatbeans 差异过大时，
才考虑替换 watcher 进程本身。即便替换，也应保留 `build_monitor_artifact_from_events`
之后的公共链路不变。

已实现：`local_index + shape_code` 现在会转成
`row/col/width/height/bottom_row`，并接入 Fatbeans 导入诊断。导入后可在
“轮廓坐标证据”表里看到 1-based 行列范围。

重要边界：最大 `bottom_row` 暂不作为总格数硬下限。package17 证明最深到第 17 行时，
真实总格为 157，小于 `17 * 10 = 170`，说明 10 列布局中存在空洞或留白。后续应把
最深行作为布局深度特征，结合已知轮廓总格和更多全库样本做软约束，而不是直接过滤 MC。

---

## 对当前优先级的影响

新的推荐顺序：

1. **P0.5 观测事件接口 + reducer**
   shadow 事件流已接入；下一步处理来源展示并切换 canonical input。
2. **Research ProtoHub 离线 fixture**
   packet 可能直接提供 item shape / item id / 公开 footprint，比继续优化现有
   OCR 数字读数更能提升约束质量。先离线 parser，再实时监听。
3. **P1 枚举 / joint cache**
   shape / footprint 约束接入后，缓存和局部分支重算会更重要。
4. **P1 自动重算状态机**
   已有 dirty → 后台 MC 门控，后续主要补 packet 来源和取消/合并策略。
4. **P1 Pareto 多级评估**
   在输入与重算稳定后再给动作建议。
5. **Research ProtoHub 离线验证**
   与上面并行做，但不阻塞当前手填/OCR路径。

---

## 近期不做

- 不把 ProtoHub 直接写进 Streamlit 页面。
- 不让抓包结果直接覆盖 `SessionObs`。
- 不恢复旧秒仓/放仓 UI。
- 不做自动竞价、自动点击、改包或注入。
