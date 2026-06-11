# BidKing Hero Ref Portable

这是 Hero Ref 支线的应用包模板，用于生成一个可独立复制的文件夹。工程源码仍保留在 `external_references/ahmad_live_reference_lab`。

## 启动

1. 优先阅读 `使用说明.txt`。
2. 如果是 public-safe 包，先运行 `Import-LocalTables.bat`，选择 BidKing 游戏目录、`StreamingAssets` 目录或 `Tables` 目录，把本机表导入到包内。
3. 启动 Hero Ref：
   - 默认悬浮窗：`Start-HeroRef.bat`。
   - 任务栏窗口：`Start-HeroRef-Taskbar.bat`。
   - 双击启动会自动申请管理员权限；如果 Windows 没有弹出管理员授权或启动失败，请先看 `管理员运行说明.txt`，再右键对应启动文件，选择以管理员身份运行。
4. 正常场景使用默认端口抓包，不开 VPN/UU 时优先保持默认。
5. VPN/UU 场景可在 PowerShell 里运行：

```powershell
.\Start-HeroRef.ps1 -BroadSniff -IncludeLoopback
```

关闭 Hero Ref UI 默认会停止后台 monitor。如果只想调试 UI，不想停止 monitor，可加 `-KeepMonitorOnClose`。

如果希望 Hero Ref 像普通窗口一样出现在任务栏，并支持 `Alt+Tab` / `Win+Tab` 切换，优先运行 `Start-HeroRef-Taskbar.bat`。等价 PowerShell 命令是：

```powershell
.\Start-HeroRef.ps1 -ShowTaskbar
```

## 运行前检查

- 需要 Windows 管理员权限，因为 WinDivert 需要加载内核驱动。
- 当前 portable 版本内置 Hero Ref UI exe 和 WinDivert monitor exe；普通用户不需要安装 Python、`pydivert` 或 `psutil`。
- 火绒、Windows Defender 或其他安全软件可能拦截 WinDivert 驱动加载或 PyInstaller EXE。确认来源可信后，可以把整个 `BidKingHeroRefPortable` 文件夹加入信任区。
- 需要本包内存在 `data\raw\tables\BidMap.txt`、`Drop.txt`、`Item.txt`。public-safe 包可通过 `Import-LocalTables.bat` 从用户本机导入；这些是本地游戏表，不建议公开发布。
- 已兼容快递/仓库、集装箱、别墅、沉船/活动沉船和 hidden 的基础地图族。快递/仓库/集装箱会读取外援 StaticData 的 tier 与 nest price；hidden 当前若本地表缺专属价格，会在诊断里显示 `fallback_default_price`，只作为保底参考。

## 目录说明

- `BidKingHeroRef\BidKingHeroRef.exe`：Hero Ref Tk UI。
- `BidKingHeroMonitor\BidKingHeroMonitor.exe`：包内 WinDivert live monitor。
- `Start-HeroRef.bat`：默认悬浮窗启动 monitor + Hero Ref UI。
- `Start-HeroRef-Taskbar.bat`：任务栏窗口启动，支持 `Alt+Tab` / `Win+Tab` 切换。
- `Start-HeroRef.ps1`：PowerShell 启动入口，可加 `-ShowTaskbar`、`-BroadSniff`、`-IncludeLoopback` 等参数。
- `管理员运行说明.txt`：告诉用户为什么需要管理员权限，以及如何右键以管理员身份运行启动文件。
- `Import-LocalTables.bat` / `Import-LocalTables.ps1`：public-safe 包导入本机游戏表的入口。
- `Stop-HeroRef.ps1`：强制停止本包启动的 UI 和 monitor。
- `Stop-HeroRef.bat`：给普通用户看的停止入口。
- `使用说明.txt` / `火绒拦截说明.txt` / `VPN或UU备用启动.txt`：普通用户优先阅读的短说明。
- `scripts\`：开发/诊断脚本，正式启动优先使用包内 monitor exe。
- `src\`：monitor 所需的 `bidking_lab` 运行代码。
- `data\processed\`：已处理的模型辅助 JSON。
- `data\raw\tables\`：本地游戏表，仅用于本机运行，不建议公开传播。
- `data\logs\live\`：运行时日志与最新快照，默认不应上传。

## 边界

Hero Ref 是实战参考工具，不保证收益，不直接接正式出价。UI 参考 B站猫饭团子uu 外援计算器思路，本支线 UI 修改与计算优化：B站加菲_barista。

项目链接：<https://github.com/SeasonCake/bidking-lab>
