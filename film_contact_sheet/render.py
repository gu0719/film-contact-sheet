from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from film_contact_sheet.layout import layout_sheet
from film_contact_sheet.meta import average_luminance, footer_lines, text_rgb
from film_contact_sheet.models import SIZE_PIXELS, Frame, Roll, Settings, Template
from film_contact_sheet.sprocket import default_sprocket

FONT_PATH = Path(__file__).resolve().parent / "assets" / "NotoSansSC-Regular.otf"
NUMBER_COLOR = (0xF2, 0xC1, 0x4B)


def render_sheet(
    roll: Roll,
    template: Template,
    settings: Settings,
    target_size: tuple[int, int] | None = None,
    proof: bool = False,
) -> Image.Image:
    canvas_size = target_size or SIZE_PIXELS[template.output_size]
    image = Image.new("RGB", canvas_size, "white")
    _paste_background(image, template.background_path)
    if not roll.frames:
        return _maybe_proof(image, proof)
    layout = layout_sheet(canvas_size, roll.format_guess.format_id, len(roll.frames), True)
    strip = _load_strip(template.strip_path)
    font_path = FONT_PATH
    for row_box, cells in layout.rows:
        _paste_strip(image, strip, _tile_span(row_box, cells))
        for cell in cells:
            if cell.frame_index is None:
                ImageDraw.Draw(image).rectangle(_xyxy(cell.box), fill="black")
                continue
            frame = roll.frames[cell.frame_index]
            photo = _window_image(frame, cell.box[2] / cell.box[3])
            image.paste(photo.resize((cell.box[2], cell.box[3]), Image.Resampling.LANCZOS), cell.box[:2])
            if frame.edge_number is not None and font_path.exists():
                _draw_number(image, row_box, cell.box, str(frame.edge_number), font_path)
        if settings.brand_text.strip() and font_path.exists():
            _draw_brand(image, _tile_span(row_box, cells), settings.brand_text.strip(), font_path)
    _draw_footer(image, roll, template, font_path)
    return _maybe_proof(image, proof)


def _maybe_proof(image: Image.Image, proof: bool) -> Image.Image:
    if not proof:
        return image
    from film_contact_sheet.color_profile import soft_proof

    return soft_proof(image)


def _paste_background(image: Image.Image, path: str) -> None:
    if not path or not Path(path).is_file():
        return
    try:
        with Image.open(path) as background:
            cover = _cover(background.convert("RGB"), image.width / image.height)
            image.paste(cover.resize(image.size, Image.Resampling.LANCZOS), (0, 0))
    except OSError:
        return


def _load_strip(path: str) -> Image.Image:
    if path and Path(path).is_file():
        try:
            with Image.open(path) as strip:
                return strip.convert("RGB")
        except OSError:
            return default_sprocket()
    return default_sprocket()


def _tile_span(row_box: tuple[int, int, int, int], cells) -> tuple[int, int, int, int]:
    if not cells:
        return row_box
    left = min(cell.tile[0] for cell in cells)
    right = max(cell.tile[0] + cell.tile[2] for cell in cells)
    top = min(cell.tile[1] for cell in cells)
    height = max(cell.tile[3] for cell in cells)
    return left, top, max(1, right - left), height


def _paste_strip(image: Image.Image, strip: Image.Image, row_box: tuple[int, int, int, int]) -> None:
    x, y, width, height = row_box
    scaled_h = max(1, height)
    scale = scaled_h / strip.height
    scaled_w = max(1, round(strip.width * scale))
    tile = strip.resize((scaled_w, scaled_h), Image.Resampling.NEAREST)
    row = Image.new("RGB", (width, scaled_h), "black")
    cursor = 0
    while cursor < width:
        row.paste(tile, (cursor, 0))
        cursor += tile.width
    image.paste(row, (x, y))


def _window_image(frame: Frame, aspect: float) -> Image.Image:
    source = frame.image if frame.image is not None else Image.new("RGB", frame.oriented_size, "black")
    return _contain(_turn_landscape(source, aspect), aspect)


def _turn_landscape(image: Image.Image, aspect: float) -> Image.Image:
    if aspect <= 1 or image.height <= image.width:
        return image
    return image.transpose(Image.Transpose.ROTATE_90)


def _contain(image: Image.Image, aspect: float) -> Image.Image:
    width, height = image.size
    if width <= 0 or height <= 0:
        return image
    current = width / height
    if abs(current - aspect) < 0.02:
        return image
    if current > aspect:
        canvas_h = max(1, round(width / aspect))
        canvas = Image.new("RGB", (width, canvas_h), "black")
        canvas.paste(image, (0, (canvas_h - height) // 2))
        return canvas
    canvas_w = max(1, round(height * aspect))
    canvas = Image.new("RGB", (canvas_w, height), "black")
    canvas.paste(image, ((canvas_w - width) // 2, 0))
    return canvas


def _cover(image: Image.Image, aspect: float) -> Image.Image:
    width, height = image.size
    if width <= 0 or height <= 0:
        return image
    current = width / height
    if current > aspect:
        new_width = max(1, round(height * aspect))
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    new_height = max(1, round(width / aspect))
    top = (height - new_height) // 2
    return image.crop((0, top, width, top + new_height))


def _draw_number(image, row_box, cell_box, text, font_path: Path) -> None:
    _x, row_y, _w, row_h = row_box
    rebate_top = row_y + round(row_h * 0.84)
    rebate_h = max(1, row_y + row_h - rebate_top)
    size = max(8, int(rebate_h * 0.45))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path), size)
    text_w = draw.textlength(text, font=font)
    x = cell_box[0] + (cell_box[2] - text_w) / 2
    y = rebate_top + (rebate_h - size) / 2
    draw.text((x, y), text, fill=NUMBER_COLOR, font=font)


def _draw_brand(image, row_box, text, font_path: Path) -> None:
    _x, row_y, row_w, row_h = row_box
    rebate_h = max(1, round(row_h * 0.16))
    start = max(8, int(rebate_h * 0.4))
    minimum = max(6, start // 2)
    max_width = row_w - round(row_w * 0.04)
    draw = ImageDraw.Draw(image)
    size = start
    font = ImageFont.truetype(str(font_path), size)
    while size > minimum and draw.textlength(text, font=font) > max_width:
        size -= 1
        font = ImageFont.truetype(str(font_path), size)
    x = round(row_w * 0.02)
    y = row_y + (rebate_h - size) / 2
    if draw.textlength(text, font=font) <= max_width:
        draw.text((x, y), text, fill=NUMBER_COLOR, font=font)
        return
    scratch = Image.new("RGBA", (max_width, rebate_h), (0, 0, 0, 0))
    ImageDraw.Draw(scratch).text((0, 0), text, fill=NUMBER_COLOR + (255,), font=font)
    image.paste(scratch.convert("RGB"), (x, row_y), scratch)


def _draw_footer(image, roll: Roll, template: Template, font_path: Path) -> None:
    if not font_path.exists():
        return
    lines = footer_lines(roll.film_name, roll.order_number, roll.shoot_date, len(roll.frames), template)
    if not lines:
        return
    width, height = image.size
    sizes = [max(10, round(height * scale)) for scale in (0.028, 0.018, 0.014)]
    fonts = [ImageFont.truetype(str(font_path), size) for size in sizes[: len(lines)]]
    draw = ImageDraw.Draw(image)
    gap = max(2, round(height * 0.006))
    line_boxes = []
    total_h = 0
    max_w = 0
    for line, font, size in zip(lines, fonts, sizes[: len(lines)]):
        text_w = draw.textlength(line, font=font)
        line_boxes.append((line, font, text_w, size))
        max_w = max(max_w, text_w)
        total_h += size
    total_h += gap * (len(lines) - 1)
    right = width - round(width * 0.04)
    bottom = height - round(height * 0.05)
    block = (
        int(right - max_w),
        int(bottom - total_h),
        int(right),
        int(bottom),
    )
    color = text_rgb(average_luminance(image, block))
    y = bottom - total_h
    for line, font, text_w, size in line_boxes:
        draw.text((right - text_w, y), line, fill=color, font=font)
        y += size + gap


def _xyxy(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, width, height = box
    return x, y, x + width, y + height
