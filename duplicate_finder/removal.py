"""Removing approved duplicates, with re-verification before every change.

Safety rules:
  1. The copy being kept is verified first; if it changed or vanished,
     the whole group is skipped, so the last good copy is never lost.
  2. Each copy is re-verified (type, size, full content) right before removal.
  3. Nothing is deleted permanently: files go to a quarantine folder (with a
     manifest for restoring) or to the operating system's recycle bin.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Protocol

from .errors import FileChangedError
from .hashing import full_digest
from .models import DuplicateGroup, FileIssue, IssueKind, RemovalReport, Selection
from .progress import ProgressCallback, ProgressReporter, Stage

MANIFEST_NAME = "manifest.jsonl"


class Remover(Protocol):
    """Strategy for getting a verified duplicate out of the way."""

    def remove(self, path: Path) -> None: ...


def is_inside(child: Path, parent: Path) -> bool:
    """True if ``child`` is ``parent`` or located below it."""
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


class QuarantineRemover:
    """Moves files into a folder, mirroring their layout below the scan root.

    Every move is appended to ``manifest.jsonl`` immediately, so the record
    survives a crash halfway through and files can always be restored.
    """

    def __init__(self, quarantine_dir: Path, scan_root: Path) -> None:
        self.quarantine_dir = Path(quarantine_dir).resolve()
        self.scan_root = Path(scan_root).resolve()
        if is_inside(self.quarantine_dir, self.scan_root):
            raise ValueError("Quarantine folder must not be inside the scanned folder.")
        if is_inside(self.scan_root, self.quarantine_dir):
            raise ValueError("Quarantine folder must not contain the scanned folder.")

    @property
    def manifest_path(self) -> Path:
        return self.quarantine_dir / MANIFEST_NAME

    def remove(self, path: Path) -> None:
        destination = _unique_path(self.quarantine_dir / path.relative_to(self.scan_root))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))
        self._record(path, destination)

    def _record(self, original: Path, destination: Path) -> None:
        entry = {
            "moved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "original": str(original),
            "quarantined": str(destination),
        }
        with open(self.manifest_path, "a", encoding="utf-8") as manifest:
            manifest.write(json.dumps(entry, ensure_ascii=False) + "\n")


class TrashRemover:
    """Sends files to the OS recycle bin (requires the optional send2trash)."""

    def __init__(self) -> None:
        from send2trash import send2trash  # optional dependency, imported lazily

        self._send2trash = send2trash

    @staticmethod
    def is_available() -> bool:
        try:
            import send2trash  # noqa: F401
        except ImportError:
            return False
        return True

    def remove(self, path: Path) -> None:
        self._send2trash(str(path))


def remove_duplicates(
    selections: Iterable[Selection],
    remover: Remover,
    *,
    on_progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> RemovalReport:
    """Remove every non-keeper file of each approved group.

    Per-file failures are collected rather than raised, so one locked file
    does not abort the batch. Raises ``OperationCancelled`` between files.
    """
    selections = list(selections)
    reporter = ProgressReporter(on_progress, cancel_event)
    total = sum(len(selection.files_to_remove) for selection in selections)
    removed: list[Path] = []
    failures: list[FileIssue] = []
    done = 0

    for selection in selections:
        try:
            verify_unchanged(selection.keeper, selection.group)
        except OSError:
            failures.append(FileIssue(selection.keeper, IssueKind.KEEPER_CHANGED))
            done += len(selection.files_to_remove)
            continue

        for path in selection.files_to_remove:
            reporter.check_cancelled()
            try:
                verify_unchanged(path, selection.group)
                if os.path.samefile(path, selection.keeper):
                    raise FileChangedError(IssueKind.HARD_LINKED)
                remover.remove(path)
                removed.append(path)
            except OSError as exc:
                failures.append(FileIssue.from_os_error(path, exc))
            except ValueError as exc:  # e.g. a path outside the quarantine's scan root
                failures.append(FileIssue(path, IssueKind.ACCESS_ERROR, str(exc)))
            done += 1
            reporter.report(Stage.REMOVING, done, total)

    return RemovalReport(tuple(removed), tuple(failures))


def verify_unchanged(path: Path, group: DuplicateGroup) -> None:
    """Raise ``FileChangedError`` unless ``path`` still matches the scan."""
    if path.is_symlink() or not path.is_file():
        raise FileChangedError(IssueKind.MISSING)
    if path.stat().st_size != group.size:
        raise FileChangedError(IssueKind.SIZE_CHANGED)
    if full_digest(path) != group.digest:
        raise FileChangedError(IssueKind.CONTENT_CHANGED)


def _unique_path(path: Path) -> Path:
    """``path``, or ``name_duplicate_N.ext`` if it is already taken."""
    candidate, counter = path, 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_duplicate_{counter}{path.suffix}")
        counter += 1
    return candidate
