"""Immutable data objects passed between the core layers and the GUI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    errors: tuple[str, ...]

    @property
    def reclaimable_bytes(self) -> int:
        return sum(group.reclaimable_bytes for group in self.groups)


@dataclass(frozen=True)
class Selection:
    """A group the user approved, together with the copy they chose to keep."""

    group: DuplicateGroup
    keeper: Path

    def __post_init__(self) -> None:
        if self.keeper not in self.group.files:
            raise ValueError(f"Keeper is not part of the group: {self.keeper}")

    @property
    def files_to_remove(self) -> tuple[Path, ...]:
        return tuple(path for path in self.group.files if path != self.keeper)


@dataclass(frozen=True)
class RemovalReport:
    removed: tuple[Path, ...]
    failures: tuple[str, ...]
