from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import platform
import shutil
import sys
import time
import traceback
import zipfile
from importlib import metadata
from pathlib import Path
from types import TracebackType

from .config import APP_DATA_DIR, CONFIG_FILE

LOG_DIR = APP_DATA_DIR / "Logs"
REPORT_DIR = APP_DATA_DIR / "DiagnosticReports"
LOG_FILE = LOG_DIR / "writeonside.log"
STARTUP_FAILURE_FILE = LOG_DIR / "startup_failure.txt"
MAX_LOG_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3

_LOGGER_NAME = "writeonside"
_configured = False


def _version_text() -> str:
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def _dependency_versions() -> dict[str, str]:
    names = ("keyboard", "Pillow", "pystray", "Pygments", "tkinterdnd2", "watchdog")
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def configure_logging() -> logging.Logger:
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if _configured:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    _configured = True
    return logger


def get_logger() -> logging.Logger:
    return configure_logging()


def log_startup(argv: list[str] | None = None) -> None:
    logger = get_logger()
    logger.info("Starting WriteOnSide v%s", _version_text())
    logger.info("Python: %s", sys.version.replace("\n", " "))
    logger.info("Platform: %s", platform.platform())
    logger.info("Executable: %s", sys.executable)
    if argv is not None:
        logger.info("Args: %s", argv)


def log_exception(
    message: str,
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
) -> None:
    get_logger().error(message, exc_info=(exc_type, exc, tb))


def write_startup_failure_report(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    content = [
        f"WriteOnSide startup failure at {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Version: {_version_text()}",
        f"Python: {sys.version.replace(chr(10), ' ')}",
        f"Platform: {platform.platform()}",
        f"Executable: {sys.executable}",
        "",
        "".join(traceback.format_exception(exc_type, exc, tb)),
    ]
    STARTUP_FAILURE_FILE.write_text("\n".join(content), encoding="utf-8")
    return STARTUP_FAILURE_FILE


def install_exception_hooks() -> None:
    def excepthook(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
        log_exception("Unhandled exception", exc_type, exc, tb)
        sys.__excepthook__(exc_type, exc, tb)

    def threading_excepthook(args) -> None:
        log_exception(
            f"Unhandled thread exception in {getattr(args.thread, 'name', 'unknown')}",
            args.exc_type,
            args.exc_value,
            args.exc_traceback,
        )

    sys.excepthook = excepthook
    if hasattr(sys, "unraisablehook"):
        original_unraisablehook = sys.unraisablehook

        def unraisablehook(args) -> None:
            get_logger().error(
                "Unraisable exception: %r",
                args.object,
                exc_info=(type(args.exc_value), args.exc_value, args.exc_traceback),
            )
            original_unraisablehook(args)

        sys.unraisablehook = unraisablehook
    try:
        import threading

        threading.excepthook = threading_excepthook
    except Exception:
        pass


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _copy_if_exists(zip_file: zipfile.ZipFile, path: Path, arcname: str) -> None:
    if path.exists() and path.is_file():
        zip_file.write(path, arcname)


def export_diagnostic_report(destination: Path | None = None) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    destination = destination or (REPORT_DIR / f"WriteOnSide-diagnostics-{timestamp}.zip")
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    temp_dir = REPORT_DIR / f".diagnostics-{timestamp}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True)
    try:
        _write_json(
            temp_dir / "environment.json",
            {
                "version": _version_text(),
                "python": sys.version,
                "platform": platform.platform(),
                "executable": sys.executable,
                "frozen": bool(getattr(sys, "frozen", False)),
                "dependencies": _dependency_versions(),
                "app_data_dir": str(APP_DATA_DIR),
            },
        )
        if CONFIG_FILE.exists():
            _copy_if_exists_to_path(CONFIG_FILE, temp_dir / "config.json")

        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in temp_dir.iterdir():
                archive.write(file, file.name)
            for index, log_path in enumerate([LOG_FILE, *sorted(LOG_DIR.glob("writeonside.log.*"))]):
                _copy_if_exists(archive, log_path, f"logs/{index}-{log_path.name}")
            _copy_if_exists(archive, STARTUP_FAILURE_FILE, "startup_failure.txt")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    get_logger().info("Diagnostic report exported: %s", destination)
    return destination


def _copy_if_exists_to_path(source: Path, destination: Path) -> None:
    if source.exists() and source.is_file():
        shutil.copy2(source, destination)
