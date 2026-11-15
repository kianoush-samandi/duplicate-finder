"""The user's decisions while reviewing results: which copy to keep, which groups to skip.

Kept separate from the GUI so the rules are unit-testable and reusable by
any future front end (CLI, web, ...).
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .models import DuplicateGroup, Selection


class ReviewPlan:
    """By default every group is included and its first file is kept."""

    def __init__(self, groups: Sequence[DuplicateGroup]) -> None:
        self._groups = tuple(groups)
        self._keepers = {index: group.files[0] for index, group in enumerate(self._groups)}
        self._skipped: set[int] = set()

    @property
    def groups(self) -> tuple[DuplicateGroup, ...]:
        return self._groups

    def keeper(self, group_index: int) -> Path:
        return self._keepers[group_index]

    def set_keeper(self, group_index: int, path: Path) -> None:
        if path not in self._groups[group_index].files:
            raise ValueError(f"{path} is not part of group {group_index}")
        self._keepers[group_index] = path

    def is_skipped(self, group_index: int) -> bool:
        return group_index in self._skipped

    def toggle_skipped(self, group_index: int) -> bool:
        """Flip the group's skipped state and return the new state."""
        self._skipped ^= {group_index}
        return self.is_skipped(group_index)

    def selections(self) -> list[Selection]:
        return [
            Selection(group, self._keepers[index])
            for index, group in enumerate(self._groups)
            if index not in self._skipped
        ]

    @property
    def files_to_remove_count(self) -> int:
        return sum(len(selection.files_to_remove) for selection in self.selections())

    @property
    def reclaimable_bytes(self) -> int:
        return sum(selection.group.reclaimable_bytes for selection in self.selections())
