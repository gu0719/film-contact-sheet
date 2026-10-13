from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageCms

from film_contact_sheet.models import ColorMode, Template

PROFILE_PATH = Path(__file__).resolve().parent / "assets" / "ISOcoated_v2_eci.icc"


def save_jpeg(image: Image.Image, path: Path, template: Template) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if template.color_mode == ColorMode.CMYK:
        converted = _to_cmyk(image.convert("RGB"))
        profile = PROFILE_PATH.read_bytes()
        converted.save(path, "JPEG", quality=90, icc_profile=profile)
        return
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    image.convert("RGB").save(path, "JPEG", quality=90, icc_profile=profile)


def soft_proof(image: Image.Image) -> Image.Image:
    converted = _to_cmyk(image.convert("RGB"))
    return _from_cmyk(converted)


def _to_cmyk(image: Image.Image) -> Image.Image:
    transform = ImageCms.buildTransformFromOpenProfiles(
        ImageCms.createProfile("sRGB"),
        ImageCms.getOpenProfile(str(PROFILE_PATH)),
        "RGB",
        "CMYK",
        renderingIntent=ImageCms.Intent.PERCEPTUAL,
    )
    return ImageCms.applyTransform(image, transform)


def _from_cmyk(image: Image.Image) -> Image.Image:
    transform = ImageCms.buildTransformFromOpenProfiles(
        ImageCms.getOpenProfile(str(PROFILE_PATH)),
        ImageCms.createProfile("sRGB"),
        "CMYK",
        "RGB",
        renderingIntent=ImageCms.Intent.PERCEPTUAL,
    )
    return ImageCms.applyTransform(image, transform)
