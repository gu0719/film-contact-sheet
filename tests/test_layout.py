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
