from pathlib import Path

import pytest

from duplicate_finder.formatting import format_size
from duplicate_finder.models import DuplicateGroup
from duplicate_finder.review import ReviewPlan


def _group(*names, size=10):
    return DuplicateGroup(size=size, digest="d", files=tuple(Path(n) for n in names))


def test_plan_defaults_to_first_file_and_all_groups():
    plan = ReviewPlan([_group("a", "b", "c"), _group("x", "y")])

    assert plan.keeper(0) == Path("a")
    assert plan.files_to_remove_count == 3
    assert plan.reclaimable_bytes == 30


def test_set_keeper_changes_what_is_removed():
    plan = ReviewPlan([_group("a", "b")])
    plan.set_keeper(0, Path("b"))

    (selection,) = plan.selections()
    assert selection.files_to_remove == (Path("a"),)


def test_set_keeper_rejects_foreign_path():
    with pytest.raises(ValueError):
        ReviewPlan([_group("a", "b")]).set_keeper(0, Path("zzz"))


def test_skipped_groups_are_excluded_and_can_be_restored():
    plan = ReviewPlan([_group("a", "b"), _group("x", "y")])

    assert plan.toggle_skipped(1) is True
    assert [s.group.files[0] for s in plan.selections()] == [Path("a")]
    assert plan.toggle_skipped(1) is False
    assert len(plan.selections()) == 2


@pytest.mark.parametrize(
    "size, expected",
    [(0, "0.00 B"), (1023, "1023.00 B"), (1024, "1.00 KB"), (1536 * 1024, "1.50 MB"),
     (1024 ** 5, "1.00 PB"), (1024 ** 6, "1024.00 PB")],
)
def test_format_size(size, expected):
    assert format_size(size) == expected
