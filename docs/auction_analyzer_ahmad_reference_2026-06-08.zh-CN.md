# AuctionAnalyzer / Ahmad Reference Review

日期：2026-06-08

## 结论

`external_references/AuctionAnalyzer4.13.3` 可作为算法参考，但不适合整套接入正式出价。它的价值主要在三类局部能力：

- 数量、品质、总格、均格之间的组合枚举与可达性检查；
- 均格显示值反推候选总格区间，例如 `count + avg_cells -> possible total_cells`；
- 价格模型可作为 sanity check，但不能直接替换 v3 posterior/sampler。

本轮先落地 Ahmad 输入通道，不改 sampler 权重、不改外部计算器价格模型、不影响另一个窗口的 v3 promotion/audit 主线。

## 外部计算器可复用点

AuctionAnalyzer 的核心是通用 calculator，不是 Ahmad 专用实现。它通过 `CalcParams` 接收：

- total count / total grid / total avg grid；
- q3/q4/q5/q6 count、grid、avg grid；
- q4/q5/q6 avg value；
- green+white merged count/grid/avg。

这些字段和 Ahmad 技能强相关：

- `100204`：R1 总藏品数量；
- `1002041`：R2 金/橙色平均格数；
- `1002042`：R3 紫色平均格数；
- `1002043`：R4 蓝色平均格数；
- `1002044`：R5 绿色+白色总数量。

外部 `bidking-booooot` 也使用同一语义：`1002044` 从 `HitItemIndex` 取绿白件数，`1002043` 从 `AllHitItemAvgBoxIndex` 取蓝色均格。

## 本轮已落地

新增 Ahmad 数值技能通道：

- `FatbeansSkillReveal` 增加 `result/result_field`；
- parser 保留“无 observed_items、只有数字结果”的 skill reveal；
- live field updates：
  - `100204 -> session.total_item_count`；
  - `1002041 -> bucket.5.avg_cells`；
  - `1002042 -> bucket.4.avg_cells`；
  - `1002043 -> bucket.3.avg_cells`；
  - `1002044 -> bucket.1.count`，沿用现有 q1=绿白合并普品口径；
- v3 `SKILL_REVEAL_SPECS` 增加 `100204x`；
- v3 canonical evidence payload 增加 skill `result/result_field`，因此 hard/soft constraints 可以消费 Ahmad 数值。

## 尚未直接接入的部分

暂不接入 AuctionAnalyzer 的整套价格模型，原因：

- 它是 WPF/C# calculator + OCR 流程，和当前 live/Fatbeans/v3 pipeline 责任不同；
- 它使用枚举 + 对数概率 + safety factor，和当前 v3 posterior、formal/advisory 出价口径不同；
- 直接替换会绕开现有 archive/live/readiness/guard 指标，不利于解释过冲或低估。

更合适的下一步是移植局部算法为 shadow/advisory：

- avg-cells reachability：基于 count、avg display、可组合格数，输出候选 total_cells band；
- deterministic cell inference：当候选总格唯一时，作为 soft-to-hard 候选进入 shadow audit；
- impossible/narrow/broad 标记显示到 UI，提醒用户该均格信息是否足够强。

## 风险与确认项

2026-06-08 初版记录时，真实样本库尚未找到 Ahmad `100204x` capture，因此字段号曾是基于现有 action/public parser 与外部 skill log 语义推断。

2026-06-09 实战样本已修正该口径：

- Ahmad `100204` 的 R1 总件数真实出现于 `field7`；
- 普通 action count result 也可出现在 `field7`，例如 `100117` 良品存量；
- 整数结果字段候选已扩展为 `14/12/7`；
- 浮点均格优先尝试 fields `11/9/10`；
- Victor `100209` 已按实战文本统一为 `q4+q5+q6` 件数和；
- `100113` 等均格 action 的 `0` 是合法结果；没有显式 result 但同局状态继续推进时，UI/notes 必须标出 `inferred_zero`。

后续如果出现新的字段位置，应只修 parser field mapping，并补 focused test；不需要推翻当前 structured ref bridge 或 v3 registry/constraint 设计。
