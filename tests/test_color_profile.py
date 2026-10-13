from PIL import Image

from film_contact_sheet.color_profile import save_jpeg, soft_proof
from film_contact_sheet.models import ColorMode, OutputSize, default_template


def test_srgb_and_cmyk_exports_keep_the_same_pixel_size(tmp_path):
    image = Image.new("RGB", (1080, 1350), (255, 0, 0))
    template = default_template()
    template.output_size = OutputSize.SOCIAL
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
        profile = open("film_contact_sheet/assets/ISOcoated_v2_eci.icc", "rb").read()
        assert saved.info["icc_profile"] == profile


def test_soft_proof_moves_pure_red_toward_print():
    red = Image.new("RGB", (16, 16), (255, 0, 0))
    proof = soft_proof(red)
    assert proof.mode == "RGB"
    assert proof.getpixel((8, 8)) != (255, 0, 0)
