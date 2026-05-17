"""Optional OCR helpers — soft dependency."""

from __future__ import annotations

import io
import logging
import threading
from typing import Any, Literal

from bidking_lab.capture.log_util import LOG, configure_capture_logging
from bidking_lab.capture.ocr_normalize import normalize_ocr_text
from bidking_lab.capture.screen import INFO_PANEL_CROP_FRAC

configure_capture_logging()

_ENGINE: Any = None
_warm_lock = threading.Lock()
_warm_status: Literal["idle", "loading", "ready", "error"] = "idle"
_warm_error: str | None = None

_PANEL_CROP = INFO_PANEL_CROP_FRAC


def _get_engine() -> Any:
    global _ENGINE  # noqa: PLW0603
    if _ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR

        _ENGINE = RapidOCR()
    return _ENGINE


def warm_ocr_engine() -> None:
    """Load RapidOCR via the same crop/resize path as real screenshots."""
    from bidking_lab.capture.screen import OCR_WARMUP_SAMPLE

    if OCR_WARMUP_SAMPLE.is_file():
        payload = OCR_WARMUP_SAMPLE.read_bytes()
    else:
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("需要 Pillow：pip install pillow") from exc
        buf = io.BytesIO()
        Image.new("RGB", (1920, 1080), color=(32, 34, 38)).save(buf, format="PNG")
        payload = buf.getvalue()
    _text, err = image_bytes_to_text(payload)
    if err and "未安装" in err:
        raise RuntimeError(err)


def start_ocr_warmup_background() -> None:
    """Start one background warm-up per process (does not block the UI thread)."""
    global _warm_status, _warm_error  # noqa: PLW0603
    with _warm_lock:
        if _warm_status in ("loading", "ready"):
            return
        _warm_status = "loading"
        _warm_error = None

    def _worker() -> None:
        global _warm_status, _warm_error  # noqa: PLW0603
        try:
            warm_ocr_engine()
            with _warm_lock:
                _warm_status = "ready"
        except Exception as exc:  # noqa: BLE001
            with _warm_lock:
                _warm_status = "error"
                _warm_error = str(exc)

    threading.Thread(target=_worker, daemon=True, name="ocr-warmup").start()


def ocr_warmup_status() -> tuple[str, str | None]:
    """Return ``(status, error)`` where status is idle|loading|ready|error."""
    with _warm_lock:
        return _warm_status, _warm_error


def crop_info_panel(
    data: bytes,
    *,
    crop: tuple[float, float, float, float] = _PANEL_CROP,
) -> bytes:
    """Crop to the center-left bidding panel (less noise, faster OCR)."""
    try:
        from PIL import Image
    except ImportError:
        return data

    img = Image.open(io.BytesIO(data))
    w, h = img.size
    l, t, r, b = crop
    box = (int(w * l), int(h * t), int(w * r), int(h * b))
    cropped = img.crop(box)
    out = io.BytesIO()
    cropped.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _maybe_downscale(data: bytes, max_side: int = 1280) -> bytes:
    """Shrink large screenshots so OCR is faster (full-screen PNGs are slow)."""
    try:
        from PIL import Image
    except ImportError:
        return data

    img = Image.open(io.BytesIO(data))
    w, h = img.size
    if max(w, h) <= max_side:
        return data
    scale = max_side / max(w, h)
    img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def image_bytes_to_text(
    data: bytes,
    *,
    max_side: int = 1280,
    crop_panel: bool = True,
) -> tuple[str, str | None]:
    """Run OCR if ``rapidocr_onnxruntime`` is installed.

    Returns ``(text, error_message)``. On success ``error_message`` is None.
    """
    try:
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401
    except ImportError:
        return "", (
            "未安装 OCR 引擎。请用与 Streamlit 相同的 Python 执行：\n"
            "C:\\Python313\\python.exe -m pip install rapidocr-onnxruntime "
            "--default-timeout=600\n"
            "或手动复制游戏左侧文字到文本框。"
        )

    try:
        if crop_panel:
            data = crop_info_panel(data)
        data = _maybe_downscale(data, max_side=max_side)
        engine = _get_engine()
        result, _ = engine(data)
    except Exception as exc:  # noqa: BLE001
        return "", f"OCR 失败: {exc}"

    if not result:
        return "", "OCR 未识别到文字，请检查截图区域或改用手动粘贴。"

    lines = [str(row[1]).strip() for row in result if len(row) > 1 and row[1]]
    text = normalize_ocr_text("\n".join(lines))
    LOG.info(
        "OCR ok: %d lines, crop_panel=%s, crop_frac=%s",
        len(lines),
        crop_panel,
        _PANEL_CROP if crop_panel else None,
    )
    if LOG.isEnabledFor(logging.DEBUG):
        LOG.debug("OCR text:\n%s", text[:2000])
    return text, None
