from __future__ import annotations

from dataclasses import dataclass


LARGE_DOCUMENT_CHAR_THRESHOLD = 1_000_000
LARGE_DOCUMENT_LINE_THRESHOLD = 10_000
VERY_LARGE_DOCUMENT_CHAR_THRESHOLD = 5_000_000
VERY_LARGE_DOCUMENT_LINE_THRESHOLD = 50_000
READ_MODE_RENDER_BYTE_LIMIT = 1_500_000
SOURCE_HIGHLIGHT_FULL_CHAR_LIMIT = 250_000
VISIBLE_HIGHLIGHT_MARGIN = 100


@dataclass(frozen=True)
class DocumentMetrics:
    characters: int
    lines: int

    @property
    def is_large(self) -> bool:
        return (
            self.characters >= LARGE_DOCUMENT_CHAR_THRESHOLD
            or self.lines >= LARGE_DOCUMENT_LINE_THRESHOLD
        )

    @property
    def is_very_large(self) -> bool:
        return (
            self.characters >= VERY_LARGE_DOCUMENT_CHAR_THRESHOLD
            or self.lines >= VERY_LARGE_DOCUMENT_LINE_THRESHOLD
        )


def metrics_for_content(content: str) -> DocumentMetrics:
    return DocumentMetrics(len(content), content.count("\n") + 1)


def limit_read_mode_content(
    content: str,
    limit: int = READ_MODE_RENDER_BYTE_LIMIT,
) -> tuple[str, bool]:
    encoded = content.encode("utf-8")
    if len(encoded) <= limit:
        return content, False
    limited = encoded[:limit].decode("utf-8", errors="ignore")
    boundary = limited.rfind("\n")
    if boundary >= max(0, len(limited) - 16_384):
        limited = limited[:boundary]
    return limited, True
