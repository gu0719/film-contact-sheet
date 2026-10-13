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
