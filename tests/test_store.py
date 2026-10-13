import json

from film_contact_sheet.models import ColorMode, OutputSize
from film_contact_sheet.store import (
    TemplateError,
    add_template,
    delete_template,
    load_settings,
    rename_template,
    save_settings,
)


def test_first_load_creates_folders_and_default_template(tmp_path):
    settings = load_settings(tmp_path)
    assert (tmp_path / "backgrounds").is_dir()
    assert (tmp_path / "strips").is_dir()
    assert settings.templates[0].name == "默认"
    assert settings.film_presets[0] == "Kodak Portra 160"
    assert settings.brand_text == ""
    save_settings(tmp_path, settings)
    assert json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))["last_template_id"] == "default"


def test_default_template_cannot_be_deleted_or_renamed(tmp_path):
    settings = load_settings(tmp_path)
    try:
        delete_template(settings, "default")
        raise AssertionError("delete should fail")
    except TemplateError:
        pass
    try:
        rename_template(settings, "default", "春日")
        raise AssertionError("rename should fail")
    except TemplateError:
        pass


def test_template_names_are_unique_and_capped_at_30(tmp_path):
    settings = load_settings(tmp_path)
    add_template(settings, "春日")
    try:
        add_template(settings, "春日")
        raise AssertionError("duplicate should fail")
    except TemplateError:
        pass
    for index in range(28):
        add_template(settings, f"模板{index}")
    assert len(settings.templates) == 30
    try:
        add_template(settings, "超出")
        raise AssertionError("cap should fail")
    except TemplateError:
        pass
    settings.templates[1].color_mode = ColorMode.CMYK
    settings.templates[1].output_size = OutputSize.A4
    save_settings(tmp_path, settings)
    loaded = load_settings(tmp_path)
    assert loaded.templates[1].color_mode == ColorMode.CMYK
    assert loaded.templates[1].output_size == OutputSize.A4
