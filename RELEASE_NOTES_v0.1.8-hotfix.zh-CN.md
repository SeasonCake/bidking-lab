# BidKing Hero Ref v0.1.8-hotfix

> 相对 **v0.1.8**（commit `a706bd5`）的补丁 release。下一版计划仍为 **v0.2.0**。

发布日期：2026-06-14  
源 commit：`3fc9271`（拉文修复 `b9b4ab0` + 回归测试 + 发布物整理）

## 修复

- **拉文 R5 全品质扫描缺档锁 0**：第五轮技能（100301）或公开全品质信息（200030/200004）扫完全场后，未出现的品质档（如无红）锁定为 **0/0/0**，不再显示 **0/1/2** 并按「可能还有红」抬高推荐价。
- **拉文 R5 全品质扫描已出现档精确锁定**：扫全后已出现的档（如 **3 红**）锁定为 **3/3/3**，不再显示 **3/3/4** 并按「可能还有第 4 红」抬高推荐价。旧版只设下限、不设精确件数时会出现后者。随机 partial 揭示（如未知别墅）不受影响，仍只作下限。

## 验证

| 样本 | 结算 | hotfix R5 红件 | hotfix 参考价 | 旧 v0.1.8 红件 | 旧参考价 |
|---|---|---|---|---|---|
| 0 红（2408 奢华养老院） | q6=0 | **0/0/0** | 194,680 | 0/1/2 | 392,678 |
| 3 红（2407，`data 10`） | q6=3 | **3/3/3** | 634,882 | 3/3/4 | 698,862 |

- UI replay + 群友导出双重核对。
- `tests/test_ahmad_ref_engine_public_info.py` 拉文相关 4 条 + 全文件 141 passed。

## 包与校验

| 包 | 大小 | SHA256 |
|---|---|---|
| `BidKingHeroRef-v0.1.8-hotfix-full.zip` | 42.2 MB（44,198,209 bytes） | `C463B7FB0F030AAA5F5A14DD3222D21CF50103616953E3EE22CA443E176100C5` |
| `BidKingHeroRef-v0.1.8-hotfix-public-safe.zip` | 38.5 MB（40,421,627 bytes） | `04D6686E03840E3E78DDE38C8724A59A98065EE8DBA7CDFD7D67EC6CE47FAF6E` |

发布物路径：`bidking-lab/dist/`（构建脚本亦会同步至此）。

校验（Windows PowerShell）：

```powershell
Get-FileHash .\BidKingHeroRef-v0.1.8-hotfix-full.zip -Algorithm SHA256
Get-FileHash .\BidKingHeroRef-v0.1.8-hotfix-public-safe.zip -Algorithm SHA256
```

或 `certutil -hashfile <文件名> SHA256`。完整列表见 `SHA256SUMS-v0.1.8-hotfix.txt`。

## 升级说明

- 已装 **v0.1.8** 的用户：解压覆盖或换新目录均可；无需重导表。
- **public-safe** 不含 `data/raw/tables`，解压后运行 `Import-LocalTables.bat` 导入本机游戏表。
- 仍用 **v0.1.6 / v0.1.7** 的用户：建议直接换本包，不要跨多版混用旧 monitor。
- 换包后请**重启 Hero Ref**（勿混用旧 monitor / 旧 exe）。

## 已知遗留（仍计划 v0.2.0）

- 艾莎等无总件揭示英雄早期轮次 count_prior 偏保守。
- 其他非拉文 R5 全品质路径不受影响；partial 随机揭示仍只作下限。
