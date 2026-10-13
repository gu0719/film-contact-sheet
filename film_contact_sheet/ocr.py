from __future__ import annotations

import re

from PIL import Image


def parse_edge_number(text: str) -> int | None:
    for token in re.findall(r"\d+", text):
        number = int(token)
        if 0 <= number <= 99:
            return number
    return None


class RapidRebateReader:
    def __init__(self, engine=None):
        self._engine = engine

    def read(self, rebate: Image.Image) -> str:
        engine = self._engine
        if engine is None:
            from rapidocr_onnxruntime import RapidOCR

            engine = RapidOCR()
            self._engine = engine
        import numpy as np

        parts: list[str] = []
        for strip in _ocr_strips(rebate):
            try:
                result, _elapsed = engine(np.asarray(strip))
            except Exception:
                continue
            if not result:
                continue
            parts.append(" ".join(item[1] for item in result))
        return " ".join(parts)


def _ocr_strips(rebate: Image.Image) -> list[Image.Image]:
    """Keep every strip inside the size RapidOCR can resize.

    A wide rebate used to be enlarged 3x. RapidOCR then rounds both sides to a
    multiple of 32, and a short side collapses to 0. Strips stay at most 960
    on the long side and at least 32 on the short side, read from left to right.
    """
    rgb = rebate.convert("RGB")
    if rgb.width < 1 or rgb.height < 1:
        return [Image.new("RGB", (32, 32), "black")]
    if rgb.width >= rgb.height:
        target = _band_size(rgb.height)
        if rgb.height != target:
            rgb = rgb.resize((max(1, rgb.width), target), Image.Resampling.LANCZOS)
    else:
        target = _band_size(rgb.width)
        if rgb.width != target:
            rgb = rgb.resize((target, max(1, rgb.height)), Image.Resampling.LANCZOS)
    rgb = _pad_min(rgb, 32)
    return [_pad_min(strip, 32) for strip in _chunks(rgb)]


def _band_size(short_side: int) -> int:
    if short_side < 32:
        return 48
    if short_side > 96:
        return 96
    return short_side


def _pad_min(image: Image.Image, minimum: int) -> Image.Image:
    if image.width >= minimum and image.height >= minimum:
        return image
    color = image.getpixel((0, 0))
    canvas = Image.new(
        "RGB",
        (max(image.width, minimum), max(image.height, minimum)),
        color,
    )
    canvas.paste(image, (0, 0))
    return canvas


def _chunks(image: Image.Image) -> list[Image.Image]:
    horizontal = image.width >= image.height
    span = image.width if horizontal else image.height
    step = 960
    overlap = 64
    if span <= step:
        return [image]
    strips = []
    start = 0
    while start < span:
        end = min(span, start + step)
        if horizontal:
            strips.append(image.crop((start, 0, end, image.height)))
        else:
            strips.append(image.crop((0, start, image.width, end)))
        if end == span:
            break
        start = end - overlap
    return strips
