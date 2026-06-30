from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, unquote

from .dragdrop import IMAGE_SUFFIXES
from .markdown import IMAGE_MD, resolve_markdown_path
from .note_index import is_hidden_relative
from .preview import PDF_SUFFIX
from .text_files import EDITABLE_TEXT_SUFFIXES
from .wikilinks import WikiLinkIndex, parse_wiki_links, refresh_wiki_index

MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\n]+)\)")

TEXT_FILE_SUFFIXES = frozenset(EDITABLE_TEXT_SUFFIXES - {".md"})
PDF_SUFFIXES = frozenset({PDF_SUFFIX})
AUDIO_SUFFIXES = frozenset({".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".opus", ".aiff", ".aif"})
VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".m4v", ".mpeg", ".mpg"})
ARCHIVE_SUFFIXES = frozenset({".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz", ".tbz2"})

TYPE_FILTERS: dict[str, frozenset[str]] = {
    "all": frozenset(),
    "images": IMAGE_SUFFIXES,
    "text": TEXT_FILE_SUFFIXES,
    "pdf": PDF_SUFFIXES,
    "audio": AUDIO_SUFFIXES,
    "video": VIDEO_SUFFIXES,
    "archives": ARCHIVE_SUFFIXES,
}

FILTER_CATEGORY_ORDER: tuple[str, ...] = ("images", "text", "pdf", "audio", "video", "archives")


@dataclass(frozen=True)
class AttachmentInfo:
    path: Path
    relative: Path
    size: int
    suffix: str
    reference_count: int

    @property
    def referenced(self) -> bool:
        return self.reference_count > 0


@dataclass
class AttachmentIndexState:
    workspace_key: str
    attachments_folder: str
    root: Path
    items: tuple[AttachmentInfo, ...] = field(default_factory=tuple)
    attachment_mtimes: dict[str, int] = field(default_factory=dict)
    note_mtimes: dict[str, int] = field(default_factory=dict)


def attachments_root_path(workspace: Path, attachments_folder: str) -> Path:
    return (workspace.resolve() / attachments_folder).resolve()


def format_file_size(size: int) -> str:
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def suffix_category(suffix: str) -> str:
    normalized = suffix.casefold() if suffix.startswith(".") else f".{suffix.casefold()}"
    for key in FILTER_CATEGORY_ORDER:
        if normalized in TYPE_FILTERS[key]:
            return key
    return "other"


def iter_attachment_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.casefold() == ".md":
                continue
            if is_hidden_relative(path, root):
                continue
            try:
                files.append(path.resolve())
            except OSError:
                continue
    except OSError:
        return []
    files.sort(key=lambda item: item.as_posix().casefold())
    return files


def _resolve_link_target(raw: str, note_path: Path, wiki_index: WikiLinkIndex) -> Path | None:
    cleaned = unquote(raw.strip().strip("<>"))
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        return None
    cleaned = re.split(r"(?<!^)[#?]", cleaned, maxsplit=1)[0]
    resolved = resolve_markdown_path(cleaned, note_path)
    if resolved is not None:
        try:
            candidate = resolved.resolve()
            if candidate.exists() and candidate.is_file():
                return candidate
        except OSError:
            pass
    return wiki_index.resolve_asset(cleaned, note_path)


def _attachment_needles(attachment: Path, attachments_root: Path) -> tuple[str, ...]:
    try:
        relative = attachment.resolve().relative_to(attachments_root.resolve())
    except ValueError:
        return ()
    relative_posix = relative.as_posix()
    encoded = quote(relative_posix, safe="/")
    return (
        relative_posix.casefold(),
        relative_posix.replace("/", "\\").casefold(),
        encoded.casefold(),
    )


def _content_matches_needles(content_cf: str, needles: tuple[str, ...]) -> bool:
    return any(needle in content_cf for needle in needles)


def _file_mtime_ns(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def _collect_note_mtimes(workspace: Path) -> dict[str, int]:
    workspace = workspace.resolve()
    mtimes: dict[str, int] = {}
    try:
        for path in workspace.rglob("*.md"):
            if not path.is_file() or is_hidden_relative(path, workspace):
                continue
            mtime = _file_mtime_ns(path)
            if mtime is None:
                continue
            mtimes[str(path.resolve())] = mtime
    except OSError:
        pass
    return mtimes


def _collect_attachment_mtimes(root: Path) -> dict[str, int]:
    root = root.resolve()
    mtimes: dict[str, int] = {}
    for path in iter_attachment_files(root):
        mtime = _file_mtime_ns(path)
        if mtime is None:
            continue
        mtimes[str(path)] = mtime
    return mtimes


def attachment_index_is_current(
    state: AttachmentIndexState | None,
    workspace: Path,
    attachments_folder: str,
) -> bool:
    if state is None:
        return False
    workspace = workspace.resolve()
    if state.workspace_key != str(workspace):
        return False
    if state.attachments_folder != attachments_folder:
        return False
    root = attachments_root_path(workspace, attachments_folder)
    if state.root.resolve() != root.resolve():
        return False
    return (
        _collect_note_mtimes(workspace) == state.note_mtimes
        and _collect_attachment_mtimes(root) == state.attachment_mtimes
    )


def _iter_note_paths(workspace: Path) -> list[Path]:
    try:
        return [
            path.resolve()
            for path in workspace.rglob("*.md")
            if path.is_file() and not is_hidden_relative(path, workspace)
        ]
    except OSError:
        return []


def collect_attachment_references(
    workspace: Path,
    attachments_root: Path,
    *,
    wiki_index: WikiLinkIndex | None = None,
) -> dict[Path, int]:
    workspace = workspace.resolve()
    attachments_root = attachments_root.resolve()
    if wiki_index is None:
        wiki_index, _ = refresh_wiki_index(workspace, None)

    counts: dict[Path, int] = {}
    attachment_files = iter_attachment_files(attachments_root)
    pending_needles = {path: _attachment_needles(path, attachments_root) for path in attachment_files}

    def bump(path: Path) -> None:
        try:
            resolved = path.resolve()
            resolved.relative_to(attachments_root)
        except (ValueError, OSError):
            return
        counts[resolved] = counts.get(resolved, 0) + 1
        pending_needles.pop(resolved, None)

    for note_path in _iter_note_paths(workspace):
        try:
            content = note_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        content_cf = content.casefold()
        for match in IMAGE_MD.finditer(content):
            resolved = _resolve_link_target(match.group(2), note_path, wiki_index)
            if resolved is not None:
                bump(resolved)
        for match in MARKDOWN_LINK_RE.finditer(content):
            resolved = _resolve_link_target(match.group(1), note_path, wiki_index)
            if resolved is not None:
                bump(resolved)
        for link in parse_wiki_links(content):
            if not link.target:
                continue
            resolved = wiki_index.resolve_asset(link.target, note_path)
            if resolved is None:
                resolved = _resolve_link_target(link.target, note_path, wiki_index)
            if resolved is not None:
                bump(resolved)
        if not pending_needles:
            break
        matched = [
            path
            for path, needles in pending_needles.items()
            if needles and _content_matches_needles(content_cf, needles)
        ]
        for path in matched:
            bump(path)

    return counts


def _build_attachment_items(root: Path, references: dict[Path, int]) -> list[AttachmentInfo]:
    items: list[AttachmentInfo] = []
    for path in iter_attachment_files(root):
        try:
            relative = path.relative_to(root)
            size = path.stat().st_size
        except (OSError, ValueError):
            continue
        suffix = path.suffix.casefold() or ""
        items.append(
            AttachmentInfo(
                path=path,
                relative=relative,
                size=size,
                suffix=suffix,
                reference_count=references.get(path, 0),
            )
        )
    return items


def refresh_attachment_index(
    workspace: Path,
    attachments_folder: str,
    *,
    wiki_index: WikiLinkIndex | None = None,
    previous: AttachmentIndexState | None = None,
    force: bool = False,
) -> tuple[Path, list[AttachmentInfo], AttachmentIndexState]:
    workspace = workspace.resolve()
    root = attachments_root_path(workspace, attachments_folder)
    if not force and attachment_index_is_current(previous, workspace, attachments_folder):
        assert previous is not None
        return root, list(previous.items), previous

    references = collect_attachment_references(workspace, root, wiki_index=wiki_index)
    items = _build_attachment_items(root, references)
    state = AttachmentIndexState(
        workspace_key=str(workspace),
        attachments_folder=attachments_folder,
        root=root.resolve(),
        items=tuple(items),
        attachment_mtimes=_collect_attachment_mtimes(root),
        note_mtimes=_collect_note_mtimes(workspace),
    )
    return root, items, state


def scan_attachments(
    workspace: Path,
    attachments_folder: str,
    *,
    wiki_index: WikiLinkIndex | None = None,
    previous: AttachmentIndexState | None = None,
    force: bool = False,
) -> tuple[Path, list[AttachmentInfo], AttachmentIndexState]:
    root, items, state = refresh_attachment_index(
        workspace,
        attachments_folder,
        wiki_index=wiki_index,
        previous=previous,
        force=force,
    )
    return root, items, state


def matches_filter(
    info: AttachmentInfo,
    *,
    type_filter: str,
    query: str,
    unreferenced_only: bool,
) -> bool:
    if unreferenced_only and info.referenced:
        return False
    if type_filter and type_filter != "all":
        category = suffix_category(info.suffix)
        if type_filter == "other":
            if category != "other":
                return False
        elif category != type_filter:
            return False
    normalized_query = query.strip().casefold()
    if normalized_query:
        name_match = normalized_query in info.path.name.casefold()
        path_match = normalized_query in info.relative.as_posix().casefold()
        if not name_match and not path_match:
            return False
    return True
