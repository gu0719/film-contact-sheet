from __future__ import annotations

import re
from collections import Counter
from datetime import date

from PIL import Image

from film_contact_sheet.models import Template

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def choose_date(dates: list[date | None]) -> date | None:
    present = [value for value in dates if value is not None]
    if not present:
        return None
    counts = Counter(present)
    highest = max(counts.values())
    return min(value for value, count in counts.items() if count == highest)


def export_filename(order_number: str) -> str:
    cleaned = _ILLEGAL.sub("_", order_number).strip().rstrip(". ")
    if not cleaned:
        cleaned = "contact-sheet"
    return cleaned + ".jpg"


def footer_lines(
    film_name: str,
    order_number: str,
    shoot_date: date | None,
    count: int,
    template: Template,
) -> list[str]:
    lines = []
    if template.show_film_name and film_name.strip():
        lines.append(film_name.strip())
    if template.show_order and order_number.strip():
        lines.append(f"Order: {order_number.strip()}")
    date_part = shoot_date.isoformat() if shoot_date else ""
    count_part = f"{count} images"
    meta = None
    if template.show_date and template.show_count and date_part:
        meta = f"{date_part} | {count_part}"
    elif template.show_date and not template.show_count and date_part:
        meta = date_part
    elif template.show_count:
        meta = count_part
    if meta:
        lines.append(meta)
    return lines


def text_rgb(luminance: float) -> tuple[int, int, int]:
    if luminance > 0.6:
        return (0x1A, 0x1A, 0x1A)
    return (255, 255, 255)


def average_luminance(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    crop = image.crop(box).convert("RGB")
    pixels = list(crop.get_flattened_data())
    if not pixels:
        return 1.0
    return sum(_relative_luminance(pixel) for pixel in pixels) / len(pixels)


def _relative_luminance(pixel: tuple[int, int, int]) -> float:
    def channel(value: int) -> float:
        x = value / 255
        if x <= 0.04045:
            return x / 12.92
        return ((x + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(pixel[0]), channel(pixel[1]), channel(pixel[2]))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue
