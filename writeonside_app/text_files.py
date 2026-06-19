from __future__ import annotations

from pathlib import Path


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


def read_editable_text(path: Path) -> tuple[str, str, str]:
    data = path.read_bytes()
    if b"\x00" in data[:4096] and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise UnicodeError("The selected file appears to be binary.")
    if data.startswith(b"\xef\xbb\xbf"):
        encodings = ("utf-8-sig",)
    elif data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ("utf-16",)
    else:
        encodings = ("utf-8", "gb18030")
    for encoding in encodings:
        try:
            content = data.decode(encoding)
            has_cr = b"\r" in data
            newline = "\r\n" if has_cr and b"\r\n" in data else "\r" if has_cr else "\n"
            normalized = content.replace("\r\n", "\n").replace("\r", "\n") if has_cr else content
            return normalized, encoding, newline
        except UnicodeError:
            continue
    raise UnicodeError("The text encoding is not supported.")
