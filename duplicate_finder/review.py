"""The user's decisions while reviewing results: which copies to keep, which groups to skip.

Kept separate from the GUI so the rules are unit-testable and reusable by
any future front end (CLI, web, ...).

Invariant: every group keeps at least one copy, so carrying out the plan can
never remove the last copy of anything.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Sequence

from .models import DuplicateGroup, Selection


class ReviewPlan:
    """By default every group is included and only its first file is kept."""

    def __init__(self, groups: Sequence[DuplicateGroup]) -> None:
        self._groups: list[DuplicateGroup] = list(groups)
        self._kept: list[set[Path]] = [{group.files[0]} for group in self._groups]
        self._skipped: list[bool] = [False] * len(self._groups)

    @property
    def groups(self) -> tuple[DuplicateGroup, ...]:
        return tuple(self._groups)

    # ------------------------------------------------------------ kept copies

    def is_kept(self, group_index: int, path: Path) -> bool:
        return path in self._kept[group_index]

    def kept_files(self, group_index: int) -> tuple[Path, ...]:
        """The kept copies, in the group's order."""
        kept = self._kept[group_index]
        return tuple(path for path in self._groups[group_index].files if path in kept)

    def keep_only(self, group_index: int, path: Path) -> None:
        """Keep ``path`` and mark every other copy of the group for removal."""
        self._require_member(group_index, path)
        self._kept[group_index] = {path}

    def keep(self, group_index: int, path: Path) -> None:
        """Keep ``path`` too, leaving the other copies' marks as they are."""
        self._require_member(group_index, path)
        self._kept[group_index].add(path)

    def can_mark_for_removal(self, group_index: int, path: Path) -> bool:
        """False for the group's only kept copy (see the module invariant)."""
        return self._kept[group_index] != {path}

    def mark_for_removal(self, group_index: int, path: Path) -> None:
        self._require_member(group_index, path)
        if not self.can_mark_for_removal(group_index, path):
            raise ValueError(f"{path} is the only kept copy of group {group_index}")
        self._kept[group_index].discard(path)

    # ----------------------------------------------------------------- groups

    def is_skipped(self, group_index: int) -> bool:
        return self._skipped[group_index]

    def toggle_skipped(self, group_index: int) -> bool:
        """Flip the group's skipped state and return the new state."""
        self._skipped[group_index] = not self._skipped[group_index]
        return self._skipped[group_index]

    def forget(self, group_index: int, path: Path) -> None:
        """Drop a file that is gone from disk.

        A group left with a single file no longer holds duplicates and is
        dropped too, which shifts the indices of the groups after it.
        """
        self._require_member(group_index, path)
        group = self._groups[group_index]
        remaining = tuple(file for file in group.files if file != path)
        if len(remaining) < 2:
            del self._groups[group_index], self._kept[group_index], self._skipped[group_index]
            return
        self._groups[group_index] = replace(group, files=remaining)
        self._kept[group_index].discard(path)
        if not self._kept[group_index]:
            self._kept[group_index] = {remaining[0]}

    # ------------------------------------------------------------- selections

    def selection(self, group_index: int) -> Selection:
        return Selection(self._groups[group_index], self.kept_files(group_index))

    def selections(self) -> list[Selection]:
        return [
            self.selection(index)
            for index in range(len(self._groups))
            if not self._skipped[index]
        ]

    def single_removal(self, group_index: int, path: Path) -> Selection:
        """A Selection that removes just ``path``, whatever its mark.

        It is verified against one other copy (a kept one when possible), so
        removing it immediately is as safe as the batch removal.
        """
        self._require_member(group_index, path)
        others = [file for file in self._groups[group_index].files if file != path]
        reference = next((file for file in others if self.is_kept(group_index, file)), others[0])
        pair = replace(self._groups[group_index], files=(reference, path))
        return Selection(pair, (reference,))

    @property
    def files_to_remove_count(self) -> int:
        return sum(len(selection.files_to_remove) for selection in self.selections())

    @property
    def reclaimable_bytes(self) -> int:
        return sum(selection.reclaimable_bytes for selection in self.selections())

    def _require_member(self, group_index: int, path: Path) -> None:
        if path not in self._groups[group_index].files:
            raise ValueError(f"{path} is not part of group {group_index}")
