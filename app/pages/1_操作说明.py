"""Streamlit sub-page: end-user instructions (does not load OCR / game tables)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_APP = Path(__file__).resolve().parent.parent
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from ui_theme import inject_app_theme
from user_guide import render_user_guide_page

st.set_page_config(
    page_title="操作说明 · bidking-lab",
    page_icon="📖",
    layout="wide",
)
inject_app_theme()
render_user_guide_page()
