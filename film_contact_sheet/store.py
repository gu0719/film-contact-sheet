from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from film_contact_sheet.film_names import FACTORY_PRESETS
from film_contact_sheet.models import ColorMode, OutputSize, Settings, Template, default_template


class TemplateError(Exception):
    pass


def default_data_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ["APPDATA"]) / "FilmContactSheet"
    return Path.home() / "Library/Application Support/FilmContactSheet"


def load_settings(root: Path) -> Settings:
    root.mkdir(parents=True, exist_ok=True)
    (root / "backgrounds").mkdir(exist_ok=True)
    (root / "strips").mkdir(exist_ok=True)
    path = root / "settings.json"
    if not path.exists():
        return _factory(root)
    data = json.loads(path.read_text(encoding="utf-8"))
    return Settings(
        brand_text=data["brand_text"],
        backgrounds_dir=Path(data["backgrounds_dir"]),
        strips_dir=Path(data["strips_dir"]),
        last_template_id=data["last_template_id"],
        last_export_dir=Path(data["last_export_dir"]) if data["last_export_dir"] else None,
        templates=[_template_from(item) for item in data["templates"]],
        film_presets=list(data["film_presets"]),
    )


def save_settings(root: Path, settings: Settings) -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "brand_text": settings.brand_text,
        "backgrounds_dir": str(settings.backgrounds_dir),
        "strips_dir": str(settings.strips_dir),
        "last_template_id": settings.last_template_id,
        "last_export_dir": str(settings.last_export_dir) if settings.last_export_dir else None,
        "templates": [_template_to(item) for item in settings.templates],
        "film_presets": list(settings.film_presets),
    }
    (root / "settings.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_template(settings: Settings, name: str) -> Template:
    _require_capacity(settings)
    _require_unique_name(settings, name)
    created = default_template()
    created.id = uuid.uuid4().hex
    created.name = name
    created.builtin = False
    settings.templates.append(created)
    return created


def duplicate_template(settings: Settings, template_id: str) -> Template:
    _require_capacity(settings)
    source = _find(settings, template_id)
    created = Template(
        id=uuid.uuid4().hex,
        name=_copy_name(settings, source.name),
        background_path=source.background_path,
        strip_path=source.strip_path,
        show_film_name=source.show_film_name,
        show_order=source.show_order,
        show_date=source.show_date,
        show_count=source.show_count,
        color_mode=source.color_mode,
        output_size=source.output_size,
        builtin=False,
    )
    settings.templates.append(created)
    return created


def rename_template(settings: Settings, template_id: str, name: str) -> None:
    template = _find(settings, template_id)
    if template.builtin:
        raise TemplateError("默认模板不能改名")
    _require_unique_name(settings, name)
    template.name = name


def delete_template(settings: Settings, template_id: str) -> None:
    template = _find(settings, template_id)
    if template.builtin:
        raise TemplateError("默认模板不能删除")
    settings.templates.remove(template)


def update_template(settings: Settings, template: Template) -> None:
    current = _find(settings, template.id)
    if current.builtin and template.name != current.name:
        raise TemplateError("默认模板不能改名")
    current.background_path = template.background_path
    current.strip_path = template.strip_path
    current.show_film_name = template.show_film_name
    current.show_order = template.show_order
    current.show_date = template.show_date
    current.show_count = template.show_count
    current.color_mode = template.color_mode
    current.output_size = template.output_size


def _factory(root: Path) -> Settings:
    return Settings(
        "",
        root / "backgrounds",
        root / "strips",
        "default",
        None,
        [default_template()],
        list(FACTORY_PRESETS),
    )


def _require_capacity(settings: Settings) -> None:
    if len(settings.templates) >= 30:
        raise TemplateError("模板最多 30 个")


def _require_unique_name(settings: Settings, name: str) -> None:
    if any(item.name == name for item in settings.templates):
        raise TemplateError("模板名称不能重复")


def _copy_name(settings: Settings, source: str) -> str:
    candidate = f"{source} 副本"
    number = 2
    while any(item.name == candidate for item in settings.templates):
        candidate = f"{source} 副本 {number}"
        number += 1
    return candidate


def _find(settings: Settings, template_id: str) -> Template:
    for template in settings.templates:
        if template.id == template_id:
            return template
    raise TemplateError("找不到模板")


def _template_to(template: Template) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "background_path": template.background_path,
        "strip_path": template.strip_path,
        "show_film_name": template.show_film_name,
        "show_order": template.show_order,
        "show_date": template.show_date,
        "show_count": template.show_count,
        "color_mode": template.color_mode.value,
        "output_size": template.output_size.value,
        "builtin": template.builtin,
    }


def _template_from(data: dict) -> Template:
    return Template(
        id=data["id"],
        name=data["name"],
        background_path=data["background_path"],
        strip_path=data["strip_path"],
        show_film_name=data["show_film_name"],
        show_order=data["show_order"],
        show_date=data["show_date"],
        show_count=data["show_count"],
        color_mode=ColorMode(data["color_mode"]),
        output_size=OutputSize(data["output_size"]),
        builtin=data["builtin"],
    )
