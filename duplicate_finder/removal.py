"""Removing approved duplicates, with re-verification before every change.

Safety rules:
  1. Every copy being kept is verified first; if one changed or vanished,
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
    """Moves files into a folder, mirroring their layout below the scanned folders.

    With one scanned folder, ``folder/sub/a.txt`` lands at ``quarantine/sub/a.txt``.
    With several, each one's files go below a sub-folder named after it
    (``quarantine/folder/sub/a.txt``), so copies from different folders stay apart.

    Every move is appended to ``manifest.jsonl`` immediately, so the record
    survives a crash halfway through and files can always be restored.
    """

    def __init__(self, quarantine_dir: Path, scan_roots: Iterable[Path]) -> None:
        self.quarantine_dir = Path(quarantine_dir).resolve()
        self.scan_roots = tuple(Path(root).resolve() for root in scan_roots)
        for root in self.scan_roots:
            if is_inside(self.quarantine_dir, root):
                raise ValueError("Quarantine folder must not be inside a scanned folder.")
            if is_inside(root, self.quarantine_dir):
                raise ValueError("Quarantine folder must not contain a scanned folder.")

    @property
    def manifest_path(self) -> Path:
        return self.quarantine_dir / MANIFEST_NAME

    def remove(self, path: Path) -> None:
        destination = _unique_path(self.quarantine_dir / self._mirrored_path(path))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))
        self._record(path, destination)

    def _mirrored_path(self, path: Path) -> Path:
        """``path`` relative to its scanned folder; raises ValueError if it has none."""
        for root in self.scan_roots:
            if is_inside(path, root):
                relative = path.relative_to(root)
                return relative if len(self.scan_roots) == 1 else Path(root.name) / relative
        raise ValueError(f"{path} is not inside a scanned folder.")

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
    """Remove every file of each approved group that is not marked to keep.

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
        changed_keeper = _first_changed_keeper(selection)
        if changed_keeper is not None:
            failures.append(FileIssue(changed_keeper, IssueKind.KEEPER_CHANGED))
            done += len(selection.files_to_remove)
            continue

        for path in selection.files_to_remove:
            reporter.check_cancelled()
            try:
                verify_unchanged(path, selection.group)
                if any(os.path.samefile(path, keeper) for keeper in selection.keepers):
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


def _first_changed_keeper(selection: Selection) -> Optional[Path]:
    """The first kept copy that no longer matches the scan, if any."""
    for keeper in selection.keepers:
        try:
            verify_unchanged(keeper, selection.group)
        except OSError:
            return keeper
    return None


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
