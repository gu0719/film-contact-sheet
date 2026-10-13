from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from film_contact_sheet.models import ColorMode, OutputSize, Settings, Template
from film_contact_sheet.store import (
    TemplateError,
    add_template,
    delete_template,
    duplicate_template,
    rename_template,
    update_template,
)


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._original = settings
        self.settings = copy.deepcopy(settings)
        self.setWindowTitle("设置")
        self.resize(760, 560)
        self._loading = False
        self._build()
        self._reload_assets()
        self._reload_templates(self.settings.last_template_id)
        self._reload_presets()
        self.brand_edit.setText(self.settings.brand_text)

    def add_named_template(self, name: str) -> None:
        created = add_template(self.settings, name)
        self._reload_templates(created.id)

    def set_selected_template_options(
        self,
        color_mode: ColorMode | None = None,
        output_size: OutputSize | None = None,
        show_date: bool | None = None,
        show_film_name: bool | None = None,
        show_order: bool | None = None,
        show_count: bool | None = None,
    ) -> None:
        if color_mode is not None:
            _select(self.color_combo, color_mode.value)
        if output_size is not None:
            _select(self.size_combo, output_size.value)
        if show_film_name is not None:
            self.film_check.setChecked(show_film_name)
        if show_order is not None:
            self.order_check.setChecked(show_order)
        if show_date is not None:
            self.date_check.setChecked(show_date)
        if show_count is not None:
            self.count_check.setChecked(show_count)
        self._apply_form()

    def add_preset(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned or cleaned in self.settings.film_presets:
            return
        self.settings.film_presets.append(cleaned)
        self.preset_list.addItem(cleaned)

    def accept(self) -> None:
        try:
            self._apply_form()
        except TemplateError as exc:
            QMessageBox.warning(self, "模板", str(exc))
            return
        self.settings.brand_text = self.brand_edit.text()
        self._original.brand_text = self.settings.brand_text
        self._original.backgrounds_dir = self.settings.backgrounds_dir
        self._original.strips_dir = self.settings.strips_dir
        self._original.last_template_id = self.settings.last_template_id
        self._original.last_export_dir = self.settings.last_export_dir
        self._original.templates = self.settings.templates
        self._original.film_presets = list(self.settings.film_presets)
        super().accept()

    def _build(self) -> None:
        self.template_list = QListWidget()
        self.template_list.currentRowChanged.connect(self._template_selected)
        self.background_combo = QComboBox()
        self.strip_combo = QComboBox()
        self.color_combo = QComboBox()
        self.color_combo.addItem("sRGB", ColorMode.SRGB.value)
        self.color_combo.addItem("CMYK", ColorMode.CMYK.value)
        self.size_combo = QComboBox()
        for size in OutputSize:
            self.size_combo.addItem(size.value, size.value)
        self.film_check = QCheckBox("胶卷名")
        self.order_check = QCheckBox("订单号")
        self.date_check = QCheckBox("日期")
        self.count_check = QCheckBox("张数")
        self.brand_edit = QLineEdit()
        self.preset_list = QListWidget()

        add_button = QPushButton("新增")
        copy_button = QPushButton("复制")
        self.rename_button = QPushButton("重命名")
        self.delete_button = QPushButton("删除")
        add_button.clicked.connect(self._add_template)
        copy_button.clicked.connect(self._duplicate_template)
        self.rename_button.clicked.connect(self._rename_template)
        self.delete_button.clicked.connect(self._delete_template)

        background_dir = QPushButton("打开底图文件夹")
        strip_dir = QPushButton("打开齿孔文件夹")
        change_backgrounds = QPushButton("更改底图文件夹")
        change_strips = QPushButton("更改齿孔文件夹")
        background_dir.clicked.connect(lambda: self._open_dir(self.settings.backgrounds_dir))
        strip_dir.clicked.connect(lambda: self._open_dir(self.settings.strips_dir))
        change_backgrounds.clicked.connect(self._change_backgrounds)
        change_strips.clicked.connect(self._change_strips)

        preset_add = QPushButton("新增")
        preset_edit = QPushButton("修改")
        preset_delete = QPushButton("删除")
        preset_add.clicked.connect(self._add_preset_from_dialog)
        preset_edit.clicked.connect(self._edit_preset)
        preset_delete.clicked.connect(self._delete_preset)

        buttons = QHBoxLayout()
        for button in (add_button, copy_button, self.rename_button, self.delete_button):
            buttons.addWidget(button)

        form = QFormLayout()
        form.addRow("底图", self.background_combo)
        form.addRow("齿孔", self.strip_combo)
        form.addRow("色彩", self.color_combo)
        form.addRow("尺寸", self.size_combo)
        toggles = QHBoxLayout()
        for check in (self.film_check, self.order_check, self.date_check, self.count_check):
            toggles.addWidget(check)
        form.addRow("显示", _wrap(toggles))
        form.addRow(background_dir)
        form.addRow(change_backgrounds)
        form.addRow(strip_dir)
        form.addRow(change_strips)

        left = QVBoxLayout()
        left.addWidget(QLabel("模板"))
        left.addWidget(self.template_list, 1)
        left.addLayout(buttons)

        right = QVBoxLayout()
        right.addLayout(form)
        right.addWidget(QLabel("品牌字"))
        right.addWidget(self.brand_edit)
        right.addWidget(QLabel("胶卷名"))
        right.addWidget(self.preset_list, 1)
        preset_buttons = QHBoxLayout()
        for button in (preset_add, preset_edit, preset_delete):
            preset_buttons.addWidget(button)
        right.addLayout(preset_buttons)

        body = QHBoxLayout()
        body.addLayout(left, 1)
        body.addLayout(right, 2)
        self.setLayout(body)

    def _reload_templates(self, select_id: str | None) -> None:
        self._loading = True
        self.template_list.clear()
        for template in self.settings.templates:
            item = QListWidgetItem(template.name)
            item.setData(Qt.ItemDataRole.UserRole, template.id)
            self.template_list.addItem(item)
        row = 0
        for index, template in enumerate(self.settings.templates):
            if template.id == select_id:
                row = index
                break
        self.template_list.setCurrentRow(row)
        self._loading = False
        self._load_selected()

    def _reload_assets(self) -> None:
        _fill_files(self.background_combo, "白底", self.settings.backgrounds_dir, {".jpg", ".jpeg", ".png"})
        _fill_files(self.strip_combo, "内置方孔", self.settings.strips_dir, {".png"})

    def _reload_presets(self) -> None:
        self.preset_list.clear()
        self.preset_list.addItems(self.settings.film_presets)

    def _template_selected(self) -> None:
        if self._loading:
            return
        self._load_selected()

    def _load_selected(self) -> None:
        template = self._selected()
        builtin = template is None or template.builtin
        self.rename_button.setEnabled(not builtin)
        self.delete_button.setEnabled(not builtin)
        if template is None:
            return
        self._loading = True
        _select(self.background_combo, template.background_path)
        _select(self.strip_combo, template.strip_path)
        _select(self.color_combo, template.color_mode.value)
        _select(self.size_combo, template.output_size.value)
        self.film_check.setChecked(template.show_film_name)
        self.order_check.setChecked(template.show_order)
        self.date_check.setChecked(template.show_date)
        self.count_check.setChecked(template.show_count)
        self._loading = False

    def _selected(self) -> Template | None:
        item = self.template_list.currentItem()
        if item is None:
            return None
        template_id = item.data(Qt.ItemDataRole.UserRole)
        for template in self.settings.templates:
            if template.id == template_id:
                return template
        return None

    def _apply_form(self) -> None:
        template = self._selected()
        if template is None or self._loading:
            return
        template.background_path = self.background_combo.currentData() or ""
        template.strip_path = self.strip_combo.currentData() or ""
        template.show_film_name = self.film_check.isChecked()
        template.show_order = self.order_check.isChecked()
        template.show_date = self.date_check.isChecked()
        template.show_count = self.count_check.isChecked()
        template.color_mode = ColorMode(self.color_combo.currentData())
        template.output_size = OutputSize(self.size_combo.currentData())
        update_template(self.settings, template)

    def _add_template(self) -> None:
        name, ok = QInputDialog.getText(self, "新增模板", "模板名称")
        if not ok or not name.strip():
            return
        try:
            self.add_named_template(name.strip())
        except TemplateError as exc:
            QMessageBox.warning(self, "模板", str(exc))

    def _duplicate_template(self) -> None:
        template = self._selected()
        if template is None:
            return
        try:
            created = duplicate_template(self.settings, template.id)
        except TemplateError as exc:
            QMessageBox.warning(self, "模板", str(exc))
            return
        self._reload_templates(created.id)

    def _rename_template(self) -> None:
        template = self._selected()
        if template is None:
            return
        name, ok = QInputDialog.getText(self, "重命名", "模板名称", text=template.name)
        if not ok or not name.strip():
            return
        try:
            rename_template(self.settings, template.id, name.strip())
        except TemplateError as exc:
            QMessageBox.warning(self, "模板", str(exc))
            return
        self._reload_templates(template.id)

    def _delete_template(self) -> None:
        template = self._selected()
        if template is None:
            return
        try:
            delete_template(self.settings, template.id)
        except TemplateError as exc:
            QMessageBox.warning(self, "模板", str(exc))
            return
        self._reload_templates(self.settings.last_template_id)

    def _add_preset_from_dialog(self) -> None:
        name, ok = QInputDialog.getText(self, "胶卷名", "名称")
        if ok:
            self.add_preset(name)

    def _edit_preset(self) -> None:
        row = self.preset_list.currentRow()
        if row < 0:
            return
        current = self.settings.film_presets[row]
        name, ok = QInputDialog.getText(self, "修改胶卷名", "名称", text=current)
        if not ok or not name.strip():
            return
        self.settings.film_presets[row] = name.strip()
        self._reload_presets()
        self.preset_list.setCurrentRow(row)

    def _delete_preset(self) -> None:
        row = self.preset_list.currentRow()
        if row < 0:
            return
        del self.settings.film_presets[row]
        self._reload_presets()

    def _change_backgrounds(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "底图文件夹", str(self.settings.backgrounds_dir))
        if not path:
            return
        self.settings.backgrounds_dir = Path(path)
        self._reload_assets()
        self._load_selected()

    def _change_strips(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "齿孔文件夹", str(self.settings.strips_dir))
        if not path:
            return
        self.settings.strips_dir = Path(path)
        self._reload_assets()
        self._load_selected()

    def _open_dir(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


def _fill_files(combo: QComboBox, empty_label: str, folder: Path, suffixes: set[str]) -> None:
    current = combo.currentData()
    combo.clear()
    combo.addItem(empty_label, "")
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix.lower() in suffixes:
                combo.addItem(path.name, str(path))
    if current:
        _select(combo, current)


def _select(combo: QComboBox, value) -> None:
    index = combo.findData(value)
    combo.setCurrentIndex(index if index >= 0 else 0)


def _wrap(layout) -> QWidget:
    widget = QWidget()
    widget.setLayout(layout)
    return widget
