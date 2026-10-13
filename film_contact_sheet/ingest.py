from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from PIL import Image, ImageCms, ImageOps


class NoJpegError(Exception):
    pass


@dataclass
class LoadedImage:
    path: Path
    filename: str
    image: Image.Image
    date: date | None


def list_jpegs(folder: Path) -> list[Path]:
    candidates = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
    ]
    if not candidates:
        raise NoJpegError("这个文件夹里没有 JPG。")
    return sorted(candidates, key=lambda item: item.name)


def load_frame(path: Path) -> LoadedImage:
    image, taken = _open_frame(path)
    return LoadedImage(path, path.name, image, taken)


def scan_folder(folder: Path) -> tuple[list[LoadedImage], list[tuple[str, str]]]:
    loaded: list[LoadedImage] = []
    skipped: list[tuple[str, str]] = []
    for path in list_jpegs(folder):
        try:
            loaded.append(load_frame(path))
        except OSError:
            skipped.append((path.name, "无法打开"))
    return loaded, skipped


_LONG_SIDE = 2400


def _open_frame(path: Path) -> tuple[Image.Image, date | None]:
    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None
    try:
        with Image.open(path) as raw:
            raw.draft("RGB", (_LONG_SIDE, _LONG_SIDE))
            if max(raw.size) > _LONG_SIDE:
                raw.thumbnail((_LONG_SIDE, _LONG_SIDE), Image.Resampling.LANCZOS)
            icc = raw.info.get("icc_profile")
            exif = raw.getexif()
            taken = _exif_date(exif) or datetime.fromtimestamp(path.stat().st_mtime).date()
            image = ImageOps.exif_transpose(raw)
            image = image.convert("RGB")
            image = _limit_long_side(image, _LONG_SIDE)
            if icc:
                image = _to_srgb(image, icc)
            return image, taken
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit


def _limit_long_side(image: Image.Image, limit: int) -> Image.Image:
    width, height = image.size
    long_side = max(width, height)
    if long_side <= limit:
        return image
    scale = limit / long_side
    return image.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))),
        Image.Resampling.LANCZOS,
    )


def _exif_date(exif) -> date | None:
    for tag in (36867, 306):
        value = exif.get(tag)
        if not value or len(str(value)) < 10:
            continue
        text = str(value)[:10]
        try:
            return datetime.strptime(text, "%Y:%m:%d").date()
        except ValueError:
            continue
    return None


def _to_srgb(image: Image.Image, icc: bytes) -> Image.Image:
    try:
        source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        destination = ImageCms.createProfile("sRGB")
        return ImageCms.profileToProfile(image, source, destination, outputMode="RGB")
    except (OSError, ImageCms.PyCMSError):
        return image
