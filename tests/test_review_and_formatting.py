from pathlib import Path

import pytest

from duplicate_finder.formatting import format_size
from duplicate_finder.models import DuplicateGroup
from duplicate_finder.review import ReviewPlan


def _group(*names, size=10):
    return DuplicateGroup(size=size, digest="d", files=tuple(Path(n) for n in names))


def test_plan_defaults_to_first_file_and_all_groups():
    plan = ReviewPlan([_group("a", "b", "c"), _group("x", "y")])

    assert plan.kept_files(0) == (Path("a"),)
    assert plan.files_to_remove_count == 3
    assert plan.reclaimable_bytes == 30


def test_keep_only_changes_what_is_removed():
    plan = ReviewPlan([_group("a", "b")])
    plan.keep_only(0, Path("b"))

    (selection,) = plan.selections()
    assert selection.files_to_remove == (Path("a"),)


@pytest.mark.parametrize("action", ["keep_only", "keep", "mark_for_removal", "forget"])
def test_review_actions_reject_foreign_path(action):
    with pytest.raises(ValueError):
        getattr(ReviewPlan([_group("a", "b")]), action)(0, Path("zzz"))


def test_skipped_groups_are_excluded_and_can_be_restored():
    plan = ReviewPlan([_group("a", "b"), _group("x", "y")])

    assert plan.toggle_skipped(1) is True
    assert [s.group.files[0] for s in plan.selections()] == [Path("a")]
    assert plan.toggle_skipped(1) is False
    assert len(plan.selections()) == 2


def test_several_copies_can_be_kept():
    plan = ReviewPlan([_group("a", "b", "c")])
    plan.keep(0, Path("c"))

    (selection,) = plan.selections()
    assert selection.keepers == (Path("a"), Path("c"))
    assert selection.files_to_remove == (Path("b"),)
    assert plan.reclaimable_bytes == 10


def test_marked_copy_is_removed_and_last_kept_copy_is_protected():
    plan = ReviewPlan([_group("a", "b")])
    plan.keep(0, Path("b"))
    plan.mark_for_removal(0, Path("a"))

    assert plan.kept_files(0) == (Path("b"),)
    assert not plan.can_mark_for_removal(0, Path("b"))
    with pytest.raises(ValueError):
        plan.mark_for_removal(0, Path("b"))


def test_forget_keeps_a_copy_and_drops_groups_without_duplicates():
    plan = ReviewPlan([_group("a", "b", "c"), _group("x", "y")])
    plan.forget(0, Path("a"))  # "a" was the only kept copy

    assert plan.groups[0].files == (Path("b"), Path("c"))
    assert plan.kept_files(0) == (Path("b"),)

    plan.toggle_skipped(1)
    plan.forget(0, Path("b"))
    assert [g.files for g in plan.groups] == [(Path("x"), Path("y"))]
    assert plan.is_skipped(0)  # the surviving group kept its own state


def test_single_removal_pairs_the_file_with_a_kept_copy():
    plan = ReviewPlan([_group("a", "b", "c")])
    plan.keep_only(0, Path("c"))

    selection = plan.single_removal(0, Path("a"))
    assert selection.keepers == (Path("c"),)
    assert selection.files_to_remove == (Path("a"),)

    only_kept = plan.single_removal(0, Path("c"))  # falls back to another copy
    assert only_kept.files_to_remove == (Path("c"),)
    assert only_kept.keepers == (Path("a"),)


@pytest.mark.parametrize(
    "size, expected",
    [(0, "0.00 B"), (1023, "1023.00 B"), (1024, "1.00 KB"), (1536 * 1024, "1.50 MB"),
     (1024 ** 5, "1.00 PB"), (1024 ** 6, "1024.00 PB")],
)
def test_format_size(size, expected):
    assert format_size(size) == expected
