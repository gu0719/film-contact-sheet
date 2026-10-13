from __future__ import annotations

import os
import stat
from pathlib import Path

_HIDDEN = getattr(stat, "UF_HIDDEN", 0x8000)


def ensure_qt_plugins_visible() -> None:
    """Qt skips UF_HIDDEN plugins. Clear that flag so the app can start."""
    if os.name == "nt" or not hasattr(os.stat_result, "st_flags"):
        return
    try:
        import PySide6
    except ImportError:
        return
    root = Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
    if not root.is_dir():
        return
    for path in (root, *root.rglob("*")):
        try:
            flags = os.lstat(path).st_flags
        except OSError:
            continue
        if flags & _HIDDEN:
            try:
                os.chflags(path, flags & ~_HIDDEN)
            except OSError:
                continue
