# Fatbeans capture inspection: `bid_king_packages_5.json`

## 中文摘要

这是 Fatbeans JSON 抓包导出的离线检查报告。报告只记录结构化统计、frame 索引、消息号和少量字符串预览，不需要把原始抓包文件提交到 Git。

结论：

- 当前导出包含 `103` 条 packet；这代表已导出的筛选结果，不一定等于抓包工具底栏的全部捕获数量。
- 全部 payload 已通过 Base64 长度校验，说明不是 UI 文本复制，也没有明显截断。
- 应用层可按 4 字节大端长度前缀重组成 `118` 条完整 frame。
- `SEND msg=0x0022`、`SEND msg=0x0026`、`REV push msg=0x0025` 和 `REV push msg=0x002d` 是当前优先分析对象。
- 下一步应验证这些 message id 和字段位置在更多样本中是否稳定，再把真实 packet 转为 normalized fixture / `LiveObservationBatch`。

简历/项目叙事价值：

- 这条链路覆盖 GUI 抓包、主 TCP 会话筛选、payload 校验、TCP 片段拼接、应用层 frame 重组、protobuf wire 字段探查和候选事件时间线生成。
- 它把项目从 OCR/手填输入推进到 packet 观测层，同时保持只读、离线、非自动化边界。

## 人工记录对照

本局 session 为 `2408:1274127927582599`，地图号 `map=2408`。当前导出包含
`103` 条 packet，可重组为 `118` 条完整 frame。

### 动作与回合

- R1：`SEND msg=0x0026 value=100136`，对应 `宝光四鉴`。
- R2：`SEND msg=0x0026 value=100129`，对应 `随机抽检（2）`。
- R3：`SEND msg=0x0026 value=100105`，对应蓝品总格扫描，结果 `26`。
- R4：`SEND msg=0x0026 value=100104`，对应白绿总格扫描，结果 `7`。
- R5 前：`SEND msg=0x0026 value=100112`，对应 `优品均格`，fixed32 结果 `2.3076923`。

### 公开信息

- `public info=200013` 的 fixed32 值为 `2.30769`。
- `public info=200033` 的 fixed32 值为 `14798.8`。

### 宝光四鉴

宝光四鉴的 action block 不返回一个整数 `result`，而是返回 4 条 item observation：

| runtime id | 宝光品质 | 结算 item_id | 结算物品 | 结算格数 | 结算价值 |
|---:|---:|---:|---|---:|---:|
| 1274127927583413 | 4 紫 | 1024001 | 输液泵 | 4 | 9880 |
| 1274127927583400 | 5 金 | 1045007 | 单兵水下推进器 | 6 | 37350 |
| 1274127927583403 | 4 紫 | 1054007 | 和田玉原石 | 4 | 18240 |
| 1274127927583386 | 5 金 | 1035005 | 机械腕表 | 1 | 9245 |

这说明宝光包本身能稳定给出“被揭示物品 runtime id + 品质”，但不直接给 item_id；
结算清单里能用相同 runtime id 反查到具体物品、格数和价值。

### 随机抽检（2）

抽检包直接给出 item_id、品质、价值、shape code 和格数：

| runtime id | item_id | 物品 | 品质 | value | shape code | cells |
|---:|---:|---|---:|---:|---:|---:|
| 1274127927583419 | 1021005 | 医用一次性口罩 | 1 白 | 207 | 21 | 2 |
| 1274127927583399 | 1023009 | 静脉注射用人免疫球蛋白 | 3 蓝 | 1313 | 11 | 1 |

这与截图中的 `医用一次性口罩`、`静脉注射...` 对齐。抽检确实和宝光不是同一种
刷新结构：抽检 action block 里直接带完整 item_id，而宝光只带品质。

### 结算清单

结算 `REV push msg=0x002d` 的 inventory block 能还原完整战利品：

- 物品数：`42`
- 总格数：`114`
- 表内价值合计：`753522`
- 格数分布：`1格 x21`、`2格 x7`、`3格 x1`、`4格 x7`、`6格 x3`、`9格 x2`、`12格 x1`
- 品质件数：白 `2`、绿 `3`、蓝 `13`、紫 `13`、金 `8`、红 `3`
- 品质格数：白 `3`、绿 `4`、蓝 `26`、紫 `30`、金 `42`、红 `9`

用户手动记录的总格 `114` 和战利品价值 `753522` 与 packet 完全一致；手动件数
`41` 与 packet 中的 `42` 不一致，packet 的 `42` 件同时满足总格和总价，优先记录为
当前样本的精确值。

### 出价与结算

结算包中 `九千年之梦` 的 values 序列包含 `750000`，与最终成交价对齐。
注意：结算包里的玩家出价 values 不总是按时间顺序排列，不能简单取最后一个值作为最终价。

## VPN / 加速器备注

用户观察到 VPN / UU 加速器会干扰 Fatbeans 抓包，且影响可能不只限于 `BidKing.exe`。
后续采样建议关闭 VPN/加速器，只筛选 `BidKing.exe` 主 TCP 会话
`127.0.0.1:<local> <-> 8.133.195.27:10000` 后导出 JSON。

## Capture Summary

- packets: 103
- sort_id range: 2 .. 206
- time range: 2026-05-28T11:18:25.2814568+08:00 .. 2026-05-28T11:22:39.1198624+08:00
- total payload bytes: 20430
- packet directions: {'SEND': 38, 'REV': 65}

## Endpoints

- `8.133.195.27:10000 -> 127.0.0.1:57446`: 65
- `127.0.0.1:57446 -> 8.133.195.27:10000`: 38

## Reconstructed Frames

- frames: 118
- frame directions: {'SEND': 38, 'REV': 80}
- SEND: 38 frames, 447 body bytes
  - common message ids: 0x019a x26, 0x0026 x5, 0x0022 x5, 0x00fa x1, 0x001c x1
- REV: 80 frames, 18247 body bytes
  - common message ids: 0x019b x26, 0x0077 x20, 0x0027 x10, 0x0023 x10, 0x0013 x6, 0x0025 x4, 0x00fb x1, 0x001d x1

## Interesting Frames

Showing up to 220 frames with JSON/text markers or length >= 700 bytes.

| frame | sort | time | dir | msg | tag | len | body | notes |
|---:|---:|---|---|---:|---|---:|---:|---|
| 3 | 7 | 11:18:26.545 | REV | 0x0021 | `push` | 701 | 685 | str=2408:1274127927582599 / _Barista / kangjian<br>pb=1:len=682 '2408:1274127927582599' |
| 19 | 72 | 11:19:22.544 | REV | 0x0025 | `push` | 931 | 915 | str=2408:1274127927582599 / kangjian / _Barista<br>pb=1:len=912 '2408:1274127927582599' |
| 32 | 102 | 11:19:57.651 | REV | 0x0025 | `push` | 1259 | 1243 | str=2408:1274127927582599 / _Barista / kangjian<br>pb=1:len=1240 '2408:1274127927582599' |
| 46 | 128 | 11:20:38.611 | REV | 0x0025 | `push` | 1477 | 1461 | str=2408:1274127927582599 / kangjian / _Barista<br>pb=1:len=1458 '2408:1274127927582599' |
| 61 | 159 | 11:21:25.611 | REV | 0x0025 | `push` | 2238 | 2222 | str=2408:1274127927582599 / _Barista / kangjian<br>pb=1:len=2219 '2408:1274127927582599' |
| 76 | 194 | 11:22:13.639 | REV | 0x002d | `push` | 10769 | 10753 | str=2408:1274127927582599 / _Barista / kangjian<br>pb=1:varint=79714593058995; 2:len=6802 '2408:1274127927582599'; 6:len=425 ';gFh'; 6:len=1666 'heinfljgk'; 6:len=856 ';gFh' |

## Notes

- `REV` is Fatbeans' receive direction label.
- `tag=push` means the server-side request tag is zero, so the frame is likely an unsolicited server push.
- Message ids and protobuf fields are heuristic until matched against game semantics.

## Candidate Game Event Timeline

These rows are heuristic. They mark messages whose shape matches bids/actions or server-side round/settlement pushes.

| frame | sort | time | dir | msg | candidate | session | value | details |
|---:|---:|---|---|---:|---|---|---|---|
| 7 | 65 | 11:19:14.721 | SEND | 0x0026 | tool_or_action_candidate | 2408:1274127927582599 | 100136 |  |
| 9 | 70 | 11:19:21.963 | SEND | 0x0022 | bid_candidate | 2408:1274127927582599 | 369213 |  |
| 19 | 72 | 11:19:22.544 | REV | 0x0025 | round_state_push_candidate | 2408:1274127927582599 | map=2408 round=1 | field5=4 field6=2 field7=1 field8=1 |
| 12 | 90 | 11:19:45.136 | SEND | 0x0026 | tool_or_action_candidate | 2408:1274127927582599 | 100129 |  |
| 14 | 100 | 11:19:57.329 | SEND | 0x0022 | bid_candidate | 2408:1274127927582599 | 369213 |  |
| 32 | 102 | 11:19:57.651 | REV | 0x0025 | round_state_push_candidate | 2408:1274127927582599 | map=2408 round=2 | field5=4 field6=3 field7=2 field8=2 |
| 17 | 111 | 11:20:13.594 | SEND | 0x0026 | tool_or_action_candidate | 2408:1274127927582599 | 100105 |  |
| 20 | 125 | 11:20:37.496 | SEND | 0x0022 | bid_candidate | 2408:1274127927582599 | 369213 |  |
| 46 | 128 | 11:20:38.611 | REV | 0x0025 | round_state_push_candidate | 2408:1274127927582599 | map=2408 round=3 | field5=4 field6=4 field7=2 field8=3 |
| 22 | 135 | 11:20:48.755 | SEND | 0x0026 | tool_or_action_candidate | 2408:1274127927582599 | 100104 |  |
| 25 | 145 | 11:21:03.377 | SEND | 0x0022 | bid_candidate | 2408:1274127927582599 | 690000 |  |
| 61 | 159 | 11:21:25.611 | REV | 0x0025 | round_state_push_candidate | 2408:1274127927582599 | map=2408 round=4 | field5=4 field6=5 field7=2 field8=4 |
| 31 | 178 | 11:21:54.181 | SEND | 0x0026 | tool_or_action_candidate | 2408:1274127927582599 | 100112 |  |
| 33 | 185 | 11:22:07.431 | SEND | 0x0022 | bid_candidate | 2408:1274127927582599 | 719000 |  |
| 76 | 194 | 11:22:13.639 | REV | 0x002d | settlement_or_r5_push_candidate | 2408:1274127927582599 | map=2408 round=4 v3=None v4=None v5=None | field6_players_or_results=4 snapshot_field6=5 |
