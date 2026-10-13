from __future__ import annotations

from pathlib import Path

from PIL import Image

from film_contact_sheet.film_names import match_film_name
from film_contact_sheet.format_guess import guess_format
from film_contact_sheet.frames import apply_warnings, sort_frames
from film_contact_sheet.ingest import scan_folder
from film_contact_sheet.meta import choose_date
from film_contact_sheet.models import Frame, Roll
from film_contact_sheet.rebate import split_rebate


def build_roll(folder: Path, reader, presets: list[str]) -> Roll:
    loaded, skipped = scan_folder(folder)
    frames: list[Frame] = []
    texts: list[str] = []
    aspects: list[float | None] = []
    sprockets: list[bool] = []
    for item in loaded:
        frame, text, aspect, sprocket = read_frame(item, reader)
        frames.append(frame)
        texts.append(text)
        aspects.append(aspect)
        sprockets.append(sprocket)
    return finish_roll(folder, frames, texts, aspects, sprockets, skipped, presets)


def read_frame(item, reader) -> tuple[Frame, str, float | None, bool]:
    split = split_rebate(item.image)
    if split.uncertain:
        number = None
        text = ""
        aspect = None
    else:
        rebate = _rebate_image(item.image, split.picture_box)
        try:
            text = reader.read(rebate)
        except Exception:
            text = ""
        number = parse_number(text)
        width, height = split.picture_box[2], split.picture_box[3]
        aspect = max(width, height) / min(width, height)
    frame = Frame(
        source_path=item.path,
        filename=item.filename,
        edge_number=number,
        picture_box=None if split.uncertain else split.picture_box,
        uncertain_aspect=split.uncertain,
        has_sprockets=split.has_sprockets,
        oriented_size=item.image.size,
        date=item.date,
        image=item.image,
    )
    return frame, text, aspect, split.has_sprockets


def finish_roll(folder, frames, texts, aspects, sprockets, skipped, presets: list[str]) -> Roll:
    ordered = sort_frames(frames)
    apply_warnings(ordered)
    return Roll(
        folder=folder,
        order_number=folder.name,
        shoot_date=choose_date([frame.date for frame in ordered]),
        film_name=match_film_name(" ".join(texts), presets),
        format_guess=guess_format(aspects, sprockets),
        frames=ordered,
        skipped=skipped,
    )


def parse_number(text: str):
    from film_contact_sheet.ocr import parse_edge_number

    return parse_edge_number(text)


def _rebate_image(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x, y, width, height = box
    full_w, full_h = image.size
    top = image.crop((0, 0, full_w, y)) if y > 0 else None
    bottom_start = y + height
    bottom = image.crop((0, bottom_start, full_w, full_h)) if bottom_start < full_h else None
    parts = [part for part in (top, bottom) if part is not None and part.height > 0]
    if not parts:
        return image.crop((x, y, x + width, y + height))
    canvas_h = sum(part.height for part in parts)
    canvas = Image.new("RGB", (full_w, canvas_h))
    cursor = 0
    for part in parts:
        canvas.paste(part, (0, cursor))
        cursor += part.height
    return canvas
