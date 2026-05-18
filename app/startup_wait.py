"""First-run / OCR warm-up wait layout (game slot + link to instructions)."""

from __future__ import annotations

import streamlit as st

from ui_loading import inject_loading_css, render_status_banner
from user_guide import render_instructions_link


def render_startup_wait_screen(*, screen_warmup: bool) -> None:
    """Center wait UI; right column reserved for a future mini-game."""
    inject_loading_css()

    st.markdown("### 正在准备推断台…")
    detail = (
        "样例图 + 主屏抓屏暖机（约 20–50 秒）"
        if screen_warmup
        else "样例图暖机（约 15–35 秒）"
    )
    render_status_banner(
        kind="loading",
        message="OCR 引擎加载中",
        detail=f"首次启动仅一次 · {detail} · 完成后抓屏会快很多",
    )

    left, right = st.columns([2, 3], gap="large")

    with left:
        st.progress(0, text="暖机进行中…")
        st.markdown(
            """
等待期间可以：

- 打开下方**操作说明**了解推荐流程（新页面，不占本区空间）
- 右侧预留**小游戏**位（后续版本）
            """
        )
        render_instructions_link()
        st.caption(
            "工程进度与版本计划见仓库 `PROGRESS.md`；"
            "安装问题见 `TROUBLESHOOTING.md`。"
        )

    with right:
        st.markdown(
            """
<div style="
  border: 2px dashed rgba(99,102,241,0.35);
  border-radius: 12px;
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(100,116,139,0.9);
  font-size: 0.95rem;
  background: rgba(99,102,241,0.04);
">
  小游戏占位区<br/>
  <span style="font-size:0.82rem">（暖机完成后可在此放置跳跃小游戏）</span>
</div>
""",
            unsafe_allow_html=True,
        )
