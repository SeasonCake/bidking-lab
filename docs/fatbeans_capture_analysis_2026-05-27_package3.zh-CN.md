# Fatbeans capture inspection: `bidking_package3.json`

## 中文摘要

这是 Fatbeans JSON 抓包导出的离线检查报告。报告只记录结构化统计、frame 索引、消息号和少量字符串预览，不需要把原始抓包文件提交到 Git。

结论：

- 当前导出包含 `83` 条 packet；这代表已导出的筛选结果，不一定等于抓包工具底栏的全部捕获数量。
- 全部 payload 已通过 Base64 长度校验，说明不是 UI 文本复制，也没有明显截断。
- 应用层可按 4 字节大端长度前缀重组成 `80` 条完整 frame。
- `SEND msg=0x0022`、`SEND msg=0x0026`、`REV push msg=0x0025` 和 `REV push msg=0x002d` 是当前优先分析对象。
- 下一步应验证这些 message id 和字段位置在更多样本中是否稳定，再把真实 packet 转为 normalized fixture / `LiveObservationBatch`。

简历/项目叙事价值：

- 这条链路覆盖 GUI 抓包、主 TCP 会话筛选、payload 校验、TCP 片段拼接、应用层 frame 重组、protobuf wire 字段探查和候选事件时间线生成。
- 它把项目从 OCR/手填输入推进到 packet 观测层，同时保持只读、离线、非自动化边界。

## 人工截图对照

截图中可见本局为 `map=2404`，局内 session 为 `2404:1274127889621635`。本局只有 3 轮：

- `SEND msg=0x0026 value=100105` 后，`REV push msg=0x0025` 的 field8 里出现
  `action=100105` 与结果 `51`，对应截图“所有蓝色品质藏品总占位数为 51 格”。
- `SEND msg=0x0026 value=100104` 后，下一次 `REV push msg=0x0025` 的 field8 里出现
  `action=100104` 与结果 `10`，对应截图“所有白色和绿色品质藏品总占位数为 10 格”。
- 地图/公开信息 field7 里出现 `map=2404` 与结果 `8`，对应截图“养生学家居所：金色品质总占用的格子数量为 8 格”。
- `SEND msg=0x0026 value=100124` 后，最终 `REV push msg=0x002d` 的 field8 里出现
  `action=100124` 与结果 `36798`，对应截图“所有紫色品质藏品的总价值为 36798”。

这说明 `0x0025` / `0x002d` 不只是心跳，而是在保存可直接进入 live 观测层的读数字段。
用户截图中选中的 SortID `8`、`32`、`50` 本身都是很短的确认/心跳类响应；真正承载
道具结果的是附近的服务器状态 push，例如 SortID `28`、`48`、`71`。

## 关于等待时收到封包

样本中即使用户不出价也会收到 `REV push msg=0x0077` 小包。它们包含玩家 ID 和
session id，但当前没有看到能直接解释为“对手出价金额”的字段。更可能的语义是：
某个玩家/NPC 已经提交动作、状态变更、倒计时/同步事件，或服务器通知客户端刷新局内状态。

因此当前结论是：**可以提前知道有服务器状态事件发生，可能包括哪个玩家已行动；但还不能证明
能在揭示前拿到对手出价金额。** 真正可读的详细回合状态仍出现在 `0x0025`，最终详细结果
出现在 `0x002d`。

## Capture Summary

- packets: 83
- sort_id range: 1 .. 93
- time range: 2026-05-27T23:31:08.1877859+08:00 .. 2026-05-27T23:33:34.8031548+08:00
- total payload bytes: 35360
- packet directions: {'SEND': 27, 'REV': 56}

## Endpoints

- `8.133.195.27:10000 -> 127.0.0.1:28935`: 56
- `127.0.0.1:28935 -> 8.133.195.27:10000`: 27

## Reconstructed Frames

- frames: 80
- frame directions: {'SEND': 27, 'REV': 53}
- SEND: 27 frames, 304 body bytes
  - common message ids: 0x019a x15, 0x0026 x3, 0x0022 x3, 0x001c x1, 0x0004 x1, 0x006c x1, 0x0048 x1, 0x0174 x1
- REV: 53 frames, 33884 body bytes
  - common message ids: 0x019b x15, 0x0077 x12, 0x0027 x6, 0x0023 x6, 0x0013 x4, 0x0025 x2, 0x001d x1, 0x0021 x1

## Interesting Frames

Showing up to 120 frames with JSON/text markers or length >= 700 bytes.

| frame | sort | time | dir | msg | tag | len | body | notes |
|---:|---:|---|---|---:|---|---:|---:|---|
| 2 | 4 | 23:31:08.947 | REV | 0x0021 | `push` | 825 | 809 | str=2404:1274127889621635 / _Barista / jmghkenf:<br>pb=1:len=806 '2404:1274127889621635' |
| 17 | 28 | 23:31:55.951 | REV | 0x0025 | `push` | 937 | 921 | str=2404:1274127889621635 / _Barista / fejmhkgn2<br>pb=1:len=918 '2404:1274127889621635' |
| 30 | 48 | 23:32:30.946 | REV | 0x0025 | `push` | 1094 | 1078 | str=2404:1274127889621635 / _Barista / fkemgnjh2<br>pb=1:len=1075 '2404:1274127889621635' |
| 44 | 71 | 23:33:06.036 | REV | 0x002d | `push` | 8110 | 8094 | str=2404:1274127889621635 / _Barista / hnfkejmg2<br>pb=1:varint=355898170652903; 2:len=5595 '2404:1274127889621635'; 6:len=516; 6:len=496; 6:len=755 'efk0' |
| 45 | 74 | 23:33:14.624 | REV | 0x0005 | `911ac01a` | 20145 | 20129 | pb=2:len=1356; 2:len=1369; 2:len=1198; 2:len=1521; 2:len=1165 |
| 46 | 80 | 23:33:14.905 | REV | 0x006d | `911ac01b` | 1461 | 1445 | pb=2:len=10; 2:len=13; 2:len=10; 2:len=10; 2:len=11 |
| 49 | 86 | 23:33:28.108 | REV | 0x0049 | `911ac01e` | 796 | 780 | str=mail_tiltle_102 / !&mail_text_102&itemName_1083009&1" / mail_sender_12<br>pb=2:len=95 'mail_tiltle_102'; 2:len=95 'mail_tiltle_102'; 2:len=95 'mail_tiltle_102'; 2:len=95 'mail_tiltle_102'; 2:len=95 'mail_tiltle_102' |

## Notes

- `REV` is Fatbeans' receive direction label.
- `tag=push` means the server-side request tag is zero, so the frame is likely an unsolicited server push.
- Message ids and protobuf fields are heuristic until matched against game semantics.

## Candidate Game Event Timeline

These rows are heuristic. They mark messages whose shape matches bids/actions or server-side round/settlement pushes.

| frame | sort | time | dir | msg | candidate | session | value | details |
|---:|---:|---|---|---:|---|---|---|---|
| 3 | 10 | 23:31:32.818 | SEND | 0x0026 | tool_or_action_candidate | 2404:1274127889621635 | 100105 |  |
| 6 | 21 | 23:31:52.363 | SEND | 0x0022 | bid_candidate | 2404:1274127889621635 | 280000 |  |
| 17 | 28 | 23:31:55.951 | REV | 0x0025 | round_state_push_candidate | 2404:1274127889621635 | map=2404 round=1 | field5=4 field6=2 field7=1 field8=1 |
| 9 | 33 | 23:32:11.870 | SEND | 0x0026 | tool_or_action_candidate | 2404:1274127889621635 | 100104 |  |
| 12 | 45 | 23:32:30.608 | SEND | 0x0022 | bid_candidate | 2404:1274127889621635 | 280000 |  |
| 30 | 48 | 23:32:30.946 | REV | 0x0025 | round_state_push_candidate | 2404:1274127889621635 | map=2404 round=2 | field5=4 field6=3 field7=2 field8=2 |
| 15 | 54 | 23:32:53.789 | SEND | 0x0026 | tool_or_action_candidate | 2404:1274127889621635 | 100124 |  |
| 18 | 67 | 23:33:05.266 | SEND | 0x0022 | bid_candidate | 2404:1274127889621635 | 280000 |  |
| 44 | 71 | 23:33:06.036 | REV | 0x002d | settlement_or_r5_push_candidate | 2404:1274127889621635 | map=2404 round=2 v3=None v4=None v5=None | field6_players_or_results=4 snapshot_field6=3 |
