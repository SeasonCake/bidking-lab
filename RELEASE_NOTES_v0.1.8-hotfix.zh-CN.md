# BidKing Hero Ref v0.1.8-hotfix

> 相对 **v0.1.8**（commit `a706bd5`）的群补丁包；下一版计划仍为 **v0.2.0**。

发布日期：2026-06-14  
源 commit：`0ad6a97`（含拉文修复 `b9b4ab0`）

## 修复

- **拉文 R5 全品质扫描缺档锁 0**：第五轮技能（100301）或公开全品质信息（200030/200004）扫完全场后，未出现的品质档（如无红）锁定为 **0/0/0**，不再显示 **0/1/2** 并按「可能还有红」抬高推荐价。随机 partial 揭示（如未知别墅）不受影响，仍只作下限。

## 验证

- 群友导出 `2408:1425860637281329` R5 replay：红件 **0/0/0**，参考 **194,680**，结算 `final_q6_count=0`。
- `tests/test_ahmad_ref_engine_public_info.py` 140 passed。

## 包与校验

- `BidKingHeroRef-v0.1.8-hotfix-full.zip` — 42.2 MB（44,198,209 bytes），SHA256 `C463B7FB0F030AAA5F5A14DD3222D21CF50103616953E3EE22CA443E176100C5`
- 路径：`external_references/ahmad_live_reference_lab/dist/BidKingHeroRef-v0.1.8-hotfix-full.zip`

校验：

```powershell
Get-FileHash .\BidKingHeroRef-v0.1.8-hotfix-full.zip -Algorithm SHA256
```

或 `certutil -hashfile BidKingHeroRef-v0.1.8-hotfix-full.zip SHA256`。

## 升级说明

- 已装 **v0.1.8** 的用户：解压覆盖或换新目录均可；无需重导表。
- 仍用 **v0.1.6 / v0.1.7** 的用户：建议直接换本包，不要跨多版混用旧 monitor。
