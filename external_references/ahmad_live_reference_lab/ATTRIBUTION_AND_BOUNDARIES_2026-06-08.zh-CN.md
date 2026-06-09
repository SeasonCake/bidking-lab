# Attribution and Boundaries

日期：2026-06-08

## 当前可确认来源

本实验线参考以下本地外部资料：

- `external_references/AuctionAnalyzer4.13.3`
  - 本地二进制与反编译参考，项目名在文档中记录为 `MapBidCalculator v4.13.3`；
  - 主要参考 `MainWindow.cs`、`Models/CalcParams.cs`、`Services/DataLoaderService.cs`、`Services/MapQualityProbs.cs`、`Services/OcrParser.cs`；
  - 用户确认作者/来源主页为 B站 `猫饭团子uu`：`https://space.bilibili.com/1981353429`；
  - 当前本地文档仍未确认明确许可证，暂按“本地外援参考，不直接复制发布”处理。
- `external_references/bidking-booooot`
  - GitHub：`nql1314/bidking-booooot`；
  - License：Apache-2.0；
  - 本地 `viewer_main.py` 中包含 `免费分享 禁止倒卖 Q群 956946772 B站 https://space.bilibili.com/1934731`；
  - 可参考其 Ahmad runner/解析/视图结构，但若复制代码必须保留 Apache-2.0 attribution。
- `external_references/jrinky-bidking`
  - GitHub：`Jrinky908/bidking`；
  - 本地 snapshot 未找到明确 license，README 请求署名；
  - 只作 Monte Carlo/prior schema 参考。

当前署名口径：

```text
Ahmed reference calculator inspired by MapBidCalculator / AuctionAnalyzer 4.13.3.
原作者/参考来源：B站猫饭团子uu（https://space.bilibili.com/1981353429）及本地外援文档。
本支线 UI 修改与计算优化：B站加菲_barista（https://space.bilibili.com/88048665）
```

如果后续发布或迁移到主线，仍应再人工复核原程序的发布说明、许可和作者署名要求。

## 代码边界

第一阶段允许：

- 在 `external_references/ahmad_live_reference_lab` 内写新代码；
- 用文档引用外援文件路径；
- 手工移植算法思想，并重写为 bidking-lab 风格的小模块；
- 只读主线 live JSON/log，不 import 主线内部未稳定 API。
- UI 使用与现有 `scripts/run_live_overlay.py` 相同的 Tkinter 桌面 overlay 方向。

第一阶段不允许：

- 复制整包二进制或 OCR 模型到新目录；
- 把反编译 C# 大段原样搬入主线；
- 把外援计算器输出直接接正式出价；
- 改主线 v3 readiness/promotion gate；
- 改 live monitor/overlay 主文件，直到另一个窗口完成并合并。
- 把 HTML 原型当作最终 UI；HTML 只允许作为临时调试 API/浏览器预览。

## UI 署名建议

Level 1 compact overlay 不放长署名，避免干扰实战。

Level 2/3 或关于页显示：

```text
Ahmed Ref: based on local MapBidCalculator/AuctionAnalyzer 4.13.3 reference notes,
with BidKing Lab v3 packet evidence and guard diagnostics.
External references are used for comparison and design inspiration only.
```

中文：

```text
Ahmed 参考推理：参考 B站猫饭团子uu 与本地 MapBidCalculator/AuctionAnalyzer 4.13.3 外援计算器思路；
本支线 UI 修改与计算优化：B站加菲_barista（https://space.bilibili.com/88048665）；
并结合 BidKing Lab v3 的实时 packet 证据与风险标签。外援仅作设计参考。
```
