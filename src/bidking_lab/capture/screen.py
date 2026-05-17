"""Display capture + ROI for the center-left bidding info panel (C-36).

Coordinates are **fractions of the captured monitor's pixel rectangle**
(left, top, right, bottom in 0..1). The reference frame is always the
**primary (main) monitor** when the game runs fullscreen/windowed there.

Multi-monitor: enumerate via :func:`list_monitors`; default capture uses
``is_primary=True``. Secondary monitors use the same fraction crop relative
to *that* monitor's resolution (not the virtual desktop bbox).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# Calibrated on 1920×1080 (data/samples/panel_round4_1920x1080.png, notebook 06).
# Center text panel only; excludes left player list & right warehouse grid.
INFO_PANEL_CROP_FRAC: tuple[float, float, float, float] = (0.30, 0.07, 0.59, 0.72)

_REPO_ROOT = Path(__file__).resolve().parents[3]
OCR_WARMUP_SAMPLE = _REPO_ROOT / "data" / "samples" / "panel_round4_1920x1080.png"

PanelCropFrac = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class MonitorInfo:
    """One physical/virtual display from the OS."""

    index: int
    left: int
    top: int
    width: int
    height: int
    is_primary: bool

    @property
    def pixel_box(self) -> tuple[int, int, int, int]:
        """Absolute virtual-desktop box ``(left, top, right, bottom)``."""
        return (self.left, self.top, self.left + self.width, self.top + self.height)


@dataclass(frozen=True, slots=True)
class ScreenCaptureConfig:
    """Runtime capture settings for C-36 Streamlit button."""

    monitor_index: int | None = None  # None → primary
    crop_frac: PanelCropFrac = INFO_PANEL_CROP_FRAC
    # If game window is not 1:1 with monitor pixels, scale crop by reference res:
    reference_width: int = 1920
    reference_height: int = 1080


def fraction_to_pixel_box(
    width: int,
    height: int,
    crop: PanelCropFrac,
) -> tuple[int, int, int, int]:
    """Map normalized crop to PIL-style ``(left, upper, right, lower)``."""
    l, t, r, b = crop
    return (int(width * l), int(height * t), int(width * r), int(height * b))


def list_monitors() -> list[MonitorInfo]:
    """Return connected monitors (requires optional ``mss``)."""
    try:
        import mss
    except ImportError as exc:
        raise RuntimeError(
            "实时抓屏需要 mss：pip install mss（或 pip install -e \".[capture]\")"
        ) from exc

    monitors: list[MonitorInfo] = []
    with mss.mss() as sct:
        for i, mon in enumerate(sct.monitors[1:], start=1):
            monitors.append(
                MonitorInfo(
                    index=i,
                    left=int(mon["left"]),
                    top=int(mon["top"]),
                    width=int(mon["width"]),
                    height=int(mon["height"]),
                    is_primary=(i == 1),
                ),
            )
    return monitors


def resolve_monitor(
    monitors: Sequence[MonitorInfo],
    *,
    prefer_primary: bool = True,
    monitor_index: int | None = None,
) -> MonitorInfo:
    if monitor_index is not None:
        for m in monitors:
            if m.index == monitor_index:
                return m
        raise ValueError(f"monitor_index={monitor_index} not found")
    if prefer_primary:
        for m in monitors:
            if m.is_primary:
                return m
    if not monitors:
        raise RuntimeError("no monitors detected")
    return monitors[0]


def capture_monitor_png_bytes(
    config: ScreenCaptureConfig | None = None,
) -> tuple[bytes, MonitorInfo]:
    """Grab one monitor frame and crop to the info panel (PNG bytes).

    Intended for Streamlit 「抓取当前屏幕」; OCR path reuses
    ``bidking_lab.capture.ocr.crop_info_panel`` on the result.
    """
    cfg = config or ScreenCaptureConfig()
    monitors = list_monitors()
    mon = resolve_monitor(monitors, monitor_index=cfg.monitor_index)

    try:
        import mss
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("需要 mss + Pillow") from exc

    import io

    with mss.mss() as sct:
        shot = sct.grab(
            {
                "left": mon.left,
                "top": mon.top,
                "width": mon.width,
                "height": mon.height,
            },
        )
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    if (
        mon.width != cfg.reference_width
        or mon.height != cfg.reference_height
    ):
        # Keep crop fractions defined on 1920×1080 stable across DPI/res changes.
        pass
    box = fraction_to_pixel_box(mon.width, mon.height, cfg.crop_frac)
    cropped = img.crop(box)
    out = io.BytesIO()
    cropped.save(out, format="PNG", optimize=True)
    return out.getvalue(), mon
