from datetime import date

from PIL import Image

from film_contact_sheet.meta import (
    average_luminance,
    choose_date,
    export_filename,
    footer_lines,
    text_rgb,
)
from film_contact_sheet.models import default_template


def test_choose_date_uses_the_most_common_then_the_earlier_day():
    first = date(2026, 3, 28)
    second = date(2026, 4, 1)
    assert choose_date([first, second, first, None]) == first
    assert choose_date([second, first]) == first
    assert choose_date([None, None]) is None


def test_export_filename_replaces_illegal_characters():
    assert export_filename("318167") == "318167.jpg"
    assert export_filename("a/b:c*") == "a_b_c_.jpg"
    assert export_filename("   ") == "contact-sheet.jpg"


def test_footer_lines_follow_the_toggles():
    template = default_template()
    assert footer_lines("Fuji", "318167", date(2026, 3, 28), 1, template) == [
        "Fuji",
        "Order: 318167",
        "2026-03-28 | 1 images",
    ]
    template.show_film_name = False
    template.show_order = False
    template.show_date = False
    assert footer_lines("Fuji", "318167", None, 36, template) == ["36 images"]
    template.show_count = False
    assert footer_lines("Fuji", "318167", None, 36, template) == []
    template.show_date = True
    template.show_count = False
    assert footer_lines("", "", date(2026, 3, 28), 36, template) == ["2026-03-28"]


def test_text_color_threshold_and_luminance():
    assert text_rgb(0.61) == (0x1A, 0x1A, 0x1A)
    assert text_rgb(0.6) == (255, 255, 255)
    white = Image.new("RGB", (4, 4), "white")
    assert average_luminance(white, (0, 0, 4, 4)) > 0.6
