"""User-facing instructions doc is present and linked from the app."""

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def test_instructions_markdown_exists() -> None:
    path = _REPO / "docs" / "INSTRUCTIONS.zh-CN.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "flowchart" in text
    assert "抓取当前屏幕" in text


def test_instructions_streamlit_page_exists() -> None:
    assert (_REPO / "app" / "pages" / "1_操作说明.py").is_file()
