"""The order in which duplicate groups are listed. No Tk code here."""

from __future__ import annotations

from enum import Enum
from typing import Callable, Sequence

from .models import DuplicateGroup


class SortField(Enum):
    SIZE = "size"
    NAME = "name"
    TYPE = "type"  # file extension


def _name(group: DuplicateGroup) -> str:
    return group.files[0].name.casefold()


def _extension(group: DuplicateGroup) -> str:
    return group.files[0].suffix.casefold()


# Ties are broken by name, so the order is always predictable.
_SORT_KEYS: dict[SortField, Callable[[DuplicateGroup], tuple]] = {
    SortField.SIZE: lambda group: (group.size, _name(group)),
    SortField.NAME: lambda group: (_name(group), group.size),
    SortField.TYPE: lambda group: (_extension(group), _name(group)),
}


def ordered_group_indices(
    groups: Sequence[DuplicateGroup], field: SortField, descending: bool
) -> list[int]:
    """Indices of ``groups`` in display order; the groups themselves are not moved.

    Returning indices keeps the review plan, which is keyed by index, untouched.
    """
    key = _SORT_KEYS[field]
    return sorted(range(len(groups)), key=lambda index: key(groups[index]),
                  reverse=descending)
