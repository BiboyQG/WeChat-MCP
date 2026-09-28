"""
Screen capture and text recognition helpers.

- ``capture_window_region`` grabs a region of the WeChat window straight
  from the window server (``CGWindowListCreateImage``), which works even
  when WeChat is behind other windows, so reading a chat does not need to
  steal focus. It needs the Screen Recording permission; without it the
  capture comes back blank and callers fall back to a screen grab.
- ``recognize_text`` runs Apple's Vision text recognition on a PIL image
  (used to read the sender name WeChat paints above bubbles in group
  chats, which is not exposed through Accessibility).
"""

from __future__ import annotations


import Quartz
from PIL import Image, ImageGrab

from .logging_config import logger

try:  # Vision is part of the pyobjc meta package; keep it optional anyway.
    import Vision  # type: ignore
    import Foundation  # type: ignore
except Exception:  # noqa: BLE001  pragma: no cover - depends on host setup
    Vision = None
    Foundation = None


def find_window_id(pid: int, frame: tuple[float, float, float, float] | None) -> int | None:
    """
    Return the CGWindowID of the on-screen window owned by ``pid`` whose
    bounds match ``frame`` (x, y, w, h in points); falls back to the
    largest window of that process.
    """
    options = (
        Quartz.kCGWindowListOptionOnScreenOnly
        | Quartz.kCGWindowListExcludeDesktopElements
    )
    infos = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or []
    best_id = None
    best_area = -1.0
    for info in infos:
        if int(info.get(Quartz.kCGWindowOwnerPID, -1)) != pid:
            continue
        if int(info.get(Quartz.kCGWindowLayer, 0)) != 0:
            continue
        bounds = info.get(Quartz.kCGWindowBounds) or {}
        x, y = float(bounds.get("X", 0)), float(bounds.get("Y", 0))
        w, h = float(bounds.get("Width", 0)), float(bounds.get("Height", 0))
        window_id = int(info.get(Quartz.kCGWindowNumber))
        if frame is not None and all(
            abs(a - b) <= 2 for a, b in zip((x, y, w, h), frame)
        ):
            return window_id
        if w * h > best_area:
            best_area = w * h
            best_id = window_id
    return best_id


def _cgimage_to_pil(cg_image) -> Image.Image | None:
    if cg_image is None:
        return None
    width = Quartz.CGImageGetWidth(cg_image)
    height = Quartz.CGImageGetHeight(cg_image)
    if width == 0 or height == 0:
        return None
    bytes_per_row = Quartz.CGImageGetBytesPerRow(cg_image)
    provider = Quartz.CGImageGetDataProvider(cg_image)
    data = Quartz.CGDataProviderCopyData(provider)
    buffer = bytes(data)
    # WeChat windows come back as 32-bit BGRA (little-endian ARGB).
    image = Image.frombuffer(
        "RGBA", (width, height), buffer, "raw", "BGRA", bytes_per_row, 1
    )
    return image.convert("RGB")


def capture_window_region(
    window_id: int,
    window_frame: tuple[float, float, float, float],
    region: tuple[float, float, float, float],
) -> Image.Image | None:
    """
    Capture ``region`` (screen coordinates, points) of the given window
    without requiring it to be frontmost. The returned image is resized
    to point dimensions so pixels map 1:1 onto Accessibility coordinates.
    Returns None when the window server refuses (no Screen Recording
    permission) or the capture is empty.
    """
    cg_image = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,
        Quartz.kCGWindowListOptionIncludingWindow,
        window_id,
        Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageNominalResolution,
    )
    image = _cgimage_to_pil(cg_image)
    if image is None:
        return None

    wx, wy, ww, wh = window_frame
    if ww <= 0 or wh <= 0:
        return None
    scale_x = image.width / ww
    scale_y = image.height / wh

    rx, ry, rw, rh = region
    left = int(round((rx - wx) * scale_x))
    top = int(round((ry - wy) * scale_y))
    right = int(round((rx - wx + rw) * scale_x))
    bottom = int(round((ry - wy + rh) * scale_y))
    left, top = max(0, left), max(0, top)
    right, bottom = min(image.width, right), min(image.height, bottom)
    if right <= left or bottom <= top:
        return None
    cropped = image.crop((left, top, right, bottom))
    if cropped.size != (int(rw), int(rh)):
        cropped = cropped.resize((max(1, int(rw)), max(1, int(rh))))
    return cropped


def capture_screen_region(region: tuple[float, float, float, float]) -> Image.Image:
    """Screen grab fallback (requires the region to be unobscured)."""
    x, y, w, h = region
    return ImageGrab.grab(bbox=(int(x), int(y), int(x + w), int(y + h))).convert("RGB")


def looks_blank(image: Image.Image) -> bool:
    """True when the capture is uniform (typical for a denied capture)."""
    extrema = image.getextrema()
    return all(lo == hi for lo, hi in extrema)


def _pil_to_cgimage(image: Image.Image):
    rgba = image.convert("RGBA")
    data = rgba.tobytes()
    provider = Quartz.CGDataProviderCreateWithData(None, data, len(data), None)
    color_space = Quartz.CGColorSpaceCreateDeviceRGB()
    return Quartz.CGImageCreate(
        rgba.width,
        rgba.height,
        8,
        32,
        rgba.width * 4,
        color_space,
        Quartz.kCGImageAlphaPremultipliedLast,
        provider,
        None,
        False,
        Quartz.kCGRenderingIntentDefault,
    )


def recognize_text(
    image: Image.Image,
    languages: tuple[str, ...] = ("zh-Hans", "en-US"),
    upscale: int = 2,
) -> list[str]:
    """
    Run Vision text recognition on ``image`` and return the recognised
    lines in reading order (top to bottom, left to right). Returns an
    empty list when Vision is unavailable.
    """
    if Vision is None:
        return []
    if upscale > 1:
        image = image.resize((image.width * upscale, image.height * upscale), Image.LANCZOS)
    cg_image = _pil_to_cgimage(image)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(False)
    try:
        request.setRecognitionLanguages_(list(languages))
    except Exception:  # noqa: BLE001
        pass
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
    ok, error = handler.performRequests_error_([request], None)
    if not ok:
        logger.debug("Vision text recognition failed: %s", error)
        return []
    observations = request.results() or []
    lines: list[tuple[float, float, str]] = []
    for obs in observations:
        candidates = obs.topCandidates_(1)
        if not candidates:
            continue
        text = str(candidates[0].string()).strip()
        if not text:
            continue
        box = obs.boundingBox()
        # Vision uses a bottom-left origin; sort top-to-bottom, left-to-right.
        lines.append((-float(box.origin.y), float(box.origin.x), text))
    lines.sort()
    return [text for _, _, text in lines]
