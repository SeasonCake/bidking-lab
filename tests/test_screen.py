"""Tests for capture.screen ROI math (no display required)."""

from bidking_lab.capture.screen import (
    INFO_PANEL_CROP_FRAC,
    fraction_to_pixel_box,
)


def test_fraction_to_pixel_box_1920x1080() -> None:
    box = fraction_to_pixel_box(1920, 1080, INFO_PANEL_CROP_FRAC)
    assert box == (326, 75, 998, 777)


def test_info_panel_crop_within_unit_square() -> None:
    l, t, r, b = INFO_PANEL_CROP_FRAC
    assert 0 <= l < r <= 1
    assert 0 <= t < b <= 1
