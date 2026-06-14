from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .frontmatter import NoteMetadata, parse_front_matter


def is_hidden_relative(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part.startswith(".") for part in relative.parts)


@dataclass
class NoteIndexState:
    metadata: dict[str, NoteMetadata]
    tag_counts: dict[str, int]
    mtimes: dict[str, float]


def _count_tags(metadata: dict[str, NoteMetadata]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for note_metadata in metadata.values():
        for tag in note_metadata.tags:
            counts[tag] = counts.get(tag, 0) + 1
    return counts


def _read_note_metadata(path: Path) -> NoteMetadata | None:
    try:
        content = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return None
    return parse_front_matter(content, path.stem)


def build_note_index(
    scope: Path,
    previous: NoteIndexState | None = None,
) -> NoteIndexState:
    scope = scope.resolve()
    metadata: dict[str, NoteMetadata] = dict(previous.metadata) if previous else {}
    mtimes: dict[str, float] = dict(previous.mtimes) if previous else {}

    current_paths: set[str] = set()
    try:
        notes = scope.rglob("*.md")
        for path in notes:
            if is_hidden_relative(path, scope):
                continue
            resolved = str(path.resolve())
            current_paths.add(resolved)
            try:
                mtime = path.stat().st_mtime_ns
            except OSError:
                continue
            if previous and resolved in mtimes and mtimes[resolved] == mtime:
                continue
            note_metadata = _read_note_metadata(path)
            if note_metadata is None:
                metadata.pop(resolved, None)
                mtimes.pop(resolved, None)
                continue
            metadata[resolved] = note_metadata
            mtimes[resolved] = mtime
    except OSError:
        pass

    if previous:
        for stale_path in set(metadata) - current_paths:
            metadata.pop(stale_path, None)
            mtimes.pop(stale_path, None)

    return NoteIndexState(metadata=metadata, tag_counts=_count_tags(metadata), mtimes=mtimes)


def filter_workspace_files(
    scope: Path,
    query: str,
    selected_tags: set[str],
    metadata: dict[str, NoteMetadata],
    limit: int = 1500,
) -> list[Path]:
    scope = scope.resolve()
    scope_text = str(scope)
    scope_prefix_length = len(scope_text)
    normalized_query = query.strip().casefold()
    matches: list[Path] = []
    for raw_path, note_metadata in metadata.items():
        relative_text = raw_path[scope_prefix_length:].lstrip("\\/")
        if normalized_query and normalized_query not in relative_text.casefold():
            continue
        if selected_tags and not selected_tags.issubset(note_metadata.tags):
            continue
        matches.append(Path(raw_path))
        if len(matches) >= limit:
            break
    return matches
