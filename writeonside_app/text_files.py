from __future__ import annotations

import codecs
from pathlib import Path

READ_CHUNK_SIZE = 1024 * 1024


EDITABLE_TEXT_SUFFIXES = {
    ".asm", ".bat", ".c", ".cc", ".cfg", ".clj", ".cljs", ".cmd", ".conf",
    ".cpp", ".cs", ".css", ".csv", ".cxx", ".dart", ".ex", ".exs", ".fs",
    ".fsx", ".go", ".groovy", ".h", ".hh", ".hpp", ".htm", ".html", ".hxx",
    ".ini", ".java", ".js", ".json", ".jsx", ".kt", ".kts", ".less", ".log",
    ".lua", ".m", ".md", ".mm", ".pas", ".php", ".pl", ".pm", ".ps1", ".py",
    ".pyw", ".r", ".rb", ".rmd", ".rs", ".sass", ".scala", ".scss", ".sh",
    ".sql", ".svelte", ".swift", ".tex", ".toml", ".ts", ".tsx", ".tsv",
    ".txt", ".vb", ".vue", ".xml", ".yaml", ".yml", ".zig",
}

EDITABLE_TEXT_FILENAMES = {
    "cmakelists.txt", "dockerfile", "gemfile", "jenkinsfile", "makefile", "procfile",
}


def is_markdown_note(path: Path) -> bool:
    return path.suffix.lower() == ".md"


def is_editable_text_path(path: Path) -> bool:
    return path.suffix.lower() in EDITABLE_TEXT_SUFFIXES or path.name.casefold() in EDITABLE_TEXT_FILENAMES


def requested_file_from_args(args: list[str] | tuple[str, ...]) -> Path | None:
    for value in args:
        if not value or value.startswith("-"):
            continue
        path = Path(value).expanduser()
        if path.exists() and path.is_file():
            return path.resolve()
    return None


def _read_file_prefix(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(4096)


def _read_text_incremental(path: Path, encoding: str) -> str:
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    parts: list[str] = []
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            decoded = decoder.decode(chunk, final=False)
            if decoded:
                parts.append(decoded)
        final = decoder.decode(b"", final=True)
        if final:
            parts.append(final)
    return "".join(parts)


def read_editable_text(path: Path) -> tuple[str, str, str]:
    first_chunk = _read_file_prefix(path)
    if b"\x00" in first_chunk and not first_chunk.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise UnicodeError("The selected file appears to be binary.")
    if first_chunk.startswith(b"\xef\xbb\xbf"):
        encodings = ("utf-8-sig",)
    elif first_chunk.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ("utf-16",)
    else:
        encodings = ("utf-8", "gb18030")
    for encoding in encodings:
        try:
            content = _read_text_incremental(path, encoding)
            has_cr = "\r" in content
            newline = "\r\n" if has_cr and "\r\n" in content else "\r" if has_cr else "\n"
            normalized = content.replace("\r\n", "\n").replace("\r", "\n") if has_cr else content
            return normalized, encoding, newline
        except UnicodeError:
            continue
    raise UnicodeError("The text encoding is not supported.")
