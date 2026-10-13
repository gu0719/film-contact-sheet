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
    assert match_film_name("not a film", presets) == ""
    assert match_film_name("   ", presets) == ""


def test_longer_token_match_wins():
    presets = ["Fujifilm Superia Premium 400", "Fujifilm Superia X-TRA 400"]
    text = "SUPERIA PREMIUM 400 SUPERIA X-TRA 400"
    assert match_film_name(text, presets) == "Fujifilm Superia Premium 400"
