from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import ImageTk

from .dragdrop import IMAGE_SUFFIXES
from .image_safety import ImageTooLargeError, load_thumbnail_image
from .markdown import IMAGE_MD, resolve_markdown_path
from .preview import _is_pdf_path, pdf_page_index_from_fragment
from .wikilinks import parse_wiki_links

EDITOR_IMAGE_ELIDE_TAG = "md_image_elide"


@dataclass(frozen=True)
class EditorImageBlock:
    key: str
    line: int
    start: str
    end: str
    markdown: str
    image_path: Path
    asset_type: str = "image"
    initial_page: int = 0


def plan_editor_image_blocks(
    content: str,
    base_path: Path | None,
    *,
    wiki_asset_resolver: Callable[[str, Path | None], Path | None] | None = None,
) -> tuple[EditorImageBlock, ...]:
    blocks: list[EditorImageBlock] = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        image_match = IMAGE_MD.fullmatch(stripped)
        if image_match is not None:
            asset_path = resolve_markdown_path(image_match.group(2), base_path)
            asset_type = _previewable_asset_type(asset_path)
            if asset_type is not None:
                col = line.index(stripped)
                start = f"{line_no}.{col}"
                end = f"{line_no}.{col + len(stripped)}"
                blocks.append(
                    EditorImageBlock(
                        key=str(line_no),
                        line=line_no,
                        start=start,
                        end=end,
                        markdown=stripped,
                        image_path=asset_path.resolve(),
                        asset_type=asset_type,
                        initial_page=pdf_page_index_from_fragment(image_match.group(2)),
                    )
                )
            continue
        wiki_links = parse_wiki_links(stripped)
        if len(wiki_links) != 1 or wiki_links[0].raw != stripped or not wiki_links[0].embed:
            continue
        if wiki_asset_resolver is not None:
            asset_path = wiki_asset_resolver(wiki_links[0].target, base_path)
        else:
            asset_path = resolve_markdown_path(wiki_links[0].target, base_path)
        asset_type = _previewable_asset_type(asset_path)
        if asset_type is None:
            continue
        col = line.index(stripped)
        start = f"{line_no}.{col}"
        end = f"{line_no}.{col + len(stripped)}"
        blocks.append(
            EditorImageBlock(
                key=str(line_no),
                line=line_no,
                start=start,
                end=end,
                markdown=stripped,
                image_path=asset_path.resolve(),
                asset_type=asset_type,
                initial_page=pdf_page_index_from_fragment(wiki_links[0].heading),
            )
        )
    return tuple(blocks)


def _is_previewable_image(path: Path | None) -> bool:
    return bool(
        path
        and path.exists()
        and path.is_file()
        and path.suffix.casefold() in IMAGE_SUFFIXES
    )


def _previewable_asset_type(path: Path | None) -> str | None:
    if _is_previewable_image(path):
        return "image"
    if path and path.exists() and path.is_file() and _is_pdf_path(path):
        return "pdf"
    return None


def load_preview_photo(path: Path, max_width: int) -> ImageTk.PhotoImage | None:
    try:
        width = max(120, max_width)
        image = load_thumbnail_image(path, (width, width * 4))
        return ImageTk.PhotoImage(image)
    except (OSError, ImageTooLargeError):
        return None
