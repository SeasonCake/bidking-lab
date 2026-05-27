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

- [ ] 定义 `InferenceStatus`: `idle / dirty / running / ready / error`。
- [ ] 所有观测变化只标记 dirty，不直接在 UI 控件里启动重算。
- [ ] 后台 worker 监听 fingerprint 变化，自动取消旧任务并启动新任务。
- [ ] UI 显示“当前结果是否过期、来自哪一版观测”。

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
- [ ] 抓一段离线样本，保存为不含敏感信息的 JSON fixture。
- [x] 写第一版宽松 parser：JSON-like fixture → `LiveObservationBatch`。
- [ ] 对比同一局 OCR / 手填 / packet 的字段一致性。

第一版 parser 位于 `bidking_lab.live.packet`，暂不绑定具体抓包工具。它接受普通
dict/JSON fixture，并提取 session、bucket 汇总、公开/可见 item footprint、
round/tool/public event 等字段。真实 ProtoHub 样本拿到后，优先在这个 adapter
中补字段别名，而不是改推理引擎。

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
