from __future__ import annotations

from dataclasses import dataclass

from film_contact_sheet.models import ROW_CYCLES, WINDOW_RATIO, FormatId


def row_plan(format_id: FormatId, count: int) -> list[list[int | None]]:
    cycle = ROW_CYCLES[format_id]
    rows: list[list[int | None]] = []
    index = 0
    cycle_index = 0
    while index < count:
        width = cycle[cycle_index % len(cycle)]
        row: list[int | None] = []
        for _ in range(width):
            if index < count:
                row.append(index)
                index += 1
            else:
                row.append(None)
        rows.append(row)
        cycle_index += 1
    return rows


def majority_landscape(sizes: list[tuple[int, int]]) -> bool:
    landscape = sum(1 for width, height in sizes if width >= height)
    return landscape >= len(sizes) - landscape


def window_aspect(format_id: FormatId, landscape: bool) -> float:
    ratio = WINDOW_RATIO[format_id]
    if format_id == FormatId.F66:
        return 1.0
    return ratio if landscape else 1 / ratio


@dataclass(frozen=True)
class Cell:
    box: tuple[int, int, int, int]
    frame_index: int | None
    tile: tuple[int, int, int, int]


@dataclass(frozen=True)
class SheetLayout:
    canvas: tuple[int, int]
    rows: list[tuple[tuple[int, int, int, int], list[Cell]]]


def layout_sheet(
    canvas: tuple[int, int],
    format_id: FormatId,
    count: int,
    landscape: bool,
) -> SheetLayout:
    if count <= 0:
        return SheetLayout(canvas, [])
    canvas_w, canvas_h = canvas
    plan = row_plan(format_id, count)
    top = round(canvas_h * 0.04)
    floor = round(canvas_h * 0.86)
    row_gap = max(2, round(canvas_h * 0.008))
    gaps = row_gap * max(0, len(plan) - 1)
    available = max(1, floor - top - gaps)
    row_h = max(1, min(round(canvas_h * 0.34), available // len(plan)))
    aspect = window_aspect(format_id, landscape)
    rows = []
    for row_index, indexes in enumerate(plan):
        row_y = top + row_index * (row_h + row_gap)
        row_box = (0, row_y, canvas_w, row_h)
        rows.append((row_box, _cells_for_row(row_box, indexes, aspect)))
    return SheetLayout(canvas, rows)


def _cells_for_row(
    row_box: tuple[int, int, int, int],
    indexes: list[int | None],
    aspect: float,
) -> list[Cell]:
    _x, row_y, row_w, row_h = row_box
    count = len(indexes)
    margin = round(row_w * 0.012)
    gap = max(2, round(row_w * 0.006))
    band_top = row_y + round(row_h * 0.14)
    band_h = max(1, row_h - round(row_h * 0.14) - round(row_h * 0.16))
    usable = row_w - 2 * margin - (count - 1) * gap
    window_w = max(1, usable // count)
    window_h = max(1, round(window_w / aspect))
    if window_h > band_h:
        window_h = band_h
        window_w = max(1, round(window_h * aspect))
    group_w = count * window_w + (count - 1) * gap
    x = max(0, (row_w - group_w) // 2)
    y = band_top + max(0, (band_h - window_h) // 2)
    cells = []
    for index in indexes:
        box = (x, y, window_w, window_h)
        cells.append(Cell(box, index, (x, row_y, window_w, row_h)))
        x += window_w + gap
    return cells
