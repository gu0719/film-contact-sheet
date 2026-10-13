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
