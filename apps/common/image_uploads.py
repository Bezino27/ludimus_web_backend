from io import BytesIO
from uuid import uuid4
import warnings

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers


MB = 1024 * 1024

IMAGE_UPLOAD_PROFILES = {
    "player": {
        "max_bytes": 20 * MB,
        "max_size": (1600, 1600),
        "quality": 85,
        "prefix": "player-photo",
        "preserve_transparency": False,
    },
    "article": {
        "max_bytes": 25 * MB,
        "max_size": (1920, 1920),
        "quality": 84,
        "prefix": "article-image",
        "preserve_transparency": False,
    },
    "hero": {
        "max_bytes": 30 * MB,
        "max_size": (2560, 1440),
        "quality": 86,
        "prefix": "hero-image",
        "preserve_transparency": False,
    },
    "gallery": {
        "max_bytes": 25 * MB,
        "max_size": (1920, 1920),
        "quality": 82,
        "prefix": "gallery-image",
        "preserve_transparency": False,
    },
    "partner_logo": {
        "max_bytes": 15 * MB,
        "max_size": (1600, 1600),
        "quality": 90,
        "prefix": "partner-logo",
        "preserve_transparency": True,
    },
}

SUPPORTED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def _format_limit(max_bytes):
    return f"{max_bytes // MB} MB"


def _has_transparency(image):
    return (
        image.mode in {"RGBA", "LA"}
        or (image.mode == "P" and "transparency" in image.info)
    )


def _prepare_for_webp(image, preserve_transparency):
    has_transparency = _has_transparency(image)

    if preserve_transparency and has_transparency:
        return image.convert("RGBA")

    if has_transparency:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background

    if image.mode not in {"RGB", "RGBA"}:
        return image.convert("RGB")

    return image


def optimize_uploaded_image(uploaded_file, profile_name, filename_prefix=None):
    if not uploaded_file:
        return uploaded_file

    profile = IMAGE_UPLOAD_PROFILES[profile_name]
    max_bytes = profile["max_bytes"]

    if uploaded_file.size and uploaded_file.size > max_bytes:
        raise serializers.ValidationError(
            f"Súbor je príliš veľký. Maximálna veľkosť je {_format_limit(max_bytes)}."
        )

    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(uploaded_file)
            image_format = (image.format or "").upper()

            if image_format == "JPG":
                image_format = "JPEG"

            if image_format not in SUPPORTED_IMAGE_FORMATS:
                raise serializers.ValidationError(
                    "Podporované formáty sú JPG, JPEG, PNG a WebP."
                )

            image = ImageOps.exif_transpose(image)
            image.load()
    except serializers.ValidationError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, ValueError) as exc:
        raise serializers.ValidationError(
            "Obrázok sa nepodarilo spracovať. Skontroluj, či súbor nie je poškodený."
        ) from exc
    finally:
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

    max_size = profile["max_size"]
    if image.width > max_size[0] or image.height > max_size[1]:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

    output_image = _prepare_for_webp(
        image,
        preserve_transparency=profile["preserve_transparency"],
    )

    buffer = BytesIO()
    try:
        output_image.save(
            buffer,
            format="WEBP",
            quality=profile["quality"],
            method=6,
        )
    except (OSError, ValueError) as exc:
        raise serializers.ValidationError(
            "Obrázok sa nepodarilo bezpečne uložiť."
        ) from exc

    prefix = filename_prefix or profile["prefix"]
    name = f"{prefix}-{uuid4().hex}.webp"

    return SimpleUploadedFile(
        name=name,
        content=buffer.getvalue(),
        content_type="image/webp",
    )
