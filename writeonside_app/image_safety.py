from __future__ import annotations

import warnings
from pathlib import Path

from PIL import Image, ImageOps

MAX_IMAGE_PIXELS = 40_000_000
MAX_PREVIEW_PIXELS = 12_000_000


class ImageTooLargeError(ValueError):
    pass


def _check_image_size(image: Image.Image, pixel_limit: int = MAX_IMAGE_PIXELS) -> None:
    pixels = int(image.width) * int(image.height)
    if pixels > pixel_limit:
        raise ImageTooLargeError(f"image is too large: {image.width}x{image.height}")


def open_image_checked(path: Path, *, pixel_limit: int = MAX_IMAGE_PIXELS) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                _check_image_size(source, pixel_limit)
                image = ImageOps.exif_transpose(source)
                return image.copy()
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ImageTooLargeError(str(exc)) from exc


def load_thumbnail_image(path: Path, max_size: tuple[int, int], *, pixel_limit: int = MAX_PREVIEW_PIXELS) -> Image.Image:
    image = open_image_checked(path, pixel_limit=pixel_limit)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image.convert("RGBA")
