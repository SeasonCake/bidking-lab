# Ahmad/Victor Hero Ref 执行记录 - 2026-06-10

这份记录把最近一轮实战反馈、我已经检查过的内容、以及新窗口最值得复用的结论按顺序收口。  
它不是最终 release notes，但它是后续继续修 UI / packaging / smoke 时最直接的工作底稿。

## 1. 当前状态

- Hero Ref 已经跑到实战可用、接近发布的阶段。
- 主线 v3 不在这个支线里推进，仍然保持 shadow-only / audit-only。
- 这个支线现在最重要的不是再加一层推理，而是把已有功能收口成稳定可发版本。

## 2. 我已经核对过的东西

### 2.1 目录与路径

- `external_references/ahmad_live_reference_lab` 已经从“纯外部参考”变成可版本化支线代码。
- `data\logs\live\` 是当前 Hero Ref 运行后应看到的日志位置。
- `full` 包是面向直接分享/直接运行的版本。
- `safe` 包是不给原表时的版本，需要用户自己导入游戏表。

### 2.2 监测和解析

- `load_monitor_tables()` 读到的 `BidMap.txt` 里，4406 这类 map family 是能识别的，不是缺 row。
- 4406 相关会话里，`0x002D` settlement payload 和结算库存是完整的，不是少了一个“结算块”。
- `capture_source_status.json` 没有看到 `dropped_bytes`，没有直接的 monitor 丢包证据。
- 因此，当前更像是价格表 / 活动版本 / 外部表漂移，而不是解析器把某块内容吃掉了。

### 2.3 语义口径

- count / cells / value 已经明确分层。
- count 字段只接受整数。
- avg_cells 字段可以保留用户输入的精度，不要静默截断。
- `0` 均格是合法值。
- `1.8` 和 `1.80` 在 UI 上可以 compact，但引擎要保持 exact float 语义，不要把展示格式当成语义差异。
- `100209` 是 Victor 的 `q4 + q5 + q6` 件数和，不是旧的 `q4 + q5`。
- `100204` 系列是 Ahmad 的总件数 / 均格 / 白绿件数 bridge。
- `0x002D` 主要是 metadata + inventory 事实，不是隐藏的 session capacity source。

## 3. 朋友反馈，按原意记录

### 3.1 公开红轮廓能看到，但不知道具体物品

反馈方向：

- 他能看到抽检或公共抽检亮的红，但不知道具体是什么物品，所以估价不懂。

我的回应：

- 这个方向是对的，公开轮廓应该分成硬约束和软约束。
- 全桶轮廓可以做硬件数 / 硬格数约束；
- 只有单点或模糊轮廓时，先作为下界或软线索，不要硬化成唯一 truth。

当前状态：

- Hero Ref 里已经按“硬桶轮廓 / 软 reveal”分层了。

### 3.2 金均格、小数均格和件数锁定

反馈方向：

- 他提到金均 0 没读到；
- 也提到金均价的小数信息没理解；
- 还举了金均 0.75、均格 4、已经算出金红 7 件，但没有锁定金 4 件 / 红 3 件的例子。

我的回应：

- 这里核心不是“显示成 1.8 还是 1.80”，而是引擎必须保留 exact float。
- `avg_cells`、`count`、`cells` 要分开，不要把一个平均值自动抹平成模糊显示。
- 只知道均格时，要推导候选件数组合，不要直接卡死成单一件数。

当前状态：

- 已经收紧到 exact avg-product 口径。
- `count` 和 `cells` 不能再用一位小数容差硬糊。

### 3.3 三种估价都参照红个数，变成一样

反馈方向：

- 他觉得三种估价似乎完全参照红个数，确定之后三个估价一致，逻辑不如之前那个计算器。

我的回应：

- 这说明不能让 q6 单点支配整套三档结果。
- 价格必须按 count / cells / value 分层，P50、P90 和红件数量不能混成同一个诊断入口。

当前状态：

- Hero Ref 里已经保留了多个视角，不再只看一个红数。

### 3.4 手填区域太难找，迷你版变量太多

反馈方向：

- 详情里的“手动填写”太不整齐；
- 初用的时候想手动填/看个东西要找半天；
- 迷你版里有些变量对用户来说没用，比如来源、状态。

我的回应：

- UI 应该把用户真正关心的前置，不重要的信息放到 hover / detail。
- 手填、详情、minimap 要分层，不要把所有字段都挤成一层。

当前状态：

- 这部分已经朝 compact/minimal 方向调整过。
- 后续只做小修，不再扩成更复杂的 v3 风格。

### 3.5 开局 `?` 英雄名

反馈方向：

- 艾莎 / 艾哈迈德开局有时候是 `?`，第二轮才识别出来。

我的回应：

- 这更像本机 `player_id` 延迟绑定，不是英雄表本身缺失。
- 需要保守绑定，后续在同 session 中回填前序状态，而不是一开始就硬猜。

当前状态：

- 这个问题已经被当成 local-player binding timing 处理，而不是英雄表错误。

### 3.6 结算一直挂着、是否清空、网络卡顿

反馈方向：

- 结算结束后 UI 会挂着；
- 网络卡顿时手填会被打断或者清掉；
- 他们担心这一点会影响下轮次。

我的回应：

- 结算态可以保留，但不能让上一局输入污染下一局。
- 新局开始、session change、stale snapshot 都要清理手填缓存。
- 如果结算态不影响下一轮刷新，它可以挂着；如果会阻塞刷新，就必须清。

当前状态：

- 已做 stale snapshot / session change 清理逻辑；
- 关闭 UI 时 monitor 是否联动关闭也在检查范围内。

### 3.7 release / 说明 / logs

反馈方向：

- 他们要把这版发给别人试；
- 需要知道 logs 放哪；
- 需要知道 `safe` 和 `full` 的区别；
- 需要一个更简单的使用说明。

我的回应：

- `full` 包是给别人直接用的版本；
- `safe` 包不带原始表，适合公开分发但需要用户自己导入表；
- logs 统一写在 `data\logs\live\`；
- 说明里必须写明管理员权限、WinDivert、火绒 / Defender 信任边界。

当前状态：

- 这部分已经进入 release 收口阶段，不再单独扩大功能。

## 4. 这轮最值得带到下一窗口的结论

1. 不要再把 `1.8` 当成糊涂的小数展示，`1.8` 和 `1.80` 只是展示格式问题，语义上要保留 exact float。
2. `count` / `cells` / `value` 一定要分层。
3. 公共红 / 抽检红如果只是 reveal 轮廓，不要直接当成唯一 truth。
4. `0x002D` 更像 metadata + inventory，不像隐藏 capacity source。
5. 这次 4406 的价差更像价格表 / 活动版本 / 外部表漂移，不像缺块。
6. `sparse_exact_prior` 是稀疏局的合理快路径，不是 `max_combos` 截断的替代名词。

## 5. 适合新窗口直接做的检查

1. 用最新样本再确认 Ahmad / Victor / Aisha 的英雄识别、手填清理、轮次切换。
2. 把 full 包在一个干净目录里跑通一次，确认不依赖外部 Python。
3. 检查 `data\logs\live\` 是否能按预期落日志。
4. 关 UI 后确认 monitor 是否联动关闭。
5. 如果继续改 UI，只做小幅布局和提示层次调整，不要再把支线做成另一个 v3。

## 6. 2026-06-10 后续补丁：公开均价与结算态覆盖

本轮基于 `data\logs\live_2026.06.10_ahmed` 继续核验朋友反馈，确认了两个 Hero Ref 支线问题：

1. `public_avg_values` 里的品质均价（例如金均价 `34288.75`、紫均价 `5615.625`）已进入 runtime contract，但 ref_v0 此前没有把它作为件数约束使用。
2. 4406 的 `060929` 样本中，pre-settlement bridge 仍带着 `total_count=39`，但 settlement inventory truth 是 `24` 件、`62` 格、结算值 `477562`；这不是 `BidMap` 缺 row，更像 reset/结算态旧输入残留。

已做补丁：

- `src/ahmad_ref_engine.py`
  - 新增 `avg_values` / `quality_values` evidence；
  - 读取 action `100122-100126` 的品质总价；
  - 读取 `public_avg_values` / `public_numeric_facts` 的 `q4/q5/q6_avg_value`；
  - 品质均价使用小分母有理数约束：`.75 -> /4`、`.625 -> /8`、`25417.80078125 -> /5`，避免按两位小数 rounding 误杀；
  - `avg_value=0` 锁对应品质 count 为 0；
  - `avg_value + quality_value` 可推导 fixed count；
  - 估值优先使用 exact quality value，其次使用 avg value * count，再回退价格表 / grid-conditioned value。
- `src/bidking_lab/live/monitor.py`
  - Hero Ref structured bridge 现在保留 `bucket.*.avg_value` 与 `bucket.*.value_sum`。
- settlement phase：
  - `truth.total_items` / `truth.total_cells` 覆盖 stale bridge total；
  - `final_quality_cells` 覆盖 stale bridge avg/cells，并重新从 settlement count/cells 推导 avg。

验证：

- `py_compile` 通过：`ahmad_ref_engine.py`、`src/bidking_lab/live/monitor.py`。
- focused pytest 通过：`tests/test_ahmad_ref_engine_public_info.py` + Hero Ref bridge tests，共 37 个 case。
- UI 关闭联动 tests 通过：3 个 cleanup case。
- 日志回放：
  - 4 个含公开均价的 Ahmad reset 样本均可达；
  - `34288.75` 完整样本锁到金 4 / 红 3；
  - `5615.625` 样本不再 `no_reachable`；
  - 4406 settled 样本全部 `ok`，其中 `060929` 从 bridge 39 覆盖到 truth 24。

仍未完成：

- 本轮没有重新打包 full/public-safe zip；现有 zip 是旧 commit 构建物，不能代表本轮补丁。
- 本轮没有实际启动 freshly unzipped full 包；只读检查确认旧 full zip 包含 UI exe、monitor exe、raw tables、`data/logs/live/`，public-safe zip 不含 raw tables、包含 `PUT_TABLES_HERE.txt`。

## 7. 朋友反馈的核心待办与明确路径

原则：先做低风险、可快速验证的 UI / contract 收口；不要在 Hero Ref 支线里恢复主线 v3 formal/value sampler，也不要把 Hero Ref 的展示口径提升成主线 truth。

### 7.1 已处理，后续只需回归验证

1. 金 / 紫 / 红均价小数推理
   - 已处理路径：`external_references/ahmad_live_reference_lab/src/ahmad_ref_engine.py`
   - 已覆盖测试：`tests/test_ahmad_ref_engine_public_info.py`
   - 已验证样本：`data/logs/live_2026.06.10_ahmed/live/raw/archive/reset`
   - 保留结论：`34288.75` 可作为件数约束，完整样本已锁到金 4 / 红 3；`5615.625` 不能按两位显示 rounding 误伤。

2. 4406 结算态旧输入污染
   - 已处理路径：`external_references/ahmad_live_reference_lab/src/ahmad_ref_engine.py`
   - 核心映射：settlement `truth.total_items/total_cells` 覆盖 pre-settlement bridge total；`final_quality_counts/final_quality_cells` 覆盖 stale avg/cells。
   - 已验证样本：`windivert_live_2026-06-10_060929_4406_1402770724242732_reset.json` 从 bridge 39 覆盖到 truth 24。

3. live bridge 保留品质价值证据
   - 已处理路径：`src/bidking_lab/live/monitor.py::_ahmad_ref_inputs_from_batches`
   - 已覆盖测试：`tests/test_live_monitor.py::test_ahmad_ref_inputs_bridge_keeps_quality_value_fields`

### 7.2 下一批低风险快修，建议优先顺序

1. Mini 区信息重排：把“来源 / 状态”降级，把“当前不确定性”前置
   - 入口路径：
     - `external_references/ahmad_live_reference_lab/tools/ahmad_live_panel_server.py::summarize_snapshot`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_live_panel_server.py::_ref_input_summary`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py::render`
   - 目标：
     - mini 上方继续保留紫 / 金 / 红件数；
     - 原来的“红品与价值风险”区域改成“还不确定什么”：总件、总格、白绿 / 蓝 / 紫 / 金 / 红 count range；
     - `source/readiness` 只放 detail 或 hover，不占 mini 主信息位。
   - 快速验证：
     - 更新 `tests/test_live_overlay.py::test_overlay_model_uses_ui_contract_shadow_reference` 附近的 mini/interaction 断言；
     - 用一条 4405 `34288.75` 样本确认 mini 显示金 4 / 红 3 或仍显示金 4..8 / 红 0..5 的不确定性。

2. 低品信息 top3 / 下一步该查什么
   - 入口路径：
     - `external_references/ahmad_live_reference_lab/tools/ahmad_live_panel_server.py::_ref_input_summary`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py::_quality_count_summary`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py::_update_detail_rows`
   - 目标：
     - 不做新引擎，只把现有 `quality_count_ranges` / `quality_cells_ranges` 变成“低品未锁定提示”；
     - 例：白绿均格 1.5 时，提示白绿可能件数/格数仍未锁，建议补白绿件数或白绿格数；
     - 如果所有高品已锁但低品未锁，mini 不再只显示红品风险。
   - 快速验证：
     - 新增/更新 `tests/test_live_overlay.py` 的 summary 文本断言；
     - 手工回放 `data/logs/live_2026.06.10_ahmed` 中低品信息不足的样本，确认不覆盖原来的紫金红件数。

3. 公共抽检 / outline 亮红时，显示具体物品或下界，不只显示红色
   - 入口路径：
     - `src/bidking_lab/runtime/snapshot.py::_ui_minimap_contract`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_live_panel_server.py::_minimap_summary`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py::_render_minimap_header`
   - 目标：
     - 如果 public observed item 有 `item_name/item_id/quality/cells`，在 detail/minimap hover 显示物品名；
     - 如果只有 quality / outline，没有 item_id，不要编造物品名，只显示“红品≥1 / 已知轮廓格数”。
   - 快速验证：
     - 复用 `tests/test_live_overlay.py::test_ahmad_server_summary_keeps_public_info_marker_soft`；
     - 加一个负例：只有 quality 没 item_id 时不能显示假 item name。

4. 手动填写区分块排版
   - 入口路径：
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py::_build_manual_panel`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py::_manual_inputs_snapshot`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py::_manual_values_from_summary`
   - 目标：
     - 只做视觉分块：基础信息、白绿拆分、高品件数/格数/均格；
     - 不改变 manual input key，不改变 bridge contract。
   - 快速验证：
     - 跑 `tests/test_live_overlay.py` 中 manual 相关 case；
     - 必须截图检查 compact/details 两种窗口，没有文字遮挡或输入框被挤压。

5. 结算隐藏 / 显示价值按钮
   - 入口路径：
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py::render`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py::_truth_text`
     - `external_references/ahmad_live_reference_lab/tools/ahmad_live_panel_server.py::summarize_snapshot`
   - 目标：
     - 默认可以保守隐藏结算总值或保持现状加按钮，待确认；
     - 只影响 UI 显示，不改 `truth.total_value` contract。
   - 快速验证：
     - 加 UI state 单测：隐藏时 mini/detail 不显示金额，显示时恢复；
     - 结算态回放确认不影响 ref evidence。

### 7.3 需要日志或截图后再动

1. 网络卡顿导致自动清空 / 手填不可填
   - 先看路径：`data/logs/live_2026.06.10_ahmed/monitor_errors.jsonl`、`capture_source_status.json`、`latest_snapshot.json`。
   - 当前观察：已有 `KeyError: 2527` 更像旧主线 artifact 异常，不应直接归因到 Hero Ref UI。
   - 下一步证据：朋友详细 24 局截图 / 对应 raw 文件名 / 发生时间点。

2. 置顶开关
   - 入口路径：`external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py` 中 `root.attributes("-topmost", True)`。
   - 当前建议：默认置顶保持；如果要加开关，做成小图标按钮，不要扩大 mini 面板。
   - 需要验证：多显示器、游戏全屏/窗口化、鼠标穿透期望。

3. full 包 clean unzip 实跑
   - 构建路径：`external_references/ahmad_live_reference_lab/build_hero_ref_portable.ps1`
   - 验证路径：
     - 解压到临时干净目录；
     - 运行 `Start-HeroRef.bat`；
     - 确认 `data/logs/live/latest_snapshot.json`、`monitor.lock`、`monitor.stdout.log` 落在包内 `data/logs/live/`；
     - 确认不用外部 Python。
   - 注意：本轮补丁后必须重新打包，旧 zip 不能代表当前代码。

### 7.4 已落地的低风险 UI 修复（2026-06-10）

1. mini 主区信息重排
   - 已做：
     - `红品与价值` 中原 `风险` 行改成 `低品件`；
     - `当前建议` 中原 `来源 / 状态` 改成 `总格 / 输入`；
     - `source / readiness / diagnostics` 仍保留在详情区，不占 mini 主信息位。
   - source -> output：
     - `ahmad_ref_engine.as_dict().quality_count_ranges` 中的 `q1/q3` -> server `red.uncertainty_summary` -> Tk `红品与价值 / 低品件`；
     - `reference.total_grid_range` -> Tk `当前建议 / 总格`；
     - `evidence.ref_input_summary` 的 `总件 / 总格 / 估总格` 前两段 -> Tk `当前建议 / 输入`。
   - 显示口径：
     - 未锁值为显示摘要，不回灌 engine，不作为主线 truth；
     - `evidence.min_counts` 与 live minimap 已见红下界会抬高未锁摘要中的对应品质下界；
     - 为避免和上方紫 / 金 / 红件数重复，低品件只显示白绿 / 蓝，例如 `未锁 白绿6/9/12 蓝8/11/15`。

2. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_live_overlay.py -q` -> 87 passed
     - `git diff --check -- external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_overlay.py` -> 仅 CRLF warning
   - 视觉验证：
     - 用主屏左半边截取 compact Tk，结算态和临时 bidding 态均无明显重叠；
     - bidding 态关键行可见：`未锁 白绿6/9/12 蓝8/11/15`，`输入 总件 33 · 估总格 76 / 78 / 80格`。

3. 剩余待做
   - manual 表单分块排版还没动；
   - 本轮代码后未重新打 full/public-safe 包，clean unzip 仍需重打包后验证。

### 7.5 已落地的公共抽检 / outline 提示修复（2026-06-10）

1. 已做
   - `src/bidking_lab/live/monitor.py`：
     - `revealed_items_detail` 现在保留 `item_name`；
     - source -> output：`FatbeansObservedItem.item_id` + `tables.items[item_id].name` -> `public_info_rows[].revealed_items_detail[].item_name`。
   - `src/bidking_lab/runtime/snapshot.py`：
     - public/action quality marker 不再因为有 `item_id` 被跳过；
     - 已知物品会带 `item_id/item_name/display_label/shape_key/cells` 进入 `ui_contract.minimap.items[]`。
   - `external_references/ahmad_live_reference_lab/tools/ahmad_live_panel_server.py`：
     - 有 `item_name` 时，tooltip 显示物品名 + 品质 + 轮廓；
     - 没有 `item_name/item_id` 时，只显示下界，例如 `红品≥1；轮廓 2x2/4格；公共抽检`，不编造物品名。

2. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile src\bidking_lab\live\monitor.py src\bidking_lab\runtime\snapshot.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py`
     - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_live_monitor.py tests\test_runtime_snapshot.py tests\test_live_overlay.py -q` -> 152 passed
     - `git diff --check -- src\bidking_lab\live\monitor.py src\bidking_lab\runtime\snapshot.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_monitor.py tests\test_runtime_snapshot.py tests\test_live_overlay.py` -> 仅 CRLF warning
   - 视觉验证：
     - 用主屏左半边截取 details 小地图 tooltip；
     - 未知 public marker 显示：`红品≥1；轮廓 2x2/4格；公共抽检`；
     - 命名 public marker 显示：`民用垂直起降飞行器；红品；轮廓 2x2/4格；公共抽检`。

3. 剩余待做
   - manual 表单分块排版还没动；
   - 本轮代码后未重新打 full/public-safe 包，clean unzip 仍需重打包后验证。

### 7.6 已落地的结算隐藏 / 显示价值按钮（2026-06-10）

1. 已做
   - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py` 新增 header 按钮：
     - 默认 `藏价`，保持原来的结算金额直接显示；
     - 结算态点击后切到 `显价`，金额位置显示 `已隐藏`；
     - 非结算态按钮置灰，不改变任何字段。
   - source -> output：
     - `truth.total_value`、`reference.conservative/balanced/aggressive`、`red.value_range` 仍保留在 summary；
     - 只在 Tk render 层用 `已隐藏` 替换可见金额；
     - 件数、格数、紫金红/低品信息不隐藏。

2. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_live_overlay.py -q` -> 90 passed
     - `git diff --check -- external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_overlay.py` -> 仅 CRLF warning
   - 视觉验证：
     - 用主屏左半边截取 compact Tk；
     - 默认显示：估价 / 结算 / 差值仍显示原金额；
     - 隐藏后：三张价格卡、红值、当前最高均显示 `已隐藏`，按钮变 `显价`，无重叠。

3. 剩余待做
   - manual 表单分块排版还没动；
   - 本轮代码后未重新打 full/public-safe 包，clean unzip 仍需重打包后验证。

### 7.7 已落地的 hover 文案澄清（2026-06-10）

1. 已做
   - `藏价 / 显价` tooltip 改成明确文案：
     - `隐藏结算金额，想自己看结算时用；只影响界面，不影响计算`
     - `显示被隐藏的结算金额；只影响界面，不影响计算`
     - 非结算态：`结算态可隐藏金额；当前未结算`
   - footer `GitHub` hover 不再显示 URL，改为：`如果觉得不错，就给一个免费的 Star 吧！`
   - 补充 / 调整了几个容易误解的 header hover：
     - `详情`：展开 / 收起详情、小地图和手动填写区；
     - `手填`：断网或识别缺项时补总件、均格、件数；
     - `地图`：悬停预览，点击固定 / 取消固定；
     - `关闭`：说明会关闭 Hero Ref，并在启动脚本场景下清理监控进程。

2. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_live_overlay.py -q` -> 91 passed
     - `git diff --check -- external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_overlay.py` -> 仅 CRLF warning
   - 视觉验证：
     - 用主屏左半边截取 `藏价` 和 footer `GitHub` hover；
     - tooltip 可读，无明显遮挡；GitHub hover 不再暴露 URL。

### 7.8 已落地的 manual 表单分块排版（2026-06-10）

1. 已做
   - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py`：
     - 新增 `MANUAL_BASE_FIELDS`、`MANUAL_QUALITY_ROWS`、`MANUAL_EXTRA_FIELDS`；
     - 详情态 manual 区改为计算器式表格：顶部基础字段，下面按 `品质 / 均格 / 件 / 格` 行列填写；
     - 保留原 manual 输入 key，不改 `_manual_inputs_snapshot`、自动填入、均格小数派生或 live merge 逻辑。

2. source -> output 契约
   - `MANUAL_BASE_FIELDS` / `MANUAL_QUALITY_ROWS` / `MANUAL_EXTRA_FIELDS` -> Tk `self.manual_entries[key] / self.manual_vars[key]`；
   - 所有旧 key 仍存在且不重复：`hero/map_id/total_count/total_cells/total_avg`、`white/green/q1/q3/q4/q5/q6` 的 `avg/count/cells`、`q4q5_count`；
   - 表格只影响显示和查找路径，不影响 engine 语义、manual snapshot 字段名或桥接字段。

3. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py::test_ahmad_manual_field_layout_preserves_input_contract tests\test_live_overlay.py::test_ahmad_manual_snapshot_allows_total_avg_and_zero_gold tests\test_live_overlay.py::test_ahmad_manual_inline_derivation_covers_all_qualities_and_totals tests\test_live_overlay.py::test_ahmad_manual_state_auto_resets_on_settlement_and_session_change -q` -> 4 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 92 passed
   - 视觉验证：
     - 用真实物理像素全屏截图后裁主屏左半边，确认展开态 manual、证据/参考、小地图、footer 可见；
     - manual 表格无明显遮挡、重叠或文本溢出；显示顺序为基础字段 -> 白/绿/白绿/蓝/紫/金/红 -> 紫金红件。

4. 剩余待做
   - 本轮代码后仍未重新打 full/public-safe 包，clean unzip 仍需重打包后验证；
   - 如果朋友后续 24 局图里出现手填状态被 live 刷新清空，需要按对应 log/session 复现，不从 UI 排版推断原因。

### 7.9 已核对并撤回的 Hero Ref formal mode 默认切换（2026-06-10）

1. 结论
   - 撤回“默认启动口径改回 `v2`”这一步；`apps/hero_ref/Start-HeroRef.ps1`、`external_references/ahmad_live_reference_lab/start_ahmad_live.ps1`、`scripts/start_live_windivert_overlay.ps1`、`scripts/run_fatbeans_webhook_monitor.py` 默认仍为 `v3_practical`。
   - `v2` 不是原作者 `AuctionAnalyzer4.13.3` 路线；它是 bidking-lab 的旧 MC baseline。不能用“主线 v3 不 promotion”推导出“Hero Ref 默认切 v2”。
   - Hero Ref 当前主报价仍以 `external_references/ahmad_live_reference_lab/src/ahmad_ref_engine.py` 的 `ref_v0`/原作者参考路线承接；monitor `formal_mode` 影响的是 live artifact/UI contract 的 baseline 与对照字段。

2. source -> output 边界
   - 启动默认：`FormalMode=v3_practical` / `--formal-mode v3_practical` -> `build_monitor_artifact_from_events(... formal_mode="v3_practical")` -> 若 v3 practical rows ready，则 `artifact.bid_rows` / `ui_contract.baseline` 使用 v3 practical formal rows，同时保留 `v2_bid_rows` reference；
   - Hero Ref 面板主报价：`snapshot` -> `run_reference_engine(snapshot)` -> `ref_result`；ready 时 conservative / balanced / aggressive 主要来自 `ref_v0`，并把 monitor baseline 作为对照/风险信息；
   - 主线 v3 仍保持 shadow-only / audit-only 记录状态；不要把 Hero Ref 的显示口径提升成主线 truth，也不要恢复 formal/value sampler 主线正式接入。

3. 剩余待做
   - 继续用 Ahmad/Victor/Aisha 与朋友 24 局 log 检查 `v3_practical` baseline 对照是否会误导 UI 文案；如果误导，优先改 Hero Ref 展示标签/来源说明，而不是直接切到 `v2`；
   - 重打 full/public-safe 包前，重新验证启动脚本默认 formal mode、日志目录、无外部 Python 依赖和 clean unzip。

### 7.10 已补充的 UI 展示层 diagnostics 日志（2026-06-10）

1. 已做
   - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py` 新增展示层日志：
     - 输出文件：`data\logs\live\hero_ref_ui_summary.jsonl`（跟随 `latest_snapshot.json` 所在目录）；
     - 写入时机：`render` / `render_standby` / `render_missing` 后，也就是用户实际看到的状态；
     - 去重：同一展示状态不重复刷日志，避免每秒追加相同内容。

2. 记录字段
   - `context`：hero / map / round / phase / session；
   - `reference`：ref_v0 展示价、v3 对照、价差、来源和 note；
   - `red`：红件/红格/红值、紫金件、低品未锁摘要；
   - `evidence`：ref 输入摘要、公开数值摘要、minimap 品质摘要、manual overlay 标记、展示诊断；
   - `ref_v0.evidence`：source_notes、fixed/min counts、avg_cells、quality_cells、avg_values、quality_values；
   - `truth`：结算总值/总件/总格/q6；
   - `settlement_values_hidden`：结算藏价状态。

3. 对应排查点
   - 金均价 / 0 均价有没有进入 ref_v0：看 `ref_v0.evidence.avg_values` 与 `source_notes`；
   - “明知金红件数但没锁定”：看 `fixed_counts`、`min_counts`、`quality_values`、`avg_values` 和 `quality_value_*` notes；
   - 结算估价异常：看 `reference.balanced`、`truth.total_value`、`ref_minus_v3_balanced`、`settlement_values_hidden`；
   - 手填被 live 刷新或叠加：看 `render_mode`、`manual_active`、`evidence.manual_overlay`；
   - 公共抽检/小地图信息不足：看 `minimap.summary_text`、`quality_counts`、`evidence.public_numeric_summary`。

4. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py src\bidking_lab\runtime\snapshot.py src\bidking_lab\live\monitor.py`
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 93 passed
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> 33 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_monitor.py -q` -> 46 passed
     - `C:\Python313\python.exe -m pytest tests\test_runtime_snapshot.py -q` -> 18 passed
     - `C:\Python313\python.exe -m pytest tests\test_fatbeans_webhook_monitor.py::test_live_starters_default_to_v3_practical_formal_mode -q` -> 1 passed

### 7.11 已归档的新优化与排查计划（2026-06-10）

1. 已做的低风险 UI / 诊断项
   - 置顶开关：
     - `external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py` 在关闭按钮左侧新增小 `T`；
     - 默认仍置顶；点击后切换为自由窗口，再点恢复置顶；
     - hover：`置顶中；点击切换为自由窗口` / `自由窗口；点击恢复置顶`；
     - 小地图浮窗与固定小地图同步该 topmost 状态。
   - 详情态诊断包导出：
     - 只放在详情态小地图标题行，简化态不显示；
     - 输出目录：`latest_snapshot.json` 同目录下 `exports\`；
     - zip 内容包含当前 `latest_snapshot.json`、raw capture / raw jsonl、`hero_ref_ui_summary.jsonl`、当前 UI summary、manifest；
     - hover 会说明导出绝对目录和用途，导出后 hover 改为精确 zip 路径。
   - 连续采样独立性：
     - `hero_ref_ui_summary.jsonl` 追加 `source_files.file/raw_capture/raw_capture_jsonl`；
     - 后续统一分析时，样本可按 `session_id + round/phase + raw_capture_jsonl + logged_at/render_mode` 分组；
     - 不要求每局结束后手动跑 `.\scripts\post_game_live.ps1 -SinceHours 72`；连续采样结束后统一导出或统一分析。

2. 已归档但未在本轮实现的计划
   - formal-mode / ref_v0 边界：
     - 继续保留 `v3_practical` 默认；
     - 下一步要核实 UI 文案中 `v3_balanced`、`ref_minus_v3`、baseline source 是否会误导成正式报价；
     - 若误导，优先改文案与标签，例如明确 `ref_v0 主报价 / monitor baseline 对照`，不直接切 `v2`。
   - 价值均价 / 总价约束：
     - `公开随机 N 件均价` 默认不作为核心需求，只可保留为风险/参考；
     - `所有藏品均格`、品质均格仍是计算器核心输入；
     - 品质均价优先用于件数锁定；品质总价可作为 exact / lower-bound 约束缩小枚举，但需要逐样本验证是否会过硬；
     - 若 parser/公开信息来源不能保证 exact，应降级为 soft constraint 或只作为日志诊断。
   - 结算异常：
     - 当前未宣称已修复 728211 / 685641 / 477562 这类异常；
     - 后续拿到错误样本后，按 `price table / activity version / external table drift / parser` 顺序排查；
     - 不优先当 missing settlement block。
   - 手填 vs 自动抓取模式拆分：
     - 方向认可：默认自动抓取，手填区灰掉不可编辑；
     - 点击模式按钮后进入手填，启用输入，并断开自动叠加/实时刷新对 manual 的影响；
     - 需要先设计状态机：`auto_live`、`manual_editing`、`manual_applied`、`return_to_live`，并保证不静默清空用户输入。
   - 下一步信息提示：
     - 目标是在 mini 版给出“再开哪个信息更能锁方案”；
     - 默认策略从低品到高品，优先锁白绿/蓝/低品质总格，再辅助红品和价值判断；
     - 需要基于当前 posterior/ref_v0 候选范围计算信息增益或至少给规则化 top 3，避免硬编码文案。
   - 道具/公开信息映射审计：
     - 需要系统核对 `终极审计`、`全知全能`、`明镜之眼`、`珍品均格`、`珍品均价` 等少见来源；
     - 输出目标是 source -> transform -> ref_v0/manual/UI 的映射表；
     - 重点确认有用字段是否进入 `structured_ref_inputs` / `public_numeric_facts` / minimap，而不是只留在 raw log。
   - UI 实机检查：
     - 当前代码层和测试通过；手填排版、置顶、导出按钮仍需实机确认；
     - 截图仍按真实全屏物理像素后裁主屏左半边，不用局部不完整截图判断布局。

3. 本节验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py::test_ahmad_topmost_toggle_updates_root_and_popups tests\test_live_overlay.py::test_ahmad_export_diagnostic_package_collects_snapshot_raw_and_ui_log tests\test_live_overlay.py::test_ahmad_summary_diagnostic_log_records_display_ref_inputs tests\test_live_overlay.py::test_ahmad_hover_copy_keeps_settlement_and_github_clear -q` -> 4 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 95 passed
     - `C:\Python313\python.exe -m pytest tests\test_fatbeans_webhook_monitor.py::test_live_starters_default_to_v3_practical_formal_mode -q` -> 1 passed

### 7.12 手填 / 实时模式回跳与中文地图名（2026-06-10）

1. 已做
   - 顶部 `手填` 改为双向模式按钮：
     - 实时态显示 `手填`，点击展开详情并启用手填输入；
     - 手填编辑态或手动叠加态显示 `实时`，点击返回 live 主展示；
     - 返回实时时不清空手填内容，只禁用输入并停止手填叠加。
   - 手填输入默认灰掉不可编辑；进入手填后启用 `应用并启用` / `填入当前`，live 仍继续监测和刷新最新 snapshot。
   - auto-sync 只在非手填编辑态写入手填字段，避免用户输入中途被 live 覆盖。
   - 无 live 时先手填，不再把手填绑定到 `"manual"` 会话；第一帧 live 到来后可叠加当前 live，并在之后按真实 session_id 判断换局清空。
   - 手填地图支持中文名：
     - `养生学家居所`、`2404 养生学家居所`、`2404` 都会解析为 `map_id=2404`；
     - 自动填入当前 live 地图时显示为 `2404 养生学家居所`；
     - 未识别中文地图名会显示错误，不静默当作空 map。

2. source -> transform -> output 边界
   - 地图来源：外援 `AuctionAnalyzer4.13.3` 的 `StaticData.cs` -> `ahmad_ref_engine.load_reference_static_data().map_nests` -> overlay 手填 map lookup；
   - 手填输入：`manual_entries["map_id"]` 中文/数字文本 -> `_manual_map_id_from_text` -> manual snapshot 顶层 `map_id` 与 `ui_contract.context.map_id`；
   - 展示：live prefill 用 `_manual_map_display_value`，只影响输入框展示；传给 ref_v0 的仍是整数 `map_id`；
   - 模式：`auto_live` / `manual_editing` / `manual_applied` / `return_to_live` 只影响 overlay 选择 live summary 还是 manual overlay summary，不停止 monitor 进程。

3. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 99 passed
     - `git diff --check -- external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_overlay.py` -> 仅 CRLF/LF 工作区提示，无空白错误
   - 未做：
     - 本轮未重新打包；
     - 未做真实窗口视觉截图，仍需实机确认按钮文字、灰态输入和手填回跳体验。

### 7.13 手填擦除边界与项目级映射来源（2026-06-10）

1. 擦除 / 覆盖规则
   - 同一局 live 普通刷新不能擦除手填，也不能覆盖用户正在填写的字段。
   - `monitor_restarted` / 普通 stale 只说明监控或 snapshot 状态变化，不再触发手填整体清空。
   - 只有明确下一局或明确本局结束才清空：
     - `stale.reason=session_ahead`；
     - `session_id` 从已绑定局变成另一个局；
     - `phase=settled` 且 `truth.available=true`。
   - 无 live 先手填时，第一帧 live 不清空；叠加成功后绑定真实 `session_id`，后续再按上述规则判断。

2. 项目级映射
   - 手填地图名 lookup 已改为优先读取 bidking-lab 根数据：
     - `data/processed/maps.json`；
     - 外援 `AuctionAnalyzer4.13.3` 的 `StaticData.cs` 仅作 fallback。
   - 这样 `3101 未知快递` 等项目表中存在但外援表未必覆盖的地图编号也能解析。
   - item 名称链路维持项目主表：
     - `data/processed/items.json` / `items_droppable.json` / `battle_items.json`；
     - live monitor 已通过项目 `Item` 表给 `action_result_rows`、`public_info_rows`、`minimap_grid_items` 透传 `item_name`；
     - overlay tooltip/小地图继续消费这些字段，不从外援表反推物品名。

3. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 102 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_monitor.py::test_public_info_rows_attach_item_names_to_revealed_details tests\test_live_monitor.py::test_minimap_table_shape_requires_cell_count_match tests\test_runtime_snapshot.py::test_ui_contract_minimap_includes_quality_only_markers tests\test_runtime_snapshot.py::test_ui_contract_minimap_preserves_named_public_marker -q` -> 4 passed
     - `git diff --check -- external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_overlay.py external_references\ahmad_live_reference_lab\EXECUTION_NOTES_2026-06-10.zh-CN.md` -> 仅 CRLF/LF 工作区提示，无空白错误

### 7.14 少见道具 / 公开信息 diagnostic-only 日志（2026-06-10）

1. 已做
   - runtime UI contract 新增 `diagnostics.rare_signals`：
     - action：`100114 珍品均格`、`100121 终极审计`、`100126 珍品估价`、`100127 全知全能`、`100134 明镜之眼`；
     - public info：`200016 红均格`、`200031-200034 随机公开均价`、`200035 全均价`、`200036-200038 紫/金/红均价`；
     - 每项记录 `label`、`semantic`、`ref_v0_role`、`result/value`、`revealed_items`、`has_revealed_detail`。
   - ref_v0 对暂不参与推理的来源只写 source_notes，不加约束：
     - `100121` -> `action_100121_total_value_diagnostic_only`；
     - `100127` -> `action_100127_all_items_diagnostic_only`；
     - `100134` -> `action_100134_all_item_quality_diagnostic_only`；
     - `200035` -> `public_total_avg_value_diagnostic_only`。
   - overlay 的 `hero_ref_ui_summary.jsonl` 新增 `diagnostics.rare_signals`，便于连续采样后按局筛选少见信息命中与是否参与 ref_v0。
   - 详细界面诊断包导出保持 diagnostic 用途：zip 包含 `latest_snapshot.json`、UI summary log、raw capture / jsonl 以及当前 summary，不包含截图。

2. source -> transform -> output 边界
   - `action_result_rows` / `action_send_rows` -> `ui_contract.diagnostics.rare_signals.actions` -> `summarize_snapshot(...).diagnostics.rare_signals` -> `hero_ref_ui_summary.jsonl`。
   - `public_info_rows` -> `_ui_public_numeric_contract` 与 `diagnostics.rare_signals.public_info`：
     - 紫/金/红均价、红均格、品质总价仍按已有 ref_v0 路线进入约束；
     - 随机公开均价只作为 soft value floor / diagnostic；
     - 全均价、终极审计、全知全能、明镜之眼先 diagnostic-only，不改变报价。

3. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile src\bidking_lab\runtime\snapshot.py external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - `C:\Python313\python.exe -m pytest tests\test_runtime_snapshot.py::test_ui_contract_records_rare_signals_as_diagnostics tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_marks_rare_actions_diagnostic_only_without_constraints tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_marks_total_avg_value_public_info_diagnostic_only tests\test_live_overlay.py::test_ahmad_summary_diagnostic_log_records_display_ref_inputs tests\test_live_overlay.py::test_ahmad_server_preserves_rare_signal_diagnostics -q` -> 5 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py::test_ahmad_export_diagnostic_package_collects_snapshot_raw_and_ui_log tests\test_runtime_snapshot.py::test_ui_contract_exposes_public_numeric_soft_facts tests\test_live_monitor.py::test_write_monitor_logs_updates_latest_and_jsonl tests\test_live_monitor.py::test_ahmad_ref_inputs_bridge_keeps_quality_value_fields tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_public_quality_avg_value_decimal_filters_count tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_quality_value_sum_and_avg_value_derive_count -q` -> 6 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 103 passed
     - `C:\Python313\python.exe -m pytest tests\test_runtime_snapshot.py tests\test_ahmad_ref_engine_public_info.py -q` -> 54 passed
     - `git diff --check -- src\bidking_lab\runtime\snapshot.py external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_runtime_snapshot.py tests\test_ahmad_ref_engine_public_info.py tests\test_live_overlay.py` -> 仅 CRLF/LF 工作区提示，无空白错误
   - 未做：
     - 未重新打包；
     - 本轮未调整 Tk 布局，因此未做真实窗口视觉截图；导出按钮路径由单测覆盖，实机布局仍待后续统一确认。

### 7.15 mini 候选 / 下一步建议与诊断包 manifest（2026-06-10）

1. 已做
   - 手填 hover 文案补充“编辑时自动抓取不会覆盖当前输入”，明确手填态不会被 live 覆盖。
   - mini `当前建议` 卡中：
     - `总格` 行改为 `候选`，展示 `candidate_summary`，优先显示总件 / 总格候选；
     - `输入` 行改为 `下一步`，展示 `next_info_hint`，优先提示补白绿/蓝件数或均格，其次补总件、总格/全均格、金/红均价或总价；
     - 上方 `红品与价值` 的红件、红格、紫金件、红值、低品件保持不变。
   - server summary 新增：
     - `evidence.candidate_summary`；
     - `evidence.next_info_hint`。
   - manual overlay summary 复用同一规则，手填模式也能显示候选和下一步提示。
   - 诊断包 `BUILD_EXPORT_MANIFEST.json` 补充：
     - `version`：schema / ui_contract schema / source file / snapshot created_at；
     - `parameters`：n_trials / roi_trials / shadow_trials / formal_mode / hero / map / round / phase；
     - `current_summary`：当前 readiness、candidate_summary、next_info_hint、rare_signal_summary；
     - `log_summary`：log dir、latest_snapshot、UI summary、model_eval、monitor_errors 的存在性、大小和 mtime。

2. source -> transform -> output 边界
   - `ref_result.evidence.total_count` + `ref_result.total_grid_range` -> `_candidate_summary` -> `summary.evidence.candidate_summary` -> mini `候选` 行 / `hero_ref_ui_summary.jsonl` / 诊断包 manifest。
   - `ref_result.quality_count_ranges` + `evidence.min_counts` -> `_next_info_hint` -> `summary.evidence.next_info_hint` -> mini `下一步` 行 / `hero_ref_ui_summary.jsonl` / 诊断包 manifest。
   - 手填 hover 只改 tooltip 文案，不改变手填/自动状态机；live 仍继续监测，但手填编辑态不覆盖用户输入。

3. 验证
   - 已跑：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py::test_ahmad_export_diagnostic_package_collects_snapshot_raw_and_ui_log tests\test_live_overlay.py::test_ahmad_overlay_mini_input_text_keeps_compact_totals tests\test_live_overlay.py::test_ahmad_overlay_mini_candidate_and_next_info_use_actionable_fields tests\test_live_overlay.py::test_ahmad_server_candidate_summary_and_next_info_hint tests\test_live_overlay.py::test_ahmad_manual_toggle_returns_to_live_without_clearing_inputs tests\test_live_overlay.py::test_ahmad_summary_diagnostic_log_records_display_ref_inputs -q` -> 6 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 105 passed
     - `git diff --check -- external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_overlay.py` -> 仅 CRLF/LF 工作区提示，无空白错误
   - 未做：
     - 未重新打包；
     - 本轮未做真实窗口截图；这次只替换同一 mini 行位的标签和值，实机视觉仍需下一轮统一确认。

### 7.16 真实样本回放与 public 均价 fallback（2026-06-10）

1. 已做
   - 用真实 Fatbeans 样本跑 Hero Ref pre-settlement 链路：
     - Ahmad 22 份、Victor 6 份全量；
     - Aisha 按 map/kind 抽 24 份代表样本；
     - 路径：`.tmp/codex/hero_ref_real_sample_audit_20260610_after_fallback.json`。
   - 回放链路为：Fatbeans JSON -> `parse_fatbeans_capture` -> pre-settlement prefix events -> `build_monitor_artifact_from_events(... formal_mode="v3_practical")` -> `summarize_snapshot` -> ref_v0/UI summary。
   - 结果：
     - 52/52 无构建失败；
     - readiness：`live_ready=22`、`count_prior=28`、`sparse_exact_prior=2`；
     - `candidate_missing=0`，`next_info_hint` 全部存在；
     - formal 请求均为 `v3_practical`；6 份样本因无可用 v3 formal rows 回退到 `v2`，不是启动默认被切走。

2. 修复
   - 修复候选/输入摘要的浮点展示噪声：
     - 真实 live snapshot 中 `总格 120.00000476837158` 现在显示为 `总格 120`；
     - 只改 UI 展示格式化，不改 ref_v0 引擎数值语义。
   - 修复 public 品质均价过硬导致 no-combo：
     - 真实样本 `fatbeans_valid_aisha_2402_3rounds_2402_1367586310602652_0052.json` 中 `public_q4_avg_value` 会把组合清空；
     - 现在保留正常均价推理；仅当 `public_q4/q5/q6_avg_value` 导致 `no_reachable_combo` 时，自动去掉该 public avg 重跑一次；
     - 成功 fallback 后 notes 记录 `public_quality_avg_value_conflict_fallback` 和 `public_q*_avg_value_downgraded`，方便后续按日志排查价格表 / 活动版本 / 外部表漂移。
   - 补充重复 exact 总数 / 总格诊断：
     - public 总件、Ahmad/action 总件、field_update 总件同值时不会叠加；
     - 若多源总件或总格不一致，保持现有覆盖顺序，但新增 `*_conflicts_total_count:*->*` / `*_conflicts_total_grid:*->*` notes，方便实机日志定位来源冲突。

3. source -> transform -> output 边界
   - public 品质均价正路：`ui_contract.constraints.public_info.public_avg_values/public_numeric_facts` -> `extract_evidence().avg_values` -> count/value 约束 -> ref_v0 ranges。
   - public 品质均价 fallback：原路 no-combo -> clone snapshot 去掉 public q4/q5/q6 avg facts -> rerun ref_v0 -> 返回可达结果并附加 downgrade notes。
   - public 随机均价仍为 soft floor：`public_random_avg_values` -> `random_value_floors` -> soft weight；真实 Aisha 负例中单独保留随机均价不导致 no-combo。

4. 验证
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> 38 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py tests\test_runtime_snapshot.py tests\test_ahmad_ref_engine_public_info.py -q` -> 162 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_monitor.py -q -k "avg_values or ahmad_ref or public_avg or random_avg"` -> 3 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py src\bidking_lab\runtime\snapshot.py`
     - `git diff --check -- external_references/ahmad_live_reference_lab/src/ahmad_ref_engine.py external_references/ahmad_live_reference_lab/tools/ahmad_live_panel_server.py external_references/ahmad_live_reference_lab/tools/ahmad_tk_overlay.py tests/test_live_overlay.py tests/test_ahmad_ref_engine_public_info.py` -> 仅 CRLF/LF 工作区提示，无空白错误
   - 未做：
     - 未重新打包；
     - 未做真实窗口视觉截图；
     - 728211 / 685641 / 477562 这类结算异常仍需新的实机错误样本继续按价格表 / 活动版本 / 外部表漂移优先排查。

### 7.17 全锁价值带宽与 UI 卡顿诊断（2026-06-10）

1. 用户实机反馈
   - 当白绿 / 蓝 / 紫 / 金 / 红的件数和格数都被限定时，旧 ref_v0 会把保守 / 参考 / 激进三档价格压成同一个数。
   - 这不等价于真实价值已完全确定：同一品质、同一件数/格数下仍可能有不同具体物品和价格。
   - 最新一轮 UI 有卡顿体感；怀疑 Tk 主线程在刷新时同步做 ref_v0 summary，和 live monitor 写入/接收叠加。

2. 已确认
   - 旧实现 `_combo_value` 是聚合估值：每个品质使用 nest 加权均价 + 格子修正。
   - 当品质 counts/cells 聚合 combo 只剩 1 个时，旧 `weighted_values` 只有一个中心点，因此 P25/P50/P75 必然相同。
   - 2404 实机导出中，结算前全锁样本旧显示：
     - `decision_range = 524,574 / 524,574 / 524,574`
     - `combo_count = 1`
   - 这属于 ref_v0 价值粒度不足，不是 UI 格式化错误。

3. 修复
   - ref_v0 保留现有 counts/cells 枚举，不改变锁件数逻辑。
   - 当某品质没有明确 `quality_values` 或 `avg_values` 时，为该品质加入同品质内价值带宽：
     - P50 保持当前聚合中心；
     - P25/P75 按品质和件数的保守 CV 展开；
     - 若品质总价或品质均价已知，则该品质不额外加带宽。
   - 新增 note：`intra_quality_value_band_v0`，用于标记“件数/格数已锁，但价值仍是同品质分布估计”。
   - 复算用户两局导出：
     - 2401 一轮局：`173,001 / 181,889 / 190,776`，raw `203,531 / 213,987 / 224,443`；
     - 2404 五轮局：`464,349 / 524,574 / 584,799`，raw `546,293 / 617,146 / 687,999`；
     - 两局中位数保持旧值，范围不再虚假塌缩。

4. UI 卡顿诊断
   - 确认 Tk overlay 的 `refresh()` 会在 Tk 主线程同步调用 `summarize_snapshot(...)`；summary 内会跑 ref_v0，理论上可造成 UI 卡顿。
   - 当前先做低风险诊断增强，未做 worker 线程化：
     - `summary.diagnostics.performance.summary_total_ms`
     - `summary.diagnostics.performance.ref_engine_ms`
     - `summary.diagnostics.performance.settlement_ref_engine_ms`
     - `summary.diagnostics.performance.refresh_total_ms`
     - 导出包 manifest 新增 `performance.export_ms`
   - performance 字段进入 `hero_ref_ui_summary.jsonl` / 导出包，但从 summary 去重签名中排除，避免同画面因耗时变化重复刷日志。

5. source -> transform -> output 边界
   - counts/cells：手填 / live / public 信息 -> `extract_evidence` -> count/grid combo -> UI 品质件数和总格，未改变。
   - value band：combo 中心值 -> `_combo_value_uncertainty` -> `_value_distribution_points` -> weighted P25/P50/P75 -> UI 三档报价。
   - exact value 负例：`quality_values` 或可用 `avg_values` 存在时，该品质不注入带宽；真实总价证据仍可形成单点。
   - performance：Tk refresh / summarize / ref_v0 / settlement pre-ref / export -> `diagnostics.performance` / `BUILD_EXPORT_MANIFEST.json`。

6. 验证
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> 40 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 105 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
   - 未做：
     - 未重新打包；
     - 未做 Tk 真实窗口视觉截图；
     - UI 卡顿尚未 worker 化；下次若导出包显示 `summary_total_ms` / `refresh_total_ms` 在低配机器上达到秒级，再优先做后台 summary worker。

### 7.18 结算态手填解锁与诊断档位拆分（2026-06-10）

1. 用户实机反馈
   - UI 停在结算界面时点击“手填”，详情区域会展开，但输入框无法填写。
   - 工程阶段新增了较多后台诊断字段；本机可以承受，但朋友低配机器不一定适合持续写完整诊断。

2. 已确认
   - 手填不可编辑原因是结算态 reset 规则过硬：
     - `open_manual_panel()` 刚启用手填；
     - 下一次 refresh 看到同一结算 summary 含 truth，就走 `_should_reset_manual_for_summary()` 并重置手填；
     - 结果是 UI 看起来展开了，但输入框马上被禁用。
   - 这属于结算态保护逻辑问题，不是 Tk Entry 控件本身损坏。

3. 修复
   - 新增同一局结算页手填解锁状态：
     - 同一 `session_id` 结算页进入手填后，不再被下一次 refresh 自动 reset；
     - 不同 `session_id` 或新局信息仍会重置，避免把上一局手填带到下一局。
   - 手填区新增“清结算”按钮：
     - 只在当前为结算态且进入手填时启用；
     - 清掉自动带入的结算数字，保留英雄 / 地图；
     - hover 明确说明“不删除 live 日志”。
   - 结算页手填应用时改为 standalone manual result：
     - 不再把手动输入叠加到 settled live snapshot 上；
     - 避免 truth/settlement 继续影响手填计算。

4. 诊断档位
   - `full/safe` 仍是包内容边界：
     - `full` 带本地 raw tables，适合私下直接运行；
     - `PublicSafe` 不带 raw tables，用户需自行导入本机表。
   - 新增运行时诊断档位 `--diagnostic-profile engineering|portable|public-safe`：
     - `engineering`：源码默认，继续写 `hero_ref_ui_summary.jsonl`，保留完整连续 UI summary；
     - `portable`：便携包默认，跳过连续 UI summary 追加，仍保留 live/latest/raw 和手动“导出诊断包”；
     - `public-safe`：公开安全档，跳过连续 UI summary，导出包也不包含 raw/jsonl。
   - 启动入口已接通：
     - `external_references/ahmad_live_reference_lab/start_ahmad_live.ps1 -DiagnosticProfile engineering|portable|public-safe`；
     - `external_references/ahmad_live_reference_lab/start_ahmad_overlay.ps1 -DiagnosticProfile engineering|portable|public-safe`；
     - `apps/hero_ref/Start-HeroRef.ps1 -DiagnosticProfile engineering|portable|public-safe`，默认 `portable`；
     - 打包 manifest 记录 `DefaultDiagnosticProfile: portable` 或 `public-safe`。
   - 导出包 manifest 新增：
     - `log_summary.diagnostic_profile`；
     - `log_summary.continuous_ui_summary`。

5. 后续拆分建议
   - 工程自测包：`full + engineering`，适合本机连续采样和分析。
   - 朋友稳定包：`full + portable`，直接运行，减少后台 UI summary 写盘。
   - 公开安全包：`PublicSafe + public-safe`，不带 raw tables，手动导出也不包含 raw/jsonl。
   - 若后续低配机器仍卡顿，优先检查导出包中的 `refresh_total_ms` / `summary_total_ms`，再决定是否把 summary/ref_v0 移到后台 worker。

6. 验证
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 109 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - PowerShell parse：
       - `external_references\ahmad_live_reference_lab\start_ahmad_live.ps1`
       - `external_references\ahmad_live_reference_lab\start_ahmad_overlay.ps1`
       - `apps\hero_ref\Start-HeroRef.ps1`
       - `external_references\ahmad_live_reference_lab\build_hero_ref_portable.ps1`
     - `C:\Python313\python.exe external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py --help` -> 已显示 `--diagnostic-profile {engineering,portable,public-safe}`
     - `git diff --check` -> 仅 CRLF/LF 工作区提示，无空白错误。
   - 未做：
     - 未重新打包；
     - 未启动真实 Tk 窗口做视觉检查；
     - 未关闭 monitor raw/latest 记录，因为它们仍是复盘和导出诊断包的核心证据。

### 7.19 诊断档位命名修正与 17:42 实机导出核对（2026-06-10）

1. 命名修正
   - 旧名 `stable` 过于笼统，容易和 full / safe 包边界混淆。
   - 正式运行时诊断档位改为：
     - `engineering`：工程自测，持续写 `hero_ref_ui_summary.jsonl`，导出包包含 UI summary + raw；
     - `portable`：私下给朋友跑，默认不持续写 UI summary，手动导出仍包含 raw，便于复盘；
     - `public-safe`：公开安全档，不持续写 UI summary，手动导出也不包含 raw/jsonl。
   - `stable` / `public_safe` 保留为兼容别名，内部会规范化为 `portable` / `public-safe`。
   - 便携包模板 `apps/hero_ref/Start-HeroRef.ps1` 默认 `portable`；
   - `build_hero_ref_portable.ps1 -PublicSafe` 会把拷贝出的启动脚本默认改成 `public-safe`，普通 full 包默认 `portable`。

2. 最新实机导出核对
   - 最新导出包：
     - `data\logs\live\exports\HeroRefDiag-20260610-174249-2401_1402770754854377.zip`
   - zip 内容正常：
     - `latest_snapshot.json`
     - `hero_ref_ui_summary.jsonl`
     - `capture_source_status.json`
     - `raw\windivert_live.jsonl`
     - `hero_ref_current_summary.json`
     - `BUILD_EXPORT_MANIFEST.json`
   - manifest 关键信息：
     - `session_id = 2401:1402770754854377`
     - `hero = ahmed`
     - `map_id = 2401`
     - `phase = settled`
     - `formal_mode = v3_practical`
     - `latest_snapshot.size_bytes = 193177`
     - `ui_summary.size_bytes = 665801`
     - `export_ms = 16.32`
   - 当前 summary 显示：
     - 结算总值 `388,248`
     - Hero Ref 结算页估价 / 结算 / 差值：`347,630 / 388,248 / +40,618`
     - 候选：`总件 48 · 总格 127`
     - public 数字信息：`金均价 27,325`
     - ref notes 含 `public_q5_avg_value` 与 `intra_quality_value_band_v0`
   - UI summary 尾部 performance：
     - 最大 `refresh_total_ms = 10.24`
     - 最大 `summary_total_ms = 7.34`
     - 最大 `ref_engine_ms = 4.42`
     - `settlement_ref_engine_ms = 4.25`
   - 因此这次导出数据是完整的；当前证据不支持“ref_v0 单次推理秒级卡死”，更像 Tk/UI 事件循环或关闭/重启联动路径的问题。

3. 针对 UI 卡住的新增诊断
   - 新增 `hero_ref_ui_health.jsonl`：
     - 主线程每次 refresh 更新 heartbeat；
     - 后台 watchdog 只在疑似 UI 事件循环超过 5 秒未响应时写 `ui_event_loop_stall_suspected`；
     - 若后续恢复，会写 `ui_event_loop_recovered` 和 gap 秒数。
   - `hero_ref_ui_health.jsonl` 会进入所有档位的手动导出包；
   - `public-safe` 仍不导出 raw/jsonl 和连续 UI summary。
   - 修复 monitor PID 退出分支：`root.destroy()` 后不再继续安排下一次 `root.after(...)`。

4. 验证
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 111 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
     - PowerShell parse：
       - `external_references\ahmad_live_reference_lab\start_ahmad_live.ps1`
       - `external_references\ahmad_live_reference_lab\start_ahmad_overlay.ps1`
       - `apps\hero_ref\Start-HeroRef.ps1`
       - `external_references\ahmad_live_reference_lab\build_hero_ref_portable.ps1`
     - `C:\Python313\python.exe external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py --help` -> 显示 `--diagnostic-profile {engineering,portable,public-safe}`
   - 未做：
     - 未重新打包；
     - 未启动真实 Tk 窗口做视觉检查；
     - 卡住根因仍需下一次实机复现后看 `hero_ref_ui_health.jsonl` 是否记录 stall。

5. 零均价约束
   - 引擎侧：`q4/q5/q6` 的 public `avg_value = 0` 仍按“该品质件数=0”处理，不会把总件/总格一起清零。
   - 手填侧：如果某个品质 `均格=0`，则该品质的 `件` / `格` 也必须为 `0`；否则会直接报更明确的冲突提示。
   - 已补测试覆盖这条零值冲突提示。

6. 手填派生刷新
   - 修正了 `总件/总格/全均格` 与各品质 `件/格/均格` 的自动派生刷新：依赖字段变化后，仍然保持“自动填入”的值会重新计算，不再挂着旧值。
   - 本地离线样本验证：`总件 32 / 总格 100 / 金均格 0` 在同步刷新后可正常生成 snapshot；引擎返回的是 `count_prior` 宽范围结果，不是全局不一致。

7. 手填与实时切换
   - `手填编辑中` 时，live 包继续进入后台缓存，但主视图不会动态刷新成新的参考/证据/价格，避免误导。
   - 点击 `实时` 会返回动态更新，同时保留用户已填内容；未被用户改过的缺失字段仍可继续自动补齐。
   - 已补回归测试覆盖“编辑中冻结视图”。
   - 后续修正：点击 `实时` 时会立刻用缓存的最新 live summary 做一次安全 auto-sync，不再等下一包才补齐缺失字段；用户 dirty 字段仍不覆盖。
   - 动态 probe 覆盖 3 个 Ahmed 真实快照与 1 个 Aisha artifact：手填中后台更新不刷新主视图，返回实时后渲染最新 round，并补齐缺失 `q6/q4` 字段；跨 session 时旧手填 dirty 状态会清理并回到新局实时。

8. 手填合同收紧：独立手算而非 live 叠加
   - 打开 `手填` 不再自动把当前 live 的英雄 / 地图 / 数值写入输入框；需要显式点击 `填入当前` 才做可见预填。
   - 应用手填时，若英雄或地图留空且当前有 live 上下文，会只作为计算 fallback 使用，并在 `ui_contract.source.manual_context_fallback` 记录 `hero/map_id -> live_context`，不会写回输入框。
   - `总件 + 总格` 已允许直接推理，返回宽约束 `count_prior`；不再硬拦截为“需补品质均格/件数/格数”。补紫/金/红均格时继续进入 `avg_cells` 缩小候选。
   - `应用并启用` 改为独立 manual result，不再把手填 snapshot 合并进旧 live snapshot；live monitor 仍后台缓存，点击 `实时` 才恢复自动结果。
   - 动态 probe 覆盖：
     - fresh auto-sync 不会把空手填框预填为当前英雄/地图；
     - 空英雄/地图 + live fallback + `总件 35 / 总格 105` 可得到 `count_prior` 和价格；
     - 再补 `紫均格 3.5` 仍可得到 `count_prior`，并收窄 q4 候选；
     - manual active 期间 live 新包只更新 `_last_live_summary`，不会 render 覆盖当前手填结果。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 119 passed
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> 40 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`

9. 公开红品约束与中文手填映射补测
   - 补充 public 红品随机公开下界测试：
     - `public_info_rows[].revealed_items_detail[].quality=6` -> `_public_quality_reveal_min_counts` -> `evidence.min_counts["q6"]`；
     - 重复 `runtime_id` 会去重；
     - `run_reference_engine` 枚举结果的 `quality_count_ranges["q6"][0] >= 2`，确认下界进入组合枚举，不只是解析层字段。
   - 补充 public 红品公共抽检 exact 测试：
     - `info_id=200003` -> `PUBLIC_BUCKET_OUTLINE_QUALITY["q6"]`；
     - `shape_code/shape_key` -> `_shape_cells` -> `fixed_counts["q6"]`、`quality_cells["q6"]`、`avg_cells["q6"]`；
     - bucket exact 不再重复走 `public_quality_reveal_min_counts`。
   - 补充手填中文英雄全覆盖：
     - `艾哈迈德 -> ahmed`、`维克托 -> victor`、`艾莎 -> aisha`；
     - 中文地图 `养生学家居所 -> map_id 2404`。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> 42 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 120 passed

10. 手填删除与点击选中体验
   - 发现 Backspace 之所以像“删不掉”，是因为清空后同一轮 `_sync_manual_derived_fields()` 会从剩余的均格/件数把该字段自动回填。
   - 修正后：如果用户已经手动清空某字段，它会保持空白，不再立刻被派生回填；只有未被用户动过的空白字段才允许自动补全。
   - 另外给手填输入框加了 `<FocusIn>` 自动全选：点击已有数字块后，能直接键入新数字覆盖，不用先手动删到最后一位。
   - 已补测试：
     - 用户清空 `q3_count` 后，`_sync_manual_derived_fields()` 不再把它从 `q3_avg/q3_cells` 自动补回；
     - 点击已有文本会触发整段选中，便于直接覆盖输入。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 123 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`

11. `清空手动` 不再自动回实时
   - 之前 `清空手动` 复用了 `_reset_manual_state()`，会顺带关闭手动编辑并把视图切回 live。
   - 现在 `清空手动` 只清空当前手填内容、清 dirty/autofill、保留手动编辑模式，不再自动 render live，也不把用户拉回实时监测。
   - 视觉上会把状态按钮和提示更新为“已清空，待填写”，但手动模式仍然保持开启，用户仍可继续填或手动点 `实时` 主动退出。
   - 已补测试：
     - `clear_manual_inputs()` 后 `_manual_edit_enabled` 仍为 `True`；
     - 不会触发 live render / standby / missing；
     - 输入框内容被清空，状态文案为 `已清空，待填写`。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 123 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`

12. `清结算` 交互与 Tk 主线程卡顿拆分
   - `清结算` 不再只是清空手填输入框：
     - 当前 summary 若仍是 settled/truth，会生成 `settlement_cleared` 手动占位 summary；
     - `truth.available = false`，估价/结算字段显示为待手填；
     - 保留英雄 / 地图，清掉结算 truth 对手填视图的影响；
     - 立即 render 新占位视图，并禁用 `清结算`，避免用户误以为按钮没响应。
   - live refresh 的重计算改成后台 worker：
     - Tk 主线程只读取 snapshot 签名、启动 worker、drain result queue、render；
     - `summarize_snapshot(...)` 和其中的 ref_v0 枚举不再直接阻塞 Tk refresh；
     - 修正 capture-status 只在 `latest_snapshot.json` 缺失时参与 refresh 变更判断，避免应用一次 worker 结果后立刻重复排第二个 worker。
   - 手填 `应用并启用` 也改成后台 worker：
     - `_manual_inputs_snapshot()` 仍在主线程做轻量解析/校验；
     - `_manual_result_summary()` 后台计算；
     - 用户编辑过输入后，旧 worker 结果会按 revision 丢弃，提示“输入已改动，请重新应用”。
   - 当前仍需实机验证：
     - 低配机器上是否还出现 Windows `Python is not responding`；
     - 大范围宽约束枚举是否只是 CPU 忙而非 UI 永久假死；
     - `hero_ref_ui_health.jsonl` 中是否还有 5 秒以上 stall。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 125 passed
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> 42 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`

13. 手填补齐品质均价 / 品质总价字段
   - 手填 UI 在原品质表右侧新增 `均价` / `总价` 两列：
     - `白绿/蓝/紫/金/红` 可填价值证据；
     - `白/绿` 单独拆分行继续只填 `均格/件/格`，避免和白绿合并价值重复。
   - 字段合同：
     - `q*_avg_value` -> `structured_ref_inputs.avg_values` -> ref_v0 `evidence.avg_values`；
     - `q*_value_sum` -> `structured_ref_inputs.quality_values` -> ref_v0 `evidence.quality_values`；
     - `件数 + 总价` 会在手填 UI 内派生均价；
     - `件数 + 均价` 会在手填 UI 内派生总价；
     - `均价 + 总价` 不在 UI 层强推件数，交给 ref_v0 通过 `quality_value_*_count_derived` 锁定。
     - 若 ref_v0 输出的 `quality_count_ranges.q*` 已收敛为 `[N,N,N]`，`填入当前` / 自动同步会把该品质 `件` 回填到手填框；覆盖金/紫等由均价约束唯一锁定的情况。
   - 校验：
     - 均价/总价负数拒绝；
     - 总价要求整数；
     - 已填件数时，均价与总价不一致会直接提示，例如 `金均价与金总价/金件不一致`。
   - live / public / action 映射复核：
     - public `public_avg_values` 与 `public_numeric_facts` 的 `q4/q5/q6_avg_value` 均进入同一 `avg_values` 路径；
     - action `100122-100126` 的品质总价进入 `quality_values`；
     - action 总价可与 public 均价联合推导品质件数；
     - 全场 `100121 total_value` 与 public `total_avg_value` 仍为 diagnostic-only，不进入品质约束。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 130 passed
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> 44 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_fatbeans.py::test_standard_quality_action_results_update_bucket_fields tests\test_live_monitor.py::test_ahmad_ref_inputs_bridge_keeps_quality_value_fields tests\test_runtime_snapshot.py::test_ui_contract_exposes_public_numeric_soft_facts -q` -> 5 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
   - 后续修正：
     - 价值字段已从下方独立表改为并入原品质表右侧，避免拉长整个手填 UI；
     - 补测 `quality_count_ranges` 唯一解回填 `件`。
   - 复跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 130 passed
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q tests\test_live_fatbeans.py::test_standard_quality_action_results_update_bucket_fields tests\test_live_monitor.py::test_ahmad_ref_inputs_bridge_keeps_quality_value_fields tests\test_runtime_snapshot.py::test_ui_contract_exposes_public_numeric_soft_facts -q` -> passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
   - 后续修正 2：
     - 白 / 绿行右侧也补齐 `均价` / `总价` 输入，视觉上不再留空；
     - 引擎没有独立 white/green value evidence，手填侧只在白、绿价值两边都能形成总价时聚合为 `q1`：
       - 白总价 + 绿总价 -> `quality_values.q1`；
       - 白/绿件数 + 均价可先派生各自总价，再聚合；
       - 若能确定白绿总件，则派生 `avg_values.q1`；
       - 只填白或只填绿会提示 `白/绿价值需同时填写`，避免把单边价格误当白绿总价。
     - `清空手动` 测试覆盖新增价值字段，确认清除后仍留在手填模式、不回跳实时。
   - 复跑 2：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 132 passed
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q tests\test_live_fatbeans.py::test_standard_quality_action_results_update_bucket_fields tests\test_live_monitor.py::test_ahmad_ref_inputs_bridge_keeps_quality_value_fields tests\test_runtime_snapshot.py::test_ui_contract_exposes_public_numeric_soft_facts -q` -> passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`
   - 未做：
     - 未重新打包；
     - 未启动真实 Tk 窗口做视觉检查，实际高度和滚动体验仍需实机看一眼。

14. 手填总计行自动格数刷新修复
   - 用户反馈：只填写 `总件 45` + `全均格 2.86` 时，UI 自动显示 `总格 90`。
   - 排查结论：
     - 平均格反推函数本身正确，`45 / 2.86` 的游戏显示规则唯一对应 `129` 格；
     - `90` 对应显示应为 `2`，不是 `2.86`；
     - 问题在 UI 派生字段同步：总计行只在 `总格` 为空时补一次，若 `总格` 是上一轮自动补出的旧值，后续修改 `全均格` 不会刷新它。
   - 修复：
     - 总计行现在与品质行一致：只要 `总件 + 全均格` 能唯一反推出格数，就尝试刷新自动补出的 `总格`；
     - 如果 `总格` 是用户手填值，则不自动覆盖，仍由 `应用并启用` 校验并提示 `全均格与总格/总件不一致`。
   - 已补测试：
     - `45 + 2.86` 会把旧自动 `总格 90` 刷新为 `129`；
     - 用户真实手填 `总格 90` + `全均格 2.86` 仍会被拒绝，不会静默修正。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 134 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`

15. 手填总格清空后重新派生修复
   - 用户反馈：
     - 先填 `总件` + `总格` 时会自动给 `全均格`；
     - 再清空 `总格`，清空 `全均格`，把 `总件 41` 改成 `40`，重新填 `全均格 2.5` 时，没有自动补出 `总格 100`。
   - 排查结论：
     - `总格` 被用户清空后会进入 dirty 状态；
     - 旧逻辑对“空但 dirty”的字段一律拒绝自动填充，这是为了避免刚清空字段后马上被 UI 弹回；
     - 但后续 `总件` / `全均格` 发生变化时，应允许重新派生 `总格`。
   - 修复：
     - `_sync_manual_derived_fields()` 接收触发字段；
     - 刚清空 `总格` 时仍不会立刻弹回；
     - 当触发字段是 `总件` 或 `全均格`，且 `总格` 为空、能唯一反推时，允许重新自动填写 `总格`。
   - 已补测试：
     - 清空 `总格` 后不会马上回填；
     - `总件 40` + `全均格 2.5` 会自动补出 `总格 100`。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 136 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`

16. Ahmad 2403 R5 红格低估样本
   - 样本：
     - `data\logs\live\exports\HeroRefDiag-20260610-215803-2403_1402770772799599.zip`
     - `ahmed / 2403 / R5 / session_id=2403:1402770772799599`
   - 结论：
     - 不是 async / low trials 导致。该局 live ref_v0 在 R4/R5 结算前稳定显示 `combo=1`；
     - 结算前没有外部 `总格` / `全均格` / `红均格` / `红扫描` 证据；
     - 已知非红格为 `白绿20 + 蓝40 + 紫20 + 金30 = 110`；
     - ref_v0 用默认红均格先验把 1 件红显示为 `2/3/4`，于是估总格为 `113`；
     - 结算 truth 为 `总格125 / 红件1 / 红格15 / 红值293400`，回放或手填补入总格/红均格后能正确得到红格 15。
   - 数值核对：
     - 结算后 ref_v0 红值区间 `158,781 / 288,693 / 418,604`，真实红值 `293,400` 接近中位，属正常；
     - 结算前红值区间 `125,143 / 210,425 / 280,310` 偏低，根因是红格候选只显示近默认 top3，没有覆盖 1 件红可达的高格尾部。
   - 已做低风险 UI 修正：
     - 当红件已锁、但缺 `总格/全均格/红均格/红扫描` 时，`下一步` 提示改为 `补总格/全均格或红均格`；
     - 不改正式报价和 ref_v0 枚举，避免把一次样本直接变成追价策略。
   - 待评估优化：
     - 红件数已锁但红格未知时，是否应把 q6 可达格尾部纳入显示分位或风险上沿；
     - 若要改报价，需要用更多结算样本验证覆盖率，避免因为单个 15 格红样本把常规红格过度抬高。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 137 passed
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q tests\test_live_fatbeans.py::test_standard_quality_action_results_update_bucket_fields tests\test_live_monitor.py::test_ahmad_ref_inputs_bridge_keeps_quality_value_fields tests\test_runtime_snapshot.py::test_ui_contract_exposes_public_numeric_soft_facts -q` -> passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py`

17. `藏价` 开局预设开关
   - 用户反馈：`藏价` 只有报价/结算出来后才能点，不符合“提前隐藏结算金额”的设计预期。
   - 修复：
     - `藏价` 从 UI 启动后即可点击；
     - 非结算态点击只切换 `settlement_values_hidden` 预设状态，不重渲染价格；
     - 结算态点击仍会立即 render 当前 summary，隐藏/显示金额；
     - hover 改为说明“结算出现后生效，只影响界面，不影响计算”。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 137 passed
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py`

18. 小版本发布审计与新命名打包
   - 发布判断：
     - 用户实测确认整体达到可发布小版本要求；
     - 本轮没有再观察到此前结算异常；
     - mini 信息层级、手填/实时、藏价预设、导出诊断包、手填均价/总价等当前视为闭环。
   - 红品下界复核：
     - `tests/test_ahmad_ref_engine_public_info.py` 已覆盖：
       - `public_quality_reveal_min_counts`；
       - `public_bucket_outline_q6_count`；
       - `public_bucket_outline_q6_cells`；
       - 结构化 `min_counts.q6`；
     - 额外 probe 使用真实 `public_info_rows` 形态复核：
       - 随机公开红品：`min_counts.q6=2`，结果红件下界不低于 2；
       - 红轮廓：`fixed_counts.q6=2`、`quality_cells.q6=7`，结果红件/红格锁定；
       - 结构化红下界：结果红件下界不低于 2。
   - 异步 worker 复核：
     - live refresh 通过后台 `hero-ref-summary` worker 计算 summary，主线程只 drain queue 后 render；
     - 手填通过 `hero-ref-manual` worker 计算，按 `revision` 丢弃旧输入结果；
     - live worker 按 `seq/signature` 防旧 snapshot 覆盖；
     - 未发现明显 Tk 跨线程 render；
     - 自动测试覆盖 background worker apply / refresh / manual edit freeze。
   - 打包脚本修正：
     - `build_hero_ref_portable.ps1` 新增 `-DiagnosticProfile engineering|portable|public-safe`；
     - `BUILD_MANIFEST.txt` 新增 `PackageProfile` 和 `DirtyWorktree`；
     - 普通包仍带 raw tables，`public-safe` 不带 raw tables。
   - 新包：
     - `dist\BidKingHeroRef-v0.1.2-20260610-47624a2-engineering.zip`
       - full + engineering，带 raw tables，独立运行，连续工程诊断；
     - `dist\BidKingHeroRef-v0.1.2-20260610-47624a2-portable.zip`
       - full + portable，带 raw tables，独立运行，推荐给朋友实测；
     - `dist\BidKingHeroRef-v0.1.2-20260610-47624a2-public-safe.zip`
       - public-safe，不带 raw tables，需要用户导入本机表，不属于完全离线独立包；
     - `dist\BidKingHeroRef-v0.1.2-20260610-47624a2-SHA256.txt`
   - clean unzip smoke：
     - 解压 `portable` 到 `dist\_smoke_BidKingHeroRef-v0.1.2-portable`；
     - 检查存在：
       - `BidKingHeroRef\BidKingHeroRef.exe`
       - `BidKingHeroMonitor\BidKingHeroMonitor.exe`
       - `data\raw\tables\BidMap.txt / Drop.txt / Item.txt`
       - `data\logs\live`
       - `BUILD_MANIFEST.txt`
     - `BUILD_MANIFEST.txt`：
       - `RequiresExternalPython: False`
       - `IncludesRawTables: True`
       - `PackageProfile: portable`
       - `DirtyWorktree: true`
     - `Start-HeroRef.ps1` 默认 `DiagnosticProfile = "portable"`；
     - `BidKingHeroRef.exe --help` exit 0；
     - `BidKingHeroMonitor.exe --help` exit 0。
   - SHA256：
     - `engineering.zip`: `BDA31B4E7D0F1957F52320ABECBAD5E9A5346549BB9410F9F233AD08729F992A`
     - `portable.zip`: `6908AEFD60D2DEEB92A44747A09050ECCB19D5E78EF5E0BF1889D4B69ECA7A5A`
     - `public-safe.zip`: `D0C75B1BFC6AE8213E9A20B66C142EF2F2F4F46572ADC1CE1F360BD55AD39A64`
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> 44 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 137 passed
     - `C:\Python313\python.exe -m pytest tests\test_runtime_snapshot.py -q` -> 19 passed
     - `C:\Python313\python.exe -m pytest tests\test_live_monitor.py tests\test_live_fatbeans.py -q` -> 118 passed, 25 skipped
     - `C:\Python313\python.exe -m py_compile ...` -> passed
   - 残余风险：
     - 包来自 dirty worktree，不是干净 tag；
     - 未在无 Python 的第二台机器真实启动 WinDivert live，只做了 clean unzip + exe help smoke；
     - `public-safe` 不带 raw tables，不满足完全离线独立；
     - 红件锁定但红格未知时只做了下一步提示修正，报价是否扩大红格尾部仍需更多样本评估。

19. 2026-06-11 小版本后续反馈与下一批低风险 UI 项
   - 朋友继续使用后反馈：
     - 偶尔仍会出现结算不完全或结算展示不完整的情况；
     - 该问题需要等用户提供新的 `data` 路径 / 对应导出包后按样本回查，优先仍按结算 payload、价格表 / 活动版本 / 外部表漂移、UI settlement truth 覆盖链路排查；
     - 暂不在没有样本的情况下把它归因成 missing settlement block。
   - 群友反馈的两个低风险 UI 改进：
     - UI 中红件、红格、紫 / 金件数、白绿蓝等候选值当前常按 `0/2/4` 这类从小到大显示；实战阅读更希望从大到小显示，例如高风险 / 高值可能性先看到；
     - Hero Ref 当前主要是悬浮窗，用户不能像普通窗口一样通过任务栏或 `Alt+Tab` / `Win+Tab` 切换，后续应提供可选的 taskbar 显示模式，默认仍保持悬浮 overlay 口径。
   - 实施边界：
     - 候选值降序只改变 UI 展示顺序，不改变 ref_v0 枚举、候选集合、价格计算、排序语义或主线 v3 truth；
     - taskbar 显示做成可选开关 / 启动参数，不强制改变默认悬浮窗体验；
     - 这轮优先做 UI 层低风险改动，不推进主线 v3 promotion，不恢复 formal/value sampler 正式接入。
