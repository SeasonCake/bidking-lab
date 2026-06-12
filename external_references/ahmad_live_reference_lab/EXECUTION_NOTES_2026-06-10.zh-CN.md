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

20. 2026-06-11 低风险 UI 项回退与保留
   - 候选值显示顺序：
     - 朋友实测后认为高值优先显示与主界面低到高的报价口径存在视觉冲突；
     - 已回退到原本低到高展示，继续保持 `ref_result.red_count_range`、`red_cells_range`、`quality_count_ranges.q4/q5`、白绿 / 蓝未锁摘要、估总件 / 估总格的原始顺序；
     - 底层 `ref_result` 数组、`_range_mid()`、件数锁定、下界约束和估值计算都不变；
     - 金额类主报价仍保持 `保守 / 参考 / 激进` 的原语义。
   - taskbar 可选模式：
     - `tools/ahmad_tk_overlay.py` 新增 `--show-taskbar`；
     - `start_ahmad_overlay.ps1`、`start_ahmad_live.ps1`、portable `Start-HeroRef.ps1` 新增 `-ShowTaskbar` 并透传 UAC 重启；
     - 默认仍是无边框悬浮 overlay，启用后使用普通 Tk 窗口进入任务栏并支持 `Alt+Tab` / `Win+Tab`。
   - 验证：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> 138 passed；
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py` -> passed；
     - PowerShell parser 检查 `start_ahmad_overlay.ps1`、`start_ahmad_live.ps1`、`apps\hero_ref\Start-HeroRef.ps1` -> passed。

21. 2026-06-11 portable 包启动入口说明修正
   - 用户反馈旧文件名 `右键管理员运行_启动HeroRef.bat` 容易被当成“说明”或导致朋友点错入口。
   - 包模板新增两类明确入口：
     - `管理员启动HeroRef_悬浮窗.bat` / `Start-HeroRef.bat`：默认无任务栏悬浮 overlay，双击会自动申请管理员权限；
     - `管理员启动HeroRef_任务栏窗口.bat` / `Start-HeroRef-Taskbar.bat`：普通窗口 taskbar 模式，支持 `Alt+Tab` / `Win+Tab`，双击会自动申请管理员权限。
   - 新模板不再包含 `右键管理员运行_启动HeroRef.bat`；README / `使用说明.txt` / `VPN或UU备用启动.txt` / `PACKAGE_MANIFEST.zh-CN.md` 已改为只推荐两条管理员启动入口。
   - `build_hero_ref_portable.ps1` 的 `BUILD_MANIFEST.txt` 和构建完成提示改为同时列出 floating 与 taskbar 两种启动方式。
   - 本轮只更新模板和说明，未重新打包；历史 `dist\...` 目录里的旧包仍保留旧说明，下一次打包才会更新。

22. 2026-06-11 结算异常样本索引补记
   - 用户提醒：项目目录和朋友 recordings 目录中已经有大量 WinDivert raw 样本，不应只看手动导出的 zip。
   - 已新增集中索引：
     - `docs\hero_ref_settlement_sample_index_2026-06-11.zh-CN.md`
   - 粗筛范围：
     - `data\logs\live\raw\archive\reset`：8 个 WinDivert reset，8 个含 settlement frame；
     - `data\logs\live_2026.06.10_ahmed\live\raw\archive\reset`：35 个 WinDivert reset，21 个含 settlement frame；
     - `C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset`：26 个 WinDivert reset，25 个含 settlement frame；
     - `C:\Users\shenc\Desktop\recordings\data\logs\live\exports`：1 个手动导出 zip。
   - 重点样本：
     - 4406：`data\logs\live_2026.06.10_ahmed\live\raw\archive\reset\windivert_live_2026-06-10_060929_4406_1402770724242732_reset.json`
       - settlement truth：24 件 / 62 格；
       - 历史问题：pre-settlement bridge total 39 污染 settled 结果；
       - 当前处理方向：settlement truth 覆盖 stale live/action 输入。
     - 朋友导出：`C:\Users\shenc\Desktop\recordings\data\logs\live\exports\HeroRefDiag-20260611-021539-4521_1402770788450965.zip`
       - session：`4521:1402770788450965`；
       - 补丁后复放：`status=ok`、`combo_count=1`、14 件 / 43 格。
     - 朋友 raw 活动图：`C:\Users\shenc\Desktop\recordings\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_013131_4521_1402770786856860_reset.json`、`...\windivert_live_2026-06-11_020526_4521_1402770788280922_reset.json` 等 4521/4524/4527/4530 样本。
   - 后续回查优先级：
     - 先用索引里的 raw / zip 复放；
     - 再按价格表 / 活动版本 / 外部表漂移 -> settlement truth 覆盖 -> UI 展示链路检查；
     - 不再把“另一个异常局没有快照”作为默认判断，因为 raw archive 里已有可筛选样本。
   - 当前批量复放结果：
     - 对 54 个含 settlement frame 的 raw WinDivert 样本执行 `build_monitor_artifact_from_file(...)` -> `run_reference_engine(..., max_combos=60000)`；
     - 结果为 `ok=54`、`problem_count=0`、`hard_conflict=0`；
     - 4406 四个 settlement raw 样本均 `status=ok`、`combo_count=1`；
     - 朋友 recordings 里两个 4521 raw 样本均 `status=ok`、`combo_count=1`；
     - 这说明当前补丁已覆盖 raw artifact 到 ref_v0 的 settlement truth 链路。剩余风险转向 UI 时序显示、打包版本是否包含补丁、以及价格表 / 活动版本 / 外部表漂移。

23. 2026-06-11 settlement summary 与 dirty 包 smoke
   - UI summary 层批量复放：
     - 对同一批 54 个含 settlement frame 的 raw WinDivert artifact 执行 `summarize_snapshot(...)`；
     - 结果为 `status=ok=54`、`reference.source=settlement=54`、`ahmed_ref.status=ok=54`、`problem_count=0`；
     - 4406 四个样本、朋友 recordings 两个 4521 raw 样本均在 summary 层对齐 settlement truth。
   - 新增回归测试：
     - `tests\test_live_overlay.py::test_ahmad_server_summary_settlement_truth_overrides_stale_live_actions`
     - 目标：结算态 summary 不被 stale live action / structured bridge 覆盖。
   - dirty worktree smoke 包：
     - `dist\BidKingHeroRef-v0.1.3-20260611-dirty-portable.zip`
       - SHA256：`CF8B98552025A2721BE4F3311D67A4630FAE05F1A37B09C6060A95E668C85D5A`
       - full/portable，带 raw tables，`PublicSafe=False`，`IncludesRawTables=True`，`RequiresExternalPython=False`，`PackageProfile=portable`，`DirtyWorktree=true`。
     - `dist\BidKingHeroRef-v0.1.3-20260611-dirty-public-safe.zip`
       - SHA256：`530CD1C043F783C78FA2A640EDA518F66B5E2A5B4FBA44DCB63800B8DEBEA8FA`
       - public-safe，不带 raw tables，包含 `PUT_TABLES_HERE.txt`，`PublicSafe=True`，`IncludesRawTables=False`，`RequiresExternalPython=False`，`PackageProfile=public-safe`，`DirtyWorktree=true`。
   - clean unzip smoke：
     - 两个包均包含 UI exe、monitor exe、四个明确启动入口、`Start-HeroRef.ps1`、`data\logs\live`；
     - 旧入口 `右键管理员运行_启动HeroRef.bat` 数量为 0；
     - UI exe `--help` exit 0；monitor exe `--help` exit 0；
     - public-safe 解压后未发现 `BidMap.txt` / `Drop.txt` / `Item.txt`。
   - 已跑：
     - `C:\Python313\python.exe -m pytest -p no:cacheprovider tests\test_live_overlay.py tests\test_ahmad_ref_engine_public_info.py tests\test_runtime_snapshot.py tests\test_live_monitor.py tests\test_live_fatbeans.py -q` -> `329 passed, 25 skipped`
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py`
   - 残余风险：
     - 这两个包来自 dirty worktree，不是 clean tag release；
     - 没有在第二台无 Python 机器实机启动 WinDivert 抓包，只做 clean unzip + exe help smoke；
     - 金额差价若仍出现，下一步优先查价格表 / 活动版本 / 外部表漂移，而不是 missing settlement block。

24. 2026-06-11 金均格 0 / `0/1/1` 时序补丁
   - 新反馈：朋友遇到游戏内金均格为 `0` 时，计算器金件仍显示类似 `0 / 1 / 1`，疑似“没检测完”。
   - 样本粗查：
     - 新导出包：`C:\Users\shenc\Downloads\HeroRefDiag-20260611-133716-4405_1425860427403590.zip`；
     - 已解压到：`.tmp\diag_4405_1425860427403590`；
     - 该包当前 `latest_snapshot.json` / `hero_ref_current_summary.json` 的 4405 settled 结果是干净的：q5/q6 结算为 exact 0/1 对应真实结算，没有复现“0 均格仍不归零”；
     - `hero_ref_ui_summary.jsonl` 中历史 4401 / 4405 bidding 帧曾出现 `金件 0 / 1 / 1`，但对应证据没有抓到 `100113` 金均格 0 或 inferred_zero，只能判定为“金均格未进 evidence 时的先验残留”，不是已确认的 0 观测已进入但漏消费。
   - 确认的源 -> transform -> output 链路：
     - source：`events.sends` 中 `100110-100114` 均格动作，尤其 `100113` 金均格动作，和同 session 后续 `states`；
     - transform：`src\bidking_lab\live\monitor.py::_action_result_rows(...)` 生成 `actions.results`，若动作已发出、同 session 后续 state 出现且无结果块，补 `result=0` + `inferred_zero=True`；
     - output：`runtime.snapshot._ui_actions_contract(...)` 将 action rows 写入 `ui_contract.actions.results`，`ahmad_ref_engine.ACTION_AVG_CELLS` 消费 `100113 -> q5 avg_cells=0`，再由 `zero_avg_cells_q5_count_zero` 固定金件和金格为 `0/0/0`。
   - 本次补丁：
     - `src\bidking_lab\live\monitor.py::_action_result_rows(...)` 新增 `session_id` 参数，artifact 构建时传 `_latest_session_id(events)`，避免旧局同 action 结果挡住当前局 zero fallback；
     - zero fallback 不再被“同 action 空结果占位且无揭示物”的 row 挡住；
     - 若已有数值结果或已有揭示物，仍不覆盖为 0；
     - 若没有后续 state、没有抓到对应 action send，仍不会静默猜 0。
   - 新增回归测试：
     - `tests\test_live_monitor.py::test_action_result_rows_infer_zero_for_latest_session_after_old_result`
     - `tests\test_live_monitor.py::test_action_result_rows_infer_zero_over_empty_result_placeholder`
   - 已跑：
     - `python -m pytest tests/test_live_monitor.py tests/test_ahmad_ref_engine_public_info.py::test_ref_engine_victor_inferred_zero_action_constrains_gold_avg` -> `49 passed`
     - `git diff --check` -> 无 whitespace error，仅现有 CRLF 提示。

25. 2026-06-11 0611 官方更新与 minimap taskbar 闪烁修复
   - 官方更新内容已抄录到项目笔记，后续跟进重点是：
     - 世界杯主题活动、活动藏品掉落、红色藏品“土豆服务器”；
     - 藏品订单功能和任务界面提交非绑定藏品换银币；
     - 兑换商店新增礼盒 2 期；
     - 竞拍中藏品百科提示修复、成就计数修复、十二生肖藏品系统回收清除。
   - 当前 Hero Ref 代码侧先跟进的是桌面体验问题：
     - 浮窗模式下 `root` 与 minimap popup 补了 Windows `-toolwindow` 样式；
     - hover/click 打开 minimap popup 时先 `withdraw()`，再配置样式，最后 `deiconify()`；
     - 目标是降低全屏游戏下鼠标滑到小地图时 taskbar 突然闪出的概率。
   - 验证：
     - `python -m pytest tests/test_live_overlay.py` -> `140 passed`
     - `python -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py` -> passed
   - 0611 表快照对照：
     - `C:\Users\shenc\Downloads\data\raw\tables` 与仓库 `data\raw\tables` 逐文件 hash 一致；
     - `fileVersion=303`，当前本机可见的 raw/processed 表快照还没有额外的 `Activity/Item/Drop` 差异可直接吸收；
     - 也就是说，现阶段先把官方 0611 活动公告和 release 边界记清，后续如果拿到新的 `StreamingAssets` 再重新跑 `copy_game_tables.ps1` / `build_processed_data.py` 补齐差异。

26. 2026-06-11 mini 导出入口、包名规则与“等待对局包”诊断
   - 用户新增边界：
     - 不再自行打包；只有用户明确要求打包时才执行 build/zip；
     - 后续包名只保留版本号和包类型，不再默认拼日期、commit 或 dirty 标记。
   - UI 调整：
     - `导出` 从展开后的小地图 header 移到 mini 常驻控制行，迷你模式下也能直接点；
     - `地图` 按钮保留 hover 右侧预览和点击固定/取消固定，只移除多余的按钮提示文案；
     - 小地图画布本身、结算/物品 tooltip、固定小地图里的 hover 逻辑未改。
   - 包名规则：
     - `build_hero_ref_portable.ps1` 新增 `-Version`，默认 `0.1.4`；
     - 默认 full 输出：`dist\BidKingHeroRef-v0.1.4-full`；
     - 默认 public-safe 输出：`dist\BidKingHeroRef-v0.1.4-public-safe`；
     - `-Version` / `-OutputDir` 若包含日期块或 dirty 标记会直接拒绝；
     - 本次没有重新生成任何包。
   - 0611 新内容状态：
     - `C:\Users\shenc\Downloads\data\raw\tables` 与仓库 raw tables hash 一致，`fileVersion=303`；
     - 当前本机表里还没有“土豆服务器”或世界杯活动掉落的新增 `Item/Drop` 差异可直接进入推理；
     - 只能确认公告已记录，不能把新增掉落物当作本地推理表已吸收。拿到新 `StreamingAssets` 后再跑表同步和 processed rebuild。
   - “打开后一直等待对局包”排查：
     - 朋友 `C:\Users\shenc\Desktop\recordings\data\logs\live\capture_source_status.json` 里可见 `active_flows=3`、`raw_packets=9`、`accepted_frames=0`、`ignored_reasons.rev_not_game_frame=9`；
     - 结论：不是单纯 UI-only，也不是 monitor 完全没启动；monitor 已看到 BidKing.exe 流量，但当前包都没有被解析成游戏状态帧；
     - 可能方向：启动时机/抓包模式不匹配、只抓到反向非状态包、VPN/UU/路由导致默认 port-only 模式太窄，或当前还没触发可解析的竞拍状态帧；
     - 优先建议：用管理员入口 `-Restart` 重启整条链；若仍然如此，用备用启动 `-BroadSniff -IncludeLoopback`，进新局或使用道具后再点 mini 常驻 `导出` 回传。
   - 验证：
     - `C:\Python313\python.exe -m pytest tests/test_live_overlay.py -q` -> `141 passed`
     - `C:\Python313\python.exe -m pytest tests/test_live_monitor.py tests/test_ahmad_ref_engine_public_info.py -q` -> `101 passed`
     - `C:\Python313\python.exe -m pytest tests/test_live_overlay.py tests/test_live_monitor.py tests/test_ahmad_ref_engine_public_info.py -q` -> `242 passed`
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py` -> passed
     - PowerShell parser 检查 `build_hero_ref_portable.ps1` -> passed
     - Tk 实例化 introspection：mini `440x397`；`导出` parent 为常驻 header 控件区且 viewable；`details_card/minimap_card` 在 mini 下隐藏；`地图` `<Enter>/<Leave>` 预览绑定与 `<Button-1>` 固定绑定均存在；hover 右侧 popup 可显示并可隐藏；额外 `map_tip` 不存在。

27. 2026-06-11 v308 原始游戏表同步与发布前 UI 文案回收
   - 用户纠偏：
     - 不只看 `C:\Users\shenc\Downloads\data\raw\tables`，必须到游戏原始 `StreamingAssets` 解码核对；
     - `导出` hover 要明确告诉群友：异常/卡住/结算不对时点击，会生成诊断 zip，把 zip 发群里作为 log 排查；
     - 中文 BAT 本体也要能提示“右键以管理员身份运行”；
     - “下一步”推荐不要让 mini 文案看起来只是在提示红均格。
   - 原始表核对：
     - 游戏原始目录：`C:\xiangmuyunxing\steamapps\common\BidKing\BidKing_Data\StreamingAssets`；
     - 原始 `fileVersion=308`，项目/Downloads 旧快照此前仍是 `303`；
     - 已用项目 Base64/TSV 解码器核对，原始 `Item.txt` 包含 0611 新增/活动物品：
       - `1016007` 决赛指定用球，q6，4 格，758000；
       - `1036006` 世界冠军奖杯，q6，6 格，7202026；
       - `1036007` “退钱”手举牌，q6，12 格，555555；
       - `1036008` 传奇球星签名球衣，q6，6 格，1225000；
       - `1076007` 土豆服务器，q6，6 格，990000。
     - `scripts\copy_game_tables.ps1` 已同步当前工作区 raw tables；`data\raw\fileVersion` 现在是 `308`；
     - `scripts\build_processed_data.py` 已重建：
       - `items.json`: 1207 items；
       - `items_droppable.json`: 587 items（map-reachable physical loot）；
       - `maps.json`: 165 maps；
       - 生成时显式 warning：地图掉落引用缺失 Item row `1106013`；活动地图引用缺失 Drop pools `2521-2530`。
   - 活动掉落边界：
     - `Drop.txt` 与旧快照 hash 一致，仍没有 `2521-2530` / `4521-4530` 的活动 Drop pool；
     - `summarize_v3_archive_table_timing.py --format summary` 仍显示：
       - `activity_range=2521-2530 bidmap_present=10 drop_present=0 drop_missing=10`
       - `activity_range=4521-4530 bidmap_present=10 drop_present=0 drop_missing=10`
     - 因此 0611 新物品已进入 item price/cells lookup，能用于结算/显式 item_id 价格表语义；但世界杯活动额外掉落权重/overlay 仍不能当作正式 prior，继续保持 shadow-only / audit-only。
     - `items_droppable.json` 口径已从“任何 Drop 池引用过”收敛为“从 BidMap 可达且 quality/value/占格有效的物理藏品”，防止非地图可达或 q0/0格/0价值编码污染推理。
     - 全量 `Drop.txt` 审计里仍能看到 `120006` 青龙、`120007` 白虎、`120008` 朱雀、`120009` 玄武：均来自 `Drop` pool `1001`、category `12`、weight `10000`、q0/cells0/value0、map_reachable=false；当前不进入 `items_droppable`，也不进入 MC 概率分布。
     - `1012005` 足球在当前 `Drop.txt` 中有权重引用（如 `1012` weight 134、`1202` weight 135），并且 map_reachable=true；已保留在当前 `items_droppable` 中。
     - `1016007` / `1036006` / `1036007` / `1036008` / `1076007` 当前 `drop_pool_count=0`，即本地 `Drop.txt` 没有它们的概率权重；若游戏实际掉落这些物品，概率/source 需要来自活动 overlay、服务端规则或后续新表。
     - 原始 `Language.txt` 的 `activity_des_10007` 只说明活动期间不同地图可掉落“退钱”牌、决赛指定用球，以及高阶场景可掉落 4 件限时藏品；没有数值权重。该活动描述未直接提到 `1076007` 土豆服务器，因此土豆服务器目前只能算新红 Item/价格表条目，不能算已确认活动 Drop prior。
   - 代码修复：
     - `src\bidking_lab\extract\bid_map_table.py`：空 `col[7]` 的 shipwreck-family fallback 扩到 `2501-2530 -> 105`、`4501-4530 -> 305`，避免 v308 `2521/4521` 读表失败导致 monitor 看起来只剩 UI；
     - `src\bidking_lab\simulation\basic_mc.py`：`flatten_pool` 只把 quality>0、value>0、占格>0 的物理藏品纳入概率分布；
     - `scripts\build_processed_data.py`：`items_droppable.json` 从地图入口递归 Drop 树生成，非地图可达/非物理藏品只保留在 `items.json`，不参与推理 prior；
     - `scripts\copy_game_tables.ps1`：同步列表补入 `Tables\Language.txt`，后续可直接在 `data\raw\tables\Language.txt` 复查活动描述；
     - `tools\ahmad_tk_overlay.py`：`导出` hover 改为异常场景说明，明确生成诊断 zip 并发群里排查；
     - `apps\hero_ref\管理员启动HeroRef_悬浮窗.bat` / `管理员启动HeroRef_任务栏窗口.bat`：启动前输出管理员权限提示，说明无 UAC 或一直等待对局包时右键以管理员身份运行；
     - `tools\ahmad_live_panel_server.py`：红件锁定但红格未知时，`下一步` mini 文案从 `补总格/全均格或红均格` 收敛为 `优先补总格/全均格`，保留原判断条件，不改变引擎约束。
   - 本次没有打包。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_bid_map_table.py tests\test_live_overlay.py::test_ahmad_export_diagnostic_tip_tells_users_to_send_zip_for_abnormal_cases tests\test_live_overlay.py::test_ahmad_server_next_info_hint_targets_q6_grid_when_red_count_locked -q` -> `16 passed`
     - `C:\Python313\python.exe -m pytest tests\test_bid_map_table.py tests\test_live_overlay.py tests\test_live_monitor.py tests\test_ahmad_ref_engine_public_info.py -q` -> `257 passed`
     - `C:\Python313\python.exe -m py_compile src\bidking_lab\extract\bid_map_table.py src\bidking_lab\live\monitor.py external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py` -> passed
     - `git diff --check` -> 无 whitespace error，仅 CRLF 提示
     - Tk introspection：mini `440x397`；`导出` 在常驻 header 控件区且 viewable；tooltip 包含 `生成诊断 zip` / `发群里` / `log 排查`；`details_card/minimap_card` 在 mini 下隐藏；`地图` `<Enter>/<Leave>/<Button-1>` 绑定仍存在；`map_tip` 不存在。

28. 2026-06-11 活动掉落权重二次逆向与 shadow-only 拟合
   - 用户要求：正式 `Drop.txt` 找不到 0611 新物品概率时，继续从游戏源文件查找；若仍无正式来源，尝试用同品质/占格/价值区间做可用拟合。
   - 源文件逆向结果：
     - `dll\Scripts.dll.bytes` / `dll\Scripts.pdb.bytes` / `dll\NotHotUpdate.dll.bytes` 使用 4 字节 XOR key `ryrs` 可还原为 .NET assembly/metadata；
     - 解码后的 `Scripts.decoded.dll` 中 `GameServerDemo.Utils.DoDrop` IL 证实正式 drop 流程是：
       - `Table_Drop.getBygroup_id(group_id)`；
       - 读取 `Table_Drop.weight_type` 与 `Table_Drop.items_list`；
       - `items_list[*][0] == 9999` 时递归 `DoDrop(next_group_id, count)`；
       - 否则 `AddItem(item_id, RandomCount(n_min, n_max))`；
     - `Table_Drop` 元数据字段为 `group_id / weight_type / items_list`，没有发现活动 overlay 权重字段；
     - 全量解码表精确检索：`1016007` / `1036006` / `1036007` / `1036008` / `1076007` 只在 `Item.txt` 作为 item row 出现，`Language.txt` 只提供名称/描述/活动文案，`Activity.txt` 只指向 `activity_des_10007`；
     - `Item.txt` 的 `number_weight`/raw col[29] 不是 `Drop` 概率；已用已有 q6 物品负例对照：同列数值与正式 `Drop.txt` 权重不一致，不能直接当爆率。
   - 结论：
     - 仍未找到正式数值概率/权重来源；世界杯活动额外掉落继续不能进入 formal prior；
     - `土豆服务器` 未出现在 `activity_des_10007` 的四件限时藏品描述中，只保留为新红 item/结算 lookup，不作为活动掉落边。
   - 新增 shadow-only 拟合产物：
     - 脚本：`scripts\build_activity_shadow_prior.py`；
     - 输出：`data\processed\activity_drop_shadow_prior.json`；
     - 注意：`data/processed/**` 当前在 `.gitignore` 中，新增 shadow JSON 是本地生成物；若后续要纳入 git，需要显式 `git add -f`；
     - 明确标记：`status=shadow_only_not_formal_prior`、`do_not_merge_into_items_droppable=true`；
     - 拟合方法：在当前 map-reachable q6 正式掉落物上拟合 `log(value) -> log(weight)`，再与同品质、同类/标签、相近占格/价值的邻居 median weight 做几何融合；
     - 活动边界来自 `activity_des_10007`：
       - 废弃仓库：`1036007` “退钱”手举牌；
       - 航运集装箱：`1036007` + `1016007` 决赛指定用球；
       - 高阶活动场景：`1036007` / `1016007` / `1036006` 世界冠军奖杯 / `1036008` 传奇球星签名球衣；
       - `1076007` 土豆服务器：不在活动文案中，`activity_text_eligible=false`。
     - 当前估计 leaf weight（仅 audit/replay 参考）：
       - `1016007` 决赛指定用球：约 `2721`，`confidence=medium_low`；
       - `1036006` 世界冠军奖杯：约 `175`，`confidence=low_value_extrapolation`；
       - `1036007` “退钱”手举牌：约 `2640`，`confidence=very_low`；
       - `1036008` 传奇球星签名球衣：约 `1426`，`confidence=low`；
       - `1076007` 土豆服务器：约 `2423`，`confidence=medium_low`，但无活动掉落文案边。
     - 新增 `impact_guard`：
       - `formal_use_allowed=false`、`drop_rate_validation_allowed=false`；
       - 废弃仓库 shadow 新物品加权均值约 `555555`；
       - 航运集装箱 shadow 新物品加权均值约 `658307`；
       - 高阶活动场景 shadow 新物品加权均值约 `938866`，最高价值的 `1036006` 世界冠军奖杯权重占比约 `2.51%`，没有被拟合成离谱高权重；
       - 由于低置信项仍存在，recommendation 统一保持 `keep_read_only_until_official_or_sample_confirmed`。
   - 本轮没有把 shadow prior 接入 Hero Ref 正式推荐或 `items_droppable.json`。
   - 已跑：
     - `C:\Python313\python.exe scripts\build_activity_shadow_prior.py` -> wrote `data\processed\activity_drop_shadow_prior.json`；
     - `C:\Python313\python.exe -m pytest tests\test_activity_shadow_prior.py tests\test_build_processed_data.py tests\test_basic_mc.py -q` -> `10 passed`；
     - `C:\Python313\python.exe -m py_compile scripts\build_activity_shadow_prior.py tests\test_activity_shadow_prior.py` -> passed。

29. 2026-06-11 shadow prior 边界测试与 UI 不刷新自动状态记录
   - 用户担心：拟合 leaf weight 可能在过渡期把某些地图报价抬偏；少数群友反馈 UI 不刷新，不能完全依赖用户手动点导出。
   - shadow prior 边界：
     - `tests\test_activity_shadow_prior.py` 新增正式 prior 边界测试；
     - 直接读取 `data\processed\items_droppable.json`，并逐地图调用 `basic_mc.flatten_pool()`，确认 `1016007` / `1036006` / `1036007` / `1036008` / `1076007` 均不在正式 map prior；
     - 同时保留正例 `1012005` 足球仍在正式 prior，避免测试只验证空路径；
     - 结论：当前 fitted shadow prior 只读，不会影响 live 推荐、报价或正式爆率验证。
   - UI 自动状态记录：
     - `tools\ahmad_tk_overlay.py` 新增 `hero_ref_ui_runtime_status.json`；
     - 文件写入位置为 `data\logs\live\`，采用覆盖写，记录最近一次 UI 刷新状态，不会像 jsonl 一样持续增大；
     - 记录字段包括：`event`、snapshot 是否存在/mtime signature/age、last applied signature、summary/manual worker 状态、manual active/edit 状态、最近 summary 的 hero/map/round/phase/session/source，以及 compact capture 状态；
     - capture compact 状态包含 `active_flows`、`raw_packets`、`accepted_frames`、`ignored_frames`、`active_session_id`、`top_ignored_reason`、`wait_state`、`wait_action`、`wait_note`；
     - `waiting_for_snapshot` 可区分 `no_capture_status` / `no_active_flow` / `no_raw_packets` / `raw_no_game_frame` / `session_waiting_snapshot`，用于判断是权限/设备/抓包模式问题，还是 UI 自身卡住；
     - 诊断导出包现在会包含 `hero_ref_ui_runtime_status.json`（若存在），manifest 的 `log_summary.ui_runtime_status` 会列出该文件摘要。
     - `monitor.stdout.log` / `monitor.stderr.log` 也会进入诊断包；如果截图停在 `no_capture_status`，优先看 stderr 是否有 pydivert 缺失、权限被拒、驱动加载失败或进程秒退。
     - 即使没有 `latest_snapshot.json`，mini 常驻 `导出` 现在也会生成 `no_snapshot` 诊断 zip，避免最需要排查 monitor 时反而导不出包。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> `144 passed`；
     - `C:\Python313\python.exe -m pytest tests\test_activity_shadow_prior.py tests\test_live_overlay.py -q` -> `145 passed`；
     - `C:\Python313\python.exe scripts\build_activity_shadow_prior.py` -> wrote `data\processed\activity_drop_shadow_prior.json`；
     - `C:\Python313\python.exe -m pytest tests\test_activity_shadow_prior.py tests\test_build_processed_data.py tests\test_basic_mc.py tests\test_bid_map_table.py tests\test_live_monitor.py tests\test_live_status.py tests\test_ahmad_ref_engine_public_info.py tests\test_live_overlay.py -q` -> `280 passed`；
     - `C:\Python313\python.exe -m py_compile scripts\build_activity_shadow_prior.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_activity_shadow_prior.py tests\test_live_overlay.py` -> passed；
     - `git diff --check` -> 无 whitespace error，仅 CRLF 提示。

30. 2026-06-11 v0.1.4 release package
   - 用户明确要求：做最后 UI/hover/数据/推理/打包检查，确认后打包。
   - 打包前新增一个小 UI 修复：
     - 打开手填面板时，如果当前没有任何手填输入/dirty/autofill 状态，会自动填入当前 live context 中的英雄、地图、已知总件等；
     - 若用户已有手填内容，则不覆盖；
     - 覆盖测试：`test_ahmad_open_manual_panel_prefills_empty_live_context`、`test_ahmad_open_manual_panel_does_not_overwrite_existing_inputs`。
   - UI 实窗 smoke：
     - 截图路径：`.tmp\release_ui_smoke\mini_final.png`、`details_final.png`、`manual_final.png`；
     - mini geometry `440x397`；
     - 样例渲染确认：`aisha · 2521 · R4`、三档价 `1,980,000 / 2,330,000 / 2,720,000`、当前最高 `玩家A 2,100,000`、最近 `显影=金0`、候选 `总件 38 · 总格 126`、下一步 `优先补总格/全均格`；
     - 详情确认：结算 `4,405,555 · 38件/126格 · 红3件/24格`，小地图来源 `settlement_inventory`；
     - 手填确认：打开后自动填入 `aisha`、`2521 未知残骸`、`38`；
     - 地图按钮确认：hover popup 可显示，点击固定 popup 可显示；按钮额外 tooltip 仍不存在。
   - 本轮包内文案收口：
     - “下一步”在有 `金均价` 时不再提示补金/红均价；
     - 红件、红格、红均格仍保留给表格/手填/复盘，不进入推荐下一步；
     - `公开轮廓` 兜底收敛为普通可见信息优先的文案。
   - 打包产物：
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.4-full.zip`
       - SHA256 `11b452ae6101476db8afd0b2898189dbf5a9d7c2e009421753b413da10c164bb`
       - 常规群友使用版，含 raw tables，默认 diagnostic profile `portable`。
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.4-engineering.zip`
       - SHA256 `bd1fa6e09fb6d96dad5bd4a6027947e961000288ba7a9fd4f2e8a1c3bef62584`
       - 工程排查版，含 raw tables，默认 diagnostic profile `engineering`。
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.4-public-safe.zip`
       - SHA256 `e46aeb59acef9ecd0afc36b98cee68219c4766153ca926b1be4c7529f9ef6d86`
       - 公开转发版，不含 `BidMap.txt` / `Drop.txt` / `Item.txt` raw tables，需先运行 `导入本机游戏表.bat`。
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.4-SHA256.txt`
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.4-RELEASE_NOTES.zh-CN.txt`
   - 包级 clean unzip 检查：
     - 三个 zip 均解压到 `.tmp\release_unzip_checks_v014d` 干净目录；
     - 均包含 `BidKingHeroRef\BidKingHeroRef.exe`、`BidKingHeroMonitor\BidKingHeroMonitor.exe`、`Start-HeroRef.ps1`、`Start-HeroRef.bat`、`Start-HeroRef-Taskbar.bat`、`data\logs\live`；
     - `Start-HeroRef.ps1` 默认引用包内 UI/monitor exe，未默认依赖 `C:\Python313\python.exe`；
     - 每个包内 `BidKingHeroMonitor.exe --help` 可直接运行；
     - full/engineering 包含 `BidMap.txt` / `Drop.txt` / `Item.txt` / `Language.txt`；
     - public-safe 仅有 `PUT_TABLES_HERE.txt`，未包含上述 raw tables；
     - mini 下一步文本长度未撑坏布局。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> `148 passed`；
     - `C:\Python313\python.exe -m pytest tests\test_live_monitor.py tests\test_ahmad_ref_engine_public_info.py tests\test_activity_shadow_prior.py tests\test_basic_mc.py tests\test_build_processed_data.py -q` -> `112 passed`；
     - `C:\Python313\python.exe -m py_compile ...` -> passed；
     - `git diff --check` -> 无 whitespace error，仅 CRLF 提示。
   - release 边界：
     - 本次包来自 `SourceCommit=e872c3a` 加当前未提交 Hero Ref 工作区修改，`BUILD_MANIFEST.txt` 标记 `DirtyWorktree=true`；
     - 包名未包含日期或 dirty 字样，符合用户要求；
     - 主线 v3 仍未 promotion，活动 fitted prior 仍为 shadow-only / audit-only。

31. 2026-06-11 v0.1.4 next-info 文案回收
   - 用户反馈：
     - 新版 `下一步` 文案在已经有 `金均价` 时仍会提示补金/红均价；
     - calculator 不应要求普通用户补红色信息，红总格/红均格等字段可以保留给表格、手填和复盘，但不应作为推荐下一步；
     - `公开轮廓` 对玩家不如 `总格/全均格` 清晰，且不同道具语义不完全等价。
   - 日志对照：
     - 新包桌面运行目录：`C:\Users\shenc\Desktop\BidKingHeroRef-v0.1.4-full`；
     - 该局 `latest_snapshot.json` 已有 `public_numeric_summary=金均价 26,730`，说明解析链路拿到了金均价；
     - 问题在 UI fallback 的 `_next_info_hint(ref_result)` 文案策略，不在 public info 解析；
     - 旧包典型 R5 日志原文为 `补总格/全均格或红均格`，新逻辑复算为 `优先补总格/全均格`。
   - 修复：
     - `tools\ahmad_live_panel_server.py`：`下一步` 推荐顺序改为：
       1. 缺总件 -> `先补总件`；
       2. 缺总格且总格范围未锁，或红件已锁但红格只能靠总格收紧 -> `优先补总格/全均格`；
       3. 白绿/蓝未锁 -> `优先补白绿/蓝件数或均格`；
       4. 紫/金未锁 -> `补紫/金件数或均格`；
       5. 无明确普通可补项 -> `信息已足够，观察出价`。
     - `下一步` 不再生成红相关建议，也不再生成 `补金/红均价或总价` 这种价值口径建议；
     - 表格/手填/复盘中的红件、红格、红均格、红值字段不变，引擎约束不变。
   - 验证：
     - 新增测试覆盖：
       - `金均价` 已知但 q5/q6 仍有范围时，不推荐红，也不推荐均价；
       - 只剩红范围未锁时，不把红作为推荐下一步；
       - 红件已锁但红格未知时，仍推荐 `优先补总格/全均格`。
     - 桌面 v0.1.4 full 日志复算后，结算态 `下一步=信息已足够，观察出价`，`public_numeric_summary=金均价 26,730` 保留显示。
     - Tk introspection：mini `440x397`，`下一步` 文本请求宽度 `116px`，没有撑开布局；`details_card/minimap_card` 在 mini 下仍隐藏。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> `148 passed`；
     - `C:\Python313\python.exe -m pytest tests\test_live_monitor.py tests\test_ahmad_ref_engine_public_info.py tests\test_activity_shadow_prior.py tests\test_basic_mc.py tests\test_build_processed_data.py -q` -> `112 passed`；
   - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py src\bidking_lab\live\monitor.py` -> passed。

32. 2026-06-11 发布包 hotfix：PowerShell 解析与 next-step 文案收口
   - 群友反馈的 `Import-LocalTables.ps1` ParserError 已在包级处理：
     - `build_hero_ref_portable.ps1` 现在会把打包后的所有 `*.ps1` 重写为 UTF-8 BOM；
     - 当前 `BidKingHeroRef-v0.1.4-full.zip` 在 Windows PowerShell 5.1 下跑 `Import-LocalTables.ps1` 已不再报 ParserError，而是正常走到 `AppRoot not found` 的业务校验；
     - 这说明问题是包内脚本编码兼容，不是脚本逻辑本身炸掉。
   - UI 的“下一步”口径已继续收口：
     - `tools\ahmad_tk_overlay.py` 里显示给用户看的下一步改为动作文本，不再直接把 `no_raw_packets` 这类内部状态码露出来；
     - 内部诊断仍保留 `no_raw_packets`，用于 monitor / runtime status 排查。
   - public-safe 边界复核：
     - 当前解压后的 public-safe 包里，`data\raw\tables` 只有 `PUT_TABLES_HERE.txt` 占位，没有实际的 `BidMap.txt` / `Drop.txt` / `Item.txt`；
     - 包内也没有回退到系统 Python 的引用。
   - 当前 v0.1.4 三包哈希：
     - full: `0cf21a1fb812a5b97241c7d80eeb7aafac07d0bf90e2950a59f140db1a93e44f`
     - engineering: `f6e0a83cf86e884f3d5a56b5f9445bbe35ac455656d892be8b45209955806b78`
     - public-safe: `6f53cc0e4353e0c8d91060241c3a44accd35d24419d9c369a231a51254233039`
   - 这次更新不改主线 v3 promotion，继续只把 Hero Ref 当支线发布收口。

33. 2026-06-11 recordings data2/data3 排查，不打包
   - 用户明确要求：先做排查，暂时不打包。
   - `C:\Users\shenc\Desktop\recordings\data2`：
     - 本地日志显示 `capture_source_status.json` 为 `active_flows=2`、`raw_packets=0`、`accepted_frames=0`；
     - `monitor.stderr.log` 为 `FileNotFoundError: [WinError 2]`，发生在 `pydivert.WinDivert(...).open`；
     - 用户随后补截图，确认是防火墙 / 安全软件杀底层抓包，不再继续当协议问题深挖。
   - 为了后续少猜，补了诊断小修：
     - `scripts\run_windivert_live_monitor.py`：WinDivert `PermissionError` / `FileNotFoundError` / `OSError` 时写入 `capture_source_status.json` 的 `error_code`、`error_message`、`error_hint`；
     - `tools\ahmad_tk_overlay.py`：如果 capture status 有 `error_code`，mini 显示“检查防火墙/安全软件”，证据行显示具体错误码，不再只表现为普通 `no_raw_packets`。
   - `C:\Users\shenc\Desktop\recordings\data3-logsdeficit`：
     - 有效日志为 `monitor.stdout (1).log`，连续归档 7 个 reset；
     - 当前 `latest_snapshot.json` 是 `4401:1425860450521121`，`phase=settled`，`ui_contract.truth.available=true`，33 件 / 73 格 / `507630`，小地图 `settlement_inventory` 且 `layout_complete=true`；
     - `raw\windivert_live.jsonl` 同 session 有 `0x002D`，与 latest 对齐；
     - `raw\archive\reset` 中 7 个样本有 6 个带 `0x002D`，均复放为 `truth.available=true`；
     - 唯一 partial：`windivert_live_2026-06-11_185557_4401_1425860449894597_reset.json`，没有 `0x002D`，只到 R2/R3 bidding，因此不能当结算 truth 异常样本。
   - 两个旧导出 zip：
     - `HeroRefDiag-20260611-171256-4402_1425860441516292.zip` 有结算帧；旧 latest 总值 `666861`，当前 v308 复放同一 raw 为 `1222416`，差值 `555555` 来自新增物品 `1036007` “退钱”手举牌旧表缺价格；结论是价格表 / 新物品版本漂移，不是 missing settlement block；
     - `HeroRefDiag-20260611-171943-4410_1425860442951286.zip` 复放与 latest 对齐，32 件 / 75 格 / `370645`；hero 为 Gabriela，ref readiness `not_structured_hero`，settlement truth 完整。
   - 样本索引已更新：`docs\hero_ref_settlement_sample_index_2026-06-11.zh-CN.md` 第 7 节。
   - 已跑：
     - `C:\Python313\python.exe -m pytest tests\test_windivert_live_monitor.py::test_write_source_status_records_windivert_open_error tests\test_live_overlay.py::test_ahmad_render_missing_surfaces_windivert_open_error tests\test_live_overlay.py::test_ahmad_render_missing_uses_action_text_for_next_step -q` -> `3 passed`；
   - `C:\Python313\python.exe -m py_compile scripts\run_windivert_live_monitor.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_windivert_live_monitor.py tests\test_live_overlay.py` -> passed。

34. 2026-06-11 admin launcher bat 的中文行在 cmd 下解析异常
   - 复现结论：
     - `apps\hero_ref\管理员启动HeroRef_悬浮窗.bat` 和 `apps\hero_ref\管理员启动HeroRef_任务栏窗口.bat` 之前是 LF-only；
     - 在 `cmd.exe` 里跑含中文 `echo` 的 LF-only 版本，会把命令读歪，出现 `not recognized` 的碎片错误；
     - 同内容改成 CRLF 后，中文提示可以正常打印。
   - 修复：
     - 已将这两份 admin launcher 归一化为 CRLF，保留原有中文提示和 `call Start-HeroRef*.bat` 链路；
     - `build_hero_ref_portable.ps1` 打包时也会把输出包内所有 `*.bat` 归一化为 UTF-8 无 BOM + CRLF；
     - 纯 ASCII 的 `Start-HeroRef.bat` / `Start-HeroRef-Taskbar.bat` 不受影响。
   - 验证：
     - 用 stub `Start-HeroRef.bat` 进行隔离测试后，两个 admin launcher 都能正常输出中文提示，不再吐出 `cmd.exe` 的命令未识别错误。
     - `tests\test_hero_ref_scripts_encoding.py` 新增非 ASCII bat 的 no-BOM / CRLF 检查；
     - 已跑：`C:\Python313\python.exe -m pytest tests\test_hero_ref_scripts_encoding.py -q` -> `2 passed`；
     - 已跑：PowerShell `scriptblock` parse check for `build_hero_ref_portable.ps1` -> `parse-ok`。

35. 2026-06-11 v0.1.5 简化包入口与 next-info 顺序
   - 用户反馈：
     - 包根目录里可执行入口太多，对不熟悉电脑的群友容易造成选择困难；
     - 继续保留中文 txt/md 操作说明，但最终包根目录的 bat 入口改成英文；
     - `下一步` 文案希望更接近玩家可补信息顺序：白绿、蓝、紫、金、总格/均格，红相关不主动催用户补。
   - next-info 修复：
     - `_next_info_hint(ref_result)` 的优先级改为：
       1. 缺总件 -> `先补总件`；
       2. 白绿 / 蓝 count range 未锁 -> `优先补白绿/蓝件数或均格`；
       3. 紫 / 金 count range 未锁 -> `补紫/金件数或均格`；
       4. 以上都没有普通可补项时，再推荐 `优先补总格/全均格` 或 `补总格/全均格`；
       5. 红不作为常规 next-step 推荐，仍保留手填/复盘/表格字段。
     - 新增测试覆盖：金 count range 未锁且总格也缺时，优先推荐 `补金件数或均格`，不抢到总格，也不出现红。
   - 包结构修复：
     - 新增英文 wrapper：`Import-LocalTables.bat`、`Stop-HeroRef.bat`；
     - `build_hero_ref_portable.ps1` 复制模板后会移除中文 bat：
       - `管理员启动HeroRef_悬浮窗.bat`
       - `管理员启动HeroRef_任务栏窗口.bat`
       - `导入本机游戏表.bat`
       - `停止HeroRef.bat`
     - 最终包根目录只保留 4 个英文 bat：
       - `Start-HeroRef.bat`
       - `Start-HeroRef-Taskbar.bat`
       - `Import-LocalTables.bat`
       - `Stop-HeroRef.bat`
     - 中文 `使用说明.txt`、`管理员运行说明.txt`、`火绒拦截说明.txt`、`VPN或UU备用启动.txt` 仍保留。
   - 已构建：
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.5-full.zip`
       - SHA256 `EDBB761CF7E1E7B5F83F33CA7336621FECDDA664BF3140C211953E3C000F886A`
       - 包含 raw tables，仅本机/可信私发。
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.5-public-safe.zip`
       - SHA256 `B8C0D5BCE1ABD611D4ABB4AD63E2ED01462AC6CF56866F392A8E3E2734CF4135`
       - 不包含 raw tables，需先运行 `Import-LocalTables.bat`。
     - release note：`external_references\ahmad_live_reference_lab\dist\RELEASE_NOTES_v0.1.5.zh-CN.md`。
   - 验证：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> `151 passed`；
     - `C:\Python313\python.exe -m pytest tests\test_hero_ref_scripts_encoding.py -q` -> `2 passed`；
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py` -> passed；
     - PowerShell parse check for `build_hero_ref_portable.ps1` -> `parse-ok`；
     - v0.1.5 full/public-safe zip 内容检查：
       - 根目录 bat 均为英文；
       - 中文 bat 数量为 0；
       - 4 个 bat 均为 UTF-8 no BOM + CRLF；
       - full 包含 `BidMap.txt` / `Drop.txt` / `Item.txt`；
       - public-safe 不包含上述 raw tables。
     - `git diff --check` -> 无 whitespace error，仅 CRLF 提示。

36. 2026-06-11 红品与价值候选对应、金均格 0 exact 展示修复（未打包）
   - 用户反馈：
     - mini 的“红品与价值”里，红件 / 红格候选不能独立升序展示；当金候选是 `2 / 3 / 4` 且金红总量为 6 时，红候选应按同一列互补显示为 `4 / 3 / 2`；
     - 金均格为 0 时，engine 已能推 q5=0，但 mini/手填叠加显示仍可能像未锁定；
     - 本次不改底部手填表的 `均格 / 件 / 格 / 均价 / 总价` 排布。
   - 修复：
     - `tools\ahmad_live_panel_server.py` 新增红品显示层 helper：
       - 只有在能推出 exact `金+红` 件数 / 格数总量，且互补候选集合与 engine 的红候选集合一致时，才把红候选按金候选同列互补展示；
       - 无法证明对应关系时保持原引擎候选，不硬猜；
       - 已锁定范围压缩为单值展示，例如 `金件 0`、`红件 1`，不再显示 `0 / 0 / 0`。
     - `tools\ahmad_tk_overlay.py`：
       - 手填 `某品质均格=0` 且件 / 格无矛盾时，直接写入 `fixed_counts=0` 和 `quality_cells=0`；
       - `0 均格 / 0 件 / 0 格` 在通用均格一致性校验里显式合法；
       - 手动本地计算路径复用同一套红候选互补展示 helper。
   - 验证：
     - 新增测试覆盖：
       - live summary 中 `avg_cells.q5=0` -> engine evidence `fixed_counts.q5=0`、q5 件/格 range 为 `[0,0,0]`，mini summary 显示 `金件 0`；
       - 金候选 `2 / 3 / 4`、金红总件 exact 6 -> 红件显示 `4 / 3 / 2`；格数同理；
       - 底部手填表的品质行和值行字段顺序保持不变。
     - 已跑：
       - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> `154 passed`；
       - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_victor_q4_q5_q6_count_sum_and_zero_gold_avg -q` -> `1 passed`；
       - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py` -> passed；
       - `git diff --check -- external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_overlay.py` -> 无 whitespace error，仅 CRLF 提示。
   - 状态：
     - 本次只修当前工作区代码与测试，未重新打包。

37. 2026-06-11 手填均格 0 的输入框联动（未打包）
   - 用户确认：手填某品质 `均格=0` 时，希望同品质 `件` / `格` 空框也肉眼显示为 `0`，而不是只在计算层 exact。
   - 修复：
     - `tools\ahmad_tk_overlay.py` 的手填派生刷新中，若某品质 `均格=0` 且 `件` / `格` 都没有非 0 冲突，则自动把空的 `件`、`格` 输入框补成 `0`；
     - 点击“应用并启用”解析时也做兜底补写，防止即时刷新未触发；
     - 如果用户已经填了非 0 件或格，不自动覆盖，仍按原有 hard conflict 报错。
   - 验证：
     - 新增测试覆盖：
       - 编辑 `金均格=0` 时，空的 `金件` / `金格` 自动显示 `0`；
       - 已有 `金件=4` 时，不自动把 `金格` 补成 `0` 来掩盖冲突；
       - 点击应用路径也会补写空框并输出 `fixed_counts.q5=0`、`quality_cells.q5=0`。
     - 已跑：
       - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> `157 passed`；
       - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py` -> passed；
       - `git diff --check -- external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_overlay.py` -> 无 whitespace error，仅 CRLF 提示。
   - 状态：
     - 本次只修当前工作区代码与测试，未重新打包。

38. 2026-06-11 红格候选物理配对与手填任意 0 联动（未打包）
   - 用户反馈：
     - mini “红品与价值”出现 `红件 3 / 1 / 0`、`红格 0 / 4 / 9`，第一列等价于 3 件红 0 格，不可能；
     - 手填希望不只是 `均格=0` 触发联动，而是同一品质 `均格 / 件 / 格 / 均价 / 总价` 任意一个为 0，其他空框也自动变为 0，并且进入推理输入。
   - 红格修复：
     - `tools\ahmad_live_panel_server.py` 中，红件仍可按金件互补列显示；
     - 红格不再独立按金格互补列展示，而是按红件显示列重排，并校验：
       - 红件为 0 时红格必须为 0；
       - 红件大于 0 时红格至少不小于件数；
       - 无法形成物理合法配对时，不使用该互补展示。
     - 新增测试覆盖截图同形态：原始红件 `0 / 1 / 3`、红格 `0 / 4 / 9`，金件互补后显示为红件 `3 / 1 / 0`、红格 `9 / 4 / 0`。
   - 手填 0 联动修复：
     - `tools\ahmad_tk_overlay.py` 中，同一品质任意一个字段为 0，且没有非 0 冲突时，空的 `均格 / 件 / 格 / 均价 / 总价` 都会自动补 0；
     - 点击“应用并启用”时也兜底补写；
     - 如果同时存在非 0 字段，直接 hard conflict，例如 `均价=0` 但 `件=3`；
     - 应用后的 `structured_ref_inputs` 会带入 `fixed_counts=0`、`quality_cells=0`、`avg_cells=0`、`avg_values=0`、`quality_values=0`，引擎实际使用该信息。
   - 验证：
     - 已跑：
       - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> `160 passed`；
       - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_zero_quality_avg_value_fixes_count_zero tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_victor_q4_q5_q6_count_sum_and_zero_gold_avg -q` -> `2 passed`；
       - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py` -> passed；
       - `git diff --check -- external_references\ahmad_live_reference_lab\tools\ahmad_live_panel_server.py external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py tests\test_live_overlay.py` -> 无 whitespace error，仅 CRLF 提示。
   - 状态：
     - 本次只修当前工作区代码与测试，未重新打包。

39. 2026-06-11 data4 无红局中途偏红排查与金总价 soft weight（未打包）
   - 用户反馈：
     - `C:\Users\shenc\Desktop\recordings\data4` 中有一局第五轮附近“没红，但计算器算成有红且约 73w”。
   - 样本定位：
     - 匹配“无红 + 73w 附近中途估价”的样本是：
       - `C:\Users\shenc\Desktop\recordings\data4\data\logs\live\raw\archive\reset\windivert_live_2026-06-11_212612_2410_1425860462549881_reset.json`
       - session `2410:1425860462549881`，map `2410`。
     - `C:\Users\shenc\Desktop\recordings\data4\logs\live` 根目录里的最新 `4401:1425860450521121` 结算实际有 `q6=1 / 4格 / 266050`，不是这次“没红”反馈对应局。
   - 根因：
     - 结算解析本身正确：完整回放最终 truth 为 `q6 count=0 / cells=0 / value=0`。
     - 问题出在结算前：中途已有 `total_count=50`、`q3 count=16`、`q1/q3/q4/q5 avg_cells`、`q5 value_sum=208230`，但没有 `q5 avg_value`；
     - 旧逻辑只把 `q5 value_sum` 用作金总价展示/价值点，不参与金件数候选加权，因此允许 `q5=3 + q6=3` 的组合占优，形成 72w 左右偏红估价。
   - 修复：
     - `src\ahmad_ref_engine.py` 新增 `quality_value_soft_weight_v0`：
       - 当某品质有 exact `quality_values`，但没有对应 `avg_values` 时，按当前候选的件数/格数估计该品质总价中心；
       - 与 exact 总价偏离越大的候选软降权；
       - 不做 hard lock，避免把异常高价金件/低价金件误判成矛盾；
       - `avg_values` 已存在时仍走原有 exact 件数推导，`0` 语义仍走 existing zero absent 逻辑。
   - 映射验证：
     - raw prefix `SortID<=18`：
       - 输入含 `q5 avg_cells=3.6666667461395264`、`q5 value_sum=208230`；
       - 修复后 `q5 count=[6,6,6]`，`q6 count/cells/value=[0,0,0]`，balanced 约 `293258`。
     - raw prefix `SortID<=23`：
       - 修复后 `q5 count=[6,6,6]`，`q6 count/cells/value=[0,0,0]`，balanced 约 `293959`；
       - `summarize_snapshot(...).ahmed_ref` 同步输出 `red_count_range/red_cells_range/red_value_range=[0,0,0]`。
     - full settlement：
       - truth 仍为 `q6 count=0 / cells=0 / value=0`，没有破坏结算复盘。
   - 验证命令：
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py tests\test_ahmad_ref_engine_public_info.py` -> passed；
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_quality_value_sum_soft_weights_count_without_avg_value tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_quality_value_sum_and_avg_value_derive_count tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_zero_quality_avg_value_fixes_count_zero -q` -> `3 passed`；
     - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> `54 passed`。
   - 状态：
     - 本次只修当前工作区代码与测试，未重新打包。

40. 2026-06-11 均价 + 均格 exact-only 件数交集（未打包）
   - 用户确认：
     - `均价 + 均格` 可以做轻量联合推导，但不要把“最可能”硬写成 truth；复杂概率锁继续留给 v3 主线。
   - 语义：
     - `avg_values` 约束：某品质件数乘均价后必须能形成合法整数总价；
     - `avg_cells` 约束：某品质件数乘均格后必须能形成合法整数格，并且该格数可由物品形状组合出来；
     - 只有在 `total_count` 范围内的合法件数交集唯一时，才写入 `fixed_counts/min_counts`；
     - 交集为空或多于一个候选时不 hard lock，不新增 hard conflict，让后续枚举/先验继续处理。
   - 修复：
     - `src\ahmad_ref_engine.py` 新增 `avg_value_cells_{quality}_count_derived` exact-only 推导；
     - 该推导放在残差推导之前，若某品质因此 exact，后续 `total_count` / `count_sums` residual 仍能继续补齐其它品质；
     - 若已有 `quality_values` 或 `quality_cells`，继续使用原有更强的 `均价+总价`、`均格+总格` exact 路径，不走该平均值交集捷径。
   - 验证：
     - 新增正例：`total_count=7`、`q5 avg_value=34288.75`、`q5 avg_cells=3.25`，合法交集唯一为 `q5=4`，写入 `fixed_counts.q5=4`；
     - 新增负例：`total_count=12`、同样均价/均格，合法交集多于一个，不写入 `fixed_counts.q5`；
     - 已跑：
       - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py tests\test_ahmad_ref_engine_public_info.py` -> passed；
       - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_avg_value_and_avg_cells_unique_intersection_derives_count tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_avg_value_and_avg_cells_multiple_intersections_do_not_lock tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_quality_value_sum_soft_weights_count_without_avg_value tests\test_ahmad_ref_engine_public_info.py::test_ref_engine_quality_value_sum_and_avg_value_derive_count -q` -> `4 passed`；
       - `C:\Python313\python.exe -m pytest tests\test_ahmad_ref_engine_public_info.py -q` -> `56 passed`。
   - 状态：
     - 本次只修当前工作区代码与测试，未重新打包。

41. 2026-06-11 预打包轻量化审查与 taskbar 入口收口（未打包）
   - 用户目标：
     - 打包前先审查是否还有影响运行质量的常驻审计代码；
     - 另一个窗口试做了 `Start-HeroRef-Taskbar.ps1`，但不希望临时分支改动污染当前发布包；
     - 本轮仍暂时不打包。
   - 运行轻量化：
     - `tools\ahmad_tk_overlay.py` 的 `hero_ref_ui_runtime_status.json` 不再对同一 UI/capture 状态反复写盘；
     - 相同状态 10 秒内去重，状态变化、capture 计数变化、worker/manual 状态变化和错误仍会即时覆盖写；
     - `capture_source_status.json`、diagnostic export、UI health stall log 继续保留，因为它们仍是排查“UI 开着但 monitor 没刷新”的必要证据。
   - taskbar 包边界：
     - 正式 taskbar 能力已经由 `Start-HeroRef.ps1 -ShowTaskbar` 和 `Start-HeroRef-Taskbar.bat` 提供；
     - `build_hero_ref_portable.ps1` 在输出包内移除临时 `Start-HeroRef-Taskbar.ps1`，并把包内 `Start-HeroRef-Taskbar.bat` 固定为调用 `Start-HeroRef.ps1 -ShowTaskbar`；
     - `BUILD_MANIFEST.txt` 不再列 `LauncherTaskbarPowerShell`，避免群友看到多一层启动入口。
   - 验证：
     - `C:\Python313\python.exe -m pytest tests\test_live_overlay.py -q` -> `161 passed`；
     - `C:\Python313\python.exe -m pytest tests\test_hero_ref_scripts_encoding.py -q` -> `2 passed`；
     - `C:\Python313\python.exe -m py_compile external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py` -> passed；
     - PowerShell parse check：`build_hero_ref_portable.ps1`、`Start-HeroRef.ps1`、`Import-LocalTables.ps1`、`Stop-HeroRef.ps1` -> passed；
     - `git diff --check` -> 无 whitespace error，仅 CRLF 提示。
   - 状态：
     - 临时 `apps\hero_ref\Start-HeroRef-Taskbar.ps1` 已移出源码树，`apps\hero_ref\Start-HeroRef-Taskbar.bat` 已恢复为直接调用 `Start-HeroRef.ps1 -ShowTaskbar`；
     - 当前剩余改动是本轮轻量化、包脚本防污染、测试和记录，提交后即可形成 clean checkpoint；本轮仍未重新打包。

42. 2026-06-11 v0.1.6 full/public-safe 包发布记录
   - 代码 checkpoint：
     - source commit：`8503625 Reduce Hero Ref runtime diagnostics churn`；
     - build manifest：`DirtyWorktree=false`；
     - `main` 已 push 到 `origin/main`。
   - 产物：
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.6-full.zip`
       - SHA256：`C8CFBABC8FB1F86B22B291984EB2E4FD85F6DE2F35475E7FDA0B81517F5EE445`
       - bytes：`44113285`
       - 包含 raw tables，仅适合本机测试或可信私发。
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.6-public-safe.zip`
       - SHA256：`BF8798197019F17CE75DB7FE6BB67C224E7DB6E6FA4BFC6C9CFB138A82567CEC`
       - bytes：`40336693`
       - 不包含 raw tables，用户需先用 `Import-LocalTables.bat` 导入本机游戏表。
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.6-SHA256.txt`
     - `external_references\ahmad_live_reference_lab\dist\RELEASE_NOTES_v0.1.6.zh-CN.md`
   - clean unzip smoke：
     - full/public-safe manifest 均为 `PackageVersion=v0.1.6`、`DirtyWorktree=false`、`RequiresExternalPython=False`；
     - 根目录 bat 仅保留 `Start-HeroRef.bat`、`Start-HeroRef-Taskbar.bat`、`Import-LocalTables.bat`、`Stop-HeroRef.bat`；
     - 未发现临时 `Start-HeroRef-Taskbar.ps1` 或 `LauncherTaskbarPowerShell`；
     - `Start-HeroRef-Taskbar.bat` 明确调用 `Start-HeroRef.ps1 -ShowTaskbar`；
     - 包内 `Start-HeroRef.ps1`、`Import-LocalTables.ps1`、`Stop-HeroRef.ps1` PowerShell parse 通过；
     - full 包含 `BidMap.txt` / `Drop.txt` / `Item.txt` / `Language.txt`，public-safe 只保留 `PUT_TABLES_HERE.txt`；
     - `data\logs\live` 存在；
     - UI exe `--help` 输出正常，monitor exe `--help` exit 0。

43. 2026-06-12 data6 公开大红下界修复（未打包）
   - 用户反馈：
     - `C:\Users\shenc\Desktop\recordings\data6` 中，公开信息已见大红时，红件显示 `2/?/?`，红格被显示层抬到 `15/15/15`，但红值仍只有二三十万到四十多万，低于已公开的大红价值。
   - 样本定位：
     - 当前问题快照：`C:\Users\shenc\Desktop\recordings\data6\logs\live\latest_snapshot (1).json`
     - session：`2309:1425860479021171`，hero：`ahmed`，map：`2309`，round：`5`。
     - `public_info_rows` 中 `info_id=200023` 揭示 `民用垂直起降飞行器`：`quality=6`、`cells=15`、`value=452800`。
     - 结算 truth：`q6 count=2 / cells=16 / value=520900`，总已知结算值 `858400`。
   - 根因：
     - 公开揭示物品原来只进入 `public_quality_reveal_min_counts`，即只约束“某品质至少几件”；
     - 具体物品的格数和价值没有进入 ref 引擎，只由 UI 显示层用 minimap/已见红做红格 floor；
     - 结果是红格显示被抬高，但红值仍按普通红先验估算，出现低于已公开大红价值的候选。
   - 修复：
     - `src\ahmad_ref_engine.py` 新增 `quality_cell_floors` / `quality_value_floors`；
     - 非 bucket-outline 的 `public_info_rows[].revealed_items_detail[]` 会按品质累计已公开物品的格数下界和值下界；
     - 枚举格数候选必须满足对应品质的格数下界；
     - 品质价值和红值分布不再低于已公开物品价值下界；
     - bucket outline 仍保持原有 exact bucket 语义，不把随机公开物品误当成完整红桶。
   - data6 回放验证：
     - 修复前前结算口径：红件 `2/2/2`，红格原始 `5/6/7`，红值 `237859/335240/423949`；
     - 修复后前结算口径：红件 `2/2/2`，红格 `15/16/17`，红值 `452800/459933/603588`；
     - 总报价从约 `551326/599022/646717` 抬到约 `635501/698640/761778`，仍低于最终 `858400` 属于隐藏第二红与全局价值不确定性残差，不再违反“已见大红价值下界”。
   - 验证命令：
     - `python -m py_compile external_references\ahmad_live_reference_lab\src\ahmad_ref_engine.py` -> passed；
     - `pytest -q tests\test_ahmad_ref_engine_public_info.py` -> `57 passed`；
     - `pytest -q tests\test_live_overlay.py::test_ahmad_server_summary_pairs_red_candidates_with_gold_candidates tests\test_live_overlay.py::test_ahmad_server_red_display_keeps_count_and_cells_physically_paired tests\test_live_overlay.py::test_ahmad_server_summary_keeps_public_info_marker_soft tests\test_live_overlay.py::test_ahmad_server_summary_keeps_public_info_item_name` -> `4 passed`；
     - `git diff --check` -> 无 whitespace error，仅 CRLF 提示。
   - 状态：
     - 本次只修当前工作区代码与测试，未重新打包。

44. 2026-06-12 v0.1.6-hotfix full/public-safe 包记录
   - 用户目标：
     - 基于 data6 公开大红下界修复，生成一个名字带 `hotfix` 后缀的新包，方便群里替换分享。
   - 代码来源：
     - `SourceCommit=a34539f`；
     - 包内 `BUILD_MANIFEST.txt` 标记 `DirtyWorktree=true`；
     - dirty 内容是本轮公开揭示物品格数/价值下界 hotfix、对应测试、执行记录。
   - 产物：
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.6-hotfix-full.zip`
       - SHA256：`137B597B550EA2ACFC905A8BECBA47E9BE92145058109EA8F3CB848BAFCC9458`
       - bytes：`44115089`
       - 包含 raw tables，适合本机测试或可信私发。
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.6-hotfix-public-safe.zip`
       - SHA256：`D635E76CD0EED5D3E5E005F52FFF3A2D5F174CD663C8CB6BB0022668D9866169`
       - bytes：`40338497`
       - 不包含 raw tables，首次运行前用 `Import-LocalTables.bat` 导入本机游戏表。
     - `external_references\ahmad_live_reference_lab\dist\BidKingHeroRef-v0.1.6-hotfix-SHA256.txt`
     - `external_references\ahmad_live_reference_lab\dist\RELEASE_NOTES_v0.1.6-hotfix.zh-CN.md`
   - clean unzip smoke：
     - full/public-safe manifest 均为 `PackageVersion=v0.1.6-hotfix`、`DirtyWorktree=true`、`RequiresExternalPython=False`；
     - 根目录 bat 仅有 `Start-HeroRef.bat`、`Start-HeroRef-Taskbar.bat`、`Import-LocalTables.bat`、`Stop-HeroRef.bat`；
     - 未发现临时 `Start-HeroRef-Taskbar.ps1`；
     - `Start-HeroRef-Taskbar.bat` 调用 `Start-HeroRef.ps1 -ShowTaskbar`；
     - `Start-HeroRef.ps1`、`Import-LocalTables.ps1`、`Stop-HeroRef.ps1` PowerShell parse 通过；
     - full 包含 `BidMap.txt` / `Drop.txt` / `Item.txt` / `Language.txt`，public-safe 只保留 `PUT_TABLES_HERE.txt`；
     - `data\logs\live` 存在；
     - UI exe `--help` 输出正常，monitor exe `--help` exit 0。

45. 2026-06-12 hotfix2 候选：公开精确数值 + 显示均格 + 金格归零（待打包）
   - 用户反馈 / 样本：
     - 截图：`200011=0`（金品质总占用格数 0 格）时 UI 仍显示金件 `1/2/4`、红格 `0/4/9`（ahmed 2410 R1）。
     - 均格：`2.09×11→23` 等显示截断导致精确乘法失败；recordings / fatbeans 有 `2.909…`、`2.428571…` 等浮点样本。
     - 红格 mini 行：锁定红件后仍显示 `3/?/?` 而非 `3/3/3`。
   - 修复（`src\ahmad_ref_engine.py`）：
     - 消费 `public_info_rows` 精确字段：`200009/200017` 总会话、`200010–200012` 品质总格、`200018–200020` 品质件数。
     - `quality_cells.q*=0` 同步 `fixed_counts.q*=0`（含 `200011=0` 截图路径）。
     - 显示均格 fallback：仅对像屏幕读数的 ≤3 位小数启用（如 `2.09`），避免长比例浮点误扩候选。
   - 修复（UI）：
     - `ahmad_live_panel_server.py` / `ahmad_tk_overlay.py`：红件/红格 range 用 `_red_range_text`，锁定三元组不再折叠成 `3/?/?`。
   - 测试：
     - `tests\test_ahmad_ref_engine_public_info.py`：`200009–200020` 参数化 + 均格 capture fixtures；`85 passed`。
     - `tests\test_live_overlay.py`：WinDivert error 诊断 + 红 range 显示；与 ref 合计 `247 passed`（overlay + public_info 子集）。
   - 群友 WinDivert 被删：
     - `capture_source_status.error_code` 路径已能提示「检查防火墙/安全软件」；环境侧暂不继续产品化兜底，长期可能换抓包底层。
   - 状态：
     - 已随 commit `3cebdc2` 入库；最终 hotfix2 发包含 §47 monitor 修复（`dcb1bd1`）。

46. 2026-06-12 规划：mini UI 顶部倒三角缩放应联动字体（hotfix2 不做）
   - 群友反馈：
     - 希望拖 mini UI 顶部 resize grip（倒三角）时，窗口变大后 **字体/控件整体放大**，而不只是露出更多折叠区域。
   - 现状（`tools\ahmad_tk_overlay.py`）：
     - `top_resize_grip` → `_resize_window` 只改 `root.geometry(width x height)`；
     - `details_expanded` 时记录 `_custom_details_size`；字体仍为固定 tuple（如 `FONT_UI 7–12`、`FONT_NUMERIC 15`），不随窗口 scale。
   - 目标行为（后续版本）：
     - 引入 `ui_scale`（或按基准窗口宽高比计算 scale factor），拖动 grip 时同步更新 scale；
     - 统一刷新已创建 widget 的 `font=` / padding / minimap cell size；持久化到本地 prefs（可选）；
     - 与「详情展开」模式解耦：缩放 = 视觉放大，展开 = 显示更多 panel 行。
   - 非目标 / 风险：
     - hotfix2 不改布局树，避免打包前引入 Tk 全量 reconfigure 回归；
     - 需单独 visual QA：430×320 最小尺寸、任务栏窗口模式、配色/置顶/手填模式下的可读性。
   - 建议实现顺序：
     1. 抽 `FONT_UI_BASE` / `FONT_NUMERIC_BASE` + `_scaled_font(base, scale)` helper；
     2. resize 结束（`_end_resize`）或 motion 节流时 `_apply_ui_scale(scale)`；
     3. pytest 只测 scale 计算；视觉用 `$product-ui-polish` + 截图对比。
   - 状态：**工作树已实现（2026-06-12）** — 迷你模式 **宽度驱动 scale**（`compute_mini_ui_scale`），**横/竖拖均放大**（取 max(Δx,Δy)），高度 **实时自动贴合**内容；详情模式仍自由改宽高。拖动 grip **实时**改字体/间距（不必等松手）。

47. 2026-06-12 hotfix2 补充：关 UI 后停止 monitor + v0.1.6-hotfix2 发包
   - 群友反馈：
     - 关闭 Hero Ref UI 后，解压目录仍显示「文件夹正在使用」，无法删除/移动/重打包；疑 monitor 仍在后台占目录。
   - 根因：
     - `Start-HeroRef.ps1` 仅在启动 5 秒内读到 `monitor.lock` 时才传 `--stop-pid-on-exit`；race / 直接双击 UI exe 时关窗不会杀 monitor。
   - 修复（`tools\ahmad_tk_overlay.py` + 启动脚本）：
     - 退出 cleanup 兜底读 `snapshot 同目录/monitor.lock`，终止 PID 并删 lock；
     - 新增 `--keep-monitor-on-close`（`-KeepMonitorOnClose` 调试保留 monitor）；
     - monitor 先退出导致 UI 关闭的路径也走 cleanup。
   - 测试：
     - `tests\test_live_overlay.py` 新增 exit cleanup fallback / keep-monitor 用例；全文件 `166 passed`；
     - 与 `test_ahmad_ref_engine_public_info.py` 合计 `251 passed`。
   - Git：
     - engine/UI hotfix2：`3cebdc2`；
     - monitor lifecycle：`dcb1bd1`（发包用此 commit）。
   - 产物（`dist\`，PackageVersion=v0.1.6-hotfix2，`SourceCommit=a2fa686`，`DirtyWorktree=false`）：
     - `BidKingHeroRef-v0.1.6-hotfix2-full.zip` — SHA256 `190770CCFE562E5FF3BC0B1C1A024C698F2C2847D08C82B1D7ED0CF681CEDEB9`，43165883 bytes；
     - `BidKingHeroRef-v0.1.6-hotfix2-public-safe.zip` — SHA256 `1B9DA0907011717C5CCC2B7EB8C60E4A75CD7AA783C78330BA22BCDAD7AF1D23`，39421739 bytes；
     - `RELEASE_NOTES_v0.1.6-hotfix2.zh-CN.md` / `BidKingHeroRef-v0.1.6-hotfix2-SHA256.txt`（同步 Desktop）。
   - 备注：
     - 若仍被占用，先 `Stop-HeroRef.bat` 或结束 `BidKingHeroMonitor.exe`；
     - 初版 hotfix2（仅 `3cebdc2`、无 monitor fix）如已私发，请换本包。

48. 2026-06-12 规划：紫局（q4）均价+均格不唯一时用 ranking 软收窄（hotfix2 不做）
   - 群友反馈：
     - 「紫的难算」；高质量紫局误差偏大；金「估价+均格」cheap 组合误差小，希望紫也有类似泛用优化。
   - 现状（`src\ahmad_ref_engine.py`）：
     - 公开 `200036` 紫均价 → `avg_values.q4`；`200013` / action `100112` 紫均格 → `avg_cells.q4`；
     - `_apply_avg_value_cells_exact_count_intersection` 仅在交集中**唯一**候选时硬锁；紫局常见 0 候选或多候选 → 不锁；
     - 强行硬锁或缺少总件/紫金红件和时，可能出现 `no_reachable_combo`（样本：紫均价 `5615.625` + 紫均 `2.9` + 总件 10 → 交集为空）。
     - 金（q5）同路径在总件/件和约束下常能硬锁或枚举收窄；公开 `200037` 单独也常能把 q5/q6 压到单点（fatbeans 回放已见）。
   - 目标行为（后续版本）：
     - 交集不唯一或为空时**不要**硬锁；改为用 **总格 / 紫金红件和 / 随机均价软约束** 对候选 combo 做 log-weight ranking；
     - 输出仍保留宽范围 UI，但在 `notes` / `next_info_hint` 标明「紫件数偏好 N」而非 silent fail；
     - 与现有 `quality_value_soft_weight_v0`、`public_random_avg_value_floor_*` 共用权重框架，避免单独一套紫逻辑。
   - 非目标 / 风险：
     - hotfix2 不改 ref 枚举权重，避免未测 regression；
     - 需 fatbeans 紫局负例集（多候选 / 0 候选 / 高质量局）+ pytest 固定 ranking 行为，再考虑 promotion。
   - 建议实现顺序：
     1. 审计 `data\samples\fatbeans` 中 `200036`/`200013` 共现 batch，列出 intersection 候选数分布；
     2. 在 `_apply_avg_value_cells_exact_count_intersection` 失败分支写 diagnostic note（已有宽范围时不再报 hard conflict）；
     3. 新增 `purple_avg_value_cells_rank_v0` soft weight（仅 q4，仅 intersection 非唯一）；
     4. 对照群友局 replay，确认不再 `no_reachable_combo` 且 top combo 方向正确。
   - 状态：**仅规划，hotfix2 不包含。**

49. 2026-06-12 hotfix2.1：前几轮计算性能修复 + 发包
   - 群友 / 本机反馈：
     - hotfix2 起前几轮 Hero Ref 明显变慢；`start_ahmad_live.ps1` 与打包版均有。
   - 根因（已确认）：
     - hotfix2 将公开精确字段 `200010/200011/200012`（紫/金/红**总格**）写入 `quality_cells`；
     - `_should_use_sparse_exact_total_prior` 原逻辑为「`quality_cells` 非空即禁用快路径」→ 走完整嵌套枚举（可达 ~11s / 5 万组合量级）；
     - 合成复现：`200017=33` + `200011=23` 约 11–18s；仅总件数约 0.5–1.2s。
   - 修复（`src\ahmad_ref_engine.py`）：
     - 新增 `_quality_cells_blocks_sparse_exact_prior`：**仅当 ≥2 个品质有正总格** 才禁用 sparse prior；
     - 单个金总格（典型 R1–R2）仍走 `sparse_exact_total_prior_enumeration` + probability prior；
     - 回归：`test_ref_engine_public_gold_total_cells_keeps_sparse_prior_path`；`test_ahmad_ref_engine_public_info.py` + `test_live_overlay.py` → **252 passed**。
   - data7 群友包复核（`Desktop\recordings\data7\data`，`v0.1.6-hotfix-full`）：
     - 53 局归档回放 138 个前几轮窗口；9 处 `200011`，修复后应恢复 `sparse=True`；
     - **另一类慢**（本版未改）：R1 尚无总件数 `200017`、仅有仓储总格时 → `total_count_from_ref_count_prior`（center±4），艾哈迈德 R1 常见 4–6s，艾莎 2407 极端 ~100s（36260 组合）；与 hotfix2 bug 独立。
   - 产物（`dist\`，PackageVersion=v0.1.6-hotfix2.1，`SourceCommit=f9fca54`，`DirtyWorktree=true`）：
     - `BidKingHeroRef-v0.1.6-hotfix2.1-full.zip` — SHA256 `D58872FA9E7E8BCD135F85C9F068674EA9F681231C6C45AADDE449EF153A52E4`，44119810 bytes；
     - `BidKingHeroRef-v0.1.6-hotfix2.1-public-safe.zip` — SHA256 `94EDE7CB695860197EE902F77F04376AA455568BF1C86F1CDC1240003DBA6AA1`，40343227 bytes；
     - `RELEASE_NOTES_v0.1.6-hotfix2.1.zh-CN.md` / `BidKingHeroRef-v0.1.6-hotfix2.1-SHA256.txt`。
   - 相对 hotfix2 变更摘要：
     - 仅 ref 引擎 sparse prior 路由；继承 hotfix2 全部 engine/UI/monitor 修复。
   - 备注：
     - hotfix2（无本修复）如已群发，请换 hotfix2.1；Quark 链接待上传后补。

50. 2026-06-12 后续规划汇总（版本号稳定后再细化实现）
   - **性能（Hero Ref ref_v0）**
     1. R1 无总件数、仅有总格（`total_count_from_ref_count_prior`）：用总格/地图/已知桶 tighter 估 center 或延迟计算至 `200017` 到达；data7 第二大慢源；**勿**简单降 `max_combos`（项目已证会价格偏置）。
     2. 有总件数 + 金均格（`avg_cells.q5`）：快路径仍 ~3–4s；可优化 `_prior_count_values` 均格/均价过滤枚举范围。
     3. 多档总格同时出现（紫+金）：评估 prior + 硬约束替代全嵌套枚举（需负例集）。
     4. UI summary worker：忙时跳过新 snapshot → 改为 cancel/coalesce 只算最新帧；R1 证据不足时可显示「等待总件数」再跑 ref。
   - **准确度 / 显示（已有条目，仍 deferred）**
     - §46 mini UI 顶部倒三角缩放联动字体（`$product-ui-polish` + 430×320 visual QA）。
     - §48 紫局（q4）均价+均格不唯一时 ranking 软收窄（`purple_avg_value_cells_rank_v0`）。
   - **底层 / 运维**
     - WinDivert 被火绒 / 360 / Defender 删驱动或 exe、误报内核钩子：**当前最大 UX 阻塞**（§33 data2、§45 群友反馈、§56 迁移规划）。短期仅有信任区 + 管理员 + `capture_source_status.error_code` 诊断文案；**中长期必须换底层抓包架构，不再以 WinDivert 为默认 live 路径**。
     - 开发脚本 `start_ahmad_live.ps1` 默认 `engineering` 连续 jsonl：打包版 `portable` 已够用；非主因。
   - **诊断工具**
     - `tools\_audit_data7_perf.py`：回放 `archive/reset` 前几轮窗口，对比 old/new sparse 路由与耗时（本地 audit，不进包）。
   - **建议发版顺序**
     1. **v0.1.6-hotfix2.1**（§49，性能 bugfix）；
     2. 下一 minor：§50 性能项 (1) + UI worker；
     3. 再后：§46 / §48 产品向优化；
     4. **新道具 shadow prior 试点**（§51，活动地图 gated MC overlay）；
     5. **capture 后端迁移**（§56，与 ref 功能批解耦；优先级随火绒/360 反馈上调）。

51. 2026-06-12 规划：0611 五个新道具 + shadow 似然估计可行性（未应用）
   - **五个新道具（v308 Item.txt 已有，Drop.txt 无 leaf 权重）**
     - `1016007` 决赛指定用球，q6，4 格，758000；
     - `1036006` 世界冠军奖杯，q6，6 格，7202026；
     - `1036007` “退钱”手举牌，q6，12 格，555555；
     - `1036008` 传奇球星签名球衣，q6，6 格，1225000；
     - `1076007` 土豆服务器，q6，6 格，990000（**不在** `activity_des_10007` 文案边）。
   - **已有工作（§28–29，未接入 live）**
     - 脚本 `scripts\build_activity_shadow_prior.py` → `data\processed\activity_drop_shadow_prior.json`；
     - 方法 `q6_log_value_weight_plus_similarity_v0`：正式 q6 物品上拟合 `log(value)→log(weight)`，再与**同品质/同 tag/相近占格与价值**邻居 median weight 几何融合；
     - 活动边界来自 `activity_des_10007`（废弃仓库 / 航运集装箱 / 高阶活动场景）；
     - 当前估计 leaf weight（audit only）：2721 / 175 / 2640 / 1426 / 2423；confidence 自 `very_low` 到 `medium_low`；
     - `impact_guard.formal_use_allowed=false`；五个 target **不在** `items_droppable.json` 与任意地图 `flatten_pool()` 正式 prior；正例 `1012005` 足球仍在正式 prior。
   - **分路径现状**
     | 路径 | 新道具是否需要爆率 | 当前状态 |
     |------|-------------------|----------|
     | 结算 / 显式 item_id 查价 | 否，只需 Item.txt | ✅ v308 表已支持（如 `1036007` 结算差 555555 已证实） |
     | Hero Ref ref_v0 预出价 |  mostly 否 | 用 nest 均价 + 品质 tier prob，**不按单道具 drop 采样**；揭示具体物品时走 Item 价/下界 |
     | v3 MC / monitor layout posterior | 是 | ❌ 五个 item 不在 formal map prior；活动图 MC 低估含新红的布局概率 |
   - **可行性结论**
     - **可以做的（推荐分阶段）**
       1. **Shadow overlay（MC only，活动地图 gated）**：仅在 `2521–2530` / 对应 activity 地图族，把 shadow weight 作为**额外 leaf** 注入 `flatten_pool` overlay；默认 `shadow_only` flag，snapshot 写 `activity_shadow_prior_applied` note；**禁止**写入全局 `items_droppable.json`。
       2. **Audit / replay 对照**：用已有 fatbeans + 群友 settlement 样本，比较「无 overlay / 有 overlay」对 q6 尾部与总值的 P50 偏差；以 settlement 为 truth，不以 shadow 自证。
       3. **Hero Ref 侧（低优先）**：若公开揭示已带 `item_id`，确认 `_public_quality_reveal_floors` 等路径已用 Item.txt 精确价值；一般**不需** shadow drop rate。
     - **暂不建议直接 promotion 的**
       - 把 shadow weight 合入正式 `items_droppable` 或默认 live bid（无官方 Drop 来源）；
       - 对非活动地图启用（尤其 `1076007` 无活动文案边）；
       - 用 shadow 通过 formal drop-rate validation（guard 已禁）。
   - **主要风险 / 阻塞**
     - 本地仍缺活动 Drop pools `2521–2530`（BidMap 有、Drop 无）；shadow 是**估计**不是表逆向实锤；
     - `1036006` 价值极高且 confidence=`low_value_extrapolation`，即使 weight share ~2.5% 也会拉动高阶场景尾部；
     - `1036007` confidence=`very_low`（同形邻居少）；
     - `1076007` 不应按世界杯活动边发放。
   - **建议实现顺序（下一专题，版本号待定）**
     1. 跑 `build_activity_shadow_prior.py`，冻结一版 shadow JSON + basis 明细进 audit 报告；
     2. 实现 `activity_map_shadow_overlay_v0`（monitor/basic_mc 读 overlay，feature flag）；
     3. 选 3–5 个含 `1036007`/新红的 settlement 样本做 replay gate：\|ΔP50\| 与 red tail 可接受再开 shadow live；
     4. 仍无官方表前，Hero Ref 打包继续依赖 Item.txt 结算价；MC overlay 与 ref_v0 解耦发布。
   - **状态：可行性 ✅（活动地图 shadow overlay）；正式 prior ❌（缺官方 Drop）。**

52. 2026-06-12 Maria skill pipeline（108 / maria）

   - **目标**：Maria 从仅 `public_info_200027` 扩展到 skill reveal：粗品（白/绿/蓝）件数 + 白/绿/蓝 tier 总价下界。
   - **代码**：
     - `src\bidking_lab\live\fatbeans.py`：`MARIA_HERO_ID=108`；`10010801` 粗品 reveal；`100108`→q1 白 tier value_sum（live 已见）；`10010802`/`10010803` 预留 q2/q3；
     - `src\bidking_lab\live\monitor.py`：artifact 含 `skill_reveal_rows` / `skill_reveals`；
     - `src\bidking_lab\runtime\snapshot.py`：minimap 从 skill reveals 取 marker；
     - `src\ahmad_ref_engine.py`：`_apply_maria_skill_evidence()` + `maria_skill_*` notes；
     - Tests：`test_live_fatbeans.py`、`test_live_monitor.py`、`test_ahmad_ref_engine_public_info.py`。
   - **边界**：`public_info_200027` 仍是公开摇号，与 `maria_skill_*` 分开；绿/蓝 skill id 待 R1 导出确认。
   - **验证**：聚焦 pytest 98+ passed；`start_ahmad_live.ps1` replay Maria export。

53. 2026-06-12 金均格 0 / UI 仍显示非零 — 机制与 recordings 审计（未修）

   - **反馈**：均格/均价/件/格 = 0 时 UI 仍非零；手动填表有时无效。
   - **SEND-only 无 REV**：金均格界面 0 常表示 SEND `100113` 无 REV `0x0027`；`monitor._action_result_rows` inferred_zero 需同 session 后续 state（§24）；仅 SEND 或无 later state → 不推断 0 → prior 残留（如金件 0/1/1）。
   - **手动路径（调查）**：未「应用并启用」仍走 live；`q4q5_count` 与显式 q5/q6=0 可 `no_reachable_combo`；`_red_display_ranges` complement pairing。
   - **recordings 审计**（`Desktop\recordings\...\reset`，125 局）：0 次 `100113`/`100114` SEND；0 显式 gold-zero evidence；4 局 bidding；不能验收「zero 已进 engine 仍错」。
   - **样本索引**：`docs\hero_ref_settlement_sample_index_2026-06-11.zh-CN.md` §8；handoff：`handoff_2026-06-12.zh-CN.md`。
   - **临时 audit 脚本**：已删，结论已归档。

54. 待分批风险点（本 checkpoint 后，按批实施）

   | 批 | 项 | 说明 |
   |---|---|---|
   | A | inferred_zero 时序 | SEND-only 无 REV 是否推断 0 或 UI「推断 0 待确认」 |
   | B | 手动 UX | 已填未应用 banner；q4q5_count 与 zero 行 reconcile |
   | C | public avg fallback | `200013–200016` 缺失时是否走 `public_info_rows` |
   | D | 展示 pairing | q6 锁 `[0,0,0]` 时跳过 red complement |
   | E | 底层抓包架构 | WinDivert → 新 capture 后端（§56）；与 A–D 解耦，单独里程碑 |

   - 每批需：样本 session + 期望 UI 行，再改 monitor/engine/UI 单层，避免三处漂移。
   - **E 批**需：新后端能复用现有 `parse_fatbeans_capture` / jsonl artifact 契约，且保留 raw 回放能力。

55. 2026-06-12 聊天记录落地核实表（checkpoint `32f4bb3` 基线）

   对照近期会话与 git，便于 diff / 成果追踪。**已记录** = EXECUTION_NOTES 或 handoff 已有正文；**本表补录** = 此前代码已入库但笔记缺条。

   | 主题 | 落地 | Git / 文件 | 文档 | 备注 |
   |------|------|------------|------|------|
   | data6 公开大红价值下界 | ✅ | §43 → hotfix 包 | §43–§44 | `quality_value_floors` / `quality_cell_floors` |
   | 红件 `3/?/?` 显示 | ✅ | `3cebdc2` → `32f4bb3` | §45 | `_red_range_text`，锁定三元组不折叠 |
   | 公开精确 `200009–200020` + 金总格 0 | ✅ | `3cebdc2` | §45 | `200011=0` → q5 件格归零链 |
   | live ref 显示均格 `2.09×11→23` | ✅ | `3cebdc2` → `32f4bb3` | §45 | `_avg_grid_options` display 截断兜底 |
   | WinDivert 被删诊断文案 | ✅ | §33 前后 | §33、§45 | `error_code` + mini 提示 |
   | monitor 随 UI 退出 | ✅ | `dcb1bd1` | §47 | `monitor.lock` fallback |
   | hotfix2.1 金总格 sparse 性能 | ✅ | `f9fca54` 链 | §49 | 单档金总格仍走 sparse prior |
   | **16 英雄识别 + generic ref** | ✅ | `32f4bb3` `ahmad_ref_engine.py` | **本表补录** | 非 Aisha/Ahmed/Victor 走 nest-tier + `generic_ref_hero` |
   | **公开最高品质 200048 → q6=0** | ✅ | `32f4bb3` | **本表补录** | 对齐 v2 `public_max_quality`；冲突 `hard_conflict` |
   | Maria skill 粗品 + 白 tier 价值 | ✅ | `32f4bb3` | §52 | `10010801` 粗 location 无轮廓；`100108`→q1；200027≠Maria skill |
   | Maria 绿/蓝 skill id | ❌ | — | §52 | `10010802/03` 待 R1 导出 |
   | **拉文 R5 全品质** | ❌ 低优先级 | — | **§59** | 用户确认暂缓；待 `100301` + 样本 |
   | 金均格 0 / SEND-no-REV | 调查 | — | §53、sample §8 | 行为未改；§54 A–D 待批 |
   | mini UI 缩放联动字体 | ✅ | 工作树 | §46 | resize 松手后 scale 字体/间距/小地图 |
   | 紫局均价+均格 ranking | ❌ | — | §48 | 规划 only |
   | 底层非 WinDivert 抓包 | ❌ | — | §56 | 规划 only；用户 06-12 明确要求列入计划 |
   | 桌面包 hotfix 副本（未重打包 exe） | 部分 | Desktop hotfix 目录 | §44–§45 | 源码已 push；exe 需重打包才生效 |
   | **至宝估价 minimap + 未知品质条纹** | ✅ | 工作树 | **§57–§58** | 加布里 live 验收；**未 commit** |
   | **吴起灵 10002071 轮廓 footprint** | ✅ | `snapshot.py` | §57 | 斜条纹未知品质 |
   | **索菲 100163 → ref q6 锁 0** | ✅ | `ahmad_ref_engine.py` | §57 | merged Q5 skill quality |

   - **追踪约定**：后续每批合并前更新本表「文档」列与 commit；handoff 只写增量，本表作总索引。
   - **补录细节（16 英雄 + 200048）**
     - `HERO_BY_ID` / `HERO_ALIASES` 对齐 `fatbeans._HERO_MODE_BY_ID`（101–110、201–209、301）；
     - `SUPPORTED_REF_HERO_KEYS`：structured 三英雄逻辑保留，其余 `generic_ref_hero` + 通用 nest-tier；
     - `_extract_public_max_quality` + `_apply_public_max_quality_ceiling`：`200048` 或 Isabella `100110` 揭示最高品质 ≤5 → `fixed_counts.q6=0`；
     - 测试：`test_ref_engine_generic_hero_runs_reference_engine`、`test_ref_engine_public_max_quality_gold_locks_q6_to_zero`、`test_ref_engine_public_max_quality_conflicts_with_existing_red_count`。

56. 2026-06-12 规划：底层抓包架构迁移（WinDivert 退场）

   - **问题（已确认，非偶发）**
     - 当前 live 默认：`scripts\run_windivert_live_monitor.py` + pydivert + 包内 WinDivert 驱动/exe。
     - 火绒、360、Windows Defender 等常**直接删除** WinDivert 组件或拦截内核驱动加载；用户侧表现为 `FileNotFoundError` / `PermissionError` on open、`raw_packets=0`、monitor 秒退。
     - 已有短期缓解（§33、§45）：`capture_source_status.json` 写 `error_code` / `error_hint`；mini UI 提示「检查防火墙/安全软件」；包内 `火绒拦截说明.txt`。**不能**从根上消除误杀与信任成本。
   - **方向（用户确认）**
     - **后续版本不再以 WinDivert 为默认 live 抓包方案**；WinDivert 路径保留为 replay / 工程调试 / 兼容旧样本，直至迁移完成。
   - **约束（迁移时必须满足）**
     1. **下游契约不变**：仍产出 Fatbeans JSONL / reset artifact → `parse_fatbeans_capture` → `build_monitor_artifact_from_events` → snapshot / ref / UI；避免 ref 引擎与 UI 再改一遍。
     2. **回放兼容**：现有 `windivert_live_*.jsonl` / reset 样本继续可复放（§28–29、sample index）。
     3. **权限与部署**：新方案需明确 UAC/驱动/用户态代理取舍；文档与安装步骤比 WinDivert 更简单或同等可教。
     4. **双轨期**：feature flag `capture_backend=windivert|…`，便于 A/B 与回归；默认逐步切到新后端。
   - **候选方向（待选型，本笔记不定案）**
     - 游戏/平台官方或半官方 API、已有进程内 hook（若合规且稳定）；
     - 用户态代理 / 本地 relay（避免内核驱动签名问题）；
     - 其他 OS 级 capture 框架（需评估与现有 port-only / flow 过滤等价能力）。
     - **非目标**：继续堆「加白名单教程」当作长期方案。
   - **建议里程碑**
     1. **设计稿**：新 backend 接口 + 与 `run_windivert_live_monitor` 等价的状态字段（`capture_source_status` 语义对齐）。
     2. **Shadow 并行**：engineering 模式双写 jsonl，对比 frame 覆盖率与 parse 成功率（不要求用户换包）。
     3. **默认切换**：新包默认新 backend；WinDivert 降为 optional / dev-only。
     4. **文档**：替换 `火绒拦截说明` 为主流程说明；EXECUTION_NOTES 标记 WinDivert 为 legacy。
   - **与 §54 关系**：属 **E 批**，与金均格 0 / 手动 UX 等 ref 逻辑分批独立；优先在「用户无法启动 monitor」类反馈多时提前 E 的设计阶段。

57. 2026-06-12 小地图 / 至宝估价 / 未知品质显示（live UI 批次，**工作树未 commit**）

   - **用户反馈链**
     - 索菲 / 塔蒂安娜 / 加布里：R3–R4 使用 **至宝估价 `100163`** 后，小地图看不见 marker；要求按 **抽检 footprint** 展示，价格只在 **悬浮 tooltip** 显示。
     - 吴起灵：技能 **10002071** 古董轮廓「有显示但太黑」；要求 **未知品质** 用 **斜条纹方块**，不要一片 `#172033`。
     - 2026-06-12 晚：**加布里 live 验收通过**（「显示也非常棒」）。

   - **根因（已确认）**
     1. **Panel 路径**：`_minimap_summary` 在 contract 未 `available` 时退回 `minimap_grid_items`；value-only 行无 row/col 被 skip。
     2. **Contract 路径**：`_ui_minimap_quality_markers` 对 `100163` 单独 marker，且 `local_index`/`runtime_id` 已在 grid 占位时被 skip；local 与 anchor 不一致（塔蒂安娜 local 8 vs settlement anchor 7）。
     3. **Tk 绘制**：未知品质 `MAINLINE_QUALITY_STYLE["unknown"]` 误设 `"unknown": False`，斜条纹逻辑从未触发；曾短暂在格子上画常驻 `display_label`，用户认为「脏」。
     4. **Shape-only skill**：`shape_key` 存在时仍发 `render_mode=marker` + 1×1，吴起灵古董轮廓缩成小黑点。

   - **落地（源码，见 git diff）**

     | 层 | 文件 | 行为 |
     | --- | --- | --- |
     | Parse / grid | `fatbeans.py` | 重复 `runtime_id` 合并 **value**；value-only 默认 `shape_key=11` |
     | Artifact | `monitor.py` | minimap 行统一 `render_mode=footprint`；`display_label` 留空（tooltip 用语义字段） |
     | Contract | `snapshot.py` | `_apply_treasure_value_reveals()`：`100163` 按 **runtime_id 优先** 升级 footprint；带 `shape_key` 的 marker 按真实宽高 footprint；`100163` 不再走 quality_marker 重复路径 |
     | Panel | `ahmad_live_panel_server.py` | value-only → shape 11 + footprint；contract items 优先；`local_index→row/col` 回退 |
     | Tk | `ahmad_tk_overlay.py` | 去掉格子常驻文字；未知品质 **浅底 + 斜条纹**（`unknown: True`）；未知 marker 浅底 |
     | Ref | `ahmad_ref_engine.py` | `TREASURE_HIGHEST_ITEM_VALUE_ACTION_IDS={100163}`；合并 skill/action 品质后 `public_max_quality_ceiling` → 索菲局 q6 锁 0 |

   - **至宝估价 UI 契约（现行）**
     - Action id：**`100163`**（不是 `100168`）。
     - Live：在对应格画 **与抽检相同的 footprint 色块**（有 shape 则真实轮廓）；**不在格子上画价格字**。
     - Hover：`tooltip` 含 `至宝估价 / {价值} / local {n}`；contract 可保留 `display_label` 供 panel 格式化，Tk 不渲染。
     - 结算：settlement footprint 覆盖 transient value；同一 `runtime_id` 保留 Q6 色 + tooltip 价值（加布里验收样例）。

   - **加布里验收样本（latest_snapshot / 用户刚导出）**

     | 项 | 值 |
     | --- | --- |
     | session | `2402:1425860548836801` |
     | hero / map | gabriela / 2402 设计师居所 |
     | 至宝估价 | sort **19** send / **20** result；local **25**；value **71,500** |
     | 结算对照 | Q6 **大溪地黑珍珠** @ local 25（`runtime_id=1425860548836826`） |
     | settlement truth | 40 件 / 117 格；q6=**3**；ref `q6=[3,3,3]`、`red=[3,3,3]` |
     | minimap | row 3 col 6；Q6 footprint；tooltip 含至宝估价与 71,500 |
     | 说明 | 至宝揭示的是 **最高品质档内一件** 的价值（71,500），非 session 最高价（531,000 高斯振动匕首） |

   - **其它 live 回归样本（同批修复，见 sample index §11）**
     - 索菲 `2401:1425860545985228` — R3 85623 → Q6 黄金水龙头；q6 不锁 0
     - 塔蒂安娜 `2409:1425860547014998` — R4 29700 → Q5 浪漫主义风景素描（runtime 合并）
     - 吴起灵 `2409:1425860547799228` — 10002071 古董斜条纹 footprint

   - **测试（本批新增/更新）**
     - `test_ui_contract_minimap_shows_treasure_value_action_without_quality`
     - `test_ui_contract_treasure_value_merges_onto_existing_runtime_footprint`
     - `test_treasure_value_action_result_adds_value_only_grid_marker`
     - `test_ref_engine_treasure_value_action_locks_q6_when_merged_quality_is_q5`
     - `test_ahmad_tk_minimap_unknown_footprint_uses_stripes_without_permanent_text`

   - **验证命令**

     ```powershell
     cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
     python -m pytest tests/test_runtime_snapshot.py tests/test_live_fatbeans.py tests/test_live_overlay.py -q -k "minimap or treasure"
     ```

   - **仍缺 / 未做**
     - Hero Ref **zip 归档** 加布里 session（用户 export 在 `data/logs/live/exports/`，待 `organize_hero_ref_samples.py --apply`）
     - 加布里 / 塔蒂安娜 **ref 特化**（仍 `generic_ref_hero`；仅 parse + minimap 完整）
     - 吴起灵 R1 **`100207`** 数值 skill → category count（P0 样本缺口，见 §11）
     - 桌面包 **重打包** 后上述 UI 才进 exe

58. §55 增量（2026-06-12 晚，小地图批次 — 补 §57 一行对照）

   | 主题 | 落地 | 文件 | 文档 | 备注 |
   | --- | --- | --- | --- | --- |
   | 至宝估价 minimap footprint | ✅ | snapshot/monitor/panel/tk | §57 | `100163`；tooltip-only 价格 |
   | 未知品质斜条纹 | ✅ | `ahmad_tk_overlay.py` | §57 | 修复 `unknown: False` bug |
   | 吴起灵 shape 轮廓 footprint | ✅ | `snapshot.py` | §57 | `10002071` 等 shape_key 宽高 |
   | 至宝 ref q6 ceiling（索菲） | ✅ | `ahmad_ref_engine.py` | §57 | merged Q5 → q6=0 |
   | 加布里 live 验收 | ✅ | latest_snapshot | §57、sample §11 | 用户确认 UI OK |
   | Hero pool ref 特化（加布里等） | ❌ | — | §11 | 待样本 + bridge |
   | Wuqilin `100207` count | ❌ | — | §11 | 待 R1 样本 |
   - **状态：规划 ✅；选型与实现 ❌（待专题）。**

59. 2026-06-12 伊森样本库审计 + 支线接入 +  backlog（工作树）

   - **样本库规模（Fatbeans JSON，2026-06-12 扫库）**
     - 路径：`data/samples/fatbeans/` + `data/samples/fatbeans_activity_20260605_shipwreck/`
     - **166** 份 `*ethan*.json`；**166/166** `parse_fatbeans_capture` 通过
     - 地图 Top：`2401×30`、`2501×28`、`2601×11`、`2502×9`、`2508×9` …
     - 文件名轮次：`1r×10`、`2r×20`、`3r×48`、`4r×50`、`5r×38`
   - **技能树事件统计（全库累计）**
     - `1002081` R1 类别轮廓：**746** 次；观测 item `quality=None`，件数 **5–41**（中位 **22**）→ 符合「5 类抽样、非全库」
     - `1002082/3/4` R2–R4 已知品质轮廓：**325 / 259 / 145**
     - `1002085` R5 全仓轮廓：**76** 次（≈ 五轮局）
   - **预结算 warehouse 精确 pin（`warehouse_total_cells` + `total_item_count`）**
     - **123/166** 无 pin（R1–R4 局部轮廓，符合设计）
     - **37/166** 由 **R5 `1002085`** pin
     - **5/166** 由 **明镜 `100134` + R2–R4 join** pin（package13 类）
     - **1/166** 其它路径（待单样本复核）
   - **Hero Ref 支线本次接入（源码，见 diff）**
     | 层 | 行为 |
     | --- | --- |
     | `monitor.py` | 伊森/艾莎/艾哈迈德/维克托/加布里/拉文 **技能标签**（不再 `技能 100208x`） |
     | `fatbeans.py` | R2–R4 **仅合并已知品质 runtime** 的 Ethan 轮廓 |
     | `ahmad_ref_engine.py` | `_apply_ethan_skill_evidence`：R5 / mirror join → **硬总格+总件**；R1 → **`ethan_skill_r1_outline:N:M` 软 note** |
     | `ahmad_live_panel_server.py` | 技能 minimap 来源显示 **「英雄技能」** |
     - 样本回放：`ref_r1_note` **166/166**；`ethan_skill_full_outline_*` **42/166**（R5 + mirror 子集）
     - 仍 **generic_ref_hero**（无 structured bridge）；总件/总格靠 skill evidence + 公开信息，不靠 Aisha/Ahmed 式 bucket bridge
   - **未知轮廓显示（样本侧观察）**
     - R1 纯 shape：`quality=None` → 斜条纹 footprint + tooltip「品质? + 轮廓 NxM」✅
     - 品质 join 后（宝光/明镜/公开）：末 batch unknown grid **中位 0**（median），max 1 ✅
     - **未做**：R1 五类集合 → 类别 label（游戏 hover 也不给类名；需 item→category + R1 类集推断）
   - **测试**
     - `test_skill_reveal_rows_label_ethan_and_aisha_skills`
     - `test_fatbeans_ethan_r2_outline_skips_items_without_known_quality`
     - `test_ref_engine_ethan_full_outline_skill_sets_total_grid_target`
     - `test_ref_engine_ethan_r1_outline_is_diagnostic_only`
   - **Backlog / 计划（优先级）**
     | 项 | 优先级 | 说明 |
     | --- | --- | --- |
     | **明红 partial 红值下界** | P1 | §43 延伸；已知 1 红 + 未知 1 红（武夷山类）|
     | **艾莎格子估计** | P1 | 主线已有 layout 证据；Hero Ref 特化 **暂缓** |
     | **伊森 R1 类别 soft 约束** | P2 | 166 样本可 replay；需 item 表 category + R1 类集 |
     | **伊森 structured ref bridge** | P3 | 可选；当前 generic + skill evidence 已覆盖 R5 总格 |
     | **拉文 R5 全品质 `100301`** | **低** | 用户确认 **暂缓**；仅 hero alias，待样本 + skill pipeline |
     | 加布里/塔蒂安娜 ref 特化 | P3 | minimap 完整，ref generic |
     | 底层抓包迁移 | E 批 | §56 |
   - **代表样本（可复放）**
     - R1 未知轮廓 + 公共紫桶：`fatbeans_valid_ethan_2401_*`（package10 同类）
     - R5 全仓 pin：`fatbeans_valid_ethan_2401_5rounds_*` / `fatbeans_mixed_ethan_*_5rounds_*`
     - 明镜 join：`bidking_package13_eye_of_clarity_ethan.json`（若本地有 package 副本）
     - 沉船活动：`fatbeans_activity_20260605_shipwreck/fatbeans_valid_ethan_2529_5rounds_*`
   - **状态**：样本审计 ✅；伊森支线基础接入 ✅（工作树）；zip/桌面包 **未重打**

   - **明红 partial 红值下界（P1，工作树）— 验证状态 2026-06-12**
     - **已实现**：`quality_value_floor_item_counts` + `_partial_known_quality_value_state()`；硬下界 = 已知 value + 未知件×默认单价；中心 = 已知 + 剩余格 grid 估计
     - **单元测试**：`test_ref_engine_partial_known_red_value_includes_unknown_estimate`（390k/1格/q6=2）；`test_ref_engine_partial_known_red_data6_style_above_known_not_flat`（452800/15格）
     - **合成回放**
       | 场景 | 修复前（用户报） | 当前 `red_value_range` |
       | --- | --- | --- |
       | 390k 武夷山 / q6=2 | 390k / 390k / ~512k | **585k / 614k / 691k** |
       | data6 452800/15格 / q6=2 | 452k / 460k / 604k（§43 前更低） | **623k / 623k / 686k**（结算 q6 truth≈521k，rv50 **+19.6%**，偏保守下界） |
     - **真实 Fatbeans 样本**：全库 **0** 份 `info_id=200023` + 单件 q6 value + q6 件数>1 的 partial 局（用户 live 2408 R3 截图 **未入库**）；198 份 q6 value 多为 `200048/200050` 至宝/最高品质，语义不同
     - **审计脚本**：`scripts/audit_partial_red_and_ethan_r5_ref.py`
     - **跨英雄对照表（2026-06-12，audit 扩展）**
       - 命令：`python scripts/audit_partial_red_and_ethan_r5_ref.py`（可选 `--skip-ethan` / `--no-report-file`）
       - 报告：`data/reports/audit_cross_hero_q6_value.txt`
       - 扫描 **43** 份公开 q6 value（Aisha 21 / Ethan 14 / Ahmed 3 / 其它 5）；形态 **single_no_lock 41**、**full_known 2**、**partial 0**
       - rv10 > 已知最高价 **23/43**；`settle` 列仅 q6 件数/格数（fatbeans 结算 inventory 无 item value）
       - **决策**：当前 partial 红估实现 **先保留**（合成 390k + data6 可接受作保守下界）；分层 floor / 未知残差分布 **留待统一大优化**
     - **下一步**：收 live Ahmed partial 样本入库（2408 R3 武夷山类）；大优化前用对照表作 baseline
     - **recordings 扫库（2026-06-12）**：`Desktop\recordings\data*` 共 **6** 份 reset/json 含公开 q6 value；**partial 仍 0**（引擎侧 q6_lock 未大于 known_count）。**不可用**：390k 武夷山 partial（库内无 ref 语义 partial 局）
     - **data6 fatbeans 入库（2026-06-12）**：源 `Desktop\recordings\data6\logs\live\raw\windivert_live (1).jsonl`（38 行，单 session `2309:1425860479021171`）→ `data\samples\fatbeans\fatbeans_valid_ahmed_2309_5rounds_2309_1425860479021171_0001.json`（`organize_fatbeans_real_samples.py --apply`）。R5 bidding 复放：200023 民用垂直起降 452800/15 格 → `quality_value_floors.q6=452800`；红值 **623146 / 623146 / 686310**（结算 q6=2/16，truth value≈521k，rv50 +19.6% 保守下界）
     - **UI 推理速率（§50-4，工作树）**：`ahmad_tk_overlay.py` summary worker **coalesce** — 忙时缓存最新 snapshot，当前 worker 结束后只算最新帧；丢弃过期 seq 结果、同 signature 不重复 pending（测：`test_ahmad_refresh_coalesces_summary_worker_to_latest_snapshot` 等）
     - **R1 总件数延迟重算（§50-1，工作树）**：`ahmad_ref_engine.py` 在 **仅总格、无总件** 且其它约束不足时返回 `missing_total_count` + `waiting_total_count:grid_only`，UI 显示 **「等待总件数」**；`200017` / skill 精确总件 / Aisha 多品质约束 / Victor min_count 等路径 **不延迟**
     - **伊森 R5 generic ref 抽检（3+3 样本）**：`ethan_skill_full_outline_*` → `grid_target` 与结算 **cells 100% 一致**；总报价暂无 Item 表 truth 对比

60. 2026-06-12 §50 性能 checkpoint + **暂缓继续优化**（commit `a0135c7` @ `origin/main`）

   - **本版已落地**
     | 项 | 行为 | 验证 |
     | --- | --- | --- |
     | §50-1 | Ahmed **仅总格** → `missing_total_count` + `waiting_total_count:grid_only`；Aisha 多品质约束 **不延迟** | `test_ref_engine_*defers*` / `keeps_aisha_grid_prior*` |
     | §50-2 | 精确总件 + `avg_cells` 微优化（均格剪枝 + 默认格快路径）；notes `exact_total_avg_cells_fast_path` | Ahmed r2 fatbeans：`combo_count`+`balanced` 锁定；warm **<500ms** |
     | §50-4 | summary worker **coalesce** 只算最新 snapshot | `test_ahmad_refresh_coalesces_summary_worker*` |
     | Aisha UI | `_aisha_next_info_hint`：蓝→紫→金→总格→最后补总件；R1 不催白绿 | `test_ahmad_server_aisha_*` |
     | Audit | `scripts/audit_data7_perf.py` + `exact_total_avg_cells_fast_path` 路由 | `data/reports/audit_data7_perf.txt`（本地，不进 git） |

   - **Ahmed audit（`--hero ahmed --max-round 2`，`a0135c7` 后复跑）**
     | 路由 | n | avg | p95 | 备注 |
     | --- | ---: | ---: | ---: | --- |
     | `sparse_exact_prior` | 32 | ~601ms | ~1.48s | R1 仍跑 prior 的样本；最慢 ~2.6s |
     | `exact_total_avg_cells_fast_path` | 17 | ~235ms | ~1.32ms | 含冷启动；同路径 **warm ~37–97ms** |
     | §50-2 回归样本 r2 | 2 | 冷 ~1.3–1.4s | — | 热跑已 <500ms |

   - **体验结论（用户 2026-06-12 确认）**
     - **Ahmed 主 live 路径（R2+ 有总件 + 均格）**：速度 **可接受**，不必为发版继续抠 §50-2。
     - **仍慢但非阻塞**：R1 `sparse_exact_prior`（avg ~0.6s，p95 ~1.5s）；Ethan generic ref **仍搁置**。
     - **精度硬约束（后续任何 perf 仍遵守）**：不改 `max_combos` 换速度；每条优化至少绑 fatbeans `balanced` + `combo_count` 回归。

   - **暂缓项（需要时再开）**
     1. `sparse_exact_prior` 枚举范围收紧（Ahmed R1 p95 目标 ~800ms 量级）
     2. Aisha 2407 类 `count_prior` 极端慢（~100s / 3.6 万 combo，见 §49）— 与 §61 艾莎批交叉
     3. §50-3 多档 `quality_cells` 混合 prior
     4. evidence/session 缓存
     5. §48 紫品 ranking、Ethan perf

   - **诊断命令**
     ```powershell
     cd bidking-lab
     python scripts/audit_data7_perf.py --max-round 2 --hero ahmed
     python -m pytest tests/test_ahmad_ref_engine_public_info.py -k "exact_total_q5_avg_cells_fast_path" -q
     ```

61. 2026-06-12 规划：**艾莎（Aisha）体验 + 准确度适配** — 逐步扩大 Hero Ref 适用范围

   - **目标**：在 **不牺牲已验证精度** 的前提下，让艾莎局从「能跑 ref」升级到「群友日常可用」——覆盖更多地图/轮次/工具组合，UI 提示与引擎结论一致。
   - **Git 基线**：`a0135c7`；艾莎 fatbeans 样本库 **~249** 份（含 `fatbeans_activity_20260605_shipwreck` 活动图）。
   - **精度门禁（每批必做）**
     - 新增/改动引擎逻辑：至少 **1 条真实 fatbeans 端到端** + 结算 truth（`final_quality_counts` / `final_quality_cells` / 总价若可得）对照；
     - 白绿 split：保持现有 `split_*` 单元测试 + 不引入 silent 补数；
     - public avg 冲突：仍走 `public_quality_avg_value_conflict_fallback`，notes 必须可见。

   - **群友反馈 ↔ 状态（艾莎相关）**
     | 反馈 | 状态 | 文档/测试 |
     | --- | --- | --- |
     | 下一步提示顺序（蓝→紫→金→总格→总件；R1 不催白绿） | ✅ `a0135c7` | `test_ahmad_server_aisha_*` |
     | 金均格显示截断（2.09 / 1.80 / 2.90） | ✅ 引擎 display avg fallback | `CAPTURE_AVG_CELL_FIXTURES` |
     | 金/品质总格 = 0 仍显示先验 | ✅ `200010–200020` + `quality_cells=0→fixed_counts=0` | hotfix2 回归 |
     | public 紫均价过硬 → 无价/ no-combo | ✅ downgrade 重跑 | `0052` 样本路径；需 **批量 replay 确认** |
     | R1 英雄显示 `?` 第二轮才识别 | ⏳ 待查 monitor hero detect | §61-B |
     | 仅 SEND 无 REV → 0 值不进 engine | ⏳ 跨英雄 §54-A | 非艾莎独有 |
     | 艾莎 R1 仅总格 + 多品质已锁 → 仍慢 count_prior | ⏳ §61-D | `keeps_aisha_grid_prior*` 有意不 defer |
     | Hero Ref 格子/layout 特化 | ⏳ 低优先 | v3 主线有 layout；§59 backlog |

   - **已有引擎能力（艾莎 structured ref）**
     - `split_counts` / `split_quality_cells` 白绿拆分、互补、与 merged q1 折叠；
     - 总件残差派生 q1、map grid floor、`split_low_quality_*` 硬冲突诊断；
     - 与 Ahmed 共用 public 精确字段、display avg、sparse prior 路由；
     - **不共用** Ahmed `100204` bridge；艾莎靠 structured inputs + public_info + split 管道。

   - **分批计划（建议顺序）**

     **批 A — 基线审计（只读，1–2 天）**
     - 脚本：扩展 `audit_data7_perf.py` 或新增 `audit_aisha_fatbeans.py` — 对 **艾莎** 样本按轮次回放 ref，统计 `status` / route / `balanced` / 结算 Δ；
     - 分层：常规图 240x / 活动 252x / mixed；标记 `no_reachable_combo`、`count_prior` 慢样本、`public_*_downgraded`；
     - 产出：`data/reports/audit_aisha_baseline.txt` + 5–10 条 **代表样本** 写入 sample index（新 §12 艾莎）。

     **批 B — 准确度（P1，样本驱动）**
     1. **public 紫/金均价 + 均格不唯一**：§48 `purple_avg_value_cells_rank_v0` 软收窄（艾莎 21 份 q6 value audit 已示多样本形态）；
     2. **0052 类 fallback 回归**：锁定 `fatbeans_valid_aisha_2402_*_0052.json` r3 `balanced` / ranges 不回归；
     3. **白绿 live bridge**：核对 `monitor._ahmad_ref_inputs_from_batches(hero=aisha)` 是否漏掉 action/public 白绿字段；补 structured 映射 + fatbeans 复放；
     4. **活动地图 2521–2530**：用 `fatbeans_activity_20260605_shipwreck` 子集做 settlement gate（件/格 truth）。

     **批 C — 体验（P1，UI + 提示）**
     1. R1 hero `?` → 尽早显示 `aisha`（monitor/snapshot context）；
     2. mini UI：艾莎局「未锁 白绿/蓝」摘要与 `_aisha_next_info_hint` 不矛盾（白绿仅在手填/已锁时展示，不主动催）；
     3. `missing_total_count` / `count_prior` 状态下候选行与「下一步」文案一致；
     4. §46 字体缩放仍 **不做**，除非单独开 UI 专题。

     **批 D — 性能（P2，仅当群友仍报卡）**
     - 艾莎 **多品质已锁、无总件** 的 `count_prior`：tighter center（总格残差 + split + 已知 q3–q5），**禁止**降 `max_combos`；
     - 与 §60 暂缓项 (2) 合并实施；样本：`2407_*` 极端局 + 常规 2410 多品质 R1。

     **批 E — 扩大适用范围（P2–P3）**
     - 地图：2401–2410 已有多样本；补 **250x 新图** 与活动图混局；
     - 轮次：R1–R5 分轮验收（R1 提示 / R4–R5 高品+红）；
     - 与 v3 layout 证据 **不合并** ref_v0，除非样本证明 split+public 不足。

   - **明确不做（本专题）**
     - Ethan / 加布里 structured bridge；
     - WinDivert → 新抓包（§56，独立 E 批）；
     - 为提速牺牲 combo 空间或 silent 改 balanced。

   - **下一动作（用户 2026-06-12）**：**暂停 §50 后续 perf**；**启动 §61 批 A** — 艾莎 fatbeans 基线 audit + 代表样本表，再与群友对齐优先级（准确度 vs 提示 vs 新地图）。

   - **样本筛选原则（用户 2026-06-12，批 A 必守）**
     | 纳入 | 排除 |
     | --- | --- |
     | `rounds ≥ 3` 且文件名/ live 一致 | 仅 1–2 轮对局 |
     | 有 settlement inventory | 无结算 / parse 失败 |
     | audit 轮证据分 ≥ 4（总件/总格/多档品质） | `missing_total_count` / `no_reachable_combo` |
     | 常规图 + 活动图 **分 cohort 报告** | 不混 tail 进主结论 |
     | — | q6 结算 value > 1.2M 或 q6 件数 > 4（高长尾） |
     - **不全库 audit**：244 扫描 → **173  curated**（脚本默认）；代表样本再人工缩至 15–25 条进 sample index §12。
     - 工具：`scripts/audit_aisha_gap.py` → `data/reports/audit_aisha_gap.txt`（本地，不进 git）。

   - **批 A 初跑结论（173 curated，penultimate bidding round vs settlement）**
     | 维度 | 全 curated miss | 仅 `total_count` 已精确（n=15） | 解读 |
     | --- | ---: | ---: | --- |
     | 总件 | 91.9% | — | ** inflated**：大量仍 `count_prior`、尚无 `200017` |
     | **总格** | **69.4%** | **66.7%** | **最大结构性缺口**；avg mid-gap ≈ 18 格 |
     | 金件 q5 | 51.4% | 6.7% | 多数误差来自 **总件/总格 prior 未收束**，非金均格本身 |
     | 红件 q6 | 29.5% | 0% | 总件锁定后件数 band 尚可 |
     | 红值 q6 | 39.9% | 20.0% | 尾部与 partial 红值仍宽；绝对 gap 可达 ~1M |
     | 金/红 **格** | n/a | n/a | ref 很少锁 `quality_cells.q5/q6`；格数误差体现在 **总格 residual** |
     - **与用户直觉对齐**：**总格 > 红值 > 金件（prior 阶段）> 红件**；现行 v0 应优先 **总格收束 + 红值下界**，金件在总件/总格到位后误差下降。
     - **留给 v3/完全体**：品质桶、形状/layout、MC posterior；Hero Ref v0 只做 nest-tier + 公开/ split 证据，不 silent 扩 combo。

   - **批 B 优先修复方向（v0 范围内）**
     1. `count_prior` 下 **总格 target** 与已知 q3–q5 cells 残差对齐（艾莎多品质已锁仍宽格的主因）；
     2. 红值：`quality_value_floors` / partial 红已知件 + 公开 q6 value（已有 P1 partial，艾莎样本 partial≈0）；
     3. 金件：在 **总件+总格** 锁定后复测；均格 display fallback 已修，非主矛盾；
     4. 0052 / public avg downgrade 回归 + 白绿 live bridge（monitor → structured inputs）。

62. 2026-06-13 艾莎 gap audit 扩展 + 代表样本表（commit 待 `188c628` 之后）

   - **工具**：`scripts/audit_aisha_gap.py`（指标扩展、`--audit-round`、`--write-representative-doc`）
   - **代表样本**：`docs/hero_ref_aisha_representative_samples_2026-06-13.zh-CN.md`（20 条分层 + **15 条 exact total 回归门禁**）
   - **筛选不变**：244 扫 → 173 curated（penultimate）；不全库、去 tail / ≤2 轮 / 证据不足

   - **件数估计（用户 2026-06-13）— 确认为独立误差点**
     - 旧指标「仅 exact total band」→ 总件 miss **91.9%**（虚高）
     - 新指标「各 tier count band 求和 band」→ 总件 miss **50.3%**，avg mid-gap **~6 件**
     - `count_prior` 下 per-tier 求和仍常宽于 settlement；与 **总格 miss 69%** 同源（prior 未收束）
     - **q4 件 30%**、**q5 件 51%**（prior 阶段）；exact total 子集 q5 **6.7%**

   - **扩展指标（173 curated，penultimate）**
     | 指标 | miss | 备注 |
     | --- | ---: | --- |
     | total_cells | 69% | 仍 #1；cells_ranges 已纳入 |
     | q5_cells (band) | 49% | 金格 band 宽，不单列 locked cells |
     | q4_cells | 38% | 紫格 |
     | q6_value | 40% | 红值 tail |
     | q6_count | 30% | exact total 后 → 0% |
     | q3_count | 9% | 蓝件相对准 |
     | q1_count | 100% | **白绿 split vs merged q1** 口径差 — 单独审计，勿当引擎 bug |
     | balanced vs settlement | 86% | nest prior ≠ inventory 精确总价；**非 v0 首要修复** |

   - **金价 only（用户 2026-06-13）**
     - 子集定义：有 `avg_values.q5` / public 金均价，**无**金件数锁、无 `avg_cells.q5`、无 `quality_cells.q5`
     - penultimate **n=0**；`--audit-round 3` 在 curated 内仍 **n=0** → fatbeans 里金均价常与均格/扫描同窗到达
     - 现行引擎：`_apply_avg_value_cells_exact_count_intersection` **必须 avg_value + avg_cells 同时** 才派生金件数；**仅金价不会收窄**
     - **v0 批 B 试验（待做）**：在 `total_count` 精确时，若 `_avg_value_count_matches` 对 q5 **唯一** → 允许 `avg_value_only_q5_count_derived`（对齐手算「金均价 × 件数」）；需 synthetic + 早期 public-only 负例
     - 群友「扫描比金价贵」路径：**产品/UI 仍应提示先开金扫描**；引擎侧金价-only 是 **低成本补强**，不能替代 scan/cells

   - **批 B 实施顺序（2026-06-13 确认）**
     1. `count_prior` **总格 target ← 已知 q3–q5 cells 残差**（15 条 exact total 回归）
     2. 试验 **金均价-only** unique count pin（有 total 时）
     3. 0052 fallback + 白绿 bridge
     4. q1 split 口径文档化 / 测试（不计入批 B 门禁）

   - **批 B #1 完成（2026-06-13）**
     - 引擎：`total_grid_target_from_known_high_tier_cells`（`total_count` 精确 + ≥2 档 q3/q4/q5 整数 `quality_cells` + 无 hard grid）
     - 顺带：`avg_value_only_q5_count_derived`（仅 public 金均价 + 精确总件 + `_avg_value_count_matches` 唯一；整数均价不触发）
     - 复审计 curated penultimate：`total_cells` miss **69%→68%**；`subset_exact_total_count` n=14 miss **50%**（原 ~67%）
     - 回归：`tests/test_ahmad_ref_engine_public_info.py` — **7 条**已命中 band 的 exact-total fatbeans 不回归 + synthetic 金价-only

   - **批 B #3（2026-06-13）**
     - fatbeans `2402_*_0052.json` r3：`combo_count=2421`、`balanced=292763`、白绿 split bridge → `split_low_quality_q1_*_merged`（**不回归门禁**）
     - public avg downgrade：保留 synthetic `public_quality_avg_value_conflict_fallback`；不在单条 fatbeans 上迭代

   - **小样本纪律（批 B 起）**
     - curated n=173、exact-total n=14：**不够**做 MAE/miss 优化目标；audit miss% 仅作方向监控
     - pytest 门禁 = **已 hit 不回归** + **单条代表路径**（0052 / 合成负例）；**不要求** 14/14 band
     - 禁止：在 14 条上扫 `RESIDUAL_ITEM_CELL_ESTIMATE`、high-tier 档数阈值等；下一引擎改动需 **语义规则 + synthetic**

   - **批 B #2 残差均格（2026-06-13）**
     - 已知 high-tier cells + 残差件：优先 unfixed tier `avg_cells` 均值估计残差格；无信号才 `RESIDUAL_ITEM_CELL_ESTIMATE=4.0`
     - note：`total_grid_target_residual_avg_cells_estimate`；synthetic 单测 + 7 条 no-regress 仍绿

   - **验证**
     ```powershell
     python scripts/audit_aisha_gap.py
     python scripts/audit_aisha_gap.py --audit-round 3  # 早期轮 / 金价路径
     ```
