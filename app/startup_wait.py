"""First-run / OCR warm-up wait layout (game slot + link to instructions)."""

from __future__ import annotations

import time

import streamlit as st

from ui_loading import inject_loading_css, render_status_banner, render_warmup_progress_bar
from user_guide import render_instructions_link

# Observed warm-up (session d186da): ~52s with screen capture path, ~25s sample-only.
_WARMUP_SEC_SCREEN = 50.0
_WARMUP_SEC_SAMPLE = 26.0


def warmup_expected_sec(*, screen_warmup: bool) -> float:
    return _WARMUP_SEC_SCREEN if screen_warmup else _WARMUP_SEC_SAMPLE


def warmup_estimated_pct(*, screen_warmup: bool) -> int:
    """Piecewise curve aligned to ONNX load -> sample OCR -> screen OCR stages."""
    t0 = st.session_state.get("_warmup_t0")
    if t0 is None:
        return 4
    elapsed = time.perf_counter() - float(t0)
    exp = warmup_expected_sec(screen_warmup=screen_warmup)
    t = min(1.05, elapsed / exp)

    if t < 0.14:
        pct = 16.0 * (t / 0.14)
    elif t < 0.48:
        pct = 16.0 + 48.0 * ((t - 0.14) / 0.34)
    elif t < 0.90:
        pct = 64.0 + 24.0 * ((t - 0.48) / 0.42)
    else:
        pct = 88.0 + 4.0 * min(1.0, (t - 0.90) / 0.15)

    return max(4, min(91, int(pct)))


def warmup_stage_detail(*, screen_warmup: bool, pct: int) -> str:
    if screen_warmup:
        if pct < 18:
            return "加载 ONNX 识别模型…"
        if pct < 55:
            return "样例图推理暖机（2 遍）…"
        if pct < 88:
            return "主屏抓屏路径暖机…"
        return "收尾中…"
    if pct < 22:
        return "加载 ONNX 识别模型…"
    if pct < 75:
        return "样例图推理暖机（2 遍）…"
    return "收尾中…"


def _warmup_pane():
    if "_warmup_ui_pane" not in st.session_state:
        st.session_state["_warmup_ui_pane"] = st.empty()
    return st.session_state["_warmup_ui_pane"]


def render_startup_wait_screen(
    *,
    screen_warmup: bool,
    progress_pct: int | None = None,
    progress_mode: str = "grow",
    finalize: bool = False,
) -> None:
    """Center wait UI; single empty slot avoids duplicate ghost on reruns."""
    inject_loading_css()

    if finalize or progress_mode == "done":
        pct, mode = 100, "done"
    elif progress_pct is not None:
        pct = max(0, min(100, int(progress_pct)))
        mode = progress_mode
    else:
        pct = warmup_estimated_pct(screen_warmup=screen_warmup)
        reruns = int(st.session_state.get("_warmup_render_n", 0))
        mode = "grow" if reruns == 0 and pct < 10 else "pct"

    pane = _warmup_pane()
    with pane.container():
        if finalize or mode == "done":
            elapsed_ms = None
            t0 = st.session_state.get("_warmup_t0")
            if t0 is not None:
                elapsed_ms = int((time.perf_counter() - float(t0)) * 1000)
            st.markdown("### 正在准备推断台…")
            render_status_banner(
                kind="ready",
                message="OCR 引擎已就绪",
                detail="即将进入推断台",
            )
            render_warmup_progress_bar(pct=100, screen_warmup=screen_warmup, mode="done")
            try:
                from agent_debug_log import agent_debug_log

                agent_debug_log(
                    location="startup_wait.py:render_startup_wait_screen",
                    message="warmup pane finalized",
                    data={
                        "pct": 100,
                        "elapsed_ms": elapsed_ms,
                        "screen_warmup": screen_warmup,
                    },
                    hypothesis_id="H-warmup-ghost",
                    run_id="post-fix",
                )
            except Exception:
                pass
            return

        st.markdown("### 正在准备推断台…")
        eta = "约 45–55 秒" if screen_warmup else "约 20–30 秒"
        render_status_banner(
            kind="loading",
            message="OCR 引擎加载中",
            detail=f"首次启动仅一次 · {warmup_stage_detail(screen_warmup=screen_warmup, pct=pct)} · {eta}",
        )
        render_warmup_progress_bar(pct=pct, screen_warmup=screen_warmup, mode=mode)

        left, right = st.columns([11, 13], gap="medium")

        with left:
            st.markdown("**等待期间**")
            render_instructions_link()
            st.markdown(
                """
- 说明在**浏览器**中打开，不占侧栏  
- 暖机完成后可在侧栏抓屏、填读数  
                """
            )
            st.caption("安装问题见 `TROUBLESHOOTING.md`")

        with right:
            _game_box = (
                '<motion style="border:2px dashed rgba(99,102,241,0.4);border-radius:14px;'
                "min-height:200px;padding:1.25rem 1rem;display:flex;flex-direction:column;"
                "align-items:center;justify-content:center;text-align:center;gap:0.35rem;"
                'color:#64748b;font-size:0.92rem;'
                "background:linear-gradient(160deg,rgba(99,102,241,0.06) 0%,"
                'rgba(124,58,237,0.04) 100%);">'
                '<span style="font-size:1.75rem;line-height:1;">🎮</span>'
                '<strong style="color:#475569;font-size:1rem;">小游戏预留区</strong>'
                '<span style="font-size:0.8rem;max-width:16rem;">'
                "后续可放跳跃小游戏；暖机期间仅占位</span></motion>"
            )
            st.markdown(_game_box.replace("motion", "div"), unsafe_allow_html=True)

    try:
        from agent_debug_log import agent_debug_log

        agent_debug_log(
            location="startup_wait.py:render_startup_wait_screen",
            message="warmup pane rendered",
            data={
                "pct": pct,
                "mode": mode,
                "screen_warmup": screen_warmup,
                "rerun": int(st.session_state.get("_warmup_render_n", 0)),
            },
            hypothesis_id="H-warmup-ghost",
            run_id="post-fix",
        )
    except Exception:
        pass
    st.session_state["_warmup_render_n"] = (
        int(st.session_state.get("_warmup_render_n", 0)) + 1
    )
