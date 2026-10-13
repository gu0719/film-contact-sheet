from datetime import date
from pathlib import Path

from PIL import Image

from film_contact_sheet.layout import layout_sheet
from film_contact_sheet.models import (
    FormatGuess,
    FormatId,
    Frame,
    OutputSize,
    Roll,
    Settings,
    default_template,
)
from film_contact_sheet.render import render_sheet
from film_contact_sheet.sprocket import default_sprocket


def roll_of(count, fmt):
    frames = []
    for index in range(count):
        image = Image.new("RGB", (30, 20), (10, 140, 30))
        frames.append(
            Frame(
                Path(f"{index}.jpg"),
                f"{index}.jpg",
                index + 1,
                None,
                False,
                False,
                (30, 20),
                date(2026, 3, 28),
                "",
                image,
            )
        )
    return Roll(
        Path("roll"),
        "318167",
        date(2026, 3, 28),
        "Kodak Portra 400",
        FormatGuess(fmt, True, 1.5),
        frames,
        [],
    )


def settings(tmp_path):
    return Settings("", tmp_path, tmp_path, "default", None, [], [])


def test_default_sprocket_has_white_holes_on_black():
    tile = default_sprocket()
    assert tile.getpixel((40, 4)) == (0, 0, 0)
    assert tile.getpixel((40, 18))[0] > 220


def test_black_cells_have_no_yellow_numbers_and_sprockets_reach_both_sides(tmp_path):
    template = default_template()
    template.output_size = OutputSize.SOCIAL
    image = render_sheet(roll_of(1, FormatId.F135), template, settings(tmp_path), (1080, 1350))
    assert image.size == (1080, 1350)
    row_box, cells = layout_sheet((1080, 1350), FormatId.F135, 1, True).rows[0]
    photo_rebate = _bottom_rebate(row_box, cells[0].box)
    black_rebate = _bottom_rebate(row_box, cells[1].box)
    assert _has_yellow(image.crop(photo_rebate))
    assert not _has_yellow(image.crop(black_rebate))
    top_rebate = (0, row_box[1], 1080, max(1, round(row_box[3] * 0.16)))
    left = image.crop((0, top_rebate[1], 540, top_rebate[1] + top_rebate[3]))
    right = image.crop((540, top_rebate[1], 1080, top_rebate[1] + top_rebate[3]))
    assert _has_white(left) and _has_white(right)


def _bottom_rebate(row_box, cell_box):
    _x, row_y, _w, row_h = row_box
    top = row_y + round(row_h * 0.84)
    return (cell_box[0], top, cell_box[0] + cell_box[2], row_y + row_h)


def _has_yellow(image):
    for pixel in image.convert("RGB").getdata():
        red, green, blue = pixel
        if red > 200 and green > 150 and blue < 120:
            return True
    return False


def _has_white(image):
    return any(
        pixel[0] > 220 and pixel[1] > 220 and pixel[2] > 220
        for pixel in image.convert("RGB").getdata()
    )


def test_portrait_frame_fills_the_landscape_window(tmp_path):
    roll = roll_of(1, FormatId.F135)
    portrait = Image.new("RGB", (20, 40), (10, 140, 30))
    roll.frames[0].image = portrait
    roll.frames[0].oriented_size = (20, 40)
    template = default_template()
    template.output_size = OutputSize.SOCIAL
    image = render_sheet(roll, template, settings(tmp_path), (1080, 1350))
    _row, cells = layout_sheet((1080, 1350), FormatId.F135, 1, True).rows[0]
    x, y, width, height = cells[0].box
    assert width > height
    assert image.getpixel((x + 2, y + height // 2))[1] > 100
