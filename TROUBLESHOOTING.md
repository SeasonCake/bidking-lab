# Troubleshooting & Lessons Learned（bidking-lab）

> 记录 BidKing 数据解析 / 本地工具链里**真实踩过的坑**，按主题归档，方便以后自己和协作者查阅。  
> 环境参考：Windows 11 / PowerShell 7 / Python 3.13 / Steam 版《竞拍之王》安装于自定义库目录。

## 目录

1. [可编辑安装 `pip install -e` 是干什么的](#1-可编辑安装-pip-install--e-是干什么的)
2. [游戏路径：不要搜整盘 `StreamingAssets`](#2-游戏路径不要搜整盘-streamingassets)
3. [`Tables/*.txt` 看起来像乱码 ≠ 一定"加密"](#3-tablestxt-看起来像乱码--一定加密)
4. [`Drop.txt` 头部形态（283KB 样本）](#4-droptxt-头部形态283kb-样本)
5. [把表拷进 `data/raw/`（git 外）](#5-把表拷进-data-rawgit-外)
6. [调试速查](#6-调试速查)
7. [`Tables/*.txt` 解码结论：Base64 → UTF-8 TSV](#7-tablestxt-解码结论base64--utf-8-tsv)
8. [PowerShell 里中文显示乱码 ≠ 数据坏了](#8-powershell-里中文显示乱码--数据坏了)
9. [启动 Streamlit UI（避开 anaconda）](#9-启动-streamlit-ui避开-anaconda)
10. [`st.dataframe` 在 anaconda 下崩：pyarrow vs numpy 2.x](#10-stdataframe-在-anaconda-下崩pyarrow-vs-numpy-2x)
11. [`QualityBucketObs(value_range=(0,0))` 触发 `ZeroDivisionError`](#11-qualitybucketobsvalue_range00-触发-zerodivisionerror)
12. [`UnicodeEncodeError: 'gbk'` ↔ 中文字符 `\u200b`](#12-unicodeencodeerror-gbk--中文字符-u200b)
13. [`demo_snipe.py` 提示 "Snipe gating failed; no recommendation"](#13-demo_snipepy-提示-snipe-gating-failed-no-recommendation)
14. [matplotlib 中文字体在 Streamlit 中缺失（字符变方框）](#14-matplotlib-中文字体在-streamlit-中缺失字符变方框)
15. [Streamlit "推理一直转圈" 实际是 widget 太多卡渲染](#15-streamlit-推理一直转圈-实际是-widget-太多卡渲染)
16. ["填了巨物/估值，但秒仓·放仓输出没变" 不是 bug](#16-填了巨物估值但秒仓放仓输出没变-不是-bug)
17. [Streamlit ROI tab 慢的真正原因不是计算，是没缓存](#17-streamlit-roi-tab-慢的真正原因不是计算是没缓存)
18. [`st.number_input` 默默吞掉尾零 → avg_cells 引擎 AttributeError](#18-stnumber_input-默默吞掉尾零--avg_cells-引擎-attributeerror)
19. [道具命名错位：代码里的"精品/珍品"≠ 游戏里的术语](#19-道具命名错位代码里的精品珍品-游戏里的术语)
20. [ROI 引擎"总仓储空间"= 0 不是 bug 也不是 feature，是缺少噪声模型](#20-roi-引擎总仓储空间-0-不是-bug-也不是-feature是缺少噪声模型)
21. [Snipe gate 在小样本场景静默返回 None](#21-snipe-gate-在小样本场景静默返回-none)
22. [BidMap 静态字段 ≠ session 动态 hint](#22-bidmap-静态字段--session-动态-hint)
23. [分析估算红品自动推断在 bucket 未填全时仍把残差归红品](#23-分析估算红品自动推断在-bucket-未填全时仍把残差归红品)
24. [`value=0` 默认值导致"未提供"和"确认为零"无法区分](#24-value0-默认值导致未提供和确认为零无法区分)
25. [`compute_analytical_estimate` 没用枚举，用户填的 `value_sum` 被忽略](#25-compute_analytical_estimate-没用枚举用户填的-value_sum-被忽略)
26. [`_build_session` 红品残差不用枚举，只填 count 的 bucket 被吞](#26-_build_session-红品残差不用枚举只填-count-的-bucket-被吞)
27. [`HUGE_CELLS_PER_QUALITY` 阈值与 UI 文案不一致](#27-huge_cells_per_quality-阈值与-ui-文案不一致)
28. [`huge_cells_override` 已实现但 UI 从未暴露 → 玩家无法精确锁定具体巨物](#28-huge_cells_override-已实现但-ui-从未暴露--玩家无法精确锁定具体巨物)
29. [放仓推荐忽略红/金 bucket 约束 → 给红有大件的高价仓也建议放](#29-放仓推荐忽略红金-bucket-约束--给红有大件的高价仓也建议放)
30. [秒仓/放仓 UI 下线（实验功能）](#30-秒仓放仓-ui-下线实验功能)
31. [均价/均格只收紧枚举、不进 MC — 设计如此](#31-均价均格只收紧枚举不进-mc--设计如此)
32. [MC fallback 重建 bucket 丢失 `huge_cells_override`](#32-mc-fallback-重建-bucket-丢失-huge_cells_override)
33. [各字段对 MC / 枚举的影响矩阵（设计预期）](#33-各字段对-mc--枚举的影响矩阵设计预期)
34. [安装 capture OCR 时 pip 下载超时](#34-安装-capture-ocr-时-pip-下载超时)
35. [换图后 toast 闪烁、地图下拉锁死（widget rev 未同步）](#35-换图后-toast-闪烁地图下拉锁死widget-rev-未同步)
36. [Capture OCR 日志与 ROI 调参](#36-capture-ocr-日志与-roi-调参)
37. [紫品均格 OCR 有数但输入框为空](#37-紫品均格-ocr-有数但输入框为空)
38. [实机 OCR 比改版前慢](#38-实机-ocr-比改版前慢)
39. [切 tab 读数被清空 / 抓屏卡顿](#39-切-tab-读数被清空--抓屏卡顿)
40. [启动仍慢：screen_ocr_warmup 与首屏等待](#40-启动仍慢screen_ocr_warmup-与首屏等待)
41. [后台推断很慢：MC 采样冷缓存，不是 filter](#41-后台推断很慢mc-采样冷缓存不是-filter)
42. [金品只填均价预览显示 0格/1件 或 ⚠️ 无候选](#42-金品只填均价预览显示-0格1件-或--无候选)

---

## 1. 可编辑安装 `pip install -e` 是干什么的

**用途**：在本机把 `src/bidking_lab` **链接**进当前 Python，任意目录可 `import bidking_lab`，改代码**无需反复重装**。

**典型命令**（仓库根目录）：

```powershell
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
python -m pip install -e ".[dev]"
```

**症状**：若提示 `normal site-packages is not writeable`，pip 会退回到 **user** 安装（`%APPDATA%\Python\...`），一般仍可用。

**教训**：做库型项目时 **`-e` 一次即可**；CI 或纯脚本用户也可用 `pip install .` 非可编辑。

---

## 2. 游戏路径：不要搜整盘 `StreamingAssets`

**症状**：资源管理器搜索 `C:\` 下 `StreamingAssets`，结果极多、格式杂乱，怀疑“加密”。

**原因**：**多个游戏/引擎**都会在各自安装目录下有 `StreamingAssets`，和 BidKing 无关。真正要盯的是：

```text
<SteamLibrary>\steamapps\common\BidKing\BidKing_Data\StreamingAssets
```

本机示例：`C:\xiangmuyunxing\steamapps\common\BidKing\...`（Steam 库根在注册表里常指向自定义盘符）。

**修法**：在代码里用环境变量 **`BIDKING_GAME_ROOT`** 指向 `...\BidKing` 根目录，或用仓库内 `bidking_lab.config.get_game_root()`。

---

## 3. `Tables/*.txt` 看起来像乱码 ≠ 一定“加密”

**症状**：`Drop.txt` 等用记事本打开是一长串 `ODAxCQnk...` 类字符，不像 CSV。

**原因**：多为 **序列化/编码后的表**（例如 Base64 层 + 内部结构），不是给人直接阅读的明文；**资源侧**还有大量 Unity `.data` AssetBundle，本来就是二进制。

**与 `filelist.txt` 的关系**：`filelist.txt` 每行形如 `路径|指纹=$大小`，用于 **版本/完整性**，不等于表内字段不可解析。

**教训**：解析之前不要假设“UTF-8 CSV”；需要写 **专用解码器** 或查社区/逆向文档（遵守游戏 ToS、仅本地研究）。

---

## 4. `Drop.txt` 头部形态（283KB 样本）

**样本前缀（用户提供）**：

```text
ODAxCQnkuKrkurrmqKHmi5/mtYvor5UJMglbWzgsODAwMSwxLDEsMTBdLFs4LDgwMDIsMSwxLDEwXSxbOCw4MDAzLDEsMSwxMF0s...
```

**初步观察**：

- 开头 **`ODAx`** 很像 Base64 片段（解码后可能出现可读结构或二进制头）。
- 其后混合 **拉丁字母与汉字片段**（如 `kuKrkurr` 对应 Unicode 经某种编码），整体为 **单行或极少行的大 blob**，与常规“多行表格”不同。

**待办**：在 `extract/` 里实现解码试探（Base64 → 解压/Protobuf 等），**未验证前不要写死字段含义**。

---

## 5. 把表拷进 `data/raw/`（git 外）

**目的**：在仓库内固定一处做实验，避免每次去 `steamapps` 里翻。

**现状**：`data/raw/**` 已在 `.gitignore` 中忽略（**不会进 Git**），避免误传游戏资源。

**复制方式**：

1. **脚本（推荐）**（游戏更新后可重跑）：

   ```powershell
   cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
   .\scripts\copy_game_tables.ps1
   # 或自定义安装根：
   $env:BIDKING_GAME_ROOT = "D:\SteamLibrary\steamapps\common\BidKing"
   .\scripts\copy_game_tables.ps1
   ```

2. **已拷文件一览（核心表）**：  
   `filelist.txt`、`fileVersion`、`fileDiff.txt`，以及 `Tables` 侧：`Drop`、`BidMap`、`Item`、`Hero`、`Item_Type`、`Constant`、`Cabinet`、`Condition`、`BattleItem`、`ItemRestock`、`LevelUp` 等（以脚本列表为准）。

**教训**：大版本更新后 **指纹会变**，重新复制即可；若解析依赖版本号，记录 `data/raw/fileVersion` 与 `filelist.txt` 首行 `Ver:`。

---

## 6. 调试速查

| 问题 | 动作 |
|------|------|
| `import bidking_lab` 失败 | 在仓库根执行 `python -m pip install -e .` |
| 找不到游戏目录 | 设 `$env:BIDKING_GAME_ROOT`，或检查 Steam 库是否非默认盘 |
| 表文件解码失败 | 先确认 `data/raw/tables/Drop.txt` 是否最新复制；再单步试 Base64/ zlib |
| 不要上传 GitHub | 确认未 `git add -f data/raw`；仅提交代码与 `TROUBLESHOOTING.md` |

---

## 7. `Tables/*.txt` 解码结论：Base64 → UTF-8 TSV

**症状**：之前怀疑文件加密 / 压缩 / 二进制。

**实测**（`scripts/probe_tables.py` + `scripts/decode_all_tables.py`）：

- 整个 `*.txt` 文件就是一段 **Base64 字符串**（首字符例如 `ODAxCQnk...`）；
- Base64 解出来直接是 **UTF-8 编码的 TSV**（行=`\n`，列=`\t`）；
- **没有**额外的 gzip/zlib/protobuf 包装；
- 每张表所有行的列数一致（uniform），见下表：

| 表名 | 行数 | 列数 |
|------|------|------|
| BattleItem | 64 | 6 |
| BidMap | 105 | 21 |
| Cabinet | 12 | 14 |
| Condition | 206 | 13 |
| Constant | 83 | 4 |
| **Drop** | 608 | 5 |
| Hero | 20 | 21 |
| **Item** | 1132 | 38 |
| Item_Type | 29 | 8 |
| ItemRestock | 487 | 10 |
| LevelUp | 256 | 8 |

**修法**：用 `bidking_lab.extract.tables`：

```python
from pathlib import Path
from bidking_lab.extract import load_table_rows

rows = load_table_rows(Path("data/raw/tables/Drop.txt"))
print(len(rows), len(rows[0]))   # 608 5
```

**教训**：解码前总是先做"无压缩 / Base64 → UTF-8 → 看 hex / ascii 头"这套三步探针，不要先入为主猜加密。脚本 `scripts/probe_tables.py` 留作以后版本更新时的复检工具。

---

## 8. PowerShell 里中文显示乱码 ≠ 数据坏了

**症状**：跑 `python scripts/decode_table_preview.py Drop`，输出里的中文显示成 `δΈͺδΊΊζ¨‘ζ‹Ÿ` 之类。

**原因**：Windows PowerShell / cmd 默认控制台代码页是 GBK，但我们打印的是 UTF-8 字节。**字节本身没错**，只是控制台把它按错的编码渲染。

**修法**：脚本里强制把 stdout 包成 UTF-8：

```python
import io, sys
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
```

或者在终端执行 `chcp 65001`，但前者更可靠（脚本自带、不依赖会话状态）。
单元测试里中文往返已经通过（`tests/test_tables.py::test_decode_table_text_handles_utf8`），所以**底层是干净的**。

---

## 9. 启动 Streamlit UI（避开 anaconda）

**症状**：在 anaconda Python 下 `streamlit run` 会因为旧版 `pyarrow` 跟 `numpy 2.x` 冲突直接抛 `ImportError`（见第 10 条）。

**目标环境**（本仓库测试通过的版本）：

```text
Python      3.13.3        位于 C:\Python313\python.exe
streamlit   1.57.0
matplotlib  3.10.8
numpy       2.4.4
（不需要 pyarrow，UI 已全部用 st.table）
```

**确认你在哪个 Python**：

```powershell
where.exe python      # 列出 PATH 里所有 python.exe，第一行是默认那个
python -c "import sys; print(sys.executable)"
```

如果第一行返回的是 `...Anaconda3\python.exe`，你有两种选择：

A. **直接用全路径调用 Python 3.13**（不动 PATH，最稳）：

```powershell
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
C:\Python313\python.exe -m streamlit run app\streamlit_app.py
```

B. **临时把 Python 3.13 放在 PATH 最前**（仅本次会话）：

```powershell
$env:PATH = "C:\Python313;C:\Python313\Scripts;$env:PATH"
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
python -m streamlit run app\streamlit_app.py
```

**首次启动前**（如果是新机器或换了 Python 环境）：

```powershell
C:\Python313\python.exe -m pip install -e ".[ui,dev]"
# 这一步会把 bidking_lab 链入 site-packages，并装 streamlit / matplotlib / pytest 等
```

**浏览器会自动打开** `http://localhost:8501`。如果想停止：终端里 `Ctrl+C`。

**修改代码后**：Streamlit 自动检测文件变化，右上角会弹 "Source file changed" → 点 "Rerun" 即可，不用重启。

**教训**：项目里要同时支持 anaconda（数据科学家熟悉）和系统 Python（更新更快）两套环境时，把"启动命令"写进 README/TROUBLESHOOTING 而不是依赖 PATH 假设——别人 clone 下来第一件事就是问 "怎么跑"。

---

## 10. `st.dataframe` 在 anaconda 下崩：pyarrow vs numpy 2.x

**症状**：anaconda 环境跑 `streamlit run app/streamlit_app.py`，打开"读数输入"tab 立刻抛：

```text
ImportError: numpy.core.multiarray failed to import
AttributeError: _ARRAY_API not found
File "pyarrow\lib.pxi", line ...
```

**原因**：anaconda 默认安装的 `pyarrow` 是 numpy 1.x 时代编译的二进制 wheel。`numpy 2.x` 改了 C API，pyarrow 一 import 就崩。而 Streamlit 的 `st.dataframe` 内部强依赖 pyarrow 做 Arrow 序列化（即使你只是显示几行数据）。

**修法（已采用）**：把 UI 里所有 `st.dataframe(...)` 改成 `st.table(...)`。`st.table` 是纯 HTML 渲染、不 import pyarrow，所以完全绕开这个依赖链。代价是分页、排序等交互功能没有；但对几十行的展示表完全够用。

```python
# Before（在 numpy 2.x + 旧 pyarrow 上崩）
st.dataframe(rows)

# After（纯 HTML，没有 pyarrow 依赖）
st.table(rows)
```

**根治法（可选）**：升级 pyarrow 到 17.x+（numpy 2 兼容版本）：

```powershell
C:\Python313\python.exe -m pip install "pyarrow>=17"
```

但既然 UI 现在不需要 `st.dataframe`，就懒得装这个 100+MB 的轮子了。

**教训**：选 Streamlit 控件时优先选轻量控件（`st.table` / `st.metric` / `st.markdown`），重控件（`st.dataframe`、`st.data_editor`、`st.plotly_chart`）会拖一长串依赖，遇到旧 conda env 容易翻车。

---

## 11. `QualityBucketObs(value_range=(0,0))` 触发 `ZeroDivisionError`

**症状**：用户在 UI 红品 section 没填 value，但选了"红品巨物=1"。后台 `_build_session` 给 `QualityBucketObs(value_range=(0, 0), huge_band="1")`，引擎内部算 `value_score = abs(v - mean) / ((hi - lo) / 2)` 时 `hi - lo == 0`，直接除零。

**原因**：`value_range` 在 schema 里允许 `None` 表示"未提供"，但 UI 把 `st.number_input` 的默认 0 当成"用户填了 0"传给了引擎。`(0, 0)` 是合法 tuple 但数学上是退化区间。

**修法（已采用）**：在 UI 层加 `_maybe_red_bucket` / `_maybe_gold_bucket` 辅助函数，只在用户真的填了非零值时才构造 `value_range`：

```python
def _maybe_red_bucket(state, *, allow_huge):
    lo = int(state.get("red_value_lo") or 0)
    hi = int(state.get("red_value_hi") or 0)
    band = state.get("red_huge_band", "none") if allow_huge else "none"
    if lo <= 0 and hi <= 0 and band == "none":
        return None
    return QualityBucketObs(
        quality=6,
        value_range=(lo, hi) if (lo > 0 and hi > 0 and hi > lo) else None,
        huge_band=band,
    )
```

**教训**：UI 默认值（数字 input 通常 0、下拉 "none"）≠ 用户输入。所有"从 UI 转 schema"的胶水代码都要做一次 sentinel-to-None 翻译，否则 schema 里的可选字段会被默认值污染。

---

## 12. `UnicodeEncodeError: 'gbk'` ↔ 中文字符 `\u200b`

**症状**：跑 `python scripts/analyze_maps.py` 打印地图名，崩在：

```text
UnicodeEncodeError: 'gbk' codec can't encode character '\u200b' in position 7
```

**原因**：两个独立问题叠加：

1. PowerShell 默认 console 编码 GBK（第 8 条已记录）。
2. **`BidMap.name` 字段里偶尔混入了零宽空格 `\u200b`**（开发者复制粘贴时带进来的）。GBK 编码集里没有 U+200B，遇到就崩。

**修法**：

```powershell
# 临时把 stdout 切到 UTF-8（治本，配 chcp 65001 或脚本里 reconfigure stdout）
$env:PYTHONIOENCODING="utf-8"
python scripts/analyze_maps.py
```

代码层把零宽空格剥掉：

```python
map_name = bid_map.name.replace("\u200b", "").strip()
```

**教训**：解析游戏内文本时**永远不要假设"中文只有汉字 + 标点"**。零宽空格、unicode BOM、全角空格 `\u3000`、emoji 都可能混进来。脚本入口处统一过一遍 `name.replace("\u200b", "").strip()` 比每处单独处理省心。

---

## 13. `demo_snipe.py` 提示 "Snipe gating failed; no recommendation"

**症状**：第一次跑 snipe 示例：

```powershell
python scripts/demo_snipe.py
# 输出：
# Map: 别墅 2407 ...
# Snipe gating failed; no recommendation surfaced.
```

**原因**：snipe gate 要求**同时**满足三个条件：

1. 仓库 ≥ 120 格（大仓才有秒仓性价比）
2. 玩家给出了 q=1/2/3 (白/绿/蓝) 的 cells 数
3. MC 匹配样本 ≥ 30（采样后 `warehouse ± tol` 还能找到 ≥30 个）

别墅 2407 是中仓地图，平均生成 ~74 格 → 模拟出"仓库 ≥120"的样本极少 → 匹配数不够。换成大仓地图（沉船 2510 是个好选择）+ warehouse 填 140 就触发了。

**修法**：在 `demo_snipe.py` 加诊断输出，把每个 gate 失败的具体原因（哪一条没满足、匹配数多少）打出来，而不是只说 "no recommendation"。

```python
if snipe is None:
    print("Snipe gate failed:")
    print(f"  warehouse_cells = {session.warehouse_cells}  (need ≥ 120)")
    print(f"  low_tier_cells_known = {has_low_tier(session)}")
    print(f"  matching_samples = {n_matched}  (need ≥ 30)")
```

UI 里同样的逻辑也加上了详细 warning（出价 tab 的 "未触发" 卡片）。

**教训**：决策类函数（"要不要推荐"）返回 None / boolean 远不够 debug，至少要带一个 reason field，否则调用方完全不知道怎么调参才能触发。

---

## 14. matplotlib 中文字体在 Streamlit 中缺失（字符变方框）

**症状**：在 Streamlit 里 `st.pyplot(fig)`，图例 / 标题里的中文显示成方框 `□□□`。

**原因**：matplotlib 默认字体 DejaVu Sans 不含 CJK 字符。Streamlit 在服务器端渲染图片再发给浏览器，所以靠浏览器装中文字体不起作用——必须 matplotlib 自己能找到中文字体。

**修法（已采用，简单）**：图表轴标签 / 图例 **用英文**，把中文解读放到图片**下方的 `st.metric` 卡片** / `st.markdown` 文字里。

```python
ax.set_xlabel("Total session value (silver)")    # 英文
ax.set_ylabel("Number of MC sessions")            # 英文
...
st.pyplot(fig)
col1, col2 = st.columns(2)
col1.metric("中位数 P50", f"{int(p50):,}")        # 中文走 Streamlit 文字层
```

**修法（替代，麻烦但图也中文）**：在脚本顶部强制指定中文字体（需要系统装了对应字体）：

```python
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False
```

Windows 自带 Microsoft YaHei，所以这种方案在本机大概率能跑；但部署到 Linux 服务器要装 `fonts-wqy-microhei` 或类似包。

**教训**：图表里的中文是"运行环境依赖"，文字层的中文是"代码自己控制"。能把表达放进文字层就别塞进图，跨平台移植成本差一个量级。

---

## 15. Streamlit "推理一直转圈" 实际是 widget 太多卡渲染

**症状**：用户在 UI 里点了"运行联合推断"按钮后看到 spinner 一直转，等了几十秒还没出结果。

**第一反应**：肯定是引擎慢，DFS 爆炸了。

**实际定位**（命令行直接 profile）：

```powershell
python -c "
import time, sys
sys.path.insert(0,'src')
from bidking_lab.inference.observation import SessionObs, QualityBucketObs
from bidking_lab.inference.joint import joint_top_k_for_session

session = SessionObs(
    map_id=2503, hero='ethan', warehouse_total_cells=140,
    buckets={
        1: QualityBucketObs(quality=1, total_cells=24),
        3: QualityBucketObs(quality=3, total_cells=16),
        4: QualityBucketObs(quality=4, total_cells=50, huge_band='2-3'),
    },
)
t0 = time.perf_counter()
hyps = joint_top_k_for_session(session, k=3, per_bucket_top=6)
print(f'{(time.perf_counter()-t0)*1000:.1f} ms')
"
# 输出：1.7 ms
```

引擎一点不慢。

**真正原因**：上一轮往形状反查字典里加了"每行 +1 / ↻ button + metric"，5 个 shape × 23 件物品 × 3 widget = **~70 个新 widget**。Streamlit 的执行模型是：

- 任何 widget 变化（按钮点击、输入改变）触发 `st.rerun()`
- rerun **从头到尾重新跑整个脚本**，每个 widget 都重新构造、序列化、发到浏览器
- 浏览器拿到 100+ widget 的 diff 后再渲染

100 个 widget 的 rerun 在普通笔记本上轻松 1-3 秒；累计几次 click 就让人误以为后端在算。

**修法（已采用）**：

- 凡是"列表型 + 每行操作"的 UI，改成**一个聚合控件**：例如 5 个形状 × 23 件物品的"每件 +1 button" → 5 个 `number_input`（每形状 1 个）。Widget 数从 ~70 砍到 5。
- 列表展示用 `st.markdown` 而不是 `st.write` 每行单独调用。markdown 一次性渲染整段，不占 widget 配额。

**经验阈值**：

| Widget 数 | 体感 |
|---|---|
| < 30 | 流畅 |
| 30–60 | 略卡，可接受 |
| 60–100 | 明显延迟，用户开始怀疑后端 |
| > 100 | 严重卡顿，体验崩坏 |

**调试技巧**：怀疑前端时，**先用命令行 profile 后端**，确认毫秒级；再用浏览器 DevTools → Network 看 `/_stcore/stream` WebSocket 的 message 大小。message 几百 KB 就基本是 widget 太多了。

**教训**：

1. Streamlit 的性能瓶颈 80% 在前端 widget 数量，不在 Python 后端。
2. 把"每行交互按钮"换成"每组聚合控件"是最有效的优化。
3. UI 设计时先问"用户真的需要操作到这么细的粒度吗"——多数情况下答案是否定的，per-item 操作往往可以换成 per-group。

---

## 16. "填了巨物/估值，但秒仓·放仓输出没变" 不是 bug

### 症状

用户在出价 tab 修改 `紫品巨物数量`、`紫品估值区间`、`金品均格` 等字段，再点 *运行出价推理*，结果**完全相同**。第一反应是"共享采样把状态卡死了"。

### 原因

`compute_snipe_recommendation` / `compute_pass_recommendation` 在文档和实现里都**只对 `(warehouse_total_cells, purple_total_cells)` 做 conditioning**（见 `src/bidking_lab/inference/snipe.py:147-166`）：

```python
purple_obs = session.buckets.get(4)
purple_cells_obs = purple_obs.total_cells if purple_obs is not None else None
# 后面循环里只用 warehouse_total_cells 和 purple_cells_obs 过滤
```

其它字段（huge_band / value_sum / avg_cells / outline）都不在 filter 里。这是**故意的**：每加一个维度就乘上一层匹配率，2000 个样本很快就被过滤到只剩个位数，p25/p75 区间会噪声爆炸，gate 函数判 `len(values) < min_matching_samples` 直接 return `None`，反而让用户看不到任何推荐。

### 修法

不改逻辑。在 UI 顶部加一条 `st.warning`，明确告诉用户**当前 conditioning 集合**，并说明其它字段只在"实验性联合推断"里生效。

未来若想让 huge_band 真正参与，正确路径是：

1. 先扩 `sample_session_truth` 输出 `huge_band` summary
2. 再在 `compute_snipe_recommendation` 里加 fallback 链（窄过滤不够样本时回退到宽过滤）
3. 加单测覆盖"高/低样本数 → 用哪一档过滤"

### 教训

1. **UI 输入字段≠引擎全用到** — 哪些字段实际进了哪个推断要在 UI 旁边标清楚。
2. **Monte-Carlo 的 conditioning 维度有上限** — 不是想加就加，匹配率会快速塌掉。
3. **"看着像 bug" 第一步先读源 + caption**，比改代码便宜。

---

## 17. Streamlit ROI tab 慢的真正原因不是计算，是没缓存

### 症状

ROI tab 切换地图后第一次点击要 30-60s，**同一地图再点也是 30-60s**。用户怀疑算法慢。

### 原因

`compute_tool_roi(map_id, tool_kit, hero, n_trials, ...)` 是 leave-one-out MC，**纯函数**：相同 (map_id, tools, hero, n_trials, seed) 一定产出相同结果。但 streamlit 每次 rerun 都重新 `compute_tool_roi(...)`。

确认输入与会话观测**完全无关**（不读 `SessionObs`）→ 缓存 key 极简，命中率会非常高。

### 修法

```python
@st.cache_data(max_entries=16, show_spinner=False)
def _cached_tool_roi(map_id, *, tools: tuple, hero: str, n_trials, seed, per_bucket_top):
    maps_, drops_, items_ = _load_tables()
    return compute_tool_roi(map_id, tool_kit=list(tools), ...)
```

注意：

- key 用 `tuple(ETHAN_KIT)`（list 不可哈希）；
- `max_entries=16` 够放 8 张图 × 2 种 hero。

效果：首次 30-60s，之后切回**瞬发**。

### 教训

1. 任何**与输入 widget 无关**的重计算都该用 `@st.cache_data` 包一层。
2. 决定能不能加缓存的关键问题是"这个函数是不是纯函数"，而不是"它快不快"。
3. ROI 这种"离线指标"和"在线推断"应该在 UI 里明确分开提示，避免用户误以为它会随读数变。

---

## 18. `st.number_input` 默默吞掉尾零 → avg_cells 引擎 AttributeError

### 症状

UI 上 `紫品均格` 字段填 `2.90`，提交后引擎照样返回 "32/11 跟 29/10 都是候选" 这种本应被尾零规则排除的结果。打开"实验性联合推断 tab" 点运行后直接崩：

```
AttributeError: 'float' object has no attribute 'raw'
```

### 原因

- `st.number_input(..., format="%.2f")` 看起来支持两位小数，但**返回的永远是 Python `float`**。
- `2.90`、`2.9` 在 float 域里是同一个数（其实是 `2.8999999999999999...`），尾零信息在控件级别就丢了。
- 我们 dataclass 上写 `avg_cells: Reading | None`，但 Python 不强制类型 — 把 float 塞进去也能构造成功。
- 一旦联合推断引擎走到 `enumerate_candidates(bucket.avg_cells)`，它访问 `.raw` 触发 `AttributeError`。

### 修法

`avg_cells` 必须经过 `parse_reading()` 显式包成 `Reading`：

```python
state["purple_avg_raw"] = c2.text_input(
    "紫品均格", value="", placeholder="例 2.90 或 3.43",
    help="按游戏原样填。「2.9」=精确，「2.90」=被舍入过的近似",
)
# 后续：
avg = _try_parse_reading(state.get("purple_avg_raw"))   # None on parse error
buckets[4] = QualityBucketObs(quality=4, avg_cells=avg, ...)
```

把 `number_input` 换成 `text_input` 才能精确保留尾零。

### 教训

1. **UI 控件返回类型 ↔ dataclass 字段类型** 必须有一道 round-trip 校验，否则 dataclass 的类型标注会变成谎言。
2. 任何"游戏显示语义带歧义"的字段（如 `2.9` vs `2.90`）都不能用 `number_input` — 它会把语义压平。
3. 这个 bug 在 streamlit UI 引入后存活了几个 commit 没被发现，因为：
   - 实验性 tab 默认隐藏（C-20），用户从不点；
   - snipe MC 不消费 avg_cells，UI 主流程"看着 ok"。
   一旦上游字段进了 dataclass 但下游某条引擎路径才会真用，就要写一个 "dataclass 能否被消费" 的最简 round-trip 单测。

---

## 19. 道具命名错位：代码里的"精品/珍品"≠ 游戏里的术语

### 症状

ROI tab 输出 "珍品估价 ROI = +3.09 for Aisha"。用户实测后指出：
> 优品是紫色的，珍品是扫描红色的好像，极品才是金色的，之前艾莎都是配看金色格子数或者总价格的。

代码里的 `珍品估价` 其实是绑到 `q=5`（金品），跟游戏术语"珍品 = 红品工具"完全相反。结果是：
- ROI 报表数值是对的（金品估值挽回 ~108K silver）
- 但**给玩家看的标签是误导的**（玩家以为是红品工具）
- `珍品扫描`、`珍品均格` 也都对应错了品质

### 排查

decode 游戏的 `BattleItem.txt`（base64 → TSV），从 100100~100135 取出全部 6 类工具，对照描述列：

| 100126 | 珍品估价 | "显示**红色**品质藏品总价值" |
| 100124 | 优品估价 | "显示**紫色**品质藏品总价值" |
| 100125 | 极品估价 | "显示**金色**品质藏品总价值" |

跟代码里的命名完全错位。

### 真值表

| 前缀 | 操作品质 | 颜色 |
|---|---|---|
| 普品 | q=1+2 | 白+绿 |
| 良品 | q=3 | 蓝 |
| **优品** | **q=4** | **紫** |
| **极品** | **q=5** | **金** |
| **珍品** | **q=6** | **红** |

"精品"根本不存在于游戏。

### 修法

系统重命名（C-25）：
- `synth_readings.TOOL_SPECS`：精品* → 优品*、珍品* → 极品*；**新增** q=6 红品三件（珍品扫描/估价/均格）
- 同步：`observation.{ETHAN/AISHA}_LOADOUT`、`app/streamlit_app.{ETHAN_KIT, AISHA_KIT, ALL_TOOLS, TOOL_EN_LABEL, TOOL_DEFAULT_PRICE, TOOL_PRICE_OVERRIDABLE}`
- 测试/脚本/notebook 一并 batch replace；全 202 单测继续绿

### 教训

1. **代码里的领域术语应该跟原始数据源对齐**——这里就是 `BattleItem.txt` 的 `name` 字段，不要凭"感觉"映射。
2. 这次的语义实质上是对的（绑定到正确品质 bucket），所以单测没炸；**只有外部用户能发现的命名错位需要外部 review**。
3. 重要术语 + 多文件用 → 集中定义一份常量映射 + replace_all 重命名，比手 PR 几个文件改半天稳。
4. **decode 一次原表 + grep "扫描|估价|均格" 30 秒** 就能确认这种映射，下次类似怀疑直接做 probe，不要先改代码后纠错。

---

## 20. ROI 引擎"总仓储空间"= 0 不是 bug 也不是 feature，是缺少噪声模型

### 症状

C-24 端到端验证 Aisha + 别墅 2407（含 R1-R4 轮廓加料）：
```
珍品估价（实际是极品估价）  ROI = +3.091
总仓储空间                  ROI = +0.000
```
用户：
> 总仓储是 0 吗，是因为价格原因吗？玩家的格数估计是有误差的，这个可能没考虑在内。

### 排查

`compute_tool_roi` 走 leave-one-out：full kit run 跟去掉 `t` 的 LOO run 对比。
- Full kit 含总仓储 → `obs.warehouse_total_cells = truth.warehouse_total_cells`（精确）
- LOO 去掉总仓储 → `obs.warehouse_total_cells = None` → 引擎调 `session.warehouse_capacity()` → 走 fallback **常数 159**

后果：LOO 估计跟 truth 差距巨大（truth 70 vs fallback 159 这种），full 跟 truth 完全一致。差距听起来应该是大正数（总仓储有用！），但价值估算流程是先用 cells 锁 bucket 候选；当 cells 容量从 70 → 159 时，候选空间反而**多挤进一堆不可能的高 cells 配置**，joint 选 top-1 时偶尔反而离 truth 更远——但更多时候，由于其他 bucket 的硬约束（紫品估价、轮廓加料）已经把 q=1..4 cells 死锁住，capacity 大小不影响 top-1 选择 → 价值差为 0。

### 真实原因

引擎默认"不带总仓储 = 玩家完全不知道仓库多大 = 用 159 兜底"。但现实里玩家**用眼睛能数出仓库大小** ± 几格。这个噪声模型完全没建模。

### 修法

`compute_tool_roi` 新增参数 `player_warehouse_noise_std: float = 10.0`。每个 MC trial：
1. 独立采一次玩家眼估值 `approx = truth.warehouse_total_cells + N(0, σ)`
2. 所有 LOO（包括去掉总仓储的那次）都用这个 `approx` 写到 `obs.warehouse_total_cells_approx`
3. Full kit（含总仓储）继续用精确 truth

效果（Aisha + 别墅 2407）：

| σ (cells) | 总仓储 ROI |
|---|---|
| 0  | +0.000  ← 玩家完美眼力 → 工具确实无价值 |
| 5  | +0.080  ← 老练玩家 |
| 10 | +0.446  ← 默认（现实多数玩家） |
| 15 | +0.924  ← 新手 |

总仓储在现实噪声下 ROI 正常 ~0.45，验证了"玩家会选择带总仓储是有原因的"。

### 教训

1. **ROI 的 LOO baseline 必须模拟真实"没有这件道具时玩家拿到的信息"**，不能用引擎兜底的 sentinel 值（这里是 159）。否则 ROI = 计算的是 sentinel 漏洞，不是工具价值。
2. 任何"没观测就 fallback 常量"的字段在 ROI 评估里都要打这种补丁；否则会出现"工具看起来无用、其实是 baseline 太聪明"的反直觉信号。
3. 把这种参数暴露到 UI 滑块比硬编码更好——用户能直接看到\"我假设眼估多准 → 工具 ROI 多少\"的灵敏度。

---

## 21. Snipe gate 在小样本场景静默返回 None

### 症状

`scripts/demo_snipe.py` 跑场景 A（伊森 + 沉船 145 格 + 优品均格 2.90 + 1 红巨物）：
```
Both snipe and pass gates returned None. Reasons: ...
```
用户先前观察："场景 A 只差 1 个样本就触发"。问：能不能差一点的情况下返回带警告的结果，而不是静默返回 None？

### 排查

`compute_snipe_recommendation` 的逻辑：
1. 优先取 purple + warehouse 双条件子集，需要 `≥ min_matching_samples`（默认 30）
2. 否则降级为 warehouse-only 子集，仍需 `≥ min_matching_samples`
3. 都不够 → return None

145 格在沉船分布尾部，n=3000 trials 里只能采到 ~29 个匹配样本——卡在 30 阈值下方 1 个，gate 静默失败。

### 修法

新增三阶 fallback：
```python
if purple ≥ 30:   # 高置信
    ...
elif warehouse ≥ 30:   # 正常
    ...
elif warehouse ≥ 10:   # NEW: 低置信（min_matching_samples_relaxed）
    low_confidence = True
else:
    return None
```

`SnipeRecommendation` / `PassRecommendation` 新增 `low_confidence: bool` 字段，rationale 里挂 "⚠️ 样本仅 N 个" 警告。Streamlit 出价 tab 在 `low_confidence=True` 时用 `st.warning()` 替换 `st.success()`，玩家一眼能看到"这个数仅供参考"。

实测场景 A：现在返回 `snipe_max = 1,761,306, samples = 29, ⚠️LOW-CONF`，既不丢推荐也告知不可靠。

### 教训

1. **硬阈值 + 静默 None** 是最差的 UX。要么放宽阈值返回带警告的结果，要么显式告诉用户为啥拒绝。两者中 streamlit UI 偏好前者（玩家能根据警告自己判断要不要用）。
2. 类似"阈值附近卡 N=29/30"是常见场景；任何 MC-based 推荐都该考虑这种三阶 fallback。
3. 新增 dataclass 字段（这里是 `low_confidence`）需要扫一遍所有 `XxxRecommendation(...)` 构造点 — grep `XxxRecommendation\(` 找全比凭记忆改稳。

---

## 22. BidMap 静态字段 ≠ session 动态 hint

### 症状

用户先前提："地图字段，其实有用的信息不多，有时候会给 9 件均价、几件总价"。问能不能把这些 hint 抓出来塞 UI prefill。

### 排查

decode `BidMap.txt` 105 行全表 + dump 别墅 2407 / 沉船 2510 / 集装箱 2102 的全字段：

| col | 内容 | 已用？ |
|---|---|---|
| 7 | category（101 快递 / 104 别墅 / 105 沉船） | ✓ |
| 10 | entry_fee_silver（10/15/20/25/30） | ✓ |
| 13 | per-round timer `[40,40,...]`（40/50/60s） | 不需要 |
| 14 | starting_budget_silver | ✓ |
| 16 | `[9999, drop_pool_id, items_min, items_max]` | ✓（min/max 已用） |
| 18 | bid_price_ladder（5 轮价格梯度） | ✓ |
| 19 | round_category_hints（5 元素 category id） | ✓ |
| 9  | value_tier_ui（"ui_value_low/higher/high"） | parser 抓了，UI 没显示 |

结论：所有**静态**字段 parser 早就抓全了，但 Streamlit UI 没显示。

### 真实原因

用户问的 "9 件均价 / 几件总价" 是 session 开局后**动态生成**的，不在表里。BidMap 给的都是 session-agnostic 的设定参数（件数范围、预算、价值档次、可能出现的 category）。

### 修法

在 Streamlit 侧边栏选完地图后，加 `st.expander("📍 地图静态信息（仅参考）")`，显示：件数范围 / 起步预算 / 入场费 / 价值档次 / 轮号分类提示（"R1=武器 / R3=时尚"等格式化）/ 出价梯度。**Caption 明确说：动态 hint 请到读数输入 tab 手动填**，避免用户混淆。

### 教训

1. **先 probe 后建模**。30 秒解码 + 一个 dump 脚本就能知道"有什么字段、字段长啥样、动态 vs 静态"。
2. parser 抓了的字段不等于 UI 暴露的字段——这两个面之间要有意识地审计，否则 schema 里躺着的信息永远不会到用户面前。
3. 把"为什么动态 hint 必须手输"写在 caption 里能预防一遍又一遍的用户疑问。

---

## 23. 分析估算红品自动推断在 bucket 未填全时仍把残差归红品

### 症状

仓库 80 格、白绿 15、蓝 30、紫 16（含 1 巨物），金品**未填写**。系统直接把剩余 19 格全部归为红品，估值飙到 ~100 万 silver——但玩家本地实测大致 10-20 万。

### 原因

`compute_analytical_estimate` 里的红品自动推断只检查"红品 bucket 是否已存在"，没检查"其它非红 bucket 是否都填全了"。如果金品没填，系统把"未知格数"全部当成"必然是红品"——红品先验是 50,000 silver/格，把 19 格×50,000 = 95 万塞进估值，误差爆炸。

`_build_session` 里的同名"自动推断红品"逻辑虽然有 `all_buckets_filled` 检查，但下游 `compute_analytical_estimate` 走的是独立路径，**没继承同样的检查**。

### 修法

`compute_analytical_estimate`：

```python
required_non_red = {1, 3, 4, 5}
provided_qs = set(obs.buckets.keys())
all_non_red_filled = required_non_red.issubset(provided_qs)
red_auto = (6 not in known_cells and red_cells > 0 and all_non_red_filled)
```

未填全时，把残差以**「全金到全红」的范围**显示给玩家，而不是直接当红品。例如 9 格未分配 → `9×9400 ≈ 8.5万 ~ 9×50000 = 45 万`，区间宽但不再误导。

UI 配套加 warning：「⚠️ 剩余 X 格未分配（金品未填写），无法判断红品占比。估值区间已按"全金"到"全红"范围显示。」

### 教训

1. **不同代码路径里相似的"自动推断"逻辑必须同步**——`_build_session` 和 `compute_analytical_estimate` 都做红品推断，写第二份的时候很容易漏掉前一份的安全检查。
2. **未填的 bucket 不等于零格 bucket**。"没数据"和"数据为零"在 UI 层和后端都要明确区分——零是断言，未填是不知道。
3. 高单价品质（红=50,000/格）容易把估值算飞，相关推断必须有"是否所有约束都到位"的 gate。

---

## 24. `value=0` 默认值导致"未提供"和"确认为零"无法区分

### 症状

UI 上「金品总格数」、「金品件数」、「紫品估价」、「红品价值上下限」等字段默认显示 `0`。玩家可能：

1. 真的看到了"金色 0 件"（地图直接告诉过），希望系统当成确认；
2. 没填任何东西，想让引擎自己推断。

但 `value=0` 让两种意图视觉上完全一样，后端也只能按"未提供"处理（因为按"确认为零"处理会把残差全推给红品，看 #23）。

### 原因

`st.number_input(..., value=0)` 的 0 是合法值，无法表达"留空"。所有 `state.get("gold_cells") or 0` 之类的写法把 0 也当 falsy 处理，进一步丢失信息。

### 修法

把所有"可选"数值字段改成：

```python
state["gold_cells"] = st.number_input(
    "金品总格数",
    min_value=0, max_value=80,
    value=None, step=1,
    placeholder="可选",
    help="留空 = 未提供；填 0 = 确认无金品。",
)
```

后端按 `None` vs `0` 分别处理：

```python
cells_raw = state.get("gold_cells")
cells = int(cells_raw) if cells_raw is not None else None
# bucket.total_cells = cells (允许传 0 进去当作"确认零格")
```

涉及的字段（一次性全改）：`wg_cells / blue_cells / purple_cells / purple_count / purple_value / gold_cells / gold_count / gold_value / red_cells_total / red_value_lo / red_value_hi`。

### 教训

1. **可选数值字段必须用 `value=None` + `placeholder`**，永远不要拿 0 当默认值。
2. 后端读取时 `state.get(k) or 0` 是反模式（吞掉合法 0 输入），必须显式 `is None` 判断。
3. 用户的 mental model 里"没填"和"填 0"是两件事——UI 必须支持这个区分。

---

## 25. `compute_analytical_estimate` 没用枚举，用户填的 `value_sum` 被忽略

### 症状

紫品填了 `value_sum = 86,490` + `huge_band = "1"`（确认 1 个紫色巨物），但分析估算的明细显示 **「紫 12格×2500/格」**——只用了"1 个巨物的最小占用 12 格"，把估价信息当装饰。86,490 / 2,500 ≈ 34.6 格，差距巨大。

### 原因

老的 `known_cells` 构造逻辑：

```python
if b.total_cells is not None:
    known_cells[q] = b.total_cells
elif b.huge_band != "none":
    known_cells[q] = b.min_huge_cells()  # 12 for purple
# value_sum、count、avg_cells 完全没看
```

但项目里早就有 `candidates_for_bucket` 暴力枚举器（`observation.py`），它综合考虑 `value_sum / count / avg_cells / huge_band / 仓库容量上限 / 均格先验`，能给出非常精确的 top-1 候选。**只是分析估算路径完全没调用它**。

### 修法

在 `compute_analytical_estimate` 里增加二次枚举 pass：

```python
for q, b in obs.buckets.items():
    if b.total_cells is not None or q in (1, 2):
        continue
    has_info = (
        (b.value_sum is not None and b.value_sum > 0)
        or b.huge_band != "none"
        or b.avg_cells is not None
        or b.count is not None
    )
    if not has_info:
        continue
    cands = candidates_for_bucket(
        b, warehouse_capacity=warehouse,
        other_known_cells=explicitly_known,
    )
    if cands:
        known_cells[q] = cands[0].total_cells
        inferred_count[q] = cands[0].count
```

明细输出里标注数据来源：「紫 35格×2471/格 → 51,894~129,735（用户估价）（由枚举推算→10件）」。

### 教训

1. **同一个语义有两条计算路径时，要么共享逻辑，要么明确写"为什么这条路径要简化"**——这里两条路径（候选预览面板 vs 分析估算）都该用同样的枚举器，差异只是展示形式。
2. 用户填的所有字段都该被消费；如果有字段被丢弃，UI 要么不显示该字段、要么明确说"这个不参与本次推断"。
3. 暴力枚举在我们的规模（紫品候选 ~50 个）几乎无成本，没理由用更弱的近似。

---

## 26. `_build_session` 红品残差不用枚举，只填 count 的 bucket 被吞

### 症状

仓库 135、白绿 40、蓝 26、紫 37（含巨物）、**金品只填件数=5**。系统跑出来红品=32 格、金品 0 格。但 5 件金品按平均 4.4 格/件应该 ~22 格，红品才 ~10 格。

### 原因

`_build_session` 里的红品残差计算：

```python
# 老逻辑：只看 total_cells 和 huge_band
known_sum = sum(b.total_cells for b if b.total_cells > 0)
              + sum(b.min_huge_cells() for b if b.huge_band != "none")
red_residual = warehouse - known_sum  # 132 - (40+26+37) = 32
buckets[6] = QualityBucketObs(total_cells=red_residual)
```

`count=5` 没有 `total_cells`、没有 `huge_band` → `known_sum` 把它当成 **0 格**贡献。然后红品被错算为 32 格塞进 buckets。

后续 `compute_analytical_estimate` 跑二次枚举（修复 #25）时，`other_known_cells = 40+26+37+32 = 135 = warehouse`，**金品的可用容量被红品挤光**，枚举返回空，金品在最终明细里彻底消失。

### 修法

`_build_session` 用枚举先估格数，再算残差：

```python
explicit_sum = sum(b.total_cells for b if b.total_cells > 0)
derived_sum = 0
for q, b in buckets.items():
    if b.total_cells is not None or q in (1, 2):
        continue
    if has_info(b):  # value_sum / huge_band / avg_cells / count
        cands = candidates_for_bucket(
            b, warehouse_capacity=warehouse,
            other_known_cells=explicit_sum + derived_sum,
        )
        if cands:
            derived_sum += cands[0].total_cells
known_sum = explicit_sum + derived_sum
red_residual = warehouse - known_sum  # 现在金品贡献 22 格 → 红品 10 格
```

### 教训

1. **bug 链条**：上游错把可推断字段忽略 → 下游再补救已经太晚（容量被错误占用）。修要修源头。
2. 当一段计算逻辑被两个模块共享语义但各自写了一份时，**先抽公共 helper 再各自调用**，否则迟早会漂移。
3. **测试用例要包含"只填部分字段"的组合**——本 bug 在"全填" or "全空"两种极端情况下都不会暴露。

---

## 27. `HUGE_CELLS_PER_QUALITY` 阈值与 UI 文案不一致

### 症状

UI 文案说"≥ 12 格 算巨物"，但 `HUGE_CELLS_PER_QUALITY = {4: 16, 5: 18, 6: 16}` —— 紫色 16 格才算、金色 18 格才算。结果：

- 玩家选「紫品巨物=1个」，引擎估出 16 格紫品，但实际游戏里 12 格的可折叠盾就是巨物
- 12-15 格的金品（防弹衣、波斯毯、机柜等）按代码"不算巨物"，但 UI 上玩家看到一个不规则大轮廓 100% 当巨物报上来

### 原因

`HUGE_CELLS_PER_QUALITY` 是早期估值的硬编码，按"游戏里最常见的巨物形状"取值（16=4×4 屏风类，18=3×6 游艇）。但实际数据 `BIG_ITEMS_BY_SHAPE` 里 12 格、15 格、16 格、18 格、20 格都有巨物，UI 文案后来改了但常量没跟上。

### 修法

`observation.py`：

```python
HUGE_CELLS_PER_QUALITY: dict[int, int] = {4: 12, 5: 12, 6: 12}
```

`quality_priors.py`：金色巨物 `PER_CELL_VALUE_HUGE[5]` 从 6,000 调到 7,000/格（按 12-18 格金品的加权中位数重新算）。同步更新相关测试和 UI help 文本。

### 教训

1. **常量和文案必须用同一个数据源**，否则迟早会 drift。这里 `HUGE_CELLS_PER_QUALITY` 应该从 `BIG_ITEMS_BY_SHAPE` 派生（取最小巨物形状的 cells），而不是硬编码。
2. 数值常量改动要扫所有用例 + 测试 + UI 文本，可以用 grep 把所有出现的 `12 \| 16 \| 18` 列出来再人工审计。
3. 玩家口述跟代码常量对不上是常态，**优先信玩家**——他们看到的是游戏，代码是我们脑补的模型。

---

## 28. `huge_cells_override` 已实现但 UI 从未暴露 → 玩家无法精确锁定具体巨物

### 症状

`QualityBucketObs.huge_cells_override` 在 `observation.py` 里早就支持，`huge_cells_per_item()` 也优先用 override。但 UI 上「巨物数量」永远只能选 `无 / 1个 / 2-3个 / 4+个`——只能给数量段，不能告诉引擎"这个 1 个具体是 18 格的游艇"。

实际游戏里，单人郊游快艇（6×3=18 格）是金品里**唯一**的 18 格物品，玩家看到这个轮廓 100% 能识别。同理紫色防护盾（12 格唯一）。但这些信息没有任何 UI 通道可以告诉引擎。

### 原因

UI 设计时只考虑了模糊场景（"我看到 1 个大紫物，但不确定是哪件"），**漏掉了"我能精确识别"的高信息场景**。导致后端有能力但前端不暴露。

### 修法

在 huge_band 选项后追加 `BIG_ITEMS_BY_SHAPE` 中该品质的所有具体物品作为新选项：

```python
def _huge_options_for_quality(q):
    options = list(HUGE_BANDS)  # ["none", "1", "2-3", "4+"]
    labels = dict(HUGE_BAND_LABELS)
    for item in _items_for_quality(q):  # 紫:1 / 金:7 / 红:12
        key = f"item:{item['name']}"
        options.append(key)
        labels[key] = f"★ {item['name']} ({item['cells']}格·{item['value']:,})"
    return options, labels

def _resolve_huge_selection(raw, quality):
    # "item:xxx" → ("1", item.cells)；其它原样返回
    ...
```

bucket 构造端调用 `_resolve_huge_selection` 解析为 `(huge_band="1", huge_cells_override=cells)`。这样下游所有现有逻辑（`min_huge_cells()` → `candidates_for_bucket` → `_build_session derived_sum` → `compute_analytical_estimate`）**自动消费**新信息，零额外接线。

### 教训

1. **后端能力先行 + 前端追赶**经常导致功能"半成品"——`huge_cells_override` 字段写了一年没人能填，等于没写。
2. 数据驱动的 UI 选项（从 `BIG_ITEMS_BY_SHAPE` 自动派生）比硬编码下拉菜单可维护得多。
3. 给可选项加视觉前缀（`★ 物品名`）能立刻让玩家区分"通用档"和"精确识别档"，不需要额外说明文档。

---

## 29. 放仓推荐忽略红/金 bucket 约束 → 给红有大件的高价仓也建议放

### 症状

输入 `仓库=80, 白绿=20, 蓝=15, 紫=24, 金 count=1+v=24435, 红 huge=1`，引擎仍然显示「🛑 放仓推荐 — 超过 405,960 就放，仅是全图均值的 98%」。但红 huge=1 明显暗示有大件红品（≥12 格），仓库期望价值远高于全图均值，"放仓"是误导。

同 case 不给红 huge 跑一遍 → 阈值降到 ~370K，与异常 case 几乎相同，证明红信息根本没进 MC 过滤。

### 原因

`compute_pass_recommendation` / `compute_snipe_recommendation` 的 MC 过滤只走两层：

```python
if abs(truth.warehouse_total_cells - wh) > warehouse_tolerance: continue
if purple_cells_obs is not None and abs(tp_cells - purple_cells_obs) > purple_tolerance: continue
```

红 / 金 bucket 的 `huge_band` / `value_range` 完全没出现在过滤条件里。结果中位仓价是"warehouse=80 + purple=24 的所有可能仓库的均值"——绝大多数没红 huge，把均值压到 ~360K。

量化（H29 audit, map_id=2403, n=1000）：

| 过滤层级 | n | p50 |
|---|---|---|
| 当前：warehouse + purple | 104 | **358K** |
| 应该：+ red_huge≥1 | 12 | **616K** |

### 修法

两步：

1. **新增 cond_red tier**：在原 cond_warehouse / cond_purple 之上加一层 cond_red，同时过滤红 `huge_band` 和 `value_range`。tier 选择优先 cond_red（n≥30）→ cond_red 宽松（n≥10，标 `low_confidence`）→ cond_purple → cond_warehouse → 宽松 cond_warehouse。红约束样本天生稀，所以放宽阈值到 `min_matching_samples_relaxed`。

2. **新增 `suppress_above_ratio` 参数**（默认 1.0）：当条件中位价 / 全图中位价 > 1.0 时，整个 `compute_pass_recommendation` 返回 None。语义：玩家已经把仓库锁定为"高于平均"了，"超过 X 就放"的提示是反向的。

`compute_snipe_recommendation` 做同样的 cond_red 接入（秒仓本身是"高仓位才推"，不需要 ratio 守卫）。

### 教训

1. **MC 过滤要对称地消费 obs**：观察值进了 SessionObs，过滤逻辑就该全用上，否则等于免费信息被丢弃。
2. 对"建议性"输出（推荐值），始终留一个**反向 sanity check**——这次是 `ratio > 1.0` 直接 suppress。否则数据正向时能给合理建议，数据反向时只会"建议得很有信心、也很错"。
3. 红约束样本稀（n=10-20）是常态，min_matching_samples 不能跟主路径一样硬卡 30；用 relaxed 阈值 + low_confidence 标记是更稳的折中。

### 已知遗留（未在本 checkpoint 修）

- 同输入两次跑结果不同：tier 切换的硬阈值在边界附近会跨档，导致放仓有时返回有时 None。改进方向：连续置信度权重 / bootstrap CI。
- 小红仓漏报：79 格 / 红 1-2 cells / 总仓 22w 不触发，因为 `low_fraction ≥ 0.4` 是必要条件而当前红少时低品占比可能不到 40%。
- ratio 守卫粗糙：`> 1.0` 一刀切。改进方向：`0.85 < ratio < 1.05` 区段标"中等仓位、自由发挥"。

---

## 30. 秒仓/放仓 UI 下线（实验功能）

### 症状

实战反馈：同输入多次运行秒/放仓卡片有时出现、有时消失；红 huge=1 的高价仓仍可能建议放仓（C-30 已部分修）；79 格 / 红 1–2 格 / 总仓 ~22w 该放却未触发。用户易被误导。

### 原因

`compute_snipe_recommendation` / `compute_pass_recommendation` 依赖稀疏 MC 子样本 + 硬阈值 tier（30 / 10）+ 粗粒度 `low_fraction` 门控；与主路径「仓库价值区间 + bucket 后验」不同步。

### 修法（2026-05-17）

- `app/streamlit_app.py`：`_ENABLE_SNIPE_PASS_HINTS = False`，UI 显示与未知巨物相同的 **🧪 实验功能，暂未接入推断接口** 说明。
- **不删** `src/bidking_lab/inference/snipe.py` 与 `tests/test_snipe.py`。
- 恢复：改 flag 为 `True` 并重启 Streamlit。

### 待修 backlog（见 PROGRESS C-31）

tier 平滑、小红仓门控、ratio 守卫细化、紫/金 huge 进 cond 链等。

---

## 31. 均价/均格只收紧枚举、不进 MC — 设计如此

### 症状

用户同时填 `value_sum` + `avg_value` + `huge_band` + `avg_cells` 后，候选列表骤减甚至 0 条；但 MC 分位图似乎「没用到」均价/均格。

### 原因

**分层设计**：

- **MC 后验**（`filter_truths_by_obs`）：cells / count / value_sum / value_range / huge **件数 band**。
- **枚举**（`candidates_for_bucket`）：在上述之上加 avg_cells、avg_value、物理格数上限、Item-DB boost；用于预览锁 (cells,count) 与分析估算推格数。

`avg_value` 来自地图动态 hint，与 Drop 池抽样分布未必一致；若硬塞进 MC 会大量「过滤后零匹配」。

### 是否 bug？

**不是 bug，是 MVP 取舍。** 若产品要求「填了均价 MC 也要跟」，需新增 `avg_value` 软约束或后验加权（Phase 2）。

### 联合填写过狠时

- 枚举路径：多字段 **AND** 硬过滤 → 正常但激进。
- **已缓解（C-31b）**：`active_reading_constraint_count >= 4` 时仅把 `avg_value` 容差从 ±10% 放宽到 ±18%（有 `value_sum`）或 ±25%→±35%（无总价）；**MC 与采样次数不变**。

### P2「均价进 MC」要不要做？

**建议不做，也不必加 UI 勾选项。** 均价来自地图 session hint，与 Drop 池 MC 样本分布常不一致；硬塞进 `filter_truths_by_obs` 会复现「过滤后零匹配」。当前分层（MC 用 cells/count/value/huge 件数；均价只收紧枚举）是刻意设计。

---

## 32. MC fallback 重建 bucket 丢失 `huge_cells_override`

### 症状

OBS #31 审计：玩家选了 `★ 具体巨物（18 格）`，若 MC 走 `adaptive_filter` 的 warehouse-only fallback，`hard_buckets` 重建时只保留 `huge_band`，`huge_cells_override` 变 0 → `huge_cells_per_item()` 退回品质默认（金 12）。

### 原因

`adaptive_filter` fallback 分支用 `QualityBucketObs(quality=..., huge_band=...)` 浅拷贝，漏字段。

### 修法（C-32, 2026-05-17）

- 抽出 `posterior._fallback_hard_buckets(obs)`，在 `value_sum` / `huge_band` 重建时拷贝 `huge_cells_override`。
- 单测 `TestFallbackHardBuckets::test_preserves_huge_cells_override`。

### 实际影响与风险

- **当前 UI**：枚举与分析估算读完整 `session`，**通常无可见变化**；MC 过滤仍只看 `huge_count` band，不看单件格数。
- **价值**：fallback 路径对象与玩家输入一致，避免日后把 `fallback_obs` 接到更多模块时 silent 退化。
- **风险**：极低（只补字段拷贝）；不会单独收紧 MC。

### 教训

修「硬约束保留」时要 **整对象字段清单** 对照 `QualityBucketObs`，不能只抄审计表里出现的字段名。

---

## 33. 各字段对 MC / 枚举的影响矩阵（设计预期）

> 用于判断「改了一个输入，为什么 MC 分位 / 候选列表变了」——**是否符合设计**。

| 改动 / 字段 | 作用路径 | 会不会拉偏估计 | 设计结论 |
|-------------|----------|----------------|----------|
| **C-32** fallback 保留 `huge_cells_override` | 仅 MC 样本不足时的 warehouse fallback | 正常对局几乎无感 | ✅ 一致性修复；**不需改算法** |
| **★ 具体巨物** | 枚举 + 分析估算（`huge_cells_override`） | 选 ★ 后格数/候选变 — **预期内** | ✅ 玩家须选 ★ 才按 18 格游艇等 |
| **巨物 band「1个」无 ★** | 枚举下限 = 最小占格（紫10/金红12）；MC 只过滤件数 | 非游艇场景合理；游艇价+只选「1个」会对不齐 | ✅ **设计如此**；文案已说明 |
| **Item-DB boost**（`composite×0.01`） | **仅**枚举排序 | 件数=1 且总价命中单品时候选置顶；**不改 MC** | ✅ 符合设计；误填总价会「看起来锁死」小件 — UI 已标注 |
| **红 `total_cells=0`** / 勾选「已确认无红」 | MC **硬约束** | 仓价 P50 **显著下降** | ✅ 正确；勿与 bug 混淆 |
| **红 `huge_band`** | MC 件数 +（后端）放仓 cond_red | 分位可明显上移 | ✅ 符合设计 |
| **紫/金 `cells` / `value_sum` / `huge_band`** | MC | 按字段进入 filter | ✅ |
| **均格 / 均价** | **仅**枚举 + 分析推格 | 只缩/放宽候选；**不改 MC 直方图** | ✅ 见 #31 |
| **联合 ≥4 项读数** | 仅枚举 `avg_value` 容差 ±10%→±18% | 候选变多；MC 不变 | ✅ C-31b |
| **秒/放仓 UI** | 已 `_ENABLE_SNIPE_PASS_HINTS=False` | 当前无 UI 影响 | ⏸ P0-A 暂缓 |

**巨物默认值（2026-05-17 拍板）**：

- **占格**：未选 ★ → `HUGE_CELLS_PER_QUALITY` 最小 footprint（10/12/12），**不用格数均值**。
- **估值**：`PER_CELL_VALUE_HUGE` 金 ≈7000/格、红 ≈30000/格（多形状混合中位），与占格下限分开。

若 MC 分位「突然跳」：优先查是否新填了 **进 MC 的字段**（红=0、红 huge、各品质 cells/value/huge 件数），而非 C-32 或金默认 12。

---

## 34. 安装 capture OCR 时 pip 下载超时

**症状**：`pip install rapidocr-onnxruntime` 在下载 `opencv-python`（~40MB）时报 `ReadTimeoutError`。

**原因**：默认 pip 读超时偏短；且若用 **Anaconda 的 pip** 装到另一套环境，Streamlit 仍用 `C:\Python313\python.exe` 时会继续提示「未安装 OCR」。

**修法**（与 Streamlit 同一解释器）：

```powershell
C:\Python313\python.exe -m pip install "rapidocr-onnxruntime>=1.2.0" --default-timeout=600 --retries=5
# 或一次性装 UI + capture 可选依赖：
cd c:\xiangmuyunxing\biancheng\2026\bidking-lab
C:\Python313\python.exe -m pip install -e ".[ui,capture]" --default-timeout=600
```

**验证**：

```powershell
C:\Python313\python.exe -c "from rapidocr_onnxruntime import RapidOCR; print('OK')"
```

**教训**：capture 是 **UI 辅助**，与 Anaconda 日常环境可分离；文档与安装命令都写清 **Python313 路径**，避免装错环境。

---

## 35. 换图后 toast 闪烁、地图下拉锁死（widget rev 未同步）

**症状**：侧栏已上传截图（未 OCR）、切换或清空「具体地图」后，右侧「地图已切换…」toast **反复弹出**，地图 selectbox **无法再选**；仓库格数被反复清零。

**原因**：手动换图时 `_on_map_context_changed` 会 `obs_map_select_rev += 1` 生成新 key `obs_map_select__r{N}`，但若未把当前 `map_id` 写入新 key，本 run 末尾 post-selectbox 同步看到 `tracked=旧图`、`resolved=null`，再次调用 reset → 每轮 rerun 都 toast + bump rev。

**修法**（`app/streamlit_app.py`）：

1. bump 后立即 `_sync_map_select_widget_value(new_mid)`。
2. 本轮已在 `on_change` 处理时设 `_map_change_toast`，post-sync **跳过**二次 reset。
3. toast 后不再 `st.rerun()`（减少无意义整页刷新）。

**教训**：Streamlit 版本化 widget key 必须 **rev 与 value 同批更新**；`on_change` 与「渲染后校正」不要对同一事件各 reset 一次。

---

## 36. Capture OCR 日志与 ROI 调参

**OCR 裁切（绿色框）**：`INFO_PANEL_CROP_FRAC = (0.30, 0.07, 0.59, 0.72)`。预览：

**暖机样图**：`data/samples/game_warmup_1920x1080.jpg`（由游戏内 4K 截图压缩；源文件 `Desktop_Screenshot_*.png` 在 gitignore）。重生成：

```powershell
C:\Python313\python.exe scripts/compress_warmup_sample.py
```

```powershell
C:\Python313\python.exe scripts/preview_panel_roi.py --ocr
```

**错别字**：`ocr_normalize.py` 表驱动替换 → `patterns.py` 正则。R4 全屏常见：`置品/震品/费品→藏品`、`自色→白色`、`总点位→总占位`、`紧色→紫色`、`扫罐/扫装→扫描`。技能/轮廓说明行由 `IGNORE_PATTERNS` 丢弃，不进表单。

**日志**（可选）：

```powershell
$env:BIDKING_CAPTURE_LOG="1"
C:\Python313\python.exe -m streamlit run app/streamlit_app.py
```

控制台见 `bidking_lab.capture`；侧栏「上次导入」展开会多两行 pipeline 摘要（OCR 行数、解析到的 key）。

**耗时拆分（C-37）**：诊断展开可见 `抓屏 · OCR · 诊断图` 毫秒数。实机慢时先看 **抓屏** 是否因曾默认生成全屏预览；再看 **OCR** 是否仍 >1s（未重启 Streamlit 时旧模块可能仍在内存）。

---

## 37. 紫品均格 OCR 有数但输入框为空

**症状**：OCR 诊断里 `purple_avg_raw` / 解析值正常（如 3.27），读数 tab「紫品均格」仍空白；或删不掉旧值。

**原因**：

1. `st.text_input(..., value="")` 固定空值，与 session 里 widget key 冲突。
2. `hydrate_reading_widgets_from_obs` 在 `obs["purple_avg_raw"]==""` 时仍跳过写入。
3. `sync_obs_from_reading_widgets` 用空 widget 回写覆盖 OCR 刚填的值。

**修法（C-37）**：

- 均格/均价用版本化 key + `reconcile_avg_raw_widget_return`。
- hydrate：**不**用空 `obs` 覆盖已有 widget；换图时清 `*_avg_raw`。
- 读数 tab：`sync_obs(..., allow_clear=False)`。

**教训**：Streamlit 的 `text_input` 与 `number_input` 不同 — 显式 `value=""` 会制造「永远空」的假象；OCR 预填要走 widget key + hydrate，不要混用 `value=` 参数。

---

## 38. 实机 OCR 比改版前慢

**症状**：点「抓取当前屏幕」后 `st.status` 转很久；以前感觉「很快就好」。

**原因**（多段叠加，见 OBS #34）：

| 段 | 典型问题 |
|----|----------|
| 抓屏 | 4K 全屏复制 + 生成 monitor 预览 JPEG |
| 预处理 | PNG 编码 → 再解码进 RapidOCR |
| OCR | 模型本身（暖机后应稳定） |
| 诊断图 | `_png_for_debug_store` 大图缩放（在 OCR 之后） |

**修法（C-37）**：

- `ScreenCaptureConfig.include_monitor_preview=False`（默认）。
- `panel_rgb_array_for_ocr` 直传 ndarray；`prepare_image_for_ocr` 无变更时跳过重编码。
- **完全重启** Streamlit 使 capture 模块生效。

**验收**：诊断区 `OCR` 行单独应回到数百 ms 量级（视 CPU）；`抓屏` 在关预览后明显下降。

---

## 39. 切 tab 读数被清空 / 抓屏卡顿

**症状 A**：填完读数 → 切到「出价推荐」→ 再回「读数输入」，字段变空。  
**症状 B**：点抓屏后整页无响应数秒。  
**症状 C**：后台 MC 突然显示已取消。

**原因**：

- A：`sync_obs_from_reading_widgets(allow_clear=True)` 在非读数 tab 渲染时把未挂载的 widget 当成空。
- B：OCR 在 sidebar 同步执行，阻塞整页 script。
- C：观测侧栏字段变更触发 `cancel_bg_inference`，与地图 OCR 无关。

**修法**：

- A：读数 tab 专用 `allow_clear=False`；主 tab 用 `st.empty()` 槽避免卸载 widget 丢状态。
- B：`_deferred_capture_job` + `_execute_deferred_capture`；`apply_capture_result` 在 sidebar 前执行一次 `rerun`。
- C：仅在 `_on_map_context_changed` 取消 MC。

---

## 40. 启动仍慢：screen_ocr_warmup 与首屏等待

**症状**：`streamlit run` 后首屏要等很久；侧栏显示「OCR 暖机」或样本+实屏双暖机。

**原因**：

- 默认 `screen_ocr_warmup=true`（`data/ui_prefs.json`）：样本图 2 遍 + **实屏抓屏** 2 遍 ONNX。
- 这与 **实机点抓屏** 的耗时无关，但影响「第一次打开应用」体验。

**临时修法**：

- 高级 →「MC 采样参数」→ 取消 **启动时实屏 OCR 暖机** → **重启 Streamlit**。
- 仅关暖机不影响识别准确度；首次实机 OCR 可能多 1–2s。

**操作说明**：等待时可点 **「操作说明」** 子页或阅读 [`docs/INSTRUCTIONS.zh-CN.md`](docs/INSTRUCTIONS.zh-CN.md)（玩家向流程图，不是 PROGRESS）。

**计划（C-38）**：后台暖机 + 右侧小游戏占位区；工程项见 PROGRESS「C-38 启动体验」。

---

## 41. 后台推断很慢：MC 采样冷缓存，不是 filter

### 症状

点抓屏或改读数后，「出价推荐」tab 转圈 **几十秒到一两分钟**；有时同一张图第二次又快很多（约 7–12s）。

### 原因

`hint_pipeline.compute_hint_bundle` 写调试日志（`BIDKING_AGENT_DEBUG=1`）：

```json
{"message": "MC timing", "data": {"sample_ms": 54847, "filter_ms": 1, "n_trials": 1000, "map_id": 2401}}
```

- **`sample_ms`**：`sample_session_truth` × `n_trials`（默认侧栏常 **1500**；抓屏自动推断常用 **1000**）。
- **`filter_ms`**：通常 &lt; 20ms，**不是瓶颈**。
- **冷缓存**：`_sample_truths_cached(map_id, n_trials, seed)` — 换地图或 `max_entries=16` 挤出后，2401/2501 等曾出现 **50–108s** 单次采样。
- **叠加**：OCR 5–8s 在前；读数 fingerprint 变化会 **cancel** 后台 MC 并整段重跑。

### 修法（使用侧）

1. 侧栏 MC 样本数保持 **1000** 或 **500** 试跑。
2. **同地图连续推断** — 第二次起多半命中缓存。
3. 抓屏后少改读数，等 MC 完成再改（避免 cancel 重跑）。
4. 关闭「启动时实屏 OCR 暖机」只影响首启，不解决单次 MC（见 #40）。

### 教训

profile 时先看日志里的 **`sample_ms`**，不要先怀疑 `adaptive_filter` 或枚举。若要工程优化：按常用 map 预热缓存、抓屏自动推断固定 1000 trials、读数 debounce 再启 MC。

---

## 42. 金品只填均价预览显示 0格/1件 或 ⚠️ 无候选

### 症状

- 只填或 OCR 识别到 **金品均价**（如 35100），预览显示 **「0 格 / 1 件」** 或 ⚠️ 无合法候选。
- 手填 **金品总格 26** 则正常 💡 约 25 种解。

### 原因

1. **Session 残留** `gold_cells=0`（widget 默认 0 曾被当成已填）。
2. OCR 写入 `gold_avg_value` 但未写 `gold_cells`；严格枚举下 `total_cells=0` + 均价 → 退化或 0 候选。
3. **MC 与预览不同步**：均价 **不进 MC**（#31），只影响预览/分析估算 — 用户可能以为「推断没用上均价」，实际是预览路径问题。

### 修法（C-39 代码）

- `effective_number_field_for_preview`：预览时 widget `0` 当未填。
- `apply_capture_result`：仅 OCR 到金品均价时清除陈旧 `gold_cells`。
- `relax_bucket_for_enumeration_preview`：预览放宽 `avg_value` 等；去掉 `total_cells=0`。
- 换图：`reset_obs_for_manual_map_change` 清读数。

### 教训

区分 **预览 ⚠️** 与 **MC 分位不变**：前者看枚举+relax，后者看 #33 矩阵。填总格数或清残留后再填均价。

---

## 参考项目（写法）

本文件结构参考同工作区内 `projects/openclaw-discord-bot/TROUBLESHOOTING.md`：**症状 / 原因 / 修法 / 教训** 四段式，便于检索与复用。
