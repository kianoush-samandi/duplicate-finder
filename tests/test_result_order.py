from pathlib import Path

import pytest

from duplicate_finder.models import DuplicateGroup
from duplicate_finder.result_order import SortField, ordered_group_indices


def _group(name, size):
    return DuplicateGroup(size=size, digest=name, files=(Path(name), Path("copy") / name))


GROUPS = [_group("b.pdf", 30), _group("C.txt", 10), _group("a.zip", 20)]


@pytest.mark.parametrize(
    "field, descending, expected",
    [
        (SortField.SIZE, True, [0, 2, 1]),
        (SortField.SIZE, False, [1, 2, 0]),
        (SortField.NAME, False, [2, 0, 1]),  # case-insensitive
        (SortField.NAME, True, [1, 0, 2]),
        (SortField.TYPE, False, [0, 1, 2]),  # .pdf, .txt, .zip
        (SortField.TYPE, True, [2, 1, 0]),
    ],
)
def test_groups_are_ordered_by_the_chosen_field(field, descending, expected):
    assert ordered_group_indices(GROUPS, field, descending) == expected


def test_ties_are_broken_by_name():
    groups = [_group("z.txt", 5), _group("a.txt", 5)]
    assert ordered_group_indices(groups, SortField.SIZE, False) == [1, 0]
