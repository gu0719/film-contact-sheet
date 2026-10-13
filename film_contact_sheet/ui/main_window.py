from __future__ import annotations

import os
from datetime import date
from functools import partial
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from film_contact_sheet.assemble import build_roll, finish_roll, read_frame
from film_contact_sheet.color_profile import save_jpeg
from film_contact_sheet.frames import apply_warnings
from film_contact_sheet.ingest import NoJpegError, list_jpegs, load_frame
from film_contact_sheet.meta import export_filename
from film_contact_sheet.models import ColorMode, FormatId, Roll, Template
from film_contact_sheet.render import render_sheet
from film_contact_sheet.store import (
    TemplateError,
    add_template,
    load_settings,
    save_settings,
    update_template,
)
from film_contact_sheet.ui.settings_dialog import SettingsDialog

FILE_ROLE = Qt.ItemDataRole.UserRole + 1
PREVIEW_SIZE = (480, 600)
EMPTY_DATE = date(1900, 1, 1)

FORMAT_LABELS = (
    (FormatId.F135, "135"),
    (FormatId.F645, "645"),
    (FormatId.F66, "6×6"),
    (FormatId.F67, "6×7"),
    (FormatId.F68, "6×8"),
    (FormatId.F69, "6×9"),
)


class ExportError(Exception):
    pass


class MainWindow(QMainWindow):
    def __init__(self, reader, data_root: Path):
        super().__init__()
        self.reader = reader
        self.data_root = Path(data_root)
        self.settings = load_settings(self.data_root)
        self.roll: Roll | None = None
        self._loading = False
        self._job: dict | None = None
        self._job_token = 0
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._refresh_preview)
        self.setWindowTitle("胶卷样张")
        self.resize(1180, 760)
        self._build()
        self._fill_films()
        self._fill_templates()

    def load_folder(self, path: Path) -> None:
        try:
            roll = build_roll(Path(path), self.reader, self.settings.film_presets)
        except NoJpegError:
            QMessageBox.information(self, "胶卷样张", "这个文件夹里没有 JPG。")
            return
        self._show_roll(roll)

    def _show_roll(self, roll: Roll) -> None:
        self.roll = roll
        self._loading = True
        self.order_edit.setText(roll.order_number)
        self._fill_films()
        self.film_edit.setCurrentText(roll.film_name)
        self._set_date(roll.shoot_date)
        self._set_format()
        self._fill_list()
        self._loading = False
        self._refresh_preview()

    def set_edge_number(self, row: int, number: int | None) -> None:
        if self.roll is None or row < 0 or row >= len(self.roll.frames):
            return
        self.roll.frames[row].edge_number = None if number is None else int(number)
        apply_warnings(self.roll.frames)
        self._rewrite_frame_items()
        self._refresh_preview()

    def export_to(self, path: Path) -> None:
        self._pull_form()
        if self.roll is None or not self.roll.frames:
            raise ExportError("没有可以导出的照片。")
        target = Path(path)
        template = self.current_template()
        image = render_sheet(self.roll, template, self.settings, proof=False)
        partial = target.with_name(target.name + ".partial")
        try:
            save_jpeg(image, partial, template)
            os.replace(partial, target)
        except Exception:
            if partial.exists():
                partial.unlink()
            raise

    def current_template(self) -> Template:
        template_id = self.template_combo.currentData()
        for template in self.settings.templates:
            if template.id == template_id:
                return template
        return self.settings.templates[0]

    def _build(self) -> None:
        self.frame_list = QListWidget()
        self.frame_list.setObjectName("frame_list")
        self.frame_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.frame_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.frame_list.model().rowsMoved.connect(self._frames_reordered)
        self.frame_list.currentRowChanged.connect(self._show_selected_number)

        self.preview = QLabel("打开一个文件夹")
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(*PREVIEW_SIZE)

        self.format_combo = QComboBox()
        for format_id, label in FORMAT_LABELS:
            self.format_combo.addItem(label, format_id.value)
        self.format_combo.currentIndexChanged.connect(self._format_changed)

        self.film_edit = QComboBox()
        self.film_edit.setObjectName("film_edit")
        self.film_edit.setEditable(True)
        self.film_edit.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        self.order_edit = QLineEdit()
        self.order_edit.setObjectName("order_edit")

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setMinimumDate(self._qdate(EMPTY_DATE))
        self.date_edit.setSpecialValueText(" ")

        self.template_combo = QComboBox()
        self.template_combo.currentIndexChanged.connect(self._template_changed)

        self.number_edit = QLineEdit()
        self.number_edit.setPlaceholderText("边字序号，留空表示未识别")
        self.number_edit.editingFinished.connect(self._commit_number)

        self.open_button = QPushButton("打开文件夹")
        self.open_button.clicked.connect(self._browse)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel_job)
        settings_button = QPushButton("设置")
        settings_button.clicked.connect(self._open_settings)
        export_button = QPushButton("导出")
        export_button.clicked.connect(self._choose_export)
        self.apply_button = QPushButton("应用")
        self.apply_button.setObjectName("apply_button")
        self.apply_button.clicked.connect(self._apply_fields)
        self.save_template_button = QPushButton("保存模板")
        self.save_template_button.setObjectName("save_template_button")
        self.save_template_button.clicked.connect(self._save_template)

        actions = QHBoxLayout()
        actions.addWidget(self.apply_button)
        actions.addWidget(self.save_template_button)

        form = QFormLayout()
        form.addRow("规格", self.format_combo)
        form.addRow("胶卷名", self.film_edit)
        form.addRow("订单号", self.order_edit)
        form.addRow("日期", self.date_edit)
        form.addRow("模板", self.template_combo)
        form.addRow(actions)
        form.addRow(export_button)

        left = QVBoxLayout()
        left.addWidget(QLabel("画格"))
        left.addWidget(self.frame_list, 1)
        left.addWidget(QLabel("边字"))
        left.addWidget(self.number_edit)
        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(280)

        right = QWidget()
        right.setLayout(form)
        right.setFixedWidth(260)

        body = QHBoxLayout()
        body.addWidget(left_widget)
        body.addWidget(self.preview, 1)
        body.addWidget(right)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.open_button)
        toolbar.addWidget(self.cancel_button)
        toolbar.addWidget(settings_button)
        toolbar.addStretch(1)

        root = QVBoxLayout()
        root.addLayout(toolbar)
        root.addLayout(body, 1)
        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

    def _browse(self) -> None:
        if self._job is not None:
            return
        path = QFileDialog.getExistingDirectory(self, "打开文件夹")
        if path:
            self._start_job(Path(path))

    def _start_job(self, folder: Path) -> None:
        try:
            paths = list_jpegs(folder)
        except NoJpegError:
            QMessageBox.information(self, "胶卷样张", "这个文件夹里没有 JPG。")
            return
        self._job_token += 1
        token = self._job_token
        self._job = {
            "folder": folder,
            "paths": paths,
            "index": 0,
            "frames": [],
            "texts": [],
            "aspects": [],
            "sprockets": [],
            "skipped": [],
        }
        self.open_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.preview.setText(f"正在读取 1/{len(paths)}\n{paths[0].name}")
        QTimer.singleShot(0, partial(self._job_step, token))

    def _cancel_job(self) -> None:
        if self._job is None:
            return
        self._job_token += 1
        self._job = None
        self.open_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if self.roll is not None:
            self._refresh_preview()
        else:
            self.preview.setText("已取消")

    def _job_step(self, token: int) -> None:
        job = self._job
        if job is None or token != self._job_token:
            return
        path = job["paths"][job["index"]]
        try:
            frame, text, aspect, sprocket = read_frame(load_frame(path), self.reader)
        except OSError:
            job["skipped"].append((path.name, "无法打开"))
        except Exception:
            job["skipped"].append((path.name, "无法打开"))
        else:
            job["frames"].append(frame)
            job["texts"].append(text)
            job["aspects"].append(aspect)
            job["sprockets"].append(sprocket)
        job["index"] += 1
        if job["index"] >= len(job["paths"]):
            roll = finish_roll(
                job["folder"],
                job["frames"],
                job["texts"],
                job["aspects"],
                job["sprockets"],
                job["skipped"],
                self.settings.film_presets,
            )
            self._job = None
            self.open_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self._show_roll(roll)
            return
        nxt = job["paths"][job["index"]]
        self.preview.setText(f"正在读取 {job['index'] + 1}/{len(job['paths'])}\n{nxt.name}")
        QTimer.singleShot(0, partial(self._job_step, token))

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        save_settings(self.data_root, self.settings)
        self._fill_films()
        self._fill_templates()
        if self.roll is not None:
            self.film_edit.setCurrentText(self.roll.film_name)
        self._refresh_preview()

    def _choose_export(self) -> None:
        self._pull_form()
        if self.roll is None or not self.roll.frames:
            QMessageBox.warning(self, "导出", "没有可以导出的照片。")
            return
        directory = self.settings.last_export_dir or self.roll.folder
        suggested = Path(directory) / export_filename(self.roll.order_number)
        path, _selected = QFileDialog.getSaveFileName(
            self,
            "导出样张",
            str(suggested),
            "JPEG (*.jpg)",
        )
        if not path:
            return
        try:
            self.export_to(Path(path))
        except Exception as exc:
            QMessageBox.warning(self, "导出", str(exc))
            return
        self.settings.last_export_dir = Path(path).parent
        save_settings(self.data_root, self.settings)

    def _fill_films(self) -> None:
        current = self.film_edit.currentText() if self.film_edit.count() or self.film_edit.lineEdit() else ""
        self.film_edit.blockSignals(True)
        self.film_edit.clear()
        self.film_edit.addItems(self.settings.film_presets)
        if current:
            self.film_edit.setCurrentText(current)
        self.film_edit.blockSignals(False)

    def _fill_templates(self) -> None:
        selected = self.template_combo.currentData() or self.settings.last_template_id
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        for template in self.settings.templates:
            self.template_combo.addItem(template.name, template.id)
        index = self.template_combo.findData(selected)
        self.template_combo.setCurrentIndex(index if index >= 0 else 0)
        self.template_combo.blockSignals(False)

    def _fill_list(self) -> None:
        self.frame_list.clear()
        if self.roll is None:
            return
        for frame in self.roll.frames:
            self.frame_list.addItem(self._frame_item(frame))
        for filename, _reason in self.roll.skipped:
            item = QListWidgetItem(f"无法打开：{filename}")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            self.frame_list.addItem(item)

    def _frame_item(self, frame) -> QListWidgetItem:
        item = QListWidgetItem()
        self._write_frame_item(item, frame)
        return item

    def _write_frame_item(self, item: QListWidgetItem, frame) -> None:
        number = "" if frame.edge_number is None else str(frame.edge_number)
        pieces = [frame.filename, number]
        if frame.warning:
            pieces.append(frame.warning)
        item.setText("  ".join(piece for piece in pieces if piece))
        item.setData(Qt.ItemDataRole.UserRole, frame.edge_number)
        item.setData(FILE_ROLE, frame.filename)

    def _rewrite_frame_items(self) -> None:
        if self.roll is None:
            return
        by_name = {frame.filename: frame for frame in self.roll.frames}
        for row in range(self.frame_list.count()):
            item = self.frame_list.item(row)
            frame = by_name.get(item.data(FILE_ROLE))
            if frame is not None:
                self._write_frame_item(item, frame)

    def _frames_reordered(self, *_args) -> None:
        if self._loading or self.roll is None:
            return
        by_name = {frame.filename: frame for frame in self.roll.frames}
        ordered = []
        for row in range(self.frame_list.count()):
            frame = by_name.get(self.frame_list.item(row).data(FILE_ROLE))
            if frame is not None:
                ordered.append(frame)
        self.roll.frames = ordered
        apply_warnings(self.roll.frames)
        self._rewrite_frame_items()
        self._refresh_preview()

    def _show_selected_number(self, row: int) -> None:
        if self.roll is None or row < 0 or row >= len(self.roll.frames):
            self.number_edit.clear()
            return
        number = self.roll.frames[row].edge_number
        self.number_edit.blockSignals(True)
        self.number_edit.setText("" if number is None else str(number))
        self.number_edit.blockSignals(False)

    def _commit_number(self) -> None:
        row = self.frame_list.currentRow()
        if self.roll is None or row < 0 or row >= len(self.roll.frames):
            return
        text = self.number_edit.text().strip()
        if text == "":
            self.set_edge_number(row, None)
            return
        try:
            self.set_edge_number(row, int(text))
        except ValueError:
            return

    def _set_format(self) -> None:
        if self.roll is None:
            return
        guess = self.roll.format_guess
        index = self.format_combo.findData(guess.format_id.value)
        self.format_combo.blockSignals(True)
        self.format_combo.setCurrentIndex(index if index >= 0 else 0)
        self.format_combo.blockSignals(False)
        if guess.confirmed:
            self.format_combo.setStyleSheet("")
        else:
            self.format_combo.setStyleSheet("QComboBox { border: 1px solid #c0392b; }")

    def _format_changed(self) -> None:
        if self._loading or self.roll is None:
            return
        self.roll.format_guess.format_id = FormatId(self.format_combo.currentData())
        self.roll.format_guess.confirmed = True
        self.format_combo.setStyleSheet("")
        self._refresh_preview()

    def _template_changed(self) -> None:
        if self._loading:
            return
        template_id = self.template_combo.currentData()
        if template_id:
            self.settings.last_template_id = template_id
        self._refresh_preview()

    def _apply_fields(self) -> None:
        self._pull_form()
        self._refresh_preview()

    def _save_template(self) -> None:
        name, ok = QInputDialog.getText(self, "保存模板", "模板名称")
        if not ok or not name.strip():
            return
        source = self.current_template()
        try:
            created = add_template(self.settings, name.strip())
        except TemplateError as exc:
            QMessageBox.warning(self, "模板", str(exc))
            return
        created.background_path = source.background_path
        created.strip_path = source.strip_path
        created.show_film_name = source.show_film_name
        created.show_order = source.show_order
        created.show_date = source.show_date
        created.show_count = source.show_count
        created.color_mode = source.color_mode
        created.output_size = source.output_size
        update_template(self.settings, created)
        self.settings.last_template_id = created.id
        save_settings(self.data_root, self.settings)
        self._fill_templates()

    def _pull_form(self) -> None:
        if self.roll is None:
            return
        self.roll.order_number = self.order_edit.text()
        self.roll.film_name = self.film_edit.currentText()
        self.roll.shoot_date = self._date_value()

    def _set_date(self, value: date | None) -> None:
        self.date_edit.setDate(self._qdate(value or EMPTY_DATE))

    def _date_value(self) -> date | None:
        qdate = self.date_edit.date()
        value = date(qdate.year(), qdate.month(), qdate.day())
        if value == EMPTY_DATE:
            return None
        return value

    def _qdate(self, value: date):
        from PySide6.QtCore import QDate

        return QDate(value.year, value.month, value.day)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.roll is not None and self._job is None:
            self._preview_timer.start(80)

    def _preview_canvas(self) -> tuple[int, int]:
        width = max(self.preview.width(), PREVIEW_SIZE[0])
        height = max(self.preview.height(), PREVIEW_SIZE[1])
        if width / height > 4 / 5:
            width = max(1, round(height * 4 / 5))
        else:
            height = max(1, round(width * 5 / 4))
        return width, height

    def _refresh_preview(self) -> None:
        if self.roll is None:
            self.preview.setText("打开一个文件夹")
            self.preview.setPixmap(QPixmap())
            return
        template = self.current_template()
        proof = template.color_mode == ColorMode.CMYK
        image = render_sheet(self.roll, template, self.settings, self._preview_canvas(), proof=proof)
        self.preview.setPixmap(_pixmap(image))


def _pixmap(image: Image.Image) -> QPixmap:
    rgb = image.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimage = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())
