# Fatbeans capture inspection: `bid_king_packages6.json`

## 中文摘要

这是 Fatbeans JSON 抓包导出的离线检查报告。报告只记录结构化统计、frame 索引、消息号和少量字符串预览，不需要把原始抓包文件提交到 Git。

结论：

- 当前导出包含 `70` 条 packet；这代表已导出的筛选结果，不一定等于抓包工具底栏的全部捕获数量。
- 全部 payload 已通过 Base64 长度校验，说明不是 UI 文本复制，也没有明显截断。
- 应用层可按 4 字节大端长度前缀重组成 `74` 条完整 frame。
- `SEND msg=0x0022`、`SEND msg=0x0026`、`REV push msg=0x0025` 和 `REV push msg=0x002d` 是当前优先分析对象。
- 下一步应验证这些 message id 和字段位置在更多样本中是否稳定，再把真实 packet 转为 normalized fixture / `LiveObservationBatch`。

简历/项目叙事价值：

- 这条链路覆盖 GUI 抓包、主 TCP 会话筛选、payload 校验、TCP 片段拼接、应用层 frame 重组、protobuf wire 字段探查和候选事件时间线生成。
- 它把项目从 OCR/手填输入推进到 packet 观测层，同时保持只读、离线、非自动化边界。

## Capture Summary

- packets: 70
- sort_id range: 1 .. 151
- time range: 2026-05-28T14:26:54.1628355+08:00 .. 2026-05-28T14:29:35.988243+08:00
- total payload bytes: 15582
- packet directions: {'SEND': 23, 'REV': 47}

## Endpoints

- `8.133.195.27:10000 -> 127.0.0.1:10518`: 47
- `127.0.0.1:10518 -> 8.133.195.27:10000`: 23

## Reconstructed Frames

- frames: 74
- frame directions: {'SEND': 23, 'REV': 51}
- SEND: 23 frames, 222 body bytes
  - common message ids: 0x019a x17, 0x0022 x4, 0x001c x1, 0x0026 x1
- REV: 51 frames, 14268 body bytes
  - common message ids: 0x019b x17, 0x0077 x16, 0x0023 x8, 0x0025 x3, 0x0013 x2, 0x0027 x2, 0x001d x1, 0x0021 x1

## Interesting Frames

Showing up to 260 frames with JSON/text markers or length >= 700 bytes.

| frame | sort | time | dir | msg | tag | len | body | notes |
|---:|---:|---|---|---:|---|---:|---:|---|
| 3 | 7 | 14:26:58.015 | REV | 0x0021 | `push` | 461 | 445 | str=2405:1274127940692446 / _Barista<br>pb=1:len=442 '2405:1274127940692446' |
| 14 | 61 | 14:27:38.992 | REV | 0x0025 | `push` | 759 | 743 | str=2405:1274127940692446 / _Barista<br>pb=1:len=740 '2405:1274127940692446' |
| 24 | 92 | 14:28:11.982 | REV | 0x0025 | `push` | 1158 | 1142 | str=2405:1274127940692446 / _Barista<br>pb=1:len=1139 '2405:1274127940692446' |
| 35 | 116 | 14:28:47.998 | REV | 0x0025 | `push` | 1398 | 1382 | str=2405:1274127940692446 / _Barista<br>pb=1:len=1379 '2405:1274127940692446' |
| 49 | 146 | 14:29:31.058 | REV | 0x002d | `push` | 9936 | 9920 | str=2405:1274127940692446 / _Barista / TEUU<br>pb=1:varint=353149392814275; 2:len=6392 '2405:1274127940692446'; 6:len=659 'TEUU'; 6:len=601; 6:len=1037 |

## Notes

- `REV` is Fatbeans' receive direction label.
- `tag=push` means the server-side request tag is zero, so the frame is likely an unsolicited server push.
- Message ids and protobuf fields are heuristic until matched against game semantics.

## Normalized Findings

- session: `2405:1274127940692446`
- map: `2405`
- states: round 1 at `sort=61`, round 2 at `sort=92`, round 3 at `sort=116`, settlement at `sort=146`
- user sends: bid `450000` repeated 4 times, action `100129` once
- public info `200031`: fixed32 value `69183.0`
- public reveal `200026`: 3 runtime ids with quality only, matching the user's note that the system revealed one green, one purple, and one gold item without shape/name.

### Aisha Skill Reveals

`field6` is now parsed as hero skill reveal blocks. In this sample hero `103` exposes cumulative `runtime_id + quality + shape_code` entries:

- `1001034`: 6 white items, 11 cells total.
- `1001033`: 13 green items, 24 cells total.
- `1001032`: 14 blue items, 28 cells total.
- `1001031`: 9 purple items, 32 cells total.

The parsed counts/cells align with the screenshots and final manual notes for white/green/blue/purple.

### Random Inspection

The action `100129` returns exact item facts:

| runtime_id | item_id | item | quality | shape | cells | value |
|---:|---:|---|---:|---:|---:|---:|
| 1274127940693022 | 1025001 | 手术用显微镜 | 5 | 22 | 4 | 49920 |
| 1274127940693002 | 1071004 | 耳机防尘塞 | 1 | 11 | 1 | 137 |

### Settlement Inventory

The settlement inventory is internally consistent with the user's final totals:

| quality | count | cells |
|---:|---:|---:|
| 1 白 | 6 | 11 |
| 2 绿 | 13 | 24 |
| 3 蓝 | 14 | 28 |
| 4 紫 | 9 | 32 |
| 5 金 | 7 | 29 |
| 6 红 | 4 | 13 |
| total | 53 | 137 |

- table value sum: `1271891`
- user-recorded bid / price: `981112`
- computed profit from these two numbers: `290779`

## Candidate Game Event Timeline

These rows are heuristic. They mark messages whose shape matches bids/actions or server-side round/settlement pushes.

| frame | sort | time | dir | msg | candidate | session | value | details |
|---:|---:|---|---|---:|---|---|---|---|
| 6 | 59 | 14:27:38.353 | SEND | 0x0022 | bid_candidate | 2405:1274127940692446 | 450000 |  |
| 14 | 61 | 14:27:38.992 | REV | 0x0025 | round_state_push_candidate | 2405:1274127940692446 | map=2405 round=1 | field5=4 field6=2 field7=1 field8=0 |
| 9 | 75 | 14:27:57.594 | SEND | 0x0022 | bid_candidate | 2405:1274127940692446 | 450000 |  |
| 24 | 92 | 14:28:11.982 | REV | 0x0025 | round_state_push_candidate | 2405:1274127940692446 | map=2405 round=2 | field5=4 field6=3 field7=2 field8=0 |
| 14 | 105 | 14:28:36.537 | SEND | 0x0022 | bid_candidate | 2405:1274127940692446 | 450000 |  |
| 35 | 116 | 14:28:47.998 | REV | 0x0025 | round_state_push_candidate | 2405:1274127940692446 | map=2405 round=3 | field5=4 field6=4 field7=2 field8=0 |
| 17 | 122 | 14:29:03.482 | SEND | 0x0026 | tool_or_action_candidate | 2405:1274127940692446 | 100129 |  |
| 19 | 133 | 14:29:12.085 | SEND | 0x0022 | bid_candidate | 2405:1274127940692446 | 450000 |  |
| 49 | 146 | 14:29:31.058 | REV | 0x002d | settlement_or_r5_push_candidate | 2405:1274127940692446 | map=2405 round=3 v3=None v4=None v5=None | field6_players_or_results=4 snapshot_field6=4 |
