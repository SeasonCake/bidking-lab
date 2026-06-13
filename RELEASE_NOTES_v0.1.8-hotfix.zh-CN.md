# BidKing Hero Ref v0.1.8-hotfix

> 相对 **v0.1.8**（commit `a706bd5`）的补丁 release。下一版计划仍为 **v0.2.0**。

发布日期：2026-06-14  
源 commit：`b94c474`（拉文修复 `b9b4ab0` + 艾莎结算页估价修复 `b94c474` + 回归测试 + 发布物整理）

> 本 hotfix 在原拉文修复基础上**追加艾莎结算页估价修复**，仍沿用 `v0.1.8-hotfix` 标签，直接替换旧包。

## 修复

- **拉文 R5 全品质扫描缺档锁 0**：第五轮技能（100301）或公开全品质信息（200030/200004）扫完全场后，未出现的品质档（如无红）锁定为 **0/0/0**，不再显示 **0/1/2** 并按「可能还有红」抬高推荐价。
- **拉文 R5 全品质扫描已出现档精确锁定**：扫全后已出现的档（如 **3 红**）锁定为 **3/3/3**，不再显示 **3/3/4** 并按「可能还有第 4 红」抬高推荐价。旧版只设下限、不设精确件数时会出现后者。随机 partial 揭示（如未知别墅）不受影响，仍只作下限。
- **艾莎/通用：结算页「估价」不再泄露结算证据**：结算页三档卡左侧「估价」本应复现末轮 live 估价，旧版重建快照时只翻 `phase/truth`，没清结算级证据（尤其 `ui_contract.constraints` 携带精确结算件数），引擎回读后把估价抬高（样本 639k vs 真实 live 402k；群友截图显示 91 万、末轮实际 40/50/60 万）。现一并剥离 `final_*`/`inventory`/`known_value_sum`/`minimap_grid_items`/`model_eval` 与 `ui_contract.constraints/minimap`，估价回落到 live 量级。**仅影响结算页显示，不影响 live 竞价决策**。

## 验证

| 样本 | 结算 | hotfix R5 红件 | hotfix 参考价 | 旧 v0.1.8 红件 | 旧参考价 |
|---|---|---|---|---|---|
| 0 红（2408 奢华养老院） | q6=0 | **0/0/0** | 194,680 | 0/1/2 | 392,678 |
| 3 红（2407，`data 10`） | q6=3 | **3/3/3** | 634,882 | 3/3/4 | 698,862 |

- 艾莎结算页：样本 `2404:…906376` r02_settled 估价由泄露的 **639,131** 回落到 **402,958**（= 真实 live r02_bidding），q6 区间由泄露的 `[3,3,4]` 回到 prior `[1,2,3]`；逐字段剥离锁定元凶为 `ui_contract.constraints`。
- UI replay + 群友导出双重核对。
- `tests/test_ahmad_ref_engine_public_info.py` 拉文相关 4 条 + 全文件 141 passed；`tests/test_live_overlay.py` 209 passed（含新增 `test_pre_settlement_clone_strips_settlement_grade_evidence`）。

## 包与校验

| 包 | 大小 | SHA256 |
|---|---|---|
| `BidKingHeroRef-v0.1.8-hotfix-full.zip` | 41.2 MB（43,245,330 bytes） | `45D46FC15BBB31AFC3B306A9E31D15ECE7194DED5AFD288501401BB4810E77FD` |
| `BidKingHeroRef-v0.1.8-hotfix-public-safe.zip` | 37.7 MB（39,501,186 bytes） | `7AD3AE9D7446FE9F69AC4743F45E1B76B54DA45F75D94CE825859DBE8596CFD8` |

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
