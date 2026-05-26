# bidking-lab 优化路线图

> 用途：记录 2026-05-26 之后的优化决策、优先级和 TODO。
> 只写可执行方向；过大的想法先拆成验证任务，避免直接重构。
> 实时监控专项设计见 [`realtime_monitoring_design.zh-CN.md`](realtime_monitoring_design.zh-CN.md)。

---

## 当前结论

项目当前不是“功能坏了”，而是进入 **体验、速度、决策质量、实时观测架构** 四条线的优化期。

已验证基线：

- `pytest -q`：431 passed。
- `.\scripts\test_smoke.ps1`：418 passed，13 个真实 OCR 图片回归 deselected。
- `python scripts/demo_scenarios.py`：端到端 demo 正常。
- 后台 MC 慢的首个明确瓶颈是 anthology 地图重复 `flatten_pool`，已用 `SessionTruthSampler` 预编译采样器解决。
- 已新增 `bidking_lab.live` 薄接口层，为未来手填 / OCR / packet 统一观测事件预留接口。
- 启动等待已取消：手填和 tab 浏览不再初始化 OCR，首次 OCR 请求时按需加载模型。

---

## 优先级


| 优先级      | 方向                 | 目标                       | 当前决策                                   |
| -------- | ------------------ | ------------------------ | -------------------------------------- |
| P0       | MC 采样预编译           | 先消掉明显冷启动瓶颈               | 已完成；保留旧 `sample_session_truth` 兼容测试/脚本 |
| P0       | Pytest smoke 加速     | 日常验证不跑真实 OCR 图片回归         | 已完成；`slow` marker + `scripts/test_smoke.ps1` |
| P0       | UI 切换效率            | 切 tab、读数编辑、后台 MC 轮询不互相拖慢 | 读数 fragment 与 hint 独立容器 first cut 已完成；后续按指标拆函数 |
| P0       | 启动去阻塞             | 手填与浏览不等待 OCR                 | 已完成；首次 OCR 操作按需加载模型                       |
| P0.5     | 观测事件接口             | 为手填/OCR/packet 三路输入统一入口     | OCR/手填已镜像到 shadow live state；下一步切换 canonical input |
| P1       | 实时状态机               | 信息变化自动标 dirty、取消旧任务、重算推荐 | 只响应轮次/道具/公开信息等语义事件，不按 heartbeat 重算 |
| P1       | 枚举 / joint 缓存       | 支撑实时刷新，减少重复枚举             | bucket fingerprint cache 已完成；joint cache 按指标再决定 |
| P1       | Session-level 联合候选 | 把仓库大小、均格、均价、总价放到同一个组合评分里 | 已接入分析估算与 UI 联合筛选 tab       |
| P1       | 多级评估 + Pareto      | 出价建议从单一分位数升级为风险/收益/置信度组合 | 状态机稳定后做；秒仓/放仓作为动作层再恢复             |
| P2       | 推理并行               | snipe/pass/ROI 等独立分支并行   | 先向量化和缓存，再考虑线程/进程                       |
| Research | ProtoHub / 网络抓包直读 | 替代或增强 OCR，直接读取当前仓位/物品状态 | 只做离线 fixture → `LiveObservationBatch` 验证      |


---

## 已完成：MC 采样预编译

### 问题

`sample_session_truth()` 每次采样都会解析地图对应 drop pool。普通地图影响较小，但 anthology 地图有 10 个 sub-pool，批量 MC 会重复做同一份 flatten 工作。

### 决策

新增 `prepare_session_sampler()`，把每张地图的 flattened pools、概率、物品面积、品质、价值、巨物标记预编译成数组。UI 的 `_sample_truths_cached()` 改为：

1. 每个 `(map_id, n_trials, seed)` cache miss 时准备 sampler。
2. 用同一个 sampler 连续采样 `n_trials` 次。
3. 保留原 `sample_session_truth()`，避免影响 ROI、脚本和旧测试。

### 实测


| 地图        | 类型                  | 旧 200 次采样 | 新 200 次采样 | 备注                     |
| --------- | ------------------- | --------- | --------- | ---------------------- |
| 2401 未知别墅 | anthology, 10 pools | 2.951s    | 0.012s    | sampler prepare 0.016s |
| 2501 未知残骸 | anthology, 10 pools | 3.002s    | 0.013s    | sampler prepare 0.017s |
| 2405 望族居所 | single pool         | 0.307s    | 0.011s    | sampler prepare 0.002s |


### 验证

- `python -m pytest tests/test_ground_truth.py tests/test_bg_inference.py tests/test_posterior.py -q`
- `python -m pytest -q`
- `python scripts/demo_scenarios.py`

---

## P0：UI Fragment 化

### 背景

此前 `app/streamlit_app.py` 使用一个共用 `_tab_pane = st.empty()`，再用 `_main_tab` 分支渲染读数、出价、联合筛选、ROI。C-45/C-48 后读数页已进入 fragment、hint 已使用独立容器；当前仍需逐步拆函数并观测 rerun 指标，避免读数 widget 与后台 MC 轮询继续互相影响。

### 已完成（2026-05-26 first cut）

- [x] 读数 tab 整块包进 `@st.fragment`，fragment 内自带 `st.container()`。
- [x] `_tab_pane` 不再服务读数页与 hint 页；joint 已恢复为常驻主 tab。
- [x] 保持读数页内部 widget key、hydrate/sync 顺序不变，降低行为回归风险。
- [x] 语法检查与核心回归测试通过。

### 决策

采用渐进式拆分，避免一次性移动上千行 UI 代码：

1. 先把读数页整体放入 fragment，并切断 `_tab_pane` 依赖。（已完成）
2. 再抽出 `render_obs_tab(...)`，保持行为不变。
3. 抽出 `render_hint_tab(...)`，只接收 bundle/state，不直接启动后台任务。（已先用独立 container 渲染）
4. 最后让每个主 tab 都拥有独立 render 函数，逐步淘汰共享 pane 模式。

### TODO

- 用浏览器手测 fragment rerun：改读数页数字时 hint/joint DOM 不应闪动。
- 记录每次切 tab 的 `run_elapsed_ms`，优化前后对比。
- 读数 tab 先拆函数，不改 UI 文案。
- [x] hint tab 脱离 `_tab_pane`，保持现有 `_bg_infer_autopoll_fragment` 行为。
- [x] 手测回归修复：OCR → hint 推理 → 切回读数页时，预览仓库容量使用 `obs_warehouse_cells` 或 `state["warehouse_cells"]` fallback。
- 继续手测：填紫/金均格均价、切 hint、切回，候选预览和 MC bundle 都不丢。

---

## P1：Session-level 联合候选

### 背景

`candidates_for_bucket()` 是单 bucket 枚举。`top_k_for_session()` 现在按红→金→紫→蓝→绿→白的 greedy 顺序扣仓库预算，能工作，但当均格、均价、总价和仓库总格互相制约时，局部 top-1 可能不是全局最优组合。

### 决策

做轻量 beam search，不做 belief propagation：

1. 每个 bucket 先生成 top-N 候选。
2. 组合候选时累加总格数、总价值解释、均格/均价解释分。
3. 用仓库容量、已知低品格数、总件数作为全局约束。
4. 输出全局 top-K session hypotheses，再回填到预览/分析估算。

### TODO

- [x] 复用现有 `JointHypothesis`：per_bucket、total_cells、warehouse_penalty、score。
- [x] 写最小单测：局部 purple/gold top-1 被仓库约束推翻时，全局候选能选可行组合。
- [x] 将 `compute_analytical_estimate()` 优先使用 session-level top-1。
- [x] UI 中恢复联合筛选 tab，展示全局 top-5 组合、容量对比、局部 top-1 差异与评分拆解。

### 已完成（2026-05-26 first cut）

- `compute_analytical_estimate()` 先调用 `joint_top_k_for_session(k=1, per_bucket_top=16, warehouse_slack=5)`。
- joint 覆盖的非白绿、非显式格数 bucket 直接回填 `known_cells` 和 `inferred_count`。
- joint 无结果或未覆盖的 bucket 保留原单桶枚举兜底。
- 新增回归：60 格仓库里紫/金局部 top-1 各为 35 格时，分析估算应使用 `30+30` 的全局可行组合。
- UI 恢复为常驻「联合筛选」tab：不再需要侧栏实验开关；每个 hypothesis 展示仓库剩余/过仓、局部评分、独立 top-1 对比和调整原因。
- 出价推荐页接入折叠的 joint 摘要：作为推理依据层展示，不打开秒仓/放仓动作建议。

---

## P1：多级评估与 Pareto

### 背景

目前出价建议主要看条件 MC 分位数、bucket 后验和实验性的 snipe/pass gate。实际玩家决策需要同时看收益、风险、置信度、道具成本和是否值得秒仓。

### 决策

把多目标决策放在 hint 层：

- 不改 `SessionTruth` 和底层 MC 数据结构。
- 每次 MC bundle 后计算 candidate bid ladder。
- 对每个 bid 计算：EV、P(loss)、P(big_win)、P(miss_good_warehouse)、sample_confidence。
- 展示 Pareto front，而不是只给一个“推荐价”。

### TODO

- 定义 `BidEvaluation`：bid、expected_profit、loss_prob、win_prob、p75_capture、confidence。
- 做 Pareto filter：被另一个点在收益更高且风险更低时剔除。
- UI 展示 3 档：保守 / 均衡 / 激进。
- 低样本时只显示区间，不显示强推荐。

---

## P0.5：观测事件接口与实时状态机

### 背景

后续可能通过 ProtoHub / 抓包只读获得伊森技能里的未知品质格子、仓库大小、
当前局状态等信息。若直接把这些数据塞进 Streamlit state 或 `SessionObs`，会和
OCR、手填路径混在一起，后续很难做实时监控与自动重算。

### 决策

先建立 source-agnostic 观测层：

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

当前已新增 `bidking_lab.live`：

- `FieldUpdate`：逻辑字段更新，例如 `("session", "warehouse_total_cells")`。
- `GridItemObservation`：未来承接伊森未知品质 footprint、抓包 item_id/value。
- `LiveObservationBatch`：一次 UI transaction / OCR / packet tick 的观测批次。
- 来源优先级：`packet > manual > ocr > derived`。
- `event_kind`：仅轮次变化、道具揭示、公开信息变化等语义事件触发重算；`heartbeat` 只承载传输元数据。

### TODO

- [x] 定义薄接口和来源优先级。
- [x] 定义 `LiveSessionState` reducer，解决冲突合并、stale、版本号。
- [x] 增加 adapter：`LiveSessionState` → `SessionObs`。
- [x] 加入离散事件重算门控，避免 packet 心跳造成无意义推理刷新。
- [x] 新增 legacy snapshot adapter，并让 OCR apply / 手填 sync 镜像发送 live batch。
- [x] 补齐 bridge 显式字段等价性：巨物 override、小仓红品、Aisha 可见性、零值与格式化均价。
- [ ] 将推理输入从 legacy `obs` 切到 `LiveSessionState` adapter。
- [ ] 切换前统一覆盖策略：现有 OCR 会覆盖手填，目标 reducer 为 `manual > ocr`。
- [ ] UI 显示每个关键字段来源：手填 / OCR / packet / derived。

### 复杂度评估

| 子任务 | 复杂度 | 风险 | 备注 |
|---|---:|---:|---|
| 事件 dataclass | S | 低 | 已完成 |
| reducer + adapter | M | 低 | 纯函数，可测试 |
| Streamlit 接入 dirty/ready 状态 | M-L | 中 | 要避免 rerun 循环 |
| ProtoHub 离线 parser | M | 中 | 取决于输出格式 |
| 实时监听游戏状态 | L | 中-高 | 取决于协议稳定性 |

---

## P1：枚举引擎优化

### 背景

`candidates_for_bucket()` 典型耗时可接受，但 UI rerun 频繁。优化重点不是改数学，而是避免重复做同一组枚举。

### TODO

- [x] 做 bucket fingerprint：quality、cells、count、value_sum、avg_cells raw、avg_value、huge_band、warehouse、other_known_cells。
- [x] 给 `candidates_for_bucket()` 外包一层 LRU cache；UI 预览、joint、分析估算共享命中结果。
- 当 `total_cells` 和 `count` 都给定时直接返回单候选/空候选。
- 当 `avg_cells` 给定时复用 `enumerate_candidates()` 结果，不再后续重复 `is_compatible()` 两次。

### 已完成（2026-05-26 first cut）

- cache key 包含所有枚举输入以及仓库剩余预算；改变 `other_known_cells` 不会误复用候选。
- 对外继续返回新的 `list`，防止 UI 截断或 mutation 污染共享缓存。
- 实测紫品 `avg_cells=2.5 + value_sum=86490`：cold 枚举约 `22.1ms`；随后 1000 次相同约束命中总计约 `0.39ms`。
- 暂不增加 joint 组合层 cache：其每 bucket 枚举已先受益，先观察组合阶段是否仍是瓶颈。

---

## P2：推理并行

### 决策

暂不先做全局并行。原因：MC 采样预编译后，最大确定瓶颈已消失；盲目并行会增加 Streamlit 状态同步复杂度。

### TODO

- 先采集 `sample_ms/filter_ms/render_ms` 三段指标。
- 将 snipe/pass/analytical/Pareto 分支拆成纯函数。
- 如果单分支仍慢，再用线程池并行独立分支。

---

## Research：ProtoHub / 网络抓包直读

### 目标

验证是否能只读地获得当前仓位、物品 ID、品质、价值、未知品质 footprint 或地图状态，
从而增强甚至替代 OCR。

### 边界

- 只做本机只读观察，不做注入、改包、自动竞价。
- 先确认游戏协议是否明文、是否本地回环、是否加密。
- 先走离线样本：pcap/json fixture → `LiveObservationBatch`。
- 任何实时实现前先检查游戏 ToS 和账号风险。

### TODO

- 明确“ProtoHub”具体工具、仓库或教程来源。
- 抓一段本机 pcap/json，确认是否有可读 payload。
- 建离线 parser：pcap/json → `LiveObservationBatch`，不连接游戏进程。
- 用同一局对比 OCR / 手填 / packet 的字段一致性。
- 如果协议加密或需要 hook/绕过保护，停止该方向。

---

## 下一次开工建议

1. 给关键读数显示来源，并明确 `manual > ocr` 下重新 OCR 的覆盖/保留交互。
2. 将 hint/MC 输入逐步从 legacy `obs` 切到 `LiveSessionState` adapter。
3. 做自动重算状态机：只响应语义事件的 dirty → running → ready，取消陈旧任务。
4. 以运行指标判断是否需要 joint 组合 cache 或进一步枚举剪枝，再做 Pareto 出价评估。
5. ProtoHub 走离线 fixture 验证，与主线并行，不阻塞手填/OCR路径。
