# 信任、火绒与 WinDivert 说明

## 为什么需要管理员权限

Hero Ref 的实时监测使用 WinDivert 抓取本机到游戏服务器的网络包。WinDivert 是开源的 Windows packet capture / packet filtering 项目，架构上需要加载内核驱动，因此启动时必须使用管理员权限。

本工具的默认链路是：

```text
BidKing.exe 网络包
  -> WinDivert 本机抓包
  -> BidKingHeroMonitor.exe 解析游戏状态
  -> data/logs/live/latest_snapshot.json
  -> BidKingHeroRef.exe 显示参考估价
```

Hero Ref 不会主动向外上传样本、日志或账号信息。运行时会在本地 `data\logs\live` 写入快照和日志。

## 火绒 / 安全软件提示

火绒、Windows Defender 或其他安全软件可能拦截以下行为：

- WinDivert 驱动加载；
- EXE 读取本机网络包；
- 隐藏 PowerShell 启动后台 monitor exe；
- 首次运行 PyInstaller 打包的 EXE。

如果确认包来源可信，可以把整个 `BidKingHeroRefPortable` 文件夹加入信任区。不要只信任单个临时文件，因为 monitor、UI、日志目录和 WinDivert 驱动路径都可能参与启动。

## 不应上传或公开的内容

公开发包前请先检查：

- 不上传 `data\logs\`；
- 不上传 `data\samples\`；
- 不上传 `.tmp\`；
- 不上传个人截图、录屏、账号相关日志；
- 不公开传播 `data\raw\tables\`，除非你确认具备相关授权。

公开的 public-safe 包默认不包含 `data\raw\tables\`。用户需要在自己的电脑上运行 `导入本机游戏表.bat`，从本机 BidKing 安装目录复制表文件到包内再启动。

## WinDivert 来源说明

WinDivert 是开源项目，当前包内 monitor exe 基于 Python `pydivert` 打包，会携带 WinDivert 驱动文件。实际驱动文件位于 `BidKingHeroMonitor` 运行目录的 PyInstaller 内部资源中；安全软件拦截时，请确认包来源后再决定是否信任整个文件夹。

普通用户不需要单独安装 Python、`pydivert` 或 `psutil`。
