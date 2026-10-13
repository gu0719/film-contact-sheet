from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path

from PIL import Image


class FormatId(str, Enum):
    F135 = "135"
    F645 = "645"
    F66 = "66"
    F67 = "67"
    F68 = "68"
    F69 = "69"


class ColorMode(str, Enum):
    SRGB = "sRGB"
    CMYK = "CMYK"


class OutputSize(str, Enum):
    SOCIAL = "1080×1350"
    SHARP = "2160×2700"
    A4 = "2480×3100"


SIZE_PIXELS = {
    OutputSize.SOCIAL: (1080, 1350),
    OutputSize.SHARP: (2160, 2700),
    OutputSize.A4: (2480, 3100),
}

ROW_CYCLES = {
    FormatId.F135: (6,),
    FormatId.F645: (4,),
    FormatId.F66: (3,),
    FormatId.F67: (3, 3, 2, 2),
    FormatId.F68: (3,),
    FormatId.F69: (2,),
}

WINDOW_RATIO = {
    FormatId.F135: 3 / 2,
    FormatId.F645: 4 / 3,
    FormatId.F66: 1.0,
    FormatId.F67: 7 / 6,
    FormatId.F68: 4 / 3,
    FormatId.F69: 3 / 2,
}


@dataclass
class Frame:
    source_path: Path
    filename: str
    edge_number: int | None
    picture_box: tuple[int, int, int, int] | None
    uncertain_aspect: bool
    has_sprockets: bool
    oriented_size: tuple[int, int]
    date: date | None
    warning: str = ""
    image: Image.Image | None = None


@dataclass
class FormatGuess:
    format_id: FormatId
    confirmed: bool
    aspect_ratio: float | None


@dataclass
class Roll:
    folder: Path
    order_number: str
    shoot_date: date | None
    film_name: str
    format_guess: FormatGuess
    frames: list[Frame] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Template:
    id: str
    name: str
    background_path: str
    strip_path: str
    show_film_name: bool
    show_order: bool
    show_date: bool
    show_count: bool
    color_mode: ColorMode
    output_size: OutputSize
    builtin: bool


@dataclass
class Settings:
    brand_text: str
    backgrounds_dir: Path
    strips_dir: Path
    last_template_id: str
    last_export_dir: Path | None
    templates: list[Template]
    film_presets: list[str]


def default_template() -> Template:
    return Template(
        id="default",
        name="默认",
        background_path="",
        strip_path="",
        show_film_name=True,
        show_order=True,
        show_date=True,
        show_count=True,
        color_mode=ColorMode.SRGB,
        output_size=OutputSize.SHARP,
        builtin=True,
    )
