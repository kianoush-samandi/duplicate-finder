import os
import threading

import pytest

from duplicate_finder.errors import OperationCancelled
from duplicate_finder.hashing import PARTIAL_SIZE
from duplicate_finder.scanner import find_duplicates


def test_finds_identical_files_across_folders(tmp_path, make_file):
    a = make_file("a.txt", b"same content")
    b = make_file("sub/b.txt", b"same content")
    make_file("c.txt", b"different!!!")  # same size, different content

    result = find_duplicates(tmp_path)

    assert len(result.groups) == 1
    group = result.groups[0]
    assert set(group.files) == {a, b}
    assert group.size == len(b"same content")
    assert group.reclaimable_bytes == group.size
    assert result.total_files == 3


def test_files_identical_at_start_but_different_later_are_not_duplicates(tmp_path, make_file):
    prefix = b"x" * PARTIAL_SIZE
    make_file("a.bin", prefix + b"A")
    make_file("b.bin", prefix + b"B")

    assert find_duplicates(tmp_path).groups == ()


def test_empty_files_are_ignored_by_default(tmp_path, make_file):
    make_file("a", b"")
    make_file("b", b"")

    assert find_duplicates(tmp_path).groups == ()
    assert len(find_duplicates(tmp_path, min_size=0).groups) == 1


def test_hard_links_are_not_reported_as_duplicates(tmp_path, make_file):
    original = make_file("a.txt", b"hello")
    os.link(original, tmp_path / "link.txt")

    assert find_duplicates(tmp_path).groups == ()


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_symlinks_are_not_followed(tmp_path, make_file):
    target = make_file("a.txt", b"hello")
    (tmp_path / "file_link.txt").symlink_to(target)
    (tmp_path / "dir_link").symlink_to(tmp_path, target_is_directory=True)

    assert find_duplicates(tmp_path).groups == ()


@pytest.mark.skipif(
    os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced for root / on Windows",
)
def test_unreadable_folder_is_reported_not_swallowed(tmp_path, make_file):
    locked = tmp_path / "locked"
    make_file("locked/x.txt", b"data")
    locked.chmod(0)
    try:
        result = find_duplicates(tmp_path)
    finally:
        locked.chmod(0o755)
    assert any("locked" in error for error in result.errors)


def test_groups_are_sorted_largest_first(tmp_path, make_file):
    for name in ("s1", "s2"):
        make_file(name, b"small")
    for name in ("b1", "b2"):
        make_file(name, b"bigger content")

    sizes = [group.size for group in find_duplicates(tmp_path).groups]
    assert sizes == sorted(sizes, reverse=True)


def test_progress_is_reported_for_every_stage(tmp_path, make_file):
    make_file("a", b"dup")
    make_file("b", b"dup")
    stages = []

    find_duplicates(tmp_path, on_progress=lambda stage, done, total: stages.append(stage))

    assert {stage.value for stage in stages} >= {"partial_hash", "full_hash"}


def test_cancellation_stops_the_scan(tmp_path, make_file):
    make_file("a", b"dup")
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(OperationCancelled):
        find_duplicates(tmp_path, cancel_event=cancel)
