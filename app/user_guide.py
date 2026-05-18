"""Render the end-user guide inside Streamlit (see ``docs/INSTRUCTIONS.zh-CN.md``)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_REPO = Path(__file__).resolve().parent.parent
_INSTRUCTIONS_MD = _REPO / "docs" / "INSTRUCTIONS.zh-CN.md"
_HOME_PAGE = "streamlit_app.py"


def instructions_page_path() -> str:
    """Path for ``st.page_link`` / ``st.switch_page`` (relative to ``app/``)."""
    return "pages/1_操作说明.py"


def render_instructions_link(*, label: str = "📖 打开操作说明（新页面）") -> None:
    try:
        st.page_link(instructions_page_path(), label=label, icon="📖")
    except Exception:  # noqa: BLE001
        st.markdown(
            f"在左侧边栏选择 **操作说明**，或刷新后重试。",
        )


def _mermaid_block(diagram: str, *, height: int = 280) -> None:
    import streamlit.components.v1 as components

    safe = diagram.replace("`", "\\`")
    components.html(
        f"""
<!DOCTYPE html>
<html><head>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  body {{ margin: 0; font-family: system-ui, sans-serif; background: transparent; }}
  .mermaid {{ display: flex; justify-content: center; }}
</style>
</head><body>
<pre class="mermaid">{safe}</pre>
<script>mermaid.initialize({{ startOnLoad: true, theme: "neutral" }});</script>
</body></html>
""",
        height=height,
        scrolling=False,
    )


def render_user_guide_page() -> None:
    """Full instructions view (standalone Streamlit page)."""
    st.title("📖 bidking-lab 操作说明")
    st.caption(
        "玩家向简明手册 · 工程文档见 "
        "[README.zh-CN.md](https://github.com/SeasonCake/bidking-lab/blob/main/README.zh-CN.md)"
    )

    try:
        st.page_link(_HOME_PAGE, label="← 返回推断台", icon="🏛️")
    except Exception:  # noqa: BLE001
        pass

    st.markdown(
        """
本页说明**怎么用** Streamlit 推断台；方法论与版本历史不在此重复。

**工具做什么**：把游戏信息面板 OCR/手填读数 → 约束 → 出价分布与候选枚举。  
**不做什么**：不自动出价、不读游戏内存。
        """
    )

    st.subheader("推荐操作顺序")
    _mermaid_block(
        """
flowchart LR
  A[① 选英雄与地图] --> B[② 填仓库总格]
  B --> C{③ 读数}
  C --> D[抓屏 OCR]
  C --> E[粘贴/上传]
  C --> F[手填]
  D --> G[④ 出价推荐]
  E --> G
  F --> G
  G --> H[⑤ 看 P50 等]
        """,
        height=220,
    )

    st.markdown(
        """
| 步骤 | 位置 | 要点 |
|------|------|------|
| ① | 侧栏「会话」 | 先类型后具体地图；**换图**可能清空读数 |
| ② | 侧栏「仓库」 | OCR **一般不会填**，请对照游戏手填 |
| ③ | 侧栏抓屏 / 读数 tab | 游戏在前台；信息区在屏幕**左中** |
| ④⑤ | **出价推荐** tab | 需地图 + 仓库 + 至少一条读数 |
        """
    )

    st.subheader("抓屏时发生了什么")
    _mermaid_block(
        """
sequenceDiagram
  participant U as 你
  participant UI as 推断台
  participant OCR as OCR
  U->>UI: 抓取当前屏幕
  UI->>UI: 裁切左侧信息区
  UI->>OCR: 识别
  OCR-->>UI: 文本
  UI-->>U: 填入读数 tab
        """,
        height=300,
    )

    st.subheader("四个 Tab")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
**读数输入** — 各品质 cells / count / 总价 / 均格 / 巨物  

**出价推荐** — MC 直方图、P25–P90、分析估算（默认 **1500** 次 MC）
            """
        )
    with col2:
        st.markdown(
            """
**道具 ROI** — Ethan 默认道具包的性价比实验  

**联合推断** — 实验性，日常可忽略
            """
        )

    _mermaid_block(
        """
flowchart TB
  R[读数输入] --> H[出价推荐]
  R --> I[道具 ROI]
  R --> J[联合推断·实验]
        """,
        height=200,
    )

    with st.expander("读数字段：哪些进 MC？"):
        st.markdown(
            """
| 输入 | 进 MC？ | 说明 |
|------|---------|------|
| cells / count / 总价 | ✅ | 硬约束过滤样本 |
| 均格、均价 | ❌ | 主要收窄**枚举候选** |
| 巨物「1个」 | ✅ | 按**件数** band |
| ★ 具体巨物（船名等） | ❌ MC / ✅ 枚举 | 精确格数给候选列表 |
            """
        )

    with st.expander("常见问题"):
        st.markdown(
            """
1. **识别了地图但读数空** — 看侧栏「上次导入」OCR 原文；不清晰就手填。  
2. **启动要等很久** — 首次 OCR 暖机；高级里可关「实屏暖机」后**重启**。  
3. **首次抓屏比第二次慢** — 正常；同一会话内会更快。  
4. **仓库格数被清空** — 换图时可能清空；请先填格数再抓屏或 OCR 换图。
            """
        )

    st.divider()
    if _INSTRUCTIONS_MD.is_file():
        with st.expander("完整 Markdown 原文（与仓库同步）"):
            st.markdown(_INSTRUCTIONS_MD.read_text(encoding="utf-8"))
