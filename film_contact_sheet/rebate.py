from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class Split:
    picture_box: tuple[int, int, int, int]
    has_sprockets: bool
    uncertain: bool


def split_rebate(image: Image.Image) -> Split:
    rgb = np.asarray(image.convert("RGB"))
    height, width = rgb.shape[:2]
    top_band = max(1, int(height * 0.18))
    sprockets = _row_has_sprockets(rgb, top_band // 2) or _row_has_sprockets(
        rgb, int(height * 0.82) + (height - int(height * 0.82)) // 2
    )
    if sprockets:
        top, bottom = _content_bounds(rgb)
        return Split((0, top, width, max(1, bottom - top)), True, False)
    border = _median_border(rgb)
    left, top, right, bottom = _bounds_unlike(rgb, border)
    area = max(0, right - left) * max(0, bottom - top)
    if area >= 0.9 * width * height:
        return Split((0, 0, width, height), False, True)
    return Split((left, top, max(1, right - left), max(1, bottom - top)), False, False)


def _row_has_sprockets(rgb: np.ndarray, y: int) -> bool:
    height = rgb.shape[0]
    y = min(max(y, 0), height - 1)
    white = np.all(rgb[y] > 220, axis=-1)
    padded = np.concatenate(([False], white, [False]))
    changes = np.diff(padded.astype(np.int8))
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)
    return int(np.count_nonzero(ends - starts >= 3)) >= 3


def _content_bounds(rgb: np.ndarray) -> tuple[int, int]:
    height, width = rgb.shape[:2]
    white = np.all(rgb > 220, axis=-1).mean(axis=1)
    dark = np.all(rgb < 40, axis=-1).mean(axis=1)
    picture = np.flatnonzero((white <= 0.05) & (dark < 0.8))
    if picture.size == 0:
        return height - 1, height
    return int(picture[0]), int(picture[-1]) + 1


def _median_border(rgb: np.ndarray) -> np.ndarray:
    samples = np.concatenate((rgb[0], rgb[-1]))
    order = np.lexsort((samples[:, 2], samples[:, 1], samples[:, 0]))
    return samples[order[len(order) // 2]]


def _bounds_unlike(rgb: np.ndarray, border: np.ndarray) -> tuple[int, int, int, int]:
    height, width = rgb.shape[:2]
    unlike = np.abs(rgb.astype(np.int16) - border.astype(np.int16)).sum(axis=-1) > 40
    row_hits = unlike[:, ::2].sum(axis=1)
    rows = np.flatnonzero(row_hits > width * 0.25)
    if rows.size == 0:
        return 0, 0, width, height
    top = int(rows[0])
    bottom = int(rows[-1]) + 1
    span = max(1, bottom - top)
    col_hits = unlike[top:bottom:2].sum(axis=0)
    cols = np.flatnonzero(col_hits > span * 0.25)
    if cols.size == 0:
        return width - 1, top, width, bottom
    return int(cols[0]), top, int(cols[-1]) + 1, bottom
