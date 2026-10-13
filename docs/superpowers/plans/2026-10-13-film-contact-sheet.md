# 胶片 Contact Sheet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 做一个本机运行的 Python 桌面程序，把一个文件夹里的分幅翻拍 JPG 拼成一张 4:5 contact sheet，并可按模板导出 sRGB 或 CMYK JPG。

**Architecture:** 纯函数负责排版、画幅判断、卷名匹配、序号排序和绘制；`assemble.build_roll` 把读取和识别收成一份可编辑的 `Roll`；PySide6 只改这份数据并调用同一套绘制。识别器通过 `RebateReader` 注入，测试不下载 OCR 模型。

**Tech Stack:** Python 3.11、Pillow、PySide6、RapidOCR（onnxruntime）、pytest、pytest-qt。

**Spec:** `docs/superpowers/specs/2026-10-13-film-contact-sheet-design.md`

## Global Constraints

- 一次只打开一个文件夹，不进入子文件夹，只读 `.jpg` / `.jpeg`。
- 导出 JPG 质量 90，宽高比只有 4:5。尺寸只能是 `1080×1350`、`2160×2700`、`2480×3100`。
- 画面先画成 sRGB。模板色彩为 `CMYK` 时，用感知意图转到 ISO Coated v2（FOGRA39）再保存，并嵌入该 ICC。
- 无特性文件的输入按 sRGB 解释。
- 片条区域为画布高度 2% 到 68%，单行高度不超过 22%，行在该区域内顶对齐。
- 片条内部：上片边 16%、画面带 68%、下片边 16%。窗口间隙为行宽 1.5%，左右边距至少为行宽 2%。
- 底部文字距右 4%、距底 5%。字色在转 CMYK 之前决定：背后相对亮度高于 0.6 用 `#1A1A1A`，否则用 `#FFFFFF`。
- 序号和品牌字颜色 `#F2C14B`。黑格不印序号。品牌字为空则不印。
- 叠字字体文件为 `film_contact_sheet/assets/NotoSansSC-Regular.otf`。
- 出厂模板 id 为 `default`，名称为「默认」，不能删除，不能改名。模板名称唯一，总数最多 30。
- 数据目录：Windows `%APPDATA%/FilmContactSheet/`，其他系统 `~/Library/Application Support/FilmContactSheet/`。
- 界面文字用中文。图片不上传。
- 这一版不做：多文件夹、非 JPG 输入、规格绑进模板、模板级品牌字或字号、黑格序号、半格或宽幅、任意像素、非 4:5 画布。

## File Structure

- `film_contact_sheet/models.py` — 规格、尺寸、色彩、画格、一卷、模板、设置。
- `film_contact_sheet/layout.py` — 行宽循环和窗口几何。
- `film_contact_sheet/format_guess.py` — 画幅判断。
- `film_contact_sheet/film_names.py` — 出厂预设和卷名匹配。
- `film_contact_sheet/meta.py` — 日期、导出文件名、底部三行字、字色。
- `film_contact_sheet/frames.py` — 序号排序和警告。
- `film_contact_sheet/store.py` — 本机 JSON、模板和预设的增删改。
- `film_contact_sheet/ingest.py` — 列 JPG、EXIF 方向和日期、转到 sRGB。
- `film_contact_sheet/rebate.py` — 分开画面和片边、判断齿孔。
- `film_contact_sheet/ocr.py` — 边字数字解析和 `RebateReader`。
- `film_contact_sheet/assemble.py` — 把文件夹收成 `Roll`。
- `film_contact_sheet/sprocket.py` — 内置方孔齿孔图。
- `film_contact_sheet/render.py` — 绘制预览和导出图。
- `film_contact_sheet/color_profile.py` — sRGB / CMYK 转换和 JPEG 保存。
- `film_contact_sheet/ui/main_window.py` — 主窗口。
- `film_contact_sheet/ui/settings_dialog.py` — 设置。
- `film_contact_sheet/__main__.py` — 启动。
- `film_contact_sheet/assets/` — 字体和 FOGRA39 特性文件。
- `tests/` — 与上面模块对应的测试。

---

### Task 1: 项目骨架和数据模型

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `film_contact_sheet/__init__.py`
- Create: `film_contact_sheet/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: 无。
- Produces: `FormatId`、`ColorMode`、`OutputSize`、`SIZE_PIXELS`、`ROW_CYCLES`、`WINDOW_RATIO`、`Frame`、`FormatGuess`、`Roll`、`Template`、`Settings`、`default_template()`。

- [ ] **Step 1: Write the failing test**

```python
from film_contact_sheet.models import (
    SIZE_PIXELS,
    OutputSize,
    default_template,
)


def test_output_sizes_are_four_to_five():
    assert SIZE_PIXELS[OutputSize.SOCIAL] == (1080, 1350)
    assert SIZE_PIXELS[OutputSize.SHARP] == (2160, 2700)
    assert SIZE_PIXELS[OutputSize.A4] == (2480, 3100)
    for width, height in SIZE_PIXELS.values():
        assert width * 5 == height * 4


def test_default_template_matches_spec():
    template = default_template()
    assert template.id == "default"
    assert template.name == "默认"
    assert template.builtin is True
    assert template.background_path == ""
    assert template.strip_path == ""
    assert template.show_film_name is True
    assert template.show_order is True
    assert template.show_date is True
    assert template.show_count is True
    assert template.color_mode.value == "sRGB"
    assert template.output_size.value == "2160×2700"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`

Expected: FAIL with `ModuleNotFoundError: film_contact_sheet`

- [ ] **Step 3: Write minimal implementation**

`pyproject.toml`:

```toml
[project]
name = "film-contact-sheet"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "Pillow>=10.4",
  "PySide6>=6.6",
  "rapidocr-onnxruntime>=1.4",
]

[project.optional-dependencies]
dev = ["pytest>=8.2", "pytest-qt>=4.4"]

[tool.pytest.ini_options]
testpaths = ["tests"]
qt_api = "pyside6"

[tool.setuptools.packages.find]
include = ["film_contact_sheet*"]
```

`.gitignore`:

```gitignore
__pycache__/
.pytest_cache/
.venv/
*.pyc
.DS_Store
```

`film_contact_sheet/__init__.py` 为空文件。

`film_contact_sheet/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path

from PIL import Image


class FormatId(str, Enum):
    F135 = "135"
    F645 = "645"
    F66 = "66"
    F67 = "67"
    F68 = "68"
    F69 = "69"


class ColorMode(str, Enum):
    SRGB = "sRGB"
    CMYK = "CMYK"


class OutputSize(str, Enum):
    SOCIAL = "1080×1350"
    SHARP = "2160×2700"
    A4 = "2480×3100"


SIZE_PIXELS = {
    OutputSize.SOCIAL: (1080, 1350),
    OutputSize.SHARP: (2160, 2700),
    OutputSize.A4: (2480, 3100),
}

ROW_CYCLES = {
    FormatId.F135: (6,),
    FormatId.F645: (4,),
    FormatId.F66: (3,),
    FormatId.F67: (3, 3, 2, 2),
    FormatId.F68: (3,),
    FormatId.F69: (2,),
}

WINDOW_RATIO = {
    FormatId.F135: 3 / 2,
    FormatId.F645: 4 / 3,
    FormatId.F66: 1.0,
    FormatId.F67: 7 / 6,
    FormatId.F68: 4 / 3,
    FormatId.F69: 3 / 2,
}


@dataclass
class Frame:
    source_path: Path
    filename: str
    edge_number: int | None
    picture_box: tuple[int, int, int, int] | None
    uncertain_aspect: bool
    has_sprockets: bool
    oriented_size: tuple[int, int]
    date: date | None
    warning: str = ""
    image: Image.Image | None = None


@dataclass
class FormatGuess:
    format_id: FormatId
    confirmed: bool
    aspect_ratio: float | None


@dataclass
class Roll:
    folder: Path
    order_number: str
    shoot_date: date | None
    film_name: str
    format_guess: FormatGuess
    frames: list[Frame] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Template:
    id: str
    name: str
    background_path: str
    strip_path: str
    show_film_name: bool
    show_order: bool
    show_date: bool
    show_count: bool
    color_mode: ColorMode
    output_size: OutputSize
    builtin: bool


@dataclass
class Settings:
    brand_text: str
    backgrounds_dir: Path
    strips_dir: Path
    last_template_id: str
    last_export_dir: Path | None
    templates: list[Template]
    film_presets: list[str]


def default_template() -> Template:
    return Template(
        id="default",
        name="默认",
        background_path="",
        strip_path="",
        show_film_name=True,
        show_order=True,
        show_date=True,
        show_count=True,
        color_mode=ColorMode.SRGB,
        output_size=OutputSize.SHARP,
        builtin=True,
    )
```

Install: `python -m pip install -e ".[dev]"`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore film_contact_sheet/__init__.py film_contact_sheet/models.py tests/test_models.py
git commit -m "feat: add contact sheet domain models"
```

---

### Task 2: 行宽和窗口几何

**Files:**
- Create: `film_contact_sheet/layout.py`
- Test: `tests/test_layout.py`

**Interfaces:**
- Consumes: `FormatId`、`ROW_CYCLES`、`WINDOW_RATIO`。
- Produces: `row_plan(format_id, count) -> list[list[int | None]]`、`majority_landscape(sizes) -> bool`、`window_aspect(format_id, landscape) -> float`、`layout_sheet(canvas, format_id, count, landscape) -> SheetLayout`。`SheetLayout.rows` 的每一项是 `(row_box, cells)`。`row_box` 和 `Cell.box` 都是 `(x, y, w, h)`。`Cell.frame_index is None` 表示黑格。

- [ ] **Step 1: Write the failing test**

```python
from film_contact_sheet.layout import layout_sheet, majority_landscape, row_plan, window_aspect
from film_contact_sheet.models import FormatId


def test_row_plan_pads_only_the_last_row():
    assert row_plan(FormatId.F135, 7) == [
        [0, 1, 2, 3, 4, 5],
        [6, None, None, None, None, None],
    ]
    assert row_plan(FormatId.F67, 7) == [
        [0, 1, 2],
        [3, 4, 5],
        [6, None],
    ]
    assert row_plan(FormatId.F67, 10) == [
        [0, 1, 2],
        [3, 4, 5],
        [6, 7],
        [8, 9],
    ]
    assert row_plan(FormatId.F67, 12) == [
        [0, 1, 2],
        [3, 4, 5],
        [6, 7],
        [8, 9],
        [10, 11, None],
    ]
    assert row_plan(FormatId.F69, 8) == [[0, 1], [2, 3], [4, 5], [6, 7]]
    assert row_plan(FormatId.F68, 9) == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]


def test_tie_orientation_is_landscape_and_square_window_is_square():
    assert majority_landscape([(10, 20), (20, 10)]) is True
    assert majority_landscape([(10, 20), (11, 30)]) is False
    assert window_aspect(FormatId.F135, True) == 1.5
    assert window_aspect(FormatId.F135, False) == 1 / 1.5
    assert window_aspect(FormatId.F66, False) == 1.0


def test_layout_scales_by_the_same_percentages():
    small = layout_sheet((1080, 1350), FormatId.F135, 6, True)
    large = layout_sheet((2160, 2700), FormatId.F135, 6, True)
    (sx, sy, sw, sh), small_cells = small.rows[0]
    (lx, ly, lw, lh), large_cells = large.rows[0]
    assert sx == 0 and lx == 0
    assert sw == 1080 and lw == 2160
    assert abs(sy / 1350 - ly / 2700) < 0.01
    assert abs(sh / 1350 - lh / 2700) < 0.01
    assert abs(small_cells[0].box[0] / 1080 - large_cells[0].box[0] / 2160) < 0.015
    assert small_cells[0].frame_index == 0


def test_one_frame_of_135_pads_five_black_cells():
    layout = layout_sheet((1080, 1350), FormatId.F135, 1, True)
    cells = layout.rows[0][1]
    assert [cell.frame_index for cell in cells] == [0, None, None, None, None, None]
    photo = cells[0].box
    assert abs((photo[2] / photo[3]) - 1.5) < 0.05
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_layout.py -v`

Expected: FAIL with `ModuleNotFoundError: film_contact_sheet.layout`

- [ ] **Step 3: Write minimal implementation**

```python
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
    top = round(canvas_h * 0.02)
    available = round(canvas_h * 0.68) - top
    row_h = max(1, min(round(canvas_h * 0.22), available // len(plan)))
    aspect = window_aspect(format_id, landscape)
    rows = []
    for row_index, indexes in enumerate(plan):
        row_box = (0, top + row_index * row_h, canvas_w, row_h)
        rows.append((row_box, _cells_for_row(row_box, indexes, aspect)))
    return SheetLayout(canvas, rows)


def _cells_for_row(
    row_box: tuple[int, int, int, int],
    indexes: list[int | None],
    aspect: float,
) -> list[Cell]:
    _x, row_y, row_w, row_h = row_box
    count = len(indexes)
    margin = round(row_w * 0.02)
    gap = round(row_w * 0.015)
    band_h = max(1, round(row_h * 0.68))
    usable = row_w - 2 * margin - (count - 1) * gap
    window_w = max(1, usable // count)
    window_h = max(1, round(window_w / aspect))
    if window_h > band_h:
        window_h = band_h
        window_w = max(1, round(window_h * aspect))
    group_w = count * window_w + (count - 1) * gap
    x = max(0, (row_w - group_w) // 2)
    band_top = row_y + round(row_h * 0.16)
    y = band_top + max(0, (band_h - window_h) // 2)
    cells = []
    for index in indexes:
        cells.append(Cell((x, y, window_w, window_h), index))
        x += window_w + gap
    return cells
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_layout.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/layout.py tests/test_layout.py
git commit -m "feat: plan contact sheet rows and windows"
```

---

### Task 3: 画幅判断

**Files:**
- Create: `film_contact_sheet/format_guess.py`
- Test: `tests/test_format_guess.py`

**Interfaces:**
- Consumes: `FormatId`、`FormatGuess`。
- Produces: `guess_format(aspects: list[float | None], sprocket_flags: list[bool]) -> FormatGuess`。`aspects` 里的 `None` 不参加中位数，但计入张数。齿孔须严格超过一半。

- [ ] **Step 1: Write the failing test**

```python
from film_contact_sheet.format_guess import guess_format
from film_contact_sheet.models import FormatId


def guess(ratio, count, sprockets):
    aspects = [ratio] * count
    flags = [sprockets] * count
    return guess_format(aspects, flags)


def test_definitive_table():
    assert guess(1.50, 20, False).format_id == FormatId.F135
    assert guess(1.50, 20, False).confirmed is True
    assert guess(1.50, 8, False).format_id == FormatId.F69
    assert guess(1.33, 15, False).format_id == FormatId.F645
    assert guess(1.33, 9, False).format_id == FormatId.F68
    assert guess(1.02, 12, False).format_id == FormatId.F66
    assert guess(1.02, 13, False).format_id == FormatId.F66
    assert guess(1.18, 10, False).format_id == FormatId.F67
    assert guess(1.18, 11, False).format_id == FormatId.F67


def test_sprockets_force_135_even_when_short_or_square():
    result = guess(1.02, 8, True)
    assert result.format_id == FormatId.F135
    assert result.confirmed is True


def test_exactly_half_the_sprockets_do_not_force_135():
    result = guess_format([1.5, 1.5, 1.5, 1.5], [True, True, False, False])
    assert result.format_id == FormatId.F69
    assert result.confirmed is True


def test_gaps_are_suggestions_and_stay_unconfirmed():
    gap = guess(1.33, 11, False)
    assert gap.format_id == FormatId.F68
    assert gap.confirmed is False
    wide_gap = guess(1.50, 14, False)
    assert wide_gap.format_id == FormatId.F69
    assert wide_gap.confirmed is False
    no_ratio = guess_format([None, None], [False, False])
    assert no_ratio.confirmed is False
    assert no_ratio.format_id == FormatId.F69
    assert guess_format([None] * 14, [False] * 14).format_id == FormatId.F645
    assert guess_format([None] * 9, [False] * 9).format_id == FormatId.F68


def test_uncertain_frames_do_not_move_the_median():
    result = guess_format([1.5, 1.5, None], [False, False, False])
    assert result.aspect_ratio == 1.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_format_guess.py -v`

Expected: FAIL with `ModuleNotFoundError: film_contact_sheet.format_guess`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_format_guess.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/format_guess.py tests/test_format_guess.py
git commit -m "feat: guess film format from aspect ratio and count"
```

---

### Task 4: 卷名匹配和出厂预设

**Files:**
- Create: `film_contact_sheet/film_names.py`
- Test: `tests/test_film_names.py`

**Interfaces:**
- Consumes: 无。
- Produces: `FACTORY_PRESETS: tuple[str, ...]`、`match_film_name(ocr_text: str, presets: list[str]) -> str`。

- [ ] **Step 1: Write the failing test**

```python
from film_contact_sheet.film_names import FACTORY_PRESETS, match_film_name


def test_factory_list_contains_the_sample_stock_and_manual_names():
    assert "Fujifilm Superia Premium 400" in FACTORY_PRESETS
    assert "乐凯新锐 100" in FACTORY_PRESETS
    assert "上海 GP3 100" in FACTORY_PRESETS
    assert len(FACTORY_PRESETS) == 40


def test_match_ignores_brand_case_and_punctuation():
    presets = list(FACTORY_PRESETS)
    assert match_film_name("FUJICOLOR SUPERIA X-TRA 400", presets) == "Fujifilm Superia X-TRA 400"
    assert match_film_name("portra 400", presets) == "Kodak Portra 400"
    assert match_film_name("not a film", presets) == "not a film"
    assert match_film_name("   ", presets) == ""


def test_longer_token_match_wins():
    presets = ["Fujifilm Superia Premium 400", "Fujifilm Superia X-TRA 400"]
    text = "SUPERIA PREMIUM 400 SUPERIA X-TRA 400"
    assert match_film_name(text, presets) == "Fujifilm Superia Premium 400"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_film_names.py -v`

Expected: FAIL with `ModuleNotFoundError: film_contact_sheet.film_names`

- [ ] **Step 3: Write minimal implementation**

```python
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
        return ocr_text.strip()
    return best


def _tokens(preset: str) -> list[str]:
    words = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", " ", preset).upper().split()
    kept = [word for word in words if word not in _BRANDS]
    if not kept:
        kept = words
    return [_flatten(word) for word in kept if _flatten(word)]


def _flatten(text: str) -> str:
    return re.sub(r"[^0-9A-Z\u4e00-\u9fff]", "", text.upper())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_film_names.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/film_names.py tests/test_film_names.py
git commit -m "feat: match rebate text to factory film names"
```

---

### Task 5: 日期、文件名、底部文字和字色

**Files:**
- Create: `film_contact_sheet/meta.py`
- Test: `tests/test_meta.py`

**Interfaces:**
- Consumes: `Template`。
- Produces: `choose_date(dates: list[date | None]) -> date | None`、`export_filename(order_number: str) -> str`、`footer_lines(...) -> list[str]`、`text_rgb(luminance: float) -> tuple[int, int, int]`、`average_luminance(image, box) -> float`。

- [ ] **Step 1: Write the failing test**

```python
from datetime import date

from PIL import Image

from film_contact_sheet.meta import (
    average_luminance,
    choose_date,
    export_filename,
    footer_lines,
    text_rgb,
)
from film_contact_sheet.models import default_template


def test_choose_date_uses_the_most_common_then_the_earlier_day():
    first = date(2026, 3, 28)
    second = date(2026, 4, 1)
    assert choose_date([first, second, first, None]) == first
    assert choose_date([second, first]) == first
    assert choose_date([None, None]) is None


def test_export_filename_replaces_illegal_characters():
    assert export_filename("318167") == "318167.jpg"
    assert export_filename('a/b:c*') == "a_b_c_.jpg"
    assert export_filename("   ") == "contact-sheet.jpg"


def test_footer_lines_follow_the_toggles():
    template = default_template()
    assert footer_lines("Fuji", "318167", date(2026, 3, 28), 1, template) == [
        "Fuji",
        "Order: 318167",
        "2026-03-28 | 1 images",
    ]
    template.show_film_name = False
    template.show_order = False
    template.show_date = False
    assert footer_lines("Fuji", "318167", None, 36, template) == ["36 images"]
    template.show_count = False
    assert footer_lines("Fuji", "318167", None, 36, template) == []
    template.show_date = True
    template.show_count = False
    assert footer_lines("", "", date(2026, 3, 28), 36, template) == ["2026-03-28"]


def test_text_color_threshold_and_luminance():
    assert text_rgb(0.61) == (0x1A, 0x1A, 0x1A)
    assert text_rgb(0.6) == (255, 255, 255)
    white = Image.new("RGB", (4, 4), "white")
    assert average_luminance(white, (0, 0, 4, 4)) > 0.6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_meta.py -v`

Expected: FAIL with `ModuleNotFoundError: film_contact_sheet.meta`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import re
from collections import Counter
from datetime import date

from PIL import Image

from film_contact_sheet.models import Template

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def choose_date(dates: list[date | None]) -> date | None:
    present = [value for value in dates if value is not None]
    if not present:
        return None
    counts = Counter(present)
    highest = max(counts.values())
    return min(value for value, count in counts.items() if count == highest)


def export_filename(order_number: str) -> str:
    cleaned = _ILLEGAL.sub("_", order_number).strip().rstrip(". ")
    if not cleaned:
        cleaned = "contact-sheet"
    return cleaned + ".jpg"


def footer_lines(
    film_name: str,
    order_number: str,
    shoot_date: date | None,
    count: int,
    template: Template,
) -> list[str]:
    lines = []
    if template.show_film_name and film_name.strip():
        lines.append(film_name.strip())
    if template.show_order and order_number.strip():
        lines.append(f"Order: {order_number.strip()}")
    date_part = shoot_date.isoformat() if shoot_date else ""
    count_part = f"{count} images"
    meta = None
    if template.show_date and template.show_count and date_part:
        meta = f"{date_part} | {count_part}"
    elif template.show_date and not template.show_count and date_part:
        meta = date_part
    elif template.show_count:
        meta = count_part
    if meta:
        lines.append(meta)
    return lines


def text_rgb(luminance: float) -> tuple[int, int, int]:
    if luminance > 0.6:
        return (0x1A, 0x1A, 0x1A)
    return (255, 255, 255)


def average_luminance(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    crop = image.crop(box).convert("RGB")
    pixels = list(crop.getdata())
    if not pixels:
        return 1.0
    return sum(_relative_luminance(pixel) for pixel in pixels) / len(pixels)


def _relative_luminance(pixel: tuple[int, int, int]) -> float:
    def channel(value: int) -> float:
        x = value / 255
        if x <= 0.04045:
            return x / 12.92
        return ((x + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(pixel[0]), channel(pixel[1]), channel(pixel[2]))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_meta.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/meta.py tests/test_meta.py
git commit -m "feat: format sheet date, filename, and footer lines"
```

---

### Task 6: 序号排序和警告

**Files:**
- Create: `film_contact_sheet/frames.py`
- Test: `tests/test_frames.py`

**Interfaces:**
- Consumes: `Frame`。
- Produces: `sort_frames(frames: list[Frame]) -> list[Frame]`、`apply_warnings(frames: list[Frame]) -> None`。警告文案只使用 `未识别`、`序号重复`、`序号未递增`，多条用 `、` 连接。

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
from pathlib import Path

from film_contact_sheet.frames import apply_warnings, sort_frames
from film_contact_sheet.models import Frame


def frame(name, number):
    return Frame(Path(name), name, number, None, False, False, (30, 20), date(2026, 3, 28))


def test_sort_puts_missing_numbers_last_by_filename():
    ordered = sort_frames([frame("c.jpg", None), frame("b.jpg", 4), frame("a.jpg", None), frame("d.jpg", 2)])
    assert [item.filename for item in ordered] == ["d.jpg", "b.jpg", "a.jpg", "c.jpg"]


def test_warnings_mark_missing_duplicates_and_decreases():
    frames = [frame("a.jpg", 2), frame("b.jpg", 2), frame("c.jpg", 1), frame("d.jpg", None)]
    apply_warnings(frames)
    assert frames[0].warning == "序号重复"
    assert frames[1].warning == "序号重复、序号未递增"
    assert frames[2].warning == "序号未递增"
    assert frames[3].warning == "未识别"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_frames.py -v`

Expected: FAIL with `ModuleNotFoundError: film_contact_sheet.frames`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from collections import Counter

from film_contact_sheet.models import Frame


def sort_frames(frames: list[Frame]) -> list[Frame]:
    numbered = [frame for frame in frames if frame.edge_number is not None]
    missing = [frame for frame in frames if frame.edge_number is None]
    numbered.sort(key=lambda frame: (frame.edge_number, frame.filename))
    missing.sort(key=lambda frame: frame.filename)
    return numbered + missing


def apply_warnings(frames: list[Frame]) -> None:
    counts = Counter(frame.edge_number for frame in frames if frame.edge_number is not None)
    for index, frame in enumerate(frames):
        reasons = []
        if frame.edge_number is None:
            reasons.append("未识别")
        else:
            if counts[frame.edge_number] > 1:
                reasons.append("序号重复")
            if index > 0:
                previous = frames[index - 1].edge_number
                if previous is not None and frame.edge_number <= previous:
                    reasons.append("序号未递增")
        frame.warning = "、".join(reasons)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_frames.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/frames.py tests/test_frames.py
git commit -m "feat: sort edge numbers and flag sequence problems"
```

---

### Task 7: 本机存储和模板规则

**Files:**
- Create: `film_contact_sheet/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `Settings`、`Template`、`default_template()`、`FACTORY_PRESETS`。
- Produces: `default_data_dir() -> Path`、`load_settings(root: Path) -> Settings`、`save_settings(root: Path, settings: Settings) -> None`、`add_template`、`duplicate_template`、`rename_template`、`delete_template`、`update_template`。违规时抛出 `TemplateError`。第一次加载会创建 `backgrounds` 和 `strips`。

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_store.py -v`

Expected: FAIL with `ModuleNotFoundError: film_contact_sheet.store`

- [ ] **Step 3: Write minimal implementation**

`film_contact_sheet/store.py` 使用下面这份实现。`add_template` 复制出厂模板的开关、色彩和尺寸，但 id 用 `uuid4().hex`，`builtin` 为 `False`。

```python
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
    (root / "settings.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
    return Settings("", root / "backgrounds", root / "strips", "default", None, [default_template()], list(FACTORY_PRESETS))


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_store.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/store.py tests/test_store.py
git commit -m "feat: store templates and film presets locally"
```

---

### Task 8: 读取文件夹

**Files:**
- Create: `film_contact_sheet/ingest.py`
- Test: `tests/test_ingest.py`

**Interfaces:**
- Consumes: Pillow。
- Produces: `NoJpegError`、`LoadedImage`、`scan_folder(folder: Path) -> tuple[list[LoadedImage], list[tuple[str, str]]]`。`LoadedImage` 含转正后的 RGB 图、`date | None`、路径和文件名。打不开的文件进入第二个列表，不抛异常。目录里没有 JPG 时抛出 `NoJpegError`。

- [ ] **Step 1: Write the failing test**

```python
from datetime import date

from PIL import Image

from film_contact_sheet.ingest import NoJpegError, scan_folder


def test_scan_reads_only_top_level_jpegs_and_exif_date(tmp_path):
    image = Image.new("RGB", (20, 10), "red")
    exif = image.getexif()
    exif[36867] = "2026:03:28 10:11:12"
    exif[274] = 6
    image.save(tmp_path / "A.JPG", exif=exif)
    Image.new("RGB", (4, 4), "blue").save(tmp_path / "note.png")
    nested = tmp_path / "nested"
    nested.mkdir()
    Image.new("RGB", (4, 4), "green").save(nested / "hidden.jpg")
    (tmp_path / "broken.jpg").write_bytes(b"not a jpeg")
    loaded, skipped = scan_folder(tmp_path)
    assert [item.filename for item in loaded] == ["A.JPG"]
    assert loaded[0].image.size == (10, 20)
    assert loaded[0].date == date(2026, 3, 28)
    assert skipped == [("broken.jpg", "无法打开")]


def test_empty_folder_raises(tmp_path):
    try:
        scan_folder(tmp_path)
        raise AssertionError("expected NoJpegError")
    except NoJpegError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ingest.py -v`

Expected: FAIL with `ModuleNotFoundError: film_contact_sheet.ingest`

- [ ] **Step 3: Write minimal implementation**

用 `folder.iterdir()`，不递归。后缀比较前转小写，只接受 `.jpg` 和 `.jpeg`。没有此类文件时抛出 `NoJpegError("这个文件夹里没有 JPG。")`。

每张图：`Image.open` 失败则记录 `(filename, "无法打开")`。成功则 `ImageOps.exif_transpose`，再转 RGB。若 `info["icc_profile"]` 存在，用 `ImageCms.profileToProfile` 转到 sRGB；转换失败就保持刚才的 RGB。日期优先读 EXIF 36867，否则读 306，解析 `YYYY:MM:DD` 的前 10 个字符；都没有就用 `path.stat().st_mtime` 的本地日期。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ingest.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/ingest.py tests/test_ingest.py
git commit -m "feat: load oriented jpeg frames from one folder"
```

---

### Task 9: 画面和片边分开

**Files:**
- Create: `film_contact_sheet/rebate.py`
- Test: `tests/test_rebate.py`

**Interfaces:**
- Consumes: Pillow。
- Produces: `Split(picture_box, has_sprockets, uncertain)`、`split_rebate(image) -> Split`。`picture_box` 是 `(x, y, w, h)`。

- [ ] **Step 1: Write the failing test**

```python
from PIL import Image, ImageDraw

from film_contact_sheet.rebate import split_rebate


def test_sprocket_band_marks_135_and_returns_the_inner_picture():
    image = Image.new("RGB", (200, 120), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 24, 199, 96), fill=(20, 180, 40))
    for x in range(8, 200, 24):
        draw.rectangle((x, 4, x + 10, 16), fill="white")
        draw.rectangle((x, 104, x + 10, 116), fill="white")
    split = split_rebate(image)
    assert split.has_sprockets is True
    assert split.uncertain is False
    _x, y, _w, h = split.picture_box
    assert 16 <= y <= 32
    assert 60 <= h <= 90


def test_flat_image_is_uncertain_and_has_no_sprockets():
    split = split_rebate(Image.new("RGB", (80, 60), (20, 180, 40)))
    assert split.has_sprockets is False
    assert split.uncertain is True
    assert split.picture_box == (0, 0, 80, 60)


def test_orange_border_without_holes_is_a_certain_inner_picture():
    image = Image.new("RGB", (100, 80), (180, 90, 30))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 10, 87, 69), fill=(20, 180, 40))
    split = split_rebate(image)
    assert split.has_sprockets is False
    assert split.uncertain is False
    x, y, w, h = split.picture_box
    assert x >= 8 and y >= 6
    assert w < 100 and h < 80
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rebate.py -v`

Expected: FAIL with `ModuleNotFoundError: film_contact_sheet.rebate`

- [ ] **Step 3: Write minimal implementation**

按前面测试能通过的规则实现，不要再引入第二种分割策略：

- 在顶部 18% 和底部 18% 的中间行上数近白像素段。近白指 RGB 都大于 220。一段行程至少 3 个白段才算有齿孔。
- 有齿孔时，从上往下和从下往上跳过白孔比例大于 5% 的行，剩下的垂直范围就是画面。左右不裁。`uncertain=False`。
- 没有齿孔时，取上下两条边的像素中位数当作片边颜色。与它的通道差之和大于 40 视为画面。找到画面的外接矩形。矩形面积达到整张的 90% 时，`picture_box` 为整张，`uncertain=True`。否则 `uncertain=False`。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rebate.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/rebate.py tests/test_rebate.py
git commit -m "feat: separate picture area from film rebate"
```

---

### Task 10: 边字解析和收成一卷

**Files:**
- Create: `film_contact_sheet/ocr.py`
- Create: `film_contact_sheet/assemble.py`
- Test: `tests/test_ocr.py`
- Test: `tests/test_assemble.py`

**Interfaces:**
- Consumes: `scan_folder`、`split_rebate`、`guess_format`、`match_film_name`、`choose_date`、`sort_frames`、`apply_warnings`、`Frame`、`Roll`。
- Produces: `parse_edge_number(text: str) -> int | None`、`RebateReader.read(image) -> str`、`RapidRebateReader`、`build_roll(folder, reader, presets) -> Roll`。`parse_edge_number` 取文本里第一个 0 到 99 的整数，没有就返回 `None`。

- [ ] **Step 1: Write the failing test**

```python
from PIL import Image, ImageDraw

from film_contact_sheet.assemble import build_roll
from film_contact_sheet.film_names import FACTORY_PRESETS
from film_contact_sheet.models import FormatId
from film_contact_sheet.ocr import RapidRebateReader, parse_edge_number


class FakeReader:
    def __init__(self, text):
        self.text = text

    def read(self, image):
        return self.text


def test_parse_edge_number_ignores_film_speed():
    assert parse_edge_number("FRAME 12 400") == 12
    assert parse_edge_number("PORTRA 400") is None
    assert parse_edge_number("") is None


def test_reader_joins_engine_text():
    class Engine:
        def __call__(self, array):
            return [[["box", "12", 0.9], ["box", "PORTRA 400", 0.8]], None]

    assert RapidRebateReader(Engine()).read(Image.new("RGB", (8, 8))) == "12 PORTRA 400"


def test_build_roll_sorts_numbers_and_names_the_folder(tmp_path):
    for name, color in (("b.jpg", (255, 0, 0)), ("a.jpg", (0, 255, 0))):
        Image.new("RGB", (60, 40), color).save(tmp_path / name)
    roll = build_roll(tmp_path, FakeReader("3 PORTRA 400"), list(FACTORY_PRESETS))
    assert roll.order_number == tmp_path.name
    assert roll.film_name == "Kodak Portra 400"
    assert roll.frames[0].edge_number == 3
    assert roll.format_guess.format_id == FormatId.F69
    assert roll.format_guess.confirmed is True
```

两张没有齿孔、比例 1.5 的图，张数 ≤ 10，判定为已确认的 6×9。两张序号都是 3，所以应出现 `序号重复`。把这个断言加进同一个测试。

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ocr.py tests/test_assemble.py -v`

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

`parse_edge_number` 用 `re.findall(r"\d+")`，返回第一个 `0 <= n <= 99` 的整数。

`RapidRebateReader.read` 把图片放大 3 倍，转成 numpy RGB 数组，调用 `engine(array)`。`engine` 为空时才导入 `RapidOCR` 并创建。结果为空时返回空字符串，否则把每条的文字用空格连起来。

`build_roll` 调用 `scan_folder`。对每张成功的图调用 `split_rebate`。不确定时序号为空、片边文字为空。确定时裁出画面上方和下方两块，上下拼成一张交给 `reader.read`，再用 `parse_edge_number`。长宽比用画面矩形的长边除以短边；不确定的图传 `None`。然后 `guess_format`、`match_film_name(全部片边文字, presets)`、`choose_date`、`sort_frames`、`apply_warnings`。订单号是 `folder.name`。跳过的文件放进 `roll.skipped`。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ocr.py tests/test_assemble.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/ocr.py film_contact_sheet/assemble.py tests/test_ocr.py tests/test_assemble.py
git commit -m "feat: assemble a roll from rebate text"
```

---

### Task 11: 绘制片条、序号和黑格

**Files:**
- Create: `film_contact_sheet/sprocket.py`
- Create: `film_contact_sheet/render.py`
- Test: `tests/test_render_strip.py`

**Interfaces:**
- Consumes: `layout_sheet`、`majority_landscape`、`Roll`、`Template`、`Settings`、`default_sprocket()`。
- Produces: `default_sprocket() -> Image.Image`、`render_sheet(roll, template, settings, target_size=None) -> Image.Image`。`target_size` 为空时用模板尺寸。绘制结果保持 RGB，本任务不做 CMYK。

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
from pathlib import Path

from PIL import Image

from film_contact_sheet.models import (
    FormatGuess,
    FormatId,
    Frame,
    Roll,
    Settings,
    default_template,
)
from film_contact_sheet.render import render_sheet
from film_contact_sheet.sprocket import default_sprocket


def roll_of(count, fmt):
    frames = []
    for index in range(count):
        image = Image.new("RGB", (30, 20), (10, 140, 30))
        frames.append(
            Frame(Path(f"{index}.jpg"), f"{index}.jpg", index + 1, None, False, False, (30, 20), date(2026, 3, 28), "", image)
        )
    return Roll(
        Path("roll"),
        "318167",
        date(2026, 3, 28),
        "Kodak Portra 400",
        FormatGuess(fmt, True, 1.5),
        frames,
        [],
    )


def settings(tmp_path):
    return Settings("", tmp_path, tmp_path, "default", None, [], [])


def test_default_sprocket_has_white_holes_on_black():
    tile = default_sprocket()
    assert tile.getpixel((40, 4)) == (0, 0, 0)
    assert tile.getpixel((40, 18))[0] > 220


def test_black_cells_have_no_yellow_numbers_and_sprockets_reach_both_sides(tmp_path):
    from film_contact_sheet.layout import layout_sheet

    template = default_template()
    template.output_size = template.output_size.__class__("1080×1350")
    image = render_sheet(roll_of(1, FormatId.F135), template, settings(tmp_path), (1080, 1350))
    assert image.size == (1080, 1350)
    row_box, cells = layout_sheet((1080, 1350), FormatId.F135, 1, True).rows[0]
    photo_rebate = _bottom_rebate(row_box, cells[0].box)
    black_rebate = _bottom_rebate(row_box, cells[1].box)
    assert _has_yellow(image.crop(photo_rebate))
    assert not _has_yellow(image.crop(black_rebate))
    top_rebate = (0, row_box[1], 1080, max(1, round(row_box[3] * 0.16)))
    left = image.crop((0, top_rebate[1], 540, top_rebate[1] + top_rebate[3]))
    right = image.crop((540, top_rebate[1], 1080, top_rebate[1] + top_rebate[3]))
    assert _has_white(left) and _has_white(right)


def _bottom_rebate(row_box, cell_box):
    _x, row_y, _w, row_h = row_box
    top = row_y + round(row_h * 0.84)
    return (cell_box[0], top, cell_box[0] + cell_box[2], row_y + row_h)


def _has_yellow(image):
    for pixel in image.convert("RGB").getdata():
        red, green, blue = pixel
        if red > 200 and green > 150 and blue < 120:
            return True
    return False


def _has_white(image):
    return any(pixel[0] > 220 and pixel[1] > 220 and pixel[2] > 220 for pixel in image.convert("RGB").getdata())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_render_strip.py -v`

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

`default_sprocket()` 返回 80×200 的 RGB 图：底色黑，顶部和底部各一个白色圆角矩形齿孔。

`render_sheet`：

1. 用 `target_size` 或 `SIZE_PIXELS[template.output_size]` 建白底 RGB 图。
2. 底图路径存在且能打开时，按 cover 铺满画布。失败或路径为空则保持白底。
3. 齿孔路径存在且能打开时用它，否则用 `default_sprocket()`。缩放到行高，横向重复，裁到行宽，贴到 `layout_sheet` 给出的行位置。
4. 有照片的窗口：从 `frame.image` 按 `picture_box` 裁切，再按窗口宽高比居中裁切，缩放到窗口并贴上。黑格的窗口涂成 `#000000`。
5. 只在有照片的窗口下方、该行下片边内，用 `#F2C14B` 和 Noto Sans SC 居中画 `str(edge_number)`。序号为 `None` 时不画。
6. `settings.brand_text` 非空时，每行上片边画一次。起始字号为上片边高度的 40%，最小为该高度的一半。仍超出行宽就画到一张最大宽度的透明图上再裁切贴上。

方向用 `majority_landscape`，尺寸取画面矩形，没有矩形时用 `oriented_size`。

字体路径：`Path(__file__).parent / "assets" / "NotoSansSC-Regular.otf"`。文件不存在时抛出 `FileNotFoundError`，提示先完成 Task 13 的字体下载。本任务的测试只检查齿孔和黄色像素，品牌字传空字符串，因此还用不到字体文件。序号也需要字体。测试前先放一个可用的 Noto Sans SC Regular OTF 到该路径；Task 13 会把它正式纳入资源。若字体尚未下载，本任务第一步用 Pillow 画出序号时允许暂时调用同一个路径，测试命令改为先执行 Task 13 的下载再回来跑。为了不打乱顺序，本任务的序号用 `ImageFont.truetype`，字体缺失时测试先下载：

```bash
mkdir -p film_contact_sheet/assets
curl -L -o /tmp/NotoSansSC.zip https://github.com/notofonts/noto-cjk/releases/download/Sans2.004/13_NotoSansSC.zip
unzip -p /tmp/NotoSansSC.zip "OTF/SimplifiedChinese/NotoSansSC-Regular.otf" > film_contact_sheet/assets/NotoSansSC-Regular.otf
```

下载失败就停止，不要换字体。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_render_strip.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/sprocket.py film_contact_sheet/render.py film_contact_sheet/assets/NotoSansSC-Regular.otf tests/test_render_strip.py
git commit -m "feat: draw film strips, numbers, and black pads"
```

---

### Task 12: 底部文字、丢失的素材和三种尺寸

**Files:**
- Modify: `film_contact_sheet/render.py`
- Test: `tests/test_render_footer.py`

**Interfaces:**
- Consumes: `footer_lines`、`average_luminance`、`text_rgb`、Task 11 的 `render_sheet`。
- Produces: 同一 `render_sheet` 现在会画底部文字。字号按画布高度：胶卷名 2.8%，订单号 1.8%，日期行 1.4%。右对齐。

- [ ] **Step 1: Write the failing test**

```python
from PIL import Image

from film_contact_sheet.models import OutputSize
from film_contact_sheet.render import render_sheet


def test_hidden_footer_line_adds_no_ink(tmp_path, roll_of, settings):
    template = roll_of.template
    template.show_film_name = False
    template.show_order = False
    template.show_date = False
    template.show_count = False
    blank = render_sheet(roll_of.roll, template, settings, (1080, 1350))
    template.show_film_name = True
    named = render_sheet(roll_of.roll, template, settings, (1080, 1350))
    assert _ink(blank.crop((0, 1080, 1080, 1350))) == 0
    assert _ink(named.crop((0, 1080, 1080, 1350))) > 0


def test_dark_background_uses_white_text(tmp_path, roll_of, settings):
    background = tmp_path / "dark.png"
    Image.new("RGB", (20, 20), (0, 20, 40)).save(background)
    template = roll_of.template
    template.background_path = str(background)
    template.show_order = False
    template.show_date = False
    template.show_count = False
    image = render_sheet(roll_of.roll, template, settings, (1080, 1350))
    assert image.getpixel((1070, 1340))[0] > 200


def test_missing_background_is_white_and_sizes_match_template(tmp_path, roll_of, settings):
    template = roll_of.template
    template.background_path = str(tmp_path / "gone.png")
    template.strip_path = str(tmp_path / "gone-strip.png")
    for size, pixels in (
        (OutputSize.SOCIAL, (1080, 1350)),
        (OutputSize.SHARP, (2160, 2700)),
        (OutputSize.A4, (2480, 3100)),
    ):
        template.output_size = size
        image = render_sheet(roll_of.roll, template, settings)
        assert image.size == pixels
    assert render_sheet(roll_of.roll, template, settings, (1080, 1350)).getpixel((10, 1300)) == (255, 255, 255)


def _ink(image):
    return sum(1 for pixel in image.getdata() if pixel != (255, 255, 255))
```

在 `tests/conftest.py` 里提供 `roll_of` 和 `settings` fixture，复用 Task 11 的一卷一张 135 图，胶卷名是 `Fuji`。三个测试都放进 `tests/test_render_footer.py`。

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_render_footer.py -v`

Expected: FAIL，因为底部还没有文字，或尺寸没有按模板读取。

- [ ] **Step 3: Write minimal implementation**

在贴完片条之后、返回之前画 `footer_lines(...)`。张数用 `len(roll.frames)`。先按字号量出文字块，用 `average_luminance` 取这块背后的亮度，再整块用 `text_rgb` 的颜色画。关掉的行不占位。底图和齿孔的打开要用 `try/except OSError`，失败时分别退回白底和 `default_sprocket()`。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_render_footer.py tests/test_render_strip.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/render.py tests/test_render_footer.py tests/conftest.py
git commit -m "feat: draw footer text and honor template output size"
```

---

### Task 13: sRGB 和 CMYK 导出

**Files:**
- Create: `film_contact_sheet/color_profile.py`
- Create: `film_contact_sheet/assets/ISOcoated_v2_eci.icc`
- Modify: `film_contact_sheet/render.py`
- Test: `tests/test_color_profile.py`

**Interfaces:**
- Consumes: Task 12 的 RGB 绘制结果、模板的 `color_mode`。
- Produces: `save_jpeg(image, path, template)`、`soft_proof(image) -> Image.Image`。`render_sheet(..., proof=False)` 在 `proof=True` 时对 RGB 结果做软打样后仍返回 RGB。

- [ ] **Step 1: 下载特性文件并写失败测试**

```bash
curl -L -o /tmp/eci_offset_2009.zip https://www.eci.org/_media/downloads/icc_profiles_from_eci/eci_offset_2009.zip
unzip -p /tmp/eci_offset_2009.zip "eci_offset_2009/ISOcoated_v2_eci.icc" > film_contact_sheet/assets/ISOcoated_v2_eci.icc
```

压缩包里的实际路径以 `unzip -l` 为准，取出文件名包含 `ISOcoated_v2_eci.icc` 的那一个。下载失败就停止。

```python
from PIL import Image

from film_contact_sheet.color_profile import save_jpeg, soft_proof
from film_contact_sheet.models import ColorMode, default_template


def test_srgb_and_cmyk_exports_keep_the_same_pixel_size(tmp_path):
    image = Image.new("RGB", (1080, 1350), (255, 0, 0))
    template = default_template()
    template.output_size = template.output_size.__class__("1080×1350")
    srgb_path = tmp_path / "srgb.jpg"
    save_jpeg(image, srgb_path, template)
    with Image.open(srgb_path) as saved:
        assert saved.size == (1080, 1350)
        assert saved.mode == "RGB"
        assert saved.info.get("icc_profile")

    template.color_mode = ColorMode.CMYK
    cmyk_path = tmp_path / "cmyk.jpg"
    save_jpeg(image, cmyk_path, template)
    with Image.open(cmyk_path) as saved:
        assert saved.size == (1080, 1350)
        assert saved.mode == "CMYK"
        assert saved.info["icc_profile"] == open(
            "film_contact_sheet/assets/ISOcoated_v2_eci.icc", "rb"
        ).read()


def test_soft_proof_moves_pure_red_toward_print():
    red = Image.new("RGB", (16, 16), (255, 0, 0))
    proof = soft_proof(red)
    assert proof.mode == "RGB"
    assert proof.getpixel((8, 8)) != (255, 0, 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_color_profile.py -v`

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

`save_jpeg` 以质量 90 保存。`sRGB` 时嵌入 `ImageCms.createProfile("sRGB")` 的字节。`CMYK` 时用感知意图从 sRGB 转到 `ISOcoated_v2_eci.icc`，保存 CMYK，并嵌入该文件的原始字节。

`soft_proof` 先做同一次 CMYK 转换，再用感知意图转回 sRGB。

`render_sheet` 增加 `proof: bool = False`。为真时返回 `soft_proof` 的结果。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_color_profile.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/color_profile.py film_contact_sheet/render.py film_contact_sheet/assets/ISOcoated_v2_eci.icc tests/test_color_profile.py
git commit -m "feat: export sRGB and FOGRA39 CMYK jpegs"
```

---

### Task 14: 主窗口

**Files:**
- Create: `film_contact_sheet/ui/__init__.py`
- Create: `film_contact_sheet/ui/main_window.py`
- Create: `tests/conftest.py` 中的 `QT_QPA_PLATFORM=offscreen`（若 Task 12 已建该文件，则只追加这两行）
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: `build_roll`、`render_sheet`、`load_settings`、`save_settings`、`apply_warnings`、`export_filename`。
- Produces: `MainWindow(reader, data_root)`。公开方法 `load_folder(path: Path)` 和 `export_to(path: Path)`。

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from PIL import Image

from film_contact_sheet.ui.main_window import MainWindow


class FakeReader:
    def read(self, image):
        return "8 PORTRA 400"


def test_load_folder_fills_order_number_and_edge_number(qtbot, tmp_path):
    Image.new("RGB", (40, 30), "red").save(tmp_path / "frame.jpg")
    window = MainWindow(FakeReader(), tmp_path / "data")
    qtbot.addWidget(window)
    window.load_folder(tmp_path)
    assert window.order_edit.text() == tmp_path.name
    assert window.film_edit.currentText() == "Kodak Portra 400"
    assert window.frame_list.item(0).data(0x0100) == 8
    assert window.preview.pixmap() is not None


def test_editing_a_number_refreshes_the_warning(qtbot, tmp_path):
    Image.new("RGB", (40, 30), "red").save(tmp_path / "one.jpg")
    Image.new("RGB", (40, 30), "blue").save(tmp_path / "two.jpg")
    window = MainWindow(FakeReader(), tmp_path / "data")
    qtbot.addWidget(window)
    window.load_folder(tmp_path)
    window.set_edge_number(1, 8)
    assert "序号重复" in window.frame_list.item(1).text()
```

`0x0100` 是 `Qt.ItemDataRole.UserRole`。测试里写成 `Qt.ItemDataRole.UserRole`，需要从 `PySide6.QtCore` 导入。

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_main_window.py -v`

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

主窗口从左到右三栏：

- 左侧 `QListWidget`，对象名能让测试读到 `frame_list`。每项文字是 `文件名  序号  警告`。UserRole 存序号，没有序号时存 `None`。内部拖动改变 `roll.frames` 的顺序，不改序号，然后 `apply_warnings` 并重画预览。
- 中间 `QLabel`，对象名对应 `preview`，按宽度约 480 像素调用 `render_sheet(..., target_size=按比例缩小, proof=模板是 CMYK)`。
- 右侧：规格 `QComboBox`、胶卷名可编辑 `QComboBox`、订单号 `QLineEdit`、日期 `QDateEdit`、模板 `QComboBox`、按钮「导出」。规格未确认时组合框样式为红色边框。用户改规格后把 `confirmed` 设为 `True` 并去掉红框。

顶部按钮「打开文件夹」调用 `QFileDialog.getExistingDirectory`，测试直接调用 `load_folder`。没有 JPG 时弹出「这个文件夹里没有 JPG。」，不替换当前一卷。打不开的文件在列表里显示 `无法打开：文件名`，不可拖动。

`set_edge_number(row, number)` 把该画格序号改成 `None`（空输入）或整数，再跑 `apply_warnings` 和预览。`order_edit`、`film_edit` 是测试要读的属性名，中文标签仍是「订单号」和「胶卷名」。

日期控件在 `shoot_date is None` 时显示空。用户选了日期就写回 `roll.shoot_date`。

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_main_window.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/ui tests/test_main_window.py tests/conftest.py
git commit -m "feat: add the contact sheet main window"
```

---

### Task 15: 设置窗口

**Files:**
- Create: `film_contact_sheet/ui/settings_dialog.py`
- Modify: `film_contact_sheet/ui/main_window.py`
- Test: `tests/test_settings_dialog.py`

**Interfaces:**
- Consumes: `add_template`、`duplicate_template`、`rename_template`、`delete_template`、`update_template`、`save_settings`。
- Produces: `SettingsDialog(settings, parent=None)`。接受后写回同一个 `Settings` 对象。

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_settings_dialog.py -v`

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

对话框用中文：模板列表、新增、复制、重命名、删除、底图、齿孔、四个显示开关、色彩、尺寸、胶卷名列表、新增、修改、删除、品牌字、打开底图文件夹、打开齿孔文件夹、更改这两个文件夹。

底图列表来自底图目录里的 JPG 和 PNG，第一项是「白底」，存成空路径。齿孔列表来自齿孔目录里的 PNG，第一项是「内置方孔」，存成空路径。色彩只有 `sRGB` 和 `CMYK`。尺寸只有三种像素值。

默认模板的删除和重命名按钮禁用。`accept` 时调用 store 里的更新函数；`TemplateError` 用消息框显示，不关闭对话框。主窗口的「设置」按钮打开它，关闭后刷新模板下拉框和预览，并 `save_settings`。

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_settings_dialog.py tests/test_main_window.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/ui/settings_dialog.py film_contact_sheet/ui/main_window.py tests/test_settings_dialog.py
git commit -m "feat: edit templates, presets, and brand text"
```

---

### Task 16: 导出和失败提示

**Files:**
- Modify: `film_contact_sheet/ui/main_window.py`
- Test: `tests/test_export.py`

**Interfaces:**
- Consumes: `save_jpeg`、`export_filename`、`render_sheet`。
- Produces: `MainWindow.export_to(path: Path)`。保存框只是调用它的外壳。

- [ ] **Step 1: Write the failing test**

```python
from PIL import Image

from film_contact_sheet.models import ColorMode, OutputSize
from film_contact_sheet.ui.main_window import MainWindow


class FakeReader:
    def read(self, image):
        return "1 GOLD 200"


def test_export_writes_jpeg_and_leaves_existing_file_when_render_fails(qtbot, tmp_path, monkeypatch):
    Image.new("RGB", (30, 20), "red").save(tmp_path / "a.jpg")
    window = MainWindow(FakeReader(), tmp_path / "data")
    qtbot.addWidget(window)
    window.load_folder(tmp_path)
    target = tmp_path / "out" / "318167.jpg"
    target.parent.mkdir()
    window.export_to(target)
    assert target.exists()
    with Image.open(target) as saved:
        assert saved.size == (2160, 2700)
        assert saved.mode == "RGB"

    window.current_template().output_size = OutputSize.A4
    window.current_template().color_mode = ColorMode.CMYK
    printed = tmp_path / "print.jpg"
    window.export_to(printed)
    with Image.open(printed) as saved:
        assert saved.size == (2480, 3100)
        assert saved.mode == "CMYK"

    original = target.read_bytes()

    def explode(*args, **kwargs):
        raise OSError("磁盘已满")

    monkeypatch.setattr("film_contact_sheet.ui.main_window.save_jpeg", explode)
    try:
        window.export_to(target)
        raise AssertionError("export should fail")
    except OSError as exc:
        assert str(exc) == "磁盘已满"
    assert target.read_bytes() == original
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_export.py -v`

Expected: FAIL，因为还没有 `export_to`

- [ ] **Step 3: Write minimal implementation**

`export_to` 在没有成功读入的画格时抛出 `ExportError("没有可以导出的照片。")`。否则渲染全尺寸、`proof=False`，先写入 `目标文件名 + ".partial"`，成功后 `os.replace` 到目标路径。任何异常都删掉 partial 再抛出，不改已经存在的目标文件。

「导出」按钮打开 `QFileDialog.getSaveFileName`。默认目录是 `last_export_dir`，默认文件名是 `export_filename(订单号)`。用户取消则什么都不做。保存成功后记住目录并 `save_settings`。失败时消息框显示异常文字。

没有可导出照片时，按钮的消息框显示「没有可以导出的照片。」打开空文件夹的消息仍是「这个文件夹里没有 JPG。」

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_export.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/ui/main_window.py tests/test_export.py
git commit -m "feat: export jpeg without damaging an existing file"
```

---

### Task 17: 启动入口

**Files:**
- Create: `film_contact_sheet/__main__.py`
- Test: `tests/test_main_window.py` 里追加一条导入测试，不新开窗口循环。

**Interfaces:**
- Consumes: `MainWindow`、`default_data_dir`、`RapidRebateReader`。
- Produces: `python -m film_contact_sheet` 打开主窗口。

- [ ] **Step 1: Write the failing test**

```python
from film_contact_sheet.__main__ import build_window


def test_build_window_uses_the_rapid_reader(tmp_path, monkeypatch):
    monkeypatch.setattr("film_contact_sheet.__main__.default_data_dir", lambda: tmp_path)
    window = build_window()
    assert window.data_root == tmp_path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_main_window.py::test_build_window_uses_the_rapid_reader -v`

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

```python
import sys

from PySide6.QtWidgets import QApplication

from film_contact_sheet.ocr import RapidRebateReader
from film_contact_sheet.store import default_data_dir
from film_contact_sheet.ui.main_window import MainWindow


def build_window() -> MainWindow:
    return MainWindow(RapidRebateReader(), default_data_dir())


def main() -> None:
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

`MainWindow` 要保存 `self.data_root`。`RapidRebateReader()` 在第一次 `read` 之前不要创建 OCR 引擎，避免这条测试下载模型。

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest -v`

Expected: PASS，全部测试通过。

- [ ] **Step 5: Commit**

```bash
git add film_contact_sheet/__main__.py tests/test_main_window.py
git commit -m "feat: launch the contact sheet app"
```

手动看一次：`QT_QPA_PLATFORM=offscreen` 不要加，直接运行 `python -m film_contact_sheet`。打开一个只有几张 JPG 的文件夹，确认预览、模板里的尺寸和色彩、以及导出的文件模式与规格文档一致。
