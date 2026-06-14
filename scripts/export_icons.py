from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

try:
    import fitz
except ImportError as exc:  # pragma: no cover - build-time dependency
    raise SystemExit("PyMuPDF is required to export icons: pip install pymupdf") from exc


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PNG_SIZE = 256
ICO_SIZES = (256, 128, 64, 48, 32, 16)

SVG_SOURCES = {
    ASSETS / "icon_dark.png": ASSETS / "writeonside_logo_dark.svg",
    ASSETS / "icon_light.png": ASSETS / "writeonside_logo_light.svg",
}


def svg_to_png(svg_path: Path, png_path: Path, size: int = PNG_SIZE) -> None:
    document = fitz.open(str(svg_path))
    try:
        page = document[0]
        rect = page.rect
        scale = size / max(rect.width, rect.height)
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=True)
        pixmap.save(str(png_path))
    finally:
        document.close()


def png_to_ico(png_path: Path, ico_path: Path, sizes: tuple[int, ...] = ICO_SIZES) -> None:
    source = Image.open(png_path).convert("RGBA")
    frames = [source.resize((size, size), Image.LANCZOS) for size in sizes]
    frames[0].save(
        ico_path,
        format="ICO",
        sizes=[(frame.width, frame.height) for frame in frames],
        append_images=frames[1:],
    )


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for png_path, svg_path in SVG_SOURCES.items():
        if not svg_path.exists():
            print(f"Missing SVG source: {svg_path}", file=sys.stderr)
            return 1
        svg_to_png(svg_path, png_path)
        print(f"Wrote {png_path.name} from {svg_path.name}")

    ico_path = ASSETS / "WriteOnSide.ico"
    png_to_ico(ASSETS / "icon_light.png", ico_path)
    print(f"Wrote {ico_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
