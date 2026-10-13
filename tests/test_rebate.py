from PIL import Image, ImageDraw

from film_contact_sheet.rebate import split_rebate


def test_sprocket_band_marks_135_and_returns_the_inner_picture():
    image = Image.new("RGB", (200, 120), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 24, 199, 96), fill=(20, 180, 40))
    for x in range(8, 200, 24):
        draw.rectangle((x, 4, x + 10, 16), fill="white")
        draw.rectangle((x, 104, x + 10, 116), fill="white")
    split = split_rebate(image)
    assert split.has_sprockets is True
    assert split.uncertain is False
    _x, y, _w, h = split.picture_box
    assert 16 <= y <= 32
    assert 60 <= h <= 90


def test_flat_image_is_uncertain_and_has_no_sprockets():
    split = split_rebate(Image.new("RGB", (80, 60), (20, 180, 40)))
    assert split.has_sprockets is False
    assert split.uncertain is True
    assert split.picture_box == (0, 0, 80, 60)


def test_orange_border_without_holes_is_a_certain_inner_picture():
    image = Image.new("RGB", (100, 80), (180, 90, 30))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 10, 87, 69), fill=(20, 180, 40))
    split = split_rebate(image)
    assert split.has_sprockets is False
    assert split.uncertain is False
    x, y, w, h = split.picture_box
    assert x >= 8 and y >= 6
    assert w < 100 and h < 80
