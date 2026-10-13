from __future__ import annotations

import re

FACTORY_PRESETS = (
    "Kodak Portra 160",
    "Kodak Portra 400",
    "Kodak Portra 800",
    "Kodak Ektar 100",
    "Kodak Gold 200",
    "Kodak ColorPlus 200",
    "Kodak Ultramax 400",
    "Kodak Pro Image 100",
    "Kodak Ektachrome E100",
    "Kodak Tri-X 400",
    "Kodak T-Max 100",
    "Kodak T-Max 400",
    "Kodak Vision3 50D",
    "Kodak Vision3 250D",
    "Kodak Vision3 500T",
    "Fujifilm Superia Premium 400",
    "Fujifilm Superia X-TRA 400",
    "Fujifilm C200",
    "Fujifilm Pro 400H",
    "Fujichrome Velvia 50",
    "Fujichrome Velvia 100",
    "Fujichrome Provia 100F",
    "Cinestill 50D",
    "Cinestill 400D",
    "Cinestill 800T",
    "Ilford HP5 Plus 400",
    "Ilford FP4 Plus 125",
    "Ilford Delta 100",
    "Ilford Delta 400",
    "Ilford Delta 3200",
    "Ilford XP2 Super 400",
    "Ilford Kentmere 400",
    "Fomapan 100",
    "Fomapan 200",
    "Fomapan 400",
    "Lomography Color Negative 100",
    "Lomography Color Negative 400",
    "Lomography Color Negative 800",
    "乐凯新锐 100",
    "上海 GP3 100",
)

_BRANDS = {"KODAK", "FUJIFILM", "FUJICHROME", "ILFORD"}


def match_film_name(ocr_text: str, presets: list[str]) -> str:
    haystack = _flatten(ocr_text)
    if not haystack:
        return ""
    best: str | None = None
    best_length = -1
    for preset in presets:
        tokens = _tokens(preset)
        if tokens and all(token in haystack for token in tokens):
            length = sum(len(token) for token in tokens)
            if length > best_length:
                best = preset
                best_length = length
    if best is None:
        return ""
    return best


def _tokens(preset: str) -> list[str]:
    words = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", " ", preset).upper().split()
    kept = [word for word in words if word not in _BRANDS]
    if not kept:
        kept = words
    return [_flatten(word) for word in kept if _flatten(word)]


def _flatten(text: str) -> str:
    return re.sub(r"[^0-9A-Z\u4e00-\u9fff]", "", text.upper())
