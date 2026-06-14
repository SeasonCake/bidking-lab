# 紫金件数+格子 UI 预览样本

用于目视确认 v0.1.9 dev 的「紫金件」行是否在 top3 锁定时显示 `紫N/M · 金N/M`。

## 1. 命令行预览（最快）

```powershell
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
python scripts/preview_purple_gold_cells_display.py
```

会打印三份样本的 summary，写入 `preview_expected.txt`，并生成带 fresh 时间戳的 `*_ui.json`（给 UI 加载用）。

## 2. 打开 Hero Ref UI（推荐目视）

先跑上一节命令，再开 UI。**请用 `*_ui.json`**（避免 stale）：

**主样本（紫+金都锁且有格）**：

```powershell
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
python external_references\ahmad_live_reference_lab\tools\ahmad_tk_overlay.py `
  --snapshot data\samples\hero_ref\fixtures\purple_gold_cells_display\locked_both_ui.json `
  --load-existing
```

看中间 **「红品与价值」** 卡片 → **「紫金件」** 行，应为：

```text
紫9/28 · 金4/7
```

红品仍单独两行：**红件** `1 / 1 / 1`、**红格** `4 / 4 / 4`（与紫金行分开）。

## 3. 其他两个对照样本

| 文件 | 预期「紫金件」行 | 场景 |
|---|---|---|
| `zero_gold_ui.json` | `紫5/9 · 金0/0` | 金档锁 0 且有格 |
| `settled_ui.json` | `紫8/27 · 金5/13` | 结算态读 `final_quality_*` |

`*_ui.json` 由预览脚本生成；源模板为同名的 `*_snapshot.json`。

## 4. 与低品「已锁」格式对齐

低品在 **「低品件」** 行，例如 `已锁 白绿10/27 蓝13/18`；紫金在 **「紫金件」** 行用同样 `档N/M` 紧凑格式，但不混进低品行。
