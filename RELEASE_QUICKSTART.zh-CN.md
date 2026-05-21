# BidKing Lab v1.0.0 · 3 步上手

> 非官方《竞拍之王》推断辅助工具。不包含游戏本体；**请仅在已合法拥有游戏的前提下使用**。

---

## 系统要求

| 项目 | 要求 |
|------|------|
| 系统 | Windows 10 / 11 |
| Python | **3.10+**（推荐 **3.13**，安装时勾选 **Add to PATH**） |
| 网络 | 首次运行需联网下载 Python 依赖 |
| 游戏 | 需已安装《竞拍之王》；本包**不**修改游戏、不读内存 |

下载：[Python 3.13](https://www.python.org/downloads/)

---

## 3 步启动

1. **解压** `bidking-lab-v1.0.0.zip` 到任意文件夹（路径尽量不含中文空格问题较少）
2. **双击** `start_ui.ps1`  
   - 若提示「无法运行脚本」：在 PowerShell 中执行一次  
     `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`  
     或在资源管理器中对 `start_ui.ps1` 右键 → **使用 PowerShell 运行**
3. 等待首次安装完成 → 浏览器自动打开 **http://localhost:8501**

---

## 30 秒使用流程

1. 侧栏选 **英雄 + 地图**，手填 **仓库总格数**（OCR 通常不会填这项）
2. 侧栏 **抓取当前屏幕** 或读数 tab 手填
3. 顶栏切到 **出价推荐** → 看 MC 分布与各品质后验

详细说明见 [`docs/INSTRUCTIONS.zh-CN.md`](docs/INSTRUCTIONS.zh-CN.md)。

### 演示视频

https://github.com/user-attachments/assets/9fb463dc-ca85-4fc0-b10e-56b81091a5a8

---

## 常见问题

**Q：双击没反应 / 闪退？**  
在文件夹空白处 Shift+右键 →「在此处打开 PowerShell 窗口」，输入 `.\start_ui.ps1` 看报错。

**Q：预览显示「无合法候选」但出价 tab 仍有结果？**  
正常。下方预览只看枚举；MC 仍使用总价/格数/件数等硬读数。见 [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) #47。

**Q：OCR 抓屏不可用？**  
首次运行会下载 OCR 模型，需等待。确保游戏信息面板在屏幕**左侧中部**且未被遮挡。

**Q：我是开发者，想从 git 更新？**  
本 zip 面向玩家；开发请 clone 仓库：`pip install -e ".[ui,capture]"`。

---

## 包内有什么

| 目录 / 文件 | 用途 |
|-------------|------|
| `app/` | Streamlit 界面 |
| `src/` | 推断引擎 |
| `data/processed/*.json` | 派生数据（无游戏也可解析） |
| `data/raw/tables/*.txt` | 运行 MC 所需的表（自游戏 Tables 提取，**仅随 release 包分发**） |
| `start_ui.ps1` | 一键建 venv + 装依赖 + 启动 |

---

*版本 v1.0.0 · Phase 1A · 406 tests · MIT License*
