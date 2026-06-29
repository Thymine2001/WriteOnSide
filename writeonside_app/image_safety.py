from __future__ import annotations

import gzip
import math
from functools import lru_cache
from io import BytesIO
import warnings
from pathlib import Path

from PIL import Image, ImageOps

MAX_IMAGE_PIXELS = 40_000_000
MAX_PREVIEW_PIXELS = 12_000_000
SVG_SUFFIXES = {".svg", ".svgz"}


class ImageTooLargeError(ValueError):
    pass


@lru_cache(maxsize=1)
def _svg_font_database():
    try:
        from svg2png_py import FontDatabase
    except ImportError as exc:
        raise OSError("SVG rendering requires svg2png-py.") from exc
    return FontDatabase.system()


def _check_image_size(image: Image.Image, pixel_limit: int = MAX_IMAGE_PIXELS) -> None:
    pixels = int(image.width) * int(image.height)
    if pixels > pixel_limit:
        raise ImageTooLargeError(f"image is too large: {image.width}x{image.height}")


def _read_svg_text(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.casefold() == ".svgz":
        data = gzip.decompress(data)
    return data.decode("utf-8-sig")


def _open_svg_checked(
    path: Path,
    *,
    pixel_limit: int,
    max_size: tuple[int, int] | None = None,
) -> Image.Image:
    try:
        from svg2png_py import svg_intrinsic_size, svg_to_png
    except ImportError as exc:
        raise OSError("SVG rendering requires svg2png-py.") from exc

    svg_text = _read_svg_text(path)
    font_db = _svg_font_database()
    width, height = svg_intrinsic_size(svg_text, font_db)
    width = max(1, int(math.ceil(float(width))))
    height = max(1, int(math.ceil(float(height))))
    if max_size is None:
        target_width = width
        target_height = height
        scale = 1.0
    else:
        max_width, max_height = max_size
        scale = min(1.0, max(1, max_width) / width, max(1, max_height) / height)
        target_width = max(1, int(round(width * scale)))
        target_height = max(1, int(round(height * scale)))
    if target_width * target_height > pixel_limit:
        raise ImageTooLargeError(f"image is too large: {target_width}x{target_height}")

    kwargs = {}
    if scale != 1.0:
        kwargs["transform"] = (scale, 0.0, 0.0, 0.0, scale, 0.0)
        kwargs["bg_size"] = (target_width, target_height)
    png_data = svg_to_png(svg_text, font_db, **kwargs)
    with Image.open(BytesIO(png_data)) as source:
        image = source.convert("RGBA")
        _check_image_size(image, pixel_limit)
        return image.copy()


def open_image_checked(path: Path, *, pixel_limit: int = MAX_IMAGE_PIXELS) -> Image.Image:
    if path.suffix.casefold() in SVG_SUFFIXES:
        return _open_svg_checked(path, pixel_limit=pixel_limit)
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
    if path.suffix.casefold() in SVG_SUFFIXES:
        image = _open_svg_checked(path, pixel_limit=pixel_limit, max_size=max_size)
    else:
        image = open_image_checked(path, pixel_limit=pixel_limit)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    return image.convert("RGBA")
