from __future__ import annotations

from pathlib import Path


EDITABLE_TEXT_SUFFIXES = {
    ".bat", ".c", ".cfg", ".cmd", ".conf", ".cpp", ".cs", ".css", ".csv",
    ".go", ".h", ".hpp", ".htm", ".html", ".ini", ".java", ".js", ".json",
    ".jsx", ".log", ".lua", ".md", ".php", ".ps1", ".py", ".pyw", ".r",
    ".rb", ".rmd", ".rs", ".scss", ".sh", ".sql", ".tex", ".toml", ".ts",
    ".tsx", ".tsv", ".txt", ".xml", ".yaml", ".yml",
}


def is_markdown_note(path: Path) -> bool:
    return path.suffix.lower() == ".md"


def is_editable_text_path(path: Path) -> bool:
    return path.suffix.lower() in EDITABLE_TEXT_SUFFIXES


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
            newline = "\r\n" if b"\r\n" in data else "\r" if b"\r" in data else "\n"
            normalized = content.replace("\r\n", "\n").replace("\r", "\n")
            return normalized, encoding, newline
        except UnicodeError:
            continue
    raise UnicodeError("The text encoding is not supported.")
