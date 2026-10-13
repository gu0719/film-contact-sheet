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
