# Troubleshooting & Lessons Learned（bidking-lab）

> 记录 BidKing 数据解析 / 本地工具链里**真实踩过的坑**，按主题归档，方便以后自己和协作者查阅。  
> 环境参考：Windows 11 / PowerShell 7 / Python 3.13 / Steam 版《竞拍之王》安装于自定义库目录。

## 目录

1. [可编辑安装 `pip install -e` 是干什么的](#1-可编辑安装-pip-install--e-是干什么的)
2. [游戏路径：不要搜整盘 `StreamingAssets`](#2-游戏路径不要搜整盘-streamingassets)
3. [`Tables/*.txt` 看起来像乱码 ≠ 一定“加密”](#3-tablestxt-看起来像乱码--一定加密)
4. [`Drop.txt` 头部形态（283KB 样本）](#4-droptxt-头部形态283kb-样本)
5. [把表拷进 `data/raw/`（git 外）](#5-把表拷进-data-rawgit-外)
6. [调试速查](#6-调试速查)
7. [`Tables/*.txt` 解码结论：Base64 → UTF-8 TSV](#7-tablestxt-解码结论base64--utf-8-tsv)
8. [PowerShell 里中文显示乱码 ≠ 数据坏了](#8-powershell-里中文显示乱码--数据坏了)

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

## 参考项目（写法）

本文件结构参考同工作区内 `projects/openclaw-discord-bot/TROUBLESHOOTING.md`：**症状 / 原因 / 修法 / 教训** 四段式，便于检索与复用。
