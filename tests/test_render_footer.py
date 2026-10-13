from PIL import Image

from film_contact_sheet.models import OutputSize
from film_contact_sheet.render import render_sheet


def test_hidden_footer_line_adds_no_ink(roll_of, settings):
    template = roll_of.template
    template.show_film_name = False
    template.show_order = False
    template.show_date = False
    template.show_count = False
    blank = render_sheet(roll_of.roll, template, settings, (1080, 1350))
    template.show_film_name = True
    named = render_sheet(roll_of.roll, template, settings, (1080, 1350))
    assert _ink(blank.crop((0, 1080, 1080, 1350))) == 0
    assert _ink(named.crop((0, 1080, 1080, 1350))) > 0


def test_dark_background_uses_white_text(tmp_path, roll_of, settings):
    background = tmp_path / "dark.png"
    Image.new("RGB", (20, 20), (0, 20, 40)).save(background)
    template = roll_of.template
    template.background_path = str(background)
    template.show_order = False
    template.show_date = False
    template.show_count = False
    image = render_sheet(roll_of.roll, template, settings, (1080, 1350))
    footer = image.crop((0, 1080, 1080, 1350))
    assert any(min(pixel) > 200 for pixel in footer.getdata())


def test_missing_background_is_white_and_sizes_match_template(tmp_path, roll_of, settings):
    template = roll_of.template
    template.background_path = str(tmp_path / "gone.png")
    template.strip_path = str(tmp_path / "gone-strip.png")
    for size, pixels in (
        (OutputSize.SOCIAL, (1080, 1350)),
        (OutputSize.SHARP, (2160, 2700)),
        (OutputSize.A4, (2480, 3100)),
    ):
        template.output_size = size
        image = render_sheet(roll_of.roll, template, settings)
        assert image.size == pixels
    assert render_sheet(roll_of.roll, template, settings, (1080, 1350)).getpixel((10, 1300)) == (
        255,
        255,
        255,
    )


def _ink(image):
    return sum(1 for pixel in image.getdata() if pixel != (255, 255, 255))
