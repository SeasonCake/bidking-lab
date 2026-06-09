# Hero Ref 应用包清单

生成脚本：`external_references/ahmad_live_reference_lab/build_hero_ref_portable.ps1`

默认输出：`external_references/ahmad_live_reference_lab/dist/BidKingHeroRefPortable`

## 默认包含

- Hero Ref UI exe；
- WinDivert live monitor exe；
- 一键启动 / 停止脚本；
- public-safe 本机表导入脚本；
- WinDivert live monitor 诊断/回退脚本；
- `src/bidking_lab` 运行代码；
- `data/processed/*.json`；
- 本机运行需要的 `data/raw/tables` 表文件；
- `使用说明.txt`、`火绒拦截说明.txt`、`VPN或UU备用启动.txt`；
- 用户 README、安全说明、署名和边界说明。

## 默认排除

- `data/logs` 历史内容；
- `data/samples` 真实样本；
- `data/review`；
- `.tmp`；
- `build`、`__pycache__`、`.pytest_cache`；
- Codex 附件、截图、录屏、个人路径记录。

## Public-safe 模式

如果使用构建脚本的 `-PublicSafe`，会排除 `data/raw/tables`。这种包更适合公开传输；用户第一次运行前可以执行 `导入本机游戏表.bat`，从自己本机的 BidKing 游戏目录导入 `BidMap.txt`、`Drop.txt`、`Item.txt` 等表文件，否则 monitor 无法运行。

## 运行时依赖

默认 portable 包不要求用户安装 Python、`pydivert` 或 `psutil`。WinDivert 抓包仍需要管理员权限，并可能需要在火绒、Windows Defender 等安全软件中信任整个应用文件夹。
