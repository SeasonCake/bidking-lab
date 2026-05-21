# BidKing Lab v1.0.0

Phase 1A 稳定版：**读数输入 · MC 出价推荐 · OCR 抓屏（可选）**

---

## 下载（推荐）

| 文件 | 说明 |
|------|------|
| **`bidking-lab-v1.0.0-portable.zip`** | **便携版（推荐玩家）**：解压 → 双击 `启动.bat`，无需安装 Python |
| **`bidking-lab-v1.0.0.zip`** | 标准版：需本机 Python 3.10+，双击 `start_ui.ps1` |
| Source code (zip) | 开发者源码（需自行 `pip install` + 复制游戏表） |

玩家**无 Python** 请下载 **`-portable.zip`**；已有 Python 可选标准版（体积更小）。

---

## 系统要求

- Windows 10/11
- Python 3.10+（推荐 3.13，[下载](https://www.python.org/downloads/)）
- 已安装《竞拍之王》（本工具不附带游戏）

---

## 3 步上手（便携版）

1. 解压 **`bidking-lab-v1.0.0-portable.zip`**
2. 双击 **`启动.bat`**
3. 浏览器打开 http://localhost:8501

标准版（需 Python）：解压 `bidking-lab-v1.0.0.zip` → 双击 `start_ui.ps1`。详见各包内说明文档。

---

## 演示

https://github.com/user-attachments/assets/9fb463dc-ca85-4fc0-b10e-56b81091a5a8

---

## 本版本亮点

- 三主 tab UI：读数输入 / 出价推荐 / 道具 ROI
- 侧栏 OCR 抓屏预填读数
- MC 默认 1000 样本，406 单测通过
- 枚举预览与 MC 推理分层（预览 ⚠️ 不阻断 MC，见 TROUBLESHOOTING #47）
- 均格/均价联合约束、tab 切换读数同步（C-40 / C-41）

---

## 已知限制

- **非官方**工具，与游戏 / Steam 无关联
- Release zip 内含自游戏 Tables 提取的运行时表文件；请仅在合法拥有游戏的前提下使用
- OCR 首次运行需下载模型，可能较慢
- 秒仓/放仓 UI 仍为实验功能，默认隐藏

---

## 开发者

```powershell
git clone https://github.com/SeasonCake/bidking-lab.git
cd bidking-lab
pip install -e ".[ui,capture]"
streamlit run app/streamlit_app.py
```
