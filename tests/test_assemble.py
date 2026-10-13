from PIL import Image

from film_contact_sheet.assemble import build_roll
from film_contact_sheet.film_names import FACTORY_PRESETS
from film_contact_sheet.models import FormatId


class FakeReader:
    def __init__(self, text):
        self.text = text

    def read(self, image):
        return self.text


def test_build_roll_sorts_numbers_and_names_the_folder(tmp_path):
    for name, color in (("b.jpg", (255, 0, 0)), ("a.jpg", (0, 255, 0))):
        image = Image.new("RGB", (80, 56), (180, 90, 30))
        draw_box = (10, 8, 69, 47)
        from PIL import ImageDraw

        ImageDraw.Draw(image).rectangle(draw_box, fill=color)
        image.save(tmp_path / name)
    roll = build_roll(tmp_path, FakeReader("3 PORTRA 400"), list(FACTORY_PRESETS))
    assert roll.order_number == tmp_path.name
    assert roll.film_name == "Kodak Portra 400"
    assert roll.frames[0].edge_number == 3
    assert roll.format_guess.format_id == FormatId.F69
    assert roll.format_guess.confirmed is True
    assert "序号重复" in roll.frames[0].warning
    assert "序号重复" in roll.frames[1].warning
