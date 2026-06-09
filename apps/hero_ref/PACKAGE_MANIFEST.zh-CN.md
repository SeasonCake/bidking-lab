# Hero Ref 应用包清单

生成脚本：`external_references/ahmad_live_reference_lab/build_hero_ref_portable.ps1`

默认输出：`external_references/ahmad_live_reference_lab/dist/BidKingHeroRefPortable`

## 默认包含

- Hero Ref UI exe；
- 一键启动 / 停止脚本；
- WinDivert live monitor 必要脚本；
- `src/bidking_lab` 运行代码；
- `data/processed/*.json`；
- 本机运行需要的 `data/raw/tables` 表文件；
- 用户 README、安全说明、署名和边界说明。

## 默认排除

- `data/logs` 历史内容；
- `data/samples` 真实样本；
- `data/review`；
- `.tmp`；
- `build`、`__pycache__`、`.pytest_cache`；
- Codex 附件、截图、录屏、个人路径记录。

## Public-safe 模式

如果使用构建脚本的 `-PublicSafe`，会排除 `data/raw/tables`。这种包更适合公开传输，但用户需要自行补齐本地表文件，否则 monitor 无法运行。
