"""Fix common RapidOCR misreads before panel parsing."""

from __future__ import annotations

# (wrong, right) — order matters when replacements overlap.
_OCR_CHAR_FIXES: tuple[tuple[str, str], ...] = (
    ("意品", "藏品"),
    ("蒙品", "藏品"),
    ("随品", "藏品"),
    ("常色品", "紫色品"),
    ("常色", "紫色"),
    ("扫膜", "扫描"),
    ("扫媒", "扫描"),
    ("占位款", "占位数"),
    ("占位致", "占位数"),
    ("总点位", "总占位"),
    ("点位数", "占位数"),
    ("紧色", "紫色"),
    ("货色", "金色"),
    ("代优品", "优品"),
    ("扫猫", "扫描"),
    ("扫强", "扫描"),
    ("扫摄", "扫描"),
    ("空间觉！", "空间觉知"),
    ("空间觉\n", "空间觉知\n"),
    ("白色积", "白色和绿色"),
    ("均格：优品", "优品均格：优品均格"),
    ("单约占位", "平均占位"),
    ("品质质", "品质"),
    ("底护", "庇护"),
    ("完拍", "竞拍"),
    ("底护所", "庇护所"),
)


def normalize_ocr_text(text: str) -> str:
    """Apply lightweight string fixes; does not change layout."""
    if not text:
        return text
    out = text.replace("\r\n", "\n")
    for wrong, right in _OCR_CHAR_FIXES:
        out = out.replace(wrong, right)
    return out
