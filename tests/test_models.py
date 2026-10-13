from film_contact_sheet.models import (
    SIZE_PIXELS,
    OutputSize,
    default_template,
)


def test_output_sizes_are_four_to_five():
    assert SIZE_PIXELS[OutputSize.SOCIAL] == (1080, 1350)
    assert SIZE_PIXELS[OutputSize.SHARP] == (2160, 2700)
    assert SIZE_PIXELS[OutputSize.A4] == (2480, 3100)
    for width, height in SIZE_PIXELS.values():
        assert width * 5 == height * 4


def test_default_template_matches_spec():
    template = default_template()
    assert template.id == "default"
    assert template.name == "默认"
    assert template.builtin is True
    assert template.background_path == ""
    assert template.strip_path == ""
    assert template.show_film_name is True
    assert template.show_order is True
    assert template.show_date is True
    assert template.show_count is True
    assert template.color_mode.value == "sRGB"
    assert template.output_size.value == "2160×2700"
