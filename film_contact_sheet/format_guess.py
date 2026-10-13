from __future__ import annotations

from film_contact_sheet.models import FormatGuess, FormatId


def guess_format(aspects: list[float | None], sprocket_flags: list[bool]) -> FormatGuess:
    count = len(aspects)
    sprocket = sum(1 for flag in sprocket_flags if flag) > count / 2
    measured = [value for value in aspects if value is not None]
    ratio = _median(measured) if measured else None
    if sprocket:
        return FormatGuess(FormatId.F135, True, ratio)
    if ratio is None:
        return FormatGuess(_by_count(count), False, None)
    if ratio >= 1.42 and count >= 20:
        return FormatGuess(FormatId.F135, True, ratio)
    if ratio >= 1.42 and count <= 10:
        return FormatGuess(FormatId.F69, True, ratio)
    if 1.28 <= ratio < 1.42 and count >= 15:
        return FormatGuess(FormatId.F645, True, ratio)
    if 1.28 <= ratio < 1.42 and count < 10:
        return FormatGuess(FormatId.F68, True, ratio)
    if ratio < 1.12 and count in (12, 13):
        return FormatGuess(FormatId.F66, True, ratio)
    if 1.12 <= ratio < 1.28 and count in (10, 11):
        return FormatGuess(FormatId.F67, True, ratio)
    return FormatGuess(_by_ratio(ratio, count), False, ratio)


def _by_count(count: int) -> FormatId:
    if count >= 20:
        return FormatId.F135
    if count >= 14:
        return FormatId.F645
    if count in (12, 13):
        return FormatId.F66
    if count in (10, 11):
        return FormatId.F67
    if count == 9:
        return FormatId.F68
    return FormatId.F69


def _by_ratio(ratio: float, count: int) -> FormatId:
    if ratio < 1.12:
        return FormatId.F66
    if ratio < 1.28:
        return FormatId.F67
    if ratio < 1.42:
        return FormatId.F645 if count >= 12 else FormatId.F68
    return FormatId.F135 if count >= 15 else FormatId.F69


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2
