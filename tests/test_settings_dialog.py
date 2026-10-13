from film_contact_sheet.models import ColorMode, OutputSize
from film_contact_sheet.store import load_settings
from film_contact_sheet.ui.settings_dialog import SettingsDialog


def test_dialog_can_add_a_cmyk_a4_template_and_a_film_name(qtbot, tmp_path):
    settings = load_settings(tmp_path)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)
    dialog.add_named_template("印刷")
    dialog.set_selected_template_options(
        color_mode=ColorMode.CMYK,
        output_size=OutputSize.A4,
        show_date=False,
    )
    dialog.add_preset("测试卷")
    dialog.brand_edit.setText("IROHAS PHOTO")
    dialog.accept()
    assert settings.brand_text == "IROHAS PHOTO"
    created = next(item for item in settings.templates if item.name == "印刷")
    assert created.color_mode == ColorMode.CMYK
    assert created.output_size == OutputSize.A4
    assert created.show_date is False
    assert "测试卷" in settings.film_presets
