from __future__ import annotations

import os
import logging
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .frontmatter import parse_front_matter, split_front_matter
from .note_index import is_hidden_relative


WIKI_LINK_PATTERN = re.compile(r"(!)?\[\[([^\[\]\n]+?)\]\]")
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class WikiLink:
    raw: str
    target: str
    heading: str
    alias: str
    embed: bool
    start: int
    end: int
    block_id: str = ""

    @property
    def label(self) -> str:
        if self.alias:
            return self.alias
        if self.block_id:
            if self.target:
                base = Path(self.target).stem or self.target
            elif self.heading:
                base = self.heading
            else:
                base = "Block"
            return f"{base} (#^{self.block_id})"
        return self.heading or Path(self.target).stem or self.target


@dataclass(frozen=True)
class WikiNote:
    path: Path
    title: str
    aliases: tuple[str, ...]
    headings: tuple[str, ...]
    links: tuple[WikiLink, ...]


@dataclass(frozen=True)
class WikiLinkRewrite:
    path: Path
    original: str
    updated: str


@dataclass
class _StagedWikiLinkRewrite:
    rewrite: WikiLinkRewrite
    destination: Path
    updated_temp: Path
    rollback_temp: Path


def normalize_wiki_name(value: str) -> str:
    text = value.strip().replace("\\", "/")
    if text.casefold().endswith(".md"):
        text = text[:-3]
    return text.strip("/").casefold()


def parse_wiki_links(content: str) -> tuple[WikiLink, ...]:
    links: list[WikiLink] = []
    for match in WIKI_LINK_PATTERN.finditer(content):
        inner = match.group(2).strip()
        destination, separator, alias = inner.partition("|")
        target, heading_separator, heading = destination.partition("#")
        heading = heading.strip() if heading_separator else ""
        block_id = ""
        if heading.startswith("^"):
            block_id = heading[1:].strip()
            heading = ""
        links.append(
            WikiLink(
                raw=match.group(0),
                target=target.strip(),
                heading=heading,
                alias=alias.strip() if separator else "",
                embed=bool(match.group(1)),
                start=match.start(),
                end=match.end(),
                block_id=block_id,
            )
        )
    return tuple(links)


def parse_markdown_headings(content: str) -> tuple[str, ...]:
    _header, body = split_front_matter(content)
    headings: list[str] = []
    in_code_block = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        match = MARKDOWN_HEADING_PATTERN.match(line)
        if match:
            headings.append(match.group(2).strip())
    return tuple(headings)


@dataclass
class WikiIndexState:
    notes: dict[Path, WikiNote] = field(default_factory=dict)
    mtimes: dict[Path, int] = field(default_factory=dict)


def collect_identifier_keys(path: Path, root: Path, title: str, aliases: tuple[str, ...]) -> set[str]:
    keys: set[str] = set()
    try:
        relative = path.relative_to(root).with_suffix("").as_posix()
        keys.add(normalize_wiki_name(relative))
    except ValueError:
        pass
    keys.add(normalize_wiki_name(path.stem))
    normalized_title = normalize_wiki_name(title)
    if normalized_title:
        keys.add(normalized_title)
    for alias in aliases:
        normalized = normalize_wiki_name(alias)
        if normalized:
            keys.add(normalized)
    keys.discard("")
    return keys


def preferred_link_target(source: Path, target: Path, root: Path, fallback: str) -> str:
    try:
        relative = target.relative_to(source.parent)
        if relative.suffix.casefold() == ".md":
            relative = relative.with_suffix("")
        text = relative.as_posix()
        if text and text != ".":
            return text
    except ValueError:
        pass
    try:
        return target.relative_to(root).with_suffix("").as_posix()
    except ValueError:
        return fallback


def format_wiki_link(link: WikiLink, target: str) -> str:
    prefix = "!" if link.embed else ""
    destination = target
    if link.block_id:
        destination = f"{destination}#^{link.block_id}"
    elif link.heading:
        destination = f"{destination}#{link.heading}"
    if link.alias:
        destination = f"{destination}|{link.alias}"
    return f"{prefix}[[{destination}]]"


def _read_wiki_note(path: Path, root: Path) -> WikiNote | None:
    try:
        content = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return None
    metadata = parse_front_matter(content, path.stem)
    resolved = path.resolve()
    return WikiNote(
        path=resolved,
        title=metadata.title or path.stem,
        aliases=metadata.aliases,
        headings=parse_markdown_headings(content),
        links=parse_wiki_links(content),
    )


def refresh_wiki_index(root: Path, previous: WikiIndexState | None = None) -> tuple["WikiLinkIndex", WikiIndexState]:
    root = root.resolve()
    notes: dict[Path, WikiNote] = dict(previous.notes) if previous else {}
    mtimes: dict[Path, int] = dict(previous.mtimes) if previous else {}
    current_paths: set[Path] = set()
    try:
        for path in root.rglob("*.md"):
            if is_hidden_relative(path, root):
                continue
            resolved = path.resolve()
            current_paths.add(resolved)
            try:
                mtime = path.stat().st_mtime_ns
            except OSError:
                continue
            if previous and resolved in mtimes and mtimes[resolved] == mtime and resolved in notes:
                continue
            note = _read_wiki_note(path, root)
            if note is None:
                notes.pop(resolved, None)
                mtimes.pop(resolved, None)
                continue
            notes[resolved] = note
            mtimes[resolved] = mtime
    except OSError:
        pass
    if previous:
        for stale_path in set(notes) - current_paths:
            notes.pop(stale_path, None)
            mtimes.pop(stale_path, None)
    state = WikiIndexState(notes=notes, mtimes=mtimes)
    return WikiLinkIndex(root, notes), state


def find_notes_linking_to(index: WikiLinkIndex, target_path: Path) -> set[Path]:
    resolved_target = target_path.resolve()
    candidates: set[Path] = set()
    for note, _link in index.backlinks(resolved_target):
        candidates.add(note.path)
    for note in index.notes.values():
        for link in note.links:
            if index.resolve(link.target, note.path) == resolved_target:
                candidates.add(note.path)
    return candidates


def plan_wikilink_rewrites_after_rename(
    root: Path,
    old_path: Path,
    new_path: Path,
    *,
    old_title: str,
    old_aliases: tuple[str, ...],
    new_title: str | None = None,
    index: WikiLinkIndex | None = None,
    candidate_paths: set[Path] | None = None,
) -> tuple[WikiLinkRewrite, ...]:
    root = root.resolve()
    old_path = old_path.resolve()
    new_path = new_path.resolve()
    if new_path.suffix.casefold() != ".md":
        return ()
    old_keys = collect_identifier_keys(old_path, root, old_title, old_aliases)
    if not old_keys:
        return ()
    if new_title is None:
        try:
            content = new_path.read_text(encoding="utf-8-sig")
            new_title = parse_front_matter(content, new_path.stem).title or new_path.stem
        except (OSError, UnicodeError):
            new_title = new_path.stem
    new_default = new_title or new_path.stem
    index = index or WikiLinkIndex.build(root)
    if candidate_paths is None:
        candidate_paths = find_notes_linking_to(index, old_path)
        if not candidate_paths:
            candidate_paths = {
                note.path
                for note in index.notes.values()
                if any(normalize_wiki_name(link.target) in old_keys for link in note.links)
            }
    planned: list[WikiLinkRewrite] = []
    for note_path in sorted(candidate_paths):
        note_path = note_path.resolve()
        try:
            note_path.relative_to(root)
            content = note_path.read_text(encoding="utf-8-sig")
            # Validate write access before any rename or replacement occurs.
            with note_path.open("r+b"):
                pass
        except (OSError, UnicodeError, ValueError) as exc:
            raise OSError(f"Cannot prepare Wiki link update for {note_path}: {exc}") from exc
        links = parse_wiki_links(content)
        if not links:
            continue
        replacements: list[tuple[int, int, str]] = []
        for link in links:
            resolved = index.resolve(link.target, note_path)
            target_norm = normalize_wiki_name(link.target)
            if resolved != old_path and target_norm not in old_keys:
                continue
            new_target = preferred_link_target(note_path, new_path, root, new_default)
            new_raw = format_wiki_link(link, new_target)
            if new_raw != link.raw:
                replacements.append((link.start, link.end, new_raw))
        if not replacements:
            continue
        updated = content
        for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
            updated = updated[:start] + replacement + updated[end:]
        if updated != content:
            planned.append(WikiLinkRewrite(note_path, content, updated))
    return tuple(planned)


def _write_transaction_temp(destination: Path, content: str, label: str) -> Path:
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{destination.name}.{label}.",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return temp_path
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _apply_wikilink_transaction(
    plan: tuple[WikiLinkRewrite, ...],
    *,
    rename_from: Path | None = None,
    rename_to: Path | None = None,
) -> list[Path]:
    logger = logging.getLogger("writeonside")
    logging_ready = bool(logger.handlers)
    rename_from = rename_from.resolve() if rename_from is not None else None
    rename_to = rename_to.resolve() if rename_to is not None else None
    staged: list[_StagedWikiLinkRewrite] = []
    committed: list[_StagedWikiLinkRewrite] = []
    renamed = False
    try:
        if (rename_from is None) != (rename_to is None):
            raise ValueError("rename_from and rename_to must be provided together")
        if rename_from is not None and rename_to is not None:
            if not rename_from.is_file():
                raise OSError(f"Rename source does not exist: {rename_from}")
            if rename_to.exists() and rename_to != rename_from:
                raise FileExistsError(rename_to)

        destinations: set[Path] = set()
        for rewrite in plan:
            destination = rename_to if rename_from is not None and rewrite.path == rename_from else rewrite.path
            if destination in destinations:
                raise OSError(f"Duplicate Wiki link transaction destination: {destination}")
            destinations.add(destination)
            updated_temp = _write_transaction_temp(destination, rewrite.updated, "updated")
            try:
                rollback_temp = _write_transaction_temp(destination, rewrite.original, "rollback")
            except Exception:
                updated_temp.unlink(missing_ok=True)
                raise
            staged.append(
                _StagedWikiLinkRewrite(
                    rewrite=rewrite,
                    destination=destination,
                    updated_temp=updated_temp,
                    rollback_temp=rollback_temp,
                )
            )

        if logging_ready:
            logger.info(
                "Wiki rename transaction prepared: %s -> %s; rewrites=%d",
                rename_from,
                rename_to,
                len(staged),
            )
        if rename_from is not None and rename_to is not None and rename_from != rename_to:
            rename_from.rename(rename_to)
            renamed = True
        for item in staged:
            os.replace(item.updated_temp, item.destination)
            committed.append(item)

        for item in staged:
            item.rollback_temp.unlink(missing_ok=True)
        if logging_ready:
            logger.info("Wiki rename transaction committed; rewrites=%d", len(committed))
        return [item.destination for item in staged]
    except Exception:
        if logging_ready:
            logger.exception(
                "Wiki rename transaction failed; rolling back: %s -> %s; committed=%d",
                rename_from,
                rename_to,
                len(committed),
            )
        for item in reversed(committed):
            try:
                os.replace(item.rollback_temp, item.destination)
            except OSError:
                if logging_ready:
                    logger.exception("Unable to roll back Wiki link file: %s", item.destination)
        if renamed and rename_from is not None and rename_to is not None:
            try:
                if rename_to.exists() and not rename_from.exists():
                    rename_to.rename(rename_from)
            except OSError:
                if logging_ready:
                    logger.exception("Unable to roll back note rename: %s -> %s", rename_to, rename_from)
        raise
    finally:
        for item in staged:
            for temp_path in (item.updated_temp, item.rollback_temp):
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass


def rewrite_wikilinks_after_rename(
    root: Path,
    old_path: Path,
    new_path: Path,
    *,
    old_title: str,
    old_aliases: tuple[str, ...],
    new_title: str | None = None,
    index: WikiLinkIndex | None = None,
    candidate_paths: set[Path] | None = None,
) -> list[Path]:
    plan = plan_wikilink_rewrites_after_rename(
        root,
        old_path,
        new_path,
        old_title=old_title,
        old_aliases=old_aliases,
        new_title=new_title,
        index=index,
        candidate_paths=candidate_paths,
    )
    return _apply_wikilink_transaction(plan)


def rename_note_and_rewrite_wikilinks(
    root: Path,
    old_path: Path,
    new_path: Path,
    *,
    old_title: str,
    old_aliases: tuple[str, ...],
    index: WikiLinkIndex,
    candidate_paths: set[Path],
) -> list[Path]:
    plan = plan_wikilink_rewrites_after_rename(
        root,
        old_path,
        new_path,
        old_title=old_title,
        old_aliases=old_aliases,
        new_title=new_path.stem,
        index=index,
        candidate_paths=candidate_paths,
    )
    return _apply_wikilink_transaction(
        plan,
        rename_from=old_path,
        rename_to=new_path,
    )


def is_markdown_note_path(path: Path) -> bool:
    return path.suffix.casefold() == ".md"


class WikiLinkIndex:
    def __init__(self, root: Path, notes: dict[Path, WikiNote]) -> None:
        self.root = root.resolve()
        self.notes = notes
        self._lookup: dict[str, list[Path]] = {}
        self._asset_cache: dict[tuple[str, str | None], Path | None] = {}
        for path, note in notes.items():
            relative = path.relative_to(self.root).with_suffix("").as_posix()
            keys = {
                normalize_wiki_name(relative),
                normalize_wiki_name(path.stem),
                normalize_wiki_name(note.title),
                *(normalize_wiki_name(alias) for alias in note.aliases),
            }
            for key in keys:
                if key:
                    self._lookup.setdefault(key, []).append(path)
        # Fix #11: build reverse-link index at construction time so
        # backlinks() is O(1) instead of O(N×L) per query.
        self._backlinks_index: dict[Path, list[tuple[WikiNote, WikiLink]]] = {}
        self._build_backlinks_index()

    def _build_backlinks_index(self) -> None:
        """Populate self._backlinks_index: target_path → [(source_note, link), ...]."""
        index: dict[Path, list[tuple[WikiNote, WikiLink]]] = {}
        for note in self.notes.values():
            for link in note.links:
                target = self.resolve(link.target, note.path)
                if target is not None:
                    index.setdefault(target, []).append((note, link))
        # Sort each bucket once so callers get a stable, alphabetical order
        for entries in index.values():
            entries.sort(
                key=lambda item: (item[0].title.casefold(), str(item[0].path).casefold())
            )
        self._backlinks_index = index

    @classmethod
    def build(cls, root: Path, previous: WikiIndexState | None = None) -> "WikiLinkIndex":
        index, _state = refresh_wiki_index(root, previous)
        return index

    def resolve(self, target: str, source: Path | None = None) -> Path | None:
        key = normalize_wiki_name(target)
        if not key:
            return source.resolve() if source else None

        direct = Path(target.replace("\\", "/"))
        if direct.suffix.casefold() != ".md":
            direct = direct.with_suffix(".md")
        candidates: list[Path] = []
        if source is not None:
            candidates.append((source.parent / direct).resolve())
        candidates.append((self.root / direct).resolve())
        for candidate in candidates:
            if candidate in self.notes:
                return candidate

        matches = self._lookup.get(key, [])
        if not matches:
            return None
        if source is None or len(matches) == 1:
            return matches[0]
        source_parent = source.resolve().parent
        return min(matches, key=lambda path: _path_distance(source_parent, path.parent))

    def resolve_asset(self, target: str, source: Path | None = None) -> Path | None:
        cache_key = (target.strip().casefold(), str(source.resolve()) if source else None)
        if cache_key in self._asset_cache:
            return self._asset_cache[cache_key]
        cleaned = target.strip().replace("\\", "/")
        if not cleaned:
            self._asset_cache[cache_key] = None
            return None
        raw = Path(cleaned)
        candidates: list[Path] = []
        if source is not None:
            candidates.append((source.parent / raw).resolve())
        candidates.append((self.root / raw).resolve())
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                self._asset_cache[cache_key] = candidate
                return candidate
        name = raw.name.casefold()
        try:
            matches = [
                path.resolve()
                for path in self.root.rglob(raw.name)
                if path.is_file() and path.name.casefold() == name and not is_hidden_relative(path, self.root)
            ]
        except OSError:
            self._asset_cache[cache_key] = None
            return None
        if not matches:
            self._asset_cache[cache_key] = None
            return None
        resolved = matches[0] if source is None or len(matches) == 1 else min(
            matches, key=lambda path: _path_distance(source.resolve().parent, path.parent)
        )
        self._asset_cache[cache_key] = resolved
        return resolved

    def backlinks(self, target_path: Path) -> list[tuple[WikiNote, WikiLink]]:
        # Fix #11: O(1) lookup via pre-built reverse index (was O(N×L) full scan)
        resolved_target = target_path.resolve()
        return list(self._backlinks_index.get(resolved_target, []))

    def suggestions(self, query: str, limit: int = 12) -> list[WikiNote]:
        normalized = query.strip().casefold()
        notes = list(self.notes.values())
        if normalized:
            notes = [
                note
                for note in notes
                if normalized in note.title.casefold()
                or normalized in note.path.stem.casefold()
                or any(normalized in alias.casefold() for alias in note.aliases)
            ]
        notes.sort(
            key=lambda note: (
                0 if note.title.casefold().startswith(normalized) else 1,
                note.title.casefold(),
            )
        )
        return notes[:limit]


def _path_distance(left: Path, right: Path) -> int:
    left_parts = left.parts
    right_parts = right.parts
    common = 0
    for left_part, right_part in zip(left_parts, right_parts):
        if left_part.casefold() != right_part.casefold():
            break
        common += 1
    return (len(left_parts) - common) + (len(right_parts) - common)
