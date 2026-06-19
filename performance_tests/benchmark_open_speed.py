from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path
from statistics import mean, median
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from writeonside_app.document_performance import metrics_for_content
from writeonside_app.markdown import render_markdown
from writeonside_app.text_files import read_editable_text
from writeonside_app.theme import get_theme
from writeonside_app.ui.editor import READ_MODE_FRAGMENT_LINES, _build_outline_cache_data


DEFAULT_FILES = (
    Path(__file__).with_name("test_5mb.md"),
    Path(__file__).with_name("test_10mb.md"),
    Path(__file__).with_name("test_20mb.md"),
)


def summarize(values: list[float]) -> str:
    return (
        f"min={min(values):.1f} ms, "
        f"median={median(values):.1f} ms, "
        f"mean={mean(values):.1f} ms, "
        f"max={max(values):.1f} ms"
    )


def benchmark_file(path: Path, root: tk.Tk, text: tk.Text, read_text: tk.Text, runs: int) -> None:
    read_times: list[float] = []
    insert_times: list[float] = []
    render_times: list[float] = []
    outline_times: list[float] = []

    for _ in range(runs):
        start = perf_counter()
        content, encoding, newline = read_editable_text(path)
        read_times.append((perf_counter() - start) * 1000)

    content, encoding, newline = read_editable_text(path)
    metrics = metrics_for_content(content)
    lines = content.splitlines()
    fragment = "\n".join(lines[:READ_MODE_FRAGMENT_LINES])
    if fragment:
        fragment += "\n"

    ui_runs = max(1, min(runs, 3))
    for _ in range(ui_runs):
        text.delete("1.0", tk.END)
        start = perf_counter()
        text.insert("1.0", content)
        text.edit_reset()
        text.edit_modified(False)
        root.update_idletasks()
        insert_times.append((perf_counter() - start) * 1000)

        read_text.delete("1.0", tk.END)
        start = perf_counter()
        render_markdown(read_text, fragment, path, "Segoe UI", 11)
        root.update_idletasks()
        render_times.append((perf_counter() - start) * 1000)

        start = perf_counter()
        _build_outline_cache_data(content)
        outline_times.append((perf_counter() - start) * 1000)

    edit_first_paint = median(read_times) + median(insert_times)
    read_first_paint = edit_first_paint + median(render_times)

    print(f"FILE {path.name}")
    print(f"size_mb={path.stat().st_size / 1024 / 1024:.2f}")
    print(f"chars={metrics.characters} lines={metrics.lines} encoding={encoding} newline={newline!r}")
    print(f"read: {summarize(read_times)}")
    print(f"tk_insert: {summarize(insert_times)}")
    print(f"read_fragment_render: {summarize(render_times)}")
    print(f"background_outline: {summarize(outline_times)}")
    print(f"estimated_edit_first_paint={edit_first_paint:.1f} ms")
    print(f"estimated_read_first_paint={read_first_paint:.1f} ms")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark WriteOnSide large Markdown opening speed.")
    parser.add_argument("files", nargs="*", type=Path, default=list(DEFAULT_FILES))
    parser.add_argument("--runs", type=int, default=5, help="Number of read runs; UI runs are capped at 3.")
    args = parser.parse_args()

    missing = [path for path in args.files if not path.exists()]
    if missing:
        for path in missing:
            print(f"Missing benchmark file: {path}", file=sys.stderr)
        return 1

    import writeonside_app.markdown as markdown_module

    palette = get_theme("graphite")
    for key, value in palette.items():
        setattr(markdown_module, key, value)

    root = tk.Tk()
    root.withdraw()
    text = tk.Text(root, width=100, height=40, undo=True, wrap="word")
    read_text = tk.Text(root, width=100, height=40)
    text.pack()
    read_text.pack()
    root.update_idletasks()
    try:
        for path in args.files:
            benchmark_file(path.resolve(), root, text, read_text, max(1, args.runs))
    finally:
        root.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
