"""Persisted UI preferences (take effect after Streamlit server restart)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PREFS_PATH = Path(__file__).resolve().parent.parent / "data" / "ui_prefs.json"
_DEFAULTS: dict[str, Any] = {
    "screen_ocr_warmup": True,
}


def load_ui_prefs() -> dict[str, Any]:
    if not _PREFS_PATH.is_file():
        return dict(_DEFAULTS)
    try:
        raw = json.loads(_PREFS_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {**_DEFAULTS, **raw}
    except (OSError, json.JSONDecodeError):
        pass
    return dict(_DEFAULTS)


def save_ui_prefs(prefs: dict[str, Any]) -> None:
    merged = {**_DEFAULTS, **prefs}
    _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PREFS_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
