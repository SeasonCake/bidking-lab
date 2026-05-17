"""Regression tests for OCR normalize (fixture strings + optional user screenshots)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bidking_lab.capture.ocr import image_bytes_to_text
from bidking_lab.capture.ocr_normalize import normalize_ocr_text
from bidking_lab.capture.parser import parse_panel_text

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ocr_regression"
_CASES_PATH = _FIXTURES / "normalize_cases.json"

# User-provided regression screenshots (skip if not on disk).
REGRESSION_IMAGES: tuple[tuple[str, Path], ...] = (
    ("desktop_r3_ethan", Path(r"C:\Users\shenc\Pictures\Desktop Screenshot 2026.05.15 - 11.10.26.79.png")),
    ("wechat_r4", Path(r"C:\Users\shenc\Pictures\微信图片_20260517163704.jpg")),
    ("wechat_r5_gabriela", Path(r"C:\Users\shenc\Pictures\微信图片_20260517145925.jpg")),
    ("wechat_r3_warehouse", Path(r"C:\Users\shenc\Pictures\微信图片_20260517135143.jpg")),
    ("wechat_r4_metrics", Path(r"C:\Users\shenc\Pictures\微信图片_20260517135136.jpg")),
    ("wechat_r4_aisha", Path(r"C:\Users\shenc\Pictures\微信图片_20260517223852.jpg")),
)

_REPO_SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples" / "panel_round4_1920x1080.png"


def _load_map_names() -> dict[int, str]:
    maps_path = Path(__file__).resolve().parents[1] / "data" / "processed" / "maps.json"
    if not maps_path.is_file():
        return {}
    raw = json.loads(maps_path.read_text(encoding="utf-8"))
    return {int(m["map_id"]): str(m["name"]) for m in raw}


@pytest.fixture(scope="module")
def map_names() -> dict[int, str]:
    return _load_map_names()


@pytest.mark.parametrize("case", json.loads(_CASES_PATH.read_text(encoding="utf-8")), ids=lambda c: c["id"])
def test_normalize_fixture_cases(case: dict) -> None:
    out = normalize_ocr_text(case["raw"])
    for frag in case.get("expect_contains", []):
        assert frag in out, f"missing {frag!r} in {out!r}"
    for frag in case.get("expect_not_contains", []):
        assert frag not in out, f"unexpected {frag!r} in {out!r}"


def test_panel_round4_sample_normalize_and_parse(map_names: dict[int, str]) -> None:
    if not _REPO_SAMPLES.is_file():
        pytest.skip("panel_round4 sample missing")
    text, err = image_bytes_to_text(_REPO_SAMPLES.read_bytes(), crop_panel=True)
    assert err is None and text
    norm = normalize_ocr_text(text)
    assert "轮廓" in norm
    assert "轮属" not in norm
    parsed = parse_panel_text(text, map_names=map_names)
    keys = set(parsed.suggestion_map().keys())
    assert {"blue_cells", "wg_cells", "purple_cells", "gold_cells"}.issubset(keys)


@pytest.mark.parametrize("label,path", REGRESSION_IMAGES, ids=[x[0] for x in REGRESSION_IMAGES])
def test_user_regression_image_ocr_smoke(label: str, path: Path) -> None:
    if not path.is_file():
        pytest.skip(f"missing {path}")
    text, err = image_bytes_to_text(path.read_bytes(), crop_panel=True)
    assert err is None, err
    assert text.strip()
    norm = normalize_ocr_text(text)
    assert norm  # normalize must not blank the panel


@pytest.mark.parametrize("label,path,expected_keys", [
    (
        "desktop_r3_ethan",
        REGRESSION_IMAGES[0][1],
        {"wg_cells", "blue_cells", "purple_avg_raw"},
    ),
    (
        "wechat_r4",
        REGRESSION_IMAGES[1][1],
        {"wg_cells", "blue_cells", "purple_cells", "gold_cells"},
    ),
    (
        "wechat_r3_warehouse",
        REGRESSION_IMAGES[3][1],
        {"warehouse_cells", "wg_cells", "blue_cells", "purple_avg_raw"},
    ),
    (
        "wechat_r4_metrics",
        REGRESSION_IMAGES[4][1],
        {"wg_cells", "blue_cells", "purple_avg_raw", "purple_value"},
    ),
    (
        "wechat_r4_aisha",
        REGRESSION_IMAGES[5][1],
        {"gold_cells"},
    ),
], ids=["desktop", "wechat_r4", "wechat_r3_wh", "wechat_metrics", "wechat_aisha"])
def test_user_regression_parse_keys(
    label: str,
    path: Path,
    expected_keys: set[str],
    map_names: dict[int, str],
) -> None:
    if not path.is_file():
        pytest.skip(f"missing {path}")
    if not map_names:
        pytest.skip("maps.json missing")
    text, err = image_bytes_to_text(path.read_bytes(), crop_panel=True)
    assert err is None
    parsed = parse_panel_text(text, map_names=map_names)
    got = set(parsed.suggestion_map().keys())
    missing = expected_keys - got
    assert not missing, f"missing keys {missing}; got {sorted(got)}"


def test_user_regression_map_names_when_present(map_names: dict[int, str]) -> None:
    if not map_names:
        pytest.skip("maps.json missing")
    cases = [
        (REGRESSION_IMAGES[0][1], "望族居所"),
        (REGRESSION_IMAGES[2][1], "末日庇护所"),
    ]
    # 35136 / 223852 crops often omit the map title line — no assert
    for path, name_fragment in cases:
        if not path.is_file():
            pytest.skip(f"missing {path}")
        text, err = image_bytes_to_text(path.read_bytes(), crop_panel=True)
        assert err is None
        parsed = parse_panel_text(text, map_names=map_names)
        assert parsed.map_id is not None
        assert name_fragment in (parsed.map_name or "")
