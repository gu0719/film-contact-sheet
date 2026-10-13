from pathlib import Path

from PIL import Image, ImageDraw
from PySide6.QtCore import Qt

from film_contact_sheet.ui.main_window import MainWindow


class FakeReader:
    def read(self, image):
        return "8 PORTRA 400"


def test_load_folder_fills_order_number_and_edge_number(qtbot, tmp_path):
    _save_frame(tmp_path / "frame.jpg", (180, 40, 40))
    window = MainWindow(FakeReader(), tmp_path / "data")
    qtbot.addWidget(window)
    window.load_folder(tmp_path)
    assert window.order_edit.text() == tmp_path.name
    assert window.film_edit.currentText() == "Kodak Portra 400"
    assert window.frame_list.item(0).data(Qt.ItemDataRole.UserRole) == 8
    assert window.preview.pixmap() is not None
    assert not window.preview.pixmap().isNull()


def test_editing_a_number_refreshes_the_warning(qtbot, tmp_path):
    _save_frame(tmp_path / "one.jpg", (180, 40, 40))
    _save_frame(tmp_path / "two.jpg", (40, 80, 180))
    window = MainWindow(FakeReader(), tmp_path / "data")
    qtbot.addWidget(window)
    window.load_folder(tmp_path)
    window.set_edge_number(1, 8)
    assert "序号重复" in window.frame_list.item(1).text()


def test_build_window_uses_the_rapid_reader(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr("film_contact_sheet.__main__.default_data_dir", lambda: tmp_path)
    from film_contact_sheet.__main__ import build_window

    window = build_window()
    qtbot.addWidget(window)
    assert window.data_root == tmp_path


def _save_frame(path: Path, color) -> None:
    image = Image.new("RGB", (80, 56), (180, 90, 30))
    ImageDraw.Draw(image).rectangle((8, 8, 71, 47), fill=color)
    image.save(path, quality=95)


def test_cancel_stops_an_open_before_the_roll_is_applied(qtbot, tmp_path):
    _save_frame(tmp_path / "one.jpg", (180, 40, 40))
    _save_frame(tmp_path / "two.jpg", (40, 80, 180))
    window = MainWindow(FakeReader(), tmp_path / "data")
    qtbot.addWidget(window)
    assert not window.cancel_button.isEnabled()
    window._start_job(tmp_path)
    assert window.cancel_button.isEnabled()
    window.cancel_button.click()
    qtbot.wait(50)
    assert window._job is None
    assert window.roll is None
    assert window.open_button.isEnabled()
    assert not window.cancel_button.isEnabled()
    assert window.preview.text() == "已取消"


def test_film_name_is_applied_only_on_the_button(qtbot, tmp_path):
    _save_frame(tmp_path / "frame.jpg", (180, 40, 40))
    window = MainWindow(FakeReader(), tmp_path / "data")
    qtbot.addWidget(window)
    window.load_folder(tmp_path)
    window.film_edit.setCurrentText("Kodak Gold 200")
    assert window.roll.film_name == "Kodak Portra 400"
    qtbot.mouseClick(window.apply_button, Qt.MouseButton.LeftButton)
    assert window.roll.film_name == "Kodak Gold 200"
