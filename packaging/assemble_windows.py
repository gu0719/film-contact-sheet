"""Assemble a Windows folder from an embeddable CPython and win_amd64 wheels."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "dist" / "win-build"
STAGE = ROOT / "dist" / "胶卷样张"
WHEELS = BUILD / "wheels"
SITE = STAGE / "runtime" / "Lib" / "site-packages"

SKIP_WHEEL_PREFIXES = (
    "pyside6_addons",
    "pyside6_webengine",
    "pyside6_pdf",
)


def main() -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    SITE.mkdir(parents=True)
    _extract_python()
    _extract_wheels()
    _copy_app()
    for name in ("README.md", "启动胶卷样张.bat", "排查启动问题.bat"):
        shutil.copy2(ROOT / "packaging" / name, STAGE / name)
    archive = ROOT / "dist" / "胶卷样张-Windows.zip"
    if archive.exists():
        archive.unlink()
    shutil.make_archive(archive.with_suffix(""), "zip", ROOT / "dist", "胶卷样张")
    print(archive, archive.stat().st_size)


def _extract_python() -> None:
    runtime = STAGE / "runtime"
    with zipfile.ZipFile(BUILD / "python-embed.zip") as archive:
        archive.extractall(runtime)
    pth = next(runtime.glob("python*._pth"))
    pth.write_text("python312.zip\n.\nLib\\site-packages\nimport site\n", encoding="ascii")


def _extract_wheels() -> None:
    wheels = sorted(WHEELS.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"no wheels in {WHEELS}")
    ordered = [wheel for wheel in wheels if not wheel.name.startswith("pyside6-")]
    ordered.extend(wheel for wheel in wheels if wheel.name.startswith("pyside6-"))
    for wheel in ordered:
        if wheel.name.lower().startswith(SKIP_WHEEL_PREFIXES):
            print("skip", wheel.name)
            continue
        print("extract", wheel.name)
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(SITE)


def _copy_app() -> None:
    source = ROOT / "film_contact_sheet"
    target = SITE / "film_contact_sheet"
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


if __name__ == "__main__":
    main()
