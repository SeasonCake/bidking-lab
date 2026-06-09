# BidKing Hero Ref Portable

这是 Hero Ref 支线的应用包模板，用于生成一个可独立复制的文件夹。工程源码仍保留在 `external_references/ahmad_live_reference_lab`。

## 启动

1. 右键 `Start-HeroRef.bat`，选择以管理员身份运行。
2. 正常场景使用默认端口抓包，不开 VPN/UU 时优先保持默认。
3. VPN/UU 场景可在 PowerShell 里运行：

```powershell
.\Start-HeroRef.ps1 -BroadSniff -IncludeLoopback
```

关闭 Hero Ref UI 默认会停止后台 monitor。如果只想调试 UI，不想停止 monitor，可加 `-KeepMonitorOnClose`。

## 运行前检查

- 需要 Windows 管理员权限，因为 WinDivert 需要加载内核驱动。
- 当前 portable 版本仍需要本机 Python 3.13，并安装 `pydivert`、`psutil`：

```powershell
C:\Python313\python.exe -m pip install pydivert psutil
```

- 需要本包内存在 `data\raw\tables\BidMap.txt`、`Drop.txt`、`Item.txt`。这些是本地游戏表，不建议公开发布。
- 已兼容快递/仓库、集装箱、别墅、沉船/活动沉船和 hidden 的基础地图族。快递/仓库/集装箱会读取外援 StaticData 的 tier 与 nest price；hidden 当前若本地表缺专属价格，会在诊断里显示 `fallback_default_price`，只作为保底参考。

## 目录说明

- `BidKingHeroRef\BidKingHeroRef.exe`：Hero Ref Tk UI。
- `Start-HeroRef.ps1` / `Start-HeroRef.bat`：一键启动 monitor + Hero Ref UI。
- `Stop-HeroRef.ps1`：强制停止本包启动的 UI 和 monitor。
- `scripts\`：WinDivert monitor 启动和运行脚本。
- `src\`：monitor 所需的 `bidking_lab` 运行代码。
- `data\processed\`：已处理的模型辅助 JSON。
- `data\raw\tables\`：本地游戏表，仅用于本机运行，不建议公开传播。
- `data\logs\live\`：运行时日志与最新快照，默认不应上传。

## 边界

Hero Ref 是实战参考工具，不保证收益，不直接接正式出价。UI 参考 B站猫饭团子uu 外援计算器思路，本支线 UI 修改与计算优化：B站加菲_barista。

项目链接：<https://github.com/SeasonCake/bidking-lab>
