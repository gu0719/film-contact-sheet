from PIL import Image, ImageDraw

from film_contact_sheet.models import ColorMode, OutputSize
from film_contact_sheet.ui.main_window import MainWindow


class FakeReader:
    def read(self, image):
        return "1 GOLD 200"


def test_export_writes_jpeg_and_leaves_existing_file_when_render_fails(qtbot, tmp_path, monkeypatch):
    image = Image.new("RGB", (80, 56), (180, 90, 30))
    ImageDraw.Draw(image).rectangle((8, 8, 71, 47), fill=(180, 40, 40))
    image.save(tmp_path / "a.jpg", quality=95)
    window = MainWindow(FakeReader(), tmp_path / "data")
    qtbot.addWidget(window)
    window.load_folder(tmp_path)
    target = tmp_path / "out" / "318167.jpg"
    target.parent.mkdir()
    window.export_to(target)
    assert target.exists()
    with Image.open(target) as saved:
        assert saved.size == (2160, 2700)
        assert saved.mode == "RGB"

    window.current_template().output_size = OutputSize.A4
    window.current_template().color_mode = ColorMode.CMYK
    printed = tmp_path / "print.jpg"
    window.export_to(printed)
    with Image.open(printed) as saved:
        assert saved.size == (2480, 3100)
        assert saved.mode == "CMYK"

    original = target.read_bytes()

    def explode(*args, **kwargs):
        raise OSError("磁盘已满")

    monkeypatch.setattr("film_contact_sheet.ui.main_window.save_jpeg", explode)
    try:
        window.export_to(target)
        raise AssertionError("export should fail")
    except OSError as exc:
        assert str(exc) == "磁盘已满"
    assert target.read_bytes() == original
