from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

import tkinter as tk

from ..attachment_index import (
    AttachmentIndexState,
    AttachmentInfo,
    attachment_index_is_current,
    refresh_attachment_index,
)

AttachmentIndexCallback = Callable[[Path | None, list[AttachmentInfo], Exception | None], None]


class AttachmentIndexMixin:
    def _setup_attachment_index(self) -> None:
        self._attachment_index_state: AttachmentIndexState | None = None
        self._attachment_index_after: str | None = None
        self._attachment_index_scan_id = 0
        self._attachment_index_scanning = False
        self._attachment_index_pending_force = False
        self._attachment_index_callbacks: list[AttachmentIndexCallback] = []

    def _schedule_attachment_index_refresh(self, *, delay_ms: int = 250, force: bool = False) -> None:
        if force:
            self._attachment_index_pending_force = True
        if self._attachment_index_after is not None:
            try:
                self.root.after_cancel(self._attachment_index_after)
            except tk.TclError:
                pass
        self._attachment_index_after = self.root.after(delay_ms, self._run_scheduled_attachment_index_refresh)

    def _run_scheduled_attachment_index_refresh(self) -> None:
        self._attachment_index_after = None
        force = self._attachment_index_pending_force
        self._attachment_index_pending_force = False
        self._refresh_attachment_index(force=force)

    def _refresh_attachment_index(self, *, force: bool = False) -> None:
        if self._attachment_index_scanning:
            if force:
                self._attachment_index_pending_force = True
            return

        workspace = self._workspace_dir().resolve()
        attachments_folder = self.config.attachments_folder
        previous = getattr(self, "_attachment_index_state", None)
        if not force and attachment_index_is_current(previous, workspace, attachments_folder):
            return

        self._attachment_index_scanning = True
        self._attachment_index_scan_id += 1
        generation = self._attachment_index_scan_id

        def worker() -> None:
            try:
                wiki_index = getattr(self, "_wiki_index", None)
                prev = getattr(self, "_attachment_index_state", None)
                root, items, state = refresh_attachment_index(
                    workspace,
                    attachments_folder,
                    wiki_index=wiki_index,
                    previous=prev,
                    force=force,
                )
                self.root.after(
                    0,
                    lambda: self._finish_attachment_index_scan(generation, root, items, state, None),
                )
            except Exception as exc:
                self.root.after(
                    0,
                    lambda: self._finish_attachment_index_scan(generation, None, [], None, exc),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _finish_attachment_index_scan(
        self,
        generation: int,
        root: Path | None,
        items: list[AttachmentInfo],
        state: AttachmentIndexState | None,
        error: Exception | None,
    ) -> None:
        if generation != self._attachment_index_scan_id:
            return
        self._attachment_index_scanning = False
        if error is None and state is not None:
            self._attachment_index_state = state

        callbacks = list(getattr(self, "_attachment_index_callbacks", []))
        self._attachment_index_callbacks.clear()
        for callback in callbacks:
            try:
                callback(root, items, error)
            except Exception:
                pass

        organizer = getattr(self, "_attachment_organizer_window", None)
        if organizer is not None and hasattr(organizer, "_on_app_index_updated"):
            try:
                if organizer.win is not None and organizer.win.winfo_exists():
                    organizer._on_app_index_updated(root, items, error)
            except tk.TclError:
                pass

        if self._attachment_index_pending_force:
            self._attachment_index_pending_force = False
            self._refresh_attachment_index(force=True)

    def _attachment_index_display_snapshot(self) -> tuple[Path, list[AttachmentInfo], bool] | None:
        state = getattr(self, "_attachment_index_state", None)
        if state is None:
            return None
        workspace = self._workspace_dir().resolve()
        current = attachment_index_is_current(state, workspace, self.config.attachments_folder)
        return state.root, list(state.items), current

    def _request_attachment_index(
        self,
        callback: AttachmentIndexCallback | None = None,
        *,
        force: bool = False,
    ) -> None:
        if callback is not None:
            self._attachment_index_callbacks.append(callback)

        if not force:
            snapshot = self._attachment_index_display_snapshot()
            if snapshot is not None:
                root, items, is_current = snapshot
                if callback is not None:
                    callback(root, items, None)
                if is_current and not self._attachment_index_scanning:
                    return

        if self._attachment_index_scanning and not force:
            return

        delay_ms = 0 if force else 80
        self._schedule_attachment_index_refresh(delay_ms=delay_ms, force=force)

    def _invalidate_attachment_index(self) -> None:
        self._attachment_index_state = None
        self._schedule_attachment_index_refresh(delay_ms=400, force=False)
