# BidKing Lab v1.0.0 · 便携版（免安装 Python）

> **解压 → 双击 `启动.bat` → 浏览器打开即可。** 无需安装 Python、无需 venv、无需 pip。

---

## 系统要求

| 项目 | 要求 |
|------|------|
| 系统 | **Windows 10/11 64 位** |
| 磁盘 | 约 1 GB 解压空间 |
| 网络 | OCR 首次抓屏可能需下载小模型 |
| 游戏 | 已安装《竞拍之王》；本包不附带游戏 |

---

## 使用步骤

1. 解压 **`bidking-lab-v1.0.0-portable.zip`** 到任意文件夹（路径尽量短、少中文）
2. 双击 **`启动.bat`**（或 **`start.bat`**）
3. 等待几秒 → 浏览器打开 http://localhost:8501

关闭黑色命令行窗口 = 停止服务。

---

## 与标准版 zip 的区别

| | 便携版 `-portable.zip` | 标准版 `.zip` |
|---|---|---|
| 需安装 Python | ❌ | ✅ |
| 首次 pip 安装 | ❌ | ✅（约 1–3 分钟） |
| 体积 | 较大（~300–600 MB） | 较小（~2 MB + 依赖） |
| 适合 | 只想双击用的玩家 | 已有 Python 的用户 |

---

## 演示视频

https://github.com/user-attachments/assets/9fb463dc-ca85-4fc0-b10e-56b81091a5a8

详细操作见 [`docs/INSTRUCTIONS.zh-CN.md`](docs/INSTRUCTIONS.zh-CN.md)。

---

## 常见问题

**杀毒软件拦截 `runtime\python\`？**  
便携版内置官方 Python embed 运行时。若误报，请将解压目录加入白名单。

**双击闪退？**  
在解压目录 Shift+右键 →「在终端中打开」，输入 `启动.bat` 查看报错。

**端口 8501 被占用？**  
关闭其他 Streamlit 程序，或编辑 `启动.bat` 在 streamlit 命令后加 `--server.port 8502`。

---

*非官方工具 · MIT License · 请仅在合法拥有游戏的前提下使用*
