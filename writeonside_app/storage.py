import os
import re
import shutil
import tempfile
import hashlib
from datetime import datetime
from pathlib import Path

from .config import APP_DATA_DIR


BACKUP_DIR = APP_DATA_DIR / "Backups"
BACKUP_RETENTION = 20


def _vault_backup_key(workspace_root: Path) -> str:
    resolved = str(workspace_root.resolve()).casefold().encode("utf-8", errors="replace")
    return hashlib.sha256(resolved).hexdigest()[:12]


def _backup_existing_file(path: Path, workspace_root: Path | None) -> None:
    if not path.exists() or not path.is_file():
        return
    root = workspace_root.resolve() if workspace_root else path.parent.resolve()
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        relative = Path(path.name)
    backup_folder = BACKUP_DIR / _vault_backup_key(root) / relative.parent / relative.name
    backup_folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_folder / f"{stamp}{path.suffix}.bak"
    shutil.copy2(path, backup_path)
    backups = sorted(
        backup_folder.glob(f"*{path.suffix}.bak"),
        key=lambda item: item.stat().st_mtime_ns,
        reverse=True,
    )
    for old_backup in backups[BACKUP_RETENTION:]:
        try:
            old_backup.unlink()
        except OSError:
            pass


def safe_write_text(
    path: Path,
    content: str,
    encoding: str = "utf-8",
    newline: str = "\n",
    workspace_root: Path | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline=newline) as f:
            f.write(content)
        if path.exists():
            try:
                _backup_existing_file(path, workspace_root)
            except OSError:
                pass
        os.replace(temp_path, path)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def read_text_file(path: Path) -> str:
    # Fix #9: use utf-8-sig so that a UTF-8 BOM (\ufeff) is silently stripped,
    # consistent with note_index.py and wikilinks.py which also use utf-8-sig.
    return path.read_text(encoding="utf-8-sig")


def safe_note_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name).strip().strip(".")
    if not name:
        name = "Untitled"
    if not name.lower().endswith(".md"):
        name += ".md"
    return name
