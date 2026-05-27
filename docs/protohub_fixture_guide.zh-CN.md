# ProtoHub 离线样本获取指南

## 当前需要你做什么

继续开发并不要求你一直开着游戏。现在只有一件事需要实机协助：获得一份
ProtoHub 能看到的原始输出样本，用来确定真实字段名和事件格式。

不要手动整理或改写第一份原始样本。原始字段名本身就是 parser 需要验证的信息。

## 最小样本目标

优先取得一局中的以下两个时间点：

1. 进入竞拍、伊森已经显示部分轮廓时的一条状态输出。
2. 第五回合或总仓储格数被精确揭示后的另一条状态输出。

有条件再补充一次道具使用后的输出。R1-R4 不要求推断未知总件数，也不需要手动补齐；
R5 若协议里已经给出完整轮廓 / 物品列表 / 准确件数，请保留原始字段，项目会把它当作
`total_item_count` 精确约束。

## 操作方式

ProtoHub 的具体版本和界面尚未确认，因此当前按通用流程操作：

1. 打开游戏，并进入一局使用伊森的对局。
2. 打开你视频中使用的 ProtoHub 工具，开始只读捕获或日志查看。
3. 在工具里找到包含当前局状态、轮次、物品格子/轮廓、道具揭示的记录。
4. 若工具有 `Export`、`Save`、`Copy JSON`、`Copy Response` 或 `Save Session`，优先导出原始 JSON/文本。
5. 若只能导出 `.har`、`.pcap`、`.log` 或工具自身 session 文件，也可以直接保留。
6. 把文件放在本机任意位置，并把完整路径告诉我；无需提交到 Git。

若你找不到导出按钮，提供 ProtoHub 当前窗口截图即可，我可以按界面指出下一步。

## 本项目已能读取的规范化 fixture

当前 adapter 支持的目标格式示例位于：

`data/samples/packet_fixture.example.json`

可用下列命令验证格式：

```powershell
C:\Python313\python.exe scripts\inspect_packet_fixture.py data\samples\packet_fixture.example.json
```

示例中特意使用：

- `warehouse_estimated_cells`：伊森 R1-R4 根据底部轮廓估出来的大致仓库格数。
- `warehouse_estimate_tolerance`：为遮挡、站位和未揭示上方空间保留的冗余。
- `visible_items[].shape_key`：已知形状但品质未知的物品。

第五回合若获得准确总格，应改用 `warehouse_total_cells`，若获得准确总件数则使用
`total_item_count`。此时推理会优先使用精确总格，不再依赖近似容差。
