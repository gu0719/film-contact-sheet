from PIL import Image

from film_contact_sheet.ocr import RapidRebateReader, parse_edge_number


def test_parse_edge_number_ignores_film_speed():
    assert parse_edge_number("FRAME 12 400") == 12
    assert parse_edge_number("PORTRA 400") is None
    assert parse_edge_number("") is None


def test_reader_joins_engine_text():
    class Engine:
        def __call__(self, array):
            return [[["box", "12", 0.9], ["box", "PORTRA 400", 0.8]], None]

    assert RapidRebateReader(Engine()).read(Image.new("RGB", (8, 8))) == "12 PORTRA 400"


def test_wide_rebate_stays_inside_the_ocr_size_limit():
    seen = []

    class Engine:
        def __call__(self, array):
            seen.append(array.shape)
            return [[["box", "7", 0.9]], None]

    text = RapidRebateReader(Engine()).read(Image.new("RGB", (5000, 10), "black"))
    assert text.startswith("7")
    assert seen
    assert all(min(shape[0], shape[1]) >= 32 for shape in seen)
    assert all(max(shape[0], shape[1]) <= 960 for shape in seen)


def test_reader_skips_a_strip_when_the_engine_fails():
    class Engine:
        def __call__(self, array):
            raise RuntimeError("resize_w or resize_h is less than or equal to 0")

    assert RapidRebateReader(Engine()).read(Image.new("RGB", (4000, 8), "black")) == ""
