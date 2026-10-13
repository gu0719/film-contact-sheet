import sys

from PySide6.QtWidgets import QApplication

from film_contact_sheet.ocr import RapidRebateReader
from film_contact_sheet.qt_plugins import ensure_qt_plugins_visible
from film_contact_sheet.store import default_data_dir
from film_contact_sheet.ui.main_window import MainWindow


def build_window() -> MainWindow:
    ensure_qt_plugins_visible()
    return MainWindow(RapidRebateReader(), default_data_dir())


def main() -> None:
    ensure_qt_plugins_visible()
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
