"""Immutable data objects passed between the core layers and the GUI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class IssueKind(Enum):
    """Why a file could not be scanned or removed.

    Core code reports a kind, never a sentence: wording (and its language)
    is the presentation layer's job.
    """

    ACCESS_ERROR = "access_error"  # OS-level error; details in FileIssue.detail
    CHANGED_DURING_SCAN = "changed_during_scan"
    MISSING = "missing"
    SIZE_CHANGED = "size_changed"
    CONTENT_CHANGED = "content_changed"
    HARD_LINKED = "hard_linked"
    KEEPER_CHANGED = "keeper_changed"  # the whole group was skipped


@dataclass(frozen=True)
class FileIssue:
    path: Path
    kind: IssueKind
    detail: str = ""  # untranslated OS message, only for ACCESS_ERROR

    @classmethod
    def from_os_error(cls, path: Path, exc: OSError) -> "FileIssue":
        kind = getattr(exc, "kind", IssueKind.ACCESS_ERROR)
        detail = "" if kind is not IssueKind.ACCESS_ERROR else (exc.strerror or str(exc))
        return cls(Path(path), kind, detail)


@dataclass(frozen=True)
class DuplicateGroup:
    """Files whose contents are byte-for-byte identical."""

    size: int
    digest: str
    files: tuple[Path, ...]

    @property
    def reclaimable_bytes(self) -> int:
        """Space freed when every copy but one is removed."""
        return self.size * (len(self.files) - 1)


@dataclass(frozen=True)
class ScanResult:
    root: Path
    groups: tuple[DuplicateGroup, ...]
    total_files: int
    errors: tuple[FileIssue, ...]

    @property
    def reclaimable_bytes(self) -> int:
        return sum(group.reclaimable_bytes for group in self.groups)


@dataclass(frozen=True)
class Selection:
    """A group the user approved, together with the copies they chose to keep."""

    group: DuplicateGroup
    keepers: tuple[Path, ...]

    def __post_init__(self) -> None:
        if not self.keepers:
            raise ValueError("At least one copy of every group must be kept.")
        for keeper in self.keepers:
            if keeper not in self.group.files:
                raise ValueError(f"Keeper is not part of the group: {keeper}")

    @property
    def files_to_remove(self) -> tuple[Path, ...]:
        return tuple(path for path in self.group.files if path not in self.keepers)

    @property
    def reclaimable_bytes(self) -> int:
        return self.group.size * len(self.files_to_remove)


@dataclass(frozen=True)
class RemovalReport:
    removed: tuple[Path, ...]
    failures: tuple[FileIssue, ...]
