"""Duplicate detection. Pure logic: no GUI and no file modification.

Candidates are narrowed in three increasingly expensive stages, so most
non-duplicates are discarded before their full content is read:

    file size  ->  hash of the first 64 KiB  ->  hash of the full content
"""

from __future__ import annotations

import os
import stat as stat_module
import threading
from collections import defaultdict
from pathlib import Path
from typing import Callable, Hashable, Iterable, Iterator, Optional

from .errors import FileChangedError
from .hashing import full_digest, partial_digest
from .models import DuplicateGroup, FileIssue, IssueKind, ScanResult
from .progress import ProgressCallback, ProgressReporter, Stage

PathGroups = list[list[Path]]
FileFilter = Callable[[Path], bool]


def find_duplicates(
    *roots: Path,
    min_size: int = 1,
    file_filter: Optional[FileFilter] = None,
    shared_only: bool = False,
    on_progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> ScanResult:
    """Return every group of identical files below any of ``roots``.

    Copies are matched across all roots, so a file in one folder and its twin
    in another form a single group. With ``shared_only``, only groups that
    span two or more roots are returned (the files the folders have in common).

    Files smaller than ``min_size`` bytes are ignored (by default, empty files,
    which are trivially "identical" but free no space), and so are files
    ``file_filter`` rejects (e.g. an ``ExtensionFilter``).
    Raises ``OperationCancelled`` if ``cancel_event`` is set.
    """
    if not roots:
        raise ValueError("At least one folder is required.")
    roots = tuple(Path(root).resolve() for root in roots)
    reporter = ProgressReporter(on_progress, cancel_event)
    errors: list[FileIssue] = []

    files_by_size = _collect_files_by_size(roots, min_size, file_filter, reporter, errors)
    total_files = sum(len(paths) for paths in files_by_size.values())

    size_groups = [paths for paths in files_by_size.values() if len(paths) > 1]
    size_of = {
        path: size for size, paths in files_by_size.items() if len(paths) > 1 for path in paths
    }
    partial_groups = [
        paths
        for _, paths in _regroup(
            size_groups, partial_digest, Stage.PARTIAL_HASH, reporter, errors
        )
    ]
    full_groups = _regroup(
        partial_groups, _stable_full_digest, Stage.FULL_HASH, reporter, errors
    )

    groups = [
        _build_group(str(digest), paths, size_of[paths[0]]) for digest, paths in full_groups
    ]
    if shared_only:
        groups = [group for group in groups if _roots_spanned(group, roots) > 1]
    groups.sort(key=lambda group: (-group.size, _sort_key(group.files[0])))
    return ScanResult(roots, tuple(groups), total_files, tuple(errors))


def _roots_spanned(group: DuplicateGroup, roots: tuple[Path, ...]) -> int:
    """How many of ``roots`` hold at least one file of ``group``."""
    return sum(
        any(path.is_relative_to(root) for path in group.files) for root in roots
    )


def _collect_files_by_size(
    roots: Iterable[Path],
    min_size: int,
    file_filter: Optional[FileFilter],
    reporter: ProgressReporter,
    errors: list[FileIssue],
) -> dict[int, list[Path]]:
    """Walk every root and bucket regular files by size.

    Symlinks and Windows junctions are never followed, and hard links to an
    already-seen file are skipped: they share storage, so "removing" one
    frees nothing and would only mislead the user.
    """
    files_by_size: dict[int, list[Path]] = defaultdict(list)
    seen_inodes: set[tuple[int, int]] = set()
    count = 0

    def on_walk_error(exc: OSError) -> None:
        errors.append(FileIssue.from_os_error(exc.filename, exc))

    for path in _walk_files(roots, reporter, on_walk_error):
        if file_filter is not None and not file_filter(path):
            continue  # checked first: it needs no disk access
        try:
            if _is_link_like(path):
                continue
            stat = path.stat()
        except OSError as exc:
            errors.append(FileIssue.from_os_error(path, exc))
            continue

        # Excludes FIFOs, sockets and devices, which must never be read.
        if not stat_module.S_ISREG(stat.st_mode) or stat.st_size < min_size:
            continue
        inode = (stat.st_dev, stat.st_ino)
        if inode in seen_inodes:  # also covers a file reached through two roots
            continue
        seen_inodes.add(inode)

        files_by_size[stat.st_size].append(path)
        count += 1
        reporter.report(Stage.COLLECTING, count)

    return files_by_size


def _walk_files(
    roots: Iterable[Path], reporter: ProgressReporter, on_error: Callable[[OSError], None]
) -> Iterator[Path]:
    """Every file name below ``roots``, without descending into linked folders."""
    for root in roots:
        for current_dir, dirs, filenames in os.walk(root, onerror=on_error):
            reporter.check_cancelled()
            current = Path(current_dir)
            dirs[:] = [name for name in dirs if not _is_link_like(current / name)]
            yield from (current / filename for filename in filenames)


def _regroup(
    groups: PathGroups,
    key_func: Callable[[Path], Hashable],
    stage: Stage,
    reporter: ProgressReporter,
    errors: list[FileIssue],
) -> list[tuple[Hashable, list[Path]]]:
    """Split each group by ``key_func`` and keep only sub-groups of 2+ files.

    One generic step reused by every hashing stage (DRY).
    """
    total = sum(len(paths) for paths in groups)
    done = 0
    result: list[tuple[Hashable, list[Path]]] = []

    for paths in groups:
        buckets: dict[Hashable, list[Path]] = defaultdict(list)
        for path in paths:
            reporter.check_cancelled()
            try:
                buckets[key_func(path)].append(path)
            except OSError as exc:
                errors.append(FileIssue.from_os_error(path, exc))
            done += 1
            reporter.report(stage, done, total)
        result.extend((key, bucket) for key, bucket in buckets.items() if len(bucket) > 1)

    return result


def _stable_full_digest(path: Path) -> str:
    """Full digest that rejects files modified while being read."""
    before = path.stat()
    digest = full_digest(path)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise FileChangedError(IssueKind.CHANGED_DURING_SCAN)
    return digest


def _build_group(digest: str, paths: list[Path], size: int) -> DuplicateGroup:
    return DuplicateGroup(size=size, digest=digest, files=tuple(sorted(paths, key=_sort_key)))


def _sort_key(path: Path) -> str:
    return str(path).casefold()


def _is_link_like(path: Path) -> bool:
    """Symlink, or (Python 3.12+, Windows) an NTFS junction."""
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())
