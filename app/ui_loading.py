"""Animated loading banners for Streamlit (OCR warm-up, MC hints)."""

from __future__ import annotations

import streamlit as st

LOADING_CSS = """
<style>
@keyframes bk-shimmer {
  0% { background-position: 200% center; }
  100% { background-position: -200% center; }
}
@keyframes bk-hourglass {
  0%, 100% { transform: rotate(0deg); opacity: 0.85; }
  50% { transform: rotate(180deg); opacity: 1; }
}
@keyframes bk-dots {
  0%, 20% { opacity: 0.25; }
  50% { opacity: 1; }
  100% { opacity: 0.25; }
}
.bk-load-banner {
  border-radius: 8px;
  padding: 0.45rem 0.65rem;
  margin: 0.15rem 0 0.35rem;
  font-size: 0.88rem;
  line-height: 1.35;
}
.bk-load-banner.loading {
  background: linear-gradient(
    90deg,
    rgba(99, 102, 241, 0.12) 0%,
    rgba(99, 102, 241, 0.32) 50%,
    rgba(99, 102, 241, 0.12) 100%
  );
  background-size: 200% auto;
  animation: bk-shimmer 2.2s linear infinite;
}
.bk-load-banner.ready {
  background: rgba(34, 197, 94, 0.12);
}
.bk-load-banner.error {
  background: rgba(239, 68, 68, 0.12);
}
.bk-hourglass {
  display: inline-block;
  animation: bk-hourglass 2.4s ease-in-out infinite;
  margin-right: 0.35rem;
}
.bk-dots span {
  animation: bk-dots 1.2s ease-in-out infinite;
}
.bk-dots span:nth-child(2) { animation-delay: 0.2s; }
.bk-dots span:nth-child(3) { animation-delay: 0.4s; }
.bk-warmup-bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.15);
  overflow: hidden;
  margin: 0.35rem 0 0.25rem;
}
.bk-warmup-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #6366f1, #7c3aed);
  transition: width 0.55s ease-out;
}
.bk-warmup-bar-fill--grow {
  width: 3%;
  animation: bk-warmup-grow cubic-bezier(0.4, 0.0, 0.2, 1) forwards;
}
.bk-warmup-bar-fill--pct {
  /* width set inline */
}
.bk-warmup-bar-fill--done {
  width: 100% !important;
  animation: bk-warmup-complete 0.45s ease-out forwards;
}
@keyframes bk-warmup-complete {
  from { width: 91%; }
  to { width: 100%; }
}
/* Installer-style curve: fast ONNX load → sample OCR → screen path (tuned ~52s total) */
@keyframes bk-warmup-grow {
  0% { width: 3%; }
  10% { width: 14%; }
  28% { width: 38%; }
  52% { width: 62%; }
  78% { width: 80%; }
  100% { width: 91%; }
}
</style>
"""


_loading_css_done = False


def inject_loading_css() -> None:
    global _loading_css_done
    if _loading_css_done:
        return
    _loading_css_done = True
    st.markdown(LOADING_CSS, unsafe_allow_html=True)


def _dots_html() -> str:
    return '<span class="bk-dots"><span>.</span><span>.</span><span>.</span></span>'


def loading_slot():
    """Return a placeholder; call ``.empty()`` after work finishes to dismiss banner."""
    return st.empty()


def render_warmup_progress_bar(
    *,
    pct: int,
    screen_warmup: bool,
    mode: str = "grow",
) -> None:
    """Simulated install-style progress (CSS anim while blocked; inline width on reruns)."""
    inject_loading_css()
    pct = max(0, min(100, int(pct)))
    if mode == "done":
        cls = "bk-warmup-bar-fill bk-warmup-bar-fill--done"
        style = ""
    elif mode == "pct":
        cls = "bk-warmup-bar-fill bk-warmup-bar-fill--pct"
        style = f' style="width: {pct}%;"'
    else:
        dur = 48 if screen_warmup else 24
        cls = "bk-warmup-bar-fill bk-warmup-bar-fill--grow"
        style = f' style="animation-duration: {dur}s;"'
    _d = "div"
    st.markdown(
        f'<{_d} class="bk-warmup-bar" aria-label="warmup progress">'
        f'<{_d} class="{cls}"{style}></{_d}></{_d}>',
        unsafe_allow_html=True,
    )


def render_status_banner(
    *,
    kind: str,
    message: str,
    detail: str = "",
) -> None:
    """HTML banner with shimmer / hourglass."""
    inject_loading_css()
    if kind == "loading":
        inner = (
            f'<span class="bk-hourglass">⏳</span>'
            f"<strong>{message}</strong> {_dots_html()}"
        )
        cls = "loading"
    elif kind == "ready":
        inner = f"✅ <strong>{message}</strong>"
        cls = "ready"
    elif kind == "error":
        inner = f"⚠️ <strong>{message}</strong>"
        cls = "error"
    else:
        inner = message
        cls = "loading"
    extra = (
        f'<br><span style="font-size:0.82rem;opacity:0.85">{detail}</span>'
        if detail
        else ""
    )
    st.markdown(
        f'<div class="bk-load-banner {cls}">{inner}{extra}</div>',
        unsafe_allow_html=True,
    )
