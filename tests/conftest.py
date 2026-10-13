import os
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from film_contact_sheet.qt_plugins import ensure_qt_plugins_visible

ensure_qt_plugins_visible()

import pytest
from PIL import Image

from film_contact_sheet.models import (
    FormatGuess,
    FormatId,
    Frame,
    Roll,
    Settings,
    default_template,
)


class _RollFixture:
    def __init__(self, roll, template):
        self.roll = roll
        self.template = template


@pytest.fixture
def roll_of():
    image = Image.new("RGB", (30, 20), (10, 140, 30))
    frame = Frame(
        Path("0.jpg"),
        "0.jpg",
        1,
        None,
        False,
        False,
        (30, 20),
        date(2026, 3, 28),
        "",
        image,
    )
    roll = Roll(
        Path("roll"),
        "318167",
        date(2026, 3, 28),
        "Fuji",
        FormatGuess(FormatId.F135, True, 1.5),
        [frame],
        [],
    )
    return _RollFixture(roll, default_template())


@pytest.fixture
def settings(tmp_path):
    return Settings("", tmp_path, tmp_path, "default", None, [], [])
